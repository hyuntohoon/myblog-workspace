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

resource "aws_iam_role_policy" "backend_ssm" {
  name = "ssm"
  role = aws_iam_role.backend.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "GetDbParams"
        Effect   = "Allow"
        Action   = ["ssm:GetParameter", "ssm:GetParameters", "ssm:GetParameterHistory"]
        Resource = "arn:aws:ssm:ap-northeast-2:${var.account_id}:parameter/myblog/prod/db/*"
      },
      {
        Sid       = "KmsDecryptForSecureString"
        Effect    = "Allow"
        Action    = "kms:Decrypt"
        Resource  = "*"
        Condition = { StringEquals = { "kms:ViaService" = "ssm.ap-northeast-2.amazonaws.com" } }
      }
    ]
  })
}

# --- music: LambdaRDSControlRole ---
# 제거: AmazonRDSFullAccess (Neon DB 사용, AWS RDS 없음)
#        AmazonSQSFullAccess, AmazonSQSReadOnlyAccess (AWSLambdaSQSQueueExecutionRole으로 충분)
resource "aws_iam_role" "music" {
  name               = "LambdaRDSControlRole"
  path               = "/"
  assume_role_policy = local.lambda_assume_role
}

resource "aws_iam_role_policy_attachment" "music_sqs_exec" {
  role       = aws_iam_role.music.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaSQSQueueExecutionRole"
}

resource "aws_iam_role_policy" "music_rds_ctrl" {
  name = "rdscontorller"
  role = aws_iam_role.music.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["rds:StartDBInstance", "rds:StopDBInstance", "rds:DescribeDBInstances"]
        Resource = "arn:aws:rds:ap-northeast-2:${var.account_id}:db:blogdb"
      },
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
