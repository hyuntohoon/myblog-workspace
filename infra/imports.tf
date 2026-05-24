# Run `terraform init` then `terraform plan` to preview, then `terraform apply` to import.
# After first apply completes, these import blocks become no-ops and can be removed.

import {
  to = aws_sqs_queue.album_sync_dlq
  id = "https://sqs.ap-northeast-2.amazonaws.com/338183196042/album-sync-dlq"
}

import {
  to = aws_sqs_queue.blog_sqs
  id = "https://sqs.ap-northeast-2.amazonaws.com/338183196042/blogSQS"
}

import {
  to = aws_cognito_user_pool.myblog_admin
  id = "ap-northeast-2_54vEJKEU5"
}

import {
  to = aws_cognito_user_pool_client.admin_client
  id = "ap-northeast-2_54vEJKEU5/2tpkov6549a13544s9domcsnoe"
}

import {
  to = aws_cognito_user_pool_client.spa_client
  id = "ap-northeast-2_54vEJKEU5/68ccmcanfbvla9qbovnb9b18bt"
}

import {
  to = aws_s3_bucket.myblog_prod_web
  id = "myblog-prod-web"
}

import {
  to = aws_s3_bucket_website_configuration.myblog_prod_web
  id = "myblog-prod-web"
}

import {
  to = aws_s3_bucket_public_access_block.myblog_prod_web
  id = "myblog-prod-web"
}

import {
  to = aws_cloudfront_distribution.myblog
  id = "E2Q2JH5EAYVU1O"
}
