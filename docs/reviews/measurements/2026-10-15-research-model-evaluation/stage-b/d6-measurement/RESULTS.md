# D6 instrument check — results

- Predeclared in `CHECK.md` and pushed before dispatch (commit 6ce6284). 16 blind Claude audits (`claude-opus-5-5`, effort medium, web tools, safe mode, Claude Code 2.1.304), all `success`, dispatched 2026-10-20 04:40–05:19 UTC. No comparative, no redispatch.
- Per-output levels: `review/tally.json` (from `tally.py`). Reports: `review/runs/claude-review-D01..D16/output.md`. Label key: `review/blind-key.json`.

## Verdict under the predeclared rule: the instrument is not usable as designed

`CHECK.md` §5 makes the instrument usable only if all three mutants are detected (D6 FAIL in both new-packet audits) and P5 r3 unmodified is not D6 FAIL. m2 was missed in both audits, so **D6 is not measurable by the Claude reviewer under this design**. Under the predeclared rule it falls to owner calibration in Stage C. The rules were not iterated inside the check.

| Item | New packet D6 (2 audits) | Old packet D6 | Reading | Rationale names the planted spot? |
|---|---|---|---|---|
| m1, track-9 roles dropped in a "nothing omitted" row | FAIL, FAIL (D12 also G4, medium) | BORDERLINE | **detected** | yes, both: "Karriem Riggins, Drums" vs reference "Composer, Lyricist, Drums", R-c |
| m2, Sped Up row counted in the ③ coverage line (11/11) | PASS, PASS | BORDERLINE | **missed** | the error was found in both, but placed under D1/D2 and defect 6, not D6 |
| m3, guessed "Lacy plays drums on Sunshine" against the row | FAIL, FAIL | BORDERLINE | **detected** | yes, both: ④-1 Sunshine drums vs Riggins, R-b/R-c |
| P5 r3 unmodified (negative control) | PASS | — | met | "10 rows match the frozen reference" |

## What the check shows

1. **The rules and the reference changed D6 placement for role defects.** With the round-5 packet, the reviewer gave all three mutants D6 BORDERLINE. It saw m2 and m3 (D2 FAIL on m3) but had no rule placing them at FAIL. With the new packet, it gave the R-c and A-route mutants D6 FAIL in 4 of 4 audits, each naming the planted row. This is the gap `DESIGN.md` F2/F3 diagnosed, now measured with a control.
2. **m2 was seen and routed elsewhere, so it is not a blindness miss.** All four m2 audits found "11/11 incl. the Sped Up row".
   - The two new-packet audits put it under D1 (edition) and D2. D10 says explicitly: "③의 11/11은 크레딧 집계가 아닌 커버리지 수치의 오류".
   - The old-packet audit put it under D6 BORDERLINE.
   - The anchors' FAIL route says "wrong-edition tracks (C)" and C-D6-FAIL says "deluxe track counted". Neither says whether a coverage numerator is a credit aggregate, and D1 also covers edition. So the mutant sat on a boundary the rules do not define. That was an orchestrator design choice, and this record does not reinterpret it as a pass.
3. **The sentinel reads FAIL for the first time since round 1** (D08, R-b: "Genius and Wikipedia only, while the Qobuz row was accessible"). Its round-1 answer was the R-b reading, so the control now agrees with the rule it was set by.
4. **Re-scored round-5 D6, descriptive only (owner decision 3: round 5 stands).**

   | Output | Round 5 Claude D6 | New packet D6 | Route named |
   |---|---|---|---|
   | P0 r1, r2, r3 | B, B, B | FAIL, FAIL, FAIL | R-b (r3: "no narrowing; conflicts resolvable from the row") |
   | P5 r1 | B | FAIL | R-b, plus R-c: composer credit read as vocal part ("Fousheé가 크레딧된 곡(3·5·7·9)") |
   | P5 r2 | B | FAIL | R-b ("no R-c error") |
   | P5 r3 | PASS | PASS | — |

   Five of these six moves are rule consequences (R-b). The outputs did not change. P5 r1's R-c finding is a content defect; the round-5 Claude audit marked defect 4 absent on it. Under these rules, the P0 control fails D6 in 3/3 runs and P5 in 2/3, so D6 would bind in round 6 for any candidate that does not open the authoritative row.

## Limits

- One album, one reviewer, 2 audits per mutant. Three mutants cover the R-c, A-route and edition routes only once each. Aggregate disclosure (G7 territory) was deliberately not planted.
- The reference was captured after generation. Accessibility rests on the 2026-10-19 producer trace.
- Claude Code moved 2.1.303 → 2.1.304 between round 5 and this check. The old-packet arm ran on 2.1.304, so the within-check contrast holds. The round-5 column above crosses versions.

## Open for the owner (recorded, not decided here)

- **What follows the predeclared "not usable".** The predeclared rule sends D6 to Stage C calibration. The record also supports these, and none is taken here:
  - (a) accept as predeclared;
  - (b) treat m2's placement as a mutant-design fault and run one more bounded check with the edition defect planted in a credit aggregate, and with the D1/D6 split for edition stated;
  - (c) accept D6 as measurable for the role/track routes (R-b, R-c, A-route) and unmeasured for the edition route.
- R-a to R-c stay adopted for development rounds (owner decision 2), whatever is chosen above.

**Owner decision, 2026-10-20 (chat): (a).** The predeclared outcome stands. D6 falls to owner calibration (Stage C, acceptance-v1 §6); in development rounds it is scored under R-a–R-c and reported descriptively, without binding a round rule. (b) and (c) are not taken.

## Publication

Review packets embed the Gemini Rights input. The owner-collection line was redacted in every review file (`PUBLICATION-REDACTIONS.json`, original hashes kept), and a token scan found 0 hits. `review/build-report.json` keeps the hashes of the bytes actually dispatched.
