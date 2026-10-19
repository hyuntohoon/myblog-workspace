# Stage B round 3 — predeclared scope (frozen before dispatch)

- Parent: `docs/rfcs/CHORE-research-model-evaluation.md` §B. Contract: `criteria/acceptance-v1.md` (v1). Anchors: `criteria/a2-anchors/anchors-v1-rc.md` (anchors-v1).
- Predecessor: `../round2/` (P2 did not advance; `../round2/RESULTS.md`).
- Date: 2026-10-19. Owner direction in chat: run the round-3 revision on **Gemini Rights only** and review it, and use the Genius annotations we hold. Prepared by the orchestrating session (`claude-opus-5-5`) and reviewed read-only by a Fable subagent. Its findings were checked against the files and code and applied (13 findings; the per-track checklist deletion was withdrawn as one-reviewer-only). **Owner decisions in chat, 2026-10-19, before any round-3 producer output:** §2 option A (per-environment verdict), §3b option B (third arm P3G), §7 defer.
- This is a **development round**. Its verdict is a model-proxy development judgement, not an acceptance-v1 pass. Nothing here touches the confirmation or calibration albums, the owner's 30–60 h budget, or production.

## 0. Changes from round 2

| Item | Round 2 | Round 3 | Why |
|---|---|---|---|
| Candidate | P2 = P0 + 4 edits | **P3 = P2 + 4 definition/deletion edits**, and **P3G = P3 + annotation rule, with a Genius annotation input block** | P3: the four points on which both round-2 comparatives overlap (`../round2/RESULTS.md` §"Proposed direction"); P3G: owner, §3b |
| Albums | Gemini Rights + 2000 TAPE | **Gemini Rights only** | owner direction 2026-10-19 |
| Verdict scope | (a) and (e) pooled over environments; (c) per cell | **per environment** (owner, §2) | round 2: Codex · P2 had 0 FAILs while every agreed FAIL came from the Claude CLI lane |
| Everything else | — | unchanged: 2 runs/cell, sentinel, agreed-FAIL rule, D7 not assessed, `--safe-mode` | |

## 1. Prompts

| Role | File | sha256 |
|---|---|---|
| Control P0 | `prompts/P0.md` (byte copy of round-1/2 P0) | `f6c3a6277f4d6e4a5b7a1a978820e5c592e2a24151bc022c87d2f9cb290a8d2f` |
| Candidate P3 | `prompts/P3.md` (frozen; rc0 unchanged by the fidelity check) | `225ec41c57e20bd8fbf9a8675c8133ca4d869e2a8e5e98f5d82a5d34d6cf77b5` |
| Candidate P3G | `prompts/P3G.md` (frozen) = P3 + one line (`prompts/P3-to-P3G.diff`) | `31b75db9829342970f0794cb906ba2a75fe453dee37e8aabae4da93bed185a2f` |

P3 = P2 with these edits (`prompts/P2-to-P3.diff`; P2 14,119 → P3 14,710 bytes, P0 12,650):

