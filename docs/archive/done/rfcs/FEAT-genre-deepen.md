# FEAT-genre-deepen: deepen the genre taxonomy to 4 tiers + dense edge graph

- **Status**: **done — prod-live + archived 2026-06-15** (owner-directed)
- **Owner**: 박지훈
- **Created / shipped**: 2026-06-15
- **Reverses**: the `FEAT-genre-subgenres` single-parent **2-tier** decision (`docs/archive/done/rfcs/FEAT-genre-subgenres.md`).

## Why

Owner, 2026-06-15: "촘촘하게 하자 … 계층 두개로 굳이 둘 필요 없어 훨씬 더 깊이 있어도 돼." The
2-tier (12 + 211) taxonomy was thin and the relationship graph was sparse (40
edges, **0** nodes with 2+ edges). The owner wanted real RYM-grade depth + a
dense influence/related web. Containment stays **single-parent** (a clean tree);
the cross-cutting relationships live in `genre_edges` (now dense).

## Result (prod-live)

- **1,230 genres** (was 223): 13 top-level (added **Blues** as a 13th), 246
  tier-1, 780 tier-2, 179 tier-3, 12 tier-4.
- **2,064 edges** (was 40): 1,434 influenced_by / 590 related; **874 nodes now
  carry 2+ relationships** (was 0).
- Everything additive — the existing 12 tier-0 + 211 tier-1 rows + the 40 V20
  edges are untouched.

## How

1. **Research** — a 13-agent workflow: one taxonomy expert per top-level branch
   deepened it to tier 2/3/4 (RYM/Wikipedia/AllMusic/Discogs-grounded, real
   genres only) and proposed intra/inter-branch edges; a synthesis pass added the
   cross-branch edge web + flagged issues.
2. **Cleanup** — merged 6 duplicate concepts, added the missing **Blues** branch
   (Delta/Chicago/Electric→Texas·Swamp / Jump / Boogie-Woogie / British / Blues-
   Rock / R&B-classic→Doo-Wop …) + Kwaito/Calypso/Soca/Rare-Groove, reparented
   Disco (→ Electronic, was buried under dance-pop) / Riddim / Trip-Hop-UK, and
   dropped dangling edges.
3. **Migration** — `shared_db` **V21** (data-only, no DDL; tier-ordered
   `INSERT … ON CONFLICT DO NOTHING`). Validated against prod in a rolled-back tx
   (1230/13/2064) before the real apply.
4. **Frontend N-tier** (`myblog_front` #165) — `gm-model.buildDoc` recurses the
   full forest; TreeA expands at any depth; TreeB drills (col-2 re-roots) +
   breadcrumb; TreeC is a recursive depth-as-column dendrogram; the `/write`
   `GenrePicker` browse is a collapsible tree (roots collapsed → lazy-expand) so
   1.2k nodes never paint at once.

## Verification

- **shared_db V21**: prod rollback-validation (1230/13/2064, all joins resolve) →
  real apply (psql `BEGIN…COMMIT`) → prod = 1230/13/2064. CI schema-parity pass
  (data-only). (shared_db #36)
- **Frontend**: headless CDP on a 4-tier mock — A 4-level nesting, B drill +
  breadcrumb, C 4 columns w/ tier-3, picker collapsed→deep-expand→deep-select.
  lint 0 / astro check 0 / build.
- **Prod smoke**: live `/genres` renders "13개 최상위 장르"; expanding
  Electronic → House → Deep House surfaces Balearic House (tier-3) at depth-3.
  Deep nodes show 0 albums (nothing tagged yet — populated organically).

## Notes

- The **related-review recommendation** (`FEAT-genre-recommendation`, old
  subgenres Steps 5–6) stays **Frozen** — gated on review volume, unchanged here.
- Definitions remain on-demand / Claude-authored; most are empty.
- A handful of slug collisions across branches (≈45) were deduped (first-wins) —
  same concept claimed by two branches; acceptable.

## Decisions log

| Date | Decision | By |
|---|---|---|
| 2026-06-15 | Deepen 2→4 tiers + densify edges; keep single-parent containment + edge graph for cross-links | owner |
| 2026-06-15 | Full depth (~1,230), not a curated trim | owner |
| 2026-06-15 | **Blues** added as a 13th top-level (root ancestor of rock/soul/R&B; musically correct over burying it under R&B-Soul) | owner |
| 2026-06-15 | Frontend ships before the V21 apply (renders whatever depth the API has); no degraded window | owner |
