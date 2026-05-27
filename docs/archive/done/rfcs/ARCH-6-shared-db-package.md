# ARCH-6: Shared DB Models Package

- **Status**: done
- **Owner**: TBD
- **Created**: 2026-05-26
- **Plan row**: `plan.md` → ARCH-6

---

## Goal

A single Python package, `myblog_shared_db`, owns the canonical SQLAlchemy models for the shared Neon database. `myblog_backend`, `myblog_music`, and `myblog_worker` all import from it. Schema drift across services is no longer possible without a coordinated change to the shared package.

## Non-goals

- Replacing raw SQL inside `myblog_worker` with ORM. Worker keeps Core + raw SQL for bulk upsert performance; it just gets its **table definitions** from the shared package.
- Changing the canonical DDL workflow. `docs/contracts/schema.sql` remains the source of truth for DDL; the shared package's models must match it. (Drift detection — Step 5 — enforces this.)
- Splitting the database. Single Neon instance; multiple ORMs over it is the problem, not multi-tenancy.
- Introducing a service mesh, internal HTTP API for DB access, or any other distributed-systems refactor.
- 100% raw-SQL drift detection inside `myblog_worker`. Worker's column names appear inside SQL strings (e.g. `"INSERT INTO albums (spotify_id, name, ...)"`). Shared package guarantees column **definitions** are consistent; SQL strings referencing them are not statically validated. Accepted as 80% solution.

## Current state

Three independent model/table definitions over the same Neon tables:

| Service | Location | Style |
|---------|----------|-------|
| `myblog_backend` | `app/db/models.py` (SQLAlchemy ORM declarative) | ORM, used in handlers |
| `myblog_music` | `app/domain/models.py` (SQLAlchemy ORM declarative) | ORM, used in repositories |
| `myblog_worker` | `worker/infra/tables.py` (SQLAlchemy Core `Table` objects) | Core, used in raw SQL builders |

Canonical DDL: `docs/contracts/schema.sql` (ADR 0003).

Known drift incidents that motivate this RFC:
- `tracks.spotify_id` UNIQUE missing from one model (BUG-3)
- `albums.ext_refs` not updated in worker upsert despite being in schema (ARCH-5)
- `artists.aliases` defined in worker's table object but unknown to backend until ARCH-1

## Target state

```
myblog_shared_db/                    ← new private GitHub repo, installed via git URL
├── pyproject.toml                   ← installable as `myblog-shared-db`
├── src/myblog_shared_db/
│   ├── __init__.py                  ← re-exports
│   ├── models.py                    ← SQLAlchemy ORM declarative (one source)
│   ├── tables.py                    ← Core Table objects, derived from models
│   ├── enums.py                     ← shared enum types
│   └── _generated_schema.sql        ← generated from models; compared in CI
├── tests/
│   └── test_schema_parity.py        ← models match docs/contracts/schema.sql
└── README.md
```

Each consumer:
- `myblog_backend` — `from myblog_shared_db.models import Post, Category, Album, ...`
- `myblog_music` — same
- `myblog_worker` — `from myblog_shared_db.tables import albums_t, tracks_t, ...`

## Distribution (decided)

**Method**: private GitHub repo, installed via git URL pin.

```toml
# in each consumer's pyproject.toml
myblog-shared-db = { git = "https://github.com/<owner>/myblog_shared_db.git", tag = "v0.1.0" }
```

Rationale (1-person ops): zero infra cost (no CodeArtifact registry to maintain), explicit tag pinning per service so consumers upgrade independently, fits existing repo-per-service layout.

Rejected alternatives:
- **CodeArtifact** — adds an AWS service to maintain; over-engineered for current scale.
- **Git submodule** — submodule update friction; deploys can drift from latest commit unnoticed.
- **Monorepo** — long-term attractive but a separate, larger decision. Consolidating 5 service repos warrants its own RFC.

Trade-off accepted: consumer CIs need a GitHub PAT to install from the private repo (handled in Step 2.5).

## Steps

Each step is **independently mergeable** unless noted. Do not start Step N+1 until Step N is on `main` in every affected repo. The workspace CLAUDE.md hard rule "one RFC step per session" applies.

---

### Step 1 — Create the package skeleton

- New private GitHub repo `myblog_shared_db`.
- `pyproject.toml`, package metadata, `py.typed` marker.
- Empty `models.py` with a single `DeclarativeBase`.
- README with install instructions and the consumer-side pyproject snippet.
- Tag `v0.0.1`.

**Verification**:
```
pip install "git+https://github.com/<owner>/myblog_shared_db.git@v0.0.1"
python -c "from myblog_shared_db.models import Base; print(Base)"
```

**Rollback**: archive repo (do not delete — preserves any setup work).

