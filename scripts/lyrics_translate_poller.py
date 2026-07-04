#!/usr/bin/env python3
"""FEAT-lyrics-translation Step 3 — local lyrics-translation poller.

Drains `track_lyrics_translations(status='requested')` rows (filled by the lyrics
viewer's 번역 요청 button via POST /api/lyrics/{sid}/translation-request) and
translates each designated track line-by-line with **Amazon Translate**
(auto→ko, Formality=INFORMAL) — the genre-heal/research poller claim pattern
(launchd fires it every 60s; claim via FOR UPDATE SKIP LOCKED + a 20-min
claimed_at re-claim window). RFC: docs/rfcs/FEAT-lyrics-translation.md.

Engine note (decisions log 2026-07-04): the original engine, headless
`claude -p --model sonnet`, consistently REFUSES full-lyrics translation on
copyright grounds (sonnet and opus both, private-use context included) — the
RFC's in-session engine evidence does not replicate headless. Engine swapped to
Amazon Translate: per-line calls give 1:1 segment alignment by construction (no
length validation needed), the existing owner AWS credentials cover auth (no
new secret), and cost is ~$0.02/track after the 12-month free tier. Quality is
re-validated by the Step 3 pilot gate (15 tracks, ≥90% mistranslation-free).

Fingerprint parity by construction: this script imports `normalize_lyrics` +
`compute_source_fingerprint` from the LOCAL myblog_backend checkout, so the
fingerprint stored at translate time equals what the read path re-derives in
`attach_translation`. The backend repo must therefore sit on merged `main`
(same rule as the other pollers).

Flow per claimed row:
  load track_lyrics → normalize (same code as the read) → Korean-dominant guard
  (nothing to translate; closed as failed('korean_source')) → per-line Amazon
  Translate (already-Korean lines pass through untouched) → re-insert gaps as ""
  → upsert done + fingerprint (origin='poller').

REQUIRES the backend venv (psycopg v3 + boto3 + the shared_db pin) and
`translate:TranslateText` on the local AWS identity (claude_aws_manager inline
policy — console-managed, like claude-ssm-myblog):

    myblog_backend/.venv/bin/python scripts/lyrics_translate_poller.py           # one row
    myblog_backend/.venv/bin/python scripts/lyrics_translate_poller.py --drain   # until empty

Env: DATABASE_URL overrides; else resolved from SSM /myblog/backend (owner AWS creds).
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
import time
from pathlib import Path
from types import SimpleNamespace

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("lyrics-translate-poller")

ROOT = Path(__file__).resolve().parent.parent  # myblog-workspace/
BACKEND = ROOT / "myblog_backend"
sys.path.insert(0, str(BACKEND))

# Same normalizer + fingerprint as the read path (parity by construction — see header).
from app.services.lyrics_service import (  # noqa: E402
    NORMALIZER_VERSION,
    compute_source_fingerprint,
    normalize_lyrics,
)

REGION = "ap-northeast-2"
SSM_PARAM = "/myblog/backend"          # SecureString JSON holding DATABASE_URL
MT_MODEL = "amazon.translate"          # `model` column value — decisions log 2026-07-04
TRANSLATOR_VERSION = "v1"              # bump on any engine/pipeline change
STALE_CLAIM = "20 minutes"             # crash-recovery re-claim window
HANGUL_DOMINANT_RATIO = 0.5            # viewer heuristic mirror (OQ3)
INTER_RUN_SLEEP_S = 5                  # serial spacing in --drain mode


# --- secrets / db -----------------------------------------------------------
def database_url() -> str:
    url = os.environ.get("DATABASE_URL")
    if not url:
        import boto3

        ssm = boto3.client("ssm", region_name=REGION)
        url = json.loads(
            ssm.get_parameter(Name=SSM_PARAM, WithDecryption=True)["Parameter"]["Value"]
        )["DATABASE_URL"]
    # SQLAlchemy `postgresql+psycopg://` → the libpq form psycopg.connect wants.
    return re.sub(r"^postgresql\+\w+", "postgresql", url)


def connect():
    import psycopg
    from psycopg.rows import dict_row

    # connect_timeout=30 absorbs Neon cold-start (reference-database-url-psql).
    return psycopg.connect(database_url(), connect_timeout=30, row_factory=dict_row)


# --- claim / writeback ------------------------------------------------------
CLAIM_SQL = f"""
UPDATE track_lyrics_translations SET claimed_at = now(), updated_at = now()
WHERE track_id = (
    SELECT track_id FROM track_lyrics_translations
    WHERE status = 'requested'
      AND (claimed_at IS NULL OR claimed_at < now() - INTERVAL '{STALE_CLAIM}')
    ORDER BY requested_at
    LIMIT 1
    FOR UPDATE SKIP LOCKED
)
RETURNING track_id, lang;
"""

SOURCE_SQL = """
SELECT tl.match_status, tl.lyric_plain, tl.lyric_synced,
       t.id AS track_id, t.title, t.spotify_id,
       COALESCE(
           (SELECT array_agg(ar.name ORDER BY ar.name)
            FROM track_artists ta JOIN artists ar ON ar.id = ta.artist_id
            WHERE ta.track_id = t.id),
           '{}'
       ) AS artists
