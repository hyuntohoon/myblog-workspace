#!/usr/bin/env python3
"""FEAT-lyrics-best-of-promotion Step 3 — retroactive one-shot backfill (WRITES).

Re-selects the *current* parked ``ambiguous`` / ``review_required`` pool (snapshot at
run start), fetches fresh LRCLIB candidates and replays the worker's own live path —
``run_eval_batch`` → ``decide_match`` → ``promote_best`` → basis-aware invariant →
``should_replace`` guard → ``TrackLyricsWriter`` (per-row commit). This driver adds NO
decision or write logic of its own; everything that touches a row is the Step 2 code
already live in the worker, so the backfill writes exactly what the forward path would.

Safety / resumability:
  * a pre-run rollback snapshot of every pool row's ``track_lyrics`` state is written to
    ``tools/out/bestof_backfill_snapshot_pre.json`` before any write (parked rows carry
    no lyric bodies — the snapshot restores status + evidence + NULL lyric);
  * per-row commit inside ``run_eval_batch`` — an interrupt loses nothing committed;
  * re-running resumes naturally: promoted rows leave the pool selection, and
    still-parked rows rewritten this run are excluded from retry passes via
    ``updated_at >= run_start`` (transient LRCLIB skips keep their old ``updated_at``
    and are re-selected).

Usage:
    export DATABASE_URL='postgresql+psycopg://...'      # prod (SSM /myblog/backend)
    python tools/lyrics_bestof_backfill.py --limit 20    # sanity slice
    python tools/lyrics_bestof_backfill.py               # full pool
    python tools/lyrics_bestof_backfill.py --report-only # post-run counts, no writes

RFC: docs/rfcs/FEAT-lyrics-best-of-promotion.md (Step 3)
"""

import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "myblog_worker"))

from worker.clients.lrclib_client import LrclibClient  # noqa: E402
from worker.service.lyrics_eval_core import (  # noqa: E402
    PRIMARY_ARTIST_NAMES_LATERAL,
    new_metrics,
    run_eval_batch,
)
from worker.service.lyrics_reassessment_service import should_replace  # noqa: E402

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)

OUT_DIR = Path(__file__).resolve().parent / "out"
SNAPSHOT = OUT_DIR / "bestof_backfill_snapshot_pre.json"
REPORT = OUT_DIR / "bestof_backfill_report.json"

# Step 3 target: the parked pool only. NOT not_found (out of scope — nothing to choose)
# and NOT the widened best-of re-check arm (that is the reassessment job's rotation).
POOL_SQL = f"""
    SELECT t.id, t.title, t.duration_sec,
           primary_artists.artist_names                     AS artist_names,
           ARRAY_REMOVE(ARRAY_AGG(DISTINCT al.alias), NULL) AS aliases,
           tl.match_status                 AS existing_status,
           (tl.evidence ->> 'match_basis') AS existing_basis
    FROM track_lyrics tl
    JOIN tracks t         ON t.id = tl.track_id
    JOIN track_artists ta ON ta.track_id = t.id
    JOIN artists a        ON a.id = ta.artist_id
    LEFT JOIN LATERAL jsonb_array_elements_text(a.aliases) AS al(alias) ON true
{PRIMARY_ARTIST_NAMES_LATERAL}
    WHERE tl.match_status IN ('ambiguous', 'review_required')
      AND tl.updated_at < :run_start
    GROUP BY t.id, t.title, t.duration_sec,
             tl.match_status, (tl.evidence ->> 'match_basis'),
             primary_artists.artist_names
    ORDER BY t.id
"""

STATUS_COUNTS_SQL = """
    SELECT match_status, COALESCE(evidence->>'match_basis', '(none)') AS basis, COUNT(*)
    FROM track_lyrics
    GROUP BY match_status, basis
    ORDER BY match_status, basis
"""


def _rows_to_tracks(rows):
    return [
        {
            "id": r[0], "title": r[1], "duration_sec": r[2],
            "artist_names": list(r[3] or []), "aliases": list(r[4] or []),
            "existing_status": r[5], "existing_basis": r[6],
        }
        for r in rows
    ]


def fetch_pool(session, run_start, limit=None):
    sql = POOL_SQL + (f" LIMIT {int(limit)}" if limit else "")
    return _rows_to_tracks(session.execute(text(sql), {"run_start": run_start}).fetchall())


def status_counts(session):
    out = {}
    for status, basis, n in session.execute(text(STATUS_COUNTS_SQL)):
        out.setdefault(status, {})[basis] = n
    return out


