resource "aws_sqs_queue" "album_sync_dlq" {
  name                       = "album-sync-dlq"
  message_retention_seconds  = 1209600 # 14 days
  visibility_timeout_seconds = 30

  lifecycle {
    ignore_changes = [max_message_size]
  }
}

# OPS-delivery-safety-gates Step 4 — async on-failure DLQ for the worker's
# EventBridge crons. EventBridge invokes the worker ASYNCHRONOUSLY; a handler that
# throws after Lambda's async retries would otherwise be silently discarded. The
# worker's event_invoke_config on_failure destination (lambda.tf) parks the failed
# invocation record (payload + error) here for inspection/replay. Distinct from
# album-sync-dlq, which is the SQS-ESM (blogSQS) redrive target — a different path.
resource "aws_sqs_queue" "worker_cron_dlq" {
  name                      = "worker-cron-dlq"
  message_retention_seconds = 1209600 # 14 days

  lifecycle {
    ignore_changes = [max_message_size]
  }
}

resource "aws_sqs_queue" "blog_sqs" {
  name                       = "blogSQS"
  message_retention_seconds  = 345600 # 4 days
  visibility_timeout_seconds = 720    # STAB-3: >= worker Lambda timeout (120s); 6x AWS-recommended margin. DLQ visibility unchanged (no consumer).

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.album_sync_dlq.arn
    maxReceiveCount     = 3
  })

  lifecycle {
    ignore_changes = [max_message_size]
  }
}

# --- researchSQS + album-research-dlq: REMOVED (FIX-bug-audit-2026-07 WS-G) ---
# Torn down with researchWorkerLambda (see lambda.tf). Research runs $0/local-
# poller mode; the queue had no real consumer and silently dropped messages.
