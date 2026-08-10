# ARCH-global-playback-experience: unify remaining playback state, one app-wide lyrics host, playlist-style Playback Bucket detail

- **Status**: draft
- **Owner**: TBD
- **Created**: 2026-08-10
- **Plan row**: `plan.md` → ARCH-global-playback-experience
- **Depends on**: `docs/rfcs/ARCH-buckit-navigation-shell.md` Step 1 (`BucketDetailShell`'s
  `playback_queue` empty slot) for the Playback Bucket's playlist detail placement. This RFC's other
  work (state unification, lyrics host) has no dependency on that RFC.
- **Extends, does not redo**: `docs/archive/done/rfcs/FEAT-playback-bucket-player.md` (done
  2026-08-10, all 9 steps shipped — the Playback Bucket, its mini/expanded player forms, single-tab
  ownership, and the drop-source wiring already exist in production) and
  `docs/rfcs/ARCH-entity-interaction-domain-audit.md` Step 3 (3a/3b/3c done — partial `session.ts`
  adoption by `NowPlaying`/`LyricsViewer`, identity+anchor only). This RFC is the continuation those
  two explicitly left unbuilt, not a rewrite of either.
- **Reuses, does not touch**: `lib/dockTear.ts` (already extracted and used by `PlaybackPanel.tsx` for
  the docked↔floating expanded-player physics — see Current state) and `lib/surfaceGeometry.ts`
  (`ARCH-movable-resizable-surfaces`, move/resize) — **the playback panel does not gain move/resize in
  this RFC.** That capability stays scoped to the memo modal and the Lyrics/Research-Notes context
  panel per that RFC's own non-goal.

---

## Goal

Most of "a global playback experience" already shipped under `FEAT-playback-bucket-player`: a
system-owned Playback Bucket, a mini-player and an expanded (docked/floating/mobile-sheet) player form
sharing one session, single-tab ownership with transfer and crash recovery, and drop sources reaching
the queue from most of the product. What remains, verified against current code rather than assumed
from the feature's name: (1) `lib/playback/session.ts` still does not own capability tier, device
list/transfer, shuffle, repeat, volume, liked-state, or reconnect flow — `NowPlaying.tsx` keeps all six
locally, by design, and a single `MYBLOG_PLAYBACK_CHANGED` event still triggers three uncoordinated live
reads (`session.ts`/`NowPlaying`/`LyricsViewer`) with no single-flight coalescing; (2) the live lyrics
viewer's open event (`ent:open-live-lyrics`) is dispatched from the app-wide-mounted Pocket tray, but
its only listener is inside the dashboard-scoped `SelfDashboard`, so lyrics cannot open from any
non-dashboard route; (3) the Playback Bucket's queue view has transport, per-row play/remove, duration,
and current-track indication, but no per-row artwork thumbnail, no play-all/track-count/total-duration
summary, and no in-list reorder; (4) reaching the mini/expanded player at all still requires opening
the Pocket tray — there is no zero-interaction persistent bar. After this RFC: `session.ts` is the
single owner of the six remaining state axes with `NowPlaying`/`LyricsViewer` as pure subscribers, live
reads are single-flight and shared, lyrics open from any route, the Playback Bucket's playlist detail
has artwork/summary/reorder, and a persistent compact playback surface is reachable with zero
navigation from any route including Home — the specific form (always-visible bar vs. easier-to-reach
Pocket entry) is an open owner decision, not pre-decided by this document.

## Non-goals

- **A second player, a second queue, or duplicated playback state.** `lib/spotifyPlayback.ts` stays the
  only SDK/token owner; `play(intent)`/`playbackSession.replaceQueueAndPlay` stay the only entry points.
  A review gate for every step here is a grep proving no new `api.spotify.com` string appears outside
  `lib/spotifyPlayback.ts` — the same gate `FEAT-playback-bucket-player` Step 6 used.
- **Home-specific playback or lyrics state.** Home gains reachability to the *existing* session and
  lyrics host, not a Home-only mini player or a Home-only lyrics surface.
- **Polling, in any form.** D28 stays upheld unchanged — every read this RFC adds is 1:1 with a user
  action, a track boundary, or an existing event, never a timer loop.
