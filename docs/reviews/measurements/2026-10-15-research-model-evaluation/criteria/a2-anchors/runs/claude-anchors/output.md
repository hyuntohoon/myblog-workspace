# A2 anchors — Claude (`claude-opus-5-5`)

**Fictional fixtures** (all invented, used only here): album *Tidewater Ledger* by Mara Quell (Northlight Records). It has a standard edition (2025, 10 tracks) and a deluxe edition (2026, 14 tracks). Juno Quell is a relative who contributes vocals. Ines Darrow is an engineer and co-producer. *Low Signal* (2021) is an earlier EP by Quell. Ada Brenn is another artist. The sources are *Fieldnote Weekly* (an interview), *The Quarter Review* (a review), the Northlight bio, Northlight liner notes, and the "Distributor row", meaning a per-track credit page. Where I mention pilot behaviour, it is described as behaviour, not as facts about the pilot album.

---

## D1 Target lock

### PASS
- **Observable:** "Target: *Tidewater Ledger*, standard edition (Northlight, 2025, 10 tracks). A 2026 deluxe adds tracks 11–14. Those tracks appear only in §Editions, each marked 'deluxe only'."
- **Verdict reason:** The lock is correct. The one real ambiguity (two editions) is disclosed, and the disclosure carries down to each claim. This is "correct" or "correct with disclosed ambiguity".
- **Boundary move:** Remove the per-track "deluxe only" markers but keep the header. That gives BORDERLINE.

### BORDERLINE (use / use after fixes)
- **Observable:** The header is correct and says "a deluxe edition exists". The tracklist section lists 14 tracks without marking which are deluxe-only, and the credits for T12 come from the deluxe row.
- **Verdict reason:** The target is correct and the ambiguity is disclosed at note level. At claim level, a reader cannot tell which edition some claims describe.
- **Boundary move:** Mark T11–T14 to reach PASS. Remove the header disclosure, so that deluxe material reads as the target, to reach FAIL. If that undisclosed material is central, the result is G1.

### FAIL
- **Observable:** "Target taken as the 2026 deluxe (14 tracks); the standard edition could not be located." The request named the standard edition, and it was accessible.
- **Verdict reason:** The lock is wrong. It is **not G1** because the note discloses it, and G1 requires "undisclosed". It would be G1 if the note presented deluxe credits or tracks as the standard edition's without saying so, in central claims.
- **Boundary move:** Lock onto the standard edition and keep the deluxe material flagged. That gives BORDERLINE or PASS.

**Not this dimension:** A wrong release date for the correct edition belongs to D2, as imprecise (temporal).

**Annotator note:** Use D1 when the note confuses one album or edition with another. Use D2 when a fact about the correct target is wrong.

---

## D2 Accuracy

### PASS
- **Observable:** "Tracked at Harbour Room between Oct 2023 and Feb 2024 (*Fieldnote Weekly*, ¶6)." The audit finds every central claim supported. One peripheral tour date is off by a day and is recorded as imprecise.
- **Verdict reason:** Precision is high. There is no central error, and the only error is a low-severity peripheral imprecision, which is reported in the imprecise share.
- **Boundary move:** Add a peripheral inversion of background chronology. That gives BORDERLINE.

### BORDERLINE (use / use after fixes)
- **Observable:** Central claims are supported. In "Background", the note says "the lead single followed the album announcement", but the sources show the reverse (a temporal inversion). It also says "the only feature on the record is Juno Quell", but the Distributor row lists a second featured artist on T9 (a scope inversion, adjudicated peripheral).
- **Verdict reason:** Precision drops because of two peripheral errors. The inversion types are recorded, and no central claim is affected.
- **Boundary move:** Remove both errors to reach PASS. Make one of them a central claim (still hedged) to reach FAIL.

### FAIL
- **Observable:** "Reportedly mixed by the band's drummer." The sources name an external engineer, so the claim is central and incorrect. The note also contains several peripheral errors, including the negative inversion "no remix EP was issued" when one was.
- **Verdict reason:** Low precision, plus a central incorrect claim. It is **not G4** because the central claim is hedged ("reportedly") and not presented as established. It is also not G6: the remix claim is peripheral, and peripheral G6 patterns are defects. It would be G4 if the note said "Mixed by the band's drummer" as fact.
- **Boundary move:** Correct the central claim. That gives BORDERLINE.

**Not this dimension:** A correct claim that the note labels "confirmed" when it was only relayed belongs to D5 (overstatement).

