# FEAT-ai-editorial-critique: AI editorial critic — Phase 0 thin slice

> ⚠️ **STALE — do not cite this RFC's Current state as evidence (flagged 2026-08-16).** The section
> below asserts "**Zero AI/LLM code in any of the 5 repos**", verified by grep on 2026-06-06. That has
> been false for months. Verified against `origin/main` on 2026-08-16: `myblog_shared_db` ships a whole
> `src/myblog_shared_db/llm/` package — `cli_engine.py` **and `api_engine.py`**, with
> `LLMTransientError`/`LLMValidationError` and a retry policy — plus an `LlmUsage` model in `models.py`
> for cost accounting, and the workspace runs `scripts/buckit_nightly.py`, `editor_buckit.py` and the
> `research_poller` / `lyrics_translate_poller` / `genius_translate_poller` trio (all launchd-scheduled)
> against it. `api_engine.py` in particular is the direct-to-API path this RFC's Goal describes as not
> yet existing. The "first runtime path from code to an LLM" this RFC was
> written to build **already exists by another route**, so its Goal, Current state, and step sequencing
> all need re-deriving against `origin/main` before anyone acts on them
> (`feedback-rfc-current-state-audit`). Considered for promotion on 2026-08-16 and **rejected on exactly
> this ground** — it is a rewrite candidate, not an accept candidate. Nothing below has been edited;
> the body is left intact as the historical record of the 2026-06-06 intent.

- **Status**: draft — **body stale, see the warning above**
- **Owner**: 박지훈
- **Created**: 2026-06-06
- **Plan row**: `plan.md` → FEAT-ai-editorial-critique

---

## Goal

After this RFC, the product has its **first runtime path from code to an LLM**, and a single
endpoint — `POST /api/editorial/critique` — that takes a draft review (`body_mdx`) plus the
draft's already-linked album DB facts and returns **grounded Korean editorial feedback** under
`docs/editorial/review-critique-method.md`: section-anchored notes, `[ ]` / `[source?]` /
`[passage]` gap markers, and the §4 checklist status. The critic **reconstructs and gives
feedback — it never rewrites the prose from scratch**, and when the draft is thin on
viewpoint/grounds it reflects the seed already in the owner's own words and asks for the one
missing piece (§0). The slice is **proven by curl + a golden-draft eval set** before any frontend
or fact-check work — turning the hand-run methodology (a doc the owner pastes into a chat tool)
into the product's first editorial-staff capability, at a bounded, known token cost.

This is **Phase 0** of the editorial engine identified in the 2026-06-06 whole-project review
(memory `project-ai-editorial-greenfield`). It is deliberately the thinnest end-to-end proof.

## Non-goals

Anti-scope-creep insurance. Each of these is a **separate, later** RFC/step, explicitly **not**
in Phase 0:

- **Dedicated fact-check pass** (claim-extraction → diff asserted discography/dates/track-titles
  vs the music DB → verified/contradicted verdicts). Phase 0's critique runs over album facts
  passed in the prompt, but does **not** build a structured claim-extraction/diff engine. That is
  Phase 1, its own slice — it is the riskiest, least-deterministic sub-capability and must not be
  stapled to the first proof. **Also: the fact-check is narrow, not deterministic** — most
  honesty-line facts (lyrics, interviews, liner notes, confirmed intent, relationships) live
  **outside** the DB; the DB only grounds release-date / track-title / discography / artist
  identity. Phase 0 marks DB-absent facts `[source?]`, it does not "verify" them.
- **In-editor `/write` sidebar UI** (render feedback, inline markers, §4 checklist, a "reflect"
  button). Phase 0.5, separate RFC — built only after the endpoint's output quality is proven by
  curl. No frontend, no `api.gen.ts` regen tax in this RFC.
- **Editorial persistence** (`post_revisions` / `post_feedback` tables, revision history). Not
  here. When persistence is eventually wanted it starts in `Post.extra` (JSONB, zero migration) —
  normalized tables only when a query/index need is proven. Phase 0 is **stateless** (no critique
  is stored).
- **Content-planning agent**, **pre-publish honesty gate**, **catalog-staleness subsystem** —
  all deferred per the review's necessity-gate (single-author scale).
