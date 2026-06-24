# MyBlog + Music Review — System Architecture

> ⚠️ **Verify against code — this doc drifts.** The 2026-06-05 review (STAB-1) found ≥4 load-bearing errors here; the ones found were corrected (2026-06-05, STAB-4), but treat any specific claim (pins, queue type, auth, imports) as needing a code/tfstate check before relying on it. Source of truth: `docs/contracts/schema.sql` (current through V15) + `infra/`.

## Overview

A personal blog combined with a music review feature. Blog authoring, music search and sync, and static site publishing are each owned by an independent service.

> Concrete resource IDs (pool IDs, distribution IDs, ARNs, queue URLs) live in `infra/README.md`, not here. This document describes intent and structure; that one describes what currently exists.

---

## Services

| Service | Responsibility | Lambda function | Deployment |
|---------|----------------|-----------------|------------|
| `myblog_front` | Static site + admin authoring UI | — | S3 + CloudFront |
| `myblog_backend` | Blog post and section CRUD + auth + publishing | `ratemymusic-api` | Lambda + API Gateway |
| `myblog_music` | DB-first music search + sync trigger | `musicApi` | Lambda + API Gateway |
| `myblog_worker` | SQS consumer + Spotify sync + scheduled alias generation | `blogWorkerLambda` | Lambda (SQS + EventBridge) |

All AWS resources are managed by Terraform in `infra/` (IAC-1, 2026-05-25). The four service repos no longer carry SAM templates; CI deploys Lambda code only via `aws lambda update-function-code`.

---

