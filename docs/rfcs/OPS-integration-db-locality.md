# OPS-integration-db-locality: run the integration suite against a local Postgres, then let it gate deploy

- **Status**: draft
- **Owner**: 오너
- **Created**: 2026-08-26
- **Plan row**: `plan.md` → OPS-integration-db-locality

---

## Goal

`myblog_backend`'s integration suite runs against a Postgres service container in the CI job itself —
schema loaded from the committed canonical DDL, catalog rows from a committed fixture — finishing in
roughly a minute instead of 13. Once it is that fast, `deploy` depends on it, closing the gap where a
commit whose DB tests fail still ships to production today.

The two halves are one RFC because they are sequential, not merely related: gating `deploy` on a
13-minute job would make every merge wait 13 minutes for a Lambda that currently ships in 40 seconds.
The suite has to get fast **before** it is allowed to gate.

## Non-goals

- **No move of `myblog_music`'s recall gate.** `tests/integration/test_search_recall_gate.py` measures
  Hit@1/Hit@5 against a real catalog and says so in its own docstring ("it never seeds, so it points at
  whatever catalog the gate DB holds"; a small branch "will report most cases as data-misses rather than
  recall results"). Pointing it at a synthetic fixture would not make it faster, it would make it
  meaningless. It stays on a real catalog DB.
- **No removal of Neon from CI.** A small Neon-targeted job remains for behavior only Neon has — see
  Step 4. Deleting it would trade 12 minutes for a blind spot.
- **No test rewrites.** Assertions and test bodies stay as they are; the only thing that changes is
  where the rows they read come from. If a test cannot pass on a seeded fixture without changing its
  assertion, that is a finding to report, not a licence to edit the assertion (OQ2).
- **No `pytest-xdist` in this RFC.** Parallelism becomes *safe* after this work (each run owns its own
  database instead of sharing one Neon branch) but it is a separate change with its own failure modes.
- **No change to how humans apply migrations.** The Neon test branch and the
  `reference-neon-test-branch-migration-drift` procedure survive untouched.
- **No new deploy-gate for `myblog_music`.** Its integration job stays advisory for the same reason its
  suite stays on Neon — a gate whose job is a data-quality measurement would block deploys on catalog
  drift, which is not a code regression.

## Current state

Every number below was measured on 2026-08-26 against live CI runs and the checked-out code, not
carried over from an earlier claim.

### The cost is one job, and inside it, one call

`myblog_backend` PR run [32934736644](https://github.com/hyuntohoon/myblog_backend/actions/runs/32934736644),
job `integration` (98073686536):

| step | duration |
| --- | --- |
| checkout + setup-python + git auth | 2s |
| `pip install -r requirements.txt -r requirements-test.txt` | 15s |
| **`pytest tests/integration -m integration -rs`** | **765s** |
| `Fail on DB-reason skips` | 0s |

The other three jobs are irrelevant to the wall clock: `check` 23s, `contract` 13s, `test` (684 unit
tests) 25s — all parallel, all done inside 25 seconds.

### It is latency, not test count

170 tests collected (169 run, 1 skipped). Per-file, from the timestamped CI log:

| file | tests | CI time | per test |
| --- | ---: | ---: | ---: |
| `test_bucket_service_db.py` | 86 | 390.1s | 4.5s |
| `test_rating_service_db.py` | 22 | 101.2s | 4.6s |
| `test_rerating_service_db.py` | 15 | 83.4s | 5.6s |
| `test_nightly_grow_db.py` | 8 | 57.3s | 7.2s |
| `test_library_service_db.py` | 18 | 52.5s | 2.9s |
| `test_planned_rating_service_db.py` | 8 | 28.0s | 3.5s |
| `test_post_genres_db.py` | 5 | 19.9s | 4.0s |
| `test_todays_pick_queue_db.py` | 4 | 16.8s | 4.2s |
| `test_tracked_artist_service_db.py` | 4 | 14.8s | 3.7s |

The per-test cost is uniform across files — 2.9s to 7.2s — so it is fixed overhead per test, not a few
pathological tests. `test_bucket_service_db.py` dominates only because it holds 86 of the 170.

The overhead is network round trips. The Neon test branch is in **ap-southeast-1**; GitHub's
`ubuntu-latest` runners are in the US. Measured from this laptop (Seoul), a single `SELECT 1` round trip
costs **75.9ms** (mean of 50, warm connection). The same suite run from this laptop finishes in
**321s — 1.87s per test**, against 4.5s in CI: a 2.4× ratio that tracks the distance, since neither the
tests nor the engine changed. A test that seeds a user, exercises a service call and asserts on the
result issues on the order of 20–30 statements, and pays the round trip on each one.

The engine fixture is already module-scoped and each test runs inside an outer transaction rolled back
on teardown, so connection setup and schema creation are *not* the cost. There is no cheap win left
inside the current topology.

### `deploy` does not depend on `integration` — in two repos

`myblog_backend/.github/workflows/deploy.yml`: `deploy: needs: [check, test, contract]`. `integration`
is absent. Observed on main run
[32935635449](https://github.com/hyuntohoon/myblog_backend/actions/runs/32935635449): merge at
05:50:34Z, `deploy` ran 05:51:14Z → 05:51:46Z **success**, while `integration` kept running until
06:04:35Z. The Lambda was live in production 72 seconds after the merge, 13 minutes before its DB tests
finished. Had they failed, nothing would have stopped or reverted the deploy.

`myblog_music` has the same shape: `deploy: needs: [test, contract]`, `integration` absent.

`myblog_worker` is the opposite: it has no separate integration job — its 12 DB-bound test files run
inside `test`, and `deploy: needs: test`. So the worker *does* gate on its DB tests, and pays for it:
latest main run, `test` 06:32:25Z → 06:37:04Z (**4m39s**) before a 34-second deploy.

Three repos, three different answers to the same question. This RFC makes the backend the deliberate one.

### The suite borrows catalog rows it does not seed

Six of nine files pull existing rows out of the branch rather than creating them:

```
6 ×  SELECT id FROM albums LIMIT n
1 ×  SELECT id FROM artists LIMIT n
```

They seed their own `users`, `review_buckets`, ratings and picks, but treat the catalog
(`albums` / `artists` / `tracks` / `genres`) as ambient — it is there because the Neon test branch is a
copy of production. **This, not the container, is what makes the migration non-trivial.**

Worse, absence is not loud. All ten guards `skip`:

```
test_bucket_service_db.py:83          need ≥3 albums in test DB
test_library_service_db.py:64         need ≥3 albums in test DB
test_nightly_grow_db.py:68            need ≥2 albums in test DB
test_planned_rating_service_db.py:74  need ≥2 albums in test DB
test_rating_service_db.py:124         need ≥2 albums in test DB
test_rerating_service_db.py:90        need ≥2 albums in test DB
test_todays_pick_queue_db.py:80       need >=2 tracks with albums in test DB
test_tracked_artist_service_db.py:55  need >=2 artists in test DB
test_tracked_artist_service_db.py:124 need an album credit for test artist
test_post_genres_db.py:90             need ≥2 genres in test DB
```

and the existing guard step only fails on skip reasons matching
`TEST_DB_URL|test branch|not deployed|schema`. **None of the ten match.** Pointing the current suite at
an empty Postgres would therefore print `No DB-reason skips.` and go green with most of the suite
silently gone — the exact false-green shape that guard was written to prevent
([[feedback-green-ci-can-be-false-green]]).

### Schema sources, and a live drift

Two committed DDL mirrors exist. `myblog_shared_db/tests/canonical_schema.sql` (1281 lines, 56
`CREATE TABLE`, plain SQL with no `psql` meta-commands, declares its own `pgcrypto` + `pg_trgm`
extensions) is loadable as-is. `docs/contracts/schema.sql` (1257 lines) is **two migrations behind right
now** — it lacks V53's `tracks.disc_no` and the whole V54 `pending_reratings` table. Their identity is
convention-only and unenforced ([[reference-schema-mirror-drift-unenforced]]), and it is currently
violated.

Corroborating evidence that the drift bites: `test_rerating_service_db.py:47-66` opens with an inline
`CREATE TABLE IF NOT EXISTS pending_reratings` commented "Guard against a lagging test branch" — a
workaround for a schema source that lags. A bootstrap from canonical DDL makes that guard dead code.

`myblog_shared_db/migrations/` holds 53 `V{N}__*.sql` files (highest V54). Each self-commits
([[reference-migration-file-self-commits]]).

### Secret location, and a stale instruction

`TEST_DB_URL` lives in SSM at `/myblog/test-db` (fetched successfully this session).
`myblog_worker/tests/conftest.py:13-16` still instructs developers to fetch it from **AWS Secrets
Manager** (`myblog/test-db`) — that secret does not exist (`ResourceNotFoundException`), and CLAUDE.md
bans Secrets Manager outright. The comment is dead instructions.

## Target state

- `myblog_backend`'s `integration` job runs a `postgres:16` service container. Schema is loaded from
  `myblog_shared_db/tests/canonical_schema.sql`; catalog rows come from a committed fixture. No
  `TEST_DB_URL` secret, no cross-ocean round trip. Target: **under 90 seconds** for the same 170 tests
  (170/170 collected, ≥169 passing — the same count as today, with skips forbidden).
- Loading the canonical DDL every CI run turns the mirror-identity convention into something CI
  executes, so a file that no longer loads becomes a red job instead of a silent divergence.
- A separate, small `integration-neon` job keeps the handful of assertions that are about Neon rather
  than about Postgres — pooler semantics, the `default_transaction_read_only` leak
  ([[reference-neon-pooler-readonly-leak]]), connection lifetime. It runs on `main` and on demand, not
  on every PR.
- `deploy: needs: [check, test, contract, integration]`. A commit whose DB tests fail cannot reach
  production.
- The skip guard fails on **any** skip in the integration suite, not on a grep of known reasons.

## Steps

Steps 1–2 are the work; 3–4 are small and depend on it. Step 5 is cross-repo and deliberately last.

### Step 1 — catalog fixture, provable on both engines

Add a seed fixture (`tests/integration/fixtures/catalog.sql` or a conftest fixture — OQ1) that creates
the minimum catalog the ten guards ask for: ≥3 `albums` with ≥2 `artists`, ≥2 `tracks` joined to an
album, ≥2 `genres`, and at least one artist↔album credit. FK-integral, id-stable, seeded once per
session inside a transaction the suite rolls back.

Rewire the six borrowing fixtures to read from the seeded rows instead of `LIMIT n` over ambient data.
Do not touch assertions.

The proof is parity, not green: the suite must pass **the same 170/170 against the Neon branch as
against a local Postgres**. Run both in the same pass ([[feedback-measure-with-a-control]]) — a fresh
harness reporting a low number is as likely to be a broken harness as a finding.

**Verification**:
```
# control: unchanged target, must still be 169 passed / 1 skipped
TEST_DB_URL=<neon> pytest tests/integration -m integration -rs

# treatment: same suite, local engine
docker run -d --name pgtest -e POSTGRES_PASSWORD=x -p 55432:5432 postgres:16
psql postgresql://postgres:x@localhost:55432/postgres -v ON_ERROR_STOP=1 \
  -f myblog_shared_db/tests/canonical_schema.sql
TEST_DB_URL=postgresql+psycopg://postgres:x@localhost:55432/postgres \
  pytest tests/integration -m integration -rs
```
Both runs must report the same passed count and the same skip list. Record the local wall clock — it is
the number Step 2's CI target is checked against.

**Rollback**: revert; nothing else reads the fixture.

---

### Step 2 — CI runs the suite against a service container

`integration` gains a `services: postgres:16` block, a schema-load step, and drops `TEST_DB_URL` and its
two secret-shape guards. Keep the Neon run alongside as a second matrix leg for one merge cycle so the
parity from Step 1 is demonstrated in CI, not just locally.

**Verification**:
```
gh run view <run-id> --repo hyuntohoon/myblog_backend --json jobs \
  -q '.jobs[] | select(.name|startswith("integration")) | "\(.name) \(.conclusion) \(.startedAt) \(.completedAt)"'
```
Both legs green, same test count. Local leg under 90s; if it lands materially above that, stop and
report rather than accepting it — the whole premise of this RFC is that the 765s was latency.

**Rollback**: revert the workflow; the Neon leg is still present and passing.

---

### Step 3 — the skip guard stops being a grep

Replace the reason-matching `grep` with `pytest ... -p no:randomly --strict-markers` plus a hard check
that the run reports **zero** skips in `tests/integration`. A skip in this suite now always means
something is missing, because nothing in it is environment-conditional any more.

**Verification**: land Step 3 together with a deliberate temporary `pytest.skip` in one test and confirm
the job goes red; remove it before merge. A guard that has never been seen to fire is not a verified
guard ([[feedback-verify-by-running-not-reading]]).

---

### Step 4 — split off `integration-neon`, then gate `deploy`

Move the Neon-specific assertions into `tests/integration_neon/` with its own job (`main` +
`workflow_dispatch`, `TEST_DB_URL` from SSM, not a PR gate). Then add `integration` to
`deploy.needs`.

**Verification**:
```
# the gate actually gates: push a branch whose integration suite fails, dispatch, confirm deploy is skipped
gh run view <run-id> --repo hyuntohoon/myblog_backend --json jobs -q '.jobs[] | "\(.name) \(.conclusion)"'
```
`integration failure` + `deploy skipped`. Same reasoning as Step 3 — assert the gate by watching it stop
something.

**Rollback**: remove `integration` from `deploy.needs`. Immediate, no state.

---

### Step 5 — cross-repo (`myblog_worker`), last

`myblog_worker`'s 12 DB-bound test files already gate deploy and already cost 4m39s. Apply the same
container + fixture pattern, and fix the dead Secrets Manager instruction in
`tests/conftest.py:13-16` to point at SSM `/myblog/test-db` in the same change
([[feedback-cross-repo-twin-drift-sweep]]).

Deliberately last: the backend proves the pattern first, and the worker is the one repo where getting
this wrong stops deploys rather than merely reporting late.

**Verification**: `pytest` green in CI with the same test count as the last Neon-targeted run; job under
90s; `deploy` still `needs: test`.

---

## Open questions

1. **Fixture form — SQL file or conftest factory?** (blocks Step 1) A `.sql` file is one artifact and
   reviewable at a glance; a conftest factory composes with the existing session/transaction fixtures and
   cannot drift from the ORM. Leaning `.sql` for the catalog (it mirrors DDL, is read-only to the tests,
   and never needs to change when a service changes) with the per-test rows staying in conftest where
   they already are.
2. **Do any assertions depend on properties of real catalog rows** — genre coverage, release dates,
   popularity ordering — rather than on ids alone? (blocks Step 1) Unknown until the fixture runs. If
   one does, the honest outcome is to seed a row with that property, not to relax the assertion. Any
   test that cannot be satisfied this way is a candidate for `integration_neon` in Step 4 instead.
3. **Canonical DDL or migration replay as the schema source?** (blocks Step 2) Leaning
   `canonical_schema.sql` — one declarative file, already committed, and executing it makes the
   unenforced mirror convention enforced. Replaying all 53 `V{N}__` files would additionally prove
   migrations apply from scratch (nothing checks this today), but it is 53 files of unknown
   from-scratch replayability and would put an unrelated failure mode in this job's path. Suggest
   canonical DDL here and migration-replay as its own additive job later.
4. **Does `docs/contracts/schema.sql` get fixed in this RFC or separately?** (blocks nothing) It is two
   migrations behind today (V53, V54). It is not on this RFC's path — the bootstrap reads the
   `myblog_shared_db` copy — but it is a live drift found while writing this, and leaving it unfixed
   means the next person reads a stale contract.
5. **Is a 170-test suite that never touches production-shaped data still worth 90 seconds of every
   merge?** (blocks Step 4) Stated plainly so it is answered rather than assumed: these tests exercise
   service-layer SQL against real Postgres semantics — transactions, constraints, `ON CONFLICT`,
   cascade behavior — none of which a fixture weakens. What a synthetic catalog does weaken is anything
   depending on data *shape at scale*. If OQ2 finds such tests, they belong in `integration_neon`.

## Decisions log

| Date | Decision | Step |
|------|----------|------|
| 2026-08-26 | RFC opened after measuring the 13m CI job; owner asked whether a local DB should replace the Neon test branch | — |
