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
  for Step 1's read-only inventory on 2026-10-12, and for Step 2's read-only page, split 2a–2e (2f added after 2c),
  on the same day; and for Step 3, split by control, on 2026-10-13.)
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
| `genius_fetch` + `album_id` | local `research_poller.py` nudge | local poller | **disabled with its producer** (see C). **→ active 2026-10-15** with research-poller |
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
| `gpt-translate-poller` (`gpt_queue_worker.py`, frozen runtime) | yes (template) | yes | enabled | **yes** (pid 71502) | `worker.log` 16:45 KST today | `lyrics_translation_work` (`chatgpt/lyrics-ko-v1`, `chatgpt/genius-ko-v1`); also `track_lyrics_translations` `requested`, `track_genius_annotations` `pending` and `lyrics_album_tracks` (corrected in 2b) | **active** — see D |
| `buckit-nightly` (03:00 daily; `buckit_nightly.py`) | yes | yes | enabled | no | `myblog-buckit-nightly.log` last INFO 2026-09-27 03:31 KST ("no checked memos … $0") | review-bucket memos → draft reports | disabled (not reloaded after reboot; OPS-project-stabilization Step 2D gates reload on the subscription-guard fix). **→ active 2026-10-15** (see the reload note below) |
| `research-poller` (60 s, `--once`) | yes | yes | enabled | no | last line 2026-09-27 11:31 KST (genius nudge timeout) | `album_research` | disabled (same gate). Queue: 87 `done`, **0 `queued`** — nothing stranded today. **→ active 2026-10-15** |
| `genre-heal-poller` (30 min) | yes | yes | enabled | no | last INFO 2026-09-24 20:59 KST ("no pending genre-backfill request") | `genre_backfill_requests` | disabled (same gate). Queue: 2 finished (06-21), **0 pending**. **→ active 2026-10-15** |
| `genre-backfill` (04:00 daily; shared_db `backfill_genres.py`) | shared_db only | yes | enabled | no | last line 2026-09-27 06:31 KST (throttle cool-down) | genre pipeline over catalog | disabled (same gate). **→ active 2026-10-15**, now under the heartbeat wrapper |
| `lyrics-translate-poller` (60 s) | yes | **no** | **disabled** | no | — | `track_lyrics_translations` (legacy Claude) | **obsolete** — script returns before DB work (retired by Chat translation). *Corrected in 2b:* the table is not orphaned — the GPT worker drains its `requested` rows |
| `genius-translate-poller` (60 s) | yes | **no** | **disabled** | no | — | `track_genius_annotations` | **obsolete** — same; 6,596 done / 23 failed / 12 pending, last update 2026-08-15. *Corrected in 2b:* the table is **not frozen** — the GPT worker drains eligible `pending` rows; all 12 are ineligible for its filter |
| `cdp-reaper` (30 min; `~/.local/bin/cdp-reaper.sh`) | **no** | yes | enabled | yes (687 runs, last exit 0) | — | stray CDP Chrome processes | active, **dev tooling, not a site job** — excluded from the catalog |

