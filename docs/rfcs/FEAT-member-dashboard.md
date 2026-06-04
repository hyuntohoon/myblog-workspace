# FEAT-member-dashboard: 회원 대시보드 (`/profile`)

- **Status**: accepted
- **Owner**: TBD
- **Created**: 2026-06-04
- **Plan row**: `plan.md` → FEAT-member-dashboard

---

## Goal

A member can open `/profile` (auth-gated, their own page) and see, in one editorial-styled
dashboard: their written reviews, their listening activity ("now playing" + recently played),
a review-bucket board, their library, and genre/artist distribution. The page is built in
**vertical slices**: Step 1 ships the full **frontend** with real data where it exists today
(reviews + derived stats) and clearly-labeled **sample** data everywhere the backend can't yet
supply it; later steps replace each sample surface with a real API, one slice per step.

The design was mocked in Claude Design ("Lowfreq 회원 페이지") and its `ds.css` was lifted 1:1
from our [`global.css`](../../myblog_front/src/styles/global.css), so the visual system is
already ours — Step 1 is a faithful React/TS port, not a redesign.

## Non-goals

- **No new backend in Step 1.** No user/profile table, no listening-history table, no
  library-status persistence, no aggregation endpoints. Step 1 is frontend-only.
- **No multi-user.** `/profile` is the single admin's own page (gated like `/write`). Public
  profiles (`/members/[handle]`), followers/following, and lists are deferred — those stats are
  **hidden** in Step 1, not faked.
