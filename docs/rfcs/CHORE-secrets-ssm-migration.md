# CHORE-secrets-ssm-migration: Move all secrets from Secrets Manager → SSM Parameter Store

- **Status**: draft
- **Owner**: TBD
- **Created**: 2026-06-22
- **Plan row**: `plan.md` → CHORE-secrets-ssm-migration

---

## Goal

All 8 app secrets move from AWS Secrets Manager to **SSM Parameter Store Standard SecureString**. The Secrets Manager storage bill drops from **~$3.20/mo → ~$0** (Parameter Store Standard storage + standard throughput + the AWS-managed KMS key `alias/aws/ssm` are all free). Security posture is **unchanged**: per-parameter IAM scoping gives the same least-privilege granularity as per-secret ARNs, SecureString provides KMS encryption at rest, and no secret value ever lands in `tfstate`.

Motivation: a 2026-06-22 cost audit found storage (per-secret $0.40/mo) is the entire driver — secret count grew 3→8 since late May. API-call cost is negligible (~$0.15/mo). Consolidation inside Secrets Manager can't reach the owner's <$1/mo target without breaking least-privilege (4 distinct Lambda trust boundaries → $1.60 floor), because Secrets Manager IAM scopes per-secret-ARN, not per-JSON-key. Moving to a free store that keeps per-resource IAM is the only secure path under $1.

## Non-goals

- **No value or rotation change.** Same secret contents; rotation stays manual/console (none of the 8 use Secrets Manager managed rotation today — confirmed `RotationEnabled=null` on all).
- **No customer-managed KMS key.** A CMK is $1/mo and would erase the savings. Use the free AWS-managed `alias/aws/ssm`.
- **No secret consolidation/merging.** Each service keeps its own parameter = least-privilege preserved.
- **No change to GitHub Actions secrets.** `secrets.TEST_DB_URL`, `secrets.ANTHROPIC_API_KEY`, `secrets.AWS_*`, `secrets.SHARED_DB_PAT` live in GHA (already free, separate store) and are untouched.
- **Not adopting the Parameters & Secrets Lambda Extension.** Optional later optimization; runtime API cost is already negligible.

## Current state

8 secrets in Secrets Manager (region `ap-northeast-2`, account `338183196042`), no rotation, no replication. Reader/writer map (audit 2026-06-22):

| Secret | Read by | Written by | Lambda hot path |
|---|---|---|---|
| `myblog/backend` | backend Lambda `myblog_backend/app/core/config.py:84` (`@lru_cache get_settings`); local `scripts/health.sh:23`, `research_poller.py:75`, `editor_buckit.py:84`, `buckit_nightly.py:164` | — | yes (cold start) |
| `myblog/music` | music Lambda `myblog_music/app/core/config.py:76`; local `scripts/genre_heal_poller.py:43` (aws CLI) | — | yes |
| `myblog/worker` | worker + researchWorker Lambdas `myblog_worker/worker/core/config.py:76` | — | yes |
| `myblog/spotify` | backend `app/clients/sqs_client.py:136-154` (300s TTL), worker `worker/clients/spotify_user_client.py:129`; `scripts/spotify_bootstrap_token.py:141` | **worker `spotify_user_client.py:174` (`PutSecretValue`)**, `spotify_bootstrap_token.py:156` (`--write`) | yes + write-back |
| `myblog/smoke` | `scripts/buckit_nightly.py:577` only (`SMOKE_SECRET_ID`) | — | no |
| `myblog/test-db` | **no code/script reader** — CI uses GHA `secrets.TEST_DB_URL` (worker `deploy.yml:30`) | — | no |
| `myblog/neon-api` | **no code reader** — manual console lookup during DB role rotation | — | no |
| `myblog/anthropic` | researchWorker Lambda via `ANTHROPIC_SECRETS_ARN` (runtime; FEAT-ai-editorial-critique not yet shipped) | owner (console) | yes (future) |