**Reload (2026-10-15, OPS-project-stabilization Step 2D).** The four Claude-CLI agents were
re-bootstrapped after a waiting `album_research` row was found with no consumer. Alongside the reload:
the subscription-guard fix (shared_db #87) and its pins (backend #185, worker #110); the backend and
worker venvs reinstalled at shared_db `08b2ee7`; the shared checkout moved from a stale detached
`9ba84f6` to `origin/main` so the plists run the #1052 heartbeat writers; and `genre-backfill`
wrapped by `automation_heartbeat.py exec` (shared_db #88). The backend catalog (#185) declares the
four agents `active`.

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

##### F. EventBridge Scheduler and event buses (resolved 2026-10-12, after the inventory)

The inventory could not read these: `scheduler:ListSchedules` and `events:ListEventBuses` were denied for
`claude_aws_manager`. With the owner's approval the same day, that user's inline `events-manage-terraform`
policy was compacted (`events:List*`, `events:Describe*`) and gained `scheduler:List*` and
`scheduler:GetSchedule`; no write action was added. Reads were taken the same day, before 09:20 UTC:

- **Event buses:** `default` only. Its 18 rules are table A; nothing is hidden on another bus.
- **Scheduler:** one group (`default`) with **two schedules that `infra/` does not declare**:

| Schedule | Expression (Asia/Seoul) | Target | Input | State |
|---|---|---|---|---|
| `StartBlogDB` | `cron(0 9 ? * TUE-FRI *)` | Lambda `mydbhandler` | `{"action":"start"}` | **obsolete, still firing** |
| `StopBlogDB` | `cron(0 18 ? * TUE-FRI *)` | Lambda `mydbhandler` | `{"action":"stop"}` | **obsolete, still firing** |

  Both were created 2025-10 in the console. `mydbhandler` does not exist (`GetFunction` →
  `ResourceNotFoundException`) and the account has no RDS instance or cluster, so these are the pre-Neon
  office-hours DB switch. They still fire: `AWS/Scheduler TargetErrorCount` summed 4 for 10-05 → 10-12.
  Retry is 0 and there is no DLQ, so the failure goes nowhere. Harmless, but noise. Deleting them is the
  owner's call (finding 5); the catalog lists them as obsolete.

##### G. Not observable with this audit's access (unknown)

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
     `album_research` and `genre_backfill_requests`. Frozen legacy tables are shown as frozen. (2b added
     `track_lyrics_translations` and `track_genius_annotations` as live GPT inputs; the only frozen store is
     the `claude.sonnet/v2` slice of `lyrics_translation_work`.)
   - **Local heartbeat**: each local agent writes a small row (short label, `observed_at`, last outcome,
     enabled, model/cap for GPT, today's usage totals) to a new additive table. The page derives
     "not loaded / not running" from **heartbeat age**, which is exactly the failure that went
     unnoticed here: four agents silently stopped at the 09-27 reboot.
3. **One owner-only read endpoint in `myblog_backend`** (`require_owner`; whether it also gets an
   `infra/apigateway.tf` JWT route is decided in 2b, see the Step 2 design notes), and one page in `myblog_front` via `apiFetch`. Backend, not music, because owner authorization
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

- Every row in tables A–F (excluding dev tooling) is in the catalog.
- Each state cell shows `observed_at`, and a stale or missing source renders "unknown".
- A local agent that is not loaded shows stale by the staleness rule in the Step 2 design notes.
- Opening the page starts nothing.
- A non-owner gets 403, and an unauthenticated caller gets 401.
- The AWS adapter's IAM grant contains no non-read action.
- AWS reads use an explicit botocore `Config` (connect/read timeout, bounded retries) and batch metrics
  with `GetMetricData`, not one `GetMetricStatistics` per rule.
- No DB session is held across the AWS calls: fetch DB → close → AWS → assemble.

**Coverage gaps carried into Step 2.**

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
5. Two console-made Scheduler schedules (`StartBlogDB` / `StopBlogDB`) still invoke a deleted Lambda
   every weekday (F).

### Step 2 — Add status reporting and a read-only management page

Agree the shared status contract first, then implement necessary service/worker reporting
and the frontend page. Keep schema changes additive if needed; do not invent runtime state
from schedule configuration. Follow existing API contract and authentication requirements.

**Verification**: Owner/non-owner authorization checks; queued, running, failed, paused and
stale-source cases; service checks and a browser walkthrough; deployment smoke for each
changed service. No job is started by opening the page.

**Rollback**: Revert UI/read endpoints; retain additive history data and existing execution.

#### Step 2 split (owner-approved 2026-10-12)

One sub-step per session. Each ships and verifies alone, and every sub-step leaves the page honest:
a source that is not wired yet renders **unknown**, never healthy or empty.

| Sub-step | Scope | Repos | Mandatory review |
|---|---|---|---|
| **2a** | `automation_heartbeats` table (V59, additive), prod + test-branch apply | workspace `schema.sql` → shared_db | `reviewer` (contract) |
| **2b** | Static catalog (tables A–F) + DB adapter + heartbeat read; `GET /api/admin/automation` behind `require_owner`; contract + `openapi.json`. AWS rows render unknown | backend → workspace contract → front types | `reviewer` + `security-review` |
| **2c** | Owner page via `apiFetch`; real-browser walkthrough | front | — |
| **2d** | AWS adapter (`GetMetricData` batch, explicit botocore `Config`, DB session closed before AWS calls) + read-only IAM on the backend role; full `terraform plan` | backend + infra | `reviewer` + `security-review` |
| **2e** | Heartbeat writers: GPT worker first (frozen runtime → reinstall); the four unloaded Claude-CLI agents get the code but only report once OPS Step 2D reloads them | workspace `scripts/` | — |
| **2f** | Queue detail API (added 2026-10-12, owner's B+C pick): per queue, counts by **reason code** (`last_reason` / status-reason columns, never raw error text — `track_lyrics_translations.error` can hold a raw exception), 24 h in/out, the oldest N waiting rows (ids, titles, age, next retry). Read-only, `require_owner`, same one-transaction DB adapter as 2b. The 2c detail panel then shows *why* rows wait and whether the queue drains | backend → workspace contract → front | `reviewer` + `security-review` |

Why 2d is split from 2b: it is the only sub-step with IAM and Terraform, and 2b already makes the
failure that went unnoticed visible (DB queues + local-agent staleness).

**2a result (2026-10-12, shipped).** V59 `automation_heartbeats` was merged in shared_db #85
(`d31b060`) after ws #1046 added it to the canonical schema. It was applied to Neon prod and to the test
branch **before** the merge. A live check at 09:20 UTC showed 5 columns, the 4 constraints and 0 rows,
and is quoted on shared_db #85. Consumers pin `d31b060` (no tag) when 2b lands. The migration test runs
the real V59 file and asserts every CHECK by a rejected write; all 5 mutants were killed.

**2b result (2026-10-12).** Backend [#181](https://github.com/hyuntohoon/myblog_backend/pull/181):
`GET /api/admin/automation` (`require_owner`), pinning shared_db `d31b060` (requirements and the CI
canonical-schema ref). The catalog is 40 rows (A 18, F 2, B 12, C 7, E 1). The DB adapter reads 7 queue
tables plus `lyrics_translation_work` per `translator_version` in one `SET TRANSACTION READ ONLY`
transaction, closed before assembly. Every row without fresh evidence renders `unknown`; a failed read
gives `counts: null`, never `{}`.

- **Inventory correction.** Table C was wrong about two tables. The GPT worker's `CANDIDATES` reads
  `track_lyrics_translations.status='requested'`, `track_genius_annotations.translation_status='pending'`
  and `lyrics_album_tracks`, and `gpt_translation_store.py` publishes to the first two. All three are live.
  Rows its filter can never pick up count as `*_ineligible`, not waiting. On prod, all 12 pending Genius
  annotations are ineligible, so they no longer read as a stuck backlog.
- **Local smoke against prod (read-only), 09:50 UTC:** 200 in about 2 s; 40 jobs, all `unknown`
  (0 heartbeats). Queue counts match the Step 1 audit, e.g. `claude.sonnet/v2` with
  `stale_running 70` (every lease expired).
- **Carried to 2c/2e.** An agent that has never written a heartbeat shows unknown, not stale, until its
  first write. The 2e GPT writer must heartbeat mid-run if `run()` can exceed 15 minutes. 2c renders
  `details`/`last_outcome` as text only. 2e writers must not put raw exception strings in `details`.

**2c result (2026-10-12, shipped in two PRs).**

- **First page:** front [#456](https://github.com/hyuntohoon/myblog_front/pull/456) (`887e484`). Prod
  smoke through CloudFront: no token → 401, member → 403 `Owner only`, and the deployed bundle carries
  the new identifiers (quoted on #456). The owner then opened it on prod, which was the first owner 200.
- **Owner feedback the same day:** *"not intuitive — I can't tell whether it is running, what is wrong,
  or what is waiting."* From a three-direction mock-up the owner picked **B+C, in two stages**: a front
  rework now (B: 흐름/표 switch, C: one shared detail panel), and the data the panel needs later (**2f**).
- **Rework:** front [#457](https://github.com/hyuntohoon/myblog_front/pull/457) (`6e76327`). Queue
  verdicts come from evidence the 2b snapshot already carries: counts, the oldest waiting row, expired
  leases and `frozen`. The tiers are 손볼 것 (expired leases, ranked above frozen), 동결, 지켜볼 것
  (consumers all off in the inventory, or the oldest waiting row is over a day old), 볼 수 없음 (read
  failed, or the table is empty, shown apart) and 문제 없음. The page opens on the most urgent queue.
  Prod smoke (deploy run 38256808492): no token → 401, member → 403, and the new bundle
  `AutomationBoard.Ijj7j7_d.js` carries the new identifiers and no `막힘`. It is quoted on #457.
- **Why the verdicts are conservative.** A read-only prod check the same day showed 848 of 854 waiting
  album jobs at `album_not_in_catalog`, with the queue shrinking (13 in / 18 out in 24 h). It also
  showed 2,409 of 2,412 album tracks at `not_found`, and 167 of 169 `claude.sonnet/v2` retries at
  `engine_validation`. A count-only "stuck" verdict would have been confidently wrong. So the page
  never says 막힘/stuck, says only "1일 넘게 대기" for a long wait, and states that the reason and the
  drain rate are not visible yet. `declared_state` is used in one direction only, to warn that a
  queue's consumers are switched off.
- **What the page now shows on prod (local walkthrough against the prod DB, 13:28 UTC):** 10 queues.
  1 is 손볼 것: `claude.sonnet/v2`, 70 expired leases, frozen. 3 are 지켜볼 것: album jobs 855 (31 days),
  album tracks 2,412 (15 days), GPT lyrics 26 (3 days). 1 is 볼 수 없음: GPT Genius, no rows yet. 5 are
  문제 없음. Of the 40 jobs, 0 show run evidence: AWS waits on 2d, and heartbeats wait on 2e (0 rows).
- **Next sub-step: the owner picks.** The recommendation is **2f → 2e → 2d**. 2f answers the owner's
  actual complaint (why rows wait, and whether a queue drains) from the DB alone, with no IAM. 2e is
  small and makes the one live Mac agent (GPT worker) observable. 2d is the only step with IAM and
  Terraform, and it adds AWS liveness, which no current verdict depends on.

**2f result (2026-10-12, shipped).** Backend [#182](https://github.com/hyuntohoon/myblog_backend/pull/182)
(`b648eeb`), contract ws [#1050](https://github.com/hyuntohoon/myblog-workspace/pull/1050), front
[#458](https://github.com/hyuntohoon/myblog_front/pull/458) (`16891e9`).

- **Endpoint.** `GET /api/admin/automation/queue-detail?key=<snapshot queue key>`, `require_owner` on the
  edge_guard GET catch-all (2b's posture). Only keys the snapshot can show resolve; the translator version
  is a bind parameter. A member gets 403 for a real, unknown or missing key (not 404/422). One
  `SET TRANSACTION READ ONLY` transaction, 4 SELECTs, no external call. A failed read gives
  `status: unknown` with null sections.
- **Reason codes only.** `lyrics_translation_work.last_reason` holds `engine_validation: <exception text>`
  on the legacy Claude rows. So the code is cut in SQL (`^[a-z][a-z0-9_]{0,63}`, optionally followed by
  `:`), and anything else comes back as `unrecognized`. The `error` columns of `album_research` /
  `track_lyrics_translations` are never selected. `album_research`, `genre_backfill_requests`,
  `track_lyrics_translations` and `track_genius_annotations` record no codes, and the panel says so.
- **Flow is not uniform: each queue states its basis, and a basis that cannot measure returns null.**
  Review found two traps. The GPT worker publishes album translations straight into
  `track_lyrics_translations` as `done` (`requested_at = translated_at`). Those are excluded from
  "entered", and "left" is **null** there. A Genius re-fetch bumps `updated_at`, so "left" uses
  `translated_at`. `lyrics_album_tracks` has no `created_at`, so its "entered" is null. The `updated_at`
  proxies elsewhere are labelled *Approximate*. The front never claims a direction unless both sides were
  measured. **The verdict tiers stay snapshot-only** for the same reason.
- **Prod reading (2026-10-12 ~14:05 UTC, read-only).**
  - Album jobs: 848 `album_not_in_catalog`, **all backing off**; 14 in / 19 out in 24 h.
  - Album tracks: 2,409 `not_found`, all backing off.
  - GPT lyrics: 25 `temporary_error` + 1 `output_limit`.
  - claude v2: 169 `engine_validation`, retries all overdue (frozen).
  - Manual lyrics requests: 0 entered in 24 h. The 255 "requests" a naive count showed were GPT publishes.
- **Smoke.** Backend through CloudFront at 14:20 UTC: 401 / member 403 (quoted on #182). Front bundle
  `AutomationBoard.C6rXGmSs.js` carries the new identifiers, and the 2c placeholder is gone (quoted on
  #458). The owner's own 200 is still unobserved by Claude. The local clickthrough against the prod DB
  rendered all three sections, including at 390 px.
- **Tests.** Mutation-tested on both sides. The backend killed 19 of 20 mutants; the survivor is an
  unreachable `requested_ineligible` state. The front killed 6 of 7; the survivor is a single-render-flash
  guard, which a DOM test cannot observe.
- **Next sub-step: the owner picks between 2e and 2d.** The recommendation is still 2e first: it is
  small, needs no IAM, and the GPT worker is the one live Mac agent.

**2e result (2026-10-13, shipped).** Workspace [#1052](https://github.com/hyuntohoon/myblog-workspace/pull/1052)
(`2974705`).

- **Writer.** `scripts/automation_heartbeat.py` upserts one row per agent in its own short connection
  (`observed_at = now()`, connect timeout 10 s, `statement_timeout` 5 s, and `SET TRANSACTION READ WRITE`
  against a pooler session's leaked read-only default). It keeps the design-note contract:
  `last_outcome` at most 200 characters, `details` at most 2 KB of JSON (a marker replaces anything
  larger), codes and counts only, and only the exception *type* in logs. A failed write never fails
  the agent.
- **GPT worker.** It writes at the end of every run. During a run it writes at most every 120 s, and only
  when a slot makes progress, so a run whose slots all hang stops writing and goes stale after 15 min.
  An idle start (stopped, paused or limit wait) writes at most every 300 s. *Behaviour change:* a
  disabled or limit-waiting worker used to skip the DB entirely. It now opens one short connection at
  most every 5 min (no claims). The runtime was reinstalled from `2974705` with backend `54d7491` and
  shared `98875c8`, the same pins as before, so the heartbeat is the only change.
- **Prod check (02:19 UTC).** The first tick wrote `gpt-translate-poller` (`scan_wrap 2, scanned 2`,
  phase `finished`, model/cap/today's usage). A local backend at `b648eeb` against the prod DB returned
  it as **fresh (23 s, 900 s bound)**. The heartbeat source reads `ok, 1 agent(s) reporting`. This is
  quoted on #1052.
- **Claude-CLI agents: code only.** research-poller (one write per start and per handled item),
  buckit-nightly and genre-heal-poller (one write per start) report only after OPS Step 2D reloads them.
  Their plists run the **shared checkout's** `scripts/`, so that checkout must be on a main that includes
  #1052 at reload time. A genre-heal backfill longer than its 60-min bound shows stale until it ends.
- **genre-backfill is not wired.** Its code and plist live in shared_db. The wrapper
  `automation_heartbeat.py exec genre-backfill -- <command>` exists, but the shared_db plist was not
  changed. Carried to OPS Step 2D: install it through the wrapper when it is reloaded.
  **Done 2026-10-15:** shared_db #88, installed with the reload.
- **Tests.** Writer 17 and GPT worker 40, both on the shared test branch, run serially. 19 mutants: the
  first pass killed 17, and after two added tests (DSN text in the log, read-only session default) all
  19 were killed. `security-review`: no findings.
- **Next sub-step:** 2d (AWS adapter + read-only IAM + full `terraform plan`). It is the last Step 2
  sub-step. Step 3 still needs separate approval.

**2d result (2026-10-13; shipped, IAM applied the same day).** Backend
[#183](https://github.com/hyuntohoon/myblog_backend/pull/183) (`f7f4c44`), this workspace PR (contract +
`infra/iam_roles.tf`), front [#459](https://github.com/hyuntohoon/myblog_front/pull/459). Owner's pick at the
start of the session: a structured `aws` block in the contract **and** a front panel in the same sub-step,
rather than packing AWS state into reason strings.

- **Adapter** (`app/services/automation_aws.py`). It runs four read-only sections concurrently: `DescribeRule`
  for each of the 18 rules; one `GetMetricData` pass over two windows; `GetQueueAttributes` for blogSQS and its
  two DLQs; and `DescribeAlarms` for the 24 alarms. The metric windows are 24 h at 5-minute periods, and
  15 days at hourly periods for the daily and weekly rules.
  - Each section has its own `status` and `observed_at`, and a failed read gives null numbers, never 0.
  - Every client has an explicit botocore `Config` (connect 2 s, read 3 s, 2 attempts), and all four sections
    share one 6 s deadline. The backend Lambda's timeout is 15 s.
  - The DB session is closed before the first AWS call.
  - The response holds names, counts and states. It contains no ARN, account id or queue URL, and errors
    appear as AWS error codes only.
- **Rule liveness.**
  - `fresh`: the rule is ENABLED and its last **successful** delivery (Invocations − FailedInvocations > 0)
    is within the existing 2 × interval / min 15 min bound.
  - `stale`: the rule is disabled, or no successful delivery is inside that bound.
  - **New value `failing`:** the newest attempt failed, a failure falls inside the bound, or the rule's
    alarm is in ALARM.
  - Why `failing` is needed: EventBridge counts a failed delivery as an invocation, and the
    FailedInvocations alarm returns to OK after 5 minutes.
  - A fresh reason says it is **delivery only**. EventBridge invokes the worker asynchronously, and handler
    failures are worker-wide (`blogWorkerLambda-errors`, `worker-cron-dlq`), not per rule.
- **Applied (2026-10-13, owner-authorized in session).** A full plan gave 1 to add, 0 to change and 0 to destroy, with
  no drift. The IAM simulator allows the four read actions on the backend role and still denies `events:PutRule`.
  On the prod page the owner saw blogSQS and both DLQs, the three Lambdas' 24 h counts, and all 24 alarms read
  (`OK 24 · 경보 0`). So the batched `DescribeAlarms` call is authorized under ARN scoping, which the reviewer had
  flagged as a risk.
  - Scheduler rows (F) stay unknown: they are outside the grant. SQS message rows stay unknown: SQS keeps
    no per-message history.
- **IAM** (`backend_automation_read`, inline on `myblog-prod-lambda-role`). It is read-only:
  - `events:DescribeRule` on the 18 rule ARNs.
  - `cloudwatch:DescribeAlarms` on the 24 alarm ARNs.
  - `sqs:GetQueueAttributes` on the 3 queue ARNs.
  - `cloudwatch:GetMetricData` on `*`, because its only resource type is `dataset`.

  `events:ListRules` and `cloudwatch:GetMetricStatistics` from the original proposal are **not** used:
  ListRules can only be granted on `*`, and the batched GetMetricData replaces GetMetricStatistics. Resource
  support was checked against AWS's Service Reference JSON.
  - **Full `terraform plan`:** 1 to add, 0 to change, 0 to destroy, with no drift.
  - The plan's rule, alarm and queue lists equal the catalog's (checked programmatically).
  - **Apply is the owner's.** Until then prod shows the `aws` source as unavailable (AccessDenied) and
    every AWS row as unknown. `iam simulate-principal-policy` on the role returns `implicitDeny` for now and
    is the post-apply check.
- **Review.**
  - `reviewer` found one blocking bug: a weekly or daily rule read `fresh` 24 h after a failed delivery.
    It was fixed with regression tests and re-reviewed ✅.
  - The reviewer then suggested that `failing` mean "failing now", not "any failure in 24 h". One
    transient failure would otherwise keep a 5-minute rule red for a day. Taken.
  - `security-review`: no findings.
- **Route decision revisited (design-notes trigger).** The response now carries more than identifiers:
  queue depths, Lambda error counts and alarm states. The decision is **kept: catch-all + in-Lambda
  `require_owner`**.
  - These are operational numbers, no more sensitive than the DB queue counts the page already showed.
  - They hold no credentials or member data.
  - A JWT route would still only prove "a valid pool token", which members also hold.
  - Both reviews found no exposure.
- **Verification.**
  - Tests: backend 1072 unit tests and all required checks green; front 1450 tests.
  - Mutation: backend 33/33 and front 9/9 mutants killed.
  - **Local smoke at `5c645ef`** (prod DB read-only, AWS as `claude_aws_manager`, 03:33 UTC):
    - `200` in 2.9 s, with all four sources `ok`.
    - 19 jobs fresh: the 18 EventBridge rules and the GPT worker.
    - Queues 0/0/0, Lambda errors 0, 24 alarms OK.
  - Real-browser walkthrough of the front at 1440 px and 390 px.
  - **Prod smoke after deploy:** `smoke.sh prod` passed 30/0. On `/api/admin/automation`, no token gives
    401, a member gives 403, and the raw API GW gives 403 (quoted on #183).
- **Observed, not acted on:** during the session the GPT worker's heartbeat reported `error
  OperationalError`. That coincided with a window in which this Mac's Neon handshake timed out, while prod
  Lambdas logged 0 DB errors. It is left to the owner with the other GPT worker items.
- **Step 2 is complete in code once front #459 merges.** AWS rows become observable in prod after the
  owner's `terraform apply`. Step 3 (controls) still needs separate approval.

**Design notes fixed for 2a–2e**

- **Route (decided in 2b's security-review, not here):** functionally, a read-only owner GET needs no
  `infra/apigateway.tf` route. It can ride the edge_guard GET catch-all and be owner-gated in-Lambda by
  `require_owner`, as `GET /api/todays-pick/queue` and `GET /api/me/reratings` do. Through CloudFront an
  unauthenticated caller then gets 401 "Missing token" from the Cognito guard. On the raw API Gateway
  host the `edge_guard` fallthrough answers 403 "Forbidden". Both fail closed. The same file has the
  opposite precedent for sensitive owner reads: `spotify-library/state`, `playback/spotify-token` and
  `lyrics_get` each have their own JWT route as defence in depth. This page exposes operational detail
  but no credentials, so the catch-all is the default; 2b's security-review must weigh it explicitly.
  The acceptance criterion "unauthenticated → 401" is checked through CloudFront.
  **Decided in 2b (security-review, 2026-10-12): catch-all + in-Lambda `require_owner`, no apigateway
  route.** A JWT route's authorizer only proves "valid pool token", which self-signup members also hold,
  so the owner/member boundary is `require_owner` either way; the guard-downgrade regression is pinned by
  backend `tests/test_route_guard_map.py`. **Revisit when** Step 3 adds controls (mutations need routes
  regardless) or 2d puts anything beyond AWS resource identifiers in the response. *Revisited in 2d
  (2026-10-13): kept — see the 2d result. Step 3's trigger still stands.*
- **Heartbeat shape (2a):** one row per agent, upserted in place with `observed_at = now()` on the DB
  side. No history, so OQ3 retention does not arise for this table. Writer contract for 2e:
  - `agent_key` is the **short** label with `com.myblog.` removed (e.g. `gpt-translate-poller`). The
    full launchd label has dots, which the key CHECK rejects.
  - Writers truncate `last_outcome` to 200 characters.
  - `details` is a JSON object whose **stored** size is capped at 8 KB (`pg_column_size`, which is
    not the JSON text length), so writers keep it far smaller. It must never hold credentials, tokens or
    member data.
  - A rejected write leaves the row stale while the agent runs. That fails safe (the page shows
    unknown), but writers log the rejection so it can be found.
- **Staleness (OQ3, recommendation taken):** a heartbeat is stale after **2 × the agent's schedule
  interval, minimum 15 minutes**. A daily agent is therefore stale after 48 h. The thresholds live in
  the static catalog, next to each schedule.

### Step 3 — Add supported operational controls

Add per-job manual run, pause/resume and retry only after the underlying adapter supports
their semantics. Make actions idempotent, auditable and scoped; preserve manual priority,
deduplication and existing result-write guards. Clarify in-flight behavior for each executor.

**Verification**: Repeated clicks do not duplicate work; pause boundaries are observable;
retry does not overwrite newer/manual results; unauthorized requests fail closed; complete
service checks, browser walkthrough and production smoke for the approved rollout scope.

**Rollback**: Disable the control endpoints first, retain status visibility and audit history,
and reconcile any already-started work before reverting execution adapters.

#### Step 3 split (owner-approved 2026-10-13)

Each executor offers a different control point, so Step 3 is split by control, one sub-step per session.

| Sub-step | Control | Executors | Needs |
|---|---|---|---|
| **3b** (first) | Pause / resume, plus the audit + idempotency base every later control reuses | the 16 worker crons (table A minus the two warm pings) and `gpt-translate-poller` | V60, worker, GPT worker reinstall, backend, contract, one `infra/apigateway.tf` route (`apply`), front |
| **3c** | Run now | the worker crons, through `lambda:InvokeFunction` on `blogWorkerLambda` only | a mutating IAM grant + `apply`; a per-job cooldown; it competes with the account's 10 concurrent Lambda executions |
| **3a** (deferred) | Retry | DB queues | a retry-limit policy first (OQ3) — see below |

**Why retry was demoted from first (measured 2026-10-13, prod, `BEGIN READ ONLY … ROLLBACK`).**

- The GPT queues hold 7 waiting rows, **all at `attempts = 2`**: 4 `temporary_error` and 3 `output_limit`.
  None is backing off, because a `temporary_error` backs off only 10 minutes
  (`gpt_translation_store.fail`). So a "retry now" that advances `next_attempt_at` would change **0 rows**.
- Rearming a row at the cap means overriding `MAX_ATTEMPTS = 2`. That is OQ3's retry-limit policy, not a
  button. Resetting `attempts` would also refund the day's budget, because admission sums today's
  `attempts`.
- The album queues back off for long periods: 856 jobs at `album_not_in_catalog` for up to 24 h, and
  2,409 tracks at `not_found` for up to 30 days. These causes are structural, so advancing them would mostly
  repeat the same result. For tracks it would also mean a mass re-query of LRCLIB (~2.5 req/s).
- Pause is the control the owner set as a design constraint on 2026-10-06 ("continuous monitoring with
  manual stopping"). Today stopping requires the Mac's setup screen (GPT) or the console/Terraform (crons).

#### 3b design

**Semantics.** Pause means *stop starting new runs at the executor's next boundary*. Resume clears it.
Nothing is cancelled.

- **Worker crons.** The check sits at the top of `lambda_handler`, for top-level events only (EventBridge, or a
  direct invoke). It maps an event to its catalog key: `job`, plus `mode` for `release_upcoming_poll` and
  `spotify_saved_tracks_sync`; `source = aws.events` maps to `musicbrainz_alias_fill`. A run already
  executing finishes. **SQS messages of the same job type are not paused**, because they are user or owner
  actions (for example "지금 새로고침"). The page says so. **The one exception is `lyrics_incremental`:** the
  worker enqueues it itself after every album sync, so exempting it would make the pause a no-op while the page
  reads "confirmed". Its SQS branch honours the pause too. A skipped pass is harmless, because the cron
  catches up after resume.
- **GPT worker.** The DB flag joins the worker's existing hold check, which runs every tick and before each
  inference. An inference already streaming finishes and saves. A claim taken but not yet inferred is
  released with its attempt refunded (`claim_released`), **never `user_cancelled`**: on this worker that
  reason is terminal, and a site pause must not permanently stop a source. The local `settings.json`
  switches keep working unchanged.
- **The pause boundary is observable.** When a consumer skips because of the pause, it writes
  `honored_at = now()` on the control row, using one `UPDATE … WHERE paused RETURNING` in its own short
  transaction. That single statement both checks and stamps. **"Confirmed" means `honored_at >= changed_at`**,
  so a stamp left over from an earlier pause does not count.
  - The page shows "paused, last skip HH:MM" or "paused, not yet confirmed by the executor". It warns about
    "not yet confirmed" only after one schedule interval has passed since `changed_at`, so a weekly cron does
    not warn for a week.
  - The GPT worker reads the flag only when its local switch is on and it is not in a usage-limit wait. A
    disabled worker therefore never confirms a pause, and the page reads that together with the heartbeat's
    `enabled`.
- **Keys live in one place.** `myblog_shared_db.automation.PAUSABLE_JOB_KEYS` (V60) is the list of pausable
  keys. The backend tests that the catalog's `pause` rows equal it, and the worker tests that its
  `(job, mode)` mapping (using the handler's own `mode` defaults) covers exactly its cron subset.
- **A read failure means proceed (fail-open), with an `ERROR` log.** Pause is an operational control, not
  an auth boundary. Failing closed would let a DB blip, or a missing V60, silently stop all 16 crons. A
  pause that failed to apply stays visible, because `honored_at` does not advance.

**Schema (V60, additive).**

- `automation_controls`: `job_key` PK (`^[a-z0-9][a-z0-9_-]{0,63}$`; catalog keys use both `_` and `-`),
  `paused` (default false), `changed_at`, `honored_at`. One row per controlled job, created on first use.
- `automation_control_events` (the audit trail): `request_id` primary key, `job_key`, `action`
  (`pause`/`resume`), `outcome` (`applied`/`no_change`), `actor_sub`, `created_at`. **Kept indefinitely**
  (OQ3 retention): one small row per owner action. The action and outcome CHECKs stay narrow. 3c widens them
  in its own migration, together with the requested → invoked → completed columns that an external invoke
  needs.
- `actor_sub` is the verified JWT `sub`. Under `ENV=local|dev`, `require_owner` returns no claims, so the
  backend records the existing single-owner sentinel (`authz.resolve_owner`). That is a value, not a new
  bypass.

**Endpoint.** `POST /api/admin/automation/controls` with `{job_key, action, request_id}`, gated by
`require_owner` and given its own JWT route in `infra/apigateway.tf` (the 2b route decision's Step 3
trigger: mutations always get a route).

- Idempotency is two-layered:
  - The client mints one `request_id` per confirmation dialog, so a double click or a network retry replays
    the stored result instead of acting twice. Reusing a `request_id` with a different job or action is a
    409.
  - The action itself is idempotent: pausing a paused job records `no_change`.
- **Transaction order** (one short transaction, with every transaction taking the locks in the same order,
  so no deadlock cycle is possible):
  1. Upsert and lock the control row: `INSERT … ON CONFLICT (job_key) DO UPDATE SET job_key = EXCLUDED.job_key
     RETURNING …`.
  2. Compute the outcome from the locked row.
  3. `INSERT` the event with `ON CONFLICT (request_id) DO NOTHING RETURNING`.
  4. If no row comes back, the `request_id` was already used. Roll back and read the stored event. When its
     job and action match, it is a replay: return the stored outcome with the **current** state, and never
     act again (an old pause replayed after a resume does not pause). Otherwise return 409.
  5. Otherwise update the flag (and `changed_at`, only when `applied`) and commit.

  This is tested against a real engine with two connections; a mock cannot see the race.
- **3c interaction (decided now):** run-now on a paused job is rejected with 409 by the backend, so the worker
  needs no force flag.
- Only catalog keys with `controls` containing `pause` are accepted. A member gets 403 for any body.
- The snapshot gains a `control` block per controllable job (`paused`, `changed_at`, `honored_at`).

**Rollout order: consumers before the producer**, so a button never exists before it is honoured:
workspace `schema.sql` → shared_db V60 (prod + test branch before merge) → worker + its shared_db pin
(requirements and the CI canonical-schema ref) → GPT worker (reinstall) → backend + pin → workspace contract
+ route (`apply`) → front.

**Rollback.** Resume everything first, because executors keep honouring a flag after the UI is gone, and a
backend revert for an unrelated reason would leave no button:
`UPDATE automation_controls SET paused = false, changed_at = now() WHERE paused;`
Then remove the route and the button. The flags and the audit trail stay.

## Open questions

1. **Coverage and tooling** — *Answered by Step 1 (2026-10-12):* the catalog is tables A–F, and the
   approach is site-native aggregation (static catalog + AWS/DB read adapters + local heartbeat), with no
   queue/dashboard library. The Scheduler/bus check (F) was resolved the same day, and Step 2 was
   approved as sub-steps 2a–2e (2f added after 2c).
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
| 2026-10-12 | Owner approved Step 2 as sub-steps 2a–2e (one per session) and granted `claude_aws_manager` read access to Scheduler/event buses; F resolved. Stale threshold = 2 × interval, min 15 min. Status stays draft. | Step 2 |
| 2026-10-12 | After opening the 2c page on prod, owner chose the B+C layout (흐름/표 switch + shared detail panel) in two stages: front rework now (#457), queue detail API as new sub-step 2f. Ordering of 2d/2e/2f left to the owner (recommended 2f → 2e → 2d). Status stays draft. | Step 2 (2c, 2f) |
| 2026-10-12 | Owner picked 2f as the next sub-step; shipped the same day (backend #182, ws #1050, front #458). 2e/2d remain, owner picks (recommended 2e → 2d). Status stays draft. | Step 2 (2f) |
| 2026-10-13 | Owner picked 2d, with AWS state as a structured contract block plus a front panel in the same sub-step (backend #183, front #459). New liveness value `failing`. Route decision revisited and kept. IAM apply is the owner's. Status stays draft. | Step 2 (2d) |
| 2026-10-13 | Owner authorized Claude to run the 2d `terraform apply` in session; applied from a full plan (1 add). Step 2 complete. Status stays draft; Step 3 needs separate approval. | Step 2 (2d) |
| 2026-10-13 | Owner approved Step 3, split by control (retry / pause-resume / run now). A prod read the same session showed retry would change 0 rows today, so the owner moved **3b (pause/resume + audit base) first**; 3a is deferred behind OQ3's retry-limit policy. Audit history is kept indefinitely. Status stays draft. | Step 3 |
