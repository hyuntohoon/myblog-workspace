#!/usr/bin/env python3
"""FIX-lyrics-matcher-noise Step 1 — old-vs-new matcher replay probe (READ-ONLY).

Re-fetches LRCLIB candidates for three prod pools and replays BOTH matcher
versions over the SAME candidate set, isolating the code change from LRCLIB
drift:

  old = ``decide_match`` @ origin/main (step2-v2), loaded from ``git show``
  new = ``decide_match`` (+ ``promote_best`` when still parked) @ the branch

Pools (tagged per row):
  unresolved — every current ``ambiguous`` / ``review_required`` row (the
               post-backfill residual this RFC targets)
  bestof     — sample of ``best-of-*`` matched rows (expected to upgrade to
               source-resolved exact-title; informational)
  exact      — sample of pre-existing ``exact-title`` rows (regression guard:
               the new matcher must keep the SAME pick)

Reports: the outcome-delta matrix per pool, exact-title regression count
(must be 0), genuine-ambiguity retention, and a stratified changed-outcome
audit sample (RFC OQ3 gate: n>=40, >=90% precision). Writes NOTHING to the DB.

Usage:
    export DATABASE_URL='postgresql+psycopg://...'      # prod (SSM /myblog/backend)
    python tools/lyrics_matcher_noise_probe.py
    python tools/lyrics_matcher_noise_probe.py --report-only

RFC: docs/rfcs/FIX-lyrics-matcher-noise.md
"""

import argparse
import importlib.util
import json
import logging
import os
import subprocess
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

TOOLS_DIR = Path(__file__).resolve().parent
WORKER_DIR = TOOLS_DIR.parent / "myblog_worker"
sys.path.insert(0, str(TOOLS_DIR))
sys.path.insert(0, str(WORKER_DIR))

from lyrics_batch_api import TransientError, search_candidates  # noqa: E402

from worker.service.lyrics_matcher import (  # noqa: E402  (NEW matcher, branch)
    STATUS_AMBIGUOUS,
    STATUS_MATCHED,
    STATUS_REVIEW_REQUIRED,
    decide_match as new_decide_match,
)
from worker.service.lyrics_promote import promote_best  # noqa: E402

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)

OUT_DIR = TOOLS_DIR / "out"
CHECKPOINT = OUT_DIR / "noise_probe_checkpoint.jsonl"
REPORT = OUT_DIR / "noise_probe_report.json"
AUDIT_SAMPLE = OUT_DIR / "noise_probe_audit_sample.json"
OLD_MATCHER_SNAPSHOT = OUT_DIR / "_old_matcher_step2v2.py"

POOL_SQL = """
    WITH pool AS (
        SELECT tl.track_id, tl.match_status, tl.evidence->>'reason' AS reason,
               tl.evidence->>'match_basis' AS basis,
               tl.evidence->>'lrclib_id'   AS old_lrclib_id,
               CASE
                 WHEN tl.match_status IN ('ambiguous', 'review_required') THEN 'unresolved'
                 WHEN tl.match_status = 'matched'
                      AND tl.evidence->>'match_basis' LIKE 'best-of-%%' THEN 'bestof'
                 WHEN tl.match_status = 'matched'
                      AND tl.evidence->>'match_basis' = 'exact-title' THEN 'exact'
               END AS pool
        FROM track_lyrics tl
    ), sampled AS (
        (SELECT * FROM pool WHERE pool = 'unresolved')
        UNION ALL
        (SELECT * FROM pool WHERE pool = 'bestof'
         ORDER BY md5(track_id::text) LIMIT :bestof_n)
        UNION ALL
        (SELECT * FROM pool WHERE pool = 'exact'
         ORDER BY md5(track_id::text) LIMIT :exact_n)
    )
    SELECT t.id, t.title, t.duration_sec,
           ARRAY_REMOVE(ARRAY_AGG(DISTINCT a.name), NULL)   AS artist_names,
           ARRAY_REMOVE(ARRAY_AGG(DISTINCT al.alias), NULL) AS aliases,
           s.match_status AS existing_status,
           s.reason       AS existing_reason,
           s.basis        AS existing_basis,
           s.old_lrclib_id,
           s.pool
    FROM sampled s
    JOIN tracks t         ON t.id = s.track_id
    JOIN track_artists ta ON ta.track_id = t.id
    JOIN artists a        ON a.id = ta.artist_id
    LEFT JOIN LATERAL jsonb_array_elements_text(a.aliases) AS al(alias) ON true
    GROUP BY t.id, t.title, t.duration_sec, s.match_status, s.reason,
             s.basis, s.old_lrclib_id, s.pool
    ORDER BY s.pool, t.id
"""


