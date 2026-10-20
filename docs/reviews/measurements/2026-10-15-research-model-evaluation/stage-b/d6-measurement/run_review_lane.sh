#!/usr/bin/env bash
# Usage: run_review_lane.sh <label>...  D6 instrument check (CHECK.md §4): Claude reviewer only, same
# model/effort/web settings as round 5. One dispatch per label, serial; no retries; halts on
# rate_limited / blocked_cooldown. Claimed labels are skipped, never redispatched.
set -u
R="$(cd "$(dirname "$0")" && pwd)"; W="$(cd "$R/../../../../../.." && pwd)"
mkdir -p "$R/review/manifests"
for L in "$@"; do
  id=claude-review-$L; m="$R/review/manifests/$id.json"
  if [ ! -e "$R/review/runs/$id" ]; then
    python3 -c "import json,sys;json.dump({'artifact_dir':'../runs','shared_db_src':sys.argv[2],'timeout_s':1500,'models':[{'id':sys.argv[3],'provider':'claude','model':'claude-opus-5-5','availability':'available','reasoning_effort':'medium','web_search':True}]},open(sys.argv[1],'w'),indent=2)" "$m" "$HOME/.local/share/myblog-research/shared-db-guard/src" "$id"
    python3 "$W/scripts/research_model_benchmark.py" --manifest "$m" --prompt "$R/review/inputs/$L.txt" >> "$R/review/dispatch-claude.jsonl" 2>&1
  fi
  st=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['status'])" "$R/review/runs/$id/metadata.json" 2>/dev/null || echo missing)
  echo "claude $L $st"
  case $st in rate_limited|blocked_cooldown) echo "claude lane halted"; exit 2;; esac
done
