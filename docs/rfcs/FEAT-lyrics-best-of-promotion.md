# FEAT-lyrics-best-of-promotion: auto-promote the best plausible candidate out of `ambiguous` / `review_required`

- **Status**: in-progress (Step 1 started 2026-07-03, owner-approved in-session)
- **Owner**: 박지훈
- **Created**: 2026-07-03
- **Plan row**: `plan.md` → FEAT-lyrics-best-of-promotion
- **Predecessor**: `FEAT-lyrics-corpus` (Status: done) — builds the conservative matcher + corpus this RFC widens.

---

## Goal

After this RFC, a catalog track that the conservative matcher parks as `ambiguous` or
`review_required` (because evidence cannot cleanly separate the candidates, or the single
candidate fails the version-token / fuzzy bar) **no longer sits without a lyric when one candidate
is safely separable**. The corpus job **automatically promotes the single best plausible candidate**
(v1: only via exact base-title + version-token agreement — see the ladder) and attaches its lyric as
a distinctly-tagged `matched` row — `match_basis = best-of-ambiguous` / `best-of-review` — so coverage
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
  present), pick one candidate and return a `matched` outcome carrying its lyric, tagged so it is
  never confused with an exact match. **v1 promotes on tier 1 only**; tiers 2–4 are specified for
  completeness but **gated off** until the Step-1 probe + labelled sample justify opening them
  (Open questions):
  0. **Body filter (precondition, not a tiebreak)** — candidates flagged **instrumental** or
     carrying no lyric body (`plain_lyrics`/`synced_lyrics` both empty) are excluded up front. If
     no candidate survives: all-instrumental → the row resolves to `no_lyrics` (mirroring
     `decide_match`'s `instrumental_or_empty`); otherwise it **stays parked** with the attempt
     recorded in `evidence.promotion` (`reason: "no_body_candidate"`). A promoted `matched` row
     therefore always carries non-empty lyric text — never a viewer-invisible empty match.
  1. **Exact base-title agreement + version-token agreement** (the only tier live in v1) — the
     candidate whose stripped base title equals the catalog's, whose duration is within tolerance,
     and whose version tokens agree with the catalog's; ties broken by richest lyric
     (`synced > plain`). (Resolves the Come Back to Earth case to the clean `Come Back to Earth`.)
  2. *(gated)* **Duration-nearest** among the rest (smallest `|catalog − candidate|`). NB every
     plausible candidate already passed the ±2 s duration gate, so this tier discriminates inside a
     ≤4 s window — near-arbitrary for genuine two-song ambiguity, which is why it ships gated.
  3. *(gated)* **Highest title similarity** (fuzzy ratio on stripped base).
  4. *(gated)* **Richest lyric** (`synced > plain`) as the final tiebreak.
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
- **Version safety, scoped**: under the v1 tier-1-only ladder **every promotion carries
  version-token agreement** — including `best-of-review`, which in v1 fires only when the candidate
  set contains a version-agreeing sibling of the representative that failed the gate
  (`decide_match` picks its group representative by richest-lyric, not version agreement, so such
  siblings exist — see Open question 5). Attaching a candidate that itself **disagrees** on version
  tokens becomes possible only if the gated tiers open; it stays an accepted, tagged relaxation
  recorded in `evidence.promotion` + the distinct basis, guarded by metric 5. No `exact-title` row
  loses its guarantee either way.
- **Replacement / reassessment**: a best-of `matched` row **remains a reassessment target** (LRCLIB
  growing may later yield an `exact-title` match that legitimately supersedes it). This does **not**
  hold for free: the current selection (`lyrics_reassessment_service.py:_fetch_unresolved_tracks`)
  selects only `not_found`/`ambiguous`/`review_required` — a promoted row would leave the pool
  forever and the promised supersession could never occur. Step 2 therefore **widens the selection**
  (`OR (tl.match_status = 'matched' AND tl.evidence->>'match_basis' LIKE 'best-of-%')`), ordered so
  unresolved rows keep rotation priority over best-of re-checks (a best-of row already carries a
  usable lyric; `not_found` recovery is the scarcer win). The replacement guard enforces "strictly
  stronger basis only", so reassessment can upgrade best-of → exact-title but never best-of → a
  different best-of (no lateral churn).
- **Consistency invariant made basis-aware (required, or best-of writes are blocked)**:
  `run_eval_batch` currently refuses any `matched` outcome with `version_agrees=False` as a matcher
  bug (`lyrics_eval_core.py:121`, counted `consistency_errors`, row never written). Under the v1
  tier-1-only ladder every promotion agrees on version, but Step 2 must still make the invariant
  basis-aware (`matched` + `exact-title` ⇒ `version_agrees=True`; `matched` + `best-of-*` ⇒
  `evidence.promotion` present, version agreement per the tier that fired) so that opening the
  gated tiers later cannot silently zero out `best-of-review` writes as consistency errors.
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

- **Risk-quantification probe (run first, gates the ladder)**: over the **live prod ambiguous +
  review pool**. NB this is **not a DB-only query** — stored `evidence` keeps only ≤3 candidate
  previews and no bodies, so the probe **re-fetches LRCLIB candidates** for the pool (~2,783 rows ≈
  ~19 min at the predecessor's ~2.5 req/s ceiling; reuse the `tools/lyrics_batch_api.py` fetch
  shape — memory `reference-lrclib-bulk-api-ops`). It writes nothing. Measure (a) the **tier-1 hit
  rate** — the fraction whose candidate set contains an exact stripped-base-title,
  version-agreeing, body-carrying candidate (the fraction v1 can promote at all), (b) the
  **duration gap** distribution of the tier-1 pick, (c) how many ambiguous sets are *genuine*
  two-distinct-songs ambiguity vs duplicate-noise (Come Back to Earth style), (d) for
  `review_required` rows, how many carry a **version-agreeing sibling** (the class parked by
  `decide_match`'s richest-first representative choice — the natural target of the Open-question-5
  source fix), and (e) the residual pool the gated tiers 2–4 *would* cover — the evidence base for
  (not) opening them. Denominators stated on every line. If the tier-1 hit rate is low, the ladder /
  thresholds are revised **before** any write.
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

Four coordinated changes, all in the worker:

1. Invoke `promote_best` inside `run_eval_batch` immediately after `decide_match` (only when the
   outcome is `ambiguous`/`review_required`), **before** the consistency check and the writer.
2. Make the consistency invariant **basis-aware** (Target state) — without this, `run_eval_batch`
   refuses `matched` + `version_agrees=False` rows, and `best-of-review` writes would silently die
   as `consistency_errors` the day the gated tiers open.
3. Slot `best-of-*` into `_BASIS_STRENGTH` (above `fuzzy-title`, below `exact-title`) and extend
   `should_replace`'s tests.
4. **Widen the reassessment selection** to re-select `best-of-*` `matched` rows (Target state) so
   the promised exact-title supersession can actually occur, with unresolved rows keeping rotation
   priority.

Extend `new_metrics` with `promoted_ambiguous`, `promoted_review`, and per-criterion counters (all
with explicit denominators). Because the loop is shared, this single change makes **both** the
incremental job (Step 3 of the predecessor) and the reassessment job (Step 4) promote forward — and
any future backfill reuses it.

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
   disagreed with the catalog's. **Zero by construction under the v1 tier-1-only ladder** (tier 1
   requires agreement); a non-zero value in v1 is a bug. Becomes a live, audited guard only if the
   gated tiers open — there, a high rate triggers a direction recheck. *Denominator =
   `best-of-review` count.*
