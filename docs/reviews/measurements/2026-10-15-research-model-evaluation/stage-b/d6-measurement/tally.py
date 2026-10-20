#!/usr/bin/env python3
"""Tally the D6 instrument check per CHECK.md §5. Per-output levels only; there is no comparative.

Usage: python3 -I tally.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REVIEW = HERE / "review"


def last_json(text: str) -> dict:
    blocks = re.findall(r"```json\s*(\{.*?\})\s*```", text, re.S)
    return json.loads(blocks[-1]) if blocks else {}


def main() -> int:
    items = json.loads((REVIEW / "build-report.json").read_text(encoding="utf-8"))["items"]
    rows = {}
    for label, spec in sorted(items.items()):
        out = REVIEW / "runs" / f"claude-review-{label}" / "output.md"
        meta = REVIEW / "runs" / f"claude-review-{label}" / "metadata.json"
        status = json.loads(meta.read_text(encoding="utf-8"))["status"] if meta.exists() else "missing"
        parsed = last_json(out.read_text(encoding="utf-8")) if out.exists() else {}
        rows[label] = dict(spec, status=status, D6=parsed.get("D6"),
                           levels={k: parsed.get(k) for k in ("D1", "D2", "D3", "D4", "D5", "D6")},
                           gates=parsed.get("gate_allegations", []))
    mutants = {}
    for m in ("m1", "m2", "m3"):
        new = [r for r in rows.values() if r["source"] == m and r["packet"] == "new"]
        old = [r for r in rows.values() if r["source"] == m and r["packet"] == "old"]
        fails = sum(r["D6"] == "FAIL" for r in new)
        mutants[m] = {"new_D6": [r["D6"] for r in new], "old_D6": [r["D6"] for r in old],
                      "new_gates": [r["gates"] for r in new],
                      # §5: detection is a D6 FAIL (or G4/G7 on the planted spot, checked by hand in RESULTS).
                      "reading": "detected" if fails == 2 else "unstable" if fails == 1 else "missed"}
    base = next(r for r in rows.values() if r["item"] == "cl-P5-gemini-rights-r3")
    out = {"rows": rows, "mutants": mutants, "negative_control_D6": base["D6"],
           "usable": all(v["reading"] == "detected" for v in mutants.values()) and base["D6"] != "FAIL"}
    (REVIEW / "tally.json").write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"mutants": {m: (v["reading"], v["new_D6"], v["old_D6"]) for m, v in mutants.items()},
                      "negative_control_D6": base["D6"], "usable": out["usable"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
