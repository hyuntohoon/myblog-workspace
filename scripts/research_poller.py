#!/usr/bin/env python3
"""FEAT-album-research-notes Step 3 — the $0 local research poller.

Drains `album_research(status='queued')` rows by running the album-research
prompt through **headless Claude Code** (`claude -p`), which executes on the
owner's Claude Code **subscription** — so each research run costs **$0** at
opus-4.8 quality (the 2026-06-11 bench winner). The DB writeback is done by
THIS script, not the model; the model only gets `--allowed-tools
WebSearch,WebFetch` (no Bash/Edit) so a headless run can't touch the repo.

This is a standalone operator script. It is NOT deployed anywhere and shares no
code with the dormant `researchWorkerLambda` (the paid cloud path, kept inert in
$0 mode). RFC: docs/rfcs/FEAT-album-research-notes.md (Execution backend, Step 3).

REQUIRES a Python with `psycopg` (v3) + `boto3`, and the `claude` CLI logged in
to the Max subscription. The repo's backend venv already has the Python deps:

    myblog_backend/.venv/bin/python scripts/research_poller.py --once
    myblog_backend/.venv/bin/python scripts/research_poller.py            # loop

Auth/secret model (no Anthropic key needed — $0 path):
  * `claude -p` uses the subscription login already on this machine.
  * prod `DATABASE_URL` is read from Secrets Manager `myblog/backend` with the
    owner's AWS creds (`postgresql+psycopg://` → `postgresql://`; Neon cold-start
    ⇒ connect_timeout=30).

Dedupe / single-flight (RFC "Claim gate"): a conditional UPDATE claims one
`queued`/`failed`/stale-`running` row at a time (`FOR UPDATE SKIP LOCKED`), so
two poller instances never double-run a row and a crash-stranded `running` row
(laptop sleep, `claude -p` crash) is re-claimed after 20 min. Processing is
**serial** with an inter-run sleep so a bucket-wide `research_mode='all'` flip
drains steadily instead of spiking the subscription rate limit.

Refine vs. fresh: a claimed row is a **refine** iff it still carries a prior
`result_md` (restart clears it, first-run never had one); the prior note + the
owner's `last_instruction` are then sent for an integrated update, and a failed
refine keeps the old note (never blanks the panel). Otherwise it's a fresh run.

OQ5 (poller host/schedule): start by running `--once` by hand or under `/loop`;
formalize to launchd/cron only if draining-by-hand proves annoying. Correctness
does not depend on it — queued rows simply wait until the poller runs.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path

# shared_db is read from the LOCAL checkout via src-path injection (not the git
# pin) — same pattern as lyrics_translate_poller's backend injection. Resolves
# relative to this script so it works from any checkout that carries the nested
# myblog_shared_db repo (the launchd runtime = the workspace main checkout).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "myblog_shared_db" / "src"))

from myblog_shared_db.llm import CliEngine, LLMJob, ToolPolicy  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger("research_poller")

# --- config ---------------------------------------------------------------
REGION = "ap-northeast-2"
SECRET_ID = "/myblog/backend"         # SSM SecureString param (holds DATABASE_URL)
PROMPT_VERSION = "v2"                  # must match the vendored prompt below
PROMPT_FILE = "album_research_v2.md"   # vendored beside this script (lines 1-98 of the doc)
CLAUDE_MODEL = "opus"                  # bench winner = opus 4.8
CLAUDE_TIMEOUT_S = 900                 # a run is 3-8 min; 15-min hard ceiling
STALE_RUNNING = "20 minutes"          # crash-recovery re-claim window (a run is <=~10 min)
DEFAULT_INTERVAL_S = 120              # poll cadence when no row is waiting
DEFAULT_INTER_RUN_SLEEP_S = 30       # serial spacing between runs (rate-limit guard)


# --- secrets / db ---------------------------------------------------------
def database_url() -> str:
    """Read prod DATABASE_URL from SSM Parameter Store and normalize for psycopg."""
    import boto3

    ssm = boto3.client("ssm", region_name=REGION)
    secret = json.loads(ssm.get_parameter(Name=SECRET_ID, WithDecryption=True)["Parameter"]["Value"])
    url = secret["DATABASE_URL"]
    # SQLAlchemy form `postgresql+psycopg://` -> libpq form psycopg.connect wants.
    return url.replace("postgresql+psycopg://", "postgresql://", 1)


def connect():
    import psycopg
    from psycopg.rows import dict_row

    # connect_timeout=30 absorbs Neon cold-start (reference-database-url-psql).
    return psycopg.connect(database_url(), connect_timeout=30, row_factory=dict_row)


# --- prompt assembly ------------------------------------------------------
def _prompt_path() -> str:
    import os

    return os.path.join(os.path.dirname(os.path.abspath(__file__)), PROMPT_FILE)


def load_base_prompt() -> str:
    with open(_prompt_path(), encoding="utf-8") as f:
        return f.read()


def _album_block(meta: dict) -> str:
    artists = ", ".join(meta["artists"]) or "(미상)"
    return (
        "## 앨범 (조사 대상)\n"
        f"- 아티스트: {artists}\n"
        f"- 제목: {meta['title']}\n"
        f"- 구분(album_type): {meta.get('album_type') or '(미상)'}\n"
        f"- 발매일: {meta.get('release_date') or '(미상)'}\n"
        f"- 레이블: {meta.get('label') or '(미상)'}\n"
        f"- 트랙 수: {meta.get('total_tracks') if meta.get('total_tracks') is not None else '(미상)'}\n"
        f"- Spotify ID: {meta.get('spotify_id') or '(미상)'}\n"
    )


# Pipeline addendum (RFC "Prompt vendoring"): there is no human mid-run, so the
# model must pin the release itself and emit ONLY the note markdown.
ADDENDUM = """
---
## Pipeline addendum (headless — no human in the loop)

