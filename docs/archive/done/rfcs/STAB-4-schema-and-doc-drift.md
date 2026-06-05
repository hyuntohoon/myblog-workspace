# STAB-4: schema.sql backfill + architecture.md / contract doc drift

- **Status**: done (2026-06-05 — pending archive to `docs/archive/done/rfcs/`)
- **Owner**: TBD (주인장)
- **Created**: 2026-06-05
- **Plan row**: `plan.md` → STAB-4
- **Spawned from**: `STAB-1-stabilization.md` §Prioritization & stabilization sequencing **item 4** (P2-8 / MODEL-12 + architecture.md). STAB-1 + this RFC are **accepted** (2026-06-05, owner-approved).

---

## Goal

Make the canonical contract docs trustworthy again so they stop misleading planning for the section-model redesign, the genre work, and any "does the contract match prod" audit. After this RFC: `docs/contracts/schema.sql` reflects the **actual prod schema** (the 6 missing V6+ tables backfilled, `posts.rating` corrected), and `docs/architecture.md` + `docs/contracts/sqs-album-sync.md` no longer carry the four load-bearing false statements the 2026-06-05 review found.

## Non-goals

- No DB change of any kind — this RFC edits **docs only**. Prod is the source of truth; the docs are brought up to match it. (No migration, no DDL applied.)
- Not adding a migration runner or a `schema_migrations` ledger (prod has none; hand-numbered `V{N}__` stays — P2-5).
- Not pruning the intentional bootstrap tables from `schema.sql` (`reference-schema-sql-bootstrap-tables` — never prune `tags`/`post_tags`/`post_metrics`/`post_comments`/`post_likes`/`outbox_events`/`publishing_runs`/`op_logs`).
- Not rewriting the worker's dead `@v0.2.2` pin or the music `@v0.3.0` pin (intentional per-service lag — P2-6); only the **doc** describing them is corrected.

## Evidence gathered (2026-06-05, read-only prod introspection + local — authoritative)

**Prod schema** (backend `DATABASE_URL`, read-only `information_schema`/`pg_*`):

| Check | Result |
|-------|--------|
| `posts.rating` type | `numeric_precision=3, scale=2` → **`NUMERIC(3,2)`** (matches ORM + V5; `schema.sql:65` says `(3,1)` — stale). |
| prod base tables (24) | `album_artists, album_to_listen_items, albums, artists, categories, op_logs, outbox_events, post_albums, post_artists, post_comments, post_likes, post_metrics, post_recommended_tracks, post_tags, posts, publishing_runs, review_bucket_items, review_buckets, spotify_now_playing, spotify_play_events, spotify_recent_albums, tags, track_artists, tracks`. |
| `review_buckets.parent_id` | present (V11). |
| extensions | `pg_trgm` present (added by V12); `pgcrypto` present (already in `schema.sql:18` bootstrap — **not** a backfill item). |
| `genres` table | **absent** (`to_regclass` null) → no V13 applied → ledger ≤ V12, **V13 free** (P8-4). |
| migration ledger table | **none** (`schema_migrations`/`flyway_schema_history` both null) → hand-applied, no runner. |
| `library_items` (V7) | **absent** in prod (`to_regclass` null); its enum `library_item_status` **absent** (prod enums = only `post_status`, `review_bucket_item_status`). |
| live row counts | `categories=3`, `tags=0`, `post_tags=0`. |

**Local files:**

- `docs/contracts/schema.sql` has **18** `CREATE TABLE`s, self-declares "Source of truth — update THIS file first," and stopped tracking after V5.
- Tables in prod but **missing from `schema.sql` (6)**: `album_to_listen_items` (V8), `review_bucket_items` + `review_buckets` (V6), `spotify_now_playing` + `spotify_recent_albums` (V9), `spotify_play_events` (V10) — plus the enum `review_bucket_item_status`.
- `myblog_shared_db/src/myblog_shared_db/_generated_schema.sql` (ORM-derived) has **16** tables: it *does* carry the V6+ ORM tables (`review_buckets`, `review_bucket_items`, `album_to_listen_items`, `spotify_*`) but **omits `library_items`** (not an ORM model) **and** omits all 8 bootstrap tables. So it is **not** a clean backfill source either.
- Migration files present: `V2`..`V12`, gapless, no `V1`. `V7__library_items.sql` creates a `library_items` table + `library_item_status` enum that **do not exist in prod**.