---

### Step 2 — Port models into the package

Prerequisite: **model diff review gate**. Before writing code, run a 3-way diff across the three current model files and produce a short table recording which fields exist where, including types, nullability, indexes, and defaults. Paste the result into the Decisions log of this RFC. This gate ensures the "richest source" claim is verified, not assumed.

After the gate:

- Pick the most-complete model set as the base. Tentative starting point is `myblog_music`'s `app/domain/models.py`, but the diff may reveal that backend has fields music lacks, or that both have drift requiring a merge.
- Move (do not copy) into `myblog_shared_db/models.py`.
- Generate `tables.py` Core objects from the ORM models:
  ```python
  # tables.py
  from .models import Base
  albums_t = Base.metadata.tables["albums"]
  tracks_t = Base.metadata.tables["tracks"]
  # ...
  ```
- Generate `_generated_schema.sql` from `Base.metadata` via `sqlalchemy.schema.CreateTable`.
- Tag `v0.1.0`.

**Verification**:
- Diff table is in the Decisions log.
- `python -c "from myblog_shared_db.models import Album, Track, Artist, Post, Category"` succeeds.
- All current columns from all 3 services are accounted for in `models.py` (cross-reference the diff table).

**Rollback**: discard branch; keep `v0.0.1` as the live tag.

---

### Step 2.5 — Wire up CI access to the private package

Each consumer repo (`myblog_backend`, `myblog_music`, `myblog_worker`) needs to install from the private `myblog_shared_db` repo during CI and during Lambda packaging.

- Create a fine-scoped GitHub PAT (or deploy key per repo) with **read access to `myblog_shared_db` only**.
- Add to each consumer repo's GitHub Actions secrets as `SHARED_DB_PAT`.
- Update each consumer's `deploy.yml` to inject the PAT into pip's git auth before install:
  ```yaml
  - name: Configure git auth for private package
    run: git config --global url."https://${{ secrets.SHARED_DB_PAT }}@github.com/".insteadOf "https://github.com/"
  ```
- Update each consumer's `pyproject.toml` with the dependency line (pinned to `v0.1.0`), but **do not import from it yet** — that's Step 3.

**Verification**:
- Push a no-op commit to each consumer repo; CI installs `myblog-shared-db` successfully (visible in pip install output).
- `pip show myblog-shared-db` in CI logs reports `v0.1.0`.

**Rollback**: revert the dependency line in each pyproject; CI returns to its previous behavior.

> Steps 2 and 2.5 can run in parallel after Step 2's tag exists — 2.5 only depends on the package being installable, not on any specific model content.

---

### Step 3 — Migrate `myblog_music` (lowest-risk consumer)

`myblog_music`'s model file is the candidate source for the shared package (subject to Step 2's diff review). If Step 2 confirmed it as the starting point, this migration is the smallest diff.

- Replace `from app.domain.models import ...` with `from myblog_shared_db.models import ...`.
- Delete `app/domain/models.py`.
- Run full test suite, including `tests/test_candidates_localstack.py`.

**Verification**:
```
cd myblog_music && pytest
# All tests pass; no behavioral change.
```

Deploy to Lambda. Smoke test `/api/music/search/unified` and `/api/music/albums/:id`.

**Rollback**: revert PR; previous code still works because shared package install is purely additive until imports change.

---

### Step 4 — Migrate `myblog_backend` and `myblog_worker`

