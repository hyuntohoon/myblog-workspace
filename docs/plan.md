# Plan

Active workspace tracker for cross-repo work. Each row carries `Scope / Order (if multi-repo) / Verification (local + prod smoke) / Rollback / Status`; RFC-backed entries collapse to a one-line pointer at `docs/rfcs/<id>-<slug>.md`. When a row finishes, drop it — `git log` and `docs/archive/done/YYYY-MM.md` are authoritative for history.

---

## Active

_(none — BUG-10 wrapped 2026-05-28 with backend #24 / workspace #63 / front #26 / smoke #64. Prod smoke 22/22 incl. new PUT-category round-trip guard.)_

---

## Backlog

- **PR-12** — type `/api/music/search/candidates` response (music + workspace + front). Audit finding M-1.
- **PR-13** — decide delete vs `ENV` gate for legacy `/api/music/search?mode=` (music + front + workspace). Audit finding M-2.
- **CHORE-front-typing** — switch `review/index.ts` AlbumDetail to generated types; drop `json?.items` fallback in `fetchCategories`; type `searchBar*.client.ts` mappers. Audit findings L-1 / L-2 / L-3.
- **PR-metrics-real** — replace `InMemoryMetricsRepository` with a real backing store before exposing like/comment counters publicly. Audit finding M-3.
