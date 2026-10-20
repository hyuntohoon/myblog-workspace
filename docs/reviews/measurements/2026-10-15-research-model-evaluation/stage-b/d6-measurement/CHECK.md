# D6 instrument check — predeclaration

- Date: 2026-10-20. Design and diagnosis: `DESIGN.md`. This file fixes the check before any dispatch.
- **Owner decisions in chat, 2026-10-20, after reading `DESIGN.md`:**
  1. Run the M1 + M2 instrument check.
  2. Adopt R-a to R-c as written, as development-round D6 rules. This decides scoring-manual blank 3 for development rounds only; blanks 1 and 2 stay deferred, and §6 is not frozen.
  3. Re-scored round-5 D6 levels are descriptive only. P5's round-5 status stands. The rules apply from round 6.
- Unchanged: D6 judged by the Claude reviewer alone (2026-10-20); no Astra lane in this check; production untouched.

## 1. Frozen reference

`reference/qobuz-gemini-rights.json` (raw HTML sha256 inside; raw pages kept outside the repo at `~/.local/share/myblog-research/d6-check/`) and its text rendering `reference/qobuz-gemini-rights.txt`, which is the block reviewers receive.

- Authoritative row: Qobuz `zbylnavz5biaa`, the Explicit-marked 10-track edition. It is the listing the round-5 P5 r3 producer retrieved on 2026-10-19 and the one the round-5 audits used. Track titles and durations match the 10-track standard album.
- The other Qobuz edition, `v9b6d7bh8muhl` (no Explicit marker), differs in one cell only: track 3, Dahi `AdditionalStudioProducer` instead of `Producer`. No control depends on that cell.
- Captured 2026-10-20 by `curl` from static HTML, after generation. Accessibility at generation time rests on the 2026-10-19 producer trace (round-5 S04 trace seq 21).

## 2. Rules given to the reviewer

R-a to R-c exactly as `DESIGN.md` §4.2, inside a `<D6_DEVELOPMENT_RULES>` block, plus one LEAD sentence pointing to the two new blocks (`build_d6_inputs.py`). Nothing else in the round-5 packet changes.

## 3. Items

The base is P5 r3 (`cl-P5-gemini-rights-r3`). It is the only round-5 output whose credits rest on the authoritative row. Round 5 scored it Claude D6 PASS, Astra BORDERLINE with no narrowing or single-source reliance. Each mutant changes exactly one string (`build_d6_inputs.py` `MUTANTS`; exact diffs in `review/build-report.json`). Each planted defect is peripheral and D6-level:

| Mutant | Planted defect | Route |
|---|---|---|
| m1 | ⑤ full-row transcription, track 9: "Karriem Riggins, Composer, Lyricist, Drums" → "Karriem Riggins, Drums", in a list the note says omits nothing | R-c narrowing (roles dropped) |
| m2 | ③ coverage line: "S5 크레딧 행 10/10" → "11/11 (incl. the 'Bad Habit (Sped Up)' row of the same S5 listing)" | wrong-edition track counted in an aggregate (anchors C-D6-FAIL) |
| m3 | ④-1 adds "Sunshine의 드럼은 Lacy 본인이 연주한 것으로 보입니다(추정)." The reference and the note's own ⑤ give Riggins, Drums. | unverified credit guess with an accessible row (anchors A-D6-FAIL) |

16 blind audits, labels D01–D16 from one `secrets.SystemRandom` draw (`review/blind-key.json`):

- new packet: the 6 round-5 outputs, the sentinel, and each mutant twice (13);
- old packet (round 5 unchanged): each mutant once (3).

## 4. Dispatch

- `run_review_lane.sh D01 … D16`: Claude reviewer `claude-opus-5-5`, effort medium, WebSearch/WebFetch, `--safe-mode`, the round-5 runner and settings. Serial, no retries, halts on a rate limit.
- **No comparative step.**
- Versions at predeclaration: Claude Code **2.1.304**. Round 5 ran on 2.1.303; this is the auto-update patch class, recorded rather than treated as a stop. The old-packet arm runs on the same version, so the within-check contrast is unaffected.

## 5. Predeclared reading

- **Mutant detected:** both new-packet audits give D6 FAIL. A G4/G7 allegation located on the planted spot also counts, checked by hand in RESULTS.
- **Unstable:** detected in one of two. This is reported as unstable, not as a miss; one run is not attributable.
- **Missed:** neither audit detects it.
- **Instrument usable:** all three mutants are detected and P5 r3 unmodified is not D6 FAIL.
- **Instrument not usable:** any mutant is missed. Then D6 is not measurable by the Claude reviewer under this design and falls to owner calibration (Stage C). The rules are not iterated inside the check.
- Any mutant ending unstable (with none missed) is reported as "usable with noted instability", and the owner decides whether that suffices.
- **Old-packet arm, descriptive.** If the old packet also detects a mutant, that defect was always visible and the new blocks were not needed for it. If only the new packet detects it, the rules or the reference made the difference.
- **Re-scored round-5 D6 and sentinel levels: descriptive only** (owner decision 3). A level that moves under R-b is labelled a rule consequence.
- Orchestrator check: each mutant FAIL's rationale is read to confirm that it names the planted spot. A FAIL for another reason is reported as such and does not count as detection.

## 6. Stop conditions

A harness change beyond the recorded version; any audit with a non-success status (the lane halts, nothing is redispatched); a FAIL that needs the owner to adjudicate a rule, which is recorded and not resolved here.

## 7. Publication

Review packets embed the Gemini Rights input. Before push, redact the owner-collection line in all review files, as in round 5, and token-scan for 0 hits.
