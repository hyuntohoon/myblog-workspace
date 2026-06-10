# FEAT-album-catalog-ingest: Scheduled new-album catalog ingest

- **Status**: draft
- **Owner**: TBD
- **Created**: 2026-06-10
- **Plan row**: `plan.md` → FEAT-album-catalog-ingest

---

## Goal

A scheduled, source-agnostic job grows the music catalog automatically. An EventBridge
rule fires the worker on a fixed cadence; the worker produces a list of new Spotify album
IDs (first source: `GET /browse/new-releases?country=KR`), filters out IDs already in the
DB, and feeds the novel IDs through the **existing** ingest pipeline (SQS → `sync_albums_batch`
upsert). The Spotify source is isolated behind one strategy function so it can be swapped
or removed without touching the pipeline. The existing batch-upsert path gains Spotify 429
retry so bulk ingest can't leak messages to the DLQ.

## Non-goals

- **Not** a display/feed feature. Surfacing new releases in the UI (per-review-artist cards,
  `/api/music/feed/new-releases`, an `artist_new_releases` table) is the separate Frozen idea
  **FEAT-new-release-feed** — this RFC only fills the catalog tables (`albums`/`tracks`/`artists`).
- **No DB migration / no provider change.** Storage is not the constraint: ~7 kB/album all-in,
  current footprint 16 MB / 936 albums, Neon Free 0.5 GB ≈ 70k-album headroom (70× current).
  Stay on Neon. The "limited capacity" cap here is a **curation policy**, not a storage wall.
- **No eviction / LRU.** Headroom is vast; deleting albums is out of scope.
- **No editorial ranking / chart import.** Spotify exposes no public chart/Top-50 API; the
  per-album `popularity` field (already stored) is the only ranking proxy and is untouched here.
- **No new user-facing endpoint.** Worker-internal only.

## Current state

- **Ingest is reactive only.** `/api/music/search/candidates`
  (`myblog_music/app/api/routers/search.py`) enqueues NEW album IDs to SQS `blogSQS`
  (`{"album_ids":[...],"market":"KR"}`, ≤20/msg). The worker consumer
  (`myblog_worker/worker/handler.py` → `_process_batch` → `AlbumSyncService.sync_albums_batch`,
  `worker/service/sync_service.py`) bulk-upserts artists→albums→album_artists→tracks→track_artists
  via raw SQL `ON CONFLICT DO UPDATE`. There is **no** "pull new albums" job.
- **Dedup primitive exists.** `AlbumRepository.get_existing_spotify_ids()` already filters
  known IDs (used by the candidates path).
- **Spotify client (client-credentials).** `worker/clients/spotify_client.py` — `get_albums`
  (multi-get `/albums?ids=`, ≤20), `get_album` single, `get_artists` (≤50). **No retry** on
  Spotify errors; a 429 propagates → SQS redelivers 3× → DLQ. Retry/backoff exists only in
  `spotify_user_client.py` (user-auth flow), not here.
- **Scheduled-job pattern exists.** `infra/eventbridge.tf` has two rules invoking
  `blogWorkerLambda`: alias-fill `rate(15 minutes)` (`source==aws.events`, 10 artists/tick) and
  listening-sync `rate(1 hour)` (constant input `{"job":"spotify_listening"}`). New jobs route
  on `event.get("job")` in `handler.py`.
- **Spotify access tier — Development Mode (probed 2026-06-10).** Despite the Feb-2026 changelog
  marking `/albums` multi-get, `/search`, and `/browse/new-releases` as `[REMOVED]`, a live
  client-credentials probe returned **HTTP 200 for all three** — existing integration is
  grandfathered (Dev-Mode enforcement postponed, not enforced). Treat new-releases + multi-get
  as **borrowed time**; `/search` and `/albums/{id}` are core metadata endpoints, lower removal risk.
  (See memory `reference-spotify-devmode-endpoints-live`.)

## Target state

- **New worker job** `{"job":"album_ingest"}`, routed in `handler.py` before the SQS-record branch.
- **Source-agnostic contract.** A strategy function `discover_new_album_ids() -> list[str]` is the
  only Spotify-coupled surface. First implementation: paginate
  `GET /browse/new-releases?country=KR` up to a bounded page count. Swapping/removing the source =
  replace this one function; the pipeline below is untouched.
- **Reuse the pipeline.** Job body: `discover` → `get_existing_spotify_ids()` filter →
  enqueue novel IDs to `blogSQS` (≤20/msg, same contract as candidates) → existing consumer upserts.
  Tick stays well under the 120 s Lambda budget (it only discovers + enqueues; heavy upsert runs in
  the SQS consumer under its 720 s visibility window).
