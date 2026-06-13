# 05 — Feature Candidates (synthesis, NOT decisions)

Date: 2026-06-13. Input: `01-code-audit.md`, `02-db-review.md`, `03-feature-gaps.md`,
`04-market-research.md`, plus `docs/plan.md` (Backlog/Frozen) to avoid re-proposing decided work.

**These are options, not a roadmap.** Each candidate is presented with trade-offs for the owner to
pick from. Every candidate is checked against the in-flight/frozen exclusion list below and is
genuinely NOT already on the roadmap (or is a concretely different angle on a gap).

**Exclusion list (already in-flight or frozen — NOT re-proposed; may appear only as a dependency):**
AI editorial critique (FEAT-ai-editorial-critique, draft), album research notes
(FEAT-album-research-notes, all 5 steps done), genre system tier-0 (FEAT-genre-system, Steps 0-4
shipped), genre/artist distribution stats (FEAT-genre-artist-distribution, draft), multi-user
accounts (FEAT-multi-user-accounts, draft), genre sub-genres (FEAT-genre-subgenres, frozen),
new-release feed (FEAT-new-release-feed, frozen).

Each block: **what · audience · rationale (report→finding) · size (S/M/L) · risk · dependencies**.
Grouped loosely by primary audience: READER-discovery, WRITER-flow, then CODE/DB-health
(refactors/hygiene that unlock or de-risk features).

---

## A. Reader-discovery candidates

### 1. RSS feed — ⚠️ ALREADY SHIPPED (correction 2026-06-13); only an XS polish remains
- **CORRECTION:** This candidate was originally written as "build an Astro `/rss.xml` with
  `@astrojs/rss`." A main-loop verification found **that already exists and is wired**:
  `myblog_front/src/pages/rss.xml.ts` is a complete prerendered `@astrojs/rss` feed over the live
  `blog` collection (`getCollection('blog')`, filters `!draft`, links `/blog/<slug>/`), AND
  `myblog_front/src/layouts/layout.astro:18` already emits the autodiscovery tag
  `<link rel="alternate" type="application/rss+xml" title="buckit" href="/rss.xml" />`. The Task-3
  inventory even lists it (`03a-feature-inventory.md:30,111`); the Task-5 draft failed to reconcile
  against it. **So RSS is functionally done** — do NOT build it.
- **What actually remains (optional, XS):** (a) the feed/title/description use the placeholder
  `"buckit"` (`rss.xml.ts:16` description, `layout.astro:18` title) — set a real title/description;
  (b) per-item `description` falls back to `''` and there's no rating/album in the item body — enrich
  if desired; (c) there is **no human-visible "Subscribe / RSS" link** in the footer/nav (only the
  machine autodiscovery tag), so a reader can't click to it. None of this is a feature; it's polish.
- **Audience:** reader. **Size:** XS. **Risk:** none. **Dependencies:** none.
- **Net:** drop RSS from the "new feature" list; if anything, fold the placeholder-title +
  visible-subscribe-link polish into the next front housekeeping PR.

### 2. Year-end "Best Albums of [year]" list page
- **What:** A curated annual list page (`/best/[year]` or `/year-end/[year]`) the owner hand-orders,
  rendering the chosen reviews as a ranked editorial artifact.
- **Audience:** reader.
- **Rationale:** `04-market: the year-end list is "the single most universal artifact"` — present at
  every surviving outlet on both continents (Pitchfork "Best Albums of [year]", IZM "올해의 국내 앨범",
  Music Y "Best"), "produced once a year (negligible ongoing cost)... the most shareable
  credibility signal a small outlet can make" (04 §3 adopt #3). `03-feature-gaps: R4` notes the
  reader has no editorial landing beyond the flat review filter. Not on the roadmap.
- **Size:** S-M (a new Astro page + a small ordering mechanism — could start as hand-authored MDX,
  upgrade to a DB-backed ordered list later).
- **Risk:** Low-Med. Trivial as static MDX; the "where does the ordering live" decision (frontmatter
  flag vs a new `Post.extra` key vs a tiny editorial table) is the only design fork. No new backend
  strictly required for a static version.
