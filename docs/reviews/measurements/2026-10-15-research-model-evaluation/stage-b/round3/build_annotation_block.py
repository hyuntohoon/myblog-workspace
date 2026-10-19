#!/usr/bin/env python3
"""Render the round-3 Genius community-annotation block (ROUND.md §3b) offline.

Usage: build_annotation_block.py <rows.json> <album input .txt> > gemini-annotations.txt

<rows.json> is the read-only export written by the query in ROUND.md §3b
(one object per annotation, plus the song description and URL). Track numbers
come from the album input's Genius match list, so the block uses the same
numbering the producer already sees. No production renderer is involved.
"""
import json
import re
import sys

CAP_TOTAL = 8000      # whole block, chars (ROUND.md §3b)
CAP_BODY = 280        # one annotation body; longer bodies are cut and marked
CAP_DESC = 280        # one song description
CAP_SPEECH = 600      # a body that mentions a statement: the lead to the original is the point
SPEECH = re.compile(r"\b(interview|said|says|told|explained|tweet(ed)?|instagram|stated|revealed)\b", re.I)


def cut(text: str, cap: int) -> str:
    text = " ".join(text.split())
    return text if len(text) <= cap else text[:cap].rstrip() + " …(잘림)"


def main() -> int:
    rows = json.load(open(sys.argv[1], encoding="utf-8"))
    album = open(sys.argv[2], encoding="utf-8").read()
    numbers = {m.group(2).strip(): int(m.group(1))
               for m in re.finditer(r"^- (\d+) (.+?) → Genius", album, re.M)}
    tracks: dict[str, dict] = {}
    for r in rows:
        t = tracks.setdefault(r["title"], {"desc": r.get("description") or "", "url": r.get("genius_url") or "", "ann": []})
        if r.get("genius_annotation_id"):
            t["ann"].append(r)
    order = sorted(tracks, key=lambda title: numbers.get(title, 99))
    # Per track: every annotation that mentions a statement, then the rest by votes.
    picked = {}
    for title in order:
        ann = tracks[title]["ann"]
        speech = [a for a in ann if SPEECH.search(a["body_source"] or "")]
        rest = sorted((a for a in ann if a not in speech), key=lambda a: -a["votes_total"])
        picked[title] = speech + rest
    head = [
        "## Genius 커뮤니티 주석 (파이프라인 제공 — 조사 대상 앨범)",
        "- 성격: Genius 이용자가 쓴 주석의 원문(영어)이다. 이 앨범의 주석 중 아티스트 인증(verified) 주석은 0건이다. "
        "주석 안의 발언 인용은 커뮤니티가 옮긴 것이며, 발언자의 원문이 아니다.",
        "- 선별: 곡마다 곡 설명, 발언을 언급한 주석 전부, 나머지는 추천 수 순. 블록 전체 약 8,000자 상한이라 일부 주석은 빠졌고 긴 본문은 잘렸다(…(잘림)). "
        "빠지거나 잘린 것은 부재의 근거가 아니다.",
        "- 위치: 주석 ID는 https://genius.com/<ID> 로 열린다. 「」 안은 주석이 붙은 가사 구절이다.",
    ]
    out = "\n".join(head)
    sections = []
    for title in order:
        t = tracks[title]
        n = numbers.get(title)
        if n is None:
            # Not in the input's match list = the ambiguous match (input marks it ⚠︎); carry nothing from it.
            sections.append([[f"### {title} — Genius 매칭 모호(앨범 블록 참조), 주석 미수록"], []])
            continue
        lines = [f"### {n} {title} — 수집 주석 {len(t['ann'])}건 · {t['url']}"]
        if t["desc"]:
            lines.append(f"- 곡 설명: {cut(t['desc'], CAP_DESC)}")
        if not t["ann"]:
            lines.append("- 이 곡에는 수집된 주석이 없다.")
        sections.append([lines, picked[title]])
    # Round-robin fill so the cap does not starve the later tracks.
    budget = CAP_TOTAL - len(out) - sum(len("\n".join(s[0])) + 1 for s in sections) - 1
    progress = True
    while progress:
        progress = False
        for s in sections:
            if not s[1]:
                continue
            a = s[1][0]
            line = (f"- [{a['genius_annotation_id']}] 「{cut(a['fragment'], 60)}」 (추천 {a['votes_total']}): "
                    f"{cut(a['body_source'] or '', CAP_SPEECH if SPEECH.search(a['body_source'] or '') else CAP_BODY)}")
            if len(line) + 1 > budget:
                s[1] = []
                continue
            s[0].append(line)
            s[1].pop(0)
            budget -= len(line) + 1
            progress = True
    for lines, _ in sections:
        out += "\n" + "\n".join(lines)
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
