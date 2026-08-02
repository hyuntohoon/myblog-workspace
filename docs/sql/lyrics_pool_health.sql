-- lyrics_pool_health.sql — DATA-catalog-noise-and-lyrics-coverage, Step 3 verification.
--
--   psql "$DATABASE_URL" -f docs/sql/lyrics_pool_health.sql
--
-- Read-only. The RFC's Step 3 Verification block has pointed at this path since the RFC was
-- written; the file itself did not exist until 2026-08-03, so every "net pool change" figure
-- quoted before that date was computed ad hoc. This is the canonical form of those queries.
--
-- Success metric (RFC §Step 3): net pool change <= 0/day, and daily promotions rising from
-- the 2.25/day baseline measured 2026-07-25.
--
-- Definitions used throughout:
--   * pool          = unresolved rows (not_found / ambiguous / review_required) that Step 3a's
--                     label-yield rule has NOT parked (`evidence ? 'excluded_by'`).
--   * promotion     = a row that left the pool for matched / no_lyrics on a RE-CHECK. The
--                     `updated_at > created_at + 1 day` guard is what separates a re-check
--                     promotion from an intake match; without it the intake collector's own
--                     hits inflate drain by an order of magnitude.
--   * excluded rows = parked by rule F, still present and reversible; NOT drained.

\echo '== 1. pool composition (excluded rows are parked, not drained) =='
SELECT match_status,
       (evidence ? 'excluded_by')                                    AS excluded,
       count(*)                                                      AS rows
FROM track_lyrics
GROUP BY 1, 2
ORDER BY 3 DESC;

\echo ''
\echo '== 2. net pool change per day (THE success metric: must reach <= 0) =='
WITH win AS (SELECT INTERVAL '7 days' AS w)
SELECT
  round(count(*) FILTER (WHERE tl.created_at >= NOW() - win.w
                           AND tl.match_status IN ('not_found','ambiguous','review_required'))
        / 7.0, 1)                                                    AS entered_per_day,
  round(count(*) FILTER (WHERE tl.updated_at >= NOW() - win.w
                           AND tl.match_status IN ('matched','no_lyrics')
                           AND tl.updated_at > tl.created_at + INTERVAL '1 day')
        / 7.0, 1)                                                    AS drained_per_day,
  round((count(*) FILTER (WHERE tl.created_at >= NOW() - win.w
                            AND tl.match_status IN ('not_found','ambiguous','review_required'))
       - count(*) FILTER (WHERE tl.updated_at >= NOW() - win.w
                            AND tl.match_status IN ('matched','no_lyrics')
                            AND tl.updated_at > tl.created_at + INTERVAL '1 day'))
        / 7.0, 1)                                                    AS net_per_day
FROM track_lyrics tl, win;

\echo ''
\echo '== 3. live pool size + how many days one full rotation takes at the batch limit =='
SELECT count(*)                                                      AS live_pool,
       150                                                           AS batch_limit_per_day,
       round(count(*) / 150.0, 1)                                    AS days_per_rotation
FROM track_lyrics
WHERE match_status IN ('not_found','ambiguous','review_required')
  AND NOT (evidence ? 'excluded_by');