Two PRs, one per repo. Either order works; backend first is slightly safer (worker's path is harder to verify without invoking SQS).

For `myblog_worker`:
- Replace `from worker.infra.tables import albums_t, ...` with `from myblog_shared_db.tables import albums_t, ...`.
- Delete `worker/infra/tables.py`.

**Verification**:
- `myblog_backend`: full pytest, then deploy + smoke `/posts` CRUD.
- `myblog_worker`: full pytest, then send a test SQS message and verify upsert hits Neon with all expected columns (spot-check `ext_refs`, `aliases`).

**Rollback**: revert PR per repo.

---

### Step 5 — Add schema parity CI check

In `myblog_shared_db`:
```python
# tests/test_schema_parity.py
def test_generated_schema_matches_canonical():
    canonical = read_canonical_schema()  # see open question 1 for source resolution
    generated = read("src/myblog_shared_db/_generated_schema.sql")
    assert_semantic_equal(canonical, generated)
```

Add to `myblog_shared_db` CI. On any PR that changes `models.py`, `_generated_schema.sql` is regenerated and compared against the canonical `docs/contracts/schema.sql`.

**Verification**: deliberately introduce a drift (add a column to `models.py` only) — CI fails. Revert the drift; CI passes.

**Rollback**: not applicable; this is a pure check.

---

### Step 6 — Cleanup

- Each consumer repo's CLAUDE.md mentions `myblog_shared_db` in the "DB layer" section.
- Workspace `architecture.md` "Schema Contract" section updated to point at the package, not just the .sql file.
- ADR `0005-shared-db-package.md` written: records the decision, the rejected alternatives (CodeArtifact, submodule, monorepo), and the 80% drift detection trade-off.
- This RFC marked `done` and moved to `docs/done/rfcs/ARCH-6-shared-db-package.md`.

**Verification**: `grep -r "from app.domain.models" myblog_*/` returns nothing in backend, music. `grep -r "from worker.infra.tables" myblog_worker/` returns nothing.

---

## Migration order summary

```
Step 1 ──► Step 2 (with diff gate) ──┬─► Step 3 (music) ──► Step 4 (backend, worker) ──► Step 5 (CI guard) ──► Step 6 (docs/ADR)
                                     │                                │
                                     └─► Step 2.5 (CI PAT)             └─► both PRs can be parallel after Step 3 lands
                                         (parallel-safe with Step 3)
```

## Rollback (overall)

If the package approach fails partway:
- Pre-Step 3: nothing deployed depends on the package. Archive the repo.
- Post-Step 3: revert the import-swap PRs in reverse order (Step 4 first, then Step 3). Each consumer's old model file lives in git history; restore via `git revert`.
- The shared package repo can remain as a dead artifact; no shared state to clean up.

## Open questions

1. **How does `myblog_shared_db` CI access `myblog-workspace/docs/contracts/schema.sql`?** Three options: (a) duplicate the file into `myblog_shared_db` and have a separate CI in the workspace verify they match, (b) make `docs/contracts/schema.sql` a published artifact, (c) submodule the workspace into the shared repo. Decide before Step 5. (Tentative: a — duplication + workspace-side verification is the simplest.)
2. **Python version & SQLAlchemy version pinning.** Backend, music, worker may currently pin different versions. Shared package must declare a compatible range, and consumers must align before Step 3.
3. **Alembic / migrations ownership.** Currently each service has (or doesn't have) its own migrations dir. After this RFC, who owns migrations? Tentative answer: a new `migrations/` dir inside `myblog_shared_db`. But this expands scope — possibly a follow-up RFC (ARCH-6b).

## Decisions log

_(to be filled as steps execute)_

| Date | Decision | Step |
|------|----------|------|
| 2026-05-26 | Distribution method: private GitHub repo + git URL (option A). Rejected: CodeArtifact, submodule, monorepo. | Pre-Step 1 |
| 2026-05-26 | Step 1 complete. Repo `hyuntohoon/myblog_shared_db` created (private), tagged `v0.0.1`. Verified: `from myblog_shared_db.models import Base` → `<class 'myblog_shared_db.models.Base'>`. `requires-python = ">=3.12"` confirmed against Lambda runtime. | Step 1 |
| 2026-05-26 | Step 2 complete. Canonical models committed on `feat/step2-models`, PR merged. Tagged `v0.1.0`. Drift gate passed: `post_albums_table`, `post_recommended_tracks_table` aligned to canonical schema. `artist.followers` BigInteger, `DateTime(timezone=True)`. `_generated_schema.sql` committed. | Step 2 |
| 2026-05-26 | Step 2.5 complete. GitHub Actions CI in myblog_shared_db wired (`SHARED_DB_PAT` secret, `gh auth token`). Schema parity test passes (stack-based paren counter to handle `gen_random_uuid()` in canonical SQL). | Step 2.5 |
| 2026-05-26 | Step 3 complete. `myblog_music`: `app/domain/models.py` deleted; 3 repository files updated to import from `myblog_shared_db.models`. `requirements.txt` + CI git-auth step added. PR merged. | Step 3 |
| 2026-05-26 | Step 4 complete. `myblog_backend`: `app/models/` directory (6 files) deleted; post_service, post_repo, category_repo updated to import from `myblog_shared_db.models` (association tables aliased to preserve call-site names). `myblog_worker`: `worker/infra/tables.py` deleted (was orphaned — sync_service.py uses raw `text()` directly). Both `requirements.txt` + CI git-auth steps added. PRs merged. | Step 4 |
| 2026-05-26 | Step 5 complete. `tests/test_schema_parity.py` in `myblog_shared_db`: two tests — generated schema freshness check + modeled columns present in canonical. CI passes. | Step 5 |
| 2026-05-26 | Step 6 complete. `myblog_backend` and `myblog_worker` CLAUDE.md updated. Workspace `docs/architecture.md` Schema Contract section updated. ADR `0005-shared-db-package.md` written. RFC moved to `docs/done/rfcs/`. ARCH-6 row cut from `plan.md`. | Step 6 |
