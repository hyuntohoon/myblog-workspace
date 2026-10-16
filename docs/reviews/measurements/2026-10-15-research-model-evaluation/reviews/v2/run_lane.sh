#!/bin/bash
# Usage: run_lane.sh <astra|claude> <label>...   One runner dispatch per label, serialized;
# stops the lane on the first rate_limited / blocked_cooldown result. No retries.
set -u
lane=$1; shift
V=$(cd "$(dirname "$0")" && pwd)
WT=/private/tmp/myblog-research-eval-r2
for L in "$@"; do
  m="$V/manifests/$lane-$L.json"; mkdir -p "$V/manifests"
  if [ "$lane" = astra ]; then prov=gpt; model=gpt-6-astra; else prov=claude; model=claude-opus-5-5; fi
  python3 -c "import json,sys;json.dump({'artifact_dir':'../runs','shared_db_src':'/private/tmp/shared-db-guard-r2/src','timeout_s':1500,'models':[{'id':'$lane-review-$L','provider':'$prov','model':'$model','availability':'available','reasoning_effort':'medium'}]},open('$m','w'),indent=2)"
  (cd "$WT" && PATH=/Applications/ChatGPT.app/Contents/Resources/codex-cli/bin:$PATH python3 scripts/research_model_benchmark.py --manifest "$m" --prompt "$V/per-sample/$L.txt")
  st=$(python3 -c "import json;print(json.load(open('$V/runs/$lane-review-$L/metadata.json'))['status'])")
  echo "LANE $lane $L $st"
  case $st in rate_limited|blocked_cooldown) echo "LANE $lane HALT after $L"; exit 2;; esac
done