This runs unattended; there is NO human to confirm with mid-run. Therefore:
- Workflow step 1 (disambiguate): do NOT pause to ask. Pin the exact release
  yourself from the album metadata below (artist, title, release date, label,
  Spotify id), and record any residual ambiguity inside the 앨범 식별 section
  instead of stopping.
- Your ENTIRE reply must be ONLY the research-note markdown (the Output-format
  sections above, Korean headers). No preamble, no "Here is…", no closing line.
"""

REFINE_HEADER = """
## 보강 요청 (refine)
아래는 이전에 생성된 리서치 노트다. 폐기하지 말고, 다음 지시를 반영해 **전체 노트를
업데이트**해서 반환하라(기존의 좋은 내용은 유지, 정직성 규칙 동일 — 새 주장에는 새 출처 필수).
출력은 동일하게 노트 마크다운만.

### 지시
{instruction}

### 기존 노트
{prior_note}
"""


def build_prompt(base: str, meta: dict, *, refine: bool, prior_note: str | None,
                 instruction: str | None) -> str:
    parts = [base, ADDENDUM, _album_block(meta)]
    if refine:
        parts.append(REFINE_HEADER.format(
            instruction=(instruction or "(지시 없음 — 출처 재검증 및 보강)").strip(),
            prior_note=(prior_note or "").strip(),
        ))
    return "\n".join(parts)


# --- claude -p (via shared_db CliEngine) -----------------------------------
# P4 cutover #1 (FEAT-multi-user-accounts-p4-llmengine): argv byte-parity with
# the previous inline subprocess call is pinned by shared_db
# tests/test_llm_engine.py::test_golden_argv_research_poller. No metering
# session_factory yet — this poller never wrote llm_usage; wiring pollers into
# owner-audit metering is a separate decision.
ENGINE = CliEngine()


def run_claude(prompt: str) -> dict:
    """Run headless Claude Code via CliEngine; return {result, tokens_in,
    tokens_out, search_count, model}. Raises LLMTransientError /
    LLMValidationError so the caller can mark the row failed.

    search_count: LLMResult does not surface `usage.server_tool_use`, so this
    now always records 0. The field was already documented as unreliable (the
    `claude -p` JSON aggregate often reported 0 even when the model demonstrably
    fetched — 2026-06-11); the citations inside result_md remain the real
    grounding evidence. tokens_in stays cache-inclusive (an order-of-magnitude
    audit field, not a bill — $0 on the subscription).
    """
    res = ENGINE.run(LLMJob(
        feature="research_poller",
        prompt=prompt,
        model=CLAUDE_MODEL,
        tools=ToolPolicy(allowed=("WebSearch", "WebFetch")),
        output_mode="json",
        timeout_s=CLAUDE_TIMEOUT_S,
    ))
    return {
        "result": res.result,
        "tokens_in": res.tokens_in,
        "tokens_out": res.tokens_out,
        "search_count": 0,
        "model": res.model or CLAUDE_MODEL,
    }


# --- db ops ---------------------------------------------------------------
CLAIM_SQL = f"""
UPDATE album_research SET status = 'running', started_at = now()
WHERE id = (
    SELECT id FROM album_research
    WHERE status IN ('queued', 'failed')
       OR (status = 'running' AND started_at < now() - INTERVAL '{STALE_RUNNING}')
    ORDER BY requested_at
    LIMIT 1
    FOR UPDATE SKIP LOCKED
)
RETURNING id, album_id, prompt_version, refine_count, last_instruction, result_md;
"""

ALBUM_SQL = """
SELECT a.title, a.release_date, a.label, a.spotify_id, a.album_type, a.total_tracks,
       COALESCE(
           array_agg(ar.name ORDER BY ar.name) FILTER (WHERE ar.name IS NOT NULL),
           '{}'
       ) AS artists
