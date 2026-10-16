# Diagnostic pilot — final results (2026-10-16)

Parent: `docs/rfcs/CHORE-research-model-evaluation.md`, pilot Steps 2–4. This completes the historical pilot. It is diagnostic material for Stage B. It is **not** an acceptance test: `criteria/acceptance-v1.md` was frozen after these notes existed, and a pilot album is development material by definition. Scores below are under the frozen pilot `rubric.md`, not acceptance-v1.

## What ran

| Part | Result |
|---|---|
| GPT generation (2026-10-15) | 7/7 success, one dispatch each (`runs/`) |
| Claude generation, first attempt (2026-10-15) | `claude-opus-5-5` HTTP 429, zero tokens; 9 not run (`runs/`, unchanged) |
| Claude generation, resume (2026-10-16) | 10/10 success, one dispatch each, same input sha256 `9acd15eb…` (`runs-claude-resume-2026-10-16/`, manifest `manifest-claude-resume-2026-10-16.json`) |
| Astra per-sample audits | 7 GPT samples (2026-10-15, unchanged) + 10 Claude samples (2026-10-16, `reviews/v2/runs/astra-review-R??/`) |
| Claude (`claude-opus-5-5`) per-sample audits | all 17 (`reviews/v2/runs/claude-review-R??/`) |
| Comparative calibration | one per reviewer over its own 17 reports (`reviews/v2/runs/{astra,claude}-comparative/`) |

Neither reviewer saw the other's reports, scores or the identity key before both comparatives were frozen. The table below is the first unblinded view.

## Scores (single album, single generation per model)

Astra made 0 score changes in calibration. Claude made 9, each aligning the same defect with the same score, with the evidence recorded. "Astra verdict" and "Claude tier" are the reviewers' own groupings: Claude's tiers A–D overlap by ±5; *excl* = gate-level defects.

| Label | Model | Astra | Claude per-sample → calibrated | Astra verdict | Claude tier | Wall s | Web calls | Chars |
|---|---|---:|---:|---|---|---:|---:|---:|
| R04 | `gpt-6-astra` | 85.5 | 80 → 80 | use-after-fix | A | 288 | 11 | 6,849 |
| R13 | `gpt-6.1-sol` | 82 | 83 → 83 | use-after-fix | A | 230 | 15 | 8,055 |
| R01 | `gpt-6-sol` | 78.5 | 71.5 → 69 | use-after-fix | B | 172 | 16 | 6,471 |
| R06 | `gpt-5.6-sol` | 72.5 | 73.5 → 71 | rework | B | 211 | 16 | 8,365 |
| R15 | `claude-opus-5-5` | 68 | 74 → 71.5 | rework | B | 310 | 36 | 7,136 |
| R09 | `gpt-6-luna` | 69.5 | 66 → 65.5 | rework | C | 82 | 8 | 5,865 |
| R17 | `gpt-5.6-luna` | 65.5 | 67 → 66 | rework | C | 67 | 8 | 5,098 |
| R12 | `claude-opus-5` | 61 | 67.5 → 65 | rework (partial) | C | 224 | 19 | 8,525 |
| R07 | `claude-sonnet-5-5` | 61 | 64.5 → 62 | rework (partial) | C | 330 | 22 | 6,709 |
| R10 | `claude-haiku-5-5` | 57 | 63.5 → 64.5 | rework (partial) | C | 262 | 12 | 5,513 |
| R03 | `gpt-5.6-terra` | 56 | 63 → 63 | rework (partial) | C | 137 | 7 | 4,995 |
| R16 | `claude-sonnet-4-6` | 58.5 | 58 → 58 | rework (partial) | D | 224 | 12 | 6,301 |
| R14 | `claude-opus-4-7` | 56.5 | 59.5 → 59.5 | rework (partial) | D | 392 | 8 | 8,027 |
| R08 | `claude-opus-4-6` | 58 | 49.5 → 49.5 | rework (partial) | excl | 407 | 21 | 9,647 |
| R11 | `claude-sonnet-5` | 44.5 | 49.5 → 49.5 | re-research list | excl | 165 | 14 | 5,972 |
| R05 | `claude-opus-4-8` | 44 | 50.5 → 48 | re-research list | excl | 195 | 9 | 7,268 |
| R02 | `claude-haiku-4-5-20251001` | 34 | 31.5 → 31.5 | re-research list | excl | 225 | 26 | 10,096 |

**Agreement:**
- Spearman ρ between the two reviewers' per-sample totals is **0.90** (n = 17).
- Both put R04 and R13 in a tied top group.
- Both exclude or demote R02, R05 and R11.
- They disagree most on R08: Astra 58, Claude 49.5 and excluded. Claude records a location-less quote and a fabricated failure history for an untried fetch.

