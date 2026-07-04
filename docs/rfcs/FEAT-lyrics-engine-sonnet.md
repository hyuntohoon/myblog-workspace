# FEAT-lyrics-engine-sonnet: swap the translation poller engine Amazon Translate → Claude Sonnet

- **Status**: in-progress
- **Owner**: 박지훈
- **Created**: 2026-07-05
- **Plan row**: `plan.md` → FEAT-lyrics-engine-sonnet
- **Supersedes**: the 2026-07-04 engine decision in `docs/archive/done/rfcs/FEAT-lyrics-translation.md`
  (decisions log row 3 — "Engine swapped Claude → Amazon Translate")

---

## Goal

The lyrics-translation poller (`scripts/lyrics_translate_poller.py`) translates with headless
**`claude -p --model sonnet`** instead of per-line Amazon Translate, using the benchmark-frozen
의역 prompt (paraphrase, 1:1 line mapping, JSON-only output). Whole-lyric context replaces
context-free per-line MT: consistent register across a track, idioms translated as idioms,
elided subjects restored. The 13 existing `amazon.translate` rows are re-translated in place.
Everything else — queue schema, claim pattern, launchd cadence, fingerprint parity, privacy
bar, viewer — is untouched. No contract, schema, or infra change; workspace `scripts/` +
`tools/` only.

## Non-goals

- **Amazon fallback.** Owner decision 2026-07-05: tracks that still fail after one retry are
  marked `failed` with a diagnostic error; the Amazon Translate code path is **removed**, not
  kept as fallback. (`translate:TranslateText` stays on `claude_aws_manager` — console-managed,
  removal is a separate owner chore if ever wanted.)
- **Corpus-wide batch translation / Anthropic API usage.** Still designated-tracks-only, still
  subscription `claude -p` on the owner's machine (same boundary as genre backfill). No SSM
  anthropic key, no Lambda LLM, no Batch API.
- **Prompt-engineering iterations beyond the frozen prompt.** The benchmarked prompt shipped
  15/15; it is frozen as a constant. Tuning it is a future change that bumps
  `TRANSLATOR_VERSION`.
- **Other models.** Haiku (quality: nuance loss, occasional invented meaning) and Opus
  (quality ≈ Sonnet, no clear win for the cost/limit budget) were benchmarked and not chosen.
  Model swap = one-constant change + `TRANSLATOR_VERSION` bump, future decision.
