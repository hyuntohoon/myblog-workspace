# RESEARCH-playback-product-architecture: Playback product strategy

- **Status**: done
- **Owner**: 박지훈
- **Created**: 2026-07-02
- **Plan row**: `plan.md` → RESEARCH-playback-product-architecture

---

## Goal

Determine whether the current Spotify SDK/API integration and playback architecture can
support a **Spotify-like-but-simpler playback experience** for this project — specifically
the one FEAT-lyrics-viewer needs (current track identity + playback position for the
currently-playing track only) — and decide whether a **separate custom playback RFC is
necessary**, or whether existing capability + a small amount of UI/state work suffices.

This is a **decision research RFC, not an implementation**: it separates confirmed current
capabilities, gaps/constraints, items requiring verification, MVP features to retain/defer,
and a single recommended next step grounded in evidence.

## Non-goals

- **No implementation.** No code, no schema, no route is added here.
- **Not a Spotify feature inventory.** Only the operations needed for *this* project's
  listening/bucket/lyrics flows are evaluated — no exhaustive SDK capability catalog.
- **No assumption that custom playback is required.** The recommendation may be "no
  custom playback RFC; consume what exists."
- **No multi-listener / per-user streaming tokens.** v1 is single-owner (the owner's Premium
  account); multi-user playback is gated on FEAT-multi-user-accounts (per FEAT-spotify-streaming-playback).
- **No in-app OAuth/PKCE consent.** Stays deferred (D27) — provisioning is a one-time owner-run script.
- **No continuous-progress karaoke/auto-advance.** FEAT-lyrics-viewer is manual-nav only;
  this research asks only whether position can be read for one-shot focus, not for live tracking.

## Current state (verified against code 2026-07-02)

### Two separate playback-adjacent surfaces exist

1. **`NowPlaying` — read-only display, the live anchor FEAT-lyrics-viewer wants to bind to.**
   `components/member/NowPlaying.tsx` renders `banner | full | list` variants off **one**
   `useNowPlaying()` hook → `getNowPlayingData()` (`src/components/member/spotify.api.ts:86`)
   → `GET /api/library/now-playing`. The backend `NowPlayingResponse`
   (`schemas.py:589-603`) is an **intentionally-public single-admin vanity read
   (edge_guard-only, no JWT)** that **deliberately omits `progress_ms` / `duration_ms` (D28)**
   — *"a ≤1h-stale snapshot can't advance a progress bar."* It exposes: `is_playing`,
   `track`, `artist`, `album`, `album_id`, `album_cover_url`, `updated_at`. It is
   **manual-refresh only** (no live polling) and shows "최근 재생" (recent-tracks row 0) when idle.
   **Critically: no ▶ button on `NowPlaying` — it is explicitly "not a player."**

