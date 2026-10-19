# Stage B round 5 — predeclared scope (frozen before dispatch)

- Parent: `docs/rfcs/CHORE-research-model-evaluation.md` §B. Contract: `criteria/acceptance-v1.md` (v1). Anchors: `criteria/a2-anchors/anchors-v1-rc.md` (anchors-v1).
- Predecessor: `../round4/`. P4 did not advance because of one D5 FAIL that the orchestrator confirmed against sources: r3 dropped a search result's own "tentative". It met (c) and (e): FAIL marks 3 vs 5, length 1.005×. See `../round4/RESULTS.md`.
- Date: 2026-10-20. Prepared by the orchestrating session (`claude-opus-5-5`) and reviewed read-only by a Fable subagent before the owner saw it. The review raised 10 findings and no blocker. Each was checked against the files and all 10 were applied. Four changed P5's text: the language line names both exceptions, change 2's mismatch clause is bound to the `상충` definition, the role-string example no longer uses `Composer` (the field S07 substituted), and the range phrase is short. The others are change 2's attribution, the (d) row's counting unit, the push-before-dispatch rule, the §6 heading, and the recorded CLI and input hashes.
- **Owner confirmed this scope in chat on 2026-10-20 ("이대로 확정"), before any round-5 dispatch. The question stated 3 runs per cell, the length risk to (e), and the inert D6 gate.**
- This is a **development round**. Its verdict is a model-proxy development judgement, not an acceptance-v1 pass. Nothing here touches the confirmation or calibration albums, the owner's 30–60 h budget, or production.

Carried over unchanged from the owner's earlier decisions:
- The Codex producer lane stays discontinued (2026-10-19). Generation runs in the Claude CLI lane only.
- Astra reviews Claude-lane outputs and the sentinel, with no web tool.
- There is no annotation arm (2026-10-20). Genius annotations return only as a much smaller block in a separate round, and only when the owner raises it.
- D6 is judged by the Claude reviewer alone (2026-10-20). Astra's D6 is excluded from agreed-FAIL counting.
- The three scoring-manual gaps (`../round3/ROUND.md` §7) stay deferred.

The D6 measurement question and the P4 r1 G4 allegation remain open for the owner (`../round4/RESULTS.md`). This round neither decides them nor depends on them.

## 0. Changes from round 4

| Item | Round 4 | Round 5 | Why |
|---|---|---|---|
| Candidate | P4 | **P5 = P4 + 3 overlapping comparative points** | `../round4/RESULTS.md` §"Proposed direction for a round 5" |
| Arms | P0 / P4 | **P0 / P5** | P4 is not re-run. Its round-4 values appear descriptively only and are never pooled. |
| Everything else | — | unchanged: Gemini Rights only, same dispatched input bytes, Claude CLI only, 3 runs per cell, sentinel, `--safe-mode`, D7 not assessed, no-web Astra, D6 counted from Claude only | |

## 1. Prompts

| Role | File | sha256 |
|---|---|---|
| Control P0 | `prompts/P0.md` (byte copy of rounds 1–4 P0) | `f6c3a6277f4d6e4a5b7a1a978820e5c592e2a24151bc022c87d2f9cb290a8d2f` |
| Candidate P5 | `prompts/P5.md` (frozen after the fidelity check; the rc is `freeze-check/P5-rc.md`, `203f59f5…`) | `eec6451a7bbe7239ad57cec6af7477390ddde45eb469abc759775212b8ddf987` |

P5 is round-4 P4 with the changes below. They are in `prompts/P4-to-P5.diff`; the full contrast with P0 is `prompts/P0-to-P5.diff`. Sizes: P4 16,444 bytes, P5 17,753 (rc 17,593), P0 12,650. Every change is a definition or a generalisation of a rule P4 already has. None adds a section or a recording list.

