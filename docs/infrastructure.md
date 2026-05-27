# Infrastructure — Concrete Resources

Concrete resource identifiers used across the system. Update this file whenever a resource is created, replaced, or destroyed. Architecture intent lives in `architecture.md`; this file is just the current values.

> **Source of truth**: For anything managed by Terraform, the running state in `infra/terraform.tfstate` is authoritative. This document is a human-readable mirror; if it disagrees with `terraform show`, Terraform wins. Refresh this file after any `terraform apply` that adds, replaces, or renames resources.

---

## AWS Region

- Primary: `ap-northeast-2` (Seoul)
- Neon DB: `ap-southeast-1` (Singapore) — separate from AWS region by design (Neon Free tier availability)

---

## Lambda Functions

| Function | Runtime | Timeout | Trigger |
|----------|---------|---------|---------|
| `ratemymusic-api` | Python | 15s | API Gateway |
| `musicApi` | Python | 15s | API Gateway |
| `blogWorkerLambda` | Python | 120s | SQS + EventBridge |
| `publisher-github` | Python | 15s | API Gateway |
| `handler` (CloudFront function) | JS | — | CloudFront viewer-request |

All settings managed by Terraform. To inspect:

```
aws lambda get-function-configuration --function-name <name>
```

---

## API Gateway

- HTTP API: `lambdaAPI` (ID: `ld8pjw3mx4`)
- Routes: 6 (posts CRUD, categories, music search, publish)
- JWT authorizer: Cognito-backed

---

## Cognito

- User Pool: `MyBlogAdminPool`
- Pool ID: `ap-northeast-2_54vEJKEU5`
- Used by: `myblog_backend`, `myblog_music`, `myblog_front`

---

## SQS

- Main queue: `blogSQS`
- DLQ: configured via redrive policy
- Lambda event source: `ReportBatchItemFailures` enabled

---

## S3 + CloudFront

- Bucket: `myblog-prod-web`
- Distribution domain: `d2y4n52sgjlrz6.cloudfront.net`
- Custom domain: `www.ratemymusic.blog`
- CloudFront function: rewrites `uri` → `uri + '/index.html'` for Astro directory build output

---

## Database (Neon)

- Provider: Neon (serverless Postgres)
- Region: `ap-southeast-1`
- Connection: pooler URL stored in each service's Secrets Manager entry
- Migration history: per-service `db/migrations/` directories

---

## AWS Secrets Manager

| Secret name | Consumed by |
|-------------|-------------|
| `myblog/backend` | `ratemymusic-api` |
| `myblog/music` | `musicApi` |
| `myblog/worker` | `blogWorkerLambda` |
| `myblog/publish` | `publisher-github` |

Each Lambda receives `SECRETS_ARN` as an env var; `get_settings()` fetches once per cold start via `@lru_cache`. No plaintext secrets in Lambda environment variables.

---

## EventBridge

| Rule | Schedule | Target | Purpose |
|------|----------|--------|---------|
| Gemini alias generation | `rate(15 min)` | `blogWorkerLambda` (alias mode) | Backfill artist aliases; no-op if `GEMINI_API_KEY` missing in `myblog/worker` secret |

---

## CloudWatch

- Log retention: 14 days (all four Lambdas)
- Alarms: Lambda errors, throttles, DLQ depth (9 alarms total, added in IAC-1)

---

## Known Out-of-IaC Items

These exist in AWS but are not managed by Terraform yet. Track in `plan.md` if remediation is planned.

- **IAM execution roles** (4 Lambdas) — referenced by name in Terraform but defined manually. `LambdaRDSControlRole` carries unused `AmazonRDSFullAccess` (legacy, predates Neon migration).
- **`publisher-github` Function URL** — public, `AuthType: NONE`. Bypasses API Gateway / JWT. Security review pending.
- **CloudFront `handler` function** — code defined in console, not Terraform.
