# Stage B round 4 — results (2026-10-20)

Scope: `ROUND.md`. The owner confirmed it before any producer output, and it was frozen and pushed (`0864a1f`, committed 2026-10-20 02:26 KST) before the first generation; the rebase onto main before merge rewrote it as `607270f` with identical round-4 files. This is a development round. Its verdict is a model-proxy development judgement, not an acceptance-v1 pass.

## Verdict: P4 does not advance. It fails (a) on one orchestrator-confirmed D5 FAIL; length is solved

| Condition (§6) | P4 | |
|---|---|---|
| (a) no agreed FAIL after calibration | **fails** | No dimension is FAILed by both reviewers. One single-reviewer FAIL is confirmed against sources (below): Astra's **D5 on r3**. |
| (b) no unresolved gate allegation on P4 | **open** | Astra raised G4 (medium) on r1. The owner has not adjudicated it, and it cannot change the verdict (see below). |
| (c) P4 FAIL marks ≤ P0's | **holds** | **3 vs 5** |
| (d) pilot defects listed | table below | |
| (e) median length ≤ 1.10 × P0 | **holds** | **6,988 vs 6,952 chars = 1.005×** |

Nothing below is a pass.

### The single-reviewer FAILs on P4, checked against sources

§6 (a) counts a FAIL from one reviewer when the orchestrator confirms it against sources. Every such FAIL on a P4 output was checked against the producer's own trace (`review/web-traces/`) and the frozen anchors:

| Output | FAIL | Check | Result |
|---|---|---|---|
| r3 (S07) | Astra D5: C6 says "S11(Deezer 스니펫)도 같은 네 명이다", but the search result it came from (trace seq 19) says "The layout is ambiguous, so treat that attribution as tentative" | Text matched in the trace. The anchors' D5 FAIL row names "an uncertainty silently resolved" outright, with no consequence condition. The note kept the snippet label but dropped the source's own "tentative". | **Confirmed → agreed FAIL** |
| r3 (S07) | Claude D4: the quotation "written, performed, and produced entirely by Steve" is not recovered from BrooklynVegan (403) | The phrase is in the producer's received search result (seq 19), which attributes it to BrooklynVegan. The note labels it `(S10, 스니펫)`. Non-recovery from the page cannot be checked further. | Not confirmed |
| r1 (S03) | Astra D2: ④-1 says Kirby and Ely Rise "연주자로만 적혀 있다" in S8 (Wikipedia) | S8 as received (trace seq 13) lists Kirby as writer on 1, 5, 6 and Ely Rise on 3, 4, 10. The sentence is literally false. In its producer-comparison context, the point it makes is right: S8 does not list them as producers. D2 FAIL needs a *central* incorrect claim; whether a ④ hand-off item is central is the M2 question that the G4 allegation puts to the owner. | Fact confirmed. FAIL not confirmed: centrality is the owner's call (b) |

The D5 confirmation alone decides (a). Claude's comparative saw the same dropped qualifier and left S07's D5 at PASS, because it "could not see what C6 had settled". The anchors' FAIL wording does not depend on that, so the confirmation stands. The orchestrator is the one applying it, and the owner may overrule it.

**Gate allegations.** P4 r1 has Astra G4 (medium) on the ④-1 sentence above. P0 r3 has two G4 (medium), one from each reviewer, at different locations. All three are unresolved. With (a) failing, the r1 allegation cannot change the verdict, and P0's allegations do not enter §6. In round 1 the owner deferred allegations that could not change the verdict; the same handling is assumed here unless the owner asks.

## What ran

