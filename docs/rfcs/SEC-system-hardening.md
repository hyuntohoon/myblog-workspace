# SEC-system-hardening: main governance, keyless deploys, and one JWT verifier

- **Status**: accepted
- **Owner**: 오너
- **Created**: 2026-08-26
- **Plan row**: `plan.md` → SEC-system-hardening
- **Repositories**: `myblog-workspace`, `myblog_front`, `myblog_backend`, `myblog_music`,
  `myblog_worker`, `myblog_shared_db`
- **Related**: `docs/archive/decisions/0009-remove-orphan-github-oidc-roles.md`

---

## Goal

Four named weaknesses in the delivery path are closed, each with its own rollback boundary. `main`
cannot be pushed to, force-pushed, or deleted on any repository, and a PR cannot merge with absent
or red CI. GitHub Actions reaches AWS through a short-lived OIDC-assumed role scoped to one
repository, one ref and one workflow file, and the **AWS root account access key currently held in
a public repository's Actions secrets** is retired. Cognito JWT *authentication* binds the token to
an app client we actually issue to, cannot be used to amplify traffic at Cognito, and has test
vectors built from real signed tokens; *authorization* stays per-service.

## Non-goals

- **No change to what any endpoint authorizes.** The owner / member / draft-agent tiers keep their
  meaning. Step 4 changes what the guard *rejects* and where the code lives, never who may do what.
- **No repository restructuring.** Step 5 is an assessment ending in a recommendation. A monorepo
  migration would be a separate RFC that this one does not pre-approve.
- **No new bypass switch.** `ENV=local|dev` remains the only local-development affordance. Nothing
  added here may be flipped to disable a check in a deployed environment.
- **No secret rotation beyond the AWS keys.** The Cognito pool, `EDGE_SECRET`, and Spotify
  credentials are out of scope.
- **No required status check that GitHub does not actually produce.** A required check whose
  workflow never runs on a given PR blocks that PR forever, and with a single maintainer who cannot
  approve their own PR there is nobody to override it.
- **No consolidation of the two `auth.py` copies in the same change as a behaviour fix.** Step 4
  fixes the defects in both copies; Step 6 (not yet written) consolidates. Shipping a security
  change and a package-pin rollout together is the one combination that cannot be bisected during
  an incident.

## Current state

Verified against the live GitHub and AWS APIs and `origin/main` of all six repositories on
2026-08-26. Where an earlier draft of this document or ADR 0009 said something different, the
correction is called out rather than quietly rewritten.

### Governance — before Step 1

`GET /repos/hyuntohoon/<repo>/rulesets` returned `[]` and
`GET /repos/hyuntohoon/<repo>/branches/main/protection` returned `404 Branch not protected` for all
six repositories. Nothing prevented a direct push, force push, or deletion of `main` anywhere. This
matched CLAUDE.md's own note ("No branch protection exists on any repo (verified 2026-08-09)"): the
workspace ran on Claude self-attestation as the only merge gate.

Constraints that shaped the design:

- **One collaborator.** `GET /collaborators` returns exactly `hyuntohoon (admin)` on all six; they
  are user-owned, not org-owned. GitHub does not let anyone approve their own pull request, so any
  rule requiring `required_approving_review_count >= 1` is an unbreakable deadlock here.
- **The workspace repository has no PR CI.** `.github/workflows/` holds one file,
  `merge-contract.yml`, triggered only by `workflow_dispatch` and `repository_dispatch`.
- **CI does not push to `main`.** The only `git push` in any workflow is
  `merge-contract.yml:59`, which pushes a generated branch and opens a PR (`:60-64`).
- **No automation depended on an admin bypass.** `--admin`, `push --force` to main, and
  `push origin main` appear nowhere in `~/.claude/skills/`, `.claude/`, `scripts/`, `tools/`,
  `AGENTS.md`, `CLAUDE.md`, or `.codex/`.
- **Commits are attributed.** Recent `main` commits resolve to `author.login = hyuntohoon`,
  including one authored from `zlxlgus123@naver.com`. This matters because GitHub silently defaults
  `require_extra_approval_for_unattributed_changes` to `true`, and an unattributed commit would
  demand an approval nobody here can give.
- **A cancelled run reports no check at all**, not a red one — the workflows' own concurrency
  comments say so, added after front #333. "Absent CI" is exactly what a required status check
  converts from *silently satisfied* into *blocked*.

### AWS deploy identities — before Step 3

The account (`338183196042`) already trusted GitHub's OIDC provider
(`token.actions.githubusercontent.com`, created 2025-10-14) and carried **three hand-made roles
trusting it, none referenced by any workflow and none in Terraform**. `git` trusted
`repo:hyuntohoon/*` — any repository, any ref — with `AmazonS3FullAccess`, `AWSLambda_FullAccess`
and `AWSCloudFormationFullAccess`; `AmazonS3FullAccess` covers
`myblog-terraform-state-338183196042`, the Terraform state for the whole system. All three were
deleted on 2026-08-26 (ADR 0009), leaving the account's GitHub-OIDC trust surface at zero.

Deploy authentication as it stands:

| Lane | Identity | Permission surface |
|---|---|---|
| backend, music, worker | IAM user `github-actions-deploy`, one access key | customer-managed `lambda-deploy-only`: `lambda:UpdateFunctionCode`/`GetFunction` on 4 named functions + `InvokeFunction` on `blogWorkerLambda`. No S3, no CloudFront. |
| **front** | **the AWS root account access key** | unbounded — root cannot be constrained by IAM policy, permission boundary, or SCP |

The front finding is the reason this RFC exists in its current shape, and an earlier revision of
ADR 0009 got it wrong (it said "static IAM user keys"). Evidence, gathered without reading any
secret value:

| Fact | Value |
|---|---|
| root `access_key_2` last rotated | `2025-10-22T02:36:36Z` |
| `myblog_front` secret `AWS_ACCESS_KEY_ID` last updated | `2025-10-22T02:36:47Z` — 11 s later, never since |
| root `access_key_2` last used | `2026-08-26T06:09:00Z`, service `cloudfront` |
| front deploy run 32936631790, CloudFront invalidation step | `2026-08-26T06:09:51Z` |
| `github-actions-deploy` key last used | service `lambda`; its policy grants no S3 or CloudFront action |
| any IAM user with S3 or CloudFront permission | **none** — and front's deploy demonstrably uses both |

`myblog_front` is a **public** repository. The account also carries a second active root key,
`access_key_1`, last used `2025-12-10` against `cloudformation` and unused since.

Also: **no GitHub Environments exist on any repo** (`total_count: 0` everywhere), so an OIDC trust
condition can key only off `repo` / `ref` / `job_workflow_ref` claims, not an environment claim.

### Cognito auth — before Step 4

The verification cores of `myblog_backend/app/core/auth.py:30-92` and
`myblog_music/app/core/auth.py:55-97` are semantically identical: same JWKS lookup, `algorithms=
["RS256"]`, `issuer=`, `options={"verify_at_hash": False}`, same `token_use` check, same exception
mapping. The divergence is structural — backend factors the body into `verify_token` so `edge_guard`
can reuse it; music inlines it, and therefore cannot add an edge guard without a third copy.

Defects found, ranked by the harm each actually enables:

1. **No app-client binding in either guard.** Neither file referenced `client_id` or `aud`. The
   binding existed only at the API Gateway authorizer (`infra/apigateway.tf:42`, `audience =
   [spa_client.id]`), which is attached to 51 of 55 routes — not to any `/api/music/*` route, and
   not to every backend GET. So any token minted by the pool was accepted there, including one for
   `MyBlogAdminClient`, which the authorizer rejects. Live harm today is bounded: every real caller
   (the SPA, `scripts/smoke.py:50`, `scripts/buckit_nightly.py:170`) uses the same SPA client. The
   harm prevented is the next app client silently inheriting the whole API with no code change.
2. **Unauthenticated JWKS refetch amplification.** `key is None → _get_jwks.cache_clear()` ran
   *before* the 401 and needs only a base64 JWT header — no signature, no valid claims. N junk
   requests produced N outbound fetches to Cognito, and on the backend `edge_guard` runs this for
   every `/api/*` path on the raw invoke domain, not just guarded routes.
3. **`edge_guard` flattened 401 into 403** (`myblog_backend/app/main.py`), so an expired token was
   indistinguishable from no token on the raw invoke domain. **A first draft of this entry claimed
   the flattening broke the SPA's session refresh; that was wrong.** `PUBLIC_API_URL` and
   `PUBLIC_BACKEND_API_URL` both point at CloudFront, so every SPA request carries
   `x-origin-verify` and returns from the edge branch before reaching this code — verified by
   replaying an expired token with the edge header against both the old and new middleware, which
   answered 401 either way. The actual affected callers are `scripts/smoke.py` and
   `scripts/buckit_nightly.py`, and the actual cost is diagnostic: losing the one signal that
   separates "your token aged out" from "you sent nothing".
4. **`EDGE_SECRET` compared with `==`.** Not a practical timing attack through CloudFront and
   Lambda variance, and not claimed as one — a one-line change that removes the question.
5. **`ENV=local|dev` is a single-flip total-auth-off switch**, held only by two Terraform literals
   and a restrictive config default. Nothing at runtime notices it is running in Lambda with
   `ENV=dev`. Not addressed in Step 4 — see Open question 3.

And the finding that made the rest hard to trust: **of the 40 auth tests that existed, not one
constructed a signed JWT.** Every test passed `credentials=None`, a literal `"x.y.z"`, or
monkeypatched the verifier away. Signature verification, issuer checking, `token_use`, expiry,
`nbf`, and the RS256 pin were entirely unverified by automation. That is not hypothetical: the
`token_use in ("access", "id")` line advertises ID-token support that has never worked, because
`jwt.decode` is called without `audience=` and jose rejects any token carrying `aud` — and nothing
would have noticed if a refactor turned any other check into the same kind of no-op.

### Secrets hygiene

No secret is committed in any repository. The scan candidates are benign, verified by shape without
printing any value: the `DATABASE_URL` literals at
`myblog_backend/.github/workflows/deploy.yml:95,129` and
`myblog_music/.github/workflows/deploy.yml:75,108` are localhost CI service-container URLs, and the
`export DATABASE_URL=...` lines in `tools/lyrics_*.py` and `tools/genius_anchor.py` are
documentation placeholders.

### Cross-repo coupling (input to Step 5)

Over the 180 days ending 2026-08-26 there were 89 days with at least one commit to `main` across the
six repositories. On **50 of those days (56%) four or more repositories changed**; on 33 days (37%)
five or six did; only 11 days (12%) touched a single repository.

`myblog_shared_db` is pinned three different ways:

| Service | Pin | Resolves to | Distance from `shared_db` `main` |
|---|---|---|---|
| `myblog_backend` | `requirements.txt:10` — commit `90a6fca` | 2026-08-17, V54 | 0 commits |
| `myblog_music` | `requirements.txt:13` — commit `8319a56` | 2026-08-16, V53 | 1 commit |
| `myblog_worker` | `requirements.txt:7` — tag `v0.26.0` | 2026-06-25, V32 | **28 commits** |

