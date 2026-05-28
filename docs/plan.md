# Plan

Active workspace tracker for cross-repo work. Each row carries `Scope / Order (if multi-repo) / Verification (local + prod smoke) / Rollback / Status`; RFC-backed entries collapse to a one-line pointer at `docs/rfcs/<id>-<slug>.md`. When a row finishes, drop it — `git log` and `docs/archive/done/YYYY-MM.md` are authoritative for history.

---

## Active

_(none — CHORE-search-orphans wrapped 2026-05-28 with music #25 / workspace #74 / front #30. Prod smoke 22/22; `GET /api/music/artists/spotify/{any}/albums` → 404 confirmed in prod. Also closed stale auto-PRs #60 #62.)_

---

## Backlog

- **PR-metrics-real** — replace `InMemoryMetricsRepository` with a real backing store before exposing like/comment counters publicly. Audit finding M-3.
