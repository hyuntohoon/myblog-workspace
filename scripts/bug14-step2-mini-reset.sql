-- BUG-14 Step 2 (RFC §Step 2) — hangul `not_found` mini-reset
-- 2026-05-30
--
-- 대상: prod `artists` 테이블에서 `musicbrainz_id = 'not_found'` AND `name ~ '[가-힣]'`
-- 인 sentinel 행 (Step 1 deploy 직전 측정 142행, RFC 시점 126행에서 +16). musicbrainz_id
-- 를 NULL 로 되돌려 EventBridge alias_fill (rate(15 min)) 이 다음 사이클부터 Step 1 의
-- query= 자유형 Lucene 으로 재lookup 하도록 한다. (sentinel 행은 재시도되지 않으므로
-- NULL 화 필수.)
--
-- 효과: alias union 으로 한글 name → MB hangul alias 인덱스 hit. 회복률 목표 ≥50%.
-- 미달 시 RFC Step 3 (잔존 분석) 트리거.
--
-- 전제 (실측 2026-05-30):
--   - Step 1 worker PR #29 머지 + auto deploy 성공 (test+deploy ✓, commit bb50bcb)
--   - 머지 시점 hangul NULL=0 → 자연 cycle 관찰 무의미 → 본 reset 으로 강제 lookup
--
-- 실행 전 timestamp 치환:
--   sed -i '' "s/YYYYMMDD-HHMMSS/$(date +%Y%m%d-%H%M%S)/g" scripts/bug14-step2-mini-reset.sql
--
-- 실행 (postgresql:// 형식, [[reference-database-url-psql]] 패턴, Neon cold-start
-- 대응 PGCONNECT_TIMEOUT=30):
--   DB_URL=$(aws secretsmanager get-secret-value --secret-id myblog/worker \
--     --query SecretString --output text \
--     | python3 -c "import sys,json; print(json.load(sys.stdin)['DATABASE_URL'])" \
--     | sed 's|postgresql+psycopg://|postgresql://|')
--   PGCONNECT_TIMEOUT=30 psql "$DB_URL" -f scripts/bug14-step2-mini-reset.sql
--
-- Rollback: 백업 CSV (`/tmp/bug14-step2-reset-backup-YYYYMMDD-HHMMSS.csv`) 의
-- (id, musicbrainz_id) 로 UPDATE 복구.

\set ON_ERROR_STOP on

BEGIN;

-- 사전 확인: 대상 행 수 (RFC 기준 ~126행)
SELECT count(*) AS rows_to_reset
  FROM artists
 WHERE musicbrainz_id = 'not_found'
   AND name ~ '[가-힣]';

-- 백업 (실행자 머신의 /tmp 에 저장됨, timestamp 사전 치환 필요)
\copy (SELECT id, spotify_id, name, musicbrainz_id, aliases FROM artists WHERE musicbrainz_id = 'not_found' AND name ~ '[가-힣]') TO '/tmp/bug14-step2-reset-backup-YYYYMMDD-HHMMSS.csv' CSV HEADER;

-- reset: sentinel → NULL (EventBridge alias_fill 은 NULL 만 처리)
UPDATE artists
   SET musicbrainz_id = NULL
 WHERE musicbrainz_id = 'not_found'
   AND name ~ '[가-힣]';

-- 사후 확인: NULL 화된 행 수 = pre-reset count, sentinel 남아있으면 0
SELECT
    SUM((musicbrainz_id IS NULL)::int) AS now_null,
    SUM((musicbrainz_id = 'not_found')::int) AS still_sentinel
  FROM artists
 WHERE name ~ '[가-힣]';

COMMIT;

-- ---------- 1-2 EventBridge 사이클 (15~30분) 후 회복률 측정 ----------
-- 별도 세션에서 실행 (트랜잭션 분리). PR comment / plan.md row 에 결과 인용.
--
-- SELECT
--   SUM((musicbrainz_id IS NULL)::int) AS still_null,
--   SUM((musicbrainz_id = 'not_found')::int) AS new_not_found,
--   SUM((musicbrainz_id IS NOT NULL AND musicbrainz_id <> 'not_found')::int) AS recovered
--   FROM artists WHERE name ~ '[가-힣]';
--
-- 목표:
--   recovered / (reset 행수) ≥ 50% → Step 2 성공, Step 3 (잔존 분석) 트리거
--   ≥ 80% → BUG-14 종료, plan 행 드롭
--   <50% → backlog 방향 (1) latinized fallback 또는 (3) 매핑 테이블 RFC
