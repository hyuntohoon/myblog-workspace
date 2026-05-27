# Plan

Active workspace tracker for cross-repo work. Each row carries `Scope / Order (if multi-repo) / Verification (local + prod smoke) / Rollback / Status`; RFC-backed entries collapse to a one-line pointer at `docs/rfcs/<id>-<slug>.md`. When a row finishes, drop it — `git log` and `docs/archive/done/YYYY-MM.md` are authoritative for history.

---

## Active

- **PR-12 — type `/api/music/search/candidates` response (replace `Dict[str, Any]` + `{}` contract).**
  Scope: music (`app/domain/schemas.py` new `CandidateSearchResult` + nested item/pagination models, wire `response_model=` on `routers/search.py:search_candidates`) → workspace (regen `docs/contracts/openapi.json` via `scripts/merge_openapi.py`) → front (regen `src/lib/api.gen.ts`, replace local `CandidateSearchResponse` in `src/scripts/types/search.ts` with `components['schemas']['Music_CandidateSearchResult']`, drop `TODO(PR-12)` markers).
  Order: music PR first (pytest covers response shape); workspace merges contract once music deploys; front PR consumes generated types.
  Verification: music `pytest` + local `/candidates` request shape inspection; workspace `python3 scripts/merge_openapi.py` + diff review; front `pnpm lint` + `pnpm exec astro check`; prod smoke regression-free (`scripts/smoke.sh prod` — no new positive coverage required because `/candidates` already exercised by writer page sync flow).
  Rollback: `git revert` per repo; contract regen is idempotent.
  Status: drafted 2026-05-28 from `docs/contracts/audit-2026-05-28.md` finding M-1. Picks up `TODO(PR-12)` marker left by `CHORE-front-typing` (workspace #66 / front #27).

---

## Backlog

- **PR-13** — decide delete vs `ENV` gate for legacy `/api/music/search?mode=` (music + front + workspace). Audit finding M-2.
- **PR-metrics-real** — replace `InMemoryMetricsRepository` with a real backing store before exposing like/comment counters publicly. Audit finding M-3.
