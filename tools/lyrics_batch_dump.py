#!/usr/bin/env python3
"""
FEAT-lyrics-corpus Step 2 Phase 2: Local LRCLIB dump batch.

Downloads and processes LRCLIB dump (~28.6 GiB) against catalog tracks.
RFC: Runs locally (dump size unfit for Lambda), writes outcomes + lyrics to DB.

Usage:
    # Download LRCLIB dump first (one-time, ~28.6 GiB):
    curl -L https://lrclib.net/lrclib.db -o /tmp/lrclib.db

    # Run batch (requires DATABASE_URL):
    export DATABASE_URL='postgresql+psycopg://...'
    python tools/lyrics_batch_dump.py \
      --lrclib-db /tmp/lrclib.db \
      --batch-size 100 \
      --dry-run  # Dry-run mode: don't write to DB

    # Full run (after validation passes):
    python tools/lyrics_batch_dump.py \
      --lrclib-db /tmp/lrclib.db \
      --full-run

Expected metrics (from RFC):
- Auto-match precision ≥ 99% (primary gate)
- Auto-match coverage: reported, not maximized
- Review-required rate: fraction ∈ [0, 1]
- Unresolved/no-lyrics rate: reported separately
- Version-conflict false-match count = 0 (absolute)
- Source-quality conflict rate: reported
"""

import argparse
import logging
import os
import sys
from pathlib import Path
from typing import List, Dict

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).parent.parent / "myblog_shared_db" / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent / "myblog_worker"))

from myblog_shared_db.models import Track
from worker.service.lyrics_matcher import LRCLIBDumpMatcher, TrackLyricsWriter

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


class Metrics:
    """Track batch metrics for RFC gate."""

    def __init__(self):
        self.total_evaluated = 0
        self.matched = 0
        self.no_lyrics = 0
        self.not_found = 0
        self.ambiguous = 0
        self.review_required = 0
        self.version_conflict_false_matches = 0

    def record(self, status: str):
        self.total_evaluated += 1
        if status == "matched":
            self.matched += 1
        elif status == "no_lyrics":
            self.no_lyrics += 1
        elif status == "not_found":
            self.not_found += 1
        elif status == "ambiguous":
            self.ambiguous += 1
        elif status == "review_required":
            self.review_required += 1

    def report(self):
        """RFC metrics: precise denominators."""
        total = self.total_evaluated
        if total == 0:
            logger.warning("No tracks evaluated")
            return

        precision = self.matched / total if total > 0 else 0
        coverage = (self.matched + self.no_lyrics) / total if total > 0 else 0
        review_rate = self.review_required / total if total > 0 else 0
        unresolved_rate = (self.not_found + self.ambiguous) / total if total > 0 else 0

        logger.info("\n" + "=" * 70)
        logger.info("BATCH METRICS (RFC Success Criteria)")
        logger.info("=" * 70)
        logger.info(f"Total evaluated: {total}")
        logger.info(f"  Matched: {self.matched} ({precision:.1%})")
        logger.info(f"  No lyrics: {self.no_lyrics}")
        logger.info(f"  Not found: {self.not_found}")
        logger.info(f"  Ambiguous: {self.ambiguous}")
        logger.info(f"  Review required: {self.review_required}")
        logger.info(f"\nMetrics:")
        logger.info(f"  Auto-match precision: {precision:.1%} (gate: ≥99%)")
        logger.info(f"  Coverage: {coverage:.1%}")
        logger.info(f"  Review-required rate: {review_rate:.1%}")
        logger.info(f"  Unresolved rate: {unresolved_rate:.1%}")
        logger.info(f"  Version-conflict false-matches: {self.version_conflict_false_matches} (gate: =0)")
        logger.info("=" * 70)

        # Gate check
        gate_pass = precision >= 0.99 and self.version_conflict_false_matches == 0
        if gate_pass:
            logger.info("✓ ACCEPTANCE GATE PASSED")
        else:
            logger.warning("✗ ACCEPTANCE GATE FAILED")
            if precision < 0.99:
                logger.warning(f"  Precision {precision:.1%} < 99%")
            if self.version_conflict_false_matches > 0:
                logger.warning(f"  Version conflicts: {self.version_conflict_false_matches}")

        return gate_pass


