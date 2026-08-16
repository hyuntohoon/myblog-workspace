# FEAT-desktop-playback-bar: Spotify-shaped bottom playback deck

- **Status**: **done** (2026-08-16 — both steps shipped + prod-verified; archived)
- **Owner**: 박지훈
- **Created**: 2026-08-16
- **Plan row**: `plan.md` → FEAT-desktop-playback-bar
- **Repository**: `myblog_front` only
- **Extends, does not reopen**: `ARCH-global-playback-experience` (the global session, persistent
  reachability, and enhanced Playback Bucket queue already shipped) and the archived
  `FEAT-member-player` / `FEAT-playback-bucket-player` RFCs.

---

## Goal

Replace the current 56px player strip fixed below the site header with a purpose-built bottom playback
deck based on the information architecture of Spotify's desktop player: current-track identity and
Like on the left, primary transport plus a seekable progress rail in the center, and queue, device, and
volume controls on the right. The bar stays site-wide while a track is playing or paused, survives
Astro client-side navigation, and opens the one existing Playback Bucket expanded panel instead of
creating another player or queue.

The existing player **behavior** is reused: the Playback Bucket's dockable right panel supplies queue
and expansion behavior, while Profile → Overview's player supplies seek, shuffle, repeat, Like, device
transfer, and volume behavior. Their current visual treatments are not reused. The new bottom deck has
its own DOM, tokens, responsive rules, and control presentation.

## Non-goals

- No new playback session, queue store, or Home-specific player state. `lib/playback/session.ts` remains
  the one playback-state owner and the Playback Bucket remains the persisted queue.
- No synchronous Spotify call from a backend endpoint. All provider controls keep using the existing
  browser-side Spotify token and command layer.
- No backend route, API contract, Cognito scope, database, SQS, worker, or infrastructure change.
- No Spotify live-queue import or reverse synchronization. The queue button opens the **Playback
  Bucket queue**, not `components/member/lyrics/queue.api.ts`'s separate read-only Spotify queue.
- No pixel-for-pixel Spotify clone, Spotify green, Spotify branding, or reuse of Spotify assets. The
  reference is its three-zone desktop control grammar and priority hierarchy.
- No reuse of the current persistent bar's frosted top strip, serif/italic identity, or `pbp-*` player
  styling as the new bar design. Profile `NowPlaying` and `PlaybackPanel` are behavior sources, not
  presentation templates.
- No redesign of the whole Pocket Buckit tray. It only gains a shared bottom inset so it stacks above
  the player instead of covering it.
- No player inside `/write`; `write-layout.astro` intentionally has no `PocketBuckit` mount today and
  remains unchanged.

## Reference and design direction

### What is taken from Spotify desktop

- A persistent bottom edge, separate from page content and stable across routes.
- Three functional zones: identity/library action; playback/progress; context/output controls.
- Primary transport centered independently of title length or right-side control count.
- Queue and device controls as direct, labelled icon buttons; the device list opens above the bar.
- Progressive reduction at narrower widths instead of squeezing every control until labels or seek
  targets become unusable.

This RFC does not depend on the exact pixel layout of one Spotify release. These are durable
interaction roles already supported by this product's session.

### Visual system — new, player-only

The first obvious direction was Spotify's near-black surface plus bright green. It was rejected as a
generic imitation: the reference should explain the control hierarchy, not supply the brand. The
revised direction is a compact **listening deck** with a cool signal color and one continuous playback
rail.

| Token | Value | Role |
|---|---:|---|
| `deck-night` | `#12151B` | fixed bottom surface in both site themes |
| `deck-raised` | `#1B2028` | hover, popover, and active-panel surface |
| `deck-ink` | `#F4F7FB` | primary text and transport |
| `deck-muted` | `#9DA8B6` | artist, elapsed time, inactive icons |
| `deck-signal` | `#74B9FF` | progress, active repeat/shuffle, focus accent |
| `deck-alert` | `#FF8A80` | provider or transfer failure only |

