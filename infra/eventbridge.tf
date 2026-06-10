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
