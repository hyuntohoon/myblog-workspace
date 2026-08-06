---
name: wrap
description: Verify MyBlog session completion, report unfinished work, prepare a focused next-thread prompt, and create the next Codex thread only when every chain gate is green. Use when AGENTS.md says a completed RFC step or concluded no-ship step must hand off automatically, or when the user explicitly asks to wrap the session.
---

# Wrap

Run the workflow without asking for confirmation only when the repository's standing chain rules authorize it. Use Korean for user-facing status. Do not broaden the authority granted by AGENTS.md.

## 1. Audit state

Check the workspace and each nested repository: myblog_backend, myblog_front, myblog_music, myblog_worker, and myblog_shared_db.

For each repository, read:

- status --porcelain
- current branch
- origin/main..HEAD commits
- open pull requests

For work merged this session, verify the post-merge Definition of Done:

- deployment completed
- production smoke passed
- the smoke result is quoted in a PR comment
- the docs/plan.md row was dropped

Read ~/.codex/myblog-rfc-chain.json if it exists.

## 2. Report

Summarize in Korean:

- what shipped or concluded
- uncommitted files, unpushed branches, and open PRs per repository
- missing Definition of Done items
- the single next item

If any required check is missing or red, stop after reporting it. Do not create a thread.

## 3. Decide whether chaining is allowed

Automatic chaining is allowed only for the immediate next step of the same accepted or in-progress RFC. Stop the chain when any condition below is true:

- ~/.codex/.wrap-chain-stop exists
- local verification, required PR CI, deployment, or production smoke is red or missing
- an unmerged PR would be a base for the next step
- the next step has an unresolved decision or conditional gate
- the next step needs terraform apply, a production rollback migration, or RFC status promotion
- the RFC status is not accepted or in-progress
- the current worktree contains foreign commits
- another live session is already doing the same RFC step
- no steps remain

A human-observation signal is not a stop condition when production smoke is green. Carry every unconfirmed observation into the next prompt and chain state.

Keep the chain state in ~/.codex/myblog-rfc-chain.json with rfc, current_step, total_steps, shipped, observations, status, and iteration. Cap automatic chains at eight iterations. Starting a different RFC resets iteration to zero. A stopped chain records stop_reason instead of deleting history.

## 4. Prepare one next-thread prompt

Write ~/.codex/myblog-next-session.md with these sections, omitting only sections that truly do not apply:

- title naming one RFC step or one task
- one-sentence objective and RFC link
- shipped steps and carried observations
- current short SHA for all six repositories
- expected clean branches and open PR count
- actual cautions from this session
- exact files or memories to load
- tasks explicitly out of scope
- starting rule

Put only one task at the top. When an owner decision is required, do not create the next thread; save the prompt and ask in the current thread.

For an automatic RFC chain, the starting rule must require the new thread to:

1. Run .agents/skills/wrap/scripts/session-claim.sh before touching git.
2. Compare the recorded baseline when using the shared checkout.
3. Use isolated worktrees from origin/main when the shared checkout is busy.
4. Complete one RFC step only.
5. Run the full pre-merge and post-merge Definition of Done.
6. Stop on any owner-only decision.
7. Invoke this skill again only after the step reaches a valid conclusion.

## 5. Create the next Codex thread exactly once

Before claiming thread management is unavailable, search for the current create_thread capability. Create a new user-owned Codex thread in this workspace with the prepared prompt. Do not use terminal automation, osascript, tmux, the Claude CLI, or a self-referential Codex MCP server.

Call create_thread exactly once. Never retry after a partial or ambiguous failure because the first call may already have created the thread.

After success:

1. Record the returned thread identifiers.
2. Increment the chain iteration when chaining.
3. Run .agents/skills/wrap/scripts/session-claim.sh retire.
4. Make no further git or file changes in the retired thread.
5. Include the required created-thread directive in the final response.

If the tool is unavailable or fails, leave the prompt file in place, report the exact failure, and do not improvise another spawn path.

## 6. Final response

Tell the user whether a next thread was created, which RFC step it owns, and that this thread is retired. If the chain stopped, name the single blocking condition and leave the current thread active.
