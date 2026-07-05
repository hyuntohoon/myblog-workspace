# FEAT-mobile-web-app: Mobile-first read path + PWA

- **Status**: accepted
- **Owner**: TBD
- **Created**: 2026-07-05
- **Plan row**: `plan.md` → FEAT-mobile-web-app

---

## Goal

The public read path (home, `/reviews`, `/review/[slug]`, `/genres`, `/canon`, `/collection`, `/artist/[id]`, `/search`) is comfortable on a 390px phone: chrome (header + nav) takes a fraction of the first viewport instead of ~60%, no clipped text, navigation follows a mobile pattern chosen from real mockups, page transitions feel app-like, and the site is installable to the home screen as a PWA (manifest + service worker + offline shell + iOS install guidance). Final scope decision 2026-07-05: **PWA is the end state — no native/store packaging** (Capacitor explicitly out).

## Non-goals

- Native app packaging (Capacitor / app stores). PWA is the ceiling of this RFC.
- Logged-in workspace touch redesign — BucketBoard drag-drop, Pocket Buckit multi-drawer free placement, `/write` editor. That is a follow-on RFC (`FEAT-mobile-workspace-touch`, not yet drafted); this RFC must not regress those surfaces but does not improve them.
- Push notifications, Background Sync, offline mutation queues. (iOS has no Background Sync at all; push requires installed-PWA on iOS 16.4+ — deferred until there is a notification product need.)
- Visual redesign of the editorial identity (fonts, dark palette, serif voice stay as-is).
- Backend/contract/infra changes beyond one possible CloudFront cache-behavior entry for `sw.js` (Step 4).

## Current state

Verified 2026-07-05 by code audit + live-prod CDP at 390×844 (iPhone-class viewport) + mobile Lighthouse.

**Solid already** (do not rebuild):
- Tailwind v4 + CSS-variable design tokens in `myblog_front/src/styles/global.css:10-111` — type scale, `--bp-*` tokens (480/640/768/1024/1280), `clamp()` display sizes, dark mode.
- 44px tap targets under `@media (pointer: coarse)`; hover-only kebab already has a `(hover: none)` fallback; bottom sheets use `env(safe-area-inset-bottom)`; body has `overflow-x: clip`.
- Mobile Lighthouse (prod, 2026-07-05): a11y 100 / best-practices 100 / SEO 92. No horizontal document scroll on home or `/genres`.

**Broken / missing**:
1. **Header chrome eats ~60% of the first mobile viewport** (`src/components/header.astro`): search bar + full-size masthead wordmark + 5 nav links wrapped into 2 rows. No hamburger, no bottom nav — the desktop nav merely shrinks at 640px (`.hdr-bar-nav { display:none }` kills the compact-bar nav on mobile, leaving only the tall masthead nav). Search input placeholder clips; a `⌘K` shortcut badge renders on touch devices.
2. **Breakpoint fragmentation**: ~25 `@media` rules across `src/styles/` using 10 ad-hoc widths (480/540/560/600/640/720/760/880/1024/1120) that ignore the `--bp-*` tokens; 30+ `white-space: nowrap` instances. Observed live: `/genres` stats line clips to "CONTAI…" at 390px; `genres.css` layouts B (Miller columns) and C (dendrogram) have no ≤480px breakpoint at all.
3. **No app-like navigation**: full MPA reloads; no View Transitions (`ClientRouter` not used in `src/layouts/layout.astro`).
4. **Zero PWA surface**: no `manifest.json`, no service worker, no `theme-color` meta, no PWA deps in `package.json`. Build is `output: 'static'` → S3 + CloudFront (directory-index rewrite lives in the console-managed CloudFront function `handler`).
5. Logged-in bottom conflict (context for Step 1 design, fixed in the follow-on RFC): Pocket Buckit tray (`.pb-tray`) is fixed to the bottom edge, which constrains any bottom-nav pattern.

## Target state

