# FEAT-album-research-notes: auto AI research notes for bucketed albums

- **Status**: draft
- **Owner**: 박지훈
- **Created**: 2026-06-11
- **Plan row**: `plan.md` → FEAT-album-research-notes

---

## Goal

When the owner adds an album to a review bucket, the system **automatically researches it** —
running `docs/editorial/album-research-prompt.md` (v2, lines 1–98) against the live web via the
Anthropic API — and stores the resulting Korean research note **per album** in the DB. The note
(non-audible grounds: credits, samples, production method, genre coordinates, lineage, angles,
with citations and 상충/불채택 honesty sections) is then readable in the writer GUI next to the
bucket item, so pre-writing research is one click away from where review intent is declared.

The auto-trigger is the bucket itself — **opt-in per bucket** (`off`/`all`/`selected` + per-album
checkboxes), with manual research/refine available for any album from the board or `/write`. No
polling, no catalog-wide scans, no duplicate calls — each (album, prompt version) runs exactly
once unless the owner explicitly restarts or refines it.

Validation behind this: 2026-06-09/10 manual validation on 6 albums (prompt doc §Validation log)
plus a 2026-06-11 4-model × 3-album bench (haiku/sonnet/opus/fable). Verdict: **opus 4.8** —
top-tier honesty discipline (conflicts recorded, no verdict leakage, snippet-confidence respected)
at the lowest token count (~49k/run, ~3.4 min). The prompt's own re-decision gate ("helps, and
recurs → evaluate an in-app RFC; citations + human-review gate mandatory") is the entry condition
for this RFC.

## Non-goals

- **Public display.** Notes are for the writer, not readers. No public page section, no contract
  exposure beyond authed routes. (Owner decision 2026-06-11: "이건 글 쓰는 사람을 위한거야".)
- **Backlog backfill** of the ~50 already-bucketed albums. Deferred (owner: "나중에 생각하자").
  When wanted, options are Claude Code batch ($0, like the 2026-06-11 bench) or running the
  pipeline over existing items; a one-shot enqueue script is trivial once Steps 1–4 exist.
- **The critique feature** (`FEAT-ai-editorial-critique`, separate draft RFC). Research notes
  gather grounds *before* writing; critique reviews a draft *after*. They share the Anthropic
  dependency but no code path yet — first-mover lands the API-key secret, the other reuses it.
- **Auto re-research on prompt bump.** A new prompt version does not fan out re-runs over the
  bucket. Re-research is per-album, manual (restart or refine POST).
- **Track/artist research, review generation, fact-check engine.** Out of scope.

## Current state (verified 2026-06-11 by code read)

- **Bucket**: `review_buckets` / `review_bucket_items` (shared_db `V6__review_buckets.sql`;
  `UNIQUE(bucket_id, album_id)`, item status `candidate|drafting|published`). API in
  `myblog_backend/app/api/routes/buckets.py` — `add_item()` (L290) is `POST
  /api/buckets/{id}/items`, Cognito-JWT at API Gateway. Front: `/profile` BucketBoard via
  `apiFetch`.
- **Worker**: `blogWorkerLambda`, timeout **120s**, consumes `blogSQS` (visibility 720s, DLQ
  `album-sync-dlq`) with a job-key dispatch in `worker/handler.py` (`spotify_listening`,
  `spotify_refresh`, `spotify_library_sync`, `album_ingest`, album-id batches). Secrets via
  Secrets Manager ARN env + pydantic-settings. **A research run is 3–8 min — it cannot ride
  blogSQS/120s.** Dedicated queue + function required.
- **Backend → SQS**: thin boto3 wrappers exist (`app/clients/sqs_client.py`:
  `send_listening_refresh`, `send_library_sync`) — pattern to extend.
- **Albums**: `albums.id` UUID PK. Latest shared_db migration **V15**; next-free is V16 — note
  `FEAT-genre-taxonomy` (deferred) also reserves V16; first to land takes it, the other bumps.
- **No Anthropic anything** in any repo (unchanged from the 2026-06-06 grep; no SDK, no key, no
  prompt asset wired in).

## Design

```
add_item() ──(no album_research row?)──▶ researchSQS ──▶ researchWorkerLambda
                                                            │ claim row (queued→running, conditional UPDATE)
                                                            │ anthropic messages.create:
                                                            │   model=claude-opus-4-8
                                                            │   system = album-research-prompt v2 (vendored)
                                                            │   tools = web_search_20260209 (max_uses cap)
                                                            │         + web_fetch_20260209
                                                            │   pause_turn continuation loop
                                                            ▼
                                                   album_research.result_md (done)
writer GUI (BucketBoard panel) ◀── authed GET ───────┘
```

**Dedupe / no-duplicate-call invariants (two layers):**

