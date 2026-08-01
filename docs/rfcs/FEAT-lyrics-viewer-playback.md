# FEAT-lyrics-viewer-playback: transport controls and the queue inside the lyrics viewer

- **Status**: accepted
- **Owner**: 오너
- **Created**: 2026-08-01
- **Plan row**: `plan.md` → FEAT-lyrics-viewer-playback

---

## Goal

The full-screen live lyrics viewer stops being read-only. A bottom bar carries 이전 / 재생·일시정지 / 다음 plus a 대기열 entry; the 대기열 entry swaps the panel to a full-screen queue list showing what plays next, with a back arrow to the lyrics. Tapping a queue row jumps to that track **when Spotify allows it** (album/playlist context playback) and is inert otherwise. Every command reuses the existing `sendPlayerCommand` transport — no new backend route, no new contract.

## Non-goals

- **Volume, shuffle, repeat, device transfer, 좋아요.** The owner scoped this to 재생/일시정지/다음/이전/대기열 (2026-08-01). Shuffle/repeat/volume/transfer remain `FEAT-member-player` Step 6 candidates; 좋아요 already shipped there as 6d on the player bar.
- **The static reading surfaces.** `LyricsSheet` and `DockableLyricsSheet` (`FEAT-lyrics-sheet`) are documents, not players. Untouched.
- **Queue editing.** No add / remove / reorder. Read and jump only.
- **Polling the queue.** The queue is read once when the queue screen opens and once per track change while it is open. D28 holds.
- **Sync mechanics.** How a command re-anchors the lyrics clock is `FEAT-lyrics-sync-precision`. This RFC only emits the signal that RFC already consumes.

## Current state

> Re-audited against code 2026-08-01 **after front #325** (`feat(lyrics): remove the fixed sync lead and re-anchor on playback events`, +263 lines in `LyricsViewer.tsx`), which landed between this RFC's drafting and its acceptance. The file path and every `LyricsViewer.tsx` line number in the original draft were wrong; the three subsections marked **[#325]** are new facts the draft could not have known.

**Mount point.** `LyricsViewer` lives at `myblog_front/src/components/member/lyrics/LyricsViewer.tsx` (**not** `member/LyricsViewer.tsx`, as the draft said) and is mounted only at `myblog_front/src/components/member/SelfDashboard.tsx:198`, for `lyrics.kind === 'live'` (tapped from `NowPlaying`), with `canRefresh` set. `LyricsSheet` (`:199`) and `AlbumDetail`'s `DockableLyricsSheet` are separate components on the static path.

**Command transport already exists.** `myblog_front/src/lib/spotifyPlayback.ts:331`:

```ts
export type PlayerCommand =
  | { kind: 'play' } | { kind: 'pause' } | { kind: 'seek', positionMs: number }
  | { kind: 'next' } | { kind: 'previous' }
```

`sendPlayerCommand` (`:345`) issues the Spotify Connect call client-side with the member's minted token, retries once on a mid-session 401, never throws, and returns `{ ok: true }` or a typed failure (`no-capability` / `token` / `transient`). `NowPlaying.tsx` is the only consumer today (`:371` play/pause, `:406` seek, `:433` next/prev — member-player Steps 3 and 6a). **Nothing new is needed on the wire for 재생/일시정지/다음/이전.**

**`sendPlayerCommand` does NOT dispatch `MYBLOG_PLAYBACK_CHANGED`.** The draft claimed it did, citing `spotifyPlayback.ts:424` — but `:424` sits inside `sendConnectPlay` (`:390`), a different function, the one that starts an album/track from a card. `sendPlayerCommand`'s success path is a bare `return { ok: true }` (`:363-364`). Confirmed in a browser 2026-08-01: with a listener attached, ⏭ and ⏸ produced **zero** events.

Two things follow, and Step 1 depends on both:

- The `MYBLOG_PLAYBACK_CHANGED` → `resync('command')` wiring `FEAT-lyrics-sync-precision` Step 2 added (`LyricsViewer.tsx:686`) has **never fired for a transport command** — only for "playback started elsewhere on the page". Its `ResyncSource = 'command'` residual channel has correspondingly never recorded a transport round-trip, so any accuracy series read off it is not measuring what its name says. The in-code comment asserting otherwise was corrected in this step.
- Making `sendPlayerCommand` dispatch would be the tidier fix, but `NowPlaying.tsx:528` also listens, so it would give a shipped component a new self-triggered re-read. Out of scope here — recorded as OQ4.

**Queue is not implemented anywhere.** `grep` for `me/player/queue` in `myblog_front/src` returns only `/api/todays-pick/queue` (an unrelated backend route) and a `pocketBuckit/leaf.ts` comment. The Spotify queue endpoint has never been called.

**The viewer's chrome.** Header (`LyricsViewer.tsx:918`) carries the eyebrow + title block on the left and an actions cluster on the right: 번역 · ↻ · ⚙ · ✕. `.lyv-list` uses `padding: 38vh 28px` and the focused line is centred at `boxH * 0.42` (`applyCenter`, `LyricsViewer.tsx:656`).

The bar's space comes out of the list for free: `.lyv-panel` is a flex column and `.lyv-body` is `flex: 1; min-height: 0` (`layout.css:758`), so a sibling bar shrinks `.lyv-scroll` rather than overlaying it, and `boxH` shrinks with it.

**The panel foot is NOT empty** (the draft claimed it was). `.lyv-return` — the browse-mode snap-back countdown ring — floats there: `position: absolute; left: 50%; bottom: calc(28px + env(safe-area-inset-bottom)); width/height: 42px; z-index: 4` (`layout.css:474`), rendered whenever `suspended` (`LyricsViewer.tsx:908`). That is exactly where a ~60 px transport bar lands. Step 1 must lift it above the bar.

**The gesture model is the constraint.** `.lyv-scroll` is `overflow-y: hidden` with `touch-action: none`; vertical pointer drag is captured as **line stepping** (`onPointerMove`, `LyricsViewer.tsx:807`, `DRAG_STEP = 56`), wheel is captured as stepping (`WHEEL_STEP = 80`), and a real drag suppresses the click so it cannot double as tap-to-focus. A scrollable list cannot share this surface — hence the owner's choice of a full screen swap rather than an overlaid sheet (2026-08-01).

**Capability degrade already has a shape.** member-player Step 3 established the pattern: a failed command surfaces a short inline line and degrades the control rather than throwing, with `no-capability` distinguished from `transient`.

