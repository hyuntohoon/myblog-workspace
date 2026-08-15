# ARCH-global-playback-experience: unify remaining playback state, one app-wide lyrics host, playlist-style Playback Bucket detail

- **Status**: accepted (2026-08-11, owner approval this session)
- **Owner**: 박지훈
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
- **No backend/contract change beyond the one artwork field this RFC's own audit found necessary** (see
  *Current state* and *Data/API/contract impact*) — no unrelated schema or route additions ride along
  with it.
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

**Artwork IS a real contract gap — corrected after direct re-verification.** An earlier draft of this
section (produced by a subagent whose work was not yet reviewed when this correction was made) claimed
`BoardAlbum.cover` already carries artwork for playback-queue rows. That claim does not survive a direct
read of the code and is replaced here with the verified facts:

`lib/buckets.ts:195-198` — the `mapItem()` function's own comment states the gap explicitly: *"TrackBrief
has no cover_url (the cover lives on its album, not resolved [here]) → a track tile shows the initials
placeholder."* The line right below it: `cover: isArtist ? (ar?.photo_url ?? null) : (a?.cover_url ??
null)`, where `a = it.album`. For a playback-queue row (`item_type === 'playback'`), `it.album` is
**always `null`**, confirmed on the backend side: `myblog_backend/app/api/routes/buckets.py`'s
`_item_response()` only sets `album=_album_brief(album, ...)` when `item.album is not None` (`:127,
152-153`), and a playback row's `album_id` is null by design (queue rows key off `track_id`, per
`FEAT-playback-bucket-player` T2 — a track has no `album_id` foreign key on the *membership* row itself).
The generated type `Backend_TrackBrief` (`lib/api.gen.ts:3339-3350`) confirms this from the contract
side: `album_id`/`artist_names`/`duration_sec`/`id`/`title` — **no `cover_url` field exists anywhere in
the response for a playback-kind row.** `lib/buckets.ts:264`/`:292` (the line numbers the earlier draft
cited) belong to a **different, unrelated type** — `PublicCollection`'s album-cover projection for
`/collection` — not to any playback-queue row shape; citing it here was a copy-paste-shaped citation
error, not a real precedent.

**Consequence**: rendering any per-row or representative artwork for the Playback Bucket detail requires
an actual payload change — there is no way to do it from today's response, and the "artwork delivery
without frontend N+1" requirement can only be satisfied by extending the *backend* response (a resolve-
at-render-time client fallback would reintroduce exactly the N+1 the requirement forbids). See *Data/API/
contract impact* and Step 3 below.

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
- **Playlist detail enhancements are additive to `PlaybackPanel.tsx`**: per-row `<img>` off a **new**
  `cover_url` field on `Backend_TrackBrief` (Step 3 below — does not exist today, see *Current state*'s
  corrected artwork finding), a summary header (`N곡 · MM:SS 총 재생 시간`, computed client-side from
  already-loaded `durationSec` — a null duration degrades the total to "—", matching the existing
  per-row `—` fallback at `PlaybackPanel.tsx:101`), a play-all action (`playbackSession.playAt(rows[0]
  .itemId)` — reuses the existing per-row play call, not a new session method), and reorder (pointer-based
  drag reusing the
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
- **Playlist detail (Step 4)**: desktop shows the artwork thumbnail + summary header above the existing
  row list; mobile (the 390px full-height sheet, "대기열" tab) gets the same header and thumbnails at
  reduced size, reorder via long-press-drag consistent with the tray's existing touch-drag threshold.
- **Persistent surface (Step 5, gated on Open question 1)**: if built, a thin bar — matching the
  external survey `FEAT-playback-bucket-player` Step 6 already ran (SoundCloud 48px / Apple Music 54px–
  61px at 390 / Genius 80px–107px at 390, "no service puts the queue in that bar") — sits below the
  header on every route, click-through opens the existing mini/expanded forms, no new player logic.

## Data / API / contract impact

**One small, additive backend contract change is required — corrected finding, see *Current state*.**
`Backend_TrackBrief` gains a nullable `cover_url`, resolved server-side in `_track_brief()`
(`myblog_backend/app/api/routes/buckets.py:98-104`) via the track's own `album_id` → `albums.cover_url`
join — the same join `_album_brief()` right above it already performs for album rows, so this is
extending an existing pattern, not inventing a new query shape. Because the bucket-items list already
returns every row in one call, adding one column to an existing join costs **zero additional queries** —
the N+1-avoidance requirement is satisfied by construction, not by a new resolver endpoint. `openapi.json`
regenerated → workspace `merge_openapi.py` → front `api.gen.ts` regenerated, the standard three-artifact
chain (`reference-workspace-contract-merge-order`). No new route, no `infra/apigateway.tf` change — the
existing `GET /api/buckets` response shape only. The six state fields moving into `session.ts` (Step 1)
are moves of existing client-side reads, not new endpoints; the live-lyrics host relocation and the
single-flight read wrapper (Steps 1–2) are pure frontend — only Step 3 (artwork) touches a contract.

## Dependency and repository order

Steps 1–2 are `myblog_front`-only, no cross-repo ordering. Step 3 (artwork contract) is cross-repo:
`myblog_backend` (serializer + `openapi.json` export) → `myblog-workspace` (contract merge) →
`myblog_front` (regen), per `reference-workspace-contract-merge-order`. Step 4 (playlist detail UI)
depends on both Step 3's field existing *and* `ARCH-buckit-navigation-shell` Step 1 shipping (the
`BucketDetailShell` `playback_queue` slot it renders into) — two independent prerequisites, either order
upstream, both required before Step 4. Step 5 (persistent bar, conditional) is front-only, no cross-repo
dependency.

```
ARCH-global-playback-experience  Step 1 ─┬─ Step 2
                                  unify   │  lyrics host
                                  controller
                                          │
                                  Step 3 (cross-repo: backend → workspace → front)
                                  artwork contract
                                          │
                                          v
                                  Step 4 ── depends also on ARCH-buckit-navigation-shell Step 1
                                  playlist detail UI
                                          │
                                          v
                                  Step 5 (conditional on Open question 1)
                                  persistent bar