- **429 retry on the batch path.** `spotify_client.SpotifyClient` honors `Retry-After` on 429 and
  retries 5xx (mirror `spotify_user_client` policy), so bulk ingest doesn't bleed to the DLQ.
- **Curation soft-cap.** `MAX_CATALOG_ALBUMS` setting; the job no-ops when `count(albums) >= cap`.
  Policy guardrail (not storage). Logged when it trips.
- **New EventBridge rule** `rate(1 day)` → `blogWorkerLambda` with constant input
  `{"job":"album_ingest"}`, plus IAM `sqs:SendMessage` to `blogSQS` on the worker role.

## Steps

### Step 1 — worker: 429/5xx retry on the client-credentials SpotifyClient

Add `Retry-After`-aware retry + bounded exponential backoff to `spotify_client.py`
(`get_albums`/`get_album`/`get_artists`), matching `spotify_user_client.py`'s policy
(retryable `{429,500,502,503,504}`, max 3 tries, `Retry-After` capped). Hardens the **existing**
reactive ingest too; independently mergeable and shippable before any new job exists.

**Verification**:
```
cd myblog_worker && pytest worker/tests -k "spotify and retry" -q
# new unit: mock httpx 429 (Retry-After: 1) then 200 → asserts one retry, no raise
```

---

### Step 2 — worker: `album_ingest` job (source-agnostic) + dedup + enqueue

- Add `discover_new_album_ids()` strategy (new-releases, `country=KR`, bounded pages) +
  an SQS-send client (`sqs:SendMessage` to `blogSQS`, ≤20 IDs/msg, reusing the candidates contract).
- Route `{"job":"album_ingest"}` in `handler.py`: cap-check (`MAX_CATALOG_ALBUMS`) → discover →
  `get_existing_spotify_ids()` filter → enqueue novel IDs. Structured `logger.info` of
  discovered/novel/enqueued counts (prod Lambda is `LOG_LEVEL=WARNING` → also emit a single
  `WARNING` summary line so it lands in CloudWatch).
- Config: `MAX_CATALOG_ALBUMS`, `NEW_RELEASE_PAGES` (or page-size/offset), `country` default `KR`.

**Verification**:
```
cd myblog_worker && pytest worker/tests -k album_ingest -q
# local invoke: handler({"job":"album_ingest"}) with mocked new-releases + mocked SQS send
#   → asserts known IDs filtered out, only novel IDs enqueued in ≤20 chunks, cap short-circuits
```

**Rollback**: job is additive and only fires on the new EventBridge rule (Step 3); not wiring
the rule = dead code, no behavior change.

---

### Step 3 — infra: EventBridge rule + worker SQS-send IAM

`infra/eventbridge.tf`: new `rate(1 day)` rule → `blogWorkerLambda`, constant input
`{"job":"album_ingest"}`, with the matching `aws_lambda_permission`. Add `sqs:SendMessage`
(+ `GetQueueUrl`) on `blogSQS` to the worker Lambda role.

**Verification**:
```
cd infra && terraform plan   # clean except the new rule + permission + IAM statement
# post-merge: manual one-shot invoke, then confirm albums row count rises + no DLQ growth
```

**Rollback**: `terraform apply` removing the rule stops all ingest immediately; Steps 1–2 stay inert.

---

## Open questions

1. **Enqueue-to-SQS vs inline upsert in the tick** — chosen: enqueue (reuse batch path + DLQ +
   stay under 120 s). Worker enqueues to the same `blogSQS` it consumes; confirm no feedback loop
   (it won't — consumer never enqueues) and IAM scoping. *Blocks Step 2.*
2. **`MAX_CATALOG_ALBUMS` value** — curation policy, not storage. Suggest 5,000 (5× current, still
   <0.1 GB). Owner picks. *Blocks Step 2 config.*
3. **Absorption rate per tick** — how many new albums/day to pull (`NEW_RELEASE_PAGES` × page size,
   chunked to ≤20/msg). Suggest a small bound (e.g. ≤100/day) to keep Spotify load + DLQ risk low.
   *Blocks Step 2.*
4. **Markets** — `country=KR` only, or add others later? KR-only for v1. *Blocks Step 2 strategy
   (additive later).*
5. **Source longevity** — new-releases is Dev-Mode borrowed time. If it 403s post-enforcement, the
   source-agnostic seam lets us swap to a `/search`-driven or editor-curated strategy with no
   pipeline change. *Risk, not a blocker.*

## Decisions log

| Date | Decision | Step |
|------|----------|------|
| 2026-06-10 | Source = `/browse/new-releases?country=KR`, automated EventBridge schedule, stay on Neon (storage not the constraint) | — |
| 2026-06-10 | Source-agnostic seam: pipeline reuses existing candidates→SQS→`sync_albums_batch` path | 2 |
