# OPS-delivery-safety-gates: CI merge gates, deploy smoke, and async failure boundaries

- **Status**: in-progress (Step 4) — Step 1 shipped + prod-smoked 2026-07-23 (backend #130, SHA 4018f50); Step 2 shipped + prod-smoked 2026-07-23 (worker #77 SHA 4d1d3dd, front #306 SHA 4de9193); Step 3 shipped + prod-smoked 2026-07-24 (backend #132 6b0447c, music #59 b9b4d42, worker #78 ffb1cf7 + waiter/IAM fix #79 bc008f3, front #313 8061c63)
- **Owner**: TBD
- **Created**: 2026-07-23
- **Plan row**: `plan.md` → OPS-delivery-safety-gates
- **Source**: `docs/reviews/2026-07-23-current-state-audit.md` §O-1..O-4, C-5

---

## Goal

After this RFC, an unsafe change cannot silently merge or reach prod: the backend `pytest` suite (already 46 files / 631 tests, including the fail-closed auth regression) runs as a **PR-blocking** gate; `myblog_front` and `myblog_worker` gain PR-stage gates equivalent to what they already run post-merge; and every service deploy runs an automated **post-deploy smoke** whose failure surfaces a documented one-command rollback. Async EventBridge cron jobs get an explicit failure boundary (DLQ or `on_failure` destination) so a repeatedly-failing cron is recoverable rather than silently discarded.

## Non-goals

- No staging environment. Single `prod` tier stays (audit O-3); this RFC adds gates around it, not a new tier.
- No automated canary/alias traffic-shift rollback. Rollback here = a documented, human-triggered "redeploy previous artifact" runbook, optionally scripted — not blue/green.
- No new test **authoring** beyond thin smoke assertions. The existing suites are wired in as-is; broadening coverage is separate work.
- No frontend browser-flow (Playwright) gate — that belongs to `REFACTOR-frontend-member-surface` (test-net step). This RFC's front gate is the existing `astro check` + `lint` + `api.gen.ts` diff, moved to PR stage.
- No change to what deploys, only to what must pass first and what happens after.

## Current state

Verified against each repo's `.github/workflows/*.yml` and `infra/*.tf` (audit 2026-07-23):

- **myblog_backend** `deploy.yml`: `on: [push main, pull_request main, workflow_dispatch]`. Jobs `check` (pyright `app/` only), `contract` (openapi export + `git diff --exit-code`), `deploy`. **`pytest` runs nowhere** — not PR, not push, not deploy. Suite exists: `tests/` 46 files, 631 tests, incl. `tests/test_auth_failclosed.py`.
- **myblog_music** `deploy.yml`: PR-triggered `test` job runs pyright + `pytest -m "not integration"` + openapi diff. This is the reference-good gate.
- **myblog_worker** `deploy.yml`: `on: [push main, workflow_dispatch]` — **no `pull_request` trigger**. `pytest tests/ -v` runs only post-merge on push. PR-stage CI = none.
- **myblog_front** `main.yml` (`astro check`, `pnpm lint`, `pnpm build`, `api.gen.ts` sync diff) is `on: [push main, workflow_dispatch]` — **push-only**. The only PR-triggered workflow is `code-review.yml` (advisory Claude comment; self-skips without `ANTHROPIC_API_KEY`; never fails the build).
- **myblog_shared_db** `ci.yml`: PR-triggered schema-parity `test` (intra-repo only).
- **Deploy safety**: all 4 deploy workflows have `concurrency` serialization + `needs:[check/test]` pre-gate + detect-only CloudWatch alarms (SNS email). **No post-deploy smoke, no health gate, no rollback step.** Deploy = `aws lambda update-function-code` / `aws s3 sync` + CloudFront invalidation. Recovery is manual redeploy; no rollback runbook documented (`grep rollback/staging/canary` over ops docs = 0).
- **Async failure boundary**: SQS `blogSQS` has DLQ `album-sync-dlq` (`maxReceiveCount=3`). The worker Lambda has **no** `dead_letter_config`, so the ~10 EventBridge cron job types (album_ingest, lastfm, member_poll, release pollers, saved_tracks, lyrics, artist_photo, alias) rely on Lambda async retry (2×) then silent discard. `FailedInvocations` alarm covers only 2 of ~10 rules (`monitoring.tf`).
- A smoke harness already exists: `scripts/smoke.sh` / `smoke.py` (Cognito USER_AUTH; password in SSM `/myblog/smoke`). It is run **manually** post-merge per CLAUDE.md workflow, not by CI.

## Target state

- **backend**: a PR-triggered job runs `pytest -m "not integration"` (mirroring music's marker split) and blocks merge on failure. Integration-marked tests stay excluded (need a live DB).
- **worker**: `deploy.yml` gains a `pull_request` trigger for its existing `test` job (or a dedicated `ci.yml`), so `pytest tests/` blocks merge.
- **front**: the `check` job (astro check + lint + build + api.gen.ts diff) runs on `pull_request` (in addition to, or moved from, push), blocking merge. `code-review.yml` stays advisory.
- **deploy smoke**: each deploy job, after `update-function-code` / S3 sync completes, runs a minimal smoke assertion (a scoped subset of `scripts/smoke.py`) against the just-deployed surface. A non-zero smoke exit fails the workflow run and emits the rollback instruction. (Note: Lambda code is already live at that point — the smoke is detect-and-alert-fast + rollback-trigger, not a pre-cutover gate. This limitation is documented, not hidden.)
- **rollback runbook**: `infra/README.md` (or a new `docs/ops/rollback.md`) documents the exact one-command redeploy-previous-artifact per service (re-run the prior green deploy / `update-function-code` to the previous S3 bundle / CloudFront invalidation).
- **async boundary**: worker Lambda gets a `dead_letter_config` (SQS DLQ) or per-rule `on_failure` destinations for the cron paths, plus `FailedInvocations` alarm coverage extended to the remaining crons.

## Steps

Steps are independently mergeable. **Order 1 → 2 → 3 → 4 → 5.** Steps 1–3 are CI-only (no infra, no prod change) and low-risk; Step 4 touches infra (needs full `terraform plan` + human apply per hard rule #6); Step 5 is a doc + optional script.

### Step 1 — backend pytest as a PR gate (P0)

Add a `test` job (or extend `check`) in `myblog_backend/.github/workflows/deploy.yml` running `pytest -m "not integration"`, gated on `pull_request`, added to `deploy: needs`. Confirm the marker exists / integration tests are marked; if not, mark them (test-only change).

**Verification**:
```
# locally, mirror what CI will run:
cd myblog_backend && pytest -m "not integration"   # expect ~554 passed
# open a throwaway PR that breaks one assertion → CI red → confirms it blocks
```
**Rollback**: revert the workflow edit (CI-only, no prod impact).

> ✅ Done 2026-07-23, SHA `4018f50` (backend #130). Added a `test` job (`pytest -m "not integration"`) to `deploy.yml` + `deploy: needs`; registered the `integration` marker in `pyproject.toml` (repo .gitignore blocks `*.ini`/`*.cfg`); marked the 6 `TEST_DB_URL` integration suites; added `requirements-test.txt` (pytest + boto3 — the gate immediately caught boto3 missing from CI, a runtime-provided dep, audit C-10). PR CI: 554 passed / 77 deselected. Prod smoke 19/0 post-deploy.

---

### Step 2 — worker + front PR gates (P1)

- `myblog_worker`: add `pull_request: branches: [main]` trigger so the existing `test` job runs on PRs.
- `myblog_front`: make the `check` job run on `pull_request` (keep push-deploy behavior intact — the `deploy` job stays push-only via its `if` ref guard).

**Verification**:
```
# worker: PR with a failing test → CI red
# front: PR with a lint/astro-check error → check job red; deploy job does not run on PR
```
**Rollback**: revert workflow edits (CI-only).

> ✅ Done 2026-07-23. worker #77 (SHA `4d1d3dd`) + front #306 (SHA `4de9193`). Each added a 4-line `pull_request: branches: [main]` trigger to `on:`; the existing `test`/`check` job now runs on PRs while `deploy` stays push/dispatch-only via its unchanged ref guard. Gate confirmed live on the PRs themselves (triggers self-activate): worker `test` **pass** (3m18s) + `deploy` **skipping**; front `check` **pass** (56s) + `deploy` **skipping** (`code-review.yml` still advisory). Post-merge deploys both green; system prod smoke 19/0. Background security review flagged `ci-cd-trust` (fork PRs get no secrets on `pull_request` → no exposure) and `ci-cd-availability` (shared concurrency group serializes PR checks with deploys — minor queue delay, parity with backend) — both accepted, no change (owner "a" 2026-07-23).

---

### Step 3 — scoped deploy-smoke assertion (P1)

Factor a minimal, read-mostly smoke path out of `scripts/smoke.py` (health + one authed GET per service) callable as `smoke.py --stage prod --scope <service>`. Add a post-deploy step to each deploy job that runs it; non-zero exit fails the run. Requires the smoke password already in SSM `/myblog/smoke` to be reachable from the deploy role (verify IAM read on that parameter; if absent, that's a Step-4 infra item).

**Verification**:
```
scripts/smoke.py --stage prod --scope backend   # green against current prod
# temporarily point at a bad URL → non-zero exit → workflow fails as designed
```
**Rollback**: remove the smoke step; deploy reverts to unguarded (status quo).

> ✅ Done 2026-07-24 (backend #132 `6b0447c`, music #59 `b9b4d42`, worker #78 `ffb1cf7` + waiter/IAM fix #79 `bc008f3`, front #313 `8061c63`). **Scope = health-only** (OQ1 resolved, owner 2026-07-24): no Cognito credentials in CI. Each deploy job gained a post-deploy step, added at the END of the push-only `deploy` job so it runs after the real deploy — detect-and-alert-fast + rollback trigger, not a pre-cutover gate.
>
> Per-service health signal: backend `curl /api/db/ping` → `Database connected`; music `curl /api/music/search/unified` → `albums` body; front `curl /` → HTML; all with a 5× retry to absorb propagation. Worker has no HTTP surface → `wait function-updated-v2` then an empty-`{}` invoke (a pure no-op: no DB/external calls, handler returns `{"batchItemFailures":[]}`), failing on any `FunctionError` (catches an import/entry break in the deployed bundle). Each failure path echoes the roll-back instruction.
>
> **Deviation from the "factor out of `scripts/smoke.py --scope`" plan (deliberate):** CI uses **inline** per-service assertions, not the workspace smoke script. Running the workspace script from a service deploy job would require adding `WORKSPACE_GITHUB_TOKEN` (cross-repo sparse-checkout) to backend/music/worker — three new secret wirings — for what is one curl / one invoke each. Inline keeps Step 3 CI-only + zero-new-secrets. The full authed `smoke.py prod` stays the manual post-merge check.
>
> **Prod-verified** before merge (the smoke *logic*, since the step only executes post-merge on a real deploy): the three curls hit live prod with markers present; the worker `{}` invoke returned StatusCode 200 / no FunctionError. Post-merge, all four deploy runs' smoke steps passed.
>
> **IAM finding + fix (worker).** The first worker deploy's smoke failed `AccessDeniedException` on `lambda:GetFunctionConfiguration` — the v1 `function-updated` waiter polls that action, which the least-privilege **`lambda-deploy-only`** deploy-user policy does not grant (it allows `UpdateFunctionCode` + `GetFunction`). The code deploy itself succeeded (prod worker healthy). Fix (owner-approved "grant IAM now" 2026-07-24): (a) switch the workflow to the `function-updated-v2` waiter, which polls the already-granted `GetFunction`; (b) add a one-statement `lambda:InvokeFunction` grant **scoped to `blogWorkerLambda`** to `lambda-deploy-only` (new default version **v2**; roll back = `aws iam set-default-policy-version … v1`). **The `github-actions-deploy` user + `lambda-deploy-only` policy are manual, NOT Terraform-managed** — this grant lives only in AWS; a future IaC-the-deploy-user chore should capture it.

---

### Step 4 — async failure boundary + alarm coverage (P1, infra)

Add worker Lambda `dead_letter_config` (or per-cron `on_failure` destination) and extend `FailedInvocations` alarms to the uncovered cron rules in `infra/`. Full `terraform plan`; stop on unexpected drift; human applies (hard rule #6).

**Verification**:
```
terraform plan    # only the intended DLQ/alarm resources
# post-apply: force a cron failure in a scratch invoke → payload lands in DLQ / alarm fires
```
**Rollback**: `terraform apply` the reverted config (removes DLQ/alarm; no data loss — DLQ is additive).

---

### Step 5 — rollback runbook (P1, docs)

Document per-service "redeploy previous artifact" in `infra/README.md` or `docs/ops/rollback.md`: how to re-run the last green deploy, restore the previous S3 front bundle, and invalidate CloudFront. Optionally script it.

**Verification**: dry-run the documented commands in a non-mutating form (`--dry-run` / echo) and confirm they reference real, current artifact locations.

## Open questions

1. ~~**Smoke credential exposure in CI**~~ — **RESOLVED 2026-07-24 → health-only (option b).** No Cognito credentials in CI; each deploy job asserts an unauthed health signal (worker via an empty-`{}` no-op invoke). The full authed `smoke.py prod` stays the manual post-merge check.
2. **Integration-test DB in CI** — backend has `tests/integration/*` needing a live DB. Keep excluded (marker) or provide a CI DB (like worker's `TEST_DB_URL` GHA secret)? Blocks how complete Step 1 is. Default: exclude, matching music.
3. **Worker DLQ vs on_failure** — a single function-level SQS DLQ catches both SQS-path and async-cron failures mixed; per-rule `on_failure` destinations isolate but multiply resources. Blocks Step 4 shape.

## Decisions log

| Date | Decision | Step |
|------|----------|------|
| 2026-07-24 | Deploy smoke scope = **health-only** (no Cognito creds in CI); OQ1 resolved to option (b). | 3 |
| 2026-07-24 | CI uses **inline** per-service assertions, not `smoke.py --scope` — avoids adding `WORKSPACE_GITHUB_TOKEN` to 3 repos for one curl/invoke each. | 3 |
| 2026-07-24 | Worker health = empty-`{}` no-op invoke + `function-updated-v2` waiter; grant `lambda:InvokeFunction` (scoped to blogWorkerLambda) on the manual `lambda-deploy-only` policy (v2). Owner "grant IAM now". | 3 |
