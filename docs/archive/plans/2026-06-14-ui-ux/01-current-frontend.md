> **⚠️ HISTORICAL SNAPSHOT — 2026-06-14. SUPERSEDED. Read for IA/positioning rationale only, not as a current spec.**
> This is a frozen overnight UI/UX & IA planning snapshot. Since it was written: the home direction it recommends
> (two-lane WriterStrip + drag-reorder personalization) was **superseded by FEAT-home-redesign-v2** (Variant B
> "Refined Editorial", front #176, 2026-06-16, prod-live), which removed WriterStrip + drag/reorder. The public-bucket
> viewer shipped as **`/collection`** (singular; the `/collections` plural used here was a deferred proposal).
> `FEAT-home-redesign` is **done + archived** (`docs/archive/done/rfcs/FEAT-home-redesign.md`), not "draft".
> See `git log` + the FEAT-* RFCs for current state.

---

# 01 — Current Frontend Audit (myblog_front)

**Scope.** A complete, citation-backed audit of the `myblog_front` page/routing/IA layer, the component tree, the bucket feature, and what the home page surfaces today. Every code claim cites `file_path:line`; anything not verified against code is marked *speculation*.

**Relationship to prior art.** This builds on `docs/reviews/2026-06-13/01-code-audit-myblog_front.md` (the structural code audit). It does **not** redo that audit. The new angle here is the **UI/UX + information-architecture lens** and a **bucket-vs-magazine reality check** — i.e. what the user actually sees and navigates, where the "담기" (bucket) foundation surfaces (or fails to surface) to readers, and where the IA diverges from the editorial-publication goal. File paths below are relative to `/Users/park_hyun/myblog-workspace/myblog_front/` unless otherwise noted.

All routing is file-based: `output: 'static'`, `trailingSlash: 'always'`, `build.format: 'directory'` (`astro.config.ts:37-39`). There are **no `Astro.redirect` calls and no `redirects` config** anywhere (grep of `src/` + `astro.config.ts`). Every route is a static directory page or a prerendered dynamic page.

---

## Pages & routes

| Route | File:line | Role | Status | Problems |
|---|---|---|---|---|
| `/` | `src/pages/index.astro:1-43` | Home. Renders the interactive review browser (`ReviewsIndex` island, **default** variant) over all `blog` entries. SEO `forceTitle="buckit"`. | live | Home == a duplicate of `/reviews` minus the `variant="editorial"` flag (`index.astro:33` vs `reviews/index.astro:33`). Masthead `<h1>` literally reads "Reviews" (`index.astro:22`), so `/` presents itself as the reviews list, not an editorial home. Empty-state is a bare two-line message (`index.astro:27-30`). No BNM hero, no genre/by-the-numbers modules, no writer strip — the FEAT-home-redesign two-lane concept is not implemented; this is the pre-redesign state. |
| `/reviews` | `src/pages/reviews/index.astro:1-43` | Full review browser, `variant="editorial"` (oversized featured hero + 3-col grid). All filters/sort/search/BNM/year/view. | live | Near-identical to `/` (same `buildReviewCards`, same island, same empty-state, same "Reviews" masthead). The only delta is the `variant` prop. Two routes serve almost the same page. |
| `/blog/[slug]` | `src/pages/blog/[slug].astro:17-23` (`getStaticPaths`) | Single post / review article. `prerender = true`. Branches: `isReview` (album or rating present, `:32`) → "Lowfreq Article" layout (kicker, album hero, score card, drop-cap prose, track-by-track injected client-side); else → plain `ReviewHero` (`:78`). | live | Heavy single-file page (614 lines, large inline `<style>`/`<script>` blocks). Author 편집 link revealed client-side (`:599-603`). Tracklist depends on two client side-effect scripts hitting the music API (`:612-613`). |
| `/blog/category/[category]` | `src/pages/blog/category/[category].astro:10-14` | Per-category post list (title + stars + date). Categories derived from non-draft posts' `category` field. `prerender = true`. | live | Category set = whatever frontmatter `category` values exist; not a curated nav surface. **Not linked from the header** (see IA section) — only reachable via the legacy `constants.ts` HEADER (unused) or direct URL. |
| `/blog/category` | `src/pages/blog/category/index.astro:1-58` | "Categories" index — flat list of **all** posts (title + date), header says "Categories" but it lists posts, not categories. | partial / misleading | The `<h1 class="sr-only">Categories</h1>` (`:15`) and title "Categories" (`:13`) mislabel a flat all-posts list (`:9` `sortAsc(getCollection('blog'))` — no grouping, includes drafts since it doesn't filter `draft`). Not linked from the header. Likely vestigial. |
| `/genres` | `src/pages/genres/index.astro:1-33` | Public Genre Map (tier-0 Outliner). Server shell + `GenreMap` island (`client:load`). | live | Data is fetched **client-side** from `GET /api/genres/tree` (`src/lib/genres.ts:1-12`), not at build — so the page is empty/loading until the API responds, and is not statically pre-rendered with content. Owner inline-edit via `PUT /api/genres/{id}`. |
| `/profile` | `src/pages/profile.astro:1-77` | Owner "회원" hub — `ProfileApp` island fed all non-draft posts + computed stats (`:29-65`). Auth-guarded (`profile.guard.ts` redirects to login if `!isLoggedIn()`, `:76`). | live (owner-only) | Auth guard is **client-side only** (`profile.guard.ts`) — the static HTML/props still ship to anyone; guard just redirects after load. `MEMBER_IDENTITY` (`src/lib/member.ts:90`) is a hardcoded single identity. Carries member/library/Spotify/research components (`components/member/*`) — large surface for a single-author site. |
| `/write` | `src/pages/write.astro:1-13` | Writer/editor app (`WriterApp` island) on `write-layout.astro` (no site header/footer). Auth-guarded client-side (`write.guard.ts:1-12`). | live (owner-only) | Uses its own minimal layout (no `Header`/`Footer`, `write-layout.astro`). Client-only guard (same caveat as `/profile`). Excluded from sitemap (`astro.config.ts:46`). |
| `/drafts` | `src/pages/drafts.astro:1-550` | Owner post manager — tabs 초안/발행됨/보관함, edit/archive/restore/hard-delete via `apiFetch` to `/api/posts*`. `noIndex`. Auth-gated inside the script (`loadPosts` calls `goLogin` if `!isLoggedIn`, `:492-495`). | live (owner-only) | **Not linked anywhere in the header, footer, or any page** (no `href="/drafts"` in grep). Reachable only by typing the URL — discoverability gap for the owner's main content-management surface. 550-line single file with all logic inline. Excluded from sitemap. |
| `/admin/callback` | `src/pages/admin/callback.astro:1-23` | Cognito OAuth callback handler (code→token). Standalone HTML (no site layout, own styles), `noindex`. | live (infra) | Self-contained by design (renders before theme provider). This is the registered `PUBLIC_COGNITO_REDIRECT_URI` target (`src/lib/auth.ts:5,9`). Excluded from sitemap. |
| `/rss.xml` | `src/pages/rss.xml.ts:9-27` | RSS feed of non-draft posts, date-desc, linking `/blog/<slug>/`. `prerender = true`. | live | Fine. Declared in `<head>` of `layout.astro:18`. |
| `/blog` (index) | — **no file** (`src/pages/blog/` has only `[slug].astro` + `category/`) | — | **dead** | `constants.ts:25` HEADER still lists `{ title: 'Reviews', url: '/blog' }` and `{ title: 'Best New Music', url: '/blog/category/review' }`, but there is **no `/blog/index.astro`** → `/blog/` 404s. That `HEADER` constant is **not imported by the live header** (`header.astro` hardcodes its own `navLinks`, `:20-26`), so these are dead config, but any other consumer or a typed-in `/blog` URL breaks. |

*Speculation:* `/blog/category` and `/blog/category/[category]` appear to be pre-redesign leftovers (the live nav routes everything through `/reviews`); they are not in the header and overlap the reviews browser's own genre/category filtering. Not verified against an RFC — flagged as likely-vestigial, not confirmed dead.

---

## Component inventory

**Reuse-class legend.** `reusable` = imported by ≥2 areas; `area-shared` = reused within one area only; `one-off` = single caller; `duplicated` = near-identical logic exists elsewhere (flagged).

### MEMBER area (`src/components/member/`, `/profile` dashboard)

| Component | Location | Role | Reuse-class | Problems |
|---|---|---|---|---|
| `ProfileApp` | `member/ProfileApp.tsx:250` | Root island for `/profile`; owns tab/theme/layout/density/detail state. Mounted `client:load` in `pages/profile.astro:71` | one-off | Carries 3 prototype layout modes (sidebar/stacked/dashboard, `ProfileApp.tsx:316-333`) + density — heavy config surface for a single-author tool |
| `BucketBoard` | `member/BucketBoard.tsx:1243` | The 평론 버킷 board (the bucket feature). 1994 lines. See "Bucket implementation" | one-off | Single 2k-line file: DnD payload as module global `dnd` (`:48`), tree helpers, per-bucket view controls, trash, Spotify-library section, research badges all inline |
| `AddAlbumModal` | `member/AddAlbumModal.tsx:29` | "앨범 담기" search→pick modal; resolves DB album id back to caller | area-shared (BucketBoard + LibraryTab) | Album-only `useMusicSearch` wrapper; overlaps CommandPalette's result rendering (`qb-hit` vs `wr-row`) |
| `AlbumDetail` | `member/AlbumDetail.tsx:26` | Centered album modal, 3 modes (info/write/edit) driven by `DetailTarget.writable` + published-review match | one-off | Embeds a SECOND inline draft-authoring path (`WriteBody:220`, own `RatingInput:393`) that duplicates the real `/write` editor logic (savePost/updatePost, picks, score) |
| `LibraryTab` | `member/LibraryTab.tsx:501` | 라이브러리 tab: 들을 것 (real queue) + 평론한 앨범 + 최근 들은 (worker cache) | one-off | `fmtWhen` duplicated here (`:28`) and in `OverviewDash.tsx:24`; album-grid card markup repeated 3× |
| `OverviewDash` | `member/OverviewDash.tsx:650` | 개요 customizable row-board (pointer-DnD widget dashboard) | one-off | Full bespoke DnD engine (`RowsBoard:464`) separate from BucketBoard's HTML5-DnD and LibraryTab's list-DnD — **3rd independent drag system**; `AlbumColl`/`TrackColl` re-implement album cards again |
| `ReviewsTab` | `member/ReviewsTab.tsx:91` | 평론 tab: real reviews + drafts; archive via `DELETE /api/posts/{id}` | one-off | Local `ReviewCard` component name collides with `lib/reviews.ts` `ReviewCard` type and `ReviewsIndex`'s card |
| `StatsTab` | `member/StatsTab.tsx` | 통계 tab; genre/artist/activity are **sample** (`StatsTab.tsx:1-3`) | one-off | Sample-only; shows 샘플 badge |
| `OverviewDash` charts via `charts.tsx` | `member/charts.tsx` | `DistChart` (bar/donut/treemap/tag/list) | area-shared (Overview + Stats) | Fed only `DistItem` sample data today |
| `NowPlaying` | `member/NowPlaying.tsx` | Read-only worker-fed now-playing snapshot, 3 variants | area-shared (Overview) | Real data; not a player by design (D11) |
| `SpotifyIntegrationTab` | `member/SpotifyIntegrationTab.tsx` | 연동 status surface (no OAuth flow) | one-off | Status-only |
| `ResearchNote` | `member/ResearchNote.tsx:46` | Shared AI research-note panel (album-keyed store) | **reusable** (BucketBoard slide-over + WriterApp drawer) | Good reuse; but see `ResearchDoc` duplication below |
| `ui.tsx` primitives | `member/ui.tsx` | `Cover`, `AlbumArt:20`, `Stars:42`, `ScoreNum:59`, `Stat`, `SectionTitle:81`, `Seg`, `Avatar`, `Equalizer`, `Progress`, `BucketShortcut:177`, `SampleBadge` | **reusable** (whole member area) | `Stars` here is the member-area star renderer — one of **4 star implementations** (see Cross-cutting) |
| `library.api.ts` / `spotify.api.ts` | `member/*.api.ts` | Typed clients (to-listen, reviewed, recently-listened, now-playing, listened-albums, spotify-library) | area-shared | Fine |

### WRITER area (`src/components/writer/`, `/write`)

| Component | Location | Role | Reuse-class | Problems |
|---|---|---|---|---|
| `WriterApp` | `writer/WriterApp.tsx:141` (default export) | Root `/write` editor: subject pick, per-album draft slots, save/publish, split research view | one-off | 845 lines; has its OWN `fetchAlbumDetail` (`:51`) separate from `lib/albumDetail.ts` and CommandPalette's `selectAlbumByLookup` — **3 album-detail fetch shapes** |
| `CommandPalette` | `writer/CommandPalette.tsx:65` | ⌘K search palette (album/artist/track + artist drill-in) | one-off | Result-row markup (`PaletteRow:528`) duplicates AddAlbumModal's `qb-hit`; both wrap `useMusicSearch` |
| `SubjectHero` | `writer/SubjectHero.tsx:25` | Hero: cover + title + `DragRatingInput` + BNM toggle | one-off | Cover-fallback letter tile re-implemented (vs `ui.AlbumArt`) |
| `DragRatingInput` | `writer/DragRatingInput.tsx:16` | Drag-continuous rating strip (0.01 precision, writer) | area-shared (SubjectHero) | Near-identical to `AlbumDetail.RatingInput:393` (member-side pointer rating) — **2 drag-rating inputs** |
| `PartialStars` | `writer/PartialStars.tsx:15` | Writer-token star renderer (`.hdr-pstars`) | area-shared (writer) | Star renderer #3 (writer tokens) |
| `BodyArea` | `writer/BodyArea.tsx` | Auto-grow MDX textarea + formatting bubble | one-off | — |
| `RecommendedTracksBlock` | `writer/RecommendedTracksBlock.tsx` | ★/☆ best-track picker | one-off | Track-pick logic duplicated in `AlbumDetail.WriteBody` picks (`:335-367`) |
| `SettingsPanel` | `writer/SettingsPanel.tsx` | Publish panel (section/tags/date) | one-off | — |
| `PreviewView` | `writer/PreviewView.tsx` | Read-preview; inline-markdown renderer `renderInline:13` | one-off | Has its OWN markdown renderer, separate from `GenreMap.inlineMd`, `researchMarkdown`, `prose.astro` |
| `WriterChrome` | `writer/WriterChrome.tsx` | Top bar (status dot, save/publish) | one-off | — |
| `ArtistDetail` | `writer/ArtistDetail.tsx` | Artist drill-in panel inside palette | area-shared (CommandPalette) | — |
| `ResearchDoc` | `writer/ResearchDoc.tsx:31` | Split-view research **document** (right pane) | one-off | **Heavily duplicates `member/ResearchNote.tsx`** — same `useResearch`, same empty/queued/failed/refine/restart states, divergent markup (`:48-82` mirror `ResearchNote:57-87`) |
| `types.ts` / `autoGrow.ts` | `writer/*` | Shared writer types + hook | area-shared | — |

### REVIEWS area (`src/components/reviews/`, `/reviews` + home)

| Component | Location | Role | Reuse-class | Problems |
|---|---|---|---|---|
| `ReviewsIndex` | `reviews/ReviewsIndex.tsx:121` | `/reviews` browser island (genre/tag/sort/search/BNM/year/view, URL-synced); `variant='editorial'` for home | **reusable** (reviews page + home) | Has its OWN `Stars:89` (`.rev-stars`) + `Cover:104` + `fmtDate:73` — star renderer #4, date-fmt #N |

### GENRES area (`src/components/genres/`, `/genres`)

| Component | Location | Role | Reuse-class | Problems |
|---|---|---|---|---|
| `GenreMap` | `genres/GenreMap.tsx:345` (default export) | Tier-0 containment Outliner: share-bars, expand-defs, owner inline edit | one-off | Own mini-markdown (`inlineMd:26`, `Markdown:47`) — markdown renderer #N; tier-1 (sub-genres/ego) deferred (`:13`) |

### SHARED `.astro` (`src/components/`)

| Component | Location | Role | Reuse-class | Problems |
|---|---|---|---|---|
| `partial-stars.astro` | `components/partial-stars.astro` | Public read-page star renderer (`.partial-stars`, scoped CSS) | reusable (review-hero, prose) | Star renderer #1 — canonical for public pages |
| `review-hero.astro` | `components/review-hero.astro:1` | Blog-post review hero (cover + meta + big stars) | one-off (blog post layout) | Rating-normalization logic (`:20-27`) duplicates `lib/reviews.ts:120-131` and `profile.astro:34-46` |
| `prose.astro`, `aside.astro` | `components/*.astro` | MDX prose wrapper / pull-aside | reusable | — |
| `accent-select.astro`, `theme-provider.astro`, `theme-select.astro` | `components/*.astro` | Theme/accent controls | reusable | — |
| `header.astro`, `footer.astro`, `seo.astro`, `search-bar.astro`, `search.astro`, `icon.astro`, `link.astro`, `spacer.astro`, a11y/* | `components/*` | Chrome / nav / a11y | reusable | — |

### Cross-cutting duplication (explicit)

1. **Star rendering — 4 independent implementations** of the same partial-fill-stars visual, each with its own CSS class namespace and tokens:
   - `components/partial-stars.astro:20` (`.partial-stars`, public, canonical)
   - `writer/PartialStars.tsx:15` (`.hdr-pstars`, writer tokens)
   - `member/ui.tsx:42` `Stars` (`.lf-stars`, member dashboard)
   - `reviews/ReviewsIndex.tsx:89` `Stars` (`.rev-stars`, reviews page)
   All compute `pct = value/max*100` and render bg/fg `★★★★★` spans. Same math, 4 copies. (Verified: `partial-stars.astro:17`, `writer/PartialStars.tsx:17`, `member/ui.tsx:50`, `reviews/ReviewsIndex.tsx:94`.)

2. **Drag-rating input — 2 copies**: `writer/DragRatingInput.tsx:16` (0.01 precision) and `member/AlbumDetail.tsx:393` `RatingInput` (0.1 step). Same pointer-strip pattern.

3. **Album-detail fetch — 3 shapes**: `lib/albumDetail.ts:35` (cached, member modal), `writer/WriterApp.tsx:51`, `writer/CommandPalette.tsx:197` `selectAlbumByLookup`. All GET `/api/music/albums/{id}` and map to slightly different `AlbumDetail` types (`lib/albumDetail.ts:21` vs `writer/types.ts`).

4. **Album-card markup repeated** ~6×: `OverviewDash.AlbumColl` (3 view modes), `LibraryTab` (3 sections), `BucketBoard.AlbumChip:442`, `AddAlbumModal.qb-hit`, `CommandPalette.PaletteRow` — each re-renders cover + title + artist with `whiteSpace:nowrap/ellipsis`.

5. **Three drag systems**: BucketBoard (HTML5 native DnD + module-global `dnd`), OverviewDash (`RowsBoard` pointer-events geometry engine, `:464`), LibraryTab (simple HTML5 list reorder). No shared DnD abstraction.

6. **Draft-authoring duplicated**: full `/write` flow (`WriterApp`) AND a mini draft editor inside `AlbumDetail.WriteBody:220` (own textarea, rating, track-picks, savePost/updatePost). Two publish-adjacent code paths.

7. **Markdown renderers — 4+**: `researchMarkdown.tsx` (shared by ResearchNote/ResearchDoc), `GenreMap.inlineMd:26`, `PreviewView.renderInline:13`, `prose.astro`. Each hand-rolls `**bold**`/`*italic*`.

8. **Rating-normalization (0–10→0–5)** copied in `lib/reviews.ts:120-131`, `review-hero.astro:20-27`, `pages/profile.astro:34-46`.

9. **`fmtWhen`/`fmtDate`** duplicated across `OverviewDash.tsx:24`, `LibraryTab.tsx:28`, `ReviewsTab.tsx:20`, `ReviewsIndex.tsx:73`, `ResearchNote.tsx:29`, `ResearchDoc.tsx:15`.

---

## Bucket implementation — current state

**The bucket ("담기"/크레이트) feature is REAL, fully API-backed, and owner-only. It is the most developed surface in the app.** It is NOT a localStorage prototype (the `lib/member.ts` `bucketsInit` sample path is legacy/dead for the board itself — see "What is missing / partial").

### What exists today, precisely

- **Entry point**: `/profile` → "평론 버킷" tab (`ProfileApp.tsx:21,291`), rendering `BucketBoard` (`member/BucketBoard.tsx:1243`). `/profile` is auth-guarded by `scripts/profile.guard.ts` (referenced `profile.astro:78`).
- **Data model** (`lib/buckets.ts`):
  - `BoardBucket` (`buckets.ts:65`): `id, name, color (accent), isDone ("평론 완료" flag), kind ('review' | 'spotify_library'), researchMode ('off'|'all'|'selected'), albums[], children[]` — a **nested tree** (roots at top, descendants inlined as `children`).
  - `BoardAlbum` (`buckets.ts:22`): `itemId (review_bucket_items.id), albumId (DB album), title, artist, cover, year, alreadyReviewed, researchSelected, researchStatus, popularity, releaseDate, artistNames[], genres[]`.
- **Storage = backend API (Postgres via shared_db), not localStorage.** Full typed client in `lib/buckets.ts`, all through `apiFetch` (Bearer + 401 refresh) against `PUBLIC_BACKEND_API_URL` (`buckets.ts:12`):
  - `GET /api/buckets` → nested tree (`:139`)
  - `POST /api/buckets` create root (`:146`)
  - `PATCH /api/buckets/{id}` rename / color / research_mode (`:155,164,177`)
  - `PATCH /api/buckets/{id}/items/{itemId}` research_selected (`:189`)
  - `DELETE /api/buckets/{id}` cascade (`:198`)
  - `PUT /api/buckets/{id}/move` reparent+reposition, server-side cycle prevention (`:207`)
  - `POST /api/buckets/{id}/items` add album, 409 on dup (`:223`)
  - `DELETE /api/buckets/{bucketId}/items/{itemId}` (`:234`)
  - `PUT /api/buckets/reorder` bulk cross-bucket item reorder (`:244`)
- **localStorage is used only as SWR cache + transient client state**, never as source of truth:
  - `BUCKETS_KEY='lf_buckets'` seeds first paint then is overwritten by the GET (`BucketBoard.tsx:1248,1444`; `member.ts:129`).
  - `lf_crate_recent` (`:61`), `lf_crate_trash` (`:57`), `lf_bucket_views` per-bucket sort/group/filter (`:174`). Trash and per-bucket view state are **client-only** (not persisted server-side).
- **Capabilities implemented** (all in `BucketBoard.tsx`):
  - Nested buckets with drag-to-reorder, drag-to-nest, drag-to-unnest (red insertion-line gaps, `BucketDropGap:1108`), trash dock portaled to body (`TrashDock:1051`), recoverable album trash drawer (`TrashDrawer:1193`).
  - Per-bucket accent color picker (`BUCKET_COLORS:65`), rename inline, add album (`AddAlbumModal`), add sub-bucket.
  - Per-bucket view controls: sort (newest/oldest/popular), group (artist/genre), genre-filter chips — client-side, persisted per bucket (`FEAT-bucket-organize`, `:160-336`).
  - Rating chips on covers inside the single `is_done` "평론 완료" bucket, read from the member's own `reviews` prop (`ratings` map, `:1349`) — no extra fetch.
  - Per-cover AI research badge + auto-research mode (`CoverResearchBadge:413`, wired to `lib/research.ts`).
  - Optimistic mutations everywhere with `.catch(refresh)` rollback (BB-1 note `:1618`).
- **Spotify-library integration**: a special `kind='spotify_library'` bucket (`SLIB_KIND:55`) split out of the normal tree and rendered as its own section (`:1866`), with source/state badges (`SlibBadges:394`), 동기화 button that enqueues a worker reconcile and polls (`runLibrarySync:1471`) — no synchronous Spotify call (rule #9). 기존/preexisting albums are non-deletable.
- **Pinned "최근 들은 앨범" strip** (`RECENT_ID:52`, worker-fed `GET /api/library/recently-listened`) — drag a cover to copy it into a bucket.

### Public vs private boundary

**Owner-only / private.** Buckets live behind `/profile` (auth-guarded) and every read/write carries a Bearer token (`buckets.ts:6-7`). There is **no public-facing bucket surface** — no public page renders a bucket, and the GET itself is authed. A reader of the site cannot see the owner's buckets. This is the crux for the bucket-vs-magazine task: the "담기 → organize" foundation is presently **entirely backstage**; nothing of the bucket structure (collections, ordering, the owner's personal record) is exposed to readers as editorial output.

### What is missing / partial (honest)

1. **No public projection.** Buckets are invisible to readers. The personal-record/"organize into a personalized record" half of the premise has zero public IA today. (Bridging this — surfacing curated buckets as reader-facing collections/lists without leaking the raw board — is the open design space.)
2. **Trash + per-bucket views are client-only** (`lf_crate_trash`, `lf_bucket_views`) — not synced across devices; a different browser loses them. Server only stores manual `position`.
3. **Bucket→review linkage is loose/heuristic.** Rating chips correlate by `albumId` against the member's posts (`:1349`); the album-detail "write" path matches an existing draft **by title string** (`AlbumDetail.tsx:238`, "PostListItem has no album_ids"), not by id. Drafts started from a bucket cover can mis-link.
4. **Dead/legacy bucket sample path.** `lib/member.ts` still exports `getBucketsInit`/`bucketCount` reading `BUCKETS_KEY` from the **sample** `bucketsInit()` (`member.ts:124,138-155`, `member.sample.ts:124`). `OverviewDash` still calls `bucketCount()` for its `BucketShortcut` (`OverviewDash.tsx:449`) — so the overview's bucket count reads the SWR-cached real tree IF present, else falls back to sample data. This is a stale seam the real API-backed board has outgrown.
5. **Near-zero content degradation untested at the bucket level.** Empty-state strings exist ("비어 있음" `:1002`, "버킷 없음" `:1911`), but with posts reset to 0 (STAB-5) the rating chips and "평론한 앨범" correlations are all empty; the board is currently mostly the recent-strip + empty crates. *(Speculation: not verified against a live near-zero `/profile` render — static read only.)*
6. **Single hardcoded identity.** `MEMBER_IDENTITY` (`member.ts:90`) is `김저음`/`lowfreq`; multi-user is a non-goal (separate RFC). Buckets are implicitly one owner's.

**Load-bearing summary:** the bucket is a real, rich, owner-private organization tool backed by a full backend bucket/item/move/reorder API and a nested tree model. Its single biggest structural gap relative to the bucket-vs-magazine premise is that **none of it is reader-facing** — there is no public IA that turns "what the owner put in buckets" into editorial output.

---

## Current information architecture & navigation

**Global chrome** (`layout.astro:28-33`): `SkipNavLink` → `Header` → page `<slot>` → `Footer`. `write-layout.astro` is the exception — `/write` renders with **no header/footer** (`write-layout.astro:26-28`).

**Header** (`src/components/header.astro`) — a magazine masthead that collapses on scroll (`header.client.ts`, hysteresis ENTER=48/EXIT=16). Two zones:

- **Primary nav** (`header.astro:20-26`), hardcoded, three items: `Reviews → /reviews`, `Genres → /genres`, `Best New Music → /reviews?bnm=1`. (Note: "Best New Music" is a **filter on `/reviews`, not a route**, `:25`.) Rendered twice — centered in the expanded masthead (`:55-64`) and left-aligned in the compact bar (`:69-78`).
- **Persistent utilities, top-right** (`:35-49`): `Search` (Pagefind dialog trigger, ⌘K), and **auth-gated** `글쓰기 → /write`, avatar `→ /profile`, `Login`/`Logout`. These start `.hidden` and are toggled by `header.client.ts:11-25` via `isLoggedIn()` (write + profile + logout show only when logged in). The wordmark `buckit` links to `/` (`:53`, `:79`).

So the **entire public IA is 3 nav entries** (Reviews, Genres, BNM-filter) + search + the `/` wordmark. `/drafts` and `/blog/category*` are **not in the nav at all**. Owner-only routes (`/write`, `/profile`) appear in the utility cluster only when authenticated.

**Footer** (`src/components/footer.astro:7-17`) — minimal: a `ThemeSelect` + `AccentSelect` on a top border, and an empty right `<div>`. **No navigation links, no sitemap, no site identity/wordmark, no RSS link, no copyright.** It is purely a theme-control strip.

**Stale nav config**: `constants.ts:23-29` defines a `HEADER` object (`/blog`, `/blog/category/review`) that is **dead** — not imported by `header.astro`. It points at non-existent/un-nav'd routes.

**Cross-page linking**:

- `/` and `/reviews` cards/hero → `/blog/<slug>` (`ReviewsIndex.tsx:214,220,234,250,387,405`). Note these are emitted **without a trailing slash** (`/blog/${slug}`) while the site is `trailingSlash: 'always'` — relies on a redirect/normalization at the edge (not verified here; flagged).
- `/blog/[slug]` review → `/write?id=<postId>` (author edit, `:113`), and (when not a review) `ReviewHero`.
- `/blog/category` & `/blog/category/[category]` → `/blog/<slug>/` (with trailing slash, via `Link` component `link.astro:11-18`).
- `/drafts` rows → `/write?id=<id>` and `/write` (`drafts.astro:32,429`).
- `/genres`, `/profile` are island-driven; no static outbound editorial links.

**IA assessment.** The navigation is review-centric and flat. There is **no editorial framing layer** (no "about", no author/identity page beyond the auth-gated `/profile`, no curated category landing). The "bucket" concept has no public surface at all in the nav — buckets live inside the owner-only `/profile` (`components/member/BucketBoard.tsx`, `library.api.ts`), invisible to readers. Home and Reviews are near-duplicate destinations, so two of the three nav slots resolve to essentially the same browser.

---

## What the home surfaces today

`src/pages/index.astro` composition (`:12-41`):

1. Builds `reviews = buildReviewCards(await getCollection('blog'))` (`:12`).
2. Renders `<Layout>` → `.container` → a `<header class="rev-masthead"><h1 class="rev-title">Reviews</h1></header>` (`:21-23`) — the home page's visible H1 is literally "Reviews".
3. If `reviews.length === 0` → empty-state block: "아직 리뷰가 없습니다 / 첫 리뷰를 작성해 보세요." (`:27-30`). **This is the live state today** (posts reset to 0 in STAB-5).
4. Else → `<ReviewsIndex client:load reviews={reviews} />` (`:33`) — **default** variant (contrast `/reviews` which passes `variant="editorial"`, `reviews/index.astro:33`).
5. Footer: a small `buckit` wordmark (`:37-39`).

**Selection / sort logic — what `/` surfaces, precisely.**

`buildReviewCards` (`src/lib/reviews.ts:108-148`) is the data feed:

- **Filter** (`:110-114`): include an entry iff `!draft` **AND** (`rating != null` OR `musicReview != null` OR `albumIds.length > 0`). I.e. only album-review-ish posts; plain essays/columns are excluded from home.
- **Sort** (`:115`): `date` **descending** (newest first). This is the array order handed to the island.
- **Per-card normalization** (`:116-147`): canonical `rating` = top-level `rating` normalized to 0–5 (`scale===10 ? value/2 : value`, `:131`); album/artist from `musicReview` (`:135-136`); `genres` from `musicReview.genres` (empty if none — category is **not** used as a fake genre, `:137` + comment `:14-19`); `bestNew` from frontmatter (`:143`); `cover` falls back `albumCover → image → musicReview.cover.src` (`:144`); `excerpt` = `description` or stripped body (`:145`).

**Featured surfacing** — `selectFeatured` (`src/lib/reviews.ts:40-48`), invoked inside the island (`ReviewsIndex.tsx:196-199`, `selectFeatured(reviews)`), **only when no filter is narrowed** (`narrowed ? [] : selectFeatured(reviews)`, where `isNarrowed` = any genre/tag/q/bnm/year active, `:69-71`). Its ranking:

1. `bnm = reviews.filter(r => r.bestNew)` — all Best New Music, **in incoming order (= date-desc)**, placed first (`:41,47`).
2. If **no** BNM at all → fall back to the **latest 3** (`reviews.slice(0,3)`, `:42-43`).
3. Otherwise fill remaining slots from the **rest sorted by rating desc** (`(b.rating ?? -1) - (a.rating ?? -1)`, `:44-46`), then `slice(0,3)` (`:47`).

So the featured block is: *latest Best-New-Music first, topped up to 3 by highest-rated non-BNM; if no BNM, just the latest 3.* In the **default** variant the island renders this as `lead` + up to 2 `sides` (`ReviewsIndex.tsx:200-201,232-262`), and the lead **stays in the grid below too** (the comment at `:202-204` notes the default variant intentionally double-shows the lead; only the editorial variant drops it, `:205-206`).

**Below the featured block**, the island shows controls (search / sort `[date|score|artist]` / year / "BEST NEW만" toggle / grid-list view, `:264-324`), a **genre chip rail** (`allGenres`, first-seen order, `:326-344`), a **tag chip rail** (`allTags`, `:346-366`), then the grid/list of `filtered` cards. Default grid sort when untouched is again **date-desc** (`:190-191`), titled "최신 리뷰" (`:208`). Paged: initial 9, +6 per "더 보기" (`:29-30,427-432`).

**Net.** The home `/` does **not** sort/surface by anything editorial or bucket-derived. It surfaces **newest-first album reviews**, with a featured strip biased to **Best New Music then rating**, identical to `/reviews` except for the visual `variant`. There is no curated home, no "by the numbers", no genre-browse module, no writer strip, and no bucket presence — i.e. the FEAT-home-redesign two-lane home is **not built**; `/` is still the legacy reviews browser. At current zero-content it shows only the empty-state line.

---

## Problems summary (ranked by UX/IA impact)

1. **Home is not a home — it is a second copy of `/reviews`.** `/` renders the same island over the same data, differing only by the `variant` prop (`index.astro:33` vs `reviews/index.astro:33`); its visible H1 literally reads "Reviews" (`index.astro:22`). Two of three nav slots resolve to the same browser. No editorial framing, no curated entry. *(Highest IA impact — the editorial-publication goal has no front door.)*
2. **The bucket — the app's most developed feature and the stated foundation — has zero reader-facing surface.** Buckets are entirely behind auth-guarded `/profile` and an authed GET (`buckets.ts:6-7,139`); no public IA projects them (`BucketBoard.tsx:1243`). The "organize into a personalized record" half of the premise is invisible to readers.
3. **Owner's main content-management surface `/drafts` is undiscoverable.** Not linked from header, footer, or any page (no `href="/drafts"` anywhere); reachable only by typing the URL (`drafts.astro:1-550`). The owner has to memorize a URL to manage content.
4. **Footer carries no IA at all.** No nav, sitemap, identity/wordmark, RSS, or copyright — only theme controls (`footer.astro:7-17`). A magazine-style site has no editorial footer.
5. **Dead / misleading legacy routes and config.** `/blog/` 404s (no `blog/index.astro`) yet is still referenced by the dead `constants.ts:25` HEADER; `/blog/category` mislabels a flat all-posts list as "Categories" and includes drafts (`category/index.astro:9,13,15`); `/blog/category/*` is un-nav'd and overlaps the reviews browser's own filtering. *(Speculation that these are pre-redesign leftovers — flagged, not confirmed.)*
6. **`/genres` content is not pre-rendered** — fetched client-side from `GET /api/genres/tree` (`genres.ts:1-12`), so the page is empty/loading until the API responds and has no static content for crawlers.
7. **Trailing-slash mismatch on review links.** Cards emit `/blog/${slug}` with no trailing slash (`ReviewsIndex.tsx:214,220,…`) while the site is `trailingSlash:'always'` (`astro.config.ts:38`) — relies on unverified edge normalization.
8. **Client-only auth guards ship owner props to anyone.** `/profile` and `/write` guards run after load (`profile.guard.ts`, `write.guard.ts`); the static HTML/props are served to all, guard only redirects post-load. *(Security note, lower UX impact.)*
9. **Heavy duplication tax across the component tree** — 4 star renderers, 3 album-detail fetch shapes, 3 drag systems, 2 draft-authoring paths, 4+ markdown renderers, repeated rating-normalization and date-format (see Cross-cutting duplication). Raises the cost of any consistent visual/IA change. *(Maintainability, not directly user-visible.)*
10. **Near-zero-content degradation only partially handled.** Home/reviews have a one-line empty-state (`index.astro:27-30`); bucket board empty-strings exist (`BucketBoard.tsx:1002,1911`) but the live near-zero render is unverified. *(Speculation on the bucket side.)*

---

## IA diagram (text)

### Route structure

```
/  (buckit)                          [public]  ── home == /reviews (default variant); H1 "Reviews"
├── /reviews                         [public]  ── full browser (editorial variant)
│   └── /reviews?bnm=1               [public]  ── "Best New Music" = a FILTER, surfaced as a nav item
├── /genres                          [public]  ── tier-0 Outliner (client-fetched, not prerendered)
├── /blog/<slug>                     [public]  ── article (review vs plain branch)
├── /blog/category                   [partial] ── mislabeled "Categories" (flat all-posts, un-nav'd)
│   └── /blog/category/<category>    [public]  ── per-category list (un-nav'd)
├── /blog                            [DEAD]    ── no index file → 404; still in dead constants.ts HEADER
├── /rss.xml                         [public]  ── feed (in <head>)
│
├── /profile                         [owner]   ── ProfileApp hub  ← BUCKET lives here (private)
│     ├── 개요 (OverviewDash)
│     ├── 평론 버킷 (BucketBoard) ← the bucket feature, API-backed, owner-only
│     ├── 라이브러리 (LibraryTab)
│     ├── 평론 (ReviewsTab)
│     ├── 통계 (StatsTab, sample)
│     └── 연동 (SpotifyIntegrationTab)
├── /write                           [owner]   ── WriterApp; own layout, NO header/footer
├── /drafts                          [owner]   ── post manager; UNLINKED anywhere (URL-only)
└── /admin/callback                  [infra]   ── Cognito OAuth callback (standalone)

Public nav (header) = {Reviews, Genres, Best New Music(filter)} + Search + buckit wordmark→/
Owner utilities (header, auth-gated) = {글쓰기→/write, avatar→/profile, Logout}
Footer = theme + accent controls only (NO nav / identity / rss / copyright)
NOT in nav: /drafts, /blog/category, /blog/category/<category>
```

### Home (`/`) module composition (today)

```
Layout (Header + slot + Footer)
└── .container
    ├── <header class="rev-masthead"><h1>Reviews</h1></header>     ← not an editorial masthead
    └── reviews.length === 0 ?
        ├── EMPTY STATE  "아직 리뷰가 없습니다 / 첫 리뷰를 작성해 보세요."   ← LIVE today (0 posts)
        └── <ReviewsIndex variant="default">
            ├── Featured strip   = selectFeatured(reviews)         ← BNM-first, then rating; else latest 3
            │     └── lead + up to 2 sides  (lead ALSO repeats in grid below in default variant)
            ├── Controls    search · sort[date|score|artist] · year · "BEST NEW만" · grid/list
            ├── Genre chip rail     (allGenres, first-seen order)
            ├── Tag chip rail       (allTags)
            └── Card grid/list  "최신 리뷰"  (date-desc; 9 initial, +6 per "더 보기")

NOT present (FEAT-home-redesign two-lane concept, unbuilt):
  ✗ BNM editorial hero      ✗ Browse-by-genre module     ✗ By-the-numbers module
  ✗ auth-gated writer strip ✗ reader drag-personalization (홈 편집)   ✗ any bucket presence
```
