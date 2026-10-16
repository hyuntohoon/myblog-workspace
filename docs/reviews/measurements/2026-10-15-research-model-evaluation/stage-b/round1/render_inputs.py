#!/usr/bin/env python3
"""Render the shared input block for Stage B round 1, read-only.

Uses the production poller's own renderers (_album_block, _genius_block,
_catalog_block) joined as build_prompt joins them, so candidate and control get
the same bytes per album. Usage: render_inputs.py <shared_db_src> <out_dir> <album_id>=<slug>...
"""
import sys
from pathlib import Path

shared_db_src, out_dir, *pairs = sys.argv[1:]
sys.path.insert(0, shared_db_src)
sys.path.insert(0, str(Path(__file__).resolve().parents[6] / "scripts"))
import research_poller as rp  # noqa: E402

with rp.connect() as conn:
    conn.read_only = True
    for pair in pairs:
        album_id, slug = pair.split("=", 1)
        meta = rp.album_meta(conn, album_id)
        parts = [rp._album_block(meta)]
        for block in (rp._genius_block(conn, album_id), rp._catalog_block(conn, album_id)):
            if block:
                parts.append(block)
        Path(out_dir, f"{slug}.txt").write_text("\n".join(parts), encoding="utf-8")
        print(slug, meta["title"], len("\n".join(parts)))
