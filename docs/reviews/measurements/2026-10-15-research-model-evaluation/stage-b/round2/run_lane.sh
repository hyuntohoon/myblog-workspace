#!/usr/bin/env bash
# Usage: run_lane.sh <claude|gpt> <input dir holding the dispatched (unredacted) inputs>.
# Serial lane in the ROUND.md §5 order; stops on throttle; never redispatches a claimed run ID.
set -u
R="$(cd "$(dirname "$0")" && pwd)"; W="$(cd "$R/../../../../../.." && pwd)"; I="$2"
export PATH=/Applications/ChatGPT.app/Contents/Resources/codex-cli/bin:$PATH
pre=gx; [ "$1" = claude ] && pre=cl
for combo in P2-gemini-rights-r1 P0-gemini-rights-r1 P2-2000-tape-r1 P0-2000-tape-r1 \
             P0-gemini-rights-r2 P2-gemini-rights-r2 P0-2000-tape-r2 P2-2000-tape-r2; do
  p=${combo%%-*}; rest=${combo#*-}; a=${rest%-r?}; md="$R/runs/$pre-$combo/metadata.json"
  if [ -e "$R/runs/$pre-$combo" ]; then
    while python3 -c "import json,sys;sys.exit(json.load(open(sys.argv[1]))['status'] not in ('claimed','running'))" "$md" 2>/dev/null; do sleep 15; done
  else
    python3 "$W/scripts/research_model_benchmark.py" --manifest "$R/manifests/$combo.json" \
      --prompt "$R/prompts/$p.md" --input "$I/$a.txt" --input "$I/run-block.txt" \
      --provider "$1" >> "$R/dispatch-$1.jsonl" 2>&1
  fi
  st=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['status'])" "$md" 2>/dev/null || echo missing)
  echo "$1 $combo $st"
  case $st in rate_limited|blocked_cooldown) echo "$1 lane halted"; exit 2;; esac
done
