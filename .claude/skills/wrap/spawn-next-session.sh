#!/bin/bash
# /wrap 4단계 전용: 다음 세션을 새 터미널에서 "정확히 한 번" 띄운다.
# 락을 스폰 시도 전에 기록하므로, 부분 실패 후 재실행돼도 중복 스폰이 없다.
set -u

PROMPT_FILE="$HOME/.claude/myblog-next-session.md"
RUNNER="$HOME/.claude/skills/wrap/next-session-run.sh"
LOCK_DIR="$HOME/.claude/.wrap-spawn.lock"

if [ ! -f "$PROMPT_FILE" ]; then
  echo "ERROR: $PROMPT_FILE 이 없습니다. 3단계(next-session prompt 작성)를 먼저 하세요."
  exit 1
fi

# 멱등성: 프롬프트 파일 버전(mtime)당 스폰 1회
STAMP="$(stat -f %m "$PROMPT_FILE")"
if [ "$(cat "$LOCK_DIR/stamp" 2>/dev/null)" = "$STAMP" ]; then
  echo "ALREADY_SPAWNED: 이 프롬프트로 이미 새 세션을 띄웠습니다. 중복 방지로 아무것도 하지 않습니다."
  echo "정말 다시 띄우려면: rm -rf $LOCK_DIR && bash $0"
  exit 0
fi

# 락을 먼저 기록 — 아래 스폰이 어중간하게 실패해도 재실행 시 중복이 안 생긴다
mkdir -p "$LOCK_DIR" || { echo "ERROR: 락 생성 실패 ($LOCK_DIR). sandbox 없이 다시 실행하세요."; exit 1; }
echo "$STAMP" > "$LOCK_DIR/stamp"

MANUAL_CMD="bash $RUNNER"

if [ -n "${TMUX:-}" ]; then
  if tmux new-window -c /Users/park_hyun/myblog-workspace "bash $RUNNER"; then
    echo "OK: tmux 새 창에서 다음 세션 시작"
    exit 0
  fi
elif [ "${TERM_PROGRAM:-}" = "iTerm.app" ]; then
  if osascript >/dev/null \
    -e 'tell application "iTerm" to tell current window' \
    -e '  set newTab to (create tab with default profile)' \
    -e "  tell current session of newTab to write text \"bash $RUNNER\"" \
    -e 'end tell'; then
    echo "OK: iTerm 현재 창의 새 탭에서 다음 세션 시작"
    exit 0
  fi
else
  # Terminal.app은 스크립트로 탭을 직접 못 만들어서 Cmd+T 키 입력으로 연다 (손쉬운 사용 권한 필요)
  if osascript >/dev/null \
    -e 'tell application "Terminal" to activate' \
    -e 'tell application "System Events" to keystroke "t" using command down' \
    -e 'delay 0.4' \
    -e "tell application \"Terminal\" to do script \"bash $RUNNER\" in selected tab of front window"; then
    echo "OK: Terminal 현재 창의 새 탭에서 다음 세션 시작"
    exit 0
  fi
fi

# 여기 도달 = 스폰 실패. 절대 다른 방법으로 재시도하지 말 것 (창이 이미 떠 있을 수 있음).
echo "FAILED: 자동 스폰 실패 (자동화/손쉬운 사용 권한 거부 또는 sandbox 차단 가능성)."
echo "아래 한 줄을 직접 터미널에 붙여넣으세요:"
echo "  $MANUAL_CMD"
exit 1