The worker pin is stale by two months **and** uses the tag mechanism the workspace otherwise
abandoned for `main` SHAs. It is a latent trap, not a live defect: worker's entire surface into the
package is `from myblog_shared_db.genre_mapping import attachable_slugs`
(`worker/service/sync_service.py:8`), and `genre_mapping.py` is byte-identical between `v0.26.0` and
`main`. The first time worker imports a model it will silently be two months behind the schema.

## Target state

- Every repository rejects direct pushes, force pushes and deletions of `main`, with no standing
  bypass actor; the five repositories with PR CI additionally require their real check names.
- Every deploy lane assumes a role via OIDC, scoped by `sub` **and** `job_workflow_ref`, holding
  only the actions that lane performs. No long-lived AWS key exists in any GitHub secret, and the
  root account has no access key.
- Both auth guards bind the token to a configured app-client allowlist, fail closed when that
  allowlist is unset, bound the JWKS refetch, and are covered by a vector suite built from real
  RS256 tokens that is duplicated wherever the guard is duplicated.

## Steps

### Step 1 — `main-protection` ruleset on all six repositories — **DONE 2026-08-26**

One repository ruleset per repo, `enforcement: active`, targeting `~DEFAULT_BRANCH`, with
**`bypass_actors: []`**: `pull_request` (`required_approving_review_count: 0`), `non_fast_forward`,
`deletion`.

`required_approving_review_count` is `0` deliberately: it is the largest value that is not a
deadlock for a sole maintainer. The gate this adds is *"every change is a reviewable PR with a diff
and a history"*, not *"someone else approved it"*.

Ruleset ids: workspace `21563640`, front `21563641`, backend `21563642`, music `21563643`,
worker `21563537`, shared_db `21563644`.

**Verification** (2026-08-26, all six green):
```
for r in myblog-workspace myblog_front myblog_backend myblog_music myblog_worker myblog_shared_db; do
  gh api repos/hyuntohoon/$r/rules/branches/main --jq '[.[].type] | sort | join(", ")'
done
# -> deletion, non_fast_forward, pull_request   (x6)
gh api repos/hyuntohoon/myblog_backend/rulesets/21563642 --jq '.current_user_can_bypass'   # -> never
```

Proven non-deadlocking on `myblog_worker` with a throwaway PR (#97, opened and closed without
merging): `mergeable: true`, `reviewDecision: ""` — no approval demanded. Probe branch deleted.

**Rollback**: `gh api -X DELETE repos/hyuntohoon/<repo>/rulesets/<id>`. Per-repo, instant.

---

### Step 2 — `main-required-checks` ruleset — **DONE 2026-08-26**

A **second** ruleset, not an addition to `main-protection`, so a wrong check name or a CI outage can
be rolled back without also dropping force-push and deletion protection.

| Repo | Ruleset id | Required checks |
|---|---|---|
| `myblog_front` | `21564100` | `check` |
| `myblog_backend` | `21564102` | `check`, `test`, `contract`, `integration` |
| `myblog_music` | `21564105` | `test`, `contract`, `integration` |
| `myblog_worker` | `21564106` | `test` |
| `myblog_shared_db` | `21564108` | `test` |
| `myblog-workspace` | — | none possible |

Every name above is a check GitHub has actually produced on a recent merged PR, not a name inferred
from YAML. `deploy` is excluded: it reports `skipped` on PR runs because of its `if:` guard.
`code-review` (front) is excluded: it skips when `ANTHROPIC_API_KEY` is absent. No workflow in any
repo has a `paths:` filter, so no PR can be permanently blocked by a check that never runs.

**Rollback**: delete the one ruleset. `main-protection` is untouched.

---

### Step 3 — GitHub Actions → AWS via OIDC, and retire the root key

**3a — remove the orphan roles.** Done 2026-08-26; see ADR 0009 for definitions and reasoning.

**3b — front pilot.** Done and **production-verified** 2026-08-27 (run `32998882925`: both S3 syncs, CloudFront invalidation and the post-deploy health smoke all green; `https://www.ratemymusic.blog/` 200). `infra/github_oidc.tf` defines
`myblog-github-front-deploy` with `s3:ListBucket` on `myblog-prod-web`, `s3:PutObject` +
`s3:DeleteObject` under it, and `cloudfront:CreateInvalidation` on the one distribution — the exact
set an empirical `aws s3 sync --dryrun --debug` shows the job issuing, and nothing more. Trust
conditions, all `StringEquals`:

```
aud               = sts.amazonaws.com
sub               = repo:hyuntohoon/myblog_front:ref:refs/heads/main
job_workflow_ref  = hyuntohoon/myblog_front/.github/workflows/main.yml@refs/heads/main
```

A fourth condition, `repository_owner = hyuntohoon`, was applied first and **broke the deploy**:
every assume-role attempt returned `Not authorized to perform sts:AssumeRoleWithWebIdentity`. It was
removed after a bisect — `aud`+`sub` alone deployed green (run `32998312450`), then adding
`job_workflow_ref` stayed green (run `32998882925`), leaving `repository_owner` as the only
condition that could have caused it. Why it fails to match was not determined and is not worth
determining: the claim is redundant, because `sub` and `job_workflow_ref` both already begin with
the owner. The episode is worth recording for two reasons — it is the negative test this role would
otherwise lack (a non-matching condition produces a hard deny, not a silent pass), and it is a
reminder that an OIDC condition key is only useful if you have watched a real run succeed *and*
fail with it.

`job_workflow_ref` is not decoration. `sub` pins the ref, not the workflow, and a
`pull_request_target` run reports `GITHUB_REF` as the *base* branch — so its `sub` is also
`...:ref:refs/heads/main`. On a public repository that means a future `pull_request_target` workflow
with `id-token: write` would hand a fork PR author production S3 write. `job_workflow_ref` restricts
assumption to this one file whatever event started it.

