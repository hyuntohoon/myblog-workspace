FREEZE AFTER LISTED FIXES

# Round-2 sign-off: Claude contributor (`claude-opus-5-5`)

**Status:** I reviewed the acceptance-v1 draft against both round-1 responses. I used no web tools, looked at no producer outputs, researched no album and ranked no models. The drafter shares my model family, so I checked closest wherever the draft adopted or adapted my round-1 positions. Two of the problems below come from my own round-1 text.

All the fixes below are text changes inside the existing design. None changes the panel, the environments, the baseline or the separate-claims decision.

---

## 1. Section verdicts

| § | Verdict | Short reason |
|---|---|---|
| 1 Scope | **SIGN** | |
| 2 Units | **MATERIAL OBJECTION** | The definition of "central" depends on where a claim sits in the note. A consequential error moved out of the priority section avoids every central-only gate. |
| 3 Integrity gates | **MATERIAL OBJECTION** | There is no rule for a gate allegation that can't be resolved, and the confirmation runs aren't required to preserve evidence. Either way, an unchecked fabrication can turn into "no gate failure found". |
| 4 Dimensions and floors | **MATERIAL OBJECTION** | Binding status isn't frozen before confirmation, and a pass could rest on gates alone if accuracy (D2) and omissions (D7) fail to bind. |
| 5 Reference map | **MATERIAL OBJECTION** | The owner sets the top-3 after reading a candidate note. Additions that only control outputs could reveal are found at lower audit depth. Both favour the candidate. |
| 6 Calibration | **MATERIAL OBJECTION** | The reliability criterion is undefined. About 8 examples can't hold ladders "per dimension" for 11 dimensions. |
| 7 Confirmation design | **MATERIAL OBJECTION** | There is no deferral rule if audits run past the hour budget. |
| 8 Pass pattern | **MATERIAL OBJECTION** | Item 4 can't be evaluated per environment. It's unclear which claim a pass requires. "Comparable evidence" is undefined. |

### §2: material objection

**Problem.** G1, G4, G5, G6, G7 and G9 apply only to central claims. The operational definition covers three cases: claims in the note's priority content, claims answering a top-3 question, and claims the owner marked during a task. Only 2 of the 4 confirmation albums have a candidate-assisted task, so for 12 of the 16 candidate outputs there's nothing to mark. A wrong credit or a model-memory claim presented as verified would pass the gates if it sat in a non-priority section. That is the "move it to an appendix" gaming Astra's objection 5 describes. It also contradicts Astra's B2, which the draft cites: centrality "depends on potential consequences for the critic, not the section containing the claim."

**Replacement text** (replaces the "Central claim" paragraph):

> **Central claim:** one with a potential consequence for the critic. A claim is central if **any** of these holds: (a) it is in the note's priority content; (b) it answers a frozen top-3 essential question (§5); (c) the owner marked it as relied-on during the task, recorded before adjudication; or (d) the adjudicator judges that, if wrong, it would plausibly change a factual statement, attribution, credit or listening focus in a review of this album. Test (d) applies wherever the claim appears, including appendices, and is applied before the claim's correctness is known where practicable. Placement can make a claim central; it can never make one peripheral.

### §3: material objection

**Problem 1: unresolved gate allegations.** The draft says that without a snapshot, the result is *unassessable*. The >25% deferral rule in §2 only counts central claims. So a G2 or G3 allegation that can't be resolved, central or not, ends up as "no gate failure found". That record is accurate, but the version can still pass under §8.1.

**Problem 2: no preservation requirement.** B10 was agreed in substance by both contributors, but the draft never requires preservation for the confirmation runs. Both environments return processed text: Claude CLI's WebFetch gives the producer a model-processed summary of the page, not the raw page. So "what the producer saw" is the tool output, not the URL. If either environment's trace can't record what was retrieved, the second G3 clause and G8 become N/A there. The two environments would then be screened unequally.

**Replacement text** (append to §3 after the "Evidence distinctions" sentence):

> **Preservation (confirmation runs).** Every confirmation run stores the full tool-call log: queries, URLs, retrieval times and the tool output the producer actually received. The harness also captures its own retrieval of each cited URL at run time, subject to storage permissions. The record distinguishes producer-received tool output (which may be a summary or snippet), harness-captured page content and relayed material. A hash may supplement stored content but never replaces it. Trace availability per gate (G3 second clause, G8) is reported per environment. A gate that is N/A in one environment only is stated as a screening asymmetry in the result.
>
> **Unresolved gate allegations.** An alleged gate failure the owner cannot confirm or clear is recorded as *unresolved* with its reason. An unresolved allegation on a central claim makes the note **deferred**, not passed. Unresolved peripheral allegations are listed in the result next to the verdict.

### §4: material objection

**Problem.** Floor policy 3 lets any dimension that fails reliability become reported-only, but doesn't say when that is decided. If every dimension fails reliability, a "pass" rests on gates alone and is still called an acceptance pass. Accuracy (D2) and omissions (D7) are what the deliverable exists for.

**Replacement text** (replaces floor-policy item 3):

