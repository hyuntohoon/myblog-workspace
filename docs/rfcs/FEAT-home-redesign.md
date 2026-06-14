# FEAT-home-redesign: Editorial home with reader personalization + writer strip

- **Status**: draft
- **Owner**: TBD
- **Created**: 2026-06-13
- **Plan row**: `plan.md` → FEAT-home-redesign (not yet added — pending promotion)

> Brainstorm doc. One feedback round completed (2026-06-13). Not an accepted RFC.
> Source design: Claude Design handoff `ratemymusic/project/홈.html` (+ `home.jsx`,
> `home-modules.jsx`, `home-data.js`; intent in `chats/chat2.md`). The handoff was
> drawn for an RYM/AOTY-style **community** site; this doc reconciles it against the
> reality that myblog is a **single-author editorial** publication.

---

## Goal

Replace the current home (`/` = a bare `ReviewsIndex` browser) with a two-lane
editorial front page. The public **reader lane** is a magazine-style, reader-
personalizable module stack (drag-reorder / hide-restore, localStorage). A
**writer lane** — a thin strip pinned directly below the header, visible only when
logged in — surfaces the owner's bucket (crate) + drafts + "new review" entry. The
home renders honestly with real data only and degrades gracefully at near-zero
content (current reality: posts were reset to 0 in STAB-5).

## Implementation status (2026-06-14)

**Front shipped & prod-live.** myblog_front PR **#151** squash-merged to main (`746591c`),
auto-deployed, prod smoke PASSED on `https://www.ratemymusic.blog/` and `/canon`. Front-only —
no backend/API/contract/infra change.

Built (A–G of the home redesign):

- **A — home shell** (`home/EditorialHome.tsx`): auth-gated writer strip + personalizable
  reader module stack — 홈 편집 toggle, drag + keyboard reorder, hide/restore, localStorage,
  empty state. (Steps 1, 4, 5.)
- **B — Best New Music hero** (`home/BnmHero.tsx`): 30-day rolling window, self-hides when
  empty, stars-only. (Step 2.)
- **C — Latest reviews** (`home/LatestReviews.tsx`). (Step 2.)
- **D — Browse-by-genre teaser** (`home/BrowseGenres.tsx`): **kept SEPARATE** from the full
  `/genres` Outliner per the reconciliation decision — the home module is a *teaser* that links
  into the full page; single data source `/api/genres/tree`. (Step 3.)
- **E — By the numbers**: real honest counts (reviews / albums / genres / last-updated),
  replacing the placeholder — completed in this same push by the main agent. (Step 3.)
- **F — editorial footer**: `components/footer.astro` rewritten. (New, beyond the original step
  sketch.)
- **G — `/canon` route**: `pages/canon.astro` + `components/canon/CanonPage.tsx` — ≥4.0★ canon
  hall, no ranking/numbers, year-end placeholder; + header Canon→/canon nav; + `ds.css` helper
  classes ported into `styles/global.css`. (Owner decision D5.)

Decisions confirmed in the build: **genre = teaser + full page kept separate** (single source
`/api/genres/tree`); **BNM = 30-day rolling**; **stars only, never a numeric score to readers**
(hard rule honored). Reviewer pass: 0 HIGH / 3 MED (all fixed).

**NOT done in #151:** the `/blog → /review` prefix migration (Step 6) — **extracted 2026-06-14 to
its own RFC `docs/rfcs/FEAT-blog-to-review-migration.md`** (implemented on branch
`feat/blog-to-review-migration`, PR open, not merged). With Step 6 extracted, this RFC's own scope
(steps 1–5 + `/canon`) is complete; promotion to `done` is owner-gated (rule 5).

> **Status stays `draft`; front steps 1–5 + `/canon` shipped & prod-live — done-promotion pending
> owner approval** (rule 5, no RFC self-promotion).

## Design decisions (this brainstorm)

