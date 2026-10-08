# FEAT-lyrics-chat: automatic translation with a local GPT worker

- **Status**: draft
- **Owner**: site owner
- **Created**: 2026-10-05
- **Plan row**: docs/plan.md → FEAT-lyrics-chat
- **Execution**: single-PR cutover (code + docs); activation follows the delivery gates below. This record does not promote lifecycle status.

## Decision record

| Date | Decision | Why |
|---|---|---|
| 2026-10-05 | Manual per-song Chat (owner-only MCP tools, backend #179) | First proposal. |
| 2026-10-05 | Owner corrected to **automatic** queue processing; local GPT worker built and installed disabled | Per-song manual prompts do not scale to the queue. |
| 2026-10-05 | Owner selected Work Cloud (MCP Events) | Not implemented; routing to fresh chats was unverified. |
| 2026-10-08 | Owner asked for translation through a **chat that leaves no history (temporary chat)**, then chose the **local GPT worker** | See below. |

**Why not a chat, 2026-10-08.** Any ChatGPT chat — temporary or not — can only reach our queue through a custom MCP app, and adding one requires ChatGPT *developer mode*. The owner's account is **ChatGPT Plus** (read from the plan claim of the local Codex login, no token printed), and the owner confirmed the settings screen offers no developer mode. OpenAI's help centre lists full (write-capable) custom MCP for Business/Enterprise/Edu only. Even where available, a temporary chat starts only when a person opens it, so it cannot consume the queue automatically. Nothing is deployed for chat: API Gateway has no MCP/chat route, there is no MCP Lambda and no Cognito client for it (checked 2026-10-08); backend #179 was closed unmerged.

**What the owner's actual goal maps to.** "No chat left behind" is met by the local worker by construction: it calls the Responses API with `store=false` through the owner's own ChatGPT plan sign-in, outside any chat UI, so no conversation is ever created. Wiring in Work Cloud is dropped.

## Model comparison (2026-10-08, owner-requested)

One song, the production lyrics prompt verbatim, production validator (JSON array, line count, index set): Tame Impala, "It Might Be Time" (41 non-gap lines) — chosen because production Claude Sonnet had refused it.

| Model | Result |
|---|---|
| Claude Sonnet (retired production engine) | **refused 3/3** (plus the production refusal: 4/4) |
| Claude Opus | pass 2/2 |
| Claude Haiku | pass; literal, some awkward lines |
| GPT-5.6-sol / -terra / -luna, GPT-5.5 | pass, each 1/1 |

GPT ran through the Codex CLI on the same ChatGPT Plus account (`--ephemeral`, read-only, empty cwd), **not** through this worker's sign-in path; the worker's model list comes from the signed-in account and may differ. One song, one judge (the agent), no control: this is a smoke-level comparison, not a benchmark. Not run: Fable 5.1 (needs usage credits), GLM (provider balance empty), GPT-6.x (rejected for ChatGPT-account Codex).

**Prompt alignment.** The comparison used the retired pollers' frozen 의역 prompt, but the worker had shipped a generic one-line English instruction. The worker now sends the same 의역 rules per kind (`INSTRUCTIONS` in `scripts/gpt_translation_store.py`), adapted to the `{i,text_ko}` schema; `scripts/tests/test_gpt_prompt_mirror.py` pins them to the Claude pollers' `PROMPT_HEADER`. `translator_version` stays `chatgpt/*-v1`: no GPT result has been stored under it yet.

## Outcome

Keep the AWS producers, durable PostgreSQL queues and viewer. Replace the local Claude executor with a dedicated local GPT consumer. The machine periodically checks the queue, claims one eligible source, closes the DB transaction, calls GPT with dedicated ChatGPT-plan OAuth credentials, then validates and publishes atomically. An empty queue causes no inference.

The official locally hosted Sign in with ChatGPT flow supports eligible Responses API requests with a user-authorized OAuth token. No Codex execution, ChatGPT browser automation, Codex credential reuse or paid API-key fallback. Account eligibility (including whether Plus is eligible) is established only by the owner's successful sign-in.

## Queue and controls

Retain explicit requested lyrics, active album demand and matched Genius pending commentary. Do not recreate a research-catalog sweep. Preserve unfinished Claude work/history and rebind active album demands to GPT work for the current source; reuse completed translations. One active inference at a time, 20-minute claims and source fingerprint checks, ordered segment/gap validation, newer request/manual edit protection, and actual selected model provenance (reserved work-result metadata stripped before viewer publication). Queue scans are bounded and continue by cursor so a stopped source cannot starve later requests.

Keep all eligible demand durable. A configurable daily admission budget pauses consumption until the next UTC day; it does not delete or truncate member scope. Default 10 until measured. Per source/version at most two attempts; refusal/cancellation stops immediately. Temporary failures use a delayed, bounded retry. Authentication revocation, unavailable plan usage and plan-limit errors trip a persistent consumer pause rather than trying the remaining queue. Partial/incomplete streams never publish.

## Authentication and inference

Fresh dedicated dynamic client, stable opaque host ID, loopback 127.0.0.1 callback, state/nonce/PKCE, verified ID-token signature/issuer/audience/expiry/nonce and returned plan-use scopes. Credentials in owner-only local files (0600 in a 0700 directory), refreshed without log disclosure. Never a token copied from Codex or a browser cookie.

List the signed-in account's eligible models and require an explicit selection. Send `store=false`, `stream=true`, text input, no tools. Accept success only at `response.completed`. Reject refusal, errors, incomplete output and malformed/misaligned segments. No automatic model fallback or SDK retry.

## Delivery gates

1. Tests: full `scripts/tests` suite against the canonical schema (Neon test branch). No real inference in tests.
2. Merge, then reinstall the runtime from merged `main` so the frozen manifest carries the aligned prompt. launchd job stays disabled.
3. Owner completes **Continue with ChatGPT** on the loopback setup page, reviews plan-use permission and selects a model. Verify sign-in, scopes and model list without spending inference.
4. One `--smoke` tick: one queued source → GPT → DB → authenticated viewer. Then an idle tick with no eligible source to confirm no inference. Only then set `enabled` and load the launchd job. Preserve every unrelated Claude research/nightly job.

Do not claim completion until the installed worker processes a queued item automatically and the viewer displays the validated result. If sign-in shows the Plus account is not eligible, stop and report — there is no API-key fallback.

Rollback: disable the GPT launchd job (or Stop on the setup page); keep both Claude translation jobs disabled; retain sources, pending demand, completed results and old work history. No DB migration or Terraform change.

## Sources

- [ChatGPT plan usage (Sign in with ChatGPT)](https://developers.openai.com/siwc/token-sharing-open-source)
- [Models and streamed inference](https://developers.openai.com/siwc/token-sharing-open-source/models-and-inference)
- [Developer mode and MCP apps in ChatGPT](https://help.openai.com/en/articles/12584461-developer-mode-and-mcp-apps-in-chatgpt)
- [Temporary Chat FAQ](https://help.openai.com/en/articles/8914046-temporary-chat-faq)
