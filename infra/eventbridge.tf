# ── Worker cron rules — single source of truth ────────────────────────────────
#
# OPS-safety-net-drift Step 1 (derive-not-declare): every scheduled invocation of
# the worker Lambda is declared ONCE in local.worker_crons, and the rule, target,
# permission AND the FailedInvocations alarm (monitoring.tf, for_each over
# aws_cloudwatch_event_rule.worker_cron) are all generated from it. Adding a cron
# here cannot skip its alarm — the alarm exists by construction. The predecessor
# was a hand-maintained alarm map in monitoring.tf that silently regressed to
# 12-of-13 two days after being closed as "ALL worker crons" (audit OPS-1).
#
# Do NOT add a standalone aws_cloudwatch_event_rule for a worker cron — that
# recreates exactly the blind spot this structure removes. Non-worker rules
# (the two warm pings below) stay standalone on purpose: they target other
# Lambdas and are deliberately outside the alarm set.
#
# Per-entry fields: name/description/schedule are the rule; input is the constant
# target payload (null = default scheduled event, which carries
# source == "aws.events"); target_id and statement_id are frozen at their
# pre-consolidation values so `terraform plan` stays 0 changed / 0 destroyed
# (both force replacement when altered).

locals {
  worker_crons = {
    # MusicBrainz alias generation. The SQS path and this schedule share one
    # Lambda; the handler tells them apart via event["source"] == "aws.events"
    # (worker/handler.py), which the default scheduled event always carries — so
    # no target input. generate_and_save_aliases() looks up MusicBrainz for any
    # artist with musicbrainz_id IS NULL, then writes either the MBID + aliases
    # or a MBID_NOT_FOUND sentinel. No Gemini fallback (was planned, never
    # implemented).
    musicbrainz_alias = {
      name         = "worker-musicbrainz-alias-generation"
      description  = "Backfill artists.musicbrainz_id + aliases via MusicBrainz lookup"
      schedule     = "rate(15 minutes)"
      input        = null
      target_id    = "blogWorkerLambda"
      statement_id = "AllowInvokeFromEventBridge"
    }

    # Spotify listening cache sync (FEAT-member-dashboard Step 3, D5). Constant
    # input fully replaces the event payload (so it carries no
    # "source":"aws.events"); the handler checks event["job"] first, before the
    # alias source check. Reads /me/player/recently-played + currently-playing
    # and upserts the spotify_recent_albums / spotify_now_playing cache. Never a
    # synchronous Spotify call from a user-facing endpoint (rule #9).
    spotify_listening = {
      name         = "worker-spotify-listening-sync"
      description  = "Hourly Spotify recently-played + now-playing cache refresh"
      schedule     = "rate(1 hour)"
      input        = { job = "spotify_listening" }
      target_id    = "blogWorkerLambda-spotify-listening"
      statement_id = "AllowInvokeFromEventBridgeSpotifyListening"
    }

    # FEAT-multi-user Phase 3a: per-user Last.fm recent-tracks poll. Reads
    # user.getRecentTracks for each connected user and upserts the
    # lastfm_recent_tracks cache + now-playing row. NO-OP until the owner sets
    # LASTFM_API_KEY in the SSM /myblog/worker blob (the handler guards on it).
    lastfm_recent_tracks = {
      name         = "worker-lastfm-recent-tracks"
      description  = "Per-user Last.fm recent-tracks + now-playing poll (15 min)"
      schedule     = "rate(15 minutes)"
      input        = { job = "lastfm_recent_tracks" }
      target_id    = "blogWorkerLambda-lastfm-recent-tracks"
      statement_id = "AllowInvokeFromEventBridgeLastfmRecentTracks"
    }

    # FEAT-multi-user 3b-d: per-user Spotify listening poll (5-user tier).
    # KMS-decrypt each connected member's refresh token, refresh,
    # rotate/re-encrypt, write the V45 member listening tables. Naturally
    # dormant until the 3b-a CMK is applied AND members connect (3b-c fails
    # closed pre-CMK). rate(15 minutes) = the lastfm precedent; ~3
    # req/user/tick, trivial at <=5 users.
    spotify_member_poll = {
      name         = "worker-spotify-member-poll"
      description  = "Per-member Spotify now-playing + recently-played poll (15 min)"
      schedule     = "rate(15 minutes)"
      input        = { job = "spotify_member_poll" }
      target_id    = "blogWorkerLambda-spotify-member-poll"
      statement_id = "AllowInvokeFromEventBridgeSpotifyMemberPoll"
    }

    # FEAT-release-calendar Step 4: multi-source upcoming-release poller. TWO
    # entries, one per source (handler routes on event["job"] then
    # event["mode"]), so one source lagging or failing never delays the other.
    # Deliberately EventBridge-only, never the blogSQS queue — an MB/iTunes
    # outage must not clog album sync (the same boundary that keeps the
    # MusicBrainz alias fill off SQS). Each tick processes a stateless
    # time-bucket of the pop>=50 watchlist bounded for the 120 s Lambda; the
    # rates are COUPLED to the tick-index divisors in
    # worker/service/release_upcoming_service.py (MB_TICK_SECONDS=3600 /
    # ITUNES_TICK_SECONDS=1800): at 70 artists/tick hourly the ~1,530-artist MB
    # cycle completes in ~22 h, at 22 artists/tick half-hourly the iTunes cycle
    # in ~21 h — full watchlist coverage about once a day. Removing an entry
    # stops that source's polling; the job code is inert without it.
    release_upcoming_mb = {
      name         = "worker-release-upcoming-mb"
      description  = "Upcoming-release poll, MusicBrainz release-group pass (hourly bucket)"
      schedule     = "rate(1 hour)"
      input        = { job = "release_upcoming_poll", mode = "musicbrainz" }
      target_id    = "blogWorkerLambda-release-upcoming-mb"
      statement_id = "AllowInvokeFromEventBridgeReleaseUpcomingMb"
    }

    release_upcoming_itunes = {
      name         = "worker-release-upcoming-itunes"
      description  = "Upcoming-release poll, iTunes pre-order pass (half-hourly bucket)"
      schedule     = "rate(30 minutes)"
      input        = { job = "release_upcoming_poll", mode = "itunes" }
      target_id    = "blogWorkerLambda-release-upcoming-itunes"
      statement_id = "AllowInvokeFromEventBridgeReleaseUpcomingItunes"
    }

    # Album-catalog ingest (FEAT-album-catalog-ingest Step 3). Sweeps
    # gate-passing catalog artists for new full-length releases and enqueues
    # novel IDs onto the existing blogSQS album-sync pipeline — discover+enqueue
    # only, the upsert runs in the SQS consumer. Worker-role sqs:SendMessage and
    # SQS_QUEUE_URL already exist (worker_sqs_produce / lambda.tf). Removing
    # this entry stops all scheduled ingest immediately.
    album_ingest = {
      name         = "worker-album-catalog-ingest"
      description  = "Daily new-release sweep of catalog artists into the album-sync pipeline"
      schedule     = "rate(1 day)"
      input        = { job = "album_ingest" }
      target_id    = "blogWorkerLambda-album-ingest"
      statement_id = "AllowInvokeFromEventBridgeAlbumIngest"
    }

    # Saved-tracks (좋아요) sync (FEAT-genre-artist-distribution Step 2): daily
    # incremental + weekly full reconcile, two entries with the same job and
    # different modes. Upserts the spotify_saved_tracks cache from /me/tracks
    # (reuses the user-library-read scope; rule #9 applies):
    #   - incremental (daily): fetch likes newer than max(added_at), upsert, no prune.
    #   - full (weekly): page the whole library, upsert all + prune un-likes.
    # The full-mode prune is cache-only (no Spotify write-back). The manual
    # blogSQS {"job":"spotify_saved_tracks_sync","mode":…} message still works
    # either way.
    spotify_saved_tracks_incremental = {
      name         = "worker-spotify-saved-tracks-incremental"
      description  = "Daily incremental Spotify saved-tracks (좋아요) cache refresh"
      schedule     = "cron(0 18 * * ? *)"
      input        = { job = "spotify_saved_tracks_sync", mode = "incremental" }
      target_id    = "blogWorkerLambda-saved-tracks-incremental"
      statement_id = "AllowInvokeFromEventBridgeSavedTracksIncremental"
    }

    spotify_saved_tracks_full = {
      name         = "worker-spotify-saved-tracks-full"
      description  = "Weekly full Spotify saved-tracks reconcile (upsert all + prune un-likes)"
      schedule     = "cron(0 19 ? * SUN *)"
      input        = { job = "spotify_saved_tracks_sync", mode = "full" }
      target_id    = "blogWorkerLambda-saved-tracks-full"
      statement_id = "AllowInvokeFromEventBridgeSavedTracksFull"
    }

    # Incremental lyrics collection (FEAT-lyrics-corpus Step 3). Follows the
    # MusicBrainz alias-fill template: selects recently-added tracks lacking a
    # track_lyrics row, evaluates each via the LRCLIB /api/search API with the
    # Step 2 canonical matcher, and writes exactly one outcome row per track
    # (matched / no_lyrics / not_found / ambiguous / review_required) — that row
    # is the sentinel, dropping the track from the pool. Failure-isolated from
    # album sync; bounded per run (settings.LYRICS_INCR_BATCH_LIMIT + a
    # wall-clock budget) for the 120s worker timeout; per-row commits make an
    # over-budget run resumable. 15-min cadence = near-real-time lyrics for new
    # tracks; an empty pool is a single SELECT and exits in milliseconds. The
    # manual blogSQS {"job":"lyrics_incremental"} message still works either way.
    lyrics_incremental = {
      name         = "worker-lyrics-incremental"
      description  = "Incremental LRCLIB lyrics corpus collection for newly-ingested tracks"
      schedule     = "rate(15 minutes)"
      input        = { job = "lyrics_incremental" }
      target_id    = "blogWorkerLambda-lyrics-incremental"
      statement_id = "AllowInvokeFromEventBridgeLyricsIncremental"
    }

    # Periodic lyrics reassessment (FEAT-lyrics-corpus Step 4). Re-checks the
    # UNRESOLVED corpus pool (not_found / ambiguous / review_required, stalest
    # first) against current LRCLIB coverage: promotes a track to
    # matched/no_lyrics when evidence now supports it, refreshes a
    # still-unresolved row (bumps updated_at so the queue rotates), and NEVER
    # overwrites a good match (replacement guard — only strictly-stronger
    # evidence replaces). Bounded per run (settings.LYRICS_REASSESS_BATCH_LIMIT
    # + wall-clock budget). Daily cadence: coverage changes slowly; daily ×
    # batch-limit cycles the ~12.5k unresolved pool in ~2-3 months. The manual
    # blogSQS {"job":"lyrics_reassessment"} message still works either way.
    lyrics_reassessment = {
      name         = "worker-lyrics-reassessment"
      description  = "Periodic LRCLIB re-check of unresolved lyrics rows (promote-only, guarded)"
      schedule     = "rate(1 day)"
      input        = { job = "lyrics_reassessment" }
      target_id    = "blogWorkerLambda-lyrics-reassessment"
      statement_id = "AllowInvokeFromEventBridgeLyricsReassessment"
    }

    # Weekly artist-photo backfill sweep (BUG-artist-image-backfill Step 3).
    # Selects artists with photo_url IS NULL and runs the Step-1 enrich routine:
    # photo filled when Spotify has one, '' sentinel written when it doesn't, so
    # a swept row never re-enters the pool. The Step-2 one-shot cleared the
    # 463-row backlog (still_null 463→0, 2026-07-19); this sweep only catches
    # artists created outside an album-sync enrich window, so a normal week
    # selects ~0 rows. Weekly, offset one hour from the saved-tracks full
    # reconcile (19:00 SUN) to keep the two scheduled Spotify consumers apart.
    # The manual blogSQS {"job":"artist_photo_backfill"} message still works
    # either way.
    artist_photo_backfill = {
      name         = "worker-artist-photo-backfill"
      description  = "Weekly enrich sweep of artists with photo_url IS NULL (fill or '' sentinel)"
      schedule     = "cron(0 20 ? * SUN *)"
      input        = { job = "artist_photo_backfill" }
      target_id    = "blogWorkerLambda-artist-photo-backfill"
      statement_id = "AllowInvokeFromEventBridgeArtistPhotoBackfill"
    }

    # ISRC backfill (FEAT-lyrics-corpus Step 1b). Selects tracks with no ISRC
    # and no prior attempt, fetches Spotify GET /v1/tracks in chunks of 50, and
    # writes either the real ISRC to tracks.isrc or a miss marker to
    # tracks.ext_refs->>'isrc_status'. Bounded by
    # settings.ISRC_BACKFILL_BATCH_LIMIT (500 = 10 Spotify chunks) + a 90s
    # wall-clock budget. WEEKLY since 2026-07-26: the one-time backlog was
    # drained by hand the same day (6 manual invokes at limit=3000, ~41s each;
    # coverage 0% → 99.9%, 26,594 of 26,619 — the 25 misses are tracks Spotify
    # genuinely has no ISRC for). Measured headroom for any future bulk re-run:
    # 500 rows = 4.9s, 3,000 = 41s against the 90s budget, so ~6,000/invocation
    # is the practical ceiling. 21:00 UTC Sunday keeps it one hour clear of the
    # Spotify sequence (saved-tracks 18:00 daily / 19:00 SUN, artist-photo
    # 20:00 SUN) so the four never contend for the same quota window. The
    # manual blogSQS {"job":"isrc_backfill"} message still works either way.
    #
    # This was audit OPS-1's missing-alarm instance: scheduled 2026-07-26,
    # never added to the hand-maintained alarm map — the regression that
    # motivated this file's derive-not-declare structure.
    isrc_backfill = {
      name         = "worker-isrc-backfill"
      description  = "Weekly ISRC top-up for newly-ingested tracks (miss → ext_refs.isrc_status)"
      schedule     = "cron(0 21 ? * SUN *)"
      input        = { job = "isrc_backfill" }
      target_id    = "blogWorkerLambda-isrc-backfill"
      statement_id = "AllowInvokeFromEventBridgeIsrcBackfill"
    }
  }
}

