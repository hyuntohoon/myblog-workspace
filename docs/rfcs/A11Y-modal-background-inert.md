# A11Y-modal-background-inert: deactivate the background while a modal is open

- **Status**: draft
- **Owner**: 오너
- **Created**: 2026-08-16
- **Plan row**: `plan.md` → A11Y-modal-background-inert
- **Origin**: `docs/archive/done/rfcs/ARCH-overlay-modal-isolation.md` OQ2, which deliberately scoped
  this out ("Non-goals") after fixing scroll isolation only. This RFC does not reopen that one.
- **Repository**: `myblog_front` only

---

## Goal

While a scrim-backed modal is open, the rest of the page stops existing for assistive technology: a
screen-reader user in browse mode cannot arrow-key their way out of the dialog into the page behind
the scrim. Achieved by marking every `<body>` child that does not contain the top open dialog as
`inert`, from one place, with no per-modal bookkeeping.

## Non-goals

- **Focus trap, ESC-to-close, focus restore.** All three already exist and work
  (`src/lib/useDismissable.ts`). Nothing about Tab-key behaviour changes.
- **Background scroll lock.** Already shipped by `ARCH-overlay-modal-isolation` Step 1
  (`src/lib/useScrollLock.ts`). This RFC reuses its modality signal but does not alter it.
- **Anchored, non-scrim popups.** `OverviewDash`'s "add widget" menu, `gm-shared`'s peek, the Pocket
  add-to-bucket menu in its menu (not sheet) form: these are deliberately not modal and must keep
  the page behind them live. They are identified by already opting out of scroll lock.
- **A general a11y audit.** No colour-contrast, heading-order, label or landmark work. One defect.
- **`aria-hidden` as the mechanism.** See Current state for why `inert` is the correct primitive and
  `aria-hidden` alone is not.

## Current state

`src/lib/useDismissable.ts` (28 call sites across 20 files) already provides, per open overlay:

- ESC-to-close, one layer at a time, via a module-level `openStack` that lets only the top entry act;
- a Tab focus trap (`visibleFocusables` + wrap-around at both ends), also top-of-stack only;
- focus capture on open and restore-to-trigger on close;
- optional `lockScroll`, composing in `useScrollLock`.

**What is missing is narrower than the archived RFC's OQ2 line suggests.** That line reads
"doesn't deactivate the background for screen readers/tab order". The tab-order half is already
handled — the trap above is real and tested (`src/lib/useDismissable.test.ts`). The remaining hole is
specifically **screen-reader browse mode**: a virtual cursor (VoiceOver's arrow keys, NVDA's browse
mode) does not move DOM focus, so a focus trap constrains nothing. The reader walks straight through
the scrim into the header, the article, and the footer, reading content the sighted user cannot see
or reach. `role="dialog" aria-modal="true"` is already set on the dialogs and does not fix this on
its own — `aria-modal` is advisory and unevenly honoured; `inert` is the primitive that actually
removes a subtree from the accessibility tree *and* from hit-testing and focus.

Confirmed by grep against `myblog_front` `origin/main` on 2026-08-16: **zero occurrences of `inert`
anywhere in `src/`.** The only `aria-hidden` uses are on decorative glyphs and SVGs.

**The modal population is enumerable, not a judgement call.** This codebase already encodes "is this
overlay modal?" as "does it lock background scroll?":

- 11 `useDismissable(..., { lockScroll: true })` call sites — `gm-shared`, `BucketBoard` ×2,
  `ImportAnalysis`, `OverviewDash` ×2, `AddToBucketMenu`, `CommandPalette`, `DraftsInbox`,
  `SettingsPanel`, `WriterApp`;
- 13 direct `useScrollLock()` callers — `AlbumOverlay`, `TodayPickHistory`, `TodaySongPicker`,
  `ActionSheet`, `AddAlbumModal`, `AddArtistModal`, `AlbumDetail`, `BucketPickerSheet`,
  `LyricsSheet`, `LyricsViewer`, `ContextPanel`, `PlaybackPanel`, `PocketDesignSettings`.

Most of the second group also call `useDismissable` separately. **Exactly three do not**:
`ActionSheet`, `BucketPickerSheet`, `PocketDesignSettings`. Those three are scrim modals with
`role="dialog" aria-modal="true"` that today have **no focus trap and no focus restore** —
`ActionSheet` hand-rolls its own `window` ESC listener instead. That is a pre-existing gap this RFC
found rather than created; Step 2 closes it.

**The DOM shape that makes this non-trivial.** `src/layouts/layout.astro` renders these `<body>`
children: `<SkipNavLink>`, `<div class="site-shell">` (header + page + footer), the `PocketBuckit`
island, the `AlbumOverlay` island, `<IosInstallHint>`. Overlays reach the top in two different ways:

- **portalled** — `createPortal(<scrim>, document.body)`, so the scrim becomes its own `<body>`
  child (`ActionSheet`, `BucketPickerSheet`, and the notice portals);
- **rendered in place** — inside whichever island already owns them, e.g. `CommandPalette` and
  `DraftsInbox` live under `.site-shell`, and `AlbumOverlay`'s dialog lives in its own island root.

