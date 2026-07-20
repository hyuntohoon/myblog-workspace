# RFC-ui-surface-unification: album/artist interaction rules + profile polish (areas 4·5·9)

- **Status**: done (2026-07-21 — Steps 1–5 all shipped + prod-smoked; Step 4 ws #673 / backend #127 / music #57 / front #299, Step 5 ws #676 / music #58 / front #300)
- **Owner**: 박지훈
- **Created**: 2026-07-18
- **Plan row**: `plan.md` → RFC-ui-surface-unification
- **Origin**: 2026-07-18 UI planning session, areas 4, 5, 9. Extends
  ARCH-entity-interaction-unify (done) — does not reinvent it. Pre-resolved owner decision
  **D4** (profile container 1200px).

---

## Goal

Every surface that shows an album or artist follows one written interaction rule (which click →
which modal/link, with which capabilities); the four measured dead spots are clickable; artist
names are links wherever an id exists **and** the missing-id chains are plumbed; the artist page
404-gap for post-build artists has a fallback; and the member profile stops jumping width
between tabs, with the 평가 list typography normalized onto the existing token scale.

## Non-goals

- Merging the two album modals into one (owner decision 8, 2026-07-18: **keep the dual system**,
  codify the rule instead).
- ArtistHub content-rule changes — honesty rules stay (owner decision 12): albums are the only
  rated unit, no artist score / similar-artists, followers/popularity as footnote. Layout-only
  refresh.
- Lyrics viewer internals (FEAT-lyrics-viewer-controls) and player internals
  (FEAT-member-player) — this RFC only supplies the id-plumbing those surfaces consume.
- Hybrid/SSR rendering migration for `/artist/[id]` (rejected as too structural; see Step 5).

## Current state (inventories measured 2026-07-18; scratchpad notes: area4/area5/area9 files)

**The written rule that already exists implicitly**: shared read-only path `openAlbum()` →
`AlbumOverlay`+`AlbumDetailView` (layout.astro; **already carries community rating + signed-in
write panel**, `AlbumDetailView.tsx:165`, lyrics only when host passes `onOpenLyrics`) vs member
writable path `SelfDashboard.openDetail(DetailTarget)` → `member/AlbumDetail.tsx` (modes
memo/info/edit).

**openAlbum adopters**: home strips ×4, releases calendar, SearchPage, HeaderSearch, ArtistHub
discography, MemberProfile 평가 (:250,:266), ReviewsTab (partial). **member-modal adopters**:
OverviewDash, ReviewsTab, BucketBoard (+ its own touch AlbumSheet), StatsTab/LikedBoard.

**Dead spots (album)**: public review page cover/title (~~`review-hero.astro:57`~~ **corrected
at Step 2**: the live album-review surface is the lfq layout in `pages/review/[slug].astro` —
`isReview` = albumIds>0 OR rating, so review-hero's `hasReview` branch is unreachable for posts
with album ids), pocket tray items (remove-only), NowPlaying album text.

**Artist links**: already broad (strips, releases, review byline, ADV block, PocketTray:543,
BucketBoard:639, search artist cards). **Plain text**: NowPlaying + LyricsViewer header + 오늘의
곡/픽 히스토리 + search album-card meta (all **lack an artist id** in their data chains — e.g.
`playback.api.ts:103-106` drops `artists[].id`; TodaySong rows are denormalized text by design
note), OverviewDash lines, LikedBoard (**has** `artistId`, `buckets.ts:52` — free win), 평가 list
(**renders no artist at all**).

**Artist page 404-gap**: `pages/artist/[id].astro` getStaticPaths = catalog ids fetched at build
(fallback: review-linked only) → artists synced after the last front deploy 404 until the next
push-to-main build.

**Profile (area 9)**: `MemberProfile.tsx:191` `maxWidth: dashActive ? 1200 : 760` → width jumps;
평가 tab is default AND the only 760 surface; visitors always 760. 평가 list is inline
(:234-282), bespoke: serif non-italic 16px title, 10px date, sans 13.5/1.5 body, raw 64px
`<img>`, no SectionTitle, **no artist line**. Dashboard tabs use 7 different album-title sizes,
4 star sizes, italic/non-italic split. Token scale `--text-*` exists (`global.css:82-94`) but
member components bypass it; no line-height tokens.

## Target state

1. **Interaction rule, written into this RFC and the code comments** (owner decision 8):
   *Public/read contexts open the shared overlay (`openAlbum`); dashboard work contexts
   (memo/edit) open the member modal; the overlay is the default for anything new.* Surface ×
   treatment table (below) is the enforcement checklist.
2. **Immediate fixes** (owner decision 9, all four): review-page album → `openAlbum`; pocket
   tray + NowPlaying albums → `openAlbum`; LikedBoard artists → `artistHref` links; 평가 list
   gains an artist line (field availability checked at implementation; add to response if absent
   — contract note below).
3. **Artist id plumbing** (owner decision 10: full scope): `playback.api.ts` →
   `LivePlayback` → `LyricsOpenTarget` carries `artists[{id,name}]`; NowPlaying + lyrics header
   render links; search album-card meta gains artist link where unified-search rows carry ids;
   오늘의 곡 rows get `artist_id` added to the daily_picks read model (**contract change** —
   openapi regen + merge procedure applies).
4. **404 fallback shell** (owner decision 11): static `/artist/404` → client shell that reads
   the id from `location`, fetches hero/albums at runtime, renders the hub (no SEO; the next
   build promotes it to a real page). CloudFront 404 routing checked against the `handler`
   function's `uri` rewrite.
5. **Profile polish** (D4 + owner decision 14): container fixed 1200; 평가 list inner reading
   column 680px; typography normalized to `--text-*` tokens + new `--leading-*` tokens;
   shared `AlbumArt`/`SectionTitle` replace bespoke pieces. The 8 measured inconsistencies are
   the acceptance checklist (scratchpad area9 note).

## Surface × treatment table (enforcement checklist)

| Surface | Album click | Artist render | Change |
|---|---|---|---|
| Home strips ×4 | openAlbum ✓ | linked (except 오늘의곡 — plumb id) | 오늘의곡 id |
| Releases | openAlbum ✓ | linked ✓ | — |
| Search page/header | openAlbum ✓ | artist cards ✓; album meta → link | meta link |
| Review page | **→ openAlbum** | linked ✓ | fix |
| Pocket tray | **→ openAlbum** | linked ✓ | fix |
| NowPlaying | openAlbum ✓ (#292 snapshot, #293 live) | linked ✓ (#293, resolvable-only) | done |
| Lyrics header | n/a | **→ link (plumb id)** | plumb |
| 평가 list | openAlbum ✓ | **→ add artist line** | fix |
| LikedBoard | member modal ✓ | **→ link (id exists)** | fix |
| OverviewDash/Bucket/Stats | member modal ✓ | text (low priority; link where id exists) | opportunistic |

## Steps

Steps 1–3 are front-only and independently mergeable; Step 4 is cross-repo (contract); Step 5 is
front-only. UI changes require real-browser click-through (DoD) and the frontend-design skill.

### Step 1 — profile width + 평가 typography (area 9) — ✅ SHIPPED (front #290, 2026-07-19)
`MemberProfile` container → 1200 always; 평가 list column 680; tokens + shared components;
artist line added if the profile payload already carries it (else deferred into Step 4).
**Verification**: CDP desktop + 390px, light/dark; tab switch shows no width jump.
**Shipped**: container 1200 fixed (no jump, measured 1200→1200), 680 column, SectionTitle +
AlbumArt adopted, title italic at `--text-md`, date `--text-2xs`, comment
`--text-base`/`--leading-normal`; new `--leading-{tight,snug,normal,relaxed}` tokens live in
prod CSS. OQ1 answered: payload has no artist field → artist line moved to Step 4.
Implementation note: leading tokens must live in a plain `:root` block, NOT `@theme` —
Tailwind v4 prunes @theme tokens with no var() reference (`--leading-relaxed` vanished from
the build) and `--leading-*` would override the `leading-*` utility namespace.

### Step 2 — album dead-spot fixes (review page, pocket tray, NowPlaying) — ✅ SHIPPED (front #292, 2026-07-19)
**Verification**: click-through each surface; overlay opens with correct data.
**Shipped**: review page (lfq hero cover + title, `astro:page-load`-bound; inventory correction
above), pocket tray (card-viewer album cards + list-viewer titles; artist nav untouched),
NowPlaying (snapshot `album_id` was ALREADY in `Backend_NowPlayingResponse` — worker-resolved —
so cover buttons + underlined album-text links shipped across banner/full/list + 최근 들은
앨범/최근 재생 rows now, ahead of the RFC's Step-4 assumption). The one-shot LIVE-read path
carries no album_id → stays plain text until the Step 4 playback plumb (commented at
`applyLive`). All surfaces CDP click-verified light+dark; prod marker = PocketBuckit chunk's
new `entityEvents` import. *(Superseded 2026-07-19: the live-path plumb shipped in
FEAT-member-player Step 3, front #293 — see the decisions log.)*

### Step 3 — artist quick links (LikedBoard + search album meta) + 404 fallback shell — ✅ SHIPPED (front #296, 2026-07-20; 404 shell only — both quick links deferred to Step 4, see below)
**Verification**: LikedBoard artist → hub; unknown-artist URL renders shell with live data.
**Shipped**: 404 fallback shell (owner decision 11). Measured first: S3 website config already
declares `error_document = error.html` (`infra/s3.tf`) but the build never shipped that key —
every unknown URL returned S3's raw XML error page. Fix is front-only: `src/pages/404.astro`
(Astro emits `dist/404.html`) + an `astro:build:done` hook mirroring it to `dist/error.html`.
**Zero CloudFront change**: the console `handler` viewer-request function passes
extension-less/trailing-slash URIs through unchanged (verified via `get-function`), and
`custom_error_response {404, ttl 0}` only caps caching; `/api/*` 404 bodies (by-spotify
poll flow) are untouched. `NotFoundShell` island: `/artist/{id}/` paths render the existing
`ArtistHub` island with live data (its hero/albums/top-tracks fetches were already runtime),
unknown ids fall through to ArtistHub's own not-found state; other paths get an in-system
generic 404 (mono kicker / serif headline / path echo / 홈·검색 links). Serves with HTTP 404 +
noIndex, excluded from sitemap; `sw.js` has no navigation fallback to shadow it.
**Scope corrections (measured 2026-07-20)**:
- OQ2 answered → search album meta link deferred to Step 4 (below).
- **Inventory correction — LikedBoard was NOT a free win**: the RFC's `buckets.ts:52 artistId`
  claim refers to `BucketItem.artistId`, which is non-null only for `itemType==='artist'`
  members and already linked (`BucketBoard.tsx:639`). LikedBoard rows are
  `Backend_SavedTrackItem` (artist = name string; `Backend_AlbumBrief` carries `artist_names`
  strings only) → **no artist id anywhere in the liked-tracks chain**. LikedBoard artist link
  moves to Step 4 as a contract addition alongside the 평가 artist line.
- OQ3 answered → no opportunistic OverviewDash/BucketBoard link possible (no unlinked
  artist render has an id).

### Step 4 — id plumbing (contract): 오늘의곡 `artist_id`, lyrics chain (`LyricsOpenTarget` + lyrics header), 평가 artist, search album meta `artist_id`, saved-tracks artist id (LikedBoard) — ✅ SHIPPED (workspace #673, backend #127, music #57, front #299 — 2026-07-21)
Music/backend response additions → openapi regen in service repo(s) → `tools/merge_openapi.py`
→ front `pnpm generate:types` (api.gen.ts commit). Workspace-first merge order per memory.
NB the NowPlaying leg of the playback plumb is already DONE (member-player #293, 2026-07-19):
`LivePlayback` carries `artists[{id,name}]` + `albumSpotifyId`; only the `LyricsOpenTarget` →
lyrics-header link remains from that chain.
**Verification**: openapi-verify CI green; lyrics header links live.
**Shipped**: NO DB migration — every leg resolves at read time from stored album ids.
- Backend (all Optional/additive): `DailyPickItem.artist_id` (batch
  `albums→album_artists` resolve per page, both today + history + write echoes),
  `MemberReviewResponse.artist_name/artist_id` (one batch resolve per profile
  feed), `SavedTrackItem.artist_id` (in-memory pick over the already-eager-loaded
  `album.artists`). Shared deterministic primary pick in
  `app/services/artist_primary.py` mirrors musicApi's BUG-19 ordering
  (popularity DESC NULLS LAST, name ASC) so both services present the same
  primary artist.
- Music: `AlbumItem.artist_id` via `get_primary_artist_map` now also selecting
  `Artist.id`; candidate rows (pre-catalog Spotify data) stay None.
- Front: lyrics chain plumbed (`LyricsOpenTarget`/`LiveLyrics.artists` →
  viewer header renders the exported `ArtistNames`, resolvable-only links);
  오늘의곡 tile + history artist links (album buttons and artist anchors
  restructured as siblings — no nested interactives); search album-card meta
  artist link (**HeaderSearch dropdown rows intentionally unchanged** —
  single-action keyboard rows, artists have their own group); LikedBoard
  **card view** artist link (primary-artist href under the denormalized
  multi-artist name string; **list view stays text** — shared `TrackRow.sub`
  is string-only); 평가 artist line (linked with id / plain with name only /
  omitted when absent).
- Verified: backend 550 pass, music 92 pass (one pre-existing localstack env
  failure reproduced on clean main, deselected), lint/astro-check 0; CDP
  click-through on local backend+music against prod DB (todays-pick history,
  search, LikedBoard = real rows; member profile + live playback via mocks —
  prod has no reviewed member yet), mobile 390 + light scheme, artist links
  land on the live ArtistHub.

### Step 5 — ArtistHub refresh + genre-map integration (rules intact; scope expanded 2026-07-21) — ✅ SHIPPED (workspace #676, music #58, front #300 — 2026-07-21)
Original scope: masthead/discography/top-tracks visual pass only. Owner-expanded
at the Step 5 go (2026-07-21 session):
1. **Visual pass** — typography normalized onto `--text-*`/`--leading-*` tokens,
   letter-tile font onto the site serif stack, empty-state polish. No layout
   re-architecture; honesty rules untouched.
2. **Discography sort toggle** — client-side 인기순 (default; server order) /
   최신순 / 제목순. (Measured: the server list is popularity DESC → release_date
   DESC; there was no user-facing control.)
3. **Artist genre chips → our taxonomy** (owner decision: replace, not
   link-in-place): `ArtistHero.catalog_genres [{label,slug}]` (music contract
   add) — high-confidence `album_genres` aggregated over the artist's catalog,
   most-tagged first. Chips link to the genre map; raw Spotify ko-KR `genres`
   remain the unlinked fallback for label-less artists. (Measured: the old
   chips were Spotify ko-KR strings — 545 distinct, 498 Korean, only ~13 match
   taxonomy labels — the one surface off the site's genre vocabulary.)
4. **Genre-map deep link** — `/genres/?g=<slug>` selects that node + opens its
   ego view (GenreMap previously had no deep link).
5. **Site-wide genre links** — display-only genre labels link to
   `/genres/?g=…` via a module-cached label→slug resolver (resolvable-only,
   the Step-4 ArtistNames idiom). Filter chips (LikedBoard facets, BucketBoard,
   GenrePicker, analysis charts) explicitly excluded — they keep local filter
   semantics. AlbumDetailView's artist-genre lines (ko vocabulary) stay text.
**Verification**: click-through incl. sort orders + chip → genre-map ego view +
deep-link URL direct-load; honesty-rule elements unchanged (stars only,
footnote metrics); mobile 390.
**Shipped**: all five legs as scoped. CDP-verified against prod DB (chips →
Pop ego view lands, three sort orders + default restore, `/genres/?g=pop`
direct load, BrowseGenres rows re-targeted `/reviews?genre=` → genre map,
LikedBoard card view upgraded 1,003 chips with analysis-panel/filter chips
untouched, mobile 390 dark + desktop light). CanonPage skipped (genre sits
inside the whole-card anchor); review-page build-time links covered by
astro-check + offline fallback (content collection empty — no live review
URLs yet). Prod smoke 19/19; prod `catalog_genres` live (Charli xcx →
[Pop, Electronic]); deployed ArtistHub chunk + artist CSS carry the step-5
markers.

## Open questions

1. **평가 list artist field** — ~~does the profile ratings payload already include artist?~~
   **Resolved at Step 1 (2026-07-19)**: `Backend_MemberReviewResponse` carries no artist field
   → 평가 artist line moves to Step 4 (contract addition alongside 오늘의곡 `artist_id`).
2. **Search album rows** — ~~do unified-search album items carry `artist_id` today?~~
   **Resolved at Step 3 (2026-07-20)**: `Music_AlbumItem` carries `artist_name` +
   `artist_spotify_id` but no DB `artist_id` (music `AlbumItem` schema + primary_map return
   name/spotify-id pairs) → meta link moves to Step 4. Note for Step 4 design: a contract
   `artist_id` add is the clean fix; a client-side `/artists/by-spotify/{id}` resolve-on-click
   exists as a no-contract alternative but loses real-href semantics.
3. **OverviewDash/BucketBoard artist linking** — ~~opportunistic or explicit step?~~
   **Resolved at Step 3 (2026-07-20)**: nothing to do — every artist render without a link is
   id-less (`artist_name`/`artist_names` strings); `itemType==='artist'` rows already link
   (`BucketBoard.tsx:639`). Any further linking rides the Step 4 contract adds.

## Decisions log

| Date | Decision | Step |
|------|----------|------|
| 2026-07-18 | D4 (owner, pre-session): container 1200px, comfortable inner measure | 1 |
| 2026-07-18 | Owner: dual-modal kept + rule codified; 4 immediate fixes; full id plumbing; 404 fallback shell; honesty rules stay; 680px + token normalization | all |
| 2026-07-19 | Owner: Status → in-progress approved; Step 1 shipped (front #290). OQ1: no artist field in profile payload → Step 4 | 1 |
| 2026-07-19 | Owner: Step 2 approved + shipped (front #292). Inventory corrected: review dead spot lives in `[slug].astro` lfq hero, not review-hero. NowPlaying snapshot already carries `album_id` → clickable now; live-read path deferred to Step 4 | 2 |
| 2026-07-20 | Owner (pre-session): Step 3 approved + shipped (front #296) as 404-shell-only. OQ2: no `artist_id` in search album rows → Step 4. OQ3: nothing opportunistic. Inventory corrected: LikedBoard has no artist id (`buckets.ts:52` is BucketItem, artist-type only) → Step 4 contract add. error.html was missing from the build — site-wide 404 fixed as a side effect, no CloudFront change | 3 |
| 2026-07-20 | **Cross-stream sync (consistency tidy)**: the NowPlaying live-path plumb SHIPPED 2026-07-19 in FEAT-member-player Step 3 (front #293) per the file-ownership decision — `LivePlayback` carries `artists[{id,name}]` + `albumSpotifyId`; NowPlaying renders real `artistHref` links via `@lib/spotifyCatalog` by-spotify pre-resolve (the OQ2 "no-contract alternative", resolvable-only so no dead clicks — and it KEEPS real-href semantics, contra the OQ2 note, because resolution happens at render not on click). Step 4 scope narrowed accordingly (NowPlaying leg removed; lyrics header + contract adds remain); surface table NowPlaying row marked done | 2, 4 |
| 2026-07-20 | Owner (session go): Step 4 approved + shipped. Contract shape decision: read-time primary-artist resolve (no DB migration, no denormalized artist_id columns); primary pick = musicApi's BUG-19 deterministic ordering, now shared verbatim by backend `artist_primary.py`. At the approval gate the owner kept **Step 5 in scope** (a same-session descope proposal was declined) — RFC stays open, next = Step 5 | 4 |
| 2026-07-21 | Owner (Step 5 go, scope expanded): visual pass + discography **sort toggle** + genre-map integration. Two gated choices: artist chips **replaced** by taxonomy-derived `catalog_genres` (over display-only linking of the Spotify ko strings — recommended and accepted), and the **site-wide** display-genre → `/genres/?g=` sweep rides Step 5 (over a follow-up PR). Filter chips excluded by design | 5 |
