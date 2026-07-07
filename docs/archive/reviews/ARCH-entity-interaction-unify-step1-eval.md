# ARCH-entity-interaction-unify — Step 1 structural evaluation (OQ1 crux)

- **Reviewer**: architect
- **Date**: 2026-07-08
- **Scope**: app-wide album-detail overlay — (a) mount same `AlbumDetail` vs (b) extract read-only view
- **Note on the RFC**: `docs/rfcs/ARCH-entity-interaction-unify.md` **does not exist** in the tree
  (only the predecessor `docs/archive/done/rfcs/ARCH-entity-interaction-contract.md`, done). This
  evaluation is grounded in the code + that predecessor + `docs/frontend/component-map.md`. If the
  unify RFC exists elsewhere, re-check my read of OQ1 against it.

All `file:line` refer to `myblog_front/src/` unless noted.

---

## 1. Coupling inventory — what `AlbumDetail` consumes that only exists in `ProfileApp`

**Headline finding:** `AlbumDetail.tsx` imports **no** React context, **no** `usePocket`, **no**
`bucketStore` (grep: 0 hits). Its entire "member context" is **props + the `DetailTarget` data
shape**, and the writable/read split is **data-driven**, not context-driven. This is the single
most important fact for OQ1: there is no `usePocket()`-returns-null crash risk outside the provider,
because `AlbumDetail` never calls `usePocket`.

| Consumed thing | Site | Path needing it | Source |
|---|---|---|---|
| `album: DetailTarget` | `AlbumDetail.tsx:53` | both | prop from `ProfileApp.openDetail` (`ProfileApp.tsx:371-374`). Type lives in **`@lib/member`** (`member.ts:51-87`) — a member module. |
| `reviews: MemberReview[]` | `AlbumDetail.tsx:53-54` | **read (edit-banner detect) + memo gate** | prop; server-built, threaded through `ProfileApp` props. Used only to compute `published` (`:54`) → picks `edit` vs `info` and gates `MemoWindow` (`:59`). Public read: pass `[]` → always `info`. |
| `onClose` | `AlbumDetail.tsx:53` | both | prop (generic). |
| `onMemoSaved` | `AlbumDetail.tsx:53,60,292` | **writable only** | prop → `ProfileApp.memoEdits` ref (`ProfileApp.tsx:367-374`). Member-only staleness bridge. |
| `onOpenLyrics` | `AlbumDetail.tsx:53,207` | **read (가사 action) — privacy-scoped** | prop → `ProfileApp.openStaticLyrics` → the ProfileApp `LyricsSheet` mount (`ProfileApp.tsx:350,480`). Must be **undefined** on public routes (lyric presence is authed-only per CLAUDE.md privacy invariant). Tracklist already omits the button when it's falsy (`AlbumDetail.tsx:207`). |
| `updateBucketItemMemo` | `AlbumDetail.tsx:21,333` | **writable only** | `@lib/buckets` → `apiFetch` PATCH w/ JWT (`buckets.ts:373-381`). Never called unless `writable && bucketId && itemId` (`AlbumDetail.tsx:59`). On a 401 `apiFetch` redirects to login (`api.ts:70-79`) — so it must stay unreachable on public. |
| Read fetch `fetchAlbumDetail` / `getCachedAlbumDetail` | `AlbumDetail.tsx:22,102,112` | both | `lib/albumDetail.ts` — **plain `fetch`, no JWT** (`albumDetail.ts:42-53`), DB-only edge-cached GET. **Already public-safe.** |
| Presentation `./ui` (`AlbumArt`, `fmtTime`, `Seg`, `Stars`), shared `TrackRow`, `lyrics/LyricsSheet` + `DockableLyricsSheet` | `AlbumDetail.tsx:26-29` | read (ui/TrackRow) / writable (sheet dock) | `./ui` is member-folder but presentation-only. `LyricsSheet`/`DockableLyricsSheet` are only reachable via `MemoWindow` (`:644-651`) or `onOpenLyrics` — both member/authed. |

**Read-only path (public-reachable) needs only:** `DetailTarget` display fields
(`album`, `artist`, `cover`, `year`, `albumId`), the plain-fetch read stack, `./ui`, `TrackRow`.
**Writable path (member-only) needs:** `reviews`, `onMemoSaved`, `updateBucketItemMemo`,
`bucketId`/`itemId`/`note`/`prepTonight`, the `MemoWindow` + lyrics-sheet dock subtree.

The branch that separates them is a single data guard: `AlbumDetail.tsx:59`
(`album.writable && !published && album.albumId && album.bucketId && album.itemId → MemoWindow`),
else `StandardModal` (`:65`). A public `DetailTarget` with `writable` unset falls straight to the
read-only `StandardModal` **with no context dependency**.

---

## 2. Recommendation — (b), but a *thin* extraction (structurally forced, not just cleaner)

