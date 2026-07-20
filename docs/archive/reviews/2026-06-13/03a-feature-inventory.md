# 03a — Code-Based Feature Inventory (source of truth = code)

Date: 2026-06-13. Scope: every user-facing feature that **actually exists in code today**,
enumerated from frontend routes, React islands, served API route decorators, and worker
handlers. Docs/plan.md were NOT used as a source — only as a cross-check.

Method anchors: frontend pages = `myblog_front/src/pages/**`; islands =
`myblog_front/src/components/**`; backend routes = `@router.*` in `myblog_backend/app`
mounted in `app/main.py:87-95`; music routes mounted in `myblog_music/app/main.py:25-27`;
worker jobs = `myblog_worker/worker/handler.py:lambda_handler`.

---

## A. Frontend route surfaces (Astro pages)

`find myblog_front/src/pages -type f` →

| Route | File | Audience | Notes |
| --- | --- | --- | --- |
| `/` | `pages/index.astro:5,33` | reader | Interactive review browser (`ReviewsIndex` island, default variant). "Home is the interactive review browser (moved from /reviews)" `index.astro:10`. |
| `/reviews` | `pages/reviews/index.astro:5,33` | reader | Same `ReviewsIndex` island, `variant="editorial"` (hero + 3-col big-cover grid). |
| `/blog/[slug]` | `pages/blog/[slug].astro:15-23` | reader | Prerendered post/review detail. Two layouts: review (`isReview`, `[slug].astro:32`) vs plain `ReviewHero`. Album hero, partial-stars score, track-by-track list (client fetch), scroll progress, A−/A/A+ font-size toggle, author-only 편집 link. |
| `/blog/category` | `pages/blog/category/index.astro:9` | reader | Flat title/date list of all posts. |
| `/blog/category/[category]` | `pages/blog/category/[category].astro:10-16` | reader | Per-category post list w/ stars. Categories derived from MDX frontmatter at build (`getStaticPaths`), NOT a backend API. |
| `/genres` | `pages/genres/index.astro:5,23` | reader | **Spike/sample only.** `GenreMapTabs` renders 3 graph variants over **hardcoded** `@lib/genres-sample` seed — no backend, no `/api/genres` call (`index.astro:8-10` "public read-only graph over hardcoded seed data — no backend"). |
| `/write` | `pages/write.astro:4,9` | writer | `WriterApp` island. Auth-gated by `scripts/write.guard.ts` (`write.astro:12`). |
| `/drafts` | `pages/drafts.astro:7` | writer | "내 글" — 초안/발행됨/보관함 tabs, table, hard-delete confirm modal, toast. `noIndex`. Auth-gated by `scripts/profile.guard.ts` pattern. |
| `/profile` | `pages/profile.astro:5,72` | writer (owner) | `ProfileApp` member dashboard island. Auth-gated `profile.guard.ts` (`profile.astro:76`). |
| `/admin/callback` | `pages/admin/callback.astro:21` | auth | Cognito OAuth redirect handler (`scripts/callback.client.ts`), noindex. |
| `/rss.xml` | `pages/rss.xml.ts` | reader | RSS feed endpoint. |

Site-wide chrome (all pages via layout): editorial masthead that collapses on scroll
(`components/header.astro:49,65,87-89`, `is-scrolled` toggled by `header.client.ts`);
Pagefind static-content search modal (`components/search.astro:18,44`, integration
`utils.ts:81`); theme + accent selectors (`components/theme-select.astro`,
`accent-select.astro`); login/avatar buttons revealed when logged in
(`header.astro:35,39` `#write-link`/`#profile-link` `.hidden`).

---

## B. Writer / authoring features (islands + scripts)

Root: `components/writer/WriterApp.tsx` + `components/member/*` (profile is owner-only).

- **⌘K command palette music search** — `components/writer/CommandPalette.tsx:17-18,43-56`.
  Filter by 앨범/아티스트/트랙 (`CommandPalette.tsx:43-45`), keyboard nav, artist drill-in,
  paging. Engine = shared `lib/useMusicSearch.ts` (DB unified + Spotify-candidate paging,
  race/cooldown guards) `CommandPalette.tsx:61-63`. Picks resolve a DB album id then load
  `AlbumDetail` (`WriterApp.tsx:50` `fetch ${MUSIC}/api/music/albums/{id}`).
