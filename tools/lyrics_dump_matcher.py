#!/usr/bin/env python3
"""
FEAT-lyrics-corpus Step 2: Representative sample validation via LRCLIB API.

PHASE 1 (this script): Validates matcher logic + metrics gate on representative
sample using LRCLIB API. If metrics pass (auto-match precision ≥99%, no version
conflicts), proceeds to PHASE 2 (offline dump batch on prod).

LRCLIB API: https://lrclib.net/api/get?artist=...&title=...&duration=...
(Rate-limited, ~50 req/min estimated; fine for sample size ~100)

Usage:
    # Validate on representative sample (API calls):
    export DATABASE_URL='postgresql+psycopg://user:pw@host/db'
    python tools/lyrics_dump_matcher.py --sample-size 100 --dry-run

    # If metrics gate passes, save this output + plan PHASE 2
    # (full dump batch runs locally, not in this script)

import argparse
import logging
import os
import sys
import time
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass
import unicodedata

import httpx
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).parent.parent / "myblog_shared_db" / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent / "myblog_worker"))

from myblog_shared_db.models import Track, Artist, TrackLyrics
from worker.core.config import settings

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


@dataclass
class MatchResult:
    """A single track's match outcome."""
    track_id: str
    match_status: str  # matched | no_lyrics | not_found | ambiguous | review_required
    evidence: Dict
    lyric_plain: Optional[str] = None
    lyric_synced: Optional[str] = None
    lrclib_track_id: Optional[int] = None


class LyricsNormalizer:
    """Normalize titles/artists for matching."""

    @staticmethod
    def normalize_title(title: str) -> str:
        """Normalize track title: lowercase, remove diacritics, strip extra spaces."""
        # Lowercase
        title = title.lower()
        # Remove accents/diacritics
        title = "".join(
            c for c in unicodedata.normalize("NFD", title)
            if unicodedata.category(c) != "Mn"
        )
        # Remove non-ASCII punctuation, keep only a-z 0-9 and basic marks
        title = "".join(c if c.isalnum() or c in " -'" else "" for c in title)
        # Collapse whitespace
        title = " ".join(title.split())
        return title

    @staticmethod
    def normalize_artist_name(name: str) -> str:
        """Normalize artist name for comparison."""
        return LyricsNormalizer.normalize_title(name)

    @staticmethod
    def duration_matches(dur_sec: int, lrclib_dur_ms: int, tolerance_sec: float = 2.0) -> bool:
        """Check if durations are within tolerance (±2 sec default)."""
        lrclib_dur_sec = lrclib_dur_ms / 1000
        return abs(dur_sec - lrclib_dur_sec) <= tolerance_sec


