# Stage B round 4 — predeclared scope (frozen before dispatch)

- Parent: `docs/rfcs/CHORE-research-model-evaluation.md` §B. Contract: `criteria/acceptance-v1.md` (v1). Anchors: `criteria/a2-anchors/anchors-v1-rc.md` (anchors-v1).
- Predecessor: `../round3/` (neither P3 nor P3G advanced; length was the only unmet condition in the Claude CLI lane; `../round3/RESULTS.md`).
- Date: 2026-10-20. Prepared by the orchestrating session (`claude-opus-5-5`) and reviewed read-only by a Fable subagent before the owner saw it. The review raised 12 findings and no blocker. Each was checked against the files and all 12 were applied. Three changed P4's text: §4 A now agrees with the ①-only rule, the tool's demand for a source list is satisfied by ⑤, and the character unit is defined. The others are the cut order, whole credit rows, the (c) counting unit, the inert D6 term, attribution of change 4, defect 5 in (d), the order of the r3 pair, and rerun eligibility.
- **Owner confirmed this scope in chat on 2026-10-20 ("이대로 확정"), before any round-4 dispatch, with 3 runs per cell and the D6 limitation in §5 stated in the question.**
- This is a **development round**. Its verdict is a model-proxy development judgement, not an acceptance-v1 pass. Nothing here touches the confirmation or calibration albums, the owner's 30–60 h budget, or production.

## Owner decisions recorded here (chat, 2026-10-20, after ws #1155, before this round was drafted)

1. **No annotation arm in round 4.** Length is fixed first. Genius annotations come back later as a much smaller block holding only the annotations that mention a statement, in a separate round.
2. **D6 is judged by the Claude reviewer alone.** The no-web Astra reviewer's D6 is excluded from agreed-FAIL counting. All other dimensions keep the agreed-FAIL rule.

Carried over unchanged: the Codex producer lane stays discontinued (owner, 2026-10-19, `../round3/ROUND.md` §10); generation runs in the Claude CLI lane only. Astra stays a reviewer of Claude-lane outputs and the sentinel, with no web tool. The three scoring-manual gaps (`../round3/ROUND.md` §7) stay deferred.

## 0. Changes from round 3

| Item | Round 3 | Round 4 | Why |
|---|---|---|---|
| Candidate | P3, P3G | **P4 = P3 − edit 3 + 3 overlapping comparative points + a length cut** | `../round3/RESULTS.md` §"Proposed direction" |
| Arms | P0 / P3 / P3G | **P0 / P4** | owner decision 1 |
| Environments | Claude CLI + Codex | **Claude CLI only** | owner, 2026-10-19 |
| Runs per cell | 2 | **3** | see §4 |
| D6 counting | both reviewers | **Claude reviewer alone** | owner decision 2 |
| Everything else | — | unchanged: Gemini Rights only, same dispatched input bytes, sentinel, `--safe-mode`, D7 not assessed, no-web Astra | |

## 1. Prompts

| Role | File | sha256 |
|---|---|---|
| Control P0 | `prompts/P0.md` (byte copy of rounds 1–3 P0) | `f6c3a6277f4d6e4a5b7a1a978820e5c592e2a24151bc022c87d2f9cb290a8d2f` |
| Candidate P4 | `prompts/P4.md` (frozen after the §1 fidelity check; rc is `freeze-check/P4-rc.md`, `41d23244…`) | `db9252502e611f696d738ed0ce1b2f0d8ed5edd9db3f83638042b78cab459e55` |

P4 = round-3 P3 with these changes (`prompts/P3-to-P4.diff`; P3 14,710 → P4 16,444 bytes, P0 12,650; full contrast `prompts/P0-to-P4.diff`):

