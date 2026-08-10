# ARCH-album-context-panel: Shared dockable Lyrics/Research context panel for the memo window

- **Status**: accepted (single-PR merge — owner directed immediate implementation this session)
- **Owner**: 박지훈
- **Created**: 2026-08-10
- **Plan row**: `plan.md` → ARCH-album-context-panel

---

## Goal

`myblog_front`'s bucket-album memo window (`MemoWindow` in `src/components/member/AlbumDetail.tsx`) has one
dockable panel (lyrics, track-scoped) and one inline-expanding panel (research notes, album-scoped) with
different interaction models and duplicated placement code. After this RFC, both live in **one** shared,
dockable, tabbed context panel — Lyrics tab (track-scoped, empty state when no track selected) and Research
Notes tab (album-scoped) — that can dock into the memo window's right column or float freely, with the
per-tab scroll/content state preserved across tab switches. The tear→dock physics (`useDockTear`) gets a
"leave and re-enter the target before it can (re-)dock" gate so a floating panel resting or nudged near the
right edge no longer docks by accident. On mobile the same tabs render in a single floating (never-docked)
panel instead of the desktop docked layout.

## Non-goals

- No change to the standalone, non-memo lyrics surfaces (`LyricsSheet`/`LyricsSheetContent` as used by
  `LikedBoard.tsx`, `AlbumDetailView.tsx`'s `?lyrics=` entry, `TrackRow`'s float-open path). Those keep their
  own header + float-only placement, unchanged.
- No CSS class rename sweep. The existing `.lys-*` prefix (originally "lyrics sheet") is reused as the
  generic panel-chrome/dock-mechanics naming; only new tab/pane classes are added. Renaming for naming
  purity is out of scope.
- No change to `ResearchNote`'s data layer (`lib/research.ts`, `useResearch`) or its `'rail'`/`'panel'`
  variants used elsewhere (the `/write` margin rail, BucketBoard cover slide-over). Only the memo window's
  usage moves from inline `variant="doc"` to inside the new panel's Research tab (still `variant="doc"`).
- No backend/contract/infra change. Frontend-only.

## Current state

- `src/lib/dockTear.ts` — `useDockTear` is a **host-agnostic** grab→resist→tear→glide→dock state machine.
  `DockState = { docked, dragging, expect, freePos }`. `inSlot(x, y)` is evaluated on every `pointermove`
  once the panel is torn (`d.torn`), and the panel docks on `pointerup` iff `wasTorn && inSlot(x, y)` at
  that instant — **no requirement that the pointer ever left the slot during this drag**. A panel that
  starts a drag already resting inside (or near) the slot bounds can be nudged a few pixels and re-dock
  immediately; this is the "overly sensitive" behavior item 5 of the ask targets.
- `src/components/member/lyrics/DockableLyricsSheet.tsx` — the tear/dock **wrapper**, lyrics-only. Supplies
  `dockRect`/`floatSize`/`restRect`/`clampPos`/`inSlot` geometry (measured off the memo modal, via
  `--lys-dock-w`) to `useDockTear`, and renders `LyricsSheetContent` with `panelClassName`/`headHandlers`/
  `placementControl` wired through. `inSlot` today is the dock column's bounds **padded by 28px on every
  side**, spanning the modal's full height — a large, implicit hit-box with no matching visual outline other
  than the `.lys-dock-hint` dashed box (which is drawn smaller, `inset: 16px 12px` inside the slot, so the
  hit-box does not equal the visual affordance).
- `src/components/member/lyrics/LyricsSheet.tsx` — `LyricsSheetContent` (the placement-agnostic sheet: owns
  lyrics data/mode/annotations/translation/copy state, and renders **both** its own `<header class="lys-head">`
  (title + mode/anno/translate/copy actions, and the pointer-drag handle) **and** its own `.lys-body`). Also
  exports `LyricsSheet` (float-only standalone wrapper for the other surfaces above).
- `src/components/member/ResearchNote.tsx` — album-scoped research note, `variant: 'panel' | 'rail' | 'doc'`.
  `'doc'` renders via `NoteBody` (sectioned) with no own collapse header (host owns the title). Has its own
  data lifecycle (`useResearch(albumId, {auto})`) independent of any panel/dock state.
- `src/components/member/AlbumDetail.tsx` `MemoWindow`:
  - `sheet: {trackId, meta} | null` gates the **entire** lyrics dock apparatus (`dockCapable = sheet != null
    && !mobile`). Opening a track's lyrics (`openSheet`) always resets `dock` to `INITIAL_DOCK` (re-docks).
  - Research notes are a **separate, non-dockable** inline expansion: a `.memo-research` block with a
    `.memo-research-toggle` button (chevron) directly below the memo textarea, rendering
    `<ResearchNote albumId variant="doc">` when `researchOpen`. `album.focusResearch` auto-opens + scrolls it
    into view on mount (one-shot).
  - `.lys-dock-slot` (reserved right column, collapses to width 0 when not docked/dragging) lives in
    `memo-dock-main`, sized via `--lys-dock-w` (per memo size: m/l/xl → 340/440/560px).
  - Mobile (`useIsMobileHost`, `<768px`) renders the lyrics sheet as a plain float `<LyricsSheet>` (no dock);
    research notes still only exist as the inline expansion — there is no mobile equivalent of a floating
    panel for research today.
- No existing test file covers `dockTear.ts`, `DockableLyricsSheet.tsx`, or `MemoWindow`'s panel/dock
  behavior (`AlbumDetail.addTrack.test.tsx` / `AlbumDetail.dragTrack.test.tsx` cover unrelated flows).

## Target state

