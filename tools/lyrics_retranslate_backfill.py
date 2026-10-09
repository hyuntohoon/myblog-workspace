#!/usr/bin/env python3
"""Retired Claude lyrics backfill. Requests now run explicitly in Chat.

Legacy flags are accepted, but the entrypoint returns before DB/model access.
The historical single-row helper also reaches the retired model dispatch.
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
    ap.parse_args()
    log.warning("Claude retranslation backfill is retired; request a track in Chat")
    return 0


if __name__ == "__main__":
    sys.exit(main())
