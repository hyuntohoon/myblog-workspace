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

### Step 2 — per-member streaming/access token route (backend) — ✅ DONE 2026-07-19 (backend #125)

Generalize `GET /api/playback/spotify-token` → per-member mint (owner path unchanged as a
special case). Fail closed on missing config; guard change lands in backend only (music has no
twin for this route — verify with the cross-repo grep sweep anyway). apigateway.tf already
routes this GET through the authorizer — confirm no new route needed.
**Verification**: member JWT → 200 + token scoped to that member; anonymous → 401; smoke quoted.

**Shipped**: route `require_owner` → `require_cognito_token`; owner sub + local/dev bypass keep
the owner credential path (`playback_service.py` byte-identical to main); other verified subs
mint via new `IntegrationService.mint_member_access_token` — fail-closed gates (KMS key/app
creds/custody → 503 before any outbound call), row-scoped by JWT sub, refresh-token rotation
persisted (worker `_rotated_payload` twin shape), `invalid_grant` → row `status='error'` for
the reconnect banner. Shared `app/core/kms_envelope.py` extracted. No contract change (openapi
byte-identical), no infra change (route pre-existing in apigateway.tf). Music grep: no twin.
Prod smoke: anon 401; member-without-Spotify 503 (pre-merge this sub got 403 = member branch
proven live); full suite 19/19. Member-with-Spotify 200 mint is exercised in Step 3's
real-browser pass (owner decision: no prod member token provisioned to the smoke user).

### Step 3 — player bar UI + Connect remote controls + clock-estimate progress (front) — ✅ DONE 2026-07-19 (front #293)

Rebuild the three variants' internals (keep outer variant structure + Seg). Extract the clock
estimator from LyricsViewer into a shared util (no behavior change to lyrics). Controls call
`PUT /me/player/{play|pause|seek}` client-side with the member token; 403/404 → degrade to
fallback tier (probe model). Fallback tier renders estimate-driven bar from the one-shot.
**Verification**: real-browser click-through (DoD): full-tier member controls an active device;
fallback member sees moving bar, no controls; CDP mobile 390px pass.

**Shipped**: hairline-LCD design (owner pick from 3 mockup directions; the EQ-as-progress
signature option was declined). Estimator extracted to `@lib/clockEstimate`
(`ClockAnchor`/`estimateMs`/`useClockEstimate`); LyricsViewer refactored onto it,
behavior-identical (review-verified). Connect remote via `sendPlayerCommand`
(`@lib/spotifyPlayback`, single 401 re-mint retry); pause freezes the anchor client-side (a
paused player reads as `idle` in the one-shot contract — no confirming read); tier probe per D5
with optimistic controls. Token-route mapping branched per #126: 404 → new `disconnected`
status (quiet fallback), 503 → dormant, 502 → inline reconnect line (bridged over the 502→404
sequence with a sessionStorage flag; fresh sessions rely on the Step 1 integrations-tab
banner). `readLivePlayback` owner gate removed; concurrent mints dedup in-flight. ui-unify
playback plumb executed here (ownership decision): live `artists[]`/album Spotify ids resolve
via new `@lib/spotifyCatalog` (`by-spotify`, promise-cached; `releaseShared` moved onto the
shared resolver) — artist names link only when resolvable, album links light post-resolve.
Reviewer subagent: no blockers. Pre-merge: lint + astro check clean; CDP fetch-mocked
clickthrough 33 asserts PASS (full/degrade/disconnected/reconnect/lyrics + mobile 390, no
horizontal overflow). Prod: deploy run 29682764996 success; markers `np-spotify-reconnect` +
`재생 위치` in `SelfDashboard.*.js`, `position_ms=` in `spotifyPlayback.*.js`; owner real-device
clickthrough confirmed play/pause/seek control an active device + bar sync across all three
variants (2026-07-19).

### Step 4 — 'playing elsewhere' device hint — ✅ DONE 2026-07-20 (front #297)

`GET /me/player` one-shot (with playback-state scope) supplies device name → Connect-style
"Listening on <device>" line in full/banner variants. No polling — refreshed only on the
existing ↻ sync action.

**Shipped**: zero extra requests — the existing one-shot `GET /me/player` body already
carries `device`, so `playback.api.ts` just parses `device.name` into `LivePlayback`,
threaded through `LiveMoment`. New `DeviceHintLine`: faded-mono "Listening on <device>"
line + device glyph in the panel-bottom-edge slot (the Step 3 reconnect-line idiom),
full/banner variants only; list omits it. D28 upheld by construction (name refreshes only
when the one-shot fires: mount / ↻ / seek confirm — verified by call-count assert).
Scope-limited members never see it: their `/me/player` read fails before a live moment
exists — no separate branch. Pre-merge: lint + astro check clean; CDP 18/18 asserts
(banner/full show + list omits, rename-without-sync stays + 0 extra GET, ↻ updates with
exactly 1 GET, pause survives, device-less body omits, disconnected = zero reads, mobile
390 no overflow). Prod: deploy 29721956735; markers `Listening on` + `deviceName` in
`SelfDashboard.*.js`. Owner real-active-device clickthrough pending (Step 3 close-out
pattern).