- **Auto-fire on type.** The endpoint is manual-fire only (an explicit POST). No keystroke /
  debounce trigger exists until the Phase 0.5 sidebar, and even then auto-fire is opt-in (cost).

## Current state

- **Zero AI/LLM code in any of the 5 repos** (verified 2026-06-06 by grep: the only keyword hits
  — `promptly`, `@clack/prompts`, `parseScrollMode`, OAuth `prompt=login` — are false positives).
  No Anthropic SDK, no API key in Secrets Manager, no model config in pydantic-settings, no
  prompt asset. `docs/editorial/review-critique-method.md` (v2.5) is applied **by hand** in a
  chat tool; it is not wired into the product.
- **`myblog_backend`** is a FastAPI Lambda (`ratemymusic-api`) with routes `posts`, `sections`,
  `tags`, `publish`, `buckets`, `library`, `metrics` and a service/repository layering. Secrets
  are fetched from `/myblog/backend` (SSM Parameter Store SecureString) and read via `settings.*` (pydantic-settings),
  cached on cold start. `app/core/auth.py:require_cognito_token` is the JWT dependency on writer
  routes; no-op under `ENV=local|dev`.
- **A draft already resolves to its album's DB facts today** — `Post.albums` is a real M:N link
  via the `post_albums` join table (`myblog_shared_db/.../models.py:61`, relationship at :232).
  So the critic can reach the subject album's facts (`title`, `release_date` as a true `Date`,
  `label`, `genres[]`, `total_tracks`, `Track.title`/`track_no`/`duration_sec`, `Artist.name` +
  `aliases` + `musicbrainz_id`) **with no schema change**. (`GET /api/posts/{id}` returns the
  post + linked album ids; album/track/artist detail is reachable via the existing music service
  or a direct shared_db read.)
- **`Post.extra`** (JSONB, `default '{}'`) exists and is currently unused — a ready zero-migration
  sink **if** persistence is ever wanted (out of Phase 0 scope).
