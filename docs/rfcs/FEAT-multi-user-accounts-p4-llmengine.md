# FEAT-multi-user-accounts Phase 4 — LLMEngine design decision

- **Status**: **confirmed + scaffolding shipped 2026-07-11** — owner confirmed the design + OQ3 (Anthropic-only v1) in-session; the "Session deliverable" below landed as shared_db **#59** (V43 numbered in place of V44 — V42 went to the parallel NOT-NULL flip; `llm_usage` prod-applied). Remaining: `/myblog/anthropic` SSM provisioning at first real ApiEngine caller; live-site cutover + BYOK per "Explicitly deferred".
- **Scope this pass**: owner-central scaffolding ONLY. BYOK / `user_api_keys` **deferred to Gate G2** (owner decision, 2026-07-08).
- **Parent**: `docs/rfcs/FEAT-multi-user-accounts.md` §Phase 4.
- **Method**: an `architect` subagent read RFC §Phase 4 + all 5 `claude -p` call sites + the 3 service `requirements.txt` + shared_db `pyproject.toml` (spot-checked, not trusted blind).

> This resolves the P4 open questions so implementation can be a mechanical follow-on. No code lands until the owner confirms this design.

## Verified current state (the load-bearing facts)

- **NO LLM SDK anywhere** — every LLM call is a headless `claude -p` subprocess on the owner's Max subscription (metered-credit pool, not a per-call bill). The one prior SDK path was torn down in FIX-bug-audit-2026-07 (ws #553).
- **Pollers do NOT import shared_db via the installed pin.** `myblog_shared_db/scripts/backfill_genres.py` path-injects `../src` (local checkout); the 4 `scripts/*.py` pollers import nothing from shared_db. **→ a new `src/myblog_shared_db/llm/` subpackage is visible to both poller families from local src with ZERO git pin bump.** This is the decisive fact.
- **5 sites / 2 shapes**, exact axes (model / tools / output-format / timeout):

  | site | model | tools | format | timeout |
  |---|---|---|---|---|
  | research_poller | `opus` | `WebSearch,WebFetch` | json | 900 |
  | editor_buckit | `opus` | `WebSearch,WebFetch` | json | 1200 |
  | buckit_nightly | `opus` | **disallow ×11 + `--setting-sources user`** | json | 1800 |
  | lyrics_translate | `sonnet` (env) | none | text | 300 |
  | backfill_genres | **NONE (CLI default)** | none | text | 900 |

## Decisions

1. **Engine home = `myblog_shared_db/src/myblog_shared_db/llm/`** (sibling subpackage, NOT mixed into models; NOT a standalone package; NOT vendored-twice). It is the only shared import surface both poller families already reach via local src → zero pin bump. Standalone = double-pin twin-drift (the exact liability shared_db exists to kill). The charter objection ("shared SQLAlchemy models") is narrow — shared_db already ships non-model code (`genre_mapping`, `scripts/`).

2. **Interface = `LLMEngine.run(job: LLMJob) -> LLMResult`** — one ABC, two engines. `LLMJob` carries `feature, prompt, output_schema (Pydantic | None), engine, model (opus|sonnet|None), user_id` + CLI knobs (`tools: ToolPolicy`, `output_mode`, `timeout_s`, `setting_sources`, `cwd`). `LLMResult` = `result (raw), parsed (only when output_schema given), tokens_in/out (0 in text mode — honest gap), model, is_error`. **`output_schema` defaults None** — the 5 live sites keep their bespoke quirk-tuned extractors; the structured-output machinery fires ONLY for new (ApiEngine) callers.

3. **Error split = a RAISED exception hierarchy, not a buried flag**: `LLMTransientError` (exit≠0 / timeout / empty → retryable/claim-kept), `LLMValidationError` (parse/schema fail → retry-once-internally then terminal), `LLMQuotaError` (pre-dispatch cap). This is **lifted from `lyrics_translate_poller`'s existing** `TransientEngineError`/`EngineValidationError` (real, not invented) and promoted to the interface.

