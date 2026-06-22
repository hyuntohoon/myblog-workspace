# Lambda functions.
#
# Split of ownership:
#   - Terraform owns CONFIG (role, handler, runtime, timeout, memory, env).
#   - Each service's CI owns CODE via `aws lambda update-function-code`.
#     `ignore_changes` on the code attributes keeps the two from fighting.
#
# `placeholder.zip` only satisfies the required code argument; it is never
# uploaded because filename/source_code_hash are ignored after import.

locals {
  lambda_role_prefix = "arn:aws:iam::${var.account_id}:role"
}

# --- ratemymusic-api (myblog_backend) ---
resource "aws_lambda_function" "backend" {
  function_name = "ratemymusic-api"
  role          = "${local.lambda_role_prefix}/myblog-prod-lambda-role"
  handler       = "app.main.handler"
  runtime       = "python3.12"
  architectures = ["arm64"]
  timeout       = 15 # corrected from 3 (cold-start safety)
  memory_size   = 512
  filename      = "placeholder.zip"

  environment {
    variables = {
      ENV     = "prod"
      APP_ENV = "prod"
      # STAB-2 / AUTH-5: backend require_cognito_token was a no-op in prod
      # because this was never set. With auth.py now fail-closed, APPLY THIS
      # (and verify JWKS reachable) BEFORE deploying the fail-closed backend.
      COGNITO_USER_POOL_ID = aws_cognito_user_pool.myblog_admin.id
      SECRETS_ARN          = data.aws_secretsmanager_secret.backend.arn
      GITHUB_REPO_OWNER    = "hyuntohoon"
      GITHUB_REPO_NAME     = "myblog_front"
      GITHUB_REPO_BRANCH   = "main"
      CONTENT_DIR          = "content/blog"
      # FEAT-member-dashboard Step 3: manual "지금 새로고침" → SQS; 연동 status read.
      SQS_QUEUE_URL       = aws_sqs_queue.blog_sqs.url
      SPOTIFY_SECRETS_ARN = data.aws_secretsmanager_secret.spotify.arn
      # CHORE-secrets-ssm-migration cutover switches. Empty = read Secrets Manager
      # (no-op). Set to the SSM SecureString name + apply to cut THIS service over
      # (one at a time = rule-#4 prod-observe gate); empty again to revert.
      SECRETS_PARAM         = "/myblog/backend" # CHORE-secrets-ssm-migration: cut over to SSM
      SPOTIFY_SECRETS_PARAM = "/myblog/spotify" # cut over (status read only; worker owns write-back)
      # FEAT-spotify-library-sync: read-only mirror for the /profile "검토 모드" banner
      # (backend never writes Spotify — rule #9). Keep in sync with the worker value.
      SPOTIFY_LIBRARY_WRITES_ENABLED = "true"
    }
  }

  lifecycle {
    ignore_changes = [filename, source_code_hash, layers]
  }
}

# --- musicApi (myblog_music) ---
resource "aws_lambda_function" "music" {
  function_name = "musicApi"
  role          = "${local.lambda_role_prefix}/LambdaRDSControlRole"
  handler       = "app.main.handler"
  runtime       = "python3.12"
  architectures = ["arm64"]
  timeout       = 15 # corrected from 10
  memory_size   = 512
  filename      = "placeholder.zip"

  environment {
    variables = {
      # STAB-2 Step 4 (P6-2): ENV=prod activates require_cognito_token on the
      # music Lambda. Only /candidates carries Depends(require_cognito_token), so
      # only it becomes gated; /unified, /albums/*, /artists/* have no such dep
      # and stay public. PREREQ: deploy the myblog_music JWKS->503 handler first
      # (PR #42) + verify the pool's JWKS URL is reachable from this Lambda's
      # egress, else a JWKS outage 500s. Off-switch = remove this ENV line.
      ENV                  = "prod"
      FASTAPI_ROOT_PATH    = "/api"
      QUEUE_NAME           = "blogSQS"
      SECRETS_ARN          = data.aws_secretsmanager_secret.music.arn
      SECRETS_PARAM        = "/myblog/music" # CHORE-secrets-ssm-migration: cut over to SSM
      COGNITO_USER_POOL_ID = aws_cognito_user_pool.myblog_admin.id
      # FEAT-music-search-recall Step 4 (A1): activate the pg_trgm fuzzy/typo
      # search path. Safe only after V12 (pg_trgm extension + GIN indexes) is
      # applied to prod Neon — done 2026-06-05. A/B via the recall gate:
      # off = 0.600, on = 1.000 (Hit@5/Hit@1). Off-switch = set back to "false".
      SEARCH_USE_PG_TRGM = "true"
    }
  }

  lifecycle {
    ignore_changes = [filename, source_code_hash, layers]
  }
}

