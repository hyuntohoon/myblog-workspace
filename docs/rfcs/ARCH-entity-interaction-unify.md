# ARCH-entity-interaction-unify: One entity → one interaction, everywhere

- **Status**: in-progress (Step 1 shipped + prod-verified 2026-07-08)
- **Owner**: TBD
- **Created**: 2026-07-08
- **Plan row**: `plan.md` → ARCH-entity-interaction-unify
- **Extends**: `docs/archive/done/rfcs/ARCH-entity-interaction-contract.md`
  (Steps 2+3 established `TrackRow` + `lib/entityLinks.ts`; this RFC completes
  the dispatch to all three entity types and kills the load-bearing
  album-detail duplication)
- **Consumed by**: `FEAT-today-buckit` (its buckit tiles are the first
  consumer that must click identically to every other surface)

---

## Goal

After this RFC, clicking an **artist**, **album**, or **track** does the same
thing no matter which surface it is rendered on, and that behavior is dispatched
through one contract point (`lib/entityLinks.ts`) instead of per-surface
hand-rolling:

- **Artist** → route to `/artist/[id]` (already true via `artistHref`; this RFC
  only closes the remaining not-linkable gaps).
- **Album** → open **one** global album-detail overlay window (mounted app-wide,
  opened by a CustomEvent), on **public and member surfaces alike**. The current
  vanilla-vs-React duplication is removed.
- **Track** → open the album-detail window for the track's album (the album
  window is the canonical track destination in v1; play/add stay reserved).

The concrete win: the `docs/frontend/component-map.md` "Duplicate / overlapping
responsibilities (load-bearing)" item #1 (two album-detail paths) is resolved,
and a new component (like a home buckit tile) can make an entity clickable by
calling one helper, with no knowledge of routes vs overlays.

## Non-goals

- **No new play/add affordances.** `TrackRow`'s `play`/`add` slots stay reserved
  (ARCH-entity-interaction-contract OQ2 default holds). Track click = open album
  window, not play. Existing ▶/＋ on the review tracklist and pocket tray are
  untouched in behavior.
- **No vanilla → React migration of unrelated code.** Only the album-detail
  render path in `scripts/albumDetail.client.ts` is redirected; the review
  page's ▶/＋ track buttons and `ReviewTrackAdder` keep their current wiring.
- **No album detail *route* (`/album/[id]`).** Owner chose a global overlay
  window over a page route (2026-07-08). SEO/deep-link for albums is a possible
  later RFC, not here.
- **No change to the lyrics viewer, bucket DnD, or now-playing paths.**
- **No backend/contract/infra change.** This is a `myblog_front`-only refactor.

## Current state

Verified against `docs/frontend/component-map.md` (stamped 2026-07-03) + source
2026-07-08. Re-verify the 3 load-bearing claims (album-detail duplication,
overlay host, entityLinks surface) at Step 1 per the map's re-verify rule.

- **`lib/entityLinks.ts`** is the contract point but only covers `artistHref(id)`
  and `reviewHref(slug)` (trailing-slash canonical). **No album or track
  dispatch exists.** Album/track "navigation" is an `onOpen(DetailTarget)`
  callback threaded through the member islands, not a route or a shared helper.
- **Album click = two implementations** (the load-bearing duplication):
  1. React `components/member/AlbumDetail.tsx`, mounted **once** by
     `ProfileApp.tsx:419` (member island only), cache `lib/albumDetail.ts`.
     Branches: `MemoWindow` (writable bucket) / `StandardModal` info / edit
     (`AlbumDetail.tsx:52-64`). Opened via the `onOpen(DetailTarget)` callback
     (`DetailTarget` shape at `lib/member.ts:51`).
  2. Vanilla `scripts/albumDetail.client.ts` on the **public** `/review/[slug]`
     page (renders `#albumDetail`, own `sessionCache`, ▶ + ＋ buttons).
  Different caches, different entry points, different interactivity. The React
  modal is **member-coupled** (lives inside `ProfileApp`) — this coupling is the
  central risk this RFC must resolve (see OQ1).
- **Track click** varies per surface (`component-map.md` track table):
  member `AlbumDetail`/`LikedBoard` use shared `components/shared/TrackRow.tsx`
  with declared actions `{lyrics?, open?}` (`open` → album detail; `lyrics` →
  viewer); review tracklist is vanilla ▶/＋; pocket tray is ▶ play; search rows
  are `action:'static'` (not clickable). `play`/`add` are reserved-unimplemented.
- **Overlay infrastructure is reusable and ready.** `lib/useDismissable.ts`
  (ESC + focus trap + module-level nested-overlay stack — overlays already nest,
  e.g. lyrics over album-detail); primitives `.lf-scrim` / `.lf-slideover` /
  `.lf-modal-card` (`styles/member.css`), z-tokens `--z-overlay:80` /
  `--z-panel:90` (`styles/global.css:52`).
