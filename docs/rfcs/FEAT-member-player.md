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
### Measured 2026-08-02 (app + owner token, not docs or dashboard)

Probed with a client-credentials token and with tokens minted from the stored refresh tokens
in SSM `/myblog/spotify`. Recipe kept so this is re-runnable, not a one-time claim.

- **We are in Extended Quota Mode — measured, 6/6.** Every capability the Feb/Mar 2026
  Development-Mode change removed still answers 200: `search?limit=50` (returns 50, Dev caps
  at 10), batch `/albums` `/artists` `/tracks`, `popularity` + `available_markets` fields,
  `/browse/new-releases`, `/artists/{id}/top-tracks`. Existing Dev-Mode apps were force-migrated
  2026-03-09, so this is a post-migration observation. ⇒ **unlimited users, no allowlist; a
  growing user base never needs a second app registration** (owner question, 2026-08-02).
- **That grant is irreplaceable.** Since 2025-05-15 only registered organizations with ≥250k
  MAU may request extended access — individuals cannot apply at all. A newly registered app
  today would be Development Mode permanently, which would break *already-shipped* features:
  the music/worker catalog sync uses the batch endpoints and library sync + the 6d heart use
  `/me/tracks` `/me/albums` `/me/following`, all of which Dev Mode removed.
- **The owner's stored grant already contains `streaming`** (full set: `streaming
  user-modify-playback-state user-read-playback-state user-read-currently-playing
  user-read-recently-played user-library-read user-library-modify user-follow-read`; both
  `refresh_token` and `streaming_refresh_token` carry it). ⇒ Step 5 needs **no re-consent**.
  `/me/player/devices` and `/me/player/queue` both read 200 today.
- **Not grandfathered into the 2024-11-27 deprecations** — measured dead for us too:
  Recommendations, available-genre-seeds, **Audio Features**, Audio Analysis, Related Artists,
  Featured Playlists, `preview_url` (null). No feature may be planned on derived mood/energy
  or "similar artists"; `popularity` (already stored) is the only quantitative signal left.
- **`user-top-read` is alive but ungranted** (403 = missing scope, not 404 = removed) → "가장
  많이 들은 아티스트/곡". Not a player feature — recorded as a cross-RFC candidate below.
- **Prod reality check**: 4 users, **1** Spotify integration (the owner). The member mint path
  built in Steps 1–2 has never been exercised by a second account.

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

### User-situation capability matrix (added 2026-07-20, owner request)

The Full/Fallback pair above is the *engineering* tier model; real member situations are
finer. This matrix is the canonical map of **which features apply to whom** — every new
player feature (Step 5/6/7 included) must add a column or amend rows here in the same PR.
Row behavior asserted at design level; re-verified 2026-07-21 for the shipped S6a/S6d columns
via the #302 CDP fixture matrix (free-account row: transport 403 degrade + heart survives;
구스코프 row: library read 403 → 재동의 link heart). S6b rides the S6a-c/e column. S5 and the
unshipped 6c/6e remain design-level.

| 상황 | snapshot 표시 | live 바 (one-shot+estimate) | 재생/일시정지/seek | device hint | 가사 live 진입 | S5 in-page 기기 | S6a-c/e 컨트롤 | S6d 좋아요 |
|------|--------------|---------------------------|-------------------|-------------|---------------|-----------------|----------------|-----------|
| 멤버, 연동 없음 | — (idle) | — (`disconnected` quiet fallback) | — | — | — | — | — | — |
| 멤버, **Last.fm만** | ✅ (worker poll 경유, 표시 전용) | — (Spotify 토큰 없음) | — | — | — (Spotify track id 없음) | — | — | — |
| 멤버, Spotify **구스코프** (Step 1 재동의 전) | ✅ | ✅ (`currently-playing`은 구grant에 포함) | — | — (`playback-state` 필요) | ✅ | — | — | — |
| 멤버, Spotify 신스코프 + **무료** | ✅ | ✅ | — (403-probe → fallback) | ✅ (읽기 scope, 무료 OK) | ✅ | — (SDK init 실패) | — (Premium) | ✅ (**무료 가능**) |
| 멤버, Spotify 신스코프 + **Premium** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ (opt-in) | ✅ | ✅ |
| 방문자 (남의 공개 멤버 페이지) | ✅ 공개 now-playing strip (`via Last.fm/Spotify` provenance)만 | — | — | — | — | — | — | — |

**Amendment 2026-08-02 (Step 5 reframe).** The `S5 in-page 기기` column narrows to
**owner-only at ship time** — every member row reads `—` until the `streaming` scope is opened
(see Step 5 scope). Two further columns are implied by the Step 5 ladder and apply to the same
rows as `S6a-c/e`: **기기 선택기** (needs `user-read-playback-state`, so 구스코프 row = `—`,
free + Premium rows = ✅) and **콜드 스타트 재생** (rung 2 is Premium-only, so the free row
stays `—` and keeps only rung 1's "활성 기기가 있을 때"). The matrix is not rewritten here
because the shipped columns are unchanged; the implementing PR must fold these in properly.

Key asymmetries worth stating to users (Step 7 surfaces them): **좋아요(6d)는 무료 계정도
됨**, 컨트롤(재생 조작)은 Premium 전용; **device hint는 무료도 됨** (Premium이 아니라 scope
문제); Last.fm 연동은 표시 전용 (라이브 바·가사·컨트롤은 전부 Spotify 연동 필요); 구스코프
멤버는 재동의 한 번으로 무료여도 device hint까지 올라옴.

### Step 7 (candidate) — capability transparency — 7a PROMOTED + ✅ SHIPPED 2026-07-21 (front #302); 7b/7c stay candidates

Recorded 2026-07-20 (owner: "언젠가 설정이나 설명서를 통해 알 수 있도록, 기능 상으로도 확인
및 추가할 수 있도록"). Today the only capability feedback is the degrade toast + reconnect
banner — a member has no way to learn *why* controls are missing or *what a re-consent /
Premium / Spotify connect would unlock*. Scope when promoted (owner picks the subset):

- **7a 연동 tab 기능 안내** — per-provider "이 연동으로 열리는 기능" list on the integrations
  tab, driven by the matrix above; shows the member's CURRENT standing (connected / scope
  generation / last probe outcome) and what the next action (연동/재동의) would add. Server
  already stores the granted-scope string (Step 1) and token status; probe outcome is
  session-local — persist last-known tier client-side only (no new contract).
- **7b 플레이어 인라인 안내** — the fallback-tier bar gets a quiet "왜 컨트롤이 없나요?"
  affordance (tooltip/popover reusing the matrix rows relevant to the member's situation),
  replacing the one-shot degrade toast as the durable explanation.
- **7c 설명서 페이지** — a static help page (e.g. `/help/player` or a 설정 내 섹션) rendering
  the user-facing version of the matrix; the RFC matrix is the single source — regenerate the
  page content from it when either changes.

**Verification (whichever subset ships)**: per-situation CDP fixture matrix (each row of the
capability table = one mocked session, assert the announced feature set matches); 설명서
content diffed against the RFC matrix in review.

**7a shipped (front #302)**: "이 연동으로 열리는 기능" guide on both integration surfaces
(설정 panel + dashboard 연동 tab), matrix-driven, with current standing = connected state +
scope generation derived from the stored grant string (`none/legacy/playback/library` via new
`spotifyScopeGeneration`) + last probe outcome persisted client-side only (sessionStorage
`myblog:spotify-capability-v1`, written at the existing 403-probe sites; no contract change).
Last.fm row marked 표시 전용. Note: the dashboard 연동 tab was re-sourced from the member
integrations contract — its old data source (`GET /api/library/spotify-connection`) is the
owner-only D27 surface, dead for members. CDP: 3 scope-generation fixtures asserted (part of
the 37/37 matrix).

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

### Step 2 — per-member streaming/access token route (backend) — ✅ DONE 2026-07-19 (backend #125 + #126 follow-up)

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

> **NB (superseded same day by #126 — see Decisions log):** the consolidation follow-up moved
> the member mint into `PlaybackService.mint_member_streaming_token` and remapped
> member-without-connection **503 → 404** (`Spotify not connected`), so the front branches
> quiet-fallback (404) vs outage (503). The paragraph above records #125 as shipped.

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
`SelfDashboard.*.js`. Owner real-active-device clickthrough CONFIRMED 2026-07-20 ("2번
동작한다") — Step 4 fully closed.

### Step 5 — play from the site (unified play ladder + device picker) — REFRAMED 2026-08-02 · ✅ SHIPPED + prod-verified 2026-08-02 (front #334, `9df4c7a`, deploy 30740995167)

> **Shipped 2026-08-02** — front #334, squash `9df4c7a`. `play(intent)` replaces `requestPlayback` + `sendConnectPlay`;
> all six surfaces call only it. Device picker rides the Step 4 device line. Media Session bound on
> rung 2 only. Persistence via the `astro:before-swap` override the OQ4 measurement pointed to.
> Verification below; the owner's real-device items are still open.
>
> **The implementation insight, recorded because it changed the work's size**: the two paths differed
> by *exactly one query parameter*. Both PUT the same body to `/v1/me/player/play`; only `device_id`
> differs. So the ladder is not a merge of two subsystems — it is one request with a fallback on that
> parameter, which is why rung selection could stay attempt-then-fallback (the 404 the old path already
> returned *is* the signal) rather than a `GET /me/player/devices` probe. One request on the happy
> path; D28 holds by construction.

The draft framed this as "add an in-page SDK device as an opt-in output". That framing was
wrong twice over: the SDK device **already exists and already plays** (`requestPlayback`,
FEAT-spotify-streaming-playback, done 2026-06-25), and the actual defect is not a missing
output — it is that **the site has two unrelated play paths and the newer one cannot cold
start**.

**The defect, stated precisely.** Six surfaces start playback, split by build date, not design:

| Path | Surfaces | Cold start (nothing playing anywhere) |
|------|----------|----------------------------------------|
| SDK — `requestPlayback()`, sends `device_id` | Pocket tray ▶, review tracklist ▶ | ✅ works |
| Connect remote — `sendConnectPlay()` / `sendPlayerCommand()`, deliberately omits `device_id` | album overlay "이 앨범 재생", bucket row, player-bar transport, lyrics-viewer track jump | ❌ 404 `no-active-device` |

Everything the owner actually uses is on the second row. Hence "재생 시작이 안 된다".

**Target — one `play(target)` ladder, every surface calls only it** (owner, 2026-08-02):

1. active Connect device exists → **remote-control it** (default; see audio-quality note below)
2. none → **raise this tab as the 'Buckit' device** and play there, with a quiet
   "이 브라우저에서 재생 중 (음질 제한)" marker
3. not Premium → no playback; notice + "Spotify에서 열기"

Plus, in the same step:

- **Device picker** (owner: "스포티파이처럼 클릭을 통해서 변경") — `GET /v1/me/player/devices`
  + `PUT /v1/me/player` transfer, the in-page 'Buckit' device listed alongside real ones.
  **Pulled out of the 6e candidate bundle**; the rest of 6e (shuffle/repeat/volume) stays a
  candidate.
- **Media Session API** — once this tab emits audio it must own the OS media keys, lock
  screen and headset buttons, or the sound has no visible source. Not optional decoration.
- **Global persistence** — playback must survive navigation (owner: "전역으로 할 수 있게
  해야만 해"). See the ClientRouter note in Current state and OQ4.

**Scope: owner-only** (owner, 2026-08-02). Measured that day: the owner's stored grant
already carries `streaming`, so this ships with **zero re-consent**. The member path is built
but its scope stays closed — prod has 4 users and exactly **1** Spotify integration (the
owner), so shipping the member tier now would deploy an unverifiable feature. Opening it later
is a scope-string change plus the Step 1 banner idiom; the `getStreamingToken()` seam already
absorbs the difference.

**Audio quality is why "remote first" is correct, not just a preference** (researched
2026-08-02). The Web Playback SDK is capped at **AAC 256 kbps**; Spotify Lossless (2025-09,
24-bit/44.1 kHz FLAC) is native-app/Connect-device only and explicitly excluded from the web
player. Remote-controlling a real device therefore costs **zero** audio quality, while the
in-page device always costs some. Rung 2 is a fallback, not a peer — and the UI should say so.

**Verification**: real-browser clickthrough with nothing playing anywhere (the case that 404s
today) on every one of the six surfaces; device picker switches output both directions;
navigate across ≥3 pages mid-playback without a gap; OS media keys drive the in-page device;
CDP mobile 390 pass.

**Verification actually run (2026-08-02, front #334)** — split by what a session can and cannot
reach, because most of this list needs a Premium account that only the owner has.

Machine-checkable, all green: `pnpm lint` clean · `astro check` **0 errors** · `pnpm test`
**173 passed** (12 new) · `pnpm build` 2143 pages. The 12 new tests pin the three properties that
would let this regress silently — the 404 is a **hand-off** not a dead end; the two rungs send an
**identical body** and differ by `device_id` alone; and a play that cannot possibly sound
(visitor / dormant 503 / unresolvable) **never downloads the ~1 MB SDK**.

Real browser (CDP, local dev server) — aimed at the piece with the widest blast radius, the swap
override: audio host **ALIVE across 3 hops**, all **6 persisted islands** intact, **0 duplicate
head scripts**, the mobile drawer still interactive *after* an override-driven swap (the
script-re-execution risk), the inert path unchanged, no console errors.

**Prod smoke (2026-08-02, after deploy 30740995167)**: the old dead-end string `재생 중인 Spotify 기기가 없어요` is **gone** from the live `AlbumOverlay` chunk — the message only existed because a cold start had nowhere to go, so its absence is the behavior change. The override was re-run against prod itself, on the same page that destroyed the iframe that morning: audio **ALIVE across 3 hops**, 6/6 persisted islands, no console errors. Inert path re-checked on prod too — correct page, 6 islands, header script still interactive, no duplicated head scripts.

**Still open — owner, real device**: cold-start play on each of the six surfaces; device switching
both directions; OS media keys driving the in-page device; CDP mobile 390 on the picker. These need
a live Premium session and a second Connect device, so no session can close them. ⚠️ Until the
first item is checked, "재생 시작이 안 된다" is fixed *in test*, not *in use*.

#### OQ4 measurement — the SDK iframe and `ClientRouter` (prod, 2026-08-02)

Run before any UI work, as the OQ demanded. CDP against **prod** (`www.ratemymusic.blog`), the
site's real `ClientRouter`, the real `https://sdk.scdn.co/spotify-player.js`. No prod state was
written. Same-origin probe iframes were stamped with a value on their `contentWindow` so the
measurement distinguishes **the node surviving** from **the browsing context surviving** — the
distinction the whole question turns on. For the cross-origin SDK iframe, a re-fired `load`
event plus a `MutationObserver` detach count stand in for the stamp.