# --- blogWorkerLambda (myblog_worker) ---
resource "aws_lambda_function" "worker" {
  function_name = "blogWorkerLambda"
  role          = "${local.lambda_role_prefix}/service-role/blogWorkerLambda-role-7w21g7o3"
  handler       = "worker.handler.lambda_handler"
  runtime       = "python3.12"
  architectures = ["arm64"]
  timeout       = 120 # corrected from 10 (batch Spotify sync needs headroom)
  memory_size   = 512
  filename      = "placeholder.zip"

  environment {
    variables = {
      SECRETS_ARN = data.aws_secretsmanager_secret.worker.arn
      # FEAT-member-dashboard Step 3: Spotify user OAuth creds + re-enqueue queue.
      SPOTIFY_SECRETS_ARN = data.aws_secretsmanager_secret.spotify.arn
      # CHORE-secrets-ssm-migration cutover switches (empty = Secrets Manager no-op).
      SECRETS_PARAM         = "/myblog/worker"  # CHORE-secrets-ssm-migration: cut over to SSM
      SPOTIFY_SECRETS_PARAM = "/myblog/spotify" # cut over (read + token write-back via put_parameter)
      SQS_QUEUE_URL         = aws_sqs_queue.blog_sqs.url
      # FEAT-spotify-library-sync Gate 3: enable real PUT/DELETE /me/albums in the
      # reconcile. "false" = plan-only (reads + DB writes + logs intended writes, no
      # Spotify mutation). Flip to "false" + apply to pause real writes.
      SPOTIFY_LIBRARY_WRITES_ENABLED = "true"
    }
  }

  lifecycle {
    ignore_changes = [filename, source_code_hash, layers]
  }
}

# --- SQS event source: blogSQS -> worker ---
# ReportBatchItemFailures lets the worker fail individual records (PR-7);
# only failed records are retried instead of the whole batch.
resource "aws_lambda_event_source_mapping" "worker_sqs" {
  event_source_arn = aws_sqs_queue.blog_sqs.arn
  function_name    = aws_lambda_function.worker.arn
  batch_size       = 10
  enabled          = true

  function_response_types = ["ReportBatchItemFailures"]
}

# --- researchWorkerLambda (myblog_worker, FEAT-album-research-notes) ---
# Same codebase/image as blogWorkerLambda (worker CI must update BOTH functions
# from Step 3 on), but a separate function because research runs are 3–8 min
# Anthropic API calls (timeout 900s vs 120s).
#
# Concurrency cap lives on the SQS event source mapping (scaling_config below),
# NOT as function reserved_concurrent_executions: this account's total concurrent
# execution limit is 10, and any function-level reservation drops the account's
# UnreservedConcurrentExecution below its hard floor of 10 (PutFunctionConcurrency
# 400). ESM maximum_concurrency throttles the researchSQS poller without carving
# out the shared account pool — the SQS-native, recommended mechanism.
resource "aws_lambda_function" "research_worker" {
  function_name = "researchWorkerLambda"
  role          = aws_iam_role.worker.arn
  handler       = "worker.handler.lambda_handler"
  runtime       = "python3.12"
  architectures = ["arm64"]
  timeout       = 900
  memory_size   = 512
  filename      = "placeholder.zip"

  environment {
    variables = {
      SECRETS_ARN   = data.aws_secretsmanager_secret.worker.arn
      SECRETS_PARAM = "/myblog/worker" # CHORE-secrets-ssm-migration: cut over to SSM
      # Feature-scoped key (RFC Forward-compat): myblog/anthropic, value set in
      # console by the owner — never via terraform (no value in tfstate).
      # anthropic SSM migration deferred to RFC Step 6 (feature not yet shipped).
      ANTHROPIC_SECRETS_ARN = aws_secretsmanager_secret.anthropic.arn
    }
  }

  lifecycle {
    ignore_changes = [filename, source_code_hash, layers]
  }
}

# --- SQS event source: researchSQS -> research worker ---
# batch_size 1: one album per invocation; a failure retries only itself.
# maximum_concurrency 2: caps concurrent research runs so a research_mode='all'
# burst (dozens of enqueues) drains ≤2-at-a-time — smooths Anthropic rate limits
# and spend ramp. Min allowed value is 2. Does not touch account reserved pool.
resource "aws_lambda_event_source_mapping" "research_worker_sqs" {
  event_source_arn = aws_sqs_queue.research_sqs.arn
  function_name    = aws_lambda_function.research_worker.arn
  batch_size       = 1
  enabled          = true

  scaling_config {
    maximum_concurrency = 2
  }

  function_response_types = ["ReportBatchItemFailures"]
}
