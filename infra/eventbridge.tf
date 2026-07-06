# MusicBrainz alias generation — scheduled invocation of the worker Lambda.
#
# The SQS path and this schedule share one Lambda. The handler tells them
# apart via event["source"] == "aws.events" (worker/handler.py), which the
# default EventBridge scheduled event always carries — so no target input
# is required.
#
# generate_and_save_aliases() looks up MusicBrainz for any artist with
# musicbrainz_id IS NULL, then writes either the MBID + aliases or a
# MBID_NOT_FOUND sentinel. There is no Gemini fallback (was planned, never
# implemented).
resource "aws_cloudwatch_event_rule" "musicbrainz_alias" {
  name                = "worker-musicbrainz-alias-generation"
  description         = "Backfill artists.musicbrainz_id + aliases via MusicBrainz lookup"
  schedule_expression = "rate(15 minutes)"
  state               = "ENABLED"
}

resource "aws_cloudwatch_event_target" "musicbrainz_alias" {
  rule      = aws_cloudwatch_event_rule.musicbrainz_alias.name
  target_id = "blogWorkerLambda"
  arn       = aws_lambda_function.worker.arn
}

resource "aws_lambda_permission" "musicbrainz_alias_events" {
  statement_id  = "AllowInvokeFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.worker.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.musicbrainz_alias.arn
}

# Spotify listening cache sync — scheduled invocation of the worker Lambda
# (FEAT-member-dashboard Step 3, D5).
#
# Shares the worker Lambda with the SQS path and the alias schedule. Unlike the
# alias rule, this target sends a CONSTANT input {"job":"spotify_listening"} which
# fully replaces the event payload (so it carries no "source":"aws.events"); the
# handler checks event["job"] first, before the alias source check
# (worker/handler.py). The worker reads /me/player/recently-played +
# currently-playing and upserts the spotify_recent_albums / spotify_now_playing
# cache. Never a synchronous Spotify call from a user-facing endpoint (rule #9).
resource "aws_cloudwatch_event_rule" "spotify_listening" {
  name                = "worker-spotify-listening-sync"
  description         = "Hourly Spotify recently-played + now-playing cache refresh"
  schedule_expression = "rate(1 hour)"
  state               = "ENABLED"
}

resource "aws_cloudwatch_event_target" "spotify_listening" {
  rule      = aws_cloudwatch_event_rule.spotify_listening.name
  target_id = "blogWorkerLambda-spotify-listening"
  arn       = aws_lambda_function.worker.arn
  input     = jsonencode({ job = "spotify_listening" })
}

resource "aws_lambda_permission" "spotify_listening_events" {
  statement_id  = "AllowInvokeFromEventBridgeSpotifyListening"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.worker.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.spotify_listening.arn
}

# Album-catalog ingest — daily scheduled invocation of the worker Lambda
# (FEAT-album-catalog-ingest Step 3).
#
# Constant input {"job":"album_ingest"} (same pattern as spotify_listening; the
# handler routes on event["job"] before the alias source check). The job sweeps
# gate-passing catalog artists for new full-length releases and enqueues novel
# IDs onto the existing blogSQS album-sync pipeline — discover+enqueue only, the
# upsert runs in the SQS consumer. Worker-role sqs:SendMessage and SQS_QUEUE_URL
# already exist (worker_sqs_produce / lambda.tf). Removing this rule stops all
# scheduled ingest immediately; the job code is inert without it.
resource "aws_cloudwatch_event_rule" "album_ingest" {
  name                = "worker-album-catalog-ingest"
  description         = "Daily new-release sweep of catalog artists into the album-sync pipeline"
  schedule_expression = "rate(1 day)"
  state               = "ENABLED"
}

resource "aws_cloudwatch_event_target" "album_ingest" {
  rule      = aws_cloudwatch_event_rule.album_ingest.name
  target_id = "blogWorkerLambda-album-ingest"
  arn       = aws_lambda_function.worker.arn
  input     = jsonencode({ job = "album_ingest" })
}

resource "aws_lambda_permission" "album_ingest_events" {
  statement_id  = "AllowInvokeFromEventBridgeAlbumIngest"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.worker.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.album_ingest.arn
}