1. **Role strings: original language first, translation only in parentheses, everywhere (§6, and the language line in the intro).** Astra proposed this as point 2 and Claude as point 2. The rule now covers the body, the checklist's summary columns and legend, aggregates and check questions. "Narrowing" joins "merging" and "renaming" as forbidden. The intro's "모든 출력은 한국어로 작성한다" gets one exception sentence, which names role strings and change 2's uncertainty markers.
   - Target: defect 4. Change 3 of P4 did not move it (P0 4 marks, P4 5). Claude's round-4 comparative traced it to the Korean-output instruction, and S07 turned a source role string into a different field.
   - **Orchestrator addition, declared:** the translation of a given string is attached only at its first occurrence in the note. A parenthetical on every occurrence would add length to the checklist, which the cut order forbids shortening. Neither comparative asked for this.
   - Not taken: Claude's "if you merge or narrow, say so in place". P4 already forbids merging, and the stricter wording is kept.
2. **A source's own uncertainty marker stays next to the claim (§5, and a guard in §10's cut order).** Astra proposed this in points 3 and 5. Claude's comparative saw the same dropped qualifier (its §1, D5) but proposed no rule, so `../round4/RESULTS.md`'s "Claude 4" attribution for this point is corrected here. The change is taken on the orchestrator-confirmed D5 FAIL, not on reviewer overlap. That is the only exception to the one-reviewer exclusion below. Markers such as "tentative", "ambiguous", "reportedly" and "~로 알려진" stay beside the claim in the original wording. That includes cases where the claim is written together with other evidence or used to cross-check something. When two statements about the same object, role, scope and time disagree and the cause has not been checked, the note does not pick one: it marks them `[상충]`. A scope difference is still explained under the existing `상충` definition, so this adds no new conflict route.
   - In the cut order, "출처의 불확실성 표지" is added to what may never be deleted, so a marker cannot be cut as "②의 중복 한계 서술".
   - Target: the round-4 confirmed D5 FAIL (P4 r3, C6).
3. **Exclusive and negative statements are checked against material already received before they are written (§5).** Claude proposed this as point 4 and Astra in point 3. P4's line "‘유일하다’, ‘없다’, ‘상충 없음’도 같다 …" is generalised. The list becomes ‘유일하다’, ‘~만’, ‘전부’, ‘없다’, ‘언급하지 않는다’, ‘~로만 적혀 있다’, ‘상충 없음’. Before writing such a statement, the producer compares it with what it has already received: the input block, opened pages and search results. The statement is written only within that range, and the range is named in the sentence, briefly, by source ID. Claims about sources, credits and research paths are all covered.
   - Claude's version asked the producer to "적는다 what was compared" as a separate record. P5 asks only for the range inside the sentence, so no recording duty is added.
   - Target: the r1 ④-1 sentence ("연주자로만 적혀 있다") and defect 5 (unchecked exclusives).

