# FEAT-genre-recommendation: genre-based related-review recommendation (+ edge authoring)

- **Status**: frozen (deferred — gated on **review volume**)
- **Owner**: 박지훈
- **Created**: 2026-06-15
- **Split from**: `FEAT-genre-subgenres` (old Step 5; old Step 6 edge-authoring folded in here)

## Goal

The "**장르 기준 추천 평론**" — the genre-based related-review recommendation. From
a review, surface **connected reviews** via shared sub-genre tags + the
sub-genre relationship graph (`influenced_by` / `related` edges):

- A "related reviews" block on `/review/{slug}`: reviews sharing a `post_genres`
  sub-genre, plus reviews tagged with **edge-linked** sub-genres, **ranked**
  (shared-tag first, then edge-distance, then recency).

The **edge graph is the recommendation engine** — and it is already seeded +
live. This feature is just the consumption logic + the on-page block.

Also parked here (low-priority): **owner edge authoring** —
`POST/DELETE /api/genres/{id}/edges` to add/retype edges from the UI. The owner
maintains edges via Claude-Code (migrations/scripts) for now, so a UI is
optional ("옵션 많으면 좋지만 규정은 claude로", 2026-06-15).

## Why deferred

The recommendation has **nothing to rank until reviews are tagged** — with ~1
published review today, "related reviews" would be empty. Unfreeze once a body
of tagged reviews exists (ranking also needs ≥10–20 to tune). Same review-volume
precondition as `FEAT-ai-editorial-critique`.

> Note: the genre-map **visualization** (`/genres` ego-view) is NOT here — it was
> revived into `FEAT-genre-subgenres` (Step 4), since it visualizes the live
> taxonomy + edges independent of review volume.

## Current state (substrate is live)

- `genre_edges` (40 seeded: 33 influenced_by / 7 related) + `post_genres`
  (filled per-review by FEAT-genre-subgenres Step 2) + the 211-genre tier-1 tree
  — all prod-live. `GET /api/genres/tree` returns the tree + edges.
- So the recommendation has all its **inputs**; only the ranking/query + the
  `/review/{slug}` block + (optionally) the edge-authoring write endpoints are
  missing.

## Steps (when unfrozen)

1. **Related-review recommendation** (front + maybe a light endpoint) — query
   shared-sub-genre + edge-linked reviews, rank, render the `/review/{slug}`
   block. Tune weights once reviews accrue.
2. **Edge authoring** (backend + front, lowest priority) — `POST/DELETE
   /api/genres/{id}/edges` + `apigateway.tf` JWT routes (`buckets_post` pattern)
   + ORM/service + an inline editor in the `/genres` ego-view (the FEAT-genre-
   subgenres Step-4 surface). Only if Claude-Code edge maintenance proves
   insufficient.

## Open questions

- Recommendation ranking weights (shared-tag vs edge-distance vs recency).
- Build-time (content collection) vs a runtime endpoint for the block.
- Whether edge authoring ever needs a UI, or stays Claude-Code-driven.

## Decisions log

| Date | Decision | By |
|---|---|---|
| 2026-06-15 | Split out of FEAT-genre-subgenres (old Step 5); frozen until review volume. Genre-map viz (old Step 4) revived into FEAT-genre-subgenres instead — it's review-volume-independent. Edge authoring (old Step 6) folded here, low-priority (Claude-Code-driven) | owner |
