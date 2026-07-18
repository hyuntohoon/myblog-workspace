# BUG-artist-image-backfill: artist photo NULL backlog + missing backfill loop

- **Status**: done (all 3 steps shipped + prod-smoked 2026-07-19 — worker #74/#75, infra ws #647 applied; weekly `still_null ≈ 0` stays as an observation gate)
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

### Step 1 — sentinel + shared enrich routine + batch fallback (worker) — ✅ DONE 2026-07-19 (worker #74 + test-fix #75)

Extract the enrich block from `sync_service.py` into a reusable
`enrich_artists(spotify_ids: list[str])` routine: chunk 50 → `get_artists_batch` → on batch
error, fall back to per-id `GET /artists/{id}` → write `photo_url` (or `''` sentinel when
`images` is empty), genres, followers, popularity. Rows sorted by conflict key before write
(CLAUDE.md upsert rule). Narrow the in-sync predicate to `photo_url IS NULL`.

**Verification**: worker pytest (new unit: no-image artist → `''` written, second run skips it;
batch-403 → individual fallback used); local run against TEST_DB.

### Step 2 — one-shot backlog job (worker, same PR as Step 1 allowed) — ✅ DONE 2026-07-19 (worker #74; prod one-shot executed)

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

### Step 3 — weekly sweep (infra + worker trigger) — ✅ DONE 2026-07-19 (ws #647, applied)

EventBridge schedule (weekly) → existing worker Lambda with the Step-2 job payload.
`infra/` change: rule + target + permission; full `terraform plan`, no `-target`.

**Verification**: `terraform plan` clean; after first scheduled run, the Step-2 SQL shows no
accumulation (`still_null` stays ≈ 0 week-over-week).

**Shipped**: `worker-artist-photo-backfill`, `cron(0 20 ? * SUN *)` (1 h after the saved-tracks
full reconcile), constant input `{"job":"artist_photo_backfill"}` → blogWorkerLambda. Full plan
= exactly 3 add / 0 change / 0 destroy; applied same day. Post-apply smoke: `describe-rule`
ENABLED + target input verified, manual `lambda invoke` → 200 with DB unchanged (still_null 0,
sentinel 460 / 5,107) — expected no-op. First scheduled run = Sun 20:00 UTC; weekly
`still_null ≈ 0` (denominator = all `artists` rows) remains as the observation gate.

## Open questions

1. **App mode confirmation** (owner, dashboard) — Extended Quota Mode or Dev Mode? Blocks
   nothing here (fallback covers both) but sets the urgency of the fallback path and feeds
   FEAT-member-player risk. 
2. **Job transport** — RESOLVED 2026-07-19 (Step 2): `{"job": "artist_photo_backfill", "limit"?}`
   routed in both the EventBridge constant-input check and the SQS record-body section
   (`lyrics_incremental` pattern) — Step 3's weekly rule reuses the payload as-is.
3. **`ab677269`-prefix rows (109) + ~10 non-scdn singletons** — inspect during Step 2; decide
   re-enrich or leave. Blocks nothing.

## Decisions log

| Date | Decision | Step |
|------|----------|------|
| 2026-07-18 | Owner: 3-piece set (one-shot + sentinel + weekly sweep + individual-GET fallback); S3 mirroring rejected | all |
| 2026-07-19 | Job transport = `{"job": "artist_photo_backfill"}` via EventBridge + SQS body routing (OQ2) | 2 |
| 2026-07-19 | Steps 1+2 shipped (worker #74; #75 test-only fix — sync integration tests' spotify patch target no longer covered the extracted enrich, CI-only failure). Prod one-shot: still_null 463→**0**, sentinel 0→**460**, 3 real photos filled. Sentinel ground-truthed vs live API (popularity-63 artist genuinely `images: []`) — backlog was overwhelmingly "Spotify has no artist image", now permanently excluded from re-fetch. Gate met (still_null ≈ 0, denominator = 5,107 artists) | 1+2 |
| 2026-07-19 | Step 3 shipped + applied (ws #647): weekly rule `cron(0 20 ? * SUN *)`, plan 3/0/0, post-apply manual invoke = clean no-op. RFC done; weekly still_null ≈ 0 observation gate + OQ1 (owner app-mode check) remain | 3 |
