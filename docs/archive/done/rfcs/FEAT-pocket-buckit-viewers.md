# FEAT-pocket-buckit-viewers: bidirectional DnD + per-drawer Card Viewer

- **Status**: done (both tracks prod-live — Track A 2026-06-30 front #218, Track B 2026-07-01 front #219; owner-approved close 2026-07-01)
- **Owner**: TBD
- **Created**: 2026-06-30
- **Plan row**: `plan.md` → FEAT-pocket-buckit-viewers
- **Related**: `docs/archive/done/rfcs/FEAT-my-buckit-artist.md` (done — Step 6 **Pocket→board** tray-open DnD this RFC mirrors + the General/Artist type rules it preserves), `docs/rfcs/FEAT-pocket-buckit.md` (canonical Buckit product, in-progress), `docs/archive/done/rfcs/FEAT-pocket-buckit-workspace.md` (the multi-drawer workspace Track B extends)

> Two front-only, additive extensions to Pocket Buckit, both over the existing shared `bucketStore`
> (one source of truth → every island repaints off one optimistic update, so "reflected immediately
> everywhere" is free): **(A)** the **reverse** drag direction — a board My Buckit member dragged onto a
> Pocket target (tray chip / open drawer) adds to that bucket, reusing the board's own drop routing
> **verbatim** so General/Artist rules + artist-expansion are preserved; **(B)** a **per-drawer Card
> Viewer** — the bucket window opened from a tray chip can toggle between today's list drawer (Current
> Viewer) and a board-style card grid of the bucket's members (Card Viewer). **No new bucket types, no
> membership-semantics change, no new API/contract, no infra.**

---

## Goal

After this RFC, on `/profile` (the "main My Buckit view") a user can drag an album/track/artist member
**out of a board bucket card and drop it onto a Pocket Buckit target** — a tray chip or an open drawer —
and it is added to that bucket with the **exact** semantics of dropping it on another board bucket
(General accepts all → add/move; Artist accepts artist members directly and **expands** album/track
sources into their credited artists, VA excluded). The existing **Pocket→board** drag (Step 6) is
untouched and still works.

Independently, the bucket window that opens when a tray chip is clicked gains a **per-window viewer
toggle**: **Current Viewer** (today's list-style mini-drawer, unchanged) ⇄ **Card Viewer** (the same
bucket's members rendered as a board-style card grid — albums as square covers, artist members as their
square photo, both consistent with the main My Buckit board's member tiles). Each open drawer toggles
independently. Both viewers read the same `bucketStore` bucket, so a change made through either viewer —
or through the board, or via reverse DnD — is reflected immediately in all of them.

## Non-goals

- **No new bucket types, no membership-rule changes.** General/Artist behavior, the closed type enum,
  dedup, and source-expansion are reused as-is from FEAT-my-buckit-artist.
- **No new API, contract, schema, or infra.** Reverse DnD reuses `addBucketItem`/`addBucketTrack`/
  `expandSourceArtists`/`reorderItems` through the board's existing `ops.*`; the Card Viewer is pure
  front rendering.
- **No change to the existing Pocket→board (Step 6) drag** — its `pb:dnd-start`/`pb:dnd-end` bridge and
  the board's `dnd` consumption stay exactly as shipped.
- **No global/persisted viewer mode** — the Current⇄Card toggle is **per open drawer** (ephemeral local
  state), per the owner decision; not a `pb:design` axis.
- **No round artist avatars / new tile chrome.** The Card Viewer matches the board, where an artist
  member is a **square** photo tile with a type badge (not a round avatar) — `ui.tsx` has no `ArtistArt`.
- **No reverse DnD off `/profile`.** A board drag can only *start* where the board island is mounted
  (`/profile`); the site-wide tray is a drop target only when such a drag is in flight.

## Current state

Verified against code 2026-06-30 (2-agent map of both islands).

**Shared state — already one source of truth.** `src/lib/pocketBuckit/bucketStore.ts` is a module
singleton (sessionStorage-backed, user-scoped) consumed by both the layout Pocket island and the
`/profile` board via `useBucketStore()` / `bucketStore.setTree()`. The board's `setTree` is a shim that
writes through to `bucketStore.setTree` (`BucketBoard.tsx:1564-1568`). So any optimistic mutation in one
island repaints the others with no extra wiring.

**Step 6 Pocket→board DnD (to preserve).** Tray drawer items are `draggable`
(`PocketTray.tsx:402-416`): `onDragStart` dispatches `PB_DND_START_EVENT` with a `DndItem`-shaped detail;
the board listens (`BucketBoard.tsx:1738-1754`, `onDndStart`), populates its module-level
`let dnd: DndItem | null` (`:53`), and routes the drop through the **same** logic the board uses for its
own member drags. `PB_DND_END_EVENT` clears `dnd`. Events declared in
`src/lib/pocketBuckit/events.ts:39-52`.

**Board drop machinery (to reuse verbatim).**
- `DndItem` interface `:51`; `let dnd` `:53`; set in `AlbumChip.onDragStart` `:597-609`.
- Accept-gate `canAcceptAlbumDrag(it)` `:826-830`: `bucket.type !== 'artist'` → true (General accepts
  all); Artist → `it.srcItemType === 'artist' || !!it.albumId || !!it.trackId`.
- Bucket card is the drop target (`BucketCard` root `:955-973`): `onDragOver` `:831-840` (preventDefault
  + `setDropTarget(bucket.id)` when accepted), `onDrop` `:841-884`. The **routing** lives inline in that
  `onDrop` `:859-872`: artist member → `ops.insertAlbum`; `it.albumId` → `ops.expandSource({albumId})`;
  `it.trackId` → `ops.expandSource({trackId})`; General target → `ops.copyAlbum`/`ops.insertAlbum`.
- `ops.*` impl `:1961-2340` → `api.addBucketItem` / `api.reorderItems` / `api.expandSourceArtists`
  (optimistic, write through `bucketStore.setTree`).
- The tray currently has **no** `onDragOver`/`onDrop` — it is drag-source-only. The board's only reverse
  target is its internal `TrashDock` (`:1313`).

**Drawer / viewer (to extend for Track B).** Clicking a tray chip opens a `DrawerPanel`
(`PocketTray.tsx:280-434`) — a movable mini-drawer listing up to 8 member rows (26px `Cover` + title +
meta + ▶). `DrawerLayer` (`:437`) renders several at once (`openDrawers` from the provider). The Pocket
island loads only `pocket.css`; `member.css` (which defines the board's `.bb-tile`/`.lf-cover` tile
classes) is **/profile-only** (`profile.astro:9`, `collection.astro:9`) — so the Card Viewer must
self-supply its tile styles in `pocket.css`, like `AddToBucketMenu` does.

**Member model.** `BoardAlbum` (`buckets.ts:27-99`) carries `itemType`
(`album|track|artist|review|playback|snapshot`), `albumId|trackId|artistId` (exactly one non-null per
typed kind), `title`, `artist`, `cover`. `mapItem` (`:143-185`) already fills an artist member as
`title=name`, `artist=''`, `cover=photo_url`; a track member has no cover (placeholder). `ui.tsx`
exports the reusable `AlbumArt({url,label,size})` and `Cover({label,size,square})`; there is **no**
`ArtistArt`.

## Target state

**Track A.** A new symmetric cross-island bridge (mirror of Step 6) carries the board's live drag to the
Pocket island and the Pocket drop target back to the board:
- `events.ts` gains `PB_BOARD_DND_START` (board→pocket, `DndItem`-shaped detail), `PB_BOARD_DND_END`
  (clear), `PB_BOARD_DROP` (pocket→board, `{ targetBucketId }`).
- `BucketBoard.tsx`: `AlbumChip.onDragStart` additionally dispatches `PB_BOARD_DND_START` (and
  `onDragEnd` → `PB_BOARD_DND_END`). The inline bucket-drop routing is extracted into a board-scope
  `dropOnBucket(targetBucketId)` that reads the live `dnd` and runs `canAcceptAlbumDrag` +
  `ops.*` exactly as today; **both** the card `onDrop` and a new `PB_BOARD_DROP` listener call it (no
  duplicated routing → semantics provably identical).
- Pocket island: a module mirror `boardDnd` populated from `PB_BOARD_DND_START` / cleared on END (so a
  drop target knows the drag kind for the accept-gate highlight). Tray chips (`PocketTray` rail) and
  `DrawerPanel` become drop targets: `onDragOver` previews the drop only when the target bucket accepts
  the mirrored payload (a 3-line replica of `canAcceptAlbumDrag` keyed on the target's `bucket.type`);
  `onDrop` dispatches `PB_BOARD_DROP { targetBucketId }`. The actual mutation runs in the board via
  `dropOnBucket`, so General/Artist rules + expansion are the board's, verbatim. Existing Pocket→board
  drag wiring is unchanged.

**Track B.** `DrawerPanel` gains local `viewMode: 'list' | 'card'` (ephemeral, per drawer) with a header
toggle button. `card` renders `bucket.albums` in a `repeat(auto-fill, minmax(112px, 1fr))` grid of
square tiles (cover via `AlbumArt`/a pocket-local cover, title, secondary line / type badge; artist
member click → `/artist/[id]`), styled by new `pocket.css` rules (self-contained, site-wide safe). Both
modes share the same drawer container, header, edit-mode `−` controls, drop-target behavior (Track A),
and the "전체 버킷 페이지 열기" link; both read the same provider `bucketById` → live everywhere.

## Steps

### Step A — Reverse DnD (board member → Pocket target)

`events.ts` +3 events; `BucketBoard.tsx` broadcast + `dropOnBucket` extraction + `PB_BOARD_DROP`
listener; `PocketTray.tsx`/provider drop targets + `boardDnd` mirror; `pocket.css` drop highlight.
Preserves Step 6 and General/Artist/expansion semantics by reusing the board's `ops.*`.

**Verification**:
```
# myblog_front
pnpm lint && pnpm exec astro check
# headless CDP on /profile (prod JWT, throwaway buckets):
#  - drag a board album chip onto a General Pocket chip  → 1 addBucketItem / item appears in both islands
#  - drag the same onto an Artist Pocket chip            → expandSourceArtists (credited artists added), source not stored
#  - drag a board ARTIST member onto an Artist chip       → added directly (dedup on repeat → 409, no dup)
#  - confirm Step 6 (Pocket drawer item → board bucket) still works unchanged
#  - console 0; no spurious bucket-tree GET on hover/dragover
```

**Rollback**: front-only; revert the front PR. No data/infra.

---

### Step B — Per-drawer Card Viewer

`DrawerPanel` viewMode toggle + card-grid rendering; `pocket.css` tile/grid + viewer-toggle styles.

**Verification**:
```
# myblog_front
pnpm lint && pnpm exec astro check
# headless CDP:
#  - open an album bucket drawer → toggle Card → board-style square-cover grid; toggle back → list
#  - open an artist bucket drawer → Card shows square artist-photo tiles + 아티스트 badge; click → /artist/[id]
#  - two drawers open: one Card, one List simultaneously (per-window state)
#  - add/remove a member (board, reverse DnD, or edit −) → both viewers + board reflect it immediately
#  - off-/profile page: open a drawer in Card mode → covers render (pocket.css self-supplied, not member.css)
```

**Rollback**: front-only; revert the front PR.

---

## Open questions

1. **Card Viewer member cap** — list mode shows `slice(0,8)`; card mode should show more (all, with the
   drawer's existing scroll) but a very large bucket could make the drawer tall. Blocks Step B polish —
   default: render all in the existing `maxHeight` scroll area; revisit only if a real bucket is unwieldy.
2. ~~**Reverse-drop move vs copy into a General Pocket bucket**~~ — **RESOLVED (Step A CDP, 2026-06-30):**
   a board member dropped on a General Pocket bucket is a cross-bucket **MOVE** (`PUT /reorder` via
   `ops.insertAlbum`) — the item leaves its origin bucket — exactly mirroring a board member→bucket drag.
   A *copy* still happens only for recent-strip (`copy`) / library (`fromLib`) sources. No new policy.

## Decisions log

| Date | Decision | Step |
|------|----------|------|
| 2026-06-30 | Two tracks, sequential; Track A first (Hard rule #4). Owner-approved, RFC promoted to in-progress. | A,B |
| 2026-06-30 | Card Viewer = the **per-bucket** click window rendered as the board's member tiles (album=cover, artist=square photo), NOT a whole-set card grid. Toggle is **per open drawer**, ephemeral, button inside the drawer header. | B |
| 2026-06-30 | Reverse DnD reuses the board's `ops.*` via an extracted `dropOnBucket` + `PB_BOARD_DROP` event, so membership/General/Artist/expansion semantics are the board's verbatim (no duplicated routing). | A |
| 2026-06-30 | Drop targets = tray chips + open drawers (both viewer modes share the drawer container). | A |
| 2026-06-30 | Card Viewer styles live in `pocket.css` (self-contained), not `member.css` (which is /profile-only) — site-wide drawer must not depend on it. | B |
| 2026-06-30 | Step A verified headless e2e (real Chrome synthetic DragEvents + mock backend, 0 console errors): General drop = cross-bucket move (`PUT /reorder`), Artist drop = source-expansion (`POST source_album_id`), accept-gate `data-droppable` correct, Step 6 `pb:dnd-start` intact. | A |
| 2026-07-01 | Step B shipped (front #219) + prod-live. `DrawerPanel` ephemeral per-drawer `viewMode` toggle; Card Viewer = `bucket.albums` as a board-style square-cover grid (album=cover, artist=square photo + 아티스트 badge, click→`/artist/[id]`); `Cover` gained `url`/`square` (site-wide global `.cover`/`.cover img`, no `member.css` dep); `pocket.css` self-supplies `.pb-cardgrid`/`.pb-card*`/`.pb-viewtoggle`. List rows + card tiles share `dragBind` so Step 6 drag-out + edit-− work in both. Verified headless CDP off-`/profile`: list⇄card toggle, 2 img-covers + 1 placeholder with `member.css` NOT loaded & `.bb-tile` rule absent, artist tiles + badge + click→`/artist/ar1`, two drawers independent per-window mode, edit-− live reflection (grid 3→2 + chip 3→2), console clean; prod bundle `PocketBuckit.BqMp8rYZ.js` + CSS `Cc5GMNRB.css` carry all markers (deploy 28479488342). Open-Q 1 resolved: render all members in the existing scroll area (no slice cap). | B |
