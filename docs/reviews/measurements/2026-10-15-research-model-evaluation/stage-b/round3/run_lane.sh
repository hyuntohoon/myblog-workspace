#!/usr/bin/env bash
# Usage: run_lane.sh <claude|gpt> <input dir holding the dispatched (unredacted) inputs>.
# Serial lane in the ROUND.md §4 order; stops on throttle; never redispatches a claimed run ID.
set -u
R="$(cd "$(dirname "$0")" && pwd)"; W="$(cd "$R/../../../../../.." && pwd)"; I="$2"
export PATH=/Applications/ChatGPT.app/Contents/Resources/codex-cli/bin:$PATH
pre=gx; [ "$1" = claude ] && pre=cl
for combo in P3-gemini-rights-r1 P3G-gemini-rights-r1 P0-gemini-rights-r1 \
             P0-gemini-rights-r2 P3G-gemini-rights-r2 P3-gemini-rights-r2; do
  p=${combo%%-*}; md="$R/runs/$pre-$combo/metadata.json"
  inputs=(--input "$I/gemini-rights.txt")
  [ "$p" = P3G ] && inputs+=(--input "$I/gemini-annotations.txt")
  inputs+=(--input "$I/run-block.txt")
  if [ -e "$R/runs/$pre-$combo" ]; then
    while python3 -c "import json,sys;sys.exit(json.load(open(sys.argv[1]))['status'] not in ('claimed','running'))" "$md" 2>/dev/null; do sleep 15; done
  else
    python3 "$W/scripts/research_model_benchmark.py" --manifest "$R/manifests/$combo.json" \
      --prompt "$R/prompts/$p.md" "${inputs[@]}" \
      --provider "$1" >> "$R/dispatch-$1.jsonl" 2>&1
  fi
  st=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['status'])" "$md" 2>/dev/null || echo missing)
  echo "$1 $combo $st"
  case $st in rate_limited|blocked_cooldown) echo "$1 lane halted"; exit 2;; esac
done
