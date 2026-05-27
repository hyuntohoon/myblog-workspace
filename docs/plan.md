# Plan

Active workspace tracker for cross-repo work. Each row carries `Scope / Order (if multi-repo) / Verification (local + prod smoke) / Rollback / Status`; RFC-backed entries collapse to a one-line pointer at `docs/rfcs/<id>-<slug>.md`. When a row finishes, drop it — `git log` and `docs/archive/done/YYYY-MM.md` are authoritative for history.

---

## Active

- **BUG-10 — PUT /api/posts/{id} silently drops category / album_ids / artist_ids.**
  Scope: backend (`schemas.py` UpdatePostRequest + post_service.update / post_repository.update for M2M handling) → workspace (regen openapi.json) → front (regen api.gen.ts, re-test WriterApp draft edit).
  Order: backend PR first (with pytest covering POST→PUT(category swap)→GET); workspace merges contract; front PR consumes new types.
  Verification: local pytest in backend; `pnpm exec astro check` + `pnpm lint` in front; prod smoke extended with update-category step (`scripts/smoke.sh`).
  Rollback: `git revert` per repo; OpenAPI re-merge is idempotent.
  Status: drafted 2026-05-28 from `docs/contracts/audit-2026-05-28.md` finding H-1.

---

## Backlog

- **PR-12** — type `/api/music/search/candidates` response (music + workspace + front). Audit finding M-1.
- **PR-13** — decide delete vs `ENV` gate for legacy `/api/music/search?mode=` (music + front + workspace). Audit finding M-2.
- **CHORE-front-typing** — switch `review/index.ts` AlbumDetail to generated types; drop `json?.items` fallback in `fetchCategories`; type `searchBar*.client.ts` mappers. Audit findings L-1 / L-2 / L-3.
- **PR-metrics-real** — replace `InMemoryMetricsRepository` with a real backing store before exposing like/comment counters publicly. Audit finding M-3.