> 🔴 **Key correction — backfill source.** Neither the migration files nor `_generated_schema.sql` is a reliable source: `V7`'s `library_items` is a **ghost** (never applied / superseded by `V8 album_to_listen_items`), and `_generated_schema.sql` omits both the bootstrap tables and `library_items`. **The authoritative backfill source is a `pg_dump --schema-only` (or `information_schema` introspection) of prod**, reconciled into `schema.sql`'s existing hand-written style. Do **not** copy V7 in.

**architecture.md / contract drift** (local grep — confirmed):

| ID | Doc says | Reality |
|----|----------|---------|
| P2-1 | `architecture.md:233` backend pin `@v0.5.0` | `myblog_backend/requirements.txt:10` = `@v0.10.0` (latest tag `v0.11.0`, pyproject `0.11.0`). |
| P2-2 | `architecture.md:215` "FIFO queue (`album-sync.fifo`)" | standard `blogSQS` (tfstate `fifo=False`; `sqs-album-sync.md:6` "Standard queue"). |
| P2-3 | `architecture.md:243` worker "imports `myblog_shared_db.tables`" | `grep` of `myblog_worker` for `from myblog_shared_db|import myblog_shared_db` = **0** (raw `text()` SQL throughout); pin `@v0.2.2` is dead/unimported. |
| P2-4 | `architecture.md:126` `POST /api/categories` = "Cognito JWT" | route `AuthType NONE` (live) — the doc actively conceals AUTH-1 (owned by STAB-2; fix the doc here). |
| P1-7 | `sqs-album-sync.md:7` "DLQ: 미설정 (P1 작업 예정)" | `album-sync-dlq` exists (redrive `maxReceiveCount=3`). Also `:59` describes FIFO `MessageGroupId`/`MessageDeduplicationId` on a queue declared "Standard" at `:6` (internal inconsistency). |

## Current state

`schema.sql` is a stale 18-table subset (missing 6 prod tables + the `review_bucket_item_status` enum, wrong `posts.rating` type), self-declaring "Source of truth" while having stopped tracking after V5. `architecture.md` carries four false load-bearing statements (P2-1/2/3/4) and `sqs-album-sync.md` claims an unconfigured DLQ + implies FIFO semantics on a standard queue (P1-7).

## Target state

`schema.sql` matches prod exactly (introspection-sourced — the full 24-table set + `review_bucket_item_status` + `review_buckets.parent_id` + `pg_trgm`, with `posts.rating NUMERIC(3,2)`, bootstrap tables retained, `library_items` *not* added). `architecture.md` + `sqs-album-sync.md` state the verified facts (or carry an explicit "verify against code — may drift" banner, consistent with `reference-architecture-md-unreliable`).

## Steps

All steps are **doc-only** (no DB/infra/code), independently mergeable, low-risk (revert = trivial). They can reasonably ride a single PR since none touches running systems — but keep them as labeled commits.

> ✅ **All steps done 2026-06-05 (this PR).** Step 1: `schema.sql` backfilled from `pg_dump` of prod — 6 tables + `review_bucket_item_status` enum + `pg_trgm` ext/indexes added, `posts.rating` → `NUMERIC(3,2)` with the actual prod `CHECK (… <= rating_scale)` (not the stale `<= 10`), `library_items` deliberately omitted. **Verified: schema.sql's 24 `CREATE TABLE` set is IDENTICAL to prod's base tables, and the full file executes cleanly against prod in a `ROLLBACK` transaction (exit 0).** Step 2: `architecture.md` P2-1/2/3/4 corrected + drift banner. Step 3: `sqs-album-sync.md` DLQ + FIFO-branch claims corrected.

