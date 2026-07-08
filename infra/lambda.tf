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
      # FEAT-multi-user-accounts 0d: DELETE /api/me refuses this sub (403) so the
      # blog-admin identity can't self-delete via the member flow. Value = the
      # owner account's Cognito sub. Points at zlxlgus123@gmail.com (CONFIRMED),
      # the account actually used to sign in; the original naver.com native user
      # (9488ed3c…) is stuck in FORCE_CHANGE_PASSWORD, so require_owner 403'd the
      # live admin on all owner-gated routes (buckets/library/posts) until repointed.
      OWNER_SUB            = "0468fd3c-2011-70f5-0681-b852ddaade41"
      GITHUB_REPO_OWNER    = "hyuntohoon"
      GITHUB_REPO_NAME     = "myblog_front"
      GITHUB_REPO_BRANCH   = "main"
      CONTENT_DIR          = "content/blog"
      # FEAT-member-dashboard Step 3: manual "지금 새로고침" → SQS; 연동 status read.
      SQS_QUEUE_URL = aws_sqs_queue.blog_sqs.url
      # CHORE-secrets-ssm-migration: secrets read from SSM Parameter Store (SM removed Step 7).
      SECRETS_PARAM         = "/myblog/backend"
      SPOTIFY_SECRETS_PARAM = "/myblog/spotify" # status read only; worker owns write-back
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
      SECRETS_PARAM        = "/myblog/music" # CHORE-secrets-ssm-migration: SSM Parameter Store
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
      # FEAT-member-dashboard Step 3: Spotify user OAuth creds + re-enqueue queue.
      # CHORE-secrets-ssm-migration: secrets from SSM Parameter Store (SM removed Step 7).
      SECRETS_PARAM         = "/myblog/worker"
      SPOTIFY_SECRETS_PARAM = "/myblog/spotify" # read + token write-back via put_parameter
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

# --- researchWorkerLambda / researchSQS: REMOVED (FIX-bug-audit-2026-07 WS-G) ---
# The research pipeline runs in $0/local-poller mode (myblog_backend
# research_service.py: "NO SQS send"; scripts/research_poller.py reads the DB).
# The function was live-wired to researchSQS but worker CI only ever deployed
# blogWorkerLambda and the worker has no research handler branch — any message
# reaching researchSQS was logged "Unknown message format" and silently deleted.
# Owner decision 2026-07-07: tear down the whole unused path (function + ESM +
# both queues + dedicated IAM) rather than build a consumer for a dormant queue.
