# Plan — Hotfix Cycle (2026-05-27)

This is the **operational tracker** for the current stabilization cycle. The goal: stop shipping broken features by establishing visibility (Phase 1) and a local-first test loop (Phase 2). Each row carries `Scope / Order (if multi-repo) / Verification (local + prod smoke) / Rollback / Status`; RFC-backed entries collapse to a one-line pointer at `docs/rfcs/<id>-<slug>.md`. When a row reaches `Status: done`, cut it and append to `docs/archive/done/YYYY-MM.md`.

Phases are sequential — finish Phase N before starting Phase N+1. Inside a phase, items can run in parallel.

---

## Phase 0 — Cleanup (✅ done 2026-05-27)

Surface-area reduction so subsequent work had fewer places to drift. All four cleanup items finished — see "Recent Done" for merge refs.

- **CLEANUP-0a** — per-repo CLAUDE.md files deleted across 4 repos.
- **CLEANUP-0b** — workspace docs consolidated into single root `CLAUDE.md`; legacy files moved under `docs/archive/`.
- **CLEANUP-0c** — local `myblog_publish/` renamed to `_archive_myblog_publish/`; GitHub repo `hyuntohoon/myblog_publish` archived.
- **CLEANUP-0d** — completed-project snapshot memories removed; only rules/preferences + active feature roadmap remain in `MEMORY.md`.

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

## Phase 2 — Local test loop (✅ done 2026-05-27)

- **LOCAL-2a** (no code change): backend/music already bypass Cognito JWT validation on `ENV=local` (`app/core/auth.py:33`).
- **LOCAL-2b**: frontend now treats localhost/127.0.0.1/*.local as logged-in with a dummy `'local-dev'` token (`myblog_front` PR #24 `2038718`).
- **LOCAL-2c**: `scripts/smoke.sh` (+ `smoke.py`) runs 20 end-to-end checks in ~7s. Hits health, search filter (BUG-2 guard), album-detail wrapper (BUG-3 guard), post CRUD (BUG-1/BUG-7 guard). Works against `prod` and `local`.

Local-dev quickstart and smoke usage are documented in `CLAUDE.md` → "Local development".

**Definition of Done now strictly requires a prod smoke result quoted in every PR.**

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
- BUG-6 click-through: user logged in + published end-to-end 2026-05-27. Implicitly exercises BUG-2 frontend on prod. BUG-4 alias path only triggers for artists with populated `aliases` — defer until such data exists.

### Closed bugs — see git log + PR descriptions for full context

BUG-3, BUG-2, BUG-4, BUG-5, BUG-6, BUG-7, BUG-8 fully resolved 2026-05-27. Repro/fix detail preserved in the merge commits and PR bodies. See "Recent Done" section at the end of this file.

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