2. **Streaming playback — the live-play path, separate from now-playing.**
   `myblog_front/src/lib/spotifyPlayback.ts` is the **sole** SDK/token owner. `requestPlayback(target)`
   (`:243`) is the only entry that mints a token (`getStreamingToken`, `:70`, JWT-gated) and
   loads the Web Playback SDK (`ensureSdk`/`ensureConnectedDevice`, `:140-198`). It resolves a
   catalog DB id → spotify URI via `resolveProviderUri` (`:210`) → `GET /api/playback/resolve`
   (edge_guard-only, direct `spotify_id` DB read — no Spotify search), then `PUT /v1/me/player/play`.
   Token+SDK load fire **only on a real ▶ click** (rule #9-safe). Scoped for
   `user-read-playback-state` among others, minted from the owner's `streaming_refresh_token`
   in SSM `/myblog/spotify`. ▶ works on two sites only: the Pocket tray (`PocketTray.tsx:587`,
   React `onClick`) and the review tracklist (`scripts/albumDetail.client.ts:130`, vanilla).
   FEAT-spotify-streaming-playback (done 2026-06-25) verified real audio plays on a Premium session.

### Position data exists server-side but is not exposed

The worker saves `progress_ms` / `duration_ms` into the now-playing snapshot
(`worker/service/listening_sync_service.py`; per FEAT-lyrics-viewer's audit), but the backend
**does not expose them** (D28). So position is available upstream of the API but blocked at the
response boundary by design.

## MVP playback experience needed by this project

The only consumer in flight (FEAT-lyrics-viewer) needs, for the **currently playing track only**:

- **Track identity** — track id + title/artist (to select the right lyrics). `NowPlaying` already
  provides this (minus a `track_id`, which it lacks — see gaps).
- **"is something playing"** — `NowPlaying.is_playing` already provides this.
- **Playback position (one-shot, on manual refresh)** — to optionally initialize the focus line
  on a lyrics refresh. Not a live ticker. FEAT-lyrics-viewer is manual-nav; position is a
  convenience for one-shot initial focus, degraded to "track identity only" if absent.
- **An entry point to open the viewer** — bound to the now-playing area's active-playback state;
  hidden with no recent-history fallback when idle.

This is strictly **less** than a full player (no play/pause/seek/next/queue in the viewer; those
belong to the existing ▶ sites and to Spotify's own client).

## What the existing Spotify SDK/API integration can support

| Need | Existing capability | Verdict |
|---|---|---|
| Track identity (title/artist/album) | `NowPlaying` snapshot via `GET /api/library/now-playing` | ✅ Confirmed |
| "is playing" | `NowPlaying.is_playing` | ✅ Confirmed |
| Track id (to fetch lyrics) | `NowPlaying` lacks `track_id`; `album_id` present but lyrics are track-scoped | ⚠️ Gap — verify what id the snapshot holds |
| Playback position (one-shot) | `streaming_refresh_token` scopes include `user-read-playback-state` (FEAT-spotify-streaming-playback OQ). The token mint can call `GET /v1/me/player` (currently-playing incl. `progress_ms`). **No code calls it today.** | ⚠️ Capable-but-unbuilt — confirm the SDK-or-API read path |
| Start playback | `requestPlayback` + ▶ on tray/review tracklist | ✅ Confirmed (owner Premium) |
| Entry point mount | `NowPlaying` is React, on the authed `/profile`; viewer consumes ARCH-frontend-component-map's overlay ownership | ✅ Confirmed (capability exists; wiring is the viewer's RFC) |

## Gaps / constraints

- **No `track_id` on the now-playing read path.** FEAT-lyrics-viewer needs a track-id to hit its
  authenticated lyrics endpoint; `NowPlaying` carries `album_id` but not `track_id`. **Verified
  2026-07-02 (code): the `SpotifyNowPlaying` table (`models.py:766-785`) stores `track_name`,
  `artist_name`, `album_name`, `album_id` (FK), `progress_ms`, `duration_ms`, `updated_at` — and
  **no `track_id` / `spotify_track_id` column**.** The worker writes the track *name* but not its
  catalog id. So a lyrics lookup cannot get a track id from the cached snapshot alone. Options Step
  1 weighs: (a) the live `/v1/me/player` read (resolution #2 above) returns `item.id` = the
  `spotify_track_id` — resolve to the catalog `tracks.id` via the same direct read
  `PlaybackService.resolve_uri` already does (reverse direction: spotify_id → `Track.id`); (b) add a
  `track_id` column to the snapshot. (a) needs no schema change and matches the "live read on
  demand" model; (b) re-opens the D28 boundary. **Decided 2026-07-02 (pre-acceptance review,
  recorded in FEAT-lyrics-viewer): (a)** — the lyrics endpoint accepts the `spotify_track_id`
  from the live read and resolves it server-side to `Track.id` (one round trip, no separate
  resolve endpoint).
- **Position not exposed (D28, by design).** The D28 rationale ("a ≤1h-stale snapshot can't advance a
  progress bar") applies to *continuous* progress — but FEAT-lyrics-viewer's position need is
  *one-shot*, exactly the case D28's frozen-bar argument does not block. **Items requiring
  verification** below.
- **The now-playing snapshot can be up to ~1h stale** (hourly cron + manual refresh). A one-shot
  position from a ≤1h-stale cache is rough-but-usable for "scroll near where I am"; it is **not**
  usable as a live seek. FEAT-lyrics-viewer already accepts this (degrades to track-only).
- **Now-playing is a different read path than the streaming token.** The token route is JWT-gated;
  now-playing is edge_guard-only. A position read off the *live* `/v1/me/player` would be a
  JWT-gated, on-demand read (mirroring `getStreamingToken`/`resolve` patterns), **not** the cached
  snapshot — the cleanest way to honor D28.
- **No position → never auto-advance.** Even with a one-shot position, FEAT-lyrics-viewer binds it to
  a single focus init, never to continuous progression (a hard non-goal of the viewer's RFC).

## Items requiring verification

1. ~~**Does the worker now-playing snapshot store a track id (`spotify_track_id` / DB track_id)?**~~
   **Resolved 2026-07-02 (code): no.** `SpotifyNowPlaying` (`models.py:766-785`) stores `track_name`
   + `album_id` but **no track id column**. The lyrics read resolves a track id via the *live*
   `/v1/me/player` `item.id` (spotify_track_id) → catalog `Track.id` (a reverse of the existing
   `PlaybackService.resolve_uri` direct read), not from the cached snapshot. See [Gaps](#gaps--constraints).
2. ~~**Can the streaming token (already scoped for `user-read-playback-state`) read `GET /v1/me/player`
   for position?**~~ **Resolved 2026-07-02 (code): the scope is present, no code calls it, but the
   read path is precedent-setting and rule-#9-clean.** `spotifyPlayback.ts:276` **already** makes a
   direct client-side `fetch('https://api.spotify.com/v1/me/player/play?device_id=…')` with the
   streaming token. A `GET /v1/me/player` (currently-playing) read is the **same pattern** — a
   client-side Spotify *content* call with the JWT-minted token, not a backend proxy. Rule #9 bans a
   *synchronous Spotify call on a user-facing **backend** endpoint*; client-side content calls
   (already done by `requestPlayback`) are the sanctioned path. So no backend content-read proxy is
   needed and no D/RFC decision is required — the position read is a **client-side fetch in the
   viewer/now-playing area on demand**, mirroring `requestPlayback`. What Step 1 still verifies is
   whether a *live* Premium session actually returns `progress_ms` + `item.id` (a runtime probe,
   not a code question). **Runtime probe PASSED 2026-07-02** — see Step 1: `progress_ms` +
   `item.id` + `is_playing` returned on a live session; idle returns 204 (empty).
3. ~~**Is an on-demand live position read acceptable under rule #9?**~~ **Resolved 2026-07-02
   (same as #2):** client-side, mirroring `requestPlayback`'s existing `api.spotify.com` call.
   No backend proxy, no new rule-#9 decision.
4. **Does `NowPlaying` need an explicit "open lyrics" entry, or does it bind to the track-click flow
   from ARCH-frontend-component-map?** Document-only: which surface owns the viewer's open action
   (answers in ARCH-frontend-component-map).

## MVP features to retain / defer

- **Retain (MVP):** current-track identity + is-playing (from `NowPlaying`); active-playback-only
  entry; manual refresh of track identity; degraded-to-track-only when position unavailable.
- **Retain conditionally:** one-shot playback position on refresh — **iff** verification #2/#3
  confirm a clean read path. If not, ship track-only (FEAT-lyrics-viewer's stated degradation) and
  defer position to a follow-on.
- **Defer:** continuous/auto-advancing position (out of scope for the viewer); play/pause/seek/next
  UI in the viewer (owned by the existing ▶ sites + Spotify's own client); multi-listener tokens;
  in-app OAuth/PKCE; non-Premium fallback; queue/context playback.

## Recommended next step (evidence-based)

**Do not open a separate custom playback RFC.** (Confirmed 2026-07-02.)

Evidence: the pieces FEAT-lyrics-viewer needs that **already exist** are track identity +
is-playing (`NowPlaying`) and on-demand play (`requestPlayback`, owner-Premium). The **one missing
piece** is a one-shot position read — and the *capability* for it is already provisioned (the
streaming token carries `user-read-playback-state`) **plus the read path is already precedent**:
`requestPlayback` (`spotifyPlayback.ts:276`) already makes a direct client-side
`fetch('https://api.spotify.com/v1/me/player/play')` with the JWT-minted token. A `GET /v1/me/player`
read is the **same client-side content-call pattern** — rule #9 (no synchronous Spotify call on a
**backend** user-facing endpoint) is not engaged. So the position read is a small client-side fetch
in the now-playing area on demand, not a new product surface and not a backend proxy.

**Concrete next step (verification, not implementation):** resolved 2026-07-02 — the read path is
**client-side** (verification items #1–#3 closed by code: `requestPlayback` already calls
`api.spotify.com` client-side at `spotifyPlayback.ts:276`, so a `GET /v1/me/player` read is the same
rule-#9-sanctioned client-side pattern; `track_id` is obtained from the live response's `item.id`,
not the snapshot). The only remaining check is a **runtime** probe: does a live Premium session's
`GET /v1/me/player` actually return `progress_ms` + `item.id`? That is the one thing code can't
settle without a live owner session — it matches the FEAT-spotify-streaming-playback Step 4 pattern
("owner confirms on a Premium session"). The two remaining outcomes:

- **Live probe returns position (expected — the scope is provisioned and the endpoint is standard)** →
  no custom playback RFC; FEAT-lyrics-viewer's Step 3 binds client-side `/v1/me/player` for one-shot
  position + track id, degrading to track-only if the call fails.
- **Live probe fails / position unusable** → ship FEAT-lyrics-viewer track-only (its stated
  degradation); position waits. Still no custom playback RFC.

A full custom playback RFC (SDK control layer, queue, seek, position tracking) is **not justified**
by the lyrics viewer's needs, which are read-only and one-shot. The recommendation is: verify the
position read, then either reuse it directly or write a **minimal** playback-read step scoped to
now-playing — not a custom playback architecture.

## Risks

- **Assuming position is easy when the read path is unclear.** Mitigation: verification #2/#3 before
  any implementation; degrade-to-track-only is the viewer's stated fallback, so this never blocks MVP.
- **Tier drift — exposing live position on the edge_guard-only now-playing path.** Mitigation: any
  live position read is JWT-gated + on-demand (not on the cached snapshot), mirroring `getStreamingToken`;
  the now-playing vanity read keeps its D28 boundary.
- **Scope creep into a full player.** Mitigation: this research caps the need at read-only one-shot;
  play/seek/queue stay with existing ▶ sites + Spotify's client.
- **Stale position mistaken for live.** Mitigation: one-shot init only (FEAT-lyrics-viewer non-goal:
  continuous progression); the refresh re-reads explicitly.

## Steps

Docs-only research RFC. Hard rule #4 — one step per session.

### Step 0 — RFC + plan.md pointer (this document, docs-only)

This RFC + one-line `plan.md` Backlog pointer + `docs/rfcs/README.md` index entry. No code.

**Verification**: doc review against `TEMPLATE.md` / README required sections. `git diff --stat`
shows only doc files.

---

### Step 1 — runtime position-read probe (research, no code) — **DONE 2026-07-02, probe PASSED**

**Probe result (2026-07-02, live owner Premium session, iPhone device):** smoke JWT →
`GET /api/playback/spotify-token` **200** → client-pattern `GET /v1/me/player` with the
streaming token → **200** with `is_playing: true`, **`progress_ms: 23200`**,
**`item.id: 0TFTAtCYhp2tQ9KcJIZb55`**, `item.duration_ms: 182088`,
`currently_playing_type: track`. (Idle control observed earlier the same session: **204**
empty body — the viewer's "hidden when idle" state maps to exactly this response.)
**Outcome: FEAT-lyrics-viewer Step 3 can bind position** — one-shot focus init via the live
read; track-only degradation stays the documented fallback for 204/failure.

The code questions (#1–#3) are resolved 2026-07-02 (client-side read path; `track_id` via live
`item.id`). Step 1 is now the **single remaining runtime probe**: on a live owner Premium session,
`GET /v1/me/player` with the streaming token returns `progress_ms` + `item.id` (and `is_playing`).
Record the outcome under [Items requiring verification](#items-requiring-verification) + a
Decisions-log row. **No code is written in this step** — it confirms whether FEAT-lyrics-viewer
Step 3 can bind position (expected yes) or ships track-only (its stated degradation).

**Verification**: a Decisions-log row records "live probe: progress_ms + item.id returned" or
"live probe: unavailable → FEAT-lyrics-viewer ships track-only".

**Rollback**: n/a (docs-only; no code committed).

---

## Open questions

1. ~~**Position read path (blocks the recommendation)** — client-side `GET /v1/me/player` vs a
   backend read-proxy.~~ **Resolved 2026-07-02 (code): client-side**, mirroring `requestPlayback`'s
   existing direct `fetch('https://api.spotify.com/v1/me/player/play')` (`spotifyPlayback.ts:276`).
   Rule #9 (no synchronous Spotify call on a **backend** user-facing endpoint) is not engaged — the
   read is a client-side content call with the JWT-minted token, same as the existing play call. No
   backend proxy, no D/RFC decision. Step 1's remaining check is a **runtime** probe (does a live
   Premium session return `progress_ms` + `item.id`?), not a code/feasibility question.
2. ~~**`track_id` on now-playing (blocks FEAT-lyrics-viewer Step 1)**~~ **Resolved 2026-07-02
   (code): no `track_id` column on `SpotifyNowPlaying`.** The lyrics read resolves id via the live
   `/v1/me/player` `item.id` → catalog `Track.id` (reverse of `PlaybackService.resolve_uri`).
3. **Who owns the viewer's open action** — forwarded to ARCH-frontend-component-map (overlay +
   track-click ownership), not this RFC. Resolved there when that RFC's map is published.

## Decisions log

| Date | Decision | Step |
|------|----------|------|
| 2026-07-02 | Research, not implementation — separates capability/gaps/verify/retain/next-step per the task brief | 0 |
| 2026-07-02 | No assumption that custom playback is required — recommendation is evidence-conditional | 0 |
| 2026-07-02 | Not a Spotify feature inventory — scoped to this project's listening/bucket/lyrics flows only | 0 |
| 2026-07-02 | Initial recommendation: no separate custom playback RFC; verify the position read, then reuse or write a minimal playback-read step | 0 |
| 2026-07-02 | OQ1 resolved (code) — position read is client-side `GET /v1/me/player`, mirroring `requestPlayback`'s existing `api.spotify.com` call (`spotifyPlayback.ts:276`); rule #9 (backend-only) not engaged; no backend proxy, no D/RFC decision | 0 |
| 2026-07-02 | OQ2 resolved (code) — `SpotifyNowPlaying` (`models.py:766-785`) has no `track_id` column; lyrics read resolves id via the live `/v1/me/player` `item.id` → `Track.id` (reverse of `PlaybackService.resolve_uri`) | 0 |
| 2026-07-02 | Only remaining check is a runtime probe (live Premium session returns `progress_ms` + `item.id`); matches FEAT-spotify-streaming-playback Step 4 "owner-confirms-on-Premium" pattern | 0 |
| 2026-07-02 | Pre-acceptance review: lyrics endpoint keyed by `spotify_track_id` with server-side resolve → `Track.id` (option (a), one round trip) — recorded in FEAT-lyrics-viewer Step 1 | 0 |
| 2026-07-02 | Status draft → accepted (owner approval in session, post final review) | 0 |
| 2026-07-02 | **Live probe: progress_ms + item.id returned** — `GET /v1/me/player` (streaming token, client-side pattern) → 200 `{is_playing: true, progress_ms: 23200, item.id: 0TFTAtCYhp2tQ9KcJIZb55, duration_ms: 182088}` on a live owner Premium session (iPhone); idle = 204 empty. Final recommendation stands: **no custom playback RFC**; FEAT-lyrics-viewer Step 3 binds the one-shot position read, track-only on 204/failure | 1 |
