# STAB-2: P0 Auth boundary remediation

- **Status**: accepted
- **Owner**: TBD (주인장)
- **Created**: 2026-06-05
- **Plan row**: `plan.md` → STAB-2
- **Spawned from**: `STAB-1-stabilization.md` §Prioritization & stabilization sequencing **item 1** (P0 Auth boundary). STAB-1 + this RFC are **accepted** (2026-06-05, owner-approved); this is the scoped follow-up STAB-1 calls for.

---

## Goal

Close the internet-reachable, unauthenticated holes in the API boundary so that (a) no unpublished/archived post content is readable without a valid Cognito JWT, (b) no mutation is reachable without one, (c) the side-effecting music `/candidates` endpoint stops answering unauthenticated, and (d) the raw `execute-api` invoke domain is no longer an unthrottled bypass of CloudFront/WAF. After this RFC, app-level auth fails **closed** in prod and is no longer masked by passing tests.

## Non-goals

- The category→section model redesign itself (the `POST /api/categories` *removal* is coordinated here but the section schema/migration/writer-UI work lives in the separate section-taxonomy RFC). This RFC only **gates or removes** the endpoint as an auth fix.
- Multi-user authz (FEAT-multi-user-accounts) — it is *blocked behind* this RFC, not part of it.
- Adding caching of any kind (out of scope per STAB-1).
- Rewriting the music search internals (P5) or worker reliability (that is STAB-3).

## Evidence gathered (2026-06-05, read-only live probes — authoritative)

All probes were read-only GETs against the raw invoke domain `https://ld8pjw3mx4.execute-api.ap-northeast-2.amazonaws.com` (HTTP API `lambdaAPI`, `DisableExecuteApiEndpoint=false`) plus AWS config reads. The mutating `POST /api/categories` write probe was **deliberately not run**; its reachability is proven by the route map + the live Bearer bypass.

| Finding | Probe | Result |
|---------|-------|--------|
| **AUTH-5** backend app-guard fail-open | `aws lambda get-function-configuration --function-name ratemymusic-api` | `ENV=APP_ENV=prod`, **no `COGNITO_USER_POOL_ID`** key → `auth.py` `not settings.COGNITO_USER_POOL_ID` is true → `require_cognito_token` returns `{}` (bypass). |
| **AUTH-3** Bearer-prefix bypass | `GET /api/posts?include_archived=true` with `Authorization: Bearer x` (garbage), no `x-origin-verify` | **HTTP 200**. With `Authorization: Basic x` → 500; with lowercase `bearer x` → 500. Bypass is exactly the literal `startswith("Bearer ")` (capital B). |
| **AUTH-3** reject path | same, no auth header | **HTTP 500, not 403** — edge_guard's reject path returns a 500. Code-quality defect to fix alongside. |
| **AUTH-9** draft disclosure | the AUTH-3 probe body | `{"posts":[13]}`, status distribution `{draft: 2, published: 11}` → **2 draft posts disclosed unauthenticated**. |
| **AUTH-4** route→authorizer map | `aws apigatewayv2 get-routes --api-id ld8pjw3mx4` | `AuthType NONE`: `POST /api/categories`, `POST /api/metrics/batch`, `GET /api/{proxy+}`, `ANY /api/music`, `ANY /api/music/{proxy+}`. JWT (authorizer `6eia7l`): all `posts` mutations, `POST /api/publish`, all `buckets`/`library` mutations. |
| **AUTH-1** unauthed write route | route map above | `POST /api/categories` = `AuthType NONE`. (Write not executed.) |
| **P6-2** music guard bypass | `aws lambda get-function-configuration --function-name musicApi` | **No `ENV` key at all** (keys: `FASTAPI_ROOT_PATH=/api`, `SEARCH_USE_PG_TRGM=true`, `QUEUE_NAME=blogSQS`, `SECRETS_ARN`, `COGNITO_USER_POOL_ID=ap-northeast-2_54vEJKEU5`). `settings.ENV` defaults `'local'` → `require_cognito_token` bypasses (the ENV branch fires *before* the pool-id check; the pool id being set is irrelevant). |
| **P6-2/P6-5/P6-1** side-effecting GET unauth | `GET /api/music/search/candidates?q=…&type=album&limit=1` with `Authorization: Bearer x` | **HTTP 200** with real Spotify album results — the Spotify-calling, SQS-enqueuing "writer sync" endpoint answers unauthenticated. (Probe used a junk query + `limit=1`; at most one idempotent enqueue.) |
| **AUTH-7** WAF | `aws wafv2 list-web-acls --scope REGIONAL` | `[]` — no REGIONAL ACL. The API is **HTTP (v2)**; WAFv2 cannot associate to an HTTP API at all (only REST v1 / CloudFront / ALB / etc.). |
| **P6-6** no throttle | `aws apigatewayv2 get-stage … --stage-name '$default'` | `DefaultRouteSettings` carries no throttle; `RouteSettings` empty; `AutoDeploy=true`. |

