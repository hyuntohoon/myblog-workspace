# SQS Contract: Album Sync

**Queue**: `blogSQS` (prod) / `test-queue` (local/dev)  
**Region**: `ap-northeast-2`  
**Account**: `338183196042`  
**Type**: Standard queue (NOT FIFO)  
**DLQ**: `album-sync-dlq` — redrive `maxReceiveCount=3`, 14-day retention, CloudWatch-alarmed (observe-only, no auto-redrive). Visibility timeout: 720s (raised from 30s to clear the worker timeout, STAB-3, applied 2026-06-05).  
**Producer**: `myblog_music` (album sync, Format A/B — `app/clients/sqs_client.py`, Lambda: `musicApi`) + `myblog_backend` (job-control, Format C — `app/clients/sqs_client.py`, Lambda: `ratemymusic-api`) + workspace `scripts/research_poller.py` (Format C `genius_fetch` readiness nudge, boto3 from the owner's machine)  
**Consumer**: `myblog_worker` (`worker/handler.py`, Lambda: `blogWorkerLambda`)

---

## Message Formats

Three formats are accepted. The consumer handles all in the same handler — album-sync (A/B, from `myblog_music`) and job-control (C, from `myblog_backend`).

### Format A — Batch (preferred)

Sent only after an authenticated caller explicitly posts candidate album IDs to
`POST /api/music/sync-requests`. `GET /api/music/search/candidates` is a pure Spotify read and
never emits this message.
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

### Format C — Job-control messages (`myblog_backend` / worker self-chain)

Dispatched by the **backend** (not `myblog_music`) — and, for the lyrics rows, by the **worker
itself** — onto the same `blogSQS` queue. The user-facing endpoint only **enqueues** (202
Accepted) — per hard rule #9 the worker performs all Spotify I/O.
These carry a `job` key and **no** `album_ids`/`market` fields.

```json
{ "job": "spotify_library_sync" }
```

| `job` value | Producer | Endpoint | Worker action |
|---|---|---|---|
| `spotify_library_sync` | backend `SqsClient.send_library_sync` | `POST /api/buckets/spotify-library/sync` | mirror saved-albums Library (GET/PUT/DELETE `/me/albums`); writes gated on the worker's own `SPOTIFY_LIBRARY_WRITES_ENABLED` |
| `spotify_refresh` | backend `SqsClient.send_listening_refresh` | `POST /api/library/refresh-recent` | re-pull recently-played → `spotify_recent_tracks` (V14) |
| `lyrics_incremental` | worker self-chain `sqs_producer.enqueue_lyrics_incremental` — sent once per invocation after an album-sync record lands (worker #62); also send-able manually | — | run one bounded incremental LRCLIB lyrics pass now (near-real-time; the 15-min EventBridge cron is the safety net). Optional `limit`. The lyrics branch never re-chains (no feedback loop). |
| `lyrics_reassessment` | manual only | — | run one bounded reassessment pass over unresolved lyrics rows. Optional `limit`. With `album_id` (uuid string) the pass is album-scoped out of turn (the DATA-catalog-noise Step 4 expedite; optional `cooldown_sec` bounds a double-fire). |
| `genius_fetch` | workspace `research_poller.py` `_nudge_unready_albums` (readiness nudge, ≤1/album/5 min) — also send-able manually | — | run one bounded Genius annotation fetch over research-requested albums. Optional `limit`. With `album_id` (uuid string) the pass is scoped to that album — the research claim gate's collection path; duplicates are cheap (only still-missing tracks are selected, all writes upsert). |

The worker dispatches on the `job` key (`handler.py`) **before** the Format A/B branches and before the
unknown-format fallthrough — so these are recognized messages, not "unknown format".

---

## Producer Behaviour (`myblog_music`)

File: `app/clients/sqs_client.py::SqsClient.enqueue_album_sync`

1. Filters out empty strings from the input ID list.
2. Groups IDs into chunks of **20** (Spotify batch limit).
3. Sends chunks to SQS using `send_message_batch` with up to **10 entries per API call**.
4. The producer has a FIFO branch (`MessageGroupId = "album-sync"`, `MessageDeduplicationId` from `uuid5(NAMESPACE_URL, body + ":" + market)`) gated on `queue_name.endswith('.fifo')` — **dead in prod** (`blogSQS` is Standard). Prod relies on at-least-once delivery + an idempotent consumer (`ON CONFLICT`), NOT FIFO exactly-once/dedup.
5. A full batch returns `202 {"status":"accepted", ...}`. Any partial or total
   `send_message_batch` failure is raised to the route and returned as a safe
   `503 {"status":"failed","message":"Album sync request could not be accepted"}`; provider
   details and queue identifiers are never exposed in the HTTP response.

---

## Consumer Behaviour (`myblog_worker`)

File: `worker/handler.py::lambda_handler`

1. Reads `event["Records"]` (standard Lambda SQS event structure).
2. For each record, parses `record["body"]` as JSON.
3. Dispatches on the `job` key first (Format C: `spotify_library_sync`, `spotify_refresh`), then to `_process_batch` (Format A) or `_process_single` (Format B) based on key presence.
4. **Unrecognized** formats (no `job`, no `album_ids`/`spotify_album_id`) are **logged as warnings** and the record is considered successful (not retried). Recognized `job` keys are NOT treated as unknown.
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
| Unrecognized format (no `job`/`album_ids`/`spotify_album_id`) | N/A | Logs warning, record treated as success (no retry) — recognized `job` keys (Format C) excluded |
| Spotify API error | N/A | Record fails → added to `batchItemFailures` → SQS retries |
| DB write error | N/A | Record fails → added to `batchItemFailures` → SQS retries |
| `send_message_batch` partial failure | Raises; HTTP producer returns safe `503 failed` (some earlier messages may already be queued) | N/A |

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
