# FEAT-album-research-notes: auto AI research notes for bucketed albums

- **Status**: accepted (2026-06-11, owner: "승격하고"). **Execution backend pivoted 2026-06-11**
  (owner: subscription-cost, not API): primary executor = **local poller → headless Claude Code
  ($0 on the Max subscription)**. The paid `researchSQS`/`researchWorkerLambda` path (built +
  prod-applied in Steps 1–2) is retained **dormant** as the cloud-autonomous upgrade. See
  Execution backend below.
- **Owner**: 박지훈
- **Created**: 2026-06-11
- **Plan row**: `plan.md` → FEAT-album-research-notes

---

## Goal

When the owner adds an album to a review bucket, the system **researches it** — running
`docs/editorial/album-research-prompt.md` (v2, lines 1–98) against the live web — and stores the
resulting Korean research note **per album** in the DB. The note (non-audible grounds: credits,
samples, production method, genre coordinates, lineage, angles, with citations and 상충/불채택
honesty sections) is then readable in the writer GUI next to the bucket item, so pre-writing
research is one click away from where review intent is declared.

The trigger is the bucket itself — **opt-in per bucket** (`off`/`all`/`selected` + per-album
checkboxes), with manual research/refine available for any album from the board or `/write`. A
bucket-add writes a `queued` row (DB only, **zero AI cost**); a **local poller** on the owner's
machine picks queued rows up and runs the research via **headless Claude Code** (`claude -p`),
which executes on the Max **subscription** — so the research itself costs **$0**, at the opus 4.8
quality the bench selected. No catalog-wide scans, no duplicate calls — each (album, prompt
version) runs exactly once unless the owner explicitly restarts or refines it.

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
  Trivial once Step 3 exists: one SQL insert of `queued` rows for the existing items, then let the
  poller drain them ($0). No separate tooling needed.
- **The critique feature** (`FEAT-ai-editorial-critique`, separate draft RFC). Research notes
  gather grounds *before* writing; critique reviews a draft *after*. Shared dependency is now the
  **subscription executor pattern** (or, on the paid path, the `myblog/anthropic` key) — no shared
  code yet.
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

## Execution backend (the 2026-06-11 pivot)

The data model, trigger, dedupe, and GUI are **executor-agnostic** — `album_research(queued)` is
both the worklist and the store, regardless of who drains it. The owner chose the **$0 path** as
primary; the paid path stays built but dormant.

| | **Primary — local poller (chosen)** | **Dormant — Lambda (built, prod-applied)** |
|---|---|---|
| Executor | `claude -p` headless Claude Code | `anthropic` SDK in `researchWorkerLambda` |
| Auth / cost | Max **subscription** → **$0** | `myblog/anthropic` API key → ~$1/run |
| Where it runs | owner's machine (a poller process) | AWS, fully unattended |
| Trigger reach | poller polls the table | backend sends to `researchSQS` |
| Quality | opus 4.8 (same model/tools as bench) | opus 4.8 |
| Trade-off | machine must be on; subject to subscription rate limits | always-on, but costs money |

Why the split is cheap to keep: the trilemma is **{$0, machine-off-autonomous, opus-quality} —
pick two**. $0 + opus today, with the Lambda as the one-flag upgrade to machine-off-autonomous
when/if recurring volume justifies paying. The infra (researchSQS/Lambda/`myblog/anthropic`) is
already applied to prod (Steps 1–2) and is inert as long as the backend never feeds the queue —
flipping to it later is "set the API-key value + have the backend `send_album_research()`".

**Headless legitimacy / limits**: `claude -p` (and the Claude Agent SDK) are first-party
automation surfaces — this is **not** browser-scraping claude.ai. Caveats the owner accepted:
(a) the poller's host must be running; (b) a 50-album backlog batch can hit the subscription's
rolling usage window → drain across a day; steady-state (occasional new album) is well within
limits.

## Design

