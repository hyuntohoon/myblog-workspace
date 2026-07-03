# Frontend component map — developer / LLM reference

> **Verified 2026-07-03** against `myblog_front/src/` (Astro 5 + React 19).
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

## Track-click behavior — shared `TrackRow` for React member islands

**Contract point** (ARCH-entity-interaction-contract Step 2):
`components/shared/TrackRow.tsx` — one row component with a **declared action set**
`{lyrics?, open?}` (`play`/`add` are reserved slots — granting a surface a NEW play/add
affordance is a product decision per RFC OQ2, implemented in TrackRow when approved).
Consumers: `AlbumDetail` tracklist + `LikedBoard` list rows (both inside the `ProfileApp`
island). A future track action on these surfaces is wired in TrackRow once, not per surface.
`components/search/SearchPage.tsx` has an unrelated local `SearchTrackRow` (search-static).

**Explicitly excluded:** the vanilla review tracklist (`scripts/albumDetail.client.ts`)
stays hand-rolled (RFC non-goal: no vanilla → React migration; revival trigger = a track
action that must ship on the public review page). Writer pick rows and search rows keep
their own idioms (`RowAction` union in `search/atoms.tsx` — TrackRow promotes that idea
to compound actions).

| Surface | File:component | Click does | Playback path | Shared row? |
|---|---|---|---|---|
| Review tracklist (vanilla, public) | `scripts/albumDetail.client.ts` (row render `:66,:71`; delegated handlers `:124-144`) | two buttons/row: `.lfq-tt-play` (▶) + `.lfq-tt-add` (＋) | ▶ → `requestPlayback({kind:'track',trackId,title})` (`:130`); ＋ → `window` event `pb:add-track` (`:144`) → `ReviewTrackAdder` | **no — excluded** |
| Pocket tray drawer members | `components/member/pocket/PocketTray.tsx:587` | React `<button onClick={onPlay}>` ▶ (list view) | `onPlay`→`playbackTargetFor` (`:53-59`)→`requestPlayback` (`:412`) | no (tray lyrics deferred — RFC OQ4, separate React root) |
| Member `AlbumDetail` tracklist | `components/member/AlbumDetail.tsx` `Tracklist` | `TrackRow` — 가사 (when track has `spotify_id`) → lyrics viewer non-live | none | **TrackRow** (`lyrics`) |
| `LikedBoard` list rows | `components/member/LikedBoard.tsx` `Row` | `TrackRow` — identity → `onOpen` (detail); 가사 → lyrics viewer non-live; ⋯ → 담기/평론쓰기 (surface-specific trailing) | none | **TrackRow** (`open`+`lyrics`); card view NOT adopted (no lyrics affordance there) |
| Search track rows + header | `components/search/SearchPage.tsx` (`SearchTrackRow`), `HeaderSearch.tsx:295-308` | `ResultRow` `action` union — track rows are `action:'static'` (not clickable) | none | no |
| Writer `RecommendedTracksBlock` / `ArtistDetail` | `components/writer/RecommendedTracksBlock.tsx:66-76`, `writer/ArtistDetail.tsx:43` | ★/☆ pick / `onPickTrack` (select-for-review) | none | no |

`requestPlayback` (`lib/spotifyPlayback.ts:242`) — the **only** SDK owner — is imported
in exactly **2 files**: `scripts/albumDetail.client.ts` and `components/member/pocket/PocketTray.tsx`.
TrackRow adds **no** play affordance anywhere (OQ2 default).

**Static lyrics entry** (privacy-scoped): TrackRow's `lyrics` action opens `ProfileApp`'s
existing `LyricsViewer` mount with `{trackId, progressMs: null, live: false}` — authed
member island only; grep-verified no lyric affordance/import exists in any public-route
component (FEAT-lyrics-viewer invariant unchanged).

## Entity navigation — `lib/entityLinks.ts`

**Contract point** (ARCH-entity-interaction-contract Step 3):
`lib/entityLinks.ts` — `artistHref(id)` / `reviewHref(slug)` return the canonical
**trailing-slash** form. Every artist/review href in `components/` and `scripts/` is built
by these helpers; hand-rolled `/artist/${…}` / `/review/${…}` template literals exist only
in `pages/` internals (grep-gated in the RFC). OQ3 probe (2026-07-03): the CloudFront
viewer-request function serves the slashless form too (200, no redirect) — canonicalizing
ends cache-key/URL drift, it does not fix a 404.

Artist names link to `/artist/[id]` on: search surfaces (`SearchPage` card, `HeaderSearch`
row), tray/board artist members (`window.location.assign`), the public review hero, and —
new in Step 3 — the member `AlbumDetail` InfoBody (`.lf-artist-link`). **Not linkable**
(payload carries names only, no artist ids): `NowPlaying`, `LikedBoard` rows — revival
trigger = backend adds `artist_id` to saved-tracks / now-playing payloads.

## Ownership by domain

- **track row rendering** — **shared `components/shared/TrackRow.tsx`** (declared actions
  `{lyrics?, open?}`; consumers `AlbumDetail.Tracklist` + `LikedBoard.Row` list view);
  still hand-rolled: vanilla review tracklist (`scripts/albumDetail.client.ts:66,71` +
  delegated handlers `:124-144`, excluded by RFC), `search/atoms.tsx` `ResultRow`
  (shared by `SearchPage`/`HeaderSearch`/`CommandPalette`, `action` union navigate/button/static),
  `writer/RecommendedTracksBlock.tsx:66` (★ toggle), `writer/ArtistDetail.tsx:43` (`onPickTrack`),
  `LikedBoard` card view.
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
  reuses `ResultRow`); `lib/useMusicSearch.ts` (headless core). (`search-bar.astro` +
  `searchBarDb.client.ts` were orphaned → deleted in ARCH-entity-interaction-contract Step 3.)

## Overlay / drawer / store / context / cache ownership

- **Overlay primitives** — `.lf-scrim` / `.lf-slideover` (`styles/member.css:193,203`) and
  `.lf-modal-card`. Z-tokens in `styles/global.css:52-53`: `--z-overlay: 80`, `--z-panel: 90`
  — the scrim/slide-over primitives stack at `--z-panel`. `useDismissable`
  (`lib/useDismissable.ts`) = ESC + focus trap/restore **+ a module-level open-overlay
  stack: only the top-most overlay handles ESC / traps Tab** (overlays nest — the lyrics
  viewer opens OVER the album-detail modal; every instance holds a document-level capture
  keydown listener, so without the stack one ESC would close all layers). The
  centered-600px pattern (`StandardModal`) is **not** the Spotify-mobile full-bleed shape.
- **Who mounts overlays** — `ProfileApp` (`AlbumDetail` + `LyricsViewer` — the lyrics mount
  serves the dynamic NowPlaying entry (`live:true`), the `?lyrics=` debug entry, and the
  TrackRow static entry (`live:false`)), `AlbumDetail` (`StandardModal` + `MemoWindow`),
  `OverviewDash` (`RecentAlbumsModal`/`RecentTracksModal`), `ImportAnalysis`, `ReviewsTab`
  (DELETE scrim), `BucketBoard` (`TrashDrawer`). `AddToBucketMenu` / `BucketPickerSheet`
  deliberately do **not** use `useDismissable` (inline backdrop + manual ESC).
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
