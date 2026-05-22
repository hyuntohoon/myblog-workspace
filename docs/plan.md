# Cross-Repo Work Plan

---

## 1. Context

Initial code review of `myblog_music` (2026-05-20) identified runtime bugs, security gaps, and debug code that must be resolved before production. This section defines the work order by priority.

- Source: `docs/reviews/2026-05-20-myblog-music-initial.md`
- Created: 2026-05-20
- Last updated: 2026-05-20

---

## 2. Issue Classification

### Quick isolation (low risk, completable same day)

| ID | Item | Location |
|----|------|----------|
| DEBT-2 | Move inline `import` statements out of class body in `album_repo.py` | `app/repositories/album_repo.py` L128–129 |
| DEBT-3 | Fix filename typo: `cadidate_search_service.py` → `candidate_search_service.py` | `app/services/`, `app/api/routers/search.py` |
| DESIGN-2 | Remove dead code `singleflight.py` — absorbed into PR-1, confirmed for deletion | `app/core/singleflight.py` |

### Correctness bugs (this week, clear fixes)

| ID | Item | Location | Symptom |
|----|------|----------|---------|
| BUG-1 | `schema.sql` artists table has duplicate `);` — DDL fails to execute | `db/schema.sql` L90–91 | DB init error on fresh environment |
| BUG-2 | `album_service.py` `get_primary_artist_map` — delete service method, reuse `AlbumRepository` method | `app/services/album_service.py` L29–30 | `NameError` on call |
| BUG-3 | `Track` model missing `spotify_id unique=True` (out of sync with schema) | `app/domain/models.py` L197 | Duplicate track inserts possible |
| DEBT-1 | Remove production `print()` calls (`album_repo`, `sqs_client`, `candidate_search_service`) | Multiple files | CloudWatch cost + secret exposure in logs |
| DEBT-4 | Remove timing/debug code from `get_existing_spotify_ids`; remove forced `db.connection()` acquisition | `app/repositories/album_repo.py` L131–170 | Unnecessary overhead on every request |

### Design decisions needed (agree with Jack before proceeding)

| ID | Item | Decision needed |
|----|------|-----------------|
| DESIGN-1 | Auth method for `/candidates` endpoint | Depends on whether a user system will be introduced. See `docs/tracks/auth-design.md` |
| INFRA-1 | CI test gate scope | Confirm unit test gate. Integration tests run locally or on schedule. IaC migration goal tracked in `docs/tracks/iac-migration.md` |

### Tracked separately

| ID | Item | Note |
|----|------|------|
| BUG-3 migration | Add UNIQUE constraint on `tracks.spotify_id` in existing DB | `CREATE UNIQUE INDEX CONCURRENTLY` (zero-downtime). Check for duplicate data first. |

---

## 3. PR Bundles

### PR-1: Quick isolation — typo, dead code, import cleanup

- **Title**: `fix: rename typo, remove dead code, move imports (myblog_music)`
- **Covers**: DEBT-2, DEBT-3, DESIGN-2
  - Move `import` statements to module top in `album_repo.py`
  - Rename `cadidate_search_service.py` → `candidate_search_service.py`
  - Update import path in `app/api/routers/search.py`
  - Delete `app/core/singleflight.py` (no references, confirmed unused)
- **Affected repo**: `myblog_music`
- **Acceptance**: Lambda handler (`handler = Mangum(app)`) loads without import errors. Router works after rename.
- **Estimated time**: < 1h
- **Prerequisite**: None

> ✅ Done (2026-05-21, SHA: <merge commit>)

---

### PR-2: Runtime bug fixes — schema + NameError + model mismatch

- **Title**: `fix: schema.sql bracket error, album_service NameError, Track model unique missing`
- **Covers**: BUG-1, BUG-2, BUG-3 (model declaration only; DB migration is separate)
  - Remove duplicate `)` in `db/schema.sql` artists table
  - Delete `get_primary_artist_map` from `album_service.py`; replace callers with `AlbumRepository` method
  - Add `unique=True` to `Track.spotify_id` in `app/domain/models.py`
- **Affected repo**: `myblog_music`
- **Acceptance**:
  - `db/schema.sql` runs against a blank PostgreSQL instance without error
  - `GET /api/music/albums/{id}` returns 200 without 500
  - Unit test confirms `IntegrityError` on duplicate `spotify_id` insert
  - `grep` for `album_service.get_primary_artist_map` callers returns 0 results before starting
- **Estimated time**: 2–3h
- **Prerequisite**: PR-1 merged

