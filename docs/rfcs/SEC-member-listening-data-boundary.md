# SEC-member-listening-data-boundary: the owner's listening history is visible to every signed-in member

- **Status**: **accepted** (owner-approved in-session 2026-08-30, all three steps, together with OQ1)
- **Owner**: 오너
- **Created**: 2026-08-30
- **Plan row**: `plan.md` → SEC-member-listening-data-boundary

---

## Goal

Every listening-history widget on a member's own dashboard shows **that member's** data or shows
nothing. Today six `GET /api/library/*` reads are `edge_guard`-only, carry no user scope at all, and
are rendered by `SelfDashboard` for any signed-in member — so a second member's Overview tab is a
window onto the owner's now-playing, recently-played albums, cumulative listen counts and 좋아요
library. This RFC closes that read boundary, and it separates the three cases so the closure is not
blocked on the one that needs a schema.

This is a privacy boundary, not playback polish. It is sequenced ahead of
`ARCH-playback-authority-convergence` for that reason (owner decision, 2026-08-30).

## Non-goals

- No change to the owner's own experience. Every widget listed here keeps working, unchanged, for
  the owner.
- No retro-fitting of `user_id` onto `spotify_play_events` / `spotify_recent_albums` /
  `spotify_saved_tracks`. Those are owner-global by construction (V45's own header records the
  decision: *"owner-global `spotify_*` caches and their worker jobs stay untouched"*), and a
  backfill has no per-member source to backfill from.
- No new provider polling. Everything member-scoped here is already written by the worker's
  per-member poll (`myblog_worker/worker/service/spotify_member_sync_service.py`).
- Not a change to `/api/library/stream-history/*` or `/api/library/to-listen` — both are already
  member-scoped via `provisioned_member_id` and are correct today.

## Current state

Verified against `origin/main` in `myblog_backend`, `myblog_front` and `myblog_shared_db` on
2026-08-30, not from the RFC that introduced them.

### The guard actually in force

`myblog_backend/app/api/routes/library.py` — these route handlers take `db` + `svc` and **nothing
else**. There is no `provisioned_member_id`, no `require_owner`. They ride the API GW `GET`
catch-all, so the only thing in front of them is the CloudFront edge check:

| Route | Handler | Scope dependency |
|---|---|---|
| `GET /api/library/now-playing` | `now_playing` | none |
| `GET /api/library/recently-listened` | `list_recently_listened` | none |
| `GET /api/library/recent-tracks` | `list_recent_tracks` | none |
| `GET /api/library/listened-albums` | `list_listened_albums` | none |
| `GET /api/library/saved-tracks` | `list_saved_tracks` | none |
| `GET /api/library/saved-tracks/{genre,artist}-distribution` | | none |
| `GET /api/library/play-events/{genre,artist}-distribution` | | none |
| `GET /api/library/stream-history/*` | | `provisioned_member_id` ✅ |
| `GET /api/library/to-listen` | `list_to_listen` | `provisioned_member_id` ✅ |

### Why they cannot simply take a `member_id`

The tables have no user column. From `myblog_shared_db` `tests/canonical_schema.sql`:

- `spotify_now_playing` — `id SMALLINT PRIMARY KEY DEFAULT 1` with a **singleton CHECK constraint**.
  One row, for the whole installation.
- `spotify_recent_albums`, `spotify_play_events`, `spotify_track_play_events`,
  `spotify_recent_tracks`, `spotify_saved_tracks` — no `user_id`, no `member_id`.
- `spotify_stream_history` — `user_id` added by V46. This is why the stream-history panels are
  already correct.

So `WHERE user_id = :me` is not available on any of the six, and adding it is not a formality —
there is no per-member history in those rows to scope.

### What already exists per member

V45 shipped two per-member tables, written by the worker's per-member Spotify poll:

- `spotify_member_now_playing` — `user_id` PK, `is_playing`, track/artist/album/image,
  `progress_ms`, `duration_ms`, `updated_at`. Already read by
  `IntegrationService.public_now_playing` and served publicly at
  `GET /api/members/{handle}/now-playing`.
- `spotify_member_recent_tracks` — `user_id` FK, `spotify_track_id`, names, `image_url`,
  `played_at`. **Written by the worker and read by nothing.** There is no route over it.

### What the front renders, for whom

`SelfDashboard.tsx` is mounted for **any** signed-in member on their own profile — the only thing it
branches on is `handle === OWNER_HANDLE`, and that branch only picks the 평론 source
(`/profile-reviews.json` vs `publicReviews`). Every panel below is rendered identically for a
non-owner:

| Widget | Component | Read | Whose data a non-owner sees |
|---|---|---|---|
| 지금 재생 중 | `NowPlaying` (`OverviewDash` card `nowplaying`) | `/api/library/now-playing` | **owner's** |
| 최근 재생 트랙 | `OverviewDash` | `/api/library/recent-tracks` | **owner's** |
| 최근 들은 앨범 | `OverviewDash`, `BucketBoard` | `/api/library/recently-listened` | **owner's** |
| 들은 앨범(누적) | `OverviewDash` | `/api/library/listened-albums` | **owner's** |
| 좋아요 보드 | `LikedBoard` (`StatsTab`) | `/api/library/saved-tracks` | **owner's** |
| 좋아요 분석 | `LikedAnalysis` | `saved-tracks/*-distribution` | **owner's** |
| 오늘의 곡 고르기 | `TodaySongPicker` (Home) | `/api/library/saved-tracks` | **owner's** |
| 임포트 분석 | `ImportAnalysis` | `stream-history/*` | their own ✅ |
| Last.fm 지금 재생 | `LastfmNowPlaying` | `/api/integrations/lastfm/now-playing` | their own ✅ |

