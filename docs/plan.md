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

## Phase 1 — Diagnostic sweep (next)

**Do not fix yet.** Catalog every broken user-facing behavior. Each finding becomes a `BUG-N` row appended to this file, with reproduction steps. Prioritize after the sweep, not during.

### DIAG-1a: Search filter behavior (album / artist / track)

- Scope: `myblog_music`, `myblog_front`
- Reproduction target:
  - Visit search UI; switch filter to album / artist / track.
  - Verify each filter returns only that type, with correct distinction in the result tiles.
- Suspected: `/api/music/search/unified` may ignore the type filter; frontend tile rendering may not differentiate.
- Status: not started

### DIAG-1b: Publish payload completeness

- Scope: `myblog_front`, `myblog_backend`
- Reproduction target:
  - Pick an album in WriterApp → fill body → press Publish.
  - Inspect the request payload sent to `POST /api/publish` and the resulting MDX.
  - Verify every field round-trips: `title`, `description`, `body_mdx`, `posted_date`, `category`, `slug`, `post_id`, `album_ids`, **`artist_ids`**, `album_cover_url`, `rating`.
- Known: `artist_ids` is empty in the produced MDX even when an album with artists is selected.
- Status: not started

### DIAG-1c: MusicBrainz alias usage

- Scope: `myblog_worker`, `myblog_music`, `myblog_front`
- Reproduction target:
  - Confirm `artists.aliases` column is populated for at least some artists (worker did run).
  - Trace where the aliases are read in the search flow.
  - Verify alias search actually works end-to-end (e.g. search by Korean alias → returns artist).
- Status: not started

### DIAG-1e: Draft CRUD + edit mode

- Scope: `myblog_front`, `myblog_backend`
- Reproduction target:
  - `/drafts` lists drafts (PR-12 work).
  - Click Edit → `/write?id=…` loads existing draft.
  - Modify → Save Draft → reload `/drafts` → changes persisted.
  - Delete → row disappears.
- Known: BUG-1 (PUT/DELETE 404) already fixed; verify full path still works post-fix.
- Status: not started

### DIAG-1f: Cognito auth flow end-to-end

- Scope: `myblog_front` + Cognito
- Reproduction target:
  - Logged-out user visits `/drafts` → redirect to Cognito hosted UI → login → return to `/drafts` with token.
  - Logout → return to origin → re-login works.
- Known: logout_urls were broken mid-session; verify the user-facing flow recovers cleanly.
- Status: not started

**Output of Phase 1**: BUG-N entries below, prioritized.

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

## Phase 3 — Fix in priority order

Populated from Phase 1's BUG inventory. Each fix:

1. Write reproduction in `scripts/smoke.sh` first (so it fails).
2. Implement fix.
3. Local smoke passes.
4. Deploy → prod smoke passes.
5. Merge.

_(BUG-N rows will be added here after Phase 1)_

---

## Notes on cadence

- Today's goal: Phase 0 done + Phase 1 done. Phase 2 may slip to tomorrow if local DB setup is non-trivial.
- If a Phase 1 bug is obviously trivial (1-line fix) and unblocks Phase 2, fix it inline. Otherwise: catalog, prioritize, defer.
- No new feature work until Phase 2 complete.

---

## Recent Done

- **BUG-1** (2026-05-27, SHA `85c30cf`): API Gateway PUT/DELETE /api/posts routes added; Cognito logout_urls reverted to origin values (SHA `ba35b0e`).
- **PR-12** (2026-05-27): Post CRUD endpoints + drafts UI.
- **PR-11** (2026-05-27): rating scale 0–5 unification.
- **ARCH-12** (2026-05-27): contract-first OpenAPI workflow.

Older history: `docs/archive/done/`.