**Annotator note:** S1/S2/S3 labels come from the frozen scoring manual (§6.1). These anchors deliberately do not assign them.

---

## D3 Attribution

### PASS
- **Observable:** "*Fieldnote*'s interviewer writes that sessions 'stretched over two winters' (narration). Quell, quoted in the same piece: 'I kept the first takes.' *Quarter Review* and *Fieldnote* both repeat the Northlight bio's 'recorded in a lighthouse'. This is treated as one source (label bio)."
- **Verdict reason:** Each sentence has the correct speaker class, there are no upgrades, and relayed copies of the same source are not counted as independent.
- **Boundary move:** Leave one narrated number without a speaker. That gives BORDERLINE.

### BORDERLINE (use / use after fixes)
- **Observable:** "Forty demos were cut to ten." This sits in Background with no speaker named. It is interviewer narration, and the claim is peripheral.
- **Verdict reason:** There is no upgrade, but the speaker class cannot be recovered from the note. This matches the pilot pattern of numbers losing their speaker.
- **Boundary move:** Add "(interviewer)" to reach PASS. Add "Quell says" to reach FAIL.

### FAIL
- **Observable:** "Quell says she wrote most lyrics 'on the night bus'." The phrase is interviewer narration, and the claim was adjudicated peripheral. The note also says: "Three outlets independently confirm the lighthouse recording." All three relay the label bio.
- **Verdict reason:** There is one upgrade and one independence error. It is **not G5** because the upgraded claim is non-central under test (d), and the independence error is not a gate pattern. It would be G5 if the same narration-to-speech upgrade carried a central claim, for example about the album's concept or recording method. The pilot's narration-promoted-to-speech defect is the same mechanism.
- **Boundary move:** Restore "interviewer writes" and say that the three outlets share the bio as their source. That gives PASS.

**Not this dimension:** A correctly attributed quote cited to the wrong URL or paragraph belongs to D4.

**Annotator note:** An independence error counts even when the claim turns out to be true. What D3 judges is the claimed corroboration.

---

## D4 Traceability

### PASS
- **Observable:** "[S3] *Fieldnote Weekly*, 2025-03-02, ¶6: 'we tracked live, no click, over eleven days'." A non-producer reader finds this in the preserved capture almost immediately, and the excerpt is verbatim.
- **Verdict reason:** The passage is recovered, time-to-locate is short, and excerpt fidelity is exact.
- **Boundary move:** Drop the paragraph locator and paraphrase inside the quotation marks. That gives BORDERLINE.

### BORDERLINE (use / use after fixes)
- **Observable:** A central claim is cited to a 6,000-word interview URL with no locator. The text reads: "'no click track; eleven days live'". The reader finds the passage after scanning, and the meaning is preserved but the wording is not verbatim.
- **Verdict reason:** The passage is recovered, but time-to-locate is long and fidelity is imperfect. The meaning holds.
- **Boundary move:** Add ¶6 and the verbatim words to reach PASS. Make the passage unrecoverable or meaning-changing to reach FAIL.

### FAIL
- **Observable:** Central claims are cited as a block, "[S1–S5]". One quoted line is not present in the preserved capture or on the live page, and no locator is given. The pilot's location-less quote is this pattern.
- **Verdict reason:** Passage recovery fails for central claims. It is **not G2**: non-recovery alone is classified as unsupported, incorrect or unassessable (§3, G2). It would be G2 only if adjudication established invention, for example by showing that the quoted article never existed.
- **Boundary move:** Give each central claim its own source and locator, with an excerpt the reader can recover. That gives BORDERLINE.

**Not this dimension:** If the passage is found but says less than the claim, that belongs to D2 (unsupported) or D5 (overstatement).

**Annotator note:** Check fidelity against the harness capture of the cited URL, and record the producer's received text separately (§3 preservation). Sometimes an excerpt matches the summary the producer received but not the page. Record that as a fidelity miss, and as a D5 issue if the excerpt was presented as source text.

---

## D5 Provenance communication

### PASS
- **Observable:** "Read in primary: Northlight liner notes PDF, engineer Ines Darrow. Relayed: *Quarter Review* says 'recorded in a lighthouse', citing the label bio (bio not retrieved). Conflicting: release month March (label) vs April (*Fieldnote*); unresolved."
- **Verdict reason:** All three levels are clear from the wording. There is no overstatement or understatement, and the uncertainty is stated.
- **Boundary move:** Present one search-snippet claim as "per *Fieldnote*" without saying it was a snippet. That gives BORDERLINE.

