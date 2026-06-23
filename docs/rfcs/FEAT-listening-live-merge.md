# FEAT-listening-live-merge

**Status:** draft

> Follow-on to the completed **FEAT-listening-history-import** (closed 2026-06-23, `docs/archive/done/2026-06.md`). That RFC deliberately kept the lifetime import and the live poller as **separate** sources ("never silently union the two grains — double-count"). This RFC does the union **safely**, via a time boundary rather than per-row dedup, and folds the live poller into the import source so the 분석 버킷 shows one continuous **lifetime + live** signal.

## Goal

The 분석 버킷 "임포트(평생)" source becomes **"임포트(평생+라이브)"**: the GDPR import is authoritative up to its `as_of` (export horizon), and the hourly recently-played poller fills `as_of → now`. One continuous source; the separate **재생** toggle is removed. No double-counting.

## Non-goals

- **No per-row fuzzy dedup** (import `ts` = stream end vs poller `played_at` = report time; album-grain poller has no track id; second-precision won't align). Dedup is by the `as_of` time boundary instead — exact by construction.
- **No new ingestion.** The poller (`spotify_track_play_events`, worker-written) and the import are both already populated; this RFC only adds a **reader** + the union.
- **No schema change.** All tables exist (`spotify_stream_history` V27, `spotify_track_play_events` V19, `tracks.duration_sec`).
- **No change to the 좋아요 source.**

## Current state (verified against code 2026-06-23)

- **Import** = `spotify_stream_history` (V27): per-stream `ts` (stream end), **`ms_played`**, `spotify_track_uri`, `track_id`/`album_id`. Lifetime but frozen at `as_of` = `max(ts)` (≈2026-06-21). The 6 Step-4/5 endpoints aggregate it.
- **Live poller** = `spotify_track_play_events` (V19): `spotify_track_id`, `track_id`, `album_id`, `played_at`, unique `(spotify_track_id, played_at)`. **Worker-written** (`listening_sync_service.py`), append-only, but has **no app reader**. **No `ms_played`.** (The album-grain `spotify_play_events` feeds today's 재생 toggle; this RFC uses the richer track-grain table instead.)
- **Time source for estimation**: `tracks.duration_sec` (nullable Integer) — joinable via `track_id`. (`spotify_saved_tracks.duration_ms` is liked-only, not usable for arbitrary plays.)

## Target state

- A shared **as_of time-boundary union** in the backend: for each stream-history endpoint, aggregate `spotify_stream_history WHERE ts ≤ as_of` (import, exact ms) **∪** `spotify_track_play_events WHERE played_at > as_of` (live tail), keyed identically (track / album / artist / genre / decade / year). `as_of = max(ts)` over the import. The boundary is dynamic (a future re-import advances it; the live tail it supersedes simply drops out).
- **Count metric**: live tail contributes `count(*)` per key — exact.
- **Time metric** (owner decision 2026-06-23): live tail has no `ms_played`, so estimate **`duration_sec × 1000` per play** (join `tracks`). Labelled an **estimate** in the UI; plays whose track lacks `duration_sec` contribute 0 time (counted, logged). Overcounts skip-throughs / partial plays — accepted, captioned.
- **Display predicate parity**: the import filter is `music URI + ms_played ≥ 30s + not skipped`. The poller has no skip/ms signal, so the live tail can only filter by catalog presence — its rows are "a recently-played appearance," already ≥ the recently-played threshold. Note the asymmetry in the honesty caption.
- **Frontend**: the **재생** toggle + its `play-events` distribution calls are **removed**; the source toggle becomes `[임포트(평생+라이브), 좋아요]`. The hero/captions gain a "라이브 since `as_of`" note; the time total is marked **estimated** when the live tail is non-empty.
- **Contract**: shapes unchanged where possible; add a small honesty field (e.g. `live_count` / `estimated_live_ms` or a boolean `time_estimated`) so the front can caption the live portion. Decide at Step 1.

## Steps

> One step per session. shared_db needs no migration (tables exist). Cross-repo: backend + contract first, then front.

1. **Backend: as_of-boundary union over the live poller + contract caption.** A shared helper unions `spotify_track_play_events` (played_at > as_of) into each of the 6 stream-history aggregations; count exact, time estimated via `tracks.duration_sec`. Add the honesty field(s) to the contract. Wire `spotify_track_play_events` as the live reader.
   - *Verification*: pytest (route + a real-engine integration test for the union/boundary — mock units miss it, `feedback-sa-session-lifecycle-mock-blind`); read-only prod sanity (live tail count + estimated time vs import-only); `openapi.json` regenerated. *Rollback*: revert (additive).
2. **Frontend: collapse the toggle to 임포트(평생+라이브) + 좋아요; drop 재생.** Remove `getPlayed*` calls + the `'played'` source; relabel; caption the live extension + the estimated-time marker; regen `api.gen.ts`.
   - *Verification*: `pnpm lint` + `astro check` + browser click-through (BUG-11/12). *Rollback*: revert (front-only).

## Open questions

1. **Estimated-time honesty** — is a single "≈" / "추정" marker on the time total enough, or split the bar into exact(≤as_of) + estimated(>as_of)? *Lean*: marker for v1; the live tail is small.
2. **Retrospective per-year/"on this day"** — these now extend past `as_of` with live data; the live year (2026) becomes part import + part live. Surface the split, or just one number? *Lean*: one number, live caption.
3. **Keep the backend `play-events` distribution endpoints?** They become unused by this view. *Lean*: leave them (other consumers / overview dash) — front just stops calling them here.
4. **Necessity / timing** — the live tail is ~2 days now (poller started ≈18 days ago, `as_of` ≈06-21); value grows until the next export. Ship now (small but correct), or after the gap is meaningful? *Owner chose to extend now.*

## Decisions log

| Date | Step | Decision |
|---|---|---|
| 2026-06-23 | — | Merge direction: extend 임포트 to **lifetime + live**; **remove the 재생 toggle** (owner). |
| 2026-06-23 | — | Dedup = **`as_of` time boundary**, not per-row fuzzy matching (import ≤ as_of, poller > as_of) — exact by construction, no double-count. |
| 2026-06-23 | — | Live source = **`spotify_track_play_events`** (track grain, worker-written, no reader yet), not the album-grain `spotify_play_events`. |
| 2026-06-23 | — | Time metric past `as_of` = **estimate `duration_sec × plays`** (owner); marked estimated; missing-duration plays count but add 0 time. |