- **Viewer/backend/contract changes.** `text_ko` semantics are unchanged; the viewer's
  identical-passthrough dedup (front #230) keeps working (already-Korean lines are returned
  verbatim by the prompt contract, same as Amazon's passthrough).

## Current state

(Audited 2026-07-05 against the working tree + prod DB.)

- **Poller**: `scripts/lyrics_translate_poller.py` — launchd every 60s, claim via
  `FOR UPDATE SKIP LOCKED` + 20-min `claimed_at` re-claim window. Flow: load `track_lyrics` →
  `normalize_lyrics` (imported from the LOCAL backend checkout; fingerprint parity by
  construction) → Korean-dominant guard (`failed('korean_source')`) → **per-line Amazon
  Translate** (`translate_lines`: auto→ko, Formality=INFORMAL, hangul-dominant lines pass
  through, `UnsupportedLanguagePair`/`LowConfidence` lines pass through per-line — ws #524) →
  re-insert gaps as `""` → `mark_done` with `model='amazon.translate'`,
  `TRANSLATOR_VERSION='v1'`. Any exception → `mark_failed` (poller stays up).
- **Data**: `track_lyrics_translations` holds exactly **13 rows, all `done|amazon.translate`**
  (the LUX pilot; queried 2026-07-05). `segments` = `[{i, text_ko}]` keyed by normalized
  segment index, gaps `""`.
- **Why Amazon is the current engine**: decisions log 2026-07-04 — headless `claude -p`
  (sonnet ×2 prompts, opus ×1, honest private-use context) **consistently refused**
  full-lyrics translation on copyright grounds; the in-session Berghain 43/43 evidence did not
  replicate headless.
- **New evidence (2026-07-04 benchmark, this RFC's trigger)**: the same headless
  `claude -p` path with a *different prompt shape* — 의역 instruction + numbered lines +
  "JSON array only" output contract — ran **15/15 PASS** (LUX 5 tracks × opus/sonnet/haiku,
  194 non-gap lines): **0 refusals, 0 JSON-parse failures, 0 line-count mismatches, 0
  index-alignment breaks**, including the DE/EN "Berghain" and the 75-line "Porcelana".
  The 07-04 refusal therefore keys on prompt shape, not on headless-vs-in-session.
  Quality (owner-reviewed comparison artifact): Sonnet — consistent register, natural subject
  restoration, no over-paraphrase; chosen over Opus (converges with Sonnet on most lines) and
  Haiku (clips nuance, occasionally invents meaning). Timing: Sonnet 147s / 5 tracks
  sequential (max 43s @ 75 lines) vs Haiku 364s, Opus 189s. Bench inputs/outputs/scorer
  preserved in the 2026-07-04 session scratchpad (`lyrics_bench/`); the prompt is reproduced
  verbatim in Target state.

## Target state

### Engine call (per claimed track)

One `claude -p --model sonnet` subprocess per track (not per line), prompt on stdin,
`timeout` ~300s. Prompt frozen as `PROMPT_HEADER` (benchmark-identical, Korean):

```
각 줄을 한국어로 **의역**해줘 — 축자적 직역이 아니라, 글의 정서와 핵심 의미를 자연스러운
한국어로 옮겨. 단 반드시 원문 1줄 ↔ 번역 1줄로 대응시켜(줄 합치기·재배치·삭제 금지).
이미 한국어인 줄은 그대로 둬. 출력은 오직 JSON 배열만, 설명 금지:
[{"i":<원문 줄번호>,"ko":"<의역>"}]. 원문:
---
1: <non-gap line 1>
2: <non-gap line 2>
…
```

Input lines are the same `non_gap` segments the Amazon path used (normalizer output, gaps
excluded); prompt numbering is 1..N positional, mapped back to segment `i` exactly as today.

### Validation (ported from the benchmark scorer)

Extract the JSON array (code-fence strip → first `[`..last `]`), then require:
`json.loads` succeeds, every item is `{i, ko}`, `len == N`, and the `i`-set == `{1..N}`.
Refusal prose fails extraction and lands in the same failure path — no separate refusal
detector needed for correctness (the error text captures the head of stdout for diagnosis).

### Failure policy (owner decision 2026-07-05: no Amazon fallback)

- **Validation failure** (refusal / bad JSON / count / alignment): retry the engine call
  **once**; second failure → `mark_failed` with `error='engine_validation: <detail (first
  200 chars of stdout)>'`. The row is visible in the viewer as before (`status='failed'`).
- **Transient CLI failure** (non-zero exit with usage/session-limit text, or timeout): do
  **not** `mark_failed` — log and return with the claim left in place; the 20-min stale-claim
  window retries automatically on a later cycle. This distinguishes "Sonnet said no /
  garbled" (terminal) from "subscription budget momentarily exhausted" (self-healing).
- **Everything upstream unchanged**: `source_unavailable`, `korean_source` guards stay.

### Provenance / bookkeeping

- `model` column: **`claude.sonnet`** (alias, mirrors `amazon.translate` naming; the CLI
  resolves the alias to the current Sonnet — see OQ2 on pinning).
- `TRANSLATOR_VERSION`: `v1` → **`v2`** (engine + prompt change).
- `boto3`/`translate` imports, `translate_lines`, and the per-line passthrough logic are
  deleted; the hangul-dominant *track* guard stays (per-line Korean passthrough is now the
  prompt's job, verified in the bench — "이미 한국어인 줄은 그대로 둬").
- Fingerprint computation unchanged (same normalizer, same segments): re-translation does not
  invalidate read-path parity.

### Backfill (13 existing rows)

One-shot local tool `tools/lyrics_retranslate_backfill.py` (pattern:
`tools/lyrics_bestof_backfill.py` — reuse the poller's engine + validation functions
verbatim, no logic fork):

- Select `status='done' AND model='amazon.translate'` (today: 13).
- **Dump pre-state** (full rows as JSON) to a local file first — cheap rollback material.
- Per track: run the Step-1 engine path **in place** — only on PASS does a single UPDATE
  replace `segments` + `model` + `translator_version` + `translated_at`; failures leave the
  Amazon row untouched (viewer never loses a translation mid-backfill).
- Report: per-track PASS/FAIL matrix, same shape as the bench.

## Steps

Sequential (Step 2 depends on Step 1 being merged; both are workspace-only, no deploy
pipeline involved — the poller runs from the local checkout on merged `main`).

1. **Poller engine swap** — replace `translate_lines` with the `claude -p` engine + validation
   + failure policy above; `MT_MODEL='claude.sonnet'`, `TRANSLATOR_VERSION='v2'`; drop boto3
   translate usage; update the module docstring (engine history stays in it). Local
   verification: re-request 2 pilot tracks (1 short + "Porcelana" 75-line) via SQL, run
   `--drain`, assert `done|claude.sonnet|v2` + segment count parity + viewer spot-open;
   forced-failure check (temporarily bad model alias → row left claimed, not failed).
   Quote results in the PR body.
2. **Backfill the 13 Amazon rows** — write + run `tools/lyrics_retranslate_backfill.py`
   against prod (local, owner AWS creds for SSM only). Success gate: **13/13 rows flipped to
   `claude.sonnet` with validation PASS** (denominator = all 13 current `amazon.translate`
   rows), plus owner spot-audit of any 3 of the 13 in the viewer. Pre-state dump path quoted
   in the PR body. If any track fails both attempts: leave its Amazon row, report, owner
   decides (accept mixed / retry later) — do not block the other 12.

## Rollback

- Step 1: revert the poller commit (git); `failed` rows are re-requestable from the viewer
  button as today.
- Step 2: restore any row from the pre-state JSON dump (single UPDATE per row); the dump file
  path is recorded in the PR.

## Open questions

- **OQ1 — refusal regression at scale.** The bench covered one album (ES/DE/EN/IT/Latin). If
  a future album re-triggers principled refusals, rows fail visibly (`engine_validation`)
  and the viewer button allows re-request; if refusals become systematic, the owner decides
  between prompt iteration (new RFC/step, `v3`) or reverting to MT. No silent degradation
  path exists by design (no fallback).
- **OQ2 — model pinning.** `--model sonnet` follows the CLI's current Sonnet; a CLI upgrade
  silently changes the engine under a constant `translator_version`. Accepted for v2
  (subscription aliases are the norm in this workspace's `claude -p` tooling); pinning a
  dated model id is a one-constant change if drift ever matters.
- **OQ3 — throughput ceiling.** ~30–45s/track serial and a shared subscription session
  budget: fine for designated-track volume (13 total today). If volume ever grows to
  corpus-scale, that's the separate Batch-API RFC already named a non-goal here and in
  FEAT-lyrics-translation.

## Decisions log

| Date | Decision | Step |
| ---- | -------- | ---- |
| 2026-07-05 | RFC drafted from the 2026-07-04 LUX benchmark (15/15 PASS headless — prompt shape, not headless-ness, caused the 07-04 refusals). Engine = Sonnet (owner: "sonnet으로 가자"); failure policy = failed-marking only, **no Amazon fallback** (owner-selected); backfill = all 13 existing rows (owner-selected) | — |
| 2026-07-05 | Status → accepted (owner-approved in session, ws #529), then Step 1 built same session (owner: "Step 1 진행"). Poller engine swapped to `claude -p --model sonnet`; local verification: offline engine-path harness 5/5 (fake CLI: ok/out-of-order/fence/empty-ko, count-mismatch retry→terminal, refusal prose, exit-1 transient), forced-failure check PASS (bogus alias → claim kept, row untouched), 2-pilot re-request `--drain` PASS (Mundo Nuevo 8 lines 15.0s, Porcelana 75 lines 37.4s → `done\|claude.sonnet\|v2`, segment/gap/fingerprint parity vs pre-state dump, authed prod GET attaches all `text_ko`) | 1 |
| 2026-07-05 | Step 2 run same session (owner: "Step 2 진행"): `tools/lyrics_retranslate_backfill.py` (imports the Step-1 poller functions verbatim — no logic fork; per-track commit; UPDATE guarded by `status='done' AND model='amazon.translate'`). Pre-state dump `tools/out/retranslate_prestate_20260705-013142.json` → **11/11 PASS** (denominator = all 11 rows still `amazon.translate` at run start; ~25–65s/track, 0 refusals) → prod now **13/13 `done\|claude.sonnet\|v2`, 0 amazon rows**; authed prod GET spot check (Berghain 43/43 `text_ko`). Owner 3-track viewer spot-audit pending → close-out after | 2 |
