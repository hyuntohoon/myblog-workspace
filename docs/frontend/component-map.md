# Frontend component map — developer / LLM reference

> **Verified 2026-07-02** against `myblog_front/src/` (Astro 5 + React 19).
> Canonical living copy — produced by `docs/rfcs/ARCH-frontend-component-map.md` Step 1.
> Re-verify (3 spot claims minimum) in the step of any RFC whose impact template touches
> track-click / overlay / cross-island / shared-chrome. A stale "Verified" stamp is the
> signal to re-verify, not to trust. Human-readable companion: [structure.md](structure.md).

This is the artifact an LLM (or developer) reads to answer "who owns X" without re-grepping.
File references are `path:line` anchors relative to `myblog_front/src/`.

## Routes & islands

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

## Track-click behavior — **no shared track-row component exists**

Track interaction is fragmented across **≥6 independent code paths**. There is no common
row component. The surfaces differ in whether they **play**, **navigate**, **open detail**, or
**add to bucket** — only play is shared at the SDK layer (`requestPlayback`), never at the row layer.

| Surface | File:component | Click does | Playback path | Shared with? |
|---|---|---|---|---|
| Review tracklist (vanilla, public) | `scripts/albumDetail.client.ts` (row render `:66,:71`; delegated handlers `:124-144`) | two buttons/row: `.lfq-tt-play` (▶) + `.lfq-tt-add` (＋) | ▶ → `requestPlayback({kind:'track',trackId,title})` (`:130`); ＋ → `window` event `pb:add-track` (`:144`) → `ReviewTrackAdder` | play only |
| Pocket tray drawer members | `components/member/pocket/PocketTray.tsx:587` | React `<button onClick={onPlay}>` ▶ (list view) | `onPlay`→`playbackTargetFor` (`:53-59`)→`requestPlayback` (`:412`) | play (different wrapper) |
| Member `AlbumDetail` tracklist | `components/member/AlbumDetail.tsx:154-178` | not clickable — read-only `<li>` | none | — |
| `LikedBoard` rows | `components/member/LikedBoard.tsx:274-285` | cover/title → `onOpen` (opens `AlbumDetail`); ⋯ → 담기/평론쓰기 | none | detail/add (via `BucketPickerSheet`, not play) |
| Search track rows + header | `components/search/SearchPage.tsx:67-91`, `HeaderSearch.tsx:295-308` | `ResultRow` `action` union — track rows are `action:'static'` (not clickable) | none | — |
| Writer `RecommendedTracksBlock` / `ArtistDetail` | `components/writer/RecommendedTracksBlock.tsx:66-76`, `writer/ArtistDetail.tsx:43` | ★/☆ pick / `onPickTrack` (select-for-review) | none | selection (not play) |

`requestPlayback` (`lib/spotifyPlayback.ts:242`) — the **only** SDK owner — is imported
in exactly **2 files**: `scripts/albumDetail.client.ts` and `components/member/pocket/PocketTray.tsx`.
Every other surface has no play affordance.

**Verdict (documented, not fixed):** play funnels through the shared `requestPlayback` SDK
layer; the **row UI** around it is re-implemented per surface (vanilla delegated-click in the
review tracklist vs React `onClick` in the tray), and navigation/detail-open/add-to-bucket are
each separate paths. A future unified `<TrackRow action={...}>` would mirror the existing
`search/atoms.tsx` `RowAction` union + call the already-shared `requestPlayback` — documented
here as the seam, deliberately **not created** (ARCH-frontend-component-map non-goal).

## Ownership by domain

- **track row rendering** — vanilla review tracklist (`scripts/albumDetail.client.ts:66,71`
  render `data-track-id` buttons; delegated `root.addEventListener('click')` handlers `:124-144`);
  React `AlbumDetail.Tracklist` (`components/member/AlbumDetail.tsx:154`, read-only `<li>`);
  `LikedBoard.Row` (`components/member/LikedBoard.tsx:274`); `search/atoms.tsx` `ResultRow`
  (shared by `SearchPage`/`HeaderSearch`/`CommandPalette`, `action` union navigate/button/static);
  `writer/RecommendedTracksBlock.tsx:66` (★ toggle); `writer/ArtistDetail.tsx:43` (`onPickTrack`).
  **No shared track-row component.**
- **album detail** — vanilla `scripts/albumDetail.client.ts` + `albumDetail.fetch.client.ts`
  (review tracklist, `sessionCache` cache) vs React `components/member/AlbumDetail.tsx` (member
  modal/slide-over, `lib/albumDetail.ts` cache). `ArtistHub` renders catalog + reviewed-album cards.
