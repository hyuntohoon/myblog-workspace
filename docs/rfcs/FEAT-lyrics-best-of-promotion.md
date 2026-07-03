# FEAT-lyrics-best-of-promotion: auto-promote the best plausible candidate out of `ambiguous` / `review_required`

- **Status**: draft
- **Owner**: 박지훈
- **Created**: 2026-07-03
- **Plan row**: `plan.md` → FEAT-lyrics-best-of-promotion
- **Predecessor**: `FEAT-lyrics-corpus` (Status: done) — builds the conservative matcher + corpus this RFC widens.

---

## Goal

After this RFC, a catalog track that the conservative matcher parks as `ambiguous` or
`review_required` (because evidence cannot cleanly separate the candidates, or the single
candidate fails the version-token / fuzzy bar) **no longer sits without a lyric**. Instead the
corpus job **automatically picks the single best plausible candidate** and attaches its lyric as a
distinctly-tagged `matched` row — `match_basis = best-of-ambiguous` / `best-of-review` — so coverage
grows without weakening the *meaning* of an `exact-title` match and without any owner UI / manual
selection. The original conservative matcher and its evidence are **preserved verbatim**; the
best-of promotion is a separate decision layer that runs after it, records which candidate it chose
and why, and remains re-evaluable by the existing reassessment job.

The immediate, measured target is the current parked pool — **~2,783 tracks** (`ambiguous` 2,749 +
`review_required` 34 as of 2026-07-03) — plus every future ambiguous/review outcome produced by the
incremental and reassessment jobs. `not_found` (no candidate at all) is explicitly **out of scope**:
there is nothing to choose from.

## Non-goals

- **No manual selection UI.** The owner does not pick a candidate in the app. This is auto-promote
  only. (A future owner-override surface is a separate RFC.)
- **No change to `exact-title` matching.** The conservative `decide_match` thresholds, version-token
  gate, and artist-identity gate are untouched. A row that already matches cleanly keeps meaning
  exactly what it meant under `FEAT-lyrics-corpus`.
- **No public exposure.** `track_lyrics` stays owner-only research data (V33 privacy boundary). No
  API / page / search / shared response gains a lyrics field. Best-of promotion changes which rows
  carry a lyric internally; it does not change what is exposed.
- **No `not_found` recovery here.** A track with no plausible candidate has nothing to promote;
  lifting `not_found` would require a manual-search surface (separate RFC).
- **No matcher false-positive cleanup (yet).** The duplicate-noise cases that *cause* false
  ambiguity — e.g. `01 -` track-number prefixes, `(Paused)` non-rendition parentheticals — are a
  separate, later improvement (see Open questions). This RFC treats the matcher as-is and decides
  *given* its candidate set.
- **No translation / interpretation / album analysis.** Same out-of-scope line as the predecessor
  RFC — this widens the *corpus*, not any consumer of it.

## Current state

Verified against code + a live read-only prod query on 2026-07-03:

- **Conservative matcher** (`myblog_worker/worker/service/lyrics_matcher.py`): `decide_match` is a
  pure, no-I/O decision. `ambiguous` fires at `:318-327` when plausible candidates collapse to **≥2
  groups** keyed by `(normalized artist, stripped base title)`; `review_required` fires at `:351-379`
  when a single representative either disagrees on version tokens
  (`reason=version_token_mismatch`) or matched only fuzzily (`reason=title_fuzzy_only`). Both write
  `lyric_plain=NULL` and keep an `evidence` JSONB with the candidate **previews only**
  (`title`/`artist`/`duration_sec`, up to 3) — **no lyric body**.
- **Shared eval loop** (`worker/service/lyrics_eval_core.py:run_eval_batch`): the single loop both
  jobs share. It calls `decide_match`, then a `should_write` gate (optional), then
  `TrackLyricsWriter`. Crucially, the in-memory `Candidate` list passed to `decide_match` **does
  carry lyric bodies** (`plain_lyrics` / `synced_lyrics`) at this point — they are only stripped when
  flattened into `evidence`. So a promotion layer invoked inside this loop can attach a body without
  a second LRCLIB round trip.
- **Step 3 incremental** (`worker/service/lyrics_incremental_service.py`): no write gate — every
  outcome is written (the row is the sentinel).