IAM: `infra/secrets.tf` grants `secretsmanager:GetSecretValue` per-secret-ARN to each Lambda role, plus `secretsmanager:PutSecretValue` (spotify→worker). ARNs injected as env vars (`SECRETS_ARN`, `SPOTIFY_SECRETS_ARN`, `ANTHROPIC_SECRETS_ARN`) in `infra/lambda.tf`. Code fetches at runtime via boto3 `get_secret_value(SecretId=...)` and `json.loads(...["SecretString"])`.

Each secret is a JSON blob (`DATABASE_URL`, `EDGE_SECRET`, `GITHUB_TOKEN`, Spotify creds/`refresh_token`, etc.) — all well under the 4 KB Standard-tier parameter limit.

## Target state

8 SecureString parameters at the **same names** `/myblog/backend`, `/myblog/music`, … (leading slash for SSM hierarchy), Standard tier, encrypted with `alias/aws/ssm`. Same JSON value as today — code does `ssm.get_parameter(Name=..., WithDecryption=True)["Parameter"]["Value"]` then the **same `json.loads`** (minimal diff; `@lru_cache`/TTL caching preserved). Write-back: `ssm.put_parameter(Name, Value, Type="SecureString", Overwrite=True)`.

IAM (`infra/secrets.tf` rewritten): `ssm:GetParameter` (+ `ssm:PutParameter` for the worker/spotify path) scoped to `arn:aws:ssm:ap-northeast-2:338183196042:parameter/myblog/<name>` per role, plus `kms:Decrypt` on the `alias/aws/ssm` key. Env vars carry the **parameter name** (e.g. `/myblog/backend`) not an ARN, since `get_parameter` takes `Name`. Parameter **values created out-of-band** (CLI by owner); Terraform manages IAM only and references ARNs as constructed strings — **no values in tfstate** (mirrors the existing `myblog/anthropic` container/value split).

Secrets Manager ends empty → storage bill ~$0. `test-db` AWS copy is **deleted** (redundant with GHA), not migrated.

## Steps

Dual-run safety: Step 0 populates SSM and adds SSM IAM **additively while keeping every Secrets Manager grant and secret**. Each later code step is therefore reversible by redeploying the previous bundle (still reads Secrets Manager). The old secrets are deleted only in the final step — that is the step that realizes the savings.

### Step 0 — Provision SSM params + additive IAM (no prod risk)

Owner runs a CLI snippet that, for each secret, copies the current `SecretString` into an SSM SecureString param of the same name (values never enter tfstate). Terraform PR adds `ssm:GetParameter`/`PutParameter` + `kms:Decrypt` to the relevant roles **without removing** the `secretsmanager:*` grants. After apply, both stores hold identical values; nothing reads SSM yet.

**Verification**:
```
aws ssm get-parameter --name /myblog/backend --with-decryption --query 'Parameter.Value' --output text | python -c 'import sys,json;json.load(sys.stdin)'
# from a Lambda role context: confirm kms:Decrypt is allowed on alias/aws/ssm (OQ2)
terraform plan   # clean; only additive IAM
```

**Rollback**: delete the new SSM params + revert the IAM PR. Secrets Manager untouched.

---

### Step 1 — Non-Lambda cutover: ops scripts + delete test-db/neon-api (no prod risk)

`scripts/` switch `aws secretsmanager get-secret-value --secret-id X --query SecretString` → `aws ssm get-parameter --name X --with-decryption --query Parameter.Value`, and boto3 `sm.get_secret_value` → `ssm.get_parameter(WithDecryption=True)`: `health.sh`, `research_poller.py`, `editor_buckit.py`, `buckit_nightly.py` (both `myblog/backend` + `myblog/smoke`), `genre_heal_poller.py`, `spotify_bootstrap_token.py` (read + `put_parameter` write). Then **delete** the `myblog/test-db` (redundant w/ GHA) and `myblog/neon-api` (manual-only) Secrets Manager secrets, and migrate `myblog/smoke` (drop the SM copy once `buckit_nightly` reads SSM).

**Verification**:
```
python scripts/research_poller.py --once   # resolves DATABASE_URL from SSM
python scripts/buckit_nightly.py --dry-run # mints smoke token from SSM
aws secretsmanager describe-secret --secret-id myblog/test-db   # ResourceNotFound after delete
```

