# FEAT-home-strip-ranking: hybrid ordering + visible horizontal-scroll affordances

- **Status**: draft
- **Owner**: 박지훈
- **Created**: 2026-07-18
- **Plan row**: `plan.md` → FEAT-home-strip-ranking
- **Origin**: 2026-07-18 UI planning session, area 1. Pre-resolved owner decision **D2**
  (recency·popularity hybrid).

---

## Goal

The two home album strips (새 앨범, 오늘 이 앨범들) are visibly and easily scrollable with a
mouse (arrows + edge fade + thin scrollbar), and both order by a recency×popularity weighted
score instead of today's single-axis-first sorts. **Zero contract change** — ordering moves in
the music service layer only; affordances are front-only.

## Non-goals

- New popularity metrics (playcounts etc.) — `albums.popularity` already exists and is the
  chosen axis.
- Response schema changes (both strips' sorts are server-side; the new-releases response already
  carries popularity fields regardless).
- Touch behavior changes (swipe stays as is).

## Current state (verified 2026-07-18)

- CSS: `.nrl-strip`/`.otd-strip` identical idiom — `overflow-x:auto; scroll-snap; 
  scrollbar-width:none; ::-webkit-scrollbar{height:0}`; cards `clamp(128px,32vw,150px)`.
  No arrows/fade/drag. (`NewReleasesCard.tsx:35-53`, `TodayAlbumBuckit.tsx:39-53`.)
- Ordering is decided in the music **service layer** (SQL is an over-fetch, cap 300/200):
  - new-releases: `feed_service.py:64-68` — primary-artist popularity DESC, then date DESC.
  - on-this-day: `album_service.py:74-78` — release_date DESC (newest anniversary), then album
    popularity DESC.
- Metrics: `albums.popularity` INT exists (`models.py:248`); artist popularity/followers exist;
  no track/album playcount. Primary artist = derived (popularity DESC, name ASC).
- Loading contract asymmetry (belongs to the deferred PERF area, noted here for context):
  NewReleasesCard renders nothing while loading; TodayAlbumBuckit draws a skeleton.

## Target state

- **Ordering** (owner decisions 2·3, 2026-07-18): weighted sum on **album popularity**:
  - 새 앨범: `score = w·(1 − days_since_release/30) + (1−w)·(albums.popularity/100)`, w=0.6.
  - 오늘의 앨범: `score = w·(1/years_ago) + (1−w)·(albums.popularity/100)`, w=0.6.
  - Parameters live as service-level constants (tunable without contract impact); NULL
    popularity → 0. Dedup logic unchanged.
- **Affordances** (owner decision 1 — all three):
  1. Desktop hover ‹ › arrows, one-page scroll per click (`scrollBy` container width).
  2. Edge fade + deliberate partial clipping of the next card (padding math so a card peeks).
  3. Thin visible scrollbar (`scrollbar-width:thin` + matching webkit style) replacing full hide.
  - Applied to both strips via one shared pattern (component or CSS module) so future strips
    inherit it.

## Steps

### Step 1 — service-layer ordering (myblog_music)

Implement the two scores in `feed_service.py` / `album_service.py`. No router/schema change ⇒
no openapi regen. Unit tests pin the formula (fixture albums: fresh-unknown vs old-popular).
**Verification**: pytest; prod smoke = strips return re-ranked order (spot-check one known pair).

### Step 2 — strip affordances (myblog_front)

Shared strip-affordance treatment on `.nrl-strip`/`.otd-strip`: arrows (hover, hidden on
touch/coarse pointers), edge fade masks, thin scrollbar, peek padding.
**Verification**: real-browser click-through desktop + 390px CDP (arrows absent on touch,
swipe unaffected); `pnpm lint` + `astro check`.

## Open questions

1. **w per strip** — start both at 0.6; revisit after a week of owner feel. Blocks nothing
   (constant).
2. **오늘의 앨범 recency shape** — `1/years_ago` weights 1-year anniversaries heavily; if the
   feel is too recent-biased, switch to `1/log2(1+years_ago)`. Step 1 constant choice.

## Decisions log

| Date | Decision | Step |
|------|----------|------|
| 2026-07-18 | D2 (owner, pre-session): recency·popularity hybrid | 1 |
| 2026-07-18 | Owner: weighted-sum formula; album popularity axis; contract-invariant (service-layer only); all three affordances | 1, 2 |
