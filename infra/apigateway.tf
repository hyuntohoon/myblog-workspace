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

# FEAT-multi-user 3b-c: member Spotify connect/disconnect (server-side code
# exchange + KMS token custody). Same JWT shape as the lastfm pair above.
resource "aws_apigatewayv2_route" "integrations_spotify_put" {
  api_id             = aws_apigatewayv2_api.lambda_api.id
  route_key          = "PUT /api/integrations/spotify"
  target             = "integrations/${aws_apigatewayv2_integration.backend.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

resource "aws_apigatewayv2_route" "integrations_spotify_delete" {
  api_id             = aws_apigatewayv2_api.lambda_api.id
  route_key          = "DELETE /api/integrations/spotify"
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
# Same for the two authed reads under it, deliberately routeless:
# GET /api/me/album-states (FEAT-album-review-authoring Step 1) and
# GET /api/me/review-candidates (Step 2) — both private, both JWT-in-Lambda.
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

# --- Tracked artists (FEAT-personal-release-tracking Step 2) ---
# GET /api/me/tracked-artists and GET /api/me/release-feed ride the edge_guard
# GET catch-all (api_get_proxy) — JWT validated in-Lambda via
# provisioned_member_id. Only the mutations are Cognito-JWT gated here
# (me_patch pattern).
resource "aws_apigatewayv2_route" "tracked_artists_preview_post" {
  api_id             = aws_apigatewayv2_api.lambda_api.id
  route_key          = "POST /api/me/tracked-artists/preview"
  target             = "integrations/${aws_apigatewayv2_integration.backend.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

resource "aws_apigatewayv2_route" "tracked_artists_post" {
  api_id             = aws_apigatewayv2_api.lambda_api.id
  route_key          = "POST /api/me/tracked-artists"
  target             = "integrations/${aws_apigatewayv2_integration.backend.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

resource "aws_apigatewayv2_route" "tracked_artists_delete" {
  api_id             = aws_apigatewayv2_api.lambda_api.id
  route_key          = "DELETE /api/me/tracked-artists/{artist_id}"
  target             = "integrations/${aws_apigatewayv2_integration.backend.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

# Owner-gated in-Lambda via provisioned_owner_id (FEAT-for-you-releases Step 2:
# the async Spotify followed-artists import trigger — enqueue only, rule #9).
resource "aws_apigatewayv2_route" "tracked_artists_spotify_import_post" {
  api_id             = aws_apigatewayv2_api.lambda_api.id
  route_key          = "POST /api/me/tracked-artists/spotify-import"
  target             = "integrations/${aws_apigatewayv2_integration.backend.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

# --- Reratings (FEAT-album-rerating) ---
# 재평가: withdraw a finished 평가 so the album can be re-listened and rated
# again. PUT starts one (409 when there is no 평가 to withdraw), DELETE cancels
# and restores the withdrawn score. GET /api/me/reratings rides the edge_guard
# GET catch-all — only these two mutations need a JWT route here.
resource "aws_apigatewayv2_route" "reratings_put" {
  api_id             = aws_apigatewayv2_api.lambda_api.id
  route_key          = "PUT /api/me/reratings/{album_id}"
  target             = "integrations/${aws_apigatewayv2_integration.backend.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

resource "aws_apigatewayv2_route" "reratings_delete" {
  api_id             = aws_apigatewayv2_api.lambda_api.id
  route_key          = "DELETE /api/me/reratings/{album_id}"
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

# Owner-only mark/unmark of albums.best_new from the rating surface, without
# opening the post editor (require_owner in-app; the JWT authorizer here only
# proves a valid Cognito token).
resource "aws_apigatewayv2_route" "reviews_album_best_new_put" {
  api_id             = aws_apigatewayv2_api.lambda_api.id
  route_key          = "PUT /api/reviews/albums/{album_id}/best-new"
  target             = "integrations/${aws_apigatewayv2_integration.backend.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

# --- Planned ratings / 평가 예정 (FEAT-rating-smart-collections Step 2, Option B) ---
# GET /api/me/planned-ratings rides the edge_guard GET catch-all like every other
# authed GET in app/api/routes/me.py — no route needed here. Only the two
# mutations (mark/unmark) need a Cognito-JWT route, same shape as reviews_album_*.
resource "aws_apigatewayv2_route" "planned_ratings_put" {
  api_id             = aws_apigatewayv2_api.lambda_api.id
  route_key          = "PUT /api/me/planned-ratings/{album_id}"
  target             = "integrations/${aws_apigatewayv2_integration.backend.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

resource "aws_apigatewayv2_route" "planned_ratings_delete" {
  api_id             = aws_apigatewayv2_api.lambda_api.id
  route_key          = "DELETE /api/me/planned-ratings/{album_id}"
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

# --- Today's song pick (FEAT-today-buckit Step 5) ---
# Owner-curated "song of the day" store. The two public reads —
# GET /api/todays-pick and GET /api/todays-pick/history — ride the edge_guard
# GET catch-all (api_get_proxy) like GET /api/buckets, no route here. Only the
# owner mutations are Cognito-JWT gated (integrations_lastfm_put/delete pattern:
# literal path, no {id}). The Lambda's require_owner enforces single-owner.
resource "aws_apigatewayv2_route" "todays_pick_put" {
  api_id             = aws_apigatewayv2_api.lambda_api.id
  route_key          = "PUT /api/todays-pick"
  target             = "integrations/${aws_apigatewayv2_integration.backend.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

resource "aws_apigatewayv2_route" "todays_pick_delete" {
  api_id             = aws_apigatewayv2_api.lambda_api.id
  route_key          = "DELETE /api/todays-pick"
  target             = "integrations/${aws_apigatewayv2_integration.backend.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

# FEAT-todays-pick-queue Step 3: private owner staging queue for 오늘의 곡.
# GET /api/todays-pick/queue deliberately has NO route here — it rides the
# edge_guard GET catch-all (api_get_proxy) and stays owner-gated in-Lambda
# (require_owner verifies the JWT itself; no token → 403 "Forbidden" — FastAPI
# HTTPBearer's missing-credential response — and non-owner → 403. Observed on
# the raw API GW host post-Step-4; via CloudFront no-token is 401. Fail-closed
# either way; only the mutation routes below 401 at the API GW authorizer).
resource "aws_apigatewayv2_route" "todays_pick_queue_post" {
  api_id             = aws_apigatewayv2_api.lambda_api.id
  route_key          = "POST /api/todays-pick/queue"
  target             = "integrations/${aws_apigatewayv2_integration.backend.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

resource "aws_apigatewayv2_route" "todays_pick_queue_delete" {
  api_id             = aws_apigatewayv2_api.lambda_api.id
  route_key          = "DELETE /api/todays-pick/queue/{id}"
  target             = "integrations/${aws_apigatewayv2_integration.backend.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

resource "aws_apigatewayv2_route" "todays_pick_queue_promote_post" {
  api_id             = aws_apigatewayv2_api.lambda_api.id
  route_key          = "POST /api/todays-pick/queue/{id}/promote"
  target             = "integrations/${aws_apigatewayv2_integration.backend.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

# FEAT-spotify-library-sync: manual "동기화" enqueues an async Spotify-Library sync
# job; the worker does the Spotify reads/diffs/writes (rule #9 — never sync here).
# Declared before the {id} routes is unnecessary for API Gateway (it matches the
# more-specific literal path), but kept grouped.
#
# BUG-25 (2026-08-09): GET /api/buckets/spotify-library/state used to ride the
# edge_guard catch-all (api_get_proxy) with NO route here — meaning no Cognito
# authorizer, so the backend route's own missing auth dependency was the only
# thing standing between anonymous internet traffic and the owner's synced
# Spotify library state. Both bugs are fixed together: the backend route now
# requires provisioned_owner_id, and this dedicated route gives it the same
# JWT authorizer as the sibling POST below.
resource "aws_apigatewayv2_route" "buckets_spotify_library_state_get" {
  api_id             = aws_apigatewayv2_api.lambda_api.id
  route_key          = "GET /api/buckets/spotify-library/state"
  target             = "integrations/${aws_apigatewayv2_integration.backend.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

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

# FIX-nightly-draft-identity: grow-once for the 03:00 draft agent. The item
# PATCH above is member-scoped (the agent owns no buckets → 404 by design), so
# after creating a draft the nightly job calls this narrow route instead; the
# backend pins the acting user to OWNER_SUB server-side and only stamps the
# owner's checked memos for the named album (backend fix/nightly-draft-grow).
resource "aws_apigatewayv2_route" "buckets_nightly_grow_post" {
  api_id             = aws_apigatewayv2_api.lambda_api.id
  route_key          = "POST /api/buckets/nightly-grow"
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
# GET /api/library/recently-listened, /recent-tracks, /listened-albums, /now-playing
# and /spotify-connection are served by the catch-all `api_get_proxy`. No route
# resource is needed for any of them.
#
# SEC-member-listening-data-boundary Step 1 (2026-08-30) gave the first four
# `require_owner` IN THE LAMBDA — they read owner-global tables with no user column,
# so any signed-in member's dashboard was rendering the owner's listening history.
# That is deliberately NOT an authorizer here: the catch-all carries the edge_guard
# and the Lambda verifies the JWT itself, exactly as the member-scoped
# /api/library/stream-history/* reads and the owner-gated GET /api/posts already do.
# `/spotify-connection` is unchanged. The authoritative inventory of which endpoints
# are owner-gated is myblog_backend `tests/test_route_guard_map.py`, which fails if
# one of them loses its guard.
#
# Only this POST trigger is Cognito-JWT gated at the gateway. The handler just
# enqueues an SQS job (rule #9 — no sync Spotify call).
resource "aws_apigatewayv2_route" "library_refresh_recent_post" {
  api_id             = aws_apigatewayv2_api.lambda_api.id
  route_key          = "POST /api/library/refresh-recent"
  target             = "integrations/${aws_apigatewayv2_integration.backend.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

# --- 분석 버킷: 분류하기 (FEAT-genre-artist-distribution Step 5) ---
# The GET /api/library/saved-tracks* + /play-events/* distributions ride the catch-all
# api_get_proxy. Since SEC-member-listening-data-boundary Step 1 they are
# `require_owner` in the Lambda (owner-global tables, no per-member scope) — see the
# note on the 지금 새로고침 block above for why that needs no route resource here.
# Only this POST is Cognito-JWT gated at the gateway; the handler just enqueues an
# SQS catalog-sync job (rule #9 — no sync Spotify call).
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

