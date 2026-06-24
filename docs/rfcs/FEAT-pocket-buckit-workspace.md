# FEAT-pocket-buckit-workspace: Pocket Buckit — multi-drawer workspace, edit mode, efficient reads

- **Status**: draft (needs owner accept before Active; Step A scoped + ready to build front-only)
- **Owner**: TBD
- **Created**: 2026-06-24
- **Plan row**: `plan.md` → FEAT-pocket-buckit-workspace
- **Related**: `docs/rfcs/FEAT-pocket-buckit.md` (the membership-generalization track — **complete**; this RFC is a distinct *interaction-shell + read-efficiency* follow-on, not more item-kinds), `docs/rfcs/FEAT-bucket-identity.md`

> A follow-on to the shipped Pocket Buckit. It does **not** add item kinds or change membership. It makes
> the tray a real **multi-bucket workspace** (several movable mini-drawers open at once), adds an explicit
> **edit/arrange mode** (removal + reorder gated, separate from drawer-open), and stops the tray + profile
> from **re-fetching the full bucket tree on every navigation** — backed by a new **lightweight tray
> read-model** so the tray never pays for full item/album/snapshot payloads it does not render.

---

## Why (motivating audit — all verified against code 2026-06-24)

A 5-area read of the current implementation found the prompt that motivated this RFC was written against an
earlier build; much already ships. The genuine gaps:

- **Tray drawer is single.** `PocketBuckitProvider` holds one `inspectId: string | null` + one `drawerPos`;
  `PocketTray.InspectSurface` renders exactly one movable, viewport-clamped, accent-bordered, `pbRise`-
  animated drawer. Opening bucket B replaces bucket A's drawer. (`PocketTray.tsx:264-398`,
  `PocketBuckitProvider.tsx:82-103`.)
- **No edit mode.** Drawer item-remove `−` buttons are **always** shown (`PocketTray.tsx:383`); tray
  drag-reorder is always live (gated only on `design.order==='pinned'` + unfiltered, `PocketTray.tsx:430`),
  so a normal drag-to-open can accidentally reorder. The chip-level `.lminus` remove badge exists in CSS
  (`pocket.css:240`) but is never rendered — a ready seed.
- **Heavy read on every nav.** `GET /api/buckets` returns the **entire nested tree** with every item fully
  embedded (`AlbumBrief`: cover_url/release_date/popularity/artist_names[]/genres[] per album, plus
  note/status/research fields, recursive `children[]`). The site is an **MPA** (no `ClientRouter`/view-
  transitions), so the layout-mounted provider **remounts and refetches this whole payload on every page
  navigation** (`PocketBuckitProvider.tsx:120-122`). There is **no** summary/projection endpoint and **no**
  single-bucket `GET /{id}`.
- **Three independent copies of bucket data.** The Pocket provider, `/profile` `BucketBoard`, and
  `StatsTab→LikedBoard` each call `listBuckets()` into their own `useState`; a mutation in one is invisible
  to the others until remount (separate React roots — no shared store/event). No query/cache library exists
  anywhere in `myblog_front` (manual `apiFetch` + `useState/useEffect`, localStorage-seeded SWR).
- **No user-scoped cache / logout clear.** localStorage seeds (`lf_crate_*`, `pb:drawer`, `pb:design`) are
  global per-browser; a logout/user-switch repaints the previous user's tree.

What already ships (do **not** rebuild): the whole layer scales by one `--pb-scale` knob (desktop **1.25**;
owner chose to **keep 1.25**, so no scale change here); the drawer is already movable/clamped/persisted;
hover is already non-translating (scale+shadow, no overlap — `pocket.css:128-130,207-210`); drag-reorder
already **persists** via `PUT /api/buckets/{id}/move` (the `position` column); per-bucket accent already
flows `bucket.color → --chip-accent / --bucket-accent` with `color-mix` tints; profile **tabs already
keep-alive** (mount-once, hide with `display:none`, no refetch on tab switch — `ProfileApp.tsx:255-267`).

## Goal

Several bucket drawers open at once (each movable / focusable / closable, brought-to-front on re-click,
never duplicated); an explicit edit/arrange mode that gates removal + reorder and is **independent** of
drawer-open; and tray + profile data that is fetched once, cached per-user, reused across surfaces and
navigations, and revalidated deliberately — backed by a lightweight tray read-model so the tray never loads
full item payloads.

## Non-goals

- No change to `--pb-scale` / overall size (owner keeps **1.25**).
- No new item kinds, no membership change, no schema migration (every column the read-model needs already
  exists; `item_count` is a `COUNT`).
- No query/cache library dependency — extend the existing hand-rolled SWR pattern (sessionStorage + a
  module-level observable store), matching repo conventions.
- The `/profile` `BucketBoard` is **not** redesigned; it only joins the shared bucket store (Step B) and
  gains a lazy-detail path (Step C).

---

## Steps

