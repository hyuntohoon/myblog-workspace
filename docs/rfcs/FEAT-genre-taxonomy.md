# FEAT-genre-taxonomy: 장르 브랜치 저작 (v1, authoring-only)

- **Status**: draft
- **Owner**: 박지훈
- **Created**: 2026-06-04
- **Plan row**: `plan.md` → FEAT-genre-taxonomy

---

## Goal

블로그 주인장이 **장르 트리(2단: 상위 장르 → 하위 장르)를 직접 손으로 저작**할 수 있는 도구가 생긴다.
장르는 임의 자유입력이 아니라 **관리되는 통제 어휘(controlled vocabulary)** 로, shared_db `genres`
테이블에 캐노니컬하게 저장된다. 저작 캔버스의 출발점은 **이미 prod `artists.genres` 에 들어있는 실제
장르**(케이팝/한국 랩/시티 팝 …)를 부모 없는 풀(unparented pool)로 시드한 것이고, 주인장이 상위 장르를
만들고 각 항목에 부모를 지정해 트리를 큐레이팅한다. 라벨은 **영문 canonical(slug + label_en) + 한국어
표시(label_ko)**. v1 은 데이터 토대 + 저작 UI 까지이며, **독자 화면 변화는 없다**(앨범↔장르 연결·필터·
통합 뷰는 v2+).

## Non-goals

- **앨범↔장르 연결** (`album_genres` M:M + worker 가 MB release-group 으로 채우기) — v2. 이게 "아티스트
  장르 복사" 부정확성을 *실제로* 고치는 단계지만 이번 범위 밖.
- **글 쓸 때 다중 장르 부착** (`post_genres` + writer 멀티셀렉트) — v2.
- **장르 기반 필터** (music search + review search) / **통합 "장르로 묶어보기" 뷰** — v2.
- **rename / merge / delete 관리** — v2. v1 은 **생성 + 부모지정**만. (merge 는 `album_genres` 재지정
  로직을 동반하므로 연결이 생긴 뒤에야 의미.)
