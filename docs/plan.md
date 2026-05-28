# Plan

Active workspace tracker for cross-repo work. Each row carries `Scope / Order (if multi-repo) / Verification (local + prod smoke) / Rollback / Status`; RFC-backed entries collapse to a one-line pointer at `docs/rfcs/<id>-<slug>.md`. When a row finishes, drop it — `git log` and `docs/archive/done/YYYY-MM.md` are authoritative for history.

---

## Active

### BUG-13: alias_fill UNIQUE violation on `musicbrainz_id='not_found'` — 🟡 active

- Scope: `myblog_shared_db` (schema) + `myblog_worker` (git-pin bump)
- 증상: EventBridge `worker-musicbrainz-alias-generation` 매 15분 tick → `psycopg.errors.UniqueViolation: Key (musicbrainz_id)=(not_found) already exists` → 트랜잭션 ROLLBACK. MB lookup 성공한 행의 aliases 도 같이 날아감.
- 원인: `generate_and_save_aliases` ([myblog_worker/worker/service/sync_service.py](../myblog_worker/worker/service/sync_service.py):286) 가 lookup 실패한 여러 행에 `musicbrainz_id='not_found'` sentinel 을 batch UPDATE 하는데, `idx_artists_musicbrainz_id` UNIQUE 제약과 충돌. 2026-05-27 (`089aab2 docs(schema): sync artists.musicbrainz_id`) 즈음 schema/index 정리되며 노출.
- 결정: **(a) 채택** — UNIQUE 를 partial index 로 좁혀 `musicbrainz_id IS NOT NULL AND musicbrainz_id <> 'not_found'` 행에만 적용. sentinel 정책/컬럼 추가 없이 schema 1줄 + worker 코드 0줄. (b)/(c) 는 코드 변경 폭이 크고 sentinel 의미를 바꿔야 해서 보류.
- Order: (1) `myblog_shared_db` V3 마이그레이션 PR — partial UNIQUE 로 교체 + canonical/generated schema 동기화 → (2) `myblog_worker` git-pin bump PR (코드 0줄).
- 우선순위: P1 — alias-fill 잡이 매 tick 무의미 ROLLBACK 으로 존재 의미 상실 + ERROR 로그 noise 누적. 데이터 손상은 없으나 silent rot.
- Verification: shared_db parity test 통과 + worker pytest + 다음 15분 tick 의 `/aws/lambda/blogWorkerLambda` 에 UniqueViolation 없음 + artists 테이블에 실제 `musicbrainz_id` 값이 박히는지 확인 + prod smoke (`scripts/smoke.sh`).
- Rollback: V3 down migration (DROP partial INDEX → 원래 full UNIQUE 재생성). worker PR 은 pin 되돌리기.
- Status: 🟡 active

---

## Backlog

### BUG-14: MusicBrainz search 가 한글 artist name 을 못 잡음 — P2

- Scope: `myblog_worker` (MB lookup) — 잠재적으로 `myblog_music` (검색 fallback)
- 증상: 예 — '아이유' / '조용히' 검색 시 MB API 가 NO RESULTS. canonical 영문 표기 ('IU' / 'Jo Yong-pil') 로만 hit.
- 추정 원인: MB 의 한국어 alias 인덱싱 빈약 + 현 lookup 이 query 그대로 보냄. canonical 영문/한국어 alias fallback 미구현.
- 영향: K-pop / 국내 artist 의 `musicbrainz_id` 채움률 저조 → alias_fill 잡이 'not_found' sentinel 만 채우는 경우 다수.
- 방향(미확정): (1) Spotify artist name 의 latinized alias 를 검색 키로 fallback, (2) MB `alias:` 검색 연산자 명시 사용, (3) 사내 한↔영 alias 매핑 테이블.
- Status: ⚪ backlog

### BUG-15: MusicBrainz search false-match (예: Big Bang → Big Country, score=100) — P2

- Scope: `myblog_worker` (MB scoring/filter)
- 증상: 'Big Bang' (K-pop) 검색 시 'Big Country' (GB rock band) 가 score=100 으로 first hit. 현 `_MIN_SCORE=90` 컷오프로는 못 거름.
- 추정 원인: MB score 가 name 토큰 매칭만으로 100 을 뱉음. country / disambiguation / type 가중치 미반영.
- 방향(미확정): (1) Spotify country/genre 와 cross-check (Spotify 가 KR/k-pop 인데 MB 후보가 GB rock → 거절), (2) MB `country:` / `tag:` 필터 추가, (3) disambiguation 텍스트로 secondary filter.
- 영향: 잘못된 `musicbrainz_id` 박힘 → alias_fill 로 엉뚱한 alias 채워짐 → 검색 품질 저하.
- Status: ⚪ backlog
