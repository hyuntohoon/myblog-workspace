#!/usr/bin/env python3
"""Tally round-4 review results per ROUND.md §6 (after comparative calibration).

Usage: python3 -I tally.py   -> prints a JSON summary used to write RESULTS.md.
Calibrated levels come from each comparative's final ```json block; a label the
comparative omits keeps its per-output level. Owner decision 2 (ROUND.md head):
D6 is judged by the Claude reviewer alone, so Astra's D6 enters neither the
agreed-FAIL list (a) nor the FAIL sum (c); it is kept in levels for the side table.
"""
from __future__ import annotations

import json
import re
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REVIEW = HERE / "review"
DIMS = ["D1", "D2", "D3", "D4", "D5", "D6"]


def last_json(text: str) -> dict:
    blocks = re.findall(r"```json\s*(\{.*?\})\s*```", text, re.S)
    return json.loads(blocks[-1])


def main() -> int:
    key = json.loads((REVIEW / "blind-key.json").read_text(encoding="utf-8"))["key"]
    out: dict = {"levels": {}, "lengths": {}, "gates": {}, "defects": {}, "tokens": {}}
    for lane in ("astra", "claude"):
        comp = REVIEW / "runs" / f"{lane}-comparative" / "output.md"
        calibrated = last_json(comp.read_text(encoding="utf-8")).get("calibrated", {}) if comp.exists() else {}
        for label, run in key.items():
            d = REVIEW / "runs" / f"{lane}-review-{label}"
            if not d.exists():
                continue
            per = last_json((d / "output.md").read_text(encoding="utf-8"))
            levels = {k: calibrated.get(label, {}).get(k, per.get(k)) for k in DIMS}
            out["levels"].setdefault(run, {})[lane] = levels
            out["gates"].setdefault(run, {})[lane] = per.get("gate_allegations", [])
            out["defects"].setdefault(run, {})[lane] = per.get("recurring_defects", {})
            usage = None
            for line in (d / "stdout.jsonl").read_text(encoding="utf-8").splitlines():
                try:
                    e = json.loads(line)
                except ValueError:
                    continue
                if e.get("type") == "turn.completed":
                    usage = e["usage"]
                if e.get("type") == "result" and isinstance(e.get("usage"), dict):
                    usage = e["usage"]
            out["tokens"][f"{lane}-{label}"] = usage
    for run in key.values():
        if run.startswith("sentinel"):
            continue
        out["lengths"][run] = len((HERE / "runs" / run / "output.md").read_text(encoding="utf-8"))
    cells: dict = {}
    for run, by in out["levels"].items():
        if run.startswith("sentinel"):
            continue
        env, prompt = run.split("-")[:2]
        c = cells.setdefault(f"{env}-{prompt}", {"fails": 0, "agreed": [], "single": [], "runs": []})
        c["runs"].append(run)
        for dim in DIMS:
            fs = [lane for lane, lv in by.items() if lv.get(dim) == "FAIL" and not (dim == "D6" and lane == "astra")]
            c["fails"] += len(fs)
            if len(fs) == 2 or (dim == "D6" and fs == ["claude"]):
                c["agreed"].append(f"{run.split('-')[-1]} {dim}")
            elif len(fs) == 1:
                c.setdefault("single", []).append(f"{run.split('-')[-1]} {dim} {fs[0]}")
    for name, c in cells.items():
        c["median_len"] = statistics.median(out["lengths"][r] for r in c["runs"])
        c["lengths"] = {r: out["lengths"][r] for r in sorted(c["runs"])}
    out["cells"] = cells
    json.dump(out, sys.stdout, ensure_ascii=False, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
