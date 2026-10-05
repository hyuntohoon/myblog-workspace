# FEAT-lyrics-chat: automatic GPT translation queue consumer

- **Status**: draft
- **Owner**: site owner
- **Created**: 2026-10-05
- **Plan row**: docs/plan.md → FEAT-lyrics-chat
- **Execution**: single-PR cutover; user explicitly corrected the manual-Chat proposal to preserve automatic queue processing. This record does not promote lifecycle status.

## Outcome

Keep the existing AWS producers, durable PostgreSQL queues and viewer. Replace the local Claude executor with a dedicated local GPT consumer. No per-song Chat prompt is required. The machine periodically checks the queue, claims one eligible source, closes the DB transaction, calls GPT with its dedicated ChatGPT-plan OAuth credentials, then validates and publishes atomically. An empty queue causes no inference.

The official locally hosted OSS Sign in with ChatGPT flow supports eligible public Responses API requests with a user-authorized OAuth token. No Codex execution, Work Cloud subscription, ChatGPT browser automation, existing Codex credential reuse or paid API-key fallback. It is a local application using ChatGPT plan permission, not a normal Chat conversation receiving a webhook. Account eligibility and actual usage permissions require successful owner sign-in.

## Queue and controls

Retain explicit requested lyrics, active album demand and matched Genius pending commentary. Do not recreate a research-catalog sweep. Preserve unfinished Claude work/history and rebind active album demands to GPT work for the current source; reuse completed translations. One active inference at a time, existing 20-minute claims and source fingerprint checks, ordered segment/gap validation, newer request/manual edit protection, and actual selected model provenance (reserved work-result metadata stripped before viewer publication). Queue scans are bounded and continue by cursor so a stopped source cannot starve later requests.

Keep all eligible demand durable. A configurable operational daily admission budget pauses consumption until the next UTC day; it does not delete/truncate member scope. Default 10 until measured. Per source/version at most two attempts; refusal/cancellation stops immediately. Temporary failures use a delayed, bounded retry. Authentication revocation, unavailable plan usage and plan-limit errors trip a persistent consumer pause rather than trying the remaining queue. Partial/incomplete streams never publish. Stream timeout/byte bounds bound local work, not exact billed tokens. Sign-in UI exposes ChatGPT usage settings and requires confirmation before automatic consumption.

## Authentication and inference

Use a fresh dedicated dynamic client, stable opaque host ID, loopback 127.0.0.1 callback, state/nonce/PKCE, verified ID-token signature/issuer/audience/expiry/nonce and returned plan-use scopes. Store credentials in owner-only local files and refresh without log disclosure. Returning login must retain the verified account/client identity. Never use a token copied from Codex or a browser cookie.

List the signed-in account's eligible models and require an explicit selection. Send store=false, stream=true, text input, no tools and no unsupported tuning/background fields. Accept success only at response.completed. Reject refusal, errors, incomplete output and malformed/misaligned segments. No automatic model fallback or SDK retry.

## Delivery gates

1. Implement and test the local OAuth/inference adapter, queue bridge and retirement guards; run the complete script suite and PostgreSQL regressions against the pinned canonical schema. No real inference in tests.
2. Supersede the manual-only draft backend/MCP deployment and remove its unnecessary infra changes from the workspace PR. No AWS Terraform apply is needed for this local-executor cutover.
3. Install a dedicated runtime with the new launchd job disabled. The owner completes Continue with ChatGPT, reviews plan-use permission and selects a model. Verify sign-in/scopes/models without spending inference.
4. Enable only after tests and sign-in pass; perform one controlled queue-to-GPT-to-viewer smoke, verify idle/no-call and bounded failure behavior, and then enable periodic consumption. Preserve every unrelated Claude research/nightly job.

Do not claim completion until the installed worker processes a requested queue item automatically and the viewer displays the validated result. Browser security-policy denial must not be bypassed; user authentication is an explicit remaining gate if access is unavailable.

Rollback: disable the dedicated GPT job; keep both Claude translation jobs disabled; retain sources, pending demand, completed results and old work history. No DB rollback migration or Terraform change.

## Sources

- [ChatGPT plan usage](https://developers.openai.com/siwc/token-sharing-open-source)
- [OAuth registration](https://developers.openai.com/siwc/token-sharing-open-source/sign-in)
- [Models and streamed inference](https://developers.openai.com/siwc/token-sharing-open-source/models-and-inference)
- [Preview limitations](https://developers.openai.com/siwc/token-sharing-open-source/preview-limitations)
- [Usage controls](https://developers.openai.com/siwc/ui-ux-guidelines)

Work Cloud MCP Events remains an alternative if execution must live in ChatGPT tasks; it adds subscriptions, callbacks and dispatch state. It is not required for the selected local GPT executor.
