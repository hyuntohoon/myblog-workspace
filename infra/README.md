# Infrastructure facts

Source of truth: `infra/terraform.tfstate`. The values below are a human-readable mirror; if they disagree with `terraform show`, Terraform wins.

| Resource | Identifier |
|----------|------------|
| AWS region | `ap-northeast-2` (Seoul); Neon in `ap-southeast-1` |
| API Gateway | `lambdaAPI` (HTTP API ID: `ld8pjw3mx4`) |
| Cognito | `MyBlogAdminPool` (Pool ID: `ap-northeast-2_54vEJKEU5`, SPA Client ID: `68ccmcanfbvla9qbovnb9b18bt`) |
| Cognito hosted UI domain | `ap-northeast-254vejkeu5.auth.ap-northeast-2.amazoncognito.com` |
| SQS | `blogSQS` + DLQ via redrive policy |
| S3 bucket | `myblog-prod-web` |
| CloudFront | `d2y4n52sgjlrz6.cloudfront.net` → `www.ratemymusic.blog` |
| Neon DB | Pooler URL stored in each service's Secrets Manager entry |
| Secrets | `myblog/backend`, `myblog/music`, `myblog/worker` |
| EventBridge | `rate(15 min)` → `blogWorkerLambda` (alias mode) |

## Lambda functions

| Function | Service | Timeout |
|----------|---------|---------|
| `ratemymusic-api` | myblog_backend | 15s |
| `musicApi` | myblog_music | 15s |
| `blogWorkerLambda` | myblog_worker | 120s |

## Auth flow — two entry points

- **CloudFront → backend** (most routes): `edge_guard` middleware checks `x-origin-verify: <EDGE_SECRET>`. Bypassed when `ENV=local`/`dev`. Bearer-token requests pass through without `x-origin-verify` check.
- **API Gateway → backend** (`POST /api/posts`, `PUT /api/posts/{id}`, `DELETE /api/posts/{id}`, `POST /api/publish`): Cognito JWT validated at API Gateway authorizer (`6eia7l`) before reaching Lambda.
