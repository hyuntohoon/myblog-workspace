# FEAT-writer-cleanup: Writer 발행 폼 정리 + 삭제 플로우 (status=archived)

- **Status**: draft
- **Owner**: TBD
- **Created**: 2026-05-29
- **Plan row**: `plan.md` → FEAT-writer-cleanup
- **회의록 출처**: `/Users/park_hyun/.claude/plans/soft-hatching-raccoon.md` (2026-05-29 브레인스토밍, 점수 28)

---

## Goal

WriterApp 의 매거진 잔재(headline/dek/author/authorRole/tags/bestNew/genre) 를 제거해 DB 에 실제 저장되는 필드와 입력 폼을 일치시키고, 삭제 플로우를 `status=archived` 가짜 soft delete + `?hard=true` 영구 삭제 두 갈래로 마련한다. Post 스키마는 변경하지 않는다 — `status` enum 과 기존 컬럼만으로 달성한다.

## Non-goals

- `posts.author` 컬럼 추가 — 단일 작성자 가정. 다중 작성자가 생기면 별도 RFC.
- `posts ↔ genres` 다대다 관계 신설 — 본 RFC 범위 밖. 차후 CHORE-schema-audit 에서 분리.
- 매거진 스타일 헤드라인/dek 의 시각적 대체(별도 description 강조) — view 페이지 디자인은 FEAT-view-redesign 에서 다룸.
- Cognito 클레임 → DB 의 author 저장. 컬럼이 없으니 의미 없음.
- DELETE 동작의 backward compat 토큰. 단일 작성자 본인 UI 이므로 한 PR 로 갈아엎음.

## Current state

**WriterApp 상태 (myblog_front/src/components/writer/WriterApp.tsx:104-115):**
- 입력 필드: `subject`(AlbumDetail), `score`, `bestNew`, `headline`, `dek`, `body`, `tags[]`, `section`, `genre`, `publishDate`, `author`, `authorRole`
- 저장 시 매핑(myblog_front/src/scripts/write/api.ts:9): `title`=headline, `description`=dek, `body_mdx`=body, `posted_date`=publishDate, `category`=section, `album_ids`=[subject.album.id], `artist_ids`=subject.artists ids, `album_cover_url`, `rating`=score
- **저장 안 되는 dead 필드**: `bestNew`, `tags`, `genre`, `author`, `authorRole`. 입력은 받지만 payload 에서 누락
- Edit 모드 로드(WriterApp.tsx:139-150)에서도 위 dead 필드는 비어있는 채로 시작 — 사용자 혼란

**Post 모델 필드 (myblog_shared_db/models.py:195-227):**
- 저장 컬럼: `id, slug, title, description, body_mdx, body_text, posted_date, last_updated_at, status(enum draft/published/archived), category_id, search_index, rating, rating_scale, album_cover_url, extra(JSONB)`
- 관계: `albums`, `artists` (M:M via post_albums, post_artists), `recommended_tracks`
- `author` 컬럼 없음

**DELETE 현황 (myblog_backend/app/api/routes/posts.py:139-148):**
- Hard delete 만 구현. `svc.delete(db, post_id)` → `PostRepository.delete_by_id()` → `db.delete(post)`.
- CASCADE 로 `post_albums`, `post_artists`, `post_recommended_tracks` 연쇄 삭제.
- 프론트엔드 호출 코드 없음 (`src/scripts/write/api.ts` 에 delete 함수 부재).

**GET /api/posts 필터 현황:**
- 호출 시 `status` 필터 옵션 — 확인 필요 (PR-1 작성 시 코드 확인 후 명시).
- 클라이언트가 `status=published` 만 보냐, 또는 무필터 후 클라이언트에서 거르냐 미확인.

## Target state

**WriterApp 입력 필드(축소):**
- `subject`(AlbumDetail), `score`, `body`, `publishDate`, `section`(= category), `title`, `description`
- `headline` → `title`, `dek` → `description` 으로 이름 정리 (변수만 변경, UI 라벨은 의도에 맞춰)
- 제거: `bestNew`, `tags`, `genre`, `author`, `authorRole`
- `loadDraft` 의 기존 dead 키는 무시(silent ignore) — 마이그레이션 코드 없음

**Backend DELETE 분기:**
- `DELETE /api/posts/{id}` 기본: `status=archived` 로 변경 (가짜 soft delete) — 응답 200 + 변경된 status
- `DELETE /api/posts/{id}?hard=true`: 현 hard delete 유지 — 응답 204
- 새 엔드포인트: `PATCH /api/posts/{id}/restore` — status=archived → published (복구). 필요 최소량만 추가
- 인증: 셋 다 Cognito JWT (현행과 동일)

**GET /api/posts:**
- 기본 응답: `status='published'` 만 (퍼블릭 read 기본값)
- `?include_archived=true` (Cognito 토큰 있을 때만 유효): archived 포함

**프론트엔드 삭제 UI:**
- writer/내 글 페이지에서 "보관(Archive)" / "완전 삭제(Hard delete)" 두 액션
- 보관: 즉시 실행, 토스트 "보관됨 — 복구 가능"
- 완전 삭제: 확인 모달 ("복구 불가, 정말 삭제할까요?") → 진행
- 보관함 보기: 관리 모드(로그인 상태)에서 `?include_archived=true` 토글, 복구 버튼 노출

## Steps

각 단계는 독립 PR. PR-1 머지 → PR-2 머지 → PR-3 머지 순서.

### Step 1 — PR-1: Backend DELETE 분기 + status 필터

