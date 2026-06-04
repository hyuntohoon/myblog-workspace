# FEAT-member-dashboard: 회원 대시보드 (`/profile`)

- **Status**: closed (shipped 2026-06-04, Steps 1–5 + D28–D31 follow-ups end-to-end)
- **Owner**: TBD
- **Created**: 2026-06-04
- **Closed**: 2026-06-04 — plan row dropped in the same workspace PR that moved this file under `docs/archive/done/rfcs/`. Per-step merges live in `git log` across `myblog_shared_db` (v0.7.0–v0.10.0 / Neon V8–V11; #17, #18), `myblog_backend` (#48–#52), `myblog_worker` (#33–#37), `myblog_front` (#72, #76–#81), and workspace (#208, #210, #211, #213, #216, #217, #220, #223, #224, #225); summary entry added to `docs/archive/done/2026-06.md`. Step 5 verified with backend e2e 18/18 + integration 20/20 real-engine and front `/reviews/queue`→404 (prod smoke green). Follow-up **not** done: flat `PUT /api/buckets/reorder` kept live — cross-bucket album moves still depend on it; retirement is gated on first adding a nested-tree-aware item-move route (see §Step 5 retire note).
- **Plan row**: dropped on close

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
  deferred to a later RFC (D11). Step 3's Spotify read scopes are `user-read-recently-played` and
  `user-read-currently-playing` only.

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

> **Status — shipped baseline + adopted follow-ups.** The **baseline** below shipped end-to-end
> and is live in prod (shared_db #17 / worker #33 / backend #48 / front #76 / workspace #208;
> marked shipped in #209, prod smoke green: 5 real recently-listened rows, `connected:true`).
> Decisions **D28–D31** and the review fixes (drop `progress_ms`/`duration_ms` + idle
> `updated_at`, append-only events table, retry/backoff + symmetric isolation, server debounce +
> `last_synced_at` poll, token write-back, real-album panel, cron alarms) were adopted **after**
> ship and land as **post-ship follow-up PRs** (the "Follow-up rollout" block below). **D28, D29 +
> D31 shipped 2026-06-04** (D28: workspace #211 / front #77 / backend #49; D31: worker #34 /
> workspace #213 / backend #50 / front #78; D29: shared_db #18 v0.9.0 / Neon V10 / worker #35),
> and **D30 shipped 2026-06-04** (worker #36 / workspace #216+#217 / backend #51 / front #79 —
> all prod smoke green). The **final review fixes also shipped 2026-06-04**: retry/backoff +
> symmetric isolation (worker #37), the real-album panel (front #80), and the cron
> `FailedInvocations` alarm (workspace #220, `terraform apply`-ed; cache-staleness deferred).
> **Step 5** (nested-bucket backend) is the only remaining open work.

Pulls data per the **hybrid sync model (D5)**:
- **EventBridge cron, 1h**: worker reads `/me/player/recently-played`, then (a) upserts the
  distinct album set to the `spotify_recent_albums` snapshot cache (album_id, last_played_at,
  source='spotify') and prunes albums that fell out of the 50-item window, and (b) appends each
  individual play to an **append-only `spotify_play_events` table** (album_id, played_at) — a
  **new migration V10** (V9 already shipped to prod, so this can't fold into it); the durable
  history Step 4's listen-count distribution aggregates over. The snapshot alone only ever knows
  the current rolling window, so without the events table Step 4 has nothing to count (**D29**). Player/token reads go through a shared retry/backoff helper (3 tries, honour
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

**Follow-up rollout (post-ship).** The baseline already rolled out (secret created → V9 applied →
IAM/cron/JWT route via #208 `terraform apply` → refresh token bootstrapped). The D28–D31
follow-ups ship as normal cross-repo PRs; ordering notes:

1. ✅ **Shipped 2026-06-04** (shared_db #18 v0.9.0 → Neon **V10** applied → worker #35). The
   append-only `spotify_play_events` table (D29) is a **new migration V10** — V9 is immutable in
   prod, so it couldn't fold in. V10 applied to Neon (rule #3, psql + `ON_ERROR_STOP`) **before**
   the worker deploy that appends to it (the append shares the snapshot tx, so a missing table
   would fail the whole sync). Worker appends every play with `ON CONFLICT (album_id, played_at)
   DO NOTHING` (rolling-window re-read is a no-op); worker pin **not** bumped (raw SQL — only the
   migration must be live). prod smoke: append SQL ROLLBACK-validated on prod (`INSERT 0 1` /
   `INSERT 0 0`); manual refresh → table 0→50 rows. Backend pins v0.9.0 only at Step 4.
2. ✅ **Shipped 2026-06-04** (workspace #211 → front #77 → backend #49). Dropping
   `progress_ms`/`duration_ms` (D28) was a **contract change** → regen `openapi.json` + front
   types; the idle response now also carries `updated_at`. Merge order workspace→front→backend
   kept the front api.gen.ts drift gate green and gave a zero cosmetic window.
3. ✅ **Shipped 2026-06-04** (worker #34 → workspace #213 → backend #50 → front #78). Manual-refresh
   debounce + `last_synced_at` poll (D31). The worker skips Spotify reads when the cache is `<60s`
   old (age measured DB-side via `GREATEST(spotify_recent_albums.synced_at,
   spotify_now_playing.updated_at)`, skew-free; the 1h cron is never debounced). `last_synced_at`
   (additive, max `synced_at`) was added to the recently-listened response; the UI polls it until it
   advances past the click and shows a neutral "이미 최신 상태" on the debounced-timeout path. Merge
   order worker→workspace→backend→front (worker is contract-independent; workspace before front for
   the drift gate). prod smoke: refresh ×2 → only the 1st advanced `synced_at` (06:57→07:21), 2nd
   debounced. The debounce SELECT was also validated read-only against prod Postgres pre-merge.
4. ✅ **Shipped 2026-06-04** (workspace #217 infra+#216 contract → worker #36 → backend #51 →
   front #79). Token write-back (D30): a worker-only `secretsmanager:PutSecretValue` on
   `myblog/spotify` (separate policy — backend stays read-only) was `terraform apply`-ed (2 add / 0
   change / 0 destroy, no drift) **before** the worker deploy. The worker persists a rotated
   `refresh_token` + `last_successful_refresh_at` and flips `needs_reauth` on a 400 `invalid_grant`
   (transient 5xx never trips it); write-back is best-effort (non-fatal, never logs the token).
   `spotify-connection` exposes `needs_reauth` + `last_successful_refresh_at`; the 연동 tab shows
   연결됨 / 재인증 필요 / 연결 안 됨 with a last-refresh stamp. Recovery = re-run
   `spotify_bootstrap_token.py --write` (clears `needs_reauth`, stamps a fresh timestamp). prod
   smoke: worker cron invoke → secret gained `last_successful_refresh_at` → endpoint returned
   `{connected:true, needs_reauth:false, last_successful_refresh_at:…}`; deployed ProfileApp chunk
   ships all three states. The `needs_reauth` path is unit + browser verified (the live token was
   not revoked).
5. ✅ **Shipped 2026-06-04** (workspace #220, `terraform apply`: 2 add / 0 change / 0 destroy, no
   drift). Cron `FailedInvocations` alarm on **both** worker EventBridge crons (Spotify listening +
   MusicBrainz alias), namespace `AWS/Events` → existing `myblog-alerts` SNS topic; both alarms live
   (INSUFFICIENT_DATA = no failures yet). **Cache-staleness deferred** — not a native CloudWatch
   metric (would need a custom-metric canary).
6. ✅ **Shipped 2026-06-04** (worker #37 / front #80). Retry/backoff helper (3 tries, honour
   `Retry-After` on 429, 5xx + transport backoff; non-transient incl. token `invalid_grant` pass
   through) + **symmetric isolation** (recent-albums + now-playing both wrapped — a recent failure no
   longer aborts the tick). Real-album detail panel: a real 최근 들은 앨범 click now opens a real
   cover + metadata panel (no 샘플 badge, no fabricated tracklist; sample path unchanged). prod smoke
   green (worker invoke → cache `synced_at` advanced 10:13, 26 recent rows; front `ProfileApp` chunk
   ships the real panel + local-browser click-through). **Completes the follow-up rollout.**

**Verification** (baseline is prod-smoke-green per #209; the below cover the D28–D31 follow-ups +
regression):

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

**Rollback**: the baseline is live, so a baseline rollback is an **emergency** revert of the
shipped PRs (front → backend reads → worker, in that order so the deployed backend never queries a
dropped table) + (rule #3 human approval) drop the V9 tables `spotify_recent_albums` +
`spotify_now_playing`; the recent section + now-playing return to sample/idle. Follow-ups roll
back per-PR (drop V10 `spotify_play_events`; restore `progress_ms`/`duration_ms`).

---

### Step 4 — Genre / artist distribution

**Carved out → `docs/rfcs/FEAT-genre-artist-distribution.md`** (draft, plan.md Backlog).
Aggregation for the 통계 charts; depends on `FEAT-genre-taxonomy` (genre) + the
`spotify_play_events` history seeded here in Step 3 (D29, listen counts).

---

### Step 5 — Nested-bucket backend + retire `/reviews/queue` _(cross-repo)_

The two bucket implementations collapse to one — the nested `/profile→bucket` board with a
real backend. The flat `/reviews/queue` page is **retired** (D1), not unified.

> **Shipped 2026-06-04 (full Step 5).** 5.1 (shared_db `review_buckets.parent_id`, V11/**v0.10.0**,
> PR #19) plus the coupled landing: **backend #52** (nested-tree `GET /api/buckets` + `PUT
> /api/buckets/{id}/move` with app-layer cycle prevention and both source+dest sibling groups
> renumbered + D22 hard-delete cleanup of `review_bucket_items` (same-tx, app-layer — FK kept
> `SET NULL`, no migration) + pin v0.10.0), **workspace #224** (additive contract regen + infra
> `move` route, `terraform apply` 1-add/no-drift), **front #81** (`/profile` board on the API via
> `src/lib/buckets.ts`, `AddAlbumModal` relocated to `components/member/` + its `qb-*` styles ported
> into `member.css`, `/reviews/queue` retired). **GET decision:** kept the full nested `children[]`
> tree (RFC-literal) — safe through the deploy window because existing buckets are all roots, so the
> nested GET lists them flat-at-top with empty children and the still-live old flat board ignores the
> extra field. Verified: unit **121 pass**, integration **20 pass** (real Neon engine — nest/move/both
> cycle rejections/source-compaction + D22 cascade & soft-delete-keeps-item), prod smoke **18/18**
> (self-cleaning e2e: move nest/un-nest, cycle→400, D22 cascade) + front deployed-chunk grep
> (`/reviews/queue`→404, ProfileApp ships the API board + modal styles, D22 confirm copy live).

- **shared_db** ✅ **shipped (v0.10.0 / V11, prod Neon)**: added `parent_id UUID NULL FK →
  review_buckets(id) ON DELETE CASCADE` + `idx_review_buckets_parent_id`. No max depth (Q10,
  outliner standard). Additive; existing flat buckets remain valid with `parent_id IS NULL`.
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
    BucketColumn, AlbumCard, AlbumDetailPanel, ReviewDrawer) + `src/styles/queue.css`,
    **except `AddAlbumModal.tsx`** — relocate it to `src/components/member/` first: the shipped
    Step 2 `LibraryTab.tsx` still imports it (with its `AddOutcome` type) and renders it, so a
    blind delete breaks the live Library tab's add-album flow and fails the front build.
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

### Step 6 — Multi-user accounts

**Carved out → `docs/rfcs/FEAT-multi-user-accounts.md`** (draft, plan.md Backlog).
User/profile model, public `/members/[handle]`, social graph; un-hides the social stats.

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
| 2026-06-04 | **D29**: Add an append-only `spotify_play_events` table (post-ship **migration V10** — V9 already in prod; snapshot reader unchanged) so Step 4's listen-count distribution has durable history — the rolling-window snapshot would otherwise leave Step 4 nothing to aggregate. | 3/4 |
| 2026-06-04 | **D30**: Worker writes back a Spotify-rotated `refresh_token` to `myblog/spotify` + records `last_successful_refresh_at`; connection status reflects token **validity** (shows "재인증 필요" after revoke), not mere presence. Re-auth runbook lives in the bootstrap-script header. | 3 |
| 2026-06-04 | **D31**: Manual refresh is debounced server-side (worker skips Spotify reads when cache < ~60s old) so spam can't burst Spotify into 429/DLQ and the non-commutative prune stays serialised; `last_synced_at` added to the recently-listened response and the UI polls it (replacing the blind 4s `setTimeout`). | 3 |
