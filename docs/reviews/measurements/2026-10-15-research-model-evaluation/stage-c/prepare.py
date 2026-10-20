#!/usr/bin/env python3
"""Prepare the Stage C trial inputs and manifests at dispatch (TRIAL.md §3).

Renders each album's shared input read-only from prod with stage-b/round1/render_inputs.py
(the production poller's own block renderers), writes the common run block with today's
research date, and writes one manifest per album pinning the combined prompt hash
(P6 + album input + run block, joined as the runner joins them).

Usage: python3 -I prepare.py <shared_db_src> <input dir outside the repo>
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
RENDER = HERE.parent / "stage-b" / "round1" / "render_inputs.py"
RUN_BLOCK_SRC = HERE.parent / "stage-b" / "round1" / "inputs" / "run-block.txt"
ALBUMS = {"habibti": "eb1817f0-2468-4e14-9926-a3af404b6547", "jdl": "7eb56967-085e-4b55-9427-db7dc0ebc2eb"}
P6_SHA = "ac7c63023f66ffcd2dbadda6fe4509f9651037e4aea8a084cb7630f40f26af74"


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def main() -> int:
    shared_db_src, out = sys.argv[1], Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    prompt = (HERE / "prompts" / "P6.md").read_text(encoding="utf-8")
    assert sha(prompt.encode()) == P6_SHA
    subprocess.run([sys.executable, "-I", str(RENDER), shared_db_src, str(out),
                    *(f"{i}={s}" for s, i in ALBUMS.items())], check=True)
    block = RUN_BLOCK_SRC.read_text(encoding="utf-8")
    assert block.count("조사 기준일: 2026-10-16") == 1
    (out / "run-block.txt").write_text(block.replace("2026-10-16", date.today().isoformat()), encoding="utf-8")
    record = {"date": date.today().isoformat(), "prompt_sha256": P6_SHA, "inputs": {}, "combined": {}}
    for slug in ALBUMS:
        album = (out / f"{slug}.txt").read_text(encoding="utf-8")
        run = (out / "run-block.txt").read_text(encoding="utf-8")
        combined = sha("\n\n".join([prompt, album, run]).encode())
        record["inputs"][slug] = sha(album.encode())
        record["combined"][slug] = combined
        (HERE / "manifests" / f"P6-{slug}.json").write_text(json.dumps({
            "description": f"Stage C owner-use trial (TRIAL.md §3): P6 on {slug}, one run. Claude CLI with --safe-mode.",
            "artifact_dir": "../runs",
            "shared_db_src": shared_db_src,
            "timeout_s": 1500,
            "expected_prompt_sha256": combined,
            "models": [{"id": f"cl-P6-{slug}", "provider": "claude", "model": "claude-opus-5-5",
                        "availability": "available", "reasoning_effort": "medium"}],
        }, indent=2) + "\n", encoding="utf-8")
    record["inputs"]["run-block"] = sha((out / "run-block.txt").read_bytes())
    (HERE / "inputs-record.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(record, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
