-- BUG-15 Step 4 (RFC §Step 4) — country=NULL pass-through tiebreaker mini-reset
-- 2026-05-29
--
-- 대상: Step 2 reset (2026-05-29 11:01 KST) +1h31m 시점 prod 표본에서
-- hint=KR + candidate.country=NULL pass-through 사각지대로 sticky false-match
-- 잔존이 확인된 6 spotify_id. Step 4 worker deploy + EventBridge 1 사이클
-- 관찰 후에만 실행 (CloudWatch "MB hangul-tiebreak reject" 발화 확인 선행).
--
-- 잔존 false-match (백업 CSV `/tmp/bug15-step2-reset-backup-20260529-105923.csv`):
--   V.I (0boGn8zBcxCZIT8N4wNpjD)            → "Shizzy Sixx" alias
--   JA$ (0QGm4hjuiDqfRorb2tewU1)            → "Jeffrey Atkins" (Ja Rule)
--   SUGA (0ebNdVaOfp6N0oZ1guIxM8)           → "Dajuan L. Walker"
--   Jimmy Paige (0lb59tIBwWrDfP6X956pkK)    → "J Kaleth"
--   Rocky L (0sVdt9nuNGEwrX3dPXRhwJ)        → "Kevin Hiatt"
--   Suh Young Eun (1uQ8BQhLtGMfK8PS3UAdNX)  → "Lee Youngeun"
--
-- 효과: musicbrainz_id NULL 화 → 다음 EventBridge 사이클에서 Step 4 hangul-tiebreak
-- 적용된 cross-check 가 재lookup. country=NULL + alias 한글 없음 후보는 거절,
-- sentinel 'not_found' 또는 한글 alias 보유 새 MBID 로 전환.
--
-- Rollback: 백업 CSV 의 (musicbrainz_id, aliases) 로 UPDATE 복구.

\set ON_ERROR_STOP on

BEGIN;

-- 사전 확인: 영향 행 6 (현재 musicbrainz_id NOT NULL 상태이어야 함)
SELECT count(*) AS rows_to_reset
  FROM artists
 WHERE spotify_id IN (
   '0boGn8zBcxCZIT8N4wNpjD',  -- V.I
   '0QGm4hjuiDqfRorb2tewU1',  -- JA$
   '0ebNdVaOfp6N0oZ1guIxM8',  -- SUGA
   '0lb59tIBwWrDfP6X956pkK',  -- Jimmy Paige
   '0sVdt9nuNGEwrX3dPXRhwJ',  -- Rocky L
   '1uQ8BQhLtGMfK8PS3UAdNX'   -- Suh Young Eun
 )
   AND musicbrainz_id IS NOT NULL
   AND musicbrainz_id != 'not_found';

UPDATE artists
   SET musicbrainz_id = NULL,
       aliases        = '[]'::jsonb
 WHERE spotify_id IN (
   '0boGn8zBcxCZIT8N4wNpjD',
   '0QGm4hjuiDqfRorb2tewU1',
   '0ebNdVaOfp6N0oZ1guIxM8',
   '0lb59tIBwWrDfP6X956pkK',
   '0sVdt9nuNGEwrX3dPXRhwJ',
   '1uQ8BQhLtGMfK8PS3UAdNX'
 )
   AND musicbrainz_id IS NOT NULL
   AND musicbrainz_id != 'not_found';

-- 사후 확인
SELECT spotify_id, name, musicbrainz_id, aliases
  FROM artists
 WHERE spotify_id IN (
   '0boGn8zBcxCZIT8N4wNpjD',
   '0QGm4hjuiDqfRorb2tewU1',
   '0ebNdVaOfp6N0oZ1guIxM8',
   '0lb59tIBwWrDfP6X956pkK',
   '0sVdt9nuNGEwrX3dPXRhwJ',
   '1uQ8BQhLtGMfK8PS3UAdNX'
 )
 ORDER BY spotify_id;

COMMIT;
