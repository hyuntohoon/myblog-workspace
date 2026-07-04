#!/usr/bin/env python3
"""FEAT-lyrics-engine-sonnet Step 2 — one-shot re-translation backfill (WRITES).

Re-translates every remaining ``done | amazon.translate`` row of
``track_lyrics_translations`` in place with the Step-1 poller engine
(headless ``claude -p --model sonnet``, benchmark-frozen 의역 prompt). This
driver adds NO engine, validation, or normalization logic of its own — it
imports ``scripts/lyrics_translate_poller.py`` and reuses its functions
verbatim (RFC: no logic fork), so the backfill writes exactly what the
forward path would.

Safety (RFC Step 2):
  * a pre-run dump of every selected row (full row as JSON) is written to
    ``--out-dir`` BEFORE any write — restoring a row is a single UPDATE from
    that file;
  * per-track commit; only a validation-PASS translation touches the row
    (failures of either kind leave the Amazon row intact — the viewer never
    loses a translation mid-backfill);
  * the UPDATE is guarded by ``AND status='done' AND model='amazon.translate'``
    so a concurrent viewer re-request can't be clobbered;
  * re-running resumes naturally: converted rows leave the selection.

Usage:
    python tools/lyrics_retranslate_backfill.py                 # dry-run: selection only
    python tools/lyrics_retranslate_backfill.py --execute       # translate + write
    python tools/lyrics_retranslate_backfill.py --execute --limit 2
    # DATABASE_URL overrides; else SSM /myblog/backend (owner AWS creds).

RFC: docs/rfcs/FEAT-lyrics-engine-sonnet.md (Step 2). Success gate: all
selected rows flipped to ``claude.sonnet`` with validation PASS (denominator =
rows still ``model='amazon.translate'`` at run start), plus owner 3-track
viewer spot-audit.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent.parent  # myblog-workspace/
sys.path.insert(0, str(ROOT / "scripts"))

# Engine + validation + DB plumbing come from the live poller — no logic fork.
import lyrics_translate_poller as poller  # noqa: E402  (inserts myblog_backend on sys.path)
from app.services.lyrics_service import (  # noqa: E402
    NORMALIZER_VERSION,
    compute_source_fingerprint,
    normalize_lyrics,
)

log = logging.getLogger("lyrics-retranslate-backfill")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

SELECT_SQL = """
SELECT tr.track_id, t.title, t.spotify_id,
       jsonb_array_length(tr.segments) AS seg_count
FROM track_lyrics_translations tr JOIN tracks t ON t.id = tr.track_id
WHERE tr.status = 'done' AND tr.model = 'amazon.translate'
ORDER BY jsonb_array_length(tr.segments);
"""

DUMP_SQL = """
SELECT jsonb_agg(to_jsonb(tr)) FROM track_lyrics_translations tr
WHERE tr.status = 'done' AND tr.model = 'amazon.translate';
"""

UPDATE_SQL = """
UPDATE track_lyrics_translations
SET segments = %s::jsonb, source_fingerprint = %s, normalizer_version = %s,
    model = %s, translator_version = %s, error = NULL,
    translated_at = now(), updated_at = now()
WHERE track_id = %s AND status = 'done' AND model = 'amazon.translate';
"""


def retranslate_one(conn, track_id: str, execute: bool) -> dict:
    """Step-1 engine path over one existing row. Returns a report entry;
    only a validation PASS (with --execute) writes."""
    with conn.cursor() as cur:
        cur.execute(poller.SOURCE_SQL, (track_id,))
        src = cur.fetchone()
    conn.commit()
    if src is None:
        return {"result": "FAIL:track_vanished"}

    row = SimpleNamespace(
        match_status=src["match_status"], lyric_plain=src["lyric_plain"],
        lyric_synced=src["lyric_synced"], track_id=track_id,
    ) if src["match_status"] is not None else None
    out = normalize_lyrics(row)
    if out.availability != "ok":
        return {"result": f"FAIL:source_{out.availability}"}
    non_gap = [s for s in out.segments if s.text != ""]

    t0 = time.monotonic()
    try:
        texts_ko = poller.claude_translate([s.text for s in non_gap])
    except poller.TransientEngineError as e:
        return {"result": f"FAIL:transient ({e})", "lines": len(non_gap)}
    except poller.EngineValidationError as e:
        return {"result": f"FAIL:engine_validation ({e})", "lines": len(non_gap)}
    dt = round(time.monotonic() - t0, 1)

    ko_by_i = {s.i: t for s, t in zip(non_gap, texts_ko)}
    stored = [{"i": s.i, "text_ko": ko_by_i.get(s.i, "")} for s in out.segments]
    fingerprint = compute_source_fingerprint(out.normalizer_version, out.segments)

    if not execute:
        return {"result": "PASS:dry-run(no write)", "lines": len(non_gap), "secs": dt}
    with conn.cursor() as cur:
        cur.execute(UPDATE_SQL, (
            json.dumps(stored, ensure_ascii=False), fingerprint,
            NORMALIZER_VERSION, poller.MT_MODEL, poller.TRANSLATOR_VERSION, track_id,
        ))
        written = cur.rowcount
    conn.commit()
    if written != 1:  # guard clause lost the race (e.g. concurrent re-request)
        return {"result": "FAIL:row_changed_underneath", "lines": len(non_gap)}
    return {"result": "PASS", "lines": len(non_gap), "secs": dt,
            "segments": len(out.segments)}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--execute", action="store_true",
                    help="run the engine and write (default: list the selection only)")
    ap.add_argument("--limit", type=int, default=None, help="sanity slice")
    ap.add_argument("--out-dir", type=Path, default=ROOT / "tools" / "out",
                    help="pre-state dump + report directory (gitignored)")
    args = ap.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    conn = poller.connect()
    try:
        with conn.cursor() as cur:
            cur.execute(SELECT_SQL)
            targets = cur.fetchall()
        conn.commit()
        if args.limit:
            targets = targets[: args.limit]
        log.info("selection: %d row(s) still done|amazon.translate", len(targets))
        for t in targets:
            log.info("  %s  %s (%d segments)", t["track_id"], t["title"], t["seg_count"])
        if not targets:
            return 0
        if not args.execute:
            log.info("dry-run — pass --execute to translate + write")
            return 0

        # Pre-state dump BEFORE any write (rollback = one UPDATE per row from this file).
        with conn.cursor() as cur:
            cur.execute(DUMP_SQL)
            pre = cur.fetchone()
        conn.commit()
        stamp = time.strftime("%Y%m%d-%H%M%S")
        dump_path = args.out_dir / f"retranslate_prestate_{stamp}.json"
        dump_path.write_text(json.dumps(list(pre.values())[0], ensure_ascii=False, indent=1))
        log.info("pre-state dumped: %s", dump_path)

        report = []
        for i, t in enumerate(targets):
            entry = {"track_id": str(t["track_id"]), "title": t["title"]}
            entry.update(retranslate_one(conn, t["track_id"], execute=True))
            report.append(entry)
            log.info("[%d/%d] %s — %s", i + 1, len(targets), t["title"], entry["result"])
            if i + 1 < len(targets):
                time.sleep(poller.INTER_RUN_SLEEP_S)

        report_path = args.out_dir / f"retranslate_report_{stamp}.json"
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=1))
        n_pass = sum(1 for r in report if r["result"] == "PASS")
        log.info("==== %d/%d PASS ==== report: %s", n_pass, len(report), report_path)
        for r in report:
            log.info("  %-28s %s", r["title"][:28], r["result"])
        return 0 if n_pass == len(report) else 1
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
