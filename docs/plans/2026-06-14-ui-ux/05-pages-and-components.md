# 05 — Pages & Components Plan

**Scope.** A concrete page/component build plan for the redesign — a target IA page tree
(every node tagged [NEW]/[KEEP]/[MERGE]/[DEPRECATE] and justified), a text-wireframe spec per
page, a component table (NEW vs REUSE, citing the existing components from Task 1), the
writer/reader flows as literal page paths, and the open questions this plan surfaces. It is the
**"keep / merge / build"** layer that sits under Tasks 3–4: it does not re-decide positioning
(`03-positioning.md`) or the home concept (`04-home-strategy.md`) — it turns the recommended
directions into a page/component inventory a designer can pick up.

**Inputs.** Built on Task 1 (`01-current-frontend.md` — current routes + component inventory +
the bucket public-projection gap), Task 2 (`02-reference-teardown.md` — authority via voice +
curated canon, not crowd), Task 3 (`03-positioning.md` — "Letterboxd-foundation / IZM-surface"
model; public/private boundary Options 1→2→3), Task 4 (`04-home-strategy.md` — Concept B as the
home frame), and the already-decided site-level scope in `docs/rfcs/FEAT-home-redesign.md`
("Site-level scope" table + OQ resolutions).

**Evidence rule.** Code claims cite `file_path:line` (paths relative to `myblog_front/` unless
noted). Reference claims cite the 02 teardown section or a URL. Anything unverified is marked
*speculation*.

**Decided constraints honored as fixed (not re-opened — working rule 6):**
- `/reviews` stays the full browser; `/` becomes the editorial home (`FEAT-home-redesign.md`
  OQ4, resolved 2026-06-14). `/` does NOT subsume `/reviews`.
- The whole `/blog/` prefix migrates; `/blog/category` is removed (`FEAT-home-redesign.md` OQ0,
  resolved 2026-06-14). **The exact new prefix is NOT yet decided** — `FEAT-home-redesign.md`'s
  migration TODO still lists `[ ] Decide the new prefix (/review/[slug] vs /reviews/[slug])`. This
  doc writes **`/review/[slug]` illustratively only**; note `/reviews/[slug]` would collide with the
  surviving `/reviews` browser (see OQ in this doc + `OPEN_QUESTIONS.md` OQ-1.5). The read page
  **content** is untouched — only its route moves. The migration gets its own RFC/step and is NOT
  bundled with the home work.
- `/profile` is kept as-is for now; the single-author "About / critic" reframing is deferred
  (`FEAT-home-redesign.md` site-scope table). `BucketBoard` is **updated**, not replaced.
- Artist hub `/artist/[id]` = recommended-but-deferred (`FEAT-home-redesign.md` site-scope table).

Anything this plan adds beyond those decisions (a public bucket surface, a canon/year-end page, a
"how I rate" page) is marked **[NEW] (proposal)** and tied to the relevant OQ — it is an option for
the owner, not a decision.

---

## Target IA — page tree

