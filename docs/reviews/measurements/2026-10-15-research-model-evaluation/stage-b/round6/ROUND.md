# Stage B round 6 — predeclared scope (frozen before dispatch)

- Parent: `docs/rfcs/CHORE-research-model-evaluation.md` §B. Contract: `criteria/acceptance-v1.md` (v1). Anchors: `criteria/a2-anchors/anchors-v1-rc.md` (anchors-v1).
- Predecessor: `../round5/`. P5 advanced under the round-5 rule (FAIL marks 3 vs 9, length 0.879×, no confirmed single FAIL), but change 3 did not stop unchecked negative claims: two of three P5 runs wrote "없음" / "받지 못했다" against material they had received (`../round5/RESULTS.md`, defect 3). Then the D6 instrument check (`../d6-measurement/RESULTS.md`).
- Date: 2026-10-20. Prepared by the orchestrating session (`claude-opus-5-5`) and reviewed read-only by a Fable subagent before the owner saw it. The review raised 13 findings and no blocker. Each was checked against the files.
  - Two (tooling still counting D6; packet builders without the D6 blocks) described files the review read before they were edited. Both were already fixed and tested (§5, §6).
  - The other 11 were applied. Two changed P6's text: part (b) gets a consequence clause, and part (a) gets a referent for lines under the table and the range rule of §5. The rest: the (d) row unit made arm-symmetric and counted blind, the harness-failure rule restored to round 5's, the Buttons fact, Astra's point 4 cited, recorded hashes and versions, reference re-check details, a packet-drift caveat, and the sentinel wording.
- **Owner confirmed this scope in chat on 2026-10-20 ("이대로 확정"), before any round-6 dispatch.** The question stated the single change and its ⑤ extension, 3 runs per cell, D6 as descriptive only, the reviewer-packet additions with the reference re-check, the (e) noise risk, and the budget.
- This is a **development round**. Its verdict is a model-proxy development judgement, not an acceptance-v1 pass. Nothing here touches the confirmation or calibration albums, the owner's 30–60 h budget, or production.

Carried over unchanged from the owner's earlier decisions:
- The Codex producer lane stays discontinued (2026-10-19). Generation runs in the Claude CLI lane only.
- Astra reviews Claude-lane outputs and the sentinel, with no web tool.
- No annotation arm (2026-10-20).
- D6 is judged by the Claude reviewer alone (2026-10-20). Astra's D6 enters no count.
- **R-a to R-c are the development-round D6 rules from this round on** (2026-10-20, `../d6-measurement/CHECK.md` head, decision 2).
- **D6 does not bind the round rule** (2026-10-20, owner chose (a) after the D6 check). It is scored under R-a–R-c and reported descriptively. D6 calibration belongs to Stage C (acceptance-v1 §6).
- The scoring-manual gaps stay deferred, apart from blank 3, which R-a–R-c fill for development rounds only. §6 is not frozen and the §7 floors stay deferred (2026-10-19).

## 0. Changes from round 5

| Item | Round 5 | Round 6 | Why |
|---|---|---|---|
| Candidate | P5 | **P6 = P5 + change 3 placed at the tables** | `../round5/RESULTS.md` §"What the round shows" 3; handed over as the next step after the D6 decision |
| Arms | P0 / P5 | **P0 / P6** | P5 is not re-run. Its round-5 values appear descriptively only and are never pooled. |
| Review packet | round-5 packet | **+ R-a–R-c and the frozen Qobuz reference**, for both reviewers (§5) | Owner decision 2 of the D6 check |
| D6 in the decision rule | Claude D6 FAIL counted in (a) and (c) | **descriptive only** | Owner decision (a) |
| Everything else | — | unchanged: Gemini Rights only, same dispatched input bytes, Claude CLI only, 3 runs per cell, sentinel, `--safe-mode`, D7 not assessed, no-web Astra | |

## 1. Prompts

