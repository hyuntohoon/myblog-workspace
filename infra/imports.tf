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

# ── IAC-1: Lambda + API Gateway + log groups ────────────────────────────────

# Lambda functions
import {
  to = aws_lambda_function.backend
  id = "ratemymusic-api"
}
import {
  to = aws_lambda_function.music
  id = "musicApi"
}
import {
  to = aws_lambda_function.worker
  id = "blogWorkerLambda"
}

# SQS event source mapping (blogSQS -> worker)
import {
  to = aws_lambda_event_source_mapping.worker_sqs
  id = "811e2036-efde-404f-aee2-78de6da178b2"
}

# API Gateway HTTP API
import {
  to = aws_apigatewayv2_api.lambda_api
  id = "ld8pjw3mx4"
}
import {
  to = aws_apigatewayv2_stage.default
  id = "ld8pjw3mx4/$default"
}
import {
  to = aws_apigatewayv2_authorizer.cognito
  id = "ld8pjw3mx4/6eia7l"
}

# Integrations
import {
  to = aws_apigatewayv2_integration.backend
  id = "ld8pjw3mx4/0woghr4"
}
import {
  to = aws_apigatewayv2_integration.music
  id = "ld8pjw3mx4/judcqxt"
}

# Routes
import {
  to = aws_apigatewayv2_route.music_proxy
  id = "ld8pjw3mx4/5s66rz7"
}
import {
  to = aws_apigatewayv2_route.music_root
  id = "ld8pjw3mx4/mh2gfao"
}
import {
  to = aws_apigatewayv2_route.api_get_proxy
  id = "ld8pjw3mx4/l40j69f"
}
import {
  to = aws_apigatewayv2_route.categories_post
  id = "ld8pjw3mx4/ibw7jrt"
}
import {
  to = aws_apigatewayv2_route.posts_post
  id = "ld8pjw3mx4/w0t3k4r"
}

# CloudWatch log groups
import {
  to = aws_cloudwatch_log_group.lambda["backend"]
  id = "/aws/lambda/ratemymusic-api"
}
import {
  to = aws_cloudwatch_log_group.lambda["music"]
  id = "/aws/lambda/musicApi"
}
import {
  to = aws_cloudwatch_log_group.lambda["worker"]
  id = "/aws/lambda/blogWorkerLambda"
}
