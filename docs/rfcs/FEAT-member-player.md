# FEAT-member-player: rebuild '지금 듣는 음악' as a real player bar (capability-tiered controls)

- **Status**: in-progress
- **Owner**: 박지훈
- **Created**: 2026-07-18
- **Plan row**: `plan.md` → FEAT-member-player
- **Origin**: 2026-07-18 UI planning session, area 2. Pre-resolved owner decision **D1**.
- **Repeals**: **D11** (read-only, no playback control — FEAT-nowplaying-live-sync). D1
  supersedes it: members whose own Spotify account supports it get real controls; everyone else
  gets a visual-only estimated progress bar. **D28 (no polling / one-shot sync) stays in force.**

---

## Goal

The profile-overview '지금 듣는 음악' surface looks and works like a real player bar in all three
variants (banner / full / list): cover + title/artist + progress bar with elapsed/total times +
state indicator. **Full tier** (signed-in member, own Spotify connected, Premium, granted
scopes): working play/pause/seek against the member's active device (Spotify Connect remote), and
— as a second phase — an optional in-page Web Playback SDK device. **Fallback tier** (everyone
else): visual-only progress driven by the lyrics viewer's clock-estimate technique. No polling
anywhere; control calls are client-side with the user's token (CLAUDE.md rule 9).

## Non-goals

- Queue, volume, shuffle/repeat controls (drop-order research says these go first in compact
  bars anyway; the surface is a bar, not a full player page).
- Server-side progress storage or polling loops (D28 upheld; snapshot schema comment
  `myblog_backend/.../schemas.py:608-611` stays true).
- Any synchronous Spotify call from a user-facing backend endpoint (rule 9).
- Lyrics viewer changes (FEAT-lyrics-viewer-controls) beyond sharing the estimator util.

## Current state (verified 2026-07-18)

- `myblog_front/src/components/member/NowPlaying.tsx` (512 L): variants at :412 (banner) /
  :322 (full) / :354 (list); host `OverviewDash.tsx:483` + `Seg` selector :673; pref state
  `SelfDashboard.tsx:123`. Wrapper-owned `useNowPlaying()` :132-200 — two parallel one-shots on
  mount: `GET /api/library/now-playing` (worker-fed, ≤1h stale, **no progress fields**) +
  `readLivePlayback()` (has `progressMs/readAtMs/durationMs` but is **owner-gated**,
  `playback.api.ts:57-59`). `↻` re-fires the live read.
- Member OAuth scopes (`integrations.api.ts:55`): `user-read-currently-playing
  user-read-recently-played` — no playback-state read, no modify, no streaming.
- `GET /api/playback/spotify-token` (`playback.py:33`) is `require_owner`; front seam
  `spotifyPlayback.ts` `getStreamingToken()` :70 is the designed single swap point ("FUTURE: a
  per-listener variant swaps only this function body"). SDK path: `requestPlayback` :242,
  device 'Buckit' :177, control via client-side `PUT v1/me/player/play`.
- Clock-estimate reference: `LyricsViewer.tsx:25-50` (`estimatedMs = anchorMs +
  (performance.now() − wallMs)`), `applyAnchor` :277-289.
- **Spotify 2026-02 changes verified** (migration guide + changelog, fetched 2026-07-18):
  player endpoints (`PUT /me/player/play|pause|seek`, `GET /me/player`, `currently-playing`)
  are **not** in the removal list. Dev-Mode apps lose `GET /me`'s `product` field (and batch
  endpoints); empirically our app is unaffected as of 2026-07-18 (⇒ likely Extended Quota
  Mode — owner to confirm, OQ1).

## Target state

- **Capability tiers** (D1): resolved per session, per user.
  - *Full*: play/pause/seek work. Mechanism (owner decision 4, 2026-07-18): **both** — Step 3
    ships Spotify-Connect remote control of the member's active device (`PUT /me/player/*`, no
    SDK download, fits the "what you're playing elsewhere" surface; "playing on <device>" hint
    shown Connect-style); Step 5 adds the in-page SDK device as an opt-in output target.
  - *Fallback*: progress bar advances by clock estimate from the freshest one-shot
    (`progress_ms` via `user-read-currently-playing`, which members already grant); controls
    hidden (not disabled-greyed).
- **Capability detection** (owner decision 5): **403-probe based, no `product` dependency** —
  optimistic controls for connected members with the new scopes; first control call returning
  403 (Premium required / scope missing) or 404 (no active device) degrades the session to
  fallback tier with a small toast. Survives Dev-Mode field removals by construction.
- **Scopes**: member connect adds `user-read-playback-state user-modify-playback-state`
  (+ `streaming` only at Step 5). Existing connected members see a re-consent banner on the
  integrations tab; write path = standard re-authorize, new refresh token stored (KMS-enveloped,
  as today).
