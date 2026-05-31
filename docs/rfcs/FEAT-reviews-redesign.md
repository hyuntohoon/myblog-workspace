# FEAT-reviews-redesign: Pitchfork-style review index + site-wide stars-only

- **Status**: accepted
- **Owner**: park (hyuntohoon)
- **Created**: 2026-05-31
- **Plan row**: `plan.md` → FEAT-reviews-redesign
- **Repo**: `myblog_front` (frontend-only; no backend/contract/infra/DB change)
- **Design source**: Claude Design handoff `fitchpork-style-magazine-website` → `Lowfreq Reviews.html` (+ shared `reviews.jsx`, `reviews-app.jsx`, `browse-data.js`, `covers.jsx`). Re-fetchable at the design URL; essential specs embedded below so this RFC is self-contained.

---

## Goal

A new top-level **`/reviews` review-index page** in the established `lfq` editorial design language (cream/ink/accent, Newsreader + Noto Serif KR + IBM Plex, hairline rules), matching the Pitchfork-style "Lowfreq Reviews" mockup: a masthead, a featured row (lead + 2 side cards), a control strip (genre chips + sort), a square-cover card grid, and load-more. The page is interactive (genre filter, sort, search, BNM/year filters, grid/list toggle) with all filter state URL-synced for shareable/back-button-able views. Ratings render **as partial-fill stars only — no numeric score anywhere** — and the homepage review cards are unified to the same stars-only treatment so the whole site is consistent with the read-page decision (FEAT-view-redesign Step 4).

## Non-goals

