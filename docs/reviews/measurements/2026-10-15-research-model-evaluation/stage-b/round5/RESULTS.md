# Stage B round 5 — results (2026-10-20)

Scope: `ROUND.md`. The owner confirmed it before any producer output. It was frozen and pushed as `fd09bd7` before the first generation. If the merge rebases that commit, the rewritten sha is recorded in the PR. This is a development round. Its verdict is a model-proxy development judgement, not an acceptance-v1 pass.

## Verdict: P5 advances under the round-5 rule, after the owner dismissed both gate allegations

| Condition (§6) | P5 | |
|---|---|---|
| (a) no agreed FAIL after calibration | **holds** | No dimension is FAILed by both reviewers. None of the three single-reviewer FAILs (all Astra) is confirmed against sources (below). |
| (b) no unresolved gate allegation on P5 | **holds after owner adjudication** | Two G4 allegations were raised on P5 outputs. The owner dismissed both in chat on 2026-10-20 ("둘 다 기각"). |
| (c) P5 FAIL marks ≤ P0's | **holds** | **3 vs 9** |
| (d) pilot defects listed | table below | |
| (e) median length ≤ 1.10 × P0 | **holds** | **7,366 vs 8,382 chars = 0.879×** |

**What "advances" means here, and what it does not.**
- P5 is now the development candidate. It replaces P4 as the base for any further Stage B work and is the one that would go to Stage C.
- It does **not** meet the RFC's Stage B gate ("all predeclared dimensions pass; no unresolved material disagreement"):
  - D6 is still unmeasured. The Claude reviewer's D6 has no FAIL in 44 audits, and neither reviewer met the sentinel control. See below.
  - D7 was not assessed. Development rounds have no frozen top-3 map.
  - Astra's three unconfirmed FAILs are reviewer disagreements resolved by the orchestrator's source check, not by agreement.
- The candidate was tuned on Gemini Rights over five rounds. A pass here is a result on training material.

### The single-reviewer FAILs on P5, checked against sources

Every D1–D5 FAIL from one reviewer on a P5 output was checked against the producer's trace (`runs/<id>/stdout.jsonl`, blinded copies in `review/web-traces/`), the dispatched input, and the frozen anchors.

| Output | FAIL | Check | Result |
|---|---|---|---|
| r2 (S01) | Astra D5. C7 says the Kirby / Ely Rise credit differences are "범위 차이 또는 미확인이며, 상충은 아니다", but Genius 6/9 vs S6 (Wikipedia) 3/10 for the same role cannot be explained by one excluded track. | C7 is labelled `[DB등재·미확인]` and says why: S6 was received as a tool summary ("S6에 없다는 것은 위키 요약에 없다는 뜻일 뿐"). G gives no track list, so a track-level comparison is impossible. The item is handed to ④-1 for booklet / Tidal comparison. P4/P5 §5 makes absence from filtered material `미확인`, not `상충`. Claude read the same C7 as "범위 차이로 정확히 처리했다". The anchors' D5 FAIL needs a consequential misstatement or an uncertainty resolved *silently*; here it is stated and handed off. | **Not confirmed** |
| r1 (S02) | Astra D5, raised to FAIL in calibration. The check question says "Fousheé가 크레딧된 곡(3·5·7·9)", which uses an unconfirmed credit as the premise for vocal placement. | 3·5·7 are Genius 작곡·작사 rows. 9 is the input's own track title, "Sunshine (feat. Fousheé)" (input line 12), so Fousheé's credit on 9 was received, not inferred. No uncertainty was resolved. The question does merge two kinds of credit (writer and featured artist) under "크레딧된". That is a role-merging observation for change 1 (defect 4), not a D5 status error. | **Not confirmed** (role merge noted under (d)) |
| r3 (S04) | Astra D2: ③'s line "실제로 제작 과정까지 다룬 곡은 5번 Bad Habit 1곡" contradicts C6, and ③ marks Static and Buttons "참조 관계 없음". | Both facts are confirmed. C6 in the same note records the Mercury parts dropped as "too pitchy", and ③'s own evidence column lists C6 on tracks 2, 3, 8 and 10. The input's G block lists remixes and samples of Static (line 30) and a remix of Buttons (line 32), and ③'s legend says that column holds G-registered items. D2 FAIL needs a *central* incorrect claim. The same location carries Astra's G4, which put centrality to the owner, and the owner dismissed it. | **Fact confirmed. FAIL not confirmed: not central (owner, (b))** |

**Gate allegations on P5.** Both were dismissed by the owner on 2026-10-20.
- r3 (Astra G4, medium) is the ③ coverage line above. The owner ruled it peripheral: the per-track rows and C6 are correct, and only the summary line under the table is wrong.
- r2 (Claude G4, low) is C5, "기자의 서술이며 Lacy의 발언이 아니다". The producer's received fetch summary of the Consequence article says it literally: "that comes from the writer's report, not a direct Lacy quote" (trace, Consequence fetch). Claude, which has web access, found "the singer also teased…" on the live page. The note followed the document it received, as P4 §4 B requires, and labelled it `[보도·검색 결과 경유]`.