resource "aws_cloudwatch_event_rule" "worker_cron" {
  for_each            = local.worker_crons
  name                = each.value.name
  description         = each.value.description
  schedule_expression = each.value.schedule
  state               = "ENABLED"
}

resource "aws_cloudwatch_event_target" "worker_cron" {
  for_each  = local.worker_crons
  rule      = aws_cloudwatch_event_rule.worker_cron[each.key].name
  target_id = each.value.target_id
  arn       = aws_lambda_function.worker.arn
  input     = each.value.input == null ? null : jsonencode(each.value.input)
}

resource "aws_lambda_permission" "worker_cron" {
  for_each      = local.worker_crons
  statement_id  = each.value.statement_id
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.worker.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.worker_cron[each.key].arn
}

# ── State moves: pre-consolidation individual resources → for_each instances ──
# One trio per cron. Pure address renames; `terraform plan` must report
# 0 changed / 0 destroyed across all of them.

moved {
  from = aws_cloudwatch_event_rule.musicbrainz_alias
  to   = aws_cloudwatch_event_rule.worker_cron["musicbrainz_alias"]
}
moved {
  from = aws_cloudwatch_event_target.musicbrainz_alias
  to   = aws_cloudwatch_event_target.worker_cron["musicbrainz_alias"]
}
moved {
  from = aws_lambda_permission.musicbrainz_alias_events
  to   = aws_lambda_permission.worker_cron["musicbrainz_alias"]
}

