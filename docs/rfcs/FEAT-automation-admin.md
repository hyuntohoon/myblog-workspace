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

- This registration does not authorize implementation, deployment or enabling any job.
- Moving every job into Work Cloud or replacing all queues with a new framework.
- Introducing a separately billed model API as a prerequisite.
- Automatically publishing generated reviews or changing existing content permissions.

## Current state

Preliminary code discovery found multiple independent execution paths; the inventory and
live-state audit are incomplete. Source configuration is not proof of deployment or execution.

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

1. **Coverage and tooling** — Step 1 must establish the complete catalog and the smallest
   useful first release; no queue/dashboard library has been selected.
2. **Cloud model controls** — Verify event-run model selection/persistence and what the
   site can observe or change. Blocks that control, not the read-only page.
3. **Operational policy** — Decide history retention, stale thresholds, optional budgets
   and retry limits before the affected implementation. No daily ten-run cap is assumed.

## Decisions log

| Date | Decision | Step |
|---|---|---|
| 2026-10-06 | Owner requested task registration in plan and RFC only; keep draft/backlog, with no implementation or runtime changes. | Registration |
| 2026-10-06 | Continuous monitoring with manual stopping is acceptable; self-unsubscription is not a production requirement. | Design constraint |
