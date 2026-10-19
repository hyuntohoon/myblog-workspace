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
Genius matcher                  ──▶  track_genius_annotations  pending              every 60 s → gpt_queue_worker.py (one run, 3 slots)
                                     lyrics_translation_work   (claims, leases)        1. scan ≤30 candidates by cursor (no model call)
                                                                                     2. bind album demand, claim a source (short txn)
                                                                                     3. close DB → Responses API, store=false, stream
                                                                                        (owner's ChatGPT plan OAuth token)
viewer GET /api/lyrics/{id}     ◀──  track_lyrics_translations  status=done   ◀── 4. validate {i,text_ko} → publish (fresh short txn)
```

- **One run = up to three concurrent inferences** (since 2026-10-12; see _Throughput and usage_). Each slot repeats one-item ticks; an empty queue makes no model call. At most three live leases across all GPT work (`lyrics_translation_work.status='running'`). A run that is still going holds `worker.lock`, so the next launchd start exits at once.
- **Runtime is frozen, not the checkout.** `scripts/install_gpt_translation_worker.py` copies the worker scripts plus the backend `app/` and shared-db `src/` at explicit revisions into `~/.local/share/myblog-gpt/runtime`, with its own `.venv` and a `manifest.json` (revisions + script SHA-256). Changing code on `main` changes nothing until the installer is rerun — and it refuses while `enabled` is true (Stop first).
- **State directory** `~/.local/share/myblog-gpt/` (0700; files 0600): `settings.json` (`enabled`, `model`, `daily_cap`, `active`, `pause_reason`, and during a plan-limit wait `resume_at` / `limit_hits`), one credential file per signed-in account, `host.json`, `scan.json` (cursor), `status.json` (outcome counts of the last run), `usage.json` (token totals per UTC day), `fallback-usage.json` / `fallback-skip.json` (Claude fallback, 2026-10-18), `claude-cwd/` (empty working directory for the CLI), `worker.log`, and `worker.lock` / `control.lock` / `usage.lock`.
- **Owner controls** run from the loopback setup page (`runtime/.venv/bin/python runtime/scripts/gpt_worker_setup.py`, prints `http://127.0.0.1:<random port>`): sign in, list models, save model + daily budget, **Stop**. Saving never enables background work; enabling is a separate step (gate 4).
- **Pauses are persistent; usage limits wait.** Plan/auth rejection writes `pause_reason` and `enabled=false`; the next tick does nothing until sign-in + save + re-enable. A plan usage limit waits one hour and probes again, indefinitely; it is never a persistent pause (changed 2026-10-18, see _Usage-limit fallback_). While the wait lasts, an enabled Claude fallback keeps the queue moving.
- **What reaches OpenAI:** the source segments and the instructions only. No tools, no project files, no chat; `store=false`, so nothing appears in ChatGPT history.
- **Provenance:** `track_lyrics_translations.model` holds the model the response reported (`gpt-5.6-sol`); `translator_version` is `chatgpt/lyrics-ko-v1` / `chatgpt/genius-ko-v1`.

## Queue and controls

Retain explicit requested lyrics, active album demand and matched Genius pending commentary. Do not recreate a research-catalog sweep. Preserve unfinished Claude work/history and rebind active album demands to GPT work for the current source; reuse completed translations. At most three concurrent inferences (originally one; changed 2026-10-12), 20-minute claims and source fingerprint checks, ordered segment/gap validation, newer request/manual edit protection, and actual selected model provenance (reserved work-result metadata stripped before viewer publication). Queue scans are bounded and continue by cursor so a stopped source cannot starve later requests.

Keep all eligible demand durable. A configurable daily admission budget pauses consumption until the next UTC day; it does not delete or truncate member scope. Default 10 until measured. Per source/version at most two attempts; refusal/cancellation stops immediately. Temporary failures use a delayed, bounded retry (since 2026-10-17: four attempts, backing off 10 min / 1 h / 6 h — FEAT-automation-admin OQ3). Authentication revocation and unavailable plan usage trip a persistent consumer pause rather than trying the remaining queue. A plan usage limit waits and resumes (_Throughput and usage_). Partial/incomplete streams never publish.

## Throughput and usage (2026-10-12)

Owner decisions, 2026-10-12: budget **300 per UTC day** (set in `settings.json`, not code), **three concurrent inferences**, **resume by itself after a plan usage limit**, and **record token usage** so it can be compared with `chatgpt.com/settings/usage`.

**Why.** Each tick ran one inference: p50 27 s, p90 42 s. Ticks started every 60 s, so the gap between two saves had a p50 of 90 s, and 100 items took about 2.5 h. At 300/day that would be about 7.5 h. With three streams in flight and no wait between items, 300 take about an hour.

**Concurrency.**
- `GPTTranslationStore.max_running = 3` replaces the single-lease rule. Before, any live `running` lease refused a claim. Now a claim is refused only when three are live. A lease whose time has run out frees its slot.
- **The budget and slot checks were already free of races, and stay that way.** `prepare` takes `pg_advisory_xact_lock('myblog-gpt-translation-admission')` before it reads `sum(attempts)` and the live-lease count. It keeps the lock until the claim commits. Two claimers cannot both pass the last budget unit or the last slot. A test widens the window between the read and the claim with a sleep. With the lock removed, that test fails.
- `QueueWorker.run()` starts `PARALLEL = 3` slots. Each slot repeats `tick()` until any slot reaches a final outcome: `idle`, `scan_wrap`, `daily_budget`, `owner_paused`, `usage_limit_wait` or `disabled`. Then every slot stops after the item it holds. One run therefore makes at most one pass over the queue; without the shared stop, a wrap would let the other two slots rescan it from the start. A slot that raises also stops the others. A thread lock serializes the scan cursor and claims. Claims take milliseconds against a 27 s inference, so claiming one at a time costs nothing. The claim `UPDATE` still guarantees that two slots never get the same source.
- Session shape is unchanged for each slot: fetch → close → stream → fresh short write session. A test asserts that the pool has no connection checked out while inference runs.
- `--smoke` still runs exactly one item.
- **A run can last about an hour, so stopping and saving behave differently.** Before each tick a slot reads `enabled` again, and before each claim and each stream it reads `pause_reason`. **Stop** on the setup page, or setting `enabled=false` in `settings.json`, therefore ends the run once the in-flight streams finish (at most 3, each bounded by the 300 s deadline). **Save** on the setup page still needs `worker.lock`, so it fails while a run is going. Stop first, wait for the run to end, then save. The same applies to reinstalling.
- `PlanAccount.credentials()` refreshes tokens under `account.lock`, which is an `flock`. Measured: it serializes threads within one process (peak 1 holder of 3), so concurrent slots cannot reuse one refresh token.

**Plan usage limit → wait, resume, then stop.** _(The stop was removed on 2026-10-18 — see _Usage-limit fallback_. Kept as the 10-12 record.)_
- A plan usage limit is either HTTP 429 or the code `subscription_sharing_usage_limit_exceeded`. The client marks it `limit`. The worker writes `resume_at = now + 3600` and `limit_hits += 1` under `control.lock`. Scheduled starts before `resume_at` exit before any DB access.
- **The third consecutive limit** sets `enabled=false` and `pause_reason`, as every limit did before this change.
- A completed inference after the wait clears the streak.
- If three streams are rejected by the same event, it counts once: any limit while `resume_at` is still in the future is not counted. A stream that started before the event and succeeds during the wait does not cancel the wait.
- 401/403, eligibility, scope and sign-in failures still stop immediately. A 429 that carries one of those codes also stops; only the usage-limit code resumes.
- **A limit rejection returns the source's attempt** (`fail(..., refund=True)`, which also gives back the daily budget unit). The source stays `retryable_error`. Before this change a limit used up one of the two attempts, which was harmless only because a person restarted the worker. With automatic resume, two limits on the same small queue would have stopped a member's request permanently.
- **Only the owner's own Stop, or a model change, cancels a source that is claimed but not yet streamed** (`user_cancelled`, which is terminal). Two other things can stop a slot between its claim and its stream: a sibling's plan stop, or a limit wait. In both cases the claim is released as `claim_released`, the attempt is returned, and the source can be retried at once.
- The third limit in a row also clears `limit_hits`, so re-enabling starts a fresh streak.

**Usage.**
- Each `response.completed` returns `usage`: input, cached input, output and reasoning tokens. A missing or malformed count is recorded as 0.
- The worker logs one line per request (model and counts only) and adds the counts to `usage.json` as `{ "YYYY-MM-DD" (UTC): {requests, input_tokens, cached_input_tokens, output_tokens, reasoning_tokens} }`, under `usage.lock`.
- A failure to record usage, or to reset the limit streak, never fails the item.
- Requests that end without `response.completed` (errors, limits) are not counted, because they have no usage to report.
- No API reads the plan usage itself: `/v1/usage` and `/v1/me` return 401 with this token. These totals are the only machine-side record. Compare them with the settings page by hand.

**Plan-usage reading (owner Chrome, 2026-10-12 06:10 UTC).**
- Plan limits are shared by Codex, Work and apps. **Chat conversations are not included**, so the worker does not use up the owner's chat allowance.
- Only a weekly bar is shown, with 89% left; there is no 5-hour bar.
- Estimate: about **3% of the weekly allowance per 100 translations**. The prior week's "Unknown" 5.8% ≈ ~197 worker rows; the upper bound is 11%. At 300/day that is about 9% per day, so the weekly allowance may run out in about 10 days of full budget. The wait-and-resume path, and then the third-limit stop, are what bound that.
- App limits show four "MyBlog GPT translation worker" rows, one per sign-in attempt on 10-09. Whether to tidy them is the owner's account setting.

## Usage-limit fallback (2026-10-18)

**Owner request (2026-10-18, in session):** when the GPT plan hits its usage limit, the work must keep going, and resume on its own. This overrides "no automatic model fallback" for the usage-limit case only, and the 10-05 retirement of Claude translation for that case only.

**What happened.** On 2026-10-17 the ChatGPT account hit its usage limit (09:00, 10:00, 11:01 KST). The third limit in a row set `enabled=false`, and nothing restarted the worker. A probe on 2026-10-18 02:18 KST was still rejected: the Responses stream returns `200`, then `error` / `response.failed` with `subscription_sharing_usage_limit_exceeded`. The body carries **no reset time**. Codex on the same account reports a reset at 2026-10-22 20:08 KST. So the queue would have stopped for about five days, and only a person could restart it.

**Change** (scripts only — no DB migration and no service deploy; the frozen runtime is reinstalled):
- **A usage limit never stops the worker.** Each limit event writes `resume_at = now + 3600` and counts `limit_hits`, then GPT is probed again. A rejected probe returns its attempt (unchanged), so hourly probing costs nothing. Plan/auth rejections still stop persistently. A limit that a sibling stream reports after the worker was stopped no longer re-arms `resume_at` / `limit_hits` (a stale state was seen in `settings.json` on 10-17).
- **Claude fallback** (`scripts/claude_fallback_client.py`), off unless `settings.json` has `fallback: {enabled: true, model, daily_cap}` (defaults: off, `opus`, 50). While `resume_at` is in the future, a start runs the fallback instead of exiting:
  - **One slot.** The shared subscription guard (`myblog_shared_db.llm.subscription_guard.coordinated_call`) serializes Claude calls across every local job, and cools all of them down for 15 min after a recognised throttle.
  - **Same claim, prompt and validation as GPT.** The same `INSTRUCTIONS` go in `--system-prompt`, and the `{i,text}` array goes on stdin. The result must be a JSON array that passes the same `_shape` and store validation. Rows publish under the same `translator_version` (`chatgpt/*-v1` denotes the prompt and schema). The `model` column records the Claude model (`claude-opus-5-5`).
  - **Isolation.** `claude -p --safe-mode --tools "" --strict-mcp-config --setting-sources "" --no-session-persistence --output-format json`, run from an empty `claude-cwd/`, by absolute path (`~/.local/bin/claude`; launchd's `PATH` does not include it). Lyrics text can reach the model and nothing else. No result text, stderr or provider message is logged or kept in an error.
  - **Attempts belong to GPT.** Every fallback failure releases the claim as `claim_released` with the attempt refunded. A source on which the model ran and failed (prose refusal, bad shape, timeout) is written to `fallback-skip.json`. The fallback skips it until a GPT completion ends the wait, and that completion clears the file. A throttle or cooldown ends the run and skips nothing.
  - **Budget.** A fallback success is an attempt like any other, so it counts toward the shared daily admission budget (300). Calls that ran — success or failure — also count toward `fallback.daily_cap`, tracked in `fallback-usage.json`.
  - **The wait is GPT's.** A Claude success does not clear `resume_at` / `limit_hits`. When `resume_at` passes, the fallback run stops (`gpt_available`), and the next start probes GPT with three slots.
  - **A claim cannot outlive its lease.** If waiting for the guard leaves less than 420 s (300 s CLI timeout + 120 s margin) of the 20-minute lease, the call is not dispatched (`lease_too_short`, refunded).
  - **Owner controls still apply.** Stop (`pause_reason`) and the admin page's site pause are checked before every fallback claim and call. The heartbeat `details` gain `engine` (`gpt` | `claude_fallback`) and `fallback` (switch, model, cap, today's counts).
- **Model choice.** Opus, from the 2026-10-08 comparison: Sonnet refused the test song 4/4, Opus passed 2/2, and Haiku passed but was literal. The cap of 50 a day is a starting value. The owner's Claude subscription is also used by interactive sessions, which the guard does not see.

**Observation, 2026-10-19 — the fallback has not run yet.** Read from the worker's local state and `worker.log` at 22:50 KST.
- **The limit lifted before the fallback could matter.** The last limit event was 2026-10-18 04:20 KST. When the changed worker was installed and re-enabled (16:39 KST), the first GPT probe succeeded. That is about four days before the reset Codex reported (10-22 20:08 KST), so Codex's reset time is not a reliable predictor for this API.
- **Claude fallback calls: 0.** No limit event has occurred since the change, so `resume_at` was never set. `fallback-usage.json` was never created, and `fallback-skip.json` is `{}`. The refusal rate is therefore unmeasured (denominator 0), not zero.
- **GPT since recovery:** 10-18 UTC 162 saved, 14 `invalid_output` (of 176 attempts, 8%); 10-19 UTC 300 saved of 300 attempts. On both days the queue hit the 300/day admission budget, so throughput is budget-bound, not limit-bound.
- **Still open:** the fallback's refusal rate and Claude usage. They are measured at the next plan usage-limit event, from `fallback-usage.json`, `fallback-skip.json` and the heartbeat `fallback` counts.

## Authentication and inference

Fresh dedicated dynamic client, stable opaque host ID, loopback 127.0.0.1 callback, state/nonce/PKCE, verified ID-token signature/issuer/audience/expiry/nonce and returned plan-use scopes. Credentials in owner-only local files (0600 in a 0700 directory), refreshed without log disclosure. Never a token copied from Codex or a browser cookie.

List the signed-in account's eligible models and require an explicit selection. Send `store=false`, `stream=true`, text input, no tools. Accept success only at `response.completed`. Reject refusal, errors, incomplete output and malformed/misaligned segments. No automatic model fallback or SDK retry — except the owner-enabled Claude fallback during a plan usage-limit wait (2026-10-18, _Usage-limit fallback_).

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

**First days measured (2026-10-11, read at 08:02 UTC).** Sources: production `lyrics_translation_work` (read-only) and `~/.local/share/myblog-gpt/worker.log` (local times converted to UTC). Enabled 2026-10-09 06:36 UTC, so 10-09 is a partial day; 10-10 is the first full UTC day; 10-11 is partial up to the read.

| UTC day | Inferences (HTTP 200) | Saved (`done`) | Not saved | Budget exhausted at | Ticks after exhaustion |
|---|---|---|---|---|---|
| 10-09 (from 06:36) | 100 (99 logged + the `--smoke` tick, which ran before `worker.log` began) | 99 | 1 `output_limit` | 09:18 | 734, no inference |
| 10-10 | 99 | 97 | 1 `output_limit` (2nd attempt, same row), 1 `temporary_error` | 02:33 | 1,145, no inference |
| 10-11 (to 08:02) | 100 | 100 | 0 | 02:31 | 288, no inference |

- **Refusal rate: 0 of 298 attempted rows.** Denominator = `chatgpt/%` rows that left `ready` (296 `done` + 2 `retryable_error`). Neither refusal path appears: no `refused` (structured refusal event) and no `invalid_output` (prose instead of a JSON array). The second path matters. The control is the retired engine on the same table: `claude.sonnet/v2` also shows **0** `refused`, yet **199 of 2,247** of its rows end in `engine_validation: no JSON array in output: 이 가사는 저작권이 있…`. It refused in prose, so counting `last_reason='refused'` alone would have reported "0" for Claude too.
- **The two failures are not refusals.** "WILSHIRE" hit `output_limit` on both attempts and is now terminal (`attempts=2`). This is a length limit, not a content limit. "Diver" had one `temporary_error`; it is due again and will be retried when the scan cursor wraps around to it.
- **Budget behaviour.** The 100-per-UTC-day budget ran out about 2.5 h into every full day. After that the worker kept ticking every 60 s, made no request to `api.openai.com`, and resumed at 00:00 UTC. No `pause_reason`, no ERROR line, no sign-in failure (8 token refreshes, all 200).
- **Backlog, not inflow, sets the pace.** 509 `chatgpt/%` rows exist: 508 seeded on 10-09 and **1** new on 10-10. 211 are still `ready`. At 100/day the queue should empty around 10-13 UTC; after that the worker should reach its first real idle tick in production (gate 4's unrun check).

**Open — observe, no decision needed:**
- **Plan usage.** Budget is 100 admissions per UTC day (owner's choice at save). Whether this draws on the same Plus allowance as ChatGPT chat messages is unverified; read `chatgpt.com/settings/usage` after a few days. A plan-limit rejection pauses the worker by design (`pause_reason` in `settings.json`).
- **The Mac must be awake.** A sleeping or switched-off machine stops consumption; the queue is durable and resumes.

### Throughput and usage delivery (2026-10-12)

| Gate | Result | Evidence |
|---|---|---|
| 1 Tests | ✅ 2026-10-12 | Full `scripts/tests`: **269 passed / 0 skipped** against the Neon test branch, run alone. Every new check was mutation-tested: 15 mutants (admission lock removed, slot limit off by one, limit counted per sibling, streak cleared inside the wait, `main` ignoring the wait, serial slots, no third-limit stop, limit treated as pause, usage written without its lock, no attempt refund, every held claim cancelled, no shared stop, streak kept after stop, Save keeping the wait, a failing slot not stopping the others). All 15 fail the suite. Two first-round "kills" were syntax errors and were redone. Independent `reviewer` pass: 3 real defects fixed before merge (sibling stop cancelled a source permanently; limits used up attempts; idle runs rescanned the queue 3×); its `finish()` locking finding was wrong, because the only caller already holds `worker.lock` + `control.lock`. **These DB tests share one test database and read global counts.** Run them alone: a concurrent run, or fixtures left by a killed run, make `run()` translate other suites' rows. |
| 2 Merge | ✅ 2026-10-12 | ws #1043 merged `381a6e7`; `workspace-check` pass. |
| 3 Stop → reinstall → re-enable | ✅ 2026-10-12 07:17 UTC | `enabled=false` under `control.lock`; `worker.lock` was free; installer ran from merged `main`. Manifest: workspace `381a6e7`, backend `54d7491`, shared `98875c8`; the four changed scripts are byte-identical to `main`. `daily_cap=300`, model `gpt-5.6-sol` and `pause_reason=None` were confirmed before `enabled=true` and the launchd bootstrap. |
| 4 Observe | ✅ throughput / ⏳ idle tick | **First run, 07:18:55–07:30 UTC:** three streams opened within 5 s. Production showed **3 live leases** at once, and never more. 23 saved plus 7 `temporary_error` in 11 min, about **2.1 saved/min against about 0.67/min serial** (≈3×). `usage.json` after 22 completions: 31,774 input / 0 cached / 39,325 output / 6,325 reasoning tokens. 0 ERROR lines and no plan-limit event. Budget used today: 178 of 300; 85 sources still `ready`. The idle tick waits for the backlog to drain. |

**Observed, not caused by this change: `temporary_error` rose on 10-12 from about 06:00 UTC.**

| Window (UTC) | Worker | Ticks / items | `temporary_error` |
|---|---|---|---|
| 00–02 | old serial worker | 100 ticks | 3 |
| 06:00–07:17 | old serial worker | 45 ticks | 17 |
| 07:19–07:30 | new worker | 30 items | 7 |

The failures arrive about 1 s after HTTP 200, with no `usage`. The client deliberately keeps no provider detail, so the event type (`response.failed` without a known code, `response.incomplete`, or an early stream end) is not recorded. Each failure uses an attempt, so a source hit twice becomes terminal. Recording the event type (no text) is the next step if the rate stays high.

Rollback: **Stop** on the setup page, or `launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/com.myblog.gpt-translate-poller.plist` (an in-flight tick may finish); keep both Claude translation jobs disabled; retain sources, pending demand, completed results and old work history. No DB migration or Terraform change.

## Sources

- [ChatGPT plan usage (Sign in with ChatGPT)](https://developers.openai.com/siwc/token-sharing-open-source)
- [Models and streamed inference](https://developers.openai.com/siwc/token-sharing-open-source/models-and-inference)
- [Developer mode and MCP apps in ChatGPT](https://help.openai.com/en/articles/12584461-developer-mode-and-mcp-apps-in-chatgpt)
- [Temporary Chat FAQ](https://help.openai.com/en/articles/8914046-temporary-chat-faq)
