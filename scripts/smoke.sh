#!/usr/bin/env bash
# Wrapper for scripts/smoke.py — finds a Python with boto3 available.
#
# Usage:
#   ./scripts/smoke.sh prod
#   ./scripts/smoke.sh local
#
# Needed env (prod):
#   MYBLOG_SMOKE_PASSWORD   — test user password
#   MYBLOG_SMOKE_EMAIL      — optional, default test@ratemymusic.blog
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY=""

for candidate in python3.11 python3.12 python3; do
  if command -v "$candidate" >/dev/null 2>&1; then
    if "$candidate" -c "import boto3" >/dev/null 2>&1; then
      PY="$candidate"
      break
    fi
  fi
done

if [ -z "$PY" ]; then
  echo "No Python with boto3 found. Install boto3 (pip install boto3)." >&2
  exit 2
fi

exec "$PY" "$HERE/smoke.py" "$@"