# Saved-tracks (좋아요) sync — daily incremental + weekly full reconcile
# (FEAT-genre-artist-distribution Step 2).
#
# Two rules, same constant-input pattern as spotify_listening / album_ingest (the
# handler routes on event["job"] before the alias source check, then reads
# event["mode"]). The worker upserts the spotify_saved_tracks cache from /me/tracks
# (reuses the user-library-read scope; never a synchronous Spotify call from a
# user-facing endpoint, rule #9):
#   - incremental (daily): fetch likes newer than max(added_at), upsert, no prune.
#   - full (weekly): page the whole library, upsert all + prune un-likes.
# The full-mode prune is cache-only (no Spotify write-back). Removing a rule stops
# that cadence; the manual blogSQS {"job":"spotify_saved_tracks_sync","mode":…}
# message still works either way.
resource "aws_cloudwatch_event_rule" "spotify_saved_tracks_incremental" {
  name                = "worker-spotify-saved-tracks-incremental"
  description         = "Daily incremental Spotify saved-tracks (좋아요) cache refresh"
  schedule_expression = "cron(0 18 * * ? *)"
  state               = "ENABLED"
}

resource "aws_cloudwatch_event_target" "spotify_saved_tracks_incremental" {
  rule      = aws_cloudwatch_event_rule.spotify_saved_tracks_incremental.name
  target_id = "blogWorkerLambda-saved-tracks-incremental"
  arn       = aws_lambda_function.worker.arn
  input     = jsonencode({ job = "spotify_saved_tracks_sync", mode = "incremental" })
}

resource "aws_lambda_permission" "spotify_saved_tracks_incremental_events" {
  statement_id  = "AllowInvokeFromEventBridgeSavedTracksIncremental"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.worker.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.spotify_saved_tracks_incremental.arn
}

resource "aws_cloudwatch_event_rule" "spotify_saved_tracks_full" {
  name                = "worker-spotify-saved-tracks-full"
  description         = "Weekly full Spotify saved-tracks reconcile (upsert all + prune un-likes)"
  schedule_expression = "cron(0 19 ? * SUN *)"
  state               = "ENABLED"
}

resource "aws_cloudwatch_event_target" "spotify_saved_tracks_full" {
  rule      = aws_cloudwatch_event_rule.spotify_saved_tracks_full.name
  target_id = "blogWorkerLambda-saved-tracks-full"
  arn       = aws_lambda_function.worker.arn
  input     = jsonencode({ job = "spotify_saved_tracks_sync", mode = "full" })
}

resource "aws_lambda_permission" "spotify_saved_tracks_full_events" {
  statement_id  = "AllowInvokeFromEventBridgeSavedTracksFull"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.worker.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.spotify_saved_tracks_full.arn
}

# Incremental lyrics collection — FEAT-lyrics-corpus Step 3.
#
# Constant input {"job":"lyrics_incremental"} (same routing pattern as album_ingest /
# isrc_backfill; the handler matches event["job"] before the alias source check). The job
# follows the MusicBrainz alias-fill template: it selects recently-added tracks lacking a
# track_lyrics row, evaluates each via the LRCLIB /api/search API with the Step 2 canonical
# matcher, and writes exactly one outcome row per track (matched / no_lyrics / not_found /
# ambiguous / review_required) — that row is the sentinel, dropping the track from the pool.
# It is failure-isolated from album sync: a separate invocation from the SQS album path, a
# lyrics-source outage only skips rows. Bounded per run (settings.LYRICS_INCR_BATCH_LIMIT +
# a wall-clock budget) so it finishes inside the 120s worker timeout; per-row commits make an
# over-budget run resumable. Runs every 15 minutes so newly-ingested tracks get lyrics within
# minutes of landing (near-real-time); a run with an empty pool is a single SELECT and exits in
# milliseconds, and total LRCLIB volume is unchanged — each track is still evaluated once.
# Removing this rule stops scheduled collection; the job code is inert without it (the manual
# blogSQS {"job":"lyrics_incremental"} message still works either way).
resource "aws_cloudwatch_event_rule" "lyrics_incremental" {
  name                = "worker-lyrics-incremental"
  description         = "Incremental LRCLIB lyrics corpus collection for newly-ingested tracks"
  schedule_expression = "rate(15 minutes)"
  state               = "ENABLED"
}

resource "aws_cloudwatch_event_target" "lyrics_incremental" {
  rule      = aws_cloudwatch_event_rule.lyrics_incremental.name
  target_id = "blogWorkerLambda-lyrics-incremental"
  arn       = aws_lambda_function.worker.arn
  input     = jsonencode({ job = "lyrics_incremental" })
}

