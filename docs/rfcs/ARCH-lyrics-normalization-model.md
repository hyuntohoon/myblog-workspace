# ARCH-lyrics-normalization-model: Lyric normalization model

- **Status**: accepted
- **Owner**: 박지훈
- **Created**: 2026-07-02
- **Plan row**: `plan.md` → ARCH-lyrics-normalization-model

---

## Goal

Define how raw `lyric_plain` and raw `lyric_synced` (LRC) stored on `track_lyrics` are
**normalized into one project-specific lyrics structure** before being sent to the lyrics
viewer (FEAT-lyrics-viewer). After this RFC, there is a single normalized segment contract the
viewer consumes — regardless of whether the source row is plain-only, synced-only, or
plain-plus-synced — and the viewer does no LRC parsing, no timestamp stripping, and no raw-text
fallback of its own.

This RFC owns the **normalized segment contract, plain/synced normalization paths, raw-source
preservation, re-normalization, synced-only exposure rules, and the missing/low-quality
representation** — the five things FEAT-lyrics-viewer explicitly routes here (see its
[Dependencies](../rfcs/FEAT-lyrics-viewer.md#dependencies)). Translation and LLM translation are
explicitly **out of scope** (the viewer renders original lyrics only).

## Non-goals

- **No preselection of schema or storage before investigation.** The model is defined from the
  current data + constraints; a normalized column, a computed field, an API-time transform, or a
  separate derived table are all candidates evaluated in [Current state](#current-state) /
  [Target state](#target-state), not assumed.
- **No translation / LLM translation / slang-meme / interpretation.** Original lyrics only — same
  boundary as FEAT-lyrics-corpus + FEAT-lyrics-viewer.
- **No synced-only-by-raw-text.** The viewer consumes normalized segments only; a synced-only row
  is never rendered by stripping timestamps client-side (hard non-goal, mirroring FEAT-lyrics-viewer).
- **No continuous / auto-advance sync.** Timestamps define units + enable optional one-shot
  initial focus; they never drive progression (FEAT-lyrics-viewer non-goal).
- **No changing the corpus.** This RFC reads `track_lyrics` only — it does not re-collect,
  re-match, or alter match-status. FEAT-lyrics-corpus owns that.
- **No public exposure.** Normalized lyrics carry the corpus's "never in any shared response" bar;
  the read path is authenticated-only (FEAT-lyrics-viewer Step 1).

## Current state (verified against code + data 2026-07-02)

### Source formats and states

`track_lyrics` (`myblog_shared_db/src/myblog_shared_db/models.py:308-330`):

```python
match_status:   Text NOT NULL            # matched | no_lyrics | not_found | ambiguous | review_required
evidence:       JSONB NOT NULL DEFAULT '{}'
lyric_plain:    Text  (nullable)         # LRCLIB plainLyrics — untimestamped text, \n-separated
lyric_synced:   Text  (nullable)         # LRCLIB syncedLyrics — LRC `[mm:ss.xx] line` (one/more timestamps per line)
matcher_version: Text (nullable)
created_at / updated_at
```

- **V33 CHECK (`ck_track_lyrics_lyric_on_resolved`)** — `matched`/`no_lyrics` rows require
  `lyric_plain IS NOT NULL`; `ambiguous`/`review_required`/`not_found` require `lyric_plain IS NULL`.
- **Corpus data state (FEAT-lyrics-corpus Phase 2, 2026-07-02; distribution re-probed
  2026-07-02 read-only against prod)** — 7,955 `matched` rows split across the four text-bearing
  categories as actually observed:

  | `match_status` | `lyric_plain` | `lyric_synced` | count | category |
  |---|---|---|---|---|
  | matched | non-empty | non-empty | 7,253 | **mixed** (plain + synced) |
  | matched | non-empty | NULL/empty | 702 | **plain-only** |
  | matched | non-empty='' / NULL | non-empty | **0** | **synced-only** (none observed) |
  | no_lyrics | empty | empty | 417 | instrumental/empty |
  | not_found | NULL | NULL | 9,798 | unresolved |
  | ambiguous | NULL | NULL | 2,743 | unresolved |
  | review_required | NULL | NULL | 33 | unresolved |

  **Key correction to the 2026-07-02 draft**: it stated "synced-only = 91%"; that was wrong. The
  91% figure is **mixed** (plain + synced). **`synced-only` rows are 0 in the actual corpus** —
  LRCLIB supplies plain alongside synced whenever it supplies synced. The matcher's
  `_lyric_plain_for` (`lyrics_matcher.py:553-565`) *can* coerce a synced-only candidate to
  `lyric_plain=''`, but **no such row exists in production**. Three consequences:
  - The pure normalizer's **mixed path is the dominant case (91%)**, not an edge case.
  - The **plain-only path (702 rows, 9%)** is real and must be handled (segments with
    `start_ms: null`, trackable=false → viewer first-segment focus).
  - The **synced-only path is a defensive-only branch** — it must still be correct (parse LRC to
    segments, never raw-text strip) because future LRCLIB data or an alternate source could
    produce it, but it is not exercised by the current corpus.

### No normalization code exists today

Grep confirms: there is **no LRC parser, no segment builder, no `to_segments`/`normalize_lyrics`**
anywhere in `myblog_worker` or `myblog_backend`. The matcher (`lyrics_matcher.py`) stores raw
LRCLIB `plainLyrics`/`syncedLyrics` verbatim (after NUL strip). The `_strip_nul` helper is the
only text transformation. **Normalization is a greenfield concern** — there is no existing
implementation to reconcile, only raw sources.

### Consumer constraint

FEAT-lyrics-viewer renders the **normalized segment contract** this RFC produces. It does no
LRC parsing, no plain/synced selection, and no timestamp stripping. A track is viewable iff (a) it
has a `matched` `track_lyrics` row **and** (b) normalization has produced consumable segments.
The viewer is **manual-nav only** (prev/next + swipe + tap-to-focus); timestamps, if retained in
the normalized shape, are used only to define units and (optionally) one-shot initial focus — never
to auto-advance.

## Target state — the normalization model

The model answers the brief's six questions in order. It is stated at the **principle level**;
exact segment schema columns are produced at step-time against a real-data probe (per the RFC scope:
behavior/principles now, implementation later).

### 1. Current source formats and states

(documented in [Current state](#current-state-verified-against-code--data-2026-07-02)): raw
`lyric_plain` (untimestamped) + raw `lyric_synced` (LRC-timestamped), both nullable, all four
categories real, no normalizer exists. The viewer must receive **one** normalized shape from any
of the three text-bearing categories (plain-only / synced-only / mixed).

### 2. Normalization paths for plain-only, synced-only, and mixed

A **single pure function** `normalize_lyrics(track_lyrics_row) -> NormalizedLyrics | None`
produces the same segment list regardless of source category:

- **plain-only** — split `lyric_plain` on line boundaries into one segment per line. No
  timestamps. Each segment = `{ text, start_ms: null }` (or the chosen shape's timestamp-or-null).
  Line-break source = the stored plain text's `\n`.
- **synced-only** — **parse the LRC**, never strip timestamps to make plain text. Each LRC line
  `[mm:ss.xx]text` → one segment `{ text, start_ms }` (multiple timestamps on one line → either
  repeated segments or a multi-timestamp segment — decided at step-time). **The viewer receives
  segments with their timestamps; it is forbidden from doing the parse itself.** This is the brief's
  hard rule: synced-only is not handled by stripping timestamps and passing raw text.
- **plain-plus-synced (the dominant 91% case)** — **derive segments from the synced LRC alone**:
  each LRC line → `{ text: <post-timestamp line content>, start_ms }`, i.e. the same code path as
  synced-only. **Plain is not used in the mixed path.** **Second probe (2026-07-02 pre-acceptance
  review, n=1000 mixed rows, prod read-only): after stripping timestamps from synced and removing
  blank lines from both sides, plain ≡ synced text in 98.0% of rows (99.5% identical non-blank
  line counts).** The first probe's "85% line-count divergence (avg Δ5)" was a **counting artifact
  of the synced side's blank stanza-marker lines** (present in 93% of rows) — the two sources carry
  the *same text*, and the "plain is the cleaner text" premise does not hold. An index-alignment
  rule would have shifted text against timestamps at every stanza marker and duplicated tail
  lines; deriving from synced alone eliminates the alignment problem entirely. The residual ~2%
  (plain ≠ stripped synced) is recorded in diagnostics with synced preferred — its text and
  timestamp come from the same line, so the pair is self-consistent; lines are never silently
  dropped or guess-merged.

### 3. Minimum common payload required by the viewer

The normalized payload the viewer renders must carry, at minimum:

- **`segments[]`** — the ordered list, each with at least `text` (the line content) and an optional
  `start_ms` (present when derived from synced, `null` when derived from plain-only).
- **`trackable`** — whether one-shot position-based initial focus is possible (true iff ≥1 segment
  has a `start_ms`). Plain-only → false → viewer degrades to first-segment focus.
- **A source-derived quality/availability marker** — to drive the empty states: `matched_with_text`
  / `no_lyrics` (instrumental) / `unavailable`. (The `match_status` already encodes this; the
  normalized payload carries it through.)

The exact field names are produced at step-time; the **contract** is: segments with optional
timestamps, trackability flag, availability marker. The viewer renders segments + focus-one; it
reads `start_ms` only for one-shot init.

### 4. How plain and synced information may conflict or combine

- **Line-count mismatch** (plain N lines vs synced M lines) — almost entirely the synced side's
  blank stanza-marker lines (probe: 99.5% of mixed rows have identical non-blank line counts).
  Moot in the mixed path: segments derive from synced alone, so plain's line structure is never
  aligned against synced's. Any residual real mismatch is recorded in diagnostics only.
- **Text disagreement** (plain ≠ timestamp-stripped synced; ~2% of mixed rows) — **synced wins**:
  its text and `start_ms` come from the same line, so the pair is self-consistent. The
  disagreement is flagged in diagnostics, not silently merged.
- **synced-only with `lyric_plain=''`** (the V33-driven stored state) — handled by path 2
  (parse LRC), never by treating `''` as the text.
- **Future estimated sync (out of scope now)** — when a plain-only track later gets *estimated
  timing*, it would upgrade `start_ms: null` → `start_ms: <estimate>` on existing segments. The
  boundary this protect: a normalized segment already has an optional `start_ms` slot, so the
  upgrade is additive — **a future estimation step edits timestamps on existing segments, not the
  segment text/structure.** This is why plain-only segments carry `start_ms: null` rather than no
  field at all.

### 5. Future timing estimation + line restructuring at the boundary

- **Estimated synchronization / auto line-break / split-merge** are explicitly **future**, out of
  this RFC's implementation scope. But the normalized shape must **not preclude** them:
  - `start_ms: null` on plain-derived segments leaves room for future estimated timing without a
    schema change.
  - Segments keyed by **index + text + optional timestamp** (not by a frozen line-id) lets a future
    split/merge rewrite the segment list without breaking the viewer (the viewer is
    index/nav-driven, not id-driven).
  - The normalizer is a **pure, replayable function**: re-running it on the same raw row yields the
    same segments, so a future estimation pass can layer on top without re-deriving text.

### 6. Unavailable / low-quality representation

Mapped to the viewer's empty states (FEAT-lyrics-viewer defines the copy):

- `no_lyrics` (instrumental/empty) → normalize returns the `no_lyrics` availability marker; viewer
  shows "가사 없음 (연주곡)".
- `not_found` / `ambiguous` / `review_required` / missing row → normalize returns `None`/unavailable;
  viewer shows "아직 연결된 가사가 없어요".
- **Low-quality-but-present** (e.g. romanized where original-script expected, truncated — corpus
  metric #6 "source-quality conflict rate") — the normalizer does **not** decide quality; it passes
  the text through. Quality gating belongs to the corpus (FEAT-lyrics-corpus already tracks this in
  `evidence`); the normalizer only flags source_kind. The viewer reads text as an aid, never asserts
  authority (FEAT-lyrics-viewer risk note).

### Where + when normalized data is produced and maintained

- **Produced where:** at read time, behind the authenticated lyrics-read endpoint
  (FEAT-lyrics-viewer Step 1), **not** stored on `track_lyrics` in a first cut. Rationale: the
  normalizer is pure + replayable; a normalized column would duplicate the raw sources and create a
  re-normalization maintenance burden before there is a second consumer. **Raw `lyric_plain` /
  `lyric_synced` stay the source of truth**; normalization is a derived view materialized on read.
  (A stored normalized column is a candidate **only if** profiling shows the parse is hot or a
  second consumer appears — evaluated at step-time, not assumed.)
- **Produced when:** per authenticated read request. The endpoint returns the normalized payload
  (+ `match_status`), not raw text.
- **Maintained / re-normalization:** because normalization is a pure function over the raw row,
  re-normalization is implicit — any raw update (Step 4 reassessment, a future match improvement)
  flows through automatically on the next read; no separate re-write job is needed in this RFC.
  If a future estimation step or schema change alters the segment shape, the normalizer's version
  is bumped (mirroring the corpus's `matcher_version` idea) so a cached normalized payload can be
  invalidated.

## Normalized payload spec (Step 1, pinned 2026-07-02)

This is the contract FEAT-lyrics-viewer Step 1 implements against. It resolves the "exact
field names at step-time" deferrals above; the principles in [Target state](#target-state--the-normalization-model)
remain the rationale. Written from the resolved OQ1–5 probes — no new data probe was needed.

### Payload shape

```jsonc
// GET <authenticated lyrics read endpoint>  (route naming owned by FEAT-lyrics-viewer Step 1)
// JWT-gated. Never public, never edge-cached.
{
  "availability": "ok" | "no_lyrics" | "unavailable",
  "source_kind": "synced" | "plain",   // present iff availability == "ok"
  "trackable": false,                   // true iff ≥1 segment has non-null start_ms
  "normalizer_version": 1,              // bumped on any segment-shape/derivation change
  "segments": [                         // [] unless availability == "ok"; file order preserved
    { "i": 0, "text": "line content", "start_ms": 12340 }   // start_ms: int | null
  ]
}
```

- **`segments[].i`** — 0-based index; the viewer's nav/focus key (index-keyed, not id-keyed,
  per [§5](#5-future-timing-estimation--line-restructuring-at-the-boundary)).
- **`segments[].text`** — line content. **May be `""`**: an empty-text segment is a stanza
  gap (the blank-timestamp LRC markers present in 93% of synced rows, and blank lines in
  plain text). The viewer renders gaps as spacing and skips them in prev/next/tap focus;
  `text == ""` is the gap discriminator — no extra field.
- **`segments[].start_ms`** — millisecond offset from track start; `null` when derived from
  plain-only. Optional-from-day-one so future estimated timing is an additive upgrade.
- **`trackable`** — drives the viewer's optional one-shot initial focus; `false` → first-segment focus.
- **`availability`** — `ok` (renderable segments) / `no_lyrics` (instrumental → "가사 없음 (연주곡)")
  / `unavailable` (`not_found`/`ambiguous`/`review_required`/missing row/defensive empty →
  "아직 연결된 가사가 없어요"). Derived from `match_status`; the raw status is not exposed.
- **`normalizer_version`** — cache-invalidation hook (mirrors `matcher_version`); starts at `1`.

### `normalize_lyrics` pseudocode (pure, replayable)

```python
def normalize_lyrics(row: TrackLyrics | None) -> NormalizedLyrics:
    if row is None or row.match_status in ("not_found", "ambiguous", "review_required"):
        return NormalizedLyrics(availability="unavailable", trackable=False, segments=[])
    if row.match_status == "no_lyrics":
        return NormalizedLyrics(availability="no_lyrics", trackable=False, segments=[])

    # match_status == "matched"
    if (row.lyric_synced or "").strip():
        # synced-only AND mixed (91%): derive from synced ALONE — same code path.
        # Plain is never aligned against synced (pre-acceptance correction, OQ3).
        segments = parse_lrc(row.lyric_synced)
        source_kind = "synced"
        if (row.lyric_plain or "").strip() and plain_disagrees(row.lyric_plain, segments):
            log.warning("lyrics normalize: plain != stripped synced (synced wins)", ...)  # ~2% residual; diagnostics only
    elif (row.lyric_plain or "").strip():
        # plain-only (9%): one segment per line, blank lines kept as gaps
        segments = [Segment(i=i, text=t.rstrip("\r"), start_ms=None)
                    for i, t in enumerate(row.lyric_plain.split("\n"))]
        source_kind = "plain"
    else:
        return NormalizedLyrics(availability="unavailable", trackable=False, segments=[])  # defensive

    trackable = any(s.start_ms is not None and s.text != "" for s in segments)
    return NormalizedLyrics(availability="ok", source_kind=source_kind,
                            trackable=trackable, segments=segments)
```

`parse_lrc` rules (pinned from the OQ probes):

1. **One segment per LRC line with one leading timestamp** — multi-timestamp lines do not
   occur (0/2000); if a future source introduces them, each timestamp becomes its own
   segment (additive).
2. **Timestamp grammar** — `[mm:ss]`, `[mm:ss.x]`, `[mm:ss.xx]`, `[mm:ss.xxx]` →
   `start_ms = mm*60_000 + ss*1_000 + frac_ms` (2-digit frac ×10, 1-digit ×100). Minutes may
   exceed 59.
3. **Blank-timestamp lines** (`[mm:ss.xx]` + empty/whitespace text) → gap segments
   (`text: ""`, `start_ms` kept).
4. **Non-timestamp lines** — LRC ID tags (`[key:value]`, non-numeric key, e.g. `[ar:…]`) are
   metadata → dropped; any other non-empty untimestamped line is kept as a segment with
   `start_ms: null` + a diagnostics flag (text is never silently dropped).
5. **File order preserved** — segments are not re-sorted; an out-of-order timestamp is a
   diagnostics flag, not a re-order.
6. **Text** — post-timestamp content, one leading space trimmed, `\r` stripped. No other
   mutation (NUL was already stripped at ingest).

`plain_disagrees` (diagnostics only, never merges): compare non-blank line counts and
whitespace-normalized joined text of `lyric_plain` vs the parsed segments' non-gap text;
any difference → one `log.warning` with track id + counts. **Synced always wins** — the
payload is built from synced regardless.

### Production/maintenance (restated as contract)

Derived at read time behind the JWT-gated endpoint; no stored normalized column in v1
(re-evaluate only on profiling or a second consumer). Raw `lyric_plain`/`lyric_synced` stay
source-of-truth; any raw update flows through on the next read. A segment-shape or
derivation change bumps `normalizer_version`.

### Acceptance gate (checked by FEAT-lyrics-viewer Step 1 verification)

- plain-only / synced-only / mixed all return the identical payload shape above.
- A synced-bearing row's segments carry `start_ms` — synced-only is **never** raw text
  (`lyric_plain=''` + synced present ⇒ `source_kind: "synced"`, parsed segments).
- `no_lyrics` / unresolved / missing rows map to the two empty states, never to `availability: "ok"`.
- The normalizer is pure: same row in ⇒ byte-identical payload out.

## Steps

Docs-only RFC. Hard rule #4 — one step per session.

### Step 0 — RFC + plan.md pointer (this document, docs-only)

This RFC + one-line `plan.md` Backlog pointer + `docs/rfcs/README.md` index entry. No code,
no schema.

**Verification**: doc review against `TEMPLATE.md` / README required sections. `git diff --stat`
shows only doc files.

---

### Step 1 — normalize model + read-path contract (docs/spec, no code) — **DONE 2026-07-02**

Pin the exact normalized payload shape (`segments[]`, `start_ms`, `trackable`, availability
marker, `source_kind`) + the pseudocode for `normalize_lyrics` over the three paths. The data probe
([Open questions](#open-questions) 1–4, resolved 2026-07-02) already confirmed: line is the unit;
multi-timestamp lines absent (one segment per LRC line); blank-timestamp lines kept as stanza
spacing; mixed rows derive from synced alone (plain ≡ timestamp-stripped synced in 98%). This
step writes the spec from those resolved answers — **no new data probe needed**. Produces the spec
FEAT-lyrics-viewer Step 1 implements against. **Executed 2026-07-02 → the
[Normalized payload spec](#normalized-payload-spec-step-1-pinned-2026-07-02) section above.**

**Verification**: spec review; `git diff --stat` is docs-only.

**Rollback**: n/a (docs-only).

---

### Step 2 — (later, FEAT-lyrics-viewer's step) implement behind the read endpoint

The actual normalization function + the authenticated lyrics-read endpoint (FEAT-lyrics-viewer
Step 1) implements this spec. **This RFC's Step 2 is a pointer** — the implementation ownership
stays with FEAT-lyrics-viewer; ARCH-lyrics-normalization-model owns the contract it conforms to.

**Verification**: the implemented endpoint's response matches the segment contract pinned in
Step 1; plain-only/synced-only/mixed all return the same shape; synced-only is never raw text.

**Rollback**: owned by FEAT-lyrics-viewer.

---

## Risks

- **Synced-only mishandled as raw text.** The single biggest risk. Mitigation: pure normalizer
  parses LRC server-side (path 2); the viewer contract forbids raw-text/timestamp-strip; the
  acceptance gate enforces it.
- **Plain/synced text mismatch silently merged.** Mitigation: the mixed path derives from synced
  alone (no cross-source alignment exists to get wrong); the ~2% real disagreements are flagged
  in diagnostics, never guess-merged.
- **Premature storage of a normalized column.** Mitigation: read-time derivation first; a stored
  column is a profiling-gated follow-on, not assumed — keeps re-normalization a non-issue.
- **V33 `lyric_plain=''` confusion.** A future implementer may read `''` and render an empty
  viewer for a synced-only row. Mitigation: the normalizer treats `lyric_synced`-present +
  `lyric_plain=''` as synced-only (path 2), not as empty plain.
- **Future estimation breaking the shape.** Mitigation: `start_ms` is optional from day one; segments
  are index-keyed; the normalizer is pure/replayable.
- **Privacy tier drift.** Mitigation: normalization is behind the JWT-gated authenticated read
  only; the normalized payload never enters a public/edge-cached response (corpus + viewer privacy
  boundary).

## Open questions

Resolved by the 2026-07-02 read-only prod probe (n=2000–3000):

1. **Segment granularity** — **resolved: line, with stanza-aware grouping optional.** The viewer's
   "focus-one-line" → line is the render unit. **Probe: 93% of synced rows (1,861/2,000) contain a
   blank/empty LRC segment** (`^\[[0-9:.]+\]\s*$`) — i.e. LRCLIB uses empty lines as stanza break
   markers pervasively. Decision: the **segment = one timestamped line**; blank-timestamp lines are
   kept as inter-stanza spacing segments (not dropped), so the viewer can render natural stanza
   gaps. A future "collapse to stanza" view is additive, not a schema change.
2. **Multi-timestamp LRC lines** — **resolved: not present (0/2000 rows).** Word-level karaoke
   (multiple `[mm:ss.xx]` on one line) does **not** occur in the corpus. Decision: **one segment per
   LRC line** (one leading timestamp). No multi-timestamp handling needed; if a future source
   introduces it, treat each timestamp as its own segment (additive, not breaking).
3. **Plain/synced line-count divergence** — **resolved (corrected 2026-07-02, pre-acceptance
   review): the divergence was a blank-line counting artifact, not text divergence.** Second probe
   (n=1000 mixed rows): after timestamp-strip + blank-line removal, plain ≡ synced text in 98.0%
   (99.5% identical non-blank line counts) — the first probe's "85% divergence" was the synced
   side's stanza markers. Decision recorded in
   [Normalization paths](#2-normalization-paths-for-plain-only-synced-only-and-mixed): the mixed
   path derives segments from synced alone (no index alignment; same code path as synced-only);
   the residual ~2% is flagged in diagnostics with synced preferred — never guess-merge.
4. **Stored normalized column vs read-time derive** — **resolved: read-time derive.** No stored column
   unless profiling shows the parse is hot or a second consumer appears. (Avg ~59 lines/lyric is
   cheap to parse per read.)
5. **`synced-only` path necessity** — **resolved: defensive-only.** 0 such rows in prod today; the
   branch stays correct (parse LRC, never raw strip) but is not the focus. Mixed (91%) + plain-only
   (9%) are the live paths.

## Decisions log

| Date | Decision | Step |
|------|----------|------|
| 2026-07-02 | One pure normalizer → one segment shape for plain-only/synced-only/mixed; viewer does no parsing | 0 |
| 2026-07-02 | synced-only parsed into segments, never stripped to raw text (hard rule from brief + viewer non-goal) | 0 |
| 2026-07-02 | Raw `lyric_plain`/`lyric_synced` stay source-of-truth; normalization is a read-time derived view (no stored column unless profiling) | 0 |
| 2026-07-02 | Future estimated sync / line restructure kept out of scope, but the shape (`start_ms` optional, index-keyed segments, pure/replayable) does not preclude them | 0 |
| 2026-07-02 | Translation / LLM translation explicitly out of scope (original lyrics only) | 0 |
| 2026-07-02 | V33 `lyric_plain=''` synced-only stored state handled as path 2 (parse LRC), not as empty plain | 0 |
| 2026-07-02 | Prod probe resolves OQ1–5: mixed=91% (7,253) / plain-only=9% (702) / synced-only=0 rows (draft's "synced-only=91%" was wrong — that was mixed); line is the unit; multi-timestamp LRC absent (0/2000) → one segment/line; blank-timestamp stanza markers in 93% of rows → keep as spacing segments; plain/synced line-count divergence is the norm (exact match 15%, avg Δ 5 lines over n=3000) → follow synced structure, best-effort align plain by index; read-time derive confirmed (avg 59 lines, cheap) | 0 |
| 2026-07-02 | **Pre-acceptance correction (supersedes the OQ3 alignment rule above)**: 2nd probe (n=1000) shows the "85% divergence" was blank stanza-marker counting — plain ≡ timestamp-stripped synced in 98.0% (99.5% same non-blank line count) → **mixed path derives segments from synced alone** (no index alignment; index alignment would shift text vs timestamps at every stanza marker + duplicate tail lines); plain used only in the plain-only path; ~2% residual mismatch → diagnostics, synced wins | 0 |
| 2026-07-02 | Status draft → accepted (owner approval in session, post final review) | 0 |
| 2026-07-02 | Step 1 executed — payload spec pinned (`availability`/`source_kind`/`trackable`/`normalizer_version`/`segments[]{i,text,start_ms}`; `text==""` = stanza gap, no extra field) + `normalize_lyrics`/`parse_lrc` pseudocode (synced-only & mixed share one path; ID-tag lines dropped, untimestamped text kept + flagged; file order preserved; `plain_disagrees` = diagnostics only, synced wins) + acceptance gate | 1 |
