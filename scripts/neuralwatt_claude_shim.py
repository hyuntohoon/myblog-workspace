#!/usr/bin/env python3
"""CHORE-neuralwatt-credit-burn — claude-CLI-compatible shim → NeuralWatt glm-5.2.

genre_heal_poller injects a wrapper named `claude` (this file, run under the
worker venv python) at the front of PATH for the backfill subprocess, so the
S3 LLM stage in myblog_shared_db/scripts/backfill_genres.py (CliEngine, argv
`claude -p --output-format text`, prompt on stdin) dispatches to NeuralWatt
instead of the local Claude Code CLI. Nothing in shared_db changes; the argv
contract this shim honors is pinned by shared_db tests/test_llm_engine.py.

Contract: stdin = prompt, stdout = completion text ONLY, exit 0 on success.
Anything the shim cannot serve — unsupported flags (--allowed-tools /
--output-format json / --model), missing NEURALWATT_API_KEY, API error or
timeout — falls back to running the REAL `claude` binary found further down
PATH with the identical argv/stdin, so the nightly cannot break because the
prepaid credit ran out. The fallback and its reason are logged.

Key: NEURALWATT_API_KEY from the environment (the poller supplies it under
launchd). Never logged. Uses stdlib urllib, not the `openai` package — the
worker venv (the poller's interpreter) does not carry it and a nightly must
not depend on an unrecorded venv install; the call is still a plain
OpenAI-compatible chat.completions POST against base_url, no proxy.

Usage/cost audit (owner requirement): every API call appends one JSON line —
tokens, $ estimate at glm-5.2 list price, cumulative spend — to
~/Library/Logs/myblog-neuralwatt-usage.jsonl (override: NEURALWATT_USAGE_LOG).
"""
from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

log = logging.getLogger("neuralwatt-shim")

BASE_URL = os.environ.get("NEURALWATT_BASE_URL", "https://api.neuralwatt.com/v1")
MODEL = os.environ.get("NEURALWATT_MODEL", "glm-5.2")  # owner: glm-5.2 only
TIMEOUT_S = int(os.environ.get("NEURALWATT_TIMEOUT_S", "840"))  # < CliEngine's 900
USAGE_LOG = Path(
    os.environ.get(
        "NEURALWATT_USAGE_LOG",
        str(Path.home() / "Library" / "Logs" / "myblog-neuralwatt-usage.jsonl"),
    )
)
# glm-5.2 list price (GET /v1/models, 2026-07-20); cached-input discount not
# modeled — estimates are an upper bound.
PRICE_IN_PER_M = 1.45
PRICE_OUT_PER_M = 4.50

# Flags whose presence means the caller wants real Claude Code behavior
# (tools, JSON envelope, a specific Anthropic model) — never emulate those.
UNSUPPORTED_FLAGS = {"--allowed-tools", "--disallowed-tools", "--model", "--setting-sources"}


def _real_claude() -> str | None:
    """The genuine claude binary: skip the shim's own wrapper dir on PATH."""
    explicit = os.environ.get("NEURALWATT_REAL_CLAUDE")
    if explicit and Path(explicit).exists():
        return explicit
    shim_dir = os.environ.get("NEURALWATT_SHIM_DIR", "")
    entries = [p for p in os.environ.get("PATH", "").split(os.pathsep) if p and p != shim_dir]
    return shutil.which("claude", path=os.pathsep.join(entries))


def _fallback(argv: list[str], prompt: str, reason: str) -> int:
    log.warning("neuralwatt shim falling back to real claude: %s", reason)
    _append_usage({"source": "fallback", "reason": reason, "tokens_in": 0, "tokens_out": 0,
                   "cost_usd": 0.0})
    real = _real_claude()
    if real is None:
        log.error("no real claude binary on PATH — cannot fall back")
        return 1
    proc = subprocess.run([real, *argv], input=prompt, capture_output=True, text=True,
                          timeout=TIMEOUT_S + 60)
    sys.stdout.write(proc.stdout)
    sys.stderr.write(proc.stderr)
    return proc.returncode


def _append_usage(entry: dict) -> None:
    try:
        cum = 0.0
        if USAGE_LOG.exists():
            lines = USAGE_LOG.read_text().strip().splitlines()
            if lines:
                cum = json.loads(lines[-1]).get("cum_cost_usd", 0.0)
        entry = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "model": MODEL, **entry,
                 "cum_cost_usd": round(cum + entry.get("cost_usd", 0.0), 6)}
        USAGE_LOG.parent.mkdir(parents=True, exist_ok=True)
        with USAGE_LOG.open("a") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:  # audit must never break the pipeline
        log.exception("usage log append failed (non-blocking)")


def _neuralwatt_complete(prompt: str, api_key: str) -> tuple[str, dict]:
    """One chat.completions call. Returns (text, usage). Raises on failure."""
    body = json.dumps({
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
    }).encode()
    req = urllib.request.Request(
        f"{BASE_URL}/chat/completions",
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT_S) as r:
        data = json.load(r)
    text = (data["choices"][0]["message"].get("content") or "").strip()
    if not text:
        raise ValueError("empty completion content")
    return text, data.get("usage") or {}


def main() -> int:
    logging.basicConfig(level=logging.INFO, stream=sys.stderr,
                        format="%(asctime)s %(levelname)s %(name)s %(message)s")
    argv = sys.argv[1:]
    prompt = sys.stdin.read()

    if "-p" not in argv or any(f in argv for f in UNSUPPORTED_FLAGS):
        return _fallback(argv, prompt, f"unsupported argv: {argv}")
    api_key = os.environ.get("NEURALWATT_API_KEY")
    if not api_key:
        return _fallback(argv, prompt, "NEURALWATT_API_KEY not set")

    try:
        text, usage = _neuralwatt_complete(prompt, api_key)
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError,
            KeyError, json.JSONDecodeError, OSError) as e:
        return _fallback(argv, prompt, f"api call failed: {e}")

    tokens_in = usage.get("prompt_tokens") or 0
    tokens_out = usage.get("completion_tokens") or 0
    cost = tokens_in * PRICE_IN_PER_M / 1e6 + tokens_out * PRICE_OUT_PER_M / 1e6
    _append_usage({"source": "api", "tokens_in": tokens_in, "tokens_out": tokens_out,
                   "cost_usd": round(cost, 6)})
    log.info("neuralwatt %s: %d in / %d out tokens, ~$%.4f", MODEL, tokens_in, tokens_out, cost)
    sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
