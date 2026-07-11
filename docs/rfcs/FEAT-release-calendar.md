# FEAT-release-calendar: New-release calendar (신보 캘린더)

- **Status**: accepted (2026-07-11, owner in-session approval; discovery re-opened same session — see Decisions log)
- **Owner**: TBD
- **Created**: 2026-07-06
- **Plan row**: `plan.md` → FEAT-release-calendar
- **Absorbs**: Frozen idea `FEAT-new-release-feed` (plan.md, no RFC) **and** the
  parallel 2026-07-06 draft RFC `FEAT-new-release-feed` (6a886a8, branch
  discarded 2026-07-07 — its probe findings and home-card scope folded in here
  as Track A + the Step 5 redesign)

---

## Goal

Two public surfaces (no user concept), fed by the same catalog:

1. **Home "새 앨범" card (Track A)** — full-length albums released in the
   **last 30 days** by high-popularity catalog artists, ranked by artist
   popularity, with a reviewed-artist marker. **DB-only, no new ingestion**:
   the daily `album_ingest` job has been landing exactly this data since
   2026-06-10 (see Current state).
2. **Calendar page (Track B)** — **announced (예정)** and **released (발매)**
   albums / EPs / singles for a watchlist of artists derived from our own
   catalog. Upcoming entries come from MusicBrainz future-dated release data;
   release-day confirmation reuses the existing `album_ingest` discography
   sweep (Step 5). The calendar read path is **DB-only** (rule #9).

After this RFC: the home page surfaces what just dropped, and a visitor can
open a calendar view and see what is coming for the artists this blog covers.

Owner decisions locked 2026-07-06: (1) v1 is a public shared calendar — no
per-user subscriptions; (2) "공표" means visible on the calendar only — no
notifications / blog-post generation; (3) the **calendar** includes all
release types (album + EP + single), with an empirical noise re-check after
real data accumulates (OQ4); (4) the **home card** is albums only, 30-day
window (surface-specific — decided for the feed, kept as-is under absorption).

## Non-goals

- **Per-user artist subscriptions** — requires a `users` table; follow-on
  after `FEAT-multi-user-accounts` Phase 0 lands (RFC accepted 2026-07-06,
  ws #546). The schema keeps the door open
  (watchlist is server-derived today, a join table later).
- Notifications, e-mail, push, or auto-generated posts about releases.
- Editorial curation of *which* releases matter (possible Editor Buckit
  follow-on, not here).
- A **global** MusicBrainz sweep as the discovery mechanism — empirically the
  global future window is long-tail dominated (see Current state); discovery
  is per-watchlist-artist only.
- User "checked/listened" state (확인) — deferred with subscriptions; v1 status
  is the release lifecycle only (`announced` → `released`).
- **No new Spotify fetch path for the home card** — Track A is a pure DB read
  off the existing ingest; no worker job, no EventBridge rule, no SQS message
  type, no `artist_new_releases` table (the frozen idea's design is
  superseded).
- **No Spotify `/browse/new-releases` integration** — probed 2026-07-06 with
  our app credentials: returns 200 (the app survived the Feb 2026 Dev-Mode
  removals), but the content is editorially abandoned — newest item dated
  2025-07-31, a year stale. Also removed outright for Dev-Mode apps.
- **No coverage expansion beyond catalog artists** (e.g. a "seed famous
  artists" job). Coverage grows as the catalog grows; if it proves thin,
  seeding is a separate later RFC.

## Current state

All claims verified against code + prod DB (2026-07-06 probes; `album_ingest`
code claims re-verified 2026-07-07).

- **A daily Spotify discography sweep already runs.** `infra/eventbridge.tf`
  schedules `{"job":"album_ingest"}` at `rate(1 day)` →
  `myblog_worker/worker/service/album_ingest_service.py` sweeps catalog
  artists with `popularity >= ARTIST_POP_MIN` (60, `worker/core/config.py`),
  pulls each artist's Spotify discography with **`include_groups="album"`
  (full albums only — no singles/EPs)**, keeps releases newer than
  `INGEST_SINCE` (2026-06-10), and enqueues novel albums into the normal
  catalog-sync SQS pipeline. This is load-bearing twice: Track A's data
  already exists, and Track B's release-day confirmation should extend this
  job rather than duplicate it (Step 5).
- **Prod already holds the home card's content.** 120 albums with
  `release_date >= 2026-06-06` (83 `album` / 37 `single`), including pop-95
  artists (Taylor Swift 2026-06-12, Justin Bieber 2026-06-26, Olivia Rodrigo,
  Tyler the Creator, Charli xcx, Madonna …). The singles arrive via other
  catalog paths, not the ingest.
- `artists` (shared_db `models.py`) already carries what the watchlist needs:
  `musicbrainz_id` (partial-unique, `'not_found'` sentinel — see
  `V3__partial_unique_excl_not_found.sql`), `popularity`, `followers`,
  `spotify_id`. Prod counts (2026-07-06, read-only): **4,548** artists total,
  **4,044** with a valid `musicbrainz_id`, **1,518** of those with
  `popularity ≥ 50`.
- Worker already has `worker/clients/musicbrainz_client.py`, driven by the
  EventBridge alias-fill schedule (`infra/eventbridge.tf`, rate(15 minutes)).
  MB etiquette (1 req/s, User-Agent) is established there.
- Spotify access already flows exclusively through the worker (SQS +
  EventBridge); `GET /artists/{id}/albums` is **still available** post the
  Feb 2026 Web API removals.
- No table stores future release dates; `albums` holds released catalog only.
  `albums` has `release_date`, `album_type`, `cover_url`, `popularity`;
  `album_artists` joins to `artists`; `post_albums` / `post_artists`
  (shared_db `models.py`) support a reviewed-artist marker — the home card
  needs **no schema change**.
- **musicApi** (`myblog_music/app/main.py`) registers 3 routers under
  `/api/music/{search,albums,artists}`; no feed or calendar router yet. The
  DB-only pattern to copy is `GET /api/music/search/unified`
  (`app/api/routers/search.py` — `Session = Depends(get_db)`, no Spotify
  client, explicit `Cache-Control` header on 200).
- **Routing already covers both new paths.** `infra/apigateway.tf` routes
  `ANY /api/music/{proxy+}` → musicApi; CloudFront injects `X-Origin-Verify`
  (edge_guard); music reads are public (no JWT) — same posture as unified
  search. **No terraform change for either endpoint.**
- **Front.** The home (`myblog_front/src/pages/index.astro`) is fully
  build-time today (`EditorialHome` island does no runtime fetch). Existing
  music-API calls elsewhere use plain `` fetch(`${MUSIC}/api/music/...`) ``
  (`src/lib/useMusicSearch.ts`) — both surfaces are public reads, so
  `apiFetch` (authed) is not needed. Album detail UI is the `AlbumDetail`
  overlay component (`src/components/member/AlbumDetail.tsx`), not a page
  route.
- **Known data caveats** (shape the queries, don't block them):
  - Near-duplicate releases: same title under 2+ `spotify_id`s (e.g. "ICONIC
    BY MISTAKE" 2026-06-10 and 2026-06-12) → both surfaces must dedup.
  - Classical/compilation noise can carry high composer popularity ("A Summer
    Reverie: Classical Works", pop 75); `album_type = 'album'` filters most of
    it — see OQ6.
- Empirical MusicBrainz probe (2026-07-06):
  - Global 30-day future window ≈ **1,327** releases (**1,207** official) —
    long-tail dominated (sample of 30 official: no artist overlapping our
    catalog's popular tier).
  - Type mix in a 100-release sample: Album 76 / Single 15 / EP 7 — singles
    are a minority of future-dated MB data.
  - `arid:<mbid> AND date:[A TO B]` Lucene queries work (Taylor Swift past
    18 months = 185 hits; her future window = 0 — genuinely nothing announced,
    not a query failure).
  - **Year-only partial dates (`2026`) match date-range queries** — they
    cannot be placed on a calendar day and must be filtered to full
    `YYYY-MM-DD` (or surfaced separately as "date TBA", OQ3).

## Target state

### Track A — home "새 앨범" card

- `GET /api/music/feed/new-releases?days=30&limit=12` (musicApi, new `feed.py`
  router at prefix `/api/music/feed`) returns

  ```json
  {
    "items": [
      {
        "album_id": "…", "spotify_album_id": "…", "title": "…",
        "cover_url": "…", "release_date": "2026-06-26",
        "artists": [{"id": "…", "name": "…", "popularity": 95}],
        "artist_popularity": 95,
        "reviewed_artist": false
      }
    ],
    "window_days": 30,
    "total": 12
  }
  ```

  Query semantics: `album_type = 'album'` AND `release_date >= current_date -
  days`; dedup on (normalized title, primary artist) keeping the row with
  highest album `popularity`, then latest `release_date`; rank
  `artist_popularity DESC, release_date DESC`; `reviewed_artist` = any
  credited artist appears in `post_artists` (or via `post_albums →
  album_artists`). `days` capped (e.g. ≤ 90), `limit` capped (e.g. ≤ 50).
  `Cache-Control` set like unified search.
- The home page renders a "새 앨범" card — a small client island fetching the
  feed at runtime (the home's first runtime fetch; build-time won't do since
  the feed changes daily while the site only redeploys on merge). Covers in a
  horizontal strip, artist + release date caption, reviewed-artist marker;
  fetch failure or 0 items → the card renders nothing (home degrades to
  exactly today's layout).

### Track B — calendar

- New shared_db table `artist_release_events`:
  - `id` PK, `artist_id` FK → `artists.id`
  - `mb_release_group_id` text NULL (dedupe key for MB-discovered entries)
  - `spotify_album_id` text NULL (set on release-day confirmation)
  - `title` text NOT NULL
  - `release_type` text (`album` | `ep` | `single` | `other`)
  - `release_date` date NOT NULL (full dates only in v1)
  - `status` text (`announced` | `released`)
  - `source` text (`musicbrainz` | `spotify`)
  - `first_seen_at` / `updated_at` timestamptz
  - Dedup via NOT-EXISTS guard in the poller, **not** bare `ON CONFLICT`
    against a partial index (memory `reference-onconflict-partial-index-break`).
- Worker: a daily EventBridge-scheduled **MB upcoming poller** — watchlist =
  artists with valid `musicbrainz_id` above a popularity floor (OQ1); one MB
  release-group query per artist over `[today, today + horizon]` (OQ2);
  upserts `announced` rows. Watchlist is fetched → materialized → session
  closed before the external loop (memory
  `reference-db-session-across-long-external-loop`).
- Worker: **release-day confirmation inside `album_ingest`** (not a new job —
  see Step 5): when the daily ingest sees a release by a watchlist artist, it
  flips the matching `announced` row to `released` + `spotify_album_id` (or
  inserts `released` directly for releases never announced in MB). Day-0
  auto-catalog comes free — the ingest already enqueues catalog sync (chunked
  per memory `reference-sqs-fanout-burst-pitfalls`).
- Music API: `GET /api/music/releases/calendar?from=&to=` — DB-only,
  edge_guard read (consistent with other public music reads), returns events
  grouped by date with artist + type + status. Contract exported + merged.
- Front: a public calendar view (month grid or agenda list — design decision
  at Step 7) fed by the new endpoint.

## Steps

**Track A (Steps 1–2) and Track B (Steps 3–7) are independent** — no shared
schema, no shared code path — and Track A is 2 cheap additive steps that ship
visible value first; recommend landing A before B. Within each track, steps
are sequential. Each step independently mergeable; rule 4 (one step per
session) applies as usual.

### Step 1 (Track A) — musicApi feed endpoint + contract

- New `app/api/routers/feed.py` + service-layer query + response schemas;
  register `app.include_router(feed.router, prefix="/api/music/feed",
  tags=["Feed"])` in `main.py`.
- pytest: window boundary (29/30/31 days), `album_type` filter, dedup keeps
  highest-popularity row, ranking order, `reviewed_artist` flag on/off, param
  caps.
- Export `openapi.json` in the myblog_music PR; workspace PR runs
  `tools/merge_openapi.py` and commits the regenerated
  `docs/contracts/openapi.json`.

**Verification**:
```
cd myblog_music && pytest
curl 'http://localhost:8001/api/music/feed/new-releases?days=30&limit=12'   # local
# prod smoke (post-merge): via CloudFront —
curl 'https://www.ratemymusic.blog/api/music/feed/new-releases?days=30&limit=12'
# expect >=1 item; spot-check a known June release (e.g. Taylor Swift 2026-06-12) present,
# no 'single' rows, no duplicate (title, primary artist) pairs.
```

**Rollback**: revert PR (additive route; nothing depends on it until Step 2).

---

### Step 2 (Track A) — front home card

- Regen `src/lib/api.gen.ts` (`pnpm generate:types`) off the merged contract.
- New island (e.g. `src/components/home/NewReleasesCard.tsx`) mounted from
  `index.astro`; plain `` fetch(`${MUSIC}/api/music/feed/new-releases?...`) ``;
  hide-on-empty/error.
- `frontend-design` skill at implementation time (per workspace trigger
  table); real-browser click-through before merge (DoD).

**Verification**:
```
cd myblog_front && pnpm lint && pnpm exec astro check && pnpm build
# real-browser click-through: card renders covers, reviewed marker, console 0,
# card absent when the API is blocked (degradation path).
# prod smoke (post-deploy): home shows the card with current releases; console 0.
```

**Rollback**: revert PR (island removal restores today's home exactly).

---

### Step 3 (Track B) — shared_db `artist_release_events` migration

Plain `V{N}__artist_release_events.sql` + ORM model + version bump. Rollout
order per memory `reference-shared-db-cross-repo-rollout`: migration → prod
apply (pre-merge, owner-approved) → service pin bumps land with Steps 4/6.

**Verification**:
```
cd myblog_shared_db && PYTHONPATH=src pytest   # schema parity
psql "$DATABASE_URL" -c "\d artist_release_events"
```

**Rollback**: `DROP TABLE artist_release_events` (no consumer yet at this step).

---

### Step 4 (Track B) — worker MB upcoming poller (announced path)

New EventBridge rate(1 day) rule → worker handler: load watchlist, query MB
release-groups per artist (`arid` + `firstreleasedate` range — exact
field/endpoint choice probed at implementation, OQ3), filter official +
full-date, upsert `announced` events. Reuses `musicbrainz_client.py`
throttling. At 1 req/s: popularity≥50 tier ≈ 1,518 req ≈ 25 min; full
valid-MBID set ≈ 4,044 req ≈ 68 min — both fit a daily Lambda-chunked batch,
but chunking/timeout design must respect the worker's 120 s limit (fan-out in
SQS chunks like the catalog sync, or an EventBridge-driven cursor).

**Verification**:
```
pytest myblog_worker  # handler unit + upsert idempotency (re-run = 0 new rows)
# one manual prod invoke → SELECT count(*), min/max(release_date) FROM artist_release_events;
```

---

### Step 5 (Track B) — release-day confirm via `album_ingest` (released path)

The absorbed draft's probe showed the daily `album_ingest` job already diffs
Spotify discographies for catalog artists — a separate "release-day confirmer"
job (the original design here) would duplicate it. This step **extends
`album_ingest_service.py`** instead: when the ingest encounters a release
within the calendar window by a watchlist artist, upsert/flip the matching
`artist_release_events` row to `status=released` + `spotify_album_id` (match
by artist + fuzzy title + date proximity; insert `released` directly when
never announced in MB). Catalog sync for novel albums already happens in this
job — no extra enqueue path needed.

Two coverage gaps, resolved at implementation (OQ5):

- **Floor mismatch** — ingest sweeps `popularity ≥ 60`; the calendar watchlist
  floor is OQ1 (proposed ≥ 50). Align the floors or accept that 50–59 artists
  only ever show `announced`.
- **Type gap** — ingest fetches `include_groups="album"` (no singles/EPs),
  while the calendar includes all types. Widen `include_groups` for watchlist
  artists, or accept album-only confirmation in v1 (announced singles/EPs
  would then never flip to `released`).

**Verification**:
```
pytest myblog_worker
# prod: a known release-day album flips status + appears in albums via sync
```

---

### Step 6 (Track B) — music API calendar endpoint + contract

`GET /api/music/releases/calendar?from=&to=` in myblog_music (DB-only,
edge_guard). Export `openapi.json`, merge contract, regen front types.

**Verification**:
```
pytest myblog_music
curl "$MUSIC_URL/api/music/releases/calendar?from=2026-07-01&to=2026-08-01"
```

---

### Step 7 (Track B) — front calendar view

Public page consuming the endpoint. UI shape (month grid vs agenda) decided at
a mockup gate with the owner; `frontend-design` skill applies. Real-browser
click-through pre-merge (DoD).

**Verification**:
```
pnpm lint && pnpm exec astro check  # + CDP click-through incl. 390px mobile
```

---

## Follow-on (explicitly out of this RFC)

- **Personal subscriptions** — after `FEAT-multi-user-accounts` Phase 0: a
  `user_artist_subscriptions` join table; calendar gains a "my artists"
  filter; per-user 확인(checked) state. Separate RFC.

## Open questions

1. **Watchlist floor** (blocks Step 4) — `popularity ≥ 50` (1,518 artists,
   ~25 min/day) vs all valid-MBID (4,044, ~68 min/day). Recommend starting at
   ≥50 and widening if coverage feels thin; the floor is one constant. Note
   the existing ingest floor is 60 (`ARTIST_POP_MIN`) — interacts with OQ5.
2. **Horizon** (blocks Step 4) — how far ahead to query. Recommend 180 days;
   MB entries typically appear ≤2 months before release, so longer horizons
   are nearly free but mostly empty.
3. **MB granularity + partial dates** (blocks Step 4) — release-group
   `firstreleasedate` (dedupes editions, recommended) vs release `date`;
   and whether year-only dates get dropped (recommended for v1) or shown as
   "date TBA". Probe both queries at Step 4 start.
4. **Single-type noise gate** (blocks nothing; review gate after Step 7) —
   owner chose include-all for the calendar. Re-check after **14 days of live
   data**: if singles exceed ~50% of calendar entries **(denominator: all
   `artist_release_events` rows with `release_date` in those 14 days)** and
   the owner finds the view noisy, add a type filter toggle rather than
   dropping data.
5. **Ingest extension coverage** (blocks Step 5) — align `ARTIST_POP_MIN`
   with the watchlist floor (OQ1)? Widen `include_groups` beyond `"album"`
   for watchlist artists so announced singles/EPs can be confirmed, or ship
   album-only confirmation in v1? Widening also changes what the ingest
   catalogs — singles are cheap to sync and searchable later (recommend
   widen), but decide with the floor question as one Step 5 design pass.
6. **Feed noise beyond `album_type='album'`** (blocks nothing; Track A) — is
   artist-pop ranking enough, or do classical/compilation-style albums still
   pollute the top-N? Ship simple, judge on the first prod feed, tighten in a
   follow-up if needed.
7. **Card placement + click behavior** (blocks Step 2 layout only; Track A) —
   where in the home flow (above/below Best New Music), and does a cover
   click open the `AlbumDetail` overlay, the artist page, or Spotify? Owner
   eyeball at implementation; record the answer in the Decisions log.

## Decisions log

| Date | Decision | Step |
|------|----------|------|
| 2026-07-06 | v1 public shared calendar; personal subscriptions deferred until after FEAT-multi-user-accounts (owner) | scope |
| 2026-07-06 | 공표 = calendar visibility only, no notifications (owner) | scope |
| 2026-07-06 | Calendar includes albums + EPs + singles; noise re-check with live data (owner) | OQ4 |
| 2026-07-06 | Home card: albums only, 30-day window (owner; surface-specific — the calendar keeps all types) | Track A |
| 2026-07-06 | Discovery = MB per-artist future queries + Spotify day-0 diff; Spotify `/browse/new-releases` removed Feb 2026 (and content stale — newest 2025-07-31 — for surviving apps), global MB sweep rejected (long-tail) | design |
| 2026-07-07 | Parallel draft RFC `FEAT-new-release-feed` (6a886a8) absorbed (owner): its endpoint + home card become Track A; its `album_ingest` probe redesigns the released path as confirm-on-ingest (Step 5) instead of a new worker job; draft branch discarded | scope |
| 2026-07-11 | Promoted draft → accepted (owner in-session) | status |
| 2026-07-11 | Owner reconcile with #549: the 2026-07-06 discovery lock is **re-opened** — Track B discovery to be **redesigned multi-source** (corroborating hard-ID sources within watchlist scope, e.g. Apple/iTunes pre-order, per #549's Divergences), not MB per-artist + Spotify day-0 only. Track B Steps 3–5 need a design-revision pass before Step 3 starts; Track A is unaffected and still ships first | design |
