# FEAT-liked-tracks-workbench: 분석 버킷 redesign — Liked Tracks workbench

- **Status**: in-progress (accepted + steps 1–3 started on owner go-ahead, 2026-06-21)
- **Owner**: TBD
- **Created**: 2026-06-21
- **Plan row**: `plan.md` → FEAT-liked-tracks-workbench
- **Supersedes the UI of**: FEAT-genre-artist-distribution (the current 분석 버킷; backend kept)
- **Reuses**: the 평론 버킷 bucket API (`/api/buckets`) + `BucketPickerSheet` (per owner request: "필요한 api·기능 있으면 평론 버킷 참조해서 구축")
- **Design source**: claude.ai/design `ratemymusic` → `회원 페이지.html` (`liked-tracks.jsx` `LikedBoard` + `liked-analysis.jsx` `LikedAnalysis`)

---

## Goal

The `/profile` **분석 버킷** tab becomes a critic's **"좋아요한 트랙(Liked Tracks)" workbench** instead of a single flat distribution chart. The owner can browse their whole Spotify 좋아요 set as a sortable/filterable track table (list + card views), see live analysis over the current filter (genre · artist · decade · likes-over-time), and act on each track — open album detail, **담기 to a 평론 버킷** (reusing the review-bucket API), or jump to `/write`. The redesign is **mostly frontend**: the backend already serves the rich per-track fields the current UI ignores; only a small additive widening (per-track `genre`) is needed for v1.

## Non-goals

- **좋아요 해제 / unlike (Spotify write-back)** — the design shows it, but it mutates the owner's real Spotify library and needs a new SQS→worker DELETE `/me/tracks` path (rule #9). Deferred to an optional later step (Step 5), default **out** for v1.
- **길이(duration) column, total-duration in the hero, sort-by-length** — `spotify_saved_tracks` has **no duration column**; adding it is a cross-repo shared_db + worker change. Deferred to an optional step (Step 4), default **out** for v1.
- The **track table, hero, classify facets, 연대 분포, 좋아요 흐름** are **liked-only**. The analysis panel's 장르·아티스트 *distribution* keeps a 좋아요/재생 source toggle (decided 2026-06-21), but the rest of the workbench does **not** gain a 재생 view.
- **mood / energy / hue** — present in the design's mock data, not stored in our DB, not surfaced.
- No new social/identity surface, no public exposure of the liked set (스테이 owner-only, behind the `/profile` auth guard).

## Current state

