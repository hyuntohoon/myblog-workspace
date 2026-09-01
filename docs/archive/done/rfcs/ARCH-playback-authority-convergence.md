# ARCH-playback-authority-convergence: one playback truth, consumed by every surface

- **Status**: **done** (2026-09-01 — Steps 1–4 all shipped and production-verified; archived).
  Owner promoted the Status in-session on 2026-09-01 under CLAUDE.md rule #7's explicit-approval
  exception; accepted in-session 2026-08-30, Steps 1–4 as drafted, and executed as drafted with no
  step dropped or added (item-level scope *was* corrected inside Steps 1 and 4, and
  `myblog_front#431` shipped as an out-of-list Step 3 addendum — both recorded below). Last
  shipment: Step 4, `myblog_front#436` (`13373a1`), deploy run
  `33456804663` green, prod smoke **30 passed / 0 failed**. OQ4 (`BOUNDARY_BUFFER_MS`) closed **not
  by answering it** but by moving it to `plan.md` → Backlog as work in its own right (owner,
  2026-09-01); the three residual risks in OQ3 stay recorded and unfixed, by the same decision that
  recorded them. Reopen with a fresh `plan.md` row rather than editing this file.
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

**SHIPPED 2026-08-30** — `myblog_front#428`, squash `e075f73`, deploy run `33299620786` green,
production smoke **30 passed / 0 failed**. It merged *after* `SEC-member-listening-data-boundary`
Step 1 (owner, 2026-08-30), as sequenced: the live read-boundary defect was not left open while a
playback refactor landed ahead of it.

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

**Result**: `pnpm lint` clean, `astro check` 0 errors, `pnpm test` 70 files / 757 tests, **0
skipped**. The clickthrough ran against a dev server with a stub backend and an in-page stub of
`api.spotify.com` + the Web Playback SDK, the Spotify stub modelling the ack→apply lag so a
"one read after the command" bug cannot pass. Two tabs shared one browser context, so the ownership
lease and the `BroadcastChannel` were real. It **found a defect Step 1 had left** — see the
decisions log — and the fix shipped in the same PR.

The authed *deployed* bundle still cannot be driven directly (mixed content blocks the http token
relay), so liveness used a **counting** marker: the takeover copy occurs exactly once across 49
crawled JS chunks, where the pre-fix tree carried it twice. Note for whoever repeats this: the
member islands are `astro-island component-url` references, not `<script src>` — a `src=`-only
crawl stops at 19 files and reports the marker missing.

**Rollback**: revert the PR. Front-only, no contract, no persisted state.

---

### Step 2 — queue execution invariant

Closes **D1, C2**, and the rest of **C1**.

**SHIPPED 2026-08-30** — `myblog_front#430`, squash `dd1fe82`, deploy run `33312780594`.
The invariant is asserted directly in the suite (issued URI list === visible order from the
current row onward) and confirmed in a real browser against a control on `origin/main`.
Detection hangs off `bucketStore.subscribe` rather than the six mutation call sites, so a
seventh path added later cannot land outside it. What review caught after the first commit,
and the three residual risks that were recorded instead of fixed, are in the decisions log and
open questions below.

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

### Step 3 — UX state correctness — **SHIPPED 2026-08-31**

Closes **E1–E5, G1**. Shipped as `myblog_front#434`; see the Decisions log
for what review and the clickthrough changed, and the correction to E5 below.

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

**Narrow residual SHIPPED 2026-08-30** — `myblog_front#431`, squash `087dc047`, deploy run
`33316040634` green, production smoke **30 passed / 0 failed**. One Step 1 residual discovered after
Step 2 was handled without pulling the rest of Step 3 forward: a live mirror may move lyric `focus`
for visual browsing, but because it cannot seek real playback it must not re-anchor the
playback-relative clock to the tapped line. Mirror line taps use
the existing browse/suspend path and preserve the live anchor; the static/debug entry keeps its
purely local navigation semantics. Only an accepted real seek may move the live anchor.

