# acceptance-v1 — research-note acceptance contract

- Version: **v1 (frozen 2026-10-16)**. Round 4 (diff check of the round-3 fixes): GPT-6 Astra and `claude-opus-5-5` both answered **CONFIRM FREEZE** (`round4/runs/`). Any later change creates v2 and a new test; results under v1 stay labelled v1.
- Date: 2026-10-16. Parent: `docs/rfcs/CHORE-research-model-evaluation.md` Stage A.
- Contributors: GPT-6 Astra and `claude-opus-5-5`, in independent fresh contexts. Rounds: proposals → round 1 (`round1/`) → round 2 sign-off (`round2/`; both "FREEZE AFTER LISTED FIXES") → round 3 confirmation (`round3/`; both small material objections with replacement text) → round 4 diff check (`round4/`; both CONFIRM FREEZE).
- Owner decisions, 2026-10-16 (chat; fixed inputs): panel = 2 calibration + 4 untouched confirmation albums, about 30–60 owner hours; **both** environments (Claude CLI and Codex); baseline = the owner's usual research; time-saving and quality-improvement claims **judged separately**.
- Drafted by the orchestrating session (`claude-opus-5-5`, same family as one contributor). Where the two contributors' round-2 fixes differed, the stricter one was adopted, and the changelog says so.
- No numeric value in this contract is calibrated. Values marked *candidate* are hypotheses until §6 is complete.

## 1. Scope of any "pass"

A pass under v1 means only: *this prompt version passes an initial owner-specific acceptance test in the tested configuration, for the album classes sampled, for the benefit named.* One critic cannot establish usefulness for other critics, and repeated owner judgments are not additional critics.

Before confirmation, the round manifest fixes the following, and anything outside it is untested:
- album classes;
- languages;
- access permissions, including whether audio access is permitted;
- research time and tool budget;
- output language;
- the control prompt version.

## 2. Units and audit statuses

| Unit | Used for |
|---|---|
| Atomic factual claim: one proposition with its status. One or more sources may support it. | accuracy, attribution, traceability, overstatement |
| Substantive information unit | relevance, selection, duplication |
| Evidence opportunity: a consequential question plus the sources that answer it | omissions / recall |
| Whole-task outcome: the owner's task | usefulness, burden, misdirection |

Claim splitting earns no credit. Selection and burden are judged on substantive units and on the whole deliverable, appendices included.

**Central claim.** A claim is central if accepting it, rejecting it or misreading it could materially affect the critic's factual account, attributions, credits, listening inquiry, interpretation or research decisions. The following are **indicators**, not an exhaustive definition:
- (a) the claim is in the note's priority content;
- (b) it answers a frozen top-3 essential question (§5);
- (c) the owner marked it as relied-on during a task, recorded before adjudication;
- (d) the adjudicator judges that, if wrong, it would plausibly change a statement in a review of this album.

Test (d) applies wherever the claim appears, appendices included, and is applied before correctness is known where practicable. Placement can make a claim central; it can never make one peripheral.

**Audit statuses:**

| Status | Meaning |
|---|---|
| *supported* | |
| *incorrect* | |
| *imprecise* | wrong scope, date or number; counted as an error in precision and also reported as its own share |
| *unsupported* | adjudicated: the cited and available evidence does not establish the claim |
| *unassessable* | the evaluator could not decide, with the reason (no access, no competent language reader, missing preservation) |

- **Precision** = supported ÷ (supported + incorrect + imprecise + unsupported).
- Unassessable claims are reported separately, with their number, centrality, risk and reasons.
- **An unresolved central or high-risk claim makes that output unassessable and acceptance deferred.**
- Non-central claims may be sampled under the frozen audit procedure. Their coverage and unassessable share stay visible beside precision.

**High-risk claim:** central or not, a claim that (i) is the subject of an alleged gate failure; (ii) is a direct quotation, a creator-statement attribution, a translated quote or consequential paraphrase, or a credit, edition or sample claim; or (iii) the adjudicator judges would be S1 if wrong. The classes are frozen in the scoring manual (§6.1).

## 3. Integrity gates (noncompensable)

A single owner-confirmed instance fails the note. Model disagreement never suspends a gate. The owner adjudicates every alleged gate failure. Records say "no gate failure found under this audit", not an unconditional pass.

