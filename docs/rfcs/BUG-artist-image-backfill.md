# BUG-artist-image-backfill: artist photo NULL backlog + missing backfill loop

- **Status**: draft
- **Owner**: 박지훈
- **Created**: 2026-07-18
- **Plan row**: `plan.md` → BUG-artist-image-backfill
- **Origin**: 2026-07-18 UI planning session, area 6. Independent of all other areas — **can ship first.**

---

## Goal

Every catalog artist whose Spotify profile has an image shows that image (ArtistHub masthead,
AlbumDetailView artists block) instead of the LetterTile fallback; artists Spotify has no image
for stop being re-queried on every sync batch; and newly-missed artists get picked up by a
periodic sweep instead of staying NULL forever.

## Non-goals

- **S3 image mirroring / self-hosted cache** — measured 2026-07-18: all 4,644 stored URLs are
  `i.scdn.co`, samples (including 2026-03 cohort) HEAD 200. URL expiry is NOT the failure mode;
  hotlinking is fine today. Mirroring is a resilience option with real pipeline/storage cost and
  no present benefit — rejected by owner (decision 13, 2026-07-18). Revisit only if scdn URLs
  actually start dying.
- Fixing the ~21% of `photo_url` values that are album-cover URLs (`ab67616d…` prefix) — Spotify
  itself serves album art as the artist image for artists without photos; not a bug.
- Any frontend change. The render path is verified working.

## Current state (all verified 2026-07-18, prod)

- **Coverage**: `artists` 5,105 rows; `photo_url` NULL 463 (9.1%). Top-100 by popularity: 0 NULL.
  Top-100 by views: 12 NULL — this is the LetterTile the owner sees. NULL rows include
  popularity-46–62 artists created 05-29 → 06-23, i.e. **3+ weeks old and never filled**.
- **Pipeline verified end-to-end**: fill path exists (worker), read path serializes
  (`myblog_music/app/services/artist_service.py:79`, `album_service.py:122`), prod endpoints
  return `photo_url`, live-browser render OK (CDP, `/artist/957a4f30…`). Not a render/CSP/expiry
  bug.
- **Root cause — no backfill loop**: enrich runs only inside an album-sync batch for that batch's
  artists (`myblog_worker/worker/service/sync_service.py:235-283`:
  `WHERE spotify_id = ANY(:ids) AND (photo_url IS NULL OR photo_url = '')` →
  `spotify.get_artists_batch(chunk)` (50/chunk) → `UPDATE artists SET photo_url, genres,
  followers, popularity`). Artists created outside that moment stay NULL forever:
  - `sync_service.py:137` inserts `(spotify_id, name)` only; if the enrich step later in the
    same run fails (Spotify error, timeout), there is no retry.
  - `myblog_music/app/repositories/artist_repo.py:124-149` `upsert_min` (candidates path) can
    create artists without a photo.
- **Sentinel gap**: when Spotify returns an artist with no `images`, the enrich writes
  `photo_url = NULL` back — indistinguishable from "never tried", so the artist is re-fetched in
  every future batch containing it (waste, no correctness harm).
- **API risk (2026-02 Spotify changes)**: batch `GET /v1/artists` is REMOVED for Development
  Mode apps (enforced 2026-03-09 for existing apps). Empirically our app is unaffected as of
  2026-07-18 (artists created today have popularity/followers 100% filled ⇒ batch + removed
  fields still served ⇒ app behaves as Extended Quota Mode). **Owner to confirm app mode in the
  Spotify dashboard** (also OQ for FEAT-member-player).

## Target state

- One-shot backfill has processed the 463-row backlog; rows Spotify has an image for are filled.
- `photo_url = ''` (empty string) is the persisted sentinel for "Spotify has no image for this
  artist" — enrich and backfill both write it, and the existing
  `photo_url IS NULL OR photo_url = ''` batch predicate is **narrowed to `IS NULL`** so
  sentinel rows stop being re-fetched. (Frontend already treats `''` as falsy → LetterTile.)
- A weekly EventBridge sweep (same trigger style as the MusicBrainz alias fill — which must not
  be blocked by or block it) enriches any `photo_url IS NULL` artists, catching future misses.
- Spotify client has an individual-`GET /artists/{id}` fallback when the batch endpoint errors
  (403/404/410), so a future Dev-Mode enforcement degrades throughput, not correctness.

## Steps

Owner decision (13, 2026-07-18): the full 3-piece set — one-shot + sentinel + periodic sweep,
with individual-GET fallback. Single service repo (worker) + small infra touch → Steps 1–2 are
one PR; Step 3 is the infra PR.

### Step 1 — sentinel + shared enrich routine + batch fallback (worker)

Extract the enrich block from `sync_service.py` into a reusable
`enrich_artists(spotify_ids: list[str])` routine: chunk 50 → `get_artists_batch` → on batch
error, fall back to per-id `GET /artists/{id}` → write `photo_url` (or `''` sentinel when
`images` is empty), genres, followers, popularity. Rows sorted by conflict key before write
(CLAUDE.md upsert rule). Narrow the in-sync predicate to `photo_url IS NULL`.

**Verification**: worker pytest (new unit: no-image artist → `''` written, second run skips it;
batch-403 → individual fallback used); local run against TEST_DB.

### Step 2 — one-shot backlog job (worker, same PR as Step 1 allowed)

A worker-side entry (SQS message type or CLI/管理 script consistent with existing worker job
patterns) that selects `photo_url IS NULL` artists (463 today), runs `enrich_artists` over them.
Respect Neon session rule: materialize the id list, close, then loop the external API, then
short write sessions per chunk.

**Verification** (post-deploy prod smoke):
```
SELECT count(*) FILTER (WHERE photo_url IS NULL) AS still_null,
       count(*) FILTER (WHERE photo_url = '')   AS no_image_sentinel
FROM artists;   -- expect still_null ≈ 0, sentinel > 0
```
Quote before/after counts in the PR comment.

### Step 3 — weekly sweep (infra + worker trigger)

EventBridge schedule (weekly) → existing worker Lambda with the Step-2 job payload.
`infra/` change: rule + target + permission; full `terraform plan`, no `-target`.

**Verification**: `terraform plan` clean; after first scheduled run, the Step-2 SQL shows no
accumulation (`still_null` stays ≈ 0 week-over-week).

## Open questions

1. **App mode confirmation** (owner, dashboard) — Extended Quota Mode or Dev Mode? Blocks
   nothing here (fallback covers both) but sets the urgency of the fallback path and feeds
   FEAT-member-player risk. 
2. **Job transport** — SQS message type vs EventBridge-direct payload for the one-shot: pick
   whichever matches the existing worker job dispatch in implementation; blocks Step 2 shape only.
3. **`ab677269`-prefix rows (109) + ~10 non-scdn singletons** — inspect during Step 2; decide
   re-enrich or leave. Blocks nothing.

## Decisions log

| Date | Decision | Step |
|------|----------|------|
| 2026-07-18 | Owner: 3-piece set (one-shot + sentinel + weekly sweep + individual-GET fallback); S3 mirroring rejected | all |
