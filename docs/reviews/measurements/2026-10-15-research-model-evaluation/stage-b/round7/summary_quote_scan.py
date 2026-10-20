#!/usr/bin/env python3
"""Search-summary-only quote scan for round 7 (ROUND.md §6 (d), change 1 row).

Lists every quoted English passage (20-200 chars) in a note that appears in some
web_search result's summary text (after its Links line) and in no web_fetch result.
Each hit is a candidate unit; the orchestrator then reads the citing line and records
whether the passage is filed under a listed link (counted) or under the search summary
/ without quote marks (not counted). Approximate by design: paraphrase is not caught.

Usage:
  python3 -I summary_quote_scan.py --blind <review dir> S01 ... S07   # before the key is read
  python3 -I summary_quote_scan.py --runs <run dir> ...              # stdout.jsonl traces (baseline)
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

QUOTE = re.compile(r"[\"“]([A-Za-z][^\"”]{20,200})[\"”]")


def norm(s: str) -> str:
    return re.sub(r"[\s’'“”\"]+", " ", s).lower().strip()


def from_run(run: pathlib.Path) -> tuple[str, list[tuple[str, str]]]:
    tools, out = {}, []
    for line in open(run / "stdout.jsonl", encoding="utf-8"):
        o = json.loads(line)
        msg = o.get("message")
        for c in msg.get("content", []) if isinstance(msg, dict) else []:
            if not isinstance(c, dict):
                continue
            if c.get("type") == "tool_use":
                tools[c["id"]] = {"WebSearch": "web_search", "WebFetch": "web_fetch"}.get(c["name"], c["name"])
            if c.get("type") == "tool_result":
                t = c.get("content")
                if isinstance(t, list):
                    t = " ".join(x.get("text", "") for x in t if isinstance(x, dict))
                out.append((tools.get(c.get("tool_use_id"), "?"), str(t)))
    return (run / "output.md").read_text(encoding="utf-8"), out


def from_blind(review: pathlib.Path, label: str) -> tuple[str, list[tuple[str, str]]]:
    packet = (review / "inputs" / f"{label}.txt").read_text(encoding="utf-8")
    note = packet.split(f'<NOTE id="{label}">', 1)[1].split("</NOTE>", 1)[0]
    trace = json.loads((review / "web-traces" / f"{label}.json").read_text(encoding="utf-8"))
    return note, [(x["type"], x["result"] or "") for x in trace]


def scan(name: str, note: str, results: list[tuple[str, str]]) -> None:
    search = [norm(t.split("]\n", 1)[-1]) for kind, t in results if kind == "web_search"]
    fetch = [norm(t) for kind, t in results if kind == "web_fetch"]
    quotes = sorted(set(QUOTE.findall(note)))
    hits = []
    for q in quotes:
        key = norm(q)[:60]
        if any(key in s for s in search) and not any(key in f for f in fetch):
            line = next((l for l in note.splitlines() if q[:30] in l), "")
            hits.append((q, line.strip()))
    print(f"== {name}: quotes {len(quotes)}, search-summary-only {len(hits)}")
    for q, line in hits:
        print(f"  Q: {q[:100]}\n  L: {line[:300]}")


def main() -> int:
    if len(sys.argv) < 3 or sys.argv[1] not in ("--blind", "--runs"):
        print(__doc__)
        return 2
    if sys.argv[1] == "--blind":
        review = pathlib.Path(sys.argv[2])
        for label in sys.argv[3:]:
            scan(label, *from_blind(review, label))
    else:
        for run in sys.argv[2:]:
            p = pathlib.Path(run)
            scan(p.name, *from_run(p))
    return 0


if __name__ == "__main__":
    sys.exit(main())
