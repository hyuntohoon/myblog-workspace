#!/usr/bin/env python3
"""Redact round-4 records before push (ROUND.md §8).

The owner-collection line of the Gemini Rights catalog block (as rounds 1-3). There is
no annotation block in round 4. It is matched in plain, JSON-escaped (ensure_ascii False/True) forms. Original
hashes go to PUBLICATION-REDACTIONS.json. Then a token scan must find 0 hits.

Usage: python3 -I redact_for_publication.py <dispatched-input-dir>
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OWNER_WITH = "### 오너 컬렉션 신호: [redacted: owner bucket names] — 이미 담아둔 것이므로, 오너가 아는 맥락은 다시 설명하지 말 것."
TOKENS = ("To Listen",)


def forms(s: str) -> list[str]:
    return list(dict.fromkeys([s, json.dumps(s, ensure_ascii=False)[1:-1], json.dumps(s)[1:-1]]))


def main() -> int:
    inputs = Path(sys.argv[1])
    album = (inputs / "gemini-rights.txt").read_text(encoding="utf-8")
    owner_line = next(l for l in album.splitlines() if l.startswith("### 오너 컬렉션 신호:"))
    pairs = [(owner_line, OWNER_WITH)]
    record: dict = {"date": "2026-10-20", "replaced": {"owner_collection_line": OWNER_WITH}, "files": {}}
    for path in sorted(p for p in HERE.rglob("*") if p.is_file() and p.suffix in (".txt", ".jsonl", ".json", ".md")):
        if path.name == "PUBLICATION-REDACTIONS.json":
            continue
        raw = path.read_bytes()
        text = raw.decode("utf-8", errors="strict")
        counts = {}
        for old, new in pairs:
            for o, n in zip(forms(old), forms(new)):
                c = text.count(o)
                if c:
                    text = text.replace(o, n)
                    counts[old[:24]] = counts.get(old[:24], 0) + c
        if counts:
            path.write_text(text, encoding="utf-8")
            record["files"][str(path.relative_to(HERE))] = {"original_sha256": hashlib.sha256(raw).hexdigest(),
                                                            "occurrences": counts}
    hits = []
    probes = list(TOKENS)
    for path in HERE.rglob("*"):
        if path.is_file() and path.suffix in (".txt", ".jsonl", ".json", ".md"):
            text = path.read_text(encoding="utf-8")
            for t in probes:
                for f in forms(t):
                    if f in text:
                        hits.append((str(path.relative_to(HERE)), t[:40]))
    record["token_scan_hits_after"] = len(hits)
    (HERE / "PUBLICATION-REDACTIONS.json").write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n",
                                                      encoding="utf-8")
    print(json.dumps({"files": len(record["files"]), "hits": hits[:10]}, ensure_ascii=False))
    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main())
