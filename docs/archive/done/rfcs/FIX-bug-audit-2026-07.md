# FIX-bug-audit-2026-07 — Consolidated fixes from the 2026-07-07 six-track audit

- **Status**: done (closed 2026-07-07 — all 8 workstreams + 3 deferred items complete; owner-approved close in session)
- **Date**: 2026-07-07
- **Owner**: 박지훈
- **Source**: six parallel audit agents (frontend / backend / SQL / architecture / infra / security), findings cross-verified between tracks. No CRITICAL found.

## 1. Problem

A full-workspace audit surfaced 5 HIGH and ~20 MED defects. The dominant root cause is **twin drift**: lessons already applied once (fail-closed auth, ON CONFLICT key sort, fetch→materialize→close) were fixed at the reported site but not swept to duplicated code in sibling repos. This RFC groups the fixes into independently shippable workstreams and adds conventions to stop the drift class itself.

## 2. HIGH findings (fix all — denominator: 5)

| ID | Location | Defect |
|----|----------|--------|
| H1 | `myblog_music/app/core/auth.py:33` | `require_cognito_token` fails OPEN when `COGNITO_USER_POOL_ID` unset (`return {}`) — the exact AUTH-5 pattern already hardened in backend. Un-gates `/candidates` (sync Spotify + SQS enqueue). |
| H2 | `myblog_worker/worker/service/isrc_backfill_service.py:134` + `worker/handler.py:103-105` | Raw `conn.commit()` inside handler-owned `session.begin()` → repro-verified `InvalidRequestError` on context exit; every writing run "fails" after succeeding. Also `except…continue` without rollback aborts all later batches. |
| H3 | `myblog_backend/app/services/post_service.py:286-298` | Album replacement DELETE→re-INSERT on `post_albums` cascades away `post_recommended_tracks` (FK `ON DELETE CASCADE`, `schema.sql:273`) even for an identical album set; re-insert hardcodes `is_classic=False`; `update()` commits per field group so a late 400 leaves a half-applied edit. |
| H4 | `infra/monitoring.tf:69-85` | DLQ alarm watches `NumberOfMessagesSent`, which redrive never increments → alarm can never fire; poison messages age out silently. `album-research-dlq` has no alarm at all. |
| H5 | `myblog_front/src/lib/pocketBuckit/bucketStore.ts:141-145` | `ensureFresh(force=true)` joins an already-in-flight stale fetch → pre-mutation snapshot cached as fresh for 5 min; all optimistic-failure rollback paths depend on this broken force refetch. |

## 3. Workstreams

All workstreams are **parallel/additive** (independent repos/files) unless noted. Each ships as its own PR(s) following the standard flow (local smoke → PR → approval → merge → prod smoke).

### WS-A — Fail-closed + alarms (H1, H4 + edge_guard) — repos: music, backend, infra

1. music: mirror backend's fail-closed guard — missing pool id ⇒ 503, never `return {}`. Gate localhost CORS origins behind `ENV in ("local","dev")` (currently always on with `allow_credentials=True`).
2. backend `app/main.py:51`: require `settings.EDGE_SECRET` truthy before comparing (empty secret + empty header currently passes edge_guard).
3. infra: alarm the album-sync DLQ on `ApproximateNumberOfMessagesVisible >= 1` (research DLQ is removed by WS-G teardown — no alarm needed).

### WS-B — Post data integrity (H3 + PK + N+1) — repos: backend, shared_db (sequenced internally)

1. backend: make `update()` single-transaction (no per-field-group commits); on album replacement, diff instead of delete-all/re-insert (or snapshot+restore recommended-track rows and `is_classic`); add `selectinload(Post.section, Post.tags)` to the posts list (2N+1 today, `posts.py:37-51`).
2. shared_db (next free `V{N}__` — V36 is already taken by FEAT-multi-user-accounts `users`, so V37+): `post_recommended_tracks` PK `(track_id)` → `(post_id, track_id)` (one track currently recommendable by only one post globally). Rollout per the established order: migration → prod apply → service pin bump → workspace contract → frontend. **This sub-step is NOT parallel with other shared_db changes, and must be sequenced against any in-flight multi-user shared_db migration to avoid a version-number collision.**

### WS-C — Worker DB robustness (H2 + session lifecycle + upsert sort) — repo: worker

1. isrc_backfill: remove `conn.commit()`; commit via the owning session per batch, rollback in the `except` path.
2. Apply fetch→materialize→close to the three idle-in-transaction sites: `album_ingest_service.py:53-102`, `saved_tracks_sync_service.py:64-80`, `library_sync_service.py:255-414` (Neon pooler drops idle-in-txn conns; lyrics pipeline is the reference implementation).
3. `sync_service.py:145-208`: sort albums/tracks bulk upserts by conflict key (artists already sorted for exactly this deadlock).
4. Include one real-engine integration test for the txn-boundary changes (mock units are blind to pool semantics).

