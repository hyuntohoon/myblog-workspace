# FEAT-listening-history-import

**Status:** draft

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

- **New shared_db table `spotify_stream_history` (V27)** — one row per stream: `ts` (timestamptz, stream end), `ms_played` (int), `spotify_track_uri` (text), denormalized `track_name`/`artist_name`/`album_name`, flags `skipped`/`offline`/`shuffle`/`incognito` + `reason_start`/`reason_end`, nullable catalog FKs `track_id`/`album_id` (best-effort resolved). Dedup: unique `(ts, spotify_track_uri)`. Append-only; re-import idempotent. **No IP / user-agent columns.**
- **`scripts/import_streaming_history.py`** ($0 local pattern; reads SSM `/myblog/backend` DATABASE_URL like `editor_buckit.py`/`backfill_genres.py`): unzips/parses `Streaming_History_Audio_*.json` (+ legacy `endsong*.json`), inserts streams idempotently, resolves `spotify_track_uri` → `tracks.spotify_id` and backfills `track_id`/`album_id`, enqueues catalog sync for missing albums (reuse candidates→SQS path), retains podcast/episode rows but excludes them from music aggregates. Never logs DATABASE_URL.
- **Backend lifetime read/aggregation endpoints** (edge_guard, DB-only, no synchronous Spotify per hard rule #9): lifetime top tracks/artists/albums/genres by **count** and by **time** (`sum(ms_played)`), era/decade distribution (count- or time-weighted), retrospective (per-year + "on this day"). Display filters = import defaults (exclude `skipped`, `ms_played < 30000`, local files, podcasts); raw rows retained for future re-filtering.
- **분석 버킷 gains an "임포트(평생)" source**: lifetime top lists (count/time sort), listening-time totals, era distribution, retrospective panel. **Primary "favorite" signal = import lifetime-play**; 좋아요 shown as a secondary "intent" signal. Reuses the source-agnostic distribution chart contract.

## Steps

> One step per session unless the owner says "go". Each step is independently mergeable. Cross-repo: shared_db migration applied to prod **before** merge, then service pin bump (`reference-shared-db-cross-repo-rollout`).

1. **shared_db V27 `spotify_stream_history`** — plain `V27__*.sql` + ORM model + tag/pin. Apply to prod before merge.
   - *Verification*: table + unique `(ts, spotify_track_uri)` present; `terraform plan` N/A (no infra).
   - *Rollback*: `DROP TABLE spotify_stream_history` (no consumer yet).
2. **Local import script** (`scripts/import_streaming_history.py`) — parse + idempotent upsert + URI→catalog resolution + enqueue-missing + podcast exclusion.
   - *Verification*: dry-run on a sample export (row counts; re-run inserts 0 = idempotent; podcasts excluded from music aggregates); then owner runs the real import; spot-check counts/time via read-only SQL.
   - *Rollback*: `TRUNCATE spotify_stream_history` (script-only; no schema change).
3. **Backend lifetime aggregation endpoints + contract** — count/time top lists + era + retrospective; extend `distribution.rank_counts` for `ms_played` weighting.
   - *Verification*: pytest + read-only prod aggregate sanity; `openapi.json` regenerated + committed.
   - *Rollback*: revert (routes additive).
4. **Frontend 분석 버킷 "임포트(평생)" source** — listening-time + count/time top lists + era; primary-signal shift; 좋아요 demoted to secondary label.
   - *Verification*: `pnpm lint` + `astro check` + browser click-through (BUG-11/12 rule); `api.gen.ts` regenerated.
   - *Rollback*: revert (front-only).
5. **Retrospective view** — "on this day" / per-year recap panel.
   - *Verification*: browser click-through.
   - *Rollback*: revert (front-only).

## Open questions

1. **Catalog backfill scope** — a lifetime export references many albums absent from the catalog. Backfill all (cost: SQS fan-out, account Lambda concurrency 10 — `reference-sqs-fanout-burst-pitfalls`) or only albums above a play/time threshold? *Lean*: resolve FK for all; enqueue catalog-sync only above a min play/time, leave the long tail denormalized.
2. **Genre for un-catalogued lifetime albums** — rides the existing pipeline once catalogued; albums left denormalized show as 미분류 in genre views. Acceptable for v1?
3. **Re-import cadence** — owner re-requests ~yearly; `(ts, spotify_track_uri)` dedup makes re-import safe. Report only the new-row count, or also the gap between exports? *Lean*: new-row count only.
4. **Retrospective depth** — "on this day" + per-year is in v1. Beyond (first-listen dates, "this year vs last")? Defer.
5. **Storage volume** — a long-tenured account may be 100k–500k rows; trivial for Postgres, but confirm Neon plan headroom before the first full import.

## Decisions log

| Date | Step | Decision |
|---|---|---|
| 2026-06-22 | — | v1 scope = **core + retrospective** (owner). |
| 2026-06-22 | — | Post-import primary "favorite" signal = **import lifetime-play**; 좋아요 = secondary (owner). |
| 2026-06-22 | — | Ingestion = **local script**, no web-upload UI in v1 (owner packaging choice + $0/local pattern). |
| 2026-06-22 | — | Display filters = import defaults (exclude skipped / <30s / local / podcasts); store raw (owner). |
| 2026-06-22 | — | Do **not** store IP / user-agent fields (privacy; not needed for any feature). |

Source / rationale: `docs/reviews/2026-06-22/analysis-bucket-statsfm-research.md` (§2 import mechanics, §5 brainstorm, §6 recommendation; coverage diagnosis §9).
