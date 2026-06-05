# Plan

Active workspace tracker for cross-repo work. Each row carries `Scope / Order (if multi-repo) / Verification (local + prod smoke) / Rollback / Status`; RFC-backed entries collapse to a one-line pointer at `docs/rfcs/<id>-<slug>.md`. When a row finishes, drop it — `git log` and `docs/archive/done/YYYY-MM.md` are authoritative for history.

---

## Active

- **FEAT-music-edge-cache** (code-complete, **awaiting human `terraform apply`**) — cache the music read path via $0 layers. All 5 steps merged 2026-06-05: Step 1 `Cache-Control` headers (music #39, prod-smoked ✅), Step 2 CloudFront edge behaviors (infra #246, **plan clean but NOT applied** — `x-cache: Miss` in prod until apply), Step 3 in-session client cache (front #92, live), Step 4 cover-img lazy/async (front #93, live), Step 5 Lambda TTLCache (music #40, live). RFC → `docs/rfcs/FEAT-music-edge-cache.md`. **Remaining: human runs `cd infra && terraform apply` (TF_VAR_edge_secret from Secrets Manager `myblog/backend`), then 2nd-hit `x-cache: Hit` smoke → drop this row + archive RFC.**

---

## Backlog

- **FEAT-genre-artist-distribution** (draft) — `/profile` 통계 charts: genre + artist/listen distribution. Carved from `FEAT-member-dashboard` Step 4. RFC → `docs/rfcs/FEAT-genre-artist-distribution.md`. Depends on `FEAT-genre-taxonomy` (genre, **deferred → Later**) + `spotify_play_events` (shipped, listen counts). Not yet scoped/accepted.
- **FEAT-multi-user-accounts** (draft) — user/profile model, public `/members/[handle]`, social graph; un-hides social stats. Carved from `FEAT-member-dashboard` Step 6. RFC → `docs/rfcs/FEAT-multi-user-accounts.md`. Largest follow-on; needs data + auth model. Not yet scoped/accepted.

---

## Later (트리거 대기)

- **FEAT-genre-taxonomy** (draft, **deferred 2026-06-05** — 주인장 추후 착수) — genre branch-authoring v1 (2-tier single-parent tree, create + assign-parent only; seeded from prod `artists.genres`). RFC → `docs/rfcs/FEAT-genre-taxonomy.md`. v2+ (album↔genre linkage, multi-genre on write, cross-cutting filter, browse-by-genre view, rename/merge/delete) in the RFC Non-goals. Cross-repo (shared_db **V13 / v0.12.0** → seed → backend API + infra → contract → front; numbering refreshed 06-05 after music-search-recall shipped V12-only). 착수 트리거 = 주인장 의향; UI 경로(OQ2) 는 그때 결정. RFC numbering 최신, Status draft. 의존 기능 `FEAT-genre-artist-distribution` 도 대기.

---

## Frozen (아이디어만, RFC 없음)

확장 기능 후보. 의향 생기면 그때 RFC 시작. 지금 아무것도 안 함.

- **FEAT-new-release-feed** (L) — EventBridge 주기 → 본인 review artist 의 최근 앨범 fetch → `artist_new_releases` → `/api/music/feed/new-releases` → 메인 카드
