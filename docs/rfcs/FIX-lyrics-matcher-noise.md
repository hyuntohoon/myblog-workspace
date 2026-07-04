# FIX-lyrics-matcher-noise: matcher false-ambiguity source fixes (best-of OQ5 follow-on)

- **Status**: in-progress
- **Owner**: 박지훈
- **Created**: 2026-07-04
- **Plan row**: `plan.md` → FIX-lyrics-matcher-noise
- **Predecessor**: `docs/archive/done/rfcs/FEAT-lyrics-best-of-promotion.md` (OQ5, owner decision 2026-07-03: "matcher source fixes = separate follow-on RFC")

---

## Goal

The conservative lyrics matcher stops manufacturing **false ambiguity** out of LRCLIB
crowd-data noise, so rows resolve as genuine `exact-title` matches **at the source**
instead of parking and needing the best-of promotion layer to rescue them. Three fixes,
all inside `decide_match`'s candidate canonicalization / grouping / representative
selection:

1. **Track-number prefix strip** — a crowd upload titled `01 - Come Back to Earth`
   no longer splits into its own plausible group.
2. **Non-rendition parenthetical strip** — `Song (From "Movie")`, `Song (feat. X)`
   retitles no longer split groups (rendition parentheticals like `(Live)` keep their
   full version-token semantics and still park on mismatch).
3. **Version-agreeing representative** — the per-group representative prefers a
   candidate whose version tokens agree with the catalog track (then exact-kind, then
   richest lyric) instead of `_richest`'s lyric-richness-only sort.

Measured targets: the Step-1 probe classified refetch-still-ambiguous rows as
**duplicate_noise 2,673 vs genuine 68 (≈40:1)** — most of that inflow class should now
resolve `matched`; and the **26 review_required rows** parked after the best-of backfill
(the `no_tier1_candidate` class) get a real chance to resolve.

## Non-goals

- No schema change, no new `match_status` values, no change to public exposure
  (`track_lyrics` stays owner-only).
- No relaxation of the artist-identity gate, the ±2s duration tolerance, or the 0.80
  fuzzy threshold — this RFC removes *noise*, it does not loosen *evidence*.
- No change to the best-of promotion layer (`lyrics_promote.py` tiers, bases, ladder,
  `evidence.promotion`) — already-promoted `best-of-*` rows upgrade to `exact-title`
  through the **existing** reassessment supersession (ladder rung 3 > 2), not through
  this RFC.
- Not opening gated tiers 2–4 (best-of OQ2 stays closed; residual was 26 rows).
- No retroactive rewrite of pre-existing `exact-title` rows (regression guard, same as
  the best-of RFC: the 7,9xx exact-title population must be untouched except where the
  new matcher agrees exactly).

## Current state

Verified 2026-07-04 against `myblog_worker` main (`worker/service/lyrics_matcher.py`):

- `decide_match` collapses near-duplicate candidates by grouping on
  `(TitleNormalizer.normalize(artist), _strip_version_tokens(normalized title))`
  (`lyrics_matcher.py:304-307`). `len(reps) > 1` ⇒ `ambiguous` / `multiple_plausible`
  (`lyrics_matcher.py:318-327`).
- **Prefix noise**: `01 - Title` normalizes to `01 title` — the numeric prefix survives
  both `TitleNormalizer.normalize` (digits are alnum) and `_strip_version_tokens` (not a
  version token) ⇒ second group ⇒ false ambiguity. When the prefixed upload is the
  *only* candidate it lands `fuzzy` ⇒ `review_required` / `title_fuzzy_only`.
- **Parenthetical noise**: `normalize` drops the paren *characters* but keeps the words
  (`Song (From "Movie")` → `song from movie`); non-rendition words are not in
  `_VERSION_TOKENS`, so the stripped title differs ⇒ separate group. Feature credits
  (`feat` deliberately not a version token) behave the same.
