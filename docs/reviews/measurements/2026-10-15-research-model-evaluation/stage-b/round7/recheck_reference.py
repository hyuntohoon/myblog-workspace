#!/usr/bin/env python3
"""Re-check the frozen D6 reference before the first round-7 generation (ROUND.md §5).

Fetches the Qobuz listing zbylnavz5biaa with the D6 check's method (curl, static HTML,
the first track__info of each track__infos block), and compares the ten credit lines
with ../d6-measurement/reference/qobuz-gemini-rights.txt. On a byte match it writes
reference/qobuz-gemini-rights.txt (the frozen text, capture note updated) and
reference/recheck.json. On any difference it writes nothing but recheck.json and exits 1:
the round stops before generation.

Usage: python3 -I recheck_reference.py
"""
from __future__ import annotations

import hashlib
import html
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
FROZEN = HERE.parent / "d6-measurement" / "reference" / "qobuz-gemini-rights.txt"
URL = "https://www.qobuz.com/us-en/album/gemini-rights-steve-lacy/zbylnavz5biaa"
OLD_NOTE = ("Captured 2026-10-20, after generation; the same listing was retrieved by a producer on 2026-10-19, "
            "so it was accessible at generation time.")


def main() -> int:
    raw = subprocess.run(["curl", "-sSL", "--max-time", "30", "-A", "Mozilla/5.0", URL],
                         check=True, capture_output=True).stdout
    page = raw.decode("utf-8")
    credits = [html.unescape(m).strip() for m in
               re.findall(r'<div class="track__infos">\s*<p class="track__info">(.*?)</p>', page, re.S)]
    frozen = FROZEN.read_text(encoding="utf-8")
    frozen_lines = re.findall(r"^\d+\. .*? \(\d\d:\d\d:\d\d\): (.*)$", frozen, re.M)
    now = datetime.now(timezone.utc).isoformat()
    match = credits == frozen_lines and len(credits) == 10
    (HERE / "reference").mkdir(exist_ok=True)
    (HERE / "reference" / "recheck.json").write_text(json.dumps({
        "checked_at": now, "url": URL, "html_sha256": hashlib.sha256(raw).hexdigest(),
        "tracks_found": len(credits), "frozen_tracks": len(frozen_lines), "match": match,
        "diff": [] if match else [{"n": n + 1, "frozen": f, "now": c}
                                  for n, (f, c) in enumerate(zip(frozen_lines, credits)) if f != c],
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if not match:
        print("reference differs; stop before generation", file=sys.stderr)
        return 1
    assert frozen.count(OLD_NOTE) == 1
    note = (f"Captured 2026-10-20 for the D6 check and re-checked byte for byte at round-7 dispatch ({now[:16]}Z), "
            "before generation, so it was accessible when these notes were produced.")
    (HERE / "reference" / "qobuz-gemini-rights.txt").write_text(frozen.replace(OLD_NOTE, note), encoding="utf-8")
    print(json.dumps({"match": True, "checked_at": now}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