6. **Replacement-guard behavior** — best-of rows superseded by a later `exact-title` match during
   reassessment, and best-of→best-others refused. *Denominator = reassessed best-of rows.*

## Risks

- **Genuine (non-noise) ambiguity promoted wrong** — some `ambiguous` sets really are two distinct
  songs at near-equal duration; the ladder's tier-1 cannot always tell. Mitigation: tier-1 (exact
  base-title) first; the risk-quantification probe (Step 1) measures how often tier-1 covers before
  any write; wrong promotions are fully reconstructable from `evidence.promotion` and reversible.
- **Version-safety relaxation** (`best-of-review`) — in v1 this risk is **structurally absent**
  (tier-1 requires version agreement; a review row promotes only via an agreeing sibling). It
  materializes only if the gated tiers open; there, the mitigation is the distinct basis + recorded
  disagreement, `exact-title` guarantees untouched, and metric 5 as the recheck trigger.
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
   **Decided 2026-07-03 (owner): ≥ 90%.**
2. **Gated tiers 2–4 — open at all, and on what evidence? (decided post-probe, not pre-Step-1).**
   v1 ships tier-1-only. The Step-1 probe reports the residual pool tiers 2–4 would cover (measure
   e); the owner decides whether that coverage justifies opening any of them — the duration
   tiebreak sign (nearest-absolute vs prefer-shorter) is decided then too. Default: **stay
   closed**.
