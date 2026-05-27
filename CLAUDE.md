# MyBlog + Music Review — Workspace

Personal blog combined with a music review feature. 4 service repos (`myblog_backend`, `myblog_front`, `myblog_music`, `myblog_worker`) + this workspace. Each service deploys independently as AWS Lambda.

This file is the **single source of truth** for cross-repo rules, system layout, and operational facts. Per-repo CLAUDE.md files have been removed — repo-specific details belong in code, not in docs.

---

## Layout

```
myblog-workspace/
├── myblog_backend/   ← user-facing API (posts, categories, publish)  →  Lambda `ratemymusic-api`
├── myblog_front/     ← Astro 5 + React 19 client                      →  S3 + CloudFront
├── myblog_music/     ← DB-first music search + Spotify sync trigger   →  Lambda `musicApi`
├── myblog_worker/    ← SQS consumer + scheduled MusicBrainz/Gemini    →  Lambda `blogWorkerLambda`
├── infra/            ← Terraform (canonical for all AWS resources)
├── docs/
│   ├── plan.md            ← active work + hotfix tracker
│   ├── contracts/         ← merged OpenAPI + SQS message schemas
│   ├── rfcs/              ← multi-step migrations (in-flight only)
│   └── archive/           ← historical (done logs, decisions, conventions, old architecture/infra)
└── scripts/
    ├── smoke.sh           ← smoke test against local or prod
    └── merge_openapi.py   ← merges backend + music OpenAPI → contracts/openapi.json
```

Note: `myblog_publish/` was absorbed into `myblog_backend` (ARCH-11). The directory `_archive_myblog_publish/` is kept for reference only — **do not edit, do not deploy**.

---

## System overview

```
Browser
  │
  ▼
CloudFront ── /         ─→ S3 (Astro static site)
            \
             \── /api/* ─→ API Gateway (lambdaAPI)
                            │
                            ├─→ ratemymusic-api (backend): posts CRUD, categories, /api/publish
                            └─→ musicApi (music):        /api/music/search/*, /api/music/albums/*

Backend  ──→ Neon Postgres
        ──→ GitHub Contents API (publish: writes MDX → triggers front build)

Music    ──→ Neon Postgres
        ──→ Spotify Web API (candidates only — never on /search/unified)
        ──→ SQS  → blogWorkerLambda → Spotify batch fetch → DB upsert
                                    + EventBridge rate(15m) → MusicBrainz alias fill
```

### Hard service boundaries

- `/api/music/search/unified` is **DB-only**. Never call Spotify synchronously from it. Spotify access goes `candidates` → SQS → worker.
- Spotify outage must not affect post reads or writes. That's why backend and music are split.
- Gemini/MusicBrainz alias generation runs from EventBridge, **not** from the SQS path — a Gemini/MusicBrainz outage must not block album sync.

---

## Hard rules — never violate

1. **Never work on `main`.** First command of any session: `git checkout -b <type>/<plan-id>-<desc>`.
2. **Never write secrets to any file in the repo** — no `.env`, `secrets.yaml`, etc. Use AWS Secrets Manager or GitHub Actions Secrets.
3. **Never run a rollback migration against the production database directly.** Migrations go through each repo's tooling; rollbacks require human approval.
4. **Never run more than one RFC step per session** unless the RFC explicitly says steps may run in parallel.
5. **Never self-promote an RFC's Status.** `draft` → `accepted` is human-only.
6. **Never use `terraform apply -target=...`** without the user's explicit go-ahead. `-target` silently pulls related drift in — that's how Cognito logout_urls got broken (2026-05-27). Always run a full plan; if you see unexpected changes, stop and report.
7. **Never claim "done" without a prod smoke test result quoted in this session.** Unit tests passing locally is not "verified". See "Definition of Done" below.
8. **Never add a synchronous Spotify call to a user-facing endpoint.** Async path only.
9. **Never log secrets** (`GITHUB_TOKEN`, `DATABASE_URL`, `EDGE_SECRET`, Spotify creds, etc.).
10. **Never use `os.getenv()` in application code** — always go through `settings.*` (pydantic-settings).
11. **Never use `print()`** — use `logging.getLogger(__name__)`.
12. **Never use raw `fetch()` for authenticated frontend requests** — use `apiFetch` from `src/lib/api.ts`.
13. **Never hardcode frontend paths without the `/api` prefix** when targeting backend/music.
14. **Never push or merge without explicit human approval** ("push" or "ok push"). AI may `git add` and `git commit` freely.
15. **Never skip git hooks** (`--no-verify`, `--no-gpg-sign`) unless the user explicitly says so.

