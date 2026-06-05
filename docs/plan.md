# Plan

Active workspace tracker for cross-repo work. Each row carries `Scope / Order (if multi-repo) / Verification (local + prod smoke) / Rollback / Status`; RFC-backed entries collapse to a one-line pointer at `docs/rfcs/<id>-<slug>.md`. When a row finishes, drop it — `git log` and `docs/archive/done/YYYY-MM.md` are authoritative for history.

---

## Active

- **STAB-1** (draft) — **System stabilization & hardening (pre-expansion)**. Investigation/prioritization/sequencing of the 2026-06-05 arch review, re-verified against code (47 real issues across auth boundary / worker-SQS-EventBridge / shared_db-schema drift / repo hygiene / S3-CloudFront / search-observability / side-effecting GET / IAM), plus the final **category → section + review-tags** model decision. RFC → `docs/rfcs/STAB-1-stabilization.md`. **No code/Terraform/data/file changes in this RFC** — it ends at "evidence required before implementation"; fixes spawn scoped follow-up RFCs/BUG rows. **Top priority: product expansion is frozen behind this** (see Backlog/Later/Frozen — each item is blocked on its stabilization area; multi-user→P0 auth, genre→P2 schema, distribution/feed→worker observability). Caching is out of scope. Status draft (accept = human-only).
- **STAB-2** (draft) — **P0 auth boundary remediation** (STAB-1 §Seq item 1). Evidence re-verified **live 2026-06-05**: AUTH-3 `Bearer x` bypass + AUTH-9 unauth draft disclosure (2 drafts) confirmed on the raw invoke domain; AUTH-5 backend `require_cognito_token` fail-open (no `COGNITO_USER_POOL_ID`); P6-2 music `/candidates` answers unauth (no `ENV` key); no REGIONAL WAF (HTTP API can't take WAFv2); no stage throttle. RFC → `docs/rfcs/STAB-2-p0-auth-boundary.md`. 5 steps (fail-closed app guard → edge_guard JWT validation → gate/remove `POST /api/categories` → music `/candidates` auth → bound invoke domain). Cross-repo (backend + music + front + infra); infra steps need human apply. Status draft (accept = human-only).
- **STAB-3** (draft) — **blogSQS visibility ≥ worker timeout** (STAB-1 §Seq item 2 / P1-1). Evidence **live 2026-06-05**: visibility 30s ≪ worker 120s; CloudWatch 126 received vs 55 deleted (2.3× redelivery), ConcurrentExecutions 4, Duration to 120s timeout; DLQ sent=0 (no loss yet). Fix = raise `blogSQS` visibility 30→720s (`infra/sqs.tf`, human apply). RFC → `docs/rfcs/STAB-3-sqs-visibility-timeout.md`. Status draft (accept = human-only).
- **STAB-4** (draft) — **schema.sql backfill + doc drift** (STAB-1 §Seq item 4 / P2-8, MODEL-9, MODEL-12, P2-1/2/3/4, P1-7). **Doc-only.** Prod introspection (06-05): 6 tables missing from `schema.sql`, `posts.rating` stale `(3,1)` vs prod `(3,2)`; `library_items` (V7) is a **ghost** (absent in prod) → backfill from `pg_dump`, not migrations/ORM. RFC → `docs/rfcs/STAB-4-schema-and-doc-drift.md`. Status draft (accept = human-only).

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
