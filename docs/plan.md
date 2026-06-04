# Plan

Active workspace tracker for cross-repo work. Each row carries `Scope / Order (if multi-repo) / Verification (local + prod smoke) / Rollback / Status`; RFC-backed entries collapse to a one-line pointer at `docs/rfcs/<id>-<slug>.md`. When a row finishes, drop it — `git log` and `docs/archive/done/YYYY-MM.md` are authoritative for history.

---

## Active

- **BUG-21** — `/profile` 평론 버킷: resetting a bucket color to "기본"(default) silently no-ops. `PATCH /api/buckets/{id}` with `{"color": null}` returns 200 but the color is never cleared (`bucket_service.update_bucket` treated `color=None` as "not provided"). A color could be set but never reset. Scope: backend only (`fix/BUG-21-bucket-color-reset`). Verification: pytest (new route-contract + real-engine set→clear regression tests) + the prod CDP click-through that surfaced it; prod smoke post-deploy. Rollback: revert the PR (1 commit). Post-deploy cleanup: smoke test account `우선순위` is stuck red on prod (clear via `{"color": null}` once the fix deploys). Status: fix implemented + tested, awaiting merge.

---

## Backlog

- **FEAT-genre-taxonomy** (draft) — genre branch-authoring v1 (2-tier single-parent tree, create + assign-parent only; seeded from prod `artists.genres`). RFC → `docs/rfcs/FEAT-genre-taxonomy.md`. v2+ (album↔genre linkage, multi-genre on write, cross-cutting filter, browse-by-genre view, rename/merge/delete) tracked in that RFC's Non-goals. Cross-repo (shared_db V14 → seed → backend API → contract → front; V12/V13 reserved by FEAT-music-search-recall). Not yet accepted.
- **FEAT-genre-artist-distribution** (draft) — `/profile` 통계 charts: genre + artist/listen distribution. Carved from `FEAT-member-dashboard` Step 4. RFC → `docs/rfcs/FEAT-genre-artist-distribution.md`. Depends on `FEAT-genre-taxonomy` (genre) + `spotify_play_events` (shipped, listen counts). Not yet scoped/accepted.
- **FEAT-multi-user-accounts** (draft) — user/profile model, public `/members/[handle]`, social graph; un-hides social stats. Carved from `FEAT-member-dashboard` Step 6. RFC → `docs/rfcs/FEAT-multi-user-accounts.md`. Largest follow-on; needs data + auth model. Not yet scoped/accepted.
- **FEAT-music-search-recall** (draft) — writer-facing music search recall re-assessment; goal Hit@5 ≥ 0.9 / Hit@1 ≥ 0.6 on a 30-query fixture covering multi-token / KO / common-word / typo / alias cases. RFC → `docs/rfcs/FEAT-music-search-recall.md`. Cross-repo (front IME → music fixture+gate → pg_trgm probe ✅ done 06-05 → shared_db V12 pg_trgm + GIN indexes + `SEARCH_USE_PG_TRGM` flag → shared_db V13 album/track aliases + worker MB extend → music query decomposition → music ?explain=1). Extension resolved: **pg_trgm** (pg_bigm/pg_search not installable on Neon PG17; pg_trgm works on Korean — #230). Brainstorm went through 3-agent critique (architect/reviewer/general-purpose) before draft — A3 promoted ahead of A2, §4 debug-storage reframed to V10 precedent (`spotify_play_events`). Not yet accepted.

---

## Later (트리거 대기)

_(none — FEAT-view-redesign trigger fired 2026-05-31, promoted to Active.)_

---

## Frozen (아이디어만, RFC 없음)

확장 기능 후보. 의향 생기면 그때 RFC 시작. 지금 아무것도 안 함.

- **FEAT-new-release-feed** (L) — EventBridge 주기 → 본인 review artist 의 최근 앨범 fetch → `artist_new_releases` → `/api/music/feed/new-releases` → 메인 카드