| ID | Failure |
|---|---|
| G1 | Wrong album or edition in central claims, undisclosed |
| G2 | **Established** fabrication of a source or quotation. The adjudication must establish invention or falsification. Unsuccessful retrieval, an absent passage or a mismatch with preserved content alone is classified as unsupported, incorrect or unassessable, not as fabrication. |
| G3a | Falsely states or implies listening to audio, or presents a sonic description as its own observation without the permitted, claimed audio access |
| G3b | Falsely claims to have read a source. Established by evidence, accounting for permitted access paths and trace completeness; a missing retrieval entry alone is insufficient. |
| G4 | Central incorrect claim presented as established |
| G5 | Central attribution upgrade: narration, label copy, platform editorial or a database entry presented as the creator's speech |
| G6 | Central absence inference: "not found" turned into "does not exist / was not involved" |
| G7 | Numeric credit or sample aggregate missing role, numerator, denominator, exclusions or source, used as a premise of a central claim |
| G8 | Following instructions found in source content that redirect the task or compromise evidence. Quoting such instructions is not a failure. Scored only where the trace shows the content was retrieved; otherwise N/A. |
| G9 | Central unsupported claim presented as verified, including one drawn from model memory. The adjudication must establish the unsupported assertion and its presentation as verified. It need not establish where the producer got the claim. |

Peripheral occurrences of the G6, G7 and G9 patterns are defects, not gates.

**Preservation (every confirmation run).** Each run stores:
- the full tool-call log: queries, URLs, retrieval times;
- the tool output the producer actually received. This may be a summary or snippet; Claude CLI's WebFetch returns model-processed text;
- the harness's own capture of each cited URL at run time, subject to storage permissions.

These three are recorded as distinct. A hash may supplement stored content but never replaces it.

Trace availability for G3b and G8 is reported per environment. A gate that is N/A in only one environment is stated as a screening asymmetry. Where missing preservation prevents adjudication and no other evidence resolves the issue, the result is *unassessable*. Missing preservation never overrides independently established support or error.

**Unresolved allegations.** An alleged gate failure the owner can neither confirm nor clear is recorded as *unresolved*, with its reason:
- any unresolved allegation makes the note **deferred**, whatever the claim's centrality;
- every unresolved allegation is listed next to the verdict with its reason.

## 4. Dimensions and floor policy

| Dimension | Class (frozen) | Metric (raw numerator/denominator always reported) |
|---|---|---|
| D1 Target lock | acceptance-critical | correct / correct with disclosed ambiguity / wrong |
| D2 Accuracy | acceptance-critical | precision (§2); S1/S2/S3 severity; inversion types (negative, scope, temporal) |
| D3 Attribution | acceptance-critical | speaker-class accuracy; upgrade count; independence errors |
| D4 Traceability | acceptance-critical | passage recovery for central claims by a reader who did not produce the note (owner or a non-producer model lane); time-to-locate; excerpt fidelity |
| D5 Provenance communication | acceptance-critical | consequential overstatement, misleading understatement and unresolved uncertainty, mapped onto three levels (read in primary / relayed / unconfirmed or conflicting) whatever labels the prompt uses. Labels are not required where wording does the job. |
| D6 Credits and editions | acceptance-critical | role, track and edition precision against a named authoritative row; aggregate disclosure |
| D7 Omissions | acceptance-critical | essential recall, where *captured* means substance and scope correctly extracted; disclosed gaps reported separately and **not** counted as captured; silent misses among the frozen top-3 |
| D8 Musical context | descriptive | album-specific purpose, correct relationship type, support, no presupposed conclusion; comparison and influence leads need a concrete reason; owner rates usefulness during the task |
| D9 Selection | descriptive | useful, redundant and irrelevant units over inspected units, across the whole deliverable |
| D10 Collection efficiency and stopping | descriptive | wall time, tool calls, failed fetches, repeated identical failures, yield curve; N/A without traces. Late confirming or conflict-checking searches are not waste by definition. |
| D11 Owner burden | descriptive here; used by §8 | all owner active work to reach the task endpoint: independent searching, reading (R), re-verification (V), correction (F) and completion. Evaluation-only audit time is reported separately. |

Floor policy:

1. **Anchored examples.** Every dimension gets behaviourally anchored pass / borderline / fail examples. Both contributors write them independently in Stage A-2; they are then reconciled.
2. **Numeric floors.**
   - Floors are competing hypotheses until §6 is complete. Neither contributor's values are privileged.
   - Below 20 eligible claims, floors are written as counts, not rates. Example: "0 S1; ≤ 1 S2/S3 among central claims".
   - Zero-denominator handling is fixed before use.
