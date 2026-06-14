# FEAT-public-bucket-multiuser: Public read-only bucket viewer + multi-user accounts

- **Status**: draft — **investigation + design + task breakdown only. NOT implemented.**
- **Owner**: TBD
- **Created**: 2026-06-14 (overnight Task 3)
- **Plan row**: pointer under `FEAT-multi-user-accounts` (Backlog)
- **Supersedes/absorbs**: expands the `FEAT-multi-user-accounts` stub and the `FEAT-home-redesign`
  D2/D4 "public bucket projection" decision into a single scoped design.

> This RFC is a **design document produced without writing product code** (overnight safety scope:
> no implementation-to-merge, no ACL/IAM changes, no production wiring). It exists to be reviewed,
> sequenced, and approved before any step runs. The current state below is verified against code
> (file:line evidence from a 2026-06-14 read-only cross-repo investigation).

---

## Goal

Let anyone view the owner's album **buckets/crates** as a read-only public page, and (separately,
larger) introduce real multi-user accounts. After Scope A: a logged-out visitor can browse a
curated, read-only projection of the bucket board at a public URL, with private/workflow crates
excluded. After Scope B: the site supports multiple end-users with per-user ownership, public
member pages, and a social graph.

## The two scopes are separable — read this first

The owner bundled this as "public bucket viewer + multiuser," and `FEAT-home-redesign` D2/D4 says
the public bucket projection is "**coupled to multi-user accounts**." **Engineering-wise they are
not actually coupled** — and decoupling them is the single most important decision for the owner:

| | **Scope A — Public read-only bucket viewer** | **Scope B — Multi-user accounts** |
|---|---|---|
| Size | Small (front + 1 backend read endpoint + 1 small migration) | Large (new auth model, users table, ownership FKs across every table, social graph, data migration) |
| Needs a `users` table? | **No** — one owner today | Yes |
| Needs an auth-model change? | **No** — public reads already unauthenticated (see security model) | Yes — single-admin Cognito → per-user identity |
| Delivers the owner's D2/D4 "read-only public viewer of the bucket board"? | **Yes, fully** | Also, but as a side effect |
| Risk | Low, reversible | High, touches every table + the auth boundary |

