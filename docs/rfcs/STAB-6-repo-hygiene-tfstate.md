# STAB-6: repo hygiene + remote Terraform backend

- **Status**: DONE 2026-06-06 (all 5 steps; Step 5 migrated S3-only, DynamoDB lock dropped)
- **Owner**: TBD (주인장)
- **Created**: 2026-06-05
- **Plan row**: `plan.md` → STAB-6
- **Spawned from**: `STAB-1-stabilization.md` §Prioritization & stabilization sequencing **item 6** (P3 hygiene + P3-1 remote tfstate backend). STAB-1 + this RFC are **accepted** (2026-06-05, owner-approved).

---

## Goal

Clean the tracked build-artifact / OS / IDE cruft out of the repos and move the canonical Terraform state off a single laptop. After this RFC: no 26 MB build zip or transcript-`.gitignore` or `allure-results`/`.DS_Store`/`.idea`/`.vscode` noise is tracked, and `infra/terraform.tfstate` lives in a locked remote backend (S3 + DynamoDB) instead of a local-only, unencrypted file holding a plaintext Cognito client secret.

## Non-goals

- Not history-rewriting (`git filter-repo`) unless clone size proves it necessary — default is `git rm --cached` + `.gitignore` (the blob stays in history but stops being the working artifact).
- Not rotating the Cognito `admin_client` secret unless laptop exposure is suspected (console-only — out of band).
- Not touching `infra/placeholder.zip` (legit TF Lambda-bootstrap artifact, P3-6) or any `.env` (none tracked — P3-7).
- No application code or behavior change.

## Evidence gathered (2026-06-05 — authoritative)

| ID | Item | Verified |
|----|------|----------|
| P3-2 | `myblog_worker/bundle.zip` | git-tracked, **26 MB** build output; CI rebuilds + deploys its own zip (the committed one is never deployed). |
| P3-3 | `myblog_worker/.gitignore` | opens with a pasted shell transcript (`cd ~/Dow/worker_lambda` on line 1, `cat > .gitignore << 'EOF'` on line 3; intended patterns start line 4) — leaks a home-dir path; `EOF` becomes a live ignore pattern. |
| P3-4 | workspace `allure-results/` | **18** files tracked at workspace root; root `.gitignore` has no allure entry. |
| P3-5 | `myblog_music` OS/IDE | tracked: `.DS_Store`, `app/.DS_Store`, `app/api/.DS_Store`, `.idea/vcs.xml`, `.idea/workspace.xml`. |
| P3-8 | `myblog_front/.vscode/` | tracked `.vscode/setting.json` (typo — inert) + `.vscode/settings.json`. |
| P3-1 | tfstate backend | `infra/main.tf:1` has `terraform {` but **no `backend` block** → local-only state, no locking; tfstate holds the 52-char `admin_client.client_secret` plaintext (correctly gitignored, not committed). Workspace path is **not** under Dropbox/iCloud/OneDrive → Time Machine is the only ambient backup vector. |

## Current state

Build artifacts, OS/IDE files, and a transcript-`.gitignore` are tracked across `myblog_worker` / `myblog_music` / `myblog_front` / workspace; the canonical AWS state is a single unencrypted local file (`infra/terraform.tfstate`) with no lock, holding a plaintext Cognito client secret.

## Target state

Those files untracked + matching `.gitignore` rules in place; `terraform.tfstate` migrated to an encrypted, versioned S3 backend with DynamoDB locking.

## Steps

