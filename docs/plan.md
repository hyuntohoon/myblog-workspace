# Plan

Active workspace tracker for cross-repo work. Each row carries `Scope / Order (if multi-repo) / Verification (local + prod smoke) / Rollback / Status`; RFC-backed entries collapse to a one-line pointer at `docs/rfcs/<id>-<slug>.md`. When a row finishes, drop it — `git log` and `docs/archive/done/YYYY-MM.md` are authoritative for history.

---

## Active

- **STAB-1** (accepted) — **System stabilization & hardening (pre-expansion)**. Investigation/prioritization/sequencing of the 2026-06-05 arch review, re-verified against code (47 real issues across auth boundary / worker-SQS-EventBridge / shared_db-schema drift / repo hygiene / S3-CloudFront / search-observability / side-effecting GET / IAM), plus the final **category → section + review-tags** model decision. RFC → `docs/rfcs/STAB-1-stabilization.md`. **No code/Terraform/data/file changes in this RFC** — it ends at "evidence required before implementation"; fixes spawn scoped follow-up RFCs/BUG rows. **Top priority: product expansion is frozen behind this** (see Backlog/Later/Frozen — each item is blocked on its stabilization area; multi-user→P0 auth, genre→P2 schema, distribution/feed→worker observability). Caching is out of scope. Status **accepted** (2026-06-05, owner-approved).
- **STAB-2** (accepted) — **P0 auth boundary remediation** (STAB-1 §Seq item 1). Evidence re-verified **live 2026-06-05**: AUTH-3 `Bearer x` bypass + AUTH-9 unauth draft disclosure (2 drafts) confirmed on the raw invoke domain; AUTH-5 backend `require_cognito_token` fail-open (no `COGNITO_USER_POOL_ID`); P6-2 music `/candidates` answers unauth (no `ENV` key); no REGIONAL WAF (HTTP API can't take WAFv2); no stage throttle. RFC → `docs/rfcs/STAB-2-p0-auth-boundary.md`. 5 steps (fail-closed app guard → edge_guard JWT validation → gate/remove `POST /api/categories` → music `/candidates` auth → bound invoke domain). Cross-repo (backend + music + front + infra); infra steps need human apply. Status **accepted** (2026-06-05, owner-approved).
- **STAB-3** (accepted) — **blogSQS visibility ≥ worker timeout** (STAB-1 §Seq item 2 / P1-1). Evidence **live 2026-06-05**: visibility 30s ≪ worker 120s; CloudWatch 126 received vs 55 deleted (2.3× redelivery), ConcurrentExecutions 4, Duration to 120s timeout; DLQ sent=0 (no loss yet). Fix = raise `blogSQS` visibility 30→720s (`infra/sqs.tf`, human apply). RFC → `docs/rfcs/STAB-3-sqs-visibility-timeout.md`. Status **accepted** (2026-06-05, owner-approved).

- **STAB-5** (accepted) — **category → section taxonomy + review tags** (STAB-1 §Seq item 5 + §model decision; STAB-1 called it `FEAT-section-taxonomy`). Implements the ratified model: rename `category`→`section` (keep single FK), migration-seeded curated set, **no public create API**, review tags reuse the empty `tags`/`post_tags` M:N, reset junk data. Evidence (06-05): **all 13 prod posts + 11 MDX + 3 categories are junk** → clean reset, no data loss. Cross-repo (shared_db **V13** [next contiguous after V12; reconcile genre RFC's V13 claim — STAB-5 OQ4] → backend → writer → tags → contract → data/MDX reset). **Depends on STAB-2** (removes `POST /api/categories`); coordinate w/ STAB-4 (schema.sql). RFC → `docs/rfcs/STAB-5-section-taxonomy.md`. Step 6 destructive (human approval). Status **accepted** (2026-06-05, owner-approved).
- **STAB-6** (in-progress, Step 2 done) — **repo hygiene + remote Terraform backend** (STAB-1 §Seq item 6 / P3-1..3-8). Untrack `bundle.zip` (26M) + rewrite worker `.gitignore` transcript + `allure-results` (18) + music `.DS_Store`/`.idea` + front `.vscode`; migrate tfstate to S3+DynamoDB lock (plaintext Cognito secret in local-only state; workspace not in cloud-sync). RFC → `docs/rfcs/STAB-6-repo-hygiene-tfstate.md`. Per-repo branches (rule #1 hook only guards workspace); Step 5 needs human `terraform init -migrate-state`. Status **accepted** (2026-06-05, owner-approved).
- **STAB-7** (accepted, **necessity-gated**) — **IAM least-privilege + IaC drift-visibility + observability** (STAB-1 §Seq item 7 / P7-5/1/3, P4-2/7/8, P5). Recommended: drop musicApi's account-wide SQS-consume grant (P7-5; ESM empty, producer-only) + import plan-invisible WAF/CF-function/bucket-policy (P4 drift). Optional: dead RDS grant (P7-1). Signal-gated: observability (musicApi p99 ≈ 3.65s → likely no change). RFC → `docs/rfcs/STAB-7-iam-drift-observability.md`. Adopt only where harm-if-unfixed is nameable; "do P7-5 + cheap imports only" is valid. Status **accepted** (2026-06-05, owner-approved).

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
