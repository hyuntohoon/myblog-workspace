#!/usr/bin/env python3
"""FEAT-lyrics-corpus Step 2 — Phase 2 (API variant): full-catalog LRCLIB backfill.

The ~30.7 GiB gzip LRCLIB dump (decompresses to ~90 GiB+) does not fit this
machine's free disk (~54 GiB), so Phase 2 runs the **same canonical matcher**
(`worker.service.lyrics_matcher.decide_match`) over the **full catalog** via the
LRCLIB `/api/search` endpoint instead of the local dump (owner decision
2026-07-01). The decision logic and the written outcomes are identical to the
dump batch — the dump would only have avoided per-request rate limits. Writes
`matched` / `no_lyrics` / `not_found` / `ambiguous` / `review_required` +
evidence to `track_lyrics` via the shared `TrackLyricsWriter` (per-row commit).

Resumable: a full run skips tracks that already have a `track_lyrics` row, so an
interrupted run is safe to re-launch. Transient LRCLIB errors (network / 5xx /
429) are retried, then the track is **skipped** (left unwritten for a later
resume) rather than poisoned as `not_found`.

RFC: docs/rfcs/FEAT-lyrics-corpus.md

Usage:
    export DATABASE_URL='postgresql+psycopg://...'          # prod (SSM /myblog/backend)
    # dry-run (no writes), 500-track slice — verify metrics + gate:
    python tools/lyrics_batch_api.py --limit 500
    # full run (writes; resumes past already-written rows):
    python tools/lyrics_batch_api.py --full-run
"""

import argparse
import logging
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "myblog_worker"))

from worker.service.lyrics_matcher import (  # noqa: E402
    STATUS_MATCHED,
    Candidate,
    TrackLyricsWriter,
    decide_match,
)

# Reuse the honest metrics (single source of the metric definitions + gate).
from lyrics_batch_dump import Metrics  # noqa: E402

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
# httpx logs one INFO line per request — silence it (20.9k requests would bury the run log).
logging.getLogger("httpx").setLevel(logging.WARNING)

LRCLIB_SEARCH = "https://lrclib.net/api/search"
DEFAULT_DELAY = 0.3  # polite: ~3 req/s over ~20.9k tracks; LRCLIB documents no hard limit
_RETRYABLE_STATUS = {429, 500, 502, 503, 504}


class TransientError(Exception):
    """LRCLIB was unreachable/erroring after retries — skip + resume, do NOT mark not_found."""


def fetch_catalog_tracks(session, limit=None, skip_existing=False):
    """Catalog tracks with artist names + aliases (deterministic order).

    ``skip_existing`` excludes tracks that already have a ``track_lyrics`` row so a
    full run resumes where a previous one stopped.
    """
    where = "WHERE tl.track_id IS NULL" if skip_existing else ""
    limit_clause = "LIMIT :lim" if limit else ""
    rows = session.execute(
        text(
            f"""
            SELECT t.id, t.title, t.duration_sec,
                   ARRAY_REMOVE(ARRAY_AGG(DISTINCT a.name), NULL)   AS artist_names,
                   ARRAY_REMOVE(ARRAY_AGG(DISTINCT al.alias), NULL) AS aliases
            FROM tracks t
            JOIN track_artists ta ON ta.track_id = t.id
            JOIN artists a        ON a.id = ta.artist_id
            LEFT JOIN LATERAL jsonb_array_elements_text(a.aliases) AS al(alias) ON true
            LEFT JOIN track_lyrics tl ON tl.track_id = t.id
            {where}
            GROUP BY t.id, t.title, t.duration_sec
            ORDER BY t.id
            {limit_clause}
            """
        ),
        {"lim": limit} if limit else {},
    ).fetchall()
    return rows


def search_candidates(client, title, artist, *, max_retries=3):
    """GET /api/search → list[Candidate]. Distinguishes 'no match' from 'transient error'.

    404 / empty list  -> legitimate no-match (decide_match parks it as not_found).
    network/5xx/429    -> retried with backoff, then raises TransientError (caller skips).
    """
    params = {"track_name": title, "artist_name": artist}
    last = None
    for attempt in range(max_retries):
        try:
            resp = client.get(LRCLIB_SEARCH, params=params)
            if resp.status_code == 404:
                return []
            if resp.status_code in _RETRYABLE_STATUS:
                last = f"HTTP {resp.status_code}"
                time.sleep(1.0 * (attempt + 1))
                continue
            resp.raise_for_status()
            data = resp.json()
            recs = data if isinstance(data, list) else []
            return [Candidate.from_api(r) for r in recs]
        except (httpx.TransportError, httpx.TimeoutException) as exc:
            last = repr(exc)
            time.sleep(1.0 * (attempt + 1))
            continue
        except httpx.HTTPError as exc:
            # non-retryable HTTP error (e.g. 4xx other than 404) — treat as transient-skip
            last = repr(exc)
            break
    raise TransientError(last or "unknown")


