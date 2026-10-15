# FEAT-spotify-library-autosync: sync on entry, saved-date order, auto-research, cover overlap

- **Status**: draft
- **Owner**: owner
- **Created**: 2026-10-15
- **Plan row**: `plan.md` → FEAT-spotify-library-autosync

---

## Goal

Opening the board syncs the Spotify library on its own, and sync requests never pile up:
one worker run at a time, and a run that just finished absorbs any request that arrives
right after it. The library renders as one list, newest-saved first, with other sort
orders available. There is no 내가 넣은 / 기존 split. Every library album is queued for
research exactly once. The ✎ 평론 쓸 것 mark on a cover can be clicked again, because the
research dot no longer covers it.

## Non-goals

- Scheduled (EventBridge) library sync. A sync still only starts from a page entry or the
  manual button.
- Running the research poller. Queued rows wait for the owner's local `research-poller`
  (`scripts/research_poller.py`, launchd). It is **not loaded** as of 2026-10-15
  (`launchctl list` shows no entry), and starting it is an owner action.
- Changing the reconcile rules (ADD / REMOVE / PULL, never delete a `preexisting` album).
  `source` is still stamped and still blocks deletion. Only its display goes away.
- Multi-user library sync. The bucket stays owner-only (`require_owner`).

## Current state

Audited against `origin/main` and production on 2026-10-15.

**Sync trigger and debounce.**
- `useSpotifyLibrary.runLibrarySync` (`myblog_front/src/components/member/useSpotifyLibrary.ts`)
  runs only from the 동기화 button.
- The button calls `POST /api/buckets/spotify-library/sync` (`myblog_backend/app/api/routes/buckets.py`).
  The route enqueues `{"job":"spotify_library_sync"}` unless
  `BucketService.library_sync_debounced` holds.
- The debounce is computed from `max(spotify_library_albums.last_synced_at)`
  (`LIBRARY_SYNC_DEBOUNCE_SECONDS = 30`). The worker (`run_library_sync`) stamps
  `last_synced_at` **only on rows it changes**. Production on 2026-10-15: max was
  12:47:58 while the time was 12:54:10, with no change in between.

Running the sync automatically on entry, as the code stands, would cause three problems:
1. In steady state no row changes, so the debounce never engages. Every entry would
   enqueue a full `GET /me/albums` page walk (97 albums = 2 pages per entry).
2. The server has no in-flight notion. Two tabs, or an entry made during a running sync,
   each enqueue a job. SQS delivery is also at-least-once.
3. The client polls up to 10 × 2 s waiting for a `last_synced_at` advance that never
   comes when nothing changed. The loop also has no cancel on unmount.

**Order.**
- `SpotifyUserClient.get_saved_albums` unwraps each `{added_at, album}` item and drops
  `added_at`.
- PULL appends at `MAX(position)+1`, so the board order is first-sync order, not
  saved order.
- The board splits the bucket into `myblog_added` ("내가 넣은") and `preexisting` ("기존")
  sections (`BucketBoard.tsx`, `libMine`/`libExisting`), with a source pill on every
  cover. The library bucket gets no sort/group controls.

**Research.**
- The library bucket has `research_mode='off'`. Production: 97 albums, 41 with a `done`
  note, 56 with no `album_research` row.
- Covers in the library bucket receive no `research` prop, and the library albums are
  excluded from `researchAlbumIds`.
- Dedupe is already structural:
  - `UNIQUE (album_id, prompt_version)` (`uq_album_research_album_prompt`, verified in
    production) + `ON CONFLICT DO NOTHING` in `ResearchService.enqueue_album`.
  - The poller claims one row at a time with `FOR UPDATE SKIP LOCKED`, and re-claims a
    stale `running` row only after 20 min.
  - `PROMPT_VERSION = "v2"` exists in `myblog_backend/app/services/research_service.py`
    and in `scripts/research_poller.py`. All 88 production rows are `v2`.
- The worker inserts PULLed items with raw SQL, so `add_item`'s research enqueue never
  sees them.

