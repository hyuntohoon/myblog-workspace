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
├── scripts/          ← smoke test (smoke.sh/smoke.py) + Editor Buckit nightly pipeline (pollers, plists)
└── tools/            ← merge_openapi.py (→ docs/contracts/openapi.json) + lyrics corpus/best-of batch tools

## Service boundaries

- `/api/music/search/unified` is **DB-only**. Spotify access goes `candidates` → SQS → worker.
- MusicBrainz alias fill runs from EventBridge, not SQS. Its outage must not block album sync.
- Backend ↔ music split exists so Spotify outage can't affect posts.

## Auth — two entry points

- **CloudFront → backend** (most routes): `edge_guard` checks `x-origin-verify: <EDGE_SECRET>`. Bypassed when `ENV=local|dev`. Bearer tokens skip this check.
- **API Gateway → backend** (every mutation route — posts/publish/buckets/items/me/reviews/integrations/library-writes/genres/research/todays-pick — plus `GET /api/playback/spotify-token` and `GET /api/lyrics/*`): Cognito JWT validated at the API Gateway authorizer before Lambda (authorizer ID → `infra/README.md`; full route list → `infra/apigateway.tf`). A new authed mutation 404s until added there (probe: 401 = live, 404 = missing route).
- **Authorization inside backend** (multi-user since FEAT-multi-user-accounts): `require_owner` fail-closed (`sub == OWNER_SUB`) on the ~27 single-owner routes (editorial/publish/genres/playback/library-ops); member routes use `require_cognito_token` + lazy user provisioning (`provisioned_member_id`), row-scoped by `user_id`. Third, narrow tier: the 03:00 nightly draft agent (`DRAFT_AGENT_SUB`, empty = no agent) passes `require_owner_or_draft_agent` on exactly `POST /api/posts` (status + editorial fields coerced — draft-only) and `POST /api/buckets/nightly-grow` (acting user pinned server-side to `OWNER_SUB`); runbook → `infra/README.md` "Nightly draft agent".
- **Local**: backend/music/worker bypass JWT when `ENV=local|dev`. Frontend on `localhost` uses dummy token `'local-dev'`; `isLoggedIn()` returns true.

## Hard rules

Rules marked **🔒 hook-enforced** are auto-denied by PreToolUse hooks in `.claude/hooks/` (gitignored, local). The rest are convention only — Claude must self-police.

1. 🔒 Never work on `main`. First command: `git checkout -b <type>/<plan-id>-<desc>`.
2. 🔒 Never commit secrets. Use AWS SSM Parameter Store (SecureString) / GitHub Actions Secrets — Secrets Manager was emptied; do not reintroduce it (CHORE-secrets-ssm-migration).
3. Never run rollback migrations against prod directly — human approval required.
4. Never run >1 RFC step per session — unless (a) the RFC marks steps as `parallel`/`additive` or declares a single-PR merge, or (b) the user explicitly OKs the next step (e.g. "next step", "go", "gogo"). Reason: each gap enforces a prod-observe + direction-recheck gate (see PR-reviews-polymorphic — 4 steps reached prod before full revert).

   **Standing OK for chained sessions (owner rule 2026-08-01).** One step per session still holds — what changed is that the *gap* no longer needs a fresh human OK. `/wrap` auto-spawns the next session to run the next step whenever every chain condition passes; the owner's approval is standing, not per-step. A **human-observation** success signal (e.g. "does the owner's rating row leave 0") does **not** stop the chain — prod smoke green is enough, and the observation is carried forward into the next prompt as a one-liner.

   The chain still stops — and asks — on anything Claude cannot decide for the owner: an unresolved open question on the next step, a conditional step whose gate hasn't been judged, `terraform apply` / a rule-3 prod migration / a rule-5 Status promote, red or missing verification, an unmerged PR the next step would stack on, foreign commits in the worktree, or the iteration cap. Kill switch, effective mid-flight: `touch ~/.claude/.wrap-chain-stop` (the spawn script refuses while it exists). Full condition list + run state → `~/.claude/skills/wrap/SKILL.md` §3-1.
5. Never self-promote RFC Status **without explicit in-session user approval**. `draft` → `accepted` (and `accepted` → `in-progress`) default to human-only; on explicit approval (e.g. "승격해" / "promote"), Claude may make the Status edit. Absent approval, default no.
6. 🔒 Never `terraform apply -target=...` without explicit go-ahead. Always run full plan; stop on unexpected drift.
7. 🔒 (partial — force-push to main) **Push + merge is autonomous once verification is green** (owner rule 2026-08-01, replacing the prior ask-first default). When every applicable pre-merge DoD check passes, proceed through PR open → CI pass → squash merge → branch delete without asking. `git add` + `commit` never needed approval either.

   **Green means all of these, actually run and actually passing** — not "should pass", not "unrelated to my change":
   - the repo's own suite (`pytest` / `pnpm lint` + `pnpm exec astro check` + `pnpm test`), quoted in the PR body
   - PR CI green on every required check (workspace has no PR-CI — its own suite is the gate)
   - `terraform plan` clean for any touched stack
   - frontend UI change → real-browser clickthrough done
   - no foreign commits in the worktree (`origin/main..HEAD` is only mine)

   **Still stop and ask** — these are not "verification failures", so they need naming separately: any red or missing check, merge conflict, unexpected `terraform` drift, a rule-3 prod migration, a destructive/irreversible step, HEAD found on an unexpected branch, or signs another session shares the worktree. Also stop when the change is green but the *approach* turned out different from what was agreed — green tests do not ratify a changed plan.

   User can still opt out per request with "push only" (halt at PR open) or "PR만" .
