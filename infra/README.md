# Infrastructure facts

Source of truth: Terraform state in **S3** (`myblog-terraform-state-338183196042`, key `infra/terraform.tfstate`, region `ap-northeast-2`, versioned + AES256 + public-access-blocked) — migrated 2026-06-06 (STAB-6 Step 5). **S3-only, no DynamoDB state lock** (owner decision: single-author, no auto-apply → lock value low; `claude_aws_manager` also lacks `dynamodb:CreateTable`). The old local `infra/terraform.tfstate` is now a stale backup. The values below are a human-readable mirror; if they disagree with `terraform show`, Terraform wins. Refresh this file after any `terraform apply` that adds, replaces, or renames a resource.

**Recurring gotchas (FIX-bug-audit-2026-07 WS-F):**

- **DLQ alarms must use `ApproximateNumberOfMessagesVisible`, not `NumberOfMessagesSent`.** AWS does not increment `NumberOfMessagesSent` for messages moved to a DLQ by a redrive policy — and redrive is the only way messages enter these DLQs. A `NumberOfMessagesSent` alarm can never fire (`monitoring.tf`).
- **The `myblog-prod-web` public-read bucket policy is now Terraform-managed** (`s3.tf`, imported from the console) — do not delete it console-side thinking it's unmanaged.
- **This distribution is on the CloudFront Free pricing plan.** Custom cache policies AND custom response-headers policies are Business-tier — both rejected at apply. Security response headers (HSTS/CSP/XFO) therefore need a viewer-response CloudFront **Function**, not a response-headers policy (deferred).
- The `researchSQS`/`researchWorkerLambda` stack was torn down (WS-G) — research runs `$0`/local-poller.

| Resource | Identifier |
|----------|------------|
| AWS region | `ap-northeast-2` (Seoul); Neon in `ap-southeast-1` (separate by design — Neon Free-tier availability) |
| API Gateway | `lambdaAPI` (HTTP API ID: `ld8pjw3mx4`) — **49 route resources** (2026-07-27: +`POST /api/buckets/nightly-grow`; ~40 authed mutation routes carry the Cognito authorizer, count per 2026-07-23 audit, see `infra/apigateway.tf`); Cognito-backed JWT authorizer |
| Cognito | `MyBlogAdminPool` (Pool ID: `ap-northeast-2_54vEJKEU5`, SPA Client ID: `68ccmcanfbvla9qbovnb9b18bt`) |
| Cognito hosted UI domain | `ap-northeast-254vejkeu5.auth.ap-northeast-2.amazoncognito.com` |
| SQS | `blogSQS` + DLQ via redrive policy; consumer uses `ReportBatchItemFailures` |
| S3 bucket | `myblog-prod-web` |
| CloudFront | `d2y4n52sgjlrz6.cloudfront.net` → `www.ratemymusic.blog` |
| Neon DB | Serverless Postgres; pooler URL stored in each service's SSM Parameter Store SecureString param |
| Secrets (SSM) | `/myblog/backend`, `/myblog/music`, `/myblog/worker` (one per service; SSM SecureString, leading slash; `SECRETS_PARAM` env var; fetched once per cold start via `@lru_cache`). Plus `/myblog/spotify` — Spotify user OAuth client_id/secret + refresh_token (`SPOTIFY_SECRETS_PARAM`; read by worker for `/me/player/*`, by backend for connection status), `/myblog/smoke` — the smoke user's Cognito credentials, and `/myblog/nightly-agent` — the nightly draft agent's Cognito credentials (see "Nightly draft agent" below). Secrets Manager emptied per CHORE-secrets-ssm-migration. |
| EventBridge | **13 rules (2026-07-23 audit — this table lists only 2 of them)**: alias 15m, spotify_listening 1h, lastfm 15m, member_poll 15m, release_mb 1h, release_itunes 30m, album_ingest daily, saved_tracks incremental/full, lyrics incremental 15m + reassessment daily, artist_photo weekly, backend_warm_ping 5m. Canonical list → `infra/eventbridge.tf`. |

## Lambda functions

| Function | Runtime | Service | Timeout | Trigger |
|----------|---------|---------|---------|---------|
| `ratemymusic-api` | Python | myblog_backend | 15s | API Gateway |
| `musicApi` | Python | myblog_music | 15s | API Gateway |
| `blogWorkerLambda` | Python | myblog_worker | 120s | SQS + EventBridge |
| `handler` (CloudFront function) | JS | — | — | CloudFront viewer-request (rewrites `uri` → `uri + '/index.html'` for Astro directory build) |

Inspect any config: `aws lambda get-function-configuration --function-name <name>`.

## Auth flow — two entry points

- **CloudFront → backend** (most routes): `edge_guard` middleware checks `x-origin-verify: <EDGE_SECRET>`. Bypassed when `ENV=local`/`dev`. Bearer-token requests pass through without `x-origin-verify` check.
- **API Gateway → backend** (`POST /api/posts`, `PUT /api/posts/{id}`, `DELETE /api/posts/{id}`, `POST /api/publish`): Cognito JWT validated at API Gateway authorizer (`6eia7l`) before reaching Lambda.

## Nightly draft agent (Cognito service identity)

