resource "aws_cognito_user_pool" "myblog_admin" {
  name             = "MyBlogAdminPool"
  mfa_configuration = "OFF"

  auto_verified_attributes = ["email"]

  password_policy {
    minimum_length                   = 8
    require_lowercase                = true
    require_numbers                  = true
    require_symbols                  = true
    require_uppercase                = true
    temporary_password_validity_days = 7
  }

  account_recovery_setting {
    recovery_mechanism {
      name     = "verified_email"
      priority = 1
    }
  }
}

resource "aws_cognito_user_pool_client" "admin_client" {
  name         = "MyBlogAdminClient"
  user_pool_id = aws_cognito_user_pool.myblog_admin.id

  explicit_auth_flows = [
    "ALLOW_REFRESH_TOKEN_AUTH",
    "ALLOW_USER_AUTH",
    "ALLOW_USER_SRP_AUTH",
  ]

  allowed_oauth_flows                  = ["code"]
  allowed_oauth_scopes                 = ["email", "openid", "phone"]
  allowed_oauth_flows_user_pool_client = true

  callback_urls                = ["https://d84l1y8p4kdic.cloudfront.net"]
  supported_identity_providers = ["COGNITO"]
}

resource "aws_cognito_user_pool_client" "spa_client" {
  name         = "My SPA app - huvjal"
  user_pool_id = aws_cognito_user_pool.myblog_admin.id

  explicit_auth_flows = [
    "ALLOW_REFRESH_TOKEN_AUTH",
    "ALLOW_USER_AUTH",
    "ALLOW_USER_SRP_AUTH",
  ]

  allowed_oauth_flows                  = ["code"]
  allowed_oauth_scopes                 = ["email", "openid", "profile"]
  allowed_oauth_flows_user_pool_client = true

  callback_urls = [
    "http://localhost:4321/admin/callback",
    "https://www.ratemymusic.blog/admin/callback/",
  ]
  logout_urls = [
    "http://localhost:4321/admin",
    "https://www.ratemymusic.blog/admin/",
  ]

  supported_identity_providers = ["COGNITO"]
}
