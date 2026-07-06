resource "aws_s3_bucket" "myblog_prod_web" {
  bucket = "myblog-prod-web"
}

resource "aws_s3_bucket_website_configuration" "myblog_prod_web" {
  bucket = aws_s3_bucket.myblog_prod_web.id

  index_document {
    suffix = "index.html"
  }

  error_document {
    key = "error.html"
  }
}

resource "aws_s3_bucket_public_access_block" "myblog_prod_web" {
  bucket = aws_s3_bucket.myblog_prod_web.id

  block_public_acls       = false
  ignore_public_acls      = false
  block_public_policy     = false
  restrict_public_buckets = false
}

# FIX-bug-audit-2026-07 WS-F: this public-read policy existed only console-side —
# Terraform could neither detect nor restore it if deleted (silent drift). Bring
# it under management (imported, matches live). It keeps the S3 website endpoint
# public (required for the endpoint) AND grants the CloudFront service principal;
# the website endpoint bypassing the WAF/HTTPS/cache is a known trade-off tracked
# separately (OAC migration is a larger change).
resource "aws_s3_bucket_policy" "myblog_prod_web" {
  bucket = aws_s3_bucket.myblog_prod_web.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "PublicReadGetObject"
        Effect    = "Allow"
        Principal = "*"
        Action    = "s3:GetObject"
        Resource  = "arn:aws:s3:::myblog-prod-web/*"
      },
      {
        Sid       = "AllowCloudFrontServicePrincipal"
        Effect    = "Allow"
        Principal = { Service = "cloudfront.amazonaws.com" }
        Action    = "s3:GetObject"
        Resource  = "arn:aws:s3:::myblog-prod-web/*"
        Condition = {
          ArnLike = {
            "AWS:SourceArn" = "arn:aws:cloudfront::${var.account_id}:distribution/E2Q2JH5EAYVU1O"
          }
        }
      },
    ]
  })
}
