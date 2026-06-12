# Plan

Active workspace tracker for cross-repo work. Each row carries `Scope / Order (if multi-repo) / Verification (local + prod smoke) / Rollback / Status`; RFC-backed entries collapse to a one-line pointer at `docs/rfcs/<id>-<slug>.md`. When a row finishes, drop it — `git log` and `docs/archive/done/YYYY-MM.md` are authoritative for history.

---

## Active

_STAB-1 stabilization program complete (STAB-2..STAB-7 all merged, prod-live, archived 2026-06-06); product-expansion freeze lifted 2026-06-06. FEAT-spotify-library-sync DONE + LIVE 2026-06-08, archived 2026-06-09 (#288–#291). FEAT-album-catalog-ingest DONE + LIVE 2026-06-10 (ws #297/#298, worker #42/#43; rule applied, one-shot verified `enqueued=0` as designed) — `git log` + `docs/archive/done/rfcs/` authoritative._

- **FEAT-album-research-notes** (**accepted 2026-06-11**, in progress) — per-bucket opt-in auto AI research notes (scope modes, opus 4.8 + web search, `album_research` table, restart/refine, writer-GUI display in BucketBoard + `/write` gutter). Steps 1–2 done (V16 + dormant paid infra); **Step 3 done** ($0 local poller `scripts/research_poller.py`, prod-verified + launchd-automated #310); **Step 4 done** (backend triggers/routes/contract + apigateway POST route + api.gen.ts regen); **Step 5 done** (front writer GUI — BucketBoard mode control + per-item checkbox + cover badge/slide-over, `/write` margin rail, shared `ResearchNote` + no-dep markdown renderer; PR #138 myblog_front, prod-deployed + smoke-passed). **All 5 steps complete** — only the optional `'all'`-bucket→poller→*rendered*-note visual e2e (owner's subscription) + RFC archive (human-only) remain. RFC → `docs/rfcs/FEAT-album-research-notes.md`.
  - **Step 1 (shared_db) MERGED + PROD-APPLIED** — V16 `album_research` + bucket `research_mode`/`research_selected`, shared_db **v0.16.0** (PR #25). Applied to Neon **test AND prod** (`ep-broad-firefly`, 2026-06-11; album_research + both cols verified live).
  - **Step 2 (infra) MERGED + APPLIED** — researchSQS + DLQ, researchWorkerLambda (900s), `myblog/anthropic` secret container, research-worker IAM (#304). **`terraform apply` done + live-verified.** Concurrency cap moved off function-reserved (account limit is 10 → reservation hit the unreserved floor) onto the SQS ESM `maximum_concurrency=2` (#306 fix).
  - **EXECUTION BACKEND PIVOTED 2026-06-11** (owner — subscription cost, not API): primary executor = **local poller → headless `claude -p` ($0 on Max subscription, opus quality)**. Steps 1–2 infra (researchSQS/Lambda/`myblog/anthropic`) retained **dormant** as the cloud-autonomous paid upgrade — inert while the backend never feeds the queue + the key stays unset. **No Anthropic API key needed for the $0 path.**
  - **Next: Step 3 = local poller** (`scripts/research_poller.py`: poll `queued` → claim → `claude -p` w/ WebSearch/WebFetch → write `result_md`; 1 real measured run). Validatable standalone via a hand-inserted queued row — does not block on Step 4. → 4 backend (INSERT queued row on scope triggers, no SQS send; routes + API GW route + contract) → 5 front (BucketBoard + `/write` panels). OQ5 (poller host/schedule) decided at Step 3.
  - **Follow-up fix `fix/research-cover-badge-status` DONE + PROD-VERIFIED 2026-06-11** (ws #313, be #62, front #143) — Step-5 cover badge only lit a "조사 완료" dot after the note panel was opened (badge auto-fetched a note only when `research_mode != 'off'`); a done album looked un-researched on first paint. Fix seeds `research_status` per album into the bucket GET (+ item/bucket mutation responses) via new `ResearchService.status_map` (one batched query, mirrors `reviewed_album_ids`); front badge paints from the payload, note GET stays the on-open/live-poll source. Additive field. Merge order ws-contract → be → front (front deploy sync gate diffs api.gen.ts vs ws main). **Prod smoke**: `GET /api/buckets` 200, all 65 items carry `research_status` (`{None:39, done:26}`); the `off`-mode "Spotify 라이브러리" bucket's done albums (Blonde/BRAT/Swimming) now seed `done` — the exact bug condition, fixed. Front+backend deploys green. No infra/DB change.

---

## Backlog

> ✅ **Unblocked 2026-06-06** — STAB-1 P0 auth boundary + SQS fix + section model all shipped. These are scope-ready but still need owner go + RFC accept before promotion to Active.

- **FEAT-ai-editorial-critique** (draft) — **AI editorial critic, Phase 0 thin slice** (the product's defining feature — see 2026-06-06 whole-project review, memory `project-ai-editorial-greenfield`). LLM service layer + `POST /api/editorial/critique` that runs `docs/editorial/review-critique-method.md` over a draft + its already-linked album DB facts (`post_albums`, no schema change), returning grounded Korean feedback + `[ ]`/`[source?]` markers + §4 checklist — reconstruction/feedback only, never rewrites. UI-less; proven by curl + a golden-draft eval (critic must not hallucinate) before any frontend. Backend-only, 2 steps (Step 1 local + golden eval → Step 2 infra JWT route + contract). RFC → `docs/rfcs/FEAT-ai-editorial-critique.md`. **Caveats baked in: token-ceiling cost guard + manual-fire only ($0-bias owner); fact-check is narrow-not-deterministic (most honesty-line facts live outside the DB → `[source?]`); prompt single-source vs drift (OQ1).** Fact-check pass, `/write` sidebar, persistence, planner, publish-gate = later RFCs (non-goals). Status draft — needs owner accept before Active.
- **FEAT-genre-system** (draft) — tier-0 genre system: fixed 12-genre English vocabulary (K-Pop = idol-industry category; multi-attach), **zero-human** labeling pipeline (Spotify-string mapping + iTunes UPC anchor + LLM fallback/arbitration — chosen via a 7-source benchmark 2026-06-12; Deezer/Last.fm/Wikidata/MB rejected on evidence), tracks inherit album genres with OST/compilation per-song exceptions, public `/genres` map page with owner-editable DB definitions, `/reviews` real-genre filter, `derive_subject_meta` swap. shared_db migration = **V17** — **Step 1 DONE 2026-06-12** (V17 re-verified next-free, prod-applied before merge, shared_db PR #26 merged + tagged v0.17.0; contracts schema.sql synced incl. V16 backfill). Steps 2–7 remain. RFC → `docs/rfcs/FEAT-genre-system.md`. **Supersedes FEAT-genre-taxonomy (discarded 2026-06-12 → archive).** Sub-genre vocab + writer picker = separate future RFC; music-search filter rejected.
- **FEAT-genre-artist-distribution** (draft) — `/profile` 통계 charts: genre + artist/listen distribution. Carved from `FEAT-member-dashboard` Step 4. RFC → `docs/rfcs/FEAT-genre-artist-distribution.md`. Depends on `FEAT-genre-system` (tier-0 genre labels, in Backlog) + `spotify_play_events` (shipped, listen counts). Not yet scoped/accepted.
- **FEAT-multi-user-accounts** (draft) — user/profile model, public `/members/[handle]`, social graph; un-hides social stats. Carved from `FEAT-member-dashboard` Step 6. RFC → `docs/rfcs/FEAT-multi-user-accounts.md`. Largest follow-on; needs data + auth model. Not yet scoped/accepted.

---

## Later (트리거 대기)

_(empty — FEAT-genre-taxonomy discarded 2026-06-12, superseded by FEAT-genre-system in Backlog)_

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