So "the background" is not a fixed selector. Inerting `.site-shell` unconditionally would inert the
writer's own command palette. The mark has to be computed per-open-dialog.

## Target state

`useDismissable` gains one option, `inertBackground`, defaulting to `lockScroll`'s value — so every
overlay that already declares itself modal by locking scroll gets background deactivation with no
call-site change, and every anchored popup that opted out of scroll lock stays opted out of both.

A module-level refcounted controller (the same shape as `useScrollLock`'s `lockCount`/`prevOverflow`,
which exists precisely because these overlays nest) does the work:

1. On the first modal open, walk up from the top dialog's `ref.current` to its `<body>` child
   ancestor. Set `inert` on every *other* `<body>` child, remembering which ones were already inert.
2. On nested open, recompute against the new top of `openStack` — the outer dialog's body-child
   ancestor becomes inert too, unless it is also the inner one's ancestor.
3. On close, pop and recompute. Restore exactly the elements the controller set, never the ones that
   were already inert.

Nothing else changes: same ESC, same trap, same scroll lock, same markup.

## Steps

### Step 1 — central `inertBackground` mechanism, applied to existing modals

Add the controller and the option to `src/lib/useDismissable.ts`, defaulting `inertBackground` to the
resolved `lockScroll`. No component file changes: the 11 `lockScroll: true` call sites inherit it,
and the overlays that pair `useDismissable` with a direct `useScrollLock()` opt in by passing
`inertBackground: true` at their existing `useDismissable` call.

The controller must be resilient to the two things this codebase has already been bitten by:

- **`ClientRouter` keeps module state alive across navigations** while components remount
  (the `capabilityTier` regression in `ARCH-global-playback-experience` Step 1). A route change with
  a modal open must not strand an `inert` attribute on `.site-shell` forever. The recompute is
  driven off `openStack`, and the effect cleanup runs on unmount, so an empty stack always restores.
- **`transition:persist` islands are body children too.** Inerting `PocketBuckit` while a dialog is
  open is correct and intended, but the persistent playback bar lives inside it — confirm the bar
  is unreachable-by-AT, not merely visually behind, while a modal is open.

**Verification**:
```
cd myblog_front
pnpm lint && pnpm exec astro check && pnpm test
# new unit tests in src/lib/useDismissable.test.ts: sets inert on siblings only, never on the
# dialog's own body-child ancestor; nested open/close restores in order; pre-existing inert
# attributes survive; empty stack leaves zero inert attributes behind.
```
Plus a real-browser CDP pass (`feedback-verify-front-live-dom-not-harness`): open a modal, assert
`document.body.children` inert flags in the live DOM, navigate via `ClientRouter` with the modal
open, assert nothing is stranded.

**Rollback**: `inertBackground` defaults to `false`. One-line revert, no data, no contract.

---

### Step 2 — migrate the three scrim modals that never got `useDismissable`

`ActionSheet`, `BucketPickerSheet` and `PocketDesignSettings` call `useScrollLock()` and declare
`aria-modal="true"` but never adopted `useDismissable`, so they have no focus trap and no focus
restore, and `ActionSheet` carries a hand-rolled `window` ESC listener that does not participate in
the nesting stack. Replace with `useDismissable(true, onClose, ref, { lockScroll: true })`, deleting
the bespoke listener. They pick up background inert from Step 1 as a consequence.

Sequenced after Step 1 so the two changes are separable if the migration surfaces a regression in
these three surfaces specifically.

**Verification**:
```
cd myblog_front && pnpm lint && pnpm exec astro check && pnpm test
```
Plus CDP: on each of the three, ESC closes exactly one layer, Tab cycles inside the sheet, focus
returns to the trigger on close.

**Rollback**: revert the three call sites; Step 1 stands alone.

---

## Open questions

1. **Is the persistent playback bar meant to stay operable while a modal is open?** — blocks Step 1's
   second bullet. `PlaybackPersistentBar` mounts inside `PocketBuckit`, a `<body>` child, so the
   default treatment inerts it along with the rest of the background. Options: (a) inert it like
   everything else — consistent, but a user cannot pause playback without closing the dialog;
   (b) exempt the `PocketBuckit` island from inert — keeps transport reachable, but then AT can also
   reach the whole tray behind the scrim, which is the defect this RFC exists to fix; (c) exempt only
   the bar element. Recommendation is **(a)**: it matches what sighted users already get (the scrim
   covers the bar), and the RFC's whole premise is that AT should not have reach that sighted
   interaction does not.
2. **Does anything need `inert` without wanting scroll lock, or vice versa?** — blocks nothing;
   decide only if Step 1's default turns out to mis-handle a specific surface. Recorded so a future
   reader knows the coupling was deliberate, not accidental.

## Decisions log

| Date | Decision | Step |
|------|----------|------|
| 2026-08-16 | RFC drafted on owner's in-session approval to promote the frozen `ARCH-overlay-modal-isolation` OQ2 idea. Current-state audit corrected the origin line: the focus trap already exists, so the defect is screen-reader browse mode only, and the modal population is enumerable from the existing `useScrollLock` signal rather than needing judgement. Audit also found a pre-existing gap the idea did not mention — three scrim modals never adopted `useDismissable` at all — now Step 2. | — |
