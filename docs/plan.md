# Plan

Active workspace tracker for cross-repo work. Each row carries `Scope / Order (if multi-repo) / Verification (local + prod smoke) / Rollback / Status`; RFC-backed entries collapse to a one-line pointer at `docs/rfcs/<id>-<slug>.md`. When a row finishes, drop it — `git log` and `docs/archive/done/YYYY-MM.md` are authoritative for history.

---

## Active

- **CHORE-search-orphans — sweep remaining search-related orphans surfaced after PR-13.**
  Scope: music (`app/api/routers/artists.py` drop `get_spotify_artist_albums`; `app/services/artist_service.py` drop `list_albums_by_spotify_artist`; regen openapi.json) → workspace (auto-merged contract refresh) → front (delete `src/scripts/searchBarSpotify.client.ts`; regen `api.gen.ts`).
  Order: music PR → workspace contract auto-merge → front PR.
  Verification: music `pytest`; front `pnpm lint` + `pnpm exec astro check`; prod smoke `scripts/smoke.sh prod` (22/22 unchanged) + curl `GET /api/music/artists/spotify/{any}/albums` → 404 after deploy.
  Rollback: `git revert` per repo; contract regen idempotent.
  Status: drafted 2026-05-28 post-PR-13. The route had a single live caller (`searchBarSpotify.client.ts`), which itself is fully orphan — no astro page/component imported it. `external_candidates()` / `AlbumCandidateMapper` already gone with PR-13's basic_search sweep.

---

## Backlog

- **PR-metrics-real** — replace `InMemoryMetricsRepository` with a real backing store before exposing like/comment counters publicly. Audit finding M-3.
