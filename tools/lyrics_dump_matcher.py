#!/usr/bin/env python3
"""
FEAT-lyrics-corpus Step 2 — Phase 1: representative-sample validator.

Validates the canonical conservative matcher (worker.service.lyrics_matcher)
against a random sample of REAL catalog tracks, using the LRCLIB **API**
(`/api/search`, returns up to 20 candidates so ambiguity is observable). This
is the cheap gate before Phase 2 (the ~28.6 GiB local dump batch).

What it does:
  - read a random sample of catalog tracks (with artists + aliases), read-only;
  - for each, fetch LRCLIB `/api/search` candidates and run `decide_match`;
  - write a per-track **audit JSON** (lyric snippet included) for manual
    correctness review;
  - print honest metrics (coverage / parked rates / version-conflicts-caught)
    and a consistency gate. Precision is NOT auto-claimed — the owner audits the
    `matched` set in the JSON (denominator = matched count).

Read-only. No `track_lyrics` writes. RFC: docs/rfcs/FEAT-lyrics-corpus.md.

Usage:
    export DATABASE_URL='postgresql+psycopg://user:pw@host/db'   # prod, read-only
    python tools/lyrics_dump_matcher.py --sample-size 50 \
        --out tools/.lyrics-phase1-sample.json
"""

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "myblog_worker"))

from worker.service.lyrics_matcher import (  # noqa: E402
    Candidate,
    decide_match,
)

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

LRCLIB_SEARCH = "https://lrclib.net/api/search"
REQUEST_DELAY = 0.2  # polite; LRCLIB documents no rate limit


def fetch_sample(session, size: int):
    """Random catalog tracks with artist names + aliases (read-only)."""
    rows = session.execute(
        text(
            """
            SELECT t.id, t.title, t.spotify_id, t.isrc, t.duration_sec,
                   ARRAY_REMOVE(ARRAY_AGG(DISTINCT a.name), NULL)     AS artist_names,
                   ARRAY_REMOVE(ARRAY_AGG(DISTINCT al.alias), NULL)  AS aliases
            FROM tracks t
            JOIN track_artists ta ON ta.track_id = t.id
            JOIN artists a        ON a.id = ta.artist_id
            LEFT JOIN LATERAL jsonb_array_elements_text(a.aliases) AS al(alias) ON true
            GROUP BY t.id, t.title, t.spotify_id, t.isrc, t.duration_sec
            ORDER BY RANDOM()
            LIMIT :n
            """
        ),
        {"n": size},
    ).fetchall()
    return [
        {
            "id": r[0], "title": r[1], "spotify_id": r[2], "isrc": r[3],
            "duration_sec": r[4], "artist_names": list(r[5] or []), "aliases": list(r[6] or []),
        }
        for r in rows
    ]


def search_lrclib(client: httpx.Client, title: str, artist: str):
    """GET /api/search?track_name=&artist_name= → list of LRCLIB records (may be empty)."""
    try:
        resp = client.get(LRCLIB_SEARCH, params={"track_name": title, "artist_name": artist})
        if resp.status_code == 404:
            return []
        resp.raise_for_status()
        data = resp.json()
        return data if isinstance(data, list) else []
    except httpx.HTTPError as exc:
        logger.debug("LRCLIB search error for %r by %r: %s", title, artist, exc)
        return []


def evaluate_track(client: httpx.Client, track) -> dict:
    candidates = [
        Candidate.from_api(rec)
        for rec in search_lrclib(client, track["title"], (track["artist_names"] or [""])[0])
    ]
    outcome = decide_match(
        track_id=track["id"],
        title=track["title"],
        artist_names=track["artist_names"],
        aliases=track["aliases"],
        duration_sec=track["duration_sec"],
        candidates=candidates,
    )
    snippet = None
    if outcome.lyric_plain:
        snippet = outcome.lyric_plain[:240]
    return {
        "spotify_id": track["spotify_id"],
        "title": track["title"],
        "artists": track["artist_names"],
        "aliases": track["aliases"],
        "isrc": track["isrc"],
        "duration_sec": track["duration_sec"],
        "status": outcome.match_status,
        "match_basis": outcome.match_basis,
        "version_tokens_track": outcome.version_tokens_track,
        "version_tokens_candidate": outcome.version_tokens_candidate,
        "version_agrees": outcome.version_agrees,
        "reason": outcome.evidence.get("reason"),
        "evidence": outcome.evidence,
        "plain_lyrics_snippet": snippet,
    }


