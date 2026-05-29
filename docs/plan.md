# Plan

Active workspace tracker for cross-repo work. Each row carries `Scope / Order (if multi-repo) / Verification (local + prod smoke) / Rollback / Status`; RFC-backed entries collapse to a one-line pointer at `docs/rfcs/<id>-<slug>.md`. When a row finishes, drop it — `git log` and `docs/archive/done/YYYY-MM.md` are authoritative for history.

---

## Active

### BUG-15 follow-up: Korean hint widening + Step 2 reset — P1 ⚠ 긴급

- RFC: `docs/rfcs/BUG-15-mb-false-match-cross-check.md` (Status: accepted)
- 트리거: BUG-18 Step 1 prod smoke (2026-05-29 01:06 UTC) 에서 stuck 3행이 sentinel 이 아닌 **또 다른 false-match MBID 로 교체**됨이 확인됨. 한국 아티스트의 `genres` 가 ko-KR localized (`"한국 랩"` / `"케이팝"` / `"k-발라드"` 등) 라 BUG-15 의 `_COUNTRY_HINTS` 영문 needle 이 안 잡힘. Step 1 의 pre-check 가 UNIQUE collision 가드 (= "false-match 같은 MBID 누적" 방어막) 를 우회시킨 부작용으로 **데이터 정확성 악화 + false-match 누적 가속화**.
- Scope:
  - **PR-A** (`myblog_worker`): `_COUNTRY_HINTS` 에 한국어 needle 3개 추가 (`"한국"` → KR / `"케이팝"` → KR / `"k-발라드"` → KR — prod artists.genres 빈도 분석 기반: 한국 랩 253, K-발라드 91, 케이팝 49, 한국 록 35 = 428행 영향).
  - **PR-B** (prod DB reset, **사용자 명시 OK 필요**): BUG-15 RFC Step 2. K* genres 행 중 musicbrainz_id NOT NULL && != 'not_found' 인 행을 NULL 로 reset (PR-A 머지 + 1 사이클 prod 동작 확인 후). 사전 SELECT 표본 점검 의무.
- Sequencing: PR-A → 1 사이클 prod 관찰 (한국어 토큰 → cross-check reject 로그) → PR-B.
- Verification: PR-A 는 worker pytest + 새 단위 케이스. PR-B 는 사전 SELECT 캡처 + UPDATE + 다음 사이클 후 재SELECT.
- Rollback: PR-A revert. PR-B 는 reset 전 SELECT 캡처본으로 UPDATE 복구.
- Status: 🟡 PR-A 시작

### BUG-18 Step 1: alias_fill fetch 단 MBID pre-check callback — 종료 대기 (PR-1 prod smoke 통과)

- RFC: `docs/rfcs/BUG-18-mbid-uniqueness-pre-check.md` (Status: accepted)
- Prod smoke 결과 (2026-05-29 01:06 UTC):
  - ✅ WARNING 0건 (이전 사이클 3-9건 → 0)
  - ✅ Duration 22.6초 (이전 51-64초 절반, `get_artist_by_id` 호출 절약)
  - ✅ 사이클당 진척 20행 (NULL 549→529, sentinel 54→56, 차이 18행은 진짜 MBID)
  - ⚠ 단, 박힌 MBID 가 또 다른 false-match (위 BUG-15 follow-up 영역)
- Status: 🟢 Step 1 기술 목표 달성. plan row drop 은 BUG-15 follow-up PR-A 와 묶어 처리.

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
