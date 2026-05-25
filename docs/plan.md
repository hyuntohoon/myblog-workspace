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

> ✅ Done (2026-05-25) — `ext_refs['spotify_url']` → `AlbumOut.external_url`; PR #11 (myblog_music), 3 unit tests

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

> ✅ Done (2026-05-23) — `docs/contracts/sqs-album-sync.md` 작성 완료

---

### P1-E: Secrets Manager 마이그레이션

> ✅ Done (2026-05-24)

- 4개 AWS Secrets Manager 시크릿 생성: `myblog/backend`, `myblog/worker`, `myblog/music`, `myblog/publish`
- Terraform IAM 정책 4개 적용 (`terraform apply`) — `infra/secrets.tf`
- 4개 repo 코드 수정 (`SECRETS_ARN` 패턴, `get_settings()` + `lru_cache`) — PR 머지 + CI 배포 완료
- 모든 Lambda 평문 시크릿 제거 (`DATABASE_URL`, `SPOTIFY_CLIENT_ID/SECRET`, `EDGE_SECRET`, `GITHUB_TOKEN`)

**후속 권고 → ✅ Done (2026-05-25)**:
- `myblog_worker`: `DATABASE_URL` missing 체크 추가 + `infra/db.py` lazy init, `myblog_music`: 이미 완료 상태 확인 — PR #9 (worker), 7 unit tests

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

> ✅ Done (2026-05-23) — canonical DDL at `docs/contracts/schema.sql`; ADR at `docs/decisions/0003-schema-canonical.md`; worker `ext_refs` upsert fixed; `aliases` added to music schema

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
2. **ARCH-2 (Spotify client)**: ✅ Resolved (2026-05-25) — accept duplication; cross-ref comments added to both files. See `docs/decisions/0004-spotify-client-duplication.md`.
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

**5. Frontend has no type contract with the backend** ✅ Fixed (2026-05-25)

`PostPayload` now derived from generated `WritePostRequest` type. `pnpm generate:types` regenerates from `docs/contracts/openapi-backend.json`. myblog_front PR #5.

**6. Gemini alias generation is coupled to the main sync transaction lifecycle** ✅ Fixed (2026-05-25)

Removed from SQS sync path. Now runs on EventBridge `rate(15 min)` schedule. LIMIT reduced 20→10 to fit 120s timeout. myblog_worker PR #10.

---

## CICD-1: Frontend CI/CD fix

- **Scope**: myblog_front
- **Branch**: `fix/CICD-1-frontend-cicd`
- **Status**: done — myblog_front PR #6, merged 2026-05-25

### Problems

1. **pnpm version mismatch** — workflow uses `pnpm/action-setup@v3` with `version: 9` but `package.json` declares `"packageManager": "pnpm@10.6.3"`. pnpm@9 cannot read a pnpm@10 lockfile; CI silently regenerates it, meaning the lockfile is never actually verified.

2. **No quality gate before deploy** — `pnpm build` runs directly with no prior `pnpm lint` or `pnpm exec astro check`. Type errors and lint failures are invisible until they manifest at runtime.

3. **Cache-Control is wrong for all assets** — `aws s3 cp --cache-control "no-cache, no-store"` is applied to everything including `_astro/**` (content-hashed filenames). Hashed assets should be `max-age=31536000, immutable`; only HTML/XML/JSON should be `no-cache`.

4. **No dependency cache** — every run does a full `pnpm install` with no `actions/cache`. On pnpm@10, the store lives at `~/.local/share/pnpm/store`; caching it would save ~30–60s per run.

### Planned fixes

- `pnpm/action-setup` → `version: 10` (match `packageManager` field)
- Split into two jobs: `check` (lint + astro check) → `deploy` (build + S3 sync), `deploy` needs `check` to pass
- S3 sync: use separate `aws s3 cp` calls per path pattern with correct `--cache-control` values:
  - `_astro/**` → `max-age=31536000, immutable`
  - `*.html`, `sitemap*.xml`, `rss.xml` → `no-cache, no-store, must-revalidate`
  - `pagefind/**` → `max-age=3600`
- Add `actions/cache@v4` keyed on `pnpm-lock.yaml` hash for `~/.local/share/pnpm/store`

### Verification

```
CI green on a no-op commit; `astro check` failure blocks deploy; S3 object metadata shows correct Cache-Control per file type
```

---

## IAC-1: SAM → Terraform 전체 마이그레이션

