# SEC-member-listening-data-boundary: the owner's listening history is visible to every signed-in member

- **Status**: **done — scope reduced to Step 1** (2026-09-01; archived). Accepted in-session
  2026-08-30 for all three steps together with OQ1. **Step 1 shipped and production-verified
  2026-08-30 and closed the leak completely**: with the owner's amended scope all nine routes are
  `require_owner`-gated, class (b) included, so the boundary this RFC exists to fix measures **zero**
  today. **Steps 2 and 3 were never built, and on 2026-09-01 the owner deferred them to `plan.md` →
  Backlog behind a trigger rather than leaving this RFC open.** The deciding evidence was a
  current-state audit run before starting Step 2 — see *Closeout audit* below: the population Step 2
  serves is **0 of 3** non-owner accounts, and the step's own verification is not executable today.
  Status promoted in-session by the owner under CLAUDE.md rule #7's explicit-approval exception.
  Reopen with a fresh `plan.md` row, not by editing this file.
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

> **Corrected at closeout (2026-09-01).** "Six" is this RFC's own headline number and it is wrong:
> the route table below lists **nine**, Step 1 shipped against nine, and the production verification
> was nine 403s. Left in place rather than silently edited, because the miscount is part of why
> Step 1's scope had to be amended by the owner mid-flight.

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
  **Amended 2026-08-30 (owner):** these two are *also gated in Step 1*. As drafted, Step 1 would
  have shipped with a third of the leak still live — a P0 privacy step that closes five of nine
  routes is not closed. Gating them now costs two widgets and makes Step 2 purely additive: it
  gives members back their OWN data rather than merely swapping a source.
- **(c) needs durable per-member history** — album-level recently-played and cumulative listen
  counts, and the 좋아요 library. These need new per-member tables and a per-member worker job
  before the widget can come back for a non-owner. Step 3, and it is the only step that needs a
  migration.

## Steps

### Step 1 — stop rendering owner-global listening data to non-owners (P0)

**Shipped scope differs from the draft above — read this, not the class table, for what Step 1 did.**
The owner amended it in-session on 2026-08-30: **all nine** routes are gated, class (b) included,
so the leak is zero on this deploy rather than two-thirds closed.

`SelfDashboard` already computes `isOwner`; it is threaded to the widgets and they render only for
the owner. A non-owner gets the panel **omitted**, not a spinner over an empty read — an empty state
reading "아직 기록이 없어요" would be a lie about someone else's data (OQ1).

Backend, same step: `require_owner` on `/api/library/{now-playing,recently-listened,recent-tracks,
listened-albums,saved-tracks,saved-tracks/*-distribution,play-events/*-distribution}`, so the
boundary does not depend on the front remembering.

**Three things the draft above got wrong, found while implementing:**

1. **`infra/apigateway.tf` needs no route change.** These are GETs on the `GET /api/{proxy+}`
   catch-all, which carries no authorizer — the JWT is verified in the Lambda. The already
   member-scoped `stream-history/*` GETs and the owner-gated `GET /api/posts` prove it by working
   today. CLAUDE.md's route-match rule is about *mutations*. Only the file's comments changed, and
   `terraform plan` reports No changes.
2. **The Home `TodaySongPicker` needed nothing.** Its only entry is `TodaySongBuckit`, which already
   renders the trigger behind `isOwnerUser()`.
3. **`useSpotifyLibrary` was a ninth surface this RFC's table never listed** (review found it). It
   calls `listListenedAlbums()` on every `BucketBoard` mount, so a member opening My Buckit fetched
   the owner's listened archive and stamped their own bucket covers "이미 들음" from it. Its comment
   claimed the board "only ever mounts on the self-dashboard, so this is inherently own-view-only" —
   the exact assumption this RFC disproves. **Lesson for Steps 2–3: the widget inventory was
   assembled from components, and a shared hook was invisible to it. Grep the api client's callers,
   not the dashboard's components.**

Also discovered: gating the fetch is not sufficient where a widget caches. `BucketBoard`'s
최근 들은 앨범 strip seeds from `localStorage['lf_crate_recent']`, so a member who had already
loaded the board would have kept painting the owner's albums from their own browser indefinitely
after the server closed. The seed is refused and the stale cache evicted.

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

