# FEAT-lyrics-viewer-playback: transport controls and the queue inside the lyrics viewer

- **Status**: draft
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

**Mount point.** `LyricsViewer` is mounted only at `myblog_front/src/components/member/SelfDashboard.tsx:198`, for `lyrics.kind === 'live'` (tapped from `NowPlaying`). `LyricsSheet` (`:199`) and `AlbumDetail`'s `DockableLyricsSheet` are separate components on the static path.

**Command transport already exists.** `myblog_front/src/lib/spotifyPlayback.ts:331`:

```ts
export type PlayerCommand =
  | { kind: 'play' } | { kind: 'pause' } | { kind: 'seek', positionMs: number }
  | { kind: 'next' } | { kind: 'previous' }
```

`sendPlayerCommand` (`:345`) issues the Spotify Connect call client-side with the member's minted token, retries once on a mid-session 401, never throws, and returns `{ ok: true }` or a typed failure (`no-capability` / `token` / `transient`). On success it dispatches `MYBLOG_PLAYBACK_CHANGED` (`:34`, `:424`). `NowPlaying.tsx` is the only consumer today (`:367` play/pause, `:402` seek, `:429` next/prev — member-player Steps 3 and 6a). **Nothing new is needed for 재생/일시정지/다음/이전.**

**Queue is not implemented anywhere.** `grep` for `me/player/queue` in `myblog_front/src` returns only `/api/todays-pick/queue` (an unrelated backend route) and a `pocketBuckit/leaf.ts` comment. The Spotify queue endpoint has never been called.

**The viewer's chrome.** Header (`LyricsViewer.tsx:747`) carries the eyebrow + title block on the left and an actions cluster on the right: 번역 · ↻ · ⚙ · ✕. The bottom of the panel is empty. `.lyv-list` uses `padding: 38vh 28px` and the focused line is centred at `boxH * 0.42` (`applyCenter`, `LyricsViewer.tsx:527`).

**The gesture model is the constraint.** `.lyv-scroll` is `overflow: hidden` with `touch-action: none`; vertical pointer drag is captured as **line stepping** (`onPointerMove`, `LyricsViewer.tsx:636`, `DRAG_STEP = 56`), wheel is captured as stepping (`WHEEL_STEP = 80`), and a real drag suppresses the click so it cannot double as tap-to-focus. A scrollable list cannot share this surface — hence the owner's choice of a full screen swap rather than an overlaid sheet (2026-08-01).

**Capability degrade already has a shape.** member-player Step 3 established the pattern: a failed command surfaces a short inline line and degrades the control rather than throwing, with `no-capability` distinguished from `transient`.

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

- New `.lyv-transport` bar rendered inside `.lyv-panel` below `.lyv-body`, live entries only (`canRefresh` already marks the live entry).
- Play/pause reflects a `playing` flag. `FEAT-lyrics-sync-precision` Step 2 introduces that flag for the clock; if this RFC ships first, it owns the flag and that RFC consumes it. Either order works — the flag is one `useState`.
- Failures reuse the member-player degrade shape: `no-capability` disables the cluster with a one-line reason, `transient` shows a brief inline notice via the existing `notice` state (`LyricsViewer.tsx:432`), `token` routes to the existing streaming-status messages.
- Centring math: `applyCenter` targets `boxH * 0.42` of `.lyv-scroll`'s height. Since the bar shrinks `.lyv-scroll` rather than overlaying it, `boxH` shrinks with it and the focus line stays centred. Verify the measurement cache (`measureRef`) is invalidated when the bar appears/disappears.
- Mobile: `env(safe-area-inset-bottom)` padding, ≥44 px touch targets at 390 px.

**Verification**

```
cd myblog_front
pnpm lint && pnpm exec astro check && pnpm test
```

Plus a real-browser clickthrough at desktop and 390 px: each button issues its command against a live device; the focused line stays centred with the bar present; `prefers-reduced-motion` unaffected.

**Rollback**: revert. No persisted state.

---

### Step 2 — Queue screen (view only)

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

1. **Does the current token carry the scope the queue endpoint needs?** — blocks Step 2. Spotify's Get User's Queue documents `user-read-currently-playing` **and** `user-read-playback-state`. `playback.api.ts:8` states the minted token carries `user-read-playback-state`; whether `user-read-currently-playing` is granted is unverified. If it is missing this needs a re-consent, which `FEAT-member-player` treated as a significant cost (좋아요 was called out as its *sole* re-consent item). **Probe the live token before designing around it.**
2. **User-added queue items under an album/playlist context.** — blocks Step 3. `/me/player/queue` returns one flat `queue[]` and does not mark which entries came from the context versus the user's manual queue. A `context_uri` + `offset` jump only works for the former. Options: (a) make every row inert whenever any ambiguity exists, (b) attempt the jump and degrade on failure, (c) match rows against the context's track list with a second request. Owner picked "되는 경우만 점프" as the *behaviour*; this question is how we determine "되는 경우" without lying to the user.
3. **Does the bar belong on the dock/static sheet too?** — blocks nothing; currently a non-goal. Raise only if the owner asks after using it.

## Decisions log

| Date | Decision | Step |
|------|----------|------|
| 2026-08-01 | Owner: controls go in an always-visible bottom bar, not the header and not a tap-to-reveal overlay — thumb reach and no hunting, at the cost of ~60 px of lyric height. | 1 |
| 2026-08-01 | Owner: the queue is a full screen swap, not an overlaid sheet. The viewer's vertical drag is already line-stepping, so a sheet would force gesture arbitration at a boundary; a swap has zero conflict by construction. | 2 |
| 2026-08-01 | Owner: 되는 경우만 점프 — rows jump where Spotify permits it and are inert otherwise. "Repeat ⏭ until we arrive" was rejected (slow, pollutes listening history). | 3 |
| 2026-08-01 | Scope fixed to 재생/일시정지/다음/이전/대기열. Volume, shuffle, repeat, transfer, 좋아요 stay out. | — |
| 2026-08-01 | Split out of the sync brainstorm into its own RFC: new UI surface, new Spotify API, mobile touch design and a possible re-consent — a different risk profile and a different verification from timing math. Cross-refs `FEAT-member-player` (queue was a Step 6 candidate) and `FEAT-lyrics-sync-precision` (consumes the commands as re-anchor events). | — |
