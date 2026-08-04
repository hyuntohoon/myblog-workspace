# ARCH-entity-interaction-v2: one canonical definition per entity — identity, URL, open, data, actions, drag payload

- **Status**: accepted (owner approval 2026-08-03, in-session)
- **Owner**: TBD
- **Created**: 2026-08-03
- **Plan row**: `plan.md` → ARCH-entity-interaction-v2
- **Extends** (does not replace): `docs/archive/done/rfcs/ARCH-entity-interaction-contract.md`
  (`TrackRow` + `lib/entityLinks.ts` contract points),
  `docs/archive/done/rfcs/ARCH-entity-interaction-unify.md` (`openAlbum`/`openTrackAlbum` dispatch +
  the app-wide `AlbumOverlay`), `docs/archive/done/rfcs/RFC-ui-surface-unification.md` (the
  public-overlay vs member-modal rule + the surface × treatment table).
- **Consumed by**: `docs/rfcs/FEAT-playback-bucket-player.md` Step 8 (its drop sources need this
  RFC's drag-payload contract; only two surfaces in the product are draggable today).
- **Reopens, with cause**: `ARCH-entity-interaction-contract` OQ2 (`play`/`add` reserved slots) and
  its "no album-detail unification" non-goal; `RFC-ui-surface-unification` owner decision 8 (keep the
  dual album-detail system); `ARCH-entity-interaction-unify`'s "no album detail *route*" decision.
  Each is named individually in the *Comparison table* with what changed since it was taken.

---

## Goal

For each of **album**, **track** and **artist** there is one written, code-enforced definition of:
its **canonical id**, its **canonical URL** (or the explicit decision that it has none), what
**opening** it does, what **data** is displayed, what **actions** are available, and what its
**drag payload** is. Every surface in `myblog_front` conforms to that definition or is listed as a
documented, reasoned exception — no surface invents its own behavior. Most album, track and artist
representations become draggable with a uniform payload, the internal-**move** vs external-**copy/add**
distinction is preserved unchanged, and every drop target declares which of **direct-add**,
**transform** or **reject** it performs for each entity type, with a visible state for each. Mobile
and pointer conflicts (click vs drag vs scroll) are settled by a measured prototype, not by picking a
library. `docs/frontend/component-map.md` carries the resulting contract and is re-stamped.

## Non-goals

- **No backend or contract change unless the audit proves a payload gap.** The three predecessor RFCs
  were front-only; the one that needed ids (`RFC-ui-surface-unification` Step 4) added them
  additively with no migration. Same posture here: a missing id is a flagged, separately-scoped
  contract add, not something smuggled into a refactor.
- **No new entity types.** Album, track, artist. Review, snapshot, playback and research-note
  membership kinds exist and are untouched.
- **No vanilla → React migration for its own sake.** The `/review/[slug]` inline editorial tracklist
  (`scripts/albumDetail.client.ts`, ★ picks + ▶/＋) is a first-class editorial surface, not a
  duplicate — the `ARCH-entity-interaction-unify` Step-2 audit established that deleting it is a UX
  regression. It participates in this contract through the existing window-event bridge idiom
  (`pb:add-track` → `ReviewTrackAdder`), or it is documented as an exception. It does not get rewritten.
- **No monolith splitting** (`BucketBoard.tsx` is 2,752 lines) and no `AddToBucketMenu` /
  `BucketPickerSheet` merge — nothing is blocked by either, and `necessity-gate` applies.
- **No change to the member-writable path's architecture.** The architect rule from
  `ARCH-entity-interaction-unify` Step 1 stands: the `ent:*` event cannot carry writable/bucket
  context, so member surfaces stay on `onOpen(DetailTarget)`. "Unifying" member call sites onto the
  lossy event is explicitly forbidden, not merely unwanted.
- **No playback behavior.** Queue semantics, the play ladder and the player forms belong to
  `FEAT-playback-bucket-player` and `FEAT-member-player`. This RFC defines only the *payload* a
  playback drop consumes and the *action slot* a play affordance occupies.
- **No lyrics-privacy change.** `GET /api/lyrics/{id}` is `require_owner`; the lyrics action slot is
  defined here, its authorization is not.

---

## Current state

Measured 2026-08-03 against `myblog_front/src`. **`docs/frontend/component-map.md` is stale** — see
the last subsection; that staleness is itself evidence that Step 1 must re-measure rather than copy.

### Entity definitions today — three different shapes

| | Album | Track | Artist |
|---|---|---|---|
| Canonical id | DB uuid `albumId`; `spotifyAlbumId` on some payloads; **null** = not in catalog | DB uuid `trackId`; `spotify_id` on some; **null** = Spotify-only hit | DB uuid; **often absent** from payloads |
| Canonical URL | **none** — no `/album/[id]` route (owner decision 2026-07-08) | **none** | `/artist/[id]/` — trailing slash canonical (`artistHref`) |
| Open behavior | **three paths**: `openAlbum` event → app-wide read-only `AlbumOverlay`; `onOpen(DetailTarget)` → member writable `AlbumDetail`; the `/review/[slug]` **inline editorial tracklist** (vanilla, always visible, not a modal) | `openTrackAlbum` → the album overlay (public bespoke rows); `TrackRow.open` → the member modal (LikedBoard) | route navigation |
| Actions | 담기 (`AddToBucketMenu` / `BucketPickerSheet`), 이 앨범 재생 ▶ (`sendConnectPlay`, member-only), 평론 후보 mark | 가사 (`TrackRow.lyrics` → `LyricsSheet`), ▶ (review tracklist + pocket tray only), ＋ (review tracklist), ★ (writer) | — (navigate only) |
| Drag payload | `DndItem` from **two surfaces only** | same `DndItem`, `trackId` set | same `DndItem`, `artistId` set |

### Drag exists on exactly two surfaces

Repo-wide `draggable` grep: `BucketBoard.tsx:569` (member chip), `BucketBoard.tsx:965` (bucket node),
`PocketTray.tsx:435` + `:589` (tray member). **Nothing else in the product is draggable** — not
search cards, not the album overlay, not `ArtistHub`, not the review page, not `NowPlaying`, not
`LikedBoard`, not the home strips, not `/releases/`.

The payload is `DndItem` (`lib/boardDnd.ts:23`):

```ts
interface DndItem { kind: 'album' | 'bucket', itemId?, fromBucketId?, bucketId?, copy?,
                    albumId?, fromLib?, source?, trackId?, artistId?, srcItemType? }
```

Note `kind: 'album' | 'bucket'` is a **misnomer** — `kind:'album'` means "a bucket member of any
`srcItemType`", so an artist member drags as `kind:'album'` with `srcItemType:'artist'`. Any new
external drag source inherits this confusion unless the payload is renamed.

### The move/add/transform/reject rules already exist and work

`lib/boardDnd.ts` (102 lines, extracted by `REFACTOR-frontend-member-surface` Step 4a specifically so
these are unit-testable) is the **single source of drop semantics** for the board card, the trash
dock, and the reverse-DnD Pocket bridge. It already encodes all four states the brief asks for:

- **direct-add** — General bucket, matching type → `copyAlbum` / `insertAlbum`.
- **transform** — Artist bucket + album/track source → `expandSource` (album/track → **credited
  artists**). The source row is never stored; the original is never removed.
- **reject** — `canAcceptAlbumDrag` returns false → no glow, no optimistic insert, and (the D-series
  invariant) the target **stays in place, muted** — the tray must not reflow during a drag.
- **internal move vs external copy/add** — `copy` (recent-plays strip) and `fromLib` (the
  sync-owned library bucket) drop as a **COPY**; a real member with `fromBucketId !== target.id`
  drops as a **MOVE** (`insertAlbum`). Same-bucket drops are guarded so they do not persist a
  spurious reorder.

`lib/pocketBuckit/boardDnd.ts` mirrors the accept-gate for the Pocket island (two React roots cannot
share the payload, so a window event carries it) and explicitly re-checks authoritatively on drop.

**This is the asset of this RFC, not its problem.** The rules are right; they are reachable from two
surfaces.

### Non-drag path already exists and is the primary path on touch

`AddToBucketMenu` (`components/member/pocket/AddToBucketMenu.tsx`, 281 lines) is the WCAG 2.5.7
non-drag peer — self-styled, `member.css`-independent so it works on any surface, with a logged-out
`pb:resume` intent handoff (`lib/pocketBuckit/intent.ts`, tagged union over `album | track | review`,
single-drain, TTL-bounded). `BucketPickerSheet` is the member-only variant. FEAT-pocket-buckit's
cross-cutting rule stands: **no default may depend on HTML5 drag**.

### The album-detail situation, stated accurately

The brief asks to "explicitly revisit the previous decision to retain two album-detail systems."
That decision has been taken **and re-affirmed twice**, and what exists now is not what the phrase
suggests:

1. `ARCH-entity-interaction-contract` (2026-07-03) non-goal: "No album-detail unification… the
   difference is intentional per-context behavior, not drift."
2. `ARCH-entity-interaction-unify` (2026-07-08) **partially resolved it**: Step 1 extracted the shared
   read-only `components/album/AlbumDetailView.tsx`, used by **both** the app-wide `AlbumOverlay`
   (public, event-opened) and the member writable `AlbumDetail` (memo/edit stay member-side). The
   component-map's "load-bearing duplication #1" was struck as *resolved*.
3. `RFC-ui-surface-unification` (2026-07-18, owner decision 8) re-affirmed the split and **codified
   the rule** instead: *public/read contexts open the shared overlay; dashboard work contexts open
   the member modal; the overlay is the default for anything new.*

So today it is **one shared read body, two hosts** (differing in whether they can carry writable
bucket context), plus a **third, genuinely different surface** — the review page's inline editorial
tracklist. The honest open question is not "merge two duplicates" (they are already merged where they
can be) but: **does the read-only host and the writable host need to be two components at all, now
that the read body is shared?** The architect rule says the *event* cannot carry writable context —
it does not say the *component* cannot. That is the question Step 2 answers, with the answer allowed
to be "no change".

There is a smaller, concrete duplication the map does flag and which is *not* resolved: the member
`AlbumDetail`'s `MemoWindow` replaced `TrackRow` with its own `memo-trow`, so **the lyrics affordance
exists twice, hand-rolled** — "a place a change must be made twice."

### Component-map is stale — measured

`docs/frontend/component-map.md` is stamped **2026-07-08** and states artist names are "**Not
linkable** (payload carries names only, no artist ids): `NowPlaying`, `LikedBoard` rows". Both are
false as of today:

- `components/member/NowPlaying.tsx:43` imports `artistHref`; `ArtistNames` (`:761`) renders real
  links at `:949` and `:999` (shipped in FEAT-member-player #293, 2026-07-19).
- `components/member/LikedBoard.tsx:15,39,91,318` carries `artistId` from `SavedTrackItem.artist_id`
  and links it (shipped in `RFC-ui-surface-unification` Step 4, front #299, 2026-07-21).

The map's own rule — "a stale Verified stamp is the signal to re-verify, not to trust" — applies.
**Step 1 re-measures every row; nothing is copied forward.**

### Interaction-conflict surface (unmeasured today)

Nothing in the product currently has to resolve click-vs-drag-vs-scroll, because the two draggable
surfaces are grid tiles and list rows inside scroll containers that were built around them. Making a
search result card, a home strip tile, a review-page track row and a player queue row all draggable
introduces conflicts that **have not been measured here**:

- HTML5 native DnD has **no touch support** — `BucketBoard` already falls back to `ActionSheet`.
- A drag threshold on a horizontally-scrolling home strip competes with the scroll gesture.
- The lyrics viewer's vertical drag is already line-stepping (FEAT-lyrics-viewer-playback chose a
  full-screen queue swap over a sheet **for exactly this reason**) — a precedent that gesture
  collisions in this product are resolved by changing the surface, not by tuning thresholds.

---

## Step 1 audit — measured 2026-08-04

Measured against `myblog_front` **`origin/main` = `40f27a6`**, read from an isolated worktree (the
shared checkout was 5 commits behind and would have produced stale citations). Nothing below is
copied from `component-map.md`; every row is a fresh read, and every `path:line` in this section was
re-verified by printing the cited line after the table was written.

**The re-measure was not a formality — this RFC's own *Current state* is already stale.** The drag
inventory it records as `BucketBoard.tsx:569` / `:965` and `PocketTray.tsx:435` / `:589` is now
`:580` / `:981` and `:444` / `:641`. The *set* of draggable surfaces is unchanged (two), so the
conclusion drawn from it stands — but four of five cited line numbers had moved in one day. Line
citations in this lineage decay within a single step; Step 6's re-stamp of `component-map.md` should
prefer symbol names over line numbers wherever a symbol exists.

### A. Album representations

`open` values: **overlay** = app-wide read-only `AlbumOverlay` via `openAlbum`; **modal** = member
writable `AlbumDetail` via `onOpen(DetailTarget)`; **nav** = page navigation; **none** = inert.
`add` = 담기 (`AddToBucketMenu` / `BucketPickerSheet`). `drag` = HTML5 `draggable`.

| # | Surface | Cite | Album id in payload | Open | Actions | Drag |
|---|---|---|---|---|---|---|
| A1 | Home 신보 카드 | `home/NewReleasesCard.tsx:91` (artist `:102`) | DB `album_id` | overlay | — | no |
| A2 | Home 오늘의 앨범 | `home/TodayAlbumBuckit.tsx:65` (artist `:74`) | DB `album_id` | overlay | — | no |
| A3 | Home For-You 신보 | `home/ForYouReleasesCard.tsx:92` (artist `:98`) | DB, **non-null asserted** (`it.album_id!`) | overlay | — | no |
| A4 | Home 오늘의 곡 (앨범으로) | `home/TodaySongBuckit.tsx:147,155` (artist `:161`) | DB `album_id` | overlay | — | no |
| A5 | Home 오늘의 곡 히스토리 | `home/TodayPickHistory.tsx:99,108` (artist `:113`) | DB `album_id` | overlay | — | no |
| A6 | 발매 이벤트 (캘린더 · 레이더) | `releases/releaseShared.tsx:212-214` (artist `:260`,`:294`) | **Spotify id**; DB id resolved async on click, and on miss the **Spotify id is passed as `albumId`** | overlay | — | no |
| A7 | 검색 앨범 카드 | `search/SearchPage.tsx:73-85` (artist `:87`) | DB, **nullable** → static figure | overlay | — | no |
| A8 | 헤더 검색 앨범 행 | `search/HeaderSearch.tsx:131-138`, `:154` | DB, **nullable** → keyboard target is `null` | overlay | — | no |
| A9 | 아티스트 허브 디스코그래피 | `artist/ArtistHub.tsx:253-269` | DB, **nullable** → static div | overlay | — | no |
| A10 | 평론 페이지 히어로 앨범 | `pages/review/[slug].astro:96,181,212,901-904` | DB `post.albumIds[0]` | overlay | **add** (`:238`) | no |
| A11 | `/collection` 공개 컬렉션 | `collection/CollectionView.tsx:80` | DB `albumId` — **present** | **none** | **none** | no |
| A12 | Canon 카드 | `canon/CanonPage.tsx:20` | **absent** (`lib/reviews.ts:10-31`) | nav → review | — | no |
| A13 | 평론 인덱스 · 홈 평론 행 | `reviews/ReviewsIndex.tsx:209,229,245,368,386`; `home/EditorialHome.tsx:103,151` | **absent** | nav → review | — | no |
| A14 | 검색 평론 카드 | `search/SearchPage.tsx:27`; `search/HeaderSearch.tsx:152` | **absent** | nav → review | — | no |
| A15 | **Buckit 보드 멤버 칩** | `member/BucketBoard.tsx:580` | `BoardAlbum.albumId`, **nullable** (`lib/buckets.ts:45`) | modal `:627` (artist → hub `:621`; other kinds → no-op `:625`) | ✎ 평론표시 `:684`, ⋯ 액션시트 `:700`, ▶ `:2701` | **yes** — `DndItem` `:583`/`:585`/`:589` |
| A16 | **Pocket 트레이 리스트 행** | `member/pocket/PocketTray.tsx:641` | `BoardAlbum.albumId`, nullable | overlay `:661` | ▶ `:665` (owner), − 제거 `:658` | **yes** — window event `:644` |
| A17 | **Pocket 카드 뷰어 타일** | `member/pocket/PocketTray.tsx:444` | 〃 | artist → hub `:597`, album → overlay `:599` | − 제거 `:612` | **yes** — `dragBind` `:443-459` |
| A18 | 공개 앨범 오버레이 (본체) | `album/AlbumOverlay.tsx` + `album/AlbumDetailView.tsx` | given | — | ▶ `:72-82` (logged-in only), 평가 블록; **가사 없음** | no |
| A19 | 멤버 앨범 모달 (본체) | `member/AlbumDetail.tsx` (same shared body) | given | — | 가사(트랙별), 메모, 평가, 평론 보기 `:110` | no |
| A20 | NowPlaying 현재 앨범 | `member/NowPlaying.tsx:216,224` | DB | overlay | — | no |
| A21 | NowPlaying 최근 들은 앨범 | `member/NowPlaying.tsx:1564` | DB `it.album_id` | overlay | — | no |
| A22 | 재생 패널 — 앨범 정보 | `member/playback/PlaybackPanel.tsx:103-111`, `:193` | `trackAlbumId ?? albumId` | overlay | 가사 `:191`, 트랙 정보 `:192` | no |
| A23 | 평론 후보 카드 | `member/ReviewCandidates.tsx:24` (artist `:42`) | DB | overlay | 평론 쓰기 `:59` | no |
| A24 | 멤버 프로필 평가 목록 | `member/MemberProfile.tsx:304,314` (artist `:326`) | DB | overlay | — | no |
| A25 | 평론 탭 | `member/ReviewsTab.tsx:50-56` | DB `r.albumIds[0]` | overlay | 보기 `:105` | no |
| A26 | 스포티파이 임포트 분석 | `member/ImportAnalysis.tsx:468` | DB `target.id` | — | **add** | no |
| A27 | LikedBoard 카드 커버 | `member/LikedBoard.tsx:312` | DB, nullable → disabled | modal | ⋯ 메뉴 `:328` | no |

### B. Track representations

| # | Surface | Cite | Track id in payload | Open | Actions | Drag |
|---|---|---|---|---|---|---|
| B1 | 앨범 트랙리스트 (공유 본문) | `album/AlbumDetailView.tsx:56-73` | DB `t.id` + `t.spotify_id` | — | **가사만**, and only when the host passes `onOpenLyrics` (`:70`) — public omits it | no |
| B2 | LikedBoard 리스트 행 | `member/LikedBoard.tsx:280-299` | **Spotify id only** (`LikedRowVM.id`, `:34-36`) — no DB track id | 앨범 modal `:294` | 가사 `:295`, ⋯ `:297` | no |
| B3 | 멤버 메모창 `memo-trow` — **TWIN 1** | `member/AlbumDetail.tsx:429` | DB | whole row = 가사 | 가사 | no |
| B4 | 평론 페이지 인라인 트랙리스트 (vanilla) — **TWIN 2** | `scripts/albumDetail.client.ts:58-71` | DB `t.id` | — | ▶ `:58`, ＋▶ 다음에 듣기 `:64`, **＋ 담기** `:69` → `pb:add-track` `:176` | no |
| B5 | 검색 트랙 행 | `search/SearchPage.tsx:95-132`; `search/HeaderSearch.tsx:139-146` | `TrackHit.id` nullable, **unused** | **앨범** overlay (never the track) | — | no |
| B6 | 아티스트 허브 주요 트랙 | `artist/ArtistHub.tsx:280-294` | not carried | **앨범** overlay | — | no |
| B7 | 재생 큐 행 | `member/playback/PlaybackPanel.tsx:239-255` | `BoardAlbum.trackId` | — | ▶ `:239`, × 제거 `:255` | no |
| B8 | 가사 뷰어 큐 | `member/lyrics/LyricsViewer.tsx:274` | DB | tap → jump | — | no |
| B9 | 라이터 추천 트랙 ★ | `writer/RecommendedTracksBlock.tsx:71` | DB | — | selection toggle (different semantic) | no |

**B4 is the most action-dense track row in the product and the only place a track can be 담기'd —
and it is unreachable in prod** (zero published reviews; measured below). Every reachable track row
today offers at most 가사.

### C. Artist representations

| # | Surface | Cite | Artist id in payload | Open | Drag |
|---|---|---|---|---|---|
| C1 | `/artist/[id]/` hub | `lib/entityLinks.ts:14` | — (route param) | canonical URL, trailing slash | no |
| C2 | 링크로만 등장하는 이름 — the catch-all row: **19 `artistHref(` call sites across 16 files**, C3/C4/C6/C7 included | `grep -rn "artistHref(" src` | DB, mostly nullable → plain text on null | nav → hub | no |
| C3 | **Buckit 보드 아티스트 멤버** | `member/BucketBoard.tsx:619-622` | `BoardAlbum.artistId` (`buckets.ts:58`) | nav → hub | **yes** |
| C4 | **Pocket 트레이 아티스트 멤버** | `member/pocket/PocketTray.tsx:596-597` | 〃 | nav → hub | **yes** |
| C5 | 검색 아티스트 카드 | `search/SearchPage.tsx:45` | nullable → `href` undefined (**dead card, deliberate**) | nav → hub | no |
| C6 | NowPlaying 아티스트명 | `member/NowPlaying.tsx:1009-1039` | **not in the payload** — resolved async per render via `resolveDbArtistId` `:1018` | nav → hub when resolved, else plain text | no |
| C7 | AlbumDetailView 아티스트 블록 | `album/AlbumDetailView.tsx:88-99` | DB `ar.id` | nav → hub | no |
| C8 | 레이더 추적/후보 아티스트 | `releases/ReleaseRadar.tsx:328-338` | DB `c.artist_id` — **present** | **none** — `artistHref` count in this file is **0** | no |
| C9 | 라이터 작품 검색 결과 | `writer/ArtistDetail.tsx:107,123,153` | DB | — (selection: `onPickArtist`/`onPickTrack`/`onPickAlbum`) | no |

### D. Drag inventory — exact and grep-reproducible

```
grep -rn "draggable" myblog_front/src --include='*.tsx' --include='*.astro' --include='*.ts'
```
returns 9 hits at `origin/main` `40f27a6`; **4 are live drag sources**, and they are the RFC's two
surfaces:

- `BucketBoard.tsx:580` (member chip) · `:981` (bucket node — a container, not an entity)
- `PocketTray.tsx:444` (card-viewer tile) · `:641` (list row)

The other 5 are non-sources: `BucketBoard.tsx:691`,`:706` are `draggable={false}` (the ✎ and ⠿
buttons opting **out** so a tap on them is not a drag start), and three are prose in comments
(`genres/gm-shared.tsx:83`, `PocketTray.tsx:439`, `writer/WriterApp.tsx:26`). Any Step-5 grep gate
must diff against this baseline rather than assert an absolute count
(memory `feedback-grep-gate-needs-baseline-diff`).

### E. Payload-gap list — flagged, not fixed

Each gap is stated as *the action it blocks*, with a reproducing grep. **None is fixed in this step.**

| # | Gap | Blocks | Reproduce |
|---|---|---|---|
| G1 | **Build-time `ReviewCard` carries no album or artist id** — only `slug` + display strings | A12/A13/A14 can never open an album, be dragged, or be 담기'd. This is the largest single class: every editorial surface on the public site | `grep -n "interface ReviewCard" -A 22 src/lib/reviews.ts` → no `*Id` field. Contrast `lib/member.ts:47`'s `MemberReview`, which **does** carry `albumIds` (used at `ReviewsTab.tsx:50`) — the member side of the same content already has the id the public side lacks |
| G2 | **`LikedRowVM` has no DB track id** — `id` is the Spotify track id | B2 cannot 담기 a track (`addBucketTrack` needs a DB id) and cannot become a track drag source; only the album path via promote works | `grep -n "interface LikedRowVM" -A 24 src/components/member/LikedBoard.tsx` |
| G3 | **Search `TrackHit.id` is carried but never used**; the row opens the album instead | B5 cannot address the track it displays | `grep -n "openTrackAlbum(t" src/components/search/*.tsx` — both call sites pass `t.albumId`, never `t.id` |
| G4 | **Release events carry a Spotify album id, not a DB id**, and the async resolve **falls back to passing the Spotify id into `albumId`** | A6 can hand the overlay an id from the wrong namespace on a resolve miss — an id-*type* conflation, not merely a missing id | `sed -n '212,214p' src/components/releases/releaseShared.tsx` |
| G5 | **`NowPlaying` artist ids are absent from the payload** and resolved per-render | C6 cannot be a drag source without a network round-trip first | `sed -n '1009,1022p' src/components/member/NowPlaying.tsx` |
| G6 | **`ArtistHub` top tracks carry no track id** | B6 cannot address the track | `sed -n '280,294p' src/components/artist/ArtistHub.tsx` |

Two more findings are **not** payload gaps — the id is present and the surface simply does nothing
with it. They are cheaper to close than G1–G6 and are handed to Step 5, not to a contract change:

- **A11 `/collection`** — 48 album covers on prod carrying `albumId`, with **zero** interactive
  descendants (measured below). The richest inert album surface in the product.
- **C8 `ReleaseRadar`** — the only artist surface that holds `artist_id` and renders **no hub link**;
  every other artist name in the product links. `grep -c artistHref` on that file returns `0`.

### F. Real-browser spot-check — prod, 2026-08-04

Six checks on `https://www.ratemymusic.blog`, chosen to test claims that a code read could get wrong
(not to re-confirm ones it settles). All ran logged out.

| Surface | Claim tested | Measured |
|---|---|---|
| `/collection/` | A11 is fully inert | **48 `<figure>`, 0 clickable descendants, 0 draggable, `cursor:auto`** — confirmed |
| `/search/?q=radiohead` | album/track/artist row behavior + no add/drag | 20 album cards, all with open buttons; **20 track rows, all labeled "앨범 상세 보기"**; artist links all trailing-slash; **draggable 0, 담기 0** |
| album overlay (opened from search) | public overlay grants no lyrics/add/drag | buttons = **닫기, 로그인하고 평가 남기기** only; 가사 0; draggable 0; artist link present |
| `/artist/<id>/` | discography + top tracks open the album, never the track | 1 clickable disco item, 1 top track labeled "**앨범** 상세 보기"; draggable 0, 담기 0 |
| `/releases/` | A6's open affordance | **52 artist links**, and **0 album-open buttons** — the default view's events have no `spotify_album_id` yet, so they are album representations with *no id at all* |
| `/` (home) | home tiles + review reachability | 12 `.nrl-open` + 4 `.otd-open` album tiles, each with an artist link; draggable 0, 담기 0; **`a[href^="/review/"]` = 0** |

**Scope of this evidence, stated plainly.** The six checks cover the public side. The two draggable
surfaces (A15–A17, C3–C4) are **member-only and were measured from source, not in a browser** — a
prod board would have to be populated for the drag nodes to exist at all, and Step 3's verification
already mandates a full CDP board+tray drag matrix. That is where the browser confirmation belongs;
it is deferred deliberately, not skipped.

**The zero-review finding is load-bearing, not trivia.** `a[href^="/review/"] = 0` on the home page
confirms prod still has no published review, which means **A10 and B4 — the only public 담기 surface
and the only track-담기 surface in the entire product — cannot be exercised by anyone today.** Any
Step-5 claim of "most representations are draggable/addable" that counts those two is counting
surfaces no user can reach.

### G. External patterns — extended, not repeated

The prior analyses stand and are not re-run: FEAT-pocket-buckit's conclusions on Spotify's overloaded
"Add" and its churning queue, and `FEAT-playback-bucket-player` Step 6's four-service comparison
(Genius / Apple Music web / SoundCloud / Bandcamp measured; Spotify web + YouTube Music left
**unverified behind login walls**). What this step adds is the one thing those did not cover — **drag
semantics** — measured on the closest product analogue.

**Are.na `/explore`, logged out, 2026-08-04 (measured):**

- **Every content card is `draggable="true"` — 12/12 on the page**, blocks and channels alike. Drag
  is not an affordance granted to a privileged surface; it is the default state of a representation.
- The draggable node is the **card container wrapping the `<a href>`**, not the image — so click
  (navigate) and drag live on the same node, resolved by native HTML5 DnD. This is the identical
  mechanism `BucketBoard.tsx:617-618` already relies on and documents ("a drag never fires a click").
- Each card carries a **named non-drag peer action, "Connect"** — drag and the explicit button
  coexist rather than substitute.
- **At 390×844 with touch emulation, `draggable="true"` drops to 0 while the cards remain
  (6 block + 10 channel) and "Connect" survives.** Verified this is not a render failure by counting
  the cards in the same pass.

That last measurement is the one that matters here: the closest analogue to this product **abandons
drag entirely on touch and keeps the named button as the sole path** — it does not implement a
long-press drag. That is external corroboration for OQ4's recommended default (`AddToBucketMenu` as
the touch path), and it lowers the burden on Step 4: the prototype must still measure the *desktop*
threshold-vs-scroll conflicts, but "long-press drag on mobile" now needs a positive reason to exist
rather than merely failing to be ruled out.

Not measured, with the reason: Spotify web and YouTube Music (login wall — same boundary Step 6 hit);
Finder and Yoink (native macOS, no instrumentation path from here). Their drag conventions are
well-established but would be assertion, not measurement, and this RFC does not launder the two.

### H. What this feeds forward

- **Step 2 (E1/E3)** inherits three id shapes that must appear in the canonical definitions:
  nullable DB id (the common case), Spotify-id-in-an-`albumId`-slot (G4), and id-resolved-async
  (G5). "Canonical id" cannot be a single field name.
- **OQ1 (album URL)** gains a concrete argument it did not have: G1 means the *public editorial*
  surfaces — the ones an album URL would most serve — cannot address an album at all today. The
  question is therefore partly "add a route?" and partly "put an id in the frontmatter payload?",
  and the second is cheaper and independently useful. Still the owner's call.
- **OQ3 (how far "most" goes)** now has a measured exclusion list: selection-mode surfaces (B9, C9)
  and keyboard command rows (A8, B5 via `HeaderSearch`), matching the recommended default.
- **Step 5** starts from **two** free wins that need no contract change — A11 `/collection` and
  C8 `ReleaseRadar` — and from the knowledge that its headline surfaces (A10, B4) are prod-unreachable.

---

## Target state

### E1 — canonical entity definitions (written here, enforced in code)

One table per entity covering: canonical id + null semantics, canonical URL (or "none, by decision"),
open behavior, displayed data, action set, drag payload. Produced by Step 2 from Step 1's audit,
recorded in this RFC **and** in `component-map.md`.

### E2 — one drag payload

`lib/entityDrag.ts` — a single typed payload used by every draggable representation:

```ts
type EntityRef =
  | { entity: 'album',  albumId: string,  title, artist, cover }
  | { entity: 'track',  trackId: string,  albumId: string | null, title, artist }
  | { entity: 'artist', artistId: string, name, image }

type DragPayload = {
  ref: EntityRef
  /** internal = a real bucket membership (MOVE default); external = any other surface (COPY/ADD). */
  origin: { kind: 'internal', itemId: string, fromBucketId: string } | { kind: 'external' }
}
```

- **The move/add distinction is preserved by construction**: `origin.kind` carries it, replacing
  today's implicit `copy` / `fromLib` / `fromBucketId` triad.
- `DndItem` is **adapted, not deleted** — `boardDnd.ts`'s rules are correct and unit-tested; Step 3
  introduces an adapter both ways so board behavior is provably byte-identical before any surface is
  rewired. Renaming `kind:'album'` (which really means "a member of any type") is part of Step 3.
- **A null id is non-draggable**, not a crashing drag — the `openTrackAlbum` no-op precedent
  (`ARCH-entity-interaction-unify` OQ4) extended to drag.

### E3 — drop-target declarations

Every drop target declares, per entity type, one of **direct-add** / **transform** / **reject**, and
each has a required visible state:

| State | Visual contract | Existing precedent |
|---|---|---|
| direct-add | target highlights, verb visible | General bucket `add` |
| transform | target highlights **and names the transform** (`앨범 → 트랙 14곡`) | Artist bucket album→artists |
| reject | target **stays in place**, muted, with a concise reason — never hidden, tray never reflows | `canAcceptAlbumDrag` false branch |

Known targets and their matrix — General bucket, Artist bucket, Playback Bucket, trash dock, bucket
node — filled in Step 2. The Playback Bucket's row is *specified* by
`FEAT-playback-bucket-player` and *consumed* here.

### E4 — action slots opened

`TrackRow`'s `play` and `add` slots — reserved since `ARCH-entity-interaction-contract` OQ2 pending a
product decision — are **granted** by this RFC's owner-approved scope, and `drag` joins them. Track
row actions become `{lyrics?, open?, play?, add?, drag?}`. The two hand-rolled twins (`memo-trow`,
review tracklist) are either brought onto the contract or listed as reasoned exceptions with a
revival trigger — no fake unification (the `ARCH-entity-interaction-contract` house rule).

### E5 — mobile and pointer conflicts, settled by measurement

A prototype, not a library choice, decides: the pointer-drag threshold that coexists with vertical
and horizontal scroll, and the non-drag equivalent on touch. The default candidate is the shipped
`AddToBucketMenu` (already the WCAG primary path); the prototype's job is to prove or refute that it
covers the new surfaces, and to measure whether a long-press drag can coexist with the scroll
containers those surfaces live in.

---

## Comparison table — existing decision / retained / superseded / new

| # | Existing decision | Source | Verdict | What this RFC does |
|---|---|---|---|---|
| 1 | `lib/entityLinks.ts` is the artist/review href contract point; trailing slash canonical | contract Step 3 | **Retained** | Extended, not replaced |
| 2 | `openAlbum` / `openTrackAlbum` window events; album/track have **no route** | unify Step 1/3 | **Retained** (the overlay); **URL question reopened with cause** | unify called an album route "a possible later RFC, not here" — the brief asks to define canonical URLs, so this *is* that later RFC → **OQ1** |
| 3 | Artist click → route `/artist/[id]` | unify | **Retained unchanged** | The one entity whose canonical URL is settled |
| 4 | Member surfaces stay on `onOpen(DetailTarget)`; the `ent:*` event cannot carry writable context | unify Step 1 architect rule | **Retained — load-bearing** | Constrains E1; "unifying" member call sites onto the event stays forbidden |
| 5 | Null ids are first-class; non-navigable entities no-op rather than crash | unify OQ3/OQ4 | **Retained, extended to drag** | A null-id entity is non-draggable |
| 6 | Read-only album body shared (`AlbumDetailView`); duplication #1 struck as resolved | unify Step 1 | **Retained** | The revisit starts from this state, not from "two duplicate modals" |
| 7 | **Keep the dual album-detail system**, codify the rule instead | ui-surface-unification owner decision 8 | **Reopened with cause; outcome open** | What changed: the read body is now shared (#6) and drag is about to be added to every album representation. Step 2 answers "two hosts or one"; "no change" is an allowed answer → **OQ2** |
| 8 | The `/review/[slug]` inline editorial tracklist is a **distinct surface**, not a duplicate; deleting it regresses UX | unify Step-2 audit | **Retained unchanged** | Participates via the event bridge or is a documented exception; never rewritten |
| 9 | `TrackRow` `play`/`add` are **reserved slots**; granting them is a product decision needing approval | contract OQ2 | **Superseded by owner product scope** | The brief's "most representations should support drag and drop" + playback drops *is* that approval. Slots open; `drag` added |
| 10 | Vanilla review tracklist excluded from `TrackRow`; **revival trigger = a track action that must ship on the public review page** | contract non-goal | **Trigger fires — evaluated, not auto-executed** | Drag on public track rows meets the stated trigger. Step 4 decides bridge-vs-adopt; the non-goal against gratuitous migration still holds |
| 11 | Internal **MOVE** default + external **ADD/COPY**; conversion preserves the original; bucket-local Undo | pocket-buckit D-series | **Retained — explicitly preserved** | Encoded structurally in `DragPayload.origin` instead of inferred from three flags |
| 12 | Reject state: target **stays in place**, muted, reasoned; the tray never reflows mid-drag | pocket-buckit D-series | **Retained as a hard visual invariant** | Becomes a required declaration per target × entity |
| 13 | Cross-type 1:N expansion requires **mandatory confirmation** | pocket-buckit D8 | **Retained as the general rule**; superseded **only** for an intentional Playback-Bucket drop | The exception is scoped and owned by `FEAT-playback-bucket-player` OQ3, not generalized here |
| 14 | No default may depend on HTML5 drag; `AddToBucketMenu` is the WCAG 2.5.7 **primary** path on touch | pocket-buckit | **Retained — binding** | E5's prototype must prove coverage, not replace the principle |
| 15 | `boardDnd.ts` is the single source of drop semantics, pure + unit-tested | REFACTOR-frontend-member-surface 4a | **Retained** | Payload is adapted around it; the rules are not rewritten |
| 16 | Two "add to bucket" flows (`AddToBucketMenu` / `BucketPickerSheet`) stay separate — nothing blocked | contract non-goal + component-map #2 | **Retained** | Necessity gate: no merge without a named concrete harm |
| 17 | `component-map.md` is the contract registry; a stale stamp means re-verify | ARCH-frontend-component-map | **Retained, and enforced** | Measured stale today (NowPlaying/LikedBoard artist links). Step 1 re-measures; Step 6 re-stamps |
| — | **One typed drag payload across all surfaces** | — | **NEW** | `DndItem` is board-internal and its `kind` is a misnomer |
| — | **Most album/track/artist representations draggable** | — | **NEW** | Exactly 2 surfaces are draggable today |
| — | **Per-target × per-entity direct-add / transform / reject declaration** | — | **NEW** | The three states exist in code but are implicit and General-vs-Artist only |
| — | **Canonical URL decided per entity** (incl. "none, by decision") | — | **NEW** | Never written down; artist has one by accident of being a route |
| — | **Measured click/drag/scroll conflict resolution + mobile equivalent** | — | **NEW** | Never measured; the only precedent is "change the surface" (lyrics queue swap) |

---

## Steps

One step per session (hard rule #4). Steps 1–3 are the prerequisite block for
`FEAT-playback-bucket-player` Step 8.

### Step 1 — full surface re-audit (docs-only, measurement) — ✅ **DONE 2026-08-04**

Results: **§Step 1 audit — measured 2026-08-04** above (matrix A/B/C, drag inventory D, payload gaps
E, browser spot-check F, external patterns G, feed-forward H). Verification met: every row cites
`path:line` re-verified against `origin/main` `40f27a6`; six real-browser spot-checks on prod; the
gap list is grep-reproducible. Boundary stated in §F: the two draggable surfaces are member-only and
were measured from source — their browser confirmation is Step 3's mandated CDP matrix, deferred on
purpose.

Original scope, for reference:

Re-measure **every** album / track / artist representation in `myblog_front/src` — id availability
and nullability, open behavior, displayed data, actions, draggability — and compare relevant external
product patterns (Spotify, Apple Music, Are.na, Finder/Yoink for drag semantics; the
FEAT-pocket-buckit reference analysis is the precedent for how this repo does that, and its
conclusions on Spotify's overloaded "Add" and its churning queue are already recorded — extend, do
not repeat). Nothing is copied from `component-map.md`; it is **measured stale** (NowPlaying /
LikedBoard artist links) and that is the reason.

Output: a surface × entity × (id / URL / open / data / actions / drag) matrix in this RFC, plus a
list of surfaces whose payload lacks the id needed to act — flagged, **not** fixed here.

**Verification**: every row cites `path:line`; a spot-check of ≥5 rows in a real browser; the
"payload gap" list is grep-reproducible.

---

### Step 2 — canonical definitions + drop matrix + the album-detail decision (docs-only)

Fill E1 and E3 from Step 1. Resolve **OQ1** (canonical URLs) and **OQ2** (two album-detail hosts or
one) with the owner, both allowed to resolve as "no change". Record the drop matrix including the
Playback Bucket row.

**Verification**: doc review; each decision names the prior decision it retains or supersedes and
what changed since.

---

### Step 3 — `lib/entityDrag.ts` + adapter, board behavior provably unchanged (front-only)

Introduce the payload and a bidirectional adapter to `DndItem`; rename `kind:'album'` to what it
means; keep `boardDnd.ts`'s rules untouched. **No surface gains a drag in this step** — the point is
that the board and the tray behave identically through the new payload before anything new depends
on it.

**Verification**: `pnpm lint` (antfu, before commit) + `pnpm exec astro check` (Node 20) +
`pnpm test`; `boardDnd.test.ts` extended to run every existing case through the adapter and assert
identical `ops` calls; real-browser CDP on the board + tray: move, copy-from-recent, library copy,
artist expansion, trash, bucket-into-bucket, and a rejected drag that does **not** reflow the tray.

**Rollback**: revert — additive until a surface uses it.

---

### Step 4 — pointer/gesture prototype + mobile equivalent (measurement, then a narrow decision)

Prototype in a real browser on real surfaces (not a synthetic harness — memory
`feedback-front-verify-live-dom-not-harness`): drag threshold vs vertical scroll on a list, vs
horizontal scroll on a home strip, vs a click on a card that also opens an overlay; and the touch
path. Measure; then decide, recording the numbers.

**Verification**: CDP with `emulate("390x844x3,mobile,touch")` (not `resize_page` — memory
`reference-cdp-mobile-emulation`); a recorded table of threshold × surface × outcome; a decision row
in the Decisions log naming what was measured. **A decision made without the measurement fails this
step.**

---

### Step 5 — roll the contract out across surfaces (front-only, possibly split by surface group)

Apply E1–E4 surface by surface. Open `TrackRow`'s `play`/`add`/`drag` slots. Bring or document the
two hand-rolled track-row twins. This is the step most likely to need splitting; the split axis is
**surface group** (public read surfaces / member dashboard / search / writer), never entity type — a
half-migrated entity is worse than a half-migrated surface.

**Verification**: lint + astro check + `pnpm test`; CDP matrix — one drag and one non-drag add per
surface group, an id-less entity proving non-draggable, mobile 390 pass; grep gate: no hand-rolled
drag payload outside `lib/entityDrag.ts`.

---

### Step 6 — `component-map.md` rewrite + re-stamp (docs-only)

Entity-navigation, track-click and ownership sections rewritten to the new contract; the
2026-07-08 stale rows corrected; impact template filled; `Verified` re-stamped.

**Verification**: doc-only; every claim spot-checked against code in the same session.

---

## Dependencies and sequencing

- **Steps 1–3 gate `FEAT-playback-bucket-player` Step 8.** That RFC's Steps 1–7 do not depend on this
  one; only its external drop sources do.
- **Step 2's drop matrix consumes `FEAT-playback-bucket-player`'s Playback Bucket row** — that row is
  specified there and referenced here. If the playback RFC has not reached Step 2 yet, the row is
  recorded as pending and the matrix ships without it.
- **Step 4 blocks Step 5**, and its outcome feeds `FEAT-playback-bucket-player` OQ5 (the mobile
  add-to-queue path).
- No cross-repo ordering: this RFC is front-only unless Step 1's payload-gap list turns into a
  separately-scoped contract add (the `RFC-ui-surface-unification` Step 4 precedent, which needed no
  migration).

---

## Open questions

1. **Does an album get a canonical URL?** *(blocks Step 2.)* `ARCH-entity-interaction-unify` decided
   **no `/album/[id]` route** (owner, 2026-07-08) in favor of the app-wide overlay, and explicitly
   parked "SEO/deep-link for albums" as "a possible later RFC". The brief now asks to define canonical
   URLs — so this is that later RFC and the question is legitimately live, not a re-litigation.
   What actually changed since: `SEO-review-structured-data` shipped `MusicAlbum` JSON-LD on review
   pages, and the 404 fallback shell (`NotFoundShell`) proved a runtime-hydrated entity page works
   without a build. **No default asserted** — the trade (deep-linkable/shareable/indexable vs one more
   route, a build-time path problem for a growing catalog, and a second way to open an album) needs
   the owner, and the same question applies to tracks with a different answer likely.
   **Step 1 adds a concrete argument the question did not have** (§Step 1 audit G1): the public
   editorial surfaces an album URL would most serve — canon cards, the review index, home review
   rows, search review cards — carry **no album id at all**, so they cannot address an album by
   *any* mechanism today, route or overlay. That splits the question in two: "add a route?" and
   "put an id in the review frontmatter payload?" The second is cheaper, independently useful, and
   a prerequisite either way. Still the owner's call.
2. **Two album-detail hosts, or one?** *(blocks Step 2.)* Stated accurately in *Current state*: the
   read body is already shared; the split is read-only-event-host vs writable-prop-host. What changed
   since owner decision 8: the shared body landed, and drag is about to be added to every album
   representation, which means a third behavior to keep in sync across hosts.
   **Recommended default: keep two hosts, unify nothing further** — the architect rule that the event
   cannot carry writable context is unchanged, and a merged host would have to branch on
   `isLoggedIn()` + bucket presence internally, which is the option the Step-1 architect pass already
   rejected in favor of extraction. The genuinely actionable item is the smaller one: the
   `memo-trow` / `TrackRow` twin, where a lyrics change must be made twice. Owner confirmation still
   needed, because the brief asked for the revisit explicitly.
3. **How far does "most representations" go?** *(blocks Step 5's scope.)* Some representations are
   arguably not drag sources: header-search dropdown rows (single-action keyboard rows — already
   excluded once, deliberately, in `RFC-ui-surface-unification` Step 4), writer ★-pick rows (a
   different selection semantic), and analysis-chart data points (query output with no entity id).
   **Recommended default**: drag every representation that has a stable entity id **and** lives in a
   browsing context; exclude command/keyboard surfaces and selection-mode rows, listing each
   exclusion with its reason. Needs a yes because "most" is the owner's word and the boundary is a
   product call. **Step 1 supplies the exclusion list to say yes or no to**: selection-mode surfaces
   (B9 라이터 추천 트랙 ★, C9 라이터 작품 검색) and keyboard command rows (A8/B5 `HeaderSearch`) —
   exactly the shape the default predicted.
4. **What replaces drag on touch?** *(blocks Step 5; answered by Step 4's measurement, not by
   opinion.)* Candidates: the shipped `AddToBucketMenu` on every surface (lowest risk, already the
   WCAG primary path), long-press drag, or a selection mode. Recorded as an OQ rather than
   pre-decided because the brief explicitly asks to prototype before fixing one interaction.
   **Step 1 did not answer this, but it moved the burden** (§Step 1 audit G): Are.na — the closest
   product analogue — drops `draggable` from 12 to **0** under 390×844 touch emulation while keeping
   its cards and its named "Connect" button. It does not attempt a long-press drag. Step 4 still owes
   the *desktop* threshold-vs-scroll measurement; what changed is that "long-press drag on mobile"
   now needs a positive reason to exist rather than merely surviving a lack of evidence against it.

---

## Risks

- **A refactor that changes behavior while claiming not to.** `boardDnd.ts`'s rules are subtle
  (same-bucket guard, `copy` vs `fromLib` vs move, the library album-id guard). Mitigation: Step 3's
  adapter must make every existing `boardDnd.test.ts` case assert *identical* `ops` calls, and no
  surface changes in that step.
- **Fake unification.** The house rule from `ARCH-entity-interaction-contract` — do not claim
  "unified track rows" while the highest-traffic tracklist cannot consume the component. Two
  hand-rolled twins exist; each must be adopted or documented with a revival trigger. A grep gate
  only proves *hand-rolled payloads* are gone, not that behavior converged.
- **Gesture decisions made from a synthetic harness.** Layout and overlay behavior must be verified
  against the live DOM (memory `feedback-front-verify-live-dom-not-harness`), and a stub that answers
  instantly erases the very races a drag threshold has to survive.
- **Scope inflation via "most".** OQ3 exists to bound it; Step 5 splits by surface group so a
  descope leaves whole surfaces consistent rather than entities half-done.
- **Re-litigating settled decisions.** Three of the four reopened items were decided by the owner
  with a written rationale. Each is reopened with an explicit "what changed since", and two carry a
  recommended default of **no change** — the reopen is a check, not a presumption of reversal.

## Decisions log

| Date | Decision | Step |
|------|----------|------|
| 2026-08-03 | **Owner: Status draft → accepted.** Runs in parallel with `FEAT-playback-bucket-player` (different repos, no shared files); only that RFC's Step 8 waits on Steps 1–3 here | 1 |
| 2026-08-03 | Filed as a draft alongside `FEAT-playback-bucket-player` after a joint audit; scoped as the **third** RFC in the entity-interaction lineage (contract → unify → v2), inheriting both predecessors' contract points rather than replacing them | 1 |
| 2026-08-03 | **`component-map.md` measured stale** — its "NowPlaying / LikedBoard artists not linkable" claim is false since front #293 (2026-07-19) and #299 (2026-07-21). Step 1 therefore re-measures every row instead of extending the map | 1 |
| 2026-08-03 | **The album-detail revisit starts from the accurate state**, not the brief's framing: `ARCH-entity-interaction-unify` Step 1 already extracted the shared read body and struck component-map duplication #1. The live question is two hosts vs one, and the recommended default is **no further change** | 2 |
| 2026-08-03 | `boardDnd.ts`'s move/transform/reject rules are **retained verbatim**; only the payload around them is unified. Rewriting proven, unit-tested drop semantics was rejected as the largest avoidable risk in this RFC | 3 |
| 2026-08-03 | `ARCH-entity-interaction-contract` OQ2's reserved `play`/`add` slots are **granted** — the brief's drag-and-drop scope plus the Playback Bucket's track drops constitute the product approval that OQ2's default was waiting for | 5 |
| 2026-08-04 | **Step 1 audit landed.** The re-measure justified itself immediately: 4 of the 5 drag citations in this RFC's own *Current state* had moved in one day (`:569`→`:580`, `:965`→`:981`, `:435`→`:444`, `:589`→`:641`). The *conclusion* (two draggable surfaces) held. **Step 6 should re-stamp `component-map.md` with symbol names, not line numbers**, wherever a symbol exists — line citations in this lineage decay within a single step | 1 |
| 2026-08-04 | **Payload gaps are recorded as blocked-actions, not missing fields, and none was fixed** (the RFC's own non-goal). Six are listed (G1–G6); the largest by far is **G1 — the build-time `ReviewCard` carries no album or artist id**, which is why every public editorial surface can only navigate. G4 is a different species and worth calling out separately: release events **pass a Spotify id into the `albumId` slot** on a resolve miss — an id-*namespace* conflation, not an absence | 1 |
| 2026-08-04 | **Two findings were deliberately NOT filed as payload gaps** — `/collection` (48 albums, id present, zero interactive descendants, measured in prod) and `ReleaseRadar` (holds `artist_id`, renders no hub link — `grep -c artistHref` = 0). The id is already there; these are Step 5 wiring, not a contract change, and conflating the two categories would have inflated the contract-change surface | 5 |
| 2026-08-04 | **Are.na measured as the drag-semantics analogue** (`/explore`, logged out): every card `draggable="true"` (12/12), drag on the container that also wraps the navigating link (native DnD resolving click-vs-drag — the same mechanism `BucketBoard.tsx:617-618` documents), and a named non-drag peer ("Connect") coexisting with it. **At 390×844 touch, draggable drops 12 → 0 while the cards and "Connect" remain.** The closest analogue abandons drag on touch rather than implementing a long-press — external corroboration for OQ4's default, and it shifts the burden: long-press drag now needs a positive reason to exist | 4 |
| 2026-08-04 | **The zero-review fact is recorded as scope-limiting, not trivia.** Prod has no published review (`a[href^="/review/"]` = 0 on home), so A10 and B4 — **the only public 담기 surface and the only track-담기 surface in the product** — are unreachable by anyone. Any Step-5 coverage claim that counts them is counting surfaces no user can reach | 5 |
| 2026-08-04 | **Member-side browser verification deferred to Step 3, on purpose.** The two draggable surfaces need a populated member board to exist in the DOM at all, and Step 3 already mandates a full CDP board+tray drag matrix. Step 1's six spot-checks are public-side; §F says so rather than implying full coverage | 3 |
