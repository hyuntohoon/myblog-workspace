# FEAT-album-rerating: 재평가 — withdraw a finished 평가, re-listen, rate again

- **Status**: draft
- **Owner**: 박지훈
- **Created**: 2026-08-17
- **Plan row**: `plan.md` → FEAT-album-rerating
- **Depends on**: nothing. Builds on the shipped `FEAT-rating-smart-collections`
  (평가완료/평가전 static tiles, `planned_ratings`) and `FEAT-album-review-authoring`
  (`album_reviews` = one user-album state row, `rating` nullable since V50).

---

## Goal

An album the member has already rated can be sent back to "not yet rated" on purpose: one
click withdraws the star (and the one-liner), files the album under a 재평가 중 list on the
profile 평가 tab and under a static 다시 들어볼 앨범 tile in 마이버킷, and keeps the withdrawn
score privately so the withdrawal can be undone. Saving a new star for that album ends the
재평가 automatically — the album leaves the 재평가 중 list and the static tile in the same
write, with no separate cleanup step and no way for the two surfaces to disagree.

## Non-goals

- **No new bucket kind.** 다시 들어볼 앨범 is a client-synthesized static tile in `BucketBoard`
  (exactly how 평가완료/평가전 already work), NOT a `review_buckets` row. This is what makes
  "평가가 완료되면 스태틱 버킷에서도 삭제" true by construction rather than by a delete call that
  can be forgotten. `FEAT-rating-smart-collections`'s rejected Option C ("버킷 kind must not
  encode state") stays rejected.
- **No reuse of the existing `to_listen` ('들을 것') system bucket.** 재평가 is a rating-domain
  state, not a listening queue; folding it in would mix never-heard with heard-and-withdrawn.
- **`review_candidate` ("평론 쓸 것") is untouched** — no rename, no repurposing, no shared
  storage, per `FEAT-album-review-authoring`'s standing prohibition. A 재평가 does not clear or
  set it.
- **No track or artist reratings** — album-only, matching `album_reviews`'s scope.
- **No 평론(post) side effects.** Withdrawing a 평가 never touches a published or draft post,
  even when a post exists for that album.
- **No history.** One withdrawn score is kept per (user, album) so the current 재평가 can be
  undone. Reratings are not accumulated into a timeline, and a second 재평가 overwrites nothing
  because the first must have ended before it can start.
- **No notifications or reminders** about albums sitting in 재평가 중.

## Terminology

- **평가 (rating)** = public star (0.5–5.0 half-step) + optional ≤60-char one-liner, one row per
  (user, album) in `album_reviews`. 한국어 "리뷰"는 쓰지 않는다.
- **재평가 (rerating)** = this RFC's new state: "I withdrew my 평가 for this album and intend to
  rate it again after listening." Code identifier `rerating`; user-facing Korean 재평가.
- **평가 예정 (`planned_ratings`)** = "I intend to rate this, and never have." Disjoint from
  재평가 by definition — a 재평가 exists only for an album that HAD a rating.

## Verified current state (code evidence, this session, against `origin/main`)

- `album_reviews` (`myblog_shared_db/src/myblog_shared_db/models.py:1388`, class `AlbumRating`):
  `rating NUMERIC(2,1) NULL`, `comment TEXT NULL`, `review_candidate BOOL NOT NULL`,
  `UNIQUE(user_id, album_id)`, and three CHECKs — a comment requires a rating
  (`ck_album_reviews_comment_needs_rating`) and a row with neither a rating nor a mark may not
  exist (`ck_album_reviews_state_not_empty`). **Consequence for this RFC:** clearing the star of
  a row whose `review_candidate` is false necessarily DELETES the row. The 재평가 state therefore
  cannot live on that row — there is no row to live on.
- `RatingService.upsert` (`myblog_backend/app/services/rating_service.py:57`) is the single
  partial-update path for all three facets and already deletes a state that lost its last facet.
  Every public read filters `rating IS NOT NULL`.
- `PlannedRatingService` (`myblog_backend/app/services/planned_rating_service.py`) + table
  `planned_ratings` (V52) is the shipped precedent for a rating-domain state kept in its own
  table specifically to avoid touching `album_reviews`'s CHECK/upsert logic. Routes:
  `GET/PUT/DELETE /api/me/planned-ratings[/{album_id}]` (`app/api/routes/me.py:188-244`).
- Profile 평가 tab = `myblog_front/src/components/member/MemberProfile.tsx:376-430`, fed by
  `GET /api/members/{handle}` (`app/api/routes/members.py:54`). Rows render cover / title /
  stars / date / `RatingCommentCell`. **There is no 수정 button on these rows today** — only an
  inline "한 줄 감상 남기기" affordance that appears when the comment is empty.
