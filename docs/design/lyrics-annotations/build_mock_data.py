#!/usr/bin/env python3
"""Assemble real LUX data into one JSON the design mockups can render.

Three sources, joined on annotation array order (the Korean translation doc was
mechanically checked against the raw JSON's array order, so index i is the same
annotation in all three):

  lux_synced.json   our LRCLIB lyrics        -> the lines on screen
  lux_genius.json   raw Genius payload       -> fragment, votes, url
  lux_anchors.json  genius_anchor.py output  -> (start_segment, end_segment) span
  LUX_genius_ko.md  full Korean translation  -> the body a Korean reader would see
"""
import json
import os
import pathlib
import re
import sys

sys.path.insert(0, "/Users/park_hyun/myblog-workspace")
sys.path.insert(0, "/Users/park_hyun/myblog-workspace/myblog_backend")
from app.services.lyrics_service import parse_lrc as backend_parse  # noqa: E402
from tools.genius_anchor import parse_lrc as tool_parse  # noqa: E402


def viewer_lines(synced):
    """What the viewer actually renders, and the tool-index -> viewer-index map.

    genius_anchor.py drops gap segments (timestamped but blank — the stanza
    break the viewer draws as `· · ·`) and untimestamped lines; the backend
    keeps both and numbers `i` across all of them. So a span emitted by the
    tool is NOT addressable against the rendered list. Measured on 1,200 prod
    tracks: 93.5% differ in segment count, 44.2% shift at least one index
    (median 2, max 22). The map below is the correction.
    """
    segs = backend_parse(synced)
    lines = [{"text": s.text, "gap": s.text == ""} for s in segs]
    keep = [i for i, s in enumerate(segs) if s.start_ms is not None and s.text != ""]
    assert len(keep) == len(tool_parse(synced)), "tool/backend keep-set disagreement"
    return lines, keep

# The four LUX source dumps (lux_synced.json, lux_genius.json, lux_anchors.json,
# LUX_genius_ko.md) were produced by the 2026-07-25 collection session and are NOT in
# this repo — they carry lyrics. Point GENIUS_SRC at wherever they are kept.
SRC = os.environ.get("GENIUS_SRC", str(pathlib.Path(__file__).resolve().parent / "local" / "src"))
OUT = str(pathlib.Path(__file__).resolve().parent / "local" / "lux_mock_data.json")

# One dense track and one sparse one — the two ends of the design problem.
WANT = {11: "dense", 10: "sparse"}


def korean_bodies(track_title):
    """Pull the `**[n]**` blocks out of the Korean translation for one track."""
    doc = open(f"{SRC}/LUX_genius_ko.md").read()
    start = doc.find(f"### 11. {track_title}") if track_title == "La Yugular" else doc.find(f". {track_title}")
    if start < 0:
        return {}
    end = doc.find("\n### ", start + 10)
    section = doc[start : end if end > 0 else len(doc)]
    body_start = section.find("#### 줄별 주석")
    if body_start < 0:
        return {}
    section = section[body_start:]

    out = {}
    for m in re.finditer(r"\*\*\[(\d+)\]\*\*\n(.*?)(?=\n\*\*\[\d+\]\*\*|\Z)", section, re.S):
        idx = int(m.group(1)) - 1
        block = m.group(2)
        gist = re.search(r"\*\*가사\*\*\s*—\s*(.+)", block)
        quote = [
            re.sub(r"^>\s?", "", ln)
            for ln in block.split("\n")
            if ln.startswith(">") and not ln.startswith(">>")
        ]
        votes = re.search(r"득표=(-?\d+)", block)
        url = re.search(r"\[주석 출처\]\((https?://[^)]+)\)", block)
        out[idx] = {
            "gist_ko": gist.group(1).strip() if gist else "",
            "body_ko": "\n\n".join(p.strip() for p in "\n".join(quote).split("\n\n") if p.strip()),
            "votes": int(votes.group(1)) if votes else None,
            "url": url.group(1) if url else "",
        }
    return out


synced = {r["no"]: r for r in json.load(open(f"{SRC}/lux_synced.json"))}
genius = {r["no"]: r for r in json.load(open(f"{SRC}/lux_genius.json"))}
anchors = json.load(open(f"{SRC}/lux_anchors.json"))["rows"]

tracks = []
for no, kind in WANT.items():
    g, s = genius[no], synced[no]
    lines, keep = viewer_lines(s["synced"])
    ko = korean_bodies(g["title"])
    rows = [a for a in anchors if a["track_no"] == no]

    anns = []
    for a in rows:
        raw = g["annotations"][a["index"]]
        k = ko.get(a["index"], {})
        span = [keep[a["span"][0]], keep[a["span"][1]]] if a["span"] else None
        anns.append(
            {
                "index": a["index"],
                "status": a["status"],          # unique | repeated | partial | section | unmatched
                "span": span,                   # inclusive [start, end] into `lines`, 0-based
                "occurrences": a["occurrences"],
                "fragment": raw["fragment"],
                "votes": raw["votes"],
                "url": raw["url"],
                "gist_ko": k.get("gist_ko", ""),
                "body_ko": k.get("body_ko", ""),
                "body_es": raw["body"],
            }
        )

    marked = {i for a in anns if a["span"] for i in range(a["span"][0], a["span"][1] + 1)}
    tracks.append(
        {
            "no": no,
            "kind": kind,
            "title": g["title"],
            "genius_url": g["genius_url"],
            "description_es": g.get("description", ""),
            "lines": lines,
            "annotations": anns,
            "stats": {
                "lines": len(lines),
                "annotations": len(anns),
                "located": sum(1 for a in anns if a["span"]),
                "marked_lines": len(marked),
                "coverage_pct": round(100 * len(marked) / len(lines), 1),
            },
        }
    )

payload = {
    "album": {
        "title": "LUX",
        "artist": "ROSALÍA",
        "released": "2025-11-07",
        "label": "Columbia",
    },
    "album_stats": {
        "tracks_total": 15,
        "tracks_with_synced_lyrics": 13,
        "annotations_total": 115,
        "annotations_measured": 103,
        "lyric_bound": 95,
        "unique": 61,
        "partial": 10,
        "repeated": 19,
        "unmatched": 5,
        "section_markers": 8,
        "placed_pct": 74.7,
        "located_incl_repeated_pct": 94.7,
        "median_span_lines": 2,
        "line_coverage_pct": 34.1,
    },
    "tracks": tracks,
}

json.dump(payload, open(OUT, "w"), ensure_ascii=False, indent=1)
for t in tracks:
    print(f"T{t['no']:02d} {t['title']:<22} {t['kind']:<7} {t['stats']}")
    missing = [a["index"] for a in t["annotations"] if not a["body_ko"]]
    if missing:
        print(f"     !! no Korean body for annotation indexes {missing}")
print(f"\n-> {OUT}")