**3c — remaining lanes.** **DONE and production-verified 2026-08-28.** Three per-lane roles
(`myblog-github-{backend,music,worker}-deploy`), each trusting only its own repo's `main` through
its own `deploy.yml`, each granting only `lambda:UpdateFunctionCode` on **one** function — worker
additionally `GetFunction` (for the `function-updated-v2` waiter; the v1 waiter polls
`GetFunctionConfiguration`, which no role grants) and `InvokeFunction` (post-deploy health check).

Why per-lane rather than one shared role: `github-actions-deploy`'s policy granted
`UpdateFunctionCode` on four functions to whoever held its key, and all three repos held the *same*
key — a compromise of any one repo's secret could overwrite any of the others' Lambda code.

Merged worker → music → backend, each verified by its own real deploy before the next started. All
three Lambdas show new `CodeSha256` values, the worker's post-deploy health invoke passed (which is
what proves `GetFunction`/`InvokeFunction` were granted correctly), and `scripts/smoke.sh prod`
returned 19 passed / 0 failed afterwards.

Review caught one thing worth recording: `myblog_music`'s deploy job was the only one of the four
lanes **without** the `&& github.ref == 'refs/heads/main'` guard its twins carry. Safe today only
because `on.push.branches` is `[main]` — but music is also the only lane with no
`workflow_dispatch`, so adding one is the obvious next change, and this PR is what gave that job
`id-token: write`. Fixed in the same change, per CLAUDE.md's sweep rule.

**3d — retire the keys.** In order, and the order is the rollback path:

1. ✅ front OIDC deploy green in production
2. ✅ deleted `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` from `myblog_front` (2026-08-28), then
   proved the lane still deploys with no static key present at all (dispatch run `33158785878`)
3. ✅ same for backend, music and worker (2026-08-28)
4. ✅ `github-actions-deploy`'s access key: **deactivated first**, a worker deploy run green while
   it was `Inactive` (run `33161432250`) as proof nothing still used it, **then deleted**. The user
   now has zero keys. Its `lambda-deploy-only` policy is retained but unused, and still lists a
   dead `publisher-github` ARN — clean up with the user itself.
5. ⛔ **delete both AWS root account access keys** — `access_key_2` (the exposed one; last used
   `2026-08-26T06:09`, the final static-key front deploy, and nothing since) and `access_key_1`
   (unused since `2025-12-10`). **Still open. Owner action.**

**No AWS credential secret exists in any of the six repositories as of 2026-08-28**, and every
deploy runs on a short-lived OIDC session scoped to one repo, one ref, one workflow file and one
resource.

Step 5 is **not** Claude's to perform: root keys can only be removed by signing in as root with MFA.
Deleting the GitHub secrets alone leaves both root keys active in AWS, so "secrets deleted" must
never be recorded as completion of this step.

**Rollback (3b)**: revert the workflow commit — the static key secrets are still present and
unused, so the previous path is restored by the revert alone. The role and repo variable remain,
harmless. This is why the key deletions come *after* the green deploy, not with it.

---

### Step 4 — harden both Cognito guards, with real token vectors — **DONE 2026-08-27, production-verified**

Behaviour changes, applied to **both** copies in one change per repo:

| Change | backend | music |
|---|---|---|
| app-client allowlist (`COGNITO_ALLOWED_CLIENT_IDS`), unset ⇒ 503 | yes | yes |
| kid-miss JWKS refetch throttled to 1 per 60 s | yes | yes |
| `edge_guard` preserves 401 instead of flattening to 403 | yes | n/a (no edge guard) |
| `EDGE_SECRET` via `hmac.compare_digest` | yes | n/a (no `EDGE_SECRET`) |

`COGNITO_ALLOWED_CLIENT_IDS` is set from `infra/lambda.tf` to the SPA client only —
`MyBlogAdminClient` is deliberately absent because nothing in any repository authenticates with it.
The in-process guard and the API Gateway authorizer now pin the same client.

**Ordering constraint.** The Terraform env var must be applied *before* the code that reads it
deploys, or the services fail closed with 503. Applied 2026-08-26; the running (old) code ignores
the new variable, and production was verified healthy afterwards.

`tests/cognito_tokens.py` mints RS256 tokens against a throwaway keypair and serves a matching
JWKS; `tests/test_cognito_token_vectors.py` runs 26 vectors against it. Both files exist in both
repos, because the guard exists in both.

**Verification**:
```
myblog_backend: pytest -> 712 passed, 170 skipped (all skips TEST_DB_URL integration; no auth test skipped)
myblog_music:   pytest -> 160 passed, 7 skipped, 1 pre-existing failure
npx pyright app/ (backend `check` gate) -> 0 errors
openapi.json regenerated in both -> unchanged, so no contract procedure applies
```

The vectors were also **mutation-tested**, after an adversarial review found that three of them
proved less than they claimed. Each of these now fails the suite, and did not before:

| Mutation | Before | After |
|---|---|---|
| delete `_get_jwks.cache_clear()`, leave the counter | 26/26 green | 1 failed |
| replace the `token_use` check with `pass` | 26/26 green | 2 failed |
| delete the no-token fail-closed branch | 710-test suite green | 1 failed |

The first was the sharpest: the throttle test asserted `_jwks_refresh_count()`, a counter the guard
increments *next to* the `cache_clear()` rather than because of it. It now counts real fetches
through an `lru_cache`-wrapped stub, and a second vector proves a rotated key is actually picked up
— which is the half that fails if the cache is never cleared at all. The `token_use` vectors now
assert the rejection *detail*, because several distinct checks all answer 401 and status alone
cannot see one of them disappear.

