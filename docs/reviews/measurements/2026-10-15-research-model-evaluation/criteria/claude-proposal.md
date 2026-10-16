# Acceptance Criteria for a Pre-Review Music Research Prompt: Claude Contributor Proposal

**Status:** Independent proposal. Every number below is a **candidate** that still needs calibration (§4). None of them is an agreed threshold. I have not seen the other contributor's proposal, any producer outputs, any scores or any rankings, and I make no guesses about them.

**Access limitations:** I did not use web tools. I did not open the five reference-anchor URLs in the pilot rubric and cannot confirm anything they say. Nothing in this proposal depends on their content. One technical premise is unverified: that Genius, Qobuz or Apple pages expose stable per-track role fields. I flag it in §2.5, where it matters.

---

## 0. Design stance

1. **Score claims, not notes.** The basic unit is the *atomic claim*: one checkable proposition with one stated source and one status. Accuracy, attribution, traceability and label calibration all count over claims. A score given to a whole note mostly reflects how much the reviewer liked it.
2. **Gates first, floors second, composite last.** A weighted total is only a tie-breaker among notes that pass every gate and floor. It never decides acceptance.
3. **Usefulness is measured against a baseline.** A note is worth its cost only if the critic ends up with better-grounded knowledge in less total time than with a cheap baseline. Examples of a baseline: the critic's own 30–45 minutes of searching, or a "Wikipedia + label page + top interviews" packet. The pilot had no baseline. Without one, "useful" means nothing.
4. **Cost has two sides.** Collection cost is wall time, tool calls and failed fetches. Critic cost is reading minutes plus re-verification minutes. Both are reported next to quality and are never folded into it.
5. **Judge the outcome, not compliance.** The prompt's caps (8 core items, 1,800–3,000 characters, ≤3 comparisons, ≤2 sample relations, ≤2 questions, ≤3 open items) are not success criteria. A note that breaks a cap but has high value density and low critic burden should pass. A note that follows every cap but silently misses an essential source should fail.

---

## 1. Claim-extraction protocol (prerequisite for every rate)

- **Body claim:** a proposition in the critic-facing body about the album, its people, its process, its sources or its context. Scoping and meta statements ("this search did not access X") are *disclosure items*, logged separately.
- **Atomicity:** split any sentence that mixes verification levels. If the note itself mixes levels in one sentence, record a *bundling defect* and score each part separately.
- **Centrality:** a claim is *central* if (a) the note puts it in its core/priority section, or (b) at least 2 of 3 critic raters say they would rely on it in a review. The raters do this before seeing the adjudicated accuracy.
- **Reliability check:** two annotators extract claims from a subset of notes, at least 20% (candidate). If claim-count agreement is poor (ICC < 0.8, candidate), fix the extraction rules before scoring anything.
- **Appendix:** appendix claims are checked for gate failures, especially fabrication, but they do not count toward density. A fabricated source buried in the appendix is still a gate failure.

---

## 2. Dimensions and metrics

For each dimension: what is observed, the metric, the denominator, and how unavailable data is handled.

### 2.1 Target lock (edition identity)
- **Observed:** artist, title, edition, release date and tracklist are correct and stated. Deluxe, reissue, regional and same-title variants are told apart or explicitly left ambiguous.
- **Metric:** binary *correct / correct-with-disclosed-ambiguity / wrong*. Separately, the share of central claims tied to a named edition.
- **Unavailable:** if the input identifier is truly ambiguous and the note says so, that counts as *correct-with-disclosed-ambiguity*. It is not a defect.

### 2.2 Factual accuracy
- **Observed:** each checked claim is adjudicated *correct*, *wrong*, *imprecise* (right fact, wrong scope, date or number) or *unverifiable by reviewer*.
- **Metrics:**
  - Precision = correct ÷ (correct + wrong + imprecise). The denominator is **verifiable checked claims only**.
  - Error severity: **S1** is central and changes understanding. **S2** is peripheral and wrong. **S3** is imprecise.
  - Named inversion types are counted separately: *negative inversion* ("not found" turned into "doesn't exist"), *scope inversion* (one track generalized to the album; narration treated as quote), *temporal inversion* (a retrospective statement presented as contemporaneous intent).