4. **CliEngine = stateless argv-builder + subprocess + JSON-envelope parser.** Reproduces all 5 sites by parameterizing the 4 axes. Load-bearing invariants: buckit_nightly's **11 disallowed tools + `--setting-sources user`** stay atomic (secret-exfil guard); backfill's **`model=None` ⇒ no `--model` flag** (CLI default is the tuned 12-label behavior — do NOT default to opus); **zero module-level state** so backfill's `LLM_PARALLELISM=4` is thread-safe by construction (the caller keeps its own store lock). All 5 stay `claude -p` ($0-ish).

5. **ApiEngine = conformant skeleton, NOT wired to any caller this session.** Owner Anthropic key from SSM SecureString **`/myblog/anthropic`** (never Secrets Manager — hard ban; read lazily, never logged). Structured-output ladder (only when `output_schema != None`): provider-native `json_schema` → forced-tool-call → Pydantic `model_validate` + 1 retry → `LLMValidationError`. **Anthropic-first** (OQ3 lean), `Provider` protocol shaped for four. **RECOMMEND a thin adapter over the `anthropic` SDK, not Pydantic-AI**, on Lambda-dep-weight grounds (`[project.optional-dependencies] llm-api`, lazy-imported) — ⚠️ **flagged: verify Pydantic-AI's actual transitive tree before locking** (the arg is from framework-weight priors, not a measured manifest).

6. **Metering (V44 `llm_usage`, append-only)** — reuses the shipped Phase-1 review-cap pattern (a live aggregate query, no denormalized counter). Columns: `id, user_id, feature, engine, model, tokens_in, tokens_out, is_error, created_at`; index `(user_id, feature, created_at)`. Pre-dispatch check in `ApiEngine.run` (SUM/COUNT over a config-driven `settings.LLM_CAP_*` window) → `LLMQuotaError` before dispatch. CliEngine records without blocking (owner audit); both go through one `record_usage()` helper (single write path). Session lifecycle: a fresh short write session AFTER the subprocess/API returns — never held across the 900–1800s call.

7. **Rollout — no forced pin bump, and do NOT migrate the 5 live sites this session.** The `llm/` subpackage adds NO hard dependency (`[project]` stays `SQLAlchemy` only; SDKs in `[llm-api]` optional extra). 🔴 **The one genuine trap**: genre labels + lyrics translations are prod data written by model-quirk-tuned validators; re-routing through a new argv builder risks a silent argv delta that changes stored output. Mitigation: this session is **pure scaffolding + tests**; a later PR migrates each site one-at-a-time behind a **golden-argv diff test** (assert byte-identical argv per site).

## Session deliverable (the P4 first-step PR, once confirmed)

`myblog_shared_db/src/myblog_shared_db/llm/` — `interface.py` (LLMJob/LLMResult/LLMEngine ABC/ToolPolicy), `exceptions.py`, `cli_engine.py` (build_argv + runner + envelope parser), `api_engine.py` (skeleton, owner-SSM stub, Anthropic Provider adapter, lazy SDK import — **no caller**), `metering.py` (record_usage + check_cap); **V44** `llm_usage` migration + `LlmUsage` model; `pyproject.toml` `[llm-api]` optional extra (`[project]` deps unchanged). **Tests are the real value** — golden-argv per site (esp. buckit_nightly 11-disallow + `setting-sources user`, and genre **no-`--model`**), Shape-A envelope parse, Shape-B text passthrough, exception mapping, metering cap, ApiEngine structured-output ladder (mock SDK), CliEngine⇄ApiEngine substitutability. **No Lambda pin bump; no poller edited.**

## Explicitly deferred

- BYOK / `user_api_keys` + KMS envelope custody + live-probe-on-save + masked display — **Gate G2** (after Phase 3).
- Live-site cutover (all 5 `run_claude` bodies stay verbatim; one-at-a-time golden-diff migration later). → **started 2026-07-11; see Cutover log.**
- Owner `claude -p` → ApiEngine migration.
- Non-Anthropic providers (adapter shaped for them; none built).