- **Tab wiring**: `myblog_front/src/components/member/ProfileApp.tsx:20` maps `{ id: 'stats', label: '분석 버킷' }` → `ProfileApp.tsx:301` renders `<StatsTab />`.
- **Current 분석 버킷 UI**: `myblog_front/src/components/member/StatsTab.tsx` (FEAT-genre-artist-distribution, accepted 2026-06-21) — one flat panel: source toggle 좋아요/재생, dimension toggle 장르/아티스트, chart-style toggle, a `<DistChart>`, a 미분류 row with `분류하기`/`장르 채우기`, and a "최근 좋아요" list of the **top 12** saved tracks rendering **only `track_name` + `artist_name`** (it discards the rest of the payload).
- **Front API client**: `myblog_front/src/components/member/analysis.api.ts`
  - `GET /api/library/saved-tracks/{genre,artist}-distribution`, `GET /api/library/play-events/{genre,artist}-distribution` → `DistributionResponse` (edge_guard, no JWT).
  - `GET /api/library/saved-tracks?limit=60` → `{ items, total, last_synced_at }`.
  - `POST /api/library/saved-tracks/classify`, `.../fill-genres` → Cognito-JWT, enqueue-only (rule #9).
- **Backend already serves rich saved-track data** (the UI just ignores it). `myblog_backend/app/api/schemas.py:512` `SavedTrackItem` = `{ spotify_track_id, track_name, artist_name, album_name, album_sid, album_id, album: AlbumBrief, added_at }`. `AlbumBrief` (`schemas.py:190`) = `{ id, title, cover_url, release_date, popularity, artist_names, genres }`. Serialized at `library.py:235` `list_saved_tracks` (default `limit=200`, max 500, ordered `added_at DESC`).
  - ⚠ The `_album_brief` helper (`library.py:51`) does **not** populate `AlbumBrief.genres` (defaults to `[]`), so per-track genre is **not** currently reachable from the list payload.
- **Data model**: `myblog_shared_db/src/myblog_shared_db/models.py:682` `SpotifySavedTrack` = `spotify_track_id (PK)`, `track_name`, `artist_name`, `album_name`, `album_sid`, `track_id (FK→tracks, nullable)`, `album_id (FK→albums, nullable)`, `added_at (NOT NULL, indexed)`, `synced_at`. **No `duration_ms`.** Genre is not stored — it resolves at read time (`library_service._resolve_saved_genre`: `track_genres` override → `album_genres` inherit → `None`).
- **Worker sync** (`myblog_worker/worker/service/saved_tracks_sync_service.py`) upserts each saved track, resolving `album_id`/`track_id` best-effort and writing the real Spotify `added_at`. So `added_at` and `album_id` are **populated in prod** today.
- **평론 버킷 (reference, already built)**: `myblog_backend/app/api/routes/buckets.py` — `POST /api/buckets/{bucket_id}/items {album_id, note?}` → `BucketItemResponse` (409 on duplicate), `GET /api/buckets` (nested tree, Cognito-JWT), `POST /api/buckets {name, color?}`. Front: `myblog_front/src/lib/buckets.ts` (`listBuckets`, `addBucketItem`, `createBucket`), `BucketBoard.tsx`, and `BucketPickerSheet.tsx` (a touch bottom-sheet bucket picker we can reuse for the promote action).

## Target state

`StatsTab.tsx` is replaced by a `LikedBoard` workbench (ported from the design `liked-tracks.jsx` / `liked-analysis.jsx`, adapted to real data + the `member.css` / `lf-*` design system, no inline-style prototype):

1. **Hero** — total 곡 count + distinct-artist count (duration-derived stats deferred to Step 4).
2. **Analysis panel** (toggle `분석 보기/숨기기`):
   - **장르 분포 · 아티스트 분포** — via the existing `<DistChart>`, accurate over the **whole** set (not the loaded page). A **좋아요/재생 source toggle** here switches the charts between `saved-tracks/{genre,artist}-distribution` and `play-events/{genre,artist}-distribution` (both already built). The toggle scopes the **charts only** — the table / hero / facets / decade / likes-flow stay liked.
   - **연대 분포 (decade)** + **좋아요 흐름 (weekly likes-over-time)** — computed client-side from the loaded rows' `album.release_date` + `added_at`. (Caveat surfaced if the table list is capped — see Step 1/OQ5.)
   - The 미분류 affordance (`분류하기` / `장르 채우기`) lives here, unchanged.
3. **Classify-by facets** — `장르`/`아티스트` toggle → filter pills with counts.
4. **Search · sort · view** — text search (track/artist/album); sort by 최근추가(added_at)/제목/아티스트/앨범/장르 (length deferred); list ⇄ card.
5. **Track table / cards** — cover (+ Spotify mark) · track · artist · album · 추가한 날짜(`added_at`) · row menu; grouped section headers when sorted by artist/genre.
6. **Row menu** — `작품 상세 열기` (existing `AlbumDetail` via `onOpen`) · `평론 버킷에 담기` (Step 3) · `평론 쓰기 →` (`/write`). `좋아요 해제` only if Step 5 ships.

Backend delta for v1: `SavedTrackItem` gains a resolved `genre: Optional[str]` (Step 1). Everything else the redesign needs is already in the payload.

## Steps

### Step 1 — backend: populate `album.genres` on the saved-tracks list (contract-free) ✅ DONE

`myblog_backend`: `list_saved_tracks` (`library.py`) now batch-resolves the page's catalog album genres via `GenreService().labels_map` (the SAME resolver the bucket view + the saved-tracks genre-distribution use) and passes them into each row's `AlbumBrief` (new optional `genres=` arg on `_album_brief`). **Schema-identical** — `AlbumBrief.genres` already exists in the contract, so there is NO `openapi.json` / `api.gen.ts` change and no contract-merge-order dependency; backend and frontend PRs are independent. The /profile facet/chip reads `album.genres[0]` as the primary genre. (Reframed from the original "add a `genre` field" to stay contract-free and unblock full parallelism — see Decisions log. v1 uses the album's primary genre; a per-track `track_genres` override — which the *distribution chart* applies — is not reflected per-row; acceptable for v1.)

**Verification** (done):
```
cd myblog_backend && .venv/bin/python -m pytest -q tests/api/test_saved_tracks.py   # 9 passed
# new test test_list_populates_album_genres asserts items[0].album.genres == [...]
```
**Rollback**: revert the `_album_brief(..., genres=...)` call; `album.genres` returns to `[]`; front shows 미분류.

---

### Step 2 — frontend: port `LikedBoard` workbench over `StatsTab` (core redesign)

`myblog_front`: replace `StatsTab.tsx` body with the `LikedBoard` workbench. Reuse `analysis.api.ts` (extend `SavedTrack`/`listSavedTracks` for the new `genre` + the already-present `album`/`added_at`; fetch the full list — paginate-accumulate via `offset` to a ~1000-row ceiling, then note any overflow; the charts stay accurate via the server distributions regardless). Analysis panel uses the server distribution endpoints for genre/artist **with the 좋아요/재생 source toggle** and computes decade + likes-flow client-side. Port hero, classify facets, search/sort, list/card table, grouped headers, row menu (작품 상세 + 평론 쓰기 only this step). Use `member.css` `lf-*` classes + `Seg`/`SectionTitle`/`AlbumArt`/`Stars` from `ui.tsx`; **no inline-style prototype**. Keep `분류하기`/`장르 채우기` in the analysis panel.

**Verification**:
```
cd myblog_front && pnpm lint && pnpm exec astro check
# browser click-through on /profile → 분석 버킷: toggle analysis, classify genre↔artist,
# search, sort (incl. grouped headers), list⇄card, open album detail. (BUG-11→12 rule)
```
**Rollback**: revert the file; the tab returns to the distribution-only StatsTab.

---

### Step 3 — frontend: `평론 버킷에 담기` (reuse the review-bucket API)

Wire the row-menu `평론 버킷에 담기` to the **existing** review-bucket API: open `BucketPickerSheet` (reused) → `POST /api/buckets/{bucketId}/items { album_id }` via `buckets.ts#addBucketItem`. Enabled **only when `album_id` is present** (catalogued track); uncatalogued rows show a disabled item hinting `분류하기 먼저`. Handle 409 (already in bucket) as a friendly toast. Cognito-JWT (always present on the owner's `/profile`).

**Verification**:
```
cd myblog_front && pnpm lint && pnpm exec astro check
# click-through: 담기 → picker → confirm item appears in 평론 버킷 tab; 409 path; uncatalogued disabled
```
**Rollback**: hide the menu item; no backend change to revert.

---

### Step 4 — (optional) duration: `duration_ms` end-to-end → 길이 / total-duration / sort-by-length

Only if OQ2 = yes. Ordered cross-repo rollout (per `reference-shared-db-cross-repo-rollout`): shared_db `V{N}__add_saved_track_duration.sql` (add `duration_ms int`) → **prod apply before merge** → worker `saved_tracks_sync_service` writes `track.duration_ms` from `/me/tracks` → backend `SavedTrackItem.duration_ms` + serializer → front shows 길이 column, hero total-duration, sort-by-length. Backfill is automatic on the next weekly full sync (or a one-off `mode=full` SQS message).

**Verification**:
```
# shared_db: psql idempotent ALTER applied; worker integration test writes duration_ms;
# backend pytest; front astro check + click-through length sort
```
**Rollback**: column is nullable/additive; front hides 길이 when null.

---

### Step 5 — (optional) `좋아요 해제` (Spotify un-like via SQS worker)

Only if OQ3 = yes. New `DELETE /api/library/saved-tracks/{spotify_track_id}` (Cognito-JWT) → enqueue an SQS un-like job (rule #9: endpoint never calls Spotify) → worker `DELETE /me/tracks` + prune the cache row. Front: optimistic removal + undo toast (re-add on undo before the job lands is best-effort). **Reconciliation risk**: the weekly full sync is the source of truth; document the eventual-consistency window.

**Verification**:
```
# backend pytest (enqueue only); worker integration test for the un-like handler;
# manual: 해제 a throwaway like → confirm it disappears from Spotify after the job
```
**Rollback**: remove the endpoint + menu item; the cache self-heals on the next full sync.

---

## Open questions

All v1-scoping questions were resolved 2026-06-21 (see Decisions log). No remaining blockers; the table-size ceiling (~1000) is the one detail left to tune at implementation time.

## Decisions log

| Date | Decision | Step |
|------|----------|------|
| 2026-06-21 | **재생(play) distribution kept as a 좋아요/재생 source toggle inside the analysis panel** — charts only; table/hero/facets/decade/flow stay liked-only. | 2 |
| 2026-06-21 | **길이/duration deferred — out of v1.** Step 4 (cross-repo `duration_ms`) stays optional, on a later owner go only. | 4 |
| 2026-06-21 | **좋아요 해제 (unlike) deferred — out of v1.** Step 5 (SQS→worker un-like) stays optional, on a later owner go only. | 5 |
| 2026-06-21 | **평론 버킷에 담기 reuses the existing `BucketPickerSheet`** (pick/create any bucket; no hardcoded "좋아요 후보"). | 3 |
| 2026-06-21 | **Table list paginate-accumulates to a ~1000-row ceiling**; charts stay accurate via the server distributions; overflow noted in the UI. | 1, 2 |
| 2026-06-21 | **Step 1 reframed to contract-free**: reuse the existing `AlbumBrief.genres` field (populate it for saved-tracks) instead of adding a new `genre` field — no openapi/`api.gen.ts` change, no contract-merge-order dependency, backend & frontend PRs fully parallel. Trade-off: per-row genre is album-primary only (no `track_genres` override per-row); acceptable v1. | 1 |
| 2026-06-21 | **Status promoted draft → in-progress** on explicit owner go-ahead ("병렬로 작업 진행하자 … 스텝도 병렬 작업 다 하자"). | — |