1. **Revert edit 3 (§6).** Delete "모든 집계와 확인률의 분자는 ③ 점검표에서 센다. 요약과 본문의 수치는 점검표와 같아야 한다." This returns §6 to P2's numerator wording. In round 3, numerator inconsistency (defect 6) was absent from both P0 runs and present in both P3 runs.
2. **Attribution per claim to the document actually received (§4 B).** Both comparatives proposed this (Astra 2, Claude 4). A claim's source is the document whose text this run actually received. When that document names another outlet, the received document stays the source, and the note says the outlet is relayed ("X에 실렸다고 전함"). Each claim carries its own source, never one bundle for several claims. Scope qualifiers ("part of", track vs album) keep the received document's wording. In round 3, the defect-2 marks on P3 · r1 were mis-attributions of this kind (S07: a quotation bundled onto S2 and S3; timing attributed to the Guardian through S8 and S6), not access-label promotions.
3. **Credit role strings verbatim, including summary columns, legends and aggregates (§6).** Both comparatives proposed this (Astra 3, Claude 3). It generalises P2's "원래 역할 필드를 보존한다".
4. **Delete repeated access explanations and memory-based counts (§4 A, §8).**
   - Access limits and the received tool-output kinds are written once, in ①, and ④'s gap items refer to ①. There is no separate access-failure list. §4 A's per-source failure record becomes "반영한다 in ①", so it no longer rebuilds one. Both comparatives proposed this deletion (Astra 5, Claude 5).
   - Search and fetch counts and response status codes are not written, and a stopped branch names the materials checked rather than a count. This comes from Claude 5 alone, which still allowed counts copied from tool logs, plus round-3 data: S07 wrote "검색 2회", and Claude's audit counted 4 relevant searches in the trace.
5. **Length cut (§8, §10).** Orchestrator-derived from round-3 data, not a reviewer proposal.
   - The length rule now covers the whole note: "노트 전체는 부록과 URL을 포함해 6,000자를 넘기지 않는다". The count includes spaces, tables, markdown symbols and URLs, which is how (e) measures it. This replaces "URL과 부록을 제외하고 1,800~3,000자를 목표로 한다".
   - Why: round-3 Claude-lane notes ran 6,696–10,070 characters, with ⑤ at about 1,800–3,670. The old target excluded ⑤, so it never applied to the part that grew most. Bodies without ⑤ also overshot the 3,000 target by 1.7–2.1×.
   - The cap does not guarantee (e). If P0 behaves as in round 3, the bar is 1.10 × 7,150 = 7,865, so P4 may overshoot 6,000 by about 1.3×. If P0's median falls near round-2 P0 · r2 (5,431), the bar is about 5,974, below the cap itself. "이는 채워야 할 할당량이 아니다" stays.
   - A cut order was added to the final checklist: ⑤ excerpts first, then ②'s limitation text, then ④. ③ and the credit role strings are never cut. Length pressure must not land on the rows D6 is judged on.
   - Deleted: "상한을 넘길 때는 핵심 근거가 왜 추가로 필요한지 설명한다." It was an escape clause, and an explanation adds text.
   - ⑤ is redefined. It holds a one-line-per-source list (ID, markdown hyperlink, author/outlet, date), positions and excerpts not already in the body, and the **whole row** (per §6) of every track whose credits differ between sources. It does not hold a restatement of body content or a list of excluded or deferred items. Round-3 S07 carried a "제외·보류" table, and also a trailing "Sources:" list repeating ⑤-1's links (938 chars; Astra defect 8). That list answers the WebSearch tool's own result text ("REMINDER: You MUST include the sources above in your response to the user using markdown hyperlinks", 13 times in one round-3 run). P4 therefore does not forbid it; ⑤'s hyperlinked list is declared to satisfy it.

Considered and not taken:
- **Access label by actual tool output (both comparatives, point 1).** P3 edit 1 already defines `원문 확인` by unprocessed text received in this run, and round 3's remaining defect-2 marks were attribution errors, which change 2 targets. No further label text.
- Claude's new `[가공 요약 경유]` status: a new label, and one reviewer only.
- Claude's quotation-excerpt rule (original-language passage plus translation, portable positions) and Astra's absence/aggregate cross-check: one reviewer each.
- The per-track checklist stays, as in round 3.

