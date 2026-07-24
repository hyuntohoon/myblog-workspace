# --- SNS topic for CloudWatch alarm notifications ---
resource "aws_sns_topic" "alerts" {
  name = "myblog-alerts"
}

resource "aws_sns_topic_subscription" "alerts_email" {
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

locals {
  # logical name -> actual Lambda function name
  lambda_functions = {
    backend = "ratemymusic-api"
    music   = "musicApi"
    worker  = "blogWorkerLambda"
  }
}

# --- Log groups (imported; retention corrected None -> 14 days for cost) ---
resource "aws_cloudwatch_log_group" "lambda" {
  for_each          = local.lambda_functions
  name              = "/aws/lambda/${each.value}"
  retention_in_days = 14
}

# --- Lambda error / throttle alarms ---
resource "aws_cloudwatch_metric_alarm" "lambda_errors" {
  for_each            = local.lambda_functions
  alarm_name          = "${each.value}-errors"
  alarm_description   = "Lambda invocation errors >= 1 over two 5-min periods"
  namespace           = "AWS/Lambda"
  metric_name         = "Errors"
  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 2
  threshold           = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  ok_actions          = [aws_sns_topic.alerts.arn]

  dimensions = {
    FunctionName = each.value
  }
}

resource "aws_cloudwatch_metric_alarm" "lambda_throttles" {
  for_each            = local.lambda_functions
  alarm_name          = "${each.value}-throttles"
  alarm_description   = "Lambda throttles >= 5 over two 5-min periods"
  namespace           = "AWS/Lambda"
  metric_name         = "Throttles"
  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 2
  threshold           = 5
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    FunctionName = each.value
  }
}

# --- DLQ alarm: messages reaching the DLQ mean the worker failed after retries ---
# FIX-bug-audit-2026-07 WS-A: was NumberOfMessagesSent, which AWS does NOT
# increment for messages moved to a DLQ by a redrive policy — and redrive is the
# only way messages enter this DLQ (no direct producer). The alarm could never
# fire; poisoned messages aged out silently after 14 days. ApproximateNumberOf-
# MessagesVisible reflects the actual backlog. Use Maximum over the period (a
# Sum of a gauge metric is meaningless) and keep firing while anything is parked.
resource "aws_cloudwatch_metric_alarm" "dlq_messages" {
  alarm_name          = "album-sync-dlq-messages"
  alarm_description   = "Album sync messages visible in DLQ — worker failed after retries"
  namespace           = "AWS/SQS"
  metric_name         = "ApproximateNumberOfMessagesVisible"
  statistic           = "Maximum"
  period              = 300
  evaluation_periods  = 1
  threshold           = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    QueueName = aws_sqs_queue.album_sync_dlq.name
  }
}

# --- EventBridge cron delivery-failure alarms ---
# FailedInvocations fires when EventBridge cannot DELIVER a scheduled tick to the
# worker Lambda (target throttle / permission / delivery failure) — a failure mode
# the Lambda "Errors" alarm above cannot see, because the function never ran.
#
# OPS-delivery-safety-gates Step 4: extended from 2 rules to ALL worker crons (audit
# O-4 — 10 of ~12 rules were uncovered). Pairs with the worker-cron-dlq on-failure
# destination (lambda.tf): FailedInvocations catches DELIVERY failures (never ran),
# the DLQ catches HANDLER failures (ran and threw after retries) — together the full
# async failure boundary.
#
# Cache-staleness (recent-albums / now-playing rows going stale) is intentionally NOT
# covered: it is not a native CloudWatch metric and would need a custom-metric canary.
locals {
  worker_cron_rules = {
    spotify_listening                = aws_cloudwatch_event_rule.spotify_listening.name
    musicbrainz_alias                = aws_cloudwatch_event_rule.musicbrainz_alias.name
    lastfm_recent_tracks             = aws_cloudwatch_event_rule.lastfm_recent_tracks.name
    spotify_member_poll              = aws_cloudwatch_event_rule.spotify_member_poll.name
    release_upcoming_mb              = aws_cloudwatch_event_rule.release_upcoming_mb.name
    release_upcoming_itunes          = aws_cloudwatch_event_rule.release_upcoming_itunes.name
    album_ingest                     = aws_cloudwatch_event_rule.album_ingest.name
    spotify_saved_tracks_incremental = aws_cloudwatch_event_rule.spotify_saved_tracks_incremental.name
    spotify_saved_tracks_full        = aws_cloudwatch_event_rule.spotify_saved_tracks_full.name
    lyrics_incremental               = aws_cloudwatch_event_rule.lyrics_incremental.name
    lyrics_reassessment              = aws_cloudwatch_event_rule.lyrics_reassessment.name
    artist_photo_backfill            = aws_cloudwatch_event_rule.artist_photo_backfill.name
  }
}

resource "aws_cloudwatch_metric_alarm" "cron_failed_invocations" {
  for_each            = local.worker_cron_rules
  alarm_name          = "${each.value}-failed-invocations"
  alarm_description   = "EventBridge rule ${each.value} failed to invoke the worker Lambda"
  namespace           = "AWS/Events"
  metric_name         = "FailedInvocations"
  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 1
  threshold           = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    RuleName = each.value
  }
}

# --- worker-cron-dlq alarm: async cron handler failed after retries ---
# OPS-delivery-safety-gates Step 4. Messages parked in worker-cron-dlq mean a cron
# invocation ran and threw, exhausting async retries — the payload+error record is
# preserved for replay. Same gauge-Maximum pattern as the album-sync-dlq alarm (a
# Sum of a gauge is meaningless; redrive/destination sends do not increment
# NumberOfMessagesSent).
resource "aws_cloudwatch_metric_alarm" "worker_cron_dlq_messages" {
  alarm_name          = "worker-cron-dlq-messages"
  alarm_description   = "Async cron invocation records parked in worker-cron-dlq — a cron handler failed after retries"
  namespace           = "AWS/SQS"
  metric_name         = "ApproximateNumberOfMessagesVisible"
  statistic           = "Maximum"
  period              = 300
  evaluation_periods  = 1
  threshold           = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    QueueName = aws_sqs_queue.worker_cron_dlq.name
  }
}