- `infra/apigateway.tf` gates writer mutations behind a Cognito JWT authorizer (e.g.
  `posts_post`, `buckets_post`). `categories_post` has **no** authorizer — **never copy it**
  (STAB-2 hole; dead route, see this RFC's cleanup note / health audit).

## Target state

A new editorial slice in `myblog_backend`, reachable first locally (curl) then in prod, with the
method doc executed as the system prompt over a draft + its album facts.

### LLM service layer (`myblog_backend/app/services/llm_client.py`)

- A thin Anthropic client wrapper. **No SDK call leaks above this module.** API key in Secrets
  Manager (`myblog/editorial` → `ANTHROPIC_API_KEY`), read via `settings.*` — **never** `os.getenv`,
  **never** logged (CLAUDE.md rule #2 + code conventions). `logging.getLogger(__name__)`, not
  `print`.
- Model id + `max_tokens` + an **input token ceiling** are pydantic-settings fields with
  conservative defaults (recommended default: a current Sonnet-tier model for quality/cost
  balance; confirm the exact model id via the `claude-api` skill at implementation time, do not
  hardcode a guessed id). The ceiling truncates/refuses an over-long `body_mdx` so a single call
  can never run away — the **cost guard** (the owner is $0-biased; this is the stack's first
  usage charge).
- The **method doc is the system prompt.** Single-source-of-truth handling — see OQ1.

### Critique service (`myblog_backend/app/services/editorial_service.py`)

- `critique(db, post_id) -> CritiqueResult`: load the post (`body_mdx`, score, section, tags),
  resolve its linked album(s) → assemble a compact **facts block** (album/artist/track fields
  above), build the user message `{method-doc-as-system-prompt} + {facts block} + {draft body}`,
  call `llm_client`, parse the model's structured reply into `CritiqueResult`.
- **Hard constraints encoded in the prompt + validated on output:** (1) output is **Korean**;
  (2) the reply is **feedback + markers + checklist + (optional) reflected-seed**, never a
  rewritten draft body — a response that returns a full rewritten essay is rejected/flagged;
  (3) inferences are marked as claims (`~으로 들린다` / 추측), never asserted as fact (§2 ★);
  (4) DB-absent facts are marked `[source?]`, never invented; (5) when viewpoint/grounds are thin
  the model returns a `reflectedSeed` (the half-formed angle in the owner's own words + the one
  missing question), it does **not** guess-fill (§0).

### API (`myblog_backend/app/api/routes/editorial.py`)

| Method | Path | Body | Auth |
| ------ | ---- | ---- | ---- |
| POST | `/api/editorial/critique` | `{ "post_id": "<uuid>" }` | **Cognito JWT** (`require_cognito_token`) |

`CritiqueResult` schema (`app/api/schemas.py`):

```jsonc
{
  "notes":      [ { "anchor": "<quoted span or §-ref>", "kind": "viewpoint|evidence|voice|language", "note": "<korean>", "severity": "block|aim" } ],
  "gapMarkers": [ { "kind": "factual|viewpoint", "anchor": "<span>", "ask": "<the one missing piece, korean>" } ],
  "checklist":  [ { "item": "lead-controlling-idea|no-track-walking|audible-evidence|intent-marked|judged-on-own-intent-and-worth|reappraisal|score-last|listen-next|keep-voice", "status": "pass|miss|na" } ],
  "reflectedSeed": "<korean, present only when viewpoint/grounds thin>",
  "meta": { "model": "<id>", "inputTokens": 0, "outputTokens": 0 }
}
```

- POST is an **explicit JWT route** in `infra/apigateway.tf` (`editorial_critique_post`) — **copy
  the `posts_post` / `buckets_post` JWT pattern, never `categories_post`** (unauthed).
- `openapi.json` regen → `tools/merge_openapi.py` → `docs/contracts/openapi.json`. Workspace
  merges first (`reference-workspace-contract-merge-order`); watch pydantic version drift
  (`reference-openapi-pydantic-version-drift`).

### Golden-draft eval (`myblog_backend/tests/test_editorial_critique.py`)

A small fixed set proving **the critic itself honors the method doc** (the product's whole reason
to exist is the ★ honesty line — a critic that hallucinates is worse than none):

- A draft with a **deliberately wrong release date** → assert the critic flags it (`[source?]` or
  a correction note referencing the facts block), and **does not** silently accept it.
- A draft **thin on viewpoint** (pure track-walking, no controlling idea) → assert a
  `reflectedSeed` is returned and `checklist.lead-controlling-idea = miss`; assert the reply is
  **not** a fabricated viewpoint and **not** a rewritten essay.
- A clean draft → assert no false-positive `block`-severity notes.

These run against the live model (gated/skipped if `ANTHROPIC_API_KEY` unset, like the worker's
`TEST_DB_URL` conftest skip — `reference-test-db-url-source`), plus a mocked-client unit test for
the parsing/ceiling logic that always runs in CI.

## Steps

Each step independently mergeable. Hard rule #4 — one step per session, prod-observe gate between
steps. Branch/commit per repo (`feedback-nested-repo-branch-per-repo`, `feedback-bash-cwd-resets`).

### Step 0 — RFC + plan.md pointer (this document, docs-only)

This RFC + a one-line `plan.md` Backlog pointer + the `docs/rfcs/README.md` index entry. No code.

**Verification**: doc review against `TEMPLATE.md` structure. `git diff --stat`.

---

### Step 1 — backend LLM layer + critique endpoint (local-only) + golden eval

`app/services/llm_client.py`, `app/services/editorial_service.py`, `app/api/routes/editorial.py`,
`app/api/schemas.py` (CritiqueResult etc.), `app/main.py` include, `requirements.txt` (+ `anthropic`),
settings fields (model id / `max_tokens` / input ceiling / `ANTHROPIC_API_KEY`),
`tests/test_editorial_critique.py`. **Method-doc-as-prompt vendored per OQ1.**

**Not** exposed in prod yet — no `apigateway.tf` route, no contract merge. Reachable only locally
(`ENV=local` JWT bypass) so the **output quality is proven by curl before paying the infra +
contract tax** (the thin-slice discipline). Set the `ANTHROPIC_API_KEY` locally for the eval.

**Verification**:
```
cd myblog_backend && pytest tests/test_editorial_critique.py -v   # mocked unit always; live golden if key set
# local server, ENV=local:
curl -s -X POST localhost:8000/api/editorial/critique \
  -H 'Content-Type: application/json' -d '{"post_id":"<a real draft id>"}' | jq .
#   → korean notes + gapMarkers + checklist; NO rewritten body; reflectedSeed only when thin
#   → meta.inputTokens within the configured ceiling
```
(No local DB → seed one draft + album via fixtures or point at prod read for facts;
`feedback-local-db-smoke-fallback` — pytest+curl substitute, real prod curl after Step 2.)

**Rollback**: remove the new modules + include + requirements line (no infra/contract touched).

---

### Step 2 — expose in prod (infra JWT route + contract merge)

`infra/apigateway.tf` `editorial_critique_post` (**copy `buckets_post` JWT block**), backend
`openapi.json` regen committed in the same PR, then workspace `tools/merge_openapi.py` →
`docs/contracts/openapi.json`. Now reachable via the real API for **real-draft evaluation with a
smoke JWT** (`reference-smoke-password-source`).

**Verification**:
```
cd infra && terraform plan          # only editorial_critique_post added; stop on unexpected drift
python tools/merge_openapi.py && git diff --stat docs/contracts/openapi.json   # editorial path only
# post-merge prod smoke: curl prod /api/editorial/critique with a smoke JWT against a real draft id
```
**Rollback**: revert the apigateway entry + openapi regen (Step 1 code stays; endpoint just
returns to local-only reachability).

---

## Open questions

1. **Method-doc single source (blocks Step 1)** — the canonical doc is
   `docs/editorial/review-critique-method.md` in the **workspace** repo, but the prompt runs in
   the **`myblog_backend`** repo (separate deploy). Copying it in risks drift — the exact
   docs-drift class this project fights (and the doc is actively versioned, v2.1→v2.5).
   Options: (a) **vendor at build** — backend CI copies the workspace doc in (needs cross-repo
   access in CI); (b) **vendored copy + hash gate** — keep `myblog_backend/app/editorial/method.md`
   with a CI check asserting its sha matches the canonical (mirrors the openapi drift gate);
   (c) load from S3/DB at runtime. Recommend **(b)** for Phase 0 (no runtime fetch, drift caught
   in CI). Confirm with owner.
2. **Model id + cost ceiling (blocks Step 1)** — recommended default = a current Sonnet-tier model
   (quality for nuanced critique, far cheaper than Opus); Haiku-tier as a cheap iteration toggle.
   Confirm the exact current model id via the `claude-api` skill at implementation (do not
   hardcode a guess). Set the input-token ceiling + `max_tokens` defaults with the owner — this is
   the monthly-cost lever. Proposed: cap input at the method doc + facts + a bounded `body_mdx`
   slice; `max_tokens` modest (feedback is short).
3. **Facts-block source (blocks Step 1)** — assemble the album/track/artist facts via (a) a direct
   `myblog_shared_db` read inside the backend (backend already owns the session) or (b) an
   internal call to the music service. Recommend **(a)** — no cross-service hop, and the backend
   already has the ORM models. (The music service's `?explain=1` confidence signal is a Phase-1
   fact-check concern, not needed here.)
4. **Should the response include a `usage`/cost echo for the owner?** `meta.inputTokens/outputTokens`
   are in the schema so the owner can watch spend during the curl-eval phase before any auto-fire
   is ever considered. Keep.

## Decisions log

| Date | Decision | Step |
|------|----------|------|
| 2026-06-06 | Phase 0 = thinnest UI-less critique slice; fact-check pass, `/write` sidebar, persistence, planner, publish-gate all explicitly deferred to later RFCs (review necessity-gate) | 0 |
| 2026-06-06 | Reconstruction/feedback only — endpoint must never return a rewritten draft body; thin-viewpoint → reflect-the-seed, never guess-fill (§0) | 1 |
| 2026-06-06 | Cost guard mandatory: input-token ceiling + manual-fire only (no auto-on-type in Phase 0); meta echoes token usage | 1 |
| 2026-06-06 | Golden-draft eval (wrong-date + thin-viewpoint + clean) ships **with** Step 1 — the critic must be proven not to hallucinate before the slice counts as "value proven" | 1 |
| 2026-06-06 | Validate by curl locally (Step 1) before paying the infra+contract tax (Step 2); no frontend in this RFC | 1/2 |
| 2026-06-06 | JWT auth copies `buckets_post`; `categories_post` (unauthed) forbidden | 2 |
