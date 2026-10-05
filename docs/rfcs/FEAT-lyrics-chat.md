# FEAT-lyrics-chat: automatic translation with Work Cloud

- **Status**: draft
- **Owner**: site owner
- **Created**: 2026-10-05
- **Plan row**: docs/plan.md → FEAT-lyrics-chat
- **Decision**: the owner selected ChatGPT Work Cloud on 2026-10-05, superseding the local GPT plan-login executor. This record does not promote lifecycle status.

## Outcome

Preserve automatic processing of the existing AWS-produced PostgreSQL translation queue and the current viewer. Work Cloud is the selected execution destination. The queue, source revisions, claims and published results remain authoritative in the database. Neither a manual prompt for every song nor a separately billed OpenAI Platform API is part of the selected design.

The local GPT prototype is implemented and tested, but remains disabled and is not the selected rollout. Both retired Claude translation jobs remain disabled. Cloud integration is not implemented or enabled yet; local tests do not verify Cloud execution.

## Conversation policy

Proposed default: one independent conversation/context per bounded translation job, initially one track or one commentary source. Supply the fixed translation instructions, current source and output schema on every job. Do not accumulate unrelated songs in a permanent translation chat or create a chat per lyric line. A later small batch may group related sources only after measuring context size and failure recovery.

Persist job identity, attempts, source revision and results in the database rather than relying on conversation history. Retried delivery of the same event retains its event/idempotency identity; retrying a job must not bypass claim checks or the attempt ceiling. Do not require chat continuity for correctness. A fresh conversation does not reset subscription usage limits.

Keep conversation output to a short job summary after tool-based result submission. Successful conversations may be archived where supported; retain failures for diagnosis. Archiving organizes history and does not establish that model context was reset. Durable settings belong in the configured task/skill, not in incidental earlier chat messages.

## Trigger capability gate

Official MCP Events documentation supports Work on ChatGPT web and desktop with Cloud selected. It specifies delivery to the subscribed chat, potentially batched according to task settings. It does not establish a switch that creates a fresh conversation for every custom MCP event. Verify actual supported routing before promising independent event-triggered chats.

Official scheduled-task documentation distinguishes standalone runs starting from a saved prompt from runs returning to an existing chat. This is a possible fallback, not the selected trigger: periodic model wakeups may spend allowance even when the queue is empty, so assess that behavior before enabling polling.

The separately documented Workspace Agents trigger API provides conversation_key and Idempotency-Key. It is an alternative only if the owner's workspace supports that product and its API channel; ordinary Work Cloud access does not prove eligibility. Do not silently substitute this product or request a Platform API key.

Prefer a lightweight AWS dispatcher that checks eligible work without invoking a model and emits bounded events only when work exists. MCP event receipt is not proof of completed translation. A subscribed control chat and independent execution chats would be acceptable only after supported dispatch/routing is verified; do not assume nested chat creation is available to a Cloud task.

## Queue and usage controls

Preserve explicit requested lyrics, active album demand and matched pending Genius commentary. A trigger/model change alone does not reduce producer-created demand; do not silently broaden admission. Keep all eligible demand durable and preserve completed results, manual edits and unfinished historical work.

Reuse source fingerprints, ordered segment/gap validation, claim fencing, newer-request protection and live album-demand checks. No DB transaction may span model work. Publish only complete validated results; never accept a stale claim or changed source. Keep observed model provenance when exposed, and explicitly mark it unavailable otherwise rather than inventing it.

Start with one active job, a conservative daily admission budget of 10, and at most two attempts per source/version. An operational budget pauses consumption without deleting or truncating member scope. Use delayed bounded retry for temporary failures; refusal/cancellation stops the source. Plan/usage/authentication rejection must pause dispatch instead of draining the queue through repeated failures. Cloud-level retries and batching must not defeat database admission controls.

MCP subscriptions, callback secrets, delivery attempts and pending events need durable storage. Implement owner-scoped authentication, signed webhook verification, subscription expiry/unsubscribe, SSRF-safe callback delivery and stable event IDs. Result writes must not recursively trigger more translation events. Do not send arbitrary translation payloads into the existing generic SQS consumer without a matching handler.

## Delivery gates

1. Verify the owner's supported Work Cloud trigger and conversation-routing capabilities. Resolve fresh execution context without assuming an undocumented custom-event setting. Keep existing executors disabled throughout this check.
2. Finalize cloud contracts and the RFC implementation sequence after that gate. Implement authenticated queue claim/result tools, durable subscriptions/outbox and bounded AWS dispatch as required. Update API contracts, schema pins and infrastructure plans together where touched.
3. Validate idle/no-model behavior, duplicate events, stale claims, changed sources, withdrawn demand, partial output, retries, usage pauses and restart recovery. Local prototype tests are reusable evidence for queue rules only.
4. Connect the owner's Cloud integration through its supported authorization flow. Process one controlled queued job, verify the database and viewer, then confirm separate subsequent jobs receive the agreed context isolation before enabling broader consumption.

Do not claim cutover complete until an AWS-produced job is automatically processed in Work Cloud and displayed correctly. Account authorization or unsupported routing must be reported explicitly. Do not bypass a browser security-policy denial.

Rollback: pause Cloud dispatch/subscriptions and new claims; keep Claude and local GPT translation jobs disabled. Retain pending work, source data and completed results. Preserve unrelated Claude research/nightly jobs.

## Sources

- [MCP Events and subscribed chats](https://developers.openai.com/plugins/build/mcp-events)
- [Standalone and existing-chat scheduled tasks](https://learn.chatgpt.com/docs/automations)
- [Workspace Agents trigger runs](https://developers.openai.com/workspace-agents/trigger-runs)
- [Superseded local plan-login prototype](https://developers.openai.com/siwc/token-sharing-open-source)