- **Review composition** — subject hero (album cover/artist/title), drag-rating input
  (`components/writer/DragRatingInput.tsx`), headline/dek, section + review tags, body
  textarea w/ auto-grow (`autoGrow.ts`), recommended-tracks block
  (`RecommendedTracksBlock.tsx`), Best New Music flag (`WriterApp.tsx:457` `subjectBestNew`),
  publish date.
- **Editor / Doc split view** — draggable, clamped, persisted pane ratio
  (`WriterApp.tsx:24-27` `SPLIT_KEY`, `SPLIT_MIN/MAX`); `ResearchDoc` pane shown beside the
  editor on wide screens (`WriterApp.tsx:701,769`).
- **Preview view** — `view: 'edit' | ... ` toggle; `PreviewView.tsx` (`WriterApp.tsx:251`).
- **Settings panel** — `SettingsPanel.tsx` (`WriterApp.tsx:800`).
- **Local draft autosave** — 30s periodic + tab-hide flush (`WriterApp.tsx:459,310`),
  localStorage draft slots (`scripts/write/draftStore.ts`, `WriterApp.tsx:18`).
- **Save / publish to Git** — `savePost`/`updatePost`/`publishToGit`
  (`WriterApp.tsx:16`); publish writes an MDX file to GitHub via backend
  `POST /api/publish` (`publish.py:45-97`, `publish_to_github`). Self-heal against dup-slug
  409 (`WriterApp.tsx:479,599`).
- **Draft management** — list/restore/hard-delete from `/drafts` (`pages/drafts.astro`,
  uses `GET /api/posts`, `PATCH /api/posts/{id}/restore`, `DELETE /api/posts/{id}`).
- **AI research note (writer-only)** — `components/member/ResearchNote.tsx:46` +
  `ResearchDoc.tsx`. Per-album note: 조사하기 trigger → queued/running live caption → done
  (collapsible) → failed + 다시 시도; refine-with-instruction never blanks prior note
  (`ResearchNote.tsx:8-11`). API client `lib/research.ts:3-4` →
  `GET/POST /api/research/albums/{id}` (`research.py:48-75`). Execution is **DB-state-driven**:
  POST only flips a `queued` row; a **$0 local poller** (`scripts/research_poller.py`, per
  memory `project-album-research-notes-status`) runs headless `claude -p` and writes the note
  back — there is no server-side AI call.

### Owner-only member dashboard (`/profile` → `ProfileApp.tsx:19-24,288-294`) tabs:
- **개요 (overview)** — `OverviewDash.tsx`; now-playing widget, charts, recent reviews,
  jump-to-bucket (`ProfileApp.tsx:289`).
- **평론 (reviews)** — `ReviewsTab.tsx`; the owner's own posts (album리뷰/트랙리뷰/칼럼 typed
  in `profile.astro:47`).
- **평론 버킷 (bucket)** — `BucketBoard.tsx` (`ProfileApp.tsx:291`); to-review queue board.
- **라이브러리 (library)** — `LibraryTab.tsx` (`ProfileApp.tsx:292`); listened/reviewed/
  to-listen lists, add-album modal (`AddAlbumModal.tsx`, same DB→Spotify-sync search core).
- **통계 (stats)** — `StatsTab.tsx`, `charts.tsx` (`ProfileApp.tsx:293`).
- **연동 (integration)** — `SpotifyIntegrationTab.tsx` (`ProfileApp.tsx:294`); Spotify
  connection status + library-sync trigger ("thin status surface, not an OAuth flow"
  `SpotifyIntegrationTab.tsx:3`).
- Dashboard prefs: layout (사이드바/에디토리얼/대시보드), density, now-playing style, chart
  style — persisted (`ProfileApp.tsx:34-42,46`).

---

## C. Reader / public discovery features

- **Review browser** (`/` and `/reviews`) — `ReviewsIndex.tsx`. Filters: genre, tag, sort
  (date/score/artist), free-text search, Best-New-Music toggle, year, grid/list view
  (`ReviewsIndex.tsx:19-27`). Every filter mirrored to URL querystring + back-button restore
  (`ReviewsIndex.tsx:10-13,32-66`). Featured row + load-more cursor (`PAGE=9`, `STEP=6`).
  Genre filter uses **real genres** (category fake removed Step 6, `ReviewsIndex.tsx:84-86`).
