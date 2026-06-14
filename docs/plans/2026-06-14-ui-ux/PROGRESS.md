# PROGRESS — myblog UI/UX & IA overnight plan (2026-06-14)

Running log. Updated as each Task completes. Artifacts saved incrementally so the
work survives context truncation.

## Status board

| Task | Output | Status | Notes |
|------|--------|--------|-------|
| Setup | dir + PROGRESS + OPEN_QUESTIONS | ✅ done | output dir created; foundational docs read |
| 1 | 01-current-frontend.md | ✅ done | 297 lines; full page/component inventory, bucket current-state, IA diagram. Key: bucket is real+API-backed but 100% owner-private (no public projection) |
| 2 | 02-reference-teardown.md | ✅ done | 277 lines; 7 sites, comparison table, BORROW/NOT-BORROW. Key: authority via voice+canon pages, not crowd-aggregation |
| 3 | 03-positioning.md | ✅ done | 350 lines; Model A/B + recommended middle "Letterboxd-foundation / IZM-surface"; 3 boundary options + tree-projection rule |
| 4 | 04-home-strategy.md | ✅ done | 327 lines; Concept A/B/C + recommend B-frame + A-surface-later; per-module data confirmation |
| 5 | 05-pages-and-components.md | ✅ done | 432 lines; tagged IA tree, per-page wireframes, component reuse/new + public-bucket DTO, flows |
| 6 | 00-SUMMARY.md (Korean) | ✅ done | morning decision doc — D1–D9 + impact×effort + OQ summary |

## Decided-items baseline (do NOT re-propose — rule 6)

The brief's `2026-05-29-feature-prioritization-v2.md` does **not exist** anywhere in
repo or git history (confirmed; also OQ-0 in the 2026-06-13 review bundle). Baseline
adopted instead = `docs/plan.md` + `docs/rfcs/` + `docs/archive/done/` + the
**2026-06-13 review bundle** (`docs/reviews/2026-06-13/`) + project memory roadmap.

Already decided (sources in parens):
- Identity = **single-author editorial publication**; community features (votes, members,
  likes, comments) deliberately dropped; no fake community data (FEAT-home-redesign D1; roadmap).
- **Album rating only** (0–5, 0.5 steps; stored 0–10 + ratingScale). Track ratings rolled
  back 2026-05-28; artist ratings ✗ (memory project-feature-roadmap).
- **Home redesign already brainstormed** (FEAT-home-redesign.md, draft): two-lane home
  (reader module stack [BNM hero / Latest / Browse-by-genre / By-the-numbers] + auth-gated
  writer strip), reader drag-personalization behind "홈 편집" toggle, empty-state first-class,
  `/reviews` stays full browser & `/` becomes editorial home, `/blog` prefix migration (own RFC).
- `/genres` Outliner shipped (tier-0, prod-live); ego-graph/sub-genres deferred
  (FEAT-genre-subgenres, frozen).
- **AI editorial critique** = product's defining feature, 0% built, Phase-0 RFC drafted
  (FEAT-ai-editorial-critique); precondition = hand-publish ≥1 real review first.
- Artist hub `/artist/[id]` = recommended/roadmap, not built.
- RSS already shipped.
- Year-end "Best Albums of [year]" list = candidate (inert until content; ~0–1 posts now
  after STAB-5 reset).
- Multi-user accounts = separate draft RFC (FEAT-multi-user-accounts).

## Log

- 2026-06-14 — Setup complete. Read CLAUDE.md, FEAT-home-redesign.md, plan.md,
  2026-06-13 review 00-SUMMARY. Confirmed bucket implementation exists in code.
  Output dir + tracking files created. Launching Task 1 + Task 2.
- 2026-06-14 — Workflow A done (11 agents, ~780k tok, ~20min). Tasks 1 & 2 written +
  spot-verified (bucket section + comparison/borrow lists read & confirmed grounded).
  9 design-decision OQs surfaced → appended to OPEN_QUESTIONS.md. Launching Workflow B
  (Tasks 3→4→5 sequential, each reads prior docs from disk) + a cross-doc reviewer.
- 2026-06-14 — Workflow B done (4 agents, ~410k tok, ~11min). Tasks 3/4/5 written; cross-doc
  reviewer returned 0 high / 2 med / 4 low findings. ALL 6 patched directly (prefix marked
  illustrative-not-decided + OQ-1.5 added; 03 tree-projection/leakage rule added; 05 public DTO
  narrowed; 04 Concept A "recently-reviewed" + Concept B near-zero runtime-fetch caveat; 02 AOTY
  2,411 figure marked unverified). Through-line confirmed consistent across all 5 docs.
- 2026-06-14 — Task 6 (00-SUMMARY.md, Korean) written by orchestrator from faithful reads of all
  5 reports. ALL TASKS COMPLETE. Markdown-only, nothing committed (per brief). Deliverables under
  docs/plans/2026-06-14-ui-ux/.
- 2026-06-14 (interactive) — Owner resolved D1–D9 + a new BNM decision. Recorded into
  `00-SUMMARY.md` ("확정 결정" section) and `docs/rfcs/FEAT-home-redesign.md` ("Owner decisions —
  2026-06-14" + BNM module row + decisions-log row; **Status left `draft`**, no self-promotion).
  Key confirmations: D1=middle model, D3=Concept B, D5=/canon ★4.0+ computed, D2/D4 public bucket =
  read-only viewer coupled to multi-user (deferred), D6/D8 = no, D9=`/review`. BNM hero = **30-day
  rolling window + daily rebuild cron**. D7 (stars-only, no numbers) = **already implemented**
  (`DragRatingInput.tsx` — rating is continuous 2-decimal, not 0.5-step; number is author-only).
  Corrected two stale memories (rating granularity).

- 2026-06-14 — **Implementation shipped (front-only, prod-live).** myblog_front PR **#151**
  squash-merged to main (`746591c`), auto-deployed, prod smoke PASSED on
  `https://www.ratemymusic.blog/` and `/canon`. Shipped A–G of the redesign:
  **A** home shell (auth-gated writer strip + personalizable module stack: 홈 편집 toggle,
  drag + keyboard reorder, hide/restore, localStorage, empty state) — `home/EditorialHome.tsx`;
  **B** Best New Music hero (30-day rolling, self-hides when empty, stars-only) — `home/BnmHero.tsx`;
  **C** Latest reviews module — `home/LatestReviews.tsx`;
  **D** Browse-by-genre **teaser** — `home/BrowseGenres.tsx`, links into the full `/genres`
  Outliner (**KEPT SEPARATE** per the reconciliation decision: teaser → full page, single data
  source `/api/genres/tree`);
  **F** editorial footer rewrite — `components/footer.astro`;
  **G** new `/canon` route (≥4.0★ canon hall, no ranking/numbers, year-end placeholder) —
  `pages/canon.astro` + `components/canon/CanonPage.tsx`, + header Canon→/canon nav,
  + ds.css helper classes ported into `styles/global.css`.
  **E** "By the numbers" (real honest counts) is being built now in this same push (just completed
  by the main agent — replaces the placeholder). Hard rule honored: stars only, never a numeric
  score to readers. Reviewer pass: 0 HIGH / 3 MED (all fixed). `/blog → /review` prefix migration
  (RFC step 6) intentionally **NOT** done — separate future work. RFC Status left `draft`
  (done-promotion pending owner approval, rule 5).
