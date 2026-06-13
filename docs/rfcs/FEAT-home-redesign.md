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
| **Best New Music hero** | ✅ on | `bestNew` flag via `selectFeatured()` | build now |
| **Latest reviews** | ✅ on | `blog` collection, date desc (reuse `ReviewsIndex` card) | build now |
| **Browse by genre** | ✅ on | `/genres` `album_count` share-bars → filtered `/reviews` | build now |
| **By the numbers** | ✅ on | real counts: reviews / albums covered / genres / last-updated | build now |
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
| `/blog/[slug]` (review read page) | **Keep** | The actual review reading surface — untouched. |
| `/profile` | **Keep as-is for now** | Single-author "critic/About" reframing deferred; the dead "트랙 리뷰" tab is a minor later cleanup (track ratings rolled back 2026-05-28), not this scope. |
| **Bucket view** (`BucketBoard`, source `bucket.jsx` / 평론 버킷 크레이트) | **Update existing** (not new) | Already a nestable-row DnD board with localStorage. Re-wire it as the writer-lane destination from the home's writer strip; align "add album" with the real `/write` command-palette pick. |
| Artist hub page (`/artist/[id]`) | **Recommended, not yet decided** | Roadmap item (`artist = hub page + search`). Not in the active design prompt below; add on request. |

## Open questions

0. **Scope of "remove `/blog`"** — confirmed as removing the `/blog/category` flat list
   only; `/blog/[slug]` read page stays. If the intent is to drop the `/blog/` URL prefix
   entirely (e.g. `/review/[slug]`), that's a routing migration with redirect concerns —
   handle separately. Blocks the page-removal step.

1. **Module manager affordance for readers** — does reorder/hide need an explicit
   "edit home" toggle (like the source) or inline drag handles always-on? Blocks the
   reader-personalization step. (Leaning: explicit toggle, less clutter for casual readers.)
2. **Writer-strip ↔ crate data** — does `/write`'s crate expose a count the home can
   read without loading the full WriterApp island (localStorage? a light API)? Blocks
   the writer-strip step.
3. **"Browse by genre" depth** — chips only, or share-bars mirroring `/genres`? Blocks
   that module's build.
4. **`/reviews` relationship** — does `/reviews` stay as the full browser while `/`
   becomes the editorial home, or does `/` subsume it? Affects nav + routing.

## Steps (sketch — not yet sequenced for execution)

> Draft only. Promote to accepted + add `plan.md` row before implementing.

1. **Writer strip** — auth-gated component under header; counts from crate + drafts.
2. **BNM hero + Latest** — reuse `selectFeatured()` / `ReviewCard`; editorial layout.
3. **Browse-by-genre + By-the-numbers** — real `album_count` + content counts.
4. **Reader personalization** — drag reorder / hide-restore + localStorage.
5. **Empty-state polish** — graceful 0/1/2-post rendering; writer-lane prominence.

Each step: `pnpm lint` (Node 20) + `pnpm exec astro check` + browser click-through
(UI changes need a real render check — lint/astro-check miss render/event regressions).

## Decisions log

| Date | Decision | Step |
|------|----------|------|
| 2026-06-13 | Identity = editorial (not community); keep drag personalization for readers; writer strip pinned top, auth-gated; empty-state first-class | brainstorm |
| 2026-06-13 | Remove `/blog/category`; keep `/profile`; bucket view = update existing `BucketBoard`; artist hub recommended-but-deferred | site scope |

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
