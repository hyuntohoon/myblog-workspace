#!/usr/bin/env python3
"""FEAT-lyrics-best-of-promotion Step 1 — risk-quantification probe (READ-ONLY).

Re-fetches LRCLIB candidates for the live prod ``ambiguous`` / ``review_required``
pool (stored ``evidence`` keeps only ≤3 candidate previews and no bodies, so a
DB-only probe is impossible), replays ``decide_match`` → ``promote_best`` (v1,
tier-1-only) and reports the RFC's five measures with explicit denominators:

  (a) tier-1 hit rate — the fraction v1 can promote at all
  (b) duration-gap distribution of the tier-1 pick
  (c) genuine two-song ambiguity vs duplicate-noise (heuristic, ambiguous rows)
  (d) review_required rows carrying a version-agreeing sibling (OQ5 class)
  (e) residual pool the gated tiers 2-4 *would* cover

Writes NOTHING to the DB. Per-track results append to a JSONL checkpoint so an
interrupted run resumes past completed tracks; transient LRCLIB skips are
retried in end-of-run passes. Concurrency defaults to 30 — the throttle ceiling
observed on the predecessor backfill (reference-lrclib-bulk-api-ops).

Usage:
    export DATABASE_URL='postgresql+psycopg://...'      # prod (SSM /myblog/backend)
    python tools/lyrics_bestof_probe.py                  # full pool, resume-aware
    python tools/lyrics_bestof_probe.py --limit 50       # slice
    python tools/lyrics_bestof_probe.py --report-only    # re-aggregate checkpoint

RFC: docs/rfcs/FEAT-lyrics-best-of-promotion.md
"""

import argparse
import json
import logging
import os
import re
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "myblog_worker"))

from lyrics_batch_api import TransientError, search_candidates  # noqa: E402

from worker.service.lyrics_matcher import (  # noqa: E402
    STATUS_AMBIGUOUS,
    STATUS_MATCHED,
    STATUS_REVIEW_REQUIRED,
    TitleNormalizer,
    _strip_version_tokens,
    decide_match,
)
from worker.service.lyrics_promote import _plausible, promote_best  # noqa: E402

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)

OUT_DIR = Path(__file__).resolve().parent / "out"
CHECKPOINT = OUT_DIR / "bestof_probe_checkpoint.jsonl"
REPORT = OUT_DIR / "bestof_probe_report.json"

_TRACKNUM_RE = re.compile(r"^\d{1,3}\s+")

POOL_SQL = """
    SELECT t.id, t.title, t.duration_sec,
           ARRAY_REMOVE(ARRAY_AGG(DISTINCT a.name), NULL)   AS artist_names,
           ARRAY_REMOVE(ARRAY_AGG(DISTINCT al.alias), NULL) AS aliases,
           tl.match_status            AS existing_status,
           tl.evidence->>'reason'     AS existing_reason
    FROM tracks t
    JOIN track_lyrics tl  ON tl.track_id = t.id
                         AND tl.match_status IN ('ambiguous', 'review_required')
    JOIN track_artists ta ON ta.track_id = t.id
    JOIN artists a        ON a.id = ta.artist_id
    LEFT JOIN LATERAL jsonb_array_elements_text(a.aliases) AS al(alias) ON true
    GROUP BY t.id, t.title, t.duration_sec, tl.match_status, tl.evidence->>'reason'
    ORDER BY t.id
"""


def fetch_pool(db_url, limit=None):
    engine = create_engine(db_url, future=True)
    session = sessionmaker(bind=engine)()
    try:
        sql = POOL_SQL + (f" LIMIT {int(limit)}" if limit else "")
        return session.execute(text(sql)).fetchall()
    finally:
        session.close()
        engine.dispose()


def _noise_variant(base: str, catalog_base: str) -> bool:
    """Heuristic: is this group base a duplicate-noise variant of the catalog base?

    Covers the observed LRCLIB noise shapes: leading track-number prefixes
    (``01 come back to earth``) and extra non-rendition words around the same
    base (``come back to earth paused``). A base with no containment relation
    to the catalog base is treated as a genuinely different song.
    """
    if base == catalog_base:
        return True
    if _TRACKNUM_RE.sub("", base) == catalog_base:
        return True
    return catalog_base in base or (base and base in catalog_base)


def classify_ambiguity(title, artist_names, aliases, duration_sec, candidates):
    """duplicate_noise if every plausible group's base is a noise-variant of the catalog base."""
    catalog_base = _strip_version_tokens(TitleNormalizer.normalize(title or ""))
    bases = set()
    for c in _plausible(title, artist_names, aliases, duration_sec, candidates):
        bases.add(_strip_version_tokens(TitleNormalizer.normalize(c.title)))
    if not bases:
        return "no_plausible"
    return "duplicate_noise" if all(_noise_variant(b, catalog_base) for b in bases) else "genuine"


