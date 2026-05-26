# ADR 0005 — Shared DB Models Package

- **Status**: accepted
- **Date**: 2026-05-26
- **RFC**: `docs/done/rfcs/ARCH-6-shared-db-package.md`

## Context

Three services (`myblog_backend`, `myblog_music`, `myblog_worker`) maintained independent SQLAlchemy model definitions over the same Neon database tables. Known drift incidents (BUG-3: missing UNIQUE, ARCH-5: missing ext_refs column, ARCH-1: aliases unknown to backend) demonstrated the pattern was unsustainable.

## Decision

Introduce `myblog_shared_db` — a private GitHub repository installable as a Python package via git URL pin — as the single source for SQLAlchemy ORM models and Core Table objects.

**Distribution method chosen**: private GitHub repo + git URL pin.
```
myblog-shared-db @ git+https://github.com/hyuntohoon/myblog_shared_db.git@v0.x.x
```

## Rejected Alternatives

| Option | Reason rejected |
|--------|-----------------|
| **AWS CodeArtifact** | Adds a managed registry to maintain; over-engineered for one-person ops |
| **Git submodule** | Submodule update friction; deploy artifact can silently drift from latest commit |
| **Monorepo** | Attractive long-term but warrants its own RFC; separate decision scope |

## Consequences

**Good**
- Schema drift across services is no longer possible without a coordinated change to `myblog_shared_db`
- `artists.aliases`, `albums.ext_refs`, and similar cross-service columns are defined exactly once
- Step 5 CI check in `myblog_shared_db` detects stale `_generated_schema.sql` and missing canonical columns

**Accepted trade-offs**
- Consumer CI requires `SHARED_DB_PAT` secret to install the private package (handled in Step 2.5)
- `myblog_worker`'s raw-SQL strings reference column names that are not statically validated by the ORM (80% solution — worker imports `tables.py` for structural definitions; SQL strings are not checked)
- `tests/canonical_schema.sql` in `myblog_shared_db` is a copy of `docs/contracts/schema.sql`; the two files must be kept in sync manually (or via a workspace-level CI check, future work)
