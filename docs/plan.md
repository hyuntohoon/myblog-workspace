# Plan

Active workspace tracker for cross-repo work. Each row carries `Scope / Order (if multi-repo) / Verification (local + prod smoke) / Rollback / Status`; RFC-backed entries collapse to a one-line pointer at `docs/rfcs/<id>-<slug>.md`. When a row finishes, drop it — `git log` and `docs/archive/done/YYYY-MM.md` are authoritative for history.

---

## Active

### BUG-18 Step 1: alias_fill fetch 단 MBID pre-check callback — P2

- RFC: `docs/rfcs/BUG-18-mbid-uniqueness-pre-check.md` (Status: accepted — 2026-05-29 사용자 승격)
- Scope: `myblog_worker` 단독 (musicbrainz_client.py + sync_service.py + tests). cross-check 와 동일한 구조 — Step 1 단일 PR.
- Verification: `pytest tests/test_musicbrainz_client.py tests/test_sync_service.py tests/integration/test_alias_fill_session_lifecycle.py -v` + `ruff check worker/`. 통합 테스트는 `TEST_DB_URL` 미설정 시 skip ([[feedback-local-db-smoke-fallback]]).
- Prod smoke: post-merge EventBridge 1주기 (≈15 min). 절차는 RFC §Prod smoke. 전제로 `LOG_LEVEL=INFO` 임시 설정 후 원복.
- Rollback: PR revert. callback default `None` → 현행 동작. 데이터 mutation 없음.
- Status: 🟡 in progress

---

## Backlog

### FEAT-write-ux-bundle PR-2: 앨범 상세 확장 (D) — P2

- 트리거: PR-1 완료 후 (2026-05-29 완료) — 사용자 진행 OK 받으면 시작
- Scope: `myblog_music` (TrackOut 에 duration_sec/feat_artist_names, AlbumOut 에 label/release_country — Spotify 응답 있을 경우) + `myblog_front` (트랙 행 `mm:ss` + 피처링; 앨범 메타)
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
