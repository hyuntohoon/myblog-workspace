#!/usr/bin/env python3
"""Anchor Genius annotations onto our LRCLIB lyric segments.

The problem this solves. Our lyrics come from LRCLIB as timestamped LRC, which breaks
lines where the vocal breathes. Genius breaks lines where the *sentence* ends. So the
same passage looks different on the two sides:

    Genius   "En el primero, sexo, violencia y llantas"
    our LRC  "sexo violencia y llantas"

Comparing line-to-line therefore fails on most annotations (measured: 33% located).
Instead we drop line boundaries entirely: concatenate every LRC segment into one
normalized string while remembering which segment each character came from, find the
Genius fragment as a plain substring, then map the matched character span back to a
``(start_segment, end_segment)`` range. A fragment covering three of our segments simply
resolves to three. Measured on ROSALIA's *LUX* (13 tracks with synced lyrics, 103
annotations): **74.7% resolve to a single span, 4.9% unmatched**.

Anchoring is deliberately a PURE FUNCTION over the current lyric text, never stored.
Storing offsets would silently rot the first time ``lyrics_reassessment`` re-matches a
track against a different LRCLIB upload; recomputing costs microseconds and self-heals.
It also means the annotation store does not depend on lyrics existing at all — a track
with no lyrics yields an empty anchor list rather than an error, which is what lets the
annotation feature ship independently of the lyrics viewer.

CLI (batch measurement, used by the scheduled multi-album regression):

    python3 tools/genius_anchor.py --album-id <uuid> [--json out.json]
    python3 tools/genius_anchor.py --self-test
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

# A Genius fragment that is only a structural marker — "[Verso 1]", "[Outro Instrumental]".
# These annotate a *section*, not a line, and LRC never carries them, so they are counted
# separately instead of being reported as failures.
_SECTION_RE = re.compile(r"^\s*\[[^\]]{1,40}\]\s*$")

_LRC_LINE_RE = re.compile(r"^\s*\[(\d+):(\d+)(?:[.:](\d+))?\]\s*(.*)$")

# Kept deliberately wide: Latin, Cyrillic, Arabic, Kana/Han, Hangul. LUX alone spans at
# least 11 languages, so a Latin-only filter would silently drop whole tracks.
_KEEP_RE = re.compile(r"[^0-9a-zЀ-ӿ؀-ۿ぀-ヿ一-鿿가-힯 ]")


def normalize(text: str) -> str:
    """Fold to a comparison form: strip accents/case/punctuation, collapse whitespace.

    Accent stripping matters — LRCLIB uploads are crowd-typed and inconsistent about
    diacritics ("De Madruga" vs "De Madrugá") while Genius is usually correct.
    """
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return " ".join(_KEEP_RE.sub(" ", text.lower()).split())


def parse_lrc(lyric_synced: str) -> List[str]:
    """Timestamped LRC -> ordered segment texts, blanks dropped.

    Mirrors what ``lyrics_service.normalize_lyrics`` renders, which is the text the
    viewer actually shows. Anchoring against ``lyric_plain`` instead would measure text
    the user never sees.
    """
    segments: List[str] = []
    for line in (lyric_synced or "").split("\n"):
        match = _LRC_LINE_RE.match(line)
        if match and match.group(4).strip():
            segments.append(match.group(4).strip())
    return segments


@dataclass
class _Haystack:
    text: str
    owner: List[int]  # owner[i] = index of the segment character i came from


def _build_haystack(segments: Sequence[str]) -> _Haystack:
    parts: List[str] = []
    owner: List[int] = []
    for idx, segment in enumerate(segments):
        norm = normalize(segment)
        if not norm:
            continue
        if parts:                      # single space joins segments; attribute it forward
            parts.append(" ")
            owner.append(idx)
        parts.append(norm)
        owner.extend([idx] * len(norm))
    return _Haystack("".join(parts), owner)


@dataclass
class Anchor:
    """Where one annotation lands. ``span`` is None when it could not be placed."""

    index: int
    status: str                                   # unique | repeated | partial | section | unmatched
    span: Optional[Tuple[int, int]] = None        # inclusive segment range
    occurrences: int = 0
    matched_chars: int = 0
    fragment: str = ""

    @property
    def placed(self) -> bool:
        return self.status in ("unique", "partial")


def anchor_fragments(segments: Sequence[str], fragments: Iterable[str]) -> List[Anchor]:
    """Locate each Genius fragment inside our LRC segments.

    Statuses:
      ``unique``    exactly one occurrence — safe to render inline on that span
      ``repeated``  several occurrences (a chorus) — render on the first, note the repeat
      ``partial``   only the fragment's head matched; the span is approximate
      ``section``   a structural marker, not a lyric line
      ``unmatched`` genuinely absent from our text

    Returns one Anchor per input fragment, in input order. An empty ``segments`` yields
    all-``unmatched`` rather than raising — that is the no-lyrics case, and callers rely
    on it degrading quietly.
    """
    hay = _build_haystack(segments)
    results: List[Anchor] = []

    for i, raw in enumerate(fragments):
        raw = raw or ""
        if _SECTION_RE.match(raw.strip()):
            results.append(Anchor(i, "section", fragment=raw))
            continue

        needle = normalize(" ".join(raw.split("\n")))
        if not needle or not hay.text:
            results.append(Anchor(i, "unmatched", fragment=raw))
            continue

        starts = [m.start() for m in re.finditer(re.escape(needle), hay.text)]
        if starts:
            end = min(starts[0] + len(needle) - 1, len(hay.owner) - 1)
            results.append(Anchor(
                i,
                "unique" if len(starts) == 1 else "repeated",
                span=(hay.owner[starts[0]], hay.owner[end]),
                occurrences=len(starts),
                matched_chars=len(needle),
                fragment=raw,
            ))
            continue

        # Head-of-fragment fallback. Genius sometimes carries an ad-lib or a trailing
        # word our upload omits ("...yo siempre lo doy, uh-uh"), which breaks the whole
        # -fragment match while the opening still pins the location unambiguously.
        words = needle.split()
        placed = None
        for width in (8, 6, 4):
            if len(words) < width:
                continue
            head = " ".join(words[:width])
            hits = [m.start() for m in re.finditer(re.escape(head), hay.text)]
            if hits:
                end = min(hits[0] + len(head) - 1, len(hay.owner) - 1)
                placed = Anchor(
                    i,
                    "partial" if len(hits) == 1 else "repeated",
                    span=(hay.owner[hits[0]], hay.owner[end]),
                    occurrences=len(hits),
                    matched_chars=len(head),
                    fragment=raw,
                )
                break
        results.append(placed or Anchor(i, "unmatched", fragment=raw))

    return results


@dataclass
class Coverage:
    total: int = 0
    counts: Dict[str, int] = field(default_factory=dict)

    @property
    def lyric_bound(self) -> int:
        """Annotations that target a lyric line — the honest denominator."""
        return self.total - self.counts.get("section", 0)

    @property
    def placed_rate(self) -> float:
        n = self.lyric_bound
        return 0.0 if not n else (self.counts.get("unique", 0) + self.counts.get("partial", 0)) / n

    @property
    def any_rate(self) -> float:
        n = self.lyric_bound
        return 0.0 if not n else (n - self.counts.get("unmatched", 0)) / n


def summarize(anchors: Sequence[Anchor]) -> Coverage:
    cov = Coverage(total=len(anchors))
    for a in anchors:
        cov.counts[a.status] = cov.counts.get(a.status, 0) + 1
    return cov


# --------------------------------------------------------------------------- self-test

_SELF_TEST_SEGMENTS = [
    "Quién pudiera vivir",
    "Entre los dos",
    "En el primero,",
    "sexo, violencia y llantas",
    "Deportes de sangre",
    "Quién pudiera vivir",
]

_SELF_TEST_CASES = [
    # (fragment, expected status) — the line-splitting case this module exists for
    ("En el primero, sexo, violencia y llantas", "unique"),
    ("Quién pudiera vivir", "repeated"),
    ("[Verso 1]", "section"),
    ("Esta línea no existe en ninguna parte", "unmatched"),
]


def _self_test() -> int:
    anchors = anchor_fragments(_SELF_TEST_SEGMENTS, [f for f, _ in _SELF_TEST_CASES])
    failures = 0
    for anchor, (fragment, expected) in zip(anchors, _SELF_TEST_CASES):
        ok = anchor.status == expected
        failures += (not ok)
        print(f"  [{'ok ' if ok else 'FAIL'}] {expected:9} <- {fragment[:46]!r}"
              f"{'' if ok else f'  (got {anchor.status})'}")
    spanning = anchors[0]
    if spanning.span != (2, 3):
        print(f"  [FAIL] cross-segment span expected (2, 3), got {spanning.span}")
        failures += 1
    else:
        print("  [ok ] fragment spanning two LRC segments resolved to (2, 3)")
    print("self-test:", "PASS" if not failures else f"{failures} FAILURE(S)")
    return 1 if failures else 0


# --------------------------------------------------------------------------------- CLI

_ALBUM_SQL = """
    SELECT t.track_no, t.title, tl.lyric_synced
      FROM tracks t
      JOIN track_lyrics tl ON tl.track_id = t.id
     WHERE t.album_id = %(album_id)s
       AND tl.lyric_synced IS NOT NULL
     ORDER BY t.track_no
