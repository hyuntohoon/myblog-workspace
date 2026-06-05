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

- **STAB-1** (accepted, **Active — top priority**) — 시스템 안정화/하드닝 (확장 착수 전). 2026-06-05 아키텍처 리뷰를 코드에 재검증한 조사·우선순위·시퀀싱 문서 (auth 경계 / worker-SQS-EventBridge / shared_db-schema drift / repo hygiene / S3-CloudFront / search-observability / side-effecting GET / IAM, 총 real issue 47건) + 최종 **category → section + review-tags** 모델 결정. 이 RFC 자체는 코드/Terraform/데이터/파일 무수정 — "구현 전 필요 증거"까지만; 수정은 후속 RFC/BUG 로. 모든 확장 기능은 이 뒤에 동결. 캐싱은 범위 외. **후속 구현 RFC: STAB-2/3/4 (증거는 2026-06-05 live 재검증).**
- **STAB-2** (accepted) — STAB-1 §Seq item 1 구현: **P0 auth 경계 수정**. raw invoke 도메인에서 `Bearer x` 우회(AUTH-3)·미인증 draft 노출(AUTH-9, 2건)·백엔드 fail-open(AUTH-5)·뮤직 `/candidates` 미인증(P6-2) live 확인. 5스텝 (fail-closed app guard → edge_guard JWT 검증 → `POST /api/categories` 게이트/제거 → 뮤직 `/candidates` 인증 → invoke 도메인 제한). cross-repo (backend+music+front+infra), infra 스텝은 human apply. WAFv2 는 HTTP API 에 부착 불가(correction).
- **STAB-3** (accepted) — STAB-1 §Seq item 2 구현: **blogSQS visibility ≥ worker timeout** (P1-1). 30s ≪ 120s; CloudWatch 재전달 live 확인(126 received vs 55 deleted, ConcurrentExecutions 4) — 단 DLQ sent=0 (아직 유실 없음). 수정 = visibility 30→720s (`infra/sqs.tf`, human apply). worker 코드 무변경(idempotent).
- **STAB-4** (**done** 2026-06-05, archive pending) — STAB-1 §Seq item 4 구현: **schema.sql 백필 + 문서 drift** (P2-8/MODEL-12, P2-1/2/3/4, P1-7). **문서 전용.** prod introspection: 6개 테이블 누락·`posts.rating` (3,1)→실제 (3,2)·`library_items`(V7) 는 prod 부재 ghost → 백필 소스는 migration/ORM 이 아니라 `pg_dump`. `genres` 부재 → V13 free.
- **STAB-5** (accepted) — STAB-1 §Seq item 5 + §model decision 구현: **category → section + review tags** (STAB-1 이 `FEAT-section-taxonomy` 로 예고). category→`section` rename(단일 FK 유지)·migration 시드 큐레이션 set·**public create API 없음**·review tags 는 빈 `tags`/`post_tags` 재사용·junk 리셋. 증거: prod 13 posts + 11 MDX + 3 categories **전부 junk** → 무손실 리셋. cross-repo (shared_db **V13** [V12 다음 연속; 단 deferred genre RFC 도 V13 주장 → STAB-5 OQ4 에서 조정] → backend → writer → tags → contract → data/MDX 리셋). **STAB-2 의존** + STAB-4 조정. Step 6 파괴적(사람 승인).
- **STAB-6** (in-progress, Step 2 done) — STAB-1 §Seq item 6 구현: **repo hygiene + remote tfstate backend** (P3-1..3-8). `bundle.zip`(26M)·worker `.gitignore` 트랜스크립트·`allure-results`(18)·music `.DS_Store`/`.idea`·front `.vscode` untrack; tfstate → S3+DynamoDB lock (로컬 전용 state 에 Cognito secret 평문). repo별 브랜치; Step 5 는 사람이 `terraform init -migrate-state`.
- **STAB-7** (accepted, **necessity-gated**) — STAB-1 §Seq item 7 구현: **IAM 최소권한 + IaC drift 가시성 + 관측성** (P7-5/1/3, P4-2/7/8, P5). 권장: musicApi account-wide SQS-consume 제거(P7-5; ESM 비어있음) + WAF/CF-function/bucket-policy import(P4 drift). 선택: dead RDS grant(P7-1). signal-gated: 관측성(p99 ≈ 3.65s → 변경 없음 유력). harm-if-unfixed 명확한 것만 채택.
- **FEAT-genre-taxonomy** (draft, **deferred**) — 장르 브랜치 저작 v1: 2단 단일부모 트리(상위→하위), 생성+부모지정만, prod `artists.genres` 시드. Cross-repo (shared_db 마이그레이션 → 시드 → backend API → contract → front 저작 UI). RFC 본문은 genres=**V13** 으로 확정해 두었으나, **STAB-5(section)가 active 라 먼저 V13 을 선점** → genre 는 un-defer 시 V14/next-free 로 재지정 필요(STAB-5 OQ4). (recall 은 **V12 만** 출시; V13 aliases 는 deferred.) 앨범↔장르 연결·필터·통합뷰·관리는 v2+.
- **FEAT-music-search-recall** (draft) — writer 음악 검색 recall 재평가, 목표 Hit@5 ≥ 0.9 / Hit@1 ≥ 0.6. 매칭레이어 우선(pg_trgm — A1 PoC done) + alias 커버리지. Cross-repo (front IME → fixture+gate → shared_db V12 pg_trgm → V13 aliases → music decomposition → ?explain=1).
- **FEAT-genre-artist-distribution** (draft) — `/profile` 통계 charts: genre + artist/listen 분포. `FEAT-member-dashboard` Step 4에서 분리. `FEAT-genre-taxonomy`(genre) + `spotify_play_events`(listen) 의존. 미착수.
- **FEAT-multi-user-accounts** (draft) — user/profile 모델, public `/members/[handle]`, social graph. `FEAT-member-dashboard` Step 6에서 분리. 가장 큰 follow-on; data+auth 모델 필요. 미착수.

