# Stage B round 3 — results (2026-10-20)

Scope: `ROUND.md`, predeclared and owner-confirmed before any producer output, with the §10 amendment (Codex producer lane discontinued; Astra review lane reduced and run without web), made before any review dispatch. This is a development round. Its verdict is a model-proxy development judgement, not an acceptance-v1 pass.

## Verdict: neither P3 nor P3G advances — length is the only unmet condition in the Claude CLI lane

Claude CLI lane (the lane that continues, §10):

| Condition (§6) | P3 | P3G |
|---|---|---|
| (a) no agreed D1–D6 FAIL | **holds**: Astra FAILs D6 in both runs, Claude rates D6 BORDERLINE | **holds**: r1 Astra FAILs D5, D6 and Claude FAILs D4; no dimension shared |
| (b) no unresolved gate allegation on X | **holds** (none raised) | **holds** (none raised) |
| (c) X FAILs ≤ P0 FAILs (either reviewer, both runs) | **holds**: 2 vs 5 | **holds**: 4 vs 5 |
| (d) pilot defects listed | table below | table below |
| (e) median length ≤ 1.10 × P0 | **fails**: 8,922.5 vs 7,150 chars = **1.248×** | **fails**: 9,315.5 vs 7,150 = **1.303×** |

Codex lane (descriptive only, Claude reviewer alone, §10): every output has 0 FAILs, P0 included, and no gate allegations. Median length relative to P0: P3 1.146×, P3G 0.957×.

Nothing below is a pass.

## What ran

| Part | Result |
|---|---|
| Fidelity check (`freeze-check/`) | Both reviewers rated P3 faithful with no scope creep; both objected to the same P3G line, applied once (ROUND.md §1). |
| Generations (`runs/`) | **12/12 success**, no reruns. Claude CLI 303–385 s, 12–19 searches + 15–23 fetches; every Claude run had 0 hook events, no `memory_paths`, and tools exactly WebSearch + WebFetch. Codex 176–276 s, 9–14 searches. |
| Blind draw (`review/blind-key.json`) | 2026-10-19 14:31:18Z, one `secrets.SystemRandom().shuffle` over 12 outputs + sentinel. 0 identity hits in notes; one trace hit is a wiki named "Codex Gamicus" in search results (S08), left as is. One harness error string in one note neutralised (S01). |
| Per-output audits | **Claude 13/13, Astra 7/7 success** (Astra: Claude-lane outputs + sentinel, no web tool, 0 tool calls). |
| Comparative calibration | 2/2 success. Astra 1 level change, Claude 6. |

The comparative brief said "thirteen for one reviewer, seven for the other". Both reviewers read it as a request to calibrate reports they had not received and said so. Each calibrated only its own set, so nothing was lost, but the wording should name only the reader's own count next time.

## Reviewer control (sentinel = S01)

| Reviewer | Sentinel D1–D6 after calibration | Control (D6 FAIL, §5) |
|---|---|---|
| Astra (no web) | P B P P F F | **met** |
| Claude | P B P P B B | **not met**. As in round 2, Claude gives the sentinel no FAIL on any dimension. |

So Claude's PASS / BORDERLINE levels are lenient in a measured way. Astra's D6 is the opposite problem: without web it FAILs D6 on 6 of its 7 packets (all but S12 = Claude · P0 · r2). It cannot link a credit to an authoritative row it cannot open. Astra's D6 therefore separates outputs very little in this round. Its D5 FAILs (S02, S12 = both P0; S13 = P3G r1) do vary by output.

## Calibrated levels (D1–D6; D7 not assessed)

| Cell | Run | Label | Astra | Claude | FAILs | Chars |
|---|---|---|---|---|---:|---:|
| Claude CLI · **P0** | r1 | S02 | B F P B F F | P B F B B B | 4 | 7,604 |
| | r2 | S12 | P P B P F B | P B P B B P | 1 | 6,696 |
| Claude CLI · **P3** | r1 | S07 | P B P P P F | P B P B P B | 1 | 10,070 |
| | r2 | S11 | P B P B B F | P B P B P B | 1 | 7,775 |
| Claude CLI · **P3G** | r1 | S13 | P B B P F F | P B P F P B | 3 | 9,792 |
| | r2 | S08 | P P P B P F | P B P B B B | 1 | 8,839 |
| Codex · P0 | r1 / r2 | S10 / S05 | – | P P P B P P / P P P P P P | 0 | 6,803 / 6,258 |
| Codex · P3 | r1 / r2 | S06 / S09 | – | P P P B B P / P P P B P P | 0 | 7,230 / 7,738 |
| Codex · P3G | r1 / r2 | S03 / S04 | – | P P P B P P / P P P B P P | 0 | 6,461 / 6,041 |

Gate allegations: two, both on non-candidates. One is on Claude · P0 · r1 (Astra G4 high, a "none" in the checklist that the input contradicts; Claude G5 low). The other is on the sentinel (Astra G9 medium). None is on P3 or P3G.

## Pilot recurring defects, Claude CLI lane (A = Astra, C = Claude; p = present)

