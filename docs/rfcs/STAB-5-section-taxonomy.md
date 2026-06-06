# STAB-5: category → section taxonomy + review tags

- **Status**: accepted
- **Owner**: TBD (주인장)
- **Created**: 2026-06-05
- **Plan row**: `plan.md` → STAB-5
- **Spawned from**: `STAB-1-stabilization.md` §Prioritization & stabilization sequencing **item 5** + the §"Final decision — category/board/section + review tags model". STAB-1 prospectively called this **`FEAT-section-taxonomy`**; renamed to **STAB-5** for consistency with the STAB-N ↔ §Seq-item-N family. STAB-1 + this RFC are **accepted** (2026-06-05, owner-approved).
- **Depends on**: **STAB-2** (P0 auth — removes the public `POST /api/categories` create path; do not start before STAB-2 Step 3 is decided). ~~**Coordinate with STAB-4**~~ — **STAB-4 is DONE + archived** (`docs/archive/done/rfcs/STAB-4-schema-and-doc-drift.md`, verified 2026-06-06); its `schema.sql` backfill already landed (`categories` DDL now lives in `_generated_schema.sql:39`). So the only live coordination left is that **STAB-5 Step 1's `_generated_schema.sql` regen renames that `categories` DDL → `sections`** — nothing to sequence against an in-flight STAB-4.

---

## Goal

Implement the STAB-1 §model decision: reinterpret the `category` axis as a curated public **`section`** taxonomy — one section per post (keep the single FK), a read-only writer picker fed by a migration-seeded set (no public create API), review classification via **review tags** reusing the empty `tags`/`post_tags` M:N — and reset the existing all-junk category/post/MDX data so the new model launches clean. After this RFC the four competing "category" vocabularies (DB / `categories.json` / writer `SECTIONS` / build-time `categories.json.ts`) collapse to one authoritative source.

## Non-goals

- No multi-section-per-post (single FK stays — STAB-1 OQ2).
- No new `review_tags` table (reuse `tags`/`post_tags` — STAB-1 OQ3).
- No public/admin section-creation API or UI (sections seeded by migration; future creation internal-only — STAB-1 §model point 5).
- Not the auth fix itself (STAB-2 owns removing `POST /api/categories`); this RFC consumes that removal.
- Not genre taxonomy (FEAT-genre-taxonomy is a separate, deferred axis; sections ≠ genres).
- No change to the private `review_buckets` kanban (orthogonal to public taxonomy — MODEL-5).
- No caching (out of scope per STAB-1).

## Evidence gathered (2026-06-05 — authoritative)

**Prod data (read-only):**

| Check | Result |
|-------|--------|
| `categories` rows | **3, all junk**: `default` (id 1), `smoke-bug10` (id 2), `Reviews` (id 3 / slug `reviews`). |
| posts | **13, all test data**, **all `category_id=1` (`default`)** — `212121`, `432432432432`, `untitled`, `테스트2`, `2121`, `6666`, …; 11 published + 2 draft (`SMOKE test — do not keep`, `E2E Test - Radiohead OK Computer`). Categories 2 & 3 are orphaned (zero posts). |
| content MDX | **11 dirs** in `myblog_front/content/blog/` (`2026-05-25--2121` … `2026-05-27--untitled`), one per published test post. All junk. |
| `tags` / `post_tags` | 0 / 0 (empty — ready to reuse). |

> So there is **no real content to preserve** — the cleanup (STAB-1 §model point 7) can delete all 13 posts + 11 MDX dirs + 3 junk categories with no data-loss concern. (The 2 drafts are the same ones AUTH-9 leaks.)

