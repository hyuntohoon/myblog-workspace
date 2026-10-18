# Stage B round 2 — results (2026-10-18)

Scope: `ROUND.md`, predeclared and owner-confirmed before any output, with the §10 (pause) and §11 (early resume) amendments. This is a development round. Its verdict is a model-proxy development judgement, not an acceptance-v1 pass.

## Verdict: P2 does **not** advance

Of the five predeclared conditions (`ROUND.md` §7):
- **(a) fails.** Two P2 outputs carry an **agreed** FAIL after calibration (both reviewers FAIL the same dimension): Claude CLI · 2000 TAPE · r1 on D5, and Claude CLI · Gemini · r2 on D2, D4 and D5. No source confirmation was needed to reach this, so none of the single-reviewer FAILs was checked against sources.
- **(b) open.** Five gate allegations on four P2 outputs are unresolved (table below). Adjudication cannot change the verdict, because (a) and (c) already fail.
- **(c) fails in both Claude CLI cells and holds in both Codex cells.** P2 vs P0 FAILs: Claude/Gemini 11 vs 8, Claude/2000 TAPE 7 vs 4, Codex/Gemini 0 vs 1, Codex/2000 TAPE 0 vs 1.
- **(d)** is the defect table below.
- **(e) holds, narrowly.** Pooled median `output.md` length: P2 7,504.5 chars vs P0 6,835.5 chars = **1.098×** (limit 1.10×).

Nothing below is a pass. A round 3 has to be predeclared separately (proposal at the end).

## What ran

| Part | Result |
|---|---|
| Generations (`runs/`) | 16/16 cells with a usable output: Claude 8/8, Codex 4/4 r1 + 4/4 `-resume` r2. `gx-P0-gemini-rights-r2` stays `rate_limited` and was not reviewed (§10). |
| Blind label draw (`review/blind-key.json`) | 2026-10-18 10:48:58Z, one `secrets.SystemRandom().shuffle` over the 16 outputs plus the sentinel. `build-report.json`: 0 identity hits in notes or traces; one harness error string in one note replaced by the neutral marker. |
| Per-output blind audits (`review/runs/*-review-S??`) | **34/34 success**, one dispatch each, no reruns. Astra 91–135 s, Claude 95–166 s. |
| Comparative calibration (`review/runs/*-comparative`) | 2/2 success. Astra 91 s, 6 level changes; Claude 147 s, 5 level changes. |
| Claude-lane cleanliness (§2) | All 18 Claude review dispatches: 0 hook events, no `memory_paths`, tool set exactly WebFetch + WebSearch. |

One harness edit, no scope change: `run_review_lane.sh` named the subscription-guard source as a session scratchpad path that no longer existed. It now uses `~/.local/share/myblog-research/shared-db-guard/src`, the same guard the generation and resume runs used (§10). That checkout is one shared_db commit behind `origin/main`; the commit in between (V64 lyrics reports) does not touch `myblog_shared_db/llm/`, so the guard code is the same. The comparative step uses `review/run_comparative.sh`, which writes the same manifest shape as round 1's comparative manifests.

## Reviewer control (sentinel)

The sentinel (round-1 Claude CLI · Gemini · P1, D6 FAIL agreed in round 1) drew label S07.

| Reviewer | Sentinel D1–D6 after calibration | Control met? |
|---|---|---|
| Astra | P P P F F F | yes (D6 FAIL) |
| Claude | P B B P B B | yes (D6 BORDERLINE), but with no FAIL on any dimension |

Both reviewers meet the predeclared control. Claude is the more lenient of the two: it gave the sentinel no FAIL at all, where both reviewers had agreed a D6 FAIL in round 1. Read Claude's PASS and BORDERLINE levels with that caveat. The sentinel is excluded from every tally below.

## Calibrated levels (D1–D6; D7 not assessed)

P = PASS, B = BORDERLINE, F = FAIL. FAILs are summed over both reviewers. Web calls: S = WebSearch, F = WebFetch (Claude CLI); Codex counts are `web_search` items.

