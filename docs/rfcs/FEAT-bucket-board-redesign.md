# FEAT-bucket-board-redesign: Bucket album cards — cover-forward tiles, enriched detail, drag-to-trash delete

- **Status**: draft
- **Owner**: TBD
- **Created**: 2026-06-04
- **Plan row**: `plan.md` → FEAT-bucket-board-redesign

---

## Goal

The `/profile` 평론 버킷 board (`myblog_front`) presents each album as a larger cover-forward tile (the same visual grammar as 「평론한 앨범」), inside a visibly bigger bucket card. Clicking a tile opens a detail slide-over enriched with the album's full tracklist, label, popularity, type, and per-artist photo/genres — all from the **existing** DB-only `GET /api/music/albums/{id}` endpoint, with no synchronous Spotify call. A user can remove a single album from a bucket two ways: a hover ✕ on the tile, or dragging it onto a 휴지통 drop zone; both route through a confirm modal before deleting via the **existing** `DELETE /api/buckets/{bucket_id}/items/{item_id}` route. The current vertical-text layout defect in the album chip is gone.

## Non-goals

- **No backend, contract, infra, or shared_db change.** The delete-item route (`buckets.py:267-277`, `apigateway.tf` `buckets_items_delete`) and the rich detail endpoint already exist in prod. `api.gen.ts` does not change (DELETE returns 204, no typed body).
- **No synchronous Spotify call.** Detail enrichment reads only what the worker has already synced to the DB (CLAUDE.md rule #9). Albums missing tracks in the DB simply render without a tracklist — no on-demand fetch-from-Spotify.
- **No soft-delete / 휴지통 보관/복구.** Delete is permanent-after-confirm (user picked the confirm-modal option, not the recoverable-trash option). No `deleted_at` column, no restore UI.
- **No card-level enrichment.** Popularity/tracklist/label stay in the slide-over only; the bucket list response (`BoardAlbum`) is unchanged, so no extra per-card fetch and no backend field add.
- **No change to bucket nesting, move, reorder, or add-album flows.** Those Step 5 behaviors stay as-is.

## Current state

- **Album chip** — `myblog_front/src/components/member/BucketBoard.tsx:78-104` (`AlbumChip`). A fixed `width:184` horizontal card: 42px cover left, then title (serif) + artist (sans) + 평론함/미평론 badge stacked in a `flex:1, minWidth:0` text column. Title/artist already carry `whiteSpace:'nowrap'` + ellipsis. Rendered in a horizontal-scroll row at `BucketBoard.tsx:235` (`minHeight:78`). **Reported defect: album text renders vertically (one char per line).** Root cause is not visible in this markup on desktop (nowrap is present); the redesign supersedes it regardless (see Step 1 note).
- **Detail slide-over** — `myblog_front/src/components/member/AlbumDetail.tsx`. `RealBody` (lines 39-61) shows only cover + title + artist + release year. A stale comment claims *"Spotify gives us no tracklist here"* — untrue: the worker syncs tracklist/label/popularity to the DB (`myblog_worker/.../sync_service.py`), exposed by `GET /api/music/albums/{id}`.
- **Reviewed-album tile (design reference)** — `myblog_front/src/components/member/LibraryTab.tsx:289-318` (`ReviewedSection`). Grid `repeat(auto-fill, minmax(160px,1fr))`; each item is a column: full-width square `AlbumArt` on top, title (serif italic 16px, nowrap ellipsis) + artist (mono uppercase, nowrap ellipsis) below; optional badge overlay on the cover. This is the target card grammar.
- **Delete** — none for a single item. `buckets.ts` exposes `deleteBucket` (whole bucket) but no `deleteBucketItem`. Backend `DELETE /api/buckets/{bucket_id}/items/{item_id}` **already exists and is wired through API Gateway** — only the frontend client + UI are missing.
- **Detail endpoint** — `GET /api/music/albums/{id}` → `AlbumDetail` = `AlbumOut` (release_date, cover_url, album_type, label, popularity, external_url) + `ArtistOut[]` (photo_url, genres, followers_count, popularity, spotify_url) + `TrackOut[]` (track_no, title, duration_sec, feat_artist_names). Public DB read. Frontend already calls this base elsewhere via `import.meta.env.PUBLIC_API_URL` with plain `fetch` (`AddAlbumModal.tsx:151`, `WriterApp.tsx:142`).
- **DnD payload** — module-level `dnd` in `BucketBoard.tsx:18` already carries `{kind:'album', itemId, fromBucketId}` on album drag start.

## Target state

- **`AlbumChip` → cover-forward tile** matching the `ReviewedSection` grammar: full-width square `AlbumArt` on top, title (serif italic) + artist (mono uppercase) below, both nowrap+ellipsis on a full-width block (no horizontal flex squeeze). 평론함/미평론 shown as a small overlay/meta. Tiles are `flex:'0 0 <W>'` (W ≈ 132–140px) in the existing horizontal-scroll row, which grows taller — making the bucket card visibly bigger. Bucket panel padding/min-height bumped so the bigger tiles breathe. A hover ✕ delete affordance sits on each tile.
- **`RealBody` enriched**: on open, fetch `${PUBLIC_API_URL}/api/music/albums/{albumId}`; render larger cover, title, artist(s), a meta row (album_type · release_date · total_tracks · ●popularity · label), per-artist strip (photo + genres), and the full tracklist (track_no · title · mm:ss · feat). Loading + error states; on fetch failure fall back to today's minimal cover+title+artist+year card (graceful degrade). Stale "no tracklist" comment removed.
- **Delete**: new `deleteBucketItem(bucketId, itemId)` in `buckets.ts` (calls the existing DELETE route via `apiFetch`). A 휴지통 drop zone in `BucketBoard` (always present at the board foot beside "최상위로 빼기", highlighted while an album is dragged). Dropping an album there, or clicking a tile's hover ✕, opens a confirm modal ("이 앨범을 버킷에서 뺄까요?"). Confirm → optimistic removal from `tree` + DELETE, `refresh()` on failure. Cancel → no-op.

## Steps

Steps are **frontend-only and additive**. They can ship as three small PRs (default; each gets a browser click-through + prod observe) or be bundled into one PR if the user prefers — note the bundling choice in the plan row. Order: Step 1 first (it removes the layout defect); Steps 2 and 3 are independent of each other.

### Step 1 — Cover-forward album tile + bigger bucket

Replace `AlbumChip` (`BucketBoard.tsx:78-104`) with a column tile mirroring `ReviewedSection`'s markup (`LibraryTab.tsx:294-315`): square `AlbumArt` on top sized to the tile width, title + artist block below (nowrap+ellipsis on a full-width div — structurally immune to the vertical-text squeeze), 평론함/미평론 as a cover overlay or sub-meta. Keep `draggable` + the existing `onDragStart/onDragEnd/onClick(onOpen)` wiring and `lf-drag-handle`/`lf-is-dragging` classes. Set tile `flex:'0 0 ~136px'`; bump the album-row container (`BucketBoard.tsx:235`) min-height and the bucket panel padding so the larger tiles fit. Update the empty-state cell height to match.

> **Vertical-text note**: `ReviewedSection` uses the same nowrap pattern and does **not** break, so the defect is chip-layout-specific (the row/flex context), not a global CSS rule. The column tile gives the text full tile width, eliminating the squeeze regardless of the exact trigger. Step is verified by a real browser click-through with a long-title / Korean-title album (per the realistic-data repro rule), not just `astro check`.

**Verification**:
```
cd myblog_front && pnpm lint && pnpm exec astro check
# browser: /profile bucket board renders cover-forward tiles, long/Korean titles ellipsis (not vertical), horizontal scroll + drag-between-buckets still work
```

---

### Step 2 — Enriched detail slide-over

In `AlbumDetail.tsx`, make `RealBody` fetch `${import.meta.env.PUBLIC_API_URL}/api/music/albums/${album.albumId}` on mount (plain `fetch`, public read; guard missing `albumId`). Render: larger cover; title + artist(s); meta row (album_type · release_date · total_tracks · ● popularity · label); per-artist strip (photo_url + genres); full tracklist (`track_no` · title · `duration_sec`→mm:ss · feat_artist_names). Add loading + error states; on failure or empty payload, fall back to the current minimal card. Remove the stale "Spotify gives us no tracklist" comment. No `DetailTarget` field change (data comes from the fetch, keyed by `albumId`).

**Verification**:
```
cd myblog_front && pnpm lint && pnpm exec astro check
# browser: click a bucket album with synced tracks → tracklist + label + popularity + artist genres show; click one without synced tracks → graceful minimal fallback, no console error
```

---

### Step 3 — Single-album delete (hover ✕ + drag-to-trash) with confirm modal

Add `deleteBucketItem(bucketId, itemId)` to `buckets.ts` (DELETE `${BASE}/api/buckets/${bucketId}/items/${itemId}` via `apiFetch`, `expectNoContent`). In `BucketBoard`: add a `pendingDelete` state and a confirm modal (styled like the existing `qb-modal`/`lf-panel`); add an `ops.deleteItem(itemId, fromBucketId)` that optimistically splices the item from `tree`, calls `deleteBucketItem`, and `refresh()`es on failure. Wire two entry points, both opening the confirm modal: (a) a hover ✕ on each tile; (b) a 휴지통 drop zone at the board foot (beside the existing root-eject zone, `BucketBoard.tsx:432-455`) that `preventDefault`s + highlights when `dnd.kind==='album'` and on drop sets `pendingDelete`. Keep the localStorage bucket-count mirror (`BucketBoard.tsx:275-282`) in sync after delete.

**Verification**:
```
cd myblog_front && pnpm lint && pnpm exec astro check
# browser: drag album → 휴지통 zone → confirm modal → confirm removes it (and survives reload); cancel keeps it; hover ✕ opens the same modal; move-between-buckets unaffected
```

**Rollback**: revert the PR; no persisted state shape changed (delete is an existing idempotent route).

---

## Open questions

1. **Bucket album layout: horizontal-scroll vs wrap grid** — keeping the horizontal-scroll row preserves the "한 가로줄 = 버킷" model and the nesting layout (default). A wrapping grid (like 평론한 앨범) shows more at once but changes the row metaphor. Blocks Step 1's container choice. *Default: horizontal scroll with taller tiles.*
2. **Vertical-text root cause confirmation** — a screenshot + viewport (PC/mobile) would confirm the defect's exact trigger. Not blocking (Step 1's column layout fixes it either way), but useful to rule out a deeper global-CSS issue affecting other surfaces.
3. **Trash zone visibility** — always-visible (clear affordance) vs appears-only-while-dragging (less clutter). Blocks Step 3 styling. *Default: always present, highlight on album drag.*

## Decisions log

| Date | Decision | Step |
|------|----------|------|
| 2026-06-04 | Card grammar = 「평론한 앨범」 cover-forward tile, grouped in a bigger bucket card | 1 |
| 2026-06-04 | Delete UX = confirm modal (not recoverable-trash, not silent-delete) | 3 |
| 2026-06-04 | Detail enrichment = slide-over only via existing `/api/music/albums/{id}`; cards unchanged | 2 |
| 2026-06-04 | Design owned by agent against the `lf-` editorial system | all |
| 2026-06-04 | Frontend-only: delete route + detail endpoint already exist in prod; no backend/contract/infra change | all |