1. *Enqueue gate (backend)* — `add_item()` inserts an `album_research` row
   (`status='queued'`) **only if** no row exists for `(album_id, prompt_version)`; enqueues only
   on successful insert (`ON CONFLICT DO NOTHING` + rowcount check). Re-adding the same album to
   another bucket, button mashing, double-submit: zero extra messages.
2. *Claim gate (worker)* — handler does `UPDATE album_research SET status='running',
   started_at=NOW() WHERE album_id=… AND prompt_version=… AND (status IN ('queued','failed')
   OR (status='running' AND started_at < NOW() - INTERVAL '20 minutes')) RETURNING id`; if no
   row claimed, exit silently. SQS at-least-once redelivery and DLQ replays therefore never
   produce a second API call for a completed run. The **stale-`running` clause** is the
   crash-recovery path: if the Lambda dies mid-run (timeout kill, OOM), the row would otherwise
   be stuck `running` forever with nothing able to re-claim it — the 20-min staleness window
   (run budget is ≤15 min) lets the SQS redelivery pick it up.

**Failure path**: exception → `status='failed'` + `error` recorded; SQS retry (maxReceive 3) can
re-claim `failed`; after DLQ, the manual restart POST is the recovery lever (restart accepts
`done`, `failed`, and stale-`running` rows).

**Cost guard**: `web_search` declared with `max_uses` (bound per-run search spend; tune from the
Step 3 measured run), `max_tokens` ceiling, and the enqueue gate above means total spend is
bounded by bucket adds — there is no autonomous fan-out surface.

**Prompt vendoring**: worker ships `worker/prompts/album_research_v2.md` = lines 1–98 of
`docs/editorial/album-research-prompt.md`, **plus a pipeline addendum**: (a) the prompt's
workflow step 1 says "if ambiguous, present the candidates and confirm" — there is no human
mid-run, so the addendum instructs the model to pin the release itself and record any ambiguity
under 앨범 식별 (the 2026-06-11 bench ran exactly this addendum successfully on all 12 runs);
(b) disambiguation is largely pre-solved anyway — the user message carries the album row's
metadata (artist, title, release_date, label, spotify id), not a bare title. `PROMPT_VERSION =
"v2"` recorded on every row.
Single-source-vs-drift is accepted as the same OQ1 as FEAT-ai-editorial-critique: the workspace
doc stays canonical; copying into the worker is a deliberate build-time act that bumps
`PROMPT_VERSION`.

**New table** (shared_db, V16 or next-free):

```sql
CREATE TABLE album_research (
  id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  album_id       UUID NOT NULL REFERENCES albums(id) ON DELETE CASCADE,
  prompt_version TEXT NOT NULL,
  status         TEXT NOT NULL DEFAULT 'queued'
                 CHECK (status IN ('queued','running','done','failed')),
  model          TEXT,
  result_md      TEXT,
  tokens_in      INT,
  tokens_out     INT,
  search_count   INT,
  error          TEXT,
  refine_count   INT NOT NULL DEFAULT 0,
  last_instruction TEXT,
  requested_at   TIMESTAMP NOT NULL DEFAULT NOW(),
  started_at     TIMESTAMP,
  finished_at    TIMESTAMP,
  UNIQUE (album_id, prompt_version)
);

-- same migration: auto-research scope controls
ALTER TABLE review_buckets
  ADD COLUMN research_mode TEXT NOT NULL DEFAULT 'off'
  CHECK (research_mode IN ('off','all','selected'));
ALTER TABLE review_bucket_items
  ADD COLUMN research_selected BOOLEAN NOT NULL DEFAULT FALSE;
```

**Auto-research scope (owner decision 2026-06-11, supersedes "all buckets")** — auto-trigger is
**opt-in per bucket**, with optional per-album narrowing:

- `review_buckets.research_mode`: `'off'` (default) | `'all'` | `'selected'`.
- `review_bucket_items.research_selected` boolean (default false) — meaningful only in
  `'selected'` mode (item checkboxes in the GUI).
- Auto-enqueue fires on these transitions, always through the dedupe gate (so flipping modes
  back and forth never re-calls for albums that already have a note):
  - item added to a bucket in `'all'` mode;
  - bucket mode switched to `'all'` → enqueue its note-less items;
  - item's `research_selected` checked while bucket is `'selected'` mode (and mode switched to
    `'selected'` → enqueue its checked, note-less items).
- Deselecting/`off` only stops *future* auto-triggers; it cancels nothing in flight and deletes
  no notes.
- **Manual trigger stays unscoped** — any album, from any surface, regardless of bucket mode.

**Re-research, two flavors (owner-requested)** — `POST` body `{"mode": …}` on an existing row:

- `"restart"`: full redo. Resets the `(album_id, prompt_version)` row in place
  (`status→'queued'`, result/error/token fields cleared) and enqueues. Previous note replaced.
- `"refine"` + `"instruction"` (preferred for "마음에 안 듦" cases): incremental. The worker
  sends the **existing note + the owner's instruction** ("X 부분을 더 조사해줘", "Y 출처를
  확인해줘") with the same system prompt + web tools, asking for the **full updated note with the
  additions integrated** (honesty rules unchanged — new claims need new citations). On success
  the result replaces `result_md`; `refine_count` increments, `last_instruction` stored.
  **Refine never clears the existing note** — unlike restart, the queued/running/failed states
  of a refine keep the prior `result_md` intact, so a failed refine degrades to "old note +
  error badge", never to an empty panel. Refine is valid on `done` rows only. Cheaper than
  restart and keeps what was already good instead of re-rolling it.

Both reuse the single UNIQUE row and the claim gate — re-runs are single-flight; no history
beyond `prompt_version` (and `refine_count`) is kept — **overwrite confirmed by owner
2026-06-11 ("덮어쓰자"), no pre-refine backup**. A plain POST (no mode) on a
`done`/`running`/`queued` row is a no-op returning current state — accidental duplicates stay
impossible.

**New routes** (backend):

- `POST /api/research/albums/{album_id}` — body `{mode?: "restart"|"refine", instruction?}`;
  no body = first-time manual trigger. Usable from anywhere an album appears (bucket item,
  `/write` editor). Cognito-JWT at API Gateway (new `infra/apigateway.tf` route, same block
  shape as `buckets_post`).
- `GET /api/research/albums/{album_id}` — latest note for the album (writer GUI; authed
  dependency, served via the CloudFront catch-all like other GETs).

**Trigger surfaces** (all hit the same two routes — the note belongs to the album, not the
surface): (a) auto via bucket `research_mode` scope above; (b) manual button on a BucketBoard
item; (c) manual button in `/write` for the album(s) linked to the draft — research, read, and
refine the note without leaving the editor.

**Secrets**: dedicated `myblog/anthropic` entry, key `ANTHROPIC_API_KEY` (created console/manual,
per credential-rotation convention), readable by the research Lambda — feature-scoped per the
Forward-compat section; FEAT-ai-editorial-critique reuses the same entry later.

**Infra**: `researchSQS` (visibility ≥ 5400s = 6× function timeout, DLQ maxReceive 3, **batch
size 1**) + `researchWorkerLambda` (same worker image/codebase, timeout **900s**, 512MB,
**reserved concurrency 2**) + event source mapping + IAM (SQS consume, secrets read). The
concurrency cap is deliberate: a bucket flipped to `'all'` can enqueue dozens of runs at once —
serializing to ≤2 concurrent 5-min opus calls keeps Anthropic rate limits and spend ramp smooth
(a 50-item flip drains in ~2h; the queue absorbs the burst). No change to `blogSQS` or the
existing Lambda. The `POST /api/research/...` API GW JWT route ships **with Step 4** (backend),
per the route↔backend DoD pairing — not in Step 2. Workspace infra merge ≠ prod change — owner
runs `terraform apply` manually.

## Steps

Order follows the shared_db rollout convention (migration → prod apply → pin bump → service →
front). Steps 1–2 are additive/independent of each other; 3–5 depend on them.

1. **shared_db — `album_research` + scope columns** (V16 or next-free at land time). Plain SQL
   migration (new table + the two `review_buckets`/`review_bucket_items` ALTERs, all additive
   with defaults) + SQLAlchemy models + tag bump. **Prod apply required before any dependent
   merge.**
   - Verify: migration applies on Neon test branch; models import; backend pin unchanged yet.
2. **infra — queue, function, secret plumbing.** `researchSQS` + DLQ (batch size 1),
   `researchWorkerLambda` (timeout 900s, reserved concurrency 2), event source mapping, IAM,
   secret ARN env var. Full `terraform plan`, owner applies manually. `myblog/anthropic` +
   ANTHROPIC_API_KEY created in console. (API GW route moves to Step 4 — see Infra note.)
   - Verify: plan clean; after apply, function exists + a hand-sent SQS message reaches the
     handler (no-op job logs).
3. **worker — research handler.** `{"job": "album_research", "album_id": …, "instruction"?: …}`
   dispatch (instruction present ⇒ refine: prior note included in the call); claim gate;
   vendored prompt; anthropic SDK call (opus 4.8, web_search `max_uses` + web_fetch, pause_turn
   loop, streaming-safe timeout budget inside 900s); persist result/tokens/searches/refine
   fields; failure path. Unit tests with mocked anthropic client (claim-gate idempotency,
   refine-payload shape, failure writeback). **One real prod-side run measured here** (single
   album, quote tokens + $ in PR) — this sets `max_uses` and confirms the 900s budget.
   - Verify: pytest; real-run note lands in `album_research`, cost quoted.
