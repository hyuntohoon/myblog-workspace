# Plan

Active workspace tracker for cross-repo work. Each row carries `Scope / Order (if multi-repo) / Verification (local + prod smoke) / Rollback / Status`; RFC-backed entries collapse to a one-line pointer at `docs/rfcs/<id>-<slug>.md`. When a row finishes, drop it — `git log` and `docs/archive/done/YYYY-MM.md` are authoritative for history.

---

## Active

_(none)_

---

## Backlog

- **PR-reviews-polymorphic** — see `docs/rfcs/PR-reviews-polymorphic-track-rating.md`. Per-track ratings (0–5/0.5, 앨범 척도와 통일) via `post_reviews`, 6 steps across `myblog_shared_db` / `myblog_backend` / `infra` / `myblog_front`. 4 결정 확정 (Decisions log: scale=5, partial UNIQUE `(post_id, track_id)`, FK `ON DELETE CASCADE`, batch all-or-nothing). Status: draft RFC — 사용자가 `accepted` 로 promote 후 Step 0 (Neon prod schema verify + 2 migrations) 부터.