moved {
  from = aws_cloudwatch_event_rule.spotify_listening
  to   = aws_cloudwatch_event_rule.worker_cron["spotify_listening"]
}
moved {
  from = aws_cloudwatch_event_target.spotify_listening
  to   = aws_cloudwatch_event_target.worker_cron["spotify_listening"]
}
moved {
  from = aws_lambda_permission.spotify_listening_events
  to   = aws_lambda_permission.worker_cron["spotify_listening"]
}

moved {
  from = aws_cloudwatch_event_rule.lastfm_recent_tracks
  to   = aws_cloudwatch_event_rule.worker_cron["lastfm_recent_tracks"]
}
moved {
  from = aws_cloudwatch_event_target.lastfm_recent_tracks
  to   = aws_cloudwatch_event_target.worker_cron["lastfm_recent_tracks"]
}
moved {
  from = aws_lambda_permission.lastfm_recent_tracks_events
  to   = aws_lambda_permission.worker_cron["lastfm_recent_tracks"]
}

moved {
  from = aws_cloudwatch_event_rule.spotify_member_poll
  to   = aws_cloudwatch_event_rule.worker_cron["spotify_member_poll"]
}
moved {
  from = aws_cloudwatch_event_target.spotify_member_poll
  to   = aws_cloudwatch_event_target.worker_cron["spotify_member_poll"]
}
moved {
  from = aws_lambda_permission.spotify_member_poll_events
  to   = aws_lambda_permission.worker_cron["spotify_member_poll"]
}

