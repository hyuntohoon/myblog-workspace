# Plan

Active workspace tracker for cross-repo work. Each row carries `Scope / Order (if multi-repo) / Verification (local + prod smoke) / Rollback / Status`; RFC-backed entries collapse to a one-line pointer at `docs/rfcs/<id>-<slug>.md`. When a row finishes, drop it — `git log` and `docs/archive/done/YYYY-MM.md` are authoritative for history.

---

## Active

- **FEAT-member-dashboard** (draft) — 회원 대시보드 (`/profile`). Auth-gated member page (개요·평론·평론 버킷·라이브러리·통계). RFC → `docs/rfcs/FEAT-member-dashboard.md`. Built in vertical slices. **Step 1 = frontend shell** (myblog_front only): real reviews + derived stats, sample-labeled placeholders behind one adapter (`src/lib/member.ts`), nested bucket board on localStorage. Later steps add backend (library status → listening history → genre/artist agg → nested-bucket backend → multi-user). Verify: `pnpm lint` + `astro check` + browser click-through; prod smoke = deployed chunk grep (auth-gated). Not yet accepted.

---

## Backlog

- **FEAT-genre-taxonomy** (draft) — genre branch-authoring v1 (2-tier single-parent tree, create + assign-parent only; seeded from prod `artists.genres`). RFC → `docs/rfcs/FEAT-genre-taxonomy.md`. v2+ (album↔genre linkage, multi-genre on write, cross-cutting filter, browse-by-genre view, rename/merge/delete) tracked in that RFC's Non-goals. Cross-repo (shared_db V7 → seed → backend API → contract → front). Not yet accepted.

---

## Later (트리거 대기)

_(none — FEAT-view-redesign trigger fired 2026-05-31, promoted to Active.)_

---

## Frozen (아이디어만, RFC 없음)

확장 기능 후보. 의향 생기면 그때 RFC 시작. 지금 아무것도 안 함.

- **FEAT-spotify-personalize-light** (K) — 1인용 약식: OAuth 1회 → refresh token → Secrets → EventBridge 주기 fetch → `/api/music/recommendations/my-top` → write 사이드바
- **FEAT-new-release-feed** (L) — EventBridge 주기 → 본인 review artist 의 최근 앨범 fetch → `artist_new_releases` → `/api/music/feed/new-releases` → 메인 카드