- **Replacing `FEAT-lyrics-sync-precision`'s sub-100ms anchor logic.** `LyricsViewer.refresh()`'s
  identity/jump/skip-confirmation/translation/cover/meta logic is untouched; this RFC's only lyrics-host
  change is *where* the viewer mounts, not how it tracks sync.
- **Move/resize on the playback panel.** Stays out of `ARCH-movable-resizable-surfaces`' scope per that
  RFC's own non-goal; this RFC does not reopen it.
- **The Playback Bucket's own nav-tree placement, header chrome, rename/trash/color.** Owned by
  `ARCH-buckit-navigation-shell`'s `BucketDetailShell` — this RFC only fills that shell's
  `playback_queue` body slot with the enhanced playlist detail.
- **Backend/contract change unless artwork genuinely cannot be delivered through the existing
  response.** See *Data/API/contract impact* — the audit below found the existing `BoardAlbum.cover`
  field already present; a contract change is not currently justified, and this RFC does not add one
  unless implementation proves otherwise.
- **`ARCH-entity-interaction-domain-audit`'s open Step 5** (memo naming) and its `useDismissable`
  backdrop/portal question (OQ4) — unrelated surfaces, not reopened here.

## Domain terminology and invariants carried in

- **Rung** (1 = Spotify Connect remote control, no in-page device; 2 = in-page Web Playback SDK device)
  and **degraded** (rung 2 must self-report as quality-limited) — `FEAT-member-player`/
  `FEAT-playback-bucket-player` vocabulary, unchanged.
- **D28 — no polling, ever.** Carried from `FEAT-member-player`, reaffirmed by every playback RFC since.
- **"The Buckit queue plays by re-issuing its own tail"** (`play({kind:'uris', uris:[n…end]})`) — never
  writes to Spotify's own queue. Unchanged.
- **Single-tab ownership governs rung 2 (writes) only** — every tab is an equally valid rung-1 remote;
  the lease governs who owns the SDK device and issues transport, not who may see or edit the queue.

## Current state (verified against `myblog_front`, this session)

### What `lib/playback/session.ts` already owns

`PlaybackSessionState` (`lib/playback/session.ts:69-95`): `currentItemId`, `external` (non-queue live
playback), `playing`, `anchor` (`ClockAnchor`, shared with the lyrics viewer), `durationMs`, `rung`,
`degraded`, **`device` — a single currently-active `PlaybackDevice`, read-only projection, not a device
list or a transfer control**, `notice`, `busy`, and the tab-ownership triad `isOwner`/`ownerPresent`/
`ownerRung`. This is queue + transport + tab-lease state. It is **not** capability tier, not a device
picker, not shuffle/repeat/volume, not liked-state, and not reconnect flow — confirmed by grep
(`capabilityTier`, `shuffle`, `repeat`, `volume` as state fields: zero hits in `session.ts`).

### What `NowPlaying.tsx` still owns locally, by design

