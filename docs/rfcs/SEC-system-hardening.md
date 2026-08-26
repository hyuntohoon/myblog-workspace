# SEC-system-hardening: main governance, keyless deploys, and one JWT verifier

- **Status**: draft
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
   indistinguishable from no token. The SPA refreshes only on 401
   (`myblog_front/src/lib/auth.ts`), so an aged-out session died silently instead of refreshing.
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

**3b — front pilot.** Done 2026-08-26. `infra/github_oidc.tf` defines
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

**3c — remaining lanes.** backend, music, worker onto per-lane roles, each pinned the same way,
each holding only its own `lambda:UpdateFunctionCode`/`GetFunction` (worker additionally
`InvokeFunction` on itself). Not started.

**3d — retire the keys.** In order, and the order is the rollback path:

1. front OIDC deploy green in production
2. delete `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` from `myblog_front`
3. same for the other three lanes after 3c
4. delete the `github-actions-deploy` IAM user's access key
5. **delete both AWS root account access keys** — `access_key_2` (the exposed one) and
   `access_key_1` (unused since 2025-12-10)

Step 5 is **not** Claude's to perform: root keys can only be removed by signing in as root with MFA.
Deleting the GitHub secrets alone leaves both root keys active in AWS, so "secrets deleted" must
never be recorded as completion of this step.

**Rollback (3b)**: revert the workflow commit — the static key secrets are still present and
unused, so the previous path is restored by the revert alone. The role and repo variable remain,
harmless. This is why the key deletions come *after* the green deploy, not with it.

---

### Step 4 — harden both Cognito guards, with real token vectors

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
myblog_backend: pytest -> 710 passed, 170 skipped (all skips TEST_DB_URL integration; no auth test skipped)
myblog_music:   pytest -> 158 passed, 7 skipped, 1 pre-existing failure
                (test_candidates_localstack, fails identically on origin/main — local env, needs a DB URL)
npx pyright app/ (backend `check` gate) -> 0 errors
openapi.json regenerated in both -> unchanged, so no contract procedure applies
```

**Rollback**: revert the two service PRs. The Terraform env var can stay — the reverted code ignores
it, exactly as the pre-change code does now.

---

### Step 5 — polyrepo assessment (analysis only)

Ships no code. Ends in `KEEP POLYREPO` or `PLAN MONOREPO MIGRATION` with evidence.

---

### Step 6 — consolidate the JWT verifier (not started)

Deliberately after Step 4, and deliberately not in the same change. The owner's decision on
2026-08-26 was: fix the defects in both copies first, then consolidate, so that a security fix never
ships in the same PR as a package-pin rollout.

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
4. **`myblog-prod-web` has S3 versioning disabled**, so a partially-completed front deploy has no
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
| 2026-08-26 | The app-client allowlist excludes `MyBlogAdminClient` — nothing in any repo authenticates with it, and the API Gateway authorizer already rejects it. | 4 |