def snapshot_pool(session, run_start):
    """Rollback snapshot: full track_lyrics state of every still-parked pool row."""
    rows = session.execute(text("""
        SELECT track_id, match_status, evidence, matcher_version,
               created_at, updated_at
        FROM track_lyrics
        WHERE match_status IN ('ambiguous', 'review_required')
    """)).fetchall()
    snap = {
        "run_start": str(run_start),
        "rows": [
            {
                "track_id": str(r[0]), "match_status": r[1], "evidence": r[2],
                "matcher_version": r[3], "created_at": str(r[4]), "updated_at": str(r[5]),
            }
            for r in rows
        ],
    }
    OUT_DIR.mkdir(exist_ok=True)
    SNAPSHOT.write_text(json.dumps(snap, ensure_ascii=False, default=str))
    logger.info("pre-run snapshot: %d parked rows -> %s", len(rows), SNAPSHOT)
    return len(rows)


def merge_metrics(total, m):
    for k, v in m.items():
        if isinstance(v, dict):
            sub = total.setdefault(k, {})
            for ck, cv in v.items():
                sub[ck] = sub.get(ck, 0) + cv
        else:
            total[k] = total.get(k, 0) + v
    return total


def run_backfill(session, args, run_start):
    pool = fetch_pool(session, run_start, limit=args.limit)
    pool_ids = {t["id"] for t in pool}  # retries target the run-start pool ONLY
    logger.info("pool selected at run start: %d rows (ambiguous/review_required)", len(pool))

    client = LrclibClient(max_connections=args.concurrency + 4)
    totals = new_metrics()
    started = time.time()
    try:
        todo = pool
        for pass_no in range(args.retry_passes + 1):
            if not todo:
                break
            if pass_no:
                logger.info("retry pass %d: %d rows untouched by earlier passes",
                            pass_no, len(todo))
            chunks = [todo[i:i + args.chunk_size] for i in range(0, len(todo), args.chunk_size)]
            for i, chunk in enumerate(chunks, 1):
                m = run_eval_batch(
                    session, chunk,
                    concurrency=args.concurrency,
                    time_budget_sec=args.chunk_budget_sec,
                    client=client,
                    should_write=should_replace,
                    log_prefix=f"Best-of backfill p{pass_no} chunk {i}/{len(chunks)}",
                )
                merge_metrics(totals, m)
                done = totals["evaluated"] + totals["guard_kept"]
                rate = done / max(time.time() - started, 1e-6)
                logger.info("progress: written=%d guard_kept=%d transient=%d (%.2f rows/s)",
                            totals["evaluated"], totals["guard_kept"],
                            totals["skipped_transient"], rate)
            # Rows still parked AND untouched (old updated_at) = transient/budget skips.
            # Restrict to the run-start pool so a --limit slice retries its own skips
            # instead of pulling the next N parked rows, and so rows parked mid-run by
            # other jobs are never swept in.
            todo = [t for t in fetch_pool(session, run_start) if t["id"] in pool_ids]
    finally:
        client.close()

    totals["unresolved_skips_after_retries"] = len(todo)
    totals["elapsed_min"] = round((time.time() - started) / 60, 1)
    return totals


def main():
    parser = argparse.ArgumentParser(description="best-of promotion retroactive backfill (WRITES)")
    parser.add_argument("--limit", type=int, default=None, help="cap pool (sanity slice)")
    parser.add_argument("--concurrency", type=int, default=40,
                        help="parallel LRCLIB fetches (probe ran clean at 40)")
    parser.add_argument("--chunk-size", type=int, default=200)
    parser.add_argument("--chunk-budget-sec", type=float, default=240.0)
    parser.add_argument("--retry-passes", type=int, default=2,
                        help="re-select untouched parked rows after the main sweep")
    parser.add_argument("--report-only", action="store_true",
                        help="print current status/basis counts, write nothing")
    args = parser.parse_args()

    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        logger.error("DATABASE_URL not set")
        sys.exit(1)

    engine = create_engine(db_url, future=True)
    session = sessionmaker(bind=engine)()
    try:
        if args.report_only:
            print(json.dumps(status_counts(session), indent=2))
            return

        run_start = session.execute(text("SELECT NOW()")).scalar_one()
        session.rollback()  # release the snapshot txn; eval core commits per row
        before = status_counts(session)
        session.rollback()
        snapshot_pool(session, run_start)
        session.rollback()

        totals = run_backfill(session, args, run_start)

        after = status_counts(session)
        report = {"run_start": str(run_start), "before": before, "after": after,
                  "metrics": totals}
        REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False))
        print(json.dumps(report, indent=2, ensure_ascii=False))
    finally:
        session.close()
        engine.dispose()


if __name__ == "__main__":
    main()