| # | What was measured | Result |
|---|---|---|
| 1 | SDK iframe after one navigation (today's behavior) | **destroyed.** `sdk.scdn.co/embedded/index.html` is appended straight to `<body>`; after a `/` → `/reviews/` hop there are **0** SDK iframes. `window.Spotify` and module state survive — the JS context was never the problem. |
| 2 | The presumed fix: `data-astro-transition-persist` on the injected iframe | **refuted — NODE GONE.** Persist matches an element against a **counterpart in the incoming document**; a runtime-injected node has none, so it is dropped outright. |
| 3 | The iframe placed *inside* a genuinely persisted island (`pocket-buckit`) | **refuted again, and more sharply.** The host survived as the *same node object* (`hostIsSameNode: true`) and the iframe inside it still came back **RELOADED**. |
| 4 | Control: moving an iframe within one document | **RELOADED.** Re-insertion destroys the browsing context — this is the root cause, not anything Astro-specific. |
| 5 | Candidate fix: `astro:before-swap` override that mutates `<body>` in place | **ALIVE (context kept).** |
| 6 | Same override with the **real SDK iframe**, 3 consecutive hops | **0 reloads, 0 detach events, same node** across `/` → `/reviews/` → `/genres/` → `/releases/`. |

**Why persist cannot work here** — read from `astro/dist/transitions/swap-functions.js`:
`swapBodyElement` does `oldElement.replaceWith(newElement)` and then, for each persisted element,
`newEl.replaceWith(el)`. Both are re-insertions. Astro preserves *node identity* by design; the
HTML spec destroys an iframe's browsing context on re-insertion regardless. The two guarantees
are simply different things, and audio needs the one Astro does not offer.

**The path that works.** `swapFunctions` is a public export of `astro:transitions/client`
(verified in Astro 5.15.9 — `vite-plugin-transitions.js` re-exports it from the virtual module),
so the override composes the official `deselectScripts` / `swapRootAttributes` /
`swapHeadElements` / `saveFocus` and replaces only `swapBodyElement` with an in-place variant
that never detaches the audio host. **The prototype above is not shippable as written**: it
replaced `<head>` wholesale and skipped script de-duplication, which would re-execute page
scripts. The shipped version must reuse Astro's own head/script handling and override the body
step alone.

**What this costs.** The override sits in `layout.astro` and changes how **every** navigation on
the site swaps — a wider blast radius than the ladder itself. Whatever else Step 5 gets sliced
into, this piece needs its own regression pass over the persisted islands (`PocketBuckit`,
`AlbumOverlay`, the four header roots) and over `astro:page-load` consumers.

**One consequence worth stating plainly**: this whole problem belongs to **rung 2 only**. When
rung 1 remote-controls a real Connect device, the audio is not in the tab at all, so it is
global for free. Persistence is the price of the fallback, not of the feature.

### Step 5b — `/write` layout refactor (playback follows into the editor) — ✅ SHIPPED + prod-verified 2026-08-02 (front #335, `8e82d74`, deploy 30742211114)

`write-layout.astro` is 35 lines used by exactly one page and carries **no `ClientRouter`, no
header/footer, no PocketBuckit, no AlbumOverlay, no PWA chrome** — it is an island detached
from the site shell. Any navigation between it and `layout.astro` is a full document load, so
Step 5's persistence stops at the editor door. Owner approved refactoring it (2026-08-02:
"수정을 하자 … 가장 오래된 기능이기도 하니까").

