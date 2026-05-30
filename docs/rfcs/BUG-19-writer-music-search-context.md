# BUG-19: writer music search — 1-hop cross-expansion + full participating artist display

- **Status**: closed (shipped 2026-05-30, plan row dropped via workspace #150 — see `docs/archive/done/2026-05.md`)
- **Owner**: TBD
- **Created**: 2026-05-29 (redesigned 2026-05-30)
- **Plan row**: dropped 2026-05-30

---

## Goal

On any music-search query in the writer page (`myblog_front/src/components/writer/SubjectBlock.tsx`) and the global search bar (`myblog_front/src/scripts/searchBarDb.client.ts`), the unified DB endpoint performs literal matching across artist / album / track, then **expands one hop** along the existing relations, then buckets, dedups, ranks, and returns all three buckets in a single response. Track rows display every participating artist — `${primary} (feat. Y, Z)` — irrespective of whether the track title text already contains "feat. X". The two symptoms previously framed as separate work items (feat-artist display + artist → album / track related search) are one feature with one mechanism.

## Non-goals

- **Track popularity** schema / sync / backfill. Tracks have no `popularity` column today. The track bucket uses path-dependent ranking (see Target state). When a future schema batch adds `Track.popularity`, only the expansion-path sort key is swapped — out of scope here.
- **Multi-hop expansion.** An album match expands to its artist, but **not** to that artist's _other_ albums. "Other albums by this artist" lives behind tapping the artist (artist-detail), not in the first search response.
- **"Similar albums" recommendation** (genre / popularity similarity). Separate project, separate RFC if it ever lands.
- **Image re-download on filter switch.** Real bug but a separate frontend rendering / caching issue (likely remount / unstable `key` / cache-busting querystring). File separately; do not fold into this RFC.
- **MusicBrainz alias refinement** (BUG-14). Independent track.
- **Track-title "feat. X" normalization.** Leave the Spotify-supplied title as-is; do not strip or rewrite.
- **Spotify-sync changes.** The worker already stores every participating artist of every track in `track_artists` as a pure N:N (`myblog_worker/worker/service/sync_service.py`). Do not touch.
- **`AlbumDetail.TrackOut.feat_artist_names` rule.** The album-detail service uses `if ta.id not in album_artist_ids` because it has album-artist metadata to compare against. The unified-search `TrackItem.feat_artist_names` uses `if a.name != primary` because the search response carries no album-artist metadata. The two rules differ intentionally; do not unify.

## Current state

**DB / sync — unchanged baseline**

- `myblog_shared_db/src/myblog_shared_db/models.py:46-51` — `track_artists` is a pure N:N (`track_id`, `artist_id`, `role`). No `position` column; main artists and featured artists are stored as identical rows.
- `myblog_shared_db/src/myblog_shared_db/models.py:39-44` — `album_artists` likewise. No `position` column.
- `myblog_shared_db/src/myblog_shared_db/models.py:128-133, 159-161, 190-192` — `Track.artists` / `Album.artists` / `Artist.tracks` / `Artist.albums` relationships have **no `order_by`**. Postgres returns rows in physical order, which is implementation-defined.
- `myblog_shared_db/src/myblog_shared_db/models.py:119-122` — `Artist.popularity` and `Artist.followers` exist. `Album.popularity` (line 152) exists. `Track` has **no `popularity` column**.
- `myblog_worker/worker/service/sync_service.py` already writes every participating artist for every track. No change needed.

**Search response — partial baseline (the prior Step 1 of this RFC shipped via PRs #141 / #142 / #143)**

- `myblog_music/app/api/routers/search.py:20-37` — `/api/music/search/unified` already returns all three buckets in one call (default `type=album,artist,track`, single `offset` / `limit`).
- `myblog_music/app/services/search_service.py:27-47` — runs three independent literal matches in parallel. **No expansion. No cross-bucket dedup. No path-dependent ranking.**
- `myblog_music/app/repositories/track_repo.py:29-41` — `search_by_title` eager-loads `selectinload(Track.album).selectinload(Album.artists)` + `selectinload(Track.artists)`. N+1-safe today; the same discipline must extend to expansion queries.
- `myblog_music/app/repositories/album_repo.py:38-48` — `search_by_title` eager-loads `selectinload(Album.artists)` and orders by `Album.popularity DESC NULLS LAST`.
- `myblog_music/app/repositories/artist_repo.py:24-47` — `search_by_name` matches `Artist.name ILIKE` OR an element of the `aliases` JSONB array ILIKE; orders by `popularity DESC, followers DESC, views DESC`.
- `myblog_music/app/domain/schemas.py:36-52` — `TrackItem` already exposes `feat_artist_names: List[str]` (additive, default empty). `artist_name: Optional[str]` retained for backward compat.
- `myblog_music/app/mappers/track_mapper.py` — primary chosen as `track_artists[0].name`; `feat_artist_names` built as `sorted({a.name for a in track_artists if a.name and a.name != primary})`. Display plumbing in place but **primary pick is non-deterministic** because of the missing `order_by` above.
- `myblog_music/app/repositories/album_repo.py:111-127` — `get_primary_artist_map` joins `album_artists` without `ORDER BY` and keeps the first row seen → same non-determinism on album rows.
- `myblog_music/app/services/album_service.py:46-49` — `AlbumDetail.TrackOut.feat_artist_names` rule differs intentionally (see Non-goals).

**Frontend — partial baseline**

- `myblog_front/src/lib/api.gen.ts` already carries `feat_artist_names?: string[]` on `Music_TrackItem`.
- `myblog_front/src/components/writer/SubjectBlock.tsx:418-422` already renders `${artist_name} (feat. ${feat_artist_names.join(', ')}) · ${album_title}`.
- `myblog_front/src/scripts/searchBarDb.client.ts:104-119` `mapDBTracksUnified` carries `feat_artist_names` through.
- `SubjectBlock.tsx:185-188` confirms filter tabs (전체 / 앨범 / 트랙 / 아티스트) are **client-side post-filter only** — they narrow `results` with `useMemo` and do not re-hit the API.
- No per-bucket "load more" exists in either surface today; both call `/unified` once with `limit=20, offset=0` and that is the entire result set.
- `searchBarDb.client.ts:318-327` does a separate fetch on artist _click_ to load that artist's albums (`/api/music/artists/{id}/albums`) — correct as a click action but does not address the in-line expansion this RFC introduces.

→ Net: feat display is mechanically wired but the primary pick is unstable; artist / album / track searches return their own bucket only; "artist → tracks" needs an extra click; per-bucket pagination is absent.

## Target state

**Unified search (DB)** — single endpoint, single response, three buckets:

1. **Match phase** — literal substring / alias match per bucket, unchanged:
   - artist: `name ILIKE` OR `aliases` JSONB element ILIKE.
   - album: `title ILIKE`.
   - track: `title ILIKE`.

2. **Expansion phase** — exactly one hop along the existing relations:
   - **artist match → that artist's albums + that artist's tracks.** Tracks expand via `track_artists`, which is symmetric N:N with no main/feat distinction, so featured tracks are inherently included — there is no separate feat code path.
   - **album match → that album's tracks + that album's artists.**
   - **track match → that track's album + that track's artists.**

   Hop depth is **strictly 1**. An album match must not expand into "other albums by this album's artists" — that is multi-hop and belongs behind artist-detail.

3. **Merge / dedup phase** — keyed by `track_id` / `album_id` / `artist_id`. The same entity arriving via literal match AND via expansion collapses to one row. The merged row **retains its strongest entry path** (literal > expansion), because the ranking key is path-dependent (see Rank phase).

4. **Rank phase**:
   - **artist bucket**: literal match → match similarity to the query, then `Artist.popularity DESC`. Expansion-only artists (arrived solely because their album/track matched) → `Artist.popularity DESC`.
   - **album bucket**: literal match → similarity, then `Album.popularity DESC`. Expansion-only albums → `Album.popularity DESC`.
   - **track bucket** — path-dependent, because there is no `Track.popularity`:
     - **literal title match** → match similarity to the query.
     - **arrived via artist or album expansion** → `Album.release_date DESC` (newest first). All such tracks share an artist or album, so similarity and popularity cannot differentiate them; recency is the user-expected default.

5. **Trim / page phase**: initial bucket sizes — tracks 10, albums 10, artists 5 (tunable). Per-bucket "load more" via offset (see Open Q3 for the API shape). The artist → track expansion is the one path that must be bounded: a prolific artist with hundreds of tracks must not fan out unbounded. Album → track and track → album/artist are naturally small.

**Display rule (frontend)** — every track row, whether literal-matched or expanded-in, displays all participating artists:

```
${primary}${feat.length ? ` (feat. ${feat.join(', ')})` : ''} · ${album_title}
```

`feat_artist_names` is built mapper-side as `sorted(set(a.name for a in track_artists if a.name and a.name != primary))`. The `set()` step is **mandatory** so two artists with the same display name, or data-level duplicates, collapse — we never render `X (feat. X)`. If `track_artists` is empty and the mapper falls back to `album_artists` for the primary, `feat_artist_names = []`.

**Backward compatibility**

- `TrackItem.artist_name` retained.
- `TrackItem.feat_artist_names` already present (additive field carried over from prior work).
- Pagination param shape decided by Open Q3 — backward compat preferred.

**Filters** — `SubjectBlock.tsx` filter tabs (전체 / 앨범 / 트랙 / 아티스트) stay client-side; the single unified response feeds all tabs; switching tabs triggers no network request. Only "load more" hits the API.

## Steps

### Step 1 — single bundled change (one PR per repo, shipped together)

This RFC ships in **one PR per repo, sequenced on the same day** to avoid contract drift:

1. `myblog_music` PR — expansion + dedup + path-dependent ranking in `search_service.unified_search`; new expansion methods on `artist_repo` / `album_repo`; ordering stabilization (per Open Q1); per-bucket pagination param shape (per Open Q3); regen `openapi.json` in the service repo.
2. workspace PR — `python scripts/merge_openapi.py` → `docs/contracts/openapi.json`; `pnpm --filter myblog_front generate:types` → `src/lib/api.gen.ts`; `SubjectBlock.tsx` + `searchBarDb.client.ts` per-bucket "load more" UI; drop this plan row when prod smoke passes.

**Do not split-merge**: the contract regen and frontend types must reach `main` in the same workspace PR as the UI; otherwise the deploy CI guard or contract-drift gate trips (see `feedback-frontend-api-gen-sync`, `reference-workspace-contract-merge-order`).

**Verification (pre-merge)**

`myblog_music`:

```
cd myblog_music && pytest tests/ -v
cd myblog_music && ruff check app/
```

- Unit tests: dedup retains the strongest path; per-bucket ranking respects the path-dependent rule; mapper builds `feat_artist_names` with `sorted(set(...))`; primary pick is deterministic across repeated calls.
- **Real-engine integration test** (mandatory per `feedback-sa-session-lifecycle-mock-blind`): seed a real Postgres with one artist + 2 albums + ≥1 feat track + ≥1 main track, run `unified_search` on the artist's name, assert all three buckets populated, the feat track appears in the artist's track expansion, and query count stays bounded (no N+1) via an SA event listener.

workspace:

```
cd myblog_front && pnpm lint && pnpm exec astro check
```

- Browser click-through (mandatory per `feedback-browser-verify-ui-changes`): launch the dev server, drive both surfaces (writer page + global search bar) for an artist query, an album query, and a track query — confirm all three buckets render, filter tabs narrow without a network call, "load more" issues exactly one bucketed request.

**Prod smoke** (post-merge)

- `GET /api/music/search/unified?q=<artist with feat tracks>` — assert all three buckets non-empty, the artist's feat tracks appear in `tracks[]`, no duplicates, `feat_artist_names` deduped.
- `GET /api/music/search/unified?q=<album title>` — assert `albums[]` includes the album, `tracks[]` includes its tracks, `artists[]` includes its artists, and `tracks[]` does **not** include tracks from other albums by the same artists (1-hop guard).
- `GET /api/music/search/unified?q=<track title>` — assert symmetric.
- Quote prod-smoke output in the workspace PR comment (per `feedback-prod-smoke-required`).

**Rollback**: PR revert in both repos. Schema is additive (no DDL change in this step). No data mutation. Rollback risk is contained.

---

## ~~Open questions~~ — Resolved 2026-05-30

_Answers captured in the Decisions log (2026-05-30, "Open Qs resolved" row). Question bodies kept below for traceability — what was asked and which alternatives were on the table._

1. **Primary-artist ordering stabilization** — `Track.artists` and `Album.artists` lack a deterministic `order_by`, and the join tables lack a `position` column. The primary pick can flip between page loads (`X (feat. Y)` ↔ `Y (feat. X)`). Three candidates:
   - (a) In-mapper heuristic: sort `track_artists` by `(-Artist.popularity, Artist.name)` so the most-popular participant becomes "main". `get_primary_artist_map` adds an equivalent SQL `ORDER BY`. Music-repo-only change; no DDL.
   - (b) Schema fix: add `position smallint` to `track_artists` + `album_artists`, worker writes Spotify's array index, backfill existing rows, relationships use `order_by="position"`. Spotify-authoritative; scope expansion across `myblog_shared_db` + worker + a music shared_db pin bump; rollback adds a DDL revert.
   - (c) Accept the flicker. Document as a known pre-existing bug and file a follow-up.

   Blocks: Step 1 display correctness.

2. **Artist → track fan-out cap** — Spotify artists with very deep catalogues must not flood the bucket. Proposed default: initial page 10, max page 50, ranked by `Album.release_date DESC`. Confirm cap value and ranking key.

   Blocks: Step 1 bounded expansion.

3. **Pagination API shape** — `/unified` accepts a single `offset` today. Per-bucket "load more" needs three independent offsets. Two shapes:
   - (a) Additive: keep `offset` as a fallback applied to all buckets when no per-bucket value is given; add `artist_offset`, `album_offset`, `track_offset` overrides. Backward-compatible.
   - (b) Replace: drop `offset`, expose only per-bucket offsets. Cleaner; breaks any caller mid-rollout (the frontend is the only known caller today).

   Blocks: Step 1 API surface.

## Decisions log

| Date       | Decision                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           | Step         |
| ---------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------ |
| 2026-05-29 | The two symptoms (artist → album / track expansion missing; feat artists missing in display) were initially scoped as separate Steps — Step 1 = feat-display field; Step 2 = related search, deferred for post-prod observation. _(superseded 2026-05-30 — see below.)_                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            | (superseded) |
| 2026-05-29 | Mapper rule for the unified-search `TrackItem.feat_artist_names`: exclude by **name equality** to the chosen `primary`, not by `album_artist_ids`. The search response carries no album-artist metadata, and the UI renders `${primary} (feat. ${feat}…)` — only the representative needs removal from the feat list. The album-detail service's rule (`if ta.id not in album_artist_ids`) is intentionally different and must remain.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             | 1            |
| 2026-05-29 | Keep `TrackItem.artist_name: Optional[str]` for backward compat; add `feat_artist_names: List[str]` additively. No breaking schema change.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         | 1            |
| 2026-05-30 | **Supersedes the Step 1 / Step 2 split above.** The two symptoms are one problem with one mechanism: 1-hop cross-expansion along the existing relations. Feat display is demoted from a separate step to a display rule applied to the resulting track rows (literal-matched or expanded-in); the previously-shipped `feat_artist_names` field already carries that rule. The RFC now describes a single Step that bundles backend + workspace contract regen + frontend in coordinated PRs to avoid contract drift. Track popularity, multi-hop expansion, similar-album recommendation, and the image-cache rerender bug are explicitly out of scope and recorded as Non-goals. Open questions retained: ordering stabilization (Open Q1), fan-out cap (Open Q2), pagination API shape (Open Q3).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                | all          |
| 2026-05-30 | **Open Qs resolved.** **Q1 = (a)** in-mapper heuristic: sort `track_artists` / `album_artists` by `(-Artist.popularity, Artist.name)` mapper-side; add the matching `ORDER BY` to `album_repo.get_primary_artist_map` (`myblog_music/app/repositories/album_repo.py:111-127`). Confirmed Spotify's original artist-array index is not preserved anywhere queryable — lost at `myblog_worker/worker/service/sync_service.py:105-110` (no `enumerate`, no `position` column on join tables, no raw payload in `ext_refs`). Restoring it would require DDL on `track_artists` / `album_artists` + worker patch + full-catalog Spotify re-sync — out of scope here. Trade-off recorded: the heuristic optimizes for **stability across reloads, not for matching Spotify's authoritative primary**; with similar-popularity collaborators it may stably pick a different primary than Spotify's array index. Trigger to reopen option (b) = a real user-flagged wrong-primary case in prod. **Q2 = 10 / 50 / `Album.release_date DESC NULLS LAST`**: artist→tracks expansion query bounded at the SQL layer with `LIMIT 50` (not post-fetch — preserves the bounded-query-count integration test on line 120); initial track-bucket page 10. Non-blocking note: multiple literally-matched artists multiply the per-artist 50 into the pre-trim candidate set — fine for v1, add a global expansion-candidate cap only if prod response size grows. **Q3 = (a)** additive per-bucket offsets `artist_offset` / `album_offset` / `track_offset` with the existing `offset` retained as fallback. Precedence: `<bucket>_offset` if present, else `offset`, default 0. Limits stay singular this step — do **not** add per-bucket limits. | 1            |
