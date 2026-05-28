# Plan

Active workspace tracker for cross-repo work. Each row carries `Scope / Order (if multi-repo) / Verification (local + prod smoke) / Rollback / Status`; RFC-backed entries collapse to a one-line pointer at `docs/rfcs/<id>-<slug>.md`. When a row finishes, drop it — `git log` and `docs/archive/done/YYYY-MM.md` are authoritative for history.

---

## Active

### FEAT-search-grid-fix: 검색 결과 그리드 수정 (카드 크기 불균일 + 가로 스크롤) — P0

- Scope: `myblog_front` (대부분) + 선조사 결과에 따라 `myblog_worker` (커버 인덱스)
- RFC: `docs/rfcs/FEAT-search-grid-fix.md`
- 묶음 근거: 2026-05-29 회의 v2. 스크린샷 진단으로 B(스크롤)+C(이미지 크기) 통합 1건 버그. 지금 바로 단독 PR.
- Sequencing: 선조사 30분 → CSS 1순위 (`aspect-ratio: 1; object-fit: cover` + 반응형 grid) → (조건부) 워커 커버 인덱스 고정
- Verification: dev server 검색 → 다건 결과 시각 확인 + 모바일 viewport
- Rollback: 단일 revert. CSS 변경 위주라 안전
- Status: 🟡 active (RFC draft 작성)

---

## Backlog

### FEAT-write-ux-bundle: 추천 트랙 UI + 앨범 상세 확장 — P2

- 트리거: FEAT-writer-cleanup 머지 완료 (2026-05-29). 진행 OK 받으면 시작
- Scope: 다음 묶음. F (추천 트랙 UI — 백엔드 완성, UI 만) + D (TrackOut 확장 — duration/피처링/label)
- Sequencing: PR-1 F → PR-2 D
- Status: ⚪ backlog

### CHORE-health-script: 운영 가시성 스크립트 — P3

- Scope: `scripts/health.sh` 에 aliases 빈배열 비율 + MBID_NOT_FOUND 비율 + post_metrics 신선도 SQL 추가
- Status: ⚪ backlog

### BUG-14: MusicBrainz search 가 한글 artist name 을 못 잡음 — P2

- Scope: `myblog_worker` (MB lookup) — 잠재적으로 `myblog_music` (검색 fallback)
- 증상: 예 — '아이유' / '조용히' 검색 시 MB API 가 NO RESULTS. canonical 영문 표기 ('IU' / 'Jo Yong-pil') 로만 hit.
- 추정 원인: MB 의 한국어 alias 인덱싱 빈약 + 현 lookup 이 query 그대로 보냄. canonical 영문/한국어 alias fallback 미구현.
- 영향: K-pop / 국내 artist 의 `musicbrainz_id` 채움률 저조 → alias_fill 잡이 'not_found' sentinel 만 채우는 경우 다수.
- 방향(미확정): (1) Spotify artist name 의 latinized alias 를 검색 키로 fallback, (2) MB `alias:` 검색 연산자 명시 사용, (3) 사내 한↔영 alias 매핑 테이블.
- Status: ⚪ backlog

### BUG-15: MusicBrainz search false-match — P2

- RFC: `docs/rfcs/BUG-15-mb-false-match-cross-check.md` (Status: accepted)

### BUG-16: tests/conftest.py 에 Neon test branch DB 비번 평문 — P3

- Scope: `myblog_worker` (`tests/conftest.py`)
- 증상: `TEST_DB_URL` env var 미설정 시 fallback default 에 Neon connection string (계정/비번 포함) 이 박혀있고 git 에 push 됨 (`conftest.py:14-17`).
- 추정 원인: 초기 통합테스트 셋업 시 편의 목적의 default fallback 을 그대로 남겨둠. Secrets Manager / GHA Secret 경로 미수립.
- 영향: Neon test branch 자체는 prod schema 와 분리지만 (a) 같은 organization 이라 lateral 공격 표면, (b) 향후 prod URL 도 같은 패턴으로 새어들 위험. test branch credential rotation 도 필요.
- 방향(미확정): (1) fallback default 제거 → env 미설정 시 `pytest.skip` collection-time, (2) Neon URL 을 AWS Secrets Manager + GHA secret 으로 옮기고 conftest 는 env 만 읽기, (3) test branch 비번 rotate.
- Status: ⚪ backlog

### BUG-17: alias_fill executemany 배치가 첫 UniqueViolation 에서 통째 롤백 — P1

- Scope: `myblog_worker` (`worker/service/sync_service.py:generate_and_save_aliases`)
- RFC: `docs/rfcs/BUG-17-alias-fill-batch-failure.md`
- 트리거: BUG-15 Step 1 post-merge verification (2026-05-28T16:07Z CloudWatch) 에서 발견. Kim Gwang-Jin → MBID `4b462375-...` (Kim Wilde UK) 충돌, 같은 MBID 가 이미 Kim Chang-Wan 에 박힘.
- 증상: MB lookup 한 행이 기존 MBID 와 충돌하면 `psycopg.errors.UniqueViolation`, `executemany` 배치 전체 (10행) 롤백. SELECT 가 같은 10행을 매 사이클 재공급 → 24h 95건 ERROR, alias_fill 진척 = 0.
- 영향: 데이터 부패는 UNIQUE (BUG-13) 가 막고 있어 user-facing 영향 없음. `musicbrainz_id NOT NULL` 행 13개에서 정체, alias_fill 사실상 정지. CloudWatch ERROR 노이즈.
- 방향: per-row UPDATE + `IntegrityError` 캐치 → 충돌행만 WARNING 흘리고 skip, 나머지 9행 persist. sentinel 강제 박지 않음.
- BUG-15 와 관계: 별 관심사. BUG-17 은 batch failure mode, BUG-15 는 false-match 방지. BUG-15 Step 2 (known-bad row reset) 는 BUG-17 머지 후 재개. BUG-15 `_COUNTRY_HINTS` 한국어 토큰 확장은 별도 follow-up (BUG-17 RFC Open Q1 참조).
- Status: 🟡 active (RFC draft 작성)

---

## Later (트리거 대기)

### FEAT-view-redesign: View 페이지 디자인 개편 — 트리거 대기

- 트리거: 사용자 디자인 예시(스크린샷/URL/Figma/손그림) 도착
- 즉시 실행 계획: `~/.claude/plans/soft-hatching-raccoon.md` "G. View 디자인" 절 (Phase 1~4)
- Status: 🔵 awaiting trigger

### CHORE-seo-audit: 블로그 read 경로 OG/sitemap/structured data 조사 — 의향 대기

- 트리거: 사용자 진행 OK
- Step 0 (조사 30분): `src/pages/blog/[slug].astro` + 메인 OG meta, sitemap.xml, JSON-LD 현황
- Step 1: 누락 있으면 `FEAT-seo-essentials` RFC; 의도된 상태면 닫기
- Status: 🔵 awaiting decision

---

## Frozen (아이디어만, RFC 없음)

확장 기능 후보. 의향 생기면 그때 RFC 시작. 지금 아무것도 안 함.

- **FEAT-spotify-personalize-light** (K) — 1인용 약식: OAuth 1회 → refresh token → Secrets → EventBridge 주기 fetch → `/api/music/recommendations/my-top` → write 사이드바
- **FEAT-new-release-feed** (L) — EventBridge 주기 → 본인 review artist 의 최근 앨범 fetch → `artist_new_releases` → `/api/music/feed/new-releases` → 메인 카드