| Cell | Run | Label | Astra | Claude | FAILs | Agreed FAIL | Chars | Web calls |
|---|---|---|---|---|---:|---|---:|---|
| Claude CLI · Gemini · **P0** | r1 | S08 | P F P F F F | P B P P B B | 4 | – | 7,068 | 17 S + 12 F |
| | r2 | S17 | P F P F F F | P B B P B B | 4 | – | 5,431 | 20 S + 18 F |
| Claude CLI · Gemini · **P2** | r1 | S09 | P F P F F F | P B P P B B | 4 | – | 8,393 | 11 S + 19 F |
| | r2 | S15 | P F P F F F | P F B F F B | 7 | **D2, D4, D5** | 7,810 | 16 S + 20 F |
| Claude CLI · 2000 TAPE · **P0** | r1 | S11 | P B P F F P | P B P B B P | 2 | – | 7,419 | 7 S + 13 F |
| | r2 | S04 | P F P B F P | P B P B B B | 2 | – | 6,744 | 17 S + 13 F |
| Claude CLI · 2000 TAPE · **P2** | r1 | S13 | P F P F F P | P B B P F P | 4 | **D5** | 7,871 | 11 S + 11 F |
| | r2 | S10 | B F B F B F | P B P B P B | 3 | – | 7,246 | 10 S + 13 F |
| Codex · Gemini · **P0** | r1 | S14 | P B P P P B | P P P P P B | 0 | – | 8,119 | 13 |
| | r2 | S03 | P B P P B B | P B P F P B | 1 | – | 6,927 | 8 |
| Codex · Gemini · **P2** | r1 | S05 | P P P P P P | P P P P P P | 0 | – | 7,713 | 11 |
| | r2 | S12 | P P P P P P | P B P B P P | 0 | – | 7,296 | 9 |
| Codex · 2000 TAPE · **P0** | r1 | S01 | P P P F P P | P P P P P P | 1 | – | 5,596 | 10 |
| | r2 | S06 | P B P P B P | P P P B B P | 0 | – | 5,541 | 8 |
| Codex · 2000 TAPE · **P2** | r1 | S02 | P P P P P P | P P P P P P | 0 | – | 5,884 | 8 |
| | r2 | S16 | P P P P P P | P P P P P P | 0 | – | 4,997 | 8 |

**Condition (c), per cell, both runs shown (P2 vs P0 FAILs):** Claude/Gemini 4 + 7 = 11 vs 4 + 4 = 8 (**worse**); Claude/2000 TAPE 4 + 3 = 7 vs 2 + 2 = 4 (**worse**); Codex/Gemini 0 + 0 vs 0 + 1 (meets); Codex/2000 TAPE 0 + 0 vs 1 + 0 (meets).

**Codex r1 vs r2** (date and CLI-version confound, §10/§11; r1 on 0.162.0-alpha.17.2, r2 on 0.163.0-alpha.10.2): P0 FAILs r1 1, r2 1; P2 FAILs r1 0, r2 0. No visible shift between the two halves.

**Length, per cell (reported, not judged):** Claude CLI medians P2 7,840.5 vs P0 6,906 (1.135×); Codex medians P2 6,590 vs P0 6,261.5 (1.052×).

**Reviewer agreement on FAILs.** Of 32 FAIL marks on the 16 outputs, 27 are Astra's and 5 are Claude's. The four agreed FAILs are all on Claude-lane P2 outputs. Two of them (S13 D5, S15 D5) exist because Claude's comparative moved those levels from BORDERLINE to FAIL; Claude's S15 D2 and D4 FAILs were already in its per-output report. Astra's comparative raised D4 to FAIL on five notes (S09, S10, S11, S13, S17); all five are Claude-lane outputs, under both prompts.

## (b) Gate allegations on P2 outputs — unresolved

| Label (cell, run) | Gate, reviewer, confidence | Location |
|---|---|---|
| S09 (Claude CLI · Gemini · r1) | G4, Astra, high | ③ 편중: tracks 8 and 10 said to have no track mention in S1–S4 |
| S09 | G6, Astra, high | ③ 편중: information that the summarised fetch did not return is stated as absent from the source |
| S10 (Claude CLI · 2000 TAPE · r2) | G4, Astra, medium | C4 track position and appendix S11: the claim that YesAsia lists XYZ as track 9 |
| S13 (Claude CLI · 2000 TAPE · r1) | G4, Astra, medium | ② C4 title marked [상충], and the closing sentence leaving KC's artist/label status unresolved |
| S15 (Claude CLI · Gemini · r2) | G4, Astra high + Claude medium | K7 family-vocal conflict claim; ③ Mercury row; ④ official-credit follow-up |

S15's allegation is the only one both reviewers raised, independently, at the same location. No Codex-lane P2 output has a gate allegation. P0 outputs also carry allegations (S04, S08, S11, S17 from Astra; S03, S17 from Claude); they are in the per-output reports and are not adjudicated here.

## (d) Pilot recurring defects, per P2 output

"Present" means at least one reviewer marked it present. Defect numbers are those in `pilot-final-results.md`.

