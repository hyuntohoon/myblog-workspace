# FEAT-listening-history-import

**Status:** in-progress

> **Accepted 2026-06-22** (owner) — draft → accepted → in-progress; Step 1 (shared_db V27) started the same session.

> **Review-revised 2026-06-22** (adversarial design review — 2 independent lenses + code ground-truth; all "Current state" claims verified accurate). Folded in: a **catalog-coverage gate** + **two-pass re-resolution** (Steps 3/5 — without these the headline album/era/genre views ship mostly 미분류 and never improve as the catalog grows); **SQL `GROUP BY` aggregation** + **BIGINT `ms_played`** + V27 indexes (the load-all-rows `rank_counts` path won't survive 100k–500k rows); a **KST timezone** decision for retrospective/era; an explicit **import↔poller seam** + as-of horizon caption; and correctness pins (URI-prefix strip, podcast-by-URI-prefix predicate, SQS chunk+key-sort, dedup-precision note, script home, import-run ledger). **Step 4/6 re-scoped** — the front work reworks the merged `#194` source panel, not a small additive extension.

## Goal

The owner can import their Spotify **Extended Streaming History** (GDPR data export — a lifetime, per-stream JSON ledger) into the system's own Postgres, and the `/profile` 분석 버킷 surfaces true **lifetime** listening analytics that no Spotify API can provide: per-track/artist/album/genre **play counts** AND **listening time** (`ms_played`), an **era/decade** distribution of what was actually played, and a **retrospective** view ("on this day" / per-year recap). Post-import, the bucket's primary "favorite" signal is lifetime play (count + time); the 좋아요(saved) set is demoted to a secondary "intent" signal.

## Non-goals

- **No web upload UI in v1.** Ingestion is a local script the owner runs when the (~yearly) export arrives. Web upload / Lambda payload handling = later RFC.
- **No real-time/continuous sync change.** The hourly recently-played poller (`spotify_play_events`) is untouched; import is a separate, lifetime backfill source that coexists.
- **No PII storage.** The export contains IP address + user agent; these are parsed out and never persisted.
- **No recommendation engine** (separate, frozen `FEAT-genre-recommendation`).
- **No Apple Music / non-Spotify sources.**
- **No new genre signal** — genre still derives from the existing album pipeline (Spotify deprecated track/artist genres 2024-11).

## Current state

- Listening *behavior* today = `spotify_play_events` (shared_db V10), **album-grain**, `played_at` only (**no `ms_played`**), fed hourly from the rolling 50-item `GET /me/player/recently-played` window (`myblog_worker/worker/service/listening_sync_service.py`). Live prod (2026-06-22): 854 events / 227 albums / **18-day horizon** (2026-06-03…06-21); **65% of played albums have exactly 1 play**. `spotify_track_play_events` (V19) exists at track grain but has **no app reader**.
- *Intent* = `spotify_saved_tracks` (V24/26), the 좋아요 set, **100% catalogued + genred** (1017 tracks / 816 albums).
- 분석 버킷 (`myblog_front/src/components/member/{LikedBoard,LikedAnalysis}.tsx` + `myblog_backend/app/api/routes/library.py`) renders genre/artist distributions over a 좋아요/재생 source toggle. **"Listening time" is impossible** — no duration data exists anywhere (`spotify_play_events.played_at` only; `duration_ms` fields are full track length, not time listened).
- **No Spotify API exposes play counts or minutes** (verified against official docs: `/me/top/{type}` = affinity rank over 3 fixed windows, no counts; recently-played = 50-item rolling, no aggregates). Only the **Extended Streaming History export** carries per-stream `ts` + `ms_played` over the account lifetime.

## Target state

- **New shared_db table `spotify_stream_history` (V27)** — one row per stream: `ts` (timestamptz, stream end), **`ms_played` BIGINT** (per-row fits INT, but a lifetime `sum(ms_played)` is tens of billions of ms → exceeds INT4; store BIGINT), `spotify_track_uri` (text — the full `spotify:track:…` / `spotify:episode:…` URI), denormalized `track_name`/`artist_name`/`album_name`, flags `skipped`/`offline`/`shuffle`/`incognito` + `reason_start`/`reason_end`, nullable catalog FKs `track_id`/`album_id` (best-effort, **two-pass** — see Steps). Dedup unique `(ts, spotify_track_uri)`; append-only, re-import idempotent. **No IP / user-agent columns.** Indexes `(album_id)`, `(track_id)`, `(ts)` for drilldown / re-resolution UPDATE / retrospective range. A small **`stream_import_runs`** ledger (file, row count, `as_of`=max(ts), imported_at) records each import → crash-detection + the as-of horizon caption.
- **`myblog_shared_db/scripts/import_streaming_history.py`** ($0 local; same home + psycopg/raw-SQL heritage as `backfill_genres.py` — NOT the content-oriented workspace `scripts/`; reads SSM `/myblog/backend`, never logs it): unzip/parse `Streaming_History_Audio_*.json` (+ legacy `endsong*.json`), idempotent insert (`ON CONFLICT (ts, spotify_track_uri) DO NOTHING`), **strip the `spotify:track:` prefix** before matching `tracks.spotify_id` (storing the URI but joining a bare id silently resolves 0 rows — a "100% uncatalogued" failure mode), backfill `track_id`/`album_id`. Catalog-absent albums → existing SQS catalog-sync, **chunked ≤20 album_ids/msg + sorted by key** (the concurrency-10 deadlock-livelock — `reference-sqs-fanout-burst-pitfalls`). A canonical **music-stream predicate keys on the URI prefix** (`spotify:track:`), NOT on resolution failure — uncatalogued *music* also fails resolution and must stay distinct from podcasts (`spotify:episode:`). Re-runnable as `--resolve-only` (the two-pass backfill).
- **Backend lifetime endpoints** (edge_guard, DB-only, no synchronous Spotify — rule #9), aggregated with **SQL `GROUP BY count(*) / sum(ms_played)` returning top-N** — NOT the load-all-rows-into-`rank_counts` path (it timed out once at limit=500 and won't survive 100k–500k rows; keep `rank_counts` for the small saved/played sources):
  - *Coverage-independent (off denormalized text):* lifetime **top tracks / artists** by count and by time → ship **ungated**.
  - *Coverage-dependent (needs catalog FK + `Album.release_date`):* **top albums, genre distribution, era/decade, listening-time-by-album, retrospective** (per-year + "on this day") → **gated** on the Step 3 resolution rate. Era/year/"on this day" bucket via **`ts AT TIME ZONE 'Asia/Seoul'`** (export `ts` is UTC; UTC bucketing misfiles late-night KST listens by a day/year). Display filters = import defaults (exclude `skipped`, `ms_played < 30000`, local, podcasts) via the shared predicate; raw rows retained.
  - Contract gains a value-**unit** field (count vs ms) so the source-agnostic chart renders a Count↔Time axis — "time" is long-track-biased (research §3.2), labelled as such.
- **분석 버킷 gains an "임포트(평생)" source** — a **structural extension** of the merged `#194` panel (today `LikedAnalysis` `Source` is the binary `'liked' | 'played'` with a binary `SourceNote` + `'liked:'/'played:'` dist keys): add the 3rd source, a **Count↔Time toggle**, listening-time totals, era histogram, retrospective. **Primary "favorite" = import lifetime-play; 좋아요 demoted to secondary "intent".** Carries the #194 honesty captions (meaning + denominator + **horizon = the import `as_of` date**, so the post-export staleness is surfaced, not hidden). Album/era/genre panels honor the coverage gate (population caption + 미분류 bar).
- **UX patterns** (research note §9.4 — borrow interaction/IA, not Stats.fm's visual skin): per-item drill-down (artist/album/track → its own stats; reuse `/artist/[id]` hub), Count↔Time toggle on ranked lists, era histogram, "on this day"/per-year recap cards. Explicitly avoid consumer-app skin / Wrapped share cards / leaderboards. `frontend-design` skill sets visual direction when the front step lands; no separate design RFC.

## Steps

> One step per session unless the owner says "go". Each step is independently mergeable. Cross-repo: shared_db migration applied to prod **before** merge, then service pin bump (`reference-shared-db-cross-repo-rollout`). **Resolution is two-pass** (import-time best-effort + a re-runnable `--resolve-only` backfill), and **catalog coverage gates the album/genre/era panels** (Steps 3 → 5).

1. **shared_db V27 `spotify_stream_history` + `stream_import_runs`** — plain `V27__*.sql` + ORM models + tag/pin. Apply to prod before merge.
   - Columns per Target state; **`ms_played` BIGINT**; `ts timestamptz`; unique `(ts, spotify_track_uri)`; indexes `(album_id)`, `(track_id)`, `(ts)`; the `stream_import_runs` ledger.
   - *Verification*: table + unique + indexes present. *Rollback*: `DROP TABLE` (no consumer yet).
2. **Local import script** (`myblog_shared_db/scripts/import_streaming_history.py`) — parse + idempotent insert + **`spotify:track:`-prefix-stripped** URI→catalog resolution + enqueue-missing (**chunk ≤20/msg + key-sort**) + URI-prefix podcast exclusion + record the run.
   - *Verification*: dry-run on a sample (counts; re-run inserts 0 = idempotent; **Audio↔endsong overlap tested**; podcasts excluded by URI prefix); then the owner runs the real import; read-only SQL spot-check.
   - *Rollback*: `TRUNCATE spotify_stream_history` (script-only).
3. **Re-resolution backfill + coverage GATE** — `import_streaming_history.py --resolve-only`: idempotent `UPDATE … SET track_id/album_id FROM tracks WHERE album_id IS NULL AND <uri match>`. **Re-runnable** (the daily album-ingest cron + manual classify keep cataloging albums all year → a recurring owner action, not one-time). Then **measure + report the resolution rate** (% music streams with `album_id`; of those, with `release_date` / genre). **This rate gates Step 5's album/era/genre panels** (Step 4 is ungated).
   - *Verification*: re-run after the SQS catalog wave drains → coverage rises; print the rate. *Rollback*: N/A (idempotent UPDATE).
4. **Backend count/time top-track + top-artist endpoints + contract (UNGATED)** — `count(*)` and `sum(ms_played)` top-N in **SQL `GROUP BY`** over the **denormalized** `track_name`/`artist_name` → independent of catalog coverage. Add the value-**unit** field to the distribution contract.
   - *Verification*: pytest + read-only prod aggregate sanity; `openapi.json` regenerated. *Rollback*: revert (additive).
5. **Backend album / genre / era + listening-time-by-album + retrospective endpoints (GATED on Step 3)** — all need the catalog FK + `Album.release_date`; era/year/"on this day" bucket via **`ts AT TIME ZONE 'Asia/Seoul'`**. SQL aggregation + the V27 indexes.
   - *Verification*: pytest + prod sanity; `openapi.json` regenerated. *Rollback*: revert.
6. **Frontend 분석 버킷 "임포트(평생)" source** — **structural rework of the merged `#194` panel** (binary `Source`/`SourceNote`/dist-keys → 3rd source): Count↔Time toggle, listening-time totals, era histogram, retrospective panel. **Primary signal = import lifetime-play; 좋아요 → secondary "intent" label.** Carries the #194 honesty captions (meaning + denominator + horizon = import `as_of`); album/era/genre panels honor the Step 3 gate.
   - *Verification*: `pnpm lint` + `astro check` + browser click-through (BUG-11/12). *Rollback*: revert (front-only).

## Open questions

1. **Catalog backfill scope** — *RESOLVED by Step 3 (2026-06-23): the post-drain resolution rate hit **99.7%**, so no long-tail-denormalized compromise was needed — the album/era/genre panels ship now (gate PASS). The remaining 14-row tail stays denormalized.*
2. **Genre quality for lifetime albums** — denormalized albums show 미분류; *and* the import fans thousands of albums through the iTunes/LLM backfill, swelling the ~318 low-confidence-genred set (research §9.1). Distinguish **미분류 vs low-confidence-genred** in the honesty story. Acceptable bar for v1?
3. **Re-import cadence** — `(ts, spotify_track_uri)` dedup makes re-import safe; `stream_import_runs` records the as-of date. *Lean*: report new-row count + as-of date.
4. **Retrospective depth** — "on this day" + per-year in v1; first-listen dates / "this year vs last" deferred.
5. **Storage + signal shape** — 100k–500k rows is trivial for *storage*, but aggregation must be SQL GROUP BY + indexed (not load-all-rows). Separately, the **count-signal shape** is unknown until the real import (the 18-day poller shows 65% single-play) — do a post-import sanity read (top-N repeat counts) before committing the front to a count-ranked "favorite" headline.
6. **Dedup precision** — `ts` is second-precision stream-end → two genuine same-second replays of one URI collapse under `ON CONFLICT` (small systematic undercount of heavy-rotation/skip behavior). Accept as a logged ~0.x% undercount, or add a tiebreaker (e.g. include `ms_played`)? Verify on a real Audio↔endsong overlap.

## Decisions log

| Date | Step | Decision |
|---|---|---|
| 2026-06-22 | — | v1 scope = **core + retrospective** (owner). |
| 2026-06-22 | — | Post-import primary "favorite" signal = **import lifetime-play**; 좋아요 = secondary (owner). |
| 2026-06-22 | — | Ingestion = **local script**, no web-upload UI in v1 (owner packaging choice + $0/local pattern). |
| 2026-06-22 | — | Display filters = import defaults (exclude skipped / <30s / local / podcasts); store raw (owner). |
| 2026-06-22 | — | Do **not** store IP / user-agent fields (privacy; not needed for any feature). |
| 2026-06-22 | review | **Two-pass resolution**: import-time best-effort + a re-runnable `--resolve-only` backfill (cataloging never re-touches historical rows; same latent gap already exists for `spotify_track_play_events`). |
| 2026-06-22 | review | **Coverage gate** after import: album/era/genre panels wait on a measured resolution rate; denormalized count/time top tracks/artists ship ungated. |
| 2026-06-22 | review | **`ms_played` BIGINT**; aggregation via SQL `GROUP BY` (not load-all-rows `rank_counts`); V27 indexes `(album_id)`,`(track_id)`,`(ts)`. |
| 2026-06-22 | review | Retrospective/era bucketing in **`Asia/Seoul`** (export `ts` is UTC). |
| 2026-06-22 | review | Import↔poller seam explicit: import is the lifetime source; surface its `as_of` as the horizon caption; never silently union the two grains (double-count). |
| 2026-06-22 | review | Script home = `myblog_shared_db/scripts/` (DB-mutating, like `backfill_genres.py`), not workspace `scripts/`. |
| 2026-06-22 | accept | Owner accepted (draft → in-progress). Step 1 = shared_db V27 `spotify_stream_history` + `stream_import_runs` (BIGINT `ms_played`, dedup `(ts, spotify_track_uri)`, indexes), tag `v0.24.0`. |
| 2026-06-23 | Step 2 | Script reads **SSM** (`/myblog/backend` DB, `/myblog/spotify` creds) — the `backfill_genres.py` Secrets-Manager path is dead post-CHORE-secrets-ssm-migration. Catalog-sync needs Spotify **album** ids (export has only track uris) → import does a `GET /tracks` URI→album lookup for unresolved music streams, then key-sorted ≤20/msg enqueue (owner chose "include Spotify lookup"). |
| 2026-06-23 | Step 2 | Owner chose to **include `Streaming_History_Video_*`** music-video plays (spotify:track: rows) alongside Audio; video-podcast episodes drop out via the URI-prefix music predicate. |
| 2026-06-23 | Step 2 | **Shipped + prod-imported**: 4523 rows (4520 music / 3 podcast), 186h lifetime, **80.6% album-resolved** (100% of resolved carry release_date+genre); idempotent re-run = 0; 486 catalog-absent albums enqueued (25 SQS msgs). Q#5 (count-signal shape) resolved POSITIVE — real spread (top track 53×, top artist 316×), so a count-ranked "favorite" headline is viable (not the poller's 65%-single-play). Q#6 (same-second dedup) observed: 14 within-file collapses in the Video export, accepted. |
| 2026-06-23 | Step 3 | **`--resolve-only` re-run after the SQS catalog wave drained** (no new code — Step 2's script path): **861 rows newly resolved → album coverage 80.6% → 99.7%** (4506/4520). Only **14 rows / 9 distinct track ids** remain unresolved = the expected Spotify-lookup / catalog-sync failure tail (single/low-play one-offs + an obscure local-upload artist "SYSTEM SEOUL" with corrupted track names). Of resolved: **release_date 99.96%** (4504/4506 — era panel input), **genre 92.7%** (4188/4520; **167 distinct resolved albums 미분류** = open Q#2). 899 distinct albums now in history; the 486-album enqueue wave was **fully drained by the worker** (cross-checked read-only: 9 distinct tracks absent ⇒ near-all 486 landed). |
| 2026-06-23 | Step 4 | **Backend ungated count/time endpoints shipped** — `GET /api/library/stream-history/top-{tracks,artists}?metric=count\|time&limit=N` (edge_guard reads). SQL `GROUP BY count(*)`/`sum(ms_played)` top-N over the **denormalized** uri/track_name/artist_name (coverage-independent — no catalog FK). Display predicate = import defaults (music URI prefix, `ms_played ≥ 30s`, not skipped). New `StreamRankResponse` carries the **`unit`** field (count vs ms) for the front Count↔Time axis + honesty captions (`total_streams`/`total_ms`/`as_of`=import horizon); `metric` is a `Literal` → 422 on bad input. Top-artists groups the album-artist string (no per-artist split — that's the gated Step 5 path). shared_db pin **v0.23.0 → v0.24.0**. Verify: 5 route tests + full suite 279 pass / 38 skip; pyright 0 err; openapi regen. Read-only **prod sanity**: 3215 in-scope streams / 172.4h (from 4520 raw — skip/<30s filtered), top track 48×, top artist Kid Milli 274×; count vs time rankings diverge (Radiohead long-track bias, §3.2). **Next = Step 5** (gated album/genre/era — gate already PASSED in Step 3). |
| 2026-06-23 | Step 3 | **Coverage GATE = PASS.** 99.7% album / 99.96% release_date / 92.7% genre clears the bar for Step 5's **album / era / genre / listening-time-by-album / retrospective** panels — **ship them** (genre panel carries a **미분류 bucket** for the 7.3%; era panel keys on release_date, near-total). No further catalog-wait needed; `--resolve-only` stays a recurring owner action as the catalog grows. **Next = Step 4** (ungated count/time top-track/artist endpoints). |

Source / rationale: `docs/reviews/2026-06-22/analysis-bucket-statsfm-research.md` (§2 import mechanics, §5 brainstorm, §6 recommendation; coverage diagnosis §9; UX/design patterns §9.4).
