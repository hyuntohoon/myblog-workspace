# CHORE-secrets-ssm-migration (2026-06-22): ALL secrets migrated to SSM Parameter
# Store SecureString (see the SSM section below); every Secrets Manager secret + its
# read/write IAM removed, including the empty myblog/anthropic container. AWS Secrets
# Manager is no longer used by this stack, and `secretsmanager:ListSecrets` in
# ap-northeast-2 returns an empty list (re-verified 2026-08-28).
#
# The migration's final leg landed 2026-08-28: backend, music and worker no longer
# carry a Secrets Manager fallback in their runtime secret loaders, and each repo
# lints its own runtime tree against a reintroduction. When FEAT-ai-editorial-critique
# ships, provision myblog/anthropic as an SSM SecureString (RFC Step 6) and read it
# with a plain SSM read — an earlier revision of this comment asked for an
# "ANTHROPIC_PARAM dual-source read", which is now exactly the shape that was
# removed. Do NOT reintroduce a Secrets Manager secret or a fallback to one.

# Research worker IAM (consume researchSQS + own log group): REMOVED
# (FIX-bug-audit-2026-07 WS-G) — torn down with researchWorkerLambda + the queue.

# ============================================================================
# CHORE-secrets-ssm-migration — SSM Parameter Store (SecureString) access.
# This is the ONLY secret-read grant any Lambda role holds. It was originally
# additive alongside secretsmanager:GetSecretValue policies; those were removed
# with the secrets themselves in 2026-06, and the runtime fallback that named
# them was removed in 2026-08. Nothing above grants a secretsmanager action.
#
# ORDER: the owner must provision the SSM SecureString params (RFC Step 0) BEFORE
# `terraform plan/apply` — `data.aws_kms_alias.ssm` resolves the AWS-managed key
# that SSM auto-creates on the first SecureString, and kms:Decrypt is scoped to it.
# ============================================================================

data "aws_kms_alias" "ssm" {
  name = "alias/aws/ssm"
}

locals {
  ssm_param_arn_prefix = "arn:aws:ssm:${var.aws_region}:${var.account_id}:parameter/myblog"
}

# --- backend role: read /myblog/backend + /myblog/spotify (status), decrypt ---
resource "aws_iam_policy" "backend_ssm_read" {
  name        = "myblog-backend-ssm-read"
  description = "Allow ratemymusic-api to read its SSM params (backend + spotify status)"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["ssm:GetParameter"]
        Resource = ["${local.ssm_param_arn_prefix}/backend", "${local.ssm_param_arn_prefix}/spotify"]
      },
      {
        Effect   = "Allow"
        Action   = ["kms:Decrypt"]
        Resource = [data.aws_kms_alias.ssm.target_key_arn]
      },
    ]
  })
}

resource "aws_iam_role_policy_attachment" "backend_ssm" {
  role       = "myblog-prod-lambda-role"
  policy_arn = aws_iam_policy.backend_ssm_read.arn
}

# --- music role: read /myblog/music, decrypt ---
resource "aws_iam_policy" "music_ssm_read" {
  name        = "myblog-music-ssm-read"
  description = "Allow musicApi to read its SSM param"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["ssm:GetParameter"]
        Resource = ["${local.ssm_param_arn_prefix}/music"]
      },
      {
        Effect   = "Allow"
        Action   = ["kms:Decrypt"]
        Resource = [data.aws_kms_alias.ssm.target_key_arn]
      },
    ]
  })
}

resource "aws_iam_role_policy_attachment" "music_ssm" {
  role       = "LambdaRDSControlRole"
  policy_arn = aws_iam_policy.music_ssm_read.arn
}

# --- worker role (blogWorkerLambda): read worker+spotify, WRITE spotify, en/decrypt ---
# PutParameter on a SecureString needs kms:Encrypt + GenerateDataKey (write-back, D30);
# scoped to the aws/ssm key. Read-only roles get kms:Decrypt only.
resource "aws_iam_policy" "worker_ssm" {
  name        = "myblog-worker-ssm"
  description = "Allow blogWorkerLambda to read its SSM params + write back the rotated Spotify token"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["ssm:GetParameter"]
        Resource = ["${local.ssm_param_arn_prefix}/worker", "${local.ssm_param_arn_prefix}/spotify"]
      },
      {
        Effect   = "Allow"
        Action   = ["ssm:PutParameter"]
        Resource = ["${local.ssm_param_arn_prefix}/spotify"]
      },
      {
        Effect   = "Allow"
        Action   = ["kms:Decrypt", "kms:Encrypt", "kms:GenerateDataKey"]
        Resource = [data.aws_kms_alias.ssm.target_key_arn]
      },
    ]
  })
}

resource "aws_iam_role_policy_attachment" "worker_ssm_attach" {
  role       = "blogWorkerLambda-role-7w21g7o3"
  policy_arn = aws_iam_policy.worker_ssm.arn
}

# research worker SSM-read role: REMOVED (FIX-bug-audit-2026-07 WS-G) —
# torn down with researchWorkerLambda. The shared worker role (aws_iam_role.worker)
# is untouched; only the research-specific attachment + policy are gone.
