# Plan

Active workspace tracker for cross-repo work. Each row carries `Scope / Order (if multi-repo) / Verification (local + prod smoke) / Rollback / Status`; RFC-backed entries collapse to a one-line pointer at `docs/rfcs/<id>-<slug>.md`. When a row finishes, drop it — `git log` and `docs/archive/done/YYYY-MM.md` are authoritative for history.

---

## Active

_(none — FEAT-view-redesign closed 2026-05-31, all 6 active steps shipped end-to-end across `myblog_front`, `myblog_backend`, `myblog_shared_db`. Step 7 ("Appears On") stays deferred as a pointer for a future RFC. See `docs/archive/done/rfcs/FEAT-view-redesign.md` or `git log` for per-step merges.)_

_(FEAT-writer-lowfreq-redesign closed 2026-05-31, all 6 steps shipped end-to-end. See `docs/rfcs/FEAT-writer-lowfreq-redesign.md` or `git log` for merge commits across all repos.)_

---

## Backlog

_(none — BUG-16 Step 2 closed 2026-05-30: Neon test-db credential rotated via Neon API, stores synced, leaked credential dead. See git log + docs/archive/done/2026-05.md)_

---

## Later (트리거 대기)

_(none — FEAT-view-redesign trigger fired 2026-05-31, promoted to Active.)_

---

## Frozen (아이디어만, RFC 없음)

확장 기능 후보. 의향 생기면 그때 RFC 시작. 지금 아무것도 안 함.

- **FEAT-spotify-personalize-light** (K) — 1인용 약식: OAuth 1회 → refresh token → Secrets → EventBridge 주기 fetch → `/api/music/recommendations/my-top` → write 사이드바
- **FEAT-new-release-feed** (L) — EventBridge 주기 → 본인 review artist 의 최근 앨범 fetch → `artist_new_releases` → `/api/music/feed/new-releases` → 메인 카드
