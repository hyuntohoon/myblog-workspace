# CHORE-secrets-ssm-migration: Move all secrets from Secrets Manager → SSM Parameter Store

- **Status**: accepted
- **Owner**: 박지훈
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

8 SecureString parameters at the **same names** `/myblog/backend`, `/myblog/music`, … (leading slash for SSM hierarchy), Standard tier, encrypted with `alias/aws/ssm`. Same JSON value as today.

**Design (revised 2026-06-22): dual-source loader + env-flip cutover.** Instead of a hard call swap, each loader prefers SSM when a new `SECRETS_PARAM` env var is set and falls back to Secrets Manager (`SECRETS_ARN`) on unset-or-error:

```python
def _load_secrets(s) -> dict:
    if s.SECRETS_PARAM:
        try:
            ssm = boto3.client("ssm", region_name="ap-northeast-2")
            return json.loads(ssm.get_parameter(Name=s.SECRETS_PARAM, WithDecryption=True)["Parameter"]["Value"])
        except Exception as e:
            logger.error("SSM load failed for %s, falling back to Secrets Manager: %s", s.SECRETS_PARAM, e)
    if s.SECRETS_ARN:
        sm = boto3.client("secretsmanager", region_name="ap-northeast-2")
        return json.loads(sm.get_secret_value(SecretId=s.SECRETS_ARN)["SecretString"])
    return {}
```

This makes the **code deploy a safe no-op** (`SECRETS_PARAM` unset → unchanged Secrets Manager path) and the **cutover a single Terraform env flip** (`SECRETS_PARAM=/myblog/<name>`, owner-applied), fully reversible by unsetting it. `@lru_cache`/TTL caching preserved. Write-back (spotify): `ssm.put_parameter(Name, Value, Type="SecureString", Overwrite=True)`, gated on the same `SECRETS_PARAM`.

IAM (`infra/secrets.tf`): **additively** grant `ssm:GetParameter` (+ `ssm:PutParameter` for worker/spotify) scoped to `arn:aws:ssm:ap-northeast-2:338183196042:parameter/myblog/<name>` per role, plus `kms:Decrypt` on `data.aws_kms_alias.ssm.target_key_arn` — **keeping the existing `secretsmanager:*` grants** until the final cleanup step. Parameter **values created out-of-band** (CLI by owner — see constraint below); Terraform manages IAM + env only, never values → **no values in tfstate**.

Secrets Manager ends empty → storage bill ~$0. `test-db` AWS copy is **deleted** (redundant with GHA), not migrated.

## Execution constraint (discovered 2026-06-22)

The `claude_aws_manager` IAM user **lacks `ssm:PutParameter`** (and likely `ssm:GetParameter`) — net-new service type, AccessDenied (memory `reference-claude-aws-manager-iam-limits`). Two actions are therefore **owner-only** and gate the whole migration:

1. **Provision the SSM parameter values** (copy from Secrets Manager) — owner runs the Step-0 CLI snippet, OR grants `claude_aws_manager` `ssm:PutParameter`+`ssm:GetParameter` on `parameter/myblog/*` so Claude can run it.
2. **`terraform apply`** the IAM/env changes — workspace infra has no auto-apply (memory `reference-workspace-no-infra-autoapply`); a human applies.

Claude CAN: write all dual-source code (safe no-op), open PRs with local verification, and author the Terraform diff. Claude CANNOT: provision values, apply infra, or therefore complete a live cutover. The dual-source design means Claude's code can merge+deploy safely ahead of provisioning, and the cutover waits on the two owner actions above.

## Steps

Dual-run safety: Step 0 populates SSM and adds SSM IAM **additively while keeping every Secrets Manager grant and secret**. With the dual-source loader, deploying the code is a no-op (SM path) until the owner flips `SECRETS_PARAM` per service; each flip is reversible by unsetting it (→ SM fallback). The old secrets are deleted only in the final step — that is the step that realizes the savings.