- **Cross-island messaging pattern exists.** `lib/pocketBuckit/events.ts`
  (`pb:*` CustomEvents) + `bucketStore` singleton already carry tray↔board
  handoffs across separate React roots. A global album-open event follows this
  established idiom.
- **Null ids are a first-class case.** Search/board payloads carry
  `id: string|null` (null = not-in-catalog) and already render dead/no-op cards
  (`SearchPage.tsx:42`). The unified dispatch must preserve non-navigable
  entities, not crash on them.

## Target state

- **`lib/entityLinks.ts` becomes the full dispatch.** Add, alongside
  `artistHref`/`reviewHref`:
  - `openAlbum(target)` — dispatches a window CustomEvent (proposed
    `ent:open-album`, namespaced like `pb:*`) carrying an album identity
    (`{albumId?, spotifyAlbumId?, cover?, title?}`), or a no-op when the id is
    null.
  - `openTrackAlbum(track)` — resolves the track's album id and calls
    `openAlbum`.
  - `artistHref` unchanged; the "not linkable" gaps (`NowPlaying`, `LikedBoard`
    rows, null-id search cards) close **only** when a real id is in the payload
    (backend payload changes are out of scope — flagged where they block).
- **One global album-detail overlay host.** A single `AlbumDetail` overlay is
  mounted **app-wide** (in `layouts/layout.astro`, sibling to `PocketBuckit`),
  listening for `ent:open-album`. It renders the **read-only** `StandardModal`
  branch for everyone; the **writable** `MemoWindow` / edit branches stay gated
  behind `isLoggedIn()` + bucket context (so public visitors get info-only, the
  owner keeps authoring). This is the design crux — OQ1 decides whether
  `AlbumDetail` can be lifted out of `ProfileApp` cleanly or needs a thin
  read-only variant.
- **Public review page dispatches the event.** `scripts/albumDetail.client.ts`
  stops rendering its own `#albumDetail` and instead dispatches `ent:open-album`;
  the vanilla `sessionCache` album-detail render path is deleted, converging on
  the `lib/albumDetail.ts` cache. The ▶/＋ track buttons on that page keep their
  current `requestPlayback` / `pb:add-track` wiring (non-goal to touch).
- **Track click routes through the album window** on every non-excluded surface
  via `TrackRow`'s `open` action → `openTrackAlbum`.
- **`docs/frontend/component-map.md` updated**: entity-navigation section gains
  album/track dispatch; the "load-bearing duplication #1" item is struck; the
  impact template is filled for this RFC.

## Steps

Sequential (each mergeable; rule 4 one-step-per-session applies). **Architect
review recommended at Step 1** — lifting a member-coupled modal to app scope is
a structural change (workspace trigger table: cross-repo/structural design).

### Step 1 — Global album overlay host + `entityLinks` dispatch (behavior-preserving)

Mount a single app-wide `AlbumDetail` overlay host in `layout.astro` opened by
`ent:open-album`; add `openAlbum`/`openTrackAlbum` to `entityLinks.ts`. Migrate
`ProfileApp`'s existing mount to dispatch through the same host (or have the host
coexist and `ProfileApp` delegate) so member behavior is unchanged. No public
surface rewired yet. Re-verify the 3 component-map claims first.

**Verification**:
```
cd myblog_front && pnpm lint && pnpm exec astro check
# real-browser: member /profile album click still opens the same modal (info +
# writable MemoWindow for a writable bucket); ESC nesting with lyrics viewer
# still correct; console 0.
```

**Rollback**: revert PR — the host is additive until a surface dispatches to it.

---

### Step 2 — Public `/review` album click → global event (kill the duplication)

Redirect `scripts/albumDetail.client.ts` album-open to dispatch `ent:open-album`;
delete its `#albumDetail` render + `sessionCache` album-detail path. Public
visitors now get the same read-only overlay. Keep ▶/＋ buttons as-is.

**Verification**:
```
cd myblog_front && pnpm lint && pnpm exec astro check
# real-browser on a public /review/[slug]: album card click opens the shared
# overlay (read-only, no MemoWindow when logged out); ▶/＋ still work; no
# #albumDetail duplicate node; console 0.
# prod smoke (post-deploy): public review album click opens overlay.
```

**Rollback**: revert PR (restores the vanilla path exactly).

---

### Step 3 — Track click → album window on shared surfaces

Wire `TrackRow`'s `open` action to `openTrackAlbum` and extend to any surface
carrying an album id per the component-map table (search track rows stay static
unless they gain an id — flagged, not forced).

