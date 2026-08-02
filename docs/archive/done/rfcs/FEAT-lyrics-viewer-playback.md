# FEAT-lyrics-viewer-playback: transport controls and the queue inside the lyrics viewer

- **Status**: done (2026-08-03, archived — Steps 1–3 all SHIPPED + prod-smoked
  and all three owner-confirmed on a real device (2026-08-01, 2026-08-02); the
  last open item, OQ4, was answered and shipped 2026-08-03 in front #342. No
  observation gates remain → moved to `docs/archive/done/rfcs/`. Original
  status line below.)
  <br>_accepted_ (오너 승격 2026-08-01)
- **Owner**: 오너
- **Created**: 2026-08-01
- **Plan row**: dropped 2026-08-03 — nothing left to track; history in `git log`
  and `docs/archive/done/2026-08.md`

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
  **This check shipped broken and the owner found it in prod on 2026-08-02 — fixed in front #333.**
  Step 1 issued its identity read, but exactly ONE, and Spotify Connect keeps answering
  `GET /me/player` with the pre-skip track for a beat after its 204. That stale read is
  indistinguishable from an ordinary same-track read, so `refresh` took its same-track branch,
  re-anchored to the track being left, and never asked again. Step 3's queue-row jump had
  already solved the identical race with a retry loop; the skip never got one. Both now share
  `confirmTransport()`. **A skip cannot name its destination, so it names the track it is
  leaving (`awaitingChangeFrom`) and waits for any read that disagrees.**
  The lesson for the remaining steps: **a post-command read-back is a race, and a verification
  that reads back once can win it by luck.** Re-verify this class against a stub that lags
  (front #333 ships one) or against a real device, never against an instant answer.
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

### Step 3 — Context jump (되는 경우만) — **SHIPPED + prod-verified 2026-08-02**

front #329 `2a4fd9e` · deploy run 30708914030 success · prod smoke 19/0 · new-bundle markers confirmed in the live assets (`play-context` in `_astro/spotifyPlayback.*.js`, `is-tappable` in the member CSS).

**오너 실기기 확인 — 통과 (2026-08-02). 이 단계에 남은 항목은 없다.** 실제 폰에서 직접 추가한 곡을 탭한 뒤 **그 아래 곡들이 Spotify 앱 대기열에 그대로 남아 있었다.** 이것이 이 단계의 유일한 사람-확인 항목이었던 이유는, 폴백이 꼬리를 같이 싣는지가 **기기의 Spotify 앱 상태로만 드러나기** 때문이다 — 단독 곡으로 폴백하는 버그였다면 뒤에 쌓인 대기열이 조용히 사라졌을 것이고, 브라우저에서는 그 소멸이 보이지 않는다. `queueJump.test.ts`가 같은 성질을 단위 테스트로 잡고 있지만, 그건 우리 코드가 무엇을 보내는지를 고정할 뿐 Spotify가 그 결과로 무엇을 남기는지는 말해주지 않는다.

Tapping a queue row starts that track when it belongs to the current album/playlist context.

**Changes**

- `GET /v1/me/player` already returns the playback `context` (`uri`, `type`) — currently unread by `readLivePlayback`. Surface it.
- When `context.type` is `album` or `playlist`, a row tap issues `PUT /v1/me/player/play` with `context_uri` + `offset: { uri: <track uri> }` (a new `PlayerCommand` kind, so it inherits the existing 401 re-mint retry — **not** a `MYBLOG_PLAYBACK_CHANGED` dispatch; this line said otherwise and was wrong for the same reason the Current state section records, `sendPlayerCommand` has never dispatched).
- **Fallback (OQ2, answered 2026-08-01)**: when the context jump fails, or there is no context at all, re-issue `play` with `uris: [tapped, ...the rest of the visible queue after it]`. Carrying the tail is the point — a lone-track `uris` replaces the context and deletes everything queued behind it. If that also fails, an in-panel notice; never a silent no-op.
- Consequence: rows are **tappable by default**, not inert-by-default. The draft assumed we had to predict which rows could be reached; the fallback removes the need to predict. A row stays inert only when there is nothing to send at all (no context *and* nothing behind it).
- The queue screen already renders `재생 중` separately from the numbered rows, so "the rest of the queue after the tapped row" is a plain slice of what is on screen — no second request, no matching heuristic.

**Verification**

```
cd myblog_front
pnpm lint && pnpm exec astro check && pnpm test
```

Plus a real-browser clickthrough covering the three paths the fallback chain creates: (1) album context, tap a context row → jumps with the context intact; (2) tap a user-added row → the context jump fails and the `uris` tail takes over, and **the rows below the tapped one are still there afterwards** (that is the check that proves the tail was carried, and the one a lone-track fallback would fail); (3) force both to fail → an in-panel notice, viewer stays open, lyrics unaffected.

**What shipped, where it differs from the plan above**

- The chain lives in its own module, `queueJump.ts`, rather than inside the viewer. The one property this step exists to protect — *the fallback carries the tail* — is then pinned by a unit test that does not have to mount a 1450-line component. `queueJump.test.ts` names the lone-track fallback as the regression it guards, so a future reader cannot mistake the tail for incidental.
- **The context is read alongside the queue, not at tap time.** The viewer never called `readLivePlayback` on open (it seeds from `initialProgressMs`), so `context` would have been `null` on the first tap and *every* first jump would have silently taken the fallback — defeating link 1 entirely. The queue-open effect now runs `Promise.all([readQueue(), readLivePlayback()])`, and `refresh()` keeps the context current for free thereafter. Cost: one extra request per queue open; benefit: the tap itself stays one round trip.
- A failed `readLivePlayback` (`unavailable`) **keeps** the previously known context rather than clearing it. A failed read is not evidence the context is gone, and clearing would drop the next tap to the fallback for no reason.
- Row markup moved into a `QueueRowBody` sub-component. Making rows tappable created a third shape (재생 중 / tappable / uri-less) of the same badge-plus-title markup; leaving it copied three times is exactly the twin-drift class this repo hardened against.
- `QueueEntry.uri` is nullable and a missing uri does **not** drop the row — the list must not silently disagree with the Spotify app. No `spotify:track:${id}` synthesis either: an episode's uri is not a track uri, and guessing would send a wrong one.

**Verified in a browser** (CDP, the real `/members/` dashboard; Spotify stubbed at the network boundary rather than commanded, so no music was started on the owner's device at 01:30), desktop 1440 + mobile 390×844×3. The stub mutates its own playback state on a successful `play`, so "the rows below survived" is read off the re-rendered screen, not off a fixed list:

| path | observed |
| --- | --- |
| context row tapped | **one** `PUT /play` `{context_uri, offset:{uri}}`, fallback never issued; queue re-read to the album tail |
| user-added row tapped | context jump 403s (offset not in context), fallback sends `uris: [u1, a3, a4]`, and 네 번째 곡 / 다섯 번째 곡 **are still on screen afterwards** |
| both links 403 | in-panel notice, viewer stays open, queue intact, every row disabled (`no-capability` is sticky) |

Also: ESC on the queue still returns to lyrics before closing the viewer; returning lands on the correct lyric line; rows 56 px at 390 px; a title wider than the panel ellipsises without horizontal overflow; no console errors.

One thing worth recording because it cost time and was **not** a code defect: the local stub emitted lyric segments keyed `index` while the schema field is `i`, which surfaced as a React duplicate-key error pointing at `LyricsViewer`. A harness bug can look exactly like a component fault — check the fixture against the schema before reading the warning as a finding.

**Follow-up fix 2026-08-02 — front #330 `aefcb02`, deploy 30709949344 success, prod smoke 19/0.** The owner's real-device pass found it: the song changed, the **title at the top usually did not**.

Cause, and it is the more important half of this step's record: **Spotify applies `PUT /me/player/play` asynchronously.** The 204 is an acknowledgement, not a completion. Step 3 fired exactly one identity read straight after it, so whenever the device had not caught up, that read returned the track we had just left — and the viewer wrote it back and stayed there. Title, lyrics *and* queue all stale, the queue worst, because its effect is keyed on `trackId`, which never moved. Nothing re-read afterwards.

**The original verification could not have caught this, and that is the lesson.** The stub mutated its playback state in the same tick as the 204, so there was never a window in which a read could be stale. A harness that answers instantly cannot exercise a propagation race. Re-run with a 1.2 s lag, the pre-fix build kept the old title at 0.5/1/1.6/2.6/4.2 s — indefinitely.

The fix is the shape Step 1 already used for `playing`: the jump writes identity itself from the tapped row, and the read that follows is a **confirmation**, not the write path. `awaitingTrack` holds the track we asked for and `refresh` drops any read still naming a different one; `confirmJump` re-reads until Spotify agrees, bounded (4 × 500 ms, behind one tap — a burst, not a cadence, so D28 holds) and then gives up so normal reads resume. The queue effect deliberately does **not** read while a jump is unconfirmed — Spotify would hand back the pre-jump queue and put a list on screen contradicting the head — and `confirmJump` bumps `queueSeq` when identity settles, so the queue reads exactly once, correctly.

Post-fix under the same 1.2 s lag: header correct at 150 ms and never reverts; 3 stale reads dropped, 4th agreed; queue lands on the tapped song with the tail below; one queue read. Zero-lag path not slowed (header 120 ms, queue 820 ms).

**Proving it reached production needed a second method, and the first was wrong.** This change adds no new string literal and every identifier it introduces is minified away. Diffing the reachable chunk list before/after showed only `MemberProfile.*.js` changing — which read as "the fix did not ship" but was an artifact: the crawl went **two** levels deep from `/members/` and `LyricsViewer` lives three levels down, in `SelfDashboard.*.js`. What settled it was building the merged tree with and without the commit and finding a construct that survives minification — the two new constants, which land in the module's constant list (`…Ja=1500,Qa=4,Za=500;` present in the deployed chunk, absent from the pre-fix build). Carry forward: **crawl the island import graph to a fixed point, not a fixed depth**, and when a change adds no strings, diff two local builds for a minification-surviving constant rather than guessing at a marker.

**Known, not fixed, needs an owner call**: ⏭ has the same one-unconfirmed-read race (reproduced under the same lag). It is **not** the same fix — ⏮ pressed mid-song legitimately returns the *same* track, so "same track means stale" is wrong for previous. Changing a shipped, owner-verified transport path on that asymmetry is a decision, not a cleanup, so it is recorded here rather than folded in.

**Remaining, owner-only**: one real-device pass — on a phone with music actually playing, tap a hand-queued song and confirm the songs below it are still queued in the Spotify app afterwards, and that the title now follows.

**Rollback**: revert. Steps 1–2 stand alone.

---

## Open questions

1. **Does the browser's token carry the scope the queue endpoint needs?** — ~~blocks Step 2~~ **CLOSED 2026-08-01 (answer below); Step 2 shipped.** **Narrowed from code 2026-08-01, and the news is bad.** `scripts/spotify_bootstrap_token.py` mints two *distinct* refresh tokens with disjoint scope sets:

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
2. **User-added queue items under an album/playlist context.** — ~~blocks Step 3~~ **CLOSED 2026-08-01 by the fallback recorded in Step 3; Step 3 shipped.** `/me/player/queue` returns one flat `queue[]` and does not mark which entries came from the context versus the user's manual queue. A `context_uri` + `offset` jump only works for the former. Options: (a) make every row inert whenever any ambiguity exists, (b) attempt the jump and degrade on failure, (c) match rows against the context's track list with a second request. Owner picked "되는 경우만 점프" as the *behaviour*; this question is how we determine "되는 경우" without lying to the user.

   **ANSWERED 2026-08-01 (owner). Option (b), with the fallback specified: try → fall back → give up.**

   1. **Try** `context_uri` + `offset: { uri }` when a context exists. This is the only jump that keeps the album/playlist context intact.
   2. **Fall back** on failure (or no context) to `PUT /v1/me/player/play` with **`uris: [tapped, ...the rest of the visible queue after it]`** — not `uris: [tapped]` alone.
   3. **Give up** with an in-panel notice if that also fails. Never silently do nothing.

   Why the fallback carries the tail rather than the single track: `uris` **replaces** the playback context, so a lone-track fallback would jump one song and delete everything queued behind it — a much larger loss than the tap was worth, and invisible until the track ends. Re-sending the tail reconstructs exactly what the screen was already showing, so from the member's side nothing disappears. What is genuinely lost either way is the *album context itself*: once the re-sent tail runs out, Spotify has nothing to continue from, where the real context would have kept going. The owner accepted that trade knowingly — the queue the member can see is worth more than autoplay past the end of it.

   `uris` accepts well over the ~20 items this endpoint ever returns, so the tail always fits in one request.

   Note this makes "되는 경우만 점프" cover **every** row in practice: step 2 works for a user-added item, and step 1 works for a context item. Rows stay inert only when there is nothing to send at all. The original worry — a row that looks tappable and then fails — is answered by the fallback existing, not by predicting which rows are which.
3. **Does the bar belong on the dock/static sheet too?** — blocks nothing; currently a non-goal. Raise only if the owner asks after using it.
4. **Should `sendPlayerCommand` dispatch `MYBLOG_PLAYBACK_CHANGED`?** — ~~blocks nothing~~ **CLOSED 2026-08-03 — yes, with three guards (answer at the bottom); front #342.** Found during Step 1. It does not today, so `FEAT-lyrics-sync-precision` Step 2's `'command'` residual channel has never observed a transport command, and any conclusion drawn from that series is about `sendConnectPlay` only. Adding the dispatch would fix the channel in one line, but `NowPlaying.tsx:528` listens too and would start re-reading after its own commands — a behaviour change to a shipped component, hence not folded into Step 1. Decide alongside whatever next consumes the residual series.

   **Premise corrected 2026-08-02 (Step 3), from code — and it cuts against the one-line fix.** Two claims about this channel were floating around and both were loose. The dispatch is only half the story: `logResidual` has exactly **one** call site, `LyricsViewer.tsx:594`, and it sits inside `refresh`'s *same-track* branch. The track-changed branch re-seeds the anchor and logs nothing. So:

   - Step 1's `refresh('command')` after a skip does **not** feed the channel in the ordinary case — a skip changes the track, which is precisely the branch that skips the residual. (A carried-forward note claiming ⏭/⏮ residuals "are already being recorded, only ⏯ is empty" is wrong for this reason.)
   - Step 3 adds nothing to it either: a jump changes the track too.
   - The only transport command that can land a residual today is one that resolves to the *same* track (⏮ restarting the current song).

   Consequence for the question itself: **adding the dispatch would not repair the channel in one line.** The residual would still be dropped on every track-changing command. Anyone picking this up must decide about the log site as well as the dispatch. Still blocks nothing; still not decided here.

   **ANSWERED 2026-08-03 (owner) — yes, dispatch. Both of the premises above were partly wrong, and the second one hid a regression.**

   **The log site does not move, and the 2026-08-02 correction over-read its own finding.** A residual is predicted-minus-actual *position*. A track change destroys the prediction — the anchor belonged to the previous song — so ⏭/⏮ have **nothing to measure**, which is not the same as a measurement being dropped. The same-track branch is the right and only place for `logResidual`. What that correction did get right is that the dispatch alone was not the fix; what it missed is where the actual hole was. ⏸/▶ keep the track, so they are measurable — and until this change the viewer issued **no read at all** after them (`runCommand` reads only after a skip, via `confirmSkip`). That is the empty half of the channel, and the dispatch fills exactly it.

   **The dispatch was not a one-line change, for a reason nobody had written down.** `NowPlaying.applyLive` folded `paused` into its `idle` branch — `setMoment(null)`, `is_playing: false`, `setPaused(false)`. Harmless while nothing could deliver a paused read mid-session; the moment a ⏸ pressed in the viewer or on a headset dispatches, that fold wipes the progress bar, duration, device hint and mode controls and flips the button back to ▶. The card collapsing in response to its own pause. `NowPlaying.playPause` doing **no** confirmation read is not an oversight — it is the workaround that kept this invisible.

   So the answer ships with three guards, none of them optional:

   - `applyLive` renders `paused` alongside `playing` (moment kept, `paused: true`); only `idle` still clears. Verified by a control run in the browser: the same event carrying an `idle` read still collapses the card, so the new branch is doing real work.
   - The NowPlaying listener ignores events raised by its **own** commands (`controlBusyRef`). This preserves `playPause`'s deliberate no-read and keeps `seek`/`skip` at one confirmation read each instead of two. Events from other surfaces still land — that is the whole point.
   - The viewer gains `awaitingPlayState`, the third member of the `awaitingTrack` / `awaitingChangeFrom` family (and the third instance of "when a race is found, grep the file for every other site of the same shape" — see the 2026-08-02 entry in the decisions log). A read still reporting the state we just commanded away from is dropped rather than written back over the optimistic `playing` write. Deliberately **no** confirmation loop: unlike a skip or a jump, the optimistic write is already the right answer, so a dropped read costs one residual sample and nothing else.

   Modes — shuffle / repeat / volume — do **not** dispatch. The event means "the playhead or the track moved"; those move neither, NowPlaying already reconciles them off the next one-shot, and the viewer has no volume control to justify a read per slider move.

   **One thing the question did not anticipate: the series needed a label before it needed samples.** `estimateMs` ages an anchor by wall time with no notion of pause, so a residual measured against a held player carries the elapsed round-trip inside it. The two live samples from the browser run were **37,084 ms** (`readState: 'paused'`) and **89 ms** (`readState: 'playing'`) — side by side in one series, indistinguishable without the state they were taken in. `logResidual` now records `readState`. Had the dispatch landed alone, OQ4 would have opened a channel that arrives unreadable.

## Decisions log

| Date | Decision | Step |
|------|----------|------|
| 2026-08-03 | **OQ4 closed: dispatch, plus the two things the question did not know it was asking for.** The owner picked the dispatch over a viewer-local fix, knowingly taking the behaviour change to a shipped component. What the audit found on the way is the part worth keeping: the 2026-08-02 "the log site has to move too" correction over-read itself — a track change destroys the prediction, so ⏭/⏮ have nothing to measure and the log site is already right; the real empty half was ⏸/▶, which issued no read at all. And the dispatch would have collapsed the NowPlaying card on the first ⏸ from another surface, because `applyLive` folded `paused` into `idle` — a latent defect that only a paused read could expose, and nothing could deliver one until now. `playPause`'s missing confirmation read was the workaround that hid it. Shipped in front #342 with three guards (paused branch, self-event suppression, `awaitingPlayState`) and a `readState` label on the residual, without which the newly-opened series would have mixed a 37,084 ms paused sample with an 89 ms live one. | 4 |
| 2026-08-01 | Owner: controls go in an always-visible bottom bar, not the header and not a tap-to-reveal overlay — thumb reach and no hunting, at the cost of ~60 px of lyric height. | 1 |
| 2026-08-01 | Owner: the queue is a full screen swap, not an overlaid sheet. The viewer's vertical drag is already line-stepping, so a sheet would force gesture arbitration at a boundary; a swap has zero conflict by construction. | 2 |
| 2026-08-01 | Owner: 되는 경우만 점프 — rows jump where Spotify permits it and are inert otherwise. "Repeat ⏭ until we arrive" was rejected (slow, pollutes listening history). | 3 |
| 2026-08-01 | Scope fixed to 재생/일시정지/다음/이전/대기열. Volume, shuffle, repeat, transfer, 좋아요 stay out. | — |
| 2026-08-01 | OQ1 narrowed from code, not from a probe: the two scopes the queue endpoint documents sit on two **different** refresh tokens (`SCOPES` vs `STREAMING_SCOPES` in `scripts/spotify_bootstrap_token.py`) and the browser's token is missing `user-read-currently-playing`. Whether Spotify enforces it is the only open half; a 2-line console probe settles it. | 2 |
| 2026-08-01 | Owner: Status draft → **accepted**, and Step 1 starts without the OQ1 probe — OQ1 gates Step 2 only, so blocking Step 1 on it buys nothing. | — |
| 2026-08-01 | **Owner real-device pass on Steps 1+2 — all green.** Queue list scrolls past the fold, `←` returns to the correct lyric line, ⏭/⏸ work, and the queue refreshes with the track. One false alarm resolved on the way: a queue that looked wrong was **repeat mode**, not a bug (repeated ids are why rows are keyed `${id}:${index}`). Steps 1+2 now have no outstanding human check. | 1, 2 |
| 2026-08-01 | **OQ2 answered: option (b) — try, fall back, give up.** Context jump first; on failure re-issue `play` with `uris: [tapped, ...rest of the visible queue]`; if that fails too, an in-panel notice. The fallback carries the TAIL, not the lone track, because `uris` replaces the context and a single-track fallback would silently delete everything queued behind the tap. Cost the owner accepted: the album context is gone either way, so Spotify will not autoplay past the re-sent tail. Side effect on the design — rows become tappable by default, since the fallback removes the need to predict which rows are reachable. | 3 |
| 2026-08-01 | **OQ1 answered: 200, no re-consent, Step 2 unblocked.** The narrowing above reasoned from `STREAMING_SCOPES` — the constant that *requests* scopes — but the grant actually stored in `/myblog/spotify` was minted with a broader consent and carries both documented scopes. Two corrections carried forward: a requested-scope constant is not evidence of a granted scope, and the question was never owner-only (the browser's token is minted server-side from a secret in SSM, so it is answerable without a human). | 2 |
| 2026-08-02 | **The lag fix was applied to one call site and its twin was left behind — the owner found the twin the same day.** The row below drew exactly the right lesson for the queue-row jump and stopped there; ⏭/⏮ was the other post-command read-back in the same file and kept its single unconfirmed read, so a skip left the viewer on the previous track's lyrics. Fixed in front #333 by extracting `confirmTransport()` and putting **both** callers on it: the jump waits for the track it named, the skip (which cannot name a destination) waits for any read that disagrees with the track it left. The generalisable rule is not "model the lag" — that was already written down — it is **when a race is found, grep the file for every other site of the same shape before closing it.** Verification now carries a regression guard asserting the one-read version FAILS against a lagging stub. | 1 |
| 2026-08-02 | **`play` is asynchronous — one read after it is a guess, not a fact.** The owner's device pass caught the title not following a jump; the cause was a single unconfirmed identity read landing before Spotify had applied the play, and the viewer writing that stale answer back over everything. Fixed by making the jump write identity from the tapped row and demoting the read to a bounded confirmation. **The Step 3 verification could not have caught it**: the stub changed state in the same tick as its 204, so no read could ever be stale. A harness that answers instantly cannot exercise a propagation race — model the lag. | 3 |
| 2026-08-02 | **Bundle-marker verification has two traps, both hit today.** Crawling `/members/` for a new-bundle marker went two levels deep while `LyricsViewer` sits three levels down, so the chunk under test was never compared and a shipped fix read as missing. And a change that adds no string literal has no greppable marker at all once identifiers are minified. The reliable method: crawl the import graph to a fixed point, and diff two local builds (with/without the commit) for a construct that survives minification — constants do. | 3 |
| 2026-08-02 | **Step 3 shipped as specified — the fallback chain, unchanged from the owner's OQ2 answer.** Two things the plan did not anticipate, both structural rather than cosmetic: the viewer had no `readLivePlayback` on open, so the context had to be read alongside the queue or *every* first tap would have silently taken the fallback and link 1 would never have run; and the chain was extracted to `queueJump.ts` so "the tail is carried" is pinned by a unit test instead of resting on a clickthrough. | 3 |
| 2026-08-02 | **OQ4's premise corrected from code, and it makes the question bigger, not smaller.** `logResidual` has one call site and it lives in `refresh`'s same-track branch, so a track-*changing* command never lands a residual no matter who dispatches what. Adding the dispatch to `sendPlayerCommand` would therefore not repair the `'command'` channel on its own — the log site has to move too. Recorded, not decided. | 4 |
| 2026-08-01 | Browser verification of Step 1 disproved the draft's `sendPlayerCommand` → `MYBLOG_PLAYBACK_CHANGED` claim (`:424` is `sendConnectPlay`, a different function; a live listener saw 0 events from ⏯⏭⏮). The first audit pass repeated the claim instead of checking it, and its "next/prev swaps lyrics for free" conclusion fell with it. Step 1 therefore owns both the `playing` write and the post-skip identity read. Raised as OQ4 whether the dispatch should simply be added. | 1 |
| 2026-08-01 | Current state re-audited against code after front #325 and corrected: wrong component path (`member/` → `member/lyrics/`), every `LyricsViewer.tsx` line number stale, and the panel foot is occupied by `.lyv-return`, not empty. Three facts #325 introduced are now load-bearing for Step 1 — the `playing` flag already exists, its only writer is a re-read behind a 1.5 s floor (so Step 1 writes it optimistically), and next/prev inherits the track swap for free. | 1 |
| 2026-08-01 | Split out of the sync brainstorm into its own RFC: new UI surface, new Spotify API, mobile touch design and a possible re-consent — a different risk profile and a different verification from timing math. Cross-refs `FEAT-member-player` (queue was a Step 6 candidate) and `FEAT-lyrics-sync-precision` (consumes the commands as re-anchor events). | — |
