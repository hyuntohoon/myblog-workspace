# Round-1 response: Claude contributor (`claude-opus-5-5`)

**Status:** This is a round-1 review of reconciliation draft v0. I used no web tools, researched no album and looked at no producer outputs. Every number here is a candidate. The drafter comes from my own model family, so I checked closely wherever the draft adopted my proposal. Several of my original positions don't work with one critic, and I concede them below.

---

## 1. Verdicts on B1–B12

| # | Verdict | Exact replacement rule / reason |
|---|---|---|
| **B1** Reference build | **AMEND** | "Before any producer output is generated, at least two independent mapping passes build the evidence-opportunity map for each album. One pass comes from a GPT-family lane and one from a Claude-family lane, each with web access, the same cutoff and a fixed time box. **The owner does not build the map** (see Objection 1). The owner merges the passes and labels each item *essential / supplementary* with a one-line reason. The owner also marks the **top-3 essentials**. All of this happens before the owner sees any output, and the map is then hashed. At run time, each essential item is re-checked for accessibility, and inaccessible items leave the gating denominator. **The gating recall denominator is the frozen, accessible essentials only.** Items that notes find later are adjudicated by the owner and reported as *unique contributions* and as a secondary 'pooled recall'. They never enter the gating denominator in the current round. They may be added to maps prospectively, for the next version only." *Reason:* a pre-frozen denominator stops consensus pooling from being gamed, which beats my TREC pooling for gating. But a map written by one author has blind spots. A map written only by models may share blind spots with model producers, which is why two families are required and the owner adjudicates essentiality. |
| **B2** Gate list | **AMEND** | Take the union, with these corrections. **G3** is narrowed to "states or implies that the producer *listened to* the audio, or presents a sonic description as the producer's own observation." Unattributed sonic description stays a §2.8 defect, not a gate. My original wording ("describes sound as heard") would have gated, for example, a duration or instrumentation taken from metadata. **G4** becomes "S1 error *presented as established*", independent of the label taxonomy (see B11). **G7** gets an observable test: "a numeric credit or sample aggregate lacking any of role/numerator/denominator/exclusions/source, used as a premise of a central claim." **G8** is scored only where the trace shows the injected content was retrieved. Otherwise it is N/A, not a pass. G6/G7/G9 gate only when central, as drafted. **Centrality must be redefined** (see Section A, A3). |
| **B3** Floors | **AMEND** | "Every dimension has behaviourally anchored pass/borderline/fail examples, written independently by both contributors and reconciled. Numeric floors are hypotheses until calibrated (B4). **Where a note has fewer than 20 eligible claims, floors are written as counts, not rates.** Example candidate: '0 S1; ≤1 S2-or-S3 among central claims'. A rate is not used there, because with n≈15 a 0.95 precision floor flips on one error." I am withdrawing my rate-only framing for small n. |
| **B4** Calibration | **OBJECT** to "Astra–Claude agreement is the α measured." | Two models agreeing does not show that a human-relevant judgement is reliable. Their errors can be correlated, and both of us helped write the criteria, so we would be marking our own definitions. Replacement: "Reliability is measured (i) between the owner and each model annotator on a fixed subset, and (ii) by **owner test–retest**: a blinded re-rating of ≥10 items after ≥7 days (candidate). Model–model agreement is necessary but not sufficient. A dimension that fails (i) or (ii) is redefined or reported only. It does not bind. The calibration knee is found from **ordered perturbation ladders** per dimension. On each ladder, the owner rates rungs blind and in random order, and the floor is set at the first rung the owner consistently rejects or would fix before use. Logistic fits across critics are dropped (one critic)." **What would change my mind:** evidence that Astra–Claude disagreement on a dimension predicts owner disagreement on that dimension. |
| **B5** Baseline | **AMEND** | "An explicit baseline arm is required. **Preferred:** the owner's own time-boxed research on separate holdout albums, giving T₀. **Fallback:** a mechanically assembled fixed packet (encyclopedia entry + label/distributor page + top-N search results, rule frozen in advance). Acceptance requires (a) no more note-traced errors in owner drafts than in the baseline condition, and (b) the burden B per album is below the median T₀, reported per album with album difficulty named as a confound." The claim allowed is "no evidence of net loss for this critic", not "proven saving" (see Objection 5). |
| **B6** Gate adjudication | **AMEND** | "During development, model triage locates passages and proposes gate flags. The owner adjudicates every flagged gate failure plus a random ≥20% (candidate) of unflagged central claims. **For the final candidate's confirmatory notes, the owner confirms every gate failure and every central-claim pass.** For any album used in the critic task, adjudication starts only **after** the owner finishes that album's critic task." Without that sequencing, the burden measurements are contaminated (Objection 1). |
| **B7** Validation size | **ACCEPT as owner-bound** | My 12+4 albums and 4–6 critics in a Latin square cannot be done with one critic. I withdraw that design as a requirement. See §C. |
| **B8** Reception | **AMEND** | "Documented reception *facts* (charts, awards, documented controversy, published interview quotes found in reviews) are admissible as information. They are labelled 'relayed' at best, and the original speaker class is preserved. Evaluative verdicts from critics never appear as findings. Whether a separate reception section exists is a Stage-B prompt question." |
| **B9** Translation | **AMEND** | "Where a central quote is translated into the output language, the note gives a minimal original-language excerpt (one sentence or a short phrase), or a timecode for audio/video. Fidelity is scored only where some reviewer reads the source language. Otherwise it is *unassessable*, not passed." The draft as written would let unreadable sources pass silently. |
| **B10** Snapshots | **AMEND** | "Adopt as an evaluation-harness requirement, not a prompt requirement. Where no snapshot exists (including all pilot outputs), a later 404 makes the claim *unassessable*, never G2 on its own. Snapshots are not shown to the owner during the critic task." |
| **B11** Labels | **ACCEPT with one addition** | Add: "The evaluation maps whatever labels a prompt version uses onto three evidence levels (read in primary / relayed / unconfirmed or conflicting). The overclaim rate is computed on that mapping, so the criterion survives taxonomy changes." |
| **B12** Context usefulness | **AMEND** | "Context items are typed. A *checkable reason* is required for comparison candidates and influence claims only. Documented participation needs none. The owner rates usefulness 0–2 **during the real critic task**, not in a separate rating session, and marks which items changed what they listened for." |

