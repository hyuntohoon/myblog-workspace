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
      ENV                = "prod"
      APP_ENV            = "prod"
      SECRETS_ARN        = data.aws_secretsmanager_secret.backend.arn
      GITHUB_REPO_OWNER  = "hyuntohoon"
      GITHUB_REPO_NAME   = "myblog_front"
      GITHUB_REPO_BRANCH = "main"
      CONTENT_DIR        = "content/blog"
      # FEAT-member-dashboard Step 3: manual "지금 새로고침" → SQS; 연동 status read.
      SQS_QUEUE_URL       = aws_sqs_queue.blog_sqs.url
      SPOTIFY_SECRETS_ARN = data.aws_secretsmanager_secret.spotify.arn
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
      FASTAPI_ROOT_PATH    = "/api"
      QUEUE_NAME           = "blogSQS"
      SECRETS_ARN          = data.aws_secretsmanager_secret.music.arn
      COGNITO_USER_POOL_ID = aws_cognito_user_pool.myblog_admin.id
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
      SQS_QUEUE_URL       = aws_sqs_queue.blog_sqs.url
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
