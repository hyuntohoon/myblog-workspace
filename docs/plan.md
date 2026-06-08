# Plan

Active workspace tracker for cross-repo work. Each row carries `Scope / Order (if multi-repo) / Verification (local + prod smoke) / Rollback / Status`; RFC-backed entries collapse to a one-line pointer at `docs/rfcs/<id>-<slug>.md`. When a row finishes, drop it — `git log` and `docs/archive/done/YYYY-MM.md` are authoritative for history.

---

## Active

_(none)_ — STAB-1 stabilization program complete (STAB-2..STAB-7 all merged, prod-live, archived 2026-06-06). **Product-expansion freeze lifted.** No work is promoted to Active until the owner picks the next target from Backlog/Later/Frozen.

---

## Backlog

> ✅ **Unblocked 2026-06-06** — STAB-1 P0 auth boundary + SQS fix + section model all shipped. These are scope-ready but still need owner go + RFC accept before promotion to Active.

- **FEAT-ai-editorial-critique** (draft) — **AI editorial critic, Phase 0 thin slice** (the product's defining feature — see 2026-06-06 whole-project review, memory `project-ai-editorial-greenfield`). LLM service layer + `POST /api/editorial/critique` that runs `docs/editorial/review-critique-method.md` over a draft + its already-linked album DB facts (`post_albums`, no schema change), returning grounded Korean feedback + `[ ]`/`[source?]` markers + §4 checklist — reconstruction/feedback only, never rewrites. UI-less; proven by curl + a golden-draft eval (critic must not hallucinate) before any frontend. Backend-only, 2 steps (Step 1 local + golden eval → Step 2 infra JWT route + contract). RFC → `docs/rfcs/FEAT-ai-editorial-critique.md`. **Caveats baked in: token-ceiling cost guard + manual-fire only ($0-bias owner); fact-check is narrow-not-deterministic (most honesty-line facts live outside the DB → `[source?]`); prompt single-source vs drift (OQ1).** Fact-check pass, `/write` sidebar, persistence, planner, publish-gate = later RFCs (non-goals). Status draft — needs owner accept before Active.
- **FEAT-genre-artist-distribution** (draft) — `/profile` 통계 charts: genre + artist/listen distribution. Carved from `FEAT-member-dashboard` Step 4. RFC → `docs/rfcs/FEAT-genre-artist-distribution.md`. Depends on `FEAT-genre-taxonomy` (genre, **deferred → Later**) + `spotify_play_events` (shipped, listen counts). Not yet scoped/accepted.
- **FEAT-multi-user-accounts** (draft) — user/profile model, public `/members/[handle]`, social graph; un-hides social stats. Carved from `FEAT-member-dashboard` Step 6. RFC → `docs/rfcs/FEAT-multi-user-accounts.md`. Largest follow-on; needs data + auth model. Not yet scoped/accepted.
- **CHORE-front-copy-cleanup** (ready, scoped 2026-06-08) — site-wide copy cleanup, follow-up to #110/#111 (decorative prose already stripped from home, `/reviews`, header, `/profile` member surfaces, writer "비평가의 픽"). Remaining `myblog_front` spots are all category-A descriptive/explanatory copy to shorten or remove; functional labels (buttons, tabs, stat labels, section titles, errors, aria) stay. Single repo / one PR / revert-trivial → no RFC. Scope:
  - `writer/CommandPalette.tsx` — ~6 empty/status sentences → short ("DB에 결과가 없습니다. Spotify로 검색해보세요." → "DB에 결과 없음"; "Spotify에서 검색하고 DB 동기화를 시작합니다…" → "Spotify 싱크 중…"; "앨범 동기화가 아직 완료되지 않았습니다. 잠시 후 다시 선택해주세요." → "앨범을 다시 선택해주세요"; idle "…에서 작품을 검색하세요" → "작품 검색"; "이 트랙의 앨범 정보가 없습니다." → "앨범 정보 없음").
  - `member/AddAlbumModal.tsx` — same 3 search-status sentences (83/104/121) → short, drop "(DB 동기화 백그라운드 진행 중)" parenthetical.
  - `writer/SubjectHero.tsx` — empty prompt "평론할 작품을 선택하세요" → "작품 선택".
  - `writer/BodyArea.tsx` — placeholder "본문을 시작하세요…" → "본문…"; `writer/PreviewView.tsx` — "본문이 비어 있습니다." → "본문 없음".
  - `writer/ArtistDetail.tsx` — "데이터를 가져올 수 없습니다." → "데이터 로드 실패"; "장르 미분류" → "미분류".
  - `writer/WriterApp.tsx` — subtitle placeholder "부제 또는 한 줄 요약" → "부제"; "발행 조건이 충족되지 않았습니다. (작품과 본문이 필요합니다)" → "작품과 본문이 필요합니다"; publish toast "발행 완료! 사이트 반영까지 약 3–5분 — /blog 에서 확인하세요." → shorten **AND fix the dead `/blog` link → `/reviews`** (blog index removed in #109 — correctness, not just copy).
  - `drafts.astro` — error/empty sentences (load-fail, "로그인 상태를 확인해주세요.", "임시저장된 글이 없습니다", the JS empty-state variants) → bare labels; delete-warning "이 작업은 되돌릴 수 없습니다. 보관함에서도 복구할 수 없습니다. 관련 버킷 항목도 함께 삭제됩니다." → "되돌릴 수 없습니다".
  - `member/SpotifyIntegrationTab.tsx` — kicker "이 연동이 제공하는 것" → "기능"; "연동 상태를 불러오지 못했습니다" → "상태 로드 실패".
  - `search-bar.astro` — placeholder "Search artists, albums, tracks (DB first)" → "작품 검색…".
  - `review-grid.astro` — default title `'Latest Reviews'` → `'최신 리뷰'`; ⚠️ this component was orphaned by the #109 home rewrite — confirm it's still referenced before editing, else delete it instead.
  - **Owner decision**: English kickers "LISTENING STATS" (`member/StatsTab.tsx`) + "SPOTIFY" (`SpotifyIntegrationTab`) — keep as brand flourish or localize/drop? Default keep.
  Verification: `pnpm lint` + `astro check` + build clean; headless render of `/write` `/drafts` `/profile` with fixtures; grep `dist/` for removed strings = 0; prod smoke post-deploy. Rollback: revert PR. Status: ready (needs owner go).

---

## Later (트리거 대기)

- **FEAT-genre-taxonomy** (draft, **deferred 2026-06-05** — 주인장 추후 착수) — genre branch-authoring v1 (2-tier single-parent tree, create + assign-parent only; seeded from prod `artists.genres`). RFC → `docs/rfcs/FEAT-genre-taxonomy.md`. v2+ (album↔genre linkage, multi-genre on write, cross-cutting filter, browse-by-genre view, rename/merge/delete) in the RFC Non-goals. Cross-repo (shared_db migration → seed → backend API + infra → contract → front). **Migration number: V14** — STAB-5 (sections) took V13; genres = next-free V14, RFC body fully reconciled 2026-06-06 (STAB-5 OQ4). Re-confirm next-free + version/pin at un-defer. 착수 트리거 = 주인장 의향; UI 경로(OQ2) 는 그때 결정. Status draft. 의존 기능 `FEAT-genre-artist-distribution` 도 대기.

---

## Frozen (아이디어만, RFC 없음)

확장 기능 후보. 의향 생기면 그때 RFC 시작. 지금 아무것도 안 함.

- **FEAT-new-release-feed** (L) — EventBridge 주기 → 본인 review artist 의 최근 앨범 fetch → `artist_new_releases` → `/api/music/feed/new-releases` → 메인 카드
