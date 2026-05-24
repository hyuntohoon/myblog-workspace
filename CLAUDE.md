# MyBlog + Music Review — Workspace

Meta-management layer for 5 microservice repos. Each service's code lives in its own repo with its own CLAUDE.md; this workspace owns cross-repo planning, contracts, and architecture.

## Layout

```
myblog-workspace/
├── myblog_backend/   ← user-facing API
├── myblog_front/     ← Astro 5 + React 19 client
├── myblog_music/     ← music review service
├── myblog_publish/   ← publishing pipeline
├── myblog_worker/    ← async SQS consumer (Spotify fetches live here)
└── docs/
    ├── architecture.md, plan.md
    ├── contracts/    ← SQS messages, service-to-service APIs
    ├── decisions/    ← ADRs
    ├── conventions/  ← git.md and other workflow standards
    └── agents.md     ← subagent + slash command catalog
```

When working inside one repo, that repo's CLAUDE.md takes precedence over this file.

## How to work here

- **Cross-repo change (≥2 repos)**: write/update `docs/plan.md` _before_ code. For contract changes, write the new contract in `docs/contracts/` first, then propagate.
- **Single-repo change**: defer to the repo's CLAUDE.md.
- **Conventions, git flow, agents**: see `docs/conventions/` and `docs/agents.md`. Read them when relevant; don't load preemptively.

## Hard rules (never violate)

- **Never work on `main`.** First command of any session: `git checkout -b <type>/<plan-id>-<desc>`. Branch/commit format in `docs/conventions/git.md`.
- **Never make `/search/unified` synchronously call Spotify.** That path is DB-only. Spotify access goes `candidates` → SQS → `myblog_worker`.
- **Never run a rollback migration against RDS directly.** Use each repo's migration tooling; rollbacks require human approval.
- **Never write secrets to any file in the repo** — no `.env`, `.env.*`, `secrets.yaml`, `config.local.json`, etc. Secrets go through AWS Secrets Manager or GitHub Actions Secrets only.

## Working rules

- AI may run `git add` and `git commit`. AI must wait for explicit human approval (e.g. "push" or "ok push") before `git push` or `git merge` — implicit agreement does not count.
- If scope expansion is needed, **stop and report**; do not silently expand.
- Never claim "fixed" / "works" / "done" without running a verification command _in this session_ and quoting the result.
- For any investigation spanning 3+ files or 2+ repos, delegate to a subagent instead of pulling everything into main context.
- Before delegating to any subagent, read `docs/agents.md` for triggers and the agent catalog.

## Plan format

`docs/plan.md` entries use this structure:

```
## PR-11: Add explicit_filter to /search/unified
- Scope: myblog_backend, myblog_front
- Order: backend contract → frontend consumer
- Rollback: feature flag, default off
- Verification: pytest tests/search/test_explicit_filter.py
- Status: in-progress
```

`<plan-id>` uses a categorical prefix + number (e.g. `PR-11`, `P0-2`, `BUG-4`, `ARCH-1`) and is also the branch name component: `feat/PR-11-explicit-filter`.