---

## Working rules

- **Cross-repo change (≥2 repos)**: update `docs/plan.md` _before_ code. For API contract changes, run the OpenAPI export in the affected service repo and commit `openapi.json` in the same PR — the workspace merge tool regenerates `docs/contracts/openapi.json` when that PR lands. Frontend types are derived from the merged spec; CI fails on drift.
- **Multi-step migration (≥2 repos OR multi-day OR ordered PRs)**: write an RFC in `docs/rfcs/`; `plan.md` row is a one-line pointer.
- **Single-repo change**: discover the code structure by reading the repo; no per-repo CLAUDE.md to fall back on.
- **Investigation across 3+ files or 2+ repos**: delegate to an `explorer` subagent rather than pulling everything into main context.
- **Looking up a completed PR**: use `git log`. `docs/archive/done/` has older summaries but git is authoritative.

---

## Workflow — branch, commit, PR

### Branch names

```
<type>/<plan-id>-<short-desc>
```

`<type>` ∈ `feat | fix | chore | refactor | docs | test | ci | db`
`<plan-id>` matches `docs/plan.md` (e.g. `PR-12`, `BUG-1`, `ARCH-12`)
`<short-desc>` kebab-case, 3–5 words.

Examples: `fix/BUG-1-api-gw-put-delete-routes`, `feat/PR-12-post-crud`.

### Commit messages — Conventional Commits

```
<type>(<scope>): <subject>

<body>          ← optional, wrap at 72; explain *why*, not *what*

Co-Authored-By: Claude <model> <noreply@anthropic.com>     ← only when AI authored
```

Subject: lowercase imperative, no trailing period, ≤72 chars.

### PR flow

1. Branch off `main`.
2. Implement.
3. **Local smoke**: `./scripts/smoke.sh local` (or equivalent) — must pass.
4. Push, open PR with summary + verification block (see Plan format).
5. **Prod smoke**: `./scripts/smoke.sh prod` after deploy — quote the result.
6. Squash merge. Squash commit title = Conventional Commits format.
7. Update `docs/plan.md`: move row to "✅ Done" or remove if trivial.

### Definition of Done — none of these are optional

- [ ] Tests pass locally (`pytest`, `pnpm lint`, `pnpm exec astro check`).
- [ ] `terraform plan` shows no unexpected drift for any affected stack.
- [ ] If a backend route was added/removed: corresponding API Gateway route exists in `infra/apigateway.tf`.
- [ ] If an API contract changed: `openapi.json` regenerated and committed; merged contract updated.
- [ ] **Local smoke test passes** and result quoted in PR.
- [ ] **Prod smoke test passes** after deploy and result quoted in PR.

If any box is unchecked, the work is not done — say so explicitly instead of claiming success.

---

## Plan format (`docs/plan.md`)

```
## PR-N: <one-line title>
- Scope: <repos affected>
- Order: <step order if multi-repo>
- Verification:
  - local smoke: <command> → <expected result>
  - prod smoke:  <command> → <expected result>
- Rollback: <optional, for low-risk skip>
- Status: <not started | in-progress | blocked | done>
```

RFC-backed entries are a one-line pointer:

```
## ARCH-N: <title>
- RFC: docs/rfcs/ARCH-N-<slug>.md
- Status: accepted
```

When a row moves to `Status: done`, cut it and append to `docs/archive/done/YYYY-MM.md` with merge SHA + date.

---

## Infrastructure facts

Source of truth: `infra/terraform.tfstate`. The values below are a human-readable mirror; if they disagree with `terraform show`, Terraform wins.

| Resource | Identifier |
|----------|------------|
| AWS region | `ap-northeast-2` (Seoul); Neon in `ap-southeast-1` |
| API Gateway | `lambdaAPI` (HTTP API ID: `ld8pjw3mx4`) |
| Cognito | `MyBlogAdminPool` (Pool ID: `ap-northeast-2_54vEJKEU5`, SPA Client ID: `68ccmcanfbvla9qbovnb9b18bt`) |
| Cognito hosted UI domain | `ap-northeast-254vejkeu5.auth.ap-northeast-2.amazoncognito.com` |
| SQS | `blogSQS` + DLQ via redrive policy |
| S3 bucket | `myblog-prod-web` |
| CloudFront | `d2y4n52sgjlrz6.cloudfront.net` → `www.ratemymusic.blog` |
| Neon DB | Pooler URL stored in each service's Secrets Manager entry |
| Secrets | `myblog/backend`, `myblog/music`, `myblog/worker` |
| EventBridge | `rate(15 min)` → `blogWorkerLambda` (alias mode) |