**변경 파일 (예상):**
- `myblog_backend/app/services/post_service.py` — `archive(db, post_id)` / `delete(db, post_id, hard=False)` / `restore(db, post_id)` 메소드 추가
- `myblog_backend/app/repositories/post_repository.py` — 기존 `delete_by_id` 옆에 `set_status(post_id, status)` 추가
- `myblog_backend/app/api/routes/posts.py:139` — DELETE 핸들러에 `hard: bool = Query(False)` 파라미터; PATCH `/restore` 추가; GET 목록에 `include_archived` 옵션
- `myblog_backend/app/api/schemas.py` — 응답 스키마 보강 (필요 시 `status` 노출 확인)
- `myblog_backend/tests/` — DELETE 두 경로 + restore + GET 필터 케이스 추가
- `openapi.json` 재생성 + 커밋

**Verification:**
```bash
cd myblog_backend && uv run pytest tests/ -k "delete or archive or restore"
cd myblog_backend && uv run python -m app.openapi_gen > openapi.json && git diff openapi.json
# workspace 머지 PR 자동 발생 확인 또는 수동 merge_openapi.py 실행
```

**Rollback**: revert PR-1. 스키마 변경 없음 → DB 영향 0. 진행 중 archive 된 데이터는 archived 상태로 남음(읽기 안 됨) — restore 또는 직접 SQL UPDATE 로 복구 가능.

---

### Step 2 — PR-2: WriterApp dead 필드 제거

**변경 파일:**
- `myblog_front/src/components/writer/WriterApp.tsx` — useState 5개 제거 (`bestNew`, `tags`, `section`→유지하되 라벨만 정리, `genre`, `author`, `authorRole`), `headline`/`dek` 변수명은 그대로 두되 UI 라벨만 "제목"/"부제" 로 정리(또는 변수도 함께 rename — 둘 중 PR 작성 시 결정)
- `myblog_front/src/scripts/write/api.ts` — 페이로드 매핑은 이미 위 필드 미사용 → 검증만
- `myblog_front/src/scripts/write/ui.ts` — 폼 렌더링에서 dead 입력 컴포넌트 제거
- `myblog_front/src/scripts/write/draft.ts` (또는 동등 위치) — `DraftState` 타입에서 dead 키 제거, `loadDraft` 는 부재 키 silent ignore
- 관련 import / 상수 (`SECTIONS`, `GENRES`) — `GENRES` 만 쓰는 경우 파일 제거

**Verification:**
```bash
cd myblog_front && pnpm lint
cd myblog_front && pnpm exec astro check
cd myblog_front && pnpm dev  # localhost 띄워 글 쓰기 → 발행 → 다시 진입 매트릭스 click-through
# CLAUDE.md DoD: UI 변경은 브라우저 확인. 결과 인용 후 PR body 에 첨부
```

**Rollback**: revert PR-2. 백엔드는 dead 필드를 받지도 않으므로 영향 0.

---

### Step 3 — PR-3: 삭제 UI + 보관함

**변경 파일:**
- `myblog_front/src/scripts/write/api.ts` — `archivePost(id)`, `deletePost(id)`, `restorePost(id)` 추가 (apiFetch 사용)
- `myblog_front/src/pages/blog/[slug].astro` 또는 내 글 목록 페이지 — 작성자(=Cognito 로그인) 일 때만 보관/삭제 버튼 노출
- `myblog_front/src/components/` — confirm 모달 컴포넌트 (간단한 dialog 한 개)
- `myblog_front/src/scripts/myposts.client.ts` (또는 신설) — `?include_archived=true` 토글 + 복구 버튼
- 라우팅: 별도 페이지 추가 없이 기존 글 목록에 토글로 노출 (적은 비용 우선)

**Verification:**
```bash
cd myblog_front && pnpm lint && pnpm exec astro check
cd myblog_front && pnpm dev  # 글 작성 → 보관 → 보관함 토글 → 복구 → 완전 삭제 → 모달 확인
```

**Rollback**: revert PR-3. 백엔드 archive 된 데이터는 이전 PR-1 가 머지된 상태이므로 SQL UPDATE 로 복구 가능.

---

## Open questions

1. **WriterApp `section` 라벨** — UI 에서 "Section" 으로 둘지 "Category" 로 바꿀지. (PR-2 작성 시 결정 — Blocks Step 2)
2. **headline/dek 변수명** — JSX 노출만 한국어 라벨로 바꾸고 변수명은 유지할지, 변수까지 `title`/`description` 으로 rename 할지. rename 하면 diff 크지만 명확. (PR-2 — Blocks Step 2)
3. **GET /api/posts 의 `status` 파라미터 현재 동작** — 코드 확인 후 `include_archived` 도입 방식 확정. PR-1 작성 직전 30분 조사. (Blocks Step 1)
4. **보관함 노출 위치** — 별도 페이지 vs 기존 글 목록 토글. 본 RFC 는 토글 권고. 사용자 의도 재확인 가능. (Blocks Step 3)
5. **Cognito 클레임으로 본인 글 판단** — 단일 작성자라 모든 글이 본인이므로 sub 검증 불필요. 다인 시 별도 RFC 필요. (Blocks Step 3 — 본 RFC 가정으로 진행)

## Decisions log

| Date | Decision | Step |
|------|----------|------|
| 2026-05-29 | hard 컬럼 추가 대신 `status=archived` 활용. 사용자 회의 결정 (점수 28) | All |
| 2026-05-29 | `posts.author` 컬럼 추가 보류. 1인 작성자 가정 | Step 1 |
| 2026-05-29 | `genre` 멀티 선택은 별도 PR (스키마 변경 동반) | Step 2 |
