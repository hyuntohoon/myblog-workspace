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

# FEAT-multi-user Phase 3a: per-user Last.fm recent-tracks poll. Constant input
# {"job":"lastfm_recent_tracks"} (handler checks event["job"] first, before the
# alias source check). The worker reads user.getRecentTracks for each connected
# user and upserts the lastfm_recent_tracks cache + now-playing row. NO-OP until
# the owner sets LASTFM_API_KEY in the SSM /myblog/worker blob (the handler guards
# on it). Never a synchronous Last.fm call from a user-facing endpoint (rule #9).
resource "aws_cloudwatch_event_rule" "lastfm_recent_tracks" {
  name                = "worker-lastfm-recent-tracks"
  description         = "Per-user Last.fm recent-tracks + now-playing poll (15 min)"
  schedule_expression = "rate(15 minutes)"
  state               = "ENABLED"
}

resource "aws_cloudwatch_event_target" "lastfm_recent_tracks" {
  rule      = aws_cloudwatch_event_rule.lastfm_recent_tracks.name
  target_id = "blogWorkerLambda-lastfm-recent-tracks"
  arn       = aws_lambda_function.worker.arn
  input     = jsonencode({ job = "lastfm_recent_tracks" })
}

resource "aws_lambda_permission" "lastfm_recent_tracks_events" {
  statement_id  = "AllowInvokeFromEventBridgeLastfmRecentTracks"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.worker.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.lastfm_recent_tracks.arn
}

# FEAT-multi-user 3b-d: per-user Spotify listening poll (5-user tier). Constant
# input {"job":"spotify_member_poll"} — KMS-decrypt each connected member's
# refresh token, refresh, rotate/re-encrypt, write the V45 member listening
# tables. Naturally dormant until the 3b-a CMK is applied AND members connect
# (3b-c fails closed pre-CMK, so no connected rows can pre-exist the key).
# rate(15 minutes) = the lastfm precedent; ~3 req/user/tick, trivial at <=5 users.
resource "aws_cloudwatch_event_rule" "spotify_member_poll" {
  name                = "worker-spotify-member-poll"
  description         = "Per-member Spotify now-playing + recently-played poll (15 min)"
  schedule_expression = "rate(15 minutes)"
  state               = "ENABLED"
}

resource "aws_cloudwatch_event_target" "spotify_member_poll" {
  rule      = aws_cloudwatch_event_rule.spotify_member_poll.name
  target_id = "blogWorkerLambda-spotify-member-poll"
  arn       = aws_lambda_function.worker.arn
  input     = jsonencode({ job = "spotify_member_poll" })
}

resource "aws_lambda_permission" "spotify_member_poll_events" {
  statement_id  = "AllowInvokeFromEventBridgeSpotifyMemberPoll"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.worker.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.spotify_member_poll.arn
}

# FEAT-release-calendar Step 4: multi-source upcoming-release poller. TWO rules,
# one per source ({"job":"release_upcoming_poll","mode":...} — handler routes on
# event["job"] then event["mode"], saved_tracks pattern), so one source lagging
# or failing never delays the other. Deliberately EventBridge-only, never the
# blogSQS queue — an MB/iTunes outage must not clog album sync (the same
# boundary that keeps the MusicBrainz alias fill off SQS). Each tick processes
# a stateless time-bucket of the pop>=50 watchlist bounded for the 120 s Lambda;
# the rates below are COUPLED to the tick-index divisors in
# worker/service/release_upcoming_service.py (MB_TICK_SECONDS=3600 /
# ITUNES_TICK_SECONDS=1800): at 70 artists/tick hourly the ~1,530-artist MB
# cycle completes in ~22 h, at 22 artists/tick half-hourly the iTunes cycle in
# ~21 h — full watchlist coverage about once a day. Removing a rule stops that
# source's polling; the job code is inert without it.
resource "aws_cloudwatch_event_rule" "release_upcoming_mb" {
  name                = "worker-release-upcoming-mb"
  description         = "Upcoming-release poll, MusicBrainz release-group pass (hourly bucket)"
  schedule_expression = "rate(1 hour)"
  state               = "ENABLED"
}

