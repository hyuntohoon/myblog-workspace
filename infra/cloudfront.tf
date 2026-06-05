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

# --- FEAT-music-edge-cache Step 2: custom cache policy for public music reads ---
# Cache key = query strings only (q/type/limit/offset/...). No cookies, no
# Authorization header → public responses share one entry regardless of any
# bearer token (music reads ignore auth). Origin Cache-Control (set by the music
# Lambda in Step 1) drives the effective TTL, clamped to [min_ttl, max_ttl]:
# search max-age=60 → 60s; album/artist max-age=300 → 300s.
resource "aws_cloudfront_cache_policy" "music_read" {
  name        = "myblog-music-read-cache"
  comment     = "FEAT-music-edge-cache: public music read endpoints (search/album/artist)"
  default_ttl = 60
  min_ttl     = 0
  max_ttl     = 300

  parameters_in_cache_key_and_forwarded_to_origin {
    enable_accept_encoding_gzip   = true
    enable_accept_encoding_brotli = true

    query_strings_config {
      query_string_behavior = "all"
    }
    headers_config {
      header_behavior = "none"
    }
    cookies_config {
      cookie_behavior = "none"
    }
  }
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

  # --- FEAT-music-edge-cache Step 2: cache public music reads at the edge ---
  # These MUST precede the `/api/*` catch-all below (CloudFront uses the first
  # matching ordered behavior). cached_methods = GET/HEAD only, so any non-GET
  # passes through uncached. Origin request policy stays AllViewerExceptHostHeader
  # so the `X-Origin-Verify` origin header + query strings still reach the Lambda;
  # the cache *key* (from the cache policy) is query-strings-only.
  #
  # Scope notes (current-state audit, FEAT-music-edge-cache Decisions log):
  #   * search is `/unified` EXACT — NOT `/search/*` — so the auth-gated,
  #     SQS-enqueuing `/search/candidates` stays on the CachingDisabled `/api/*`.
  #   * `/albums/by-spotify/*` and `/artists/by-spotify/*` return 404 while the
  #     worker absorbs; those 404s are kept uncached by the distribution-level
  #     `custom_error_response` (error_caching_min_ttl = 0) so the writer poll works.
  ordered_cache_behavior {
    path_pattern             = "/api/music/albums/*"
    target_origin_id         = local.apigw_origin_id
    viewer_protocol_policy   = "redirect-to-https"
    compress                 = true
    allowed_methods          = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    cached_methods           = ["GET", "HEAD"]
    cache_policy_id          = aws_cloudfront_cache_policy.music_read.id
    origin_request_policy_id = local.origin_req_policy_all_viewer
  }

  ordered_cache_behavior {
    path_pattern             = "/api/music/artists/*"
    target_origin_id         = local.apigw_origin_id
    viewer_protocol_policy   = "redirect-to-https"
    compress                 = true
    allowed_methods          = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    cached_methods           = ["GET", "HEAD"]
    cache_policy_id          = aws_cloudfront_cache_policy.music_read.id
    origin_request_policy_id = local.origin_req_policy_all_viewer
  }

  ordered_cache_behavior {
    path_pattern             = "/api/music/search/unified"
    target_origin_id         = local.apigw_origin_id
    viewer_protocol_policy   = "redirect-to-https"
    compress                 = true
    allowed_methods          = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    cached_methods           = ["GET", "HEAD"]
    cache_policy_id          = aws_cloudfront_cache_policy.music_read.id
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

  # Keep absorb-pending 404s (album/artist by-spotify) out of the edge cache so
  # the writer's poll-until-ready flow sees the 404→200 flip immediately. Passes
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