### Step 5 — in-page SDK device (opt-in output)

Swap `getStreamingToken()` per the seam for members with `streaming` scope; 'Buckit' device
becomes selectable output. Premium-gated by SDK init failure (second capability signal).
**Verification**: SDK connects for a Premium member; non-Premium init failure degrades cleanly.

## Open questions

1. **App mode** — RESOLVED 2026-07-19: owner confirmed **Extended Quota Mode** in the Spotify
   dashboard (checked during BUG-artist-image-backfill closeout). No Dev-Mode 25-user cap;
   rollout is not gated on user-allowlisting.
2. **Seek granularity** — RESOLVED 2026-07-19 (owner): accept 1 extra one-shot read per seek
   (event-driven, D28-compatible — same precedent as end-of-track re-sync). Implementation
   detail: the confirmation read is skipped while paused, since a paused player reads as
   `idle` in the one-shot contract and would collapse the card; the optimistic anchor is
   exact there anyway.
3. **Where the re-consent banner lives** — RESOLVED fully 2026-07-19 (owner): integrations tab
   (Step 1) + inline player line on grant breakage (Step 3): a mint 502 (or a 404 following a
   same-session 502, sessionStorage-bridged) renders a panel-bottom-edge reconnect line
   linking `/settings/` — the same slot idiom Step 4's Connect device hint will use.

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
| 2026-07-19 | OQ1 RESOLVED: owner confirmed **Extended Quota Mode** in the Spotify dashboard — no Dev-Mode 25-user connect cap; rollout not gated on allowlisting | all |
| 2026-07-19 | **Step 2 SHIPPED + prod-smoked** — backend #125. Member mint lives in `IntegrationService` (payload-schema single-owner; avoids playback→integration circular import via extracted `kms_envelope`); member-without-connection → 503 same-detail as dormant (single front handling path); `invalid_grant` flags `status='error'` (reconnect UX seam for Step 3). 550 pytest pass; prod anon 401 / member 503 / suite 19/19. NB: first codex pass timed out mid-refactor and an orphaned executor kept rewriting the worktree — final code hand-completed after kill | 2 |
| 2026-07-19 | **Step 2 follow-up SHIPPED + prod-smoked** — backend #126, a consolidation on top of #125 (two parallel sessions shipped the same step; #125 landed first). Member mint moved to `PlaybackService.mint_member_streaming_token` sharing `_exchange_refresh_token` with the owner path — the refresh-grant exchange exists once (no circular import: playback imports only `kms_envelope`). **Supersedes #125's 503-same-detail choice: member-without-connection → 404 `Spotify not connected`** — a normal member state stays out of 5xx monitoring and Step 3's tier probe can distinguish quiet-fallback (404) from outage (503); front must branch on 404 vs 503 accordingly. `invalid_grant` row-flagging kept (`PlaybackGrantRevokedError`, still 502; next mint 404s). openapi no diff. 550 pytest pass; prod: suite 19/19, anon 401, member 404 | 2 |
| 2026-07-19 | Step 3 design: owner picked **direction A "hairline LCD"** from 3 mockup directions (A hairline / B 3-zone transport / C EQ-as-progress signature) — quietest delta from the existing card; banner keeps its decorative 32-bar equalizer. Narrow banners hoist the transport below the identity row (full card width) for a usable touch seek surface | 3 |
| 2026-07-19 | OQ2 accepted (1 confirmation read per seek, skipped while paused) + OQ3 fully resolved (inline reconnect line on 502, sessionStorage-bridged over the 502→404 sequence; fresh sessions covered by the integrations-tab banner only) — see Open questions | 3 |
| 2026-07-19 | ui-unify NowPlaying plumb executed in this stream per the file-ownership decision: `LivePlayback` now carries `artists[{id,name}]` + `albumSpotifyId`; catalog resolution via new `@lib/spotifyCatalog` (`artists|albums/by-spotify`, promise-cached, no contract change — endpoints pre-existed). Lyrics-header artist links remain with RFC-ui-surface-unification Step 4 | 3 |
| 2026-07-19 | **Step 3 SHIPPED + prod-smoked** — front #293 (+ review-nit follow-up in-PR). Hairline transport across banner/full/list; Connect remote `sendPlayerCommand`; 403-probe degrade + toast; fallback estimate bar; `disconnected` token status (404 branch per #126); owner gate removed. CDP 33 asserts + mobile 390 PASS pre-merge; prod deploy 29682764996, bundle markers live, **owner real-device clickthrough: play/pause/seek control an active device, bar syncs, all 3 variants** | 3 |
| 2026-07-20 | **Step 4 SHIPPED + prod-smoked** — front #297. Device hint costs zero extra requests (the `device` object rides the existing one-shot `GET /me/player` body); `DeviceHintLine` in the panel-bottom-edge slot, full/banner only; D28 by construction (call-count asserted: rename without ↻ = 0 extra GETs). CDP 18/18 + mobile 390 PASS; prod markers `Listening on`/`deviceName` in `SelfDashboard.*.js`. Owner real-active-device line check pending. Remaining scope = Step 5 only | 4 |
