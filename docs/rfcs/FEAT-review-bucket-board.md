# FEAT-review-bucket-board: 평론 버킷 보드

- **Status**: draft
- **Owner**: 박지훈
- **Created**: 2026-06-03
- **Plan row**: `plan.md` → FEAT-review-bucket-board

---

## Goal

평론을 쓰고 싶은 앨범을 사용자가 직접 만든 칸반형 버킷(칼럼)에 담아두고, 버킷 간/내에서 드래그앤드롭으로
우선순위를 정하고, 카드 클릭으로 앨범 정보를 한눈에 보고, 그 자리에서 인라인 드로어로 평론을 작성·발행하거나
전체 편집기(`/write`)로 넘어갈 수 있는 "작성 전 단계(to-review queue)" 페이지가 생긴다. 단일 사용자(주인장)
전용 편집 도구이며, 검색/카드/작성기/앨범상세 등 기존 자산을 최대한 재사용한다.

## Non-goals

- 다중 사용자/공유 버킷 (단일 사용자 블로그 — `user_id` 없음).
- 자동 추천의 ML/외부 시그널화 — 초기 정렬은 DB 컬럼(release_date·popularity·best_new)만 쓰는 단순 가중합. 이후엔 수동 드래그가 진실.
- 버킷 자체의 공개/발행 (버킷은 비공개 편집 도구, 발행되는 건 평론 post뿐).
- Spotify 동기 호출 추가 (하드룰 #9). 앨범은 이미 DB에 있는 것만 담음 (필요 시 기존 candidates→SQS 흡수 플로우 경유).

## Current state

- 작성 플로우는 `myblog_front/src/pages/write.astro` → `WriterApp.tsx` 단발성뿐. "나중에 리뷰할 앨범" 을 담아둘 곳이 없다.
- 통합 검색: `myblog_front/src/components/writer/SubjectBlock.tsx` → `GET /api/music/search/unified` (albums/artists/tracks).
- 앨범 카드 UI: `myblog_front/src/components/reviews/ReviewsIndex.tsx` 의 `Cover`/`Stars` + `src/styles/reviews.css` 토큰.
- 앨범 상세: `GET /api/music/albums/{id}` (트랙·아티스트 포함).
- 본문/별점 입력: `BodyArea.tsx`(auto-grow + 선택 포맷팅), `DragRatingInput.tsx`(포인터 드래그 별점), 발행 모달 `SettingsPanel.tsx`.
- 작성 API: `POST /api/posts`, `POST /api/publish` (`album_ids`, `artist_ids`, `rating`, `body_mdx`, `recommended_track_ids` …) — `myblog_backend/app/api/routes/{posts,publish}.py`.
- auth fetch: `myblog_front/src/lib/api.ts` `apiFetch` (401 시 refresh 재시도). 페이지 가드: `/write` 의 `write.guard.ts` 패턴.
- shared_db 최신 마이그레이션 V5 (`migrations/`), 모델 `myblog_shared_db/src/myblog_shared_db/models.py`, 생성 스키마 `_generated_schema.sql`.
- 드래그앤드롭 라이브러리 없음 (`DragRatingInput` 은 별점 전용 커스텀 포인터).
- 단일 사용자: posts 에 author_id 없음, auth 는 Cognito JWT, user 테이블 없음.

## Target state

### 데이터 모델 (shared_db, Flyway V6)

`migrations/V6__review_buckets.sql` + `models.py`. 단일 사용자 → `user_id` 없음.

```
review_buckets
  id          UUID PK
  name        TEXT NOT NULL          -- 사용자가 지정 (예: "꼭", "신보", "보류")
  position    INT  NOT NULL          -- 칼럼 좌→우 순서
  color       TEXT NULL              -- 라벨 색 (선택)
  created_at  TIMESTAMPTZ
  updated_at  TIMESTAMPTZ

review_bucket_items
  id          UUID PK
  bucket_id   UUID FK → review_buckets (ON DELETE CASCADE)
  album_id    UUID FK → albums
  position    INT  NOT NULL          -- 버킷 내 순서 (초기값=자동추천, 이후 수동)
  note        TEXT NULL              -- "왜 리뷰하려는지" 메모
  status      ENUM(candidate, drafting, published) DEFAULT candidate
  post_id     UUID FK → posts NULL   -- 인라인/전체 작성으로 발행되면 연결
  rec_reason  TEXT NULL              -- 자동추천 이유 스냅샷 (신보/인기/best_new)
  added_at    TIMESTAMPTZ
  updated_at  TIMESTAMPTZ
  UNIQUE(bucket_id, album_id)        -- 같은 버킷 내 중복 방지
```

### 백엔드 API (myblog_backend — posts/categories 와 같은 서비스)

새 라우터 `myblog_backend/app/api/routes/buckets.py` + `BucketService`. albums 는 shared_db 로 읽음.

| 메서드 | 경로 | 용도 | auth |
|--------|------|------|------|
| GET | `/api/buckets` | 전 버킷+아이템(앨범 조인, 정렬) | edge_guard |
| POST | `/api/buckets` | 버킷 생성 `{name, color?}` | Cognito JWT |
| PATCH | `/api/buckets/{id}` | 이름/색/칼럼 position 변경 | Cognito JWT |
| DELETE | `/api/buckets/{id}` | 버킷 삭제 (아이템 cascade) | Cognito JWT |
| POST | `/api/buckets/{id}/items` | 앨범 담기 `{album_id, note?}` → 자동 position | Cognito JWT |
| PATCH | `/api/buckets/{id}/items/{item_id}` | note/status 수정 | Cognito JWT |
| DELETE | `/api/buckets/{id}/items/{item_id}` | 아이템 제거 | Cognito JWT |
| PUT | `/api/buckets/reorder` | 드래그 결과 일괄 반영 `{buckets:[{id, item_ids:[...]}]}` | Cognito JWT |

- **`PUT /api/buckets/reorder`** 가 DnD 영속화 핵심: 영향받은 버킷의 정렬된 item_id 리스트를 통째로 받아 멱등하게 position 재할당.
- **자동 추천(`BucketService`)**: 담을 때 `score = w_recency·recency(release_date) + w_pop·(popularity/100) + w_bnm·best_new` 로 초기 position 결정, `rec_reason` 기록. 이후엔 드래그가 진실.
- **중복 가드**: 담으려는 앨범이 이미 `post_albums` 에 있으면 응답에 `already_reviewed: true` → 프론트 배지.
- 변경 라우트는 `infra/apigateway.tf` 에 엔트리 추가.

### Contract

backend `openapi.json` regen → `tools/merge_openapi.py` → `docs/contracts/openapi.json` → frontend `pnpm generate:types`.

### 프론트엔드 (myblog_front)

- 페이지 `src/pages/queue.astro` → `<BucketBoard client:load />`, `/write` 처럼 auth 가드.
- 신규 `src/components/queue/`: `BucketBoard.tsx`(`@dnd-kit` DndContext + reorder 영속), `BucketColumn.tsx`, `AlbumCard.tsx`(Cover/Stars 재사용 + status/already_reviewed 배지 + rec_reason 칩), `AddAlbumModal.tsx`(SubjectBlock 검색 재사용), `AlbumDetailPanel.tsx`(`/api/music/albums/{id}`), `ReviewDrawer.tsx`(인라인 작성·발행 + "/write 로 열기").
- 신규 라이브러리 `@dnd-kit/core` + `@dnd-kit/sortable`.
- **드로어 localStorage 충돌 주의**: `WriterApp` 의 `'lowfreq-draft'` 단일 키를 덮어쓰지 않게, 드로어는 아이템별 키 또는 백엔드 `status=drafting` 으로 분리.

## Steps

각 스텝 독립 머지. 하드룰 #4 — 세션당 1스텝, 스텝 사이 prod-observe 게이트.

### Step 0 — RFC + plan.md (이 문서)

이 RFC 작성 + `plan.md` Active 한 줄 포인터. docs-only.

**Verification**: 문서 리뷰. 코드 변경 없음.

---

### Step 1 — shared_db V6 마이그레이션 + 모델

`migrations/V6__review_buckets.sql`(두 테이블 + enum), `models.py` 모델 2개, `_generated_schema.sql` regen, `pyproject.toml` 버전 bump + 태그.

**Verification**:
```
cd myblog_shared_db && pytest          # 모델 ↔ _generated_schema.sql 일치
# V6 가 test-db 에 클린 적용되는지 (reference-test-db-url-source)
```

**Rollback**: V6 는 신규 테이블만 추가 (기존 테이블 무변경). 머지 전 prod apply 후 문제 시 `DROP TABLE review_bucket_items, review_buckets`.

**롤아웃 주의**: reference-shared-db-cross-repo-rollout — migration prod apply 는 **머지 전** 필수. 그래야 Step 2 backend pin bump 후 unknown table 500 안 남.

---

### Step 2 — backend buckets API

`BucketService` + `routes/buckets.py`(CRUD + items + reorder + 자동추천 + 중복가드), shared_db pin bump, `infra/apigateway.tf` 변경 라우트 엔트리, backend `openapi.json` regen, pytest.

**Verification**:
```
cd myblog_backend && pytest
# 로컬 cURL: 버킷 생성 → 앨범 담기(자동 position 확인) → reorder → 삭제
# 이미 리뷰한 앨범 담기 → already_reviewed:true 확인
cd infra && terraform plan             # apigateway 클린
```

**Rollback**: 라우터 미등록 + apigateway 엔트리 revert. 테이블은 Step 1 소관.

---

### Step 3 — workspace contract merge

`tools/merge_openapi.py` → `docs/contracts/openapi.json` 재생성·커밋. reference-openapi-pydantic-version-drift 주의.

**Verification**:
```
python tools/merge_openapi.py && git diff --stat docs/contracts/openapi.json
```

---

### Step 4 — frontend 보드 UI

`pnpm generate:types`, `queue.astro` + `BucketBoard`/`BucketColumn`/`AlbumCard`/`AddAlbumModal`/`AlbumDetailPanel`, `@dnd-kit` 도입. 버킷 CRUD·담기·드래그·상세 동작.

**Verification**:
```
cd myblog_front && pnpm lint && pnpm exec astro check
# dev server: 버킷 N개 생성/이름변경 → 검색→담기 → 버킷 간/내 드래그 → 새로고침 영속 → 카드 클릭 상세
# feedback-browser-verify-ui-changes / feedback-ui-repro-realistic-data (긴 제목·다수 항목)
```

**Rollback**: 신규 페이지/컴포넌트 제거 (기존 화면 무영향).

---

### Step 5 — frontend 인라인 작성 드로어

`ReviewDrawer` 저장(draft)·발행(`POST /api/posts`/`publish`), `/write?album=` 프리필 이동(WriterApp 소폭 확장), 발행 성공 시 아이템 `status=published`/`post_id` 갱신.

**Verification**:
```
cd myblog_front && pnpm lint && pnpm exec astro check
# dev server: 드로어 인라인 발행 → published 배지 + post 링크 → "전체 편집기로 열기" 이동
```

**Rollback**: 드로어 컴포넌트 제거, 보드는 Step 4 상태로 유지.

---

## Open questions

1. **페이지 경로** — `/queue` vs `/reviews/queue`, 네비 노출 여부. Step 4 블록.
2. **자동추천 가중치** — `w_recency`/`w_pop`/`w_bnm` 초기값과 recency 정규화 방식. Step 2 블록.
3. **발행 후 아이템 처리** — published 배지로 유지 vs 자동 아카이브/제거. Step 5 블록.
4. **인라인 draft 저장 위치** — 백엔드 `status=drafting` vs 프론트 아이템별 localStorage 키. Step 5 블록.

## Decisions log

| Date | Decision | Step |
|------|----------|------|
| 2026-06-03 | 저장: 백엔드 테이블 처음부터 (localStorage MVP 아님) — 사용자 결정 | 0 |
| 2026-06-03 | 레이아웃: 사용자 생성 칸반 버킷 + 버킷 간/내 드래그 — 사용자 결정 | 0 |
| 2026-06-03 | 우선순위: 자동추천 초기값 + 수동 드래그 override — 사용자 결정 | 0 |
| 2026-06-03 | 평론 작성: 인라인 드로어(저장·발행) + /write 이동 둘 다 — 사용자 결정 | 0 |
