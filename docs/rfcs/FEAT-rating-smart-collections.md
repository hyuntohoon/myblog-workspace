# FEAT-rating-smart-collections: 평가 완료 / 평가 예정 — two derived rating-domain collections

- **Status**: draft
- **Owner**: TBD
- **Created**: 2026-08-10
- **Plan row**: `plan.md` → FEAT-rating-smart-collections
- **Depends on**: `docs/rfcs/ARCH-buckit-navigation-shell.md` Step 1 (`BucketDetailShell`'s
  smart-bucket-like empty slot) **only if** the owner decides these two collections surface as
  nav-tree-adjacent entries rather than a standalone page (Unresolved owner decision 1). No other
  dependency on either sibling RFC.
- **Sibling RFC of `FEAT-album-review-authoring`, not a continuation of it.** That RFC (accepted
  2026-07-31, Steps 1–2 shipped) defined and shipped `album_reviews`'s current shape — `rating`
  (nullable), `comment` (≤60 char), `review_candidate` (private "will write a 평론" mark) — and
  explicitly, by name, forbade exactly the collision this RFC's title invites: *"Never rename or
  repurpose `review_candidate` as 평가 예정"* (that RFC's terminology section). This RFC does not
  reopen `FEAT-album-review-authoring`'s Steps 3–5 (AI distillation, unified entry) and does not touch
  `review_candidate`'s meaning or column.

---

## Goal

Two non-manual, derived collections exist in the rating domain, both distinct from every other
"album+user" state the product already has:

- **평가 완료** ("ratings I've completed") — a *view*, not new storage: every album the caller has
  publicly rated, derived read-only from the existing `album_reviews` rows where `rating IS NOT NULL`.
  No new table, no new column, no `review_buckets` row ever created by viewing or acting on this list.
- **평가 예정** ("albums I plan to rate") — a **new private per-(user, album) state**: "I intend to give
  this a star rating eventually." Strictly distinct in storage and in UI from public ratings,
  `review_candidate` (which means "will write a 평론," an editorial concept, not a rating-intent
  concept), and manual bucket membership (which is a curation/organization concept, not a rating-intent
  one). Idempotent mark/unmark, bulk retrieval with no N+1.

## Non-goals

- **`review_candidate`/"평론 쓸 것" is untouched** — no rename, no repurposing, no shared storage with
  the new 평가 예정 flag, per the explicit prior-RFC prohibition quoted above.
- **`FEAT-album-review-authoring`'s remaining Steps 3–5** (AI distillation trial, unified write entry,
  general AI opening) — unrelated scope, not reopened, not blocked by this RFC either direction.
- **Manual bucket structure, bucket lifecycle tags (담음→조사 중→작성 중→완료), or bucket names as
  signal** — per that RFC's own hard rule 3-3 ("버킷 이름은 이름표일 뿐이다"), reused here: this RFC
  does not read bucket membership or bucket names as evidence of rating-intent, and 평가 예정 does not
  become a bucket-name convention.
- **Track or artist ratings** — album-only, matching the existing `album_reviews` scope.
- **A public 평가 예정 surface.** Per this RFC's own privacy invariant below, 평가 예정 is
  author-only, always — no public profile section, no public API field, ever.
