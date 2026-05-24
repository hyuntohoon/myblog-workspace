# MyBlog + Music Review — Workspace

## Purpose

This workspace is the **meta-management layer** for five microservice repos. Individual service code lives in each repo; this workspace manages cross-repo planning, contracts, architecture documentation, and decision records.

```
myblog-workspace/
├── myblog_backend/    ← each repo has its own CLAUDE.md (or will)
├── myblog_front/
├── myblog_music/
├── myblog_publish/
├── myblog_worker/
└── docs/
    ├── architecture.md       ← system-wide architecture
    ├── plan.md               ← cross-repo work plan (start here)
    ├── conventions/          ← coding and workflow standards
    ├── decisions/            ← architectural decision records (ADRs)
    └── contracts/            ← SQS message formats, API contracts
```

## Per-Repo CLAUDE.md

Each repo (`myblog_backend`, `myblog_front`, `myblog_music`, `myblog_publish`, `myblog_worker`) has or will have its own CLAUDE.md with service-specific guidance. When working inside a single repo, defer to that repo's CLAUDE.md first.

## Cross-Repo Work

Any change that spans two or more repos (API contract changes, schema changes, shared infrastructure) must go through `docs/plan.md`.

- Before starting: record scope, order, and rollback approach in `docs/plan.md`.
- For contract changes: write the new/updated contract in `docs/contracts/` first, then propagate to each repo.

## Document Locations

| Document type                    | Location                  |
| -------------------------------- | ------------------------- |
| System architecture              | `docs/architecture.md`    |
| Cross-repo work plan             | `docs/plan.md`            |
| Architectural decisions (ADRs)   | `docs/decisions/`         |
| SQS message formats              | `docs/contracts/`         |
| Service-to-service API contracts | `docs/contracts/`         |
| Git workflow and conventions     | `docs/conventions/git.md` |
| Service-specific guides          | Each repo's `CLAUDE.md`   |

## Git Workflow

See `docs/conventions/git.md` for commit format, branch naming, and PR flow.

## Work Rules

- Always create a new branch before any code change: `git checkout -b <type>/<plan-id>-<desc>`
- The AI may run `git add` and `git commit`. The AI must ask for explicit approval before running `git push` or `git merge`.
- During multi-file work, report changes one line per file as you complete each.
- If you discover changes needed outside the stated scope, stop and report. Do not silently expand scope.
- See `docs/conventions/git.md` for commit message format and PR flow.
- See `docs/decisions/` for architectural decision records.
- Never claim "fixed" / "works" / "done" without running the verification command in this session. State the evidence (test output, command result) explicitly.

## Hard Rules

- **Never work directly on `main`** — all changes go on a branch. The first command of any work session must be `git checkout -b <type>/<plan-id>-<short-desc>`. See `docs/conventions/git.md` for naming rules.
- **Never run a rollback migration directly against RDS** — migrations must go through each repo's migration tooling; rollbacks require human review and manual approval.
- **Never add a synchronous Spotify API call to the user-facing search path** — `/search/unified` must remain DB-only. Spotify calls go through the async path only: `candidates` → SQS → Worker.
- **Never commit `.env` files** — no `.env`, `.env.local`, or `.env.*` in any repo. Secrets are managed via AWS Secrets Manager or GitHub Actions Secrets.

## Agent Delegation

Subagents preserve main context. Use them proactively:

- **explorer**: When understanding a cross-repo flow requires reading 3+ files. Especially for tracing SQS message paths across repos.
- **planner**: For any change touching 2+ repos. Output goes into `docs/plan.md`.
- **debugger**: When a bug isn't isolated within ~15 min. Hand off the failing test or error.
- **test-engineer**: When writing pytest cases or fixing flaky tests.
- **reviewer**: Before pushing a PR branch. Runs myblog-specific checklist (contract violations, idempotency, secret leaks, conventions). Fix issues found here, then push.
- **architect**: For system-level structural evaluation — module boundaries, dependency direction, responsibility separation across the 5-repo system. Writes to `docs/architecture-review.md`. Use when adding a new service or making a cross-repo design decision.
- **/code-review**: After pushing a PR branch. Runs 4 parallel agents (CLAUDE.md compliance ×2, bug detection, git blame context), scores each issue 0–100, posts GitHub comment with issues ≥80 confidence.
- **frontend-design plugin**: Auto-applied when working in `myblog_front`. No explicit invocation needed — enhances frontend output with production-grade aesthetics automatically.

**reviewer vs /code-review**: `reviewer` runs *before* push (fix locally), `/code-review` runs *after* push (GitHub comment). Use both in sequence for important PRs.

Do not handle multi-repo investigation in the main context — delegate to explorer.
