# Anchors v1 — release candidate (Stage A-2, acceptance-v1 §4.1)

- Status: **release candidate**. It is frozen only after both contributors' diff check (`round2/`).
- Date: 2026-10-16. Contract: `../acceptance-v1.md` (sha256 `605b72a0…`). Nothing here changes it.
- Inputs: two anchor sets written independently in fresh contexts from the same brief (`brief.txt`; combined prompt sha256 `6c6f8528…`). Neither contributor saw the other's set.
  - `runs/astra-anchors/output.md`: GPT-6 Astra, Codex CLI 0.162.0-alpha.17.2, 198 s.
  - `runs/claude-anchors/output.md`: `claude-opus-5-5`, Claude CLI, 267 s, 0 web requests.
- Reconciled by the orchestrating session (`claude-opus-5-5`, the same family as one contributor). The rule is the one used for acceptance-v1: keep both texts, and where they place a behaviour at different levels, adopt the stricter placement and record it.

## 1. What the anchor set is

The anchor set is **both contributors' exemplar files, verbatim**, plus §2–§4 of this document. A file is cited as `A` (Astra) or `C` (Claude), with dimension and level. For example, `C-D4-FAIL` is Claude's D4 FAIL anchor.

- Each dimension therefore has two exemplars per level, built on different fictional albums: Astra's *Glass Orchard* and Claude's *Tidewater Ledger*. Two exemplars per level give calibration more than one picture of each boundary. Neither file is privileged.
- §2 below is the reconciled boundary for each dimension. Where an exemplar and §2 disagree, §2 wins, and §3 lists every such case.
- The levels are illustrations for §6 calibration. They are not floors, not whole-note verdicts and not gate rulings. Integrity gates (§3 of the contract) are always judged separately and bind regardless of any dimension level.

## 2. Reconciled boundaries

| Dim | PASS | BORDERLINE | FAIL | Adjacent gate (what turns the FAIL into the gate) |
|---|---|---|---|---|
| D1 Target lock | Every central claim is attributable to the target object. Any other edition's material is marked at claim level, and the edition wording is unambiguous. | The target is correct, but either the disclosure is at note level only (C), or claims are attached to the target while its labels remain unclear (A). | A disclosed wrong target (A, C). | G1: the wrong object is used in central claims and not disclosed. |
| D2 Accuracy | The audit supports the central claims. At most incidental imprecision remains, reported in the imprecise share. | Errors are confined to non-central claims: an incidental imprecise date (A), or peripheral temporal or scope inversions (C). | Several peripheral errors (A), or a central incorrect claim that is hedged rather than presented as established (C). | G4: a central incorrect claim presented as established. |
| D3 Attribution | Speaker class is correct per sentence, and relays of one source are counted as one. | No upgrade, but a speaker class cannot be recovered from the note (C), or source independence is left unclear (A). | A peripheral narration→speech upgrade, or a claim of independent corroboration from relays (A, C). | G5: the upgrade carries a central claim. |
| D4 Traceability | A non-producer reader recovers each central passage quickly, and the excerpt is faithful. | Recovery succeeds only after scanning a long source, or fidelity is imperfect but meaning is kept. | Central claims cannot be mapped to a passage (A: bibliography only), or a quoted passage cannot be recovered (C). | G2: only if invention is *established*. Non-recovery alone is unsupported, incorrect or unassessable. |
| D5 Provenance communication | Wording makes primary / relayed / unconfirmed or conflicting clear per claim. | An access route is overstated without consequence (C: snippet read as primary), or a status is unexplained (A). | A consequential overstatement or understatement, or an uncertainty silently resolved (A, C). | G9 if a central *unsupported* claim is shown as verified; G3b if the note falsely says it read a source. |
| D6 Credits and editions | Original role strings, tracks and edition are given against a named authoritative row, and every aggregate discloses role, numerator, denominator, exclusions and source. | Exact rows are available, but a summary normalises a role (A, C) or an aggregate is incompletely disclosed while not being a central premise (C). | Credits are not anchored to an accessible authoritative row: role narrowing, wrong-edition tracks (C), or only unverified guesses (A). | G7: an undisclosed aggregate is a premise of a central claim. G4: a role adjudicated *incorrect* is presented as established. |
| D7 Omissions | Every essential is captured with correct substance and scope, and gaps are disclosed separately. | An essential that was accessible is disclosed as a gap, not captured (A, C). | A silent miss of an accessible essential, or a capture with the wrong scope (C). | G6: the note turns not-found into "does not exist / was not involved" in a central claim. |
| D8 Musical context *(descriptive)* | Album-specific, supported, with the correct relationship type, a concrete reason, and the conclusion left to the critic. | Support is sound but the comparison lacks a reason (A), or the relationship type is overstated or the wording leans toward a conclusion (C). | The critic's conclusion is presupposed, or the context is unsupported (A, C). | G3a: a sonic description given as the note's own observation. |
| D9 Selection *(descriptive)* | Each substantive unit serves research or verification. The appendix does not restate the body. | Useful content is intact, but there is skippable redundancy or an irrelevant paragraph. | Redundant or irrelevant units are a large share of the whole deliverable. | — |
| D10 Collection and stopping *(descriptive, trace)* | Yield rises, failures are switched away from, and late checks resolve conflicts. | Some identical retries or a flat tail, but collection progresses. | Repeated identical failures and no stopping point once yield is flat. | G8: following instructions found in retrieved content. |
| D11 Owner burden *(descriptive, task record)* | Active work is mainly reading and light verification, with small correction and completion work. | Work saved in searching is spent on locating and repair (A), or some sections need re-derivation (C). | Active work is dominated by reconstruction, independent research and correction. | — (a factual misdirection is §8.3) |

