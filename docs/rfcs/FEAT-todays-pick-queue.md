# FEAT-todays-pick-queue: staging queue for 오늘의 곡

- **Status**: accepted
- **Owner**: 박지훈
- **Created**: 2026-07-17
- **Plan row**: `plan.md` → FEAT-todays-pick-queue

---

## Goal

The owner can stash tracks into a private queue whenever they come across one, then later pick one from that queue to post as the day's 오늘의 곡 — instead of having to find the track by search at the moment of posting. The queue lives in the DB, so it is shared across the owner's devices and survives a browser-data wipe. It is reachable from a **큐** tab inside the existing 곡 올리기 modal; the home page gains no new surface, and visitors/members see no change.

## Non-goals

- **No manual reordering / priority.** The queue is date-added-desc. A `position` column and drag-sort are scope creep for a "대충 담아두는" list.
- **No per-member queues.** The queue exists to feed the single owner-curated `daily_picks` row (`require_owner`). Members do not get one. See OQ1.
- **No scheduling.** The queue does not auto-post on a date; posting stays a manual click. (An auto-fill-from-queue cron is a plausible later RFC, deliberately excluded here.)
- **No notes/annotations per queued track.** `daily_picks` has no note column by owner decision (V39 note (4)); the queue mirrors that.
- **No album-level queueing.** Track-primary, mirroring `daily_picks` (V39 note (2)).
- **No change to the public reads** (`GET /api/todays-pick`, `/history`) or to the home tile.

## Current state

- **Store**: `daily_picks` (shared_db `migrations/V39__daily_picks.sql`) — one row per calendar day, `UNIQUE (pick_date)`. Track-primary: `track_id` + `album_id` both `NOT NULL` FK, plus denormalized display columns `title` / `artist` / `cover_url` (nullable) / `spotify_track_id`, so the public GET needs no cross-service join. Latest applied migration is **V47** (`user_artist_tracks`) → this RFC's migration is **V48**.
- **Backend**: `myblog_backend/app/api/routes/todays_pick.py` — `GET ""` + `GET "/history"` public; `PUT ""` + `DELETE ""` gated by `require_owner` (`app/core/auth.py:133`). Service layer at `app/services/todays_pick_service.py`, wired in `app/di.py`.
- **Auth shape (load-bearing for the queue read)**: `require_owner` → `require_cognito_token` (`auth.py:110`) → `verify_token(...)`, i.e. the backend **verifies the JWT itself** rather than trusting a pre-validated API Gateway authorizer context. A queue GET riding the public `edge_guard` GET catch-all (`api_get_proxy`) is therefore still owner-gated: no token → 401, non-owner token → 403. The queue is never publicly readable despite the catch-all.
- **Infra**: `infra/apigateway.tf:307–327` declares `PUT /api/todays-pick` + `DELETE /api/todays-pick` as JWT routes. The two public GETs deliberately have **no** route (they ride `api_get_proxy`). A new authed mutation 404s until it gets a route here (probe: 401 = live, 404 = missing).
- **Front**: `components/home/TodaySongPicker.tsx` — a `qb-modal--add` search modal over the shared `useMusicSearch({recallTypes:['track','artist']})` core; a picked `TrackHit` is mapped to the `PUT /api/todays-pick` body and handed to the parent via `onPick`. `components/home/TodaySongBuckit.tsx` owns the API call + owner gating (`isOwnerUser()`). Client at `lib/todaysPick.ts`.
  - The picker already refuses Spotify-only hits (`!hit.id` → "이 곡은 아직 DB에 없어요"), because `daily_picks.track_id` is `NOT NULL` and a Spotify candidate has no DB track id until the SQS absorb lands. **The queue inherits this constraint verbatim** — see OQ2.

## Target state

