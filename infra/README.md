# Infrastructure facts

Source of truth: Terraform state. **STAB-6 Step 5 (in progress):** state is migrating from the local-only `infra/terraform.tfstate` to an S3 backend (`myblog-terraform-state-338183196042`, key `infra/terraform.tfstate`, region `ap-northeast-2`) with a DynamoDB lock table (`myblog-terraform-locks`) — see `docs/rfcs/STAB-6-repo-hygiene-tfstate.md` §Step 5. Until the `backend "s3"` block in `main.tf` is uncommented + `terraform init -migrate-state` is run, the local file is still canonical. The values below are a human-readable mirror; if they disagree with `terraform show`, Terraform wins. Refresh this file after any `terraform apply` that adds, replaces, or renames a resource.

| Resource | Identifier |
|----------|------------|
| AWS region | `ap-northeast-2` (Seoul); Neon in `ap-southeast-1` (separate by design — Neon Free-tier availability) |
| API Gateway | `lambdaAPI` (HTTP API ID: `ld8pjw3mx4`) — 10 routes (see `infra/apigateway.tf`); Cognito-backed JWT authorizer |
| Cognito | `MyBlogAdminPool` (Pool ID: `ap-northeast-2_54vEJKEU5`, SPA Client ID: `68ccmcanfbvla9qbovnb9b18bt`) |
| Cognito hosted UI domain | `ap-northeast-254vejkeu5.auth.ap-northeast-2.amazoncognito.com` |
| SQS | `blogSQS` + DLQ via redrive policy; consumer uses `ReportBatchItemFailures` |
| S3 bucket | `myblog-prod-web` |
| CloudFront | `d2y4n52sgjlrz6.cloudfront.net` → `www.ratemymusic.blog` |
| Neon DB | Serverless Postgres; pooler URL stored in each service's Secrets Manager entry |
| Secrets | `myblog/backend`, `myblog/music`, `myblog/worker` (one per service; `SECRETS_ARN` env var; fetched once per cold start via `@lru_cache`). Plus `myblog/spotify` — Spotify user OAuth client_id/secret + refresh_token (`SPOTIFY_SECRETS_ARN`; read by worker for `/me/player/*`, by backend for connection status). |
| EventBridge | `rate(15 min)` → `blogWorkerLambda` (alias mode — MusicBrainz lookup). `rate(1 hour)` → `blogWorkerLambda` with constant input `{"job":"spotify_listening"}` (Spotify recently-played + now-playing cache, FEAT-member-dashboard Step 3). |

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

## CloudWatch

- Log retention: 14 days (all four Lambdas)
- Alarms: Lambda errors, throttles, DLQ depth (9 alarms total, added in IAC-1)

## Known out-of-IaC items

These exist in AWS but are **not managed by Terraform** → `terraform plan` is blind to out-of-band changes or deletion of them. STAB-7 Step 2 chose to **document** them here rather than `terraform import` (import is apply-class / heavier than the drift-value warrants at this scale). Track in `plan.md` if remediation is planned.

- **CloudFront `handler` function** — JS code defined in console, not Terraform. Deleting it breaks site-wide deep-link routing (Astro `uri → uri + '/index.html'` rewrite). High-value to guard; not yet imported.
- **S3 bucket policy** on the web bucket (`myblog-prod-web`) — console-created; still carries a dead `AllowCloudFrontServicePrincipal` OAC statement (the distribution serves the bucket's website endpoint, not via OAC).
- **WAFv2 Web ACL** (CloudFront scope) — console-created; its rules are invisible to `plan`. (It cannot be attached to the HTTP API in any case — WAFv2 does not support API Gateway v2; see `reference-waf-http-api-invoke-domain`.)
- **S3 versioning / access logging** on the web bucket — console-set, not in Terraform.
- **Worker console policy** `AWSLambdaBasicExecutionRole-976d757e-…` — attached by ARN (`iam_roles.tf` `worker_basic_exec`), policy body not in repo or state. It carries the worker's real `blogSQS` consume grant, so a console edit could cause a silent consumer outage invisible to `plan`. Audit with `aws iam get-policy-version` before relying on `plan` for the worker's SQS perms.

> The 3 Lambda execution roles (backend/music/worker) are managed in `infra/iam_roles.tf`. **STAB-7** dropped the music role's account-wide `AWSLambdaSQSQueueExecutionRole` attachment (P7-5 over-grant — `musicApi` is producer-only) and the dead `music_rds_ctrl` `rds:Start/Stop/DescribeDBInstances` grant on the phantom `db:blogdb` (P7-1; Neon is the DB). `music_rds_ctrl` is now logs-only. Both land via the STAB-7 `terraform apply`.
