# Stage B round 2 — predeclared scope (frozen before dispatch)

- Parent: `docs/rfcs/CHORE-research-model-evaluation.md` §B. Contract: `criteria/acceptance-v1.md` (v1). Anchors: `criteria/a2-anchors/anchors-v1-rc.md` (anchors-v1).
- Predecessor: `../round1/` (P1 did not advance; `../round1/RESULTS.md`).
- Date: 2026-10-16. Prepared by the orchestrating session (`claude-opus-5-5`) and reviewed read-only by a Fable subagent before it went to the owner; its findings were checked against the code and traces and applied, except one (failing runs on a non-empty `skills`/`plugins` list), which would fail every safe-mode run (§2). The owner confirmed this scope in chat on 2026-10-16, including the change to §7 (a), before any round-2 producer output existed.
- This is a **development round**. Its verdict is a model-proxy development judgement, not an acceptance-v1 pass. Nothing here touches the confirmation or calibration albums, the owner's 30–60 h budget, or production.

## 0. Changes from round 1

| Item | Round 1 | Round 2 | Why |
|---|---|---|---|
| Candidate | P1 = P0 + 7 pilot amendments | **P2 = P0 + 4 definition/deletion edits** | P1 lengthened every note (+27–79 %) and added failures; the edits are the four points on which both round-1 calibrations overlap (`../round1/RESULTS.md` §"Proposed direction") |
| Claude CLI lane | loaded user hooks, global `CLAUDE.md`, auto-memory | **`--safe-mode`**; a run whose trace shows a hook event, `memory_paths`, or a tool set other than WebSearch + WebFetch is a failed run | harness finding of round 1 |
| Runs per cell | 1 | **2** | round 1 could not separate prompt effect from run-to-run variance |
| D7 | scored, then moved to not-assessable by both reviewers | **not assessed** (no frozen top-3 map in a development round) | M4; both calibrations |
| Reviewer control | none | **one blind sentinel per reviewer** (a round-1 output with a FAIL both reviewers agreed on) | round 1 could not tell a strict reviewer from a broken one |
| Decision rule | §7 (a)–(d) | (a) counts **agreed or source-confirmed** FAILs; single-reviewer FAILs go into (c); (c) summed over both runs; **(e) pooled length** added | see §7 |

## 1. Prompts

| Role | File | sha256 |
|---|---|---|
| Control P0 | `prompts/P0.md` (byte copy of round-1 P0) | `f6c3a6277f4d6e4a5b7a1a978820e5c592e2a24151bc022c87d2f9cb290a8d2f` |
| Candidate P2 | `prompts/P2.md` | `2ba674bec6f10e41a8d9bc9433521cd70ad54792413be5201c51ce0e18e62724` |

P2 = P0 plus six inserted lines and nothing else (`prompts/P0-to-P2.diff`, +1,469 bytes, +11.6 %):

1. **Access label (definition, §5).** `원문 확인` means the sentence was read in page text the tool returned unprocessed. A tool-summarised fetch and a search snippet are `검색 결과 경유`. If processing is unknown, treat it as processed. No new label is introduced. The label *distribution* can still reveal the condition: a Claude-lane P2 note should carry almost no fetch-based `원문 확인` (see §6).
2. **Scope test (generalisation, §5).** The existing "not found ≠ does not exist" rule extends to "only", "none" and "no conflict", including claims about research paths. It is a check, not a duty to write the compared scope out.
3. **Credit-row transcription (definition, §6).** When a named row is copied into the checklist or appendix, it is copied completely for the target track, or declared a selective copy naming the omitted *kinds* of role (not each person). Selection is by whole role only: a role that is copied carries every person who holds it, jointly. Body mentions of a single credit are not affected.
4. **Gaps (definition, §8), and compression (deletion, §8–§9).** Before recording a gap, recheck received material. Only gaps raised to ④ (already capped at 3) carry what was checked and why it does not answer; a relayed lead is a lead, not a gap. A checklist column identical for every track becomes a one-line legend. A gap or access limit is written once and referenced elsewhere.

Not included: Astra's N/A-grading item and Claude's D2/D4/D6 manual items (scoring-manual matters, acceptance-v1 §6.1, not producer prompt), Claude's location-format item (proposed by one reviewer only).

**Pre-freeze fidelity check** (`freeze-check/`, as round 1): one fresh-context dispatch each to `gpt-6-astra` (29 s) and `claude-opus-5-5` (safe mode, 56 s, 0 hook events) over the round-1 findings, both calibration proposals and the rc1 diff. Both answered MATERIAL OBJECTION on the same line, credit transcription: declaring only the omitted role kinds lets a producer drop one co-holder of a role it keeps. Astra proposed listing omitted people and roles; Claude proposed restricting selection to whole roles and fixing an ambiguous scope phrase. Applied **once**, without a second check, merging toward the stricter wording: Claude's replacement, which closes the same gap without adding an enumeration duty. All other points were rated faithful by both. rc1 is `freeze-check/P2-rc1.md`; the change is `freeze-check/rc1-to-frozen.diff`. One paragraph of the round-1 Claude calibration that came from the contaminated harness (a recommendation drawn from the operator's global rules) was removed from the packet (`doc2.txt`).