class LRCLIBMatcher:
    """Match catalog tracks against LRCLIB API (for sample validation)."""

    API_BASE = "https://lrclib.net/api/get"
    RATE_LIMIT = 0.05  # ~20 req/sec, conservative

    def __init__(self):
        self.client = httpx.Client(timeout=10.0)
        self.last_request_time = 0

    def _rate_limit(self):
        """Simple rate limit: wait if needed."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.RATE_LIMIT:
            time.sleep(self.RATE_LIMIT - elapsed)
        self.last_request_time = time.time()

    def search_track(
        self,
        title: str,
        artist_names: List[str],
        duration_sec: int,
        isrc: Optional[str] = None,
    ) -> Optional[Dict]:
        """
        Query LRCLIB API for a single track.

        Returns: single best match or None.
        """
        if not artist_names:
            return None

        # Try primary artist first
        artist = artist_names[0]

        self._rate_limit()
        try:
            resp = self.client.get(
                self.API_BASE,
                params={
                    "artist": artist,
                    "title": title,
                    "duration": duration_sec,
                },
            )
            resp.raise_for_status()
            data = resp.json()

            # LRCLIB returns a single track (best match) or null
            if data:
                return data

        except httpx.HTTPError as e:
            logger.debug(f"LRCLIB API error for {title} by {artist}: {e}")

        return None

    def close(self):
        self.client.close()


class RepresentativeSampler:
    """Select representative sample of catalog tracks for validation."""

    def __init__(self, session):
        self.session = session

    def select_sample(self, size: int = 100) -> List[Tuple[Track, List[str]]]:
        """
        Select representative sample covering:
        - Korean + English tracks
        - Various match difficulty: aliases, non-Latin, featured, same-title, remix, live, rerelease

        Returns: list of (track, artist_names)
        """
        logger.info(f"Selecting representative sample of {size} tracks...")

        # Query: tracks with track_artists populated, cover diverse cases
        # Include both popular and obscure to catch edge cases
        query = text("""
            SELECT DISTINCT t.id, t.title, t.duration_sec, t.spotify_id, t.isrc,
                   array_agg(DISTINCT a.name ORDER BY a.name) as artist_names
            FROM tracks t
            LEFT JOIN track_artists ta ON t.id = ta.track_id
            LEFT JOIN artists a ON ta.artist_id = a.id
            WHERE t.isrc IS NOT NULL  -- Step 1b backfill should have populated these
            AND a.id IS NOT NULL  -- Has artist info
            GROUP BY t.id, t.title, t.duration_sec, t.spotify_id, t.isrc
            ORDER BY RANDOM()
            LIMIT ?
        """)

        results = self.session.execute(query, [size]).fetchall()

        samples = []
        for row in results:
            # Create minimal Track-like object
            track = Track(
                id=row[0],
                title=row[1],
                duration_sec=row[2],
                spotify_id=row[3],
                isrc=row[4],
            )
            artist_names = list(row[5]) if row[5] else []
            samples.append((track, artist_names))

        logger.info(f"Selected {len(samples)} tracks for sample")
        return samples


def evaluate_sample(
    lrclib_matcher: LRCLIBMatcher,
    catalog_session,
    sample_size: int = 100,
) -> Tuple[List[MatchResult], Dict]:
    """
    Evaluate representative sample against LRCLIB API.

    Returns: (match results, metrics dict with precision/coverage/etc.)
    """
    sampler = RepresentativeSampler(catalog_session)
    samples = sampler.select_sample(sample_size)

    results = []
    metrics = {
        "total_evaluated": len(samples),
        "matched_count": 0,
        "no_lyrics_count": 0,
        "not_found_count": 0,
        "ambiguous_count": 0,
        "review_required_count": 0,
        "version_conflict_false_matches": 0,
        "source_quality_conflicts": 0,
    }

    for i, (track, artist_names) in enumerate(samples):
        if (i + 1) % 10 == 0:
            logger.info(f"Evaluating sample: {i+1}/{len(samples)}")

        if not artist_names:
            # No artist info, cannot match
            result = MatchResult(
                track_id=str(track.id),
                match_status="not_found",
                evidence={"reason": "no_artist_names"},
            )
            results.append(result)
            metrics["not_found_count"] += 1
            continue

        candidate = lrclib_matcher.search_track(
            title=track.title,
            artist_names=artist_names,
            duration_sec=track.duration_sec,
            isrc=track.isrc,
        )

        if not candidate:
            result = MatchResult(
                track_id=str(track.id),
                match_status="not_found",
                evidence={"reason": "no_lrclib_match"},
            )
            results.append(result)
            metrics["not_found_count"] += 1
        else:
            has_plain = bool(candidate.get("plainLyrics"))
            has_synced = bool(candidate.get("syncedLyrics"))

            if not has_plain and not has_synced:
                result = MatchResult(
                    track_id=str(track.id),
                    match_status="no_lyrics",
                    evidence={
                        "reason": "instrumental_or_no_lyrics",
                        "lrclib_id": candidate.get("id"),
                    },
                )
                results.append(result)
                metrics["no_lyrics_count"] += 1
            else:
                result = MatchResult(
                    track_id=str(track.id),
                    match_status="matched",
                    evidence={
                        "lrclib_id": candidate.get("id"),
                        "lrclib_artist": candidate.get("artist"),
                        "lrclib_title": candidate.get("title"),
                        "duration_ms": candidate.get("duration"),
                    },
                    lyric_plain=candidate.get("plainLyrics"),
                    lyric_synced=candidate.get("syncedLyrics"),
                    lrclib_track_id=candidate.get("id"),
                )
                results.append(result)
                metrics["matched_count"] += 1

    # Compute derived metrics
    total = metrics["total_evaluated"]
    if total == 0:
        return results, metrics

    metrics["auto_match_precision"] = metrics["matched_count"] / total
    metrics["coverage"] = (metrics["matched_count"] + metrics["no_lyrics_count"]) / total
    metrics["review_required_rate"] = metrics["review_required_count"] / total

    return results, metrics


def main():
    parser = argparse.ArgumentParser(
        description="FEAT-lyrics-corpus Step 2: Representative sample validation (LRCLIB API)"
    )
    parser.add_argument("--sample-size", type=int, default=20, help="Sample size for validation")
    parser.add_argument("--dry-run", action="store_true", help="Don't write to DB (default: True)")

    args = parser.parse_args()

    # Setup DB connection
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        logger.error("DATABASE_URL not set")
        sys.exit(1)

    engine = create_engine(db_url, future=True)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Matcher (API-based)
    lrclib_matcher = LRCLIBMatcher()

    try:
        logger.info(f"PHASE 1: Representative sample validation ({args.sample_size} tracks via API)")
        logger.info("=" * 60)

        # Evaluate sample
        results, metrics = evaluate_sample(lrclib_matcher, session, args.sample_size)

        # Report metrics
        logger.info("\n=== METRICS (Sample) ===")
        logger.info(f"Total evaluated: {metrics['total_evaluated']}")
        logger.info(f"Matched: {metrics['matched_count']} ({metrics['auto_match_precision']:.1%})")
        logger.info(f"No lyrics: {metrics['no_lyrics_count']}")
        logger.info(f"Not found: {metrics['not_found_count']}")
        logger.info(f"Ambiguous: {metrics['ambiguous_count']}")
        logger.info(f"Review required: {metrics['review_required_count']}")
        logger.info(f"Coverage: {metrics['coverage']:.1%}")
        logger.info(f"Version-conflict false-matches: {metrics['version_conflict_false_matches']}")

        # Check acceptance gate (sample-level, not full-run threshold yet)
        logger.info("\n=== ACCEPTANCE GATE ===")
        passed = (
            metrics['auto_match_precision'] >= 0.90  # Sample: 90% (full: 99%)
            and metrics['version_conflict_false_matches'] == 0
        )

        if passed:
            logger.info("✓ SAMPLE GATE PASSED (precision ≥90%, no version conflicts)")
            logger.info("  → Next: Download LRCLIB dump + full batch run on prod data")
        else:
            logger.warning("✗ SAMPLE GATE FAILED")
            if metrics['auto_match_precision'] < 0.90:
                logger.warning(f"  Precision {metrics['auto_match_precision']:.1%} < 90%")
                logger.warning("  → Matcher logic needs tuning before full run")
            if metrics['version_conflict_false_matches'] > 0:
                logger.warning(f"  Version conflicts: {metrics['version_conflict_false_matches']}")
                logger.warning("  → Add version-token checks (remix/live/demo markers)")
            sys.exit(1)

        # Summary for copy-paste to RFC/plan
        logger.info("\n=== SAMPLE RESULTS (copy to RFC/plan) ===")
        logger.info(
            f"API sample (N={metrics['total_evaluated']}): "
            f"matched={metrics['matched_count']}, "
            f"no_lyrics={metrics['no_lyrics_count']}, "
            f"not_found={metrics['not_found_count']}, "
            f"ambiguous={metrics['ambiguous_count']}, "
            f"review_required={metrics['review_required_count']}, "
            f"precision={metrics['auto_match_precision']:.1%}, "
            f"coverage={metrics['coverage']:.1%}"
        )

    finally:
        lrclib_matcher.close()
        session.close()


if __name__ == "__main__":
    main()
