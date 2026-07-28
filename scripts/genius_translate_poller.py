#!/usr/bin/env python3
"""Korean bodies for Genius annotations — FEAT-lyrics-annotations Thread 1.

The owner decision is that **the body a reader sees is always Korean**; the original
stays as the collapsible secondary. The fetch job (worker `genius_fetch`) writes
`body_source` and leaves `translation_status='pending'`. This fills `body_ko`.

**Why a local poller and not the worker Lambda.** The fetch job runs in Lambda by
owner decision (RFC §6.9 O1) because it only needs an HTTP token. Translation runs
`claude -p` on the owner's subscription, which has no Lambda equivalent — the same
constraint that already puts `lyrics_translate_poller.py` on launchd. Different
answer, different reason; not an inconsistency.

Sibling of `lyrics_translate_poller.py` and deliberately shaped like it: same
`CliEngine`, same SSM/DATABASE_URL resolution, same claim/stale-claim recovery.

Two things it does NOT copy, both because annotation bodies are a different shape
from lyric lines:

* **It batches by OUTPUT SIZE, not by row count.** Bodies run past 2,500 characters.
  The 2026-07-25 session lost two runs to exactly this: an agent given 4 tracks /
  38 annotations died on "response stalled mid-stream", and splitting into 2+1+1
  succeeded immediately. Size the output, not the input.
* **It translates one annotation per call.** A 1:1 line contract makes sense for
  lyrics, where a dropped line silently misaligns the whole track. Here each body is
  independent prose, so a per-body call means a refusal or a stall costs one row.

**The fingerprint is a twin and must not drift.** The read path recomputes
`sha256(body_source)` and withholds `body_ko` when it differs
(`lyrics_service.compute_body_fingerprint`). This imports that function rather than
reimplementing it — a local copy that drifted would mark every row stale and the UI
would silently show "아직 준비되지 않았습니다" for translations that exist.

Usage:
    python3 scripts/genius_translate_poller.py            # one bounded batch
    python3 scripts/genius_translate_poller.py --drain    # until the queue is empty
    python3 scripts/genius_translate_poller.py --limit 3
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import re
import shutil
import sys
import tempfile
import time
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("genius-translate-poller")

ROOT = Path(__file__).resolve().parent.parent  # myblog-workspace/
sys.path.insert(0, str(ROOT / "myblog_backend"))
sys.path.insert(0, str(ROOT / "myblog_shared_db" / "src"))

# Same fingerprint as the read path — parity by construction, not by copy.
from app.services.lyrics_service import compute_body_fingerprint  # noqa: E402
from myblog_shared_db.llm import CliEngine, LLMJob, LLMTransientError  # noqa: E402

REGION = "ap-northeast-2"
SSM_PARAM = "/myblog/backend"
MT_MODEL = "claude.sonnet"
TRANSLATOR_VERSION = "genius-v1"          # bump on any prompt/engine change
ENGINE_CLI_MODEL = os.environ.get("GENIUS_CLAUDE_MODEL", "sonnet")
ENGINE_TIMEOUT_S = 180                    # one body; the lyrics poller needs 300 for a whole track
BATCH_PER_RUN = 20                        # annotations per non-drain firing
INTER_CALL_SLEEP_S = 1.5                  # spacing between subprocesses
MAX_BODY_CHARS = 6000                     # skip absurd outliers rather than stall the batch

# Shapes of a `claude -p` answer that is ABOUT the request instead of being the
# translation. A refusal written in Korean passes every "is this Korean" check,
# which is how 25890 was stored as a translation on the first live run.
_REFUSAL_MARKERS = (
    "이 요청은", "요청하신", "번역 요청", "무관한", "프로젝트 작업", "코드베이스",
    "죄송", "도와드릴 수", "i can't", "i cannot", "i'm unable", "as an ai",
)

PROMPT_HEADER = (
    "아래는 어떤 노래 가사 한 구절에 달린 해설이야. 이걸 한국어로 **의역**해줘 —\n"
    "축자적 직역이 아니라, 글의 정서와 핵심 의미를 자연스러운 한국어로 옮겨.\n"
    "문단 구분은 원문을 따라가고, 인용은 인용으로 남겨. 이미 한국어면 그대로 둬.\n"
    "해설 자체만 출력하고 설명이나 머리말은 붙이지 마.\n"
    "---\n"
)


class TransientEngineError(RuntimeError):
    """CLI-level failure — the row is left pending so the next run retries."""


class EngineValidationError(RuntimeError):
    """The model answered, but not usably. Retried once, then recorded failed."""


# --- secrets / db -----------------------------------------------------------

def database_url() -> str:
    url = os.environ.get("DATABASE_URL")
    if not url:
        import boto3

        ssm = boto3.client("ssm", region_name=REGION)
        url = json.loads(
            ssm.get_parameter(Name=SSM_PARAM, WithDecryption=True)["Parameter"]["Value"]
        )["DATABASE_URL"]
    return re.sub(r"^postgresql\+\w+", "postgresql", url)


def connect():
    import psycopg
    from psycopg.rows import dict_row

    # connect_timeout=30 absorbs Neon cold-start (reference-database-url-psql).
    return psycopg.connect(database_url(), connect_timeout=30, row_factory=dict_row)


# --- queue ------------------------------------------------------------------
# Only annotations whose parent track actually resolved: an `ambiguous` match may
# be the wrong song entirely, and paying for a translation of another song's
# commentary is worse than leaving it pending.
CLAIM_SQL = """
SELECT a.genius_annotation_id, a.body_source, a.body_source_lang
  FROM track_genius_annotations a
  JOIN track_genius_songs g ON g.track_id = a.track_id
 WHERE a.translation_status = 'pending'
   AND g.match_status = 'matched'
   AND btrim(coalesce(a.body_source, '')) <> ''
   AND length(a.body_source) <= %s
 ORDER BY a.genius_annotation_id
 LIMIT %s;