```
/  (buckit) ......................................... [KEEP route, REBUILD content]
│   Justification: route exists (index.astro:1-43); today it is a duplicate of /reviews
│   (default ReviewsIndex variant, H1 literally "Reviews", index.astro:22,33). The redesign
│   replaces its CONTENT with the two-lane editorial home (Concept B, 04-home-strategy.md;
│   FEAT-home-redesign "Target state"). Route kept, page recomposed. NOT a duplicate of /reviews
│   anymore (FEAT-home-redesign OQ4).
│
├── /reviews ....................................... [KEEP]
│   Full review browser (reviews/index.astro:1-43, variant="editorial"). Stays the canonical
│   browser (FEAT-home-redesign OQ4). All filters/sort/search/BNM/year/view. The near-duplicate-
│   of-/ problem (01-current-frontend.md problem #1) is resolved by / being rebuilt, not by
│   touching /reviews.
│   └── /reviews?bnm=1 .............................. [KEEP] BNM is a FILTER, surfaced in nav
│       (header.astro:25). Keep as the nav entry per current IA; no separate route.
│
├── /review/[slug]  (was /blog/[slug]; prefix ILLUSTRATIVE — see note) [MERGE: route migrates, content KEPT]
│   The review/article read page. Content untouched (blog/[slug].astro:1-614 — review vs plain
│   branch, album hero, score card, tracklist). ONLY the URL prefix changes. FEAT-home-redesign OQ0
│   decided the migration, but the EXACT prefix (`/review` vs `/reviews/[slug]`) is still an open RFC
│   TODO — `/review/[slug]` is used illustratively here; `/reviews/[slug]` would COLLIDE with the
│   surviving `/reviews` browser (OQ-1.5). Tagged MERGE because it folds into the surviving /reviews
│   prefix family; redirects from old /blog/[slug] required (no-404 window). Own RFC/step.
│
├── /genres ........................................ [KEEP]
│   Public Genre Map / tier-0 Outliner (genres/index.astro:1-33, GenreMap island). Shipped,
│   prod-live. Client-fetched album_count share-bars. Ego-graph/sub-genres deferred (frozen).
│   This is the ONE existing public surface that already projects a curated structure — reuse its
│   share-bar pattern for Browse-by-genre on / and (proposed) public bucket lists.
│
├── search  (Pagefind dialog) ...................... [KEEP]
│   Not a route — a ⌘K overlay (header.astro:35-49, search.astro). Keep. (Site-search; distinct
│   from the music-catalog ⌘K CommandPalette inside /write.)
│
├── /rss.xml ....................................... [KEEP]
│   Feed of non-draft posts (rss.xml.ts:9-27). Keep. Link target updates to /review/<slug> under
│   the prefix migration. Candidate to extend with a curated/canon feed (OQ, see Task 2 BORROW #1).
│
├── /canon  (명반 + 올해의 앨범) ...................... [NEW] (proposal → OQ-2.2 / OQ-3-canon)
│   A single-author "canon" surface: a standing 명반 (≥4.0★) tab + a non-ranked year-end Picks
│   section (IZM /picks + 음악취향Y Best/Choice pattern, 02-reference-teardown.md IZM §3 /
│   Music-Y §2; BORROW #3/#5). NOT in the current IA. v1 = ≥4.0★ canon COMPUTED from published
│   review `rating` (content.config.ts:118) — ships with no new API. Year-end Picks as a curated,
│   blurbed, ordered list is a LATER feature (no editor-lists feature today; FEAT-home-redesign
│   non-goals). Inert-until-earned at near-zero content (03-positioning.md "inert-until-earned" OQ).
│   PROPOSAL — owner decides via OQ-2.2.
│
├── /collections  (or /lists) ...................... [NEW] (proposal → OQ-2.5 / positioning Option 2)
│   The KEY GAP from Task 1: a PUBLIC projection of selected buckets as reader-facing curated
│   lists. Today buckets are 100% owner-private behind an authed GET (01-current-frontend.md
│   "Public vs private boundary"; buckets.ts:140 GET carries Bearer; no public read path,
│   buckets.ts has zero public/visibility concept — verified). This is positioning Option 2
│   ("selected buckets public as curated lists"): only buckets the owner marks public render here,
│   the raw board + workflow crates ("재평가 대기") stay backstage. Requires a backend visibility
│   flag + an unauthed public read endpoint (medium build, 03-positioning.md Option 2 cost).
│   PROPOSAL — owner decides via OQ-2.5 / positioning Option 1/2/3. NOT shipped by the home redesign.
│
├── /about/how-i-rate  (or /how-i-rate) ............ [NEW] (proposal → OQ-2.3)
│   A short "how I rate" page making the single-author subjective-scale stance explicit (turn "no
│   universal scale" into the selling point — Letterboxd's deliberately un-standardized half-star
│   calibrated to ONE palate, 02-reference-teardown.md Letterboxd §4 / BORROW #4). Static MDX page,
│   ~no data. Doubles as the editorial framing that keeps any public rating record from reading as
│   a leaderboard (03-positioning.md "how I rate" OQ). PROPOSAL — owner decides via OQ-2.3.
│
│   ── OWNER-ONLY (auth-gated; unchanged surfaces) ──
├── /profile ....................................... [KEEP]
│   Owner hub (profile.astro:1-77, ProfileApp). Kept as-is (FEAT-home-redesign site-scope). The
│   BUCKET lives here (BucketBoard, member/BucketBoard.tsx:1243) and stays the owner's private
│   workspace. The (proposed) public /collections projects FROM this board; it does not replace it.
│   ├── 개요 (OverviewDash) ......................... [KEEP]
│   ├── 평론 버킷 (BucketBoard) ..................... [KEEP + EXTEND] add a per-bucket "공개" flag
│   │     (proposal, feeds /collections — OQ-2.5). Today no public concept exists on the board.
│   ├── 라이브러리 (LibraryTab) ..................... [KEEP]
│   ├── 평론 (ReviewsTab) ........................... [KEEP]
│   ├── 통계 (StatsTab, sample) ..................... [KEEP] (sample data; D11)
│   ├── 연동 (SpotifyIntegrationTab) ................ [KEEP]
│   └── 트랙 리뷰 tab (if present) .................. [DEPRECATE] track ratings rolled back
│         2026-05-28 (memory roadmap); FEAT-home-redesign flags it a minor later cleanup.
│
├── /write ......................................... [KEEP]
│   WriterApp editor (write.astro, write-layout.astro — no header/footer). Owner-only. Destination
│   of the writer flow from /'s writer strip. Crate ⌘K CommandPalette → compose → publish.
│
├── /drafts ........................................ [KEEP + LINK]
│   Owner post manager (drafts.astro:1-550). Today UNLINKED anywhere (01-current-frontend.md
│   problem #3 — reachable only by typing the URL). FIX: link it from the /'s writer strip
│   ("이어쓸 초안 N개", FEAT-home-redesign "Target state" #2) and from /profile. No route change.
│
├── /admin/callback ................................ [KEEP] Cognito OAuth callback (infra).
│
│   ── REMOVED ──
├── /blog/category ................................. [DEPRECATE] mislabeled flat all-posts list,
│     includes drafts, un-nav'd (category/index.astro:9,13,15). FEAT-home-redesign: REMOVE
│     (site-scope table, decided). Fold into /reviews.
├── /blog/category/[category] ...................... [DEPRECATE] per-category list, un-nav'd,
│     overlaps the /reviews genre/tag filtering. Removed with the prefix migration.
└── /blog/  (index) ................................ [DEPRECATE] already DEAD — no index file →
      404 (01-current-frontend.md, no blog/index.astro). Remove the dead constants.ts:25 HEADER
      reference that still points at it. (Also drop the dead constants.ts HEADER object entirely.)
```