1. **Access label, tightened (definition, §5).** `원문 확인` only for unprocessed page text received *in this run*. Summarised fetches and snippets stay `검색 결과 경유` (no new label; Claude's comparative called it "중계"). New: ① states once which kinds of tool output the run received (unprocessed text / tool summary / snippet); the §10 ① line names it too.
2. **Conflict definition (definition, §5).** `상충` only when statements about the same subject's same role field, scope (track / album / edition) and time cannot both be true. Otherwise "범위 차이" in prose, stated in P3 as not a new status label; each statement keeps its own status. Absence from a truncated or filtered source is `미확인`, never conflict or absence.
3. **Numerators from the table (definition, §6).** Every aggregate and coverage numerator is counted from the ③ checklist; summary and body figures must match it (Astra 3 "집계는 표의 동일한 포함 기준으로 재계산"; Claude 4's numerator half).
4. **Compression by deletion (§8, §10, header).**
   - The "write once, reference elsewhere" rule extends from gaps/access limits to detailed evidence and open status (Astra 5, Claude 4).
   - The run-metadata duty (prompt revision ID, hash, runner commit, collection time) is deleted (Astra 5 "근거 없는 … 실행 이력은 삭제", Claude 4).
   - The header line `제안일: 2026-10-15` is deleted. Orchestrator-derived, not a reviewer proposal: Astra flagged an unsupported "proposal date" in S03/S06, and those notes cite the prompt header (`../round2/runs/gx-P0-gemini-rights-r2-resume/output.md:76`, `gx-P0-2000-tape-r2-resume/output.md:73`). Both are P0 outputs, so P0 still carries the line and (d) will show the contrast.
   - **The per-track checklist stays** (P2's one-line-legend rule unchanged). Deleting it was Claude 4 only; Astra 3 presupposes the table, and reviewers use it for D6 row linkage. Under this round's own overlap rule it is excluded.

Not included (one reviewer only): Astra's quotation-trace rule; Claude's role-string-in-headings rule, quotation-context rule and checklist deletion.

**Pre-freeze fidelity check** (as rounds 1–2): one fresh-context dispatch each to `gpt-6-astra` and `claude-opus-5-5` (safe mode) over the round-2 comparatives, the P2→P3 and P3→P3G diffs and the head of the annotation block (`freeze-check/`). A material objection is applied once, toward the stricter wording, without a second check.

**Result (2026-10-19).** Both reviewers rated all four P3 points *applied faithfully*, with no scope creep and no new P3 defect. Both answered MATERIAL OBJECTION on the same P3G line, for two reasons:
- "곡별 공백을 메울 후보" invites unverified community text into ③'s substantive-evidence column, which edit 3 then counts. Claude named this; Astra called it quota-filling.
- "원문을 찾기 전까지" can be met by another relay of the same quotation (Claude), or by locating rather than reading the passage (Astra).

Applied once, merged toward the stricter wording. A quotation becomes direct speech only when the passage is read in unprocessed original text in this run. Other relays of the same quotation are not originals. Annotations alone never fill ③'s substantive evidence. The optional per-track grouping is kept (owner's request) without repetition. rc0 is `freeze-check/P3G-rc0.md`; the change is `freeze-check/rc0-to-frozen.diff`.

## 2. Producers and verdict scope

| Environment | Model | Effort | Tools | CLI |
|---|---|---|---|---|
| Claude CLI | `claude-opus-5-5` | medium | WebSearch + WebFetch | 2.1.303, `--safe-mode` |
| Codex | `gpt-6-astra` | medium | `--search` | ChatGPT.app bundled 0.163.0-alpha.10.2 |

Versions differ from round 2 (2.1.301; 0.162/0.163). Round 3 is compared with round-3 P0 only, never pooled with round 2.

**Claude CLI WebFetch confound — owner chose A (2026-10-19).** The Claude lane's WebFetch returns model-processed text, so in that lane the round-2 defects 2 (summary promoted to `원문 확인`) and 3 (under-reading) cannot be attributed to the prompt alone. The lane matches **production in tool set**, and therefore in this confound. Production (`scripts/research_poller.py:93,577`; argv pinned by `myblog_shared_db/tests/test_llm_engine.py::test_golden_argv_research_poller`) runs `claude -p --allowed-tools WebSearch,WebFetch --model opus`, without `--safe-mode` or an effort flag, with a 900 s timeout. Options:
- **(A, recommended) Keep both lanes unchanged and judge each separately.** P3 advances *per environment*. Edit 1 is aimed at exactly this confound, so the Claude lane is where it gets tested. The 2026-10-16 decision (confirmation runs in both environments) stands.
- (B) Fix the Claude lane first by giving it a raw-text fetch tool. That changes the production-equivalent harness, needs its own P0 re-baseline, and is a separate decision about the production poller's tool set.
- (C) Codex lane only. Cheapest, but its result does not carry over to production without a separate decision to move the poller to Codex.

## 3. Album and inputs

`gemini-rights` — Gemini Rights, Steve Lacy, 2022-07-15, 10 tracks, `albums.id 79bf97d9-0069-49e3-9f5f-27206ecb9bc2`. The round-1/2 dispatched bytes are reused unchanged, copied to `~/.local/share/myblog-research/stage-b-round3-inputs/` (`gemini-rights.txt` sha256 `fcdea93c…`, `run-block.txt` `259ecbdf…`). No prod re-render. The same directory holds the P3G-only `gemini-annotations.txt` (sha256 `c0e757d2c1f475a4d9cdf0636adce0974418bf83005b70156f8e0f94aa4decb5`) and the read-only row export it was built from.

All four edits were derived from this album's outputs (among others), so a pass here is a development result on training material. Advancement stays conditional on Stage C's held-out panel. With one album, a round-3 pass is weaker evidence than round 2 would have been: no second album shows the edits are not Gemini-specific.

**Floor effect in the Codex lane.** Round-2 Codex · Gemini had P0 1 FAIL and P2 0 FAILs. There, (c) is close to a tie-at-zero test: a Codex advance means P3 did not regress, not that edits 1–4 improved anything. The Claude lane is where edits 1–2 are actually tested.

## 3b. Genius annotations as input (owner chose B, 2026-10-19)

Owner view: use the per-song Genius annotations we already hold, possibly in their own section of the note. Today's input carries Genius credits, matches and sample relations, but **no annotation text**. Prod DB, read-only, Gemini Rights (2026-10-19):
- 100 annotations on 8 of 10 tracks (Mercury 27, Helmet 18, Cody Freestyle 17; 2Gether and Sunshine 0); 95 have `body_ko`; 9 tracks have a song description.
- **0 verified** (`is_verified`): all are community-written. A quotation inside one is relayed by the community, never the artist's speech (G5 risk).
- 10 mention an interview or statement; 1 carries a URL. Source text 27,686 chars, about 3.7× the current 7,484-char input.

Options:
- **(A) Separate later round.** Round 3 stays prompt-only; an annotation input arm follows. Cleanest attribution, slowest.
- **(B, recommended) Third arm in this round: P3 + annotation block.** Cells become P0 / P3 / P3+G per environment. P3 vs P0 stays prompt-only, and P3+G vs P3 isolates the annotation effect. Cost: 12 generations, (12 + 1) × 2 + 2 = 28 review dispatches; a ChatGPT limit is more likely to cut the Codex lane short (then §4's halt rule applies).
- (C) Give the block to both P0 and P3. Rejected: it changes the control and mixes the input change into P3's edits.

**Block as built** (`build_annotation_block.py`, from a read-only export of 102 rows, 0 verified):
- Original-language `body_source`, not our machine translation, so translation errors cannot become evidence.
- Per track, in the input's track numbering: song description (≤ 280 chars), then every annotation that mentions a statement (≤ 600 chars, the lead is the point), then the rest by votes (≤ 280 chars), filled round-robin across tracks under an 8,000-char cap. Cut text is marked `…(잘림)`.
- Result: 7,943 chars, 14 annotations from 7 tracks, 8 of which mention a statement. Track 6 has no annotations and says so. Track 9 (Sunshine) is the input's ambiguous match: its Genius row points at a Spanish translation page, so nothing is carried from it.
- The header says the annotations are community-written, unverified, selected and truncated, that quotations inside them are relayed, and that what was left out is not evidence of absence.
- The dispatched block is `gemini-annotations.txt` in the round-3 inputs directory (sha256 in §3).

P3G adds one rule (§6): annotations are unverified `DB등재` records; a statement they quote is `재인용` until the original is found; they serve as leads and as candidates for per-track gaps, and may be gathered per track. No production renderer change.

## 4. Runs and limits

- 3 arms × 2 environments × 1 album × 2 runs = **12 generations**. IDs `cl-<P>-gemini-rights-r<n>`, `gx-<P>-gemini-rights-r<n>`, P ∈ {P0, P3, P3G}.
- Inputs: P0 and P3 get `gemini-rights.txt` + `run-block.txt` (round-2 bytes). P3G gets `gemini-rights.txt` + `gemini-annotations.txt` + `run-block.txt`.
- Order per lane (counterbalanced): r1 P3, r1 P3G, r1 P0, r2 P0, r2 P3G, r2 P3. Lanes may run concurrently.
- Limits, rerun, throttle and preservation rules as round 2 §5: 1,500 s ceiling, no automatic retry, one `-rerun` per harness failure, a Claude trace that is not instruction-clean is a failed run, Bash `run_in_background`, no redispatch of a claimed ID.
- A ChatGPT usage limit halts the Codex lane; the round then reports the Claude lane alone and says so. It does not pause and resume (round 2 §10 is not carried over).

## 5. Review

As round 2 §6. Both reviewers (`gpt-6-astra`, `claude-opus-5-5` safe mode) audit every usable output blind, fresh context, anonymous labels from one `secrets.SystemRandom` draw after all 12 outputs have an outcome. Reviewers give PASS / BORDERLINE / FAIL for D1–D6 and record D7 as not assessed. Each also lists gate allegations and the recurrence of the eight pilot defects, then writes one comparative calibration.

- **Sentinel.** The same round-1 S03 (Claude CLI · Gemini · P1; D6 FAIL agreed in round 1) is relabelled into the pool. All thirteen packets are now Gemini, so it blends better than in round 2. The control is met only by a **D6 FAIL** (tightened from FAIL-or-BORDERLINE): in round 2, Claude gave D6 BORDERLINE to 9 of 17 notes, so BORDERLINE could not tell a lenient reviewer from a working one.
- Known leakage: producer family is visible in traces; the `원문 확인` distribution and the new ① tool-output line can reveal P3; the annotation block in the packet's input reveals P3G. Reviewers get each output's own dispatched input, so P3G packets include the block.
- Budget: (12 + 1) × 2 + 2 = **28 review dispatches**. Per account, including generation and the fidelity check: 6 + 13 + 1 + 1 = **21** each.

## 6. Decision rule (predeclared)

Applied **separately per environment** (option A), to each candidate X ∈ {P3, P3G} against P0. X advances in an environment only if all hold:
- (a) no X output in that environment (2 runs) has an **agreed** D1–D6 FAIL after calibration: both reviewers FAIL the same dimension, or one does and the orchestrator confirms it against sources with the check recorded;
- (b) no gate allegation on an X output remains unresolved; the owner adjudicates any that remain;
- (c) X's D1–D6 FAILs (either reviewer) summed over both runs are no more than P0's in that environment;
- (d) the recurrence of each pilot defect is listed per X output, with defects 2, 5, 6 and 8 (the ones edits 1–4 target) compared against round-3 P0;
- (e) the median `output.md` length of that environment's two X outputs is no more than 1.10 × its two P0 outputs.

P3G vs P3 (the annotation effect) is **descriptive**, not a gate: per environment, both runs' FAILs per dimension, defect recurrence, length, the number of tracks with production or context evidence, and how annotation content was labelled (any annotation quotation presented as the artist's speech is listed). P3G's length is judged against P0 under (e) like P3's; the block's leads may justify a longer note, but the predeclared limit still applies.

An environment with fewer than 2 usable outputs for any arm gives that arm no verdict and is reported incomplete. Every statement that one arm differs from another reports both runs' values, not a mean alone. If P3 advances in only one environment, the result says so and does not generalise to the other.

## 7. Scoring-manual gaps (owner: defer, 2026-10-19)

Raised by Claude's round-2 comparative; they belong to acceptance-v1 §6.1 (scoring manual), not the prompt:
1. A reviewer whose own fetch is blocked vs an R5 "retrieval failure" by the producer.
2. The D5 level of an understatement with no downstream effect (round-2 S01, S08).
3. Whether Genius and Wikipedia rows count as an "authoritative row" for D6.

Left open in round 3. Reviewers keep using acceptance-v1 as written, so rounds stay comparable. Decide them when the §6 scoring manual is frozen before calibration, where acceptance-v1 already requires it.

## 8. Owner time

Confirmation of this scope and the three decisions (§2, §3b, §7; given 2026-10-19); adjudication of any surviving gate allegation (0–1 h). Nothing is drawn from the confirmation budget.

## 9. Publication

As round 2 §9: every record embedding the Gemini Rights catalog block has the owner-collection line redacted before push (`PUBLICATION-REDACTIONS.json` with dispatched-byte hashes), followed by a token scan with 0 hits required. Originals stay outside the repository.

The annotation block is third-party community text. It is **not published verbatim**: the repo keeps `build_annotation_block.py` and the block's sha256, and every published copy of a P3G input (run `input.txt`, review packets) has the block replaced by a placeholder line naming that hash, recorded in `PUBLICATION-REDACTIONS.json`. Short annotation quotations inside producer notes or reviews stay as written.

## 10. Codex producer lane discontinued (amendment, owner decision 2026-10-19)

Recorded after all six Codex generations had finished and before any review dispatch. Nothing above is changed for this round.

- **Observation.** Codex-lane generation costs 621,853–1,317,722 input tokens per note (83–90 % cached) and 4,415–6,662 output tokens (`runs/gx-*/stdout.jsonl`, `turn.completed`). The agent loop resends the growing context on every search.
- **Owner decision (chat).** Stop producing research notes in the Codex environment after this round. This replaces the 2026-10-16 decision to confirm in both environments; later rounds and confirmation runs use the Claude CLI lane only.
- **This round.** The six Codex outputs are still reviewed (owner's choice), by Claude only (below). The Codex verdict is recorded for comparison only and drives no later round.
- **Reviewer kept, lane reduced (second owner decision, same evening, before any review dispatch).** `gpt-6-astra` stays a reviewer, so the GPT + Claude design holds, but at lower cost. Round-2 records show an Astra per-output audit at 168k–284k input tokens with 2–3 searches, each search resending the whole packet.
  - **Astra audits only the six Claude-lane outputs plus the sentinel**, and writes one comparative over those seven. That is 8 dispatches instead of 14. Claude still audits all 13 and writes one comparative over them.
  - **Astra runs with no web tool.** Its packets (`review/inputs-astra/`) replace the one sentence allowing web tools with an instruction to judge from the shared input, the note and the anonymous trace. Uncheckable support is counted as unverifiable, never FAILed for that reason alone.
  - The runner's new `"web_search": false` passes `web_search="disabled"` after `exec`, disables the `apps` and `plugins` features, and turns off the operator's `chrome-devtools` and `node_repl` MCP servers. Probes on 2026-10-19 showed each of these was a working route to the web, or an attempted one, when left on. The final probe answered `NO_WEB_TOOL` with no tool call. No earlier Codex generation or Astra review contains an MCP tool call (all `stdout.jsonl` scanned).
- **Consequences for §6.** Claude lane: (a) still needs agreed FAILs, but Astra's are now no-web judgements; that changes the reviewer method from round 2 and is reported next to the verdict. Codex lane: one reviewer only, so (a) can only be met by orchestrator source confirmation, and the lane verdict is descriptive. Sentinel: Astra's control is the same D6 FAIL test, without web. Budget: 13 + 1 (Claude) + 7 + 1 (Astra) = **22 review dispatches**. Review-lane token use is reported in RESULTS.md.
