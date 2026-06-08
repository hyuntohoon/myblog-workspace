# RFCs

Multi-step migrations, architectural changes, and any work that:

- spans 2+ repos
- needs more than one session to complete
- has reversibility / migration order concerns that don't fit in a `plan.md` row

…lives here as a long-form RFC. `plan.md` keeps a one-line pointer.

## RFC vs ADR

These two often get confused. They serve different purposes and have different lifecycles.

| | RFC (`docs/rfcs/`) | ADR (`docs/decisions/`) |
|---|---|---|
| **Purpose** | Plan and execute future work | Record the outcome of a past decision |
| **Lifecycle** | Created → executed → archived to `docs/done/rfcs/` | Created → permanent |
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
- **FEAT-ai-editorial-critique** (draft) — AI editorial critic **Phase 0** thin slice: first code→LLM path + `POST /api/editorial/critique` running `docs/editorial/review-critique-method.md` over a draft + its `post_albums`-linked album facts (no schema change) → grounded Korean feedback + `[ ]`/`[source?]` markers + §4 checklist, **reconstruction/feedback only**. UI-less, proven by curl + golden-draft eval (critic must not hallucinate) before any frontend. Backend-only, 2 steps (local+eval → infra JWT route + contract). Caveats baked in: token-ceiling cost guard + manual-fire ($0-bias), narrow-not-deterministic fact-check, prompt single-source vs drift (OQ1). Fact-check pass / `/write` sidebar / persistence / planner / publish-gate = later RFCs. From the 2026-06-06 whole-project review (memory `project-ai-editorial-greenfield`).
- **FEAT-genre-taxonomy** (draft, **deferred**) — 장르 브랜치 저작 v1: 2단 단일부모 트리(상위→하위), 생성+부모지정만, prod `artists.genres` 시드. Cross-repo (shared_db 마이그레이션 → 시드 → backend API → contract → front 저작 UI). genres = **V14** (STAB-5 section 이 V13 선점 → 다음 연속 번호; RFC 본문 reconciled 2026-06-06, STAB-5 OQ4). (recall 은 **V12** pg_trgm 만 출시; V13 = STAB-5 section rename.) 앨범↔장르 연결·필터·통합뷰·관리는 v2+.
- **FEAT-genre-artist-distribution** (draft) — `/profile` 통계 charts: genre + artist/listen 분포. `FEAT-member-dashboard` Step 4에서 분리. `FEAT-genre-taxonomy`(genre) + `spotify_play_events`(listen) 의존. 미착수.
- **FEAT-multi-user-accounts** (draft) — user/profile 모델, public `/members/[handle]`, social graph. `FEAT-member-dashboard` Step 6에서 분리. 가장 큰 follow-on; data+auth 모델 필요. 미착수.

Recently archived (2026-06): STAB-1 (stabilization umbrella — investigation/sequencing + section model decision, done 2026-06-06 once STAB-2..7 all shipped), STAB-2 (P0 auth boundary, 5 steps, #255–#267 — fail-closed guard / edge_guard JWT / categories gate / music `/candidates` auth / invoke-domain throttle), STAB-5 (category→section + review tags, 6 steps, #276 — junk data lossless reset), STAB-6 (repo hygiene + S3 tfstate, #268), STAB-3 (blogSQS visibility 30→720s ≥ worker timeout, applied #256), STAB-7 (necessity-gated IAM least-privilege: P7-5 account-wide SQS-consume + P7-1 dead RDS grant removed + out-of-IaC documented, applied #257; Step 4/OQ2 observability deferred), STAB-4 (schema.sql backfill from prod pg_dump + architecture.md/sqs-doc drift fix, docs-only, #254), FEAT-music-search-recall (writer 음악 검색 recall 재평가 — Step 4 에서 목표 달성, pg_trgm Hit@5=Hit@1=1.000; Steps 1–4/6/7 출시·prod-live [decomposition + `?explain=1` 포함], Step 5 album/track aliases deferred; closed 2026-06-05, #243), FEAT-music-edge-cache (음악 read 경로 $0 캐싱 5스텝; Step 2 CloudFront 엣지는 Free-plan 제약으로 축소 — album-detail만 managed-cache, search/artists 제외; prod Miss→Hit ✅), FEAT-bucket-board-redesign (`/profile` 평론 버킷 cover-forward tiles + enriched detail slide-over + single-album delete, frontend-only, prod #84), FEAT-header-scroll-prefs (사이트 전역 헤더 스크롤 거동 3-모드 토글, frontend-only, prod #82), FEAT-member-dashboard (회원 대시보드 `/profile`, 5탭 vertical-slice, Steps 1–5 + D28–D31 follow-ups, cross-repo), FEAT-review-bucket-board (평론 버킷 보드, 5 steps end-to-end, prod 16/16), FEAT-design-system-measure (design token scale + content measure unify to 800px + break-out hero + daisyUI removal + writer.css split), FEAT-post-edit-delete-ui (published-post edit/delete UI + restore flow). (2026-05): FEAT-reviews-redesign (Pitchfork-style `/reviews` index + filter island + stars-only cards), FEAT-view-redesign (lowfreq article read page, 6 steps cross-repo), FEAT-writer-lowfreq-redesign (writer flow end-to-end, 6 steps cross-repo), BUG-11/12 (writer search filter), BUG-14 (MB hangul alias), BUG-15 (MB false-match cross-check), BUG-17 (alias_fill per-row UPDATE), BUG-18 (MBID uniqueness pre-check), BUG-19 (writer music search cross-expansion), FEAT-search-grid-fix, FEAT-writer-cleanup. Earlier: ARCH-6 (shared DB, ADR 0005), ARCH-11 (absorb publish, ADR 0006), ARCH-12 (contract-first OpenAPI, ADR 0007). All in `docs/archive/done/rfcs/`.