**Cover overlap.**
- `.bb-tile-mark` (✎, `styles/member/widgets.css`) is 26×26 at `left:6px; bottom:6px; z-index:1`.
- `.rsh-cover-badge` (research dot, `styles/research.css`) is 16×16 at the same corner
  with `z-index:2`.
- The dot spans 6–22 px and the ✎ glyph's centre sits at 19 px, so a click on the ✎
  lands on the dot and opens the research note instead of toggling the mark. The comments
  in both rules record that the corner was knowingly shared and the stacking only made
  explicit.

## Target state

- **V61** (additive):
  - `spotify_library_albums.spotify_added_at TIMESTAMPTZ NULL`.
  - New table `spotify_library_sync_runs (bucket_id PK → review_buckets ON DELETE CASCADE,
    requested_at, started_at, finished_at, last_outcome)`. Exactly one row per library
    bucket.
  - One-time `UPDATE review_buckets SET research_mode='all' WHERE kind='spotify_library'`.
- **Backend `POST /spotify-library/sync`** — one conditional `UPDATE … RETURNING` on the
  runs row decides the result (row lock serialises concurrent tabs):
  - `queued`: never requested; or the last run finished and is older than 30 s; or a
    request is stale (> 5 min without finishing — lost message or crashed worker).
    `requested_at` is set and the job enqueued. If the SQS send fails, `requested_at` is
    restored, so a lost send cannot fake an in-flight run for 5 min.
  - `in_flight`: a run is requested and not yet finished. No enqueue.
  - `debounced`: the last run finished within 30 s. No enqueue.
- **Backend `GET /spotify-library/state`** adds:
  - `sync_requested_at`, `sync_finished_at` and `sync_in_flight`;
  - per album, `spotify_added_at`.
  `last_synced_at` keeps its meaning.
- **Worker `run_library_sync`:**
  - It claims the run with `started_at` (a conditional UPDATE, so a second concurrent
    delivery skips) and always writes `finished_at` + `last_outcome` in `finally`, even
    when nothing changed.
  - A delivery whose request has already been serviced is skipped.
  - `spotify_added_at` is refreshed for every saved album on every pass, in one bulk
    UPDATE sorted by `album_id`, writing only rows where the value differs.
  - When the bucket's `research_mode='all'`, every bucket album with **no
    `album_research` row of any version** is inserted as `queued` (one `INSERT … SELECT
    … WHERE NOT EXISTS`, `ON CONFLICT DO NOTHING`). The any-version guard means the
    worker's copy of the prompt version can never create a second note for an album.
- **Front:**
  - `useSpotifyLibrary` requests a sync on every board entry while the tab is visible;
    a hidden tab waits for `visibilitychange`.
  - It polls `state` only while the server reports `sync_in_flight`, or until
    `sync_finished_at` passes the request. The poll pauses while hidden, is cancelled on
    unmount, and is capped.
  - The library is one list with sort/group controls. The default is `저장 최신순`; the
    other orders are 저장 오래된순, 발매 최신, 발매 오래된, and 인기, and grouping is by
    artist or genre. There is no source split or source pill.
  - Library covers carry the research dot and the bucket's research-mode control.
  - The ✎ and the research dot sit side by side, so the corners no longer overlap.

## Steps

Step 1 is independent of 2–4 (**parallel**). Steps 3a and 3b both depend only on Step 2 and
are additive to each other (**parallel**). Step 4 depends on 3a + 3b. The owner asked in
session (2026-10-15) for all parallelisable work to proceed in this session.

### Step 1 — Cover overlap: ✎ and research dot (front, parallel)

Move `.rsh-cover-badge` beside the ✎ (`left: 38px`; `48px` on coarse pointers where the ✎
is 36 px), vertically centred on it. Keep the z-order comments truthful.

