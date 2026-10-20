# Stage B round 7 — predeclared scope (frozen before dispatch)

- Parent: `docs/rfcs/CHORE-research-model-evaluation.md` §B. Contract: `criteria/acceptance-v1.md` (v1). Anchors: `criteria/a2-anchors/anchors-v1-rc.md` (anchors-v1).
- Predecessor: `../round6/`. P6 did not advance, on one orchestrator-confirmed Claude D4 FAIL. P6 r2 quoted Lacy ("The drums were different, the chorus was different.") from a search result whose summary text names no source, and filed it under the result's first link, Wikipedia, which does not contain it (`../round6/RESULTS.md` §Verdict). Every other condition held: FAIL marks 2 vs 8, length 0.813×, no open allegation, and 0 contradicted absence values in P6 tables (P0 had 1).
- Date: 2026-10-20. Prepared by the orchestrating session (`claude-opus-5-5`). Reviewed read-only by a Fable subagent before the owner saw it: 9 findings, no blocker, each checked against the files and all applied (the prompt wording of change 1 (a), the P7 manifest hash step, the (d) row's unit and limits, the prevalence wording, the fetch-summary confirmation rule, the confirmation rule's dependence stated in §6 (a), the base-choice wording, two stale tool comments). 
- **Owner confirmed this scope in chat on 2026-10-20, with P6 as the base ("P6 기준으로 확정"), before any round-7 dispatch.** The question stated the single change in two places, the base choice, 3 runs per cell, the new (d) row and its blind count, the thin target (4 of 18 candidate units), the verdict's dependence on reading a summary-cited quote as recoverable, and the budget.
- This is a **development round**. Its verdict is a model-proxy development judgement, not an acceptance-v1 pass. Nothing here touches the confirmation or calibration albums, the owner's 30–60 h budget, or production.

Carried over unchanged from the owner's earlier decisions:
- The Codex producer lane stays discontinued (2026-10-19). Generation runs in the Claude CLI lane only.
- Astra reviews Claude-lane outputs and the sentinel, with no web tool.
- No annotation arm (2026-10-20). No Genius footnote clause (2026-10-20).
- D6 is judged by the Claude reviewer alone (2026-10-20). Astra's D6 enters no count.
- R-a to R-c are the development-round D6 rules (2026-10-20). D6 does not bind the round rule (2026-10-20, owner chose (a)). It is scored and reported descriptively.
- The scoring-manual gaps stay deferred (blank 3 filled by R-a–R-c for development rounds only). §6 is not frozen and the §7 floors stay deferred (2026-10-19).

## 0. Changes from round 6

| Item | Round 6 | Round 7 | Why |
|---|---|---|---|
| Candidate | P6 | **P7 = P6 + change 1 (search-summary attribution)** | `../round6/RESULTS.md` §"What the round shows" 3, and the first option under "Open for the owner" |
| Base | P5 | **P6** (owner decision, §1) | P6's only failed condition is the one change 1 targets |
| Arms | P0 / P6 | **P0 / P7** | P6 is not re-run. Its round-6 values appear descriptively only and are never pooled. |
| (d) extra rows | contradicted absence; dropped marker | **+ search-summary quote filed under a link** (change 1); the other two kept | §6 |
| Everything else | — | unchanged: Gemini Rights only, same dispatched input bytes, Claude CLI only, 3 runs per cell, sentinel, `--safe-mode`, D7 not assessed, no-web Astra, R-a–R-c and the re-checked Qobuz row in every packet and comparative | |

## 1. Prompts

| Role | File | sha256 |
|---|---|---|
| Control P0 | `prompts/P0.md` (byte copy of rounds 1–6 P0) | `f6c3a6277f4d6e4a5b7a1a978820e5c592e2a24151bc022c87d2f9cb290a8d2f` |
| Base P6 | `prompts/P6.md` (byte copy of round-6 P6) | `ac7c63023f66ffcd2dbadda6fe4509f9651037e4aea8a084cb7630f40f26af74` |
| Candidate P7 | `prompts/P7.md` (frozen after the fidelity check; the rc is `prompts/P7-rc.md`, `b7c2aec3…`) | `b7c2aec3eb4d41e22fd3716bc352c105aae053cfc8494e1f9d3ec6103620368a` |