## 3. Reconciliation decisions

| # | Point | A | C | Decision |
|---|---|---|---|---|
| R1 | D1: where "correct with disclosed ambiguity" falls | Terminology left unclear, with claims attached to the target → BORDERLINE (`A-D1-BORDERLINE`) | Ambiguity resolved per claim → PASS (`C-D1-PASS`) | **Both stand.** The rule is §2: PASS needs claim-level attribution *and* unambiguous edition wording. This is the stricter of the two readings, so Astra's terminology case stays BORDERLINE. |
| R2 | D11 and the paired baseline | Levels are phrased against the baseline (`A-D11-PASS`, `-FAIL`) | Levels describe the composition of the work; the comparison is §8 (`C-D11` note) | **C's framing.** The contract makes D11 descriptive here and used by §8. The baseline clauses in `A-D11-PASS` and `A-D11-FAIL` are read as context, not as the level criterion. The A exemplars keep their levels on composition alone, because both describe the same composition pattern. |
| R3 | D6 FAIL scope | Only unverified credit guesses with accessible rows (`A-D6-FAIL`) | Single encyclopedia, role narrowing, deluxe track counted (`C-D6-FAIL`) | **Both stand** as two FAIL routes. A's is the narrower one, and A flags it as one to test in calibration. |
| R4 | D2 FAIL | Peripheral errors only | Includes a hedged central incorrect claim | **Both stand.** Both are FAIL under §2. C's is the one next to G4. |
| R5 | D4 FAIL with an unrecoverable quote (`C-D4-FAIL`) | — | Traceability fail; not G2 | **Stands, with a note.** The same quote is also audited under D2 as *unsupported* or *unassessable*. Scoring it in both is allowed, because the dimensions measure different things. |

## 4. Open items for the scoring manual (§6.1)

The contributors raised these as contract friction. They are **not contract changes**. The scoring manual is frozen before calibration (contract §6.1), and each item needs a frozen rule there. The proposals are the orchestrator's, offered for the diff check.

| # | Raised by | Item | Proposed scoring-manual rule |
|---|---|---|---|
| M1 | C friction 2 | D5: which of the three levels a search snippet or a model-processed fetch summary belongs to | **Relayed**, unless the excerpt is checked against the harness capture of that URL. It follows the stricter reading, and it matches the pilot evidence that summarised fetches reversed attributions. |
| M2 | C friction 3 | G4 versus a central *imprecise* claim presented as established | The owner decides whether the imprecision changes the truth of the proposition *as it is used* in the central claim. If it does, the claim is adjudicated *incorrect* and G4 applies. If it does not, the claim stays *imprecise* under D2 or D6. The ruling is recorded per claim. |
| M3 | C friction 4; A friction 3 | S1/S2/S3 definitions | Written in the scoring manual. The anchors deliberately assign no severity. |
| M4 | A friction 1–2; C D8 and D11 notes | Applicability preconditions | D7 needs the preserved initial and amended maps and the frozen top-3. D8 usefulness needs the owner's in-task rating. D11 needs the full task record. D10 without traces is N/A. Without its precondition a dimension is reported as *not assessable*, never as FAIL. |
| M5 | C friction 1 | D1 levels | Resolved by R1 and §2. Listed here only so the manual states it. |

## 5. Not part of this document

- Numeric floors and zero-denominator rules: they are frozen in the round manifest after §6 calibration (contract §4.3).
- The round manifest: `../round-manifest-v1.md`.