**Pre-freeze fidelity check** (as rounds 1–3): one fresh-context dispatch each to `gpt-6-astra` (no web) and `claude-opus-5-5` (safe mode) over the two round-3 comparatives, `../round3/RESULTS.md` §"Proposed direction", and `prompts/P3-to-P4.diff` (`freeze-check/`). Each answers per change: applied faithfully / scope creep / new defect, then FREEZE or MATERIAL OBJECTION. A material objection is applied once, toward the stricter wording, without a second check. The frozen hash replaces the rc hash above, and the change is kept as `freeze-check/rc-to-frozen.diff`.

**Result (2026-10-20).** Both reviewers rated the revert and changes 2–4 *applied faithfully*, with no scope creep and nothing album-specific. Both answered MATERIAL OBJECTION, and every objection was about the length cut or ⑤:
- **Cut order** (both). "⑤의 발췌, ②의 한계 서술" could remove a kept claim's only excerpt, limitation or conflict, which leads to status inflation. Claude added that excerpts may hold the only position anchor for a relayed quotation (D5).
- **⑤ dropped `검증·상충 기록`** (Claude). A conflict recorded only in the appendix would have had nowhere to go.
- **"따로 만들지 않는다" forbade the tool's source list** (Claude). That contradicted this ROUND.md, which says P4 does not forbid it.
- **"중단 이유는 … 적는다" was a new recording duty with no location** (Claude).

Applied once, merged toward the stricter wording, without a second check. The cut now removes only unneeded excerpts (positions stay), duplicate limitation text and non-core ④ items. It never removes the sole evidence or limitation of a kept claim. If the note is still over, a low-priority claim goes together with the evidence only it needs. ③, role strings and ⑤'s credit rows are never cut. ⑤ keeps conflict records, and the tool's source list is satisfied by ⑤'s list, no longer forbidden. A stopped branch is written only as a result-changing gap in ④, naming the materials, not counts. Records: `freeze-check/` (`runs/astra-p4-fidelity`, no web, 0 tool calls; `runs/claude-p4-fidelity`).

## 2. Producer

| Environment | Model | Effort | Tools | CLI |
|---|---|---|---|---|
| Claude CLI | `claude-opus-5-5` | medium | WebSearch + WebFetch | 2.1.303, `--safe-mode` |

Same CLI version as round 3, checked 2026-10-20. Round 4 is compared with round-4 P0 only, never pooled with earlier rounds. The WebFetch confound (summarised fetches) is unchanged and matches production's tool set (`../round3/ROUND.md` §2). Any Claude trace that is not instruction-clean (a hook event, `memory_paths`, or a tool set other than WebSearch + WebFetch) is a harness failure, eligible for its one `-rerun` (§4).

Astra review lane: ChatGPT.app bundled `codex-cli 0.163.0-alpha.10.2` (checked 2026-10-20). The bundle auto-updates, so the version is checked again just before the first review dispatch, and any change is recorded in RESULTS.md.

## 3. Album and inputs

`gemini-rights` — Gemini Rights, Steve Lacy, 2022-07-15, 10 tracks. The round-1–3 dispatched bytes are reused unchanged, from `~/.local/share/myblog-research/stage-b-round3-inputs/` (`gemini-rights.txt` sha256 `fcdea93c…`, `run-block.txt` `259ecbdf…`), copied to `stage-b-round4-inputs/`. No annotation block. No prod re-render.

All P4 changes were derived from this album's outputs, so a pass is a development result on training material. Advancement stays conditional on Stage C's held-out panel.

## 4. Runs and limits

- 2 arms × 1 environment × 1 album × **3 runs** = **6 generations**. IDs `cl-<P>-gemini-rights-r<n>`, P ∈ {P0, P4}.
- **Why 3 runs.** Condition (e) is the one round 3 failed, and it is a two-sample median. Claude-lane Gemini P0 lengths across rounds 2–3 were 5,431, 6,696, 7,068 and 7,604: a 2,173-character spread from an unchanged prompt and input. With 2 runs, one long or short run moves the median by half that. With 3, the median ignores one outlier. The cost is 2 more generations and 4 more audits, within the budget the dropped Codex lane freed.
- Order (counterbalanced): r1 P4, r1 P0, r2 P0, r2 P4, r3 P0, r3 P4. Serial.
- Limits, rerun and preservation rules as round 3 §4: 1,500 s ceiling, no automatic retry, one `-rerun` per harness failure, Bash `run_in_background`, no redispatch of a claimed ID.