- `src/lib/dockTear.ts`: `useDockTear` gains a per-drag "armed" gate, tracked in the local (non-React-state)
  `DragState`, not in `DockState` — no public API break. `d.wasOutsideSlot` starts `false` at the moment a
  drag becomes "torn" (float) and only flips `true` the first time `pointermove` observes `!inSlot(x, y)`
  during that same continuous drag. `pointerup` docks iff `wasTorn && d.wasOutsideSlot && inSlot(x, y)`. A
  drag that starts already inside the slot and never leaves it cannot dock, no matter how it ends. The
  explicit "도킹" button (`togglePlacement`) is untouched — it docks unconditionally, remaining the reliable
  fallback (item 5's last bullet).
- `inSlot`'s hit-box is tightened to match the visible `.lys-dock-hint` affordance (from a 28px pad to a
  small pad matching the hint's own inset) so the explicit target and its preview are the same region.
- A new component, `src/components/member/panel/ContextPanel.tsx`, generalizes `DockableLyricsSheet` into a
  **tabbed** panel: `가사` (Lyrics) / `리서치 노트` (Research Notes). Desktop variant wraps `useDockTear`
  exactly as `DockableLyricsSheet` did (same geometry contract, host = memo modal); mobile variant
  (`< 768px`) renders the same tab body markup in a plain floating, header-drag-to-reposition, **never
  dockable** shell (module-level branch, not a prop toggle — mirrors today's `mobile ? <LyricsSheet> :
  <DockableLyricsSheet>` split in `MemoWindow`). `DockableLyricsSheet.tsx` is removed; its only caller
  (`MemoWindow`) moves to `ContextPanel`.
- `LyricsSheet.tsx` is refactored (no behavior change for its existing standalone consumers) to expose the
  lyrics state/toolbar/body as reusable pieces so `ContextPanel`'s Lyrics tab can render them under a
  panel-level (not lyrics-owned) header. `LyricsSheetContent`/`LyricsSheet` keep composing the same pieces
  into their existing all-in-one layout — `LikedBoard`, `AlbumDetailView`, and any other float-only caller
  see no change.
- `ContextPanel` mounts **both** tab bodies at all times once the panel is open and toggles visibility with
  a CSS class (not conditional JSX), so switching tabs preserves each pane's scroll position and in-flight
  state (open annotation, refine-instruction draft, etc.) without remounting either. The Lyrics pane renders
  an explicit empty state (예: "트랙을 선택하면 가사가 여기 표시됩니다") when no track is selected instead of
  attempting to fetch with an empty id.
- `MemoWindow` replaces `sheet`/`researchOpen` with a single panel-state shape (`panelOpen`, `tab`, `track`)
  driving `ContextPanel`. The old `.memo-research` inline toggle + block is deleted once the new panel is
  verified working; a small "리서치 노트 열기" affordance in its place opens the panel on the Research tab.
  `.lys-dock-slot` reservation now gates on `panelOpen && !mobile` (was `sheet != null && !mobile`).
- Tests: `dockTear` re-arm behavior (unit, jsdom pointer-event simulation), `ContextPanel` tab-switch state
  preservation + empty state, and a `MemoWindow`/panel integration test for open/close/dock/float
  transitions.

## Steps

### Step 1 — dock re-arm fix + generalized ContextPanel + MemoWindow wiring + mobile variant + tests

Single PR. Frontend-only, no infra/contract/auth surface touched, so no ordering dependency on another repo.

1. `dockTear.ts`: add the per-drag `wasOutsideSlot` gate; tighten `inSlot` callers' padding is a caller-side
   change (each host defines its own `inSlot`), so the shared hook change is only the gating logic.
2. `ContextPanel.tsx` (new, `src/components/member/panel/`): desktop dockable + mobile floating variants,
   tabs, empty state, per-tab-mounted panes.
3. `LyricsSheet.tsx`: extract reusable state/toolbar/body; `LyricsSheetContent`/`LyricsSheet` unchanged in
   behavior.
4. `AlbumDetail.tsx`: `MemoWindow` rewires to `ContextPanel`; remove `DockableLyricsSheet.tsx` and the old
   `.memo-research` inline block (after manual verification the new panel works).
5. `layout.css`: tighten `inSlot`'s companion visual (`.lys-dock-hint` inset) if the hit-box tightening
   changes it; add tab/pane classes.
6. Tests per Target state.

**Verification**:
```
pnpm lint && pnpm exec astro check && pnpm test
```
Plus a real-browser (CDP) clickthrough: open a bucket memo → open a track's lyrics (docks) → switch to
Research tab (state preserved) → switch back to Lyrics (scroll preserved) → drag panel off (floats) → nudge
it near the dock column without leaving/re-entering (must NOT dock) → drag fully out and back in
(dock preview shows, drop docks) → explicit 도킹 button (docks unconditionally) → resize to mobile width
(single floating tabbed panel, no dock column, no drag-to-dock).

**Rollback**: revert the PR; `DockableLyricsSheet.tsx` + the inline research block are removed in the same
PR so a straight revert restores both without a second step.

---

## Open questions

None blocking — scope, naming, and mobile behavior were resolved during audit/design in this session per
the owner's ask. If real-browser verification surfaces a UX call (e.g. exact dock-hint padding), it will be
logged in the Decisions log below rather than blocking the step.

## Decisions log

| Date | Decision | Step |
|------|----------|------|
| 2026-08-10 | Single-PR merge (owner directive this session) rather than multi-step RFC | — |
| 2026-08-10 | Re-arm gate lives in `useDockTear`'s local `DragState`, not `DockState` — no public API/consumer change | Step 1 |
| 2026-08-10 | Keep `.lys-*` CSS prefix; no rename sweep | Step 1 |
