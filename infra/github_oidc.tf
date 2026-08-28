# GitHub Actions → AWS with short-lived OIDC-assumed roles.
# SEC-system-hardening Step 3. See docs/rfcs/SEC-system-hardening.md.
#
# Why the provider is read, not managed: the OIDC provider was created by hand on
# 2025-10-14 and is an account-wide trust anchor shared by every future deploy lane.
# Importing it into this stack would put it inside a blast radius that a single
# `terraform destroy` could take out, and removing it would break every lane at once
# rather than one. It is referenced, never owned.
#
# Three hand-made roles that trusted this provider — `git`, `myblog-prod-github-deploy-role`,
# and `GitHubActionsDeployRole` — were deleted on 2026-08-26; `git` alone trusted
# `repo:hyuntohoon/*` (any repo, any ref) with S3/Lambda/CloudFormation FullAccess. Full
# definitions and the reasoning are in docs/archive/decisions/0009-remove-orphan-github-oidc-roles.md.
# Every role below is scoped to one repository and one ref, and none carries a `*` resource
# except where the AWS API itself has no resource to scope to.

data "aws_iam_openid_connect_provider" "github" {
  url = "https://token.actions.githubusercontent.com"
}

locals {
  github_owner = "hyuntohoon"

  # `sub` is matched with StringEquals, not StringLike. StringLike is what let the
  # deleted `git` role accept `repo:hyuntohoon/*`; with StringEquals a wildcard is not
  # expressible, so the branch below is the only ref that can ever assume the role.
  # `workflow_dispatch` on main produces this same `sub`, so manual redeploys still work;
  # a pull_request run produces `...:pull_request` and cannot.
  github_front_sub = "repo:${local.github_owner}/myblog_front:ref:refs/heads/main"

  # `sub` alone is NOT enough, and this is the part that is easy to get wrong.
  # It pins the *ref*, not the *workflow*: a `pull_request_target` run reports
  # `GITHUB_REF` as the base branch, so its `sub` is also `...:ref:refs/heads/main`.
  # myblog_front is a PUBLIC repository, so anyone can open a fork PR against it —
  # and if a `pull_request_target` workflow with `id-token: write` were ever added,
  # a fork PR author would inherit production S3 write. The same applies to
  # `workflow_run`, `schedule`, and every other event that runs on the default branch.
  # `job_workflow_ref` closes that: only this one workflow file, on this one ref,
  # can assume the role, whatever event started it.
  #
  # A `repository_owner = "hyuntohoon"` condition was tried alongside these and is
  # deliberately NOT here: with it present, every assume-role attempt failed with
  # `Not authorized to perform sts:AssumeRoleWithWebIdentity`. Established by bisect —
  # aud+sub alone deployed green (run 32998312450), and adding job_workflow_ref stayed
  # green (run 32998882925), so `repository_owner` was the only condition that broke it.
  # Why it does not match was not determined, and is not worth determining: the claim is
  # redundant, since both `sub` and `job_workflow_ref` already begin with the owner.
  # The failure is itself the negative test this role otherwise lacks — a condition that
  # does not match produces a hard deny, not a silent pass.
  github_front_workflow_ref = "${local.github_owner}/myblog_front/.github/workflows/main.yml@refs/heads/main"
}

# --- myblog_front: build → S3 → CloudFront invalidation ---

resource "aws_iam_role" "github_front_deploy" {
  name = "myblog-github-front-deploy"
  path = "/"

  # 1h is the floor AWS allows and more than the deploy needs (~4 min observed).
  max_session_duration = 3600

  description = "GitHub Actions OIDC deploy role for myblog_front (main only). SEC-system-hardening Step 3."

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Federated = data.aws_iam_openid_connect_provider.github.arn }
      Action    = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringEquals = {
          "token.actions.githubusercontent.com:aud"              = "sts.amazonaws.com"
          "token.actions.githubusercontent.com:sub"              = local.github_front_sub
          "token.actions.githubusercontent.com:job_workflow_ref" = local.github_front_workflow_ref
        }
      }
    }]
  })
}