3. **`review_required` participation in v1 (blocks Step 1).** Under tier-1-only, a review row
   promotes only via a **version-agreeing sibling** — the version-bleed concern applies only to
   the gated tiers. Proposed: **include** `review_required` in v1 (`best-of-review`, safe by
   construction). Alternative: ambiguous-only. Owner call.
   **Decided 2026-07-03 (owner): include `review_required` in v1.**
4. **Retroactive delivery (blocks Step 3).** One-shot via the existing batch tool vs a one-off
   reassessment-style invocation. Confirm shape + whether it runs local or worker.
   **Decided 2026-07-03 (owner): local one-shot** (`tools/lyrics_batch_api.py` shape, resumable) —
   the ~19-min pool does not fit the 120 s worker Lambda budget; matches the predecessor's backfill.
5. **Matcher noise cleanup — same RFC or a follow-on?** Two source fixes would *prevent* false
   parking before any promotion: (a) stripping `01 -` track-number prefixes + non-rendition
   parentheticals from the group key (shrinks false ambiguity); (b) making `decide_match`'s group
   representative prefer **version-agreeing** candidates over richest-first (`_richest`) — that
   class currently parks as `review_required` and would become a **full-strength `exact-title`
   match** at the source, strictly better than a best-of tag (probe measure d sizes it). Proposed:
   **separate follow-on RFC** so this RFC's promotion semantics stay isolated and reviewable.
   Confirm.
   **Decided 2026-07-03 (owner): separate follow-on RFC.**

## Acceptance criteria

- On the labelled sample: **best-of precision ≥ the owner-set bar** (proposed ≥ 90%, denominator =
  best-of-promoted count) **and exact-title precision unchanged at ≥ 99%** (regression guard).
- Every previously-`ambiguous`/`review_required` row either promotes to a tagged
  `best-of-*` `matched`/`no_lyrics`, or stays parked **for a recorded reason** in `evidence`.
- **No public schema or response** references or exposes lyric text or its presence (privacy gate,
  unchanged).
- A `best-of-*` `matched` row is **re-selected by the widened reassessment query** and superseded
  by a later `exact-title` match under the replacement guard, and is never laterally swapped to a
  different best-of candidate.
- A promoted `matched` row always carries **non-empty lyric text** (body filter is a precondition);
  best-of rows written with `version_agrees=False` are impossible in v1 (tier-1 requires
  agreement + the basis-aware invariant).
- All six metrics reported per run with denominators; the promotion-tier breakdown is auditable per
  row from `evidence.promotion`.

## No-go conditions

