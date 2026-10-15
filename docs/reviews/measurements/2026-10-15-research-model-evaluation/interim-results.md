# Interim result: revised research prompt, 2026-10-15

**Incomplete cross-provider experiment.** All 7 catalog-listed visible GPT models completed one research generation each. The first included Claude call returned account-level HTTP 429 before any generation/search tokens; the remaining 9 included Claude models were not dispatched. Claude's independent review is pending the same external limit. The announced reset is **2026-10-16 02:40 Asia/Seoul**. Two Fable models were excluded by owner instruction because they require separately billed credits.

The GPT-6 Astra audits of all 7 successful anonymous outputs are complete. The individual scores below are reviewer judgments under the frozen rubric, not observed human usefulness, a factual-precision percentage or a stable model ranking. Producer identities remain in the separate key; future Claude receives the unchanged blind packet, not these judgments.

| Anonymous sample | Astra individual score /100 | Wall seconds | Output characters |
|---|---:|---:|---:|
| R04 | 85.5 | 287.947 | 6,849 |
| R13 | 82 | 229.803 | 8,055 |
| R01 | 78.5 | 171.831 | 6,471 |
| R06 | 72.5 | 210.863 | 8,365 |
| R09 | 69.5 | 82.410 | 5,865 |
| R17 | 65.5 | 66.939 | 5,098 |
| R03 | 56 | 136.533 | 4,995 |

Generation-process time sums to 1,186.326 seconds. This is one run per model, with different query trajectories and cached scaffolding. Treat latency as an observation, not a benchmark distribution. Token usage includes cached agent context and is not a subscription bill. Requested model IDs are pinned; Codex JSON did not expose resolved model identity. No orchestration fallback or duplicate generation occurred. Provider search tools/harnesses differ.

## Source-supported findings

- Clear improvements appeared across several outputs: named artist statements were used; title origin was sought directly; family-vocal inclusion and discarded recording were separated; intent was kept apart from achieved effect; game-disk trivia and unsupported generational theses mostly disappeared.
- Improvement was uneven. Several outputs still promoted AnOther journalist narration about two years / more than 300 songs / ten tracks into direct artist speech. Finding the original article did not guarantee attribution accuracy.
- R13 and R04 each reported 6/10 substantive track coverage while their own tables support seven named tracks. R01's 7/10 arithmetic was correct. Coverage should be generated from the track/evidence ledger rather than prose counting.
- Reviewers found edition mismatches or inadequately disclosed clean/other-ID metadata, role narrowing such as Written-By → lyrics/composition, and Producer [Additional] → co-production. Do not treat every credit as changed simply because editions differ; preserve actual role and scope.
- Bibliographic author/date errors and mismatched claim/source IDs survived explicit provenance instructions.
- Relevant retrieved content still went unused, including discarded Mercury vocals, prior-family-collaboration continuity, and concrete writing/editing decisions. This is extraction/selection failure, not necessarily missing search.
- All notes are shorter than the historical supplied note (10,199 characters), but lower length did not imply higher quality. Total length spans 4,995–8,365 characters; body and appendix must be evaluated separately.
- No fabricated listening was established. A reviewer failing to reproduce a page's credit section was not treated as proof that the generator lied; native traces were consulted and their limits documented.

## Provisional disposition

R04 is the current anonymous GPT quality candidate, with corrections required. Its untouched output is preserved as `provisional-gpt-quality-leader-uncorrected.md`. There is **no overall Claude/GPT selection** and no production adoption. Final Astra comparative calibration is complete in `reviews/astra-comparative-feedback.md` and retains all original scores. Independent Claude feedback and disagreement reconciliation remain pending.

## Resume boundary

After Claude's account reset, resume only the missing Claude generations and independent Claude review using the same frozen generation input and blind review packet. Preserve this failed zero-token dispatch; do not overwrite or score it as an inferior research note. Any resumed wave needs a new explicit artifact directory so prior attempt markers are not bypassed. Do not rerun successful GPT outputs or include Fable. Record cross-day/search-access confounding. No scheduled wakeup or automatic retry has been created.

## Repository publication

The local protocol is committed. Automatic approval review rejected push + draft PR because authorization to export the user-supplied note was unclear. The owner was asked whether to publish with the note, without it, or keep local. Remote publication remains pending; no push or PR was created. Existing shared checkout files were not modified.
