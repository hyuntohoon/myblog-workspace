# OPS-integration-db-locality: run the integration suite against a local Postgres, then let it gate deploy

- **Status**: **done 2026-09-03** (promotion owner-approved in-session — CLAUDE.md rule #7). Originally
  accepted 2026-08-26 (explicit owner approval in-session —
  answering the recommendations verbatim: `.sql` catalog fixture, canonical DDL as the schema source,
  and any assertion that cannot survive a seeded catalog moves to `integration_neon` rather than being
  relaxed; Step 4 later mapped that set to zero and the owner clarified local-only). **All five steps
  shipped** (backend #163, #164, #165, #167; worker #99).
- **Owner**: 오너
- **Created**: 2026-08-26
- **Plan row**: removed after Step 5 production verification on 2026-08-28

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
- ~~**No removal of Neon from CI.**~~ **Superseded 2026-08-27 by the owner:** the completed mapping
  found no backend assertion about Neon itself, so the 170-test backend suite becomes local-only.
  A future production-data or Neon-platform contract needs its own specified assertions and thresholds.
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
  `TEST_DB_URL` secret, no cross-ocean round trip. Target: **under 60 seconds** for the same 170 tests,
  all passing, zero skips. The target is no longer a guess — Step 1 measured the identical suite at
  **12.04s** against a local `postgres:16`, so anything near a minute in CI is container startup and
  install, not query time.
- Loading the canonical DDL every CI run turns the mirror-identity convention into something CI
  executes, so a file that no longer loads becomes a red job instead of a silent divergence.
- No backend Neon job remains: the mapping found no Neon-only assertion to preserve. Historical
  pooler/read-only failures belong to workspace scripts, not this backend suite; a future targeted
  contract must specify its own behavior and thresholds before adding a remote-DB job.
- `deploy: needs: [check, test, contract, integration]`. A commit whose DB tests fail cannot reach
  production.
- The skip guard fails on **any** skip in the integration suite, not on a grep of known reasons.

## Steps

Steps 1–2 are the work; 3–4 are small and depend on it. Step 5 is cross-repo and deliberately last.

### Step 1 — catalog fixture, provable on both engines — **SHIPPED 2026-08-26** (backend #163)

**Outcome — parity met, and it moved two open questions.**

| target | result | wall clock |
| --- | --- | --- |
| local `postgres:16` | **170 passed, 0 skipped** | **12.04s** |
| Neon test branch | **170 passed, 0 skipped** | 367.19s |
| full suite (local PG) | 854 passed, 0 skipped | 11.59s |
| unit-only | 684 passed (unchanged) | 3.21s |

Was 169 passed + 1 skipped; the count rose because the bucket-preview test's
album-credit `skip` became a passing assertion. Neon pollution asserted, not assumed: 0 leftover
`fixture-%` rows in `albums`/`artists`/`tracks`/`genres` after the run.

**Interim regression, stated because this step alone makes one number worse:** seeding costs round
trips, so while CI still points at Neon the job goes from ~13min to ~14min. Step 2 reverses it
entirely — the same work is 12 seconds against a local engine.

Implementation note worth keeping: the first version of `catalog.py` split the `.sql` on `;` and asked
the SQL file to keep semicolons out of its comments. The SQL file broke that rule in its own header on
the first run and all 85 seeded tests errored. The splitter is now comment-aware. A rule a sibling file
has to remember is not a contract, it is a trap.

---

<details>
<summary>Original Step 1 plan (kept for the record)</summary>

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

</details>

---

### Step 2 — CI runs the suite against a service container — **SHIPPED 2026-08-26** (backend #164)

**Outcome — parity held and the local job met the target.** Final PR run
[32976208413](https://github.com/hyuntohoon/myblog_backend/actions/runs/32976208413) ran the same
170-test suite on both matrix legs with **170 passed / 0 skipped**: local `postgres:16` completed the
whole job in **49s** (pytest **4.19s**) while the Neon control took **14m31s** (pytest **13m44s**).
The main run repeated the local leg in **46s**, then deployed in **27s** with the post-deploy database
health smoke green. This is the intended intermediate topology: deploy gating remains Step 4.

One false-green-adjacent workflow trap was found by the merge policy rather than the test suite. The
first matrix name changed the required check context from `integration` to `integration (local)`; every
job was green, but main correctly refused the merge because its ruleset still required the now-missing
exact context. The final matrix preserves local as `integration` and names only the control
`integration (neon)`. A CI refactor must preserve required-check identity, not only job behavior.

`integration` gains a `services: postgres:16` block, a schema-load step, and drops `TEST_DB_URL` and its
two secret-shape guards. Keep the Neon run alongside as a second matrix leg for one merge cycle so the
parity from Step 1 is demonstrated in CI, not just locally.

**Verification**:
```
gh run view <run-id> --repo hyuntohoon/myblog_backend --json jobs \
  -q '.jobs[] | select(.name|startswith("integration")) | "\(.name) \(.conclusion) \(.startedAt) \(.completedAt)"'
```
Both legs green, same test count. Local leg under 60s against Step 1's 12.04s baseline; if it lands
materially above that, stop and report rather than accepting it — the whole premise of this RFC is that
the 765s was latency, and Step 1 has already demonstrated it on this machine.

**Rollback**: revert the workflow; the Neon leg is still present and passing.

---

### Step 3 — the skip guard stops being a grep — **SHIPPED 2026-08-26** (backend #165)

**Outcome — the invariant fired on command, then passed cleanly on both engines.** The workflow now
runs pytest with `-p no:randomly --strict-markers`, writes a JUnit XML report, and fails whenever that
report contains any skipped testcase. It no longer depends on skip reason text or terminal-summary
formatting. The local matrix leg retained the exact required context `integration`; the Neon control
remained in place for Step 4.

The deliberate-red run
[32980509452](https://github.com/hyuntohoon/myblog_backend/actions/runs/32980509452) added one temporary
`pytest.skip`: pytest reported **169 passed / 1 skipped in 4.26s**, then the required `integration` job
failed in `Enforce zero integration skips` with `1 integration test(s) skipped; expected zero`. The
temporary skip was removed before merge; the existing PR concurrency policy superseded that run
without waiting for its obsolete Neon leg.

The clean PR run
[32981057436](https://github.com/hyuntohoon/myblog_backend/actions/runs/32981057436) passed with
**170/170 and zero skips on both legs**: local `integration` completed in **53s** (pytest **3.68s**),
and `integration (neon)` completed in **17m3s** (pytest **980.57s**). Squash merge `4ebc5be` deployed
in main run [32982946555](https://github.com/hyuntohoon/myblog_backend/actions/runs/32982946555);
the deploy job finished in **36s** and the production database health smoke reported
`Backend health OK.`. The smoke and parity results are quoted on backend #165.

Replace the reason-matching `grep` with `pytest ... -p no:randomly --strict-markers` plus a hard check
that the run reports **zero** skips in `tests/integration`. A skip in this suite now always means
something is missing, because nothing in it is environment-conditional any more.

**Verification**: land Step 3 together with a deliberate temporary `pytest.skip` in one test and confirm
the job goes red; remove it before merge. A guard that has never been seen to fire is not a verified
guard ([[feedback-verify-by-running-not-reading]]).

---

### Step 4 — remove the Neon control, then gate `deploy` — **SHIPPED 2026-08-28** (backend #167)

**Outcome — the fast local suite now gates production deploy.** Backend #167 removed the temporary
Neon matrix leg, preserved the exact required context `integration`, and added it to `deploy.needs`.
The deliberate-red dispatch
[33024138313](https://github.com/hyuntohoon/myblog_backend/actions/runs/33024138313) proved the edge:
`check`/`test`/`contract` passed, `integration` reported **170 passed + 1 intentional failure**, and
`deploy` was **skipped**. The temporary failure was removed before the clean PR run
[33024497728](https://github.com/hyuntohoon/myblog_backend/actions/runs/33024497728), where all four
required checks passed and local `integration` completed in **55s** with **170/170, zero skips**.

One live-governance mismatch surfaced after the concurrent security ruleset rollout: ruleset
`21564102` required the obsolete `integration (neon)` context even though its RFC record listed only
the four intended checks. The owner authorized completing the local-only direction; the stale context
was removed while preserving `check`, `test`, `contract`, and `integration`.

Squash `aefa1a8` deployed in main run
[33159253480](https://github.com/hyuntohoon/myblog_backend/actions/runs/33159253480). The required local
job finished first in **46s** (**170/170, zero skips; pytest 3.19s**), then deploy ran in **27s** and
the production `/api/db/ping` smoke reported **`Backend health OK.`**. The result is quoted on #167.

Remove the temporary Neon matrix leg, keep the exact required local `integration` context, then add
`integration` to `deploy.needs`.

**Implementation mapping — 2026-08-27:** there are currently no Neon-only assertions to move. Step 1
proved that all 170 tests exercise engine-independent Postgres behavior against both targets, and the
pooler/read-only examples above are historical workspace-script failures rather than backend tests.
Do not invent a new contract or create an empty false-green suite in this step. The owner clarified
that the goal is to stop running this backend suite on Neon, not to retain its 17-minute duplicate as
an advisory job. A future targeted data-shape or Neon-platform contract can be added when its
assertions and thresholds are specified.

**Verification**:
```
# the gate actually gates: push a branch whose integration suite fails, dispatch, confirm deploy is skipped
gh run view <run-id> --repo hyuntohoon/myblog_backend --json jobs -q '.jobs[] | "\(.name) \(.conclusion)"'
```
`integration failure` + `deploy skipped`. Same reasoning as Step 3 — assert the gate by watching it stop
something.

**Rollback**: remove `integration` from `deploy.needs`. Immediate, no state.

---

### Step 5 — cross-repo (`myblog_worker`), last — **SHIPPED 2026-08-28** (worker #99)

**Outcome — the existing worker deploy gate now runs entirely on disposable Postgres 16.** The
current-main inventory corrected the RFC's stale "12 DB-bound files" shorthand: the broad 12-file set
contains eight remote-Postgres files with **41 tests**, one self-contained SQLite file with four tests,
and three fake/unit-only files with 74 tests. Seven Postgres files were already self-seeded. The only
ambient inputs were one album in `test_library_sync_db.py` plus the `hip-hop` and `rock` vocabulary
rows used by `test_sync_service.py`; the committed SQL fixture supplies exactly those rows.

Latest pre-change main run
[33160764527](https://github.com/hyuntohoon/myblog_worker/actions/runs/33160764527) collected **539**
tests and reported **536 passed / 3 intentional MusicBrainz live skips in 212.06s**; the required
`test` job took **3m54s**. PR run
[33164957302](https://github.com/hyuntohoon/myblog_worker/actions/runs/33164957302) preserved the same
539 / 536+3 result, completed pytest in **3.98s**, reported `db_bound_skips=0`, and finished the whole
job in **52s**. No assertion, test body, skip condition, dependency, or database semantic was relaxed.

Squash `324cd22` repeated the proof on main run
[33165063868](https://github.com/hyuntohoon/myblog_worker/actions/runs/33165063868): required `test`
finished in **1m9s** (pytest **3.95s**, 539 / 536+3, zero DB-bound skips), then the still-dependent
`deploy` job ran in **33s** and the production Lambda health invoke returned
`{"batchItemFailures": []}` plus `Worker health OK (empty-event invoke, no FunctionError).` The exact
ruleset context remains `test`, and `deploy.needs: test` is unchanged. The post-merge evidence is quoted
on worker #99.

The same change replaced the dead Secrets Manager test instructions in `tests/conftest.py` and the
worker README with SSM SecureString `/myblog/test-db` guidance. CI no longer reads a remote
`TEST_DB_URL` secret; it loads canonical DDL from shared-db `90a6fca` and the committed deterministic
fixture on every run.

---

## Open questions

1. ~~**Fixture form — SQL file or conftest factory?**~~ **RESOLVED 2026-08-26 (owner): `.sql`.**
   Shipped as `tests/integration/fixtures/catalog.sql` + `catalog.py`, with the ids owned by the SQL
   and read back by the helper so the two cannot drift. Original reasoning: A `.sql` file is one artifact and
   reviewable at a glance; a conftest factory composes with the existing session/transaction fixtures and
   cannot drift from the ORM. Leaning `.sql` for the catalog (it mirrors DDL, is read-only to the tests,
   and never needs to change when a service changes) with the per-test rows staying in conftest where
   they already are.
2. ~~**Do any assertions depend on properties of real catalog rows?**~~ **RESOLVED 2026-08-26 by
   running it: no.** All 170 pass on a synthetic catalog with nothing relaxed, so no test moved to
   `integration_neon` on this ground. One got *stronger* by accident: `test_empty_album_is_zero`
   previously relied on whichever ambient album it happened to pick having no reviews. Original
   question: do any depend on properties of real catalog rows — genre coverage, release dates,
   popularity ordering — rather than on ids alone? (blocks Step 1) Unknown until the fixture runs. If
   one does, the honest outcome is to seed a row with that property, not to relax the assertion. Any
   test that cannot be satisfied this way is a candidate for `integration_neon` in Step 4 instead.
3. ~~**Canonical DDL or migration replay as the schema source?**~~ **RESOLVED 2026-08-26 (owner):
   canonical DDL**, and verified — `myblog_shared_db/tests/canonical_schema.sql` loads into stock
   `postgres:16` unmodified, 56 tables, zero errors, extensions self-declared. Migration replay stays a
   separate additive job. Original reasoning: Leaning
   `canonical_schema.sql` — one declarative file, already committed, and executing it makes the
   unenforced mirror convention enforced. Replaying all 53 `V{N}__` files would additionally prove
   migrations apply from scratch (nothing checks this today), but it is 53 files of unknown
   from-scratch replayability and would put an unrelated failure mode in this job's path. Suggest
   canonical DDL here and migration-replay as its own additive job later.
4. **Does `docs/contracts/schema.sql` get fixed in this RFC or separately?** (blocks nothing) It is two
   migrations behind today (V53, V54). It is not on this RFC's path — the bootstrap reads the
   `myblog_shared_db` copy — but it is a live drift found while writing this, and leaving it unfixed
   means the next person reads a stale contract.
5. ~~**Is a 170-test suite that never touches production-shaped data still worth 90 seconds of every
   merge?**~~ **RESOLVED 2026-08-27 (owner): yes; keep it required on every merge.** The measured
   53-second job adds roughly 17 seconds beyond the other required checks and protects real Postgres
   transaction, constraint, `ON CONFLICT`, and cascade behavior. Production-scale data-shape behavior
   is not claimed by this suite and needs a separately specified future contract.

## Decisions log

| Date | Decision | Step |
|------|----------|------|
| 2026-08-26 | RFC opened after measuring the 13m CI job; owner asked whether a local DB should replace the Neon test branch | — |
| 2026-08-26 | Owner accepted the RFC and all three recommendations verbatim (`.sql` fixture · canonical DDL · move, never relax, an assertion that cannot survive a seeded catalog) | — |
| 2026-08-26 | Step 1 shipped (backend #163). Parity met on both engines at 170/170, 0 skips: local 12.04s vs Neon 367.19s | 1 |
| 2026-08-26 | OQ1/OQ2/OQ3 closed by the Step 1 run; Step 2's CI target tightened from a guessed 90s to 60s against the measured 12.04s baseline | 1, 2 |
| 2026-08-26 | Step 2 shipped (backend #164). Final PR parity: 170/170, 0 skips on both legs; local job 49s vs Neon 14m31s. Main local job 46s; deploy 27s + health smoke green. Local retained the exact required check context `integration` after the first matrix name made an otherwise-green PR unmergeable | 2 |
| 2026-08-26 | Step 3 shipped (backend #165). Intentional red proof: required `integration` failed after 169 passed / 1 skipped. Clean PR parity: 170/170, 0 skips on both legs; local job 53s vs Neon 17m3s. Squash `4ebc5be` deployed in 36s with production database health smoke green | 3 |
| 2026-08-27 | Owner resolved OQ5: keep the 170-test local Postgres suite required on every merge; its measured 53-second job adds roughly 17 seconds beyond the other gates | 4 |
| 2026-08-27 | Mapping found zero Neon-only backend assertions; owner clarified that the suite should stop running on Neon. Remove the temporary Neon matrix leg rather than create an empty or duplicate advisory job | 4 |
| 2026-08-28 | Step 4 shipped (backend #167). Negative proof: 170 passed + 1 intentional failure made `integration` fail and `deploy` skip. Clean PR: required local `integration` 170/170, zero skips, 55s. Removed stale `integration (neon)` from ruleset 21564102; squash `aefa1a8` main run gated deploy on local integration, then deployed in 27s with production health smoke green | 4 |