Split from Step 5 deliberately: this changes the lifecycle of a 16-component editor island,
and folding it in would make "the sound stopped" ambiguous between the SDK and the editor.

Scope: add `ClientRouter`, mount the persisted player shell, reconcile the two layouts' `head`
and body structure. **Named risk**: `/write` holds unsaved prose and has **no `beforeunload`
guard today** (grep-verified) — client-side routing changes what "navigating away" means, so
an `astro:before-preparation` guard is part of this step, not a follow-up.

**Verification**: playback continues across `/write` ↔ site in both directions; an in-progress
draft survives (or blocks) a client-side navigation; writer suite + real-browser pass.

#### What the implementation corrected (2026-08-02, front #335)

**The "named risk" above is half right, and the wrong half is the dangerous one.** `/write`
genuinely has no `beforeunload` guard — but it was never exposed, because **`pagehide` already
flushed the draft to localStorage**. The actual hazard runs the other way: client-side routing
**does not fire `pagehide`**, so the island unmounts and the in-memory draft goes with it. Step 5b
would have *introduced* the data loss it was written to prevent.

And the fix is not the guard the RFC imagined. Flushing on `astro:before-preparation` restores the
existing guarantee exactly — nothing is lost, so there is nothing to warn about, and no confirm
dialog belongs in the path. Measured: typed prose **absent** from localStorage (214 B) → navigate
away client-side → **present** (245 B), with the island confirmed unmounted and the 30 s autosave
nowhere near firing, so the flush is the only thing that could have written it. Navigating back
restored the text into the editor.

