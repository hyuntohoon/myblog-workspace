# FEAT-writer-lowfreq-redesign: Writer page → Lowfreq design parity

- **Status**: draft
- **Owner**: TBD
- **Created**: 2026-05-31
- **Plan row**: `plan.md` → FEAT-writer-lowfreq-redesign
- **Design source**: Claude Design bundle "Lowfreq Writer.html" (`fitchpork-style-magazine-website/project/`). Extracted reference at `/tmp/lowfreq-design/` during drafting; the prototype itself is not checked in.

---

## Goal

Bring the live `/write` page (`myblog_front/src/components/writer/*`) to parity with the latest Lowfreq Writer prototype: (1) Spotify-style **artist drill-in** in the subject picker (works for cold Spotify artists via a pending-then-poll flow), (2) single **DB ↔ Spotify source toggle** with loading affordance, (3) **BEST NEW MUSIC** flag end-to-end as an **album-level** boolean (DB → API → writer toggle → preview banner), (4) **preview polish** (drop-cap, styled blockquote), (5) **body toolbar** micro-refinement. Each step ships as its own PR per CLAUDE.md rule #4. The existing `RecommendedTracksBlock` position (between subject card and title) is the target placement — confirmed during RFC review, no move required.

## Non-goals

- **No new music search behavior** beyond what the existing `/api/music/...` endpoints support — artist drill-in uses DB-derived data only (sync Spotify on user request would violate CLAUDE.md rule #9).
- **No redesign of `/blog`, `/blog/[slug]`, or other pages** — this is writer-only. The Lowfreq bundle also contains Magazine/Article/Artist/Browse prototypes; those are out of scope here.
- **No change to publish-to-Git pipeline** (`POST /api/publish`), Cognito auth flow, or the Astro static build/deploy.
- **No track/artist rating** — album-only rating is the product decision (see [[project-feature-roadmap]]).
- **No removal of `RecommendedTracksBlock`** — it stays as a writer feature, only repositioned.

## Current state

`myblog_front/src/pages/write.astro` mounts `WriterApp` (`src/components/writer/WriterApp.tsx`) as a client-load React island inside `write-layout.astro`. Component tree:

- `WriterChrome.tsx` — sticky top bar (back / Lowfreq logo / save / publish / view-toggle / status).
- `SubjectBlock.tsx` (~20 KB) — search panel with **two separate buttons** for DB search vs Spotify sync, 3-column tile grid, filled `hdr-card` (cover + title + stars + numeric score). Artist tiles **select the artist directly as the subject** — no drill-in.
- `RecommendedTracksBlock.tsx` — rendered between subject and title (writer-only addition; not in the design).
- `BodyArea.tsx` — `<textarea>` + floating bubble toolbar (B / I / " / blockquote) — already present.
- `SettingsPanel.tsx` — right-side slide-in: section + publish date + checklist + save-draft + publish.
- `PreviewView.tsx` — renders subject card + headline + dek + paragraphs; no drop-cap, basic blockquote.
- `types.ts` — `DraftPersist`, `AlbumDetail`, `RecommendedTrack`. No `bestNew`.

Backend / contract surface:
- `GET /api/music/search/unified` (DB-first), `GET /api/music/search/candidates` (Spotify candidates, enqueues absorb), `GET /api/music/albums/{album_id}`, `GET /api/music/albums/by-spotify/{spotify_album_id}`, `GET /api/music/artists/{artist_id}/albums` — already exist.
- `POST /api/posts`, `PUT /api/posts/{id}`, `POST /api/publish` — used by writer. **No `best_new` field anywhere** (`Backend_WritePostRequest`, `posts` table — `myblog_shared_db/src/myblog_shared_db/models.py:195`).
- No artist-hero or top-tracks endpoint. `Artist` model has `followers`, `popularity`, `genres`, `photo_url`. `Track` model has internal `views` counter (no Spotify play count).

## Target state

After all steps:

1. **Subject picker** has a single segmented toggle `[ 내부 DB | Spotify ]` (Spotify lit green when active, spinner while candidates fetch).
2. **Clicking an artist tile** opens an inline `ArtistDetail` panel with hero (photo + name + genres + followers), top tracks list, and discography grid — each item selectable as the subject. "이 아티스트를 리뷰 →" picks the artist itself. **Spotify-cold artists**: the lookup returns a `pending` state, the panel shows a "처리 중" indicator and polls until the absorb worker writes the row, then transitions to the full detail.
3. **`hdr-card`** has a `BEST NEW` toggle pill bound to `albums.best_new` (a new boolean column). Toggling reflects in the preview banner and is written to the DB on draft/publish via the post payload.
4. **Preview** shows a drop-cap on the first paragraph, styled accent-bordered blockquote, and `BEST NEW MUSIC` banner above the headline when the subject album's `best_new = true`.
5. **Body toolbar** keeps current behavior but matches the prototype's pill geometry (rounded, soft shadow).
6. **RecommendedTracksBlock** stays where it is (between subject card and title) — no move.

## Steps

Steps 1 / 2 are frontend-only and independent (any order). Step 3 must land before Step 4; Step 5 must land before Step 6 (data first, UI second).

---

### Step 1 — Preview polish + body toolbar refinement (frontend-only)

`myblog_front` only. CSS-only changes plus a small structural tweak in `PreviewView.tsx`.

- Add `.prev-body p:first-of-type::first-letter` drop-cap rule (accent color, ~4em float-left). Skip when the first paragraph is the placeholder empty state.
- Replace plain `<blockquote>` with `.prev-quote` rule from the prototype (border-left accent, italic, 1.5em margin).
- Refine `.bubble-toolbar` to the prototype's geometry (4px padding, 6px radius, deeper shadow, 28×28 buttons).

**Verification**:
```
cd myblog_front && pnpm lint && pnpm exec astro check
# Manual: dev server → /write → drop-cap visible on first paragraph in preview;
# blockquote shows accent left-rule + italic; selection toolbar geometry matches design.
```

**Rollback**: revert CSS hunk in `write-layout.astro` (or wherever writer.css lives).

---

### Step 2 — Source toggle redesign (frontend-only)

`myblog_front` only. Refactor the search panel header inside `SubjectBlock.tsx`.

- Replace the two separate "검색 / Spotify 싱크" buttons with a single segmented `hdr-source-row` matching the prototype (`<button class="hdr-source-btn">` × 2, the active one fills with `--ink` (DB) or `#1DB954` (Spotify); inactive sits on `--bg`).
- Show the Spotify SVG mark inside the right button. Add `.hdr-spinner` while candidates fetch.
- Spotify tile badge (bottom-right SVG mark) and `.is-spotify` hover border (green) — already partly present, normalize against prototype values.
- **Behavior preserved**: existing 3 s Spotify cooldown (`syncCooldownRef`) still applies. Switching to Spotify with no query shows the full pool tile grid, same as DB.

**Verification**:
```
cd myblog_front && pnpm lint && pnpm exec astro check
# Manual: /write → toggle between DB and Spotify; confirm spinner during sync,
# tile badges, and that the cooldown gate still blocks rapid re-syncs.
```

---

### Step 3 — Backend: artist-hero + top-tracks + spotify-id lookup

`myblog_music` (route+service) → `infra/apigateway.tf` entries → `openapi.json` regen. Single PR.

Three new endpoints (DB-only; no synchronous Spotify call — rule #9). All go in `app/api/routers/artists.py` (file already exists).

- `GET /api/music/artists/{artist_id}` → `ArtistHero`:
  ```
  { id, name, photo_url, genres[], followers, popularity, spotify_url,
    album_count, track_count, status: "ready" }
  ```
  Source: `Artist` row + counted joins. 404 on miss (an unknown internal UUID is a real not-found).

- `GET /api/music/artists/by-spotify/{spotify_id}` → `ArtistHero`:
  Three response shapes by state:
  - **Absorbed** (`artists.spotify_id = :sid` row exists) → 200, same body as above with `status: "ready"`.
  - **Pending** (no row yet but a candidate absorb job is in-flight for this Spotify ID — see [[reference-workspace-no-infra-autoapply]] for the SQS/worker pattern) → 200 with `{ status: "pending", spotify_id, name?, photo_url? }` (name/photo from the original candidates payload if cached; otherwise omitted). Frontend polls.
  - **Truly unknown** (no row, no pending job) → 404. Frontend can fall back to enqueuing a fresh candidates fetch.

  Pending detection: query existing `candidate_jobs` / equivalent absorb-tracking table (verify name during implementation). If no such table exists, this endpoint reduces to "row exists → ready, else 404" and Step 4's frontend polls on the 404 path instead — but the design intent is the 200/pending split.

- `GET /api/music/artists/{artist_id}/top-tracks?limit=10` → `Music_TrackOut[]`:
  Ordering (confirmed):
  1. `tracks.views DESC`
  2. tie → `albums.popularity DESC NULLS LAST`
  3. tie → `albums.release_date DESC NULLS LAST`
  4. tie → `tracks.track_no ASC` (stable)

  Covers cold-catalog case where `views` is uniformly 0 and `popularity` is flat — newest album wins. Selects across every album the artist credits on (`album_artists` join).

No DB migration. Three handlers + Pydantic schemas + 3 `infra/apigateway.tf` entries.

**Verification**:
```
cd myblog_music && uv run pytest tests/api/test_artists.py -q
# Targeted cases: ready/pending/404 for by-spotify; ordering invariants for top-tracks.
# Per [[feedback-local-db-smoke-fallback]]: pytest + lint is the local gate if no DB.
```

**Post-merge**: hit prod for each of the three endpoints (`{id}`, `by-spotify/{sid}`, `{id}/top-tracks`), quote shapes in PR comment ([[feedback-prod-smoke-required]]).

**Rollback**: route removal is non-destructive (no schema). Revert PR.

---

### Step 4 — Frontend: artist drill-in with pending poll (depends on Step 3 contract)

`myblog_front` only. Depends on Step 3's contract being merged into `docs/contracts/openapi.json` and `api.gen.ts` regenerated ([[reference-workspace-contract-merge-order]] — workspace first, service notify becomes a no-op).

- New `src/components/writer/ArtistDetail.tsx` — hero (cover circle, name, kicker "장르 · 팔로워 N"), `art-tracks` ordered list, `art-albums` 3-column grid. Each row/tile takes an `onPick(item)` callback. **Pending variant**: a single skeleton row with a small spinner and "Spotify에서 가져오는 중…" text — same component, branch on `status`.
- New `src/scripts/write/artistApi.ts` — `fetchArtistHero(id)`, `fetchArtistHeroBySpotify(spotifyId)`, `fetchArtistTopTracks(id)` typed against `api.gen.ts`.
- In `SubjectBlock.tsx`: add `viewArtist` state. When an artist tile is clicked:
  - **DB tile** → call `fetchArtistHero(item.id)` → render full detail.
  - **Spotify tile (no internal id yet)** → call `fetchArtistHeroBySpotify(item.spotify_id)`. On `status: "pending"`, render pending variant and poll every 2 s (max 30 s) until `status: "ready"`, then swap to full detail. On 404, surface "데이터를 가져올 수 없습니다" with a retry button that re-enqueues via the existing candidates flow.
  - "← 검색 결과" button cancels any pending poll and clears `viewArtist`.
- Artist-itself selection ("이 아티스트를 리뷰 →"): calls `onSubjectSelect` with the artist payload (existing path — backend accepts `artist_ids` in the post payload). For artist-only subjects, cover falls back to `photo_url`.

**Verification**:
```
cd myblog_front && pnpm lint && pnpm exec astro check && pnpm generate:types
git diff --exit-code src/lib/api.gen.ts   # regenerated types match what code typed against
# Manual via Playwright pattern [[reference-playwright-e2e-pattern]]:
#   /write → DB source → search "이수란" → click artist → hero + tracks render → click a track → subject card updates, panel closes.
#   /write → Spotify source → search a cold artist → click → pending skeleton → (wait for worker absorb) → full detail.
```

**Rollback**: feature lives behind one new file + state branch in `SubjectBlock`. Revert the PR.

---

### Step 5 — Backend: `albums.best_new` column + payload pass-through

Cross-repo: `myblog_shared_db` (Alembic migration) → `myblog_music` (`Music_AlbumOut` / `Music_AlbumItem` schemas) → `myblog_backend` (publish payload pass-through) → `openapi.json` regen for both services. No `infra/apigateway.tf` change (no new paths).

**Why album-level, not post-level**: BEST NEW is a property of the album itself, not of any single review of it. Multiple posts can reference one album; the badge belongs to the album. Editorial workflow (Step 6's writer toggle) sets it manually at publish time.

- **Migration** (`myblog_shared_db`):
  ```sql
  ALTER TABLE albums ADD COLUMN best_new BOOLEAN NOT NULL DEFAULT FALSE;
  CREATE INDEX idx_albums_best_new ON albums (best_new) WHERE best_new = true;
  ```
  Partial index — most rows are false; this keeps the index tiny and fast for "list BNM" queries the magazine page will eventually want.
  Per [[feedback-credential-rotation-console-only]]-style caution: additive with default, no rotation risk. Normal deploy path.

- **`Music_AlbumOut` / `Music_AlbumItem`** (`myblog_music`): add `best_new: bool` (default false) so the writer reads the current state when loading the subject card.

- **Publish/draft payload** (`myblog_backend`, `Backend_WritePostRequest`): add optional `subject_best_new: bool | None = None`. When non-null AND the post has exactly one `album_ids` entry, the backend UPDATEs `albums.best_new` for that album inside the same transaction as the post insert/update. When null, the album's flag is untouched.
  Why payload-embedded vs separate PATCH endpoint: single auth gate (Cognito JWT on `/api/posts/*`), atomic write, avoids a second admin surface that would need its own permissions.

- **`POST /api/publish`** (frontmatter): pass `best_new: <bool>` through to the MDX frontmatter so the static Astro build can render the badge later. Read from the album, not the request — keeps frontmatter consistent with DB.

- **`Backend_PostOut`** (fetch single post): include `subject_best_new` (joined from the album) so the writer's edit flow can prime the toggle on load.

**Verification**:
```
cd myblog_backend && uv run pytest tests/api/test_posts_write.py -q
cd myblog_music && uv run pytest tests/api/test_albums.py -q
cd myblog_shared_db && alembic upgrade head   # local DB; or skip per [[feedback-local-db-smoke-fallback]]
```

**Post-merge prod smoke**: create a draft for an album with `subject_best_new=true`, GET `/api/music/albums/{id}` and confirm `best_new=true`; re-PUT post with `subject_best_new=false`, GET again, confirm cleared. Quote both in PR comment.

**Rollback**: migration is additive (drop column + drop index). Safe.

---

### Step 6 — Frontend: BEST NEW toggle + preview banner (depends on Step 5)

`myblog_front` only. Depends on Step 5's contract.

- `types.ts`: add `subjectBestNew?: boolean` to `DraftPersist`. `Partial<DraftPersist>` silently drops unknown keys — old drafts read `undefined` (= falsy = off), no migration code.
- `WriterApp.tsx`:
  - Add `subjectBestNew` state. On subject pick, seed it from the fetched album's `best_new`. On subject swap (different album), reseed from the new album. Include in autosave persist.
  - Thread into `savePost` / `updatePost` payloads as `subject_best_new`.
  - On edit-mode load (`?id=` path), seed from the post response's `subject_best_new`.
- `SubjectBlock.tsx` filled-card: add `.hdr-bnm` toggle pill from the prototype, bound to `subjectBestNew`. Hide when no subject selected.
- `PreviewView.tsx`: render `.prev-bnm` accent banner above headline when `subjectBestNew === true`.
- Subtle UX detail: if the user toggles BEST NEW but doesn't yet have a subject, the toggle is hidden — the state has no meaning without a target album.

**Verification**:
```
cd myblog_front && pnpm lint && pnpm exec astro check && pnpm generate:types
git diff --exit-code src/lib/api.gen.ts
# Manual: pick an album → toggle BEST NEW → preview shows banner; save draft;
# refresh page; confirm pill state restores from DB. Pick a different album
# that already has best_new=true; confirm pill shows the seeded value.
```

---

**Note: no Step 7.** RecommendedTracksBlock keeps its current position (between subject card and title) — confirmed during RFC review. No code change.

**Note: weekly upkeep batch (auto-clear stale BEST NEW)** — deferred to a follow-up RFC. Scope (for posterity): Friday EventBridge cron flips `albums.best_new` back to false when the album is outside the release window OR its editor rating < 4. The batch only *clears*, never enables — curation stays human. No DB migration in the follow-up (column ships in Step 5). Release-window length TBD.

---

## Open questions

_All four questions raised in the first draft were resolved during RFC review on 2026-05-31. See Decisions log below._

1. ~~**Drill-in for Spotify-only artists.**~~ Resolved → option (b) with pending poll. See Step 3 / Step 4.
2. ~~**`top-tracks` ordering tie-break.**~~ Resolved → `views DESC → albums.popularity DESC → albums.release_date DESC → track_no ASC`. See Step 3.
3. ~~**`best_new` semantics.**~~ Resolved → album-level (`albums.best_new`), editor-set at publish. Step 5 owns the migration; weekly auto-clear batch is a follow-up RFC.
4. ~~**Recommended-tracks position.**~~ Resolved → stays where it is (between subject card and title). No Step 7.

## Decisions log

| Date | Decision | Step |
|------|----------|------|
| 2026-05-31 | Scope = A+B+C+D+E, one RFC, separate PRs per step. | All |
| 2026-05-31 | Artist drill-in uses DB only (no synchronous Spotify call) per CLAUDE.md rule #9. | 3, 4 |
| 2026-05-31 | Drill-in for Spotify-cold artists: add `GET /api/music/artists/by-spotify/{spotify_id}` returning ready / pending / 404. Frontend polls on pending. | 3, 4 |
| 2026-05-31 | `top-tracks` ordering: `views DESC → albums.popularity DESC NULLS LAST → albums.release_date DESC NULLS LAST → track_no ASC`. | 3 |
| 2026-05-31 | `best_new` is an **album-level** boolean (`albums.best_new BOOLEAN NOT NULL DEFAULT FALSE`) with a partial index. Editor sets it manually at publish time via `subject_best_new` field on the post payload (single auth gate, atomic write). | 5, 6 |
| 2026-05-31 | Weekly auto-clear batch (Friday cron, only clears when out-of-window or rating < 4) deferred to a follow-up RFC. Column ships in this RFC so follow-up needs no second migration. | (follow-up) |
| 2026-05-31 | RecommendedTracksBlock keeps its current position (between subject card and title) — no Step 7. | — |