- ≤390px: first viewport shows content within ~200px of chrome; nav reachable via the pattern picked in Step 1 (mockup comparison — bottom tab bar vs hamburger drawer vs combo — decision deferred to Step 1 review, per owner 2026-07-05); no `⌘K` badge on `pointer: coarse`; search opens full-width.
- All read-path `@media` rules use the `--bp-*` token set (extend the set if a value is genuinely needed); `/genres` defaults to layout A (outliner) on mobile and renders without clipping at 390px; nowrap clip sites on the read path fixed or given scroll affordances.
- `<ClientRouter />` enabled with default cross-page fade + persisted header; unsupported browsers fall back to normal navigation.
- `@vite-pwa/astro` generates `manifest.webmanifest` + a Workbox precache service worker; `theme-color` meta present; installed app opens standalone; repeat visits work offline for the app shell + previously visited review pages; an unobtrusive iOS "공유 → 홈 화면에 추가" hint shown in Safari-on-iOS only (no `beforeinstallprompt` on iOS).

## Steps

Steps 1–2 are the mobile-UX core and land in order. Steps 3 and 4 are **additive** and independent of each other (each still lands as its own PR/session per rule #4's additive allowance).

### Step 1 — Mobile header/nav redesign (with pattern decision gate)

1a (in-branch, pre-implementation): build throwaway mockups of the two candidate patterns on the real header — (A) bottom tab bar (Reviews/Genres/BNM/Canon/Collection) with a logged-in coexistence sketch vs the Pocket tray, (B) compact header + hamburger drawer, (C) combo (tabs + overflow). Screenshot each at 390px, owner picks (Korean question). **This is the RFC's one deferred design decision — record it in the Decisions log.**
1b: implement the chosen pattern; collapse the masthead to a compact mobile header; hide `⌘K` badge under `pointer: coarse`; make search open as a full-width overlay/sheet on mobile; keep desktop ≥1024px visually unchanged.

**Verification**:
```
pnpm lint && pnpm exec astro check
# CDP at 390x844: first-viewport chrome height ≤ ~200px; nav reachable ≤ 2 taps;
# no ⌘K on touch; desktop 1440px screenshot diff ≈ unchanged.
# Real-browser click-through (DoD) incl. logged-in state: tray + new nav coexist without overlap.
```

**Rollback**: revert PR (front-only, no contract).

---

### Step 2 — Breakpoint/token consolidation + read-path clip sweep

Map the 10 ad-hoc media widths onto `--bp-*` tokens (CSS `@media` cannot read custom properties — consolidate to the token *values* and document the canonical set in `global.css`; delete near-duplicates like 540/560/600 → 640 where visually safe, checking each). Sweep `white-space: nowrap` on the read path: fix clip sites with wrap/`text-overflow: ellipsis`/`overflow-x: auto` per case — `/genres` stats line first. `/genres` on mobile: force layout A (outliner) — hide the B/C switcher below the mobile breakpoint (decided, OQ2). Audit fixed-width grids (`memo-lg-grid` pattern) on the read path.

**Verification**:
```
pnpm lint && pnpm exec astro check
# CDP 320/390/768px sweep over home, /reviews, /review/[slug], /genres (3 layouts),
# /canon, /collection, /artist/[id], /search:
# document.scrollingElement.scrollWidth === innerWidth on every page; no clipped stat lines.
```

---

### Step 3 — View Transitions (additive)

Add `<ClientRouter />` to `src/layouts/layout.astro`; `transition:persist` on the header (and tray mount point so the React island survives navigation — verify island state actually persists, else scope persist down); default fade elsewhere. Guard any `document`-level listeners in islands against `astro:page-load` re-runs.

**Verification**:
```
pnpm lint && pnpm exec astro check
# CDP: navigate home → review → artist; no full reload (network doc requests absent),
# tray/login state survives navigation, console 0. Firefox (no VT support) still navigates.
```

**Rollback**: remove the two lines; zero data surface.

---

### Step 4 — PWA (additive)

Add `@vite-pwa/astro` (`registerType: 'autoUpdate'`, Workbox `generateSW`): precache app shell + hashed assets, runtime-cache visited `/review/*` HTML only (`NetworkFirst`, small cap — decided, OQ3) and cover images (`StaleWhileRevalidate`, capped). **Never cache `/api/*`.** Add `manifest.webmanifest` (name, icons 192/512 + maskable, `display: standalone`, `theme-color` matching the dark bg) + `theme-color` meta. iOS install hint component (Safari-on-iOS UA + not-standalone only, dismiss-persistent). CloudFront: ensure `sw.js` is served with `Cache-Control: no-cache` — S3 metadata or a cache behavior in `infra/cloudfront.tf` (full `terraform plan`; **no `-target`**, rule #6); note the console-managed `handler` function must not rewrite `/sw.js`.

**Verification**:
```
pnpm lint && pnpm exec astro check && pnpm build   # sw.js + manifest in dist/
# Prod post-deploy: Lighthouse PWA installability pass; Chrome Android install;
# airplane-mode revisit serves shell + a previously visited review;
# curl -sI https://www.ratemymusic.blog/sw.js | grep -i cache-control  → no-cache;
# new deploy picked up within one SW update cycle (no stale-forever).
```

**Rollback**: unregister SW via a kill-switch deploy (`self.registration.unregister()` build) before removing the integration — plain removal leaves stale SWs controlling clients.

---

## Open questions

1. ~~**Nav pattern (blocks Step 1b)**~~ — RESOLVED 2026-07-05: **(B) compact header + hamburger drawer**, picked at the Step 1a mockup gate (390×844 injected mockups on live prod, logged-in state). Deciding factor: B leaves the bottom edge entirely to the Pocket tray (no dock/lift conflict), maximizing freedom for the workspace follow-on RFC; accepted trade-off is 2-tap nav reach.
2. ~~**`/genres` mobile strategy**~~ — RESOLVED 2026-07-05: force layout A (outliner) on mobile; B/C stay desktop-only exploratory views (owner).
3. ~~**SW cache scope for review HTML**~~ — RESOLVED 2026-07-05: shell + `/review/*` only, small cap; home stats change too often to cache (owner).
4. **Workspace follow-on trigger** — after this RFC ships, does mobile usage of the board/tray justify drafting `FEAT-mobile-workspace-touch` (tray as full-width bottom sheet, drag → sheet actions)? Revisit with real usage.

## Decisions log

| Date | Decision | Step |
|------|----------|------|
| 2026-07-05 | Web-app end state = PWA; no native packaging (owner) | scope |
| 2026-07-05 | Read path first; workspace touch redesign = follow-on RFC (owner) | scope |
| 2026-07-05 | Nav pattern decided at Step 1a mockup gate, not in this draft (owner) | 1 |
| 2026-07-05 | `/genres` mobile = force layout A; no ≤480px work on B/C (owner, OQ2) | 2 |
| 2026-07-05 | SW runtime cache = shell + `/review/*` only, small cap (owner, OQ3) | 4 |
| 2026-07-05 | Status draft → accepted (owner: "업셉") | — |
| 2026-07-05 | Step 1a gate: nav pattern = (B) compact header + hamburger drawer — bottom edge stays Pocket-tray-only (owner, OQ1; A/C rejected over tray dock conflict + 5-tab density at 390px) | 1 |
| 2026-07-05 | Step 2 canonical max-width set = 480 · 640 · 767 (below md) · **880 (`--bp-tab`, extended)** · 1024 · 1280. The 820/860/880 cluster (footer, genres layout B, reviews grids — 3 files) is a genuine tablet-landscape collapse point between md and lg → extended the token set per this RFC's "extend if genuinely needed" clause instead of forcing 768/1024. Container queries (search gsmain 720, artist artmain 760) excluded — they size against the container, not the viewport (front #235) | 2 |
| 2026-07-05 | Step 3 persist scope: all four header roots + PocketBuckit island. Swap side-effects handled client-side — drawer close + scroll-lock release (after-swap), nav active re-sync (page-load), theme/accent re-apply (after-swap; the swap adopts incoming `<html>` attributes). Page module scripts moved to astro:page-load inits (review template, albumDetail ×2, drafts) (front #236) | 3 |
| 2026-07-05 | Step 4 needs **no infra change** (RFC had allowed one cache-behavior touch): the front deploy workflow already uploads all non-`_astro` objects — incl. `sw.js`, workbox runtime, manifest — with `Cache-Control: no-cache`, and the console CloudFront `handler` passes any URI containing `.` straight through (live function body verified via `aws cloudfront get-function`). Precache = shell only (`/`, `/reviews/`, hashed assets), NOT `**/*.html` (unbounded client precache growth as reviews accumulate) (front #237) | 4 |
