-- BUG-15 Step 5 (RFC §Step 5) — surname-token gate mini-reset
-- 2026-05-29
--
-- 대상: PR #134 측정 표본 라벨링에서 surname-token gate 가 의도적으로
-- 거절해야 할 likely false-match 3 spotify_id. Step 4 mini-reset 잔존
-- 1행 (Suh Young Eun) + 측정 표본 라벨링 2행 (Lil Moshpit / Dragon Pony).
--
-- 잔존 false-match:
--   Suh Young Eun (1uQ8BQhLtGMfK8PS3UAdNX)    → "Young Eun Lee" (Step 4 잔존)
--   Lil Moshpit   (0tVSrjQ0NpDlecsJwGmrMy)    → "이휘민" (Suh Young Eun 동일 패턴)
--   Dragon Pony   (2aRhzujDfJ1mVe2XdddXYL)    → "Vylet Pony" (영문 alias 만, surname 무신호)
--
-- IU&Kim Yuna 는 콜라보 매칭 별도 이슈로 본 reset 미포함 (RFC §Non-goals).
--
-- 효과: musicbrainz_id NULL 화 → 다음 EventBridge 사이클에서 Step 5
-- surname-gate 적용된 cross-check 가 재lookup. surname-token substring
-- 매치 안 되는 후보는 거절, sentinel 'not_found' 또는 surname-matched
-- 신규 MBID 로 전환.
--
-- Pre-execution gate: Step 5 worker deploy + EventBridge 1 사이클 관찰 +
-- CloudWatch "MB surname-gate reject" 발화 확인 후에만 실행. 단 prod
-- Lambda LOG_LEVEL=WARNING 이면 INFO 안 잡힘 — DB 증거로 우회
-- ([[reference-prod-lambda-loglevel]]).
--
-- 사전 SELECT 결과는 백업으로 캡쳐. Rollback 시 (musicbrainz_id, aliases)
-- 원본 UPDATE 복구.

\set ON_ERROR_STOP on

BEGIN;

-- 사전 백업 (현재 musicbrainz_id, aliases 상태 캡처 — 결과를 별도 파일/CSV 저장)
SELECT spotify_id, name, musicbrainz_id, aliases
  FROM artists
 WHERE spotify_id IN (
   '1uQ8BQhLtGMfK8PS3UAdNX',  -- Suh Young Eun
   '0tVSrjQ0NpDlecsJwGmrMy',  -- Lil Moshpit
   '2aRhzujDfJ1mVe2XdddXYL'   -- Dragon Pony
 )
 ORDER BY spotify_id;

-- 영향 행 카운트 (3 예상)
SELECT count(*) AS rows_to_reset
  FROM artists
 WHERE spotify_id IN (
   '1uQ8BQhLtGMfK8PS3UAdNX',
   '0tVSrjQ0NpDlecsJwGmrMy',
   '2aRhzujDfJ1mVe2XdddXYL'
 )
   AND musicbrainz_id IS NOT NULL
   AND musicbrainz_id != 'not_found';

UPDATE artists
   SET musicbrainz_id = NULL,
       aliases        = '[]'::jsonb
 WHERE spotify_id IN (
   '1uQ8BQhLtGMfK8PS3UAdNX',
   '0tVSrjQ0NpDlecsJwGmrMy',
   '2aRhzujDfJ1mVe2XdddXYL'
 )
   AND musicbrainz_id IS NOT NULL
   AND musicbrainz_id != 'not_found';

-- 사후 확인 (모두 musicbrainz_id NULL, aliases [] 인지)
SELECT spotify_id, name, musicbrainz_id, aliases
  FROM artists
 WHERE spotify_id IN (
   '1uQ8BQhLtGMfK8PS3UAdNX',
   '0tVSrjQ0NpDlecsJwGmrMy',
   '2aRhzujDfJ1mVe2XdddXYL'
 )
 ORDER BY spotify_id;

COMMIT;
