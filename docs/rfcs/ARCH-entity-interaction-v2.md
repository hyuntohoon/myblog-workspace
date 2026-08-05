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

> **Answered 2026-08-04 (owner): two hosts, no further unification — and the twin is what gets
> fixed.** See **E6**. `shared/TrackRow.tsx` carries the `⚠️ TWIN` marker for exactly this pair, so
> the code already knew; Step 5 owns the adoption.

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

### E1 — canonical entity definitions (written here, enforced in code) — ✅ **filled Step 2, 2026-08-04**

Cited against `myblog_front` `origin/main` `40f27a6` (the same tree Step 1 measured). Symbol names
are given alongside line numbers because line citations in this lineage decay within one step
(Decisions log, 2026-08-04).

**Rule 0 — "canonical id" is a rule about the *slot*, not a field name.** Step 1 §H found three id
shapes in circulation, and the definitions below are what disambiguates them:

| Shape | Where | What the contract says |
|---|---|---|
| Nullable DB id | the common case (`BoardAlbum.albumId`, `buckets.ts` `BoardAlbum`) | first-class; a null id makes the entity **inert**, never a crash (retains unify OQ3/OQ4) |
| Foreign-namespace id in a DB-id slot | G4 — `releases/releaseShared.tsx` resolve-miss fallback writes a **Spotify** album id into `albumId` | **prohibited by this contract.** Convert at the producer or pass null; a consumer must never have to guess a slot's namespace |
| Id resolved asynchronously per render | G5 — `NowPlaying` `resolveDbArtistId` | legal for *navigation*, illegal for *drag*: a drag source must hold the id at `dragstart` or not be draggable |

Neither G4 nor G5 is fixed here — this RFC's non-goal stands. What changes is that they are now
contract violations with a named owner step (Step 5), not merely observations.

#### Album

| Facet | Canonical definition | Cite |
|---|---|---|
| Canonical id | `albums.id` (DB uuid), carried as `albumId` / `album_id` | `lib/entityEvents.ts` `OpenAlbumDetail.albumId`; `lib/buckets.ts` `BoardAlbum.albumId` |
| Null semantics | Nullable everywhere. Null ⇒ **no open, no 담기, no drag** — the surface renders as static content rather than a dead control (the existing `/search` A7 and `ArtistHub` A9 behavior, now the rule) | `boardDnd.ts` `routeAlbumDrop` library guard; `openTrackAlbum` early return |
| Canonical URL | **None, by decision** (owner 2026-08-04, OQ1 — retains `ARCH-entity-interaction-unify` 2026-07-08). An album is addressed by id + open-event, never by path | `lib/entityLinks.ts` header comment ("albums have no route") |
| Open | `openAlbum({albumId, title, artist, cover, year})` → the app-wide read-only overlay. In a member **write** context, `onOpen(DetailTarget)` → `member/AlbumDetail`. **Two hosts, by decision** (owner 2026-08-04, OQ2) | `entityEvents.ts` `openAlbum` / `ENT_OPEN_ALBUM`; `album/AlbumOverlay.tsx`; `member/AlbumDetail.tsx` |
| Displayed data (payload minimum) | `title`, `artist`, `cover`, `year` — enough to paint the header without waiting on the detail fetch. A payload carrying only an id is legal but degrades to a blank flash | `entityEvents.ts` `OpenAlbumDetail` |
| Actions | `open` (id present) · `add` 담기 · `drag` · `▶` (via `replaceQueueAndPlay`, never a raw `play()`) · 평가 / 메모 / 가사 — **member host only** | `AlbumDetailView.tsx`; `member/AlbumDetail.tsx` |
| Drag payload | `{ entity:'album', albumId, title, artist, cover }` + `origin` (E2) | E2 |

#### Track

| Facet | Canonical definition | Cite |
|---|---|---|
| Canonical id | `tracks.id` (DB uuid). **`spotify_id` is not it** — it is a second namespace that travels alongside (`AlbumDetailView` passes both) and is what G2's `LikedRowVM.id` actually holds | `album/AlbumDetailView.tsx` tracklist; `member/LikedBoard.tsx` `LikedRowVM` |
| Null semantics | Null track id ⇒ no 담기, no drag. Opening degrades to the **album** path, and a null album id there is a documented no-op | `entityEvents.ts` `openTrackAlbum` |
| Canonical URL | **None** — and for a different reason than the album's, which is why OQ1's "the answer may differ for tracks" resolves to the same word with different content: a track has no page **and no window of its own**; its canonical destination is its album's overlay (retains unify Step 3) | `entityEvents.ts` `openTrackAlbum` |
| Open | `openTrackAlbum({albumId, albumTitle, artist, cover, year})` | 〃 |
| Displayed data | `title`, `artist`, parent album title, `track_no`, duration | `AlbumDetailView.tsx`; `buckets.ts` `BoardAlbum.durationSec` |
| Actions | `lyrics?` (host-supplied — the public host deliberately omits it) · `open?` · `play?` · `add?` · `drag?` — the E4 slot set | `shared/TrackRow.tsx` |
| Drag payload | `{ entity:'track', trackId, albumId \| null, title, artist }` + `origin` | E2 |

#### Artist

| Facet | Canonical definition | Cite |
|---|---|---|
| Canonical id | `artists.id` (DB uuid), carried as `artistId` / `artist_id` | `buckets.ts` `BoardAlbum.artistId` |
| Null semantics | Null ⇒ the name renders as **plain text**, not a dead link — already the majority behavior at the 19 `artistHref(` call sites, now the rule | `lib/entityLinks.ts` `artistHref` |
| Canonical URL | **`/artist/{id}/` — trailing slash canonical.** The only entity with a URL, and it stays that way. Built **only** by `artistHref`; hand-rolled `/artist/${…}` literals outside `entityLinks.ts` and `pages/` are contract violations | `lib/entityLinks.ts` `artistHref` + file header |
| Open | Page navigation. Never an overlay — an artist has no window | 〃 |
| Displayed data | `name`, `image` | `buckets.ts` `BoardAlbum.artist` |
| Actions | `open` (nav) · `drag`. No 담기 from public surfaces today; an artist enters a bucket by drag or by Artist-bucket expansion | `boardDnd.ts` `routeAlbumDrop` artist branch |
| Drag payload | `{ entity:'artist', artistId, name, image }` + `origin` | E2 |

**Recorded in `component-map.md` by Step 6**, not here — the map is measured stale and Step 6 owns
its rewrite; duplicating E1 into it now would create a second stale copy.

### E2 — one drag payload — ✅ **shipped Step 3, 2026-08-04** (front #351)

`lib/entityDrag.ts` — a single typed payload used by every draggable representation. **The
block below is the shipped shape**, which differs from this RFC's original sketch in three
ways that the code forced; each is a Decisions-log row and the reasoning is in §Step 3.

```ts
type EntityRef =
  | { entity: 'album',  albumId: string,  title?, artist?, cover? }
  | { entity: 'track',  trackId: string,  albumId: string | null, title?, artist? }
  | { entity: 'artist', artistId: string, name?, image? }
  | { entity: 'bucket', bucketId: string, name? }              // ← added: a bucket node drags too

type DragOrigin =
  | { kind: 'internal', itemId, fromBucketId, itemType? }      // a membership → MOVE
  | { kind: 'library',  itemId, fromBucketId, itemType?, source? }  // ← added: a membership that COPIES
  | { kind: 'external', fromBucketId?, itemType?, copies? }    // ← `copies`: does dropping ADD?

type DragPayload = { ref: EntityRef | null, origin: DragOrigin }
```

