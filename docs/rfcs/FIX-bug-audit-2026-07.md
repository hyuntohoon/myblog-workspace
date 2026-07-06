# FIX-bug-audit-2026-07 — Consolidated fixes from the 2026-07-07 six-track audit

- **Status**: accepted (2026-07-07, owner-approved in session)
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
2. shared_db V36: `post_recommended_tracks` PK `(track_id)` → `(post_id, track_id)` (one track currently recommendable by only one post globally). Rollout per the established order: migration → prod apply → service pin bump → workspace contract → frontend. **This sub-step is NOT parallel with other shared_db changes.**

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

## 6. Exit gates

- 5/5 HIGH findings fixed and prod-verified (denominator: the 5 rows in §2).
- 0 remaining fail-open auth paths across backend+music (denominator: 2 guard twins — verified by grep for `return {}` / ENV-bypass in both `auth.py`).
- DLQ alarm proven live: one synthetic poison message reaches the DLQ and triggers the alarm email within 15 min.
- Workstreams A–F merged + prod-smoked; WS-G decision recorded here; WS-H merged (denominator: 8 workstreams).
- Multi-user pre-conditions (§4) recorded as gates in FEAT-multi-user-accounts before its Phase 0 starts.

## 7. Rollback

All code fixes are behavior-narrowing and independently revertible per PR. The single schema change (WS-B.2, PK widening) is backward-compatible with existing data; rollback = revert migration on the Neon test branch first, prod rollback needs human approval per hard rule #3.