Typography deliberately leaves the current player's editorial serif behind:

- Track, artist, and control labels: `ui-sans-serif, system-ui, "Noto Sans KR", sans-serif`.
- Time and device metadata: `ui-monospace, "IBM Plex Mono", monospace` with tabular numerals.
- No additional font download is introduced for a fixed utility surface.

Layout and shape:

- Desktop height: `88px`; square `56px` artwork; 8px spacing rhythm; 32px standard icon target and
  40px primary play target, each wrapped by a minimum 44px interactive hit area.
- Flat edge-to-edge surface, a single top border, no glass blur, card radius, editorial rule set, or
  decorative shadow stack from the current player.
- One signature element: a thin **signal rail** along the full top edge. It reports progress at every
  width and becomes the seek surface on desktop/tablet. The conventional center progress row still
  carries elapsed/total labels; both are one control, not two competing progress states.
- Motion is limited to rail/knob response and panel opening. `prefers-reduced-motion` removes the
  transitions; progress still updates without animation.

### Desktop wireframe

```text
┌─ full-width seekable signal rail ───────────────────────────────────────────────┐
│ [56 art] Title                 [shuffle] [prev] [ PLAY ] [next] [repeat]        │
│          Artist      [heart]    1:42 ───────────────●──────────── 4:08   [queue]│
│                                                              [device] [volume] │
└─────────────────────────────────────────────────────────────────────────────────┘
   identity zone (~1fr)              transport zone (~2fr)        utility zone (~1fr)
```

At `>= 1180px`, all three zones render. From `768px` to `1179px`, title/artist width shrinks first,
volume becomes an icon-triggered popover, and nonessential visible labels collapse to tooltips; Like,
repeat, queue, and device remain reachable. Under `768px`, the owner chose to keep **every desktop
control in the bottom bar**. The mobile deck therefore becomes a two-row `112px` control surface plus
safe-area inset instead of squeezing everything into one line: compact artwork/identity + Like on the
first row, and shuffle/previous/play/next/repeat + queue/device/volume icon triggers on the second. The
signal rail remains full-width along the top edge. Every hit target stays at least 44px; title width and
visible utility labels yield before the controls do.

## Current state — verified against `myblog_front` `origin/main` `2becbb9`

### The persistent bar is top-fixed and intentionally minimal

`src/components/member/playback/PlaybackPersistentBar.tsx`:

- is mounted from `PocketBuckit.tsx` inside the site-wide, `transition:persist` React root;
- is visible when `session.currentItemId != null || session.external != null`, including paused and
  playback outside the Buckit queue;
- renders only `PlaybackIdentity` plus previous/play/next `PlaybackTransport`;
- opens the Playback Bucket mini drawer through `usePocket().openDrawer` when its identity is clicked;
- sets `--pb-bar-h` to `56px` while visible.

`src/components/member/pocket/pocket.css` fixes the bar at `top: 52px`, directly below the header, and
`.site-shell` reserves it with `padding-top: var(--pb-bar-h)`. This is the exact placement the RFC
replaces.

### The bottom edge is already owned by Pocket

The two Pocket tray families both use `position: fixed; bottom: 0` (`.tray` and `.ltray`). Their entry
buttons, tree strip, undo ribbon, drawer geometry, and the design-settings button also use hard-coded
bottom offsets. Moving the player to `bottom: 0` without a shared inset would cover Pocket or be
covered by it.

The target therefore makes the player the bottom-most application surface and exposes one layout
contract (for example `--global-player-h`). Every Pocket bottom anchor is calculated above that
contract. The page changes from top reservation to `padding-bottom`, including the footer and mobile
safe area. Scattered one-off `+ 88px` corrections are not accepted.

### The expanded right component already owns the queue behavior

`src/components/member/playback/PlaybackPanel.tsx` already provides:

- a `380px` right dock plus detachable `420×760` floating form via `useDockTear`;
- a full-screen mobile form;
- current identity, progress, previous/play/next, notices, and tab-ownership takeover;
- queue artwork, count/total duration, play-all, per-row play/remove, and pointer + keyboard reorder.