```
[web] add_item() / scope PATCH ─▶ album_research(queued)        ← DB only, $0, no AI
                                        ▲
[local poller  (owner machine, cron/launchd/loop)]              ← Step 3
   every N min:
     claim: UPDATE … SET status='running' WHERE status='queued' (or stale) RETURNING
     for each: claude -p "<vendored prompt v2>\n\n앨범: <row metadata>"
                 --allowedTools WebSearch,WebFetch --output-format json
     parse note + usage → UPDATE result_md / tokens / status='done' (or 'failed' + error)
                                        │
writer GUI (BucketBoard + /write) ◀── authed GET ──┘            ← Step 5

[dormant] researchSQS ▷ researchWorkerLambda (anthropic SDK)    ← built; unfed in $0 mode
```

**Dedupe / no-duplicate-call invariants (two layers, executor-independent):**

1. *Enqueue gate (backend)* — the trigger inserts an `album_research` row (`status='queued'`)
   **only if** no row exists for `(album_id, prompt_version)` (`INSERT … ON CONFLICT DO NOTHING`
   + rowcount check). Re-adding the same album to another bucket, button mashing, double-submit:
   zero extra rows. (In $0 mode the insert *is* the enqueue — no SQS send.)
2. *Claim gate (poller)* — `UPDATE album_research SET status='running', started_at=NOW() WHERE
   id=… AND (status IN ('queued','failed') OR (status='running' AND started_at < NOW() -
   INTERVAL '20 minutes')) RETURNING id`; if no row claimed, skip. This makes the poll loop
   single-flight even if two poller instances run, and the **stale-`running` clause** is
   crash-recovery: a poller killed mid-run (laptop sleep, `claude -p` crash) would otherwise
   strand the row in `running` — the 20-min window (a run is ≤~10 min) lets the next poll
   re-claim it. (The dormant Lambda path uses the identical claim against SQS redelivery.)

**Failure path**: `claude -p` non-zero exit / parse failure / timeout → `status='failed'` +
`error` recorded; next poll re-claims `failed`; the manual restart POST is the operator recovery
lever (restart accepts `done`, `failed`, and stale-`running` rows).

**Cost / rate guard**: in $0 mode there is no per-run dollar spend; the bound is the
subscription's usage window. The poller processes **serially** (one `claude -p` at a time, small
inter-run sleep) so a `research_mode='all'` flip of dozens of albums drains steadily instead of
spiking the rate limit. `--allowedTools WebSearch,WebFetch` only (no Bash/Edit) so a headless run
can't touch the repo or filesystem; DB writes are done by the **poller**, not the model.

**Prompt vendoring**: the poller ships `album_research_v2.md` = lines 1–98 of
`docs/editorial/album-research-prompt.md`, passed as the `claude -p` prompt prefix, **plus a
pipeline addendum**: (a) the prompt's workflow step 1 says "if ambiguous, present the candidates
and confirm" — there is no human mid-run, so the addendum instructs the model to pin the release
itself and record any ambiguity under 앨범 식별 (the 2026-06-11 bench ran exactly this addendum
successfully on all 12 runs), and to emit **only** the note markdown (so `--output-format json` →
`.result` is the clean note); (b) disambiguation is largely pre-solved anyway — the prompt carries
the album row's metadata (artist, title, release_date, label, spotify id), not a bare title.
`PROMPT_VERSION = "v2"` recorded on every row. Single-source-vs-drift is the same OQ1 as
FEAT-ai-editorial-critique: the workspace doc stays canonical; copying into the poller is a
deliberate build-time act that bumps `PROMPT_VERSION`. (When the Lambda path is later activated it
vendors the same file — one prompt asset, two callers.)

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

