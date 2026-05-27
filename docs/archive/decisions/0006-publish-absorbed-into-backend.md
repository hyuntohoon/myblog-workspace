# ADR 0006: Absorb `myblog_publish` into `myblog_backend`

- **Status**: accepted
- **Date**: 2026-05-27
- **RFC**: `docs/done/rfcs/ARCH-11-absorb-publish-into-backend.md`

## Context

`myblog_publish` was a standalone Lambda that exposed `POST /api/publish`. It received a post payload, committed an MDX file to the blog content repo via GitHub API, and triggered a GitHub Actions build. Auth was `x-origin-verify` edge secret (set by CloudFront), but the Lambda also had a public Function URL (`AuthType: NONE`) that bypassed API Gateway entirely — a known security gap (SEC-4).

## Decision

Delete `myblog_publish`. Move `POST /api/publish` into `myblog_backend` as a new route protected by Cognito JWT (same auth as `POST /api/posts`). `GITHUB_TOKEN` added to the `myblog/backend` Secrets Manager secret.

## Alternatives considered

**Option A: Frontend-direct GitHub OAuth** — browser holds a GitHub OAuth token; no Lambda intermediary. Cleaner separation, but requires storing a GitHub token in client-side storage (or a server-side session), adds Cognito + GitHub OAuth coordination, and is a substantially larger change. Deferred as a future option.

**Option B: Keep `myblog_publish` with stronger auth** — add Cognito JWT to `myblog_publish` and delete the public Function URL. Fixes SEC-4 but leaves the two-Lambda architecture in place, increasing ops surface area for no additional capability.

## Consequences

- **Positive**: one fewer Lambda, one fewer IAM role, one fewer Secrets Manager secret, SEC-4 closed. Auth is now Cognito JWT (validates caller identity) vs edge secret (only validates "came through CloudFront").
- **Negative**: `myblog_backend` Lambda now holds `GITHUB_TOKEN` in addition to `DATABASE_URL`. Wider blast radius if `ratemymusic-api` is compromised — but `myblog_backend` was already the highest-privilege service (DB write access), so the marginal risk is low.
- **Neutral**: publish path is unchanged end-to-end; only the trigger Lambda changed. GitHub Actions → Astro build → S3 → CloudFront invalidation runs identically.