### Section A: points I do not fully accept

- **A3/A1: "central" is undefined for one critic.** My proposal defined centrality partly as "2 of 3 critic raters would rely on it", and that can't be done here. Replacement: a claim is central if the note puts it in its priority section, **or** it answers a frozen top-3 essential question, **or** the owner marks it as relied-on during the critic task. The marking is recorded before the claim is adjudicated.
- **A5: "every dimension needs its own minimum."** I disagree as stated. With about 10 dimensions, each measured noisily, independent floors compound, so a good prompt can fail by chance. Floors bind only on dimensions that pass the B4 reliability check. Trace-dependent dimensions (stopping, collection efficiency) are N/A where there are no traces, and are never failed by default.
- **A9: "reported beside quality and never folded into it."** My own §7.8 went further than this, and I stand by it. Cost is not folded into a quality score, but **non-negative net burden against the baseline is a separate acceptance condition**, not just a reported number.
- **A12** is right, but with one critic the claim it supports is limited to "useful to this critic". The criteria should say so explicitly.

### What both proposals missed

1. **The owner plays four roles**: essentiality adjudicator, gate adjudicator, calibration rater and the critic whose burden is measured. Each earlier role leaks album knowledge into the later ones. Neither proposal set a sequence for these roles.
2. **Pass pattern across runs.** Astra said to predeclare it, but neither proposal did. My candidate: any owner-confirmed gate failure in any confirmatory candidate run fails the version, because the critic cannot detect it. Floors must hold in ≥ (runs − 1) of the runs per album (candidate).
3. **Harness failures in reliability.** A run classed "not a completed research note" must count toward the run-level pass pattern. If it doesn't, an unreliable prompt can pass on its good runs. Rule (candidate): a harness failure may be rerun once, with the rerun logged. A second failure counts as a failed run.
4. **The provider environment as a confound.** Search tools differ between environments, so a prompt × environment failure may come from the tool rather than the prompt. Record tool identity and version per run.
5. **Evaluator cost as a reported quantity.** If the prompt can only be trusted with hours of owner audit per note, that cost belongs in the result.

