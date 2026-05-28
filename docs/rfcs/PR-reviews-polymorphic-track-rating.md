# PR-reviews-polymorphic: per-track rating via post_reviews

- **Status**: draft
- **Owner**: TBD
- **Created**: 2026-05-28
- **Plan row**: `plan.md` → PR-reviews-polymorphic

---

## Goal

A published blog post about an album can carry an unlimited number of per-track ratings (0–5 in 0.5 steps, matching the album scale), persisted in `post_reviews` and rendered on the post page alongside the album rating. The legacy single-column `posts.rating` stays as the album-level score; `post_reviews` carries per-track scores keyed by `track_id`.

## Non-goals

- **Artist rating.** `review_subject` enum is `('album','track')` only. Adding `artist` requires the enum migration + a nullable `artist_id` column + a constraint update; out of scope here, deferred to a follow-up RFC.
- **Migrating `posts.rating` into `post_reviews`.** Keeping both: `posts.rating` = album-level (legacy + simple), `post_reviews` (subject='album') unused for now. Backfill / dual-source consolidation is a separate cleanup.
- **Review revisions / history.** A `(post_id, subject, track_id)` UPSERT semantics — no versioned audit trail. Deletions are hard deletes.
- **Per-track comments separate from notes.** `post_reviews.notes` is the single free-text field; no nested commentary structure.
- **Rating-only posts (no body).** The current writer flow always carries `body_mdx`; rating-only posts stay out of scope.

## Current state

- **Schema** (`docs/contracts/schema.sql:238-260`): `post_reviews` table + `review_subject` enum + indexes exist in the canonical DDL and the backend's `schema_v0.sql:115-133`. Migration status in Neon prod is **unverified** — needs a `\d post_reviews` check in Step 0.
- **ORM**: `myblog_shared_db/src/myblog_shared_db/models.py` declares `Post`, `Album`, `Track`, `Artist`, association tables, but **no `PostReview` mapper**. The package's `__init__.py` (`myblog_shared_db/src/myblog_shared_db/__init__.py`) exports `ReviewSubject` from `enums.py` but no model.
- **Backend API**: `myblog_backend/app/api/routes/` has `posts.py`, `categories.py`, `metrics.py`, `publish.py` — **no `reviews.py`**. No CRUD surface for `post_reviews`.
- **Frontend writer**: `myblog_front/src/components/writer/SubjectBlock.tsx` lets the author pick an album and rate it 0–5/0.5 via `score` (mapped onto `posts.rating` with `rating_scale=5`). There is **no track list, no per-track rating UI**. `runDBSearch` already fetches tracks (`data.tracks` from `/api/music/search/unified`) but the writer ignores them — they only appear in the search modal.
- **Frontend post view**: `myblog_front/src/components/writer/types.ts` defines `AlbumDetail` which carries `id, title, cover_url, release_date, artists` — no `tracks` field. The post detail render (`src/scripts/review/index.ts`, `src/components/post-detail/*`) has no per-track rating slot.
- **Roadmap memory**: previously stated "트랙·아티스트 평점 없음, post_reviews는 dead schema" (2026-05-25). **This RFC supersedes that for tracks.** Roadmap memory will be updated in Step 1.

## Target state

- **ORM**: `myblog_shared_db` v0.2.0 publishes a `PostReview` mapper bound to `post_reviews`, with FK relationships to `Post`, `Album`, `Track`. Each consumer service (`myblog_backend`, `myblog_worker`) bumps the pinned version.
- **Backend API** (`myblog_backend/app/api/routes/reviews.py`):
  - `GET /api/posts/{post_id}/reviews` → `{album: {rating, scale} | null, tracks: [{track_id, rating, scale, notes}]}`. Public, CloudFront-direct.
  - `PUT /api/posts/{post_id}/reviews/tracks/{track_id}` → upsert one track review. Body `{rating: number, scale: number=5, notes?: string}`. Cognito JWT via API Gateway.
  - `DELETE /api/posts/{post_id}/reviews/tracks/{track_id}` → delete one. Cognito JWT.
  - `POST /api/posts/{post_id}/reviews/tracks/batch` → batch upsert (max 200 tracks). Cognito JWT. Use this from the writer to commit all per-track ratings in a single round-trip on save.
