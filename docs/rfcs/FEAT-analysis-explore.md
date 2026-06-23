# FEAT-analysis-explore

**Status:** accepted

> **Accepted 2026-06-23** (owner) — draft → accepted on explicit owner approval (rule #5). Owner also authorized **single-pass completion** (build all capabilities in one coordinated cross-repo pass — contract → backend → front — rather than the 6-session cadence; rule #4 escape (b) "user explicitly OKs"). The per-step prod-observe gates are waived for this build; verification rides the per-PR local + post-merge prod smoke instead.
>
> Follow-on to the shipped **FEAT-listening-history-import** (closed 2026-06-23) + **FEAT-listening-live-merge** (closed 2026-06-23). Those gave the 분석 버킷 a lifetime **aggregate** import source (one continuous lifetime + live signal). This RFC makes that source **explorable**: filter by time period, drill into any artist/album/track, and see *when* you listen (clock). All over the already-owned data — no new ingestion, no ML, no external cost.
>
> Grounded in `docs/reviews/2026-06-22/analysis-bucket-statsfm-research.md` (the Stats.fm study). §9.4 of that report assumed time-range/drill-down would be "absorbed into the import RFC, no separate RFC needed" — that was optimistic: the import shipped the lifetime *totals* + retrospective only; these *interaction* patterns were never built. This RFC builds them.

## Goal

Turn the 분석 버킷 import source from a fixed lifetime-aggregate view into an **explorable** one, with three capabilities (owner chose all three, 2026-06-23):

1. **Time-range filter** — view every panel for 전체 / 올해 / a chosen year / a decade / a custom range, not just lifetime.
2. **Item drill-down** — click any artist/album/track → its own stats (play count, listening time, first/last listen, per-year mini-history; for an artist, its top tracks/albums).
3. **Listening clock** — hour-of-day + weekday patterns from the stream timestamps.

These are real Stats.fm features (custom timeframes, drilldown, listening clocks) — there they sit behind **Plus (paid)**; we already own the data (`spotify_stream_history.ts` per stream), so we self-replicate them for free. This is exactly the report's §3 principle 1 ("analysis comes from owned data, not the live API").

## Non-goals

- **No new ingestion / schema change.** Everything re-aggregates the existing `spotify_stream_history` (per-stream `ts` + `ms_played`) and `spotify_track_play_events` (live tail) via the existing `_unified_events()` union. (One *additive* index on `ts` may help range scans — decided at Step 1, not a schema/contract change.)
- **No ML / audio-features / recommendation.** (Report §4 + Spotify 2024-11 audio-feature/genre deprecation.)
- **No social / leaderboard / public sharing / Wrapped cards.** (Report §4; 분석 버킷 stays `/profile`-gated, private.)
- **No writing-screen integration.** Surfacing listening evidence in `/write?album=` is the report's §5 B-2 + Q5 — owner decided 글쓰기 연결 = **부차** (2026-06-22). Deferred to a later RFC.
- **No "intensity / 진짜 끼고 산 앨범" composite metric** (count+time+span). Report §5 B-2 — deferred; this RFC keeps count and time as separate honest axes.

## Current state (verified against code 2026-06-23)

- **Union reader exists**: `library_service._unified_events()` — import (`spotify_stream_history WHERE ts ≤ as_of`, real `ms_played`) `UNION ALL` live (`spotify_track_play_events WHERE played_at > as_of`, ms = `coalesce(tracks.duration_sec,0)*1000`). Columns: `uri / track_name / artist_name / album_id / ms_played / event_ts / src`. `as_of = max(ts)` over the import.
- **6 stream-history endpoints** (`GET /api/library/stream-history/...`, edge_guard reads) all aggregate over `_unified_events`: `top-tracks`, `top-artists`, `top-albums`, `genre-distribution`, `era-distribution`, `retrospective`. Each takes **only** `metric=count|time` (+ `limit`). **No time-range param.** `retrospective` already buckets per-year + "on this day" but is a fixed breakdown, not a filter.
- **Frontend** (`ImportAnalysis.tsx`): lifetime hero, count↔time toggle, top tracks/artists/albums, genre dist, era histogram, retrospective. **No date-range selector, no click-through drill-down, no hour/weekday view.** Chart items (`DistChart`) are non-interactive.
- **Data supports it**: every stream carries `ts` (timestamptz). Time-range, per-item, and hour/weekday aggregations are all pure re-GROUP-BYs over data already in Postgres. Retrospective already proves the KST timezone path (`func.timezone('Asia/Seoul', ts)`).

## Target state

A `range` (and the drill-down / clock) all thread through the **same `_unified_events` subquery**, so the union + count-exact / time-estimated semantics + the `live_streams` honesty field carry through unchanged.

- **Time-range**: a `range` parameter on the 6 endpoints. When a range is active, the hero + every panel reflect that range; default `전체` = today's lifetime + live behavior. A range that includes "now" still pulls the live tail (estimated time → the existing 추정 marker stays honest). A range entirely ≤ `as_of` is import-only (exact).
- **Drill-down**: a new detail endpoint keyed by entity (artist | album | track) → that entity's count, time, first/last listen, per-year sparkline, and (artist) its top tracks/albums — honoring the active range. Surfaced as a slide-over panel from a chart-item click.
- **Clock**: an hour×weekday aggregation endpoint (KST) → a heatmap/clock panel.
- **Honesty carries**: `live_streams` / 추정 marker, 미분류 gate notes, and the source labels all continue to work per range.

## Open questions

**Resolved (owner, 2026-06-23):**

1. **Time-range UX** → **presets + 연도 드롭다운** for v1 (`전체 / 올해 / 작년 / 이번 달` + 연도·시대 dropdown); a free from/to date picker is deferred (covers 90% with less UI).
4. **Clock priority** → keep as **Steps 5–6, explicitly droppable** after Steps 1–4 land + prod-observe (report §9.4 "v1 비핵심").

**Leans (override at Step 1 if needed):**

2. **Range param shape** — *Lean*: raw `from`/`to` timestamps on the backend (one flexible code path); the front maps the presets → `from`/`to`. Keeps the contract small.
3. **Drill-down surface** — *Lean*: a private slide-over (reuse `lf-slideover`, like OverviewDash modals) — these are owner-only listening stats; the public `/artist/[id]` route has no per-user data.
5. **Range vs the 좋아요 source** — *Lean*: range applies to the **임포트** source only; 좋아요 (saved-tracks) has no per-stream time axis (only `added_at`), and its weekly "흐름" chart already covers its time dimension.

## Steps

> One step per session (rule #4). Cross-repo: backend + contract first, then front, per capability (the import RFC cadence). shared_db needs no migration.

1. **Backend: time-range over `_unified_events` + the 6 endpoints + contract.** Add `from`/`to` (nullable) filtering on `event_ts`; thread through all 6 stream-history methods + totals + album-weights; default (none) = current behavior. Consider an additive `ts` index. Add the range echo to responses if useful for captions.
   - *Verify*: pytest (route + real-engine integration for the range boundary, `feedback-sa-session-lifecycle-mock-blind`); read-only prod sanity (a year's totals vs lifetime); `openapi.json` regenerated. *Rollback*: revert (additive — no range = old behavior).
2. **Frontend: period selector wired to all import panels.** A `Seg`/dropdown (전체/올해/작년/이번달/연도/시대) → `from`/`to` → re-fetch; hero + captions reflect the active range; keep the count↔time toggle + 추정 marker. Regen `api.gen.ts`.
   - *Verify*: `pnpm lint` + `astro check` + browser click-through (BUG-11/12).
3. **Backend: item drill-down endpoint + contract.** `GET /api/library/stream-history/item?type=artist|album|track&id=...` (+ range) → count, time, first/last listen, per-year series, and (artist) top tracks/albums over `_unified_events`.
   - *Verify*: pytest + prod sanity (a known top artist's detail) + openapi regen.
4. **Frontend: drill-down slide-over.** Click a chart item → slide-over with the item's stats; reuse `lf-slideover` + the chart language. Regen `api.gen.ts`.
   - *Verify*: lint + astro check + click-through.
5. **Backend: listening clock aggregation + contract.** `GET /api/library/stream-history/clock` (+ range, metric) → hour×weekday matrix in `Asia/Seoul`. *(Droppable — owner may cut after Step 4.)*
   - *Verify*: pytest + prod sanity + openapi regen.
6. **Frontend: clock / weekday heatmap panel.** *(Droppable with Step 5.)*
   - *Verify*: lint + astro check + click-through.

## Decisions log

| Date | Step | Decision |
|---|---|---|
| 2026-06-23 | — | Scope = all three (time-range + drill-down + clock) in one RFC (owner). |
| 2026-06-23 | — | Re-aggregate the existing union only — no new ingestion / ML / schema (carries the import + live-merge semantics forward). |
| 2026-06-23 | — | Writing-screen evidence (§5 B-2) + "intensity" metric explicitly OUT (owner Q5 글쓰기=부차; deferred). |
| 2026-06-23 | OQ1 | Time-range UX = presets + 연도/시대 dropdown (v1); custom date picker deferred (owner). |
| 2026-06-23 | OQ4 | Listening clock = Steps 5–6, droppable after Steps 1–4 prod-observe (owner). |
| 2026-06-23 | — | Single-pass completion authorized (rule #4 escape): collapse the 6 steps into a coordinated build (workspace contract → backend → front), not 6 sessions (owner). |
