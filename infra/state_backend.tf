# STAB-6 Step 5 (P3-1): remote Terraform state backend.
#
# Replaces the local-only, unencrypted infra/terraform.tfstate (which holds a
# plaintext Cognito client secret and has no lock) with a versioned, encrypted,
# public-access-blocked S3 bucket + a DynamoDB lock table.
#
# Two-phase rollout — full plan/apply, NO -target (rule #6), human-run
# (reference-workspace-no-infra-autoapply):
#   1. terraform apply                 # creates the bucket + lock table (state still local)
#   2. uncomment the backend "s3" block in main.tf
#   3. terraform init -migrate-state   # moves terraform.tfstate into S3 (human)
#   4. terraform plan                  # confirm clean; lock row acquired/released
# Rollback: `terraform init -migrate-state` back to local (keep the local file
# until the migration is confirmed).
#
# Naming = STAB-6 OQ3 defaults; owner may rename before step 1 (also update the
# commented backend block in main.tf to match). Replication intentionally off.

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

resource "aws_dynamodb_table" "tfstate_lock" {
  name         = "myblog-terraform-locks"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "LockID"

  attribute {
    name = "LockID"
    type = "S"
  }
}
