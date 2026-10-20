# Stage B round 6 — results (2026-10-20)

Scope: `ROUND.md`. The owner confirmed it before any dispatch. It was frozen and pushed as `2694c49` before the first generation. If the merge rebases that commit, the rewritten sha is recorded in the PR. The blind absence-value pass was pushed as `717e958` before the key was read. This is a development round. Its verdict is a model-proxy development judgement, not an acceptance-v1 pass.

## Verdict: P6 does not advance, on one orchestrator-confirmed D4 FAIL

| Condition (§6) | P6 | |
|---|---|---|
| (a) no agreed D1–D5 FAIL after calibration | **fails** | No dimension is FAILed by both reviewers. Of the two single-reviewer FAILs on P6, the orchestrator confirmed one against sources: Claude's D4 on r2 (below). |
| (b) no unresolved gate allegation on P6 | **holds** | The only allegation on a P6 output (Claude G4, low, r2 ④-1) was withdrawn with evidence in Claude's own comparative. |
| (c) P6 FAIL marks ≤ P0's | **holds** | **2 vs 8** |
| (d) pilot defects listed | table below | Change 1's target row is 0 contradicted absence values on every P6 output, against 1 on P0. |
| (e) median length ≤ 1.10 × P0 | **holds** | **6,493 vs 7,986 chars = 0.813×** |

**What decides it.** P6 r2 (S07) quotes Lacy in ② K6: "The drums were different, the chorus was different." It cites S6, which is Wikipedia's "Bad Habit" article, marked "검색 스니펫만", with the claim labelled `[검색 결과 경유]`. The check:
- The quote reached the producer verbatim in one search result (trace seq 12, query "Steve Lacy "Bad Habit" made how interview…"). That result is a summary over nine links, among them the Wikipedia article and Songfacts.
- The orchestrator fetched the Wikipedia article's current wikitext (52 KB, "Gemini Rights" ×12). It paraphrases the June 2021 origin ("its drums, and its chorus") and has no such quote.
- Songfacts' Bad Habit page has the sentence verbatim ("drums were different, the chorus was different," Lacy recalled to…). The Claude reviewer reached the same finding: Songfacts relaying a Billboard interview.
- So a reader who follows the citation does not recover the quoted passage. Anchors R5 / `C-D4-FAIL`: "Non-recovery is a D4 traceability fact and is scored FAIL." **Confirmed.** It is not a G2: the passage exists, and it was received.
- The counter-reading, recorded rather than taken: the note discloses that S6 is a snippet and the status is relayed, and the passage is recoverable one link away in the same search. Round 5 had a similar slip, P5 r2 filing a Riggins snippet under another S8 URL. It was marked defect 2 there, and neither reviewer gave D4 FAIL. Under the anchors' wording, non-recovery at the cited source is FAIL, and the predeclared rule turns one confirmed single FAIL into an agreed FAIL.

This is the same shape as round 4's stop: one confirmed, narrow failure in a candidate that otherwise meets every other condition.

### The single-reviewer FAILs on P6, checked against sources

| Output | FAIL | Check | Result |
|---|---|---|---|
| r2 (S07) | Claude D4. The K6 quote is not in cited S6. K7's "the album's only guest feature" is not verbatim in S2. | K6: as above. K7: S2 (GRAMMY.com) reached the producer as a fetch summary that labels the phrase "journalist narration", so the quote marks sit on summary text (D4 BORDERLINE-type). Astra (no web) gave D4 BORDERLINE. | **K6 confirmed → agreed FAIL under §6 (a)** |
| r3 (S02) | Astra D5. C7 records the Qobuz / Genius producer difference but calls it "미확인" rather than `[상충]`; ⑤ calls Mercury's Matt Martians difference "범위 차이". | C7's text says "크레딧 집계가 서로 맞지 않는다", keeps it unresolved, and hands it to ④-1. Nothing is resolved silently. The Mercury line is in the appendix and supports no claim. Claude read the same two spots and gave D5 BORDERLINE ("본문에 '맞지 않는다'고 적어 결과적 왜곡은 없다"). The anchors' D5 FAIL needs a *consequential* misstatement or a silent resolution. This is the round-5 r2 C7 case again. | **Not confirmed** |

