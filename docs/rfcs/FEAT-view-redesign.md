# FEAT-view-redesign: Article read page → Lowfreq parity + rating / search / writer fixes

- **Status**: accepted
- **Owner**: TBD
- **Created**: 2026-05-31
- **Plan row**: `plan.md` → FEAT-view-redesign
- **Design source**: Claude Design bundle "Lowfreq Article.html" (`fitchpork-style-magazine-website/project/`), handed off from `https://api.anthropic.com/v1/design/h/9grq0ReGcaS6KDk7CkuFCw`. Extracted reference at `/tmp/lowfreq_design/` during drafting; the prototype is not checked in. Sibling of the closed `FEAT-writer-lowfreq-redesign` (writer side) — this RFC is the reader side plus the adjacent fixes the user batched in the same round.

---

## Goal

Bring the live article read page (`myblog_front/src/pages/blog/[slug].astro` + `review-hero.astro` + `prose.astro` + `AlbumDetailView.astro`) to parity with the Lowfreq Article prototype, and ship four adjacent fixes the user requested together: (1) **Spotify-style search sectioning** in the writer subject picker (Artist / Album / Track sections instead of an interleaved grid), (2) **recommended tracks → boolean "pick" model** (drop the 5-item limit and manual ordering; picks become ★ flags on the full album tracklist), (3) **continuous fractional rating** (0–5, captured by drag, stored to 2 decimals, displayed **only** as partial-fill stars — the numeric value is never shown to the reader), (4) **publish-checklist removal** with relaxed validation (only 작품 + 본문 required). Each step ships as its own PR per CLAUDE.md rule #4.

## Non-goals

- **No track or artist rating.** Album-only rating stays the product decision ([[project-feature-roadmap]]). The prototype's per-track rating column + meter bar are **dropped** — myblog has no per-track rating data.
- **No 10-point scale.** The prototype hero shows `SCORE / 10.0` with `score.toFixed(1)`; we keep the existing **0–5** scale and **hide the number entirely** (deliberate departure from the mockup — do not copy its star/number rendering).
- **No comments, likes/saves, tags, author-bio, or related-reviews sections** on the read page this round. The prototype includes them but myblog has no backing data; they are excluded (user decision 2026-05-31). Engagement/comments would need new backend tables + endpoints — out of scope here.
- **No "Appears On" / featured-track discography** in active scope. `track_artists.role` is unpopulated and surfacing participation credits needs music + worker + front changes — deferred (Step 7 pointer).
- **No change** to Cognito auth, the publish-to-Git pipeline (`POST /api/publish`), or the Astro static build/deploy.
- **Dark mode is already shipped** (`theme-provider.astro` + `theme-select.astro`, light/dark/auto). This RFC does **not** rebuild it; the only theming work is the optional accent picker (Step 6).

## Current state

Concrete, per area:

**Search (writer subject picker)**

- `myblog_music` `GET /api/music/search/unified` already returns **three typed arrays** — `artists[] / albums[] / tracks[]` (`app/domain/schemas.py` `UnifiedSearchResult`), with per-bucket `artist_offset / album_offset / track_offset` paging. `TrackItem` already carries `feat_artist_names`.
- `myblog_front/src/components/writer/SubjectBlock.tsx` (~739–796) **interleaves** the three arrays round-robin (`interleave(albums, artists, tracks)`) into one tile grid; each tile shows a small type label but they are mixed. A filter lets the user show one type at a time.

**Recommended tracks**

- `myblog_front/src/components/writer/RecommendedTracksBlock.tsx` + `types.ts:68` `RECOMMENDED_TRACK_LIMIT = 5` (frontend-only gate; no backend limit).
- Selection order → `position` (`RecommendedTrack.position`); stored in `post_recommended_tracks_table.position` (`myblog_shared_db/.../models.py:71`, `SmallInteger`); backend reads `.order_by(position.asc().nullslast())` (`myblog_backend/app/services/post_service.py:296`).

**Rating**

