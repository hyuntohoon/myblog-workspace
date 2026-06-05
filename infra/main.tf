terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # STAB-6 Step 5 (P3-1): remote state in S3 (migrated 2026-06-06). S3-only —
  # no DynamoDB lock (owner decision; single-author, no auto-apply). See
  # docs/rfcs/STAB-6-repo-hygiene-tfstate.md §Step 5 + state_backend.tf.
  backend "s3" {
    bucket  = "myblog-terraform-state-338183196042"
    key     = "infra/terraform.tfstate"
    region  = "ap-northeast-2"
    encrypt = true
  }
}

provider "aws" {
  region = var.aws_region
}

# ACM certificates for CloudFront must be in us-east-1
provider "aws" {
  alias  = "us_east_1"
  region = "us-east-1"
}
