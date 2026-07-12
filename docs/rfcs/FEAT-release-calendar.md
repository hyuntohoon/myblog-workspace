# FEAT-release-calendar: New-release calendar (신보 캘린더)

- **Status**: accepted (2026-07-11, owner in-session approval; discovery re-opened same session and **design-revision pass done 2026-07-11** — multi-source, see Decisions log; **revision approved by owner 2026-07-12**. **Track A COMPLETE 2026-07-12** — Step 1 music #53 + ws #605, Step 2 front #267 prod-smoked; **Track B Step 3 shipped 2026-07-12** — V44 prod-applied + shared_db #62; **Step 4 density probe done + OQ1/2/3 decided 2026-07-12** (floor ≥50, 180 d, RG full-date-only); **Step 4 poller SHIPPED + ARMED 2026-07-12** (worker #70 / ws #615, EventBridge bucket rotation live, first ticks clean); **Step 6 calendar endpoint SHIPPED 2026-07-13** (music #54 + contract ws #617 + types front #271, prod-smoked over live poller data) — next = full-cycle density check (~2026-07-13 16:00 KST) → Step 5; Step 7 after Step 6 data accumulates)
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
   catalog. Upcoming entries come from **per-artist multi-source discovery**
   (MusicBrainz future-dated release groups + iTunes pre-order lookups —
   redesigned 2026-07-11, see Track B target state); release-day confirmation
   reuses the existing `album_ingest` discography sweep (Step 5). The calendar
   read path is **DB-only** (rule #9).

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
- Multi-source probe (2026-07-11, live — grounds the discovery redesign):
  - **iTunes per-artist lookup exposes pre-orders as future-dated albums with
    a hard ID**: `lookup?id=<artistId>&entity=album` for As It Is returned
    the announced album "As It Is" with `releaseDate 2026-07-17` and
    `collectionId 1884980968`, six days pre-release. Same keyless iTunes
    Search API the genre pipeline already calls daily (`lookup?upc=`); rate
    etiquette ~20 req/min (`ITUNES_THROTTLE_S` 3.5 s in
    `backfill_genres.py`).
  - **No editorial "coming soon" feed survives**: the Apple marketing-tools
    v2 RSS has no coming-soon feed (404) and the legacy
    `itunes.apple.com/*/rss/comingsoon` endpoint is dead (400). Apple Music
    API proper is developer-token-gated (paid program) — out for v1.
  - iTunes lookup responses carry **no UPC**, so an MB row and an iTunes row
    for the same upcoming album share **no hard key pre-release**; hard-key
    merge across those sources is only possible at catalog confirmation.
  - iTunes `artistId` is resolvable by a **hard-ID chain with no fuzzy name
    match**: any catalog album with `ext_refs.upc` → `lookup?upc=` → the
    collection's `artistId` (the exact call the genre pipeline makes today).

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

### Track B — calendar (discovery redesigned multi-source, 2026-07-11)

Discovery is **multi-source within watchlist scope** (owner re-opened the
2026-07-06 lock on reconcile with FEAT-personal-release-tracking): per-artist
queries against sources that return **hard IDs**, never a global sweep. v1
sources: `musicbrainz` (release-group future dates) + `itunes` (per-artist
pre-order lookup — probed live 2026-07-11, see Current state) + `spotify`
(release-day confirmation via `album_ingest`). Consistency posture lifted
from FEAT-personal-release-tracking's locked strategy: **one row per source
observation, hard-key merge only** (under-merge bias — never fuzzy-merge
rows), display-level soft grouping, catalog confirmation as the
collapse-to-one-truth point.

- New shared_db table `artist_release_events` — **one row per
  (source, source_key) observation**:
  - `id` PK, `artist_id` FK → `artists.id`
  - `source` text (`musicbrainz` | `itunes` | `spotify`)
  - `source_key` text NOT NULL (MB release-group MBID / iTunes
    `collectionId` / Spotify album id) — **UNIQUE(source, source_key)**, a
    full unique so plain `ON CONFLICT` infers it (the partial-index trap of
    memory `reference-onconflict-partial-index-break` doesn't apply; bulk
    upserts still sort rows by the conflict key)
  - `spotify_album_id` text NULL (set on release-day confirmation — the
    cross-source collapse key)
  - `title` text NOT NULL
  - `release_type` text (`album` | `ep` | `single` | `other`)
  - `release_date` date NOT NULL (full dates only in v1)
  - `status` text (`announced` | `released`)
  - `first_seen_at` / `updated_at` timestamptz
- New shared_db table `artist_source_ids` — per-source artist-id resolution
  cache: `artist_id` FK, `source` text, `source_artist_id` text,
  `resolved_via` text, `resolved_at` timestamptz; UNIQUE(artist_id, source).
  v1 rows are `itunes` only (MB/Spotify ids already live on `artists`).
  Resolution = the UPC hard-ID chain probed in Current state; artists with no
  UPC-bearing catalog album stay unresolved and simply skip the iTunes source
  (coverage reported, not fudged).
- **Same-album rows from different sources stay separate rows** (no shared
  hard key exists pre-release). The read path (Step 6) **soft-groups for
  display** on `(artist_id, release_date, normalized title)` — reversible
  presentation logic, not a data merge; a 2-source group can render as a
  corroboration hint. On confirmation the matching rows all receive the same
  `spotify_album_id` and grouping keys on it.
- Worker: a daily EventBridge-scheduled **upcoming poller** — watchlist =
  artists above a popularity floor (OQ1); per artist, one MB release-group
  query over `[today, today + horizon]` (OQ2, ~1 req/s) plus one iTunes
  lookup for `artist_source_ids`-resolved artists (~3.5 s throttle); filter
  official + full-date + future-window; upsert `announced` rows per source.
  Watchlist fetched → materialized → session closed before the external loop
  (memory `reference-db-session-across-long-external-loop`); the two source
  passes fit the worker's 120 s Lambda limit only chunked (decided 2026-07-12:
  EventBridge stateless time-bucket rotation, two rules — see Step 4).
- Worker: **release-day confirmation inside `album_ingest`** (not a new job —
  see Step 5): when the daily ingest sees a release by a watchlist artist, it
  flips the matching `announced` rows (all sources; match by artist + fuzzy
  title + date proximity — a confirm-time match, not a data merge) to
  `released` + `spotify_album_id`, or inserts a `spotify`-source `released`
  row for releases never announced by any source. Day-0 auto-catalog comes
  free — the ingest already enqueues catalog sync (chunked per memory
  `reference-sqs-fanout-burst-pitfalls`).
- Music API: `GET /api/music/releases/calendar?from=&to=` — DB-only,
  edge_guard read (consistent with other public music reads), returns events
  grouped by date with artist + type + status + soft-grouping. Contract
  exported + merged.
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

### Step 2 (Track A) — front home card — **SHIPPED + prod-smoked 2026-07-12 (front #267)**

`NewReleasesCard` inside `EditorialHome` between the BNM hero and Latest (OQ7);
cover click opens the app-wide AlbumDetail overlay (`openAlbum`; host already in
`layout.astro`), artist caption → artist hub, ★ 평론 chip on `reviewed_artist`.
Verified: lint / astro check / build + CDP click-through (overlay open, marker
via fetch-mock — prod top-12 all `false` today, mobile 390×844 + desktop,
dark + light, degradation = renders nothing); prod smoke: card live with 12
releases, bundle marker `EditorialHome.BE6ribxQ.js`, console 0.

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

### Step 3 (Track B) — shared_db release-events migration — **SHIPPED 2026-07-12 (shared_db #62, V44 prod-applied pre-merge)**

V44 = both tables + ORM + parity fixtures + v0.35.0; pytest 91/91; prod
BEGIN…ROLLBACK dry-run → apply → `\d` verified. Workspace `docs/contracts/
schema.sql` mirrored byte-identical in the same-day docs PR.

Plain `V{N}__artist_release_events.sql` — **both tables** of the multi-source
design (`artist_release_events` one-row-per-source-observation +
`artist_source_ids` resolution cache) + ORM models + version bump. Rollout
order per memory `reference-shared-db-cross-repo-rollout`: migration → prod
apply (pre-merge, owner-approved) → service pin bumps land with Steps 4/6.

**Verification**:
```
cd myblog_shared_db && PYTHONPATH=src pytest   # schema parity
psql "$DATABASE_URL" -c "\d artist_release_events" -c "\d artist_source_ids"
```

**Rollback**: `DROP TABLE artist_release_events, artist_source_ids` (no
consumer yet at this step).

---

### Step 4 (Track B) — worker multi-source upcoming poller (announced path) — **SHIPPED + ARMED 2026-07-12 (worker #70 / ws #615)**

**Density probe DONE 2026-07-12** (read-only; top-200 valid-MBID by
popularity — sample floor pop 79; 180-day window; 0 errors, both sources on
all 200; raw artifacts were session-scratchpad-only — these numbers are the
durable record):

- **MB density**: 11/200 (5.5%) with ≥1 future release-group (13 RGs). Hit
  rate flat across pop 79–94 (4–12%/bucket — no collapse), so the ≥50 tier
  (1,530) extrapolates to **~75–105 artists with upcoming entries**.
  Full-date lead time: median 43.5 d / p90 68 d / **max 82 d — nothing real
  beyond 90 d** (91–180 d = year-only placeholders). Partial dates 5/13,
  all bare "2026" placeholders — full-date-only loses nothing placeable.
- **OQ3 head-to-head** (all 11 future-RG artists re-queried at release
  level): **11/11 RG `firstreleasedate` == release `date`** where both
  exist; release-level MISSES 2 announce-stage albums (Gracie Abrams, Sam
  Smith — RG exists, no release rows yet) and adds 10–14× edition rows.
- **iTunes**: UPC-bearing catalog album 157/200 (78.5%, via
  `albums.ext_refs->>'upc'`); `lookup?upc=` resolved **122/200 = 61%** (35
  stored UPCs miss in iTunes → the resolution pre-pass should fall back to
  the next-newest UPC before marking unresolved). 6/122 with future-dated
  entries; **3 iTunes-only finds MB missed (Stray Kids, ENHYPEN, Green Day
  OST — K-pop/OST lanes)**, 3 corroborate MB. Combined 14/200 (7.0%) =
  **+27% coverage over MB alone**.
- Watchlist counts refreshed: valid-MBID 4,208 / ≥50 1,530 / ≥60 985.

**OQ1/OQ2/OQ3 DECIDED 2026-07-12 (owner)**: floor **popularity ≥ 50**;
**query horizon 180 d** (displayable content concentrates ≤90 d); **MB unit
= release-group `firstreleasedate`, full-date-only v1**. Poller
implementation is unblocked — next session.

Then: new EventBridge rate(1 day) rule → worker handler, two source passes
per artist:

- **iTunes artistId resolution pre-pass** for watchlist artists missing an
  `artist_source_ids` row: catalog UPC → `lookup?upc=` → `artistId`
  (hard-ID chain, no fuzzy name match); unresolved artists skip the iTunes
  source.
- **MB**: release-group query per artist (`arid` + `firstreleasedate` range —
  exact field/endpoint choice probed at implementation, OQ3), filter
  official + full-date; reuses `musicbrainz_client.py` throttling. At
  1 req/s: popularity≥50 tier ≈ 1,518 req ≈ 25 min; full valid-MBID set ≈
  4,044 req ≈ 68 min.
- **iTunes**: `lookup?id=<artistId>&entity=album` per resolved artist,
  keep future-dated collections (`ITUNES_THROTTLE_S` 3.5 s ⇒ ≈ 89 min for
  the ≥50 tier — the slower of the two passes).

Upsert `announced` rows per source on UNIQUE(source, source_key). Both
passes exceed the worker's 120 s Lambda limit — chunked fan-out required.

**Fan-out design (DECIDED 2026-07-12, implementation session): EventBridge
stateless time-bucket rotation, two rules — one per source.** SQS chunk
fan-out was rejected: the shared blogSQS queue is the album-sync path, and an
MB/iTunes outage must never clog album sync (the same boundary that keeps
the alias fill on EventBridge); a dedicated queue would fix that but adds a
queue + DLQ + alarm for a daily-cadence job. Instead each source gets its own
schedule (`worker-release-upcoming-mb` rate(1 hour) /
`worker-release-upcoming-itunes` rate(30 minutes) — separate so one source
lagging never delays the other) and each tick processes a stateless bucket of
the stable-ordered watchlist: bucket index = ticks-since-epoch mod bucket
count (`album_ingest` rotation precedent — no cursor row to migrate or
corrupt; a failed tick's bucket is revisited next cycle, harmless at
median-43-day announcement lead). Per-tick bounds: MB 70 artists (~70 s at
1 req/s) / iTunes 22 (~77 s at 3.5 s throttle), plus a 90 s wall-clock budget
guard — full ≥50-tier coverage ≈ 22 h (MB) / ≈ 21 h (iTunes), i.e. about
daily. Failed iTunes resolutions are sentinel-cached in `artist_source_ids`
(`not_found`, MBID_NOT_FOUND precedent) and re-attempted after 30 days;
transient resolution errors leave no sentinel. The event upsert's
`DO UPDATE` deliberately never touches `status`/`spotify_album_id`, so a
Step-5 `released` confirmation can never be downgraded by a later poll.

**Verification**:
```
pytest myblog_worker  # handler unit + upsert idempotency (re-run = 0 new rows)
# one manual prod invoke → SELECT source, count(*), min/max(release_date)
#   FROM artist_release_events GROUP BY source;
```

---

### Step 5 (Track B) — release-day confirm via `album_ingest` (released path)

The absorbed draft's probe showed the daily `album_ingest` job already diffs
Spotify discographies for catalog artists — a separate "release-day confirmer"
job (the original design here) would duplicate it. This step **extends
`album_ingest_service.py`** instead: when the ingest encounters a release
within the calendar window by a watchlist artist, upsert/flip the matching
`artist_release_events` rows — all sources — to `status=released` +
`spotify_album_id` (match by artist + fuzzy title + date proximity — a
confirm-time match that collapses the soft group, not a data merge; insert a
`spotify`-source `released` row when never announced by any source). Catalog
sync for novel albums already happens in this job — no extra enqueue path
needed.

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

### Step 6 (Track B) — music API calendar endpoint + contract — **SHIPPED + prod-smoked 2026-07-13 (music #54 / ws #617 / front #271)**

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

**Entry point (owner decision 2026-07-12)**: the home `NewReleasesCard`
(Track A) is the calendar's entry point — clicking through the card/header
should land on the calendar page (exact affordance decided at the mockup
gate). The card's current in-card behavior (cover → AlbumDetail overlay)
stays.

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

1. **Watchlist floor** — **DECIDED 2026-07-12** (owner, probe-informed):
   **popularity ≥ 50** (1,530 artists). Probe hit rate was flat down to pop
   79 with no data below; widening below 50 stays a live-data revisit. Note
   the existing ingest floor is 60 (`ARTIST_POP_MIN`) — interacts with OQ5.
2. **Horizon** — **DECIDED 2026-07-12** (owner): **query 180 days** (single
   request either way); probe shows real content all sits ≤90 d (max lead
   82 d), so the UI can default to a ~3-month view.
3. **MB granularity + partial dates** — **DECIDED 2026-07-12** (owner,
   probe-informed): **release-group `firstreleasedate`, full-date-only v1**
   (11/11 date match; RG catches announce-stage entries release-level
   misses; the only partial dates seen were year-only placeholders).
4. **Single-type noise gate** (blocks nothing; review gate after Step 7) —
   owner chose include-all for the calendar. Re-check after **14 days of live
   data**: if singles exceed ~50% of calendar entries **(denominator: all
   `artist_release_events` rows with `release_date` in those 14 days)** and
   the owner finds the view noisy, add a type filter toggle rather than
   dropping data.
5. **Ingest extension coverage** — **DECIDED 2026-07-12** (owner via
   AskUserQuestion): **both widened** — align the ingest floor
   `ARTIST_POP_MIN` 60 → 50 with the watchlist floor (OQ1) AND widen
   `include_groups` to singles/EPs for watchlist artists, so `announced`
   entries of every type can flip to `released`. Implementation lands in
   Step 5; the added ingest volume stays bounded to watchlist scope.
6. **Feed noise beyond `album_type='album'`** (blocks nothing; Track A) — is
   artist-pop ranking enough, or do classical/compilation-style albums still
   pollute the top-N? Ship simple, judge on the first prod feed, tighten in a
   follow-up if needed.
7. **Card placement + click behavior** — **ANSWERED 2026-07-12** (owner,
   AskUserQuestion): card sits **between the BNM hero and Latest**; cover
   click opens the **AlbumDetail overlay** (artist caption still routes to
   the artist hub). Recorded in the Decisions log.
8. **iTunes source posture** — coverage half **RESOLVED by the 2026-07-12
   probe**: 61% artistId resolution on top-200, and iTunes contributed 3
   upcoming artists MB missed (K-pop/OST) + corroborated 3 → **iTunes stays
   a v1 source**. Impl caveats recorded: per-album multiple edition
   `collectionId`s (display soft-grouping handles it); ~22% of UPC-bearing
   artists miss on `lookup?upc=` → fall back to the next-newest UPC before
   marking unresolved. ToS: the formal per-source review stays
   FEAT-personal-release-tracking OQ2 — one review covers both RFCs.

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
| 2026-07-11 | **Discovery design-revision pass done** (same night, per the re-open): v1 sources = MB + iTunes pre-order + Spotify confirm, all per-artist within watchlist scope. Live probes: iTunes lookup surfaces pre-orders future-dated with hard `collectionId` (As It Is 2026-07-17); no coming-soon RSS survives; Apple Music API token-gated; iTunes returns no UPC ⇒ no cross-source hard key pre-release. Data model = one row per (source, source_key) observation, hard-key merge only, display soft-grouping, confirm = collapse point; new `artist_source_ids` cache for UPC-anchored `artistId` resolution; Step 4 gains a top-200 density probe gate. Steps 3–5 revised accordingly — pending owner review of this revision before Step 3 starts | design |
| 2026-07-12 | **Track B multi-source revision APPROVED** (owner in-session, AskUserQuestion) — Step 3 cleared and shipped same session | design |
| 2026-07-12 | **OQ7 answered** (owner): home card between the BNM hero and Latest; cover click opens the AlbumDetail overlay | OQ7 |
| 2026-07-12 | **Step 3 prod DDL applied pre-merge** (owner-approved in-session): V44 dry-run BEGIN…ROLLBACK → apply → `\d` verified; rollback stays `DROP TABLE` ×2 until Step 4 consumers land | Step 3 |
| 2026-07-12 | **Step 4 density probe run** (top-200, both sources, 0 errors): MB 5.5% / combined 7.0% density (+27% from iTunes), max full-date lead 82 d, RG==release dates 11/11, iTunes resolution 61%; results recorded in Step 4 | Step 4 |
| 2026-07-12 | **OQ1/OQ2/OQ3 decided** (owner, probe-informed): floor pop≥50; query horizon 180 d; MB release-group `firstreleasedate`, full-date-only v1. OQ8 coverage half resolved (iTunes stays, next-newest-UPC fallback caveat) | OQ1–3, OQ8 |
| 2026-07-12 | **OQ5 decided** (owner via AskUserQuestion): both coverage gaps widened — ingest floor `ARTIST_POP_MIN` 60→50 aligned with OQ1 AND `include_groups` widened to singles/EPs for watchlist artists; implementation in Step 5, volume bounded to watchlist scope | OQ5 |
| 2026-07-12 | **Step 4 fan-out design decided** (implementation session): EventBridge stateless time-bucket rotation, two rules (MB hourly ×70 / iTunes half-hourly ×22 + 90 s budget guard) — SQS fan-out rejected to keep MB/iTunes outages off the album-sync queue (alias-fill boundary); failed iTunes resolutions sentinel-cached 30 d; event upsert never touches `status`/`spotify_album_id` | Step 4 |
| 2026-07-12 | **Step 7 entry point** (owner): the home `NewReleasesCard` is the calendar's entry point — card/header click-through lands on the calendar page (exact affordance at the Step 7 mockup gate); in-card cover → overlay behavior stays | Step 7 |
| 2026-07-12 | **Step 4 poller SHIPPED + ARMED** (worker #70, ws #615) — EventBridge bucket rotation live (MB hourly 70/tick over 1,533 eligible; iTunes half-hourly ~10/tick over 1,593); released-flip invariant prod-proven; first ticks clean, errors=0 | Step 4 |
| 2026-07-13 | **Step 6 calendar endpoint SHIPPED + prod-smoked** (music #54) — `GET /api/music/releases/calendar` DB-only raw `text()` SQL (no shared_db pin bump); defaults = current month, 93-day range cap (both RFC-silent choices, flagged to owner in the PR); display soft-grouping on (artist_id, release_date, normalized title), normalization strips trailing " - Single"/" - EP"; `Cache-Control` 60 s + SWR. Contract ws #617, types front #271. Prod smoke: 200 over live Step-4 poller data | Step 6 |
