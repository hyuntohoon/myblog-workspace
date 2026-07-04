# FEAT-lyrics-auto-progression: Clock-based auto-advancing lyrics + Spotify-style redesign

- **Status**: draft
- **Owner**: 박지훈
- **Created**: 2026-07-04
- **Plan row**: `plan.md` → FEAT-lyrics-auto-progression

---

## Goal

Repeal FEAT-lyrics-viewer's manual-navigation-only constraint and add **continuous, playback-driven auto-advancing lyrics** with a full **Spotify-style visual redesign** (album-blur background + large focus-line typography). A viewer opened with a synced track now auto-scrolls the focused line as playback progresses, using a **client-side clock estimate** seeded from the one-shot `readLivePlayback()` position; the owner can still take over manually at any time, which **self-corrects** the estimate against the jumped-to line's `start_ms`. The viewer keeps both **auto** and **manual** modes, switchable live. No backend, contract, schema, or infra change — front-only.

## Non-goals

- **No backend / API / schema / infra change.** This RFC reuses the existing `GET /api/lyrics/{spotify_track_id}` (JWT-gated) and the existing `readLivePlayback()` one-shot REST read. No new endpoint, no DB column, no apigateway route, no terraform. Front-only.
- **No Web Playback SDK coupling.** The auto-advance is driven by a **local clock estimate**, not by `player_state_changed` events and not by polling `GET /v1/me/player`. The existing `player`/`deviceId` singletons in `spotifyPlayback.ts` stay module-private and untouched. This sidesteps the cross-device limitation (the 'Buckit' SDK device only reflects its own playback) and the rate-limit risk of polling.
- **No position source other than the existing one-shot `readLivePlayback()`.** No second `GET /v1/me/player` poll, no SDK `getCurrentState()`, no server-side progress exposure (D28 stays). The clock estimate drifts between syncs and is corrected by manual override + the re-sync button, never by continuous polling.
- **No translation.** Same as FEAT-lyrics-viewer: original lyrics only. Translation remains a separate RFC (FEAT-lyrics-translation, in progress).
- **No playback controls.** The viewer still has no play/pause/seek UI. It observes playback position read-only; it does not control it. `user-read-playback-state` scope only (no `user-modify`).
- **No change to the privacy boundary.** Lyrics remain JWT-gated, authenticated-only, never in any shared/public/edge-cached response. The redesign is visual only.
- **No change to lyric normalization.** The viewer still consumes the `LyricsSegment[]` contract from `GET /api/lyrics/{id}` as-is. No client-side LRC parsing, no timestamp stripping, no raw-text fallback.
- **No sync guaranteed for plain (non-synced) lyrics.** Auto-advance applies only to `trackable` rows (≥1 non-gap segment with `start_ms`). Plain-only rows (`source_kind: "plain"`, `trackable: false`) fall back to **manual-only mode** — no estimate is possible without timestamps.

## Current state

Verified against code 2026-07-04:

- **The viewer exists and is manual-only by explicit design.** `myblog_front/src/components/member/lyrics/LyricsViewer.tsx` renders `LyricsSegment[]` as an editorial "paper" reading surface (serif focus line at `--color-bg`, 3-level emphasis `is-focus`/`is-near`/recessed). The file header comment (lines 1-20) states the manual-only principle explicitly: *"No playback-time progression of any kind (RFC non-goal)."* Navigation: prev/next buttons, vertical swipe/drag (`DRAG_STEP = 56px`), wheel (`WHEEL_STEP = 80px`), arrow keys, tap-to-focus. Focus is centered at ~42% viewport height via programmatic `scrollTo`.
- **The one-shot position seed already exists.** `initialProgressMs` (dynamic entry only) → `pendingFocusMs` ref → consumed once by `focusIndexForMs()` on load → cleared. After that, focus never moves on its own. The plumbing for "position → focus index" is already there; this RFC **extends it from one-shot to continuous**.
- **`readLivePlayback()` returns everything needed.** `myblog_front/src/components/member/lyrics/playback.api.ts` returns `{ state: 'playing', trackId, progressMs, track, artist, album, albumCoverUrl }`. The `albumCoverUrl` is the smallest image ≥232px wide — usable directly as a CSS `background-image` for the blur backdrop (no canvas/CORS issue — it's a CSS background, not `getImageData`).
- **The redesign's CSS lives in `layout.css` lines 529-701** (`.lyv-*` classes, prefix `lyv-`). Dark `--color-bg`, serif `--font-serif`, paper editorial palette. The redesign replaces these classes' visual treatment; the structural markup (scrim/panel/head/body/scroll/list/rail) and the `useDismissable` overlay mechanics stay.
- **No color-extraction code exists anywhere in the repo** (confirmed via exhaustive search: no canvas `getImageData`, no `color-thief`/`node-vibrant`/`fast-average-color`, no PIL/Pillow in backend, no DB `dominant_color` column). The `SubjectHero.tsx` "album color" effect is a **hash-based fake** (`hueFor(subject.id)` → `oklch(0.68 0.105 ${hue})`) that is visually unrelated to the real cover and was explicitly chosen to avoid CORS-fragile canvas sampling. **This RFC does NOT use that approach** — it uses the real cover image as a CSS `background-image` + `filter: blur()`, which is CORS-free (no pixel reads).
- **Three prior RFCs declare auto-progression a non-goal.** This RFC explicitly **repeals** those non-goals (see [Repealed prior non-goals](#repealed-prior-non-goals)). The D28 "position not exposed" boundary is not violated: position still reaches the viewer only via the existing sanctioned one-shot client-side `readLivePlayback()` read, never via a server-exposed progress field and never via continuous polling.

## Target state

A redesigned `LyricsViewer` that **auto-advances** for synced tracks and looks like Spotify's lyrics screen:

### Visual redesign (Spotify-style)
- **Album-blur background.** The focused track's `albumCoverUrl` becomes a full-bleed `background-image` on a layer behind the content, with `filter: blur(72px) saturate(1.9) brightness(0.55)` + `transform: scale(1.35)` (to cover blur edges) + a dark gradient overlay for legibility. The background re-renders on track swap. When no cover URL exists (static/debug entry), fall back to a neutral dark background.
- **Large focus-line typography.** Focus line: `clamp(34px, 7vw, 50px)`, weight 700, sans-serif (`--font-sans`), pure white. Neighbors (±1): `clamp(24px, 4.4vw, 30px)`, weight 600, `rgba(255,255,255,0.7)`. Far lines: `clamp(20px, 3.6vw, 26px)`, `rgba(255,255,255,0.18)`. This replaces the serif/paper 3-level model.
- **Minimal chrome.** Header: `Lyrics · synced/plain` eyebrow + re-sync `↻` (dynamic entry only) + close `✕`. Bottom rail: a single **auto / manual** segmented toggle (the prev/next rail and position counter are removed — manual nav stays available via swipe/drag/tap/keys, but the dedicated rail UI is dropped in favor of the mode toggle). Up/down fade masks over the list edges, strengthened for the dark backdrop.

### Auto-progression (clock-based estimate)
- **Mode state.** A `mode: 'auto' | 'manual'` state, defaulting to `'auto'` when opened on a `trackable` row (synced), defaulting to `'manual'` when `trackable === false` (plain). The toggle is live-switchable.
- **Estimate engine.** On open (and on each re-sync), `readLivePlayback()` returns `progressMs`. The viewer records `{ anchorMs: progressMs, anchorWallMs: performance.now() }`. A `requestAnimationFrame` loop (or a ~250ms interval — see Open Questions) computes `estimatedMs = anchorMs + (performance.now() - anchorWallMs)`, maps it through `focusIndexForMs()` (existing helper, reused), and updates `focus` **only when** the index changes (avoids re-render churn). The loop pauses when `document.hidden` and on `manual` mode.
- **Manual override = self-correction.** When the owner manually moves focus (swipe/tap/keys) in either mode, the viewer sets `anchorMs = segs[newFocus].start_ms` (the jumped-to line's timestamp) and `anchorWallMs = performance.now()`, then (if in auto mode) resumes estimating from the new anchor. This is the drift-correction mechanism: the user realigns the estimate to the real playback by jumping to the line they hear. If the jumped-to line has no `start_ms` (plain row in a mixed row), the anchor is left unchanged (best-effort).
- **Re-sync button (`↻`).** Re-fires `readLivePlayback()`, re-seeds `{ anchorMs, anchorWallMs }` from the fresh `progressMs`, and (track change → swap segments; same track → just re-anchor). Same semantics as today's refresh, but the anchor now feeds the continuous estimate instead of a one-shot focus.
- **Drift tolerance.** Between syncs the estimate can drift (Spotify playback rate is exactly 1.0, but `performance.now()` and the seed `progressMs` snapshot can be seconds stale due to network RTT). The accepted mitigation is: (a) the estimate is "good enough" for line-level focus (lines are typically 3-8s apart, so sub-second drift is invisible); (b) manual override corrects instantly; (c) re-sync re-anchors. No auto-re-sync polling.

### What stays the same
- Overlay mechanics (`useDismissable`, `.lyv-scrim`, ESC + focus trap/restore), the three entry paths (dynamic / static / debug), the JWT-gated read API, the privacy boundary, availability-aware empty states, the `LyricsSegment[]` contract consumption.

## Repealed prior non-goals

This RFC **explicitly repeals** the following non-goals from prior RFCs. The repeal is the core rationale for opening a follow-on RFC rather than amending the (done) originals.

- **FEAT-lyrics-viewer** (`docs/archive/done/rfcs/FEAT-lyrics-viewer.md`):
  - Non-goal "Automatic synchronization" (lines 45-47): *"No continuous playback-time-driven progression, no auto-scroll, no karaoke-style time tracking. Synced timestamps may be used only to define units and, optionally, to set the initial focus on a manual refresh — never to advance it."* → **Repealed**: synced timestamps now drive continuous advance via clock estimate.
  - No-go condition (lines 424-425): *"Continuous-progression is added to 'rescue' a missing position source → reject; degrade to track-only instead."* → **Repealed with a guard**: continuous progression is added, but the position source is the *existing* one-shot `readLivePlayback()` (not a new polling/SDK source), and plain-only tracks still degrade to manual-only. The "rescue a missing source" rejection is honored — we do not invent a new source.
- **RESEARCH-playback-product-architecture** (`docs/archive/done/rfcs/RESEARCH-playback-product-architecture.md`):
  - Non-goal (lines 33-34): *"No continuous-progress karaoke/auto-advance."* → **Repealed**, same rationale: the position source is unchanged (one-shot REST read reused as a clock seed), no polling introduced, no SDK coupling.
  - "never polled" (2026-07-03 amendment, lines 178-183) → **Still honored**: `readLivePlayback()` is still fired only on entry / explicit re-sync, never on a timer. The clock estimate fills the gap between syncs without any network call.
- **ARCH-lyrics-normalization-model** (`docs/archive/done/rfcs/ARCH-lyrics-normalization-model.md`):
  - Non-goal (lines 35-36): *"No continuous / auto-advance sync."* → **Repealed**. (This RFC already designed `start_ms` as optional-from-day-one, so no schema work is needed — the segments already carry the timestamps auto-advance consumes.)

The D28 boundary ("position not exposed server-side") is **not** repealed: server-side `NowPlayingResponse` still omits `progress_ms`/`duration_ms`. Position reaches the viewer only through the existing client-side `GET /v1/me/player` one-shot, exactly as FEAT-lyrics-viewer Step 3 already sanctioned.

## Why clock-estimate (not SDK events, not polling)

The investigation surfaced three options; this RFC picks the third:

1. **Web Playback SDK `player_state_changed` events** — rejected. The `player`/`deviceId` singletons in `spotifyPlayback.ts` are module-private and only initialize on ▶ (transfer to the 'Buckit' device). Crucially, the SDK device only reflects *its own* playback — when the owner plays on iPhone / Spotify desktop (the common case per the RESEARCH probe), `player_state_changed` does not fire for the viewer. Wiring this would require exporting the player, adding a viewer-only SDK-connect path (which pulls token mint into the viewer entry, tension with lazy-mint), and still needs a REST fallback for cross-device. Too invasive for a front-only RFC.
2. **REST polling `GET /v1/me/player`** — rejected. Every prior RFC says "never polled" and Spotify's rolling rate limit makes ~1Hz polling a 429 risk. Repealing "never polled" would also be a broader architectural change than this feature needs.
3. **Clock-based estimate from the one-shot seed** *(this RFC)* — the existing `readLivePlayback()` already returns `progressMs` on entry/re-sync. Seeding `performance.now()` against it and estimating forward is **zero new network calls, zero SDK coupling, zero rate-limit risk**, and degrades gracefully (manual override + re-sync correct drift). The tradeoff is drift between syncs, which is acceptable at line-grain resolution and user-correctable. This keeps the RFC genuinely front-only and the non-goal repeal as narrow as possible.

## Steps

Each step independently mergeable. Front-only — no backend/contract/infra step.

### Step 0 — RFC + plan.md pointer (this document, docs-only)

This RFC + a one-line `plan.md` Backlog pointer. No code, no schema.

**Verification**: doc review against `TEMPLATE.md`. `git diff --stat` shows only the RFC + plan.md.

---

### Step 1 — clock-estimate auto-advance + auto/manual mode (front)

Add the estimate engine and the mode toggle to `LyricsViewer.tsx`, **keeping the current "paper" visual design**. This step is behavior-only (auto-advance + modes); the visual redesign lands in Step 2 so the two are reviewable separately.

- Add `mode: 'auto' | 'manual'` state (default `'auto'` if `trackable`, else `'manual'`).
- Add `{ anchorMs, anchorWallMs }` ref, seeded from `initialProgressMs` (existing) and from each re-sync's `readLivePlayback().progressMs`.
- Add a `requestAnimationFrame` (or interval — OQ1) loop that, in `auto` mode, computes `estimatedMs` and updates `focus` via `focusIndexForMs()` when the index changes. Pause on `document.hidden`.
- Manual nav (existing swipe/tap/keys/prev-next) now **also re-anchors** (`anchorMs = segs[newFocus].start_ms`, `anchorWallMs = now`) so auto resumes correctly from the jumped line.
- Replace the bottom prev/next rail with the **auto/manual segmented toggle** (keep prev/next available via swipe/keys/tap; the dedicated buttons are dropped, or kept behind the toggle — OQ2).
- The `↻` re-sync re-anchors (today it re-seeds focus one-shot; now it seeds the continuous anchor).

**Verification**: open the viewer on a synced track from an active session; the focus advances on its own as the track plays; tapping a line jumps focus there and auto-advance continues from that line; toggling to manual stops auto-advance; toggling back resumes from the current anchor; `↻` re-anchors; plain-only track opens in manual-only with the toggle disabled/locked. Real-browser click-through (`astro check` + `pnpm lint` + `pnpm build` 0 errors; lint alone misses render regressions — BUG-11→12). Console 0.

**Rollback**: revert the component; the read API and overlay are untouched.

---

### Step 2 — Spotify-style visual redesign (front)

Rewrite the `.lyv-*` CSS in `layout.css` (lines 529-701) and the JSX class wiring in `LyricsViewer.tsx` to the target-state visual spec: album-blur background, large sans-serif focus typography, minimal chrome. No behavior change — Step 1's auto/manual engine stays.

- Add the blur background layer (`background-image: url(albumCoverUrl)` + `filter: blur(72px) saturate(1.9) brightness(0.55)` + scale + dark gradient overlay). Re-renders on track swap. Neutral dark fallback when no cover.
- Swap typography to the large sans-serif 3-level model (focus `clamp(34px,7vw,50px)`/700/white; near `clamp(24px,4.4vw,30px)`/600/70%-white; far `clamp(20px,3.6vw,26px)`/18%-white).
- Trim chrome: header keeps eyebrow + `↻` + `✕`; bottom rail keeps the auto/manual toggle; strengthen the up/down fade masks for the dark backdrop.
- Honor `prefers-reduced-motion` (no transitions/animation) and keep focus-visible outlines for keyboard nav.

**Verification**: the viewer matches the approved design preview (`/tmp/lyrics-design-preview.html`, design A) on mobile + desktop widths, light + dark site theme (the viewer is always dark — album-blur backdrop — regardless of site theme, like Spotify); background re-renders on track swap; no layout shift on long lyrics; `pnpm lint` + `astro check` + `pnpm build` 0 errors; real-browser click-through, console 0.

**Rollback**: revert the CSS + class wiring; Step 1 behavior is untouched.

---

## Open questions

1. **Estimate loop cadence (Step 1).** `requestAnimationFrame` (~60Hz, paused on tab-hidden — most efficient, but computes every frame even when the line hasn't changed) vs a ~250ms `setInterval` (fewer computations, line-grain resolution is ~3-8s so 250ms is plenty). **Leans interval** (simpler, line-grain doesn't need 60Hz, easier to pause/resume). Blocks Step 1 implementation only — pick at step-time.
2. **Prev/next buttons in the new rail (Step 1).** The redesign drops the dedicated prev/next rail in favor of the mode toggle. Manual nav remains via swipe/drag/tap/arrow-keys, but losing the explicit ↑/↓ buttons may hurt desktop discoverability. **Options**: (a) drop them entirely (cleanest, matches Spotify mobile which has no prev/next); (b) keep them but move them into a smaller secondary control. **Leans (a)** — Spotify's reference has no prev/next and swipe/keys cover it. Blocks Step 1/2 finalization — confirm at step-time.

## Decisions log

Filled in during execution.

| Date | Decision | Step |
|------|----------|------|
| 2026-07-04 | RFC opened as a follow-on to FEAT-lyrics-viewer (done) rather than amending it; explicitly repeals the prior manual-only non-goals | 0 |
| 2026-07-04 | Auto-advance mechanism = clock-based estimate from the existing one-shot `readLivePlayback()` seed (not SDK events, not polling) — keeps the RFC front-only and the non-goal repeal narrow | 0 |
| 2026-07-04 | Background = real album cover as CSS `background-image` + `filter: blur()` (CORS-free), NOT `SubjectHero`'s hash-based fake hue and NOT canvas `getImageData` extraction | 0 |
| 2026-07-04 | Visual direction = design preview "A" (Spotify full style: dark + album-blur + large sans-serif), owner-approved in session | 0 |
| 2026-07-04 | D28 "position not exposed server-side" stays honored — position reaches the viewer only via the existing client-side one-shot REST read, never via server progress field or polling | 0 |