**Verification**:
- `pnpm lint && pnpm exec astro check && pnpm test`
- Real-browser hit-test: `document.elementFromPoint` at the ✎ centre returns `.bb-tile-mark`,
  and at the dot centre returns `.rsh-cover-badge`, both before the fix (expected: dot) and
  after, on desktop and on a coarse-pointer emulation.

**Rollback**: revert the front PR.

---

### Step 2 — V61 schema (shared_db)

The additive migration above: the column, the runs table, and the `research_mode` flip. The
canonical schema and models are regenerated. Applied to the Neon test branch and to
production in the same session (reference-neon-test-branch-migration-drift), **before** any
3a or 3b deploy.

**Verification**:
- `pytest` (`PYTHONPATH=src`)
- `\d spotify_library_sync_runs` and `\d spotify_library_albums` on prod + test
- library `research_mode` = `all`

**Rollback**: down-migration in the file header (drops the table + column, sets the mode back to `off`). Rule 4 — production rollback needs owner approval.

---

### Step 3a — Worker: run claim, added_at, research enqueue (parallel with 3b)

As in Target state. `get_saved_albums` keeps `added_at` on each returned album dict
(`_added_at`), which the other caller (`lyrics_member_demand_service`) ignores.

**Verification**:
- `pytest`, including real-engine tests (feedback-sa-session-lifecycle-mock-blind) for:
  - the claim, and the skip when a run is already serviced;
  - `finished_at` stamped on a no-change pass and on `needs_reauth`;
  - `spotify_added_at` written;
  - research rows inserted once and not again on a second pass;
  - no row inserted for an album that already has a note of another prompt version.
- Mutation check on each new test.

---

### Step 3b — Backend: sync gate + state fields (contract, parallel with 3a)

As in Target state:
- `SpotifyLibrarySyncResponse.status` gains `in_flight`;
- `SpotifyLibraryStateResponse` gains `sync_requested_at`, `sync_finished_at` and
  `sync_in_flight`;
- `SpotifyLibraryAlbumState` gains `spotify_added_at`;
- `openapi.json` is regenerated.

The contract order is service → workspace → front (additive). `reviewer` is mandatory.

**Verification**:
- `check`, `test`, `contract`, `integration` green.
- Real-engine test: two concurrent POSTs → exactly one `queued`.
- A failed send restores `requested_at`.
- Stale request → `queued`.
- No new route, so `infra/apigateway.tf` is unchanged (verified by grep).

---

### Step 4 — Front: auto-sync on entry, one sorted list, research on library covers

As in Target state. `api.gen.ts` is regenerated from the merged workspace contract.

**Verification**:
- `pnpm lint && pnpm exec astro check && pnpm test`, with a hook test for:
  - one POST per entry;
  - no POST while hidden;
  - poll stops on unmount;
  - `in_flight` polls, `debounced` doesn't.
- Real-browser clickthrough on production after deploy:
  - entering the board fires exactly one POST (network panel);
  - re-entering within 30 s → `debounced`;
  - two tabs → one `queued` + one `in_flight`;
  - default order matches Spotify's 최근 추가됨;
  - each sort option reorders;
  - the research dot shows on library covers.

---

## Open questions

None open. The three that were raised are settled in the decisions log.

## Decisions log

| Date | Decision | Step |
|------|----------|------|
| 2026-10-15 | "최신순" = Spotify saved time (`added_at`), not release date. Release-date sorts stay as options. (owner) | 2, 3a, 4 |
| 2026-10-15 | Auto-research covers every library album: the existing 56 un-noted plus all future PULLs. Dedupe was verified in production before committing (unique constraint + `SKIP LOCKED` claim). (owner) | 2, 3a |
| 2026-10-15 | Sync on **every** entry, not on a staleness threshold. Duplicates are prevented server-side (in-flight gate + 30 s post-finish debounce), not by skipping entries. (owner) | 3b, 4 |
| 2026-10-15 | Worker enqueues research with an any-version `NOT EXISTS` guard instead of importing the backend's `PROMPT_VERSION`, so the third copy of the constant cannot cause a duplicate note. | 3a |