> Net: the entire app-level auth layer (`require_cognito_token`) is inert in prod on **both** Lambdas, and edge_guard is defeated by any `Bearer ` prefix on every authorizer-less route. The only thing actually enforcing user identity today is the gateway authorizer on the explicitly-JWT'd mutation routes; everything on the `GET /api/{proxy+}` catch-all and `ANY /api/music*` is open.

## Current state

- **edge_guard** (`myblog_backend/app/main.py:34-54`): bypasses entirely when `APP_ENV in (dev,local)` (`:36-37`, cannot fire in prod — `ENV/APP_ENV=prod`); otherwise raises 403 *only* if the request both lacks a `Bearer ` prefix **and** `x-origin-verify != EDGE_SECRET` (`:45-52`). `has_bearer = headers.get("authorization","").startswith("Bearer ")` at `:50-52` — never validates the token. The reject path observably returns 500 (see evidence).
- **app guard** (`myblog_backend/app/core/auth.py:30-34`): `require_cognito_token` returns `{}` when `ENV in (local,dev)` **or** `not COGNITO_USER_POOL_ID`. Backend Lambda has the latter true (no pool id) → fail-open. `myblog_backend/app/core/config.py` defaults `COGNITO_USER_POOL_ID=""` and never injects it from Secrets/env.
- **catch-all reads** (`myblog_backend/app/api/routes/posts.py:28-34` `list_posts`, `:96-101` `get_post`): declare `Depends(require_cognito_token)` but are served by the `GET /api/{proxy+}` route (no gateway authorizer); `list_posts` accepts `status`/`include_archived` (`post_service.py:156`).
- **categories** (`myblog_backend/app/api/routes/categories.py`): `POST /api/categories` (`add_category`) has no `require_cognito_token` dep and no gateway authorizer; it does a real INSERT+commit via `CategoryService.add` (`category_service.py`). Prod `categories` table currently holds **3 rows**.
- **music** (`myblog_music/app/api/routers/search.py:61,75`): `GET /candidates` declares `Depends(require_cognito_token)`, bypassed in prod (P6-2). No `edge_guard`/`x-origin-verify` anywhere in `myblog_music/app` (P6-5). Reached via `ANY /api/music/{proxy+}` (no authorizer).
- **infra** (`infra/lambda.tf`): backend env block sets `ENV/APP_ENV=prod` but no `COGNITO_USER_POOL_ID`; music env block sets `COGNITO_USER_POOL_ID` but no `ENV`. `infra/apigateway.tf:18-22` `$default` stage has no throttle. `infra/cloudfront.tf:41` references a CloudFront-scope WAF ACL only.

## Target state

