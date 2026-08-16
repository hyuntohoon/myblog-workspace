# A11Y-modal-background-inert: deactivate the background while a modal is open

- **Status**: **accepted** (owner-approved in-session 2026-08-16, together with OQ1)
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

`src/lib/useDismissable.ts` (31 call sites across 21 files — the RFC first said 28 across 20; corrected against `origin/main` on implementation, 2026-08-16) already provides, per open overlay:

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

### Step 1 — central `inertBackground` mechanism, applied to existing modals — **SHIPPED 2026-08-16 (front #411)**

Add the controller and the option to `src/lib/useDismissable.ts`, defaulting `inertBackground` to the
resolved `lockScroll`. The 11 `lockScroll: true` call sites inherit it with no edit; the overlays that
pair `useDismissable` with a direct `useScrollLock()` opt in by passing `inertBackground: true` at their
existing `useDismissable` call — 11 sites across 10 component files. (This paragraph originally opened
"No component file changes", which contradicted its own next clause; corrected on implementation.)

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

**Result (2026-08-16, front #411).** `pnpm lint` clean · `astro check` 0 errors/0 warnings (300 files) ·
`pnpm test` 654 passed, 0 skipped, including 8 new `inertBackground` tests. Each new test was checked
against a deliberately broken build so none of them is tautological: a no-op `syncInert()` fails 6 of
the 8, removing the `astro:after-swap` sweep fails exactly the strand test, and declaring the
registration effect after the focus effect fails both the ordering test and the pre-existing
focus-restore test.

CDP on local dev, home page, `AlbumOverlay`: with the modal open every `<body>` child carries `inert`
except the island holding the dialog, a background link is not focusable, hit-testing at its
coordinates returns `div.scrim`, and the accessibility tree contains **only the dialog** (13 nodes).
Same page with the marks stripped: **176 background nodes** — the primary nav, every album card, the
footer, the Pocket tray. That pair is the before/after measurement of the defect. `ClientRouter`
navigation with the modal open: 5 inert before, 0 after, nothing stranded. ESC: dialog closes, inert 0,
scroll lock released, focus restored to the background trigger.

Two implementation findings worth carrying forward:

- **Effect order is load-bearing.** Applying `inert` blurs whatever the background had focused, and
  focusing back into an inert subtree is a no-op — so the registration effect both captures the
  restore target and is declared *before* the focus effect, whose cleanup therefore runs second, after
  the background is live again. The naive order silently drops focus restore for every modal.
- **Separating stack registration from the key-handling effect** means a `trapFocus` change
  (`ContextPanel`'s `trapFocus: dock.docked`, `PlaybackPanel`) no longer shuffles that overlay to the
  top of `openStack`. That was a latent bug in the pre-existing code, fixed as a side effect.

**Rollback**: `inertBackground` defaults to `false`. One-line revert, no data, no contract.

---

### Step 2 — migrate the three scrim modals that never got `useDismissable` — **SHIPPED 2026-08-16 (front #412)**

`ActionSheet`, `BucketPickerSheet` and `PocketDesignSettings` call `useScrollLock()` and declare
`aria-modal="true"` but never adopted `useDismissable`, so they have no focus trap and no focus
restore, and `ActionSheet` carries a hand-rolled `window` ESC listener that does not participate in
the nesting stack. Replace with `useDismissable(true, onClose, ref, { lockScroll: true })`, deleting
the bespoke listener. They pick up background inert from Step 1 as a consequence.

Sequenced after Step 1 so the two changes are separable if the migration surfaces a regression in
these three surfaces specifically.

**Two claims in the paragraph above were wrong, checked against `origin/main` before implementing:**

- `BucketPickerSheet` hand-rolled the **same** `window` ESC listener; the paragraph named only
  `ActionSheet`. Both are deleted.
- `PocketDesignSettings` carried `role="dialog"` **without** `aria-modal`, and had **no keyboard exit
  at all** — only a scrim tap and the 닫기 button closed it. `aria-modal="true"` was added with the
  migration. Its a11y gap was therefore larger than "no trap, no restore".

**Verification**:
```
cd myblog_front && pnpm lint && pnpm exec astro check && pnpm test
```
Plus CDP: on each of the three, ESC closes exactly one layer, Tab cycles inside the sheet, focus
returns to the trigger on close.

**Result (2026-08-16, front #412).** `pnpm lint` clean · `astro check` 0 errors/0 warnings
(301 files) · `pnpm test` 663 passed, 0 skipped (654 → +9). None of the 9 new tests is tautological:
each was run against the `origin/main` implementation restored in place and all 9 fail there. The
pre-existing `ActionSheet` ESC assertion moved from `window` to `document` — the shared hook listens
on `document` in the capture phase, and an event dispatched at `window` never reaches it.

CDP on the **real** authenticated member board (local dev → local auth proxy → prod API, since
`isLocalEnv()` forces the literal `local-dev` token on `localhost`; coarse-pointer emulation for the
⋯ triggers; every trigger `focus()`-ed before `click()` so restore is actually testable):

| | `PocketDesignSettings` | `ActionSheet` | `BucketPickerSheet` |
|---|---|---|---|
| DOM shape | rendered in place | portalled to `<body>` | portalled to `<body>` |
| `<body>` children inert / total | 5 / 6 | 6 / 7 | 6 / 7 |
| background a11y nodes, marks applied | **2** | **0** | **0** |
| background a11y nodes, control (marks stripped) | **63** | **218** | — |
| autofocus inside · Tab wrap both ways · ESC · restore to trigger | ✅ | ✅ | ✅ |

The control column is the before/after measurement: same open dialog, marks removed, everything else
identical. `PocketDesignSettings` keeps **2** background nodes because it renders inside the
`PocketBuckit` island and Step 1's controller deliberately keeps the dialog's own `<body>`-child
ancestor live — so the two tray controls behind the scrim stay in the tree. That is Step 1's
documented shape, not a Step 2 regression; before this PR that surface had no `inert` at all.

Step 1 only exercised an in-place island, so the `ClientRouter` case was re-checked for the portalled
shape: navigating with a portalled sheet open leaves 6 inert → 0, no stranded scrim, scroll lock
released.

**Rollback**: revert the three call sites; Step 1 stands alone.

---

## Open questions

1. ~~**Is the persistent playback bar meant to stay operable while a modal is open?**~~ — **RESOLVED
   2026-08-16 (owner): option (a), inert it like everything else.** `PlaybackPersistentBar` mounts
   inside `PocketBuckit`, a `<body>` child, so it takes the default treatment with no exemption code.
   The rejected alternatives, recorded so this is not relitigated: (b) exempting the whole `PocketBuckit`
   island would leave AT able to reach the entire tray behind the scrim — the defect this RFC exists to
   fix; (c) exempting only the bar element would preserve transport at the cost of a special case in the
   controller. (a) matches what sighted users already get, since the scrim covers the bar. **Consequence
   to verify in Step 1, not assume:** with a modal open, the bar must be unreachable by AT — assert it in
   the live DOM, not merely that it is painted behind the scrim.
   **Verified 2026-08-16 (front #411), with the bar actually rendered rather than reasoned about:** with
   a modal open the accessibility tree carries no `region "재생 중"` and the bar's `재생 패널 열기` button
   is not focusable; the control run, with `inert` removed from that island only, lists the region and
   all four transport buttons. The consequence the owner accepted is what ships.
2. **Does anything need `inert` without wanting scroll lock, or vice versa?** — blocks nothing;
   decide only if Step 1's default turns out to mis-handle a specific surface. Recorded so a future
   reader knows the coupling was deliberate, not accidental. **Step 2 surfaced no such case** — all
   three migrated surfaces wanted both — so this stays open and undecided rather than closed by
   absence of evidence.

## Decisions log

| Date | Decision | Step |
|------|----------|------|
| 2026-08-16 | RFC drafted on owner's in-session approval to promote the frozen `ARCH-overlay-modal-isolation` OQ2 idea. Current-state audit corrected the origin line: the focus trap already exists, so the defect is screen-reader browse mode only, and the modal population is enumerable from the existing `useScrollLock` signal rather than needing judgement. Audit also found a pre-existing gap the idea did not mention — three scrim modals never adopted `useDismissable` at all — now Step 2. | — |
| 2026-08-16 | **Owner approved; Status draft → accepted, and OQ1 answered (a) in the same decision** — the persistent playback bar is inerted with the rest of the background, no exemption. Step 1 is startable with nothing outstanding; OQ2 was left open by design since it blocks nothing. Promoted in a session that wrote no code for it: the session's own RFC (`DATA-multidisc-track-order` Step 2) was stopped at kickoff when its current-state audit overturned three of its claims, and this RFC was picked as the next startable item because it is single-repo, migration-free and contract-free — which also means it does not depend on the `reviewer` subagent, absent from this environment as of today. | — |
| 2026-08-16 | **Step 2 shipped (front #412) — no steps remain.** The migration's own current-state audit overturned two more RFC claims (`BucketPickerSheet` had the identical hand-rolled `window` ESC listener; `PocketDesignSettings` had `role="dialog"` without `aria-modal` and no keyboard exit at all), making this the **fourth** RFC in a row where the written current state did not survive contact with `origin/main`. Measured against a control on the real authenticated member board: background a11y nodes go 218 → 0 for the portalled sheets and 63 → 2 for the in-place panel. The residual 2 are the tray controls sharing `PocketDesignSettings`'s kept island — Step 1's documented trade-off, not a regression. OQ2 stays open: no surface wanted `inert` without scroll lock. **Status is still `accepted` and the RFC is still in `docs/rfcs/`** — promoting it and archiving it is an owner decision (hard rule 7), not something this session may do. | 2 |
| 2026-08-16 | **Step 1 shipped (front #411).** OQ1's consequence verified rather than assumed — the persistent playback bar is genuinely absent from the accessibility tree with a modal open, measured against a control. The before/after on the home page is 176 background nodes → 0. Two RFC current-state figures were corrected on implementation (call-site count; Step 1's self-contradicting "No component file changes"), the third such RFC in a row to need a current-state correction — `feedback-rfc-current-state-audit` keeps paying for itself. Implementation surfaced one thing the RFC did not anticipate: applying `inert` blurs the background's focused element, so effect declaration order decides whether focus restore survives at all. | 1 |