**Gate allegation.** Claude's per-output G4 (low) on r2 ④-1 ("요약된 자료에 이름이 빠진 것이므로 상충이 아니라 [미확인]") was withdrawn in its comparative: "결론을 [미확인]으로 남기고 핵심 논거에서 뺐다는 S07 자체 기록 때문에 '확정된 것으로 제시' 요건이 성립하지 않습니다". The wrong *cause* statement is real: neither Wikipedia's Technical list nor the Qobuz row credits Kirby or Rise as producers. It sits in Claude's D2, calibrated FAIL → BORDERLINE as non-central. P0 carries G4/G5 allegations (r1: Astra ×3, Claude ×1; r2: Astra G5). They do not enter §6 and were not adjudicated.

## What ran

| Part | Result |
|---|---|
| Fable review of the draft | 13 findings, no blocker. 2 described pre-edit files and were already fixed; 11 applied (ROUND.md header). |
| Owner confirmation | 2026-10-20, before any dispatch ("이대로 확정") |
| Fidelity check (`freeze-check/`) | Astra: CONFIRM FREEZE. Claude: MATERIAL OBJECTION on part (b), applied once verbatim (ROUND.md §1). |
| Reference re-check (`reference/recheck.json`) | 2026-10-20T09:13Z, 10/10 credit lines byte-identical to the D6-check capture. Reviewer reference sha256 `3c0eda37…` (one capture-note line differs from the D6-check file). |
| Generations (`runs/`) | **6/6 success**, no reruns, 192–381 s each. 9–21 searches and 9–29 fetches per run. Every run had 0 hook events, no `memory_paths`, and tools exactly WebSearch + WebFetch. |
| Blind draw (`review/blind-key.json`) | One `secrets.SystemRandom().shuffle` over 6 outputs + sentinel. 0 identity hits in notes or traces; one harness string neutralised in the sentinel note (S05 = sentinel). |
| Blind absence pass (`review/blind-absence-pass.md`) | Committed before the key was read. |
| Per-output audits | **Claude 7/7, Astra 7/7 success.** Claude: 2–7 web calls each. Astra: no web tool, 0 tool calls. |
| Comparative calibration | 2/2 success. Astra: S01 D2 P → B, S03 D2 B → F, S04 D2 B → F. Claude: S04 D1 B → P, S05 D2 P → B, S07 D2 F → B, and the S07 G4 withdrawn. |
| CLI versions | Claude Code 2.1.304 throughout. Astra lane `codex-cli 0.163.0-alpha.10.2`, re-checked before the fidelity and review dispatches. |

## Calibrated levels (D1–D6; D7 not assessed)

| Arm | Run | Label | Astra | Claude | Counted FAILs (D1–D5) | Chars |
|---|---|---|---|---|---:|---:|
| **P0** | r1 | S06 | P F F B F *F* | P B B B B *F* | 3 | 7,026 |
| | r2 | S04 | B F F B F *F* | P B P B B *F* | 3 | 8,232 |
| | r3 | S03 | P F P P F *F* | P B P P B *F* | 2 | 7,986 |
| **P6** | r1 | S01 | P B P P B *F* | P B B B B *F* | 0 | 6,493 |
| | r2 | S07 | P P P B B *F* | P B B **F** B *F* | 1 | 6,465 |
| | r3 | S02 | B B P B F *B* | P B P P B *B* | 1 | 7,025 |

- Italic is D6, descriptive only (§6). Neither reviewer's D6 enters any count.
- P0's 8 marks are all Astra; no P0 FAIL is shared by both reviewers.
- Round-5 P5, for reference only (not pooled, and scored on the old packet): 3 FAIL marks, lengths 5,808 / 7,366 / 7,857.
- Round-6 P0 ran at median 7,986, between round 4's 6,952 and round 5's 8,382, on identical bytes.

## D6, descriptive (§6; binds nothing)