### Step 1 — Backfill `schema.sql` from prod introspection

`pg_dump --schema-only` (read-only) the prod DB → reconcile the 6 missing tables (`album_to_listen_items`, `review_bucket_items`, `review_buckets`, `spotify_now_playing`, `spotify_recent_albums`, `spotify_play_events`) + the `review_bucket_item_status` enum + `review_buckets.parent_id` (V11) + the `pg_trgm` extension/indexes (V12) into `docs/contracts/schema.sql`, matching its existing hand-written formatting. Fix `posts.rating NUMERIC(3,1)` → `NUMERIC(3,2)` (`:65`, **MODEL-9**) — and copy prod's **actual** `CHECK` constraint rather than preserving the stale `<= 10` literal (note: `(3,2)` can store at most `9.99` and the API-enforced rating domain is 0–5 per `reference-front-rating-model`; if prod still carries `<= 10`, leave a one-line note that the constraint is looser than the domain — tightening it is out of scope here). **Do not** add `library_items`/`library_item_status`: V7 was superseded by V8 `album_to_listen_items` before any prod apply (`models.py:368` comment "the superseded V7 library_items approach"; no `LibraryItem` ORM model; live `/api/library/*` operates on `album_to_listen_items`), so its absence is by design, not a broken endpoint. **Do not** prune bootstrap tables.

**Verification:**
```
# the set of CREATE TABLE names in schema.sql == prod base tables (24)
# diff schema.sql table set against a fresh `\dt` from prod -> empty
# posts.rating line now reads NUMERIC(3,2)
grep -n 'rating ' docs/contracts/schema.sql
```
**Rollback:** `git revert`.

---

### Step 2 — Correct `architecture.md`

Fix P2-1 (pin `@v0.10.0`, note latest `v0.11.0`), P2-2 (standard `blogSQS`, not FIFO), P2-3 (worker imports nothing from `shared_db`; uses raw SQL; `@v0.2.2` pin dead), P2-4 (`POST /api/categories` is currently **unauthenticated** — cross-reference STAB-2). Given `reference-architecture-md-unreliable` flags ≥3 load-bearing errors, also add a short "verify against code; this doc drifts" banner at the top.

**Verification:** `grep -n 'v0.5.0\|FIFO\|shared_db.tables' docs/architecture.md` → no stale hits; the categories row reflects reality.
**Rollback:** `git revert`.

---

### Step 3 — Correct `sqs-album-sync.md`

Fix `:7` ("DLQ 미설정" → DLQ configured: `album-sync-dlq`, `maxReceiveCount=3`, 14-day retention, alarmed) and reconcile the FIFO `MessageGroupId`/`MessageDeduplicationId` description at `:59` with the "Standard queue" declaration at `:6` (the producer's FIFO branch is dead in prod — note it, don't imply ordering/dedup guarantees that don't exist).

**Verification:** the doc no longer claims an unconfigured DLQ and no longer implies FIFO semantics on a standard queue.
**Rollback:** `git revert`.

## Open questions

1. **Banner vs. full rewrite of `architecture.md`** — minimal targeted corrections + a drift banner (cheaper, matches `reference-architecture-md-unreliable`'s "don't trust it" posture) vs. a fuller rewrite. Default = **targeted fixes + banner**. *(Blocks Step 2 scope.)*

## Decisions log

| Date | Decision | Step |
|------|----------|------|
| 2026-06-05 | Spawned from STAB-1 §Sequencing item 4. **Doc-only**; prod is source of truth, docs brought to match. | all |
| 2026-06-05 | **Backfill source = prod introspection**, not migrations (V7 `library_items` ghost) and not `_generated_schema.sql` (omits bootstrap + `library_items`). Confirmed `library_items`/`library_item_status` absent in prod. | Step 1 |
| 2026-06-05 | `genres` absent → ledger ≤ V12, V13 free (also relevant to FEAT-genre-taxonomy). | §Evidence |