> 3. The set of binding dimensions, their floors and their zero-denominator rules are **frozen in the round manifest before any confirmation output is generated**, and are not changed afterwards. A dimension binds only if it passed the §6 reliability criterion. One that fails is redefined and re-checked before the freeze, or else reported only. Gates always bind. **If D2 (accuracy) or D7 (omissions) is not binding at freeze, confirmation may still run, but its result is reported as "gate screen passed; acceptance deferred", never as a pass.** The result names which dimensions bound.

### §5: material objection

**Problem 1: top-3 contamination.** Under the §7 sequence, the owner labels essentials and the top-3 *after* their task. On the 2 candidate-assisted albums, the owner has just read a candidate note. The top-3 they pick can then reflect what that note surfaced, which makes "0 silent top-3 misses" (§8.2) close to automatic for the candidate. This comes from my round-1 text. My B1 had the owner label essentials before seeing any output, while my §C sequence put the task first. The draft resolved that tension toward the task-first order, which keeps the task clean but compromises the gate. Labelling before the task would expose the owner to album evidence, so the top-3 has to be fixed without the owner.

**Problem 2: asymmetric discovery.** Candidate outputs are fully audited (§7), but control outputs are only triaged. An essential item that only a control output found is less likely to be noticed, and it is exactly the kind of item that could fail the candidate under the symmetric-amendment rule.

**Replacement text** (replaces the second bullet; adds a new bullet after the third):

