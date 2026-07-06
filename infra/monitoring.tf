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

# --- EventBridge cron delivery-failure alarms (FEAT-member-dashboard follow-up) ---
# FailedInvocations fires when EventBridge cannot deliver a scheduled tick to the
# worker Lambda (target throttle / permission / delivery failure) — a failure mode
# the Lambda "Errors" alarm above cannot see, because the function never ran. Covers
# both worker crons (the Spotify listening sync + the MusicBrainz alias backfill);
# either silently stalling is the harm this catches.
#
# Cache-staleness (recent-albums / now-playing rows going stale) is intentionally NOT
# covered: it is not a native CloudWatch metric and would need a custom-metric canary
# — deferred to a follow-up (RFC "Follow-up rollout" item 5).
locals {
  worker_cron_rules = {
    spotify_listening = aws_cloudwatch_event_rule.spotify_listening.name
    musicbrainz_alias = aws_cloudwatch_event_rule.musicbrainz_alias.name
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