`PocketTray.tsx` owns `playbackPanelOpen` locally, so the current persistent bar cannot open this panel
directly. A new queue button must not mount a second `PlaybackPanel`; panel-open ownership moves to the
persisted Pocket root (or a dedicated child host in that same root), and the tray's current “확장” action
and the bottom bar dispatch to that one owner.

When docked, the panel currently occupies the full viewport height. After relocation it ends at the
top edge of the bottom deck, so the panel and player read as one system and neither covers the other.
The existing dock/floating physics remain unchanged.

### Profile → Overview already has the requested provider controls

The first default Overview widget renders `NowPlaying`. Its private, inline-styled controls implement:

- a seekable progress track with click and keyboard ±5-second seek;
- shuffle and three-state repeat (`off → context → track → off`);
- previous/play/next;
- Like/save, including the missing-library-scope re-consent path;
- a device picker fetched only when opened, including “이 브라우저” creation/transfer;
- volume with the existing fixed-output-device failure distinction.

These controls are file-private inside a ~1,700-line component. Importing `NowPlaying` into the global
bar would also import the rejected current design and a second live-snapshot presentation. The shared
piece must be a small control layer driven by `PlaybackSessionState`, not the Overview widget.

### Session and queue ownership are already ready

`src/lib/playback/session.ts` already owns `devices`, `activeDeviceId`, `shuffle`, `repeat`,
`volumePercent`, `liked`, capability tier, reconnect state, queue identity, transport, and the tab
lease. It exports the required `toggleLiked`, `setMode`, `refreshDevices`, and `transferTo` actions.
`lib/playback/queue.ts` projects the one Playback Bucket from `bucketStore`; no second queue is needed.

Two small frontend gaps remain:

1. Seek is still implemented locally in `NowPlaying.useNowPlaying()`, not as a session action. It must
   move to `playbackSession.seekTo()` so Overview and the global bar do not create two competing seek
   implementations. The optimistic anchor update and confirmation read semantics move with it.
2. `readLivePlayback()` already returns `albumCoverUrl`, but the `ExternalNowPlaying` projection drops
   it. The new artwork-first bar needs a nullable client-only `albumCoverUrl` in the session and
   cross-tab broadcast shape. No backend or API change is required.

## Target architecture

```text
layout.astro
  └─ PocketBuckit (one persisted React root)
       └─ PlaybackSurfaceHost                    ← owns expanded-panel open state
            ├─ GlobalPlaybackBar                 ← new bottom presentation
            ├─ PocketTray
            │    └─ PlaybackMini “확장” ────────┐
            └─ PlaybackPanel (exactly one) ◀─────┴─ bar queue button

playbackSession ── state/actions ──▶ PlaybackControls (headless/small UI primitives)
       ▲                                ├─ GlobalPlaybackBar (new presentation)
       └────────────────────────────────└─ NowPlaying (keeps its Overview presentation)
```

- `PlaybackSurfaceHost` (the exact name may change in implementation) owns the one expanded-panel
  boolean and open/close callbacks. `PocketTray` no longer owns or mounts its own panel instance.
- New shared control primitives live under `components/member/playback/` and accept session state plus
  explicit callbacks. They contain behavior, labels, busy/error states, and accessible semantics, but
  no Profile card layout. The bottom bar supplies its own classes; `NowPlaying` supplies its existing
  layout until a separate redesign asks otherwise.
- `playbackSession.seekTo(ms)` becomes authoritative for seek. It updates the shared anchor
  optimistically, preserves the current busy/write-race rules, and performs the same one-shot
  confirmation while playing that `NowPlaying` does today.
- `ExternalNowPlaying.albumCoverUrl` is broadcast across tabs. `PlaybackIdentity` reads row artwork
  first and the external cover second.
- The bar is still shown only for active or paused playback, preserving current behavior. An empty
  permanent deck is not introduced.