- **Sampling:** check **all central claims**. If checking every remaining claim is too costly, take a stratified random sample of non-central claims and report n and the interval. Never extrapolate from central claims to the whole note.
- **Unavailable:** "unverifiable by reviewer" sits in neither the numerator nor the denominator. Report it as a share. If it exceeds 25% of central claims (candidate), confidence is marked low and the note cannot be *accepted* on that evaluation, only *deferred*.
- **Report raw fractions** (e.g. 13/14) whenever n < 20. Percentages on small n invite false comparisons.

### 2.3 Attribution
- **Observed:** for every claim about what someone said or intended, the stated speaker class matches the source. Classes: artist direct speech, collaborator direct speech, journalist narration, label/distributor copy, platform editorial, database registration.
- **Metrics:**
  - Attribution accuracy over speech/intent claims.
  - **Upgrade rate**, reported separately: narration or label copy presented as direct speech. This direction is the dangerous one.
  - Independence errors: syndicated or copied text counted as several sources.
- **Translation fidelity (missing in the frozen prompt):** the output is Korean while most sources may not be. Every direct quote used as a central claim needs a minimal **original-language excerpt** next to the translation. A metric for this: the share of central quotes where the translation keeps the speaker's hedges and scope.

### 2.4 Source traceability
- **Observed:** a reviewer can get from the claim to the supporting passage using only what the note provides.
- **Metrics:**
  - Trace success = central claims where the passage is located ÷ central claims that need a source.
  - **Time-to-locate**, median and maximum, in minutes. This is the critic's re-verification burden in its simplest form.
  - **Excerpt fidelity:** the quoted excerpt actually appears at the stated location.
  - Location granularity: paragraph, page or timecode, versus bare URL.
- **Unavailable:** link rot or paywalls found at review time are checked against the run-time snapshot or archive. **Harness requirement (missing):** runs must store retrieved-page snapshots or hashes. Without them, a later 404 cannot be told apart from fabrication. If the note itself disclosed an access failure, that is not a trace failure.

### 2.5 Status-label calibration
- **Observed:** whether each status label ([원문 확인], [교차 확인], …) matches the adjudicated evidence.
- **Metrics:** a confusion matrix of the stated label against the adjudicated label, from which:
  - **Overclaim rate:** the label is stronger than the evidence.
  - Underclaim rate, reported but weighted far less.
- **Challenge:** the frozen prompt's 5 source types × 6 statuses give 30 combinations. My expectation is that annotators will disagree on fine distinctions such as [재인용] versus [검색 결과 경유], and critics get little from them. **Candidate simplification** for the critic-facing body: three levels (*read in primary*, *seen only relayed*, *unconfirmed/conflicting*) plus the source type. The finer labels stay in the appendix. Validation (§5) should test whether the extra labels change any critic action. If they don't, drop them.
- **Missing requirement:** a claim produced from model memory with no retrieved source must be labelled as such or left out. An unsourced claim carrying any "confirmed" label counts as an overclaim and, if central, is a gate failure (§3).

### 2.6 Edition and credit precision
- **Observed:** credit claims keep the role field (composition, lyrics, production, performance, engineering), the track and the edition. Every numeric aggregate states role, numerator, denominator, excluded tracks and source.
- **Metrics:**
  - Credit-claim precision against at least one authoritative row: physical booklet, distributor credit or registry. The reviewer records which.
  - **Aggregate disclosure rate:** aggregates with all five elements ÷ aggregates. Floor is 100%, because a single undisclosed aggregate can mislead.
  - Instances of share-arithmetic, where credit counts are turned into workload or decision weight.
  - "No credit" treated as "no participation."
- **Unverified premise:** I assume some services expose per-track role fields stably. If a service flattens roles, the note should say so. The rubric must not penalize a note for not reporting a role distinction the source never contained.

