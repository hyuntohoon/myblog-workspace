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
      # SEC-system-hardening: the app clients whose tokens this service accepts.
      # Comma-separated; UNSET FAILS CLOSED (503) in app/core/auth.py, so this must
      # be applied BEFORE the code that reads it is deployed. Only the SPA client is
      # ever used — by the browser app, scripts/smoke.py and scripts/buckit_nightly.py
      # — and it is the same client the API Gateway authorizer pins
      # (infra/apigateway.tf), so the two layers now agree. MyBlogAdminClient is
      # deliberately NOT listed: nothing in any repo authenticates with it.
      COGNITO_ALLOWED_CLIENT_IDS = aws_cognito_user_pool_client.spa_client.id
      # FEAT-multi-user-accounts 0d: DELETE /api/me refuses this sub (403) so the
      # blog-admin identity can't self-delete via the member flow. Value = the
      # owner account's Cognito sub. Points at zlxlgus123@gmail.com (CONFIRMED),
      # the account actually used to sign in; the original naver.com native user
      # (9488ed3c…) is stuck in FORCE_CHANGE_PASSWORD, so require_owner 403'd the
      # live admin on all owner-gated routes (buckets/library/posts) until repointed.
      OWNER_SUB = "0468fd3c-2011-70f5-0681-b852ddaade41"
      # FIX-nightly-draft-identity Phase A: the nightly draft agent
      # (nightly-agent@ratemymusic.blog, created 2026-07-27). Accepted by
      # require_owner_or_draft_agent on POST /api/posts ONLY — require_owner and
      # its 38 routes are unchanged — and create_post coerces its posts to
      # status='draft', so this identity cannot publish. Empty would mean "no
      # agent" and degrade to owner-only; it is never a wildcard.
      DRAFT_AGENT_SUB    = "64885d4c-00c1-7082-8c40-8cb1a31d8078"
      GITHUB_REPO_OWNER  = "hyuntohoon"
      GITHUB_REPO_NAME   = "myblog_front"
      GITHUB_REPO_BRANCH = "main"
      CONTENT_DIR        = "content/blog"
      # FEAT-member-dashboard Step 3: manual "지금 새로고침" → SQS; 연동 status read.
      SQS_QUEUE_URL = aws_sqs_queue.blog_sqs.url
      # CHORE-secrets-ssm-migration: secrets read from SSM Parameter Store (SM removed Step 7).
      SECRETS_PARAM         = "/myblog/backend"
      SPOTIFY_SECRETS_PARAM = "/myblog/spotify" # status read only; worker owns write-back
      # FEAT-multi-user 3b-c: member refresh-token custody. References the 3b-a
      # alias, so this env update applies together with the owner's CMK apply;
      # until then the backend fails closed (503) on member Spotify connect.
      USER_TOKENS_KMS_KEY_ID = aws_kms_alias.user_tokens.name
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
      ENV               = "prod"
      FASTAPI_ROOT_PATH = "/api"
      # AUDIT-2026-07-26 A-5: QUEUE_NAME alone made SqsClient.__init__ resolve the
      # URL with a blocking sqs:GetQueueUrl on EVERY /candidates call — the client
      # is constructed per request (search.py) and that resolution sits OUTSIDE
      # enqueue_album_sync's best-effort try/except, so an SQS blip 500'd an
      # authed user request instead of just skipping the enqueue. Setting the URL
      # (as backend and worker already do) removes both the round-trip and that
      # failure path. QUEUE_NAME stays: SqsClient still reads it for .fifo detection.
      SQS_QUEUE_URL        = aws_sqs_queue.blog_sqs.url
      QUEUE_NAME           = "blogSQS"
      SECRETS_PARAM        = "/myblog/music" # CHORE-secrets-ssm-migration: SSM Parameter Store
      COGNITO_USER_POOL_ID = aws_cognito_user_pool.myblog_admin.id
      # SEC-system-hardening: the app clients whose tokens this service accepts.
      # Comma-separated; UNSET FAILS CLOSED (503) in app/core/auth.py, so this must
      # be applied BEFORE the code that reads it is deployed. Only the SPA client is
      # ever used — by the browser app, scripts/smoke.py and scripts/buckit_nightly.py
      # — and it is the same client the API Gateway authorizer pins
      # (infra/apigateway.tf), so the two layers now agree. MyBlogAdminClient is
      # deliberately NOT listed: nothing in any repo authenticates with it.
      COGNITO_ALLOWED_CLIENT_IDS = aws_cognito_user_pool_client.spa_client.id
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
      # FEAT-multi-user 3b-d: member token rotation re-encrypt (Decrypt needs no key
      # id). References the 3b-a alias → rides the owner's pending CMK apply, same
      # as the backend twin in this file.
      USER_TOKENS_KMS_KEY_ID = aws_kms_alias.user_tokens.name
    }
  }

  lifecycle {
    ignore_changes = [filename, source_code_hash, layers]
  }
}

# OPS-delivery-safety-gates Step 4 — async cron failure boundary.
# EventBridge invokes the worker ASYNCHRONOUSLY; without an on-failure destination a
# handler that throws (after maximum_retry_attempts async retries) is silently
# dropped. Park the invocation record (payload + error) in worker-cron-dlq for
# inspection/replay. Applies ONLY to async invokes — the SQS-ESM (blogSQS) path is
# unaffected (it has its own redrive DLQ, album-sync-dlq). retry_attempts=2 is the
# Lambda async default, set explicitly so it is managed, not implicit.
resource "aws_lambda_function_event_invoke_config" "worker_async" {
  function_name          = aws_lambda_function.worker.function_name
  maximum_retry_attempts = 2

  destination_config {
    on_failure {
      destination = aws_sqs_queue.worker_cron_dlq.arn
    }
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
