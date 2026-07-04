#!/bin/bash
# /wrap이 띄운 새 터미널에서 실행되는 러너. 프롬프트 파일을 읽어 claude를 시작한다.
cd /Users/park_hyun/myblog-workspace || exit 1
exec claude --dangerously-skip-permissions "$(cat "$HOME/.claude/myblog-next-session.md")"