| Output | Claude D6 | Route named by Claude | Credits rest on an authoritative row? (trace) | Astra D6 |
|---|---|---|---|---|
| P0 r1 (S06) | FAIL | R-b; R-c (Martians on 3·4 dropped from C7) | No. Searched "qobuz OR tidal" (seq 20) and never opened a Qobuz page. | FAIL |
| P0 r2 (S04) | FAIL | R-b; R-c (Dahi dropped in C6) | No. Qobuz left as a follow-up. | FAIL |
| P0 r3 (S03) | FAIL | R-b | No. Qobuz domain in results (seq 20), not opened. | FAIL |
| P6 r1 (S01) | FAIL | R-b; R-c (track-10 writers) | No. Qobuz domain in results (seq 18), not opened. | FAIL |
| P6 r2 (S07) | FAIL | R-b (normalisation only BORDERLINE) | No. Credits from Genius, Wikipedia and a Deezer snippet. | FAIL |
| P6 r3 (S02) | **BORDERLINE** | Row used and named as R-a. Edition (Explicit) not marked; Synthesizer 5/9 merges "John Kirby" undisclosed. | **Yes.** Qobuz `zbylnavz5biaa` fetched (seq 15, gb-en), every cross-checked cell matches the frozen reference. | BORDERLINE |
| Sentinel (S05) | FAIL | R-b | — | FAIL |

- No trace attempted a Qobuz album page and failed. One run in six (P6 r3) opened the authoritative row. P5 r3 did the same in round 5.
- **The sentinel now reads D6 FAIL for both reviewers, after the comparative step and in Astra's copy.** That is the first time since round 1. In round 5 both had it at BORDERLINE.
- Under R-a–R-c, D6 follows one fact: whether the producer opened the row. P0 3/3 and P6 2/3 are FAIL, which matches the D6 check's descriptive re-score of round 5 (P0 3/3, P5 2/3).

## Pilot recurring defects (A = Astra, C = Claude; per output, from the per-output reports)

| Defect | P0 r1 | P0 r2 | P0 r3 | P6 r1 | P6 r2 | P6 r3 | Marks P0 / P6 |
|---|---|---|---|---|---|---|---|
| 1 Reporter → direct quote | A | A | – | – | – | – | 2 / 0 |
| 2 Summary promoted / mis-attributed | A C | A C | A C | C | A C | – | 6 / 3 |
| 3 Received source under-read | C | – | A | – | A | C | 2 / 2 |
| 4 Role fields narrowed; single encyclopedia | A C | A C | A C | A C | A C | – | 6 / 4 |
| 5 Spurious scope conflict / unchecked exclusive | A C | A C | A | A | – | A | 5 / 2 |
| 6 Numerator inconsistency | A C | – | C | A | – | A C | 3 / 3 |
| 7 Reviews as factual evidence | – | – | – | – | – | – | 0 / 0 |
| 8 Length / ritual repetition | – | A | – | – | – | A | 1 / 1 |
| **Contradicted absence value in ③/⑤ (change 1)** | 0 | 0 | **1** | 0 | 0 | 0 | 1 / 0 |
| Dropped source uncertainty marker | 0 | 0 | 0 | 0 | 0 | 0 | 0 / 0 |

- **Change 1's row.** The blind pass found one contradicted absence value: S03 = P0 r3, where ③ Buttons reads "등재 없음" while the input's G block lists a later remix and the same column writes Static as "등재 없음(이후 파생만)". Astra's audit of S03 found the same cell independently. Neither reviewer reported one on any P6 output. The P6 outputs' ③ legends name a comparison range: r1 "부재 값은 S1–S8 대조 범위 안에서만 쓴다"; r3 "'미확보'·'미등재'는 S1–S8, ②, ⑤와 대조한 결과다"; r2 "대조 범위: 입력 블록과 S1–S8". Round 5's two P5 failures of this kind (r1 ⑤, r3 ③) did not recur. One P0 case in three runs is a thin baseline, so this is consistent with change 1 working, not proof of it.
- **Defect 3 on P6** (2 marks) sits outside the row's scope, in ②:
  - r2 K6, "누가 어느 부분을 맡았는지는 확인하지 못했다", while seq 12 gave partial shares;
  - r3 C7, "John Kirby 동일인 근거 미확인", while S7 Personnel lists John Carroll Kirby on the same tracks.

  Both are unchecked "not confirmed" statements in prose. Change 1 deliberately covered only the tables.
