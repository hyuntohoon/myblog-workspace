# Plan

Active workspace tracker for cross-repo work. Each row carries `Scope / Order (if multi-repo) / Verification (local + prod smoke) / Rollback / Status`; RFC-backed entries collapse to a one-line pointer at `docs/rfcs/<id>-<slug>.md`. When a row finishes, drop it — `git log` and `docs/archive/done/YYYY-MM.md` are authoritative for history.

---

## Active

_(empty — nothing in active development.)_

Last shipped: **FEAT-liked-tracks-workbench** v1 — 분석 버킷 redesigned to a "좋아요한 트랙(Liked Tracks) workbench" (hero + analysis [genre/artist + 좋아요/재생 toggle, decade, likes-flow] + facets + search/sort + list/card table + 평론 버킷에 담기); Steps 1–3 live + prod-smoked 2026-06-21 (backend #82 `album.genres` populate, front #187 workbench, **N+1 hotfix #83**), Steps 4 (duration) + 5 (unlike) deferred (see Frozen). Then **FEAT-genre-artist-distribution** (분석 버킷) + its post-merge hardening + the **FEAT-genre-autoheal on-demand 장르 채우기** button (merged into 분류하기) + the **FIX-uiux-audit-2026-06-21** front fix batch (all DONE + archived 2026-06-21), preceded by **FEAT-editor-buckit** (2026-06-18) and the 2026-06-15/16 batch — `home-redesign-v2`, the `ux-polish` sweep, `global-search`, `artist-page`, `genre-subgenres`/`-deepen`, `track-play-history`, and the `genre-autoheal` local fix. All 2026-06 completions are written up in `docs/archive/done/2026-06.md`; `git log` is authoritative.

---

## Backlog

> ✅ **Unblocked 2026-06-06** — STAB-1 P0 auth boundary + SQS fix + section model all shipped. These are scope-ready but still need owner go + RFC accept before promotion to Active.

- **FEAT-ai-editorial-critique** (draft) — **AI editorial critic, Phase 0 thin slice** (the product's defining feature — see 2026-06-06 whole-project review, memory `project-ai-editorial-greenfield`). LLM service layer + `POST /api/editorial/critique` that runs `docs/editorial/review-critique-method.md` over a draft + its already-linked album DB facts (`post_albums`, no schema change), returning grounded Korean feedback + `[ ]`/`[source?]` markers + §4 checklist — reconstruction/feedback only, never rewrites. UI-less; proven by curl + a golden-draft eval (critic must not hallucinate) before any frontend. Backend-only, 2 steps (Step 1 local + golden eval → Step 2 infra JWT route + contract). RFC → `docs/rfcs/FEAT-ai-editorial-critique.md`. **Caveats baked in: token-ceiling cost guard + manual-fire only ($0-bias owner); fact-check is narrow-not-deterministic (most honesty-line facts live outside the DB → `[source?]`); prompt single-source vs drift (OQ1).** Fact-check pass, `/write` sidebar, persistence, planner, publish-gate = later RFCs (non-goals). Status draft — needs owner accept before Active. **Open thread (from FEAT-editor-buckit, 2026-06-19):** on promotion, fold in the explicit 2-stage editorial pipeline (nightly full-draft → critique pass) + the research-grounded, tool-agnostic critique method §3.5 (`docs/editorial/review-critique-method.md` v2.6).
- **FEAT-genre-recommendation** (Frozen — gated on review volume) — the "**장르 기준 추천 평론**": related-review recommendation split out of FEAT-genre-subgenres (old Step 5, rescoped 2026-06-15). A "related reviews" block on `/review/{slug}` — reviews sharing a `post_genres` sub-genre + edge-linked sub-genres, ranked (shared-tag → edge-distance → recency). Substrate is LIVE + much richer post-FEAT-genre-deepen (genre_edges **2,064** + **1,230** genres / 4 tiers + `post_genres` filled by the `/write` picker); **deferred because nothing to rank until reviews are tagged (~1 today)** — same review-volume precondition as FEAT-ai-editorial-critique. Owner edge authoring (old Step 6, `POST/DELETE /api/genres/{id}/edges`) folded in here, lowest priority (edges are Claude-Code-driven). NB the genre-map *viz* (old Step 4) was revived into FEAT-genre-subgenres (review-volume-independent). RFC → `docs/rfcs/FEAT-genre-recommendation.md`.
- **FEAT-multi-user-accounts** (draft) — user/profile model, public `/members/[handle]`, social graph; un-hides social stats. Carved from `FEAT-member-dashboard` Step 6. RFC → `docs/rfcs/FEAT-multi-user-accounts.md`. Largest follow-on; needs data + auth model. Not yet scoped/accepted.
- **FEAT-blog-to-review-migration** — Step 1 (the `/blog → /review` prefix migration) **DONE + prod-live 2026-06-14** → `docs/archive/done/2026-06.md`. Only optional **Step 2** remains: a true HTTP 301 via the console-managed CloudFront Function `handler` (owner-applied infra; the static stubs already guarantee no-404, so 301 is SEO-only — add if inbound `/blog` links accumulate). RFC stays open for that → `docs/rfcs/FEAT-blog-to-review-migration.md`.
- **FEAT-bucket-identity** (Direction A DONE 2026-06-16 → `docs/archive/done/2026-06.md`; B/C remain) — strengthen "bucket" as the core workflow unit (save → research → listen → notes → review → link back). **B (next, front-mostly)**: replace the name-regex `crMeta` status with one **derived from real fields** (`research_status`/`already_reviewed`/`post_id`/`is_done`) so it stops lying on rename, join listened-state onto covers ("이미 들음 → 평론 가능"), add the reverse link review→bucket/research, maybe promote the board to the `/profile` landing tab. **C (deferred, L)**: merge `들을 것` (`album_to_listen_items`) into the bucket model = one save target. **D (not started)**: surface buckets as flexible PUBLIC collections (genre/artist/playlist 모음) on dedicated surfaces (from the home-redesign-v2 deferral). RFC → `docs/rfcs/FEAT-bucket-identity.md`.

---

## Later (트리거 대기)

_(empty — FEAT-genre-taxonomy discarded 2026-06-12, superseded by FEAT-genre-system, done + archived 2026-06-13)_

---

## Frozen (아이디어만, RFC 없음)

확장 기능 후보. 의향 생기면 그때 RFC 시작. 지금 아무것도 안 함.

- **FEAT-liked-tracks-workbench — Steps 4-5 (deferred)** — v1 (Steps 1-3) shipped 2026-06-21. Optional follow-ons, owner-go only: **Step 4** 길이/`duration_ms` (cross-repo shared_db migration → worker sync → backend field → front 길이 column + total-duration + length-sort); **Step 5** 좋아요 해제/unlike (new `DELETE /api/library/saved-tracks/{id}` → SQS → worker `DELETE /me/tracks`, mutates the real Spotify library, rule #9). Steps + verification spelled out in the RFC → `docs/rfcs/FEAT-liked-tracks-workbench.md`.
- **FEAT-genre-autoheal — cloud heal** (**only the cloud variant remains deferred**) — full laptop-independence for the daily genre backfill via a cloud iTunes-baseline heal, hung behind the album-ingest batch (worker EventBridge); the local launchd LLM pass stays the low→high / K-Pop-arbitration upgrade. **Blocker**: the S3 LLM step shells `claude -p` on the Max-subscription token (absent in Lambda) → a cloud pass would be iTunes-only + must use a DISTINCT partial marker so it never excludes the LLM pass. The **local** daily fix is DONE + LIVE (now **04:00**). **2026-06-21: the *on-demand* variant shipped** — a 분석 버킷 web button (folded into `분류하기`) → `genre_backfill_requests` queue (shared_db V25) → a 5-min local genre-heal poller runs the existing backfill (`claude -p` stays local; pull not push). Only the **cloud iTunes-only** pass is still open. → `docs/archive/done/2026-06.md`. Memory `reference-genre-backfill-stale-decisions-replay`, `reference-sqs-fanout-burst-pitfalls`.
- **Per-genre exemplar albums** — start inside `definition_md` markdown; structured linking only if a consumer needs it.
- **FEAT-new-release-feed** (L) — EventBridge 주기 → 본인 review artist 의 최근 앨범 fetch → `artist_new_releases` → `/api/music/feed/new-releases` → 메인 카드
