#!/usr/bin/env python3
"""
FEAT-lyrics-corpus Step 2 — Phase 2: local LRCLIB dump batch (offline backfill).

Iterates catalog tracks against the local LRCLIB SQLite dump (~28.6 GiB), via
the canonical matcher (worker.service.lyrics_matcher.LRCLIBDumpMatcher), and
writes outcomes to `track_lyrics`. Runs locally only (dump size is unfit for
Lambda). RFC: docs/rfcs/FEAT-lyrics-corpus.md.

NOT run in the Phase 1 session — gated by rule #4 (one RFC step / prod-observe
gate). This file is kept correct against the matcher signature + honest metrics
so it is ready when Phase 1 audit passes.

Usage:
    # 1. download the dump once (~28.6 GiB):
    curl -L https://lrclib.net/lrclib.db -o /tmp/lrclib.db

    # 2. dry-run (no DB writes) — inspect metrics:
    export DATABASE_URL='postgresql+psycopg://...'
    python tools/lyrics_batch_dump.py --lrclib-db /tmp/lrclib.db --limit 500

    # 3. full run (writes to track_lyrics) only after the gate passes:
    python tools/lyrics_batch_dump.py --lrclib-db /tmp/lrclib.db --full-run
"""

import argparse
import logging
import os
import sys
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "myblog_worker"))

from worker.service.lyrics_eval_core import PRIMARY_ARTIST_NAMES_LATERAL  # noqa: E402
from worker.service.lyrics_matcher import (  # noqa: E402
    LRCLIBDumpMatcher,
    TrackLyricsWriter,
)

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def fetch_catalog_tracks(session):
    """All catalog tracks with artist names + aliases (deterministic order)."""
    return session.execute(
        text(
            f"""
            SELECT t.id, t.title, t.duration_sec,
                   primary_artists.artist_names                      AS artist_names,
                   ARRAY_REMOVE(ARRAY_AGG(DISTINCT al.alias), NULL) AS aliases
            FROM tracks t
            JOIN track_artists ta ON ta.track_id = t.id
            JOIN artists a        ON a.id = ta.artist_id
            LEFT JOIN LATERAL jsonb_array_elements_text(a.aliases) AS al(alias) ON true
{PRIMARY_ARTIST_NAMES_LATERAL}
            GROUP BY t.id, t.title, t.duration_sec, primary_artists.artist_names
            ORDER BY t.id
            """
        )
    ).fetchall()


class Metrics:
    """Honest RFC metrics (denominators explicit). Precision is NOT matched/total."""

    def __init__(self):
        self.total = 0
        self.matched = 0
        self.no_lyrics = 0
        self.not_found = 0
        self.ambiguous = 0
        self.review_required = 0
        self.version_conflicts_parked = 0
        self.inconsistent_matched = 0

    def record(self, outcome):
        self.total += 1
        if outcome.match_status == "matched":
            self.matched += 1
            if outcome.version_agrees is False:
                self.inconsistent_matched += 1
        elif outcome.match_status == "no_lyrics":
            self.no_lyrics += 1
        elif outcome.match_status == "not_found":
            self.not_found += 1
        elif outcome.match_status == "ambiguous":
            self.ambiguous += 1
        elif outcome.match_status == "review_required":
            self.review_required += 1
            if outcome.evidence.get("reason") == "version_token_mismatch":
                self.version_conflicts_parked += 1

    def report(self) -> dict:
        t = self.total or 1
        m = {
            "total_evaluated": self.total,
            "matched": self.matched,
            "no_lyrics": self.no_lyrics,
            "not_found": self.not_found,
            "ambiguous": self.ambiguous,
            "review_required": self.review_required,
            # coverage, NOT precision — reported, never maximized at precision's expense
            "coverage": round((self.matched + self.no_lyrics) / t, 4),
            "review_required_rate": round(self.review_required / t, 4),
            "ambiguous_rate": round(self.ambiguous / t, 4),
            "version_conflicts_detected_and_parked": self.version_conflicts_parked,
            # consistency gate: by construction matched rows have version_agrees=True.
            # any inconsistent matched row means a matcher bug.
            "inconsistent_matched": self.inconsistent_matched,
            "consistency_gate_pass": self.inconsistent_matched == 0,
            # precision is owner-audited on a labelled slice (denom = matched)
            "precision_note": "audit a labelled slice of matched; denom = matched count",
        }
        logger.info("=" * 70)
        logger.info("BATCH METRICS (N=%d)", self.total)
        logger.info("  matched        : %d", m["matched"])
        logger.info("  no_lyrics      : %d", m["no_lyrics"])
        logger.info("  not_found      : %d", m["not_found"])
        logger.info("  ambiguous      : %d", m["ambiguous"])
        logger.info("  review_required: %d", m["review_required"])
        logger.info("  coverage (matched+no_lyrics)/total : %.1f%%", m["coverage"] * 100)
        logger.info("  version-conflicts detected & parked : %d", m["version_conflicts_detected_and_parked"])
        logger.info("  inconsistent matched (matcher bug)   : %d", m["inconsistent_matched"])
        logger.info("  CONSISTENCY GATE: %s", "PASS" if m["consistency_gate_pass"] else "FAIL")
        logger.info("  PRECISION: %s", m["precision_note"])
        logger.info("=" * 70)
        return m