- Writer input: `SubjectBlock.tsx` (578–609) star buttons + number field `step={0.5}`; `displayStars = Math.round(score)` (line 310).
- API: `WritePostRequest.rating` / `UpdatePostRequest.rating` = `Optional[float] = Field(ge=0, le=5)` — **no step constraint** (`myblog_backend/app/api/schemas.py:44,90`). `rating_scale=5` hardcoded (`publish.py:78`).
- DB: `rating: Mapped[Optional[float]] = mapped_column(Numeric(3, 1))` (`models.py:232`) — **only 1 decimal**; cannot store 4.69.
- Read display: `review-hero.astro` (80–90) renders the raw number `{rating % 1 === 0 ? rating.toFixed(1) : rating}/5` — **no stars on the read page**.

**Publish checklist**

- `myblog_front/src/components/writer/SettingsPanel.tsx` (66–72) renders 4 informational `<Check>` rows. The actual publish gate is the button `disabled={!subject || !headline.trim() || score <= 0 || body.trim().length < 80}` (SettingsPanel.tsx:83; mirrored in `WriterApp.tsx:267`). The checklist itself gates nothing.

**Article read page**

- Route `myblog_front/src/pages/blog/[slug].astro` (prerendered). Tree: `Layout → ReviewHero (review-hero.astro) → #music-section → article-wrap → Prose(Content) → tracklist-section → #albumDetail` (injected by `albumDetail.client.ts`).
- Styling: Astro scoped `<style>` + Tailwind prose + `global.css` design tokens (`--color-bg #f5f3ee`, `--color-text #1a1a1a`, `--color-accent #c8332b`, dark `#141312`; serif Newsreader + Noto Serif KR). `AlbumDetailView.astro` uses **hardcoded** grays/blues (`#f3f4f6`, `#0ea5e9`…) that break in dark mode.

**Theming** — `theme-provider.astro` + `theme-select.astro` give working light/dark/auto via `[data-theme]` on `<html>` and the `global.css` `@theme` block. No accent customization.

## Target state

1. **Search**: `SubjectBlock` renders three labeled sections — `아티스트` / `앨범` / `트랙` — each its own row/grid, in that order, instead of an interleaved tile list. Backend unchanged. Empty sections are omitted. Per-bucket "더 보기" can reuse the existing offsets (optional within the step).
2. **Recommended tracks**: no count limit, no ordering UI. A recommended track is a **boolean pick** (a set of track IDs on the post). On the read page the **full album tracklist** is shown with a `★` flag on picks (prototype "트랙 바이 트랙", `★ 표시는 비평가의 픽`). `position` column is left in place but unused (nullable; no migration required to drop it).
3. **Rating**: writer captures a continuous 0–5 value by **drag** over a star strip; the stored value keeps **2 decimals** (`Numeric(3,2)`); every surface renders it as **partial-fill stars only** (CSS clip/gradient), and the numeric value is **never** shown to the reader. The writer may show the live value to the author while dragging (author-facing affordance), but the published page does not.
4. **Publish**: the checklist block is gone. The publish gate relaxes to `subject && body.trim().length > 0` (작품 + 본문만 필수); 평점·헤드라인 optional.
5. **Article page**: `blog/[slug].astro` is restructured to the Lowfreq Article layout — reading **progress bar**, **font-size toggle** (sm/md/lg via `[data-size]`), article header (kicker · genre · date · read-time, headline, dek, byline), **album hero** card (280px cover + label/year/artist/album/genre + accent-bordered score card showing **partial-fill stars, no number**), article **body** (drop-cap first paragraph, `h2`, accent pull-quote), and **track-by-track** list (track number, title, ★ pick flag, duration — **no rating column/meter**). Tags / author / related / comments / engagement are **excluded**.
6. **(additive)** Accent color picker: a persisted `--accent` override (localStorage), options matching the prototype (`#c8332b` red, `#1f3fa8` blue, `#1f7a4a` green, `#8a5cf0` purple), wired alongside the existing theme select; `AlbumDetailView.astro` hardcoded colors replaced with `var(--color-*)`.
7. **(deferred)** "Appears On" participation tracks — pointer only, see Step 7.

## Steps

Steps 1, 2 are frontend-only and independent (any order, parallel-eligible). Step 3 (recommended-pick) and Step 4 (rating) must both land before Step 5 (article page composes their new display). Step 4 is cross-repo and ordered internally. Step 6 is additive; Step 7 is deferred.

---

### Step 1 — Search result sectioning (frontend-only)