- **The move/add distinction is preserved by construction**: `origin` carries it, replacing
  today's implicit `copy` / `fromLib` / `fromBucketId` triad. **It needs three kinds, not two** —
  a `spotify_library` row *is* a membership (it has an `itemId`; the trash can take it) yet it
  **copies** out, because the bucket is sync-owned. Collapsing it into `internal` turns a copy
  into a move.
- **`external.copies` is the residue the binary missed.** `origin.kind` alone does not reproduce
  the `copy` flag: a membership-less source bearing an album id but no copy affordance is a
  *no-op* on a General bucket, and inferring `copy: true` from "not a membership" silently
  converted that no-op into a `copyAlbum`. Caught by the round-trip test, not by review.
- **`ref` is nullable.** A member row may point at no canonical entity (a review / snapshot row).
  That is E1 Rule 0's inert entity, and it must stay a real *membership* — a review row still
  moves between General buckets.
- **Display fields are optional and no source fills them yet.** E1's "payload minimum" is a
  Step 5 obligation; populating them in Step 3 would have been a surface change.
- `DndItem` is **adapted, not deleted** — `boardDnd.ts`'s rules are correct and unit-tested; Step 3
  introduces an adapter both ways so board behavior is provably byte-identical before any surface is
  rewired. Renaming `kind:'album'` (which really means "a member of any type") is part of Step 3.
  The rule *function* names (`canAcceptAlbumDrag`, `routeAlbumDrop`) were deliberately left alone —
  E1/E3 cite them by symbol.
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

#### The matrix — ✅ **filled Step 2, 2026-08-04**

Read from `boardDnd.ts` (`canAcceptAlbumDrag`, `canAcceptBucketDrag`, `routeAlbumDrop`) and
`BucketBoard.tsx` (`TrashDock.accepts`) at `origin/main` `40f27a6`. **Nothing below is a proposal** —
every cell states what the code does today, which is the point: E3 is the declaration the rules
already obey, written down so a new surface cannot invent a fourth outcome.

**The known-target list had a hole.** The RFC named five targets; the code has **six**. The
Spotify-library bucket is a distinct target with its own rule (album-only, copy-in, null-album
reject) that neither the General nor the Artist row covers.

| Target | Album | Track | Artist | Bucket (container) |
|---|---|---|---|---|
| **General bucket** (`type` ∉ {`artist`,`playback`}) | direct-add | direct-add | direct-add | nest, cycle-guarded |
| **Artist bucket** (`type='artist'`) | **transform** → credited artists | **transform** → credited artists | direct-add | nest, cycle-guarded |
| **Playback Bucket** (`type='playback'`) | **transform** → its tracks, album order, N rows | direct-add — **one appended row, a COPY**; duplicates deliberate (D8 inverted) | **reject** | nest, cycle-guarded |
| **Spotify-library bucket** (`kind='spotify_library'`) | direct-add **as a copy** | **reject** ⚠️ *silent today* | **reject** ⚠️ *silent today* | nest, cycle-guarded |
| **Trash dock** | direct-add → recoverable trash — **unless** `source='preexisting'` (→ reject) or the drag is a `copy` source | **reject** | **reject** | direct-add, **with confirm**; a system bucket **409s with a reason** (server-side, subtree-wide) |
| **Bucket node** (any bucket as a container) | — (same as its own type row above) | — | — | nest unless self or own subtree |

Cell-by-cell provenance, and the reasons that are not obvious from the verb:

- **General accepts everything** — `canAcceptAlbumDrag` returns `true` for any non-artist,
  non-playback bucket; internal members route through `insertAlbum` (MOVE), and a `copy` / `fromLib`
  source routes through `copyAlbum` (COPY). The move-vs-copy split is the D-series default, and E2's
  `origin.kind` is what replaces today's three-flag inference.
- **Artist bucket transforms both album and track** into their *credited artists* via `expandSource`;
  an artist member itself moves in. A source bearing **no** artist-, album- or track-id is rejected
  at drag-over — the review / playback / snapshot tiles.
- **Playback Bucket rejects artists** — the Artist-bucket rule inverted, as
  `FEAT-playback-bucket-player` specifies (its comparison-table rows 9 and 10). The album→**tracks**
  expansion is the only expansion in the product that does not go to artists, and it is exempted from
  D8's mandatory-confirmation rule by that RFC's owner decision 3 (no confirm, Undo instead) — the
  exemption is scoped to this one target and is **not** generalized by E3.
- **Same-bucket drop is a reposition, not a second copy** on both the Artist and Playback branches
  (`it.fromBucketId === target.id` → return). On the Playback Bucket this is load-bearing: without it
  the deliberate-duplicates rule would swallow every reorder.
