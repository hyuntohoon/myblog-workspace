locals {
  # Match actual origin IDs in the live distribution (avoid unnecessary redeploy)
  s3_origin_id    = "myblog-prod-web.s3.ap-northeast-2.amazonaws.com-mgq7g0szxl6"
  apigw_origin_id = "ld8pjw3mx4.execute-api.ap-northeast-2.amazonaws.com"
  apigw_domain    = "ld8pjw3mx4.execute-api.ap-northeast-2.amazonaws.com"
  acm_certificate = "arn:aws:acm:us-east-1:${var.account_id}:certificate/c585f3b7-f25e-48ef-8494-dc5e99fafb7c"

  # AWS Managed Cache Policy IDs
  cache_policy_optimized = "658327ea-f89d-4fab-a63d-7e88639e58f6" # CachingOptimized
  cache_policy_disabled  = "4135ea2d-6df8-44a3-9df3-4b5a84be39ad" # CachingDisabled

  # AWS Managed Origin Request Policy
  origin_req_policy_all_viewer = "b689b0a8-53d0-40ab-baf2-68738e2966ac" # AllViewerExceptHostHeader
}

resource "aws_cloudfront_distribution" "myblog" {
  enabled         = true
  is_ipv6_enabled = true
  http_version    = "http2"
  price_class     = "PriceClass_All"
  aliases         = [var.domain_name]
  web_acl_id      = "arn:aws:wafv2:us-east-1:${var.account_id}:global/webacl/CreatedByCloudFront-72420c9a/02494b05-2403-41eb-8e1f-21b161bee794"

  tags = {
    Name = "myblog-prod-distribution"
  }

  # --- Origin 1: S3 static website (Astro frontend) ---
  origin {
    origin_id   = local.s3_origin_id
    domain_name = "myblog-prod-web.s3-website.ap-northeast-2.amazonaws.com"

    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "http-only"
      origin_ssl_protocols   = ["SSLv3", "TLSv1", "TLSv1.1", "TLSv1.2"]
    }
  }

  # --- Origin 2: API Gateway (backend + music + publish) ---
  origin {
    origin_id   = local.apigw_origin_id
    domain_name = local.apigw_domain

    custom_header {
      name  = "X-Origin-Verify"
      value = var.edge_secret
    }

    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "https-only"
      origin_ssl_protocols   = ["TLSv1.2"]
    }
  }

  # --- Default cache behavior → S3 (CachingOptimized) ---
  default_cache_behavior {
    target_origin_id       = local.s3_origin_id
    viewer_protocol_policy = "redirect-to-https"
    compress               = true
    allowed_methods        = ["GET", "HEAD"]
    cached_methods         = ["GET", "HEAD"]
    cache_policy_id        = local.cache_policy_optimized

    # CloudFront Function for SPA routing (viewer-request)
    function_association {
      event_type   = "viewer-request"
      function_arn = "arn:aws:cloudfront::${var.account_id}:function/handler"
    }
  }

  # --- /api/* → API Gateway (CachingDisabled, all headers forwarded) ---
  ordered_cache_behavior {
    path_pattern             = "/api/*"
    target_origin_id         = local.apigw_origin_id
    viewer_protocol_policy   = "redirect-to-https"
    compress                 = true
    allowed_methods          = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    cached_methods           = ["GET", "HEAD"]
    cache_policy_id          = local.cache_policy_disabled
    origin_request_policy_id = local.origin_req_policy_all_viewer
  }

  viewer_certificate {
    acm_certificate_arn      = local.acm_certificate
    ssl_support_method       = "sni-only"
    minimum_protocol_version = "TLSv1.2_2021"
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  # TLSv1.3_2025 is set on the actual distribution but not yet in provider enum.
  # viewer_certificate drift is suppressed until provider support is added.
  lifecycle {
    ignore_changes = [viewer_certificate]
  }
}