| Defect | P0 r1 | P0 r2 | P3 r1 | P3 r2 | P3G r1 | P3G r2 | Edit that targets it |
|---|---|---|---|---|---|---|---|
| 2 Summary promoted to `원문 확인` | A C | A C | A C | – | A C | C | 1 |
| 5 Spurious / unchecked scope conflicts | A C | A | – | – | C | A | 2 |
| 6 Numerator inconsistency | – | – | C | A C | C | – | 3 |
| 8 Length / ritual repetition | – | – | C | C | C | C | 4 |

- **Edit 2 worked.** Scope conflicts went from 3 marks on P0 to 0 on P3.
- **Edit 1 helped once in two runs.** P3 r2 is free of defect 2; r1 is not.
- **Edit 3 backfired.** Numerator inconsistency, absent from both P0 runs, appears in both P3 runs. Counting every numerator "from the ③ checklist" made the checklist the place where counts disagree with the summary.
- **Edit 4 did not shorten the notes.** Claude marked length/ritual repetition in all four P3/P3G outputs, and the notes got longer.

## Genius annotations (P3G vs P3, descriptive)

- **Barely used.** Of the 14 annotations in the block, the producers cited one: [26430067], the Vulture quote about the cough on "Static". The Vulture interview appears in all 4 P3G notes; 3 of them cite the annotation ID directly.
- **Labelled correctly.** Where the original was not read, it is labelled `[DB등재·재인용]`. Where it was read (Codex r1), the note cites the Vulture page, not the annotation. No annotation quotation was presented as the artist's speech.
- **No coverage gain observed.** No reviewer reported new production or context evidence for a track that P3 lacked.
- **Cost.** Claude-lane P3G notes are longer than P3's (median 9,315.5 vs 8,922.5) and carry more FAIL marks (4 vs 2).

On this album, the block's one visible contribution is that lead. Without the block, only one of eight notes found the Vulture interview (Codex · P3 · r2), and no Claude-lane note did. With it, all four did. In one run the lead was followed to the original: Codex · P3G · r1 went from the input annotation to a linked page and then to the Vulture interview (Craig Jenkins, 2022-07-12), read it, and cited specific lines for two claims (`runs/gx-P3G-gemini-rights-r1/output.md:72`). The other three P3G notes kept it `[DB등재·재인용]`. The Claude-lane runs could not reach the original page. The cost is input, length and, in the Claude lane, more FAIL marks.

## Token use

| Part | Input tokens | Output tokens |
|---|---:|---:|
| Codex generation, per note | 621,853–1,317,722 (83–90 % cached) | 4,415–6,662 |
| Astra review, 7 audits (no web) | 327,046 total (43,415–54,056 each) | 20,929 |
| Astra comparative | 33,072 | 2,449 |
| Claude review, 13 audits (cache-inclusive) | 2,910,392 | 147,077 |

For comparison, a round-2 Astra audit with web was 168,395–284,432 input tokens each.

## What the round shows

1. **The remaining blocker in the Claude lane is length, not failures.**
   - P3 cut FAIL marks from 5 to 2 and removed scope conflicts.
   - But P3 · r1 ran to 10,070 chars, and both P3 runs carry Claude's length/repetition mark.
   - The edits that define things worked. The edit that adds a counting rule (3) produced a new defect.
2. **Removing the Codex lane removes the one environment that was already clean.** Every Codex output in rounds 2 and 3 has at most one FAIL mark, mostly zero. The owner's cost decision stands; the Claude lane now has to reach that level on its own.
3. **The no-web Astra lane is cheap but blunt on D6.** It costs about 15–20 % of a web audit, and its D5 still discriminates. Its D6 FAILs nearly everything because it cannot open the authoritative row. Next round: either exclude D6 from Astra's agreed-FAIL counting, or give D6 to the Claude reviewer alone.

## Proposed direction for a round 4 (needs predeclaration and owner confirmation)

Claude CLI lane only (§10). Points where both round-3 comparatives overlap, each a definition, generalisation or deletion:

1. **Access label, by actual tool output** (Astra 1, Claude 1). Claude's version adds a distinct `[가공 요약 경유]` status for model-processed fetches. That is a new label and would need its own check.
2. **Attribution per claim to the document actually received** (Astra 2, Claude 4). A medium named only by a search summary is "the summary attributes this to X", not X. Scope qualifiers ("part of", track vs album) stay verbatim.
3. **Credit role strings verbatim, including in summary columns and legends** (Astra 3, Claude 3).
4. **Delete repeated access/verification explanations and memory-based access counts** (Astra 5, Claude 5).

Plus, from this round's data rather than the comparatives:

5. **Revert edit 3.** Return to P2's numerator wording.
6. **Length.** P3 keeps P2's checklist and gains text. Round 4 needs a deletion large enough to bring the median back under 1.10× P0, judged in the same pass.

Open for the owner, not decided here:
- whether the annotation arm continues: one real lead gained (Vulture, followed to the original once, in the Codex lane) against longer notes and more FAIL marks in the Claude lane;
- how D6 is counted for a no-web Astra.

## Publication

Every record that embedded the Gemini Rights catalog block had the owner-collection line redacted. Every copy of the annotation block (P3G run inputs, review packets, freeze-check doc4 and its two run inputs) was replaced by a placeholder naming the block's sha256. That is 55 files, listed in `PUBLICATION-REDACTIONS.json` with their original hashes. A scan for the bucket token and for every annotation line, in plain and JSON-escaped forms, found 0 hits. `review/build-report.json` keeps the pre-redaction packet hashes, which match the bytes actually dispatched.
