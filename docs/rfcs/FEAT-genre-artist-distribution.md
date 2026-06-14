# FEAT-genre-artist-distribution

**Status**: draft

> **Correction 2026-06-15:** the `FEAT-genre-taxonomy` dependency referenced below is **stale**. That RFC was **discarded 2026-06-12**, superseded by **FEAT-genre-system** (tier-0 genre vocabulary + `album_genres` labels), which is **done + prod-live 2026-06-13** (archived). The genre-chart's "needs first-class genres" data blocker is therefore **resolved** — real genre labels exist now. Read "FEAT-genre-taxonomy" below as "FEAT-genre-system (done)"; this is now scopable. (Body kept as-authored for history.)

Aggregation for the `/profile` 통계 charts — genre distribution + artist / listen
distribution. Carved out of `FEAT-member-dashboard` (was its "Step 4") because it is
large enough to track independently and is gated on a separate dependency
(`FEAT-genre-taxonomy`).

## Scope

- **Genre distribution** needs first-class genres, so it **depends on
  FEAT-genre-taxonomy** (plan.md Backlog). Until genres are first-class, the genre chart
  has no real data to aggregate.
- **Artist / listen distribution** comes from review counts **+ the `spotify_play_events`
  history accumulated since FEAT-member-dashboard Step 3** (D29) — which is why that
  append-only table was seeded then rather than here (the rolling-window snapshot keeps no
  history to count).

## Dependencies

- **FEAT-genre-taxonomy** (genre branch-authoring) — blocks the genre chart.
- **`spotify_play_events`** (shipped, migration V10) — supplies durable listen history;
  already accumulating in prod since Step 3.

## Origin

Originated as `FEAT-member-dashboard` Step 4 (closed; archived at `docs/archive/done/rfcs/FEAT-member-dashboard.md`); see that RFC's decision log (**D29**) for the
events-table rationale. Not yet scoped beyond this carve — promote to a full RFC body
(aggregation queries, `/api` chart endpoints, contract, front chart wiring) when
`FEAT-genre-taxonomy` lands and this is picked up.
