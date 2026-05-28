# Plan

Active workspace tracker for cross-repo work. Each row carries `Scope / Order (if multi-repo) / Verification (local + prod smoke) / Rollback / Status`; RFC-backed entries collapse to a one-line pointer at `docs/rfcs/<id>-<slug>.md`. When a row finishes, drop it — `git log` and `docs/archive/done/YYYY-MM.md` are authoritative for history.

---

## Active

- **PR-metrics-real** — backend #25 swaps `InMemoryMetricsRepository` → `SqlMetricsRepository` reading `post_metrics.likes/comments_count` joined on `posts.slug`. API shape unchanged, no contract regen. Scope: backend only. Verification: 23/23 pytest + prod smoke `POST /api/metrics/batch` against a known published slug. Rollback: revert single PR (no data change). Status: PR open, awaiting CI + merge.

---

## Backlog

- **PR-metrics-real** — replace `InMemoryMetricsRepository` with a real backing store before exposing like/comment counters publicly. Audit finding M-3.
