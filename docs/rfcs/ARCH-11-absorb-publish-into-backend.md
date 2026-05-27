# ARCH-11: Absorb `myblog_publish` into `myblog_backend`

- **Status**: in-progress (Step 1)
- **Owner**: TBD
- **Created**: 2026-05-26
- **Plan row**: `plan.md` → ARCH-11

---

## Goal

`myblog_publish` is deleted. Its single endpoint (`POST /api/publish`) moves into `myblog_backend` as a new route protected by Cognito JWT (replacing the current `x-origin-verify` edge secret). The public Lambda Function URL is destroyed. Net result: one fewer Lambda, one fewer IAM role, one fewer secret, one fewer attack surface.

## Non-goals

- Changing the publishing pipeline itself. GitHub API → Actions → S3 → CloudFront stays identical. Only the trigger entrypoint moves.
- Changing how the frontend authenticates. Frontend already sends Cognito JWT to `myblog_backend`; the new `/publish` route is the same auth shape as `/posts POST`.
- Moving to frontend-direct GitHub OAuth (option (ii) from the original review). That's a different RFC if ever revisited.
- Canary or staged rollout for the frontend cutover. `/publish` is an admin-only path; the entire user base is one person. A simple atomic switch is acceptable.

## Why Cognito JWT now (rationale for the auth change)

The original architecture review (2026-05-22) had as an open question: "Does `myblog_publish` need full Cognito JWT validation, or is `x-origin-verify` edge-secret sufficient given the Lambda is behind CloudFront?" That question was answered with PR-8: edge-secret is sufficient **given `myblog_publish` remains a separate Lambda**.

Absorbing the route into `myblog_backend` changes the premise. The backend Lambda already validates Cognito JWTs for `POST /posts` and other write endpoints; reusing that dependency is strictly cheaper and stronger than porting the edge-secret middleware over.

- **Stronger auth**: JWT validates the caller's identity; edge-secret only validates "request came through CloudFront", which the public Function URL (SEC-4) bypasses anyway.
- **Cheaper code**: no new middleware, no new env var, no new attack surface from a secret used only by one path.
- **Symmetry**: post creation requires JWT; post publication should not have weaker auth than post creation.

The edge-secret approach was a local optimum for the "separate Lambda" architecture. Absorbing into backend dissolves that local optimum.

## Current state

`myblog_publish`:
- One Lambda function: `publisher-github`
- One endpoint: `POST /api/publish` via API Gateway
- Auth: `x-origin-verify` edge secret middleware (PR-8). Bypassable via the public Function URL (SEC-4).
- Secret: `myblog/publish` in AWS Secrets Manager (`GITHUB_TOKEN`)
- IAM: dedicated execution role
- Logic: receives `{slug, frontmatter, body}`, creates an MDX file in the blog content repo via GitHub API, GH Actions takes it from there.

Frontend calls it as `POST ${PUBLISH_API}/api/publish` (separate base URL from backend).

## Target state

`myblog_backend`:
- New route `POST /api/publish` (same path; just lives in a different Lambda now)
- Reuses existing Cognito JWT dependency
- `GITHUB_TOKEN` added to `myblog/backend` secret
- New unit module `app/services/publish_service.py` — pure logic, no FastAPI

`myblog_publish` repo & Lambda: deleted.

Frontend: `PUBLISH_API` removed; uses `BACKEND_API` for everything.

## Migration order constraint

This RFC is **unidirectional and not atomic** — once the route lives in `myblog_backend`, deleting `myblog_publish` is a separate step. Order matters because reversing is harder than rolling forward:

```
Step 1 (additive)  ──►  Step 2 (cutover)  ──►  Step 3 (cleanup)
   add route in           frontend switches      delete publish
   backend; old             URL; old Lambda        Lambda + repo
   Lambda still up          stays alive briefly    + secret
```

Until Step 3, both Lambdas exist and either could serve. This is intentional — it makes Step 2 reversible by just flipping the frontend URL back.

## Steps

### Step 1 — Add `/publish` route to `myblog_backend` (additive, no user-visible change)

- Port `app/api/routes/publish.py` from `myblog_publish` into `myblog_backend/app/api/routers/publish.py`.
- Extract logic into `app/services/publish_service.py` (testable; no FastAPI imports).
- Replace `x-origin-verify` middleware with the existing Cognito JWT dependency used by `POST /posts`. (See "Why Cognito JWT now" above for the rationale.)
- Add `GITHUB_TOKEN` to `myblog/backend` secret in Secrets Manager.
- Add `github_token` to `Settings` in `app/core/config.py`.
- Unit tests covering: happy path (mock GitHub API), missing JWT → 401, missing token in secret → 500 with clean log.

**Verification**:
```
cd myblog_backend && pytest tests/api/test_publish.py -v
# All tests pass.
```

Deploy. Confirm in CloudWatch that the new route is reachable (it won't be hit yet by frontend, but can be `curl`'d with a valid JWT).

**Rollback**: revert PR. `myblog_publish` is still serving production traffic; no user impact.

---

### Step 2 — Cutover frontend to backend `/publish`