### BORDERLINE (use / use after fixes)
- **Observable:** "Per *Fieldnote Weekly*, the record was cut in eleven days." The trace shows that only a search snippet was received. The claim is later found supported.
- **Verdict reason:** This is a mild overstatement: the claim reads as read in primary but was relayed. It is not consequential to accuracy, but the critic would believe the claim was verified when it was not.
- **Boundary move:** Add "(search snippet only)" to reach PASS. Add "Confirmed" and drop a known conflict to reach FAIL.

### FAIL
- **Observable:** "Confirmed: recorded in a lighthouse." Only relaying sources were retrieved. The note also says "Credits unverified; recheck" for credits that were read in the primary liner notes. A conflict between release months is silently resolved to one month.
- **Verdict reason:** This shows consequential overstatement, misleading understatement and hidden uncertainty together. It is **not G9**: the lighthouse claim was adjudicated supported, and G9 requires an unsupported claim. It is **not G3b**: the note does not state that it read the bio. It would be G9 if a central claim were unsupported and presented as verified. It would be G3b if the note said "read in the Northlight bio" and the evidence established that it was not read.
- **Boundary move:** Reword to "relayed", mark the credits as read in primary, and state the conflict. That gives PASS.

**Not this dimension:** A relayed claim attributed to the wrong speaker class (for example, label bio presented as an interview) belongs to D3, or to G5 if central.

**Annotator note:** If a source was received only as a model-processed fetch summary, flag where it sits among the three levels for the owner. See Contract friction 2.

---

## D6 Credits and editions

### PASS
- **Observable:** "Distributor row, standard edition (accessed 2026-…): T4 'Background Vocals – Juno Quell'; T7 'Co-Producer – Ines Darrow'. Darrow holds a producer-class role on 3 of 10 standard tracks (counted: Producer, Co-Producer; excluded: Additional Production; source above)."
- **Verdict reason:** Role strings, tracks and edition match a named authoritative row. The aggregate states its role, numerator, denominator, exclusions and source.
- **Boundary move:** Normalise one role string and drop the exclusions line. That gives BORDERLINE.

### BORDERLINE (use / use after fixes)
- **Observable:** "T4 vocals – Juno Quell" (the row says "Background Vocals"). The aggregate reads "Darrow: producer-class on 3/10", with no exclusions stated. It is used only descriptively.
- **Verdict reason:** Role precision is slightly degraded and the aggregate is incompletely disclosed. The aggregate is not a premise of a central claim.
- **Boundary move:** Restore the original strings and add the exclusions to reach PASS. Substitute roles and remove the edition to reach FAIL.

### FAIL
- **Observable:** Credits come from a single encyclopedia entry with no edition named. It says "T7 producer: Darrow", but the row says "Additional Production". T12 (deluxe only) is credited as part of the album. This is the pilot's role-narrowing and single-encyclopedia pattern.
- **Verdict reason:** Role, track and edition precision all fail, and the credits are not anchored to a named authoritative row. It is **not G7**: no aggregate is used as a premise of a central claim. It would be G7 if the note said "Darrow produced most of the album" without role, denominator or source and used that as the premise for a central claim. If the T7 role were adjudicated *incorrect* rather than *imprecise* and presented as established, the owner would assess it under G4.
- **Boundary move:** Use the Distributor row for the standard edition with its original strings. That gives BORDERLINE or PASS.

**Not this dimension:** Locking the whole note onto the wrong edition belongs to D1, or G1 if undisclosed.

**Annotator note:** These anchors do not decide which row is authoritative. Record the row the note used, and apply the scoring manual's rule.

---

## D7 Omissions

### PASS
- **Observable:** The fictional frozen top-3 is: (1) release identity and edition, (2) principal credits, (3) the creator's statement on the title. All three are captured with the correct substance and scope. The note also says: "T3 sample provenance: not found (searched Distributor row, liner notes, two interviews); unresolved."
- **Verdict reason:** Essential recall is complete. The gap is disclosed, reported separately, and not counted as captured.
- **Boundary move:** Turn one captured essential into a disclosed gap despite an accessible source. That gives BORDERLINE.

### BORDERLINE (use / use after fixes)
- **Observable:** "No creator explanation of the title found (searched: *Fieldnote* interview, Northlight bio)." The retrieved *Fieldnote* interview does contain it. This is the pilot's under-read-then-declared-absent pattern, worded as not found.
- **Verdict reason:** One top-3 item is a disclosed gap, so it is not captured and not silent. The note points the critic to where it is.
- **Boundary move:** Extract the statement with its scope to reach PASS. Omit any mention of the title question to reach FAIL (a silent miss).

