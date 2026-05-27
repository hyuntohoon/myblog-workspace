# MyBlog + Music Review — Workspace

Meta-management layer for 4 microservice repos. Each service's code lives in its own repo with its own CLAUDE.md; this workspace owns cross-repo planning, contracts, and architecture.

## Layout

```
myblog-workspace/
├── myblog_backend/   ← user-facing API + publishing (absorbed from myblog_publish, ARCH-11)
├── myblog_front/     ← Astro 5 + React 19 client
├── myblog_music/     ← music review service
├── myblog_worker/    ← async SQS consumer (Spotify fetches live here)
└── docs/
    ├── architecture.md      ← service responsibilities + flow (stable)
    ├── infrastructure.md    ← concrete resource IDs, ARNs, URLs
    ├── plan.md              ← active + upcoming work (one-line rows)
    ├── rfcs/                ← multi-step migrations, long-form
    ├── done/                ← completed work, archived per month
    │   └── rfcs/            ← completed RFCs
    ├── contracts/           ← SQS messages, service-to-service APIs, canonical schema
    ├── decisions/           ← ADRs
    ├── conventions/         ← git.md and other workflow standards
    └── agents.md            ← subagent + slash command catalog
```

When working inside one repo, that repo's CLAUDE.md takes precedence over this file. When the Layout above and the actual filesystem disagree, the filesystem wins — flag the drift.

## How to work here

- **Cross-repo change (≥2 repos)**: write/update `docs/plan.md` _before_ code. For contract changes, write the new contract in `docs/contracts/` first, then propagate.
- **Multi-step migration (2+ repos OR multi-day OR ordered PRs)**: write an RFC in `docs/rfcs/` first; `plan.md` row is a one-line pointer. See `docs/rfcs/README.md` for the format, Status lifecycle (`draft` → `accepted` → `in-progress (Step N)` → `done`), and Claude Code usage patterns.
- **Single-repo change**: defer to the repo's CLAUDE.md.
- **Looking up a completed PR**: check `docs/done/YYYY-MM.md` or git log; do not search plan.md for history.
- **Conventions, git flow, agents**: see `docs/conventions/` and `docs/agents.md`. Read them when relevant; don't load preemptively.

## Hard rules (never violate)

- **Never work on `main`.** First command of any session: `git checkout -b <type>/<plan-id>-<desc>`. Branch/commit format in `docs/conventions/git.md`.
- **Never make `/search/unified` synchronously call Spotify.** That path is DB-only. Spotify access goes `candidates` → SQS → `myblog_worker`.
- **Never run a rollback migration against the production database (Neon) directly.** Use each repo's migration tooling; rollbacks require human approval.
- **Never write secrets to any file in the repo** — no `.env`, `.env.*`, `secrets.yaml`, `config.local.json`, etc. Secrets go through AWS Secrets Manager or GitHub Actions Secrets only.
- **Never execute more than one RFC step per session unless the RFC explicitly says steps can run in parallel.** Step boundaries exist for verification + rollback; collapsing them defeats the purpose.
- **Never self-promote an RFC's Status.** `draft` → `accepted` is a human-only transition (human says "accepted"). AI can move `accepted` → `in-progress (Step N)` and bump N, but only after a step's verification passes.

## Working rules

- AI may run `git add` and `git commit`. AI must wait for explicit human approval (e.g. "push" or "ok push") before `git push` or `git merge` — implicit agreement does not count.
- If scope expansion is needed, **stop and report**; do not silently expand.
- Never claim "fixed" / "works" / "done" without running a verification command _in this session_ and quoting the result.
- For any investigation spanning 3+ files or 2+ repos, delegate to a subagent instead of pulling everything into main context.
- Before delegating to any subagent, read `docs/agents.md` for triggers and the agent catalog.
- When working from an RFC, the RFC's `Status` line is authoritative for "where are we"; update it as a step completes (in the same commit that completes the step). Open questions belonging to an in-flight RFC live in that RFC, not in `plan.md`.

## Plan format

`docs/plan.md` entries use this structure. `Rollback` is optional for low-risk items (<1h, single-file). `Verification` is required for anything that ships. For items with an RFC, the row is just a pointer.

```
## PR-11: Add explicit_filter to /search/unified
- Scope: myblog_backend, myblog_front
- Order: backend contract → frontend consumer
- Rollback: feature flag, default off          # optional
- Verification: pytest tests/search/test_explicit_filter.py
- Status: in-progress
```

RFC-backed row:
```
## ARCH-6: Shared DB models package
- RFC: docs/rfcs/ARCH-6-shared-db-package.md
- Status: accepted
```

`<plan-id>` uses a categorical prefix + number (e.g. `PR-11`, `P0-2`, `BUG-4`, `ARCH-1`) and is also the branch name component: `feat/PR-11-explicit-filter`.

When an item moves to `Status: done`, cut it from `plan.md` and append to `docs/done/YYYY-MM.md` (current month) with the merge SHA and date. For RFC-backed items, also move the RFC file to `docs/done/rfcs/`.
