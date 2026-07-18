# RFC-ui-surface-unification: album/artist interaction rules + profile polish (areas 4·5·9)

- **Status**: draft
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

**Dead spots (album)**: public review page cover/title (`review-hero.astro:57` — plain `<img>`;
artists ARE linked :92), pocket tray items (remove-only), NowPlaying album text.

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
| NowPlaying | **→ openAlbum** | **→ link (plumb id)** | fix + plumb |
| Lyrics header | n/a | **→ link (plumb id)** | plumb |
| 평가 list | openAlbum ✓ | **→ add artist line** | fix |
| LikedBoard | member modal ✓ | **→ link (id exists)** | fix |
| OverviewDash/Bucket/Stats | member modal ✓ | text (low priority; link where id exists) | opportunistic |

## Steps

Steps 1–3 are front-only and independently mergeable; Step 4 is cross-repo (contract); Step 5 is
front-only. UI changes require real-browser click-through (DoD) and the frontend-design skill.

### Step 1 — profile width + 평가 typography (area 9)
`MemberProfile` container → 1200 always; 평가 list column 680; tokens + shared components;
artist line added if the profile payload already carries it (else deferred into Step 4).
**Verification**: CDP desktop + 390px, light/dark; tab switch shows no width jump.

### Step 2 — album dead-spot fixes (review page, pocket tray, NowPlaying)
**Verification**: click-through each surface; overlay opens with correct data.

### Step 3 — artist quick links (LikedBoard + search album meta) + 404 fallback shell
**Verification**: LikedBoard artist → hub; unknown-artist URL renders shell with live data.

### Step 4 — id plumbing (contract): 오늘의곡 `artist_id`, playback→lyrics chain, 평가 artist
Music/backend response additions → openapi regen in service repo(s) → `tools/merge_openapi.py`
→ front `pnpm generate:types` (api.gen.ts commit). Workspace-first merge order per memory.
**Verification**: openapi-verify CI green; NowPlaying/lyrics header links live.

### Step 5 — ArtistHub layout refresh (rules intact)
Masthead/discography/top-tracks visual pass only.
**Verification**: click-through; honesty-rule elements unchanged (stars only, footnote metrics).

## Open questions

1. **평가 list artist field** — does the profile ratings payload already include artist? Checked
   at Step 1; if absent, moves to Step 4. Blocks Step 1 scope only.
2. **Search album rows** — do unified-search album items carry `artist_id` today? Blocks the
   Step 3 meta-link (falls back to Step 4 if a contract add is needed).
3. **OverviewDash/BucketBoard artist linking** — opportunistic or explicit step? Default:
   opportunistic in Step 3 where ids exist.

## Decisions log

| Date | Decision | Step |
|------|----------|------|
| 2026-07-18 | D4 (owner, pre-session): container 1200px, comfortable inner measure | 1 |
| 2026-07-18 | Owner: dual-modal kept + rule codified; 4 immediate fixes; full id plumbing; 404 fallback shell; honesty rules stay; 680px + token normalization | all |
