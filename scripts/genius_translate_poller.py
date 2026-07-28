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
from concurrent.futures import ThreadPoolExecutor
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
BATCH_PER_RUN = 24                        # annotations per firing (see BATCH_SIZE)
# Annotations per `claude -p` call. One-per-call cost 18.8s each, nearly all of it
# process + model start-up; batching amortises that. Bounded by chars as well as
# count because the 2026-07-25 session lost two runs to "response stalled
# mid-stream" — 38 bodies in one call. Size the OUTPUT, not just the input.
BATCH_SIZE = 6
MAX_BATCH_CHARS = 7000
PARALLEL = int(os.environ.get("GENIUS_TRANSLATE_PARALLEL", "5"))
# The 03:00 Editor Buckit nightly draft runs `claude -p` on the same subscription,
# and parallel CLI use has already killed it once via the shared usage limit. A
# 60s poller spanning that window would do it again, predictably, so the poller
# stands down around it. Owner-visible: --force ignores the window.
QUIET_HOURS = (2, 4)                      # [02:00, 04:00) local
INTER_CALL_SLEEP_S = 1.5                  # spacing between subprocesses
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


def _translate_batch_once(bodies: list[str]) -> list[str]:
    """One `claude -p` call over a batch; returns translations in input order."""
    claude_bin = shutil.which("claude")
    if claude_bin is None:
        raise TransientEngineError("claude CLI not on PATH")
    prompt = PROMPT_HEADER + "\n\n".join(
        f"[{n}]\n{b}" for n, b in enumerate(bodies, 1)
    )
    try:
        res = CliEngine(binary=claude_bin).run(LLMJob(
            feature="genius_translate",
            prompt=prompt,
            model=ENGINE_CLI_MODEL,
            output_mode=None,
            timeout_s=ENGINE_TIMEOUT_S,
            # NEUTRAL cwd. Left unset the subprocess inherits the workspace root,
            # reads CLAUDE.md, and answers that a song annotation is unrelated to
            # this project instead of translating it. Observed live on 25890.
            cwd=tempfile.gettempdir(),
        ))
    except LLMTransientError as e:
        raise TransientEngineError(str(e)) from None

    stdout = (res.result or "").strip()
    if not stdout:
        raise TransientEngineError("empty stdout")
    head = stdout[:200]
    raw = _extract_json_array(stdout)
    if raw is None:
        # A refusal or meta-answer lands here — it is not an array, so the output
        # CONTRACT rejects it. No keyword sniffing needed.
        raise EngineValidationError(f"no JSON array in output: {head}")
    try:
        items = json.loads(raw)
    except json.JSONDecodeError as e:
        raise EngineValidationError(f"bad JSON ({e}): {head}") from None
    if not isinstance(items, list) or len(items) != len(bodies):
        got = len(items) if isinstance(items, list) else type(items).__name__
        raise EngineValidationError(f"item count {got} != {len(bodies)}: {head}")
    by_n: dict[int, str] = {}
    for it in items:
        if not (isinstance(it, dict) and isinstance(it.get("i"), int)
                and isinstance(it.get("ko"), str)):
            raise EngineValidationError(f"bad item shape {it!r:.80}: {head}")
        by_n[it["i"]] = it["ko"]
    if set(by_n) != set(range(1, len(bodies) + 1)):
        raise EngineValidationError(f"index set != 1..{len(bodies)}: {head}")
    out = [by_n[n].strip() for n in range(1, len(bodies) + 1)]
    for ko in out:
        if len(ko) < 4:
            raise EngineValidationError(f"suspiciously short item: {ko!r}")
        # The array contract rejects a refusal by SHAPE, but it cannot notice an
        # item that parsed fine and simply was not translated. Lenient threshold:
        # a real translation of a quote-heavy annotation still clears it.
        if hangul_ratio(ko) < 0.15:
            raise EngineValidationError(f"item is not Korean: {ko[:60]!r}")
    return out


def translate_batch(bodies: list[str]) -> list[str]:
    try:
        return _translate_batch_once(bodies)
    except EngineValidationError as first:
        log.warning("batch validation failed, retrying once: %s", first)
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


def _do_chunk(chunk: list[dict]) -> tuple[list[tuple[int, str, str]], str | None]:
    """Translate one chunk off-thread. Returns (writes, failure_kind)."""
    bodies = [r["body_source"] for r in chunk]
    try:
        kos = translate_batch(bodies)
    except TransientEngineError as e:
        log.warning("transient on batch of %d: %s", len(chunk), e)
        return [], "transient"
    except EngineValidationError as e:
        log.error("giving up on batch of %d: %s", len(chunk), e)
        return [], "failed"
    return [
        (r["genius_annotation_id"], ko, compute_body_fingerprint(r["body_source"]))
        for r, ko in zip(chunk, kos)
    ], None


def run_batch(conn, limit: int) -> dict:
    metrics = {"claimed": 0, "done": 0, "failed": 0, "transient": 0}
    rows = claim(conn, limit)
    metrics["claimed"] = len(rows)
    if not rows:
        return metrics

    chunks = _chunks(rows)
    # Threads, not processes: each worker just waits on a subprocess. The DB is
    # touched only back on this thread, so there is no shared-session hazard.
    with ThreadPoolExecutor(max_workers=max(1, PARALLEL)) as pool:
        for writes, failure in pool.map(_do_chunk, chunks):
            if failure == "transient":
                metrics["transient"] += 1
                continue
            if failure == "failed":
                metrics["failed"] += 1
                continue
            for aid, ko, fp in writes:
                mark_done(conn, aid, ko, fp)
                metrics["done"] += 1
    return metrics


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--limit", type=int, default=BATCH_PER_RUN)
    ap.add_argument("--drain", action="store_true", help="keep going until the queue is empty")
    ap.add_argument("--force", action="store_true", help="run even inside the nightly quiet window")
    args = ap.parse_args()

    hour = time.localtime().tm_hour
    if QUIET_HOURS[0] <= hour < QUIET_HOURS[1] and not args.force:
        log.info("inside the %02d:00-%02d:00 nightly window — standing down", *QUIET_HOURS)
        return 0

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