| # | Decision | Rationale |
|---|----------|-----------|
| 1 | **Identity = editorial publication**, single author | No community data exists (votes / members / likes / comments deliberately dropped per roadmap). Don't fake it. |
| 2 | **Keep the drag/customizable module manager** — reframed as *reader* personalization | User wants readers to arrange their own home (order + show/hide), persisted per-browser in localStorage. Carried over from the source `home.jsx` module manager. |
| 3 | **Writer strip pinned top** (directly under header), auth-gated reveal | Logged-in owner sees their work first; logged-out readers never see it. |
| 4 | **Empty state is a first-class requirement**; foreground the writer lane until content accumulates | Big BNM hero + "latest reviews" grid look broken at 0 posts. Pragmatic, fast to build. |
| 5 | Cut fabricated-community modules; keep data-backed ones | See module registry below. |

## Non-goals

- No community features (votes, member counts, "이번 주 차트" aggregate ranking,
  "당신을 위한 추천" listening-history recs). No data source exists; out of scope.
  (Note: `FEAT-multi-user-accounts` RFC exists separately — if/when multi-user lands,
  these can be revisited as real modules.)
- No release-calendar ("신보 캘린더") — no release-schedule data source.
- No editor-curated **lists** feature — fits editorial tone but the feature is unbuilt; roadmap.
- No backend/API/contract changes. This is a `myblog_front`-only redesign reusing
  existing data (`blog` content collection + `/genres` `album_count`).
- Not pixel-cloning the prototype's React-UMD/Babel structure — recreate the visual
  intent in Astro 5 + React 19 islands.

## Current state

- `myblog_front/src/pages/index.astro` — renders `<h1>Reviews</h1>` + the
  `ReviewsIndex` React island (default variant) over a server-serialized review array.
  `/` and `/reviews` share `ReviewsIndex`; `/reviews` uses `variant="editorial"`.
- `src/components/reviews/ReviewsIndex.tsx` — island owning filters / pagination /
  featured row / grid-list toggle; filter state ↔ URL querystring.
- `src/lib/reviews.ts` — `ReviewCard` shape; `buildReviewCards()`, `allGenres()`,
  `allTags()`, `allYears()`, `selectFeatured()` (BNM-first → highest-rated fallback, cap 3).
- `src/content.config.ts` — `blog` collection. Per-post: `rating` (0–10 + `ratingScale`,
  canonical 0–5), `musicReview` (subject/title/artists/genres/cover/label/links),
  `bestNew` flag, `tags[]`, `albumIds[]`, `recommendedTrackIds[]`, `draft`.
- `src/components/header.astro` — sticky magazine header, collapses on scroll; nav =
  Reviews, Best New Music; auth utils (Search, Write, Profile avatar, Login/Logout)
  toggle on `isLoggedIn()`.
- `src/components/footer.astro` — theme + accent-color pickers (the only existing "tweaks").
- `/genres` (`src/pages/genres/index.astro`) — public genre Outliner with `album_count`
  share-bars (shipped FEAT-genre-system tier-0).
- `/write` (`WriterApp`) — command-palette album pick → **crate** → review compose.
- `/drafts` — author's draft posts. `/profile` — owner stats + review tabs.
- **Content reality**: posts reset to 0 (STAB-5); AI editorial engine 0% built,
  precondition = hand-publish ≥1 real review first.

## Target state

A single `/` page composed of, top to bottom:

1. **Header** — existing `header.astro`, unchanged.
2. **Writer strip** *(auth-gated, pinned under header)* — `버킷에 담은 앨범 N장 ·
   이어쓸 초안 N개 · [새 평론 쓰기 →]`. Links to `/write`, `/drafts`. Hidden when
   logged out. Not part of the reorderable module set.
3. **Reader module stack** *(personalizable: drag reorder + hide/restore, localStorage)* —
   default order below. Each module renders only data-backed content; empty modules
   self-hide or show a graceful placeholder.

### Module registry

