# CHORE-secrets-ssm-migration (2026-06-22): ALL secrets migrated to SSM Parameter
# Store SecureString (see the SSM section below); every Secrets Manager secret + its
# read/write IAM removed, including the empty myblog/anthropic container. AWS Secrets
# Manager is no longer used by this stack. When FEAT-ai-editorial-critique ships,
# provision myblog/anthropic as an SSM SecureString (RFC Step 6) + an ANTHROPIC_PARAM
# dual-source read — do NOT reintroduce a Secrets Manager secret.

# Research worker needs: consume researchSQS + write its own log group. (anthropic
# read dropped with the secret — re-add an SSM read when the feature ships.)
resource "aws_iam_policy" "research_worker_extras" {
  name        = "myblog-research-worker"
  description = "researchWorkerLambda: consume researchSQS + own logs"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes",
          "sqs:ChangeMessageVisibility",
        ]
        Resource = aws_sqs_queue.research_sqs.arn
      },
      {
        Effect = "Allow"
        Action = ["logs:CreateLogStream", "logs:PutLogEvents"]
        Resource = [
          "arn:aws:logs:${var.aws_region}:${var.account_id}:log-group:/aws/lambda/researchWorkerLambda:*"
        ]
      },
    ]
  })
}

resource "aws_iam_role_policy_attachment" "worker_research_extras" {
  role       = aws_iam_role.worker.name
  policy_arn = aws_iam_policy.research_worker_extras.arn
}

# ============================================================================
# CHORE-secrets-ssm-migration — SSM Parameter Store (SecureString) access.
# ADDITIVE: granted alongside the secretsmanager:GetSecretValue policies above.
# The dual-source loaders prefer SSM (SECRETS_PARAM) and fall back to Secrets
# Manager until the final cleanup step removes the SM grants + secrets.
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

# --- research worker role: read /myblog/worker, decrypt ---
# (anthropic dropped — add ${local.ssm_param_arn_prefix}/anthropic back when FEAT-ai-editorial-critique ships)
resource "aws_iam_policy" "research_worker_ssm_read" {
  name        = "myblog-research-worker-ssm-read"
  description = "Allow researchWorkerLambda to read its SSM param (worker)"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["ssm:GetParameter"]
        Resource = ["${local.ssm_param_arn_prefix}/worker"]
      },
      {
        Effect   = "Allow"
        Action   = ["kms:Decrypt"]
        Resource = [data.aws_kms_alias.ssm.target_key_arn]
      },
    ]
  })
}

resource "aws_iam_role_policy_attachment" "research_worker_ssm" {
  role       = aws_iam_role.worker.name
  policy_arn = aws_iam_policy.research_worker_ssm_read.arn
}
