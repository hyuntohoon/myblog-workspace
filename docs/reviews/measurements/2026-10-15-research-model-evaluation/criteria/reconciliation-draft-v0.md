# Acceptance criteria — reconciliation draft v0 (not frozen)

- Date: 2026-10-16.
- Inputs: `astra-proposal.md` (sha256 `55a39c29…`, GPT-6 Astra, 2026-10-15) and `claude-proposal.md` (sha256 `e2058961…`, `claude-opus-5-5`, 2026-10-16, run `claude-run/claude-opus-5-5-criteria/`, 0 web requests). Both received the identical `common-brief.txt` (sha256 `7a6c7cc3…`), the frozen pilot prompt and the pilot rubric; neither saw the other's proposal, producer outputs or scores.
- Drafted by the orchestrating session (`claude-opus-5-5`). **Disclosure:** the drafter shares a model family with one contributor. This draft is therefore not a resolution. Each row goes back to both contributors for objection (round 1) before anything is frozen. A row marked *owner* depends on resources only the owner can commit.
- Nothing here is `acceptance-v1`. No numeric value below is agreed.

## A. Points both proposals already share

| # | Rule | Astra | Claude |
|---|---|---|---|
| A1 | The audit unit is the atomic, material claim, with its source location and an adjudication. Unaudited claims are never counted as correct. | §2 | §1, §2.2 |
| A2 | "Unassessable/unverifiable" is a separate visible status, outside the precision numerator and denominator. Insufficient verification yields *unassessable/deferred*, never a pass. | §2, §4 | §2.2 |
| A3 | Every central or high-risk claim is audited; the rest is audited exhaustively or by a predeclared stratified sample whose limits are reported. | §2 | §2.2 |
| A4 | Integrity failures (fabricated source/quote, false access or listening claim, central falsehood presented as established, unsupported role/sample aggregate carrying the argument) are noncompensable; appendices are inspected too. | §4 | §3 G2–G5, G7 |
| A5 | No weighted total decides acceptance. Every dimension needs its own minimum. | §4 | §0.2 (composite only as a tie-break) |
| A6 | Template features (caps, headings, track tables, IDs, length, source count) earn no credit; breaking a cap is not a failure by itself. | §1 | §0.5, §3 "not gates" |
| A7 | A disclosed important gap is not equivalent to a fabrication, but it does not prove sufficiency either. | §2 | §2.7, §3 |
| A8 | Omission is measured against accessible essential items only; inaccessible ones are reported apart; covered means substance and scope correctly extracted, not a listed link. | §2, §3 | §2.7 |
| A9 | Collection cost and critic cost (reading, re-verification, correction) are reported beside quality and never folded into it; speed cannot offset misinformation. | §3 | §0.4, §2.11–2.12 |
| A10 | Stopping is judged on the yield of searches, not on a search count. | §5 | §2.11 |
| A11 | Prompt, criteria, floors, audit sampling and budgets are frozen before confirmatory runs; an album used for tuning is no longer a holdout; changes create a new version. | §5 | §4.6 |
| A12 | Simulated judges cannot certify usefulness; actual critic use is required. | §5 | §5 |

## B. Differences to resolve in round 1