### Lambda functions

| Function | Service | Timeout |
|----------|---------|---------|
| `ratemymusic-api` | myblog_backend | 15s |
| `musicApi` | myblog_music | 15s |
| `blogWorkerLambda` | myblog_worker | 120s |

### Auth flow — two entry points

- **CloudFront → backend** (most routes): `edge_guard` middleware checks `x-origin-verify: <EDGE_SECRET>`. Bypassed when `ENV=local`/`dev`. Bearer-token requests pass through without `x-origin-verify` check.
- **API Gateway → backend** (`POST /api/posts`, `PUT /api/posts/{id}`, `DELETE /api/posts/{id}`, `POST /api/publish`): Cognito JWT validated at API Gateway authorizer (`6eia7l`) before reaching Lambda.

---

## Schema and contracts

- **Canonical DDL**: `docs/contracts/schema.sql`.
- **ORM**: SQLAlchemy 2 + psycopg3. Models in `myblog-shared-db` (separate Python package, pinned by git URL — ARCH-6).
- **OpenAPI**: each backend/music service exports `openapi.json` in its repo; workspace merge tool produces `docs/contracts/openapi.json`. Frontend `pnpm generate:types` derives `src/lib/api.gen.ts` from the merged spec.
- **SQS contract**: `docs/contracts/sqs-album-sync.md` (Format A batch / Format B single).

### Schema change procedure

1. Update `docs/contracts/schema.sql`.
2. Update `myblog_shared_db/models.py`; regenerate `_generated_schema.sql`.
3. Tag a new shared-db version; update pin in each consumer's `requirements.txt`.
4. Run migrations on Neon (per-service `db/migrations/`).

---

## Local development

Backend, music, and worker all bypass Cognito JWT validation when `ENV=local` or `ENV=dev` (see `app/core/auth.py:33` in each service). The frontend matches this: when served from `localhost`, `getAccessToken()` returns the dummy token `'local-dev'` and `isLoggedIn()` returns true, so you can write/edit posts without logging in.

### Backend (`myblog_backend`)

```bash
cd myblog_backend
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL='postgresql+psycopg://...neon.tech/...'   # from myblog/backend secret
export ENV=local
uvicorn app.main:app --reload --port 8000
```

### Music (`myblog_music`)

```bash
cd myblog_music
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL='...'           # from myblog/music secret
export SPOTIFY_CLIENT_ID='...'      # only if testing /candidates
export SPOTIFY_CLIENT_SECRET='...'
export ENV=local
uvicorn app.main:app --reload --port 8001
```

### Frontend (`myblog_front`)

```bash
cd myblog_front
pnpm install
pnpm dev    # http://localhost:4321 → talks to backend:8000 + music:8001
```

`.env` defaults to `PUBLIC_BACKEND_API_URL=http://localhost:8000` and `PUBLIC_API_URL=http://localhost:8001`. Override per-shell if needed.

### Smoke tests — `scripts/smoke.sh`

End-to-end smoke runs against either `prod` or `local`. 20 checks across health, search filter, album-detail wrapper, and post CRUD.

```bash
# Prod
export MYBLOG_SMOKE_PASSWORD='<test user password>'
./scripts/smoke.sh prod

# Local (services must be running on :8000 + :8001)
./scripts/smoke.sh local
```

Test user: `test@ratemymusic.blog` (Cognito). Password rotation: `aws cognito-idp admin-set-user-password ...`.

**Quote the smoke result in every PR.** Definition of Done above is not optional.

---

## Subagent triggers

Only delegate when the trigger matches; otherwise solve inline.

| Trigger | Subagent |
|---------|----------|
| Tracing a flow across 3+ files or 2+ repos | `explorer` |
| Change touches 2+ repos and needs a plan | `planner` (writes to `docs/plan.md`) |
| Bug not isolated after 2 failed fix attempts | `debugger` |
| Writing pytest cases or fixing flaky tests | `test-engineer` |
| Adding a new service or making a cross-repo design decision | `architect` |
| Before pushing a substantial PR branch | `reviewer` |
| UI/visual change in `myblog_front` | invoke the `frontend-design` skill |

Subagents that produce code must run that repo's verification command and quote the result in their return. No "done" without evidence.