**Stale as written — Step 1's amended scope changed the starting point.** Step 1 removed
`nowplaying` and `recent-tracks` from `OverviewDash`'s widget registry entirely for a non-owner, so
Step 2 does not adjust an existing render path: it **re-admits** the two widget ids for members and
points them at the self-scoped routes. Note also that a member's saved layout (`lf_ov_rows`) was
rewritten without those ids when they first loaded Step 1, so re-admitting the widget is not enough
to bring it back onto their board — Step 2 must re-add it to their layout or say plainly that they
re-add it via ＋ 컴포넌트 추가.

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

---

## Closeout audit — 2026-09-01

Run against `origin/main` before starting Step 2, per `feedback-rfc-current-state-audit`. Three of
this RFC's own statements did not survive it, and one measurement decided the outcome.

### The "nothing reads them" premise was half wrong

Step 2 is introduced as reading V45 tables "the worker already writes but nothing reads". That holds
for **`spotify_member_recent_tracks` — zero readers** anywhere in the backend. It does **not** hold
for `spotify_member_now_playing`, which has been read since before this RFC was written:
`IntegrationService.public_now_playing()` (`app/services/integration_service.py:269`) merges it with
the Last.fm now-playing cache and serves `GET /api/members/{handle}/now-playing`
(`app/api/routes/members.py:112`). That route is *public and handle-scoped*, deliberately flattening
"not connected" and "nothing playing" to keep integration status private — so it does not do Step 2's
job, and Step 2 was not redundant. But the premise as written would have sent an implementer looking
for a table nobody touches, and that is not what they would have found.

### Members already have half of what Step 2 promises

Not recorded anywhere in this RFC: `lastfm-nowplaying` ("Last.fm 지금 듣기") is **not** in
`OWNER_ONLY_WIDGETS` (`myblog_front/src/components/member/OverviewDash.tsx:246`), so a non-owner
already has a now-playing card. The gap Step 2 closes is the **Spotify half only**, not "지금 재생
중" as a whole.

### What actually decided it: nobody is on the other side of the boundary

Read-only count against production:

| | |
|---|---|
| `users` | **4** |
| users with a `spotify` integration | **1** |
| `spotify_member_now_playing` rows | **1** (`is_playing` = 0) |
| `spotify_member_recent_tracks` rows | **1,953**, across **1** distinct `user_id` |

That one user is the owner (`user-0468fd3c`, matching `OWNER_SUB`). The other three accounts have no
Spotify and no Last.fm integration and zero rows in either table.

Step 2 exists to give **non-owners** their own listening data. Its addressable population is
**0 of 3**. Shipping it would add two routes, a contract change and a front re-admit that render an
empty card for every member who is not the owner — and its own verification line, *"non-owner
clickthrough: their OWN Spotify play appears in 지금 재생 중"*, **cannot be performed**, because no
second connected account exists to perform it with.

Step 3 already carried the right instinct — *"whether members want these panels at all … Deciding
that before paying for three tables is the point of putting this step last."* The audit's finding is
that the same reasoning applies one step earlier.

### Why closing is safe

Step 1 did not partially close the leak, it closed it: nine of nine routes `require_owner`, verified
in production with a real non-owner token (403 on all nine, while `to-listen`, `stream-history/*` and
`/api/me` stay 200). **None of the nine owner-global listening reads is exposed by stopping here**,
and the gate is regression-pinned in two places rather than self-attested —
`myblog_backend/tests/test_route_guard_map.py` and `scripts/smoke.py` (nine 403s plus two 200
controls). What remains is a feature gap for members, not a boundary defect — which is why it belongs
in Backlog behind a usage trigger rather than in an open security RFC.