resource "aws_cloudwatch_event_target" "release_upcoming_mb" {
  rule      = aws_cloudwatch_event_rule.release_upcoming_mb.name
  target_id = "blogWorkerLambda-release-upcoming-mb"
  arn       = aws_lambda_function.worker.arn
  input     = jsonencode({ job = "release_upcoming_poll", mode = "musicbrainz" })
}

resource "aws_lambda_permission" "release_upcoming_mb_events" {
  statement_id  = "AllowInvokeFromEventBridgeReleaseUpcomingMb"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.worker.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.release_upcoming_mb.arn
}

resource "aws_cloudwatch_event_rule" "release_upcoming_itunes" {
  name                = "worker-release-upcoming-itunes"
  description         = "Upcoming-release poll, iTunes pre-order pass (half-hourly bucket)"
  schedule_expression = "rate(30 minutes)"
  state               = "ENABLED"
}

resource "aws_cloudwatch_event_target" "release_upcoming_itunes" {
  rule      = aws_cloudwatch_event_rule.release_upcoming_itunes.name
  target_id = "blogWorkerLambda-release-upcoming-itunes"
  arn       = aws_lambda_function.worker.arn
  input     = jsonencode({ job = "release_upcoming_poll", mode = "itunes" })
}

resource "aws_lambda_permission" "release_upcoming_itunes_events" {
  statement_id  = "AllowInvokeFromEventBridgeReleaseUpcomingItunes"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.worker.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.release_upcoming_itunes.arn
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

# Weekly artist-photo backfill sweep — BUG-artist-image-backfill Step 3.
#
# Constant input {"job":"artist_photo_backfill"} (same routing pattern as
# lyrics_incremental; the handler matches event["job"] before the alias source
# check — worker/handler.py). The job selects artists with photo_url IS NULL and
# runs the Step-1 enrich routine over them: photo filled when Spotify has one,
# '' sentinel written when it doesn't, so a swept row never re-enters the pool.
# The Step-2 one-shot cleared the 463-row backlog (still_null 463→0, 2026-07-19);
# this sweep only catches artists created outside an album-sync enrich window
# (insert-then-enrich-failed, candidates-path upsert_min), so a normal week
# selects ~0 rows and exits in milliseconds. Weekly cadence, offset one hour
# from the saved-tracks full reconcile (19:00 SUN) to keep the two scheduled
# Spotify consumers apart. Failure-isolated from album sync and from the
# MusicBrainz alias fill (separate invocations). Removing this rule stops the
# sweep; the manual blogSQS {"job":"artist_photo_backfill"} message still works
# either way.
resource "aws_cloudwatch_event_rule" "artist_photo_backfill" {
  name                = "worker-artist-photo-backfill"
  description         = "Weekly enrich sweep of artists with photo_url IS NULL (fill or '' sentinel)"
  schedule_expression = "cron(0 20 ? * SUN *)"
  state               = "ENABLED"
}

resource "aws_cloudwatch_event_target" "artist_photo_backfill" {
  rule      = aws_cloudwatch_event_rule.artist_photo_backfill.name
  target_id = "blogWorkerLambda-artist-photo-backfill"
  arn       = aws_lambda_function.worker.arn
  input     = jsonencode({ job = "artist_photo_backfill" })
}

resource "aws_lambda_permission" "artist_photo_backfill_events" {
  statement_id  = "AllowInvokeFromEventBridgeArtistPhotoBackfill"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.worker.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.artist_photo_backfill.arn
}

# ISRC backfill — FEAT-lyrics-corpus Step 1b, shipped 2026-07 but never scheduled.
#
# Constant input {"job":"isrc_backfill"} (same routing pattern as lyrics_incremental /
# artist_photo_backfill; the handler matches event["job"] before the alias source check).
# The job selects tracks with no ISRC and no prior attempt, fetches them from Spotify
# GET /v1/tracks in chunks of 50, and writes either the real ISRC to `tracks.isrc` or a
# miss marker to `tracks.ext_refs->>'isrc_status'`. Bounded by
# settings.ISRC_BACKFILL_BATCH_LIMIT (500 = 10 Spotify chunks) plus a 90s wall-clock
# budget, so a run always finishes inside the 120s worker timeout; a run with an empty
# pool is a single SELECT and exits in milliseconds.
#
# The service and this rule were deliberately landed apart: until worker
# `fix/isrc-backfill-sentinel-schedule` is deployed, this job writes the string
# sentinels "not_found"/"no_isrc" INTO tracks.isrc, which would break every
# `isrc IS NOT NULL` predicate. Do not apply this rule against an older worker build.
#
# Hourly rather than daily only while the ~19.3k backlog drains (≈39 runs); once
# `SELECT count(*) FROM tracks WHERE isrc IS NULL AND ext_refs->>'isrc' IS NULL
# AND ext_refs->>'isrc_status' IS NULL` flattens, drop this to weekly — steady-state
# demand is only newly-ingested tracks. Failure-isolated from album sync (separate
# invocation); a Spotify outage only skips rows.
#
# Removing this rule stops scheduled backfill; the job code is inert without it (the
# manual blogSQS {"job":"isrc_backfill"} message still works either way).
resource "aws_cloudwatch_event_rule" "isrc_backfill" {
  name                = "worker-isrc-backfill"
  description         = "Backfill tracks.isrc from Spotify (bounded; miss → ext_refs.isrc_status)"
  schedule_expression = "rate(1 hour)"
  state               = "ENABLED"
}

resource "aws_cloudwatch_event_target" "isrc_backfill" {
  rule      = aws_cloudwatch_event_rule.isrc_backfill.name
  target_id = "blogWorkerLambda-isrc-backfill"
  arn       = aws_lambda_function.worker.arn
  input     = jsonencode({ job = "isrc_backfill" })
}

resource "aws_lambda_permission" "isrc_backfill_events" {
  statement_id  = "AllowInvokeFromEventBridgeIsrcBackfill"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.worker.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.isrc_backfill.arn
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

# musicApi warm ping — PERF-home-feed-latency (2026-07-23 audit P-9).
#
# musicApi cold-starts at ~7s: measured 2026-07-23 the homepage's first
# GET /api/music/feed/new-releases = 7.21s, warm = 0.73s (req 2/3). The DB query
# itself is 0.55ms (EXPLAIN ANALYZE, prod) over a 2,884-row albums table with
# `artists` already selectinload-ed — so the cost is Lambda Init, NOT the query
# or an N+1. Unlike ratemymusic-api (backend_warm_ping above), musicApi had no
# warm ping, so the homepage's first music request (new-releases + on-this-day)
# paid the full cold start. This rule invokes musicApi every 5 minutes with a
# constant, Mangum-shaped API Gateway v2 event for
# GET /api/music/feed/new-releases?days=1&limit=1 — a public, DB-only route
# (musicApi has no edge_guard; days/limit have defaults) — keeping one execution
# environment + a warm pooled DB connection resident for ~$0 (≈8.6k invocations/mo).
# Removing this rule just brings the cold starts back; nothing depends on it.
resource "aws_cloudwatch_event_rule" "music_warm_ping" {
  name                = "music-api-warm-ping"
  description         = "Keep musicApi warm (5-min GET /api/music/feed/new-releases via constant Mangum event)"
  schedule_expression = "rate(5 minutes)"
  state               = "ENABLED"
}

resource "aws_cloudwatch_event_target" "music_warm_ping" {
  rule      = aws_cloudwatch_event_rule.music_warm_ping.name
  target_id = "musicApi-warm-ping"
  arn       = aws_lambda_function.music.arn
  input = jsonencode({
    version        = "2.0"
    routeKey       = "$default"
    rawPath        = "/api/music/feed/new-releases"
    rawQueryString = "days=1&limit=1"
    headers        = { host = "warm.internal", "user-agent" = "eventbridge-warm-ping" }
    requestContext = {
      accountId    = "warm"
      apiId        = "warm"
      domainName   = "warm.internal"
      domainPrefix = "warm"
      http = {
        method    = "GET"
        path      = "/api/music/feed/new-releases"
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

resource "aws_lambda_permission" "music_warm_ping_events" {
  statement_id  = "AllowInvokeFromEventBridgeWarmPing"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.music.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.music_warm_ping.arn
}
