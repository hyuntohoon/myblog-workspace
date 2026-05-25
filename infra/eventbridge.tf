# Gemini alias generation — scheduled invocation of the worker Lambda.
#
# The SQS path and this schedule share one Lambda. The handler tells them
# apart via event["source"] == "aws.events" (worker/handler.py), which the
# default EventBridge scheduled event always carries — so no target input
# is required.
#
# NOTE: alias generation is a no-op until GEMINI_API_KEY is added to the
# myblog/worker secret (generate_and_save_aliases early-returns without it).
resource "aws_cloudwatch_event_rule" "gemini_alias" {
  name                = "worker-gemini-alias-generation"
  description         = "Batch-generate Gemini aliases for artists without aliases"
  schedule_expression = "rate(15 minutes)"
  state               = "ENABLED"
}

resource "aws_cloudwatch_event_target" "gemini_alias" {
  rule      = aws_cloudwatch_event_rule.gemini_alias.name
  target_id = "blogWorkerLambda"
  arn       = aws_lambda_function.worker.arn
}

resource "aws_lambda_permission" "gemini_alias_events" {
  statement_id  = "AllowInvokeFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.worker.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.gemini_alias.arn
}
