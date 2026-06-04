# Plan

Active workspace tracker for cross-repo work. Each row carries `Scope / Order (if multi-repo) / Verification (local + prod smoke) / Rollback / Status`; RFC-backed entries collapse to a one-line pointer at `docs/rfcs/<id>-<slug>.md`. When a row finishes, drop it — `git log` and `docs/archive/done/YYYY-MM.md` are authoritative for history.

---

## Active

- **FEAT-member-dashboard** (accepted) — 회원 대시보드 (`/profile`). Auth-gated member page (개요·평론·평론 버킷·라이브러리·통계). RFC → `docs/rfcs/FEAT-member-dashboard.md`. Built in vertical slices. **Step 1 = frontend shell** shipped (#72): real reviews + derived stats, sample-labeled placeholders behind one adapter (`src/lib/member.ts`), nested bucket board on localStorage. **Step 2 = library tab data (to-listen + reviewed)** shipped — three-source design per RFC Decisions D18 (new `album_to_listen_items` table [shared_db v0.7.0, Neon V8] + reviewed derived view from `post_albums`; the 3rd source "최근 들은 앨범" comes in Step 3). Backend `GET/POST/DELETE/PUT /api/library/to-listen` + `GET /api/library/reviewed`, JWT routes applied, front 라이브러리 tab real. prod e2e verified (to-listen CRUD+reorder via smoke JWT; reviewed GET real data). **Step 3 = listening history + now-playing + Spotify 연동** (cross-repo, in progress): the 3rd library source "최근 들은 앨범" (D25/D26) + now-playing banner, worker/EventBridge-fed (rule #9). shared_db `spotify_recent_albums` + `spotify_now_playing` + append-only `spotify_play_events` (durable history for Step 4 listen-counts, D29) [v0.8.0, Neon V9]; worker EventBridge **1h cron** (`{job:"spotify_listening"}`) + manual "지금 새로고침" SQS trigger (`{job:"spotify_refresh"}`, server-debounced ~60s, D31) with retry/backoff + symmetric isolation; backend `GET /api/library/recently-listened` + `/now-playing` + `/spotify-connection` (**intentionally public** vanity reads, D28 — now-playing drops progress_ms/duration_ms, idle keeps updated_at) + `POST /api/library/refresh-recent` (JWT→SQS; returns `last_synced_at` for UI poll, D31); front 라이브러리 real recent + 새로고침 button + honest read-only now-playing + new **연동 tab**. Spotify refresh token bootstrapped **out-of-band** (`scripts/spotify_bootstrap_token.py`) into Secrets Manager `myblog/spotify`; worker writes back rotated tokens + status reflects validity (D30); in-app PKCE OAuth deferred (D27). Infra: EventBridge rule + `myblog/spotify` secret IAM + backend/worker `sqs:SendMessage` + apigateway JWT route **for the POST only** + FailedInvocations/staleness alarms (manual `terraform apply`). **Order**: create `myblog/spotify` secret → apply Neon V9 + confirm `\dt` → tag shared_db v0.8.0 + merge backend/worker → terraform apply → bootstrap token → deploy front (★ secret-before-apply & V9-before-backend-merge are hard gates). → Step 4 genre/artist agg → Step 5 nested-bucket backend + retire `/reviews/queue` → Step 6 multi-user. Verify: `pnpm lint` + `astro check` + browser click-through; prod smoke = deployed chunk grep (auth-gated) + DB-row evidence for the cache.

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

- **FEAT-new-release-feed** (L) — EventBridge 주기 → 본인 review artist 의 최근 앨범 fetch → `artist_new_releases` → `/api/music/feed/new-releases` → 메인 카드