> Also addressed (2026-05-21): removed duplicate `get_by_spotify_id` definition in `album_repo.py`; kept the eager-load version (L25), deleted the plain one (old L231).
> Also addressed (2026-05-21): removed temporary comment in `album_service.py` `get_album_detail_by_spotify`.

> ✅ Done (2026-05-21, SHA: fae9397)

---

### DEBT-5: `AlbumOut.external_url` missing (tracked separately)

- **Found**: During PR-2 review. `AlbumOut` constructor in DB-read paths (`/albums/:id`, `/albums/by-spotify/:id`) never receives `external_url`, so the field is always `null` in responses.
- **Location**: `app/services/album_service.py` `get_album_detail` — `AlbumOut(...)` constructor
- **Impact**: Spotify URL lost in DB-first search responses. `/candidates` path is unaffected (separate flow).
- **Decision needed**: Intentional omission (no `spotify_url` column in DB?), or should it be added? If Album model has no `spotify_url`, must extract from `ext_refs` or add the column.
- **Priority**: After PR-3, pending design confirmation.

---

### PR-3: Debug code removal — print and timing cleanup

- **Title**: `chore: remove production print/timing code, replace with structured logging (myblog_music)`
- **Covers**: DEBT-1, DEBT-4
  - `album_repo.py` `get_existing_spotify_ids` — remove all `print()`, remove `time.perf_counter`, remove forced `db.connection()` acquisition
  - `sqs_client.py` — remove SQS URL and message body prints; replace error cases with `logging.error`
  - `candidate_search_service.py` — remove `album_ids` list print
- **Affected repo**: `myblog_music`
- **Acceptance**: Lambda execution logs contain no plain-text `album_ids` list or SQS URL. Error cases still produce log output.
- **Estimated time**: 2h
- **Prerequisite**: None (can run in parallel with PR-1; touches different files)

> ✅ Done (2026-05-21, SHA: f4a5308)

---

### PR-4: Security — add `/candidates` auth (after auth-design.md decision)

- **Prerequisite**: Open questions in `docs/tracks/auth-design.md` resolved. PR-2 and PR-3 merged.

> ✅ Done (2026-05-23) — Cognito JWT validation via JWKS; bypassed when `COGNITO_USER_POOL_ID` unset

---

### PR-5: CI unit test gate ⏸️

> ⏸️ On hold — re-evaluate after architect review. See `docs/decisions/0002-paused-pr5-pr6.md`

- **Title**: `ci: add unit test gate before deploy (myblog_music)`
- **Covers**: INFRA-1 (unit test gate only)
  - Add unit test job to `.github/workflows/deploy.yml`
  - Integration tests (`tests/test_candidates_localstack.py`) excluded from CI gate; run locally or on schedule
- **Affected repo**: `myblog_music`
- **Acceptance**: Lambda deploy is blocked when unit tests fail. Localstack-dependent tests are not part of the gate.
- **Estimated time**: 1–2h
- **Prerequisite**: PR-1–3 merged

> ✅ Done (2026-05-23) — CI test job gates deploy; 5 unit tests for auth bypass; integration test marked and excluded

---

### PR-6: DB migration — add UNIQUE constraint on `tracks.spotify_id` ⏸️

> ⏸️ On hold — re-evaluate after architect review. See `docs/decisions/0002-paused-pr5-pr6.md`

- **Title**: `db: add UNIQUE constraint on tracks.spotify_id`
- **Covers**: BUG-3 migration part
  - Script to detect and clean duplicate `spotify_id` values in existing data
  - `CREATE UNIQUE INDEX CONCURRENTLY ON tracks (spotify_id);` (zero-downtime)
- **Affected repo**: `myblog_music` (shared RDS — verify `myblog_worker` upserts are unaffected)
- **Acceptance**: `\d tracks` shows UNIQUE constraint after migration. Worker upsert runs without `IntegrityError`. No traffic interruption during migration.
- **Estimated time**: 1–2h (plus data cleanup time)
- **Prerequisite**: PR-2 merged. Duplicate data check completed. Jack approval.

> ✅ Done (2026-05-23) — migration script at `db/migrations/001_tracks_spotify_id_unique.sql`; run manually against RDS following the 5-step instructions in the file

---

## 4. Dependency Graph

```
PR-1 (typo · import · singleflight)    PR-3 (print removal)
  └─→ PR-2 (runtime bugs)              ↑ parallel OK (different files)
        └─→ PR-5 (CI unit test gate)   ← after PR-1–3
        └─→ PR-4 (auth)                ← after auth-design.md decision

PR-2 merged + Jack approval
  └─→ PR-6 (DB migration) ← independent track, separate schedule
```

---

## 5. Open Questions

