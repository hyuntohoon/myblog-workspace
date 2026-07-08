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

# POST /api/categories: REMOVED (FIX-bug-audit-2026-07 WS-F). The backend has no
# categories router (STAB-5) and this route carried NO JWT authorizer — the only
# authorizer-less mutating route left on the API. Dead today (edge_guard 403s a
# direct call; FastAPI 404s), removed so it can't silently go live if a future
# /api/categories router is added.

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

# FEAT-multi-user Phase 3a: Last.fm connect/disconnect (member mutations). The
# GET /api/integrations[/lastfm/now-playing] reads ride the edge_guard GET catch-all.
resource "aws_apigatewayv2_route" "integrations_lastfm_put" {
  api_id             = aws_apigatewayv2_api.lambda_api.id
  route_key          = "PUT /api/integrations/lastfm"
  target             = "integrations/${aws_apigatewayv2_integration.backend.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

resource "aws_apigatewayv2_route" "integrations_lastfm_delete" {
  api_id             = aws_apigatewayv2_api.lambda_api.id
  route_key          = "DELETE /api/integrations/lastfm"
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

# --- Member self-profile (FEAT-multi-user-accounts Phase 0 / 0d) ---
# GET /api/me rides the edge_guard catch-all (api_get_proxy) — the Lambda's
# require_cognito_token validates the JWT and lazy-provisions the users row.
# The mutations are Cognito-JWT gated here (buckets_patch pattern).
resource "aws_apigatewayv2_route" "me_patch" {
  api_id             = aws_apigatewayv2_api.lambda_api.id
  route_key          = "PATCH /api/me"
  target             = "integrations/${aws_apigatewayv2_integration.backend.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

resource "aws_apigatewayv2_route" "me_delete" {
  api_id             = aws_apigatewayv2_api.lambda_api.id
  route_key          = "DELETE /api/me"
  target             = "integrations/${aws_apigatewayv2_integration.backend.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

# --- Album reviews (FEAT-multi-user-accounts Phase 1) ---
# The public reads — GET /api/reviews/albums/{id}, GET /api/members[/{handle}] —
# ride the edge_guard GET catch-all (api_get_proxy). Only the member/owner
# mutations are Cognito-JWT gated here (me_patch pattern). A member's review is
# lazy-provisioning at the Lambda; owner delete-any is require_owner in-app.
resource "aws_apigatewayv2_route" "reviews_album_put" {
  api_id             = aws_apigatewayv2_api.lambda_api.id
  route_key          = "PUT /api/reviews/albums/{album_id}"
  target             = "integrations/${aws_apigatewayv2_integration.backend.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

resource "aws_apigatewayv2_route" "reviews_album_delete" {
  api_id             = aws_apigatewayv2_api.lambda_api.id
  route_key          = "DELETE /api/reviews/albums/{album_id}"
  target             = "integrations/${aws_apigatewayv2_integration.backend.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

resource "aws_apigatewayv2_route" "reviews_owner_delete" {
  api_id             = aws_apigatewayv2_api.lambda_api.id
  route_key          = "DELETE /api/reviews/{review_id}"
  target             = "integrations/${aws_apigatewayv2_integration.backend.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

# --- Album research notes (FEAT-album-research-notes Step 4) ---
# Writer-facing AI research notes (never public). The manual trigger / restart /
# refine POST is Cognito-JWT here. GET /api/research/albums/{id} rides the
# edge_guard catch-all (api_get_proxy) like GET /api/buckets — no route here.
resource "aws_apigatewayv2_route" "research_albums_post" {
  api_id             = aws_apigatewayv2_api.lambda_api.id
  route_key          = "POST /api/research/albums/{album_id}"
  target             = "integrations/${aws_apigatewayv2_integration.backend.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

# --- Genres (FEAT-genre-system Step 4) ---
# Machine-labeled tier-0 taxonomy + owner-editable definitions. GET /api/genres/tree
# is public — it rides the edge_guard catch-all (api_get_proxy), no route here. The
# create/edit mutations are Cognito-JWT gated (buckets_post pattern, NOT the unauthed
# categories_post). POST is collection-root; PUT carries the {genre_id} path param.
resource "aws_apigatewayv2_route" "genres_post" {
  api_id             = aws_apigatewayv2_api.lambda_api.id
  route_key          = "POST /api/genres"
  target             = "integrations/${aws_apigatewayv2_integration.backend.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

resource "aws_apigatewayv2_route" "genres_put" {
  api_id             = aws_apigatewayv2_api.lambda_api.id
  route_key          = "PUT /api/genres/{genre_id}"
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

# --- 분석 버킷: 분류하기 (FEAT-genre-artist-distribution Step 5) ---
# The GET /api/library/saved-tracks* + /play-events/* distributions ride the catch-all
# api_get_proxy (edge_guard at the Lambda). Only this POST is Cognito-JWT gated; the
# handler just enqueues an SQS catalog-sync job (rule #9 — no sync Spotify call).
resource "aws_apigatewayv2_route" "library_saved_tracks_classify_post" {
  api_id             = aws_apigatewayv2_api.lambda_api.id
  route_key          = "POST /api/library/saved-tracks/classify"
  target             = "integrations/${aws_apigatewayv2_integration.backend.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

# 분석 버킷 장르 채우기 — on-demand genre-backfill trigger (FEAT-genre-autoheal).
# Cognito-JWT; the handler only inserts a genre_backfill_requests row (a local 5-min
# poller runs the existing backfill_genres.py — rule #9, no sync work in the request).
resource "aws_apigatewayv2_route" "library_saved_tracks_fill_genres_post" {
  api_id             = aws_apigatewayv2_api.lambda_api.id
  route_key          = "POST /api/library/saved-tracks/fill-genres"
  target             = "integrations/${aws_apigatewayv2_integration.backend.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

# --- Playback token (FEAT-pocket-buckit Step 3, D3 / OQ8) ---
# GET /api/playback/spotify-token async-mints a short-lived Spotify Web Playback SDK token.
# This is its OWN explicit Cognito-JWT route — deliberately NOT served by the
# `api_get_proxy` (GET /api/{proxy+}) edge_guard catch-all — so an edge-only request
# (CloudFront x-origin-verify, NO Bearer) is rejected at the authorizer (401) and can never
# mint a streaming token. API Gateway routes the more-specific literal path over {proxy+}.
# rule #9-safe: the handler only mints/refreshes a token, never a synchronous Spotify call.
resource "aws_apigatewayv2_route" "playback_spotify_token_get" {
  api_id             = aws_apigatewayv2_api.lambda_api.id
  route_key          = "GET /api/playback/spotify-token"
  target             = "integrations/${aws_apigatewayv2_integration.backend.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

# --- Lyrics read (FEAT-lyrics-viewer Step 1) ---
# GET /api/lyrics/{spotify_track_id} returns normalized lyric segments for one catalog
# track. Lyrics carry the corpus's "never in any shared response" privacy bar, so this is
# its OWN explicit Cognito-JWT route — deliberately NOT the GET /api/{proxy+} edge_guard
# catch-all (an edge-only request without a Bearer is rejected at the authorizer). HTTP API
# prefers the more-specific variable path over {proxy+}. rule #9-safe: a direct catalog DB
# read, never a synchronous Spotify call.
resource "aws_apigatewayv2_route" "lyrics_get" {
  api_id             = aws_apigatewayv2_api.lambda_api.id
  route_key          = "GET /api/lyrics/{spotify_track_id}"
  target             = "integrations/${aws_apigatewayv2_integration.backend.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

# --- Lyrics translation request (FEAT-lyrics-translation Step 2) ---
# POST /api/lyrics/{spotify_track_id}/translation-request upserts a 'requested' row the
# local launchd poller claims — no LLM call in the Lambda (rule #9 spirit). Translations
# are derivative works of track_lyrics and inherit the same owner-only privacy bar, so
# this is its OWN explicit Cognito-JWT route like lyrics_get. Until applied, the POST
# 404s at the edge (reference-apigateway-post-route-required).
resource "aws_apigatewayv2_route" "lyrics_translation_request_post" {
  api_id             = aws_apigatewayv2_api.lambda_api.id
  route_key          = "POST /api/lyrics/{spotify_track_id}/translation-request"
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

