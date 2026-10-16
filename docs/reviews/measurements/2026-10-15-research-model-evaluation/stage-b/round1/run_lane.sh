#!/usr/bin/env bash
# Usage: run_lane.sh <claude|gpt>. Serial lane in the ROUND.md §5 order; stops on throttle.
set -u
R="$(cd "$(dirname "$0")" && pwd)"; W="$(cd "$R/../../../../../.." && pwd)"
export PATH=/Applications/ChatGPT.app/Contents/Resources/codex-cli/bin:$PATH
pre=gx; [ "$1" = claude ] && pre=cl
for combo in P1-gemini-rights P0-gemini-rights P1-2000-tape P0-2000-tape; do
  p=${combo%%-*}; a=${combo#*-}; md="$R/runs/$pre-$combo/metadata.json"
  # Resume: a claimed run is never redispatched; wait for an in-flight one to finish.
  if [ -e "$R/runs/$pre-$combo" ]; then
    while python3 -c "import json,sys;sys.exit(json.load(open(sys.argv[1]))['status'] not in ('claimed','running'))" "$md" 2>/dev/null; do sleep 15; done
  else
  python3 "$W/scripts/research_model_benchmark.py" --manifest "$R/manifests/$combo.json" \
    --prompt "$R/prompts/$p.md" --input "$R/inputs/$a.txt" --input "$R/inputs/run-block.txt" \
    --provider "$1" >> "$R/dispatch-$1.jsonl" 2>&1
  fi
  st=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['status'])" "$md" 2>/dev/null || echo missing)
  echo "$1 $combo $st"
  case $st in rate_limited|blocked_cooldown) echo "$1 lane halted"; exit 2;; esac
done
