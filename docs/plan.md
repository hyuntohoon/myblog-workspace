# Plan

Active workspace tracker for cross-repo work. Each row carries `Scope / Order (if multi-repo) / Verification (local + prod smoke) / Rollback / Status`; RFC-backed entries collapse to a one-line pointer at `docs/rfcs/<id>-<slug>.md`. When a row finishes, drop it — `git log` and `docs/archive/done/YYYY-MM.md` are authoritative for history.

---

## Active

- **PR-reviews-polymorphic** — see `docs/rfcs/PR-reviews-polymorphic-track-rating.md`. Per-track ratings (0–5/0.5, 앨범 척도와 통일) via `post_reviews`, 6 steps across `myblog_shared_db` / `myblog_backend` / `infra` / `myblog_front`. RFC accepted (workspace #85). **Step 0/1 완료 (2026-05-28)**: Step 0 — prod 에 `review_subject` enum / `post_reviews` table / 3 base indexes base 생성 → Migration A (partial UNIQUE `uq_post_reviews_post_track`) → Migration B (`post_reviews_track_id_fkey` → `ON DELETE CASCADE`). Step 1 — `myblog_shared_db` `PostReview` mapper 추가, `v0.2.0` 태깅 (shared_db#4, commit `a8c6f6f`). 다음: Step 2 (`myblog_backend` — shared-db 핀 0.2.0 으로 업데이트 + reviews routes/repository/service).

---

## Backlog

_(none)_