- **Review/post detail** (`/blog/[slug]`) — album hero, stars-only score, genres, record
  label, read-time kicker, BEST NEW MUSIC badge, drop-cap prose, accent pull-quotes, scroll
  progress bar, A−/A/A+ body-size toggle (persisted), and **track-by-track list** fetched
  client-side from the music API (`[slug].astro:147-173,606-614`,
  `scripts/albumDetail.fetch.client.ts`).
- **Category browse** — `/blog/category` + `/blog/category/[category]` (build-time from MDX
  frontmatter).
- **Genre map** (`/genres`) — interactive React-Flow-style graph, 3 design variants, era
  filter, detail panel — **but over hardcoded sample data, not live genres.**
- **Static content search** — Pagefind modal in header (`search.astro`).
- **RSS** — `/rss.xml`.
- **Post metrics (likes/comments)** — read-only batch via `POST /api/metrics/batch`
  (`metrics.py:11-20`); returns `{likes, comments}` per slug. (guess) Likely vestigial / not
  surfaced prominently — no write endpoint, comments feature was dropped per roadmap memory.

Note: most reader pages are **static prerendered Astro** (`/blog/[slug]` has
`prerender = true` `[slug].astro:15`); only the review-browser filtering, track-by-track
fetch, metrics, and search run client-side.

---

## D. API endpoints actually served

### Backend (`musicApi` Lambda is music; this is the posts/`ratemymusic-api` Lambda)
Mounted in `myblog_backend/app/main.py:87-95`. Decorators below are router-relative; prefix prepended.

**posts** (`/api/posts`, `routes/posts.py`)
- `GET    /api/posts` (`:28`) — list (drafts/published/archived)
- `POST   /api/posts` (`:55`) — create draft
- `GET    /api/posts/{post_id}` (`:99`)
- `PUT    /api/posts/{post_id}` (`:134`) — update
- `DELETE /api/posts/{post_id}` (`:153`) — hard delete
- `PATCH  /api/posts/{post_id}/restore` (`:199`)

**publish** (`/api/publish`, `routes/publish.py`)
- `POST   /api/publish` (`:45`) — render MDX + commit to GitHub repo (`publish_to_github`)

