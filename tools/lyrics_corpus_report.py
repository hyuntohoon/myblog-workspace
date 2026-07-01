#!/usr/bin/env python3
"""FEAT-lyrics-corpus Step 2 Phase 2 — post-run report + precision-audit sampler.

Read-only. Aggregates the six RFC metrics over the written ``track_lyrics`` corpus
(denominators explicit) and prints a random sample of ``matched`` rows with the
catalog title/artist vs the LRCLIB evidence (title/artist/duration) + a lyric
snippet, so the owner can audit auto-match precision (denom = matched count).

Usage:
    export DATABASE_URL='postgresql+psycopg://...'
    python tools/lyrics_corpus_report.py --audit 25
"""
import argparse
import os
import sys
from pathlib import Path

from sqlalchemy import create_engine, text

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "myblog_worker"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--audit", type=int, default=25, help="random matched rows to print for audit")
    ap.add_argument("--version-conflicts", action="store_true", help="also list review_required version_token_mismatch")
    args = ap.parse_args()

    e = create_engine(os.environ["DATABASE_URL"], future=True)
    with e.connect() as c:
        total_tracks = c.execute(text("SELECT COUNT(*) FROM tracks")).scalar()
        rows = dict(c.execute(text(
            "SELECT match_status, COUNT(*) FROM track_lyrics GROUP BY 1")).all())
        n = sum(rows.values())
        matched = rows.get("matched", 0)
        no_lyrics = rows.get("no_lyrics", 0)
        not_found = rows.get("not_found", 0)
        ambiguous = rows.get("ambiguous", 0)
        review = rows.get("review_required", 0)
        synced = c.execute(text(
            "SELECT COUNT(*) FROM track_lyrics WHERE match_status='matched' AND lyric_synced IS NOT NULL")).scalar()
        vconf = c.execute(text(
            "SELECT COUNT(*) FROM track_lyrics WHERE match_status='review_required' "
            "AND evidence->>'reason'='version_token_mismatch'")).scalar()
        # consistency invariant: no matched row may carry version_agrees=false
        inconsistent = c.execute(text(
            "SELECT COUNT(*) FROM track_lyrics WHERE match_status='matched' "
            "AND evidence->>'version_agrees'='false'")).scalar()

        d = n or 1
        print("=" * 68)
        print(f"CORPUS COVERAGE: {n}/{total_tracks} catalog tracks evaluated")
        print("-" * 68)
        print(f"  matched         : {matched:5d}  ({matched/d*100:4.1f}%)   synced available: {synced}")
        print(f"  no_lyrics       : {no_lyrics:5d}  ({no_lyrics/d*100:4.1f}%)")
        print(f"  not_found       : {not_found:5d}  ({not_found/d*100:4.1f}%)")
        print(f"  ambiguous       : {ambiguous:5d}  ({ambiguous/d*100:4.1f}%)")
        print(f"  review_required : {review:5d}  ({review/d*100:4.1f}%)")
        print("-" * 68)
        print(f"  auto-match coverage (matched/eval)        : {matched/d*100:.1f}%  (denom={n})")
        print(f"  resolved coverage ((matched+no_lyrics)/ev): {(matched+no_lyrics)/d*100:.1f}%")
        print(f"  review_required rate                      : {review/d*100:.1f}%  (denom={n})")
        print(f"  unresolved (not_found+no_lyrics)/eval      : {(not_found+no_lyrics)/d*100:.1f}%")
        print(f"  version-conflicts detected & parked        : {vconf}")
        print(f"  inconsistent matched (matcher bug -> must be 0): {inconsistent}")
        print(f"  CONSISTENCY GATE: {'PASS' if inconsistent == 0 else 'FAIL'}")
        print("  PRECISION: audit the sample below; denom = matched count")
        print("=" * 68)

        # precision-audit sample: random matched rows, catalog vs LRCLIB evidence
        print(f"\n--- MATCHED PRECISION AUDIT (random {args.audit}; denom=matched={matched}) ---")
        sample = c.execute(text("""
            SELECT tl.track_id, t.title AS cat_title, t.duration_sec AS cat_dur,
                   tl.evidence->>'lrclib_title'  AS lr_title,
                   tl.evidence->>'lrclib_artist' AS lr_artist,
                   tl.evidence->>'lrclib_duration_sec' AS lr_dur,
                   left(tl.lyric_plain, 90) AS snippet,
                   (SELECT string_agg(a.name, ', ') FROM track_artists ta
                      JOIN artists a ON a.id = ta.artist_id WHERE ta.track_id = tl.track_id) AS cat_artists
            FROM track_lyrics tl JOIN tracks t ON t.id = tl.track_id
            WHERE tl.match_status = 'matched'
            ORDER BY md5(tl.track_id::text || 'audit-seed')
            LIMIT :k
        """), {"k": args.audit}).all()
        for i, r in enumerate(sample, 1):
            dur_delta = ""
            try:
                dur_delta = f"Δ{abs(float(r.cat_dur) - float(r.lr_dur)):.0f}s"
            except (TypeError, ValueError):
                pass
            snip = (r.snippet or "").replace("\n", " / ")
            print(f"\n[{i:2d}] CATALOG : {r.cat_title!r} — {r.cat_artists}  ({r.cat_dur}s)")
            print(f"     LRCLIB  : {r.lr_title!r} — {r.lr_artist}  ({r.lr_dur}s) {dur_delta}")
            print(f"     lyric   : {snip}")

        if args.version_conflicts:
            print(f"\n--- VERSION-CONFLICT PARKS (review_required, sample) ---")
            vc = c.execute(text("""
                SELECT t.title, tl.evidence->>'lrclib_title' AS lr, tl.evidence->>'asymmetric_tokens' AS toks
                FROM track_lyrics tl JOIN tracks t ON t.id=tl.track_id
                WHERE tl.match_status='review_required'
                  AND tl.evidence->>'reason'='version_token_mismatch' LIMIT 15
            """)).all()
            for r in vc:
                print(f"  {r.title!r}  vs LRCLIB {r.lr!r}  tokens={r.toks}")
    e.dispose()


if __name__ == "__main__":
    main()