- **Step 4 reassessment** (`worker/service/lyrics_reassessment_service.py`): `should_replace` is the
  replacement guard; `_BASIS_STRENGTH` ladder is `{None:0, fuzzy-title:1, exact-title:2,
  mb-recording:3, isrc:4}`. A `matched` row is never replaced in practice because the current matcher
  only ever emits `exact-title` for `matched`. **Best-of bases must slot into this ladder** or the
  guard would mishandle them.
- **Writer** (`lyrics_matcher.py:TrackLyricsWriter`): `ON CONFLICT (track_id) DO UPDATE` per row;
  `_lyric_plain_for` already coerces `matched` rows to a non-NULL `lyric_plain` (the V33 CHECK).
- **Viewer** (`myblog_backend/.../lyrics_service.py:115`): `ambiguous` / `review_required` /
  `not_found` all map to `availability="unavailable"`. **Best-of-promoted rows become `matched`, so
  the viewer serves them with no viewer change** — coverage gain is transparent to the consumer.
- **Prod pool (read-only 2026-07-03, denominator = 21,218 evaluated / 21,500 tracks):**
  `not_found 10,041 (47%)` · `matched 7,955 (37%)` · `ambiguous 2,749 (13%)` · `no_lyrics 439` ·
  `review_required 34`. The promotion target is the **2,783** ambiguous+review rows.
- **Concrete false-ambiguity example (read-only 2026-07-03):** catalog track *Come Back to Earth*
  (Mac Miller, 161 s, no ISRC) is parked `ambiguous` with three LRCLIB candidates that are **all the
  same recording** at slightly different durations — `Come Back to Earth` (162.0 s), `Come Back to
  Earth (Paused)` (161.84 s), `01 - Come Back to Earth` (162.0 s). They split into three groups only
  because the group key strips rendition tokens but **not** track-number prefixes nor non-rendition
  parentheticals, so the three base titles differ (`come back to earth`, `come back to earth
  paused`, `01 come back to earth`). The "best" choice here is unambiguous to a human: the clean
  `Come Back to Earth`. This is the canonical case the promotion layer must resolve correctly, and
  the case that motivates leaving the matcher's candidate set intact and deciding on top of it.

## Target state

A **separate promotion layer** that runs after `decide_match`, **inside `run_eval_batch`** (so it
covers the incremental job, the reassessment job, and any future backfill in one place):

- **`promote_best(outcome, candidates) -> outcome`** (pure, no-I/O; lives beside `decide_match`).
  Given an `ambiguous` / `review_required` outcome and the **in-memory candidate list** (bodies
  present), pick one candidate by the priority below and return a `matched` outcome carrying its
  lyric, tagged so it is never confused with an exact match:
  1. **Exact base-title agreement + version-token agreement** — the candidate whose stripped base
     title equals the catalog's, whose duration is within tolerance, and whose version tokens agree
     with the catalog's. (Resolves the Come Back to Earth case to the clean `Come Back to Earth`.)
  2. **Duration-nearest** among the rest (smallest `|catalog − candidate|`, ties broken by…).
  3. **Highest title similarity** (fuzzy ratio on stripped base).
  4. **Richest lyric** (`synced > plain > none`) as the final tiebreak.
  A candidate carrying an **instrumental** flag is never promoted to a non-empty `matched`; if every
  candidate is instrumental, the row is promoted to `no_lyrics` instead (still resolved).
- **New `match_basis` values**: `best-of-ambiguous` and `best-of-review`, **distinct from and weaker
  than** `exact-title`. They are recorded in `evidence.match_basis` and **slot just above
  `fuzzy-title`** in the `_BASIS_STRENGTH` ladder (`best-of-*: 1.5`, or integer steps reshuffled at
  step time) so the replacement guard treats them correctly: an `exact-title` match supersedes a
  best-of match, and a best-of match supersedes an unresolved row but is itself superseded by any
  future exact match as LRCLIB coverage grows.
- **Evidence preservation**: the promoted row's `evidence` keeps the **original** ambiguous/review
  `reason` (e.g. `multiple_plausible` with the full candidate preview list) **plus** a new
  `promotion` block — `{chosen: {lrclib_id,title,artist,duration_sec}, criterion: "exact-base-title"
  | "duration-nearest" | "fuzzy" | "richest", from_status: "ambiguous"|"review_required"}` — so any
  wrong promotion is fully reconstructable and reversible.