- The only existing 수정 button for a rating is `AlbumRatingBlock.tsx:192` (album overlay), which
  opens an edit panel with 저장/취소 (`AlbumRatingBlock.tsx:196-233`).
- `BucketBoard.tsx` renders 평가완료 (`:3115`) and 평가전 (`:3127`) through `RatingSmartTile`
  (`:716-770`) — static tiles that are deliberately NOT part of the bucket tree and never call a
  bucket-item API. Drop handlers: `openRatedDrop` / `markRatedPlanned`.
- `bucketLifecycle.ts:26` `SYSTEM_BUCKET_KINDS = [playback_queue, spotify_library, to_listen]` —
  untouched by this RFC (no new kind).
- Latest migration on `origin/main`: `V53__add_tracks_disc_no.sql`.

## Target state

### Storage — `pending_reratings` (new table, V54)

```
id                uuid PK  default gen_random_uuid()
user_id           uuid NOT NULL  FK users(id)  ON DELETE CASCADE
album_id          uuid NOT NULL  FK albums(id) ON DELETE CASCADE
previous_rating   NUMERIC(2,1) NULL   -- the withdrawn star, for undo + the 이전 ★ hint
previous_comment  TEXT NULL           -- the withdrawn one-liner, restored together with the star
created_at        timestamptz NOT NULL default now()

UNIQUE (user_id, album_id)                    -- uq_pending_reratings_user_album
INDEX  (user_id, created_at DESC)             -- idx_pending_reratings_user_created
CHECK  (previous_comment IS NULL OR previous_rating IS NOT NULL)
                                              -- ck_pending_reratings_comment_needs_rating
                                              -- mirrors album_reviews: a withdrawn one-liner
                                              -- can only exist alongside a withdrawn star, so a
                                              -- restore can never violate the target's own CHECK
```

Own table, not a column on `album_reviews`, for the reason the current-state section proves:
the row being withdrawn from is usually deleted by the withdrawal itself. This also repeats
`planned_ratings`'s Option-B decision verbatim — zero blast radius on `album_reviews`'s CHECKs
and on `RatingService.upsert`.

### Lifecycle (the whole feature in four transitions)

| Trigger | Effect |
|---|---|
| **재평가 시작** — `POST /api/me/reratings/{album_id}` | Snapshot the caller's `rating`/`comment` into a `pending_reratings` row, then clear both facets through `RatingService.upsert` (row deleted unless `review_candidate` keeps it alive). Idempotent: already-pending → 204, no re-snapshot. |
| **재평가 취소** — `DELETE /api/me/reratings/{album_id}` | Restore `previous_rating`/`previous_comment` via the same `upsert`, delete the pending row. Idempotent. |
| **재평가 완료** — any `PUT /api/reviews/albums/{album_id}` that lands a non-null `rating` | `RatingService.upsert` deletes the caller's `pending_reratings` row in the SAME transaction. This is the single line that makes both surfaces (평가 탭 재평가 중, 다시 들어볼 앨범 타일) clear themselves — neither surface has its own removal code. |
| **album deleted** | `ON DELETE CASCADE`. |

Withdrawal reuses `RatingService.upsert` rather than writing to `album_reviews` directly, so the
"a state with no facet left does not exist" rule and the `review_candidate` interaction keep
being enforced in exactly one place.

### Visibility

- **The 재평가 중 list is public** (owner decision, this session): `GET /api/members/{handle}`
  gains a `reratings` array — `album_id`, `album_title`, `album_cover_url`, `artist_id`,
  `artist_name`, `created_at`. Anyone can see that a member is re-listening to an album.
- **`previous_rating` / `previous_comment` are author-only, always.** They are a withdrawn
  verdict; publishing them would contradict the feature's own premise that the star is gone.
  They appear only in `GET /api/me/reratings`, never in the public payload — the same
  public-read discipline `RatingService` already documents as rule 1.

### Surfaces

1. **Profile 평가 tab** (`MemberProfile.tsx`) — a 재평가 중 section above 평가한 앨범, rendered
   whenever the list is non-empty. Self view adds `이전 ★★★☆` and a `재평가 취소` action; other
   people's profiles show album + started-at only.
2. **Profile rating rows** — a new `수정` button per row (self only) opening an inline editor
   (half-star input + one-liner + 저장/취소) with `재평가` alongside. This button does not exist
   today; the owner's intended flow (프로필 평가 → 수정 → 재평가) requires creating it.
3. **Album overlay** (`AlbumRatingBlock.tsx`) — `재평가` inside the existing 수정 panel, next to
   저장/취소.
