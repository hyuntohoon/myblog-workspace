# ARCH-movable-resizable-surfaces: opt-in movable + resizable desktop surfaces for the memo modal and detached context panel

- **Status**: done (Step 1 shipped + prod-verified 2026-08-10, front #395 `01c6e35`)
- **Owner**: 박지훈
- **Created**: 2026-08-10
- **Plan row**: `plan.md` → ARCH-movable-resizable-surfaces
- **Builds on**: `ARCH-bucket-album-modal-unification` (archived) — this RFC adds move/resize to the two
  surfaces that RFC's Step 1 shipped: the album memo modal (`MemoWindow`) and the shared dockable
  Lyrics/Research-Notes context panel (`ContextPanel` + `useDockTear`, front #394).

---

## Goal

The album memo modal and the detached (floating) state of the shared Lyrics/Research-Notes context
panel can both be moved by their header and resized from any edge or corner, via one small opt-in
shared capability — not a change applied to every modal in the app. Position and size persist for the
browser session, are clamped to viewport bounds and per-surface min/max, and the two known layout bugs
in the previous state (context panel opening at a fixed 720px float width regardless of its docked
width; the memo modal expanding to fill the space a detached panel leaves instead of shrinking) are
fixed.

## Non-goals

- Move/resize on mobile — explicitly disabled; mobile keeps the existing centred/single-floating-panel
  layouts unchanged.
- Rewriting `useDockTear`'s tear/dock/re-arm-gate physics — untouched except one additive field
  (`geometryKey`, for float-position persistence). Docking, undocking, tab-pane persistence, and the
  accidental-redock "must leave and re-enter" gate from front #394 are preserved, not rebuilt.
- Applying move/resize to any other modal (`AlbumDetail`'s read-only `info` mode, `AddAlbumModal`, the
  standard album overlay, etc.). The capability is opt-in per-surface, not global.
- Keyboard-operable resize. Resize handles are pointer-only, matching the existing pointer-only
  tear/dock drag they sit next to; the explicit dock/float button remains the keyboard-reachable
  fallback for placement, but there is no keyboard equivalent for resize.

## Current state (before this RFC)

- `src/lib/dockTear.ts` (`useDockTear`) owns `ContextPanel`'s header-drag-to-move-while-floating,
  resist→tear→dock physics, and viewport clamping. It has no resize concept. `dock.freePos` is
  in-memory only — reset to `INITIAL_DOCK` every time the panel is freshly opened, never persisted.
- `src/components/member/panel/ContextPanel.tsx`'s `floatSize()` returned a hardcoded
  `{ width: Math.min(720, innerWidth-80), height: Math.min(innerHeight-64, 900) }` — detaching the
  panel always opened it near 720px wide, regardless of the memo's current docked width (320–560px
  depending on the memo's size).
- `src/components/member/AlbumDetail.tsx`'s `MemoWindow` had a discrete `size` state
  (`'m'|'l'|'xl'`, `localStorage['lf_memo_size']`) driving a `size-${size}` CSS class with 3 fixed
  `max-width`/`--lys-dock-w` presets (`layout.css` `.memo-modal-lg.size-*`). The modal itself never
  moved and had no free resize. When the context panel detached, `.lys-dock-slot` collapsed to
  `width: 0` but the outer modal kept its static preset `max-width`, so `.memo-dock-main`'s
  `flex: 1 1 auto` stretched to fill the freed column — the memo visibly expanded instead of the whole
  modal getting narrower.

## Target state (after this RFC)

- New `src/lib/surfaceGeometry.ts`: a small shared module — pure rect/resize/clamp math
  (`resizeSurfaceRect`, `clampSurfacePosition`), sessionStorage-backed merge-patch persistence
  (`readStoredRect`/`writeStoredRect`), and two hooks (`useResizableSurface` for 8-edge resize,
  `useMovableSurface` for plain header-drag move). Both hooks are inert when `enabled` is false and
  apply geometry imperatively (direct `el.style` writes during drag, matching `dockTear.ts`'s existing
  perf pattern) so dragging never triggers a React re-render per pointermove.
- `MemoWindow` opts into both `useMovableSurface` (header = `.memo-lg-bar`) and `useResizableSurface`
  (8 handles) for one resizable "content rect", replacing the old 3-preset `Seg` toggle entirely. The
  modal's *outer* applied width is `contentRect.width + (dockSlotReserved ? dockWidth : 0)` — dock
  reservation is additive on top of the user's chosen content width, so undocking the panel shrinks the
  whole modal by exactly the reserved column instead of letting the content stretch into it.
  `--lys-dock-w` is computed in JS from `contentRect.width` (`clamp(320, width*0.39, 560)`, a
  continuous approximation of the old 3-preset ratios) and set as a plain resolved px value via inline
  style — `ContextPanel.tsx`'s `dockW()` reads it with `parseFloat(getComputedStyle(...))`, which does
  **not** resolve CSS `clamp()`/`%` expressions on arbitrary custom properties, so the value must
  already be a plain number by the time it reaches the DOM.
- `ContextPanel.tsx`'s `floatSize()` now derives its "nothing stored yet" default from the *current*
  dock width (`clamp(360, dockW(), 480)`) instead of a fixed 720px, and prefers a stored width/height
  from `sessionStorage['lf_ctx_panel_geo']` when present. 8 resize handles render only while floating
  (`!dock.docked`), reusing the same `useResizableSurface` hook.
- `dockTear.ts` gains one optional field, `geometryKey`: when set, a drag that ends torn-and-outside
  the slot persists `{left, top}` into that sessionStorage key, and the explicit "분리" button seeds
  `freePos` from it instead of always re-centring. Detached *size* is persisted independently by
  `ContextPanel.tsx` into the same key (merge-patched, not overwritten) — position and size are
  restored together the next time the panel floats, but redocking always re-fits to the dock slot
  first (dock size is host-derived, not the last free size).
- Both surfaces persist to `sessionStorage` under one global key per surface type
  (`lf_memo_geo`, `lf_ctx_panel_geo`) — not per album — matching the existing `lf_memo_size`
  precedent of being a standing UI preference, not per-item state. (Owner decision, this session.)

## Steps

Implemented and merged as a single step — the two surfaces share one module and one PR; splitting
them would not be independently mergeable (`ContextPanel`'s float-size fix depends on
`surfaceGeometry.ts` existing, and the memo modal's compact/expand fix depends on the same dock-width
formula both surfaces read).

### Step 1 — shared geometry module + wire both surfaces

- Added `src/lib/surfaceGeometry.ts` + `src/lib/surfaceGeometry.test.ts` (21 unit tests: all 8 resize
  edges growing/shrinking with the correct anchor, min/max clamping, viewport-boundary clamping,
  sessionStorage round-trip + merge-patch + corrupt-JSON degradation).
- Extended `src/lib/dockTear.ts` with optional `geometryKey` (position persistence only); extended its
  test harness and added a stores-then-restores-on-explicit-detach test.
- `ContextPanel.tsx`: dock-width-derived float default, sessionStorage-backed float size, 8 resize
  handles gated to float-only. New/updated `ContextPanel.test.tsx` cases: initial float width derives
  from dock width, resize only responds while floating.
- `AlbumDetail.tsx`'s `MemoWindow`: removed the `size`/`MEMO_SIZES`/`Seg` preset; added
  `useMovableSurface` + `useResizableSurface` over one `contentRect`; outer-width-as-content-plus-dock
  formula; JS-computed `--lys-dock-w`. New `AlbumDetail.memoGeometry.test.tsx` (5 tests): default rect
  on empty session, header-drag move + viewport clamp, resize within constraints, outer-width shrink
  on detach (not expand), mobile keeps the old centred/handle-free path.
- `layout.css`: removed the 3 `.size-*` preset blocks; converted `.memo-lg-grid`'s first column and
  the album-card cover max-width to fluid rules (`minmax(240px, 26%)`, `min(100%, 240px)`) so they
  scale continuously with the now-free-resizable width instead of jumping between 3 fixed breakpoints;
  added `.memo-modal-lg.is-surface-mounted` (fixed-position + transition, mirroring
  `.lys-sheet.is-mounted`) and the 8-handle resize-affordance rules, scoped to
  `.ctx-panel.is-float` / `.memo-modal-lg.is-surface-mounted` only.
- **Bug found and fixed during review** (not in the original spec): the first implementation pass
  recomputed `--lys-dock-w` from the *live* in-flight resize width on every `pointermove`. Since
  `dockWidth` is a ~0.39 function of content width, resizing the memo modal's east/corner handles
  while the context panel was docked made the visible right edge move ~1.39× faster than the pointer
  (content grows by `dx`, the dock column adds another `0.39·dx` on top, live, every frame). Fixed by
  freezing the dock-column width at its pre-drag value for the whole gesture — the dock column only
  re-derives from the new content width on commit (next render), so the edge tracks the pointer 1:1
  during the drag. Verified in the real browser: dragging the east handle 20/40/60/80px produced
  exactly matching width deltas before the fix would have shown 1.39× drift.

**Verification**:
```
cd myblog_front && pnpm test    # 60 files / 617 tests / 0 failed / 0 skipped
pnpm lint                       # clean
pnpm exec astro check           # 0 errors, 2 pre-existing unrelated hints
```
Real-browser (CDP, local dev server proxied to prod `https://www.ratemymusic.blog` with a smoke-user
JWT, per `reference-authed-front-prod-cdp-e2e`): temp bucket + Mac Miller "Swimming" (cataloged, real
prod data), cleaned up (bucket deleted) after. Confirmed live:
- Initial detached context-panel width derives from dock width (444.6px for this memo's size), not
  720px.
- Docking the panel widens the memo modal by exactly the dock column (1140 → 1584.6px); detaching
  shrinks it back to the *same* 1140px content width, not a value that grew to fill the freed slot.
- Resizing the floating panel (`se` handle, +80/+40px) changes its width/height live and persists to
  `sessionStorage['lf_ctx_panel_geo']`; redocking re-fits to the dock slot (444.6px, discarding the
  524.6px float size); detaching again restores the 524.6px float rect exactly.
- Header-drag moves the memo modal 1:1 and clamps at the 8px viewport margin when dragged off-screen.
- Resizing the memo modal's east edge while the context panel is docked tracks the pointer 1:1 (post-fix).
- `emulate("390x844x3,mobile,touch")` + reload: memo modal has no `is-surface-mounted` class, no inline
  position/size styles, no resize handles; context panel renders as `.ctx-panel-mobile` with no resize
  handles and no dock/float toggle — the pre-existing single-floating-tabbed-panel mobile layout is
  unaffected.

**Rollback**: revert the PR. No migration, no backend/contract change — pure frontend, safe to revert
wholesale if a regression surfaces post-deploy.

---

## Known limitations

- Resize has no keyboard equivalent (pointer-only), consistent with the existing tear/dock drag it
  sits beside. The explicit 분리/도킹 button remains the only keyboard-reachable placement control;
  there is no equivalent "reset size" affordance.
- `--lys-dock-w`'s `clamp(320, width*0.39, 560)` formula is a continuous approximation of the old
  3-preset ratios (900→340, 1140→440, 1380→560), not an exact fit at every width — visually
  indistinguishable in practice, not pixel-verified against the old preset values beyond the three
  original reference points.
- Session-level persistence is intentionally global per surface type, not per album — opening a
  different album's memo window reuses the last-used rect. If this reads as surprising in practice
  (e.g. very different album metadata needing very different layouts), re-scope to per-album keys is a
  small, contained follow-up.

## Open questions

None outstanding — the two design decisions (preset replaced fully by free resize; sessionStorage
scoped globally per surface type, not per album) were resolved with the owner before implementation.

## Decisions log

| Date | Decision | Step |
|------|----------|------|
| 2026-08-10 | Owner: fully replace the memo modal's S/M/L/XL preset with free resize (not keep as an initial-value-only preset). | 1 |
| 2026-08-10 | Owner: session-level position/size persistence is one global rect per surface type (`lf_memo_geo`, `lf_ctx_panel_geo`), not per-album. | 1 |
| 2026-08-10 | Session: found + fixed a live dock-width-compounding resize bug not present in the original spec — see Step 1 note. | 1 |