4. **backend — scope triggers + routes + contract.** shared_db pin bump;
   `send_album_research()` in `sqs_client.py`; auto-enqueue on the scope transitions (item add
   in `'all'`-mode bucket; bucket `research_mode` PATCH; item `research_selected` PATCH) — all
   fire-and-forget (bucket ops must not fail on SQS hiccups; log + continue); `POST` (restart /
   refine modes) / `GET /api/research/albums/{id}` **+ the matching API GW JWT route in
   `infra/apigateway.tf` (same PR, per DoD)**; `openapi.json` regen + workspace contract merge
   (+ front `api.gen.ts` regen in the same flow).
   - Verify: pytest (gate: duplicate transitions ⇒ no second enqueue; restart resets exactly one
     row; refine enqueues with instruction; plain POST on done ⇒ no-op); local smoke substitute
     per no-local-DB convention; contract CI green.
5. **front — writer GUI surfaces.** (a) BucketBoard: bucket research-mode control
   (off/전체/선택), item checkboxes in `'selected'` mode, research status badge
   (queued/running/done/failed) + "리서치 노트" panel — markdown render, collapsed by default,
   links clickable; "재조사" split action: 보강(instruction 입력 → refine) / 처음부터(restart,
   confirm dialog — replaces the note); failed ⇒ retry. (b) `/write`: **margin sidebar panel**
   next to the body section (owner 2026-06-11: "본문섹션 옆 여백에 조사 정보를 띄우고, 없으면
   조사하기 버튼") — note exists ⇒ render it in the gutter (collapsed sections, refine action);
   no note ⇒ "조사하기" button in its place; draft linked to multiple albums ⇒ one tab per
   album. Narrow viewports: collapse to a toggleable drawer (gutter math is fragile —
   see /profile overlay lessons). `pnpm lint` + `astro check` + real browser click-through
   (DoD).
   - Verify: click-through on prod-realistic data; prod smoke after merge = add one album to a
     bucket → note appears in GUI within ~10 min; quote in PR comment.

Steps are **sequential** (gap-gated per workflow rule 4); 1 and 2 may be OK'd together by the
owner as additive if desired.

## Cost

- Bench-measured (2026-06-11): opus 4.8 ≈ 49k tokens/run ≈ **$0.44/run** token cost (+
  per-search web_search billing, measured at Step 3 — expect ≈$1/run order of magnitude).
- Spend is strictly bounded by bucket adds × 1. 50-album scale ⇒ tens of dollars, one-time-ish.
- No recurring/cron spend. EventBridge is not used.

## Rollback

- Each step is independently revertable; the table is additive (no existing reads).
- Kill switch: disabling the event source mapping (console) stops all API spend instantly;
  enqueue gate rows stay `queued` and are processed on re-enable.

## Open questions

- **OQ1 (shared with critique RFC)**: prompt single-source vs vendored copy drift — accepted for
  now, `prompt_version` is the audit trail.
- ~~OQ2: bucket `kind` gating~~ — **resolved 2026-06-11 (owner, two rounds): auto-trigger scope
  = per-bucket `research_mode` (`off`/`all`/`selected` + item checkboxes); manual trigger
  unscoped (any album, bucket or `/write`).**
- ~~OQ3: secret placement~~ — **resolved 2026-06-11 (owner direction): feature-scoped secrets.**
  Dedicated `myblog/anthropic`; see Forward-compat below.

## Forward-compat: per-feature API keys → per-user keys

Owner direction (2026-06-11): external-API usage should be **partitioned by feature** so it is
legible which key powers which capability, because the project's end state is **multiple
personalized users** — at which point keys/quotas must be managed per user.

What this RFC does about it now (cheap, non-blocking):

- **Feature-scoped secret**: `myblog/anthropic` is its own Secrets Manager entry (not a key
  buried in the worker's blob). One feature ↔ one credential; rotation/cost questions have one
  obvious place to look. The critique feature (FEAT-ai-editorial-critique) reuses the same entry
  when it lands — same provider, same feature family (editorial AI).
- **Per-run usage attribution is already in the schema**: every `album_research` row records
  `model`, `tokens_in/out`, `search_count`. When users exist, adding a `user_id` column to usage
  rows is the whole accounting change — the measurement substrate ships now.

What is explicitly **deferred to FEAT-multi-user-accounts** (or an ARCH RFC under it): per-user
key vaulting/BYO-key, per-user quotas/budgets, and a feature→credential registry. Designing that
before the user model exists would be speculation.