### WS-D — Frontend state (H5 + data-loss UX) — repo: front

1. bucketStore: on `force=true`, abort/ignore the in-flight request and issue a fresh fetch (or version-stamp responses and drop stale ones).
2. TrashDock `restoreTrash` (`BucketBoard.tsx:2314-2318`): non-album members currently vanish on 복원 — either restore them properly or block trashing what can't be restored. Same blind spot in the tray undo toast (`PocketBuckitProvider.tsx:262-271`).
3. `WriterApp.tsx:46-48`: `todayISO()` uses UTC → KST writers before 09:00 get yesterday's `posted_date`; use the existing +9h KST conversion.
4. `routeAlbumDrop` general-bucket branch (`BucketBoard.tsx:821-823`): add the same-bucket no-op guard the artist branch has (self-drop currently persists a reorder).

### WS-E — CI/deploy hygiene — repos: all four service repos (+ workspace)

1. Add `concurrency: { group: deploy-prod, cancel-in-progress: false }` to every deploy workflow (out-of-order prod overwrites possible today).
2. Add `permissions: contents: read` at workflow level (only front code-review sets any today).
3. Add the `github.ref == 'refs/heads/main'` guard to worker + front `workflow_dispatch` deploys (backend already has it).

### WS-F — Infra security hardening — repo: infra

1. CloudFront `response_headers_policy`: CSP, HSTS, `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff` (none exist; combined with localStorage tokens this is the XSS→token-theft chain).
2. Throttle the raw invoke path: API Gateway stage/route throttling for `/api/music/*` (uncached DB queries, no guard, bypasses CloudFront today).
3. Delete the stale authorizer-less `POST /api/categories` route (`apigateway.tf:86-90`).
4. Reference the API Gateway id in CloudFront origin locals instead of the hardcoded invoke domain (`cloudfront.tf:4-5`).
5. Import the console-managed public-read bucket policy for `myblog-prod-web` into Terraform (currently invisible drift).
6. `scripts/health.sh:12-21`: replace dead Secrets Manager instructions with SSM (CHORE-secrets-ssm-migration leftover); drop the dead `GetDbParams` IAM statement (`iam_roles.tf:53-57`).

### WS-G — Research stack decision + shared_db pins — repos: infra, worker, music (**needs owner decision**)

1. **Decision (owner, 2026-07-07): (a) tear down.** researchWorkerLambda is live-wired to researchSQS but worker CI never deploys it and the handler has no research branch — messages would be logged and silently deleted. Research is settled on the $0/local-poller mode, so delete the function + queue + DLQ + ESM + related IAM from Terraform (full plan, no `-target`; a human applies locally). Consequence: WS-A.3 covers the album-sync DLQ only — no research-DLQ alarm is needed.
2. Align shared_db pins: bump music + worker `v0.26.0` (V32) → current (V35+); unify pin style (tags, not raw SHAs) so pin comparison is greppable. Optional: a workspace CI step that fails on pin divergence.

### WS-H — Conventions + docs — repos: workspace, worker, music, infra READMEs

1. CLAUDE.md "Code conventions" additions (wording below, §5).
2. README notes: worker (session-lifecycle rule + upsert sort), music (auth twin must stay fail-closed), infra (DLQ alarm metric rule, S3 policy ownership).

## 4. Explicitly out of scope (tracked elsewhere)

- **JWT `aud`/`client_id` verification** and **`owner_id` scoping on buckets/library/playback** — single-user today, HIGH the moment a second user onboards. These become **pre-conditions (gates) in FEAT-multi-user-accounts Phase 0/1**, not steps here.
- Token storage move (localStorage → httpOnly cookie / in-memory) — bundle with the multi-user auth rework; WS-F.1 mitigates meanwhile.
- LOW backlog (fix opportunistically): bucket `note` null-clear sentinel, `/api/db/ping` real query, ILIKE `%`/`_` escaping + `q` max_length, research trigger get-or-create race, `ensureConnectedDevice` timeout, `Resizer` pointercancel, OverviewDash sample-count fallback, `review_bucket_items` CHECK symmetry, publish frontmatter YAML-safe dump + GitHub call timeouts (small — may ride WS-B.1), SQS `batch_size` 10→2 for blogSQS (or queue split if fan-out overload recurs), local pre-migration tfstate shred.

## 5. Proposed CLAUDE.md additions (Code conventions)

