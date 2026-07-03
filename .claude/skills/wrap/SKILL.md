---
name: wrap
description: Session wrap — verify repo states, report unfinished work, write the next-session prompt, then auto-spawn the next session in a new terminal window
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

## 4. Spawn the next session (one-shot)

Detect the environment and run exactly ONE of these:

- Inside tmux (`$TMUX` set):
  ```bash
  tmux new-window -c /Users/park_hyun/myblog-workspace 'claude "$(cat ~/.claude/myblog-next-session.md)"'
  ```
- iTerm2 (`$TERM_PROGRAM` = `iTerm.app`):
  ```bash
  osascript -e 'tell application "iTerm" to create window with default profile' \
            -e 'tell current session of current window of application "iTerm" to write text "cd /Users/park_hyun/myblog-workspace && claude \"$(cat ~/.claude/myblog-next-session.md)\""'
  ```
- Terminal.app (default):
  ```bash
  osascript -e 'tell application "Terminal" to do script "cd /Users/park_hyun/myblog-workspace && claude \"$(cat ~/.claude/myblog-next-session.md)\""' \
            -e 'tell application "Terminal" to activate'
  ```

The `$(cat …)` must reach the NEW shell unexpanded (single-quote the osascript args; escape inner quotes as `\"`), so the freshly written prompt is read at spawn time.

If the spawn fails (macOS automation consent denied, sandbox block): do NOT retry silently — print the exact one-line command for the user to paste into their shell, and say why it failed.

## 5. Final line

Tell the user: 새 창에서 다음 세션이 시작됐고, 이 세션은 닫아도 된다. (First-ever run may pop a macOS "Terminal을 제어하려고 합니다" consent — allow once, it's cached.)