1. **DESIGN-1**: `/candidates` auth method → see `docs/tracks/auth-design.md`
2. **INFRA-1**: IaC migration goal after CI gate → see `docs/tracks/iac-migration.md`

---

---

# Full-System Refactoring Plan

- **Source**: Full codebase analysis across all five repos (2026-05-22)
- **Scope**: Cross-repo bugs, security gaps, code quality, and architecture improvements
- **Work rules**: Each PR targets a single repo unless noted. Open a branch (`fix/<pr-id>-<desc>`) before any code change.

---

## Issue Registry

### P0 — Security (ship-blocker)

| ID | Service | Issue | Location |
|----|---------|-------|----------|
| SEC-1 | `myblog_publish` | `allow_origins=["*"]` — CORS fully open | `app/main.py` L13 |
| SEC-2 | `myblog_publish` | No auth on `POST /api/publish` — anyone can commit to GitHub | `app/api/routes/publish.py` |
| SEC-3 | `myblog_worker` | All SQS exceptions caught and return `True` — DLQ never fires, failed messages silently deleted | `worker/handler.py` L79–81 |

### P1 — Runtime Bugs

| ID | Service | Issue | Location | Symptom |
|----|---------|-------|----------|---------|
| BUG-4 | `myblog_worker` | `_process_single()` calls `svc.sync_album_by_spotify()` — method does not exist on `AlbumSyncService` | `worker/handler.py` L22 | `AttributeError` on every single-album SQS message |
| BUG-5 | `myblog_front` | `addCategory` calls `${API}/categories` — missing `/api` prefix | `src/lib/api.ts` L33 | 404 on category create |
| BUG-6 | `myblog_front` | `PostPayload.rating` comment says max `10`; backend validates `le=5` | `src/scripts/write/api.ts` L19 | Silent rejection of ratings 5–10 |
| BUG-7 | `myblog_front` | `publishToGit()` payload omits `rating_scale` field | `src/scripts/write/api.ts` L82–94 | Publish always uses backend default (`5`), ignoring user selection |
| DEBT-6 | `myblog_backend` | `print()` in `get_settings()` — leaks masked DB URL on every cold start | `app/core/config.py` L43–44 | CloudWatch noise |
| DEBT-7 | `myblog_worker` | `print()` throughout `sync_service.py` — leaks Spotify IDs, artist data | `worker/service/sync_service.py` | CloudWatch cost + data exposure |

### P2 — Code Quality

| ID | Service | Issue | Location |
|----|---------|-------|----------|
| REFACTOR-1 | `myblog_backend` | `app/config.py` and `app/core/config.py` are near-identical; both instantiate `settings` at module level | Both files |
| REFACTOR-2 | `myblog_backend` | `main.py` mixes secrets loading, CORS, middleware, and routing; secrets loaded at module import time (cold start cost) | `app/main.py` |
| REFACTOR-3 | `myblog_publish` | `load_dotenv(".env")` called unconditionally — runs in Lambda where `.env` does not exist | `app/main.py` L6 |
| REFACTOR-4 | `myblog_worker` | Gemini model `gemini-2.5-flash` hardcoded in business logic | `worker/service/sync_service.py` L47 |
| REFACTOR-5 | `myblog_front` | `apiFetch(path, options = {})` has no TypeScript types | `src/lib/api.ts` L67 |

### P3 — Cross-Service Architecture

| ID | Area | Issue |
|----|------|-------|
| ARCH-1 | Schema | Three schema sources diverging: `myblog_backend/app/db/schema_v0.sql`, `myblog_music/db/schema.sql`, `myblog_worker/worker/infra/tables.py`. `aliases` JSONB column exists only in worker's table definition — backend schema is unaware. |
| ARCH-2 | Spotify client | Two separate `spotify_client.py` implementations in `myblog_music` and `myblog_worker`. Any Spotify API change requires two edits. |
| ARCH-3 | SQS contract | Message format `{"album_ids": [...], "market": "..."}` is implicit between `myblog_music` (enqueue) and `myblog_worker` (consume). No contract document in `docs/contracts/`. |
| ARCH-4 | Docs | No `CLAUDE.md` in any individual repo. |
| ARCH-5 | Worker `ext_refs` | Album upsert `ON CONFLICT DO UPDATE` does not update `ext_refs` — Spotify URL changes are never persisted after first sync. |

---

## PR Bundles

### PR-7: Worker — SQS error handling + AttributeError + logging ✅ Done (2026-05-23, SHA: a156cfb)

