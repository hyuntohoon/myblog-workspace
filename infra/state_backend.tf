# STAB-6 Step 5 (P3-1): remote Terraform state backend (S3-only).
#
# Replaces the local-only, unencrypted infra/terraform.tfstate (which held a
# plaintext Cognito client secret) with a versioned, encrypted, public-access-
# blocked S3 bucket. Migrated 2026-06-06 (be/ws apply + `init -migrate-state`).
#
# DynamoDB state-lock intentionally DROPPED (owner decision 2026-06-06): this is
# a single-author project with no infra auto-apply, so concurrent-apply lock
# value is low; and `claude_aws_manager` lacks `dynamodb:CreateTable`. The S3
# backend therefore runs without a lock (no `dynamodb_table` in main.tf). If
# multi-operator apply ever becomes real, either grant the DynamoDB perm + add a
# lock table, or upgrade Terraform to 1.10+ and set `use_lockfile = true`.

resource "aws_s3_bucket" "tfstate" {
  bucket = "myblog-terraform-state-${var.account_id}"

  # The state bucket must never be destroyed by an errant plan.
  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_s3_bucket_versioning" "tfstate" {
  bucket = aws_s3_bucket.tfstate.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "tfstate" {
  bucket = aws_s3_bucket.tfstate.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "tfstate" {
  bucket                  = aws_s3_bucket.tfstate.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
