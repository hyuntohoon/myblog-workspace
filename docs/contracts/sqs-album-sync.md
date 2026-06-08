# SQS Contract: Album Sync

**Queue**: `blogSQS` (prod) / `test-queue` (local/dev)  
**Region**: `ap-northeast-2`  
**Account**: `338183196042`  
**Type**: Standard queue (NOT FIFO)  
**DLQ**: `album-sync-dlq` — redrive `maxReceiveCount=3`, 14-day retention, CloudWatch-alarmed (observe-only, no auto-redrive). Visibility timeout: 720s (raised from 30s to clear the worker timeout, STAB-3, applied 2026-06-05).  
**Producer**: `myblog_music` (`app/clients/sqs_client.py`, Lambda: `musicApi`)  
**Consumer**: `myblog_worker` (`worker/handler.py`, Lambda: `blogWorkerLambda`)

---

## Message Formats

Two formats are accepted. The consumer handles both in the same handler.

### Format A — Batch (preferred)

Sent when `myblog_music` dispatches one or more albums from the `/candidates` flow.
Up to **20 album IDs per message** (Spotify `/albums?ids=` limit).

```json
{
  "album_ids": ["4aawyAB9vmqN3uQ7FjRGTy", "1ATL5GLyefJaxhQzSPVrLX"],
  "market":    "KR"
}
```

| Field | Type | Required | Constraints |
|---|---|---|---|
| `album_ids` | `string[]` | yes | 1–20 Spotify album IDs; empty arrays are silently skipped |
| `market` | `string` | no | ISO 3166-1 alpha-2 market code; defaults to `KR` if omitted |

### Format B — Single (legacy)

Retained for backward compatibility. Prefer Format A for new integrations.

```json
{
  "spotify_album_id": "4aawyAB9vmqN3uQ7FjRGTy",
  "market":           "KR"
}
```

| Field | Type | Required | Constraints |
|---|---|---|---|
| `spotify_album_id` | `string` | yes | Single Spotify album ID |
| `market` | `string` | no | Defaults to `KR` if omitted |

---

## Producer Behaviour (`myblog_music`)

File: `app/clients/sqs_client.py::SqsClient.enqueue_album_sync`

1. Filters out empty strings from the input ID list.
2. Groups IDs into chunks of **20** (Spotify batch limit).
3. Sends chunks to SQS using `send_message_batch` with up to **10 entries per API call**.
4. The producer has a FIFO branch (`MessageGroupId = "album-sync"`, `MessageDeduplicationId` from `uuid5(NAMESPACE_URL, body + ":" + market)`) gated on `queue_name.endswith('.fifo')` — **dead in prod** (`blogSQS` is Standard). Prod relies on at-least-once delivery + an idempotent consumer (`ON CONFLICT`), NOT FIFO exactly-once/dedup.
5. Partial `send_message_batch` failures are **logged as warnings** — no retry, no exception raised.

---

## Consumer Behaviour (`myblog_worker`)

File: `worker/handler.py::lambda_handler`

1. Reads `event["Records"]` (standard Lambda SQS event structure).
2. For each record, parses `record["body"]` as JSON.
3. Dispatches to `_process_batch` (Format A) or `_process_single` (Format B) based on key presence.
4. Unknown formats are **logged as warnings** and the record is considered successful (not retried).
5. Per-record exceptions are caught; the failing record's `messageId` is collected.
6. Returns `{"batchItemFailures": [{"itemIdentifier": messageId}, ...]}` — SQS retries only failed records.

### DRY_RUN mode

When `DRY_RUN=true` (worker config), the handler fetches album data from Spotify but **does not write to the database**. Useful for smoke-testing the queue path without side effects.

---

## Lambda SQS Event Envelope (reference)

The worker receives the standard AWS Lambda SQS event. Each record follows this shape:

```json
{
  "Records": [
    {
      "messageId": "059f36b4-87a3-44ab-83d2-661975830a7d",
      "receiptHandle": "...",
      "body": "{\"album_ids\":[\"4aawyAB9vmqN3uQ7FjRGTy\"],\"market\":\"KR\"}",
      "attributes": {
        "ApproximateReceiveCount": "1",
        "SentTimestamp": "1545082650636",
        "SenderId": "...",
        "ApproximateFirstReceiveTimestamp": "1545082650649"
      },
      "messageAttributes": {},
      "md5OfBody": "...",
      "eventSource": "aws:sqs",
      "eventSourceARN": "arn:aws:sqs:ap-northeast-2:338183196042:blogSQS",
      "awsRegion": "ap-northeast-2"
    }
  ]
}
```

---

## Error Handling Summary

| Scenario | Producer | Consumer |
|---|---|---|
| Empty `album_ids` list | Skips silently, nothing sent | `_process_batch` skips with log |
| Unknown message format | N/A | Logs warning, record treated as success (no retry) |
| Spotify API error | N/A | Record fails → added to `batchItemFailures` → SQS retries |
| DB write error | N/A | Record fails → added to `batchItemFailures` → SQS retries |
| `send_message_batch` partial failure | Logs warning | N/A |

---

## Local Development

Use LocalStack to emulate SQS locally.

```bash
# Start LocalStack
docker run -p 4566:4566 localstack/localstack

# Create queue
aws --endpoint-url=http://localhost:4566 sqs create-queue --queue-name test-queue

# Send a test message
aws --endpoint-url=http://localhost:4566 sqs send-message \
  --queue-url http://localhost:4566/000000000000/test-queue \
  --message-body '{"album_ids":["4aawyAB9vmqN3uQ7FjRGTy"],"market":"KR"}'
```

**Required env vars** (`.env` in each service):

| Service | Var | Local value |
|---|---|---|
| `myblog_music` | `LOCALSTACK_ENDPOINT` | `http://localhost:4566` |
| `myblog_music` | `AWS_ACCOUNT_ID` | `000000000000` |
| `myblog_music` | `QUEUE_NAME` | `test-queue` |
| `myblog_worker` | `LOCALSTACK_ENDPOINT` | `http://localhost:4566` |
| `myblog_worker` | `SQS_QUEUE_URL` | `http://localhost:4566/000000000000/test-queue` |
| `myblog_worker` | `DRY_RUN` | `false` (or `true` for read-only smoke test) |

---

## Change Policy

Any change to message field names, types, or the addition of required fields is a **breaking contract change** and must:

1. Be discussed and decided in `docs/decisions/`.
2. Be deployed to the consumer (`myblog_worker`) before or simultaneously with the producer (`myblog_music`).
3. Maintain backward compatibility for at least one deploy cycle (add fields as optional first).