- **artist** — `components/artist/ArtistHub.tsx` (public hub, runtime fetch; top-tracks are plain
  non-clickable `<li>`); `lib/artistNames.ts` (build-time link resolution); `AddArtistModal`
  (member); aliases live backend-side (`artists.aliases`).
- **bucket** — `components/member/BucketBoard.tsx` (board + `AlbumChip` tile + DnD + `TrashDrawer`);
  `pocket/PocketTray.tsx` (site-wide tray drawer); `pocket/PocketBuckit.tsx` (root island,
  `null` when `!isLoggedIn()`); `pocket/PocketBuckitProvider.tsx` (the one React context);
  `pocket/AddToBucketMenu.tsx` (portable add, public+authed); `BucketPickerSheet.tsx` (member-only picker).
- **playback** — `lib/spotifyPlayback.ts` (the **only** SDK/token owner: `ensureSdk` `:140`,
  `getStreamingToken` `:70`, `resolveProviderUri` `:210`, `requestPlayback` `:242`);
  `components/member/NowPlaying.tsx` (read-only now-playing snapshot — **not a player**, no ▶ button);
  `components/member/spotify.api.ts` (worker-fed cache reads: now-playing/recent-tracks/library/sync).
- **search** — `components/search/HeaderSearch.tsx` (⌘K header dropdown); `SearchPage.tsx` (`/search`);
  `search/atoms.tsx` (`ResultRow`/`GCover`/`GStars` shared); `writer/CommandPalette.tsx` (⌘K palette,
  reuses `ResultRow`); `lib/useMusicSearch.ts` (headless core). `search-bar.astro`+`searchBarDb.client.ts`
  = orphaned.

## Overlay / drawer / store / context / cache ownership

- **Overlay primitives** — `.lf-scrim` / `.lf-slideover` (`styles/member.css:193,203`) and
  `.lf-modal-card`. Z-tokens in `styles/global.css:52-53`: `--z-overlay: 80`, `--z-panel: 90`
  — the scrim/slide-over primitives stack at `--z-panel`. `useDismissable`
  (`lib/useDismissable.ts:24`) = ESC + focus trap/restore. The centered-600px pattern
  (`StandardModal`) is **not** the Spotify-mobile full-bleed shape.
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
  shared context; they communicate only via `bucketStore` + `pb:*` window CustomEvents.
- **React context** — exactly one provider: `PocketBuckitProvider`
  (`components/member/pocket/PocketBuckitProvider.tsx:124`, `PocketContext`/`usePocket`).
  `theme-provider.astro` is an inline `<script is:inline>` (vanilla `data-theme`), not React context.
- **Cache / data** — no React Query/SWR. `apiFetch` (`lib/api.ts:65-88`, 401→refresh→`goLogin`);
  `safeFetch` (8s timeout); `useMusicSearch` (`lib/useMusicSearch.ts`, headless search + `seqRef`
  race guard + 3s Spotify cooldown); `sessionCache` (`lib/sessionCache.ts`, two-tier GET cache);
  `lib/albumDetail.ts` (in-memory + inflight-dedup album-detail cache, used by the React modal
  — the vanilla review tracklist uses `sessionCache` directly).

## Key data/state flows

1. **Bucket tree flow** — `bucketStore` singleton holds the user-scoped tree; `PocketBuckitProvider`
   calls `useBucketStore` (tray island) and `BucketBoard` calls `useBucketStore` (profile island).
   Mutations (`setTree`/`ensureFresh`) notify both roots via `useSyncExternalStore`.
2. **Cross-island `pb:*` events** — tray↔board open mirror (`pb:toggle`/`pb:closed`/`pb:open-state`)
   and DnD handoff (`pb:dnd-start`/`pb:dnd-end` tray→board; `pb:board-dnd-*`/`pb:board-drop` board→tray).
   Reverse DnD populates the board's module-level `dnd` synchronously.
3. **Playback flow** — a ▶ click → `requestPlayback(target)` → `getStreamingToken` (cached, JWT) →
   `ensureConnectedDevice` (lazy SDK, `:171`) → `resolveProviderUri` (DB-id→spotify URI via
   `GET /api/playback/resolve`, edge_guard-only) → `PUT /v1/me/player/play` (direct client-side
   `fetch('https://api.spotify.com/...')`, `:276`). Token+SDK load fire **only** on a real play
   action (rule #9). `NowPlaying` is a separate read path off the worker snapshot
   (`GET /api/library/now-playing`).

## Duplicate / overlapping responsibilities (load-bearing)

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

## Component-map impact template (paste into future RFCs)

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