"""


def _load_album_segments(album_id: str) -> Dict[int, List[str]]:
    """Read-only. Same DATABASE_URL convention as the sibling lyrics tools:

        export DATABASE_URL='postgresql+psycopg://...'   # prod, from SSM /myblog/backend

    The session is opened, drained and closed before any downstream work — nothing here
    holds a Neon connection across a loop.
    """
    import os

    from sqlalchemy import create_engine, text  # lazy: --self-test needs no driver

    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise SystemExit("DATABASE_URL not set (SSM /myblog/backend)")

    engine = create_engine(db_url, future=True)
    try:
        with engine.connect() as conn:
            rows = conn.execute(
                text(_ALBUM_SQL.replace("%(album_id)s", ":album_id")),
                {"album_id": album_id},
            ).fetchall()
    finally:
        engine.dispose()
    return {row[0]: parse_lrc(row[2]) for row in rows}


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--self-test", action="store_true", help="run the built-in cases, no DB needed")
    ap.add_argument("--album-id", help="catalog album uuid to measure")
    ap.add_argument("--genius-json", help="collected Genius payload (list of per-track records)")
    ap.add_argument("--json", dest="out_json", help="write the per-annotation result here")
    args = ap.parse_args(argv)

    if args.self_test:
        return _self_test()

    if not (args.album_id and args.genius_json):
        ap.error("--album-id and --genius-json are both required unless --self-test")

    segments_by_track = _load_album_segments(args.album_id)
    records = json.load(open(args.genius_json))

    rows: List[dict] = []
    all_anchors: List[Anchor] = []
    per_track: List[Tuple[int, Coverage]] = []

    for rec in records:
        track_no = rec.get("no")
        segments = segments_by_track.get(track_no)
        if not segments:
            continue
        fragments = [a["fragment"] for a in rec.get("annotations", [])]
        anchors = anchor_fragments(segments, fragments)
        all_anchors.extend(anchors)
        per_track.append((track_no, summarize(anchors)))
        for a in anchors:
            rows.append({
                "track_no": track_no, "title": rec.get("title"), "index": a.index,
                "status": a.status, "span": a.span, "occurrences": a.occurrences,
            })

    overall = summarize(all_anchors)
    print(f"annotations: {overall.total}  (lyric-bound {overall.lyric_bound}, "
          f"section markers {overall.counts.get('section', 0)})")
    for status in ("unique", "partial", "repeated", "unmatched"):
        n = overall.counts.get(status, 0)
        if n:
            print(f"  {status:10} {n:4}  {n / overall.lyric_bound * 100:5.1f}%")
    print(f"\nplaced (unique+partial): {overall.placed_rate * 100:.1f}%"
          f"   located at all: {overall.any_rate * 100:.1f}%")

    if per_track:
        rates = sorted(c.placed_rate for _, c in per_track)
        median = rates[len(rates) // 2]
        print(f"per-track median: {median * 100:.1f}%   tracks: {len(per_track)}")

    if args.out_json:
        with open(args.out_json, "w") as fh:
            json.dump({"rows": rows, "placed_rate": overall.placed_rate}, fh,
                      ensure_ascii=False, indent=1)
        print(f"detail -> {args.out_json}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
