# GPT-side proposal: acceptance criteria for a music-research prompt

**Status:** Independent Astra proposal for discussion with Claude and the owner. This is neither a joint standard nor a completed evaluation. Claude's contribution remains pending. The existing 100-point rubric is a provisional GPT-side pilot instrument; its scores do not establish acceptance.

## 1. Define the outcome

Accept a prompt when it reliably gives a critic accurate, consequential, retrievable external evidence with an acceptable combined cost of collecting, reading, and rechecking it. The deliverable is research support, not criticism. The experiment should improve and validate the prompt, not select a winning model.

Order, headings, prose style, tables, claim IDs, length, source counts, and track-by-track presentation are optional mechanisms. Award no points for their presence. Require their underlying functions only when relevant. A concise note can fail through omission; a longer note can succeed if its additional evidence saves meaningful work.

## 2. Establish evidence and denominators

Before scoring, independent reviewers build an album-specific **evidence opportunity map** from sources accessible under the same cutoff and access conditions. Record consequential questions, relevant sources, source dependencies, contradictions, and why each item could change factual understanding or enable a specific listening investigation. Label essential versus supplementary items with reasons before examining candidate outputs. This is a revisable reference map, not an exhaustive truth list or prescribed interpretation.

An item counts as covered only when its relevant substance and scope are correctly extracted. Merely listing a source or a track earns no coverage. Group repeated versions of one fact or interview into one evidence opportunity. Record inaccessible opportunities separately from accessible omissions; honest disclosure of an important gap does not establish research sufficiency.

Audit every central or high-risk claim, including quotations, role aggregates, sample relationships, negative assertions, and claimed access. Audit remaining factual claims exhaustively when feasible; otherwise predefine stratified sampling and disclose its limits. Preserve claim text, evidence location, exact supporting passage, access status, and adjudication. Never label an unaudited claim correct. Report verified, incorrect, unsupported, and unassessable claims against the explicitly audited denominator; unassessable claims remain visible.

## 3. Evaluate six dimensions

| Dimension | Operational test and evidence |
|---|---|
| Relevance and selection | For each substantive information unit, identify the album-specific factual question or concrete listening inquiry it supports. Report useful, redundant, irrelevant, and disputable units against all inspected units. Check that compression preserves necessary qualifications; reviewers must justify relevance rather than invent a critical thesis. |
| Consequential omissions | Measure accurately covered essential opportunities against all accessible essential opportunities in the frozen map. List each missing item and its consequence. Separately assess avoidable search failures, poor extraction from retrieved sources, and unavoidable access gaps. Do not equate metadata coverage with production-context coverage or demand equal attention to every track. |
| Accuracy and traceability | Check whether evidence supports the exact claim, attribution, edition, date, and scope. Have an independent reader recover supporting passages and record success, time, and failures. A functioning URL without supporting content fails this test. |
| Roles and uncertainty | Inspect original role fields, track/edition boundaries, aggregation numerator and denominator, exclusions, and source conflicts wherever used. Assess whether evidence strength matches wording, including negative claims. Properly bounded unknowns are acceptable; pervasive uncertainty that prevents useful conclusions is insufficient. |
| Musical context without substituted criticism | Accept documented production choices, attributed intentions, established relationships, and relevant comparison leads. Verify distinctions among participation, stated influence, samples, interpolation, and resemblance. Flag unsupported listening descriptions, imported critical verdicts, biographical causation, and questions that smuggle in a conclusion. |
| End-to-end efficiency | Measure research elapsed/active time where available, critic reading and retrieval time, correction/rechecking time, and useful evidence actually retained. Count duplication across the entire deliverable. Report quality alongside time; speed cannot compensate for misinformation or essential omissions. Keep tool failures and provider-specific token accounting separate. |

## 4. Gates and minimum standards

Proposed integrity gates: fabricated evidence or quotations; false direct-access/listening claims; materially misleading central claims presented as established; or unsupported role/sample conclusions carrying the note's argument. Inspect appendices too. A gate failure requires repair and a fresh validation, not compensation through other dimensions.

Use a minimum standard for **every** dimension rather than a compensating weighted total. GPT and Claude should independently propose behaviorally anchored pass/borderline/fail examples, then reconcile disagreements against sources and the critic's needs. Calibrate numerical tolerances, if useful, from blinded pilot evidence and actual user costs. No numerical acceptance line is agreed here. Insufficient verification yields **unassessable**, never an automatic pass.

## 5. Selection, stopping, and validation

Prioritize searches by expected reduction of consequential uncertainty. Stop a branch when remaining plausible retrieval routes have low expected value relative to their cost; preserve unresolved consequential gaps with a practical next step. Search counts alone do not demonstrate saturation. Test stopping decisions against missed accessible evidence and wasted effort in traces.

Freeze prompt, criteria, minimum standards, evidence-map procedure, audit sampling, budgets, and failure handling before confirmatory runs. Log amendments; use changed criteria prospectively and re-evaluate comparable outputs consistently. Preserve initial verdicts. Do not tune thresholds to rescue a favored sample.

Revise on development albums, then validate on untouched albums differing in documentation richness, language, genre, age, collaboration, and credit/sample complexity. Include repeated runs and both intended provider environments; predeclare the required pass pattern and permissible failures jointly. Once an album informs revision, it is no longer a clean holdout.

Finally, require human critic testing: observe whether the note supplies useful evidence, reduces total research/rechecking effort versus their usual process, avoids factual misdirection, and leaves interpretation to them. Simulated judges cannot certify this outcome. Advance only after agreed cross-reviewer standards and human-use evidence are satisfied.

Candidate finite confirmation: three untouched albums, candidate and control prompts, two runs per prompt in each provider environment: 24 calls, with a fixed time cap and no automatic retries. Freeze after development. This small panel tests failures, not universal reliability. Tradeoffs: reference maps can miss novel discoveries; credit supported additions. Exhaustive auditing can itself erase efficiency gains.
