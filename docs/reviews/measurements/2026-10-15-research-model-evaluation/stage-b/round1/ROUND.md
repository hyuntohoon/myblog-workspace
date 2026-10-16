# Stage B round 1 — predeclared scope (frozen before dispatch)

- Parent: `docs/rfcs/CHORE-research-model-evaluation.md` §B. Contract: `criteria/acceptance-v1.md` (v1). Anchors: `criteria/a2-anchors/anchors-v1-rc.md` (anchors-v1).
- Date: 2026-10-16. Prepared by the orchestrating session (`claude-opus-5-5`). The owner confirmed this scope in chat on 2026-10-16 before any round-1 producer output existed, and chose the Korean development album.
- This is a **development round**. Its verdict is a model-proxy development judgement, not an acceptance-v1 pass. Nothing here touches the confirmation or calibration albums, the owner's 30–60 h budget, or production.

## 1. Prompts

| Role | File | sha256 |
|---|---|---|
| Control P0 | `prompts/P0.md` (byte copy of the pilot `prompt-revised-ko.md`) | `f6c3a6277f4d6e4a5b7a1a978820e5c592e2a24151bc022c87d2f9cb290a8d2f` |
| Candidate P1 | `prompts/P1.md` | `1b8fb9b60d61647b6f7bab5135cf7cedc64ee2881398fb66ea703869504bf3ce` |

- P1 = P0 plus the seven converged amendments of `pilot-final-results.md` §"Prompt amendments", nothing else. Diff: `prompts/P0-to-P1.diff`.
- Pre-freeze fidelity check (`freeze-check/`): one fresh-context dispatch each to `gpt-6-astra` and `claude-opus-5-5` over the amendment sources and the rc1 diff. Both answered MATERIAL OBJECTION with replacement text. Per the agreed scope, the objections were applied **once**, without a second check, merging overlapping replacements toward the stricter wording. rc1 is kept as `freeze-check/P1-rc1.md`; the applied change is `freeze-check/rc1-to-frozen.diff`.
- The control is P0, not production v2, so the contrast isolates the amendments. Production v2 remains the confirmation control (round manifest v1 §5).

## 2. Producers (round manifest v1 §4, unchanged)

| Environment | Model | Effort | Tools | CLI |
|---|---|---|---|---|
| Claude CLI | `claude-opus-5-5` | medium | WebSearch + WebFetch | 2.1.301 |
| Codex | `gpt-6-astra` | medium | `--search` | ChatGPT.app bundled 0.162.0-alpha.17.2 |

The model and tools are fixed across P0 and P1, so the round contains no model contrast.

## 3. Albums (development material)

| Slug | Album | Artist(s) in catalog | Release | Tracks | Spotify | `albums.id` |
|---|---|---|---|---:|---|---|
| `gemini-rights` | Gemini Rights | Steve Lacy | 2022-07-15 | 10 | `3Ks0eeH0GWpY4AU20D5HPD` | `79bf97d9-0069-49e3-9f5f-27206ecb9bc2` |
| `2000-tape` | 2000 TAPE (**owner**) | 김하온, JMIN, KC, NOWIMYOUNG | 2026-07-20 | 20 | `0HhoqCRYpuH5sc9mlgCgrF` | `9b9071dd-5bab-47c6-a871-dc1c5cfa4492` |

- Gemini Rights is the pilot album: English, source-rich, pre-cutoff. It serves as a regression check against the pilot defects. Its facts stay regression checks and never become prompt rules.
- 2000 TAPE is post-cutoff Korean hip-hop. Its rendered Genius block has 0/20 tracks matched, so the round includes a sparse-credit case. No `album_research` row exists for it.
- Both albums are excluded from the confirmation, calibration and spare sets in round manifest v1 §2. Both become development material.

## 4. Shared inputs

Per album, the same bytes go to P0 and P1:
- `inputs/<slug>.txt`: the production poller's `_album_block`, `_genius_block` and `_catalog_block`, rendered read-only from prod by `render_inputs.py` on 2026-10-16;
- `inputs/run-block.txt`: a common headless task block.

The combined prompt is `<prompt>\n\n<album input>\n\n<run block>`, as the runner joins it. The runner refuses to dispatch on any byte change.

| Input | sha256 |
|---|---|
| `inputs/gemini-rights.txt` | `fcdea93c639aced81c157d9e071c3ec3ccb415cb37704957a817262718b3f94b` |
| `inputs/2000-tape.txt` | `bc02329687302454f937734c2814ffce8d37d7129814ae0f28832cba91c594fa` |
| `inputs/run-block.txt` | `259ecbdfc0bd6e9cb6b6e45e6b8b34fa204cbe2532a21a525f5ed13e0887ebd8` |

Unlike the pilot, these inputs include Genius and catalog blocks. Round-1 P0 outputs are therefore compared with round-1 P1 outputs only, never with the pilot notes.

## 5. Runs and limits

- 2 prompts × 2 environments × 2 albums × 1 run = **8 generations**. Run IDs are `cl-<P>-<slug>` and `gx-<P>-<slug>` under `runs/`, and manifests are under `manifests/`.
- Each provider lane runs serially, in the order Gemini P1, Gemini P0, 2000 TAPE P1, 2000 TAPE P0. The two lanes may run concurrently.
- Each run has a 1,500 s wall ceiling and no automatic retry. A harness failure (no inference, or tool unavailable) may be rerun **once** under a new ID ending `-rerun`, with both records kept. A second failure is a failed run.
- A Claude throttle (429 or guard cooldown) halts the Claude lane, and its remaining entries are `not_run`. The round is then reported incomplete and is not resumed under these IDs.
- Preservation per run (runner): `input.txt`, `stdout.jsonl` (tool calls and tool outputs as received), `stderr.txt`, `metadata.json`, `output.md`. Claude WebFetch output is model-processed text and is recorded as such.

## 6. Review

- Each usable output gets independent blind audits from `gpt-6-astra` (Codex) and `claude-opus-5-5` (Claude CLI), in fresh contexts, under anonymous labels. The key stays out of every packet.
- Reviewers receive acceptance-v1 §2–§4, anchors-v1, the shared input, the output, and the anonymised trace of what the producer received. Each reviewer gives an anchors-v1 level (PASS / BORDERLINE / FAIL) for D1–D7, notes on D8–D11, every alleged gate failure with evidence location, and the recurrence of each of the eight pilot recurring defects.
- Then one comparative calibration per reviewer over its own reports.
- Budget: 8 outputs × 2 reviewers + 2 comparatives = 18 review dispatches. Same no-retry rule.

## 7. Decision rule (predeclared)

P1 **advances** to calibration/confirmation as the Stage B candidate only if all of the following hold:
- (a) no P1 output (2 albums × 2 environments) has a FAIL on D1–D7 from either reviewer;
- (b) no gate allegation remains unresolved; the owner adjudicates any allegation;
- (c) in each album × environment cell, P1 has no more D1–D7 FAILs than P0;
- (d) the recurrence of each pilot recurring defect is listed per P1 output.

If any of these fails, the round reports the unmet items and proposes a bounded round 2. It does not declare success. A reviewer disagreement on a FAIL counts as a FAIL for (a) unless resolved against sources.

## 8. Owner time

The owner is needed only to adjudicate gate allegations; the estimate is 0–1 h. This round draws nothing from the confirmation budget.
