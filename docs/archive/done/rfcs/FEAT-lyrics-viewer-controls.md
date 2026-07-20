# FEAT-lyrics-viewer-controls: header/controls redesign — scroll-to-manual + return affordances

- **Status**: done (Steps 1–2 shipped; owner keeper pick 2026-07-20 = **D + A's ring**, loser-removal chore front #298 shipped + prod-smoked same day)
- **Owner**: 박지훈
- **Created**: 2026-07-18
- **Plan row**: `plan.md` → FEAT-lyrics-viewer-controls
- **Origin**: 2026-07-18 UI planning session, area 3. Behavior options were prototyped as an
  interactive artifact; owner picked **both A and D, selectable after implementation**.

---

## Goal

The lyrics viewer loses its raw [자동|수동] and [블러|플랫] control rail: user scroll itself
suspends auto-follow, and two return behaviors — **A: floating-pill + 4s idle auto-return**
(YT Music + Musixmatch synthesis) and **D: Apple-style browse mode** (un-dim + line-tap surface
+ 3s snap-back) — are both implemented and switchable, so the owner picks the keeper after real
use. Style (블러/플랫) and behavior (A/D) settings move into a small ⚙ popover. Lyrics data,
translation lifecycle, and clock-estimate mechanics are untouched.

## Non-goals

- Any change to `GET /api/lyrics/*`, normalization, translation request lifecycle, or the
  estimator math (`estimatedMs = anchorMs + (performance.now() − wallMs)`).
- Dock/memo-window work — verified: the live viewer is a fixed full-screen overlay
  (`SelfDashboard.tsx:198`), not a dock host; DockState untouched.
- Player-bar work (FEAT-member-player). Seek-on-tap here reuses that RFC's full-tier seek only
  once it exists; until then tap = re-anchor.

## Current state (verified 2026-07-18)

- `LyricsViewer.tsx` — header :654-717 (eyebrow `Lyrics · source` / title / artist / translation
  cluster / ↻ / ✕), rail :771-828 ([자동|수동] + [블러|플랫]).
- **Mode mechanics**: only the explicit 수동 button leaves auto (`mode` :254). Scroll/swipe/
  wheel/keys call `moveFocusTo` :426-434 which **re-anchors but keeps mode** — so
  "scroll-suspends-follow" is a new behavior, not a rewire. Hooks available: `applyAnchor`
  :277-289, `refresh()` :356-393, `trackable` :249 gate.
- Style: `lyvStyle` blur|flat, localStorage `'lyv:style'` :180-231, applied via
  `data-lyv-style` :639.
- Artist in header is a plain string — id plumbing arrives via RFC-ui-surface-unification
  Step 4 (dependency for the header artist link only).
- UX research (scratchpad `ux-research-player-lyrics.md`): Spotify = no return affordance
  (anti-pattern, community pain); Apple = scroll-as-seek-surface + ~3-5s snap-back; YT Music =
  idle auto-resume; Musixmatch = floating return pill.

## Target state

- **Behavior A (합성안)**: wheel/touch suspends follow instantly → floating "↩ 현재 줄로" pill
  with a countdown ring → 4s idle auto-return → line tap re-anchors (or seeks, full tier).
- **Behavior D (Apple식 browse)**: scroll enters browse mode (dim lifted, all lines readable,
  every line a tap target) → 3s idle snap-back re-dims → tap seeks (full tier) / re-anchors
  (fallback tier).
- **Both shipped**, selected in the new ⚙ popover (persisted alongside style); default = A.
  A final owner pick after prod use removes the loser (follow-up chore, not this RFC).
- **⚙ popover** (owner decision 7): style choice as two icon+mini-preview options; behavior
  A/D choice; replaces the bottom rail entirely. Non-trackable rows: rail-less too — a small
  "동기화 없음 — 수동" note in the popover trigger area.
- **Header redesign**: keep the element set (eyebrow, title/artist, translation cluster, ↻, ✕),
  regroup — translation states become compact; artist becomes a link once ids flow.
- Reference prototype: claude.ai artifact "가사 뷰어 자동복귀 — 디자인 옵션" (2026-07-18) —
  A/D behaviors, timings, and implementation hooks demonstrated interactively.

## Steps

### Step 1 — behavior engine: scroll-suspend + A/D return modes (front)

New suspend state driven by wheel/touchstart (distinct from programmatic scrolls); A: pill +
4s timer; D: browse class + 3s snap-back; both re-enter follow via `moveFocusTo`/`applyAnchor`.
Setting persisted (`lyv:behavior`). Remove [자동|수동] segment; keep an accessibility-visible
status line (SR counter :825 stays).
**Verification**: real-browser click-through — wheel mid-track suspends; pill returns; idle
returns; D un-dims + taps re-anchor; `prefers-reduced-motion` path.

> **Shipped 2026-07-19** — front #289 (squash `5f7f184`). Key implementation choice: browse
> inputs (wheel/drag/keys) no longer re-anchor the clock estimate — tap is the only
> re-anchoring nav, so the live position survives browsing and return = `focusIndexForMs`
> over the untouched anchor. Interim [필|브라우즈] rail segment until the Step 2 popover.
> Verified: `pnpm lint` + `astro check` clean; CDP fetch-mock click-through 27/27
> (suspend/pill/idle-return/tap-re-anchor/browse dim-lift+snap-back/reduced-motion/390px
> touch); prod smoke post-deploy (bundle marker + /members/ 200) quoted in PR comment.

### Step 2 — ⚙ popover + header regroup (front)

Popover hosts style (블러/플랫 as icons) + behavior (A/D); rail removed; header regrouped per
mockups (frontend-design skill at implementation).
**Verification**: click-through desktop + 390px CDP; localStorage prefs survive reload;
translation cluster states (done/requested/failed/stale) all render.

> **Shipped 2026-07-20** — front #295. OQ3 resolved: header ⚙ (owner pick, mockup question).
> Popover = dark plate extending the viewer idiom; style tiles carry pure-CSS mini-previews;
> return rows are radios with timing descriptions; picks keep the popover open for live
> compare. Dismiss = house pattern (useDismissable stack — ESC closes popover before viewer —
> + outside pointerdown). `role="dialog"` (radiogroup inside; menu semantics would be wrong).
> Verified: lint + astro check clean; CDP 24/24 incl. all four translation states, plain-row
> 동기화 없음 note, reload persistence, 390px on-screen. **Implementation complete — remaining
> work is the owner's A/D keeper pick after prod use (follow-up chore, not this RFC).**

## Open questions

1. **Idle timings** (A: 4s, D: 3s) — constants, tune after use. Blocks nothing.
2. **Tap-to-seek activation** — wire to FEAT-member-player full-tier seek when that ships, or
   pre-wire behind the same 403-probe? Default: re-anchor until player RFC lands. Blocks
   nothing now.
3. **Popover placement** — header ⚙ vs bottom-corner floating; decide with mockups in Step 2.

## Decisions log

| Date | Decision | Step |
|------|----------|------|
| 2026-07-18 | Owner: implement BOTH A and D, switchable; final pick after prod use | 1 |
| 2026-07-18 | Owner: 블러/플랫 → ⚙ 설정 popover | 2 |
| 2026-07-19 | Step 1 ships an interim [필|브라우즈] rail segment (A/D switch) — absorbed into the ⚙ popover in Step 2 | 1 |
| 2026-07-19 | Browse nav (wheel/drag/keys) does NOT re-anchor the estimate; line tap is the only re-anchoring nav (return needs the live anchor) | 1 |
| 2026-07-20 | OQ3: popover trigger = header ⚙ (owner pick via mockup comparison) | 2 |
| 2026-07-20 | **Owner keeper pick: D (browse), with A's circular countdown grafted on** ("d, 원위치 시간 표시 원형으로 돌아가는 건 a처럼 하자") — browse mode keeps un-dim + 3s snap-back, and A's ring becomes a compact floating browse-mode control (clocks the snap-back, restarts per browse input, tap = immediate return). Behavior A (pill), the ⚙ 복귀 section, and `lyv:behavior` storage removed | close |
| 2026-07-20 | **Keeper chore SHIPPED + prod-smoked** — front #298 (+32/−131). CDP 14/14 vs the real SelfDashboard flow (browse ring 42px circular @3000ms, restart, snap-back, tap-return, popover style-only, stale storage key harmless, mobile 390 clean). RFC CLOSED → archived | close |
