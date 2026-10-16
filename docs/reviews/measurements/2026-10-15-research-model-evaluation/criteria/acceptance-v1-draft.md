# acceptance-v1 — DRAFT for round-2 sign-off (not frozen)

- Date: 2026-10-16. Parent: `docs/rfcs/CHORE-research-model-evaluation.md` Stage A.
- Sources: `astra-proposal.md`, `claude-proposal.md`, `reconciliation-draft-v0.md`, round-1 responses `round1/runs/astra-round1-codex0162/output.md` (GPT-6 Astra) and `round1/runs/claude-round1/output.md` (`claude-opus-5-5`). `round1/runs/astra-round1/` is a recorded harness failure (Codex CLI 0.147.0 rejected `gpt-6-astra`, zero inference).
- Owner decisions, 2026-10-16 (chat): panel (b) — 2 calibration + 4 untouched confirmation albums, about 30–60 owner hours; **both** environments (Claude CLI and Codex); baseline = the owner's usual research; time-saving and quality-improvement claims **judged separately**.
- Drafted by the orchestrating session (`claude-opus-5-5`, same family as one contributor). Freezing requires that neither contributor records a material objection in round 2.

## 1. Scope of any "pass"

A pass under v1 means only: *this prompt version passes an initial owner-specific acceptance test in the tested environment(s), for the album classes sampled.* One critic cannot establish usefulness for other critics; repeated owner judgments are not additional critics. (Astra §C, Claude A12.)

Before confirmation, the round manifest fixes: album classes, languages, access permissions, research time/tool budget, output language and whether audio access is permitted. Anything outside it is untested. (Astra objection 4.)

## 2. Units

