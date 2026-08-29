# MyBlog + Music Review — Workspace

4 service repos + workspace. Each service deploys independently as AWS Lambda.
Per-repo instruction files were consolidated here — repo specifics live in code + each repo's README.

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

Rules marked **🔒 hook-enforced** are auto-denied by project PreToolUse hooks in `.codex/hooks/`. The rest are convention only — Codex must self-police.

1. 🔒 Never work on `main`. First command: `git checkout -b <type>/<plan-id>-<desc>`.
2. 🔒 Never commit secrets. Use AWS SSM Parameter Store (SecureString) / GitHub Actions Secrets — Secrets Manager was emptied; do not reintroduce it (CHORE-secrets-ssm-migration).
3. Never run rollback migrations against prod directly — human approval required.
4. Never run >1 RFC step per session — unless (a) the RFC marks steps as `parallel`/`additive` or declares a single-PR merge, or (b) the user explicitly OKs the next step (e.g. "next step", "go", "gogo"). Reason: each gap enforces a prod-observe + direction-recheck gate (see PR-reviews-polymorphic — 4 steps reached prod before full revert).

   **Standing OK for chained sessions (owner rule 2026-08-01).** One step per session still holds — what changed is that the *gap* no longer needs a fresh human OK. `$wrap` auto-spawns the next session to run the next step whenever every chain condition passes; the owner's approval is standing, not per-step. A **human-observation** success signal (e.g. "does the owner's rating row leave 0") does **not** stop the chain — prod smoke green is enough, and the observation is carried forward into the next prompt as a one-liner.

   **`$wrap` is self-invoked — experimental, prompt-only (opened 2026-08-01).** Deliberately no 🔒: nothing enforces this but Codex reading it. Treat it as a running experiment, not a settled rule — **expect to revise this paragraph repeatedly from use.** Any session that wraps at the wrong moment, wraps on a half-verified step, or fails to wrap at all is the feedback; edit this paragraph and date the change rather than working around it in-session.

   Current shape: the owner never types `$wrap`. When a step has **reached a conclusion** — either the post-merge DoD is green (squash merge landed, prod smoke passed and quoted in the PR comment, plan.md row dropped) **or** the step concluded without shipping code (measured NO-GO, step dropped; cf. FEAT-lyrics-sync-precision Step 3) — Codex invokes `$wrap` itself as the session's last act, without asking for a go-ahead first. If any applicable item is unchecked, do **not** wrap: name the missing item and stop, so the chain never carries a half-verified step forward.

   Known gap, unclosed on purpose: a forgotten wrap is silent. A Stop-hook backstop was scoped and **rejected** — the obvious signal (branch gone from origin after merge) fires *before* deploy + prod smoke, so it would wrap early, which is the exact failure this rule exists to prevent. If the silence turns out to matter in practice, design the backstop off `SKILL.md` §3-1 run state, not off git state.

   The chain still stops — and asks — on anything Codex cannot decide for the owner: an unresolved open question on the next step, a conditional step whose gate hasn't been judged, `terraform apply` / a rule-3 prod migration / a rule-5 Status promote, red or missing verification, an unmerged PR the next step would stack on, or foreign commits in the worktree.

   **One session owns a checkout — a busy checkout means branch off, not stop** (owner rule 2026-08-02, replacing the prior stop-and-report default). Every session's first act, before touching git, is `bash .agents/skills$wrap/scripts/session-claim.sh`. `OK` → work in the shared checkout as usual. `BUSY` (another live session that hasn't retired) → **do not stop and do not touch the shared checkout**; for each repo you will modify, cut an isolated worktree off `origin/main` and work there. Say which worktree you're using in your first report. Recipe (incl. the two traps that bite: commit via `git -C <WT>` because the Bash cwd resets and the rule-#1 hook misjudges, and stage explicit paths because a symlinked `node_modules` commits as a `120000` blob and breaks the next deploy) → memory `reference-nested-repo-worktree-recipe`. A dev server in a worktree needs a real `pnpm install`, not the symlink, and a free port — **ports and processes stay shared even when the checkout isn't**.

   The one case that still stops and asks: another live session is running **the same RFC step** — worktrees prevent file collisions, not duplicated work. `$wrap` retires its own thread after spawning the next one; if a peer thread is known dead, `session-claim.sh retire <thread-id>` reclaims the shared checkout. Enforcement that must not depend on Codex remembering lives in the skill and scripts, not the prompt: the kill switch is `touch ~/.codex/.wrap-chain-stop` (effective mid-flight), and the chain iteration cap is eight. Full condition list + run state → `.agents/skills$wrap/SKILL.md`.
5. Never self-promote RFC Status **without explicit in-session user approval**. `draft` → `accepted` (and `accepted` → `in-progress`) default to human-only; on explicit approval (e.g. "승격해" / "promote"), Codex may make the Status edit. Absent approval, default no.
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