8. 🔒 Never skip git hooks (`--no-verify`, `--no-gpg-sign`) unless user says so.
9. Never add a synchronous Spotify call to a user-facing endpoint.

## Code conventions

Use `settings.*` (pydantic-settings), not `os.getenv()`. Use `logging.getLogger(__name__)`, not `print()`. Frontend authed requests go through `apiFetch` from `src/lib/api.ts`. Backend/music URLs always prefixed `/api`. Never log `GITHUB_TOKEN`, `DATABASE_URL`, `EDGE_SECRET`, `GENIUS_ACCESS_TOKEN`, Spotify creds.

Hardened after FIX-bug-audit-2026-07 (all are recurring bug classes — the audit found each already-fixed once and re-broken elsewhere):

- **Auth guards fail closed.** Missing config (e.g. `COGNITO_USER_POOL_ID`, `EDGE_SECRET`) ⇒ 503/reject, never a silent bypass. The auth guard is duplicated in **both** backend and music (`app/core/auth.py`) — a guard fix must land in both in the same PR.
- **Never hold an open DB session/transaction across an external-API loop** (Neon drops idle-in-txn conns → ProtocolViolation) — fetch → materialize → close, then loop, then a fresh short write session. The lyrics pipeline is the reference.
- **Bulk `ON CONFLICT` upserts sort rows by conflict key** (row-lock deadlock avoidance under SQS concurrency).
- **Outbound HTTP always sets an explicit `timeout`.**
- **Fixing a pattern-shaped bug in duplicated cross-repo code** (auth guards, SQS/S3 clients, settings loaders, session lifecycle)? Grep every service repo for the twin and fix all hits in the same PR — name the sweep in the PR body.

## Doc language

Plan/spec markdown — `docs/plan.md`, `docs/rfcs/`, `docs/contracts/`, `docs/archive/`, PR bodies — always in English. Token-efficient context loading; conversation/chat can stay in Korean. **Questions directed at the user — ask in Korean** (decision points where the user has to read and respond; reduces user-side cognitive load). **Information reported to the user — keep it easy to understand** (plain words, no jargon walls; owner rule 2026-07-21).

## Workflow

**Branch**: `<type>/<plan-id>-<desc>` — type ∈ feat|fix|chore|refactor|docs|test|ci|db; plan-id from `docs/plan.md` (PR-N/BUG-N/ARCH-N); desc kebab-case 3–5 words. Plan-id can be omitted for ad-hoc docs/chore work not tracked in plan.md (e.g. `docs/claude-md-cleanup`).

**Commit**: Conventional Commits, lowercase imperative subject ≤72 chars. `Co-Authored-By: Claude` trailer when AI-authored.

**Cross-repo (≥2 repos)**: update `docs/plan.md` before code. API contract change → export `openapi.json` in service repo, commit in same PR; then run `tools/merge_openapi.py` manually and commit the regenerated `docs/contracts/openapi.json` in workspace (the service→workspace notify-contract dispatch 401s — auto-merge is dead); frontend types derived from merged spec (CI fails on drift).

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
| Any non-trivial code implementation leg                            | codex or GLM — see **Implementation delegation** below |

Subagents that produce code must run that repo's verification and quote the result.

**Implementation delegation.** Code implementation legs route by risk and size — not Claude typing the code by default. Claude always keeps branch management, diff review, verification, commit, and push; both executors must be instructed **not to commit** (codex additionally runs without this workspace's git hooks; `claude-glm` inherits them).

| Situation | Executor |
| --------- | -------- |
| Auth guards / API contracts / DB migrations / infra | **Claude directly** — no delegation. These are the recurring bug classes (fail-closed guards, twin-drift sweeps, session lifecycle); rule enforcement outweighs typing savings |
| Complex leg (multi-file, new feature, cross-cutting) | `codex` MCP tool (`mcp__codex__codex`, workspace-write, `cwd` = target repo) |
| Mid-complexity single-repo leg (no boundary touch) | `claude-glm -p --model opus` (glm-5.2, headless Claude Code via z.ai — zsh function, key isolated in `~/.config/claude-glm.env`) |
| Mechanical / bulk leg (boilerplate, repetitive edits, test scaffolding) | `claude-glm -p` (glm-4.7 — lowest z.ai quota draw) |
| Trivial edit to files already in context | Claude directly (delegation overhead exceeds the gain) |
| codex rate-limit / quota error | Fall back to glm-5.2, then Claude directly — say which fallback fired |

**z.ai peak window — no GLM.** 15:00–19:00 KST (14:00–18:00 UTC+8) glm-5.2 draws 3× quota; during this window do not delegate to GLM at all — route those legs to codex (or defer). Check `date` before any `claude-glm` call. (glm-4.7 carries no multiplier, but the owner rule is a blanket no-GLM window for simplicity.)

**Trigger bypass rule.** If the main agent already has the relevant files loaded in context, do not spawn a subagent solely to satisfy a trigger — subagents exist to load context the main agent lacks, not to mirror context it already has. When bypassing a trigger, say so out loud (e.g. "explorer trigger matched but files already loaded — handling directly"). Invisible bypass = no bypass.

## Pointers

- Infra identifiers (Pool IDs, ARNs, domains) → `infra/README.md`
- Local dev setup (ports, env vars, install) → each repo's README
- Smoke test usage (test user, password rotation) → `scripts/smoke.sh` header
- Schema change procedure → `docs/contracts/README.md`
- Historical decisions (incl. 2026-05-27 Cognito incident) → `docs/archive/decisions/`
- Completed PRs → `git log` (authoritative); `docs/archive/done/` for older summaries
