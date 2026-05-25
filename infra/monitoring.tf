locals {
  # logical name -> actual Lambda function name
  lambda_functions = {
    backend = "ratemymusic-api"
    music   = "musicApi"
    worker  = "blogWorkerLambda"
    publish = "publisher-github"
  }
}

# --- Log groups (imported; retention corrected None -> 14 days for cost) ---
resource "aws_cloudwatch_log_group" "lambda" {
  for_each          = local.lambda_functions
  name              = "/aws/lambda/${each.value}"
  retention_in_days = 14
}

# --- Lambda error / throttle alarms (new) ---
# No alarm_actions yet — SNS notification wiring is a follow-up. Alarms are
# still visible in the console and queryable via the CloudWatch API.
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

  dimensions = {
    FunctionName = each.value
  }
}

# --- DLQ alarm: messages reaching the DLQ mean the worker failed after retries ---
resource "aws_cloudwatch_metric_alarm" "dlq_messages" {
  alarm_name          = "album-sync-dlq-messages"
  alarm_description   = "Album sync messages reached DLQ — worker failing after retries"
  namespace           = "AWS/SQS"
  metric_name         = "NumberOfMessagesSent"
  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 1
  threshold           = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"

  dimensions = {
    QueueName = aws_sqs_queue.album_sync_dlq.name
  }
}
