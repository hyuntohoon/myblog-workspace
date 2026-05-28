# Plan

Active workspace tracker for cross-repo work. Each row carries `Scope / Order (if multi-repo) / Verification (local + prod smoke) / Rollback / Status`; RFC-backed entries collapse to a one-line pointer at `docs/rfcs/<id>-<slug>.md`. When a row finishes, drop it — `git log` and `docs/archive/done/YYYY-MM.md` are authoritative for history.

---

## Active

- **PR-13 — delete legacy `/api/music/search?mode=` end-to-end.**
  Decision (2026-05-28): pick Option 1 from audit M-2 — delete the endpoint + the orphan front file + dev-only `searchTest/` pages. Production search/sync/SQS path (`<SearchBar>` → `searchBarDb.client.ts` → `/search/unified` + `/search/candidates`) is untouched; only orphan code shipped today is removed.
  Scope: music (`app/api/routers/search.py` drop `basic_search`; `app/services/search_service.py` drop `basic_search` + `_handle_artist_search` + `_handle_album_search`; regen openapi.json) → workspace (auto-merged contract refresh) → front (delete `src/scripts/searchBar.client.ts` + `src/pages/searchTest/`; regen api.gen.ts).
  Order: music PR first (route gone → contract auto-PR) → workspace contract merge → front PR (api.gen drift fixed + dead files removed).
  Verification: music `pytest`; workspace contract diff review; front `pnpm lint` + `pnpm exec astro check`; prod smoke `scripts/smoke.sh prod` (22/22 unchanged — endpoint deletion doesn't touch any smoke-covered path) + curl `GET /api/music/search?mode=album` → 404 after deploy.
  Rollback: `git revert` per repo; contract regen idempotent. Endpoint can be re-added trivially from history if a future caller needs it.
  Status: drafted 2026-05-28 from `docs/contracts/audit-2026-05-28.md` finding M-2. external_candidates() / AlbumCandidateMapper / searchBarSpotify.client.ts are out of scope (also orphan, but separate chore).

---

## Backlog

- **PR-metrics-real** — replace `InMemoryMetricsRepository` with a real backing store before exposing like/comment counters publicly. Audit finding M-3.
