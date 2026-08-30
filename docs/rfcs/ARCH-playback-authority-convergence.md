# ARCH-playback-authority-convergence: one playback truth, consumed by every surface

- **Status**: **accepted** (owner-approved in-session 2026-08-30, Steps 1–4 as drafted)
- **Owner**: 오너
- **Created**: 2026-08-30
- **Plan row**: `plan.md` → ARCH-playback-authority-convergence

---

## Goal

What Spotify is actually playing, and what `playbackSession`, the Global Player, the Playback Panel,
the Playback Bucket, `LyricsViewer`, `NowPlaying` and Media Session each believe, converge on one
value. Concretely: `LyricsViewer` stops being a second playback state machine with its own
ack→apply tracking, its own transport, and its own capability model; every playback mutation in the
product — including seek, queue jump, mode changes, volume, device transfer and takeover — passes
the same ownership gate; and the order visible in the Playback Bucket is the order that actually
plays next.

Verified against `myblog_front@origin/main` (`94d82f1`) on 2026-08-30. Every "Current state" claim
below was re-derived from the code, not from the RFC that shipped it.

## Non-goals

- **The lyrics rendering engine is not touched.** The boundary-scheduled focus timer, the
  `BLUR_LEAD_MS`/`FLAT_LEAD_MS` split, `applyCenter`'s transform centring and the WebKit
  measure-cache all stay exactly as they are. This RFC moves the *playback correctness* boundary
  out of `LyricsViewer`; it does not restyle or re-time the lyrics.
- No new polling loop anywhere. Permitted triggers stay: SDK push, `MYBLOG_PLAYBACK_CHANGED`,
  `visibilitychange`, a natural track boundary, a bounded confirmation burst, an explicit refresh.
- `playbackSession` does not absorb Spotify HTTP/SDK detail. Provider specifics stay in
  `lib/spotifyPlayback.ts`; the session stays orchestration + state authority.
- `LyricsViewer` and `LyricsSheet` stay two screens. Only their data lifecycle is considered for
  extraction (Step 4), never their UI state.
- Member listening-data privacy is **not** in this RFC — see
  `SEC-member-listening-data-boundary`, which the owner sequenced ahead of this one.

## Current state

Twenty-three defects, all reproduced in `origin/main`. Grouped by the invariant they break.

### A. `LyricsViewer` is a second playback controller

- **A1 — a lyric line tap never seeks.** `moveFocusTo` does `setAnchor({ms: start, …})` +
  `setFocus(next)` and issues no provider command. Real playback stays at 1:10 while the viewer's
  clock runs from 2:35.
- **A2 — the parallel state machine.** `awaitingTrack`, `awaitingChangeFrom`, `awaitingPlayState`,
  `confirmSkip`, `confirmJump`, `refreshQueued`, `endSynced`, `transportDead`, `commandBusy`, plus
  direct `sendPlayerCommand()` and `readLivePlayback()` calls. Every one of these exists to track
  Spotify's ack→apply lag *for commands this component issued behind the session's back*.
- **A3 — ownership is bypassed.** `LyricsViewer` never reads `canControlPlayback`. In a mirror tab
  whose owner is on rung 2, the Global Player's transport is disabled while the viewer's ⏮/⏯/⏭ and
  its queue-row jump are live.
- **A4 — session identity is refused.** The Step 3c effect returns early when
  `playbackSession.currentSpotifyTrackId() !== trackId`, so a session that authoritatively knows the
  track is now C cannot move a viewer sitting on B.
- **A5 — rapid external changes are dropped.** `EVENT_RESYNC_FLOOR_MS = 1500` is a leading-edge
  throttle with no trailing call. A→B→C inside 1.5s leaves the viewer on B permanently.
- **A6 — confirmation failure leaves the optimistic state.** `confirmJump`/`confirmSkip` both
  discard `confirmTransport`'s boolean. Budget exhausted ⇒ Spotify=A, viewer=B, forever.

### B. Reconciliation is single-shot where it must be bounded-retry

- **B1 — natural completion.** `session.ts`'s `scheduleBoundaryCheck` fires exactly one
  `adoptLive()` at `duration + BOUNDARY_BUFFER_MS`, and only on rung `remote`; `LyricsViewer` fires
  exactly one `refresh('end')` at `durationMs + END_GRACE_MS`. A read that lands inside Connect's
  propagation window reports the old track and nothing asks again — the same race
  `confirmTransport` was written for, unpaid on the natural path.
