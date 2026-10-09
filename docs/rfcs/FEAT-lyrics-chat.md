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
| 2026-10-09 | Owner signed in, chose `gpt-5.6-sol` and a daily budget of **100**; worker enabled | Delivery record below. |

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

**Second pass on the worker's real path (2026-10-09, after sign-in).** The signed-in account lists `gpt-6.1-sol`, `gpt-6-astra`, `gpt-6-sol`, `gpt-6-luna`, `gpt-5.6-sol`, `gpt-5.6-terra`, `gpt-5.6-luna`. The same song through `GPTPlanClient.translate` with the aligned 의역 prompt, nothing written to the DB: `gpt-6.1-sol` aligned 41/41 in 27 s, `gpt-5.6-sol` aligned 41/41 in 22 s, no refusal. Quality was near-identical line by line (6.1 better on "won't recover", 5.6 better on "roll their eyes" and on carrying "Don't they know? / Nothin' lasts forever" across the two lines). `gpt-5.6-sol` was chosen: equal quality, validated on both paths, faster.

The first pass's GPT runs went through the Codex CLI on the same ChatGPT Plus account (`--ephemeral`, read-only, empty cwd), **not** through this worker's sign-in path; the worker's model list comes from the signed-in account and may differ. One song, one judge (the agent), no control: this is a smoke-level comparison, not a benchmark. Not run: Fable 5.1 (needs usage credits), GLM (provider balance empty), GPT-6.x (rejected for ChatGPT-account Codex).

**Prompt alignment.** The comparison used the retired pollers' frozen 의역 prompt, but the worker had shipped a generic one-line English instruction. The worker now sends the same 의역 rules per kind (`INSTRUCTIONS` in `scripts/gpt_translation_store.py`), adapted to the `{i,text_ko}` schema; `scripts/tests/test_gpt_prompt_mirror.py` pins them to the Claude pollers' `PROMPT_HEADER`. `translator_version` stays `chatgpt/*-v1`: no GPT result has been stored under it yet.

## Outcome

Keep the AWS producers, durable PostgreSQL queues and viewer. Replace the local Claude executor with a dedicated local GPT consumer. The machine periodically checks the queue, claims one eligible source, closes the DB transaction, calls GPT with dedicated ChatGPT-plan OAuth credentials, then validates and publishes atomically. An empty queue causes no inference.

The official locally hosted Sign in with ChatGPT flow supports eligible Responses API requests with a user-authorized OAuth token. No Codex execution, ChatGPT browser automation, Codex credential reuse or paid API-key fallback. Account eligibility (including whether Plus is eligible) is established only by the owner's successful sign-in.

## Architecture

```
AWS (unchanged)                      PostgreSQL (Neon, unchanged schema)          Owner's Mac (new)
───────────────                      ───────────────────────────────────          ──────────────────────────────────────────
viewer POST translation-request ──▶  track_lyrics_translations  status=requested
worker Step 4/5 album demand    ──▶  lyrics_album_jobs / _tracks (V57/V58)    ◀── launchd com.myblog.gpt-translate-poller
Genius matcher                  ──▶  track_genius_annotations  pending              every 60 s → gpt_queue_worker.py (one tick)
                                     lyrics_translation_work   (claims, leases)        1. scan ≤30 candidates by cursor (no model call)
                                                                                     2. bind album demand, claim one source (short txn)
                                                                                     3. close DB → Responses API, store=false, stream
                                                                                        (owner's ChatGPT plan OAuth token)
viewer GET /api/lyrics/{id}     ◀──  track_lyrics_translations  status=done   ◀── 4. validate {i,text_ko} → publish (fresh short txn)
```