- The risk-quantification probe (Step 1) shows tier-1 (exact base-title) covers too little of the
  pool to be worth shipping, **or** best-of precision on the labelled sample sits below the owner
  bar → the RFC is **shelved**. v1 is already tier-1-only — there is no looser fallback to scope
  back to; the gated tiers open only on positive probe evidence, never as a rescue for a weak
  tier 1.
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
| 2026-07-03 | Review revisions (pre-accept, code-audited): v1 scoped to **tier-1-only** (tiers 2–4 gated on probe evidence — tier-2's ≤4 s window is near-arbitrary for genuine ambiguity); **body filter** made a promotion precondition (no viewer-invisible empty matches); Step 2 gains two mandatory changes that were RFC-internal contradictions — the eval-loop **consistency invariant must go basis-aware** (`lyrics_eval_core.py:121` would refuse best-of-review writes) and the **reassessment selection must widen** to re-select `best-of-*` rows (current SQL selects unresolved only → promoted rows would never be superseded); Step-1 probe clarified as an LRCLIB re-fetch pass (+ measures d: version-agreeing-sibling class, e: gated-tier residual); `_richest` representative fix registered under OQ5 follow-on | 0 |
| 2026-07-03 | Owner decisions: OQ1 precision bar **≥ 90%**; OQ3 **include `review_required`** in v1; OQ4 retroactive backfill = **local one-shot** (batch-tool shape); OQ5 matcher source fixes = **separate follow-on RFC**. OQ2 (gated tiers 2–4) stays open by design — decided post-probe | 0 |
| 2026-07-03 | Status draft → **accepted** (explicit owner approval in-session: "승격"). Next: Step 1 (`promote_best` core + risk-quant probe + labelled sample, worker + offline) | 0 |
| 2026-07-03 | Status accepted → **in-progress** (explicit owner approval: "시작하고 워커 늘려서 시간 줄여보자") — Step 1 begun; probe to run at raised LRCLIB concurrency (~30, the known throttle ceiling) with an end-of-run retry pass for transient skips, targeting <15 min instead of ~19 | 1 |
| 2026-07-03 | **Step 1 probe complete** (read-only, 2,783-row pool, 9.5 min @ 40-concurrency + 2 retry passes, 22 unresolved skips). `promote_best` core landed on the worker (`f4dc42d`, `worker/service/lyrics_promote.py` + 14 unit tests incl. the Come Back to Earth 3-candidate → clean-title case; full worker `pytest` 262 passed / 34 skipped). Results (every denominator stated): **(a) tier-1 hit rate 2629/2783 = 94.4%** (of still-parked 94.7%; ambiguous 95.3%, review_required 23.5%) — strong; **(b) duration gap** of the pick: 2063 ≤0.5s, 557 ≤1.0s, 8 ≤1.5–2.0s → 98.0% within 1 s, picks are tight; **(c) ambiguity class** among refetch-still-ambiguous: duplicate_noise 2673 vs genuine 68 (≈40:1) — the pool is overwhelmingly noisy duplicates, not two distinct songs, so tier-1 is the right v1 scope; **(d) review_required version-agreeing siblings** promoted via tier-1: 8/34 (23.5%), of which 8/13 version_token_mismatch (61.5%) — most review rows lack an agreeing sibling and stay parked for the OQ5 follow-on, as expected; **(e) residual after v1: 26 rows parked** (all `no_tier1_candidate`, all carry a body candidate so tiers 2–4 *could* pick them — but 26/~2.8k is not worth opening the gated tiers; OQ2 default "stay closed" confirmed). Pool drift 8 (0.3%, resolved `matched` on fresh fetch → normal re-eval, not best-of); resolved_no_lyrics 120; lyric_kind of promotions synced 2569 / plain 60. **Labelled-sample precision audit**: stratified random 48 (EN 29 / KR 19 / review 5; synced 45 / plain 3) → **48/48 correct = 100%**, comfortably above the 90% gate (OQ1). Per-row audit sample + bodies at `tools/out/bestof_probe_audit_sample.json`; probe script `tools/lyrics_bestof_probe.py`; aggregate `tools/out/bestof_probe_report.json` + per-row checkpoint `tools/out/bestof_probe_checkpoint.jsonl` (gitignored). **Step 1 verification complete; `promote_best` remains unused until Step 2.** Next: Step 2 (integrate into `run_eval_batch` + basis-aware consistency invariant + `_BASIS_STRENGTH` slot + widened reassessment selection) — separate session per hard rule #4. | 1 |
| 2026-07-03 | **Step 2 implemented** (worker `92c9ed8`, explicit owner go "step2 go") — all four coordinated changes: (1) `run_eval_batch` invokes `promote_best` after `decide_match` on `ambiguous`/`review_required` only, before the invariant + writer, reusing the same in-memory candidates (no second LRCLIB fetch); (2) consistency invariant basis-aware (`_consistency_ok`: exact-title ⇒ version agreement, `best-of-*` ⇒ `evidence.promotion` present — a stray best-of `matched` without provenance is refused); (3) ladder reshuffled to integer rungs `{None:0, fuzzy-title:1, best-of-ambiguous:2, best-of-review:2, exact-title:3, mb-recording:4, isrc:5}` — both best-of bases share rung 2 so strict-`>` gives exact-supersedes-best-of / lateral-refusal / never-displaces-exact for free; (4) reassessment selection widened (`OR matched AND match_basis LIKE 'best-of-%'`) with unresolved-first `CASE` ordering. Metrics: `promoted_ambiguous` / `promoted_review` / `promotion_parked` / `promotion_criteria` per-criterion map. 13 new tests (promotion-through-the-loop incl. Come Back to Earth end-to-end, review-sibling path, stray-best-of refusal, best-of ladder, widened-SQL assertion); full worker `pytest` 275 passed / 34 skipped. **Known wrinkle (accepted)**: a re-selected best-of row whose re-check yields the same-strength outcome is `guard_kept` without an `updated_at` bump, so the best-of tier itself doesn't rotate — unreachable in practice while the unresolved pool (~10k `not_found`) dominates the LIMIT-150 selection, and self-correcting on supersession. Prod smoke pending post-merge (DB-state evidence — prod `LOG_LEVEL=WARNING`). Next: Step 3 (retroactive local one-shot backfill, OQ4) — separate session per hard rule #4. | 2 |