Built in three gated steps. **A and B are `myblog_front`-only and additive (no contract/infra)** — they may
merge as two front PRs without a cross-repo prod-observe gate between them. **C is the cross-repo contract
step** and takes the full prod-observe gate (rule #4) + post-merge prod-verify + the standard contract
rollout.

### Step A — multi-drawer workspace + edit/arrange mode (front-only)

State model (in `PocketBuckitProvider`, all **separately** held — RFC §9 of the request):

```
openDrawers: { bucketId, pos: DrawerPos|null, z: number }[]   // several at once
topZ: number                                                   // monotonically bumped on focus
editMode: boolean                                              // global; NEVER derived from openDrawers
```

- `openDrawer(id)`: if already open → **focus** (bump `z = ++topZ`); else push a new drawer with a
  **cascade** spawn position (default placement offset by `openCount * 26px`, clamped) and `z = ++topZ`. No
  duplicate drawer for the same bucket, ever.
- `focusDrawer(id)` / `closeDrawer(id)` / `moveDrawer(id,pos)` are per-bucket; closing/opening one never
  touches the others.
- **Position persistence**: a per-bucket map `localStorage['pb:drawers'] = Record<bucketId, DrawerPos>`
  (replaces the single `pb:drawer`). On open: seed from the persisted pos **re-clamped to the live
  viewport** (a stale off-screen coord is corrected) else the cascade default. On drag-end: persist. Off-
  screen positions are never restored (existing `clampDrawer`, `DRAWER_MARGIN=8`).
- **Z / focus**: render each drawer at `z-index: base + z`; pointerdown anywhere on a drawer focuses it.
- **Open animation**: a new `@keyframes pbDrawerIn` (opacity 0→1, scale .965→1, translateY 6px→0, ~.16s
  ease-out) — connected-to-tray, no bounce/long/modal feel; disabled under `prefers-reduced-motion`.
- **Active state (RFC §3)**: every chip whose bucket has an open drawer shows `data-active` (the existing
  accent ring); multiple simultaneously is correct. Each drawer keeps its `--bucket-accent` strip/outline.

Edit mode (the only thing that reveals removal/reorder — **never** drawer-open):

- A small **편집 / 완료** toggle in the tray chrome. `editMode` adds `data-edit="true"` on `.pb-scope`.
- **Normal mode**: click opens/focuses a drawer; **drag does not reorder** (so opening is never disturbed —
  the rail still scrolls); no `×` badges; drawer item-rows hide their `−` buttons.
- **Edit mode**: chips become reorderable (drag → existing `reorderBucket` → `PUT /{id}/move`, already
  persisted); each chip shows a `.lminus`-style `×` → **delete bucket** behind an inline 2-tap confirm
  (destructive: `deleteBucket` cascades, no server undo); drawer item-rows show their `−` remove buttons; a
  subtle edit affordance (outline / faint idle motion) in the current design language (not an iOS clone).
- Reorder is gated on `editMode` (AND still the existing `order==='pinned'` + unfiltered constraint so the
  drop-index maps to visible roots).

Files: `PocketBuckitProvider.tsx`, `PocketTray.tsx`, `pocket.css` (+ `buckets.ts` already exports
`deleteBucket`). No backend, no contract.

### Step B — shared, cached, user-scoped bucket store (front-only)

- **One source of truth**: a module-level observable `bucketStore` (sessionStorage-backed, **user-scoped**
  by Cognito `sub`) that the Pocket provider **and** `BucketBoard` **and** `LikedBoard` subscribe to.
  Islands are separate React roots, so the store is a plain pub/sub module (not React context); a `storage`
  event syncs across tabs, an in-page emitter syncs across islands. A mutation in any surface patches the
  store → all surfaces update without a refetch.
- **SWR, not refetch-on-mount**: seed instantly from the user-scoped session cache; revalidate in the
  background only when **stale** (a `staleTime`, e.g. 30s) or after a mutation. Navigating between pages
  reuses the cache → no full-tree refetch per nav.
- **User-scoped keys + logout clear**: cache keys carry the `sub`; a logout/user-switch clears them (and
  the legacy `lf_crate_*` / `pb:*` seeds) so the previous user's data is never repainted.
- **De-dup**: `recently-listened` is fetched by both `BucketBoard` and `OverviewDash` → one shared fetch.
- Profile tabs already keep-alive; Step B extends the same "fetch-once, reuse-while-valid" to the
  **cross-navigation** and **cross-surface** axes the keep-alive does not cover.

Files: new `src/lib/pocketBuckit/bucketStore.ts` (+ a small `userScope` helper), `PocketBuckitProvider.tsx`,
`BucketBoard.tsx`, `LikedBoard.tsx`, `OverviewDash.tsx`. No backend, no contract.

### Step C — lightweight tray read-model + lazy drawer detail (cross-repo, contract)

Backend (`myblog_backend`) — **additive, no migration** (all columns exist; `item_count` is a `COUNT`):

- `GET /api/buckets/summary` → flat `BucketSummary[]`:
  `{ id, name, color, kind, position, parent_id, item_count, research_mode, is_public, is_done, updated_at }`.
  No items, no album metadata, no children nesting, no snapshots. The tray rebuilds its leaf list +
  depth/path from `parent_id` + `position` client-side. (`BucketResponse` deliberately omits `parent_id`;
  the summary includes it.)
- `GET /api/buckets/{id}` → one bucket's **detail** (`BucketResponse` with `items[]`, no `children`) for
  lazy drawer load. New route (none exists today); declared after the literal `/public`,
  `/spotify-library/*`, `/reorder` paths and distinct from `/{id}/move` (PUT) + `/{id}/items` — no
  ambiguity. Cognito-gated like the rest; **GETs ride the `api_get_proxy` catch-all → no `apigateway.tf`
  change** (the Lambda's `require_cognito_token` enforces the Bearer).
- Service computes `item_count` with a grouped `COUNT(review_bucket_items)` — never materializes items for
  the summary path.

Front (`myblog_front`):

- Provider derives leaves from the **summary** (Step B's store caches summaries); opening a drawer
  **lazy-loads** `GET /{id}` detail (cached per bucket in the store; revalidate on stale or after a
  mutation to that bucket). Drawer renders from cached detail on reopen.
- `api.gen.ts` regenerated off the merged contract (front deploy gate — memory
  `feedback-frontend-api-gen-sync`).

Contract rollout (standard, additive): backend PR ships its own `openapi.json` → workspace merge regenerates
`docs/contracts/openapi.json` (byte-identical to `tools/merge_openapi.py`) → front `pnpm generate:types` +
consume. Old `GET /api/buckets` stays (backward-compatible; the front summary path falls back to it if
`/summary` errors).

Files: `myblog_backend/app/api/routes/buckets.py`, `app/api/schemas.py`, `app/services/bucket_service.py`,
`tests/api/test_buckets.py`, regenerated `openapi.json`; `docs/contracts/openapi.json`;
`myblog_front` provider + `api.gen.ts`.

---

## Verification (Definition of Done per step)

- **Step A** — `pnpm lint` + `pnpm exec astro check` clean; **real-browser CDP click-through** (open 2+
  drawers; move each; re-click an open bucket → it comes to front, no duplicate; close one → others stay;
  toggle edit mode → `×`/`−`/reorder appear, normal-mode drag does not reorder and does not open on drag;
  delete via 2-tap confirm; reorder persists across reload; reduced-motion path). Post-merge prod smoke:
  deployed `PocketTray`/`PocketBuckitProvider` chunk ships the multi-drawer + edit-mode strings.
- **Step B** — lint + astro check; CDP: navigate page→page→back with the tray open → **no** `GET
  /api/buckets` on the cached navigations (network panel); mutate in the tray → `/profile` board reflects
  it without a refetch; logout → cache cleared. 
- **Step C** — backend `pytest` + `pyright`; `openapi.json` regen committed + workspace byte-identical
  merge; front `api.gen.ts` regen + lint. Post-merge prod smoke: `GET /api/buckets/summary` 200 (flat, no
  `items`), `GET /api/buckets/{id}` 200 (items, no children), tray network shows summary (small) on load +
  one detail GET per drawer-open; payload-size drop quoted.

## Rollback

- A / B are front-only → revert the front PR. B's store falls back to direct `listBuckets()` if the cache is
  disabled/corrupt.
- C is additive: the new endpoints can be left in place; the front **falls back to the full `GET
  /api/buckets`** if `/summary` or `/{id}` errors, so a front revert is independent of the backend.

## Open questions

- **OQ1 — edit-mode bucket delete.** Should edit mode allow **deleting a bucket** from the tray (the iOS-
  jiggle analogy + the dormant `.lminus`), or only reveal drawer item-removal + reorder? Proposed: yes,
  with an inline 2-tap confirm (no `window.confirm`), since `deleteBucket` already exists and the request's
  step 5 says "removal controls become visible." Destructive + no server undo → confirm is mandatory.
- **OQ2 — store ownership (Step B).** Make `PocketBuckitProvider` the canonical store, or a standalone
  `bucketStore` module both the provider and `BucketBoard` consume? Proposed: standalone module (the two
  live in **separate islands / React roots**, so a shared module-level store + events is the only way to
  unify them without a router).
- **OQ3 — summary vs reuse `/public` shape (Step C).** Define a fresh `BucketSummary` (count-only, includes
  `parent_id`) rather than reuse the flat album-only `/public` projection — the tray needs counts + tree
  parentage, not album rows. Proposed: fresh schema.
- **OQ4 — `position` is per-parent-sibling order**, not a global flat order (verified). For roots
  (`parent_id IS NULL`) it is already the correct tray order; the summary returns it as-is and the client
  groups by `parent_id`. No new ordering concept needed.