- **Version safety, scoped**: `best-of-review` deliberately attaches a candidate that **failed the
  version-token gate** (that is what `review_required` means). This is an **accepted, tagged**
  relaxation: the original `exact-title` bar is untouched, and the disagreement is recorded in
  `evidence.promotion` + the distinct basis. No `exact-title` row loses its guarantee.
- **Replacement / reassessment**: a best-of `matched` row **remains a reassessment target** (LRCLIB
  growing may later yield an `exact-title` match that legitimately supersedes it). The replacement
  guard enforces "strictly stronger basis only", so reassessment can upgrade best-of → exact-title
  but never best-of → a different best-of (no lateral churn).
- **No schema change.** `track_lyrics` already holds everything (`match_status`, `evidence` JSONB,
  `lyric_plain`, `lyric_synced`, `matcher_version`). `match_basis` is a value inside `evidence`, not
  a column. `matcher_version` bumps (e.g. `step2-v2` → `step2-v3` or a `best-of-v1` tag) so the
  provenance of every row is known.

### Privacy + source-trust boundaries (unchanged from predecessor)

Best-of promotion changes **which internal rows carry a lyric**, not what is exposed or how the text
may be used. LRCLIB stays the only lyric-text source, untrusted for factual correctness,
private-research only, never redistributed.

## Steps

Milestone-level. Hard rule #4 — one step per session, prod-observe / direction-recheck gate between
steps. Branch/commit per repo (`feedback-nested-repo-branch-per-repo`); RFC + plan row land on the
workspace repo.

### Step 0 — RFC + plan.md pointer (this document, docs-only)

This RFC + a one-line `plan.md` Backlog pointer + the `docs/rfcs/README.md` index entry. No code.

**Verification**: doc review against `TEMPLATE.md` / README required sections; `git diff --stat`
shows only doc files.

---

### Step 1 — `promote_best` decision core + labelled-sample validation (worker, code + offline)

Add the pure `promote_best(outcome, candidates)` to `lyrics_matcher.py` (or a sibling module),
implementing the priority ladder above, returning a `matched`/`no_lyrics` outcome tagged
`best-of-ambiguous` / `best-of-review` with the `evidence.promotion` block. **Before** integrating it
anywhere live, validate it offline on a labelled sample:

- **Risk-quantification read-only probe (run first, gates the ladder)**: over the **live prod
  ambiguous pool**, measure (a) the fraction whose candidate set contains a candidate with an
  **exact stripped-base-title match** to the catalog title (the ladder's tier-1 hit rate — the
  higher this is, the more promotions ride the safe tier), (b) the **duration gap** distribution of
  the tier-1 pick, and (c) how many ambiguous sets are *genuine* two-distinct-songs ambiguity vs
  duplicate-noise (Come Back to Earth style). Denominators stated on every line. If tier-1 hit rate
  is low, the ladder / thresholds are revised **before** any write.
- **Labelled sample**: a hand-checked N (~50–100) across English/Korean, alias, featured, same-title,
  remix/live/version-token-disagreement, and duplicate-noise. Report best-of precision + which tier
  each promotion rode. Acceptance: best-of precision ≥ the owner-set bar (Open questions) and **zero
  exact-title regressions** (the conservative matcher's outputs are bit-identical before/after —
  `promote_best` only ever rewrites an `ambiguous`/`review_required` outcome, never an `exact-title`
  one).

