#!/usr/bin/env bash
# Usage: run_lane_resume.sh <input dir holding the dispatched (unredacted) inputs>.
# ROUND.md §10: the four missing Codex r2 runs, under -resume IDs, in the §5 r2 order.
set -u
R="$(cd "$(dirname "$0")" && pwd)"; W="$(cd "$R/../../../../../.." && pwd)"; I="$1"
export PATH=/Applications/ChatGPT.app/Contents/Resources/codex-cli/bin:$PATH
for combo in P0-gemini-rights-r2 P2-gemini-rights-r2 P0-2000-tape-r2 P2-2000-tape-r2; do
  p=${combo%%-*}; rest=${combo#*-}; a=${rest%-r?}; md="$R/runs/gx-$combo-resume/metadata.json"
  if [ -e "$R/runs/gx-$combo-resume" ]; then
    while python3 -c "import json,sys;sys.exit(json.load(open(sys.argv[1]))['status'] not in ('claimed','running'))" "$md" 2>/dev/null; do sleep 15; done
  else
    python3 "$W/scripts/research_model_benchmark.py" --manifest "$R/manifests/resume/$combo.json" \
      --prompt "$R/prompts/$p.md" --input "$I/$a.txt" --input "$I/run-block.txt" \
      --provider gpt >> "$R/dispatch-gpt.jsonl" 2>&1
  fi
  st=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['status'])" "$md" 2>/dev/null || echo missing)
  echo "gpt $combo-resume $st"
  case $st in rate_limited|blocked_cooldown) echo "gpt lane halted"; exit 2;; esac
done