- **Title**: `fix: SQS error handling, sync_album_by_spotify AttributeError, print→logging (myblog_worker)`
- **Covers**: SEC-3, BUG-4, DEBT-7
- **Changes**:
  - `worker/handler.py` — re-raise exceptions (or raise `Exception` after logging) so SQS retries and routes to DLQ on repeated failure; remove `results.append(True)` on exception
  - `worker/handler.py` L22 — replace `svc.sync_album_by_spotify(album_id, market)` with `svc.sync_albums_batch([album_id], market)`
  - `worker/service/sync_service.py` — replace all `print()` with `logging.getLogger(__name__)`; replace `generate_artist_aliases` print calls too
- **Acceptance**: A deliberately bad album ID causes SQS to retry (message not deleted on first failure). Single-album messages process without `AttributeError`. No plain `print()` remains in worker.
- **Estimated time**: 2h
- **Prerequisite**: None

---

### PR-8: Publish — auth + CORS hardening ✅ Done (2026-05-23, SHA: 7866864)

- **Title**: `fix: add edge-secret auth, restrict CORS, remove unconditional dotenv (myblog_publish)`
- **Covers**: SEC-1, SEC-2, REFACTOR-3
- **Changes**:
  - `app/main.py` — replace `allow_origins=["*"]` with `FRONT_ORIGIN` env var (same pattern as `myblog_backend`)
  - `app/main.py` — add `edge_guard` middleware that checks `x-origin-verify` header (same logic as `myblog_backend`)
  - `app/main.py` — guard `load_dotenv` with `if os.getenv("APP_ENV", "prod") == "dev":`
- **Acceptance**: Direct `POST /api/publish` without `x-origin-verify` returns `403`. CloudFront (with the header) succeeds.
- **Estimated time**: 1h
- **Prerequisite**: Confirm `EDGE_SECRET` env var is deployed to publish Lambda

---

### PR-9: Backend — config dedup + print removal

- **Title**: `refactor: merge duplicate config files, remove print statements (myblog_backend)`
- **Covers**: REFACTOR-1, REFACTOR-2, DEBT-6
- **Changes**:
  - Delete `app/config.py`; consolidate into `app/core/config.py` (single `Settings` class, single `get_settings()`)
  - Remove `print()` from `get_settings()`; replace with `logging.getLogger(__name__).debug()`
  - `app/main.py` — move `_load_secrets_once()` into a lazy function called on first request (not at import time); or better, fold into `get_settings()` via `@lru_cache`
- **Acceptance**: Import of `app.main` does not trigger secrets fetch or print output. `DATABASE_URL` never appears in Lambda init logs.
- **Estimated time**: 2h
- **Prerequisite**: None

> ✅ Done (2026-05-23, SHA: f16ecd7)

---

### PR-10: Frontend — API path + rating schema fixes

- **Title**: `fix: API path prefix, rating scale mismatch, publishToGit missing field (myblog_front)`
- **Covers**: BUG-5, BUG-6, BUG-7, REFACTOR-5
- **Changes**:
  - `src/lib/api.ts` L33 — `${API}/categories` → `${API}/api/categories`
  - `src/scripts/write/api.ts` L19 — update `rating` max comment to `5` (match backend `le=5`)
  - `src/scripts/write/api.ts` payload — add `rating_scale` field to `publishToGit` and `PostPayload`
  - `src/lib/api.ts` L67 — add TypeScript types to `apiFetch`: `(path: string, options: RequestInit = {}): Promise<Response | null>`
- **Acceptance**: Category creation succeeds via the write UI. A post with `rating_scale=10` and `rating=8` round-trips correctly through publish.
- **Estimated time**: 1h
- **Prerequisite**: None

> ✅ Done (2026-05-23, SHA: 4a618f2)

---

### DOC-1: SQS contract document

- **Title**: `docs: add SQS album-sync message contract`
- **Covers**: ARCH-3
- **File**: `docs/contracts/sqs-album-sync.md`
- **Content**: message schema (JSON), field definitions, producer (`myblog_music`), consumer (`myblog_worker`), retry/DLQ policy
- **Prerequisite**: PR-7 merged (finalize the format after error-handling is correct)

---

### DOC-2: Per-repo CLAUDE.md

- **Covers**: ARCH-4
- **Files**: `CLAUDE.md` in each of `myblog_backend`, `myblog_front`, `myblog_music`, `myblog_publish`, `myblog_worker`
- **Content per file**: service responsibility, local dev setup, key invariants (hard rules), test commands
- **Prerequisite**: None — can be done independently

> ✅ Done (2026-05-23) — merged to main in all 5 repos

---

### ARCH-1: Schema single source of truth