**Verification**: pure-function unit tests (`promote_best` over constructed candidate sets,
including Come Back to Earth's exact three candidates → clean title); the labelled-sample precision
report; a differential test that `decide_match` outputs for `matched`/`no_lyrics`/`not_found` rows
are unchanged. Worker `pytest` green.

**Rollback**: `promote_best` is unused until Step 2; revert the module addition.

---

### Step 2 — integrate into the shared eval loop (worker, live forward path)

Invoke `promote_best` inside `run_eval_batch` immediately after `decide_match` (only when the outcome
is `ambiguous`/`review_required`), **before** the writer. Extend `new_metrics` with
`promoted_ambiguous`, `promoted_review`, and per-criterion counters (all with explicit
denominators). Slot `best-of-*` into `_BASIS_STRENGTH` and extend `should_replace`'s tests. Because
the loop is shared, this single change makes **both** the incremental job (Step 3 of the predecessor)
and the reassessment job (Step 4) promote forward — and any future backfill reuses it.

**Verification**: existing Step 3/4 tests updated (a previously-`ambiguous` fixture now promotes to a
`best-of-ambiguous` `matched`); replacement-guard tests cover best-of → exact-title supersession and
best-of → best-of refusal; the consistency invariant (`matched` ⇒ `version_agrees` consistent with
the *basis*) is re-expressed for best-of. Worker `pytest` green.

**Rollback**: revert the `run_eval_batch` call site; `promote_best` becomes dead code. Forward rows
written during the window are `best-of-*` `matched` — harmless (they are valid lyrics), and
reassessable.

---

### Step 3 — retroactive promotion of the existing parked pool (worker, one-shot backfill)

A bounded, resumable one-shot (the same `tools/lyrics_batch_api.py` shape, or a reassessment-style
invocation) that re-selects the **current** `ambiguous`/`review_required` pool (2,749 + 34), fetches
fresh LRCLIB candidates, runs `decide_match` → `promote_best`, and writes the promoted rows. Runs
**local or worker, not in a user path**; per-row commit + the LRCLIB ~2.5 req/s concurrency ceiling
from the predecessor apply. Per-status deltas reported (ambiguous→matched, review→matched, residual
ambiguous that promoted to `no_lyrics`, anything that stayed parked — e.g. all-instrumental handled,
or a tier that produced no safe pick).

**Verification**: before/after pool counts; a random-slice manual audit of best-of promotions
(denominator = promotions this run) for precision; confirm no `exact-title` row changed.

**Rollback**: the promotions are additive rewrites of previously-unresolved rows; a script restores
the prior `ambiguous`/`review_required` status + NULL lyric from the preserved `evidence` (or from a
pre-run snapshot) for the affected `track_id`s.

---

## Metrics (denominators explicit)

1. **Best-of precision** — of rows promoted to `matched` (`best-of-*`), the fraction whose attached
   lyric is correct for that exact track under manual audit. *Denominator = best-of-promoted count.*
   Primary gate; **lower bar than the predecessor's 99% is expected and accepted** (these were
   ambiguous by construction) — owner sets the number (Open questions).
2. **Exact-title precision (unchanged)** — must stay ≥ 99% (predecessor gate). *Denominator =
   `exact-title` matched count.* Regression guard, not a growth target.
3. **Best-of coverage gain** — fraction of the previously-`ambiguous`+`review_required` pool that
   reaches a `matched`/`no_lyrics` promotion. *Denominator = pre-run ambiguous+review count.*
4. **Promotion-tier breakdown** — per `criterion` (`exact-base-title` / `duration-nearest` / `fuzzy` /
   `richest`). *Denominator = best-of-promoted count.* (Tier-1 share is the safety signal.)
5. **Version-conflict attach count** — best-of rows where the chosen candidate's version tokens
   disagreed with the catalog's (only possible via `best-of-review`). *Denominator =
   `best-of-review` count.* Reported + audited, not gated to 0 (the relaxation is intentional) — but
   a high rate triggers a direction recheck.
6. **Replacement-guard behavior** — best-of rows superseded by a later `exact-title` match during
   reassessment, and best-of→best-others refused. *Denominator = reassessed best-of rows.*

## Risks

- **Genuine (non-noise) ambiguity promoted wrong** — some `ambiguous` sets really are two distinct
  songs at near-equal duration; the ladder's tier-1 cannot always tell. Mitigation: tier-1 (exact
  base-title) first; the risk-quantification probe (Step 1) measures how often tier-1 covers before
  any write; wrong promotions are fully reconstructable from `evidence.promotion` and reversible.
- **Version-safety relaxation** (`best-of-review`) — attaching a version-token-disagreeing candidate
  is an accepted, tagged trade for coverage. Mitigation: distinct basis + recorded disagreement;
  `exact-title` guarantees untouched; high version-conflict rate (metric 5) is a recheck trigger.