## 2. Producers (round manifest v1 §4, unchanged except the Claude flag)

| Environment | Model | Effort | Tools | CLI |
|---|---|---|---|---|
| Claude CLI | `claude-opus-5-5` | medium | WebSearch + WebFetch | 2.1.301, `--safe-mode` |
| Codex | `gpt-6-astra` | medium | `--search` | ChatGPT.app bundled 0.162.0-alpha.17.2 |

`--safe-mode` was verified on 2026-10-16 against a control in the same pass (`scripts/research_model_benchmark.py` change in this PR): without it, 5 hook events, `memory_paths` present, 6,633 cache-creation input tokens; with it, 0 hook events, no `memory_paths`, 2,599 tokens (the ~4k difference matches the global `CLAUDE.md` plus memory index), and WebSearch + WebFetch both execute. Safe mode still *lists* 9 plugins and 17 skills in the `init` event; they are unreachable because the tool set is exactly WebSearch + WebFetch (no Skill or Agent tool), which the runner now enforces per run and records in `metadata.json` (`cli_init`). `--bare` is not usable because it refuses subscription (OAuth) auth. The Claude lane's WebFetch still returns model-processed text; that is a property of the environment, not removed here, and edit 1 tells the producer how to label it.

## 3. Albums (development material, same as round 1)

| Slug | Album | Release | Tracks | `albums.id` |
|---|---|---|---:|---|
| `gemini-rights` | Gemini Rights — Steve Lacy | 2022-07-15 | 10 | `79bf97d9-0069-49e3-9f5f-27206ecb9bc2` |
| `2000-tape` | 2000 TAPE — 김하온, JMIN, KC, NOWIMYOUNG | 2026-07-20 | 20 | `9b9071dd-5bab-47c6-a871-dc1c5cfa4492` |

Kept so that the round-2 contrast stays comparable in kind with round 1 and the harness change is the only environment change. The cost: all four edits were derived from these two albums' round-1 failures, so a pass here is a development result on training material. **Advancement under §7 is therefore conditional on Stage C's held-out panel**; it is never evidence of generalisation on its own. Neither album enters confirmation, calibration or spare sets.

## 4. Shared inputs

The same bytes as round 1 are dispatched; no prod re-render.

| Input | Dispatched sha256 |
|---|---|
| `inputs/gemini-rights.txt` | `fcdea93c639aced81c157d9e071c3ec3ccb415cb37704957a817262718b3f94b` (unredacted original; the published copy is redacted, see §9) |
| `inputs/2000-tape.txt` | `bc02329687302454f937734c2814ffce8d37d7129814ae0f28832cba91c594fa` |
| `inputs/run-block.txt` | `259ecbdfc0bd6e9cb6b6e45e6b8b34fa204cbe2532a21a525f5ed13e0887ebd8` |

Round-2 P0 outputs are compared with round-2 P2 outputs only. Round-1 outputs are not pooled with round-2 outputs, because the Claude-lane harness differs.

## 5. Runs and limits

- 2 prompts × 2 environments × 2 albums × **2 runs** = **16 generations**. Run IDs: `cl-<P>-<slug>-r<n>` and `gx-<P>-<slug>-r<n>`.
- Each provider lane runs serially in this order, counterbalanced so that neither prompt always goes first: r1 Gemini P2, r1 Gemini P0, r1 2000 TAPE P2, r1 2000 TAPE P0, then r2 Gemini P0, r2 Gemini P2, r2 2000 TAPE P0, r2 2000 TAPE P2. The two lanes may run concurrently.
- 1,500 s wall ceiling per run, no automatic retry. A harness failure (no inference, tool unavailable, or a Claude trace that is not instruction-clean) may be rerun **once** under a new ID ending `-rerun`, with both records kept. A second failure is a failed run.
- A Claude throttle (429 or guard cooldown) halts the Claude lane; its remaining entries are `not_run`, the round is reported incomplete and is not resumed under these IDs.
- Lanes run with Bash `run_in_background` (not a session monitor) and never redispatch a claimed ID.
- Preservation per run as round 1: `input.txt`, `stdout.jsonl`, `stderr.txt`, `metadata.json`, `output.md`.

## 6. Review