- **B2 — repeat-one is invisible.** `spotifyPlayback.ts`'s `player_state_changed` listener returns
  early when `trackId === lastSdkTrackId`, so A→A (repeat track) dispatches no
  `MYBLOG_PLAYBACK_CHANGED` at all and the lyrics clock stays parked on the last line.

### C. The ownership gate is partial

- **C1 —** gated: `playAt`, `togglePlay`, `next`, `previous`, `seekTo`. **Not gated:** `setMode`
  (shuffle / repeat / volume), `transferTo`, the device picker and its "이 브라우저" raise. A mirror
  tab can therefore raise a second in-page SDK device while the lease sits in another tab.
- **C2 — `takeOver()` takes the lease without moving playback.** It does
  `ensureOwner()` then `rowIndex(current.currentItemId)`; during external playback that id is
  `null`, the index is `-1`, and `playFrom` is never called. The previous owner is deposed and
  nothing moves.

### D. The visible queue is not the queue that plays

- **D1 —** `playFrom(index)` issues `play({kind:'uris', uris: <whole tail>})` **once**. After that,
  appending, reordering or deleting a *future* row updates `bucketStore` and the server
  (`PUT /api/buckets/reorder`, `DELETE`) and never reaches Spotify. `onRemoved` returns immediately
  unless the removed row is the current one; `onDropped` returns immediately when anything is
  playing. At the next natural boundary Spotify plays the tail it was handed at press time.

### E. Capability, busy and identity are modelled as booleans that cannot recover

- **E1 —** `sendPlayerCommand` maps **both 403 and 404** to `no-capability`; `LyricsViewer` latches
  that into `transportDead`, which nothing ever clears. "No active device" (recoverable the moment
  the Spotify app opens) is thus indistinguishable from "not Premium" and disables transport until
  the viewer is closed.
- **E2 —** `runCommand`/`jumpTo` open with `if (commandBusy.current || transportDead) return`, while
  the buttons carry only `disabled={transportDead}`. A ⏭⏭ double-tap silently discards the second
  press.
- **E3 —** `setMode` opens with `if (modeBusy) return null`. A volume drag discards every value
  issued while a request is in flight, including the last one.
- **E4 —** `QueueEntry` carries no media type and `toEntry` deliberately keeps episodes, so the
  queue screen renders `it.uri ? <button>` and an episode row is tappable — while
  `readLivePlayback` classifies an episode as `idle`. The two models contradict each other.
- **E5 —** `OpenLiveLyricsDetail` carries no play state and `LyricsViewer` seeds
  `useState(true)`. Opening 가사 from a paused Global Player shows ⏸ and advances the scheduler over
  silence.

### F. URI resolution loses identity and remembers transient failures

- **F1 —** `uris.ts`'s `fetchUri` returns `null` for `!res.ok` **and** for a thrown fetch, and
  `resolveUri` memoises that `null` for the tab's lifetime. One 500 or one dropped connection makes
  a perfectly good track permanently unplayable until reload.
- **F2 —** `resolveTail` returns a bare `string[]` after `.filter()`. If row A fails to resolve and
  B, C succeed, Spotify is told to play `[B, C]` while `playFrom` records `head.itemId = A` as
  current. Session identity and audio disagree from the first note.

### G. Silent failures and dead UI

- **G1 —** `openPlaybackLyrics` reads `cachedUri(row.trackId)` only and `return`s on a miss, so the
  가사 button's behaviour depends on whether the panel's idle prefetch happened to have run.
- **G2 —** `트랙 정보` is rendered in three places (`PlaybackEntries`, the mobile sheet) wired to
  `NOOP_PLAYBACK_ENTRY`.
- **G3 —** a finished translation never reaches an open viewer: `requestTr` writes `trOverride` and
  nothing re-reads status until the track changes.
