# Plan

Active workspace tracker for cross-repo work. Each row carries `Scope / Order (if multi-repo) / Verification (local + prod smoke) / Rollback / Status`; RFC-backed entries collapse to a one-line pointer at `docs/rfcs/<id>-<slug>.md`. When a row finishes, drop it — `git log` and `docs/archive/done/YYYY-MM.md` are authoritative for history.

---

## Active

_(none — FEAT-writer-lowfreq-redesign closed 2026-05-31, all 6 steps shipped end-to-end. See `docs/rfcs/FEAT-writer-lowfreq-redesign.md` for the per-step status blocks, or `git log` for the merge commits across `myblog_shared_db`, `myblog_music`, `myblog_backend`, `myblog_front`, and workspace.)_

---

## Backlog

_(none — BUG-16 Step 2 closed 2026-05-30: Neon test-db credential rotated via Neon API, stores synced, leaked credential dead. See git log + docs/archive/done/2026-05.md)_

---

## Later (트리거 대기)

### FEAT-view-redesign: View 페이지 디자인 개편 — 트리거 대기

- 트리거: 사용자 디자인 예시(스크린샷/URL/Figma/손그림) 도착
- 즉시 실행 계획: `~/.claude/plans/soft-hatching-raccoon.md` "G. View 디자인" 절 (Phase 1~4)
- Status: 🔵 awaiting trigger

---

## Frozen (아이디어만, RFC 없음)

확장 기능 후보. 의향 생기면 그때 RFC 시작. 지금 아무것도 안 함.

- **FEAT-spotify-personalize-light** (K) — 1인용 약식: OAuth 1회 → refresh token → Secrets → EventBridge 주기 fetch → `/api/music/recommendations/my-top` → write 사이드바
- **FEAT-new-release-feed** (L) — EventBridge 주기 → 본인 review artist 의 최근 앨범 fetch → `artist_new_releases` → `/api/music/feed/new-releases` → 메인 카드
