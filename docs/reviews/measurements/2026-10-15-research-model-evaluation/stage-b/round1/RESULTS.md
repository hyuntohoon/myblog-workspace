# Stage B round 1 — results (2026-10-16)

Scope: `ROUND.md`, predeclared and committed before any output (`45e3856`). This is a development round. Its verdict is a model-proxy development judgement, not an acceptance-v1 pass.

## Verdict: P1 does **not** advance

Of the four predeclared conditions (`ROUND.md` §7), two fail and one is open:
- **(a) fails.** Three of the four P1 outputs have a D1–D7 FAIL from at least one reviewer after calibration.
- **(b) open.** Three gate allegations on P1 outputs are unresolved. The owner deferred adjudication in chat on 2026-10-16, because it cannot change the verdict: (a) and (c) already fail.
- **(c) fails.** P1 has more FAILs than P0 in two of the four cells.
- **(d)** is the defect list below.

Round 2 has to be predeclared separately. Nothing below is a pass.

## What ran

| Part | Result |
|---|---|
| Fidelity check of P1 before freeze (`freeze-check/`) | 2/2. Both MATERIAL OBJECTION with replacement text, applied once. P1 frozen at sha256 `1b8fb9b6…`. |
| Generations (`runs/`) | **8/8 success**, one dispatch each, no reruns. 158–391 s. |
| Per-output blind audits (`review/runs/*-review-S0?`) | **16/16 success**. Astra 112–137 s, Claude 120–174 s. |
| Comparative calibration (`review/runs/*-comparative`) | 2/2 success |

Two operational events, neither of which caused a redispatch:
- **Lane restart.** The generation lanes were first started under a 30-minute session monitor. Its lane shells were killed while the first two runs were in flight; both runner processes finished normally. A resumable lane then continued and never redispatches a claimed run ID.
- **Mis-split review command.** The first review-lane invocation passed all eight labels as one argument. The runner rejected the ID before any claim, so no dispatch happened (`review/dispatch-*` logs of that attempt were discarded with the empty manifests).

## Calibrated levels (D1–D6; D7 is not assessable)

Both reviewers independently moved D7 to not-assessable in calibration. A development round has no frozen top-3 map, so omission recall cannot be judged against the anchors. FAIL counts are summed over both reviewers.

| Cell | Label | Astra D1–D6 | Claude D1–D6 | FAILs | Gate allegations (reviewer) | Chars | Web calls |
|---|---|---|---|---:|---|---:|---|
| Claude CLI · Gemini · **P0** | S04 | B F B B F F | P B B B B F | 4 | Astra G4 (high) + G9 (med); Claude G3b (low) | 6,955 | 16 S + 22 F |
| Claude CLI · Gemini · **P1** | S03 | P P P F F F | P B P P B F | 4 | — | 12,446 | 25 S + 22 F |
| Claude CLI · 2000 TAPE · **P0** | S02 | B B P B F P | P B P P B B | 1 | Astra G9 (med) | 7,073 | 11 S + 18 F |
| Claude CLI · 2000 TAPE · **P1** | S06 | P F P B F B | P B P B P B | 2 | Astra G4 (high); Claude G4 (med) | 9,012 | 10 S + 19 F |
| Codex · Gemini · **P0** | S07 | P B P P P P | P B P B P B | 0 | — | 7,540 | 13 |
| Codex · Gemini · **P1** | S05 | P P P P P P | P P P P P B | 0 | — | 10,633 | 9 |
| Codex · 2000 TAPE · **P0** | S01 | B B P P P P | P P P P P B | 0 | — | 5,125 | 8 |
| Codex · 2000 TAPE · **P1** | S08 | B F P F P F | P P P P P P | 3 | Astra G4 (high) | 7,546 | 8 |

P = PASS, B = BORDERLINE, F = FAIL. "S"/"F" in the last column are WebSearch and WebFetch calls.

**Condition (c), per cell (P1 FAILs vs P0 FAILs):** Claude/Gemini 4 vs 4 (meets); Claude/2000 TAPE 2 vs 1 (**worse**); Codex/Gemini 0 vs 0 (meets); Codex/2000 TAPE 3 vs 0 (**worse**).

**Reviewer agreement is weak on FAILs.** Of the 14 FAIL marks, 12 are Astra's. Claude agrees only on D6 for S03 and S04. The S08 split (Astra 3 FAILs, Claude 0) hinges on one sentence; see the gate allegations below. Under §7 an unresolved reviewer disagreement on a FAIL counts as a FAIL.

## Gate allegations on P1 outputs — unresolved (owner deferred adjudication)

| Label (cell) | Gate | Claim | Orchestrator's source check |
|---|---|---|---|
| S08 (Codex · 2000 TAPE · P1) | G4, Astra, high | ② C2: "믹싱·마스터링은 각각 전곡에 MILLENNIUM·SUDO가 기재된다" | Genie album page (fetched 2026-10-16): "All Tracks Mixed by MILLENNIUM, SUDO / All Tracks Mastered by MILLENNIUM, SUDO". Read as "each role lists both", the sentence is correct; read as "respectively", it is wrong. The wording is ambiguous, which points to imprecise rather than established incorrect. |
| S06 (Claude CLI · 2000 TAPE · P1) | G4, Astra, high | ④-2: the CD edition is "the only route" to check credits | Astra found per-track roles and engineers on two accessible distributor pages. This is the same exclusive-scope pattern that P1 §6 targets, applied to a research-path claim. Not checked further. |
| S06 | G4, Claude, medium | ② C7: track 13 artist string "HAON & KC" | Claude's live read shows four names; both sides rely on model-processed fetches. Needs a direct look at the page. |

