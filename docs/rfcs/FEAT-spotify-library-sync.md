# FEAT-spotify-library-sync: Spotify Library sync bucket

- **Status**: draft
- **Owner**: 박지훈
- **Created**: 2026-06-08
- **Plan row**: `plan.md` → FEAT-spotify-library-sync

---

## Goal

A new **special bucket** in the review-bucket board (`review_buckets`, the BucketBoard on `/profile`) that
**explicitly** two-way mirrors the owner's Spotify saved-albums Library (`GET/PUT/DELETE /me/albums`, album-level
only — no playlists). Adding an album to the bucket and pressing **동기화** saves it to the Spotify Library;
removing it then syncing removes it from the Library **only if MyBlog added it** (a pre-existing saved album is
never deleted). Each album carries a visible **source** (added-by-MyBlog / pre-existing) and **state** (synced /
failed / needs-attention). All Spotify I/O runs in the worker (hard rule #9); the backend only enqueues and serves
cached state; the frontend polls.

This is the deferred **D11 follow-up** to `FEAT-member-dashboard` (Spotify write actions). It implements the
original 6-point spec's requirements **4/5/6**; requirements **1/2/3** already shipped in
`FEAT-member-dashboard-realdata` (#287) and are out of scope here.

## Non-goals

- Playlists (album-level Library sync only).
- Auto / scheduled reconcile — sync is **explicit** (a 동기화 button) for now. No EventBridge rule (unattended
  writes to the owner's real account are high blast-radius). Documented future option behind a flag.
- Multi-user scoping (single-owner model, no `user_id`, matches the whole codebase → `FEAT-multi-user-accounts`).
- Touching reqs 1/2/3 (draft reviews, listened-album history, recent/now-playing) — already shipped.
- The existing `album_to_listen_items` ("들을 것") queue — unrelated and untouched.

## Current state

- **No Spotify write code anywhere.** `myblog_worker/worker/clients/spotify_user_client.py` exposes only
  `get_recently_played` + `get_currently_playing`; the OAuth refresh token in Secrets Manager `myblog/spotify`
  has **read-only** scopes (`user-read-recently-played`, `user-read-currently-playing`).
- Worker SQS dispatch: `worker/handler.py:99-111` routes `{"job":"spotify_refresh"}` (manual) /
  `{"job":"spotify_listening"}` (EventBridge 1h) / album-sync messages. `_request_with_retry`
  (`spotify_user_client.py:52-90`) gives 429/5xx + Retry-After handling; token refresh (`:182-231`) writes
  rotation + `needs_reauth` back to the secret.
- Bucket model: `review_buckets` (`models.py:314-356`) + `review_bucket_items` (`:358-396`,
  `UNIQUE(bucket_id, album_id)`); `albums.spotify_id` is `TEXT UNIQUE`. Backend bucket routes in
  `app/api/routes/buckets.py`; mutations behind the API Gateway Cognito authorizer + edge_guard.
- Backend SQS enqueue template: `app/clients/sqs_client.py:22-41` `send_listening_refresh()` →
  `{"job":"spotify_refresh"}`; backend IAM already has `sqs:SendMessage` to blogSQS. The 202-enqueue + poll
  pattern already exists (`library.py:259-265` `POST /api/library/refresh-recent`, polled via
  `spotify.api.ts:102-107`).
- Frontend: `BucketBoard.tsx` (module-level `dnd` payload `:31-36`, `AlbumChip` `:174-263`, `copyAlbum` op
  `:872-897`, badge slots `:240-254`); the "최근 들은 앨범" recently-listened strip renders at `:1146-1163`.

## Target state

- A single flat `review_buckets` row with `kind='spotify_library'` holds the bucket's intent (which albums the
  owner wants mirrored). A side table `spotify_library_albums` (keyed on `album_id`) records per-album
  `source`/`state` and last-observed Library/bucket membership — **separate from `review_bucket_items`** so the
  pre-existing-source fact survives a bucket-remove (req 5's "never delete a pre-existing album").
- Worker handles `{"job":"spotify_library_sync"}`: reads the Library, stamps source on first touch
  (contains-check before any PUT), pushes MyBlog-added albums, removes only MyBlog-added albums dropped from the
  bucket, and **pulls** pre-existing Library albums into the bucket as items. Per-album failures don't abort the
  pass.
- Backend `POST /api/buckets/spotify-library/sync` (202, Cognito-gated, server-debounced) enqueues the job;
  `GET /api/buckets/spotify-library/state` (edge_guard GET, polled) returns per-album source/state +
  `last_synced_at` + `needs_reauth`.
- Frontend renders the new bucket just below the recently-listened strip, reusing AlbumChip/BucketCard DnD
  (add/remove = bucket intent only, **no** Spotify call), with a 동기화 button, per-album source/state badges, and a
  needs-reauth banner.

## Data model

Migration **`V15__spotify_library_sync.sql`** (additive, idempotent). Two PG enums + one column + one table.

```sql
-- enums
CREATE TYPE spotify_library_source AS ENUM ('myblog_added', 'preexisting');
CREATE TYPE spotify_library_state  AS ENUM ('pending', 'synced', 'failed', 'needs_attention');

-- marker on review_buckets: at most one kind='spotify_library' bucket (partial-unique,
-- mirrors the existing single-is_done index idiom)
ALTER TABLE review_buckets ADD COLUMN kind TEXT NOT NULL DEFAULT 'review';
CREATE UNIQUE INDEX idx_review_buckets_single_spotify_library
  ON review_buckets ((TRUE)) WHERE kind = 'spotify_library';

-- side table — provenance + sync state, outlives review_bucket_items churn
spotify_library_albums(
  id             UUID PK default gen_random_uuid(),
  album_id       UUID UNIQUE REFERENCES albums(id) ON DELETE CASCADE,
  spotify_id     TEXT NOT NULL,                       -- denormalized for contains/PUT/DELETE without a JOIN
  source         spotify_library_source NOT NULL,     -- immutable once stamped
  state          spotify_library_state  NOT NULL DEFAULT 'pending',
  in_bucket      BOOLEAN NOT NULL DEFAULT true,        -- bucket intent (is it an item in the special bucket?)
  in_spotify     BOOLEAN NOT NULL DEFAULT false,       -- last-observed Library membership
  last_error     TEXT,
  last_synced_at TIMESTAMPTZ,
  created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

The 5 surfaced statuses derive from `(source, state)`: **added-by-myblog** = source=myblog_added;
**pre-existing** = source=preexisting; **synced/failed/needs-attention** = the state value. `source` is
**immutable** once stamped — a safety rail against ever re-classifying a pre-existing album as deletable.

`models.py`: add `ReviewBucket.kind` (`Mapped[str]`, server_default `'review'`) + the partial-unique index in
`__table_args__`; add a new `SpotifyLibraryAlbum` model; declare the two enums as `PGEnum(..., create_type=False)`
mirroring `POST_STATUS` (`models.py:28-38`).

## Reconcile algorithm (worker, one pass, idempotent)

Let **B** = album_ids that are items in the special bucket (intent); **L** = the Spotify saved-album set.

1. Read **L** (`get_saved_albums`, paginate `next`). Token `invalid_grant`/`needs_reauth` → abort, mark pending
   rows `needs_attention`, surface via the secret's `needs_reauth` flag.
2. Map **L** → catalog (`SELECT id, spotify_id FROM albums WHERE spotify_id = ANY(:L)`). Unknown L-ids → enqueue
   album-sync (reuse `sqs_producer`), skip this pass (they surface on the next 동기화; FK to `albums` requires a
   catalog row first).
3. **First-touch source stamp**: for each B-album with no `spotify_library_albums` row, `contains`-check it →
   `preexisting` if already saved else `myblog_added`; insert the row.
4. Diffs (catalog-known albums only):
   - **ADD** = `{a ∈ B : not in_spotify}` → `PUT /me/albums` (chunk ≤ 20). Success → `state=synced, in_spotify=true`;
     per-chunk failure → `state=failed, last_error`.
   - **REMOVE** = `{a : in_spotify and not in_bucket and source=myblog_added}` → `DELETE /me/albums`. **Never**
     includes `source=preexisting` (req 5 hard rule).
   - **PULL** = `{a ∈ L : not in_bucket}` → create a `review_bucket_items` row in the special bucket (append) +
     upsert the side row (`source=preexisting, in_bucket=true, in_spotify=true, state=synced`).
5. Re-`contains`-check the touched set → `synced` where Spotify agrees with intent, else `needs_attention`.
6. Commit; set `last_synced_at = now()` (the poll anchor).

Idempotent: re-running is a no-op when intent already matches the Library. Partial failure → per-album `state`,
never a whole-pass abort (mirrors `run_listening_sync` recent/now-playing isolation). SQS DLQ (maxReceive 3) +
720s visibility cover transient worker death; every write is an `album_id`-keyed upsert, so retry is safe.

**Safety — DRY_RUN first prod pass.** The worker already honors `settings.DRY_RUN` (`handler.py:33-37`). The first
prod reconcile runs under DRY_RUN: it logs the intended PUT/DELETE sets without executing. The owner reviews
CloudWatch, then a real pass runs. This is the primary guard for the first feature that mutates the real account.

## Steps

Each step is independently mergeable and prod-gated (CLAUDE.md rule #4 — one prod-observe gate per session).
shared_db rollout order: migration → **prod apply (before merge, human approval, rule #3)** → pin bump → contract
→ frontend.

### Step 0 — Spotify token re-bootstrap (owner precondition, blocks Step 2 prod)

Owner re-runs `scripts/spotify_bootstrap_token.py --write` to mint a refresh token that includes
`user-library-read` + `user-library-modify`. Manual Spotify-console authorize; longest lead — do first. Until
done, every PUT/DELETE returns 403 missing-scope and the worker marks rows `needs_attention`.

**Verification**: `GET /api/library/spotify-connection` → `connected:true, needs_reauth:false`; a worker DRY_RUN
pass logs a successful `get_saved_albums` read (proves library-read scope).

### Step 1 — shared_db V15 migration + models

`migrations/V15__spotify_library_sync.sql` (above) + `models.py` (`ReviewBucket.kind` + `SpotifyLibraryAlbum` +
two enums). Apply to prod Neon **before merge** (human approval). Version/pin bump.

**Verification**:
```
# syntax + idempotency against Neon (test branch first, then prod with approval)
psql "$DATABASE_URL_no_psycopg" -v ON_ERROR_STOP=1 -f migrations/V15__spotify_library_sync.sql   # re-run = no-op
python -c "import myblog_shared_db.models"   # model import clean
pytest   # shared_db model tests
```
**Rollback**: `DROP TABLE spotify_library_albums; ALTER TABLE review_buckets DROP COLUMN kind;
DROP TYPE spotify_library_state, spotify_library_source;` (human approval, rule #3).

### Step 2 — worker library sync

New `worker/service/library_sync_service.py` (raw-SQL style like `listening_sync_service.py` — no ORM pin beyond
the applied migration) implementing the reconcile algorithm; new `spotify_user_client` methods
(`get_saved_albums` / `check_saved_albums` / `save_albums` / `remove_albums`, all via `_request_with_retry`,
chunk ≤ 20); dispatch branch in `handler.py:99-111` for `{"job":"spotify_library_sync"}`. Pin shared_db to the
Step-1 version. **Depends on Step 0 + Step 1 prod-applied.**

**Verification**: local pytest (mock Spotify) + one real-engine integration test of the reconcile (per
`feedback-sa-session-lifecycle-mock-blind`). Prod: hand-craft the SQS message, **DRY_RUN** first (inspect
CloudWatch for the intended PUT/DELETE sets), then a real pass; verify `spotify_library_albums` rows + the owner's
Library in the Spotify app.

**Rollback**: remove the dispatch branch (no message producer ships until Step 3) — the job becomes unreachable.

### Step 3 — backend enqueue + state endpoints

Lazy `get_or_create` of the `kind='spotify_library'` bucket; `POST /api/buckets/spotify-library/sync` (202,
Cognito-gated, server-debounced on `max(last_synced_at)` like the listening refresh) via new
`SqsClient.send_library_sync()`; `GET /api/buckets/spotify-library/state` (edge_guard GET, returns per-album
source/state + `last_synced_at` + `needs_reauth` from `get_spotify_connection_status`). New `infra/apigateway.tf`
entry for the POST. Regenerate `openapi.json` in the same PR → workspace merge → front `api.gen.ts` (CI drift gate).

**Verification**: `terraform plan` clean for apigateway; local pytest + lint (no local DB → real verify deferred to
prod per `feedback-local-db-smoke-fallback`); openapi drift gate green. Prod: `curl` the POST (202) and GET state.

### Step 4 — frontend bucket UI

New bucket rendered just below the recently-listened strip (`BucketBoard.tsx:1163`, filtered out of the normal
`tree` by `kind`), reusing AlbumChip/BucketCard DnD + `copyAlbum` (add/remove = **bucket intent only, no Spotify
call**); a 동기화 button modeled on `refreshRecent()` that polls `GET .../state` until `last_synced_at` advances;
per-album source/state badges in the existing badge slots; a needs-reauth banner reusing the 연동-tab affordance.

**Verification**: `pnpm lint` + `pnpm exec astro check`; **real browser click-through** (add/remove intent, 동기화,
badge states, needs-reauth) on prod `/profile` via CDP (seed access_token) — per
`feedback-front-verify-live-dom-not-harness`. Lint + astro-check alone miss render/event regressions (BUG-11→12).

## Open questions

1. **Migration number (blocks Step 1)** — V14 is highest applied; `FEAT-genre-taxonomy` (deferred, not applied)
   soft-claims V15 but its decisions log permits next-free at un-defer. **Resolution: this feature takes V15;
   genre re-bumps to V16 on un-defer.** Recorded in `plan.md` so whoever merges first wins V15.
2. **Two-way mirror PULL scope (Step 2/4)** — ✅ **RESOLVED 2026-06-08**: full PULL — show every Library album in
   the bucket — **but the source distinction is mandatory**: pre-existing (already in Spotify) vs MyBlog-added must
   be visually distinguished (the `source` enum + badge already does this). The bucket looks empty of pre-existing
   albums until the first 동기화 (explicit-sync contract) — document in empty-state copy.
3. **Un-catalogable Library album (Step 2)** — an album in the Library but never in our catalog loops as
   "enqueued, never appears." Cap with `needs_attention` after N misses, or accept a silent skip + UI note "일부
   앨범은 다음 동기화에 반영됩니다". **Lean: UI note now, counter later.**
4. **Large-Library visibility window (Step 2)** — a huge Library could exceed the 720s SQS visibility timeout.
   Mitigate by chunking + re-enqueueing a continuation message (worker already self-produces). Decide threshold at
   Step 2 against the owner's real Library size.

## Decisions log

| Date | Decision | Step |
|------|----------|------|
| 2026-06-08 | Scope = reqs 4/5/6 only; 1/2/3 already shipped (#287) | — |
| 2026-06-08 | "To Listen bucket" = NEW special bucket in BucketBoard, Library-mirroring — NOT `album_to_listen_items` | — |
| 2026-06-08 | Sync is explicit (동기화 button), not auto-on-add/remove | — |
| 2026-06-08 | Dedicated `spotify_library_albums` side table over columns on `review_bucket_items` (source must outlive bucket-remove) | 1 |
| 2026-06-08 | This feature takes V15; genre re-bumps to V16 | 1 |
| 2026-06-08 | First prod reconcile runs under DRY_RUN before any real write | 2 |
| 2026-06-08 | OQ2: full PULL (show all Library albums) but pre-existing vs MyBlog-added MUST be visually distinguished | 2/4 |
