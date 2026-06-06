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

### Step 1 — shared_db: seed migration + `Section` model — **DONE ✅ 2026-06-06**
**DONE:** shared_db PR #21 merged (`320a76b`) + tag **`v0.12.0`**. V13 = in-place rename `categories`→`sections` / `posts.category_id`→`section_id` + idempotent `ON CONFLICT DO NOTHING` seed; `Section` ORM. **V13 applied to prod Neon 2026-06-06** (back-to-back with Step 2 — see Rollout log): `categories`→`sections`, `category_id`→`section_id`, `INSERT 0 3` (junk `Reviews` id 3 kept via ON CONFLICT; Best New Music/Features/Tracks → id 5/6/7). Junk `default`(1)/`smoke-bug10`(2) remain until Step 6.

`myblog_shared_db`: add the sections seed migration (curated seed; explicit slugs — Unicode-safe), introduce a `Section` ORM model (or rename `Category`→`Section`), regenerate `_generated_schema.sql`, bump pyproject + tag. **Migration number = the next contiguous number at fix time** (`ls migrations | sort -V | tail -1` → currently V12 → **V13**; reconcile with the genre RFC's V13 claim per OQ4 first). Decide the canonical section set (OQ1). Apply to prod Neon main branch before any pin bump.
**Verification:** `SELECT id,name,slug FROM sections ORDER BY id` matches the seed; `_generated_schema.sql` regenerated.
**Rollback:** down-migration drops the seed (human-approved, rule #3).

### Step 2 — backend: `section_id` + read-only sections endpoint; consume `POST /api/categories` removal — **DONE ✅ 2026-06-06**
**DONE:** backend PR #56 merged (squash `d3cce15`), deployed. pin `@v0.10.0`→`@v0.12.0`; `Category{Repository,Service}`→`Section{Repository,Service}`; `post_service`/`post_repository` `category_id`→`section_id`; **get-or-create removed → seeded-section lookup by name, reject unknown** (400 on create+update); new read-only **`GET /api/sections`**; **`POST /api/categories` + dead `GET /api/categories` removed** (STAB-2 Step 3 hole closed); `content_sync` reads `post.section`; `openapi.json` regenerated. **Decoupling:** post req/resp JSON field + MDX frontmatter key stay `category` (lookup by section *name* = the picker's label → compatible with Step 3's wire format; contract rename deferred to Step 5). CI green (pyright 0 errors, contract verify). pytest isolated 54/54 (full-suite 11 fails = pre-existing config-singleton ordering pollution, identical on baseline). **Prod smoke green:** `GET /api/sections`→200 (seed), `GET`/`POST /api/categories`→404, authed `GET /api/posts`→200 (11 posts, `section_id` path restored).

Rename `posts.category_id`→`section_id` usage, replace get-or-create with a FK-to-seeded-section lookup (reject unknown), expose a read-only `GET /api/sections`. The `POST /api/categories` removal is owned by **STAB-2 Step 3** — sequence so this lands after/with it. Bump shared_db pin (after Step 1 applied to prod).
**Verification:** pytest; `GET /api/sections` returns the seed; create-with-unknown-section is rejected; no get-or-create path remains.
**Rollback:** revert pin + route.

### Step 3 — frontend: read-only section picker + delete dead code — **DONE ✅ 2026-06-06**
**DONE:** front PR #97 merged (`60864df`), deployed (ran parallel to Lane A). New single-source `src/lib/sections.ts` (**build-time seed**, no runtime `GET /api/sections` dep → merged independent of backend; contract-neutral, no `api.gen.ts` regen); writer picker reads `SECTION_LABELS` (read-only, no create); `content.config.ts` enum sources the labels; deleted dead `addCategory`/`fetchCategories`/`createCategory` + `categories.json` + `pages/api/categories.json.ts`. **Wire format:** picker emits the section LABEL as post `category` → Step 2 backend looks it up by section *name* (= label) → compatible. Prod smoke green (prod `/api/categories.json`→404 = live deploy; CDP click-through of `/write` renders exactly the 4 sections).

Replace the hardcoded `SECTIONS` (`types.ts:64`) with a picker fed by `GET /api/sections` (or a build-time seed), delete `addCategory`/`fetchCategories`/`createCategory`, reconcile `src/categories.json` + the build-time `src/pages/api/categories.json.ts` (derives a separate list from frontmatter) to the seeded set. Click-through in a real browser (rule: UI change). Regenerate `api.gen.ts` if the contract changed ([[feedback-frontend-api-gen-sync]]); `pnpm lint` before commit ([[feedback-front-lint-before-commit]]).
**Verification:** writer shows only seeded sections, can't create; `pnpm lint` + `astro check` pass; browser click-through.
**Rollback:** trivial — revert the PR (+ regen `api.gen.ts`).

### Step 4 — review tags via `tags`/`post_tags` — **BACKEND + CONTRACT DONE ✅ 2026-06-06; writer picker (UI) PENDING**
Wire the existing empty M:N for review tags. Initial tag vocabulary (OQ2, resolved): `album review` / `track review` / `reissue` / `best album` / `year-end list`.

**Pre-impl owner decisions (2026-06-06):** D1 = **fixed 5-tag seed + read-only picker** (no public create, mirrors sections). D2 = **prod psql idempotent data-seed** (no migration — the `tags`/`post_tags` tables already exist as bootstrap DDL; `ON CONFLICT DO NOTHING`). D3 = **`Tag` ORM model** in shared_db (not raw-SQL) → `post_tags` table + `Post.tags` relationship + pin bump. D4 = tags allowed on all posts. D5 = **admin / DB-only** → **no MDX frontmatter, no `content.config.ts`, no public `/reviews` filter this step** (the RFC's original "tags render on `/reviews`" is dropped per owner; revisit if/when public tag browse is wanted).

**DONE (prod-verified):**
- **shared_db** PR #22 merged + tag **`v0.13.0`** — `Tag` ORM + `post_tags` assoc table + `Post.tags`; purely **additive** (tables pre-exist) → no breaking window. `_generated_schema.sql` regen; parity tests green.
- **prod data-seed** — 5 tags `INSERT 0 5` (ids 1–5: `album review`/`track review`/`reissue`/`best album`/`year-end list`).
- **backend** PR #57 merged (`2722c1c`), deployed — pin `@v0.13.0`; `TagRepository`(ORM)+`TagService`; read-only **`GET /api/tags`**; `POST/PUT /api/posts` accept `tags` (seeded names, **reject-unknown → 400** whole-set, empty=clear); `GET` detail+list return `tags`. `openapi.json` regen (additive). pyright 0 err; tag/section/post tests 39 pass (full-suite 11 fails = pre-existing config-singleton pollution).
- **contract** workspace #273 merged (`docs/contracts/openapi.json` += `/api/tags`+`TagItem`+`TagListResponse`+`tags`). **front `api.gen.ts` re-synced** (front #100 `d56443a`, deployed — disarms the types-in-sync landmine; generated-only, no UI). This subsumes Step 5's tag-field tail.
- **prod smoke green (smoke-JWT e2e):** create-with-tags→200 + GET reflects; PUT replace→single; PUT []→cleared; unknown tag→400; `GET /api/tags`→5; hard-delete cleanup 204.

**PENDING (Lane B — writer tag picker UI):** build-time seed `src/lib/tags.ts` + writer multi-select picker reading it + wire `tags` into the post create/update payload. Was held behind the in-flight `/write` redesign (Direction C #99); **#99 landed 2026-06-06 → now unblocked.** No contract/`api.gen.ts` change needed (already synced); UI-only. Until shipped, admin can attach tags only via direct API.
**Verification (picker):** writer shows the 5 seeded tags, multi-select, can't create new; selections persist via GET; `pnpm lint` + `astro check` + browser click-through.
**Rollback:** trivial — revert the PR(s).

### Step 5 — contract regen — **DONE ✅ 2026-06-06**
**Status:** Section side — workspace #270 merged (`712b364`). Tag side — workspace #273 merged (`65b8427`, `docs/contracts/openapi.json` += the Step 4 tag surface) + front `api.gen.ts` re-synced (#100, deployed). Both contract waves are landed; nothing left here. (Unlike the section change, the tag change DID force an `api.gen.ts` resync — the `tags` field entered the generated client — so the front types-in-sync gate required a regen; done.)

Export `openapi.json` for the new `/api/sections` (+ tag fields), workspace merge regenerates `docs/contracts/openapi.json`, frontend types derived. (Per ARCH-12 contract-first; merge workspace first — [[reference-workspace-contract-merge-order]].)
**Verification:** openapi-verify CI clean; `api.gen.ts` in sync.
**Rollback:** trivial — revert the PR (+ regen `api.gen.ts`).

### Step 6 — data + MDX reset (DESTRUCTIVE — human approval) — **DONE ✅ 2026-06-06**
**DONE:** owner-approved (rule #3). All 13 test posts hard-deleted via the API path (`DELETE /api/posts/{id}?hard=true`, AccessToken Bearer to raw API GW `ld8pjw3mx4`) → 204 each (11 published + 2 draft); the 11 published deletes pushed 11 MDX-removal commits to the front content repo (`origin/main:content/blog` → **0 dirs**), drafts were DB-row-only as predicted. Junk `sections` `default`(1)/`smoke-bug10`(2) then deleted via psql (`BEGIN; DELETE FROM sections WHERE slug IN ('default','smoke-bug10'); COMMIT` → `DELETE 2`) after confirming `posts=0` (FK-safe). Final state: **`posts`=0; `sections` = 4 seed only (Reviews 3 / Best New Music 5 / Features 6 / Tracks 7)**. **Front-build race caveat:** the 11 concurrent push-deploys raced — a late-finishing build checked out an early content state and uploaded a stale `/blog` still listing some junk posts; a manual `workflow_dispatch` re-deploy from clean `origin/main` (56b17d5) fixed it. **Verified clean:** prod `/blog` 200 with zero junk titles + zero `/blog/<slug>` post links; `GET /api/sections`→200 (4 seed); `GET /api/categories`→404. **Prod smoke 28/0 PASS** (incl. section-aware checks: category PUT → `Features`, `/api/categories` gone, `/api/sections` seed; smoke's transient post self-cleaned, posts back to 0).

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
| 2026-06-06 | **Step 1 + Step 2 back-to-back rollout executed (option A, owner full-go).** V13 applied to prod Neon (`INSERT 0 3`, breaking window opened) → backend PR #56 squash-merged (`d3cce15`) → deploy success → window closed. Prod smoke green. Total admin-writer outage = the deploy duration only; public site (build-time-static) unaffected as predicted. | Step 1/2 |
| 2026-06-06 | **Step 3 (frontend) landed in parallel (Lane B), no coordination needed.** Build-time seed (not the runtime endpoint) kept it contract-neutral and mergeable independent of Lane A. Wire format compatibility confirmed: picker emits section LABEL as `category`; backend looks up by section *name* (= label), not slug. | Step 2/3 |
| 2026-06-06 | **Step 6 (destructive data/MDX reset) executed — owner-approved (rule #3).** 13 posts hard-deleted via API (204 each); 11 MDX dirs removed from front content repo (`origin/main:content/blog` → 0); junk sections `default`/`smoke-bug10` deleted via psql after `posts=0` confirmed. Final: `posts`=0, `sections`=4 seed. **Gotcha logged:** the 11 concurrent push-triggered front deploys raced → a stale build won and re-listed junk; fixed with a manual `workflow_dispatch` re-deploy from clean `origin/main`. Prod smoke 28/0. **STAB-5 still has Step 4 (review tags) remaining → RFC stays open (not archived).** | Step 6 |
| 2026-06-06 | **Step 4 pre-impl decisions D1–D5 (owner).** D1 fixed 5-tag seed + read-only. D2 prod psql idempotent data-seed (no migration — tables pre-exist). D3 `Tag` **ORM** model (not raw-SQL) → `post_tags`+`Post.tags`+pin bump. D4 tags on all posts. D5 **admin/DB-only** → dropped the RFC's public `/reviews` tag filter + all MDX/`content.config.ts` work (revisit if public tag-browse wanted). | Step 4 |
| 2026-06-06 | **Step 4 backend+contract DONE, prod-verified (owner full-batch go).** shared_db #22→`v0.13.0` (additive Tag ORM, no breaking window) → prod seed 5 tags (`INSERT 0 5`) → backend #57 (`2722c1c`) deployed → workspace contract #273 → front `api.gen.ts` resync #100 (deployed, types-gate green). Tag change **did** force an `api.gen.ts` regen (the section change hadn't). smoke-JWT e2e all-pass (attach/replace/clear/reject-unknown-400/`GET /api/tags`=5). **Writer picker (Lane B, UI-only) deferred behind the in-flight `/write` redesign #99; #99 landed same day → picker now unblocked, only remaining piece before STAB-5 archive (Step 6 already done).** | Step 4/5 |