- **No live Spotify on a user-facing endpoint** (hard rule #9). "Now playing" is never a
  synchronous Spotify call; it becomes a worker-fed cache in a later step.
- **Not rebuilding the shipped bucket board in Step 1.** The flat `/reviews/queue` board
  (FEAT-review-bucket-board, #193–197) stays live alongside Step 1's localStorage nested
  board; Step 5 retires that page (D1).
- **No Spotify write actions in this RFC.** Save-album / playlist-export / library-modify are
  deferred to a later RFC (D11). Step 3's Spotify read scope is `user-read-recently-played` only.

## Current state

- **Frontend**: no member/profile/account page exists. Auth is ready —
  [`auth.ts`](../../myblog_front/src/lib/auth.ts) `isLoggedIn()`/`goLogin()`, the protected-page
  guard pattern [`write.guard.ts`](../../myblog_front/src/scripts/write.guard.ts), and the
  logged-in-only `#write-link` toggle in
  [`header.client.ts`](../../myblog_front/src/scripts/header.client.ts). Design tokens + dark mode
  (`[data-theme=dark]`) already live in `global.css`.
- **Reviews**: real, build-time from `getCollection('blog')` (see
  [`reviews/index.astro`](../../myblog_front/src/pages/reviews/index.astro)); rating normalized to
  0–5 via the [`ReviewCard`](../../myblog_front/src/lib/reviews.ts) shape. No explicit review
  **type** field — album/track/column is inferable from album_ids / recommended_track_ids / category.
- **Buckets**: shipped as a **flat column** kanban with a real API (`/api/buckets/*`,
  `ReviewBucket`/`ReviewBucketItem`, no nesting). The design wants a **nested row** board.
- **Absent entirely**: now-playing, listening history, library status, genre/artist aggregation,
  any user/profile model.

## Target state

`/profile` renders a 5-tab dashboard (개요 · 평론 · 평론 버킷 · 라이브러리 · 통계) with profile
header, album-detail slide-over, theme toggle, and Toss-style drag reordering on the overview.
Every data surface is backed by a real API. Reached incrementally — Step 1 stands alone as a
usable, honest (sample-labeled) page; each later step turns one sample surface real.

## Steps

> Rule #4: one step per session unless the user OKs the next. Each step is independently mergeable.

### Step 1 — Frontend shell (`/profile`) _(frontend-only)_

Port the prototype (React 18 UMD + `window.LF` globals) to **React 19 + TS islands** under
`myblog_front/src/components/member/`. New route `src/pages/profile.astro` (guarded copy of the
`/write` pattern, rendered in a ~1180px wrapper inside the main layout), `profile.guard.ts`, and a
logged-in-only `#profile-link` in the header.

- **Real**: review list (build-time from `getCollection('blog')`, derived type album/track/column)
  - profile stats (review count, album count, avg rating) derived from it.
- **Sample (labeled "샘플")**: now-playing, recent albums/tracks, library, genres, artists,
  activity, and the seed bucket tree — all behind a single adapter `src/lib/member.ts`
  (`member.sample.ts` holds the mock). The adapter is the swap seam: later steps replace its
  internals with `apiFetch` calls and the islands don't change.
- **Bucket tab**: the redesigned **nested** board (recursive rows, nest/un-nest, native DnD)
  persisted to **localStorage** — frontend-only this step. Coexists with `/reviews/queue`
  until Step 5 retires that page (D1).
- Overview: custom pointer-based row board (½/⅓ width split, lifted overlay portaled to body,
  insertion indicators, FLIP-on-order-change) — ported as-is, not on `@dnd-kit`. Widget
  add/remove/reorder + list/grid/card views persist to localStorage.
- The dev "tweaks panel" is dropped; defaults fixed (sidebar layout / banner now-playing / bar chart).

**Verification**:

```
cd myblog_front && pnpm lint && pnpm exec astro check    # Node 20 (.nvmrc 20.19.5)
# + browser click-through: 5 tabs, overview drag (in-row + new-row), bucket nest/un-nest,
#   library status change, review type filter (uniform card height), album-detail slide-over.
# Prod smoke (post-deploy, auth-gated): curl deployed /profile CSS/JS chunk + grep class names.
```

**Rollback**: delete the route + components; no shared/contract surface touched.

---

### Step 2 — Library tab: to-listen + reviewed _(cross-repo)_

Make the 라이브러리 tab show real data by powering it with two of the three sources defined
in D18 (UI 통일 · 데이터 분리). The 3rd source ("최근 들은 앨범") comes in Step 3.

- **들을 것 (to-listen)** — user-curated queue, new model.
  - `shared_db`: new `album_to_listen_items(id, album_id FK, position, note, added_at)`
    table. No `status` enum (decoupled from review lifecycle per D18).
  - `backend`: `GET /api/library/to-listen`, `POST /api/library/to-listen`,
    `DELETE /api/library/to-listen/{item_id}`, `PUT /api/library/to-listen/reorder`
    (same shape as `/api/buckets/reorder`).
  - Album search reuses unified search; "Spotify Library 에 저장" is a **separate explicit
    action** (D23, deferred to D11 follow-up RFC) — never auto-coupled to add.
- **평론한 앨범 (reviewed)** — read-only derived view, no new table.
  - `backend`: `GET /api/library/reviewed?group_by=album` → returns one entry per album with
    `review_ids[]`. SQL: `post_albums JOIN posts ON posts.status='published'` grouped.
  - **Card unit = album** (D20); clicking opens a drawer listing the N reviews on that album.
    Deleting a single review uses the existing `DELETE /api/posts/{id}?hard=true` modal flow
    (D21); Step 5 will adjust that handler to cascade-clean `review_bucket_items` (D22).

Adapter's library section → real (partial, 2 of 3 sources). Contract change → regenerate
`openapi.json` + frontend types.

**Verification**:

```
cd myblog_shared_db && pytest                     # model ↔ generated schema
cd myblog_backend && pytest tests/test_library.py # CRUD + reorder + derived view
cd myblog_front && pnpm lint && pnpm exec astro check
# browser: add/remove/reorder to-listen; reviewed card click shows N-review drawer
```

**Rollback**: revert backend router + drop `album_to_listen_items`; library tab returns to
sample data.

---

### Step 3 — Listening history + now-playing + Spotify 연동 _(cross-repo)_

Adds the 3rd library source ("최근 들은 앨범", D25) and the now-playing banner. Spotify Web
API does **not** expose a complete listening history — only `GET /me/player/recently-played`
(50-item rolling cap) and top items. So this source is honestly labeled "최근 들은 앨범"
(D26), built from recently-played's distinct album set, cached server-side.

Pulls data per the **hybrid sync model (D5)**:
- **EventBridge cron, 1h**: worker reads `/me/player/recently-played`, then (a) upserts the
  distinct album set to the `spotify_recent_albums` snapshot cache (album_id, last_played_at,
  source='spotify') and prunes albums that fell out of the 50-item window, and (b) appends each
  individual play to an **append-only `spotify_play_events` table** (album_id, played_at) — the
  durable history Step 4's listen-count distribution aggregates over. The snapshot alone only
  ever knows the current rolling window, so without the events table Step 4 has nothing to count
  (**D29**). Player/token reads go through a shared retry/backoff helper (3 tries, honour
  `Retry-After` on 429); the recent-albums and now-playing syncs are isolated symmetrically so
  either can fail without aborting the other.
- **Manual "지금 새로고침" button** on the /profile 라이브러리 tab: triggers an async refresh
  via SQS (rule #9 — never a synchronous Spotify call from the user-facing endpoint). The worker
  **debounces** (skips the Spotify reads when the cache `synced_at`/`updated_at` is < ~60s old),
  which also dedups the standard SQS queue and serialises the non-commutative prune (**D31**).
- Albums in the window not yet in our catalog are best-effort enqueued to the
  `candidates → SQS` catalog sync (re-enqueued each tick until cataloged) and surface in
  최근 들은 앨범 on a **subsequent** tick — eventually consistent, up-to-1h lag.
- Backend: `GET /api/library/recently-listened` reads the snapshot cache; `POST
  /api/library/refresh-recent` returns `202` and the UI **polls** recently-listened until
  `last_synced_at` advances past the request time (no fixed-delay guess). `last_synced_at` is
  added to the response (**D31**).
- Now-playing banner: the same EventBridge tick pulls `/me/player/currently-playing` (both read
  scopes are minted unconditionally at bootstrap; a missing-scope 403 isolates now-playing
  without losing the recent sync). UI displays from cache only.

**Privacy posture (D28).** The listening GETs (`recently-listened`, `now-playing`,
`spotify-connection`) ride the CloudFront edge_guard GET proxy and are **intentionally public**
single-admin vanity reads (edge_guard proves CloudFront transit, not identity — it cannot gate
by login). To avoid leaking fine-grained real-time activity, `now-playing` **omits
`progress_ms`/`duration_ms`**, exposing only track/artist/album/album_id/`updated_at`; dropping
those also removes the misleading frozen progress bar (a ≤1h-stale snapshot can't advance one).
The **idle** response still carries `updated_at`, so the UI shows "동기화 N분 전" rather than
asserting liveness. Only `POST /api/library/refresh-recent` is Cognito-JWT gated.

**Spotify 연동 UI** lives in a new `/profile → 연동 tab` (Q16). The one-time
authorization-code consent that mints the refresh token is taken **out-of-band** via an admin
script (`scripts/spotify_bootstrap_token.py`), not an in-app PKCE flow — building a self-service
OAuth UI to acquire a single long-lived, single-admin token is deferred (**D27**). So the 연동
tab is **thin**: it shows connection status only (`GET /api/library/spotify-connection`); the
in-app `start`/`callback` endpoints come in a follow-up RFC. Refresh token stored in Secrets
Manager `myblog/spotify` (Q17) — **not** in DB. Scopes: `user-read-recently-played`,
`user-read-currently-playing` only (write scopes deferred per D11).

**Token rotation (D30).** Spotify may return a rotated `refresh_token` on a refresh exchange;
the worker **writes it back** to `myblog/spotify` when present, and records
`last_successful_refresh_at`. Connection status therefore reflects token **validity**, not mere
presence: after a revoke/expire the 연동 tab shows "재인증 필요" instead of a stale "연결됨".
Recovery is a one-liner documented in the `spotify_bootstrap_token.py` header (re-run with
`--write`).

This step **absorbs** `plan.md`'s former Frozen `FEAT-spotify-personalize-light` — its
OAuth → refresh → Secrets → cron pipeline is exactly this step's track. That Frozen line was
deleted in #208 (Step 3 infra landing).

**Rollout (ordered)** — cross-repo; the two non-obvious hard gates are starred (★):

0. **★ Create the `myblog/spotify` secret** (client_id/client_secret, no refresh_token yet)
   **before `terraform apply`** — `secrets.tf` references it as a `data` source, not a managed
   resource, so apply hard-fails if it's absent; the bootstrap script's `put_secret_value` also
   can't create it.
1. **★ Apply Neon V9** (rule #3 human approval); confirm `spotify_recent_albums`,
   `spotify_play_events`, `spotify_now_playing` exist (`\dt`) **before merging the backend PR** —
   backend deploy auto-triggers on push-to-main and its GETs 500 on a missing table.
2. Tag `shared_db` `v0.8.0`, then merge backend + worker (order-independent of each other; both
   gate on step 1). Worker stays pinned `v0.2.2` (raw SQL, no ORM bump).
3. `terraform apply` (EventBridge rule + IAM + SQS + JWT route + FailedInvocations/staleness
   alarms) — gated on step 0.
4. Run `scripts/spotify_bootstrap_token.py --write` to mint the refresh token **before the first
   hourly cron tick** (the worker raises "No Spotify refresh token configured" by design).
5. Deploy front (merged contract; `progress_ms`/`duration_ms` dropped per D28).

**Verification**:

```
cd myblog_shared_db && pytest                              # V9 model ↔ canonical_schema parity (3 tables)
cd myblog_worker && pytest tests/test_listening_sync.py    # prune/upsert/event-append + symmetric isolation
cd myblog_worker && TEST_DB_URL=... pytest tests/integration/test_listening_sync_db.py  # live-engine: ON CONFLICT / =ANY(:keep) / CAST timestamptz (unit mocks blind)
cd myblog_backend && pytest tests/api/test_library.py      # recently-listened / now-playing / refresh-recent
cd myblog_front && pnpm lint && pnpm exec astro check      # Node 20 (.nvmrc 20.19.5)
# Token bootstrap (out-of-band, D27): python scripts/spotify_bootstrap_token.py --write → verify
#   myblog/spotify holds refresh_token; /profile → 연동 shows 연결됨 (thin status-only tab).
# EventBridge: aws events put-events (test cron tick) → verify spotify_recent_albums + event rows.
# Manual refresh: click 지금 새로고침 → SQS → worker → cache; UI polls last_synced_at until it advances.
# browser: real 최근 들은 앨범 click opens a REAL panel (cover_url, no 샘플 badge), not the sample slide-over.
# Prod smoke (post-deploy): DB-row evidence for the cache (LOG_LEVEL=WARNING) + deployed chunk grep (auth-gated /profile).
```

**Rollback**: revert front → revert backend reads → revert worker handler → (emergency only,
rule #3 human approval) drop `spotify_recent_albums`, `spotify_play_events`, **and**
`spotify_now_playing` (mirror V9's down-migration; reverting the reads first keeps the deployed
backend from querying a dropped table). Recent section + now-playing return to sample/idle.

---

### Step 4 — Genre / artist distribution _(depends on FEAT-genre-taxonomy)_

Aggregation for the 통계 charts. Genre distribution needs first-class genres, so this **depends on
FEAT-genre-taxonomy** (plan.md Backlog). Artist/listen distribution comes from review counts **+
the `spotify_play_events` history accumulated since Step 3** (D29) — which is why that table is
seeded now rather than at Step 4 (the rolling-window snapshot keeps no history to count).

---

### Step 5 — Nested-bucket backend + retire `/reviews/queue` _(cross-repo)_

The two bucket implementations collapse to one — the nested `/profile→bucket` board with a
real backend. The flat `/reviews/queue` page is **retired** (D1), not unified.

- **shared_db**: add `parent_id UUID NULL FK → review_buckets(id) ON DELETE CASCADE` to
  `review_buckets`. No max depth (Q10, outliner standard). Migration is additive; existing
  flat buckets remain valid with `parent_id IS NULL`.
- **backend**:
  - Extend `GET /api/buckets` to return the recursive tree (parent-child shape).
  - New `PUT /api/buckets/{id}/move` — body `{parent_id?, position}` for DnD
    indent/outdent/reorder (DnD only — no Tab/arrow-button affordance, per D3).
  - **`DELETE /api/posts/{id}?hard=true` cascades to `review_bucket_items`** (D22):
    change FK behavior from `SET NULL` → `CASCADE`, or do explicit cleanup in
    `post_service.delete_post`. UI confirm modal text adds "관련 버킷 항목도 함께 삭제됩니다".
- **frontend**:
  - `/profile→bucket` moves from localStorage to `apiFetch` via new `src/lib/buckets.ts`
    adapter. DnD: left/right drop area = indent/outdent (D3).
  - **Card click = album-detail slide-over** (D4); inline ReviewDrawer becomes a separate
    explicit action (card menu button), no longer the default click.
  - **Card grid uses Library tile pattern** (Q11, `repeat(auto-fill, minmax(160px,1fr))`).
    `status` badge + `rec_reason` chip kept as overlay badges; `note` shown in album-detail
    panel only (not on tile).
  - **Retire**: `src/pages/reviews/queue.astro`, `src/components/queue/*` (BucketBoard,
    BucketColumn, AlbumCard, AddAlbumModal, AlbumDetailPanel, ReviewDrawer, queue.css).
    `queue.guard.ts` removed. Backend `/api/buckets/reorder` flat-list endpoint kept as
    compat for one release, then removed in a follow-up.
- **infra**: register `move` endpoint in `apigateway.tf` (JWT, copy `buckets_post` pattern).

**Verification**:

```
cd myblog_shared_db && pytest                  # parent_id model ↔ schema
cd myblog_backend && pytest tests/test_buckets.py tests/test_posts.py  # nested + cascade
cd infra && terraform plan                     # apigateway move + auth clean
cd myblog_front && pnpm lint && pnpm exec astro check
# browser: /profile→bucket nest/un-nest via DnD; delete review → bucket item gone (confirm);
#          /reviews/queue → 404 post-deploy
```

**Rollback**: revert frontend retirement + restore `/reviews/queue`; backend keeps
`parent_id` column (additive). DB rollback only on emergency.

---

### Step 6 — Multi-user accounts _(large, separate; may graduate to its own RFC)_

User/profile model, public `/members/[handle]`, followers/following/lists. Un-hides the social
stats. Likely its own RFC by the time we reach it.

---

## Open questions

_(All 3 resolved 2026-06-04 — see Decisions log D18 / D5 / D1.)_

~~1. **Library status home** — its own `library_items` table, or reuse/extend bucket-item
`status`?~~ → **Resolved (D18)**: neither. Three separate sources (to-listen new table,
recently-played cache, reviewed derived view).

~~2. **Now-playing source** — full personalize-light OAuth pipeline, or a lighter "last
scrobble" cache?~~ → **Resolved (D5)**: full personalize-light pipeline, hybrid (1h cron +
manual button).

~~3. **Bucket migration** — does the nested board _replace_ `/reviews/queue`, or do both stay
with different purposes?~~ → **Resolved (D1)**: replaces. `/reviews/queue` is retired in
Step 5.

## Decisions log

| Date       | Decision                                                                           | Step |
| ---------- | ---------------------------------------------------------------------------------- | ---- |
| 2026-06-04 | Scope Step 1 to frontend shell; real reviews + sample elsewhere behind one adapter | 1    |
| 2026-06-04 | Bucket tab = nested redesign on localStorage (not reuse flat queue) for Step 1     | 1    |
| 2026-06-04 | Now-playing mock + label now; worker-fed cache later (rule #9)                     | 1/3  |
| 2026-06-04 | Route = `/profile`; multi-user public profiles → `/members/[handle]` later         | 1/6  |
| 2026-06-04 | Hide follower/following/list stats in Step 1 (social = multi-user)                 | 1/6  |
| 2026-06-04 | **D1**: Retire `/reviews/queue` in Step 5 (not unify); single bucket UI at `/profile→bucket` | 5 |
| 2026-06-04 | **D3**: Nested bucket indent/outdent = DnD only (left/right drop area); no Tab/arrow-button | 5 |
| 2026-06-04 | **D4**: Bucket card click = album-detail slide-over; inline ReviewDrawer becomes card-menu action | 1/5 |
| 2026-06-04 | **D5**: Spotify sync = hybrid — EventBridge 1h cron + `/profile` 라이브러리 manual refresh button | 3 |
| 2026-06-04 | **D11**: Spotify write actions (save album / playlist export / library modify) deferred to a later RFC | 3 |
| 2026-06-04 | **D18**: Library tab = three separate sources (to-listen new table + recently-played cache + reviewed derived view); no unified `library_items` | 2/3 |
| 2026-06-04 | **D20**: Reviewed card unit = album (1 card per album); click opens N-review drawer (album↔review M:N preserved) | 2 |
| 2026-06-04 | **D21**: Single-review delete uses existing `DELETE /api/posts/{id}?hard=true` modal flow (no new UI) | 2/5 |
| 2026-06-04 | **D22**: Review hard-delete cascades to `review_bucket_items` (changes FK from SET NULL); confirm modal text updated | 5 |
| 2026-06-04 | **D23**: "Spotify Library 저장" is a separate explicit action, never auto-coupled to to-listen add | 2 |
| 2026-06-04 | **D25**: "들음" data = distinct album set of `/me/player/recently-played` 50-item rolling window | 3 |
| 2026-06-04 | **D26**: Label = "최근 들은 앨범" (not "Listened albums" — Spotify Web API can't back full history honestly) | 3 |
| 2026-06-04 | **Q10**: Nested bucket depth unlimited (outliner standard); enforce no cycle in app layer | 5 |
| 2026-06-04 | **Q11**: Bucket card grid = Library tile pattern (`repeat(auto-fill, minmax(160px,1fr))`); status/rec_reason badges; note in detail panel | 5 |
| 2026-06-04 | **Q16**: Spotify 연동 UI = `/profile → 연동` new tab (no separate settings page) | 3 |
| 2026-06-04 | **Q17**: Spotify refresh token in Secrets Manager `myblog/spotify`, not in DB | 3 |
| 2026-06-04 | **D27**: 연동 tab is thin (status only); the 1-time refresh-token consent is taken out-of-band via `scripts/spotify_bootstrap_token.py`. In-app PKCE start/callback endpoints deferred to a follow-up RFC (single-admin, single long-lived token doesn't justify a self-service OAuth UI now). | 3 |
| 2026-06-04 | **D28**: Listening GETs (`recently-listened`/`now-playing`/`spotify-connection`) are **intentionally public** single-admin vanity reads (edge_guard can't gate by login). `now-playing` drops `progress_ms`/`duration_ms` (fine-grained activity leak + frozen progress bar); idle response keeps `updated_at` so the UI shows "동기화 N분 전". | 3 |
| 2026-06-04 | **D29**: Add an append-only `spotify_play_events` table (additive to V9, snapshot reader unchanged) so Step 4's listen-count distribution has durable history — the rolling-window snapshot would otherwise leave Step 4 nothing to aggregate. | 3/4 |
| 2026-06-04 | **D30**: Worker writes back a Spotify-rotated `refresh_token` to `myblog/spotify` + records `last_successful_refresh_at`; connection status reflects token **validity** (shows "재인증 필요" after revoke), not mere presence. Re-auth runbook lives in the bootstrap-script header. | 3 |
| 2026-06-04 | **D31**: Manual refresh is debounced server-side (worker skips Spotify reads when cache < ~60s old) so spam can't burst Spotify into 429/DLQ and the non-commutative prune stays serialised; `last_synced_at` added to the recently-listened response and the UI polls it (replacing the blind 4s `setTimeout`). | 3 |