**A second hazard the RFC did not name at all: the `/write` login gate would have been bypassed.**
`write.guard.ts` is a page script, and Astro's `deselectScripts` marks a script already-executed
*by src* — so it runs on a fresh load and **never again**, letting a second client-side arrival at
`/write` through. `data-astro-rerun` is the documented opt-out and is a **trap here**: any
attribute makes Astro treat the script as `is:inline`, dropping bundling, and the module imports
`@lib/auth` — it would have shipped as a raw `.ts` src and 404'd (`astro check` warns `astro(4000)`
out loud). The module re-arms itself on `astro:page-load` instead, with a path check because the
listener outlives the page.

**Scope narrowed against the RFC's own wording.** "Mount the persisted player shell" was read
strictly: `ClientRouter` + the playback-persist script, and nothing else. No site header/footer, no
PocketBuckit, no AlbumOverlay on `/write` — pulling site chrome into a full-screen editor is a
product change wearing a refactor's clothes, and those islands not persisting onto `/write` is
exactly today's behavior. Both sides need `ClientRouter` or the router falls back to a document
load; the built output confirms `/write` and `/` share the **same** router and persist chunks.

**Verified**: lint clean · `astro check` 0 errors · 173 tests · build 2145 pages. Real browser —
`/write` ↔ site stays in **one document** in both directions (a window marker survives; before this
step the execution context was destroyed), audio host **ALIVE** across both crossings, draft
flushed and restored, `astro:page-load` fires on client-side arrival at `/write`.

