output "cognito_user_pool_id" {
  value = aws_cognito_user_pool.myblog_admin.id
}

output "cognito_user_pool_arn" {
  value = aws_cognito_user_pool.myblog_admin.arn
}

output "blog_sqs_url" {
  value = aws_sqs_queue.blog_sqs.url
}

output "blog_sqs_arn" {
  value = aws_sqs_queue.blog_sqs.arn
}

output "album_sync_dlq_arn" {
  value = aws_sqs_queue.album_sync_dlq.arn
}

output "cloudfront_domain" {
  value = aws_cloudfront_distribution.myblog.domain_name
}

output "cloudfront_distribution_id" {
  value = aws_cloudfront_distribution.myblog.id
}

output "s3_website_endpoint" {
  value = aws_s3_bucket_website_configuration.myblog_prod_web.website_endpoint
}