## Cutover log (one-at-a-time, golden-argv-gated)

1. **research_poller — 2026-07-11.** `run_claude()` body → `CliEngine.run(LLMJob(...))`; argv byte-parity pinned by `tests/test_llm_engine.py::test_golden_argv_research_poller` (25/25 green at cutover). shared_db reached via script-relative src-path injection (`scripts/` → `../myblog_shared_db/src`, the lyrics-poller pattern) — works from the launchd runtime (workspace main checkout) with zero pin bump. Verified: `--once` empty-queue startup (SSM → Neon → claim → exit clean) + a live trivial dispatch through the engine (envelope parsed, `model=claude-opus-4-8` from modelUsage, cache-inclusive tokens_in). **Known delta**: `search_count` now always 0 — `LLMResult` doesn't surface `usage.server_tool_use`; the field was already documented unreliable (CLI aggregate reported 0 on runs with live citations, 2026-06-11); citations in `result_md` remain the grounding evidence. No metering `session_factory` wired — this poller never wrote `llm_usage`; poller metering is a separate decision. Remaining sites: editor_buckit, buckit_nightly (secret-guard argv — extra care), lyrics_translate + backfill_genres (prod-data validators — argv-sensitive).

2. **editor_buckit — 2026-07-11 (ws #601).** Same swap as #1 (argv audited byte-identical to `test_golden_argv_editor_buckit` before any edit; 25/25 green). Verified: `--dry-run` (context 34,508 chars assembled, read-only export intact) + live trivial dispatch (`OK`, `model=claude-opus-4-8`). Known delta: `search_count` → 0 (same as #1). Sole caller has no try/except — old `RuntimeError` vs new `LLM*` exceptions equally fatal.

3. **buckit_nightly — 2026-07-11 (ws #602).** Secret-guard site: 11-disallow + `--setting-sources user` kept atomic; `DISALLOWED_TOOLS` → tuple (frozen `ToolPolicy`), guard comment in place. `claude_argv()` retained as `build_argv(_job(""))` so `--dry-run` still prints the real dispatched argv. Gate: pre-edit vs post-edit `--dry-run` argv **byte-identical** (captured to files and diffed), plus `test_golden_argv_buckit_nightly`. Live trivial dispatch with exact site axes (pure text transform): `OK`/opus. Known deltas: exception types → `LLMTransientError`/`LLMValidationError` (caller has no try/except — same crash-and-log outcome); JSON-parse failure now gets CliEngine's one internal retry before raising. Post-merge `--dry-run` from the launchd main checkout confirmed the argv line verbatim.

4. **lyrics_translate — 2026-07-11 (ws #603).** Argv-sensitive prod-data site. `shutil.which("claude")` pre-check kept, passed as engine `binary` (argv[0] preserved); no `--output-format` modeled by `output_mode=None`; prompt delivery identical (stdin `input=` both sides). Quirk-tuned validator + `MT_MODEL` provenance untouched; poller keeps its own `TransientEngineError`/`EngineValidationError` + retry-once/claim-kept semantics — engine `LLMTransientError` re-raised as `TransientEngineError` at the boundary. Live parity: `claude_translate(["Hello","World"])` → `["안녕","세상"]` validator-clean; `--sweep-only` rc=0 clean (queue empty — no real row exercised, none fabricated). Known deltas (in code): empty stdout was terminal `EngineValidationError` → now transient/claim-kept (the RFC decision-3 classification, itself lifted from this poller); non-zero-exit diagnostic now `stderr[:500]` only (log-message-only). **Remaining site: backfill_genres only** (shared_db repo, prod-data validator — next one-at-a-time pass).

## Open items for owner

1. Confirm this design (engine home + thin-adapter-over-anthropic + metering shape) before implementation.
2. Confirm Anthropic-only for the ApiEngine v1 (RFC OQ3) — adapter is designed for four regardless.
3. Provision `/myblog/anthropic` in SSM SecureString when implementation starts (owner console/manual).