**Recommend (b): extract a read-only `AlbumDetailView`; keep the writable modal member-side.**

The decisive reason is **not** aesthetics — it is the **event contract (§3)**. The public overlay is
opened by `ent:open-album`, which cannot carry member types (public callers must not import
`@lib/member`). A minimal id-only event therefore **cannot reconstruct** `writable` / `bucketId` /
`itemId` / `reviews` — the exact fields the `MemoWindow`/edit branch needs (`AlbumDetail.tsx:54,59`).
So the app-wide event-driven overlay is **inherently the read-only surface**; the writable memo/edit
flow is intrinsically member-context and stays on `ProfileApp`'s direct-prop mount. OQ1 is thus not
really "one component serves writable + read for everyone" — the writable half can't ride the event.

Given that, (b) is cheap because the read path is **already a self-contained subtree**:
`StandardModal` → `RealBody` (read branch) → `Header` + `InfoBody` + `Tracklist`
(`AlbumDetail.tsx:69-215`). Extracting it is mostly a **prop-narrowing rename** (swap `DetailTarget`
for primitives, drop `reviews`), not a rewrite. `EditBody` (`:256-270`, 평론 보기/수정 chips) and
`MemoWindow` (`:458-654`) stay in the member module; member `AlbumDetail` composes the shared view
for its info body.

