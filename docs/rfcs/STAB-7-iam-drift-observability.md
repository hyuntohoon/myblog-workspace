# STAB-7: IAM least-privilege + IaC drift-visibility + observability (necessity-gated)

- **Status**: draft
- **Owner**: TBD (주인장)
- **Created**: 2026-06-05
- **Plan row**: `plan.md` → STAB-7
- **Spawned from**: `STAB-1-stabilization.md` §Prioritization & stabilization sequencing **item 7** (P7 IAM trims, P4 drift-blindness, P5 observability). STAB-1 stays `draft`; this RFC is `draft` (accept = human-only).

> **This tier is explicitly necessity-gated** ([[feedback-necessity-gate-reviews]]). STAB-1 ranks it lowest, behind P0/P1/section/hygiene. Each item below states whether there is **concrete harm if unfixed**; default for the no-clear-harm items is **leave alone**. Adopt a change only when the harm is nameable. "Mostly fine, do only P7-5 + the cheap drift imports" is a valid outcome.

## Goal

Trim the one live over-privileged IAM grant, make the security-relevant console-created resources visible to `terraform plan`, and decide (gated on a measured latency baseline) whether any observability is worth adding. After this RFC the account has no account-wide SQS-consume grant on a producer-only Lambda, IaC `plan` no longer silently ignores the bucket policy / CF function / WAF, and the latency-blindness question is settled with data.

## Non-goals

- No app behavior change; no new always-on cost without a measured justification (the $0/Free-plan ethos stands).
- Not adopting X-Ray/EMF unless the Duration p99 baseline shows a real tail (P5 is signal-gated).
- Not the REST+OAC migration (P4-1 is an accepted website-endpoint tradeoff; this RFC only adds drift-visibility, not a redesign).
- No caching (out of scope per STAB-1).

## Evidence gathered (2026-06-05 — authoritative)

| ID | Item | Verified | Harm-if-unfixed |
|----|------|----------|-----------------|
| **P7-5** | music role attaches `AWSLambdaSQSQueueExecutionRole` (account-wide `sqs:ReceiveMessage/DeleteMessage/GetQueueAttributes` on `*`) | `aws lambda list-event-source-mappings --function-name musicApi` = **[]** (no SQS consumer); music SQS client is send-only (`sqs_client.py`); the inline `music_sqs_produce` already covers the real need. | **Real (low-med):** a live, account-WIDE consume grant on a producer-only Lambda — a compromised musicApi could drain `blogSQS` (dropping worker jobs). **Worth fixing.** |
| **P7-1** | `music_rds_ctrl` allows `rds:Start/Stop/DescribeDBInstances` on `arn:…:db:blogdb` | `aws rds describe-db-instances` = **[]** (no RDS — Neon stack); `infra/README.md:45` already flags it removable. | **None today** (acts on a non-existent ARN). Optional cleanup / audit noise only. |
| **P7-3** | worker consume perms live in console policy `AWSLambdaBasicExecutionRole-976d757e-…` (attached by ARN, `iam_roles.tf:158-161`, no body in repo/tfstate) | Not re-fetched this pass; STAB-1 verified the attachment-by-ARN. | **Governance (med drift):** the worker's `ReceiveMessage/DeleteMessage` consume grant lives in a policy TF can't reproduce/audit; a console edit → silent consumer outage invisible to `plan`. |
| **P4-2/4-7/4-8** | bucket policy, WAF ACL, CF `handler` function, S3 versioning/logging all console-created, **plan-invisible** | STAB-1 verified against tfstate + live; `infra/README.md:43` already notes the CF function is out-of-IaC. | **Drift (low-med):** out-of-band change/deletion of the WAF rules or the SPA-routing CF function is invisible to `plan`/CI; deleting the function breaks site-wide deep-link routing. |
| **P5** | observability | `musicApi` Duration **p50 = 272 ms, p99 ≈ 3.65 s** (30d, free metric); zero custom metrics/EMF/X-Ray; alarms are failure-counts only. | **Signal-gated:** p99 ~3.65 s is well under the 15 s timeout — no acute tail today. Latency-blindness is a *future* risk (catalog growth + high `limit`, P5-1/3), not an active defect. |

## Current state

One account-wide live SQS-consume over-grant (P7-5), one dead RDS grant (P7-1), worker consume perms + WAF + CF function + bucket policy all outside Terraform (unauditable / plan-invisible), and zero latency instrumentation (failure-count alarms only).

