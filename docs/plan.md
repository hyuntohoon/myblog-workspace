# Plan

Active workspace tracker for cross-repo work. Each row carries `Scope / Order (if multi-repo) / Verification (local + prod smoke) / Rollback / Status`; RFC-backed entries collapse to a one-line pointer at `docs/rfcs/<id>-<slug>.md`. When a row finishes, drop it — `git log` and `docs/archive/done/YYYY-MM.md` are authoritative for history.

---

## Active

- **PR-metrics-real** — backend swap merged (backend #25, workspace #77). Prod smoke blocked: `POST /api/metrics/batch` never wired in `infra/apigateway.tf` → always 404 in prod, frontend falls back silently. Infra fix in workspace #78 (terraform plan clean: 1 add, pre-existing cognito drift to resolve separately). Status: pending human terraform apply.

---

## Backlog

- **PR-reviews-polymorphic** — see `docs/rfcs/PR-reviews-polymorphic-track-rating.md`. Per-track ratings (0–10/0.5) via `post_reviews`, 6 steps across `myblog_shared_db` / `myblog_backend` / `infra` / `myblog_front`. Status: draft RFC, 4 open questions (rating_scale, unique constraint, FK on track delete, batch atomicity).