Considered and not taken:
- Points from one reviewer only: Claude's alias rule (3), derivability rule (5), and its audit-side D6 wording (5, a reviewer-packet change that would move the measurement mid-series); Astra's aggregate rule (4).
- The access-label redefinition (both reviewers' point 1). It is already P3 edit 1, kept in P4. Label promotion is gone from P4's D5 marks.

**Length.** The three changes add 1,309 bytes of prompt (after the fidelity edit) and ask for slightly more text in the note: parenthetical translations, a range phrase, a kept marker. The 6,000-character cap and the cut order are unchanged. Round-4 P4 runs were 6,074 / 7,342 / 6,988 against a bar of 7,647 (1.10 × 6,952). That leaves about 9 % headroom at the median, so (e) is the condition most at risk. It is judged in the same pass as everything else.

**Pre-freeze fidelity check** (as rounds 1–4): one fresh-context dispatch each, to `gpt-6-astra` (no web) and to `claude-opus-5-5` (safe mode). Each reads:
- the two round-4 comparatives' proposal sections,
- `../round4/RESULTS.md` §"Proposed direction for a round 5",
- this change list,
- `prompts/P4-to-P5.diff`.

Records go in `freeze-check/`. Each reviewer answers per change: applied faithfully / material distortion / missing; scope creep; new defect. Each then returns FREEZE or MATERIAL OBJECTION. A material objection is applied once, toward the stricter wording, without a second check. The frozen hash replaces the placeholder above, and the edit is kept as `freeze-check/rc-to-frozen.diff`.

**Result (2026-10-20).** Astra (no web, 0 tool calls) answered CONFIRM FREEZE, with all three changes and the declared addition applied faithfully, no scope creep and no new defect. Claude (safe mode, 0 web requests, 0 hook events) answered MATERIAL OBJECTION on three points. Each was applied once, toward the stricter wording, without a second check:
- **Renaming.** P5 rc forbade only translation-renaming, which reopened P4's ban on *any* renaming ("Composer"-style English normalisation is part of defect 4). It now reads "다른 이름(번역어 포함)으로 바꾸지 않는다". The example's gloss is no longer narrowed: "믹싱" became "믹싱 엔지니어".
- **Conflict test.** "어긋나는" was weaker than the unchanged `상충` definition. It now reads "함께 참일 수 없는데".
- **Range phrase.** Range phrases in every checklist cell would be ritual repetition on an uncuttable table. The range is now named once, in the column head or legend.

Records: `freeze-check/` (`runs/astra-p5-fidelity`, `runs/claude-p5-fidelity`). The combined-prompt hash for P0 (`9d2202d3…`) equals round 4's, so the inputs and assembly are unchanged. P5's combined hash is `d09db36d…`. Both are pinned in `manifests/`.

The frozen scope (this file and `prompts/P5.md`) is committed and pushed before the first generation. The commit sha, and any rebase that rewrites it, is recorded in RESULTS.md.

## 2. Producer

| Environment | Model | Effort | Tools | CLI |
|---|---|---|---|---|
| Claude CLI | `claude-opus-5-5` | medium | WebSearch + WebFetch | 2.1.303 (as round 4, checked 2026-10-20; re-checked at dispatch), `--safe-mode` |

- Round 5 is compared with round-5 P0 only, never pooled with earlier rounds.
- A Claude trace is a harness failure, eligible for its one `-rerun` (§4), if it is not instruction-clean: it has a hook event or `memory_paths`, or its tool set is not exactly WebSearch + WebFetch.
- Astra review lane: the ChatGPT.app bundled `codex-cli` (0.163.0-alpha.10.2 on 2026-10-20). The bundle auto-updates, so the version is re-checked just before the first review dispatch and any change is recorded in RESULTS.md.

## 3. Album and inputs

`gemini-rights` — Gemini Rights, Steve Lacy, 2022-07-15, 10 tracks.
- The round-1–4 dispatched bytes are reused unchanged, copied from `~/.local/share/myblog-research/stage-b-round4-inputs/` to `stage-b-round5-inputs/`, with sha256 checked against round 4 (`gemini-rights.txt` `fcdea93c…`, `run-block.txt` `259ecbdf…`; both match).
- No annotation block, and no prod re-render.

All P5 changes were derived from this album's outputs. A pass is therefore a development result on training material, and advancement stays conditional on Stage C's held-out panel.

## 4. Runs and limits

- 2 arms × 1 environment × 1 album × 3 runs = **6 generations**. IDs are `cl-<P>-gemini-rights-r<n>`, P ∈ {P0, P5}.
- Order (counterbalanced, as round 4): r1 P5, r1 P0, r2 P0, r2 P5, r3 P0, r3 P5. Serial.
- Limits, rerun and preservation rules are as in round 4 §4: a 1,500 s ceiling, no automatic retry, one `-rerun` per harness failure, Bash `run_in_background`, and no redispatch of a claimed ID.

## 5. Review

As round 4 §5.
- Labels come from one `secrets.SystemRandom` draw, made after all 6 outputs have an outcome. Packets and the defect list are unchanged.
- **Claude** (`claude-opus-5-5`, safe mode, web tools) audits all 6 outputs and the sentinel, then writes one comparative over its 7 reports.
- **Astra** (`gpt-6-astra`, no web) does the same. Its D6 is reported descriptively and enters no count.
- **Sentinel.** The same round-1 S03, relabelled into the pool. The control for both reviewers is a D6 FAIL.
  - Both missed it in round 4. Claude has missed it in rounds 2, 3 and 4, with no FAIL on any sentinel dimension.
  - Each reviewer's sentinel levels are reported **next to the verdict**. So is the descriptive count of P5 and P0 outputs whose Claude D6 is at least as severe as Claude's sentinel D6.
- **Known limitation, with its number.** Claude has given 0 D6 FAILs in 37 per-output audits (rounds 2–4). Unless that changes, the D6 clauses of (a) and (c) cannot fire. Change 1 targets defect 4, which is a D6-type defect. So whether it worked is read from the defect table in (d) and from Astra's descriptive D6, not from a gate. This is recorded as a consequence, not as a reason to change the owner's decision.
- **Orchestrator source check.** Every single-reviewer D1–D5 FAIL on a P5 output is checked against that output's producer trace and the frozen anchors, and the checks are recorded in a table, as in round 4.
- The comparative brief names only the reader's own report count.
- Known leakage: role strings written original-first with a parenthetical can reveal P5, as can the ① tool-output line inherited from P4.
- Budget: 2 fidelity dispatches + 16 review dispatches (Claude 7 + 1, Astra 7 + 1). Per account: Claude 1 + 6 + 7 + 1 = 15; Astra 1 + 7 + 1 = 9.

## 6. Decision rule (predeclared, unchanged from round 4 apart from the candidate and the (d) extra row)

P5 advances only if all of these hold:
- (a) After comparative calibration, no P5 output (3 runs) has an **agreed** FAIL.
  - For D1–D5, agreed means both reviewers FAIL the same dimension, or one does and the orchestrator confirms it against sources, with the check recorded.
  - For D6, a Claude FAIL counts on its own.
- (b) No gate allegation on a P5 output remains unresolved. The owner adjudicates any that remain.
- (c) After calibration, P5's FAIL marks summed over its 3 runs are no more than P0's.
  - A mark is one (run, reviewer, dimension) FAIL.
  - D1–D5 marks come from either reviewer; D6 marks from Claude only.
- (d) The recurrence of each pilot defect is listed per P5 output and compared against round-5 P0, with these targets:

  | Defect | Targeted by |
  |---|---|
  | 4 | change 1 |
  | 5 | change 3, with P3 edit 2 kept |
  | 2, 6, 8 | P4's changes, carried; they must not come back |

  A separate row counts **dropped source uncertainty markers** (change 2). It is not one of the eight pilot defects. The unit is one (output, claim): a document in the producer trace attaches a hedging qualifier to a claim, and the note states that claim without it or at a higher status. The orchestrator counts it for every P5 and P0 output, from both reviewers' D5 prose and its own source check, and records the trace location for each count. Reviewer packets are unchanged, so the row has no reviewer-side key.
- (e) The median `output.md` length of P5's 3 runs (Python `len`, characters) is no more than 1.10 × the median of P0's 3 runs.

With fewer than 3 usable outputs in either arm, the round gives no verdict and is reported as incomplete. A run lost to a harness failure first gets its one `-rerun`.

Every arm comparison reports all 3 runs' values, not a median alone. Round-4 P4's values sit beside them, descriptively only. A side table shows the counts with Astra's D6 included.

## 7. Owner time

- Confirmation of this scope before any producer output.
- Adjudication of any surviving gate allegation (0–1 h).

Nothing is drawn from the confirmation budget.

## 8. Publication

As round 4 §8:
- Every record embedding the Gemini Rights catalog block has its owner-collection line redacted before push. `PUBLICATION-REDACTIONS.json` records the dispatched-byte hashes.
- A token scan must then find 0 hits.
- Originals stay outside the repository.