- **Changing the public 평가한 앨범 profile feed's existing shape** (`MemberProfile.tsx`, `GET
  /api/members/{handle}`) — 평가 완료 reuses it as-is; this RFC does not add fields to the public
  response.
- **Notifications, reminders, or any "you haven't rated this yet" nudge tied to 평가 예정.** Marking
  and viewing only.

## Domain terminology and invariants (carried in, restated for precision)

- **평가 (rating)** = public star (0.5–5.0 half-step) + optional ≤60-char one-liner. One row per
  (user, album) in `album_reviews`. 한국어 "리뷰"는 절대 쓰지 않는다.
- **평론 (review)** = long-form editorial content, editor-permission only. Unrelated table (`posts`).
- **`review_candidate`** = 평론 쓸 것 — a private boolean on the *same* `album_reviews` row, meaning
  "I intend to write a 평론 about this," nothing to do with star ratings.
- **평가 완료** (this RFC) = the existing rating rows, filtered to `rating IS NOT NULL`, presented as a
  named list. Not a new state.
- **평가 예정** (this RFC) = a new state meaning "intend to rate," decided below to be either a field, an
  association, or a dedicated entity — **not yet fixed**, see Target architecture and the decision gate.
- **Invariant carried from `FEAT-album-review-authoring`**: "사용자-앨범 상태는 하나" (one user-album
  relationship state) was that RFC's organizing principle for `rating`/`comment`/`review_candidate`
  living on one row. This RFC's Target architecture section evaluates whether 평가 예정 extends that
  same principle (a fourth facet on the same row) or breaks from it (a separate entity) — see the
  decision gate; this document does not presume the answer.

## Verified current state (code evidence, this session)

### `album_reviews` — the exact current shape

`myblog_shared_db/src/myblog_shared_db/models.py:1388-1446`, class `AlbumRating`
(`__tablename__ = "album_reviews"` — table name kept unchanged by prior-RFC decision, internal Python
class name already renamed):

```
id            uuid PK
user_id       uuid FK users(id) ON DELETE CASCADE, NOT NULL
album_id      uuid FK albums(id) ON DELETE CASCADE, NOT NULL
rating        NUMERIC(2,1), nullable
comment       TEXT, nullable
review_candidate  BOOLEAN NOT NULL DEFAULT false
created_at    timestamptz NOT NULL default now()
updated_at    timestamptz NOT NULL default now()
```

Constraints (`__table_args__`, same file):
- `uq_album_reviews_user_album` — UNIQUE (user_id, album_id). One row per member per album, period.
- `ck_album_reviews_rating_halfstep` — `rating IS NULL OR (0.5 ≤ rating ≤ 5.0 AND rating % 0.5 = 0)`.
- `ck_album_reviews_comment_needs_rating` — `comment IS NULL OR rating IS NOT NULL`.
- **`ck_album_reviews_state_not_empty` — `rating IS NOT NULL OR review_candidate`.** The service layer
  deletes the row entirely once its last facet clears (both `rating` and `review_candidate` false/null)
  — this is the DB-level backstop against a ghost row with nothing set. **This constraint is load-
  bearing for the decision gate below**: any new facet added to this same row must be added to this
  constraint's OR-list, or a row holding *only* the new facet (nothing else) becomes uninsertable /
  gets silently deleted by the existing "clear when empty" service logic. This is not a blocker, but it
  is a concrete, non-zero cost of the "extend the same row" option, not a free reuse.
- `idx_album_reviews_album_id`, `idx_album_reviews_user_created`, and a **partial** index
  `idx_album_reviews_user_candidate` on `(user_id) WHERE review_candidate` — the exact precedent shape
  (`user_id`, partial-`WHERE`) a 평가 예정 index would follow if it lands on this same table.

### No existing collision — `review_candidate` is confirmed editorial-only, nothing else exists for rating-intent

Grepped across `myblog_backend`, `myblog_music`, `myblog_shared_db`, `myblog_front`: no field, column,
bucket `kind`, or flag anywhere in the codebase currently means "intend to rate this album" other than
what this RFC proposes to add. `review_candidate`'s own docstring/comment (`models.py:1436-1437`) reads
*"Private (RFC C6): never leaves the server except to the author... a promise"* — describing an
editorial-candidate promise, not a rating-intent one. No bucket `kind` resembling `to_rate` exists (the
three system kinds today are `spotify_library`, `to_listen`, `playback_queue`). The collision this RFC's
own title risks is real only at the *naming* level (평가 예정 vs. review_candidate's Korean gloss
"평론 쓸 것" are easy to conflate in prose), not at the code level — nothing today needs renaming or
disambiguating; the new work is additive.

### `GET /api/members/{handle}` — confirmed unpaginated, confirmed rating-only

`myblog_backend/app/api/routes/members.py:53-83` (`get_member`) calls `svc.member_profile(db, handle)`
→ `rating_service.py:215-227`, ordered `AlbumRating.created_at.desc()` — **no LIMIT/OFFSET, no
pagination param on the route or the service call.** The response (`MemberProfileResponse.reviews`,
`MemberRatingResponse`) casts `rating=float(r.rating)` **non-optionally**, meaning the service's own
query already excludes `rating IS NULL` rows (a comment-only or candidate-only row could not satisfy a
non-optional `float()` cast without raising) — confirms the "public reads filter `rating IS NOT NULL`"
invariant is enforced in the service layer today, not left to the caller. This is 평가 완료's entire
data source, already built, already correct.

### `MemberProfile.tsx` — confirmed public, confirmed already the 평가한 앨범 list

`myblog_front/src/components/member/MemberProfile.tsx:288` renders the `"평가한 앨범"` section title;
the file's own header comment (`:37`) documents `'ratings'` as *"the public 평가한 앨범 list every
[profile] surface since merge PR2."* Reachable logged-out (public profile route, `edge_guard` catch-all
GET per the route file's own header comment). This is the exact list 평가 완료 will present — this RFC
does not need to build a new list rendering, only (per Unresolved owner decisions) decide whether 평가
완료 gets its own dedicated view/sort/filter beyond what `MemberProfile` already shows, or is literally
the same component reused with a different frame (e.g. inside `BucketDetailShell`'s smart-entry slot).

### `GET /api/me/album-states` and `GET /api/me/review-candidates` — both exist, both precedent for 평가 예정's read shape

`myblog_backend/app/api/routes/me.py:108-142` (`get_my_album_states`) — JWT-scoped, optional `album_id`
filter, returns every own-state row (`rating`, `comment`, `review_candidate`, timestamps) via
`svc.my_states`. `me.py:145-176` (`get_my_review_candidates`) — JWT-scoped, **no filter param** (by
design — "there is no handle parameter"), joins the album table in the service
(`rating_service.py:272-297`, ordered `updated_at.desc()`) so a candidate-only row (no bucket, no
rating) still returns `album_title`/`album_cover_url`/`artist_id`/`artist_name` — **confirmed
bulk/no-N+1**: one query with a join, one batch `primary_artist_map` resolve for the whole page,
exactly the pattern a 평가 예정 bulk read must follow (whichever storage shape is chosen). Both routes
ride the `edge_guard` authed-GET catch-all — **no API Gateway route, no `terraform apply`** for either,
and a 평가 예정 read following the same shape inherits that.

### Frontend sort/stats utility already built — reusable, not to be reinvented

`myblog_front/src/lib/ratingStats.ts` exports `computeRatingStats` (count/average/half-step
distribution/peak, folded client-side over the full unpaginated feed — file's own header comment: *"If
the feed ever becomes paginated these stats must move server-side"*), `RATING_BUCKETS` (the ten
half-step buckets), and `RATING_SORTS`/`RatingSortKey` (`'recent' | 'score' | 'name'` — the exact three
axes `FEAT-album-review-authoring` Step 2 shipped, tie-break on score by `localeCompare(…, 'ko-KR')`
name). 평가 완료 reuses this file directly for ordering/filtering — no new sort utility needed.

## Verified current state — 평가 예정's storage question is genuinely open, not pre-decidable from code alone

The three representation options, with concrete costs measured against the schema above (not assumed):

| Option | Mechanism | Cost | Risk to "strictly separate" |
|---|---|---|---|
| **A — extend `album_reviews`** | new column `planned_at timestamptz null` (or `boolean`) on the same row `review_candidate` lives on | Cheapest: one migration, `ck_album_reviews_state_not_empty` extended to a 3-way OR, existing per-row upsert/delete-on-empty service logic extended | **Highest** — the row that carries the private review-candidate mark now also carries the private rating-intent mark; any future query, index, or serializer touching "does this row have a private facet" must remember to check the right one. The CHECK-constraint change alone is a live schema edit to a row every existing rating write already touches |
| **B — dedicated association/table** | new table, e.g. `PlannedRating(user_id, album_id, created_at)`, its own UNIQUE(user_id, album_id), no relation to `album_reviews` at all | Medium: one new table + migration, one new service, but zero risk of touching `album_reviews`'s existing CHECK/upsert logic | **Lowest** — physically separate storage is the literal meaning of "strictly separate"; a bug in one table's query cannot leak into the other's |
| **C — bucket membership** (a new system bucket `kind`, e.g. `to_rate`) | reuse `review_buckets`/`review_bucket_items` infra, a 4th system-kind partial unique index | Medium-high: touches bucket delete-guard, `isManualAddTarget`, bucket-type dispatch — the exact surface `ARCH-buckit-navigation-shell` is simplifying, not a place to add a 4th special case casually | **Explicitly rejected by prior-RFC hard rule** — `FEAT-album-review-authoring` hard rule 3-3 states bucket names/kinds are not how the product represents user-album *state*; a `to_rate` bucket kind would resurrect exactly the "버킷 이름이 상태를 대신한다" anti-pattern that RFC spent its Step 1 undoing (it moved 평론-candidate OFF a bucket-name convention and onto a typed row for this exact reason) |

**This RFC does not pick one.** Option C is disfavored on the evidence above (it directly contradicts a
standing hard rule from the sibling RFC this one must stay consistent with), but the choice between A
and B is a real architecture judgment — A is cheaper and consistent with the "one user-album state" row
philosophy that already governs `rating`/`comment`/`review_candidate`; B is what "strictly separate"
most literally means and has zero blast radius on `album_reviews`'s existing invariants. **Decision
gate**: implementation does not start until the owner picks A or B (see Steps, and Unresolved owner
decisions below) — this is exactly the kind of "material schema or product choice" the task instructions
require a gate for, and inventing a defaulted answer here would be presuming a schema shape the
instructions explicitly say not to presume.

## Target architecture and state ownership (shape depends on the gate; both branches specified)

### 평가 완료 (no gate — this branch is fully specified now)

- **Data source**: `album_reviews WHERE rating IS NOT NULL`, exactly what `GET /api/members/{handle}`
  and `GET /api/me/album-states` already return. No new endpoint is required for the *authenticated
  self* case (`album-states` already carries everything, filterable client-side to `rating != null`);
  the *public* case already exists (`GET /api/members/{handle}`).
- **Ordering/filtering**: reuse `lib/ratingStats.ts`'s `RATING_SORTS` (최신/별점/이름) and
  `computeRatingStats` verbatim.
- **Permissions**: public feed = public read (unchanged); if 평가 완료 gets a dedicated "my ratings"
  view distinct from the public profile section, it reads from `album-states` (already JWT-scoped,
  already returns own rows) filtered client-side.
- **Empty state**: reuse `FEAT-album-review-authoring` Step 2's already-designed empty-state copy for
  the rated-albums list (self vs. other-viewer branching, per that RFC's Decisions log).
- **Removing or changing an item** (per the task's own requirement) **modifies rating state, not bucket
  membership** — this is already true today (there is no bucket membership involved in a rating at
  all); this RFC only needs to confirm no future UI accidentally wires a "remove from 평가 완료" action
  to a bucket-delete call instead of `DELETE /api/reviews/albums/{album_id}` (the existing rating-delete
  route). Named explicitly so a Step 1 implementer doesn't invent a bucket-shaped affordance for a
  rating-shaped action.
- **Bulk retrieval**: already zero-N+1 (single unpaginated query + one batch artist resolve), confirmed
  above.

### 평가 예정 — Option A branch (extend `album_reviews`)

- New nullable column (`planned_at timestamptz` — a timestamp rather than a bare boolean gives 정렬 a
  free "최근에 표시한 순" axis at no extra cost, matching the `review_candidate` precedent's own
  `idx_album_reviews_user_candidate` partial-index shape).
- `ck_album_reviews_state_not_empty` becomes `rating IS NOT NULL OR review_candidate OR planned_at IS
  NOT NULL`.
- Read: extend `GET /api/me/album-states` (already returns every own-state row) with the new field —
  **no new route** (matches the existing "authed GET, edge_guard catch-all, no infra change" pattern).
  A dedicated `GET /api/me/planned-ratings` (mirroring `review-candidates`'s own dedicated-list
  precedent) if the UI wants a standalone list rather than filtering `album-states` client-side.
- Write: extend the existing `PUT /api/reviews/albums/{album_id}` partial-update body with
  `planned: boolean` (mirrors how `review_candidate` was added to the same PUT in
  `FEAT-album-review-authoring` Step 1) — no new write endpoint.
- Idempotent mark/unmark: PUT with `{planned: true}` twice is a no-op state (already true), matching
  the existing partial-update semantics for `review_candidate`.

### 평가 예정 — Option B branch (dedicated entity)

- New table `planned_ratings` (or similar): `id, user_id FK CASCADE, album_id FK CASCADE, created_at`,
  `UNIQUE(user_id, album_id)`. No CHECK coupling to `album_reviews` at all — a row's mere existence is
  the flag; unmark = delete the row (simpler than a nullable-field clear, and idempotent by
  construction: deleting a non-existent row is a no-op).
- Read: `GET /api/me/planned-ratings` (new, JWT-scoped, no infra change — same edge_guard pattern),
  joining `albums` for title/cover/artist exactly as `review-candidates` already does, for the same
  reason (a planned-only album may have no bucket entry and no rating row to source display data from).
- Write: `PUT /api/me/planned-ratings/{album_id}` (mark) / `DELETE /api/me/planned-ratings/{album_id}`
  (unmark) — both idempotent by the nature of upsert/delete-if-exists. **These would be the first
  authed non-GET routes this RFC adds that are not riding an existing PUT** — unlike Option A, Option B
  needs new API Gateway routes and a `terraform apply` (mutating routes are not on the edge_guard
  catch-all; only GETs are, per every existing route's own comments in this codebase).

### Whichever option: bulk retrieval and permission shape are identical

Both branches join `albums` in the service layer for display data (title/cover/artist), both are
JWT-scoped to the caller with no handle parameter (matching `review-candidates`'s "there is no way to
ask for someone else's" privacy posture — 평가 예정 is even more clearly private than 평론 후보, since
it is pre-decision noise, not even a considered candidate yet), both are one batch query + one batch
artist resolve, zero N+1 either way.

## UX behavior — desktop and mobile

- **평가 완료**: reuses the existing 평가한 앨범 list rendering (`MemberProfile.tsx`) and/or
  `lib/ratingStats.ts`'s distribution histogram (`FEAT-album-review-authoring` Step 2's already-shipped
  desktop/390px-verified layout) — no new responsive design needed, only a decision on *where* this
  list additionally surfaces (see Unresolved owner decisions).
- **평가 예정**: the mark/unmark toggle reuses the existing 평론 후보 toggle's already-proven placement
  pattern (`FEAT-album-review-authoring`'s Step 1 UX: always-visible-but-quiet on the bucket tile —
  `opacity: 0.45` idle / `1` on hover-or-marked, `:focus-visible` — and a same-pattern control on the
  album detail screen, reachable without entering edit mode and without a rating already present). A
  new, visually distinct icon/label from the existing 평론 후보 ✎ mark is required — sharing an icon
  between two conceptually different private marks on the same tile would defeat "strictly separate" at
  the UI layer even if storage is cleanly separated.
- **List/bulk view of 평가 예정**: a queue view mirroring `ReviewCandidates.tsx`'s existing shape
  (album cover, title, artist, "평가하러 가기" entry point into the rating control — not into `/write`,
  since this is a rating intent, not an editorial one).

## Data / API / contract impact

- **평가 완료**: none. Fully served by existing endpoints.
- **평가 예정, Option A**: one migration (nullable column + CHECK edit on `album_reviews`), one field
  added to `MyAlbumStateResponse`/`AlbumRatingResponse`'s write body, `openapi.json` regen + workspace
  merge + front `api.gen.ts` regen. No API Gateway route change (rides existing PUT/GET).
- **평가 예정, Option B**: one migration (new table), a new service, 2–3 new routes (list + mark +
  unmark), `openapi.json` regen + workspace merge + front regen, **plus** `infra/apigateway.tf` routes
  for the two mutating endpoints + `terraform apply` (the one piece of infra cost Option A avoids
  entirely).
- Either branch: `docs/contracts/README.md` procedure followed (service `openapi.json` regenerated and
  committed, workspace contract merged before the front regen per
  `reference-workspace-contract-merge-order`, front types verified).

## Dependency and repository order

`myblog_shared_db` (migration) → `myblog_backend` (guard/route + `openapi.json` export) →
`myblog-workspace` (contract merge) → `myblog_front` (regen + UI). Standard shared_db-first ordering
this workspace always uses. `myblog_music`/`myblog_worker` are untouched (rating identifiers are
confirmed backend+front+shared_db only, per `FEAT-album-review-authoring`'s own prior measurement that
those two services never reference this table).

## Step and PR boundaries

One step per session (hard rule #4). **Step 0 is the decision gate and must close before Step 1 can be
scoped concretely** — this mirrors `FEAT-album-review-authoring`'s own precedent of a hard stop before
committing implementation shape (that RFC's Step 3 AI-distillation re-observation gate).

### Step 0 — decision gate: Option A vs. Option B for 평가 예정 (docs-only)

Present the cost/risk table above to the owner; record the decision in this RFC's Decisions log. Blocks
every subsequent step — there is no code to write until this closes, per the task's own instruction to
include "a decision gate before implementation if a material schema or product choice remains
unresolved."

**Verification**: doc review only; no code changes.

---

### Step 1 — 평가 완료 (no schema dependency — may ship before or after Step 0 closes, since it needs no new storage)

Surface the existing rated-albums feed as a named 평가 완료 view (self-scoped, reusing `album-states` +
`ratingStats.ts`), wherever the owner decides it should live (Unresolved owner decision 1). No backend
change.

**Verification**: `pnpm test && pnpm lint && pnpm exec astro check`; real-browser CDP — the list matches
`GET /api/me/album-states` filtered to `rating != null`, sorts correctly on all three axes, empty state
renders correctly for a zero-rating account (still true for every non-owner account today per
`FEAT-album-review-authoring` Step 2's own last prod read).

**Rollback**: revert the PR. Frontend-only, no data touched.

---

### Step 2 — shared_db + backend: 평가 예정 storage (shape per Step 0's decision)

Migration + service + route(s) per whichever option Step 0 selected. Real-engine integration test for
the CHECK constraint (Option A) or the new UNIQUE constraint (Option B) — mocks cannot prove
constraint behavior (`feedback-sa-session-lifecycle-mock-blind`).

**Verification**: `pytest` including the real-engine test; `openapi.json` diff committed; if Option B,
new routes probed live (401 vs 404) before `terraform apply`, full `plan` inspected first per hard rule
#8.

**Gate** (Option B only): `terraform apply` for the new mutating routes on owner go-ahead — full plan
first, stop on unexpected drift, per hard rule #8.

**Rollback**: Option A — `DROP COLUMN` + CHECK revert, trivial while no row carries the new facet
alone (same posture as every prior nullable-column addition in this table's history). Option B — `DROP
TABLE`, trivial, no other table references it.

---

### Step 3 — workspace: contract merge

`tools/merge_openapi.py` merge, before the front regen (`reference-workspace-contract-merge-order`).

**Verification**: doc/diff review — confirm exactly the expected new field(s)/route(s) appear, nothing
else moved.

---

### Step 4 — front: mark/unmark control + 평가 예정 queue view **[gated: `ARCH-buckit-navigation-shell` Step 1, if the owner routed this into the nav shell]**

`api.gen.ts` regen; the mark/unmark toggle (album screen + bucket tile, per UX behavior above); the
queue view (`ReviewCandidates.tsx`-shaped list). Idempotent mark/unmark verified against the real API,
not just optimistic UI.

**Verification**: `pnpm test && pnpm lint && pnpm exec astro check`; real-browser CDP — mark, reload,
confirm persisted; mark twice, confirm no duplicate/error; unmark, confirm removed from the queue view;
privacy check — a logged-in-as-someone-else session issues zero requests to the 평가 예정 read path
when viewing another member's profile (mirrors `FEAT-album-review-authoring` Step 2's own privacy
measurement methodology: inspect the actual `/api/` requests fired, don't just trust the UI not
rendering it).

**Rollback**: revert the PR. Frontend-only on top of an already-shipped backend contract.

---

## Migration and rollout

`myblog_shared_db` migration applied to Neon prod on owner go-ahead before the backend pin bump
(`reference-shared-db-cross-repo-rollout` — forward migrations are Claude-applied with approval per
hard rule #3's actual scope, `feedback-forward-migration-is-claude-applied`). No backfill: a new
nullable column/table starts empty by construction, matching `V51__playback_bucket`'s own "no backfill
needed, auto-creation is idempotent anyway" precedent.

## Rollback

Per-step rollback specified above. No step is a rollback-in-production concern (hard rule #4's
restriction) since every step here is a forward migration or a frontend-only change.

## Tests and production smoke verification

`pytest` (backend, including the real-engine constraint test), `pnpm lint`/`pnpm exec astro check`/
`pnpm test` (front), real-browser CDP per step above, local smoke, deploy, production smoke quoted in
the PR body. If Option B: new route liveness probe (401 authed-vs-404-missing) before and after
`terraform apply`.

## Risks and failure modes

- **Option A's CHECK-constraint edit is a live schema touch on a row every existing rating write already
  uses** — a mistake here (e.g. an incorrect OR-list) could reject legitimate rating writes, not just
  the new feature. Mitigation: the real-engine integration test asserts the *existing* rating-only and
  candidate-only insert paths still succeed post-migration, not just the new planned-only path.
- **Icon/label collision between 평론 후보 (✎) and 평가 예정 at the UI layer**, even with clean storage
  separation — the fastest way to violate "strictly separate" is a shared visual affordance a user can't
  tell apart. Named explicitly in UX behavior above as a hard requirement, not a nice-to-have.
- **평가 예정 leaking into a public surface by omission** — the same class of risk
  `FEAT-album-review-authoring` measured explicitly for `review_candidate` (Step 2's privacy check via
  request inspection, not trust). This RFC's Step 4 verification reuses that exact methodology.
- **Option B's extra infra surface** (new routes + `terraform apply`) is a real cost this RFC does not
  minimize — if the owner picks B, Step 2's gate is a genuine stop-and-confirm point, not a formality.

## Rejected alternatives

- **Bucket-membership representation (Option C)** — rejected above, in detail, as directly
  contradicting `FEAT-album-review-authoring` hard rule 3-3.
- **Reusing `review_candidate` with a UI-level relabeling** ("call the same flag 평가 예정 in one
  context and 평론 후보 in another") — explicitly forbidden by the sibling RFC's own terminology
  section; not entertained here beyond naming it as the thing this RFC's title could be mistaken for.
- **A combined "평가 완료 + 평가 예정" single screen from Step 1** — rejected for the same reason
  `FEAT-album-review-authoring` split C5/C6 into separate steps: 평가 완료 has data today and 평가
  예정 does not until Step 0's gate closes and Step 2 ships, so combining them would either delay the
  zero-cost 평가 완료 view behind the schema decision, or ship 평가 예정 half-built. Kept as two
  independently-shippable views, Step ordering makes this explicit.

## Unresolved owner decisions

1. **Storage shape for 평가 예정 — Option A or Option B** (Step 0's actual gate). Recommended default:
   **Option B** (dedicated table), on the grounds that "strictly separate" was stated as an explicit
   requirement in the task instructions and Option B is the only one of the two that satisfies it
   structurally rather than by convention/discipline alone — but this is a recommendation, not a
   decision; the gate exists precisely because this could go either way.
2. **Where do 평가 완료 and 평가 예정 surface** — inside `ARCH-buckit-navigation-shell`'s
   `BucketDetailShell` as nav-adjacent smart entries (requiring that RFC's Step 2 first), or as
   standalone profile-page sections (no dependency, ships independently)? Blocks whether Step 4 carries
   the cross-RFC dependency edge at all.
3. **Does 평가 예정 need a sort/ordering scheme of its own** (e.g. "표시한 순" via `planned_at`), or is
   unordered-by-recency (matching `review-candidates`' own `updated_at.desc()` precedent) sufficient?
   Low-stakes, does not block Step 2 either way — default to the existing precedent if undecided at
   implementation time.

## Relationship to existing RFCs and plan rows

- Sibling of `FEAT-album-review-authoring` (accepted, Steps 1–2 shipped, Steps 3–5 open) — reuses its
  shipped `album_reviews` shape and read endpoints for 평가 완료, and is bound by its explicit
  terminology prohibition against renaming/repurposing `review_candidate`. Does not touch that RFC's own
  open steps.
- Consumes `ARCH-buckit-navigation-shell`'s `BucketDetailShell` empty slot **only if** Unresolved
  decision 2 routes these collections through the nav tree — otherwise no dependency.
- Unrelated to `ARCH-global-playback-experience` — no shared files, no shared state.
- `plan.md` gains a one-line Active-section pointer (see this session's plan.md diff), and its own row
  states plainly that Step 0 (the decision gate) is the first and current blocking item — nothing past
  Step 0 is "startable today" in the sense `plan.md`'s Backlog-vs-Active convention requires.