def main():
    parser = argparse.ArgumentParser(description="FEAT-lyrics-corpus Step 2 Phase 2 (LRCLIB API batch)")
    parser.add_argument("--limit", type=int, default=None, help="cap tracks (dry-run slice)")
    parser.add_argument("--dry-run", action="store_true", help="no DB writes (default)")
    parser.add_argument("--full-run", action="store_true", help="write outcomes to track_lyrics")
    parser.add_argument("--concurrency", type=int, default=10,
                        help="parallel LRCLIB fetch workers (throughput ~= concurrency / ~8s latency)")
    parser.add_argument("--delay", type=float, default=0.0,
                        help="extra per-fetch sleep (usually 0; concurrency self-throttles)")
    parser.add_argument("--flush-every", type=int, default=50, help="write buffer size (full-run)")
    parser.add_argument("--no-resume", action="store_true", help="re-evaluate ALL tracks (ignore existing rows)")
    args = parser.parse_args()

    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        logger.error("DATABASE_URL not set")
        sys.exit(1)

    # A full run resumes by default (skip already-written rows); dry-run always
    # takes a fresh slice so the metrics reflect the matcher, not what's left.
    skip_existing = args.full_run and not args.no_resume

    # Materialize the track list and release the read connection before the long
    # LRCLIB loop (idle Neon connections get dropped) — reference-db-session-across-long-external-loop.
    read_engine = create_engine(db_url, future=True)
    read_session = sessionmaker(bind=read_engine)()
    try:
        tracks = fetch_catalog_tracks(read_session, limit=args.limit, skip_existing=skip_existing)
    finally:
        read_session.close()
        read_engine.dispose()

    mode = "FULL-RUN" if args.full_run else "DRY-RUN"
    logger.info("PHASE 2 (API): mode=%s, tracks=%d, concurrency=%d, resume=%s",
                mode, len(tracks), args.concurrency, skip_existing)

    # Write session (full-run only) — kept alive by the periodic flush commits.
    write_engine = write_session = writer = None
    if args.full_run:
        write_engine = create_engine(db_url, future=True)
        write_session = sessionmaker(bind=write_engine)()
        writer = TrackLyricsWriter(write_session)

    limits = httpx.Limits(max_connections=args.concurrency + 2,
                          max_keepalive_connections=args.concurrency + 2)
    client = httpx.Client(timeout=20.0, limits=limits,
                          headers={"User-Agent": "myblog-lyrics-phase2/1.0 (private research)"})
    metrics = Metrics()
    buffer = []
    errors = 0
    started = time.time()

    def fetch_one(row):
        """Worker thread: only the slow LRCLIB fetch. No DB, no shared mutable state."""
        title, artist_names = row[1], list(row[3] or [])
        if args.delay:
            time.sleep(args.delay)
        try:
            return row, search_candidates(client, title, (artist_names or [""])[0]), None
        except TransientError as exc:
            return row, None, exc

    try:
        # ThreadPoolExecutor.map keeps ~concurrency fetches in flight and yields in
        # input order. decide_match + all DB writes stay on THIS (main) thread, so the
        # session is single-threaded and outcomes are written in a deterministic order.
        with ThreadPoolExecutor(max_workers=args.concurrency) as ex:
            for i, (row, candidates, exc) in enumerate(ex.map(fetch_one, tracks), 1):
                track_id, title, duration_sec, artist_names, aliases = row
                if exc is not None:
                    errors += 1
                    logger.warning("skip track %s (%r): LRCLIB transient error: %s", track_id, title, exc)
                    continue

                outcome = decide_match(
                    track_id=track_id,
                    title=title,
                    artist_names=list(artist_names or []),
                    aliases=list(aliases or []),
                    duration_sec=duration_sec,
                    candidates=candidates,
                )
                # Inline consistency gate: matched must always agree on version. A
                # violation is a matcher bug — abort rather than write a bad row.
                if outcome.match_status == STATUS_MATCHED and outcome.version_agrees is False:
                    raise SystemExit(f"CONSISTENCY VIOLATION on track {track_id}: matched but version_agrees=False")

                metrics.record(outcome)
                buffer.append(outcome)
                if writer and len(buffer) >= args.flush_every:
                    writer.write_outcomes(buffer, batch_size=args.flush_every)
                    buffer.clear()

                if i % 500 == 0:
                    rate = i / max(time.time() - started, 1e-6)
                    eta_min = (len(tracks) - i) / max(rate, 1e-6) / 60
                    logger.info("progress: %d/%d (skipped=%d) %.2f req/s ETA ~%.0f min",
                                i, len(tracks), errors, rate, eta_min)

        if writer and buffer:
            writer.write_outcomes(buffer, batch_size=args.flush_every)
    finally:
        client.close()
        if write_session is not None:
            write_session.close()
        if write_engine is not None:
            write_engine.dispose()

    summary = metrics.report()
    logger.info("transient-skipped tracks (unwritten, resume to retry): %d", errors)
    if not args.full_run:
        logger.info("DRY-RUN: outcomes not written to track_lyrics")
    if args.full_run and not summary["consistency_gate_pass"]:
        # Should be unreachable (guarded inline above), but keep the invariant loud.
        logger.error("consistency gate reported FAIL after a full run — investigate the matcher")
        sys.exit(1)


if __name__ == "__main__":
    main()