| Module | Default | Data source | Status |
|--------|:------:|-------------|--------|
| **Best New Music hero** | ✅ on | `bestNew` flag, **rolling 30-day window** (only posts flagged `bestNew` AND published within the last 30 days) via `selectFeatured()`; needs a **daily rebuild** (EventBridge cron) so aged-out picks drop without a content edit — see Owner decisions 2026-06-14 | ✅ built (#151, `home/BnmHero.tsx`; self-hides empty; daily-rebuild cron = follow-up) |
| **Latest reviews** | ✅ on | `blog` collection, date desc (reuse `ReviewsIndex` card) | ✅ built (#151, `home/LatestReviews.tsx`) |
| **Browse by genre** | ✅ on | **teaser** into the full `/genres` Outliner (kept separate; single source `/api/genres/tree`) | ✅ built (#151, `home/BrowseGenres.tsx`) |
| **By the numbers** | ✅ on | real counts: reviews / albums covered / genres / last-updated | ✅ built (#151 push, honest counts replacing the placeholder) |
| For-you recommendations | — | listening history + rec engine | roadmap (no data) |
| Weekly chart (aggregate) | — | community votes | roadmap (no data) |
| Release calendar | — | release schedule | roadmap (no data) |
| Editor lists | — | lists feature | roadmap (unbuilt) |
| Community trends (trending artists) | — | play counts | roadmap (no data) |

"By the numbers" replaces the source's `PulseStrip` (which showed fake members/votes)
with honest counts. "Browse by genre" is the honest version of the source's
"커뮤니티 트렌드 장르 분포" (real `album_count`, not fabricated aggregates).

### Reader personalization (kept from source `home.jsx`)

- Drag handle reorders modules; ✕ hides, tray restores. Persisted to `localStorage`
  (`lfh_order` / `lfh_hidden` analog). Per-browser, no server state.
- Only data-backed modules appear in the manager; roadmap modules are added to the
  registry as they gain real data.
- Existing footer theme/accent pickers stay; no separate tweaks panel needed for v1.

### Empty-state strategy (decision #4)

- 0 reviews → hero + latest grid collapse to a single "first reviews coming" editorial
  card; the writer strip is given visual prominence (the owner must publish first).
- 1–2 reviews → hero shows the best available; latest grid shows what exists; no fake
  filler.
- As content accumulates, the reader lane naturally takes the visual weight.

## Site-level scope (pages / components)

Decisions from the 2026-06-13 brainstorm, beyond the home page itself:

| Page / component | Decision | Note |
|------------------|----------|------|
| `/blog/category` (flat title+date table) | **Remove** | Redundant with the `ReviewsIndex` browser (`/reviews`). Fold into it. |
| `/blog/` URL prefix | **Migrate the whole prefix** (OQ0 resolved 2026-06-14) | Owner chose dropping `/blog/` entirely (e.g. `/review/[slug]`), *not* the category-only removal the brainstorm leaned toward. This is a **routing migration**: rename the read page, add redirects from old `/blog/[slug]` URLs (avoid breaking external/inbound links + search index), update every internal link + sitemap. Gets its own step. |
| `/blog/[slug]` (review read page) | **Keep content, move URL** | The reading surface itself is untouched; only its route changes under the prefix migration above. |
| `/profile` | **Keep as-is for now** | Single-author "critic/About" reframing deferred; the dead "트랙 리뷰" tab is a minor later cleanup (track ratings rolled back 2026-05-28), not this scope. |
| **Bucket view** (`BucketBoard`, source `bucket.jsx` / 평론 버킷 크레이트) | **Update existing** (not new) | Already a nestable-row DnD board with localStorage. Re-wire it as the writer-lane destination from the home's writer strip; align "add album" with the real `/write` command-palette pick. |
| Artist hub page (`/artist/[id]`) | **Recommended, not yet decided** | Roadmap item (`artist = hub page + search`). Not in the active design prompt below; add on request. |

## Open questions

0. **Scope of "remove `/blog`"** — ✅ **RESOLVED 2026-06-14: migrate the whole `/blog/`
   prefix** (owner chose the bigger scope, not category-only). `/blog/category` removed,
   `/blog/[slug]` read page moves to a new prefix (e.g. `/review/[slug]`). Routing
   migration: redirects for old URLs + internal-link + sitemap sweep. Owns a dedicated step.

1. **Module manager affordance for readers** — ✅ **RESOLVED 2026-06-14: explicit
   "홈 편집" toggle.** Reorder/hide drag handles + ✕ appear only in edit mode; clean for
   casual readers. (Matches the brainstorm leaning.)
2. **Writer-strip ↔ crate data** — *still open.* Does `/write`'s crate expose a count the
   home can read without loading the full WriterApp island (localStorage? a light API)?
   Blocks the writer-strip step. Resolve during implementation (likely read the same
   localStorage key the crate writes).
3. **"Browse by genre" depth** — *still open.* Chips only, or share-bars mirroring
   `/genres`? Blocks that module's build. (Likely settled by the design bundle.)
4. **`/reviews` relationship** — ✅ **RESOLVED 2026-06-14: `/reviews` stays the full
   browser; `/` becomes the editorial home.** Both remain in nav. `/` does *not* subsume
   `/reviews`. The `FEAT-reviews-home-genre-filter-removal` backlog item stays independent
   (removing the genre filter *on* `/reviews`), since `/reviews` survives.

## Steps (sketch — not yet sequenced for execution)

> Draft only. Promote to accepted + add `plan.md` row before implementing.
> **Steps 1–5 + `/canon` SHIPPED & prod-live 2026-06-14 (PR #151, `746591c`)** — see
> "Implementation status" above. Step 6 NOT done.

1. ✅ **DONE (#151)** **Writer strip** — auth-gated component under header; counts from crate + drafts. (In `home/EditorialHome.tsx`.)
2. ✅ **DONE (#151)** **BNM hero + Latest** — reuse `selectFeatured()` / `ReviewCard`; editorial layout. (`home/BnmHero.tsx` + `home/LatestReviews.tsx`.)
3. ✅ **DONE (#151)** **Browse-by-genre + By-the-numbers** — Browse-by-genre = teaser into `/genres` (kept separate); By-the-numbers = real honest counts.
4. ✅ **DONE (#151)** **Reader personalization** — drag reorder / hide-restore + localStorage, gated behind
   an explicit "홈 편집" toggle (OQ1).
5. ✅ **DONE (#151)** **Empty-state polish** — graceful 0/1/2-post rendering; writer-lane prominence.
   *(Also shipped in #151 beyond the original sketch: **F** footer rewrite + **G** `/canon` route — Owner decision D5.)*
6. **`/blog/` prefix migration** (OQ0) — **EXTRACTED 2026-06-14 → `docs/rfcs/FEAT-blog-to-review-migration.md`**
   (implemented front-only, PR open, not merged). Rename read route to `/review/[slug]`, remove
   `/blog/category`, static no-404 redirect stubs from old `/blog/[slug]` URLs, sweep internal links +
   sitemap. The redirect mechanism was non-trivial (static S3-website model → no request-time 301),
   so per the note below it was split to its own RFC.

Each step: `pnpm lint` (Node 20) + `pnpm exec astro check` + browser click-through
(UI changes need a real render check — lint/astro-check miss render/event regressions).

## `/blog/` prefix migration — TODO (✅ SUPERSEDED — now `FEAT-blog-to-review-migration`)

> **2026-06-14: this section is superseded.** The migration was written up as its own RFC
> (`docs/rfcs/FEAT-blog-to-review-migration.md`) and implemented front-only on branch
> `feat/blog-to-review-migration` (PR open, not merged). The checklist below is retained for
> history; the dedicated RFC + its manual test checklist are authoritative.

High-level task list only. **A detailed plan / sequencing doc (possibly its own RFC)
MUST be written and reviewed before any of this is executed** — especially the redirect
mechanism and no-404 sequencing. Do NOT bundle with the front-only home redesign
(steps 1–5); run last and separately.

- [ ] Decide the new prefix (`/review/[slug]` vs `/reviews/[slug]` — align with the surviving `/reviews` browser)
- [ ] Decide the redirect mechanism (CloudFront Free vs Astro-level) — note CF Free plan rejects custom policies; confirm what's feasible
- [ ] Rename the read-page route file; keep page content untouched
- [ ] Remove `/blog/category` page
- [ ] Add redirects from old `/blog/[slug]` URLs (in place before/with the rename — no 404 window for inbound/search links)
- [ ] Sweep all internal links to old `/blog/*` (header, cards, `ReviewsIndex`, footer, anywhere)
- [ ] Update sitemap + canonical URLs
- [ ] Update smoke tests / any hardcoded `/blog` paths
- [ ] Verify content-collection slug behavior under the new route

## Decisions log

| Date | Decision | Step |
|------|----------|------|
| 2026-06-13 | Identity = editorial (not community); keep drag personalization for readers; writer strip pinned top, auth-gated; empty-state first-class | brainstorm |
| 2026-06-13 | Remove `/blog/category`; keep `/profile`; bucket view = update existing `BucketBoard`; artist hub recommended-but-deferred | site scope |
| 2026-06-14 | OQ0 → migrate the whole `/blog/` prefix (not category-only); OQ1 → explicit "홈 편집" toggle; OQ4 → `/reviews` stays full browser, `/` does not subsume it. Path: implement from a Claude Design bundle (pending), promote RFC after design is confirmed. | OQ resolution |
| 2026-06-14 | **Owner UI/UX-review decisions (D1–D9 + BNM 30-day rolling)** — see "Owner decisions" section below. | review |

---

## Owner decisions — 2026-06-14 (UI/UX & IA review)

Confirmed by the owner during the `docs/plans/2026-06-14-ui-ux/` review. **Status stays `draft`**
(no self-promotion); these record design decisions, not a status change. Cross-ref:
`docs/plans/2026-06-14-ui-ux/00-SUMMARY.md` §"확정 결정".

- **Positioning (D1):** "Letterboxd-foundation / IZM-surface" — the bucket/log stays the foundation;
  a thin owner-curated editorial surface (canon + future year-end Picks) supplies authority. Neither
  pure-editorial nor pure-log.
- **Home structure (D3):** Concept B (this RFC's two-lane editorial home) — confirmed as the frame.
- **Best New Music hero (NEW):** rolling **30-day window** — the hero shows only posts flagged
  `bestNew` **and** published within the last 30 days; picks age out automatically. Because the site
  is static, this needs a **daily rebuild** (EventBridge cron) so a pick drops without a content edit.
  `selectFeatured()` gains a recency filter. *Empty-month behavior (no BNM in the last 30 days =
  self-hide vs. fall back to latest) is a follow-up OQ.*
- **Score display (D7):** stars only, **no numbers, ever** — **already implemented**
  (`writer/DragRatingInput.tsx`: the numeric value shows to the author only while dragging and never
  reaches the published read page; `partial-stars` is continuous, not 0.5-step). **No work needed.**
  A star-based `sort` on `/reviews` is acceptable.
- **`/canon` (D5):** BUILD — a computed **★4.0+** canon from review `rating` (no new API). Inert /
  scaffolded at 0 posts; fills as reviews accrue. Hand-curated, blurbed year-end Picks **deferred**
  (needs the editor-lists / bucket-as-list feature).
- **Public bucket projection (D2 / D4):** **deferred and coupled to multi-user accounts**
  (`FEAT-multi-user-accounts`). Target form = a **read-only public viewer** of the bucket board
  ("current format, not editable, anyone can view"). What is shown vs. kept private (e.g. workflow
  crates like "재평가 대기") is decided then. `/collections` is **NOT** built now.
- **`/about/how-i-rate` (D6):** NOT built.
- **Email subscription (D8):** NOT in scope (RSS-only posture kept).
- **Read-page prefix (D9):** **`/review/[slug]`** (singular — `/reviews/[slug]` would collide with
  the surviving `/reviews` browser). Confirmed for the dedicated `/blog`-migration step.

**Net "build now" set:** (1) Concept-B editorial home with the 30-day-rolling BNM hero + daily
rebuild cron, (2) `/canon` (★4.0+ computed, graceful empty state), (3) the `/blog → /review` prefix
migration (its own step). Everything else above is deferred or already done.

---

## Appendix — Claude Design prompt

Paste into claude.ai/design **on the existing `ratemymusic` bundle** (it already has
`홈.html`, `home.jsx`, `home-modules.jsx`, `bucket.jsx`, `ds.css` + shared components).
Iterate on the existing `홈.html` and `bucket.jsx`, don't start blank. Korean UI.

> 현재 `홈.html`을 **단일 저자 에디토리얼** 음악 평론지 홈으로 다시 만들어줘. 기존
> `ds.css` 디자인 시스템과 공유 컴포넌트(`Cover`/`Stars`/`ScoreNum`/`SectionTitle`/
> `AlbumDetail`)는 그대로 재사용하고, `home.jsx`·`home-modules.jsx`를 기반으로 수정해.
> 이 사이트는 커뮤니티가 아니라 **혼자 운영하는 평론지**라 가짜 커뮤니티 지표(멤버 수·
> 투표·집계 차트)는 전부 빼야 해.
>
> **유지/구축할 모듈 (실제 데이터로 채워짐):**
> 1. Best New Music 히어로 — 금주 선정 1편 대형 + 보조 2편 (기존 그대로)
> 2. 최신 평론 — 에디토리얼 카드 피드
> 3. 장르로 탐색 — 장르별 점유율 막대(share-bar) + 클릭 시 해당 장르 평론으로. 기존
>    '커뮤니티 트렌드'의 정직 버전 (앨범 수 기반, 가짜 트렌딩 아티스트 제거)
> 4. By the numbers — 멤버·투표 대신 **진짜 카운트**: 평론 N편 · 다룬 앨범 N장 ·
>    장르 N개 · 최근 업데이트. (기존 `PulseStrip` 교체)
>
> **제거할 모듈:** 당신을 위한 추천(감상이력 추천), 이번 주 차트(커뮤니티 투표),
> 신보 캘린더, 에디터의 리스트, 커뮤니티 트렌드의 급상승 아티스트. (데이터 소스 없음)
>
> **독자 개인화는 유지:** `home.jsx`의 모듈 드래그 재배치 + 숨기기/복원 +
> localStorage 저장은 그대로. 단 데이터 있는 모듈만 매니저에 노출.
>
> **새로 추가 — 작가 스트립:** 헤더 바로 아래 최상단에 얇은 밴드. **로그인 상태일
> 때만** 표시. 내용: `버킷에 담은 앨범 N장 · 이어쓸 초안 N개 · [새 평론 쓰기 →]`.
> 평론 버킷(크레이트)·글쓰기·초안으로 연결. 비로그인 독자에겐 완전히 숨김.
> 재배치 가능한 독자 모듈이 아니라 상단 고정 영역.
>
> **빈 상태 우선:** 평론이 0편일 때 히어로·최신 그리드는 "첫 평론을 준비 중" 에디토리얼
> 카드 하나로 접히고, 작가 스트립이 시각적으로 두드러지게. 1~2편이면 있는 만큼만,
> 가짜 채움 없이.
>
> **버킷뷰(`bucket.jsx` / 평론 버킷) 갱신:** 새로 만들지 말고 기존 중첩 가로줄 버킷
> 보드를 유지하되, 홈의 작가 스트립에서 도착하는 **작가 동선의 종착지**로 연결해줘.
> '앨범 추가'는 실제 `/write`의 앨범 검색→크레이트 담기 흐름과 결이 맞게(커맨드 팔레트
> 느낌). localStorage 저장 유지.
>
> **톤:** 가독성 최우선의 잡지형 — serif 디스플레이 제목, 넉넉한 여백, 1~2열, 강한
> 타이포 위계. 라이트/다크 + 액센트. 전부 한국어 UI. 정직한 데이터만(없는 숫자 금지).