## Target state

Three classes, closed in three steps, each independently shippable:

- **(a) owner-only legacy with no per-member source** — `recently-listened`, `listened-albums`,
  `saved-tracks` + both saved/play-event distributions. The read stays owner-global; the *widget*
  becomes owner-only, and a non-owner sees an honest empty/absent panel rather than someone else's
  history. Front-only, no contract change. **This is the P0 and it is Step 1.**
- **(b) member-scoped replacement already possible** — `now-playing` and `recent-tracks`. The data
  is already in `spotify_member_now_playing` / `spotify_member_recent_tracks`; only a self-scoped
  read route is missing. Step 2.
- **(c) needs durable per-member history** — album-level recently-played and cumulative listen
  counts, and the 좋아요 library. These need new per-member tables and a per-member worker job
  before the widget can come back for a non-owner. Step 3, and it is the only step that needs a
  migration.

## Steps

### Step 1 — stop rendering owner-global listening data to non-owners (P0)

Front-only. `SelfDashboard` already computes `isOwner`; thread it (or a small
`useIsDashboardOwner()`) to the widgets in class (a) and render them only for the owner. A non-owner
gets the panel omitted, not a spinner over an empty read — an empty state that reads "아직 기록이
없어요" would be a lie about someone else's data. The Home `TodaySongPicker` 좋아요 source is
owner-gated the same way.

Backend, same PR: add `require_owner` to the class-(a) routes so the boundary does not depend on the
front remembering. `/api/library/{recently-listened,listened-albums,saved-tracks,
saved-tracks/*-distribution,play-events/*-distribution}` become owner-only; per CLAUDE.md, every
newly protected route is checked against `infra/apigateway.tf` in the same change.

**Verification**:
```
# front
pnpm lint && pnpm exec astro check && pnpm test
# backend
pytest
# both guard copies read (auth-touching change), apigateway.tf route match confirmed
# prod smoke + a real-browser clickthrough as a NON-owner member, asserting the
# owner's now-playing/좋아요 are absent rather than merely empty
```

**Rollback**: revert the PR. Read-side gate only, no data change.

---

### Step 2 — self-scoped now-playing and recently-played over the V45 member tables

Add `GET /api/me/now-playing` and `GET /api/me/recent-tracks`, both `provisioned_member_id`-scoped,
reading `spotify_member_now_playing` / `spotify_member_recent_tracks`. Contract change → the
`docs/contracts/README.md` procedure (service `openapi.json` → workspace merge → front `api.gen.ts`),
and the two new authenticated routes go into `infra/apigateway.tf`.

Front: `NowPlaying` and the 최근 재생 트랙 card read the self-scoped routes for a non-owner and keep
the legacy owner-global reads for the owner, so the owner's richer catalog-resolved payload is not
regressed. The owner's own poller row exists too, so the split is a source choice, not a feature gap.

**Verification**:
```
pytest && pnpm test && pnpm lint && pnpm exec astro check
# contract: openapi regenerated + committed, workspace contract merged, api.gen.ts diff = new routes only
# non-owner clickthrough: their OWN Spotify play appears in 지금 재생 중
```

**Rollback**: revert front first, then backend — the routes are additive and safe to leave live.

---

### Step 3 — durable per-member album history and saved tracks **[needs a migration]**

Only after Steps 1–2 are live. Per-member analogs of `spotify_recent_albums` /
`spotify_play_events` / `spotify_saved_tracks`, written by the existing per-member poll, and the
class-(a) widgets un-gated for members once their own data backs them. Sequenced per
`reference-shared-db-cross-repo-rollout`: migration → prod apply → service pin → contract → front.

**Open until Step 2 ships**: whether members want these panels at all, or whether 임포트 분석
(stream-history, already member-scoped) is the whole answer for a non-owner. Deciding that before
paying for three tables is the point of putting this step last.

---

## Open questions

1. ~~**Does the owner want class-(a) widgets to disappear for non-owners, or render an explicit
   "소유자 전용" note?**~~ **Answered 2026-08-30 — omit silently.** A non-owner has no reason to be
   told what they are not seeing. Step 1 renders the class-(a) panels only for the owner; for a
   non-owner the panel is absent from the layout, not an empty card and not a "소유자 전용" note.
2. **Should `/api/library/now-playing` keep existing after Step 2?** Blocks nothing; it stays as the
   owner's own richer read unless Step 3 subsumes it.
3. **Is Step 3 worth building at all?** See Step 3. Blocks Step 3.

## Decisions log

| Date | Decision | Step |
|------|----------|------|
| 2026-08-30 | Owner: handle this as a separate RFC/PR ahead of the playback work, classifying widgets into (a)/(b)/(c) before implementing | — |
| 2026-08-30 | Owner accepted the RFC in-session, all three steps as drafted | — |
| 2026-08-30 | Owner (OQ1): class-(a) widgets are omitted silently for a non-owner — no "소유자 전용" note | 1 |
| 2026-08-30 | Owner: Step 1 merges **before** `ARCH-playback-authority-convergence` Step 1 (`myblog_front#428`), which is implemented and waiting | 1 |
