# Plan

Active workspace tracker for cross-repo work. Each row carries `Scope / Order (if multi-repo) / Verification (local + prod smoke) / Rollback / Status`; RFC-backed entries collapse to a one-line pointer at `docs/rfcs/<id>-<slug>.md`. When a row finishes, drop it — `git log` and `docs/archive/done/YYYY-MM.md` are authoritative for history.

---

## Active

- **PR-reviews-polymorphic** — see `docs/rfcs/PR-reviews-polymorphic-track-rating.md`. Per-track ratings (0–5/0.5, 앨범 척도와 통일) via `post_reviews`, 6 steps across `myblog_shared_db` / `myblog_backend` / `infra` / `myblog_front`. RFC accepted (workspace #85). **Step 0/1/2/3 완료 (2026-05-28)**: Step 0 — prod 에 `review_subject` enum / `post_reviews` table / 3 base indexes base 생성 → Migration A (partial UNIQUE `uq_post_reviews_post_track`) → Migration B (`post_reviews_track_id_fkey` → `ON DELETE CASCADE`). Step 1 — `myblog_shared_db` `PostReview` mapper 추가, `v0.2.0` 태깅 (shared_db#4, commit `a8c6f6f`). Step 2 — `myblog_backend` reviews routes + repository/service + shared-db v0.2.0 핀, 14 신규 테스트, prod smoke 3-path pass (album-hydrated / null-album / 404) (backend#27, commit `8526c75`). Step 3 — `infra/apigateway.tf` 에 PUT/DELETE/POST batch 라우트 3 개 추가 (모두 JWT authorizer `6eia7l`), GET 은 기존 `api_get_proxy` catch-all 그대로 유지, `terraform apply` 3 added/0 changed, prod smoke: 비인증 → 401 (was 404) + Cognito 토큰 PUT/GET/DELETE 라운드트립 OK (workspace#90, commit `f3b8e7e`). 다음: Step 4 (`myblog_front` — `pnpm generate:types` 로 `PostReviewBundle`/`PostReviewTrack`/`TrackReviewUpsert` 타입 동기화 + `astro check`).

---

## Backlog

_(none)_
