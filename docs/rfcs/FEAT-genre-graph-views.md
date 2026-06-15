# FEAT-genre-graph-views: genre ego-view + related-review recommendation + edge authoring

- **Status**: frozen (deferred — gated on review volume)
- **Owner**: 박지훈
- **Created**: 2026-06-15
- **Split from**: `FEAT-genre-subgenres` (old Steps 4–6, rescoped out 2026-06-15)

## Goal

The **graph *experiences*** built on top of the genre relationship data that
`FEAT-genre-subgenres` produces (the seeded `genre_edges` graph + per-review
`post_genres` tags). Three surfaces:

1. **`/genres` ego-view + populated Outliner** — the Outliner shows *populated*
   tier-1 sub-nodes; clicking any node opens a small **local** ego-diagram of
   that node + its immediate neighbours (parent, children, `influenced_by`,
   `related`) from `genre_edges`. Reuses the deferred "장르 맵" Claude Design
   layouts (ego-view / Miller-columns / diagram — see `GenreMap.tsx` comment).
2. **Related-review recommendation** — a "related reviews" block on
   `/review/{slug}`: reviews sharing a `post_genres` sub-genre + reviews tagged
   with edge-linked sub-genres, ranked (shared-tag first, then edge-distance).
3. **Owner edge authoring** — add/remove `influenced_by` / `related` (and the
   rare `parent` fallback) edges on a node, inline in the ego-view →
   `POST/DELETE /api/genres/{id}/edges` (+ `apigateway.tf` JWT routes).

## Why deferred

Both #1 and #2 have **nothing to show until reviews are tagged**: the populated-
only ego-view renders no tier-1 nodes with zero `post_genres`, and the
recommendation has nothing to rank. With ~1 published review today, this is
premature — same review-volume precondition as `FEAT-ai-editorial-critique`.
#3 (edge authoring UI) is low-priority by owner decision (2026-06-15): genre
definitions + edges are **Claude-Code-driven** (migrations/scripts), not manual
UI ("옵션 많으면 좋지만 규정은 claude로"). Edges can be added/retyped via SQL
in the meantime.

## Current state (substrate is live)

- `genre_edges` (40 seeded: 33 influenced_by / 7 related) + `post_genres`
  (empty) + the 211-genre tier-1 tree — all prod-live (FEAT-genre-subgenres
  Steps 1/1b).
- `GET /api/genres/tree` already returns the tier-1 tree **+ edges** (public).
  So #1's read API exists; only the front viz + (for #3) the write endpoints
  are missing.
- `/genres` ships the Outliner (tier-0 only today; tier-1 nodes appear once
  populated).

## Steps (when unfrozen)

1. **Ego-view + populated Outliner** (front) — extend `/genres` from the live
   `/tree` (genres + edges). Decide: show full palette vs populated-only in the
   ego-view (the global tree stays populated-only / readable).
2. **Related-review recommendation** (front + maybe a light endpoint) — the
   `/review/{slug}` block. Tune ranking once ≥10–20 reviews are tagged.
3. **Edge authoring** (backend + front) — `POST/DELETE /api/genres/{id}/edges`
   + `apigateway.tf` `genres_edges_post`/`_delete` (JWT, `buckets_post` pattern)
   + ORM/service + the ego-view inline editor. Lowest priority.

## Open questions

- Ego-view: full-palette vs populated-only inside the local diagram.
- Recommendation ranking weights (shared-tag vs edge-distance vs recency).
- Whether edge authoring ever needs a UI, or stays Claude-Code-driven.

## Decisions log

| Date | Decision | By |
|---|---|---|
| 2026-06-15 | Split out of FEAT-genre-subgenres (old Steps 4–6); frozen until review volume. Edge authoring low-priority (Claude-Code-driven) | owner |
