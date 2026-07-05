#!/usr/bin/env python3
"""FEAT-lyrics-engine-sonnet Step 1 — local lyrics-translation poller.

Drains `track_lyrics_translations(status='requested')` rows — filled by the
lyrics viewer's 번역 요청 button (POST /api/lyrics/{sid}/translation-request)
and, since FEAT-lyrics-translation-sweep, by a state-based sweep that runs at
the start of every firing: any track on an `album_research` album with viewable
matched lyrics and no translation row yet is INSERTed as `requested` (idempotent
— existing rows of any status are never touched). Each claimed track is
translated whole-lyric with headless
**`claude -p --model sonnet`** (benchmark-frozen 의역 prompt, 1:1 line mapping,
JSON-only output contract) — the genre-heal/research poller claim pattern
(launchd fires it every 60s; claim via FOR UPDATE SKIP LOCKED + a 20-min
claimed_at re-claim window). RFC: docs/rfcs/FEAT-lyrics-engine-sonnet.md.

Engine history:
  - Original plan (FEAT-lyrics-translation): `claude -p` — dropped 2026-07-04
    after headless refusals on copyright grounds (sonnet AND opus).
  - v1 shipped: per-line Amazon Translate (auto→ko, Formality=INFORMAL) —
    FEAT-lyrics-translation decisions log 2026-07-04.
  - v2 (this file): back to `claude -p --model sonnet`. The 2026-07-04 LUX
    benchmark (5 tracks × opus/sonnet/haiku, 194 non-gap lines) ran 15/15 PASS
    with 0 refusals — the earlier refusal keyed on PROMPT SHAPE (의역 framing +
    numbered lines + JSON-only output passes), not on headless-ness. Owner
    decision 2026-07-05: Sonnet, NO Amazon fallback — terminal engine failures
    are marked visibly (`failed`); transient CLI failures (session limit,
    timeout) leave the claim in place so the stale-claim window retries.

Fingerprint parity by construction: this script imports `normalize_lyrics` +
`compute_source_fingerprint` from the LOCAL myblog_backend checkout, so the
fingerprint stored at translate time equals what the read path re-derives in
`attach_translation`. The backend repo must therefore sit on merged `main`
(same rule as the other pollers).

Flow per claimed row:
  load track_lyrics → normalize (same code as the read) → Korean-dominant guard
  (nothing to translate; closed as failed('korean_source')) → one `claude -p`
  call over all non-gap lines (already-Korean lines come back verbatim per the
  prompt contract) → validate JSON/count/index alignment (retry once) →
  re-insert gaps as "" → upsert done + fingerprint (origin='poller').

REQUIRES the backend venv (psycopg v3 + boto3 for SSM + the shared_db pin) and
the `claude` CLI on PATH (owner subscription; the launchd plist puts
~/.local/bin on PATH):

    myblog_backend/.venv/bin/python scripts/lyrics_translate_poller.py               # one firing: sweep + up to BATCH_PER_RUN rows
    myblog_backend/.venv/bin/python scripts/lyrics_translate_poller.py --drain       # sweep + rows until empty
    myblog_backend/.venv/bin/python scripts/lyrics_translate_poller.py --sweep-only  # sweep only, no claims (dry observation)

Env: DATABASE_URL overrides; else resolved from SSM /myblog/backend (owner AWS
creds). LYRICS_CLAUDE_MODEL overrides the CLI model alias — test hook only
(a bogus alias exercises the transient-failure/claim-kept path end-to-end).
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import re
import shutil
import subprocess
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
MT_MODEL = "claude.sonnet"             # `model` column value — RFC provenance section
TRANSLATOR_VERSION = "v2"              # bump on any engine/pipeline change
ENGINE_CLI_MODEL = os.environ.get("LYRICS_CLAUDE_MODEL", "sonnet")  # CLI alias (OQ2: unpinned)
ENGINE_TIMEOUT_S = 300                 # per-track subprocess ceiling (bench max 43s @ 75 lines)
STALE_CLAIM = "20 minutes"             # crash-recovery re-claim window
HANGUL_DOMINANT_RATIO = 0.5            # viewer heuristic mirror (OQ3)
INTER_RUN_SLEEP_S = 5                  # serial spacing between claims
BATCH_PER_RUN = 5                      # claims per non-drain firing (sweep RFC OQ1: drop to 2-3 if Max sessions throttle)

# Benchmark-frozen 의역 prompt (RFC Target state — verbatim; 15/15 PASS 2026-07-04).
# Tuning it is a future change that bumps TRANSLATOR_VERSION.
PROMPT_HEADER = (
    "각 줄을 한국어로 **의역**해줘 — 축자적 직역이 아니라, 글의 정서와 핵심 의미를 자연스러운\n"
    "한국어로 옮겨. 단 반드시 원문 1줄 ↔ 번역 1줄로 대응시켜(줄 합치기·재배치·삭제 금지).\n"
    "이미 한국어인 줄은 그대로 둬. 출력은 오직 JSON 배열만, 설명 금지:\n"
    '[{"i":<원문 줄번호>,"ko":"<의역>"}]. 원문:\n'
    "---\n"
)


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


# --- sweep (FEAT-lyrics-translation-sweep) ------------------------------------
# The lyrics-body predicate mirrors normalize_lyrics availability=="ok" exactly
# (matched + non-blank synced or plain), so the sweep can never enqueue a track
# the claim path would reject as untranslatable. NOT EXISTS + ON CONFLICT DO
# NOTHING = never touch existing rows (done/failed/requested, any origin).
SWEEP_SQL = """
INSERT INTO track_lyrics_translations (track_id, status)
SELECT t.id, 'requested'
FROM tracks t
JOIN track_lyrics tl ON tl.track_id = t.id
WHERE tl.match_status = 'matched'
  AND (btrim(coalesce(tl.lyric_synced, '')) <> ''
       OR btrim(coalesce(tl.lyric_plain, '')) <> '')
  AND EXISTS (SELECT 1 FROM album_research ar WHERE ar.album_id = t.album_id)
  AND NOT EXISTS (SELECT 1 FROM track_lyrics_translations x WHERE x.track_id = t.id)