- Each usable output gets independent blind audits from `gpt-6-astra` (Codex) and `claude-opus-5-5` (Claude CLI, safe mode), fresh contexts, anonymous labels, key outside every packet. Labels are shuffled across all 16 outputs, so runs of the same cell are not adjacent.
- Packets as round 1: acceptance-v1 §2–§4, anchors-v1, the shared input, the output, the anonymised trace. Each reviewer gives PASS / BORDERLINE / FAIL for **D1–D6**, records D7 as not assessed, notes D8–D11, lists every alleged gate failure with evidence location, and the recurrence of each of the eight pilot recurring defects.
- **Reviewer control.** Round-1 S03 (Claude CLI · Gemini · P1), whose D6 FAIL both reviewers agreed on, is relabelled and shuffled into the pool as a 17th packet for each reviewer. A reviewer that does not give it a D6 FAIL or BORDERLINE is reported as such, and its round-2 FAILs are read with that caveat. The sentinel is excluded from every §7 tally.
- One comparative calibration per reviewer over its own 17 reports.
- Known leakage: producer family is visible in trace structure (as round 1), and the `원문 확인` distribution in Claude-lane notes can reveal P2 (§1). Each reviewer also audits its own family's outputs.
- Budget: 17 × 2 + 2 = **36 review dispatches**, same no-retry rule. Claude-lane total including generation and fidelity check: 8 + 17 + 1 + 1 = 27 dispatches.

## 7. Decision rule (predeclared)

P2 **advances** to calibration/confirmation as the Stage B candidate only if all hold:
- (a) no P2 output (2 albums × 2 environments × 2 runs) has an **agreed** D1–D6 FAIL after calibration: both reviewers FAIL the same dimension, or one does and the orchestrator confirms it against sources with the check recorded. Single-reviewer FAILs that are not source-confirmed are listed and counted in (c);
- (b) no gate allegation on a P2 output remains unresolved; the owner adjudicates any that remain;
- (c) in each album × environment cell, P2's D1–D6 FAILs (all FAILs, either reviewer) summed over both runs are no more than P0's;
- (d) the recurrence of each pilot recurring defect is listed per P2 output;
- (e) pooled over all cells, the median `output.md` length of the 8 P2 outputs is no more than 1.10 × the median of the 8 P0 outputs. Per-cell values are reported, not judged.

**Why (a) differs from round 1.** Round 1 counted a FAIL from either reviewer. Under that rule the P0 control itself failed in 2 of 4 cells, and 12 of 14 FAILs came from one reviewer, so (a) measured reviewer strictness rather than the prompt. Applied to round 1, the new (a) would still have rejected P1 (S03 D6 agreed), so it does not retroactively change round 1's verdict.

If any fails, the round reports the unmet items and proposes a bounded round 3. It does not declare success. With 2 runs per cell, any statement that P2 differs from P0 is reported with both runs' values, not a mean alone.

## 8. Owner time

Confirmation of this scope, and adjudication of any gate allegation that survives (0–1 h). Nothing is drawn from the confirmation budget.

## 9. Publication

The workspace repository is public. Every record that embeds the Gemini Rights catalog block has the owner-collection (bucket names) line redacted before push, as in round 1 (`PUBLICATION-REDACTIONS.json` with the hashes of the dispatched bytes). Originals stay outside the repository, and the branch is squashed so they never reach remote history.

## 10. Interruption and resume (amendment, owner-approved 2026-10-16)

Recorded after dispatch began; nothing above was changed.

- **What happened.** The Codex lane hit the ChatGPT account usage limit on its fifth run (`gx-P0-gemini-rights-r2`, 67 s, 8 web searches, no note): "You've hit your usage limit … try again at Oct 22nd, 2026 8:08 PM." The lane halted per §5 and dispatched nothing further. Codex: 4/8 success (all r1). Claude CLI: 8/8 success, every run with 0 hook events, no `memory_paths`, and tool set exactly WebSearch + WebFetch.
- **Owner decision (chat, 2026-10-16).** Pause, and resume after the reset rather than closing the round incomplete. This overrides §5's "not resumed under these IDs" for the Codex lane only.
- **Resume rule.** After 2026-10-22 20:08 KST, the four missing Codex runs are dispatched under new IDs ending `-resume` (`manifests/resume/`, `run_lane_resume.sh`), in the §5 r2 order. `gx-P0-gemini-rights-r2` stays on record as `rate_limited` and is not reviewed. The same no-retry, one-harness-rerun and throttle-halt rules apply. If the limit recurs, the round closes as incomplete.
- **Inputs for the resume.** The dispatched bytes (including the unredacted Gemini Rights input, sha256 `fcdea93c…`) are kept outside the repository at `~/.local/share/myblog-research/stage-b-round2-inputs/`, and the subscription guard source at `~/.local/share/myblog-research/shared-db-guard/` (a detached shared_db worktree at origin/main as of 2026-10-16). `run_lane_resume.sh` takes the inputs directory as its argument; the runner refuses on any byte change.
- **Review waits.** The blind label draw (`build_review_inputs.py`) happens only after all 16 cells have an outcome, so every output enters one draw. No review dispatch has happened. Review packets and every review run's `input.txt` embed the dispatched (unredacted) Gemini Rights input: before any push they are redacted per §9, added to `PUBLICATION-REDACTIONS.json`, and the diff is scanned for the bucket-name tokens (0 hits required).
- **Confound recorded.** The Codex r2 runs execute about six days after r1 and after the Claude runs. Web content and model serving can drift in that gap; per-cell comparisons report r1 and r2 separately as well as pooled.
