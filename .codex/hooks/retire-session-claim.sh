#!/usr/bin/env bash
# Retire a Codex checkout claim when the owning session ends.
set -euo pipefail

python3 -c '
import json
import os
import pathlib
import re
import sys

try:
    data = json.load(sys.stdin)
except Exception:
    sys.exit(0)

session_id = data.get("session_id", "")
if not re.fullmatch(r"[A-Za-z0-9._-]+", session_id):
    sys.exit(0)

root = pathlib.Path(os.environ.get("CODEX_HOME", pathlib.Path.home() / ".codex"))
claim = root / "myblog-session-claims" / session_id
try:
    claim.unlink()
except FileNotFoundError:
    pass
'