The 03:00 Editor-Buckit job (`scripts/buckit_nightly.py`, launchd on the owner's machine)
authenticates as a dedicated Cognito user — **not** the owner, **not** the smoke user
(FIX-nightly-draft-identity, 2026-07-27).

| Fact | Value |
|---|---|
| Cognito user | `nightly-agent@ratemymusic.blog` in `MyBlogAdminPool` (created 2026-07-27 by CLI — **not in Terraform**, see out-of-IaC below) |
| sub | `64885d4c-00c1-7082-8c40-8cb1a31d8078` — mirrored in `infra/lambda.tf` `DRAFT_AGENT_SUB` |
| Credentials | SSM SecureString `/myblog/nightly-agent` (JSON keys `NIGHTLY_AGENT_EMAIL` / `NIGHTLY_AGENT_PASSWORD`) |
| Server-side rights | `require_owner_or_draft_agent` on exactly two routes: `POST /api/posts` (status **and** editorial fields coerced — draft-only, no album links / rating / BEST NEW) and `POST /api/buckets/nightly-grow` (acting user pinned to `OWNER_SUB` server-side). `require_owner` rejects it everywhere else; the member item PATCH 404s it (owns no buckets). |

Procedures (manual — the user and the parameter are out-of-IaC):

- **Rotate password**: `aws cognito-idp admin-set-user-password --user-pool-id ap-northeast-2_54vEJKEU5 --username nightly-agent@ratemymusic.blog --password '<new>' --permanent`, then update the SSM param JSON. No deploy needed — the script reads SSM on every run.
- **Kill switch**: `aws cognito-idp admin-disable-user` on the account (that night's delivery exits 3 at token mint; generation + `docs/buckit/` files are unaffected) — or unset `DRAFT_AGENT_SUB` on the backend Lambda (agent 403s → exit 2; an empty value never widens access).
- **Repoint after account replacement**: create the user → set a permanent password → update SSM → update `DRAFT_AGENT_SUB` in `infra/lambda.tf` + apply. NB an **owner**-account repoint must update both `infra/lambda.tf` `OWNER_SUB` *and* the `OWNER_SUB` constant in `scripts/buckit_nightly.py` (deliberate mirror; the script warns loudly when the filter excludes checked memos).
- **Run exits non-zero**: exit 2 = identity rejected (check the wiring above) · exit 3 = token mint / delivery infrastructure failure · exit 4 = draft created but its memo is still checked — recover with one `POST /api/buckets/nightly-grow {album_id, post_id}` using the post id from the run's `draft created: id=…` log line, or uncheck the memo in the UI.

## CloudWatch

- Log retention: 14 days (all four Lambdas)
- Alarms: Lambda errors, throttles, DLQ depth (9 alarms total, added in IAC-1)

## Known out-of-IaC items

These exist in AWS but are **not managed by Terraform** → `terraform plan` is blind to out-of-band changes or deletion of them. STAB-7 Step 2 chose to **document** them here rather than `terraform import` (import is apply-class / heavier than the drift-value warrants at this scale). Track in `plan.md` if remediation is planned.

- **CloudFront `handler` function** — JS code defined in console, not Terraform. Deleting it breaks site-wide deep-link routing (Astro `uri → uri + '/index.html'` rewrite). High-value to guard; not yet imported.
- **S3 bucket policy** on the web bucket (`myblog-prod-web`) — console-created; still carries a dead `AllowCloudFrontServicePrincipal` OAC statement (the distribution serves the bucket's website endpoint, not via OAC).
- **No WAF** (OPS-safety-net-drift Step 2, owner call 2026-07-28) — the console-created CloudFront ACL documented here until 07-28 had `RuleCount: 0` + default `Allow` (audit SEC-1): a control in name only, so it was deleted rather than kept as a false signal. Abuse exposure is bounded by Lambda reserved concurrency + the Cognito authorizer on every mutation route. Because any future ACL would again be console-created and invisible to `plan`, the check is manual: `aws wafv2 list-web-acls --scope CLOUDFRONT --region us-east-1` must return `[]` — and if it ever doesn't, the ACL must carry real rules (`RuleCount > 0`), not exist as an empty shell. (WAFv2 cannot attach to the HTTP API in any case — no API Gateway v2 support; see `reference-waf-http-api-invoke-domain`.)
- **S3 versioning / access logging** on the web bucket — console-set, not in Terraform.
- **Cognito user `nightly-agent@ratemymusic.blog` + SSM `/myblog/nightly-agent`** — created by CLI 2026-07-27 (FIX-nightly-draft-identity A-S1); see "Nightly draft agent" above. Deleting either silently breaks nightly draft delivery (the 03:00 run then exits 2/3 — loud in `launchctl list`, invisible to `terraform plan`).
- **Worker console policy** `AWSLambdaBasicExecutionRole-976d757e-…` — attached by ARN (`iam_roles.tf` `worker_basic_exec`), policy body not in repo or state. It carries the worker's real `blogSQS` consume grant, so a console edit could cause a silent consumer outage invisible to `plan`. Audit with `aws iam get-policy-version` before relying on `plan` for the worker's SQS perms.

> The 3 Lambda execution roles (backend/music/worker) are managed in `infra/iam_roles.tf`. **STAB-7** dropped the music role's account-wide `AWSLambdaSQSQueueExecutionRole` attachment (P7-5 over-grant — `musicApi` is producer-only) and the dead `music_rds_ctrl` `rds:Start/Stop/DescribeDBInstances` grant on the phantom `db:blogdb` (P7-1; Neon is the DB). `music_rds_ctrl` is now logs-only. Both land via the STAB-7 `terraform apply`.