**Prod smoke (after deploy 30742211114)** — verified at the chunk level, which is what actually
decides whether a navigation is client-side: `/write/` and `/` load the **same**
`ClientRouter…C8icoCZT.js`; `/write/` installs the **same** `playbackPersist.client.CABP_EJe.js`
that `layout.astro` does; and the login gate ships as bundled JS importing `auth`, with the
`astro:page-load` re-arm and path check intact. Gate held live: logged out, clicking `/write`
bounced to Cognito.

Worth stating precisely now that it is deployed — **the re-arm's real scenario is not the
logged-out first visit.** There the script has not run yet, so the head swap inserts and executes
it either way. The hole it closes is: log in → visit `/write` → hit LOGOUT in the header →
navigate back client-side. Without the re-arm, `deselectScripts` skips the already-executed gate
and the editor opens.

**Honest limits.** The logged-out redirect itself is not reproducible locally — `isLoggedIn()`
returns `true` unconditionally on localhost — so the re-arm is verified structurally (listener
present in the shipped chunk + the event demonstrably firing); prod `/write` still redirects to
Cognito when logged out. Separately, `/write` logs a React **hydration mismatch** on the save dot
(SSR has no localStorage → renders `dirty`, hydrates `saved`); reproduced on a plain full reload,
i.e. the pre-5b model, so it is **pre-existing and independent of routing**. Left alone — its own fix.

### Step 6 (candidate menu) — Connect control extensions — PROMOTED 2026-07-21, subset 6a+6b+6d ✅ SHIPPED (front #302 + bucket-row entry in #303)

