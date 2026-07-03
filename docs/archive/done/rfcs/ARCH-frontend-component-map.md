# ARCH-frontend-component-map: Frontend component structure map

- **Status**: done
- **Owner**: 박지훈
- **Created**: 2026-07-02
- **Plan row**: `plan.md` → ARCH-frontend-component-map

---

## Goal

After this RFC, future feature work can identify **component ownership, reuse, and
impact before making changes**, instead of rediscovering the frontend's structure each
time. It produces two artifacts: (1) a **developer/LLM reference** that pins real file
paths, component responsibilities, state ownership, interaction ownership, and dependency
relationships; (2) a **human-readable component structure map** of major routes, feature
areas, shared components, global UI surfaces, and key data/state flows. Both are
verified against code as of 2026-07-02 and kept as living docs (drift re-checked on
change — same discipline as `reference-architecture-md-unreliable`).

This RFC is one of three dependency RFCs pulled out of **FEAT-lyrics-viewer**. It owns
**track-click ownership, shared interaction components, overlay state ownership, and
affected routes** — the four contracts the lyrics viewer needs before wiring any entry.

## Non-goals

- **No code change.** This RFC documents what exists; it does not refactor, consolidate,
  or create the (absent) shared track-click component. "Do not propose or create a common
  track-click component" is explicit.
- **No architecture.md replacement.** `architecture.md` is hand-maintained and lags code
  every release (memory `reference-architecture-md-unreliable`); this map is the
  verified, code-pinned alternative **for the frontend only**. It does not rewrite the
  backend/infra stories.
- **No design decisions on how the lyrics viewer binds entry.** That is FEAT-lyrics-viewer's
  call. This RFC states *where* track-click and overlay state live so the viewer can decide.
- **No exhaustive line-by-line audit.** The map names owners and load-bearing paths, not
  every helper.
- **Backend / worker / shared_db component maps.** Frontend (`myblog_front`) only.

## Current state

