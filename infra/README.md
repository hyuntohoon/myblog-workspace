# Infrastructure facts

Source of truth: `infra/terraform.tfstate`. The values below are a human-readable mirror; if they disagree with `terraform show`, Terraform wins. Refresh this file after any `terraform apply` that adds, replaces, or renames a resource.

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

These exist in AWS but are not managed by Terraform yet. Track in `plan.md` if remediation is planned.

- **CloudFront `handler` function** — code defined in console, not Terraform.

> The 3 Lambda execution roles (backend/music/worker) are now managed in `infra/iam_roles.tf` (no longer manual), and `AmazonRDSFullAccess` was dropped. Residual dead grant: `music_rds_ctrl` still allows `rds:Start/Stop/DescribeDBInstances` on `db:blogdb` — a phantom AWS RDS instance that doesn't exist (Neon is the DB). Safe to remove in a future `iam_roles.tf` change (needs `terraform apply`).
