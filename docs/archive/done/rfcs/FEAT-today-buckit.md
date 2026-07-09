# FEAT-today-buckit: Two "today" buckit tiles on the home

- **Status**: shipped (Steps 1–6 complete + prod-live 2026-07-09 — owner round-trip verified)
- **Owner**: TBD
- **Created**: 2026-07-08
- **Plan row**: `plan.md` → FEAT-today-buckit
- **Depends on**: `ARCH-entity-interaction-unify` (the buckit tiles must click
  identically to every other surface — album → global overlay, artist → route).
  The `TodayAlbumBuckit` (Steps 1–2) can ship before ARCH lands using whatever
  album-click exists at the time; the click wiring adopts the unified dispatch
  when ARCH is in.
- **Adjacent, distinct**: `FEAT-release-calendar` Track A is a **"새 앨범"** card
  = albums released in the **last 30 days**. This RFC's `TodayAlbumBuckit` is
  **"오늘, 이 앨범들"** = albums whose release **month/day == today**, across all
  past years ("N년 전 오늘"). Different query, different surface; both can coexist
  on the home.

---

## Goal

Two small, separate, buckit-styled components on the editorial home
(`EditorialHome`), following the existing home section pattern
(`SectionTitle` · `Cover` · `Stars`) and the **Buckit** product spelling:

1. **`TodaySongBuckit` (오늘의 곡)** — a single owner-curated pick. It appears
   **only on days the owner has posted a pick**; on days with no pick, the
   section renders empty (a quiet "지난 추천곡" link, no filler). Every pick is
   **stored to a history** browsable by anyone. The tile shows the song's
   identity only — cover, title, artist — with **no personal written
   impression** on it (owner decision 2026-07-08). Clicking the song/album opens
   the album window; clicking the artist routes to the artist page (both via
   `ARCH-entity-interaction-unify`).
2. **`TodayAlbumBuckit` (오늘, 이 앨범들)** — albums whose `release_date`
   month/day equals today, across years, newest-year first, with an "N년 전"
   badge. DB-only, no owner action, always populated when matches exist (hidden
   when none). Clicking behaves identically to the song tile.

After this RFC: the home has a daily-changing "오늘" pair; the owner can post
today's song from a small control and browse past picks; visitors see what came
out on this date in history.

## Non-goals

- **No always-on dock / floating panel.** The earlier "상시 독" direction was
  dropped (owner 2026-07-08); these are in-flow home sections.
- **No personal note / "왜 오늘인가" text on the tile** (owner). Whether a star
  rating shows is OQ2 (default: off — rating is impression-adjacent).
- **No automatic daily rotation / algorithmic pick.** The song is 100% manual;
  no-pick days are intentionally empty (not back-filled from a pool).
- **No new listening/recommendation ML.** `on-this-day` is a pure `release_date`
  query over the existing catalog.
- **No multi-user scope.** The pick store is single-owner (`require_owner`),
  consistent with posts/publish. Per-user picks are a later concern.
- **No merge with `FEAT-release-calendar`** — adjacent but distinct (see header).

## Current state

Verified 2026-07-08 (front + music + backend recon).

- **`release_date` supports the album query.** `Album.release_date`
  (`myblog_shared_db/src/myblog_shared_db/models.py:242`) is a full nullable
  `DATE` (`_generated_schema.sql:6` → `release_date DATE`), so
  `EXTRACT(MONTH/DAY)` filtering is possible. **No date-filtered album endpoint
  exists** — `myblog_music/app/api/routers/albums.py` exposes only `/{id}` and
  `/by-spotify/{id}`; `release_date` is used for `ORDER BY` only. Coverage is
  **partial/sparse** (nullable, `upsert_album_min` writes null when Spotify
  omits it) → the query must `WHERE release_date IS NOT NULL`.
- **DB-only music read pattern to copy**: `GET /api/music/search/unified`
  (`Session = Depends(get_db)`, no Spotify client, explicit `Cache-Control`).
  Music reads ride CloudFront edge_guard (public, no JWT, no `apigateway.tf`
  change; `ANY /api/music/{proxy+}` already routes).
