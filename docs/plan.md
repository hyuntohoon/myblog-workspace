# Plan

Active workspace tracker for cross-repo work. Each row carries `Scope / Order (if multi-repo) / Verification (local + prod smoke) / Rollback / Status`; RFC-backed entries collapse to a one-line pointer at `docs/rfcs/<id>-<slug>.md`. When a row finishes, drop it — `git log` and `docs/archive/done/YYYY-MM.md` are authoritative for history.

---

## Active

- **FEAT-spotify-library-sync** (draft — owner-requested 2026-06-08; RFC Status promotion still owner-only) — D11 follow-up: a NEW special bucket (`review_buckets.kind='spotify_library'`) in the BucketBoard that **explicitly** two-way mirrors the owner's Spotify saved-albums Library (`GET/PUT/DELETE /me/albums`, album-level, no playlists); per-album source (myblog_added/preexisting) + state, never deletes a pre-existing saved album. Implements original spec reqs **4/5/6** (1/2/3 already shipped #287). RFC → `docs/rfcs/FEAT-spotify-library-sync.md`. **Order**: Step 0 owner token re-bootstrap (`user-library-read`+`user-library-modify`) → shared_db V15 → worker → backend (contract) → front. **Migration: V15** (genre re-bumps to V16). All Spotify I/O worker-async (rule #9); first prod reconcile under DRY_RUN. **Status**: Step 1 (shared_db V15 + models) **merged** (shared_db #24, v0.15.0) + **V15 prod-applied to Neon main 2026-06-08** (kind default 'review' backfilled, no breakage). OQ2 resolved: full PULL, but pre-existing vs MyBlog-added must be visually distinguished. **Next**: Step 0 (owner re-bootstraps Spotify token w/ `user-library-read`+`user-library-modify`) → Step 2 (worker reconcile, pin shared_db v0.15.0, DRY_RUN-first prod).

_STAB-1 stabilization program complete (STAB-2..STAB-7 all merged, prod-live, archived 2026-06-06); product-expansion freeze lifted 2026-06-06._

---

## Backlog

> ✅ **Unblocked 2026-06-06** — STAB-1 P0 auth boundary + SQS fix + section model all shipped. These are scope-ready but still need owner go + RFC accept before promotion to Active.

- **FEAT-ai-editorial-critique** (draft) — **AI editorial critic, Phase 0 thin slice** (the product's defining feature — see 2026-06-06 whole-project review, memory `project-ai-editorial-greenfield`). LLM service layer + `POST /api/editorial/critique` that runs `docs/editorial/review-critique-method.md` over a draft + its already-linked album DB facts (`post_albums`, no schema change), returning grounded Korean feedback + `[ ]`/`[source?]` markers + §4 checklist — reconstruction/feedback only, never rewrites. UI-less; proven by curl + a golden-draft eval (critic must not hallucinate) before any frontend. Backend-only, 2 steps (Step 1 local + golden eval → Step 2 infra JWT route + contract). RFC → `docs/rfcs/FEAT-ai-editorial-critique.md`. **Caveats baked in: token-ceiling cost guard + manual-fire only ($0-bias owner); fact-check is narrow-not-deterministic (most honesty-line facts live outside the DB → `[source?]`); prompt single-source vs drift (OQ1).** Fact-check pass, `/write` sidebar, persistence, planner, publish-gate = later RFCs (non-goals). Status draft — needs owner accept before Active.
- **FEAT-genre-artist-distribution** (draft) — `/profile` 통계 charts: genre + artist/listen distribution. Carved from `FEAT-member-dashboard` Step 4. RFC → `docs/rfcs/FEAT-genre-artist-distribution.md`. Depends on `FEAT-genre-taxonomy` (genre, **deferred → Later**) + `spotify_play_events` (shipped, listen counts). Not yet scoped/accepted.
- **FEAT-multi-user-accounts** (draft) — user/profile model, public `/members/[handle]`, social graph; un-hides social stats. Carved from `FEAT-member-dashboard` Step 6. RFC → `docs/rfcs/FEAT-multi-user-accounts.md`. Largest follow-on; needs data + auth model. Not yet scoped/accepted.

---

## Later (트리거 대기)

- **FEAT-genre-taxonomy** (draft, **deferred 2026-06-05** — 주인장 추후 착수) — genre branch-authoring v1 (2-tier single-parent tree, create + assign-parent only; seeded from prod `artists.genres`). RFC → `docs/rfcs/FEAT-genre-taxonomy.md`. v2+ (album↔genre linkage, multi-genre on write, cross-cutting filter, browse-by-genre view, rename/merge/delete) in the RFC Non-goals. Cross-repo (shared_db migration → seed → backend API + infra → contract → front). **Migration number: was soft-reserved V14, now bumped to V15** — STAB-5 (sections) took V13; `FEAT-member-dashboard-realdata` claims V14 (`spotify_recent_tracks`, 2026-06-08) since genres are deferred and hold no migration in code → genres = next-free V15. Re-confirm next-free + version/pin at un-defer. 착수 트리거 = 주인장 의향; UI 경로(OQ2) 는 그때 결정. Status draft. 의존 기능 `FEAT-genre-artist-distribution` 도 대기.

---

## Frozen (아이디어만, RFC 없음)

확장 기능 후보. 의향 생기면 그때 RFC 시작. 지금 아무것도 안 함.

- **FEAT-new-release-feed** (L) — EventBridge 주기 → 본인 review artist 의 최근 앨범 fetch → `artist_new_releases` → `/api/music/feed/new-releases` → 메인 카드
