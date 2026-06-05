# STAB-3: blogSQS visibility timeout ≥ worker timeout

- **Status**: accepted
- **Owner**: TBD (주인장)
- **Created**: 2026-06-05
- **Plan row**: `plan.md` → STAB-3
- **Spawned from**: `STAB-1-stabilization.md` §Prioritization & stabilization sequencing **item 2** (P1-1). STAB-1 + this RFC are **accepted** (2026-06-05, owner-approved).

---

## Goal

Stop `blogSQS` messages from being redelivered (and picked up by a second concurrent worker) while a legitimate batch is still being processed, by raising the queue's `VisibilityTimeout` to be ≥ the worker Lambda timeout. After this RFC, a slow-but-correct album sync runs to completion once instead of being re-received mid-flight; the doubled Spotify volume and duplicate concurrent processing stop; and the path toward premature DLQ'ing of slow-but-correct batches is closed before it escalates to data loss.

## Non-goals

- Changing the queue type (it stays a standard queue; the FIFO conversion question is a separate doc-fix in STAB-4 / not pursued).
- Adding a DLQ redrive/replay consumer (P1-8 — observe-only DLQ is an accepted tradeoff; revisit only after this fix).
- Touching the DLQ's own visibility (P1-9 — it has no consumer, so its visibility is irrelevant; **scope the change to `blogSQS` only**).
- Worker code changes — consumer writes are already idempotent (`ON CONFLICT`), which is what kept redelivery from corrupting data (P1-4).

## Evidence gathered (2026-06-05, read-only — authoritative)

| Fact | Source | Value |
|------|--------|-------|
| `blogSQS` visibility | `aws sqs get-queue-attributes` | **`VisibilityTimeout=30`**; redrive → `album-sync-dlq` `maxReceiveCount=3`; retention 345600s (4d); currently 0/0 messages. |
| worker timeout | `aws lambda get-function-configuration --function-name blogWorkerLambda` | **`Timeout=120`** (s). |
| ESM | `aws lambda list-event-source-mappings --function-name blogWorkerLambda` | `BatchSize=10`, `MaximumBatchingWindowInSeconds=0`, **`ScalingConfig=null`** (no max-concurrency cap), `FunctionResponseTypes=[ReportBatchItemFailures]`, Enabled. |
| worker Duration (30d) | CloudWatch `AWS/Lambda Duration` | p99 ≈ **112,342 ms**, p100 = **120,000 ms** (hits the 120s timeout) in one period; ≈10 s in another. Routinely **> 30 s**. |
| redelivery signature | CloudWatch `AWS/SQS` (30d, Sum) | `NumberOfMessagesReceived=126` vs `NumberOfMessagesDeleted=55` → **2.3× divergence** (received-before-delete). |
| concurrent processing | CloudWatch `ConcurrentExecutions` (30d) | worker max = **4**. |
| actual loss so far | CloudWatch `album-sync-dlq NumberOfMessagesSent` (30d) | **0** — no message has actually been DLQ'd yet. |

> Interpretation: redelivery + duplicate concurrent processing are **live and ongoing** (126 vs 55, ConcurrentExecutions 4, Duration past 30 s), so the harm today is wasted/duplicate work and doubled Spotify volume (429 risk on the shared token). The worst case — a slow-but-correct batch hitting `maxReceiveCount=3` and being **dropped to the DLQ** — has **not** materialized yet (DLQ sent = 0). This fix removes the churn now and forecloses the data-loss escalation. Idempotent upserts (P1-4) prevent *corruption* but not the premature-redelivery harm.

## Current state

- `infra/sqs.tf` — `blogSQS` `visibility_timeout_seconds = 30`; redrive policy → `album-sync-dlq`, `maxReceiveCount = 3`. The DLQ also has visibility 30 (irrelevant — no consumer).
- `infra/lambda.tf` — `blogWorkerLambda` `timeout = 120`.
- A single SQS receive can hold `BatchSize=10` messages × up to 20 album ids = up to 200 albums; chunked Spotify calls (20/call, 20 s httpx timeout) + per-50-artist enrich easily exceed 30 s wall time, so the message reappears mid-processing.

## Target state

- `blogSQS` `visibility_timeout_seconds` raised to **≥ the worker timeout**, following AWS guidance of roughly **6× the function timeout** ⇒ **720 s** (12 min). This sits comfortably under the message retention (4 d) and gives slow batches headroom without making a genuinely-stuck message linger too long before its `maxReceiveCount` retries play out. Accepted tradeoff of the 6× margin (vs. the 120 s minimum): with `maxReceiveCount=3` unchanged, a *genuinely* poisoned message now takes up to ~36 min (3 × 720 s) instead of ~90 s to reach the DLQ — still far under the 4-day retention, so nothing expires unprocessed.
- `album-sync-dlq` visibility unchanged (out of scope).
- No worker code change.

## Steps

### Step 1 — Raise `blogSQS` visibility to 720 s

`infra/sqs.tf`: `visibility_timeout_seconds = 30` → `720` on `blogSQS` only. Full `terraform plan` (no `-target`, rule #6), human-run `apply` (no auto-apply, `reference-workspace-no-infra-autoapply`); stop on any unexpected drift. Update `infra/README.md` if it records the value.

**Verification:**
```
# plan shows ONLY blogSQS visibility 30 -> 720, nothing else
# (sqs.tf's lifecycle{ ignore_changes } is scoped to max_message_size, so
#  visibility_timeout_seconds is plan-visible and the diff is clean)
terraform -chdir=infra plan
# post-apply
aws sqs get-queue-attributes --region ap-northeast-2 \
  --queue-url https://sqs.ap-northeast-2.amazonaws.com/338183196042/blogSQS \
  --attribute-names VisibilityTimeout   # expect "720"
```
**Post-fix observation (the one-RFC-step gate):** after apply, watch a window of real album-sync traffic and confirm `NumberOfMessagesReceived` converges toward `NumberOfMessagesDeleted` and `ConcurrentExecutions` for a single logical batch drops to 1. DLQ `NumberOfMessagesSent` should stay 0.

**Rollback:** revert to `30` and `terraform apply`. Trivial and safe (raising visibility is non-destructive; lowering it back simply restores the prior, churn-prone behavior).

## Open questions

1. **Value choice** — 720 s (6× rule) vs. exactly 120 s (= timeout, minimal). 6× is the AWS-recommended safety margin against the receive→process→delete race at the ESM layer; 120 s is the bare minimum. Default = **720 s**. *(Blocks Step 1 value only.)*

## Decisions log

| Date | Decision | Step |
|------|----------|------|
| 2026-06-05 | Spawned from STAB-1 §Sequencing item 2. Scope = `blogSQS` visibility only; DLQ untouched (P1-9); no worker code change (idempotent, P1-4). | Step 1 |
| 2026-06-05 | Evidence confirmed redelivery is **live** (126 vs 55, ConcurrentExecutions 4, Duration to 120 s) but no DLQ loss yet (sent=0). | §Evidence |
| 2026-06-05 | **DONE + applied.** ws#256 merged + `terraform apply` (0 add / 1 change / 0 destroy). Live `blogSQS VisibilityTimeout = 720` (was 30). plan.md row dropped — git log + this RFC are authoritative. | Step 1 |
