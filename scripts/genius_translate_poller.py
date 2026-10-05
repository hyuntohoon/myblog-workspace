#!/usr/bin/env python3
"""Retired Claude translation runner, replaced by explicit Chat tools.

All CLI options remain parseable for old launchd/backfill invocations, but main
returns before database access. Model dispatch also fails closed when imported.
Historical claim/publication helpers remain for regression tests only. Keep the
installed launchd job disabled. See docs/contracts/lyrics-chat.md.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
import time
from functools import lru_cache
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("genius-translate-poller")

ROOT = Path(__file__).resolve().parent.parent  # myblog-workspace/
sys.path.insert(0, str(ROOT / "myblog_backend"))
sys.path.insert(0, str(ROOT / "myblog_shared_db" / "src"))

# Same fingerprint as the read path — parity by construction, not by copy.
from app.services.lyrics_service import compute_body_fingerprint  # noqa: E402
from myblog_shared_db.llm.subscription_guard import (  # noqa: E402
    LLMSubscriptionCooldown,
    ensure_subscription_available,
)

REGION = "ap-northeast-2"
SSM_PARAM = "/myblog/backend"
MT_MODEL = "claude.sonnet"
TRANSLATOR_VERSION = "genius-v1"          # bump on any prompt/engine change
ENGINE_CLI_MODEL = os.environ.get("GENIUS_CLAUDE_MODEL", "sonnet")
ENGINE_TIMEOUT_S = 180                    # one body; the lyrics poller needs 300 for a whole track
BATCH_PER_RUN = 24                        # annotations per firing (see BATCH_SIZE)
# Annotations per `claude -p` call. One-per-call cost 18.8s each, nearly all of it
# process + model start-up; batching amortises that. Bounded by chars as well as
# count because the 2026-07-25 session lost two runs to "response stalled
# mid-stream" — 38 bodies in one call. Size the OUTPUT, not just the input.
BATCH_SIZE = 6
MAX_BATCH_CHARS = 7000
# The 03:00 Editor Buckit nightly draft runs `claude -p` on the same subscription,
# and parallel CLI use has already killed it once via the shared usage limit. A
# 60s poller spanning that window would do it again, predictably, so the poller
# stands down around it. Owner-visible: --force ignores the window.
QUIET_HOURS = (2, 4)                      # [02:00, 04:00) local
MAX_BODY_CHARS = 6000                     # skip absurd outliers rather than stall the batch


# JSON-array contract, like the lyrics poller. This is not only a batching device:
# a refusal or a meta-answer does not parse as the expected array, so the output
# shape itself rejects it. The free-text version had to detect refusals by
# keyword, which is why one was stored as a translation on the first live run.
PROMPT_HEADER = (
    "아래 항목들은 노래 가사 구절에 달린 해설이야. 각 항목을 한국어로 **의역**해줘 —\n"
    "축자적 직역이 아니라, 글의 정서와 핵심 의미를 자연스러운 한국어로 옮겨.\n"
    "문단 구분은 원문을 따라가고, 인용은 인용으로 남겨. 이미 한국어면 그대로 둬.\n"
    "출력은 오직 JSON 배열만, 설명·머리말 금지:\n"
    '[{"i":<항목 번호>,"ko":"<의역>"}]\n'
    "---\n"
)


class TransientEngineError(RuntimeError):
    """CLI-level failure — the row is left pending so the next run retries."""


class EngineValidationError(RuntimeError):
    """The model answered, but not usably. Retried once, then recorded failed."""


# --- secrets / db -----------------------------------------------------------

@lru_cache(maxsize=1)
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

def _extract_json_array(stdout: str) -> str | None:
    """First top-level [...] block. The CLI sometimes wraps prose around it."""
    depth = 0
    start = None
    for i, ch in enumerate(stdout):
        if ch == "[":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0 and start is not None:
                return stdout[start:i + 1]
    return None


_URLISH = re.compile(r"^\s*(https?://\S+\s*)+$")


def is_translatable(body: str) -> bool:
    """Is there prose here at all?

    Some annotation bodies are a bare video-embed URL. The model correctly returns
    them unchanged, and a "did it come back Korean?" check then reads that as a
    failed translation and kills the whole batch — twice, with the retry. Nothing
    is wrong; there was nothing to translate.
    """
    if _URLISH.match(body):
        return False
    letters = [ch for ch in body if ch.isalpha()]
    return len(letters) >= 12


def _translate_batch_once(bodies: list[str]) -> list[str | None]:
    """Retired dispatch: imports and historical backfills cannot invoke Claude."""
    raise TransientEngineError("Claude translation is retired; request it in Chat")


def translate_batch(bodies: list[str]) -> list[str | None]:
    """Compatibility entrypoint with no model invocation or retry."""
    return _translate_batch_once(bodies)


def _chunks(rows: list[dict]) -> list[list[dict]]:
    """Split by BOTH count and total chars — whichever bounds first."""
    out: list[list[dict]] = []
    cur: list[dict] = []
    size = 0
    for r in rows:
        n = len(r["body_source"])
        if cur and (len(cur) >= BATCH_SIZE or size + n > MAX_BATCH_CHARS):
            out.append(cur)
            cur, size = [], 0
        cur.append(r)
        size += n
    if cur:
        out.append(cur)
    return out


def _do_chunk(chunk: list[dict]) -> tuple[list[tuple[int, str, str]], list[int], bool]:
    """Translate one chunk off-thread. Returns (writes, failed_ids, transient).

    failed_ids are terminal for their rows — leaving a validation give-up as
    `pending` re-claims the identical rows on every firing, forever (observed
    live 2026-07-28: one quote-heavy batch of 6 burned two CLI calls a minute).
    """
    bodies = [r["body_source"] for r in chunk]
    try:
        kos = translate_batch(bodies)
    except TransientEngineError as e:
        log.warning("transient on batch of %d: %s", len(chunk), e)
        return [], [], True
    except EngineValidationError as e:
        log.error("giving up on batch of %d: %s", len(chunk), e)
        return [], [r["genius_annotation_id"] for r in chunk], False
    writes, failed_ids = [], []
    for r, ko in zip(chunk, kos):
        if ko is None:
            failed_ids.append(r["genius_annotation_id"])
        else:
            writes.append((r["genius_annotation_id"], ko,
                           compute_body_fingerprint(r["body_source"])))
    if failed_ids:
        log.error("giving up on %d item(s) of batch of %d", len(failed_ids), len(chunk))
    return writes, failed_ids, False


def run_batch(limit: int) -> dict:
    metrics = {"claimed": 0, "done": 0, "failed": 0, "transient": 0}
    try:
        ensure_subscription_available()
    except LLMSubscriptionCooldown as e:
        log.info("subscription cooldown — skipping queue read: %s", e)
        metrics["transient"] = 1
        return metrics
    read_conn = connect()
    try:
        rows = claim(read_conn, limit)
    finally:
        # Materialize the queue slice before any lock wait or model call. Never
        # carry a Neon session/transaction across external work.
        read_conn.close()
    metrics["claimed"] = len(rows)
    if not rows:
        return metrics

    chunks = _chunks(rows)
    # Keep domain batching independent, but issue subscription-backed calls in
    # sequence.  The shared guard also serializes these calls against the lyrics
    # and research workers running in other launchd processes.
    for chunk in chunks:
        writes, failed_ids, transient = _do_chunk(chunk)
        if transient:
            metrics["transient"] += 1
            # A subscription/CLI transient normally affects the following chunks
            # too. Stop this firing after the first one so an unclassified silent
            # failure can never fan out into four real calls before cooldown.
            break
        if failed_ids or writes:
            write_conn = connect()
            try:
                for aid in failed_ids:
                    mark_failed(write_conn, aid)
                    metrics["failed"] += 1
                for aid, ko, fp in writes:
                    mark_done(write_conn, aid, ko, fp)
                    metrics["done"] += 1
            finally:
                write_conn.close()
    return metrics


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--limit", type=int, default=BATCH_PER_RUN)
    ap.add_argument("--drain", action="store_true", help="keep going until the queue is empty")
    ap.add_argument("--force", action="store_true", help="run even inside the nightly quiet window")
    args = ap.parse_args()

    # An accidentally restored launchd plist must remain harmless after cutover.
    log.warning("Claude commentary translation is disabled; use the MyBlog Chat connection")
    return 0



if __name__ == "__main__":
    raise SystemExit(main())