**Why not (a):** (a) mounts the *whole* `AlbumDetail` module app-wide — dragging `MemoWindow`,
`useBucketMemo`, `updateBucketItemMemo`, and the `LyricsSheet`/`DockableLyricsSheet` dock into the
**public route bundle**, all dead code there. Two costs: (i) a privacy-boundary smell — lyrics-sheet
wiring shipped to public routes even if runtime-gated (the CLAUDE.md invariant is "no lyric text **or
its presence** on public"; keeping the code out is the honest boundary); (ii) the event still can't
feed the writable branch, so (a) buys the bundle weight without buying writable reuse. (a) *would*
work at runtime (no `usePocket` crash — confirmed §1), so it is not unsafe; it is just strictly
dominated by (b) here.

**On the `usePocket()`-null question in the RFC:** moot. `AlbumDetail` never touches the Pocket
context or `bucketStore`, so mounting it outside `PocketBuckitProvider` does not throw
(`PocketBuckitProvider.tsx:129-133` only throws for *consumers* of `usePocket`, and there are none in
this subtree).

---

## 3. Event contract — minimal payload, but carry display identity (DB `albumId`, not spotify)

Recommend: `ent:open-album` carries **primitives only**, no `DetailTarget`:

```ts
interface EntOpenAlbumDetail { albumId: string; title?: string; artist?: string; cover?: string | null; year?: number | null }
```

Two grounded reasons the payload must be **more than bare `albumId`** yet **less than `DetailTarget`**:

1. **DB `albumId`, not `spotifyAlbumId`.** The whole read stack keys on the DB id: GET
   `/api/music/albums/{id}` (`albumDetail.ts:43`) and the cache Map is DB-id-keyed (`:23,47`). There
   is no spotify→album resolve path in `lib/albumDetail.ts`; a spotify id would need a new endpoint.
2. **Carry `title`/`artist`/`cover`/`year` for the instant header.** `RealBody` seeds the header from
   `DetailTarget` fields *before* the fetch resolves (`AlbumDetail.tsx:143-147`), and a cache **miss
   costs ~1s** (`albumDetail.ts:4-8` comment). An id-only event paints a **blank header for ~1s**.
   Passing display identity keeps the current member-modal snappiness on public opens.

The payload type must live in a **public-safe module** (e.g. a new `lib/entityEvents.ts`), **not** in
`lib/pocketBuckit/events.ts` (that module is member/bucket-scoped) and **not** in `@lib/member`.

---

## 4. Mount mechanics — separate un-gated island; do NOT fold into PocketBuckit; do NOT remove ProfileApp's mount

- **Separate island, un-gated.** `PocketBuckit` returns `null` when `!isLoggedIn()`
  (`PocketBuckit.tsx:82`); the album overlay must serve anonymous visitors, so it is a **distinct
  island** mounted as a sibling in `layout.astro` (near `:63`), **not** folded into `PocketBuckit`.
- **Hydration:** `client:only="react"` + `transition:persist` — mirror `PocketBuckit`
  (`layout.astro:63`). `client:only` because it needs `window` for the event listener; `transition:persist`
  so the listener survives `ClientRouter` view transitions (the codebase already keys client scripts off
  `astro:page-load`, e.g. `albumDetail.client.ts:139`, `albumDetail.fetch.client.ts:17`). Add an
  `astro:page-load`/route-change close so a persisted-open overlay dismisses on navigation.
- **Do NOT remove `ProfileApp`'s mount.** `ProfileApp.tsx:478` renders `AlbumDetail` with the full
  `DetailTarget` (writable) via the `onOpen`→`openDetail` prop chain (`:371-374,425-428`). Member
  surfaces dispatch **no** event — they call `onOpen(DetailTarget)` directly, carrying
  writable/bucketId/itemId the event can't. So the two coexist by **trigger**: member surfaces →
  `openDetail` prop (writable modal); public/anonymous surfaces → `ent:open-album` (read-only host).
  **No double-mount** in the common case (member surfaces never emit the event).
- **Migration boundary to flag:** if any *member* surface is later switched to `ent:open-album`, it
  **loses writable context** (silently degrades to read-only). Keep member surfaces on the prop path
  until/unless the event grows a member variant; document this so a future session doesn't "unify" the
  member call sites onto the lossy event.

---

## 5. Concrete Step-1 outline (behavior-preserving for members)

1. **Extract `AlbumDetailView`** (new `components/album/AlbumDetailView.tsx` or `components/shared/`):
   move the read subtree `StandardModal`→`RealBody`(read)→`Header`+`InfoBody`+`Tracklist`
   (`AlbumDetail.tsx:69-215`) to take **primitives** `{ albumId?, title, artist?, cover?, year?,
   onOpenLyrics? }` — **no `@lib/member` import**. Member `AlbumDetail` keeps `EditBody`
   (`:256-270`) + `MemoWindow` (`:458-654`) and composes `AlbumDetailView` for its info body.
   *Behavior-preserving:* `ProfileApp.tsx:478` still renders `AlbumDetail(DetailTarget, reviews,
   onMemoSaved, onOpenLyrics)`; only its internal read body is now the shared view.
2. **Add `lib/entityEvents.ts`** — export `ENT_OPEN_ALBUM` event name + `EntOpenAlbumDetail` type
   (§3), public-safe (no member/pocket imports).
3. **Add app-wide host** `components/album/AlbumOverlay.tsx` — `client:only="react"` island,
   `useState` open-target, `window` listener for `ENT_OPEN_ALBUM`, renders `AlbumDetailView`
   read-only with `onOpenLyrics` **undefined** (privacy). Mount in `layout.astro` sibling to
   `PocketBuckit` with `transition:persist`; close on `astro:page-load`.
4. **Wire exactly one public caller** to prove the path (or defer caller-wiring to Step 2 if the RFC
   scopes it there) — pick a surface that today navigates to `/review/[slug]`.
5. **`docs/frontend/component-map.md`** — register the app-wide overlay host + `ent:open-album` in
   "Who mounts overlays" (`:119-124`) and "Cross-island events" (`:128-131`); bump the Verified stamp
   (this touches overlay + cross-island per the impact template).

**Top risks + real-browser verification**

- **R1 — privacy (lyrics presence on public).** The public host must pass `onOpenLyrics=undefined` so
  `Tracklist` omits the 가사 button (guard at `AlbumDetail.tsx:207`). *Verify:* open the overlay on a
  public route, inspect a track with a `spotify_id` → no 가사 affordance; grep public bundle for a
  lyrics import from the host path.
- **R2 — header flash.** Id-only event → ~1s blank header on cache miss (`albumDetail.ts:4-8`).
  *Verify:* dispatch `ent:open-album` with `{albumId, title, artist, cover}` → header paints instantly
  (seed at `AlbumDetail.tsx:143-147`); with id-only → observe the 1s blank; confirm payload carries
  display identity.
- **R3 — ESC/overlay stacking on /profile.** Both the member modal and the app-wide host can exist on
  `/profile`. `useDismissable`'s module-level open-overlay stack (component-map `:114`) should make ESC
  close only the top-most. *Verify (CDP):* on `/profile` open the member album modal, ESC closes
  exactly one layer; confirm the idle app-wide host contributes no scrim/trap when no event fired.
- **R4 — persisted-open overlay across nav.** *Verify (CDP):* open the overlay, navigate via
  `ClientRouter`, confirm it dismisses (no stale scrim), and the listener still fires on the next page.

---

## Component-map impact — ARCH-entity-interaction-unify Step 1

```
Verified: 2026-07-08
Routes touched:        layout.astro (app-wide) — public + authed; /profile mount unchanged
Track-click paths hit:  albumdetail-readonly (shared read view); review-tracklist vanilla UNCHANGED
Play path:              none
Overlay changed:        new overlay host (app-wide, reuses StandardModal + useDismissable stack)
State owner:            ad-hoc (host-local open-target) + ent:open-album window event
Cross-island?:          yes (ent:open-album — public-safe, NOT in pocketBuckit/events.ts)
Cache touched:          albumDetail (shared, public-safe plain fetch — unchanged)
Duplicate it overlaps:  album-detail paths (read view now shared; writable stays member-side)
```