```

## Step and PR boundaries

One step per session (hard rule #4); Steps 1 and 2 have no ordering constraint on each other and may be
taken in either order. Step 3 is a rule-#4-sensitive cross-repo contract step. Step 4 depends on Step 3
and on the sibling RFC. Step 5 is conditional.

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

### Step 3 — backend: `cover_url` on `Backend_TrackBrief` (cross-repo contract step)

Add nullable `cover_url` to `TrackBrief`/`Backend_TrackBrief`; `_track_brief()`
(`myblog_backend/app/api/routes/buckets.py:98-104`) resolves it via the track's `album_id` →
`albums.cover_url`, mirroring `_album_brief()`'s existing join immediately above it. No schema
migration — this is a response-shape addition computed from columns that already exist
(`albums.cover_url` is already read elsewhere in the same file). `openapi.json` export → workspace
`merge_openapi.py` → front `api.gen.ts` regen, in that order.

**Verification**: backend `pytest` — new field populated correctly for `item_type='playback'` rows with
a resolvable album, null-safe for the (rare) case of a track with no album; query-count assertion (or
`EXPLAIN` inspection) confirming the added column costs no additional query on the existing
`GET /api/buckets` call; `openapi` diff committed and reviewed (expect exactly one field added, nothing
else moved); workspace contract merge verified; front `api.gen.ts` diff contains only the new field.

**Rollback**: additive nullable field — safe to leave in the schema/response even if Step 4's frontend
consumption is reverted; drop the field in a follow-up change only if genuinely necessary (unlikely,
since it's purely additive and costs nothing unused).

---

### Step 4 — Playback Bucket playlist detail: artwork, summary, play-all, reorder **[gated: Step 3 merged + `ARCH-buckit-navigation-shell` Step 1 merged]**

Add per-row artwork (the new `cover_url` field from Step 3, zero additional requests since it rides the
existing bucket-items response), a summary header (track count + total duration, client-computed), a
play-all action, and pointer-based reorder to `PlaybackPanel.tsx`'s `PlaybackQueue`. Mount the enhanced
panel as the `BucketDetailShell`'s `playback_queue` body (the sibling RFC's empty slot) in addition to
its existing Pocket mini/expanded placement — same component, two mount points, no duplicated state
(both read `usePlaybackViewModel()`/`session.ts` directly).

**Verification**: `pnpm test && pnpm lint && pnpm exec astro check`; real-browser CDP — artwork renders
with zero additional network requests (confirm via the browser's network panel: request count before/
after opening a 13-row queue is unchanged from before Step 3 shipped); play-all from the summary header
starts playback from position 0; reorder persists across a reload; the same panel opens correctly from
both the Pocket mini-player *and* the new bucket-detail-shell placement without divergent state.

**Rollback**: revert the PR. Frontend-only, additive UI on an existing component; safe even if Step 3's
backend field is later reverted (artwork just degrades back to the placeholder).

---

### Step 5 — persistent compact playback surface (conditional on Open question 1)

Only if the owner picks the always-visible-bar form. A thin site-wide strip (identity + transport,
matching the survey's 48–107px reference range) mounted at layout level, visible whenever
`session.ts` reports active/paused playback, independent of Pocket's open state. If the owner instead
accepts Pocket's existing one-tap reachability as sufficient, this step does not run and the RFC closes
at Step 4.

**Verification** (if run): real-browser CDP across every route including Home — bar appears on playback
start, persists across a client-side navigation (no remount/audio interruption — the same
`astro:before-swap` persistence `FEAT-member-player` Step 5b already proved for the underlying session),
click-through opens the existing mini/expanded forms unchanged.

**Rollback**: revert the PR. New, isolated component; no interaction with existing playback logic
beyond reading `session.ts`.

---

## Migration and rollout

No `shared_db` migration on any step — Step 3's artwork field is a response-shape addition over existing
columns, not a schema change. Steps 1, 2, 4, 5 are frontend-only. Standard PR → merge → auto-deploy →
prod smoke, per step; Step 3 additionally follows the three-artifact contract chain before its own
deploy.

## Rollback

Every step is additive/relocation-only with no schema surface — straight PR reverts, no cross-step
cleanup required. Step 3's contract addition is nullable/additive, safe to leave in place even if Step
4 (its only consumer) is reverted. Step 4's dependency on Step 3 and on the sibling RFC's shell is a
build-order constraint, not a rollback constraint — reverting Step 4 does not require reverting either
prerequisite.

## Tests and production smoke verification

Per-step `pnpm test`/`pnpm lint`/`pnpm exec astro check` (backend `pytest` for Step 3) plus real-browser
CDP, specified per step above. Race-condition and cross-tab tests reuse the existing harness family
(`feedback-stub-must-model-async-lag` — stub must model Spotify's ≥1.2s ack→apply lag, per
`FEAT-playback-bucket-player` Step 6's own shipped bug) rather than a same-tick stub. Route-transition
tests specifically check Step 2's cross-route lyrics open and, if built, Step 5's bar persisting through
`astro:before-swap`. Production smoke: general 19-check suite; Step 3 additionally needs a live
response-shape check (`cover_url` present for a known playback-bucket row on the smoke account) quoted
in its PR comment; no new smoke checks are proposed for Steps 1/2/4 unless Step 5 ships (in which case
one additional check — bar visible on `/` when a test-account queue is seeded — is added to
`scripts/smoke.sh`, decided at that step).

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
- **A persistent bar (Step 5) competing for vertical space with the existing header on mobile.**
  Mitigation: the survey's own finding stands — every measured competitor keeps this element thin
  (48–107px); Step 5's verification includes a layout-shift check against the existing header.
- **Artwork join (Step 3) adding real cost at scale.** Considered unlikely — the serializer already
  performs an equivalent join for `album` responses on other item types — but if implementation finds
  otherwise, the resolver-endpoint alternative (a client-side per-track resolve, matching the existing
  `resolveDbAlbumId` pattern) remains available as a fallback, at the cost of reintroducing the N+1 this
  RFC's default avoids.

## Rejected alternatives

- **Fold `LyricsViewer`'s full sync anchor into `session.ts` in this RFC**, going further than Step 3c
  already did. Rejected: `ARCH-entity-interaction-domain-audit` Step 3c deliberately chose the
  conservative additive-adoption design and explicitly left `refresh()` as the untouched primary source
  — reopening that decision needs the full CDP sync-precision regression battery
  `FEAT-lyrics-sync-precision` used, which is out of proportion to this RFC's actual gap (state
  ownership for six *other* axes, not sync precision).
- **Resolve artwork purely client-side** (a per-track resolve call at render time) instead of extending
  the backend response. Rejected as the default because it reintroduces the N+1 this RFC's brief
  explicitly forbids; kept only as Step 3's fallback if the server-side join proves costlier than
  expected.
- **Build a second, Home-specific mini player** instead of relocating the lyrics host and (optionally)
  adding a persistent bar. Rejected explicitly by this RFC's non-goals — it would be exactly the
  "second queue / duplicated playback state" pattern `FEAT-playback-bucket-player`'s own non-goals
  warned against, applied to a new surface instead of a new mechanism.
- **Ship Step 5 unconditionally** rather than gating it on an owner decision. Rejected: the existing
  Pocket reachability may already be judged sufficient once lyrics (Step 2) and the playlist detail
  (Step 4) close the more concrete gaps — building a new site-wide component before that judgment is
  premature scope.

## Unresolved owner decisions

1. **Does "persistent compact playback across routes, including Home" mean (a) reachable from every
   route with at most one interaction — already true today via the layout-mounted Pocket tray — or (b)
   visible with zero interaction whenever something is playing, requiring a new always-on bar (Step
   5)?** Blocks whether Step 5 runs at all. Recommended default: ship Steps 1–4 first, re-evaluate (b)
   against real usage once Home reachability is confirmed sufficient or insufficient in practice.
2. **Exact host for the relocated live-lyrics listener (Step 2)** — a new dedicated always-mounted
   component vs. folding the listener into `PocketBuckit`'s existing always-mounted root. Implementation
   detail, does not change behavior either way; left to Step 2's own session.
3. **Reorder gesture on desktop** — pointer-drag (matching the tray's own touch-pointer-drag pattern) vs.
   keyboard-reachable up/down controls as a required accessibility parallel path (matching this
   product's existing WCAG 2.5.7 non-drag-peer convention, e.g. `AddToBucketMenu` for adds). Recommended
   default: ship both, since the existing tray reorder-in-edit-mode precedent already required a
   non-drag path — confirm during Step 4 implementation whether that precedent's code is reusable here.
4. **Artwork contract shape (Step 3) — resolved 2026-08-15.** Extend `Backend_TrackBrief` with
   `cover_url` (recommended, see *Data/API/contract impact*) vs. surface `tracks.spotify_id` on
   playback rows for a client-side Spotify-catalog resolve. Owner picked the recommendation:
   `cover_url`. The alternative was rejected — it would put a per-row external call (or client-side
   resolve) on the queue path and reintroduce exactly the kind of Spotify dependency this document's
   own non-goals and the workspace's service-boundary invariant (no synchronous Spotify call from a
   user-facing flow) rule out. See Decisions log.

## Relationship to existing RFCs and plan rows

- Extends `FEAT-playback-bucket-player` (done, archived) — every piece of "already shipped" evidence in
  this document cites that RFC's own final state; this RFC does not reopen any of its 9 steps.
- Continues `ARCH-entity-interaction-domain-audit` Step 3 (3a/3b/3c done) exactly at the point that
  RFC's own State-owner registry entry says work stopped — the six-axis move and single-flight dedupe
  are that registry's own named "still open" items, not new scope invented here.
- Depends on `ARCH-buckit-navigation-shell` Step 1 for the Playback Bucket's detail-shell placement
  (Step 4 of this RFC only).
- Does not touch `ARCH-movable-resizable-surfaces` (in-progress, unmerged as of this session) — the
  playback panel's docked/floating form keeps using `useDockTear` directly, unextended by
  `surfaceGeometry.ts`.
- `plan.md` gains a one-line Active-section pointer (see this session's plan.md diff).

## Decisions log

| Date | Decision | Step |
|------|----------|------|
| 2026-08-10 | RFC drafted. Current-state verification (site-wide mount of `PocketBuckit`/`PlaybackPanel`, `session.ts`'s actual state shape, `NowPlaying.tsx`'s confirmed-still-local state per `component-map.md`'s State-owner registry, the live-lyrics single-listener gap) run against `myblog_front` `origin/main` before writing Target state | — |
| 2026-08-10 | **Corrected a factual error found during review, before this RFC was accepted or any code written.** An earlier pass of this document's *Current state* and *Data/API/contract impact* sections claimed `BoardAlbum.cover` already carries artwork for playback-queue rows, based on a citation (`lib/buckets.ts:264`/`:292`) that actually belongs to an unrelated type (`PublicCollection`'s cover projection, not any playback-queue row shape). Direct re-verification of `lib/buckets.ts:195-198`, `myblog_backend/app/api/routes/buckets.py:98-104,127,152-153`, and the generated `Backend_TrackBrief` type confirms the opposite: no `cover_url` field exists anywhere in the playback-row response today. Corrected: artwork requires a real, additive backend contract change (new Step 3), and Steps renumbered accordingly (old Step 3 → 4, old Step 4 → 5) | 3 |
| 2026-08-11 | Owner accepted the RFC (Status: draft → accepted) and selected Step 1 to run this session | — |
| 2026-08-11 | **Step 1 shipped** (front #398, `0d4f525`). Implementation drafted by `codex`, reviewed line-by-line against the invariants this document names before merge — one real regression found and fixed pre-merge (`resolveCapability()`'s permanent-once gate would have locked `capabilityTier` at `'fallback'` after any transient first-mint failure for the rest of the tab session; replaced with dedupe-only semantics). `pnpm test`/`lint`/`astro check` independently re-run, not just self-reported. Real-browser CDP verification of live-Spotify convergence (shuffle/device across both surfaces, lock-screen Media Session) was not performed — no `.env` in the isolated worktree — merged on explicit owner instruction. Production smoke 19/19 post-deploy. First CI attempt on the merge commit failed on an unrelated flaky focus-trap test (`AddToBucketMenu.test.tsx`, untouched by this change, already green twice on the same tree pre-merge); re-run was clean. | 1 |
| 2026-08-15 | **Step 2 shipped** (front #405, `55ccd47`). Relocated `ENT_OPEN_LIVE_LYRICS`'s listener from `SelfDashboard` to `PocketBuckit.tsx` — chose folding into the existing layout-mounted root (Open question 2) over a new dedicated component, since `PocketBuckit` is already the event's dispatch source (via `PocketTray`) and this avoids a second always-mounted React root. `SelfDashboard`'s own direct-call live-lyrics path (`NowPlaying`'s 가사 tap) is untouched — only the cross-island event listener moved, so the dashboard route can't double-open the overlay. **Found and fixed a real bug the relocation surfaced**: `LyricsViewer`'s `.lyv-*` CSS lived in `member/layout.css`, which loads only via `member.css` (dashboard + `/collection` only) — mounting the viewer from `PocketBuckit` would have shipped it with zero styles on every non-dashboard route, the 5th recurrence of the same `member.css` trap `.lf-artist-link`'s "MOVED OUT" note already documents in that file. Extracted to `src/styles/lyricsViewer.css`, self-imported by `LyricsViewer.tsx`, mirroring the existing `modal.css`/`pocket.css` precedent — not scope creep, since without it the RFC's own stated goal ("가사 opens from any route") would have shipped visibly broken. `pnpm test` 635/635, `pnpm lint` clean, `pnpm exec astro check` 0 errors. Real-browser CDP against a local dev server (same no-`.env` isolated-worktree limitation as Step 1) confirmed the overlay opens fully styled on Home and `/search/` and via the layout-level listener on the dashboard route, exactly one `.lyv-panel` instance each time, ✕ close works; no new console errors beyond expected localhost→prod CORS noise. A live authenticated prod click-through was not additionally performed post-merge — pure frontend relocation with no backend/data dependency, general production smoke 19/19 passed instead. | 2 |
| 2026-08-15 | **Open question 4 resolved.** Owner confirmed the recommendation: `Backend_TrackBrief` gains `cover_url`, resolved server-side (not `tracks.spotify_id` + client resolve). Step 3 implementation starting this session. | 3 |
| 2026-08-15 | **Step 3 shipped** (backend #156 `dd627bd`, ws #907 `a18d940`, front #407 `afe783c`). `_track_brief()` resolves `cover_url` off `track.album.cover_url`; `list_buckets()`'s eager-load extended with `ReviewBucketItem.track → Track.album` (`Track.album` is `lazy="select"` by default, confirmed via `myblog_shared_db`'s model) alongside the existing `Track.artists` chain — without it, a playback-row queue would N+1 one query per row the first time the serializer reads `.album`; a review pass caught this before merge (the RFC's own "zero additional queries" claim was true for HTTP round-trips but not for DB queries without this eager-load). Backend `pytest` 664 passed (non-DB) + real-DB integration suite (Neon test branch, `TEST_DB_URL`) 83 passed, including two new tests in `TestListBucketsTrackCoverEagerLoad` proving the eager-load closes the N+1 (query count does not scale with playback-row count). `openapi.json` diff exactly one field added; `api.gen.ts` regen exactly the same, no component changes (the field is unused until Step 4). Production smoke 19/19 passed post-deploy, plus a targeted authenticated `GET /api/buckets` call against prod confirming `cover_url` present on every live track/playback row (quoted on backend #156's PR). No dedicated `reviewer` subagent was registered in this session's environment (CLAUDE.md's mandatory-review table names one) — substituted a `general-purpose` agent with an equivalent review brief; flagged as a process gap in the backend PR body rather than silently skipped. | 3 |