- **Dependencies:** none for a static version; could reuse the `selectFeatured`/`buildReviewCards`
  logic in `lib/reviews.ts` (01 H2 names these). Pairs with #1.

### 3. Email subscribe (free tier, retention-only)
- **What:** A "subscribe by email" capture wired to a no/low-cost provider (Buttondown / Substack /
  Stibee), sending new reviews + the year-end list. Free tier only; no paid tier at launch.
- **Audience:** reader.
- **Rationale:** `04-market: email is "the most durable reader-retention channel"` and the on-ramp
  every durable solo independent uses (Hearing Things free weekly, First Floor free+paid) (04 §3
  adopt #5). Explicit CAUTION baked in: `04-market: free-only volunteer newsletter is THE
  documented failure mode` (stew! shut down 2026-03-15) — so this is retention, not a business
  model. Not on the roadmap.
- **Size:** S (embed a provider form) to M (self-hosted via SES + a list table — not recommended at
  $0-bias). Provider route is S.
- **Risk:** Med. Lowest-effort path is an external provider (a third-party dependency + a data-export
  concern, but $0). The $0-bias owner may dislike a SaaS dependency; an SES-based path is more work
  and more ops. Also a soft "is there even an audience yet" question — the market doc says start it
  as retention regardless.
- **Dependencies:** strongest if #1 (RSS) exists first (RSS→email bridges are turnkey). Independent
  otherwise.

### 4. Public artist page (`/artist/[id]`) over the existing DB-only artist API
- **What:** A public, unauthed reader page that renders an artist hero + discography + top-tracks +
  the artist's reviewed albums, linkable from any review.
- **Audience:** reader (and indirectly writer — reuses the writer `ArtistDetail` component).
- **Rationale:** `03-feature-gaps: R2 "No public artist hub/page — readers can't browse by artist at
  all" (M)` — the music service already serves a public DB-only artist hero+discography+top-tracks
  (`artists.py:19-78`, all unauthed), the read page already carries `artistIds` (`[slug].astro:151`)
  but links nowhere, and the roadmap memory states "artist = hub page + search" as a *decided*
  feature that is nonetheless unbuilt. NOTE: this is a decided-but-unbuilt capability, not a frozen
  RFC — distinct from FEAT-multi-user-accounts (no user model needed). Calling it out explicitly so
  it isn't conflated with the excluded multi-user work.
- **Size:** M (one new Astro page consuming existing endpoints; the writer `ArtistDetail.tsx` is
  "mostly reusable" per 03 R2).
- **Risk:** Low-Med. Data + API are done and unauthed; the risk is component reuse (the writer panel
  has drill-in/picker affordances a public page shouldn't show). Confirm 03 openQuestion #3 — is
  this implicitly blocked on FEAT-multi-user, or shippable solo now?
- **Dependencies:** none technical (API shipped). Unblocks #5 cross-links and W2/W3 sharing.

### 5. Reader cross-links: review → /genres and review → artist page
- **What:** Add links from a review (and the `/reviews` filter) out to the real `/genres` map and to
  the per-artist page, turning the flat review list into a navigable discovery graph.
- **Audience:** reader.
- **Rationale:** `03-feature-gaps: R4 "no cross-link from a review to the /genres map or to an
  artist" (L)` — "the reader's discovery graph is shallow: review → (filter) → review" with no
  genre-page or artist-page hop. The market doc frames discovery as the core reader value
  (`04-market: discovery = recurring rails + cross-links, not a score database`). Not on the roadmap.
- **Size:** S (add `href`s once the destinations exist).
- **Risk:** Low. Pure connective tissue.
- **Dependencies:** **blocked on** a real `/genres` page (FEAT-genre-system Step 6 — excluded as
  in-flight, named here only as a dependency) **and** #4 (artist page) existing first. Cheap once
  both land.

### 6. Static client-side search over the review archive
- **What:** A Pagefind/Fuse-style static search index built at Astro build time over published
  reviews (title/album/artist/body), surfaced as a `/search` box — distinct from the existing
  music-catalog autocomplete (which searches the Spotify-derived catalog, not the owner's prose).
- **Audience:** reader.
- **Rationale:** `04-market: "Search + tags over the review archive" is a baseline reader feature
  both Korean webzines ship` (IZM + Music Y both expose it; 04 §3 adopt #6), "makes a growing solo
  archive navigable without any backend work." Today's only search is the *catalog* autocomplete
  (`useMusicSearch`/`searchBarDb`), not a *review-archive* search — 03 confirms reader discovery is
  filter-only. Genuinely distinct from the catalog search and not on the roadmap.
- **Size:** S-M (Pagefind integrates with Astro at build; near-zero runtime cost). At 1 published
  post today (02 §2: `posts` = 1 row) the value is latent until the archive grows.
- **Risk:** Low. Build-time index, no backend, no DB. Main caveat: low value until there are enough
  reviews to search (02 confirms editorial scale is ~0 — see #2/year-end note too).
- **Dependencies:** none. Could share a tag taxonomy with #2.

### 7. Tag/section landing pages over the review archive
- **What:** Static per-tag and per-section (and eventually per-genre) landing pages
  (`/tag/[tag]`, `/section/[section]`) listing every review under that facet.
- **Audience:** reader.
- **Rationale:** `04-market §3 adopt #6: "search + tags over the review archive"` — content-collection
  tag pages are explicitly named as a low-cost reader feature ("Astro static... tag pages... no
  backend work"). The schema already has a `tags`/`post_tags` surface (02 §1 lists both; 01 M17
  notes `Tag`+`Post.tags` exist in shared_db). Distinct from the genre-system `/reviews` filter
  (that's an in-page filter; these are crawlable landing pages with their own URLs). Not on roadmap.
- **Size:** S (Astro dynamic routes over the content collection).
- **Risk:** Low. Static generation. Caveat: overlaps conceptually with the genre `/reviews` filter —
  scope it to *tag/section* facets to avoid stepping on the excluded genre work.
- **Dependencies:** none; complements #1/#6 (shared taxonomy). Genre landing pages would depend on
  the excluded FEAT-genre-system Step 6.

### 8. Lightweight "Album of the Month / Essential" curated rail
- **What:** A recurring short-blurb roundup surface (e.g. a monthly "이 달의 앨범" card or a small
  "Essential" list) anchored to the existing review-bucket/board, giving the homepage a freshness
  pulse without daily full reviews.
- **Audience:** reader.
- **Rationale:** `04-market §3 adopt #4: "Lightweight curated rails"` — "discovery at every outlet
  runs on cadence rails, not a ratings leaderboard; a weekly/monthly short-blurb roundup is far
  cheaper than daily full reviews" and the doc explicitly notes "the blog already has a
  review-bucket/board surface to anchor this." `04 §3 NOT-adopt #1` rules out *daily* cadence, so
  this is the monthly-light version. Not on the roadmap.
- **Size:** M (a new homepage card + a way to mark "this month's pick" — could reuse the bucket-board
  data model rather than new schema).
- **Risk:** Med. The design fork is "where does the pick live" (a bucket flag vs a new editorial
  field). Owner-cadence dependent — adds a small recurring authoring obligation (the market doc's
  whole point is keeping that obligation *light*).
- **Dependencies:** leans on the existing review-bucket/board surface; no new RFC-level deps.

---

## B. Writer-flow candidates

### 9. Artist drill-in completion: load-more + count display + album-type filter
- **What:** Finish the writer artist drill-in — a "전체 보기 / load-more" toggle on the 24-album
  discography, render the already-plumbed `album_count`/`track_count` ("24 of N"), and add an
  album-type filter (정규/EP/싱글).
- **Audience:** writer.
- **Rationale:** `03-feature-gaps: W2/W3/A "Artist drill-in toggle unfinished" (M)` — the discography
  is a fixed unpageable 24 (`CommandPalette.tsx:323`), `album_count`/`track_count` are computed and
  cross the wire (`api.gen.ts:1420,1446`) but have **zero render-site** in front, and the repo+route
  already support `offset` (`album_repo.py:216-227`, `artists.py:23`). This is the named BUG-19
  follow-up; backend paging already exists, so it's pure frontend completion. Not on the roadmap as
  its own row.
- **Size:** S-M (frontend load-more + a count label; album-type filter needs one music-service query
  param `?album_type=` per 03 W3, making it M if the filter is included).
- **Risk:** Low. Backend mostly done. Risk is the album-type filter needing a small additive music
  endpoint change (contract regen) — split it: load-more+counts is S and front-only, the filter is
  the M part.
- **Dependencies:** none for load-more/counts. The album-type filter touches the music service
  (`/artists/{id}/albums`) → openapi regen. Shares the `ArtistDetail` component with candidate #4.

### 10. `apiFetch` request timeout (hung-Lambda safety net)
- **What:** Add an AbortController timeout (~10-15s) to the live `apiFetch` wrapper so a cold/hung
  Lambda+Neon resume can't leave an island stuck in its loading skeleton forever.
- **Audience:** both (writer flows + reader pages both call through `apiFetch`).
- **Rationale:** `01-code-audit: L8 "apiFetch has no request timeout; the dead safeFetch does"` — the
  actually-used wrapper (`api.ts:65-88`) has no timeout while the dead `safeFetch` carries an 8s
  AbortController; `spotify.api.ts`/`buckets.ts`/`research.ts` all rely on `apiFetch`
  returning/rejecting to exit loading. `02-db-review` corroborates the trigger: Neon
  suspends/resumes (compute was up only 43 min), so cold-start hangs are a real path. Not on roadmap.
- **Size:** S (one wrapper change + return null on abort so existing `!res` branches handle it).
- **Risk:** Low. Pure robustness. Slight risk of a too-aggressive timeout firing on a legitimate cold
  start — pick the ceiling with Neon resume latency in mind.
- **Dependencies:** none. Could fold into a broader front-hardening pass with #11.

### 11. Front test harness (vitest) for the untested writer logic
- **What:** Add a vitest runner + a thin unit suite covering the pure logic with documented
  regression history: `lib/reviews.ts` rating normalization, `lib/member.ts` stats, and the
  `useMusicSearch` sequence-race guard. Wire `pnpm test` into the existing CI check job.
- **Audience:** writer (protects the writer-facing search + review surfaces) / dev-health.
- **Rationale:** `01-code-audit: H2 "No test runner or test suite at all (front)"` — zero test infra,
  yet documented regression history (CP-1/CP-4 search races, 0-10→0-5 rating halving) lives in
  exactly the trivially-unit-testable pure logic; "converts a recurring class of 'lint+astro-check
  pass but the logic regressed' incidents into caught-at-PR failures." This is an enabler: it
  de-risks every future writer-flow change (incl. #9). Not on the roadmap.
- **Size:** M (add runner + harness + a handful of tests + CI wiring).
- **Risk:** Low. Additive, no runtime impact. The only cost is the upfront harness setup; ongoing it
  pays for itself.
- **Dependencies:** none. Unlocks safer iteration on #9 and any front feature.

---

## C. Code-health / DB-hygiene candidates (refactors that de-risk or unlock features)

### 12. Unify the two music-search cores into one shared module
- **What:** Migrate the homepage search bar (`searchBarDb.client.ts`, 509 lines) onto the same
  framework-agnostic fetch+map+race-guard core the writer `useMusicSearch` (379 lines) uses,
  collapsing two parallel implementations into one.
- **Audience:** both (homepage reader search + writer CommandPalette) / dev-health.
- **Rationale:** `01-code-audit: H4 "Music-search core extracted for the writer but homepage search
  bar never migrated"` — the core was extracted "so CommandPalette can share one search core instead
  of hand-rolling near-identical fetch + race-guard + cooldown twice," but the homepage still
  hand-rolls all of it in parallel (duplicated mappers, race guards, cooldowns; `dedupeBySpotify`
  has no homepage equivalent). Also `01 M9` (one endpoint, two auth wrappers) folds in here.
  Unifying de-risks any future search feature (e.g. #6 archive search reuse, #4 artist links).
  Not on the roadmap.
- **Size:** M (extract framework-agnostic helpers since `searchBarDb` is a non-React `.client.ts`
  island; or at minimum port `dedupeBySpotify` to the homepage path).
- **Risk:** Med. Touches the reader-facing homepage search — needs a real-DOM click-through (memory:
  front interaction QA). Race-guard semantics must survive the migration intact (CP-1/CP-4 history).
- **Dependencies:** lands cleanly *after* #11 (vitest) so the race-guard has a test. Enables #6.

### 13. Derive the album-detail type from the generated contract + single fetcher
- **What:** Replace the 4 hand-rolled album-detail shapes (+ 3 duplicate `fetchAlbumDetail`
  implementations) with one `AlbumDetail = components['schemas']['Music_AlbumDetail']` and one
  cached+deduped fetcher.
- **Audience:** writer / dev-health.
- **Rationale:** `01-code-audit: H3 "Album-detail response shape hand-rolled in 4 places; generated
  Music_AlbumDetail exists"` — the hand-typed consumers "won't fail the api.gen.ts sync gate on a
  music-API field change," so this duplication *defeats the CI contract gate the workspace already
  invested in*. Restoring that safety net protects every writer surface that renders album detail
  (CommandPalette, WriterApp). Not on the roadmap.
- **Size:** S-M (derive one type, export one fetcher, update ~4 call sites).
- **Risk:** Low. Type-level + a fetcher dedupe; the generated type already exists at
  `api.gen.ts:1347`. Small risk of a field-name mismatch surfacing real drift (which is the point).
- **Dependencies:** none. Pairs with #12 (both are front search/detail consolidation).

### 14. Worker fetch/write split + per-tick wall-clock budget (Spotify/MusicBrainz hot paths)
- **What:** Refactor the worker's album-sync, alias-fill, and album-ingest paths to a
  fetch-all-then-write shape with a per-tick wall-clock budget, so a Neon transaction is never held
  open across seconds of Spotify HTTP and a slow upstream can't blow the 120s Lambda ceiling.
- **Audience:** dev-health / reliability (indirectly protects every reader/writer path that depends
  on a fresh catalog).
- **Rationale:** `01-code-audit: H5 "Spotify HTTP calls run inside the open DB transaction" + H6
  "~20 sequential rate-limited MusicBrainz calls/tick, no wall-clock guard" + M11 "30 sequential
  per-artist Spotify fetches, no time guard"` — the audit's #1 cross-cutting theme and its #2
  top-impact bundle: "one architectural pattern... retires two H's and one M at once, on the exact
  paths most exposed to an upstream slowdown given the account-wide Lambda concurrency-10 /
  tight-Neon-pool constraint." Not on the roadmap.
- **Size:** M (one pattern applied across 3 paths; amortized across the findings).
- **Risk:** Med. Touches the live catalog-sync write path (the hottest writer of the DB per 02 §3
  index-scan evidence) — needs the worker's real-engine integration test (memory: SA
  session-lifecycle mock-blind) because connection-boundary changes are exactly the class that
  mock-only units miss. This is a correctness-sensitive refactor, not a cosmetic one.
- **Dependencies:** none, but should land with a worker integration test; relates to 01 M12 (add
  ruff/mypy to worker CI) as a companion hardening.

### 15. Drop the duplicate UNIQUE index on `tracks(spotify_id)`
- **What:** Remove one of the two redundant UNIQUE constraints
  (`tracks_spotify_id_key` and `uq_tracks_spotify_id`) that both back an identical
  `UNIQUE btree (spotify_id)` index, via a human-approved `V{N}__` migration.
- **Audience:** dev-health / DB-hygiene (reclaims index + halves write-amp on the hottest write
  path).
- **Rationale:** `02-db-review: §4 "CONFIRMED duplicate — tracks(spotify_id) is indexed TWICE"` —
  two separate UNIQUE constraints back the same column, "~584 kB of index (≈2.5% of the whole DB,
  ~10% of tracks's 5.5 MB index footprint) duplicates the other, plus a doubled write-amplification
  cost on every track upsert (the hottest write path — the Spotify→worker catalog sync)." The DB
  review explicitly flags it as "a clean, real win." Cross-ref `01-code-audit` shared_db audit to
  decide which constraint is the source of truth (ORM `unique=True` vs a `V{N}__` migration). Not on
  the roadmap.
- **Size:** S (one DROP CONSTRAINT migration once the source-of-truth is identified).
- **Risk:** Med (process, not technical). DDL on prod → hard rule #3 (human approval) +
  shared_db cross-repo rollout order (migration → prod apply → pin bump). Low technical risk (the
  remaining UNIQUE preserves the constraint), but it must NOT be auto-applied. Identify the
  source-of-truth constraint first (02 openQuestion #2).
- **Dependencies:** cross-ref the shared_db models/migrations (01 audit) to pick which to drop;
  human-approved migration per rule #3.

### 16. Dead-weight subtraction sweep (front deps + music dead code)
- **What:** A pure-subtraction PR (or a small batch): remove 4 unused heavyweight front deps
  (`@dnd-kit/*`, `@toast-ui/editor`), the dead front exports (`safeFetch`/`fetchMetrics`/`Metrics`,
  `authFetch`), and the music service's dead worker-write methods + unused Spotify client surface +
  empty `enums.py`.
- **Audience:** dev-health (smaller bundles, fewer misleading affordances).
- **Rationale:** `01-code-audit: cross-cutting theme #3 "Dead weight shipped to prod"` — front M6 (4
  unused heavyweight deps, zero imports), M7/M8 (dead exports for cancelled likes/comments +
  refresh-less `authFetch` duplicate), music M4 (dead write methods + a whole parallel Spotify
  client in the Lambda bundle, "removes the misleading 'music can write albums' affordance"). All
  "pure subtraction." Also clears `03-feature-gaps: R3` (vestigial `/api/metrics/batch` for
  dropped likes/comments). Not on the roadmap.
- **Size:** S-M (mechanical deletes + a build/test re-run per repo; verify no test references first).
- **Risk:** Low. Subtraction with build+test verification. Risk is only missing a live reference — the
  audit already grepped call sites (zero). Do front and music as separate PRs (separate repos/deploys).
- **Dependencies:** none. Independent of every feature candidate; safe anytime.

---

## openQuestions

1. **Discovery bundle ordering — RSS (#1) + year-end (#2) + email (#3) are the market doc's top
   solo-blog recommendations and are all S/low-risk. Should they be bundled as one "reader-discovery
   v1" effort, or sequenced (RSS first, since #3 email bridges off it)?** (The market research
   frames them as a set; they share a content-collection foundation.)
2. **Email subscribe (#3) provider choice — does the $0-bias owner accept an external SaaS
   dependency (Buttondown/Substack/Stibee, the S path) or insist on a self-hosted SES list (the M
   path with ops cost)?** The market doc says start it regardless; the build size depends entirely
   on this answer. (Assumption inline: provider route is the S/recommended path.)
3. **Public artist page (#4) — is it shippable solo now over the existing unauthed API, or is it
   implicitly being held behind FEAT-multi-user-accounts?** (Mirrors 03 openQuestion #3. The API +
   data are done and need no user model — confirm it isn't conflated with the excluded multi-user
   RFC.) Assumption inline: treated as decided-but-unbuilt, not frozen.
4. **Year-end list (#2) and review-archive search (#6) have near-zero value at today's editorial
   scale (02 §2: 1 published post).** Are these worth building *now* as scaffolding for a growing
   archive, or deferred until N reviews exist? (They're cheap to build but inert until content lands —
   tied to the "hand-publish ≥1 real review first" precondition.)
5. **`tracks(spotify_id)` duplicate-index drop (#15) — which constraint is the source of truth
   (ORM `unique=True` vs a `V{N}__` migration), so the right one is dropped via a human-approved
   migration?** (02 openQuestion #2; needs the shared_db models/migrations cross-ref before any DDL.)
6. **Refactor-vs-feature appetite — #12/#13/#14/#16 are health/de-risk work that *unlocks or
   protects* features rather than shipping a visible one.** Given the necessity-gate convention
   ("adopt a change only when you can name concrete harm-if-unfixed"), which of these clear that bar
   for the owner today (e.g. #14 worker hot-path is reliability-load-bearing; #16 is pure low-risk
   subtraction) vs. which are gold-plating to defer? (Presented as options, not recommendations.)
7. **Album-of-the-month rail (#8) and tag/section landing pages (#7) both touch the same
   "editorial-facet" surface area as the in-flight genre `/reviews` filter and the frozen
   sub-genre work — is there a risk of these overlapping/colliding with FEAT-genre-system Steps 5-7
   scope?** (Scoped here to tags/sections to avoid the genre lane, but worth confirming the boundary.)
