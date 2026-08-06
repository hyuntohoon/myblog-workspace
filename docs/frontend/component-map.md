# Frontend component map — developer / LLM reference

> **Verified 2026-08-06** against `myblog_front` `origin/main` `0504637`
> (`ARCH-entity-interaction-v2` Step 6 — the transcription the prior stamp deferred: E1's canonical
> album/track/artist definitions are now recorded here (see "Entity navigation" below), not left
> RFC-only. "Track-click behavior" is rewritten for the shipped state — Step 5's nine slices (front
> #353–#368; the grants specifically are #365 `add`, #366/#368 `drag`, #367 `play`) granted
> `play`/`add`/`drag` on every TrackRow surface that's going to get them
> (LikedBoard, the member+public `AlbumDetailView` tracklist, both `AlbumDetail` modals) and closed
> the RFC's own scope; the "no surface has granted play/add/drag yet" line this doc carried since
> 2026-08-05 is now false and is rewritten below with the real per-surface grant table. **Also caught
> while re-verifying the play path, not something this step went looking for**: `requestPlayback`
> (the name this doc cited) does not exist — it was renamed `play()` (`lib/spotifyPlayback.ts`)
> before this RFC started, and the "imported in exactly 2 files" count was wrong in both directions —
> `scripts/albumDetail.client.ts` no longer imports it at all (routes through
> `playbackSession.replaceQueueAndPlay` instead), and `play()` itself is now imported directly by
> **four** files, not two. A citation can go stale from a rename the citing doc's own author never
> saw, not just from time — check the export, not just the grep hit count.
> Re-verify (3 spot claims minimum) in the step of any RFC whose impact template touches
> track-click / overlay / cross-island / shared-chrome / global-event / state-ownership. A stale
> "Verified" stamp is the signal to re-verify, not to trust — **and a current stamp does not
> guarantee correctness either**: check the claim, not just the date.
>
> **Album-card Stage 3 addendum 2026-08-06** (front #377): the canonical shared `AlbumCard` now
> exists and is registered below, but deliberately has zero live consumers until Stage 4. Its tests
> freeze the four legacy renderers' actual, different DOM/style signatures and separately record the
> canonical cover normalization; they do not claim the legacy fallbacks were identical. Also: the
> earlier "granted `play`/`add`/`drag`
> on every TrackRow surface that's going to get them" is accurate for the surfaces it names, but should
> not be read as "every drag grant has its required touch-alternative pair" — `MemoWindow` is the one
> counterexample (`drag` without `add`, tracked as BUG-24 in `plan.md`); this file's own "Ownership by
> domain" § `TrackRow` bullet already states `MemoWindow`'s actual grant correctly (`openLyrics?+drag`).
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

## Album-card behavior — shared `AlbumCard`

**Contract point** (`ARCH-album-card-contract-and-composition` Stage 3, front #377, 2026-08-06):
`components/shared/AlbumCard.tsx`, with domain-neutral presentation in
`styles/album-card.css`. `AlbumCardData` carries only
`{catalogAlbumId, spotifyAlbumId, title, artist, artistId, cover, year, loading?}`. The declared
capability set is `{open?, play?, add?, artistOpen?, drag?}`; its union makes `drag` structurally
illegal unless the same adapter supplies the `add` tap/action-sheet path required on touch.

The primitive owns `grid`/`row` layout, cover/image/fallback/loading states, title/artist/year,
badge and `secondaryLine` slots, and whether each capability's affordance exists. Artist navigation
is a real `artistHref()` anchor: an unmodified primary click may be intercepted by `artistOpen`,
while modified clicks retain native browser behavior. A granted drag emits both existing bridge
pairs (`PB_DND_*` and `PB_BOARD_DND_*`) and derives `effectAllowed` from `DragPayload.origin`.
Adapters may override `--album-card-cover-size`; dimensions and slot contents remain surface-owned.

**Live consumers: none as of Stage 3.** Only `AlbumCard.test.tsx` imports the component. Stages 4-8
will add Home, Bucket, Memo, and editorial adapters one surface at a time; the unrelated local
`SearchPage.AlbumCard` is not this primitive. Bucket membership (`itemId`, `temp:*`, bucket/move
state), memo state, and editorial form state are forbidden in the shared component and stay in
adapters. Legacy album-surface `Cover`, `AlbumArt`, and `SubjectHero` fallback paths remain live until
their planned migrations and Stage 9 deletion. `LikedBoard.LkCover` is retained outside this RFC's
migration because it presents saved-track rows/cards, not album cards. Stage 3 tests still freeze all
four renderers' actual, different DOM/style signatures and separately pin the canonical two-letter fallback plus lazy/async
image normalization; per-surface visual/interaction parity is the gate for Stages 4-8.

## Track-click behavior — shared `TrackRow` for React member islands

**Contract point** (ARCH-entity-interaction-contract Step 2; slots opened by
`ARCH-entity-interaction-v2` Step 5, front #354, 2026-08-05 — **all three now granted somewhere,
front #362–#368, 2026-08-05/06, closing Step 5's scope**):
`components/shared/TrackRow.tsx` — one row component with a **declared action set**
`{lyrics?, open?, openLyrics?, play?, add?, drag?}`. `open` and `openLyrics` are mutually
exclusive identity actions (`open` wraps only the identity cell; `openLyrics` makes the WHOLE
row the click/keyboard target — the shape the memo window needs, see below). `play`/`add` are
plain trailing-button slots with **no queue/bucket logic in the component** — the surface owns
that (`play` calls `playbackSession.replaceQueueAndPlay({kind:'track', trackId, title})`
everywhere it's granted, never a raw `play()`). `drag` (E2 `DragPayload`) makes the row natively
`draggable` and dispatches both the tray→board and board→tray bridge pairs
(`PB_DND_*`/`PB_BOARD_DND_*`, see the event registry below).

**Per-surface grant state (current, not "slots exist" — see the table below for exact actions
per surface):**

| Surface | `lyrics`/`openLyrics` | `play` | `add` | `drag` |
|---|---|---|---|---|
| `LikedBoard.Row` | `lyrics?` (host-supplied) | — | — | ✅ `{kind:'external', copies:true}` (front #366) |
| `AlbumDetailView.Tracklist` — member (`AlbumDetail.StandardModal`) | `lyrics` | ✅ | ✅ | ✅ `enableDrag` (front #368) |
| `AlbumDetailView.Tracklist` — public (`AlbumOverlay`) | — (privacy boundary) | ✅ gated `isLoggedIn() && !unresolved` (front #367) | — (no bucket to add into) | — (no tray to drop onto) |
| `AlbumDetail.MemoWindow` (hand-rolled `TrackRow`, not via `Tracklist`) | `openLyrics?` (needs `spotify_id`) | — | — | ✅ unconditional (front #368) |

`—` is a real, considered omission, not an oversight: `add`/`play` never reached `LikedBoard`
because its rows are Spotify-library saved tracks, not bucket memberships, and nobody has asked
for them there; `AlbumOverlay` omits `add` for the same reason `add`'s own eighth-slice writeup
gives (a public visitor has no bucket to add into) but was deliberately granted `play` anyway,
since it already offered an album-level ▶ to any logged-in visitor and withholding the
track-level one had no semantic basis (see the RFC's eighth-slice decisions log entry).

Consumers: `AlbumDetail` tracklist (via the shared `AlbumDetailView`, Step 1), `AlbumDetail`'s
`MemoWindow` (via `openLyrics` — adopted Step 5, see below) + `LikedBoard` list rows (all three
inside the `SelfDashboard` island); `AlbumDetailView`'s `Tracklist` is also mounted **publicly**
by `AlbumOverlay` (grants `play` only, per the table above). A future track action on these
surfaces is wired in TrackRow once, not per surface.
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
| Review tracklist (vanilla, public) | `scripts/albumDetail.client.ts` (row render `:66,:71`; delegated handlers `:124-144`) | two buttons/row: `.lfq-tt-play` (▶) + `.lfq-tt-add` (＋) | ▶ → `playbackSession.replaceQueueAndPlay({kind:'track',trackId,title})` (`onRootClick`) | **no — excluded** |
| Pocket tray drawer members | `components/member/pocket/PocketTray.tsx` `onPlay` | React `<button onClick={onPlay}>` ▶ (list view) | `onPlay`→`playbackTargetFor`→`play()` (`@lib/spotifyPlayback`, direct call — this is the one surface that still plays a queue *position*, not a replace) | no (tray lyrics deferred — RFC OQ4, separate React root) |
| Member `AlbumDetail` tracklist (`StandardModal`) | `components/album/AlbumDetailView.tsx` `Tracklist` | `TrackRow` — 가사 (when `spotify_id` present) · ▶ · ＋ · draggable onto the Pocket tray | ▶ → `playbackSession.replaceQueueAndPlay({kind:'track', ...})` | **TrackRow** (`lyrics`+`play`+`add`+`drag`) |
| Public `AlbumOverlay` tracklist | `components/album/AlbumOverlay.tsx` → same `AlbumDetailView.tsx` `Tracklist` | `TrackRow` — ▶ only, gated `isLoggedIn() && !target.unresolved` | ▶ → `playbackSession.replaceQueueAndPlay({kind:'track', ...})` | **TrackRow** (`play` only — no `lyrics`/`add`/`drag`) |
| Member `AlbumDetail` **memo window** (bucket albums) | `components/member/AlbumDetail.tsx` `MemoWindow` | `TrackRow` with `openLyrics` — **the whole row is the button** (own `role="button"`, keyboard support) → `LyricsSheet`; also draggable onto the Pocket tray | none | **TrackRow** (`openLyrics?`+`drag`) — `openLyrics` adopted Step 5 second slice (front #354); `drag` added Step 5 ninth slice (front #368) |
| `LikedBoard` list rows | `components/member/LikedBoard.tsx` `Row` | `TrackRow` — identity → `onOpen` (detail, **member modal** — writable path, NOT the event); 가사 → lyrics viewer non-live; draggable onto the Pocket tray; ⋯ → 담기/평론쓰기 (surface-specific trailing) | none | **TrackRow** (`open`+`lyrics?`+`drag`) — `drag` added Step 5 seventh slice (front #366); card view NOT adopted (no lyrics affordance there) |
| Search track rows (public) | `components/search/SearchPage.tsx` (`SearchTrackRow`), `HeaderSearch` `ResultRow` (dropdown 트랙 rows) | **Step 3**: a track with a DB `albumId` opens the app-wide album overlay (`openTrackAlbum`); id-less (Spotify-only) rows stay static | none | no (bespoke → `openTrackAlbum`) |
| Artist top-tracks (public) | `components/artist/ArtistHub.tsx` `art-tt-open` | **Step 3**: `<button>` → `openTrackAlbum` (Music_TrackItem.album_id always set) | none | no (bespoke → `openTrackAlbum`) |
| Writer `RecommendedTracksBlock` / `ArtistDetail` | `components/writer/RecommendedTracksBlock.tsx:66-76`, `writer/ArtistDetail.tsx:43` | ★/☆ pick / `onPickTrack` (select-for-review) | none | no |

**Corrected 2026-08-06 — `requestPlayback` does not exist; it is `play()`** (`lib/spotifyPlayback.ts`,
`export async function play`). Renamed before this RFC started; this doc simply never caught up. It
is imported directly by **four** files today, not the "2" this doc previously claimed:
`components/member/pocket/PocketTray.tsx`, `components/member/NowPlaying.tsx`,
`components/member/lyrics/queueJump.ts`, and `lib/playback/session.ts` (which wraps it —
`replaceQueueAndPlay`/`playFrom`/`togglePlay` all call `play()` internally, never re-implement the
ladder). **`scripts/albumDetail.client.ts` no longer imports `play()`/`requestPlayback` at all** — its
▶ now goes through `playbackSession.replaceQueueAndPlay`, the same call every `TrackRow` `play` grant
uses, so **every per-track ▶ in the product — vanilla and React alike — is one call site**, which is
exactly the "a second play path by accident" risk `FEAT-playback-bucket-player` Step 6 named and this
RFC's Step 5 closed out. `PocketTray`'s own ▶ is the one deliberate exception: it plays a specific
**queue position** the member tapped, not a replace-the-queue-with-one-track ▶, so it calls `play()`
directly rather than through `replaceQueueAndPlay`.

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

### Canonical entity definitions — added `ARCH-entity-interaction-v2` Step 6, 2026-08-06

**Recorded here for the first time** — the RFC's own E1 explicitly deferred this transcription to
Step 6 rather than duplicate a definition that was still one step old (2026-08-04). This is the
canonical reference for "what identifies an album/track/artist, and what can be done with one" —
individual sections below (track-click, ownership) restate only the parts relevant to their own
scope; this table is where a new surface should start.

**Rule 0 — "canonical id" is about the *slot*, not a field name.** Three id shapes exist in the
codebase and only one is contract-legal in a DB-id slot:

| Shape | Legal? | Where seen |
|---|---|---|
| Nullable DB id | ✅ contract | the common case — `BoardAlbum.albumId` (`lib/buckets.ts`); a null id makes the entity **inert** (no open/add/drag), never a crash |
| Foreign-namespace id in a DB-id slot | ❌ prohibited | `releaseShared.tsx` `openReleased()`'s old resolve-miss fallback (fixed via `unresolved` flag, `ARCH-entity-interaction-domain-audit`, front #358) |
| Id resolved asynchronously per render | legal for **navigation**, illegal for **drag** | `NowPlaying.tsx` `resolveDbArtistId` / `getResolvedDbArtistId` — a drag source must hold the id synchronously at `dragstart` or not be draggable |

#### Album

| Facet | Definition | Where |
|---|---|---|
| Canonical id | `albums.id` (DB uuid), carried as `albumId`/`album_id` | `lib/entityEvents.ts` `OpenAlbumDetail.albumId`; `lib/buckets.ts` `BoardAlbum.albumId` |
| Null semantics | Nullable everywhere; null ⇒ no open/add/drag, renders as static content | `boardDnd.ts` library guard; `openTrackAlbum` early return |
| Canonical URL | **None, by decision** — addressed by id + open-event, never by path | `lib/entityLinks.ts` header comment |
| Open | `openAlbum({albumId, title, artist, cover, year})` → app-wide read-only `AlbumOverlay`; member **write** context → `onOpen(DetailTarget)` → `member/AlbumDetail` (two hosts, by decision) | `lib/entityEvents.ts`; `album/AlbumOverlay.tsx`; `member/AlbumDetail.tsx` |
| Actions | `open` · `add` 담기 · `drag` · `▶` (`playbackSession.replaceQueueAndPlay`, never a raw `play()`) · 평가/메모/가사 — **member host only** | `album/AlbumDetailView.tsx`; `member/AlbumDetail.tsx` |
| Drag payload | `{entity:'album', albumId, title?, artist?, cover?}` + `origin` | `lib/entityDrag.ts` |

#### Track

| Facet | Definition | Where |
|---|---|---|
| Canonical id | `tracks.id` (DB uuid). **`spotify_id` is a second namespace, not the id** — travels alongside it | `album/AlbumDetailView.tsx` tracklist; `member/LikedBoard.tsx` `LikedRowVM` |
| Null semantics | Null track id ⇒ no add/drag; opening degrades to the **album** path | `lib/entityEvents.ts` `openTrackAlbum` |
| Canonical URL | **None** — no page and no window of its own; canonical destination is its album's overlay | `lib/entityEvents.ts` `openTrackAlbum` |
| Open | `openTrackAlbum({albumId, albumTitle, artist, cover, year})` | 〃 |
| Actions | `lyrics?` (host-supplied, public hosts omit it) · `open?` · `openLyrics?` (mutually exclusive with `open`) · `play?` · `add?` · `drag?` — see "Track-click behavior" above for the current per-surface grant table | `shared/TrackRow.tsx` |
| Drag payload | `{entity:'track', trackId, albumId: string\|null, title?, artist?}` + `origin` | `lib/entityDrag.ts` |

#### Artist

| Facet | Definition | Where |
|---|---|---|
| Canonical id | `artists.id` (DB uuid), carried as `artistId`/`artist_id` | `lib/buckets.ts` `BoardAlbum.artistId` |
| Null semantics | Null ⇒ name renders as plain text, never a dead link | `lib/entityLinks.ts` `artistHref` |
| Canonical URL | **`/artist/{id}/`** — trailing-slash canonical; the only entity with a URL. Built only by `artistHref` | `lib/entityLinks.ts` |
| Open | Page navigation. Never an overlay — an artist has no window | 〃 |
| Actions | `open` (nav) · `drag`. No public 담기 — an artist enters a bucket by drag or Artist-bucket expansion | `boardDnd.ts` `routeAlbumDrop` artist branch |
| Drag payload | `{entity:'artist', artistId, name?, image?}` + `origin` | `lib/entityDrag.ts` |

The full drag-payload type (`DragOrigin`'s three kinds — `internal`/`library`/`external`), the
drop-target matrix (which of the six bucket kinds direct-adds/transforms/rejects each entity type),
and the `EntityRef`/`DragPayload` shape itself stay **RFC-only** (`ARCH-entity-interaction-v2.md`
E2/E3) rather than duplicated here — this doc's own convention (see "don't duplicate a full rule
set across files" in the prior stamp). Consult the RFC directly for those; this table exists so a
new surface can answer "what identifies X and what can X do" without opening it.

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
  `{lyrics?, open?, openLyrics?, play?, add?, drag?}`, all three of `play`/`add`/`drag` granted
  somewhere as of `ARCH-entity-interaction-v2` Step 5's ninth slice — see "Track-click behavior"
  above for the current per-surface grant table). Consumers: `AlbumDetailView.Tracklist`, shared by
  the member `AlbumDetail.StandardModal` (`lyrics`+`play`+`add`+`drag`) and the **public**
  `AlbumOverlay` (`play` only); `AlbumDetail.MemoWindow`'s own hand-rolled `TrackRow`
  (`openLyrics?`+`drag`); `LikedBoard.Row` list view (`open`+`lyrics?`+`drag`). Still hand-rolled:
  vanilla review tracklist
  (`scripts/albumDetail.client.ts:66,71` +
  delegated handlers `:124-144`, excluded by RFC), `search/atoms.tsx` `ResultRow`
  (shared by `SearchPage`/`HeaderSearch`/`CommandPalette`, `action` union navigate/button/static),
  `writer/RecommendedTracksBlock.tsx:66` (★ toggle), `writer/ArtistDetail.tsx:43` (`onPickTrack`),
  `LikedBoard` card view.
- **album card rendering** — **shared `components/shared/AlbumCard.tsx`** with
  `styles/album-card.css`; display model and declared capability contract are registered in
  "Album-card behavior" above. **Zero live consumers at Stage 3**: legacy surface renderers remain
  authoritative until their Stages 4-8 adapters migrate, and no bucket/memo/editorial state may
  enter the primitive.
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
whether it's actually single-owned. Descriptive inventory only — the rule itself (G3) and its
enforcement live in `ARCH-entity-interaction-domain-audit.md`'s Guardrails table; see that RFC
before adding a new event.

| Event | Declared in | Dispatched from | Listened by | Single-owned? |
|---|---|---|---|---|
| `ent:open-album` (`ENT_OPEN_ALBUM`) | `lib/entityEvents.ts` | ~15 public/member surfaces via `openAlbum()`/`openTrackAlbum()` | `AlbumOverlay.tsx` (layout-mounted) | yes |
| `ent:album-state-changed` (`ENT_ALBUM_STATE_CHANGED`) | `lib/entityEvents.ts` | `notifyAlbumStateChanged()` | `BucketBoard.tsx` | yes |
| `ent:open-live-lyrics` (`ENT_OPEN_LIVE_LYRICS`) | `lib/entityEvents.ts` | `openLiveLyrics()`, called from `PocketTray.tsx` | `SelfDashboard.tsx` | yes |
| `pb:toggle`, `pb:closed`, `pb:open-state`, `pb:dnd-start`/`end`, `pb:board-dnd-start`/`end`, `pb:board-drop` | `lib/pocketBuckit/events.ts` (8 constants) | `BucketBoard.tsx`, `TrackRow.tsx`, `PocketTray.tsx`, `PocketBuckit.tsx`; `AlbumCard.tsx` is a declared producer when `drag` is granted but has no live consumer yet | `BucketBoard.tsx`, `PocketBuckit.tsx`, `pocketBuckit/boardDnd.ts` | yes |
| `pb:add-track` (`PB_ADD_TRACK_EVENT`) | `lib/pocketBuckit/events.ts` | vanilla `scripts/albumDetail.client.ts` (imported constant) | `member/pocket/ReviewTrackAdder.tsx` (imported constant) | yes — centralized by `ARCH-entity-interaction-domain-audit` Step 2 |
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
| "What's currently playing" (track/queue/playing/device) | **should be** `lib/playback/session.ts` | **Updated 2026-08-06**: `NowPlaying.tsx`'s `useNowPlaying()` subscribes to `playbackSession` via `useSyncExternalStore` for track-identity+anchor (Step 3b, front #361); tier/mode/like/device/reconnect stay independently local by design. `LyricsViewer.tsx` sources its sync anchor from `playbackSession.currentSpotifyTrackId()` when the track matches (Step 3c, front #374, shipped 2026-08-06). `NowPlaying`'s mount-time double-read race (`BUG-28`) and its track-id-namespace mixing (`CHORE-nowplaying-trackid-namespace`) both fixed 2026-08-06 (front #376). Still open: `readLivePlayback()` itself is not single-flight/cached — a single `MYBLOG_PLAYBACK_CHANGED` still fans out to 3 uncoordinated HTTP reads (`session.ts`/`NowPlaying`/`LyricsViewer`), recorded but not attempted by any of the above fixes | **Fully consolidated for identity/anchor.** Step 3a (front #360) + Step 3b (front #361) + Step 3c (front #374) all shipped. `BUG-28` (follow-up inside 3b's own code) and the track-id fix also shipped (front #376). Only the single-flight/caching half of the target architecture remains unbuilt — not a correctness bug, an efficiency gap |
| "One tab owns playback" (write lease) | `lib/playback/ownership.ts` (localStorage lease + `BroadcastChannel`, challenge/response reclaim) | only gates `session.ts`'s writes — `NowPlaying`/`LyricsViewer` act locally regardless of lease state | correctly single-owned for what it covers; does not (and structurally can't yet) cover the other two trackers above |
| "My relationship to this album" (rating / candidate-mark / bucket memo / draft-review) | **no single owner — four independent silos, by design, not drift**: `AlbumRatingBlock` (rating/comment/candidate, `PUT /api/reviews/albums/{id}`, `album_reviews` row) / `ReviewCandidates` (a **third, separate** read of the same `review_candidate` flag via `GET /api/me/review-candidates`) / `MemoWindow`+`useBucketMemo` (`PATCH /api/buckets/{bucketId}/items/{itemId}`, `review_bucket_items.note`, bucket-scoped not album-scoped) / `WriterApp` (`POST/PUT /api/posts`, `posts` row + git commit) | — | three genuinely distinct commands over three DB rows (correct, keep separate — see reviews/memos audit); `ReviewCandidates`' redundant fetch of a flag `AlbumRatingBlock` already has is unassigned to any Step — noted here, not yet fixed |
| Manual-add-target eligibility (is bucket X a valid drop for a user-initiated add) | `lib/buckets.ts` `isManualAddTarget()` (added BUG-20, 2026-08-05) + `bucket_service.py` `_assert_manual_add_allowed()` (added 2026-08-05, external review item 5 follow-up) | — | single-owned per layer since 2026-08-05; frontend was 3 independent hardcodes + 1 omission before BUG-20, backend had **no** kind-based check at all (`_assert_item_type_allowed` keys on `type`, never `kind`) until this follow-up closed `add_item`/`expand_artist_source`/`expand_album_tracks`/`reorder` — a direct API call previously bypassed the frontend guard entirely |

## Modal / overlay registry — added `ARCH-entity-interaction-domain-audit` Step 1, 2026-08-05

Every `role="dialog"`-shaped component, which primitive it's built on, and — if not
`useDismissable` — whether that's a named, reasoned exception or an unreviewed gap. Descriptive
inventory only — the rule (G4) lives in `ARCH-entity-interaction-domain-audit.md`'s Guardrails
table; see that RFC before adding a new overlay.

| Component | Primitive | Notes |
|---|---|---|
| `AlbumOverlay`, `AlbumDetail`'s `StandardModal` + `MemoWindow`, `LyricsSheet`, `DockableLyricsSheet`, `LyricsViewer`, `PlaybackPanel`, `NowPlaying`, `AddArtistModal`, `AddAlbumModal`, `SettingsPanel`, `TodayPickHistory`, `TodaySongPicker`, `WriterApp`'s research drawer, `BucketBoard`'s create-bucket menu / delete-confirm modal / research panel / **`TrashDrawer`**, `OverviewDash`'s **`RecentAlbumsModal`** / **`RecentTracksModal`**, `ImportAnalysis`'s **`ItemDetailSlideover`**, `writer/**CommandPalette**`, `writer/**DraftsInbox**`, `genres/gm-shared`'s **`Peek`** | `useDismissable` | correct — ESC + focus trap/restore + the open-overlay stack (only the top-most layer acts). Bold names migrated `ARCH-entity-interaction-domain-audit` Step 4, 2026-08-05 |
| `ActionSheet` | own `useEffect` + `keydown` (ESC/scrim/✕), no focus trap | **named exception** — used solely inside `BucketBoard.tsx`; has its own test (`ActionSheet.test.tsx`) covering ESC/scrim/✕. Deliberately not migrated by Step 4 |
| `BucketPickerSheet` | own `useEffect` + `keydown` (ESC only, no focus trap) | ungapped exception — portaled, has real ESC handling, just not `useDismissable`'s trap/restore. Not in Step 4's migration list; still open |
| `AddToBucketMenu` | **none** | **gap, not a documented exception** — zero ESC handling of any kind (grep-verified). Not in Step 4's migration list; still open. **2026-08-06 audit**: also declares `role="dialog" aria-modal="true"` (`:214`) with no initial-focus, focus-trap, focus-restore, or scroll-lock implementation, and — because it never registers on `useDismissable`'s `openStack` while nested inside `AlbumDetail`'s `StandardModal` (shipped, `AlbumDetail.tsx:185-193`) — pressing Escape closes the album-detail modal underneath instead of the topmost bucket sheet. Full fix tracked as `ARCH-overlay-modal-isolation` Step 3 |

**Step 4 results (2026-08-05, front #357).** Migrated the seven gap rows this table previously
listed (`RecentAlbumsModal`/`RecentTracksModal`, `TrashDrawer`, `ItemDetailSlideover`,
`CommandPalette`, `DraftsInbox`, `gm-shared`'s `Peek`) into the `useDismissable` row above.
`TrashDrawer` **stays non-portaled** — OQ3 resolved (owner: unintentional, not a documented
exception) but Step 4's scope was the dismiss mechanism, not the mount method; the portal gap is
now the only thing left open on that component, tracked here rather than re-opened as a new OQ.
`AddToBucketMenu`/`BucketPickerSheet` were never in Step 4's migration list (RFC scope) and remain
open gaps for a future step.

Real-browser CDP verification caught a bug the interaction tests alone missed: `gm-shared`'s
`Peek` is never unmounted by `GenreMap.tsx` — it renders once with `nodeId=null` and flips
`nodeId` later — so a first attempt passing `useDismissable(true, ...)` (matching every other
migrated component, which genuinely mount-on-open) ran the hook's mount-time effect exactly once,
while `ref.current` was still `null`. ESC still worked (it reads `onClose` through a ref updated
every render, independent of effect timing) but autoFocus and the Tab-trap silently never fired —
a live regression against exactly what G4 exists to prevent. Fixed by keying `open` off `!!node`;
confirmed on prod (`www.ratemymusic.blog/genres/`, live genre data) after deploy. Worth restating
as a pattern: **`useDismissable(true, ...)` is only correct when the parent conditionally mounts
the component** (`{open && <X/>}`); an always-mounted, internally-node-gated component needs its
real open condition passed through.

Overlay primitives (unchanged from before this step): `.lf-scrim`/`.lf-slideover`
(`styles/member.css:193,203`), `.lf-modal-card`; z-tokens `--z-overlay:80`/`--z-panel:90`
(`styles/global.css:52-53`). `useDismissable` itself (`lib/useDismissable.ts`) now has a dedicated
`useDismissable.test.ts` (Step 4) — zero coverage before this despite 15+ consumers.

## Component-map impact template (paste into future RFCs)

```
Component-map impact — <RFC-ID> <title>
Verified: YYYY-MM-DD (re-verify if frontend changed since ARCH-frontend-component-map)
Routes touched:        /path (island) — public|authed
Track-click paths hit:  review-tracklist | pocket-tray | liked-board-onOpen | search-static | writer-pick | albumdetail-readonly
Play path:              none | play()/replaceQueueAndPlay (shared SDK layer, lib/spotifyPlayback.ts + lib/playback/session.ts) — entry surface:
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

### Filled — ARCH-entity-interaction-v2 (Steps 1–6, 2026-08-06)

```
Component-map impact — ARCH-entity-interaction-v2 (canonical entity contract + drag payload + action-slot rollout)
Verified: 2026-08-06
Routes touched:        none new — /members/ (AlbumDetail modal, LikedBoard), / and any ent:open-album caller (AlbumOverlay), all public|authed as before
Track-click paths hit:  albumdetail-readonly (member StandardModal — now lyrics+play+add+drag) ; albumdetail-readonly (public AlbumOverlay — now play) ; liked-board-onOpen (now +drag) ; memo window (own hand-rolled row — now openLyrics+drag)
Play path:              playbackSession.replaceQueueAndPlay({kind:'track', trackId, title}) — entry surfaces: member AlbumDetail StandardModal tracklist, public AlbumOverlay tracklist (gated isLoggedIn && !unresolved); same primitive the vanilla review page's per-track ▶ already used
Overlay changed:        none new; existing StandardModal/MemoWindow .scrim gained a drag-scoped pointer-events passthrough (drops to 'none' only for the PB_DND_START_EVENT..PB_DND_END_EVENT window, restored after) so a drag begun inside either modal can reach PocketTray underneath
State owner:            no new state store; drag payloads flow through the existing pb:dnd-*/pb:board-dnd-* window-event bridge (lib/entityDrag.ts memberRef() builds the ref)
Cross-island?:          yes — drag grants dispatch the same PB_DND_START_EVENT/PB_BOARD_DND_START_EVENT pair every existing drag source uses; no new event added
Cache touched:          none new (bucketStore, as every existing add/drag path already touches)
Duplicate it overlaps:  none — this RFC is the one that unified the three-shape drag inference (copy/fromLib/fromBucketId) into a single typed DragPayload (E2); no new duplication introduced
```