def compute_metrics(rows: list) -> dict:
    total = len(rows)
    by_status = {}
    for r in rows:
        by_status[r["status"]] = by_status.get(r["status"], 0) + 1
    matched = by_status.get("matched", 0)
    no_lyrics = by_status.get("no_lyrics", 0)
    review = by_status.get("review_required", 0)
    ambiguous = by_status.get("ambiguous", 0)
    not_found = by_status.get("not_found", 0)
    version_conflicts_parked = sum(
        1 for r in rows
        if r["status"] == "review_required" and r["reason"] == "version_token_mismatch"
    )
    # Consistency gate: the matcher must never auto-attach something it flagged
    # inconsistent. By construction `matched` has version_agrees True and artist
    # identity passed; if any `matched` row violates that, the matcher is buggy.
    inconsistent_matched = sum(
        1 for r in rows if r["status"] == "matched" and r["version_agrees"] is False
    )
    return {
        "total_evaluated": total,
        "by_status": by_status,
        "matched": matched,
        "no_lyrics": no_lyrics,
        "not_found": not_found,
        "ambiguous": ambiguous,
        "review_required": review,
        "coverage": round((matched + no_lyrics) / total, 4) if total else 0,  # denom = total
        "review_required_rate": round(review / total, 4) if total else 0,
        "ambiguous_rate": round(ambiguous / total, 4) if total else 0,
        "version_conflicts_detected_and_parked": version_conflicts_parked,
        "inconsistent_matched": inconsistent_matched,
        "consistency_gate_pass": inconsistent_matched == 0,
        # precision: owner-audited from the `matched` rows below (denom = matched).
        "precision_note": "audit `matched` rows manually; denominator = matched count",
    }


def main():
    parser = argparse.ArgumentParser(description="FEAT-lyrics-corpus Step 2 Phase 1 validator")
    parser.add_argument("--sample-size", type=int, default=50)
    parser.add_argument("--out", default=str(Path(__file__).resolve().parent / ".lyrics-phase1-sample.json"))
    parser.add_argument("--delay", type=float, default=REQUEST_DELAY)
    args = parser.parse_args()

    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        logger.error("DATABASE_URL not set (read-only catalog connection)")
        sys.exit(1)

    engine = create_engine(db_url, future=True)
    client = httpx.Client(timeout=15.0, headers={"User-Agent": "myblog-lyrics-phase1/1.0"})

    logger.info("PHASE 1: representative sample validation (n=%d, LRCLIB /api/search)", args.sample_size)
    # Materialize the sample and release the DB connection immediately — the
    # LRCLIB loop below runs for minutes, and holding an idle Neon connection
    # open that long gets it dropped server-side (ProtocolViolation on close,
    # which would take down the whole run before metrics are written).
    session = sessionmaker(bind=engine)()
    try:
        sample = fetch_sample(session, args.sample_size)
    finally:
        session.close()
        engine.dispose()
    logger.info("sampled %d tracks", len(sample))

    rows = []
    try:
        for i, track in enumerate(sample, 1):
            rows.append(evaluate_track(client, track))
            if i % 10 == 0:
                logger.info("progress: %d/%d", i, len(sample))
            if args.delay:
                time.sleep(args.delay)
    finally:
        client.close()

    metrics = compute_metrics(rows)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sample_size": len(rows),
        "matcher_version": "step2-v2",
        "metrics": metrics,
        "tracks": rows,
    }
    out_path = Path(args.out)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    logger.info("wrote audit JSON -> %s", out_path)

    m = metrics
    logger.info("=" * 60)
    logger.info("METRICS (sample, N=%d)", m["total_evaluated"])
    logger.info("  matched        : %d", m["matched"])
    logger.info("  no_lyrics      : %d", m["no_lyrics"])
    logger.info("  not_found      : %d", m["not_found"])
    logger.info("  ambiguous      : %d", m["ambiguous"])
    logger.info("  review_required: %d", m["review_required"])
    logger.info("  coverage (matched+no_lyrics)/total : %.1f%%", m["coverage"] * 100)
    logger.info("  review_required_rate : %.1f%%", m["review_required_rate"] * 100)
    logger.info("  ambiguous_rate       : %.1f%%", m["ambiguous_rate"] * 100)
    logger.info("  version-conflicts detected & parked : %d", m["version_conflicts_detected_and_parked"])
    logger.info("-" * 60)
    gate = "PASS" if m["consistency_gate_pass"] else "FAIL"
    logger.info("CONSISTENCY GATE (no inconsistent matched): %s", gate)
    logger.info("PRECISION: %s", m["precision_note"])
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
