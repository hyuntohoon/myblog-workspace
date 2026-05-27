data "aws_secretsmanager_secret" "backend" {
  name = "myblog/backend"
}

data "aws_secretsmanager_secret" "worker" {
  name = "myblog/worker"
}

data "aws_secretsmanager_secret" "music" {
  name = "myblog/music"
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

