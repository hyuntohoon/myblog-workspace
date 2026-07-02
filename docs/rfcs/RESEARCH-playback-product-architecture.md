# RESEARCH-playback-product-architecture: Playback product strategy

- **Status**: draft
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
  authenticated lyrics endpoint; `NowPlaying` carries `album_id` but not `track_id`. **Verify**
  whether the worker snapshot stores the playing track's id and whether exposing it is acceptable
  (it would not raise the now-playing read's tier unless it leaked non-public fields).
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

1. **Does the worker now-playing snapshot store a track id (`spotify_track_id` / DB track_id)?**
   Read `worker/service/listening_sync_service.py` + the snapshot table. If absent, lyrics lookup
   must resolve id another way.
2. **Can the streaming token (already scoped for `user-read-playback-state`) read `GET /v1/me/player`
   for position?** The scope is present per FEAT-spotify-streaming-playback OQ3, but **no code
   calls it** — verify the endpoint returns `progress_ms` + `item.id` for an active Premium session,
   and that a JWT-gated read mirrors `getStreamingToken`/`resolve` cleanly (cache briefly, fail
   soft). This is the core open question; it determines whether position is "small UI/state work"
   or "a new read path."
3. **Is an on-demand live position read acceptable under rule #9?** Rule #9 bans a *synchronous
   Spotify call on a user-facing endpoint*. The existing token mint and `/resolve` are the blessed
   async exception (server-side auth mint, client-side content). A `GET /v1/me/player` read is a
   *content* read — it must be client-side (front fetches spotify.com directly with the streaming
   token, like `requestPlayback` already does for `PUT /me/player/play`), or it needs an explicit
   D/RFC decision if proxied through the backend. **Verify the intended read path.**
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

**Do not open a separate custom playback RFC yet.**

Evidence: the pieces FEAT-lyrics-viewer needs that **already exist** are track identity +
is-playing (`NowPlaying`) and on-demand play (`requestPlayback`, owner-Premium). The **one missing
piece** is a one-shot position read — and the *capability* for it is already provisioned (the
streaming token carries `user-read-playback-state`; it is just uncalled). The work to expose a
one-shot position is a **small read path** (client-side `GET /v1/me/player` with the streaming
token, mirroring how `requestPlayback` already calls `PUT /me/player/play` client-side — so it
stays rule-#9-safe), bounded to the now-playing area, not a new product surface.

**Concrete next step (verification, not implementation):** resolve verification items #2 and #3 —
probe `GET /v1/me/player` with the owner's streaming token on an active Premium session to confirm
it returns `progress_ms` + `item.id`, and confirm the client-side read path honors rule #9
(content reads go client-side, like the existing play call). Three outcomes:

- **Position read works client-side (expected)** → no custom playback RFC; the position contract for
  FEAT-lyrics-viewer is "front calls `/v1/me/player` on-demand on a manual refresh; degrades to
  track-only if the call fails." FEAT-lyrics-viewer's Step 3 binds directly.
- **Position read needs a backend proxy** → a narrow playback-read RFC (JWT-gated
  `GET /api/playback/now-playing-live`, mirroring the `spotify-token`/`resolve` patterns), **not** a
  full custom playback RFC. Smaller than FEAT-spotify-streaming-playback.
- **Position read proves infeasible / out of scope** → ship FEAT-lyrics-viewer track-only (its stated
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

### Step 1 — resolve the position-read verification (research, no code unless minimal)

Probe `GET /v1/me/player` with the owner's streaming token on an active Premium session; confirm
the return of `progress_ms` + `item.id` and the rule-#9-clean read path (client-side, mirroring
`requestPlayback`). Record the outcome under [Items requiring verification](#items-requiring-verification)
+ a Decisions-log row. **No code is written in this step** — it produces the evidence that selects
one of the three recommendation branches. A subsequent implementation (if any) is a **separate**
RFC/step, scoped minimally to a now-playing read.

**Verification**: the verification table above is updated with confirmed/confirmed-not for #2, #3
(+ #1, #4 where code confirms); the recommended-next-step branch is recorded as decided or
marked "still blocked on #X".

**Rollback**: n/a (docs-only; no code committed).

---

## Open questions

1. **Position read path (blocks the recommendation)** — client-side `GET /v1/me/player` vs a
   backend read-proxy. Resolved by Step 1 verification.
2. **`track_id` on now-playing (blocks FEAT-lyrics-viewer Step 1)** — whether the snapshot stores
   the playing track's DB id and can expose it without raising the read's tier. Resolve in Step 1
   code read.
3. **Who owns the viewer's open action** — forwarded to ARCH-frontend-component-map (overlay +
   track-click ownership), not this RFC.

## Decisions log

| Date | Decision | Step |
|------|----------|------|
| 2026-07-02 | Research, not implementation — separates capability/gaps/verify/retain/next-step per the task brief | 0 |
| 2026-07-02 | No assumption that custom playback is required — recommendation is evidence-conditional | 0 |
| 2026-07-02 | Not a Spotify feature inventory — scoped to this project's listening/bucket/lyrics flows only | 0 |
| 2026-07-02 | Initial recommendation: no separate custom playback RFC; verify the position read, then reuse or write a minimal playback-read step | 0 |
