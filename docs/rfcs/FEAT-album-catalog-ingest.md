# FEAT-album-catalog-ingest: Scheduled known-artist album ingest (curated, lean catalog)

- **Status**: accepted (owner "이걸로 가 accept" 2026-06-10 — new-releases-only mode + default gates)
- **Owner**: 박지훈
- **Created**: 2026-06-10
- **Plan row**: `plan.md` → FEAT-album-catalog-ingest

---

## Goal

A scheduled, source-agnostic job grows the music catalog with **only review-relevant albums**:
full-length releases by artists already in the catalog that clear a popularity gate
("famous, or something we plan to use" — owner's curation bar, 2026-06-10). An EventBridge
rule fires the worker daily; the worker rotates through gate-passing catalog artists, pulls
their discographies via `GET /artists/{id}/albums?include_groups=album`, filters, dedups
against the DB, and feeds novel IDs through the **existing** ingest pipeline
(SQS → `sync_albums_batch` upsert). The Spotify source sits behind one strategy function so
it can be swapped without touching the pipeline. The batch-upsert path gains Spotify 429
retry so bulk ingest can't leak messages to the DLQ.

## Non-goals

- **Not** a display/feed feature. Surfacing new releases in the UI (`artist_new_releases`
  table, `/api/music/feed/new-releases`, main-page cards) is the separate Frozen idea
  **FEAT-new-release-feed** — this RFC only fills catalog tables (`albums`/`tracks`/`artists`).
- **No `browse/new-releases` source.** Evaluated and rejected on evidence — see Current state.
- **No singles/compilations ingest.** `include_groups=album` only. Reactive candidates path
  (search-on-write) still ingests whatever the editor explicitly picks, singles included —
  "쓸 계획이 있는" is already covered by that path.
- **No DB migration / no provider change.** Storage is not the constraint: ~7 kB/album all-in,
  16 MB / 936 albums today, Neon Free 0.5 GB ≈ 70k-album headroom. The cap here is a
  **curation policy**, not a storage wall. No eviction/LRU.
- **No editorial ranking / chart import.** Spotify has no public chart API; per-album
  `popularity` (already stored) is the only ranking proxy.
- **No new user-facing endpoint.** Worker-internal only.

## Current state

- **Ingest is reactive only.** `/api/music/search/candidates`
  (`myblog_music/app/api/routers/search.py`) enqueues NEW album IDs to SQS `blogSQS`
  (`{"album_ids":[...],"market":"KR"}`, ≤20/msg). The worker consumer
  (`myblog_worker/worker/handler.py` → `_process_batch` → `AlbumSyncService.sync_albums_batch`,
  `worker/service/sync_service.py`) bulk-upserts artists→albums→album_artists→tracks→track_artists
  via raw SQL `ON CONFLICT DO UPDATE`. There is **no** scheduled "pull albums" job.
- **Dedup primitive exists.** `AlbumRepository.get_existing_spotify_ids()` already filters
  known IDs (candidates path).
- **Spotify client (client-credentials).** `worker/clients/spotify_client.py` — `get_albums`
  (multi-get ≤20), `get_album`, `get_artists` (≤50). **No retry** on Spotify errors; a 429
  propagates → SQS redelivers 3× → DLQ. Retry/backoff exists only in `spotify_user_client.py`.
- **Scheduled-job pattern exists.** `infra/eventbridge.tf`: alias-fill `rate(15 minutes)`
  (10 artists/tick, cursor = `musicbrainz_id IS NULL`) and listening-sync `rate(1 hour)`
  (constant input `{"job":"spotify_listening"}`). New jobs route on `event.get("job")`.
- **Catalog quality baseline (prod probe 2026-06-10).** 936 albums / 1,553 artists;
  artist popularity p50=40, p75=55, p90=71; **305 artists ≥60, 400 ≥55**. Album types already
  56% singles (from the reactive path).
- **`browse/new-releases` is rotten — rejected as source (live probe 2026-06-10).** The KR
  feed (100 items) returned release dates **2023-10 … 2025-07 only — zero 2026 entries**
  (probe date 2026-06-10), 73% one-to-two-track singles, mostly non-KR EDM/J-pop. The
  endpoint still answers HTTP 200 but is unmaintained ahead of its announced removal
  (Feb-2026 changelog `[REMOVED]`, Dev-Mode enforcement postponed). Stale + junk-dominated =
  exactly the catalog pollution this RFC must avoid.
- **`GET /artists/{id}/albums` is alive AND fresh (live probe 2026-06-10).** Not on the
  removal list; returns current data (BTS → 2026-03-27 release; Taylor Swift → 2025-11-07).
  Multi-get `/albums?ids=`, `/artists?ids=`, `/search` also probed 200 (existing integration
  grandfathered — memory `reference-spotify-devmode-endpoints-live`).

## Target state

- **New worker job** `{"job":"album_ingest"}`, routed in `handler.py` before the SQS-record branch.
- **Source-agnostic contract.** `discover_new_album_ids(session) -> list[str]` is the only
  Spotify-coupled surface; swapping sources never touches the pipeline.
- **First source: known-artist discography sweep, NEW-RELEASES-ONLY mode (owner-accepted).**
  - Eligible artists: `artists.popularity >= ARTIST_POP_MIN` (default 60 → 305 artists today).
    Catalog membership = "plan to use"; popularity gate = "famous".
  - Per tick, take the next `SWEEP_ARTISTS_PER_TICK` (default 30) eligible artists in stable
    order (cursor pattern like alias-fill) → `GET /artists/{id}/albums?include_groups=album`
    (full-lengths only; no singles/compilations/appears_on) → keep only
    `release_date >= INGEST_SINCE` (set to the deploy date → **no back-catalog backfill**;
    the reactive candidates path remains the on-demand route for older albums).
  - Dedup via `get_existing_spotify_ids()` → multi-get full albums for the novel IDs →
    drop `popularity < ALBUM_POP_MIN` (default 20; sheds dead variants/track-by-track
    editions) → enqueue survivors to `blogSQS` (≤20/msg, same contract as candidates),
    bounded by `MAX_ENQUEUE_PER_TICK` (default 60).
  - Expected volume: ~150 albums/yr (305 artists × ~0.5 full-length/yr); zero initial burst.
    A day-0 album below `ALBUM_POP_MIN` is re-evaluated on the next sweep cycle
    (~`305/30` ≈ 10 days) — self-healing, no extra state; accepted trade-off = up to one
    sweep-cycle ingest delay. Backfill later = relax `INGEST_SINCE` (config-only).
- **429 retry on the batch path.** `spotify_client.SpotifyClient` honors `Retry-After` on 429
  and retries 5xx (mirror `spotify_user_client` policy).
- **Curation soft-cap.** `MAX_CATALOG_ALBUMS` (default 5,000); job no-ops + warns when
  `count(albums) >= cap`.
- **New EventBridge rule** `rate(1 day)` → `blogWorkerLambda`, constant input
  `{"job":"album_ingest"}`; worker role gains `sqs:SendMessage` on `blogSQS`.

## Steps

### Step 1 — worker: 429/5xx retry on the client-credentials SpotifyClient

Add `Retry-After`-aware retry + bounded exponential backoff to `spotify_client.py`
(`get_albums`/`get_album`/`get_artists`, + the new artist-albums call), matching
`spotify_user_client.py` policy (retryable `{429,500,502,503,504}`, max 3 tries,
`Retry-After` capped). Hardens the existing reactive ingest too; independently mergeable.

**Verification**:
```
cd myblog_worker && pytest worker/tests -k "spotify and retry" -q
# new unit: mock httpx 429 (Retry-After: 1) then 200 → asserts one retry, no raise
```

---

### Step 2 — worker: `album_ingest` job (discography sweep + gate + dedup + enqueue)

- `spotify_client.py`: add `get_artist_albums(artist_id, include_groups="album")` (paginate).
- New `discover_new_album_ids(session)`: eligible-artist query
  (`popularity >= ARTIST_POP_MIN`, stable cursor, `SWEEP_ARTISTS_PER_TICK` per tick) →
  discography fetch → `release_date >= INGEST_SINCE` filter → DB dedup → multi-get novel
  albums → `ALBUM_POP_MIN` gate → return ≤ `MAX_ENQUEUE_PER_TICK` IDs.
- SQS-send client (≤20 IDs/msg, candidates contract). Route `{"job":"album_ingest"}` in
  `handler.py`: cap-check → discover → enqueue. Single `WARNING` summary line
  (prod `LOG_LEVEL=WARNING`): swept/discovered/novel/gated/enqueued counts + cursor pos.
- Config (owner-accepted defaults): `ARTIST_POP_MIN=60`, `ALBUM_POP_MIN=20`,
  `SWEEP_ARTISTS_PER_TICK=30`, `MAX_ENQUEUE_PER_TICK=60`, `MAX_CATALOG_ALBUMS=5000`,
  `INGEST_SINCE=<deploy date>` (new-releases-only; relax for backfill).

**Verification**:
```
cd myblog_worker && pytest worker/tests -k album_ingest -q
# unit: mocked discography + mocked SQS → asserts: singles never requested (include_groups),
#   known IDs filtered, low-pop albums gated, ≤20/msg chunks, per-tick cap, catalog cap short-circuit,
#   cursor advances and wraps
```

**Rollback**: additive; without the Step 3 rule it is dead code.

---

### Step 3 — infra: EventBridge rule + worker SQS-send IAM

`infra/eventbridge.tf`: `rate(1 day)` rule → `blogWorkerLambda`, constant input
`{"job":"album_ingest"}`, matching `aws_lambda_permission`. Worker role: `sqs:SendMessage`
(+ `GetQueueUrl`) on `blogSQS`.

**Verification**:
```
cd infra && terraform plan   # clean except new rule + permission + IAM statement
# post-merge: one-shot manual invoke → albums count rises only with gate-passing full-lengths,
#   no DLQ growth, WARNING summary visible in CloudWatch
```

**Rollback**: `terraform apply` removing the rule stops ingest immediately; Steps 1–2 inert.

---

## Open questions

1. ~~`ARTIST_POP_MIN`~~ — **resolved: 60** (305 artists). Owner-accepted 2026-06-10.
2. ~~`ALBUM_POP_MIN`~~ — **resolved: 20**; accepted trade-off = up to one sweep cycle (≤10 d)
   ingest delay for day-0 albums (re-evaluated each sweep; dead variants stay filtered).
3. ~~Backfill appetite~~ — **resolved: new-releases-only** (`INGEST_SINCE` = deploy date).
   Back-catalog stays on-demand via the reactive candidates path; backfill later is a
   config-only change.
4. **EPs** — Spotify tags most EPs `album_type=single`, so `include_groups=album` excludes
   them. Including EPs would require `include_groups=album,single` + `total_tracks >= 4`
   heuristic — junk risk. Default: exclude; editor can still add any EP via search. Revisit
   only if missed EPs become a felt gap. *Step 2 (non-blocking).*
5. **Source longevity** — `/artists/{id}/albums` not on the Feb-2026 removal list and probed
   fresh, but the app is Dev Mode; if it degrades, the `discover_new_album_ids` seam swaps to
   `/search`-driven or editor-curated lists with no pipeline change. *Risk, not a blocker.*

## Decisions log

| Date | Decision | Step |
|------|----------|------|
| 2026-06-10 | Automated EventBridge schedule; stay on Neon (storage not the constraint; cap = curation policy) | — |
| 2026-06-10 | Source-agnostic seam; pipeline reuses candidates→SQS→`sync_albums_batch` | 2 |
| 2026-06-10 | **`browse/new-releases` rejected**: live probe showed stale (2023–2025-07 only, zero 2026) + 73% junk singles — fails owner's "famous or planned-use" bar | 2 |
| 2026-06-10 | Source = known-artist discography sweep (`/artists/{id}/albums`, probed fresh) + artist/album popularity gates + full-lengths only | 2 |
| 2026-06-10 | **Owner accept** ("이걸로 가 accept"): mode A new-releases-only; `ARTIST_POP_MIN=60`, `ALBUM_POP_MIN=20`, sweep 30/day, cap 5000. Status → accepted | — |