**Code (verified):**
- Writer dropdown is hardcoded: `SECTIONS = ['Reviews', 'Best New Music', 'Features', 'Tracks']` (`myblog_front/src/components/writer/types.ts:64`); it never reads `GET /api/categories`.
- Dead category code (definitions only, **no call sites**): `addCategory` (`myblog_front/src/lib/api.ts:29`), `fetchCategories` + `createCategory` (`myblog_front/src/scripts/write/api.ts:15,25`).
- Two divergent slugify paths writing `categories` (MODEL-11): `CategoryService` uses `slugify` (python-slugify, strips non-ASCII — `category_service.py:16,42`); the post get-or-create path uses `_slugify = re.sub(r"[^a-z0-9]+","-", …)` (`category_repository.py:9,29`). Both mangle Korean → a curated seed with explicit slugs sidesteps this.
- Migration ledger: max applied = **V12** (no runner/ledger table; hand-numbered `V{N}__`, applied sequentially — gapless is a hard premise, `reference-shared-db-cross-repo-rollout`). 🔴 **Numbering conflict (OQ4):** FEAT-genre-taxonomy's Decisions log resolved genre = **V13** *specifically because a V13 gap would violate the gapless premise* — but genre is **deferred** while STAB-5 is **active**, so STAB-5's migration is the next one actually applied after V12 and must be **V13** (reserving V13 for a not-yet-applied deferred feature is exactly the gap the genre RFC forbids). **Default: STAB-5 = V13; genre re-points to V14/next-free when it un-defers** (owner reconciles the genre RFC's V13 claim — see OQ4).
- Taxonomy is baked into MDX frontmatter at publish (`publish_service.py:make_mdx_frontmatter`), so a section restructure must **re-emit/remove MDX**, not just change the DB (MODEL-8).

## Current state

`posts.category_id` is a nullable single FK → `categories` (already "at most one"). The live `categories` table is 3 junk rows auto-created via get-or-create; the writer ignores it and uses a hardcoded array; `myblog_front`'s public category pages build from frontmatter; `categories.json` advertises six unused slugs as a decorative zod enum; `POST /api/categories` is an unauthenticated create (STAB-2 AUTH-1). `tags`/`post_tags` exist but are empty/dead.

## Target state

- `posts.section_id` (renamed from `category_id`) single FK → a `sections` table (renamed/repurposed from `categories`), seeded by migration with a curated set; no get-or-create, no public create API.
- Writer offers a **read-only** section picker fed by one authoritative list; the hardcoded `SECTIONS` array + dead `addCategory`/`fetchCategories`/`createCategory` are deleted; `categories.json` + the build-time `categories.json.ts` reconciled to the seeded set (or removed).
- Review classification (track review / album review / best album / year-end list, …) is modeled as **tags on review posts** via the existing `tags`/`post_tags` M:N.
- All pre-existing junk categories/posts/MDX are deleted; the site builds from the clean seeded set.

## Steps

Cross-repo, ordered, each its own PR. Steps 1-4 each touch a **nested service repo** (shared_db / backend / front) — **branch + commit IN THAT repo** (the workspace rule-#1 hook only guards the workspace checkout; a `git checkout -b` in the workspace leaves the service repos on `main` — [[feedback-nested-repo-branch-per-repo]], [[reference-nested-repo-worktree-recipe]]). **One step per session** unless explicitly OK'd (rule #4). The shared_db migration must be **applied to prod Neon before** the consuming pin bumps merge (`reference-shared-db-cross-repo-rollout`). **Step 6 (data/MDX reset) is destructive — explicit human approval required (rule #3).**

> ⚠️ **CRITICAL — rename is NOT additive; Step 1 prod-apply opens a breaking window (surfaced 2026-06-06 audit).** Unlike a column *add* (old code ignores it), the V13 rename `posts.category_id`→`section_id` + `categories`→`sections` **deletes the names the live backend (pinned `@v0.10.0`, ORM maps `category_id`→column `category_id`) still queries.** The instant V13 lands on prod Neon, every runtime `SELECT … posts.category_id` 500s — until Step 2 (backend pin bump @section_id) deploys. **Blast radius (verified):** public blog + `/blog/category` pages are **build-time-static** (Astro `getCollection` from MDX) → unaffected; the **only** runtime `/api/posts*` callers are the authed admin writer + draft reads ([[reference-stab2-step1-public-read-safe]], [[reference-front-all-traffic-via-cloudfront]]) → the window breaks **only the single-author admin writer**, not the public site. Mitigation options (owner picks before Step 1 prod-apply): **(A)** keep in-place rename, accept a brief admin-only outage, run Step 1 prod-apply + Step 2 deploy **back-to-back** (relax the rule-#4 prod-observe gap for *this one pair* — data is junk + single author); **(B)** expand→contract (add `section_id` alongside `category_id`, dual-read backend, drop later — zero outage, more steps); **(C)** bundle Step 1+2 into one coordinated rollout. **Until decided, Step 1 may be fully *prepared* (branch/PR/tests) but the prod-apply must wait.** Note: building the migration file + ORM rename + schema regen is identical regardless of (A)/(C); only (B) changes the migration shape.

### Step 1 — shared_db: seed migration + `Section` model
`myblog_shared_db`: add the sections seed migration (curated seed; explicit slugs — Unicode-safe), introduce a `Section` ORM model (or rename `Category`→`Section`), regenerate `_generated_schema.sql`, bump pyproject + tag. **Migration number = the next contiguous number at fix time** (`ls migrations | sort -V | tail -1` → currently V12 → **V13**; reconcile with the genre RFC's V13 claim per OQ4 first). Decide the canonical section set (OQ1). Apply to prod Neon main branch before any pin bump.
**Verification:** `SELECT id,name,slug FROM sections ORDER BY id` matches the seed; `_generated_schema.sql` regenerated.
**Rollback:** down-migration drops the seed (human-approved, rule #3).

### Step 2 — backend: `section_id` + read-only sections endpoint; consume `POST /api/categories` removal
Rename `posts.category_id`→`section_id` usage, replace get-or-create with a FK-to-seeded-section lookup (reject unknown), expose a read-only `GET /api/sections`. The `POST /api/categories` removal is owned by **STAB-2 Step 3** — sequence so this lands after/with it. Bump shared_db pin (after Step 1 applied to prod).
**Verification:** pytest; `GET /api/sections` returns the seed; create-with-unknown-section is rejected; no get-or-create path remains.
**Rollback:** revert pin + route.

### Step 3 — frontend: read-only section picker + delete dead code
Replace the hardcoded `SECTIONS` (`types.ts:64`) with a picker fed by `GET /api/sections` (or a build-time seed), delete `addCategory`/`fetchCategories`/`createCategory`, reconcile `src/categories.json` + the build-time `src/pages/api/categories.json.ts` (derives a separate list from frontmatter) to the seeded set. Click-through in a real browser (rule: UI change). Regenerate `api.gen.ts` if the contract changed ([[feedback-frontend-api-gen-sync]]); `pnpm lint` before commit ([[feedback-front-lint-before-commit]]).
**Verification:** writer shows only seeded sections, can't create; `pnpm lint` + `astro check` pass; browser click-through.
**Rollback:** trivial — revert the PR (+ regen `api.gen.ts`).

### Step 4 — review tags via `tags`/`post_tags`
Wire the existing empty M:N for review tags. Initial tag vocabulary (OQ2, resolved): `album review` / `track review` / `reissue` / `best album` / `year-end list`. Backend read/write + writer UI + frontend filter on `/reviews`.
**Verification:** a review post can carry multiple tags; tags render on `/reviews`.
**Rollback:** trivial — revert the PR.

### Step 5 — contract regen
Export `openapi.json` for the new `/api/sections` (+ tag fields), workspace merge regenerates `docs/contracts/openapi.json`, frontend types derived. (Per ARCH-12 contract-first; merge workspace first — [[reference-workspace-contract-merge-order]].)
**Verification:** openapi-verify CI clean; `api.gen.ts` in sync.
**Rollback:** trivial — revert the PR (+ regen `api.gen.ts`).

### Step 6 — data + MDX reset (DESTRUCTIVE — human approval)
Delete the 13 test posts and the 11 junk MDX dirs and the 3 junk `categories`/`sections` rows. Note the **13-vs-11 asymmetry**: only the 11 published posts have MDX dirs; the 2 drafts have no MDX (drafts aren't published), so their deletion is DB-row-only. Use the publish hard-delete path (`posts.py` `delete_post` removes both the MDX and the DB row for published posts) so MDX + DB stay consistent; verify `/blog/category` (→ `/blog/section`) pages rebuild from the clean seed. Prod smoke after.
**Verification:** prod has only seeded sections + zero junk posts; site rebuilds clean.
**Rollback:** none (deletion is intentional; the test data has no value — but get explicit go-ahead first, rule #3).

## Open questions

1. ✅ **OQ1 (Step 1) — RESOLVED 2026-06-06 (owner):** canonical seeded set = **`Reviews / Best New Music / Features / Tracks`** (slugs `reviews` / `best-new-music` / `features` / `tracks`) — the STAB-1 writer array verbatim. English labels.
2. ✅ **OQ2 (Step 4) — RESOLVED 2026-06-06 (owner):** initial review-tag vocabulary = **`album review` · `track review` · `reissue` · `best album` · `year-end list`** (5 tags). Orthogonality principle accepted: tags are a cross-cutting axis (release format / editorial accolade / list form) distinct from the single-FK section. Owner kept `track review` despite the Tracks-section name overlap — they coexist: *Tracks section = the post's primary subject is a track; `track review` tag = a cross-cutting label that can also appear on posts in other sections*. Dropped from the STAB-1 floats: `best albums` (singular `best album` kept; no plural duplicate). Start lean; extend as content accrues. *(Lane C / Step 4 unblocked.)*
3. ✅ **OQ3 (Step 1) — RESOLVED 2026-06-06 (owner):** **in-place rename** `Category`→`Section` / `categories`→`sections` / `posts.category_id`→`section_id` (single FK kept). Audit confirmed the `Category` ORM ref is contained: `models.py:91` (class) + `models.py:258` (posts FK) only; backend `CategoryService` / `category_repository` follow in Step 2. (See ⚠️ rename-breaking-window note above — rename ≠ additive.)
4. ✅ **OQ4 (Step 1) — RESOLVED 2026-06-06 (owner):** **STAB-5 = V13**, genre re-pointed to **V14**. genre RFC text updated 2026-06-06 (`FEAT-genre-taxonomy.md` V13→V14 sweep + decisions-log supersede). The two RFCs no longer both own V13.

## Decisions log

| Date | Decision | Step |
|------|----------|------|
| 2026-06-05 | Spawned from STAB-1 §Sequencing item 5 + §model decision (section rename, single FK, no public create API, review tags reuse `tags`/`post_tags`, seed by migration, reset junk data — all owner-ratified 2026-06-05). | all |
| 2026-06-05 | Evidence: **all 13 prod posts + 11 MDX + 3 categories are junk** → Step 6 reset has no data-loss risk. (Live DB probe supersedes STAB-1 MODEL-7's frontmatter-derived "8 Reviews + 3 default" tally: all 13 posts are on `category_id=1`/`default`; `Reviews`/`smoke-bug10` are orphaned — frontmatter-string vs DB-FK provenance.) | Step 6 |
| 2026-06-05 | **Migration number = V13** (next contiguous after live V12), NOT V14 — corrects the initial "reserve V13 for deferred genre" framing, which would have left a forbidden V13 gap. Genre (deferred) re-points to V14/next-free; owner reconciles the genre RFC's V13 claim (OQ4). | Step 1 |
| 2026-06-06 | **Current-state audit (read-only live prod + code) — all RFC "Current state"/"Evidence" claims VERIFIED TRUE:** categories 3 junk (2·3 orphaned), posts 13 all `category_id=1` (11 pub + 2 draft), 11 MDX dirs, `tags`/`post_tags` 0/0, writer `SECTIONS` hardcoded (`types.ts:64`), `addCategory`/`fetchCategories`/`createCategory` defs-only (0 call sites), `POST /api/categories` unauth (`categories.py:18`, no auth dep), migration max V12, Korean-slugify mangling confirmed in MDX dir names. ([[feedback-rfc-current-state-audit]]) | all |
| 2026-06-06 | **STAB-4-coordination caveat dropped** — STAB-4 is DONE+archived; its schema.sql backfill already landed (`categories` DDL in `_generated_schema.sql:39`). No in-flight coordination; STAB-5 Step 1 just renames that DDL. | Step 1 |
| 2026-06-06 | **OQ1/OQ3/OQ4 resolved by owner.** OQ1 set = `Reviews/Best New Music/Features/Tracks`. OQ3 = in-place rename. OQ4 = STAB-5 V13 / genre V14 (genre RFC updated same day). | Step 1 |
| 2026-06-06 | ⚠️ **Rename breaking-window surfaced.** V13 rename is NOT additive: prod-apply 500s the old-pinned (`@v0.10.0`) backend's `category_id` queries until Step 2 deploys. Blast radius = admin writer only (public pages static). Owner to pick mitigation (A) back-to-back Step1+2 / (B) expand-contract / (C) bundle — before Step 1 prod-apply. | Step 1/2 |
| 2026-06-06 | **OQ2 resolved by owner.** Review-tag vocabulary = `album review` / `track review` / `reissue` / `best album` / `year-end list` (5). Orthogonality principle accepted (tags = cross-cutting format/accolade/list axis, distinct from single-FK section). `track review` kept despite Tracks-section overlap (coexist by definition); `best albums` plural dropped. Lane C / Step 4 unblocked. | Step 4 |