Per `docs/frontend/component-map.md`'s own **State-owner registry** (added
`ARCH-entity-interaction-domain-audit` Step 1, most recently updated 2026-08-06 after Steps 3a/3b/3c
shipped): `NowPlaying`'s `useNowPlaying()` subscribes to `playbackSession` via `useSyncExternalStore`
**for track-identity + anchor only** (Step 3b, front #361); **"tier/mode/like/device/reconnect stay
independently local by design."** `LyricsViewer.tsx` similarly adopts `playbackSession`'s anchor/
playing/durationMs **only when `currentSpotifyTrackId()` confirms the same track**, and its own
`refresh()` (`readLivePlayback()`-driven) stays the untouched primary/fallback source for everything
else — identity, jump, skip-confirmation, translation, cover, meta (Step 3c, front #374).

**The open gap this RFC closes is stated in the registry itself, not inferred**: *"Still open:
`readLivePlayback()` itself is not single-flight/cached — a single `MYBLOG_PLAYBACK_CHANGED` still fans
out to 3 uncoordinated HTTP reads (`session.ts`/`NowPlaying`/`LyricsViewer`), recorded but not
attempted by any of the [Step 3a/3b/3c] fixes."* This is the authoritative, dated (2026-08-06) statement
of exactly what remains — this RFC's Step 1 is that fix, not a new discovery.

### Live lyrics host — dashboard-scoped, confirmed

`ENT_OPEN_LIVE_LYRICS` (`lib/entityEvents.ts:140`) is dispatched from `PocketTray.tsx` (`openPlaybackLyrics`
prop wired to both `PlaybackMini` and `PlaybackPanel`'s 가사 entry — `PocketTray.tsx:922,1105`) — and
`PocketTray`'s host, `PocketBuckit`, is mounted **app-wide** at `layout.astro:81`
(`client:only="react"`, present on every route including Home, per `src/pages/index.astro`'s use of
`Layout.astro`). But the **only** listener is `window.addEventListener(ENT_OPEN_LIVE_LYRICS, onOpen)`
inside `SelfDashboard.tsx:168-169` — and `SelfDashboard` mounts only inside the member dashboard route,
not at the layout level. **The hypothesis is confirmed exactly as stated**: the event is app-wide, the
host that actually opens `LyricsViewer` is dashboard-local. Opening 가사 from Home, `/search`, an
artist hub, or any non-dashboard route today dispatches an event nobody is listening for — a silent
no-op, not a visible error.

### Playback Bucket detail — substantially built, three concrete gaps

`PlaybackPanel.tsx` (438 lines) + `PlaybackMini.tsx` (61 lines) already ship: transport (▶⏸⏭⏮, disabled
appropriately), a progress bar, per-row play (`playbackSession.playAt(row.itemId)`), per-row remove
(gated `removable`, `deleteBucketItem` + `playbackSession.onRemoved`), per-row duration
(`formatDuration`), and current-track indication (an animated eq icon vs. a zero-padded position
number, `PlaybackPanel.tsx:255-273`). The docked↔floating expanded form already uses
`useDockTear` (`PlaybackPanel.tsx:8,395`) — the tear/dock physics `FEAT-playback-bucket-player` Step 6
recorded as "extracted from `DockableLyricsSheet`, not re-implemented" is confirmed live in the current
file, and it is a **separate** `useDockTear` call from `ContextPanel.tsx`'s (`ARCH-album-context-panel`)
— two independent hosts of the same hook, as designed; this RFC does not merge them.

**Three things the queue rows do not do today**, verified by reading `PlaybackQueue` directly
(`PlaybackPanel.tsx:249-280`):

1. **No per-row artwork.** The row renders position/eq, title, duration — no `<img>`, and `row.cover`
   is never read inside `PlaybackQueue` (it *is* read once, for the single "current" identity block via
   `PlaybackIdentity`, `:53-72`, with a resolve-on-miss fallback — but not per list row).
2. **No reorder.** Rows have a play button and a remove button; no drag handle, no `draggable`, no
   up/down control.
3. **No play-all / track-count / total-duration summary.** There is no header above the row list; the
   closest existing concept is `PlaybackMini`'s "다음 N곡 더" (`more` count) at the bottom of a
   3-row-limited preview, which is a truncation hint, not a summary.

**Artwork is not a contract gap.** `BoardAlbum.cover` (`lib/buckets.ts:61` for the general shape, `:264`
for the queue-row-adjacent shape, both `cover: string | null`, populated at `:198`/`:292` from
`ar?.photo_url`/`a?.cover_url`) already carries a direct cover URL on every board-projected row,
including playback-queue members (which are `TrackBrief`-serialized per `FEAT-playback-bucket-player`
Step 2's own note that "playback tiles off the shared `TrackBrief`"). Rendering N queue-row thumbnails
is therefore **N `<img src>` tags against already-fetched URLs, zero additional network requests** —
the "artwork delivery without frontend N+1" requirement in scope is satisfiable with **no backend or
contract change**, contrary to what the feature description's phrasing ("any required track artwork
contract extension") might suggest before verification. This RFC's artwork step is front-only unless
implementation finds a specific row shape where `cover` is null and no fallback resolves (matching the
existing `resolveDbAlbumId` pattern already used for `external` playback's album-info action).

### Reaching the player at all still costs interaction

Pocket (`PocketBuckit`) is mounted app-wide but renders `open`/closed via its own `usePocket()` state,
toggled by `PB_TOGGLE_EVENT`/a tray button, not auto-opened. The Playback Bucket's mini-player renders
inside that bucket's own tray "drawer" (`PocketTray.tsx`'s `openDrawer`/`isDrawerOpen`, a per-bucket
expand state within the open tray), so **today, seeing the mini-player from an arbitrary route requires
opening Pocket, then opening that specific bucket's drawer** — not a zero-click persistent bar. This
partially confirms and partially corrects the "Pocket already provides persistent playback mini and
expanded queue surfaces" hypothesis: the *surfaces* exist and are reachable from every route (Pocket is
layout-mounted), but "persistent" in the sense of "visible without interaction whenever something is
playing" is **not** built. Whether that stronger form is wanted is Open question 1 below — this RFC
does not presuppose the answer.

## Target architecture and state ownership

- **`session.ts` gains six new state fields** — `capabilityTier`, `devices: PlaybackDevice[]` (list,
  distinct from the existing single `device`), `activeDeviceId`, `shuffle`, `repeat`, `volume`,
  `liked: boolean | null`, `reconnect: ReconnectState` — each populated from the same reads
  `NowPlaying` already performs today, moved rather than duplicated. `NowPlaying`'s own
  `useNowPlaying()` becomes a pure `useSyncExternalStore` subscriber for all nine axes (the three it
  already gets plus these six), with its local `useState` declarations for tier/mode/like/device/
  reconnect deleted, not kept as a shadow copy.
- **`LyricsViewer` is unaffected beyond what Step 3c already did** — its sync-critical `refresh()` stays
  primary. This RFC does not touch `FEAT-lyrics-sync-precision`'s territory.
- **Single-flight live reads.** `readLivePlayback()` gains a request-coalescing wrapper (in-flight
  dedupe, matching the existing `lib/playback/uris.ts` resolver's memoised/in-flight-deduped pattern
  from `FEAT-playback-bucket-player` Step 6's own decisions log) so a single `MYBLOG_PLAYBACK_CHANGED`
  produces **one** HTTP read shared by all three current callers, not three.
- **Live lyrics host moves to layout level.** The `ENT_OPEN_LIVE_LYRICS` listener relocates from
  `SelfDashboard` to a component mounted in `layout.astro` (alongside `PocketBuckit`, which already
  dispatches the event it would now answer) or to `PocketBuckit` itself if that avoids a second
  always-mounted React root — implementation detail for Step 2, not decided here. The `LyricsViewer`
  component itself, its data hooks, and its sync logic are unchanged; only its mount trigger moves.
- **Playlist detail enhancements are additive to `PlaybackPanel.tsx`**: per-row `<img>` off the existing
  `row.cover`, a summary header (`N곡 · MM:SS 총 재생 시간`, computed client-side from already-loaded
  `durationSec` — a null duration degrades the total to "—", matching the existing per-row `—` fallback
  at `PlaybackPanel.tsx:101`), a play-all action (`playbackSession.playAt(rows[0].itemId)` — reuses the
  existing per-row play call, not a new session method), and reorder (pointer-based drag reusing the
  `Math.hypot < 6` + `touchAction:'none'` pattern `ARCH-entity-interaction-v2` E5 confirmed as the one
  shipped touch-pointer-drag implementation in this codebase, `PocketTray`'s own — not native HTML5
  `draggable`, which E5 measured as non-functional under touch on this product's surfaces).
- **Persistent reachability** — scoped by Open question 1. If the owner picks the stronger form (a
  thin always-visible bar), it renders a compact identity + transport strip site-wide when
  `session.ts.currentItemId != null || external != null`, independent of Pocket's own open/closed
  state, and clicking it opens the existing `PlaybackMini`/`PlaybackPanel`. If the owner keeps the
  current one-tap-into-Pocket reachability, this RFC's Home-reachability requirement is already
  satisfied by Pocket's existing layout-level mount and this step does not build a new surface.

## UX behavior — desktop and mobile

- **State unification (Step 1)** is invisible by design — no UX change, only a data-source change
  behind the same rendered UI. Verification is behavioral parity (device transfer, shuffle/repeat/
  volume, like-toggle, reconnect banner) plus the new cross-tracker consistency this RFC adds: change
  shuffle from the Playback Bucket panel and confirm `NowPlaying`'s own mode indicator updates without
  its own independent read.
- **Live lyrics (Step 2)**: 가사 opens identically from the Playback Bucket panel (already works, per
  `FEAT-playback-bucket-player`'s Step 8 preflight audit) and now *also* from Home, search, an artist
  hub, or any other route with Pocket present — same `LyricsViewer` sheet, same mobile/desktop layout it
  already has.
- **Playlist detail (Step 3)**: desktop shows the artwork thumbnail + summary header above the existing
  row list; mobile (the 390px full-height sheet, "대기열" tab) gets the same header and thumbnails at
  reduced size, reorder via long-press-drag consistent with the tray's existing touch-drag threshold.
- **Persistent surface (Step 4, gated on Open question 1)**: if built, a thin bar — matching the
  external survey `FEAT-playback-bucket-player` Step 6 already ran (SoundCloud 48px / Apple Music 54px–
  61px at 390 / Genius 80px–107px at 390, "no service puts the queue in that bar") — sits below the
  header on every route, click-through opens the existing mini/expanded forms, no new player logic.

## Data / API / contract impact

**No backend or contract change is planned.** The artwork audit above found `BoardAlbum.cover` already
present on queue rows; the six state fields moving into `session.ts` are moves of existing client-side
reads, not new endpoints; the live-lyrics host relocation and the single-flight read wrapper are pure
frontend. If Step 3 implementation finds a queue-row shape where `cover` is genuinely absent with no
existing resolver (not found in this audit), that becomes a separately-scoped, flagged contract add —
not silently folded into this RFC, per this repo's standing "no contract change unless the audit proves
a payload gap" posture (`ARCH-entity-interaction-v2` non-goal, reused verbatim here).

## Dependency and repository order

Single repo (`myblog_front`) for Steps 1–3. Step 4 (if the owner picks the persistent-bar form) is also
front-only. No cross-repo ordering, no `myblog_backend`/`myblog_music`/`shared_db` involvement expected.
Step 3's Playback Bucket detail placement depends on `ARCH-buckit-navigation-shell` Step 1 shipping
first (the `BucketDetailShell` `playback_queue` slot it renders into) — recorded as this RFC's one
external dependency edge.

## Step and PR boundaries

One step per session (hard rule #4); Steps 1 and 2 have no ordering constraint on each other and may be
taken in either order. Step 3 depends on the sibling RFC noted above. Step 4 is conditional.

### Step 1 — `session.ts` absorbs the six remaining state axes; single-flight live reads

`capabilityTier`/`devices`/`activeDeviceId`/`shuffle`/`repeat`/`volume`/`liked`/`reconnect` move into
`PlaybackSessionState`; `NowPlaying`'s local `useState` declarations for the same are deleted, not
duplicated. `readLivePlayback()` gains in-flight dedupe so one `MYBLOG_PLAYBACK_CHANGED` produces one
HTTP read shared by `session.ts`, `NowPlaying`, and `LyricsViewer`'s own trigger path (not its
sync-critical `refresh()` internals — those stay separate per the non-goal above).

**Verification**: `pnpm test && pnpm lint && pnpm exec astro check` — full `NowPlaying.test.ts` suite
green with zero behavioral changes asserted (device transfer, shuffle/repeat/volume toggle, like,
reconnect banner all still pass against the moved state); a new cross-tracker test asserting a
shuffle/device change from the Playback Bucket panel is visible in `NowPlaying` without a second read;
a new single-flight test asserting exactly one `readLivePlayback()` call per `MYBLOG_PLAYBACK_CHANGED`
dispatch, regardless of how many components are mounted and listening. Real-browser CDP: toggle shuffle
from both surfaces, confirm convergence without reload; lock-screen Media Session still publishes
correctly (indirect verification per Step 3b's own precedent — a full lock-screen click-test needs a
rung-2 device).

**Rollback**: revert the PR. State move only, no persisted data, no contract.

---

### Step 2 — one app-wide live lyrics host

Relocate the `ENT_OPEN_LIVE_LYRICS` listener from `SelfDashboard.tsx` to a layout-level mount point
(exact host — a new tiny always-mounted component, or folded into `PocketBuckit` — decided during
implementation, not here). `LyricsViewer`'s own component and data hooks are untouched.

**Verification**: `pnpm test && pnpm lint && pnpm exec astro check`; real-browser CDP — 가사 opens from
the Playback Bucket panel on Home, `/search`, an artist hub page, and the member dashboard, all four
opening the identical `LyricsViewer` sheet; dashboard-only regression check (existing dashboard-internal
가사 entry points, e.g. `TrackRow.lyrics`, still open correctly post-relocation).

**Rollback**: revert the PR. Pure event-listener relocation, no data change.

---

### Step 3 — Playback Bucket playlist detail: artwork, summary, play-all, reorder **[gated: `ARCH-buckit-navigation-shell` Step 1 merged]**

Add per-row artwork (`row.cover`, no new request), a summary header (track count + total duration,
client-computed), a play-all action, and pointer-based reorder to `PlaybackPanel.tsx`'s `PlaybackQueue`.
Mount the enhanced panel as the `BucketDetailShell`'s `playback_queue` body (the sibling RFC's empty
slot) in addition to its existing Pocket mini/expanded placement — same component, two mount points, no
duplicated state (both read `usePlaybackViewModel()`/`session.ts` directly).

**Verification**: `pnpm test && pnpm lint && pnpm exec astro check`; real-browser CDP — artwork renders
with zero additional network requests (confirm via the browser's network panel: request count before/
after opening a 13-row queue is unchanged); play-all from the summary header starts playback from
position 0; reorder persists across a reload; the same panel opens correctly from both the Pocket
mini-player *and* the new bucket-detail-shell placement without divergent state.

**Rollback**: revert the PR. Frontend-only, additive UI on an existing component.

---

### Step 4 — persistent compact playback surface (conditional on Open question 1)

Only if the owner picks the always-visible-bar form. A thin site-wide strip (identity + transport,
matching the survey's 48–107px reference range) mounted at layout level, visible whenever
`session.ts` reports active/paused playback, independent of Pocket's open state. If the owner instead
accepts Pocket's existing one-tap reachability as sufficient, this step does not run and the RFC closes
at Step 3.

**Verification** (if run): real-browser CDP across every route including Home — bar appears on playback
start, persists across a client-side navigation (no remount/audio interruption — the same
`astro:before-swap` persistence `FEAT-member-player` Step 5b already proved for the underlying session),
click-through opens the existing mini/expanded forms unchanged.

**Rollback**: revert the PR. New, isolated component; no interaction with existing playback logic
beyond reading `session.ts`.

---

## Migration and rollout

Frontend-only across all steps (Step 3 depends on a sibling RFC's frontend step, not a migration).
Standard PR → merge → auto-deploy → prod smoke, per step.

## Rollback

Every step is additive/relocation-only with no schema or contract surface — straight PR reverts, no
cross-step cleanup required (Step 3's dependency on the sibling RFC is a build-order constraint, not a
rollback constraint — reverting Step 3 does not require reverting the sibling RFC's shell).

## Tests and production smoke verification

Per-step `pnpm test`/`pnpm lint`/`pnpm exec astro check` plus real-browser CDP, specified per step
above. Race-condition and cross-tab tests reuse the existing harness family
(`feedback-stub-must-model-async-lag` — stub must model Spotify's ≥1.2s ack→apply lag, per
`FEAT-playback-bucket-player` Step 6's own shipped bug) rather than a same-tick stub. Route-transition
tests specifically check Step 2's cross-route lyrics open and, if built, Step 4's bar persisting through
`astro:before-swap`. Production smoke: general 19-check suite; no new smoke checks are proposed unless
Step 4 ships (in which case one additional check — bar visible on `/` when a test-account queue is
seeded — is added to `scripts/smoke.sh`, decided at that step).

## Risks and failure modes

- **State-move regressions are the highest-risk item** — `NowPlaying.tsx` is ~1,900 lines and this is
  the second consolidation pass after Step 3a/3b/3c already found two real races (`BUG-22`, `BUG-28`)
  in the *first* pass. Mitigation: the cross-tracker consistency test is mandatory, not optional, and
  Step 1 does not touch `LyricsViewer`'s sync-critical path at all.
- **Single-flight dedupe silently swallowing a legitimately-different concurrent read** (e.g. one caller
  wants a fresher read than another mid-transition). Mitigation: dedupe keys on request identity within
  one microtask/short window, matching the `lib/playback/uris.ts` precedent this RFC reuses rather than
  inventing a new coalescing strategy.
- **Live-lyrics relocation breaking an existing dashboard-only assumption** — some dashboard code may
  implicitly assume `LyricsViewer`'s host is always mounted inside `SelfDashboard`. Mitigation: Step 2's
  verification explicitly re-tests every existing dashboard-internal lyrics entry point, not just the
  new cross-route case.
- **Reorder plus deliberate duplicate-tracks (D8)** — the Playback Bucket allows duplicate tracks by
  design; a naive reorder-by-value (not by `itemId`) could scramble duplicates. Mitigation: reorder
  operates on `itemId` (already the row identity key throughout `PlaybackPanel.tsx`), never on track
  identity.
- **A persistent bar (Step 4) competing for vertical space with the existing header on mobile.**
  Mitigation: the survey's own finding stands — every measured competitor keeps this element thin
  (48–107px); Step 4's verification includes a layout-shift check against the existing header.

## Rejected alternatives

- **Fold `LyricsViewer`'s full sync anchor into `session.ts` in this RFC**, going further than Step 3c
  already did. Rejected: `ARCH-entity-interaction-domain-audit` Step 3c deliberately chose the
  conservative additive-adoption design and explicitly left `refresh()` as the untouched primary source
  — reopening that decision needs the full CDP sync-precision regression battery
  `FEAT-lyrics-sync-precision` used, which is out of proportion to this RFC's actual gap (state
  ownership for six *other* axes, not sync precision).
  the `Backend_TrackExpansionResponse`-style contract audit found none needed.
- **Build a second, Home-specific mini player** instead of relocating the lyrics host and (optionally)
  adding a persistent bar. Rejected explicitly by this RFC's non-goals — it would be exactly the
  "second queue / duplicated playback state" pattern `FEAT-playback-bucket-player`'s own non-goals
  warned against, applied to a new surface instead of a new mechanism.
- **Ship Step 4 unconditionally** rather than gating it on an owner decision. Rejected: the existing
  Pocket reachability may already be judged sufficient once lyrics (Step 2) and the playlist detail
  (Step 3) close the more concrete gaps — building a new site-wide component before that judgment is
  premature scope.

## Unresolved owner decisions

1. **Does "persistent compact playback across routes, including Home" mean (a) reachable from every
   route with at most one interaction — already true today via the layout-mounted Pocket tray — or (b)
   visible with zero interaction whenever something is playing, requiring a new always-on bar (Step
   4)?** Blocks whether Step 4 runs at all. Recommended default: ship Steps 1–3 first, re-evaluate (b)
   against real usage once Home reachability is confirmed sufficient or insufficient in practice.
2. **Exact host for the relocated live-lyrics listener (Step 2)** — a new dedicated always-mounted
   component vs. folding the listener into `PocketBuckit`'s existing always-mounted root. Implementation
   detail, does not change behavior either way; left to Step 2's own session.
3. **Reorder gesture on desktop** — pointer-drag (matching the tray's own touch-pointer-drag pattern) vs.
   keyboard-reachable up/down controls as a required accessibility parallel path (matching this
   product's existing WCAG 2.5.7 non-drag-peer convention, e.g. `AddToBucketMenu` for adds). Recommended
   default: ship both, since the existing tray reorder-in-edit-mode precedent already required a
   non-drag path — confirm during Step 3 implementation whether that precedent's code is reusable here.

## Relationship to existing RFCs and plan rows

- Extends `FEAT-playback-bucket-player` (done, archived) — every piece of "already shipped" evidence in
  this document cites that RFC's own final state; this RFC does not reopen any of its 9 steps.
- Continues `ARCH-entity-interaction-domain-audit` Step 3 (3a/3b/3c done) exactly at the point that
  RFC's own State-owner registry entry says work stopped — the six-axis move and single-flight dedupe
  are that registry's own named "still open" items, not new scope invented here.
- Depends on `ARCH-buckit-navigation-shell` Step 1 for the Playback Bucket's detail-shell placement
  (Step 3 of this RFC only).
- Does not touch `ARCH-movable-resizable-surfaces` (in-progress, unmerged as of this session) — the
  playback panel's docked/floating form keeps using `useDockTear` directly, unextended by
  `surfaceGeometry.ts`.
- `plan.md` gains a one-line Active-section pointer (see this session's plan.md diff).
