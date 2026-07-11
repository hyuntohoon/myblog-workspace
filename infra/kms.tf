# FEAT-multi-user-accounts 3b-a — customer-managed CMK for per-user integration
# token custody (Spotify refresh tokens et al.). user_integrations.payload holds
# the KMS-envelope ciphertext (V41 pre-provisioned the column; no schema change).
#
# Access model follows the repo idiom: default key policy (account root) +
# key-ARN-scoped IAM role policies below — no wildcards.
#   - backend (connect path):  Encrypt + GenerateDataKey (envelope encrypt on
#     PUT /api/integrations/spotify code exchange, 3b-c)
#   - worker  (poll/rotation): Decrypt + Encrypt + GenerateDataKey (decrypt →
#     refresh → re-encrypt rotated token, 3b-d)
# Lambda env wiring (key ARN/alias) lands in 3b-c/3b-d, not here.

resource "aws_kms_key" "user_tokens" {
  description             = "CMK for user-integration token envelopes (FEAT-multi-user-accounts 3b)"
  enable_key_rotation     = true
  deletion_window_in_days = 30
}

resource "aws_kms_alias" "user_tokens" {
  name          = "alias/myblog-user-tokens"
  target_key_id = aws_kms_key.user_tokens.key_id
}

resource "aws_iam_role_policy" "backend_kms_user_tokens" {
  name = "kms-user-tokens-encrypt"
  role = aws_iam_role.backend.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid      = "UserTokensEncrypt"
      Effect   = "Allow"
      Action   = ["kms:Encrypt", "kms:GenerateDataKey"]
      Resource = aws_kms_key.user_tokens.arn
    }]
  })
}

resource "aws_iam_role_policy" "worker_kms_user_tokens" {
  name = "kms-user-tokens-encrypt-decrypt"
  role = aws_iam_role.worker.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid      = "UserTokensEncryptDecrypt"
      Effect   = "Allow"
      Action   = ["kms:Decrypt", "kms:Encrypt", "kms:GenerateDataKey"]
      Resource = aws_kms_key.user_tokens.arn
    }]
  })
}
