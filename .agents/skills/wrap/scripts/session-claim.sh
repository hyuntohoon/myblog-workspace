#!/usr/bin/env bash
# Coordinate shared-checkout ownership across Codex threads and legacy Claude sessions.
set -euo pipefail

WORKSPACE="/Users/park_hyun/myblog-workspace"
CLAIMS="${CODEX_HOME:-$HOME/.codex}/myblog-session-claims"
LOCK="$CLAIMS/.lock"
MODE="${1:-claim}"
THREAD_ID="${CODEX_THREAD_ID:-}"

valid_id() {
  [[ "$1" =~ ^[A-Za-z0-9._-]+$ ]]
}

require_thread_id() {
  if [ -z "$THREAD_ID" ] || ! valid_id "$THREAD_ID"; then
    echo "ERROR: CODEX_THREAD_ID is missing or invalid; refusing an ambiguous checkout claim."
    exit 2
  fi
}

acquire_lock() {
  mkdir -p "$CLAIMS"
  local attempt=0
  until mkdir "$LOCK" 2>/dev/null; do
    attempt=$((attempt + 1))
    if [ "$attempt" -ge 40 ]; then
      echo "ERROR: session claim lock is busy."
      exit 2
    fi
    sleep 0.05
  done
  trap 'rmdir "$LOCK" 2>/dev/null || true' EXIT
}

legacy_claude_sessions() {
  ps -axo pid=,comm= | while read -r pid comm; do
    [ "${comm##*/}" = "claude" ] || continue
    cwd=$(lsof -a -p "$pid" -d cwd -Fn 2>/dev/null | sed -n 's/^n//p' | head -1)
    case "$cwd" in "$WORKSPACE"*) echo "$pid" ;; esac
  done
}

list_codex_claims() {
  find "$CLAIMS" -maxdepth 1 -type f -print 2>/dev/null | while read -r file; do
    basename "$file"
  done
}

case "$MODE" in
  claim)
    require_thread_id
    acquire_lock
    if [ -f "$CLAIMS/$THREAD_ID" ]; then
      echo "OK: this Codex thread already owns the shared checkout ($THREAD_ID)"
      exit 0
    fi

    peers=""
    for id in $(list_codex_claims); do
      [ "$id" = "$THREAD_ID" ] && continue
      peers="$peers $id"
    done
    legacy=""
    for pid in $(legacy_claude_sessions); do
      legacy="$legacy $pid"
    done

    if [ -n "${peers// /}" ] || [ -n "${legacy// /}" ]; then
      echo "BUSY: another live session owns or may be using the shared checkout."
      for id in $peers; do echo "  codex thread $id"; done
      for pid in $legacy; do echo "  legacy claude pid $pid"; done
      echo "Use an isolated worktree from origin/main. Stop only if a peer is doing the same RFC step."
      echo "If a listed Codex thread is known dead: bash .agents/skills/wrap/scripts/session-claim.sh retire <thread-id>"
      exit 1
    fi

    {
      printf 'thread_id=%s\n' "$THREAD_ID"
      printf 'claimed_at=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
      printf 'cwd=%s\n' "$PWD"
    } > "$CLAIMS/$THREAD_ID"
    echo "OK: shared checkout claimed by Codex thread $THREAD_ID"
    ;;

  retire)
    shift || true
    acquire_lock
    targets="$*"
    if [ -z "$targets" ]; then
      require_thread_id
      targets="$THREAD_ID"
    fi
    for id in $targets; do
      if ! valid_id "$id"; then
        echo "ERROR: invalid thread id: $id"
        exit 2
      fi
      rm -f "$CLAIMS/$id"
      echo "RETIRED: Codex thread $id"
    done
    ;;

  list)
    mkdir -p "$CLAIMS"
    for id in $(list_codex_claims); do
      echo "codex thread $id"
    done
    for pid in $(legacy_claude_sessions); do
      echo "legacy claude pid $pid"
    done
    ;;

  *)
    echo "usage: session-claim.sh [claim|retire [thread-id...]|list]"
    exit 2
    ;;
esac
