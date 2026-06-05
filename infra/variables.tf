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

# STAB-2 Step 5 — $default stage throttle floor (AUTH-7 / P6-6).
variable "apigw_throttle_rate" {
  type        = number
  description = "Steady-state request/sec floor on the HTTP API $default stage"
  default     = 50
}

variable "apigw_throttle_burst" {
  type        = number
  description = "Burst bucket size on the HTTP API $default stage"
  default     = 100
}