## 5. Review

As round 3 §5 and §10. Labels come from one `secrets.SystemRandom` draw, made after all 6 outputs have an outcome. Packets and the defect list are unchanged.

- **Claude** (`claude-opus-5-5`, safe mode, web tools) audits all 6 outputs and the sentinel, then writes one comparative over its 7 reports.
- **Astra** (`gpt-6-astra`, no web) audits the same 7 and writes one comparative over its 7. It still records D6, but D6 is reported descriptively and enters no count (owner decision 2).
- **Sentinel.** The same round-1 S03 (Claude CLI · Gemini · P1; D6 FAIL agreed in round 1), relabelled into the pool. Control: Astra must give a D6 FAIL, as in round 3. Claude's control is the same D6 FAIL. Claude failed it in rounds 2 and 3, with no FAIL on any sentinel dimension. Round 4 makes Claude the only D6 judge, so its sentinel levels are reported **next to the verdict**. So is the number of P4 and P0 outputs whose Claude D6 is as severe as Claude's sentinel D6 or more severe (PASS < BORDERLINE < FAIL); that number is descriptive only.
- **Known limitation of decision 2, stated with its number.** Claude gave **0 D6 FAILs in 30 per-output audits** over rounds 2–3 (round 2: 8 PASS / 9 BORDERLINE; round 3: 7 / 6, unchanged by calibration). Unless that changes, the D6 clauses of (a) and (c) cannot fire, and D6 constrains P4 only through the descriptive side table. This is recorded as a consequence, not as a reason to change the decision.
- **Comparative brief wording.** Each brief names only the reader's own report count ("seven reports"). In round 3 the line "thirteen for one reviewer, seven for the other" confused both reviewers.
- Known leakage: the ① tool-output line and the absence of a separate failure list can reveal P4.
- Budget: Claude 7 + 1, Astra 7 + 1 = **16 review dispatches**, plus 2 fidelity-check dispatches. Per account: Claude 6 + 1 + 7 + 1 = 15; Astra 1 + 7 + 1 = 9.

## 6. Decision rule (predeclared)

P4 advances only if all hold:
- (a) after comparative calibration, no P4 output (3 runs) has an **agreed** FAIL. For D1–D5, agreed means both reviewers FAIL the same dimension, or one does and the orchestrator confirms it against sources, with the check recorded. For D6, a Claude FAIL counts on its own (owner decision 2).
- (b) no gate allegation on a P4 output remains unresolved; the owner adjudicates any that remain.
- (c) after calibration, P4's FAIL marks summed over its 3 runs are no more than P0's. A mark is one (run, reviewer, dimension) FAIL, as in round 3, so a dimension FAILed by both reviewers counts twice. Marks counted: D1–D5 from either reviewer, and D6 from Claude only. Astra's D6 is excluded.
- (d) the recurrence of each pilot defect is listed per P4 output, and defects 2, 4, 5, 6 and 8 (targeted by changes 2, 3, P3 edit 2 kept in P4, 1 + 4, and 5) are compared against round-4 P0.
- (e) the median `output.md` length (Python `len`, characters) of P4's 3 runs is no more than 1.10 × the median of P0's 3 runs.

With fewer than 3 usable outputs in either arm, the round gives no verdict and reports incomplete. A run lost to a harness failure gets its one `-rerun` first. Every arm comparison reports all 3 runs' values, not a median alone. Astra's D6 levels and the round-3 D6 counting are shown in a side table, so the effect of decision 2 is visible.

## 7. Owner time

Confirmation of this scope before any producer output. Adjudication of any surviving gate allegation (0–1 h). Nothing is drawn from the confirmation budget.

## 8. Publication

As round 3 §9: every record embedding the Gemini Rights catalog block has the owner-collection line redacted before push (`PUBLICATION-REDACTIONS.json` with dispatched-byte hashes), followed by a token scan with 0 hits required. Originals stay outside the repository. There is no annotation block this round.
