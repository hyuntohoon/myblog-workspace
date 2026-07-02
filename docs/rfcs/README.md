# RFCs

Multi-step migrations, architectural changes, and any work that:

- spans 2+ repos
- needs more than one session to complete
- has reversibility / migration order concerns that don't fit in a `plan.md` row

…lives here as a long-form RFC. `plan.md` keeps a one-line pointer.

## RFC vs ADR

These two often get confused. They serve different purposes and have different lifecycles.

| | RFC (`docs/rfcs/`) | ADR (`docs/archive/decisions/`) |
|---|---|---|
| **Purpose** | Plan and execute future work | Record the outcome of a past decision |
| **Lifecycle** | Created → executed → archived to `docs/archive/done/rfcs/` | Created → permanent |
| **Tense** | "We will…" | "We decided…" |
| **Updates** | Live document; Status + steps update during execution | Append-only; if reversed, write a new ADR superseding the old |
| **Length** | Long — full migration steps, verification, rollback | Short — context, decision, consequences |

An RFC that involves a structural decision usually produces an ADR as its final step (e.g. ARCH-6 → ADR 0005). The ADR survives; the RFC moves to `done/`.

## When to write an RFC vs. just a `plan.md` row

| Use `plan.md` only | Write an RFC |
|--------------------|--------------|
| Single repo, < 1 day | 2+ repos OR multi-day |
| One PR | Multiple PRs with ordering constraint |
| Rollback is trivial (revert) | Rollback needs explicit steps |
| No structural decision | Introduces or changes a structural rule |

## File naming

`<PLAN_ID>-<short-kebab-desc>.md` — same plan ID as the `plan.md` row.

Example: `ARCH-6-shared-db-package.md` ↔ `plan.md` row `ARCH-6`.

## Status lifecycle

RFCs go through four states. Both the RFC's own `Status:` line and the matching `plan.md` row must reflect the same state.

| Status | Meaning | Transition trigger |
|--------|---------|--------------------|
| `draft` | Author writing or revising. Not yet ready for execution. | Author edits until they think it's executable as-is. |
| `accepted` | Reviewed and approved. Step 1 may begin. | Human says "accepted" explicitly. AI never self-promotes. |
| `in-progress (Step N)` | Step N is the next step to execute. (Not "currently running" — "next up".) | After a step's verification passes and the merge SHA is recorded, bump N. |
| `done` | All steps complete, ADR (if any) merged, file ready to archive. | Final step verification + cleanup pass complete. |

Once `done`, the RFC is moved to `docs/archive/done/rfcs/<PLAN_ID>-*.md`.

## Required sections

Every RFC must have:

1. **Status** — one of the four above. Single source of truth for progress.
2. **Goal** — one paragraph, no preamble. What's true after this is done?
3. **Non-goals** — what we explicitly will not do in this RFC. Prevents scope creep mid-execution.
4. **Current state** — concrete: file paths, function names, current behavior. No abstractions.
5. **Target state** — same concreteness as current state.
6. **Steps** — ordered, each step independently mergeable when possible. Each step has its own Verification block. Each step that's non-trivial to revert has its own Rollback block.
7. **Open questions** — any unresolved decision that blocks a step.
8. **Decisions log** — table of in-flight decisions made during execution, with date and step.

See `TEMPLATE.md` for a starting skeleton.

## How to give an RFC to Claude Code

These RFCs are written assuming Claude Code is the executor. Two usage patterns:

**Pattern A — full RFC, let Claude pick the next step:**
```
Read docs/rfcs/<PLAN_ID>-<slug>.md. Tell me the current Status,
then propose the next step's plan before touching code.
```

**Pattern B — pin to a specific step:**
```
Read docs/rfcs/<PLAN_ID>-<slug>.md. Execute Step 2 only.
Stop after Verification and report results.
```

Both patterns end the same way: Claude commits but does not push or merge.
Human runs verification commands or trusts Claude's verification output,
then says "ok push" / "ok merge" explicitly.

Workspace `CLAUDE.md` enforces one-step-per-session as a hard rule unless the RFC marks steps as parallel-safe.

