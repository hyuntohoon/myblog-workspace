# D6 measurement — diagnosis and design options (proposal, not decided)

- Date: 2026-10-20. Written after round 5 (`../round5/RESULTS.md`), at the owner's choice of "D6 measurement design" as the next task.
- Status: **proposal for the owner.** Nothing here was dispatched. No round verdict is rewritten.
- Reviewed once by a read-only Fable pass before going to the owner. Its factual corrections were checked against the files and applied: Astra's sentinel route, the sentinel rule history, the Qobuz evidence, S02, and scoring-manual blank 3. Its design corrections were applied too: the mutant base, gate-route mutants, the comparative step, and replicate count.
- The owner's 2026-10-20 decision stands: D6 is judged by the Claude reviewer alone, and no-web Astra's D6 enters no count. None of the options below changes that.

## 1. Why D6 reads as "unmeasured"

Round 5 named D6 as the main thing between P5 and the Stage B gate. The record behind that:

- The Claude reviewer has given 0 D6 FAILs in 44 audits.
- It has missed the sentinel control in the three rounds that required a D6 FAIL (3–5). Round 2 accepted FAIL-or-BORDERLINE, and Claude met that rule (`../round2/RESULTS.md`; tightened in `../round3/ROUND.md` §Sentinel). `../round5/RESULTS.md` says "four rounds", which is the same overstatement.

Read on that record alone, the Claude reviewer looks lenient. The record points somewhere else: the instrument has gaps, and a stricter reviewer does not close them.

### F1. The sentinel's known answer was set at pool level, and the stricter reviewer does not reproduce it either

The sentinel is round-1 S03 (`cl-P1-gemini-rights`). Round 2 adopted it as "a round-1 output with a D6 FAIL both reviewers agreed on".

- **Claude's round-1 per-output audit said D6 BORDERLINE** (`../round1/review/runs/claude-review-S03/output.md`, final JSON).
- The FAIL came only in Claude's round-1 comparative (`../round1/review/runs/claude-comparative/output.md`, row S03 D6 BORDERLINE → FAIL). Its reason looked across samples: a Qobuz credit row was accessible, because the S05 and S07 audits had retrieved one. A single-output audit cannot see that reasoning.
- Astra's round-1 FAIL used a text-internal route instead: the note admits it found no distributor row, and it leaves a Wikipedia difference unresolved (`../round1/review/runs/astra-review-S03/output.md`). On identical bytes in rounds 4 and 5, Astra gave BORDERLINE ("접근 실패만으로 FAIL은 아니다", `../round5/review/runs/astra-review-S03/output.md`).
- So neither reviewer reproduces the "agreed FAIL" on the same text. Astra, the stricter of the two, moved its own level. That points to the FAIL/BORDERLINE boundary, not to one reviewer's leniency.

### F2. "Authoritative row" is undefined, and even an accessible row in the packet does not move Claude

`acceptance-v1.md` (D6 row) and `anchors-v1-rc.md` §2 require "a named authoritative row" and never say which sources qualify. Anchor reconciliation R3 keeps two FAIL routes, A's (unverified guesses with accessible rows) and C's (single encyclopedia, role narrowing, deluxe track counted), untested until calibration. This is scoring-manual **blank 3**, which the owner deferred on 2026-10-19 (`../round3/ROUND.md` §7: "Whether Genius and Wikipedia rows count as an authoritative row for D6").

The round-5 rationales split along this line:

| Output | Credit basis named by the reviewers | Astra D6 | Claude D6 |
|---|---|---|---|
| S01 P5 r2 | single encyclopedia summary (S6) as the row | FAIL "single-encyclopedia boundary" | BORDERLINE, noting "no authoritative primary row; leans heavily on the S6 wiki" |
| S02 P5 r1 | Genius + S6 summary; distributor row not received | BORDERLINE per-output, FAIL after its comparative | BORDERLINE |
| S05 P0 r2 | unsourced retail Discogs-format copy | FAIL "core credits not tied to an official row" | BORDERLINE |
| S06 P0 r3 | Wikipedia personnel for track 9 | FAIL "single encyclopedia" | BORDERLINE |
| S07 P0 r1 | Wikipedia for Sunshine | FAIL | BORDERLINE |
| S04 P5 r3 | Qobuz row, 10/10 tracks | BORDERLINE | PASS |

In S01 and S07 the producer's own trace held Qobuz search hits. Claude noted them: S01 says "S9 (Qobuz) was a search summary only", and S07 says "seq37 Qobuz snippet missed". It still gave BORDERLINE. So the accessibility fact was partly *inside* the packet, and the reviewer had no rule that said what follows from it.

### F3. "Normalises" (BORDERLINE) versus "narrowing" (FAIL) is undefined

