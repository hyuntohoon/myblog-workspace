# Plan

Active workspace tracker for cross-repo work. Each row carries `Scope / Order (if multi-repo) / Verification (local + prod smoke) / Rollback / Status`; RFC-backed entries collapse to a one-line pointer at `docs/rfcs/<id>-<slug>.md`. When a row finishes, drop it — `git log` and `docs/archive/done/YYYY-MM.md` are authoritative for history.

---

## Active

- **STAB-1** (accepted) — **System stabilization & hardening (pre-expansion)**. Investigation/prioritization/sequencing of the 2026-06-05 arch review, re-verified against code (47 real issues across auth boundary / worker-SQS-EventBridge / shared_db-schema drift / repo hygiene / S3-CloudFront / search-observability / side-effecting GET / IAM), plus the final **category → section + review-tags** model decision. RFC → `docs/rfcs/STAB-1-stabilization.md`. **No code/Terraform/data/file changes in this RFC** — it ends at "evidence required before implementation"; fixes spawn scoped follow-up RFCs/BUG rows. **Top priority: product expansion is frozen behind this** (see Backlog/Later/Frozen — each item is blocked on its stabilization area; multi-user→P0 auth, genre→P2 schema, distribution/feed→worker observability). Caching is out of scope. Status **accepted** (2026-06-05, owner-approved).
- **STAB-5** (accepted) — **category → section taxonomy + review tags** (STAB-1 §Seq item 5 + §model decision; STAB-1 called it `FEAT-section-taxonomy`). Implements the ratified model: rename `category`→`section` (keep single FK), migration-seeded curated set, **no public create API**, review tags reuse the empty `tags`/`post_tags` M:N, reset junk data. Evidence (06-05): **all 13 prod posts + 11 MDX + 3 categories are junk** → clean reset, no data loss. Cross-repo (shared_db **V13** [next contiguous after V12; reconcile genre RFC's V13 claim — STAB-5 OQ4] → backend → writer → tags → contract → data/MDX reset). **Depends on STAB-2** (removes `POST /api/categories`); coordinate w/ STAB-4 (schema.sql). RFC → `docs/rfcs/STAB-5-section-taxonomy.md`. Step 6 destructive (human approval). Status **accepted** (2026-06-05, owner-approved). **Progress 2026-06-06:** OQ1/2/3/4 all resolved (OQ2 review-tags = `album review`/`track review`/`reissue`/`best album`/`year-end list`). **Step 1 DONE ✅** (shared_db #21 `320a76b` + tag `v0.12.0`; **V13 applied to prod Neon**). **Step 2 DONE ✅** (backend #56 `d3cce15` deployed; pin→`@v0.12.0`, `Category`→`Section`, get-or-create removed→reject-unknown, read-only `GET /api/sections`, `POST /api/categories` hole closed; prod smoke green — `/api/sections`→200 seed, `/api/categories`→404, authed `/api/posts`→200). **Step 3 DONE ✅** (front #97 `60864df` deployed, parallel Lane B; build-time-seed picker, dead code deleted; prod `/api/categories.json`→404). V13+Step2 ran back-to-back (option A); window = deploy duration, admin-writer only. **Remaining:** Step 4 review tags (unblocked); Step 5 contract regen (workspace auto-PR **#270** open, no CI, ready on go); Step 6 destructive data/MDX reset.

> ℹ️ **STAB-1 §Seq item 3 (SNS alert email subscription, P1-6) — RESOLVED 2026-06-05.** Live check: the `myblog-alerts` email subscription has a real SubscriptionArn (not `PendingConfirmation`) → confirmed/active → alarms deliver. No RFC, no owner action needed.

---

## Backlog

> ⛔ **Blocked behind STAB-1.** No expansion item below is promoted to Active until the STAB-1 P0 auth boundary + P1-1 SQS fix land and the section-model decision is implemented.

- **FEAT-genre-artist-distribution** (draft) — `/profile` 통계 charts: genre + artist/listen distribution. Carved from `FEAT-member-dashboard` Step 4. RFC → `docs/rfcs/FEAT-genre-artist-distribution.md`. Depends on `FEAT-genre-taxonomy` (genre, **deferred → Later**) + `spotify_play_events` (shipped, listen counts). Not yet scoped/accepted.
- **FEAT-multi-user-accounts** (draft) — user/profile model, public `/members/[handle]`, social graph; un-hides social stats. Carved from `FEAT-member-dashboard` Step 6. RFC → `docs/rfcs/FEAT-multi-user-accounts.md`. Largest follow-on; needs data + auth model. Not yet scoped/accepted.

---

## Later (트리거 대기)

- **FEAT-genre-taxonomy** (draft, **deferred 2026-06-05** — 주인장 추후 착수) — genre branch-authoring v1 (2-tier single-parent tree, create + assign-parent only; seeded from prod `artists.genres`). RFC → `docs/rfcs/FEAT-genre-taxonomy.md`. v2+ (album↔genre linkage, multi-genre on write, cross-cutting filter, browse-by-genre view, rename/merge/delete) in the RFC Non-goals. Cross-repo (shared_db **V13 / v0.12.0** → seed → backend API + infra → contract → front; numbering refreshed 06-05 after music-search-recall shipped V12-only). 착수 트리거 = 주인장 의향; UI 경로(OQ2) 는 그때 결정. RFC numbering 최신, Status draft. 의존 기능 `FEAT-genre-artist-distribution` 도 대기.

---

## Frozen (아이디어만, RFC 없음)

확장 기능 후보. 의향 생기면 그때 RFC 시작. 지금 아무것도 안 함.

- **FEAT-new-release-feed** (L) — EventBridge 주기 → 본인 review artist 의 최근 앨범 fetch → `artist_new_releases` → `/api/music/feed/new-releases` → 메인 카드