def probe_one(row, candidates):
    """Pure per-track probe computation -> checkpoint record (JSON-safe)."""
    track_id, title, duration_sec = row[0], row[1], row[2]
    artist_names, aliases = list(row[3] or []), list(row[4] or [])
    existing_status, existing_reason = row[5], row[6]

    outcome = decide_match(
        track_id=track_id, title=title, artist_names=artist_names,
        aliases=aliases, duration_sec=duration_sec, candidates=candidates,
    )
    rec = {
        "track_id": str(track_id),
        "title": title,
        "artists": artist_names[:3],
        "duration_sec": float(duration_sec) if duration_sec is not None else None,
        "existing_status": existing_status,
        "existing_reason": existing_reason,
        "refetch_status": outcome.match_status,
        "refetch_reason": (outcome.evidence or {}).get("reason"),
    }

    plaus = _plausible(title, artist_names, aliases, duration_sec, candidates)
    with_body = [c for c in plaus
                 if not c.instrumental and (bool(c.plain_lyrics) or bool(c.synced_lyrics))]
    rec["n_candidates"] = len(candidates)
    rec["n_plausible"] = len(plaus)
    rec["n_body"] = len(with_body)

    if outcome.match_status not in (STATUS_AMBIGUOUS, STATUS_REVIEW_REQUIRED):
        # LRCLIB grew / changed since the row was parked — not a best-of case.
        rec["promotion"] = "pool_drift"
        return rec

    if outcome.match_status == STATUS_AMBIGUOUS:
        rec["ambiguity_class"] = classify_ambiguity(
            title, artist_names, aliases, duration_sec, candidates)

    promoted = promote_best(outcome, title, artist_names, aliases, duration_sec, candidates)
    if promoted.match_status == STATUS_MATCHED:
        chosen = promoted.evidence["promotion"]["chosen"]
        gap = (abs(float(duration_sec) - float(chosen["duration_sec"]))
               if duration_sec is not None and chosen["duration_sec"] is not None else None)
        body = promoted.lyric_plain or promoted.lyric_synced or ""
        rec["promotion"] = "promoted"
        rec["basis"] = promoted.match_basis
        rec["chosen"] = chosen
        rec["duration_gap"] = gap
        rec["lyric_kind"] = "synced" if promoted.lyric_synced else "plain"
        rec["lyric_snippet"] = body.strip().splitlines()[0][:120] if body.strip() else ""
        # audit context: the previews the matcher parked on
        rec["parked_candidates"] = (outcome.evidence or {}).get("candidates")
    elif promoted.match_status == "no_lyrics":
        rec["promotion"] = "resolved_no_lyrics"
    else:
        rec["promotion"] = "parked"
        rec["parked_reason"] = (promoted.evidence or {}).get("promotion", {}).get("reason")
    return rec


def run_probe(args):
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        logger.error("DATABASE_URL not set")
        sys.exit(1)

    OUT_DIR.mkdir(exist_ok=True)
    done = set()
    if CHECKPOINT.exists():
        with CHECKPOINT.open() as f:
            for line in f:
                try:
                    done.add(json.loads(line)["track_id"])
                except (json.JSONDecodeError, KeyError):
                    continue
        logger.info("checkpoint: %d tracks already probed — resuming", len(done))

    pool = fetch_pool(db_url, limit=args.limit)
    todo = [r for r in pool if str(r[0]) not in done]
    logger.info("pool=%d todo=%d concurrency=%d", len(pool), len(todo), args.concurrency)

    limits = httpx.Limits(max_connections=args.concurrency + 2,
                          max_keepalive_connections=args.concurrency + 2)
    client = httpx.Client(timeout=20.0, limits=limits,
                          headers={"User-Agent": "myblog-lyrics-bestof-probe/1.0 (private research)"})

    def fetch_one(row):
        try:
            return row, search_candidates(client, row[1], (list(row[3] or []) or [""])[0]), None
        except TransientError as exc:
            return row, None, exc

    started = time.time()
    processed = 0
    try:
        with CHECKPOINT.open("a") as ckpt:
            remaining = todo
            for pass_no in range(args.retry_passes + 1):
                if not remaining:
                    break
                if pass_no:
                    logger.info("retry pass %d: %d transient-skipped tracks", pass_no, len(remaining))
                skipped = []
                with ThreadPoolExecutor(max_workers=args.concurrency) as ex:
                    for row, candidates, exc in ex.map(fetch_one, remaining):
                        if exc is not None:
                            skipped.append(row)
                            continue
                        rec = probe_one(row, candidates)
                        ckpt.write(json.dumps(rec, ensure_ascii=False) + "\n")
                        ckpt.flush()
                        processed += 1
                        if processed % 200 == 0:
                            rate = processed / max(time.time() - started, 1e-6)
                            eta = (len(todo) - processed) / max(rate, 1e-6) / 60
                            logger.info("progress %d/%d (skipped=%d) %.2f req/s ETA ~%.0f min",
                                        processed, len(todo), len(skipped), rate, eta)
                remaining = skipped
    finally:
        client.close()

    elapsed = (time.time() - started) / 60
    logger.info("probe pass done: %d/%d in %.1f min (%.2f req/s), unresolved skips=%d",
                processed, len(todo), elapsed,
                processed / max(elapsed * 60, 1e-6), len(remaining))
    return len(remaining)