- **Defect 2** is down from 6 to 3. P6 r2's K6 misplacement is the D4 FAIL above.
- **Defect 4** reads higher than round-5 P5's 2 marks. That is expected packet drift: both reviewers now hold R-a and the Qobuz row, and the defect text includes "a single encyclopedia used for credits". The only P6 output without it is r3, the one that opened the row.
- **Defect 6** is 3 on both arms. Change 1 did not add any. P6 r3's marks are the Synthesizer 5/9 name merge in C7.
- **Dropped uncertainty markers: 0 in all six.** The scan used round 5's hedge regex over every tool result.
  - P6: r2 "Lacy reportedly told The Guardian … seven-month relationship" is not in the note. r3 "Lacy reportedly produced about 90%" comes from a Wikipedia line; the note instead quotes Complex's direct quote, which carries no hedge (seq 12). The rest are summariser comments.
  - P0: 7 hits, all summariser comments or claims not in the note.

## Token use

| Part | Input tokens (cache-inclusive) | Output tokens |
|---|---:|---:|
| Claude generation, 6 notes | 2,534,389 (208,267–983,529 each) | 95,333 |
| Claude review, 7 audits | 1,051,478 (95,851–236,474 each) | 98,934 |
| Astra review, 7 audits (no web) | 313,330 (37,605–55,615 each) | 21,441 |
| Comparatives (Astra / Claude) | 33,500 / 36,291 | 2,878 / 12,302 |
| Fidelity check (Astra / Claude) | 17,839 / 10,588 | 371 / 3,169 |

## What the round shows

1. **Change 1 did what it was aimed at, on this evidence.** 0 contradicted absence values in P6's tables against 1 on P0, and round 5's two failure sites did not recur. Every P6 ③ legend states its comparison range.
2. **P6 keeps P5's gains.**
   - FAIL marks 2 vs 8.
   - Length 0.813×, the lowest ratio so far.
   - Defects 1, 2 and 5 down.
   - No dropped markers.
   - No allegation left open.
3. **What stopped it is an attribution slip in prose, not in the tables.** A quote received in a multi-link search summary was filed under the first link, which does not contain it.
   - Both reviewers proposed rules for this independently: Astra's point 5 ("통합 요약을 개별 매체에 임의 배정하지 않고") and Claude's point 1 (quotes only of wording actually received from that source).
   - P4's per-claim attribution rule ("받은 문서가 다른 매체를 지목하면…") does not cover a summary that names no document.
4. **D6 now reads cleanly as a producer behaviour.** Under R-a–R-c both reviewers, the comparatives and the sentinel agree on one line: the run that opened the Qobuz row is BORDERLINE, and every run that did not is FAIL. It binds nothing in this phase (owner, (a)). If the owner wants D6 to move, it is now clearly a producer-side question.
   - Both comparatives propose putting R-a–R-c into the producer prompt: Astra's point 2 and Claude's point 3.
5. **Remaining overlaps in the two comparatives, not taken here:** a conflict rule that keeps "observed difference" and "cause unknown" apart (Astra 3, Claude 2), and disclosure of name merges in aggregates (Astra 4, Claude 5).

## Open for the owner (recorded, not decided here)

- **What comes next.** The options the record supports:
  - another bounded round from P6 with one change aimed at the r2 failure (a received summary's quote is attributed to the summary, not to one of its links);
  - the same plus R-a–R-c as a producer rule. That is a second change, aimed at a non-binding dimension, so it would confound the first. The two would be better separated;
  - preparing Stage C. That needs the §6 manual and §7 floors, deferred on 2026-10-19.
- P6 does not replace P5 as the development candidate. P5 stays the base under the round rule.
- The D4 confirmation decides this round's verdict, and it is recorded above together with its counter-reading.

## Publication

Every record that embeds the Gemini Rights catalog block had its owner-collection line redacted, listed in `PUBLICATION-REDACTIONS.json` with the original hashes. A token scan in plain and JSON-escaped forms then found 0 hits. `review/build-report.json` keeps the pre-redaction packet hashes, which match the bytes actually dispatched.