| Part | Result |
|---|---|
| Fable review of the draft | 12 findings, no blocker, all applied (ROUND.md header) |
| Owner confirmation | 2026-10-20, before any dispatch |
| Fidelity check (`freeze-check/`) | Both reviewers: MATERIAL OBJECTION on the length cut / ⑤ wording only; applied once (ROUND.md §1). Astra: no web, 0 tool calls. |
| Generations (`runs/`) | **6/6 success**, no reruns. 248–326 s, 11–18 searches + 12–22 fetches. Every run: 0 hook events, no `memory_paths`, tools exactly WebSearch + WebFetch. No output carries a trailing "Sources" list. |
| Blind draw (`review/blind-key.json`) | 2026-10-19T17:54:35Z, one `secrets.SystemRandom().shuffle` over 6 outputs + sentinel. 0 identity hits in notes or traces. One harness error string in one note neutralised (S04 = sentinel). |
| Per-output audits | **Claude 7/7, Astra 7/7 success.** Claude: 0 hook events, tools WebSearch + WebFetch. Astra: no web tool, 0 tool calls. |
| Comparative calibration | 2/2 success. Astra: 1 change (S06 D1 B → P). Claude: 2 (S05 D2 P → B, S07 D4 B → F). Each brief named only the reader's own seven reports; neither reviewer was confused this time. |
| CLI versions | Claude Code 2.1.303; Astra lane `codex-cli 0.163.0-alpha.10.2`, re-checked just before the review dispatch (unchanged from round 3). |

## Reviewer control (sentinel = S04)

| Reviewer | Sentinel D1–D6 after calibration | Control (D6 FAIL, §5) |
|---|---|---|
| Astra (no web) | P B P P F B | **not met** (D6 BORDERLINE). It met the control in round 3. |
| Claude | P B P P B B | **not met**, the third round running. Still no FAIL on any sentinel dimension. |

- Neither reviewer's D6 separates the sentinel from the candidates this round.
- Claude's D6 is BORDERLINE on the sentinel and on all six outputs. So all 3 P0 and all 3 P4 outputs sit at the sentinel's severity: 6/6, descriptive only (§5).
- Claude has now given **0 D6 FAILs in 37 per-output audits** (rounds 2–4). As ROUND.md §5 predicted, the D6 clauses of (a) and (c) could not fire.
- Astra's D6 runs the other way: FAIL on all three P4 outputs, but BORDERLINE on the sentinel and on two of three P0 outputs. Its D6 is excluded (owner decision 2), and the side table shows what that exclusion did.

## Calibrated levels (D1–D6; D7 not assessed)

| Arm | Run | Label | Astra | Claude | Counted FAILs | Chars |
|---|---|---|---|---|---:|---:|
| **P0** | r1 | S05 | P P B B F *F* | P B B P B B | 1 | 6,952 |
| | r2 | S01 | P P B B F B | P B P P B B | 1 | 9,084 |
| | r3 | S02 | P F P P F B | P F P B B B | 3 | 6,369 |
| **P4** | r1 | S03 | P F P P B *F* | P B P P P B | 1 | 6,074 |
| | r2 | S06 | P P P P B *F* | P B P P P B | 0 | 7,342 |
| | r3 | S07 | P B B P F *F* | P B P F P B | 2 | 6,988 |

Italic = Astra D6, excluded from every count. **Side table (round-3 counting, Astra D6 included):** P0 6 vs P4 6. (c) still holds as a tie, and no extra agreed FAIL appears, because Claude's D6 is BORDERLINE everywhere. P0 r3's D2 is the round's only FAIL shared by both reviewers.

## Pilot recurring defects (A = Astra, C = Claude; per output)

| Defect | P0 r1 | P0 r2 | P0 r3 | P4 r1 | P4 r2 | P4 r3 | Change aimed at it |
|---|---|---|---|---|---|---|---|
| 2 Summary promoted / mis-attributed to an outlet | A C | A C | A C | – | – | – | 2 (with P3 edit 1) |
| 3 Received source under-read | – | – | C | A | – | C | — |
| 4 Role fields narrowed / substituted | A C | A | A | A C | A | A C | 3 |
| 5 Spurious scope conflict / unchecked exclusive | A C | – | A C | A | A C | – | P3 edit 2 (kept) |
| 6 Numerator inconsistency | C | – | A C | – | – | C | 1, 4 |
| 8 Length / ritual repetition | A | A | A | – | A | – | 5 |

Defects 1 and 7: absent everywhere.
- **Defect 2 is gone.** It has 6 marks on P0 (all three runs, both reviewers) and 0 on P4. The attribution rule (change 2) did what round 3's comparatives asked for.
- **Length is solved without new defect-8 marks.** P4's median is 1.005× P0. Its runs (6,074 / 7,342 / 6,988) overshoot the 6,000 cap by up to 1.22×, as ROUND.md §1 expected, yet stay inside the bar. Defect-8 marks: P0 3, P4 1 (Astra only; Claude marked none).
- **Defect 4 did not move** (P0 4 marks, P4 5). The verbatim-role rule (change 3) did not stop translation and narrowing. Claude's comparative traces it to "한국어로 출력하라는 지시"; S07 turned "작곡·작사" into "Composer".
- **Defect 6 fell** (P0 3, P4 1) with edit 3 reverted.
- The confirmed D5 FAIL (r3) is not one of the eight pilot defects. It is a dropped *uncertainty*, not a status promotion.

