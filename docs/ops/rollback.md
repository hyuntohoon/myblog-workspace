# Rollback runbook

Per-service "redeploy the previous artifact" steps for when a deploy ships a bad
build. There is a single `prod` tier (no staging/canary — OPS-delivery-safety-gates
non-goal), so rollback = **redeploy known-good code**, not traffic-shift.

Deploys build from source and update Lambda `$LATEST` / sync S3 in place — there is
**no separate artifact registry**, so the canonical rollback is either (A) re-run the
last green deploy (redeploys the previous commit as-is), or (B) `git revert` + push
(ships the reverted source through the normal pipeline). Both re-run the Step 3
post-deploy health smoke, so a successful rollback is self-verifying.

Deploy workflows: backend/music/worker `deploy.yml`, front `main.yml`. All are
`push: [main]` + `workflow_dispatch`, serialized by a `concurrency` group.

---

## A) Fastest — re-run the last green deploy (all services)

Re-running a prior workflow run re-runs it **at that run's original commit**, so
re-running the last green "Deploy" run redeploys the previous code.

1. GitHub → the service repo → **Actions** → the "Deploy …" workflow.
2. Open the **last green run that predates the bad merge**.
3. **Re-run all jobs**.
4. Watch the run's **Post-deploy smoke** step go green (Step 3). If it fails, the
   rollback did not take — fall through to (B).

Use when: the bad change is isolated to one service and a clean previous run exists.

## B) Canonical — `git revert` + push (all services)

```bash
# in the affected service repo, on a branch
git checkout -b fix/rollback-<desc> origin/main
git revert <bad-sha>            # or: git revert <oldest-bad>^..<newest-bad>
git push -u origin HEAD
# open PR → CI (PR gates) green → squash-merge → push-to-main auto-deploys
```

The merge to `main` triggers the normal deploy + Step 3 smoke. Use when: no clean
prior run, or the bad change spans multiple commits.

---

## Per-service specifics

- **backend** (`ratemymusic-api`) / **music** (`musicApi`) / **worker**
  (`blogWorkerLambda`): `aws lambda update-function-code` on `$LATEST`. (A) or (B).
  Direct CLI fallback only if you already hold a known-good bundle:
  `aws lambda update-function-code --function-name <fn> --zip-file fileb://<good>.zip --architectures arm64`
  (the deploy user can update these; region `ap-northeast-2`).
- **front** (S3 + CloudFront): the deploy `aws s3 sync --delete` + CloudFront
  invalidation. HTML is `no-cache`, so a redeploy is visible immediately after the
  invalidation. Prefer (A)/(B) — restoring individual prior S3 objects by hand is
  error-prone. After rollback, confirm `https://www.ratemymusic.blog/` returns the
  expected build.

## Infra (Terraform) rollback

Infra is applied **manually by a human** (merging an infra PR ≠ a prod change).
To roll back an applied infra change: revert the `infra/*.tf` edit, then
`terraform plan` (confirm it only removes the intended resources — additive DLQ/
alarms are safe to drop, no data loss) and `terraform apply`. Requires
`TF_VAR_edge_secret` (SSM `/myblog/backend` → `EDGE_SECRET` key).

## Manual IAM (non-Terraform) rollback

The CI deploy user `github-actions-deploy` + its `lambda-deploy-only` policy are
**manual, not Terraform-managed**. To roll back a policy change:
`aws iam set-default-policy-version --policy-arn arn:aws:iam::338183196042:policy/lambda-deploy-only --version-id v1`
(then delete the unwanted version if desired). See memory
`reference-deploy-user-iam-manual`.