**Correction to a verification claim.** An earlier revision recorded the one `myblog_music` local
failure (`tests/test_candidates_localstack.py`) as "local env, needs a DB URL". The proximate cause
is indeed a DB URL — `sqlalchemy.exc.ArgumentError` at `tests/test_candidates_localstack.py:65`,
identical on unmodified `origin/main`. But the review that questioned it surfaced something worse:
the test is `@pytest.mark.integration`, music's `test` job runs `pytest -m "not integration"` (so it
is deselected) and its `integration` job runs `pytest tests/integration -m ...` (so this file, which
lives at `tests/`, is never collected). **It runs in no CI job at all.** It also calls
`/api/search/candidates` while the router is mounted at `/api/music/search` (`app/main.py:31`), so
it would 404 even with a database. Recorded as Open question 5; not fixed here, because it is
unrelated to auth and deserves its own change.

**Shipped**: `myblog_music#69` (deploy run `33003554504`), then `myblog_backend#166` (run
`33004045319`). Production verified after each: `./scripts/smoke.sh prod` → **19 passed, 0 failed**,
and direct probes of every path this touched — valid SPA-client token 200, no token 401, garbage
token 401, member-on-owner-route 403, public reads 200, on both services. **No request returned
503**, which is the specific thing to check here: the allowlist fails closed when unset, so one 503
would have meant the Terraform variable had not reached the function.

Observed during the backend deploy and recorded rather than left implicit: `deploy` completed while
`integration (neon)` was still running, because `deploy.needs` was `[check, test, contract]`.

**Both halves of that have since changed, by a parallel session rather than this one.** `myblog_backend#167`
("ci: gate deploy on local integration") added `integration` to `deploy.needs` — closing the gap for
that repo — and removed the `integration`/`integration (neon)` matrix, so `integration (neon)` is no
longer a check GitHub produces. The `main-required-checks` ruleset was updated the same day to drop
it, which is the correct maintenance: a required check whose workflow no longer emits it blocks every
PR forever. **`myblog_music` still has the original gap** — its `deploy.needs` is `[test, contract]`.

**Rollback**: revert the two service PRs. The Terraform env var can stay — the reverted code ignores
it, exactly as the pre-change code does now. Both deploy workflows call only
`aws lambda update-function-code`, so a code revert cannot drop the variable.

**The rollback hazard runs the other way, and nothing guards it.** `infra/lambda.tf` lives in the
workspace repo, whose infra is applied by hand from a local checkout and which has **no required CI
check at all**. The `aws_lambda_function` blocks ignore `filename`, `source_code_hash` and `layers`
— but **not** `environment`. So a `terraform apply` from any checkout predating workspace #940
silently removes `COGNITO_ALLOWED_CLIENT_IDS` from both Lambdas, and once this code is deployed that
turns every authenticated route on backend *and* music into 503 at the same instant. Nothing in
either service repo can revert it, and `terraform plan` would show it as an ordinary in-place
update. The existing mitigation is only the habit of pulling before applying. Open question 6.

---

### Step 5 — polyrepo assessment (analysis only) — **DONE 2026-08-27**

**Verdict: KEEP POLYREPO.** Ships no code. Three measurements drove it:

1. **The coordination cost a monorepo removes is not being paid here.** Contract propagation lag,
   measured service-commit → consuming front-commit across five real changes: 0 s, +42 s, −2 s,
   −28 s, +20 s. Two of the five merged front-before-workspace, i.e. *against* the documented order,
   with no consequence. The classic polyrepo tax is latency between teams; there is one operator.
2. **Every defect found is fixable inside the current topology**, and the largest one is a single
   file. None requires moving a byte of history.
3. **Migration would reopen what Steps 1–2 just closed.** The required-checks design is correct
   *because* no workflow has a `paths:` filter; a monorepo mandates them, and the "required check
   that never runs" deadlock is not hypothetical — it was hit live on 2026-08-26 when a check was
   renamed to `integration (local)` and the ruleset could no longer find its context. The OIDC trust
   policy also pins repo and workflow path with `StringEquals` (`infra/github_oidc.tf`), both
   invalidated by a repo rename or a workflow move.

**The strongest argument against this verdict**, recorded because it is the trigger to watch:
`docs/plan.md` audit item D-2 was closed **with no action** because the fix "did not justify a
cross-repo `myblog_shared_db` change + three re-pins". That is the repo boundary deciding what does
not get built, not merely how long it takes. Pin hygiene reduces that friction but never removes it.
**If a second or third correctness fix is declined on re-pin cost, the verdict should flip.** It is
countable; count it.

What the assessment found that is worth acting on, in order — none of it a migration:

- **`myblog_backend` has two independent `shared_db` pins**: `requirements.txt:10` and a hardcoded
  `ref:` at `.github/workflows/deploy.yml:144`. They are equal today and nothing enforces that.
  Verified directly. This is the top item: one pin source plus a CI assertion that the two agree.
- **`myblog_worker`'s pin is a tag** (`v0.26.0`), 28 commits and two months behind, on the mechanism
  the workspace otherwise abandoned. Latent, not live — its whole surface is one pure function.
- **A declared twin has drifted where an ADR said it would not.** ADR-0004 accepted Spotify client
  duplication on the reasoning that "auth logic is stable … unlikely to change".
  `myblog_worker/worker/clients/spotify_client.py:41` now mints its token through
  `_request_with_retry` (429 + 5xx backoff); `myblog_music/app/clients/spotify_client.py:24` still
  does a bare `httpx.post`. Verified directly. **The user-facing service is the one without 429
  handling**, and both files still carry the "must stay in sync" banner.
- **`deploy` does not depend on `integration`** in either backend or music (`needs:` is
  `[check, test, contract]` and `[test, contract]`). Verified directly. Steps 1–2 close this at the
  PR gate — the merge cannot happen until `integration` is green — but the post-merge `push: main`
  run still ships the Lambda while its DB suite is still going. Adding `integration` to
  `deploy.needs` is a one-line change and belongs to whoever owns the deploy gate.
