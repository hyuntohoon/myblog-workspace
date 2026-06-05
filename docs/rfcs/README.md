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

- **FEAT-music-edge-cache** (accepted) — 음악 read 경로(검색·앨범상세·커버) 캐싱, $0 레이어만: CloudFront `/api/music/{albums,search,artists}/*` 엣지 캐시 + `Cache-Control` 헤더 + 세션 클라이언트 캐시 + 커버 img lazy/async. TTL-only(수 분), 외부 캐시 스토어·능동 무효화 없음. Cross-repo 5스텝 (music 헤더 → infra → front 캐시 → front 커버 → Lambda TTLCache).
- **FEAT-genre-taxonomy** (draft) — 장르 브랜치 저작 v1: 2단 단일부모 트리(상위→하위), 생성+부모지정만, prod `artists.genres` 시드. Cross-repo (shared_db V14 → 시드 → backend API → contract → front 저작 UI; V12/V13 = FEAT-music-search-recall). 앨범↔장르 연결·필터·통합뷰·관리는 v2+.
- **FEAT-music-search-recall** (draft) — writer 음악 검색 recall 재평가, 목표 Hit@5 ≥ 0.9 / Hit@1 ≥ 0.6. 매칭레이어 우선(pg_trgm — A1 PoC done) + alias 커버리지. Cross-repo (front IME → fixture+gate → shared_db V12 pg_trgm → V13 aliases → music decomposition → ?explain=1).
- **FEAT-genre-artist-distribution** (draft) — `/profile` 통계 charts: genre + artist/listen 분포. `FEAT-member-dashboard` Step 4에서 분리. `FEAT-genre-taxonomy`(genre) + `spotify_play_events`(listen) 의존. 미착수.
- **FEAT-multi-user-accounts** (draft) — user/profile 모델, public `/members/[handle]`, social graph. `FEAT-member-dashboard` Step 6에서 분리. 가장 큰 follow-on; data+auth 모델 필요. 미착수.

Recently archived (2026-06): FEAT-bucket-board-redesign (`/profile` 평론 버킷 cover-forward tiles + enriched detail slide-over + single-album delete, frontend-only, prod #84), FEAT-header-scroll-prefs (사이트 전역 헤더 스크롤 거동 3-모드 토글, frontend-only, prod #82), FEAT-member-dashboard (회원 대시보드 `/profile`, 5탭 vertical-slice, Steps 1–5 + D28–D31 follow-ups, cross-repo), FEAT-review-bucket-board (평론 버킷 보드, 5 steps end-to-end, prod 16/16), FEAT-design-system-measure (design token scale + content measure unify to 800px + break-out hero + daisyUI removal + writer.css split), FEAT-post-edit-delete-ui (published-post edit/delete UI + restore flow). (2026-05): FEAT-reviews-redesign (Pitchfork-style `/reviews` index + filter island + stars-only cards), FEAT-view-redesign (lowfreq article read page, 6 steps cross-repo), FEAT-writer-lowfreq-redesign (writer flow end-to-end, 6 steps cross-repo), BUG-11/12 (writer search filter), BUG-14 (MB hangul alias), BUG-15 (MB false-match cross-check), BUG-17 (alias_fill per-row UPDATE), BUG-18 (MBID uniqueness pre-check), BUG-19 (writer music search cross-expansion), FEAT-search-grid-fix, FEAT-writer-cleanup. Earlier: ARCH-6 (shared DB, ADR 0005), ARCH-11 (absorb publish, ADR 0006), ARCH-12 (contract-first OpenAPI, ADR 0007). All in `docs/archive/done/rfcs/`.
