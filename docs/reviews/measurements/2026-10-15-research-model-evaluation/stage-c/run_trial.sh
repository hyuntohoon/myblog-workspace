#!/usr/bin/env bash
# Usage: run_trial.sh generate <input dir> <slug>   — one P6 generation (TRIAL.md §3)
#        run_trial.sh check <slug>                  — one model check (TRIAL.md §6); refuses unless
#                                                     owner/<slug>.md is committed (TRIAL.md §4 step 2)
# Serial, no retries; a claimed run ID is never redispatched.
set -u
mode=$1; R="$(cd "$(dirname "$0")" && pwd)"; W="$(cd "$R/../../../../.." && pwd)"
G="$HOME/.local/share/myblog-research/shared-db-guard/src"
case $mode in
  generate)
    I=$2; s=$3; id=cl-P6-$s
    [ -e "$R/runs/$id" ] && { echo "$id already claimed"; exit 1; }
    python3 "$W/scripts/research_model_benchmark.py" --manifest "$R/manifests/P6-$s.json" \
      --prompt "$R/prompts/P6.md" --input "$I/$s.txt" --input "$I/run-block.txt" \
      --provider claude >> "$R/dispatch.jsonl" 2>&1
    md="$R/runs/$id/metadata.json";;
  check)
    s=$2; id=claude-check-$s
    git -C "$R" ls-files --error-unmatch "owner/$s.md" >/dev/null 2>&1 \
      || { echo "owner/$s.md is not committed; the owner's task comes first (TRIAL.md §4)"; exit 1; }
    git -C "$R" diff --quiet HEAD -- "owner/$s.md" || { echo "owner/$s.md has uncommitted edits"; exit 1; }
    [ -e "$R/check/runs/$id" ] && { echo "$id already claimed"; exit 1; }
    m="$R/check/manifests/$id.json"; mkdir -p "$R/check/manifests"
    python3 -c "import json,sys;json.dump({'artifact_dir':'../runs','shared_db_src':sys.argv[3],'timeout_s':1500,'models':[{'id':sys.argv[2],'provider':'claude','model':'claude-opus-5-5','availability':'available','reasoning_effort':'medium','web_search':True}]},open(sys.argv[1],'w'),indent=2)" "$m" "$id" "$G"
    python3 "$W/scripts/research_model_benchmark.py" --manifest "$m" --prompt "$R/check/inputs/$s.txt" \
      >> "$R/check/dispatch.jsonl" 2>&1
    md="$R/check/runs/$id/metadata.json";;
  *) echo "usage: run_trial.sh generate <input dir> <slug> | check <slug>"; exit 2;;
esac
st=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['status'])" "$md" 2>/dev/null || echo missing)
echo "$id $st"