- New table `daily_pick_queue`, whose columns are a **superset-free mirror** of the `daily_picks` payload columns (`track_id`, `album_id`, `title`, `artist`, `cover_url`, `spotify_track_id`). A queue row *is* a staged `daily_picks` row, so promotion is a pure column copy — no re-resolve, no second search, no Spotify call.
- New owner-only routes on the existing `todays_pick` router:
  - `GET /api/todays-pick/queue` → queued rows, newest first (no apigw route; rides `api_get_proxy`, owner-gated in-Lambda).
  - `POST /api/todays-pick/queue` → add (idempotent on `track_id`).
  - `DELETE /api/todays-pick/queue/{id}` → remove.
  - `POST /api/todays-pick/queue/{id}/promote` → **atomically** upsert `daily_picks` from that row and delete the queue row, in one transaction. Returns the created `DailyPickItem`.
- `TodaySongPicker` gains two tabs: **검색** (today's behavior, plus a "큐에 담기" affordance alongside "올리기 +") and **큐** (the stashed list; each row → "오늘의 곡으로 올리기" / remove).

## Steps

Rollout follows the shared_db cross-repo order: migration → prod apply (pre-merge, human) → service pin → workspace contract → frontend.

### Step 1 — shared_db V48 `daily_pick_queue`

`migrations/V48__daily_pick_queue.sql` (plain SQL; no Flyway runner — the file self-commits, so strip `BEGIN/COMMIT` if dry-running against prod):

```sql
CREATE TABLE IF NOT EXISTS daily_pick_queue (
  id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  track_id         UUID        NOT NULL REFERENCES tracks (id) ON DELETE CASCADE,
  album_id         UUID        NOT NULL REFERENCES albums (id) ON DELETE CASCADE,
  title            TEXT        NOT NULL,
  artist           TEXT        NOT NULL,
  cover_url        TEXT,
  spotify_track_id TEXT        NOT NULL,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT uq_daily_pick_queue_track UNIQUE (track_id)
);
CREATE INDEX IF NOT EXISTS ix_daily_pick_queue_created_at ON daily_pick_queue (created_at DESC);
```

`UNIQUE (track_id)` makes re-adding the same track a no-op (`ON CONFLICT DO NOTHING`) rather than a dupe. Cascade FKs match `daily_picks` (V39 note (5)). Additive + reversible; **rule #3 — prod apply needs human approval**.

Also: ORM model in `src/`, and mirror the DDL into **both** `myblog_shared_db/tests/canonical_schema.sql` and `docs/contracts/schema.sql` — byte-identity is convention-only and unenforced across repos, so `diff` both before commit.

**Verification**:
```
cd myblog_shared_db && PYTHONPATH=src pytest        # schema-parity test (must run with PYTHONPATH=src)
diff <(...) <(...)                                   # canonical_schema.sql vs docs/contracts/schema.sql
```
**Rollback**: `DROP TABLE IF EXISTS daily_pick_queue;` (no consumer until Step 2).

---

### Step 2 — backend queue store + routes

Extend `todays_pick_service.py` + `todays_pick.py` with the four routes above, all `Depends(require_owner)`. Promote runs the `daily_picks` upsert (`ON CONFLICT (pick_date)`) and the queue-row delete **in one transaction** so a mid-flight failure can't consume the queue row without posting the pick. Bump the shared_db git pin. Export `openapi.json` in the same PR.

**Verification**:
```
cd myblog_backend && pytest
# promote atomicity: covered by a test that forces the delete to raise and asserts daily_picks is unchanged
```
**Rollback**: revert; the table is inert without consumers.

---

### Step 3 — infra routes + contract merge

Add to `infra/apigateway.tf`, following the `todays_pick_put` pattern (literal paths; `{id}` for delete/promote):

```
POST   /api/todays-pick/queue
DELETE /api/todays-pick/queue/{id}
POST   /api/todays-pick/queue/{id}/promote
```

`GET /api/todays-pick/queue` gets **no** route (rides `api_get_proxy`, owner-gated in-Lambda per Current state). Then `tools/merge_openapi.py` → commit regenerated `docs/contracts/openapi.json` (the service→workspace notify dispatch 401s; auto-merge is dead). Merge the workspace contract first so the service notify is a no-op.

**Verification**:
```
terraform plan            # full plan, no -target; expect 3 added routes, 0 changed, 0 destroyed
curl -X POST https://<api-gw-host>/api/todays-pick/queue   # 401 = route live, 404 = missing
```
**Rollback**: remove the routes + re-apply. **A merged infra PR is not a prod change — a human runs `terraform apply` locally.**

---

### Step 4 — front: 검색 / 큐 tabs in the picker

`lib/todaysPick.ts` gains `getPickQueue` / `addToPickQueue` / `removeFromPickQueue` / `promoteFromPickQueue` (all `apiFetch` — owner-only, incl. the GET, which must carry the Bearer token). `TodaySongPicker` gets a tab strip; the 검색 tab keeps today's rows and adds "큐에 담기", the 큐 tab lists queued rows with promote/remove. Regenerate `api.gen.ts` (`pnpm generate:types`) in the same PR or the front deploy gate fails.

**Verification**: `pnpm lint` + `pnpm exec astro check`; drive both tabs in a real browser (CDP fetch-mock — localhost can't reach prod backend), then prod smoke as the owner post-deploy.

---

## Open questions

1. ~~**Queue scope: owner-only, or `user_id`-scoped?**~~ — **RESOLVED 2026-07-17 (owner): owner-only, no `user_id`.** Mirrors `daily_picks` (`require_owner`, no user column). Nothing would consume a `user_id` — members have no 오늘의 곡. Revisit only if members ever get a pick; the V40–V42 bucket migrations are the precedent for adding the column later.
2. ~~**Spotify-only hits in the queue?**~~ — **RESOLVED 2026-07-17 (owner): option (a) — keep the refusal for v1.** `track_id` stays `NOT NULL`; "큐에 담기" on a Spotify-tagged row surfaces the picker's existing "이 곡은 아직 DB에 없어요" notice. Keeps the queue schema an exact `daily_picks` mirror and guarantees promote can never fail late. **Known cost, accepted:** you cannot stash a just-discovered track until its SQS absorb lands — 큐에 담기 requires a Spotify 싱크 first, then a re-search. If that friction bites in practice, option (b) (nullable `track_id`, resolve at promote) is the escape hatch and would be a follow-on migration.
3. ~~**Does promote consume the queue row?**~~ — **RESOLVED 2026-07-18 (shipped as recommended): yes.** Promote deletes the queue row in the same transaction as the pick upsert (backend #123); re-posting later means re-queueing.
4. **Queue size cap?** — none proposed. If it grows unbounded the 큐 tab needs paging. Blocks nothing now; revisit if it passes ~50 rows.

## Decisions log

| Date | Decision | Step |
|------|----------|------|
| 2026-07-17 | Storage = DB table (not localStorage); queue UI = tab inside the existing picker modal, not a new home section | — |
| 2026-07-17 | OQ1 — queue is owner-only, no `user_id` column (mirrors `daily_picks`) | 1 |
| 2026-07-17 | OQ2 — `track_id` stays `NOT NULL`; Spotify-only hits keep the existing refusal for v1. Accepted cost: no stashing a track until its absorb lands | 1 |
| 2026-07-17 | RFC accepted (owner, in-session). Steps 1–3 developed in parallel worktrees; merge order stays V48 → backend → infra/contract → front | 1–3 |
| 2026-07-18 | Steps 1–3 shipped + prod-verified: shared_db #68 (V48 prod-applied pre-consumer, owner-approved), backend #123 (pin @50d33c3; TEST_DB-gated promote-atomicity integration tests), ws #637 (tf apply 3/0/0, owner-approved). Probes: no-token 401 / member JWT 403 on all four queue routes; full prod smoke 19/0. OQ3 resolved as recommended (promote consumes the row). Step 4 (front) remains | 1–3 |
