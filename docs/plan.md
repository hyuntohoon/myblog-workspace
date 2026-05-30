# Plan

Active workspace tracker for cross-repo work. Each row carries `Scope / Order (if multi-repo) / Verification (local + prod smoke) / Rollback / Status`; RFC-backed entries collapse to a one-line pointer at `docs/rfcs/<id>-<slug>.md`. When a row finishes, drop it — `git log` and `docs/archive/done/YYYY-MM.md` are authoritative for history.

---

## Active

_(no active rows — FEAT-write-ux-bundle PR-2 shipped 2026-05-29, see git log)_

---

## Backlog

### BUG-16: tests/conftest.py Neon test branch credential 잔존 (history) — P3

- Scope: `myblog_worker` + Neon console
- Step 1 (2026-05-30 shipped, worker PR #28): fallback default 제거 + URL 을 AWS Secrets Manager `myblog/test-db` 로 이관 + conftest 는 env 만 읽기. git history 의 credential 은 여전히 잔존.
- Step 2 (pending): Neon test branch `neondb_owner` 비번 rotate (Neon 콘솔) → Secrets Manager `myblog/test-db` 및 GHA `secrets.TEST_DB_URL` 새 값으로 동기 업데이트 → history 의 leaked credential 사용 불가화. 사용자 수동 액션.
- Status: ⏳ Step 2 pending — sequential, rotate 후 행 드롭

---

## Later (트리거 대기)

### FEAT-view-redesign: View 페이지 디자인 개편 — 트리거 대기

- 트리거: 사용자 디자인 예시(스크린샷/URL/Figma/손그림) 도착
- 즉시 실행 계획: `~/.claude/plans/soft-hatching-raccoon.md` "G. View 디자인" 절 (Phase 1~4)
- Status: 🔵 awaiting trigger

### CHORE-seo-audit: 블로그 read 경로 OG/sitemap/structured data 조사 — 의향 대기

- 트리거: 사용자 진행 OK
- Step 0 (조사 30분): `src/pages/blog/[slug].astro` + 메인 OG meta, sitemap.xml, JSON-LD 현황
- Step 1: 누락 있으면 `FEAT-seo-essentials` RFC; 의도된 상태면 닫기
- Status: 🔵 awaiting decision

---

## Frozen (아이디어만, RFC 없음)

확장 기능 후보. 의향 생기면 그때 RFC 시작. 지금 아무것도 안 함.

- **FEAT-spotify-personalize-light** (K) — 1인용 약식: OAuth 1회 → refresh token → Secrets → EventBridge 주기 fetch → `/api/music/recommendations/my-top` → write 사이드바
- **FEAT-new-release-feed** (L) — EventBridge 주기 → 본인 review artist 의 최근 앨범 fetch → `artist_new_releases` → `/api/music/feed/new-releases` → 메인 카드
