# Plan

Active workspace tracker for cross-repo work. Each row carries `Scope / Order (if multi-repo) / Verification (local + prod smoke) / Rollback / Status`; RFC-backed entries collapse to a one-line pointer at `docs/rfcs/<id>-<slug>.md`. When a row finishes, drop it — `git log` and `docs/archive/done/YYYY-MM.md` are authoritative for history.

---

## Active

### BUG-13: alias_fill UNIQUE violation on `musicbrainz_id='not_found'` — 🟡 active

- Scope: `myblog_worker` (+ `myblog_shared_db` if schema/index changes)
- 증상: EventBridge `worker-musicbrainz-alias-generation` 매 15분 tick → `psycopg.errors.UniqueViolation: Key (musicbrainz_id)=(not_found) already exists` → 트랜잭션 ROLLBACK. MB lookup 성공한 행의 aliases 도 같이 날아감.
- 원인: `generate_and_save_aliases` ([myblog_worker/worker/service/sync_service.py](../myblog_worker/worker/service/sync_service.py):286) 가 lookup 실패한 여러 행에 `musicbrainz_id='not_found'` sentinel 을 batch UPDATE 하는데, `idx_artists_musicbrainz_id` UNIQUE 제약과 충돌. 2026-05-27 (`089aab2 docs(schema): sync artists.musicbrainz_id`) 즈음 schema/index 정리되며 노출.
- Order: (1) sentinel 정책 결정 → (2) shared_db / worker 동시 PR 또는 schema-only → worker 순차.
- 결정 필요한 sentinel 옵션:
  - (a) UNIQUE 를 partial index 로 변경 (`WHERE musicbrainz_id <> 'not_found'`)
  - (b) sentinel 폐기 → `musicbrainz_id` NULL + 별도 `mb_lookup_attempted_at` 컬럼
  - (c) lookup 실패 행은 UPDATE 자체 skip, 재시도는 `last_attempted_at` 기준
- 사용자 영향: 신규 artist 의 alias 검색 hit 미증가 (silent rot). 기존 데이터/검색 영향 없음, 데이터 손상 없음 (ROLLBACK 덕).
- 우선순위: P2-P3 — immediate breakage 없으나 alias-fill 잡이 매 tick 무의미 ROLLBACK 으로 존재 의미 상실 + ERROR 로그 noise 누적.
- Verification: worker pytest + 다음 15분 tick 의 `/aws/lambda/blogWorkerLambda` 에 UniqueViolation 없음 + prod smoke (`scripts/smoke.sh`).
- Rollback: revert PR. schema 마이그레이션 동반 시 별도 down migration 동봉.
- Status: 🟡 active (분류만 완료, 구현 미착수)

---

## Backlog

_(none)_