- **No owner-writable singleton/config store exists.** Backend routes
  (`myblog_backend/app/api/routes/`) are posts/publish/genres/buckets/sections/
  tags/library/playback/lyrics/research/metrics/me. `/api/me` is per-user, not
  global. Owner-only is enforced by `require_owner`
  (`myblog_backend/app/core/auth.py:133-164`, JWT `sub` == `settings.OWNER_SUB`,
  fail-closed). A daily pick needs a **new small owner-writable store**.
- **The frontend has no owner concept** — `isLoggedIn()` is the only client flag
  (`lib/auth.ts:62`). The posting control must piggyback on a logged-in surface
  (write/drafts) and rely on the backend `require_owner` gate for real
  enforcement; the front shows the control to any logged-in user, the server
  rejects non-owners (fail-closed).
- **Static build constraint**: the home is Astro → S3/CloudFront, redeployed
  only on merge. Anything daily-rotating (both tiles) must be a **runtime API
  read**, not frontmatter (which would need a redeploy per change). Existing
  home islands do build-time only; these two add the home's first runtime
  fetches (same posture `FEAT-release-calendar` Track A introduces).
- **Buckit spelling + look**: new components use the **Buckit** product spelling
  (`components/member/pocket/PocketBuckit*`, `lib/pocketBuckit/*`), not the older
  data-layer **Bucket** (`BucketBoard`, `/api/buckets`). Tile visual to echo:
  `AlbumChip` (`BucketBoard.tsx:501`) — cover + serif title + artist; shared
  primitives `Cover`/`Stars` (`components/home/ui.tsx`, `member/ui.tsx`).

## Target state

### Music — `on-this-day` endpoint

- `GET /api/music/albums/on-this-day?limit=8` (musicApi, added to the albums
  router or a small `feed`/`onthisday` router) returns albums where
  `EXTRACT(MONTH FROM release_date)=EXTRACT(MONTH FROM current_date)` AND same
  for DAY, `release_date IS NOT NULL`, excluding today's current year (only
  "past" anniversaries), dedup on (normalized title, primary artist), ordered
  `release_date DESC` (newest anniversary first), `limit` capped. Each item:
  `{album_id, spotify_album_id, title, cover_url, release_date, years_ago,
  artists:[{id,name}]}`. `Cache-Control` set like unified search.
- DB-only, edge_guard read — no `apigateway.tf` change.

### Backend — owner-writable daily pick store + history