# Exactly the four actions the deploy job performs, and nothing else:
#   aws s3 sync dist/_astro/ s3://myblog-prod-web/_astro/     -> ListBucket + PutObject
#   aws s3 sync dist/ s3://myblog-prod-web --delete           -> ListBucket + PutObject + DeleteObject
#   aws cloudfront create-invalidation --distribution-id ...  -> CreateInvalidation
# Deliberately absent: s3:GetObject (sync compares against ListObjectsV2 output, it does not
# read objects back), s3:PutObjectAcl (no --acl flag; the bucket policy grants public read),
# and every lambda/apigateway/secretsmanager action the deleted roles carried.
resource "aws_iam_role_policy" "github_front_deploy" {
  name = "front-deploy"
  role = aws_iam_role.github_front_deploy.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "ListWebBucket"
        Effect   = "Allow"
        Action   = ["s3:ListBucket"]
        Resource = aws_s3_bucket.myblog_prod_web.arn
      },
      {
        Sid      = "WriteWebObjects"
        Effect   = "Allow"
        Action   = ["s3:PutObject", "s3:DeleteObject"]
        Resource = "${aws_s3_bucket.myblog_prod_web.arn}/*"
      },
      {
        Sid      = "InvalidateOwnDistribution"
        Effect   = "Allow"
        Action   = ["cloudfront:CreateInvalidation"]
        Resource = aws_cloudfront_distribution.myblog.arn
      },
    ]
  })
}

output "github_front_deploy_role_arn" {
  description = "Set as the myblog_front repo variable AWS_DEPLOY_ROLE_ARN."
  value       = aws_iam_role.github_front_deploy.arn
}

# --- myblog_backend / myblog_music / myblog_worker: Lambda code deploys ---
#
# SEC-system-hardening Step 3c. Same trust recipe as the front lane above, arrived at
# the hard way: `repository_owner` is deliberately ABSENT. It was tried on the front
# role and every assume-role attempt failed with "Not authorized to perform
# sts:AssumeRoleWithWebIdentity" until it was removed (bisected across runs
# 32997705046 / 32998312450 / 32998882925). It is also redundant — `sub` and
# `job_workflow_ref` both already begin with the owner.
#
# These three replace the shared `github-actions-deploy` IAM user, whose single key
# all three lanes have used since 2026-03-17. That user's policy allows
# UpdateFunctionCode on FOUR functions to whichever lane holds the key, so a
# compromise of any one repo's secret could overwrite any of the others' code. Per-lane
# roles remove that: each can write exactly one function.

locals {
  github_lambda_lanes = {
    backend = {
      repo          = "myblog_backend"
      function_name = "ratemymusic-api"
      # update-function-code is the only call this lane makes.
      extra_actions = []
    }
    music = {
      repo          = "myblog_music"
      function_name = "musicApi"
      extra_actions = []
    }
    worker = {
      repo          = "myblog_worker"
      function_name = "blogWorkerLambda"
      # `aws lambda wait function-updated-v2` polls GetFunction (NOT
      # GetFunctionConfiguration — the v1 waiter uses that one and the old
      # least-privilege policy did not allow it, which is why the workflow pins the
      # v2 waiter). The post-deploy health check then invokes with an empty event.
      extra_actions = ["lambda:GetFunction", "lambda:InvokeFunction"]
    }
  }
}

resource "aws_iam_role" "github_lambda_deploy" {
  for_each = local.github_lambda_lanes

  name                 = "myblog-github-${each.key}-deploy"
  path                 = "/"
  max_session_duration = 3600
  description          = "GitHub Actions OIDC deploy role for ${each.value.repo} (main only). SEC-system-hardening Step 3c."

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Federated = data.aws_iam_openid_connect_provider.github.arn }
      Action    = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringEquals = {
          "token.actions.githubusercontent.com:aud"              = "sts.amazonaws.com"
          "token.actions.githubusercontent.com:sub"              = "repo:${local.github_owner}/${each.value.repo}:ref:refs/heads/main"
          "token.actions.githubusercontent.com:job_workflow_ref" = "${local.github_owner}/${each.value.repo}/.github/workflows/deploy.yml@refs/heads/main"
        }
      }
    }]
  })
}

resource "aws_iam_role_policy" "github_lambda_deploy" {
  for_each = local.github_lambda_lanes

  name = "${each.key}-lambda-deploy"
  role = aws_iam_role.github_lambda_deploy[each.key].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid      = "DeployOwnFunctionOnly"
      Effect   = "Allow"
      Action   = concat(["lambda:UpdateFunctionCode"], each.value.extra_actions)
      Resource = "arn:aws:lambda:${var.aws_region}:${var.account_id}:function:${each.value.function_name}"
    }]
  })
}

output "github_lambda_deploy_role_arns" {
  description = "Set each as its repo's AWS_DEPLOY_ROLE_ARN variable."
  value       = { for k, r in aws_iam_role.github_lambda_deploy : k => r.arn }
}