FROM albums a
LEFT JOIN album_artists aa ON aa.album_id = a.id
LEFT JOIN artists ar ON ar.id = aa.artist_id
WHERE a.id = %s
GROUP BY a.id;
"""


def claim_row(conn) -> dict | None:
    with conn.cursor() as cur:
        cur.execute(CLAIM_SQL)
        row = cur.fetchone()
    conn.commit()  # release the row lock; 'running' is now visible to other pollers
    return row


def album_meta(conn, album_id) -> dict:
    with conn.cursor() as cur:
        cur.execute(ALBUM_SQL, (album_id,))
        row = cur.fetchone()
    if row is None:
        raise RuntimeError(f"album {album_id} not found")
    return row


def mark_done(conn, row_id, res: dict) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE album_research
            SET status = 'done', result_md = %s, model = %s,
                tokens_in = %s, tokens_out = %s, search_count = %s,
                error = NULL, finished_at = now()
            WHERE id = %s;
            """,
            (res["result"], res["model"], res["tokens_in"], res["tokens_out"],
             res["search_count"], row_id),
        )
    conn.commit()


def mark_failed(conn, row_id, error: str) -> None:
    # Refine keeps the prior result_md (this UPDATE never touches it), so a failed
    # refine degrades to "old note + error", never an empty panel.
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE album_research SET status = 'failed', error = %s, finished_at = now() WHERE id = %s;",
            (error[:4000], row_id),
        )
    conn.commit()


# --- orchestration --------------------------------------------------------
def process_one(conn, base_prompt: str) -> bool:
    """Claim and process one row. Returns True if a row was handled, False if the
    queue was empty."""
    row = claim_row(conn)
    if row is None:
        return False

    row_id = row["id"]
    refine = bool(row["result_md"])  # restart clears result_md; first-run never had one
    kind = "refine" if refine else "research"
    if row["prompt_version"] != PROMPT_VERSION:
        log.warning("row %s prompt_version=%s but poller vendors %s — using vendored",
                    row_id, row["prompt_version"], PROMPT_VERSION)
    try:
        meta = album_meta(conn, row["album_id"])
        log.info("claimed %s [%s] album=%s — %s", row_id, kind, meta["title"], meta["artists"])
        prompt = build_prompt(
            base_prompt, meta,
            refine=refine,
            prior_note=row["result_md"],
            instruction=row["last_instruction"],
        )
        t0 = time.monotonic()
        res = run_claude(prompt)
        dt = time.monotonic() - t0
        mark_done(conn, row_id, res)
        log.info(
            "done %s in %.1fs — %d chars, tokens_in=%d tokens_out=%d web=%d model=%s",
            row_id, dt, len(res["result"]), res["tokens_in"], res["tokens_out"],
            res["search_count"], res["model"],
        )
    except Exception as e:  # noqa: BLE001 — any failure marks the row, loop continues
        conn.rollback()
        log.error("FAILED %s: %s", row_id, e)
        mark_failed(conn, row_id, str(e))
    return True


def main() -> None:
    ap = argparse.ArgumentParser(description="$0 local poller for album research notes.")
    ap.add_argument("--once", action="store_true",
                    help="drain the queue once and exit (no idle polling loop)")
    ap.add_argument("--interval", type=int, default=DEFAULT_INTERVAL_S,
                    help=f"idle poll interval seconds (default {DEFAULT_INTERVAL_S})")
    ap.add_argument("--sleep", type=int, default=DEFAULT_INTER_RUN_SLEEP_S,
                    help=f"inter-run sleep seconds, rate-limit guard (default {DEFAULT_INTER_RUN_SLEEP_S})")
    args = ap.parse_args()

    base_prompt = load_base_prompt()
    conn = connect()
    log.info("poller up (model=%s, prompt=%s, db=myblog/backend)", CLAUDE_MODEL, PROMPT_VERSION)
    try:
        while True:
            handled = process_one(conn, base_prompt)
            if handled:
                time.sleep(args.sleep)        # serial spacing between runs
                continue
            # queue empty
            if args.once:
                log.info("queue empty — exiting (--once)")
                return
            time.sleep(args.interval)
    except KeyboardInterrupt:
        log.info("interrupted — exiting")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
