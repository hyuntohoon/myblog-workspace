# Cross-Repo Work Plan

Active and upcoming cross-repo work. Completed items live in `docs/done/YYYY-MM.md` (current: `docs/done/2026-05.md`). Completed RFCs live in `docs/done/rfcs/`.

Format defined in `CLAUDE.md` → "Plan format". `Rollback` is optional for low-risk items. RFC-backed items are one-line pointers; their in-flight open questions live inside the RFC, not here.

---

## In Progress

_(none)_

---

## Upcoming — RFC-backed (high impact, multi-step)

_(none — ARCH-12 done)_

---

## Upcoming — short-form

### IAC-1-followup: SAM template removal from service repos

- **Scope**: `myblog_backend`, `myblog_music`, `myblog_worker`
- **Order**: Confirm Terraform owns all Lambda config → remove `template.yaml` / `samconfig.toml` from each repo → update CI to drop any SAM commands
- **Verification**: `grep -r "AWS::Serverless" <repo>` returns nothing; CI deploy still succeeds via `aws lambda update-function-code`
- **Prerequisite**: IAC-1 core (done 2026-05-25)
- **Status**: not started

### IAC-2-followup: IAM role consolidation

- **Scope**: `infra/`
- **Problem**: 3 Lambda execution roles defined manually, referenced by name from Terraform. `LambdaRDSControlRole` carries unused `AmazonRDSFullAccess` (legacy from pre-Neon era).
- **Order**: Terraform import each role → drop unused managed policies → faithful Terraform definition → `terraform apply`
- **Rollback**: Re-attach previous managed policies via console; roles are name-referenced so Terraform won't recreate
- **Verification**: `aws iam list-attached-role-policies` matches `terraform show` for each role; smoke test all 3 Lambda paths
- **Prerequisite**: IAC-1 core
- **Status**: not started

---

## Feature Backlog

Pitchfork-style review blog feature work. Each item needs a contract design pass before implementation.

| Item | Current state | Prerequisite |
|------|---------------|--------------|
| Rating scale unification | front `0-10` ↔ backend `le=5` mismatch | Update backend Pydantic model → re-export `openapi.json` → update `docs/contracts/openapi.json` → fix frontend consumer |
| Review subject type: `album \| track \| artist` | Album-only | Type extension in contract, then backend + frontend in lockstep |
| Track review page | Does not exist | Subject type extension |
| Artist profile + review page | Does not exist | Subject type extension |
| `ANTHROPIC_API_KEY` for code-review workflow | Not registered | GitHub → `myblog_front` Settings → Secrets |

> ARCH-12 is complete. Feature backlog items are now unblocked — API changes follow the contract-first workflow (export → merge → frontend types-in-sync CI gate).

---

## Open Questions

Workspace-level open questions only. RFC-internal questions stay in their RFC.

- _(none currently at workspace level)_

In-flight RFC questions (for awareness; resolved inside each RFC):
- **ARCH-12**: cross-repo trigger mechanism (Step 4), namespace prefix in merged spec, GitHub App vs PAT
