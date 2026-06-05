# STAB-1: System Stabilization & Hardening (pre-expansion)

- **Status**: draft
- **Owner**: TBD (주인장)
- **Created**: 2026-06-05
- **Plan row**: `plan.md` → STAB-1 (Active)

---

## Goal

Before any product expansion (genre taxonomy, multi-user, distribution charts, AI suggestions, new-release feed) resumes, drive the system to a stable, well-understood baseline. This RFC is an **investigation, prioritization, and sequencing** document: it captures every issue surfaced by the 2026-06-05 architecture review **re-verified against current code**, classifies each, states the risk and the evidence required before any fix, and fixes the public content taxonomy (category → board/section + review tags) decision. After this RFC is `accepted` it spawns scoped implementation RFCs/BUG rows; it does **not** itself change code, Terraform, data, files, or API behavior.

This is the **top active work**. All expansion stays queued behind it (see §Sequencing and `plan.md`).

## Non-goals

This RFC explicitly will **not**:

- Modify application code, Terraform, or any infrastructure.
- Delete or reset any data (prod categories, posts, MDX, DB rows).
- Remove or rewrite any tracked file.
- Change any API method, route, or behavior.
- Propose **caching** of any kind as a remedy — caching is entirely out of scope (the existing per-process + edge caches are described only where they bound a finding's worst case, never recommended as a fix).
- Write a direct implementation plan. Each finding ends at "evidence required before implementation"; the actual fix is a later, scoped RFC/PR.
- Self-promote its own Status (draft → accepted is human-only per hard rule #5).

## Method & evidence basis

The 2026-06-05 review's findings lived only in chat memory. For this RFC every claim was **re-checked against the current repo** (per the "don't blindly accept the prior review" mandate): a 20-agent verification pass (10 areas × investigate + adversarial re-verify) read the actual files, corrected stale line numbers, and reclassified. The main author then independently re-confirmed the load-bearing anchors firsthand: `myblog_backend/app/main.py:34-54` (edge_guard), `infra/apigateway.tf:58-94` (route authorizers), `myblog_shared_db/.../models.py:91-101,256-267` (Category/Post), `myblog_backend/app/api/routes/categories.py` (no auth dep), `myblog_front/src/components/writer/types.ts:64` (writer SECTIONS).

The review's hypotheses held up well, with these notable **corrections** baked into the findings below:

- Stale line numbers throughout (corrected in citations).
- The most material *newly-confirmed* facts: backend Lambda has **no `COGNITO_USER_POOL_ID`** so app-level `require_cognito_token` is a no-op in prod (AUTH-5); **`GET /api/posts?include_archived=true` exposes drafts/archived posts unauthenticated** (AUTH-9); music Lambda **defaults `ENV=local` in prod** so its `require_cognito_token` is bypassed too (P6-2); `docs/contracts/schema.sql` is **missing every table from migrations V6–V12** (P2-8).
- Downgrades where the review over-claimed: `POST /api/metrics/batch` is **read-only**, not an unauthed write (AUTH-4/P8-2); P4 website-endpoint posture is an **intentional tradeoff**, not an independent vuln (P4-1/P4-4); EventBridge cron handler failure **is** alarmed via the Lambda Errors alarm, so P8-5 is **unclear**, not a real gap (P8-5, P1-6).

Classification legend: **`real issue`** (defect/gap to fix or consciously accept) · **`intentional tradeoff`** (deliberate, low-risk for current stage) · **`unclear`** (needs a prod probe to settle) · **`false positive`** (review concern not borne out / already handled). Counts: 47 real, 17 tradeoff, 10 unclear, 8 false-positive (before consolidation).

---

## Final decision — category/board/section + review tags model

**Grounded in current state** (verified): `posts.category_id` is a **nullable FK → `categories` table** (`models.py:258-260`, `schema.sql:59`) — already *at most one* category per post. But the live data is junk (8 `Reviews` + 3 `default`, auto-created via get-or-create from test posts), the **writer never reads the DB table** — it uses a hardcoded `SECTIONS = ['Reviews','Best New Music','Features','Tracks']` dropdown (`types.ts:64`); a separate stale `categories.json` (`music`, `web-dev`, …) feeds content-schema validation as a decorative free-string enum; and a fourth build-time `pages/api/categories.json.ts` derives categories from frontmatter. Public review classification (`/reviews`) is **front-only at build time** (frontmatter `genres`, `bestNew`, `year`), with `albums.best_new` as the canonical BNM source. The private **`review_buckets` kanban** (V6/V11) is a separate writing queue — *not* public taxonomy. `tags`/`post_tags` M:N tables exist in DDL but are **dead/empty**.

**Decision** (ratified by owner 2026-06-05):

1. **Reinterpret `category` as a public-taxonomy `section`.** Adopt **`section`** as the domain name (not `board`): the writer UI already says "section", and "board" is already taken by the private `review_buckets` ("review bucket board") — reusing it would conflate the two subsystems the investigation warns against. *(Owner confirmed `section`.)*
2. **A post belongs to exactly one section.** Keep the single-FK shape (`posts.section_id`, formerly `category_id`), NOT a join table — it already encodes "at most one". *(Owner confirmed: single section per post; no multi-section requirement.)*
3. **The writer UI selects only from existing sections; it cannot create sections.** Replace the hardcoded `SECTIONS` array + the dead `createCategory`/`fetchCategories`/`addCategory` code with a read-only picker fed by a single authoritative list.
4. **Initial sections are inserted by migration** (a seed migration in `myblog_shared_db/migrations/`), establishing a curated set instead of organically auto-created junk rows.
5. **Future section creation stays internal** — via migration / seed script / internal admin script / repository config / later admin-only tooling. **No public section/category creation API.** The currently-exposed `POST /api/categories` is removed or hard-gated (AUTH-1).
6. **Review-specific classification uses review tags, not sections.** Examples: *track review, album review, best album, best albums, year-end list*. Model these as tags on review posts, **reusing the existing empty `tags`/`post_tags` M:N** *(owner decision — reuse, not a new `review_tags` table)*. This keeps the one-section-per-post rule clean while allowing multi-tag review classification.
7. **Existing temporary review/category data may be reset.** The junk `categories` rows and test posts can be deleted, and the corresponding **published/static MDX output cleaned** — note that taxonomy lives baked into frontmatter (`publish_service.py:22-69`), so any restructure requires **re-emitting/removing affected MDX**, not just a DB change.

The concrete schema, migration, writer-UI, and cleanup steps are deferred to a follow-up **implementation** RFC (e.g. `FEAT-section-taxonomy`); this RFC only fixes the model decision and the evidence to gather first (see §Evidence checklist).

---

## Findings by priority

### P0 — Auth boundary

| ID | Title | Class |
|----|-------|-------|
| AUTH-1 | `POST /api/categories` is an unauthenticated write | real issue |
| AUTH-2 | `x-origin-verify` (edge_guard) is origin-only, not user auth | real issue |
| AUTH-3 | `Authorization: Bearer <anything>` bypasses edge_guard on authorizer-less routes | real issue |
| AUTH-4 | Route→authorizer map; only categories is an unauthed write | real issue |
| AUTH-5 | Backend app-level `require_cognito_token` is a no-op in prod (no `COGNITO_USER_POOL_ID`) | real issue |
| AUTH-6 | ENV bypass cannot fire in prod; empty-pool-id fail-open is the real risk | intentional tradeoff |
| AUTH-7 | WAF is on CloudFront only, not the API Gateway invoke domain | real issue |
| AUTH-8 | Confirmed: only `categories` is an unintended public mutation | real issue |
| AUTH-9 | `GET /api/posts?include_archived=true` exposes drafts/archived unauthenticated | real issue |

**[AUTH-1] `POST /api/categories` unauthenticated write** · `real issue`
- **Now:** `infra/apigateway.tf:76-80` (`categories_post`) has no `authorization_type`/`authorizer_id` (unlike `posts_post` :88-94 which carries JWT + cognito authorizer); `categories.py` `add_category` has no `require_cognito_token` dep; it does a real `INSERT … commit` (`category_service.py`). Only edge_guard protects it. *(Confirmed firsthand.)*
- **Why:** Categories were a small admin enum; the writer calls it with a plain `fetch` (no Authorization header), so a JWT authorizer would have broken the legacy UI path. Predates the per-route-authorizer discipline used by buckets/library.
- **Risk:** Combined with AUTH-3/AUTH-7, an internet-reachable unauthenticated DB write (junk rows, slug-collision churn, table growth). Bounded to `categories` today but proves the boundary isn't systematically enforced.
- **Evidence required:** `curl -X POST <invoke-domain>/api/categories -H 'Authorization: Bearer x' -d '{"name":"probe-DELETE-ME"}'` → row created? (then hard-delete). Decide fix: JWT authorizer on the route vs. removing the endpoint per the §model decision.

**[AUTH-2] edge_guard is origin-only, not user auth** · `real issue`
- **Now:** `main.py:45-52` raises 403 only if a request lacks a `Bearer ` prefix **and** `x-origin-verify != EDGE_SECRET`. It compares one shared static secret injected by CloudFront (`cloudfront.tf:65-68`); it never inspects claims/subject.
- **Why:** Intended purely as an origin gate (force traffic through CloudFront/WAF). User identity was meant to be enforced separately by the gateway JWT authorizer.
- **Risk:** Conflating origin-verification with authentication invites the categories mistake: an authorizer-less, app-guard-less route becomes public-with-a-shared-secret. If `EDGE_SECRET` leaks (it sits plaintext in tfstate, P3-1), every edge_guard-only route opens.
- **Evidence required:** None to classify (code is explicit). Before remediation: inventory which routes rely on edge_guard as their sole gate (AUTH-4) and decide policy (origin-only + explicit per-route user-auth).

**[AUTH-3] Bearer-prefix bypass on authorizer-less routes** · `real issue`
- **Now:** `main.py:50-52` — `has_bearer = headers.get("authorization","").startswith("Bearer ")`; if true, the x-origin-verify check is skipped and the token is **never validated**. The comment (`main.py:46-49`) assumes the gateway already validated the JWT — false for routes with no authorizer (`categories_post`, `metrics_batch_post`, the `GET /api/{proxy+}` catch-all, `ANY /api/music/*`). No custom-domain-only / `disable_execute_api_endpoint`, so the invoke domain is internet-reachable. *(Confirmed firsthand.)*
- **Why:** Dual-ingress (CloudFront adds x-origin-verify; API GW adds validated Bearer) needed edge_guard to accept both; trusting any Bearer was a shortcut assuming every Bearer request passed the authorizer.
- **Risk:** edge_guard's secret-gate is defeatable from anywhere with a one-line `Bearer x` header on every authorizer-less route → unauth write (AUTH-1) and unauth reads (AUTH-9).
- **Evidence required:** The AUTH-1 curl probe demonstrates it. Fix options: validate the JWT inside edge_guard for authorizer-less paths, or attach authorizers / app-level deps to those routes.

**[AUTH-4] Route→authorizer map** · `real issue`
- **Now:** Authorizer-less: `GET /api/{proxy+}` (read catch-all), `POST /api/categories` (write), `POST /api/metrics/batch` (POST but **read-only** — `metrics.py:11-19` only `get_many`, no commit), `ANY /api/music` + `ANY /api/music/{proxy+}` (all music handlers are GET). JWT-gated: all `posts` mutations, `publish`, buckets + library mutations. *(Confirmed firsthand.)*
- **Why:** Reads are public-by-design; mutations got authorizers one at a time as features landed; categories/metrics predate that discipline.
- **Risk:** The one dangerous gap is the `categories` write (AUTH-1). The catch-all means any *new* GET route is auto-exposed with no opt-in.
- **Evidence required:** At fix time re-grep `apigateway.tf` for routes lacking `authorization_type` and cross-check each handler for `db.commit`; confirm `metrics/batch` stays read-only.

**[AUTH-5] App-level `require_cognito_token` is inert in prod** · `real issue`
- **Now:** `auth.py:33` returns `{}` (bypass) when `not settings.COGNITO_USER_POOL_ID`; the **backend** Lambda env (`lambda.tf:26-39`) never sets it (only the *music* Lambda does, `:62`); `config.py` defaults it `""` and never injects it from Secrets Manager. So in prod `require_cognito_token` is a pass-through that **fails open**; backend user-auth rests entirely on the gateway authorizer. Tests set the var so they pass while prod runs unguarded.
- **Why:** Defense-in-depth was intended but the var was wired only where first needed (music); the gateway authorizer made the app check look redundant in testing.
- **Risk:** Single point of failure — any mutating route added without a gateway authorizer (the categories mistake) has no app-level backstop, and the gap is masked by passing tests. Directly enables AUTH-9.
- **Evidence required:** `aws lambda get-function-configuration --function-name ratemymusic-api --query Environment.Variables` → confirm `COGNITO_USER_POOL_ID` absent. Decide: set it + make `auth.py` fail **closed** on missing pool id in prod, and verify JWKS fetch works from the backend Lambda first.

**[AUTH-6] ENV bypass closed in prod; empty-pool-id is the real hole** · `intentional tradeoff`
- **Now:** edge_guard fully bypasses when `APP_ENV in (dev,local)` (`main.py:36-37`) and `auth.py:33` bypasses for the same; prod hard-codes `ENV/APP_ENV=prod` (`lambda.tf:28-29`), so the ENV vector cannot fire in prod. The dangerous branch is the *other* half of `auth.py:33` (`not COGNITO_USER_POOL_ID`), which does fire (AUTH-5).
- **Why:** ENV gating is standard local-dev convenience; hard-coding `ENV=prod` in TF correctly prevents accidental dev-mode. The empty-pool-id short-circuit was a fail-open safety valve — questionable for an auth function.
- **Risk:** ENV vector is closed (tradeoff is sound); the fail-open on missing config is the live defect, captured under AUTH-5.
- **Evidence required:** Same `get-function-configuration` call (confirm `ENV=prod`, pool-id absent). Decide fail-closed behavior.

**[AUTH-7] WAF only on CloudFront, not the invoke domain** · `real issue`
- **Now:** Only WAF reference is `cloudfront.tf:41` (a us-east-1 CloudFront-scope ACL `CreatedByCloudFront-…`). No `aws_wafv2_web_acl_association` to the API Gateway stage; no custom-domain-only restriction. The `execute-api` domain sits in front of Lambda with no WAF.
- **Why:** WAF was console-provisioned for CloudFront; edge_guard was meant to force the viewer→CloudFront→API path.
- **Risk:** With edge_guard bypassable (AUTH-3), a direct invoke-domain caller gets **no** WAF (no rate-limit/managed rules) **and** no origin check → unthrottled unauth writes/reads at the origin.
- **Evidence required:** Confirm no REGIONAL web-ACL association on the stage; confirm the invoke domain responds off-CloudFront (AUTH-1 curl already hits it). Decide: associate a REGIONAL WAF or block the raw invoke domain.
- **Correction (2026-06-05, live — see STAB-2):** `wafv2 list-web-acls --scope REGIONAL` is empty **and** the API is **HTTP (v2)** — WAFv2 cannot associate to an HTTP API at all (only CloudFront / REST v1 / ALB / etc.). So "associate a REGIONAL WAF" is **impossible**; remediation re-scopes to a `$default` stage throttle (unblocked) or `disable_execute_api_endpoint`+CloudFront-only — the latter currently **site-down** because CloudFront's API origin is the raw invoke domain (`cloudfront.tf:5,63`), so it is blocked on first creating an API GW custom domain. See `STAB-2-p0-auth-boundary.md` Step 5.

**[AUTH-8] Only categories is an unintended public mutation** · `real issue`
- **Now:** Sweeping authorizer-less routes for writes: only `POST /api/categories` mutates (INSERT+commit); `metrics/batch` reads; music routes are all GET. *(Confirmed.)*
- **Why:** See AUTH-1.
- **Risk:** Bounded to categories today, but the next mutating route on the catch-all/edge_guard pattern would inherit the same hole.
- **Evidence required:** AUTH-1 probe + a one-time grep of all handlers reachable via authorizer-less routes for `INSERT/UPDATE/DELETE/commit`.

**[AUTH-9] Drafts/archived posts readable unauthenticated** · `real issue` *(missed by the prior review)*
- **Now:** `posts.py:28-34` (`list_posts`) and `:96-101` (`get_post`) declare `Depends(require_cognito_token)` but have **no gateway authorizer** (served by the `GET /api/{proxy+}` catch-all) — and `require_cognito_token` is inert in prod (AUTH-5). `list_posts` accepts `status` + `include_archived` (`post_service.py:156`), so `GET /api/posts?include_archived=true` returns draft + archived (unpublished) posts. Reachable through CloudFront (GET passes edge_guard once x-origin-verify matches) or directly with `Bearer x` (AUTH-3).
- **Why:** Treated as part of the "intended-public reads" catch-all; nobody noticed two of those reads serve private editorial state.
- **Risk:** **Confidentiality breach** — unpublished/draft and soft-archived post content (titles, slugs, bodies, ratings) is readable by anyone reaching CloudFront or the invoke domain. This turns the latent AUTH-5 fail-open into a live, exploited-by-default leak.
- **Evidence required:** `curl '<invoke-domain>/api/posts?include_archived=true' -H 'Authorization: Bearer x'` → drafts returned? Fix = set `COGNITO_USER_POOL_ID` + fail-closed `auth.py`, or split these GETs off the catch-all behind an authorizer.

### P0 — Category / board / section model (current-state map)

These are the facts the §model decision rests on. Most are descriptive (`unclear` pending a prod row count); the genuine defects are flagged `real issue`.

**[MODEL-1] `categories` table is lazily auto-created, never seeded** · `unclear`
- **Now:** `Category(id Integer PK, name/slug Text unique, created_at)` (`models.py:91-101`, `schema.sql:33-38`). Zero seed/INSERT; rows materialize via get-or-create on post create/update (`post_service.py:71-75,188-194`). *(Confirmed firsthand.)*
- **Why:** Single-author blog; lazy create avoided a seed step + admin CRUD.
- **Risk:** The live table is "whatever authors typed", not a curated taxonomy — a redesign assuming a fixed seeded set mismatches reality.
- **Evidence required:** `SELECT id,name,slug,created_at FROM categories ORDER BY id` on prod (Neon via `reference-database-url-psql`).

**[MODEL-2] Post→category is many-to-one (≤1 per post)** · `unclear`
- **Now:** `posts.category_id` BigInteger FK `ON DELETE SET NULL` nullable (`models.py:258-260`, `schema.sql:59`); scalar `Post.category`. No join table. *(Confirmed firsthand.)*
- **Why:** A review belongs to one section; single scalar is simplest.
- **Risk:** If the product ever needs multi-section membership, the single FK can't express it (would need a join table or the unused `post_tags`).
- **Evidence required:** Confirm the requirement: does a post need >1 section? (drives OQ2; default = no, keep single FK).

**[MODEL-3] Writer ignores the DB table; uses hardcoded SECTIONS; create-category code is dead** · `real issue`
- **Now:** Writer dropdown = `SECTIONS = ['Reviews','Best New Music','Features','Tracks']` (`types.ts:64`, sent as `category` at `WriterApp.tsx:244`); it never calls `GET /api/categories`. `createCategory`/`fetchCategories` (`scripts/write/api.ts`) and `addCategory` (`lib/api.ts`) have **zero call sites**. *(Confirmed firsthand.)*
- **Why:** Writer rebuilt (FEAT-writer-lowfreq) around fixed sections; the old dynamic-category UI + helpers were left in the tree.
- **Risk:** Competing vocabularies (MODEL-4); dead code is misleading; the unauthed `POST /api/categories` (AUTH-1) is a live endpoint with no UI need.
- **Evidence required:** grep (done: no call sites). Decide single source of truth, then delete the others (directly supports the §model decision).

**[MODEL-4] Three (four) disjoint "category" vocabularies** · `real issue`
- **Now:** (a) DB live = `Reviews`/`default`; (b) `categories.json` = `["music","web-dev","devops","ai-ml","opinion","productivity"]` used as a *decorative* zod enum with a `z.string()` escape (`content.config.ts:78-80`); (c) writer `SECTIONS`; (d) build-time `pages/api/categories.json.ts` derived from frontmatter. None overlap except literal `Reviews`. `/blog/category/[category].astro` builds pages from whatever frontmatter strings exist.
- **Why:** `categories.json` predates the music pivot; content.config relaxed to free-string; writer hardcoded its own; DB stores whatever arrives.
- **Risk:** Continual drift; live category pages are `Reviews`/`default` while `categories.json` advertises six unused slugs.
- **Evidence required:** Decide the single source of truth (§model decision: a migration-seeded `sections` set), then prune the others.

**[MODEL-5] Public review classification is front-only; `review_buckets` is a separate private queue** · `unclear`
- **Now:** `/reviews` filters client-side from MDX frontmatter (`genres`, `bestNew`, `year`) — no API/category (`ReviewsIndex.tsx:147-170`). Canonical BNM = `albums.best_new` (V4), set via writer toggle, mirrored to frontmatter (`publish_service.py:52`). `review_buckets`/`review_bucket_items` (V6/V11) are a **private kanban**, decoupled from publishing. No "year-end/best-album" list table exists.
- **Why:** Static-site model → cheapest classification is frontmatter + client filter; buckets are a writing tool.
- **Risk:** Two orthogonal axes — public taxonomy (frontmatter) vs private workflow (buckets). Conflating them couples a private kanban to the public site. `bestNew` has dual storage (album column + frontmatter) that can drift.
- **Evidence required:** Confirm redesign scope = PUBLIC taxonomy (sections/genres/best-new on /reviews), distinct from the private board. The §model decision targets the public axis; review **tags** address review classification without touching buckets.

**[MODEL-6] `tags`/`post_tags` exist in DDL but are dead/empty** · `unclear`
- **Now:** `tags` (`schema.sql:40-44`) + `post_tags` M:N (`:77-81`); no ORM model, zero read/write code, `FRONTMATTER_TAGS` is an empty Map. Per `reference-schema-sql-bootstrap-tables` these are intentional bootstrap tables.
- **Why:** Planned-but-unbuilt tagging, bootstrapped ahead of the feature.
- **Risk:** Low. The §model decision can **reuse** this M:N shape for review tags rather than inventing a new one (OQ3).
- **Evidence required:** `SELECT count(*) FROM post_tags; SELECT count(*) FROM tags` on prod (expect empty).

**[MODEL-7] Temporary/placeholder category + review data in live content** · `real issue`
- **Now:** 11 MDX dirs; frontmatter tally 8 `Reviews` + 3 `default`; titles/slugs are clearly test data (`432432432432`, `untitled`, `212121`, …). `bestNew` present in only 4/11. So DB `categories` holds placeholder rows.
- **Why:** Dev/QA churn (smoke tests + manual writer testing republish throwaway posts; `default` from `publish_service.py:38`).
- **Risk:** A redesign launched on top leaks junk categories + test posts into the new sections and `/blog/category` pages.
- **Evidence required:** Enumerate prod posts + categories + the content-repo MDX list; classify real vs test; plan deletion (publish DELETE path + DB cleanup) as part of the implementation RFC.

**[MODEL-8] Taxonomy is baked into static frontmatter at publish time** · `unclear`
- **Now:** `make_mdx_frontmatter` (`publish_service.py:22-69`) always emits `category` (default `default`), `bestNew`, `ratingScale`, album/artist ids, etc., committed to the content repo → S3/CloudFront rebuild.
- **Why:** Static-first — display fields are denormalized into frontmatter (no runtime DB read on the public path).
- **Risk:** A section rename/restructure must **re-emit every affected MDX**; a DB-only migration won't change what the site shows. (Denormalization-by-design, not a leak.)
- **Evidence required:** Confirm the republish mechanism (PUT path overwrites frontmatter); count real posts needing re-emit; verify no other public-path consumer reads category from the DB.

**[MODEL-9] `schema.sql` `posts.rating` type is stale (NUMERIC(3,1) vs prod 3,2)** · `real issue`
- **Now:** `schema.sql:65` = `NUMERIC(3,1)`; ORM (`models.py:264`), `_generated_schema.sql:96`, migration `V5`, and live data (3.55, 2.61) are all `NUMERIC(3,2)`. *(Confirmed `models.py:264` firsthand.)*
- **Why:** Drift — V5 + ORM updated, canonical `schema.sql` line missed.
- **Risk:** Low functional (prod correct); misleads the schema-parity test + any reviewer trusting `schema.sql`.
- **Evidence required:** `SELECT numeric_precision,numeric_scale FROM information_schema.columns WHERE table_name='posts' AND column_name='rating'` (expect 3,2). One-line `schema.sql` fix in the cleanup.

**[MODEL-10] `POST /api/categories` has no auth dep + ASCII-only slugify breaks Korean** · `real issue`
- **Now:** `add_category` has no `require_cognito_token` (AUTH-1, confirmed firsthand). The unauthed endpoint runs `CategoryService.add` → `python-slugify` (strips non-ASCII by default), so an all-Korean name collapses and collides on `UNIQUE(slug)`. *(Slugify citation corrected from the prior review's `category_repository.py` ASCII regex to `category_service.py`; the post get-or-create path uses the ASCII regex separately — see MODEL-11.)*
- **Why:** Categories route predates the standardized auth pattern; slugify was a quick ASCII helper not adapted for ko-KR content.
- **Risk:** Unauthed garbage rows; Korean section labels unusable (slug collision) — directly relevant if the new model uses Korean labels.
- **Evidence required:** Probe the endpoint with a Korean name; confirm slug behavior. The §model decision (no public create API + migration-seeded sections + unicode-aware slug) resolves both.

**[MODEL-11] Two divergent slugify + two get-or-create paths write the same table** · `real issue` *(missed)*
- **Now:** `POST /api/categories` → `CategoryService.add` (python-slugify); post create/update get-or-create → `CategoryRepository.create` (ASCII `re.sub` regex, `category_repository.py:8-9`). Different slugs for the same name → phantom duplicate/missing rows. `CategoryService.get_or_create` is never wired into post create/update.
- **Why:** Two code paths grew independently.
- **Risk:** Inconsistent slugs depending on which path created the row; a redesign standardizing on one slug rule must reconcile both.
- **Evidence required:** Diff the two slug outputs for the same names; confirm `CategoryService.get_or_create` has zero call sites; pick the canonical impl.

**[MODEL-12] `review_buckets` + other V6+ tables absent from canonical `schema.sql`** · `real issue` *(missed; see also P2-8)*
- **Now:** `schema.sql` ends at `op_logs` (273 lines) and omits `review_buckets`/`review_bucket_items` (V6), `library_items` (V7), `album_to_listen_items` (V8), spotify caches (V9), `spotify_play_events` (V10), `review_buckets.parent_id` (V11). All exist in `_generated_schema.sql` + migrations. Since `schema.sql` is the bootstrap (no migration runner), a fresh bootstrap from it lacks these tables.
- **Why:** `schema.sql` was maintained through V5 then stopped.
- **Risk:** A DB bootstrapped from the "source of truth" is missing ~7 live tables → buckets/library/listening endpoints 500; reviewers auditing against `schema.sql` draw wrong conclusions.
- **Evidence required:** Diff `schema.sql` vs `_generated_schema.sql`; backfill V6–V12 DDL (later cleanup PR).

**[MODEL-13] Backend `GET /api/categories` is functionally orphaned** · `unclear`
- **Now:** Backend `GET /api/categories` (`categories.py:11-16`) returns DB names; its only fetcher (`fetchCategories`) is dead (MODEL-3). The frontend instead builds its category list from frontmatter via `pages/api/categories.json.ts` (prerendered).
- **Why:** Frontend went static-first; the backend list endpoint was left behind.
- **Risk:** Low — a fourth category source reinforcing "no single source of truth".
- **Evidence required:** Confirm zero runtime consumers; decide keep-vs-delete alongside the dead create path.

### P1 — Worker / SQS / EventBridge reliability

**[P1-1] SQS visibility (30s) ≪ worker timeout (120s) → redelivery + duplicate concurrent processing** · `real issue` *(highest severity in P1)*
- **Now:** `blogSQS visibility_timeout=30` (`sqs.tf:14`, confirmed in tfstate `fifo=False`), worker Lambda `timeout=120` (`lambda.tf:83`), ESM `batch_size=10`, `maxReceiveCount=3`. No reserved/maximum concurrency configured. A batch can hold 10 msgs × 20 album ids = 200 albums; chunked Spotify calls (20/call, 20s httpx timeout) + per-50-artist enrich easily exceed 30s wall time → the message reappears and a 2nd concurrent Lambda picks it up; a slow-but-correct batch is redelivered 3× then DLQ'd.
- **Why:** 30s is the SQS default, never raised when the worker timeout went 10→120 for batch headroom. Idempotent upserts (P1-4) + `ReportBatchItemFailures` masked it.
- **Risk:** Doubled Spotify volume (429 risk on the shared token), wasted compute, and — worse — **legitimate slow syncs force-DLQ'd** exactly when Spotify is slow, raising false DLQ alarms and dropping albums. Idempotency prevents *corruption* but not the premature-DLQ harm.
- **Evidence required:** CloudWatch — `ApproximateAgeOfOldestMessage`, `NumberOfMessagesReceived` vs `…Deleted` divergence, worker Duration p99 vs 30000ms, `ConcurrentExecutions`, `album-sync-dlq` `NumberOfMessagesSent` history. Then raise `blogSQS` visibility to ≥ worker timeout (AWS guidance ≈ 6× ⇒ ~720s). **Scope the fix to `blogSQS` only** (the DLQ's own 30s visibility is irrelevant — no consumer, P1-9).

**[P1-2] `architecture.md` says FIFO `album-sync.fifo`; prod is standard `blogSQS` (+ dead FIFO dedup code)** · `real issue`
- **Now:** `architecture.md:215` claims FIFO; `sqs.tf:11` defines a standard `blogSQS` (no `.fifo`/`fifo_queue`), tfstate `fifo=False`. The canonical contract doc (`sqs-album-sync.md`) correctly says standard. The music producer has a FIFO dedup branch gated on `queue_name.endswith('.fifo')` (`sqs_client.py:55,88-93`) — **dead in prod**.
- **Why:** `architecture.md` predates the standard-queue decision; producer kept FIFO support as a forward hedge.
- **Risk:** Operators assuming FIFO exactly-once won't design for at-least-once duplicate delivery (compounds P1-1); dead dedup code implies suppression that doesn't exist.
- **Evidence required:** None for the mismatch (tfstate proves it). Decide: convert to FIFO (if ordering/dedup wanted) or delete the dead branch + fix the doc. (Idempotent-consumer posture, P1-4, suggests standard + idempotent is intended.)

**[P1-3] EventBridge async invokes have no `event_invoke_config` (no retry tuning / on-failure DLQ)** · `real issue` *(low severity — mostly self-healing)*
- **Now:** Two rules target the worker (alias `rate(15min)`, listening `rate(1h)`); no `aws_lambda_function_event_invoke_config` anywhere (grep empty, tfstate confirms). AWS defaults apply (2 retries, 6h max age, no on-failure destination); the handler re-raises → after 2 retries the event is silently discarded.
- **Why:** Team relied on the Lambda Errors alarm for handler crashes (P1-6); a custom on-failure DLQ was judged unnecessary for best-effort caches (missed tick re-runs).
- **Risk:** A persistently failing invoke is dropped with no captured payload for replay. Alias cron self-heals (re-selects `IS NULL` next tick); a dropped listening tick = ≤1h stale. Genuine gap = no dead-letter capture for forensics.
- **Evidence required:** CloudWatch async metrics + Errors alarm history to see if cron failures actually occur; decide whether a per-target on-failure SQS destination is worth it.

**[P1-4] Consumer writes are idempotent throughout** · `intentional tradeoff`
- **Now:** All upserts `ON CONFLICT … DO UPDATE/NOTHING` (`sync_service.py:124-205`, `listening_sync_service.py:74-145`); alias fill per-row commit with IntegrityError rollback (`sync_service.py:325-345`). This is what makes the standard-queue at-least-once posture (P1-1/P1-2) non-corrupting.
- **Why:** Deliberate at-least-once + idempotent-consumer pattern (the standard substitute for FIFO exactly-once); per-row alias commit is the BUG-17/18 hotfix lineage.
- **Risk:** Low. Duplicate delivery → redundant idempotent writes; residual concurrency could cause a transient serialization error → ReportBatchItemFailures retry. No integrity risk found.
- **Evidence required:** (Verification of an assumed-safe property.) CloudWatch logs for `deadlock`/IntegrityError during overlapping invocations, or a duplicate-batch load test.

**[P1-5] "One bad album id poisons the whole batch → DLQ"** · `false positive`
- **Now:** Explicitly handled — null array elements are skipped (`sync_service.py:66-73`, with a comment naming this exact failure mode); handler + spotify client filter empties.
- **Why:** Hard-won defensive coding.
- **Risk / evidence:** None — correct as-is.

**[P1-6] `FailedInvocations` alarm catches delivery failure only — but handler failure IS covered by the Errors alarm** · `intentional tradeoff`
- **Now:** `cron_failed_invocations` (`monitoring.tf:104-121`, namespace `AWS/Events`, `FailedInvocations`) fires only on **delivery** failure. A **separate** `lambda_errors` alarm (`AWS/Lambda Errors≥1`, `:29-47`) covers the worker and **does** fire when the async handler raises (the code re-raises precisely for this). The prior review's "handler failure unmonitored" claim is overstated.
- **Why:** Correct two-layer CloudWatch design (Errors = crashed; FailedInvocations = never ran).
- **Risk:** Two residual gaps: Errors is per-**function** so it can't attribute *which* trigger (SQS vs 2 crons) failed; a silent no-raise failure isn't caught (but the code re-raises catastrophic ones).
- **Evidence required:** Synthetic test that a cron exception trips the Errors alarm; **confirm the SNS `myblog-alerts` email subscription is actually click-confirmed** (`monitoring.tf:6-10`; `var.alert_email` has a default but email subs need manual confirmation) — load-bearing prerequisite before trusting *any* alarm. **(RESOLVED 2026-06-05: confirmed — real SubscriptionArn, not pending.)**

**[P1-7] Contract doc `sqs-album-sync.md:7` says "DLQ 미설정" but a DLQ exists** · `real issue` *(missed)*
- **Now:** The doc the review trusted over `architecture.md` says DLQ not configured; `sqs.tf:16-19` configures redrive → `album-sync-dlq` (`maxReceiveCount=3`), tfstate confirms.
- **Why:** Doc lagged the DLQ addition.
- **Risk:** Low; undercuts the doc's reliability — an operator would believe DLQ'd messages vanish when they actually land in `album-sync-dlq` (14-day retention) and trip the DLQ alarm.
- **Evidence required:** None (proven). One-line doc fix in the same cleanup as P1-2.

**[P1-8] DLQ is observe-only — no redrive/replay path** · `intentional tradeoff`
- **Now:** `album-sync-dlq` has 14-day retention + an alarm but no `redrive_allow_policy` and no consumer; recovery is a manual console redrive or expiry.
- **Why:** Visibility prioritized over automated recovery for this scale.
- **Risk:** Low, but combined with P1-1 a legitimately-DLQ'd album sync is lost if the operator misses the alarm (the email sub is confirmed as of 2026-06-05, P1-6).
- **Evidence required:** Whether any manual redrive has run; `album-sync-dlq` visible-message history. Fix P1-1 first; auto-redrive is secondary.

**[P1-9] Raising `album-sync-dlq` visibility too** · `false positive`
- **Now:** The DLQ also has `visibility_timeout=30` but no consumer, so it never matters. Flagged only to keep the P1-1 fix scoped to `blogSQS`.

### P2 — Shared DB / schema contract / doc drift

**[P2-1] `architecture.md` backend pin stale (says v0.5.0, actual v0.10.0)** · `real issue`
- **Now:** `requirements.txt:10` = `@v0.10.0`; `architecture.md:233` = `@v0.5.0`. Music (v0.3.0) + worker (v0.2.2) doc lines happen to match reality. Latest tag = v0.11.0 / pyproject 0.11.0 (migrations to V12); backend is 1 minor behind, not 6.
- **Why:** Doc-snapshot drift; never updated as the pin advanced.
- **Risk:** Mis-scopes migration planning (FEAT-genre-taxonomy already had to spell out the real @v0.10.0→@v0.12.0 jump).
- **Evidence required:** None (grep proves it). One-line doc fix.

**[P2-2] `architecture.md` SQS FIFO claim** · `real issue` — same as P1-2 (doc-drift facet). Evidence: `sqs.tf` canonical.

**[P2-3] `architecture.md` says worker imports `myblog_shared_db.tables`; worker imports nothing from shared_db** · `real issue`
- **Now:** `grep 'from myblog_shared_db|import myblog_shared_db' myblog_worker/` → **zero** (src + tests). All worker DB access is raw `text()` SQL (`sync_service.py:6` + INSERT/UPDATE blocks). The `@v0.2.2` pin is a **dead, installed-but-unimported** dependency. *(Correction to the prior note: shared_db DOES ship `src/.../tables.py`; the doc's path name is real — the doc is wrong only because the worker never imports it.)*
- **Why:** Worker uses raw SQL + `ON CONFLICT`; the pin was added defensively/by template, never used; the doc described an idealized design.
- **Risk:** A "pin bump sweep" wastes effort on the dead worker pin; the doc misleads schema-change planning (worker needs raw-SQL column names to match DDL, not a pin bump).
- **Evidence required:** None (grep definitive).

**[P2-4] `architecture.md` lists `POST /api/categories` as Cognito JWT; it's unauthed** · `real issue` — same defect as AUTH-1 (doc actively conceals it). **AUTH area owns remediation** to avoid duplicate work.

**[P2-5] Migration numbering V2..V12 gapless (no V1; baseline = `schema.sql`)** · `intentional tradeoff`
- **Now:** `migrations/` holds V2..V12 with no gaps, no V1 file. Hand-numbered `V{N}__` convention, no Alembic runner. FEAT-genre-taxonomy resolved genres = V13 with explicit gap-avoidance.
- **Why:** Deliberate convention; gapless because migrations are hand-applied sequentially.
- **Risk:** Only future risk = two parallel RFCs both claiming V13 (the genre RFC already pinned V13). No action now.
- **Evidence required:** `ls migrations | sort -V | tail -1` before numbering the next migration.

**[P2-6] Lagging music (v0.3.0) / worker (v0.2.2) pins are an intentional additive-compat window** · `intentional tradeoff`
- **Now:** Music imports only `Album/Artist/Track/album_artists_table/track_artists_table`; all (incl. `best_new`) exist at v0.3.0 (verified via `git show v0.3.0`). Music references no post-v0.3.0 column. Worker imports nothing (P2-3). `architecture.md:231` documents the per-service-pin intent.
- **Why:** ARCH-6 per-service-pin model — additive changes don't force coordinated redeploys.
- **Risk:** Low; surfaces only if a future migration **renames/drops** a column an old pin still SELECTs (the `reference-shared-db-cross-repo-rollout` failure mode). No such column today.
- **Evidence required:** Before any future rename/drop, grep each service against the lowest pin's model.

**[P2-7] Future RFCs do NOT rest on stale schema** · `false positive`
- **Now:** FEAT-genre-taxonomy cites correct V12/0.11.0 + backend @v0.10.0 and resolved V13; genre-distribution correctly gates on `spotify_play_events` (V10, exists); multi-user is schema-light pending acceptance. The "future RFCs are stale" hypothesis is not borne out.
- **Why:** The genre RFC did a current-state audit on 2026-06-05.
- **Risk:** Only transitive — a reader trusting `architecture.md` over the RFCs (fixed by P2-1..P2-3).
- **Evidence required:** None.

**[P2-8] Canonical `schema.sql` omits every table from V6–V12** · `real issue` *(missed; same root as MODEL-12)*
- **Now:** `schema.sql` (self-declared "source of truth", "update this file first") absorbed V2/V4/V5 column changes then stopped — omits `review_buckets`+`review_bucket_items` (V6), `library_items` (V7), `album_to_listen_items` (V8), spotify caches (V9), `spotify_play_events` (V10), `parent_id` (V11), and V12 pg_trgm. All present in `_generated_schema.sql` + migrations.
- **Why:** The file was maintained through V5 then abandoned as the source of truth in practice.
- **Risk:** A fresh bootstrap from `schema.sql` is missing ~7 live tables + an extension → buckets/library/listening writes 500; any "does contract match prod" audit against it is wrong. **Most consequential P2 drift after the auth issue.**
- **Evidence required:** Diff `schema.sql` vs `_generated_schema.sql`; backfill V6–V12 DDL in the cleanup (out of scope here).

> **P2 root-cause:** `docs/architecture.md` is the common source of most P2 doc-drift (P2-1/2/3/4) and `schema.sql` is incomplete (P2-8). The cheapest remediation is to rewrite those two doc sections (or add an "unreliable — verify against code" banner) — but as a follow-up, not in this RFC.

### P3 — Repository hygiene / sensitive local state

> All secret inspection was done by reporting key **names** + "present" only — **no secret value was printed**.

**[P3-1] Cognito `admin_client.client_secret` plaintext in local-only `terraform.tfstate` (no remote backend)** · `real issue` *(only P3 item with real security/recovery weight)*
- **Now:** `infra/terraform.tfstate` (+ `.backup`) holds the 52-char `admin_client.client_secret` in plaintext (value not printed). `main.tf:1-9` has **no backend block** → local-only state, no locking. tfstate IS correctly gitignored (not committed). `secrets.tf` uses `data` sources by name with zero inline values.
- **Why:** Single-owner hobby project; a remote S3+DynamoDB backend adds setup/cost and was skipped. `client_secret` in state is unavoidable for `aws_cognito_user_pool_client`; the gap is *where state lives*.
- **Risk:** Laptop loss = total loss of canonical AWS state (painful import-from-scratch); no locking (concurrent apply corrupts state); plaintext secret in an unencrypted file (Time Machine is the realistic ambient backup vector — the workspace is **not** under Dropbox/iCloud).
- **Evidence required:** Confirm the workspace isn't in a cloud-sync path; decide on a remote backend (S3 + DynamoDB lock) via `terraform init -migrate-state`; rotate the `admin_client` secret (console-only) if laptop exposure is suspected; reconcile `infra/README.md`'s "canonical state" claim.

**[P3-2] Stale 26MB `bundle.zip` committed in `myblog_worker`** · `real issue`
- **Now:** `myblog_worker/bundle.zip` is git-tracked (26,954,312 bytes), from the init commit, never re-committed. It's pure build output — `deploy.yml:57-76` + `build.sh` rebuild it and CI deploys the freshly built zip, never the committed one. The `.gitignore` rule matches but is moot (file tracked before the rule). `worker/.git` ≈ 27MB, dominated by this blob.
- **Why:** Committed once during bring-up (pre-gitignore) so a deploy could run without a build step; forgotten when CI took over.
- **Risk:** Repo bloat (lives in history); misleads operators into thinking it's the deployed artifact; build-reproducibility noise.
- **Evidence required:** Confirm `deploy.yml` is the only deploy path; then `git rm --cached bundle.zip` (history-rewrite only if clone size matters), after repairing the `.gitignore` (P3-3).

**[P3-3] `myblog_worker/.gitignore` is a committed shell here-doc transcript** · `real issue`
- **Now:** Lines 1-3 are `cd ~/Dow/worker_lambda` / `cat > .gitignore << 'EOF'`, with the intended patterns inside the here-doc, `EOF` on line 40, and a few patterns outside it. Git reads each non-comment line as a pattern, so most intended ignores work, but `EOF` becomes a live pattern and the author's home-dir path is leaked.
- **Why:** The whole "create a gitignore" snippet was pasted into the file instead of run.
- **Risk:** Fragile/confusing; a future file named `EOF` would be silently ignored; leaks a local path.
- **Evidence required:** None (read the file). Rewrite to just the intended patterns; pair with P3-2.

**[P3-4] `allure-results/` (18 files) tracked in the WORKSPACE repo** · `real issue`
- **Now:** 18 tracked Allure result/container/attachment files at workspace root; the root `.gitignore` has no allure entry. *(Correction: the WORKER repo correctly ignores allure-results; the tracked copy is at the workspace root.)* Spot-checked attachments → no secrets.
- **Why:** An `allure generate`/test run from the workspace root got git-added with no matching ignore.
- **Risk:** Non-deterministic churn (new UUID files each run); build artifacts polluting review.
- **Evidence required:** Add `allure-results/`+`allure-report/` to the root `.gitignore` and `git rm --cached` the 18 files.

**[P3-5] `.DS_Store` (4) + `.idea/` (2) tracked in `myblog_music`** · `real issue`
- **Now:** Tracked `.DS_Store` ×3 + `.idea/vcs.xml`,`.idea/workspace.xml`; music `.gitignore` omits OS/IDE patterns that other repos include. No secret value today (scanned).
- **Why:** Music's `.gitignore` (newest, May 31) omits OS/IDE patterns.
- **Risk:** Leaks local dir structure / IDE run-config; `workspace.xml` is the kind of file that later accumulates DB URLs → recurring leak risk; cross-repo inconsistency.
- **Evidence required:** Add `.DS_Store`+`.idea/` to `myblog_music/.gitignore`; `git rm --cached` the 5 files.

**[P3-6] `infra/placeholder.zip` (260B)** · `intentional tradeoff` — standard Terraform Lambda-bootstrap artifact (`lambda.tf` filename), correctly not gitignored. Non-issue.

**[P3-7] No tracked `.env`/secret files anywhere** · `false positive` — scanned all 6 repos; only `infra/secrets.tf` (config, reads by name, no inline values). Clean baseline (except P3-1 local state).

**[P3-8] `myblog_front` tracks `.vscode/` (incl. a typo'd orphan `setting.json`)** · `real issue` *(missed)*
- **Now:** Tracked `.vscode/setting.json` (typo, holds real config that VS Code never reads) + `.vscode/settings.json` (`{}`); front `.gitignore` ignores `.idea/` but not `.vscode/`. No secrets.
- **Why:** Same OS/IDE hygiene class as P3-5, different repo.
- **Risk:** IDE-metadata churn; the orphan `setting.json` is a latent footgun (config inert); `.vscode/` later accumulates env/run-config.
- **Evidence required:** Decide whether to share editor config; if not, add `.vscode/` to `.gitignore` + `git rm --cached`; if yes, delete the typo file and keep `settings.json`.

### P4 — Static hosting / CloudFront / S3 posture

> Verified against **live prod** (read-only `curl` GETs + `aws s3api get-bucket-policy`) + tfstate, not just code. Net: an **acceptable Free-plan personal-blog tradeoff** whose only real debt is **drift-blindness** (console-created resources unmanaged by Terraform).

**[P4-1] CloudFront origin is the S3 WEBSITE endpoint** · `intentional tradeoff` *(downgraded from real issue)*
- **Now:** `cloudfront.tf:50` origin = `myblog-prod-web.s3-website…` (tfstate confirms, no `s3_origin_config`). Website endpoints are HTTP-only and can't be fronted by OAC — this drives the whole P4 posture (public bucket, http-only origin, no OAC).
- **Why:** Website endpoint gives built-in index/error-document routing for the Astro directory build; the console-created CF `handler` viewer-request function leans on website semantics. REST+OAC would require moving index resolution fully into the CF function.
- **Risk:** Mandates P4-2/P4-3/P4-4. Low severity for fully-public blog content; it's the root design choice, not an independent defect.
- **Evidence required:** Already gathered (website endpoint returns real index.html over HTTP). A REST+OAC migration would need Astro routing validated against the CF function.

**[P4-2] Bucket is fully public; bucket policy is unmanaged by Terraform** · `real issue` *(on the drift-blindness basis)*
- **Now:** `s3.tf:17-24` all four public-access-block flags = false (tfstate confirms); live policy has `PublicReadGetObject` (Principal `*`, `s3:GetObject`) — **not** in any `.tf` (no `aws_s3_bucket_policy` resource; the policy text appears only as the read-back `policy` attribute on `aws_s3_bucket`). Live HTTPS REST GET `/index.html` → 200 (anon read works). Live policy also has a **dead** `AllowCloudFrontServicePrincipal` OAC statement (scoped to the current dist `E2Q2JH5EAYVU1O`, inert because origin = website endpoint).
- **Why:** Website serving requires anonymous read; with no OAC possible (P4-1), `PublicReadGetObject` is the only way. The policy is a console artifact never imported.
- **Risk:** The policy lives outside Terraform → `plan` shows nothing for it; out-of-band changes/deletions are invisible to IaC/CI. (Anon **PUT**→403 and **LIST**→403 — only `GetObject` is exposed, so the "future world-readable PUT" is not currently live.) Read-path bypasses CloudFront/WAF.
- **Evidence required:** Import the policy into TF (`aws_s3_bucket_policy`) for plan-visibility + remove the dead OAC statement; if moving to OAC, re-tighten public-access-block + replace the public grant, then re-probe (REST → 403 anon).

**[P4-3] HTTP-only origin → plaintext CF↔S3 hop + anon-reachable plain-HTTP origin** · `intentional tradeoff`
- **Now:** `cloudfront.tf:55` `origin_protocol_policy=http-only` (forced by website endpoint). Live: website endpoint HTTP→200, HTTPS→000 (no TLS). Viewer traffic IS HTTPS-enforced (`:81 redirect-to-https`); only the CF→origin hop + the direct-bypass path are plaintext.
- **Why:** Unavoidable consequence of P4-1.
- **Risk:** CF→origin hop is in-AWS-backbone (low). The material exposure is the origin being anon-reachable over plain HTTP outside CloudFront (no WAF/TLS) — inherent to the website-endpoint design, low for public assets.
- **Evidence required:** Already gathered; eliminating it requires the REST+OAC migration (P4-1/2).

**[P4-4] No OAC/OAI — origin not locked to CloudFront** · `intentional tradeoff` *(downgraded)*
- **Now:** No `aws_cloudfront_origin_access_control`/`identity` in `.tf` or state. OAC is incompatible with the website endpoint, so it was omitted. The dead `AllowCloudFrontServicePrincipal` statement references the **current** live dist (not an abandoned one) but is inert.
- **Why:** OAC requires the REST endpoint (P4-1).
- **Risk:** Defense-in-depth gap (origin reachable bypassing CloudFront/WAF), adds nothing exploitable beyond P4-2 for public content.
- **Evidence required:** Same REST+OAC migration; verify post-change REST→403 anon.

**[P4-5] Legacy TLS values (SSLv3/TLSv1/TLSv1.1) in `origin_ssl_protocols`** · `false positive`
- **Now:** `cloudfront.tf:56` lists legacy protocols on the S3 origin, but it's **inert** — that origin is http-only and the website endpoint refuses TLS (HTTPS→000), so the list is never exercised. The TLS-using API GW origin is correctly pinned to `["TLSv1.2"]`. Viewer min TLS is actually `TLSv1.3_2025` live (stronger than the `.tf`'s `TLSv1.2_2021`, which is intentionally stale under `ignore_changes`).
- **Risk:** None now; only a footgun if this origin is ever flipped to https-only (trim the list then).

**[P4-6] Overall judgment** · `intentional tradeoff`
- **Now:** Posture is internally consistent for 100%-public content; viewer HTTPS enforced, WAF attached, Free-plan constraints understood. Nothing in plan.md/rfcs tracks an S3/OAC item.
- **Risk:** Genuinely low for this content. Concrete debt = operational drift-blindness (P4-2, plus P4-7/P4-8 below).
- **Evidence required:** A `terraform plan` importing the bucket policy (confirm clean drift); staging validation only if pursuing REST+OAC.

**[P4-7] WAF web-ACL + SPA-routing CF function are unmanaged by Terraform** · `intentional tradeoff` *(missed)*
- **Now:** `cloudfront.tf:41` (WAF ACL) and `:90` (CF `handler` function) are hardcoded ARNs; state has **no** `aws_wafv2_*` or `aws_cloudfront_function` managed resource — both console-created, plan-invisible.
- **Risk:** Broadens the drift theme to two security-relevant controls. A console edit/deletion of the WAF rules or the routing function is invisible to `plan`/CI; deleting the function breaks SPA deep-link routing site-wide.
- **Evidence required:** Import `aws_cloudfront_function.handler` (+ optionally the WAF ACL) into TF, or document them as intentionally-external in `infra/README.md`.

**[P4-8] No S3 access logging; versioning disabled** · `intentional tradeoff` *(missed)*
- **Now:** tfstate: `versioning=false`, logging empty, SSE-AES256 live but undeclared in `s3.tf`. Bucket is anon-reachable.
- **Risk:** Low for regenerable public assets — no access trail for the CloudFront-bypass path, no object-version recovery (a redeploy restores content).
- **Evidence required:** Decide whether the public-bypass path warrants access logging; one-line backlog note alongside P4-6.

### P5 — Music search structure & observability

> **No caching is recommended.** The per-process TTL cache is described only to bound worst-case reasoning (P5-7).

**[P5-1] Per-artist N+1 expansion loop (dominant query-growth site)** · `real issue`
- **Now:** `_compute_unified_search` Phase-2 loops over `literal_artists` issuing one DB query per artist: `album_repo.list_by_artist_id_simple` (`search_service.py:200-205`) and `track_repo.list_by_artist_id` (`:207-212`). `literal_artists` is capped only by `limit` (`le=100`, `search.py:28`). All shared_db relationships are `lazy='select'`, so each per-artist call re-fires its `selectinload` batch (~2 round trips/artist for albums + ~4 for tracks). Worst case ≈ **~600 serial Neon round trips** at `limit=100`/all-types. *(The prior review's "~220" counted only main statements, omitting selectinload side queries — corrected. `list_by_album_ids` IS bulk, not N+1; mappers add no N+1.)*
- **Why:** BUG-19 "literal match → 1-hop expansion"; per-artist (not bulk) calls were deliberate so each artist gets a bounded per-artist LIMIT (bulk-with-per-group-limit needs a lateral/window query). At ~1k-artist prod catalog + default `limit=20`, the loop is short in practice.
- **Risk:** A broad query at `limit=100` fans into ~600 serial round trips on the cache-miss path → multi-hundred-ms-to-seconds tail against the 15s Lambda timeout. **Strict worst-case ceiling, realistically rare** at current scale — but keyed off an attacker-controllable `limit`.
- **Evidence required:** Measure the literal-artist-count distribution for real prod queries (read-only probe at prod catalog via `RECALL_GATE_DB_URL`); count actual statements per request via a `before_cursor_execute` hook for `limit∈{20,100}`; pull `musicApi` Duration p99 (free metric) to see if a tail already exists.

**[P5-2] Multi-token decomposition multiplies queries by split count** · `real issue` *(mildest of the three)*
- **Now:** Decomposition runs for 2–3-token queries; `_decompose` loops up to `DECOMP_MAX_SPLITS=6` splits × (1 artist + 1 title search) per bucket × 2 buckets ⇒ ≤24 main statements + selectinload side queries. **Bounded** (independent of `limit`), a ~7× fixed surcharge vs a single-token query.
- **Why:** Step-6 precision read of "`<artist> <title>`" queries; splits clamped to 6, top-5 artists/split. Designers accepted the fixed cost for the Hit@5 gain.
- **Risk:** A 3-token query adds ~24+ round trips on top of P5-1; bounded but unmonitored.
- **Evidence required:** Fraction of prod queries with 2–3 tokens; local statement-count probe; p50/p99 single- vs multi-token (not separable today).

**[P5-3] `limit` amplifies DB work super-linearly (public, unauthenticated input)** · `real issue`
- **Now:** `limit` (≤100) widens each query AND multiplies the per-artist expansion loop count (P5-1) AND sets decomposition title width; post-fetch trim happens only at the end, so a high `limit` doesn't reduce upstream work. `/unified` is **unauthenticated** (verified: `ANY /api/music/{proxy+}` has no authorizer; only `/candidates` has an app dep) and on CloudFront `CachingDisabled`, so every distinct `(q,limit,offset)` reaches Lambda with no CDN dedup.
- **Why:** `limit` is a single per-bucket knob; trimming after fetch keeps ranking correct; `le=100` is the only guard.
- **Risk:** A caller can drive ~600 serial DB round trips per request with `limit=100` + a broad query — a cheap-to-send, expensive-to-serve **DB-amplification asymmetry**. (Severity caveat: low-traffic single-owner blog, small practical blast radius.)
- **Evidence required:** Confirm `/unified` reachability (done); load-test `limit=100` broad query against a non-prod Neon branch + capture Duration + Neon active-query metrics; decide whether a lower default-vs-max `limit` or an expansion-artist cap (expand only top-K literal artists) is warranted from measured counts.

**[P5-4] Zero custom metrics / EMF / X-Ray / API GW access logging — only default AWS/Lambda metrics + error logs** · `real issue` *(a visibility gap, deliberate cost-first posture)*
- **Now:** grep across infra + music for `tracing_config`/`xray`/`PutMetricData`/EMF/`access_log` → **nothing**. `musicApi` (`lambda.tf:47-74`) has no `tracing_config`, no `LOG_LEVEL`. `monitoring.tf` defines only failure-count alarms (Errors, Throttles, DLQ, FailedInvocations). The music app has **zero** `logger.info/debug` calls — only 7 warning/error in catch paths.
- **Why:** Cost-minimal, error-first observability consistent with the $0/Free-plan ethos; X-Ray/EMF cost money; prod `LOG_LEVEL` is effectively WARNING.
- **Risk:** No visibility into **latency** or its causes; the P5-1/2/3 query-growth is invisible until it manifests as a 15s-timeout cliff. A slow-but-not-failing search (e.g. 5s p99) never alarms; post-hoc root-causing is near-impossible.
- **Evidence required:** `aws lambda get-function-configuration --function-name musicApi` (confirm no X-Ray, check `LOG_LEVEL`); pull the free `AWS/Lambda Duration p99` baseline before deciding to add anything.

**[P5-5] Cannot isolate any of the 8 named latency sources** · `real issue`
- **Now:** Of {cold start, DB connection, SQL time, Spotify, SQS enqueue, worker retry, EventBridge handler failure, app logic}, only **cold start** (via the free CloudWatch REPORT/Init line) and two **async failure** modes (SQS DLQ, EventBridge FailedInvocations) are observable — none with per-request attribution. No `before/after_cursor_execute`, no connect timing, no enqueue success timing, no Python-stage spans. Spotify latency exists only on `/candidates`, never `/unified` (service boundary), and is untimed.
- **Why:** Same cost-first posture; finer attribution needs X-Ray/EMF, deliberately deferred (`monitoring.tf:96`).
- **Risk:** When the P5-1/3 latency tail surfaces, on-call can't tell Neon cold-start from the per-artist query storm from Python ranking → high MTTR.
- **Evidence required:** Decide a minimum viable signal (one EMF line per `unified_search` = wall-time + DB-statement-count isolates DB+app cheaply, no X-Ray cost); confirm the REPORT line is retained for `/aws/lambda/musicApi`.

**[P5-6] Monitoring is entirely error/availability-oriented, not latency/root-cause** · `real issue`
- **Now:** Every `monitoring.tf` alarm is a failure **count** (Errors≥1, Throttles≥5, DLQ≥1, FailedInvocations≥1); no Duration/p99 alarm; staleness explicitly punted. Log stream is failure-biased (zero info/debug).
- **Why:** "Page me when it breaks" at near-zero cost.
- **Risk:** Detects outages (timeout→Errors) but is **blind to degradation** — exactly the P5-1/2/3 failure mode (slower with catalog growth + high `limit` long before it errors).
- **Evidence required:** Confirm with the owner that latency-blindness is accepted at current scale, OR pull 30 days of Duration p50/p99 — if p99 is climbing toward 15s, a single Duration alarm + one EMF line is the minimal upgrade.

**[P5-7] Per-process TTL cache doesn't bound the structural worst case** · `intentional tradeoff` *(descriptive — not a caching recommendation)*
- **Now:** `unified_search` fronts the fan-out with a per-container `TTLCache(256, 60s)`; cold containers + any new `(q,…)` tuple miss. `/unified` is also on CloudFront `CachingDisabled`, so there's no edge dedup either.
- **Why:** FEAT-music-edge-cache Step-5 DB-protection on the cache-miss path; bounded + short TTL.
- **Risk:** Not a defect — but it means P5-1/2/3 worst-case stands: the cache cannot mask the fan-out for distinct/first-seen queries or across short-lived containers. "The cache makes fan-out a non-issue" would be wrong.
- **Evidence required:** None for correctness. (Cache hit-rate measurement is itself an instrumentation gap, P5-4.)

*(P5-M1 `pg_trgm` fuzzy OR widens `literal_artists` toward `limit`, making P5-1's worst case more reachable in prod — `unclear`, re-run the P5-1 probe with trgm on/off. P5-M2 verified the cache stores Pydantic value objects, not ORM rows — confirms P5-7 safety; no defect.)*

### P6 — HTTP semantics / side-effecting GET

> Planning only — **no method change**; caching not proposed as a remedy.

**[P6-1] `GET /api/music/search/candidates` triggers Spotify call + SQS enqueue** · `intentional tradeoff`
- **Now:** `@router.get("/candidates")` (`search.py:61`) → `CandidateSearchService.search_candidates` makes a synchronous Spotify call (`cadidate_search_service.py:33`) + a fire-and-forget SQS `enqueue_album_sync` (`:66`); no DB write itself. The frontend treats it as a "Sync" button with a 3s client cooldown.
- **Why:** Deliberate writer/admin "sync from Spotify" path, distinct from the DB-only `/unified`; kept GET ("기존 유지") because the client invokes it like a search and it returns a result set; enqueue is wrapped in try/except so a queue failure never breaks search.
- **Risk:** GET semantics invite replay by prefetchers/crawlers/retries — each replay spends Spotify quota and can re-enqueue (existing-id dedup only suppresses *already-absorbed* albums; a burst for not-yet-absorbed albums still floods `blogSQS`). The 3s cooldown is the only throttle and lives in one frontend component — useless against direct callers.
- **Evidence required:** CloudWatch `blogSQS SentMessageCount` vs `musicApi` invocations; Spotify 429s in logs; API GW access logs for this route's rate + non-browser UAs. **Do not change the method without auditing caller assumptions in `myblog_front`.**

**[P6-2] The side-effecting `/candidates` GET is effectively UNAUTHENTICATED in prod** · `real issue`
- **Now:** `search.py:75` declares `Depends(require_cognito_token)`, but `auth.py:30-34` returns `{}` when `ENV in (local,dev)` OR `COGNITO_USER_POOL_ID` unset. The music Lambda **never sets `ENV`** (config default = `'local'`); live tfstate shows the deployed `musicApi` env has exactly 5 vars and **no `ENV` key**. So `settings.ENV=='local'` in prod → the guard short-circuits and never validates a JWT. The route also has no gateway authorizer (`ANY /api/music/{proxy+}`).
- **Why:** The in-Lambda guard was intended to gate this; the ENV-bypass exists for local/dev; omitting `ENV=prod` in `lambda.tf` is an oversight (the guard's presence shows intent to authenticate).
- **Risk:** Anyone reaching the music API can call `/candidates` with no token and drive Spotify quota burn + SQS flooding at will (P6-1) — and the documented "controlled writer path" boundary is not actually access-controlled in prod.
- **Evidence required:** `curl '<prod>/api/music/search/candidates?q=test&type=album&limit=1'` with no auth → 200 (bypass) vs 401. **Fix-blast-radius caveat:** naively setting `ENV=prod` flips `require_cognito_token` on for the *whole* music Lambda — but the public reads (`/unified`, `/albums/*`, `/artists/*`) carry no such dep, so they stay open (verified); a targeted fix is needed. Reconcile with the AUTH area.

**[P6-3] `/candidates` not edge-cached, but `cached_methods=GET` + no `Cache-Control`** · `intentional tradeoff`
- **Now:** `/api/*` uses `CachingDisabled` (`cloudfront.tf:123`), so CloudFront doesn't cache it; only `/api/music/albums/*` is edge-cached. But the `/api/*` behavior keeps `cached_methods=['GET','HEAD']` and the handler sets **no `Cache-Control`** (unlike `/unified` + album/artist detail).
- **Why:** `CachingDisabled` deliberate; the missing `no-store` is just an omission (the edge already won't cache it).
- **Risk:** Low at the edge. Residual: browsers/forward proxies may heuristically cache or safe-GET-retry a 200 GET with no `Cache-Control`, replaying the side effect (defense-in-depth gap, not an active bug). *(Caching is NOT proposed as a fix — flagged only as a GET-cacheability risk; a `no-store` header is signal-only.)*
- **Evidence required:** `curl -i` a prod `/candidates` call to confirm no `Cache-Control`.

**[P6-4] All other GET routes audited — no hidden side effects** · `false positive`
- **Now:** Full GET inventory checked: `/unified` is DB-only; `/artists/*`,`/albums/*` DB-only reads; backend library GETs read worker-fed caches; the one refresh trigger is correctly `POST /refresh-recent`→202 (SQS only). `/candidates` is the single side-effecting GET. `GET /spotify-connection` does an external Secrets read but is idempotent + writes nothing.
- **Risk / evidence:** None — correctly read-only.

**[P6-5] Music Lambda has NO edge_guard / x-origin-verify at all** · `real issue` *(missed)*
- **Now:** grep for `edge_guard`/`x-origin-verify`/`EDGE_SECRET` in `myblog_music/app` → **zero**. The WAF is on CloudFront only (AUTH-7); the invoke domain bypasses CloudFront/WAF. So the music Lambda has **neither** a gateway authorizer **nor** an in-app origin check — its only intended control was `require_cognito_token`, which is bypassed (P6-2).
- **Risk:** Amplifies P6-1/P6-2: the abuse path is reachable even if WAF rate rules existed on CloudFront, because the execute-api domain skips WAF. A scripted loop on the raw URL burns Spotify quota + floods SQS with no auth/origin-verify/throttle.
- **Evidence required:** Confirm the execute-api default endpoint is reachable; probe both CloudFront + raw domains with no auth. Fix = `ENV=prod`+real-token on `/candidates`, and/or add edge_guard to music + restrict to CloudFront-only.

**[P6-6] No API Gateway stage throttle / usage plan** · `real issue` *(missed)*
- **Now:** The `$default` stage (`apigateway.tf:18-22`) has `auto_deploy=true` and no `default_route_settings` throttle; grep for throttle/usage_plan/quota finds only Lambda Throttle *alarms*, not request throttling. The only rate limit anywhere is the 3s client-side cooldown.
- **Risk:** With auth bypassed (P6-2) + origin-verify absent (P6-5), an attacker is bounded only by Spotify's 429s + Lambda concurrency, not by anything the project controls.
- **Evidence required:** Confirm no `default_route_settings` throttle in code/tfstate; decide a modest `throttling_burst_limit`/`rate_limit` once the auth gap is closed. Planning-only; pairs with P6-2.

### P7 — IAM & least privilege

**[P7-1] Music role grants `rds:Start/Stop/DescribeDBInstances` on a phantom RDS instance (Neon-only stack)** · `real issue` *(low-risk dead grant)*
- **Now:** `iam_roles.tf:84-102` (`music_rds_ctrl`) allows those actions on `arn:…:db:blogdb` (account 338183196042); no `aws_db_instance`/RDS resource exists anywhere; `README.md:45` already calls it a removable residual grant.
- **Why:** Legacy console-era role (predates the Neon migration), imported verbatim to avoid an apply-time diff; `AmazonRDSFullAccess` was dropped, this narrow grant left as low-priority cleanup.
- **Risk:** Effectively harmless — Start/Stop/Describe on a single non-existent ARN do nothing; only audit noise. (Theoretical: if someone later creates a real RDS literally named `blogdb` in that account.)
- **Evidence required:** `aws rds describe-db-instances --region ap-northeast-2` (expect empty); a `terraform plan` showing only this policy deleted (human-run apply).

**[P7-2] SQS IAM placeholder/wrong account id (`123456789012`)** · `false positive`
- **Now:** Workspace-wide, `123456789012` appears only in a Korean **comment** (`iam_roles.tf:150`) and a unit-test dummy (`test_config.py:15`). Every real SQS policy uses `var.account_id=338183196042`; tfstate's only real account id is 338183196042; `123456789012` is absent from state.
- **Risk / evidence:** None — the hypothesized live wrong-account policy does not exist.

**[P7-3] Worker SQS-consume + logs grant lives in a console-managed policy unverifiable from the repo** · `unclear` *(most material P7 governance gap)*
- **Now:** `iam_roles.tf:158-161` attaches `AWSLambdaBasicExecutionRole-976d757e-…` by ARN — a console `/service-role/` customer-managed policy with no `aws_iam_policy` resource and no body in tfstate. The worker's only TF-owned SQS grants are produce-side; yet the worker is the SQS **consumer**, so `ReceiveMessage/DeleteMessage/GetQueueAttributes` (+ logs) must live in that unaudited policy.
- **Why:** Console-auto-generated at function creation; referenced by ARN at IAC-2 import rather than re-authored.
- **Risk:** Operational/governance — the worker's consume perms live in a policy Terraform doesn't own and can't reproduce/audit; a console edit/deletion → silent consumer outage invisible to `plan`. Low breach risk; medium drift risk.
- **Evidence required:** `aws iam get-policy-version` on that ARN — confirm it grants consume + logs scoped to `blogSQS` and check for `Resource:'*'` over-grant; consider importing as a TF-managed policy.

**[P7-4] Backend `kms:Decrypt` on `Resource:'*'` (scoped by `kms:ViaService`)** · `intentional tradeoff`
- **Now:** `iam_roles.tf:59-65` grants `kms:Decrypt` on `*` with `Condition kms:ViaService=ssm.ap-northeast-2.amazonaws.com`, paired with path-scoped `ssm:GetParameter` on `/myblog/prod/db/*`.
- **Why:** AWS's documented pattern for SSM SecureString decrypt without pinning the key ARN.
- **Risk:** Low — decrypt only honored when SSM mediates it, and SSM access is path-scoped.
- **Evidence required:** Optional — pin the key ARN if tightening desired.

**[P7-5] Music role attaches `AWSLambdaSQSQueueExecutionRole` (account-wide SQS consume, `Resource:*`) though musicApi is producer-only** · `real issue` *(missed; broader over-grant than P7-1)*
- **Now:** `iam_roles.tf:79-82` attaches the managed policy granting `sqs:ReceiveMessage/DeleteMessage/GetQueueAttributes` on `*` — but `musicApi` has **no** SQS event-source mapping (only the worker does) and the music SQS client is **send-only** (`sqs_client.py:16,80-102`); its real need is covered by the narrow inline `music_sqs_produce` (blogSQS only). The area's first pass wrongly waved this off as "standard".
- **Why:** Attached during setup; never trimmed.
- **Risk:** Low-to-medium — a **live, account-WIDE** consume grant (vs P7-1's dead grant on a non-existent resource). A compromised music Lambda could drain `blogSQS` (dropping worker jobs) and read queue attributes account-wide.
- **Evidence required:** `aws lambda list-event-source-mappings --function-name musicApi` (expect empty); remove the attachment and re-plan (inline produce policy already covers the need); human-run apply.

> P7 sweep otherwise clean: only two `Resource:'*'` uses (the conditioned `kms:Decrypt` + the conventional logs grant); no FullAccess/`iam:*`/`PassRole`; correctly-scoped assume-role trust; per-secret Secrets access with a deliberate worker-write / backend-read split.

### P8 — Feature sequencing risk

**[P8-1] Expansion inventory — all draft, none active** · `false positive`
- **Now:** plan.md `Active` = `_(none)_`; Backlog = genre-distribution + multi-user (draft); Later = genre-taxonomy (draft, deferred 2026-06-05); Frozen = new-release-feed (idea-only, no RFC). All 3 RFCs are `Status: draft`; zero accepted/in-progress.
- **Risk:** None — a healthy parked state (documents the baseline).

**[P8-2] No stabilization/hardening work tracked anywhere (KEY GAP)** · `real issue`
- **Now:** grep for `stabiliz/tech-debt/hardening/cleanup/BUG-` across plan.md + rfcs → no work row. The P0–P2 findings live only in chat memory. *(Correction: `POST /api/metrics/batch` is read-only — drop it from the "unauthed write" list; only `categories` is a real write hole.)*
- **Why:** The audit was read-only with findings "in chat only"; it produced no PR, so plan.md (which drops finished rows) has no footprint.
- **Risk:** Concrete known-live defects (AUTH-1, AUTH-9, P1-1) have no owner/tracking and will be forgotten when chat memory ages out; a next session sees an empty Active and starts feature work on an un-hardened boundary. *(The genre RFC already hard-codes a 🔴 "do not copy categories_post" warning — live proof the unfixed boundary is leaking into queued design.)*
- **Evidence required:** Confirm AUTH-1 reachability; size the P1-1 double-delivery window; decide which audit items become BUG-N rows vs an RFC. **This RFC + the plan.md change (below) close this gap.**

**[P8-3] Multi-user depends on the same auth boundary P0 flags** · `real issue`
- **Now:** FEAT-multi-user-accounts explicitly "needs an auth model… before promotion". The substrate has confirmed holes (AUTH-1 unauthed write + AUTH-3 Bearer bypass). Single-admin masks them today (one JWT holder); multi-user makes per-user authz first-class on top.
- **Risk:** Building per-user authz on a substrate with a known unauthed write + edge_guard bypass risks inheriting/papering over the hole, blast radius growing 1→N users. The clearest "expansion-before-stabilization" case.
- **Evidence required:** Resolve P0 (auth-boundary) and name it as a **precondition** in the multi-user RFC; enumerate all API GW routes lacking `authorization_type` and verify each against intended auth.

**[P8-4] Genre taxonomy stacks V13 + a 2-version backend pin jump on existing pin drift** · `real issue`
- **Now:** Genre Step 1 adds `V13__genres.sql` + bumps 0.11.0→0.12.0; Step 3 jumps backend pin @v0.10.0→@v0.12.0 (a 2-version jump pulling in V11 `parent_id` + V12 state the backend has never run against). The feature already forced two renumbers (V12→V14→V13).
- **Why:** Hand-numbered `V{N}__` with no Alembic runner; backend pin lag is normal until a service needs the column. The number itself is documented-correct (V13); the residual risk is the un-caught-up pin + manual-ordering fragility.
- **Risk:** Wrong rollout order → backend 500 on unknown table (RFC's own warning). The 2-version jump needs a real-engine integration test (`feedback-sa-session-lifecycle-mock-blind`), not mocks.
- **Evidence required:** Verify prod Neon has V11+V12 and nothing above; confirm V13 free; integration-test backend @v0.12.0 against a real engine; `terraform plan` shows only `genres_post` added.

**[P8-5] Distribution + new-release-feed inherit the worker/EventBridge gap** · `unclear` *(downgraded from real issue — prior framing overstated)*
- **Now:** Both ride the EventBridge/worker ingest path. **But** FailedInvocations IS alarmed for both cron rules (`monitoring.tf:104-121`, commit #6d468cb), handler-logic failure propagates → Lambda Errors alarm (`:29-47`), and async invokes carry AWS's default 2 retries; the SQS path has its own DLQ + alarm. The only genuine residual = no explicit `dead_letter_config` on the EventBridge *targets* (no per-failure forensic capture after retry exhaustion).
- **Risk:** Weaker than painted — delivery + handler failures are both alarmed, so "distribution charts undercount with no alarm" is inaccurate. The sequencing dependency is real but minor.
- **Evidence required:** CloudWatch EventBridge FailedInvocations + worker Errors/Throttles over a window to quantify any silent drop; verify cron-target alarm coverage before treating the gap as open.

**[P8-6] plan.md doesn't surface stabilization as top active/next work** · `real issue`
- **Now:** plan.md structure (Active none → Backlog 2 expansions → Later → Frozen) puts the top non-empty queued items as pure expansion; no row represents the stabilization findings. *(Largely a reader's-eye restatement of P8-2.)*
- **Risk:** A next session following the documented workflow (read plan.md → pick top work) naturally starts an expansion, re-creating P8-3/4/5 risks.
- **Evidence required:** Owner decision (Korean question) on which audit items become rows + at what priority. **Resolved by the plan.md change below** (STAB-1 as top Active + expansion explicitly behind it).

**[P8-7] edge_guard Bearer bypass is the load-bearing, route-wide auth defect** · `real issue` *(missed; = AUTH-3, elevated)*
- **Now:** Same mechanism as AUTH-3 — `main.py:45-52` admits any `/api` request whose `authorization` merely startswith `Bearer `, never validating the token, defeating the edge secret on **every** authorizer-less route (catch-all GETs, `categories`, `metrics`).
- **Risk:** The broader, more structural of the multi-user preconditions; should be a named precondition distinct from the categories-route fix.
- **Evidence required:** curl the **invoke** URL (not CloudFront) with `Authorization: Bearer junk` + no x-origin-verify → 2xx confirms bypass. Fix: validate the JWT in edge_guard for authorizer-less routes, or attach authorizers / app deps.

---

## Prioritization & stabilization sequencing

Recommended order (highest risk-reduction-per-effort first; each gated by its evidence above and by the one-RFC-step-per-session rule):

1. **P0 Auth boundary (highest).** AUTH-1 (gate/remove `POST /api/categories`), AUTH-3/AUTH-9/P8-7 (edge_guard Bearer bypass → drafts/archived disclosure + unauthed write), AUTH-5 (backend `COGNITO_USER_POOL_ID` + fail-closed `auth.py`), P6-2/P6-5 (music `ENV=prod` + origin-verify/auth on `/candidates`), AUTH-7/P6-6 (WAF/throttle on the invoke path). These are internet-reachable, unauthenticated, and the substrate every expansion builds on.
2. **P1-1 SQS visibility timeout** — the one P1 item with live data-loss/duplicate-work impact (premature DLQ of slow-but-correct syncs). Fix `blogSQS` visibility ≥ worker timeout.
3. **Cross-cutting prerequisite (do first, cheap):** confirm the **SNS `myblog-alerts` email subscription is click-confirmed** (P1-6) — otherwise every alarm is silent and all observability conclusions are moot. **RESOLVED 2026-06-05** — live check shows a real SubscriptionArn (confirmed/active, not `PendingConfirmation`); alarms deliver. No action needed (see Decisions log).
4. **P2-8 / MODEL-12 schema.sql backfill + architecture.md fixes** — the contract docs are actively misleading (and block correct planning for the section redesign + genre work).
5. **Category → section model redesign** (the §decision) as a scoped implementation RFC — depends on the P0 auth fix (removes the public create API) and the schema clarity from step 4.
6. **P3 hygiene** (bundle.zip untrack + .gitignore repairs + OS/IDE files) and **P3-1 remote tfstate backend** — low-risk, improves reproducibility/recovery.
7. **P7-5 / P7-1 IAM trims**, **P4 drift-blindness** (import bucket policy + CF function/WAF into TF or document), **P5 observability** (only if the free Duration p99 baseline justifies it — necessity-gated).

**Expansion → stabilization dependency map** (each expansion waits behind its area):

| Expansion | Blocked behind |
|-----------|----------------|
| FEAT-multi-user-accounts | **P0 auth boundary** (blast radius 1→N) |
| FEAT-genre-taxonomy | **P2** migration/pin hygiene + schema.sql clarity |
| FEAT-genre-artist-distribution / FEAT-new-release-feed | worker/EventBridge retry-DLQ + **P5** observability (P8-5 — minor; verify alarm coverage) |
| Section taxonomy redesign | **P0 auth** (drop public create API) + **P2-8** schema clarity |

**Product expansion does not resume until the P0 auth boundary and P1-1 are remediated and the section model decision is implemented.** AI suggestions and any other new feature ideas are out of scope until then.

## Evidence required before implementation (consolidated checklist)

Read-only probes to gather before any fix RFC starts (most are non-destructive; data probes are read-only SELECT / throwaway+delete):

- **Auth:** curl the **invoke domain** for `POST /api/categories` (Bearer x, no x-origin-verify) and `GET /api/posts?include_archived=true` → confirm unauth write / draft disclosure (AUTH-1/3/9, P8-7); `aws lambda get-function-configuration` for `ratemymusic-api` (no `COGNITO_USER_POOL_ID`, ENV=prod — AUTH-5) and `musicApi` (no `ENV` key — P6-2); confirm no REGIONAL WAF on the API GW stage + no stage throttle (AUTH-7, P6-6).
- **Worker/SQS:** CloudWatch `blogSQS` age/received-vs-deleted, worker Duration p99 vs 30000ms, `ConcurrentExecutions`, `album-sync-dlq` history (P1-1); **confirm the SNS alert email subscription** (P1-6).
- **Model/data:** prod `SELECT id,name,slug FROM categories`; `SELECT count(*) FROM tags, post_tags`; `information_schema` for `posts.rating` type; enumerate prod posts + content-repo MDX, classify real vs test (MODEL-1/6/7/9).
- **Schema:** diff `schema.sql` vs `_generated_schema.sql` (P2-8/MODEL-12); confirm prod Neon migration ledger ≤ V12 (P8-4).
- **Search/observability:** literal-artist-count distribution at `limit=100` against prod catalog; per-request statement count via `before_cursor_execute`; `AWS/Lambda Duration p99` baseline for `musicApi` (P5-1/4/6).
- **IAM/infra:** `aws rds describe-db-instances` empty (P7-1); `aws lambda list-event-source-mappings --function-name musicApi` empty (P7-5); `aws iam get-policy-version` on the worker `976d757e` policy (P7-3); `terraform plan` to confirm clean drift before importing the bucket policy / CF function / WAF (P4-2/4-7).

## Open questions

OQ1–OQ6 were resolved by the owner on 2026-06-05 (see Decisions log). Residual items, deferred to each scoped fix RFC (not blocking this RFC):

1. **Per-fix BUG-N vs RFC granularity.** Priority order is decided (most-urgent-first = §Sequencing). The exact split of each audit item into a `BUG-N` plan.md row vs a step inside an implementation RFC is decided when that fix is scoped.
2. **Auth fix mechanism detail.** Strategy is decided (both layers, sequenced — see Decisions log); the concrete per-route choice (edge_guard JWT validation vs. gateway authorizer vs. app-level `Depends`) is finalized in the P0 implementation RFC against the gathered evidence.

## Decisions log

| Date | Decision | Step |
|------|----------|------|
| 2026-06-05 | **Public taxonomy domain name = `section`** (rename of `category`) — owner chose `section` over `board` (OQ1) | §model decision |
| 2026-06-05 | **Single section per post** — keep the `category_id`→`section_id` single-FK shape; no join table, no multi-section requirement (OQ2) | §model decision |
| 2026-06-05 | **Review tags reuse the existing `tags`/`post_tags` M:N** — not a new `review_tags` table (OQ3) | §model decision |
| 2026-06-05 | **No public section/category creation API**; sections seeded by migration, future creation internal-only; `POST /api/categories` removed/hard-gated | §model decision |
| 2026-06-05 | **Auth remediation = both layers, sequenced** (OQ4): validate the JWT inside edge_guard for authorizer-less routes **and** set `COGNITO_USER_POOL_ID` on the backend Lambda + make `auth.py` fail-closed + attach gateway authorizers / app `Depends` per mutating route. Detailed mechanism per-route decided in the P0 fix RFC | §sequencing P0 |
| 2026-06-05 | **Priority = most-urgent-first** (OQ5) — the §Sequencing order stands (P0 auth → P1-1 SQS → SNS-sub prerequisite → P2-8/architecture.md → section model → P3 hygiene → P7/P4/P5). Expansion thaws only after P0 + P1-1 + section model | §sequencing |
| 2026-06-05 | **Adopt a remote Terraform backend (S3 + DynamoDB lock)** for `P3-1` — low urgency, scheduled in the P3 hygiene tier, not ahead of P0/P1 (OQ6) | §sequencing P3 |
| 2026-06-05 | **STAB-1 is the top active work**; all product expansion (incl. AI suggestions) is frozen behind it | §sequencing + plan.md |
| 2026-06-05 | **§Sequencing items 1, 2, 4 re-verified against live prod/AWS** (read-only probes) and spawned as scoped implementation RFCs: **STAB-2** (P0 auth), **STAB-3** (SQS visibility), **STAB-4** (schema/doc drift). All `draft` (accept = human-only). Live confirmations: AUTH-1/3/4/5/9 + P6-1/2/5/6 (item 1), P1-1 redelivery actively occurring but DLQ-loss=0 (item 2), 6 tables missing from `schema.sql` + `library_items` V7 ghost (item 4). | §sequencing items 1/2/4 |
| 2026-06-05 | **§Sequencing item 3 (SNS alert email sub, P1-6) — RESOLVED.** Live: `myblog-alerts` email subscription has a real SubscriptionArn (not `PendingConfirmation`) → confirmed/active → alarms deliver. No fix needed. | §sequencing item 3 |