moved {
  from = aws_cloudwatch_event_rule.release_upcoming_mb
  to   = aws_cloudwatch_event_rule.worker_cron["release_upcoming_mb"]
}
moved {
  from = aws_cloudwatch_event_target.release_upcoming_mb
  to   = aws_cloudwatch_event_target.worker_cron["release_upcoming_mb"]
}
moved {
  from = aws_lambda_permission.release_upcoming_mb_events
  to   = aws_lambda_permission.worker_cron["release_upcoming_mb"]
}

moved {
  from = aws_cloudwatch_event_rule.release_upcoming_itunes
  to   = aws_cloudwatch_event_rule.worker_cron["release_upcoming_itunes"]
}
moved {
  from = aws_cloudwatch_event_target.release_upcoming_itunes
  to   = aws_cloudwatch_event_target.worker_cron["release_upcoming_itunes"]
}
moved {
  from = aws_lambda_permission.release_upcoming_itunes_events
  to   = aws_lambda_permission.worker_cron["release_upcoming_itunes"]
}

moved {
  from = aws_cloudwatch_event_rule.album_ingest
  to   = aws_cloudwatch_event_rule.worker_cron["album_ingest"]
}
moved {
  from = aws_cloudwatch_event_target.album_ingest
  to   = aws_cloudwatch_event_target.worker_cron["album_ingest"]
}
moved {
  from = aws_lambda_permission.album_ingest_events
  to   = aws_lambda_permission.worker_cron["album_ingest"]
}

