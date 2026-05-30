# Plan

Active workspace tracker for cross-repo work. Each row carries `Scope / Order (if multi-repo) / Verification (local + prod smoke) / Rollback / Status`; RFC-backed entries collapse to a one-line pointer at `docs/rfcs/<id>-<slug>.md`. When a row finishes, drop it — `git log` and `docs/archive/done/YYYY-MM.md` are authoritative for history.

---

## Active

### BUG-20: prod SEO meta points to localhost (canonical/og/sitemap broken) — P1

- Scope: `myblog_front` only
- Root cause: `src/constants.ts` SITE.url 하드코딩 `http://localhost:4321` → `seo.astro` canonical/og:url + `@astrojs/sitemap` urls 전부 localhost 로 prod 빌드됨. P2: `robots.txt` 없음, sitemap 에 `drafts`/`write`/`admin`/`test` 포함, blog post `og:type=website` (article 이어야 함).
- Fix: SITE.url → `https://www.ratemymusic.blog` + sitemap filter (`drafts|write|admin|test` exclude) + `public/robots.txt` 추가 + `Seo` 컴포넌트 `type` prop 추가 (blog/[slug] 에서 `article` 주입).
- Verification: local — `pnpm lint` + `astro check` + `astro build` 후 `dist/sitemap-0.xml`, `dist/robots.txt`, sample post canonical/og 검사 (완료). prod smoke — 머지 후 `curl https://www.ratemymusic.blog/{sitemap-index.xml,sitemap-0.xml,robots.txt}` + 샘플 post HTML canonical/og 확인.
- Rollback: 단순 revert (constants + config + seo + slug + robots.txt).
- Status: ⏳ branch `fix/BUG-20-seo-prod-url-broken` 구현 + local verify 완료, push 대기
- Follow-up backlog (P3): default OG image (`/og-image.png` 부재), JSON-LD (Article/BlogPosting), RSS feed (현재 `seo.astro` 가 존재하지 않는 `/rss.xml` 참조), 더미 blog entries (`blog/2`, `blog/2211`, ...) 정리

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

---

## Frozen (아이디어만, RFC 없음)

확장 기능 후보. 의향 생기면 그때 RFC 시작. 지금 아무것도 안 함.

- **FEAT-spotify-personalize-light** (K) — 1인용 약식: OAuth 1회 → refresh token → Secrets → EventBridge 주기 fetch → `/api/music/recommendations/my-top` → write 사이드바
- **FEAT-new-release-feed** (L) — EventBridge 주기 → 본인 review artist 의 최근 앨범 fetch → `artist_new_releases` → `/api/music/feed/new-releases` → 메인 카드
