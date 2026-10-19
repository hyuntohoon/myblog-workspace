# Front UI/UX + component-structure audit — 2026-10-16

- **Scope:** production `https://www.ratemymusic.blog` (desktop 1440, mobile 390), logged out and as the smoke member; front code at `myblog_front` `origin/main` `e73cbad` (#466).
- **Not covered:** owner-account screens, playback bar / lyrics with Spotify connected, `/write`, `/admin`.
- **No code changed.** Proposals only; owner decisions recorded 2026-10-17 (see last section).
- Shareable version with screenshots: claude.ai artifact (private to the owner) — https://claude.ai/artifact/NgnYVw2XuNpS5kRYrqRFC4

**One line:** the card composition contract (`ARCH-album-card-contract-and-composition`) holds at its core but is leaking outside its boundary; the bigger user-facing problem is that the public site is organised around reviews that do not exist yet (0 published).

## 1. Structure — is the card contract holding?

The design is capability composition, not inheritance: `shared/AlbumCard.tsx` / `shared/TrackRow.tsx` are display primitives declaring `{open, play, add, artistOpen, drag}` (`drag` requires `add` at the type level); domain state lives in adapters (`CatalogAlbumCardAdapter`, `BucketAlbumCardAdapter`, `MemoAlbumCardAdapter`, `EditorialAlbumTargetAdapter`).

**Holding**
- Primitive contract intact; Spotify-only ids only via branded `unresolvedAlbumCardData()`.
- `AlbumCard` used by home rails (NewReleases, ForYou, TodayAlbumBuckit), ReviewCandidates, OverviewDash, SearchPage, BucketBoard, Memo, writer/SubjectHero. `TrackRow` used by AlbumDetailView, AlbumDetail, LikedBoard.

**Leaking**
| Item | Evidence |
|---|---|
| Album tiles bypassing `AlbumCard` (10+; most absent from the RFC's 9-surface inventory) | CanonPage `canon-card`, CollectionView, EditorialHome feature + list, TodayPickHistory, MemberProfile ×2, ReviewsTab, ArtistHub discography `art-disco-cover` + review cards, ReviewsIndex, releaseShared `rcal-card` |
| *Correction 2026-10-19 (front #486)* | Published-review cards in that list are documents, not album tiles: CanonPage `canon-card`, EditorialHome feature + list, ReviewsTab, ArtistHub review cards, ReviewsIndex. RFC `ARCH-album-card-contract-and-composition` §12 keeps them on their document renderer, so for them S1 is met by S2 (cover through `CoverImage`) only. MemberProfile's rating rows are 평가 (album entities), not documents, and stay S1 targets. |
| *Correction 2026-10-19 (front #488)* | Two more rows of that list are not album tiles. TodayPickHistory is the history view of `TodaySongBuckit`: each row is a daily **track** pick (`DailyPickItem` carries `track_id`), RFC `ARCH-album-card-contract-and-composition` open question #1 (2026-08-06) already kept that surface bespoke, and its cover is `home/ui` `Cover`, which delegates to `CoverImage` (S2 met). releaseShared `rcal-card` (`EventCard`) is a release-event card with no cover and no catalog album id (예정 events have no album at all). Its remaining `albumTileGuard` entry (`usage: 1`, same as `TodaySongBuckit`) is a delegate usage, not S1 debt. Two album-entity tiles were missing from the list: the overview 최근 평가 widget (`OverviewDash` `MiniReview`, shipped in #488) and the PocketTray card viewer `pb-card` (own `Cover` + `cover-ph`; the board's `AlbumChip` it mirrors is already on `BucketAlbumCardAdapter`). |
| User-visible consequence | Same album ("Break", 빈지노) has ＋담기 + drag on `/search`, neither on `/artist`. Three different card looks on public pages. Same gap class as #406. |
| Cover-fallback implementations: ~10 (RFC goal: 1) | home/ui `Cover`, member/ui `Cover` + `AlbumArt`, PocketTray `Cover`, `LfCover`, `NpCover`, `LkCover`, `GCover`, ReviewsIndex `Cover`, `CoverArt` in both AlbumCard and TrackCard |
| `shared/TrackCard.tsx` (#417) | Copies AlbumCard internals (`CoverArt`, `actionProps`, `Actions`, most of the CSS). `TrackRow` and `TrackCard layout="row"` overlap. |
| Adapter data loss | OverviewDash hard-codes `artistId: null` (3 branches) and injects `<style>{OVERVIEW_ALBUM_CARD_CSS}</style>` per render |
| Styling debt | 1,059 inline `style={{` · 16 `<style>{` injections · 11 files with CSS-string constants · 11,224 CSS lines |
| Oversized components | BucketBoard 3,603 lines · LyricsViewer 2,120 · NowPlaying 1,439 · PocketTray 1,099 |
| A11y | ReviewsTab cover is a `<div onClick>` — not keyboard-operable |
| Doc drift | `docs/frontend/component-map.md` (verified 08-07, addenda to 08-15) misses 65 later front commits; states member lyrics GET is owner-only, but backend `lyrics.py` GET `/{spotify_track_id}` uses `require_cognito_token` |

**Structural proposals**
- **S1** "Every album tile is `AlbumCard` via an adapter" as a grep guard test (baseline-diffed). Migration order by user impact: ArtistHub discography → Collection → Canon → MemberProfile / ReviewsTab → EditorialHome.
- **S2** One `shared/CoverImage`; the other implementations delegate to it.
- **S3** Extract a `CardShell` (cover, open-hit, actions, meta slots) composed by AlbumCard and TrackCard.
- **S4** One API-response → card-data mapper per type in `lib/`, so per-screen hand mapping cannot drop `artistId`.
- **S5** Session-aware capabilities: logged-out ＋ opens an in-site login-intent sheet; drag disabled when logged out.

## 2. User-facing findings (by severity)

### Critical
1. **Empty front door.** Home hero is the empty state ("첫 평론이 이 자리에 실립니다"); 3 of 5 nav items (Reviews, Best New Music, Canon) are empty; Canon's CTA leads to empty Reviews. The owner has 37 ratings (avg 4.1) but Canon is built at build time from blog `.mdx` reviews only (`pages/canon.astro`), so none of it surfaces.
2. **Logged-out ＋** hard-redirects without warning to the unbranded English Cognito hosted UI; the URL exposes `/admin/callback/`.
3. **Album overlay does not change the URL** — browser Back leaves the page instead of closing it (verified); no share/bookmark.
4. **Developer jargon in UI:** settings ("스코프 세대 없음 · 마지막 probe …"), overview ("+ 컴포넌트 추가"), genres ("포함(containment)"), releases ("관측 기반", "SP / MB / iTunes", "장부").

### High
5. Genre pages are dead ends: no path to the genre's albums (K-Pop 387); subgenres all 0.
6. Search: main / featured artist inverted ("빈지노 feat.어반자카파" for an 어반자카파 track); feature singles labelled 앨범 and ranked above main albums; feature-only artists in artist results; duplicate tracks.
7. Artist page: "20 앨범" of which 17 are SINGLE; feature appearances mixed in; dangling "·" before follower count; "아직 평론 없음" ×20; empty "THE CRITIC'S LENS" above discography.
8. Member album modal header omits the artist (Gemini Rights without Steve Lacy); same rating shown 3×; 3 tiny buttons per track row.
9. Owner shows as "U / @user-0468fd3c"; Collection shows "이름 없는 회원".
10. Terminology: the same 13 albums are "재생 대기열" in the bucket and "평론 대기열" in the overview; members are addressed with 평론 (review) instead of 평가 (rating).

### Medium
11. ＋ button 30×44px, transparent background, border alpha 0.18 — nearly invisible on light covers.
12. No `word-break: keep-all` — Korean breaks mid-word.
13. Floating POCKET pill + gear overlap footer theme select (desktop) and bucket cards (mobile); POCKET has two entry points.
14. Member without Spotify sees "라이브러리를 아직 불러오지 못했습니다 + 다시 동기화" instead of a connect CTA.
15. Collection blank ~0.8 s (`/api/buckets/public` 809 ms), no skeleton; year truncates before artist.
16. `/releases`, `/members`, `/radar`, `/search` not in nav; releases lists 265/month with no filter.
17. Mobile profile tabs (6) overflow with no scroll affordance.
18. Home "0개 장르" (review-derived) contradicts "13 genres · 8,391 albums" right above; a playlist-like entry appears in "오늘, 이 앨범들".

Also seen: English uppercase LOGIN/LOGOUT; faux-italic Korean headings; inconsistent page-header styles; mobile drawer lacks close button / current-page indicator; logged-out cards still `draggable=true`; footer links lack trailing slash. Contrast passed; Lighthouse `/releases` mobile: a11y 96, BP 100, SEO 100.

## 3. Suggested order
1. Wire public surfaces to real data — Canon and home hero from owner ratings ≥4.0; hide or merge empty nav items (#1, #9).
2. Login-intent sheet + overlay Back handling (#2, #3, S5).
3. Copy/terminology sweep (#4, #10).
   - *Shipped 2026-10-18 — front #482:* owner-approved copy list. Settings Spotify standing line without 스코프 세대 / probe (`SpotifyIntegrationTab` now calls the shared `standingLine()`); overview 컴포넌트 → 위젯; genre map containment → 포함 관계; releases calendar/radar without 관측/장부/룩업, source badges spelled out; member-visible 평론 misuse fixed (overview bucket card, search empty heading, 미평론 badge, bucket "이미 들음" dot); header Login/Logout → 로그인/로그아웃. `LikedBoard`'s `평론 쓰기 →` was already owner-only (no change). Prod smoke 32/0.
4. S1 + S2 starting with ArtistHub discography (#7, #8).
   - *Shipped 2026-10-19 — front #483 (first slice, ArtistHub):* the `/artist` discography composes `AlbumCard` through `CatalogAlbumCardAdapter` like `/search` (open, ＋ with the login-intent sheet when logged out, drag when logged in); byline is the year only, album type is the secondary line, the per-card 아직 평론 없음 is gone, grid tracks widened because AlbumCard ellipsizes titles. S2: `shared/CoverImage` is the one image/placeholder/skeleton branch; AlbumCard, TrackCard, `home/ui` `Cover` and ArtistHub's review-card covers delegate to it. `albumTileGuard.test.ts` ratchets per-file legacy cover usages, hand-rolled `cover-ph` and local cover definitions (exact baseline; migrations lower it). Prod smoke 32/0. Remaining S1 order: Collection → Canon → MemberProfile / ReviewsTab → EditorialHome; remaining S2 copies: member/ui `Cover` + `AlbumArt`, PocketTray, `LfCover`, `NpCover`, `LkCover`, `GCover`, ReviewsIndex. Rest of #7 (singles/feature grouping, dangling ·, empty CRITIC'S LENS) and #8 not done.
   - *Shipped 2026-10-19 — front #484 (second slice, Collection):* `/collection` shelf albums compose `AlbumCard` through `CatalogAlbumCardAdapter` (the public projection's `album_id` is the catalog id; the viewer owns no bucket items, so not the Bucket adapter). Owner-approved behaviour change: besides open, ＋ copies into the viewer's own Pocket (login-intent sheet when logged out) and drag works when logged in; the owner's shelf stays read-only. Grid tracks match the `/artist` discography; `albumTileGuard` baseline lost the CollectionView entry. Prod smoke 32/0. #15's second half stays open: a long artist list still clips the year in AlbumCard's one-line byline (owner chose to record, not fix, in this slice). Remaining S1 order: Canon → MemberProfile / ReviewsTab → EditorialHome.
   - *Shipped 2026-10-19 — front #486 (Canon, owner-approved change of approach):* Canon cards are published reviews, so they stay document cards (RFC §12, same as ArtistHub's review cards in #483) and did not move to `AlbumCard`; their two covers now render `CoverImage` with the props `Cover` passed (DOM unchanged). `albumTileGuard` lost the CanonPage entry and pins that Canon uses `CoverImage` and no `AlbumCard`; `CanonPage.test.tsx` covers the populated grid. The populated grid is not reachable in prod (0 평론); it was clicked through locally with an uncommitted fixture. Prod smoke 32/0. Remaining S1 candidates from §1: MemberProfile 평가 rows (next in the audit's order), TodayPickHistory, releaseShared `rcal-card` — check each is an album tile, not a document, before migrating. S2-only document surfaces: ReviewsTab, EditorialHome, ReviewsIndex.
   - *Shipped 2026-10-19 — front #487 (MemberProfile):* the `/members` 평가한 앨범 (`MemberRating`) and 재평가 중 (`MemberRerating`) rows are album entities, so they compose `AlbumCard` (`layout="row"`) through `CatalogAlbumCardAdapter`, like the home 평가 rail. Slots hold display content only (stars + date, the author-only withdrawn score, the 한 줄 감상 marker as the cover badge); the author's controls (수정, comment cell, edit panel, 재평가 취소) sit under the card, indented to its text column, because the slots pass pointer events only to links and buttons. Owner-approved: ＋ / logged-in copy-drag on every row of any profile; the marker moved to the badge corner (bottom-left, tooltip gone). `albumTileGuard` MemberProfile baseline 3 → 1 (the Last.fm now-playing `Cover` is a track, S2) plus a pin. Prod smoke 32/0; prod DOM 46 row cards. The logged-in self view was covered by unit tests, not clicked in a browser. Remaining S1 candidates: TodayPickHistory, releaseShared `rcal-card` (check the type first); S2-only: ReviewsTab, EditorialHome, ReviewsIndex.
   - *Shipped 2026-10-19 — front #488 (overview 최근 평가):* a member's 최근 평가 rows (`SelfDashboard.toMemberReview`, type `평가`) are the same rating rows as #487, so `MiniReview` composes `AlbumCard` (`layout="row"`, 44px cover) through `CatalogAlbumCardAdapter`: eyebrow `평가 · YYYY`, stars as the secondary line, open unchanged; owner-approved ＋ / logged-in copy-drag. The owner's 평론/칼럼 rows keep the bespoke row because a 칼럼 has no album id (the adapter would print its catalog note); their cover moved from `AlbumArt` to `CoverImage` (S2). `toMemberReview` now carries `artist_name` (was `''`). `albumTileGuard` OverviewDash baseline 1 → 0 plus a pin. Prod smoke 32/0. The live widget (own-profile only, logged in) was not clicked; a local harness page in the site layout was, at 1440 and 390. TodayPickHistory and `rcal-card` turned out not to be album tiles (see the §1 correction). Remaining S1 candidate: PocketTray card viewer `pb-card` (owner: record as a remaining candidate, after this slice). S2-only: ReviewsTab, EditorialHome, ReviewsIndex.
5. Small visual batch: keep-all, ＋ contrast, floating overlap (#11–13).
   - *Shipped 2026-10-19 — front #485:* #11: the catalog ＋ on covers has a fixed dark scrim, light ink and a light ring in both themes (every `CatalogAlbumCardAdapter` surface; the coarse-pointer 44px target kept). #12: `body { word-break: keep-all; overflow-wrap: break-word }`, which caused no new overflow at 390 (checked against a control with the rule disabled). #13: owner decision — the Pocket design-settings gear renders only while the tray is open; closed, only the pill remains. Its unscaled offset also clipped the scaled pill by 8px on desktop. The footer half of #13 had already been fixed by front #471. Not done: #13's "POCKET has two entry points". Prod smoke 32/0.

## 4. Owner decisions (decided 2026-10-17)
- **D1 — while 0 평론 exist:** keep the existing line (`FEAT-album-review-authoring` 2026-07-31: 평가 is not an editorial surface; `FEAT-home-redesign` 2026-06-14 #4: 0 평론 → cold-start hero, the owner publishes first). Hide nav items built from 평론 while there are none, and add a **separately labelled** home rail of the owner's 평가. Canon, the hero and `/reviews` stay 평론-only. (The audit's "Canon/hero from owner ratings ≥4.0" proposal in §3.1 is therefore declined.)
- **D2 — Back / album URL:** the album-route decision (2026-07-08, closed again 2026-08-04) is **not** reopened. Opening the overlay pushes a history entry with no URL change, so Back closes it; no share/bookmark. A `?album=` open-on-load parameter would be an album URL in substance and was not chosen. The member `AlbumDetail` modal is a separate host and out of that change.
  - *Shipped 2026-10-18 — front #477:* the overlay shows exactly while the current history entry carries `albumOverlay`; ✕/ESC/scrim consume it, a second album replaces it, Forward and reload re-adopt it. A classic inline head script in `layout.astro` is the first popstate listener and lets the overlay claim the pop, because ClientRouter otherwise re-fetches and swaps the page on a same-URL traverse.
  - *Shipped 2026-10-18 — front #479 (S5, finding #2):* a logged-out ＋ opens an in-site login-intent sheet (Kakao / Google / email, mirroring the header login menu) instead of jumping to the hosted UI; the post-login intent is parked only once a provider is chosen. Catalog album cards are draggable only when logged in. §3 step 2 is complete. Not covered at the time: `AlbumRatingBlock`'s "로그인하고 평가 남기기" button still went straight to `goLogin(true)`.
  - *Shipped 2026-10-18 — front #481 (S5 follow-up):* that button now opens the same login-intent sheet; the `rate-album` intent is parked only once a provider is chosen. Every logged-out login entry in the overlay now goes through the sheet. Prod smoke 32/0.
- **D3 — order:** §3 step 1 first, as an RFC → `docs/rfcs/FEAT-public-surfaces-before-first-review.md`. Finding #9 needs only the owner setting a display name in `/settings` (handle unchanged, so `OWNER_HANDLE` and the member URL are untouched).
