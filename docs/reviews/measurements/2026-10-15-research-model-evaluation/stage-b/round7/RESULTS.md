# Stage B round 7 — stopped by the owner (2026-10-20)

Scope: `ROUND.md`. The owner confirmed it before any dispatch, with P6 as the base. It was frozen and pushed as `19d93c0` before the first generation. If the merge rebases that commit, the rewritten sha is recorded in the PR.

## Verdict: none. The round was stopped before review.

During the fourth generation the owner asked whether this many rounds were worth it. The orchestrator answered that the returns had become small:
- rounds 4–7 each targeted one rare slip (the round-7 target occurred in 4 of 18 earlier outputs);
- 3 runs per cell cannot separate one such event from chance;
- every round reuses one development album;
- round 6 alone used about 4 M input tokens.

**The owner chose to stop round 7 and move to Stage C (2026-10-20, "지금 멈추고 Stage C로").** The lane was stopped by PID. Nothing was reviewed, no labels were drawn, and no verdict can be read from what follows.

## What ran

| Part | Result |
|---|---|
| Fable review of the draft | 9 findings, no blocker, all applied (ROUND.md header) |
| Owner confirmation | 2026-10-20, P6 as base, before any dispatch |
| Fidelity check (`freeze-check/`) | Astra and Claude both CONFIRM FREEZE; P7 = rc (`b7c2aec3…`) |
| Reference re-check (`reference/recheck.json`) | 2026-10-20T10:44Z, 10/10 credit lines byte-identical |
| Generations (`runs/`) | 3 of 6 success (P7 r1, P0 r1, P0 r2), each with 0 hook events and tools exactly WebSearch + WebFetch. **P7 r2 was interrupted by the stop**: its `metadata.json` still reads `running` and there is no `output.md`. P0 r3 and P7 r3 were never dispatched. |
| Review, comparative, tally | not run |

Descriptive only, unreviewed, and not a comparison: lengths P7 r1 7,032, P0 r1 7,491, P0 r2 8,179 characters. `summary_quote_scan.py --runs` finds 0 search-summary-only quotes in all three.

## Carried forward

- P6 remains the latest candidate that met every round condition except one confirmed single FAIL. P5 is the last candidate that advanced under a round rule. Which one enters Stage C is the owner's decision in the Stage C design.
- Change 1 (P7) is frozen and untested. It can be reconsidered if Stage C shows the same attribution slip on held-out albums.

## Publication

Every record embedding the Gemini Rights catalog block had its owner-collection line redacted, as listed in `PUBLICATION-REDACTIONS.json` with the original hashes (4 files). A token scan then found 0 hits.