- New shared_db table `daily_picks` (final name OQ1):
  - `id` PK
  - `pick_date` date **UNIQUE NOT NULL** (one pick per day; re-post = overwrite)
  - `track_id` FK → the picked track (nullable if an album-only pick is allowed
    — OQ3)
  - `album_id` FK (the track's album, for the album-window click target)
  - denormalized display: `title`, `artist`, `cover_url`, `spotify_track_id`
    (self-contained public GET, no cross-service join at read time)
  - `created_at` / `updated_at`
  - No note/impression column (owner: none on the tile; if ever stored for
    private reasons it is not returned by the public GET).
- Backend routes (`myblog_backend`):
  - `GET /api/todays-pick` — public (edge_guard), returns today's pick or an
    empty/`204` (front hides the tile on empty).
  - `GET /api/todays-pick/history?limit=&before=` — public, date-desc list.
  - `PUT /api/todays-pick` — **owner** (`require_owner`), sets today's pick
    (upsert on `pick_date = current_date`); body carries the chosen track's ids
    + denormalized display.
  - `DELETE /api/todays-pick` — owner, clears today's (OQ4: needed for v1?).
- Contract exported + merged; front types regenerated.

### Infra

- `infra/apigateway.tf`: add routes for the **authed** writes
  (`PUT`/`DELETE /api/todays-pick`) → backend Lambda, Cognito authorizer (like
  posts/publish). The two public GETs need **no** apigateway route (they ride
  CloudFront edge_guard, same as other public reads) — confirm at Step 5 whether
  the backend public-GET path is edge_guard-reachable without an API-GW entry
  (memory `reference-apigateway-post-route-required`: probe with curl, 401=live
  vs 404).

### Front

- `src/components/home/TodayAlbumBuckit.tsx` — runtime `fetch` of
  `/api/music/albums/on-this-day`; buckit-styled section; hide on empty/error
  (home degrades to today's layout). Album/artist clicks via
  `ARCH-entity-interaction-unify` dispatch.
- `src/components/home/TodaySongBuckit.tsx` — runtime `fetch` of
  `/api/todays-pick`; renders the single pick or the empty state with a "지난
  추천곡" link; identity-only tile; click via the unified dispatch.
- A **history view** for past picks — a small overlay or a `/today` page reading
  `/api/todays-pick/history` (shape OQ5).
- An **owner posting control** — a logged-in surface (e.g. a panel on `/write`
  or `/drafts`) that reuses the existing music search to pick a track, then
  `PUT /api/todays-pick`. Shown to any logged-in user; server enforces owner.
- Both mounted from `index.astro` into `EditorialHome` (placement: home,
  per owner) — exact slot in the home flow is OQ6.

## Steps

Music (Step 1) + its front tile (Step 2) are independent of the pick store
(Steps 3–6) and ship visible value first — recommend landing the album tile
before the song store. `ARCH-entity-interaction-unify` is the click dependency;
land it before Step 2's click wiring is finalized, or wire interim then adopt.

### Step 1 (music) — `on-this-day` endpoint + contract

New route + service query + schema; pytest for month/day boundary (leap-day
OQ7), `IS NOT NULL` filter, current-year exclusion, dedup, `years_ago`
computation, `limit` cap. Export `openapi.json`; workspace merges contract.

**Verification**:
```
cd myblog_music && pytest
curl 'http://localhost:8001/api/music/albums/on-this-day?limit=8'   # local
# prod smoke (post-merge, via CloudFront):
curl 'https://www.ratemymusic.blog/api/music/albums/on-this-day?limit=8'
# expect items all sharing today's month/day, none dated the current year,
# no null release_date, no duplicate (title, primary artist).
```

**Rollback**: revert PR (additive route).

---

### Step 2 (front) — `TodayAlbumBuckit` on the home

Regen `api.gen.ts`; new home island; runtime fetch; hide-on-empty; buckit
styling; album/artist click via the unified dispatch. `frontend-design` skill at
implementation; real-browser click-through pre-merge (DoD).

**Verification**:
```
cd myblog_front && pnpm lint && pnpm exec astro check && pnpm build
# real-browser: tile renders covers + "N년 전" badges; album click opens the
# album window; artist click routes; tile absent when API blocked; console 0.
```

**Rollback**: revert PR (restores today's home exactly).

---

### Step 3 (shared_db) — `daily_picks` migration

Plain `V{N}__daily_picks.sql` + ORM model + version bump. Rollout order per
memory `reference-shared-db-cross-repo-rollout`: migration → prod apply
(pre-merge, owner-approved) → service pin bumps with Step 4.

**Verification**:
```
cd myblog_shared_db && PYTHONPATH=src pytest
psql "$DATABASE_URL" -c "\d daily_picks"
```

**Rollback**: `DROP TABLE daily_picks` (no consumer yet).

---

### Step 4 (backend) — pick store routes + contract

`GET /api/todays-pick`, `GET /api/todays-pick/history`, `PUT /api/todays-pick`
(`require_owner`), `DELETE` (OQ4). Upsert on `pick_date=current_date`. Export +
merge contract; regen front types.

**Verification**:
```
cd myblog_backend && pytest
# local (ENV=local bypass): PUT then GET returns today's pick; history lists it.
# owner-gate unit: non-owner sub → 403; missing OWNER_SUB → 503 (fail-closed).
```

**Rollback**: revert PR (routes additive; table stays, unused).

---

### Step 5 (infra) — apigateway routes for the writes + apply

Add `PUT`/`DELETE /api/todays-pick` to `infra/apigateway.tf` (Cognito
authorizer). Full `terraform plan`; owner-applied. Confirm the public GETs are
edge_guard-reachable (curl probe: 401=live vs 404).

**Verification**:
```
terraform plan   # only the new routes, no drift
# post-apply: curl -X PUT (no token) → 401 (route live, authorizer rejects);
# curl GET /api/todays-pick via CloudFront → 200/empty (public read reachable).
```

**Rollback**: remove the routes + apply (or leave — additive).

---

### Step 6 (front) — `TodaySongBuckit` + owner posting control + history

The song tile (empty-on-no-pick), the owner posting panel (music-search pick →
`PUT`), and the history view. Real-browser click-through pre-merge incl. the
owner-post round-trip and the empty-day state.

**Verification**:
```
cd myblog_front && pnpm lint && pnpm exec astro check && pnpm build
# real-browser: owner posts a pick → tile appears with identity-only; a
# no-pick date shows the empty state; history lists past picks; song/album/artist
# clicks match ARCH dispatch; console 0.
# prod smoke (post-deploy): GET returns the posted pick; tile renders.
```

**Rollback**: revert PR (tiles/control removed; store rows persist harmlessly).

---

## Open questions

1. **Table/route name** (blocks Step 3) — `daily_picks` / `todays_pick` /
   `song_of_the_day`. Recommend `daily_picks` (table) + `/api/todays-pick`
   (route). Cosmetic; lock at Step 3.
2. **Star rating on the tile?** (blocks Step 2/6 design) — owner said no personal
   *written* impression; a star rating is impression-adjacent. Default **off**
   (identity only). If a picked track's album has a *published review* rating,
   linking to it is possible but out of v1 unless owner wants it.
3. **Pick granularity** (blocks Step 3/4) — is a pick always a **track**, or can
   it be an **album**? Recommend track-primary (carry `album_id` for the click
   target); album-only picks a later option. Shapes the `daily_picks` nullability.
4. **`DELETE /api/todays-pick` in v1?** (blocks Step 4/5) — re-`PUT` overwrites,
   so delete is only for "unpost today". Recommend include it (cheap) but it's
   optional.
5. **History surface** (blocks Step 6) — overlay vs a `/today` page. A page is
   linkable/SEO-friendly and simpler than a new overlay; recommend a light
   `/today` archive page (agenda list of past picks). **RESOLVED 2026-07-09
   (owner): overlay modal** — the "지난 추천곡 →" header link opens a date-desc
   history overlay (`TodayPickHistory`), no page navigation.
6. **Home placement slot** (blocks Step 2/6 layout) — where in the
   `EditorialHome` flow (Hero → Latest → **here?** → BrowseGenres → ByTheNumbers).
   Owner eyeball at implementation; the two tiles are separate sections (owner:
   keep them separate, not merged). Record in the Decisions log. **RESOLVED
   2026-07-09 (owner): song tile ABOVE the album tile** — 오늘의 곡 → 오늘, 이
   앨범들, each its own `Measure` section.
7. **Leap-day / Feb-29 picks** (blocks Step 1) — an album released 02-29 only
   "matches" on leap years. Decide: exact month/day (02-29 shows every 4 years)
   vs fold 02-29 into 02-28 on non-leap years. Recommend exact for v1 (rare;
   simplest), note it.

## Decisions log

| Date | Decision | Step |
|------|----------|------|
| 2026-07-08 | Two separate buckit tiles on the home (not merged, not a dock) (owner) | scope |
| 2026-07-08 | Song pick is 100% manual; shows only on posted days; history stored (owner) | scope |
| 2026-07-08 | No personal written impression on the tile (owner) | design |
| 2026-07-08 | Placement = home / EditorialHome sections (owner) | scope |
| 2026-07-08 | Buckit (not Bucket) spelling; `today ( ) buckit` naming convention (owner) | design |
| 2026-07-08 | Entity clicks route through ARCH-entity-interaction-unify (album → overlay, artist → route) (owner) | dep |
| 2026-07-08 | Step 1 SHIPPED — music `GET /api/music/albums/on-this-day` (music #52, deploy 28880892242); prod smoke 8/8 (07/07 slice, years_ago correct, no null/current-year, dedup); leap-day = exact match (OQ7 default) | Step 1 |
| 2026-07-08 | Step 2 SHIPPED — front `TodayAlbumBuckit` home tile (front #256, deploy 28903782888). Horizontal cover strip; cover→`openAlbum` overlay, artist→`artistHref`; hides on empty/error. Prod smoke: 8 real albums render (07/07 slice), cover click → overlay full render (15 tracks, 0 lyrics affordance), ESC closes | Step 2 |
| 2026-07-08 | Step 3 MERGED — shared_db V39 `daily_picks` table + `DailyPick` model + version 0.29.0→0.30.0 (shared_db #55, `PYTHONPATH=src pytest` 58/0). Track-primary (OQ3), denormalized display cols, `pick_date` UNIQUE upsert key, no note col, both FKs ON DELETE CASCADE. Additive/no-consumer. **Prod apply owner-gated (rule #3) — deferred; harmless unapplied until Step 4** | Step 3 |
| 2026-07-09 | OQ4 resolved — **include `DELETE /api/todays-pick` in v1** (owner). re-PUT overwrites so delete is only for "unpost today"; cheap to ship alongside PUT. Resolves the OQ4 "blocks Step 4/5" gate | OQ4 |
| 2026-07-09 | Step 4 PRs OPEN — backend pick store routes (backend #111): GET/PUT/DELETE `/api/todays-pick` + GET `/history`; owner gate (`require_owner`) on PUT/DELETE, public GETs ride edge_guard; upsert via `on_conflict_do_update(constraint=uq_daily_picks_pick_date)`, server pins `pick_date=today`; `pytest` 452/0 (+18 new). Contract merged (workspace #590) + front `api.gen.ts` regen (front #263). Empty today = `200 + null` (front hides tile); no-pick is normal, not 404. **V39 prod apply + Step 5 infra remain owner-gated — routes not live in prod yet** | Step 4 |
| 2026-07-09 | Step 4 MERGED — backend #111 (squash → main `fd375b3`, Lambda deploy success), workspace #590, front #263 all merged. Pre-apply smoke: public GETs 500 (daily_picks table absent in prod) — the V39 gate | Step 4 |
| 2026-07-09 | **V39 prod-applied (owner-approved, executed by Claude)** — `daily_picks` table created via V39 SQL (psycopg, file's own BEGIN/COMMIT txn) against the Neon pooler URL from SSM `/myblog/backend`. Verified: 10 cols match V39, constraints PK + 2 FKs(ON DELETE CASCADE) + `uq_daily_picks_pick_date` UNIQUE. Post-apply prod smoke: `GET /api/todays-pick` → **200 + null** (was 500), `GET /history` → **200 + []**. Forward apply only (no rollback — rule #3). Table empty/no-consumer until Step 6 posts a pick | Step 3/4 |
| 2026-07-09 | OQ5/OQ6 resolved (owner) — history = **overlay modal** (`TodayPickHistory`, opened from "지난 추천곡 →" header link); home placement = **song tile ABOVE album tile** (오늘의 곡 → 오늘, 이 앨범들); owner control = **inline on the home tile** (not a /write panel). `isLoggedIn` is the client hint; `require_owner` is the real gate | OQ5/OQ6 |
| 2026-07-09 | Step 5 MERGED — infra #592 (workspace): `PUT`/`DELETE /api/todays-pick` apigateway routes (Cognito JWT, `integrations_lastfm` pattern). `terraform plan` 2 to add / 0 change / 0 destroy / no drift. Public GETs need no route (edge_guard catch-all). **Apply owner-gated (rule #6 🔒) — deferred** | Step 5 |
| 2026-07-09 | Step 6 MERGED — front #264: `TodaySongBuckit` home tile (identity-only card; cover/title→`openAlbum`, "지난 추천곡"→history overlay) + inline owner control (올리기/바꾸기/삭제) + `TodaySongPicker` track-picker modal (`useMusicSearch['track','artist']`, TrackHit→PUT body, DB-id resolution, track_id NOT NULL guard) + `TodayPickHistory` overlay. SSR fix: `isLoggedIn()` (localStorage) moved to `useEffect` — was crashing the prod build. `pnpm lint`/`astro check` 0 errors, `pnpm build` 15pp OK, home SSR-renders the section. Mounted ABOVE `TodayAlbumBuckit` (OQ6) | Step 6 |
| 2026-07-09 | Step 5 **apply executed** (owner-approved) — `terraform apply`: 2 routes created (`todays_pick_put` `j4ksdy3`, `todays_pick_delete` `jpy2c1d`). Post-apply prod smoke: `PUT`/`DELETE /api/todays-pick` (no token) → **401** (routes live, Cognito rejects); public GETs still **200 + null/[]**; prod home SSR-renders `tsp-mod` (오늘의 곡) BEFORE `otd-mod` (오늘, 이 앨범들) per OQ6. Owner round-trip verified (owner posted a pick). **RFC → shipped** | Step 5 |
