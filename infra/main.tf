terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # STAB-6 Step 5 (P3-1): remote state. Resources live in state_backend.tf.
  # UNCOMMENT only AFTER the first `terraform apply` creates the bucket + lock
  # table, then run `terraform init -migrate-state` (human). Keep the literals in
  # sync with state_backend.tf if the OQ3 names change.
  # See docs/rfcs/STAB-6-repo-hygiene-tfstate.md §Step 5.
  # backend "s3" {
  #   bucket         = "myblog-terraform-state-338183196042"
  #   key            = "infra/terraform.tfstate"
  #   region         = "ap-northeast-2"
  #   dynamodb_table = "myblog-terraform-locks"
  #   encrypt        = true
  # }
}

provider "aws" {
  region = var.aws_region
}

# ACM certificates for CloudFront must be in us-east-1
provider "aws" {
  alias  = "us_east_1"
  region = "us-east-1"
}