def main():
    parser = argparse.ArgumentParser(description="FEAT-lyrics-corpus Step 2 Phase 2 (local dump batch)")
    parser.add_argument("--lrclib-db", required=True, help="path to LRCLIB SQLite dump")
    parser.add_argument("--batch-size", type=int, default=100)
    parser.add_argument("--limit", type=int, default=None, help="cap tracks (for a dry-run slice)")
    parser.add_argument("--dry-run", action="store_true", help="no DB writes (default)")
    parser.add_argument("--full-run", action="store_true", help="write outcomes to track_lyrics")
    args = parser.parse_args()

    if not os.path.exists(args.lrclib_db):
        logger.error("LRCLIB dump not found: %s (download from https://lrclib.net/lrclib.db)", args.lrclib_db)
        sys.exit(1)
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        logger.error("DATABASE_URL not set")
        sys.exit(1)

    engine = create_engine(db_url, future=True)
    session = sessionmaker(bind=engine)()
    # Constructs the connection + runs the PRAGMA schema self-check (raises on drift).
    matcher = LRCLIBDumpMatcher(args.lrclib_db)
    metrics = Metrics()
    outcomes = []

    try:
        logger.info("PHASE 2: local dump batch (lrclib: %s) mode=%s",
                    args.lrclib_db, "FULL-RUN" if args.full_run else "DRY-RUN")
        tracks = fetch_catalog_tracks(session)
        if args.limit:
            tracks = tracks[: args.limit]
        logger.info("evaluating %d catalog tracks", len(tracks))

        for i, row in enumerate(tracks):
            track_id, title, duration_sec, artist_names, aliases = row
            if (i + 1) % 500 == 0:
                logger.info("progress: %d/%d", i + 1, len(tracks))
            outcome = matcher.match_track(
                track_id=track_id,
                title=title,
                artist_names=artist_names or [],
                duration_sec=duration_sec or 0,
                aliases=aliases or [],
            )
            metrics.record(outcome)
            outcomes.append(outcome)

        summary = metrics.report()

        if args.full_run:
            if not summary["consistency_gate_pass"]:
                logger.error("consistency gate failed — not writing to DB; fix the matcher first")
                sys.exit(1)
            logger.info("writing %d outcomes to track_lyrics...", len(outcomes))
            written = TrackLyricsWriter(session).write_outcomes(outcomes, batch_size=args.batch_size)
            logger.info("wrote %d track_lyrics records", written)
        else:
            logger.info("DRY-RUN: outcomes not written to DB")
    finally:
        matcher.close()
        session.close()


if __name__ == "__main__":
    main()
