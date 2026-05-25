variable "aws_region" {
  type    = string
  default = "ap-northeast-2"
}

variable "account_id" {
  type    = string
  default = "338183196042"
}

variable "domain_name" {
  type    = string
  default = "www.ratemymusic.blog"
}

variable "edge_secret" {
  type        = string
  description = "X-Origin-Verify header value shared between CloudFront and Lambda"
  sensitive   = true
}

variable "alert_email" {
  type        = string
  description = "Email address to receive CloudWatch alarm notifications"
  default     = "zlxlgus123@gmail.com"
}