- **Representative**: `_richest` (`lyrics_matcher.py:309-314`) sorts by
  `(bool(synced), bool(plain))` only. A group holding both a version-agreeing candidate
  and a richer version-mismatched sibling elects the mismatched one ⇒
  `review_required` / `version_token_mismatch` despite an agreeing sibling existing.
  Probe measure (d): 8/13 review `version_token_mismatch` rows had an agreeing sibling
  (61.5% — denominator: review_required rows with reason `version_token_mismatch` in
  the 2,783-row probe pool).
- The best-of layer (`worker/service/lyrics_promote.py::_plausible`) re-derives its
  candidate set through the **same shared helpers** (`_strip_version_tokens`,
  `_artist_identity_ok`, `duration_matches`) — canonicalization changes propagate to
  tier-1 automatically.
- Post-backfill residual (prod, 2026-07-04): **26 review_required** parked
  (`no_tier1_candidate`) + **18 LRCLIB-transient ambiguous**; reassessment
  (`lyrics_reassessment`, now 15-min cadence, ws #512) re-selects unresolved +
  `best-of-*` rows, LIMIT 150, unresolved-first.
- `MATCHER_VERSION = "step2-v2"` (`lyrics_matcher.py:41`); evidence rows record it.

## Target state

- A new candidate-title canonicalization step `_strip_noise(raw_title)` applied
  **before** `normalize`/`_strip_version_tokens` in `decide_match`'s plausibility +
  grouping pipeline (and, via the shared helper path, in `promote_best._plausible`):
  - strips a leading track-number prefix matching `^\d{1,2}\s*[-–—.]\s+` **only when
    non-empty text remains** (`1999`, `7 rings` untouched — no separator);
  - strips `(...)` / `[...]` segments containing **no version token** (so `(Live)`,
    `(Remastered 2019)` survive into version-token logic and still gate; `(feat. X)`,
    `(From "...")` are dropped from the *base title* only — `extract_version_tokens`
    keeps reading the **full raw title**, so rendition semantics are unchanged).
- Applied **symmetrically to the catalog track title** (OQ2) so `Song (feat. X)` in the
  catalog matches a plain `Song` upload and vice versa.
- Group representative: sort key becomes
  `(version_agrees_with_track, kind == "exact", bool(synced), bool(plain))` — the
  version-agreeing exact sibling wins; lyric richness is the tiebreak, not the criterion.
- `MATCHER_VERSION` bumped (`step3-v1`, OQ4) so every row records which logic produced
  it; evidence gains a `title_noise` marker when a strip actually fired (reconstructable,
  same philosophy as `evidence.promotion`).
- Genuine ambiguity (two distinct base titles / artists after de-noising) still parks —
  the probe must show the 68 genuine-class rows stay `ambiguous`.

## Steps

Step 1 is branch-local (no merge — the matcher is live-wired, so landing the code IS
the rollout); the merge happens in Step 2 after the probe gates pass.

### Step 1 — matcher fixes + unit tests + read-only probe (worker branch + workspace tools, NOT merged)

- Implement `_strip_noise` + the representative sort change in
  `worker/service/lyrics_matcher.py`; bump `MATCHER_VERSION`.
- Unit tests: prefix collapse (multi-candidate → single group), prefix-only candidate →
  `matched` not `title_fuzzy_only`, non-rendition parenthetical collapse, feat-credit
  symmetry (catalog-side + candidate-side), rendition parenthetical still parks,
  version-agreeing representative beats richer mismatched sibling, genuine two-song
  ambiguity preserved, KR titles, `1999`-style numeric titles untouched.
- Read-only probe (reuse the sanctioned `tools/lyrics_bestof_probe.py` pattern —
  SELECT-only pool + in-memory replay + JSONL checkpoint + retry passes, writes
  nothing): replay **old vs new** `decide_match` over (a) the 26 + 18 residual rows and
  (b) the refetch pool sample, reporting:
  - (i) outcome-delta matrix (ambiguous→matched / review→matched / unchanged / newly
    ambiguous — the last must be ≈0);
  - (ii) disagreement on rows the old matcher already resolved `matched`/`exact-title`
    (must be 0 — regression guard);
  - (iii) genuine-ambiguity retention: the probe's `genuine` class (68 rows) stays
    parked;
  - (iv) **labelled precision sample** over rows whose outcome *changed*: stratified
    n≥40 (EN/KR + prefix/parenthetical/representative classes), gate **≥90%**
    (denominator: the sampled changed-outcome rows) — OQ3.

**Verification**: full worker `pytest` green + probe report quoted in the PR body
(every measure with its denominator).

**Rollback**: branch not merged; nothing deployed.

---

### Step 2 — merge + prod rollout + smoke (worker merge, gated on Step 1 results)

- Merge the Step-1 worker branch (this is the enable — next `lyrics_incremental` /
  `lyrics_reassessment` runs use the new matcher).
- Prod smoke via DB-state evidence (prod `LOG_LEVEL=WARNING`): after ≥1 reassessment
  cycle — status counts move in the expected direction (ambiguous/review ↓, matched ↑,
  deltas reconcile exactly), new rows carry the bumped `matcher_version`, pre-existing
  `exact-title` count untouched, 0 `matched` rows with empty lyric bodies.

**Verification**: prod smoke result quoted in PR comment (counts before/after with
exact deltas).

**Rollback**: revert the worker merge (single PR); rows written by the new version are
identifiable via `matcher_version` and re-evaluated by reassessment on revert.

---

### Step 3 — targeted residual re-eval + close-out measurement (workspace, local one-shot, optional)

- The 15-min reassessment (LIMIT 150) will reach the 26 + 18 residual rows eventually
  (~10k `not_found` share the unresolved pool); if the owner wants same-day evidence,
  run a **pool-scoped local one-shot** (reuse the `tools/lyrics_bestof_backfill.py`
  driver shape: pre-run snapshot, the live `run_eval_batch` path verbatim, scoped to
  the 44 residual track_ids).
- Close-out: report how many of the 26 review rows resolved (denominator: the 26 parked
  as of 2026-07-04) + the week-1 inflow ambiguous rate vs the pre-fix 40:1 baseline.

**Verification**: per-row outcome table for the 44 + counts quoted in plan.md close-out.

**Rollback**: pre-run snapshot (same mechanism as the best-of backfill).

---

## Open questions

All resolved 2026-07-04 (owner: "추천하는걸로 다하고" — recommendations adopted wholesale):

1. **OQ1 — strip scope**: ~~group-key only vs full pipeline~~ → **full comparison
   pipeline** (needed to touch the 26 rows; precision guarded by the Step-1 probe +
   labelled gate).
2. **OQ2 — symmetric catalog-side strip**: ~~candidate-only vs both sides~~ →
   **both sides** (feat-credit parity cuts both ways).
3. **OQ3 — precision gate**: **≥90%** on a stratified n≥40 labelled sample of
   *changed-outcome* rows (denominator: the sampled changed-outcome rows). Merge gate
   for Step 2.
4. **OQ4 — `MATCHER_VERSION` value**: **`step3-v1`**.

## Decisions log

| Date | Decision | Step |
|------|----------|------|
| 2026-07-04 | RFC drafted from best-of OQ5 (owner 2026-07-03: source fixes = separate follow-on RFC) — 3 fixes: `01 -` prefix strip, non-rendition parenthetical strip, `_richest`→version-agreeing representative; targets the 26 parked review rows + the ≈40:1 duplicate-noise inflow | 0 |
| 2026-07-04 | Owner decisions (explicit in-session: "추천하는걸로 다하고 승격 및 모든 step 다 작업하고 머지하자"): OQ1 **full comparison pipeline**, OQ2 **symmetric both-side strip**, OQ3 gate **≥90%** (changed-outcome sample n≥40), OQ4 `step3-v1`. Status draft → **accepted** → **in-progress** (single-session all-steps run + merge pre-approved — rule #4/#5/#7 explicit opt-in) | 0 |