- **The library bucket rejects a null-album row** because a track/artist row has nothing to reconcile
  against Spotify — the one place where "reject" protects a *sync contract* rather than a membership
  semantic. ⚠️ **And today that rejection is invisible, which is the one place the code does not
  already satisfy E3.** The library bucket is identified by `kind`, but `canAcceptAlbumDrag` keys only
  on `type` — so a track or artist row dragged onto it **highlights as accepted**, and
  `routeAlbumDrop`'s `isLib && !albumId` branch then returns silently: no insert, no message, no
  reason. Writing the matrix is what surfaced it; the gate and the route disagree because they key on
  different axes. ~~**Not fixed here** (docs-only) — assigned to **Step 3**~~ → ✅ **fixed in Step 3** (front #351):
  the gate now keys on `kind`, so the library no longer previews an acceptance it will refuse, and the
  change landed in both twin files. **Step 3 also corrected this bullet's framing** — the board has no
  reject visual for *any* cell, so "the one cell the code does not satisfy" was true only of the
  *false accept*; rendering E3's muted-with-a-reason state on the board is a matrix-wide Step 5
  obligation. See §Step 3.
- **The trash rejects every non-album row**, and this is the sharpest instance of the reject state
  carrying meaning: the trash restores solely via the album re-add path, so accepting a track /
  artist / review / playback row would make 복원 a lie and the delete permanent. A `preexisting`
  library album is rejected for the opposite reason — deleting it locally would not remove it from
  Spotify and the next sync re-pulls it.
- **Bucket-into-bucket** is guarded only against self and own-subtree; **moving a system bucket stays
  free**. The guard that exists is on *delete*, server-side, over the whole subtree
  (`_system_bucket_in_subtree`) — E3 declares no bucket-move restriction because there is none, and
  inventing one here would duplicate a guard that already lives where it belongs.

**Every accept-gate in this matrix is a drag-over preview, never the gate.** The server re-checks and
400s. Two consequences Step 3 and Step 5 inherit:

1. **The gate is a drift pair.** `boardDnd.ts` `canAcceptAlbumDrag` and
   `pocketBuckit/boardDnd.ts` `boardDragAccepts` are duplicated on purpose (two React roots, no
   shared context) and `boardDnd.test.ts` asserts they agree case-for-case. **A change to any cell in
   this matrix lands in both files in the same PR** — the standing cross-repo twin rule, applied
   inside one repo.
2. **A reject cell must still render.** Per the state table above, the target stays in place, mutes,
   and names the reason; the tray never reflows mid-drag. A cell that is "reject" is a UI obligation,
   not an omission.

### E4 — action slots opened

`TrackRow`'s `play` and `add` slots — reserved since `ARCH-entity-interaction-contract` OQ2 pending a
product decision — are **granted** by this RFC's owner-approved scope, and `drag` joins them. Track
row actions become `{lyrics?, open?, play?, add?, drag?}`. The two hand-rolled twins (`memo-trow`,
review tracklist) are either brought onto the contract or listed as reasoned exceptions with a
revival trigger — no fake unification (the `ARCH-entity-interaction-contract` house rule).

**Step 2 assigns the two twins different verdicts** (owner 2026-08-04, OQ2):

- **`memo-trow` → adopt.** ✅ **Done, Step 5 second slice (2026-08-05, front #354).** The member
  `AlbumDetail`'s `MemoWindow` hand-rolled track rows that `shared/TrackRow.tsx` marked `⚠️ TWIN`, so
  the lyrics affordance existed twice. Adopted via a new `openLyrics` action (whole-row identity
  click, `role="button"` + keyboard support on the row — the shape a nested `open` button couldn't
  express); the dead `.memo-trow*` CSS in `styles/member/layout.css` (the dashboard-scoped trap this
  row warned about) is removed with it.
- **Review-page inline tracklist → documented exception, unchanged.** Retains comparison-table rows 8
  and 10: it is a distinct surface, its revival trigger has fired, and **Step 4 decides
  bridge-vs-adopt**. Step 2 does not pre-empt that, and prod has zero published reviews, so nothing
  here is urgent.

### E5 — mobile and pointer conflicts, settled by measurement — ✅ **filled Step 4, 2026-08-04**

**The tap fallback wins by elimination, not by threshold-tuning.** Step 4 measured (raw CDP touch
dispatch, not a page-JS stub) that native HTML5 `draggable` never produces `dragstart` under touch on
either surface that uses it (`BucketBoard` vertical list, 최근 들은 앨범 horizontal strip), at any
distance 0–60px — the browser's own tap/scroll disambiguation (`pointercancel`) owns the outcome, not
app code, so there is no pointer-drag threshold for Step 5 to port there. The kebab/`AddToBucketMenu`-
shaped tap fallback (`onTouchActions`) is confirmed reliable at 0px on the vertical-list surface. The
one shipped touch-pointer-drag implementation (`PocketTray`'s `Math.hypot < 6` + `touchAction:'none'`)
could not be confirmed to survive real touch input in this harness — recorded as **unconfirmed**, not
disproven. **Consequence for Step 5**: ship the tap-fallback pattern on new surfaces; do not extend
PocketTray's pointer+threshold pattern elsewhere without a real-device check first. Full measurement
table and method → §Step 4.

### E6 — the album-detail decision (OQ2, owner 2026-08-04)

**Two hosts are retained. Nothing further is unified.**

- Retains `RFC-ui-surface-unification` owner decision 8 (2026-07-18) and
  `ARCH-entity-interaction-contract`'s non-goal; builds on `ARCH-entity-interaction-unify` Step 1,
  which already extracted the shared read body.
- **What changed since, and why it did not change the answer**: the read body is now shared
  (`album/AlbumDetailView.tsx`), and drag is about to become a third behavior to keep in sync. Both
  arguments cut *toward* the split rather than against it — the shared body means the remaining
  difference is exactly the writable context, and the architect rule that the `ent:*` event cannot
  carry writable context is unchanged. A merged host would have to branch internally on
  `isLoggedIn()` + bucket presence, which is the option the Step-1 architect pass rejected in favor
  of extraction.
- **Consequence for E1**: "open" is a two-valued facet for albums (overlay / member modal), and that
  is the contract, not drift. **Corrected 2026-08-05** (external review item 8 — this line as
  originally written invited exactly the "inferring intent from screen location" misreading the
  review raised): the split is **not** keyed on which page/context a surface is mounted in — a
  dashboard-mounted surface can still call `openAlbum()` (`NowPlaying`, `PocketTray`,
  `PlaybackPanel` all do, from inside the member dashboard) and a data-driven check within a
  single surface can pick either host for the same click (`ReviewsTab.tsx`: `!hasPost && albumId`
  → overlay, else → modal). The real predicate is **whether this specific album instance carries
  an editable `DetailTarget`** (a bucket/review row) — which usually correlates with dashboard vs.
  public pages, but is not defined by it. The overlay is the default for anything that has no such
  context.
- **What this decision does *not* cover**: `memo-trow` (adopt, above). The revisit was asked for and
  the answer is "no change to the hosts, fix the twin" — the small item was always the real one.

### E7 — public editorial surfaces get the album id (OQ1, owner 2026-08-04)

**No album route. The id is projected instead.** Two separable questions, answered differently:

| Question | Answer | Retains / supersedes |
|---|---|---|
| Does an album get a canonical URL? | **No** — the overlay stays the only way to open an album | **Retains** `ARCH-entity-interaction-unify`'s owner decision (2026-07-08). This RFC *is* the "possible later RFC" that decision deferred to, so the question is now **closed**, not parked again |
| Do the public editorial surfaces get an album id? | **Yes** | Closes G1 as a Step-5 item |

**Step 2 found the cost is lower than Step 1 recorded, and this is a correction of substance, not a
line-number refresh.** Step 1 framed the second question as "put an id in the review frontmatter
payload". The id is **already in the frontmatter, end to end**:

- `myblog_backend` `app/services/publish_service.py` writes `albumIds:` and `artistIds:` into the
  frontmatter it publishes.
- `myblog_front` `src/content.config.ts` validates both — `albumIds: z.array(z.string()).default([])`,
  `artistIds` alongside it.
- `src/lib/reviews.ts` `buildReviewCards` **already reads `d.albumIds`** — it is part of the filter
  that decides whether a post is a review at all (`e.data.albumIds.length > 0`).

What it does *not* do is carry the field into the emitted `ReviewCard`, which is the JSON-safe object
every public editorial surface consumes. So G1 is not "the id does not exist"; it is **"the
projection drops it"**. The conclusion Step 1 drew stands unchanged — A12/A13/A14 cannot address an
album by any mechanism — but the fix is a projection plus consumer wiring, with **no contract change,
no backend change, and no migration**. That is also why it does not turn this front-only RFC into a
cross-repo one.

Scope, stated so Step 5 cannot quietly widen: project `albumIds` (and `artistIds`, same shape, same
cost) onto `ReviewCard`, and wire the surfaces that then have something to address. **Not** a route,
**not** an SEO deliverable, **not** a frontmatter or publish-service change. `SEO-review-structured-data`
already ships `MusicAlbum` JSON-LD on review pages and is unaffected by this decision either way.

One consequence worth stating plainly: **this unblocks nothing a user can see today.** Prod has zero
published reviews, so every surface E7 serves is currently empty. It is a prerequisite, and Step 5's
coverage count must not present it as a shipped capability.

---

## Comparison table — existing decision / retained / superseded / new

| # | Existing decision | Source | Verdict | What this RFC does |
|---|---|---|---|---|
| 1 | `lib/entityLinks.ts` is the artist/review href contract point; trailing slash canonical | contract Step 3 | **Retained** | Extended, not replaced |
| 2 | `openAlbum` / `openTrackAlbum` window events; album/track have **no route** | unify Step 1/3 | **Retained — and now closed** (owner, 2026-08-04) | Reopened as the "later RFC" unify deferred to, then **retained**: no album route, no track route. What Step 2 *adds* is the album **id** on the public editorial payload (E7) — the half of OQ1 that was never about URLs |
| 3 | Artist click → route `/artist/[id]` | unify | **Retained unchanged** | The one entity whose canonical URL is settled |
| 4 | Member surfaces stay on `onOpen(DetailTarget)`; the `ent:*` event cannot carry writable context | unify Step 1 architect rule | **Retained — load-bearing** | Constrains E1; "unifying" member call sites onto the event stays forbidden |
| 5 | Null ids are first-class; non-navigable entities no-op rather than crash | unify OQ3/OQ4 | **Retained, extended to drag** | A null-id entity is non-draggable |
| 6 | Read-only album body shared (`AlbumDetailView`); duplication #1 struck as resolved | unify Step 1 | **Retained** | The revisit starts from this state, not from "two duplicate modals" |
| 7 | **Keep the dual album-detail system**, codify the rule instead | ui-surface-unification owner decision 8 | **Reopened, re-affirmed** (owner, 2026-08-04) | Both things that changed (shared read body, drag as a third synced behavior) cut *toward* the split. Two hosts retained; the actionable item is the `memo-trow` twin, assigned to Step 5 → **E6** |
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

### Step 2 — canonical definitions + drop matrix + the album-detail decision (docs-only) — ✅ **DONE 2026-08-04**

Results: **E1** (three entity tables + Rule 0 on id shapes), **E3** (the six-target × four-entity drop
matrix), **E6** (OQ2 — two hosts retained, `memo-trow` assigned to Step 5), **E7** (OQ1 — no album
route, album id projected onto `ReviewCard`). Both open questions closed by the owner, 2026-08-04.

Three things did not go as the step's own text assumed, and all three are recorded where they matter
rather than smoothed over:

- **The known-target list was short by one.** E3 named five drop targets; the code has six — the
  Spotify-library bucket carries its own rule (album-only, copy-in, null-album reject) that no other
  row covers.
- **One cell is not satisfied by the code**: that library reject is **silent** — the gate keys on
  `type` while the library is identified by `kind`, so the target highlights as accepting and the
  route then no-ops without a reason. Assigned to Step 3.
- **OQ1's cost was overstated by Step 1**, and re-checking the claim is what found it: the album id
  is already in the frontmatter, in the schema, and already read by `buildReviewCards`; only the
  emitted `ReviewCard` drops it. The blocked-action conclusion is unchanged — the price is not.

The pattern across all three: **the value came from reading the code rather than transcribing the
RFC's own prior text.** Step 1 recorded the same lesson about line numbers; Step 2 records it about
claims.

Verification met: every E1/E3 cell cites a symbol in `myblog_front` `origin/main` `40f27a6`, read
from the tree rather than copied from Step 1; each decision names the prior decision it retains or
supersedes and what changed since (E6, E7, comparison-table rows 2 and 7). The Playback Bucket row is
consumed from `FEAT-playback-bucket-player`, which has shipped Steps 1–7, so it is recorded as
measured code, not as pending.

Original scope, for reference:

Fill E1 and E3 from Step 1. Resolve **OQ1** (canonical URLs) and **OQ2** (two album-detail hosts or
one) with the owner, both allowed to resolve as "no change". Record the drop matrix including the
Playback Bucket row.

**Verification**: doc review; each decision names the prior decision it retains or supersedes and
what changed since.

---

### Step 3 — `lib/entityDrag.ts` + adapter, board behavior provably unchanged (front-only) — ✅ **DONE 2026-08-04**

Introduce the payload and a bidirectional adapter to `DndItem`; rename `kind:'album'` to what it
means; keep `boardDnd.ts`'s rules untouched. **No surface gains a drag in this step** — the point is
that the board and the tray behave identically through the new payload before anything new depends
on it.

**Verification**: `pnpm lint` (antfu, before commit) + `pnpm exec astro check` (Node 20) +
`pnpm test`; `boardDnd.test.ts` extended to run every existing case through the adapter and assert
identical `ops` calls; real-browser CDP on the board + tray: move, copy-from-recent, library copy,
artist expansion, trash, bucket-into-bucket, and a rejected drag that does **not** reflow the tray.

**Rollback**: revert — additive until a surface uses it.

#### Result — front **#351**

Shipped as specified: `lib/entityDrag.ts` + both adapters, every drag source building the payload,
every rule call site adapting at the boundary, `kind:'album'` → `'member'`. `boardDnd.ts`'s routing
was not rewritten. Both **cross-island wires** (`PB_DND_START` tray→board, `PB_BOARD_DND_START`
board→tray) now carry the payload itself rather than a hand-rolled mirror of `DndItem` — the mirror
was a second drift pair nobody had named.

**The adapter is a measurement, not a claim.** A 27-payload corpus (every payload in
`boardDnd.test.ts`, plus the four shapes the live drag sources actually build) is pushed through
`fromDndItem` → `toDndItem` and required to produce, against each of the four accept-gate targets,
the same accept answer **and the same recorded `ops` calls in the same order**. vitest **293 → 439**
(baseline measured on `origin/main` in a detached worktree, not assumed). lint clean · astro check 0
errors · build 2210 pages.

**Three spec corrections came from writing the code** — all three are E2 amendments above and
Decisions-log rows below: the third origin kind (`library`), `external.copies`, and the `bucket`
ref. The first two are the same class of error: E2's two-value `origin` looked sufficient in prose
and silently converted a copy into a move (and a no-op into a write) in code.

**Two RFC-listed scenarios were unreachable with the smoke account, and were reached by relabelling
rather than skipped.** The account has never synced Spotify, so it has no `kind='spotify_library'`
bucket. One **real** server-side bucket was relabelled in flight by the local proxy — its row, id
and every write stay genuine; only the client sees it as the library crate. It then rendered inside
the Spotify 라이브러리 panel and was excluded from the tray rail, confirming both code paths before
the drag tests ran. What this does **not** cover: server-side library semantics (sync, `source`
flags). What it does cover is exactly what Step 3 changed — the kind-keyed accept gate and
`routeAlbumDrop`'s `isLib` branch.

**The library fix was measured against a control**, on the same page and the same row, with the
library branch removed via HMR to reproduce `origin/main`:

| gate | artist → library | album → library |
|---|---|---|
| `origin/main` | **highlighted** (the false accept) | highlighted |
| Step 3 | **not highlighted, zero writes** | highlighted + `POST /items` (a copy) |

Zero prod residue: every bucket used was created for the test and deleted afterwards.

#### Scope call on the carried-over item — narrower than Step 2 described

Step 2 assigned the invisible library rejection here and called it "the one cell where the code does
not obey the doc". **Re-measured against the code, that description was too narrow**, and the
correction is what bounds the fix: the board has **no reject visual for any cell**. `BucketCard`
only ever sets a `hot` highlight when a drag is *accepted*; there is no muted state and no reason
string anywhere on the board. E3's reject contract ("stays in place, muted, names the reason") is
satisfied by the **tray** (`data-dropreject` + a title naming what the target takes) and by **no
board cell at all**.

So the item splits:

- **Done in Step 3** — the library stops *previewing an acceptance it will refuse*. The gate keys on
  `kind` (which identifies the library) instead of only `type`. One predicate, zero `ops` changes,
  landed in **both** twin files per E3's drift-pair obligation, pinned by tests.
- **Deferred to Step 5** — rendering E3's muted-with-a-reason state on the board. Absent for all six
  targets, not just the library, so it is a surface obligation across the matrix — and Step 3 states
  no surface changes.

One residual asymmetry, recorded rather than hidden: the new gate is *stricter* than
`routeAlbumDrop` for two rows that do not exist in prod (an artist row carrying an album; a track
row carrying its parent album). The gate runs first on the board's only path to the library, so it
can only prevent a write, never invent one. The test asserts the direction that matters — never
highlight what the drop would not write.

#### Noted, deliberately not done

The `canAcceptAlbumDrag` / `boardDragAccepts` twin **can be dissolved**. E3 says they are duplicated
because there is "no shared context" — but that reason applies to the live drag *state*, not to the
*rule*, which is a pure function both files can import (`pocketBuckit/boardDnd.ts` already imports
from `@lib/buckets`). Left alone on purpose: restructuring the verified rules module inside a
prove-no-change step fights that step's own contract. **Step 5/6** owns it; until then the
drift-guard test and the same-PR obligation stand.

---

### Step 4 — pointer/gesture prototype + mobile equivalent (measurement, then a narrow decision) — ✅ **DONE 2026-08-04**

Prototype in a real browser on real surfaces (not a synthetic harness — memory
`feedback-front-verify-live-dom-not-harness`): drag threshold vs vertical scroll on a list, vs
horizontal scroll on a home strip, vs a click on a card that also opens an overlay; and the touch
path. Measure; then decide, recording the numbers.

**Verification**: CDP with `emulate("390x844x3,mobile,touch")` (not `resize_page` — memory
`reference-cdp-mobile-emulation`); a recorded table of threshold × surface × outcome; a decision row
in the Decisions log naming what was measured. **A decision made without the measurement fails this
step.**

**Method (measured, not read from source).** `resize_page`/the `emulate` tool alone can drive taps and
element-to-element drags but not a *controlled pixel distance* — the one thing a threshold measurement
needs. Driven instead via raw CDP `Input.dispatchTouchEvent` against a dedicated headless Chrome
(`--remote-debugging-port`, separate from the interactive MCP browser instance), viewport
390×844×3 + `Emulation.setDeviceMetricsOverride(mobile:true)` + `setTouchEmulationEnabled`, against
the local dev server proxied to prod (smoke-account Cognito JWT, 5 temp buckets + 12 real catalog
albums seeded via `POST /api/buckets`/`POST /api/buckets/{id}/items`, deleted via `DELETE
/api/buckets/{id}` after — zero prod residue, verified). This is genuine browser-level touch dispatch
(the same primitive Chrome's own device toolbar uses), not a page-JS-stubbed event — but it is still
headless/CDP-synthetic, not a physical touchscreen; see the caveat below the table.

Three real surfaces, matching the RFC's own inventory: `BucketBoard.tsx`'s vertical bucket-item list
(native `draggable`, `onClick` opens the album overlay), the "최근 들은 앨범" horizontal strip inside
`BucketBoard.tsx` (same native-`draggable` `AlbumChip`, `overflowX:auto` — the real horizontal-scroll
+ drag surface, not `HomeStrip.tsx` which carries no drag at all today per *Current state*), and
`PocketTray.tsx`'s pointer-based bucket-chip reorder rail (`Math.hypot < 6` threshold,
`touchAction:'none'`, `suppressClick` after a completed drag — the only shipped touch-pointer-drag
code in the app).

| Surface | Gesture / net movement | Outcome | Evidence |
|---|---|---|---|
| Vertical list (`BucketBoard` album tile) | tap, 0px | `click` fires, album overlay opens | measured |
| Vertical list | 5px, 15px vertical | `click` still fires each time; **`dragstart` never fires** | measured |
| Vertical list | 50px vertical (real scroll attempt) | `pointercancel` (no `click`); **`window.scrollY` moved 167→137** — the browser's own scroll takes the gesture cleanly, no accidental overlay-open | measured |
| Horizontal strip (최근 들은 앨범, native `draggable`) | tap, 0px | `click` fires | measured |
| Horizontal strip | 3px, 10px horizontal | `click` still fires; **`dragstart` never fires** | measured |
| Horizontal strip | 30px, 60px horizontal | `pointercancel` (no `click`, no `dragstart`); container `scrollLeft` did not move in this harness — see caveat | measured |
| PocketTray rail (pointer-drag, `touchAction:'none'`, edit mode) | tap, 0px / 3px / 6px / 10px horizontal | `click` fires each time (drawer-open path taken); `data-reordering` never observed `true` | measured, see caveat |
| PocketTray rail | 40px horizontal, 20-step slow dispatch; 40px vertical | `pointercancel`; `data-reordering` never observed `true` at any of 21 polled frames | measured, see caveat |
| Kebab (⋯) touch-actions fallback, vertical-list tile | tap | Bucket-picker action sheet opens | measured |

**Headline result: native HTML5 `draggable` never produces a `dragstart` under touch, on either
surface that uses it, at any tested distance (0–60px).** This is not new — it's a byte-for-byte
match to Step 1's Are.na finding (`draggable` 12→0 at 390×844 touch) — but it is now measured
in-product rather than only observed on an external analogue. The browser's own tap/scroll
disambiguation (evidenced by `pointercancel`) is what decides the outcome on both native-`draggable`
surfaces, not any app code; the app has no threshold to tune there because it never sees a drag start.

**Caveat, stated plainly rather than buried:** the PocketTray rows and the horizontal-strip
`scrollLeft` row could not be confirmed as *production* behavior by this harness — `data-reordering`
never flipped `true` in 21 polled frames of a slow, realistic 40px drag, despite the chip's own
`touchAction:'none'` which should keep the browser from claiming the gesture before the app's 6px
threshold fires. Headless CDP touch dispatch is a step closer to "real browser" than a page-JS
`DragEvent` stub (memory `feedback-front-verify-live-dom-not-harness`), but it is still not a
physical touchscreen, and this specific result — the one shipped touch-pointer-drag implementation in
the app not completing under synthetic dispatch — is exactly the shape of thing that harness gap could
hide. It is recorded as **unconfirmed**, not as "PocketTray reorder is broken on touch": a real-device
check is the way to close it, not further headless iteration.

**Decision (OQ4, answered with this measurement — full statement in E5):** native `draggable` is
unavailable on touch, full stop, matching the RFC's own Are.na precedent — there is no partial
"threshold" for Step 5 to tune, because the browser never delivers `dragstart` under touch on the two
`draggable`-using surfaces regardless of movement distance. The kebab/action-sheet tap fallback
(`onTouchActions` → `BucketPickerSheet`, the existing WCAG-2.5.7-primary path) is confirmed reliable —
tap opens it every time, at 0px. PocketTray's custom pointer-drag + 6px threshold + `touchAction:'none'`
is the only touch-capable *drag* in the app, but this harness could not confirm it survives real touch
input, which is the load-bearing property Step 5 would need before copying the pattern elsewhere.
**Step 5 ships the tap-fallback (kebab/`AddToBucketMenu`-shaped action sheet) as the touch path on
every new surface — the RFC's own recommended default — and does NOT extend PocketTray's raw
pointer+threshold pattern to other list surfaces without a real-device verification pass first.**
Long-press drag (the other OQ4 candidate) now has two independent points against it and none for it:
Are.na's abandonment (Step 1) and native drag's complete non-participation on touch (this step).

---

### Step 5 — roll the contract out across surfaces (front-only, possibly split by surface group) — 🟡 **IN PROGRESS, third slice (E7) shipped 2026-08-05** (front #362)

Apply E1–E4 surface by surface. Open `TrackRow`'s `play`/`add`/`drag` slots. Bring or document the
two hand-rolled track-row twins. This is the step most likely to need splitting; the split axis is
**surface group** (public read surfaces / member dashboard / search / writer), never entity type — a
half-migrated entity is worse than a half-migrated surface.

**Verification**: lint + astro check + `pnpm test`; CDP matrix — one drag and one non-drag add per
surface group, an id-less entity proving non-draggable, mobile 390 pass; grep gate: no hand-rolled
drag payload outside `lib/entityDrag.ts`.

**First slice shipped 2026-08-04 (front #353): the two named free wins only.** §H and the
2026-08-04 Decisions-log row single out **A11 `/collection`** and **C8 `ReleaseRadar`** as needing
no contract change — the id was already there, only the wiring was missing. Both are now wired:

- **A11**: each album card wrapped in a button that calls `openAlbum()` — matches the existing
  "overlay, no drag" pattern already used by every other public read-only album representation
  (A1/A7/A9). Drag was deliberately **not** added — an anonymous `/collection` visitor has no
  bucket to drop into, and the RFC's own A11 row leaves "Drag" unbolded (unlike "Open"/"Actions"),
  i.e. not part of the flagged gap.
- **C8**: candidate and tracked-artist rows wrapped in `artistHref()` links (the `C2` catch-all
  pattern, already used at 19 other call sites via `SearchPage.tsx`). The candidate row lives
  inside a checkbox `<label>`; the link's `onClick` calls `stopPropagation()` so a click navigates
  without also toggling the checkbox — verified live, not just read.

No drag payload touched, so the grep gate holds trivially this slice. Verified live against real
prod data (CDP, desktop + 390px, logged out + via a temp smoke-account JWT for the authed
candidate/tracked rows — 0 residue left behind) and confirmed in the deployed bundle post-merge.
**Remaining Step 5 scope is everything else**: `TrackRow`'s `play`/`add`/`drag` slots, the
`memo-trow` adoption (E4), rendering E3's board reject-visual on every matrix cell (not just the
tray), E1 Rule 0's G4/G5 violations, and E7's `ReviewCard` id projection — none of that shipped
here; this slice was scoped narrowly to the two items the RFC already named as free-standing.

**Second slice shipped 2026-08-05 (front #354): `TrackRow`'s `play`/`add`/`drag` slots opened, plus
the `memo-trow` adoption (E4).** Two changes, one PR:

- **`play`/`add`/`drag` opened.** `shared/TrackRow.tsx`'s `TrackRowActions` gains `play?: () => void`
  and `add?: () => void` (plain trailing-button slots — no queue/bucket logic in the component, same
  pattern as the existing `lyrics` slot) and `drag?: DragPayload` (E2's payload type). Granting `drag`
  makes the row natively `draggable` and dispatches the payload on **both** the tray→board
  (`PB_DND_START_EVENT`/`PB_DND_END_EVENT`) and board→tray (`PB_BOARD_DND_START_EVENT`/
  `PB_BOARD_DND_END_EVENT`) bridges (`lib/pocketBuckit/events.ts`) — the same wire every existing
  drag source already uses, so a future grant is a real, working drop source into both the board and
  the tray with **no further plumbing**. Traced both listeners (`BucketBoard.tsx`'s `onDndStart`
  populates the board's own live `dnd` from *any* dispatcher, not just the tray; `lib/pocketBuckit/
  boardDnd.ts`'s mirror likewise) before reusing them, specifically to avoid the "accept preview but
  no-op drop" failure class E3 flagged for the library bucket — reusing only the board→tray half
  would have reproduced exactly that bug for a brand-new source. **No surface grants any of the three
  in this slice** — that stays surface-by-surface, per Step 5's own split axis. Verified by 9 new
  `TrackRow.test.tsx` cases (open-vs-openLyrics exclusivity, whole-row click+keyboard, play/add
  callbacks, drag dispatch on dragstart/dragend), not by a live drop target (none exists yet).
- **`memo-trow` adopted (E4).** `member/AlbumDetail.tsx`'s `MemoWindow` hand-rolled its own track
  rows because `TrackRow`'s only identity action (`open`) means "open the album" — memo-trow's rows
  have nothing else to click, the WHOLE row is the 가사 button. Rather than leave that gap open,
  `TrackRowActions` gains `openLyrics` (mutually exclusive with `open`): when granted, the row's
  `no`+identity+`cells` all sit under one `role="button"` element (keyboard Enter/Space included),
  not a nested `<button>` — the shape the header comment said `TrackRow` "cannot express" until now.
  `MemoWindow` now renders `TrackRow` with `openLyrics` when a track has a `spotify_id`, omitted
  otherwise (same plain-row degrade as omitting `open`). The dead `.memo-trow*` CSS
  (`styles/member/layout.css`) is removed — the twin is gone, not just quieted, so the file's own
  "check both" warning is retired along with it.
- Traded off deliberately: `drag` is real and dispatches the true bridge, but is **not yet exercised
  on a live surface** (no CDP drag-and-drop matrix this slice — nothing to drag). `memo-trow`'s
  migration **is** live-verified: CDP against a real bucket album (Troye Sivan's *Bloom*, added to a
  temp General bucket) confirmed all 10 rows render as whole-row 가사 buttons and clicking one opens
  the lyrics sheet with the correct title/artist/album/cover; temp bucket deleted immediately after
  via page-context fetch (0 residue).
- **E7 shipped (front #362, 2026-08-05): `albumIds`/`artistIds` projected onto `ReviewCard`/
  `ReviewHit`, closing G1.** `buildReviewCards` already read `d.albumIds`/`d.artistIds` (part of
  the is-this-a-review filter) but never emitted them — front-only, no contract/backend/migration,
  exactly as scoped. Each card's cover becomes an `openAlbum()` peek button when an album id is
  present (`SearchPage`'s review card reuses the file's own existing `AlbumCard`/
  `.gs-albcard-open` pattern); the rest of the card is unchanged (still the review link). Wired:
  `CanonPage`, all 5 `ReviewsIndex` card variants (editorial hero, default lead/side, list row,
  grid card), `EditorialHome` (hero + latest row), `SearchPage`'s review facet.
  **Deliberately not wired this slice**: `artistIds` → no artist-hub link — `ReviewCard.artist` is
  a joined multi-artist display string, so `artistIds[0]` can't be safely mapped to it without a
  real per-artist split (wiring it would have been a wrong link, not a missing one).
  `HeaderSearch`'s compact instant-dropdown review row — its single-action-per-row keyboard model
  (`flatAction`) doesn't fit a second interactive zone; left for a later slice if the gap turns out
  to matter. Verified: lint/astro check 0 errors, vitest 38 files / 484 tests; CDP against 3 local
  fixture posts (not committed) confirmed the cover button opens the overlay without navigating and
  the no-albumId card renders no button, across all 4 surfaces + both `/reviews` view modes; no
  DOM-nesting console warnings. Prod smoke: deploy health check green, all 4 touched pages 200 —
  **prod has 0 published reviews, so this ships zero user-visible change today** (the RFC's own
  framing; do not count it as a shipped user-facing capability in Step 5's coverage tally).

**Remaining Step 5 scope**: granting `play`/`add`/`drag` on an actual surface, rendering E3's board
reject-visual on every matrix cell, and E1 Rule 0's G4/G5 violations.

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

1. ✅ **RESOLVED 2026-08-04 (owner) — no album route; the album id is projected onto `ReviewCard`
   instead.** Full statement in **E7**; the two halves of the question were answered separately.
   Original text below, kept because the argument it records is what the answer rests on.

   **Does an album get a canonical URL?** *(blocked Step 2.)* `ARCH-entity-interaction-unify` decided
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
2. ✅ **RESOLVED 2026-08-04 (owner) — two hosts retained; the `memo-trow` twin is the item that gets
   fixed, in Step 5.** Full statement in **E6**. The recommended default held. Original text below.

   **Two album-detail hosts, or one?** *(blocked Step 2.)* Stated accurately in *Current state*: the
   read body is already shared; the split is read-only-event-host vs writable-prop-host. What changed
   since owner decision 8: the shared body landed, and drag is about to be added to every album
   representation, which means a third behavior to keep in sync across hosts.
   **Recommended default: keep two hosts, unify nothing further** — the architect rule that the event
   cannot carry writable context is unchanged, and a merged host would have to branch on
   `isLoggedIn()` + bucket presence internally, which is the option the Step-1 architect pass already
   rejected in favor of extraction. The genuinely actionable item is the smaller one: the
   `memo-trow` / `TrackRow` twin, where a lyrics change must be made twice. Owner confirmation still
   needed, because the brief asked for the revisit explicitly.
3. ✅ **RESOLVED 2026-08-04 (owner) — recommended default adopted as-is.** Drag every representation
   with a stable entity id **and** a browsing context; exclude command/keyboard surfaces and
   selection-mode rows. Step 5 excludes exactly the three candidates Step 1 already named: `A8`/`B5`
   `HeaderSearch` (keyboard command rows), `B9` 라이터 추천 트랙 ★ and `C9` 라이터 작품 검색
   (selection-mode rows). No additional exclusions or inclusions added. Original text below, kept
   because the argument it records is what the answer rests on.

   **How far does "most representations" go?** *(blocks Step 5's scope.)* Some representations are
   arguably not drag sources: header-search dropdown rows (single-action keyboard rows — already
   excluded once, deliberately, in `RFC-ui-surface-unification` Step 4), writer ★-pick rows (a
   different selection semantic), and analysis-chart data points (query output with no entity id).
   **Recommended default**: drag every representation that has a stable entity id **and** lives in a
   browsing context; exclude command/keyboard surfaces and selection-mode rows, listing each
   exclusion with its reason. Needs a yes because "most" is the owner's word and the boundary is a
   product call. **Step 1 supplies the exclusion list to say yes or no to**: selection-mode surfaces
   (B9 라이터 추천 트랙 ★, C9 라이터 작품 검색) and keyboard command rows (A8/B5 `HeaderSearch`) —
   exactly the shape the default predicted.
4. ✅ **RESOLVED 2026-08-04 — the tap fallback (kebab/`AddToBucketMenu`-shaped action sheet), by
   elimination rather than by threshold-tuning.** Full statement in **E5** and the measured table in
   §Step 4. Native `draggable` never produces `dragstart` under real touch dispatch on either surface
   that carries it, at any distance 0–60px, so there is no drag-vs-scroll threshold for Step 5 to
   port — the browser's own gesture recognizer owns the outcome before the app ever sees a drag start.
   Long-press drag is now rejected by two independent points of evidence (Are.na's abandonment, Step 1;
   native drag's total non-participation on touch, Step 4) and none for it. PocketTray's own
   pointer+threshold pattern — the only shipped touch-drag in the app — could not be confirmed to
   survive the measurement harness and is carried forward as **unconfirmed, not disproven**; Step 5
   does not copy it to new surfaces without a real-device check. Original text below, kept because the
   burden-shift it records is what the answer rests on.

   **What replaces drag on touch?** *(blocks Step 5; answered by Step 4's measurement, not by
   opinion.)* Candidates: the shipped `AddToBucketMenu` on every surface (lowest risk, already the
   WCAG primary path), long-press drag, or a selection mode. Recorded as an OQ rather than
   pre-decided because the brief explicitly asks to prototype before fixing one interaction.
   **Step 1 did not answer this, but it moved the burden** (§Step 1 audit G): Are.na — the closest
   product analogue — drops `draggable` from 12 to **0** under 390×844 touch emulation while keeping
   its cards and its named "Connect" button. It does not attempt a long-press drag. Step 4 still owes
   the *desktop* threshold-vs-scroll measurement; what changed is that "long-press drag on mobile"
   now needs a positive reason to exist rather than merely surviving a lack of evidence against it.

   **On the "desktop threshold-vs-scroll measurement" this paragraph flagged as still owed**: it turned
   out to be moot, not skipped. Desktop `dragstart` activation is a browser-native mouse-chrome
   behavior (a few px of mouse movement, not app-tunable) and desktop scrolling is wheel/scrollbar-
   driven, not click-drag-on-content — there is no desktop analogue to the touch scroll-vs-drag
   conflict this OQ is actually about. Step 4's CDP verification bar (`emulate(...,touch)`) reflects
   that: the measurement that matters is the touch one, which is what got measured.

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
| 2026-08-04 | **Owner, OQ1 — no `/album/[id]` route.** **Retains** `ARCH-entity-interaction-unify`'s 2026-07-08 decision; this RFC was the "possible later RFC" it deferred to, so the question is **closed rather than parked again**. Tracks resolve to the same word for a different reason (no page *and* no window of their own — their canonical destination is the album overlay), so unify Step 3 is retained too | 2 |
| 2026-08-04 | **Owner, OQ1 (second half) — the album id IS projected onto the public editorial payload** (E7). **Step 2 corrected Step 1's cost estimate by re-checking the claim**: the id is already written by `publish_service.py`, already validated in `content.config.ts`, and already read by `buildReviewCards` (it is part of the is-this-a-review filter); only the emitted `ReviewCard` drops it. So G1 is "the projection drops it", not "the id does not exist" — a front-only projection change, **no contract/backend/migration**, and the RFC stays front-only. The blocked-action conclusion is unchanged; only the price is. Wired in Step 5 | 5 |
| 2026-08-04 | **Owner, OQ2 — two album-detail hosts retained; nothing further unified** (E6). **Re-affirms** `RFC-ui-surface-unification` owner decision 8. Both changes since (shared read body, drag as a third synced behavior) cut *toward* the split; a merged host would branch internally on `isLoggedIn()` + bucket presence, the option the Step-1 architect pass already rejected. The actionable item is the smaller one: **`memo-trow` adopts `TrackRow`** (Step 5, carrying the dashboard-scoped `.memo-trow` style trap); the review-page tracklist stays a documented exception with Step 4 deciding bridge-vs-adopt | 2 |
| 2026-08-04 | **E3's known-target list was short by one — the Spotify-library bucket is a sixth drop target** with its own rule (album-only, copy-in, **reject** on a null-album row: a track/artist row has nothing to reconcile against Spotify). Found by reading `routeAlbumDrop` rather than transcribing the RFC's own list | 2 |
| 2026-08-04 | **Writing E3 found the one cell the code does not satisfy: the Spotify-library reject is silent.** The library is identified by `kind`, but the accept-gate keys on `type`, so a track/artist row **highlights as accepted** and `routeAlbumDrop`'s `isLib && !albumId` branch then returns with no insert and no reason. Outcome is already correct (nothing is added); the *visual contract* is violated. Assigned to **Step 3** — the adapter touches that gate and `boardDnd.test.ts` can pin the case. Not fixed in Step 2 (docs-only) | 3 |
| 2026-08-04 | **E3 declares no bucket-move restriction, deliberately.** Moving a system bucket stays free; the protection that exists is on **delete**, server-side, over the whole subtree (`_system_bucket_in_subtree`). Adding a move guard here would duplicate a guard that already lives where the destructive act is | 2 |
| 2026-08-04 | **The E3 accept-gate is a drift pair, and that is written into the matrix.** `boardDnd.ts` `canAcceptAlbumDrag` and `pocketBuckit/boardDnd.ts` `boardDragAccepts` are duplicated on purpose (two React roots); **any cell change lands in both files in the same PR**, with `boardDnd.test.ts` asserting they agree case-for-case | 3 |
| 2026-08-04 | **E1 Rule 0: "canonical id" constrains the *slot*, not the field name.** Three shapes circulate — nullable DB id (first-class), foreign-namespace id in a DB-id slot (G4 — now **prohibited**, convert at the producer or pass null), and async-resolved id (G5 — legal for navigation, **illegal for drag**: hold the id at `dragstart` or don't be draggable). Neither is fixed here; both become contract violations owned by Step 5 | 5 |
| 2026-08-04 | **E1 is not copied into `component-map.md` yet.** The map is measured stale and Step 6 owns its rewrite; duplicating E1 now would create a second stale copy of a definition that is one step old | 6 |
| 2026-08-04 | **Step 3 shipped; the adapter is a measurement, not a claim** (front #351). A 27-payload corpus — every payload in `boardDnd.test.ts` plus the four shapes the live drag sources build — round-trips through `fromDndItem`→`toDndItem` and must return the same accept answer **and the same `ops` calls in the same order** against all four accept-gate targets. vitest **293 → 439** (baseline measured on `origin/main`, not assumed) | 3 |
| 2026-08-04 | **E2's two-value `origin` was wrong in code, twice, in the same class.** (a) A `spotify_library` row IS a membership yet **copies** out (the bucket is sync-owned), so a third kind `library` exists — collapsing it into `internal` turns a copy into a move. (b) `external` needs a `copies` bit: a membership-less source with an album id but no copy affordance is a **no-op** on a General bucket, and inferring `copy:true` from "not a membership" converted that no-op into a `copyAlbum`. **Both were caught by the round-trip test, not by review** — prose sufficiency is not code sufficiency | 3 |
| 2026-08-04 | **`EntityRef` gains a `bucket` member.** E2 listed three content entities, but E3's matrix already gives Bucket its own column and a bucket node is one of the two things that drags today; without it the adapter is partial and the identity claim would not cover bucket-into-bucket. Also `ref` is **nullable** — a review/snapshot row points at no canonical entity (E1 Rule 0) and must stay a real membership | 3 |
| 2026-08-04 | **Step 2's description of the library cell was too narrow, and the correction bounds the fix.** The board has **no reject visual for any cell** — `BucketCard` sets a highlight only when a drag is accepted. E3's reject contract is met by the tray and by no board cell at all. So Step 3 fixed the *false accept* (gate keys on `kind`, zero `ops` change, both twin files); **rendering muted-with-a-reason on the board is a matrix-wide Step 5 obligation**, not a library patch | 5 |
| 2026-08-04 | **The cross-island wires were a second, unnamed drift pair.** `PB_DND_START` and `PB_BOARD_DND_START` each carried a hand-rolled mirror of `DndItem`; both now carry `DragPayload` itself, so the two React roots share the contract instead of each keeping a copy of the other's shape | 3 |
| 2026-08-04 | **The accept-gate twin can be dissolved, and was deliberately not.** E3 justifies the duplication with "no shared context", but that applies to the live drag *state*, not the *rule* — a pure function both files can import. Restructuring the verified rules module inside a prove-no-change step fights that step's contract; **Step 5/6 owns it**, the drift-guard test stands until then | 6 |
| 2026-08-04 | **Two Step-3 CDP scenarios were unreachable and were reached by relabelling, not skipped.** The smoke account has never synced Spotify, so it has no `kind='spotify_library'` bucket. A **real** server-side bucket was relabelled in flight (row, id and writes genuine; only the client sees the library kind), and the library fix was then measured **against a control** — same page, same row, library branch removed via HMR: `origin/main` **highlights** an artist row over the library, Step 3 does not. Not covered: server-side library semantics (sync, `source` flags) | 3 |
| 2026-08-04 | **Member-side browser verification deferred to Step 3, on purpose.** The two draggable surfaces need a populated member board to exist in the DOM at all, and Step 3 already mandates a full CDP board+tray drag matrix. Step 1's six spot-checks are public-side; §F says so rather than implying full coverage | 3 |
| 2026-08-04 | **Owner, OQ4 — the tap fallback wins by elimination, not by threshold-tuning.** Measured via raw CDP `Input.dispatchTouchEvent` (not `resize_page`, not a page-JS `DragEvent` stub) against a dedicated headless Chrome, on the app's own real surfaces with real prod-catalog albums seeded through 5 temp buckets (deleted after, zero residue): native `draggable` produced **zero `dragstart` events across 0–60px** on both the `BucketBoard` vertical list and the 최근 들은 앨범 horizontal strip — the browser's own `pointercancel` decides the scroll-vs-tap outcome before the app ever sees a drag start, so there is no pointer-drag threshold to port to Step 5. The kebab/`AddToBucketMenu` tap fallback is confirmed reliable (0px tap → sheet opens, every time). PocketTray's own pointer+6px-threshold+`touchAction:none` reorder — the one shipped touch-drag in the app — could not be confirmed to survive the harness (`data-reordering` never observed `true` across 21 polled frames of a slow 40px drag); recorded **unconfirmed, not disproven**, and Step 5 does not copy that pattern to new surfaces without a real-device check. Long-press drag is now rejected by two independent findings (Are.na's abandonment, Step 1; native drag's non-participation on touch, this step) and supported by none. Full table → §Step 4 | 4 |
| 2026-08-04 | **Owner, OQ3 — recommended default adopted as-is, unblocking Step 5's scope.** Drag applies to every representation with a stable entity id **and** a browsing context; command/keyboard surfaces and selection-mode rows are excluded. The owner did not add or remove any exclusion beyond the three Step 1 already named (`HeaderSearch` A8/B5, 라이터 추천 트랙 ★ B9, 라이터 작품 검색 C9). Step 5 may now start | 5 |
| 2026-08-05 | **Reusing the board⇄tray bridge for a brand-new drag source needed tracing first, not just importing the event names.** `PB_DND_START_EVENT` docs itself as "tray→board" and `PB_BOARD_DND_START_EVENT` as "board→tray" — dispatching only the board→tray half from `TrackRow` would have made the tray preview-accept a drop that silently no-ops (the board's own live `dnd`, which the drop handler actually reads, stays null), reproducing the exact "accept preview lies" bug class E3 flagged for the library bucket. Read both listeners (`BucketBoard.tsx` `onDndStart`, `lib/pocketBuckit/boardDnd.ts`) before reusing them: both populate their target generically from *any* dispatcher, so `TrackRow`'s `drag` slot dispatches **both** pairs and a future grant works against either drop target with no additional wiring | 5 |
| 2026-08-05 | **`memo-trow`'s whole-row click needed a real design decision, not a one-line reuse of `open`.** `open` wraps only the identity cell (cover+text) — established behavior for its two existing consumers, not something to change. memo-trow's row has nothing else to click, so a new `openLyrics` action makes the OUTER row element (`no`+identity+`cells` together) the target, via `role="button"` + manual keyboard handling, not a nested `<button>` (invalid HTML if `open` were reused as-is). Verified live via CDP against a real bucket album, not just the vitest cases, since a synthetic harness can't catch a click-target that's visually a full row but functionally only the title text | 5 |
| 2026-08-05 | **E6's summary sentence corrected** (external review item 8, `ARCH-entity-interaction-domain-audit`): the prose read as "picks by screen context," which is not what the code does and is not what the actual justification (the `ent:*` event can't carry writable context) requires. Traced every `openAlbum()`/`onOpen(DetailTarget)` call site: the split is data-driven (does this album instance carry an editable `DetailTarget`?), not location-driven — `NowPlaying`/`PocketTray`/`PlaybackPanel` call the read-only path from inside the member dashboard, and `ReviewsTab.tsx` branches per-row on `!hasPost && albumId` within a single surface. No code change; the decision (two hosts, split on write-context not location) already matched this — only the sentence describing it was imprecise | 2 |
| 2026-08-05 | **G4's "now prohibited" foreign-namespace-id rule (2026-08-04, this table) had a live, unfixed instance**, found by the same external review (item 9): `releaseShared.tsx:213-214`'s `openReleased()` falls back to `dbId ?? spotify_album_id` into `OpenAlbumDetail.albumId` on a resolve miss — exactly the G4 pattern this RFC declared prohibited the day before, left unconverted. Fixed (front #358): `OpenAlbumDetail` gained an `unresolved` flag, and `AlbumDetailView`/`AlbumOverlay` gate the two DB-id-dependent write actions (play, `AlbumRatingBlock`) on it, so the header-only degrade this fallback exists for is preserved without letting a Spotify id reach a write call. A second, structurally identical gap was found and fixed in the same PR: `BucketBoard.tsx`'s `insertAlbum` (drag move/reorder) had no `temp:`-client-id guard, the same bug class BUG-20 (front #355) fixed for `trashAlbum` but left open for the move path | 5 |