ON CONFLICT (track_id) DO NOTHING;
"""


def sweep(conn) -> int:
    """Derive the queue from state: enqueue every research-album track with
    viewable lyrics and no translation row. Returns the number inserted."""
    with conn.cursor() as cur:
        cur.execute(SWEEP_SQL)
        inserted = cur.rowcount
    conn.commit()
    if inserted > 0:
        log.info("sweep enqueued %d track(s) for translation", inserted)
    return inserted


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


# --- engine: headless claude -p (Sonnet) ----------------------------------------
class TransientEngineError(RuntimeError):
    """CLI-level failure (non-zero exit / timeout / missing binary) — the claim
    is left in place so the 20-min stale-claim window retries automatically
    (session budget exhaustion is self-healing, not a translation verdict)."""


class EngineValidationError(RuntimeError):
    """The engine replied but the output failed the contract (refusal prose,
    bad JSON, line-count or index-alignment break) — terminal after one retry."""


def _extract_json_array(stdout: str) -> str | None:
    """Bench-scorer extraction: strip an optional ```fence```, then take the
    outermost `[`..`]` span. Refusal prose has no array and returns None."""
    text = stdout.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    start, end = text.find("["), text.rfind("]")
    if start == -1 or end <= start:
        return None
    return text[start : end + 1]


def _claude_translate_once(lines: list[str]) -> list[str]:
    """One `claude -p --model sonnet` call over ALL non-gap lines; returns the
    translations in input order. Raises TransientEngineError (claim kept) or
    EngineValidationError (retried once by the caller)."""
    claude_bin = shutil.which("claude")
    if claude_bin is None:
        raise TransientEngineError("claude CLI not on PATH")
    prompt = PROMPT_HEADER + "\n".join(f"{n}: {ln}" for n, ln in enumerate(lines, 1))
    try:
        proc = subprocess.run(
            [claude_bin, "-p", "--model", ENGINE_CLI_MODEL],
            input=prompt, capture_output=True, text=True, timeout=ENGINE_TIMEOUT_S,
        )
    except subprocess.TimeoutExpired:
        raise TransientEngineError(f"engine timeout >{ENGINE_TIMEOUT_S}s") from None
    if proc.returncode != 0:
        detail = (proc.stderr.strip() or proc.stdout.strip())[:200]
        raise TransientEngineError(f"claude exit {proc.returncode}: {detail}")

    head = proc.stdout.strip()[:200]  # diagnostic capture (refusal prose lands here)
    raw = _extract_json_array(proc.stdout)
    if raw is None:
        raise EngineValidationError(f"no JSON array in output: {head}")
    try:
        items = json.loads(raw)
    except json.JSONDecodeError as e:
        raise EngineValidationError(f"bad JSON ({e}): {head}") from None
    if not isinstance(items, list) or len(items) != len(lines):
        got = len(items) if isinstance(items, list) else type(items).__name__
        raise EngineValidationError(f"line count {got} != {len(lines)}: {head}")
    ko_by_n: dict[int, str] = {}
    for it in items:
        if not (isinstance(it, dict) and isinstance(it.get("i"), int)
                and isinstance(it.get("ko"), str)):
            raise EngineValidationError(f"bad item shape {it!r:.80}: {head}")
        ko_by_n[it["i"]] = it["ko"]
    if set(ko_by_n) != set(range(1, len(lines) + 1)):
        raise EngineValidationError(f"index set != 1..{len(lines)}: {head}")
    # Empty translation falls back to the source line (mirrors the v1 behavior;
    # "" is the stored-gap sentinel and must not appear for a non-gap line).
    return [ko_by_n[n].strip() or lines[n - 1] for n in range(1, len(lines) + 1)]


def claude_translate(lines: list[str]) -> list[str]:
    """Engine call with the RFC failure policy: validation failure retries the
    call once; TransientEngineError propagates immediately (claim kept)."""
    try:
        return _claude_translate_once(lines)
    except EngineValidationError as e:
        log.warning("engine validation failed, retrying once: %s", e)
        return _claude_translate_once(lines)


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
            log.info("row %s Korean-dominant (%.0f%%) — closed without engine call",
                     track_id, hangul_ratio(joined) * 100)
            return True

        if target_lang != "ko":
            # The frozen prompt translates into Korean only (viewer only requests ko).
            mark_failed(conn, track_id, f"unsupported_target_lang: {target_lang}")
            log.warning("row %s target lang %r unsupported — failed", track_id, target_lang)
            return True

        log.info("claimed %s — %s / %s (%d lines, %d segments)",
                 track_id, src["title"], ", ".join(src["artists"]), len(non_gap),
                 len(out.segments))
        t0 = time.monotonic()
        try:
            texts_ko = claude_translate([s.text for s in non_gap])
        except TransientEngineError as e:
            # NOT a translation verdict — leave the claim in place; the 20-min
            # stale-claim window retries on a later cycle (RFC failure policy).
            log.warning("transient engine failure on %s — claim kept: %s", track_id, e)
            return True
        except EngineValidationError as e:
            mark_failed(conn, track_id, f"engine_validation: {e}")
            log.error("engine validation FAILED %s (both attempts): %s", track_id, e)
            return True
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
    ap = argparse.ArgumentParser(description="Local lyrics-translation poller (engine: claude -p sonnet).")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--drain", action="store_true",
                      help="process rows until the queue is empty "
                           f"(default: one firing, up to {BATCH_PER_RUN} rows)")
    mode.add_argument("--sweep-only", action="store_true",
                      help="run the sweep, report the inserted count, exit without claiming")
    args = ap.parse_args()

    conn = connect()
    try:
        sweep(conn)
        if args.sweep_only:
            return 0
        limit = None if args.drain else BATCH_PER_RUN
        handled = 0
        while limit is None or handled < limit:
            if not process_one(conn):
                break
            handled += 1
            if limit is None or handled < limit:
                time.sleep(INTER_RUN_SLEEP_S)
        if handled == 0:
            log.info("no pending translation request")
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