> - Before confirmation, the owner pre-registers album-independent essential-question categories (for example: release identity and edition; principal credits; documented creator statements; sample or interpolation provenance; reception facts). Each mapping lane proposes, blind, essentials and a top-3 within those categories. A model reconciler merges them under a fixed rule (union of the lanes' top-3, reduced to three by category priority as predeclared). This **frozen top-3 is set before the owner's task and not shown to the owner**. After the task, the owner labels the remaining essentiality and may *add* top-3-equivalent essentials. Additions are treated as amendments (next bullet), flagged "post-exposure", and reported separately. The owner may remove a frozen top-3 item only for a documented factual error in the map, with the evidence recorded.
> - Every control output, and the owner's own baseline research notes, are screened for candidate map additions (items not in the initial map) at the same depth as candidate outputs. Model triage proposes the items, and the owner adjudicates every proposed addition, blind to condition. This is a screen for *map additions*, not a full claim audit of control outputs.

### §6: material objection

**Problem.** "Passes the reliability checks" has no criterion, so whether a floor binds is decided case by case: a fail becomes arbitrary, or a pass becomes lenient. About 8 calibration examples can't also hold ladders for 11 dimensions.

**Replacement text** (replaces the two bullets):

> - Two calibration albums, never reused for confirmation. Calibration material is about 8 blinded natural outputs (covering both environments) **plus perturbation ladders only for dimensions proposed to bind**. Each ladder has at least 3 rungs built from one base note. The owner gives use / use after fixes / reject decisions in random order. The floor hypothesis is the first rung the owner consistently rejects or would fix. No curve fitting unless the observations support it.
> - A dimension **passes reliability** (and may bind) only if, as predeclared in the manifest: (i) on the delayed repeat subset (≥ 7 days; candidate), at least 2 items per proposed-binding dimension, none of which flips between *use* and *reject* (a move to or from *use after fixes* is tolerated); and (ii) the model annotator's pass/fail call on that dimension's ladder rungs matches the owner's on at least all but one rung. Astra–Claude agreement is used only to expose ambiguous definitions; it is neither human reliability nor evidence of correctness, and it is not required for binding.

The specific thresholds in (i) and (ii) are candidates. What is material is that some criterion is written down before calibration.

### §7: material objection

**Problem.** The owner's 30–60 hour ceiling and full verification of 16 outputs are both fixed. The draft doesn't say what happens if the hours run out first. Astra's §C-4 rule ("acceptance deferred if the necessary audits remain incomplete") was dropped.

**Replacement text** (append to the "Audit allocation" bullet):

> If the hour budget runs out before every candidate output's central and high-risk claims are verified, and before every alleged gate failure and proposed map addition is adjudicated, the result is **deferred**. Mandatory checks are never sampled down to fit the budget. Actual owner hours per role (mapping adjudication, task, labelling, audit, calibration) are reported.

### §8: material objection

**Problem 1: item 4 can't be evaluated per environment.** §8 decides the pass "in an environment", but item 4 requires the benefit "in both matched blocks". Under §7, each environment has exactly one candidate-assisted task, so each environment appears in only one block. Item 4 can't be evaluated per environment as written. Any verdict on it would be arbitrary.

**Problem 2: no required claim.** The section doesn't say which claim a pass requires. A version that clears items 1–3 and 5 but shows neither benefit has no defined verdict.

**Problem 3: undefined comparison.** "Comparable or better usable evidence" has no operational definition.

**Replacement text** (replaces §8 intro and item 4; items 1–3 and 5 stay as drafted):

> Before confirmation, the manifest declares the targeted claim(s): time-saving, quality improvement, or both.
>
> **Environment-level screen.** The candidate passes the v1 *screen* in an environment if items 1, 2, 3 (for that environment's task) and 5 hold for that environment's outputs.
>
> **4. Benefit claims (pooled across environments, owner decision: judged separately).** These are evaluated only if **both** environments pass the screen, and they are reported for the prompt, not per environment.
> - *Comparable usable evidence*, scored by the post-task audit for each block: the candidate-assisted outline contains no more adjudicated factual errors than the paired baseline outline, and covers at least the same proportion of that album's frozen top-3 essentials.
> - **Time-saving:** comparable usable evidence, and owner active time (search + R + V + F + outline) lower than the paired baseline, in **both** blocks. Collection latency is reported separately. Reported as "preliminary saving for this owner"; if comparable evidence holds but time is not lower in both blocks, "no evidence of net loss" may be reported only if time is not higher in either block.
> - **Quality improvement:** a predeclared consequential gain within a predeclared extra-time allowance, in **both** blocks.
> - Mixed evidence is *inconclusive* for that claim.
>
> **Verdict.** "Passes v1" is stated only for a declared claim that holds, together with the screen in both environments. If the screen passes but no declared claim holds, the result is "screen passed; benefit not shown". Each block pairs one environment's candidate task with one baseline task, so environment and album are confounded with block, and the result says so.

---

## 2. Section 9 rows

| Item | My answer |
|---|---|
| **Recall denominator after new discoveries** | **Confirm Astra's rule (§5).** I withdraw "additions are prospective only". With a frozen amendment procedure, blind and symmetric adjudication, preserved initial verdicts and both recalls reported, the gaming risk I raised is addressed. Freezing additions out would let a known essential omission pass. One condition, which is my §5 objection: discovery has to be equally likely from control outputs and baseline research. Without that, symmetric *application* doesn't produce symmetric *detection*. |
| **Floors across runs** | **Confirm "all outputs" (§8.1).** I withdraw "≥ runs − 1". With 2 runs it means 1 of 2, which would pass a prompt that falls below the floor half the time. The critic gets whichever single run is produced. The compounding concern is handled once floors bind only after reliability (§4.3 as amended) and each floor is anchored at the rung the owner would reject or fix (§6). A floor failure is then a real reject, not noise. |
| **Owner usability per environment** | **It blocks an environment-level *usefulness* claim. It does not block an environment-level *screen*.** Eight outputs per environment can support the gates, floors, top-3 check and the misdirection check on that environment's single task. One task per environment can't support a per-environment time-saving or quality claim. So benefit claims are pooled across environments, and evaluated only if both environments pass the screen. My §8 replacement says this. |

---

## 3. Misrepresentation check (my round-1 position)

- **§8.4, "no evidence of net loss / preliminary saving … (Claude objection 5)".** My objection 5 proposed "no evidence of net loss, with album difficulty reported" as the *acceptance condition*. The slash makes it read as interchangeable with "preliminary saving". These are different claims: lower burden in both blocks supports "preliminary saving"; burden that is not higher supports only "no net loss". My §8 replacement separates them. The underlying change is consistent with the owner's fixed decision, so this is attribution wording, not a dispute.
- **§6, "Astra–Claude agreement is used only to expose ambiguous definitions … (Both.)".** I wrote: "Model–model agreement is necessary but not sufficient." The draft drops "necessary". I now **accept** the draft's position: two models can disagree while the owner is reliable, so model agreement shouldn't be required for binding. The "(Both.)" attribution is accurate as of round 2, not round 1.
- **§5, top-3 timing.** The first bullet's "(Claude B1)" cites me correctly. The second bullet doesn't cite me. My round-1 text had the owner label before seeing any output, and was internally inconsistent about it (see §5 above). This isn't a misrepresentation, but the draft's resolution is the source of my §5 objection.
- **§2, central claim "(Astra B2, Claude A3)".** The operational definition is mine. It doesn't satisfy Astra's B2 as quoted above. This is Astra's call to make, but my §2 objection fixes it.

There are no other misrepresentations. The G3 narrowing, G7's test, G8's N/A rule, counts below 20 claims, ordered ladders, the owner-role sequence, the harness-rerun rule and tool/version logging all match what I proposed.

---

## 4. What the fixed owner decisions cannot support

I'm not re-arguing these; this is only scope.

- **Two environments with 4 tasks:** no per-environment usefulness, time-saving or quality claim. Environment-level results are screens only.
- **Owner's usual research on different albums:** no paired or causal saving estimate. Album difficulty and block are confounded with condition. The result is preliminary evidence for this owner.
- **30–60 hours:** this covers full candidate audits only if the per-output cost stays near the lower end of the 1–3 h range. The §7 deferral rule is what stops the budget from quietly lowering audit depth.
- **One owner:** nothing about other critics (already stated in §1).

---

## 5. Wording preferences (not material)

- D4, "independent reader": specify "a reader who did not produce the note (owner or a non-producer model lane)".
- G3 combines two failure types (claimed listening; claimed reading without retrieval). Consider G3a and G3b so per-environment trace asymmetry is easier to report.
- §2 "imprecise": say whether it counts against precision as an error or is reported as a separate share.
- §7 "control": name the control prompt version in the manifest.
- §9 can be deleted at freeze. Record the resolutions in a changelog.