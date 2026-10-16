# Lambda 실행 역할 4개 — Terraform 전체 관리
# secrets-read 정책 attachment는 secrets.tf에서 계속 관리 (중복 제외).
# worker/publish 역할은 콘솔 생성 경로(/service-role/)가 있어 path 명시.

locals {
  lambda_assume_role = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

# --- backend: myblog-prod-lambda-role ---
resource "aws_iam_role" "backend" {
  name               = "myblog-prod-lambda-role"
  path               = "/"
  assume_role_policy = local.lambda_assume_role
}

resource "aws_iam_role_policy_attachment" "backend_vpc" {
  role       = aws_iam_role.backend.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

resource "aws_iam_role_policy_attachment" "backend_basic" {
  role       = aws_iam_role.backend.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "backend_s3" {
  name = "s3-myblog-assets-access"
  role = aws_iam_role.backend.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid      = "AssetsRW"
      Effect   = "Allow"
      Action   = ["s3:GetObject", "s3:PutObject"]
      Resource = "arn:aws:s3:::myblog-prod-assets/*"
    }]
  })
}

# FEAT-multi-user-accounts 0d: DELETE /api/me removes the member's Cognito user
# (개인정보보호법 account deletion). ListUsers resolves sub → Username first (a
# sub is not a Username). Pool-ARN-scoped; no other cognito-idp action granted.
resource "aws_iam_role_policy" "backend_cognito_member_delete" {
  name = "cognito-member-delete"
  role = aws_iam_role.backend.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid      = "MemberDelete"
      Effect   = "Allow"
      Action   = ["cognito-idp:ListUsers", "cognito-idp:AdminDeleteUser"]
      Resource = aws_cognito_user_pool.myblog_admin.arn
    }]
  })
}

# backend inline "ssm" policy: REMOVED (FIX-bug-audit-2026-07 WS-F). Its
# GetDbParams statement pointed at parameter/myblog/prod/db/* — a path that holds
# nothing (real params are /myblog/backend + /myblog/spotify). The backend role's
# actual SSM read + kms:Decrypt come from aws_iam_policy.backend_ssm_read
# (secrets.tf, attached), which is tighter (key-ARN-scoped). This block was fully
# dead and invited "fixing" code toward the wrong path.

# --- music: LambdaRDSControlRole ---
# Producer-only (no SQS ESM) — send-only grant is the inline music_sqs_produce below.
# 제거: AmazonRDSFullAccess (Neon DB, AWS RDS 없음), AmazonSQSFullAccess/ReadOnlyAccess,
#       그리고 STAB-7: AWSLambdaSQSQueueExecutionRole attachment (P7-5 account-wide consume 과다권한).
resource "aws_iam_role" "music" {
  name               = "LambdaRDSControlRole"
  path               = "/"
  assume_role_policy = local.lambda_assume_role
}

# STAB-7 (P7-5): AWSLambdaSQSQueueExecutionRole attachment removed — it granted
# account-wide sqs:ReceiveMessage/DeleteMessage/* on a producer-only Lambda
# (musicApi has no SQS event-source mapping; it only sends, via music_sqs_produce).
# CloudWatch logging is unaffected — logs:* is granted independently by music_rds_ctrl.
resource "aws_iam_role_policy" "music_rds_ctrl" {
  name = "rdscontorller"
  role = aws_iam_role.music.id
  # STAB-7 (P7-1): dropped the dead rds:Start/Stop/DescribeDBInstances statement
  # (acted on a phantom db:blogdb — the stack uses Neon, not AWS RDS). Now logs-only;
  # the "rdscontorller" name is kept to avoid a destroy/recreate.
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"]
        Resource = "*"
      }
    ]
  })
}

resource "aws_iam_role_policy" "music_sqs_produce" {
  name = "sqs-produce-blogSQS"
  role = aws_iam_role.music.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid      = "SqsProduce"
      Effect   = "Allow"
      Action   = ["sqs:GetQueueUrl", "sqs:SendMessage", "sqs:SendMessageBatch"]
      Resource = "arn:aws:sqs:ap-northeast-2:${var.account_id}:blogSQS"
    }]
  })
}

# FEAT-member-dashboard Step 3: backend produces the manual "지금 새로고침" trigger
# ({"job":"spotify_refresh"}); worker re-enqueues recently-played albums not yet in
# the catalog. Both send to the same blogSQS the worker already consumes.
resource "aws_iam_role_policy" "backend_sqs_produce" {
  name = "sqs-produce-blogSQS"
  role = aws_iam_role.backend.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid      = "SqsProduce"
      Effect   = "Allow"
      Action   = ["sqs:GetQueueUrl", "sqs:SendMessage"]
      Resource = "arn:aws:sqs:ap-northeast-2:${var.account_id}:blogSQS"
    }]
  })
}

