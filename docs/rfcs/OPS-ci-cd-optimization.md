# OPS-ci-cd-optimization: measure the six repos' CI/CD and trim only what the measurement supports

- **Status**: accepted (owner approval 2026-10-16; scope Steps 1, 2, 3, 5; Steps 6, 7, 8 added by the owner's OQ3–OQ5 answers the same day)
- **Owner**: site owner
- **Created**: 2026-10-16
- **Plan row**: `docs/plan.md` → OPS-ci-cd-optimization
- **Authorization**: the owner asked on 2026-10-15 for a diagnosis of whether the test process is
  excessive and for an optimization based on it ("지금 테스트 과정이 과하진 않는지 진단해보고 분석해서
  cicd를 최적화해보자"). This document is the diagnosis plus the proposal. **No workflow file and no
  ruleset was changed while writing it.** Every step below is a separate PR and needs the owner's
  acceptance first; the required-check names in `CLAUDE.md` § Verification are bound to the
  `main-required-checks` rulesets, so a wrong edit there blocks every PR forever.

---

## Goal

Every PR gate and deploy pipeline across the six repositories costs what the measurement says it
needs. The two wastes the measurement actually found are gone: lock-drift round trips (9 of the
21 failed runs in 30 days) never reach CI, and the front deploy's S3 HTML sync (157 s median — 70 % of the `deploy` job, 42 % of the whole
push run) runs at a concurrency that fits 4,170 objects. The one workflow that has never
done anything is deleted. Each change states, on the same line, the minutes it saves and the
safety it gives up — and no change gives up safety without that line.

## Verdict first — the owner's question

**The test process is not excessive, in machine time or in money.**

| Measure (runs created 2026-09-16 … 2026-10-16) | Value |
|---|---|
| Job-minutes, the five repos with runs in the window | **296** — four public repos 283 (workspace 22, backend 81, front 144, worker 36) + private shared_db 13 |
| …of which billable | **≈ 17–25** — only `myblog_shared_db` is private (the other five are public, where standard GitHub-hosted runners are free); GitHub bills each job rounded up to a whole minute (17 jobs) and its 7 dynamic Dependency Graph runs count too |
| Allowance those minutes count against | 2,000 min/month **if** the account is on the Free plan (the plan tier is not readable with this session's token) — about 1 % |
| PR-gate wall-clock, median per repo | workspace 0.4 min · shared_db 0.8 · backend 1.6 · worker 1.7 · music 1.7 · front 2.6 |
| Merge → deployed + smoked, median per repo | backend 2.1 min · music 2.3 · worker 2.5 · front 6.3 (workspace and shared_db deploy nothing) |
| Matrices, extra OS or language versions | none — every job is `ubuntu-latest`, Python 3.12 or Node 20, one of each |

`myblog_music` had **zero runs in the window** (no PR since 2026-09-12); its figures come from its
last 30 runs (2026-08-29 … 2026-09-12) and are reported separately throughout.

Where the cost actually sits is not minutes but **round trips and one slow step**:

1. **21 of 209 runs failed (10.0 %)** (dynamic Dependency Graph runs excluded), and 9 of the 21 are one class — `requirements.lock is out of
   date` — which `scripts/check_requirements_lock.sh` would have caught locally in seconds.
2. **One step is 70 % of the front `deploy` job** (42 % of the whole push run): `Upload HTML/XML/JSON
   (no-cache)` re-uploads 4,170 HTML objects on every deploy, median 157 s, because a fresh build
   gives every file a new mtime.
3. **One workflow has never done anything**: `myblog_front/.github/workflows/code-review.yml` has
   run 481 times since 2026-05-25 and posted 0 comments ever; in the window its review job was
   skipped 18/18 (no `ANTHROPIC_API_KEY` secret).
4. **Push-to-`main` re-runs the entire PR gate on a tree that was byte-identical to the PR head in
   39 of 40 code-repo merges** — and the one push failure in the window was a flake in exactly that
   duplicate run, which held a front deploy for 17 minutes. The re-run is kept anyway; § Current
   state 4 records why.

## Non-goals

- **No change to any required-check context and no change to either ruleset.** `check` / `test` /
  `contract` / `integration` keep their names and their job ids. Renaming, deleting or
  path-filtering a required job locks every PR (SEC-system-hardening Step 5, hit live 2026-08-26).
- **No `paths:` filter on any workflow that carries a required check**, for the same reason. The one
  conditional proposed here (Step 4) is a step-level `if` inside a job that always runs.
- **No removal of the push-to-`main` gate re-run.** Measured, decided, recorded (§ 4 below).
- **No test authoring or rewriting**, beyond hardening the one flake that blocked a deploy (Step 5).
- **No change to deploy mechanics** — OIDC roles, `update-function-code`, S3 layout, CloudFront
  invalidation, post-deploy smokes — other than the S3 sync's concurrency setting.
- **No reinstatement of a review bot.** Deleting the dead workflow is not a decision to add another.
- ~~**No move of `myblog_music`'s integration suite off Neon.**~~ **Superseded 2026-10-16 by the
  owner (OQ3 → Step 7).** OPS-integration-db-locality kept music on Neon while its job was advisory;
  the job has gated `deploy` since 2026-08-28. The recall gate stays on a real catalog and stays
  deselected in CI; only the CI integration job moves.
- **No cost claim beyond the public-repo rule and the measured minutes.** The Actions billing API
  needs the `user` OAuth scope this session's `gh` token does not carry; it was not queried.

## Current state

Measured 2026-10-16 from the GitHub API, not from memory: `gh api repos/hyuntohoon/<repo>/actions/runs?created=>=2026-09-16`
(209 non-dynamic runs; the 16 dynamic Dependency Graph runs are excluded from every count) and
`…/runs/{id}/jobs` (410 jobs with step timings), failed-step logs via
`gh run view --log-failed`, rulesets via `…/rulesets/{id}`, PR up-to-dateness via
`…/compare/{merge-parent}...{pr-head}`. Workflow files read on `origin/main`: workspace `031e417`,
backend `17bc783`, front `5c4d0a4`, music `2c7d791`, worker `5faea02`, shared_db `471200a`.

### 1. Inventory

| Repo | Workflow | Triggers | Jobs on a PR | Extra on push to `main` | Required contexts (ruleset) |
|---|---|---|---|---|---|
| `myblog_backend` | `deploy.yml` | push main · PR main · dispatch | `check` (lock check, arm64 repeatability + Lambda-image import smoke, pyright) · `test` (`pytest -m "not integration"`) · `contract` (openapi export + diff) · `integration` (local Postgres 16, canonical schema at a pinned shared_db SHA, zero-skip enforcement) | `deploy` needs all four; build zip → Lambda → health curl | `check`, `test`, `contract`, `integration` |
| `myblog_music` | `deploy.yml` | push main · PR main (no dispatch) | `test` (lock check, repeatability + import smoke, pyright, unit) · `contract` · `integration` (Neon test branch via `TEST_DB_URL` secret + LocalStack SQS; grep-based DB-skip detection) | `deploy` needs all three (since 2026-08-28); same shape as backend | `test`, `contract`, `integration` |
| `myblog_worker` | `deploy.yml` | push main · PR main · dispatch | `test` (lock check, repeatability + import smoke, local Postgres 16 + canonical schema + fixtures, whole `tests/` incl. integration, zero-DB-skip enforcement, Allure + JUnit artifact upload) | `deploy` needs `test`; build zip → Lambda → empty-event invoke | `test` |
| `myblog_front` | `main.yml` | push main · PR main · dispatch | `check` (pnpm store cache, `api.gen.ts` vs workspace-`main` contract, `astro check`, lint, vitest — **no `pnpm build`**) | `deploy` needs `check`; build → `s3 sync` ×2 → invalidation → homepage curl | `check` |
| `myblog_front` | `code-review.yml` | PR main (non-draft) | `keycheck` → `code-review` (skipped when the key secret is absent — it is) | — | — |
| `myblog_shared_db` (private) | `ci.yml` | push main · PR main | `test` (local Postgres 16, `pip install -e .[dev]`, parity pytest, `cmp` canonical schema vs workspace `main`) | nothing deploys | `test` |
| `myblog-workspace` | `workspace-check.yml` | PR | `workspace-check` (`terraform fmt/validate`, invariant parser tests, plan/RFC pointers, merged OpenAPI vs backend+music `main`) | — | **none** (ruleset `main-protection` only) |
| `myblog-workspace` | `merge-contract.yml` | dispatch · `repository_dispatch` | opens a PR with the re-merged spec | — | last run 2026-06-25; the service-side dispatch 401s (`AGENTS.md`), so the path is dead and merging is manual |
| `myblog-workspace` | `verifier-drift.yml` | daily 03:20 KST · dispatch | byte-diff of the two `app/core/auth.py` copies | — | — |

Also present but not ours: GitHub's automatic dependency submission shows up as a dynamic
"Dependency Graph" workflow on backend, worker and shared_db (4–7 runs each). `myblog_worker` still
lists `.github/workflows/test-db-sync.yml` as an active workflow although the file left `main`
(last run 2026-07-28); with no file it has no trigger and costs nothing.

Concurrency is already right: PR runs are grouped per PR with `cancel-in-progress`, deploys are
serialized per repo, and the 2026-08-02 PR-vs-deploy queue bug is fixed in all four deploy
workflows (1 cancelled run in the window — a superseded fixup push, as designed).

### 2. Volume and wall-clock (runs, 30 days)

| Repo | Workflow | Event | Runs | Median | p90 | Failed |
|---|---|---|---|---|---|---|
| workspace | `workspace-check` | PR | 64 | 0.4 min | 0.5 | 6 (5 PRs; 2 merged red) |
| workspace | `verifier-drift` | schedule | 29 | 0.1 | 0.1 | 0 |
| backend | `deploy.yml` | PR | 17 | 1.6 | 1.9 | 7 (+1 cancelled) |
| backend | `deploy.yml` | push | 8 | 2.1 | 2.3 | 0 |
| front | `main.yml` | PR | 18 | 2.6 | 2.8 | 0 |
| front | `main.yml` | push | 17 | 6.3 | 6.9 | 1 |
| front | `code-review.yml` | PR | 18 | 0.1 | 0.1 | 0 (review job skipped 18/18) |
| worker | `deploy.yml` | PR | 15 | 1.7 | 2.0 | 6 |
| worker | `deploy.yml` | push | 6 | 2.5 | 2.6 | 0 |
| shared_db | `ci.yml` | PR | 9 | 0.8 | 0.9 | 1 |
| shared_db | `ci.yml` | push | 8 | 0.8 | 0.8 | 0 |
| music (last 30 runs, outside the window) | `deploy.yml` | PR | 20 | 1.7 | 2.0 | 3 (+2 cancelled; one 67.7 min outlier was queue wait on 2026-09-12, conclusion success) |
| music (same) | `deploy.yml` | push | 10 | 2.3 | 2.5 | 0 |

Merged PRs in the window: workspace 56, front 17, backend 8, shared_db 8, worker 7, music 0.

### 3. Where the seconds go (step medians, successful jobs)

**Python services.** The largest step in every PR gate is `Verify repeatable arm64 Lambda bundle`:
backend 54 s, music 57 s, worker 43 s. It installs the lock twice with `--no-cache-dir`, diffs the
two distribution manifests, then runs the bundle under the Lambda arm64 image through QEMU to
import the handler. It is 60 % of backend `check` (1.5 min) and the critical path of the gate — the
other three backend jobs finish in 0.3–0.9 min. It runs on every PR and every push whether or not
the lock changed. Per-job `pip install` is 10–16 s and is repeated in all four backend jobs plus
`deploy` (five installs per push); nothing uses a pip cache. Container start is 23–26 s for
Postgres 16 (backend, worker, shared_db) and 41 s for LocalStack (music). Suites themselves are
cheap: backend unit 12 s, integration 7 s; worker 11 s; music unit 5 s, integration 36 s against
Neon; shared_db parity 4 s.

**Front.** `check` is vitest 74 s + `astro check` 25 s + lint 20 s (+ ≈ 15 s of setup, the pnpm
store cache hits). `deploy` is build 30 s, `_astro/**` sync 10 s, and **`Upload HTML/XML/JSON
(no-cache)` 157 s median / 176 s p90** — 70 % of the 226 s `deploy` job and 42 % of the 6.3 min
push run. The bucket holds 6,851 objects, 4,170 of them HTML and
4,145 of those under `artist/`; `aws s3 sync` compares size and mtime, a fresh build gives every
file a new mtime, so every HTML object is re-uploaded on every deploy at the CLI's default of 10
concurrent requests. (`--size-only` would make the step fast and is **not** proposed: a page that
changes content without changing size would never reach S3.)

**Workspace.** `workspace-check` is 0.31 min; the daily verifier diff 0.05 min.

### 4. Push-to-`main` runs the PR gate again — measured and kept

All five `main-required-checks` rulesets have `strict_required_status_checks_policy: false`: a PR
does not have to be up to date with `main` to merge. The push run on the squash commit is therefore
the only run that ever tests the merged tree. How often does it test something new?

| Repo | Merged PRs | PR head already up to date with `main` at merge | Behind |
|---|---|---|---|
| backend | 8 | 8 | 0 |
| front | 17 | 17 | 0 |
| worker | 7 | 7 | 0 |
| shared_db | 8 | 7 | 1 (#89, 1 commit) |
| workspace | 56 | 51 | 5 (#1026, #1057, #1058, #1060, #1062) |

So in 39 of 40 code-repo merges the push run re-tested a byte-identical tree. The only push failure
in the window is front `edfe1e6` (2026-10-15 13:17Z): `MemberProfile.test.tsx` failed 4 cases on
the squash commit, having passed on the identical PR tree 10 minutes earlier (run 38739494246,
113/113 files). The deploy of that fix shipped 17 minutes later on the next merge's run
(`0584439`, 13:32Z). Push failures over 90 days: front 2026-08-30 (`AddToBucketMenu.test.tsx`, the
flake class recorded in the `feedback-flake-attribution-needs-a-baseline` memory), front
2026-08-26 (`configure-aws-credentials`, the OIDC cutover), backend 2026-08-19 (`contract`), worker
2026-07-28 (`test`, the Neon test-branch schema lag of that week). The PR heads of those four are
no longer fetchable, so whether each was stale-base or flake was **not classifiable** — not
attempted, not "not reproducible".

**Decision: keep the re-run, as a job that always executes.** (a) With `strict: false` it is the
only test of the tree that deploys, and GitHub cannot express "deploy needs the PR run of this same
tree". (b) It costs 0.8–2.6 min of free minutes per merge; the deploy delay it adds is real only
when it fails. (c) `strict: true` plus no push gate would keep the safety but invalidate every other
open PR's green on each merge — with several sessions live at once (`session-claim.sh` listed six on
2026-10-16) that is one round trip per merge per open PR; not measured here, but plainly more than
the one run it saves. Merge queue, which solves exactly this, is not available on user-owned
repositories. (d) The one design that removes the duplicate without losing the safety — a push-time
step that skips the test steps when a green `pull_request` run exists for the identical tree
(`HEAD^{tree}` match), inside a job that still reports its context — needs `actions: read` on the
token, an API lookup in every push run and a correctness argument for the tree match. It is
recorded as OQ6 rather than proposed, because what it would remove is 0.8–2.6 min of wall-clock per
merge and one flake-held deploy in 30 days. That real cost is **reduced** by Step 5, not removed:
front has had three such flakes since 2026-08-30 (08-30, 09-01, 10-15), and fixing one does not
stop the next.

### 5. Failures, classified (21 of 209 runs)

| Class | Runs | Where | Catchable before CI? |
|---|---|---|---|
| `requirements.lock is out of date` | **9** | backend 4 (35289042053 also failed `contract`/`integration`/`test` for the same cause: a `requirements.txt` shared_db SHA bump that the lock did not carry, so the installed package lacked the new model), worker 5 | **Yes** — `scripts/check_requirements_lock.sh` exists in all three services and nothing runs it locally. 7 of the 9 were the 2026-10-13/15 shared_db pin bumps (OPS-project-stabilization 2D, FEAT-spotify-library-autosync). |
| merged OpenAPI byte drift (`workspace-check`) | 6 runs on 5 PRs | workspace | Yes — `python scripts/check_workspace_invariants.py` against both service `main` specs. The drift opened when backend #184 merged (2026-10-13 10:34Z) and closed when ws #1058 merged (2026-10-15 13:26Z). Three of the five PRs changed no OpenAPI (#1059, #1060, #1061 — the last touched `schema.sql`); **two merged red** (#1059 28 s after its run started, #1061 41 s after); #1060 re-ran green before merging, #1022 is open and green since, #1032 was a contract PR fixed before merge. Red merges are possible because the check is not required. |
| real code failure | 4 | backend `test`+`integration` ×2 (same `StopIteration`, two pushes), backend pyright ×1, shared_db 2 tests ×1 | n/a — the gate doing its job |
| workflow-side schema pin stale | 1 | worker 35289160822 (`UndefinedTable`, relation `user_artist_follow_exclusions` does not exist: the `ref:` copy of the shared_db pin in `deploy.yml` lagged `requirements.txt`) | Yes — the "second copy of the pin" the workflow comment already warns about |
| flake on an identical tree | 1 | front `edfe1e6` | n/a |

Every lock-drift run still executes the sibling jobs to completion (they do not depend on the
lock step), so each costs one full gate run plus a fix commit plus a second full run.

### 6. Dead and dormant

- `myblog_front/.github/workflows/code-review.yml`: 18 PR runs in the window, `code-review`
  skipped 18/18 — `ANTHROPIC_API_KEY` is not among the repo's secrets (verified with
  `gh api repos/hyuntohoon/myblog_front/actions/secrets`). 481 runs since 2026-05-25 (before front
  #387 on 2026-08-09 the key check lived inside the review job, so those runs read `success`). A
  GitHub search for PR comments by `github-actions[bot]` on `myblog_front` returns **0**; the one
  "Code review" text hit (#204) is the owner's own comment. It has never reviewed anything.
- `myblog-workspace/.github/workflows/merge-contract.yml`: last run 2026-06-25; the automatic
  service→workspace dispatch 401s and `AGENTS.md` § cross-repo already documents the manual
  `tools/merge_openapi.py` path as the procedure.
- `myblog_worker` uploads `allure-results` (≈ 1.2 MB) and `pytest-results.xml` on every run — 131
  artifacts retained 90 days. No document outside `docs/archive/` (STAB-1, STAB-6, 2026-06) reads
  them; the JUnit file is consumed in-job by the zero-skip step, so the upload is evidence only.
  Public repo: storage is free, so this is noise, not cost.

### 7. What the gate does not cover (found while measuring; safety items, not cuts)

- **Front `check` never builds.** `pnpm build` runs only in `deploy`, after merge. In 90 days no
  push failed at the build step (the failures were tests, `api.gen.ts` sync, lint), so this is a
  latent gap, not a measured one. Closing it costs ≈ 25–30 s on every front PR (Step 8).
- **`workspace-check` is advisory.** 6 red runs on 5 PRs in 30 days, 2 of which merged red. Open item from
  SEC-system-hardening Step 6, restated with numbers in OQ1.
- **Music's integration gate is the odd one out**: Neon test branch + `TEST_DB_URL` secret +
  grep-based skip detection, while backend and worker run local Postgres with canonical schema and
  JUnit-based zero-skip enforcement. OPS-integration-db-locality kept music on Neon because its job
  was then advisory and its recall gate needs a real catalog; the job became a deploy gate on
  2026-08-28 (`deploy.needs`), so the premise moved. OQ3.

## Target state

- **Lock drift is caught at commit time**, not by CI: each Python service carries a versioned
  pre-commit hook that compares the `# requirements.txt sha256:` line in the **staged**
  `requirements.lock` with the hash of the **staged** `requirements.txt` — offline, no `uv`, no
  venv, milliseconds — enabled per clone with one documented `git config core.hooksPath` line. The
  CI step (`check_requirements_lock.sh`, the full recompile) stays exactly as it is. Expected: −9
  failed runs and −9 fix commits per month at the current pace. Lost in CI: nothing. Stated holes:
  a clone that never ran the enable line, or a branch cut before the hook file existed, runs no
  hook and falls back to CI — the status quo; and unsetting `core.hooksPath` is read by the Bash
  guard as skipping hooks (hard rule 10), so that rollback form needs the owner.
- **The front HTML sync runs at 64 concurrent requests** instead of 10, set by
  `aws configure set default.s3.max_concurrent_requests 64` immediately before the two `s3 sync`
  steps. Same objects, same comparison, same `--delete`; nothing lost. Expected: 157 s → under
  40 s (to be measured on the first deploy; the number is the step's verification, not a promise).
- **`code-review.yml` is gone** from `myblog_front`. PRs show one check row, `check`, which is the
  only required context. Nothing lost: it has never run.
- **(Optional) The repeatability manifest diff runs on PRs only when its inputs changed** —
  `requirements.lock`, `requirements*.txt`, `scripts/compile_requirements.sh`,
  `scripts/distribution_manifest.py` or the workflow file differ from the PR base — while the
  Lambda-image import smoke in the same step runs unconditionally, and push runs are unchanged. The
  job and its context still run on every PR, so the ruleset is untouched. Expected: ≈ 20–25 s off
  the PR gate's critical path in all three services (backend `check` 1.5 → ≈ 1.2 min) — an
  estimate, because the step is one timed block and part (c) keeps one install, the image pull and
  the QEMU import. Lost: a reproducibility regression whose cause is index-side rather than
  lock-side surfaces on the push run instead of the PR run — still before `deploy`, which needs
  that job, but it then turns `main` red and blocks the next unrelated merge's deploy; and the
  likeliest index-side source (build isolation fetching `setuptools` while pip builds the shared_db
  git dependency) is outside every listed input, so the conditional can never see it.
- **The flake that held a deploy is measured and fixed** the way the 2026-08-30 and 2026-09-01
  flakes were: 20 full-suite runs on `main`, fix the race if it reproduces, mutation-check the fix.
- **Dormant pieces are decided, not left**: `merge-contract.yml` (delete, with the `AGENTS.md` line
  updated to say the manual path is the only path) and the worker Allure upload (delete; keep the
  JUnit upload as the skip-enforcement evidence). OQ4 — the owner may prefer to keep either.

## Steps

Steps 1–3 and 5 are independent and additive (one PR each, any order, may share a session). Step 4
is optional and waits on OQ2 (declined). Steps 6, 7 and 8 were added or unblocked by the owner's
OQ3/OQ4/OQ5 answers on 2026-10-16; they are likewise independent and additive (one PR per repo,
any order, may share a session). None touches a required-check name, a ruleset,
Terraform, a contract, an auth guard or a migration. Steps 2, 4, 6, 7 and 8 edit deploy or CI workflows,
which `CLAUDE.md` § Subagents counts as an infra touch: `reviewer` is mandatory there, and hard rule
11 means Claude implements them directly, not through a subagent or Codex.

### Step 0 — this diagnosis (docs only) — **delivered by the PR that adds this file**

### Step 1 — offline lock-drift check as a versioned pre-commit hook (backend, music, worker) — **delivered 2026-10-16** (backend #187, music #80, worker #113)

> **Delivered.** `scripts/githooks/pre-commit`, byte-identical in the three repos, reads both blobs with
> `git cat-file blob :<file>` (reviewer: immune to a future textconv setting, unlike `git show`). Scratch-clone
> scenarios: un-recompiled bump, recompiled-but-unstaged lock, lock-only stale hash, header removed, lock removed
> from the index → refused; both staged, unrelated file → accepted; mutant `[ x != x ]` let the bump through.
> `sha256sum` and `shasum` branches and `/bin/dash` exercised. Deployed with no runtime change; prod smoke 30/30.
> **Enabled 2026-10-16 on the owner's approval** in the three clones (`core.hooksPath=scripts/githooks`, applies
> to every worktree of each clone). Verified live: a worktree cut from `origin/main` refused an un-recompiled
> `requirements.txt` commit. Checkouts still on a `main` older than the hook file run nothing until pulled.

`requirements.lock` already records the hash of the `requirements.txt` it was compiled from
(`# requirements.txt sha256: …`, written by `scripts/compile_requirements.sh`). Add
`scripts/githooks/pre-commit` to each service that, when `requirements.txt` or `requirements.lock`
is staged, reads both **staged** blobs (`git show :requirements.txt`, `git show :requirements.lock`),
hashes the first, compares it with the line in the second, and refuses the commit on mismatch,
printing the one-line fix (`./scripts/compile_requirements.sh && git add requirements.lock`). It
checks the index, not the working tree, so a recompiled lock that was not `git add`-ed is refused
too. README gains the enable line (`git config core.hooksPath scripts/githooks`). Three PRs, one
per repo, or one session.

Why not run `check_requirements_lock.sh` itself in the hook: it delegates to
`compile_requirements.sh`, which requires exactly `uv 0.12.7` on PATH (absent from the owner's
shell today; present in two of the three `.venv`s) and fetches the private shared_db git dependency
from the network, so a full-check hook would refuse commits from any non-activated or offline
shell, and hard rule 10 then leaves no way past it but the owner. The full check stays in CI, where
it also catches what the hash cannot — a hand-edited pin or a changed index freeze.

Saves ≈ 9 failed gate runs + 9 fix commits a month (all 9 observed failures were a
`requirements.txt` edit without a recompile, which the hash catches); loses nothing in CI. Stated
holes: a clone that never ran the enable line, or a worktree cut from a `main` older than the hook
file, runs no hook — git is silent about a missing hooks directory — and falls back to the CI gate,
which is the status quo.

**Verification**:
```
# hook enabled: bump the shared_db SHA in requirements.txt, do NOT recompile
git add requirements.txt && git commit -m x            # expect: refused, hash mismatch + the fix line
./scripts/compile_requirements.sh && git commit -m x   # expect: refused — lock recompiled but not staged
git add requirements.lock && git commit -m x           # expect: accepted
# CI on the PR: check/test unchanged and green
```

**Rollback**: delete the hook file in a commit. `git config --unset core.hooksPath` also works, but
the Bash guard reads a `core.hooksPath` change as skipping hooks (hard rule 10), so that form is the
owner's.

### Step 2 — front S3 HTML sync concurrency — **delivered 2026-10-16** (front #464)

> **Delivered and measured.** First deploy after merge (`83f29c3`, run 38780929262): `Upload HTML/XML/JSON
> (no-cache)` **33 s** (baseline 157 s median / 176 s p90), 4,183 objects uploaded — same work; `deploy` job
> 102 s (was 226 s). Next deploy (`ac4cc34`): 36 s. Post-deploy health and prod smoke green.

In `myblog_front/.github/workflows/main.yml` `deploy`, before `Upload _astro/** (immutable)`, add
`aws configure set default.s3.max_concurrent_requests 64` (and `max_queue_size 10000`). No flag
on the sync commands changes; `--size-only` is explicitly rejected (§ 3). Saves ≈ 2 min of every
front deploy; loses nothing.

**Verification**:
```
gh run view <first deploy run after merge> --repo hyuntohoon/myblog_front --json jobs \
  --jq '.jobs[] | select(.name=="deploy") | .steps[] | select(.name | startswith("Upload HTML")) | {started_at, completed_at}'
# expect well under the 157 s median; post-deploy smoke green; CloudFront invalidation unchanged
```

**Rollback**: revert the one-line PR; the next deploy is slow again, nothing else changes.

### Step 3 — delete `myblog_front/.github/workflows/code-review.yml` — **delivered 2026-10-16** (front #465)

> **Delivered.** The PR itself reported only `check`; the next PR (#466) produced no `code-review`/`keycheck` run.

One PR removing the file. Saves 18 no-op runs a month and one noise row per PR; loses nothing (0
reviews ever). The ruleset requires only `check`, so no required context disappears.

**Verification**:
```
gh pr checks <the PR itself> --repo hyuntohoon/myblog_front    # expect: only `check`
gh api repos/hyuntohoon/myblog_front/rulesets/21564100 --jq '.rules[]|select(.type=="required_status_checks")'   # still ["check"]
```

**Rollback**: `git revert`.

### Step 4 — (optional) gate the repeatability diff on its inputs, PR runs only

In each of the three `deploy.yml` files, split `Verify repeatable arm64 Lambda bundle` into (a) a
changed-files step (`git diff --name-only origin/main...HEAD` on the listed inputs; needs
`fetch-depth: 0` or a targeted fetch), (b) the double-install + manifest diff with
`if: github.event_name != 'pull_request' || steps.changed.outputs.lock == 'true'`, and (c) the
single install + Lambda-image import smoke, unconditional. Saves an estimated 20–25 s on the PR
gate's critical path; loses PR-time (not deploy-time) detection of an index-side reproducibility
change on PRs that do not touch the lock, which then reddens `main` and blocks the next deploy —
and the likeliest such cause is invisible to the changed-files list by construction (Target state).
Blocked on OQ2.

**Verification**:
```
# PR touching only app code: step (b) skipped, step (c) ran, `check`/`test` green
# PR touching requirements.lock: (b) and (c) both ran
# push to main: (b) and (c) both ran, deploy followed
```

**Rollback**: revert; the step is a single block again.

### Step 5 — the `MemberProfile.test.tsx` flake — **delivered 2026-10-16** (front #466)

> **Delivered; root cause reproduced deterministically.** The plain 20× full-suite measurement below was run
> first and is recorded as **not informative**: `MemberProfile` 0/20, while 4/20 runs failed elsewhere
> (`BucketBoard` and two others, `Test timed out in 5000ms`) only when a run took > 120 s against 56 s normal —
> host load average 51–99 on 8 cores from concurrent sessions. CI hit the flake at normal speed.
>
> Cause: `MemberProfile` attaches its `ENT_ALBUM_STATE_CHANGED` listener in a passive effect; `findByRole` on
> the dashboard nav resolves at the commit, RTL then waits one `setTimeout(0)`, and when that wins against
> React's scheduler (`setImmediate`) the test dispatches to no listener. Its unconsumed `mockImplementationOnce`
> entries survive `vi.clearAllMocks()` and feed the next three tests — one race, four failures, the exact CI
> signature. A temporary harness that delays `setImmediate` by 20 ms (setup file loaded before
> `src/test/setup.ts`) reproduced those 4 failures with the same 3 messages in 4/5 runs on `main`.
>
> Fix (test only): wait for the `addEventListener(ENT_ALBUM_STATE_CHANGED)` call made after mount (spy), and
> reset the `fetchMemberProfile` once-queue per test. Harness: fixed 20/20 pass; mutant without the listener
> wait 9/10 fail. **The fix recorded for earlier flakes, `await act(async () => {})`, does not work here** —
> React 19 does not flush inside `act` a passive effect it scheduled outside `act`. The load-only `BucketBoard`
> 5 s timeouts are a separate observation, not acted on.

Measure on `main` as the memory prescribes: 20 full-suite `pnpm test` runs (full suite, not the
file alone — the 2026-09-01 flake was 0/12 alone and 1/10 under load). If ≥ 1/20, fix the race
(the recorded class is `findBy*` resolving at commit before passive effects; `await act(async () =>
{})` after it), then disable the fix and confirm the test goes red. Gains: this flake no longer
holds a deploy; the class remains (three since 2026-08-30), so the 20-run measurement is the part
to keep using. Loses nothing.

**Verification**:
```
for i in $(seq 20); do pnpm test --run >/dev/null 2>&1 && echo ok || echo FAIL; done | sort | uniq -c   # before and after
```

### Step 6 — dormant cleanup (OQ4: delete both)

**Workspace PR.** Delete `.github/workflows/merge-contract.yml`; change `AGENTS.md` § cross-repo
and `docs/architecture.md` (the paragraph that still describes the `repository_dispatch` auto-PR)
to say the manual `tools/merge_openapi.py` path is the only path. The workspace repo's
`WORKSPACE_GITHUB_TOKEN` secret is then unreferenced there; the same-named secret is still read by
`myblog_front/.github/workflows/main.yml` (contracts checkout), so this removes one secret copy, not
the PAT. Deleting the workspace copy is a repo-settings action for the owner, after merge.

**Worker PR.** Remove all three traces together — the `Upload Allure results` step and
`--alluredir` in `deploy.yml`, `--alluredir=allure-results` in `tests/pytest.ini` `addopts`, and
`allure-pytest` in `requirements-test.txt` (dropping only the dependency would make every pytest
invocation fail on an unrecognised argument). Keep `--junitxml` and the JUnit upload: the zero-skip
step reads that file. The `.gitignore` lines are left (harmless).

Loses: a manual `workflow_dispatch` that opens a merged-spec PR — not used since 2026-06-25 — and an
artifact nobody reads.

**Verification**: `gh workflow list` on the workspace no longer shows `Merge OpenAPI contracts`;
`grep -rn allure` in the worker tree returns only `.gitignore`; worker `test` green on the PR with
the zero-skip step passing.

### Step 7 — music integration job on local Postgres (OQ3: yes)

Rewrite the `integration` job in `myblog_music/.github/workflows/deploy.yml` after backend's: a
`postgres:16` service, `tests/canonical_schema.sql` checked out from `myblog_shared_db` **at music's
own model pin**, read from `requirements.lock` by a step in the job (`8319a56` on 2026-10-16, not
backend's `b5d0670`; copying another service's ref is the ORM-vs-schema drift class, and a literal SHA
in the workflow would be a second copy of the pin that drifts on the next bump — the class behind
the worker's 2026-10 `UndefinedTable` failure in § 5), and
`TEST_DB_URL` pointing at the service container. The localstack service stays. The grep-based
"Fail on DB-reason skips" step becomes backend's JUnit zero-skip check, which fails on any skip
regardless of reason text. The job id stays `integration`, so the required context is unchanged.
`-m "integration and not recall_gate"` stays: `test_search_recall_gate.py` also reads `TEST_DB_URL`
and would silently run against an empty local DB if the deselect were dropped — the step comment
says so.

Why it is safe: the three DB-bound tests (`test_album_edition_collapse.py`,
`test_artist_top_tracks.py`, `test_unified_search_expansion.py`) insert their own rows in a
rolled-back transaction and probe only `information_schema`; `test_candidates_localstack.py` uses
no DB. The canonical schema creates `pgcrypto` and `pg_trgm`.

Gains: no Neon test-branch migration lag for music (the manual-apply step in the
`reference-neon-test-branch-migration-drift` procedure no longer applies to music CI), a stricter
skip check, no CI dependency on an external DB. Loses: nothing the job asserted — no test reads
Neon-specific data. The `TEST_DB_URL` repo secret on music (and the unused copies on backend and
worker) can then be deleted by the owner; the recall gate, run by hand, still needs a real catalog
URL, supplied locally.

**Verification**: on the PR, `integration` green with the zero-skip step reporting zero skips and
the same test count as the last Neon run; a mutant that drops a column the tests probe from the
loaded schema makes those tests `pytest.skip`, and the zero-skip step turns the job red.

### Step 8 — `pnpm build` in front `check` (OQ5: yes, dummy API URLs)

Add a `pnpm build` step to the front `check` job with **dummy** `PUBLIC_API_URL` /
`PUBLIC_BACKEND_API_URL` (a refused local port, e.g. `http://127.0.0.1:9`) and no Cognito/Spotify
secrets. An env-less build fails: `astro.config.ts` declares both URLs as required `envField.string`,
which `astro check` does not enforce (sync mode) but `astro build` does. With refused URLs every
build-time fetch (`index.astro`, `review/[slug].astro`, `members/[handle].astro`,
`artist/[id].astro`) takes its existing fallback, so the PR build loads no production API.

Gains: compile, bundle, content-collection and PWA-glob breakage is caught before merge (+≈ 25 s per
front PR, measured: `Build Astro` 25 s on run 38886655030). Stated divergence from the deploy build:
member pages and catalog-only artist pages are not rendered in the PR build, so a runtime error in
those templates still surfaces only in `deploy`; the build still reaches Google Fonts, so it is
API-free, not network-free. The deploy job's build is unchanged.

**Verification**: locally, `pnpm build` with only the two dummy URLs set succeeds; on the PR,
`check` green with the build step present and its duration recorded; a mutant that `astro check`
cannot see — a render-time `throw` in a page's frontmatter — passes `astro check` and fails the build
step (a missing-module import would not prove the step: `astro check` already catches it).

---

## Open questions

1. **Should `workspace-check` become a required check?** (SEC-system-hardening Step 6 open item,
   now with numbers.) If yes: a service merge that changes `openapi.json` turns every open workspace
   PR red until the contract PR lands — the contract PR itself goes green, so there is no deadlock,
   and the documented order (service → workspace → front) already requires that sequence. The cost:
   in this window the drift lasted two days (backend #184, 2026-10-13 10:34Z → ws #1058, 2026-10-15
   13:26Z); every workspace PR in that time would have waited, including the `docs/plan.md` cleanups
   that *Done* requires, and each would need a manual re-run after the contract landed because
   `workspace-check` reads the service `main`s live and does not re-trigger. If no: status quo — two
   PRs merged red in 30 days, both with the drift already known. Blocks nothing in this RFC; it is a
   ruleset change the owner makes in repo settings.
2. **Is Step 4 worth a conditional in three deploy workflows** for an estimated 20–25 s on a free
   runner? Recommendation: no, unless the PR gate's wall-clock starts to matter; the gain is small,
   the step is the one that proves the bundle is reproducible, and the likeliest failure source is
   one the conditional cannot see. Blocks Step 4.
3. **Should `myblog_music`'s integration job move to local Postgres** like backend and worker, now
   that it gates `deploy`? Keeps the recall gate on a real catalog either way (it is deselected in
   CI already). Would remove the `TEST_DB_URL` secret and the Neon-lag false-green class from
   music. Blocks nothing here; needs its own small RFC or a row. **Answered 2026-10-16: yes, as
   Step 7 of this RFC.**
4. **Step 6 deletions** — keep `merge-contract.yml` as a manual tool, or the Allure upload as
   evidence? Blocks Step 6. **Answered 2026-10-16: delete both (Step 6).**
5. **Should `pnpm build` join front `check`** (+≈ 25 s per PR, measured in Step 8) to close the latent build gap (§ 7)?
   Blocks nothing; a one-line addition if yes. **Answered 2026-10-16: yes, with dummy API URLs
   (Step 8).**
6. **Skip-by-tree on push** (§ 4 (d)): a push-time step that skips the test steps when a green
   `pull_request` run already exists for the identical tree, inside a job that still reports. Removes
   the duplicate run in ≈ 39 of 40 merges (0.8–2.6 min of deploy latency each) without losing the
   merged-tree test, at the price of `actions: read` on the token, an API lookup per push, and a
   tree-match argument that has to be right. Not proposed as a step; needs the owner's yes and its
   own small design. Blocks nothing.

## Decisions log

| Date | Decision | Step |
|---|---|---|
| 2026-10-16 | Keep the push-to-`main` gate re-run as an always-executing job; the measured duplication (39/40 identical trees) is the price of `strict: false` under concurrent sessions. The skip-by-tree variant is OQ6, not a step; Step 5 reduces the flake cost but does not remove the class. | — |
| 2026-10-16 | No pip cache: installs are 10–16 s per job for 25–39 pinned packages and run in parallel jobs; a cache save/restore costs about the same seconds. | — |
| 2026-10-16 | Never `--size-only` on the HTML sync; concurrency only. | 2 |
| 2026-10-16 | No `paths:` filter and no required-context change anywhere in this RFC. | all |
| 2026-10-16 | **Accepted by the owner** for Steps 1, 2, 3 and 5. Step 4 is not taken (OQ2, recommendation "no"); Step 6 stays blocked on OQ4. | 1, 2, 3, 5 |
| 2026-10-16 | OQ1 answered **no** by the owner: `workspace-check` stays advisory; reading its result before a workspace merge remains Claude's self-attested gate. No ruleset change. | — |
| 2026-10-16 | OQ6 answered **no** by the owner: no skip-by-tree on push; the push-to-`main` re-run stays as decided above. | — |
| 2026-10-16 | Steps 1, 2, 3, 5 delivered (backend #187, music #80, worker #113, front #464, #465, #466); prod smoke 30/30 after each deploy. Remaining: OQ3, OQ4 (→ Step 6), OQ5. | 1, 2, 3, 5 |
| 2026-10-16 | Owner approved enabling the hook: `core.hooksPath=scripts/githooks` set in the backend, music and worker clones; live refusal verified. | 1 |
| 2026-10-16 | OQ3 answered **yes**: music's CI integration job moves to local Postgres + canonical schema at music's own shared_db pin, JUnit zero-skip; recall gate stays deselected. Supersedes this RFC's Non-goal and OPS-integration-db-locality's music carve-out. | 7 |
| 2026-10-16 | OQ4 answered **delete both**: `merge-contract.yml` (with `AGENTS.md` and `docs/architecture.md`) and every worker Allure trace; JUnit upload kept. | 6 |
| 2026-10-16 | OQ5 answered **yes, dummy API URLs**: `pnpm build` in front `check` with refused-port API URLs and no secrets, so no PR build loads production; divergence from the deploy build recorded in Step 8. | 8 |

## Appendix — reproducing the numbers

```
# runs (30 d) and jobs with step timings
gh api "repos/hyuntohoon/<repo>/actions/runs?created=>=2026-09-16&per_page=100" --paginate --jq '.workflow_runs[]'
gh api "repos/hyuntohoon/<repo>/actions/runs/<id>/jobs" --jq '.jobs[] | {name,conclusion,started_at,completed_at,steps}'
# failed step + cause
gh run view <id> --repo hyuntohoon/<repo> --log-failed
# required contexts and strictness
gh api repos/hyuntohoon/<repo>/rulesets/<id> --jq '.rules[] | select(.type=="required_status_checks") | .parameters'
# PR head up to date at merge?  behind_by == 0
gh api "repos/hyuntohoon/<repo>/compare/<merge-commit-parent>...<pr-head-sha>" --jq .behind_by
# front bucket shape
aws s3 ls s3://myblog-prod-web --recursive --summarize | tail -2
```