### 2.7 Significant omissions (recall)
This is the hardest dimension to make objective, and the pilot rubric leaves it the most under-specified ("important accessible sources considered").
- **Reference set:** for each validation album, two researchers who are blind to outputs build an *essential-item list* within a fixed time box. The list is then **pooled** with items any evaluated note found, and a critic panel adjudicates each item as *essential / useful / marginal*. Pooling follows the TREC approach and reduces the bias of a reference written by one person.
- **Metrics:**
  - Essential recall, with every essential item graded one of three ways: **captured**, **flagged as gap with a route** (the note names the source class or URL it couldn't reach), or **silently missed**.
  - Report the *silent-miss* count separately. It is the failure that hurts critics, because they cannot tell what is absent.
- **Denominator:** essential items that were **accessible at run time**, confirmed by a reference retrieval in the same window. An item behind a 403 for everyone leaves the denominator. If a note retrieved it anyway, it counts as captured and is logged as such.
- **Known bias:** a pooled reference favors notes that look like the other notes. A note that finds a genuinely new essential item gets it added after adjudication. Report how many essential items each note contributed uniquely.

### 2.8 Musical context without replacing criticism
- **Observed:**
  - Context items are typed: direct participation, stated influence, production connection, comparison candidate.
  - **Listening claims:** descriptions of sound, effect or emotional arc that are not attributed to a source.
  - Evaluative verdicts.
- **Metrics:**
  - Listening-claim count, which is gated (§3).
  - Count of verdicts or evaluative adjectives presented as findings.
  - Share of comparison candidates that state a concrete, checkable reason.
  - Shared-personnel-to-influence leaps.
  - Biography-to-intent leaps.
- **Usefulness:** critic raters rate each context item from 0 ("irrelevant") to 2 ("would shape what I listen for").

### 2.9 Uncertainty and conflict handling
- **Metrics:**
  - **Conflict-disclosure recall:** reference-known conflicts surfaced ÷ reference-known conflicts.
  - **Hedge calibration:** among hedged claims, the share that adjudicate as wrong or unconfirmed, compared with the same share among confident claims. Hedges should concentrate where errors are. A note that hedges everything is not calibrated; it is noisy.
  - Unresolved items: whether each one states what would resolve it.

### 2.10 Information selection (density)
- **Metrics:**
  - **Useful share:** body claims rated essential or useful ÷ body claims.
  - **Duplication rate:** repeated propositions ÷ body claims.
  - **Off-target share:** biography, genre history and platform trivia with no stated link to the album.
  - Body length, recorded only as an input to critic cost (§2.12), not as a dimension in itself.
- **Ranking quality:** do the top-ranked body items match the items critics rate essential? A suitable measure is rank correlation, or simply whether the top 3 contain the critics' top 3.

### 2.11 Stopping and collection efficiency
These metrics need traces. Score them only where traces exist; otherwise mark them **N/A**, not zero.
- **Metrics:**
  - Wall time.
  - Tool calls.
  - Failed fetches.
  - **Identical repeated failed requests**: a direct waste signal.
  - **Time-to-last-essential:** the point at which the last essential item was acquired, as a fraction of total run time. A large tail after it suggests the run kept going after it had stopped finding anything; a run that ends before the essentials suggests it stopped too early.
  - Essential items per tool call.
- **Challenge:** the frozen prompt's rule "stop a branch after two consecutive fruitless searches" can't be observed from the note, and the number is arbitrary. Judge the *yield curve*, not compliance with a count.
- **Tokens:** token counts are provider-specific and include cached scaffolding. Report them only within one provider, and never as money charged to a subscription.

### 2.12 Critic reading and re-verification burden
- **Measured in the real-task study (§5):**
  - **R** = minutes to read the body to working understanding.
  - **V** = minutes to re-verify the claims the critic decides to rely on.
  - **F** = minutes to fix or replace claims found wrong.
- **Derived:**
  - Burden **B = R + V + F**.
  - **Net time saving = (T₀ − B) ÷ T₀**, where T₀ is the critic's baseline research time for equal coverage.
  - **Re-verification cost per relied-on claim = V ÷ relied-on claims.**
- **Downstream harm:** factual errors in the critic's draft that trace back to the note. This is the most direct measure of whether the note is safe.

---

## 3. Noncompensable failures

**Per-instance gates (one occurrence fails the note):**

| ID | Failure | Observable test |
|---|---|---|
| G1 | Wrong target | Central claims describe a different album or edition, and this is not disclosed |
| G2 | Fabricated source or quote | The URL or document doesn't exist, or the stated location doesn't contain the quoted or paraphrased content (checked against the run snapshot) |
| G3 | False access or listening claim | Claims to have read a source it never retrieved (according to the trace), or describes sound as heard |
| G4 | Confident central falsehood | An S1 error carrying a "confirmed" level label |
| G5 | Central attribution upgrade | Narration, label copy or a database entry presented as the creator's direct speech, in a central claim |
| G6 | Central absence inference | "Not found / not registered" turned into "doesn't exist / wasn't involved" and used centrally |
| G7 | Undisclosed or partial aggregate used as a thesis | |
| G8 | Instruction-following from source content | Prompt injection |
| G9 | Unsourced memory presented as verified, in a central claim | |

**Rate floors (candidates, to calibrate in §4):**

- Central-claim trace success ≥ 0.9
- Overall precision ≥ 0.95
- Overclaim rate ≤ 0.05
- Aggregate disclosure = 1.0
- **Silent misses among the top-3 essential items = 0**
- Essential recall (captured + flagged) ≥ 0.7
- Useful share ≥ 0.6
- Unverifiable share of central claims ≤ 0.25, otherwise *deferred*

**Not gates, on purpose:**

- Exceeding a length or cap.
- A disclosed important gap (the pilot rubric is right that this is not equivalent to fabrication).
- An incomplete all-track table.
- Status-label granularity mistakes that don't overclaim.

**Harness failures** (no web access, tool denial) produce the outcome class *not a completed research note*. They are reported apart from quality. The only thing graded is honesty: did the note disclose the failure, and did it avoid filling the gap from memory?

---

## 4. Threshold-calibration method

1. **Build a calibration set of perturbed notes.** On 3–4 calibration albums, take high-quality notes (written by reference researchers) and create controlled degradations:
   - inject 1–3 errors at S1, S2 or S3;
   - downgrade attributions;
   - remove essential items, either silently or with a disclosure;
   - add off-target padding;
   - strip locations from citations.
   This gives notes with known metric values.
2. **Elicit critic decisions blind.** Critics classify each note as *use as is*, *use after fixes* or *reject*, and say why.
3. **Set each floor at the knee.** For each metric, take the value below which most critics reject. Candidate rule: ≥ 80% reject or would-fix-before-use. Use logistic fits per metric, holding the other metrics roughly constant thanks to the controlled perturbations.
4. **Check against cost.** A floor is acceptable only if notes just above it still give a positive net time saving (§2.12) and no more downstream draft errors than the baseline.
5. **Check reliability before using a floor.** A dimension needs inter-rater agreement (Krippendorff's α ≥ 0.67 candidate) before its floor can bind. Otherwise, redefine or merge the dimension; don't gate on noise.
6. **Freeze before testing.** Thresholds, the claim-extraction rules and the composite weights are frozen and hashed before any held-out album is run. Calibration albums are never reused as test albums.
7. **Composite weights, if kept at all:** derive them from which dimensions predicted critic acceptance in steps 2–3, not from intuition. My expectation is that this will raise critic usability well above the pilot's 5%, because usability is the purpose of the note.

---

## 5. Finite validation design

**Albums: 12 held out + 4 calibration (candidate).** None of them is the pilot album. Strata:

- **Source richness:** heavy press coverage versus a handful of sources.
- **Release timing:** at least 4 released after the producer models' knowledge cutoffs. These test retrieval rather than memory. Older catalog albums test depth.
- **Language:** at least 3 where the key primary sources are not in English, including Korean- and Japanese-language sources.
- **Edition complexity:** at least 2 with deluxe or reissue versions or regional tracklists.
- **Credit and sample regime:** sample-heavy (hip-hop or electronic), session-musician-heavy (jazz or soul), and one long-tracklist album or compilation to stress the all-track requirement.
- **Classical:** optional, flagged out of scope unless intended. Its credit model (composer, performer, conductor, recording) differs.

**Conditions:**

- Frozen prompt.
- At least one amended prompt.
- The cheap baseline packet.
- Optionally, no-note critic self-research to obtain T₀.

The design evaluates **the prompt across producers**, without ranking the producers. Report prompt × producer interaction only to find failures the prompt causes.

**Replication:** at least 3 independent runs per condition per album. The pilot's single generation can't tell prompt effects from sampling noise.

**Reference work per album:**

- Two blind researchers build the essential list (§2.7).
- Pooled adjudication.
- A run-window accessibility check.

**Real critic task:**

- 4–6 critics, in a Latin-square crossover: each critic sees each condition, on different albums, with no critic seeing the same album twice.
- The critic writes a review outline, or a short review if the budget allows. They log R, V and F, mark which note claims they relied on, and rate usefulness.
- Drafts are fact-checked for errors that trace back to the note.
- Optional: one planted error per note, to test whether status labels prompt verification where it is needed.

**Analysis:**

- Prespecified.
- Gate pass rates with exact counts.
- Distributions of the floor metrics with intervals.
- Paired net time saving against the baseline.
- No claims of significance beyond what n supports. With 12 albums, report effect sizes and intervals, not p-values as proof.

**Budget control:**

- Claim checking is the dominant evaluator cost, roughly 1–3 hours per note (my estimate).
- Use full checks for central claims and sampled checks for the rest.
- LLM-assisted triage is acceptable for locating passages. **Gate decisions require human adjudication.**

---

## 6. Challenges to the frozen prompt and pilot rubric

**Requirements that may be unnecessary or too costly:**

- **Mandatory all-track checklist.** It is useful for showing where evidence is concentrated, but expensive and low-value per cell on long tracklists. Proposal: one compact line per track, or a coverage statement plus gaps only. Validation should test whether critics use it.
- **Three-layer A/B/C records with per-claim IDs.** Good for audits, but heavy for critics. Keep IDs for body claims; let the appendix be minimal, or hand it over as an attached file that the critic doesn't need to read.
- **Fixed caps.** They risk omissions on source-rich albums. Evaluate density and burden instead.
- **Blanket ban on other critics' reviews.** It guards against borrowing interpretations. But reception and controversy can be information a critic needs, and reviews sometimes carry first-hand interview quotes. Candidate amendment: an *opt-in*, separately labelled reception section; anything taken from it is labelled "relayed" at best.
- **The 30-combination status taxonomy** (§2.5).
- **Album-specific scars.** "게임 이용법", "9 of 10 tracks", "두 곡 샘플" read like fixes for the pilot album. They should be generalized or removed, or the prompt will overfit.

**Missing requirements:**

- Labelling or excluding claims from model memory (G9).
- Original-language excerpts for translated quotes.
- Run-time snapshot or hash storage (a harness requirement).
- A **coverage statement**: which source classes were checked, in which languages, with which outcomes. It is what lets the critic interpret absences.
- Searching in the artist's working language.
- Official lyric-source provenance (lyric sites are often unreliable).
- Recording dates and locations, and differences between formats or masters, where relevant.
- A time or tool budget that is stated, so cost is interpretable.
- A **baseline comparison** in the evaluation.

**The pilot rubric's core questions lean toward intentionalism.** Three of five centre on the creator's own account. Critics often need equal weight on documented release context, reception facts and personnel history. The rubric should reward these when they matter, without requiring them.

---

## 7. Main tradeoffs and objections

1. **Recall against brevity.** Caps produce short notes with silent misses. Ranking with a short body and a linked appendix is the answer, but it moves cost into how good the ranking is, which §2.10 must measure.
2. **Audit rigor against critic burden.** Every ID, label and excerpt helps the evaluator and costs the reader. Validate each piece of apparatus by whether it changes what the critic does.
3. **A pooled reference favors consensus.** Mitigation: track unique contributions; experts adjudicate additions.
4. **Zero-tolerance gates may reject many notes.** That is intended for G2–G5: a critic cannot see a fabricated quote, and one of them destroys trust in the whole note. For G6, G7 and G9, centrality acts as the safety valve; peripheral cases are defects, not gates.
5. **The context/criticism line is blurry.** Comparison candidates are useful, but they nudge the critic's framing. Requiring a concrete, checkable reason is the compromise. Critic ratings should show whether it holds.
6. **Albums released after the cutoff test retrieval but tend to have few sources.** The strata must include both, or recall and accuracy will be confounded with how much was published.
7. **Evaluator cost may exceed research cost.** Sampling plus human adjudication of gates only. Accept wider intervals on non-central precision.
8. **Separating cost from quality can hide bad trades.** Acceptance should require passing the gates and floors **and** positive net time saving against the baseline. A note that is excellent but takes longer to read and verify than the critic's own research does not meet the brief.