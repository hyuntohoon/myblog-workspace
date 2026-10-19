# CHORE-research-model-evaluation: Develop a research prompt that passes jointly agreed usefulness criteria

- **Status**: draft
- **Owner**: Park Hyun
- **Created**: 2026-10-15
- **Plan row**: `docs/plan.md` → CHORE-research-model-evaluation (FIRST PLANNED PRIORITY)
- **Execution authorization**: The owner explicitly requested this bounded experiment in chat on 2026-10-15. The owner expanded the goal on the same date to iterative prompt development against criteria informed by both GPT and Claude. This does not self-promote RFC Status or approve production adoption.

## Goal

Complete a prompt that reliably gathers useful pre-review evidence efficiently for a music critic. Agree explicit acceptance criteria and thresholds using independent GPT-6 Astra and Claude proposals, then improve and test prompt/model combinations until a candidate passes those criteria on development and held-out albums. Choosing a model supports this objective; winning a relative ranking is not sufficient.

The owner explicitly allows different structures, outlines, headings and expression. Evaluate the value, reliability and acquisition/use cost of the evidence, not conformity to the current output template. Do not write the critic's argument or verdict.

The already-authorized one-run-per-eligible-model comparison on *Gemini Rights* is the diagnostic pilot. Preserve its frozen inputs, outputs and provisional scoring; it is not an acceptance test under jointly agreed criteria.

## Non-goals

- Change the production research prompt, PROMPT_VERSION, model, queue, poller activation or stored notes.
- Use separately billed models (Fable 5/5.1), API keys, purchased credits or paid fallbacks.
- Generate or publish a music review, import critics' judgments, or claim to have listened.
- Treat one album / one run as a statistically reliable model ranking.
- Treat format compliance, verbosity, source counts or speed alone as evidence of research value.
- Automatically adopt every reviewer suggestion or repeat the full model matrix for each prompt revision.

## Current state

- Canonical prompt: `docs/editorial/album-research-prompt.md`; runtime mirror: `scripts/album_research_v2.md`, content last changed in `7b4789110581b638926a9c1550cdb97de2499e84` (2026-07-30).
- `scripts/research_poller.py` selects `PROMPT_VERSION=v2` and adds album/Genius/catalog/refine context. The headless addendum pins the edition without pausing.
- v4 remains a candidate. `CHORE-research-prompt-port-not-swap` recorded a 12/22 versus 12/22 *RENAISSANCE* coverage tie; it is not factual-precision or human-usefulness proof.
- The supplied *Gemini Rights* note exposes missed direct sources, insufficient extraction from retrieved interviews, unverified role aggregates, sparse direct links and low-value sample digressions.
- The revised prompt is a proposal, frozen verbatim from the immediately preceding chat response, not an already-deployed prompt.
- Model availability is discovered from account catalogs, then verified by actual dispatch. Hidden/internal GPT models are excluded. Catalog presence alone is not execution success.
- Shared checkout is busy; work uses `/private/tmp/myblog-research-eval`, branch `docs/CHORE-research-model-evaluation`, starting at `dbec55c4ac3f9600fc1a3b5100f5a9332943c4a3`.

## Target state

Artifacts: `docs/reviews/measurements/2026-10-15-research-model-evaluation/`.

1. Preserve the diagnostic pilot and complete its missing Claude outputs/review when account access permits.
2. Use the common criteria-design brief in `docs/editorial/research-note-acceptance-design.md`. Collect independent Astra and Claude proposals before reconciliation; preserve disagreements and evidence rather than averaging opinions.
3. Freeze a versioned acceptance contract: metric definitions, evidence/denominators, critical failures, dimension minimums, numerical thresholds, reviewer rules, source-access treatment and a finite test matrix. The current pilot weights are provisional, not jointly agreed.
4. Iterate prompt candidates in bounded, predeclared rounds. Freeze each candidate and control before dispatch. Distinguish prompt changes from model/tool changes; retain rejected candidates and failure evidence.
5. Validate the frozen candidate on untouched albums and critic-use tasks. A failed holdout returns the candidate to development; a subsequently used album is no longer untouched. Require new held-out evidence for any later completion claim.
6. Deliver the exact passing prompt, a flexible concise output guide, recommended model/tool conditions, evidence of passing, residual limitations and reproducible artifacts. Production adoption is separate.