---

## 2. Section C: one critic (the owner)

Assumptions (all candidates, unverified):

- Owner adjudication of central claims, with model triage: ~1 h per note. My earlier "1–3 h" was for full checking.
- Critic task: ~1.5 h per album.
- Calibration rating: ~15 min per perturbed note.
- Mapping passes: 2 calls per album.

| Option | Calls (producer) | Owner hours (est.) | Can support | Cannot support |
|---|---|---|---|---|
| **(a) 3 holdouts**, candidate + control × 2 runs × 2 envs | 24 + 6 mapping | ~12 (gate audit of 12 candidate notes) + ~4.5 (critic task) + 0 calibration ≈ **17 h** | A failure screen: "0 confirmed gate failures in 12/12 candidate runs on 3 unseen albums". By the rule of three, that bounds the per-run gate-failure rate below ~25% at 95%. | Calibrated floors (no calibration set). A baseline comparison (no spare album for T₀). Coverage of the six strata (3 albums). Any net-saving claim. |
| **(b) 2 calibration + 4 holdouts** | Candidate 4×2×2 = 16. Control 4×1×1 = 4 (single env/run suffices to show the amendment didn't regress). Mapping 12. Perturbation set ~2×10 notes, partly hand-made. | Calibration ~5. Calibration retest ~2. Gate audit 16. Critic task: candidate on 2 holdouts + own-search T₀ on 2 holdouts ≈ 6. Draft fact-check ~2. ≈ **31 h** | Floors calibrated to this critic. 0/16 gate failures → per-run rate < ~19%. Coverage of four named strata. "No evidence of net loss for this critic" on 2 vs 2 albums. | Statistical reliability. Generalization to other critics. Generalization to strata not sampled. A paired saving estimate (different albums per arm). |
| **(c) 4 calibration + 12 holdouts** | 12×2×3×2 = 144 + controls + 32 mapping | ~72 h of gate audit alone + ~18 critic + ~10 calibration ≈ **100+ h** | Tighter run-level bounds (0/72 → < ~4%) and broad strata coverage. | Still only one critic. Not feasible for one person without delegating gate adjudication, which B6 forbids. |

**Minimum I consider necessary before calling a prompt "passes": option (b).** The verdict is scoped as "passes for this owner, at this version, on these strata". It needs:

- The 4 holdouts jointly cover: post-cutoff release, non-English primary sources, edition/credit or sample complexity, and sparse documentation. One album may cover two strata.
- Roles are sequenced per holdout: mapping passes → (owner critic task, for critic-task albums) → owner adjudication.
- 0 owner-confirmed gate failures across all 16 candidate runs.
- 0 silent top-3 misses.
- Calibrated floors (or counts) held under the cross-run pass pattern.
- 0 note-traced errors in the owner's drafts.
- B below the median T₀.

If the owner can commit only about 17 h, run option (a) and label the result **"screened, not passed"**.

---

## 3. Objections in priority order

1. **The owner's roles contaminate each other.** If the owner builds or adjudicates the map, or audits an album's notes, before doing that album's critic task, then R, V, F and the usefulness ratings measure an already-informed reader. The fixed sequence above, and keeping the owner out of map-building, are mandatory. This matters more than any threshold.
2. **B4's model–model α is not a reliability measure for a human-use criterion.** The two models' errors are correlated, and both are co-authors of the criteria. Owner–model agreement and owner test–retest have to be the binding checks.
3. **Small-n rates and compounding floors will produce arbitrary verdicts.** Use counts below n=20, bind floors only on reliable dimensions, and predeclare the cross-run pass pattern. Otherwise one error, or one noisy dimension, decides the outcome.
4. **Reference maps written only by models can share blind spots with model producers.** Mapping lanes from two families plus owner adjudication of essentiality is the minimum. Unique contributions must be reported, so the map does not punish real discoveries.
5. **Net saving cannot be proven with one critic and 2 vs 2 albums.** The acceptance condition should read "no evidence of net loss, with album difficulty reported", not "positive net saving". My original wording overclaimed what this design can show.