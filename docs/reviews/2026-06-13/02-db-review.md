# 02 — DB / Data Review (PROD Neon `neondb`)

**Date:** 2026-06-13
**Scope:** Read-only review of the production Neon Postgres DB backing `myblog_music` / `myblog_backend` / `myblog_worker`.
**Method:** All evidence below is the actual output of read-only `psql` queries (`SELECT` / `pg_stat_*` / `pg_*_size` / `pg_catalog`) run against the prod `myblog/music` `DATABASE_URL`. No writes, no DDL, no `ANALYZE`.

> **CRITICAL STATS CAVEAT (applies to the whole report).** At query time the Neon compute had been running for only **43 minutes** (`pg_postmaster_start_time()` = `2026-06-12 15:50:10+00`, `now()` = `2026-06-12 16:33:33+00`), and `pg_stat_database.stats_reset` is **NULL**. Neon suspends/resumes compute on idle; cumulative `pg_stat_user_*` counters reflect activity *only since the last resume*, not the table's lifetime. **Every `idx_scan = 0` and every seq/idx ratio below is a 43-minute window, not a verdict.** Treat all "possibly unused" flags as "verify over a longer window (days of warm traffic)".

---

## 6. Total DB size

```
 db_size |  bytes
---------+----------
 23 MB   | 24133632
```

`pg_database_size(neondb)` = **24,133,632 bytes ≈ 23 MB**. This is the headline number that drives the cost analysis: the entire production database is ~23 MB.

---

## 1. Per-table size (sorted by total relation size, desc)

```
          table          |   total    |  table_sz  |  index_sz  | est_rows | total_bytes
-------------------------+------------+------------+------------+----------+-------------
 tracks                  | 7664 kB    | 2120 kB    | 5544 kB    |     7338 |     7847936
 albums                  | 2040 kB    | 992 kB     | 1048 kB    |      982 |     2088960
 artists                 | 1392 kB    | 624 kB     | 768 kB     |     1671 |     1425408
 track_artists           | 1328 kB    | 640 kB     | 688 kB     |    10084 |     1359872
 album_research          | 384 kB     | 352 kB     | 32 kB      |       41 |      393216
 album_genres            | 280 kB     | 168 kB     | 112 kB     |     1552 |      286720
 album_artists           | 208 kB     | 120 kB     | 88 kB      |     1170 |      212992
 posts                   | 176 kB     | 80 kB      | 96 kB      |        0 |      180224
 spotify_play_events     | 160 kB     | 64 kB      | 96 kB      |      348 |      163840
 review_bucket_items     | 136 kB     | 56 kB      | 80 kB      |       67 |      139264
 spotify_recent_tracks   | 112 kB     | 64 kB      | 48 kB      |       50 |      114688
 review_buckets          | 112 kB     | 48 kB      | 64 kB      |        5 |      114688
 spotify_recent_albums   | 96 kB      | 48 kB      | 48 kB      |       14 |       98304
 spotify_now_playing     | 64 kB      | 48 kB      | 16 kB      |        1 |       65536
 tags                    | 64 kB      | 16 kB      | 48 kB      |       -1 |       65536
 sections                | 64 kB      | 16 kB      | 48 kB      |       -1 |       65536
 spotify_library_albums  | 64 kB      | 16 kB      | 48 kB      |       -1 |       65536
 album_to_listen_items   | 48 kB      | 16 kB      | 32 kB      |       -1 |       49152
 genres                  | 48 kB      | 16 kB      | 32 kB      |       -1 |       49152
 post_recommended_tracks | 48 kB      | 16 kB      | 32 kB      |       -1 |       49152
 ... (post_artists, post_albums, track_genres, post_comments, outbox_events,
      publishing_runs, post_tags, op_logs, post_likes, post_metrics — all ≤40 kB)
```

(30 user tables total in `public`. `est_rows = -1` means the table has never been (auto)analyzed since its last stat-relevant change — small/cold tables.)

