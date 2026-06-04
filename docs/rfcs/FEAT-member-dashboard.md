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
- **Not rebuilding the shipped bucket board this step.** The existing flat `/reviews/queue`
  board (FEAT-review-bucket-board, #193–197) stays as-is until the nested-bucket backend step.

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
  persisted to **localStorage** — frontend-only this step. Coexists with `/reviews/queue` until
  the nested-bucket backend step.
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

### Step 2 — Library status (backend) _(cross-repo)_

Persist library state (듣는 중 / 들음 / 평론함 / 위시리스트) per album. Likely a `library_items`
table (shared_db) + `GET/PATCH /api/.../library`. Adapter's library section → real. Contract
change → regenerate `openapi.json` + frontend types.

---

### Step 3 — Listening history + now-playing (worker-fed) _(cross-repo)_

Recently-played albums/tracks + "now playing" from a **worker/EventBridge-fed cache**, never a
synchronous user-facing Spotify call (rule #9). Builds on the **FEAT-spotify-personalize-light**
idea already in `plan.md` Frozen (OAuth 1회 → refresh token → Secrets → EventBridge fetch). Adapter's
now-playing + recent sections → real.

---

### Step 4 — Genre / artist distribution _(depends on FEAT-genre-taxonomy)_

Aggregation for the 통계 charts. Genre distribution needs first-class genres, so this **depends on
FEAT-genre-taxonomy** (plan.md Backlog). Artist distribution can come from review/listen counts.

---

### Step 5 — Nested-bucket backend + unify `/reviews/queue` _(cross-repo)_

Add `parent_id` (or a nesting model) to `review_buckets` + recursive API; point the member page's
bucket tab at it; **unify or retire** the flat `/reviews/queue` board so only one bucket UI remains.

---

### Step 6 — Multi-user accounts _(large, separate; may graduate to its own RFC)_

User/profile model, public `/members/[handle]`, followers/following/lists. Un-hides the social
stats. Likely its own RFC by the time we reach it.

---

## Open questions

1. **Library status home** — its own `library_items` table, or reuse/extend bucket-item `status`?
   Blocks Step 2.
2. **Now-playing source** — full personalize-light OAuth pipeline, or a lighter "last scrobble"
   cache? Blocks Step 3.
3. **Bucket migration** — does the nested board _replace_ `/reviews/queue`, or do both stay with
   different purposes? Blocks Step 5.

## Decisions log

| Date       | Decision                                                                           | Step |
| ---------- | ---------------------------------------------------------------------------------- | ---- |
| 2026-06-04 | Scope Step 1 to frontend shell; real reviews + sample elsewhere behind one adapter | 1    |
| 2026-06-04 | Bucket tab = nested redesign on localStorage (not reuse flat queue) for Step 1     | 1    |
| 2026-06-04 | Now-playing mock + label now; worker-fed cache later (rule #9)                     | 1/3  |
| 2026-06-04 | Route = `/profile`; multi-user public profiles → `/members/[handle]` later         | 1/6  |
| 2026-06-04 | Hide follower/following/list stats in Step 1 (social = multi-user)                 | 1/6  |