P0 carries G4 allegations of its own (Astra on r1 and twice on r3, one of them G9; Claude on r3). They do not enter §6 and were not adjudicated.

## What ran

| Part | Result |
|---|---|
| Fable review of the draft | 10 findings, no blocker, all applied (ROUND.md header) |
| Owner confirmation | 2026-10-20, before any dispatch |
| Fidelity check (`freeze-check/`) | Astra (no web, 0 tool calls): CONFIRM FREEZE. Claude: MATERIAL OBJECTION on three wordings, applied once (ROUND.md §1). |
| Generations (`runs/`) | **6/6 success**, no reruns. 11–23 searches and 10–23 fetches per run. Every run had 0 hook events, no `memory_paths`, and tools exactly WebSearch + WebFetch. No output carries a trailing "Sources" list. |
| Blind draw (`review/blind-key.json`) | 2026-10-19T19:29:34Z, one `secrets.SystemRandom().shuffle` over 6 outputs + sentinel. 0 identity hits in notes or traces. One harness string in the sentinel note neutralised (S03 = sentinel). |
| Per-output audits | **Claude 7/7, Astra 7/7 success.** Claude: 3–4 WebFetch each. Astra: no web tool, 0 tool calls. |
| Comparative calibration | 2/2 success. Astra made 3 changes: S02 D5 B → F, S02 D6 B → F, S05 D3 B → F. Claude made 2: S06 D2 F → B, S01 D5 B → P. |
| CLI versions | Claude Code 2.1.303. Astra lane `codex-cli 0.163.0-alpha.10.2`, re-checked just before the review dispatch (unchanged). |

## Reviewer control (sentinel = S03)

| Reviewer | Sentinel D1–D6 after calibration | Control (D6 FAIL, §5) |
|---|---|---|
| Astra (no web) | P B P P F B | **not met** (D6 BORDERLINE), as in round 4 |
| Claude | P B P P B B | **not met**, the fourth round running. Still no FAIL on any sentinel dimension. |

- Claude's D6 is BORDERLINE on the sentinel. On the six outputs it is BORDERLINE on all three P0 runs and on P5 r1 and r2, and PASS on P5 r3. So **5 of 6** outputs sit at or above the sentinel's severity (descriptive, §5).
- Claude has now given **0 D6 FAILs in 44 per-output audits** (rounds 2–5). The D6 clauses of (a) and (c) could not fire, as ROUND.md §5 stated in advance.
- Astra's D6 FAILs all six outputs (P5: r1 and r2 FAIL, r3 BORDERLINE; P0: all FAIL) but not the sentinel. It is excluded from every count.

## Calibrated levels (D1–D6; D7 not assessed)

| Arm | Run | Label | Astra | Claude | Counted FAILs | Chars |
|---|---|---|---|---|---:|---:|
| **P0** | r1 | S07 | P F P P F *F* | P B P P B B | 2 | 8,533 |
| | r2 | S05 | P B F P F *F* | P B F B B B | 3 | 6,929 |
| | r3 | S06 | P F P F F *F* | P B P B F B | 4 | 8,382 |
| **P5** | r1 | S02 | P B P P F *F* | P B P P P B | 1 | 5,808 |
| | r2 | S01 | P B P P F *F* | P B B P P B | 1 | 7,366 |
| | r3 | S04 | B F P B B *B* | P B P B P P | 1 | 7,857 |

- Italic is Astra's D6, excluded from every count.
- P0's agreed FAILs are r2 D3 and r3 D5. They are the round's only FAILs shared by both reviewers.
- Side table, counting Astra's D6 as round 3 did: P0 12, P5 5. (c) still holds.
- Round-4 P4, for reference only (not pooled): 3 FAIL marks, lengths 6,074 / 7,342 / 6,988.
- Round-5 P0 ran longer than round-4 P0: median 8,382 vs 6,952, with the same prompt and input bytes. That widened the (e) bar. P5's own median, 7,366, is about P4's 6,988 plus 5 %. The cap overshoot (6,000) is up to 1.31×, against up to 1.22× for P4.

## Pilot recurring defects (A = Astra, C = Claude; per output, from the per-output reports)

| Defect | P0 r1 | P0 r2 | P0 r3 | P5 r1 | P5 r2 | P5 r3 | Change aimed at it |
|---|---|---|---|---|---|---|---|
| 1 Reporter → direct quote | – | C | – | – | – | – | — |
| 2 Summary promoted / mis-attributed | A C | A C | A C | – | A C | C | P4 change 2 (carried) |
| 3 Received source under-read | A | – | – | A C | – | A C | change 3 (indirectly) |
| 4 Role fields narrowed / substituted | A C | C | A | A | A | – | **change 1** |
| 5 Spurious scope conflict / unchecked exclusive | C | – | A | A | – | – | **change 3** |
| 6 Numerator inconsistency | A C | A C | C | – | – | A C | P4 changes 1, 4 (carried) |
| 7 Reviews as factual evidence | – | – | – | – | – | – | — |
| 8 Length / ritual repetition | A | A | – | – | – | – | P4 change 5 (carried) |
| Dropped source uncertainty marker (§6 (d) extra row) | 0 | 0 | 0 | 0 | 0 | 0 | **change 2** |

