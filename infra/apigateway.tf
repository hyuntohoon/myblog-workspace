# HTTP API `lambdaAPI` — single API Gateway fronting backend, music, publish.
# CloudFront's /api/* behavior targets this API's invoke domain.

resource "aws_apigatewayv2_api" "lambda_api" {
  name                       = "lambdaAPI"
  protocol_type              = "HTTP"
  route_selection_expression = "$request.method $request.path"

  cors_configuration {
    allow_credentials = false
    allow_headers     = ["content-type,authorization"]
    allow_methods     = ["*"]
    allow_origins     = ["https://www.ratemymusic.blog", "https://ratemymusic.blog"]
    max_age           = 0
  }
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.lambda_api.id
  name        = "$default"
  auto_deploy = true
}

# --- Cognito JWT authorizer (used by POST /api/posts, POST /api/publish) ---
resource "aws_apigatewayv2_authorizer" "cognito" {
  api_id           = aws_apigatewayv2_api.lambda_api.id
  name             = "CognitoAuth"
  authorizer_type  = "JWT"
  identity_sources = ["$request.header.Authorization"]

  jwt_configuration {
    audience = [aws_cognito_user_pool_client.spa_client.id]
    issuer   = "https://cognito-idp.${var.aws_region}.amazonaws.com/${aws_cognito_user_pool.myblog_admin.id}"
  }
}

# --- Integrations (AWS_PROXY → Lambda) ---
resource "aws_apigatewayv2_integration" "backend" {
  api_id                 = aws_apigatewayv2_api.lambda_api.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.backend.arn
  integration_method     = "POST"
  payload_format_version = "2.0"
  timeout_milliseconds   = 30000
}

resource "aws_apigatewayv2_integration" "music" {
  api_id                 = aws_apigatewayv2_api.lambda_api.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.music.arn
  integration_method     = "POST"
  payload_format_version = "2.0"
  timeout_milliseconds   = 30000
}


# --- Routes ---
resource "aws_apigatewayv2_route" "music_proxy" {
  api_id    = aws_apigatewayv2_api.lambda_api.id
  route_key = "ANY /api/music/{proxy+}"
  target    = "integrations/${aws_apigatewayv2_integration.music.id}"
}

resource "aws_apigatewayv2_route" "music_root" {
  api_id    = aws_apigatewayv2_api.lambda_api.id
  route_key = "ANY /api/music"
  target    = "integrations/${aws_apigatewayv2_integration.music.id}"
}

resource "aws_apigatewayv2_route" "api_get_proxy" {
  api_id    = aws_apigatewayv2_api.lambda_api.id
  route_key = "GET /api/{proxy+}"
  target    = "integrations/${aws_apigatewayv2_integration.backend.id}"
}

resource "aws_apigatewayv2_route" "categories_post" {
  api_id    = aws_apigatewayv2_api.lambda_api.id
  route_key = "POST /api/categories"
  target    = "integrations/${aws_apigatewayv2_integration.backend.id}"
}

resource "aws_apigatewayv2_route" "posts_post" {
  api_id             = aws_apigatewayv2_api.lambda_api.id
  route_key          = "POST /api/posts"
  target             = "integrations/${aws_apigatewayv2_integration.backend.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

resource "aws_apigatewayv2_route" "publish_backend" {
  api_id             = aws_apigatewayv2_api.lambda_api.id
  route_key          = "POST /api/publish"
  target             = "integrations/${aws_apigatewayv2_integration.backend.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

# --- Invoke permissions ---
# One broad permission per function (covers all routes via wildcard).
# Legacy per-route permissions created by the console remain but are redundant;
# they can be removed manually after this is verified.
resource "aws_lambda_permission" "apigw_backend" {
  statement_id  = "AllowInvokeFromHttpApi"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.backend.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.lambda_api.execution_arn}/*/*"
}

resource "aws_lambda_permission" "apigw_music" {
  statement_id  = "AllowInvokeFromHttpApi"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.music.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.lambda_api.execution_arn}/*/*"
}

