# ARCH-12: Contract-first workflow with strict OpenAPI enforcement

- **Status**: in-progress (Step 3)
- **Owner**: TBD
- **Created**: 2026-05-26
- **Plan row**: `plan.md` → ARCH-12

---

## Goal

A single `docs/contracts/openapi.json` is the authoritative API contract for the frontend. It is auto-generated from `myblog_backend` and `myblog_music` FastAPI apps and committed on every backend/music PR. The frontend regenerates TypeScript types from that spec on every CI run; **any drift between the committed spec and the generated types fails CI**. After this RFC lands, it is structurally impossible to ship a backend API change without the frontend either consuming it or failing to build.

## Non-goals

- Splitting `myblog_backend` and `myblog_music` into separate API products. They share one HTTP host (API Gateway `lambdaAPI`); a single merged spec matches the runtime reality.
- Versioning the API (`v1`/`v2`). Single-tenant admin app — breaking changes are coordinated across same-day PRs, not versioned in parallel.
- Generating Python clients (backend ↔ music don't call each other over HTTP). Only the frontend consumes the spec.
- Validating request/response bodies at runtime against the spec. FastAPI already validates via Pydantic; the spec is a build-time artifact for the frontend's benefit.
- Migrating away from FastAPI's built-in OpenAPI generation. It's good enough; don't introduce a separate spec authoring tool.

## Current state

| | Backend | Music |
|---|---|---|
| Framework | FastAPI | FastAPI |
| Spec generation | `app.openapi()` (built-in) but never persisted | Same |
| Committed artifact | `docs/contracts/openapi-backend.json` (manually exported, possibly stale) | None |
| Frontend type gen | `pnpm generate:types` reads `openapi-backend.json` (backend types only) | Music types hand-written |

Known drift this has caused:
- Rating field: frontend `0-10`, backend `le=5` (BUG-6)
- `PostPayload.rating_scale` field missing in frontend payload (BUG-7)
- Music search result types maintained twice (`AlbumSearchResult` on both sides)
- `subject_type` for reviews (when added) will hit the same problem times three (album/track/artist)

Other relevant context:
- `myblog_front` is Astro 5 + React 19, TypeScript strict mode
- pnpm@10, lockfile-enforced
- Frontend CI already has a `check` job (lint + astro check) gating `deploy` (CICD-1)

## Target state

```
docs/contracts/
└── openapi.json            ← single merged spec; only file the frontend reads

myblog_backend/
├── scripts/export_openapi.py    ← generates the backend portion
└── .github/workflows/contract.yml  ← on PR, regenerate + verify committed spec is current

myblog_music/
├── scripts/export_openapi.py    ← generates the music portion
└── .github/workflows/contract.yml  ← same as backend

myblog-workspace/
└── tools/merge_openapi.py        ← merges backend + music exports into docs/contracts/openapi.json

myblog_front/
├── scripts/generate-types.ts     ← reads merged openapi.json, emits src/types/api.ts
└── .github/workflows/deploy.yml  ← `check` job now includes a "types are in sync" step that fails on diff
```

The merged `openapi.json` is committed in the **workspace** repo (where this RFC lives), not in any service repo. This avoids the "which service repo owns the merged file" question.

## Workflow after this RFC

```
1. Dev opens a PR on myblog_backend changing /posts response shape.
2. Backend CI's contract.yml regenerates the backend portion.
3. If the dev didn't run `scripts/export_openapi.py` locally, CI fails with a clear "spec out of date" message + diff. Dev runs the script, commits, pushes.
4. PR merges. A separate workflow opens a PR against myblog-workspace updating docs/contracts/openapi.json (merged with current music spec).
5. The workspace PR triggers myblog_front CI (via repository_dispatch or scheduled poll — see Open Q 1).
6. Frontend CI regenerates types from new openapi.json. If existing frontend code no longer compiles against new types, CI fails. Frontend dev fixes consumers, pushes.
7. Workspace PR merges only after frontend is green.
```

The key property: **frontend can never merge code that disagrees with the deployed backend's spec**, and **backend can never merge a spec change that the frontend hasn't yet consumed** (because the workspace PR is the join point).

## Steps

### Step 1 — Backend & music: spec export scripts

For each of `myblog_backend` and `myblog_music`:

- Add `scripts/export_openapi.py`:
  ```python
  import json
  from app.main import app
  spec = app.openapi()
  with open("openapi.json", "w") as f:
      json.dump(spec, f, indent=2, sort_keys=True)
  ```
- Add `make export-openapi` or equivalent.
- Run it once, commit the resulting `openapi.json` to the service repo root.
- Document in repo CLAUDE.md: "Run `make export-openapi` after any FastAPI route/model change."

**Verification**: `python scripts/export_openapi.py` produces a stable, sorted JSON. Re-running produces zero diff.

**Rollback**: delete script + `openapi.json`. No downstream consumer yet.

---

### Step 2 — Backend & music: CI freshness check

In each service repo's `.github/workflows/`, add a `contract` job in the existing `check` workflow:

```yaml
- name: Verify openapi.json is up to date
  run: |
    python scripts/export_openapi.py
    git diff --exit-code openapi.json
```

If a PR changes a route/model but doesn't update `openapi.json`, this job fails with a clear "spec out of date" message. The job runs **before** any deploy job.

**Verification**: open a test PR that changes a model without re-exporting; CI fails with the expected message. Run the script, push the update; CI passes.

**Rollback**: remove the contract job. Deploy still works.

---

### Step 3 — Workspace: merge tool

In `myblog-workspace/tools/`:

- Add `merge_openapi.py` that takes the two service `openapi.json` files and produces `docs/contracts/openapi.json`.
- Merge strategy: namespace component schemas by service (e.g. `Backend_Post`, `Music_Album`) to avoid collisions. Paths are already non-overlapping in production (backend owns `/api/posts`, `/api/categories`; music owns `/api/music/*`).
- Add a workspace CI workflow that runs on PRs touching either source service's `openapi.json` (via downstream trigger from Step 4) and updates `docs/contracts/openapi.json`.
- Sort keys deterministically so re-running produces zero diff when inputs unchanged.

**Verification**:
- Hand-place two known `openapi.json` files in a test directory; run the merge tool; output matches a golden file.
- Re-running with same inputs produces zero diff.

**Rollback**: delete the tool + generated file. Frontend can continue reading the old `openapi-backend.json` until Step 5.

---

### Step 4 — Cross-repo trigger plumbing

When `openapi.json` lands on `main` in either `myblog_backend` or `myblog_music`, the workspace repo needs to know.

Pick one mechanism (tentative recommendation: A):

- **A. Service-side workflow opens a workspace PR.** On push to main, the service repo's workflow uses a GitHub App token to (1) fetch latest workspace, (2) run merge tool, (3) open a PR against workspace with the updated `docs/contracts/openapi.json`. Self-contained; no scheduled job.
- **B. Workspace cron polls.** Workspace CI runs on a schedule (every 15 min?), pulls both service specs, runs merge, opens a PR if diff. Simpler auth but lag and noise.

Both require a GitHub App or PAT with PR-write on the workspace. Decision needed before this step starts (Open Q 1).

**Verification**: open a real PR on backend changing a model. After merge to main, a PR appears on the workspace with the merged spec change.

**Rollback**: disable the trigger workflow. Merged spec stays stale; frontend still works against the older spec until human-merged.

---

### Step 5 — Frontend: regenerate from merged spec, enforce in CI

- `myblog_front/scripts/generate-types.ts`: switch input from `docs/contracts/openapi-backend.json` to `docs/contracts/openapi.json` (merged).
- Update generated types file (`src/types/api.ts` or wherever).
- Update existing consumers (`PostPayload`, music search types) to use new namespaced types from merged spec. This is the manual migration that surfaces all the drift this RFC was created to fix.
- Address rating scale mismatch and any other accumulated drift here, as a side effect of types now being strict.
- Add a `types-in-sync` step to the `check` job:
  ```yaml
  - name: Regenerate types and fail on drift
    run: |
      pnpm generate:types
      git diff --exit-code src/types/api.ts
  ```

**Verification**:
- `pnpm build` succeeds end-to-end.
- Open a test PR that changes a backend type without updating frontend; after the workspace PR lands and a frontend PR is opened (or rebased onto main), CI fails with the expected drift.
- Rating scale mismatch is now a build error, not a runtime silent rejection.

**Rollback**: revert generator input back to `openapi-backend.json`. Frontend builds again, but contract drift returns.

---

### Step 6 — Cleanup

- Delete `docs/contracts/openapi-backend.json` (subsumed by merged `openapi.json`).
- Each service repo's CLAUDE.md gains a "Contract" section pointing at the export script.
- Workspace `CLAUDE.md` "How to work here" gains: "Any backend/music API change must export openapi.json in the same PR; frontend consumes via the merged spec."
- ADR `0007-contract-first-openapi.md`: records the merged-spec decision, the rejected alternative (per-service specs), the trigger mechanism chosen in Step 4, and the fail-mode CI decision.
- This RFC marked `done` and moved to `docs/done/rfcs/`.

**Verification**: `grep -r "openapi-backend.json" .` returns nothing outside `docs/done/`.

---

## Migration order summary

```
Step 1 (export scripts) ──► Step 2 (CI freshness gate) ──► Step 3 (merge tool) ──► Step 4 (cross-repo trigger) ──► Step 5 (frontend strict) ──► Step 6 (cleanup + ADR)
                                                              │
                                                              └─► Steps 1-3 in backend/music can proceed independently before workspace work begins
```

## Rollback (overall)

- Pre-Step 5: each step is independently revertable. The old `openapi-backend.json` continues to serve the frontend.
- Post-Step 5: full revert would mean re-pinning the frontend to a pre-RFC commit and restoring `openapi-backend.json`. Realistic answer: if Step 5 surfaces problems, fix forward (the drift it exposes is the bug, not the enforcement).

## Why a merged single spec (decided)

Considered: per-service specs (`openapi-backend.json` + `openapi-music.json`), let the frontend consume both.

Rejected because:
- Runtime is one HTTP host (`lambdaAPI` on `ld8pjw3mx4`). Two specs mis-model that.
- Frontend type imports would have to discriminate by service. The frontend doesn't care which Lambda handles `/api/music/search/unified` — it just calls a URL.
- Component schema collisions are easier to handle once (Step 3 merge tool) than per-import (every consumer).
- Subject type extension (album/track/artist) crosses the backend-music boundary: reviews live in backend, but reference music entities. A single spec makes that natural.

## Why fail mode (decided)

Considered: warn mode (CI logs drift but allows merge).

Rejected because:
- The entire point of this RFC is to make drift structurally impossible. Warn mode reintroduces the social-trust dependency we're trying to remove.
- The fail isn't expensive — Step 5 includes the workflow that fixes it (one `pnpm generate:types` run, then commit).
- 1-person ops: the CI noise of warn mode is worse than the occasional hard fail.

## Open questions

1. **Cross-repo trigger mechanism (Step 4)**: A (service opens workspace PR via GitHub App) vs B (workspace cron poll). Decide before Step 4. Tentative: A — more deterministic, less lag.
2. **Namespace prefix in merged spec (Step 3)**: `Backend_Post` / `Music_Album`, or `BlogPost` / `MusicAlbum`, or no prefix and rely on path-level uniqueness? Affects every type import in frontend. Recommend deciding before Step 3 implementation.
3. **GitHub App vs PAT for Step 4**: app is cleaner but needs setup; PAT is faster to ship. Decide based on whether `SHARED_DB_PAT` (ARCH-6 Step 2.5) is already shipped — if yes, reuse the pattern.

## Decisions log

| Date | Decision | Step |
|------|----------|------|
| 2026-05-26 | Single merged OpenAPI spec, not per-service. Rationale in RFC body. | Pre-Step 1 |
| 2026-05-26 | Frontend CI fails on type drift, not warns. Rationale in RFC body. | Pre-Step 5 |

## Relationship to other RFCs

- **ARCH-6 (shared DB)**: independent. ARCH-6 fixes schema drift; ARCH-12 fixes API drift. Can proceed in parallel.
- **ARCH-11 (absorb publish)**: independent. `myblog_publish` doesn't expose typed contracts to the frontend (it takes opaque MDX strings).
- **Feature backlog (rating scale, subject type, track/artist pages)**: all depend on this RFC. Don't start them until at least Step 5 lands.
