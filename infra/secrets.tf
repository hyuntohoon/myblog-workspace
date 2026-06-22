data "aws_secretsmanager_secret" "backend" {
  name = "myblog/backend"
}

data "aws_secretsmanager_secret" "worker" {
  name = "myblog/worker"
}

data "aws_secretsmanager_secret" "music" {
  name = "myblog/music"
}

# Spotify user OAuth (FEAT-member-dashboard Step 3, Q17). Holds client_id/secret +
# the long-lived refresh token (minted out-of-band, D27). The worker reads it to
# call /me/player/*; the backend reads it only to report connection status.
data "aws_secretsmanager_secret" "spotify" {
  name = "myblog/spotify"
}


resource "aws_iam_policy" "backend_secrets_read" {
  name        = "myblog-backend-secrets-read"
  description = "Allow ratemymusic-api to read its Secrets Manager secret"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["secretsmanager:GetSecretValue"]
      Resource = [data.aws_secretsmanager_secret.backend.arn]
    }]
  })
}

resource "aws_iam_policy" "worker_secrets_read" {
  name        = "myblog-worker-secrets-read"
  description = "Allow blogWorkerLambda to read its Secrets Manager secret"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["secretsmanager:GetSecretValue"]
      Resource = [data.aws_secretsmanager_secret.worker.arn]
    }]
  })
}

resource "aws_iam_policy" "music_secrets_read" {
  name        = "myblog-music-secrets-read"
  description = "Allow musicApi to read its Secrets Manager secret"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["secretsmanager:GetSecretValue"]
      Resource = [data.aws_secretsmanager_secret.music.arn]
    }]
  })
}

resource "aws_iam_role_policy_attachment" "backend_secrets" {
  role       = "myblog-prod-lambda-role"
  policy_arn = aws_iam_policy.backend_secrets_read.arn
}

resource "aws_iam_role_policy_attachment" "worker_secrets" {
  role       = "blogWorkerLambda-role-7w21g7o3"
  policy_arn = aws_iam_policy.worker_secrets_read.arn
}

resource "aws_iam_role_policy_attachment" "music_secrets" {
  role       = "LambdaRDSControlRole"
  policy_arn = aws_iam_policy.music_secrets_read.arn
}

# --- myblog/spotify read: worker (uses the token) + backend (status only) ---
resource "aws_iam_policy" "spotify_secrets_read" {
  name        = "myblog-spotify-secrets-read"
  description = "Allow worker + backend to read the Spotify OAuth secret"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["secretsmanager:GetSecretValue"]
      Resource = [data.aws_secretsmanager_secret.spotify.arn]
    }]
  })
}

resource "aws_iam_role_policy_attachment" "worker_spotify_secrets" {
  role       = "blogWorkerLambda-role-7w21g7o3"
  policy_arn = aws_iam_policy.spotify_secrets_read.arn
}

resource "aws_iam_role_policy_attachment" "backend_spotify_secrets" {
  role       = "myblog-prod-lambda-role"
  policy_arn = aws_iam_policy.spotify_secrets_read.arn
}

# --- myblog/spotify write: worker only (D30 token-rotation write-back) ---
# The worker persists a Spotify-rotated refresh_token + last_successful_refresh_at
# back to myblog/spotify, and flips a needs_reauth marker on an invalid_grant. This
# is a separate policy (not folded into spotify_secrets_read) so the backend, which
# also attaches the read policy, stays read-only. Scoped to the spotify secret.
resource "aws_iam_policy" "spotify_secrets_write" {
  name        = "myblog-spotify-secrets-write"
  description = "Allow blogWorkerLambda to write back the rotated Spotify refresh token"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["secretsmanager:PutSecretValue"]
      Resource = [data.aws_secretsmanager_secret.spotify.arn]
    }]
  })
}

resource "aws_iam_role_policy_attachment" "worker_spotify_secrets_write" {
  role       = "blogWorkerLambda-role-7w21g7o3"
  policy_arn = aws_iam_policy.spotify_secrets_write.arn
}


# --- myblog/anthropic (FEAT-album-research-notes) ---
# Feature-scoped Anthropic API key (RFC Forward-compat: one feature family ↔ one
# credential; FEAT-ai-editorial-critique reuses this entry). Terraform creates
# the CONTAINER only — the SecretString (ANTHROPIC_API_KEY) is set by the owner
# in the console, so no key material ever enters tfstate.
resource "aws_secretsmanager_secret" "anthropic" {
  name        = "myblog/anthropic"
  description = "Anthropic API key for editorial AI features (album research, critique)"
}

# Research worker needs: consume researchSQS + write its own log group + read
# the anthropic secret. The reused worker role's existing grants are scoped to
# blogSQS / the blogWorkerLambda log group only, so this is a separate policy.
resource "aws_iam_policy" "research_worker_extras" {
  name        = "myblog-research-worker"
  description = "researchWorkerLambda: consume researchSQS, own logs, read myblog/anthropic"

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
      {
        Effect   = "Allow"
        Action   = ["secretsmanager:GetSecretValue"]
        Resource = [aws_secretsmanager_secret.anthropic.arn]
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

# --- research worker role: read /myblog/worker + /myblog/anthropic, decrypt ---
resource "aws_iam_policy" "research_worker_ssm_read" {
  name        = "myblog-research-worker-ssm-read"
  description = "Allow researchWorkerLambda to read its SSM params (worker + anthropic)"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["ssm:GetParameter"]
        Resource = ["${local.ssm_param_arn_prefix}/worker", "${local.ssm_param_arn_prefix}/anthropic"]
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
