#!/usr/bin/env python3
"""FEAT-genre-autoheal — local on-demand genre-heal poller.

Drains the genre_backfill_requests queue (filled by the /profile 분석 버킷
"장르 채우기" button) and runs the EXISTING genre pipeline on demand:
    backfill_genres.py --incremental --label --execute   (S1 mapping → S2 iTunes → S3 LLM)
— the SAME pipeline as the daily 04:00 launchd, just triggered by the web button.

Mirrors research_poller: launchd fires it `--once` every 30 min; it claims any pending
request (single-flight via FOR UPDATE SKIP LOCKED + the claimed_at gate), stamps
claimed_at, runs the backfill, stamps finished_at, exits. The S3 LLM (`claude -p`) runs
HERE on the owner's Max subscription — never in the cloud (the backend endpoint only
enqueues, rule #9-style). With no pending request it exits in milliseconds.

Env: DATABASE_URL (else resolves myblog/music via the aws CLI, like backfill_genres.py);
Spotify creds + `claude` on PATH are needed by the backfill subprocess itself.

Usage:  python scripts/genre_heal_poller.py            # claim + run one pending request
"""
from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import psycopg

log = logging.getLogger("genre-heal-poller")

ROOT = Path(__file__).resolve().parent.parent  # myblog-workspace/
BACKFILL = ROOT / "myblog_shared_db" / "scripts" / "backfill_genres.py"
PY = ROOT / "myblog_worker" / ".venv" / "bin" / "python"
NW_SHIM = Path(__file__).resolve().parent / "neuralwatt_claude_shim.py"


def _neuralwatt_env() -> dict | None:
    """CHORE-neuralwatt-credit-burn: opt-in (GENRE_HEAL_LLM=neuralwatt) env for
    the backfill subprocess that puts a `claude`-named wrapper around
    neuralwatt_claude_shim.py at the front of PATH, so the S3 LLM stage
    dispatches to NeuralWatt glm-5.2 instead of the local Claude CLI (removes
    the shared Anthropic usage-limit collision with the 03:00 nightlies).
    Returns None (= inherit env unchanged, claude -p as before) when the flag
    is off or no key is reachable; the shim itself also falls back to the real
    binary on any API failure, so this path can only degrade to status quo."""
    if os.environ.get("GENRE_HEAL_LLM") != "neuralwatt":
        return None
    env = dict(os.environ)
    if not env.get("NEURALWATT_API_KEY"):
        # launchd env has no .zshrc — pull the key from an interactive zsh,
        # delimited so rc-file chatter on stdout can't pollute it.
        try:
            out = subprocess.run(
                ["zsh", "-ic", 'print -r -- "__NW__${NEURALWATT_API_KEY}__NW__"'],
                capture_output=True, text=True, timeout=15,
            ).stdout
            m = re.search(r"__NW__(.*?)__NW__", out, re.DOTALL)
            key = (m.group(1).strip() if m else "")
        except (subprocess.TimeoutExpired, OSError):
            key = ""
        if not key:
            log.warning("GENRE_HEAL_LLM=neuralwatt but no NEURALWATT_API_KEY — claude -p path")
            return None
        env["NEURALWATT_API_KEY"] = key
    shim_dir = Path(tempfile.mkdtemp(prefix="myblog-nw-shim-"))
    wrapper = shim_dir / "claude"
    wrapper.write_text(f'#!/bin/sh\nexec "{PY}" "{NW_SHIM}" "$@"\n')
    wrapper.chmod(0o755)
    env["PATH"] = f"{shim_dir}{os.pathsep}{env.get('PATH', '')}"
    env["NEURALWATT_SHIM_DIR"] = str(shim_dir)
    log.info("S3 LLM stage routed to NeuralWatt (shim dir %s)", shim_dir)
    return env


def _db_url() -> str:
    url = os.environ.get("DATABASE_URL")
    if not url:
        out = subprocess.run(
            ["aws", "ssm", "get-parameter", "--name", "/myblog/music", "--with-decryption",
             "--query", "Parameter.Value", "--output", "text"],
            capture_output=True, text=True, check=True,
        ).stdout
        url = json.loads(out)["DATABASE_URL"]
    # psycopg.connect wants a libpq URI, not a SQLAlchemy +driver URL
    return re.sub(r"postgresql\+\w+", "postgresql", url)


def _run_backfill() -> int:
    """Run the existing genre pipeline over the marker-less (un-classified) catalog."""
    cmd = [str(PY), str(BACKFILL), "--incremental", "--label", "--execute"]
    env = _neuralwatt_env()
    log.info("running: %s (LLM=%s)", " ".join(cmd), "neuralwatt" if env else "claude-cli")
    return subprocess.run(cmd, cwd=str(BACKFILL.parent), env=env).returncode


def run_once() -> int:
    url = _db_url()
    with psycopg.connect(url) as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT id FROM genre_backfill_requests "
            "WHERE claimed_at IS NULL ORDER BY requested_at "
            "LIMIT 1 FOR UPDATE SKIP LOCKED"
        )
        row = cur.fetchone()
        if not row:
            log.info("no pending genre-backfill request")
            return 0
        req_id = row[0]
        cur.execute(
            "UPDATE genre_backfill_requests SET claimed_at = now() WHERE id = %s",
            (req_id,),
        )
        conn.commit()

    log.info("claimed request #%s — running backfill --incremental --label --execute", req_id)
    rc = _run_backfill()

    with psycopg.connect(url) as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE genre_backfill_requests SET finished_at = now() WHERE id = %s",
            (req_id,),
        )
        conn.commit()
    log.info("request #%s done (backfill rc=%d)", req_id, rc)
    return rc


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    if not BACKFILL.exists():
        log.error("backfill not found: %s", BACKFILL)
        return 2
    return run_once()


if __name__ == "__main__":
    sys.exit(main())