| Role | File | sha256 |
|---|---|---|
| Control P0 | `prompts/P0.md` (byte copy of rounds 1–5 P0) | `f6c3a6277f4d6e4a5b7a1a978820e5c592e2a24151bc022c87d2f9cb290a8d2f` |
| Candidate P6 | `prompts/P6.md` (frozen after the fidelity check; the rc is `freeze-check/P6-rc.md`, `31117723…`) `ac7c63023f66ffcd2dbadda6fe4509f9651037e4aea8a084cb7630f40f26af74` |

P6 is round-5 P5 (`prompts/P5.md`, `eec6451a…`, byte copy) with one change, in two places. The diff is `prompts/P5-to-P6-rc.diff`. Sizes: P5 17,753 bytes, P6 rc 18,431 (+678). After freeze, `prompts/P0-to-P6.diff` gives the full contrast with P0. It adds no section and no recording list.

**Change 1 — the exclusive/negative check moves to where the table values are written.**
- **(a) §9, one sentence after the ③ column list.** Before a ③ cell or a line under the table gets an absence or exclusive value ('없음', '0', '~곡뿐' and the like), the producer compares it with what it already received about that track (for a line under the table, those tracks): input block, opened pages, search results, ③'s other cells, and ② and ⑤. If an item is there, the value is not written; the item or its location is. The comparison range follows §5: once in a column head or the legend for cells, in the sentence itself for a line under the table.
- **(b) §6, one clause in the selective-transcription rule.** Before writing that a missing role was "받지 못했다", the producer compares with material already received. If the role is there, it is transcribed or its location is given.
- Targets, from `../round5/RESULTS.md`:
  - P5 r3: ③ "참조 관계 없음" on Static and Buttons while the input's G block lists a remix and samples of Static and a remix of Buttons; and the line under ③, "실제로 제작 과정까지 다룬 곡은 5번 Bad Habit 1곡", while ③'s own evidence column lists C6 on tracks 2, 3, 8 and 10.
  - P5 r1: ⑤ "연주·엔지니어링 역할은 받지 못했다", contradicted by the run's own seq-4 fetch.
- **Why this shape.** P5's change 3 is a general rule in §5's prose, far from ③. All three failures sit in a table or in the sentence that introduces one. The rule is restated where those values are written, and §5's general rule stays as it is.
- **Reviewer support.** Astra's round-5 comparative point 4 ends "부재 보고 전에는 이미 제공된 자료를 재대조한다". Claude's comparative lists "받은 자료를 '받지 못함/없음'으로 기록" (S02, S04, both P5) as a model-side recurring defect but proposes no rule for it. So this is one reviewer's proposal plus a defect both saw, the same footing as round 5's change 3.
- **Orchestrator extension, declared:** part (b). The handover named the ③ cells. r1's failure is in ⑤, and leaving it out would leave one of the three observed cases untargeted.
- **Known risk.** Round 3's edit 3 ("numerators from the checklist") created defect 6. Change 1 adds no counting rule and asks for no recount. It does make a '~곡뿐' line under ③ agree with ③'s own cells, which is close to that territory, so defect 6 is watched in (d).

Considered and not taken:
- **A producer rule built from R-a–R-c** ("prefer a distributor or store credit row"). D6 does not bind this round, and a second change aimed at a non-binding dimension would confound change 1. P5 §6 already asks for a booklet / distributor comparison in the cases that matter. The D6 table (§6) reports how often each arm used the authoritative row.
- **Round-5 comparative proposals.**
  - Both reviewers' point 1, the `[원문 확인]` label. On P5 it is already moot: all three P5 outputs declared no `[원문 확인]`, and the defect in Claude's table sits on P0 and the sentinel.
  - Role strings (Astra 2, Claude 5) are P5's change 1, already in.
  - Aggregates: Astra 3, inclusion rules and a recount from the final table; Claude 3, no unit-level claims from an aggregate without unit rows. The two overlap only in topic. Astra's recount is the shape of round 3's edit 3, which created defect 6.
  - Single-reviewer points: Claude's quote-mark rule (2) and speaker classes (4); Astra's de-duplication (5), and the conflict-test half of its point 4 (the absence half is change 1).