**Recommendation:** ship **Scope A alone first** (it fully satisfies the stated D2/D4 want — "current
format, not editable, anyone can view"), and treat **Scope B** as a genuinely separate, later,
owner-gated program. Scope A needs only: (1) a per-bucket `is_public` visibility flag (so workflow
crates stay private), (2) a public read endpoint returning only public buckets, (3) a read-only
viewer route/component. No accounts, no auth rework. **This is OQ1 — the owner must confirm the
decouple before Scope A is sequenced.**

## Non-goals (this RFC)

- **No code is written or merged.** No migrations applied. No ACL/IAM/bucket-policy changes.
- Not deciding Scope B's full social-graph schema here — Scope B is sketched at the level needed to
  sequence it and to make sure Scope A doesn't paint it into a corner.
- Not building `/collections` (owner D2/D4 explicitly: "**/collections is NOT built now**").
- Not un-hiding the follower/following/list stats hidden in member-dashboard Step 1 (that is a
  Scope B deliverable).

## Current state (verified 2026-06-14)

### Data model (`myblog_shared_db`)
- **No ownership anywhere.** `review_buckets`, `review_bucket_items`, `album_to_listen_items`,
  `spotify_library_albums`, and `posts` have **no `user_id`/owner column**; data is implicitly the
  single admin's (migrations literally comment "Single user → no user_id").
  Evidence: `models.py:329-465,478-509,285-321`; `V8__…sql`, `V15__…sql`.
- **No `users`/`profiles`/`members` table** in the product schema. (A `neon_auth` schema exists but
  is Neon-platform infra, 0 rows, unrelated.) Evidence: `docs/reviews/2026-06-13/02-db-review.md:98,251`.
- `review_buckets.kind` ∈ {`review` (default), `spotify_library` (≤1, partial-unique-indexed)}.
  `parent_id` gives a nested tree (V11). `research_mode` ∈ {off,all,selected} (V16).
  Evidence: `models.py:356-375`, `V15__…sql:56-62`.
- Migrations are plain `V{N}__` SQL (no Alembic). **Must apply to Neon prod BEFORE a consumer pin
  bumps**, else `unknown column` 500s (`reference-shared-db-cross-repo-rollout`).
- Prod is single-user-tiny: ~983 albums / 1 published post / 5 buckets / 67 bucket items.

### Backend auth (`myblog_backend`)
- **`GET /api/buckets` is currently UNAUTHENTICATED** — served by the catch-all `GET /api/{proxy+}`,
  gated only by `edge_guard` (CloudFront `x-origin-verify`), no JWT. It returns the full nested
  bucket tree + Spotify-library state. Evidence: `routes/buckets.py:150-172`, `apigateway.tf:80-83`,
  `main.py:36-72`. **Same for `GET /api/library/to-listen|reviewed|recently-listened`.**
- All **mutations** (`POST|PATCH|DELETE /api/buckets*`) require a Cognito JWT (API GW authorizer).
  Evidence: `apigateway.tf:142-250`.
- `require_cognito_token` returns the claims dict but **never extracts a subject/user_id** — there
  is no per-user scoping logic in any service. Evidence: `core/auth.py:95-115`, `bucket_service.py`.

### Infra (`infra`)
- Front S3 `myblog-prod-web` is a **public website endpoint** (public-access-block disabled on all 4
  flags — by design for a public static blog). Evidence: `s3.tf:17-24`, `cloudfront.tf:50`.
- **No user-uploaded-content bucket.** Album covers come from Spotify CDN (`i.scdn.co`), not S3.
  Evidence: `content_sync.py:90`, music tests.
- Cognito `MyBlogAdminPool` is **admin-create-user-only (no self-signup)** — provisioned single-admin.
  Evidence: `cognito.tf:1-103`.
- tfstate bucket has full public-access-block ENABLED. CloudFront is on the Free plan (managed cache
  policies only). Evidence: `state_backend.tf:39-45`, `cloudfront.tf:16-34`.

### Front (`myblog_front`)
- `/profile` is **fully auth-gated**: `profile.guard.ts` redirects to Cognito if `!isLoggedIn()`.
  A logged-out visitor sees nothing. Evidence: `profile.astro:76`, `profile.guard.ts:6`, `auth.ts:62-65`.
- `BucketBoard.tsx` owns the crate gallery, fetches `GET /api/buckets` (Bearer), caches to
  `localStorage` (`lf_buckets`, `lf_bucket_views`, `lf_crate_trash`). `MEMBER_IDENTITY` is a
  **hardcoded single user**. Evidence: `BucketBoard.tsx:1243-1391`, `member.ts:90-95`.
- **No `is_private` flag exists** — "workflow" status is inferred from the bucket **name** via regex
  heuristics (`완료/마감/평론/들을/예정…`). Evidence: `BucketBoard.tsx:342-354`.
- The DnD/reorder/color/edit logic is deeply entangled in `BucketBoard`; a read-only viewer needs a
  **new, slimmer read-only `AlbumGrid`** rather than reusing the editable board wholesale.

## Public-access security model — every world-readable surface

> This is the deliverable the task most cares about: **call out every place something becomes (or
> already is) world-readable.** Scope A intentionally publishes data; each line says what leaks and
> the control that must gate it.

1. **⚠️ Pre-existing exposure (verify, owner-review):** `GET /api/buckets` and `GET /api/library/*`
   are **already unauthenticated** behind CloudFront. The owner's "private" buckets — including
   `spotify_library` state and workflow crates — are **already retrievable today** by anyone who
   sends a request through CloudFront (the front only *surfaces* them on the auth-gated `/profile`,
   but the API itself does not gate reads). This RFC does **not** change it (no auth changes in
   overnight scope), but the owner should decide whether that is acceptable. It also means Scope A's
   "make buckets public" is, at the API layer, already partly true — the work is mostly *curating
   what is shown* and *building the viewer*, not *opening access*.
2. **Bucket contents become a public page (Scope A intent).** Album titles/covers/artists/notes/
   ratings in *public* buckets become a crawlable, indexable page. Control: a per-bucket `is_public`
   flag defaulting **false** (private), plus the public endpoint filtering to `is_public = true`.
3. **`spotify_library` bucket must NEVER be public.** It reflects the owner's private Spotify
   library + sync state (and `spotify_id`s tied to the owner's OAuth token). Control: hard-exclude
   `kind='spotify_library'` from the public endpoint regardless of `is_public`.
4. **Workflow crates (e.g. "재평가 대기" / re-evaluation pending) must NOT leak.** Today only a
   name-regex distinguishes them. Control: the explicit `is_public` flag replaces the heuristic;
   owner opts each bucket in. (Decision: opt-IN, default-private — never auto-publish.)
5. **Per-item notes / `rec_reason` / `research_*`** may contain private working notes. Control: the
   public projection must whitelist fields (album + position + optional public blurb), **not** echo
   `note`/`rec_reason`/`research_selected`.
6. **S3 / object storage:** unchanged. No user uploads, covers are external. **Scope A needs no S3
   or ACL change** — the public viewer is just more static HTML in the already-public web bucket +
   a JSON read endpoint. (Explicitly: this RFC requires **no** bucket-policy/public-access-block edit.)
7. **Scope B additionally exposes:** per-user identity, public member pages, and the social graph —
   each its own visibility decision, deferred to Scope B.

## Target state

### Scope A (public read-only bucket viewer)
- `review_buckets.is_public BOOLEAN NOT NULL DEFAULT false` (one additive migration).
- A **public** read endpoint, e.g. `GET /api/public/buckets` (or `/api/buckets/public`) returning
  only `is_public=true`, `kind='review'` buckets with a **whitelisted** field projection (no private
  notes), nested tree preserved.
- A toggle in the owner's `/profile` `BucketCard` header to set `is_public` (Cognito-gated write).
- A public route — recommend **`/collection`** (singular; `/collections` was explicitly deferred) or
  `/shelf` — rendering a **new read-only `AlbumGrid`** (not the editable `BucketBoard`), reachable
  by anyone, no login. Linked from the home/footer.
- Sitemap includes the public collection page; private buckets never appear.

### Scope B (multi-user accounts) — sketch only
- `users` table (id, handle, display_name, created_at, …) keyed to Cognito `sub`.
- `owner_id`/`author_id` FK added to `review_buckets`, `album_to_listen_items`, `posts`, etc.
  (nullable → backfill the single admin → enforce NOT NULL — a multi-step migration).
- Auth model decision: keep single-admin Cognito + add app-layer ownership, **or** enable Cognito
  self-signup / external identity. (OQ.)
- `/members/[handle]` public profile; social graph (follows/lists); un-hide member-dashboard Step-1
  stats.

## Which repos change

| Scope | shared_db | backend | front | infra | contracts |
|---|---|---|---|---|---|
| **A** | 1 additive migration (`is_public`) | 1 public GET + field projection + `is_public` on the bucket write | read-only `AlbumGrid` + `/collection` route + `/profile` toggle | **none** (no ACL/CF change) | openapi regen (new public route) |
| **B** | large (users + ownership FKs, multi-step) | auth model + per-user scoping across services | member pages, account UI, un-hide stats | maybe Cognito self-signup; API GW authorizer | large |

## Open questions (owner decides before sequencing)

1. ✅ **RESOLVED 2026-06-14 (owner): decouple — ship Scope A first**, separate from Scope B (accounts).
2. ✅ **RESOLVED 2026-06-14 (owner): NOT acceptable — harden it as part of Scope A.** "Private = private"
   at the API: non-public buckets require auth; only `is_public=true` buckets are served unauthenticated.
   This folds A5 into Scope A as a required (not optional) task, paired with A2.
3. **Public route name?** `/collection` vs `/shelf` vs reusing `/members/[handle]` (the latter
   presupposes Scope B). Recommend `/collection` for Scope-A-alone.
4. **Visibility granularity:** per-bucket `is_public` only, or also per-item hide? (Recommend
   per-bucket only for v1.)
5. **Scope B auth model:** stay single-admin Cognito + app-layer ownership, or open self-signup?
   (Large; deferred but noted so Scope A's `is_public` doesn't conflict — it won't, it generalizes
   to `owner_id + is_public` cleanly.)
6. **Spotify library + multi-user:** per-user tokens vs admin-only? (Scope B; out of A.)

## Ordered, approvable task breakdown

> **2026-06-14: A1 + A2 + A5 DONE + PROD-LIVE.** OQ1/OQ2 answered; Scope A backend shipped. Remaining:
> A3 (front publish toggle) + A4 (front read-only viewer). Each task independently reviewable, one PR
> where possible. **Scope A first; Scope B only on a separate owner go.**
>
> ⚠️ **Rollout incident (logged):** A2/A5 (be #69) first shipped using `ReviewBucket.is_public` while the
> backend's shared_db pin was still `v0.18.1` (pre-`is_public`) → `AttributeError` 500 on the new public
> endpoint AND the owner's authed `/profile`. Hotfix be #70 repinned to the `is_public` commit (`650b1e5`).
> **Lesson:** apply migration → **bump the consumer pin** → THEN merge code that uses the new column.
> **Follow-up (cleanup):** cut a proper shared_db `v0.19.0` tag, repin the backend to it, bump pyproject.

### Scope A — Public read-only bucket viewer
- **A0 — (optional) read-only spike** on a branch: render the existing `GET /api/buckets` tree in a
  throwaway read-only component to de-risk the `AlbumGrid` extraction. No prod wiring. *(A read-only
  spike is the only build activity sanctioned for this RFC tonight; deferred unless owner wants it.)*
- **A1 — shared_db migration** `V{N}__review_buckets_is_public.sql`: add `is_public BOOLEAN NOT NULL
  DEFAULT false`. Apply to Neon prod **before** any backend pin bump (rollout rule). Reversible
  (`DROP COLUMN`), additive, non-destructive. **✅ DONE + PROD-LIVE 2026-06-14** (shared_db #30, V18
  applied to Neon prod, 5 existing buckets default false).
- **A2 — backend public read endpoint**: **✅ DONE + PROD-LIVE 2026-06-14** (be #69 + ws contract #347 +
  front types #154). Shipped as **`GET /api/buckets/public`** (under the buckets router; not
  `/api/public/buckets`) → only `is_public=true` + `kind='review'`, **flat** (no nesting, so private
  structure can't leak), whitelisted projection (album + position + already_reviewed; **no** private
  item fields), `spotify_library` excluded. `PATCH /api/buckets/{id}` accepts `is_public` (refuses to
  publish the spotify_library bucket → 400). Prod smoke: `200 {"buckets":[]}`.
- **A3 — front `/profile` publish toggle**: a per-bucket `is_public` switch in `BucketCard` (Bearer
  write), with a clear "이 버킷이 공개됩니다" affordance + private default.
- **A4 — front read-only `/collection` route**: new slim `AlbumGrid` (no DnD/edit), fetches the
  public endpoint, no auth, graceful empty state, sitemap-included. Link from home/footer.
- **A5 — API privacy hardening (REQUIRED, OQ2 resolved)**: **✅ DONE + PROD-LIVE 2026-06-14** (be #69).
  `GET /api/buckets` now requires a Cognito JWT (app-layer `require_cognito_token`, full in-Lambda
  validation) — closes the pre-existing unauthenticated exposure of the owner's full board. Prod smoke:
  `401` without a token. (Optional belt-and-suspenders: an API-Gateway authorizer on `GET /api/buckets`
  — not done, app-layer enforcement is sufficient.)

### Scope B — Multi-user accounts (separate program; only on owner go)
- **B1 — RFC accept + data-model design**: finalize `users` + ownership-FK schema + the auth-model
  decision (OQ5). (This promotes the `FEAT-multi-user-accounts` stub.)
- **B2 — shared_db**: `users` table + nullable `owner_id` FKs; backfill admin; (later) enforce NOT
  NULL. Multi-step migration with its own ordering RFC section.
- **B3 — auth model**: extract Cognito `sub` → `users.id`; per-user scoping in services; authorizer.
- **B4 — `/members/[handle]`** public profiles + account UI.
- **B5 — social graph** (follows/lists) + un-hide member-dashboard Step-1 stats.

## Decisions log

| Date | Decision | Notes |
|------|----------|-------|
| 2026-06-14 | Investigation complete; Scope A and Scope B identified as **separable** | recommend shipping A first, decoupled from accounts |
| 2026-06-14 | Visibility = explicit per-bucket `is_public`, default **false**, opt-in | replaces today's name-regex heuristic; `spotify_library` hard-excluded |
| 2026-06-14 | No ACL/S3/infra change needed for Scope A | public viewer = static HTML + JSON read endpoint only |
| 2026-06-14 | Flagged pre-existing unauthenticated `GET /api/buckets` for owner review | not changed here (overnight no-auth-change scope) |
| 2026-06-14 | **OQ1 RESOLVED (owner): decouple — ship Scope A first**, separate from Scope B | Scope A sequenced + started |
| 2026-06-14 | **OQ2 RESOLVED (owner): harden the API — "private = private"** (A5 required, with A2) | non-public buckets require auth; closes the pre-existing exposure |
| 2026-06-14 | **A1 DONE + prod-live** — `review_buckets.is_public` (V18) applied to Neon prod + shared_db #30 | additive, 5 buckets default false |
| 2026-06-14 | **A2 + A5 DONE + prod-live** — `GET /api/buckets/public` (whitelisted, flat) + `GET /api/buckets` now JWT-gated | be #69, ws #347, front #154; prod smoke public=200, board=401 |
| 2026-06-14 | **Public endpoint path = `/api/buckets/public`** (buckets router) | not `/api/public/buckets` as first sketched |
| 2026-06-14 | **Rollout incident** — be #69 shipped is_public code on pin v0.18.1 → 500; hotfix be #70 repinned to `650b1e5` | lesson: bump consumer pin BEFORE merging code that uses the new column; follow-up: cut v0.19.0 tag |