# FEAT-automation-admin 2d: the owner's automation page (GET /api/admin/automation,
# require_owner) reads AWS liveness — rule state, delivery/failure metrics, the
# three queues' depth and the alarms' state. READ ONLY: no write, invoke, start,
# stop, enable or disable action, and every action that supports resource-level
# permissions is scoped to exactly the resources this config declares.
# cloudwatch:GetMetricData cannot be scoped to a metric (its only resource type is
# a dataset, which plain metric queries do not use), so it is "*"; it reads
# numbers, not configuration. events:ListRules is deliberately absent — it is
# "*"-only, and the backend already knows its rule names, so it uses the scoped
# DescribeRule instead.
resource "aws_iam_role_policy" "backend_automation_read" {
  name = "automation-admin-read"
  role = aws_iam_role.backend.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "DescribeCatalogRules"
        Effect = "Allow"
        Action = ["events:DescribeRule"]
        Resource = concat(
          [for r in aws_cloudwatch_event_rule.worker_cron : r.arn],
          [aws_cloudwatch_event_rule.backend_warm_ping.arn, aws_cloudwatch_event_rule.music_warm_ping.arn],
        )
      },
      {
        Sid    = "DescribeCatalogAlarms"
        Effect = "Allow"
        Action = ["cloudwatch:DescribeAlarms"]
        Resource = concat(
          [for a in aws_cloudwatch_metric_alarm.cron_failed_invocations : a.arn],
          [for a in aws_cloudwatch_metric_alarm.lambda_errors : a.arn],
          [for a in aws_cloudwatch_metric_alarm.lambda_throttles : a.arn],
          [aws_cloudwatch_metric_alarm.dlq_messages.arn, aws_cloudwatch_metric_alarm.worker_cron_dlq_messages.arn],
        )
      },
      {
        Sid      = "ReadMetrics"
        Effect   = "Allow"
        Action   = ["cloudwatch:GetMetricData"]
        Resource = "*"
      },
      {
        Sid    = "ReadQueueDepth"
        Effect = "Allow"
        Action = ["sqs:GetQueueAttributes"]
        Resource = [
          aws_sqs_queue.blog_sqs.arn,
          aws_sqs_queue.album_sync_dlq.arn,
          aws_sqs_queue.worker_cron_dlq.arn,
        ]
      },
    ]
  })
}

# FEAT-automation-admin 3c: the owner's run-now. The ONE mutating AWS action the
# backend role holds for automation: lambda:InvokeFunction on blogWorkerLambda's
# unqualified ARN only (no `:*`, so no version or alias), which is also the only
# function the backend ever names (RUN_FUNCTION_NAME). The backend sends
# InvocationType=Event with a cron's own constant input; revoking this statement
# stops every run-now at once, even from a stale tab.
resource "aws_iam_role_policy" "backend_automation_run" {
  name = "automation-admin-run"
  role = aws_iam_role.backend.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "InvokeWorkerForRunNow"
        Effect   = "Allow"
        Action   = ["lambda:InvokeFunction"]
        Resource = aws_lambda_function.worker.arn
      },
    ]
  })
}

resource "aws_iam_role_policy" "worker_sqs_produce" {
  name = "sqs-produce-blogSQS"
  role = aws_iam_role.worker.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid      = "SqsProduce"
      Effect   = "Allow"
      Action   = ["sqs:GetQueueUrl", "sqs:SendMessage"]
      Resource = "arn:aws:sqs:ap-northeast-2:${var.account_id}:blogSQS"
    }]
  })
}

# OPS-delivery-safety-gates Step 4: Lambda delivers failed async cron invocations
# to worker-cron-dlq using the function's execution role → needs SendMessage on that
# DLQ (the on-failure destination in lambda.tf).
resource "aws_iam_role_policy" "worker_cron_dlq_send" {
  name = "sqs-send-worker-cron-dlq"
  role = aws_iam_role.worker.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid      = "SqsSendCronDlq"
      Effect   = "Allow"
      Action   = ["sqs:SendMessage"]
      Resource = aws_sqs_queue.worker_cron_dlq.arn
    }]
  })
}

# --- worker: blogWorkerLambda-role-7w21g7o3 ---
# 인라인 sqs 정책은 잘못된 계정(123456789012)을 가리켜 dead code.
# AWSLambdaBasicExecutionRole-* 커스텀 정책이 올바른 blogSQS ARN으로 SQS를 이미 허용.
resource "aws_iam_role" "worker" {
  name               = "blogWorkerLambda-role-7w21g7o3"
  path               = "/service-role/"
  assume_role_policy = local.lambda_assume_role
}

resource "aws_iam_role_policy_attachment" "worker_basic_exec" {
  role       = aws_iam_role.worker.name
  policy_arn = "arn:aws:iam::${var.account_id}:policy/service-role/AWSLambdaBasicExecutionRole-976d757e-0149-4c67-a106-158db3a5cd8f"
}