- **Auth guards fail closed.** Missing config (e.g. `COGNITO_USER_POOL_ID`, `EDGE_SECRET`) ⇒ 503/reject, never a silent bypass. The Cognito verifier is one text in two places — `app/core/auth.py` is byte-identical in backend and music (SEC-system-hardening Step 6), so a verifier fix must land in both in the same PR; the workspace `Cognito verifier drift` workflow diffs the two `main` copies daily. Authorization tiers are backend-only, in `myblog_backend/app/core/authz.py`.
- **Never hold an open DB session/transaction across an external-API loop** (Neon drops idle-in-txn conns → ProtocolViolation) — fetch → materialize → close, then loop, then a fresh short write session. The lyrics pipeline is the reference.
- **Bulk `ON CONFLICT` upserts sort rows by conflict key** (row-lock deadlock avoidance under SQS concurrency).
- **Outbound HTTP always sets an explicit `timeout`.**
- **Fixing a pattern-shaped bug in duplicated cross-repo code** (auth guards, SQS/S3 clients, settings loaders, session lifecycle)? Grep every service repo for the twin and fix all hits in the same PR — name the sweep in the PR body.

## Doc language

Plan/spec markdown — `docs/plan.md`, `docs/rfcs/`, `docs/contracts/`, `docs/archive/`, PR bodies — always in English. Token-efficient context loading; conversation/chat can stay in Korean. **Questions directed at the user — ask in Korean** (decision points where the user has to read and respond; reduces user-side cognitive load). **Information reported to the user — keep it easy to understand** (plain words, no jargon walls; owner rule 2026-07-21).

## Workflow

**Branch**: `<type>/<plan-id>-<desc>` — type ∈ feat|fix|chore|refactor|docs|test|ci|db; plan-id from `docs/plan.md` (PR-N/BUG-N/ARCH-N); desc kebab-case 3–5 words. Plan-id can be omitted for ad-hoc docs/chore work not tracked in plan.md (e.g. `docs/codex-config-cleanup`).

**Commit**: Conventional Commits, lowercase imperative subject ≤72 chars. `Co-Authored-By: Codex` trailer when AI-authored.

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

Project custom agents and Codex skills/plugins overlap in places. Use a project agent when the work needs myblog-specific context (sync-Spotify rule, SQS contract, service boundaries); use a skill for reusable workflows or tool-specific help.

Triggers are **signals for when delegation is likely cheaper than direct work** — not mandatory escalations. See the bypass rule below the table.

| Trigger                                                            | Use                       |
| ------------------------------------------------------------------ | ------------------------- |
| Open-ended mapping of unfamiliar territory (layout not yet known)  | `explorer` subagent       |
| Cross-repo plan with sequencing / dependencies between PRs         | `planner` subagent        |
| Bug still unresolved after 2 fix attempts                          | `debugger` subagent       |
| Pytest cases / flaky tests                                         | `test-engineer` subagent  |
| New service or cross-repo structural design                        | `architect` subagent      |
| ≥3 files in a service repo OR any contract/infra touch             | `reviewer` subagent (myblog-specific contract / boundary checks) |
| UI change in `myblog_front`                                        | main agent + `browser:control-in-app-browser` for clickthrough |
| Security-sensitive change (auth, secrets, input)                   | main agent directly; use Codex Security only when installed and authorized |
| Any non-trivial code implementation leg                            | Codex `worker` subagent — see **Implementation delegation** below |

Subagents that produce code must run that repo's verification and quote the result.

**Implementation delegation.** Code implementation legs route by risk and size. The primary Codex agent always keeps branch management, diff review, verification, commit, and push. Every write-capable subagent must receive explicit file ownership, must preserve concurrent edits, and must be instructed **not to commit**.

| Situation | Executor |
| --------- | -------- |
| Auth guards / API contracts / DB migrations / infra | **Primary Codex agent directly** — no delegation. These are the recurring bug classes (fail-closed guards, twin-drift sweeps, session lifecycle); rule enforcement outweighs typing savings |
| Complex leg (multi-file, new feature, cross-cutting) | `worker` subagent; prefer the strongest available Codex model and high reasoning |
| Mid-complexity single-repo leg (no boundary touch) | `worker` subagent with a balanced Codex model and medium reasoning |
| Mechanical / bulk leg (boilerplate, repetitive edits, test scaffolding) | `worker` subagent with the fastest available Codex model and low reasoning |
| Trivial edit to files already in context | Primary Codex agent directly (delegation overhead exceeds the gain) |
| subagent rate-limit / quota error | Fall back to the primary Codex agent — say which fallback fired |


**Trigger bypass rule.** If the main agent already has the relevant files loaded in context, do not spawn a subagent solely to satisfy a trigger — subagents exist to load context the main agent lacks, not to mirror context it already has. When bypassing a trigger, say so out loud (e.g. "explorer trigger matched but files already loaded — handling directly"). Invisible bypass = no bypass.

## Pointers

- Infra identifiers (Pool IDs, ARNs, domains) → `infra/README.md`
- Local dev setup (ports, env vars, install) → each repo's README
- Smoke test usage (test user, password rotation) → `scripts/smoke.sh` header
- Schema change procedure → `docs/contracts/README.md`
- Historical decisions (incl. 2026-05-27 Cognito incident) → `docs/archive/decisions/`
- Completed PRs → `git log` (authoritative); `docs/archive/done/` for older summaries
