# Plan — Hotfix Cycle (2026-05-27)

This is the **operational tracker** for the current stabilization cycle. The goal: stop shipping broken features by establishing visibility (Phase 1) and a local-first test loop (Phase 2). Format defined in `CLAUDE.md` → "Plan format".

Phases are sequential — finish Phase N before starting Phase N+1. Inside a phase, items can run in parallel.

---

## Phase 0 — Cleanup (in-progress)

Reduce surface area so subsequent work has fewer places to drift.

### CLEANUP-0a: Delete per-repo CLAUDE.md files

- Scope: `myblog_backend`, `myblog_front`, `myblog_music`, `myblog_worker`
- Order: 4 parallel PRs (`chore/remove-claude-md` in each)
- Verification:
  - local: `ls <repo>/CLAUDE.md` → not found
  - prod: n/a (docs change)
- Status: in-progress

### CLEANUP-0b: Consolidate workspace docs into single CLAUDE.md

- Scope: workspace
- Action: merge `docs/architecture.md`, `docs/infrastructure.md`, `docs/agents.md`, `docs/conventions/git.md` content into root `CLAUDE.md`; move everything else under `docs/` (except `plan.md`, `contracts/`, `rfcs/`) into `docs/archive/`.
- Verification:
  - local: `ls docs/` → only `plan.md`, `contracts/`, `rfcs/`, `archive/`
  - prod: n/a
- Status: in-progress

### CLEANUP-0c: Archive myblog_publish

- Scope: workspace local + GitHub repo
- Action: rename local `myblog_publish/` → `_archive_myblog_publish/`; archive the GitHub repo (`gh repo archive`).
- Verification:
  - local: `ls myblog-workspace/` shows `_archive_myblog_publish/`, no `myblog_publish/`
  - GitHub: repo shows "archived" badge
- Status: not started

### CLEANUP-0d: Clean memory snapshots

- Scope: `.claude/projects/.../memory/`
- Action: delete completed-project snapshot memories (`project-arch12.md`, `project-cicd1-frontend.md`, `project-iac1-terraform.md`, `project-infra-improvement.md`, `project-frontend-redesign.md`). Keep only rules/preferences and active feature roadmap.
- Verification: `MEMORY.md` index updated; only active entries remain.
- Status: not started

---

## Phase 1 — Diagnostic sweep (✅ done 2026-05-27)

Findings cataloged as BUG-N entries below. **Not fixed yet** — Phase 3 will tackle them in priority order.

| Diag item | Result | BUGs raised |
|-----------|--------|-------------|
| DIAG-1a Search filter | Broken | BUG-2 |
| DIAG-1b Publish payload | Broken (root cause: BUG-3) | BUG-3 |
| DIAG-1c MusicBrainz aliases | Worker writes, music never reads | BUG-4 |
| DIAG-1d Tile rendering | Only album-shaped tiles | BUG-5 |
| DIAG-1e Draft CRUD | Works (BUG-1 fixed it); edit mode verified via code, **not user-clicked yet** | — |
| DIAG-1f Cognito flow | Config + OAuth authorize endpoint verified; **user flow not clicked yet** | — |

DIAG-1e/1f are marked "code/API verified, not user-clicked". Sign off after local loop (Phase 2) lets us re-click in a controlled env.

---

## Phase 2 — Local test loop (after Phase 1)

Build a local environment so bugs are caught before merge, not after deploy. Today's biggest design constraint: must be runnable without poking prod.

### LOCAL-2a: Local backend with dev-auth bypass

- Scope: `myblog_backend`, `myblog_music`
- Action:
  - `ENV=local` → `require_cognito_token` accepts a fixed dev token (e.g. `Authorization: Bearer dev-local`) and returns a stub claim.
  - `ENV=local` → `edge_guard` already bypassed (current behavior, keep).
  - Backend can target either prod Neon DB (read-only) or a local Postgres snapshot. Decide during DIAG sweep.
- Verification:
  - local: `ENV=local uvicorn app.main:app` boots; `curl -H "Authorization: Bearer dev-local" localhost:8000/api/db/ping` → 200.
- Status: not started

### LOCAL-2b: Frontend pointed at local backend

- Scope: `myblog_front`
- Action: `.env.local` with `PUBLIC_BACKEND_API_URL=http://localhost:8000`, `PUBLIC_API_URL=http://localhost:8001`. Dev-mode injects `Authorization: Bearer dev-local` so Cognito flow is bypassed locally.
- Verification:
  - local: `pnpm dev` shows `/drafts` populated from local backend.
- Status: not started

### LOCAL-2c: scripts/smoke.sh

- Scope: workspace
- Action: shell script that takes `local` or `prod` argument; hits the critical paths (search each filter, publish round-trip, draft CRUD) and asserts response shapes. Designed to be runnable in <60s.
- Verification: `./scripts/smoke.sh local` passes against a running local stack.
- Status: not started

**After Phase 2, no PR ships without `local && prod smoke` results quoted.**

---

## Phase 3 — Fix in priority order (from Phase 1 inventory)

Each fix:
1. Add a reproduction case to `scripts/smoke.sh` (so it fails first).
2. Implement fix.
3. Local smoke passes.
4. Deploy → prod smoke passes.
5. Merge.

### Priority

| # | Bug | Severity | Notes |
|---|-----|----------|-------|
| BUG-3 | SubjectBlock parses `/albums/{id}` response wrong | **P0** — blocks publish | One-line fix, highest leverage |
| BUG-2 | Search filter broken (DB unified ignores type, frontend drops artists/tracks) | **P0** — core feature visibly broken | Music API + frontend, ~half-day |
| BUG-5 | Tile rendering only fits albums | **P1** — needed once BUG-2 fixed | Frontend only |
| BUG-4 | MusicBrainz aliases written but never read | **P1** — feature absent, not visibly broken | Music API search query change |
| BUG-6 | Cognito error pages still possible if user has stale Cognito session | **P2** — workaround: clear cookies | Verify, may already be self-healing |