Steps 1-4 are **per-repo** and each needs a branch + commit **in that repo** (the workspace rule-#1 hook only guards the workspace — [[feedback-nested-repo-branch-per-repo]], [[reference-nested-repo-worktree-recipe]]). They are independent and low-risk (revert = re-add). Step 5 (tfstate backend) is infra + needs a human `terraform init -migrate-state`.

### Step 1 — `myblog_worker`: untrack `bundle.zip` + rewrite `.gitignore` (P3-2/P3-3)
Rewrite `.gitignore` to just the intended patterns (drop the `cd …`/`cat <<EOF`/`EOF` transcript lines), then `git rm --cached bundle.zip`. Confirm `deploy.yml` is the only deploy path (it rebuilds the zip) before untracking.
**Verification:** `git -C myblog_worker ls-files bundle.zip` empty; `.gitignore` is clean patterns; a CI deploy still builds+ships its own zip.
> ✅ Done 2026-06-05 — worker **#38** (`bundle.zip` untracked + `.gitignore` rewritten). Deploy was initially red on a **pre-existing test-isolation defect** (not this hygiene change); fixed by worker **#39**.

### Step 2 — workspace: untrack `allure-results/` (P3-4)
Add `allure-results/` + `allure-report/` to the root `.gitignore`; `git rm --cached` the 18 files.
**Verification:** `git ls-files 'allure-results/*'` empty.
> ✅ Done 2026-06-05 — 18 files untracked + `.gitignore` rule added (this PR).

### Step 3 — `myblog_music`: untrack `.DS_Store` + `.idea/` (P3-5)
Add `.DS_Store` + `.idea/` to `myblog_music/.gitignore`; `git rm --cached` the 5 files.
**Verification:** `git -C myblog_music ls-files '*.DS_Store' '.idea/*'` empty.
> ✅ Done 2026-06-05 — music **#41** (`.DS_Store`/`.idea/` untracked + ignores added).

### Step 4 — `myblog_front`: resolve `.vscode/` (P3-8)
Decide share-editor-config or not (OQ1). If not: add `.vscode/` to `.gitignore` + `git rm --cached` both files. If yes: delete the typo'd `setting.json`, keep `settings.json`.
**Verification:** `git -C myblog_front ls-files '.vscode/*'` reflects the decision; the typo file is gone.
> ✅ Done 2026-06-05 — front **#94**. **OQ1 resolved**: not shared → `.vscode/` ignored + both files untracked (`.gitignore` carries a "not shared; see STAB-6" note).

### Step 5 — remote Terraform backend (S3 + DynamoDB lock) (P3-1) 🟡 PR PREPARED 2026-06-06 (ws#264 — human two-phase apply)
Create an S3 bucket (versioned, SSE, public-access-blocked) + DynamoDB lock table **via a full `terraform plan` (no `-target`, rule #6) + human-run apply** ([[reference-workspace-no-infra-autoapply]]); stop on unexpected drift. Then add a `backend "s3"` block to `infra/main.tf`, run `terraform init -migrate-state` (human), verify a subsequent `plan` is clean. Reconcile `infra/README.md`'s "canonical state = `infra/terraform.tfstate`" claim. Consider rotating the `admin_client` secret only if laptop exposure is suspected (console-only).
> ✅ **DONE 2026-06-06 (ws#264 + ws#268).** S3 bucket `myblog-terraform-state-338183196042` (versioned, AES256, public-access-blocked, `prevent_destroy`) created via owner-approved `terraform apply`; state migrated with `terraform init -migrate-state -force-copy`; post-migrate `plan` → **No changes**, state object present in S3 (versioned, 144 KB). **DynamoDB lock DROPPED — S3-only** (owner decision): single-author + no infra auto-apply → concurrent-apply lock value is low, and `claude_aws_manager` lacks `dynamodb:CreateTable` (apply hit AccessDenied). If multi-operator apply ever becomes real: grant the DynamoDB perm + re-add a lock table, or upgrade Terraform to ≥1.10 and set `use_lockfile = true`. Old local `infra/terraform.tfstate` is now a stale backup (still gitignored).
**Verification:** `terraform plan` clean post-migrate; state object present in S3 (versioned); the DynamoDB lock table exists and a `plan`/`apply` acquires + releases a lock row.
**Rollback:** `terraform init -migrate-state` back to local (keep the old local file until migration is confirmed).

## Open questions

1. **OQ1 (Step 4)** — ~~share `myblog_front/.vscode/settings.json` or ignore the whole dir?~~ **ANSWERED 2026-06-05 (front #94): ignore the whole dir** (not shared) — both files untracked, `.vscode/` gitignored.
2. **OQ2 (Step 1)** — history-rewrite `bundle.zip` out (`git filter-repo`) or just `git rm --cached`? Default: `rm --cached` unless clone size is a real pain. *(Blocks Step 1 scope only.)*
3. **OQ3 (Step 5)** — ~~S3 backend bucket/region/lock-table naming + replication?~~ **ANSWERED 2026-06-06 (ws#264 defaults):** bucket `myblog-terraform-state-338183196042`, lock table `myblog-terraform-locks`, region `ap-northeast-2`, no replication. Owner may rename before apply.

## Decisions log

| Date | Decision | Step |
|------|----------|------|
| 2026-06-05 | Spawned from STAB-1 §Sequencing item 6. Remote backend = **S3 + DynamoDB lock** (STAB-1 OQ6, owner-ratified); scheduled in the hygiene tier, not ahead of P0/P1. | Step 5 |
| 2026-06-05 | Workspace confirmed **not** in a cloud-sync path → laptop loss / Time Machine is the state-loss vector the backend migration addresses. | Step 5 |