def _bucket(gap):
    if gap is None:
        return "unknown"
    for hi in (0.5, 1.0, 1.5, 2.0):
        if gap <= hi:
            return f"<= {hi}s"
    return "> 2s"


def report():
    recs = []
    with CHECKPOINT.open() as f:
        for line in f:
            try:
                recs.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    # last record per track wins (retry passes can duplicate)
    by_id = {r["track_id"]: r for r in recs}
    recs = list(by_id.values())

    n = len(recs)
    amb = [r for r in recs if r["existing_status"] == "ambiguous"]
    rev = [r for r in recs if r["existing_status"] == "review_required"]
    promoted = [r for r in recs if r["promotion"] == "promoted"]
    drift = [r for r in recs if r["promotion"] == "pool_drift"]
    still = [r for r in recs if r["promotion"] in ("parked", "resolved_no_lyrics")]

    def pct(x, d):
        return f"{x}/{d} ({100.0 * x / d:.1f}%)" if d else f"{x}/0"

    rpt = {
        "denominator_pool_probed": n,
        "existing_status_split": {"ambiguous": len(amb), "review_required": len(rev)},
        "pool_drift_on_refetch": {
            "count": pct(len(drift), n),
            "note": "no longer ambiguous/review on fresh LRCLIB fetch (would resolve via normal re-eval, not best-of)",
            "refetch_status_breakdown": dict(Counter(r["refetch_status"] for r in drift)),
        },
        "a_tier1_hit_rate": {
            "overall": pct(len(promoted), n),
            "of_still_parked_pool": pct(len(promoted), n - len(drift)),
            "ambiguous": pct(sum(1 for r in promoted if r["existing_status"] == "ambiguous"), len(amb)),
            "review_required": pct(sum(1 for r in promoted if r["existing_status"] == "review_required"), len(rev)),
        },
        "b_duration_gap_of_pick": dict(Counter(_bucket(r.get("duration_gap")) for r in promoted)),
        "c_ambiguity_class": {
            "denominator": "refetch-still-ambiguous rows",
            **dict(Counter(r.get("ambiguity_class") for r in recs if r.get("ambiguity_class"))),
        },
        "d_review_version_agreeing_sibling": {
            "denominator": "existing review_required rows probed",
            "promoted_via_tier1": pct(
                sum(1 for r in promoted if r["existing_status"] == "review_required"), len(rev)),
            "of_which_version_token_mismatch": pct(
                sum(1 for r in promoted
                    if r["existing_status"] == "review_required"
                    and r.get("existing_reason") == "version_token_mismatch"),
                sum(1 for r in rev if r.get("existing_reason") == "version_token_mismatch")),
        },
        "e_gated_tier_residual": {
            "denominator": "rows parked after v1 (excl. pool drift + no_lyrics resolution)",
            "parked_total": len([r for r in still if r["promotion"] == "parked"]),
            "with_body_candidate_tiers24_could_pick": pct(
                sum(1 for r in still if r["promotion"] == "parked" and r.get("n_body", 0) > 0),
                len([r for r in still if r["promotion"] == "parked"])),
            "parked_reasons": dict(Counter(r.get("parked_reason") for r in still
                                           if r["promotion"] == "parked")),
        },
        "resolved_no_lyrics": len([r for r in still if r["promotion"] == "resolved_no_lyrics"]),
        "lyric_kind_of_promotions": dict(Counter(r.get("lyric_kind") for r in promoted)),
    }
    REPORT.write_text(json.dumps(rpt, indent=2, ensure_ascii=False))
    print(json.dumps(rpt, indent=2, ensure_ascii=False))
    return rpt


def main():
    parser = argparse.ArgumentParser(description="best-of promotion risk-quant probe (read-only)")
    parser.add_argument("--limit", type=int, default=None, help="cap pool (slice run)")
    parser.add_argument("--concurrency", type=int, default=30,
                        help="parallel LRCLIB fetches (predecessor throttle ceiling ~30)")
    parser.add_argument("--retry-passes", type=int, default=2,
                        help="end-of-run retry passes over transient skips")
    parser.add_argument("--report-only", action="store_true",
                        help="aggregate the existing checkpoint, no fetching")
    args = parser.parse_args()

    if not args.report_only:
        run_probe(args)
    report()


if __name__ == "__main__":
    main()