## Updating the RFC during execution

When a step completes:

1. Bump the RFC `Status` line (e.g. `in-progress (Step 2)` → `in-progress (Step 3)`).
2. Add a one-liner under the completed step: `> ✅ Done <date>, SHA: <merge sha>`.
3. If a decision was made mid-step, log it in the Decisions log table.
4. Do **not** delete completed steps from the RFC — they are part of the migration's history. Only when the entire RFC is `done` does the file get archived to `docs/archive/done/rfcs/`.

## Index

In-flight RFCs only. Once `done`, an entry stays here for one cycle as a breadcrumb to the archive, then gets dropped — `git log` and `docs/archive/done/rfcs/` are authoritative for history.

- **STAB-1** (done 2026-06-06, **archived** — breadcrumb) — 시스템 안정화/하드닝 우산 RFC. 2026-06-05 아키텍처 리뷰를 코드에 재검증한 조사·우선순위·시퀀싱 (real issue 47건) + **category → section + review-tags** 모델 결정. 갈라진 구현 RFC **STAB-2..STAB-7 전부 완료·prod-live·archived** → STAB-1 종료, **확장 동결 해제**. 본문 → `docs/archive/done/rfcs/STAB-1-stabilization.md`.
- **FEAT-spotify-library-sync** (done 2026-06-08, **archived** — breadcrumb) — `review_buckets.kind='spotify_library'` 버킷이 주인장의 Spotify saved-albums Library 를 양방향 미러 (reqs 4/5/6). shared_db V15 + worker reconcile/Library client + backend sync/state endpoints + front 버킷 UI; 활성화 게이트 3개 적용, prod-verified (#288–#291). 본문 → `docs/archive/done/rfcs/FEAT-spotify-library-sync.md`.
- **FEAT-ai-editorial-critique** (draft) — AI editorial critic **Phase 0** thin slice: first code→LLM path + `POST /api/editorial/critique` running `docs/editorial/review-critique-method.md` over a draft + its `post_albums`-linked album facts (no schema change) → grounded Korean feedback + `[ ]`/`[source?]` markers + §4 checklist, **reconstruction/feedback only**. UI-less, proven by curl + golden-draft eval (critic must not hallucinate) before any frontend. Backend-only, 2 steps (local+eval → infra JWT route + contract). Caveats baked in: token-ceiling cost guard + manual-fire ($0-bias), narrow-not-deterministic fact-check, prompt single-source vs drift (OQ1). Fact-check pass / `/write` sidebar / persistence / planner / publish-gate = later RFCs. From the 2026-06-06 whole-project review (memory `project-ai-editorial-greenfield`).
- **FEAT-genre-system** (done 2026-06-13, **archived** — breadcrumb) — tier-0 장르 시스템: 12개 영어 어휘(K-Pop=아이돌 산업 범주, 다중부착) + **무인** 라벨링 파이프라인(Spotify 문자열 매핑 + iTunes UPC + LLM 폴백/중재 — 2026-06-12 7-소스 벤치마크로 선정), 트랙=앨범 상속+OST 예외, 공개 `/genres` 규정 페이지(정의문 DB 저장+인라인 편집), `/reviews` 실필터, `derive_subject_meta` 교체. shared_db = **V17** (V16 은 `album_research` 선점). 7 steps. **FEAT-genre-taxonomy (discarded 2026-06-12 → archive) 를 대체.**
- **FEAT-editor-buckit** (done 2026-06-18, **archived** — breadcrumb) — **editorial commissioning desk**: a `$0` `claude -p` pipeline turning review-bucket signal into *what to write next* (opposite funnel end from FEAT-ai-editorial-critique). All three stages prod-live: **Stage 0** dated Markdown idea report (`scripts/editor_buckit.py`), **Stage 1** the "오늘 밤 키우기" checkbox-gated 03:00 launchd nightly memo→review-draft job (`scripts/buckit_nightly.py`; claude has NO tools, script does all I/O; output contract revised 2026-06-19 skeleton→full draft), **Stage 2** the draft also lands as a `/write` 임시 저장함 **draft** (minted `$0` smoke JWT → `POST /api/posts {status:'draft'}`, grow-once via `post_id`+`prep_tonight`). Audit-hardened; a Neon pgbouncer read-only-leak was root-caused + fixed en route (`reference-neon-pooler-readonly-leak`). 본문 → `docs/archive/done/rfcs/FEAT-editor-buckit.md`; 요약 → `docs/archive/done/2026-06.md`.
- **FEAT-listening-history-import** (done 2026-06-23, **archived** — breadcrumb) — import the owner's Spotify **Extended Streaming History** (GDPR export, lifetime per-stream JSON: `ts` + `ms_played` + `spotify_track_uri`) into `spotify_stream_history` (shared_db V27) → true lifetime **play counts + listening time + per-era/per-year retrospective** (no Spotify API exposes counts/minutes). All 6 steps shipped + prod-verified same day; post-import primary "favorite" signal = lifetime-play, 좋아요 = secondary. 본문 → `docs/archive/done/2026-06.md`.
- **FEAT-multi-user-accounts** (draft) — user/profile 모델, public `/members/[handle]`, social graph. `FEAT-member-dashboard` Step 6에서 분리. 가장 큰 follow-on; data+auth 모델 필요. 미착수.
- **FEAT-blog-to-review-migration** — **Step 1 DONE + prod-live 2026-06-14** (front #153 / ws #344; prod smoke PASSED, 옛 `/blog/*` 전부 200→`/review/`, zero 404). `FEAT-home-redesign` Step 6 에서 분리. front-only: read route `git mv` → `/review/[slug]`, 모든 옛 `/blog/*` no-404 정적 stub, `/blog/category`→`/reviews` 흡수, 링크+rss+sitemap 일괄 교체. **남은 건 선택적 Step 2 (진짜 301 via CloudFront Function, owner-applied)뿐** → RFC 유지. → `FEAT-blog-to-review-migration.md`.
- **FEAT-public-bucket-multiuser** (**Scope A done + prod-live 2026-06-15**; Scope B 미착수) — "공개 버킷뷰어 + 멀티유저" 범위. **Scope A(공개 읽기전용 버킷뷰) 전체 출시·prod-verified**: A1(`is_public` 마이그레이션, shared_db #30)→A2+A5(공개 `/api/buckets/public` + `GET /api/buckets` JWT 게이트, be #69)→A3(프로필 🌐 공개토글, front #155)→A4(읽기전용 `/collection` 뷰어, front #156); v0.19 repin(be #71) + 테스트오염 수정(be #72). 아카이브 요약 → `docs/archive/done/2026-06.md`. **남은 건 Scope B(멀티유저 계정)뿐** → RFC 유지(`Status: Scope A done`). → `FEAT-public-bucket-multiuser.md`.
- **FEAT-pocket-buckit** (in-progress) — the canonical Buckit product + interaction definition: a selectable-design bottom **tray** over a **generalized-membership** bucket model (`review_bucket_items.item_type` ∈ album/track/review/playback/snapshot; V28–V31) + a single-owner server-minted playback-token model. All 6 planned steps **DONE + prod-live 2026-06-24**; kept in-progress as the home for the remaining **future kinds** (review / playback-queue / snapshot **front** surfaces — backend supports, no front yet). Design Atlas + configurator on claude.ai/design (project `cf932975`). → `FEAT-pocket-buckit.md`.
- **FEAT-pocket-buckit-workspace** (draft) — front-only follow-on to the shipped Pocket Buckit: turns the tray into a real **multi-bucket workspace** (several movable mini-drawers), adds an explicit **edit/arrange mode**, and stops the tray + profile from re-fetching the full bucket tree on every nav via a **lightweight tray read-model**. Does **not** add item kinds. → `FEAT-pocket-buckit-workspace.md`.
- **FEAT-bucket-identity** (in-progress) — the **compatibility / migration / integration** track for existing review buckets + `들을 것` + public collections, aligning them to the Pocket Buckit model. Direction A DONE 2026-06-16; Direction C subsumed + shipped via Pocket Buckit V31 (`들을 것` → `kind='to_listen'`); Direction B NEXT, D open. → `FEAT-bucket-identity.md`.
- **FEAT-genre-recommendation** (frozen — deferred) — the "**장르 기준 추천 평론**" genre-based related-review recommendation (shared sub-genre tags + `influenced_by`/`related` graph). Gated on **review volume**. 미착수. → `FEAT-genre-recommendation.md`.
- **FEAT-liked-tracks-workbench** (v1 SHIPPED — Steps 1–4 live + prod-verified 2026-06-22; Step open) — the `/profile` **분석 버킷** tab becomes a critic's "좋아요한 트랙" workbench: sortable/filterable track table + live analysis + per-track 담기 to a 평론 버킷 (reuses `/api/buckets`). Steps 1–3 (be #82, front #187) + Step 4 duration (shared_db #42/V26, be #84, front #192) shipped; Step 5 (unlike) DROPPED. → `FEAT-liked-tracks-workbench.md`.
- **ARCH-frontend-component-map** (accepted) — docs-only frontend component structure map (no refactor): two code-pinned artifacts — an LLM developer reference (real file paths, ownership, state/interaction/cache dependencies) + a human-readable route/feature/flow map. Verified 2026-07-02: routes-by-island table, domain ownership, and the **track-click verdict — no shared track-row component exists** (≥6 fragmented paths; only play funnels through the shared `requestPlayback` SDK layer, never the row UI). Includes a Component-map impact template for future RFCs. The shared track-click component is documented, NOT created. → `ARCH-frontend-component-map.md`.
- **RESEARCH-playback-product-architecture** (accepted) — docs-only decision research (not implementation): whether the current Spotify SDK/API integration supports a Spotify-like-but-simpler playback experience, or whether a separate custom playback RFC is necessary. Scoped to this project's flows (not a Spotify inventory). Separates confirmed capabilities / gaps (D28 blocks continuous position, not one-shot; no `track_id` on the snapshot → lyrics endpoint accepts `spotify_track_id` from the live read, server-side resolve) / verification (resolved 2026-07-02: position read is **client-side** `GET /v1/me/player`, mirroring `requestPlayback`'s existing call — rule #9 not engaged; remaining = one runtime probe on a live Premium session) / retain-vs-defer / recommendation: **no custom playback RFC** either way. → `RESEARCH-playback-product-architecture.md`.
- **ARCH-lyrics-normalization-model** (accepted) — docs-only (no schema preselection): how raw `lyric_plain` + raw `lyric_synced` (LRC) on `track_lyrics` normalize into **one** project-specific lyrics structure for FEAT-lyrics-viewer. Verified 2026-07-02 (prod probes): mixed = 91% of matched / plain-only = 9% / synced-only = 0 observed (defensive branch), V33 CHECK can force a synced-only row to store `lyric_plain=''` with text in `lyric_synced`, no normalizer exists (greenfield). One pure normalizer → one segment shape across plain-only/synced-only/mixed; **synced-only parsed to segments, never stripped to raw text**; **mixed derives from synced alone** (plain ≡ timestamp-stripped synced in 98%; ~2% mismatch → diagnostics, synced wins). Raw stays source-of-truth; read-time derived view. Future estimated sync / line restructure out of scope but not precluded. → `ARCH-lyrics-normalization-model.md`.
- **FEAT-lyrics-corpus** (draft) — a **private, single-owner, correctness-first lyrics corpus** on tracks already in our catalog. LRCLIB = only lyric-text source (plain + synced; bulk ~28.6 GiB dump for local historical backfill + API for increments); MusicBrainz = artist-identity/alias + recording/version **evidence only**; lyrics.ovh excluded. Lyrics stay **private** — never in any public API/page/search/shared response (`artists.aliases` + `album_research` privacy precedent). **Album name is never a hard match key**; remix/live/demo/edit/cover/remaster/rerecording **never silently merged** — weak/ambiguous parks in `review_required`/`ambiguous`/`not_found`/`no_lyrics` rather than mismatching (correctness ≫ coverage). The local dump batch evaluates **only tracks already in this DB**; a `matched` lyric is never silently replaced without stronger evidence; periodic reassessment can promote unresolved rows as coverage grows. Metrics beyond precision: coverage, review-required rate, unresolved/no-lyrics rate, version-conflict false-match count (=0 target), source-quality conflict rate. **Translation / slang-meme / interpretation / album-level analysis = later separate RFCs** (this one builds only the substrate). Backend/worker/shared_db + local batch; no frontend, no public API. From the 2026-07-01 lyrics-corpus feasibility research. → `FEAT-lyrics-corpus.md`.

Recently archived (2026-06): FEAT-home-redesign (editorial 2-lane home — writer strip + reader module stack + BNM hero + browse-genre teaser + by-the-numbers + `/canon` ≥4.0★, front-only #151; Step 6 shipped separately as FEAT-blog-to-review-migration #153/#344; done + archived 2026-06-14), STAB-1 (stabilization umbrella — investigation/sequencing + section model decision, done 2026-06-06 once STAB-2..7 all shipped), STAB-2 (P0 auth boundary, 5 steps, #255–#267 — fail-closed guard / edge_guard JWT / categories gate / music `/candidates` auth / invoke-domain throttle), STAB-5 (category→section + review tags, 6 steps, #276 — junk data lossless reset), STAB-6 (repo hygiene + S3 tfstate, #268), STAB-3 (blogSQS visibility 30→720s ≥ worker timeout, applied #256), STAB-7 (necessity-gated IAM least-privilege: P7-5 account-wide SQS-consume + P7-1 dead RDS grant removed + out-of-IaC documented, applied #257; Step 4/OQ2 observability deferred), STAB-4 (schema.sql backfill from prod pg_dump + architecture.md/sqs-doc drift fix, docs-only, #254), FEAT-music-search-recall (writer 음악 검색 recall 재평가 — Step 4 에서 목표 달성, pg_trgm Hit@5=Hit@1=1.000; Steps 1–4/6/7 출시·prod-live [decomposition + `?explain=1` 포함], Step 5 album/track aliases deferred; closed 2026-06-05, #243), FEAT-music-edge-cache (음악 read 경로 $0 캐싱 5스텝; Step 2 CloudFront 엣지는 Free-plan 제약으로 축소 — album-detail만 managed-cache, search/artists 제외; prod Miss→Hit ✅), FEAT-bucket-board-redesign (`/profile` 평론 버킷 cover-forward tiles + enriched detail slide-over + single-album delete, frontend-only, prod #84), FEAT-header-scroll-prefs (사이트 전역 헤더 스크롤 거동 3-모드 토글, frontend-only, prod #82), FEAT-member-dashboard (회원 대시보드 `/profile`, 5탭 vertical-slice, Steps 1–5 + D28–D31 follow-ups, cross-repo), FEAT-review-bucket-board (평론 버킷 보드, 5 steps end-to-end, prod 16/16), FEAT-design-system-measure (design token scale + content measure unify to 800px + break-out hero + daisyUI removal + writer.css split), FEAT-post-edit-delete-ui (published-post edit/delete UI + restore flow). (2026-05): FEAT-reviews-redesign (Pitchfork-style `/reviews` index + filter island + stars-only cards), FEAT-view-redesign (lowfreq article read page, 6 steps cross-repo), FEAT-writer-lowfreq-redesign (writer flow end-to-end, 6 steps cross-repo), BUG-11/12 (writer search filter), BUG-14 (MB hangul alias), BUG-15 (MB false-match cross-check), BUG-17 (alias_fill per-row UPDATE), BUG-18 (MBID uniqueness pre-check), BUG-19 (writer music search cross-expansion), FEAT-search-grid-fix, FEAT-writer-cleanup. Earlier: ARCH-6 (shared DB, ADR 0005), ARCH-11 (absorb publish, ADR 0006), ARCH-12 (contract-first OpenAPI, ADR 0007). All in `docs/archive/done/rfcs/`.