- **G4 —** `LyricsViewer` and `LyricsSheet` each implement `getLyrics` + loading/error +
  translation status + `isKoreanDominant` (the latter's own comment calls itself "mirror of
  LyricsViewer OQ3").
- **G5 —** no handoff from live lyrics to the full reading sheet.
- **G6 —** stale comment: `lib/entityEvents.ts:131` states the `ENT_OPEN_LIVE_LYRICS` listener only
  exists in `SelfDashboard`. It is in `PocketBuckit.tsx`; `SelfDashboard` has not listened for it
  since `ARCH-global-playback-experience` Step 2.

## Target state

```
Spotify
  ↓
lib/spotifyPlayback.ts      provider adapter — HTTP, SDK, token, capability taxonomy
  ↓
lib/playback/session.ts     the ONLY writer: identity, queue cursor, play state, anchor,
                            duration, device/rung, ownership gate, reconciliation
  ↓
GlobalPlaybackBar · PlaybackPanel · Playback Bucket · LyricsViewer · NowPlaying · Media Session
                            consumers — read state, call session actions, own only their own UI
```

`LyricsViewer` keeps: the lyrics document, `focus`, temporary browse state, translation UI, display
style, queue-view UI state. It keeps its own `readLivePlayback()` **only** as the fallback for the
case the session genuinely cannot serve — a track whose URI the session has not resolved, so
`currentSpotifyTrackId()` is null. The principle is `session-confirmed identity > viewer-local
guess`, not "the viewer never reads".

## Steps

One step per session. Steps run in order; Step 2 depends on Step 1's gate work.

### Step 1 — correctness foundation

**Merge order**: implemented in `myblog_front#428` and held there. It merges *after*
`SEC-member-listening-data-boundary` Step 1 (owner, 2026-08-30) — the live read-boundary defect is
not left open while a playback refactor lands ahead of it.

Closes **F1, F2, A1, A3, A4, A5, A6, B1, B2**, and the C1 half that Step 2 needs.

1. `uris.ts` — split durable from transient. `fetchUri` returns a discriminated result
   (`{kind:'uri'} | {kind:'unmapped'} | {kind:'transient'}`); only `unmapped` (a 404 / an explicit
   null `uri`) is memoised. Transient results are not cached, or cached with a short TTL.
2. `resolveTail` returns identity-aligned rows —
   `{ resolved: Array<{itemId, trackId, uri}>, failed: string[] }`. `playFrom` names
   `resolved[0].itemId` as current, never the requested head.
3. `playbackSession` gains the mutation surface `LyricsViewer` needs, each behind the existing
   `gate()`: `jumpToQueueEntry`, and the ownership gate extended over `setMode`/`transferTo`.
4. `LyricsViewer` line tap → `playbackSession.seekTo(start_ms)`; success re-anchors, failure
   reconciles against a live read instead of running an independent clock. Swipe / wheel / ↑↓ stay
   visual-only browse and issue nothing.
5. `LyricsViewer`'s ⏮/⏯/⏭ and queue jump route through `playbackSession`, so ownership,
   `localWriteSeq` and the confirmation burst are the session's — `awaitingTrack`,
   `awaitingChangeFrom`, `awaitingPlayState`, `confirmSkip`, `confirmJump` and `refreshQueued`
   delete rather than move. In a mirror tab the transport renders disabled with the existing
   `PlaybackOwnerBanner` takeover affordance, never enabled-then-silent.
6. Event coalescing becomes leading + trailing: first event reconciles immediately, further events
   inside the floor set `dirty`, and the floor's end fires exactly one more reconcile. Owned by
   the session, so every consumer inherits it.
7. Natural completion reuses `confirmTransport` as a bounded burst (settles on: a different track,
   `idle`, or a same-track restart near 0). `player_state_changed` additionally dispatches when the
   track id is unchanged but position has jumped backwards past a discontinuity threshold — the
   repeat-one epoch.
8. The Step 3c session-adoption effect drops the `currentSpotifyTrackId() !== trackId` early return
   and instead **adopts** a session-confirmed identity change by loading the new lyric document.

**Verification**:
```
pnpm lint && pnpm exec astro check && pnpm test
```
plus the regression suite named under "Tests" below (line tap, line-tap failure, swipe,
natural remote transition, repeat-one, rapid external skip, jump-confirmation failure, mirror-tab
transport, transient-500 resolver, identity-aligned tail), and a real-browser clickthrough of the
viewer against live playback.

**Rollback**: revert the PR. Front-only, no contract, no persisted state.

---

### Step 2 — queue execution invariant

Closes **D1, C2**, and the rest of **C1**.

The invariant, stated first and asserted in tests: *the order visible in the Playback Bucket is the
order that plays next.*

Chosen execution model — **reissue current + tail on mutation, with position restore**
(the RFC's option B), because it is the only candidate that behaves identically on rung 1 (Connect
remote, where there is no push signal and a missed boundary would strand playback) and rung 2. A
future-tail mutation while playing marks the queue dirty and, debounced past the end of a drag,
issues `play({kind:'uris', uris:[current, …newTail]})` followed by `seekTo(positionNow())`. While
paused the reissue is **deferred** to the next resume rather than performed, since reissuing would
start audio the member did not ask for.

Rejected: **one-track-at-a-time app-controlled continuation.** It requires the app to detect every
natural boundary and start the next track itself; on rung 1 that detection is a scheduled timer, and
a single missed fire is silence rather than a wrong order. It also breaks Spotify-side
repeat/shuffle outright. Rejected: **Spotify's native queue API** — it has no reorder or delete, so
it cannot represent an app queue (the `FEAT-playback-bucket-player` non-goal already says this).

`takeOver()` is reordered so the lease follows a successful transfer instead of preceding it: on
`external` playback it transfers the live track to this tab, and only a successful transfer
promotes the lease. A failed takeover leaves the previous owner intact.

**Verification**: `pnpm test` including append-while-playing, append-while-paused, append after the
current row was originally last, reorder of the future tail, delete of a future row, duplicate
tracks, delete-current, natural completion, ownership change; each asserting visible order ===
issued URI order. Real-browser: reorder the Playback Bucket mid-track and confirm the next track is
the reordered one; the current track's position is preserved across the reissue.

**Rollback**: revert the PR. Behaviour reverts to the shipped one-shot tail.

**Open question — see OQ1.** The reissue costs a brief restart of the current track (Spotify's
`play` has no "replace tail, keep playing" form). The owner may prefer the divergence to the glitch.

---

### Step 3 — UX state correctness

Closes **E1–E5, G1**.

Capability splits along the axis `lib/playerCapabilityMatrix.ts` and the session's device axis
already model: `unsupported`/`forbidden` (durable, disable), `no-active-device` (recoverable
runtime state — the controls come back when a device appears), `transient`/`token` (retry). The
provider stops folding 403 and 404 into one reason. Busy stops being a silent return: transport
uses a latest-intent coalescer so ⏭⏭ works, and everything that cannot coalesce renders disabled
while it is busy. `QueueEntry` gains a media type; episodes render non-tappable, consistent with
`readLivePlayback` treating them as `idle`. Initial play state comes from the `playbackSession`
snapshot rather than growing `OpenLiveLyricsDetail`. `openPlaybackLyrics` awaits `resolveUri` on a
cache miss and surfaces a failure instead of returning. Paused browse stops auto-returning: follow
resumes on ↩ or on playback resume, never on a 3s idle timer while the music is stopped.

**Verification**: `pnpm lint && pnpm exec astro check && pnpm test` with regressions for paused
browse, resume-after-paused-browse, recoverable 404, episode row, initial-paused, volume
last-write-wins; real-browser clickthrough for the volume drag and the device-appears recovery.

---

### Step 4 — cleanup

Closes **G2–G6**. Translation status refreshes on visibility restore / explicit refresh / a bounded
slow retry while `pending`, never on a timer. `useLyricsDocument(trackId)` extracts the shared data
lifecycle from `LyricsViewer` and `LyricsSheet` (data only — no UI state). A 전체 가사 보기 handoff
from live lyrics to the sheet. `트랙 정보` hidden until it has a destination. Stale comments,
`entityEvents.ts:131` included, corrected against the code.

---

## Open questions

1. **Step 2's reissue glitch** — a future-tail mutation mid-playback restarts the current track and
   seeks back (~200–400ms audible). Alternatives are (a) accept the glitch, (b) accept that
   reorder/delete only take effect from the next track, (c) apply only *appends* live and defer
   reorder/delete. Blocks Step 2's final shape, not its start. Recommendation: (a) — the invariant
   the owner asked for is "visible order is the next order", and (b) silently breaks it.
2. **Does the mirror tab's lyrics transport disable, or offer takeover inline?** Blocks Step 1's
   mirror UX only. Recommendation: reuse `PlaybackOwnerBanner`'s existing takeover, so the two
   surfaces answer identically.
3. **Is `BOUNDARY_BUFFER_MS = 1500` still right as a burst gap?** It is flagged in
   `FEAT-playback-bucket-player` as an unmeasured estimate. Blocks nothing; Step 1 should measure
   it against the residual series the viewer already logs rather than inherit it.

## Decisions log

| Date | Decision | Step |
|------|----------|------|
| 2026-08-30 | Current-state audit against `origin/main` confirmed all 23 items still present; none had been fixed since the reports | — |
| 2026-08-30 | Owner: write the RFC and run Step 1 (Phase 1) this session; `SEC-member-listening-data-boundary` sequenced ahead | 1 |
| 2026-08-30 | Owner accepted the RFC in-session, Steps 1–4 as drafted | — |
| 2026-08-30 | Owner resolved the sequencing the two decisions above left open: Step 1 is implemented in `myblog_front#428` but **merges after** `SEC-member-listening-data-boundary` Step 1 | 1 |