**Public nav after redesign (proposed):** `{ Reviews → /reviews, Genres → /genres, Best New Music
→ /reviews?bnm=1 }` (current 3, kept) **+ any [NEW] public surface the owner approves**
(Canon → /canon; Collections → /collections; How I rate → /about/how-i-rate). The wordmark
`buckit` → `/` (now the editorial home, not a reviews clone). Search ⌘K kept.

**Footer after redesign (proposed fix):** today the footer is theme/accent controls only — no nav,
identity, RSS, or copyright (01-current-frontend.md problem #4). Add a minimal editorial footer:
wordmark + one-line identity, a small nav echo (Reviews / Genres / Canon / How I rate / RSS), the
existing theme/accent pickers, copyright. (Low-risk, high-IA-value; not gated on any OQ.)

---

## Per-page spec

Text wireframes, top-to-bottom blocks. Concrete enough to hand to a designer. "[auth]" = visible
only when logged in. Modules that self-hide at empty content are flagged "(self-hide)".

### `/` — Editorial home  [KEEP route, REBUILD content]

The Concept-B two-lane home (`04-home-strategy.md`; `FEAT-home-redesign.md` "Target state"). Frame
= editorial; bias toward a public bucket surface layered later (Task 4 recommendation).

```
┌ Header (header.astro, unchanged) ──────────────────────────────────────────┐
│ buckit wordmark · nav[Reviews · Genres · Best New Music] · ⌘K · [auth: 글쓰기 · avatar · Logout] │
├─────────────────────────────────────────────────────────────────────────────┤
│ [auth] WRITER STRIP  (pinned under header, NOT reorderable)                  │
│   버킷에 담은 앨범 N장  ·  이어쓸 초안 N개  ·  [ 새 평론 쓰기 → ]               │
│   → links: bucket count → /profile#버킷 ; drafts → /drafts ; write → /write   │
│   (logged-out readers never see this band)                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│ READER MODULE STACK  (drag-reorder + hide/restore behind a "홈 편집" toggle;  │
│                       localStorage, per-browser; FEAT-home-redesign OQ1)      │
│                                                                              │
│  ▌Best New Music hero        — 1 large featured pick + up to 2 supporting    │
│   │  selectFeatured() (reviews.ts:40-48). At 0 BNM → self-hide OR show the    │
│   │  "첫 평론을 준비 중" editorial card (OQ — do NOT silently show "latest 3"  │
│   │  dressed as an editorial pick; 04-home-strategy.md BNM-fallback OQ).      │
│  ▌Latest reviews             — editorial card feed, date-desc (buildReviewCards│
│   │  reviews.ts:108-115). Reuse ReviewsIndex card. (self-hide at 0 posts)     │
│  ▌Browse by genre            — album_count share-bars (genres.ts:61-65),      │
│   │  click → filtered /reviews. The one module that renders even at 0 reviews │
│   │  (catalog ≠ review set, 04-home-strategy.md Concept B). Runtime-fetched.  │
│  ▌By the numbers             — honest counts: 평론 N · 다룬 앨범 N · 장르 N ·  │
│   │  최근 업데이트 (build-time from blog collection). No fake members/votes.   │
│  ▌[NEW, proposal] Canon / Picks rail — ≥4.0★ computed canon teaser + link to  │
│      /canon (Task 4 "layer in one Concept-A surface"; OQ-2.2). Off by default │
│      until /canon ships. (self-hide until ≥1 ≥4.0★ review)                    │
│                                                                              │
│  EMPTY STATE (posts=0, live today): hero + latest collapse to ONE "첫 평론을   │
│  준비 중" editorial card; writer strip gets visual prominence; Browse-by-genre │
│  may still render real album_count bars (FEAT-home-redesign empty-state strat).│
├─────────────────────────────────────────────────────────────────────────────┤
│ Footer (proposed: identity + nav echo + RSS + theme/accent + copyright)       │
└─────────────────────────────────────────────────────────────────────────────┘
```

### `/reviews` — Full review browser  [KEEP]

Unchanged structurally (the rebuild is on `/`, not here). Spec for completeness:

```
Header → masthead (editorial variant) → featured hero (oversized) + 3-col grid
→ controls [search · sort[date|score|artist] · year · "BEST NEW만" · grid/list]
→ genre chip rail → tag chip rail → card grid/list (9 initial, +6 "더 보기") → footer
```
OQ-2.1 lives here: whether `sort=score` (already present, ReviewsIndex controls) is acceptable, or
whether a score-sortable facet tips `/reviews` toward leaderboard tone. The home `/` deliberately
keeps score gated behind the article (IZM rule); `/reviews` is the browser where a score facet is
defensible. Decision deferred to OQ-2.1.

### `/review/[slug]` — Review read page  [MERGE: route migrates, content KEPT]

Content untouched (blog/[slug].astro:1-614). Spec unchanged; only the URL prefix and internal links
move. Top-to-bottom (review branch):

```
Header → kicker/genre → album hero (cover + title + artist + big partial-stars)
→ score card → drop-cap long-form prose (MDX) → [client-injected] track-by-track
→ [auth] 편집 link → /write?id=<postId> → related/next (proposed add) → footer + RSS
```
Proposed additive (ties to /canon + /collections): a "related" / "appears in" block at the foot —
"이 앨범이 담긴 컬렉션" (if /collections ships) and "같은 장르 평론" (cheap, from genres). Optional;
do not block the migration on it.

### `/genres` — Genre Map  [KEEP]

Unchanged (genres/index.astro + GenreMap island). Spec:
```
Header → page title → GenreMap Outliner (containment tree, album_count share-bars,
expand defs, [auth] inline edit) → footer
```
Note (carried from Task 1): client-fetched, not pre-rendered — empty/loading until the API
responds. Acceptable as-is; flagged if SEO of /genres becomes a goal.

### `/canon` — 명반 + 올해의 앨범  [NEW] (proposal → OQ-2.2)

```
Header → page masthead "명반 · 올해의 앨범" + one-line stance line
→ TAB 1: 명반 (canon)   — grid of ≥4.0★ reviews, cover + title + artist + ★,
│         COMPUTED from review rating (content.config.ts:118). Non-leaderboard framing:
│         "기준점 이상으로 평가한 앨범" not "highest rated #1…#N".
│         Empty: "아직 명반 기준(4.0★)을 넘긴 평론이 없습니다" (inert-until-earned).
→ TAB 2: 올해의 앨범 (Picks) — year sections; v1 = ≥4.0★ filtered by year (cheap).
          A hand-curated, blurbed, ORDERED Picks list is a LATER feature (no editor-lists
          feature today, FEAT-home-redesign non-goals; needs bucket-as-list metadata,
          03-positioning.md bucket-as-list OQ). Non-ranked framing ("순서·순위 무관",
          02-reference-teardown.md IZM §3). Empty year → hidden.
→ footer
```
Authority surface, single-author-safe (it is curation of the owner's own reviews, no crowd). Ship
v1 from review `rating` with no new API; the curated-list upgrade waits on the lists feature.

### `/collections` — Public bucket lists  [NEW] (proposal → OQ-2.5 / positioning Option 2)

The public projection of selected buckets — the central Task-1 gap closer. Renders ONLY buckets the
owner flags public; reuses the existing nested-tree model (do not invent a parallel one,
03-positioning.md "reuse the real nested tree").

```
Header → masthead "컬렉션" + stance line ("내가 담아 정리한 기록")
→ grid of PUBLIC collection cards (one per public bucket):
│     bucket name + accent color + N albums + optional blurb + cover mosaic (first 3-4 covers)
→ collection detail (/collections/[id]): bucket name + blurb
│     → album list (cover + title + artist + ★ if reviewed + optional per-entry note)
│     → each album → /review/<slug> if a review exists, else a rated-but-unwritten entry
│        (which is positioning Option 3; v1 may show only reviewed albums to avoid that scope)
→ footer
```
Build dependency (03-positioning.md Option 2): a `public` visibility flag on the bucket model + an
**unauthed** public read endpoint that returns ONLY flagged buckets (fail-closed; never the tree).
This is net-new backend (cross-repo: shared_db column-add → backend route → contract → front, per
the rollout order). Owner-private `BucketBoard` is unchanged; it gains a "공개" toggle that sets the
flag. PROPOSAL — gated on OQ-2.5; NOT part of the front-only home redesign.

### `/about/how-i-rate` — How I rate  [NEW] (proposal → OQ-2.3)

```
Header → masthead "평점에 대하여" → static MDX prose:
   · the scale (0.5–5★, 0.5 steps) and that it is ONE person's calibration, not a universal scale
   · what 4.0★ (the 명반 line) means here; what a 5.0 means
   · score is the by-product of intent→evidence→judgment, written last (review-critique-method)
→ footer
```
No data. Cheapest [NEW] page; the editorial framing that lets a public rating record read as
criticism, not a scoreboard. PROPOSAL — OQ-2.3.

### `/profile`, `/write`, `/drafts` — owner surfaces  [KEEP]

Specs unchanged (Task 1 §"MEMBER area" / "WRITER area"). Two redesign deltas only:
- `/profile` → `BucketBoard` gains a per-bucket **"공개"** toggle (proposal, feeds /collections;
  OQ-2.5). Deprecate the dead 트랙 리뷰 tab.
- `/drafts` gets LINKED (from `/`'s writer strip + `/profile`) — fixes the discoverability gap
  (01-current-frontend.md problem #3). No structural change.

---

## Component plan

REUSE cites the existing component from Task 1 (`01-current-frontend.md` component inventory).
NEW = build. The bucket-projection components and the consolidation targets are called out explicitly.

| Component | NEW / REUSE | Purpose | Notes |
|---|---|---|---|
| `EditorialHome` (page composition on `/`) | **NEW** | Two-lane home shell: writer strip + reader module stack + empty-state (Concept B) | Replaces the current `index.astro` body that just mounts `ReviewsIndex` (index.astro:33). Astro shell + small React island(s) for personalization. |
| `WriterStrip` | **NEW** | Auth-gated band: bucket count · draft count · 새 평론 쓰기 | `FEAT-home-redesign` "Target state" #2. Count source is OQ2 (localStorage `lf_buckets` SWR vs light authed `GET /api/buckets`, buckets.ts:140). Links /profile, /drafts, /write. |
| `ReaderModuleStack` + `HomeEditToggle` | **NEW** | Drag-reorder / hide-restore of modules behind "홈 편집" toggle; localStorage | `FEAT-home-redesign` OQ1 (explicit toggle). Reuse the source `home.jsx` module-manager intent. Only data-backed modules appear. |
| `BNMHero` | **REUSE+wrap** `selectFeatured` (reviews.ts:40-48) + `ReviewsIndex` featured markup | Marquee editorial pick on `/` | Reuses the existing featured-selection logic; needs an editorial-layout wrapper distinct from the in-island featured strip. Self-hide / empty-card at 0 BNM (OQ). |
| `LatestReviews` (home module) | **REUSE** `ReviewsIndex` card / `buildReviewCards` (reviews.ts:108) | Date-desc editorial card feed on `/` | Reuse the card; do NOT re-mount the full filtering island on the home. |
| `BrowseByGenre` (home module) | **REUSE** `/genres` share-bar pattern (`GenreMap`, genres.ts:61-65) | album_count share-bars on `/` → filtered /reviews | Same client-fetch caveat as `/genres`. One module that renders at 0 reviews. |
| `ByTheNumbers` | **NEW** | Honest counts: reviews / albums covered / genres / last-updated | Replaces the source `PulseStrip` (fake members/votes). Build-time counts from `blog` collection (`reviews.length`, `allGenres`, `allYears`). |
| `CanonPage` / `CanonRail` | **NEW** (proposal, OQ-2.2) | ≥4.0★ computed canon + year-end Picks (`/canon`); a teaser rail on `/` | Computes from review `rating` (content.config.ts:118) — no new API for v1. Reuse a star renderer + card markup. Curated-Picks upgrade waits on the lists feature. |
| **`PublicCollections` / `CollectionCard` / `CollectionDetail`** | **NEW** (proposal, OQ-2.5) — **the key Task-1 gap closer** | Reader-facing projection of owner-flagged public buckets (`/collections`) | **Relation to the existing owner-private `BucketBoard` (member/BucketBoard.tsx:1243):** renders FROM the same nested-tree model (`BoardBucket`/`BoardAlbum`, buckets.ts:22-85) but via a NEW **unauthed public read path** — today every bucket read carries Bearer and there is zero public/visibility concept (buckets.ts:140, verified). `BucketBoard` stays the private editor; it gains a "공개" flag that this surface reads. Fail-closed: only flagged buckets, never the tree — and the public response is a **narrowed DTO** (name / accent / albums:{title, artist, cover, year, rating-if-reviewed}), **NOT** `BoardBucket`/`BoardAlbum` verbatim, whose owner-workflow fields (`researchSelected`/`researchStatus`/`alreadyReviewed`) must never reach an unauthed reader: reuse the *model*, not the *shape* (03-positioning.md "Boundary projection rule" / Option 2). |
| `BucketBoard` "공개" toggle | **REUSE+EXTEND** `BucketBoard` (member/BucketBoard.tsx:1243) | Owner marks a bucket public → feeds `/collections` | The board already keys behavior off `kind` / `isDone` flags (buckets.ts:68,74) — a `public` flag follows the same precedent. Backend visibility column required. |
| `HowIRate` page | **NEW** (proposal, OQ-2.3) | Static "how I rate" stance page (`/about/how-i-rate`) | MDX via existing `prose.astro`. No data. |
| `EditorialFooter` | **NEW** (replaces `footer.astro` body) | Identity + nav echo + RSS + theme/accent + copyright | Today `footer.astro:7-17` is theme controls only (problem #4). Keep the existing `ThemeSelect`/`AccentSelect`, add IA. |
| Header | **REUSE** `header.astro` | Unchanged chrome | Add [NEW] public nav entries only if the owner approves /canon, /collections, /about. Remove dead `constants.ts:23-29` HEADER. |
| `partial-stars.astro` | **REUSE** (components/partial-stars.astro:20) | THE canonical star renderer | **Consolidation target — see below.** Use this everywhere a star is shown in the redesign. |

### Consolidations a redesign should fold in (Task 1 cross-cutting duplication)

The redesign touches the home, adds public surfaces, and re-renders cards/stars across all of them
— so it is the natural moment to collapse Task 1's duplications (`01-current-frontend.md`
"Cross-cutting duplication"). Do NOT add a 5th copy of anything.

| Duplication (Task 1) | Current copies | Redesign action |
|---|---|---|
| **Star renderer ×4** | `partial-stars.astro:20` (canonical), `writer/PartialStars.tsx:15`, `member/ui.tsx:42` `Stars`, `reviews/ReviewsIndex.tsx:89` `Stars` | Pick `partial-stars.astro` as canonical; new home/canon/collections components use ONE shared star (a single React `PartialStars` mirroring the `.astro` math). Do not author a new star for `/canon` or `/collections`. |
| **Album-card markup ×6** | OverviewDash / LibraryTab / BucketBoard.AlbumChip:442 / AddAlbumModal.qb-hit / CommandPalette.PaletteRow / ReviewsIndex card | The home `LatestReviews`, `CanonRail`, and `CollectionDetail` all render album cards — build ONE shared `AlbumCard` and reuse, rather than a 7th variant. |
| **Album-detail fetch ×3** | `lib/albumDetail.ts:35`, `writer/WriterApp.tsx:51`, `CommandPalette.selectAlbumByLookup:197` | Not on the home critical path, but `/collections` detail needs album data — reuse `lib/albumDetail.ts` (the cached one), do not add a 4th shape. |
| **Rating-normalization (0–10→0–5) ×3** | `reviews.ts:120-131`, `review-hero.astro:20-27`, `profile.astro:34-46` | Canon (≥4.0★) computation must reuse `reviews.ts` normalization, not re-derive it — a 4th copy here would directly risk a wrong canon threshold. |
| **`fmtDate`/`fmtWhen` ×6** | OverviewDash / LibraryTab / ReviewsTab / ReviewsIndex / ResearchNote / ResearchDoc | New components import one shared date util; "last-updated" in By-the-numbers must not add a 7th. |

These are maintainability wins, but the rating-normalization one is **correctness-load-bearing** for
`/canon` (a divergent normalization = a wrong ≥4.0★ set).

---

## Flows as page paths

### Writer / editor flow (owner, auth-gated)

```
/  (editorial home)
 └─[auth] WRITER STRIP  "버킷에 담은 앨범 N장 · 이어쓸 초안 N개 · [새 평론 쓰기 →]"
      ├─ "버킷 N장"  → /profile#평론버킷  (BucketBoard — drop albums into crates, AddAlbumModal)
      │                   └─[proposal] mark a bucket "공개" → projects to /collections (OQ-2.5)
      ├─ "초안 N개"  → /drafts  (resume/edit/archive; now LINKED — fixes Task-1 problem #3)
      └─ "새 평론 쓰기" → /write
                          → ⌘K CommandPalette (album/artist/track search → crate pick)
                          → SubjectHero (cover + DragRatingInput + BNM toggle)
                          → BodyArea (MDX compose) + RecommendedTracksBlock + SettingsPanel
                          → publish (savePost → POST /api/posts → /api/publish)
                          → read page  /review/<slug>   (was /blog/<slug>)
```
Note: the writer's crate ⌘K (`/write` `CommandPalette`, writer/CommandPalette.tsx:65) is the
music-catalog search — distinct from the site-wide Pagefind ⌘K in the header.

### Reader flow (logged-out)

```
/  (editorial home — NO writer strip)
 ├─ BNM hero / Latest reviews module → /review/<slug>   (read a review)
 │      └─ on read page: [proposal] "이 앨범이 담긴 컬렉션" → /collections/<id>
 │      └─ on read page: "같은 장르 평론" → /reviews?genre=<g>
 ├─ Browse-by-genre share-bar → /reviews?genre=<g>  → /review/<slug>
 ├─ nav "Best New Music" → /reviews?bnm=1 → /review/<slug>
 ├─ nav "Genres" → /genres (Outliner) → /reviews?genre=<g>
 ├─[proposal] nav/footer "Canon" → /canon (명반 ≥4.0★ + 올해의 앨범) → /review/<slug>
 ├─[proposal] nav/footer "Collections" → /collections → /collections/<id> → /review/<slug>
 ├─[proposal] footer "How I rate" → /about/how-i-rate  (framing for the scores seen above)
 └─ footer / read page → RSS (/rss.xml)  [subscribe surface]
      └─[proposal, OQ-2.4] email capture (Bandcamp-"Notes"-style curated newsletter)
```
Both flows terminate at `/review/<slug>` (the read page) and a subscribe surface (RSS today;
+ optional newsletter if OQ-2.4 is in scope). The reader's path to the bucket foundation runs
exclusively through the [proposal] `/collections` + `/canon` surfaces — without at least one of
them, the bucket stays invisible to readers (the unresolved Task-1 gap).

---

## Open questions

OQ: Adopt the public **`/collections`** surface (positioning Option 2 — selected buckets public as
curated lists) as the reader-facing closer for the Task-1 bucket gap, or keep buckets fully private
(Option 1) with only reviews + a computed canon public? This is the single decision that determines
whether the bucket foundation ever reaches readers. (Ties OQ-2.5 + positioning Option 1/2/3.)

OQ: Build **`/canon`** (≥4.0★ computed canon + year-end Picks) now as the v1 authority surface
(cheap, no new API), or defer as premature at near-zero published content? (OQ-2.2.) If built, v1 is
a *computed* canon; the hand-curated/blurbed Picks list waits on an editor-lists / bucket-as-list
feature (FEAT-home-redesign non-goals; positioning bucket-as-list OQ).

OQ: Ship the static **`/about/how-i-rate`** page (cheapest [NEW]) as the editorial framing that
keeps public scores reading as criticism, not a leaderboard? (OQ-2.3.)

OQ: Does `/collections` (and any rated-but-unwritten public entry) require a `shared_db` **bucket
visibility column + an unauthed public read endpoint**? Today every bucket read is Bearer-gated and
`buckets.ts` has no public/visibility concept (buckets.ts:140, verified) — so yes for Option 2/3,
and it is cross-repo (shared_db → backend → contract → front). Confirm scope/sequencing. (OQ-2.5 /
positioning Option 2/3 build-cost.)

OQ: On `/reviews`, is `sort=score` (already present) acceptable, or does a score-sortable facet tip
the browser toward leaderboard tone? The home `/` keeps score gated behind the article (IZM rule);
`/reviews` is where a score facet is most defensible. (OQ-2.1.)

OQ: Should the **BNM hero on `/`** self-hide / show the empty-state editorial card when no post sets
`bestNew`, rather than silently rendering "latest 3" as if it were an editorial anointing?
(04-home-strategy.md BNM-fallback OQ — empty-state tone for the marquee slot.)

OQ: Is **email capture** (a curated, Bandcamp-"Notes"-style newsletter — 02-reference-teardown.md
Bandcamp §4) in scope for this redesign, or out given the current no-account, RSS-only posture?
(OQ-2.4.) If in scope, it is a footer/read-page subscribe affordance, not a new page.

OQ: Add the new public surfaces (Canon / Collections / How I rate) to the **header nav**, or keep
the header at its current 3 entries and surface them via the new editorial footer + cross-links
only? (Nav-weight vs discoverability; the small-content site can least afford nav clutter —
02-reference-teardown.md NOT-BORROW "opaque/over-stuffed nav".)

OQ-1.5: **The exact new read-page prefix is undecided** — `/review/[slug]` (used illustratively
throughout this doc) vs `/reviews/[slug]`. `FEAT-home-redesign.md` decided *that* the `/blog/` prefix
migrates but left the prefix string an open TODO. Note `/reviews/[slug]` would **collide with the
surviving `/reviews` browser** (the review *list* lives at `/reviews`), so `/review/[slug]` (singular)
is the cleaner pick — but this is the owner's call and belongs to the dedicated migration RFC, not
this redesign.

OQ: Is the **read-page additive block** ("이 앨범이 담긴 컬렉션" / "같은 장르 평론") worth building,
and does the "컬렉션" half presuppose `/collections` (OQ above)? The "같은 장르" half is cheap and
independent.
