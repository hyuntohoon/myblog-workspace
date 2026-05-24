# Subagents and Slash Commands

This file is loaded on-demand. CLAUDE.md tells agents to read it when investigation spans 3+ files or 2+ repos, when a bug isn't isolated after the second failed attempt, or before pushing a PR.

## When to delegate

Subagents preserve main context. Triggers are behavior-based, not time-based:

| Trigger                                                     | Subagent                                           |
| ----------------------------------------------------------- | -------------------------------------------------- |
| Tracing a flow across 3+ files or 2+ repos                  | `explorer`                                         |
| Change touches 2+ repos                                     | `planner` (output → `docs/plan.md`)                |
| Bug not isolated after 2 failed fix attempts                | `debugger`                                         |
| Writing pytest cases or fixing flaky tests                  | `test-engineer`                                    |
| Adding a new service or making a cross-repo design decision | `architect` (writes `docs/architecture-review.md`) |
| Before pushing a PR branch                                  | `reviewer` (fix issues locally before push)        |
| Working in `myblog_front`                                   | invoke `frontend-design` skill                     |

## Slash commands

- **/code-review**: run _after_ push. 4 parallel agents (CLAUDE.md compliance ×2, bug detection, git blame context) → posts GitHub comment with issues scoring ≥80 confidence.

## reviewer vs /code-review

- `reviewer` = before push, fix locally
- `/code-review` = after push, GitHub comment

For important PRs use both in sequence.

## Reporting during multi-file work

Report one line per file as you complete each. For changes touching >10 files, group by directory or concern instead of per-file.

## On verification

Every subagent that produces code must run the repo's verification command (defined in that repo's CLAUDE.md, typically `pytest` or `npm test`) and quote the result in its return. No "done" without evidence.