### FAIL
- **Observable:** The note never addresses the title question. The statement is in a retrieved interview. Separately, a credit summary covers only T1–T5 but is presented as the album's credits, so its scope is wrong and it is not captured.
- **Verdict reason:** There is one silent top-3 miss and one essential that is not captured because of scope. It is **not G6**: the note makes no absence claim. It would be G6 if the note said "Quell has never explained the title."
- **Boundary move:** Disclose the gap with the search path. That gives BORDERLINE.

**Not this dimension:** An essential that is captured correctly but buried in an appendix belongs to D9 and D11.

**Annotator note:** A paraphrase counts as captured only if its scope matches. Post-exposure essentials are reported separately from the frozen top-3 (§5.3).

---

## D8 Musical context

### PASS
- **Observable:** "Lead: *Low Signal* (2021). Same co-producer (Distributor row). Quell calls *Ledger* 'the answer to *Low Signal*' (*Fieldnote* ¶9). Relationship: creator-stated continuity. Whether the records sound continuous is a listening question for the critic."
- **Verdict reason:** The context is specific to this album, the relationship type is correct, there is a concrete supported reason, and no conclusion is presupposed.
- **Boundary move:** Loosen the relationship type or add an evaluative adjective. That gives BORDERLINE.

### BORDERLINE (use / use after fixes)
- **Observable:** "Influenced by Ada Brenn (they toured together, *Quarter Review*); a clear maturation from *Low Signal*."
- **Verdict reason:** The reason (touring together) is concrete and supported. But "influenced" overstates the relationship type, and "clear maturation" leans toward a conclusion.
- **Boundary move:** Change the wording to "toured with" and remove "clear maturation" to reach PASS. Remove the touring reason to reach FAIL.

### FAIL
- **Observable:** "*Ledger* is best understood as Quell's reckoning with her folk roots, in the line of Ada Brenn's *Coastline*: a mature step beyond her debut."
- **Verdict reason:** No reason is given for the comparison, there is no support, the relationship type is unstated, and it presupposes the critic's interpretation and verdict. It is **not G3a**: it contains no sonic description. It would be G3a if it said "the fingerpicked guitars clearly echo Brenn" as the note's own observation without permitted audio access.
- **Boundary move:** Give a documented reason and a neutral relationship type. That gives BORDERLINE.

**Not this dimension:** Sonic description presented as the producer's own observation belongs to G3a.

**Annotator note:** Usefulness is rated by the owner during the task. Annotators score only purpose, relationship type, support and presupposition.

---

## D9 Selection

### PASS
- **Observable:** The core prose holds identity, credits, statements, context leads and gaps, each stated once. The appendix holds the source list and credit table, and the prose does not repeat them.
- **Verdict reason:** Across the whole deliverable, almost all inspected units are useful, with little redundancy or irrelevance.
- **Boundary move:** Add a "Key takeaways" block that restates the body. That gives BORDERLINE.

### BORDERLINE (use / use after fixes)
- **Observable:** The release facts appear in the summary, the body and the closing takeaways. One paragraph covers Quell's unrelated podcast.
- **Verdict reason:** There are some redundant and irrelevant units, but the useful content is intact and easy to find.
- **Boundary move:** Cut the restatements to reach PASS. Add large irrelevant blocks and repeated caveat paragraphs to reach FAIL.

### FAIL
- **Observable:** There are paragraphs on Northlight's corporate history and other artists' chart runs. The same caveat appears in each section, the release date is stated four times, and *Quarter Review*'s score is listed with no stated purpose. The note is far beyond length with no stated reason, which matches pilot behaviour.
- **Verdict reason:** Redundant and irrelevant units make up a large share of inspected units, including the appendices.
- **Boundary move:** Remove the irrelevant blocks and ritual repetition. That gives BORDERLINE.

**Not this dimension:** A review's judgment presented as a finding is a §4.5 reception defect, and belongs to D3 if the speaker class is mislabelled.

**Annotator note:** Count substantive units, not sentences. Splitting a claim into parts earns no credit. Appendices count.

---

## D10 Collection efficiency and stopping (trace)