**Scoped deliberately: "the nine listening reads", not "nothing at all".** Closeout review found the
absolute phrasing this section first used was broader than what was verified.
`GET /api/library/spotify-connection` (`app/api/routes/library.py:253`) takes **no dependency at
all**, and `edge_guard` (`app/main.py:52-75`) passes any `/api/*` request carrying the
CloudFront-injected `x-origin-verify` **without a JWT** — the same posture the repo documents as
*public* elsewhere. Since every front request reaches the backend through CloudFront, that route is
reachable rather than merely dormant, and it returns the owner's `connected` / `needs_reauth` /
`last_successful_refresh_at` — the integration status `public_now_playing` deliberately flattens to
keep private. Its front helper `getSpotifyConnection` (`spotify.api.ts:114`) is defined and never
called, so the "zero callers" half is true. **It is out of this RFC's scope by owner decision and is
not fixed here**, but it is recorded because "nothing is exposed" was the wrong sentence to close a
security RFC with.

**One structural note for whoever owns the boundary next.** `test_route_guard_map.py` is an
*allowlist* of owner-only endpoints: it pins the nine, but it cannot fail when a *new* ungated read is
added to `library.py`. With this RFC closed, that is the only standing structural guard on the
boundary.

### Decisions banked for whoever picks this up

- **Source for `/api/me/now-playing`, if it is ever built: Spotify-only**, reading
  `spotify_member_now_playing` directly as Step 2 drafts it — *not* a self-scoped reuse of
  `public_now_playing`'s Last.fm+Spotify merge (owner, 2026-09-01). This keeps `nowplaying` as the
  Spotify card and `lastfm-nowplaying` as the Last.fm card, mirroring what the owner already sees,
  and avoids two overlapping merged cards on one dashboard. Recorded so the fork is not re-derived.
- Step 2's "**stale as written**" note stands and is still the correct starting point: Step 1 removed
  the widget ids from a non-owner's registry entirely, so Step 2 **re-admits** them rather than
  repointing an existing render path — and a member's saved `lf_ov_rows` layout was rewritten without
  those ids, so re-admitting the widget does not by itself put it back on their board.
- OQ2 (does `/api/library/now-playing` keep existing?) closes as **yes, unchanged** — it is the
  owner's own richer read and Step 3, which might have subsumed it, is not being built.

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
| 2026-08-30 | **Step 1 shipped and production-verified.** `myblog_backend@5675d00` → `myblog-workspace@11ce8f4` → `myblog_front@673bf08`. Nine routes `403` for a non-owner in prod, controls still `200`, prod smoke 30/30, non-owner clickthrough passed with an `origin/main` control (4/4 widgets and 5 calls there, 0 and 0 on the shipped code) | 1 |
| 2026-08-30 | Merge order is **service → workspace → front** for an additive contract change, not workspace-first: `workspace-check` re-merges the contract from both services' `main`, so the workspace PR is red until the service spec lands. Recorded because the usual rule says the opposite | — |
| 2026-08-30 | Owner **expanded Step 1's scope**: class (b) (`now-playing`, `recent-tracks`) is gated now too, not deferred to Step 2 — all nine routes. Rationale: a P0 privacy step that leaves a third of the leak live is not a closure, and Step 2 becomes purely additive | 1, 2 |
| 2026-09-01 | Closeout audit before starting Step 2 found the addressable population is **0 of 3** non-owner accounts — the only user with member listening data is the owner — and that Step 2's own non-owner verification is therefore not executable | 2 |
| 2026-09-01 | Owner: **defer Steps 2–3 to Backlog behind a usage trigger and close this RFC at Step 1.** Step 1 already measures the leak at zero, so what remains is a member feature gap, not a boundary defect | — |
| 2026-09-01 | Owner: if `/api/me/now-playing` is ever built it reads `spotify_member_now_playing` **directly (Spotify-only)**, not a self-scoped reuse of `public_now_playing`'s Last.fm+Spotify merge — banked so the fork is not re-derived | 2 |
| 2026-09-01 | Audit correction: the "nothing reads the V45 tables" premise held only for `spotify_member_recent_tracks`; `spotify_member_now_playing` has been read by the public profile route since before this RFC | 2 |
| 2026-09-01 | Audit correction: `lastfm-nowplaying` is not owner-only, so members already had a now-playing card — Step 2's real gap was the Spotify half only. Never recorded in the RFC body | 2 |