- `--global-player-h` is `0px` while hidden, `88px` on desktop/tablet, and `112px` on mobile, plus
  `env(safe-area-inset-bottom)` while visible. `.site-shell`, Pocket trays, tree/undo/settings controls,
  and the docked panel all consume it.
- Opening queue sets an active state on the queue button, opens the existing right panel directly on
  desktop, and opens the existing full-screen panel on mobile. It does not force the Pocket tray open.

## Control behavior

| Control | State/action source | Required behavior |
|---|---|---|
| Identity/artwork | `usePlaybackViewModel`, external cover extension | queue and external tracks render the same; long names ellipsize without moving center transport |
| Like | `state.liked`, `session.toggleLiked()` | optimistic toggle; scope-missing opens Integration re-consent; unavailable state is not a dead clickable heart |
| Shuffle | `state.shuffle`, `session.setMode()` | `aria-pressed`; null means the device/capability does not expose it |
| Repeat | `state.repeat`, `session.setMode()` | off/context/track cycle; repeat-one has a distinct glyph and spoken label |
| Previous/play/next | existing session transport | respects tab ownership, busy state, external playback, and takeover banner semantics |
| Seek/progress | new `session.seekTo()` + shared anchor | pointer and keyboard seek on desktop/tablet; full-width progress rail remains visible on mobile |
| Queue | `PlaybackSurfaceHost` | toggles exactly one existing expanded panel; `aria-expanded`/`aria-controls` |
| Device | `refreshDevices` / `transferTo` | fetch on open only; active device, empty, Premium/scope, transient, and busy-transfer states |
| Volume | `state.volumePercent`, `session.setMode()` | debounced/coalesced UI writes if needed; fixed-output-device failure does not degrade all transport capability |

## Data, API, and repository impact

Frontend-only. The external-cover addition widens an in-memory TypeScript interface and its
`BroadcastChannel` payload using a value already returned by the existing live read. It does not change
OpenAPI, backend serialization, Spotify scopes, infrastructure, or the DB.

Only `myblog_front` is implemented. The RFC and plan pointer live in the workspace repository.

## Step and PR boundaries

Each step is independently mergeable. Do not start either step until the owner accepts this RFC and
resolves the approval questions below.

### Step 1 — shared playback controls and session gaps, no visual change

- Add `playbackSession.seekTo()` by moving the proven seek behavior out of `NowPlaying`.
- Extend `ExternalNowPlaying` and the cross-tab broadcast with nullable `albumCoverUrl`.
- Extract small reusable control behavior/primitives for Like, shuffle/repeat/volume, device selection,
  and seek. Keep accessible labels, capability hiding, scope re-consent, and error copy with the shared
  layer.
- Rewire Profile → Overview `NowPlaying` to use the shared behavior while preserving its current DOM
  appearance for this refactor step.
- Update `docs/frontend/component-map.md` so the state-owner and player-surface registry reflects the
  current post-`ARCH-global-playback-experience` architecture rather than its stale 2026-08-06 text.

**Verification**:

```bash
pnpm test
pnpm lint
pnpm exec astro check
```

Targeted tests prove seek optimistic/confirmation behavior, repeat cycling, Like scope states, device
fetch/transfer states, external artwork broadcast, and that Overview still renders the same variants
without an additional live read.

**Rollback**: revert the frontend PR. No persisted data or contract changed.

---

### Step 2 — replace the top strip with the bottom deck and one panel host