Recorded 2026-07-20 on owner request ("rfc 작성해두고, 해당 스텝 진행할 때 선택할 수 있도록").
**Owner selected 6a+6b+6d at promotion (2026-07-21 go, same message as the 7a pick); 6c/6e
stay candidates below.** All are client-side Spotify Web API calls with the member token
(rule #9 clean, same 403-probe degrade + 401 re-mint as Step 3). Feasibility verified
2026-07-20:

- **6a 다음/이전 곡** — `POST /v1/me/player/{next,previous}`. Scope already granted
  (`user-modify-playback-state`, Step 1) → NO re-consent. ⏮ ⏭ on full/banner (list follows
  the miniaturization drop order). Track change warrants one confirmation one-shot
  (event-driven, OQ2 seek precedent — D28-compatible).
- **6b 특정 곡/앨범 재생** — `PUT /v1/me/player/play` with `context_uri` (album) /
  `uris` (tracks). Same scope, no re-consent. Unlocks "이 앨범 재생 ▶" entries on album
  overlay / bucket rows — the listen→review-loop tie-in, highest product value of the menu.
  Needs an active device (404 → toast; Step 5's in-page device is the natural complement).
- **6c 대기열에 추가** — `POST /v1/me/player/queue?uri=`. Same scope. "다음에 듣기" affordance
  on the same surfaces as 6b.
- **6d 좋아요 (Spotify Liked Songs)** — heart on the player bar for the current track:
  `PUT/DELETE /v1/me/tracks?ids=` + liked-state via `GET /v1/me/tracks/contains`. **Requires
  NEW scopes `user-library-read` + `user-library-modify`** → member re-consent (Step 1
  banner idiom, granted-scope string already stored). NOT Premium-gated (free accounts can
  like). Liked-state read = one extra GET per track change, event-driven (D28-compatible).
- **6e 셔플/반복/볼륨/~~기기 전환~~** — `PUT /v1/me/player/{shuffle,repeat,volume}`.
  Same scope, no re-consent. Lowest value; grouped as one item. **Device transfer was pulled
  out of this bundle into Step 5 (2026-08-02)** — a play ladder whose second rung raises a new
  device is unusable without a way to choose between devices, so it is not an extra there.

Scope impact summary: only 6d re-consents; 6a/6b/6c/6e ride the Step 1 grant as-is.
**Verification (whichever subset ships)**: CDP assert matrix per control incl. 403/404
degrade + mobile 390; owner real-device clickthrough for the shipped subset.

**Shipped (6a+6b+6d, front #302; bucket-row 6b entry in front #303)**: 6a = `sendPlayerCommand`
next/previous (POST verb branch), ⏮ ⏭ on full/banner only (drop order), exactly one
confirmation one-shot after success. 6b = new `sendConnectPlay` (Connect active-device play:
no SDK, no `device_id`; `context_uri`/`uris`; distinct `no-active-device` 404 outcome →
toast) with entries on the album overlay ("이 앨범 재생 ▶", members only) and the bucket-row
action sheet (#303, file-ownership split); success dispatches `myblog:playback-changed` →
NowPlaying does one event-driven re-sync. 6d = heart on full/banner, liked-state `contains`
read once per track identity, optimistic toggle w/ rollback; library 403 =
`library-scope-missing`, fully independent of the transport probe (free accounts keep 좋아요,
transport degrade never hides the heart); scope union + separate
`spotifyGrantLacksLibraryScopes` + library re-consent banner (Step 1 idiom). Pre-merge: lint +
astro check clean; CDP fetch-mock matrix 37/37 (asymmetry asserts, D28 call counts, scope
generations, mobile 390) + 6/6 bucket-row entry. Prod: deploy 29783059420; markers
`no-active-device`/`이 앨범 재생` in `AlbumOverlay.*.js`, `다음 곡`/`좋아요 권한 재동의하기` in
`SelfDashboard.*.js`, `myblog:playback-changed` in `spotifyPlayback.*.js`. Owner real-device
clickthrough pending (checklist in #302 body).

## Open questions

1. **App mode** — RESOLVED 2026-07-19: owner confirmed **Extended Quota Mode** in the Spotify
   dashboard (checked during BUG-artist-image-backfill closeout). No Dev-Mode 25-user cap;
   rollout is not gated on user-allowlisting.
2. **Seek granularity** — RESOLVED 2026-07-19 (owner): accept 1 extra one-shot read per seek
   (event-driven, D28-compatible — same precedent as end-of-track re-sync). Implementation
   detail: the confirmation read is skipped while paused, since a paused player reads as
   `idle` in the one-shot contract and would collapse the card; the optimistic anchor is
   exact there anyway.
4. ~~**Does the Web Playback SDK's hidden iframe survive a `ClientRouter` navigation?**~~ —
   **CLOSED, measured on prod 2026-08-02 (CDP, `www.ratemymusic.blog`, real ClientRouter, real
   `sdk.scdn.co` script). Answer: NO — and the presumed fix is refuted.** Details in
   §"OQ4 measurement" below. Short form: the iframe is destroyed on every navigation; tagging it
   `data-astro-transition-persist` does **not** save it; the working fix is an
   `astro:before-swap` swap override that mutates `<body>` in place instead of replacing it
   (measured: 3 hops, 0 reloads). Step 5 is therefore **a ladder rewrite plus a contained
   swap-strategy change** — not the architecture change this OQ feared, but not a one-attribute
   fix either.
5. **Cross-RFC candidate, not owned here** — `user-top-read` (one scope add; endpoint verified
   alive) yields the owner's most-played artists/tracks over 4 weeks / 6 months / all time.
   The product use is "많이 들었는데 아직 평가를 안 쓴 앨범", which is a real-data seed for the
   `FEAT-album-review-authoring` Step 2 "평론 쓸 것" queue — that queue currently has to be
   built from seed data because ratings are still 0. Recorded here because it was discovered
   while probing the grant; **it belongs to that RFC, not this one.** Owner has not scoped it.

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
| 2026-07-20 | **Step 4 owner real-device check CONFIRMED** ("2번 동작한다") — Step 4 fully closed. Same message: owner asked what else the player could control → **Step 6 candidate menu recorded** (6a next/prev, 6b play specific track/album, 6c queue, 6d 좋아요 Liked Songs [only item needing re-consent: `user-library-read/modify`], 6e shuffle/repeat/volume/transfer) — owner selects the subset when the step is promoted; nothing scoped-in yet. Remaining scope = Step 5 + Step 6 selection, both rule-4 gated | 4/6 |
| 2026-07-21 | Owner go (batch prompt): Step 6 promoted with subset **6a+6b+6d** + Step 7 promoted as **7a only** — explicit candidate-promotion approval in the same message; both steps executed in one PR per the owner's parallel-batch instruction | 6/7 |
| 2026-07-21 | **Step 6 (6a/6b/6d) + 7a SHIPPED + prod-smoked** — front #302 (+ bucket-row 6b entry in front #303 per the BucketBoard file-ownership split with FEAT-bucket-identity B). CDP 37/37 + 6/6; prod deploy 29783059420, markers verified. Free-like/Premium-control asymmetry enforced end-to-end (library 403 never degrades transport; transport 403 never hides the heart). Owner real-device checklist pending in #302. Remaining scope = Step 5 + candidates 6c/6e + 7b/7c | 6/7 |
| 2026-08-02 | **Step 5 reframed from "add an SDK output" to "one play ladder".** The premise that an in-page device was missing was wrong — `requestPlayback` has shipped and played since 2026-06-25. The real defect is that six play surfaces are split across two unrelated paths by build date, and the four the owner actually uses are Connect-remote, which 404s with nothing already playing. Owner: build both, **remote wins when a device is active**, plus a click-to-switch device picker | 5 |
| 2026-08-02 | Owner: **"전역으로 할 수 있게 해야만 해"** — playback surviving navigation is a requirement, not a nicety. Existing `ClientRouter` + `transition:persist` infrastructure covers the main layout by construction; the SDK's own iframe is the unverified part (OQ4) and `/write` is a known gap (Step 5b) | 5, 5b |
| 2026-08-02 | Owner approved refactoring `write-layout.astro` ("가장 오래된 기능이기도 하니까"). Split out as **Step 5b** rather than folded in — it alters a 16-component editor island's lifecycle, and mixing it in would make a playback gap ambiguous between SDK and editor | 5b |
| 2026-08-02 | Device transfer moved **6e → Step 5**; remainder of 6e (shuffle/repeat/volume) stays a candidate. Media Session API added to Step 5 as mandatory, not decorative | 5, 6 |
| 2026-08-02 | **Owner question answered by measurement, not docs: one app serves every user.** 6/6 Dev-Mode-removed capabilities answer 200 ⇒ Extended Quota Mode, unlimited users, no allowlist, no second app registration ever needed. Recorded the corollary as a standing risk: since 2025-05-15 individuals cannot obtain extended access, so this grant is irreplaceable and *already-shipped* catalog/library/좋아요 features depend on it | all |
| 2026-08-02 | **Step 5 scoped owner-only.** The owner's live grant already carries `streaming` (measured) ⇒ zero re-consent. Member tier deferred not for consent fatigue but because prod has 1 Spotify integration total — shipping it now would deploy something unverifiable. Member code path still built; only the scope stays closed | 5 |
| 2026-08-02 | **Step 5b SHIPPED** (front #335, `8e82d74`) — and it corrected its own named risk. `/write` was **not** unprotected: `pagehide` already flushed the draft. The hazard is that client-side routing does not *fire* `pagehide`, so this step would have introduced the loss it was written to prevent. Fix is a flush on `astro:before-preparation`, not a confirm dialog — the guarantee is restored exactly, so nothing needs warning about | 5b |
| 2026-08-02 | **A hazard the RFC never named: the `/write` login gate would have been bypassed.** `deselectScripts` marks a page script already-executed by src, so it runs once and never again — a second client-side arrival would walk in. **`data-astro-rerun` is a trap**: any attribute makes Astro treat the script as `is:inline`, dropping bundling, and the module imports `@lib/auth` → it would ship as a raw `.ts` src and 404. The module re-arms on `astro:page-load` instead, path-checked because the listener outlives the page | 5b |
| 2026-08-02 | **"Mount the persisted player shell" read strictly** — `ClientRouter` + the persist script and nothing else. No site header/footer/PocketBuckit/AlbumOverlay on `/write`: pulling site chrome into a full-screen editor is a product change wearing a refactor's clothes, and those islands not persisting there is already today's behavior | 5b |
| 2026-08-02 | **Step 5 SHIPPED** (front #334, `9df4c7a`). The implementation found the ladder was smaller than the reframing implied: the two paths differ by **exactly one query parameter** — same endpoint, same body, only `device_id` — so rung selection stayed attempt-then-fallback (the 404 the old path already returned *is* the "no active device" signal) instead of a `GET /me/player/devices` probe. One request on the happy path, D28 by construction. The device picker reused the Step 4 device line as its own trigger rather than adding chrome. Media Session bound on rung 2 only, so it never competes with a real device's own app | 5 |
| 2026-08-02 | **The swap override is inert unless this tab is the audio device** — that guard is what makes a site-wide navigation change shippable. With no audio host in `<body>`, Astro's default swap runs untouched, so the ordinary navigation keeps stock behavior and stock risk. Also decided: copy upstream's `swapBodyElement` faithfully (persist-id match, the `astro-island` props copy, `attachShadowRoots`) rather than simplify it — the props-copy default is opt-*out*, so "this site does not need it" was an assumption worth not making | 5 |
| 2026-08-02 | **Left alone on purpose**: `sendPlayerCommand` still does not dispatch `MYBLOG_PLAYBACK_CHANGED` for transport kinds. Unifying the play paths made it tempting to close, but that is `FEAT-lyrics-viewer-playback` OQ4's open decision — a step must not silently resolve another RFC's open question | 5 |
| 2026-08-02 | **OQ4 CLOSED by prod measurement — the SDK iframe does NOT survive a `ClientRouter` navigation, and `data-astro-transition-persist` does not save it.** Measured twice over: a runtime-injected node has no counterpart in the incoming document and is dropped, and even inside a genuinely persisted island (host survived as the same node object) the iframe still reloaded. Root cause is not Astro-specific — `swapBodyElement` re-inserts, and re-insertion destroys an iframe's browsing context; Astro guarantees node identity, which is a different guarantee than the one audio needs. Working fix measured: an `astro:before-swap` override mutating `<body>` in place — real SDK iframe, 3 hops, 0 reloads, 0 detaches. Verdict: Step 5 = ladder rewrite **+** a contained swap-strategy change in `layout.astro`, whose blast radius is every navigation and which needs its own regression pass. Corollary: persistence is a **rung-2-only** problem — rung 1 plays on another device, so it is global for free | 5 |
| 2026-08-02 | **Audio quality settles the ladder order**: Web Playback SDK caps at AAC 256 kbps and Spotify Lossless (2025-09, 24-bit FLAC) excludes the web player, so remote control costs zero quality and the in-page device always costs some. "Remote first" is a correctness argument, not a preference — and rung 2 must say it is degraded | 5 |
| 2026-08-02 | **Negative finding, recorded so it is not re-planned**: we were NOT grandfathered into the 2024-11-27 deprecations. Recommendations, Audio Features, Audio Analysis, Related Artists, genre seeds, featured playlists and `preview_url` are all dead for this app too (measured). No feature may assume derived mood/energy or "similar artists". Separately, `user-top-read` is alive but ungranted → recorded as OQ5, belonging to `FEAT-album-review-authoring` | — |
| 2026-07-20 | **Capability-classification audit (owner request)**: the RFC's Full/Fallback pair under-specified real member situations (Last.fm-only, free-vs-Premium, old-scope generation were implicit or absent) and no user-facing surface explains per-situation availability. Added the **user-situation capability matrix** (canonical; every new player feature must amend it in the same PR) + **Step 7 candidate** (7a 연동 tab 기능 안내 / 7b 플레이어 인라인 "왜 컨트롤이 없나요?" / 7c 설명서 페이지, matrix-driven). Notable user-facing asymmetries: 좋아요·device hint work on FREE accounts (controls alone are Premium); Last.fm = display-only | 7 |