**Verification**: `pnpm lint && pnpm exec astro check && pnpm test` with regressions for paused
browse, resume-after-paused-browse, recoverable 404, episode row, initial-paused, volume
last-write-wins, and a mutation-sensitive mirror line-tap regression that returns from the tapped
line to the unchanged live anchor after the existing browse timeout; real-browser clickthrough for
the volume drag, the device-appears recovery, and the mirror browse-return path.

**What that list missed, recorded because it missed it again.** As in Step 2, the defects review
found were on paths this list does not name — this time because splitting `busy` into `busy` +
`transportBusy` silently disarmed every *other* predicate that had relied on transport setting
`busy`. The list names the controls the step adds; it does not name the controls the step *stops
protecting*. A future step's list should enumerate the readers of any flag whose meaning it narrows.

**E5, corrected against a real browser.** "Opening 가사 from a paused Global Player shows ⏸" is
narrower than written: the `useState(true)` seed is overwritten by the session-adoption effect
before first paint whenever `currentSpotifyTrackId()` can name the track, and a control run on
`origin/main` rendered ▶ from frame 0. The seed only lies in the A4 condition — a cold URI cache,
where the session cannot name what is sounding. The fix stands (a seed must not assert something
false, and the session is this RFC's single writer of playback truth), but it is a narrow fix, not
the broad one the wording implied.

The mirror browse-return path shipped ahead of this step as `myblog_front#431` with its own
regression, and that regression still passes here — paused browse removes the idle timer only while
the music is stopped, and that test browses against a playing mirror.

**Deliberately not fixed, recorded instead** (same standard as Step 2's residual risks — an
untested guard claiming a fix is worse than a recorded risk):
- a throw inside a coalesced run drops the remembered press. No reachable thrower today:
  `sendPlayerCommand`, `play` and `resolveTail` all swallow.
- `transportBusy` is not broadcast, so a mirror's `aria-busy` is dead for a forwarded press.
- depth 1 inside the `'transport'` family drops a *different* command, not just a repeat:
  ⏭ → ⏯ → ⏭ loses the ⏯. Giving them separate keys would let two writers reach one playhead, which
  is worse; "every press lands" needs an ordered queue with one in-flight slot, not a bigger slot.
- the episode backstop in `queueJump` returns `nothing-to-send`, which renders no sentence — a
  silent no-op for a jump forwarded from a mirror running an older bundle.

---

### Step 4 — cleanup — **SHIPPED 2026-09-01**

Closes **G2–G6**. Shipped as `myblog_front#436`; the corrections this step made to the RFC's own
Current-state claims are below, and the residual it recorded rather than fixed is at the end.

`useLyricsDocument(trackId)` is the one lyrics document lifecycle: the read, the loading/error
phase, the translation row, the local 요청됨 override, the 번역 default, and `isKoreanDominant`.
`LyricsViewer` and `LyricsSheet` each keep only what is theirs — the sheet keeps its two typography
modes, the annotation treatment, which annotations are open and 전문 복사; the viewer keeps focus,
the clock anchor, browse/suspend, display style and the queue view. Translation status refreshes on
a visibility return, on an explicit 확인 press, and on a bounded three-attempt burst while the row
is `requested`; there is no interval, and the burst is armed once per pending episode. `트랙 정보`
renders only where a destination is passed. `전체 가사` hands off from the live viewer to the
static sheet, wired in both hosts.

**Two Current-state claims were wrong, and the audit that found them is why this step's list is
shorter than the RFC's.**
- **G6 was already closed.** The RFC said `lib/entityEvents.ts:131` states the
  `ENT_OPEN_LIVE_LYRICS` listener only exists in `SelfDashboard`. It does not — Step 1 corrected
  that comment, and `origin/main` says the opposite in as many words. The stale comment this step
  actually found is in `playbackEntryActions.ts`, which told the next reader that `uris.ts`'s
  memoised `null` was Step 4's work; F1 shipped in **Step 1** and a transient failure is no longer
  remembered at all.
- **G2 is two render sites, not three.** Both are in `PlaybackPanel.tsx` (the desktop entry row and
  the mobile entry strip), and both call sites — `PocketTray` and `PocketBuckit` — passed
  `NOOP_PLAYBACK_ENTRY`.

**G5 required fixing the member.css trap for the fifth time.** Every `.lys-*` and `.ctx-*` rule
lived in `member/layout.css`, which only `SelfDashboard` and `MemberProfile` import. The live
viewer's app-wide host is `PocketBuckit` (mounted from `layout.astro` on every page), so a sheet
opened by 전체 가사 anywhere but the dashboard would have rendered with zero of its rules. They
move verbatim to `styles/lyricsSheet.css`, imported by `LyricsSheet.tsx` itself. Order-safe by
construction: those two prefixes appear in no other stylesheet, so nothing outside the new file
targets these elements, and relative order is preserved byte-for-byte — `.lys-note` and `.lys-line`
are each declared twice and the later declaration is load-bearing. The memo-window dock HOST rules
stay in `layout.css`; they are genuinely dashboard-scoped and target neither prefix.

**What this step stops protecting** — the enumeration Step 3's own retrospective asked the next step
to write before its verification list, not after:

| Removed / narrowed | Readers | Disposition |
|---|---|---|
| `NOOP_PLAYBACK_ENTRY` (deleted) | `PocketTray`, `PocketBuckit` | both updated; grep is 0 |
| `onOpenTrackInfo` now optional | `PlaybackEntries`, the mobile strip, `PlaybackMini` (forwards `PlaybackEntryProps`) | both render sites guarded; `PlaybackMini` renders no entry row of its own |
| the viewer's local `phase`/`trOverride`/`showKo`/`requesting`/`loadSeq` | the whole component | typed — `astro check` is the guard |
| `useLyricsSheetState`'s return shape | `LyricsSheetContent`, `ContextPanel`'s lyrics pane | every existing key kept; `checkingTr`/`recheckTr` added |
| `.lyv-tr-state` / `.lys-tr-state` | none once the 요청됨 chip became a button | rules deleted |
| `role="status"` on the 요청됨 chip | nothing asserted it | the state is now the button's own label |
| `.lys-*` / `.ctx-*` leaving `layout.css` | `LyricsSheet`, `ContextPanel`, `AlbumDetail`, `annotations.ts` | all reach the new file through `LyricsSheet.tsx`'s import |

**Verification**: `pnpm lint` clean, `pnpm exec astro check` 0 errors, `pnpm test`
**875 tests / 0 skipped** (855 before). Real-browser clickthrough **against a control on
`origin/main`**, both driven by the same stub backend, and it discriminated on every check:

| Check | control (`origin/main`) | shipped |
|---|---|---|
| `트랙 정보` in the playback panel | present, and pressing it left DOM shape, dialog count and URL identical — the dead button | absent |
| `전체 가사` in the live viewer | absent | present; opens the sheet and closes the viewer |
| the sheet's styling on a NON-dashboard route (`/`) | — | fully styled, in a document where `.memo-modal.has-dock` (the `layout.css` remainder) is not defined at all |
| a translation finishing while the viewer is open | after the poller answered `done`, a tab return AND a manual ↻, still `요청됨` and zero Korean 9s later | `요청됨 · 확인` became `번역` and all three lines showed Korean on the tab return |

**The mutation sweep earned its place again**: 20 mutants, 19 killed. The survivor was shown to be
an *equivalent* mutant rather than a gap — adding `translation` to the burst effect's deps changes
nothing, because `recheck` only replaces state when the status actually changed, and two mutants
that make the burst a REAL poll (a `setInterval`, and a last attempt that re-arms itself) were both
killed. Four more survived a first pass and the tests were strengthened until they did not: a
dropped press reported as success, `aria-live` moved off the wrapper, `전체 가사` re-gated on
`settingsReady`, and that gate removed entirely.

**Review blocked the first commit for the third step running, and again on paths this step's list
does not name.** Six findings, each fixed with a regression that kills its own mutant: `requestTr`
was the one async write in the hook without the epoch guard the rest of the file uses twice (an
answer for track A could land on B, and Step 4's own `pending` machinery would then arm a burst and
a visibility listener against it); a dropped double-press was reported as success, so the caller
wiped an unrelated notice; the bounded burst set `checkingTr`, so the control greyed itself out
three times unbidden — the burst being invisible is the whole justification for it not being a
poll; the arrival was silent, on the surface whose entire purpose is that the translation arrives;
`전체 가사` was gated on "synced lyrics exist" and so hid on the tracks whose sheet is most worth
opening; and the order-safety premise stated here was overstated (`.ctx-` does still appear in
`layout.css`) in a way a future move would have leaned on.

**And the fix for the silent arrival was itself wrong, which only the browser caught.** Putting
`aria-live` on each branch's own `div.lyv-tr-cluster` looks right — React reuses the node — but the
ATTRIBUTE goes with the branch, so the region stopped being a region at the exact moment it had
something to announce. Verified live: same node, `getAttribute('aria-live')` → `null`. One wrapper
per surface now, with a regression on both. The lesson is the Step 1 one restated: a render
property is not verified by reading the render.

**A defect this step introduced and an existing test caught.** Moving the read into the hook makes
"seed the clock from an effect on `phase`" the obvious shape, and it is wrong: it puts the anchor
one commit behind the lyrics, so the list paints focused on line 1 with no anchor and anything the
member does in that window is overwritten by the seed landing behind it. The hook takes an
`onLoaded` callback that runs in the load's own batch instead.

**A pre-existing flake, measured before it was touched.** `LyricsViewer.transport.test.tsx` failed
about 1 full-suite run in 10 with "the browse step did nothing" — which reads exactly like a browse
regression. Measured on `origin/main` as well: **1/10 there, 1/10 here**, so it was not this step's.
Instrumenting `origin/main` until it reproduced gave the mechanism: `findByText` resolves off a DOM
mutation, which React fires at commit, before that commit's passive effects run; the follow
scheduler's effect then runs *after* the test's interaction carrying the pre-interaction
`suspended`, and pulls the focus back to the anchor's line. The four tests that interacted in that
window now settle the mount first, as `open()` already did. **Recorded because it costs something**:
those un-settled interactions were, by accident, the only guard on the narrower invariant above —
that the seed lands in the load's batch rather than one commit later. A test written to replace it
by watching the DOM failed to kill its own mutant and was deleted rather than kept as decoration.
**Review then supplied the version that works**: the invariant is the HOOK's contract, not the
viewer's, and asking what the last RENDERED phase was when `onLoaded` ran discriminates
deterministically — `loading` in the load's own batch, `ready` from an effect. So the trade did not
have to be accepted after all.

**Two more flakes, both in this step's own new tests, both found by repetition rather than by any
green run** — the 20-run measurement taken to confirm the fix above, and the 12-run one taken to
confirm the review fixes. One dispatched `visibilitychange` before the effect registering the
listener had flushed; one asserted an ORDER before the passive effect recording the second event had
run. Same class as the pre-existing one, same fix, mutation re-checked so neither lost its teeth.
Repetition after each: **25/25** and **20/20** full-suite runs green.

**Rollback**: revert the PR. Front-only, no contract, no persisted state.

---

**All four steps are shipped.** The RFC's `Status` stays `accepted`: promoting it is the owner's
call, not Claude's. What remains before it can be archived is that decision plus OQ4
(`BOUNDARY_BUFFER_MS`), which has been open for four steps and still blocks nothing.

> **Superseded 2026-09-01.** Both were resolved at closeout: the owner promoted the Status to `done`
> and moved OQ4 to `plan.md` → Backlog as `MEASURE-playback-boundary-buffer`. The paragraph above is
> kept as written at the time. Note that the removed `plan.md` row called `BOUNDARY_BUFFER_MS`
> "OQ3"; **this file numbers it OQ4**, and OQ3 is the three residual risks.

## Open questions

1. ~~**Step 2's reissue glitch** — a future-tail mutation mid-playback restarts the current track
   and seeks back (~200–400ms audible).~~
   **Answered 2026-08-30 — (a), accept the glitch.** Every mutation applies live: append, reorder
   and delete alike. (b) and (c) were declined because the invariant the owner asked for is
   "visible order is the next order", and deferring reorder/delete to the next track breaks it
   silently — the failure mode this step exists to end. Two mitigations keep the glitch off the
   common path, and neither is a compromise on the invariant: only rows AFTER the current one are
   in the signature (reordering already-played rows costs nothing), and a reissue while paused is
   deferred to the next resume rather than performed, since starting audio nobody asked for is
   worse than the wait.
2. ~~**Does the mirror tab's lyrics transport disable, or offer takeover inline?**~~
   **Answered 2026-08-30 — both, from one component.** The mirror renders the transport disabled
   *and* an inline takeover, and `PlaybackOwnerBanner` moved out of `PlaybackPanel.tsx` into its own
   module so the lyrics viewer imports the component rather than the hand-copied markup Step 1
   first shipped. `className` re-lays it out for the lyrics transport grid; the copy, the action and
   the predicate are single-sourced.
3. **Residual risks Step 2 accepted rather than closed.** Recorded here because
   review raised them, they were investigated, and none is fixed:
   (a) `adoptLive`'s completion gate deletes the previous row when the live URI
   differs and the playhead is within `BOUNDARY_BUFFER_MS` of the end — and a reissue
   restores the playhead to exactly that region. A guard was written for it and then
   **removed**: the scenario could not be reproduced in the harness (the adoption that
   actually runs during a reissue sees a position near zero, not near the end), and an
   untested guard claiming a fix is worse than a recorded risk. (b) A bucket reorder
   repaints the whole server tree (`PocketBuckitProvider`), so one landing while a
   queue `PUT /reorder` is still in flight can paint the pre-reorder order and cost one
   spurious reissue, then a second when the truth arrives. (c) A tab promoted to owner
   inherits an executing list it cannot know; Step 2 drops its baseline rather than
   reissuing, so a promoted tab that is never edited again plays out the list the
   previous owner left. All three are audible-glitch or stale-order-until-next-edit
   shaped, none is a data risk.
4. **Is `BOUNDARY_BUFFER_MS = 1500` still right as a burst gap?** It is flagged in
   `FEAT-playback-bucket-player` as an unmeasured estimate. Blocks nothing; Step 1 should measure
   it against the residual series the viewer already logs rather than inherit it.
   *(Two things in that sentence are wrong, and the closeout below is what disproves them: it is not
   a burst gap — the burst gap is `COMPLETION_CONFIRM_GAP_MS = 500` — and the residual series cannot
   measure it. Left standing because it is what the question asked at the time.)*
   **Still open after all four steps, and deliberately so** — it was kept out of every one of them
   rather than folded into whichever happened to touch that code. It needs an owner decision on
   whether the measurement is worth a session of its own.
   **Resolved procedurally, not substantively, on 2026-09-01: the owner moved it to `plan.md` →
   Backlog as work in its own right.** The value is still unmeasured. What the closeout added is the
   thing that decides whether measuring is worth it — *where a wrong value actually lands*, read off
   the code rather than assumed.

   **The two uses are not independent; one calls the other.** `scheduleBoundaryCheck()`
   (`session.ts:2194-2211`) arms only while `isOwner && rung === 'remote' && playing`, and fires at
   `Math.max(500, remaining + BOUNDARY_BUFFER_MS)`. What it fires is `confirmCompletion()`, which
   calls `adoptLive()` — and `adoptLive()` is where the deleting gate lives
   (`session.ts:1081`, `positionNow() >= previousDurationMs - BOUNDARY_BUFFER_MS` → `deleteBucketItem`).
   So the constant sets **both** the instant the check happens and the tolerance it is judged by, and
   `positionNow()` keeps extrapolating from the anchor by wall clock while `playing`
   (`session.ts:2164-2168`). Raising it defers the read *and* loosens the gate: by the time the read
   lands, `positionNow()` is well past `duration` and the `completed` test is close to free, leaving
   "the URI changed" plus `!anchorAmbiguous` as the real protection. A mid-track skip performed on
   another device — which raises no `MYBLOG_PLAYBACK_CHANGED` in this tab — is first observed by
   exactly this scheduled read.

   **An earlier draft of this paragraph said the scheduler "costs one redundant read, never a false
   removal", citing the comment above the constant. Both halves were wrong, and review caught it.**
   That sentence is not the comment above the constant (`session.ts:1006-1010`, which only says the
   value is a first-pass estimate); it is the rung-1 block comment at `session.ts:2180-2182` — and
   `session.ts:2184` records that `BOUNDARY_BUFFER_MS` was *later* reused inside `adoptLive()` by
   BUG-26. The comment was written before a destructive delete was put on that path, so it cannot be
   cited to rule one out. The honest statement is narrower: **the removal decision is
   `adoptLive()`'s, and the scheduler chooses the instant it is evaluated at.** (The cost of a wrong
   guess is also not one read — `confirmCompletion` runs up to `COMPLETION_CONFIRM_TRIES = 4` reads
   spaced `COMPLETION_CONFIRM_GAP_MS = 500`.)

   That is the same window as OQ3(a), where a reissue restores the playhead into exactly this
   region — so the two open questions are one question, and measuring the constant is the only way to
   size the risk that was recorded rather than fixed. This is why it went to Backlog rather than
   being closed outright. The measurement route and the full sweep set live in the `plan.md` row.