> Auth guards fail closed: missing config ⇒ 503, never bypass — and auth twins exist in both backend and music; a guard fix must land in both in the same PR.
> Never hold an open DB session/transaction across an external-API loop (Neon drops idle conns) — fetch → materialize → close.
> Bulk `ON CONFLICT` upserts sort rows by conflict key (deadlock avoidance under SQS concurrency).
> Outbound HTTP always sets an explicit timeout.
> Fixing a pattern-shaped bug in duplicated cross-repo code (guards, clients, settings)? Grep all service repos for the twin and fix every hit in the same PR.

## 5a. Progress log

All workstreams implemented 2026-07-07 (owner drove push+merge+apply in-session). Status by workstream:

- **WS-A — MERGED + prod-verified.** music fail-closed + CORS ENV-gate (myblog_music #49, pytest 54p; prod `/candidates`→401, `/unified`→200), backend edge_guard truthy-secret (myblog_backend #101, pytest 388p; prod smoke 28/0), infra DLQ alarm→`ApproximateNumberOfMessagesVisible/Maximum` (ws #552, **applied** — alarm live, State OK). H1, H4, edge_guard MED. ✅
- **WS-B — backend H3 MERGED-pending** (myblog_backend #103, pytest 388p): atomic `update()` + album **diff** (stops CASCADE pick/`is_classic` loss) + posts-list `selectinload`. **WS-B.2 DONE 2026-07-07** (shared_db #53 = V37 + backend pin bump #104; prod ALTER applied, smoke 28/0, E2E: same track recommended by two posts → both 200). Current-state audit: prod already had PK `(post_id, album_id, track_id)` from diverged bootstrap DDL — the 422 never reproduced in prod; V37 normalized prod + ORM + canonical + `docs/contracts/schema.sql` to the intended `(post_id, track_id)`, ending a 3-way drift.
- **WS-C — worker MERGED-pending** (myblog_worker #66, pytest 308p +1 DB-gated integration test): isrc_backfill txn fix (H2; `Session`-owned commit/rollback, dropped handler `session.begin()`), 3 idle-in-txn sites → fetch/materialize/close, albums+tracks upserts sorted.
- **WS-D — front MERGED + browser-verified 2026-07-07** (myblog_front #247): bucketStore force-refresh (H5) + monotonic seq guard, trash non-album block + conditional undo, `todayISO` KST, routeAlbumDrop self-drop guard. Real-browser click-through done via Playwright vs prod (fixture buckets, cleaned up): self-drop → 0 writes / cross-drop → reorder PUT; artist→trash cold+no DELETE / album→trash hot+1 DELETE; artist remove → no 되돌리기, album remove → 되돌리기; delayed-GET race → 2 tree GETs (force skips stale in-flight); `Date.now` @ 00:30 KST → same-day publish date. Full log in front #247 comment.
- **WS-E — CI hygiene MERGED-pending** (4 PRs: backend #102, music #50, worker #65, front #246): `concurrency` + `permissions: contents:read` + `workflow_dispatch` ref-guard where missing.
- **WS-F — infra MERGED-pending + applied** (ws #554): deleted dead `POST /api/categories` route (prod 404), removed dead backend `ssm` IAM, imported `myblog-prod-web` bucket policy, health.sh SSM fix. **Security response headers DONE 2026-07-07** (ws #557, applied two-stage): Free plan rejects `response_headers_policy` → `cloudfront-js-2.0` viewer-response Function on the default (S3) behavior stamps HSTS(2y, preload)/XFO DENY/nosniff/Referrer-Policy/Permissions-Policy/**CSP-Report-Only**; verified with `aws cloudfront test-function` before attach (0 errors, CU 9); prod `curl -sI` shows all 6, Playwright sweep (home/reviews/detail/search/profile+SDK/write) 0 console errors + 0 CSP violations. Enforcing-CSP promotion = separate future step. Per-route music throttle skipped (stage `$default` throttle already covers it).
- **WS-G — MERGED + applied** (ws #553): researchSQS/DLQ/researchWorkerLambda/IAM torn down (8 resources destroyed).
- **WS-H — this PR**: CLAUDE.md conventions + worker/music/infra README gotchas + this log.

## 6. Exit gates

- 5/5 HIGH findings fixed and prod-verified (denominator: the 5 rows in §2).
- 0 remaining fail-open auth paths across backend+music (denominator: 2 guard twins — verified by grep for `return {}` / ENV-bypass in both `auth.py`).
- DLQ alarm proven live: one synthetic poison message reaches the DLQ and triggers the alarm email within 15 min.
- Workstreams A–F merged + prod-smoked; WS-G decision recorded here; WS-H merged (denominator: 8 workstreams).
- Multi-user pre-conditions (§4) recorded as gates in FEAT-multi-user-accounts before its Phase 0 starts.

## 7. Rollback

All code fixes are behavior-narrowing and independently revertible per PR. The single schema change (WS-B.2, PK widening) is backward-compatible with existing data; rollback = revert migration on the Neon test branch first, prod rollback needs human approval per hard rule #3.