**Length.** The change asks for no new text in the note. If anything, a contradicted "없음" becomes an item or a pointer. Round-5 P5 ran 5,808 / 7,366 / 7,857 against round-5 P0's median 8,382. Round-5 P0 also ran about 20 % longer than round-4 P0 on identical bytes, so (e) carries run-to-run noise of that size. The rule is unchanged.

**Pre-freeze fidelity check** (as rounds 1–5): one fresh-context dispatch each, to `gpt-6-astra` (no web) and to `claude-opus-5-5` (safe mode). Each reads:
- the two round-5 comparatives' proposal sections,
- `../round5/RESULTS.md` §"What the round shows",
- this change list,
- `prompts/P5-to-P6-rc.diff`.

Each answers per part, (a) and (b): applied faithfully / material distortion / missing; scope creep; new defect. Each then returns FREEZE or MATERIAL OBJECTION. A material objection is applied once, toward the stricter wording, without a second check. The frozen hash replaces the placeholder above, and the edit is kept as `freeze-check/rc-to-frozen.diff`. Records go in `freeze-check/`.

**Result (2026-10-20).** Both on the fresh-context brief `75d023b3…` (`freeze-check/header.txt` + `doc1–4.txt`; the same assembly reproduces round 5's `59b3d03f…`), 0 hook events and 0 tool calls each.
- **Astra** (no web): CONFIRM FREEZE. Both parts were applied faithfully, with no scope creep and no new defect. It noted that '~곡뿐' touches the numerator area but asks for no recount.
- **Claude** (safe mode): MATERIAL OBJECTION on part (b), for attribution upgrade. "그 역할을 옮기거나" lets a role found in another source be transcribed into the named row being copied, which hides which source lists it. Its replacement text was applied verbatim, once, without a second check: "그 역할을 원래 출처와 함께 따로 옮기거나 위치를 적는다. 다른 출처에서 찾은 역할을 옮기고 있는 행에 합치지 않는다." The edit is `freeze-check/rc-to-frozen.diff`.
  - Its non-blocking note ("5의 규칙" → "§5의 규칙") was not taken, because P5 already cites its own sections as "6의 규칙대로".
- Frozen P6: 18,544 bytes. Diffs: `prompts/P5-to-P6.diff`, with the full contrast in `prompts/P0-to-P6.diff`. The rc diff `prompts/P5-to-P6-rc.diff` is kept as the reviewed input.
- Combined prompt hashes (prompt + `gemini-rights.txt` + `run-block.txt`): P0 `9d2202d3…`, equal to rounds 4–5; P6 `03a85cba…`. Both are pinned in `manifests/`, and a runner dry run accepts both.

The frozen scope (this file and `prompts/P6.md`) is committed and pushed before the first generation. The commit sha, and any rebase that rewrites it, is recorded in RESULTS.md.

## 2. Producer

| Environment | Model | Effort | Tools | CLI |
|---|---|---|---|---|
| Claude CLI | `claude-opus-5-5` | medium | WebSearch + WebFetch | 2.1.304 (checked 2026-10-20 at predeclaration; re-checked at dispatch), `--safe-mode` |

- Astra lane (fidelity check and review): ChatGPT.app-bundled `codex-cli 0.163.0-alpha.10.2`, checked 2026-10-20, re-checked before the fidelity and review dispatches.
- A producer run that loads hooks, memory or extra tools is a harness failure, as in rounds 4–5: it gets its one `-rerun` (§4).

- Round 5 ran on 2.1.303; the D6 check on 2.1.304. Round 6 is compared with round-6 P0 only, never pooled.
- A CLI version change between this file and dispatch is recorded. A patch-class auto-update is not a stop; anything else is (§9).

## 3. Album and inputs

- Album: Gemini Rights (Steve Lacy, 2022), standard 10-track edition, as rounds 1–5.
- The same dispatched input bytes as rounds 4 and 5, copied from `~/.local/share/myblog-research/stage-b-round5-inputs/` to `stage-b-round6-inputs/`. sha256 checked at predeclaration: `gemini-rights.txt` `fcdea93c…`, `run-block.txt` `259ecbdf…`, both equal to round 5. The P0 manifests pin the combined prompt hash `9d2202d3…`, which the runner enforces.
- No annotation block, no prod re-render.

All P5 changes, and this one, were derived from this album's outputs. A pass is therefore a development result on training material, and advancement stays conditional on Stage C's held-out panel.

## 4. Runs and limits

- 2 arms × 1 environment × 1 album × 3 runs = **6 generations**. IDs are `cl-<P>-gemini-rights-r<n>`, P ∈ {P0, P6}.
- Order (counterbalanced, as rounds 4–5): r1 P6, r1 P0, r2 P0, r2 P6, r3 P0, r3 P6. Serial.
- A 1,500 s ceiling, no automatic retry, one `-rerun` per harness failure, Bash `run_in_background`, and no redispatch of a claimed ID.

## 5. Review

As round 5 §5, with these differences:

- **D6 rules and reference in the packet.** Every per-output packet adds `<D6_DEVELOPMENT_RULES>` (R-a to R-c, the exact text of `../d6-measurement/build_d6_inputs.py`) and `<D6_FROZEN_REFERENCE>`, plus the D6 check's one LEAD sentence pointing to them. Astra's packet keeps its no-web sentence and gets the same pointer and blocks. The two packets still differ only in the web sentence.
- **Reference freshness.** `../d6-measurement/reference/qobuz-gemini-rights.txt` (Qobuz `zbylnavz5biaa`, captured 2026-10-20) is re-captured by `recheck_reference.py` with the same method before the first generation. Its parser reproduces the frozen ten lines from the D6 check's saved page (checked at predeclaration). If the live ten credit lines match byte for byte, the frozen text is used with its capture note changed to say it was re-checked at round-6 dispatch, and the new file's sha256 goes into RESULTS (it differs from the D6-check bytes in that one line). If they differ, the round stops before generation and the owner is told. This keeps R-b's "accessible when the note was produced" true for round 6. Any P0 or P6 trace that tried a Qobuz page and failed is recorded next to the D6 table.
- **Comparative.** Each comparative brief also carries the R-a–R-c block, so calibration does not undo per-output D6 placements by reading the anchors alone.
- **Tooling** (copied from round 5, edited, and checked in a scratch copy with round-5 outputs as stand-ins):
  - `build_review_inputs.py` imports R-a–R-c from the D6 check's builder. For P5 r3's bytes it produces a packet identical to the D6 check's new packet, apart from label and redaction. Astra's packet differs from Claude's only in the web sentence (diffed).
  - `tally.py` counts D1–D5 only. Replaying round 5's reviews reproduces 3 vs 9 and the agreed FAILs r2 D3, r3 D5. A planted Claude D6 FAIL leaves the count unchanged, and a planted D5 FAIL raises it by one.
  - sha256 at predeclaration: `build_review_inputs.py` `71287123…`, `build_comparative_inputs.py` `cab0a5db…`, `tally.py` `534f8f74…`, `recheck_reference.py` `6c7537f4…`.
- **Packet drift.** Both reviewers now hold the Qobuz row, which can move D2/D5 levels on credit claims in both arms, not only D6. Round 6 compares arms within the round, so the rule is unaffected, but the round-5 column beside it crosses packets. `../d6-measurement/review/tally.json` holds Claude's new-packet D1–D5 levels for the six round-5 outputs as a drift baseline; Astra has none.
- Labels come from one `secrets.SystemRandom` draw, made after all 6 outputs have an outcome. The defect list is unchanged.
- **Claude** (`claude-opus-5-5`, safe mode, web tools) audits all 6 outputs and the sentinel, then writes one comparative over its 7 reports. **Astra** (`gpt-6-astra`, no web) does the same.
- **Sentinel.** Round-1 S03, relabelled into the pool as before. With D6 descriptive, it no longer gates anything. It stays for continuity: it read D6 FAIL under R-b in the D6 check, which had no comparative step and no Astra copy, so its round-6 level shows whether that placement survives both. Its levels are reported next to the D6 table.
- **Orchestrator source check.** Every single-reviewer D1–D5 FAIL on a P6 output is checked against that output's producer trace and the frozen anchors, and the checks are recorded in a table, as in rounds 4–5.
- The comparative brief names only the reader's own report count.
- Known leakage: original-first role strings and the ① tool-output line, both inherited from P4/P5, can reveal P6.
- Budget: 2 fidelity dispatches + 16 review dispatches (Claude 7 + 1, Astra 7 + 1). Per account: Claude 1 + 6 + 7 + 1 = 15; Astra 1 + 7 + 1 = 9.

## 6. Decision rule (predeclared)

P6 advances only if all of these hold:
- (a) After comparative calibration, no P6 output (3 runs) has an **agreed** FAIL on D1–D5. Agreed means both reviewers FAIL the same dimension, or one does and the orchestrator confirms it against sources, with the check recorded.
- (b) No gate allegation on a P6 output remains unresolved. The owner adjudicates any that remain.
- (c) After calibration, P6's FAIL marks summed over its 3 runs are no more than P0's. A mark is one (run, reviewer, dimension) FAIL on D1–D5, from either reviewer.
- (d) The recurrence of each pilot defect is listed per P6 output and compared against round-6 P0, with these targets:

  | Defect | Targeted by |
  |---|---|
  | 3, 5 | change 1 |
  | 4 | P5 change 1, carried; it must not come back |
  | 2, 6, 8 | P4's changes, carried; they must not come back |

  Two extra rows, counted by the orchestrator for every P6 and P0 output, each with the location recorded:
  - **Contradicted absence value (change 1).** The unit is one (output, statement): any statement in ③ (cells and lines under it) or ⑤ that an item or role is absent, not received, or exclusive, while the input block, the run's own trace, or the note's own ②/③/⑤ holds it. The unit does not depend on P6's wording, so P0 can score on it equally. Counted from both reviewers' defect-3/5 prose and from the orchestrator's own pass over ③ and ⑤. **The pass runs over the blind labels S01–S07, and its table is committed before `blind-key.json` is read for analysis.**
  - **Dropped source uncertainty marker** (P5 change 2, carried): as round 5 §6 (d).
- (e) The median `output.md` length of P6's 3 runs (Python `len`, characters) is no more than 1.10 × the median of P0's 3 runs.

With fewer than 3 usable outputs in either arm, the round gives no verdict and is reported as incomplete. A run lost to a harness failure first gets its one `-rerun`.

Every arm comparison reports all 3 runs' values, not a median alone. Round-5 P5's values sit beside them, descriptively only.

**D6, descriptive (not part of the rule).** RESULTS reports, for every output and the sentinel, the Claude D6 level and the route it names (R-a source class, R-b accessibility, R-c narrowing, edition). A separate column, from the orchestrator's reading of the trace, says whether the output's credits rest on the authoritative row (Qobuz `zbylnavz5biaa` or another distributor / store row) or on secondary sources only. A candidate that does not open the authoritative row has its D6 level written as it is, FAIL included. Astra's D6 goes in a side column.

## 7. Owner time

- Confirmation of this scope before any dispatch.
- Adjudication of any surviving gate allegation (0–1 h).

Nothing is drawn from the confirmation budget.

## 8. Publication

As rounds 4–5:
- Every record embedding the Gemini Rights catalog block has its owner-collection line redacted before push. `PUBLICATION-REDACTIONS.json` records the dispatched-byte hashes.
- A token scan must then find 0 hits.
- Originals stay outside the repository.

## 9. Stop conditions

- A non-patch CLI change. (A run that loads hooks, memory or extra tools is a harness failure with one `-rerun`, §2; a second such failure in the same ID stops the round.)
- A re-captured reference that differs from the frozen one (§5).
- Input or P0 combined-prompt hashes that differ from round 5's (§3).
- A rate limit: the lane halts and nothing is redispatched. The round resumes only on the owner's word.
