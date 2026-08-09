# DATA-multidisc-track-order: capture `disc_no` and stop colliding multi-disc tracklists

- **Status**: draft
- **Owner**: 오너
- **Created**: 2026-08-09
- **Plan row**: `plan.md` → DATA-multidisc-track-order

---

## Goal

Every album-tracklist read path currently orders by `track_no ASC NULLS LAST` alone. Because Spotify
restarts `track_number` at 1 on each disc, any multi-disc release collides at every `(disc, track_no)`
pair and falls back to arbitrary `created_at`/`id` insertion order to break the tie. This RFC adds a
`disc_no` column, backfills it for the releases that actually collide today, teaches ingestion to capture
it going forward, and switches every ordering site to `(disc_no, track_no)`.

When this RFC is done, a multi-disc album's tracklist reads disc 1 in full, then disc 2, on every surface
that lists tracks — search results, the album detail page, and the playback-bucket queue expansion.

## Non-goals

- **No UI for disc numbers.** No "Disc 1 / Disc 2" section headers or badges. This is an ordering-
  correctness fix only; a disc-label display is a separate, future, front-end-only change if ever wanted.
- **No full-catalog backfill.** Only the releases that collide under the current single-key `track_no`
  ordering get a Spotify re-fetch. Every future sync captures `disc_no` naturally via the Step 2 twin fix,
  so single-disc albums (the overwhelming majority) never need a backfill row at all — their `track_no`
  values are already unique and `disc_no IS NULL` on both sides of a tie changes nothing.
- **No change to `track_no` semantics.** `track_no` keeps meaning "position within its disc," exactly what
  Spotify returns. `disc_no` is additive.
- **No retroactive fix for compilations without a true "disc" concept** (e.g. classical box sets that
  Spotify itself only exposes as one disc with a huge `track_no` range) beyond whatever `disc_number`
  Spotify's API reports for them — if Spotify says disc 1, we store disc 1, even if the useful ordering
  signal for a listener would be something else (movement number, work grouping). That is out of scope.

## Current state

Live-data spot check (2026-08-09, `docs/plan.md`) found **77 of 3,313 albums (~2.3%)** with a repeated
`track_no` under `GROUP BY album_id, track_no HAVING count(*) > 1` — both classical multi-work
compilations and clean 2-disc mainstream releases (Nirvana *In Utero (Deluxe Edition)*, *Hamilton* OBC,
*SOS Deluxe: LANA*, *SWAG II*, Rolling Stones *Forty Licks*). Re-audited fresh for this draft (2026-08-09):

1. **No `disc_no`/`disc_number` column exists anywhere.** `myblog_shared_db/src/myblog_shared_db/models.py:273-321`'s
   `Track` model has `id, album_id, title, track_no, duration_sec, spotify_id, isrc, views, ext_refs,
   created_at` — no disc column. `grep -rniE "disc_no|disc_number"` across all 50 migration files
   (`V2`…`V51`) returns zero hits: it was never added, not dropped. `tests/canonical_schema.sql:265-279`'s
   `tracks` DDL agrees.

2. **Both ingestion twins read only `track_number`, and `disc_number` is discarded before it ever reaches
   a typed field** — not just unused, structurally absent from the parse layer:
   - `myblog_music/app/repositories/track_repo.py:163` — `track_no = t.get("track_number")`, used at
     `:173`/`:181` to populate `Track.track_no` on construction.
   - `myblog_worker/worker/service/sync_service.py:174` — `no=t.get("track_number")`, later written via
     raw-SQL upsert at `:287-296` (`INSERT INTO tracks (..., track_no, ...)`).
   - `myblog_worker/worker/clients/spotify_client.py` has no track model at all — raw Spotify dicts pass
     through untyped, so `disc_number` in the API response is simply never read out of the dict.
   - `myblog_music/app/domain/schemas.py:214-222`'s `CandidateTrackItem` (the candidates → SQS → worker
     contract) has `track_number: Optional[int] = None` but no `disc_number` field — the twin gap extends
     into the SQS message shape, not just the two repos.

