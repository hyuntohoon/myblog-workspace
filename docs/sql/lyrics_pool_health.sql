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
--
-- 2026-08-16 correction. Queries 2 and 6 were both written against the PRE-Step-3b world and
-- silently went wrong when 3b shipped (worker #93, 2026-08-03). Both are fixed below; read
-- their own comments for the mechanism. The headline symptom was that query 2 reported
-- `net_per_day = -61.7` — a draining pool — on a day the pool had demonstrably GROWN, from
-- 11,033 rows (recorded 2026-08-03 in `lyrics_reassessment_service._fetch_unresolved_tracks`'s
-- docstring) to 11,928, i.e. **+68.8/day**. The sign was inverted, not merely the magnitude.
-- Treat any net-pool figure quoted between 2026-08-03 and 2026-08-16 as unusable.

\echo '== 1. pool composition (excluded rows are parked, not drained) =='
SELECT match_status,
       (evidence ? 'excluded_by')                                    AS excluded,
       count(*)                                                      AS rows
FROM track_lyrics
GROUP BY 1, 2
ORDER BY 3 DESC;

\echo ''
\echo '== 2. net pool change per day, split by intent (see 2026-08-16 correction above) =='
-- The original `drained_per_day` counted EVERY matched/no_lyrics row whose `updated_at` moved
-- inside the window. Before Step 3b only a genuine promotion moved it, so that was sound.
-- Step 3b then added two writers that move `updated_at` on rows which were NEVER in the
-- unresolved pool:
--   * `TrackLyricsWriter.touch` bumps the rotation cursor on a best-of row the replacement
--     guard KEPT — content untouched. Pure cursor motion, zero drain. 33.4/day on 2026-08-16.
--   * a best-of SUPERSESSION rewrites `match_basis` best-of-* -> exact-title. Real work, but
--     the row was already `matched`; it never occupied a pool slot, so it is not drain either.
-- Both were being credited as pool drainage, which is how a growing pool reported net -61.7.
-- `bestof_touch_kept` is separable in SQL (basis still best-of-*). Supersessions are NOT
-- separable from current state alone — they now look identical to a genuine promotion — so
-- `non_bestof_drain` remains an UPPER BOUND on real drain until the best-of arm goes quiet.
-- The only trustworthy net figure while the sweep runs is query 3's `live_pool` differenced
-- against a previous run. Record it every time you run this file.
WITH win AS (SELECT INTERVAL '7 days' AS w)
SELECT
  round(count(*) FILTER (WHERE tl.created_at >= NOW() - win.w
                           AND tl.match_status IN ('not_found','ambiguous','review_required'))
        / 7.0, 1)                                                    AS entered_per_day,
  round(count(*) FILTER (WHERE tl.updated_at >= NOW() - win.w
                           AND tl.match_status IN ('matched','no_lyrics')
                           AND tl.updated_at > tl.created_at + INTERVAL '1 day')
        / 7.0, 1)                                                    AS moved_per_day_RAW,
  round(count(*) FILTER (WHERE tl.updated_at >= NOW() - win.w
                           AND tl.match_status = 'matched'
                           AND tl.evidence ->> 'match_basis' LIKE 'best-of-%'
                           AND tl.updated_at > tl.created_at + INTERVAL '1 day')
        / 7.0, 1)                                                    AS bestof_touch_kept,
  round(count(*) FILTER (WHERE tl.updated_at >= NOW() - win.w
                           AND tl.match_status IN ('matched','no_lyrics')
                           AND coalesce(tl.evidence ->> 'match_basis','') NOT LIKE 'best-of-%'
                           AND tl.updated_at > tl.created_at + INTERVAL '1 day')
        / 7.0, 1)                                                    AS drain_upper_bound
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
--
-- 2026-08-16: these tiers are currently NOT comparable to that flat baseline. They read
-- 13.66 / 30.55 / 58.31, and the gradient is an artifact of the same contamination query 2
-- documents — best-of rows sit overwhelmingly on older albums (tier 2), and the Step 3b sweep
-- is rewriting them right now, so tier 2's `promoted_30d` is counting supersessions rather
-- than pool promotions. Re-run this only after query 6 reports `arm_gone_quiet = t`; any
-- recency decision taken on these numbers before then is measuring the sweep, not recency.
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
\echo '== 6. best-of supersession backlog: how much is left, and when does the arm go quiet? =='
-- REWRITTEN 2026-08-16. The previous form computed `bestof_reachable := unresolved < 150`,
-- which was the correct test only while unresolved rows were ordered AHEAD of best-of rows.
-- Step 3b inverted that ordering — `_fetch_unresolved_tracks` now sorts
-- `CASE WHEN tl.match_status = 'matched' THEN 0 ELSE 1 END` first, so best-of rows are at the
-- HEAD of every batch. The old column therefore reported `f` (unreachable) while the arm was
-- demonstrably draining the backlog 2,765 -> 1,141. It was answering a question that stopped
-- existing, so it is replaced rather than patched.
--
-- What matters now is the opposite: the arm is reachable BY CONSTRUCTION, and the question is
-- when it finishes and hands the budget back to unresolved recovery. `bestof_due` is the part
-- actually selectable today (the 30-day rest interval, LYRICS_BESTOF_RECHECK_INTERVAL_DAYS,
-- holds the rest back); once `bestof_due` sits below the batch limit the arm has gone quiet
-- and unresolved rows start filling the remainder of each batch.
SELECT (SELECT count(*) FROM track_lyrics
          WHERE match_status = 'matched'
            AND evidence ->> 'match_basis' LIKE 'best-of-%'
            AND NOT (evidence ? 'excluded_by'))                   AS bestof_rows,
       (SELECT count(*) FROM track_lyrics
          WHERE match_status = 'matched'
            AND evidence ->> 'match_basis' LIKE 'best-of-%'
            AND NOT (evidence ? 'excluded_by')
            AND updated_at < NOW() - INTERVAL '30 days')          AS bestof_due,
       150                                                        AS batch_limit,
       (SELECT count(*) FROM track_lyrics
          WHERE match_status = 'matched'
            AND evidence ->> 'match_basis' LIKE 'best-of-%'
            AND NOT (evidence ? 'excluded_by')
            AND updated_at < NOW() - INTERVAL '30 days') < 150    AS arm_gone_quiet,
       (SELECT count(*) FROM track_lyrics
          WHERE match_status IN ('not_found','ambiguous','review_required')
            AND NOT (evidence ? 'excluded_by'))                   AS unresolved_behind;