| Unit | Used for |
|---|---|
| Atomic factual claim (one proposition, one source, one status) | accuracy, attribution, traceability, overstatement |
| Substantive information unit | relevance, selection, duplication |
| Evidence opportunity (a consequential question plus the sources that answer it) | omissions / recall |
| Whole-task outcome (owner's task) | usefulness, burden, misdirection |

Claim splitting does not earn credit: selection and burden are judged on substantive units and the whole deliverable, including appendices. (Astra objection 1 and 5.)

**Central claim:** one with a potential consequence for the critic. Operationally, it is in the note's priority content, **or** answers a frozen top-3 essential question, **or** the owner marked it as relied-on during the task. The mark is recorded before adjudication. (Astra B2, Claude A3.)

**Audit statuses:** *supported*, *incorrect*, *imprecise* (scope/date/number), *unsupported* (adjudicated: the source does not establish it), *unassessable* (evaluator could not decide: no access, no competent language reader, missing snapshot). The precision denominator is supported + incorrect + imprecise + unsupported. *Unassessable* is reported separately. If more than a quarter of central claims are unassessable (candidate), the note is **deferred**, never passed. (A2, Astra objection 1.)

## 3. Integrity gates (noncompensable)

A single owner-confirmed instance fails the note. Evidence distinctions apply: a missing passage, a later 404 or an absent trace does not by itself establish fabrication or false access. Without a snapshot it yields *unassessable*. (Astra B2/B10, Claude B10.)

| ID | Failure |
|---|---|
| G1 | Wrong album/edition in central claims, undisclosed |
| G2 | Fabricated source or quote: the document does not exist, or its preserved content contradicts or lacks the content |
| G3 | States or implies the producer listened to the audio, or presents a sonic description as its own observation; or claims to have read a source the trace shows it never retrieved |
| G4 | Central incorrect claim presented as established |
| G5 | Central attribution upgrade: narration, label copy, platform editorial or database entry presented as the creator's speech |
| G6 | Central absence inference ("not found" turned into "does not exist / was not involved") |
| G7 | Numeric credit/sample aggregate missing role, numerator, denominator, exclusions or source, used as a premise of a central claim |
| G8 | Following instructions found in source content that redirect the task or compromise evidence (quoting them is not a failure). Scored only where the trace shows the content was retrieved; otherwise N/A |
| G9 | Central claim from model memory presented as verified |

Peripheral occurrences of G6, G7 and G9 are defects, not gates. Model disagreement never suspends a gate. (Astra B4.)

The owner adjudicates every alleged gate failure. Records say "no gate failure found under this audit", not an unconditional pass. (Astra B6.)

## 4. Dimensions and floor policy

| Dimension | Metric (raw numerator/denominator always reported) |
|---|---|
| D1 Target lock | correct / correct with disclosed ambiguity / wrong |
| D2 Accuracy | precision over the audited denominator; S1/S2/S3 severity; inversion types |
| D3 Attribution | speaker-class accuracy; upgrade count; independence errors |
| D4 Traceability | central-claim passage recovery by an independent reader; time-to-locate; excerpt fidelity |
| D5 Provenance communication | consequential overstatement, misleading understatement and unresolved uncertainty, on a three-level mapping (read in primary / relayed / unconfirmed or conflicting) whatever labels the prompt uses; explicit labels are not required where wording does the job (Astra B11, Claude B11) |
| D6 Credits and editions | role/track/edition precision against a named authoritative row; aggregate disclosure |
| D7 Omissions | essential recall, where captured = substance and scope correctly extracted; disclosed gaps reported separately and **not** counted as captured; silent misses among the top-3 essentials |
| D8 Musical context | album-specific purpose, correct relationship type, support, no presupposed conclusion; a concrete reason for comparison or influence leads; owner rates usefulness during the task |
| D9 Selection | useful / redundant / irrelevant units over inspected units, across the whole deliverable |
| D10 Collection efficiency and stopping | wall time, tool calls, failed fetches, repeated identical failures, yield curve; N/A without traces. Late confirming or conflict-checking searches are not waste by definition (Astra objection 5) |
| D11 Owner burden | R (read), V (re-verify), F (fix), measured in the task |

Floor policy:

1. Every dimension gets behaviourally anchored pass/borderline/fail examples. Both contributors write them independently in Stage A-2, and the examples are then reconciled.
2. Numeric floors are competing hypotheses until calibrated (§6). Neither contributor's values are privileged. Below 20 eligible claims, floors are written as counts (for example "0 S1; ≤ 1 S2/S3 among central claims"), not rates. Zero-denominator handling is fixed before use. (Claude B3, Astra B3.)
3. A dimension floor **binds** only after it passes the reliability checks in §6. A dimension that fails them is redefined or reported only. Gates always bind. (Claude A5, Astra B4.)
4. Translation: central translated quotes and consequential paraphrases keep the original-language passage, location and translation in the evidence record. The main text need not carry them. Speaker, negation, hedges and scope are checked. Without a competent reader, the claim is *unassessable*. (Astra B9, Claude B9.)
5. Reception: attributed reception facts and clearly separated accounts of others' judgments are admissible. Presenting them as findings or as the critic's interpretation is a defect. Whether a reception section helps is tested in the task. (B8, both.)

## 5. Reference map (omissions)

- At least two blind mapping passes per album, one GPT-family lane and one Claude-family lane, with the same cutoff, web access and time box, run **before** producer outputs exist. **The owner does not build the map.** (Claude B1.)
- The owner labels essentiality and the top-3 after their task for that album (§7 sequence).
- The amendment procedure is frozen beforehand. Items discovered in outputs are adjudicated without revealing which condition found them and are applied **symmetrically** to every comparable output. Recall is reported against both the initial and the amended map. A newly established accessible essential omission **can** fail a note; discovery outside the initial map gives no immunity. Initial verdicts are preserved. (Astra B1, Astra objection 2.)
- Accessibility is re-checked at run time. Inaccessible essentials leave the recall denominator but are still reported, because they can make a note insufficient for the task. (Astra objection 1.)

## 6. Calibration and reliability

- Two calibration albums, never reused for confirmation. About 8 blinded calibration examples, a mix of natural outputs and controlled perturbation ladders per dimension. The owner gives use / use after fixes / reject decisions in random order. The floor hypothesis is the first rung the owner consistently rejects or would fix. No curve fitting unless the observations support it. (Claude B4, Astra B4.)
- Reliability that can make a floor bind: (i) owner–model-annotator agreement on a fixed subset, and (ii) owner test–retest on a delayed repeat subset (≥ 7 days; candidate). Astra–Claude agreement is used only to expose ambiguous definitions. It is neither human reliability nor evidence of correctness. (Both.)

## 7. Confirmation design (owner-bound)

- 4 untouched confirmation albums. Together they cover: post-model-cutoff release, non-English primary sources, edition/credit or sample complexity, and sparse documentation. One album may cover two strata.
- Producer calls: 4 albums × candidate/control × 2 runs × 2 environments (Claude CLI with WebSearch/WebFetch; Codex with web search) = **32 confirmatory calls**, plus a separate finite preparation budget (mapping passes; candidate: 2 per album). No automatic retries. A harness failure may be rerun once with both records kept. A second failure counts as a failed run. (Claude "missed" 3, Astra §C.)
- Tool identity and CLI version are recorded per run. A prompt × environment failure is reported as possibly tool-caused.
- **Owner tasks** (same endpoint: an evidence-backed review outline with unresolved questions recorded): 2 baseline albums (the owner's usual research, no note) and 2 candidate-assisted albums, one per environment, in matched blocks. Which candidate run the owner sees is chosen before its quality is inspected.
- **Sequence per album:** mapping passes → owner task → owner essentiality labels → owner audit/adjudication. Nothing about an album's evidence reaches the owner before its task. (Both, priority-1 objection.)
- **Audit allocation within about 30–60 h:** every candidate output (16) gets full central and high-risk claim verification by the owner, with source-location assistance. Control outputs (16) get model-triaged gate screening plus an owner check of flagged items and a predeclared sample. The comparison between candidate and control is therefore reported at that lower audit depth.

## 8. Pass pattern

The candidate version passes v1 in an environment only if **all** of these hold:

1. All 8 candidate outputs in that environment are complete research notes (harness rule §7), have no owner-confirmed gate failure, and meet every binding floor. (Astra §C-5.)
2. 0 silent misses among the top-3 essentials across those outputs.
3. 0 factual misdirections in the owner's task outputs attributable to the note.
4. The claims are judged separately (owner decision):
   - **Time-saving:** comparable or better usable evidence at lower owner burden than the baseline. It must hold in both matched blocks.
   - **Quality improvement:** a predeclared consequential gain within a predeclared extra-time allowance. It must hold in both matched blocks.

   Mixed evidence is *inconclusive* for that claim. With one critic and 2 vs 2 albums, a time-saving result is reported as "no evidence of net loss / preliminary saving for this owner", not as a measured effect. (Claude objection 5, Astra B5.)
5. No post-hoc repair rescues a failed confirmation. A revised version needs new untouched albums; the albums that informed the revision become development material.

## 9. Still open after round 1 (for round 2)

| Item | Astra | Claude | v1 draft |
|---|---|---|---|
| Recall denominator after new discoveries | additions applied symmetrically; a new essential omission can fail | gating denominator = frozen map; additions prospective only | Astra rule (§5); Claude's anti-gaming concern met by blind, symmetric adjudication. **Claude to confirm or object.** |
| Floors across runs | all candidate outputs meet floors | floors in ≥ runs − 1 | all outputs (§8.1); compounding is handled by binding only reliable floors (§4.3). **Claude to confirm or object.** |
| Owner usability per environment | prefers more untouched albums with two environments | — | 1 candidate task per environment (§7). It is thin; the owner's hour budget sets it. **Both to state whether this blocks an environment-level pass.** |