- **Scope**: `infra/` (workspace) + 후속으로 4개 service repo의 SAM 템플릿 제거
- **Branch**: `infra/IAC-1-terraform-migration`
- **Status**: core applied ✅ (2026-05-25) — `Apply complete! 21 imported, 12 added, 9 changed, 0 destroyed`. 검증: timeout 교정 확인, 사이트/음악검색 HTTP 200 무중단. 후속: EventBridge(권한 확장 후), 4 repo SAM 템플릿 제거.
- **Source**: `docs/tracks/iac-migration.md`
- **Decisions (2026-05-25)**:
  - Lambda 설정은 import하며 **올바른 값으로 교정** (timeout, musicApi Cognito)
  - EventBridge는 **IAM 권한 확장 후 포함** (Gemini 스케줄)
  - Terraform state는 **로컬 유지** (`infra/terraform.tfstate`)

### 배경

- SAM은 실제 배포에 사용되지 않음. `blog-backend` CloudFormation 스택은 드리프트(Lambda 삭제됨) 상태로 방치.
- 실제 운영: Lambda는 CI의 `aws lambda update-function-code`로 코드만, 나머지 인프라(API GW, IAM 역할)는 콘솔 수동.
- Terraform(`infra/`)이 이미 21개 리소스 관리 중: S3, CloudFront, Cognito, SQS(redrive 포함), Secrets IAM.

### 마이그레이션 대상 (Terraform으로 흡수)

| 리소스 | 방식 | 비고 |
|--------|------|------|
| Lambda 함수 4개 | import + `ignore_changes`(코드) | 설정 교정: worker timeout 10→120, api/publish 3→15, music 10→15. (musicApi COGNITO는 보류 — 아래 참고) |
| API Gateway `lambdaAPI` | import | api + 3 integration + 6 route + JWT authorizer + $default stage |
| Lambda invoke 권한 | 신규(consolidated) | 기존 per-route 권한은 레거시로 잔존, 수동 정리 |
| SQS 이벤트소스 매핑 | import | `ReportBatchItemFailures` 활성화 (PR-7 코드 대응) |
| CloudWatch 로그그룹 4개 | import | retention None→14일 |
| CloudWatch 알람 | 신규 | Lambda 에러/쓰로틀 + DLQ 알람 |
| EventBridge (Gemini) | 후속 | IAM 권한(events:*/scheduler:*) 확장 후 |

### 범위 제외 (의도적)

- **IAM 실행 역할 4개**: 그대로 이름 참조 유지 (secrets.tf가 이미 그렇게 동작). 역할이 복잡·비일관(예: `LambdaRDSControlRole`에 불필요한 `AmazonRDSFullAccess`)하여 faithful import는 고위험. 정리/import는 별도 후속.
- **CloudFront `handler` 함수**: ARN 참조로 안정 동작 중, 코드 fetch 필요하여 제외.
- **DB**: Neon 유지, AWS RDS 미사용 → IaC 범위 외.

### Order

1. `.tf` 작성 + import 블록 (lambda, apigateway, monitoring)
2. `terraform plan` — import는 no-op, 교정 항목만 변경으로 표시되는지 검증
3. **사용자 승인 후 `terraform apply`** (프로덕션 변경)
4. 운영 검증
5. (후속) IAM 권한 확장 → EventBridge 추가
6. (후속) 4개 repo SAM 템플릿 제거

### Rollback

- `terraform plan` 단계는 읽기 전용 — apply 전까지 무위험.
- apply 후 문제 시 해당 리소스 설정을 이전 값으로 되돌려 재apply (timeout 등은 즉시 가역).
- state는 로컬 + `terraform.tfstate.backup` 자동 백업 존재.

### Verification

```
terraform plan  # import no-op + 교정만 표시 확인
terraform apply
# apply 후:
aws lambda get-function-configuration --function-name blogWorkerLambda --query Timeout  # 120
aws apigatewayv2 get-routes --api-id ld8pjw3mx4  # 6 routes 유지
curl https://www.ratemymusic.blog/api/...  # 골든패스 무중단 확인
```

### 보류 / 후속 보안 항목

- **musicApi COGNITO_USER_POOL_ID — 보류 확정**. 프론트 `searchBar.client.ts`의 `getJSON`이 인증 헤더 없이 `/candidates`를 호출함을 확인. COGNITO를 켜면 sync 버튼이 401로 깨짐. 프론트가 Cognito 토큰을 보내도록 고치는 별도 PR 이후 재활성화.
- **publisher-github 공개 Function URL** 발견 (`FunctionURLAllowPublicAccess`, AuthType NONE) → API GW/JWT 우회 가능. 본 마이그레이션 범위 외이나 보안 검토 권고.

### 최종 plan 결과 (2026-05-25)

```
Plan: 21 to import, 12 to add, 9 to change, 0 to destroy.
```
- import 21: Lambda 4, 이벤트소스 1, API GW 12, 로그그룹 4 (전부 현 상태와 일치하는 no-op import)
- add 12: 알람 9 + Lambda invoke 권한 3 (additive)
- change 9: 로그그룹 retention 0→14 ×4, 이벤트소스 +ReportBatchItemFailures, Lambda timeout ×4
- **destroy/replace 0** — 무중단
