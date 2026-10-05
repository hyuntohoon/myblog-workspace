# Private, owner-only Chat connection. Existing SPA clients/authorizers are unchanged.
# The callback-ID-specific URI comes from ChatGPT's connection management page;
# never guess it. Until configured, no OAuth client is created and tools fail closed.
variable "chatgpt_callback_urls" {
  type        = list(string)
  default     = []
  description = "Exact OAuth redirect URIs shown by the private ChatGPT MCP connection"
  validation {
    condition = alltrue([
      for url in var.chatgpt_callback_urls : can(regex("^https://chatgpt\\.com/connector/oauth/[A-Za-z0-9_-]+$", url))
    ])
    error_message = "Use the exact callback-ID-specific https://chatgpt.com/connector/oauth/... URI."
  }
}

resource "aws_cognito_resource_server" "chat_translation" {
  identifier   = "myblog-chat"
  name         = "MyBlog Chat translations"
  user_pool_id = aws_cognito_user_pool.myblog_admin.id
  scope {
    scope_name        = "translate"
    scope_description = "Prepare and save explicitly requested Korean translations"
  }
}

resource "aws_cognito_user_pool_client" "chat_translation" {
  count                                = length(var.chatgpt_callback_urls) > 0 ? 1 : 0
  name                                 = "MyBlog private Chat translation"
  user_pool_id                         = aws_cognito_user_pool.myblog_admin.id
  generate_secret                      = false
  allowed_oauth_flows_user_pool_client = true
  allowed_oauth_flows                  = ["code"]
  allowed_oauth_scopes                 = ["${aws_cognito_resource_server.chat_translation.identifier}/translate"]
  callback_urls                        = var.chatgpt_callback_urls
  supported_identity_providers         = ["COGNITO", aws_cognito_identity_provider.google.provider_name, aws_cognito_identity_provider.kakao.provider_name]
  explicit_auth_flows                  = ["ALLOW_REFRESH_TOKEN_AUTH"]
  access_token_validity                = 30
  refresh_token_validity               = 5
  token_validity_units {
    access_token  = "minutes"
    refresh_token = "days"
  }
}

# No Gateway authorizer on this transport: it must return the MCP OAuth challenge.
# Lambda validates signature, Cognito issuer, resource audience, dedicated client,
# scope and owner on EVERY request; the public metadata contains no private data.
resource "aws_apigatewayv2_route" "chat_mcp" {
  api_id    = aws_apigatewayv2_api.lambda_api.id
  route_key = "ANY /mcp"
  target    = "integrations/${aws_apigatewayv2_integration.backend.id}"
}

resource "aws_apigatewayv2_route" "chat_mcp_resource_metadata" {
  api_id    = aws_apigatewayv2_api.lambda_api.id
  route_key = "GET /.well-known/oauth-protected-resource/mcp"
  target    = "integrations/${aws_apigatewayv2_integration.backend.id}"
}

resource "aws_apigatewayv2_route" "chat_mcp_oauth_metadata" {
  api_id    = aws_apigatewayv2_api.lambda_api.id
  route_key = "GET /.well-known/oauth-authorization-server/mcp-auth"
  target    = "integrations/${aws_apigatewayv2_integration.backend.id}"
}

output "chat_mcp_url" {
  value = "${aws_apigatewayv2_api.lambda_api.api_endpoint}/mcp"
}

output "chat_mcp_client_id" {
  value = try(aws_cognito_user_pool_client.chat_translation[0].id, "")
}
