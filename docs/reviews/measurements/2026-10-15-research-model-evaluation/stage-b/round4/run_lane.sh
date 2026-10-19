#!/usr/bin/env bash
# Usage: run_lane.sh <input dir holding the dispatched (unredacted) inputs>.
# Round 4 (ROUND.md §4): Claude CLI lane only, serial, counterbalanced order; stops on throttle;
# never redispatches a claimed run ID.
set -u
R="$(cd "$(dirname "$0")" && pwd)"; W="$(cd "$R/../../../../../.." && pwd)"; I="$1"
for combo in P4-gemini-rights-r1 P0-gemini-rights-r1 P0-gemini-rights-r2 \
             P4-gemini-rights-r2 P0-gemini-rights-r3 P4-gemini-rights-r3; do
  p=${combo%%-*}; md="$R/runs/cl-$combo/metadata.json"
  if [ -e "$R/runs/cl-$combo" ]; then
    while python3 -c "import json,sys;sys.exit(json.load(open(sys.argv[1]))['status'] not in ('claimed','running'))" "$md" 2>/dev/null; do sleep 15; done
  else
    python3 "$W/scripts/research_model_benchmark.py" --manifest "$R/manifests/$combo.json" \
      --prompt "$R/prompts/$p.md" --input "$I/gemini-rights.txt" --input "$I/run-block.txt" \
      --provider claude >> "$R/dispatch-claude.jsonl" 2>&1
  fi
  st=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['status'])" "$md" 2>/dev/null || echo missing)
  echo "claude $combo $st"
  case $st in rate_limited|blocked_cooldown) echo "claude lane halted"; exit 2;; esac
done