| # | Question | Astra | Claude | Draft proposal | Status |
|---|---|---|---|---|---|
| B1 | How is the essential-item reference built? | Evidence-opportunity map built **before** seeing outputs; revisable. | Two blind researchers build a list, then **pooled** with items found by any note, adjudicated afterwards (TREC-style). | Freeze a pre-output map first. Pooled discoveries are adjudicated and reported as *unique contributions*, but the gating recall denominator is the pre-frozen accessible essentials. | open |
| B2 | Gate list | 4 gates. | G1–G9 (adds wrong target, prompt-injection compliance, unsourced model memory labelled verified, central absence inference). | Union of both. G6/G7/G9 gate only when the claim is central; peripheral occurrences are defects. | open |
| B3 | Floors: numbers now, or anchored examples first? | No numeric line; behaviourally anchored pass/borderline/fail examples, numbers only if calibrated. | Candidate numbers (trace ≥ 0.9, precision ≥ 0.95, overclaim ≤ 0.05, aggregate disclosure = 1.0, 0 silent misses in top-3 essentials, essential recall ≥ 0.7, useful share ≥ 0.6, unverifiable central ≤ 0.25 → defer). | Use Claude's numbers only as a starting hypothesis for calibration, together with Astra's anchored examples. No number binds until calibrated (B4). | open |
| B4 | Calibration method | Calibrate from blinded pilot evidence and actual user costs. | Perturbed-note set with known defects, blind critic accept/fix/reject decisions, floor at the rejection knee; a floor binds only when inter-rater α ≥ 0.67. | Perturbation set plus the critic's decisions. With two model reviewers, Astra–Claude agreement per dimension is the α measured; a dimension below it is redefined, not gated. | open |
| B5 | Baseline condition | Implicit ("versus their usual process"). | Explicit: cheap baseline packet and/or the critic's own search time T₀; acceptance requires positive net time saving. | Explicit baseline required. | open |
| B6 | Gate adjudication | Not specified. | Human adjudication for gate decisions; LLM triage only for locating passages. | Human (owner) confirms every gate failure and every gate *pass* on central claims of the final candidate. | owner |
| B7 | Validation size | 3 untouched albums × candidate/control × 2 runs × 2 provider environments = 24 calls. | 12 held-out + 4 calibration albums, ≥ 3 runs per condition, baseline arm, 4–6 critics in a Latin square. | See §C — this is bounded by resources, not by argument. | owner |
| B8 | Reception and other critics' writing | "Imported critical verdicts" are a defect. | Opt-in, separately labelled reception section; anything from it is at best "relayed". | Keep verdicts out of findings (both). Whether an opt-in reception section exists is a prompt-design question for Stage B, tested by the critic task. | open |
| B9 | Translation fidelity | Not addressed. | Central translated quotes need an original-language excerpt. | Adopt as a traceability requirement. | open |
| B10 | Run snapshots | "Independent reader recovers the passage." | Harness must store retrieved-page snapshots/hashes so a later 404 is not mistaken for fabrication. | Adopt as a harness requirement for every new round. | open |
| B11 | Status-label taxonomy | Not addressed. | 30-combination taxonomy too fine; critic-facing body uses 3 levels. | A prompt-design item for Stage B, not an acceptance criterion; the criterion is the overclaim rate (Claude §2.5). | open |
| B12 | Musical-context usefulness | Relevance test per unit; flag smuggled conclusions. | Typed items, 0–2 critic rating, checkable reason for comparisons. | Combine: typed items + checkable reason required; usefulness rated by the critic. | open |

## C. What depends on the owner

Claude's design assumes 4–6 critics; the project has **one** critic, the owner. Astra's design leaves the number of critics open. Every human-use number below is therefore an owner commitment, not a reviewer preference.

| Item | Why it matters | Options to decide |
|---|---|---|
| Human critic time | Calibration (B4), gate adjudication (B6) and the critic task (A12) all need it. Claude estimates 1–3 h per note for claim checking. | How many hours the owner can give per round. |
| Holdout panel size | Small panels test failures, not reliability. | (a) Astra-sized: 3 holdouts. (b) Middle: 2 calibration + 4 holdouts. (c) Claude-sized: 4 + 12. |
| Runs and providers | Subscription quota; this session itself showed the Claude lane can hit the session limit. | 1 vs 2 provider environments; 2 vs 3 runs per condition. |
| Baseline arm | Needed for net time saving (B5). | Owner's own search time on a holdout album, or a cheap fixed packet. |

## D. Round-1 procedure

1. Send this draft plus **both** proposals (now that both are preserved) to the same two contributors, in fresh contexts, with the same instruction: for each B row, accept, amend or object with a reason. For §C, say what minimum is needed for the claim each option would support.
2. Preserve both responses verbatim. Material disagreements stay open; they are not averaged.
3. Then the owner settles §C, and `acceptance-v1` is frozen with every row's resolution recorded.