- **The `openapi-updated` sender no longer exists.** `merge-contract.yml:7-8` triggers on a
  `repository_dispatch` that no workflow in any of the six repos fires; the contract merge is manual
  in practice. Either restore the sender or delete the dead trigger and write the manual step down.
- **`docs/contracts/README.md:20` is stale** — it still says to tag a shared-db version, and tags
  were abandoned for `main` SHAs. The procedure doc for the sharpest edge in the system is wrong.

Caveat on provenance: the agent that produced this had no shell, so its history figures come from
reflogs and committed docs, and it said so. The four claims above marked "verified directly" were
re-checked here with the actual files. The 180-day coupling statistics in *Current state* are mine,
not its.

---

### Step 5 follow-ups — delivery-path hardening (owner-directed 2026-08-28)

These are separate, ordered PRs. Each item must be rechecked against current `main` before it starts;
an item already fixed elsewhere is recorded and skipped rather than rebuilt.

1. **Workspace PR CI + deterministic invariants — DONE 2026-08-28** (workspace #948 `1f12694`,
   shared_db #78 `76c7d9c`) — the real `workspace-check` context passed Terraform format/validate,
   deterministic Active-plan RFC ownership/status tests, and merged OpenAPI consistency. V53
   `tracks.disc_no` and V54 `pending_reratings` were restored to the workspace canonical; shared-db's
   existing required `test` job now checks out public workspace `main` and enforces byte identity.
   The workspace check remains non-required: its context is proven, but mutable backend/music `main`
   inputs still need a defined immediate pre-merge refresh policy before promotion. Production smoke
   was N/A because neither PR applied Terraform, ran a migration, deployed code, or changed runtime
   behavior; post-merge evidence is quoted on both PRs.
2. **Music candidates side-effect split — DONE 2026-08-28** (music #73 additive POST + #74 pure
   GET, workspace #951 additive contract + #952 final contract/docs, front #427 caller/types/status)
   — the rollout kept legacy GET enqueue until the new GET-then-POST frontend was deployed, then
   removed DB/SQS construction and enqueue from GET. Music passed 166 unit tests, contract CI, and
   LocalStack zero-message GET / exact Format-A POST coverage; frontend passed 718 tests and a real
   browser clickthrough; authenticated production smoke returned GET 200 then POST 202 `accepted`.
   Reverse rollback restores legacy GET enqueue before reverting frontend, allowing only a brief
   idempotent duplicate-enqueue window and no sync outage.
3. **Python dependency reproducibility — DONE 2026-08-29** (backend #171 `7d230083`, music #77
   `d0f8aeeb`, worker #101 `766fd1f6`, merged and deployed in that order). `requirements.lock` is
   now the sole listed input to each production bundle and is resolved for the Lambda target rather
   than for the machine that runs the script: `uv pip compile --python-version 3.12
   --python-platform aarch64-manylinux2014 --only-binary :all: --exclude-newer <frozen>`, with those
   flags mirroring the `pip install` flags in `deploy.yml` and `build.sh` one-for-one.

   The item was justified as "freeze the current resolution", but the audit found a live defect
   rather than a formality. Because markers are evaluated against the resolving host, the locks
   compiled on a macOS arm64 laptop reported `platform_machine == "arm64"` and **omitted `greenlet`
   from backend and worker**, which SQLAlchemy declares required on `aarch64`. The bundle installs
   with `--no-deps`, so that package would simply not have been in the deployed zip. The red CI
   check was reporting a real bundle defect, not an architecture quirk.

   Two rounds of review changed the design after the first draft:

   - **The drift gate could not detect a hand-edited pin.** Both scripts seeded the resolver with the
     existing lock, so uv kept any seeded pin still resolvable — a pin downgraded by two years passed
     green, and `compile_requirements.sh` could never move a pin forward, so there was no supported
     way to upgrade anything. Seeding is gone; resolution runs from empty against a recorded index
     freeze. Re-resolving all three locks that way reproduced them exactly, so no pin moved.
   - **The qemu pin did not pin what executes.** `docker/setup-qemu-action`'s real work is
     `docker run --privileged <image>`, defaulting to the mutable tag `tonistiigi/binfmt:latest`,
     one step before `SHARED_DB_PAT` is written to `~/.gitconfig`. The image is now digest-pinned.
   - **The repeat-build check was blind to the only runner-built distribution.** Without
     `--no-cache-dir` the second install was handed the wheel the first built, so `myblog-shared-db`
     — the one package produced on the runner — was the one the check could not see. Both installs
     now run cache-free; CI shows two separate clones building an identical wheel digest.

   Verified per repo: lock byte-identical when compiled on macOS arm64, linux/amd64 and linux/arm64;
   two clean production-target installs identical including a sha256 over every installed file; lock
   pins == installed distributions with none missing or extra; the bundle imports its handler inside
   `public.ecr.aws/lambda/python:3.12` on `linux/arm64`; and an eight-case tamper matrix (downgraded
   pin ×2, deleted pin, injected package, edited git SHA, injected marker, forged source digest,
   edited `requirements.txt`) all red. Post-deploy: each Lambda's `CodeSha256` changed, all three
   `Active`/`Successful`, production smoke 19/19 after each merge, and worker — which has no HTTP
   surface — returns `{"batchItemFailures": []}` with no `FunctionError` on a direct invoke.

   **Known limit, recorded in all three READMEs.** `--require-hashes` requires a hash on every
   requirement and a `git+` URL cannot carry one; `--only-binary` likewise does not apply to a direct
   URL. So `myblog-shared-db` is built on the runner at deploy time from a build backend fetched
   unpinned from PyPI. The lock is therefore not literally the sole input to the bundle. Closing this
   needs shared_db published as a hashed wheel, which is not in this item's scope.

   No package was upgraded, and no `shared_db` version changed. Worker's `requirements.txt` moved off
   the lightweight tag `v0.26.0` onto the commit it already pointed at (`dd016c4b`, verified with
   `rev-parse`) because uv re-resolves a git ref on every run, so a repointed tag would silently
   rewrite the lock while the recorded source digest stayed byte-identical. That is a mutability fix,
   not the pin-invariant work in item 4.
4. **Per-service shared_db pin invariants** — intentional cross-service skew remains allowed, but
   duplicated pins inside one service must fail CI when they drift.
5. **Frontend Playwright golden E2E** — only after items 1–4; start with 3–5 stable, mocked-boundary
   journeys and keep the check non-required until repeated PR evidence shows it is stable.

Rollback is per PR: revert the individual workflow/contract/build/E2E PR. No item authorizes a
production migration, Terraform apply, dependency upgrade, or required-check promotion by itself.

### Step 6 — consolidate the JWT verifier (SHIPPED 2026-08-29)

Deliberately after Step 4, and deliberately not in the same change. The owner's decision on
2026-08-26 was: fix the defects in both copies first, then consolidate, so that a security fix never
ships in the same PR as a package-pin rollout. That constraint is honoured literally — this step
introduces no package and bumps no pin.

**Measured before designing.** The two verifiers' *code* was already token-for-token identical.
Tokenising both files with comments and docstrings dropped, and diffing per function:
`_get_jwks`, `_refresh_jwks_if_due`, `_jwks_refresh_count`, `_reset_jwks_refresh_throttle` and
`_allowed_client_ids` were IDENTICAL. The entire divergence was comments plus one structural split —
`myblog_backend` had factored `verify_token` out so `edge_guard` could reuse it, `myblog_music` had
the same body inlined in `require_cognito_token`. There was no behavioural drift to reconcile, only a
right to drift to remove.

**Shape.** `app/core/auth.py` is now one canonical text, byte-identical in both repositories
(`cmp` clean). Both name their package `app` and define the same four settings fields (`ENV`,
`COGNITO_REGION`, `COGNITO_USER_POOL_ID`, `COGNITO_ALLOWED_CLIENT_IDS`), so the shared file needs no
injection seam. The backend-only authorization tiers — `SINGLE_OWNER`, `resolve_owner`,
`require_owner`, `require_owner_or_draft_agent`, `is_owner` — moved verbatim to
`myblog_backend/app/core/authz.py`.

The split direction matters and was chosen for testability, not tidiness. Every existing test seam
patches `app.core.auth.settings` or `app.core.auth._get_jwks`; had the verifier moved to a new module,
those patches would have silently stopped governing the code under test and the vectors would have
gone on passing for the wrong reason. Keeping the verifier at its existing path put the churn on the
authorization side instead, where a mistake fails loudly (an unset `OWNER_SUB` is 503, never "allow").
For the same reason `authz.py` reads `auth.settings.*` rather than taking its own `settings` binding.

**Placement — why not a shared package.** `myblog_shared_db` was the obvious host and is the wrong
one. The three services pin it at three different revisions today — backend `90a6fca`, music
`8319a56`, worker the abandoned tag `v0.26.0`. A packaged verifier would therefore have shipped two
different versions of this code to the two services it exists to unify, and an auth hotfix would have
become a package release plus two pin bumps plus two deploys, on a pin mechanism already known to
drift. It would also have put `httpx` and `python-jose` inside a DB-models package. Owner decision,
2026-08-29: vendor the canonical text and enforce it, rather than package it.

**Enforcement.** `.github/workflows/verifier-drift.yml` in the workspace repository fetches both
`main` copies daily and fails on any difference. It is scheduled rather than a required PR check on
each repo *by design*: a coordinated change must land in two repositories and one merges first, so a
PR-time comparison against the twin's `main` would go red on the first merge and stay red until the
second — a deadlock during exactly the change it is meant to protect. A daily diff catches drift
within a day and never blocks the fix. The job refuses an empty or non-verifier-looking fetch, so a
rename or a 404 fails rather than passing vacuously.

Two costs of that choice, accepted rather than discovered later:

1. **The tolerated drift window is up to ~17 hours, and it is *auth* drift.** If a verifier hotfix
   merges in one repo at 10:00 KST and the twin PR stalls, production runs two different verifiers
   until the 03:20 job. The only signal is a red job in the workspace Actions tab — there is no
   paging path. The mitigation is procedural and cheap: after landing a coordinated verifier change,
   run `gh workflow run verifier-drift.yml` and read the result, rather than waiting for the cron.
2. **A single-repo revert turns the gate red as a side effect.** Each commit is self-contained, so
   an incident revert of either repo alone is behaviourally safe — but it *is* drift, and the job
   will say so until the twin is reverted too. That is the correct report, not a false alarm; it
   should not be mistaken for a second incident.

The enforcement also lives in the one repository with no required checks, which means **merging the
workspace PR is not optional**: both `app/core/auth.py` copies carry a docstring asserting the daily
check exists. Ship them together or the shared file documents a control that does not run.

**A hole this step surfaced, and closed.** The vector suites prove *authentication*; what the step
physically edits is eleven files of *authorization* imports. Adversarial review mutation-tested that
surface and found that rebinding `require_owner` to `require_cognito_token` inside `publish.py`,
`genres.py`, `research.py`, `library.py` or `posts.py` silently downgrades those routes to "any valid
pool token" while the **entire backend unit suite stays green** — `tests/api/test_publish.py`'s JWT
test asserts 401 for a *missing* token only, which the member guard also produces. With
`FEAT-multi-user-accounts` 0c self-signup enabled that is any pool member able to `POST /api/publish`
or `DELETE /api/posts/{id}`. The gap predates Step 6, but Step 6 is what makes those import lines
load-bearing, so it closes it: `myblog_backend/tests/test_route_guard_map.py` builds the route→guard
map from the live FastAPI dependency graph and pins the 24 owner-only and 2 draft-agent routes by
(method, path). The same mutation now fails 2–6 assertions in each of the five previously-silent
modules.

**Evidence that behaviour is unchanged.** The golden contract is the Step 4 vector suites, and they
are UNCHANGED — byte-identical in `myblog_backend` (`tests/test_cognito_token_vectors.py`,
`tests/test_edge_guard.py`, `tests/cognito_tokens.py`), and code-identical in `myblog_music` (two
prose lines updated; executable tokens verified equal to `origin/main`). 29 signed-JWT vectors per
repo cover invalid signature, `alg=none`, HS256-with-the-RSA-modulus, unknown and missing `kid`,
wrong and missing issuer, expired, not-yet-valid, no clock skew, refresh and missing `token_use`,
ID-token rejection, unlisted app client, missing `client_id`, multi-client allowlists, unset
allowlist fail-closed in prod, malformed tokens, JWKS outage → 503, the explicit fetch timeout, the
kid-miss refetch throttle, and rotated-key pickup after the window. All green in both repos with no
edit to an assertion.

**Open item this surfaced.** `CLAUDE.md`'s merge-gate table said the workspace repository has no
`pull_request`-triggered workflow. It gained one in ws #948 (`workspace-check`), so that reasoning is
stale; the ruleset still carries only `main-protection`. Making `workspace-check` a required check is
now possible and is *not* decided here.

## Open questions

1. **`require_extra_approval_for_unattributed_changes`** — GitHub defaulted this to `true` on all
   six rulesets and it was left there. It is fail-closed and currently inert (every recent commit is
   attributed). The risk is specific: one commit authored from an email not linked to the GitHub
   account makes its PR permanently unmergeable, because the extra approval cannot come from the
   PR's own author. Keep it (safe, known trigger, documented remedy: fix the author email and
   re-push) or set it `false` (removes a control with near-zero value in a one-collaborator repo)?
   Blocks nothing.
2. **Worker's `shared_db` pin** — 28 commits and two months stale, and on the abandoned tag
   mechanism. Latent only, because worker imports one pure function. Bump to a `main` SHA as part of
   Step 5's follow-up, or leave until worker needs a model? Blocks nothing.
3. **`ENV=dev` in a deployed environment** — held today by two Terraform literals and a restrictive
   config default, with no runtime assertion. A guard that refuses to serve when `ENV in
   ("local","dev")` *and* an AWS-provided Lambda marker is present would make it structurally
   impossible rather than conventionally forbidden, and would not be a second bypass switch because
   it can only ever make the guard stricter. Worth a step of its own? Blocks nothing.
4. **A `myblog_music` test runs in no CI job.** `tests/test_candidates_localstack.py` is
   `@pytest.mark.integration`, which the `test` job deselects, and it lives outside `tests/integration/`,
   which the `integration` job is scoped to. It also targets a route path that does not exist. Fix
   the path and move it under `tests/integration/`, or delete it — but a marked test that no
   selection reaches is the "green CI can be false green" shape and should not just sit there.
   Blocks nothing.
5. **Nothing prevents a stale `terraform apply` from stripping `COGNITO_ALLOWED_CLIENT_IDS`** from
   both Lambdas, which would 503 every authenticated route on two services at once (see Step 4's
   rollback note). Options: `lifecycle { ignore_changes = [environment] }` (blunt — it would also
   stop Terraform managing every other variable), a `precondition` asserting the variable is
   non-empty, or moving the value into the SSM parameter each service already reads. Worth deciding
   before the next infra apply.
6. **`myblog-prod-web` has S3 versioning disabled**, so a partially-completed front deploy has no
   object-level rollback — recovery is redeploying the previous commit. Enable versioning with a
   lifecycle expiry? Blocks nothing.

## Decisions log

| Date | Decision | Step |
|------|----------|------|
| 2026-08-26 | `required_approving_review_count: 0`, not 1 — a sole maintainer cannot approve their own PR, so 1 is a permanent deadlock, not a stricter gate. | 1 |
| 2026-08-26 | `bypass_actors: []` on all six; emergency access is "disable the ruleset" (audited), not a standing bypass. | 1 |
| 2026-08-26 | Required checks split into their own ruleset so CI problems cannot force a rollback of push protection. | 1, 2 |
| 2026-08-26 | Owner: delete all three orphan OIDC roles rather than adapt any of them. | 3a |
| 2026-08-26 | Owner: migrate front to OIDC first, retire the root key only after that lane is green in production. | 3b, 3d |
| 2026-08-26 | Trust conditions pin `job_workflow_ref`, not `sub` alone — `sub` does not distinguish `pull_request_target` from `push` on a public repo. Added after review. | 3b |
| 2026-08-26 | Owner: fix the auth defects in both duplicated copies first; consolidation is a later, separate step. | 4, 6 |
| 2026-08-27 | Vectors mutation-tested after review: three of them passed against a guard with the check they named deleted. Fixed by asserting real fetch counts and rejection details. | 4 |
| 2026-08-26 | The app-client allowlist excludes `MyBlogAdminClient` — nothing in any repo authenticates with it, and the API Gateway authorizer already rejects it. | 4 |
| 2026-08-28 | Owner explicitly accepted the RFC so the ordered delivery-hardening follow-ups may continue one step per session. | 5 follow-ups |