- **Promotion churn under reassessment** — a best-of row could be re-promoted to a *different*
  candidate next reassessment. Mitigation: replacement guard allows only strictly-stronger-basis
  replacement; lateral best-of→best-of is refused.
- **LRCLIB body availability** — promotion needs the candidate body, which lives only in the
  in-memory `Candidate` at eval time, not in stored `evidence`. Mitigation: `promote_best` runs
  inside `run_eval_batch` where the `Candidate` list is live; the retroactive backfill (Step 3)
  re-fetches rather than reading stale evidence.
- **Bar drift** — relaxing one boundary can pressure the next. Mitigation: the predecessor's
  `exact-title` bar is fenced off by the distinct basis; this RFC grows coverage only through the
  best-of channel.

## Open questions

1. **Best-of precision bar (blocks Step 1 acceptance).** The predecessor gates `exact-title` at ≥99%.
   Best-of promotions start from ambiguity, so a lower bar is honest — proposed **≥ 90%** (owner to
   set). *Denominator = best-of-promoted count.*
2. **Promotion ladder priority (blocks Step 1).** Proposed order: exact-base-title+version →
   duration-nearest → fuzzy → richest. Confirm, and decide the duration tiebreak sign (e.g. prefer
   the *shorter* candidate? or strictly nearest absolute?).
3. **`review_required` version-token disagreement — promote or keep parked? (blocks Step 1).**
   Promoting = `best-of-review` (max coverage, accepts version bleed on a tagged basis). Keeping =
   only `best-of-ambiguous` ships in v1. Owner call.
4. **Retroactive delivery (blocks Step 3).** One-shot via the existing batch tool vs a one-off
   reassessment-style invocation. Confirm shape + whether it runs local or worker.
5. **Matcher noise cleanup — same RFC or a follow-on?** Stripping `01 -` track-number prefixes and
   treating non-rendition parentheticals would *prevent* most false ambiguity at the source (and
   shrink the pool before promotion). Proposed: **separate follow-on RFC** so this RFC's promotion
   semantics stay isolated and reviewable. Confirm.

## Acceptance criteria

- On the labelled sample: **best-of precision ≥ the owner-set bar** (proposed ≥ 90%, denominator =
  best-of-promoted count) **and exact-title precision unchanged at ≥ 99%** (regression guard).
- Every previously-`ambiguous`/`review_required` row either promotes to a tagged
  `best-of-*` `matched`/`no_lyrics`, or stays parked **for a recorded reason** in `evidence`.
- **No public schema or response** references or exposes lyric text or its presence (privacy gate,
  unchanged).
- A `best-of-*` `matched` row is superseded by a later `exact-title` match under reassessment
  (replacement guard), and is never laterally swapped to a different best-of candidate.
- All six metrics reported per run with denominators; the promotion-tier breakdown is auditable per
  row from `evidence.promotion`.

## No-go conditions

- The risk-quantification probe (Step 1) shows tier-1 (exact base-title) rarely covers the pool **and**
  best-of precision on the labelled sample sits below the owner bar → **promotion is scoped back to
  tier-1-only** (or shelved) rather than shipped loose.
- Relaxing the boundary reverts any `exact-title` guarantee or lands lyric text/presence in a public
  surface → **design rejected** (privacy + exact-match integrity are non-negotiable).
- A high version-conflict attach rate (metric 5) on real data → **`best-of-review` is withdrawn**,
  leaving only `best-of-ambiguous`.

## Relationship to later work

This RFC widens the corpus the predecessor (`FEAT-lyrics-corpus`) built; it does not touch any
consumer. The viewer (`FEAT-lyrics-viewer`) serves the new coverage transparently (promoted rows are
`matched`). Translation / slang-meme / interpretation / album-level analysis remain separate later
RFCs consuming this corpus. The matcher noise-cleanup follow-on (Open question 5) is the natural next
RFC and would shrink the ambiguous pool at the source.

## Decisions log

Filled in during execution.

| Date | Decision | Step |
|------|----------|------|
| 2026-07-03 | RFC drafted — auto-promote best plausible candidate out of ambiguous/review_required as a tagged `best-of-*` basis; conservative `exact-title` matcher + evidence preserved; no manual UI; no schema change | 0 |