**Rollback**: revert script diffs (still read SM); recreate deleted secrets from a saved value if needed.

---

### Step 2 — backend Lambda → SSM

`myblog_backend/app/core/config.py:84` loader swaps to `ssm.get_parameter`. Env `SECRETS_ARN` → `SECRETS_PARAM=/myblog/backend` in `infra/lambda.tf`. Deploy, then prod smoke. **rule #4 prod-observe gate.**

**Verification**: `scripts/smoke.sh` prod green (posts/publish read DATABASE_URL) + backend CloudWatch shows no SecretsManager errors.

**Rollback**: redeploy previous backend bundle (reads SM, still present).

---

### Step 3 — music Lambda → SSM  ·  ### Step 4 — worker Lambda → SSM

Same mechanical loader swap in `myblog_music/app/core/config.py:76` and `myblog_worker/worker/core/config.py:76`; env `SECRETS_ARN`→`SECRETS_PARAM`. Independent Lambdas — **parallel-eligible** with Step 2, but each still merges + prod-smokes on its own gate (music: `/api/music/search/unified`; worker: a sync invocation drains clean).

**Rollback**: redeploy previous bundle per service.

---

### Step 5 — spotify read + write-back → SSM (highest risk)

backend (`sqs_client.py`) + worker (`spotify_user_client.py`) reads → `get_parameter`; the worker write-back (`:174`) → `put_parameter(...Overwrite=True)`. Deploy worker + backend together. **rule #4 gate.**

**Verification**: `/profile` 검토-모드 banner shows connection status (backend read); the hourly `worker-spotify-listening-sync` job runs clean; force one token refresh and confirm the SSM param is rewritten (`aws ssm get-parameter ... last_successful_refresh_at` advances).

**Rollback**: redeploy previous worker+backend (read+write SM). Reconcile any token written to SSM-only back into SM before reverting.

---

### Step 6 — anthropic → SSM

researchWorker env `ANTHROPIC_SECRETS_ARN` → `ANTHROPIC_PARAM=/myblog/anthropic`; loader swap. Trivial (feature not yet shipped). Can ride with FEAT-ai-editorial-critique instead if that lands first.

---

### Step 7 — Delete Secrets Manager secrets + drop SM IAM (realizes savings)

After all old secrets show a stale `LastAccessedDate` (no reads for ≥7 days), delete the 5 remaining Secrets Manager secrets and remove every `secretsmanager:*` grant from `infra/secrets.tf`. **This is the step the bill drops on.**

**Verification**:
```
aws secretsmanager list-secrets --query 'length(SecretList)'   # 0
terraform plan   # clean; no secretsmanager resources/policies remain
```
Confirm via console Cost Explorer (USAGE_TYPE `APN2-SecretsManager-Secrets`) the next cycle that storage → ~$0.

**Rollback**: Secrets Manager has a 7–30 day recovery window on delete (`restore-secret`) — keep that window in mind before the IAM removal merges.

---

## Open questions

1. **test-db deletion vs migration** — recommend **delete** the AWS copy (GHA `secrets.TEST_DB_URL` is the live source; nothing reads the SM copy). Blocks Step 1. Owner confirm there's no undocumented manual reader.
2. **`kms:Decrypt` on `alias/aws/ssm`** — confirm whether the Lambda roles need an explicit `kms:Decrypt` statement or the AWS-managed key's default policy auto-allows decryption via the SSM service principal. Must verify from a real role context in Step 0. Blocks Step 2.
3. **Parameter size ≤ 4 KB (Standard tier)** — all current secrets are small (DB URL + a few keys), but confirm each `SecretString` length < 4096 before Step 0; otherwise that param needs Advanced tier ($0.05/param/mo — still cheaper, but note it).
4. **Steps 2–4 batching** — gated one-per-session (rule #4) by default; owner may OK running them together since they're independent Lambdas with the same low-risk mechanical change and per-service prod smoke.

## Decisions log

| Date | Decision | Step |
|------|----------|------|
| 2026-06-22 | Full SSM migration chosen over consolidation (can't reach <$1 with least-privilege intact); AWS-managed KMS key (free), no CMK | — |
| | | |
