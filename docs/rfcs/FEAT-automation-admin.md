# FEAT-automation-admin: Unified background-job management

- **Status**: draft
- **Owner**: Project owner
- **Created**: 2026-10-06
- **Plan row**: `plan.md` → Backlog → FEAT-automation-admin

## Goal

Let the owner see what background work the existing site has scheduled, queued or running,
why it started, where it runs, and how to control it from one management page. Cover AI
work and ordinary collection/maintenance jobs, with enough evidence to explain unexpected
usage or a queue that is not progressing.

## Non-goals

- This registration does not authorize implementation, deployment or enabling any job. (Lifted
  for Step 1's read-only inventory on 2026-10-12; Steps 2+ still need owner approval.)
- Moving every job into Work Cloud or replacing all queues with a new framework.
- Introducing a separately billed model API as a prerequisite.
- Automatically publishing generated reviews or changing existing content permissions.

## Current state

The Step 1 inventory and live-state audit (2026-10-12) are recorded under Step 1 below. The table in
this section is the discovery map that the audit started from. Source configuration is not proof of
deployment or execution.

| Area | Discovery starting point | Work to inventory |
|---|---|---|
| AWS schedules | `infra/eventbridge.tf`, `infra/lambda.tf` | New album ingestion; MusicBrainz/iTunes upcoming releases; Spotify/Last.fm listening; saved tracks; lyrics collection, demand collection and reassessment; Genius fetch; artist aliases/photos; ISRC; YouTube reference refresh; service warm-ups |
| AWS queues | `infra/sqs.tf`, `myblog_worker/` | Album sync and other explicit job messages, consumers, retry/dead-letter paths |
| Local AI jobs | `scripts/*poller.py`, `scripts/com.myblog.*.plist` | Lyrics translation, Genius translation, album research and genre repair; installed launch agents may differ from repository files |
| Nightly editorial work | `scripts/buckit_nightly.py`, `scripts/com.myblog.buckit-nightly.plist` | Draft generation, prerequisites, schedule and delivery state |
| Other schedulers | `.github/workflows/`, installed launch agents and task settings | Repository maintenance and any additional site-related scheduled jobs |
| Planned Cloud execution | [Work Cloud proposal, PR #1022](https://github.com/hyuntohoon/myblog-workspace/pull/1022) (unmerged) | Event subscriptions, translation dispatch and results; verify actual model selection behavior |

The existing `FEAT-durable-job-status` backlog item covers user-visible album sync and
Spotify follow-import completion. Reuse its eventual status contract and ownership rules;
this RFC adds the owner's cross-job operational view rather than a competing job lifecycle.

## Target state

- An owner-only page within `myblog_front`, backed by authenticated service endpoints.
- A job catalog records purpose, producer, trigger/schedule and timezone, queue/store,
  executor/location, AI provider/model when applicable, and available controls.
- Show enabled/paused separately from actual health; include pending/running/failed counts,
  oldest wait, recent runs/errors, last success, next scheduled run when known, and evidence
  freshness. Unknown or stale state must never appear healthy or empty.
- Distinguish stopping new requests, pausing consumption and cancelling in-flight work.
  Show the effect of each supported action before execution. Record actor and outcome.
- Continuous event monitoring is an acceptable operating mode. The owner may stop it
  manually; model self-unsubscription is not a production requirement.
- Expose model selection only where the execution path supports it. Distinguish a requested
  model, saved automation setting and observed execution model; do not infer inheritance
  from the Work chat composer. Link to the external control surface when necessary.
- Preserve execution boundaries. Evaluate existing AWS monitoring and suitable libraries
  against the discovered stack before adding a new queue/dashboard dependency.

## Steps

### Step 1 — Complete the inventory and choose the integration approach

Reconcile code, deployed AWS resources, database job states, local launch agents and
site-related automations. Record active, disabled, obsolete and unknown separately, with
timestamped evidence. Compare reuse of existing tools with a small site-native aggregation
layer. Resolve overlap with `FEAT-durable-job-status` and Cloud translation work.

**Verification**: Every discovered producer, consumer and schedule has an inventory entry;
state claims have live evidence or an explicit unknown marker. Document chosen tooling,
coverage gaps, proposed permissions and acceptance criteria before implementation.

#### Step 1 result — inventory (2026-10-12, read-only)

**Evidence window.** All live reads were taken between 2026-10-12 07:40 and 07:50 UTC. The read-only
sources were the AWS CLI (`ap-northeast-2`, as `claude_aws_manager`), the production DB inside
`BEGIN READ ONLY … ROLLBACK`, `launchctl` on the owner's Mac, the GPT worker state directory, and
`gh` / the remote-trigger API. Code references are `origin/main` at workspace `763a6d5`, backend
`54d7491`, music `2c7d791`, worker `89b8e6b` and shared_db `98875c8`. No job, schedule, setting or
row was changed.

**State vocabulary.**

- **active**: installed or deployed, and the window shows executions.
- **disabled**: installed, but deliberately not running.
- **obsolete**: the code or config remains, but there is no executor, and/or the code returns before
  doing work.
- **unknown**: not observable with the access this audit had.

"Delivered" means the trigger fired. It does not mean the job did useful work. Useful-work evidence is
cited separately where it exists.

##### A. AWS schedules (EventBridge default bus → Lambda)

Repository config: `infra/eventbridge.tf` declares 16 `local.worker_crons` entries and 2 warm pings.
Live: `aws events list-rules` returns **the same 18 rules, all `ENABLED`**. Each rule's target and
constant input match the config, and there are no extra and no missing rules.

The 7-day invocation counts below come from CloudWatch `AWS/Events Invocations`, window 10-05 07:43 →
10-12 07:43 UTC. `FailedInvocations` was **0 for every rule**. The worker Lambda had 4,294 invocations
with 0 `Errors` and 0 `Throttles` over the same window, and `/aws/lambda/blogWorkerLambda` had 0 `ERROR`
lines in the last 24 h.

| Job (`event.job`) | Rule / schedule (UTC) | Executor | 7-day delivered | State |
|---|---|---|---|---|
| MusicBrainz alias fill (no `job`; `source=aws.events`) | `worker-musicbrainz-alias-generation` `rate(15 min)` | blogWorkerLambda | 672 | active |
| `spotify_listening` | `worker-spotify-listening-sync` `rate(1 h)` | blogWorkerLambda | 168 | active |
| `spotify_member_poll` | `worker-spotify-member-poll` `rate(15 min)` | blogWorkerLambda | 672 | active |
| `lastfm_recent_tracks` | `worker-lastfm-recent-tracks` `rate(15 min)` | blogWorkerLambda | 672 | active |
| `release_upcoming_poll` mode=musicbrainz | `worker-release-upcoming-mb` `rate(1 h)` | blogWorkerLambda | 168 | active |
| `release_upcoming_poll` mode=itunes | `worker-release-upcoming-itunes` `rate(30 min)` | blogWorkerLambda | 336 | active |
| `album_ingest` | `worker-album-catalog-ingest` `rate(1 day)` | blogWorkerLambda | 7 | active |
| `spotify_saved_tracks_sync` incremental | `worker-spotify-saved-tracks-incremental` `cron(0 18 * * ? *)` | blogWorkerLambda | 7 | active |
| `spotify_saved_tracks_sync` full | `worker-spotify-saved-tracks-full` `cron(0 19 ? * SUN *)` | blogWorkerLambda | 1 | active |
| `lyrics_incremental` | `worker-lyrics-incremental` `rate(15 min)` | blogWorkerLambda | 672 | active |
| `lyrics_demand_source` | `worker-lyrics-demand-source` `rate(15 min)` | blogWorkerLambda | 672 | active; useful work seen: `lyrics_album_jobs.updated_at` 07:37 and `lyrics_album_tracks.updated_at` 07:39 UTC today |
| `lyrics_reassessment` | `worker-lyrics-reassessment` `rate(1 day)` | blogWorkerLambda | 7 | active |
| `genius_fetch` | `worker-genius-fetch` `cron(30 * * * ? *)` | blogWorkerLambda | 168 | active |
| `artist_photo_backfill` | `worker-artist-photo-backfill` `cron(0 20 ? * SUN *)` | blogWorkerLambda | 1 | active |
| `isrc_backfill` | `worker-isrc-backfill` `cron(0 21 ? * SUN *)` | blogWorkerLambda | 1 | active |
| `youtube_ref_refresh` | `worker-youtube-ref-refresh` `cron(10 4 * * ? *)` | blogWorkerLambda | 7 | active |
| Backend warm ping (`GET /health`) | `backend-api-warm-ping` `rate(5 min)` | ratemymusic-api | 2,015 | active (not a job; keep-warm) |
| Music warm ping (`GET /api/music/feed/new-releases`) | `music-api-warm-ping` `rate(5 min)` | musicApi | 2,016 | active (not a job; keep-warm) |

Failure path for cron-invoked worker runs: Lambda async config `MaximumRetryAttempts=2`, with on-failure
destination `worker-cron-dlq` (live: 0 visible / 0 in flight / 0 delayed). Every worker cron has a
`FailedInvocations` alarm by construction (`monitoring.tf`, `for_each` over `worker_cron`). At the time
of the read, 24 alarms existed and **none was in `ALARM`**.

The worker also routes `disc_no_backfill` from an `event.job` branch, but no rule triggers it.
`handler.py` describes it as a bounded one-off, so it counts as a **manual-only entry point** and not as
a schedule.

##### B. AWS queue (`blogSQS` → blogWorkerLambda)

Live: one event-source mapping, `blogSQS → blogWorkerLambda`, `Enabled`, batch 10. The queue's redrive
target is `album-sync-dlq` (maxReceiveCount 3). Queue depths at 07:42 UTC were **all 0**: `blogSQS`,
`album-sync-dlq` and `worker-cron-dlq` had 0 visible, 0 in flight and 0 delayed. No other queue exists in
the region. 7-day worker invocations minus cron deliveries leaves 63 (4,294 − 4,231) non-cron invocations, which is roughly the SQS-triggered count.

Message types, matched producer by consumer branch (`worker/handler.py` Records loop):

| Message | Producer(s) | Trigger | State |
|---|---|---|---|
| `{album_ids:[…], market}` / `{spotify_album_id}` (album sync) | music `POST /api/music/sync-requests` (`SyncRequestService`); backend `safe_enqueue_catalog_sync` (`library.py`); worker `enqueue_album_sync` (listening/library sync, follow ingest, `album_ingest`); shared_db `scripts/import_streaming_history.py` (manual CLI) | user action + worker fan-out + manual | active (code path; no per-message evidence: SQS keeps no history) |
| `spotify_refresh` | backend `library.py` manual refresh | owner action | active (code path) |
| `spotify_library_sync` | backend `buckets.py`, `me.py` | user action | active (code path) |
| `spotify_saved_tracks_sync` | none on `main` besides the EventBridge rules (the handler also accepts an SQS copy) | — | consumer only |
| `spotify_follow_import` (+ one delayed `rerun`) | backend `tracked_artists.py`; worker self-chain | owner action | active (code path) |
| `spotify_follow_ingest` | worker `enqueue_follow_ingest` | worker fan-out | active (code path) |
| `lyrics_member_bootstrap` | backend `integrations.py` → `safe_enqueue_member_demand_bootstrap` | member connects Spotify | active (code path) |
| `lyrics_discography_enumerate` (self-chained, delayed) | worker `_nudge_discography_enumeration` / enumeration hops | worker | active; `lyrics_artist_discographies` 36 complete, last update 10-10 05:10 UTC |
| `lyrics_incremental` | worker `enqueue_lyrics_incremental` (after album sync) | worker | active (code path) |
| `genius_fetch` + `album_id` | local `research_poller.py` nudge | local poller | **disabled with its producer** (see C) |
| `lyrics_reassessment` / `lyrics_demand_source` / `artist_photo_backfill` with overrides | no `main` producer | manual send | manual-only entry points |
| `isrc_backfill` / `youtube_ref_refresh` / `disc_no_backfill` | no producer | manual send | **dropped**: the Records loop has no branch for them, so the message is logged as "Unknown message format" and deleted unrun. `infra/eventbridge.tf`'s "manual blogSQS `{"job":"isrc_backfill"}` message still works" comment is wrong. The only manual path is a direct Lambda invoke (pre-existing; relevant to Step 3 controls) |

User-facing completion of album sync and follow import is `FEAT-durable-job-status`'s subject. Today
neither has a durable record, so **SQS-borne work is invisible after consumption**. That is the largest
coverage gap for the page (see "Integration approach").

##### C. Local launch agents (owner's Mac)

The repository (`scripts/com.myblog.*.plist`, plus shared_db `scripts/com.myblog.genre-backfill.plist`)
is compared below against what is installed (`~/Library/LaunchAgents`), the launchd overrides
(`launchctl print-disabled`) and what is loaded (`launchctl list`). Last boot was **2026-09-27
02:33 UTC** (`kern.boottime`). An agent that is installed but not loaded has not run since then.

| Label | Repo | Installed | Override | Loaded | Last log activity | Work it drains | State |
|---|---|---|---|---|---|---|---|
| `gpt-translate-poller` (`gpt_queue_worker.py`, frozen runtime) | yes (template) | yes | enabled | **yes** (pid 71502) | `worker.log` 16:45 KST today | `lyrics_translation_work`, `chatgpt/lyrics-ko-v1` | **active** — see D |
| `buckit-nightly` (03:00 daily; `buckit_nightly.py`) | yes | yes | enabled | no | `myblog-buckit-nightly.log` last INFO 2026-09-27 03:31 KST ("no checked memos … $0") | review-bucket memos → draft reports | disabled (not reloaded after reboot; OPS-project-stabilization Step 2D gates reload on the subscription-guard fix) |
| `research-poller` (60 s, `--once`) | yes | yes | enabled | no | last line 2026-09-27 11:31 KST (genius nudge timeout) | `album_research` | disabled (same gate). Queue: 87 `done`, **0 `queued`** — nothing stranded today |
| `genre-heal-poller` (30 min) | yes | yes | enabled | no | last INFO 2026-09-24 20:59 KST ("no pending genre-backfill request") | `genre_backfill_requests` | disabled (same gate). Queue: 2 finished (06-21), **0 pending** |
| `genre-backfill` (04:00 daily; shared_db `backfill_genres.py`) | shared_db only | yes | enabled | no | last line 2026-09-27 06:31 KST (throttle cool-down) | genre pipeline over catalog | disabled (same gate) |
| `lyrics-translate-poller` (60 s) | yes | **no** | **disabled** | no | — | `track_lyrics_translations` (legacy Claude) | **obsolete** — script returns before DB work (retired by Chat translation) |
| `genius-translate-poller` (60 s) | yes | **no** | **disabled** | no | — | `track_genius_annotations` | **obsolete** — same; table frozen: 6,596 done / 23 failed / 12 pending, last update 2026-08-15 |
| `cdp-reaper` (30 min; `~/.local/bin/cdp-reaper.sh`) | **no** | yes | enabled | yes (687 runs, last exit 0) | — | stray CDP Chrome processes | active, **dev tooling, not a site job** — excluded from the catalog |

Not scheduled, but they share the queues above: `editor_buckit.py` (manual Stage 0; `buckit_nightly`
is its scheduled sibling), `lyrics_demand_translate.py` (library module, imported transitively by the GPT runtime via
`lyrics_translate_poller` and bundled by the installer, with no schedule of its own) and `neuralwatt_claude_shim.py` (PATH shim used only inside
`genre_heal_poller`). There is no crontab. The **dormant `researchWorkerLambda`**, which
`research_poller.py`'s header still mentions, **does not exist**: `list-functions` returns only
`ratemymusic-api`, `musicApi` and `blogWorkerLambda`. The header is stale and the paid cloud
path is obsolete.

##### D. GPT translation worker (live detail)

`settings.json`: `enabled=true`, `daily_cap=300`, `model=gpt-5.6-sol`, `pause_reason=null`. The runtime
`manifest.json` pins workspace `381a6e7`, backend `54d7491` and shared `98875c8`. Its own `enabled: false`
is the install-time default; the live switch is `settings.json`.

`usage.json` for 2026-10-12: 63 requests, 77,144 input / 94,298 output / 16,237 reasoning tokens, 0 cached.
The last completed `run()` (`status.json`, logged 16:37 KST) recorded `saved 41`, `temporary_error 13` and
`scan_wrap 1`. **No `idle` outcome yet**, so the gate-4 idle tick is still unrun.

DB at 07:45 UTC (`lyrics_translation_work`, `chatgpt/lyrics-ko-v1`): 483 `done`, 56 `ready`,
3 `running`, 35 `retryable_error`. Of the `temporary_error` rows, 33 are at `attempts=1` and 1 is at
`attempts=2` (the terminal-risk row). The `claude.sonnet/v2` rows remain frozen per OPS Step 2D:
1,915 `done`, 169 `retryable_error`, 93 `cancelled`, and 70 `running`, all 70 with an expired lease.

Observability limit: the worker's state lives only on the Mac. The cloud can see the DB rows the worker
writes, but not the worker's process, its settings or its usage.

##### E. Other schedulers

- **GitHub Actions**: across all six repos, the only `schedule:` trigger is workspace
  `verifier-drift.yml`, `cron: "20 18 * * *"`. Its last three runs were schedule-triggered `success`
  runs on 10-09, 10-10 and 10-11; the latest was at 2026-10-11 22:06 UTC, because GitHub delays cron
  starts. This is a repository guard and not a site job, but the catalog lists it because a failure
  matters to the owner.
- **Claude routines** (remote triggers): `list` returned **0**.
- **Work Cloud translation** ([#1022](https://github.com/hyuntohoon/myblog-workspace/pull/1022)):
  draft, unmerged. Nothing is deployed, so it is **planned** and not inventoried as a job.
- **Other in-process background work**: none found. A `git grep` of backend and music `app/` for
  `BackgroundTasks`, `create_task` or threads returned no matches.

##### F. Not observable with this audit's access (unknown)

- **EventBridge Scheduler** schedules and **non-default event buses**: `scheduler:ListSchedules` and
  `events:ListEventBuses` were denied for `claude_aws_manager`. Nothing in `infra/` declares either, so
  the expected answer is "none", but this is **unverified**.
- **Per-message SQS history**: SQS keeps none, so past album-sync / follow-import outcomes cannot be
  reconstructed (→ `FEAT-durable-job-status`).

##### Integration approach

| Option | Covers | Misses | Verdict |
|---|---|---|---|
| AWS-native only (CloudWatch dashboard / console links) | EventBridge delivery, Lambda errors, SQS depth, alarms | Every local agent, every DB-backed queue, GPT usage; not inside the site; no owner auth model | Rejected as the page. Keep it as a **data source** |
| Off-the-shelf queue dashboard (Flower, RQ/BullMQ boards, …) | — | The stack has no Celery/RQ/BullMQ. Adopting one means replacing the queues, which this RFC's non-goals exclude | Rejected |
| **Site-native aggregation** (chosen) | All of A–E through three adapters | Needs a heartbeat from the Mac | **Chosen** |

Shape of the chosen approach, which Step 2 builds and this step does not:

1. **Static catalog in code.** Each entry has: key, purpose, trigger and schedule (with TZ), executor
   and location, the queue/store it drains, AI provider/model, and supported controls (none in Step 2).
   The catalog is not runtime state. A row with no fresh evidence renders **unknown**, never healthy.
2. **Adapters**, each returning `observed_at` with its value:
   - **AWS**, read-only: `events:DescribeRule` (state, schedule), CloudWatch `GetMetricStatistics`
     (`AWS/Events` Invocations/FailedInvocations per rule; `AWS/Lambda` Errors/Throttles),
     `sqs:GetQueueAttributes` (three queues), `cloudwatch:DescribeAlarms` (state).
   - **DB**, read-only: per-queue counts by state, oldest waiting item and last update. The queues are
     `lyrics_translation_work`, `lyrics_album_jobs`, `lyrics_album_tracks`, `lyrics_artist_discographies`,
     `album_research` and `genre_backfill_requests`. Frozen legacy tables are shown as frozen.
   - **Local heartbeat**: each local agent writes a small row (label, `observed_at`, last outcome,
     enabled, model/cap for GPT, today's usage totals) to a new additive table. The page derives
     "not loaded / not running" from **heartbeat age**, which is exactly the failure that went
     unnoticed here: four agents silently stopped at the 09-27 reboot.
3. **One owner-only read endpoint in `myblog_backend`** (`require_owner`, matching `infra/apigateway.tf`
   route), and one page in `myblog_front` via `apiFetch`. Backend, not music, because owner authorization
   tiers are backend-only (`app/core/authz.py`).

**Overlap resolution.**

- `FEAT-durable-job-status` owns the per-request job record for album sync and follow import. Once that
  record exists, this page reads it as one more DB adapter and defines no lifecycle of its own. Until
  then, those two rows show "accepted → unknown" honestly.
- Cloud translation (#1022) gets a catalog row only after it merges and deploys. The row records the
  observed execution model per run, not an assumed inheritance.

**Proposed permissions (for Step 2 approval).** The backend Lambda role gains read-only
`events:DescribeRule`, `events:ListRules`, `cloudwatch:GetMetricStatistics`, `cloudwatch:DescribeAlarms`
and `sqs:GetQueueAttributes`, scoped to the named rules, queues and alarms where the action supports
resource scoping. No write, invoke, start or stop actions. The local heartbeat writes through the DB
credentials the agents already hold. No new secret.

**Acceptance criteria for Step 2.**

- Every row in tables A–E (excluding dev tooling) is in the catalog.
- Each state cell shows `observed_at`, and a stale or missing source renders "unknown".
- A local agent that is not loaded shows stale within one schedule interval plus grace.
- Opening the page starts nothing.
- A non-owner gets 403, and an unauthenticated caller gets 401.
- The AWS adapter's IAM grant contains no non-read action.
- AWS reads use an explicit botocore `Config` (connect/read timeout, bounded retries) and batch metrics
  with `GetMetricData`, not one `GetMetricStatistics` per rule.
- No DB session is held across the AWS calls: fetch DB → close → AWS → assemble.

**Coverage gaps carried into Step 2.**

- The Scheduler/bus check (F) needs an owner-run read or a role grant before Step 2 can claim it.
- SQS message outcomes are invisible until `FEAT-durable-job-status`.
- GPT plan usage on chatgpt.com remains external: the page can show local `usage.json` totals and link to
  the account page, but cannot read the plan allowance.

**Findings the owner may want to act on** (none changed here):

1. Four Claude-CLI agents (`buckit-nightly`, `research-poller`, `genre-heal-poller`, `genre-backfill`)
   have not run since the 2026-09-27 reboot. This is consistent with OPS Step 2D's disposition, and their
   queues hold nothing pending.
2. The UI producers for `album_research` (adding an album to a bucket whose `research_mode` is `all`/`selected`) and `genre_backfill_requests` (the "장르 채우기"
   button) are still live on `main`. A new request would wait with no consumer and no visible signal.
3. Manual `blogSQS` messages for `isrc_backfill`, `youtube_ref_refresh` and `disc_no_backfill` are
   silently dropped (table B). The `infra/eventbridge.tf` comment claiming otherwise is stale.
4. `research_poller.py` still names a `researchWorkerLambda` that no longer exists.

### Step 2 — Add status reporting and a read-only management page

Agree the shared status contract first, then implement necessary service/worker reporting
and the frontend page. Keep schema changes additive if needed; do not invent runtime state
from schedule configuration. Follow existing API contract and authentication requirements.

**Verification**: Owner/non-owner authorization checks; queued, running, failed, paused and
stale-source cases; service checks and a browser walkthrough; deployment smoke for each
changed service. No job is started by opening the page.

**Rollback**: Revert UI/read endpoints; retain additive history data and existing execution.

### Step 3 — Add supported operational controls

Add per-job manual run, pause/resume and retry only after the underlying adapter supports
their semantics. Make actions idempotent, auditable and scoped; preserve manual priority,
deduplication and existing result-write guards. Clarify in-flight behavior for each executor.

**Verification**: Repeated clicks do not duplicate work; pause boundaries are observable;
retry does not overwrite newer/manual results; unauthorized requests fail closed; complete
service checks, browser walkthrough and production smoke for the approved rollout scope.

**Rollback**: Disable the control endpoints first, retain status visibility and audit history,
and reconcile any already-started work before reverting execution adapters.

## Open questions

1. **Coverage and tooling** — *Answered by Step 1 (2026-10-12):* the catalog is tables A–E, and the
   approach is site-native aggregation (static catalog + AWS/DB read adapters + local heartbeat), with no
   queue/dashboard library. Still open: the EventBridge Scheduler/bus check (F), and Step 2 itself needs
   owner approval.
2. **Cloud model controls** — Verify event-run model selection/persistence and what the
   site can observe or change. Blocks that control, not the read-only page.
3. **Operational policy** — Decide history retention, stale thresholds, optional budgets
   and retry limits before the affected implementation. No daily ten-run cap is assumed.

## Decisions log

| Date | Decision | Step |
|---|---|---|
| 2026-10-06 | Owner requested task registration in plan and RFC only; keep draft/backlog, with no implementation or runtime changes. | Registration |
| 2026-10-06 | Continuous monitoring with manual stopping is acceptable; self-unsubscription is not a production requirement. | Design constraint |
| 2026-10-12 | Owner lifted the registration-only non-goal **for Step 1 only** (Steps 2+ still need approval). Step 1 inventory recorded; site-native aggregation chosen. Status stays draft. | Step 1 |
