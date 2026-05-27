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

| # | Bug | Status | Merge SHAs |
|---|-----|--------|------------|
| BUG-3 | SubjectBlock parses `/albums/{id}` response wrong + spotify_id routed to wrong endpoint (500) | ✅ done | `myblog_front` #20 (`1de9773`) |
| BUG-2 | Search filter broken (DB unified ignores type, frontend drops artists/tracks) | ✅ done | `myblog_music` #22 (`5097803`) + `myblog_front` #21 (`ed75a27`) |
| BUG-4 | MusicBrainz aliases written but never read | ✅ done (with BUG-2) | `myblog_music` #22 (`5097803`) |
| BUG-5 | Tile rendering only fits albums | ✅ done (with BUG-2 frontend) | `myblog_front` #21 (`ed75a27`) |
| BUG-6 | Cognito flow needs user click-through | ✅ verified by user 2026-05-27 (login → publish succeeded) | — |
| BUG-7 | access_token (60min) expired → no refresh → silent 401 loop on savePost/updatePost | ✅ done | `myblog_front` #22 (`802afce`) |
| BUG-8 | onPublish auto-redirects to /blog/{slug} which 404s until Astro rebuilds (3–5 min) | ✅ done (with BUG-7) | `myblog_front` #22 (`802afce`) |
| BUG-9 | Duplicate publish on same title creates `-2` suffix silently — no UX warning | not started — low pri | — |

### Verification quoted in PRs

- BUG-3 prod smoke: created post + published to GitHub with album+artists from real Radiohead album → MDX shows `artistIds: ["94ba19ef-…"]` (non-empty), `albumIds: ["9fd6f454-…"]`, `albumCover` populated.
- BUG-2 backend prod smoke: `/api/music/search/unified?q=radiohead&type=<filt>` returns only the requested section:
    - `type=album` → albums=3, others=0
    - `type=artist` → artists=1, others=0
    - `type=track` → tracks=3, others=0
    - `type=album,artist,track` → 1+3+3
- BUG-2 frontend: pending prod deploy + click-through.
- BUG-4: pending alias-populated artist click-through (requires user with `aliases` column data).

### Closed bugs — see git log + PR descriptions for full context

BUG-3, BUG-2, BUG-4, BUG-5 fully resolved 2026-05-27. Repro/fix detail preserved in the merge commits and PR bodies. See "Recent Done" section at the end of this file.

### BUG-6: Cognito flow — verify user-clickable end-to-end

- Scope: `myblog_front` + Cognito
- Status: Cognito config + `logout_urls` reverted to origin values earlier in the session; OAuth `authorize` endpoint returns 200 → login form. **User-facing flow not yet clicked end-to-end after the fix.** Needs a manual click-through (or wait for Phase 2 dev-bypass).
- Status: needs user verification

---

## Notes on cadence

- Today's goal: Phase 0 done + Phase 1 done. Phase 2 may slip to tomorrow if local DB setup is non-trivial.
- If a Phase 1 bug is obviously trivial (1-line fix) and unblocks Phase 2, fix it inline. Otherwise: catalog, prioritize, defer.
- No new feature work until Phase 2 complete.

---

## Recent Done

- **BUG-7 / BUG-8** (2026-05-27, `myblog_front` PR #22 `802afce`): refresh_token retry on 401 in apiFetch + savePost/updatePost/fetchPostById; remove premature post-publish redirect that 404'd before Astro rebuild.
- **BUG-2 / BUG-4 / BUG-5** (2026-05-27): search filter `type` on `/search/unified` + `aliases` JSONB search + frontend filter passes type + discriminated tile rendering. `myblog_music` PR #22 (`5097803`), `myblog_front` PR #21 (`ed75a27`).
- **BUG-3** (2026-05-27, `myblog_front` PR #20 `1de9773`): unwrap `/api/music/albums/{id}` wrapper response + route spotify_id → `/by-spotify`. Fixes publish payload `album_ids: [undefined]` + empty `artist_ids`.
- **Phase 1** (2026-05-27): diagnostic sweep — 5 bugs inventoried (BUG-2 through BUG-6).
- **Phase 0** (2026-05-27): single-file CLAUDE.md, 4 repo CLAUDE.md removed (PR #22/#19/#21/#17), docs archived, myblog_publish archived (`_archive_myblog_publish/`, GitHub repo archived).
- **BUG-1** (2026-05-27, SHA `85c30cf`): API Gateway PUT/DELETE /api/posts routes added; Cognito logout_urls reverted to origin values (SHA `ba35b0e`).
- **PR-12** (2026-05-27): Post CRUD endpoints + drafts UI.
- **PR-11** (2026-05-27): rating scale 0–5 unification.
- **ARCH-12** (2026-05-27): contract-first OpenAPI workflow.

Older history: `docs/archive/done/`.
