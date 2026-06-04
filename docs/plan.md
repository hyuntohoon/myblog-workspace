# Plan

Active workspace tracker for cross-repo work. Each row carries `Scope / Order (if multi-repo) / Verification (local + prod smoke) / Rollback / Status`; RFC-backed entries collapse to a one-line pointer at `docs/rfcs/<id>-<slug>.md`. When a row finishes, drop it — `git log` and `docs/archive/done/YYYY-MM.md` are authoritative for history.

---

## Active

- **FEAT-member-dashboard** (accepted) — 회원 대시보드 (`/profile`). Auth-gated member page (개요·평론·평론 버킷·라이브러리·통계). RFC → `docs/rfcs/FEAT-member-dashboard.md`. Built in vertical slices. **Step 1 = frontend shell** shipped (#72): real reviews + derived stats, sample-labeled placeholders behind one adapter (`src/lib/member.ts`), nested bucket board on localStorage. **Step 2 = library tab data (to-listen + reviewed)** in progress — three-source design per RFC Decisions D18 (new `album_to_listen_items` table + reviewed derived view from `post_albums`; the 3rd source "최근 들은 앨범" comes in Step 3). Later steps: Step 3 listening history + Spotify 연동 (hybrid 1h cron + manual refresh, OAuth in /profile→연동) → Step 4 genre/artist agg → Step 5 nested-bucket backend + retire `/reviews/queue` → Step 6 multi-user. Verify: `pnpm lint` + `astro check` + browser click-through; prod smoke = deployed chunk grep (auth-gated).

---

## Backlog

- **FEAT-genre-taxonomy** (draft) — genre branch-authoring v1 (2-tier single-parent tree, create + assign-parent only; seeded from prod `artists.genres`). RFC → `docs/rfcs/FEAT-genre-taxonomy.md`. v2+ (album↔genre linkage, multi-genre on write, cross-cutting filter, browse-by-genre view, rename/merge/delete) tracked in that RFC's Non-goals. Cross-repo (shared_db V7 → seed → backend API → contract → front). Not yet accepted.
- **FEAT-header-scroll-prefs** (draft) — site-wide header scroll behavior with three user-selectable modes (hide-on-scroll-down / compact-on-scroll / threshold-hide), default = hide-on-scroll-down. RFC → `docs/rfcs/FEAT-header-scroll-prefs.md`. Frontend-only single repo. Not yet accepted.

---

## Later (트리거 대기)

_(none — FEAT-view-redesign trigger fired 2026-05-31, promoted to Active.)_

---

## Frozen (아이디어만, RFC 없음)

확장 기능 후보. 의향 생기면 그때 RFC 시작. 지금 아무것도 안 함.

- **FEAT-spotify-personalize-light** (K) — 1인용 약식 Spotify 연동: OAuth 1회(PKCE, scopes=`user-read-recently-played` + `user-read-currently-playing`, 쓰기 scope 는 FEAT-member-dashboard D11 따라 v2 로) → refresh token in Secrets Manager `myblog/spotify`(Q17) → 하이브리드 sync(D5: EventBridge **1h cron** + `/profile→라이브러리`의 "지금 새로고침" 버튼 SQS 트리거) → DB 캐시(`spotify_recent_albums`) → `/api/library/recently-listened` + now-playing. **이 항목은 FEAT-member-dashboard Step 3 의 인프라 트랙**으로 흡수 예정 — Step 3 ship 시 본 Frozen 라인 삭제.
- **FEAT-new-release-feed** (L) — EventBridge 주기 → 본인 review artist 의 최근 앨범 fetch → `artist_new_releases` → `/api/music/feed/new-releases` → 메인 카드
