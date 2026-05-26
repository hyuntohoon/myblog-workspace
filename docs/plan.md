# Cross-Repo Work Plan

Active and upcoming cross-repo work. Completed items live in `docs/done/YYYY-MM.md` (current: `docs/done/2026-05.md`). Completed RFCs live in `docs/done/rfcs/`.

Format defined in `CLAUDE.md` → "Plan format". `Rollback` is optional for low-risk items. RFC-backed items are one-line pointers; their in-flight open questions live inside the RFC, not here.

---

## In Progress

_(none — IAC-1 core applied; follow-ups tracked under "Upcoming" below)_

---

## Upcoming — RFC-backed (high impact, multi-step)

### ARCH-6: Shared DB models package

- **RFC**: `docs/rfcs/ARCH-6-shared-db-package.md`
- **Scope**: new repo `myblog_shared_db` + `myblog_backend`, `myblog_music`, `myblog_worker`
- **Status**: in-progress (Step 1 done — Step 2 next)

### ARCH-11: Absorb `myblog_publish` into `myblog_backend`

- **RFC**: `docs/rfcs/ARCH-11-absorb-publish-into-backend.md`
- **Scope**: `myblog_backend`, `myblog_publish` (delete), `myblog_front`, `infra/`
- **Status**: accepted (ready for Step 1)
- **Note**: closes SEC-4 (`publisher-github` public Function URL) as part of Step 3.

### ARCH-12: Contract-first workflow with strict OpenAPI enforcement

- **RFC**: `docs/rfcs/ARCH-12-contract-first-openapi.md`
- **Scope**: `myblog_backend`, `myblog_music`, `myblog_front`, workspace (`docs/contracts/`, `tools/`)
- **Status**: accepted (ready for Step 1)
- **Note**: prerequisite for all Feature Backlog items below.

---

## Upcoming — short-form

### IAC-1-followup: SAM template removal from service repos

- **Scope**: `myblog_backend`, `myblog_music`, `myblog_worker`, `myblog_publish`
- **Order**: Confirm Terraform owns all Lambda config → remove `template.yaml` / `samconfig.toml` from each repo → update CI to drop any SAM commands
- **Verification**: `grep -r "AWS::Serverless" <repo>` returns nothing; CI deploy still succeeds via `aws lambda update-function-code`
- **Prerequisite**: IAC-1 core (done 2026-05-25)
- **Status**: not started
- **Note**: ARCH-11 Step 3 removes `myblog_publish` from this list; sequence with that RFC if both are active.

### IAC-2-followup: IAM role consolidation

- **Scope**: `infra/`
- **Problem**: 4 Lambda execution roles defined manually, referenced by name from Terraform. `LambdaRDSControlRole` carries unused `AmazonRDSFullAccess` (legacy from pre-Neon era).
- **Order**: Terraform import each role → drop unused managed policies → faithful Terraform definition → `terraform apply`
- **Rollback**: Re-attach previous managed policies via console; roles are name-referenced so Terraform won't recreate
- **Verification**: `aws iam list-attached-role-policies` matches `terraform show` for each role; smoke test all 4 Lambda paths
- **Prerequisite**: IAC-1 core
- **Status**: not started

### SEC-4: publisher-github Function URL hardening

- **Status**: superseded by ARCH-11. Step 3 of that RFC deletes the Function URL as part of decommissioning `myblog_publish`; Step 4 removes this row.
- Keep this row visible until ARCH-11 Step 4 lands; then archive both together.

---

## Feature Backlog

Pitchfork-style review blog feature work. Each item needs a contract design pass before implementation.

| Item | Current state | Prerequisite |
|------|---------------|--------------|
| Rating scale unification | front `0-10` ↔ backend `le=5` mismatch | Contract first: pick a single scale, update `docs/contracts/openapi-backend.json` |
| Review subject type: `album \| track \| artist` | Album-only | Type extension in contract, then backend + frontend in lockstep |
| Track review page | Does not exist | Subject type extension |
| Artist profile + review page | Does not exist | Subject type extension |
| `ANTHROPIC_API_KEY` for code-review workflow | Not registered | GitHub → `myblog_front` Settings → Secrets |

> Feature backlog items are blocked on **ARCH-12** (contract-first OpenAPI). ARCH-6 reduces schema-change cost but doesn't address API drift; ARCH-12 is the actual prerequisite for the rating/subject-type work below. Don't start any Feature Backlog item until ARCH-12 Step 5 lands.

---

## Open Questions

Workspace-level open questions only. RFC-internal questions stay in their RFC.

- _(none currently at workspace level)_

In-flight RFC questions (for awareness; resolved inside each RFC):
- **ARCH-6**: schema parity CI source-of-truth resolution, SQLAlchemy version alignment, migrations ownership
- **ARCH-11**: API Gateway routing during cutover, GitHub token rotation timing
- **ARCH-12**: cross-repo trigger mechanism (Step 4), namespace prefix in merged spec, GitHub App vs PAT
