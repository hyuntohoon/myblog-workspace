resource "aws_cognito_user_pool" "myblog_admin" {
  name                = "MyBlogAdminPool"
  mfa_configuration   = "OFF"
  deletion_protection = "ACTIVE"

  # email as login identifier — forces replacement if removed, do not change
  username_attributes      = ["email"]
  auto_verified_attributes = ["email"]

  # FEAT-multi-user-accounts 0c: self-signup ON so Google/Kakao federated users
  # auto-provision on first login (open platform; reviews gated by per-user caps
  # in Phase 1). In-place UpdateUserPool — NOT a pool replacement. Reversible.
  admin_create_user_config {
    allow_admin_create_user_only = false
  }

  password_policy {
    minimum_length                   = 8
    require_lowercase                = true
    require_numbers                  = true
    require_symbols                  = true
    require_uppercase                = true
    temporary_password_validity_days = 7
  }

  schema {
    name                     = "email"
    attribute_data_type      = "String"
    required                 = true
    mutable                  = true
    developer_only_attribute = false
    string_attribute_constraints {
      min_length = "0"
      max_length = "2048"
    }
  }

  account_recovery_setting {
    recovery_mechanism {
      name     = "verified_email"
      priority = 1
    }
    recovery_mechanism {
      name     = "verified_phone_number"
      priority = 2
    }
  }
}

resource "aws_cognito_user_pool_client" "admin_client" {
  name         = "MyBlogAdminClient"
  user_pool_id = aws_cognito_user_pool.myblog_admin.id

  # OAuth hosted UI는 spa_client 전용 — admin_client에 OAuth 필드 추가 금지.
  explicit_auth_flows = [
    "ALLOW_REFRESH_TOKEN_AUTH",
    "ALLOW_USER_AUTH",
    "ALLOW_USER_SRP_AUTH",
  ]

  access_token_validity  = 60
  id_token_validity      = 60
  refresh_token_validity = 5

  token_validity_units {
    access_token  = "minutes"
    id_token      = "minutes"
    refresh_token = "days"
  }
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

  access_token_validity  = 60
  id_token_validity      = 60
  refresh_token_validity = 5

  token_validity_units {
    access_token  = "minutes"
    id_token      = "minutes"
    refresh_token = "days"
  }

  callback_urls = [
    "http://localhost:4321/admin/callback",
    "https://www.ratemymusic.blog/admin/callback/",
  ]
  logout_urls = [
    "http://localhost:4321",
    "https://www.ratemymusic.blog",
  ]

  # 0c: members federate via Google/Kakao on the SAME client so their access
  # tokens carry client_id = spa_client.id and clear the API GW JWT authorizer
  # (audience-pinned to this client). Member login reuses the /admin/callback
  # route (generic code→token→home); a dedicated /auth route is a cosmetic
  # follow-on, not needed for the flow. COGNITO stays for the owner's SRP login.
  supported_identity_providers = [
    "COGNITO",
    aws_cognito_identity_provider.google.provider_name,
    aws_cognito_identity_provider.kakao.provider_name,
  ]
}
