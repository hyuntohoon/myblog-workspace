# MyBlog + Music Review — Workspace

4 service repos + workspace. Each service deploys independently as AWS Lambda.
Per-repo CLAUDE.md removed — repo specifics live in code + each repo's README.

## Layout

myblog-workspace/
├── myblog_backend/ ← posts/categories/publish API → Lambda ratemymusic-api
├── myblog_front/ ← Astro 5 + React 19 → S3 + CloudFront
├── myblog_music/ ← DB-first music search → Lambda musicApi
├── myblog_worker/ ← SQS + EventBridge consumer → Lambda blogWorkerLambda
├── infra/ ← Terraform (canonical AWS state; see infra/README.md for identifiers)
├── docs/{plan.md,contracts/,rfcs/,archive/}
└── scripts/{smoke.sh,merge_openapi.py}

`_archive_myblog_publish/` — do not edit, do not deploy (absorbed into backend, ARCH-11).

## Service boundaries

- `/api/music/search/unified` is **DB-only**. Spotify access goes `candidates` → SQS → worker.
- Gemini/MusicBrainz alias fill runs from EventBridge, not SQS. Their outage must not block album sync.
- Backend ↔ music split exists so Spotify outage can't affect posts.

## Auth — two entry points

- **CloudFront → backend** (most routes): `edge_guard` checks `x-origin-verify: <EDGE_SECRET>`. Bypassed when `ENV=local|dev`. Bearer tokens skip this check.
- **API Gateway → backend** (`POST/PUT/DELETE /api/posts/*`, `POST /api/publish`): Cognito JWT at authorizer `6eia7l` before Lambda.
- **Local**: backend/music/worker bypass JWT when `ENV=local|dev`. Frontend on `localhost` uses dummy token `'local-dev'`; `isLoggedIn()` returns true.

## Hard rules

1. Never work on `main`. First command: `git checkout -b <type>/<plan-id>-<desc>`.
2. Never commit secrets. Use AWS Secrets Manager / GitHub Actions Secrets.
3. Never run rollback migrations against prod directly — human approval required.
4. Never run >1 RFC step per session unless RFC says parallel is OK.
5. Never self-promote RFC Status. `draft` → `accepted` is human-only.
6. Never `terraform apply -target=...` without explicit go-ahead. Always run full plan; stop on unexpected drift.
7. Never push or merge without explicit "push" / "ok push". `git add` + `commit` are fine.
8. Never skip git hooks (`--no-verify`, `--no-gpg-sign`) unless user says so.
9. Never add a synchronous Spotify call to a user-facing endpoint.

## Code conventions

Use `settings.*` (pydantic-settings), not `os.getenv()`. Use `logging.getLogger(__name__)`, not `print()`. Frontend authed requests go through `apiFetch` from `src/lib/api.ts`. Backend/music URLs always prefixed `/api`. Never log `GITHUB_TOKEN`, `DATABASE_URL`, `EDGE_SECRET`, Spotify creds.

## Workflow

**Branch**: `<type>/<plan-id>-<desc>` — type ∈ feat|fix|chore|refactor|docs|test|ci|db; plan-id from `docs/plan.md` (PR-N/BUG-N/ARCH-N); desc kebab-case 3–5 words. Plan-id can be omitted for ad-hoc docs/chore work not tracked in plan.md (e.g. `docs/claude-md-cleanup`).

**Commit**: Conventional Commits, lowercase imperative subject ≤72 chars. `Co-Authored-By: Claude` trailer when AI-authored.

**Cross-repo (≥2 repos)**: update `docs/plan.md` before code. API contract change → export `openapi.json` in service repo, commit in same PR; workspace merge regenerates `docs/contracts/openapi.json`; frontend types derived from merged spec (CI fails on drift).

**Multi-step migration**: write RFC in `docs/rfcs/`; plan.md row is one-line pointer.

**Flow**: branch → implement → local smoke → push + open PR (CI runs lint/typecheck/openapi-verify) → wait for explicit "push"/"ok push" → squash merge to `main` → deploy auto-triggers on push-to-main → prod smoke → quote prod smoke result in PR comment + update plan.md.

Deploy timing means prod smoke is **only possible post-merge**. Treat merge as mid-flow, not end-of-flow.

**Definition of Done** — split by when each item can be checked.

Pre-merge (block merge if unchecked):

- Tests pass (`pytest`, `pnpm lint`, `pnpm exec astro check`)
- `terraform plan` clean for affected stacks
- New/removed backend route → matching `infra/apigateway.tf` entry
- Contract change → `openapi.json` regenerated + committed
- Local smoke passes, result quoted in PR body

Post-merge (block claiming "done" if unchecked):

- Prod smoke passes after auto-deploy, result quoted in PR comment
- plan.md row dropped (history lives in `git log` + `docs/archive/done/`)

Never claim "done" before the post-merge items are green. If any item is unchecked, say so explicitly.

## Subagent triggers

| Trigger                               | Subagent                |
| ------------------------------------- | ----------------------- |
| Flow across 3+ files or 2+ repos      | `explorer`              |
| Change touches 2+ repos, needs plan   | `planner`               |
| Bug not isolated after 2 fix attempts | `debugger`              |
| Pytest cases / flaky tests            | `test-engineer`         |
| New service or cross-repo design      | `architect`             |
| Before pushing substantial PR         | `reviewer`              |
| UI change in `myblog_front`           | `frontend-design` skill |

Subagents producing code must run that repo's verification and quote the result.

## Pointers

- Infra identifiers (Pool IDs, ARNs, domains) → `infra/README.md`
- Local dev setup (ports, env vars, install) → each repo's README
- Smoke test usage (test user, password rotation) → `scripts/smoke.sh` header
- Schema change procedure → `docs/contracts/README.md`
- Historical decisions (incl. 2026-05-27 Cognito incident) → `docs/archive/decisions/`
- Completed PRs → `git log` (authoritative); `docs/archive/done/` for older summaries