## Decisions log

| Date | Decision | Step |
|------|----------|------|
| 2026-08-30 | Current-state audit against `origin/main` confirmed all 23 items still present; none had been fixed since the reports | — |
| 2026-08-30 | Owner: write the RFC and run Step 1 (Phase 1) this session; `SEC-member-listening-data-boundary` sequenced ahead | 1 |
| 2026-08-30 | Owner accepted the RFC in-session, Steps 1–4 as drafted | — |
| 2026-08-30 | Owner resolved the sequencing the two decisions above left open: Step 1 is implemented in `myblog_front#428` but **merges after** `SEC-member-listening-data-boundary` Step 1 | 1 |
| 2026-08-30 | Owner (OQ2): the mirror keeps a disabled transport **and** an inline takeover, and the two surfaces stop duplicating it — `PlaybackOwnerBanner` extracted to its own module and imported by `LyricsViewer` | 1 |
| 2026-08-30 | Step 1's browser clickthrough found A3 half-open on the jump path: `JumpOutcome` dropped `rung`/`degraded`, so a cold-start jump left `rung: null` — no 음질 제한 notice and every mirror read `ownerRung: null` and kept a live transport. Fixed in the same PR | 1 |
| 2026-08-30 | Owner (OQ1): **(a)** — accept the ~200–400ms reissue glitch and apply every queue mutation live, rather than let reorder/delete take effect only from the next track | 2 |
| 2026-08-30 | Owner: `takeOver()` on `external` playback transfers the audio into this tab **only when `ownerRung === 'in-page'`** — that sound lives in the other tab's SDK device and dies with its lease. On a Connect device only the lease moves: raising a quality-limited browser device, or re-issuing the live track as a one-URI list (which discards the album context), would each take something away to gain nothing | 2 |
| 2026-08-30 | Step 2's queue-change detection hangs off `bucketStore.subscribe`, not the six mutation call sites — the queue is a projection over that store, so a seventh path added later cannot land outside the invariant | 2 |
| 2026-08-30 | Review blocked Step 2's first commit with three reproducible defects, all on the **takeover** path with two tabs — which the Step 2 verification list does not name and the clickthrough therefore never exercised. `takeOver()` moved the lease but not the audio in the only state its button renders in; the position restore was forwarded to the tab being deposed and dropped; and a failed reissue's debt was written off by the next track change. Fixed in the same PR | 2 |
| 2026-08-30 | `takeOver()` branches on **where the sound is** (`ownerRung`), not on whether the queue is driving it: the banner renders only while the owner holds the in-page device, so "inside the other tab" is the common case, not the exotic one | 2 |
| 2026-08-30 | A newly reported Step 1 residual split static navigation from live-mirror browsing: the combined `!canRefresh || !canControl` branch re-anchored a mirror's clock to a position Spotify never sought. Mirror line taps now preserve playback truth and use the existing temporary browse path; the regression advances the browse timeout and therefore fails if the fake `setAnchor(tappedPosition)` write returns | 3 |
| 2026-08-31 | Capability splits three ways, not two: `unsupported`/`forbidden` durable (disable), `no-active-device` recoverable (clears when a device appears), `transient`/`token` retry. The recoverable one must never write `rememberSpotifyTransportProbe` or degrade `capabilityTier` — both are durable claims about the account, and a sleeping phone is not one | 3 |
| 2026-08-31 | `busy` splits into `busy` (a play that cannot coalesce — surfaces disable) and `transportBusy` (a coalescing command in flight — surfaces stay pressable). Review found the trap: every predicate reading `busy` to mean "some player command is running" silently stopped protecting anything, so a lyrics queue-row jump / 전체재생 / row ▶ / 다시 시도 could each issue a second `play({uris})` across an in-flight ⏭. One shared predicate, `nonCoalescingBlocked`, now states the asymmetry in a single place | 3 |
| 2026-08-31 | Follow resumes on ↩ or on playback resuming, and a re-anchor is neither — but only while the member is actually browsing. Gating `applyAnchor` on `!isPlaying` alone also skipped `setFocus`, which made a manual ↻ on a paused track a visual no-op | 3 |
| 2026-08-31 | E5's reach corrected downward against a real browser (see Step 3). Recorded rather than quietly dropped, because the RFC's own Current-state wording was the thing that was wrong | 3 |
| 2026-09-01 | Two of Step 4's own Current-state claims were wrong: **G6 was already closed by Step 1** (the RFC's description of `entityEvents.ts:131` was the stale thing, not the comment), and G2 is **two** render sites, not three. The stale comment Step 4 actually found was `playbackEntryActions.ts` calling F1 "Step 4's" when F1 shipped in Step 1 | 4 |
| 2026-09-01 | G5 forced the **fifth** fix of the member.css trap: `.lys-*`/`.ctx-*` lived in dashboard-only `member/layout.css`, so a sheet mounted from the site-wide `PocketBuckit` would have rendered unstyled. Moved verbatim to `styles/lyricsSheet.css`, imported by the component that emits the classes | 4 |
| 2026-09-01 | `showKo` lives in `useLyricsDocument` despite the "data only" boundary: its value is *derived from the document*, the derivation was duplicated verbatim in both screens, and G3 needs the refresher and that derivation together for a completed translation to reveal itself | 4 |
| 2026-09-01 | Review blocked the first commit for the third step running. The finding that mattered most was again a reader nobody re-counted: `requestTr` was the one async write without the epoch guard, and Step 4's new `pending` machinery is what turned that pre-existing stale write into three wasted reads against a wrong-track state | 4 |
| 2026-09-01 | A render property is not verified by reading the render. The review fix for the silent translation arrival put `aria-live` on each branch rather than on a wrapper; React reuses the node but not the attribute, so the region stopped being one exactly when it mattered. Only the browser saw it | 4 |
| 2026-09-01 | Three test flakes were diagnosed rather than re-run — one pre-existing (measured at 1/10 on `origin/main` AND on the branch before anything was changed), two of this step's own, both found by repetition rather than by a green run. All three are the same class: interacting with a component before its passive effects have flushed | 4 |
| 2026-09-01 | Owner promoted the RFC to **done** and archived it: all four steps shipped and production-verified, and the RFC's own step list was executed as drafted — nothing dropped, nothing added | — |
| 2026-09-01 | Owner (OQ4): move `BOUNDARY_BUFFER_MS` to `plan.md` → Backlog rather than close it. Closing outright was declined because the closeout read the constant's consumers and found `adoptLive()`'s completion gate deletes a queue row on it, sharing its window with OQ3(a) — an unmeasured constant is what makes that recorded risk unsizeable | — |
| 2026-09-01 | OQ3's three residual risks are archived unfixed, exactly as Step 2 recorded them. They are not promoted to Backlog: each is audible-glitch or stale-order shaped, none is a data risk, and (a) could not be reproduced in the harness. Whichever future work touches that code owns them | — |
