#!/usr/bin/env python3
"""Redact Stage C records before push (TRIAL.md §10).

For each album input, the catalog block's owner-collection line ("### 오너 컬렉션 신호: …") is
replaced in every record, in plain and JSON-escaped forms. The bucket names in those lines are then
the scan tokens, and the scan must find 0 hits. An album with no such line contributes nothing.
The per-album "버킷에 담김" marker in the same catalog block is kept, as in Stage B rounds 1–7.
Original hashes go to PUBLICATION-REDACTIONS.json.

Usage: python3 -I redact_for_publication.py <dispatched-input-dir>
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PREFIX = "### 오너 컬렉션 신호: "
SUFFIX = " — 이미 담아둔 것이므로, 오너가 아는 맥락은 다시 설명하지 말 것."
REDACTED = PREFIX + "[redacted: owner bucket names]" + SUFFIX
SLUGS = ("habibti", "jdl")
SUFFIXES = (".txt", ".jsonl", ".json", ".md")


def forms(s: str) -> list[str]:
    return list(dict.fromkeys([s, json.dumps(s, ensure_ascii=False)[1:-1], json.dumps(s)[1:-1]]))


def files() -> list[Path]:
    return sorted(p for p in HERE.rglob("*") if p.is_file() and p.suffix in SUFFIXES
                  and p.name != "PUBLICATION-REDACTIONS.json")


def main() -> int:
    inputs = Path(sys.argv[1])
    lines, tokens = [], []
    for slug in SLUGS:
        for line in (inputs / f"{slug}.txt").read_text(encoding="utf-8").splitlines():
            if line.startswith(PREFIX):
                lines.append(line)
                names = line[len(PREFIX):].split(" — ", 1)[0]
                tokens += [n.strip() for n in names.split(" · ") if n.strip()]
    record: dict = {"replaced_with": REDACTED, "owner_lines": len(lines), "files": {}}
    for path in files():
        raw = path.read_bytes()
        text = raw.decode("utf-8")
        count = 0
        for line in lines:
            for o, n in zip(forms(line), forms(REDACTED)):
                count += text.count(o)
                text = text.replace(o, n)
        if count:
            path.write_text(text, encoding="utf-8")
            record["files"][str(path.relative_to(HERE))] = {"original_sha256": hashlib.sha256(raw).hexdigest(),
                                                            "occurrences": count}
    hits = [(str(p.relative_to(HERE)), t) for p in files() for t in set(tokens)
            for f in forms(t) if f in p.read_text(encoding="utf-8")]
    record["token_scan_hits_after"] = len(hits)
    (HERE / "PUBLICATION-REDACTIONS.json").write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n",
                                                      encoding="utf-8")
    print(json.dumps({"owner_lines": len(lines), "files": len(record["files"]), "hits": hits[:10]},
                     ensure_ascii=False))
    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main())