- **다중부모 DAG(RYM식)** — 채택 안 함. 2단 단일부모만.
- **외부 API 동기 호출** (Spotify/MusicBrainz/Discogs) — 저작 경로엔 일절 없음. 시드는 prod DB 의
  1회성 오프라인 추출(하드룰 #9 + 서비스 분리 격리 유지).

## Current state

- 장르 컬럼은 `artists.genres`(JSONB 문자열 배열) 하나뿐. **앨범·트랙엔 장르 컬럼 없음**
  (`myblog_shared_db/src/myblog_shared_db/models.py`).
- "앨범 장르"는 가짜다: `myblog_backend/app/services/content_sync.py` 의 `derive_subject_meta` 가
  **대표 아티스트의 Spotify 장르**를 앨범 frontmatter(`musicReview.genres[]`)로 복사. 한 아티스트의 모든
  앨범이 동일 장르.
- prod `artists.genres` 는 **ko-KR localized** (케이팝/한국 랩/시티 팝/브릿팝 …) — memory
  `project-prod-artists-genres-korean`.
- 캐노니컬 장르 목록/계층/dedup 전무 ("indie rock" vs "indie-rock" 공존).
- `/reviews` 인덱스만 `genres[]` 배열 인식 필터 보유(`myblog_front/src/lib/reviews.ts`); music search 엔
  장르 필터 없음.
- shared_db 최신 마이그레이션 **V11**(review_buckets_parent_id), 버전 **0.10.0**. backend pin `@v0.10.0`.
- 관리형 admin write 의 정착 패턴: backend 의 Cognito-JWT 라우트(`posts`/`publish`/`buckets`).
  단일 사용자(주인장) — user 테이블·author_id 없음.

## Target state

### 데이터 모델 (shared_db, V14)

`migrations/V14__genres.sql` + `models.py` `Genre` 모델. 단일 사용자 → `user_id` 없음.

> **마이그레이션 번호 deconfliction (2026-06-05)**: V12(pg_trgm) + V13(album/track aliases) 는
> `FEAT-music-search-recall` 가 예약. genres 는 충돌 회피로 **V14**. 두 RFC 의 마이그레이션은
> disjoint 테이블/익스텐션이라 번호만 deconflict 되면 병행 가능. 단 hand-numbered `V{N}__` 는
> 연속 적용이 전제(`reference-shared-db-cross-repo-rollout`) — V14 는 V12/V13 *적용 후* 에 prod
> 적용. genre-taxonomy 가 music-search 보다 먼저 실행되면 그때 free 한 V# 로 재지정.

```sql
CREATE TABLE IF NOT EXISTS genres (
  id         UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  slug       TEXT        NOT NULL UNIQUE,            -- canonical en key, e.g. 'city-pop'
  label_en   TEXT        NOT NULL,                   -- 'City Pop'
  label_ko   TEXT        NOT NULL,                   -- '시티 팝'
  parent_id  UUID        REFERENCES genres(id) ON DELETE RESTRICT,  -- NULL = top genre
  source     TEXT        NOT NULL DEFAULT 'manual',  -- 'seed-prod' | 'manual' | (v2) 'musicbrainz' | 'discogs'
  ext_refs   JSONB       NOT NULL DEFAULT '{}'::jsonb, -- v2 MB/Discogs id slot (free now; migration later)
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_genres_parent_id ON genres(parent_id);
```

- **2단 불변식**(자식의 부모는 반드시 top: `parent.parent_id IS NULL`)은 **앱 레이어(GenreService)에서
  강제**. Postgres CHECK 제약은 서브쿼리/타행 참조 불가라 DDL 로 표현 못 함. 단일 작성자(주인장)라
  TOCTOU 무관 — `posts` 에 author_id 가 없는 것과 같은 근거. (architect: DB-인덱스 norm 대비 의도적
  다운그레이드 → 모델 주석에 명시.) `ON DELETE RESTRICT` 로 "자식 있는 부모 삭제"는 DB 가 막음.
- `ext_refs JSONB` 는 `Album`/`Artist`/`Track`/`Post` 와 동일한 외부소스 hook — v2 MB sourcing 이
  스키마 변경 없이 붙도록 v1 에 미리 둠 (architect Q4b).

### 백엔드 API (myblog_backend — posts/categories/buckets 와 같은 서비스)

새 라우터 `app/api/routes/genres.py` + `GenreService`(`app/services/genre_service.py`). 구현 스타일은
**`bucket_service` 패턴(ORM 모델 + 타입드 예외 → 라우트에서 HTTPException 매핑)** 을 따른다.
`category_service` 의 raw `text()`+`db.commit()` 스타일은 복사하지 않음 (architect Q1).

| 메서드 | 경로 | 용도 | auth |
| ------ | ---- | ---- | ---- |
| GET  | `/api/genres/tree` | 2단 트리 `[{id,slug,label_en,label_ko,children:[…]}]` + 미분류 풀 | edge_guard |
| POST | `/api/genres` | 생성 `{slug,label_en,label_ko,parent_id?}` — slug unique, parent 는 top 만, 자식은 부모 불가 | **Cognito JWT** |

- **GET 은 catch-all `GET /api/{proxy+}`(edge_guard)** 로 이미 커버 — 별도 라우트 불필요
  (`GET /api/buckets`/`/api/categories` 와 동일).
- **POST 는 명시적 JWT 라우트** — `infra/apigateway.tf` 에 `genres_post` 추가. ⚠️ **`buckets_post`
  (JWT) 패턴을 복사할 것. `categories_post` 는 `authorization_type` 이 없어 *미인증* 이므로 절대 복사
  금지** (architect Q5 🔴, apigateway.tf:76-80 확인됨).
- 2단 불변식 거부: parent_id 주어지면 `SELECT parent_id FROM genres WHERE id=:parent_id` → 그 행의
  parent_id 가 non-null 이면 422 `depth_exceeded`.

### Contract

backend `openapi.json` regen → `tools/merge_openapi.py` → `docs/contracts/openapi.json` → frontend
`pnpm generate:types`. workspace 먼저 머지 (`reference-workspace-contract-merge-order`); pydantic 버전
드리프트 주의 (`reference-openapi-pydantic-version-drift`).

### 프론트엔드 (myblog_front)

- 페이지 `src/pages/genres/index.astro`(경로 `/genres`) → `<GenreAuthoring client:load />`, `/write`·
  `/reviews/queue` 처럼 auth 가드(`src/scripts/genres.guard.ts`, `queue.guard.ts` 템플릿).
- `src/components/genres/GenreAuthoring.tsx` — 2-pane: (좌) 트리 + 미분류 풀, (우) 생성 폼 + 부모
  피커(상위 장르만 노출, 자식은 부모로 선택 불가). 제출 = `apiFetch` 로 `POST /api/genres`, 성공 시 트리
  refresh. **`frontend-design` 스킬로 설계**(`feedback-frontend-design-plugin`).
- `src/lib/genres.ts` — `fetchGenreTree()`/`createGenre()` 헬퍼.

## Steps

각 스텝 독립 머지. 하드룰 #4 — 세션당 1스텝, 스텝 사이 prod-observe 게이트. 저장소별 브랜치/커밋
(`feedback-nested-repo-branch-per-repo`, `feedback-bash-cwd-resets`).

### Step 0 — RFC + plan.md 포인터 (이 문서, docs-only)

이 RFC 작성 + `plan.md` Backlog 항목을 한 줄 포인터로 축약 + RFC README 인덱스 추가. 코드 변경 없음.

**Verification**: 문서 리뷰 (TEMPLATE.md 구조 일치). `git diff --stat`.

---

### Step 1 — shared_db V14 마이그레이션 + Genre 모델

`migrations/V14__genres.sql`(위 DDL), `models.py` `Genre`(self-ref `parent`/`children` + 2단 다운그레이드
주석), `_generated_schema.sql` regen, `pyproject.toml` 버전을 직전 shared_db 버전의 다음 minor 로
bump + 매칭 태그 (music-search-recall V12/V13 선착 시 `0.12.0`→`0.13.0` + `v0.13.0`; genre 가 먼저면
`0.10.0`→`0.11.0` + `v0.11.0`), canonical `docs/contracts/schema.sql` 동기.

**롤아웃 (CRITICAL — `reference-shared-db-cross-repo-rollout`)**: V14 를 **prod Neon 에 머지 *전* 적용**
→ `\dt genres` 확인 → shared_db PR 머지 → 태그. 순서 틀리면 Step 3 backend 가 unknown-table 500.
V14 는 V12/V13(music-search) *적용 후* prod 적용 (연속 번호 전제).

**Verification**:
```
cd myblog_shared_db && pytest        # 모델 ↔ _generated_schema.sql 일치
psql "$TEST_DB_URL" -f migrations/V14__genres.sql -v ON_ERROR_STOP=1   # 클린 적용
# top G1 → child G2(parent=G1) OK; grandchild G3(parent=G2) → 앱레이어 거부(Step 3), DELETE G1 while child → RESTRICT
```
**Rollback**: `DROP TABLE genres;` (참조 FK 없음, 순수 additive). prod DROP 은 사람 승인(룰 #3).

---

### Step 2 — prod 장르 시드 스크립트 (자체 스텝/PR)

`myblog_shared_db/scripts/seed_genres_from_prod.py` — 1회성·멱등:
- prod `artists.genres` distinct 추출: `SELECT DISTINCT jsonb_array_elements_text(genres) FROM artists WHERE genres <> '[]'`.
- 각 raw 문자열을 **ko→en 매핑 테이블**로 변환 (예: `케이팝`→`k-pop`/`K-Pop`/`케이팝`,
  `한국 랩`→`korean-rap`/`Korean Rap`/`한국 랩`, `시티 팝`→`city-pop`/`City Pop`/`시티 팝`).
- `INSERT … (slug,label_en,label_ko,source) … ON CONFLICT (slug) DO NOTHING`, 전부 `parent_id=NULL`,
  `source='seed-prod'`. **부모 지정은 안 함** (저작 UI 의 몫).
- 미매핑 문자열 → stderr 로그 → 사람이 매핑 추가/스킵 결정 (Open Q1).

별도 스텝 이유: ko→en 큐레이션은 스키마가 아닌 데이터 결정이라 마이그레이션 DDL 과 분리.

**Verification**:
```
python scripts/seed_genres_from_prod.py --dry-run     # INSERT 안 하고 매핑/스킵 출력 → 사람 리뷰
python scripts/seed_genres_from_prod.py --execute      # BEGIN/COMMIT (reference-database-url-psql)
psql "$DATABASE_URL" -c "SELECT slug,label_en,label_ko,source FROM genres ORDER BY slug;"
```
**Rollback**: `DELETE FROM genres WHERE source='seed-prod';`

---

### Step 3 — backend genre API + infra

`app/api/routes/genres.py`(GET tree + POST create, 2단 거부), `app/services/genre_service.py`
(bucket_service 스타일), `app/api/schemas.py`(GenreNode/Tree/CreateReq/Resp), `app/main.py` include,
`requirements.txt` pin = Step 1 의 genres 태그 (`@v0.13.0` 가정), `infra/apigateway.tf` `genres_post`(JWT, **buckets_post 복사**),
`openapi.json` regen, `tests/test_genres.py`.

**Verification**:
```
cd myblog_backend && pytest tests/test_genres.py -v   # create top/child + depth 거부 + slug 409 + tree shape
curl -s -X POST localhost:8000/api/genres -H 'Content-Type: application/json' \
  -d '{"slug":"k-pop","label_en":"K-Pop","label_ko":"케이팝"}' | jq .     # ENV=local JWT bypass
curl -s localhost:8000/api/genres/tree | jq .
cd infra && terraform plan                              # genres_post add 만, 예상 외 드리프트 없으면 stop
```
(로컬 DB 없으면 pytest+lint 갈음 — `feedback-local-db-smoke-fallback`; prod smoke 는 머지 후.)
**Rollback**: 라우터/스키마/include/pin/apigateway 엔트리 revert. 테이블은 Step 1 소관.

---

### Step 4 — workspace contract 머지

`python tools/merge_openapi.py` → `docs/contracts/openapi.json` 재생성·커밋.

**Verification**:
```
python tools/merge_openapi.py && git diff --stat docs/contracts/openapi.json   # genres 경로/스키마만
```
**Rollback**: openapi.json 직전 커밋으로 revert.

---

### Step 5 — frontend 저작 UI

`pnpm generate:types`(`api.gen.ts` 커밋 — `feedback-frontend-api-gen-sync`), `src/pages/genres/index.astro`
+ `genres.guard.ts`, `src/components/genres/GenreAuthoring.tsx`(2-pane, **frontend-design 스킬**),
`src/lib/genres.ts`, `src/styles/genres.css`. Node 20 필수(`reference-front-node-version`).

**Verification**:
```
cd myblog_front && pnpm lint && pnpm exec astro check
# dev server (browser-verify — feedback-browser-verify-ui-changes):
# 1) /genres 비로그인 → 가드 리다이렉트  2) 로그인 → 시드 목록 로드
# 3) 상위 장르 생성 → 좌측 트리 표시  4) 하위 생성(부모=상위) → 중첩
# 5) 부모 피커에 자식 안 보임  6) 새로고침 영속(localStorage 아님)
# feedback-ui-repro-realistic-data: 15+ 장르 + 긴 한국어 라벨
```
**Rollback**: 신규 페이지/컴포넌트/스타일 제거 (기존 화면 무영향).

---

## Open questions

1. **ko→en 매핑 큐레이션 (blocks Step 2)** — `artists.genres` distinct 전체 목록을 dry-run 으로 뽑아
   주인장과 1회 큐레이션. (a) 동의어 병합(`케이팝`+`K-Pop`→`k-pop`)? (b) 미매핑 문자열은 스킵 vs
   romanize placeholder? 권장: dry-run 먼저 → 합의 후 live INSERT.
2. **`/genres` 경로 (blocks Step 5)** — `/genres` vs `/admin/genres` vs `/reviews/genres`. v1 은
   로그인 후에만 접근. 기본 `/genres` 제안.
3. **slug UNIQUE 전역 vs 범위(`UNIQUE(parent_id,slug)`)** — 엄격 2단 단일부모면 전역으로 충분.
   단 v2 에서 같은 자식 라벨이 두 상위 아래 반복되면 전역 unique 가 막아 파괴적 마이그레이션 필요
   (architect Q4a 🟡). 전역 유지로 시작, v2 진입 시 재확인.
4. **2단 강제 위치** — 앱 레이어(GenreService) 채택(단일 작성자 근거). 추후 다작성자 되면 트리거로
   격상 (architect Q3 🟡). 현재 트리거 불필요.

## Decisions log

| Date | Decision | Step |
|------|----------|------|
| 2026-06-04 | 장르 단위: 앨범 중심(장기), v1 은 저작 토대만 — 사용자 결정 | 0 |
| 2026-06-04 | 첫 기능 = 브랜치 저작 우선(데이터 연결보다 먼저), 장르 = 에디토리얼 — 사용자 결정 | 0 |
| 2026-06-04 | 트리: 2단 단일부모(Discogs식), 다중부모 DAG 배제 — 사용자 결정 | 0 |
| 2026-06-04 | 라벨: 영문 canonical(slug+label_en) + 한국어 표시(label_ko) — 사용자 결정 | 0 |
| 2026-06-04 | 시드: prod 실제 장르에서 미분류 풀로, 벌크 MB/Discogs import 안 함 — 사용자 결정 | 2 |
| 2026-06-04 | v1 범위: 생성 + 부모지정만 (rename/merge/delete = v2) — 사용자 결정 | 0 |
| 2026-06-04 | genre API 두 라우트 모두 backend, read 를 music 으로 분리 안 함 (v2 music 은 자체 필터 read 추가) — architect | 3 |
| 2026-06-04 | POST auth 는 buckets_post(JWT) 복사, categories_post(미인증) 금지 — architect 🔴 | 3 |
| 2026-06-04 | 2단 불변식 앱 레이어(단일 작성자) + ON DELETE RESTRICT, CHECK-서브쿼리 불가 | 1 |
| 2026-06-04 | `ext_refs JSONB` v1 에 미리 추가 (v2 MB sourcing 무마이그레이션 확장) — architect 🟡 | 1 |
| 2026-06-05 | shared_db 마이그레이션 V12→**V14** 리넘버: V12(pg_trgm)/V13(aliases) 는 `FEAT-music-search-recall` 가 예약 (plan.md). genres 는 V14, V12/V13 적용 후 prod 적용 — RFC 우선순위 검토 | 1 |