moved {
  from = aws_cloudwatch_event_rule.spotify_saved_tracks_incremental
  to   = aws_cloudwatch_event_rule.worker_cron["spotify_saved_tracks_incremental"]
}
moved {
  from = aws_cloudwatch_event_target.spotify_saved_tracks_incremental
  to   = aws_cloudwatch_event_target.worker_cron["spotify_saved_tracks_incremental"]
}
moved {
  from = aws_lambda_permission.spotify_saved_tracks_incremental_events
  to   = aws_lambda_permission.worker_cron["spotify_saved_tracks_incremental"]
}

moved {
  from = aws_cloudwatch_event_rule.spotify_saved_tracks_full
  to   = aws_cloudwatch_event_rule.worker_cron["spotify_saved_tracks_full"]
}
moved {
  from = aws_cloudwatch_event_target.spotify_saved_tracks_full
  to   = aws_cloudwatch_event_target.worker_cron["spotify_saved_tracks_full"]
}
moved {
  from = aws_lambda_permission.spotify_saved_tracks_full_events
  to   = aws_lambda_permission.worker_cron["spotify_saved_tracks_full"]
}

moved {
  from = aws_cloudwatch_event_rule.lyrics_incremental
  to   = aws_cloudwatch_event_rule.worker_cron["lyrics_incremental"]
}
moved {
  from = aws_cloudwatch_event_target.lyrics_incremental
  to   = aws_cloudwatch_event_target.worker_cron["lyrics_incremental"]
}
moved {
  from = aws_lambda_permission.lyrics_incremental_events
  to   = aws_lambda_permission.worker_cron["lyrics_incremental"]
}

moved {
  from = aws_cloudwatch_event_rule.lyrics_reassessment
  to   = aws_cloudwatch_event_rule.worker_cron["lyrics_reassessment"]
}
moved {
  from = aws_cloudwatch_event_target.lyrics_reassessment
  to   = aws_cloudwatch_event_target.worker_cron["lyrics_reassessment"]
}
moved {
  from = aws_lambda_permission.lyrics_reassessment_events
  to   = aws_lambda_permission.worker_cron["lyrics_reassessment"]
}

moved {
  from = aws_cloudwatch_event_rule.artist_photo_backfill
  to   = aws_cloudwatch_event_rule.worker_cron["artist_photo_backfill"]
}
moved {
  from = aws_cloudwatch_event_target.artist_photo_backfill
  to   = aws_cloudwatch_event_target.worker_cron["artist_photo_backfill"]
}
moved {
  from = aws_lambda_permission.artist_photo_backfill_events
  to   = aws_lambda_permission.worker_cron["artist_photo_backfill"]
}

moved {
  from = aws_cloudwatch_event_rule.isrc_backfill
  to   = aws_cloudwatch_event_rule.worker_cron["isrc_backfill"]
}
moved {
  from = aws_cloudwatch_event_target.isrc_backfill
  to   = aws_cloudwatch_event_target.worker_cron["isrc_backfill"]
}
moved {
  from = aws_lambda_permission.isrc_backfill_events
  to   = aws_lambda_permission.worker_cron["isrc_backfill"]
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
