# ADR 0009: Remove three unused GitHub-OIDC IAM roles

- **Date**: 2026-08-26
- **Status**: accepted (owner-approved in-session), applied
- **Scope**: AWS account `338183196042`, IAM only. No repository, workflow, or Terraform change.
- **RFC**: `docs/rfcs/SEC-system-hardening.md` Step 3

## Context

An inventory for the OIDC migration found that the account already trusts GitHub's OIDC provider —
`arn:aws:iam::338183196042:oidc-provider/token.actions.githubusercontent.com`, created 2025-10-14 —
and that **three IAM roles trusting it already exist**. None is referenced by any workflow in any of
the six repositories: no `.github/workflows/*` file in `myblog-workspace`, `myblog_front`,
`myblog_backend`, `myblog_music`, `myblog_worker`, or `myblog_shared_db` contains `role-to-assume`
or declares `id-token: write`, which is required to obtain an OIDC token at all. None is managed by
Terraform — `infra/*.tf` declares no `aws_iam_openid_connect_provider` and no `aws_iam_role` other
than the three Lambda execution roles in `iam_roles.tf`. All three were created by hand in October
2025 and then abandoned.

The reason to act rather than leave them is `git`. Its trust policy matches
`token.actions.githubusercontent.com:sub` against `repo:hyuntohoon/*` — **every repository the owner
has, on every ref**: any branch, any tag, any pull-request ref, and any repository created in
future. It carries `AmazonS3FullAccess`, `AWSLambda_FullAccess`, and `AWSCloudFormationFullAccess`.
`AmazonS3FullAccess` covers all three buckets in the account, including
`myblog-terraform-state-338183196042`, which holds the Terraform state for the whole system. So any
workflow run that could be induced in any of the owner's repositories — including a repository with
no production role at all — could assume full control of production storage, all Lambda code, and
the infrastructure state file. `RoleLastUsed` is empty: it has never been assumed. It is pure
attack surface with no operational value.

The other two are lower-risk but equally unused:

- `myblog-prod-github-deploy-role` — correctly scoped to `repo:hyuntohoon/myblog:ref:refs/heads/main`
  and `.../dev`, but its Lambda statement targets `myblog-prod-api`, a function that no longer exists
  (`aws lambda get-function --function-name myblog-prod-api` → `ResourceNotFoundException`; the
  function is now `ratemymusic-api`). Never assumed.
- `GitHubActionsDeployRole` — scoped to `repo:hyuntohoon/myblog_backend:ref:refs/heads/main`, but
  carrying `AWSLambda_FullAccess`, `AmazonAPIGatewayAdministrator`, `SecretsManagerReadWrite`, and
  `AWSCloudFormationFullAccess` — none of them resource-scoped. Assumed exactly once, on
  2025-10-22T07:37:40Z, the day it was created, and never since.

A correction worth recording, because it was nearly acted on: the inventory pass initially reported
that `myblog-prod-github-deploy-role` had **no** `sub` condition and could be assumed by any
repository on GitHub. Reading the trust policy directly disproved that — the `StringLike` block is
present and correctly scoped. The wildcard problem is real, but it belongs to `git`, not to that
role.

## Decision

Delete all three roles. The OIDC migration in `SEC-system-hardening` Step 3 creates purpose-built,
least-privilege roles scoped to one repository and one ref, so none of these three is worth
adapting. Their full definitions are preserved below; each can be recreated from this record.

`myblog-prod-github-deploy-role`'s inline policy is, however, an almost exact statement of what
`myblog_front`'s deploy job actually does (list the bucket, put/delete objects under it, invalidate
CloudFront). Step 3 reuses that *shape* — not the role — as the starting point for the new front
deploy role, minus the stale Lambda statement and with the `cloudfront:CreateInvalidation`
`Resource: "*"` narrowed to the one distribution.

## Backup — full definitions as of deletion

### `git` (created 2025-10-22T08:43:50Z, never used)

Attached: `AmazonS3FullAccess`, `AWSCloudFormationFullAccess`, `AWSLambda_FullAccess`. No inline policies.

```json
{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Federated":"arn:aws:iam::338183196042:oidc-provider/token.actions.githubusercontent.com"},"Action":"sts:AssumeRoleWithWebIdentity","Condition":{"StringEquals":{"token.actions.githubusercontent.com:aud":"sts.amazonaws.com"},"StringLike":{"token.actions.githubusercontent.com:sub":["repo:hyuntohoon/*","repo:hyuntohoon/*"]}}}]}
```

(The duplicated `sub` entry is verbatim from the live policy, not a transcription error.)

### `myblog-prod-github-deploy-role` (created 2025-10-14T07:51:57Z, never used)

No attached managed policies. One inline policy, `myblog-prod-deploy-policy`.