- **Infra**: 3 new API Gateway routes added to `infra/apigateway.tf` (the GET goes through `GET /api/{proxy+}` already; the mutating routes need explicit JWT-authorized entries).
- **OpenAPI contract**: backend `openapi.json` carries `PostReviewTrack`, `PostReviewBundle`, `TrackReviewUpsert` schemas. Workspace merge regenerates `docs/contracts/openapi.json`. Frontend `pnpm generate:types` picks up `components['schemas']['PostReviewTrack']` etc.
- **Frontend writer** (`SubjectBlock.tsx` + new `TrackRatingList.tsx`): once an album is selected, fetch its tracks (`GET /api/music/albums/{id}`, which already returns the track list) and render a list of `[track title — rating slider (0–5, 0.5 step) — notes input]` rows. On save, the writer collects non-null ratings into the batch endpoint payload alongside the existing `updatePost`. Edits are loaded via `GET /api/posts/{post_id}/reviews` and merged into the same UI state.
- **Frontend post view**: post detail page (album review) renders a "트랙 평가" section listing tracks with their per-track score and notes.
- **Roadmap memory** `project-feature-roadmap` updated: line about `post_reviews` being dead schema replaced with "Step 1 (track ratings) shipped; artist rating deferred to a follow-up RFC."

## Steps

Each step is independently mergeable. Steps 2 and 5 cannot run in parallel with anything else because they're contract / type-gen turning points.

### Step 0 — verify prod schema state + decided migrations

Confirm `post_reviews` table + `review_subject` enum + the three indexes exist in Neon prod. They are in `schema_v0.sql` but never explicitly migration-tracked, so prod state is unknown. Then apply two decided migrations on top.

**Verification (current state)**:

```
psql "$DATABASE_URL" -c "\d post_reviews" \
  && psql "$DATABASE_URL" -c "select enum_range(null::review_subject);" \
  && psql "$DATABASE_URL" -c "select indexname from pg_indexes where tablename='post_reviews';"
```

**Migration A — partial UNIQUE on `(post_id, track_id)`** (decision 2026-05-28):

```sql
CREATE UNIQUE INDEX CONCURRENTLY uq_post_reviews_post_track
  ON post_reviews(post_id, track_id)
  WHERE track_id IS NOT NULL;
```

Partial 인덱스로 두는 이유: `subject='album'` row 는 `track_id IS NULL` 이라 일반 UNIQUE 는 안 됨. 같이 도입할 `subject='album'` 측 유일 제약은 본 RFC scope 밖이라 미적용.

**Migration B — FK `track_id` → `ON DELETE CASCADE`** (decision 2026-05-28):

```sql
ALTER TABLE post_reviews DROP CONSTRAINT post_reviews_track_id_fkey;
ALTER TABLE post_reviews
  ADD CONSTRAINT post_reviews_track_id_fkey
  FOREIGN KEY (track_id) REFERENCES tracks(id) ON DELETE CASCADE;
```

`chk_post_reviews_target` (album_id XOR track_id 보장) 와 충돌 방지: track 행 삭제 시 해당 트랙 평점 행도 함께 제거되므로 orphan row 가 남지 않음.

위 두 마이그레이션은 `docs/contracts/schema.sql` 과 `myblog_backend/.../schema_v0.sql` 양쪽에도 반영해서 다음 fresh DB 구축 시 재현되게 함.

**Rollback**:
- Migration A: `DROP INDEX uq_post_reviews_post_track;`
- Migration B: FK 를 다시 `ON DELETE SET NULL` 로 ALTER. 단 cascade 동작을 가정한 후속 PR 이 머지된 뒤라면 worker / writer 영향 재검증 필요.
- Table/enum 자체가 없으면: `schema_v0.sql:13-16,115-133` 을 forward-only 로 적용 (idempotent `IF NOT EXISTS`).

---

### Step 1 — add `PostReview` ORM model in `myblog_shared_db`

Add `PostReview` mapper to `myblog_shared_db/src/myblog_shared_db/models.py`, export from `__init__.py`, regenerate `_generated_schema.sql`, bump the package version to `v0.2.0`, tag the release.

**Verification**:

```
cd myblog_shared_db && pytest tests/test_schema_parity.py
```

(The parity test confirms the ORM produces DDL matching `docs/contracts/schema.sql`.)

**Rollback**: untag `v0.2.0`; consumers stay pinned to `v0.1.0`.

---

### Step 2 — backend: implement reviews routes + repository

