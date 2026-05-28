# Plan

Active workspace tracker for cross-repo work. Each row carries `Scope / Order (if multi-repo) / Verification (local + prod smoke) / Rollback / Status`; RFC-backed entries collapse to a one-line pointer at `docs/rfcs/<id>-<slug>.md`. When a row finishes, drop it — `git log` and `docs/archive/done/YYYY-MM.md` are authoritative for history.

---

## Active

- **PR-metrics-real** — backend swap + IaC route merged (backend #25, workspace #77 plan row, workspace #78 `aws_apigatewayv2_route.metrics_batch_post`). Cognito `admin_client` drift cleared in workspace #81 (코드를 라이브 상태에 맞춤). `terraform plan` 결과 이제 `1 to add, 0 to change, 0 to destroy` — `metrics_batch_post` 단독. Prod smoke (`POST /api/metrics/batch` against a known slug returning non-mock counters) verifies after apply. Status: pending human `terraform apply`.

---

## Backlog

- **PR-reviews-polymorphic** — see `docs/rfcs/PR-reviews-polymorphic-track-rating.md`. Per-track ratings (0–10/0.5) via `post_reviews`, 6 steps across `myblog_shared_db` / `myblog_backend` / `infra` / `myblog_front`. Status: draft RFC, 4 open questions (rating_scale, unique constraint, FK on track delete, batch atomicity).
