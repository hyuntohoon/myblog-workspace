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
4. S1 + S2 starting with ArtistHub discography (#7, #8).
5. Small visual batch: keep-all, ＋ contrast, floating overlap (#11–13).

## 4. Owner decisions (decided 2026-10-17)
- **D1 — while 0 평론 exist:** keep the existing line (`FEAT-album-review-authoring` 2026-07-31: 평가 is not an editorial surface; `FEAT-home-redesign` 2026-06-14 #4: 0 평론 → cold-start hero, the owner publishes first). Hide nav items built from 평론 while there are none, and add a **separately labelled** home rail of the owner's 평가. Canon, the hero and `/reviews` stay 평론-only. (The audit's "Canon/hero from owner ratings ≥4.0" proposal in §3.1 is therefore declined.)
- **D2 — Back / album URL:** the album-route decision (2026-07-08, closed again 2026-08-04) is **not** reopened. Opening the overlay pushes a history entry with no URL change, so Back closes it; no share/bookmark. A `?album=` open-on-load parameter would be an album URL in substance and was not chosen. The member `AlbumDetail` modal is a separate host and out of that change.
  - *Shipped 2026-10-18 — front #477:* the overlay shows exactly while the current history entry carries `albumOverlay`; ✕/ESC/scrim consume it, a second album replaces it, Forward and reload re-adopt it. A classic inline head script in `layout.astro` is the first popstate listener and lets the overlay claim the pop, because ClientRouter otherwise re-fetches and swaps the page on a same-URL traverse.
  - *Shipped 2026-10-18 — front #479 (S5, finding #2):* a logged-out ＋ opens an in-site login-intent sheet (Kakao / Google / email, mirroring the header login menu) instead of jumping to the hosted UI; the post-login intent is parked only once a provider is chosen. Catalog album cards are draggable only when logged in. §3 step 2 is complete. Not covered at the time: `AlbumRatingBlock`'s "로그인하고 평가 남기기" button still went straight to `goLogin(true)`.
  - *Shipped 2026-10-18 — front #481 (S5 follow-up):* that button now opens the same login-intent sheet; the `rate-album` intent is parked only once a provider is chosen. Every logged-out login entry in the overlay now goes through the sheet. Prod smoke 32/0.
- **D3 — order:** §3 step 1 first, as an RFC → `docs/rfcs/FEAT-public-surfaces-before-first-review.md`. Finding #9 needs only the owner setting a display name in `/settings` (handle unchanged, so `OWNER_HANDLE` and the member URL are untouched).