## Diagnostic pilot contract

- One revised prompt, one album, one generation per eligible model; no live v2 comparison in this round. The original supplied note is a historical reference only.
- Equal task/album/edition/cutoff/instruction bytes. No old note, correction sheet or preferred sources are fed to generators.
- Medium effort where supported; no effort parameter on a model whose catalog supports no thinking control. Record this difference rather than inventing equivalence.
- Claude WebSearch/WebFetch and Codex live web tools are different harnesses. This measures usable model-plus-tool output, not a tool-independent causal model effect.
- Each provider is serialized; independent provider lanes may overlap. Claude uses the existing shared subscription guard. Existing jobs are not disabled, resumed or changed.
- 1,500 s wall ceiling per generation; no fallback or automatic rerun. Record infrastructure failure without grading it as poor research. Throttling stops that provider lane and leaves remaining entries not-run.
- Retain actual resolved model when emitted. Never infer successful routing solely from the requested alias.
- Do not rank incomplete/failed notes against complete notes as if they were equivalent observations.

## Evaluation and acceptance

The pilot's frozen `rubric.md` uses weights 25/20/20/10/10/10/5 across accuracy, important evidence, provenance, roles/uncertainty, density, musical context and usability. These weights were not jointly designed with Claude and have no final pass threshold. Preserve them for historical comparison; never silently rescore old outputs under a new contract.

Final criteria must serve **efficient collection of evidence useful to criticism**. Assess important omissions, factual support and source traceability, credit/edition precision, relevant musical context, honest uncertainty and critic autonomy. Assess efficiency across collection time and tool effort, reading time and human reverification burden. Shortness, URL count, broad track coverage or fast generation are indicators to investigate, not automatic benefits. Do not force an unsupported fact onto every track for equal coverage.

A critical fabrication or material false attribution cannot be offset by fluency or a high total. Specify critical failures and per-dimension floors before confirmatory testing; both reviewers must assess each dimension, explain disagreements and record unresolved uncertainty. Model reviewers can propose likely usefulness; actual critic task outcomes must be measured separately. Claude agreement, final weights, numerical pass lines and human-use evidence are currently pending.

`docs/editorial/research-note-acceptance-design.md` defines the joint-design workflow. Neither an Astra-only score nor the best model in a weak batch completes the goal.

## Diagnostic pilot steps (historical bounded authorization)

The owner requested the experiment as one bounded task. Steps 1–4 below are **additive parts of one experimental delivery**, permitted together; they are not successive production releases.

### Step 1 — Freeze protocol and record priority

Preserve writing block 73184 verbatim, common input, inventories, manifest, rubric and no-production boundaries. Add the highest-priority plan pointer and supersede the earlier planning order without erasing unrelated work.

**Verification**: prompt hash; manifest uniqueness; exact eligible count; `git diff --check`; workspace invariant checker.

**Rollback**: revert only this RFC/plan/artifact commit; no service rollback.

### Step 2 — Generate once per model

Use an auditable runner; fresh directory and context per dispatch. Store input, stdout/tool events, note, stderr, resolved model and timing. Do not call the production queue or modify a research row.

**Verification**: one attempt marker per eligible model; no retry/fallback; runner focused tests; inspect actual tool-access and model events. Account restrictions are outcomes, not permission to route around them.

### Step 3 — Independent Astra and Claude review

Review all usable samples under blinded labels. GPT reviewer is exactly `gpt-6-astra`; Claude reviewer is `claude-opus-5-5` from the account catalog. Give reviewers source evidence sufficient to check key claims and allow verification of unfamiliar cited claims. Keep reports independent until both are frozen. Require evidence locations for defects and explicit confidence/limitations.