Replace the round-robin `interleave()` in `SubjectBlock.tsx` with three labeled sections (`아티스트` / `앨범` / `트랙`), rendered in that order, each as its own grid. Omit empty sections. Keep the existing tile components and the type filter. Backend and contract unchanged.

**Verification**:

```
cd myblog_front && pnpm lint && pnpm exec astro check
# dev: type "빅뱅" → assert artist tiles render under 아티스트, albums under 앨범, tracks under 트랙
```

---

### Step 2 — Publish checklist removal + validation relaxation (frontend-only)

Delete the checklist block (`SettingsPanel.tsx` 66–72) and the `Check` helper (20–27) + its `writer.css` rules (~1170–1194). Relax the publish gate (SettingsPanel.tsx:83 and `WriterApp.tsx:267`) to `!subject || body.trim().length === 0`. Confirm 평점·헤드라인 no longer block publish.

**Verification**:

```
cd myblog_front && pnpm lint && pnpm exec astro check
# dev: subject + 1-char body, no rating, no headline → publish button enabled
```

---

### Step 3 — Recommended tracks → pick-flag model (frontend + backend; **contract change**)

- Frontend: remove `RECOMMENDED_TRACK_LIMIT` enforcement and any ordering UI; selection becomes a toggle (pick / unpick) over the album's tracks. Drop the `position`/`#N` display.
- Backend: post create/update payload represents recommended tracks as a set of track IDs (no `position`). `post_service.py` stops ordering by `position`; the `post_recommended_tracks_table.position` column is left nullable and unused (no destructive migration).
- Contract: `openapi.json` regen in `myblog_backend`, committed in the same PR; workspace merge regenerates `docs/contracts/openapi.json`; frontend `pnpm generate:types` re-run + `api.gen.ts` committed (else deploy CI guard fails — [[feedback-frontend-api-gen-sync]]).

**Verification**:

```
cd myblog_backend && pytest && python -m app.export_openapi   # or repo's regen cmd
cd myblog_front && pnpm generate:types && pnpm lint && pnpm exec astro check
# dev: pick 7 tracks (>old limit), no order shown; save+reload → picks persist
```

**Rollback**: revert the PR; `position` column untouched so old rows are unaffected.

---

### Step 4 — Continuous fractional rating (shared_db → backend → frontend; **cross-repo, strict order**)

Album-only, 0–5, 2-decimal, displayed only as partial-fill stars; number never shown to the reader. **Departs from the prototype** (which shows the number + integer stars) — do not copy `article.jsx` `AlbumHero` rating rendering.

Internal order (each its own PR; migration must reach **prod before** the backend pin bump — [[reference-shared-db-cross-repo-rollout]]):