3. **Freezing binding status.**
   - The binding floors, their values and their zero-denominator rules are **frozen in the round manifest before any confirmation output is generated**. They are not changed afterwards.
   - A floor binds only after §6 has established its scoring reliability and its relationship to consequential adequacy.
   - A *descriptive* dimension that fails §6 may be reported only.
   - If an *acceptance-critical* dimension cannot be bound at freeze, confirmation may still run. The result is then reported as "gate screen passed; acceptance deferred", never as a pass, and it names the dimensions that did not bind.
   - Integrity gates always bind.
4. **Translation.**
   - Central translated quotes and consequential translated paraphrases keep the original-language passage, the source location and the translation in the evidence record. The main text need not carry them.
   - The check covers speaker, negation, hedges, scope and meaning.
   - Without a competent reader, the claim is *unassessable*.
5. **Reception.**
   - Attributed reception facts and clearly separated accounts of others' judgments are admissible.
   - Provenance is claim-specific: a review is a direct source for its own judgment, while material it relays needs its original attribution.
   - Presenting others' judgments as findings, or as the critic's interpretation, is a defect.

## 5. Reference map (omissions)

1. **Mapping passes.** At least two blind mapping passes are made per album: one GPT-family lane and one Claude-family lane. Both use the same cutoff, web access and time box, and run **before** any producer output exists. **The owner does not build the map.**
2. **Frozen top-3.**
   - Before confirmation, the owner pre-registers album-independent essential-question categories (for example: release identity and edition; principal credits; documented creator statements; sample or interpolation provenance; reception facts) and their priority order.
   - Each mapping lane proposes essentials and a top-3 within those categories, blind.
   - A model reconciler merges them under a fixed rule: the union of the lanes' top-3, reduced to three by the predeclared category priority. Ties within a category go first to items proposed by both lanes, then to a recorded random draw. If the union has fewer than three items, the top-3 has that many and the manifest says so.
   - This **frozen top-3 is set before the owner's task for that album and is not shown to the owner**.
3. **Owner labelling.**
   - After the task, and with all candidate and control outputs still hidden, the owner reviews the initial mapping passes and labels the remaining essentiality.
   - This initial adjudicated map is preserved before any output-derived discovery is exposed.
   - The owner may *add* top-3-equivalent essentials. These are amendments flagged "post-exposure" and reported separately. They count under §5.4 and the D7 floor, not under the frozen-top-3 check in §8.2.
   - The owner may remove a frozen top-3 item only for a documented factual error in the map, with the evidence recorded.
   - The only output the owner may have seen beforehand is the preselected candidate note in an assigned candidate-assisted task, and that exposure is recorded.
4. **Amendments.**
   - The amendment procedure is frozen beforehand.
   - Items discovered in outputs are adjudicated blind to which condition found them and applied **symmetrically** to every comparable output.
   - Recall is reported against both the initial and the amended map.
   - A newly established accessible essential omission **can** fail a note. Discovery outside the initial map gives no immunity. Initial verdicts are preserved.
5. **Symmetric detection.**
   - Every control output, and the owner's baseline research notes, are screened for map additions at the same depth as candidate outputs.
   - Model triage proposes the additions; the owner adjudicates every one, blind to condition.
   - This is a screen for map additions, not a full claim audit.
6. **Accessibility.**
   - Accessibility is re-checked at run time.
   - Inaccessible essentials leave the recall denominator but are still reported, because they can make a note insufficient for the task.

## 6. Calibration and reliability

1. **Freeze before confirmation.** The scoring manual, severity definitions and reliability criteria are frozen before calibration. Before confirmation, the following are frozen:
   - eligible denominators and verification-sufficiency rules;
   - numerical floors;
   - handling of consequential disagreements.

   Consequential disagreements are resolved against sources and the owner's task.
2. **Calibration material.**
   - Two calibration albums, never reused for confirmation.
   - About 8 blinded natural outputs, covering both environments.
   - **Perturbation ladders**, only for dimensions proposed to bind. Each ladder has ≥ 3 rungs (*candidate*) built from one base note.
   - The owner gives use / use after fixes / reject decisions in random order.
3. **Boundaries.**
   - A rung the owner consistently judges to need fixes before use, or to merit rejection, is on the failing side of the boundary.
   - Natural outputs must also support the proposed boundary. About 8 examples do not by themselves establish calibration sufficiency.
   - No curve fitting unless the observations support it.
