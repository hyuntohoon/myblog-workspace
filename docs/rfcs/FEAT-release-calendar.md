# FEAT-release-calendar: New-release calendar (신보 캘린더)

- **Status**: draft
- **Owner**: TBD
- **Created**: 2026-07-06
- **Plan row**: `plan.md` → FEAT-release-calendar
- **Absorbs**: Frozen idea `FEAT-new-release-feed` (plan.md, no RFC)

---

## Goal

A public calendar surface (no user concept) showing **announced (예정)** and
**released (발매)** albums / EPs / singles for a watchlist of artists derived
from our own catalog. Upcoming entries come from MusicBrainz future-dated
release data; release-day confirmation comes from diffing Spotify artist
discographies in the worker. The calendar read path is **DB-only** (rule #9).
After this RFC: a visitor can open a calendar view and see what is coming and
what just dropped for the artists this blog covers.

Owner decisions locked 2026-07-06: (1) v1 is a public shared calendar — no
per-user subscriptions; (2) "공표" means visible on the calendar only — no
notifications / blog-post generation; (3) all release types included (album +
EP + single), with an empirical noise re-check after real data accumulates
(OQ4).

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

## Current state

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
  Feb 2026 Web API removals. `GET /browse/new-releases` was **removed**
  (Feb 2026 changelog) — an editorial "famous artists" feed from Spotify is
  not an option.
- No table stores future release dates; `albums` holds released catalog only.
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
- Worker: a **release-day confirmer** — for watchlist artists, diff Spotify
  `GET /artists/{id}/albums` against `albums` + `artist_release_events`; new
  releases flip/insert `status=released` + `spotify_album_id`, and enqueue the
  existing catalog-sync path (chunked per memory
  `reference-sqs-fanout-burst-pitfalls`) so day-0 releases get cataloged
  automatically. Releases never announced in MB appear directly as `released`.
- Music API: `GET /api/music/releases/calendar?from=&to=` — DB-only,
  edge_guard read (consistent with other public music reads), returns events
  grouped by date with artist + type + status. Contract exported + merged.
- Front: a public calendar view (month grid or agenda list — design decision
  at Step 5) fed by the new endpoint.

## Steps

Each step independently mergeable. Steps 2 and 3 are both worker-side but land
separately (announced-path first, confirm-path second).

### Step 1 — shared_db `artist_release_events` migration

Plain `V{N}__artist_release_events.sql` + ORM model + version bump. Rollout
order per memory `reference-shared-db-cross-repo-rollout`: migration → prod
apply (pre-merge, owner-approved) → service pin bumps land with Steps 2/4.

**Verification**:
```
cd myblog_shared_db && PYTHONPATH=src pytest   # schema parity
psql "$DATABASE_URL" -c "\d artist_release_events"
```

**Rollback**: `DROP TABLE artist_release_events` (no consumer yet at this step).

---

### Step 2 — worker MB upcoming poller (announced path)

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

### Step 3 — worker release-day confirmer (released path)

Daily diff of Spotify artist discographies for the watchlist → flip
`announced`→`released` (match by artist + fuzzy title + date proximity) or
insert `released` directly; enqueue catalog sync for new albums.

**Verification**:
```
pytest myblog_worker
# prod: a known release-day album flips status + appears in albums via sync
```

---

### Step 4 — music API calendar endpoint + contract

`GET /api/music/releases/calendar?from=&to=` in myblog_music (DB-only,
edge_guard). Export `openapi.json`, merge contract, regen front types.

**Verification**:
```
pytest myblog_music
curl "$MUSIC_URL/api/music/releases/calendar?from=2026-07-01&to=2026-08-01"
```

---

### Step 5 — front calendar view

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

1. **Watchlist floor** (blocks Step 2) — `popularity ≥ 50` (1,518 artists,
   ~25 min/day) vs all valid-MBID (4,044, ~68 min/day). Recommend starting at
   ≥50 and widening if coverage feels thin; the floor is one constant.
2. **Horizon** (blocks Step 2) — how far ahead to query. Recommend 180 days;
   MB entries typically appear ≤2 months before release, so longer horizons
   are nearly free but mostly empty.
3. **MB granularity + partial dates** (blocks Step 2) — release-group
   `firstreleasedate` (dedupes editions, recommended) vs release `date`;
   and whether year-only dates get dropped (recommended for v1) or shown as
   "date TBA". Probe both queries at Step 2 start.
4. **Single-type noise gate** (blocks nothing; review gate after Step 5) —
   owner chose include-all. Re-check after **14 days of live data**: if
   singles exceed ~50% of calendar entries **(denominator: all
   `artist_release_events` rows with `release_date` in those 14 days)** and
   the owner finds the view noisy, add a type filter toggle rather than
   dropping data.
5. **Day-0 auto-catalog** (blocks Step 3) — should Spotify-confirmed releases
   always enqueue catalog sync, or only `album`/`ep` types? Recommend all
   types (singles are cheap to sync and searchable later).

## Decisions log

| Date | Decision | Step |
|------|----------|------|
| 2026-07-06 | v1 public shared calendar; personal subscriptions deferred until after FEAT-multi-user-accounts (owner) | scope |
| 2026-07-06 | 공표 = calendar visibility only, no notifications (owner) | scope |
| 2026-07-06 | Include albums + EPs + singles; noise re-check with live data (owner) | OQ4 |
| 2026-07-06 | Discovery = MB per-artist future queries + Spotify day-0 diff; Spotify `/browse/new-releases` removed Feb 2026, global MB sweep rejected (long-tail) | design |
