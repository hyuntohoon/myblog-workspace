locals {
  s3_origin_id      = "s3-myblog-prod-web"
  apigw_origin_id   = "apigw-lambdaAPI"
  apigw_domain      = "ld8pjw3mx4.execute-api.ap-northeast-2.amazonaws.com"
  acm_certificate   = "arn:aws:acm:us-east-1:${var.account_id}:certificate/c585f3b7-f25e-48ef-8494-dc5e99fafb7c"
}

resource "aws_cloudfront_distribution" "myblog" {
  enabled         = true
  is_ipv6_enabled = true
  http_version    = "http2"
  price_class     = "PriceClass_All"
  aliases         = [var.domain_name]

  # --- Origin 1: S3 static website (Astro frontend) ---
  origin {
    origin_id   = local.s3_origin_id
    domain_name = aws_s3_bucket_website_configuration.myblog_prod_web.website_endpoint

    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "http-only"
      origin_ssl_protocols   = ["TLSv1.2"]
    }
  }

  # --- Origin 2: API Gateway (backend + music + publish) ---
  origin {
    origin_id   = local.apigw_origin_id
    domain_name = local.apigw_domain

    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "https-only"
      origin_ssl_protocols   = ["TLSv1.2"]
    }
  }

  # --- Default cache behavior → S3 ---
  default_cache_behavior {
    target_origin_id       = local.s3_origin_id
    viewer_protocol_policy = "redirect-to-https"
    compress               = true
    allowed_methods        = ["GET", "HEAD"]
    cached_methods         = ["GET", "HEAD"]

    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }

    min_ttl     = 0
    default_ttl = 86400
    max_ttl     = 31536000
  }

  # --- /api/* → API Gateway (no caching, forward all) ---
  ordered_cache_behavior {
    path_pattern           = "/api/*"
    target_origin_id       = local.apigw_origin_id
    viewer_protocol_policy = "redirect-to-https"
    compress               = false
    allowed_methods        = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    cached_methods         = ["GET", "HEAD"]

    forwarded_values {
      query_string = true
      headers      = ["Authorization", "Origin", "x-origin-verify"]
      cookies {
        forward = "none"
      }
    }

    min_ttl     = 0
    default_ttl = 0
    max_ttl     = 0
  }

  viewer_certificate {
    acm_certificate_arn      = local.acm_certificate
    ssl_support_method       = "sni-only"
    minimum_protocol_version = "TLSv1.3_2025"
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }
}
