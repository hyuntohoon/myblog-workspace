# Plan

Active workspace tracker for cross-repo work. Each row carries `Scope / Order (if multi-repo) / Verification (local + prod smoke) / Rollback / Status`; RFC-backed entries collapse to a one-line pointer at `docs/rfcs/<id>-<slug>.md`. When a row finishes, drop it — `git log` and `docs/archive/done/YYYY-MM.md` are authoritative for history.

---

## Active

_(none — FEAT-review-bucket-board shipped 2026-06-03, all 5 steps; archived to `docs/archive/done/rfcs/` + summary in `docs/archive/done/2026-06.md`.)_

---

## Backlog

- **FEAT-genre-taxonomy** — genre as first-class **multi-valued, managed** taxonomy. Scope: (1) multi-genre on write (write page can attach several genres per post), (2) **genre management API** — create/rename/merge/delete like categories (backend, likely shared_db `genres`/`post_genres`), (3) cross-cutting genre **filtering** reused in music search + review search, (4) unified "browse by genre" view, (5) edit genres on published posts (rides with the future post edit/delete logic). **Cross-repo** (backend + music + shared_db + front) + contract change → needs `architect` (structure) + `planner` (sequencing) before steps. No RFC yet. FEAT-reviews-redesign's `/reviews` genre filter is already array-aware so it slots in without rework.

---

## Later (트리거 대기)

_(none — FEAT-view-redesign trigger fired 2026-05-31, promoted to Active.)_

---

## Frozen (아이디어만, RFC 없음)

확장 기능 후보. 의향 생기면 그때 RFC 시작. 지금 아무것도 안 함.

- **FEAT-spotify-personalize-light** (K) — 1인용 약식: OAuth 1회 → refresh token → Secrets → EventBridge 주기 fetch → `/api/music/recommendations/my-top` → write 사이드바
- **FEAT-new-release-feed** (L) — EventBridge 주기 → 본인 review artist 의 최근 앨범 fetch → `artist_new_releases` → `/api/music/feed/new-releases` → 메인 카드
