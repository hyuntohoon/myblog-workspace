# Plan

Active workspace tracker for cross-repo work. Each row carries `Scope / Order (if multi-repo) / Verification (local + prod smoke) / Rollback / Status`; RFC-backed entries collapse to a one-line pointer at `docs/rfcs/<id>-<slug>.md`. When a row finishes, drop it — `git log` and `docs/archive/done/YYYY-MM.md` are authoritative for history.

---

## Active

_STAB-1 stabilization program complete (STAB-2..STAB-7 all merged, prod-live, archived 2026-06-06); product-expansion freeze lifted 2026-06-06. FEAT-spotify-library-sync DONE + LIVE 2026-06-08, archived 2026-06-09 (#288–#291). FEAT-album-catalog-ingest DONE + LIVE 2026-06-10 (ws #297/#298, worker #42/#43; rule applied, one-shot verified `enqueued=0` as designed) — `git log` + `docs/archive/done/rfcs/` authoritative._

- **FEAT-album-research-notes** (**accepted 2026-06-11**, in progress) — per-bucket opt-in auto AI research notes (scope modes, opus 4.8 + web search, `album_research` table, restart/refine, writer-GUI display in BucketBoard + `/write` gutter). Steps 1–2 done (V16 + dormant paid infra); **Step 3 done** ($0 local poller `scripts/research_poller.py`, prod-verified + launchd-automated #310); **Step 4 done** (backend triggers/routes/contract + apigateway POST route + api.gen.ts regen). Next = Step 5 (writer GUI). RFC → `docs/rfcs/FEAT-album-research-notes.md`.
  - **Step 1 (shared_db) MERGED + PROD-APPLIED** — V16 `album_research` + bucket `research_mode`/`research_selected`, shared_db **v0.16.0** (PR #25). Applied to Neon **test AND prod** (`ep-broad-firefly`, 2026-06-11; album_research + both cols verified live).
  - **Step 2 (infra) MERGED + APPLIED** — researchSQS + DLQ, researchWorkerLambda (900s), `myblog/anthropic` secret container, research-worker IAM (#304). **`terraform apply` done + live-verified.** Concurrency cap moved off function-reserved (account limit is 10 → reservation hit the unreserved floor) onto the SQS ESM `maximum_concurrency=2` (#306 fix).
  - **EXECUTION BACKEND PIVOTED 2026-06-11** (owner — subscription cost, not API): primary executor = **local poller → headless `claude -p` ($0 on Max subscription, opus quality)**. Steps 1–2 infra (researchSQS/Lambda/`myblog/anthropic`) retained **dormant** as the cloud-autonomous paid upgrade — inert while the backend never feeds the queue + the key stays unset. **No Anthropic API key needed for the $0 path.**
  - **Next: Step 3 = local poller** (`scripts/research_poller.py`: poll `queued` → claim → `claude -p` w/ WebSearch/WebFetch → write `result_md`; 1 real measured run). Validatable standalone via a hand-inserted queued row — does not block on Step 4. → 4 backend (INSERT queued row on scope triggers, no SQS send; routes + API GW route + contract) → 5 front (BucketBoard + `/write` panels). OQ5 (poller host/schedule) decided at Step 3.

---

## Backlog

> ✅ **Unblocked 2026-06-06** — STAB-1 P0 auth boundary + SQS fix + section model all shipped. These are scope-ready but still need owner go + RFC accept before promotion to Active.

- **FEAT-ai-editorial-critique** (draft) — **AI editorial critic, Phase 0 thin slice** (the product's defining feature — see 2026-06-06 whole-project review, memory `project-ai-editorial-greenfield`). LLM service layer + `POST /api/editorial/critique` that runs `docs/editorial/review-critique-method.md` over a draft + its already-linked album DB facts (`post_albums`, no schema change), returning grounded Korean feedback + `[ ]`/`[source?]` markers + §4 checklist — reconstruction/feedback only, never rewrites. UI-less; proven by curl + a golden-draft eval (critic must not hallucinate) before any frontend. Backend-only, 2 steps (Step 1 local + golden eval → Step 2 infra JWT route + contract). RFC → `docs/rfcs/FEAT-ai-editorial-critique.md`. **Caveats baked in: token-ceiling cost guard + manual-fire only ($0-bias owner); fact-check is narrow-not-deterministic (most honesty-line facts live outside the DB → `[source?]`); prompt single-source vs drift (OQ1).** Fact-check pass, `/write` sidebar, persistence, planner, publish-gate = later RFCs (non-goals). Status draft — needs owner accept before Active.
- **FEAT-genre-artist-distribution** (draft) — `/profile` 통계 charts: genre + artist/listen distribution. Carved from `FEAT-member-dashboard` Step 4. RFC → `docs/rfcs/FEAT-genre-artist-distribution.md`. Depends on `FEAT-genre-taxonomy` (genre, **deferred → Later**) + `spotify_play_events` (shipped, listen counts). Not yet scoped/accepted.
- **FEAT-multi-user-accounts** (draft) — user/profile model, public `/members/[handle]`, social graph; un-hides social stats. Carved from `FEAT-member-dashboard` Step 6. RFC → `docs/rfcs/FEAT-multi-user-accounts.md`. Largest follow-on; needs data + auth model. Not yet scoped/accepted.

---

## Later (트리거 대기)

- **FEAT-genre-taxonomy** (draft, **deferred 2026-06-05** — 주인장 추후 착수) — genre branch-authoring v1 (2-tier single-parent tree, create + assign-parent only; seeded from prod `artists.genres`). RFC → `docs/rfcs/FEAT-genre-taxonomy.md`. v2+ (album↔genre linkage, multi-genre on write, cross-cutting filter, browse-by-genre view, rename/merge/delete) in the RFC Non-goals. Cross-repo (shared_db migration → seed → backend API + infra → contract → front). **Migration number: now bumped to V16** — STAB-5 (sections) took V13; `FEAT-member-dashboard-realdata` took V14 (`spotify_recent_tracks`); `FEAT-spotify-library-sync` took V15 (`spotify_library_sync`, shared_db v0.15.0, prod-applied 2026-06-08) → genres = next-free V16. Re-confirm next-free + version/pin at un-defer. 착수 트리거 = 주인장 의향; UI 경로(OQ2) 는 그때 결정. Status draft. 의존 기능 `FEAT-genre-artist-distribution` 도 대기.

---

## Frozen (아이디어만, RFC 없음)

확장 기능 후보. 의향 생기면 그때 RFC 시작. 지금 아무것도 안 함.

- **FEAT-new-release-feed** (L) — EventBridge 주기 → 본인 review artist 의 최근 앨범 fetch → `artist_new_releases` → `/api/music/feed/new-releases` → 메인 카드