**Notable shape:** `tracks` alone is **7.6 MB = ~33% of the DB**, and of that **5.5 MB is INDEX**, not table data (2.1 MB). Indexes-on-`tracks` are 2.6× the table's heap. That is the single biggest lever in the whole database (see §3/§4).

---

## 2. Exact row counts (top tables by size)

```
tracks                     7341
albums                     983
artists                    1672
track_artists              10100
album_research             49
album_genres               1552
album_artists              1179
posts                      1
spotify_play_events        363
review_bucket_items        67
spotify_recent_tracks      50
review_buckets             5
spotify_recent_albums      14
spotify_now_playing        1
spotify_library_albums     17
```

Catalog scale: **983 albums / 7,341 tracks / 1,672 artists**. Editorial scale: **1 published post** (the product's AI-editorial output is still ~0 — consistent with the "hand-publish ≥1 real review first" precondition). Everything else is sub-100 rows.

---

## 3. Index usage (`pg_stat_user_indexes`) — `idx_scan = 0` flagged

> Re-read the stats caveat at the top. `idx_scan = 0` here = "not used in the last 43 min", **not** "never used".

### Largest `idx_scan = 0` indexes (the ones worth a second look)

| table | index | idx_scan | size | note |
|---|---|---|---|---|
| `tracks` | `idx_tracks_title_trgm` | 0 | **3464 kB** | GIN trigram on `tracks.title`. By far the biggest index in the DB. |
| `albums` | `idx_albums_title_trgm` | 0 | 776 kB | GIN trigram on `albums.title`. |
| `artists` | `idx_artists_name_trgm` | 0 | 312 kB | GIN trigram on `artists.name`. |
| `spotify_play_events` | `spotify_play_events_pkey` | 0 | 40 kB | PK — keep regardless. |
| `posts` | `idx_posts_category_id` | 0 | 16 kB | low-value at 1 post. |
| `posts` | `idx_posts_search_index` | 0 | 16 kB | partial idx; low-value at 1 post. |
| `review_buckets` | `idx_review_buckets_single_done` / `_single_spotify_library` | 0 | 16 kB ea | singleton-guard partial unique idxs (correctness, not perf — keep). |

Plus a block of **`project_config`, `invitation`, `user`, `session`, `verification`, `jwks`, `organization`, `member`, `account`** indexes all at `idx_scan = 0`. **These are NOT in `public`** — they live in the **`neon_auth`** schema (Neon's managed Stack-Auth integration; see §8). `pg_stat_user_indexes` spans every non-system schema, so they surface here, but they are platform-managed, not project tables. _(Corrected 2026-06-13 by a verification re-query — the original draft mis-attributed them to `public`.)_

**The trgm trio is the headline.** `idx_tracks_title_trgm` (3.46 MB) + `idx_albums_title_trgm` (0.78 MB) + `idx_artists_name_trgm` (0.31 MB) = **~4.55 MB of GIN trigram index ≈ 20% of the entire 23 MB database**, all showing 0 scans in the window.

- This **directly corroborates two existing memory notes**: *"trgm GIN inert at small catalog — measured: trgm GIN indexes NOT used by planner (OR-shape query seq-scans), ~3–11ms either way at 1k–5k rows; pg_trgm was a recall win not a speed win; index pays off only at 10k+ rows."* At 983 albums / 7.3k tracks / 1.7k artists the planner has every reason to seq-scan instead.
- **Do NOT drop them on this evidence alone.** (1) Stats are a 43-min window. (2) The recall RFC (`music-search-recall`, pg_trgm 1.000 recall) keeps these indexes deliberately so `ILIKE … gin_trgm_ops` works for Korean recall — the value is *recall correctness via the operator class*, not scan-speed. Dropping the GIN would change query plans/recall, not just reclaim space. This is a **flag for a deliberate longer-window measurement**, not a cleanup.

### Indexes that ARE used (sanity check that the window has signal)
`artists_pkey` (96,183 scans), `albums_pkey` (39,369), `artists_spotify_id_key` (33,468), `album_artists_pkey` (32,298), `tracks_pkey` (27,049), `uq_tracks_spotify_id` (16,779), `tracks_spotify_id_key` (15,990) … — so the worker's catalog upsert path (spotify_id lookups + FK joins) is hammering these even in a cold 43-min window. The window is not empty; it's just short.

---

## 4. Duplicate / redundant indexes

**CONFIRMED duplicate — `tracks(spotify_id)` is indexed TWICE:**

```
 conname               | contype | def
-----------------------+---------+----------------------
 tracks_pkey           | p       | PRIMARY KEY (id)
 tracks_spotify_id_key | u       | UNIQUE (spotify_id)
 uq_tracks_spotify_id  | u       | UNIQUE (spotify_id)
```

Two **separate UNIQUE constraints**, `tracks_spotify_id_key` and `uq_tracks_spotify_id`, both back a `UNIQUE btree (spotify_id)` index on the same column:

```
tracks_spotify_id_key  CREATE UNIQUE INDEX … ON public.tracks USING btree (spotify_id)   -- 600 kB, 15990 scans
uq_tracks_spotify_id   CREATE UNIQUE INDEX … ON public.tracks USING btree (spotify_id)   -- 584 kB, 16779 scans
```

- This is a **genuine redundancy**: one of the two is wasted. **~584 kB of index** (≈ 2.5% of the whole DB, and ~10% of `tracks`'s 5.5 MB index footprint) duplicates the other, plus a doubled write-amplification cost on every track upsert (the hottest write path in the system — the Spotify→worker catalog sync).
- (guess) Origin: the ORM/`shared_db` model likely declares a `UniqueConstraint`/`unique=True` on `spotify_id` *and* a separate `V{N}__` SQL migration added `uq_tracks_spotify_id`, so both got created. Worth confirming against `myblog_shared_db` models + migrations before dropping (this DB review does not touch those files; cross-ref Task 1's shared_db audit).
- **Recommendation:** drop one of the two constraints (keep `uq_tracks_spotify_id` if the migration is the source of truth, or `tracks_spotify_id_key` if the ORM is). DDL → human-approved migration, **not** done here. Low risk, low urgency (584 kB), but it's a clean, real win and removes a needless write on the busiest table.

**No other duplicate leading-column-set indexes found.** I scanned all 80 index definitions (§ full list available in query log). Pairs that *look* similar are legitimately distinct:
- `albums_spotify_id_key` (on `spotify_id`) vs `albums_pkey` (on `id`) — different columns, fine.
- `outbox_events`: `idx_outbox_processed_at` (full) vs `idx_outbox_unprocessed` (partial `WHERE processed_at IS NULL`) — partial is a deliberate hot-path index, not a dup.
- `review_buckets` two `((true)) WHERE …` partial-unique singleton guards — correctness constraints, not dups.

---

## 5. Sequential vs index scan ratio (`pg_stat_user_tables`)

> 43-min window caveat applies. `seq_pct` = `100 * seq_scan / (seq_scan + idx_scan)`.

```
          table          | seq_scan | seq_tup_read | idx_scan | live_rows | seq_pct
-------------------------+----------+--------------+----------+-----------+--------
 track_artists           |      510 |      3418215 |    23110 |     10100 |    2.2
 artists                 |     4136 |      2254968 |   131217 |      1672 |    3.1
 tracks                  |      495 |      2114566 |    61634 |      7341 |    0.8
 album_artists           |     1604 |      1256149 |    32298 |      1179 |    4.7
 albums                  |     2960 |       984283 |    53877 |       983 |    5.2
 review_bucket_items     |     2388 |        68251 |      218 |        67 |   91.6
 album_research          |     1315 |        35517 |     1764 |        49 |   42.7
 spotify_recent_tracks   |      414 |        20791 |     5481 |        50 |    7.0
 spotify_play_events     |       73 |        17148 |    10175 |       363 |    0.7
 spotify_recent_albums   |      870 |        14577 |     3169 |        14 |   21.5
 album_genres            |       14 |        13977 |     1556 |     1552 |    0.9
 posts                   |      908 |         7611 |      241 |         1 |   79.0
 review_buckets          |      836 |         2934 |       11 |         5 |   98.7
 spotify_library_albums  |      231 |         1493 |       32 |        17 |   87.8
 ... (neon_auth platform tables, separate schema, 0 rows — see §8)
```

**Read this correctly: the high-`seq_pct` tables are all TINY.** `review_buckets` (5 rows, 98.7% seq), `posts` (1 row, 79% seq), `spotify_library_albums` (17 rows, 88% seq), `review_bucket_items` (67 rows, 92% seq) — at single-/double-digit row counts the planner *correctly* seq-scans; an index would be slower. **None of these are a problem.**

The interesting line is **`track_artists`: 510 seq_scans × ~10,100 rows = 3.4M tuples read sequentially.** It's a 10,100-row table, so each full seq-scan is cheap, but 510 of them in 43 min means a query repeatedly full-scans it.
- `track_artists_pkey` is `(track_id, artist_id)` (composite). There is **no standalone index on `artist_id`** (unlike `album_artists`… which also lacks one, but `post_artists` *has* `idx_post_artists_artist_id`). (guess) A reverse lookup "given an artist, find their tracks" (`WHERE artist_id = ?`) cannot use the composite PK and falls to seq-scan.
- At 10k rows the cost is small today (~3.4M tuples/43min is trivial CPU). **Flag, not fire.** If an artist→tracks query becomes hot (e.g. the FEAT-genre-artist-distribution work), add `idx_track_artists_artist_id`. Until then, no action — adding the index now is speculative gold-plating (write cost on the second-hottest M2M table).

The big catalog tables (`tracks` 0.8%, `albums` 5.2%, `artists` 3.1%, `track_artists` 2.2%) are **overwhelmingly index-driven** — the catalog read/write paths are well-indexed.

---

## 7. Growth-rate estimate (append-heavy tables)

**Method:** for each event/log-like table, `count(*)` + `min`/`max` of its timestamp column, then rows ÷ span. Marked **(estimate)**.

### `spotify_play_events` — the one real append-heavy table
```
count=363  min(played_at)=2026-06-03 06:42  max=2026-06-12 13:19  span=9.27 days
per-day breakdown: 49,30,30,85,26,24,33,20,35,31  →  avg ≈ 36 rows/day
```
- **~36 rows/day (estimate)** ≈ ~1,100 rows/month ≈ ~13k rows/year. Row width is tiny (album_id uuid, played_at, recorded_at). At 160 kB for 363 rows ≈ ~450 B/row incl. its 3 indexes → **~16 kB/day ≈ ~0.5 MB/month ≈ ~6 MB/year (estimate)**. This is the **dominant ongoing growth source**, and it is negligible.

### `spotify_recent_tracks` / `spotify_recent_albums` — bounded, NOT append-heavy
```
spotify_recent_tracks:  50 rows, played_at 2026-06-11 13:09 → 06-12 13:19  (~24h window)
spotify_recent_albums:  14 rows, last_played_at 06-11 13:45 → 06-12 13:19
```
- These are **rolling-window snapshot tables** (recent N), not append-only logs — high dead-tuple churn (`spotify_recent_albums`: 14 live / 40 dead; `spotify_recent_tracks`: 50 live / 31 dead) confirms upsert-and-replace, not accumulate. **Flat size. No growth concern.** Autovacuum is keeping up (last_autovacuum within hours).

### `album_research` — AI editorial output, bursty not steady
```
49 rows, requested_at 2026-06-11 08:44 → 2026-06-12 15:58  (~31h)
```
- 49 rows in ~31h = the album-research-notes executor backfilling. This is a **one-time-ish backfill burst** (bounded by the 983-album catalog × prompt_versions via `uq_album_research_album_prompt`), not perpetual append. `result_md` (text) makes rows fat (352 kB table / 49 rows ≈ 7 kB/row). At catalog size, full coverage = 983 albums × ~7 kB ≈ **~7 MB total at 1 prompt_version (estimate)**; each new prompt_version re-runs the catalog (~+7 MB). Sizeable relative to today's 23 MB but a **step function tied to deliberate re-runs**, not a leak.

### `outbox_events`, `publishing_runs`, `op_logs` — currently EMPTY
```
outbox_events: 0   publishing_runs: 0   op_logs: 0
```
- All transactional-outbox / run-log tables are **drained to 0** (worker processes + deletes them). No accumulation. If retention policy ever changes to "keep processed", revisit — but today: zero growth.

### Catalog tables — the real (intentional) growth so far
```
albums  created_at by month:  Mar 124 | May 497 | Jun 362
tracks  created_at by month:  Mar 660 | May 3617 | Jun 3064
```
- The DB grew from ~124 albums to 983 via **deliberate ingest bursts** (album-catalog-ingest, spotify-library-sync), not organic event accumulation. ~3k tracks added in the first 12 days of June. **This is the actual size driver** — and it's owner-controlled, not autonomous. Doubling the catalog to ~2,000 albums / ~15k tracks roughly doubles the DB to ~45 MB (estimate).

---

## (a) Neon cost / scale analysis — WHEN does size become a problem?

**Measured:** total DB = **23 MB (0.023 GB)**.

**Neon pricing** (fetched 2026-06-13 from <https://neon.com/pricing>, after `neon.tech`→`neon.com` 308 redirect):
- **Free:** $0/mo, **0.5 GB storage/project** + 100 CU-hours/project, compute suspends on limit.
- **Launch / Scale (paid):** pay-as-you-go, **$0.35/GB-month** storage, $0.106/CU-hour compute, 500 GB egress included then $0.10/GB. (Page now shows pure PAYG with no fixed monthly minimum; historically Launch carried a ~$19/mo base — see openQuestions, the exact current plan/tier of *this* project is not determinable from inside the DB.)

**Verdict on storage:**
- 23 MB is **4.6% of the 0.5 GB Free-plan storage cap.** Even on the free tier, storage is a non-issue.
- To cross 0.5 GB the DB must grow **~22×** (23 MB → 500 MB). Drivers: ongoing event growth is ~0.5 MB/month (`spotify_play_events`) → ~6 MB/yr → **~80 years** to fill 0.5 GB on events alone (estimate, absurd by design — the point is events are irrelevant). The only realistic path to 0.5 GB is **catalog ingest** (more albums/tracks) + **`album_research` re-runs across prompt_versions**. At the observed catalog (~983 albums ≈ 11.5 MB of catalog tables) you'd need ~**40× today's catalog (~40,000 albums)** to approach the Free cap.
- **On paid PAYG**, 23 MB × $0.35/GB-mo = **~$0.008/month of storage** — rounding error. Even at 500 MB it's **$0.175/month**.

**Verdict on compute (the real Neon cost for this workload):** storage is free-tier trivial; the actual Neon bill (if any) is **compute CU-hours**, driven by query traffic and the suspend/resume behavior we observed (43-min uptime ⇒ the compute is auto-suspending when idle, which is the cost-optimal mode). That is an infra/traffic question, out of scope for a data-size review, but worth stating: **for this DB, "Neon cost" ≈ compute, and storage will not be the constraint for years.**

**Timeline:** At today's 23 MB and the dominant ~0.5 MB/month event growth, **storage never becomes the binding constraint on any realistic horizon.** It only matters if the owner does a *massive* catalog expansion (40,000+ albums) or accumulates many `album_research` prompt_version re-runs (each ~+7 MB). Concrete trigger: **revisit storage only when total DB crosses ~250 MB (half the Free cap)** — at current trajectory that is not on the multi-year horizon.

## (b) Cold-data object-storage offload — needed now?

**No. Not needed now. Not close.**

- The entire database is **23 MB**. The single largest "cold/append" candidate, `spotify_play_events`, is **160 kB total** (64 kB heap). There is no large cold dataset to offload — `album_research.result_md` (352 kB) is the only "fat text" and it's hot product data (AI reviews), not cold logs.
- Offloading 160 kB of play-events to S3 would *add* operational complexity (a join across two stores, or a rehydration path) to save **<1% of a 23 MB DB** — strictly negative ROI. The memory's own framing ("if the data is small and cheap, say not needed") applies cleanly.
- **Revisit threshold Z:** reconsider cold-storage offload only if (1) `spotify_play_events` (or any single event/log table) crosses **~50 MB** *and* is queried only by recent window, or (2) total DB approaches the Free 0.5 GB cap. Neither is in sight. At current growth `spotify_play_events` reaches 50 MB in **~8 years (estimate)**.

---

## ## Bottom line

The prod DB is a **23 MB** music catalog (983 albums / 7,341 tracks / 1,672 artists) with effectively zero accumulating-event pressure — the only steady growth is `spotify_play_events` at ~0.5 MB/month, so Neon storage (Free cap 0.5 GB, or ~$0.008/mo on PAYG) and cold-data offload are **non-issues for years; do nothing on cost.** Two concrete, low-urgency cleanups are real and evidence-backed: a **confirmed duplicate UNIQUE index** on `tracks(spotify_id)` (`tracks_spotify_id_key` *and* `uq_tracks_spotify_id`, ~584 kB + doubled write cost on the hottest upsert path), and **~4.55 MB of GIN trigram indexes (20% of the DB) showing 0 scans** — but the latter must be confirmed over a longer warm window (compute had been up only 43 min; trgm indexes are kept deliberately for Korean search *recall*, not speed) before any drop. Everything else (high seq-scan %s, `idx_scan=0` flags) is an artifact of tiny tables + a 43-minute stats window, not a defect.

## openQuestions

1. **Neon plan/tier of THIS project** — Free vs Launch/Scale is not determinable from inside the DB. The analysis holds either way (storage trivial on both), but the *compute* cost story differs. Which plan is the prod `neondb` on? (Assumption used: storage cost is negligible regardless; stated inline.)
2. **`tracks(spotify_id)` duplicate UNIQUE constraint — source of truth?** Is `uq_tracks_spotify_id` from a `V{N}__` SQL migration and `tracks_spotify_id_key` from an ORM `unique=True` (or vice-versa)? Cross-ref `myblog_shared_db` models/migrations (Task 1) before dropping one — drop the one that is NOT the source of truth, via a human-approved migration.
3. **trgm GIN indexes (4.55 MB, 0 scans in window)** — should a deliberate multi-day warm-window measurement be scheduled to decide keep-vs-drop? Note they are load-bearing for `ILIKE … gin_trgm_ops` Korean recall (music-search-recall RFC), so "0 scans" ≠ "safe to drop" — the operator class matters even if the planner seq-scans at this catalog size.
4. **`track_artists` artist→tracks reverse lookup** — is there a hot `WHERE artist_id = ?` query (10k-row table, 510 seq-scans/43min, no standalone `artist_id` index)? If FEAT-genre-artist-distribution makes it hot, add `idx_track_artists_artist_id`; otherwise leave it (speculative today).
5. **`album_research` prompt_version re-run policy** — each full re-run across the 983-album catalog adds ~7 MB. How many prompt_versions will be retained? (Affects the only non-trivial deliberate growth vector; still years from any cap.)
6. **Auth/multi-tenant tables (`user`/`session`/`organization`/`member`/`invitation`/`account`/`verification`/`jwks`/`project_config`) — RESOLVED 2026-06-13.** The original draft said these "exist in `public`" and guessed they were FEAT-multi-user-accounts remnants or a library bootstrap. **Both wrong.** A verification re-query found they live in a dedicated **`neon_auth`** schema (alongside platform schemas `auth` and `pgrst`), all 9 tables 0-row. This is **Neon Auth** — Neon's managed authentication feature (built on Stack Auth, hence the Better-Auth-shaped table names). They are **platform-managed, not project DDL, not droppable via a `V{N}__` migration, and unrelated to FEAT-multi-user-accounts.** Action: **none** — leave as-is; if the owner wants them gone, Neon Auth is disabled from the Neon console, not from this codebase. (Footprint ≤8 kB each → zero cost impact regardless.)