**Verification**: exact reviewer identity; identical review packet hash; separate reports; every sample covered or reason recorded. Preserve both scores on disagreements.

### Step 4 — Reconcile and recommend

Report per-model quality, severe errors, omissions, evidence support, density, runtime and token measurements. Explain both reviewers' feedback on the preferred model's output and on the prompt. Distinguish prompt-induced defects from model/harness failures. Update execution record; production adoption remains separate work.

**Verification**: all manifest entries have a terminal or explicitly blocked/not-run status; original outputs unchanged; recommendation links evidence; no claim that a single run establishes general superiority.

## Next development stages

These are research stages under the owner's expanded goal, not production releases. Freeze the next finite round before execution; no unlimited retries or automatic full-matrix reruns. Existing subscription-only and no-fallback boundaries apply throughout.

### A — Joint acceptance design (criteria frozen 2026-10-16; pilot review completion in progress)

Collect Astra and Claude proposals under the same brief. Reconcile criteria, record objections and freeze a measurable acceptance contract before evaluating a new candidate for passage. Complete the historical pilot review independently; keep its scores separate from criteria design.

**Gate**: both named reviewers' contributions preserved; each criterion and threshold has a rationale, metric/evidence definition and resolution record. Missing Claude input leaves this gate open.

**State (2026-10-16):** criteria part met. `criteria/acceptance-v1.md` is frozen after four rounds, and both contributors answered CONFIRM FREEZE. Numeric floors are deliberately uncalibrated: the contract's §6 calibrates them with the owner before confirmation, and an acceptance-critical floor that cannot be calibrated defers acceptance. **Stage A-2 met 2026-10-16:** anchors-v1 (`criteria/a2-anchors/anchors-v1-rc.md`) is frozen after four rounds with both contributors (round 4: both CONFIRM FREEZE), and `criteria/round-manifest-v1.md` freezes albums, blocks, categories, environments, control and the allocation draw. The §6 scoring manual and the §7 binding floors are still open by design; they freeze before calibration and before any confirmation output respectively. The historical pilot review is tracked under Execution record.

### B — Bounded prompt development

Use the pilot defects and joint criteria to propose a minimal prompt revision. For each round predeclare candidate/control hashes, model/tool configuration, albums, run count, limits and stop conditions. Keep the model/tool fixed for a prompt contrast; make any model contrast separately identifiable. Include only purposeful reruns, with run identifiers that cannot overwrite the pilot. Change format freely where it improves evidence use.

**Gate**: all predeclared dimensions pass; no critical failure; no unresolved material disagreement; a plausible workflow efficiency improvement with its measured limitations. If a round exhausts its budget, report unmet criteria and plan the next bounded round rather than declaring success.

### C — Held-out and critic-use validation

Before candidate tuning, reserve an unseen panel spanning source-rich/source-poor albums, relevant language differences and different credit/sample complexity. Freeze exact album IDs and critic tasks in the round manifest. Keep development corrections/reference answers out of generation inputs. Measure the critic's ability to locate useful evidence, verify important claims and identify remaining gaps; record time and avoid mistaking an AI simulation for a human trial.

**Gate**: frozen acceptance contract passes on the predeclared panel, with reviewer agreement or evidence-resolved disputes and actual critic-use evidence. Report small-sample limits; do not claim universal superiority.

### D — Deliver the passing prompt

Provide exact version/hash, tested model/tool conditions, prompt diff, sample note, pass/fail matrix and remaining limits. Preserve the criterion version and evidence supporting every completion claim. Keep the plan item active while any required criterion, joint review or validation remains outstanding.

## Open questions / pending evidence

- Claude criteria proposal: received 2026-10-16; acceptance-v1 frozen. Pilot review: see Execution record.
- Numerical floors: uncalibrated by design; calibrated under acceptance-v1 §6 with the owner before confirmation. Panel and budget: fixed by the owner on 2026-10-16 (see Decisions log); exact album IDs and top-3 categories go in the round manifest.
- Actual critic-use tasks and observed outcomes: not yet measured.

## Decisions log