**[#325] The `playing` flag already exists.** `FEAT-lyrics-sync-precision` Step 2 shipped, so `const [playing, setPlaying] = useState(true)` is live at `LyricsViewer.tsx:360` and already gates the focus scheduler (`:735`). The draft's "whichever RFC ships first owns the flag" hedge is dead — Step 1 **consumes** it and must not redeclare it.

**[#325] …and before Step 1 nothing could write it from a transport command at all.** `playing` is only ever set from the *result* of a `readLivePlayback()` (`:528`). The one path that was supposed to trigger such a read after a command is the `MYBLOG_PLAYBACK_CHANGED` listener — which, per the correction above, never fires for `sendPlayerCommand`. Even where it does fire it drops the read when the previous one was less than `EVENT_RESYNC_FLOOR_MS = 1500` ago (`:130`, `:579`). **So Step 1 must set `playing` at command-issue time — not as an optimisation, but as the only mechanism.** Verified: without it a ⏸ leaves the icon claiming playback and the scheduler advancing lines over silence.

**[#325] The lyrics swap after next/prev is NOT free** (the first audit pass got this wrong, on the strength of the same bad dispatch claim). Nothing re-reads identity after a skip, so the viewer keeps showing the previous track's lyrics indefinitely. Step 1 issues that read itself, and `refresh` gained a single-slot queue so a read requested while one is in flight is remembered rather than dropped — otherwise ⏭⏭ lands the viewer one track behind.

## Target state

```
가사 화면                            대기열 화면
┌──────────────────────────┐        ┌──────────────────────────┐
│ Lyrics · synced 번역 ↻ ⚙ ✕│        │ ← 대기열                  │
│                          │        │                          │
│      지난 여름의 끝에      │  ☰ 탭  │ ▸ 우리는 아무 말 없이  재생중│
│   ▸ 우리는 아무 말 없이 ◂  │ ─────▶ │   다음 트랙 제목           │
│      길게 서 있었다        │        │   그 다음 트랙            │
│                          │ ◀───── │   ...                    │
├──────────────────────────┤   ←    │                          │
│   ⏮   ⏸   ⏭      ☰ 대기열│        │                          │
└──────────────────────────┘        └──────────────────────────┘
```

- The bottom bar is always visible on the live viewer (owner pick 2026-08-01 — thumb reach beats lyric real estate; it costs ~60 px of vertical space, absorbed by the centring math, not by clipping).
- The queue screen replaces the panel body entirely, so it owns its own scroll and no gesture arbitration is needed.
- Queue rows are tappable only when a jump is actually possible; otherwise they render as plain rows with no affordance.

## Steps

### Step 1 — Bottom transport bar

`⏮ ⏸/▶ ⏭` wired to `sendPlayerCommand`, plus an inert-for-now `☰ 대기열` button.

**Changes**

- New `.lyv-transport` bar rendered inside `.lyv-panel` as a sibling of `.lyv-body`, live entries only (`canRefresh` already marks the live entry). **Outside** the `phase.k === 'ready' && n > 0` fragment (`LyricsViewer.tsx:1057`) that wraps `.lyv-body` — otherwise the bar disappears on loading / error / "가사 없음", which is precisely when the owner wants ⏭ to escape the track.
- Play/pause reflects the **existing** `playing` flag (`:360`, shipped by `FEAT-lyrics-sync-precision` Step 2 — see Current state). Do not redeclare it.
- **Set `playing` optimistically when the command is issued**, not from the resync that follows. The `MYBLOG_PLAYBACK_CHANGED` → `resync('command')` path is rate-limited to one read per 1.5 s (`EVENT_RESYNC_FLOOR_MS`), so a quick ⏭ then ⏸ otherwise leaves the icon and the focus scheduler both believing playback is running. Revert the optimistic write if `sendPlayerCommand` returns `ok: false`; the eventual resync remains the correction of record.
- Failures reuse the member-player degrade shape: `no-capability` disables the cluster with a one-line reason, `transient` shows a brief inline notice via the existing `notice` state (`LyricsViewer.tsx:515`), `token` routes to the existing streaming-status messages.
- Centring math: `applyCenter` targets `boxH * 0.42` of `.lyv-scroll`'s height. Since the bar shrinks `.lyv-scroll` rather than overlaying it, `boxH` shrinks with it and the focus line stays centred. **`measureRef` caches `boxH` (`:654`) and is invalidated only on `[showKo, lyvStyle]` (`:688`) and `resize` (`:709`)** — a bar that appears or disappears is neither, so its mount/unmount must join that invalidation set.
- Lift `.lyv-return` (the browse countdown ring, `layout.css:474`) above the bar so the two never overlap; it currently sits at `bottom: calc(28px + env(safe-area-inset-bottom))`, inside the bar's footprint.
- Mobile: `env(safe-area-inset-bottom)` padding, ≥44 px touch targets at 390 px.

**Verification**

```
cd myblog_front
pnpm lint && pnpm exec astro check && pnpm test
```

Plus a real-browser clickthrough at desktop and 390 px: each button issues its command against a live device; the focused line stays centred with the bar present; `prefers-reduced-motion` unaffected. Three checks come from the #325 audit:

- **⏭ then ⏸ within 1.5 s** — the icon must show paused and the lyrics must stop advancing (this is the case the resync floor swallows).
- **⏭ alone** — the lyrics swap to the next track with no Step-1 code doing it (the #325 listener path).
- **Browse-drag mid-playback** so `.lyv-return` renders — the ring and the bar must not overlap at 390 px with a safe-area inset.

**Rollback**: revert. No persisted state.

---

### Step 2 — Queue screen (view only) — **SHIPPED + prod-verified 2026-08-01**

front #328 `d66f173` · deploy run 30688315730 success · prod smoke 19/0 · new-bundle markers confirmed in the live `SelfDashboard` chunk and member CSS.

`☰ 대기열` swaps the panel body to a scrollable list; `←` returns.

**Changes**

- New `queue.api.ts` alongside `playback.api.ts`, same sanctioned client-side pattern (`getStreamingToken` → `fetch` with an explicit timeout → typed result, never throws): `GET https://api.spotify.com/v1/me/player/queue` → `{ currently_playing, queue[] }`.
- One read when the queue screen opens; one re-read when the viewer's track id changes while the screen is open. No interval.
- View state is local to `LyricsViewer` (`view: 'lyrics' | 'queue'`). The lyrics clock keeps running underneath — returning lands on the right line with no re-read.
- Rows: title + artists, the currently-playing row marked. Empty queue and failure both get a plain state; a failure must not close the viewer.
- ESC ordering: the existing `useDismissable` stack closes ⚙ first, then the viewer. The queue screen inserts itself so ESC on the queue returns to lyrics before closing the viewer.

**Verification**

```
cd myblog_front
pnpm lint && pnpm exec astro check && pnpm test
```

Plus a real-browser clickthrough: open with a real queue, scroll it, return, confirm the lyrics line is still correct; force a 403/timeout and confirm graceful degrade.

**What shipped, where it differs from the plan above**

- Rows are inert `<li>`s rather than anything tappable-looking. Step 3 is what decides which rows can be jumped to (it needs the playback `context`, and OQ2 is open); a row that looks tappable and isn't would promise what this step cannot keep.
- `☰` is a **toggle** (`aria-pressed`), so the bar itself is a second way back alongside `←`. It is deliberately **not** gated on `transportDead` — a queue *read* and a transport *command* fail independently.
- 다시 시도 renders only for a transient failure. `no-capability` and `token` survive any number of retries, so each gets a plain sentence instead.
- 204 is an **empty queue**, not a failure.
- 번역 / ↻ / ⚙ hide while the queue is up (they act on the lyrics surface); ✕ stays.
- One thing the plan did not anticipate: **the return had to be made to LAND, not glide.** The clock keeps running while the queue is open, so `focus` has usually moved on; leaving `positionedRef` true made the remounted list animate up from its identity transform. Reset it while the queue is up and the return re-centres instantly on the *current* line. Measured across a full open → queue → return round trip: exactly one `/api/lyrics` fetch, i.e. "no re-read" held.
- `.lyv-head-id` needed `margin-right: auto`: `.lyv-head` is `space-between`, which only reads correctly with two children, and `←` made it three.

**Verified in a browser** (CDP, live `/members/?u=owner&tab=overview`, playback stubbed after the owner's device went idle mid-session), desktop 1440 + mobile 390×844×3: open/return; ESC returns to lyrics before closing the viewer; 403 / 500 / 204-empty each degrade in-panel without closing the viewer; 다시 시도 re-reads (1 call → 2); ⏭ with the queue open re-reads the queue exactly once and swaps both list and head; long titles ellipsis without widening the panel (the only horizontal overflow is `.lyv-bg`'s deliberate 150 % overscan); rows 52 px, ☰ 44 px, 대기열 label drops below 400 px.

**Remaining, owner-only**: one real-device pass — ☰ 대기열 on a phone with music actually playing, list matches the Spotify app, `←` returns to the right lyric line.

**Rollback**: revert.

---

### Step 3 — Context jump (되는 경우만)

Tapping a queue row starts that track when it belongs to the current album/playlist context.

**Changes**

- `GET /v1/me/player` already returns the playback `context` (`uri`, `type`) — currently unread by `readLivePlayback`. Surface it.
- When `context.type` is `album` or `playlist`, a row tap issues `PUT /v1/me/player/play` with `context_uri` + `offset: { uri: <track uri> }` (a new `PlayerCommand` kind, so it inherits the existing token retry and `MYBLOG_PLAYBACK_CHANGED` dispatch).
- When there is no context, rows are inert — no tap handler, no hover affordance, so a row never looks tappable and then fails.
- OQ2 below decides how rows are treated when a context exists but the row is a user-added queue item.

**Verification**

```
cd myblog_front
pnpm lint && pnpm exec astro check && pnpm test
```

Plus a real-browser clickthrough covering all three cases: album context (jump works), no context / single-track playback (rows inert), and a user-queued item under a context (behaviour per OQ2).

**Rollback**: revert. Steps 1–2 stand alone.

---

## Open questions

1. **Does the browser's token carry the scope the queue endpoint needs?** — blocks Step 2. **Narrowed from code 2026-08-01, and the news is bad.** `scripts/spotify_bootstrap_token.py` mints two *distinct* refresh tokens with disjoint scope sets:

   ```python
   SCOPES = (                      # the WORKER's read token
       "user-read-recently-played user-read-currently-playing "
       "user-library-read user-library-modify "
       "user-follow-read"
   )
   STREAMING_SCOPES = "streaming user-read-playback-state user-modify-playback-state"
   ```

   Spotify's Get User's Queue documents `user-read-currently-playing` **and** `user-read-playback-state`. Those two scopes live on **different tokens**, and neither token holds both:
   - the browser's streaming token (what `readLivePlayback` and any queue call would use) has `user-read-playback-state` but **not** `user-read-currently-playing`;
   - the worker's read token has `user-read-currently-playing` but not `user-read-playback-state` — and it is server-side, never in the browser, so it is not a route to the queue anyway.

   What is still unverified is only whether Spotify **enforces** both for this endpoint. If it does, Step 2 requires re-minting `streaming_refresh_token` with `user-read-currently-playing` added — an owner re-consent, the cost `FEAT-member-player` called out as its sole such item (좋아요). That is a real gate on Step 2, not a footnote.

   **Cheapest decisive probe** (30 s, owner, signed in on the live site — the browser holds a real streaming token, no test account does):

   ```js
   // console on https://www.ratemymusic.blog/members/?me , with the dashboard open
   const t = await (await fetch('/api/playback/spotify-token')).json()
   const r = await fetch('https://api.spotify.com/v1/me/player/queue', { headers: { Authorization: `Bearer ${t.access_token}` } })
   r.status   // 200 → no re-consent needed, Step 2 is cheap
              // 403 → re-consent required, decide before building
   ```

   **ANSWERED 2026-08-01 — 200, no re-consent. Everything above this line was wrong, and wrong in an instructive way.**

   The analysis above reasoned from `STREAMING_SCOPES`, the constant that *requests* scopes. The grant actually stored in `/myblog/spotify` was minted with a broader consent than that constant asks for, and a token minted from it today carries **both** documented scopes:

   ```
   [mint] granted: streaming user-modify-playback-state user-library-read
                   user-follow-read user-library-modify
                   user-read-playback-state user-read-currently-playing
                   user-read-recently-played
   [queue]  GET /v1/me/player/queue → 200 · currently_playing present · 19 items
   [player] GET /v1/me/player       → 200 · is_playing false · context type album
   ```

   Note the second line: the queue reads **200 even while paused**, so the screen does not need live playback to be useful.

   Members were never at risk either. The member connect URL (`SPOTIFY_SCOPES` in `myblog_front/src/components/member/integrations.api.ts`) has asked for `user-read-currently-playing` all along; only a pre-playback *legacy* grant could lack it, and `spotifyGrantNeedsReconsent` already flags those. `readQueue` still maps 403/404 to `no-capability` for exactly that shape.

   **The probe did not need the owner or a browser.** It was written up as "owner, signed in on the live site — the browser holds a real streaming token, no test account does". That framing confused *whose* token it is with *where it is held*: the owner's browser token is minted server-side from `streaming_refresh_token`, so reading that secret from SSM and minting directly answers the identical question with no human in the loop. The step sat blocked on a human for a day for no reason. **Before parking a question on "owner-only", check whether the credential is reachable from the server.**

   The wider lesson, in one line: **a constant that requests a scope is not evidence of the scope that was granted.** Ask the live grant.
2. **User-added queue items under an album/playlist context.** — blocks Step 3. `/me/player/queue` returns one flat `queue[]` and does not mark which entries came from the context versus the user's manual queue. A `context_uri` + `offset` jump only works for the former. Options: (a) make every row inert whenever any ambiguity exists, (b) attempt the jump and degrade on failure, (c) match rows against the context's track list with a second request. Owner picked "되는 경우만 점프" as the *behaviour*; this question is how we determine "되는 경우" without lying to the user.
3. **Does the bar belong on the dock/static sheet too?** — blocks nothing; currently a non-goal. Raise only if the owner asks after using it.
4. **Should `sendPlayerCommand` dispatch `MYBLOG_PLAYBACK_CHANGED`?** — blocks nothing; found during Step 1. It does not today, so `FEAT-lyrics-sync-precision` Step 2's `'command'` residual channel has never observed a transport command, and any conclusion drawn from that series is about `sendConnectPlay` only. Adding the dispatch would fix the channel in one line, but `NowPlaying.tsx:528` listens too and would start re-reading after its own commands — a behaviour change to a shipped component, hence not folded into Step 1. Decide alongside whatever next consumes the residual series.

## Decisions log

| Date | Decision | Step |
|------|----------|------|
| 2026-08-01 | Owner: controls go in an always-visible bottom bar, not the header and not a tap-to-reveal overlay — thumb reach and no hunting, at the cost of ~60 px of lyric height. | 1 |
| 2026-08-01 | Owner: the queue is a full screen swap, not an overlaid sheet. The viewer's vertical drag is already line-stepping, so a sheet would force gesture arbitration at a boundary; a swap has zero conflict by construction. | 2 |
| 2026-08-01 | Owner: 되는 경우만 점프 — rows jump where Spotify permits it and are inert otherwise. "Repeat ⏭ until we arrive" was rejected (slow, pollutes listening history). | 3 |
| 2026-08-01 | Scope fixed to 재생/일시정지/다음/이전/대기열. Volume, shuffle, repeat, transfer, 좋아요 stay out. | — |
| 2026-08-01 | OQ1 narrowed from code, not from a probe: the two scopes the queue endpoint documents sit on two **different** refresh tokens (`SCOPES` vs `STREAMING_SCOPES` in `scripts/spotify_bootstrap_token.py`) and the browser's token is missing `user-read-currently-playing`. Whether Spotify enforces it is the only open half; a 2-line console probe settles it. | 2 |
| 2026-08-01 | Owner: Status draft → **accepted**, and Step 1 starts without the OQ1 probe — OQ1 gates Step 2 only, so blocking Step 1 on it buys nothing. | — |
| 2026-08-01 | **OQ1 answered: 200, no re-consent, Step 2 unblocked.** The narrowing above reasoned from `STREAMING_SCOPES` — the constant that *requests* scopes — but the grant actually stored in `/myblog/spotify` was minted with a broader consent and carries both documented scopes. Two corrections carried forward: a requested-scope constant is not evidence of a granted scope, and the question was never owner-only (the browser's token is minted server-side from a secret in SSM, so it is answerable without a human). | 2 |
| 2026-08-01 | Browser verification of Step 1 disproved the draft's `sendPlayerCommand` → `MYBLOG_PLAYBACK_CHANGED` claim (`:424` is `sendConnectPlay`, a different function; a live listener saw 0 events from ⏯⏭⏮). The first audit pass repeated the claim instead of checking it, and its "next/prev swaps lyrics for free" conclusion fell with it. Step 1 therefore owns both the `playing` write and the post-skip identity read. Raised as OQ4 whether the dispatch should simply be added. | 1 |
| 2026-08-01 | Current state re-audited against code after front #325 and corrected: wrong component path (`member/` → `member/lyrics/`), every `LyricsViewer.tsx` line number stale, and the panel foot is occupied by `.lyv-return`, not empty. Three facts #325 introduced are now load-bearing for Step 1 — the `playing` flag already exists, its only writer is a re-read behind a 1.5 s floor (so Step 1 writes it optimistically), and next/prev inherits the track swap for free. | 1 |
| 2026-08-01 | Split out of the sync brainstorm into its own RFC: new UI surface, new Spotify API, mobile touch design and a possible re-consent — a different risk profile and a different verification from timing math. Cross-refs `FEAT-member-player` (queue was a Step 6 candidate) and `FEAT-lyrics-sync-precision` (consumes the commands as re-anchor events). | — |