## System Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                        User / Admin                             │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTPS
                             ▼
               ┌─────────────────────────┐
               │   CloudFront + S3       │  ← GitHub Actions builds & deploys
               │   (Astro static site)   │
               │   myblog_front          │
               └──────────┬──────────────┘
                          │
          ┌───────────────┬───────────────────┐
          │               │                   │
          ▼               ▼                   ▼
  GET /posts          GET /search/*      POST /publish
  POST /posts         (music search)     (publish trigger)
  /sections
          │               │                   │
          └───────────────┤                   │
                          ▼                   │
  ┌───────────────────────────────┐           │
  │       myblog_backend          │ ◄─────────┘
  │       (Lambda)                │
  └───────┬─────────────┬─────────┘
          │             │
          ▼             ▼
        Neon        GitHub API
   (Serverless          │
    PostgreSQL)         ▼
                  GitHub Actions
                  ├── Astro build
                  ├── S3 upload
                  └── CF invalidation

  ┌────────────────┐
  │ myblog_music   │ ← GET /search/*, /api/music/*
  │ (Lambda)       │
  └───────┬────────┘
    ┌─────┴──────┐
    ▼            ▼
DB search    SQS enqueue
(unified)    (candidates)
    │            │
    ▼            ▼
 Spotify      SQS Queue
 Web API          │
                  ▼
         ┌───────────────┐       EventBridge
         │ myblog_worker │ ◄──── rate(15 min)
         │ (Lambda)      │       (alias generation)
         └───────┬───────┘
                 │
      ┌──────────┴──────────┐
      ▼                     ▼
 Spotify API             Neon
 (batch fetch)        (PostgreSQL)
                         upsert
```

---

## Service Details

### myblog_front

Astro-based static site hosted on S3 and served through CloudFront. GitHub Actions automatically builds and deploys on push to `main`.

**Role separation**

- **Public users** — read blog posts and use the music search UI via CloudFront cache
- **Admins** — write posts, link albums, and trigger publishing after Cognito authentication

**APIs called**

| Target | Purpose |
|--------|---------|
| `myblog_backend` | Post and section CRUD + publish trigger |
| `myblog_music` | Unified music search / Spotify candidate search |

Type contract with backend and music is generated from `docs/contracts/openapi.json` (merged spec, ARCH-12) via `pnpm generate:types` → `src/lib/api.gen.ts`. `PostPayload` is derived from `Backend_WritePostRequest`; do not hand-edit. CI fails if the committed `api.gen.ts` drifts from the spec.

The merged spec is regenerated automatically: each service repo publishes its own `openapi.json`; on push-to-main a `repository_dispatch` notifies the workspace, which runs `scripts/merge_openapi.py` and opens an auto-PR (`chore: update merged OpenAPI spec`). Stale auto-PRs that were superseded by manual contract refreshes should be closed.

---

### myblog_backend

Core blog API. Owns the post and section domain and is fully isolated from music sync.

**Endpoints**

| Method | Path | Auth |
|--------|------|------|
| `GET` | `/api/posts`, `/api/posts/:id` | None |
| `POST` | `/api/posts` | Cognito JWT |
| `PUT` | `/api/posts/:id` | Cognito JWT |
| `PATCH` | `/api/posts/:id/restore` | Cognito JWT |
| `DELETE` | `/api/posts/:id` | Cognito JWT |
| `GET` | `/api/sections` | None |
| `POST` | `/api/publish` | Cognito JWT |
| `POST` | `/api/metrics/batch` | None |

`POST/PUT/PATCH/DELETE /api/posts/*` and `POST /api/publish` flow through the API Gateway Cognito authorizer (`6eia7l`); other routes go through CloudFront with the `x-origin-verify` edge guard (CLAUDE.md "Auth — two entry points").

**Publishing subsystem** — `POST /api/publish` receives the post payload, generates an MDX file, and commits it to the blog content repo via the GitHub API. GitHub Actions picks it up from there (Astro build → S3 → CloudFront). `GITHUB_TOKEN` is loaded from `/myblog/backend` (SSM Parameter Store SecureString) at cold start.

**Metrics subsystem** — `POST /api/metrics/batch` returns like/comment counters for blog posts. Backed by `SqlMetricsRepository`, which reads `likes` / `comments_count` from `post_metrics` joined on `posts.slug` (PR-metrics-real, 2026-05-28). `InMemoryMetricsRepository` is retained as a test/local fallback; `app/di.py` wires the SQL implementation by default.

**Design rationale** — Spotify outages must not affect post reads or writes. Keeping Cognito JWT validation inside this service narrows the auth surface area. Publishing absorbed from `myblog_publish` (ARCH-11) — auth is now Cognito JWT rather than edge secret, which is strictly stronger.

---

### myblog_music

Handles music search and Spotify sync triggers. The core design principle is **"search from DB; sync only when needed, asynchronously."**

**Two search paths**

```
[Basic search]  GET /search/unified
  → DB ILIKE query → return UnifiedSearchResult (no Spotify call — hard rule)

[Sync button]   GET /search/candidates
  → Cognito JWT required
  → Spotify API search
  → ① return CandidateSearchResult immediately (response_model_exclude_none=True
       — only requested types appear in the response)
  → ② batch-enqueue album IDs to SQS (up to 20 per message)
```

**Endpoints**

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/api/music/search/unified` | None | DB-first unified search (`UnifiedSearchResult`) |
| `GET` | `/api/music/search/candidates` | Cognito JWT | Spotify candidates + SQS enqueue (`CandidateSearchResult`, PR-12) |
| `GET` | `/api/music/albums/:id` | None | Album detail by DB UUID (`AlbumDetail`, DB-only) |
| `GET` | `/api/music/albums/by-spotify/:spotify_id` | None | Album lookup by Spotify ID (`AlbumDetail`, DB-only — returns 404 until worker syncs) |
| `GET` | `/api/music/artists/:artist_id` | None | Artist hero detail (followers, genres, popularity) |
| `GET` | `/api/music/artists/:artist_id/albums` | None | Album list for a DB artist (`SearchResult`) |
| `GET` | `/api/music/artists/:artist_id/top-tracks` | None | Top tracks for a DB artist |

The legacy `GET /api/music/search?mode=` (`basic_search`) was removed in PR-13 (2026-05-28) along with its only caller; the legacy `GET /api/music/artists/spotify/:spotify_id/albums` was removed shortly after in CHORE-search-orphans for the same reason. Both moves are reversible from git history.

---

### myblog_worker

Background service. Two trigger paths:

**1. SQS-driven Spotify sync** (primary)

```
Receive SQS message (up to 20 album spotify_ids)
  → Spotify GET /albums?ids=... (batch call)
  → Artist / Album / Track upsert (idempotent on spotify_id)
  → Link album_artists and track_artists relations
  → SQS deletes message on Lambda success; failures re-raise → DLQ
```

**2. EventBridge-scheduled alias generation** (decoupled from sync)

```
EventBridge rate(15 minutes) → worker (event['source'] == 'aws.events')
  → generate_and_save_aliases:
      MusicBrainz lookup for artists with musicbrainz_id IS NULL (LIMIT 10/tick)
        → UPDATE artists.musicbrainz_id + aliases (or MBID_NOT_FOUND sentinel)
```

Separated from the SQS path so MusicBrainz latency cannot block album sync, and so an outage in MusicBrainz cannot fail SQS messages. The MBID_NOT_FOUND sentinel prevents repeat lookups for artists MusicBrainz doesn't know about. (A Gemini fallback was originally planned but is **not implemented** — non-English artists without an MBID match currently keep an empty `aliases` array; alias coverage improvement is tracked separately.)

**3. SQS job-control messages** (backend-enqueued — Spotify two-way sync, FEAT-spotify-library-sync)

```
{"job":"spotify_library_sync"}  (backend POST /api/buckets/spotify-library/sync → blogSQS)
  → worker mirrors the owner's Spotify saved-albums Library (GET/PUT/DELETE /me/albums)
  → diff bucket intent vs Library; writes gated on SPOTIFY_LIBRARY_WRITES_ENABLED
  → spotify_library_albums (V15) side-table = per-album provenance (source) + sync state
{"job":"spotify_refresh"}  (backend POST /api/library/refresh-recent → blogSQS)
  → worker re-pulls recently-played into spotify_recent_tracks (V14)
```

Per **hard rule #9** the user-facing endpoint only **enqueues** (202 Accepted); the worker does all Spotify I/O. `source` is immutable, so a pre-existing saved album is never removed on bucket-remove (req 5). Detail: `docs/contracts/sqs-album-sync.md` Format C + `docs/rfcs/FEAT-spotify-library-sync.md`.

**Key design points**

- **Batch processing** — groups of up to 20 reduce Spotify API calls to ⌈N/20⌉
- **Idempotency** — `INSERT ON CONFLICT DO UPDATE` keyed on `spotify_id`; safe to reprocess. The upsert updates `ext_refs` (ARCH-1) so Spotify URL changes persist.
- **Failure isolation** — worker delays or failures have no impact on user search UX; SQS handles retries with `ReportBatchItemFailures`.

---


## Shared Infrastructure

Concrete IDs/ARNs in `infra/README.md`.

| Infrastructure | Used by | Notes |
|----------------|---------|-------|
| **Neon PostgreSQL** | `myblog_backend`, `myblog_music`, `myblog_worker` | Serverless Postgres; connection via pooler URL. Not AWS RDS. |
| **Amazon SQS** | `myblog_music` + `myblog_backend` (enqueue), `myblog_worker` (consume) | **Standard** queue `blogSQS` (NOT FIFO; tfstate `fifo=False`) with DLQ `album-sync-dlq` (`maxReceiveCount=3`) + `ReportBatchItemFailures`; at-least-once + idempotent consumer. Carries album-sync (music) + `{job:...}` control messages (backend) |
| **AWS Cognito** | `myblog_backend` and `myblog_music` (JWT validation), `myblog_front` (login) | JWKS-based validation; bypassed when `ENV=local\|dev` or `COGNITO_USER_POOL_ID` unset |
| **AWS SSM Parameter Store (SecureString)** | All four Lambdas | One param per service, loaded once per cold start via `@lru_cache` |
| **AWS EventBridge** | `myblog_worker` (alias generation schedule) | `rate(15 minutes)` — triggers `generate_and_save_aliases` (MusicBrainz only) |
| **S3 + CloudFront** | `myblog_front` (static serving) | CloudFront function rewrites `uri` → `uri + '/index.html'` for Astro directory format |
| **Spotify Web API** | `myblog_music` (search), `myblog_worker` (data collection) | Two separate clients by design — see ADR 0004 |
| **MusicBrainz API** | `myblog_worker` (alias generation) | Looks up `musicbrainz_id` + aliases for artists; sentinel `MBID_NOT_FOUND` prevents repeat lookups. Score threshold 90 + 1 req/sec rate limit |
| **GitHub API / Actions** | `myblog_backend` (MDX commits via `/api/publish`, build trigger) | `GITHUB_TOKEN` in `/myblog/backend` SSM param (ARCH-11; moved SM→SSM per CHORE-secrets-ssm-migration) |

---

## Schema Contract

Canonical DDL: `docs/contracts/schema.sql` (ARCH-1, ADR 0003).

SQLAlchemy models are owned by `myblog_shared_db` (ARCH-6, ADR 0005) — a private Python package installed via git URL pin. Each consumer pins its own version (different services may lag the latest tag if they don't need the newest columns):
```
# myblog_backend/requirements.txt
myblog-shared-db @ git+https://github.com/hyuntohoon/myblog_shared_db.git@v0.15.0   # latest tag v0.15.0
# myblog_music/requirements.txt
myblog-shared-db @ git+https://github.com/hyuntohoon/myblog_shared_db.git@v0.3.0
# myblog_worker/requirements.txt
myblog-shared-db @ git+https://github.com/hyuntohoon/myblog_shared_db.git@v0.2.2
```

Three services import from it:
- `myblog_backend` — `from myblog_shared_db.models import Post, Category, Album, …`
- `myblog_music` — `from myblog_shared_db.models import Album, Artist, Track, …`
- `myblog_worker` — imports **nothing** from `myblog_shared_db` (grep = 0); all DB access is raw `text()` SQL with `ON CONFLICT` upserts. Its `@v0.2.2` pin is installed-but-unimported (dead)

Schema changes must:
1. Update `docs/contracts/schema.sql` first
2. Update `myblog_shared_db/models.py` and regenerate `_generated_schema.sql`
3. Tag a new version; update pin in each consumer's `requirements.txt`

---

## Service Separation Rationale

| Reason | Services |
|--------|---------|
| Spotify failure isolation — blog core must not be affected by external API failures | `myblog_backend` vs `myblog_music` |
| Latency vs stability — short-timeout API Lambda vs long-timeout Worker Lambda | `myblog_music` vs `myblog_worker` |
| CDN for read traffic — static site handles most reads without Lambda invocations | `myblog_front` |
| Sync path vs scheduled enrichment — alias generation latency and outages must not affect SQS sync | `myblog_worker` (SQS path vs EventBridge path) |