| Date | Decision | Step |
|---|---|---|
| 2026-10-15 | Owner: highest planned priority; record RFC and plan, test every available model once, GPT feedback must use Astra. | 1–4 |
| 2026-10-15 | Owner clarification: use the just-proposed revised prompt; compare both Claude and GPT models. | 1 |
| 2026-10-15 | Owner clarification: subscription-included models only; exclude separately billed Fable models. | 1–2 |
| 2026-10-15 | Owner: final goal is a prompt passing jointly designed GPT/Claude criteria for efficient research useful to a critic; structure and wording are free. Model selection is supporting evidence, not the endpoint. | A–D |
| 2026-10-15 | RFC Status remains draft; direct chat authorizes the bounded experiment, no production/status promotion inferred. | All |
| 2026-10-16 | Owner (chat): confirmation panel = 2 calibration + 4 untouched albums, about 30–60 owner hours; run **both** Claude CLI and Codex environments (32 confirmatory calls); baseline = the owner's usual research; time-saving and quality-improvement claims judged separately. | A, C |

## Protocol disclosure

The account-level Claude limit prevents completion of the originally planned two-family blind comparison in this run. A producer-labelled **owner-only interim GPT summary** is prepared before Claude's report exists; this is an explicit deviation from waiting for both reports before unblinding. The future Claude CLI judge must receive only the unchanged anonymous packet and anonymous trace support, never the owner summary, key, model-labelled run directories or Astra scores. Astra's per-output audits used two isolated instances of the requested same model; comparative calibration preserves their original scores. The interim preference is not the final cross-provider selection.

## Execution record

- Protocol frozen; runner offline tests: 13 passing. Workspace invariants and 23 parser tests passed.
- Local protocol commit: `75706eb`. The initial GitHub push/PR was rejected by automatic approval review because export of the user-supplied note was not explicitly authorized. On 2026-10-16 the owner authorized push and merge with that original note excluded. Publication uses a fresh commit based on current main, excluding the original from the full published history; the earlier local commits remain local.
- Account catalogs: 7 GPT + 10 included Claude models; 2 separately billed Fable entries excluded.
- Claude first dispatch (`claude-opus-5-5`) returned HTTP 429 `usage_limit_reached`: "resets 2:40am (Asia/Seoul)". At this 2026-10-15 evening run, the announced next reset is 2026-10-16 02:40 KST. Usage counters and web requests were zero; no Claude research output exists. Remaining 9 included Claude models are `not_run`, not quality failures. The independent Claude reviewer is also pending this external limit.
- GPT generation completed: 7/7 successful; single dispatch each, 66.939–287.947 seconds, 4,995–8,365 output characters. Requested model IDs were pinned; resolved identities were not exposed by Codex events.
- All 7 blind per-output Astra audits completed: individual scores 56–85.5/100. Final Astra comparative calibration completed with no score changes. `interim-results.md` preserves the provisional anonymous GPT candidate and caveats. No overall winner, Claude verdict or completed cross-provider comparison is claimed.
- Resume after the Claude external reset: only missing Claude generations/review, preserving the zero-token failure and all completed GPT outputs; no automated wakeup was configured.

- Goal extension recorded: the pilot remains diagnostic. Independent Astra acceptance-criteria proposal received and preserved under `criteria/`; common criteria brief checked with no Claude opinion supplied. Any proposed round size is unagreed, not dispatched. Claude contribution and a jointly frozen acceptance contract are pending. No final prompt or acceptance pass is claimed.

- 2026-10-16 publication scope: owner explicitly approved push and merge of the RFC, priority plan, prompts and experiment results, excluding the original attachment. This publishes the research record, not a completed acceptance result or production prompt change.