- `require_cognito_token` **fails closed** in prod: if `ENV=prod` and the pool id is missing or JWKS is unreachable, it raises 401/500 rather than returning `{}`. The backend Lambda has `COGNITO_USER_POOL_ID` set and JWKS fetch is verified to work from the Lambda.
- edge_guard either **validates** the Bearer JWT for authorizer-less paths, or those paths get a gateway authorizer / app-level dep — a bare `Bearer x` no longer bypasses. The reject path returns a clean 403.
- `GET /api/posts` (list/detail) is no longer unauthenticated for unpublished content: either split off the catch-all behind an authorizer, or the fixed edge_guard + fail-closed app guard covers it. `include_archived`/non-published `status` requires a valid JWT.
- `POST /api/categories` is removed (per the §model decision: no public section-creation API) or hard-gated behind the JWT authorizer.
- Music `/candidates` requires a valid JWT in prod, with the `myblog_front` caller updated to send it; public music reads (`/unified`, `/albums/*`, `/artists/*`) stay open.
- The raw invoke domain is no longer an unthrottled, WAF-less bypass: either `disable_execute_api_endpoint` + CloudFront-only custom domain, or a `$default` stage throttle floor (since WAFv2 can't attach to an HTTP API).

## Steps

Each step is independently mergeable. Sequencing is risk-ordered: the fail-closed backstop (Step 1) lands first so later steps can't regress into a silent fail-open. **One RFC step per session** unless the owner explicitly OKs the next (CLAUDE.md rule #4). Infra steps require a human `terraform apply` (no auto-apply — `reference-workspace-no-infra-autoapply`); never `-target` (rule #6).

### Step 1 — Backend app guard fails closed (`COGNITO_USER_POOL_ID` + `auth.py`)

Cross-repo: `infra/lambda.tf` (set `COGNITO_USER_POOL_ID=ap-northeast-2_54vEJKEU5` on `ratemymusic-api`) + `myblog_backend/app/core/auth.py` (when `ENV=prod`, treat a missing pool id or a failed JWKS fetch as **fail-closed** — raise, don't return `{}`). Verify JWKS is reachable from the backend Lambda **before** flipping the behavior (a wrong/unreachable JWKS would 500 every authed route). Closes **AUTH-5**; backstops AUTH-1/AUTH-9.

**Pre-req evidence:** confirm the Cognito JWKS URL for pool `ap-northeast-2_54vEJKEU5` is fetchable from within the Lambda's egress (it is for the music Lambda, which already carries the pool id — but verify for the backend role/VPC posture).

**Verification:**
```
# after apply: pool id present
aws lambda get-function-configuration --function-name ratemymusic-api --query 'Environment.Variables.COGNITO_USER_POOL_ID'
# authed route with a REAL smoke JWT still 200s (no JWKS regression)
# unauthed mutation now 401 (was fail-open)
```
**Rollback:** revert `auth.py` + remove the env var via `terraform apply`. Non-trivial because a bad JWKS path locks out all authed routes — keep the env-var add and the fail-closed flip as **separate** applies so the lockout risk is isolated.

---

### Step 2 — edge_guard validates the Bearer JWT (or routes get authorizers); fix the 403 path ✅ DONE 2026-06-05 (be#55)

`myblog_backend/app/main.py` — replace the `startswith("Bearer ")` trust with real validation for authorizer-less paths (reuse the `require_cognito_token` validator), and return a clean **403** on reject instead of the current 500. Closes **AUTH-3 / P8-7** and removes the bare-`Bearer x` bypass. Decide per the §model: validate-in-edge_guard vs. moving the catch-all reads behind an authorizer (Step 2b option).

**Verification:**
```
BASE=https://ld8pjw3mx4.execute-api.ap-northeast-2.amazonaws.com
# bypass closed: garbage Bearer no longer 200
curl -s -o /dev/null -w '%{http_code}\n' "$BASE/api/posts?include_archived=true" -H 'Authorization: Bearer x'   # expect 401/403
# real CloudFront path with valid x-origin-verify + JWT still works (prod smoke)
```
**Rollback:** revert `main.py`.

---

### Step 3 — Remove or hard-gate `POST /api/categories` (AUTH-1)

Per the STAB-1 §model decision (no public section-creation API), **remove** the endpoint and its dead `add_category`/`CategoryService.add` write path (`myblog_backend/app/api/routes/categories.py`, `category_service.py`) and drop the `POST /api/categories` route from `infra/apigateway.tf` — OR, if removal must wait on the section-taxonomy RFC, attach the JWT authorizer to the route as an interim gate. Coordinate the final removal with the section-taxonomy RFC so the writer UI no longer references it.

**Verification:**
```
aws apigatewayv2 get-routes --api-id ld8pjw3mx4 --query "Items[?RouteKey=='POST /api/categories']"   # expect [] after removal, or AuthorizationType=JWT if gated
```
**Rollback:** restore the route + handler; `terraform apply`.

---

### Step 4 — Music `/candidates` requires auth; public reads stay open (P6-2/P6-5; P6-1 = caller-audit context only)

Set `ENV=prod` on `musicApi` in `infra/lambda.tf` — this is **targeted**: only `/candidates` carries `Depends(require_cognito_token)`, so only it becomes gated; `/unified`, `/albums/*`, `/artists/*` have no such dep and stay public (verified). The **GET method itself is kept** (STAB-1 classifies P6-1 as an *intentional tradeoff* — "기존 유지"); P6-1 is referenced here only to flag that `/candidates` is side-effecting, so the caller audit matters. Optionally add `edge_guard`/origin-verify to the music app or a gateway authorizer on the candidates route as defense-in-depth. Cross-repo: `infra` + `myblog_music` + `myblog_front`.

> 🔴 **JWKS pre-req (mirror of Step 1 — applies harder here).** Flipping `ENV=prod` makes `/candidates` the **first** prod exercise of `require_cognito_token` on the music Lambda (ENV defaults `local` today → the guard short-circuits at `myblog_music/app/core/auth.py:33` and `_get_jwks()` has never run in prod). Unlike the backend, `myblog_music/app/core/auth.py` (`_get_jwks` at :20, called at :44 inside the `try` at :40) has **no `httpx.HTTPError` handler** — its only `except` is `JWTError` at :67 — so a JWKS-fetch failure raises an **unhandled 500**, whereas `myblog_backend/app/core/auth.py:45-53` catches `httpx.HTTPError` → clean 503. **Before/with the flip:** (1) verify the Cognito JWKS URL for pool `ap-northeast-2_54vEJKEU5` is reachable from the music Lambda's egress, and (2) port the backend's `httpx.HTTPError → 503` handler into the music `auth.py` so a JWKS outage degrades to 503, not 500.

**Open question (OQ-A):** the `myblog_front` `/candidates` callers are **not** a single button — there are three: writer `SubjectBlock.tsx` and member `AddAlbumModal.tsx` use `apiFetch` (sends Bearer, redirects to login on 401), but the **public search-bar** path `scripts/searchBarDb.client.ts` uses raw `fetch(url, { headers: getAuthHeader() })` where `getAuthHeader()` (`auth.ts`) returns `{}` when no token is in `localStorage`. So after Step 4 a **logged-out public visitor** clicking Sync gets 401 (today: working 200). Decide the intended behavior (hide/disable the Sync control when `!isLoggedIn`, or accept the 401) and land the front change with (or before) the infra flip. *(Re-confirm the three call sites + line numbers at fix time.)*

**Verification:**
```
# /candidates without a valid token now 401; with a real smoke JWT 200
# /unified still 200 unauthenticated (public read preserved)
# JWKS-outage path returns 503 (not 500) after the handler port
```
**Rollback:** remove `ENV=prod` from `musicApi`; revert front caller.

---

### Step 5 — Bound the raw invoke domain (AUTH-7 / P6-6)

WAFv2 **cannot** attach to an HTTP API (it only associates with CloudFront / REST API v1 stages / ALB / AppSync / Cognito / App Runner — not API Gateway HTTP v2), so the options are:

- **(b) — default near-term fix:** add a `$default` stage `default_route_settings` throttle (`throttling_burst_limit`/`throttling_rate_limit`) as a floor (`infra/apigateway.tf`). No site-down risk.
- **(a) — blocked, needs prep first:** `disable_execute_api_endpoint=true` to force all traffic through CloudFront+WAF. 🔴 **Currently unsafe / site-down:** `infra/cloudfront.tf:5,63` sets the API origin `domain_name = local.apigw_domain = "ld8pjw3mx4.execute-api.ap-northeast-2.amazonaws.com"` — CloudFront routes to the **raw invoke domain itself** (no API Gateway custom domain exists). Disabling the execute-api endpoint would sever CloudFront's own path and take the **entire site API down**. Option (a) is therefore blocked on first provisioning an API Gateway custom domain and repointing the CloudFront origin to it.

**Verification:**
```
# option (b): get-stage shows non-empty throttle
aws apigatewayv2 get-stage --api-id ld8pjw3mx4 --stage-name '$default' --query 'DefaultRouteSettings'
# option (a) — ONLY after a custom domain is in place + CloudFront repointed:
#   curl raw invoke domain -> 403/404, while the CloudFront custom domain still 200s
```
**Rollback:** revert the API/stage attribute; `terraform apply`. (Option (a) rollback also requires re-enabling the execute-api endpoint.)

---

## Open questions

1. **OQ-A (Step 4)** — *(partly answered: three callers, see Step 4).* Decide the intended behavior for a **logged-out** visitor's Sync click on the public search bar (`searchBarDb.client.ts`): hide/disable the control when `!isLoggedIn`, or accept the 401. Drives the front change scope and front-first vs. simultaneous merge. *(Blocks Step 4.)*
2. **OQ-B (Step 2)** — edge_guard JWT validation vs. moving the `GET /api/{proxy+}` catch-all reads behind a gateway authorizer. Validation keeps one ingress simple; authorizer is more standard but means enumerating which GETs are intended-public (`/unified` proxying etc.). *(Blocks Step 2 final shape.)*
3. **OQ-C (Step 3)** — remove `POST /api/categories` now (interim, ahead of section-taxonomy RFC) vs. gate-then-remove. Depends on whether the writer still calls it (STAB-1 MODEL-3 says the create path is dead — re-confirm at fix time). *(Blocks Step 3.)*
4. **OQ-D (Step 5)** — **ANSWERED (2026-06-05): unsafe as-is.** CloudFront's API origin points at the raw invoke domain (`cloudfront.tf:5,63`), so option (a) `disable_execute_api_endpoint` would take the site API down. Option (a) is blocked on first creating an API Gateway custom domain + repointing CloudFront; option (b) (stage throttle) is the unblocked near-term fix.

## Decisions log

| Date | Decision | Step |
|------|----------|------|
| 2026-06-05 | Spawned from STAB-1 §Sequencing item 1; auth remediation = **both layers, sequenced** (STAB-1 OQ4) — fail-closed app guard + edge_guard JWT validation + per-route gateway authorizers/deps. | all |
| 2026-06-05 | **WAFv2 cannot attach to the HTTP API** (live-confirmed). AUTH-7 remediation re-scoped: stage throttle (unblocked) or `disable_execute_api_endpoint` after a custom domain exists. | Step 5 |
| 2026-06-05 | **`disable_execute_api_endpoint` is currently site-down** — CloudFront's API origin = the raw invoke domain (`cloudfront.tf:5,63`); option (a) blocked on provisioning an API GW custom domain first. Stage throttle (option b) is the near-term fix. | Step 5 / OQ-D |
| 2026-06-05 | **Music `auth.py` lacks the backend's `httpx.HTTPError → 503` handler** — Step 4's `ENV=prod` flip first-exercises the JWKS path; port the handler + verify JWKS reachability before/with the flip (else 500 on JWKS outage). | Step 4 |
| 2026-06-05 | Evidence re-verified live (see §Evidence gathered): AUTH-1/3/4/5/9, P6-1/2/5/6 all confirmed; reject path returns 500 (new). | §Evidence |
| 2026-06-05 | **Step 1 DONE + verified in prod.** ws#255 applied (`COGNITO_USER_POOL_ID=ap-northeast-2_54vEJKEU5` on `ratemymusic-api`) → `require_cognito_token` flips to real JWT validation; be#54 merged + deployed (fail-closed app guard, regression-tested). Live on the raw invoke domain (`/api/posts?include_archived=true`): valid smoke JWT → 200 (2 drafts), `Bearer x` → 401 (**AUTH-5 + AUTH-9 closed**), no-auth → 500 (edge_guard reject path, unchanged → Step 2). Apply was public-read-safe as predicted. | Step 1 |
| 2026-06-05 | **Step 2 DONE + verified in prod.** be#55 merged + deployed. `verify_token(token)` extracted from `require_cognito_token` so `edge_guard` (middleware) and the dep validate identically. `edge_guard` now passes only on a matching `x-origin-verify` (CloudFront edge) **or** a Bearer that actually validates — the `startswith("Bearer ")` prefix-trust is gone; reject returns a clean **403** via `JSONResponse` (no more middleware-`raise` 500), JWKS outage → 503. Prod (raw invoke domain): `Bearer x` → **403** (AUTH-3 closed), no-auth → **403** (P8-7 fixed), public `GET /api/categories` via CloudFront → 200; canonical smoke **27/27** (authed CRUD via real smoke JWT, no regression). Design note: safe because `PUBLIC_BACKEND_API_URL = www.ratemymusic.blog` (CloudFront) → all front traffic carries the injected `X-Origin-Verify`, so public reads never depend on a Bearer. | Step 2 |
| 2026-06-05 | **OQ-C answered: the create path is NOT dead.** The writer front `addCategory` still calls `POST /api/categories` (`myblog_front/src/lib/api.ts:38`, `src/scripts/write/api.ts:16,26`). So Step 3 cannot simply *remove* the endpoint without breaking the writer — it must wait on STAB-5's writer rework, or take the interim *gate-behind-authorizer* path (`infra/apigateway.tf`, human apply). | Step 3 / OQ-C |
