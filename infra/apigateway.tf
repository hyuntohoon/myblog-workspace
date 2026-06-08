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

  # STAB-2 Step 5 (AUTH-7 / P6-6): a throttle floor on the raw invoke domain.
  # WAFv2 cannot attach to an HTTP API, so this stage-level rate/burst cap is the
  # near-term bound against abuse of the unauthenticated, CloudFront-less invoke
  # endpoint. Generous for a single-author blog's legit traffic; protects against
  # scripted floods. Tune via the vars; off = remove this block.
  default_route_settings {
    throttling_rate_limit  = var.apigw_throttle_rate
    throttling_burst_limit = var.apigw_throttle_burst
  }
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

resource "aws_apigatewayv2_route" "metrics_batch_post" {
  api_id    = aws_apigatewayv2_api.lambda_api.id
  route_key = "POST /api/metrics/batch"
  target    = "integrations/${aws_apigatewayv2_integration.backend.id}"
}

resource "aws_apigatewayv2_route" "posts_post" {
  api_id             = aws_apigatewayv2_api.lambda_api.id
  route_key          = "POST /api/posts"
  target             = "integrations/${aws_apigatewayv2_integration.backend.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

resource "aws_apigatewayv2_route" "posts_put" {
  api_id             = aws_apigatewayv2_api.lambda_api.id
  route_key          = "PUT /api/posts/{id}"
  target             = "integrations/${aws_apigatewayv2_integration.backend.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

resource "aws_apigatewayv2_route" "posts_delete" {
  api_id             = aws_apigatewayv2_api.lambda_api.id
  route_key          = "DELETE /api/posts/{id}"
  target             = "integrations/${aws_apigatewayv2_integration.backend.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

resource "aws_apigatewayv2_route" "posts_restore_patch" {
  api_id             = aws_apigatewayv2_api.lambda_api.id
  route_key          = "PATCH /api/posts/{id}/restore"
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

# --- Review buckets (FEAT-review-bucket-board) ---
# GET /api/buckets is served by the catch-all `api_get_proxy` route above
# (edge_guard at the Lambda). Every mutation is Cognito-JWT gated here.

resource "aws_apigatewayv2_route" "buckets_post" {
  api_id             = aws_apigatewayv2_api.lambda_api.id
  route_key          = "POST /api/buckets"
  target             = "integrations/${aws_apigatewayv2_integration.backend.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

resource "aws_apigatewayv2_route" "buckets_patch" {
  api_id             = aws_apigatewayv2_api.lambda_api.id
  route_key          = "PATCH /api/buckets/{id}"
  target             = "integrations/${aws_apigatewayv2_integration.backend.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

# FEAT-spotify-library-sync: manual "동기화" enqueues an async Spotify-Library sync
# job; the worker does the Spotify reads/diffs/writes (rule #9 — never sync here).
# The GET /api/buckets/spotify-library/state read rides the edge_guard catch-all
# (api_get_proxy) — no route here. Declared before the {id} routes is unnecessary
# for API Gateway (it matches the more-specific literal path), but kept grouped.
resource "aws_apigatewayv2_route" "buckets_spotify_library_sync_post" {
  api_id             = aws_apigatewayv2_api.lambda_api.id
  route_key          = "POST /api/buckets/spotify-library/sync"
  target             = "integrations/${aws_apigatewayv2_integration.backend.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

resource "aws_apigatewayv2_route" "buckets_delete" {
  api_id             = aws_apigatewayv2_api.lambda_api.id
  route_key          = "DELETE /api/buckets/{id}"
  target             = "integrations/${aws_apigatewayv2_integration.backend.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

resource "aws_apigatewayv2_route" "buckets_reorder_put" {
  api_id             = aws_apigatewayv2_api.lambda_api.id
  route_key          = "PUT /api/buckets/reorder"
  target             = "integrations/${aws_apigatewayv2_integration.backend.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

# Nested-board indent/outdent/reorder (FEAT-member-dashboard Step 5). Sets a
# bucket's parent_id + sibling position; cycle prevention lives in the app layer.
resource "aws_apigatewayv2_route" "buckets_move_put" {
  api_id             = aws_apigatewayv2_api.lambda_api.id
  route_key          = "PUT /api/buckets/{id}/move"
  target             = "integrations/${aws_apigatewayv2_integration.backend.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

resource "aws_apigatewayv2_route" "buckets_items_post" {
  api_id             = aws_apigatewayv2_api.lambda_api.id
  route_key          = "POST /api/buckets/{id}/items"
  target             = "integrations/${aws_apigatewayv2_integration.backend.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

resource "aws_apigatewayv2_route" "buckets_items_patch" {
  api_id             = aws_apigatewayv2_api.lambda_api.id
  route_key          = "PATCH /api/buckets/{id}/items/{item_id}"
  target             = "integrations/${aws_apigatewayv2_integration.backend.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

resource "aws_apigatewayv2_route" "buckets_items_delete" {
  api_id             = aws_apigatewayv2_api.lambda_api.id
  route_key          = "DELETE /api/buckets/{id}/items/{item_id}"
  target             = "integrations/${aws_apigatewayv2_integration.backend.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

# --- Member library: to-listen queue (FEAT-member-dashboard Step 2, D18) ---
# GET /api/library/to-listen and GET /api/library/reviewed are served by the
# catch-all `api_get_proxy` route above (edge_guard at the Lambda). The to-listen
# mutations are Cognito-JWT gated here. (/reorder is its own literal route.)

resource "aws_apigatewayv2_route" "library_to_listen_post" {
  api_id             = aws_apigatewayv2_api.lambda_api.id
  route_key          = "POST /api/library/to-listen"
  target             = "integrations/${aws_apigatewayv2_integration.backend.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

resource "aws_apigatewayv2_route" "library_to_listen_reorder_put" {
  api_id             = aws_apigatewayv2_api.lambda_api.id
  route_key          = "PUT /api/library/to-listen/reorder"
  target             = "integrations/${aws_apigatewayv2_integration.backend.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

resource "aws_apigatewayv2_route" "library_to_listen_delete" {
  api_id             = aws_apigatewayv2_api.lambda_api.id
  route_key          = "DELETE /api/library/to-listen/{item_id}"
  target             = "integrations/${aws_apigatewayv2_integration.backend.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

# --- Member listening: manual "지금 새로고침" (FEAT-member-dashboard Step 3, D5) ---
# GET /api/library/recently-listened, /now-playing, /spotify-connection are served
# by the catch-all `api_get_proxy` (edge_guard). Only this POST trigger is Cognito-
# JWT gated. The handler just enqueues an SQS job (rule #9 — no sync Spotify call).
resource "aws_apigatewayv2_route" "library_refresh_recent_post" {
  api_id             = aws_apigatewayv2_api.lambda_api.id
  route_key          = "POST /api/library/refresh-recent"
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