- **2026-10-16 Stage A session.**
  - **Claude generations.** Resumed after the reset in a separate run directory: 10/10 success, one dispatch each, identical input hash. The 10-15 zero-token 429 record is preserved.
  - **Criteria.** The Claude criteria proposal was received from a fresh `claude-opus-5-5` CLI context with the identical brief. Reconciliation then went through four rounds with both contributors in fresh contexts, ending with both answering CONFIRM FREEZE.
  - **acceptance-v1.** Frozen, including the owner's resource decisions (Decisions log).
  - **Astra harness note.** The Astra round-1 dispatch failed first because the PATH Codex CLI 0.147.0 rejects `gpt-6-astra` (HTTP 400, zero inference). It was rerun once with the ChatGPT.app-bundled 0.162.0-alpha.17.2, the pilot's recorded version, and both records are kept.
  - **Pilot review.** Completed: Astra audited the 10 new samples, Claude audited all 17, and each reviewer ran one comparative calibration. Reviewer agreement is ρ = 0.90.
  - **Pilot results.** Both reviewers put `gpt-6-astra` and `gpt-6.1-sol` in a tied top group. Claude CLI WebFetch returns helper-model summaries, which both reviewers link to recurring provenance and extraction defects. The result is therefore a model-plus-harness observation (`pilot-final-results.md`).
  - **Gates.** Pilot Steps 1–4 are complete. The Stage A criteria gate is met. No prompt has passed, and production is unchanged.

- **2026-10-16 Stage A-2 session.**
  - **Anchors.** Both contributors wrote anchor sets independently in fresh contexts from one brief (`a2-anchors/brief.txt`). The orchestrator reconciled them under the acceptance-v1 rule (keep both, adopt the stricter placement). Round 2: both MATERIAL OBJECTION with replacement text, applied. Round 3: Astra CONFIRM FREEZE; Claude MATERIAL OBJECTION on D2 FAIL, D11 PASS and R5, applied verbatim. Round 4: both CONFIRM FREEZE. One clerical provenance edit followed at Claude's suggestion; no scoring text changed. Frozen file sha256 `b9a3296f…`.
  - **Round manifest v1.** Albums and blocks, categories, environments, control and inputs, and the allocation draw (`round-manifest-v1-allocation-draw.json`, one `secrets.SystemRandom` execution recorded verbatim) are frozen. §6 and §7 parts remain open as the contract requires.
  - **Interruption.** The session that ran rounds 1–3 ended at 14:52 KST before reading the round-3 replies. A second session picked the work up from the uncommitted worktree, applied Claude's round-3 text and ran round 4. The shared-db guard worktree used by rounds 1–3 had been removed in a cleanup; round 4 used a fresh worktree at the same commit `b15bd71`.
  - **Gate.** Stage A-2 is met. Next: Stage B, the first bounded prompt round, predeclared in the manifest before any dispatch.