- **No numeric scores** anywhere (cards, featured, home). Extends the read-page "stars-only" decision site-wide. Numbers are removed from home cards, not added to new ones.
- **No `/blog` and `/blog/category` table redesign** this RFC — those legacy tables stay as-is (possible follow-up).
- **No new backend/API/contract/schema work.** Consumes existing `blog` collection fields only. No `openapi.json` regen, no `apigateway.tf`, no shared_db change.
- **No genre-taxonomy system.** Multi-genre on write, a genre management API (CRUD like categories), cross-cutting genre filtering (music search + review search), unified genre view, and editing genres on published posts are a **separate cross-repo initiative → FEAT-genre-taxonomy** (plan.md Backlog; to be RFC'd with `architect` + `planner`). This RFC's genre filter is built **array-aware** (reads `musicReview.genres[]`) so it stays forward-compatible when that taxonomy lands — no rework.
- **No accent-color switcher / Tweaks panel** from the mockup. Keep the fixed accent (`--color-accent: #c8332b`) and reuse the existing `theme-provider` dark mode. Drop the mockup's per-page `REVIEWS_DEFAULTS` tweak system.
- **No abstract SVG cover generator** (`covers.jsx`). Use real album covers (`albumCover` / `musicReview.cover.src`) with the existing initials placeholder fallback.
- **No multi-reviewer bylines.** Single-author site — drop the "— reviewer" line (or bind to `SITE.defaultAuthor`; see Open Q2).
- No comments/likes/save on the index.

## Current state

- **Design system is already in the codebase** (introduced by FEAT-view-redesign). Reuse, don't duplicate:
  - Tokens: `src/styles/global.css:11-53` — `--color-bg #f5f3ee`, `--color-paper #ebe7df`, `--color-text #1a1a1a`, `--color-subtle #5a5651`, `--color-faded #918a80`, `--color-border rgba(26,26,26,.18)`, `--color-border-soft rgba(26,26,26,.10)`, `--color-accent #c8332b`, `--font-serif` (Newsreader+Noto Serif KR), `--font-mono` (IBM Plex Mono), `--font-sans` (IBM Plex Sans). Dark overrides via `@variant dark` / `[data-theme=dark]`.
  - Fonts loaded once in `src/layouts/layout.astro:19,23`.
  - Dark mode: `src/components/theme-provider.astro` (localStorage `atmb-theme`, set pre-paint).
  - Stars: `src/components/partial-stars.astro` — 5-star partial fill, **no number**, props `{value, max=5, size, ariaLabel}`.
  - `.mono-label`, `.rule-ink` utilities in `global.css`.
- **No reviews-index page exists.** Listing surfaces today:
  - `src/pages/index.astro` — homepage: `HeroReview` + `BestNewMusic` (4-grid) + `ReviewGrid` (3-grid, "Latest Reviews"). Sorts `getCollection('blog')` desc by date.
  - `src/pages/blog.astro`, `src/pages/blog/category/*` — legacy **table** lists (out of scope).
  - `src/pages/blog/[slug].astro` — single-post read page (already lfq + stars-only; `isReview = albumIds.length>0 || rating != null`).
- **Home cards currently show numeric scores** (inconsistent with read page):
  - `src/components/review-grid.astro:34-73` — `.rc-score-overlay` shows `{rating}` on cover hover.
  - `src/components/best-new-music.astro:37-79` — `.score-badge` `{rating}/{ratingScale}` + gold "Best New Music" badge.
  - `src/components/hero-review.astro:23-94` — large `.score-badge` `{rating}/{ratingScale}`.
- **Rating model**: top-level `rating` (z.number 0–10, optional), `ratingScale` (5|10, default 5). Effective scale is **0–5 in 0.5 steps** (album-only; see roadmap). Stars normalization (from `[slug].astro:44-46`): `ratingForStars = rating==null ? null : (ratingScale===10 ? rating/2 : rating)` → 0–5.
- **Bindable fields**: `title`, `slug`, `date`, `description` (dek/excerpt), `category` (single), `draft`, `albumCover`, `image`, `rating`, `ratingScale`, `bestNew`, `musicReview?.{title, artists[], genres[], label, cover{src,alt}, releaseDate}`.
- **No genre/sort/search UI** anywhere yet.
- Interactivity precedent: `src/pages/write.astro` mounts a React 19 island (`WriterApp`). Same pattern is available here.

## Target state

A new route **`/reviews`** (`src/pages/reviews/index.astro`) rendering, top to bottom:

1. **Masthead** — centered, `border-top/bottom: 2px solid --color-text`, padding `28px 0 32px`. Mono kicker (uppercase, `letter-spacing .18em`, `--color-faded`); serif title `리뷰` `clamp(56px,10vw,120px)/0.92`; italic kr-serif sub.
2. **Featured** (hidden when a genre filter is active) — CSS grid `minmax(0,1.5fr) minmax(0,1fr)`, gap 28px:
   - **Lead**: 16:10 cover, BNM badge (top-left, `--color-accent` bg, white), meta (`genre · date`), mono uppercase artist, serif italic album `clamp(32px,4vw,48px)`, 2-line excerpt, foot rule with **big partial-stars** (replaces the mockup's big numeric score) + byline.
   - **Side** (2 cards): 96px square cover + `BNM` mini-badge + meta + artist + serif album + **small stars**.
   - Source = latest `bestNew` reviews first; if fewer than 3, fill remaining slots with the highest-rated recent reviews; if 0 BNM, fall back to the latest 3 reviews (row is never empty/short).
3. **Control strip** — `border-bottom: 1px solid --color-text`. Left: serif `최신 리뷰` 28px + mono count `{n}편`. Right: scrollable **array-aware** genre chips (`전체` + each distinct genre across reviews' `musicReview.genres[]`, fallback `category`; a review matches a chip if the genre ∈ its genre set — so a multi-genre review appears under several chips; active = ink fill / accent) + sort `<select>` (`최신순 / 평점순 / 가나다순`). Plus (this RFC's additions): search box, `BEST NEW만` toggle, year `<select>`, grid/list view toggle.
4. **Grid** — `repeat(auto-fill, minmax(290px,1fr))`, gap `32px 28px`. Card = 1:1 cover (border `--color-border-soft`, `scale(1.04)` on hover, BNM badge top-left), body: mono meta (`genre · date`), mono uppercase artist, serif italic album 23px, 2-line clamped excerpt, foot rule with **partial-stars** (no numeric chip) + byline. **List view**: compact horizontal rows for fast comparison.
5. **Load-more** — show 9, `+6` per click; bordered mono button. Empty-state block when filters match nothing.
6. **Footer** — mono hairline strip.

**Interactivity (React island, hydrated `client:load`)**: server serializes a normalized review array; island owns `genre / sort / search / bnmOnly / year / view / visible` state, all (except `visible`) **mirrored to the URL querystring** (`?genre=Rock&sort=score&q=...&bnm=1&year=2026&view=list`) with `history.pushState` + `popstate` so deep-links and the back button work. Reuse `partial-stars` for stars; reuse existing dark mode (no per-page tweak).

**Homepage unification** (Step 4): `review-grid`, `best-new-music`, `hero-review` drop numeric `.score-badge`/`.rc-score-overlay` → `partial-stars`, and card details align to the `/reviews` look (square cover, BNM badge, 2-line excerpt clamp). Header nav gains a `/reviews` link.

"Review" selection for the index = `rating != null || (musicReview != null) || albumIds.length > 0`, excluding `draft`.

## Steps

Steps are **frontend-additive** (no prod data/contract risk). Each is independently mergeable + browser-verified. Step 4 is **parallel** to Steps 1–3 (separate surface — homepage components).

### Step 1 — `/reviews` static page (server-rendered, stars-only)

New `src/pages/reviews/index.astro`. Server-side: select review posts, normalize to a card model (`{slug, album, artist, genres, category, date, ratingForStars, ratingScale, bestNew, cover, excerpt}`), compute featured set. Render masthead + featured + full grid + footer using lfq tokens and `partial-stars`. No filter UI / no JS yet (renders all cards). Add header nav link to `/reviews`. New page-scoped CSS (`.rev-*` classes) ported from the mockup, mapped onto existing `--color-*` tokens.

**Verification**:

```
cd myblog_front && pnpm lint && pnpm exec astro check && pnpm build
# browser: /reviews renders masthead, featured (stars not numbers), grid with real covers + placeholder fallback; dark mode toggles; responsive at 880/640px
```

**Rollback**: delete route + nav link (additive, no shared-state change).

---

### Step 2 — Interactive island: genre + sort + load-more + URL sync

Add `src/components/reviews/ReviewsIndex.tsx` (React) mounted `client:load`, fed serialized data from Step 1's page. Implement **array-aware** genre chips (a review matches if the chip's genre ∈ its `genres[]`, so multi-genre reviews surface under several chips), sort (`date-desc / score-desc / artist`), load-more (9 then +6), and **URL querystring sync** (pushState + popstate; deep-link restores state). Featured hides when `genre !== 'all'`.

**Verification**:

```
cd myblog_front && pnpm lint && pnpm exec astro check && pnpm build
# browser: click a genre chip → grid filters + URL gains ?genre=…; sort reorders; load-more reveals +6; back button restores prior filter; reload of a deep-link restores state
```

---

### Step 3 — Search + BNM toggle + year filter + grid/list toggle

Extend the island: search box (case-insensitive substring over album + artist), `BEST NEW만` toggle, year `<select>` (derived from data), grid↔list view toggle (list = compact comparison rows). All URL-synced. Empty-state when no matches (with a reset button).

**Verification**:

```
cd myblog_front && pnpm lint && pnpm exec astro check && pnpm build
# browser: type in search → filters live; BNM toggle; year narrows; list view renders compact rows; conflicting filters → empty-state + reset; all reflected in URL
```

---

### Step 4 — Homepage card unification (stars-only) — _parallel to 1–3_

Update `review-grid.astro`, `best-new-music.astro`, `hero-review.astro`: remove numeric `.score-badge` / `.rc-score-overlay`, render `partial-stars` instead; align card chrome (square cover, BNM badge, 2-line excerpt clamp) to the `/reviews` cards. No data changes.

**Verification**:

```
cd myblog_front && pnpm lint && pnpm exec astro check && pnpm build
# browser: homepage hero + BNM grid + Latest grid show stars (no numbers); visual parity with /reviews cards; dark mode intact
```

**Rollback**: revert the 3 components (self-contained).

---

## Open questions

_(all resolved 2026-05-31 — see Decisions log)_

## Decisions log

| Date       | Decision                                                                                                                                                                                                                                                                                                                                           | Step |
| ---------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---- |
| 2026-05-31 | Score display = **stars-only site-wide** (no numbers on cards/featured/home).                                                                                                                                                                                                                                                                      | all  |
| 2026-05-31 | Scope = new `/reviews` index **+ homepage card unification**; legacy `/blog` tables out of scope.                                                                                                                                                                                                                                                  | all  |
| 2026-05-31 | Include all 4 extra features: URL-synced filters, search, BNM+year filters, grid/list toggle.                                                                                                                                                                                                                                                      | 2,3  |
| 2026-05-31 | Interactivity via React island (matches `write.astro`); reuse `partial-stars`, tokens, theme-provider; drop mockup Tweaks/accent-switcher + SVG covers.                                                                                                                                                                                            | 2,3  |
| 2026-05-31 | **Genre work split out**: reviews-redesign stays frontend-only; genre filter built **array-aware** on `musicReview.genres[]` (fallback `category`) for forward-compat. Genre taxonomy (multi-genre write + management API + cross-cutting filter + unified view + edit-on-published) → separate **FEAT-genre-taxonomy** RFC (architect + planner). | 2    |
| 2026-05-31 | **Featured** = latest BNM first; fill to 3 with highest-rated recent; if 0 BNM, fall back to latest 3. Row never empty/short.                                                                                                                                                                                                                      | 1    |
| 2026-05-31 | **Excerpt** = `description` (dek / 한줄평), 2-line clamp; if empty, fall back to first ~2 lines of body.                                                                                                                                                                                                                                           | 1    |
| 2026-05-31 | **Card rating visual** = foot-row `partial-stars` only; no numeric cover chip.                                                                                                                                                                                                                                                                     | 1    |
| 2026-05-31 | **Byline** omitted on cards/featured (single-author site; redundant).                                                                                                                                                                                                                                                                              | 1    |