**Base: P6, not P5 (owner decision, 2026-10-20).** Round 6's rule left P5 as the development base, so this was a real choice.
- For P6: every condition except (a) held, and (a) failed on the slip change 1 targets. P6's own change (the absence check at ③ and ⑤) met its target row. If P7 advances, it carries that change under the same rule, scored in the same round with the round-6 absence row kept in (d).
- For P5: the comparison isolates change 1 alone. It drops P6's change, whose round-6 result is "consistent with change 1 working, not proof of it" (`../round6/RESULTS.md`), and that change would need its own round later.
- The orchestrator recommends P6. If the owner picks P5, P7 = P5 + change 1, the absence row stays in (d) as a watch row, and the diff and hashes below are rebuilt before the fidelity check.

P7 is P6 with one change, in two places. The diff is `prompts/P6-to-P7-rc.diff`. Sizes: P6 18,544 bytes, P7 rc 19,149 (+605). After freeze, `prompts/P0-to-P7.diff` gives the full contrast with P0. It adds no section and no recording list.

**Change 1 — content received only in a search tool's summary is attributed to that summary, not to one of its links.**
- **The harness fact.** A Claude CLI WebSearch result is a list of links followed by one summary text. The summary does not say which link each sentence came from, and there are no per-link snippets (`../round6/runs/cl-P6-gemini-rights-r2/stdout.jsonl`, the seq-12 result: 9 links, then the summary holding the quote).
- **(a) §4 B, after the per-claim attribution rule.** Content received only in that summary is cited to the search summary, not assigned to any listed link. A link is cited only when the producer opened it and received the same content. A passage the summary prints in quote marks may keep its quote marks only after it is received that way from a link. If it is not, it is written without quote marks, as what the summary relays.
- **(b) §10 ⑤, one clause in the source-list line.** A search summary gets its own line: ID, "검색 요약", the query, access date. Without this, (a) leaves the producer no way to list the source in ⑤'s required one-line format (ID, hyperlink, author/outlet, date), and the cheapest repair is to put a link's URL back on it.
- **Why this shape.** P4's rule ("받은 문서가 다른 매체를 지목하면 … 받은 문서를 출처로 적고") covers a document that names an outlet. It does not cover a summary that names nothing. The new sentence says what the received document is in that case, and ties quote marks to receipt from a link. It does not ask for any recording beyond the citation.
- **Reviewer support.** Astra's round-6 comparative point 5: "통합 요약을 개별 매체에 임의 배정하지 않고". Claude's point 1: "따옴표 안에는 원문 문구만 넣고, 요약만 받았다면 따옴표 없이 의역으로 표시합니다." Change 1 takes the overlap of the two: attribution of summary content (Astra 5) and quote marks on summary content (Claude 1, narrowed to search summaries).
- **Orchestrator extension, declared:** part (b), and the narrowing of Claude's point 1 to search summaries. Claude's point covers WebFetch summaries too. That half concerns the `[원문 확인]` label (Claude's defect B), which is P4's access-label rule and a different failure from the one that stopped round 6.
- **Prevalence, measured before freeze.** `summary_quote_scan.py` (sha256 `a2e768fc…`) over rounds 4–6 found candidate units (a quoted passage present in a search summary and in no fetch result) in 4 of 18 Claude-lane outputs. Their citing lines were not re-read against the §6 (d) unit definition: round-4 P4 r3, round-5 P0 r2 and P5 r2, round-6 P6 r2. One more hit (round-6 P0 r1) is a page title, not a quote. The scan reproduces the round-6 hit from the blind packets (S07) as well as from the run traces. So the target is an event of about one output in five. A clean P7 arm will show that change 1 does no harm more than that it works, and RESULTS will say so.
- **Known risks.**
  - Extra fetches to recover a quote raise tokens and time, and could lengthen ⑤. (e) is unchanged and watched.
  - The untaken WebFetch half of Claude's point 1 leaves round 6's K7 shape reachable in P7: quote marks on text received only in a fetch summary (r2, D4 BORDERLINE there).
- §4 A still asks for a direct URL per source and sends sources that could not be opened to ①. A producer may list every search summary as an access limit there. Watched, not edited.
- A quote written without quote marks loses verbatim fidelity. That is the intended trade (Claude 1), and D4's BORDERLINE "fidelity imperfect but meaning kept" is the level it should land at, not FAIL.
  - "Cited to the search summary" may still read as non-recoverable to a reviewer, since a reader cannot replay the search exactly. The ⑤ line keeps the query, so recovery takes one search.

Considered and not taken:
- **R-a–R-c as a producer rule** (Astra 2, Claude 3). It is aimed at D6, which binds nothing, and would confound change 1. It is the second option in round 6's "Open for the owner", left for its own round.
- **Access-route definitions** (Astra 1, Claude 1's WebFetch half): P4's `[원문 확인]` rule already defines it. Defect B sits mostly on P0 and the sentinel.
- **Conflict rule** keeping "observed difference" and "cause unknown" apart (Astra 3, Claude 2). It is a real overlap, but it changes §5's `상충` definition, which P3/P4 tuned against spurious conflicts (defect 5). It needs its own round.
- **Aggregate disclosure of name merges** (Astra 4, Claude 5). It overlaps, but it is a recording duty on every aggregate, the shape that lengthened notes in rounds 1–3.
- **Edition rule** (Claude 4) and the unscoped "partial information vs remaining gap" half of Astra 5: single-reviewer.

**Pre-freeze fidelity check** (as rounds 1–6): one fresh-context dispatch each, to `gpt-6-astra` (no web) and to `claude-opus-5-5` (safe mode). Each reads:
- the two round-6 comparatives' proposal sections,
- `../round6/RESULTS.md` §Verdict and §"What the round shows",
- this change list,
- `prompts/P6-to-P7-rc.diff`.

Each answers per part, (a) and (b): applied faithfully / material distortion / missing; scope creep; new defect. Each then returns FREEZE or MATERIAL OBJECTION. A material objection is applied once, toward the stricter wording, without a second check. The frozen hash replaces the placeholder above, and the edit is kept as `freeze-check/rc-to-frozen.diff`. Records go in `freeze-check/`.

**Result (2026-10-20).** Both on the fresh-context brief `7299b7ac…` (`freeze-check/header.txt` + `doc1–4.txt`; the same assembly reproduces round 6's `75d023b3…`).
- **Astra** (no web): CONFIRM FREEZE. Both parts were applied faithfully, with no scope creep and no new defect. The §4 A direct-URL tension is the declared one, and ⑤'s summary line is the intended exception.
- **Claude** (safe mode): CONFIRM FREEZE. Both parts were applied faithfully, with no scope creep and no new defect. Its one residual risk is that a fetch made to recover a quote may put the sought sentence in the fetch prompt, and the fetch summariser may echo it back. That would put the quote marks back under the fetched link (round 6's K7 shape on another link). It belongs to the untaken WebFetch half and is not a defect of this edit. It is recorded as a watch item (§5).
- No objection, so P7 = the rc byte for byte (19,149 bytes). There is no `rc-to-frozen.diff`. Diffs: `prompts/P6-to-P7.diff`, with the full contrast in `prompts/P0-to-P7.diff`.
- Combined prompt hashes (prompt + `gemini-rights.txt` + `run-block.txt`): P0 `9d2202d3…`, equal to rounds 4–6; P7 `13d5142c…`. Both are pinned in `manifests/`, and a runner dry run accepts both.

At freeze, the P7 manifests' `expected_prompt_sha256` (now the round-6 P6 combined hash, which the runner would refuse) is replaced with the frozen P7 combined hash. §3 then records both combined hashes, and a runner dry run must accept both.

The frozen scope (this file and `prompts/P7.md`) is committed and pushed before the first generation. The commit sha, and any rebase that rewrites it, is recorded in RESULTS.md.

## 2. Producer

| Environment | Model | Effort | Tools | CLI |
|---|---|---|---|---|
| Claude CLI | `claude-opus-5-5` | medium | WebSearch + WebFetch | 2.1.304 (checked 2026-10-20 at predeclaration; re-checked at dispatch), `--safe-mode` |

- Astra lane (fidelity check and review): ChatGPT.app-bundled `codex-cli 0.163.0-alpha.10.2`, checked 2026-10-20, re-checked before the fidelity and review dispatches.
- A producer run that loads hooks, memory or extra tools is a harness failure: it gets its one `-rerun` (§4).
- Round 7 is compared with round-7 P0 only, never pooled. A CLI version change between this file and dispatch is recorded. A patch-class auto-update is not a stop; anything else is (§9).

## 3. Album and inputs

- Album: Gemini Rights (Steve Lacy, 2022), standard 10-track edition, as rounds 1–6.
- The same dispatched input bytes as rounds 4–6, copied from `~/.local/share/myblog-research/stage-b-round6-inputs/` to `stage-b-round7-inputs/`. sha256 checked at predeclaration: `gemini-rights.txt` `fcdea93c…`, `run-block.txt` `259ecbdf…`, both equal to round 6. The P0 manifests pin the combined prompt hash `9d2202d3…`, which the runner enforces.
- No annotation block, no prod re-render.

All P4–P6 changes, and this one, were derived from this album's outputs. A pass is a development result on training material, and advancement stays conditional on Stage C's held-out panel.

## 4. Runs and limits

- 2 arms × 1 environment × 1 album × 3 runs = **6 generations**. IDs are `cl-<P>-gemini-rights-r<n>`, P ∈ {P0, P7}.
- Order (counterbalanced, as rounds 4–6): r1 P7, r1 P0, r2 P0, r2 P7, r3 P0, r3 P7. Serial.
- A 1,500 s ceiling, no automatic retry, one `-rerun` per harness failure, Bash `run_in_background`, and no redispatch of a claimed ID.

## 5. Review

As round 6 §5, unchanged apart from names:
- Every per-output packet and both comparatives carry `<D6_DEVELOPMENT_RULES>` (R-a–R-c) and `<D6_FROZEN_REFERENCE>`. Astra's packet differs from Claude's only in the no-web sentence.
- **Reference freshness.** `recheck_reference.py` re-captures Qobuz `zbylnavz5biaa` before the first generation. On a byte match of the ten credit lines, the frozen text is used with its capture note saying it was re-checked at round-7 dispatch. On any difference the round stops before generation and the owner is told.
- **Tooling**, copied from round 6 with names changed only (`build_review_inputs.py`, `build_comparative_inputs.py`, `tally.py`, `recheck_reference.py`, `redact_for_publication.py`, `run_lane.sh`, `run_review_lane.sh`, `review/run_comparative.sh`). New: `summary_quote_scan.py` (§6 (d)). sha256 of each is recorded in RESULTS.
- Labels come from one `secrets.SystemRandom` draw, made after all 6 outputs have an outcome. The defect list is unchanged.
- **Claude** (`claude-opus-5-5`, safe mode, web tools) audits all 6 outputs and the sentinel, then writes one comparative over its 7 reports. **Astra** (`gpt-6-astra`, no web) does the same.
- **Sentinel.** Round-1 S03, relabelled into the pool as before, for continuity. It gates nothing.
- **Orchestrator source check.** Every single-reviewer D1–D5 FAIL on a P7 output is checked against that output's producer trace and the frozen anchors, and the checks are recorded in a table, as in rounds 4–6. **A D4 FAIL on a quote cited to a search summary is checked the same way.** It is confirmed only if the passage is not in the cited summary, or a link to which the note assigns it does not hold it. A D4 FAIL on quote marks around text received only in a fetch summary is confirmed only if the fetched page does not hold the passage.
- **Watch (fidelity check, Claude).** For every quote a P7 or P0 note keeps in quote marks under a link it fetched, the orchestrator checks whether that fetch's prompt contained the quoted sentence. Hits are listed next to the (d) change-1 row. They are descriptive and are not units of that row.
- The comparative brief names only the reader's own report count.
- Known leakage: original-first role strings, the ① tool-output line, P6's ③ comparison-range legend, and now "검색 요약" source lines can reveal P7.
- Budget: 2 fidelity dispatches + 16 review dispatches (Claude 7 + 1, Astra 7 + 1). Per account: Claude 1 + 6 + 7 + 1 = 15; Astra 1 + 7 + 1 = 9.

## 6. Decision rule (predeclared)

P7 advances only if all of these hold:
- (a) After comparative calibration, no P7 output (3 runs) has an **agreed** FAIL on D1–D5. Agreed means both reviewers FAIL the same dimension, or one does and the orchestrator confirms it against sources, with the check recorded.
  - The confirmation rules in §5 treat a passage held in the cited search summary as recoverable, with the query in ⑤, although the anchors' D4 PASS asks that a non-producer reader recover it. The same rule applies to both arms. Under it, a P0 output that files a summary quote under a link is confirmable, and a P7 output that cites the summary is not. The verdict depends on that reading, and RESULTS will say so.
- (b) No gate allegation on a P7 output remains unresolved. The owner adjudicates any that remain.
- (c) After calibration, P7's FAIL marks summed over its 3 runs are no more than P0's. A mark is one (run, reviewer, dimension) FAIL on D1–D5, from either reviewer.
- (d) The recurrence of each pilot defect is listed per P7 output and compared against round-7 P0, with these targets:

  | Defect | Targeted by |
  |---|---|
  | 2 | change 1 |
  | 3, 5 | P6 change 1, carried; contradicted absence values must not come back |
  | 4 | P5 change 1, carried; it must not come back |
  | 6, 8 | P4's changes, carried; they must not come back |

  Three extra rows, counted by the orchestrator for every P7 and P0 output, each with the location recorded:
  - **Search-summary quote filed under a link (change 1).** The unit is one (output, quoted passage): `summary_quote_scan.py --blind` lists passages present in a search summary and in no fetch result. The orchestrator reads each citing line and counts the unit when the passage is in quote marks and cited to a URL-bearing source line whose received text, if any, does not hold the passage, whether or not the URL is in that search's link list. A unit cited to the search summary, or written without quote marks, is not counted and is listed. The unit does not depend on P7's wording, so P0 can score on it equally. Limits: a passage fetched from link A and cited to link B is excluded by the no-fetch test, and the regex sees only Latin-initial passages of 20–200 characters, so quotes rendered in Korean are invisible.
  - **Contradicted absence value** (P6 change 1, carried): as round 6 §6 (d).
  - **Dropped source uncertainty marker** (P5 change 2, carried): as round 5 §6 (d).

  **The orchestrator's pass for the first two rows runs over the blind labels S01–S07, and its table is committed before `blind-key.json` is read for analysis.**
- (e) The median `output.md` length of P7's 3 runs (Python `len`, characters) is no more than 1.10 × the median of P0's 3 runs.

With fewer than 3 usable outputs in either arm, the round gives no verdict and is reported as incomplete. A run lost to a harness failure first gets its one `-rerun`.

Every arm comparison reports all 3 runs' values, not a median alone. Round-6 P6's values sit beside them, descriptively only.

**D6, descriptive (not part of the rule).** As round 6 §6: per output and the sentinel, the Claude D6 level and route, whether the credits rest on the authoritative row (from the trace), and Astra's D6 in a side column.

## 7. Owner time

- Confirmation of this scope, including the base choice (§1), before any dispatch.
- Adjudication of any surviving gate allegation (0–1 h).

Nothing is drawn from the confirmation budget.

## 8. Publication

As rounds 4–6:
- Every record embedding the Gemini Rights catalog block has its owner-collection line redacted before push. `PUBLICATION-REDACTIONS.json` records the dispatched-byte hashes.
- A token scan must then find 0 hits.
- Originals stay outside the repository.

## 9. Stop conditions

- A non-patch CLI change. (A run that loads hooks, memory or extra tools is a harness failure with one `-rerun`, §2; a second such failure in the same ID stops the round.)
- A re-captured reference that differs from the frozen one (§5).
- Input or P0 combined-prompt hashes that differ from round 6's (§3).
- A rate limit: the lane halts and nothing is redispatched. The round resumes only on the owner's word.