- **2026-10-16 Stage B round 1** (`stage-b/round1/`, results `stage-b/round1/RESULTS.md`).
  - **Scope.** The owner confirmed the scope in chat before dispatch; `ROUND.md` was committed before any output. Candidate P1 = pilot prompt P0 + the seven converged amendments, frozen after one fidelity check by both reviewers (both MATERIAL OBJECTION, applied once). Control: P0. Albums: Gemini Rights and 2000 TAPE (owner's choice; post-cutoff Korean, 0/20 Genius matches). Producers per round manifest v1 §4.
  - **Runs.** 8/8 generations, 16/16 blind per-output audits and 2/2 comparative calibrations, each dispatched once.
  - **Verdict under the predeclared rule: P1 does not advance.** Three of four P1 outputs have a D1–D6 FAIL; P1 has more FAILs than P0 in two of four cells; P1 notes are 27–79 % longer, with ritual repetition in all four. Three gate allegations on P1 outputs are unresolved; the owner deferred adjudication because it cannot change the verdict. Published records redact the owner's collection signal (`stage-b/round1/PUBLICATION-REDACTIONS.json`). D7 is not assessable in a development round without a frozen map.
  - **Harness finding.** Every Claude CLI lane run (producer and reviewer) fires the user's SessionStart hooks and loads the global `~/.claude/CLAUDE.md`, despite the isolated cwd. Pilot and Stage A Claude-lane records share this exposure. Round 2 must exclude user settings from the Claude lane.
  - **Next.** A bounded round 2, predeclared and owner-confirmed, built from the reviewers' overlapping definition/deletion proposals (access labels, complete credit-row transcription with scope tests, gap justification, compression). No prompt has passed; production is unchanged.
- 2026-10-16 Stage B round 2: predeclared and owner-confirmed (`stage-b/round2/ROUND.md`; P2 = P0 + the four overlapping round-1 calibration points; §7 (a) now counts agreed or source-confirmed FAILs). The research runner runs the Claude CLI with `--safe-mode` and fails any Claude run that loads hooks, memory or extra tools. Generation paused by the ChatGPT usage limit (Codex 4/8, Claude 8/8); resume after 2026-10-22 20:08 KST per ROUND.md §10. No review yet, no verdict.
- 2026-10-18 Stage B round 2: the ChatGPT limit lifted early (one read-only Astra probe succeeded at 17:24 KST); owner approved resuming now (`ROUND.md` §11, which also records the Codex CLI auto-update to 0.163.0-alpha.10.2). The four Codex `-resume` runs all succeeded; the two Gemini Rights inputs are redacted per §9. All 16 cells have an outcome. No review yet, no verdict.
- 2026-10-18 Stage B round 2 reviewed (`stage-b/round2/RESULTS.md`): blind draw, 34/34 per-output audits, 2/2 comparatives; both reviewers met the sentinel control (Claude only at BORDERLINE). **P2 does not advance**: (a) agreed FAILs on two Claude-lane P2 outputs; (c) P2 worse than P0 in both Claude CLI cells, no worse in both Codex cells; (e) holds at 1.098×; (b) five allegations open, unable to change the verdict. The four Codex · P2 outputs have no FAIL from either reviewer; 30 of 32 FAIL marks are on Claude-lane outputs. Next: predeclare a bounded round 3 from the four overlapping comparative proposals, and decide how the Claude CLI WebFetch confound is handled. No prompt has passed; production is unchanged.
- 2026-10-19/20 Stage B round 3 (`stage-b/round3/ROUND.md`, results `stage-b/round3/RESULTS.md`). Gemini Rights only, by owner direction. Arms: P0, P3 (P2 + the four overlapping round-2 points), and P3G (P3 + a Genius community-annotation input block and one rule), the last at the owner's request. Owner decisions: per-environment verdict; annotation arm added; scoring-manual gaps deferred. After generation the owner **discontinued the Codex producer lane** for cost (0.6–1.3 M input tokens per note) and cut the Astra review to the Claude-lane outputs, run with no web tool. **Neither P3 nor P3G advances.** In the Claude lane both meet (a)–(c) (P3: 2 FAIL marks vs P0's 5; scope conflicts gone), but both fail (e) on length (1.248×, 1.303×). Edit 3 (numerators from the checklist) introduced a numerator-inconsistency defect absent from P0. The annotation block yielded one lead (Vulture), followed to the original once in the Codex lane. Next: a round-4 predeclaration, Claude lane only. No prompt has passed; production is unchanged.
- 2026-10-20 Stage B round 4 (`stage-b/round4/ROUND.md`, results `stage-b/round4/RESULTS.md`). Owner decisions recorded in ROUND.md: no annotation arm; D6 judged by the Claude reviewer alone. Claude CLI lane only, Gemini Rights, P0 vs P4 (P3 with edit 3 reverted, per-claim attribution to the received document, verbatim role strings, access text once in ①, and a whole-note 6,000-character cap with a protected cut order), 3 runs per cell. Owner-confirmed and pushed before dispatch. **P4 does not advance**: (a) fails on one orchestrator-confirmed Astra D5 FAIL (a source's "tentative" dropped). (c) holds at 3 vs 5 FAIL marks, (e) holds at 1.005×, and defect 2 went from 6 marks to 0. One G4 allegation on P4 is open but cannot change the verdict. Neither reviewer met the sentinel D6 control; the Claude reviewer has given 0 D6 FAILs in 37 audits, so D6 is unmeasured under the current design. Next: a round-5 predeclaration from P4. No prompt has passed; production is unchanged.
