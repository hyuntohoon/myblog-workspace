resource "aws_sqs_queue" "album_sync_dlq" {
  name                       = "album-sync-dlq"
  message_retention_seconds  = 1209600 # 14 days
  visibility_timeout_seconds = 30
}

resource "aws_sqs_queue" "blog_sqs" {
  name                       = "blogSQS"
  message_retention_seconds  = 345600 # 4 days
  visibility_timeout_seconds = 30

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.album_sync_dlq.arn
    maxReceiveCount     = 3
  })
}