- **Defect 4 moved for the first time.** It drops from P0's 4 marks to 2, both Astra. Claude marks none on P5, against 2 on P0. Round 4's P4 had 5.
  - Astra's two P5 marks are about relying on a single encyclopedia summary for credits (r1, r2), plus r1's writer/feature merge noted above. Neither is translation or narrowing of a role string.
  - Defect 4 is a D6-type defect and D6 is unmeasured, so this table is the only place the change's effect shows.
- **Defect 2 is back on P5** at 3 marks, against 0 for P4 in round 4 and 6 for P0 here. The cases are different from the round-3 mis-attributions:
  - r2: one Riggins snippet dated 2022-07-30 was filed under a 2022-10-22 S8 URL (both reviewers).
  - r3: a summary's paraphrase "too pitchy" was presented as a Lacy quote (Claude, "경미").
- **Defect 3 rose on P5** (4 marks, against 1 on P0). Two of them are the r3 ③ "없음" cells that contradict the G block. That is a negative statement written without checking received material, exactly what change 3 targets. The other two are r1's "연주·엔지니어링 역할은 받지 못했다", contradicted by the run's own seq-4 fetch. **Change 3 did not stop this kind of claim** in r1 and r3.
- **Defect 6** is 2 marks on P5 (r3, the ③ coverage line), against 5 on P0. **Defect 8** is 0 on P5, against 2 on P0.
- **Dropped uncertainty markers: 0 in all six outputs.** The orchestrator scanned every tool result in the six producer traces for hedges ("tentative", "ambiguous", "reportedly", "allegedly", "rumo(u)red", "unconfirmed", "unclear", "appears to", "seems to", "treat … as"). Three hits:
  - P0 r3 "reportedly came up with the title while tipsy in a bar": the claim is not in the note.
  - P0 r3 "That appears to mix up the Demo EP with Apollo XXI": a summariser's own comment. The note uses no claim it flags.
  - P5 r3 "appears to be Apple Music editorial copy": attached to an editorial blurb the note does not use. The note uses the artist statement, which the source labels as such.

  Neither reviewer reported a dropped qualifier. The scan covers English hedges in tool results only. Round 4's single case (P4 r3) did not recur, but one absence in 6 outputs is weak evidence that change 2 works.

## Token use

| Part | Input tokens (cache-inclusive) | Output tokens |
|---|---:|---:|
| Claude generation, 6 notes | 2,907,891 (279,115–890,653 each) | 95,535 |
| Claude review, 7 audits | 854,098 (89,196–151,726 each) | 85,423 |
| Astra review, 7 audits (no web) | 308,448 (37,123–54,056 each) | 21,733 |
| Comparatives (Astra / Claude) | 33,103 / 35,780 | 2,592 / 10,441 |
| Fidelity check (Astra / Claude) | 18,967 / 12,841 | 530 / 3,134 |

## What the round shows

1. **P5 keeps P4's gains and clears the round-4 blocker.**
   - FAIL marks are 3 against 9, length is 0.879×, and defects 6 and 8 stay down.
   - No dropped uncertainty marker was found in any output.
   - Every P5 FAIL was one reviewer's, and none survived the source check.
2. **Change 1 is the first edit to move defect 4.** The evidence is the defect table, plus Claude's D6 at PASS on one P5 output (it was BORDERLINE on all six outputs in round 4). No gate measures it.
3. **Change 3 did not stop unchecked negative statements.** Two of three P5 runs wrote "없음" / "받지 못했다" against material they had received. One of these is r3's ③ coverage line, which the owner judged peripheral. If a later round targets this, the likely shape is a check tied to the table cells. The current wording sits in §5's prose, far from ③.
4. **D6 is still unmeasured.** This is now the main thing standing between P5 and the Stage B gate.
   - Claude has given 0 D6 FAILs in 44 audits, and its sentinel control has failed four rounds running.
   - Astra's no-web D6 FAILs nearly everything except the sentinel.
   - Round-5 P0 also ran about 20 % longer than round-4 P0 on identical bytes, which is a reminder that (e) has run-to-run noise of that size.

## Open for the owner (recorded, not decided here)

- **How D6 is measured** before any Stage B gate or Stage C claim. Raised in round 4 and unchanged. The owner's 2026-10-20 decision (Claude alone) stands; this is its measured consequence after one more round.
- **What comes next.** The options include another bounded Stage B round from P5 (for example, change 3 moved to the checklist), resolving D6 measurement first, or preparing Stage C. Stage C needs the §6 scoring manual and §7 floors frozen, and those were deferred by the owner on 2026-10-19.

## Publication

Every record that embeds the Gemini Rights catalog block had its owner-collection line redacted, listed in `PUBLICATION-REDACTIONS.json` with the original hashes. A token scan in plain and JSON-escaped forms then found 0 hits. `review/build-report.json` keeps the pre-redaction packet hashes, which match the bytes actually dispatched.