§2 puts "a summary normalises a role" at BORDERLINE and "role narrowing" at FAIL. Claude's round-5 audits mark defect 4 (role normalisation or narrowing) present in three of seven: S03, S05 and S07. In S05, for example, Kirby's "Additional synth bass / Organ / synth textures" became "신스·오르간", and three personnel were dropped. All three went to BORDERLINE. Nothing in the anchors says when grouping, translation or dropping a role becomes narrowing.

### F4. The reading changes the round-5 verdict

This is a sensitivity statement, not an adjudication.

- Read with the round-1 comparative's rule, every round-5 output except P5 r3 rests its credits on Genius, Wikipedia or a retail copy, while a Qobuz row was accessible (S04's trace retrieved one on 2026-10-19). Those five, P5 r1 and r2 among them, would be at least D6 FAIL candidates, and P5 would not advance under rule (a).
- Read as the Claude reviewer did, nothing moves.

That would be a consequence of a rule, not a new measurement. Still, today the undefined rule, not the prompt, decides this.

**Diagnosis.** D6 is unmeasured mainly because of an instrument gap: an undefined source class (blank 3), an undefined narrowing boundary, and a control whose "agreed" answer neither reviewer reproduces on the same text. A stricter reviewer would not fix it, and Astra's own flip shows as much. The Claude reviewer does report the defects. It has no rule for placing them.

## 2. Requirements for a usable D6 measurement

1. **Known-answer control inside the text.** A control's FAIL follows from the note plus a frozen reference the reviewer is given. It does not rest on a fact the reviewer has to rediscover, or on cross-sample comparison.
2. **Same pass.** The control runs blind in the same batch, with the same packet as the outputs it vouches for.
3. **Mutation check.** The measurement FAILs a planted D6 defect and does not FAIL the same note without it. The unplanted note must therefore be a clean D6 case under the rules in force.
4. **No mid-series drift.** Any reviewer-packet change is re-run on outputs already scored, so old and new levels compare on the same bytes.

## 3. Options

| | What | Fixes | Cost | Leaves open |
|---|---|---|---|---|
| **M0 D6 to Stage C** | Keep the current Claude D6 in Stage B. File R-a to R-c (§4) as the D6 draft for the §6 manual, and run the planted-defect check at owner calibration. | Avoids deciding the D6 rule twice. Stage C needs §6 frozen and owner calibration anyway (`round-manifest-v1.md` §6). | 0 now | The RFC's Stage B gate is "all predeclared dimensions pass". Under M0, Stage B can close only if the owner explicitly moves D6 out of the B gate. Every further round reports "D6 unmeasured". |
| **M1 Frozen reference + source rules** | Freeze the authoritative credit row(s) accessible at generation time, with capture, URL, timestamp, sha256 and the named edition. Give them to the D6 reviewer with rules R-a to R-c. | F1 (accessibility becomes a given), F2, F3 | One capture per album; slightly longer packet | It decides blank 3 now, for development rounds. The 10-19 deferral was about comparability, and requirement 4 covers that. |
| **M2 Planted-defect controls** | Replace the sentinel, as the D6 control, with scripted mutants of one clean output and that output unmodified. | Requirements 1 and 3 | 7–10 extra audits once | It cannot settle F2/F3 by itself; it needs M1's rules to define "clean". |
| **M3 Mechanical role-string diff** | Script-diff extracted (person, role, track) triples against the frozen row. | Role and track precision, deterministically | Extractor, plus a control for LLM extraction | Aggregate disclosure and source class stay with a reviewer. |

**Recommendation: M1 + M2 as a one-time D6 instrument check, if the owner wants D6 inside the Stage B gate.** The source-class rule (blank 3) has to be decided before Stage C in any case. Deciding it now costs about one review lane and makes the Stage B gate closable. **If the owner is content to move D6 out of the Stage B gate, M0 is the cheaper honest choice**: the same rules and controls run once, at calibration. M3 only if the check shows the reviewer is unreliable even with M1.

## 4. Proposed D6 instrument check (only if the owner picks M1 + M2)

Scope: Gemini Rights, Claude reviewer only (the 10-20 decision), round-5 review prompt otherwise unchanged. No new generation.

1. **Freeze the reference.**
   - Capture the Qobuz credits page whose edition matches the Spotify 10-track target. Round-1 audits retrieved two Qobuz IDs (`zbylnavz5biaa`, `v9b6d7bh8muhl`); the capture names which edition it is and why.
   - Capture the Wikipedia personnel list and the Genius aggregate the producers received, labelled *secondary*.
   - Record with the capture that it post-dates generation. Accessibility at generation time rests on S04's 2026-10-19 trace and on round 1's S05/S07.
   - Stop if the role field is missing or the edition cannot be matched.