- **One tick = at most one inference.** An empty queue makes no model call. One active lease across all GPT work (`lyrics_translation_work.status='running'`).
- **Runtime is frozen, not the checkout.** `scripts/install_gpt_translation_worker.py` copies the worker scripts plus the backend `app/` and shared-db `src/` at explicit revisions into `~/.local/share/myblog-gpt/runtime`, with its own `.venv` and a `manifest.json` (revisions + script SHA-256). Changing code on `main` changes nothing until the installer is rerun — and it refuses while `enabled` is true (Stop first).
- **State directory** `~/.local/share/myblog-gpt/` (0700; files 0600): `settings.json` (`enabled`, `model`, `daily_cap`, `active`, `pause_reason`), one credential file per signed-in account, `host.json`, `scan.json` (cursor), `status.json` (last outcome), `worker.log`, and `worker.lock` / `control.lock`.
- **Owner controls** run from the loopback setup page (`runtime/.venv/bin/python runtime/scripts/gpt_worker_setup.py`, prints `http://127.0.0.1:<random port>`): sign in, list models, save model + daily budget, **Stop**. Saving never enables background work; enabling is a separate step (gate 4).
- **Pauses are persistent.** Plan/auth/usage rejection writes `pause_reason` and `enabled=false`; the next tick does nothing until sign-in + save + re-enable.
- **What reaches OpenAI:** the source segments and the instructions only. No tools, no project files, no chat; `store=false`, so nothing appears in ChatGPT history.
- **Provenance:** `track_lyrics_translations.model` holds the model the response reported (`gpt-5.6-sol`); `translator_version` is `chatgpt/lyrics-ko-v1` / `chatgpt/genius-ko-v1`.

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

## Delivery record

| Gate | Result | Evidence |
|---|---|---|
| 1 Tests | ✅ 2026-10-08 | ws #1037: `scripts/tests` 239 passed / 0 skipped against the Neon test branch; prompt-mirror test mutation-checked; `security-review` no findings. |
| 2 Merge + reinstall | ✅ 2026-10-08 | #1037 merged `178fa9f`; runtime reinstalled, launchd job installed disabled. |
| 3 Sign-in | ✅ 2026-10-09, after one fix | The first three owner sign-ins failed after a successful token exchange. A diagnostic run (exception class + library message only) showed `JWTClaimsError: No access_token provided to compare against at_hash claim` — OpenAI ID tokens carry `at_hash`, and the fixtures did not. Fixed in **ws #1038** (`fe616f6`; old code fails 7 of the updated tests; `security_reviewer` no findings). Fourth sign-in succeeded; model list read without inference. |
| 4 Smoke | ✅ 2026-10-09 | `--smoke` → `saved`: David Bowie, "Sons of the Silent Age" (album demand), 31 segments, `model=gpt-5.6-sol`, 48 s for the whole tick. Authenticated `GET /api/lyrics/3O85NMbjKkbcCi44UAwOx4` with the smoke user → HTTP 200, `translation.status=done`, 31/31 segments with `text_ko`. |
| Enable | ✅ 2026-10-09 15:36 KST | `enabled=true`, launchd bootstrapped (`run interval = 60 seconds`). **First scheduled tick → `saved`** (David Bowie, "V-2 Schneider", `gpt-5.6-sol`), exit 0. |

**Not done, and why.** The idle tick (gate 4's "no eligible source → no inference") was not run in production: the queue was not empty (12 Genius annotations pending plus album demand), and emptying it to test idleness is not a reason to spend. The behaviour is covered by `test_gpt_queue_worker.py`. The viewer was checked through its API, not in a browser (the Chrome extension was not connected).

**Open — observe, no decision needed:**
- **Plan usage.** Budget is 100 admissions per UTC day (owner's choice at save). Whether this draws on the same Plus allowance as ChatGPT chat messages is unverified; read `chatgpt.com/settings/usage` after a few days. A plan-limit rejection pauses the worker by design (`pause_reason` in `settings.json`).
- **Refusal rate under GPT.** Unmeasured. Each refusal stops that source; count `lyrics_translation_work.last_reason='refused'` for `chatgpt/%` after the first full day.
- **The Mac must be awake.** A sleeping or switched-off machine stops consumption; the queue is durable and resumes.

Rollback: **Stop** on the setup page, or `launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/com.myblog.gpt-translate-poller.plist` (an in-flight tick may finish); keep both Claude translation jobs disabled; retain sources, pending demand, completed results and old work history. No DB migration or Terraform change.

## Sources

- [ChatGPT plan usage (Sign in with ChatGPT)](https://developers.openai.com/siwc/token-sharing-open-source)
- [Models and streamed inference](https://developers.openai.com/siwc/token-sharing-open-source/models-and-inference)
- [Developer mode and MCP apps in ChatGPT](https://help.openai.com/en/articles/12584461-developer-mode-and-mcp-apps-in-chatgpt)
- [Temporary Chat FAQ](https://help.openai.com/en/articles/8914046-temporary-chat-faq)