P0 outputs also carry allegations (S04 ×3, S02 ×1). They are recorded in the per-output reports and are not adjudicated here.

## (d) Pilot recurring defects, per P1 output

"Present" means at least one reviewer marked it present. Defect numbers are those in `pilot-final-results.md`.

| Defect | Claude · Gemini P1 | Claude · 2000 TAPE P1 | Codex · Gemini P1 | Codex · 2000 TAPE P1 | Same cells under P0 |
|---|---|---|---|---|---|
| 1 Narration → direct speech | – | – | – | – | none |
| 2 Snippet/summary labelled source-verified | **present** | – | – | – | both Claude-lane P0 outputs |
| 3 Retrieved sources under-read | – | **present** | – | – | Claude · Gemini P0 |
| 4 Roles narrowed / single encyclopedia | – | – | **present** | **present** | both Claude-lane P0 outputs |
| 5 Spurious or unchecked scope conflicts | **present** | **present** | – | – | both Claude-lane P0 outputs |
| 6 Numerator inconsistency | **present** | **present** | – | – | both Claude-lane P0 outputs |
| 7 Reviews as factual evidence | – | – | – | – | none |
| 8 Length / ritual repetition | **present** | **present** | **present** | **present** | 3 of 4 P0 outputs |

## What the round shows

1. **P1 made the notes longer in every cell:** +27 % to +79 % characters. Defect 8 is present in all four P1 outputs. The amendment restricting the length target to core prose (#6) did not offset the added recording duties (#1, #3, #5). Both reviewers name ritual repetition: identical checklist rows, repeated gap statements and access limits.
2. **P1 reduced provenance defects in the Claude lane only partly.** Defect 2 persists in Claude · Gemini P1. Both reviewers attribute it mainly to the harness: WebFetch returns model-processed text, and the producer still labels it `[원문 확인]`. Neither Codex output shows defect 2 under either prompt.
3. **The new failures are exclusive-scope and credit-transcription errors on the sparse Korean album.** They are "the only route" claims, ambiguous role sentences and incomplete transcription of a named credit row. Claude's calibration names incomplete credit-row transcription as the most frequent D6 defect across all eight notes.
4. **Codex · P0 had no FAIL in either album.** Within this one-run-per-cell design, the strongest observed configuration is the control prompt in the Codex lane. One run per cell cannot separate a prompt effect from run-to-run variance. That limit applies to every comparison in this table.

## Harness findings (carry into round 2)

- **The Claude CLI lane is not instruction-clean.** Every Claude-lane run, producer and reviewer, fires the user's SessionStart hooks and loads the global `~/.claude/CLAUDE.md` (412 bytes), despite the isolated temporary cwd. One reviewer output shows it: Claude's comparative calibration ends by recommending a "Fable subagent review" from those global rules. The same runner produced the pilot and Stage A Claude-lane records, so they share this exposure. Round 2 should run the Claude lane with user settings and hooks excluded, and record that it did.
- **P1's "quote the tool's failure text verbatim" rule leaks the harness identity into notes.** One note quotes "Claude Code is unable to fetch from …". Review copies replace it with the same neutral marker the pilot used for traces (`review/build-report.json`); `runs/` keeps the original bytes.
- **Codex traces carry `thumbnail_url` on the vendor's image CDN.** These are stripped from review copies. Trace structure still reveals the producer family, as in the pilot.

## Proposed direction for round 2 (not predeclared, needs owner confirmation)

The two reviewers' calibration proposals overlap on four points, each a definition or deletion, not an added rule:
1. **Access labels.** `[원문 확인]` applies only to unprocessed page text the tool returned. A model-processed fetch is always a relayed source.
2. **Credit transcription.** Copy a named row completely for the target track, or declare a selective copy and what it omits. Preserve joint roles. Apply the scope test to "only", "none" and "no conflict" claims, including claims about research paths.
3. **Gaps.** Before recording a gap, name the received material checked and why it does not answer; a relayed lead is recorded as a lead, not a gap.
4. **Compression.** A checklist column that is identical for every track becomes a one-line legend. A gap or access limit is recorded once and referenced elsewhere.

Round 2 should also fix the Claude-lane harness and use **two runs per cell** for any contrast whose effect is expected to be smaller than run-to-run variance. Albums, budget and decision rule need a fresh predeclaration.

## Publication

The workspace repository is public. On the owner's decision (chat, 2026-10-16), one line was redacted before publication: the owner's collection signal, which lists bucket names in the poller catalog block. It appears only in the Gemini Rights input and in every record that embeds it. `PUBLICATION-REDACTIONS.json` lists the 17 affected files with the hashes of the dispatched bytes, which the round's other hash records also refer to. Originals are kept outside the repository.

## Limits

- One run per cell, two albums, model reviewers only, no owner audit. Uncalibrated anchors; D7 is not assessable without a frozen map.
- Reviewers saw anonymous labels. The prompt condition was withheld, but P1-specific labels such as `[요약 경유]` can reveal it.
- Gemini Rights is pre-cutoff and the pilot album, so model memory and pilot exposure can contribute. 2000 TAPE had 0/20 Genius matches.