## Token use

| Part | Input tokens (cache-inclusive) | Output tokens |
|---|---:|---:|
| Claude generation, 6 notes | 2,766,103 (373,194–665,981 each) | 96,494 |
| Claude review, 7 audits | 1,134,870 (111,682–246,070 each) | 90,136 |
| Astra review, 7 audits (no web) | 314,867 (40,313–54,058 each) | 20,423 |
| Comparatives (Astra / Claude) | 32,918 / 35,682 | 2,678 / 12,770 |
| Fidelity check (Astra / Claude) | 18,899 / 12,775 | 795 / 4,775 |

## What the round shows

1. **P4 fixes the round-3 blocker.**
   - Length is back at P0 (1.005×).
   - FAIL marks are below P0 (3 vs 5).
   - Defect 2 is eliminated, and defect 6 is back down.
   - What stops it is one confirmed D5 FAIL: a qualifier the producer received and dropped. That is a narrow, nameable failure, not a regression.
2. **The confirmed FAIL points at the cut.** The new cut order tells the producer to shorten "②의 중복 한계 서술" and "⑤의 불필요한 발췌". It forbids deleting the *sole* evidence or limitation of a kept claim. The fidelity check added that clause, and the producer still dropped a source's own "tentative" from a corroborating line. Whether the cap caused this cannot be shown from one instance. P0 r1–r3 have D5 FAILs too (Astra, all three runs; not confirmed, since P0 is the control).
3. **D6 is unmeasured in this design.**
   - Claude's D6 has no FAIL in 37 audits.
   - Claude's sentinel control has failed three rounds running.
   - Astra's D6 FAILed all three P4 outputs but not the sentinel.
   - Under owner decision 2, P4's credit handling, which both comparatives criticise (defect 4), cannot block it. A later round has to decide this before any pass is trusted, because D6 is acceptance-critical in acceptance-v1.

## Proposed direction for a round 5 (needs predeclaration and owner confirmation)

Claude CLI lane only. Start from P4, which meets (c) and (e). Points where both round-4 comparatives overlap:

1. **Role strings: original first, translation only in parentheses**, everywhere they appear (Astra 2, Claude 2). This targets defect 4, which change 3 did not move.
2. **Keep a source's own uncertainty marker next to the claim** ("tentative", "ambiguous", "reportedly"), and never resolve a mismatch whose cause is unchecked (Astra 3 and 5, Claude 4). This targets the confirmed D5 FAIL. It is also a guard on the cut order: such markers are not "중복 한계 서술".
3. **Exclusive and negative statements** ("only", "entirely", "~에만", "언급하지 않음") are checked against material already received before they are written (Claude 4, Astra 3). The r1 ④-1 sentence is this kind of claim.

Not overlapping, so not proposed: Claude's alias rule (3) and derivability rule (5); Astra's aggregate rule (4). The access-label redefinition (both 1) is already P3 edit 1. The D5 data shows that label promotion, which edit 1 targets, is gone from P4: Astra's P4 D5 marks are B, B, F, and the F is the dropped qualifier.

Open for the owner, not decided here:
- How D6 is measured. In rounds 2–4 neither reviewer gives a D6 that separates the sentinel. The owner's 2026-10-20 decision stands and is not re-asked; this is a measured consequence to weigh before Stage C.
- Whether the r1 G4 allegation (M2: is the ④-1 sentence central?) is adjudicated or deferred. It cannot change this verdict.

## Publication

Every record that embedded the Gemini Rights catalog block had its owner-collection line redacted: 34 files, listed in `PUBLICATION-REDACTIONS.json` with their original hashes. A scan for the bucket token in plain and JSON-escaped forms then found 0 hits. There was no annotation block this round. `review/build-report.json` keeps the pre-redaction packet hashes, which match the bytes actually dispatched.