4. **Reliability criterion.** It is written into the manifest before calibration. A proposed-binding dimension passes only if both hold:
   - (i) **Decision stability.** On a delayed repeat subset (≥ 7 days; *candidate*), at least 2 items per dimension (*candidate*), no item flips between *use* and *reject*. A move to or from *use after fixes* is tolerated.
   - (ii) **Annotator alignment.** The model annotator's pass/fail call on that dimension's ladder rungs matches the owner's on all but at most one rung (*candidate*).
5. **What alignment shows.** Owner–model agreement measures annotation alignment, not independent human reliability or correctness. Astra–Claude agreement only exposes ambiguous definitions and is not required for binding.
6. **Insufficient support.** If the calibration observations cannot support an acceptance-critical rule, §4.3 applies.

## 7. Confirmation design (owner-bound)

**Albums.** 4 untouched confirmation albums. Together they cover four strata, and one album may cover two:
- a post-model-cutoff release;
- non-English primary sources;
- edition, credit or sample complexity;
- sparse documentation.

**Producer calls.**
- 4 albums × candidate/control × 2 runs × 2 environments = **32 confirmatory calls**. The environments are Claude CLI with WebSearch/WebFetch, and Codex with web search.
- A separate finite preparation budget covers the mapping passes; *candidate*: 2 per album.
- Tool identity and CLI version are recorded per run. A prompt × environment failure is reported as possibly tool-caused.

**Retries.**
- Completion criteria and retry eligibility are frozen before confirmation. There are no automatic retries.
- A harness failure (no inference, or tool unavailability) may be rerun once, with both records kept. A second failure counts as a failed run.
- A permitted retry stays in the completion and cost reporting. It never erases an assessable candidate failure.

**Owner tasks.**
- Every task has the same endpoint: an evidence-backed review outline with unresolved questions recorded.
- Allocation:
  - Freeze two matched album blocks.
  - In each block, randomly allocate one album to candidate-assisted research and the other to the owner's usual research.
  - Allocate one candidate task to each environment before inspecting outputs.
  - Choose which candidate run the owner sees before inspecting its quality.
  - Record matching variables and residual album differences.
- Measurement:
  - D11 covers all owner active work to the endpoint.
  - Collection latency and elapsed availability are recorded separately. Collection work counts in owner burden when it requires the owner.
  - The resulting outlines in both arms are audited against the same adequacy standard.

**Sequence per album.** Mapping passes → frozen top-3 → owner task → owner essentiality labelling (outputs hidden) → amendments → owner audit and adjudication. Nothing about an album's evidence reaches the owner before its task, except the assigned candidate note.

**Audit allocation within about 30–60 h.**
- **Candidate outputs (16).** Each gets full owner verification of central and high-risk claims, with source-location assistance.
- **Control outputs (16).**
  - They get model-triaged gate screening, owner adjudication of flagged items, a predeclared sample, and the §5.5 map-addition screen.
  - Candidate–control comparisons disclose this unequal audit depth and support only conclusions justified by it.
  - Every central and high-risk claim in an output used substantively to establish comparative acceptance must be owner-verified. Otherwise the comparison stays descriptive and cannot establish non-regression or a quality advantage.
- **Budget overrun.** If the hours run out before every candidate output's central and high-risk claims are verified, every alleged gate failure is adjudicated and every proposed map addition is adjudicated, the result is **deferred**. Mandatory checks are never sampled down to fit the budget.
- Actual owner hours are reported per role: map adjudication, task, labelling, audit and calibration.

## 8. Pass pattern

The manifest declares the targeted claim(s) before confirmation: time-saving, quality improvement, or both. Evidence-quality eligibility is reported separately from each benefit verdict.

**Environment-level screen.** The candidate passes the v1 screen in an environment only if all of these hold for that environment's outputs:

1. All 8 candidate outputs in that environment:
   - are complete research notes (§7 harness rule);
   - have no owner-confirmed gate failure, no unresolved gate allegation (§3) and no unresolved central or high-risk claim (§2);
   - meet every binding floor.
2. 0 silent misses among the frozen top-3, across those outputs.
3. 0 factual misdirections attributable to the note in that environment's owner task.
4. *(Benefit claims; see below.)*
5. No post-hoc repair rescues a failed confirmation. A revised version needs new untouched albums, and albums that informed the revision become development material.

**4. Benefit claims.** These are pooled across environments, and each claim is judged separately. They are evaluated only if **both** environments pass the screen, and they are reported for the prompt, not per environment.

