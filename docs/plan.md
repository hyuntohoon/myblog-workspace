# Cross-Repo Work Plan

---

## 1. 컨텍스트

myblog_music 초기 코드 리뷰(2026-05-20) 결과, 프로덕션 투입 전 반드시 처리해야 할 런타임 버그·보안 구멍·디버그 코드 잔재가 발견되었다. 이 계획은 해당 항목을 우선순위에 따라 처리 순서를 정의한다.

- 입력 출처: `docs/reviews/2026-05-20-myblog-music-initial.md` (코드 직접 분석)
- 작성일: 2026-05-20
- 최종 수정: 2026-05-20 (결정사항 반영)

---

## 2. 항목 분류

### 빠른 격리 (오늘 안에 처리 가능, 위험 낮음)

| ID | 항목 | 위치 |
|----|------|------|
| DEBT-2 | album_repo.py 클래스 본문 내 import 문 정리 | `app/repositories/album_repo.py` L128-129 |
| DEBT-3 | cadidate_search_service.py 파일명 오타 수정 (`cadidate` → `candidate`) | `app/services/`, `app/api/routers/search.py` |
| DESIGN-2 | singleflight.py 데드 코드 제거 — PR-1에 흡수, 파일 삭제 확정 | `app/core/singleflight.py` |

### 정확성 버그 (이번 주, 명확한 수정)

| ID | 항목 | 위치 | 증상 |
|----|------|------|------|
| BUG-1 | schema.sql artists 테이블 `);\n);` 중복 괄호 — DDL 실행 불가 | `db/schema.sql` L90-91 | 신규 환경 DB 초기화 오류 |
| BUG-2 | album_service.py get_primary_artist_map — 서비스 메서드 삭제, AlbumRepository 메서드 재사용으로 확정 | `app/services/album_service.py` L29-30 | 호출 시 NameError |
| BUG-3 | Track 모델 spotify_id unique=True 누락 (스키마와 불일치) | `app/domain/models.py` L197 | 중복 트랙 삽입 가능 |
| DEBT-1 | 프로덕션 print 제거 (album_repo, sqs_client, candidate_search_service) | 여러 파일 | CloudWatch 비용 + 시크릿 로그 노출 |
| DEBT-4 | get_existing_spotify_ids 타이밍/디버그 코드 제거, db.connection() 강제 획득 제거 | `app/repositories/album_repo.py` L131-170 | 매 요청마다 불필요한 오버헤드 |

### 설계 결정 필요 (계획 추가 작업 전 Jack과 합의)

| ID | 항목 | 결정 필요 내용 |
|----|------|----------------|
| DESIGN-1 | /candidates 엔드포인트 인증 방식 | 회원 시스템 도입 여부에 따라 방식 결정 필요. `docs/tracks/auth-design.md` 참조 |
| INFRA-1 | CI 테스트 게이트 범위 | 단위 테스트 gate 확정. 통합 테스트는 로컬/스케줄 실행으로 분리. IaC 전환 상위 목표는 `docs/tracks/iac-migration.md` 참조 |

### 별도 추적

| ID | 항목 | 비고 |
|----|------|------|
| BUG-3 마이그레이션 | Track.spotify_id UNIQUE 제약을 기존 DB에 추가 | `CREATE UNIQUE INDEX CONCURRENTLY` 무중단 방식으로 확정. 점검 시간 별도 불필요. 기존 데이터 중복 확인 선행 필요. |

---

## 3. PR 묶음 제안

### PR-1: 즉시 격리 — 오타·데드코드·import 정리

- **제목**: `fix: 오타 수정, 데드 코드 제거, import 정리 (myblog_music)`
- **포함 항목**: DEBT-2, DEBT-3, DESIGN-2
  - `app/repositories/album_repo.py` 상단으로 import 이동
  - `app/services/cadidate_search_service.py` → `candidate_search_service.py` 파일명 변경
  - `app/api/routers/search.py` import 경로 업데이트
  - `app/core/singleflight.py` 파일 삭제 (사용처 없음, 삭제 확정)
- **영향 레포**: `myblog_music`
- **수락 기준**: Lambda 핸들러(`handler = Mangum(app)`)가 import 오류 없이 로드됨. 파일명 변경 후 라우터 동작 확인.
- **예상 소요 시간**: 1시간 이내
- **선행 조건**: 없음

