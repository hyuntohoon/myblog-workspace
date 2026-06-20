# FEAT-genre-artist-distribution: 분석 버킷 — 좋아요 트랙 장르/아티스트 분포

- **Status**: ✅ DONE — prod-live 2026-06-21 (all 6 steps shipped; owner-approved completion + archive)
- **Owner**: repo owner
- **Created**: 2026-06-21
- **Plan row**: dropped 2026-06-21 (done)

> **✅ Completion (2026-06-21).** All 6 steps shipped + prod-verified:
> - **Step 1** shared_db `spotify_saved_tracks` V24 + `SpotifySavedTrack` ORM, `v0.22.0` (ws #39).
> - **Step 2** worker `get_saved_tracks` + hybrid `run_saved_tracks_sync` (incremental / full+prune) + handler EventBridge/SQS branches (myblog_worker #47). 18 tests incl. 3 real-engine. **EventBridge cron rules = a follow-up Terraform infra PR (apply human-gated, rule #6); manual SQS drives it until then.**
> - **Steps 3+4** shared pure `rank_counts` module + saved-tracks & play-events `{genre,artist}-distribution` endpoints + list (myblog_backend #79).
> - **Step 5** `_safe_enqueue_*` lifted into `app/services/enqueue.py` (buckets unchanged) + `POST /saved-tracks/classify`. **Decision (owner-approved, option a):** classify is wired to the **catalog-sync** queue (`SqsClient.send_album_sync` → worker `_process_batch` → `AlbumSyncService` S1 genres), NOT the research enqueue — `enqueue_album` queues *editorial research notes* and never touches `album_genres`, so the literal "reuse 평론 버킷 enqueue" would have shipped a no-op button. Catalog-absent unclassified albums are enqueued; catalog-present-ungenred are reported as `skipped_needs_backfill` (need the manual iTunes backfill).
> - **Step 6** front `StatsTab` 통계 → **분석 버킷** (source toggle 좋아요/재생, shared `DistChart`, 미분류 chip + breakdown + 분류하기, recent-좋아요 list) (myblog_front #182).
> - **OQ4 resolved:** single 미분류 bucket + a (near-free) `uncatalogued/ungenred` breakdown in the response; the chart states "전체 N곡 중" as the denominator. **OQ5 (track-override authoring): deferred** to a later RFC.
> - **Counting contract:** each item → exactly one genre (`track_genres` override → `album_genres` inherit → 미분류) and one artist (full joined `artist_name` string, no splitting — keeps "Tyler, the Creator" intact); the play source is play-count-weighted. Clean partition `sum(count) + unclassified == total`.
> - **Prod-verified (real data):** 1,017 saved tracks synced; saved-genre 719/1017 unclassified (712 uncatalogued / 7 ungenred); play-genre 833 plays, 35 unclassified (0 uncatalogued). The two sources tell genuinely different stories — 71% of *likes* are uncatalogued vs 4% of *plays*.

> **History — 2026-06-15 correction (kept):** the original `FEAT-genre-taxonomy`
> dependency below was stale; superseded by **FEAT-genre-system** (tier-0 vocabulary +
> `album_genres` labels), **done + prod-live 2026-06-13**. Genre data exists now.
>
> **2026-06-21 pivot:** this RFC was a thin "carve" stub (a `/profile` genre + artist
> **listen** distribution from `spotify_play_events`). The owner's actual ask reshapes
> it: a **"분석 버킷"** on `/profile` built from the owner's **Spotify 좋아요(saved) 트랙**
> — browse them, classify by **genre + artist**, and see at a glance which dominate, with
> a **classification step** that pushes still-unclassified tracks through the existing
> album genre pipeline. The play-events listen distribution becomes a **sibling source**
> (Step 6, optional) sharing the same chart surface. Full body below; the carve rationale
> lives in `docs/archive/done/rfcs/FEAT-member-dashboard.md` (D29).

---

## Goal

After this RFC, `/profile` has a **분석 (analysis) 버킷** tab that lists the owner's
Spotify 좋아요(saved) tracks and renders two at-a-glance distributions — **장르별** and
**아티스트별** counts, ranked — so the owner can see which genres/artists dominate their
liked library. The same chart surface also renders a **second co-equal source — actual
play history** (`spotify_play_events`, already accumulating in prod) — switchable via a
**source toggle (좋아요 vs 재생)**: "what I *like*" vs "what I actually *listen to*", both
broken down by 장르 and 아티스트.

Saved tracks are pulled worker-side (never from a user-facing endpoint, hard rule #9) into
a `spotify_saved_tracks` cache table. Each track's genre resolves through the existing model
(`track_genres` override → else `album_genres` inherited); tracks whose album carries no
genre are surfaced as **미분류** with a manual **"분류하기"** action that enqueues their
albums into the existing catalog-sync + genre-backfill pipeline, after which the track
inherits a genre automatically. The play-history source is album-grain (`spotify_play_events`
rows carry `album_id`), so its genre resolves directly via `album_genres` and its artist via
the album's artist — no new table or sync needed.

## Non-goals

- **No new per-track genre classifier.** Spotify deprecated artist/track genres (2024-11);
  there is no track-level genre signal to model. Genre always derives from the album
  pipeline; `track_genres` stays a manual override table, not an auto-classifier.
- **No synchronous Spotify call** from any user-facing endpoint (hard rule #9). All Spotify
  reads run in the worker via EventBridge/SQS.
- **No per-user scoping / multi-user.** Saved tracks come from the single owner refresh
  token (`myblog/spotify`). Public exposure and multi-user analytics are out of scope
  (see `FEAT-multi-user-accounts`).
- **No track-grain `review_bucket`.** `review_bucket_items` are album-grain; the 분석 버킷
  is a `spotify_saved_tracks` cache + a `/profile` section, not a `review_buckets` row.
- **No writes back to Spotify** (no liking/unliking from myblog). Read-only mirror.
- **No recommendation / ranking of reviews** (that is `FEAT-genre-recommendation`).

## Current state

- **Worker Spotify user client** `myblog_worker/worker/clients/spotify_user_client.py`
  has `get_recently_played`, `get_currently_playing`, and saved-**album** methods
  (`get_saved_albums`, `check/save/remove_albums`, `/me/albums*`). **No `get_saved_tracks`
  (`GET /me/tracks`).** Token scopes already include **`user-library-read`** (used by the
  saved-albums read) — `/me/tracks` needs the *same* scope, so **no re-auth / token
  re-mint is required**.
- **Listening sync** `myblog_worker/worker/service/listening_sync_service.py` writes the
  recently-played window into `spotify_recent_tracks` (rolling cache) + durable play logs.
  This is the template for the worker's saved-tracks **write** path (raw `text()` SQL —
  the worker itself needs no shared_db pin bump). **Correction (Step 1, 2026-06-21):**
  the cache table *is* ORM-modeled in `shared_db` (`SpotifySavedTrack`) — every sibling
  Spotify cache table is, and backend `LibraryService` reads them via the ORM — so
  shared_db bumps `v0.21.0 → v0.22.0` and Step 3 backend pins `@v0.22.0`.
- **Saved-albums sync** `myblog_worker/worker/service/library_sync_service.py` reconciles
  `/me/albums` into the special `review_buckets.kind='spotify_library'` bucket — the
  precedent for a worker-fed Spotify mirror.
- **Genre model** (`myblog_shared_db/migrations/V17__genres.sql`): `genres`, `album_genres`,
  and **`track_genres` (override-only — a row exists iff the track deviates from its
  album)**. Effective rule: **track genre = `track_genres` rows if any, else the album's.**
  `album_genres` is populated by the genre backfill pipeline (`scripts/backfill_genres.py`
  + candidates→SQS catalog sync). Genre labels are Korean-localized (tier-0 live since
  2026-06-13).
- **Backend library routes** `myblog_backend/app/api/routes/library.py` already expose
  worker-fed caches read-only (`/api/library/recent-tracks`, `/listened-albums`,
  `now-playing`, …) via `LibraryService` — the pattern to extend with saved-tracks +
  distribution endpoints.
- **Existing 평론 버킷 classify/enqueue mechanism** `myblog_backend/app/api/routes/buckets.py`
  `_safe_enqueue_album` / `_safe_enqueue_bucket` → `research_service.enqueue_album` /
  `enqueue_bucket`: **fire-and-forget, best-effort** (rollback + log on failure, never fails
  the user op), **$0 mode = plain INSERT, else SQS**. This is the mechanism the owner wants
  the 분석 버킷 classification to reuse — **factored into a shared helper so both surfaces use
  one code path (통일성).**
- **`/profile` front** `myblog_front/src/components/member/ProfileApp.tsx` has tabs
  `overview / reviews / bucket` and an existing **`StatsTab`** (`통계`) / `SpotifyIntegrationTab`.
  **`StatsTab` is the rename target → "분석 버킷"; the work lands here, NOT a new tab.** Charts
  render client-side; `OverviewDash` already does a `chartStyle` bar/… toggle.

## Target state

- `spotify_saved_tracks` cache table (shared_db migration), worker-synced from `/me/tracks`.
- Worker `sync_saved_tracks` (EventBridge cron + manual SQS refresh), mirroring the saved
  set: upsert present, prune removed.
- Backend read + aggregation endpoints under `/api/library/saved-tracks*`:
  list, **genre-distribution**, **artist-distribution** — genre resolved via
  `track_genres → album_genres`, unclassified counted as **미분류**.
- A manual classification trigger: enqueue the albums of 미분류 saved tracks into the
  existing catalog-sync (candidates→SQS) + genre-backfill path.
- Backend aggregation endpoints for the **play-history source** under
  `/api/library/play-events/{genre,artist}-distribution` — group + count `spotify_play_events`
  by album genre (`album_genres`) and album artist. No new table/sync (data shipped V10).
- `/profile` **분석 버킷** tab with a **source toggle (좋아요 / 재생)**: ranked 장르/아티스트
  distribution charts for the selected source, the saved-track list, a **"미분류 분류하기"**
  action (saved source), and a last-synced stamp.

## Steps

> Cross-repo order follows `reference-shared-db-cross-repo-rollout`: migration applied to
> prod **before** the worker that reads it; contract (`openapi.json`) regenerated with the
> backend step; front types (`api.gen.ts`) regenerated after the workspace contract merge.

### Step 1 — shared_db: `spotify_saved_tracks` cache table ✅ DONE (prod-live 2026-06-21, `v0.22.0`, ws #39 → shared_db PR #39)

New migration `myblog_shared_db/migrations/V<next>__spotify_saved_tracks.sql`. Plain
`V{N}__` SQL (no Alembic), idempotent `CREATE TABLE IF NOT EXISTS`. Columns (denormalized,
mirrors `spotify_recent_tracks` so genre/artist render without a catalog join):

```
spotify_track_id  text PRIMARY KEY        -- always present (the /me/tracks item id)
track_name        text NOT NULL
artist_name       text                    -- "A, B" joined from item.track.artists
album_name        text
album_sid         text                    -- spotify album id (for catalog resolve / enqueue)
track_id          uuid NULL REFERENCES tracks(id)   -- resolved when in catalog
album_id          uuid NULL REFERENCES albums(id)   -- resolved when in catalog
added_at          timestamptz NOT NULL    -- item.added_at (Spotify "liked" time)
synced_at         timestamptz NOT NULL DEFAULT now()
```

Applied to prod (and the Neon test branch — `reference-neon-test-branch-migration-drift`)
before Step 2 merges.

**Verification**:
```
psql "$DATABASE_URL_psql" -c '\d spotify_saved_tracks'   # columns + FKs present
```

**Rollback**: `DROP TABLE IF EXISTS spotify_saved_tracks;` (cache only, no source of truth).

---

### Step 2 — worker: `get_saved_tracks` + `sync_saved_tracks`

`spotify_user_client.get_saved_tracks(since=None)` — paginate `GET /me/tracks?limit=50&offset=…`
(items come **`added_at` desc**; mirror `get_saved_albums`; reuse `user-library-read` scope
+ `_raise_for_scope`). When `since` is given, **stop paging once an item's `added_at <= since`**
(incremental); when `None`, page the whole library (full). New
`worker/service/saved_tracks_sync_service.py` (template: `listening_sync_service`), **hybrid
sync** (OQ3 — resolved):

- **Incremental (frequent, e.g. daily)** — `since = max(added_at)` from the cache → fetch
  only newer likes → upsert. Cheap; catches new 좋아요. **Does NOT prune** (early stop can't
  see removals).
- **Full reconcile (periodic, e.g. weekly)** — `since=None` → page the entire library →
  upsert all + **prune rows no longer present** so un-likes are dropped.

Both resolve `track_id`/`album_id` from the catalog when known. Drive the two cadences from
distinct EventBridge rules (or one rule + a day-of-week branch) + a manual
`{"job": "spotify_saved_tracks_sync", "mode": "incremental|full"}` SQS message. Best-effort
(`begin_nested` SAVEPOINT) so a failure never blocks the listening sync.

**Verification**:
```
cd myblog_worker && pytest tests/test_saved_tracks_sync.py
# incremental: seed cache + a newer-added stub → only the new item upserts, nothing pruned.
# full: seed cache with a since-removed track → full pass upserts present + prunes the removed.
```

**Rollback**: revert worker; cache table goes stale, no prod impact.

---

### Step 3 — backend: shared distribution module + saved-tracks endpoints + contract

**Shared aggregation module** (통일성) — a single `distribution_service` (e.g.
`app/services/distribution.py`) with source-agnostic helpers
`genre_distribution(items)` / `artist_distribution(items)` returning the ranked
`[{label, count}]` + `unclassified_count` shape. **Both** the saved-tracks source (this
step) and the play-events source (Step 4) call it — one ranking/미분류 contract, identical
response model, no duplicated counting logic.

`LibraryService` + `routes/library.py`:
- `GET /api/library/saved-tracks` — paginated list (denormalized columns + `_album_brief`
  when in catalog), `last_synced_at`.
- `GET /api/library/saved-tracks/genre-distribution` — per saved track resolve genre via
  `track_genres` (override) → else `album_genres` (inherit); feed into the shared
  `genre_distribution`; tracks with neither → **미분류**.
- `GET /api/library/saved-tracks/artist-distribution` — shared `artist_distribution` over
  `artist_name` (always available, catalog-independent), ranked desc.

Aggregation in SQL where possible. Export `openapi.json`, commit in the same PR
(`reference-openapi-pydantic-version-drift` — match CI pydantic).

**Verification**:
```
cd myblog_backend && pytest tests/api/test_saved_tracks.py
# genre-distribution: a track with album_genres only → inherits; with a track_genres
# override → override wins; with neither → counted in 미분류.
```

---

### Step 4 — backend: play-events distribution endpoints (co-equal source, shared module)

`spotify_play_events` (album-grain, shipped V10) feeds the **same** Step 3 shared module:
- `GET /api/library/play-events/genre-distribution` — resolve each event's album genre via
  `album_genres` → shared `genre_distribution`; no-genre albums → **미분류**.
- `GET /api/library/play-events/artist-distribution` — album's artist → shared
  `artist_distribution`.

No new table/sync (data already accumulating in prod). Same response model as Step 3, so the
front renders both sources through one chart component. Export `openapi.json` in the same PR.

**Verification**:
```
cd myblog_backend && pytest tests/api/test_play_events_distribution.py
# same shared-module assertions as saved-tracks; album_genres-only → inherits; none → 미분류.
```

---

### Step 5 — classification: reuse the 평론 버킷 enqueue, factored into a shared helper

The owner's directive: **classify the same way the 평론 버킷 already does**. Lift
`buckets.py`'s fire-and-forget `_safe_enqueue_album` / `_safe_enqueue_bucket` into a **shared
module** (e.g. `app/services/enqueue.py`); `buckets.py` keeps calling it (no behavior change)
and the 분석 버킷 classify route calls the **same** helper — one consistent enqueue path
(통일성). The manual **"분류하기"** action takes the distinct `album_sid` set of 미분류 saved
tracks and enqueues their albums (catalog-absent → candidates→SQS catalog sync;
present-but-genre-absent → genre-backfill) via that shared helper. Best-effort, $0 = INSERT
else SQS, never fails the request; **no per-track classifier, no synchronous Spotify/LLM in
the request path** (rule #9). After the worker runs, `album_genres` fills → the track inherits.

`POST /api/library/saved-tracks/classify`.

**Verification**:
```
# enqueue a known 미분류 album_sid via the shared helper → assert the SAME enqueue row the
# 평론 버킷 path produces (no genre computed in-request); after a worker tick, the album
# moves out of 미분류 in the distribution.
```

**Rollback**: revert the route; the shared helper + 평론 버킷 path are untouched;
`backfill_genres.py` remains the manual fallback.

---

### Step 6 — front: rename `StatsTab` → **분석 버킷**, dual-source charts + classify

`ProfileApp.tsx` / `StatsTab` (NOT a new tab): rename the `통계` tab to **분석 버킷** and build
the surface here — a **source toggle (좋아요 / 재생)** over one shared chart component (장르 /
아티스트, reuse the `chartStyle` bar pattern), the saved-track list, a **미분류 N곡** chip with
a **"분류하기"** button (calls Step 5 via `apiFetch`), and a last-synced stamp. Both sources
hit the identical distribution response shape, so the chart component is source-agnostic
(통일성). Regenerate `api.gen.ts` after the workspace contract merge
(`feedback-frontend-api-gen-sync`). Browser click-through required (DoD; lint +
`astro check` miss render/event regressions).

**Verification**:
```
cd myblog_front && pnpm lint && pnpm exec astro check
# + browser click-through: 분석 버킷 renders, source toggle swaps 좋아요/재생, charts rank,
#   분류하기 fires, 미분류 count correct.
```

---

## Open questions

1. ~~**Surface shape**~~ — **RESOLVED 2026-06-21:** rename the existing `StatsTab` (`통계`) to
   **분석 버킷**; no new tab.
2. ~~**Classification mechanism**~~ — **RESOLVED 2026-06-21:** reuse the 평론 버킷 enqueue
   path, factored into a shared helper (통일성). Trigger is the manual **"분류하기"** button
   (owner-fired, $0-bias); an auto-on-sync toggle can come later.
3. ~~**Saved-tracks sync strategy**~~ — **RESOLVED 2026-06-21: hybrid** (Step 2). Daily
   `added_at`-incremental for new likes (no prune) + weekly full reconcile (upsert all +
   prune) to drop un-likes. Pure incremental misses removals; hybrid is the cheap-but-correct
   middle.
4. **미분류 denominator** — does the genre chart's 미분류 count tracks-with-no-resolved-genre,
   or also tracks whose album simply isn't in the catalog yet? State the denominator on the
   chart (`feedback-rfc-success-gate-denominator`). Applies to both sources. Blocks Step 3/4 copy.
5. **Album-grain vs track-grain genre display** — a saved track inherits its album genre;
   finer granularity = a hand-authored `track_genres` override. Override-authoring affordance
   in scope or a later RFC? *Lean: later.*

## Decisions log

Filled in during execution.

| Date | Decision | Step |
|------|----------|------|
| 2026-06-21 | Both sources are co-equal (owner: "재생 기록도 + 좋아요 분석도"): one chart surface, source toggle 좋아요/재생. Saved-tracks is new (table+sync); play-events reuses shipped data. | 3,4,6 |
| 2026-06-21 | No new per-track classifier; genre derives from album pipeline, track inherits via `track_genres → album_genres`. | 5 |
| 2026-06-21 | Surface = rename existing `StatsTab` (`통계`) → **분석 버킷**, not a new tab (owner). | 6 |
| 2026-06-21 | Classification reuses the 평론 버킷 `_safe_enqueue_*` mechanism, factored into a shared helper so both surfaces share one code path (owner: 통일성). | 5 |
| 2026-06-21 | Distribution counting lives in one shared `genre/artist_distribution` module used by both sources (통일성). | 3,4 |
| 2026-06-21 | Saved-tracks sync = hybrid: daily `added_at`-incremental (no prune) + weekly full reconcile (prune un-likes). | 2 |
| 2026-06-21 | **Step 1 ships a `SpotifySavedTrack` ORM model** alongside the migration — every sibling Spotify cache table is ORM-modeled and backend `LibraryService` queries them via the ORM, so the "no ORM pin bump" assumption was wrong. shared_db bumped `v0.21.0 → v0.22.0`; Step 3 backend pins `@v0.22.0`. | 1,3 |
| 2026-06-21 | **Step 1 ships a single `added_at` index** (no `album_id` index). Step 3/4 genre/artist distribution is a full-set `GROUP BY` with no `album_id` predicate, the `album_genres` join is covered by that table's own PK, and at owner-only scale a secondary index sits inert while adding write cost on every reconcile — matches sibling precedent (V14/V19 index their time column alone). | 1 |
| 2026-06-21 | **Release = push the git tag to origin.** Consumers pin shared_db by *remote* git ref (`git+https://…@v0.22.0`); there is no PyPI publish, so `git tag -a v0.22.0 && git push origin v0.22.0` on the squash-merge commit IS the release. Without it Step 3 cannot `pip install @v0.22.0`. | 1,3 |
