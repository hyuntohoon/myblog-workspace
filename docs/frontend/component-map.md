# Frontend component map — developer / LLM reference

> **Verified 2026-08-05** against `myblog_front` `origin/main` `734925e`
> (`ARCH-entity-interaction-domain-audit` Step 1 — cross-domain rewrite: fixes two claims this
> step found actively **wrong**, not merely stale — the "NowPlaying / LikedBoard artists not
> linkable" line (false since front #293/#299, 2026-07-19/21 — `ARCH-entity-interaction-v2` had
> already flagged this but the doc was never fixed) and the "`AddToBucketMenu` … manual ESC" line
> (`AddToBucketMenu` has **zero** ESC handling of any kind — grep-verified, see the modal registry
> below) — and adds the three cross-domain registries (events, state owners, modals) for the
> domains `ARCH-entity-interaction-v2` scopes out. **Scope handoff, stated explicitly (this doc's
> own "don't duplicate a full rule set across files" convention):** this step does **not** transcribe
> `ARCH-entity-interaction-v2`'s E1 canonical album/track/artist definitions here — that transcription
> is still that RFC's own Step 6, not done by this rewrite, and not duplicated here either. Until
> Step 6 runs, `ARCH-entity-interaction-v2.md` itself is the source for E1/E2/E3; this doc only
> points at it (see "Entity navigation" and "Track-click behavior" below, both updated for currency
> but not restructured to hold E1's content).
> Re-verify (3 spot claims minimum) in the step of any RFC whose impact template touches
> track-click / overlay / cross-island / shared-chrome / global-event / state-ownership. A stale
> "Verified" stamp is the signal to re-verify, not to trust — **and per this step's own finding, a
> current stamp does not guarantee correctness either**: check the claim, not just the date.
> Human-readable companion: [structure.md](structure.md).

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
| `/profile` | `pages/profile.astro` | — (noindex redirect → `/members/?me`, preserves `?tab=`) | n/a — retired by profile-merge PR3 (front #280); the self-dashboard now lives at `/members/?me`. `profile.guard.ts` survives guarding `/settings` |
| `/members/` | `pages/members/index.astro` | `MembersHub` (`client:only`) — no param = directory, `?u=<handle>` = runtime profile, `?me` = self | Public (self view authed via `isSelf`) |
| `/members/[handle]` | `pages/members/[handle].astro` | `MemberProfile` (`client:only`) → lazy `SelfDashboard` on `isSelf` | Public (static SEO prebuild, reviewers-only index) |
| `/settings/` | `pages/settings.astro` (+ `settings/spotify/callback`) | `SettingsApp` (`client:only`) | **Authed** |
| `/releases/` | `pages/releases/index.astro` | `ReleaseCalendar` (`client:load`) | Public |
| `/privacy` | `pages/privacy.astro` | none (static) | Public |
| `/buckets` | `pages/buckets.astro` | — (redirect → `/members/?me&tab=bucket`) | n/a |
| `/drafts` | `pages/drafts.astro` | none (vanilla table) | Authed (inline `isLoggedIn()` → `goLogin`) |
| `/write` | `pages/write.astro` | `WriterApp` (`client:load`) | **Authed** (`scripts/write.guard.ts`) |

Shared chrome (`Header`/`Footer`/`PocketBuckit`) is mounted once in `layouts/layout.astro:35-38`.
`write-layout.astro` is standalone (no Header/Footer/Pocket).

## Track-click behavior — shared `TrackRow` for React member islands

**Contract point** (ARCH-entity-interaction-contract Step 2; slots opened by
`ARCH-entity-interaction-v2` Step 5, front #354, 2026-08-05):
`components/shared/TrackRow.tsx` — one row component with a **declared action set**
`{lyrics?, open?, openLyrics?, play?, add?, drag?}`. `open` and `openLyrics` are mutually
exclusive identity actions (`open` wraps only the identity cell; `openLyrics` makes the WHOLE
row the click/keyboard target — the shape the memo window needs, see below). `play`/`add` are
plain trailing-button slots with **no queue/bucket logic in the component** — the surface owns
that. `drag` (E2 `DragPayload`) makes the row natively `draggable` and dispatches both the
tray→board and board→tray bridge pairs (`PB_DND_*`/`PB_BOARD_DND_*`, see the event registry
below) so a future grant works against either drop target with no further wiring.
**No surface has granted `play`/`add`/`drag` yet** (verified by `TrackRow.test.tsx`'s callback
tests firing in isolation, not a live drop target) — granting one is still a per-surface,
Step-5-tracked decision; only the slot's *existence* stopped being reserved.
Consumers: `AlbumDetail` tracklist (via the shared `AlbumDetailView`, Step 1), `AlbumDetail`'s
`MemoWindow` (via `openLyrics` — adopted Step 5, see below) + `LikedBoard` list rows (all three
inside the `SelfDashboard` island). A future track action on these surfaces is wired in TrackRow
once, not per surface.
Bespoke **public** track rows (`SearchPage.SearchTrackRow`, `HeaderSearch` `ResultRow`,
`ArtistHub` top-tracks) are NOT TrackRow — they dispatch `openTrackAlbum` directly
(ARCH-entity-interaction-unify Step 3; a track opens the app-wide album overlay).

**Explicitly excluded:** the vanilla review tracklist (`scripts/albumDetail.client.ts`)
stays hand-rolled (RFC non-goal: no vanilla → React migration; revival trigger = a track
action that must ship on the public review page). Writer pick rows and search rows keep
their own idioms (`RowAction` union in `search/atoms.tsx` — TrackRow promotes that idea
to compound actions).

| Surface | File:component | Click does | Playback path | Shared row? |
|---|---|---|---|---|
| Review tracklist (vanilla, public) | `scripts/albumDetail.client.ts` (row render `:66,:71`; delegated handlers `:124-144`) | two buttons/row: `.lfq-tt-play` (▶) + `.lfq-tt-add` (＋) | ▶ → `requestPlayback({kind:'track',trackId,title})` (`:130`); ＋ → `window` event `pb:add-track` (`:144`) → `ReviewTrackAdder` | **no — excluded** |
| Pocket tray drawer members | `components/member/pocket/PocketTray.tsx:587` | React `<button onClick={onPlay}>` ▶ (list view) | `onPlay`→`playbackTargetFor` (`:53-59`)→`requestPlayback` (`:412`) | no (tray lyrics deferred — RFC OQ4, separate React root) |
| Member `AlbumDetail` tracklist (`StandardModal`) | `components/album/AlbumDetailView.tsx` `Tracklist` | `TrackRow` — a small 가사 button (when the track has `spotify_id`) → **`LyricsSheet`** | none | **TrackRow** (`lyrics`) |
| Member `AlbumDetail` **memo window** (bucket albums) | `components/member/AlbumDetail.tsx` `MemoWindow` (`AlbumDetail.tsx:435`) | `TrackRow` with `openLyrics` — **the whole row is the button** (own `role="button"`, keyboard support) → `LyricsSheet` | none | **TrackRow** (`openLyrics`) — adopted Step 5 (front #354, 2026-08-05); the twin noted below is **resolved**, not pending |
| `LikedBoard` list rows | `components/member/LikedBoard.tsx` `Row` | `TrackRow` — identity → `onOpen` (detail, **member modal** — writable path, NOT the event); 가사 → lyrics viewer non-live; ⋯ → 담기/평론쓰기 (surface-specific trailing) | none | **TrackRow** (`open`+`lyrics`); card view NOT adopted (no lyrics affordance there) |
| Search track rows (public) | `components/search/SearchPage.tsx` (`SearchTrackRow`), `HeaderSearch` `ResultRow` (dropdown 트랙 rows) | **Step 3**: a track with a DB `albumId` opens the app-wide album overlay (`openTrackAlbum`); id-less (Spotify-only) rows stay static | none | no (bespoke → `openTrackAlbum`) |
| Artist top-tracks (public) | `components/artist/ArtistHub.tsx` `art-tt-open` | **Step 3**: `<button>` → `openTrackAlbum` (Music_TrackItem.album_id always set) | none | no (bespoke → `openTrackAlbum`) |
| Writer `RecommendedTracksBlock` / `ArtistDetail` | `components/writer/RecommendedTracksBlock.tsx:66-76`, `writer/ArtistDetail.tsx:43` | ★/☆ pick / `onPickTrack` (select-for-review) | none | no |

`requestPlayback` (`lib/spotifyPlayback.ts:242`) — the **only** SDK owner — is imported
in exactly **2 files**: `scripts/albumDetail.client.ts` and `components/member/pocket/PocketTray.tsx`.
**Corrected 2026-08-05**: TrackRow's `play` slot exists (opened Step 5) but **no surface grants
it yet**, so today it still adds no play affordance anywhere in practice — same outcome as the
old "OQ2 default" line, different reason (an ungranted slot, not a reserved one).

**Static lyrics entry** (privacy-scoped): both static entries route through `SelfDashboard`'s
`openStaticLyrics`, which mounts **`LyricsSheet`** — not `LyricsViewer`. Only `NowPlaying`'s 가사 tap
opens the viewer (`kind: 'live'`). Authed member island only; grep-verified no lyric affordance or
import exists in any public-route component. The public `AlbumOverlay` renders the same
`AlbumDetailView` but omits `onOpenLyrics`, and that omission IS the privacy boundary — the tracklist
simply has no lyrics affordance when the prop is absent.

**Since 2026-07-28 the sheet is owner-only**: `GET /api/lyrics/{id}` is `require_owner`, so a
signed-in non-owner opening either entry gets an explicit "가사는 운영자만 볼 수 있어요" state
(RFC `FEAT-lyrics-annotations` §6.9 O2).

> ✅ **Resolved 2026-08-05 (ARCH-entity-interaction-v2 Step 5, front #354).** The memo window used to
> hand-roll its own `.memo-trow` track rows because `TrackRow`'s only identity action (`open`) meant
> "open the album," and the memo window's rows have nothing else to click — the twin this box used to
> warn about. `TrackRowActions` gained `openLyrics` (whole-row click + keyboard, mutually exclusive
> with `open`) specifically to let `MemoWindow` adopt the shared component; the dead `.memo-trow*` CSS
> was removed with it. **The mount, not the row, is still doubled** — see the lyrics-host note under
> "Who mounts overlays" below: `SelfDashboard`'s shared slot and `MemoWindow`'s own local dock are two
> separate `LyricsSheet`/`DockableLyricsSheet` hosts, for an unrelated, still-valid reason (docking
> needs a remount-safe ref). Do not conflate the two — the row twin is gone; the host split is not.

## Entity navigation — `lib/entityLinks.ts`

**Contract point** (ARCH-entity-interaction-contract Step 3):
`lib/entityLinks.ts` — `artistHref(id)` / `reviewHref(slug)` return the canonical
**trailing-slash** form. Every artist/review href in `components/` and `scripts/` is built
by these helpers; hand-rolled `/artist/${…}` / `/review/${…}` template literals exist only
in `pages/` internals (grep-gated in the RFC). OQ3 probe (2026-07-03): the CloudFront
viewer-request function serves the slashless form too (200, no redirect) — canonicalizing
ends cache-key/URL drift, it does not fix a 404.

Artist names link to `/artist/[id]` on: search surfaces (`SearchPage` card, `HeaderSearch`
row), tray/board artist members (`window.location.assign`), the public review hero, the member
`AlbumDetail` InfoBody (`.lf-artist-link`, Step 3), and — **corrected 2026-08-05, was wrongly
marked "not linkable" here since 2026-07-19/21** — `NowPlaying.tsx` (`artistHref` import,
`ArtistNames` renders real links; shipped `FEAT-member-player` #293) and `LikedBoard.tsx`
(carries `artist_id` from `SavedTrackItem.artist_id`; shipped `RFC-ui-surface-unification`
Step 4, #299). `ARCH-entity-interaction-v2` Step 1 (2026-08-04) had already measured this claim
false; this doc was never fixed until now — a reminder that a stale claim can outlive the RFC
that found it stale. **19 `artistHref(` call sites across 16 files** is the current count
(`ARCH-entity-interaction-v2` §D); `C8 ReleaseRadar` was the one remaining gap (held
`artist_id`, rendered no link) and was wired in that RFC's Step 5 first slice (front #353).

**Album & track have no route — they open the app-wide overlay** (ARCH-entity-interaction-unify).
`entityLinks` re-exports `openAlbum(detail)` and `openTrackAlbum(track)` from the public-safe
`lib/entityEvents.ts` (window event `ent:open-album` → the layout-mounted `AlbumOverlay`, a
read-only view — no member types, no lyrics affordance). Public callers: `TodayAlbumBuckit`
(home), `ArtistHub` catalog albums + top-tracks, `SearchPage` album cards + track rows,
`HeaderSearch` dropdown album + track rows. `openTrackAlbum` is a no-op when the track has no
DB `albumId` (Spotify-only hit → non-navigable, OQ4). **Member** track/album opens stay on the
prop path (`onOpen(DetailTarget)` → the writable `AlbumDetail` modal), NOT the event — the event
can't carry writable/bucket context (architect Step-1 rule; do not "unify" member call sites
onto the lossy event). The public `/review/[slug]` inline editorial tracklist is a distinct
surface and is untouched (Step 2 audit).

## Ownership by domain

- **track row rendering** — **shared `components/shared/TrackRow.tsx`** (declared actions
  `{lyrics?, open?, openLyrics?, play?, add?, drag?}` — see "Track-click behavior" above for the
  full contract; consumers `AlbumDetail.Tracklist`, `AlbumDetail.MemoWindow` (`openLyrics`,
  Step 5) + `LikedBoard.Row` list view); still hand-rolled: vanilla review tracklist
  (`scripts/albumDetail.client.ts:66,71` +
  delegated handlers `:124-144`, excluded by RFC), `search/atoms.tsx` `ResultRow`
  (shared by `SearchPage`/`HeaderSearch`/`CommandPalette`, `action` union navigate/button/static),
  `writer/RecommendedTracksBlock.tsx:66` (★ toggle), `writer/ArtistDetail.tsx:43` (`onPickTrack`),
  `LikedBoard` card view.
- **album detail** — the read-only body is the shared `components/album/AlbumDetailView.tsx`
  (Step 1), rendered by BOTH the app-wide `components/album/AlbumOverlay.tsx` (public, event-opened,
  `lib/albumDetail.ts` cache) and the member `components/member/AlbumDetail.tsx` (writable modal:
  `MemoWindow`/edit stay member-side). Separately, the public `/review/[slug]` keeps its **inline
  editorial tracklist** (vanilla `scripts/albumDetail.client.ts` + `albumDetail.fetch.client.ts`,
  ★ picks + ▶/＋, `sessionCache`) — a distinct surface, not a modal (Step 2 audit).
- **artist** — `components/artist/ArtistHub.tsx` (public hub, runtime fetch; catalog albums →
  `openAlbum`, top-tracks (`art-tt-open`) → `openTrackAlbum` — Step 2/3); `lib/artistNames.ts`
  (build-time link resolution); `AddArtistModal` (member); aliases live backend-side (`artists.aliases`).
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
- **Who mounts overlays** — `layouts/layout.astro` mounts the **app-wide read-only `AlbumOverlay`**
  (sibling to `PocketBuckit`, un-gated, `transition:persist`; opens on `ent:open-album`, closes on
  ESC/scrim/✕ and `astro:before-swap`). `SelfDashboard` (`AlbumDetail` + `LyricsViewer`/`LyricsSheet` —
  **two lyrics hosts, not one**: `SelfDashboard`'s own `lyrics` slot, discriminated `kind:'live'|'static'`,
  serves the dynamic NowPlaying entry, the `?lyrics=` debug entry, the TrackRow static entry, and
  `AlbumDetail`'s `StandardModal` (info/edit mode) via `onOpenLyrics`; separately, `AlbumDetail`'s
  `MemoWindow` mounts its **own** `LyricsSheet`/`DockableLyricsSheet` directly inside itself
  (`AlbumDetail.tsx`, `hostRef={cardRef}`) — deliberate, so the tear/dock state machine never crosses a
  remount boundary; `MemoWindow` is not given `onOpenLyrics` and cannot reach the shared slot). Full
  registry below — **"Modal / overlay registry."**
  `AddToBucketMenu` / `BucketPickerSheet` deliberately do **not** use `useDismissable`, but **not
  symmetrically**: `BucketPickerSheet` has a real manual ESC handler (`useEffect` + `keydown`);
  `AddToBucketMenu` has **none at all** (grep-verified, zero hits) — corrected 2026-08-05, this line
  previously claimed both had "manual ESC," which was false for `AddToBucketMenu`.
- **State store** — `lib/pocketBuckit/bucketStore.ts`: framework-agnostic observable singleton
  (user-scoped bucket tree, sessionStorage `pb:cache:buckets:<sub>`, SWR 5-min,
  `useSyncExternalStore` via `useBucketStore()`).
- **Cross-island events** — `lib/pocketBuckit/events.ts`: `pb:toggle`, `pb:closed`,
  `pb:open-state`, `pb:dnd-start`/`pb:dnd-end`, `pb:board-dnd-start`/`end`/`dropped`.
  `SelfDashboard`'s `BucketBoard` and layout's `PocketBuckit` are **separate React roots** — no
  shared context; they communicate only via `bucketStore` + `pb:*` window CustomEvents. Full
  event inventory (incl. the one drift instance) → "Global CustomEvent registry" below.
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

1. **Album-detail paths — REFRAMED/RESOLVED (ARCH-entity-interaction-unify).** The read-only
   detail body is now the single shared `components/album/AlbumDetailView.tsx` (Step 1), used by
   both the public app-wide `AlbumOverlay` and the member writable `AlbumDetail` modal. The
   Step-2 audit established these are NOT interchangeable with the third path — the vanilla
   `/review/[slug]` `#albumDetail` (`scripts/albumDetail.client.ts`, ▶/＋, `sessionCache`) — which
   is an **inline editorial tracklist**, not a click-to-open modal, and stays as its own surface
   (deleting it = UX regression). So there is no remaining "delete the dup" action: the read view
   is shared; the review inline tracklist is intentionally separate.
2. **Two "add to bucket" flows, three call sites — corrected 2026-08-05 (BUG-20, front #355).**
   `AddToBucketMenu` (portable, public+authed, album-or-track, self-contained: fetches its own
   tree, owns its own mutate/toast, logged-out intent handoff via `intent.ts` — deliberately never
   reuses `BucketPickerSheet`, which would render unstyled off the member pages) vs
   `BucketPickerSheet` (a dumb generic tree-picker: takes `tree`/`skip`/`onPick`, owns no
   fetch/mutate itself). **`BucketPickerSheet` has three callers, not one** —
   `BucketBoard.tsx` (move/nest, `skip` = cycle guard), `LikedBoard.tsx` (promote-to-bucket), and
   the review page uses `AddToBucketMenu` for its own add. **Independently re-examined and NOT
   merged** — they do different jobs; `necessity-gate` still applies (no named concrete harm from
   keeping them separate). The actual bug found was orthogonal to this split: the rule "the
   sync-owned `spotify_library` bucket is never a manual-add target" had no single owner — two of
   three enforcing call sites hardcoded the string literal `'spotify_library'`, one used the
   `SLIB_KIND` constant, and `LikedBoard.tsx`'s `BucketPickerSheet` call **omitted the check
   entirely** (no `skip` prop), letting a member write into the sync mirror with no server-side
   backstop either (`_assert_item_type_allowed` gates only on `bucket.type`, never `kind`). Fixed
   by one exported predicate, `isManualAddTarget(bucket)` (`lib/buckets.ts`) — every add-to-bucket
   call site must route through it; do not re-test `kind === 'spotify_library'` locally.

## Global CustomEvent registry — added `ARCH-entity-interaction-domain-audit` Step 1, 2026-08-05

Every `window.dispatchEvent(new CustomEvent(...))` name in the app, where it's declared, and
whether it's actually single-owned. **Rule going forward** (`ARCH-entity-interaction-domain-audit`
G3): a new app-level event's name+payload is declared in `lib/entityEvents.ts` or
`lib/pocketBuckit/events.ts` — no inline `new CustomEvent(<string literal>)` anywhere else,
including vanilla `scripts/`.

| Event | Declared in | Dispatched from | Listened by | Single-owned? |
|---|---|---|---|---|
| `ent:open-album` (`ENT_OPEN_ALBUM`) | `lib/entityEvents.ts` | ~15 public/member surfaces via `openAlbum()`/`openTrackAlbum()` | `AlbumOverlay.tsx` (layout-mounted) | yes |
| `ent:album-state-changed` (`ENT_ALBUM_STATE_CHANGED`) | `lib/entityEvents.ts` | `notifyAlbumStateChanged()` | `BucketBoard.tsx` | yes |
| `ent:open-live-lyrics` (`ENT_OPEN_LIVE_LYRICS`) | `lib/entityEvents.ts` | `openLiveLyrics()`, called from `PocketTray.tsx` | `SelfDashboard.tsx` | yes |
| `pb:toggle`, `pb:closed`, `pb:open-state`, `pb:dnd-start`/`end`, `pb:board-dnd-start`/`end`, `pb:board-drop` | `lib/pocketBuckit/events.ts` (7 constants) | `BucketBoard.tsx`, `TrackRow.tsx`, `PocketTray.tsx`, `PocketBuckit.tsx` | `BucketBoard.tsx`, `PocketBuckit.tsx`, `pocketBuckit/boardDnd.ts` | yes |
| `pb:add-track` (`PB_ADD_TRACK_EVENT`) | **`ReviewTrackAdder.tsx:16`**, not `pocketBuckit/events.ts` — despite that file's own header comment citing it as the reason the file exists | `ReviewTrackAdder`'s callers, **and as a raw string literal** (not the imported constant) from the vanilla script `scripts/albumDetail.client.ts:176` | `ReviewTrackAdder.tsx:34` | **no — the exact drift the centralizing file warns against**, live today. Fix tracked: `ARCH-entity-interaction-domain-audit` Step 2 |
| `album:detail` | raw string, `scripts/albumDetail.fetch.client.ts` | 〃 | raw string, `scripts/albumDetail.client.ts` (module-scope, bound once by design — vanilla script, not a React effect) | intentional exception, not a gap — permanent module-scope listener by design, documented inline |
| `myblog:playback-changed` (`MYBLOG_PLAYBACK_CHANGED`) | `lib/spotifyPlayback.ts` | `spotifyPlayback.ts` internals | `NowPlaying.tsx`, `LyricsViewer.tsx`, `lib/playback/session.ts` | yes (the *name* is single-owned; **the state it signals is not** — see the state-owner registry below) |
| `astro:page-load`, `astro:after-swap`, `astro:before-swap`, `astro:before-preparation` | framework (Astro `ClientRouter`) | Astro | `AlbumOverlay.tsx`, `HeaderSearch.tsx`, several vanilla scripts | n/a — framework lifecycle hooks, not an app contract |

Naming is colon+kebab at the wire level (`ent:*`/`pb:*`/`myblog:*`) but the **identifier**
convention is not: `ENT_OPEN_ALBUM` (no suffix) vs `PB_DND_START_EVENT` (`_EVENT` suffix) vs
`MYBLOG_PLAYBACK_CHANGED` (no suffix). Not fixed here (a rename is a bigger diff than this step's
scope); flagged so a new event picks *a* convention rather than inventing a third.

## State-owner registry — added `ARCH-entity-interaction-domain-audit` Step 1, 2026-08-05

What real-world state, which module is (or should be) canonical, who else touches it today.

| State | Canonical owner | Other current touchers (not yet consolidated) | Status |
|---|---|---|---|
| Bucket tree | `lib/pocketBuckit/bucketStore.ts` (singleton, `useSyncExternalStore`) | — | single-owned, correct |
| "What's currently playing" (track/queue/playing/device) | **should be** `lib/playback/session.ts` | `NowPlaying.tsx`'s `useNowPlaying()` hook and `LyricsViewer.tsx` **each independently** call `readLivePlayback()` and listen to `myblog:playback-changed`, each with its own hand-invented race guard for the same Spotify ack→apply window (`session.ts`'s `localWriteSeq` vs. `NowPlaying`'s `controlBusyRef`; `LyricsViewer` has a third, its own anchor/estimate loop) | **3 independent trackers, not consolidated.** Both `FEAT-member-player` and `FEAT-playback-bucket-player`'s own text name only 2 (session vs. NowPlaying); `LyricsViewer` is a third this audit found. Consolidation tracked as `ARCH-entity-interaction-domain-audit` Step 3 — **not started**, blocked on an owner sequencing decision (which RFC houses it) |
| "One tab owns playback" (write lease) | `lib/playback/ownership.ts` (localStorage lease + `BroadcastChannel`, challenge/response reclaim) | only gates `session.ts`'s writes — `NowPlaying`/`LyricsViewer` act locally regardless of lease state | correctly single-owned for what it covers; does not (and structurally can't yet) cover the other two trackers above |
| "My relationship to this album" (rating / candidate-mark / bucket memo / draft-review) | **no single owner — four independent silos, by design, not drift**: `AlbumRatingBlock` (rating/comment/candidate, `PUT /api/reviews/albums/{id}`, `album_reviews` row) / `ReviewCandidates` (a **third, separate** read of the same `review_candidate` flag via `GET /api/me/review-candidates`) / `MemoWindow`+`useBucketMemo` (`PATCH /api/buckets/{bucketId}/items/{itemId}`, `review_bucket_items.note`, bucket-scoped not album-scoped) / `WriterApp` (`POST/PUT /api/posts`, `posts` row + git commit) | — | three genuinely distinct commands over three DB rows (correct, keep separate — see reviews/memos audit); `ReviewCandidates`' redundant fetch of a flag `AlbumRatingBlock` already has is unassigned to any Step — noted here, not yet fixed |
| Manual-add-target eligibility (is bucket X a valid drop for a user-initiated add) | `lib/buckets.ts` `isManualAddTarget()` (added BUG-20, 2026-08-05) | — | single-owned as of 2026-08-05; was 3 independent hardcodes + 1 omission before |

## Modal / overlay registry — added `ARCH-entity-interaction-domain-audit` Step 1, 2026-08-05

Every `role="dialog"`-shaped component, which primitive it's built on, and — if not
`useDismissable` — whether that's a named, reasoned exception or an unreviewed gap.
**Rule going forward** (G4): a new overlay uses `useDismissable` or gets a row added here with a
stated reason.

| Component | Primitive | Notes |
|---|---|---|
| `AlbumOverlay`, `AlbumDetail`'s `StandardModal` + `MemoWindow`, `LyricsSheet`, `DockableLyricsSheet`, `LyricsViewer`, `PlaybackPanel`, `NowPlaying`, `AddArtistModal`, `AddAlbumModal`, `SettingsPanel`, `TodayPickHistory`, `TodaySongPicker`, `WriterApp`'s research drawer, `BucketBoard`'s create-bucket menu / delete-confirm modal / research panel | `useDismissable` | correct — ESC + focus trap/restore + the open-overlay stack (only the top-most layer acts) |
| `ActionSheet` | own `useEffect` + `keydown` (ESC/scrim/✕), no focus trap | **named exception** — used solely inside `BucketBoard.tsx`; has its own test (`ActionSheet.test.tsx`) covering ESC/scrim/✕. Kept separate deliberately, not migrated in this step (`useDismissable` migration is `ARCH-entity-interaction-domain-audit` Step 4) |
| `BucketPickerSheet` | own `useEffect` + `keydown` (ESC only, no focus trap) | ungapped exception — portaled, has real ESC handling, just not `useDismissable`'s trap/restore |
| `AddToBucketMenu` | **none** | **gap, not a documented exception** — zero ESC handling of any kind (grep-verified). `component-map.md` wrongly claimed "manual ESC" here until this rewrite. Migration candidate, Step 4 |
| `OverviewDash`'s `RecentAlbumsModal` / `RecentTracksModal` | own `useEffect` + `keydown`, ESC only | **gap** — same file (`OverviewDash.tsx`) also uses `useDismissable` correctly elsewhere (its own add-menu), i.e. the split is intra-file, not a principled boundary. Migration candidate, Step 4 |
| `BucketBoard`'s `TrashDrawer` | own `useEffect` + `keydown`, ESC only, **and not portaled** (unlike every sibling sheet in the same file) | **gap, two axes** — ESC handling AND mount method both diverge from its neighbors in the same file. Whether the non-portal mount is intentional is an open question (`ARCH-entity-interaction-domain-audit` OQ3) |
| `ImportAnalysis`, `writer/CommandPalette`, `writer/DraftsInbox`, `genres/gm-shared`'s peek dialog | own `useEffect` + `keydown`, ESC only | **gaps** — no stated reason to stay separate from `useDismissable`; migration candidates, Step 4 |

Overlay primitives (unchanged from before this step): `.lf-scrim`/`.lf-slideover`
(`styles/member.css:193,203`), `.lf-modal-card`; z-tokens `--z-overlay:80`/`--z-panel:90`
(`styles/global.css:52-53`). `useDismissable` itself (`lib/useDismissable.ts`) has **zero direct
unit tests** despite 15+ consumers — the single most-reused piece of modal infrastructure is the
least-tested; backfilling `useDismissable.test.ts` is part of Step 4, not deferred further.

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

### Filled — ARCH-entity-interaction-unify (Steps 1–3, 2026-07-08)

```
Component-map impact — ARCH-entity-interaction-unify (one entity → one interaction)
Verified: 2026-07-08
Routes touched:        / (layout AlbumOverlay host) — public ; /artist/[id], /search, header — public ; /profile — authed (unchanged prop path)
Track-click paths hit:  search-static → openTrackAlbum ; artist top-tracks → openTrackAlbum ; albumdetail-readonly (shared view) ; liked-board-onOpen (member modal, unchanged) ; review-tracklist (vanilla, untouched)
Play path:              none (▶/＋ on review tracklist unchanged)
Overlay changed:        new app-wide AlbumOverlay host (reuses useDismissable + .lf-modal-card + useScrollLock)
State owner:            ad-hoc (host-local open target) + ent:open-album window event
Cross-island?:          yes (ent:open-album — public-safe, NOT in pocketBuckit/events.ts ; shared store: none)
Cache touched:          albumDetail (shared, sole) ; review sessionCache path untouched
Duplicate it overlaps:  album-detail paths (read body shared; review inline tracklist intentionally separate — see #1)
```
