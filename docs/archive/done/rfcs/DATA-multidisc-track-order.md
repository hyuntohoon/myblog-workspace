# DATA-multidisc-track-order: capture `disc_no` and stop colliding multi-disc tracklists

- **Status**: **done 2026-09-03** (owner-approved in-session — CLAUDE.md rule #7). Steps 1–3 shipped and
  production-verified 2026-08-16/17, which delivers this RFC's entire stated Goal — every tracklist read
  path now orders by `(disc_no, track_no)`. **Step 4 was dropped in the same decision**, on this RFC's own
  recommendation; see Step 4 and the Decisions log.
- **Owner**: 오너
- **Created**: 2026-08-09
- **Plan row**: dropped on completion (2026-09-03)

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
- The **78** (re-measured against prod 2026-08-16 at Step 2 kickoff; 77 in the 08-09 draft) currently-
  colliding albums are backfilled via a one-off Spotify re-fetch keyed on `spotify_id`.
- All four sites in Current State §3 order by `(disc_no ASC NULLS LAST, track_no ASC NULLS LAST, ...)`.
- `In Utero (Deluxe Edition)` disc 1 "Serve The Servants" sorts before disc 2's "Serve The Servants - 2013
  Mix".
- ~~OpenAPI/contract/frontend types reflect the new field~~ — **struck 2026-08-16**: no consumer exists and
  the field is not auto-derived, so this is a Step 4 owner decision, not a target-state requirement. The
  Goal above is met by Steps 2–3 alone.

## Steps

Each step is independently mergeable; per rule 5, each is its own session unless the owner says otherwise.
Steps 2–4 depend on Step 1 having reached prod first (nullable column, no default — nothing reads or
writes it until Step 2 ships, so Step 1 alone is a no-op in behavior).

### Step 1 — `myblog_shared_db`: add `tracks.disc_no`, apply to prod before merge — SHIPPED 2026-08-16

Per `reference-shared-db-cross-repo-rollout` and `docs/contracts/README.md`'s schema-change procedure:

- `migrations/V53__add_tracks_disc_no.sql` (V52 was already taken by `planned_ratings` by implementation
  time — check for parallel-session collisions): `ALTER TABLE tracks ADD COLUMN disc_no INTEGER;`
- `models.py`: `Track.disc_no: Mapped[Optional[int]] = mapped_column(Integer)`.
- Regenerate `_generated_schema.sql`; mirror `tests/canonical_schema.sql` (diff both before commit —
  `reference-schema-mirror-drift-unenforced` — the two have drifted before).
- `pyproject.toml` version bump (was already `0.39.0` by implementation time → `0.40.0`).
- Apply the migration to Neon prod **and** the test branch before merging the shared_db PR (`reference-database-url-psql`,
  `reference-neon-test-branch-migration-drift`) — a nullable column with no default is safe to add live.

**Verification**: `SELECT data_type, is_nullable FROM information_schema.columns WHERE table_name='tracks'
AND column_name='disc_no'` returns `integer / YES` on both prod and the test branch. `pytest` in
`myblog_shared_db` green.

**Rollback**: `ALTER TABLE tracks DROP COLUMN disc_no;` — nothing reads or writes it yet, zero blast
radius.

### Step 2 — backfill known collisions + ingest fix (`myblog_worker`, optionally `myblog_music`)

> **2a shipped 2026-08-16** (`myblog_worker` #94, `1254c1e`). `AlbumSyncService._collect`/`_write_catalog`
> now reads Spotify's `disc_number` and writes `tracks.disc_no` on every upsert; no shared_db pin bump
> (confirmed at kickoff — raw SQL, worker only imports `genre_mapping`). `pytest` 532 passed / 3 skipped
> (musicbrainz live, network-gated) — up from 525 passed pre-change. Deployed to prod, Lambda
> `blogWorkerLambda` `LastUpdateStatus=Successful` confirmed post-deploy.
>
> **2b shipped and run against prod 2026-08-16** (`myblog_worker` #94 `1254c1e` + #95 `ad93b2f`,
> owner-approved invoke). `DiscNoBackfillService` plus a new paginated `SpotifyClient.get_album_tracks()`
> (needed because the batch `GET /albums` nested-tracks response truncates at 50, which 4 of the 78
> flagged albums hit locally) shipped as a manual-invoke-only Lambda job (`{"job": "disc_no_backfill"}`,
> no EventBridge rule — this population doesn't recur).
>
> First invoke (78 albums): `tracks_matched=2208, tracks_skipped_no_local_row=388, errors=0`, 42s. A
> post-hoc DB check found 2 albums (10 track_no ties) still unresolved — Spotify's market=KR response
> returns a relinked `id` different from what's stored locally, with the ORIGINAL id reachable only via
> the item's `linked_from.id` (the exact pitfall `IsrcBackfillService` already guards against; missed in
> the first cut). Fixed in #95 (resolve each item via `id` OR `linked_from.id` before
> matched/skipped classification) and re-invoked (idempotent — the fetch query only re-selects albums
> still missing `disc_no`): `albums_total=2, tracks_matched=0, tracks_skipped_no_local_row=33`.
>
> **Residual: 2 of 78 albums (Queen's "Sheer Heart Attack (Deluxe Remastered Version)" and "The Game
> (Deluxe Remastered Version)") remain unresolved even after the relinking fix** — direct inspection
> confirmed neither the current `id` nor `linked_from.id` in Spotify's live catalog matches what's stored
> locally for these tracks. This isn't market relinking; the local `spotify_id`s themselves appear
> stale/orphaned (Spotify likely re-issued the album's track objects since our last ingest of these two).
> Fixing it would mean a full re-sync of these 2 albums (touches title/duration/etc, not just `disc_no`)
> or an ISRC-based match — out of scope for this bounded backfill (`necessity-gate-reviews`). **76/78
> albums (97.4%) fully resolved.** These 2 keep their pre-RFC arbitrary tie-break; no regression, same as
> before this RFC. Verified via `In Utero (Deluxe Edition)`: disc 1 "Serve The Servants" (`disc_no=1`)
> now sorts before disc 2's "Serve The Servants - 2013 Mix" (`disc_no=2`) once Step 3's `ORDER BY` change
> lands.
>
> **Corrected 2026-08-16 by a kickoff current-state audit** (`feedback-rfc-current-state-audit`). The
> draft's 2a described a symmetric two-repo "twin fix" with a pin bump in both repos and a third change in
> the SQS contract. Read against `origin/main`, all three of those claims are wrong; the corrected shape is
> below and the superseded text is recorded in the Decisions log. The audit did **not** change 2b's shape,
> only its numbers.

Two parts, same step (both need the Step 1 column live):

**2a — ingest fix.** There is exactly **one live track-ingest site** in the system, and it is in the worker:

- **`myblog_worker/worker/service/sync_service.py:174`** — `_collect` reads the Spotify `GET /albums`
  response's nested `tracks.items` into `track_data` as `no=t.get("track_number")`. Add
  `disc=t.get("disc_number")` alongside it, and thread `disc_no` into the raw-SQL upsert at `:287-296`
  (`INSERT INTO tracks (spotify_id, album_id, title, track_no, duration_sec, disc_no)` + the matching
  `ON CONFLICT (spotify_id) DO UPDATE SET ... disc_no = EXCLUDED.disc_no`). Keep the existing
  `track_data.sort(key=lambda t: t["sid"])` conflict-key sort untouched.
- **No shared_db pin bump for the worker.** The worker's only shared_db import is
  `myblog_shared_db.genre_mapping.attachable_slugs` (verified by grep across `worker/` and `tests/`); it
  writes tracks through raw SQL against the live schema, where `disc_no` already exists from Step 1. Its
  `requirements.txt` pin can stay where it is for this step.
- **`myblog_music/app/repositories/track_repo.py:178`'s `Track(...)` construction is dead code.**
  `upsert_tracks_with_artists_db_only` — the only site in `myblog_music` that constructs or writes a
  `Track` — has **zero callers** in `app/` or `tests/`. Bringing it along is a twin-drift hygiene call, not
  a correctness one, and it is the *only* thing in Step 2 that would require music's pin bump. See the
  pin-gap note under Step 3: music's pin is 20 releases stale, so the bump is a change worth making where
  live read paths actually exercise it (Step 3), not for a dead writer here. **Decide at kickoff; either
  way, say which in the PR body so Step 3 does not inherit an unstated assumption.**
- **`CandidateTrackItem` is out of scope — the draft's premise was false.** `CandidateTrackItem`
  (`myblog_music/app/domain/schemas.py:214-222`) appears in exactly one place, `CandidateSearchResult.tracks`
  — it is a *music HTTP response* schema, not an SQS payload. The album-sync message is
  `SqsClient.enqueue_album_sync(album_ids, market)`: **album IDs only**. Track data never travels through
  SQS; the worker fetches it from Spotify itself, which is why 2a's single worker site is sufficient. Adding
  `disc_number` here would be a consumer-less contract change (forcing an `openapi.json` regen and the full
  `docs/contracts/README.md` procedure) that buys nothing.
- Sweep check (per `feedback-cross-repo-twin-drift-sweep`): no third mapping site exists —
  `spotify_client.py` in `myblog_worker` has no track model, so there is no additional typed layer to miss,
  and `grep -rn "track_number"` across `myblog_worker/worker/` returns `sync_service.py:174` alone.

**2b — one-off backfill for existing collisions.** Re-run the Current State §1 collision query
(`GROUP BY album_id, track_no HAVING count(*) > 1`) at kickoff — every count below is a **2026-08-16
snapshot** and will drift with continued ingest; do not reuse it as the backfill's actual work list.
Measured 2026-08-16 against prod:

| measure | value |
|---|---|
| colliding albums | **78 / 3,445** (2.26%) |
| tracks in those albums | **2,241** |
| flagged albums missing `spotify_id` | **0** |
| flagged tracks missing `spotify_id` | **0** |
| `tracks.disc_no` non-NULL | **0** |
| collision depth | 2-way ×66 · 3-way ×8 · 4-way ×4 |

Re-fetch coverage is therefore 100% — no album falls back to a manual fix. For each flagged album:
- Fetch the album's tracks fresh from Spotify (`GET /albums/{id}/tracks`, paginated) — the value is not
  locally computable, `disc_number` was never stored.
- Match returned tracks to existing rows by `spotify_id`; build an in-memory `{spotify_id: disc_number}`
  map.
- **Do not hold a DB transaction across the Spotify fetch loop** (recurring bug class — "idle-in-transaction
  caused Neon `ProtocolViolation`," lyrics-pipeline precedent). Shape: read the flagged album/track ids →
  close that session → do the Spotify fetches → open a fresh short write session per album to apply the
  `UPDATE`.
- Request volume is ~100 calls (78 albums × 1–2 pages at `limit=50`) — negligible against
  `reference-spotify-extended-quota-irreplaceable`'s irreplaceable-quota concern, so no rate-limit design
  is needed at this size.
- Per `necessity-gate-reviews`: do **not** extend this to the full 3,445-album catalog. Only the actually-
  colliding set gets a backfill row; every future sync gets `disc_no` for free from 2a.
- **UPDATE only, never INSERT.** 4 of the 78 flagged albums sit at exactly `tracks=50`, the Spotify
  album-nested page limit — they are probably truncated locally. The backfill matches on `spotify_id` and
  updates matched rows only; a returned track with no local row is skipped and counted, not inserted.
  Repairing truncated tracklists is a separate concern and out of scope here (note the count in the PR
  body so it is not silently lost).

**Verification**: re-run the collision query restricted to the backfilled album ids — each now has a
non-`NULL` `disc_no` that actually differentiates the tie (spot check *In Utero (Deluxe Edition)*, 43
tracks / 2-way collisions: disc 1 "Serve The Servants" → `disc_no=1`, disc 2 "Serve The Servants - 2013
Mix" → `disc_no=2`). A track synced after the 2a deploy has non-`NULL` `disc_no` without needing a
backfill row. `pytest` green in `myblog_worker` (and `myblog_music` if its half is taken).

**Rollback**: 2a — revert the mapping-site change; the column stays nullable and unwritten, harmless. 2b —
the backfill only sets a nullable column on existing rows; `UPDATE tracks SET disc_no = NULL WHERE id =
ANY(:backfilled_ids)` fully reverses it if ever needed.

### Step 3 — switch every `ORDER BY` to `(disc_no, track_no)` — SHIPPED 2026-08-17

> `myblog_backend` #157 (`11013e7`) + `myblog_music` #68 (`0ca8444`). All 4 `ORDER BY` sites switched to
> `Track.disc_no.asc().nullslast(), Track.track_no.asc().nullslast()` (leading keys / trailing tiebreaks
> otherwise unchanged). Both repos' shared_db pin bumped to the Step 1 merge SHA `8319a56` (`myblog_music`
> `v0.26.0`/`dd016c4` → `8319a56`; `myblog_backend` `029f8db` → `8319a56`), treated as its own reviewable
> change in each PR: `pytest` run before and after the bump alone in both repos, pass counts identical
> (`myblog_music` 132 passed/8 deselected; `myblog_backend` 664 passed/152 deselected). `pyright` 0 errors
> and `openapi.json` regen produced no diff in either repo (Step 4 not started). PR-CI green in both
> (unit + contract + real-DB integration suites). Verified against prod: direct SQL confirmed *In Utero
> (Deluxe Edition)* sorts disc 1 in full before disc 2; post-deploy, the live `GET /api/music/albums/{id}`
> response for the same album confirmed it end-to-end (disc 1 tracks 1–20, then disc 2 restarts at
> track_no=1). Frontend renders track arrays as returned (`AlbumDetailView.tsx`/`AlbumDetail.tsx` `.map`,
> no client-side sort found), so the API-level check covers the user-visible surface — no frontend PR
> needed. Production smoke 19/19 quoted on both PRs. The 2 unresolved-from-Step-2 Queen albums keep their
> pre-RFC arbitrary tie-break, as documented — not a regression.

All four sites from Current State §3, in the same PR since they're mechanical and share the same
precondition — the ORM's `Track.disc_no` attribute has to exist in the *installed* shared_db, which means
this is the step that actually pays the pin bump:

> **Pin-gap warning (measured 2026-08-16).** The three repos are not on the same shared_db, and one of them
> is far behind:
>
> | repo | pinned shared_db | equals |
> |---|---|---|
> | `myblog_backend` | `029f8dbcb3ff…` (SHA) | V52, one commit before Step 1 |
> | `myblog_music` | **tag `v0.26.0` → `dd016c4`** | **V32-era — 20 releases stale** |
> | `myblog_worker` | tag `v0.26.0` → `dd016c4` | same, but irrelevant (raw SQL, `genre_mapping` only) |
>
> Both `myblog_backend` and `myblog_music` must move to the Step 1 merge SHA **`8319a56`** (git-SHA pin, not
> a tag — `reference-shared-db-cross-repo-rollout`'s tag convention is broken; note that music/worker are
> still *on* a tag, which is how they drifted). Music's jump spans +785 lines / 17 new model classes in
> `models.py`; the diff is additive (deletions are comment and constraint-line moves, no column or class
> removals) and music only imports `Album`, `Artist`, `Genre`, `AlbumGenre`, `Track`, `album_artists_table`,
> `track_artists_table`, so the blast radius looks small — but **treat the bump as its own reviewable change
> within the PR** and run music's `pytest` before and after it, not just after the `order_by` edits. Per
> `feedback-shared-db-pin-vs-venv-drift`, grep the pin rather than trusting the local venv.


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

### Step 4 — OpenAPI re-export → contract merge → frontend type regen — **DROPPED 2026-09-03**

> **DROPPED 2026-09-03 by explicit owner decision** — the owner answered the gate below with "drop it".
> Nothing was implemented for this step; the text is kept because it records *why* the field stops at the
> database. Revisit only alongside the Open Question 1 feature that would actually display disc numbers,
> and treat that as a new decision rather than resuming this step.
>
> **Step 4 is now gated on an explicit owner "yes" and may well be dropped** (corrected 2026-08-16, same
> kickoff audit). The draft assumed the regen would pick the field up on its own; it will not. Music's
> track-shaped response schemas — `TrackItem` (`schemas.py:44`) and `TrackOut` (`schemas.py:93`) — are
> hand-written Pydantic models listing `track_no` explicitly, not ORM-derived, so `disc_no` appears in
> `openapi.json` **only if someone adds the field by hand**. That turns Step 4 from a mechanical re-export
> into a deliberate, consumer-less contract widening: Steps 2–3 deliver this RFC's entire stated Goal
> (correct server-side ordering) without it, the Non-goals already forbid a disc-number UI, and Step 4's own
> text says "No frontend logic change." Under `feedback-necessity-gate-reviews` the default answer is
> **don't ship it** — revisit only alongside the Open Question 1 feature that would actually display discs.
> If the owner does want it, note that this step is a contract touch and therefore requires the `reviewer`
> subagent per CLAUDE.md — which was **not registered in this environment as of 2026-08-16**; resolve that
> gap before starting, not during.

- Adding `disc_no: Optional[int] = None` to `TrackItem` and `TrackOut` is the actual first task, before any
  `openapi.json` regen — the regen reflects the schemas, it does not discover the column.
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
- 2026-08-16 — **owner approved; Status → accepted, promoted to plan.md Active.** Before asking, the
  draft's two load-bearing claims were re-measured against prod rather than carried over
  (`feedback-rfc-current-state-audit`): `information_schema` still reports **zero** `disc_no` /
  `disc_number` columns on `tracks`, and the collision population is **78 of 3,440 albums (2.27%)**
  against the draft's 77 of 3,313 — the same 2.3% rate, so the population tracks catalog growth rather
  than being a one-off import artifact. Both claims hold; no scope change on promotion. Chosen over the
  session's other startable candidates because it is the only open item whose completion depends on
  nothing but implementation — every other Active row is waiting on owner authoring/curation behaviour —
  and because `ARCH-global-playback-experience` Step 4 has just put a play-all / reorder queue on top of
  exactly these `ORDER BY` sites.
- 2026-08-16 — **Step 2 kickoff current-state audit; Steps 2–4 corrected, no code written**
  (`feedback-rfc-current-state-audit`). The two Step 1 abort gates were clean (`disc_number|disc_no` absent
  from both twins on `origin/main`), and 2b's population re-measured to **78 / 3,445 albums, 2,241 tracks,
  zero missing `spotify_id` on either side** — the backfill number held, so 2b's shape is unchanged. Three
  claims in the *draft's* Step 2/4 did not survive the audit and have been rewritten above; recording the
  superseded text here so a later reader can see what changed and why:
  1. **"Both mapping sites" / "twin fix" was wrong about the worker's pin.** The draft required a shared_db
     pin bump in `myblog_music` *and* `myblog_worker`. The worker imports only
     `myblog_shared_db.genre_mapping.attachable_slugs` and writes tracks by raw SQL, so it needs no bump at
     all — the Step 1 column already exists in the schema it writes against.
  2. **The music half is a dead code path.** `upsert_tracks_with_artists_db_only` (`track_repo.py:136`) is
     the only `Track(...)` writer in `myblog_music` and has zero callers. The single live ingest site is
     `myblog_worker/worker/service/sync_service.py:174`. "Twin fix" overstated the work: it is one real
     site plus one optional hygiene edit.
  3. **`CandidateTrackItem` is not on the SQS contract.** The draft justified adding `disc_number` to it as
     making the "candidates → SQS → worker contract carry the field end to end." It is only referenced by
     `CandidateSearchResult.tracks` (a music HTTP response), and `SqsClient.enqueue_album_sync` sends
     **album IDs only** — the worker gets track data from Spotify directly. Dropped from Step 2 as a
     consumer-less contract change.
  A fourth correction fell out of the same read: **Step 4 will not happen by regen.** `TrackItem` /
  `TrackOut` are hand-written Pydantic schemas, so `disc_no` reaches `openapi.json` only if added by hand —
  making Step 4 a deliberate contract widening with no consumer, now gated on an explicit owner yes and
  expected to be dropped. Also recorded under Step 3: the three repos' shared_db pins have diverged, and
  `myblog_music` is **20 releases stale** (tag `v0.26.0` → `dd016c4`, V32-era) against backend's
  `029f8db` — so Step 3, not Step 2, is where that bump gets paid and verified.

- 2026-09-03 — **Step 4 dropped and the RFC closed (owner decision, in-session).** The gate the 2026-08-16
  kickoff audit put on Step 4 was answered "drop it", which matches this RFC's own stated default under
  `feedback-necessity-gate-reviews`: the field has no consumer, the Non-goals already forbid a disc-number
  UI, and Steps 2–3 deliver the whole Goal without it. Dropping it also retires the blocker recorded
  alongside it — Step 4 is a contract touch and therefore requires the `reviewer` subagent. Status
  accepted → done; RFC archived to `docs/archive/done/rfcs/` and the plan.md row dropped.