In `myblog_backend`: bump the shared-db pin to `v0.2.0`. Add `app/repositories/review_repository.py` (SQLAlchemy ORM, mirrors `PostRepository` shape). Add `app/services/review_service.py`. Add `app/api/routes/reviews.py`. Wire DI in `app/di.py`. Mount the router in `app/main.py` under `/api/posts/{post_id}/reviews`. Pydantic schemas in `app/api/schemas.py`.

**Verification**:

```
cd myblog_backend && pytest tests/api/test_reviews.py -q
python scripts/export_openapi.py  # commit the regenerated openapi.json
```

New tests cover: empty-bundle GET, single-track PUT idempotency, DELETE, batch upsert with one invalid `track_id` returning 4xx without partial writes (transactional).

**Rollback**: revert the PR. No DB writes from previous step; the table was already empty.

---

### Step 3 — infra: API Gateway routes

Add three routes to `infra/apigateway.tf` mirroring the `posts_*` pattern:

- `aws_apigatewayv2_route.reviews_get` → `GET /api/posts/{post_id}/reviews` (no auth — already covered by `GET /api/{proxy+}` so this step may be a no-op; verify in plan)
- `aws_apigatewayv2_route.reviews_track_put` → `PUT /api/posts/{post_id}/reviews/tracks/{track_id}` (JWT)
- `aws_apigatewayv2_route.reviews_track_delete` → `DELETE /api/posts/{post_id}/reviews/tracks/{track_id}` (JWT)
- `aws_apigatewayv2_route.reviews_track_batch` → `POST /api/posts/{post_id}/reviews/tracks/batch` (JWT)

**Verification**:

```
cd infra && terraform plan -no-color -var "edge_secret=..."  # 3 or 4 to add, 0 to change other than known drift
```

Apply gated on human approval per Hard rule #6.

**Rollback**: `terraform destroy -target` (manual, human-driven only).

---

### Step 4 — contract merge + frontend types

After Step 2 lands and backend `openapi.json` is updated, the workspace merge regenerates `docs/contracts/openapi.json`. Frontend runs `pnpm generate:types`; `components['schemas']['PostReviewBundle']` etc. become available.

**Verification**:

```
cd myblog_front && pnpm generate:types && pnpm exec astro check
```

**Rollback**: re-run generation against the prior contract version.

---

### Step 5 — frontend writer: track rating list

Add `myblog_front/src/components/writer/TrackRatingList.tsx`. Wire it into `SubjectBlock.tsx` to render below the selected album. On mount-with-existing-post, call `GET /api/posts/{post_id}/reviews` to hydrate. On save, collect non-null entries into a single `POST .../tracks/batch` payload, alongside the existing `updatePost` call (two parallel requests, both must succeed before the success toast).

UX details out of RFC scope — handled by `frontend-design` skill per workspace convention.

**Verification**:

- `pnpm lint && pnpm exec astro check`
- Manual: open a draft, pick an album, rate 3 tracks, save, reload — ratings persist
- Prod smoke: `scripts/smoke.sh prod` plus a new track-rating round-trip step

**Rollback**: revert the PR. Server-side data remains untouched but unread by the UI.

---

### Step 6 — frontend post view: render per-track ratings

Add a "트랙 평가" section to the published post template. Fetches via the same `GET /api/posts/{post_id}/reviews`. Skipped silently when the bundle is empty.

**Verification**: visual check in prod; same smoke step from Step 5 covers the read path.

**Rollback**: revert the PR.

---

## Decisions log

| Date | Decision | Step |
|------|----------|------|
| 2026-05-28 | **rating_scale = 5** (0–5 / 0.5 step, 앨범 척도와 통일). Pydantic schema default `scale: int = 5`, Frontend slider `min=0 max=5 step=0.5`. | Step 2, Step 5 |
| 2026-05-28 | **`(post_id, track_id)` 유일 제약 = DB partial UNIQUE index** (`WHERE track_id IS NOT NULL`). 동시 요청에서도 row 1개 보장. UPSERT 는 `ON CONFLICT (post_id, track_id) WHERE track_id IS NOT NULL DO UPDATE`. | Step 0 (Migration A), Step 2 |
| 2026-05-28 | **Track 삭제 시 = FK `ON DELETE CASCADE`**. `chk_post_reviews_target` 위반 방지를 위해 worker 코드가 아닌 DB 측에서 처리. | Step 0 (Migration B) |
| 2026-05-28 | **Batch upsert = all-or-nothing (단일 트랜잭션)**. 하나라도 실패 시 전부 rollback, 4xx 응답에 첫 실패 사유 명시. Partial-success 응답 형식 미채택. | Step 2 |