> ✅ Done 2026-08-16, SHA: `58aca1d` (front #415).

- Replace `PlaybackPersistentBar`'s presentation with `GlobalPlaybackBar`; delete the old top-fixed DOM
  and bar styles rather than layering the new design on them.
- Lift expanded-panel ownership out of `PocketTray` into the persisted playback surface host. Wire both
  the Playback Mini “확장” action and the bottom queue button to the one `PlaybackPanel`.
- Apply the new three-zone desktop design, responsive compact design, full-width signal rail, popovers,
  focus states, and reduced-motion behavior.
- Move page reservation from top padding to bottom padding. Make Pocket tray/tree/undo/settings and the
  docked panel consume the shared bottom inset. Include `env(safe-area-inset-bottom)`.
- Reskin the expanded panel's outer player chrome so it joins the new bottom deck; retain its queue row
  data/actions, reorder behavior, and `useDockTear` mechanics.
- Delete superseded bar CSS and tests; do not leave two design systems selected by hidden flags.

**Verification**:

```bash
pnpm test
pnpm lint
pnpm exec astro check
```

Real-browser verification is mandatory at `1440×900`, `1024×768`, and `390×844`:

1. Start a queue track; the bottom bar appears, the page/footer reserve its height, and the old top gap
   is gone on Home, search, album/artist surfaces, and Profile.
2. Pause, navigate through `ClientRouter`, and resume; identity, progress, Like, repeat, device, and
   queue state survive without audio interruption or a second player instance.
3. Verify queue-matched and external playback, including external artwork.
4. Toggle Like, shuffle, repeat-off/context/track, seek by pointer and keyboard, change device, and
   change volume against a realistic delayed Spotify stub and—when credentials are available—a live
   Premium device.
5. Open queue from the bottom bar, close it, then open it from Playback Mini. Exactly one right panel
   exists; dock, detach, reorder, play-all, remove, and current-row state still work.
6. Open Pocket while the player is visible. Pocket, its tree strip, undo ribbon, entry/settings controls,
   and mobile safe area stack above the deck with no overlap.
7. Verify capability fallback, missing Like scope, no devices, transfer failure, fixed-output volume,
   another-tab ownership, and reduced-motion states expose an explanation or correct unavailable state,
   never a silent dead control.
8. On mobile, queue opens the existing full-screen player, background/player inert behavior remains
   correct, and closing returns focus to the queue button.

Production verification after merge: the general frontend smoke suite plus an authenticated real-browser
spot check on Home confirming bottom placement, queue-panel single ownership, repeat, Like, and device
selection. Quote the result in the PR comment before dropping the plan row.

**Rollback**: revert the frontend PR. The old bar files/styles were replaced in one PR, so the revert
restores their placement and Pocket offsets together.

## Risks and failure modes

- **Bottom-edge collision with Pocket is the primary layout risk.** Mitigation: one consumed inset token,
  browser checks with every Pocket shell family, and no individual magic offsets.
- **Two expanded panels or split open state.** Mitigation: lift ownership before adding the bar button;
  tests query that only one panel region exists regardless of entry path.
- **Seek race regression.** The Overview implementation already protects optimistic writes from a stale
  confirmation read. Step 1 moves that behavior with tests before the second consumer exists.
- **Provider calls flooding on volume drag.** Keep the existing serialized write guard and add a measured
  coalescing/debounce only if pointer tests show excess requests; the final value must always be sent.
- **Controls visible but unusable for fallback/non-Premium/device-specific states.** Shared capability
  decisions are extracted with the control; the bar must not infer availability independently.
- **External playback looks second-class.** Carry the already-fetched cover into session state and test
  queue/external identity parity.
- **Dense mobile chrome.** The owner explicitly chose full control parity in the bottom bar. Mitigation:
  use the documented two-row `112px` mobile deck, collapse labels into accessible icon triggers, and do
  not shrink hit targets below 44px or rely on horizontal scrolling.
- **Current-design leakage through shared components.** Shared units expose behavior/semantics. New bar
  classes own all visuals, and the old persistent-bar selectors are removed in Step 2.

## Rejected alternatives

- **Move the current 56px bar from `top` to `bottom` and append icons.** Rejected: it preserves the
  explicitly rejected design, has no room for progress/device/queue, and collides with Pocket.
- **Render Profile's `NowPlaying` component inside the global bar.** Rejected: it couples a site-wide
  persisted surface to a large dashboard widget, duplicates snapshot concerns, and imports the old
  inline visual design.
- **Mount a second `PlaybackPanel` from the bar.** Rejected: two queue panels can diverge in open/focus/
  dock state even though they read one session.
- **Use Spotify's live queue for the queue button.** Rejected: this product's ordered Playback Bucket is
  already the authoritative queue and deliberately does not reverse-sync Spotify's provider queue.
- **Keep the bar top-fixed on mobile.** Rejected: it would make placement change by breakpoint and break
  the single persistent bottom-deck mental model.
- **Move shuffle/repeat/device/volume into the mobile expanded player.** Rejected by owner decision
  2026-08-16: mobile keeps the full desktop control set in a two-row bottom deck.
- **Black + Spotify green visual clone.** Rejected: the interaction hierarchy is useful; borrowed brand
  expression is not.

## Resolved owner decisions

1. **Expanded surface scope — option A, resolved 2026-08-16.** The bottom queue button opens the
   existing right/full-screen `PlaybackPanel` directly. Only its outer player chrome is reskinned;
   queue-row mechanics remain intact.
2. **Idle visibility — option A, resolved 2026-08-16.** Preserve today's rule: show the deck for playing
   or paused playback and hide it when there is no live/current track.
3. **Mobile density — option B, resolved 2026-08-16.** Keep every desktop control in the mobile bottom
   bar. Use a two-row `112px` deck plus safe-area inset so 44px targets survive; do not push
   shuffle/repeat/device/volume exclusively into the expanded player.

## Approval and status rule

The owner resolved all three design questions as A/A/B and explicitly approved Status promotion on
2026-08-16. The RFC is accepted; Step 1 is the immediate next task.

## Decisions log

| Date | Decision | Step |
|---|---|---|
| 2026-08-16 | Initial draft from owner direction: bottom persistent deck, Spotify desktop control grammar, behavior reused from Playback Bucket expansion + Profile Overview player, current visual design rejected. | RFC |
| 2026-08-16 | Owner selected A/A/B: reskin only the expanded panel's outer chrome; show the deck only while playing/paused; keep the full desktop control set in a two-row mobile bottom deck. | RFC |
| 2026-08-16 | Owner explicitly approved promotion to `accepted` and requested `$wrap` to start Step 1 in a fresh task. | RFC |
| 2026-08-16 | **Step 2 shipped** (front #415, squash `58aca1d`). Implementation delegated to Codex, reviewed line-by-line and independently verified by Claude: `pnpm lint`/`pnpm test` (695/695)/`astro check` (0 errors/0 warnings) all re-run and green against the actual diff before commit. Real-browser CDP against a local dev build proxied to real prod data (genuine Cognito JWT for the smoke account via a CORS+auth-rewrite proxy, `PUBLIC_BACKEND_API_URL=http://127.0.0.1:8000`) with a stubbed Spotify `/v1/me/player` response (no live Premium device available in this environment) verified all three required breakpoints: 1440×900 full three-zone layout with signal-rail + center-progress driving one seek handler and `--global-player-h`/`.site-shell padding-bottom` confirmed 88px via computed style; 1024×768 compact-utilities collapse (volume → icon popover, device label → icon); 390×844 two-row 112px mobile deck with every desktop control still reachable and the queue button opening the existing full-screen mobile panel. Single-panel ownership confirmed directly (`document.querySelectorAll('.pbp-panel')` = 1) after lifting `playbackPanelOpen` out of `PocketTray` into `PocketBuckit`. No Pocket-bar collision at any breakpoint (checked via computed `bottom` on `.pkt-ctrl`/tray). Deployed via front CI (build+upload+CloudFront-invalidate + CI's own post-deploy health check all green for `58aca1d`); post-deploy `scripts/smoke.sh prod` 19/19 green, quoted on the PR. Verifying the literal deployed CloudFront bundle via CDP remains blocked by the browser's mixed-content policy for a token relay (unsolved gap, noted 2026-08-10) — fell back to the documented equivalent (pre-merge same-source-tree CDP pass + CI build success + post-deploy API smoke) rather than attempting a workaround that would put a raw token in the transcript. Both of this RFC's steps are now shipped; RFC archived | 2 |
