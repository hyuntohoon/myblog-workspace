#!/usr/bin/env bash
# Usage: run_review_lane.sh <astra|claude> <label>...  One dispatch per label, serial; no retries;
# halts the lane on rate_limited / blocked_cooldown. Claimed labels are skipped, never redispatched.
set -u
lane=$1; shift
R="$(cd "$(dirname "$0")" && pwd)"; W="$(cd "$R/../../../../../.." && pwd)"
export PATH=/Applications/ChatGPT.app/Contents/Resources/codex-cli/bin:$PATH
if [ "$lane" = astra ]; then prov=gpt; model=gpt-6-astra; else prov=claude; model=claude-opus-5-5; fi
mkdir -p "$R/review/manifests"
for L in "$@"; do
  id=$lane-review-$L; m="$R/review/manifests/$id.json"
  if [ ! -e "$R/review/runs/$id" ]; then
    python3 -c "import json,sys;json.dump({'artifact_dir':'../runs','shared_db_src':'/private/tmp/claude-502/-Users-park-hyun-myblog-workspace/d3325964-1e58-48ce-b608-d08f7ff9fb77/scratchpad/shared-db-guard/src','timeout_s':1500,'models':[{'id':sys.argv[2],'provider':sys.argv[3],'model':sys.argv[4],'availability':'available','reasoning_effort':'medium'}]},open(sys.argv[1],'w'),indent=2)" "$m" "$id" "$prov" "$model"
    python3 "$W/scripts/research_model_benchmark.py" --manifest "$m" --prompt "$R/review/inputs/$L.txt" >> "$R/review/dispatch-$lane.jsonl" 2>&1
  fi
  st=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['status'])" "$R/review/runs/$id/metadata.json" 2>/dev/null || echo missing)
  echo "$lane $L $st"
  case $st in rate_limited|blocked_cooldown) echo "$lane lane halted"; exit 2;; esac
done
