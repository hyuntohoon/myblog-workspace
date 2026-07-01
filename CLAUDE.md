# MyBlog + Music Review — Workspace

4 service repos + workspace. Each service deploys independently as AWS Lambda.
Per-repo CLAUDE.md removed — repo specifics live in code + each repo's README.

## Layout

myblog-workspace/
├── myblog_backend/   ← posts/categories/publish API → Lambda ratemymusic-api
├── myblog_front/     ← Astro 5 + React 19 → S3 + CloudFront
├── myblog_music/     ← DB-first music search → Lambda musicApi
├── myblog_worker/    ← SQS + EventBridge consumer → Lambda blogWorkerLambda
├── myblog_shared_db/ ← shared SQLAlchemy models (git-pinned by each service, ARCH-6)
├── infra/            ← Terraform (canonical AWS state; see infra/README.md for identifiers)
├── docs/{plan.md,contracts/,rfcs/,archive/}
├── scripts/{smoke.sh}            ← smoke test
└── tools/merge_openapi.py        ← merged OpenAPI spec (docs/contracts/openapi.json)

## Service boundaries

- `/api/music/search/unified` is **DB-only**. Spotify access goes `candidates` → SQS → worker.
- MusicBrainz alias fill runs from EventBridge, not SQS. Its outage must not block album sync.
- Backend ↔ music split exists so Spotify outage can't affect posts.

## Auth — two entry points

- **CloudFront → backend** (most routes): `edge_guard` checks `x-origin-verify: <EDGE_SECRET>`. Bypassed when `ENV=local|dev`. Bearer tokens skip this check.
- **API Gateway → backend** (`POST/PUT/DELETE /api/posts/*`, `POST /api/publish`): Cognito JWT validated at the API Gateway authorizer before Lambda (authorizer ID → `infra/README.md`).
- **Local**: backend/music/worker bypass JWT when `ENV=local|dev`. Frontend on `localhost` uses dummy token `'local-dev'`; `isLoggedIn()` returns true.

## Hard rules

Rules marked **🔒 hook-enforced** are auto-denied by PreToolUse hooks in `.claude/hooks/` (gitignored, local). The rest are convention only — Claude must self-police.

1. 🔒 Never work on `main`. First command: `git checkout -b <type>/<plan-id>-<desc>`.
2. 🔒 Never commit secrets. Use AWS SSM Parameter Store (SecureString) / GitHub Actions Secrets — Secrets Manager was emptied; do not reintroduce it (CHORE-secrets-ssm-migration).
3. Never run rollback migrations against prod directly — human approval required.
4. Never run >1 RFC step per session — unless (a) the RFC marks steps as `parallel`/`additive` or declares a single-PR merge, or (b) the user explicitly OKs the next step (e.g. "next step", "go", "gogo"). Reason: each gap enforces a prod-observe + direction-recheck gate (see PR-reviews-polymorphic — 4 steps reached prod before full revert).
5. Never self-promote RFC Status **without explicit in-session user approval**. `draft` → `accepted` (and `accepted` → `in-progress`) default to human-only; on explicit approval (e.g. "승격해" / "promote"), Claude may make the Status edit. Absent approval, default no. (Was 🔒 hook-enforced; relaxed to a self-policed convention 2026-06-05 — `block-rfc-self-promote.sh` removed.)
6. 🔒 Never `terraform apply -target=...` without explicit go-ahead. Always run full plan; stop on unexpected drift.
7. 🔒 (partial — force-push to main) Never push or merge without explicit go-ahead. An explicit push approval covers PR open + CI pass + squash merge + branch delete as a single flow (stop and report on CI fail / merge conflict / unexpected drift). User can opt out per request with "push only" to halt at PR open. `git add` + `commit` need no approval.
8. 🔒 Never skip git hooks (`--no-verify`, `--no-gpg-sign`) unless user says so.
9. Never add a synchronous Spotify call to a user-facing endpoint.

## Code conventions

Use `settings.*` (pydantic-settings), not `os.getenv()`. Use `logging.getLogger(__name__)`, not `print()`. Frontend authed requests go through `apiFetch` from `src/lib/api.ts`. Backend/music URLs always prefixed `/api`. Never log `GITHUB_TOKEN`, `DATABASE_URL`, `EDGE_SECRET`, Spotify creds.

## Doc language

Plan/spec markdown — `docs/plan.md`, `docs/rfcs/`, `docs/contracts/`, `docs/archive/`, PR bodies — always in English. Token-efficient context loading; conversation/chat can stay in Korean. **Questions directed at the user — ask in Korean** (decision points where the user has to read and respond; reduces user-side cognitive load).

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
- Frontend UI change → click through the change in a real browser (lint + `astro check` alone miss render/event regressions — see BUG-11 → BUG-12)

Post-merge (block claiming "done" if unchecked):

- Prod smoke passes after auto-deploy, result quoted in PR comment
- plan.md row dropped (history lives in `git log` + `docs/archive/done/`)

Never claim "done" before the post-merge items are green. If any item is unchecked, say so explicitly.

## Subagent + skill triggers

Subagents (local, myblog-specific) and skills (cross-project Anthropic plugins) overlap in places. Use the local subagent when the work needs project-specific context (sync-Spotify rule, SQS contract, service boundaries); use the skill for generic correctness or design help.

Triggers are **signals for when delegation is likely cheaper than direct work** — not mandatory escalations. See the bypass rule below the table.

| Trigger                                                            | Use                       |
| ------------------------------------------------------------------ | ------------------------- |
| Open-ended mapping of unfamiliar territory (layout not yet known)  | `explorer` subagent       |
| Cross-repo plan with sequencing / dependencies between PRs         | `planner` subagent        |
| Bug still unresolved after 2 fix attempts                          | `debugger` subagent       |
| Pytest cases / flaky tests                                         | `test-engineer` subagent  |
| New service or cross-repo structural design                        | `architect` subagent      |
| ≥3 files in a service repo OR any contract/infra touch             | `reviewer` subagent (myblog-specific contract / boundary checks) |
| UI change in `myblog_front`                                        | `frontend-design` skill   |
| Security-sensitive change (auth, secrets, input)                   | `security-review` skill   |

Subagents that produce code must run that repo's verification and quote the result.

**Trigger bypass rule.** If the main agent already has the relevant files loaded in context, do not spawn a subagent solely to satisfy a trigger — subagents exist to load context the main agent lacks, not to mirror context it already has. When bypassing a trigger, say so out loud (e.g. "explorer trigger matched but files already loaded — handling directly"). Invisible bypass = no bypass.

## Pointers

- Infra identifiers (Pool IDs, ARNs, domains) → `infra/README.md`
- Local dev setup (ports, env vars, install) → each repo's README
- Smoke test usage (test user, password rotation) → `scripts/smoke.sh` header
- Schema change procedure → `docs/contracts/README.md`
- Historical decisions (incl. 2026-05-27 Cognito incident) → `docs/archive/decisions/`
- Completed PRs → `git log` (authoritative); `docs/archive/done/` for older summaries