- **Token plumbing**: `/api/playback/spotify-token` generalized per-member (mints a short-lived
  access token from *that member's* refresh token; `require_cognito_token` + row-scoped);
  `getStreamingToken()` body swapped per the seam; `readLivePlayback()` owner gate removed.
- **Layout**: 2–3 mockups per variant at implementation time (frontend-design skill), grounded
  in the researched anatomy below.

### Design references (UX research, 2026-07-18 — folded in on promotion)

- **Spotify bar anatomy**: left = identity (cover ~56px + title/artist), center = transport
  (circular play button + progress bar), right = utilities.
- **Apple Music**: single centered "LCD" block integrating identity + progress.
- **Miniaturization drop order**: progress bar → prev/next → everything else; the last
  survivors are cover + title + play.
- **Connect hint**: "Listening on <device>" banner along the bar's bottom edge
  (Spotify Connect idiom) — model for Step 4's device line.

## Steps

### Step 1 — scopes + re-consent (backend + front integrations tab)

Add the two read/modify scopes to `SPOTIFY_SCOPES`; integrations tab shows "재연동 필요" for
members whose stored grant lacks them (store granted-scope string server-side if not already).
**Verification**: re-connect flow grants union; old token path still works for not-yet-reconsented
members (fallback tier).

### Step 2 — per-member streaming/access token route (backend)

Generalize `GET /api/playback/spotify-token` → per-member mint (owner path unchanged as a
special case). Fail closed on missing config; guard change lands in backend only (music has no
twin for this route — verify with the cross-repo grep sweep anyway). apigateway.tf already
routes this GET through the authorizer — confirm no new route needed.
**Verification**: member JWT → 200 + token scoped to that member; anonymous → 401; smoke quoted.

### Step 3 — player bar UI + Connect remote controls + clock-estimate progress (front)

Rebuild the three variants' internals (keep outer variant structure + Seg). Extract the clock
estimator from LyricsViewer into a shared util (no behavior change to lyrics). Controls call
`PUT /me/player/{play|pause|seek}` client-side with the member token; 403/404 → degrade to
fallback tier (probe model). Fallback tier renders estimate-driven bar from the one-shot.
**Verification**: real-browser click-through (DoD): full-tier member controls an active device;
fallback member sees moving bar, no controls; CDP mobile 390px pass.

### Step 4 — 'playing elsewhere' device hint

`GET /me/player` one-shot (with playback-state scope) supplies device name → Connect-style
"Listening on <device>" line in full/banner variants. No polling — refreshed only on the
existing ↻ sync action.

### Step 5 — in-page SDK device (opt-in output)

Swap `getStreamingToken()` per the seam for members with `streaming` scope; 'Buckit' device
becomes selectable output. Premium-gated by SDK init failure (second capability signal).
**Verification**: SDK connects for a Premium member; non-Premium init failure degrades cleanly.

## Open questions

1. **App mode** (owner, Spotify dashboard) — Extended Quota vs Dev Mode. Dev Mode would (a)
   eventually break nothing in this RFC's player calls (unaffected) but (b) matters for the
   25-user cap on who can connect at all. Blocks nothing; informs rollout.
2. **Seek granularity in fallback→full transition** — after a seek, re-anchor from the PUT
   response (no body) requires a follow-up one-shot read; accept 1 extra read per seek?
   Blocks Step 3 detail only.
3. **Where the re-consent banner lives** (integrations tab only vs also inline on the player) —
   Step 1 detail.

## Decisions log

| Date | Decision | Step |
|------|----------|------|
| 2026-07-18 | D1 (owner, pre-session): capability-tiered controls; D11 repealed, D28 upheld | all |
| 2026-07-18 | Owner: both Connect remote AND SDK device in this RFC, phased | 3, 5 |
| 2026-07-18 | Owner: 403-probe capability detection, no `product` dependency | 3 |
| 2026-07-19 | Owner: Status draft → in-progress approved; Step 1 started | 1 |
| 2026-07-19 | File ownership: `NowPlaying.tsx` / `playback.api.ts` / `spotifyPlayback.ts` / `LyricsOpenTarget` are owned by this stream — RFC-ui-surface-unification's NowPlaying items (album `openAlbum` click-through + `artists[].id` plumbing) will be executed here in later steps, not in that stream | 3+ |
| 2026-07-19 | Step 1: granted-scope string was already stored in `payload` since 3b-c → exposed read-only as `scope` on `GET /api/integrations` rows (spotify only; ciphertext still never serializes). OQ3 resolved minimally: re-consent banner lives on the integrations tab only for now; player-inline surfacing deferred to Step 3 | 1 |
| 2026-07-19 | **Step 1 SHIPPED + prod-smoked** — backend #124, front #287, ws #644 (contract). Prod: full smoke 19/19, `/api/integrations` member 200 / anon 401, new bundle live with both playback scopes. Verified pre-merge by 3-scenario real-browser clickthrough (authorize URL carries the 4-scope union). Security review: no findings | 1 |