4. **마이버킷** (`BucketBoard.tsx`) — a third `RatingSmartTile`, 다시 들어볼 앨범, fed by
   `GET /api/me/reratings`. Dropping a rated album on it starts a 재평가; dropping an unrated
   album is refused with a toast (there is no 평가 to withdraw).

## Steps

### Step 1 — `pending_reratings` table (shared_db)

`migrations/V54__pending_reratings.sql` + `PendingRerating` model + the two schema mirrors
(`schema.sql`, `canonical_schema.sql` — diff BOTH, their equality is convention-only and has
drifted before). Applied to prod and to the Neon test branch (`/myblog/test-db`) in the same
session, before the backend pin lands.

**Verification**:
```
cd myblog_shared_db && PYTHONPATH=src pytest
psql "$DATABASE_URL" -c "\d pending_reratings"   # prod, after apply
```

**Rollback**: `DROP TABLE pending_reratings;` — no other table references it.

---

### Step 2 — backend state + routes

- `ReratingService` (`app/services/rerating_service.py`): `start` / `cancel` / `list_pending` /
  `list_pending_for_users`, all committing once, mirroring `PlannedRatingService`'s shape.
- `RatingService.upsert`: delete the caller's pending row when the applied change leaves a
  non-null `rating`. Same transaction, before the single commit.
- Routes on `app/api/routes/me.py`: `GET /api/me/reratings`, `POST /api/me/reratings/{album_id}`,
  `DELETE /api/me/reratings/{album_id}` (204s, idempotent).
- `GET /api/members/{handle}`: `reratings` array (public fields only).
- `infra/apigateway.tf`: the two new authenticated mutations get their routes — a protected route
  missing here 404s in prod while passing every local test.
- `shared_db` pin bumped to the Step 1 main SHA (tags are broken; pin by SHA).
- `openapi.json` regenerated and committed.

**Verification**:
```
cd myblog_backend && pytest                       # incl. new DB tests for all four transitions
terraform -chdir=infra plan                       # apigateway routes only, no drift
```

---

### Step 3 — contract propagation (workspace → front types)

`docs/contracts` merge first (workspace before front, per the standing order), then
`api.gen.ts` regenerated and committed in the front repo.

**Verification**:
```
cd myblog_front && pnpm exec astro check && pnpm lint
```

---

### Step 4 — profile surfaces (front)

재평가 중 section, per-row 수정 button + inline editor, 재평가 / 재평가 취소 actions,
`AlbumRatingBlock`'s 재평가 button. New `src/components/album/reratings.api.ts` mirroring
`plannedRatings.api.ts`.

**Verification**:
```
cd myblog_front && pnpm test && pnpm lint && pnpm exec astro check
```
plus a real-browser CDP clickthrough on prod: rate → 수정 → 재평가 → the row leaves 평가한 앨범
and appears under 재평가 중 → rate again → it leaves 재평가 중.

---

### Step 5 — 다시 들어볼 앨범 static tile (front)

Third `RatingSmartTile` in `BucketBoard`, drop-to-start, unrated-album drop refused.

**Verification**:
```
cd myblog_front && pnpm test && pnpm lint && pnpm exec astro check
```
plus a CDP drag-drop pass (synthetic `DragEvent` does not work on this app's React handlers —
the CDP Input drag tool is the only thing that does).

---

## Open questions

1. **Daily-cap interaction (blocks Step 2, decidable inside it).** Completing a 재평가 recreates
   a deleted `album_reviews` row, so it counts as a CREATE against the per-member daily rating
   cap, while editing an existing rating does not. Proposed: accept it (the cap exists to bound
   volume, and a 재평가 round-trip is a real new rating) and add no rerating-specific cap, since
   starting a 재평가 requires an existing rating and is therefore self-limiting.
2. **Ordering of the 재평가 중 section (Step 4).** Proposed: newest-first by `created_at`,
   independent of the 평가한 앨범 sort control below it.

## Decisions log

| Date | Decision | Step |
|------|----------|------|
| 2026-08-17 | 재평가 clears the star for real (no "hold" flag on a still-visible rating); the withdrawn star + one-liner are kept privately so 재평가 취소 can restore them. | 1 |
| 2026-08-17 | The 재평가 중 list is public on the profile; the withdrawn score behind it is author-only. | 2 |
| 2026-08-17 | `재평가` is reachable from BOTH the album overlay's 수정 panel and a NEW per-row 수정 button on the profile 평가 list. | 4 |
| 2026-08-17 | 다시 들어볼 앨범 is a client-synthesized static tile, not a `review_buckets` row — so 평가 완료 removes it from every surface in one write. | 5 |