- **Covers**: ARCH-1, ARCH-5
- **Decision needed**: Nominate `docs/contracts/schema.sql` as the canonical DDL. Each service schema file becomes a derived copy or is removed.
- **Scope**:
  - Add `aliases JSONB` column definition to backend schema
  - Fix album upsert in worker to include `ext_refs` in the `ON CONFLICT DO UPDATE` clause
  - Document drift policy: schema changes must update `docs/contracts/schema.sql` first
- **Prerequisite**: Team agreement on canonical location

> ✅ Done (2026-05-23) — canonical DDL at `docs/contracts/schema.sql`; ADR at `docs/decisions/ADR-001-schema-canonical.md`; worker `ext_refs` upsert fixed; `aliases` added to music schema

---

## Dependency Graph

```
PR-7 (worker fixes)          PR-8 (publish security)     PR-9 (backend config)
  └─→ DOC-1 (SQS contract)

PR-10 (frontend fixes)       DOC-2 (per-repo CLAUDE.md)
  — all independent —

ARCH-1 (schema consolidation) ← requires team decision on canonical location
```

---

## Open Questions

1. **SEC-2 / PR-8**: Does `myblog_publish` need full Cognito JWT validation (same as backend write endpoints), or is `x-origin-verify` edge-secret sufficient given the Lambda is behind CloudFront?
2. **ARCH-2 (Spotify client)**: Extract to a shared internal package (`myblog_shared`) or accept duplication and keep repos independent?
3. **ARCH-1 (Schema)**: Which file becomes the canonical DDL — `myblog_music/db/schema.sql` (most complete) or a new `docs/contracts/schema.sql`?

---

## Architecture Review (2026-05-22)

### What is working well

**Service separation principle is correct.** Spotify outages cannot affect blog reads or writes. A publish failure cannot affect post saves. SQS-based async sync is the right choice for offloading Spotify data collection from the user-facing request path.

**Worker bulk upsert design is solid.** `INSERT ON CONFLICT DO UPDATE` with batches of 20 is a realistic balance between Spotify API rate limits and RDS load.

**Security boundary intent is right.** GitHub tokens isolated to `myblog_publish`, Cognito validation isolated to `myblog_backend` — the intent is correct. The problem is the boundary is not enforced in code yet (see SEC-1, SEC-2).

---

### Areas that need improvement

**1. `myblog_publish` is the highest-risk service but has no auth**

It holds GitHub tokens and can commit to the repo on behalf of anyone who calls it. The architecture doc explicitly marks it as a security boundary, but there is no enforcement code. This must be fixed before any production traffic.

**2. Worker SQS error handling is fundamentally broken (SEC-3)**

Catching all exceptions and returning `True` tells the Lambda runtime — and SQS — that every record was processed successfully. Failed syncs are silently discarded. The DLQ never receives anything. The fix is to re-raise the exception so the Lambda invocation fails, triggering SQS visibility timeout and retry.

**3. Three services share one RDS with no enforced schema contract (ARCH-1)**

`myblog_backend` (SQLAlchemy ORM), `myblog_music` (SQLAlchemy ORM), and `myblog_worker` (Core + raw SQL) all access the same tables through different abstraction layers. Schema changes require coordinated updates across three repos with no automated guard. The `aliases` column is already drifted — it exists in the worker table definition but not in the backend schema. A single canonical DDL in `docs/contracts/schema.sql` is the minimum needed to control this.

**4. `myblog_backend` config executes at module import time**

```python
SECRETS = _load_secrets_once()   # main.py top-level — runs on every cold start
settings = get_settings()        # core/config.py top-level — second redundant init
```

Lambda reuses the module across invocations, so the Secrets Manager call only happens once per container lifetime — but two separate config systems (`main.py` inline + `core/config.py`) exist simultaneously and it is not obvious which one wins for a given value. This should be one system, lazily initialized.

**5. Frontend has no type contract with the backend**

`write/api.ts` `PostPayload`, backend `WritePostRequest`, and publish `CreatePostReq` are three independent type definitions for what is effectively the same data shape. They are already diverging (`rating` max value, missing `rating_scale`). FastAPI generates an OpenAPI spec automatically — using it to generate TypeScript types (via `openapi-typescript` or similar) would eliminate this class of drift entirely.

**6. Gemini alias generation is coupled to the main sync transaction lifecycle**

`generate_and_save_aliases` runs after the main transaction commits but still holds a DB connection while making a 10-second external HTTP call to Gemini. Under load this occupies a connection slot unnecessarily. This work should be decoupled — either a separate SQS message type, an EventBridge scheduled rule, or a second Lambda trigger — so the main sync path is not affected by Gemini latency or failures.