Verified against code 2026-07-02 (Astro 5 + React 19, `myblog_front/src/`). Full detail
lives in the [Developer reference](#developer-reference-llm-reference) below; this section
is the load-bearing summary.

### Routes & islands

| Route | Page | Primary island(s) | Authed? |
|---|---|---|---|
| `/` | `pages/index.astro` | `EditorialHome` (`client:load`), `PocketResume` (`client:only`) | Public |
| `/reviews` | `pages/reviews/index.astro` | `ReviewsIndex` (`client:load`) | Public |
| `/review/[slug]` | `pages/review/[slug].astro` | `AddToBucketMenu` (hero, `client:only`), `ReviewTrackAdder` (`client:only`) + **vanilla** `scripts/albumDetail.client.ts` | Public |
| `/artist/[id]` | `pages/artist/[id].astro` | `ArtistHub` (`client:only`) | Public |
| `/genres` | `pages/genres/index.astro` | `GenreMap` (`client:only`) | Public |
| `/canon`, `/collection` | `canon.astro`, `collection.astro` | `CanonPage`, `CollectionView` (`client:load`) | Public (collection = edge_guard read) |
| `/search` | `pages/search.astro` | `SearchPage` (`client:only`) | Public |
| `/profile` | `pages/profile.astro` | `ProfileApp` (`client:only`) | **Authed** (`scripts/profile.guard.ts`) |
| `/buckets` | `pages/buckets.astro` | — (meta-refresh → `/profile?tab=bucket`) | n/a |
| `/drafts` | `pages/drafts.astro` | none (vanilla table) | Authed (inline `isLoggedIn()` → `goLogin`) |
| `/write` | `pages/write.astro` | `WriterApp` (`client:load`) | **Authed** (`scripts/write.guard.ts`) |

Shared chrome (`Header`/`Footer`/`PocketBuckit`) is mounted once in `layouts/layout.astro:35-38`.
`write-layout.astro` is standalone (no Header/Footer/Pocket).

### Track-click behavior — **no shared track-row component exists**

Track interaction is fragmented across **≥6 independent code paths**. There is no common
row component. The surfaces differ in whether they **play**, **navigate**, **open detail**, or
**add to bucket** — only play is shared at the SDK layer (`requestPlayback`), never at the row layer.

| Surface | File:component | Click does | Playback path | Shared with? |
|---|---|---|---|---|
| Review tracklist (vanilla, public) | `scripts/albumDetail.client.ts:145,522` | two buttons/row: `.lfq-tt-play` (▶) + `.lfq-tt-add` (＋) | ▶ → `requestPlayback({kind:'track',trackId,title})` (`:130`); ＋ → `window` event `pb:add-track` (`:144`) → `ReviewTrackAdder` | play only |
| Pocket tray drawer members | `components/member/pocket/PocketTray.tsx:587` | React `<button onClick={onPlay}>` ▶ (list view) | `onPlay`→`playbackTargetFor` (`:53-59`)→`requestPlayback` (`:412`) | play (different wrapper) |
| Member `AlbumDetail` tracklist | `components/member/AlbumDetail.tsx:154-178` | not clickable — read-only `<li>` | none | — |
| `LikedBoard` rows | `components/member/LikedBoard.tsx:274-285` | cover/title → `onOpen` (opens `AlbumDetail`); ⋯ → 담기/평론쓰기 | none | detail/add (via `BucketPickerSheet`, not play) |
| Search track rows + header | `components/search/SearchPage.tsx:67-91`, `HeaderSearch.tsx:295-308` | `ResultRow` `action` union — track rows are `action:'static'` (not clickable) | none | — |
| Writer `RecommendedTracksBlock` / `ArtistDetail` | `components/writer/RecommendedTracksBlock.tsx:66-76`, `writer/ArtistDetail.tsx:43` | ★/☆ pick / `onPickTrack` (select-for-review) | none | selection (not play) |

`requestPlayback` (from `lib/spotifyPlayback.ts:243`) — the **only** SDK owner — is imported
in exactly **2 files**: `scripts/albumDetail.client.ts` and `components/member/pocket/PocketTray.tsx`.
Every other surface has no play affordance.

**Verdict (documented, not fixed):** play funnels through the shared `requestPlayback` SDK
layer; the **row UI** around it is re-implemented per surface (vanilla delegated-click in the
review tracklist vs React `onClick` in the tray), and navigation/detail-open/add-to-bucket are
each separate paths. A future unified `<TrackRow action={...}>` would mirror the existing
`search/atoms.tsx` `RowAction` union + call the already-shared `requestPlayback` — but that is
**out of scope here**.

### Overlay / drawer / store / context / cache ownership

- **Overlay primitives** — `.lf-scrim` / `.lf-slideover` / `.lf-modal-card`
  (`styles/member.css:193,203`), `--z-overlay: 80` (`styles/global.css`).
  `useDismissable` (`lib/useDismissable.ts:24`) = ESC + focus trap/restore.
  The centered-600px pattern (`StandardModal`) is **not** the Spotify-mobile full-bleed shape.
- **Who mounts overlays** — `AlbumDetail` (`StandardModal` + `MemoWindow`), `OverviewDash`
  (`RecentAlbumsModal`/`RecentTracksModal`), `ImportAnalysis`, `ReviewsTab` (DELETE scrim),
  `BucketBoard` (`TrashDrawer`). `AddToBucketMenu` / `BucketPickerSheet` deliberately do **not**
  use `useDismissable` (inline backdrop + manual ESC).
- **State store** — `lib/pocketBuckit/bucketStore.ts`: framework-agnostic observable singleton
  (user-scoped bucket tree, sessionStorage `pb:cache:buckets:<sub>`, SWR 5-min,
  `useSyncExternalStore` via `useBucketStore()`).
- **Cross-island events** — `lib/pocketBuckit/events.ts`: `pb:toggle`, `pb:closed`,
  `pb:open-state`, `pb:dnd-start`/`pb:dnd-end`, `pb:board-dnd-start`/`end`/`dropped`.
  `ProfileApp`'s `BucketBoard` and layout's `PocketBuckit` are **separate React roots** — no
  shared context; they communicate only via `bucketStore` + `pb:*` window CustomEvents
  (memory `reference-front-island-boundaries`).
- **React context** — exactly one provider: `PocketBuckitProvider` (`components/member/pocket/PocketBuckitProvider.tsx:124`,
  `PocketContext`/`usePocket`). `theme-provider.astro` is an inline `<script is:inline>`
  (vanilla `data-theme`), not React context.
- **Cache / data** — no React Query/SWR. `apiFetch` (`lib/api.ts:65-88`, 401→refresh→`goLogin`);
  `safeFetch` (8s timeout); `useMusicSearch` (`lib/useMusicSearch.ts`, headless search + `seqRef`
  race guard + 3s Spotify cooldown); `sessionCache` (`lib/sessionCache.ts`, two-tier GET cache);
  `lib/albumDetail.ts` (in-memory + inflight-dedup album-detail cache, used by the React modal
  — the vanilla review tracklist uses `sessionCache` directly).

### Duplicate / overlapping responsibilities (load-bearing)

1. **Two album-detail paths** — vanilla (`scripts/albumDetail.client.ts` → `#albumDetail` on
   `/review/[slug]`, own `sessionCache` cache, ▶ + ＋) vs React (`components/member/AlbumDetail.tsx`,
   mounted once by `ProfileApp.tsx:419`, own `lib/albumDetail.ts` cache, **read-only tracklist**).
   Different caches, different entry points, different interactivity. **This is the load-bearing
   duplication for track-click.**
2. **Two "add to bucket" flows** — `AddToBucketMenu` (portable, public+authed, album-or-track,
   logged-out intent handoff via `intent.ts`) vs `BucketPickerSheet` (member-only, resolves a
   target bucket id; caller runs `ops.*`/`addBucketItem`). LikedBoard uses `BucketPickerSheet`;
   the review page uses `AddToBucketMenu`.
3. **Orphaned** — `components/search-bar.astro` + `scripts/searchBarDb.client.ts` have no importer
   (superseded by `HeaderSearch`/`SearchPage`).

## Target state

Two living artifacts under `docs/` (path finalized at step-time), both code-pinned and marked
with a "verified YYYY-MM-DD" stamp (re-verified on change):

1. **Developer / LLM reference** — the [Developer reference](#developer-reference-llm-reference)
   section of this RFC transposed into a standalone doc. File paths, component responsibilities,
   state/interaction/cache ownership, dependency relationships. The artifact a future LLM reads to
   know "who owns track click" without re-grepping.
2. **Human-readable component structure map** — routes by feature area, the shared-chrome mount,
   the two-island boundary, and a compact diagram of the three data/state flows (bucket tree,
   `pb:*` events, `requestPlayback`). The artifact a human scans to see impact before a change.

Neither artifact changes code. Both are the deliverable.

## Component-map impact template (for future RFCs)

A compact fill-in future RFCs paste into their "Current state"/"Affected components" section,
so a change names its real touchpoints up front instead of "tweaks the frontend":

```
Component-map impact — <RFC-ID> <title>
Verified: YYYY-MM-DD (re-verify if frontend changed since ARCH-frontend-component-map)
Routes touched:        /path (island) — public|authed
Track-click paths hit:  review-tracklist | pocket-tray | liked-board-onOpen | search-static | writer-pick | albumdetail-readonly
Play path:              none | requestPlayback (shared SDK layer) — entry surface:
Overlay changed:        none | new overlay (reuses useDismissable + .lf-scrim | new panel shape)
State owner:            bucketStore | pocket-events | pocket-intent | profile-local | ad-hoc
Cross-island?:          no | yes (pb:* event: ____ ; shared store: ____)
Cache touched:          sessionCache | albumDetail | useMusicSearch | none
Duplicate it overlaps:  album-detail paths | add-to-bucket flows | none
```

## Developer reference (LLM reference)

> **Step-0 snapshot — superseded 2026-07-02 (Step 1).** The canonical living copy is
> **`docs/frontend/component-map.md`** (developer/LLM reference) + `docs/frontend/structure.md`
> (human-readable map). This RFC no longer carries a second copy to drift; read and update
> the standalone artifacts. Step-1 spot re-verification corrected two anchors vs the Step-0
> body (`requestPlayback` def is `spotifyPlayback.ts:242`; the slide-over primitives stack at
> `--z-panel: 90`, with `--z-overlay: 80` a separate token at `global.css:52`).

## Steps

Docs-only RFC. Hard rule #4 — one step per session.

### Step 0 — RFC + plan.md pointer (this document, docs-only)

This RFC + one-line `plan.md` Backlog pointer + `docs/rfcs/README.md` index entry. No code,
no schema. The reference content above is already code-verified; it transposes to the standalone
artifact in Step 1.

**Verification**: doc review against `TEMPLATE.md` / README required sections. `git diff --stat`
shows only doc files.

---

### Step 1 — publish the two artifacts (docs-only)

Create `docs/frontend/component-map.md` (developer/LLM reference) and `docs/frontend/structure.md`
(human-readable map) from the [Developer reference](#developer-reference-llm-reference) + the
route/ownership/flow tables above, each with a "Verified 2026-07-02" stamp. Add a one-line pointer
from the top of each to this RFC. **In the same step, replace this RFC's Developer-reference
section body with a pointer to `docs/frontend/component-map.md`** (marking the section a Step-0
snapshot) — the standalone artifacts become the **single canonical living copy**; the RFC never
carries a second one to drift. No code change.

**Verification**: both files exist; every `path:line` anchor resolves; a spot re-verify of 3
randomly-picked ownership claims against code confirms no drift; `git diff --stat` is docs-only.

**Rollback**: delete the two files (no code references them).

---

## Open questions

1. ~~**Artifact location (blocks Step 1)** — `docs/frontend/` vs `docs/architecture/frontend/`.~~
   **Resolved 2026-07-02:** `docs/frontend/`. Confirmed no existing frontend-reference subdir or
   doc exists (the `docs/` tree today is `archive/ buckit/ contracts/ editorial/ plans/ reviews/
   rfcs/` — nothing frontend-scoped), so a new `docs/frontend/` is the natural, non-colliding home
   (sibling to `docs/contracts/`). `docs/architecture/frontend/` is rejected — `architecture.md` is
   the unreliable hand-maintained doc this map exists to *not* depend on
   (memory `reference-architecture-md-unreliable`); nesting under it invites confusion.
2. ~~**Map refresh trigger (blocks longevity)**~~ **Resolved 2026-07-02:** re-verify both artifacts
   in the step of any RFC whose [Component-map impact template](#component-map-impact-template-for-future-rfcs)
   touches track-click / overlay / cross-island / shared-chrome. Spot re-verify 3 ownership claims
   on each such step (mirrors how the 2026-07-02 verification above was done). A stale "Verified
   YYYY-MM-DD" stamp is the signal to re-verify, not to trust.

## Decisions log

| Date | Decision | Step |
|------|----------|------|
| 2026-07-02 | Map is dual-purpose (LLM reference + human map), code-pinned, separate from `architecture.md` (unreliable) | 0 |
| 2026-07-02 | No shared track-click component exists; documented, NOT created — out of scope for this RFC | 0 |
| 2026-07-02 | Template + impact section included so future RFCs name real touchpoints up front | 0 |
| 2026-07-02 | OQ1 resolved — artifacts go in `docs/frontend/` (new subdir; no existing frontend-reference doc; `architecture.md` nesting rejected as it's the unreliable doc this map avoids) | 0 |
| 2026-07-02 | OQ2 resolved — re-verify on any RFC whose impact template touches track-click/overlay/cross-island/shared-chrome; stale "Verified" stamp = re-verify signal | 0 |
| 2026-07-02 | Pre-acceptance review: at Step 1 the RFC's Developer-reference section is replaced by a pointer to `docs/frontend/component-map.md` — standalone artifacts are the single canonical living copy (no dual-copy drift) | 0 |
| 2026-07-02 | Status draft → accepted (owner approval in session, post final review) | 0 |
| 2026-07-02 | Step 1 executed — `docs/frontend/component-map.md` + `docs/frontend/structure.md` published (Verified 2026-07-02 stamps); RFC Developer-reference section replaced by a pointer (Step-0 snapshot). Spot re-verify (5 claims: `requestPlayback:242` + exactly-2 importers, `useDismissable:24`, `PocketBuckitProvider:124`, `resolveProviderUri:210`, albumDetail handlers `:130/:144`) — drift found+fixed in artifacts: `:243`→`:242`, scrim stacks at `--z-panel:90` not `--z-overlay` | 1 |
