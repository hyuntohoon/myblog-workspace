-- BUG-15 Step 2 (RFC §Step 2) — known-bad row reset
-- 2026-05-29
--
-- 대상: artists.genres 에 한국어 토큰 ("한국 랩"/"한국 록"/"케이팝"/"K-발라드")
-- 이 있는 행 중 musicbrainz_id 가 NOT NULL && != 'not_found' 인 86행.
-- 이 행들은 BUG-15 cross-check 가 한국어 needle 없던 시절 false-match MBID
-- 가 박혔거나 (BUG-18 pre-check 가 가속화), 정상 매치이지만 idempotent reset
-- 으로 무해.
--
-- 효과:
--   1. NULL → Step 3 (Korean hint widening) 적용된 cross-check 재lookup
--   2. 옳은 한국 artist: KR country 후보 또는 country=null 후보 채택 (idempotent)
--   3. false-match: cross-check 거절 → sentinel 또는 진짜 KR 후보
--
-- 사전 SELECT 백업: /tmp/bug15-step2-reset-backup-<timestamp>.csv
-- (rollback 시 INSERT 또는 UPDATE 로 복구 — 본 스크립트의 트랜잭션 자체는
-- COMMIT 하므로 사후 rollback 은 별도 작업)

\set ON_ERROR_STOP on

BEGIN;

-- 영향 행 사전 확인 (트랜잭션 안에서 실행 → COMMIT 전 검증)
SELECT count(*) AS rows_to_reset
  FROM artists
 WHERE musicbrainz_id IS NOT NULL
   AND musicbrainz_id != 'not_found'
   AND EXISTS (
         SELECT 1 FROM jsonb_array_elements_text(genres) AS g(t)
          WHERE t LIKE '%한국%' OR t LIKE '%케이팝%' OR t ILIKE 'k-발라드%'
       );

-- Reset: musicbrainz_id → NULL, aliases → []
-- 다음 EventBridge 사이클이 Step 1 pre-check + Step 3 cross-check 적용해
-- 재lookup. NULL → NOT NULL 전환으로 NULL pool 에서 자연 evicted (BUG-18 §Goal).
UPDATE artists
   SET musicbrainz_id = NULL,
       aliases        = '[]'::jsonb
 WHERE musicbrainz_id IS NOT NULL
   AND musicbrainz_id != 'not_found'
   AND EXISTS (
         SELECT 1 FROM jsonb_array_elements_text(genres) AS g(t)
          WHERE t LIKE '%한국%' OR t LIKE '%케이팝%' OR t ILIKE 'k-발라드%'
       );

-- 사후 aggregate 확인
SELECT
  count(*) FILTER (WHERE musicbrainz_id IS NULL) AS null_rows,
  count(*) FILTER (WHERE musicbrainz_id = 'not_found') AS sentinel_rows,
  count(*) AS total_rows
  FROM artists;

COMMIT;
