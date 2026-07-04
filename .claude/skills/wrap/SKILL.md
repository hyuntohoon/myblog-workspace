---
name: wrap
description: Session wrap — verify repo states, report unfinished work, write the next-session prompt, then auto-spawn the next session in a new tab of the current terminal window
disable-model-invocation: true
---

# /wrap — session wrap + one-shot handoff

Run every step without asking for confirmation. All user-facing output in Korean.

## 1. State check (workspace + all nested repos)

For the workspace and each of `myblog_backend`, `myblog_front`, `myblog_music`, `myblog_worker`, `myblog_shared_db` (use `git -C` absolute paths — cwd resets per Bash call):

- `git -C <repo> status --porcelain` — uncommitted / untracked work
- `git -C <repo> branch --show-current` + `git -C <repo> log --oneline origin/main..HEAD` — unpushed commits
- `gh pr list --repo <owner>/<repo> --state open` — unmerged PRs

Also check post-merge DoD leftovers for anything merged this session: prod smoke result quoted in a PR comment, and the `docs/plan.md` row dropped.

## 2. Wrap report (Korean)

Summarize: what shipped this session; per-repo unpushed branches + uncommitted files; open PRs; missing DoD items; and the single most important NEXT item (from `docs/plan.md` Active).

## 3. Next-session prompt

Write `~/.claude/myblog-next-session.md`, under 30 lines:

- 2–3 sentence context recap (what just finished, what state the repos are in)
- explicit task list for the next session, most important first
- pointers: the plan.md row / RFC path / memory names the next session should load
- MANDATORY final block — approval gate. The prompt must end with this instruction (verbatim, Korean), so the new session briefs first and only works after the user picks an option:

  ```
  ## 시작 규칙 (반드시 지킬 것)
  위 작업을 바로 시작하지 마라. 먼저:
  1. 위 작업 목록을 읽고, 각 작업을 무엇을/왜/어떻게 할지 한두 줄로 정리해 보여줘라.
  2. AskUserQuestion 도구로 "어떤 작업부터 시작할까요?"를 물어라 — 선택지는 위 작업들(+ "다른 것 먼저"), 추천 항목을 1번에 둬라.
  3. 사용자가 선택한 뒤에만 실제 작업을 시작해라. 선택 전에는 파일 수정/커밋/실행 금지.
  ```

## 4. Spawn the next session (one-shot)

Run this EXACTLY ONCE, sandbox disabled (osascript automation needs it):

```bash
bash ~/.claude/skills/wrap/spawn-next-session.sh
```

The script opens a new TAB in the current terminal window (tmux window / iTerm tab / Terminal.app Cmd+T), starts `claude --dangerously-skip-permissions` with the prompt, and is idempotent: it writes a lock (`~/.claude/.wrap-spawn.lock`) keyed to the prompt file BEFORE spawning, so re-running it can never open a second tab for the same prompt.

HARD RULES — these prevent the duplicate-terminal bug:
- Call the script exactly once per wrap. NEVER retry it, even if it errors — a window may already be open despite the error.
- NEVER hand-compose tmux/osascript spawn commands yourself; the script is the only spawn path.
- `ALREADY_SPAWNED` output means a session is already up — report that and stop.
- `FAILED` output: relay the script's manual one-line command to the user verbatim, say why it failed, and stop.

## 5. Final line

Tell the user: 같은 창의 새 탭에서 다음 세션이 시작됐고, 이 탭은 닫아도 된다. (First-ever run may pop macOS consent dialogs — 자동화(Terminal/iTerm 제어) and, for Terminal.app's Cmd+T keystroke, 손쉬운 사용(Accessibility) — allow once, it's cached.)
