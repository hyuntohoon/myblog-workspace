# OPEN QUESTIONS — myblog UI/UX & IA (2026-06-14)

Unattended run. Each blocker is recorded here with the **assumption adopted** to keep
moving (working rule 1). Owner reviews in the morning.

---

## OQ-0 — Referenced prioritization doc does not exist

**Q:** Working rule 6 says read `2026-05-29-feature-prioritization-v2.md`. That file is
absent from the entire workspace, all 4 service repos, and git history.

**Assumption adopted:** The intent of rule 6 ("don't re-propose already-decided items")
is served by the actual decided-items sources: `docs/plan.md`, `docs/rfcs/` (esp.
`FEAT-home-redesign.md`), `docs/archive/done/`, the **2026-06-13 overnight review bundle**
(`docs/reviews/2026-06-13/` — code audit + market research + feature candidates), and the
project memory roadmap. This task **builds on** the 2026-06-13 bundle rather than redoing
its audit/market-research; the new angle is UI/UX & IA through the bucket↔magazine lens.
Same conclusion was reached as OQ-0 in the 2026-06-13 bundle. If the owner has a v2 doc
locally / in Drive, Task 5's page/component proposals should be cross-checked against it.

---

## OQ-A — Postgres MCP not connected (Task 4 data-confirmation)

**Q:** Task 4 says "run read-only Postgres MCP queries to confirm home data exists." No
Postgres MCP is connected to this session.

**Assumption adopted:** The home is a **static Astro site fed by the `blog` content
collection** (MDX frontmatter), not the live DB — so "does the data exist" is correctly
answered by the content-collection schema (`src/content.config.ts`) + what `lib/reviews.ts`
actually reads, plus the contract (`api.gen.ts`) for the one DB-backed input (`/genres`
`album_count`, already shipped in FEAT-genre-system tier-0). Task 4 confirms data this way.
DB-level probing is unnecessary and was skipped (no writes/DDL were ever in scope anyway).

---

## Design-decision OQs surfaced by Tasks 1 & 2 (for the owner; Tasks 3–5 present as options)

These are genuine product decisions, not blockers. **Assumption adopted for all:** Tasks 3–5
present each as an explicit option with trade-offs rather than deciding; the owner picks in the
morning. Listed here so they're not lost.

From **Task 1** (frontend audit):
- **OQ-1.1** — Are `/blog/category` + `/blog/category/[category]` truly dead/vestigial or
  intentionally kept? Un-nav'd, overlap the reviews browser; no RFC confirms removal. (Note:
  FEAT-home-redesign already decided to *remove* `/blog/category` and migrate the whole `/blog/`
  prefix — so this leans "remove"; Task 5 treats it as such.)
- **OQ-1.2** — How are trailing-slash-less review links (`/blog/${slug}` emitted by
  `ReviewsIndex` under `trailingSlash:'always'`) normalized at the edge? Needs a CloudFront/redirect check.
- **OQ-1.3** — Does the near-zero-content `/profile` bucket board render acceptably (empty
  crates + recent strip only)? Only static-read verified; no live near-zero render inspected.
- **OQ-1.4** — Is the client-only auth guard on `/profile`/`/write` (static props ship to all,
  guard redirects post-load) an accepted posture, or a problem the redesign should fix?
- **OQ-1.5** *(surfaced by the cross-doc review)* — The exact new read-page prefix is **undecided**:
  `/review/[slug]` vs `/reviews/[slug]`. `FEAT-home-redesign` decided *that* the `/blog/` prefix
  migrates but left the prefix string an open TODO. `/reviews/[slug]` would **collide with the
  surviving `/reviews` browser**, so `/review/[slug]` (singular) is the cleaner pick. **Assumption
  adopted:** Task 5 writes `/review/[slug]` *illustratively only* and flags the collision; the real
  choice belongs to the dedicated `/blog`-migration RFC, not this redesign.

From **Task 2** (reference teardown):
- **OQ-2.1** — Per-album score: inside the article only (IZM-style, home stays editorial) or
  also a sortable facet on `/reviews`? Risk: a facet can tip the home toward leaderboard tone.
- **OQ-2.2** — Is an explicit single-author "canon" surface wanted (a 명반-style ≥4.0★ standing
  tab + non-ranked year-end Picks), or premature at near-zero published content?
- **OQ-2.3** — Make the single-author subjective-scale stance explicit on-site (a short "how I
  rate" page), turning "no universal scale" into the selling point?
- **OQ-2.4** — Is email capture (a Bandcamp-"Notes"-style curated newsletter) in scope for this
  redesign, or out-of-scope given the current no-account, RSS-only posture?
- **OQ-2.5** — Confirm the bucket entry's atomic public unit = `0.5–5★ + tags + optional note`
  with prose layered later. Does the current bucket schema support a **rated-but-unwritten**
  entry as a first-class *public* record? (Today buckets are owner-private; see Task 1 bucket gap.)

---

## Per-document OQ sections (detail)

Tasks 3/4/5 each carry their own detailed `## Open questions` section at the end of the respective
file — they refine the design-decision OQs above into build-level choices (positioning model + boundary
options [03], home structure + BNM-empty-state + writer-strip count source + `album_count` build-snapshot
[04], `/collections` vs fully-private + `/canon` now-vs-defer + header-nav vs footer + the new read-page
prefix [05]). `00-SUMMARY.md` §5 consolidates the morning decision list (D1–D9) with recommendations.