**buckets** (`/api/buckets`, `routes/buckets.py`)
- `GET    /api/buckets` (`:137`) — full tree + reviewed + research-status maps
- `GET    /api/buckets/spotify-library/state` (`:163`)
- `POST   /api/buckets/spotify-library/sync` (`:193`, 202) — enqueue only (rule #9)
- `POST   /api/buckets` (`:218`, 201) — create bucket
- `PATCH  /api/buckets/{bucket_id}` (`:241`)
- `DELETE /api/buckets/{bucket_id}` (`:288`, 204)
- `PUT    /api/buckets/reorder` (`:303`, 204)
- `PUT    /api/buckets/{bucket_id}/move` (`:333`)
- `POST   /api/buckets/{bucket_id}/items` (`:354`)
- `PATCH  /api/buckets/{bucket_id}/items/{item_id}` (`:388`)
- `DELETE /api/buckets/{bucket_id}/items/{item_id}` (`:419`, 204)

**library** (`/api/library`, `routes/library.py`)
- `GET    /api/library/to-listen` (`:66`)
- `GET    /api/library/reviewed` (`:75`)
- `GET    /api/library/recently-listened` (`:96`)
- `GET    /api/library/recent-tracks` (`:116`)
- `GET    /api/library/listened-albums` (`:141`)
- `GET    /api/library/now-playing` (`:168`)
- `GET    /api/library/spotify-connection` (`:191`)
- `PUT    /api/library/to-listen/reorder` (`:207`, 204)
- `POST   /api/library/to-listen` (`:221`)
- `DELETE /api/library/to-listen/{item_id}` (`:244`, 204)
- `POST   /api/library/refresh-recent` (`:259`, 202) — enqueue manual listening refresh

**research** (`/api/research`, `routes/research.py`)
- `GET    /api/research/albums/{album_id}` (`:48`) — latest note (404 = none)
- `POST   /api/research/albums/{album_id}` (`:61`, JWT) — trigger/restart/refine

**genres** (`/api/genres`, `routes/genres.py`)
- `GET    /api/genres/tree` (`:45`) — genre ontology tree
- `POST   /api/genres` (`:56`, 201, JWT)
- `PUT    /api/genres/{genre_id}` (`:81`, JWT)

**sections / tags / metrics** (writer metadata + reader metrics)
- `GET    /api/sections` (`routes/sections.py:13`) — review sections list
- `GET    /api/tags` (`routes/tags.py:13`) — review tags list
- `POST   /api/metrics/batch` (`routes/metrics.py:11`) — likes/comments per slug

**ops**
- `GET    /health` (`main.py:101`)
- `GET    /api/db/ping` (`main.py:106`)

### Music API (`musicApi` Lambda) — mounted `myblog_music/app/main.py:25-27`
**search** (`/api/music/search`, `routers/search.py`)
- `GET    /api/music/search/unified` (`:21`) — **DB-only** unified search (album/artist/track,
  per-bucket offsets, `explain` debug). Service boundary: DB-only.
- `GET    /api/music/search/candidates` (`:61`, JWT) — Spotify candidate search + **enqueues
  album sync to SQS** (the only path that touches Spotify; user-facing endpoint is DB-only).

**albums** (`/api/music/albums`, `routers/albums.py`)
- `GET    /api/music/albums/{album_id}` (`:10`)
- `GET    /api/music/albums/by-spotify/{spotify_album_id}` (`:17`)

**artists** (`/api/music/artists`, `routers/artists.py`)
- `GET    /api/music/artists/{artist_id}/albums` (`:19`)
- `GET    /api/music/artists/by-spotify/{spotify_id}` (`:36`)
- `GET    /api/music/artists/{artist_id}/top-tracks` (`:54`)
- `GET    /api/music/artists/{artist_id}` (`:66`)

> No `/api/music/genres*` route exists — the music service has no genres endpoint
> (`find ... grep genre` hits only mappers/services/schemas, not routers). Backend
> `/api/genres/tree` is the only genres read API, and the `/genres` page does not call it.

> No backend `categories` route exists — `grep categories app/main.py app/api/routes`
> returns nothing; categories are MDX-frontmatter, build-time only (CLAUDE.md / memory note
> that "categories unauthed write" refers to a historical concern; no route file present today).

---

## E. Worker background jobs (`myblog_worker/worker/handler.py:lambda_handler`)

Dispatch in `handler.py:103-164`:

1. **Spotify listening sync** — EventBridge 1h cron `{"job":"spotify_listening"}`
   (`handler.py:106-109,17-29`); also manual `{"job":"spotify_refresh"}` via SQS
   (`handler.py:136-138`, debounced). Updates recently-played + now-playing cache.
2. **Album-catalog ingest** — EventBridge daily cron `{"job":"album_ingest"}`
   (`handler.py:112-115,92-100`); discovers gate-passing new releases by catalog artists,
   enqueues them onto the same album-sync SQS.
3. **MusicBrainz alias generation** — EventBridge scheduled (`source=aws.events`)
   (`handler.py:118-121,83-89`); fills artist aliases. Runs off EventBridge, not SQS (outage
   must not block album sync — service boundary).
4. **Spotify saved-albums two-way reconcile** — SQS `{"job":"spotify_library_sync"}`
   (`handler.py:144-145,32-47`); real PUT/DELETE writes gated on the worker's OWN
   `SPOTIFY_LIBRARY_WRITES_ENABLED` setting (plan-only by default).
5. **Album sync (single / batch)** — SQS `spotify_album_id` or `album_ids[]`
   (`handler.py:150-156,50-80`); fetches album from Spotify → DB. Partial-batch failures
   reported via `batchItemFailures` (`handler.py:164`).

(Research-note execution is NOT in the worker — it's the local `claude -p` poller; the
dormant researchSQS/Lambda exists in infra but the backend never feeds it.)

---

## F. Notes / caveats

- `/genres` looks like a shipped reader feature but is a **hardcoded spike** — the real
  genre data (backfilled 982/982 albums per memory) is NOT yet wired to any reader page.
  The only live genre consumption is the `/reviews` genre filter chip (per-post genres from
  MDX) and the writer-side genre tree API.
- Two "review browser" routes (`/` and `/reviews`) render the **same** island with different
  variants — effectively one feature, two entry points.
- `POST /api/metrics/batch` returns likes/comments but there is no write path and the roadmap
  memory says comments/likes were dropped — treat as vestigial.
- Auth = Cognito Hosted UI OAuth (authorization-code + PKCE) `lib/auth.ts:92-103`; callback at
  `/admin/callback`. Mutating routes are Cognito-JWT at the API Gateway; reads ride the
  CloudFront edge_guard catch-all.
- All four service Lambdas deploy independently (CLAUDE.md). This inventory is feature-level,
  not deployment-level.
