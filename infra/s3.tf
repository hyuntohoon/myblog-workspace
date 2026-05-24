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