| Defect | Cl·Gem r1 | Cl·Gem r2 | Cl·TAPE r1 | Cl·TAPE r2 | Gx·Gem r1 | Gx·Gem r2 | Gx·TAPE r1 | Gx·TAPE r2 | Same cells under P0 (8 outputs) |
|---|---|---|---|---|---|---|---|---|---|
| 1 Narration → direct speech | – | – | – | – | – | – | – | – | 1 (Cl·Gem r2) |
| 2 Snippet/summary labelled source-verified | – | – | **present** | **present** | – | – | – | – | 5: all 4 Claude-lane, Gx·TAPE r2 |
| 3 Retrieved sources under-read | **present** | **present** | **present** | – | – | – | – | – | 3: Cl·Gem r2, Cl·TAPE r2, Gx·Gem r1 |
| 4 Roles narrowed / single encyclopedia | **present** | **present** | – | **present** | – | – | – | – | 5: Cl·Gem ×2, Cl·TAPE r2, Gx·Gem ×2 |
| 5 Spurious or unchecked scope conflicts | **present** | **present** | **present** | **present** | – | – | – | – | 4: all 4 Claude-lane |
| 6 Numerator inconsistency | – | – | **present** | – | – | – | – | – | 4: all 4 Claude-lane |
| 7 Reviews as factual evidence | – | – | – | – | – | – | – | – | none |
| 8 Length / ritual repetition | **present** | – | – | – | – | – | **present** | – | 4: Cl·TAPE r1, Gx·Gem r2, Gx·TAPE ×2 |

## What the round shows

1. **The environment separates the outputs more than the prompt does.** Codex-lane outputs carry 2 of the 32 FAIL marks, both on P0 and each from one reviewer only. The four Codex · P2 outputs have no FAIL, no gate allegation and at most one recurring defect each. The Claude CLI lane carries 30 FAILs, every agreed FAIL and every P2 gate allegation, under both prompts.
2. **P2's edits help where they target labels and transcription, not scope.** Defect 2 fell in the Claude lane from 4/4 P0 outputs to 2/4 P2 outputs (both Gemini P2 runs are free of it). Numerator inconsistency (6) fell from 4/4 to 1/4. Scope and conflict errors (5) stayed at 4/4. Both reviewers trace them to the missing definition of a comparison unit, which the scope test in edit 2 did not supply. P2 also lengthened Claude-lane notes (1.135× per-cell median) and added under-reading (3) in three of four Claude-lane P2 outputs.
3. **The Claude-lane harness confound is still the main suspect for defects 2 and 3.** WebFetch returns model-processed text. Both comparatives classify these defects as mixed harness/model, and both name truncated or summarised fetches, not read further, as the route to "absent" claims. Safe mode removed the instruction contamination (§2), not this.
4. **The reviewers still differ in strictness, and the sentinel now measures it.** Astra gave 27 of 32 FAILs and failed the sentinel on D6. Claude passed the control only at BORDERLINE and gave the sentinel no FAIL anywhere. Under the round-1 rule (any reviewer's FAIL counts), P0 itself would have failed in all four cells.

## Proposed direction for a round 3 (needs predeclaration and owner confirmation)

These are the points where both comparatives' proposals overlap. Each defines, generalises or deletes an existing rule:

1. **Access label, tightened again.** `원문 확인` only for unprocessed page text the producer received; summarised fetches and snippets get the relay label; the note states the tool output kind once at the top (Astra 1, Claude 1).
2. **Conflict definition.** `상충` only between statements about the same role field, scope (track / album / edition) and time; an absence taken from a truncated snippet or filtered aggregate is "scope difference" or "unconfirmed", never conflict or absence (Astra 3–4, Claude 2).
3. **Numerators derived from one list.** Every coverage or aggregate numerator is counted from the same listed track numbers (Astra 3, Claude 4).
4. **Compression by deletion.** Drop the per-track checklist and the run-metadata lines; list only tracks with gaps or exceptions; write detailed evidence and open status once and reference it (Astra 5, Claude 4).

Not overlapping, so not proposed: Astra's quotation-trace rule (2), Claude's role-string rule for headings and tables (3) and its quotation-context rule (5).

Two questions are outside a prompt round and are recorded for the owner, not decided here:
- **Producer environment.** In both rounds, the strongest configurations ran in the Codex lane (round 1: Codex · P0; round 2: Codex · P2 with zero FAILs). The 2026-10-16 owner decision to confirm in both environments stands; whether the Claude CLI lane's WebFetch confound should be addressed before a round 3, or the lanes judged separately, is for the round-3 predeclaration.
- **Scoring-manual gaps** raised by Claude's comparative (acceptance-v1 §6.1, not prompt matters): how a reviewer-side access block differs from an R5 "retrieval failure"; the D5 level of an understatement with no downstream effect; whether Genius and Wikipedia rows count as an "authoritative row" for D6.

## Publication

The nine Gemini Rights review packets (`review/inputs/S03, S05, S07, S08, S09, S12, S14, S15, S17`) and their 18 review-run `input.txt` copies embedded the dispatched, unredacted Gemini Rights input. The owner-collection line was replaced in all 27 files per §9 and recorded in `PUBLICATION-REDACTIONS.json` with the original hashes. A scan of the whole round directory for the bucket-name tokens, in both plain and JSON-escaped forms, found 0 hits after the redaction. `review/build-report.json` keeps the pre-redaction input hashes, so they match the bytes actually dispatched.