**Verification**:
```
cd myblog_front && pnpm lint && pnpm exec astro check
# real-browser: a track row click (member AlbumDetail / LikedBoard) opens the
# album window for that track's album; console 0.
```

**Rollback**: revert PR.

---

### Step 4 — Update `docs/frontend/component-map.md`

Fill the impact template (below), strike load-bearing duplication #1, update the
entity-navigation + track-click sections, re-stamp Verified.

**Verification**: doc-only; grep-gate that no `#albumDetail` vanilla render or
second album-detail cache remains.

---

## Component-map impact — ARCH-entity-interaction-unify

```
Verified: 2026-07-08 (re-verify at Step 1)
Routes touched:        / (layout host) — public; /review/[slug] — public; /profile (ProfileApp) — authed
Track-click paths hit:  review-tracklist (album-open only) | liked-board-onOpen | albumdetail-readonly
Play path:              none (▶ buttons unchanged — still requestPlayback)
Overlay changed:        album-detail promoted to a single app-wide host (reuses useDismissable + .lf-scrim)
State owner:            ad-hoc → new ent:* window event + lib/albumDetail.ts cache (single)
Cross-island?:          yes (new event: ent:open-album ; shared store: none)
Cache touched:          albumDetail (kept, now sole) ; sessionCache album-detail path (removed)
Duplicate it overlaps:  album-detail paths (RESOLVED by this RFC)
```

## Open questions

1. **Can `AlbumDetail` be lifted out of `ProfileApp` cleanly?** (blocks Step 1,
   the crux) — it currently assumes member/bucket context (`MemoWindow`,
   writable-bucket branch, `bucketStore`). Options: (a) mount the same component
   app-wide and gate the writable branches on `isLoggedIn()` + bucket presence
   (public = read-only `StandardModal`); (b) extract a thin read-only
   `AlbumDetailView` shared by both a public host and the member modal.
   **Architect pass at Step 1 start.** Recommend (a) if the member coupling is
   only the writable branches; (b) if data-loading is entangled with
   `ProfileApp` state.
2. **Event payload shape** (blocks Step 1) — does `ent:open-album` carry a full
   `DetailTarget` (`lib/member.ts:51`) or a minimal `{albumId|spotifyAlbumId}`
   the host re-fetches via `lib/albumDetail.ts`? Recommend minimal identity +
   host-side fetch (dedup/inflight cache already exists), so public callers need
   no member types.
3. **Not-linkable payloads** (blocks nothing here) — `NowPlaying` / `LikedBoard`
   rows / null-id search cards carry no artist/album id. They stay non-navigable
   until the backend adds ids to those payloads (separate change). Record which
   surfaces still can't dispatch after Step 3.
4. **Track → album resolution when albumId is absent** (blocks Step 3) —
   `TrackHit` carries `albumId` + `albumSpotifyId` (`useMusicSearch.ts:82`) but
   some track payloads may only have the spotify album id. `openTrackAlbum` must
   accept either; confirm every consumer surface has at least one.

## Decisions log

| Date | Decision | Step |
|------|----------|------|
| 2026-07-08 | Album click → single global overlay window (not a route page); resolve the vanilla/React duplication onto it (owner) | design |
| 2026-07-08 | Track click → open the album window for the track's album; no new play/add (owner) | design |
| 2026-07-08 | Artist click stays route `/artist/[id]` (unchanged) | design |
| 2026-07-08 | OQ1 resolved — architect rec **(b)**: `AlbumDetail` uses ZERO React context (usePocket/bucketStore = 0), so the crash worry was moot; but the event can't carry member types, so the app-wide overlay is inherently read-only. Extract a read-only `AlbumDetailView`; keep MemoWindow/edit member-side. Eval → `docs/archive/reviews/ARCH-entity-interaction-unify-step1-eval.md` | Step 1 |
| 2026-07-08 | OQ2 resolved — `ent:open-album` carries **primitives** `{albumId, title?, artist?, cover?, year?}` (host re-fetches via lib/albumDetail); public callers import no member types | Step 1 |
| 2026-07-08 | Step 1 SHIPPED — front #255 (`a549ec5`, deploy 28882687379). New `components/album/AlbumDetailView` + `AlbumOverlay` (un-gated, layout-mounted) + `lib/entityEvents.openAlbum`; member `AlbumDetail` delegates read-only body to the shared view. Public prod smoke: overlay opens on event, fetch 200/15 tracks, header+artists+tracklist render, **0 lyrics affordance** (privacy), artist link `/artist/…/`, ESC closes. Member live MemoWindow/edit gesture deferred to owner spot-check (shared view prod-proven; extraction behavior-preserving; MemoWindow untouched) | Step 1 |