**Family pattern:**
- GPT samples averaged 72.8 (Astra) and 72.0 (Claude, per-sample).
- Claude samples averaged 54.2 (Astra) and 56.8 (Claude).
- The Claude reviewer did not rate the Claude family higher. The small family-wise offset, Claude − Astra (GPT −0.8, Claude +2.5), is within either reviewer's stated uncertainty.

This is a **model-plus-harness** observation, not a model ranking. See the confound below.

## Harness confound (material for Stage B)

The two lanes did not see the web the same way.

**Claude CLI lane.**
- `WebFetch` returns text produced by a page-summarisation helper model (`claude-haiku-5-5` appears in every Claude run's model list), not the page itself.
- Both reviewers trace several defects to this layer: attribution reversed in a summary (R15), context and quantities lost (R08, R16), and summary sentences labelled as verified source text.

**Codex lane.**
- Codex `web_search` returns search results and snippets.

**Consequence.**
- Recurring defects 2 and 5 below cannot be split cleanly into model versus harness failures.
- The Claude reviewer recommends unifying or at least recording the retrieval mode in the next round. acceptance-v1 §3 already requires per-run preservation of what the producer actually received.

## Recurring defects (both reviewers, independently)

| Defect | Classification (Astra / Claude) |
|---|---|
| Journalist narration promoted to direct speech (AnOther's "two years / 300+ songs"; "hit a wall") | (b) model / mostly (b), prompt contributes: source-level labels, no required original excerpt |
| Search or summary text labelled as source-verified, or attributed to a specific outlet | (b) with prompt as secondary factor / (c) model + harness mixed |
| Already-retrieved interviews under-read (family vocals per track, the unused Mercury recording, editing principle), then declared absent | (b) / (b) with harness contribution |
| Role fields narrowed or substituted; a single encyclopedia used for credits | (b) / (a): §6 "do not re-survey reference credits" reads as a signal to skip distributor rows |
| Spurious conflicts between statements of different scope; exclusive statements ("only feature", "90%") not checked against metadata | (b) with prompt as secondary factor / (a) leaning (c) |
| Table, aggregate and coverage numerators inconsistent | (b) / (a) leaning (c): "substantive evidence" undefined |
| Reviews or ratings used as factual evidence despite the explicit ban | (b) / (b) |
| Length target exceeded without a stated reason; tables' inclusion in the count unclear | (a) / (c) |

Neither reviewer found a repeated, established fabrication of sources or quotes, or a false listening claim.

## Prompt amendments proposed for the next bounded round

The two reviewers converge on **consolidating and defining rather than adding rules**:

1. **Tie provenance labels to what was actually received in this run.** "Source-verified" requires retrieved body text plus a minimal original-language excerpt. Search snippets and summarised fetches are named as such. *Untried* is a separate status. (Astra A1/A2, Claude A-1/A-5/A-10.)
2. **Label the speaker per sentence, not per source.** Numbers, dates and durations always carry their speaker. (Astra A1, Claude A-2.)
3. **Re-read retrieved sources before declaring a gap,** with a second extraction by track and person. (Astra A3, Claude A-8.)
4. **Preserve the original role string and edition.** By default, record one distributor's per-track rows when no booklet exists. "Conflict" requires the same object, role, time and scope. (Astra A4, Claude A-3/A-4/A-15.)
5. **Define the coverage numerator** as a list of track IDs. (Astra A5, Claude A-9.)
6. **Scope the length target to the core prose only,** and remove ritual repetition. (Astra A6, Claude A-12.)
7. **Make the creator's title/concept explanation a general question,** and make the signed statement and engineer interviews path types rather than named outlets. (Claude A-6/A-7.)

Both reviewers explicitly reject turning this album's facts (Apple statement, AnOther title answer, GRAMMY family-vocal answer, Mercury, C418, named services) into prompt rules. Those facts are regression checks only.

## Limits

- One album, one generation per model. Claude CLI 2.1.301 for the resume, versus 2.1.300 in the first attempt. Source availability drifted by one day between lanes.
- Both reviewers fetched through tools that summarise pages. Per-sample precision denominators are not comparable across samples.
- Blinding to producer family is limited: trace structure differs by harness. Notes carried no identity strings, and harness error strings in traces were redacted (`reviews/v2/build-report.json`).
- The production research poller uses the Claude CLI with a different prompt (`album_research_v2`). Nothing here measures production quality or authorises a change. Production adoption remains separate work.