FROM tracks t
LEFT JOIN track_lyrics tl ON tl.track_id = t.id
WHERE t.id = %s;
"""


def mark_done(conn, track_id, stored_segments: list[dict], fingerprint: str) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE track_lyrics_translations
            SET status = 'done', segments = %s::jsonb, source_fingerprint = %s,
                normalizer_version = %s, origin = 'poller', model = %s,
                translator_version = %s, error = NULL,
                translated_at = now(), updated_at = now()
            WHERE track_id = %s;
            """,
            (json.dumps(stored_segments, ensure_ascii=False), fingerprint,
             NORMALIZER_VERSION, MT_MODEL, TRANSLATOR_VERSION, track_id),
        )
    conn.commit()


def mark_failed(conn, track_id, error: str) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE track_lyrics_translations "
            "SET status = 'failed', error = %s, updated_at = now() WHERE track_id = %s;",
            (error[:4000], track_id),
        )
    conn.commit()


# --- korean guard (viewer heuristic mirror, OQ3) ------------------------------
def hangul_ratio(text: str) -> float:
    letters = [ch for ch in text if ch.isalpha()]
    if not letters:
        return 0.0
    hangul = sum(1 for ch in letters if "가" <= ch <= "힣" or "ㄱ" <= ch <= "ㅣ")
    return hangul / len(letters)


# --- engine: Amazon Translate --------------------------------------------------
def translate_lines(lines: list[str], target_lang: str) -> list[str]:
    """Per-line Amazon Translate — 1:1 alignment by construction.

    Already-Korean lines pass through untouched (nothing to translate; also
    avoids auto-detect picking ko as both source and target). Formality
    INFORMAL keeps lyric register (반말) rather than 습니다-style prose.

    A line whose detected language has no →ko pair (auto-detect can land on
    Latin etc. for short interjections — LUX 'Porcelana' pilot) passes through
    untranslated instead of failing the whole track.
    """
    import boto3
    from botocore.exceptions import ClientError

    client = boto3.client("translate", region_name=REGION)
    out: list[str] = []
    for ln in lines:
        if hangul_ratio(ln) >= HANGUL_DOMINANT_RATIO:
            out.append(ln)
            continue
        try:
            r = client.translate_text(
                Text=ln,
                SourceLanguageCode="auto",
                TargetLanguageCode=target_lang,
                Settings={"Formality": "INFORMAL"},
            )
        except ClientError as e:
            code = e.response.get("Error", {}).get("Code", "")
            if code in ("UnsupportedLanguagePairException",
                        "DetectedLanguageLowConfidenceException"):
                log.warning("line passthrough (%s): %r", code, ln[:60])
                out.append(ln)
                continue
            raise
        out.append(r["TranslatedText"].strip() or ln)
    return out


# --- orchestration ------------------------------------------------------------
def process_one(conn) -> bool:
    """Claim and process one row. True if a row was handled, False if queue empty."""
    with conn.cursor() as cur:
        cur.execute(CLAIM_SQL)
        claim = cur.fetchone()
    conn.commit()  # release the lock; claimed_at now gates other pollers
    if claim is None:
        return False
    track_id = claim["track_id"]
    target_lang = claim["lang"] or "ko"

    try:
        with conn.cursor() as cur:
            cur.execute(SOURCE_SQL, (track_id,))
            src = cur.fetchone()
        if src is None:
            raise RuntimeError("track vanished")

        row = SimpleNamespace(  # normalize_lyrics only reads these attributes
            match_status=src["match_status"], lyric_plain=src["lyric_plain"],
            lyric_synced=src["lyric_synced"], track_id=track_id,
        ) if src["match_status"] is not None else None
        out = normalize_lyrics(row)
        if out.availability != "ok":
            mark_failed(conn, track_id, "source_unavailable")
            log.warning("row %s source availability=%s — failed", track_id, out.availability)
            return True

        non_gap = [s for s in out.segments if s.text != ""]
        joined = " ".join(s.text for s in non_gap)
        if hangul_ratio(joined) >= HANGUL_DOMINANT_RATIO:
            mark_failed(conn, track_id, "korean_source")
            log.info("row %s Korean-dominant (%.0f%%) — closed without MT call",
                     track_id, hangul_ratio(joined) * 100)
            return True

        log.info("claimed %s — %s / %s (%d lines, %d segments)",
                 track_id, src["title"], ", ".join(src["artists"]), len(non_gap),
                 len(out.segments))
        t0 = time.monotonic()
        texts_ko = translate_lines([s.text for s in non_gap], target_lang)
        dt = time.monotonic() - t0

        ko_by_i = {s.i: t for s, t in zip(non_gap, texts_ko)}
        stored = [{"i": s.i, "text_ko": ko_by_i.get(s.i, "")} for s in out.segments]
        fingerprint = compute_source_fingerprint(out.normalizer_version, out.segments)
        mark_done(conn, track_id, stored, fingerprint)
        log.info("done %s in %.1fs — %d lines translated, fp=%s…",
                 track_id, dt, len(non_gap), fingerprint[:12])
    except Exception as e:  # noqa: BLE001 — any failure marks the row; poller stays up
        conn.rollback()
        log.error("FAILED %s: %s", track_id, e)
        mark_failed(conn, track_id, str(e))
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description="Local lyrics-translation poller (Step 3).")
    ap.add_argument("--drain", action="store_true",
                    help="process rows until the queue is empty (default: one row, exit)")
    args = ap.parse_args()

    conn = connect()
    try:
        handled = process_one(conn)
        if not handled:
            log.info("no pending translation request")
            return 0
        while args.drain and process_one(conn):
            time.sleep(INTER_RUN_SLEEP_S)
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
