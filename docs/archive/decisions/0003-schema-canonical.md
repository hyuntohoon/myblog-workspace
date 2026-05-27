# ADR-0003: Single Canonical Database Schema

**Status**: Accepted  
**Date**: 2026-05-23  
**Deciders**: @hyuntohoon

---

## Context

Three services (`myblog_backend`, `myblog_music`, `myblog_worker`) share one RDS PostgreSQL instance but each had its own schema definition in different locations:

| File | State |
|------|-------|
| `myblog_music/db/schema.sql` | Most complete music catalog; missing `aliases`, junction tables |
| `myblog_backend/app/db/schema_v0.sql` | Missing music catalog columns, `rating`, `rating_scale`, junction tables |
| `myblog_front/schema.sql` | Copy of backend schema; diverged |
| `myblog_backend/backend/app/db/schema_blog.sql` | Oldest version; uses `JSON` not `JSONB`; incomplete |

Additionally, the `aliases` column referenced by `myblog_worker`'s `generate_and_save_aliases` did not exist in any schema file, and the `post_albums`, `post_artists`, `post_recommended_tracks` junction tables in the backend ORM had no DDL counterpart.

---

## Decision

`docs/contracts/schema.sql` in the workspace repo (`myblog-workspace`) is the **single source of truth** for the shared database schema.

Service-local schema files are kept for local dev convenience only — they are clearly marked as derived copies and must not diverge from `docs/contracts/schema.sql`.

---

## Consequences

### What changes

- `docs/contracts/schema.sql` created — merged and corrected DDL for all tables.
- `aliases JSONB NOT NULL DEFAULT '[]'::jsonb` added to `artists` (was missing; already referenced in worker code).
- `rating`, `rating_scale`, `album_cover_url` added to `posts` (aligned with backend ORM).
- `post_albums` (with `is_classic`), `post_artists`, `post_recommended_tracks` junction tables added.
- All timestamps changed to `TIMESTAMPTZ`.
- All JSON columns changed to `JSONB`.
- `IF NOT EXISTS` guards added throughout for idempotent re-runs.
- `myblog_worker`: `albums` upsert `ON CONFLICT DO UPDATE` now includes `ext_refs = EXCLUDED.ext_refs`.
- Service-local schema files updated with a "derived" header comment.

### Drift policy going forward

1. **Schema change proposal**: Update `docs/contracts/schema.sql` in a workspace PR first.
2. **Migration script**: Write an incremental `ALTER TABLE` / `CREATE INDEX CONCURRENTLY` script — never replace the canonical file with a fresh `CREATE TABLE`.
3. **Service propagation**: Update affected service ORM models and local schema files in the same PR or a coordinated follow-up.
4. **Deploy order**: Deploy consumer services (readers) before or simultaneously with services that introduce new columns. Never drop columns until all readers have been updated.

### What does NOT change

- Services retain their own ORM models — the canonical DDL is the reference, not a replacement for the ORM.
- No Alembic / migration tool is mandated yet. Manual `ALTER TABLE` scripts remain acceptable until traffic volume justifies automated migration tooling (tracked as a future ADR).

---

## Alternatives Considered

**1. Keep per-service schema files as-is, rely on ORM as truth**  
Rejected. The ORM is not executable by ops tooling, does not document indices or check constraints, and still diverges across services.

**2. Use `myblog_music/db/schema.sql` as canonical (no new file)**  
Rejected. It lives inside a service repo, giving `myblog_music` implicit ownership of a cross-repo concern. A workspace-level file makes ownership explicit.

**3. Introduce Alembic for automated migration management**  
Deferred. Correct direction but too much operational surface area to adopt now. Revisit when there are 3+ active contributors or a CI migration gate is required.
