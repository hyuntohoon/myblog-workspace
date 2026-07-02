# ARCH-lyrics-normalization-model: Lyric normalization model

- **Status**: draft
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
- **Corpus data state (FEAT-lyrics-corpus Phase 2, 2026-07-02)** — 7,955 `matched` rows;
  **7,253 / 7,955 (91%) carry `lyric_synced` (LRC)**. So **all four source categories are real**:
  - **plain-only** — `matched` with `lyric_synced IS NULL`.
  - **synced-only** — `matched` with `lyric_plain = ''` and `lyric_synced` set. The matcher's
    `_lyric_plain_for` (`lyrics_matcher.py:553-565`) **intentionally writes `lyric_plain=''`**
    for a matched candidate that carried only synced lyrics (to satisfy the V33 non-NULL CHECK);
    the actual text lives in `lyric_synced`. **This is the crux: a synced-only row's text is in
    `lyric_synced`, and the viewer must not get it by stripping timestamps.**
  - **plain-plus-synced** — `matched` with both populated.
  - **unavailable / low-quality** — `no_lyrics` (`lyric_plain=''`, instrumental/empty),
    `not_found`/`ambiguous`/`review_required` (no text by CHECK), missing row.

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
- **plain-plus-synced** — the **line-break source is the synced LRC's line structure**
  (it is the authoritative unit boundary; the plain text's line breaks may differ). Each segment
  takes its `text` from the **plain** (preferred — plain is the cleaner text) **aligned to the
  synced's line count/timestamps** when the counts match. When plain and synced line counts
  disagree, the normalized output follows the source with the stronger unit structure (synced,
  typically) and records the mismatch; it does not silently drop lines from either.

The viewer always gets the same shape; only how the shape was derived differs (recorded as a
`source_kind: 'plain'|'synced'|'mixed'` marker on the normalized payload, for diagnostics, never
rendered to the user).

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

- **Line-count mismatch** (plain N lines vs synced M lines) — common with crowd-sourced data; the
  normalizer follows the stronger unit structure (synced's lines) and records the mismatch in
  diagnostics; it does not merge mismatched lines by guess.
- **Text disagreement** (plain line ≠ synced line at the same index) — plain is preferred for
  `text` (closer to intended display), synced for `start_ms`; flagged, not silently swapped.
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

## Steps

Docs-only RFC. Hard rule #4 — one step per session.

### Step 0 — RFC + plan.md pointer (this document, docs-only)

This RFC + one-line `plan.md` Backlog pointer + `docs/rfcs/README.md` index entry. No code,
no schema.

**Verification**: doc review against `TEMPLATE.md` / README required sections. `git diff --stat`
shows only doc files.

---

### Step 1 — normalize model + read-path contract (docs/spec, no code yet)

Pin the exact normalized payload shape (`segments[]`, `start_ms`, `trackable`, availability
marker, `source_kind`) + the pseudocode for `normalize_lyrics` over the three paths, probed
against real `track_lyrics` rows (plain-only, synced-only, mixed, `no_lyrics`). Confirms whether
plain+synced line counts align often enough that "preferred text from plain, structure from
synced" is viable, or whether a fallback rule is needed. **No code / no endpoint** — produces the
spec FEAT-lyrics-viewer Step 1 will implement against.

**Verification**: spec review; a data probe (read-only) over a sample of each source category
confirms the three paths produce the expected segments; `git diff --stat` is docs-only.

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
- **Plain/synced line-count mismatch silently drops lines.** Mitigation: follow the stronger
  structure, record mismatches in diagnostics, never merge by guess.
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

1. **Segment granularity (blocks Step 1)** — line vs stanza vs LRC-grouped. The viewer's
   "focus-one-line" suggests line; confirm against a batch of real synced lyrics whether stanzas
   (blank-line / LRC gap-detection) are a better unit. Decide in Step 1 data probe.
2. **Multi-timestamp LRC lines (blocks Step 1)** — one LRC line with several `[mm:ss.xx]` (word-level
   karaoke). Decide: split into multiple segments (one per timestamp) vs one segment with sub-tokens.
   Lean: one segment per timestamp (keeps focus-one-line semantics clean).
3. **Plain text for mixed when counts mismatch (blocks Step 1)** — the rule "preferred text from
   plain, structure from synced" needs a concrete alignment fallback when counts diverge. Resolve
   in the Step 1 data probe against how often real mixed rows diverge.
4. **Stored normalized column vs read-time derive (deferred)** — kept read-time unless profiling
   shows otherwise. Re-open only with evidence.

## Decisions log

| Date | Decision | Step |
|------|----------|------|
| 2026-07-02 | One pure normalizer → one segment shape for plain-only/synced-only/mixed; viewer does no parsing | 0 |
| 2026-07-02 | synced-only parsed into segments, never stripped to raw text (hard rule from brief + viewer non-goal) | 0 |
| 2026-07-02 | Raw `lyric_plain`/`lyric_synced` stay source-of-truth; normalization is a read-time derived view (no stored column unless profiling) | 0 |
| 2026-07-02 | Future estimated sync / line restructure kept out of scope, but the shape (`start_ms` optional, index-keyed segments, pure/replayable) does not preclude them | 0 |
| 2026-07-02 | Translation / LLM translation explicitly out of scope (original lyrics only) | 0 |
| 2026-07-02 | V33 `lyric_plain=''` synced-only stored state handled as path 2 (parse LRC), not as empty plain | 0 |