**Two phases now:** (A) Claude-side — dual-source code merged + deployed to all Lambdas (no-op), Terraform IAM/env diff authored. (B) Owner-gated — provision SSM values, `terraform apply` additive IAM, then flip `SECRETS_PARAM` per service (each a prod-observe gate, rule #4), observe, finally delete SM secrets + drop SM grants/`SECRETS_ARN`.

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

1. ~~**test-db deletion vs migration**~~ — **RESOLVED 2026-06-22 (owner): delete the AWS copy.** GHA `secrets.TEST_DB_URL` is the live source; no code/script reads the SM copy. Step 1 deletes it (no SSM migration for test-db).
2. ~~**`kms:Decrypt` on `alias/aws/ssm`**~~ — **RESOLVED 2026-06-22: grant `kms:Decrypt` explicitly, scoped to the key, on every role that reads a SecureString.** Reasoning: SecureString decryption is a separate KMS action from `ssm:GetParameter`; the AWS-managed key's policy delegates to account IAM, and the "implicit via SSM" path is unreliable enough that gambling risks a prod cold-start `AccessDeniedException` (DB URL read = site-down). Granting it when unneeded is harmless (one key, decrypt only, $0). Scope via `data "aws_kms_alias" "ssm" { name = "alias/aws/ssm" }` → `.target_key_arn` (alias exists after Step 0 creates the first SecureString — order holds). Still confirm with the Step-0 verification command (`aws ssm get-parameter --with-decryption` from a role context). **Do NOT downgrade to `String` type to dodge KMS — that stores plaintext = security regression.**
3. **Parameter size ≤ 4 KB (Standard tier)** — all current secrets are small (DB URL + a few keys), but confirm each `SecretString` length < 4096 before Step 0; otherwise that param needs Advanced tier ($0.05/param/mo — still cheaper, but note it).
4. **Steps 2–4 batching** — gated one-per-session (rule #4) by default; owner may OK running them together since they're independent Lambdas with the same low-risk mechanical change and per-service prod smoke.

## Decisions log

| Date | Decision | Step |
|------|----------|------|
| 2026-06-22 | Full SSM migration chosen over consolidation (can't reach <$1 with least-privilege intact); AWS-managed KMS key (free), no CMK | — |
| 2026-06-22 | `myblog/test-db` AWS copy deleted, not migrated (GHA secret is the live source, no SM reader) | 1 |
| 2026-06-22 | Grant `kms:Decrypt` explicitly per role (scoped to `alias/aws/ssm` target key); don't rely on implicit SSM decryption; never downgrade to `String` | 0/2 |
| 2026-06-22 | Dual-source loader (`SECRETS_PARAM` SSM-preferred → `SECRETS_ARN` SM fallback); cutover = owner Terraform env flip, not a code swap — code deploy is a safe no-op, cutover fully reversible | 2–5 |
| 2026-06-22 | `claude_aws_manager` lacks `ssm:PutParameter`/`GetParameter` → provisioning + `terraform apply` are owner-only; migration completion is owner-gated | 0/7 |

## Progress (2026-06-22)

**Phase A — DONE + merged:** dual-source code (backend `myblog_backend#85`, music `myblog_music#46`, worker `myblog_worker#50` + worker test fix `#51`) + infra additive SSM IAM/`kms:Decrypt`/env switches (workspace `#414`). All deployed.

**Phase B — CUTOVER DONE + PROD-VALIDATED (workspace `#416`):** owner granted `claude_aws_manager` ssm/kms (inline policy `claude-ssm-myblog`); Claude then:
1. Provisioned 6 SSM SecureString params from Secrets Manager (all valid JSON, <4KB).
2. Applied `#414` (additive IAM + empty env), `terraform plan` clean (8 add / 4 change / 0 destroy).
3. Flipped `SECRETS_PARAM`/`SPOTIFY_SECRETS_PARAM` per service + applied. **Verified in prod:** backend prod smoke 28/0 (CRUD + edge_guard) + zero SSM-fallback logs; music smoke search; worker invoke 200; spotify **write-back to SSM confirmed** (`last_successful_refresh_at` 00:57→02:16) + zero fallback logs across all log groups. Every service reads SSM, not the SM fallback.

**Step 7 — REMAINING (this is where the bill drops; not yet done):**
- `scripts/` (health.sh, research_poller, editor_buckit, buckit_nightly, genre_heal_poller, spotify_bootstrap_token) still read Secrets Manager — migrate to `aws ssm get-parameter` first.
- `myblog/test-db` + `myblog/neon-api` have **no readers** (audit) → deletable now (−$0.80/mo); SM restore window is the backstop.
- backend/music/worker/spotify/smoke SM secrets + `SECRETS_ARN`/`SPOTIFY_SECRETS_ARN` env + `secretsmanager:*` IAM grants: delete after the observation window (they are the dual-source fallback net — deleting removes it). **Bill reaches ~$0 only after this.**

**Cost status: NOT yet realized.** All 8 SM secrets still exist ($3.20/mo) + 6 free SSM params. The drop happens at Step 7 deletion.

## Owner runbook

```bash
# 0a. ONE-TIME: let Claude drive the rest (option A), OR skip and run 0b yourself (option B).
#     Attach an inline policy to user claude_aws_manager:
#       ssm:PutParameter, ssm:GetParameter on arn:aws:ssm:ap-northeast-2:338183196042:parameter/myblog/*
#       (+ kms:Encrypt/Decrypt/GenerateDataKey on alias/aws/ssm to write SecureStrings)

# 0b. Provision SSM SecureString params from Secrets Manager (test-db excluded — it's deleted).
for n in backend music worker spotify smoke neon-api; do
  v=$(aws secretsmanager get-secret-value --secret-id "myblog/$n" --query SecretString --output text)
  aws ssm put-parameter --name "/myblog/$n" --type SecureString --value "$v" --overwrite
done
# anthropic: provision only once its key value is set (research feature). test-db: delete, don't migrate.

# 0c. Verify decryption works from a role context (OQ2):
aws ssm get-parameter --name /myblog/backend --with-decryption --query Parameter.Value --output text | head -c 0 && echo OK
```

Then, in order (each `apply` is owner-run — no infra auto-apply):
1. Merge the 4 PRs (#85/#46/#50 code = no-op deploys; #414 infra). Confirm prod smoke stays green after each code deploy (SM path unchanged).
2. `terraform apply` #414 — additive SSM IAM + empty env switches (no behavior change).
3. **Cutover, one service per session (rule #4):** set that Lambda's `SECRETS_PARAM` (and `SPOTIFY_SECRETS_PARAM`) to `/myblog/<name>` in `infra/lambda.tf` → `apply` → prod smoke → observe. Order: backend → music → worker → (spotify is the worker/backend `SPOTIFY_SECRETS_PARAM`, do last; verify a token write-back rewrites the SSM param).
4. After ≥7 days of stale `LastAccessedDate` on the SM secrets: migrate `scripts/`, delete the 6 SM secrets (+ test-db), remove the `secretsmanager:*` grants + `SECRETS_ARN`/`SPOTIFY_SECRETS_ARN` env from Terraform, `apply`. **Bill drops here.** SM has a 7–30 day restore window as a safety net.
