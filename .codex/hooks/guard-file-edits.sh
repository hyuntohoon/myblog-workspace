#!/usr/bin/env bash
# Block apply_patch writes to files that may contain credentials or private keys.
set -euo pipefail

python3 -c '
import fnmatch
import json
import os
import re
import sys

try:
    data = json.load(sys.stdin)
except Exception:
    sys.exit(0)

if data.get("tool_name") != "apply_patch":
    sys.exit(0)

command = (data.get("tool_input") or {}).get("command", "")
patterns = (
    ".env", ".env.*", "*.env", "secrets.yaml", "secrets.yml",
    "config.local.json", "*.pem", "*.key", "credentials",
    "credentials.json", ".credentials.json",
)
headers = re.findall(
    r"^\*\*\* (?:Add|Update|Delete) File: (.+)$|^\*\*\* Move to: (.+)$",
    command,
    flags=re.MULTILINE,
)
paths = [next(value for value in pair if value).strip() for pair in headers]
blocked = [
    path for path in paths
    if any(fnmatch.fnmatch(os.path.basename(path.rstrip("/")), pattern)
           for pattern in patterns)
]
if not blocked:
    sys.exit(0)

print(json.dumps({"hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": (
        "Hard rule #2: refusing to edit a protected secret file: "
        + ", ".join(blocked)
        + ". Use AWS SSM Parameter Store or GitHub Actions Secrets."
    ),
}}))
'
