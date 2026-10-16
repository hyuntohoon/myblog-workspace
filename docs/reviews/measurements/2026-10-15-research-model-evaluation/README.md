# Revised research prompt — model comparison, 2026-10-15

Owner request: test the revised prompt once per available Claude and GPT model, then have GPT-6 Astra and Claude give independent feedback. Both families are included; Fable's separately billed usage-credit models are excluded by owner decision. Parent RFC: `docs/rfcs/CHORE-research-model-evaluation.md`. Production remains unchanged.

**Goal extension (2026-10-15):** this is now the diagnostic pilot for a prompt that passes jointly designed Astra/Claude criteria for efficient evidence collection useful to a critic. See `docs/editorial/research-note-acceptance-design.md`. Structure and wording are free; the frozen pilot rubric is provisional, not a jointly agreed acceptance contract. No final pass is inferred from these scores.

User-facing Korean result: `RESULTS.ko.md`.

## Frozen inputs

- `prompt-revised-ko.md`: exact writing block 73184 from the immediately preceding chat response; not rewritten for this experiment.
- `generation-input.txt`: that prompt plus identical album/edition/date/task input, no prior note or source correction sheet.
- `inventory.json`: non-secret account catalog snapshot, user decisions and content hashes. Catalog-listed is not execution-proven availability.
- `manifest.json`: 7 visible GPT models and 10 subscription-included Claude models to attempt once; 2 separately billed Fable entries explicitly excluded.
- `rubric.md`: frozen weighted rubric and non-exhaustive prechecked reference anchors, withheld from generators.
- Supplied historical note: retained privately, excluded from this repository and all published commit history by the owner's 2026-10-16 instruction. It was not fed to generators or blind judges.

## Execution

**2026-10-16 resume:** Claude 10/10 success in `runs-claude-resume-2026-10-16/` (separate directory; the 10-15 `runs/` records are unchanged), same combined input hash, guard source shared_db `471200a`, Claude CLI 2.1.301. Summary: `execution-summary-claude-resume-2026-10-16.json`.


GPT generation complete: 7/7 successful, one dispatch each. Claude: first call returned HTTP 429 session usage limit with zero tokens; remaining 9 included models not-run, next announced reset 2026-10-16 02:40 KST. See `interim-results.md`. The runner preserves one-attempt markers, raw events, returned note, requested/resolved-model evidence, wall time and failure class. No retries, fallback models or production queue use. Provider-specific search/tool scaffolding differs, so this is a model-plus-harness comparison. Medium effort where supported; Haiku 4.5 has no thinking-effort setting.

## Review

**2026-10-16 completion:** blind packet v2 (`reviews/v2/review-packet-v2.txt`, 17 samples; v1 packet unchanged) built by `reviews/build_review_inputs_v2.py`. Astra audited the 10 new samples; `claude-opus-5-5` audited all 17; each reviewer then ran one comparative calibration over its own reports. Unblinded results and the harness confound: `pilot-final-results.md`. Acceptance criteria: `criteria/acceptance-v1.md` (frozen).


All 7 successful notes have opaque labels and completed independent per-sample `gpt-6-astra` audits (two isolated instances under the same frozen rubric); final comparative calibration is complete; all original scores retained. `claude-opus-5-5` review is blocked by account quota. `reviews/review-packet.txt` is frozen for the final common input; anonymous native web traces are separate hashed support. No Claude verdict or overall winner is claimed.

## Interpretation

Single album, single generation: exploratory selection only. Quality and operational cost are separate. No stable superiority, production-readiness or human usefulness is inferred from the weighted score alone.