\echo ''
\echo '== 4. yield per re-check, by album release recency (Step 3b premise) =='
-- The RFC proposed re-ordering the queue by release recency on a measured 32x signal
-- (26.7% for <=60d non-classical vs 0.8% raw pool, 2026-07-25). Re-run this after any
-- change to the pool: if the tiers are flat, recency carries no information and a
-- recency-tiered ORDER BY buys nothing. Measured flat on 2026-08-03 (see RFC Step 3b).
WITH tiered AS (
  SELECT tl.match_status, tl.created_at, tl.updated_at,
         CASE WHEN alb.release_date >= CURRENT_DATE - INTERVAL '60 days'  THEN '0: <=60d'
              WHEN alb.release_date >= CURRENT_DATE - INTERVAL '365 days' THEN '1: 60-365d'
              ELSE '2: rest' END                                     AS tier
  FROM track_lyrics tl
  JOIN tracks t         ON t.id = tl.track_id
  LEFT JOIN albums alb  ON alb.id = t.album_id
  WHERE NOT (tl.evidence ? 'excluded_by')
)
SELECT tier,
       count(*) FILTER (WHERE match_status IN ('matched','no_lyrics')
                          AND updated_at >= NOW() - INTERVAL '30 days'
                          AND updated_at > created_at + INTERVAL '1 day')    AS promoted_30d,
       count(*) FILTER (WHERE match_status IN ('not_found','ambiguous','review_required')
                          AND updated_at >= NOW() - INTERVAL '30 days'
                          AND updated_at > created_at + INTERVAL '1 day')    AS refreshed_30d,
       round(100.0 * count(*) FILTER (WHERE match_status IN ('matched','no_lyrics')
                                        AND updated_at >= NOW() - INTERVAL '30 days'
                                        AND updated_at > created_at + INTERVAL '1 day')
             / NULLIF(count(*) FILTER (WHERE updated_at >= NOW() - INTERVAL '30 days'
                                         AND updated_at > created_at + INTERVAL '1 day'), 0),
             2)                                                              AS yield_pct
FROM tiered
GROUP BY 1
ORDER BY 1;

\echo ''
\echo '== 5. Step 3a holdout: promotion rate IS the misclassification rate =='
-- Mirrors worker `holdout_audit()`. Compare holdout_promotion_pct against the pool's own
-- yield in query 4. Materially above it => rule F is parking rows that would have resolved.
WITH label_yield AS (
    SELECT al.label,
           count(*)                                            AS attempts,
           count(*) FILTER (WHERE tl.match_status = 'matched')  AS hits
    FROM track_lyrics tl
    JOIN tracks t  ON t.id = tl.track_id
    JOIN albums al ON al.id = t.album_id
    WHERE al.label IS NOT NULL
    GROUP BY al.label
), dead_labels AS (
    SELECT label FROM label_yield
    WHERE attempts >= 50 AND hits::float / attempts < 0.02
), scoped AS (
    SELECT tl.match_status,
           (tl.evidence ? 'excluded_by')                        AS excluded,
           left(md5(tl.track_id::text), 2) < '0d'               AS in_holdout
    FROM track_lyrics tl
    JOIN tracks t  ON t.id = tl.track_id
    JOIN albums al ON al.id = t.album_id
    WHERE al.label IN (SELECT label FROM dead_labels)
)
SELECT count(*) FILTER (WHERE excluded)                          AS excluded_rows,
       count(*) FILTER (WHERE in_holdout)                        AS holdout_rows,
       count(*) FILTER (WHERE in_holdout
                          AND match_status IN ('matched','no_lyrics')) AS holdout_promoted,
       round(100.0 * count(*) FILTER (WHERE in_holdout
                                        AND match_status IN ('matched','no_lyrics'))
             / NULLIF(count(*) FILTER (WHERE in_holdout), 0), 2)  AS holdout_promotion_pct
FROM scoped;

\echo ''
\echo '== 6. is the best-of supersession arm reachable? =='
-- `_fetch_unresolved_tracks` orders unresolved rows ahead of best-of-* matched rows, then
-- takes LIMIT 150. A best-of row is therefore selected only when unresolved < 150. If
-- unresolved_ahead exceeds the batch limit, the supersession path in `should_replace`
-- cannot execute at all — it is dead code in production, not merely rare.
SELECT (SELECT count(*) FROM track_lyrics
          WHERE match_status IN ('not_found','ambiguous','review_required')
            AND NOT (evidence ? 'excluded_by'))                   AS unresolved_ahead,
       (SELECT count(*) FROM track_lyrics
          WHERE match_status = 'matched'
            AND evidence ->> 'match_basis' LIKE 'best-of-%'
            AND NOT (evidence ? 'excluded_by'))                   AS bestof_rows,
       150                                                        AS batch_limit,
       (SELECT count(*) FROM track_lyrics
          WHERE match_status IN ('not_found','ambiguous','review_required')
            AND NOT (evidence ? 'excluded_by')) < 150             AS bestof_reachable;
