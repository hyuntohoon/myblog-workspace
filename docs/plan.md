# Plan

Active workspace tracker for cross-repo work. Each row carries `Scope / Order (if multi-repo) / Verification (local + prod smoke) / Rollback / Status`; RFC-backed entries collapse to a one-line pointer at `docs/rfcs/<id>-<slug>.md`. When a row finishes, drop it — `git log` and `docs/archive/done/YYYY-MM.md` are authoritative for history.

---

## Active

_STAB-1 stabilization program complete (STAB-2..STAB-7 all merged, prod-live, archived 2026-06-06); product-expansion freeze lifted 2026-06-06. FEAT-spotify-library-sync DONE + LIVE 2026-06-08, archived 2026-06-09 (#288–#291). FEAT-album-catalog-ingest DONE + LIVE 2026-06-10 (ws #297/#298, worker #42/#43; rule applied, one-shot verified `enqueued=0` as designed) — `git log` + `docs/archive/done/rfcs/` authoritative. **FEAT-genre-system (tier-0) DONE + LIVE 2026-06-13, archived 2026-06-14** (ws #325/#326 / be #66 / front #145) — `docs/archive/done/` authoritative; only the Outliner view productionized, ego-view relationships + sub-genre vocab = separate **FEAT-genre-subgenres** (Frozen). **FEAT-album-research-notes DONE + LIVE 2026-06-11, archived 2026-06-14** (5 steps, $0 local-poller path; #25/#304/#310/#138) — `docs/archive/done/` authoritative. **FEAT-home-redesign DONE + LIVE 2026-06-14, archived** (editorial home front #151 + the `/blog → /review` migration #153/#344; prod smoke passed, zero 404s). **FEAT-public-bucket-multiuser Scope A (public bucket viewer, A1–A5) DONE + LIVE 2026-06-15, archived** (opt-in `is_public` → public `/collection` viewer + `GET /api/buckets` JWT-gated; shared_db #30/#31, be #69–#72, front #154–#156, ws #346–#351; Scope B/accounts not started) — `docs/archive/done/` authoritative._

---

## Backlog

> ✅ **Unblocked 2026-06-06** — STAB-1 P0 auth boundary + SQS fix + section model all shipped. These are scope-ready but still need owner go + RFC accept before promotion to Active.

- **FEAT-ai-editorial-critique** (draft) — **AI editorial critic, Phase 0 thin slice** (the product's defining feature — see 2026-06-06 whole-project review, memory `project-ai-editorial-greenfield`). LLM service layer + `POST /api/editorial/critique` that runs `docs/editorial/review-critique-method.md` over a draft + its already-linked album DB facts (`post_albums`, no schema change), returning grounded Korean feedback + `[ ]`/`[source?]` markers + §4 checklist — reconstruction/feedback only, never rewrites. UI-less; proven by curl + a golden-draft eval (critic must not hallucinate) before any frontend. Backend-only, 2 steps (Step 1 local + golden eval → Step 2 infra JWT route + contract). RFC → `docs/rfcs/FEAT-ai-editorial-critique.md`. **Caveats baked in: token-ceiling cost guard + manual-fire only ($0-bias owner); fact-check is narrow-not-deterministic (most honesty-line facts live outside the DB → `[source?]`); prompt single-source vs drift (OQ1).** Fact-check pass, `/write` sidebar, persistence, planner, publish-gate = later RFCs (non-goals). Status draft — needs owner accept before Active.
- **FEAT-genre-artist-distribution** (draft) — `/profile` 통계 charts: genre + artist/listen distribution. Carved from `FEAT-member-dashboard` Step 4. RFC → `docs/rfcs/FEAT-genre-artist-distribution.md`. Depends on `FEAT-genre-system` (tier-0 genre labels — **DONE + archived 2026-06-13**, so the genre data exists) + `spotify_play_events` (shipped, listen counts) → **data blocker resolved, now scopable**. Not yet scoped/accepted.
- **FEAT-reviews-home-genre-filter-removal** (idea — owner-stated, not scoped) — drop the `/reviews` home genre filter; the owner navigates genre via the `/profile` crate (FEAT-bucket-organize, DONE) instead. Small front-only change; ties into `FEAT-home-redesign`'s `/reviews` relationship OQ. Carved out when FEAT-bucket-organize completed so the intent isn't lost.
- **FEAT-multi-user-accounts** (draft) — user/profile model, public `/members/[handle]`, social graph; un-hides social stats. Carved from `FEAT-member-dashboard` Step 6. RFC → `docs/rfcs/FEAT-multi-user-accounts.md`. Largest follow-on; needs data + auth model. Not yet scoped/accepted.
- **FEAT-blog-to-review-migration** — **Step 1 DONE + prod-live 2026-06-14** (front #153 / ws #344; prod smoke PASSED, old `/blog/*` all 200 → `/review/`, zero 404s). Only optional **Step 2** remains: a true HTTP 301 via the console-managed CloudFront Function `handler` (owner-applied infra; the static stubs already guarantee no-404, so 301 is SEO-only — add if inbound `/blog` links accumulate). RFC stays open for that → `docs/rfcs/FEAT-blog-to-review-migration.md`.

---

## Later (트리거 대기)

_(empty — FEAT-genre-taxonomy discarded 2026-06-12, superseded by FEAT-genre-system, done + archived 2026-06-13)_

---

## Frozen (아이디어만, RFC 없음)

확장 기능 후보. 의향 생기면 그때 RFC 시작. 지금 아무것도 안 함.

- **FEAT-genre-subgenres** (M) — tier-1 sub-genre vocabulary + writer picker + `/genres` sub-node rendering. **Owner wants a dedicated brainstorm session before any RFC** (2026-06-12). Seeds captured from the 2026-06-12 session so the brainstorm doesn't start cold:
  - **Layer separation is already decided**: sub-genres are the *editorial* layer — attached at review time, stored per-post (`post_genres`, NOT `album_genres`; machine tier-0 and human tier-1 never share a store). Writer picker lives in `/write` SettingsPanel below section/review-tag pickers.
  - **Infra already ships in FEAT-genre-system**: `genres.parent_id` (2-tier tree), `POST /api/genres` (JWT create), `/genres` page renders the tree — sub-genres slot in with no migration and minimal front work.
  - **Open fork the brainstorm must settle — vocabulary growth**: (a) add-one-while-reviewing (Pitchfork/RYM organic; no empty genres) vs (b) pre-built seed 30–50 from the prod distinct-335 pool (recurring: 하이퍼팝 39, 네오 소울, 클라우드 랩, **시티 팝 — demoted from tier-0 at the 2026-06-12 vocabulary lock, prime Pop sub-genre candidate**…; rich `/genres` page from day 1, but many unused nodes). Note Pitchfork ships 9 genres with NO sub-genres at all — "do we need tier-1 at launch?" is itself a valid brainstorm question.
  - **Definition texts double as the shared rulebook** (human consistency + LLM prompt material) — same `definition_md` mechanism as tier-0.
  - Per-genre exemplar albums: start inside `definition_md` markdown; structured linking only if a consumer needs it.
  - No genre-relations/influence edges (re-confirmed; tree only).
- **FEAT-new-release-feed** (L) — EventBridge 주기 → 본인 review artist 의 최근 앨범 fetch → `artist_new_releases` → `/api/music/feed/new-releases` → 메인 카드
