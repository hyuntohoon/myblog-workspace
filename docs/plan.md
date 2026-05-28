# Plan

Active workspace tracker for cross-repo work. Each row carries `Scope / Order (if multi-repo) / Verification (local + prod smoke) / Rollback / Status`; RFC-backed entries collapse to a one-line pointer at `docs/rfcs/<id>-<slug>.md`. When a row finishes, drop it — `git log` and `docs/archive/done/YYYY-MM.md` are authoritative for history.

---

## Active

- **PR-reviews-polymorphic** — see `docs/rfcs/PR-reviews-polymorphic-track-rating.md`. Per-track ratings (0–5/0.5, 앨범 척도와 통일) via `post_reviews`, 6 steps across `myblog_shared_db` / `myblog_backend` / `infra` / `myblog_front`. RFC accepted (workspace #85). **Step 0 완료 (2026-05-28)**: prod 에 `review_subject` enum / `post_reviews` table / 3 base indexes 가 부재 상태였어서 canonical DDL 로 base 생성 → Migration A (partial UNIQUE `uq_post_reviews_post_track`) → Migration B (`post_reviews_track_id_fkey` → `ON DELETE CASCADE`) 순으로 적용. schema 파일 동기화 진행 중. 다음: Step 1 (`myblog_shared_db` v0.2.0 — `PostReview` mapper).

---

## Backlog

_(none)_
