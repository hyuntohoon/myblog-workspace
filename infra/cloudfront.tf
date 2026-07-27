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

# --- Security response headers (FIX-bug-audit-2026-07 WS-F) ---
# A custom aws_cloudfront_response_headers_policy is a Business-tier feature and
# was rejected at apply on this distribution's FREE pricing plan (same constraint
# that blocked custom cache policies — see the FEAT-music-edge-cache note below).
# Free-plan route: a viewer-response CloudFront Function stamping the headers.
# It runs on every response of the default (S3) behavior, so it was verified in
# isolation with `aws cloudfront test-function` before the association landed.
# CSP ships REPORT-ONLY; enforcing is a separate later step.
resource "aws_cloudfront_function" "security_headers" {
  name    = "myblog-security-headers"
  runtime = "cloudfront-js-2.0"
  comment = "WS-F security response headers (Free plan blocks response_headers_policy)"
  publish = true
  code    = file("${path.module}/functions/security_headers.js")
}

# --- FEAT-music-edge-cache Step 2 (Free-plan fallback, 2026-06-05) ---
# The original design used a CUSTOM aws_cloudfront_cache_policy keyed on query
# strings (so /search/unified?q=… and /artists/{id}/albums?offset=… could be
# edge-cached). At apply time AWS rejected it: this distribution is on the
# CloudFront **Free flat-rate pricing plan**, where custom cache policies are a
# Business-tier ($200/mo) feature — incompatible with the RFC's $0-cost premise
# (it rejected ElastiCache ~$91/mo and API GW cache $14.6/mo on the same basis).
#
# Reduced scope ($0, no plan change): edge-cache ONLY the pure-path
# `/api/music/albums/*` (album detail + by-spotify) using the AWS **managed**
# CachingOptimized policy (a "default caching rule", Free-allowed). Managed
# CachingOptimized strips query strings, so it is correct ONLY where the path is
# the full cache key. Excluded:
#   * `/api/music/search/unified?q=…` — query-string-keyed; managed cache would
#     collapse all queries to one entry. Stays on /api/* (CachingDisabled).
#     Already covered by browser (Step 1) + session (Step 3) + Lambda (Step 5).
#   * `/api/music/artists/*` — `/{id}/albums?limit/offset` and `/{id}/top-tracks?limit`
#     are query-string-paginated, and CloudFront path patterns can't isolate the
#     pure-path `/{id}` from them. Left uncached at the edge.
resource "aws_cloudfront_distribution" "myblog" {
  enabled         = true
  is_ipv6_enabled = true
  http_version    = "http2"
  price_class     = "PriceClass_All"
  aliases         = [var.domain_name]
  # OPS-safety-net-drift Step 2 (2026-07-28): this ACL is MANDATORY, not a
  # control. The owner chose to delete it (RuleCount 0 + default Allow = a
  # control in name only), but the apply was rejected by AWS: "Distributions
  # with a pricing plan subscription must have a web ACL resource" — this
  # distribution is on the CloudFront Free flat-rate pricing plan (see the
  # FEAT-music-edge-cache note above), and that plan force-attaches an ACL.
  # So the line below is a plan requirement; whether it carries real rules is
  # a separate owner decision (RFC OQ2 follow-up). Do not read its presence
  # as "we have a WAF".
  web_acl_id = "arn:aws:wafv2:us-east-1:${var.account_id}:global/webacl/CreatedByCloudFront-72420c9a/02494b05-2403-41eb-8e1f-21b161bee794"

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

    # WS-F: security response headers (see aws_cloudfront_function above).
    # Verified with `aws cloudfront test-function` before this association.
    function_association {
      event_type   = "viewer-response"
      function_arn = aws_cloudfront_function.security_headers.arn
    }
  }

  # --- FEAT-music-edge-cache Step 2: edge-cache album detail (Free-plan scope) ---
  # MUST precede the `/api/*` catch-all below (CloudFront matches the first
  # ordered behavior). `/api/music/albums/*` is pure-path (`/{id}`,
  # `/by-spotify/{id}`), so the managed CachingOptimized policy — which ignores
  # query strings — is correct here. CachingOptimized honors the origin's
  # Cache-Control (Step 1 sets `max-age=300` on album detail), so effective edge
  # TTL is 300s. cached_methods = GET/HEAD only → POST/etc. pass through uncached.
  # Origin request policy stays AllViewerExceptHostHeader so the `X-Origin-Verify`
  # origin header still reaches the Lambda. Absorb-pending by-spotify 404s stay
  # uncached via the distribution-level `custom_error_response` below.
  ordered_cache_behavior {
    path_pattern             = "/api/music/albums/*"
    target_origin_id         = local.apigw_origin_id
    viewer_protocol_policy   = "redirect-to-https"
    compress                 = true
    allowed_methods          = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    cached_methods           = ["GET", "HEAD"]
    cache_policy_id          = local.cache_policy_optimized
    origin_request_policy_id = local.origin_req_policy_all_viewer
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

  # Keep absorb-pending 404s (album by-spotify, now the only edge-cached music
  # path) out of the edge cache so the writer's poll-until-ready flow sees the
  # 404→200 flip immediately (distribution-wide, so harmless for other paths too).
  # Passes
  # the origin 404 through unchanged (no response_page_path); only caps caching.
  custom_error_response {
    error_code            = 404
    error_caching_min_ttl = 0
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