resource "aws_lambda_permission" "lyrics_incremental_events" {
  statement_id  = "AllowInvokeFromEventBridgeLyricsIncremental"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.worker.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.lyrics_incremental.arn
}

# Periodic lyrics reassessment — FEAT-lyrics-corpus Step 4.
#
# Constant input {"job":"lyrics_reassessment"} (same routing pattern as lyrics_incremental;
# handler matches event["job"] before the alias source check). Re-checks the UNRESOLVED corpus
# pool (not_found / ambiguous / review_required, stalest first) against current LRCLIB coverage
# with the Step 2 canonical matcher: promotes a track to matched/no_lyrics when evidence now
# supports it, refreshes a still-unresolved row (bumps updated_at so the queue rotates), and
# NEVER overwrites a good match (replacement guard — only strictly-stronger evidence replaces).
# Failure-isolated from album sync (separate invocation) and bounded per run
# (settings.LYRICS_REASSESS_BATCH_LIMIT + wall-clock budget) for the 120s worker timeout.
# Daily cadence (lower than the incremental job): coverage changes slowly, so re-checks pay off
# over weeks, and daily × batch-limit cycles the ~12.5k unresolved pool in ~2-3 months. Removing
# this rule stops scheduled reassessment; the manual blogSQS {"job":"lyrics_reassessment"}
# message still works either way.
resource "aws_cloudwatch_event_rule" "lyrics_reassessment" {
  name                = "worker-lyrics-reassessment"
  description         = "Periodic LRCLIB re-check of unresolved lyrics rows (promote-only, guarded)"
  schedule_expression = "rate(1 day)"
  state               = "ENABLED"
}

resource "aws_cloudwatch_event_target" "lyrics_reassessment" {
  rule      = aws_cloudwatch_event_rule.lyrics_reassessment.name
  target_id = "blogWorkerLambda-lyrics-reassessment"
  arn       = aws_lambda_function.worker.arn
  input     = jsonencode({ job = "lyrics_reassessment" })
}

resource "aws_lambda_permission" "lyrics_reassessment_events" {
  statement_id  = "AllowInvokeFromEventBridgeLyricsReassessment"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.worker.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.lyrics_reassessment.arn
}

# API Lambda warm ping — FIX-front-audit-2026-07 item 3.
#
# ratemymusic-api cold-starts at ~3.0-3.2s Init (CloudWatch, 2026-07-06 3-day
# sample), and the single-owner traffic pattern means the lyrics viewer (and any
# first authed action) usually lands on a cold instance → 4-6s opens. This rule
# invokes the backend Lambda every 5 minutes with a constant, Mangum-shaped
# API Gateway v2 event for GET /health (a PUBLIC_PATHS route: no auth, no DB
# round trip), keeping one execution environment resident for ~$0 (≈8.6k
# invocations/mo × ~10ms billed). The payload shape was validated against the
# live function pre-merge (200 {"ok":true}). Removing this rule just brings the
# cold starts back; nothing depends on it.
resource "aws_cloudwatch_event_rule" "backend_warm_ping" {
  name                = "backend-api-warm-ping"
  description         = "Keep ratemymusic-api warm (5-min GET /health via constant Mangum event)"
  schedule_expression = "rate(5 minutes)"
  state               = "ENABLED"
}

resource "aws_cloudwatch_event_target" "backend_warm_ping" {
  rule      = aws_cloudwatch_event_rule.backend_warm_ping.name
  target_id = "ratemymusic-api-warm-ping"
  arn       = aws_lambda_function.backend.arn
  input = jsonencode({
    version        = "2.0"
    routeKey       = "$default"
    rawPath        = "/health"
    rawQueryString = ""
    headers        = { host = "warm.internal", "user-agent" = "eventbridge-warm-ping" }
    requestContext = {
      accountId    = "warm"
      apiId        = "warm"
      domainName   = "warm.internal"
      domainPrefix = "warm"
      http = {
        method    = "GET"
        path      = "/health"
        protocol  = "HTTP/1.1"
        sourceIp  = "127.0.0.1"
        userAgent = "eventbridge-warm-ping"
      }
      requestId = "warm-ping"
      routeKey  = "$default"
      stage     = "$default"
      time      = "01/Jan/2026:00:00:00 +0000"
      timeEpoch = 0
    }
    isBase64Encoded = false
  })
}

resource "aws_lambda_permission" "backend_warm_ping_events" {
  statement_id  = "AllowInvokeFromEventBridgeWarmPing"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.backend.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.backend_warm_ping.arn
}
