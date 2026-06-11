resource "aws_sqs_queue" "album_sync_dlq" {
  name                       = "album-sync-dlq"
  message_retention_seconds  = 1209600 # 14 days
  visibility_timeout_seconds = 30

  lifecycle {
    ignore_changes = [max_message_size]
  }
}

resource "aws_sqs_queue" "blog_sqs" {
  name                       = "blogSQS"
  message_retention_seconds  = 345600 # 4 days
  visibility_timeout_seconds = 720 # STAB-3: >= worker Lambda timeout (120s); 6x AWS-recommended margin. DLQ visibility unchanged (no consumer).

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.album_sync_dlq.arn
    maxReceiveCount     = 3
  })

  lifecycle {
    ignore_changes = [max_message_size]
  }
}

# --- FEAT-album-research-notes: dedicated long-job queue ---
# Research runs are 3–8 min API calls; they cannot ride blogSQS (visibility 720s
# is tuned to the 120s worker). Dedicated queue + dedicated 900s function.
resource "aws_sqs_queue" "research_dlq" {
  name                       = "album-research-dlq"
  message_retention_seconds  = 1209600 # 14 days
  visibility_timeout_seconds = 30

  lifecycle {
    ignore_changes = [max_message_size]
  }
}

resource "aws_sqs_queue" "research_sqs" {
  name                       = "researchSQS"
  message_retention_seconds  = 345600 # 4 days
  visibility_timeout_seconds = 5400 # 6x the 900s research Lambda timeout (STAB-3 rule)

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.research_dlq.arn
    maxReceiveCount     = 3
  })

  lifecycle {
    ignore_changes = [max_message_size]
  }
}