"""


def claim(conn, limit: int) -> list[dict]:
    with conn.cursor() as cur:
        cur.execute(CLAIM_SQL, (MAX_BODY_CHARS, limit))
        return cur.fetchall()


def mark_done(conn, annotation_id: int, body_ko: str, fingerprint: str) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE track_genius_annotations
               SET body_ko = %s,
                   body_source_fingerprint = %s,
                   translation_status = 'done',
                   translator_model = %s,
                   translator_version = %s,
                   translated_at = now(),
                   updated_at = now()
             WHERE genius_annotation_id = %s;
            """,
            (body_ko, fingerprint, MT_MODEL, TRANSLATOR_VERSION, annotation_id),
        )
    conn.commit()


def mark_failed(conn, annotation_id: int) -> None:
    """`failed` is terminal for this row; the UI renders it as "not ready" rather
    than showing the untranslated original in a surface that promised Korean."""
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE track_genius_annotations "
            "SET translation_status = 'failed', updated_at = now() "
            "WHERE genius_annotation_id = %s;",
            (annotation_id,),
        )
    conn.commit()


# --- korean guard -----------------------------------------------------------

def hangul_ratio(text: str) -> float:
    letters = [ch for ch in text if ch.isalpha()]
    if not letters:
        return 0.0
    hangul = sum(1 for ch in letters if "가" <= ch <= "힣" or "ㄱ" <= ch <= "ㅣ")
    return hangul / len(letters)


# --- engine -----------------------------------------------------------------

def _translate_once(body: str) -> str:
    claude_bin = shutil.which("claude")
    if claude_bin is None:
        raise TransientEngineError("claude CLI not on PATH")
    try:
        res = CliEngine(binary=claude_bin).run(LLMJob(
            feature="genius_translate",
            prompt=PROMPT_HEADER + body,
            model=ENGINE_CLI_MODEL,
            output_mode=None,
            timeout_s=ENGINE_TIMEOUT_S,
            # NEUTRAL cwd. Left unset, the subprocess inherits the workspace root,
            # reads CLAUDE.md, decides a song annotation is "unrelated to this
            # session's project work" and answers with that instead of a
            # translation. Observed live on annotation 25890.
            cwd=tempfile.gettempdir(),
        ))
    except LLMTransientError as e:
        raise TransientEngineError(str(e)) from None

    out = (res.result or "").strip()
    if not out:
        raise TransientEngineError("empty stdout")
    if len(out) < 8:
        raise EngineValidationError(f"suspiciously short output: {out!r}")
    # A Korean-language refusal passes a Korean-language check. The hangul ratio
    # alone let "이 요청은 이 세션의 프로젝트 작업과 무관한…" through and stored it
    # as a translation, so the meta-answer shapes are named explicitly.
    low = out.lower()
    for marker in _REFUSAL_MARKERS:
        if marker in low:
            raise EngineValidationError(f"meta-answer, not a translation: {out[:80]!r}")
    if hangul_ratio(out) < 0.15:
        raise EngineValidationError(f"output is not Korean (hangul {hangul_ratio(out):.2f})")
    return out


def translate(body: str) -> str:
    try:
        return _translate_once(body)
    except EngineValidationError as first:
        log.warning("validation failed, retrying once: %s", first)
        return _translate_once(body)


# --- run --------------------------------------------------------------------

def run_batch(conn, limit: int) -> dict:
    metrics = {"claimed": 0, "done": 0, "failed": 0, "transient": 0}
    rows = claim(conn, limit)
    metrics["claimed"] = len(rows)
    for row in rows:
        aid = row["genius_annotation_id"]
        body = row["body_source"]
        try:
            ko = translate(body)
        except TransientEngineError as e:
            # Left pending on purpose: the next run retries. Marking it failed
            # here would turn a session-budget hiccup into a permanent verdict.
            log.warning("transient on %s: %s", aid, e)
            metrics["transient"] += 1
            continue
        except EngineValidationError as e:
            log.error("giving up on %s: %s", aid, e)
            mark_failed(conn, aid)
            metrics["failed"] += 1
            continue
        # The fingerprint is of the SOURCE we translated, so a later re-fetch that
        # changes the body makes the read path withhold this Korean automatically.
        mark_done(conn, aid, ko, compute_body_fingerprint(body))
        metrics["done"] += 1
        time.sleep(INTER_CALL_SLEEP_S)
    return metrics


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--limit", type=int, default=BATCH_PER_RUN)
    ap.add_argument("--drain", action="store_true", help="keep going until the queue is empty")
    args = ap.parse_args()

    conn = connect()
    total = {"claimed": 0, "done": 0, "failed": 0, "transient": 0}
    try:
        while True:
            m = run_batch(conn, args.limit)
            for k, v in m.items():
                total[k] += v
            # Stop when a pass produced nothing: either the queue is empty, or
            # everything in it is failing transiently and hammering will not help.
            if not args.drain or m["claimed"] == 0 or m["done"] == 0:
                break
    finally:
        conn.close()
    log.info("genius-translate done: %s", total)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