> ✅ 완료 (2026-05-21, SHA: <머지 커밋 7자리>)

---

### PR-2: 런타임 버그 수정 — schema + NameError + 모델 불일치

- **제목**: `fix: schema.sql 괄호 오류, album_service NameError, Track 모델 unique 누락`
- **포함 항목**: BUG-1, BUG-2, BUG-3 (모델 선언만, DB 마이그레이션은 별도)
  - `db/schema.sql` artists 테이블 중복 `)` 제거
  - `app/services/album_service.py` get_primary_artist_map 메서드 삭제, AlbumRepository 메서드 재사용으로 교체
  - `app/domain/models.py` Track.spotify_id에 `unique=True` 추가
- **영향 레포**: `myblog_music`
- **수락 기준**:
  - `db/schema.sql`을 빈 PostgreSQL 인스턴스에 실행했을 때 오류 없이 완료됨
  - `GET /api/music/albums/{id}` 호출 시 500 없이 정상 응답
  - Track 모델 Unit 테스트에서 동일 spotify_id 중복 삽입 시 IntegrityError 발생 확인
  - PR 작업 전 `album_service.get_primary_artist_map` 호출자 grep 결과 0건 확인
- **예상 소요 시간**: 2~3시간
- **선행 조건**: PR-1 병합 후 (파일명 변경으로 import 경로 안정화 이후)

메모: PR-2 내부 항목(BUG-1/BUG-2/BUG-3)은 사실상 독립이나 리뷰 오버헤드를 고려해 단일 PR 유지.