## Target state

P7-5 removed; the plan-invisible security-relevant resources either imported into TF or explicitly documented as intentionally-external; and a settled, recorded decision on observability (likely "no change yet, re-check p99 quarterly with the scale noted" or at most one EMF line + a Duration alarm).

## Steps

Each step is independent; **adopt per the necessity gate**. IAM/infra steps need a full `terraform plan` (no `-target`, rule #6) + human `apply` ([[reference-prod-terraform-drift]], [[reference-workspace-no-infra-autoapply]]).

### Step 1 — Remove the music account-wide SQS-consume attachment (P7-5) — *recommended*
`infra/iam_roles.tf:79-82`: drop the `AWSLambdaSQSQueueExecutionRole` attachment from the music role (the inline `music_sqs_produce` already grants the send-only need). `plan` should show only that attachment removed.
**Verification:** `aws iam list-attached-role-policies` for the music role no longer lists it; musicApi `/candidates` enqueue still works (it's a `SendMessage`, covered by the inline `music_sqs_produce`); **CloudWatch logging is unaffected** — the managed policy bundles `logs:*` alongside the consume actions, but those `logs:*` are independently granted by the inline `music_rds_ctrl` policy (`iam_roles.tf:97-98`), so dropping the attachment strips only the unused account-wide consume grant (confirm `aws logs` still receives musicApi events post-apply); `plan` clean otherwise.
**Rollback:** re-attach + `apply`.

### Step 2 — Import plan-invisible security resources, or document them (P4-2/4-7/4-8, P7-3) — *recommended (cheap, high drift-value)*
Import into Terraform: `aws_s3_bucket_policy` (and remove the dead `AllowCloudFrontServicePrincipal` OAC statement), `aws_cloudfront_function.handler`, and (optionally) the WAF ACL; for the worker console policy `976d757e`, `aws iam get-policy-version` to audit it (confirm consume + logs scoped to `blogSQS`, no `Resource:'*'` over-grant) and decide import-vs-document. Where import is heavy, instead record them in `infra/README.md` §"Known out-of-IaC items" so `plan`-blindness is at least documented.
**Verification:** `terraform plan` now shows these resources (or `infra/README.md` lists each as intentionally-external with the audit result).

### Step 3 — Dead RDS grant (P7-1) — *optional*
Remove `music_rds_ctrl` `rds:Start/Stop/DescribeDBInstances` (acts on a phantom `blogdb`). Pure audit-noise cleanup; bundle with Step 1's `apply` if doing it at all.
**Verification:** `plan` shows only the policy deleted; `aws rds describe-db-instances` still empty.

### Step 4 — Observability decision (P5) — *signal-gated; default = no change*
Pull 30 days of `musicApi`/backend Duration p50/p99. **If** p99 is climbing toward the 15 s timeout, add the minimal upgrade: one EMF line per `unified_search` (wall-time + DB-statement-count) + a single Duration alarm. **Else** record "latency-blindness accepted at current scale" + **capture the scale the decision rests on** (catalog row counts — albums/artists/tracks — and the `limit` distribution at measurement time) so a quarterly re-check compares like-for-like rather than re-deciding from scratch ([[feedback-rfc-success-gate-denominator]]). (Today's p99 ≈ 3.65 s → likely the no-change branch.)
**Verification:** either a documented "no change, re-check date + measured-at scale" note, or the EMF line + Duration alarm live with a p99 baseline recorded.

## Open questions

1. **OQ1 (Step 2)** — import the WAF ACL + CF function into TF vs. document them as intentionally-external. Import gives plan-visibility; documenting is cheaper. *(Blocks Step 2 scope.)*
2. **OQ2 (Step 4)** — does the owner accept latency-blindness at current scale (p99 ≈ 3.65 s)? If yes, Step 4 is a one-line note. *(Blocks Step 4.)*

## Decisions log

| Date | Decision | Step |
|------|----------|------|
| 2026-06-05 | Spawned from STAB-1 §Sequencing item 7. **Necessity-gated** — recommended: P7-5 (Step 1) + drift imports (Step 2); optional: P7-1 (Step 3); signal-gated: P5 (Step 4, default no-change at p99 ≈ 3.65 s). | all |
| 2026-06-05 | Evidence: musicApi ESM empty (P7-5 over-grant live), `rds describe` empty (P7-1 dead), musicApi p99 ≈ 3.65 s (P5 no acute tail). | §Evidence |