### BUG-3: SubjectBlock crashes on album select; publish sends `album_ids: [undefined]`

- Scope: `myblog_front` (`src/components/writer/SubjectBlock.tsx`)
- Symptom (deduced from code + prod API responses, not user-clicked):
  - User searches album → picks one → SubjectBlock calls `GET /api/music/albums/{id}`.
  - Backend returns `AlbumDetail = {album: {…}, artists: […], tracks: […], meta: {…}}` (Pydantic wrapper, verified against prod: `{"album": {...}, "artists": [...], "tracks": [...], "meta": {...}}`).
  - Frontend casts as `AlbumDetail = {id, title, cover_url, release_date, artists}` (flat). After cast: `subject.id`, `subject.title`, `subject.cover_url` are all `undefined`; only `subject.artists` is correct.
  - Display: `subject.title[0]` (cover fallback) throws if cover_url is also undefined. `<img src={undefined}>` shows broken image.
  - Publish payload: `album_ids: [a.id]` → `[undefined]` → JSON serialized as `[null]` → backend 422.
  - User-reported "artist_ids 누락": likely the publish actually fails on `album_ids` validation; `artist_ids` derivation itself is correct (subject.artists has proper IDs).
- Fix direction:
  - Option A: change frontend to unwrap (`detail.album.id`, `detail.album.title`, etc.) and merge with `detail.artists`.
  - Option B: change backend `/api/music/albums/{id}` to return a flat shape matching what frontend expects.
  - Decide during Phase 3 — Option B may also touch `myblog_front` types because `tracks` is part of the response and may already be consumed.
- Status: not started

### BUG-2: Search filter does not work for artist/track in DB search

- Scope: `myblog_music` (search router + service), `myblog_front` (`SubjectBlock.runDBSearch`)
- Symptom (verified against prod):
  - `GET /api/music/search/unified?q=letty` returns `{artists: [Letty Morgan], albums: [], tracks: []}` — endpoint correctly includes all three sections.
  - `runDBSearch` does `data.albums.map(...)` and discards `data.artists` and `data.tracks` entirely.
  - The endpoint does **not** accept a `type` parameter — the filter UI selection has no effect on DB search (only on Spotify sync via `/candidates`).
- Fix direction:
  - Add `type` parameter to `/api/music/search/unified` (default `album,artist,track`, comma-separated, validate against `ALLOWED_TYPES`).
  - In `SearchService.unified_search`, skip repos for unselected types.
  - In frontend `runDBSearch`, pass `filterToType(filter)` as `type`; for filter=`all`, render all three with type-aware tiles; for filter=specific, only render that section.
- Status: not started

### BUG-5: Result tile rendering only fits albums

- Scope: `myblog_front` (`SubjectBlock.tsx`)
- Symptom: tile expects `title`, `artist_name`, `cover_url`, `release_date`, `source`. Tracks and artists have different shapes (no `release_date` for artists; tracks have album info).
- Dependency: BUG-2 must be fixed first so non-album results actually arrive.
- Fix direction: introduce a `kind: 'album' | 'artist' | 'track'` discriminator on each result; render three tile variants. Picking an artist or track may need a different `onSubjectSelect` path (currently `subject` is `AlbumDetail`-typed only).
- Status: blocked by BUG-2

### BUG-4: MusicBrainz aliases populated but never queried

- Scope: `myblog_music` (`app/repositories/artist_repo.py`, `search_service.py`)
- Symptom (verified by grep):
  - Worker `generate_and_save_aliases` writes `artists.aliases` via MusicBrainz lookup.
  - Music service search uses `Artist.name.ilike('%q%')` only — `aliases` column is never read.
- Fix direction: extend `search_by_name` to also match where `aliases` JSON/array contains a case-insensitive substring of `q`. Decide on shape (Postgres JSONB ops vs ARRAY ops depending on the column type — verify in `myblog_shared_db` model).
- Status: not started

### BUG-6: Cognito flow — verify user-clickable end-to-end

- Scope: `myblog_front` + Cognito
- Status: Cognito config + logout_urls fixed earlier; OAuth `authorize` endpoint returns 200 → login form. **User flow not yet clicked end-to-end after the fix.** Needs a manual click-through (or Phase 2 dev-bypass).
- Status: needs user verification

---

## Notes on cadence

- Today's goal: Phase 0 done + Phase 1 done. Phase 2 may slip to tomorrow if local DB setup is non-trivial.
- If a Phase 1 bug is obviously trivial (1-line fix) and unblocks Phase 2, fix it inline. Otherwise: catalog, prioritize, defer.
- No new feature work until Phase 2 complete.

---

## Recent Done

- **Phase 0** (2026-05-27): single-file CLAUDE.md, 4 repo CLAUDE.md removed (PR #22/#19/#21/#17), docs archived, myblog_publish marked archived (`_archive_myblog_publish/`, GitHub repo archived).
- **Phase 1** (2026-05-27): diagnostic sweep — 5 bugs inventoried (BUG-2 through BUG-6).
- **BUG-1** (2026-05-27, SHA `85c30cf`): API Gateway PUT/DELETE /api/posts routes added; Cognito logout_urls reverted to origin values (SHA `ba35b0e`).
- **PR-12** (2026-05-27): Post CRUD endpoints + drafts UI.
- **PR-11** (2026-05-27): rating scale 0–5 unification.
- **ARCH-12** (2026-05-27): contract-first OpenAPI workflow.

Older history: `docs/archive/done/`.