2. **Rule text (draft for the owner to edit; this is blank 3 plus one boundary).**
   - *R-a source class:* authoritative = a distributor, label or store credit listing with a per-track role field, or physical liner notes. Genius, Wikipedia and Discogs-format copies are secondary.
   - *R-b accessibility:* if the frozen packet shows an authoritative row was accessible and a credit claim rests only on secondary sources, that claim takes the FAIL route. If none was accessible, reliance on secondary sources caps D6 at BORDERLINE and is not a FAIL by itself.
   - *R-c narrowing:* translation or grouping that keeps every role's function and track scope is normalising (BORDERLINE). Changing a function, narrowing the track scope, or dropping a person or role that the claim's scope covers is narrowing (FAIL).
3. **Build controls on P5 r3** (`cl-P5-gemini-rights-r3`, S04). It is the only round-5 output with a Qobuz row (10/10). Claude gave it PASS, and Astra found "no role narrowing or single-source reliance". It is the clean case that requirement 3 needs. Do not use P5 r1: under R-b it already takes the FAIL route, so mutants of it would FAIL trivially. Script three mutants, each a *peripheral*, D6-level defect that does not depend on R-a or R-b, and record each exact diff:
   - m1, R-c narrowing in a peripheral credit row (④/⑤), e.g. one role string replaced by a narrower one;
   - m2, a wrong-edition track (Sped Up) counted in a disclosed aggregate. The predeclared counting dimension is D6; a D1 mark is reported beside it;
   - m3, an A-route defect: one credit stated from an unverified guess while the Qobuz row in the note shows otherwise.

   Defects in central claims would be G4/G7 gate tests (anchors §2 D6 gate column; `acceptance-v1.md` G7), so they are deliberately avoided. A G4/G7 allegation on a mutant is reported and counts as detection.
4. **Run.** All blind and shuffled, Claude reviewer, new packet:
   - 6 round-5 outputs + the sentinel + P5 r3 unmodified (as itself; it is one of the 6) + **2 audits per mutant** (6) = 13 audits.
   - Old-packet arm: the 3 mutants once each, which separates "reviewer misses planted defects" from "the old packet withheld the rule". That makes 16 audits, roughly one round-5 review lane.
   - **No comparative step.** Per-output levels are the measurement, because a comparative would see near-identical mutants side by side.
   - Re-check the CLI version before dispatch.
5. **Predeclared reading.**
   - Per mutant: detected if both new-packet audits give D6 FAIL (or a G4/G7 allegation on the planted spot).
   - The instrument is usable if all three mutants are detected and P5 r3 unmodified is not D6 FAIL.
   - A mutant detected in one of two audits is reported as unstable, not as a miss. One run cannot be attributed.
   - Any mutant missed in both audits means D6 is not measurable by the Claude reviewer under this design. D6 then falls to owner calibration (M0 path). Report that, and do not iterate the rules inside the check.
6. **Report.**
   - Re-scored round-5 D6 levels are reported descriptively next to the round-5 levels. Where they move because of R-b, that is stated as a rule consequence, not a new measurement.
   - Whether they affect P5's status is the owner's call (§6). The round-5 record is not edited, except a separate one-line correction of its "four rounds" sentinel count if the owner wants it.

Stop conditions: an unexpected CLI or harness change; a capture that fails step 1; any FAIL that needs the owner to adjudicate a rule, which is recorded and not resolved inside the check.

## 5. Unchanged, and what this proposal does decide

Unchanged:

- production prompt, poller and `PROMPT_VERSION` (RFC non-goal);
- Codex producer lane discontinued (10-19);
- no Genius annotation arm (10-20);
- D6 judged by the Claude reviewer alone (10-20);
- round-5 G4 dismissals (10-20).

**M1 asks the owner to decide scoring-manual blank 3 now, for development rounds.** Blanks 1 and 2 stay deferred. Adopting R-a to R-c does not freeze §6; the frozen manual may restate or replace them before calibration.

## 6. For the owner

**Decided in chat on 2026-10-20:** option 1 = M1 + M2 instrument check; option 2 = R-a to R-c adopted as written for development rounds; option 3 = from round 6 only (round-5 status stands). The check is predeclared in `CHECK.md`.

1. Which option: M1 + M2 instrument check (recommended if D6 should be in the Stage B gate), M0 (D6 out of the Stage B gate, checked at calibration), or another.
2. If M1: accept, edit or reject R-a to R-c as development-round D6 rules, which decides blank 3 for development rounds.
3. If the check makes D6 measurable: may the re-scored round-5 D6 change P5's "advances" status, or do the rules apply from round 6 only?
