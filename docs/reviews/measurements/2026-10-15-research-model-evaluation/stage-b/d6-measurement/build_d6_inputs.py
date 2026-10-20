#!/usr/bin/env python3
"""Build blind audit inputs for the D6 instrument check (CHECK.md §3).

Starts from the round-5 Claude review packets as dispatched: the published copies
in ../round5/review/inputs/ with the owner-collection line restored from the
dispatched input dir, and each restored packet must match the round-5
build-report hash. Then:

- "new" packets add the owner-adopted D6 development rules (R-a to R-c) and the
  frozen Qobuz reference, and one LEAD sentence pointing to them;
- "old" packets are the round-5 packet unchanged;
- mutant notes are P5 r3 (round-5 S04) with exactly one scripted replacement each.

Labels D01..D16 come from one secrets.SystemRandom shuffle, recorded in
review/blind-key.json, which no reviewer receives.

Usage: python3 -I build_d6_inputs.py <dispatched-input-dir>
"""
from __future__ import annotations

import hashlib
import json
import secrets
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
R5 = HERE.parent / "round5"
OUT = HERE / "review"
R5_KEY = json.loads((R5 / "review" / "blind-key.json").read_text(encoding="utf-8"))["key"]
R5_HASH = json.loads((R5 / "review" / "build-report.json").read_text(encoding="utf-8"))["input_sha256"]
REDACTED = "### 오너 컬렉션 신호: [redacted: owner bucket names] — 이미 담아둔 것이므로, 오너가 아는 맥락은 다시 설명하지 말 것."
BASE = "cl-P5-gemini-rights-r3"
WEB_SENTENCE = "You may open sources with your web tools."
NEW_SENTENCE = (WEB_SENTENCE + " For D6, also apply <D6_DEVELOPMENT_RULES> together with <D6_FROZEN_REFERENCE>, "
                "both given below.")
RULES = """These rules were adopted by the project owner for development rounds (2026-10-20). They fill the anchors' undefined terms for D6 only and do not change any other dimension.

R-a Source class. An authoritative row is a distributor, label or store credit listing with a per-track role field, or physical liner notes. Genius, Wikipedia and Discogs-format copies are secondary sources.
R-b Accessibility. <D6_FROZEN_REFERENCE> shows an authoritative row that was accessible when the note was produced. A credit claim that rests only on secondary sources while that row was accessible takes the anchors' FAIL route. Where no authoritative row was accessible, reliance on secondary sources caps D6 at BORDERLINE and is not a FAIL by itself.
R-c Narrowing. Translation or grouping that keeps every role's function and track scope is normalising (BORDERLINE at worst). Changing a role's function, narrowing its track scope, or dropping a person or role that the claim's scope covers is narrowing (FAIL route)."""

# CHECK.md §3: one peripheral, D6-level defect per mutant; each replacement must match exactly once.
MUTANTS = {
    "m1": ("9. L - Karriem Riggins, Composer, Lyricist, Drums - John Kirby, Synthesizer",
           "9. L - Karriem Riggins, Drums - John Kirby, Synthesizer"),
    "m2": ("- **메타데이터 확인률**: G 매칭 9/10, S5 크레딧 행 10/10입니다.",
           "- **메타데이터 확인률**: G 매칭 9/10, S5 크레딧 행 11/11입니다(같은 S5 판매 목록의 'Bad Habit (Sped Up)' 행 포함)."),
    "m3": ("   - Wikipedia에는 Matt Martians와 DJ Dahi의 miscellaneous production 표기가 있는데, 이는 미확인 단서입니다.\n",
           "   - Wikipedia에는 Matt Martians와 DJ Dahi의 miscellaneous production 표기가 있는데, 이는 미확인 단서입니다.\n"
           "   - Sunshine의 드럼은 Lacy 본인이 연주한 것으로 보입니다(추정).\n"),
}
# (item id, source, packet): 6 round-5 outputs + sentinel + 2x each mutant on the new packet; mutants once on the old.
ITEMS = ([(r, r, "new") for r in sorted(R5_KEY.values())]
         + [(f"{m}-{k}", m, "new") for m in MUTANTS for k in ("a", "b")]
         + [(f"{m}-old", m, "old") for m in MUTANTS])


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def main() -> int:
    album = (Path(sys.argv[1]) / "gemini-rights.txt").read_text(encoding="utf-8")
    owner_line = next(l for l in album.splitlines() if l.startswith("### 오너 컬렉션 신호:"))
    reference = (HERE / "reference" / "qobuz-gemini-rights.txt").read_text(encoding="utf-8")
    label_of = {run: label for label, run in R5_KEY.items()}
    packets = {}
    for run, label in label_of.items():
        body = (R5 / "review" / "inputs" / f"{label}.txt").read_text(encoding="utf-8").replace(REDACTED, owner_line)
        assert sha(body) == R5_HASH[label], f"{label} does not match the dispatched round-5 packet"
        packets[run] = (label, body)
    base_label, base_body = packets[BASE]
    for m, (old, new) in MUTANTS.items():
        assert base_body.count(old) == 1, m
    OUT.mkdir(exist_ok=True)
    (OUT / "inputs").mkdir(exist_ok=True)
    key_path = OUT / "blind-key.json"
    ids = [i for i, _, _ in ITEMS]
    if key_path.exists():
        key = json.loads(key_path.read_text(encoding="utf-8"))["key"]
        assert sorted(key.values()) == sorted(ids)
    else:
        shuffled = ids[:]
        secrets.SystemRandom().shuffle(shuffled)
        key = {f"D{n:02d}": i for n, i in enumerate(shuffled, 1)}
        key_path.write_text(json.dumps({"drawn_at": datetime.now(timezone.utc).isoformat(),
                                        "method": "secrets.SystemRandom().shuffle", "key": key}, indent=2) + "\n",
                            encoding="utf-8")
    spec = {i: (src, pk) for i, src, pk in ITEMS}
    report: dict = {"input_sha256": {}, "items": {}, "mutant_diffs": {m: {"old": o, "new": n} for m, (o, n) in MUTANTS.items()}}
    for label, item in key.items():
        src, packet = spec[item]
        if src in MUTANTS:
            old_label, body = base_label, base_body.replace(MUTANTS[src][0], MUTANTS[src][1])
        else:
            old_label, body = packets[src]
        assert body.count(f'id="{old_label}"') == 2
        body = body.replace(f'id="{old_label}"', f'id="{label}"')
        if packet == "new":
            assert body.count(WEB_SENTENCE) == 1 and body.count("</ANCHORS_V1>\n") == 1
            body = body.replace(WEB_SENTENCE, NEW_SENTENCE).replace(
                "</ANCHORS_V1>\n", "</ANCHORS_V1>\n\n<D6_DEVELOPMENT_RULES>\n" + RULES + "\n</D6_DEVELOPMENT_RULES>\n\n"
                + "<D6_FROZEN_REFERENCE>\n" + reference + "</D6_FROZEN_REFERENCE>\n")
        (OUT / "inputs" / f"{label}.txt").write_text(body, encoding="utf-8")
        report["input_sha256"][label] = sha(body)
        report["items"][label] = {"item": item, "source": src, "packet": packet}
    (OUT / "build-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"labels": len(key), "packets": {p: sum(v["packet"] == p for v in report["items"].values())
                                                      for p in ("new", "old")}}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
