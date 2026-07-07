# FEAT-multi-user-accounts Phase 0 sub-step 0c — social sign-in IdPs.
#
# Google (native) + Kakao (generic OIDC) federated into the EXISTING pool
# (option (a), pool kept — see the RFC's pool-immutability risk resolution).
# OAuth app credentials live in SSM SecureString (/myblog/oauth/*), provisioned
# out-of-band this session; read here via data sources (with_decryption default
# true) so `plan/apply` is self-contained (no TF_VAR export). claude_aws_manager
# holds ssm:GetParameter + kms:Decrypt on /myblog/* (claude-ssm-myblog).
#
# The Cognito hosted-UI domain is console-managed (NOT in Terraform) — do not add
# an aws_cognito_user_pool_domain here or it will fight the existing domain.
#
# email is a REQUIRED pool attribute (see cognito.tf schema) → every IdP MUST map
# it, else federated sign-in fails "attributes required: [email]". Kakao email is
# guaranteed present via 개인 개발자 비즈앱 + email 필수 동의 (수집 후 제공).

data "aws_ssm_parameter" "google_client_id" {
  name = "/myblog/oauth/google-client-id"
}

data "aws_ssm_parameter" "google_client_secret" {
  name = "/myblog/oauth/google-client-secret"
}

data "aws_ssm_parameter" "kakao_rest_api_key" {
  name = "/myblog/oauth/kakao-rest-api-key"
}

data "aws_ssm_parameter" "kakao_client_secret" {
  name = "/myblog/oauth/kakao-client-secret"
}

resource "aws_cognito_identity_provider" "google" {
  user_pool_id  = aws_cognito_user_pool.myblog_admin.id
  provider_name = "Google"
  provider_type = "Google"

  provider_details = {
    client_id        = data.aws_ssm_parameter.google_client_id.value
    client_secret    = data.aws_ssm_parameter.google_client_secret.value
    authorize_scopes = "openid email profile"
  }

  attribute_mapping = {
    email          = "email"
    email_verified = "email_verified"
    name           = "name"
    username       = "sub"
  }
}

resource "aws_cognito_identity_provider" "kakao" {
  user_pool_id  = aws_cognito_user_pool.myblog_admin.id
  provider_name = "Kakao"
  provider_type = "OIDC"

  # Endpoints given explicitly (not relying on discovery) for a deterministic
  # plan; oidc_issuer is kept so Cognito validates the id_token issuer + fetches
  # jwks. Kakao userinfo lives on kapi.kakao.com (GET), not kauth.
  provider_details = {
    client_id                 = data.aws_ssm_parameter.kakao_rest_api_key.value
    client_secret             = data.aws_ssm_parameter.kakao_client_secret.value
    authorize_scopes          = "openid account_email profile_nickname"
    oidc_issuer               = "https://kauth.kakao.com"
    attributes_request_method = "GET"
    authorize_url             = "https://kauth.kakao.com/oauth/authorize"
    token_url                 = "https://kauth.kakao.com/oauth/token"
    attributes_url            = "https://kapi.kakao.com/v1/oidc/userinfo"
    jwks_uri                  = "https://kauth.kakao.com/.well-known/jwks.json"
  }

  # email_verified intentionally UNMAPPED: Kakao OIDC userinfo does not document
  # an email_verified claim (RFC residual — verify with one live /v1/oidc/userinfo
  # call at 0c apply). Federated emails then land unverified, which is acceptable
  # — email-based auto-linking is explicitly excluded (decision 5). `name` maps to
  # Kakao's nickname claim; missing non-required claims do not block sign-in.
  attribute_mapping = {
    email    = "email"
    username = "sub"
    name     = "nickname"
  }
}