1. **`myblog_shared_db`** — migration `rating Numeric(3,1) → Numeric(3,2)` (widen scale; range stays 0–5). Apply to prod **before merge** (rollback migration needs human approval, rule #3).
2. **`myblog_backend`** — bump shared_db git pin. API validation already `ge=0, le=5` with no step → accepts 2-decimal values as-is; add a test asserting `4.69` round-trips. No new column.
3. **`myblog_front`** —
   - Writer input: a **drag-continuous** star strip (pointer → value in [0,5], 2-decimal) replacing the `step=0.5` number field; `displayStars` no longer `Math.round`. Author may see the live value while dragging.
   - Display component: a reusable **partial-fill star** (5 stars, fill width = `rating/5 * 100%` via CSS clip/gradient) used by `review-hero.astro` and the writer preview. **Remove** the numeric `{rating}/5` from `review-hero.astro` (80–90).

**Verification**:

```
# shared_db: migration up/down on a scratch DB; psql \d shows numeric(3,2)
cd myblog_backend && pytest -k rating   # 4.69 round-trips
cd myblog_front && pnpm lint && pnpm exec astro check
# dev: drag to ~4.69 → stars ~93.8% filled, NO number anywhere on read page
```

**Rollback**: `Numeric(3,2)→(3,1)` truncates to 1 decimal — lossy; human approval required before any prod down-migration.

---

### Step 5 — Lowfreq Article read-page layout (frontend-only)

Restructure `blog/[slug].astro` (+ extract components as needed) to the prototype layout, reusing the Step 4 partial-star component and the Step 3 pick tracklist:

- Reading **progress bar** (`.prog-bar`, scroll-driven) and **font-size toggle** (sm/md/lg → `document.documentElement.dataset.size`, `--body-size`/`--body-line`).
- **Header**: kicker (genre · publish date · read-time), headline (`clamp(36px,5vw,58px)`), dek (italic), byline.
- **Album hero**: 280px cover + label/year, artist link, album title (italic serif), genre, accent-bordered **score card with partial-fill stars only** (no number, no `/10`).
- **Body**: drop-cap on first paragraph, `h2`, accent pull-quote — applied to the rendered markdown (`Prose`).
- **Track-by-track**: full album tracklist (from the existing album-detail data) with `★` on picks; columns = number, title (+★), duration. **No** rating column or meter.
- Tags / author / related / comments / engagement: **excluded**. `AlbumDetailView` content folds into the new tracklist section (or is replaced).

Per CLAUDE.md DoD: UI change → click through in a real browser; reproduce with realistic data (long titles, many tracks, a Korean-heavy body) — [[feedback-ui-repro-realistic-data]], [[feedback-browser-verify-ui-changes]]. Auth-gated surfaces verified via deployed CSS/JS chunk grep if needed ([[reference-prod-smoke-auth-gated-front]]).

**Verification**:

```
cd myblog_front && pnpm lint && pnpm exec astro check
# dev + Playwright: render 3 published posts (long body / short body / many-track album);
# light + dark; mobile + desktop viewport; assert no numeric rating leaks, ★ picks correct
```

---

### Step 6 — (additive) Accent picker + AlbumDetailView token-ization (frontend-only)

Persisted `--accent` override (localStorage), options `#c8332b / #1f3fa8 / #1f7a4a / #8a5cf0`, wired next to the existing theme select. Replace hardcoded colors in `AlbumDetailView.astro` with `var(--color-*)` so it tracks light/dark. Additive — can land any time after Step 5.

**Verification**:

```
cd myblog_front && pnpm lint && pnpm exec astro check
# dev: switch accent → all accent surfaces update + persist across reload; AlbumDetailView correct in dark
```

---

### Step 7 — (deferred) "Appears On" / participation tracks

Pointer only — **not scheduled in this RFC**. Surfacing tracks where an artist is a non-primary credit needs: (a) verify the absorb worker stores secondary artists in `track_artists` at sync time and populate `role`; (b) a new music query ("tracks where `artist_id` in `track_artists` but not primary"); (c) artist-page "참여 곡" UI. Cross-repo (music + worker + front). Promote to its own RFC when prioritized — [[feedback-alias-search-availability]] (assess search/availability impact before any sentinel/gating).

---

## Open questions

1. **Read-time + kicker metadata** (Step 5) — the header shows genre · publish date · **read-time**. Is read-time computed client-side from body length, or omitted? Blocks Step 5 header. _Default: compute from word count if not provided._
2. **Album tracklist source on read page** (Step 5) — confirm `albumDetail.client.ts` / album-detail endpoint returns the full tracklist with durations at read time (it injects `#albumDetail` today). If durations are missing, the duration column degrades gracefully. Blocks Step 5 tracklist.
3. **Recommended-pick storage** (Step 3) — keep the join table (set semantics, `position` unused) vs. a new representation. _Default: keep table, ignore `position`_ — chosen to avoid a destructive migration.

## Decisions log

| Date       | Decision                                                                                                                                   | Step |
| ---------- | ------------------------------------------------------------------------------------------------------------------------------------------ | ---- |
| 2026-05-31 | Recommended tracks = boolean ★ pick on full album tracklist (no limit, no order, no position)                                              | 3    |
| 2026-05-31 | Rating: 0–5 scale, drag-continuous, stored `Numeric(3,2)` (2 decimals), displayed as partial-fill stars only, number never shown to reader | 4    |
| 2026-05-31 | Read page: core sections only (header / hero / body / tracklist / progress / font-size); tags, author, related, comments, likes excluded   | 5    |
| 2026-05-31 | Publish validation relaxed to 작품 + 본문 required; checklist UI removed                                                                   | 2    |
| 2026-05-31 | Dark mode already shipped — not rebuilt; accent picker is the only theming work (additive)                                                 | 6    |
| 2026-05-31 | "Appears On" participation tracks deferred to a future RFC                                                                                 | 7    |
