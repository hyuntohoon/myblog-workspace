#!/usr/bin/env bash
# Usage: run_comparative.sh <astra|claude>  One comparative-calibration dispatch (ROUND.md §6); no retries.
set -u
lane=$1
R="$(cd "$(dirname "$0")/.." && pwd)"; W="$(cd "$R/../../../../../.." && pwd)"
export PATH=/Applications/ChatGPT.app/Contents/Resources/codex-cli/bin:$PATH
if [ "$lane" = astra ]; then prov=gpt; model=gpt-6-astra; else prov=claude; model=claude-opus-5-5; fi
id=$lane-comparative; m="$R/review/manifests/$id.json"
[ -e "$R/review/runs/$id" ] && { echo "$id already claimed"; exit 0; }
python3 -c "import json,sys;json.dump({'artifact_dir':'../runs','shared_db_src':sys.argv[5],'timeout_s':1500,'models':[{'id':sys.argv[2],'provider':sys.argv[3],'model':sys.argv[4],'availability':'available','reasoning_effort':'medium'}]},open(sys.argv[1],'w'),indent=2)" "$m" "$id" "$prov" "$model" "$HOME/.local/share/myblog-research/shared-db-guard/src"
python3 "$W/scripts/research_model_benchmark.py" --manifest "$m" --prompt "$R/review/comparative/$lane.txt" >> "$R/review/dispatch-$lane-comparative.jsonl" 2>&1
python3 -c "import json,sys;print(sys.argv[2], json.load(open(sys.argv[1]))['status'])" "$R/review/runs/$id/metadata.json" "$id"
