# ARCH-buckit-navigation-shell: collapsible My Buckit navigation + one selected bucket detail

- **Status**: **retired 2026-08-15 — owner decided against reviving this RFC's structure.** This line
  previously said Steps 1 and 3's selector + shared-detail structure (`BucketDetailShell`) was live
  again after `myblog_front` #401 (`45b29b2`, 2026-08-13) reverted the corrective #399. That was true for
  a few hours. **The same day**, front #402 (`7057a82`) reverted #401 again and replaced the structure
  with the current "every bucket visible, inline disclosure" model — the owner's own commit message
  states the reason: the single-selection shell made "every other bucket a name in a sidebar, not a
  bucket you could see and open in place." Front #403 (`388db15`)/#404 (`40061bd`) built further UI on
  top of that inline-disclosure structure. This Status line went uncorrected for two days; caught
  2026-08-15 by `ARCH-global-playback-experience` Step 4 auditing its own stated gate before starting
  (`feedback-rfc-current-state-audit`). **`BucketDetailShell` does not exist in `origin/main` today** —
  confirmed by a direct grep of `myblog_front`'s `BucketBoard.tsx` (zero hits for `BucketDetailShell`/
  `BucketNavRow`/`BucketNavList`; the file instead defines `BucketInlineContent`/`BucketInlineNode`/
  `BucketInlineList`). That correction left an open owner decision: write a new RFC for the
  inline-disclosure structure, revive this RFC's single-selection shell, or leave things as-is. **The
  owner decided 2026-08-15 (same session) to document the inline-disclosure structure instead** — the
  shell had already been rejected twice in production (#401's revert, then #402 the same day), so
  reviving it a third time was not the recommended or chosen path. See `ARCH-buckit-inline-navigation.md`,
  the new RFC that now owns this structure and its extension boundary for
  `ARCH-global-playback-experience`/`FEAT-rating-smart-collections`. This RFC has no further active
  steps — Step 2 remains dropped unimplemented (below), and Steps 1/3 remain historical fact (shipped,
  then superseded) rather than a target to rebuild.
- **Owner**: 박지훈
- **Created**: 2026-08-10
- **Plan row**: `plan.md` → ARCH-buckit-navigation-shell
- **Sibling dependency — retired 2026-08-15.** `ARCH-global-playback-experience.md` and
  `FEAT-rating-smart-collections.md` used to target this RFC's shared `BucketDetailShell` variant. That
  dependency was already broken (`BucketDetailShell` does not exist — see Status above) before the owner
  decided, this same session, to retire this RFC rather than revive the shell. Both sibling RFCs now
  target `ARCH-buckit-inline-navigation.md`'s `variant` extension point instead. Do not re-point either
  sibling back to this RFC without a new explicit owner decision.
- **Historical scope statement — builds on, does not redo**:
  `docs/archive/done/rfcs/ARCH-bucket-album-modal-unification.md`
  (shipped 2026-08-09/10) — that RFC unified the **per-album** detail modal (`AlbumDetail.tsx`'s
  `MemoWindow`/`StandardModal` branch, opened by clicking an album tile). This RFC is about a
  different, currently-nonexistent concept: a **per-bucket** selected-detail pane, opened by choosing
  a bucket in the navigation. The two "detail" concepts are siblings, not the same surface — an album
  detail modal can still open *from inside* a bucket's selected-detail pane, unchanged.
- **Reuses, does not touch**: `lib/boardDnd.ts` (drop rules), `lib/pocketBuckit/boardDnd.ts` (Pocket
  mirror), `lib/pocketBuckit/events.ts` (cross-island bridge), `ARCH-entity-interaction-v2`'s drag
  payload contract (`lib/entityDrag.ts`) — all confirmed live and correct in *Current state*; none are
  redesigned here.

- **Archived**: 2026-09-03 — moved to `docs/archive/done/rfcs/`. Retired since 2026-08-15; the file stayed in `docs/rfcs/` for 19 days after its own Status said it was dead.

---

## 2026-08-12 corrective direction (authoritative for future work)

The goal and target sections below are retained as the historical design that produced front #396
and #397. They are not the target for new implementation.

- The owner rejected the desktop bucket-navigation column, mobile bucket-selection drawer, single
  selected-bucket state, and single shared detail pane as the long-term My Buckit interaction.
- The correct structure is the pre-shell inline document flow: each bucket is represented by its own
  object and paper label; opening it expands that same bucket's existing content immediately below;
  several buckets may remain open independently.
- Bucket open state is local, non-persistent UI state. It does not use a path, query parameter,
  `pushState`, `replaceState`, reload restoration, or back/forward navigation.
- Step 2 below never shipped and is dropped. It is not a dependency or blocker for corrective work.
- Steps 1 and 3 remain recorded exactly as shipped and production-smoked. Their desktop selector,
  mobile drawer, auto-selection, and shared-detail rendering are explicit removal targets rather than
  history to rewrite.
- `FEAT-inline-bucket-object-expand` supersedes `FEAT-bucket-object-collapse` and owns the single
  corrective frontend PR, complete motion contract, assets, tests, and production smoke. This RFC has
  no further standalone implementation step.

## Goal

`myblog_front`'s member bucket board (`BucketBoard.tsx`) stops always rendering the **entire** bucket
tree and every member tile inside every bucket, all at once, all the time. Instead: bucket nodes
collapse and expand, exactly **one** bucket is "selected" at a time and rendered in a single detail
pane, that selection is carried in the URL (survives reload, participates in back/forward), desktop
gets an inline collapsible tree + detail pane, mobile gets an appropriate selector/drawer instead of
the current flat scroll, and a collapsed bucket node stays a valid drag-and-drop target. The detail
pane is built behind one shared "bucket detail shell" boundary so that a manual bucket, a system
bucket (e.g. the Playback Bucket), and a smart collection (e.g. 평가 완료 / 평가 예정) can each render
their own detail content inside the same shell without three independent implementations of
selection, header chrome, and URL wiring.

## Non-goals

- **No smart-collection rules.** What "평가 완료" or "평가 예정" contain, how they're derived, and their
  permissions are `FEAT-rating-smart-collections`'s job. This RFC only makes sure the shell that would
  host them exists and accepts a variant.
- **No playback-state architecture.** The Playback Bucket's queue semantics, session ownership, and
  player UI are `ARCH-global-playback-experience`'s job. This RFC only makes sure a system-bucket
  variant slot exists in the detail shell for that RFC to fill.
- **No per-album detail-modal changes.** `AlbumDetail.tsx`'s `MemoWindow`/`StandardModal` unification
  already shipped (`ARCH-bucket-album-modal-unification`) and is untouched — it continues to open from
  inside whatever renders a bucket's member tiles, unchanged by this RFC.
- **No change to `boardDnd.ts` / `pocketBuckit/boardDnd.ts` accept/route rules.** *Current state* below
  confirms these are correct and current (including the `type==='playback'` branch already shipped by
  `FEAT-playback-bucket-player`). This RFC only has to keep collapsed nodes reachable by them — it does
  not change what they decide.
- **No `BucketBoard.tsx` monolith split for its own sake** — per the standing non-goal in
  `ARCH-entity-interaction-v2`/`ARCH-entity-interaction-domain-audit`. Splitting the render tree into a
  nav column + a detail pane is in scope because the goal requires it; extracting unrelated pieces
  (color picker, trash dock internals, etc.) into new files purely for tidiness is not.
- **No change to research notes, color, rename, trash, filters, Undo, or the mobile `ActionSheet`
  action set.** All confirmed present and working in *Current state* — they move with their bucket
  into the new shell, behaviorally unchanged.
- **No movable/resizable/dockable window work.** Out of scope per workspace instruction; unrelated to
  `ARCH-movable-resizable-surfaces`, which this RFC does not touch.

## User-facing problem

At today's prod scale (6 buckets, ~140 items) the always-fully-expanded board costs nothing visible.
The problem this RFC solves is structural rather than an observed complaint: a flat render with no
collapse has no ceiling — every new nested bucket and every new item is permanent visual weight on
every visit — there is no way to link directly to one bucket (bookmark, share, browser back/forward
through a specific selection), and there is no scaffold for a bucket-*level* detail view at all. That
last gap is the concrete blocker: it is what stops `ARCH-global-playback-experience`'s Playback Bucket
detail and `FEAT-rating-smart-collections`'s two smart collections from having anywhere to render short
of each inventing its own one-off shell — the exact "no single owner, N independent silos" pattern
`ARCH-entity-interaction-domain-audit` names as a recurring bug class in adjacent domains.

## Domain terminology and invariants carried in

- **버킷 (bucket)**, **type** (`general`/`artist`/`playback`, closed enum, immutable at create), **kind**
  (free-text system-role axis: default/`spotify_library`/`to_listen`/`playback_queue`) — unchanged
  vocabulary from `FEAT-my-buckit-artist`/`FEAT-playback-bucket-player`.
  버킷 이름은 이름표일 뿐이다 (`FEAT-album-review-authoring` hard rule 3-3) — this RFC's nav must not
  read bucket names as signal, same as every other RFC in this lineage.
- **Tree canonical, Pocket is its projection** (`FEAT-pocket-buckit` D7) — this RFC's nav is a further
  *view* over the same canonical tree, not a second data source, matching the same precedent
  `FEAT-playback-bucket-player` cited for its own queue-is-a-projection design.
  the D-series no-reflow invariant (a drag-over preview must never shift other elements) — carried in
  unchanged; the collapsed-node-stays-mounted design below exists specifically to keep this invariant
  intact under collapse.

## Current state

Verified 2026-08-10 against `myblog_front` `origin/main` (`01c6e35`, same day as
`ARCH-movable-resizable-surfaces`).

### The board renders the full hierarchy, flat, always — there is no collapse concept

`BucketBoard` (`src/components/member/BucketBoard.tsx:1706`, root) renders
`<BucketList items={visibleTree} .../>` (`:2791`) plus a separate library-bucket `BucketList`
(`:2758`). `BucketList` (`:1635`) maps every item to a `BucketCard`, and `BucketCard` recurses
**unconditionally**: it renders `<BucketList items={bucket.children} .../>` at `:1441` with no gate.
Grepping the file for `expanded|collapsed|selectedBucket|activeBucket|selectBucket` returns **zero**
hits tied to bucket nodes (the only `aria-expanded` hits belong to the Pocket-tray toggle `:2663` and a
create-menu dropdown `:2674` — unrelated). `BucketCard`'s own local state is
`editing/coloring/researching/publicizing/viewing` (`:958-963`) — none of it hides member tiles.
`BucketView` (`:207`, `{sort, group, genreFilter, typeFilter}`) is filtering/sorting, not visibility
toggling. **Every bucket at every depth, and every album/track/artist chip inside it, is always
mounted.** There is nothing to extend — collapse and single-selection are both new state.

### No URL-backed selection today, except one existing precedent to extend

`?tab=<id>` deep-links the dashboard's top-level tab (개요/평론/버킷/…) — parsed authoritatively in
`MemberProfile.tsx:33,49,54` (`new URLSearchParams(window.location.search).get('tab')`), consumed by
`ReviewsTab.tsx:33` and `MembersHub.tsx:11,111`. `SelfDashboard.tsx:154,174-176` reads/clears a
`?lyrics=<id>` param for the live-lyrics deep link via `window.history.replaceState`. **Neither a
bucket id nor an album id is ever placed in the URL** — no `?bucket=`/`?album=` param exists anywhere
in `BucketBoard.tsx`. Board scroll position, which bucket is "open" (there is no such concept today —
see above), and any open album modal are pure React state, lost on reload. `?tab=` is the one existing
idiom this RFC extends rather than invents from nothing.

### No mobile-specific navigation shape

`BucketBoard.tsx` has zero hits for `mobile`/`useIsMobileHost` (contrast `AlbumDetail.tsx`'s
`MemoWindow`, which does branch on it). The board is one DOM tree at every viewport;
`src/styles/member/widgets.css` only adjusts sizing via `@media (max-width: 560px)` (`:248`) and
`@media (hover: none), (pointer: coarse)` (`:162,170`) for touch affordance. Touch users get the same
flat hierarchy, routed to `ActionSheet` (`openAlbumSheet`/`openBucketSheet`, `:945-946`, mounted
`:2648`) instead of native drag for actions — but the navigation shape itself is identical to desktop,
just narrower. A genuine mobile drawer/selector is new work, not a breakpoint tweak.

### Drag-and-drop is DOM-event-based, not registry-based — the load-bearing constraint for collapse

`BucketCard`'s `onDragOver`/`onDrop` (`:996-1032`) are native HTML5 handlers attached directly to the
rendered card element. Acceptance is computed live via `canAcceptAlbumDrag`/`canAcceptBucketDrag` from
`@lib/boardDnd`, but the handler only fires at all if the element is mounted and receiving the
browser's native `dragover`. **Today "collapsed but still droppable" is trivially true only because
nothing is ever unmounted.** If this RFC implements collapse by unmounting a bucket's subtree, those
collapsed nodes stop receiving `dragover`/`drop` and silently fall out of the droppable set — a
regression the brief explicitly forbids ("collapsed navigation entries remaining valid drag-and-drop
targets"). This is a real design constraint the Target state below has to satisfy, not an already-solved
problem.

### The rules a collapsed node must still honor — confirmed live, unchanged by this RFC

`canAcceptAlbumDrag` (`lib/boardDnd.ts:60-68`) — three branches, all live today (not just documented in
`ARCH-entity-interaction-v2`'s RFC text):

```ts
export function canAcceptAlbumDrag(bucket: BoardBucket, it: DndItem): boolean {
  if (bucket.kind === SLIB_KIND) return !!it.albumId && !it.trackId && it.srcItemType !== 'artist'
  if (bucket.type === PLAYBACK_TYPE) return it.srcItemType !== 'artist' && (!!it.albumId || !!it.trackId)
  if (bucket.type !== 'artist') return true
  return it.srcItemType === 'artist' || !!it.albumId || !!it.trackId
}
```

`memberAcceptsLabel` (`:79-87`) supplies the reject-reason string (E3's "muted + reason" contract from
`ARCH-entity-interaction-v2`); `routeAlbumDrop` (`:100-153`) implements matching routes for
playback/artist/library/general + bucket-into-bucket. `canAcceptBucketDrag` (`:91-98`) does the
nest-cycle guard (`subtreeHas`). None of this changes here — it is reused verbatim by whatever renders
a bucket node, collapsed or not.

### System-bucket protection — confirmed live, backend-authoritative

`myblog_backend/app/services/bucket_service.py`: `SYSTEM_BUCKET_KINDS = ("playback_queue",
"spotify_library", "to_listen")` (`:132`); `delete_bucket` (`:497`) rejects any bucket whose `kind` is
in that tuple (`:506`) and separately walks up via `_system_bucket_in_subtree` (`:524`, defined `:533`)
to block deleting an ancestor that would cascade-delete a nested system bucket. Client-side guards are
cosmetic mirrors of this; the server is authoritative. Unaffected by navigation changes.

### Preserved behaviors — confirmed present, all move with their bucket unchanged

Research note toggle (`researching` state, `BucketCard.tsx:961` area), color picker (`coloring` state
+ popover, `:961,1207,1274`), rename (`editing`/`name` local state, `:959-960`), genre/type filter chips
(`:1371-1391`), trash dock (`TrashDock`/`TrashDrawer`, `:1477,1653`, mounted `:2807,2843`), mobile
`ActionSheet` for album/bucket actions (`:45`, mounted `:2883,2981`), bucket-local Undo toast
(`:2919-2924`, the `FEAT-playback-bucket-player` Step 6b idiom). Cross-bucket move/copy: `copyIn = isLib
|| it.copy || it.fromLib` (`boardDnd.ts:141`). Pocket cross-island bridge: `BucketBoard.tsx:35` imports
`PB_BOARD_DND_START_EVENT`/`PB_BOARD_DND_END_EVENT`/`PB_BOARD_DROP_EVENT`/etc. from
`@lib/pocketBuckit/events`, dispatches on drag start/end (`:798,804`), listens for the reverse-drop
(`:1938-1939`); `lib/pocketBuckit/boardDnd.ts` mirrors the accept-gate on the Pocket side (`:32-36`) —
the documented two-React-root, window-event-bridge shape, unchanged and still a drift pair to keep in
sync.

## Target architecture and state ownership

- **Navigation state** (which bucket nodes are expanded, which bucket is selected) becomes a new,
  named owner — a small hook/store local to `BucketBoard.tsx` (not `bucketStore`, which stays the
  server-synced tree; navigation state is client-only UI state layered on top of it). No new global
  event bus: this is one React root's own concern.
- **Selection is single**: exactly one bucket is "selected" and rendered in the detail pane at a time
  (the brief's own phrasing — "one selected bucket detail"). Expand/collapse of intermediate ancestors
  is a separate, multi-node concern (any number of nodes can be expanded to reveal the selected one's
  ancestry) — these are two different pieces of state, not one.
- **Collapsed nodes stay mounted, visually hidden** (`display: none` or an off-screen/zero-height
  wrapper that keeps the DOM node attached), not unmounted — this is the direct fix for the DnD
  constraint identified in *Current state*. A collapsed bucket's card, and therefore its
  `onDragOver`/`onDrop` handlers, remain live. This trades a larger DOM tree for correctness; if that
  cost becomes measurable at real bucket-tree sizes (prod today: 6 buckets — small), revisit as a
  follow-up, not as a blocker to Step 1.
- **URL-backed selection extends the existing `?tab=` idiom**: `?tab=bucket&bucket=<id>` (album
  selection inside a bucket's detail, if applicable, layers a further `&album=<id>`, matching the
  existing `?lyrics=<id>` precedent of one param per concern). `history.pushState` on an explicit user
  selection (so back/forward steps through selections); `history.replaceState` for reload-restoration
  writes that shouldn't create a back-stack entry (mirroring `SelfDashboard.tsx:174-176`'s existing
  `?lyrics=` handling). On load, the URL is the source of truth for initial selection; thereafter
  React state drives the URL, not the reverse (one-way sync, avoiding the class of bug where two
  sources of truth fight).
- **The shared bucket-detail shell** is a new component (name TBD at Step 1, e.g. `BucketDetailShell`)
  that owns: header chrome (name, color swatch, rename, kebab menu, trash), the collapse/select
  interaction with its parent nav column, and URL param wiring. It renders **variant content** via a
  discriminated union keyed on bucket `kind`/`type` (the same axes `boardDnd.ts` already keys on):
  - `manual` (today's default `general`/`artist` buckets) — renders the existing member-tile grid,
    unchanged, just relocated from "always visible inline" to "inside the selected-detail pane".
  - `system` (`kind IN ('playback_queue','spotify_library','to_listen')`) — a slot `ARCH-global-
    playback-experience` fills for the Playback Bucket; `spotify_library`/`to_listen` keep rendering
    the existing manual-tile-grid variant unless/until another RFC gives them their own.
  - `smart` — a slot `FEAT-rating-smart-collections` fills for 평가 완료 / 평가 예정. These are not
    `review_buckets` rows at all (per that RFC's own non-goal), so the shell's variant dispatch must
    accept a synthetic "virtual bucket" entry alongside the real tree, not assume every selectable node
    has a `review_buckets.id`.
  - **This RFC ships the shell and the `manual` variant only.** The `system`/`smart` variant slots are
    typed and routed but intentionally render nothing new here — that is exactly the "extension
    boundary required by later RFCs" the brief asks for, not a stub to fill in this RFC.
- **Desktop**: a collapsible nav column (the existing tree, now collapsible per node) beside a detail
  pane showing the selected bucket. **Mobile**: the nav column becomes a selector/drawer (list of
  bucket names, tap to open) that swaps to a full-screen detail view on selection, with a back
  affordance to return to the selector — the shape TBD at Step 3 against a real 390px screen (house
  precedent: measure, don't assume — `ARCH-bucket-album-modal-unification`'s own OQ1).

## UX behavior — desktop and mobile

- **Desktop**: nav column always visible, collapsible per bucket node (a disclosure triangle or
  equivalent on any bucket with children); selecting a bucket (nav row click, not a chevron click)
  swaps the detail pane's content without a full page navigation. Drag-and-drop onto a collapsed node
  in the nav column previews accept/reject exactly as an expanded node does today (E3's contract,
  unchanged).
- **Mobile**: no persistent nav column at 390px (there isn't room for nav + detail side by side); a
  selector surface (drawer or dedicated view — Step 3 decides which against real content density) lists
  buckets, tapping one opens its detail full-screen, with an explicit back control. Existing mobile
  actions (`ActionSheet` for album/bucket ops) are reachable from both the selector and the detail view
  exactly as they are from today's flat scroll.
- **Reload / back-forward**: opening `/buckets?tab=bucket&bucket=<id>` directly (bookmark, share, page
  refresh) restores that bucket selected and its ancestor chain expanded. Pressing back after selecting
  bucket B then bucket C returns to B, not to the unselected state, matching normal URL/history
  semantics — unless the owner decides at Step 2 that intra-board selection shouldn't spam the
  back-stack (see Open questions).

## Data / API / contract impact

**None.** This RFC is frontend-only, state and layout, over the existing `GET /api/buckets` tree and
existing bucket CRUD/reorder endpoints. No shared_db migration, no backend route, no `openapi.json`
change, no `infra/apigateway.tf` change. `FEAT-rating-smart-collections`' and `ARCH-global-playback-
experience`'s own data/contract work is independent of this RFC and gated only on the *shell existing*,
not on any schema this RFC introduces (it introduces none).

## Dependency and repository order

Single-repo (`myblog_front`), no cross-repo ordering. This RFC has no upstream RFC dependency — it
only requires the already-shipped `ARCH-bucket-album-modal-unification` (album-tile click behavior,
untouched and reused as-is) and `ARCH-entity-interaction-v2`'s drag payload contract (also untouched).
Downstream: `ARCH-global-playback-experience` Step 4 (Playback Bucket detail) and
`FEAT-rating-smart-collections` (both smart collections) should not start their own detail-shell UI
work until this RFC's Step 1 ships the shell — named explicitly in both sibling RFCs' dependency
sections.

**Correction 2026-08-12:** Step 1 did ship, but its shared selection destination is now a removal
target. Downstream content must attach to the owning inline bucket region defined by
`FEAT-inline-bucket-object-expand`; neither sibling waits for the dropped URL Step 2.

## Step and PR boundaries

One step per session (hard rule #4) unless the owner marks a step parallel-safe at accept time.

### Step 1 — collapsible nav + one selected-detail pane + the variant extension boundary (desktop)

> ✅ Done 2026-08-10, SHA: `7921a9f` (front #396).

The structural change: introduce per-node expand/collapse, single-bucket selection state, and the
`BucketDetailShell` component with its `manual`/`system`/`smart` variant dispatch (system/smart render
nothing new — typed pass-through only). Collapsed nodes stay mounted (visually hidden), preserving
`onDragOver`/`onDrop`. All preserved behaviors (research/color/rename/trash/filters/Undo) move into the
shell unchanged. No URL wiring yet (Step 2), no mobile shape yet (Step 3) — desktop only, plain React
state for selection in this step.

**Verification**:
```
pnpm lint && pnpm exec astro check && pnpm test
```
Real-browser (CDP): every bucket at every depth still exists and is reachable (collapse then expand
restores full content, no data loss); dragging an album onto a **collapsed** bucket node previews
accept/reject identically to an expanded node and completes the drop; selecting a bucket shows exactly
its own content, deselecting/switching does not leak a previous bucket's DOM state; all of
research/color/rename/trash/filter/Undo verified once each inside the new shell; Pocket cross-island
drag still round-trips (`PB_BOARD_DROP_EVENT` still fires and routes).

**Rollback**: frontend-only, single PR, no schema/contract change — revert the PR.

---

### Step 2 — URL-backed selection (reload + back/forward restoration) — DROPPED UNIMPLEMENTED

> Dropped 2026-08-12 by owner direction. No bucket URL/query/history wiring was present in
> `BucketBoard.tsx` at `origin/main` `0d4f525`, so there is no deployed code to revert. The text below
> is preserved only as the never-shipped proposal.

Wire Step 1's selection state to `?tab=bucket&bucket=<id>[&album=<id>]`, extending the `?tab=`/`?lyrics=`
idiom. `pushState` on explicit selection, `replaceState` on load-restoration writes. Ancestor-chain
auto-expand on direct URL load.

**Verification**: CDP — open a deep link directly, confirm correct bucket selected + ancestors expanded;
select bucket A then B then use browser back, confirm A re-selects; reload mid-selection, confirm
identical state restored; confirm `?tab=` values unrelated to `bucket` (개요/평론/연동 etc.) are
untouched by this change.

**Rollback**: revert the PR; no persisted state outside the URL itself.

---

### Step 3 — mobile selector/drawer

> ✅ Done 2026-08-10, SHA: `7a597f7` (front #397). Owner resolved Unresolved owner decision 2 as
> **drawer-over-content**, not a dedicated full-screen selector view.

Built the mobile (<=767px) navigation shape: a trigger bar (shows the selected bucket's name) opens a
top-anchored drawer over the current screen, reusing Step 1's exact nav content (`BucketNavPanel`,
extracted so desktop `<aside>` and the drawer render the same tree from one source) — gated the same
way `AlbumDetail.tsx`'s `MemoWindow` already branches on `useIsMobileHost` (extracted to
`src/lib/useIsMobileHost.ts` so both call sites share the one hook instead of a second copy). Selecting
a bucket closes the drawer and the already-mounted detail pane underneath updates in place — there is
no separate full-screen detail view and no "back" navigation between two screens; reopening the trigger
bar returns to the picker. This differs from this section's original draft text (which assumed the
full-screen-swap variant); the owner's actual decision was drawer-over-content, corrected here to match
what shipped.

**Verification** (CDP `emulate("390x844x3,mobile,touch")`, run against real prod bucket data via a
smoke-test-account dev-server proxy): trigger bar renders and opens the drawer (scrim + focus trap +
focus-restore on close); drawer lists Spotify-library section + full bucket tree, matching desktop
`<aside>` content; tapping a bucket closes the drawer and the detail pane updates without a full-page
transition; all mobile actions (`ActionSheet` — bucket 삭제/이동, reached via the detail pane's kebab)
reachable from the post-selection state; desktop layout at 1440px unaffected (grid + `<aside>` unchanged,
no drawer artifacts). Created and deleted a temp second bucket to exercise the multi-bucket switch;
prod bucket/Pocket counts confirmed back at their pre-test baseline afterward.

**Rollback**: revert the PR; mobile-only presentational change.

---

### Corrective disposition — owned by `FEAT-inline-bucket-object-expand`

No new PR is opened from this historical shell RFC. After the superseding RFC's evidence gate and
explicit acceptance conditions are green, its single corrective frontend PR must:

1. remove `selectedBucketId`, first-bucket auto-selection, `BucketNavPanel`, `BucketNavRow` /
   `BucketNavList`, the desktop `minmax(220px, 280px)` selector grid, the mobile trigger and
   `BucketNavDrawer`, and the one-at-a-time `BucketDetailShell` dispatch as board structure;
2. retain the existing bucket content implementation and render it below its own bucket object;
3. restore recursive inline parent/child flow with independent local expanded ids;
4. replace selection/drawer tests with the inline, DnD, accessibility, no-history, motion, responsive,
   and system-protection regression matrix in the superseding RFC.

This correction starts from the deployed shell rather than pretending #396/#397 did not ship.

## Migration and rollout

No data migration (no schema touched). Rollout is a normal frontend deploy per step; each step
independently mergeable and deployable. No feature flag — the new shell replaces the old flat render
in the same PR per step, matching this repo's standing convention (no backwards-compatibility shims
per CLAUDE.md).

## Rollback

Each step is a frontend-only PR with no schema/contract dependency — `git revert` the step's merge
commit and redeploy. Steps are additive on top of each other (2 depends on 1's state shape; 3 depends
on 1's shell) but each is independently revertible without touching the others' code, since none
rewrites what a prior step shipped.

## Tests and production smoke verification

- `pnpm lint`, `pnpm exec astro check`, `pnpm test` per step (existing gate).
- Real-browser CDP clickthrough per step's Verification block above — this feature is exactly the class
  of change (render-tree restructuring + DnD) that unit tests alone have repeatedly missed in this
  codebase's own history (`ARCH-entity-interaction-domain-audit` Step 4's `Peek` mount-timing bug,
  `ARCH-bucket-album-modal-unification`'s badge-collision claim that didn't reproduce as assumed).
- Production smoke: standard `scripts/smoke.sh` pass post-deploy per step; no new smoke assertions
  needed (no new authenticated endpoint, no new route) — the existing board-load smoke coverage extends
  naturally since `/buckets` is already smoked.

## Risks and failure modes

- **DnD regression on collapsed nodes** — the single most likely way this RFC could ship a real bug
  (mounted-but-hidden nodes not receiving pointer events due to a CSS mistake, e.g. `visibility:hidden`
  vs `display:none` behaving differently under different browsers' native-drag implementations). Named
  explicitly in Step 1's Verification as a required CDP check, not left to unit tests.
- **DOM size growth** — keeping every collapsed node mounted (rather than unmounted) trades render-tree
  size for DnD correctness. At today's prod scale (6 buckets) this is a non-issue; flagged as a
  follow-up if the owner's bucket count grows enough to matter.
- **Two sources of truth for selection** (React state vs. URL) — mitigated by the one-way-sync rule in
  *Target architecture* (URL is read once on load; thereafter state drives URL, never the reverse).
- **Back-stack spam** — every bucket selection pushing a history entry could make browser back
  annoying to use if the owner selects buckets rapidly while organizing. Named as Open question 1
  rather than pre-decided.

## Rejected alternatives

- **Keep the flat always-expanded board and add a filter/search instead of collapse+select.** Rejected
  because it doesn't address the stated goal (navigation model, not discoverability within a flat list)
  and doesn't produce the "one selected bucket detail" surface the sibling RFCs need to extend.
- **Unmount collapsed subtrees** (simpler render code, smaller DOM). Rejected because it silently
  breaks drag-and-drop onto collapsed nodes, which the brief explicitly requires to keep working — the
  mounted-but-hidden approach is more code but preserves a hard requirement.
- **Build the smart/system detail variants inside this RFC** (do the whole job in one RFC instead of
  three). Rejected per the user's explicit instruction not to create an umbrella RFC, and because it
  would couple this RFC's single-step-per-session budget to two other domains' unrelated schema/state
  decisions.

## Unresolved owner decisions

1. ~~**Does selecting a bucket always push a new history entry, or only some selections?**~~ **Closed
   2026-08-12:** there is no bucket selection URL and no history write; Step 2 is dropped. **Note
   (2026-08-13):** this closure was made on the assumption that the corrective inline-expand direction
   was superseding this structure. That correction has since been shipped and then reverted (see
   Status above), so this structure is live again and the underlying question may be worth an owner
   revisit — not reopened here without explicit instruction.
2. ~~**Mobile shape: drawer-over-content, or a dedicated full-screen selector view?**~~ **Resolved
   2026-08-10: drawer-over-content.** Shipped Step 3 (front #397, `7a597f7`).
3. ~~**Does the nav column show bucket-level status badges?**~~ **Obsolete 2026-08-12:** the nav column
   is a corrective removal target. Existing lifecycle status remains inside each inline bucket's
   preserved content/header treatment.

## Relationship to existing RFCs and plan rows

- Builds on `ARCH-bucket-album-modal-unification` (done, archived) — reuses its album-detail-modal
  unchanged.
- Reuses `ARCH-entity-interaction-v2` (done, archived) — drag payload contract, `boardDnd.ts` rules,
  unchanged.
- **No longer supplies** the shared selected-detail extension boundary — that role transferred
  2026-08-15 to `ARCH-buckit-inline-navigation.md`'s `variant` dispatch (see Status above).
  `ARCH-global-playback-experience` and `FEAT-rating-smart-collections` build against the new RFC now.
- Does not reopen or duplicate `FEAT-bucket-identity`'s Direction B (lifecycle status derivation) —
  that status continues to be computed the same way; this RFC only changes where/how it's displayed
  (nav row vs. detail pane), an Open question above, not a redesign.
- No `docs/rfcs/README.md` index conflict — no other active RFC claims board navigation/selection
  scope today.
- `FEAT-inline-bucket-object-expand` remains the historical record of the reverted corrective attempt;
  it has no active next step (see its Status).

## Decisions log

| Date | Decision | Step |
|------|----------|------|
| 2026-08-10 | RFC drafted. Current-state verification (bucket board render structure, URL param usage, mobile branching, DnD mechanism, drop-rule/system-bucket-guard citations) run against `myblog_front` `origin/main` `01c6e35` and `myblog_backend`'s `bucket_service.py` before writing Target state, per house rule (`feedback-rfc-current-state-audit`) | — |
| 2026-08-10 | **Accepted by owner.** Independent re-verification (separate session) re-confirmed this RFC's most load-bearing citations directly against `origin/main` code (`BucketBoard.tsx:1441`'s unconditional recursion, zero collapse/selection state; `boardDnd.ts`'s `canAcceptAlbumDrag`) — no discrepancies found. Status promoted draft → accepted; siblings `ARCH-global-playback-experience` and `FEAT-rating-smart-collections` remain draft | — |
| 2026-08-10 | **Step 1 shipped** (front #396, squash `7921a9f`). Implementation delegated to Codex, reviewed and gate-run by Claude: `pnpm lint`/`astro check`/`pnpm test` (617 tests) green — one pre-existing test (`BucketBoard.test.tsx`'s optimistic-copy race test) needed updating for the new single-selection render model, no assertion weakened. Real-browser CDP against a local dev build proxied to real prod data (smoke account) verified every Step 1 requirement explicitly: collapsed nav rows stay mounted (`display:none` on the child group, confirmed via computed style, not unmounted), dragging an album onto a **collapsed** bucket's nav row previews accept and completes the drop, switching selection swaps the detail pane with no leaked prior-bucket DOM state, and create/rename/delete (cascade) all round-tripped against the real API. Deployed via front CI (build+upload+CloudFront-invalidate succeeded for `7921a9f`); post-deploy prod smoke 19/19 green, quoted on the PR. A fully-authenticated CDP pass against the literal deployed CloudFront bundle (not just a local build) was attempted for extra confidence but was blocked by the browser's mixed-content policy on the token-relay approach used to keep the bearer token out of the session transcript — not pursued further given the strength of the other evidence | 1 |
| 2026-08-12 | Owner corrected the interaction direction. Step 2 was confirmed absent from `BucketBoard.tsx` at front `origin/main` `0d4f525` and dropped unimplemented. Shipped Steps 1 and 3 remain historical facts; their desktop selector, mobile drawer, single-selection state, and shared-detail layout become explicit removal targets in the superseding `FEAT-inline-bucket-object-expand` draft | — |
| 2026-08-13 | **Owner rejected the shipped corrective result and reverted it.** `FEAT-inline-bucket-object-expand` Step 1 (front #399) had replaced this structure in production 2026-08-12; after reviewing the live behavior the owner decided to hold/reject it rather than iterate, and `myblog_front` #401 (`45b29b2`) cleanly reverted #399, restoring this RFC's Steps 1/3 as the live structure, prod-smoked 19/19. This RFC is not reopened as active work by this entry — it records the reverted state so `docs/plan.md` and the sibling RFC stay accurate | — |
| 2026-08-13 | **Superseded again, same day — not recorded until 2026-08-15 (see the entry below).** Front #402 (`7057a82`) reverted #401 above a second time and replaced `BucketDetailShell`'s single-selection structure with the current inline-disclosure model (`BucketInlineNode`/`BucketInlineList`/`BucketInlineContent`); #403 (`388db15`)/#404 (`40061bd`) built further UI on that structure. Backdated entry — this session found it two days late while auditing a sibling RFC's dependency on this one | — |
| 2026-08-15 | **Staleness caught and corrected.** `ARCH-global-playback-experience` Step 4, auditing its own stated gate ("`ARCH-buckit-navigation-shell` Step 1, already shipped") before writing code, grepped `myblog_front` `origin/main`'s `BucketBoard.tsx` for `BucketDetailShell`/`BucketNavRow`/`BucketNavList` — zero hits. `git log` traced the cause to front #402 (above), which this RFC's Status line and the sibling-dependency note had not been updated to reflect since 2026-08-13. Both corrected in this same pass (see Status above); `docs/plan.md`'s row for this RFC corrected in the same session. No structural decision made here — this entry only records that the file is now honest about current code, not a decision about which structure to keep | — |
| 2026-08-15 | **Owner decided the open structural question, same session.** Given a choice between writing a new RFC for the live inline-disclosure structure, reviving this RFC's `BucketDetailShell` shell, or leaving things undocumented, the owner picked the first — the shell had already been turned down twice in production. This RFC is retired; `ARCH-buckit-inline-navigation.md` now owns the structure and defines the `system`/`smart` content extension point `ARCH-global-playback-experience` and `FEAT-rating-smart-collections` build against, replacing this RFC's `BucketDetailShell` dispatch in that role | — |