- **Comparable usable evidence** is scored by the post-task audit for each block against the same adequacy standard in both arms. The candidate-assisted outline must contain no more adjudicated factual errors overall, and no more errors at or above each frozen severity level, than the paired baseline outline. It must cover at least the same proportion of its album's frozen top-3 essentials and achieve at least the baseline's essential-recall proportion against each album's initial and amended maps. The audit must also establish no consequential loss of usable evidence under comparison rules frozen before confirmation. If the required comparison cannot be assessed sufficiently, the time-saving verdict is deferred.
- **Time-saving.** Comparable usable evidence **and** lower owner active burden (D11) than the paired baseline, in **both** blocks.
  - Reported as "preliminary saving for this owner".
  - "No evidence of net loss" is a separate, weaker observation. It may be reported only if comparable usable evidence holds in **both** blocks and burden is not higher in either block, and it is **never** a time-saving pass.
- **Quality improvement.** A predeclared consequential gain within a predeclared extra-time allowance, in **both** blocks.
- **Verdicts.** Each benefit gets supported, inconclusive, failed, or deferred (when comparable usable evidence cannot be assessed) under frozen rules. Mixed block results are inconclusive. Differences are reported numerically.
- **Confounding.** Each block pairs one environment's candidate task with one baseline task, so environment and album are confounded with block, and the result says so. Neither environment is claimed to have independently shown a repeatable benefit.

**Verdict wording.**
- "Passes v1 for <benefit>": stated only when that declared benefit is supported and the screen passed in both environments.
- "Screen passed; benefit not shown": the screen passed but no declared benefit is supported.
- "Gate screen passed; acceptance deferred": §4.3 applied.
- Anything else is "deferred" or "failed", with reasons.

## Changelog

| Change from `acceptance-v1-draft.md` | Source |
|---|---|
| Central claim redefined by consequence; indicators (a)–(d) not exhaustive; placement cannot make a claim peripheral | Astra R2 §2 + Claude R2 §2 (merged) |
| Removed the "> 25% unassessable → defer" allowance; any unresolved central/high-risk claim defers | Astra R2 §2 (stricter than Claude R2) |
| G2 requires established fabrication; G3 split into G3a/G3b with evidence standard; G9 broadened beyond model memory | Astra R2 §3; G3 split from Claude R2 wording note |
| Preservation requirements for confirmation runs; unresolved-allegation rule | Claude R2 §3 |
| Acceptance-critical vs descriptive classes frozen; acceptance-critical not bindable → "gate screen passed; acceptance deferred" | Astra R2 §4 + Claude R2 §4 (merged). The class assignment in §4 is the drafter's and is subject to round 3. |
| Top-3 frozen before the owner task by model lanes within owner-pre-registered categories; owner labels remaining essentials with outputs hidden; post-exposure additions flagged | Claude R2 §5 for the top-3 (**chosen over** Astra R2 §5's post-task owner top-3 with recorded exposure, as the stricter protection of §8.2); Astra R2 §5 for the hidden-outputs labelling and preserved initial map |
| Symmetric detection screen over control outputs and baseline notes | Claude R2 §5 |
| Frozen scoring manual; ladder boundary semantics; natural outputs must support boundaries; explicit candidate reliability criterion | Astra R2 §6 + Claude R2 §6 (merged) |
| Randomised block allocation; full owner-burden measurement; audit-depth disclosure; budget-overrun deferral; frozen retry eligibility | Astra R2 §7 + Claude R2 §7 (merged) |
| Screen per environment; benefits pooled and only if both screens pass; "comparable usable evidence" defined; "no evidence of net loss" never a time-saving pass; verdict wording | Claude R2 §8 + Astra R2 §8 (merged) |
| Atomic claim may have several sources; D4 reader defined; "imprecise" counted as an error and reported separately; control version named in manifest | wording notes, both |
| Round-1 misattributions corrected (centrality, the unassessable allowance, report-only dimensions, "no net loss" vs saving) | Astra R2 attribution check; Claude R2 §3 |
| Round 3: "high-risk" defined; any unresolved gate allegation defers regardless of centrality; §8.1 aligned with §2; "no evidence of net loss" requires comparable evidence in both blocks | Claude R3 defects A, B and §8.4 distortion (verbatim) |
| Round 3: "comparable usable evidence" strengthened to severity levels, recall against both maps, no consequential loss, deferral if unassessable | Astra R3 (verbatim) |
| Round 3 non-material: §6.1 retitled; §5.2 tie-break and short-union rule; §5.3 post-exposure additions excluded from §8.2 | Astra R3 + Claude R3 wording |
| Round 4 non-material: "deferred" added to benefit verdicts; §6.1 duplicate list items removed | Claude R4 notes |