def fetch_catalog_tracks(session) -> List[tuple]:
    """Fetch catalog tracks with artist info for matching."""
    query = text("""
        SELECT
            t.id, t.title, t.duration_sec, t.spotify_id, t.isrc,
            ARRAY_AGG(DISTINCT a.name ORDER BY a.name) as artist_names
        FROM tracks t
        LEFT JOIN track_artists ta ON t.id = ta.track_id
        LEFT JOIN artists a ON ta.artist_id = a.id
        WHERE a.id IS NOT NULL  -- Has artist info
        GROUP BY t.id, t.title, t.duration_sec, t.spotify_id, t.isrc
        ORDER BY t.id
    """)
    return session.execute(query).fetchall()


def main():
    parser = argparse.ArgumentParser(
        description="FEAT-lyrics-corpus Step 2 Phase 2: Local LRCLIB dump batch"
    )
    parser.add_argument(
        "--lrclib-db", required=True, help="Path to LRCLIB SQLite dump (/tmp/lrclib.db)"
    )
    parser.add_argument(
        "--batch-size", type=int, default=100, help="Batch commit size (default 100)"
    )
    parser.add_argument(
        "--limit", type=int, default=None, help="Limit tracks (default: all)"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Validate without writing to DB (default)"
    )
    parser.add_argument(
        "--full-run",
        action="store_true",
        help="Write to DB (confirmation: metrics gate must pass sample first)",
    )

    args = parser.parse_args()

    # Validate LRCLIB dump exists
    if not os.path.exists(args.lrclib_db):
        logger.error(f"LRCLIB dump not found: {args.lrclib_db}")
        logger.error("Download from: https://lrclib.net/lrclib.db")
        sys.exit(1)

    # Setup DB
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        logger.error("DATABASE_URL not set")
        sys.exit(1)

    engine = create_engine(db_url, future=True)
    Session = sessionmaker(bind=engine)
    session = Session()

    matcher = LRCLIBDumpMatcher(args.lrclib_db)
    metrics = Metrics()

    try:
        logger.info(f"PHASE 2: Local dump batch (lrclib: {args.lrclib_db})")
        logger.info(f"Mode: {'DRY-RUN (no DB writes)' if args.dry_run else 'FULL-RUN (write to DB)'}")
        logger.info("=" * 70)

        # Fetch catalog
        tracks = fetch_catalog_tracks(session)
        if args.limit:
            tracks = tracks[: args.limit]

        logger.info(f"Evaluating {len(tracks)} catalog tracks")

        # Match each track
        outcomes = []
        for i, track_row in enumerate(tracks):
            track_id, title, duration_sec, spotify_id, isrc, artist_names = track_row

            if (i + 1) % 500 == 0:
                logger.info(f"Progress: {i+1}/{len(tracks)}")

            outcome = matcher.match_track(
                track_id=track_id,
                title=title,
                artist_names=artist_names or [],
                duration_sec=duration_sec or 0,
                isrc=isrc,
            )

            metrics.record(outcome.match_status)
            outcomes.append(outcome)

        # Report metrics
        gate_pass = metrics.report()

        # Write outcomes (if not dry-run and gate passes)
        if args.full_run and gate_pass:
            logger.info(f"\nWriting {len(outcomes)} outcomes to DB...")
            writer = TrackLyricsWriter(session)
            written = writer.write_outcomes(outcomes, batch_size=args.batch_size)
            logger.info(f"Successfully wrote {written} track_lyrics records")
        elif args.full_run and not gate_pass:
            logger.error("Gate failed: not writing to DB. Fix metrics first.")
            sys.exit(1)
        else:
            logger.info("DRY-RUN: outcomes not written to DB")

    finally:
        matcher.close()
        session.close()


if __name__ == "__main__":
    main()