```json
{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Federated":"arn:aws:iam::338183196042:oidc-provider/token.actions.githubusercontent.com"},"Action":"sts:AssumeRoleWithWebIdentity","Condition":{"StringEquals":{"token.actions.githubusercontent.com:aud":"sts.amazonaws.com"},"StringLike":{"token.actions.githubusercontent.com:sub":["repo:hyuntohoon/myblog:ref:refs/heads/main","repo:hyuntohoon/myblog:ref:refs/heads/dev"]}}}]}
```

```json
{"Version":"2012-10-17","Statement":[{"Sid":"LambdaCodeUpdate","Effect":"Allow","Action":["lambda:GetFunction","lambda:UpdateFunctionCode","lambda:PublishVersion","lambda:UpdateFunctionConfiguration"],"Resource":"arn:aws:lambda:ap-northeast-2:338183196042:function:myblog-prod-api"},{"Sid":"S3UploadFrontend","Effect":"Allow","Action":["s3:ListBucket"],"Resource":"arn:aws:s3:::myblog-prod-web"},{"Sid":"S3PutDeleteFrontendObjects","Effect":"Allow","Action":["s3:PutObject","s3:DeleteObject","s3:PutObjectAcl"],"Resource":"arn:aws:s3:::myblog-prod-web/*"},{"Sid":"CloudFrontInvalidateTEMP","Effect":"Allow","Action":"cloudfront:CreateInvalidation","Resource":"*"}]}
```

### `GitHubActionsDeployRole` (created 2025-10-22T07:12:31Z, last used 2025-10-22T07:37:40Z)

Attached: `AmazonAPIGatewayAdministrator`, `CloudWatchLogsFullAccess`, `SecretsManagerReadWrite`,
`AWSCloudFormationFullAccess`, `AWSLambda_FullAccess`. No inline policies.

```json
{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Federated":"arn:aws:iam::338183196042:oidc-provider/token.actions.githubusercontent.com"},"Action":"sts:AssumeRoleWithWebIdentity","Condition":{"StringEquals":{"token.actions.githubusercontent.com:iss":"https://token.actions.githubusercontent.com","token.actions.githubusercontent.com:aud":"sts.amazonaws.com"},"StringLike":{"token.actions.githubusercontent.com:sub":"repo:hyuntohoon/myblog_backend:ref:refs/heads/main"}}}]}
```

## Consequences

- No deploy lane changes. None of the three deleted roles was in any deploy path.

  **Correction, added after review.** An earlier revision of this line said all four deploy jobs
  authenticate with "static IAM user keys". That is wrong for `myblog_front`, and the error mattered
  enough to leave the correction visible rather than silently rewrite it. Three lanes — backend,
  music, worker — use the `github-actions-deploy` IAM user, whose only policy is
  `lambda-deploy-only` and whose key's last recorded use is against `lambda`. `myblog_front` uses
  the **AWS root account's access key**. Evidence, from the IAM credential report and the run log,
  all gathered without reading any secret value:

  | Fact | Value |
  |---|---|
  | root `access_key_2` last rotated | `2025-10-22T02:36:36Z` |
  | `myblog_front` secret `AWS_ACCESS_KEY_ID` last updated | `2025-10-22T02:36:47Z` — 11 s later, never since |
  | root `access_key_2` last used | `2026-08-26T06:09:00Z`, service `cloudfront` |
  | front deploy run 32936631790, CloudFront invalidation step | `2026-08-26T06:09:51Z` |
  | `github-actions-deploy` key last used | service `lambda` — its policy grants no S3 or CloudFront action at all |

  No IAM user in the account holds any S3 or CloudFront permission, and front's deploy demonstrably
  performs both. `myblog_front` is a **public** repository. The root account cannot be constrained
  by an IAM policy, a permission boundary, or an SCP, so this is a wider grant than the `git` role
  deleted above.

  This makes the OIDC migration remediation rather than hygiene, and it adds a termination step that
  is **not** "delete the repo secrets": deleting the GitHub secrets leaves both root keys active in
  AWS. Root keys can only be removed by signing in as root with MFA, which is the owner's action,
  not Claude's. The account also carries a **second** active root key, `access_key_1`, last used
  `2025-12-10` against `cloudformation` and unused since. Tracked in
  `docs/rfcs/SEC-system-hardening.md` Step 3.
- The OIDC provider itself is **kept** — Step 3 needs it, and it is the one piece of this
  hand-built setup that is correct.
- The account's remaining GitHub-OIDC trust surface after this change is zero, until Step 3 adds one
  role scoped to one repository and one ref.
- These roles are not in Terraform, so `terraform plan` neither shows nor reverts this change. That
  asymmetry is itself a finding: Step 3 puts the new role in `infra/` so the next person reads it in
  code rather than discovering it in the console.
