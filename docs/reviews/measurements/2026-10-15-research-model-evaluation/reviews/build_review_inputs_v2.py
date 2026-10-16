#!/usr/bin/env python3
"""Build blind review packet v2 and per-sample audit inputs (2026-10-16).

Packet v1 (`review-packet.txt`, 7 GPT samples) stays byte-identical. v2 keeps
v1's rubric and frozen prompt and every v1 candidate block unchanged, adds the
successful Claude-lane resume outputs under their pre-assigned blind labels,
and drops only v1's "missing generators are blocked" sentence. Per-sample
inputs pair one candidate with its anonymous native web trace.

Usage: python3 -I build_review_inputs_v2.py  (paths are relative to this file)
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
V1 = HERE / "review-packet.txt"
RESUME = ROOT / "runs-claude-resume-2026-10-16"
KEY = json.loads((ROOT / "blind-key.json").read_text(encoding="utf-8"))
OUT = HERE / "v2"
TRACE_RESULT_CHARS = 6000
# Harness error strings that name the generator's tool vendor. Replaced with a
# neutral marker; the trace *structure* still differs between harnesses, so
# family-level blinding is limited and is disclosed in build-report.json.
HARNESS_REDACTIONS = (
    (re.compile(r"Claude Code is unable to fetch from (\S+)"), r"[harness: fetch refused for \1]"),
    (re.compile(r"Read more: https://support\.anthropic\.com/\S*"), "[harness: vendor help link removed]"),
)
IDENTITY = re.compile(r"claude|anthropic|opus|sonnet|haiku|gpt|openai|codex|astra", re.I)

V1_SENTENCE = " Missing generators are externally blocked; no score should be inferred."
PER_SAMPLE_LEAD = (
    "PER-SAMPLE AUDIT MODE. This dispatch contains exactly one anonymous candidate. "
    "Evaluate it independently under the rubric; do not compare it with, or rank it "
    "against, any other sample, and do not guess its producer. You may open sources "
    "with your web tools; the attached anonymous native web trace shows the generator's "
    "own actions and returned snippets and is support, not a complete record. State "
    "your audit denominators (URLs attempted/obtained, claims checked) and access limits.\n\n"
)


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def claude_trace(stdout: Path) -> list[dict]:
    uses: dict[str, dict] = {}
    order: list[str] = []
    for line in stdout.read_text(encoding="utf-8").splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        content = (event.get("message") or {}).get("content")
        if not isinstance(content, list):
            continue
        for part in content:
            if event.get("type") == "assistant" and part.get("type") == "tool_use":
                name = part.get("name")
                item = {"type": "web_search" if name == "WebSearch" else "web_fetch"}
                item.update({k: part["input"][k] for k in ("query", "url", "prompt") if k in part.get("input", {})})
                uses[part["id"]] = item
                order.append(part["id"])
            elif event.get("type") == "user" and part.get("type") == "tool_result":
                body = part.get("content")
                if isinstance(body, list):
                    body = "\n".join(x.get("text", "") for x in body if isinstance(x, dict))
                body = str(body or "")
                for pattern, repl in HARNESS_REDACTIONS:
                    body = pattern.sub(repl, body)
                if part.get("tool_use_id") in uses:
                    uses[part["tool_use_id"]].update(
                        is_error=bool(part.get("is_error")),
                        result=body[:TRACE_RESULT_CHARS],
                        result_truncated=len(body) > TRACE_RESULT_CHARS)
    return [dict(uses[i], seq=n + 1) for n, i in enumerate(order)]


def main() -> int:
    v1 = V1.read_text(encoding="utf-8")
    prefix, first = v1.split('<CANDIDATE id="', 1)
    assert V1_SENTENCE in prefix
    blocks = {m.group(1): m.group(0) for m in re.finditer(r'<CANDIDATE id="(R\d\d)">.*?</CANDIDATE>', v1, re.S)}
    OUT.mkdir(exist_ok=True)
    (OUT / "web-traces").mkdir(exist_ok=True)
    report = {"v1_packet_sha256": sha(v1), "v1_samples": sorted(blocks), "added": [], "skipped": [], "identity_hits": {}}
    for label, model in sorted(KEY.items()):
        if label in blocks or not model.startswith("claude-"):
            continue
        meta_path = RESUME / model / "metadata.json"
        if not meta_path.exists():
            report["skipped"].append({"label": label, "reason": "no resume run"})
            continue
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        note = (RESUME / model / "output.md").read_text(encoding="utf-8").strip() if meta["status"] == "success" else ""
        if not note:
            report["skipped"].append({"label": label, "reason": meta["status"]})
            continue
        hits = sorted({h.lower() for h in IDENTITY.findall(note)})
        if hits:
            report["identity_hits"][label] = hits
        blocks[label] = f'<CANDIDATE id="{label}">\n{note}\n</CANDIDATE>'
        trace = claude_trace(RESUME / model / "stdout.jsonl")
        (OUT / "web-traces" / f"{label}-web-trace.json").write_text(
            json.dumps(trace, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        report["added"].append(label)
    v2_prefix = prefix.replace(V1_SENTENCE, "")
    packet = v2_prefix + "\n\n".join(blocks[k] for k in sorted(blocks)) + "\n"
    (OUT / "review-packet-v2.txt").write_text(packet, encoding="utf-8")
    report["v2_packet_sha256"] = sha(packet)
    report["v2_samples"] = sorted(blocks)
    per_sample = {}
    for label in sorted(blocks):
        trace_path = (OUT if label in report["added"] else HERE) / "web-traces" / f"{label}-web-trace.json"
        trace = trace_path.read_text(encoding="utf-8")
        body = (PER_SAMPLE_LEAD + v2_prefix + blocks[label] +
                f'\n\n<ANONYMOUS_WEB_TRACE id="{label}">\n{trace}</ANONYMOUS_WEB_TRACE>\n')
        path = OUT / "per-sample" / f"{label}.txt"
        path.parent.mkdir(exist_ok=True)
        path.write_text(body, encoding="utf-8")
        per_sample[label] = sha(body)
    report["per_sample_input_sha256"] = per_sample
    trace_hits = {}
    for path in sorted((OUT / "web-traces").glob("*.json")):
        found = sorted({h.lower() for h in re.findall(r"claude|anthropic", path.read_text(encoding="utf-8"), re.I)})
        if found:
            trace_hits[path.name] = found
    report["trace_identity_hits_after_redaction"] = trace_hits
    report["blinding_limit"] = ("Trace structure differs by harness (Claude: WebSearch/WebFetch with a per-fetch prompt; "
                                "Codex: web_search action/results), so a reviewer can infer the producer family from a trace. "
                                "Notes themselves carry no identity strings.")
    (OUT / "build-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "per_sample_input_sha256"}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
