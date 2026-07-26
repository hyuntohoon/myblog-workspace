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

# Mirrors of the backend's LRC rules. The authority is
# `myblog_backend/app/services/lyrics_service.py` (`_LRC_TS`, `_LRC_ID_TAG`, `parse_lrc`);
# these must stay byte-equivalent to it — see `parse_lrc` below for why.
_LRC_TS = re.compile(r"^\[(\d+):(\d{1,2})(?:\.(\d{1,3}))?\]")
_LRC_ID_TAG = re.compile(r"^\[[A-Za-z#][^\]]*\]\s*$")

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
    """Timestamped LRC -> the exact segment list the viewer renders, in its order.

    **The index is the contract.** An anchor span is only useful if its numbers name the
    same rows the reader sees, so this must reproduce
    ``lyrics_service.parse_lrc`` — which keeps two kinds of row that carry no lyric text:

      * **gap segments** — timestamped but blank, the stanza break the viewer draws as
        ``· · ·`` (``LyricsViewer.tsx``, ``LyricsSheet.tsx``). Kept as ``""``.
      * **untimestamped lines** — kept verbatim (the backend flags but never drops text).

    Only bracketed ID tags (``[ar:...]``) and untimestamped blanks are dropped.

    An earlier version required a timestamp *and* non-blank text, which silently shifted
    every index after the first gap. Measured against prod on 2026-07-26: 93.5% of 1,200
    synced tracks differed in segment count and **44.2% had at least one row shifted**
    (median 2, max 22). The match *rate* was unaffected — ``_build_haystack`` skips
    segments that normalize to nothing, so a gap costs an index but contributes no text —
    which is exactly why the defect was invisible in the coverage numbers.
    """
    segments: List[str] = []
    for raw_line in (lyric_synced or "").split("\n"):
        line = raw_line.rstrip("\r")

        stamps = 0
        m = _LRC_TS.match(line)
        while m:                       # one segment per leading timestamp
            stamps += 1
            line = line[m.end():]
            m = _LRC_TS.match(line)

        if not stamps:
            if not line.strip() or _LRC_ID_TAG.match(line):
                continue               # untimestamped blank, or a metadata tag
            segments.append(line)      # kept with no timestamp — never silently dropped
            continue

        text = line[1:] if line.startswith(" ") else line   # one leading space trimmed
        if not text.strip():
            text = ""                  # gap segment; "" is the discriminator
        segments.extend([text] * stamps)
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

# Every row the backend keeps, in one fixture: an ID tag (dropped), an untimestamped
# blank (dropped), a gap (kept as ""), an untimestamped lyric line (kept), and a
# two-timestamp line (kept twice). Anything that shifts these indexes desynchronises
# every emitted span from the rows the reader sees.
_SELF_TEST_LRC = "\n".join([
    "[ar:ROSALÍA]",
    "[00:34.60] Quién pudiera vivir",
    "[00:37.67] Entre los dos",
    "[00:41.00]",
    "",
    "[00:41.32] En el primero,",
    "Deportes de sangre",
    "[00:47.45][01:12.10] Quién pudiera vivir",
])
_SELF_TEST_LRC_EXPECT = [
    "Quién pudiera vivir",
    "Entre los dos",
    "",                       # gap — the viewer's `· · ·`, and it holds an index
    "En el primero,",
    "Deportes de sangre",     # untimestamped, kept
    "Quién pudiera vivir",    # two timestamps -> two segments
    "Quién pudiera vivir",
]


def _parity_check() -> int:
    """Compare against the backend's own parser when this checkout has it.

    Skips silently when the backend package isn't importable — the tool has to run
    anywhere. Where it does run, this is what stops the two parsers drifting again.
    """
    import os

    backend = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "myblog_backend")
    if not os.path.isdir(backend):
        print("  [skip] backend checkout not found — parity not checked")
        return 0
    sys.path.insert(0, backend)
    try:
        from app.services.lyrics_service import parse_lrc as backend_parse
    except Exception as exc:                                  # noqa: BLE001 — advisory
        print(f"  [skip] backend not importable ({type(exc).__name__}) — parity not checked")
        return 0

    theirs = [s.text for s in backend_parse(_SELF_TEST_LRC)]
    ours = parse_lrc(_SELF_TEST_LRC)
    if ours == theirs:
        print(f"  [ok ] parity with lyrics_service.parse_lrc ({len(ours)} segments)")
        return 0
    print(f"  [FAIL] parity: ours={ours!r} backend={theirs!r}")
    return 1


def _self_test() -> int:
    failures = 0

    segments = parse_lrc(_SELF_TEST_LRC)
    if segments == _SELF_TEST_LRC_EXPECT:
        print(f"  [ok ] parse_lrc keeps gaps/untimestamped rows ({len(segments)} segments)")
    else:
        print(f"  [FAIL] parse_lrc expected {_SELF_TEST_LRC_EXPECT!r}, got {segments!r}")
        failures += 1

    # A fragment after the gap must resolve to the POST-gap index, not the pre-gap one.
    gap_anchor = anchor_fragments(segments, ["En el primero,"])[0]
    if gap_anchor.span == (3, 3):
        print("  [ok ] span after a gap keeps the viewer's index (3, 3)")
    else:
        print(f"  [FAIL] span after a gap expected (3, 3), got {gap_anchor.span}")
        failures += 1

    failures += _parity_check()

    anchors = anchor_fragments(_SELF_TEST_SEGMENTS, [f for f, _ in _SELF_TEST_CASES])
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