> 추가 처리됨 (2026-05-21): `app/repositories/album_repo.py` `get_by_spotify_id` 중복 정의 제거. eager load(`selectinload`) 포함 버전(L25) 유지, 단순 조회 버전(구 L231) 삭제. (2026-05-20 초기 리뷰 Critical #1 누락분)
> 추가 처리됨 (2026-05-21): `app/services/album_service.py` `get_album_detail_by_spotify` 임시 주석 제거.

> ✅ 완료 (2026-05-21, SHA: fae9397)

---

### DEBT-5: AlbumOut.external_url 누락 (별도 추적)

- **발견**: PR-2 리뷰 중 발견. DB 조회 경로(`/albums/:id`, `/albums/by-spotify/:id`)의 `AlbumOut` 생성자에 `external_url` 필드가 전달되지 않아 응답에서 항상 `null`.
- **위치**: `app/services/album_service.py` `get_album_detail` 내 `AlbumOut(...)` 생성자
- **영향**: Spotify URL 정보가 DB-first 검색 응답에서 유실. `/candidates` 응답에는 포함됨 (별도 경로).
- **결정 필요**: 의도적 생략인가 (DB에 spotify_url 컬럼 없음?), 아니면 추가해야 하는가. Album 모델에 `spotify_url` 컬럼이 없으면 `ext_refs`에서 추출하거나 스키마 추가 필요.
- **우선순위**: PR-3 이후, 설계 확인 후 처리.

---

### PR-3: 디버그 코드 제거 — print 및 타이밍 코드 정리

- **제목**: `chore: 프로덕션 print/타이밍 코드 제거, 구조적 로깅으로 교체 (myblog_music)`
- **포함 항목**: DEBT-1, DEBT-4
  - `app/repositories/album_repo.py` get_existing_spotify_ids — print 전부 제거, `time.perf_counter` 제거, `db.connection()` 강제 획득 제거, 정상 로직만 유지
  - `app/clients/sqs_client.py` — SQS URL·메시지 본문 print 제거. 에러만 `logging.error` 로 교체
  - `app/services/candidate_search_service.py` — album_ids 목록 print 제거
  - 추측: Python 표준 `logging` 모듈로 교체 시 Lambda에서 CloudWatch 구조적 로그로 바로 연결됨
- **영향 레포**: `myblog_music`
- **수락 기준**: Lambda 실행 로그에 album_ids 리스트·SQS URL이 평문으로 출력되지 않음. 에러 발생 시에는 로그가 남음.
- **예상 소요 시간**: 2시간
- **선행 조건**: 없음 (PR-1과 병렬 진행 가능. 다른 파일을 건드리므로 충돌 없음.)

> ✅ 완료 (2026-05-21, SHA: f4a5308)

---

### PR-4: 보안 — /candidates 인증 추가 (auth-design.md 결정 이후 진행)

- **선행 조건**: `docs/tracks/auth-design.md`의 미결 질문 합의 완료. PR-2, PR-3 병합 이후.

---

### PR-5: CI 단위 테스트 게이트 추가 ⏸️

> ⏸️ 보류 — 설계 검증(architect) 결과 이후 재평가. `docs/decisions/0002-paused-pr5-pr6.md` 참조

- **제목**: `ci: deploy 전 단위 테스트 게이트 추가 (myblog_music)`
- **포함 항목**: INFRA-1 (단위 테스트 gate만)
  - `.github/workflows/deploy.yml`에 단위 테스트 job 추가
  - 통합 테스트(`tests/test_candidates_localstack.py`)는 CI gate에서 제외. 로컬 또는 스케줄 실행으로 분리.
- **영향 레포**: `myblog_music`
- **수락 기준**: 단위 테스트 실패 시 Lambda 배포가 차단됨. localstack 의존 테스트는 CI gate에 포함되지 않음.
- **예상 소요 시간**: 1~2시간
- **선행 조건**: PR-1~3 병합 이후.

---

### PR-6: DB 마이그레이션 — Track spotify_id UNIQUE 제약 추가 (별도 트래킹) ⏸️

> ⏸️ 보류 — 설계 검증(architect) 결과 이후 재평가. `docs/decisions/0002-paused-pr5-pr6.md` 참조

- **제목**: `db: tracks.spotify_id UNIQUE 제약 추가 마이그레이션`
- **포함 항목**: BUG-3 마이그레이션 파트
  - 기존 데이터 중복 spotify_id 확인 및 정리 스크립트
  - `CREATE UNIQUE INDEX CONCURRENTLY ON tracks (spotify_id);` (무중단 방식)
- **영향 레포**: `myblog_music` (공유 RDS이므로 `myblog_worker`도 영향 확인 필요)
- **수락 기준**: 마이그레이션 완료 후 `\d tracks`에서 UNIQUE 제약 확인. Worker의 upsert가 IntegrityError 없이 동작. 기존 트래픽 차단 없이 마이그레이션 완료 확인.
- **예상 소요 시간**: 1~2시간 (데이터 정리 시간 별도)
- **선행 조건**: PR-2 병합. 기존 DB 중복 데이터 확인 및 Jack 승인.

---

## 4. 의존성 그래프

```
PR-1 (오타·import·singleflight 삭제)    PR-3 (print 제거)
  └─→ PR-2 (런타임 버그)               ↑ 병렬 진행 가능 (다른 파일)
        └─→ PR-5 (CI 단위 테스트 gate) ← PR-1~3 이후
        └─→ PR-4 (인증)                ← auth-design.md 합의 이후

PR-2 병합 + Jack 승인
  └─→ PR-6 (DB 마이그레이션) ← 독립 트랙, 별도 일정
```

---

## 5. 미결정 / 질문 사항

1. **DESIGN-1 인증 방식**: `/candidates` 인증 설계 → `docs/tracks/auth-design.md` 참조

2. **INFRA-1 IaC 전환 상위 목표**: CI 게이트 이후 Terraform 전환 계획 → `docs/tracks/iac-migration.md` 참조

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

### PR-7: Worker — SQS error handling + AttributeError + logging

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

### PR-8: Publish — auth + CORS hardening

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

---

### ARCH-1: Schema single source of truth

- **Covers**: ARCH-1, ARCH-5
- **Decision needed**: Nominate `docs/contracts/schema.sql` as the canonical DDL. Each service schema file becomes a derived copy or is removed.
- **Scope**:
  - Add `aliases JSONB` column definition to backend schema
  - Fix album upsert in worker to include `ext_refs` in the `ON CONFLICT DO UPDATE` clause
  - Document drift policy: schema changes must update `docs/contracts/schema.sql` first
- **Prerequisite**: Team agreement on canonical location

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