### PASS
- **Observable:** The trace moves from identity to credits to interviews to a conflict check. One fetch fails with a 403, and the next call retrieves an archived copy. The last two searches check the release-month conflict.
- **Verdict reason:** There are no repeated identical failures, and each step adds yield. The late searches are conflict-checking, which §4 says is not waste.
- **Boundary move:** Retry the 403 URL twice more before switching. That gives BORDERLINE.

### BORDERLINE (mixed practice)
- **Observable:** The same 403 URL is retried three times. There are several near-duplicate queries. The yield curve is flat across the last third, apart from one conflict check.
- **Verdict reason:** There is some repeated identical failure and a flat tail, but collection still progresses.
- **Boundary move:** Remove the retries to reach PASS. Turn the retries into a loop to reach FAIL.

### FAIL
- **Observable:** One failing URL is retried throughout the run. Queries cycle through the same terms, and most of the wall time comes after the last new source was retrieved.
- **Verdict reason:** Repeated identical failures, a flat yield curve and no clear stopping point.
- **Boundary move:** Switch after the first failure and stop once yield is exhausted. That gives BORDERLINE.

**Not this dimension:** A note that calls a source "unavailable" when the trace shows it was never requested belongs to D5 (provenance and understatement). It belongs to D7 if it hides an accessible essential. This was the pilot's fabricated failure history.

**Annotator note:** Without traces, D10 is N/A, not FAIL.

---

## D11 Owner burden (task record)

### PASS
- **Observable:** The owner reads the note (R) and spot-checks central claims through the excerpts, locating them quickly (V). They make one small correction (F), run one independent search on a listening-inquiry question, and reach the outline.
- **Verdict reason:** Most active work is reading and light verification. Correction and independent searching are small.
- **Boundary move:** Make the owner re-derive one section from the sources. That gives BORDERLINE.

### BORDERLINE (mixed practice)
- **Observable:** The owner re-derives credits from the Distributor row because role strings were normalised, and re-reads two interviews to settle unclear speakers. They reach the outline.
- **Verdict reason:** Some sections save work. Others need re-verification and correction comparable to doing the research.
- **Boundary move:** Preserve roles and speakers to reach PASS. Add a correction to an attribution already drafted into the outline, plus redoing the essentials, to reach FAIL.

### FAIL
- **Observable:** The owner discards the note's credits and attributions, researches most essentials independently, and goes back to fix a misattribution already in the outline.
- **Verdict reason:** Active work is dominated by independent searching and correction.
- **Boundary move:** Make credits and attributions usable with light verification. That gives BORDERLINE.

**Not this dimension:** Evaluation-only audit time is reported separately. A factual misdirection is counted under §8.3. Comparison with the baseline arm happens in §8, not here.

**Annotator note:** These anchors describe what the work was made of, not totals. Whether burden is lower than baseline is decided in §8.

---

## Contract friction

1. **D1 level mapping and gate overlap.** §4 gives the metric levels correct / correct with disclosed ambiguity / wrong, but does not map them onto pass / borderline / fail. My anchors use the wording "correct or correct with disclosed ambiguity" at PASS, and place incomplete claim-level disclosure at BORDERLINE. That is my reading; §6 should confirm it. A central, undisclosed "wrong" lock is already G1, so a non-gate D1 FAIL only exists for disclosed wrong locks or wrong-edition material that is peripheral only.
2. **D5 levels and processed retrieval.** §4 D5 does not say where a model-processed fetch summary or a search snippet of a primary page sits among "read in primary / relayed / unconfirmed". The pilot shows this matters, but the pilot's amendment 1 is a prompt proposal, not contract. My anchors flag the case to the owner and do not resolve it.
3. **G4 and *imprecise*.** G4 names "incorrect". §2 treats *imprecise* as a separate status. Whether a central imprecise claim presented as established falls under G4 is not stated. My anchors keep imprecision under D2 and D6 and refer adjudication to the owner.
4. **Severity.** S1–S3 are defined only in the scoring manual, so the D2 anchors cannot use severity labels.

## Self-check

The anchors I'm least sure of:
- **D1 FAIL:** it depends on friction 1, and the non-gate space is narrow.
- **D5 BORDERLINE:** it uses a snippet case whose level is not settled (friction 2).
- **D6 FAIL:** whether it is a dimension failure or G4 depends on the imprecise-vs-incorrect adjudication (friction 3).
- **D3 FAIL and D2 BORDERLINE:** both depend on a centrality call under test (d), which another adjudicator could make differently.
- **D11 overall:** without a baseline, "poor practice" is hard to judge on its own.