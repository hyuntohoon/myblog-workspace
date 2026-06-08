# FEAT-member-dashboard-realdata: `/profile` — drafts + durable listening data

- **Status**: in-progress
- **Owner**: TBD
- **Created**: 2026-06-08
- **Accepted**: 2026-06-08 (owner approval in-session — promote + start parallel work)
- **Plan row**: `plan.md` → FEAT-member-dashboard-realdata

---

## Goal

Make `/profile` a real personal dashboard backed by durable data instead of sample/cache-only
surfaces. After this RFC: (1) the 평론 tab shows **draft** reviews alongside published ones,
visually distinct; (2) the member page shows an **accumulated "들은 앨범"** archive derived from
the cumulative `spotify_play_events` log (not the 50-item rolling cache); (3) a **"최근 재생 트랙"**
section reflects track-level recent listening; (4) the now-playing surface shows **"재생 중"** when
playback is live and **"최근 재생"** (the latest played track) when it is not; and (5) the four
listening/writing concepts are cleanly separated in both data model and UI. This durable listening
+ writing data is the foundation the future AI editorial critic (FEAT-ai-editorial-critique) needs.

## Non-goals

- **No new Spotify scopes or API calls.** Track-level recency comes for free from the
  `/me/player/recently-played` response the worker already fetches — only the persistence changes.
  No synchronous Spotify call on any user-facing endpoint (hard rule #9).
- **No rollup table for listened-albums.** Goal 2 aggregates the existing append-only
  `spotify_play_events` (V10) on read. No `spotify_listened_albums` table (decided 2026-06-08, D-A —
  personal-scale read cost is negligible; a dedicated rollup is premature optimization).
- **No multi-user.** `/profile` stays the single admin's own page. Social stats remain hidden
  (FEAT-multi-user-accounts owns that).
- **No genre/artist distribution charts.** That is FEAT-genre-artist-distribution (also reads
  `spotify_play_events`); this RFC must not duplicate its aggregation surface.
- **No Spotify write actions** (save/playlist/library-modify) — deferred per FEAT-member-dashboard D11.
- **No live progress bar** on now-playing (FEAT-member-dashboard D28 — vanity read, ≤1h stale).
- **No change to `now_playing` worker clearing.** "Latest played" is sourced from the recent-tracks
  head, keeping `now_playing` an honest live-only snapshot (preserves concept separation, Goal 5).
- **No retention/purge of `spotify_play_events`.** It becomes the durable source for Goal 2 and must
  be kept; a purge/rollup policy is a future concern (OQ3).

## Current state

Most of `/profile` is already shipped (FEAT-member-dashboard, archived). Verified against code
2026-06-08:

- **Drafts (Goal 1)**: `posts.status` is a PG enum `draft|published|archived`
  (`myblog_shared_db/.../models.py` Post). `GET /api/posts?status=draft` already returns drafts
  (`myblog_backend/app/api/routes/posts.py`, `require_cognito_token`). But `/profile` 평론 tab
  (`myblog_front/src/components/member/ReviewsTab.tsx`) is fed by **build-time** `getCollection('blog')`
  (published MDX only) via `profile.astro` → drafts are invisible. Publish writes MDX to the content
  repo; drafts live only in the DB. `PostListItem` (schemas.py) lacks `album_cover_url`.
- **Listened albums (Goal 2)**: `spotify_play_events` (V10) is an **append-only cumulative** log,
  deduped by `UNIQUE (album_id, played_at)`, written every worker tick for **catalog-known albums
  only** (`worker/service/listening_sync_service.py`, D29). **No endpoint exposes it.** The only
  user-facing listening surface is the 50-item **cache** `spotify_recent_albums` (V9) via
  `GET /api/library/recently-listened`.
- **Recent tracks (Goal 3)**: the worker fetches `/me/player/recently-played?limit=50` (track-level,
  newest first) but **discards track identity** after deriving albums. There is **no track-level
  store**. `myblog_front/src/lib/member.ts` `getRecentTracks()` still returns **sample** data
  (`member.sample.ts RECENT_TRACKS`), rendered in `OverviewDash.tsx` (`recent-tracks` coll).
- **Now / latest played (Goal 4)**: real and wired — `spotify_now_playing` (V9, singleton) via
  `GET /api/library/now-playing`, rendered by `NowPlaying.tsx`. When playback stops the worker
  upserts `is_playing=false` **with cleared track fields** (`sync_now_playing`), so "latest played"
  is not recoverable from this table.
- **Concept separation (Goal 5)**: today only `recent_albums` (cache) vs `play_events` (log) vs
  `now_playing` (live) exist; track-level and cumulative-album surfaces are absent or sample.
- **Schema version**: highest migration on disk is **V13**; shared_db package is **v0.13.0**. Next
  free migration is **V14** (plan.md soft-reserved V14 for the *deferred* genre-taxonomy, which holds
  no migration in code yet — see OQ5).
- **⚠️ Concurrent front session**: `myblog_front` is on branch `chore/copy-cleanup` with
  **uncommitted edits** to the exact member components this RFC touches (`ProfileApp`, `ReviewsTab`,
  `OverviewDash`, `NowPlaying`, `LibraryTab`, `SpotifyIntegrationTab`). Front work here runs in an
  **isolated worktree off `origin/main`** (decided D-C); merge-conflict reconciliation with that
  branch is expected.

## Target state — the five concepts, separated (Goal 5)

| Concept | Store | Nature | Surface |
|---|---|---|---|
| Raw listening activity | `spotify_play_events` (V10, existing) | append-only cumulative event log | source for Goal 2 (not shown directly) |
| Accumulated 들은 앨범 | *aggregate of* `spotify_play_events` | derived: per-album `play_count`, first/last | `GET /api/library/listened-albums` → new section |
| Temporary recent cache (albums) | `spotify_recent_albums` (V9, existing) | 50-item rolling cache | `GET /api/library/recently-listened` (unchanged) |
| 최근 재생 트랙 | `spotify_recent_tracks` (V14, **new**) | rolling track-level cache | `GET /api/library/recent-tracks` → new section; head = "최근 재생" |
| Currently / latest played | `spotify_now_playing` (V9, existing) | singleton live snapshot | `GET /api/library/now-playing`; fallback to recent-tracks head |
| Writing state | `posts.status` (existing) | draft / published / archived | `GET /api/posts?status=draft` → draft cards in 평론 tab |

## Steps

Steps follow the shared_db cross-repo rollout order (migration → prod apply **before merge of
dependents** → service pin bump → contract → frontend). Each step is one session per hard rule #4
unless marked otherwise; Steps 2 and 3 are **additive** (new table/endpoints, no behavior change to
existing surfaces) and independent of each other once Step 1 is in prod.

### Step 1 — shared_db: `V14__spotify_recent_tracks` + model + bump

New rolling track-level cache. Denormalized text so non-catalog tracks still display; `album_id`
nullable FK links to the catalog when present.

```sql
CREATE TABLE spotify_recent_tracks (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    spotify_track_id TEXT NOT NULL,
    track_name       TEXT NOT NULL,
    artist_name      TEXT,
    album_name       TEXT,
    album_id         UUID REFERENCES albums(id) ON DELETE SET NULL,
    played_at        TIMESTAMPTZ NOT NULL,
    source           TEXT NOT NULL DEFAULT 'spotify',
    synced_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_spotify_recent_tracks_play UNIQUE (spotify_track_id, played_at)
);
CREATE INDEX idx_spotify_recent_tracks_played_at ON spotify_recent_tracks (played_at DESC);
```

Add `SpotifyRecentTrack` to `models.py`; bump package to **v0.14.0**. Apply V14 to the Neon prod
**and** test branches (REQUIRED before Step 2/3 merge — rollout order).

**Verification**:
```
cd myblog_shared_db && uv run pytest tests/test_schema_parity.py
# apply: psql "$DATABASE_URL_pg" -v ON_ERROR_STOP=1 -f migrations/V14__spotify_recent_tracks.sql
```
**Rollback**: `DROP TABLE spotify_recent_tracks;` (no dependents until Step 2 deploys).

---

### Step 2 — worker: persist recent tracks (additive)

In `listening_sync_service.sync_recent` (or a sibling), after the existing album/play-event writes,
upsert the **track-level** rows from the same `/me/player/recently-played` payload:
`INSERT ... ON CONFLICT (spotify_track_id, played_at) DO NOTHING`, resolving `album_id` from the
catalog when the album spotify_id is known (else NULL). Then **prune to the most recent 50**
(`DELETE ... WHERE id NOT IN (SELECT id ... ORDER BY played_at DESC LIMIT 50)`) — this is a cache,
not a log. No change to `now_playing` clearing. Pin shared_db **v0.14.0**.

**Verification**:
```
cd myblog_worker && uv run pytest tests/test_listening_sync.py tests/integration/test_listening_sync_db.py
# integration is real-engine (TEST_DB_URL); assert: upsert idempotency on overlapping windows + prune to 50 + non-catalog track stored with album_id NULL
```
**Rollback**: revert worker; the table simply stops being written (reads return stale/empty).

---

### Step 3 — backend: read endpoints + draft-card field + contract (additive)

Pin shared_db **v0.14.0**. Add:

- `GET /api/library/recent-tracks` (edge_guard GET) → `{ items: [{spotify_track_id, track_name,
  artist_name, album_name, album_id?, played_at, album?}], last_synced_at }`, newest first.
  Serves Goal 3; `items[0]` is the "최근 재생" fallback for Goal 4.
- `GET /api/library/listened-albums` (edge_guard GET) → aggregate over `spotify_play_events`:
  `{ items: [{album_id, play_count, first_played_at, last_played_at, album}], total }`, ordered by
  `last_played_at DESC`, paginated (`limit`/`offset`). Serves Goal 2.
- Add `album_cover_url` to `PostListItem` (it is already a `Post` column) so draft cards render a
  cover without an extra fetch. Serves Goal 1.

Export `openapi.json` in the backend PR; **merge workspace contract first** (regenerates
`docs/contracts/openapi.json`), then regenerate front `api.gen.ts` (`pnpm generate:types`).

**Verification**:
```
cd myblog_backend && uv run pytest    # incl. real-engine integration for the listened-albums aggregate
cd .. && python scripts/merge_openapi.py   # + front: pnpm generate:types (api.gen.ts committed)
```
**Rollback**: revert backend + contract; reads disappear, front degrades to sample (Step 4 not yet shipped).

---

### Step 4 — frontend: drafts + listening surfaces (isolated worktree off `origin/main`)

Per D-C, work in a `git worktree add` off `origin/main` (symlink `node_modules`, copy gitignored
`.env`), **not** the `copy-cleanup` checkout. Reconcile/rebase against `copy-cleanup` before merge.
Four surfaces (may split into 4a drafts / 4b listening if the diff is large):

- **Goal 1** — `ReviewsTab.tsx`: fetch `GET /api/posts?status=draft` via `apiFetch`; render draft
  cards with a distinct **"초안"** badge and visual treatment, separated from published reviews.
- **Goal 3** — swap `member.ts getRecentTracks()` sample → real `GET /api/library/recent-tracks`
  (new `spotify.api.ts` fn); update `OverviewDash` `recent-tracks` coll. Remove `RECENT_TRACKS` sample.
- **Goal 2** — new **"들은 앨범 (누적)"** section reading `GET /api/library/listened-albums`,
  clearly distinct from the existing **"최근 들은 앨범"** (cache) section (Goal 5 labeling).
- **Goal 4** — `NowPlaying.tsx`: when `is_playing` → **"재생 중"**; else show recent-tracks head
  labeled **"최근 재생"**.

**Verification**: `pnpm lint` + `pnpm exec astro check` (Node 20); CDP click-through of the
auth-gated `/profile` (seed `access_token` to pass the guard) confirming draft cards render, real
recent tracks load, the listened-albums section is distinct from the cache, and the now/latest label
flips. (lint + astro-check alone miss render/event regressions — BUG-11/12.)
**Rollback**: revert front; surfaces fall back to sample / hidden.

---

## Open questions

1. **`listened-albums` ordering / `play_count` exposure** — order by `last_played_at` (recency) or
   `play_count` (most-played)? Expose `play_count` in the UI, or keep it internal for the AI critic?
   Blocks Step 3 response shape + Step 4 section design. *(default: order by `last_played_at`, expose count.)*
2. **`spotify_recent_tracks` window size** — keep 50 (match the album cache) or smaller for a tighter
   "recent" feel? Blocks Step 2 prune constant. *(default: 50.)*
3. **`spotify_play_events` retention** — it is now the durable Goal-2 source and must not be purged.
   Confirm "keep forever"; revisit a rollup/archive only if it grows large. Blocks nothing now;
   flags a future concern. *(default: keep forever, no purge.)*
4. **Draft card album metadata** — is `album_cover_url` (single cover column) enough, or should draft
   cards also show linked album/artist via the `post_albums` join? Blocks Step 3 schema breadth.
   *(default: `album_cover_url` only; no extra join.)*
5. **V14 vs genre-taxonomy reservation** — plan.md soft-reserved V14 for the deferred
   FEAT-genre-taxonomy (no migration in code). Taking V14 here means genre-taxonomy re-confirms its
   number (V15) at un-defer. Confirm OK. *(default: take V14; note the bump in genre-taxonomy RFC.)*

## Decisions log

| Date | Decision | Step |
|------|----------|------|
| 2026-06-08 | **D-A** Goal 2 aggregates existing `spotify_play_events` on read; **no** `spotify_listened_albums` rollup table (negligible read cost at personal scale; avoid premature optimization). | 3 |
| 2026-06-08 | **D-B** Goal 3 uses a **new** `spotify_recent_tracks` rolling cache (denormalized + nullable album FK) rather than adding track columns to `play_events` — keeps cache vs cumulative-log concepts separate (Goal 5). | 1,2 |
| 2026-06-08 | **D-C** Goal 4 "latest played" = head of `spotify_recent_tracks`; `now_playing` stays live-only (no worker clearing change). Front work runs in an isolated worktree off `origin/main`, concurrent with the `chore/copy-cleanup` session. | 4 |