Recently archived (2026-06): FEAT-music-edge-cache (음악 read 경로 $0 캐싱 5스텝; Step 2 CloudFront 엣지는 Free-plan 제약으로 축소 — album-detail만 managed-cache, search/artists 제외; prod Miss→Hit ✅), FEAT-bucket-board-redesign (`/profile` 평론 버킷 cover-forward tiles + enriched detail slide-over + single-album delete, frontend-only, prod #84), FEAT-header-scroll-prefs (사이트 전역 헤더 스크롤 거동 3-모드 토글, frontend-only, prod #82), FEAT-member-dashboard (회원 대시보드 `/profile`, 5탭 vertical-slice, Steps 1–5 + D28–D31 follow-ups, cross-repo), FEAT-review-bucket-board (평론 버킷 보드, 5 steps end-to-end, prod 16/16), FEAT-design-system-measure (design token scale + content measure unify to 800px + break-out hero + daisyUI removal + writer.css split), FEAT-post-edit-delete-ui (published-post edit/delete UI + restore flow). (2026-05): FEAT-reviews-redesign (Pitchfork-style `/reviews` index + filter island + stars-only cards), FEAT-view-redesign (lowfreq article read page, 6 steps cross-repo), FEAT-writer-lowfreq-redesign (writer flow end-to-end, 6 steps cross-repo), BUG-11/12 (writer search filter), BUG-14 (MB hangul alias), BUG-15 (MB false-match cross-check), BUG-17 (alias_fill per-row UPDATE), BUG-18 (MBID uniqueness pre-check), BUG-19 (writer music search cross-expansion), FEAT-search-grid-fix, FEAT-writer-cleanup. Earlier: ARCH-6 (shared DB, ADR 0005), ARCH-11 (absorb publish, ADR 0006), ARCH-12 (contract-first OpenAPI, ADR 0007). All in `docs/archive/done/rfcs/`.