- `myblog_front/src/lib/api.ts` — remove `PUBLISH_API_BASE` constant.
- All callers of `${PUBLISH_API}/api/publish` switch to `${API}/api/publish`.
- `publishToGit()` (or whatever the helper is called) now goes through the same `apiFetch` (auth-headered) path as posts.
- Build, deploy, smoke test: create a draft → publish → confirm MDX commit appears in the blog content repo and the resulting site update fires.

**Verification**:
- After deploy, publish a real draft and confirm the full chain works: commit → Actions run → S3 update → CloudFront cache.
- CloudWatch shows the request hit `ratemymusic-api`, not `publisher-github`.

**Rollback**: revert the frontend PR. Old `PUBLISH_API_BASE` returns. `myblog_publish` is still up from Step 1; cutover is reversible.

> ⚠️ Do not proceed to Step 3 until Step 2 has been in production for at least one publish cycle (one real post published successfully via the new path).

---

### Step 3 — Decommission `myblog_publish`

In order:

1. **Block traffic**: in Terraform, set `myblog_publish` Lambda concurrency to 0 (kills the function without deleting it). Apply.
2. **Verify silence**: monitor CloudWatch for `publisher-github` invocations for 24h. Zero expected.
3. **Delete public Function URL** (SEC-4 closure): `terraform apply` after removing the Function URL resource. (Or AWS console + terraform import to ensure state alignment.)
4. **Delete API Gateway route** for `/api/publish` that points to `publisher-github`. The route in backend has the same path; ensure DNS/routing resolves to the backend integration, not the deleted one.
5. **Delete Lambda function**, IAM role, log group via Terraform.
6. **Delete `myblog/publish` secret**: `aws secretsmanager delete-secret --secret-id myblog/publish --recovery-window-in-days 7` (recoverable for a week).
7. **Archive `myblog_publish` repo** on GitHub (do not delete — preserves history).

**Verification**:
```
aws lambda get-function --function-name publisher-github
# Expected: ResourceNotFoundException
```
Publish a post end-to-end one more time; confirm success.

**Rollback**: hardest of the three steps. Within the 7-day secret recovery window, restoring is possible but expensive:
- `aws secretsmanager restore-secret`
- `terraform apply` after reverting the deletion commit
- Frontend rollback only needed if Step 2 was also reverted

If Step 3 has been completed and a problem surfaces, the realistic recovery is: keep `myblog_backend` serving, fix the bug forward, do not attempt to resurrect `myblog_publish`.

---

### Step 4 — Cleanup

- `docs/architecture.md` — remove `myblog_publish` from services table and flow diagram. The `myblog_backend` section gains a "Publishing" subsection.
- `docs/infrastructure.md` — remove `publisher-github` row, remove `myblog/publish` secret row, remove SEC-4 from Known Out-of-IaC Items.
- **Workspace `CLAUDE.md` Layout section** — remove the `myblog_publish/` line (otherwise the Layout block becomes a lie the moment Step 3 lands).
- `docs/plan.md` — remove the now-obsolete SEC-4 row (it was marked "superseded by ARCH-11" pending this cleanup).
- ADR `0006-publish-absorbed-into-backend.md` — records the decision, the rejected alternative (frontend OAuth), and the security trade-off (single Lambda holds more secrets but auth is stronger).
- This RFC marked `done` and moved to `docs/done/rfcs/ARCH-11-absorb-publish-into-backend.md`.

**Verification**: grep across workspace for `myblog_publish` returns only the done log and ADR.

## Security trade-off note

This RFC consolidates the `GITHUB_TOKEN` into the same Lambda that holds `DATABASE_URL` and validates Cognito. Some would argue this widens the blast radius if `myblog_backend` is compromised.

Counterargument (and the basis for proceeding):
- `myblog_backend` was always the higher-privilege service. It writes to the DB. A compromise there is already catastrophic.
- The current state has `myblog_publish` protected only by edge secret with a bypassable Function URL (SEC-4). The added "isolation" is illusory.
- Cognito JWT validation is strictly stronger than `x-origin-verify`.

If at any point this trade-off feels wrong, the alternative — frontend-direct GitHub OAuth — is the cleaner long-term answer. It's deliberately not in scope here.

## Open questions

1. **API Gateway routing during cutover**. Both Lambdas would briefly have `/api/publish` routes. The current API Gateway is `lambdaAPI` — confirm whether both routes can coexist on different integrations or if Step 1 needs a temporary alternate path (e.g. `/api/publish-v2`) until Step 2 completes.
2. **GitHub token rotation**. After Step 1 adds the token to `myblog/backend`, should we rotate it (since the publish secret will be deleted)? Probably yes, but coordinate with whatever GH Actions workflow consumes it.

## Decisions log

| Date | Decision | Step |
|------|----------|------|
| 2026-05-26 | Auth on new route: Cognito JWT (not edge-secret). Rationale in RFC body. | Pre-Step 1 |
| 2026-05-27 | Step 1 complete: route added, 6/6 tests pass, GITHUB_TOKEN added to myblog/backend secret. myblog_backend SHA: 5d33bd2. `myblog_publish` still live. | Step 1 |