**Secrets**: the **$0 poller needs no Anthropic key** — `claude -p` uses the owner's Claude Code
subscription login. It needs the prod `DATABASE_URL` (Secrets Manager `myblog/backend`, read with
the owner's AWS creds on their machine). The dedicated `myblog/anthropic` entry (created Step 2)
is **for the dormant Lambda path only**; its value is left unset until/unless that path is
activated. Feature-scoped per Forward-compat; FEAT-ai-editorial-critique reuses it.

**Infra (built + prod-applied in Step 2, now dormant)**: `researchSQS` (visibility 5400s, DLQ
maxReceive 3, batch 1) + `researchWorkerLambda` (worker codebase, timeout 900s, 512MB; concurrency
capped at the SQS ESM via `maximum_concurrency=2` — **not** function-reserved, because this
account's concurrent-execution limit is 10 and any reservation trips the unreserved floor; fix
#306) + event source mapping + IAM. **Inert in $0 mode**: the backend never sends to `researchSQS`
and `myblog/anthropic` has no value, so the Lambda never fires. No change to `blogSQS` / the
existing Lambda. The `POST /api/research/...` API GW JWT route ships **with Step 4**.

## Steps

1. **shared_db — `album_research` + scope columns** ✅ **DONE + prod-applied** (V16, shared_db
   v0.16.0, PR #25; applied to Neon test + prod 2026-06-11). The table serves both executors.
2. **infra — dormant paid path** ✅ **DONE + applied** (researchSQS/DLQ, researchWorkerLambda
   900s, `myblog/anthropic` container, research-worker IAM; PRs #304/#306; `terraform apply` done
   + live-verified). **Inert in $0 mode** — kept as the cloud-autonomous upgrade switch. The $0
   path does **not** depend on this step.
3. **local poller — the $0 executor.** ✅ **IMPLEMENTED + verified 2026-06-11** (this branch,
   pre-merge). `scripts/research_poller.py` + vendored `scripts/album_research_v2.md` (prompt doc
   lines 1–98). One real end-to-end run measured against **prod DB**: *Blonde* — Frank Ocean,
   `claude -p` opus-4.8, **162.6s (~2.7 min)**, 5253-char Korean note with **12 live citations**
   (Wikipedia/Complex/HipHopDX/The FADER), correct `[확인]/[미확인]` markers + disambiguation
   (Blond/Blonde, *Endless*), `status='done'`. Failed-row re-claim verified (forced `failed` →
   claim gate flips it to `running`). Two CLI-reporting caveats found + documented in code: the
   `claude -p` JSON `search_count` aggregate reads 0 even when the model demonstrably fetched (the
   citations are the grounding evidence), and `tokens_in` is inflated by Claude Code's own cached
   system prompt vs the API-path bench (~49k) — order-of-magnitude audit only, $0 on subscription.
   Test row deleted after verify (prod `album_research` back to 0). Runs via
   `myblog_backend/.venv/bin/python` (psycopg3 + boto3). **PR #__.** Original spec: a standalone
   operator script (`scripts/research_poller.py`, workspace-level — shares no code with the deployed
   Lambda; not deployed anywhere) that: reads prod `DATABASE_URL` from `myblog/backend`; loops on a poll
   interval; **claims** a `queued`/stale row (conditional UPDATE above); builds the prompt
   (vendored v2 + addendum + the row's album metadata; `instruction` present ⇒ refine, prior note
   included); shells `claude -p … --allowedTools WebSearch,WebFetch --output-format json`; parses
   `.result` (note) + usage; writes `result_md`/tokens/`status='done'` (or `'failed'`+`error`,
   refine keeping the prior note). Serial, with an inter-run sleep. **One real measured run here**
   (single album end-to-end, quote wall-time + subscription-usage note in the PR) confirms the
   `claude -p` headless invocation, tool-permission flags, JSON parse, and DB writeback.
   - Verify: insert a `queued` row by hand → run poller → note lands in `album_research`, status
     `done`; a forced `failed` row re-claims; quote the run.
   - (Backlog: this same poller drains the ~50 existing items once they have `queued` rows —
     see Non-goals backfill.)
4. **backend — triggers + routes + contract.** shared_db pin bump; auto-enqueue on the scope
   transitions (item add in `'all'`-mode bucket; bucket `research_mode` PATCH; item
   `research_selected` PATCH) = **INSERT `queued` row, `ON CONFLICT DO NOTHING`** (no SQS send in
   $0 mode) — fire-and-forget (bucket ops must not fail on a research hiccup; log + continue);
   `POST` (first-run / restart / refine modes — all just set row state for the poller) /
   `GET /api/research/albums/{id}` **+ the matching API GW JWT route in `infra/apigateway.tf`
   (same PR, per DoD)**; `openapi.json` regen + workspace contract merge (+ front `api.gen.ts`
   regen in the same flow).
   - Verify: pytest (gate: duplicate transitions ⇒ one row; restart resets exactly one row;
     refine sets instruction + keeps note; plain POST on done ⇒ no-op); local smoke substitute
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
   - Verify: click-through on prod-realistic data; prod smoke after merge = add an album to an
     `'all'`-mode bucket → `queued` row appears → run the poller → note renders in the GUI; quote
     in PR comment.

Steps 1–2 are **done**. Remaining 3 → 4 → 5 are gap-gated per workflow rule 4. Step 3 (poller) is
validatable standalone (hand-inserted `queued` row), so it does not block on Step 4; Step 5 needs
both.

## Cost

- **$0 in the primary path** — `claude -p` runs on the Max subscription; no per-run dollar spend.
  The real bound is the subscription's rolling usage window, so a 50-album backlog batch is spread
  across a day; steady-state (occasional new album) is negligible.
- Bench reference for the **dormant paid path** (if ever activated): opus 4.8 ≈ 49k tokens/run ≈
  ~$0.44 token + web_search per-search billing ≈ ~$1/run order of magnitude; 50 albums ⇒ tens of
  dollars one-time.
- No recurring/cron cost either way. EventBridge is not used.

## Rollback

- Each step is independently revertable; the table is additive (no existing reads).
- $0-mode kill switch: **stop running the poller** — queued rows simply wait. Nothing autonomous
  is in flight (the Lambda is unfed).
- The dormant Lambda path stays disabled by construction (no queue feed, no key value); activating
  it is an explicit future act, not a rollback concern.

## Open questions

- **OQ1 (shared with critique RFC)**: prompt single-source vs vendored copy drift — accepted for
  now, `prompt_version` is the audit trail.
- ~~OQ2: bucket `kind` gating~~ — **resolved 2026-06-11 (owner, two rounds): auto-trigger scope
  = per-bucket `research_mode` (`off`/`all`/`selected` + item checkboxes); manual trigger
  unscoped (any album, bucket or `/write`).**
- ~~OQ3: secret placement~~ — **resolved 2026-06-11 (owner direction): feature-scoped secrets.**
  Dedicated `myblog/anthropic`; see Forward-compat below.
- ~~OQ4: executor embed style~~ — **resolved 2026-06-11 (owner): `claude -p` headless subprocess,
  not the Agent SDK.** Same cost ($0 subscription) and quality; chosen for a tiny/transparent
  poller and because the poller (not the model) does the DB write. Agent SDK reconsidered only if
  this grows into a standing service.
- ~~OQ5: poller host + schedule~~ — **resolved 2026-06-11 (Step 3)**: start with **manual `--once`
  / `/loop` runs on the owner's Mac** (via `myblog_backend/.venv/bin/python`), **no launchd/cron
  yet**. Correctness is independent of cadence — queued rows wait until the poller runs; serial
  processing + a 30s inter-run sleep keep a bucket-wide `'all'` flip within the subscription rate
  window. Formalize to launchd/cron only if hand-draining proves annoying. (The poller's machine
  must be on — accepted caveat; the dormant Lambda is the machine-off-autonomous upgrade.)

## Forward-compat: per-feature API keys → per-user keys

Owner direction (2026-06-11): external-API usage should be **partitioned by feature** so it is
legible which key powers which capability, because the project's end state is **multiple
personalized users** — at which point keys/quotas must be managed per user.

What this RFC does about it now (cheap, non-blocking):

- **Today the $0 path uses no key at all** — research runs on the owner's subscription via
  `claude -p`. The per-user-key question only becomes live when the feature goes
  machine-off-autonomous (the dormant Lambda path) or multi-user.
- **Feature-scoped secret** (for that future): `myblog/anthropic` is its own Secrets Manager entry
  (not buried in the worker blob). One feature ↔ one credential. The critique feature reuses it.
- **Per-run usage attribution is already in the schema**: every `album_research` row records
  `model`, `tokens_in/out`, `search_count`. When users exist, adding a `user_id` column is the
  whole accounting change — the substrate ships now.

What is explicitly **deferred to FEAT-multi-user-accounts** (or an ARCH RFC under it): per-user
key vaulting/BYO-key, per-user quotas/budgets, a feature→credential registry, and the
subscription-vs-API executor choice **per user** (a multi-user product can't run everyone on the
owner's personal subscription — that's the natural point to require per-user API keys). Designing
that before the user model exists would be speculation.
