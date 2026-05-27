# Plan

Active workspace tracker for cross-repo work. Each row carries `Scope / Order (if multi-repo) / Verification (local + prod smoke) / Rollback / Status`; RFC-backed entries collapse to a one-line pointer at `docs/rfcs/<id>-<slug>.md`. When a row finishes, drop it — `git log` and `docs/archive/done/YYYY-MM.md` are authoritative for history.

---

## Active

_(none — PR-12 wrapped 2026-05-28 with music #23 / workspace #68 / front #28. Prod smoke 22/22 + direct `/candidates` shape check (exclude_none keys, all 8 typed album fields populated).)_

---

## Backlog

- **PR-13** — decide delete vs `ENV` gate for legacy `/api/music/search?mode=` (music + front + workspace). Audit finding M-2.
- **PR-metrics-real** — replace `InMemoryMetricsRepository` with a real backing store before exposing like/comment counters publicly. Audit finding M-3.