def load_old_matcher():
    """Load the origin/main (step2-v2) matcher as an isolated module."""
    OUT_DIR.mkdir(exist_ok=True)
    src = subprocess.run(
        ["git", "-C", str(WORKER_DIR), "show", "origin/main:worker/service/lyrics_matcher.py"],
        capture_output=True, text=True, check=True,
    ).stdout
    OLD_MATCHER_SNAPSHOT.write_text(src)
    spec = importlib.util.spec_from_file_location("old_lyrics_matcher", OLD_MATCHER_SNAPSHOT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if mod.MATCHER_VERSION == "step3-v1":
        raise RuntimeError("origin/main already carries step3-v1 — old/new comparison is void")
    return mod


def fetch_pool(db_url, bestof_n, exact_n):
    engine = create_engine(db_url, future=True)
    session = sessionmaker(bind=engine)()
    try:
        return session.execute(
            text(POOL_SQL), {"bestof_n": bestof_n, "exact_n": exact_n}
        ).fetchall()
    finally:
        session.close()
        engine.dispose()


def probe_one(row, candidates, old_decide_match):
    track_id, title, duration_sec = row[0], row[1], row[2]
    artist_names, aliases = list(row[3] or []), list(row[4] or [])

    old = old_decide_match(
        track_id=track_id, title=title, artist_names=artist_names,
        aliases=aliases, duration_sec=duration_sec, candidates=candidates,
    )
    new = new_decide_match(
        track_id=track_id, title=title, artist_names=artist_names,
        aliases=aliases, duration_sec=duration_sec, candidates=candidates,
    )
    new_final = new
    if new.match_status in (STATUS_AMBIGUOUS, STATUS_REVIEW_REQUIRED):
        new_final = promote_best(new, title, artist_names, aliases, duration_sec, candidates)

    rec = {
        "track_id": str(track_id),
        "pool": row[9],
        "title": title,
        "artists": artist_names[:3],
        "duration_sec": float(duration_sec) if duration_sec is not None else None,
        "existing_status": row[5],
        "existing_reason": row[6],
        "existing_basis": row[7],
        "existing_lrclib_id": row[8],
        "n_candidates": len(candidates),
        "old_status": old.match_status,
        "old_reason": (old.evidence or {}).get("reason"),
        "old_basis": old.match_basis,
        "old_pick": (old.evidence or {}).get("lrclib_id"),
        "new_status": new.match_status,
        "new_reason": (new.evidence or {}).get("reason"),
        "new_basis": new.match_basis,
        "new_pick": (new.evidence or {}).get("lrclib_id"),
        "new_noise_marker": (new.evidence or {}).get("title_noise_stripped"),
        "new_final_status": new_final.match_status,
        "new_final_basis": new_final.match_basis,
    }
    if new_final.match_status == STATUS_MATCHED:
        body = new_final.lyric_plain or new_final.lyric_synced or ""
        ev = new_final.evidence or {}
        chosen = ev.get("promotion", {}).get("chosen") or {
            "lrclib_id": ev.get("lrclib_id"), "title": ev.get("lrclib_title"),
            "artist": ev.get("lrclib_artist"), "duration_sec": ev.get("lrclib_duration_sec"),
        }
        rec["new_chosen"] = chosen
        rec["lyric_kind"] = "synced" if new_final.lyric_synced else "plain"
        rec["lyric_snippet"] = body.strip().splitlines()[0][:120] if body.strip() else ""
    return rec


def run_probe(args):
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        logger.error("DATABASE_URL not set")
        sys.exit(1)

    old_mod = load_old_matcher()
    logger.info("old matcher loaded: %s", old_mod.MATCHER_VERSION)

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

    pool = fetch_pool(db_url, args.bestof_sample, args.exact_sample)
    todo = [r for r in pool if str(r[0]) not in done]
    logger.info("pool=%d (%s) todo=%d concurrency=%d",
                len(pool), dict(Counter(r[9] for r in pool)), len(todo), args.concurrency)

    limits = httpx.Limits(max_connections=args.concurrency + 2,
                          max_keepalive_connections=args.concurrency + 2)
    client = httpx.Client(timeout=20.0, limits=limits,
                          headers={"User-Agent": "myblog-lyrics-noise-probe/1.0 (private research)"})

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
                        rec = probe_one(row, candidates, old_mod.decide_match)
                        ckpt.write(json.dumps(rec, ensure_ascii=False) + "\n")
                        ckpt.flush()
                        processed += 1
                        if processed % 100 == 0:
                            rate = processed / max(time.time() - started, 1e-6)
                            eta = (len(todo) - processed) / max(rate, 1e-6) / 60
                            logger.info("progress %d/%d (skipped=%d) %.2f req/s ETA ~%.0f min",
                                        processed, len(todo), len(skipped), rate, eta)
                remaining = skipped
    finally:
        client.close()

    elapsed = (time.time() - started) / 60
    logger.info("probe done: %d/%d in %.1f min, unresolved skips=%d",
                processed, len(todo), elapsed, len(remaining))
    return len(remaining)


def report(audit_n):
    recs = []
    with CHECKPOINT.open() as f:
        for line in f:
            try:
                recs.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    by_id = {r["track_id"]: r for r in recs}
    recs = list(by_id.values())

    def pct(x, d):
        return f"{x}/{d} ({100.0 * x / d:.1f}%)" if d else f"{x}/0"

    pools = {p: [r for r in recs if r["pool"] == p] for p in ("unresolved", "bestof", "exact")}

    # (i) same-candidates outcome-delta matrix (old decide -> new decide)
    delta = {}
    for p, rows in pools.items():
        delta[p] = dict(Counter(f'{r["old_status"]}->{r["new_status"]}' for r in rows))

    # (ii) exact-title regression: old matched must stay matched w/ the SAME pick
    exact_rows = pools["exact"]
    exact_old_matched = [r for r in exact_rows if r["old_status"] == "matched"]
    regressed = [r for r in exact_old_matched if r["new_status"] != "matched"]
    pick_changed = [r for r in exact_old_matched
                    if r["new_status"] == "matched" and r["new_pick"] != r["old_pick"]]
    # old matched -> new not matched ANYWHERE (all pools)
    lost_anywhere = [r for r in recs
                     if r["old_status"] == "matched" and r["new_status"] != "matched"]

    # (iii) genuine-ambiguity retention: rows BOTH matchers leave ambiguous with
    # multiple distinct groups vs rows the fix resolves
    old_ambiguous = [r for r in recs if r["old_status"] == "ambiguous"]
    newly_resolved = [r for r in old_ambiguous if r["new_final_status"] == "matched"]
    newly_ambiguous = [r for r in recs
                       if r["old_status"] != "ambiguous" and r["new_status"] == "ambiguous"]

    # changed rows (the OQ3 audit universe): parked-by-old -> matched-by-new (source)
    changed = [r for r in recs
               if r["old_status"] in ("ambiguous", "review_required")
               and r["new_status"] == "matched"]

    rpt = {
        "denominators": {p: len(rows) for p, rows in pools.items()},
        "i_outcome_delta_same_candidates": delta,
        "ii_exact_regression_guard": {
            "old_matched_probed": len(exact_old_matched),
            "new_no_longer_matched (MUST be 0)": len(regressed),
            "same_pick": pct(len(exact_old_matched) - len(pick_changed) - len(regressed),
                             len(exact_old_matched)),
            "pick_changed": [
                {"track_id": r["track_id"], "title": r["title"],
                 "old_pick": r["old_pick"], "new_pick": r["new_pick"]}
                for r in pick_changed[:20]
            ],
            "lost_matched_any_pool (MUST be 0)": [
                {"track_id": r["track_id"], "title": r["title"], "pool": r["pool"],
                 "new_status": r["new_status"], "new_reason": r["new_reason"]}
                for r in lost_anywhere[:20]
            ],
        },
        "iii_ambiguity": {
            "old_ambiguous_probed": len(old_ambiguous),
            "resolved_at_source_by_fix": pct(len(newly_resolved), len(old_ambiguous)),
            "still_ambiguous_new": pct(
                sum(1 for r in old_ambiguous if r["new_status"] == "ambiguous"),
                len(old_ambiguous)),
            "NEWLY_ambiguous (MUST be ~0)": len(newly_ambiguous),
        },
        "iv_changed_outcome_universe": {
            "denominator": "old decide parked (ambiguous/review) -> new decide matched",
            "count": len(changed),
            "by_new_basis": dict(Counter(r["new_basis"] for r in changed)),
            "noise_marker_split": dict(Counter(
                ",".join(r["new_noise_marker"]) if r.get("new_noise_marker") else "rep-only"
                for r in changed)),
        },
        "unresolved_pool_preview": {
            "denominator": "current ambiguous/review rows (Step-3 target)",
            "new_final_status": dict(Counter(r["new_final_status"] for r in pools["unresolved"])),
        },
    }
    REPORT.write_text(json.dumps(rpt, indent=2, ensure_ascii=False))
    print(json.dumps(rpt, indent=2, ensure_ascii=False))

    # stratified audit sample over changed rows: EN/KR x noise-classes
    def is_kr(r):
        return any("가" <= ch <= "힣" for ch in (r["title"] or ""))

    sample, seen = [], set()
    strata = [
        lambda r: r.get("new_noise_marker") and "candidate" in r["new_noise_marker"],
        lambda r: r.get("new_noise_marker") and "track" in r["new_noise_marker"],
        lambda r: not r.get("new_noise_marker"),  # representative-fix class
        is_kr,
    ]
    for stratum in strata:
        for r in changed:
            if len(sample) >= audit_n:
                break
            if r["track_id"] not in seen and stratum(r):
                seen.add(r["track_id"])
                sample.append(r)
    for r in changed:  # fill remainder
        if len(sample) >= audit_n:
            break
        if r["track_id"] not in seen:
            seen.add(r["track_id"])
            sample.append(r)
    AUDIT_SAMPLE.write_text(json.dumps(sample, indent=2, ensure_ascii=False))
    logger.info("audit sample: %d changed rows -> %s", len(sample), AUDIT_SAMPLE)
    return rpt


def main():
    parser = argparse.ArgumentParser(description="old-vs-new matcher noise probe (read-only)")
    parser.add_argument("--bestof-sample", type=int, default=400)
    parser.add_argument("--exact-sample", type=int, default=300)
    parser.add_argument("--audit-n", type=int, default=48)
    parser.add_argument("--concurrency", type=int, default=40)
    parser.add_argument("--retry-passes", type=int, default=2)
    parser.add_argument("--report-only", action="store_true")
    args = parser.parse_args()

    if not args.report_only:
        run_probe(args)
    report(args.audit_n)


if __name__ == "__main__":
    main()
