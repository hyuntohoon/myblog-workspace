# Research-note acceptance design — joint GPT / Claude draft

- Owner direction: 2026-10-15.
- Parent: `docs/rfcs/CHORE-research-model-evaluation.md` (first planned priority).
- Status: criteria design pending both proposals and reconciliation; no final pass threshold.
- Historical pilot: `docs/reviews/measurements/2026-10-15-research-model-evaluation/`.

## Common independent-review brief

Design acceptance criteria for a prompt that efficiently collects reliable evidence useful to a music critic before writing a review. The deliverable is research, not the review itself. Structure, outline, headings and wording may change. Judge useful information and its acquisition/use costs; do not reward compliance with the current template.

Propose observable definitions and evidence for relevance, significant omissions, factual accuracy, attribution, source traceability, edition/credit precision, musical context, uncertainty, information selection and stopping. Include the critic's reading and reverification burden alongside collection time/tool effort. Explain denominators and unavailable-data handling. Explain which failures cannot be compensated by a high total, how dimension floors and thresholds should be calibrated, and how unseen albums and real critic tasks should validate usefulness. Challenge unnecessary requirements as well as missing ones.

Return: proposed dimensions with metrics; noncompensable failures; a threshold-calibration method; a finite validation design; the most important tradeoffs/objections. Identify numeric proposals as candidates, not agreed thresholds. Do not infer the other reviewer's opinion or preferred model. Do not rank producer models during criteria design.

Both reviewers may inspect the same historical frozen prompt and pilot rubric to identify design weaknesses. The pilot rubric is an earlier GPT-side proposal, not authority and not a joint agreement. Neither receives the other's proposal until both are preserved. GPT contributor: exactly GPT-6 Astra. Claude contributor: the subscription-included reviewer already pinned in the pilot protocol. Account limits delay the contribution; silence is not agreement.

## Questions the joint contract must resolve

| Decision | Required definition/evidence |
|---|---|
| What information matters? | Album-specific evidence needs set independently of a candidate's preferred narrative; examples of high-value facts, material gaps and low-value digressions. Permit relevant discoveries beyond a reference set. |
| Is a claim supported? | Atomic, material claims; speaker and certainty scope; source location, edition and role. Separate unsupported, contradicted, inaccessible and not assessed. State audited/eligible counts and sampling method. |
| What was omitted? | Finite reference evidence needs with documented search/access conditions and importance, not an imaginary exhaustive set of all album facts. Separate failure to search, extract and select. |
| Can a critic use it? | Locate and verify important evidence, connect documented context to listening questions, and identify unresolved issues without inheriting a prescribed thesis. Actual critic tasks measured separately from AI opinion. |
| Is collection efficient? | Useful, supported, nonduplicate evidence yield alongside collection time/search effort and critic reading/reverification time. Report raw numerators, denominators and unavailable observations; avoid a misleading single cost ratio. |
| When should research stop? | Required evidence needs checked, known gaps scoped, and successive searches yielding no material new evidence under a declared finite budget. A search failure alone does not prove absence. |
| Is coverage distorted? | Track/release scope reconciled; explain single/track concentration without forcing one fact per song. Distinguish meaningful production evidence from a promotional mention. |
| What constitutes passage? | Noncompensable failures plus dimension minimums and any aggregate threshold, calibrated before confirmation; treatment of reviewer disagreement and uncertain evidence. |

No weights or pass numbers in this document are agreed. A target such as “90/100” would be arbitrary until its measurement and error tolerance are justified. Source count, character count, track count and runtime are diagnostic observations, not substitutes for usefulness.

## Agreement and version control

1. Preserve each independent proposal verbatim with model, date, input hash and access limitations. Reviewers receive this identical brief; note any historical context already seen.
2. Reconcile into a decision table: criterion, Astra proposal, Claude proposal, evidence, adopted rule/threshold and unresolved objection. Do not use a simple vote or average to erase a factual disagreement.
3. Freeze `acceptance-v1` before confirmatory outputs are evaluated. Include definitions, audit sampling, exclusions, hard failures, dimension floors, thresholds and reviewer confidence rules. Both reviewers assess every required dimension.
4. Freeze the bounded round manifest before generation. Changes discovered later create a new contract version and a new test; retain prior results and label any retrospective reanalysis explicitly.
5. Preserve pilot scores under their original rubric. They diagnose defects; they do not prove a final criterion passed. Complete the historical cross-family pilot without replacing existing GPT runs.

## Bounded validation manifest requirements

- Question: prompt change, model comparison or operational viability; separate these contrasts.
- Candidate/control prompt bytes and hashes; model ID, effort, harness, source cutoff and album/edition IDs.
- Finite album panel, calls per condition, total dispatch/time limits and stopping rules, frozen before running. Do not rerun every model for every wording change.
- Development albums and untouched holdouts identified before tuning. *Gemini Rights* is development material. A holdout used to improve the prompt becomes development material.
- Panel rationale: source availability, language and credit/sample complexity; no single-album generalisation claim.
- Equal usable input and comparable access conditions; log provider differences, date drift, quota and inaccessible sources rather than scoring them as the same outcome.
- Independent blind Astra/Claude evaluation, common evidence packet, reference-set provenance and unresolved disputes.
- Real critic tasks, observed completion/correction burden, reading and verification time; any simulated task labelled as such. Calibrate useful thresholds against actual tolerance, not fluency alone.
- No fabricated quote/source/access, material false attribution or unsupported central assertion accepted through score compensation. Exact severity rules remain subject to joint definition.
- All required dimensions/holdouts pass under the frozen rules before declaring completion; report failures and remaining uncertainty even when a candidate ranks first.

## Current contribution record

| Contributor / item | State |
|---|---|
| Astra proposal | Received independently from GPT-6 Astra; `docs/reviews/measurements/2026-10-15-research-model-evaluation/criteria/astra-proposal.md`. Common brief checked; no Claude opinion seen. Candidate numbers/designs are unagreed and no extra generation is dispatched. |
| Claude proposal | Pending account access; not yet received. |
| Joint reconciliation / acceptance-v1 | Pending both independent contributions. |
| Critic-use observation / held-out validation | Not performed. |

A successful outcome is a tested prompt and its operating conditions with useful evidence at an acceptable total effort. An attractive template, the top model in the pilot, or a long list of further research is insufficient.