3. **Four ordering sites need the `(disc_no, track_no)` switch, not the one the plan row named** (a full
   re-audit — the plan row's citation of `bucket_service.py` was accurate but partial):
   - `myblog_backend/app/services/bucket_service.py:1044-1050` — `expand_album_source` (playback-bucket
     queue expansion): `.order_by(Track.track_no.asc().nullslast(), Track.created_at.asc(),
     Track.id.asc())`.
   - `myblog_music/app/repositories/track_repo.py:23` — `TrackRepository.get_by_album`:
     `.order_by(Track.track_no.asc().nullslast())`.
   - `myblog_music/app/repositories/track_repo.py:132` — `TrackRepository.list_by_album_ids`:
     `.order_by(Track.track_no.asc().nullslast())`.
   - `myblog_music/app/repositories/track_repo.py:110-115` — `TrackRepository.list_top_tracks_by_artist`:
     `track_no` is the trailing tiebreak after `views DESC, popularity DESC, release_date DESC`; still
     collides when the leading keys also tie.

   No raw-SQL `ORDER BY track_no` sites exist outside the ORM — all four are `.order_by(...)` calls, so the
   fix is mechanical once the column exists.

4. **Confirmed real interleaving, not adjacent duplicates.** Pulling *In Utero (Deluxe Edition)* under the
   current `ORDER BY track_no ASC NULLS LAST, created_at` shows disc 1 "Serve The Servants" and disc 2
   "Serve The Servants - 2013 Mix" both at `track_no=1` with identical `created_at` (same sync batch), so
   the tie falls through to arbitrary `id` (UUID) order — the 2013 Mix track sorts first today.

## Target state

- `tracks.disc_no INTEGER NULL` exists, populated from Spotify's `disc_number` on every future sync.
- The 77 (as of 2026-08-09; re-measured at Step 2 kickoff, see below) currently-colliding albums are
  backfilled via a one-off Spotify re-fetch keyed on `spotify_id`.
- All four sites in Current State §3 order by `(disc_no ASC NULLS LAST, track_no ASC NULLS LAST, ...)`.
- `In Utero (Deluxe Edition)` disc 1 "Serve The Servants" sorts before disc 2's "Serve The Servants - 2013
  Mix".
- OpenAPI/contract/frontend types reflect the new field; no frontend behavior changes since ordering is
  entirely server-side.

## Steps

Each step is independently mergeable; per rule 5, each is its own session unless the owner says otherwise.
Steps 2–4 depend on Step 1 having reached prod first (nullable column, no default — nothing reads or
writes it until Step 2 ships, so Step 1 alone is a no-op in behavior).

### Step 1 — `myblog_shared_db`: add `tracks.disc_no`, apply to prod before merge

Per `reference-shared-db-cross-repo-rollout` and `docs/contracts/README.md`'s schema-change procedure:

- `migrations/V52__add_tracks_disc_no.sql` (confirm `V52` is still the next free number at implementation
  time — check for parallel-session collisions): `ALTER TABLE tracks ADD COLUMN disc_no INTEGER;`
- `models.py`: `Track.disc_no = Column(Integer, nullable=True)`.
- Regenerate `_generated_schema.sql`; mirror `tests/canonical_schema.sql` (diff both before commit —
  `reference-schema-mirror-drift-unenforced` — the two have drifted before).
- `pyproject.toml` version bump (currently `0.38.0` → `0.39.0`).
- Apply the migration to Neon prod **and** the test branch before merging the shared_db PR (`reference-database-url-psql`,
  `reference-neon-test-branch-migration-drift`) — a nullable column with no default is safe to add live.

**Verification**: `SELECT data_type, is_nullable FROM information_schema.columns WHERE table_name='tracks'
AND column_name='disc_no'` returns `integer / YES` on both prod and the test branch. `pytest` in
`myblog_shared_db` green.

**Rollback**: `ALTER TABLE tracks DROP COLUMN disc_no;` — nothing reads or writes it yet, zero blast
radius.

### Step 2 — backfill known collisions + twin ingest fix (`myblog_music` + `myblog_worker`)

Two parts, same step (the backfill target set depends on the twin fix's field name/shape being settled
first, and both need the Step 1 column live):

**2a — twin ingest fix.** Both mapping sites start reading `disc_number` alongside `track_number` and
populate `Track.disc_no`:
- `myblog_music/app/repositories/track_repo.py:163` area — `disc_no = t.get("disc_number")` alongside the
  existing `track_no` line, threaded into the same `Track(...)` construction at `:173`/`:181`.
- `myblog_worker/worker/service/sync_service.py:174` area — `disc=t.get("disc_number")` alongside `no=`,
  threaded into the `INSERT INTO tracks (..., disc_no, ...)` upsert at `:287-296`.
- `myblog_music/app/domain/schemas.py:214-222` — `CandidateTrackItem` gains `disc_number: Optional[int] =
  None` so the candidates → SQS → worker contract (`docs/contracts/sqs-album-sync.md`) carries the field
  end to end instead of dropping it at the music side before it ever reaches the worker.
- Requires shared_db pin bump (git-SHA pin, not a tag — `reference-shared-db-cross-repo-rollout`'s tag
  convention is broken) to the Step 1 merge SHA in both `myblog_music` and `myblog_worker`.
- Sweep check (per `feedback-cross-repo-twin-drift-sweep`): confirmed no third mapping site exists —
  `spotify_client.py` in `myblog_worker` has no track model, so there is no additional typed layer to miss.

**2b — one-off backfill for existing collisions.** Re-run the Current State §1 collision query
(`GROUP BY album_id, track_no HAVING count(*) > 1`) at kickoff — the 77/3,313 count is from 2026-08-09 and
will have drifted with continued ingest; do not reuse the stale number as the backfill's actual work list.
For each flagged album:
- Fetch the album's tracks fresh from Spotify (`GET /albums/{id}/tracks`, paginated) — the value is not
  locally computable, `disc_number` was never stored.
- Match returned tracks to existing rows by `spotify_id`; build an in-memory `{spotify_id: disc_number}`
  map.
- **Do not hold a DB transaction across the Spotify fetch loop** (recurring bug class — "idle-in-transaction
  caused Neon `ProtocolViolation`," lyrics-pipeline precedent). Shape: read the flagged album/track ids →
  close that session → do the Spotify fetches → open a fresh short write session per album to apply the
  `UPDATE`.
- Scope is 77 albums as of today; Spotify request volume is negligible against `reference-spotify-extended-quota-irreplaceable`'s
  irreplaceable-quota concern — no rate-limit design needed at this size.
- Per `necessity-gate-reviews`: do **not** extend this to the full 3,313-album catalog. Only the actually-
  colliding set gets a backfill row; every future sync gets `disc_no` for free from 2a.

**Verification**: re-run the collision query restricted to the backfilled album ids — each now has a
non-`NULL` `disc_no` that actually differentiates the tie (spot check *In Utero (Deluxe Edition)*: disc 1
"Serve The Servants" → `disc_no=1`, disc 2 "Serve The Servants - 2013 Mix" → `disc_no=2`). A track synced
after the 2a deploy has non-`NULL` `disc_no` without needing a backfill row. `pytest` green in both repos.

**Rollback**: 2a — revert the pin bump and mapping-site changes; the column stays nullable and unused,
harmless. 2b — the backfill only sets a nullable column on existing rows; `UPDATE tracks SET disc_no =
NULL WHERE id = ANY(:backfilled_ids)` fully reverses it if ever needed.

### Step 3 — switch every `ORDER BY` to `(disc_no, track_no)`

All four sites from Current State §3, in the same PR since they're mechanical and share one shared_db pin
bump (the ORM's `Track.disc_no` attribute needs to exist, which Step 1 already shipped):

- `myblog_backend/app/services/bucket_service.py:1044-1050`
- `myblog_music/app/repositories/track_repo.py:23` (`get_by_album`)
- `myblog_music/app/repositories/track_repo.py:132` (`list_by_album_ids`)
- `myblog_music/app/repositories/track_repo.py:110-115` (`list_top_tracks_by_artist` — `disc_no` inserted
  ahead of `track_no` in the existing trailing-tiebreak position, other leading keys unchanged)

Pattern: `.order_by(Track.disc_no.asc().nullslast(), Track.track_no.asc().nullslast(), ...)` (existing
trailing tiebreaks after `track_no` unchanged).

**Verification**: re-run the *In Utero (Deluxe Edition)* pull under the new ordering — disc 1 "Serve The
Servants" now sorts before disc 2's "Serve The Servants - 2013 Mix". `pytest` in both repos green.
Real-browser check of the album detail page and the playback-bucket queue expansion for one backfilled
album (`/api/music/search/unified` is DB-only, so this is a pure read-path check, no Spotify call
involved).

**Rollback**: revert the `order_by` change in the four sites. Reintroduces the known-documented ordering
bug; no data loss, since `disc_no` values already backfilled/captured are untouched.

### Step 4 — OpenAPI re-export → contract merge → frontend type regen

- Backend/music `openapi.json` regen picks up `disc_no` on any `Track`-shaped response schema.
- Workspace `merge-contract.yml` fires per merged service PR — per `reference-workspace-contract-merge-order`,
  merge one resulting `chore:` PR and close the duplicate if both service PRs land close together.
- `myblog_front`: `pnpm generate:types` → `api.gen.ts` exposes `disc_no`. **No frontend logic change** —
  ordering is entirely server-side; the frontend does not need to read or display the field for this RFC's
  goal.

**Verification**: `pnpm lint` / `pnpm exec astro check` / `pnpm test` green with no behavior diff (per
`feedback-frontend-api-gen-sync`, confirm the regenerated `api.gen.ts` is actually committed, not left
stale).

**Rollback**: revert the contract merge PR and the front type-regen PR; no runtime behavior depended on
the new field.

## Open questions

1. **Full-catalog backfill, later.** If a future feature wants to *display* disc numbers (a UI change, out
   of scope here), the non-colliding albums still won't have `disc_no` populated. Revisit then — do not
   pre-emptively backfill data with no current consumer (`necessity-gate-reviews`).
2. **`disc_no` default for albums Spotify itself reports as single-disc.** Spotify returns `disc_number: 1`
   for every single-disc track, so 2a's twin fix naturally sets `disc_no=1` (not `NULL`) for all newly
   ingested single-disc tracks going forward — only pre-existing rows stay `NULL` until touched by 2b or a
   future re-sync. This asymmetry is intentional and harmless (Non-goals §2), noted here so a future reader
   doesn't mistake it for drift.

## Decisions log

- 2026-08-09 — RFC drafted from the `docs/plan.md` DATA-multidisc-track-order row's confirmed live-data
  spot check. Current-state audit for this draft found the ordering-site count was 4, not the 1 the plan
  row cited (`feedback-rfc-current-state-audit`) — plan row's citation was accurate but partial, not wrong.
  Status remains **draft**; not owner-approved (rule 7 — no self-promotion).
