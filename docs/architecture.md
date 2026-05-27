# MyBlog + Music Review — System Architecture

## Overview

A personal blog combined with a music review feature. Blog authoring, music search and sync, and static site publishing are each owned by an independent service.

> Concrete resource IDs (pool IDs, distribution IDs, ARNs, queue URLs) live in `docs/infrastructure.md`, not here. This document describes intent and structure; that one describes what currently exists.

---

## Services

| Service | Responsibility | Lambda function | Deployment |
|---------|----------------|-----------------|------------|
| `myblog_front` | Static site + admin authoring UI | — | S3 + CloudFront |
| `myblog_backend` | Blog post and category CRUD + auth + publishing | `ratemymusic-api` | Lambda + API Gateway |
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
  /categories
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
| `myblog_backend` | Post and category CRUD + publish trigger |
| `myblog_music` | Unified music search / Spotify candidate search |

Type contract with backend is generated from `docs/contracts/openapi-backend.json` via `pnpm generate:types`. `PostPayload` is derived from `WritePostRequest`; do not hand-edit.

---

### myblog_backend

Core blog API. Owns the post and category domain and is fully isolated from music sync.

**Endpoints**

| Method | Path | Auth |
|--------|------|------|
| `GET` | `/posts`, `/posts/:id` | None |
| `POST` | `/posts` | Cognito JWT |
| `PUT` | `/posts/:id` | Cognito JWT |
| `GET` | `/categories` | None |
| `POST` | `/categories` | Cognito JWT |
| `POST` | `/api/publish` | Cognito JWT |

**Publishing subsystem** — `POST /api/publish` receives the post payload, generates an MDX file, and commits it to the blog content repo via the GitHub API. GitHub Actions picks it up from there (Astro build → S3 → CloudFront). `GITHUB_TOKEN` is loaded from `myblog/backend` Secrets Manager at cold start.

**Design rationale** — Spotify outages must not affect post reads or writes. Keeping Cognito JWT validation inside this service narrows the auth surface area. Publishing absorbed from `myblog_publish` (ARCH-11) — auth is now Cognito JWT rather than edge secret, which is strictly stronger.

---

### myblog_music

Handles music search and Spotify sync triggers. The core design principle is **"search from DB; sync only when needed, asynchronously."**

**Two search paths**

```
[Basic search]  GET /search/unified
  → DB ILIKE query → return results (no Spotify call — hard rule)

[Sync button]   GET /search/candidates
  → Cognito JWT required
  → Spotify API search
  → ① return candidates immediately
  → ② batch-enqueue album IDs to SQS (up to 20 per message)
```

**Endpoints**

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/api/music/search/unified` | None | DB-first unified search |
| `GET` | `/api/music/search/candidates` | Cognito JWT | Spotify candidates + SQS enqueue |
| `GET` | `/api/music/albums/:id` | None | Album detail (DB-only) |
| `GET` | `/api/music/albums/by-spotify/:spotify_id` | None | Album lookup by Spotify ID (DB-only) |

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
EventBridge rate(15 min) → worker (alias mode)
  → SELECT artists missing aliases LIMIT 10
  → Gemini generate → UPDATE artists.aliases
```

Separated from the SQS path so Gemini latency cannot block album sync, and so a Gemini outage cannot fail SQS messages.

**Key design points**

- **Batch processing** — groups of up to 20 reduce Spotify API calls to ⌈N/20⌉
- **Idempotency** — `INSERT ON CONFLICT DO UPDATE` keyed on `spotify_id`; safe to reprocess. The upsert updates `ext_refs` (ARCH-1) so Spotify URL changes persist.
- **Failure isolation** — worker delays or failures have no impact on user search UX; SQS handles retries with `ReportBatchItemFailures`.

---


## Shared Infrastructure

Concrete IDs/ARNs in `docs/infrastructure.md`.

| Infrastructure | Used by | Notes |
|----------------|---------|-------|
| **Neon PostgreSQL** | `myblog_backend`, `myblog_music`, `myblog_worker` | Serverless Postgres; connection via pooler URL. Not AWS RDS. |
| **Amazon SQS** | `myblog_music` (enqueue), `myblog_worker` (consume) | Standard queue with DLQ + `ReportBatchItemFailures` |
| **AWS Cognito** | `myblog_backend` and `myblog_music` (JWT validation), `myblog_front` (login) | JWKS-based validation; bypassed when `COGNITO_USER_POOL_ID` unset (dev) |
| **AWS Secrets Manager** | All four Lambdas | One secret per service, loaded once per cold start via `@lru_cache` |
| **AWS EventBridge** | `myblog_worker` (alias generation schedule) | `rate(15 min)` |
| **S3 + CloudFront** | `myblog_front` (static serving) | CloudFront function rewrites `uri` → `uri + '/index.html'` for Astro directory format |
| **Spotify Web API** | `myblog_music` (search), `myblog_worker` (data collection) | Two separate clients by design — see ADR 0004 |
| **GitHub API / Actions** | `myblog_backend` (MDX commits via `/api/publish`, build trigger) | `GITHUB_TOKEN` in `myblog/backend` secret (ARCH-11) |

---

## Schema Contract

Canonical DDL: `docs/contracts/schema.sql` (ARCH-1, ADR 0003).

SQLAlchemy models are owned by `myblog_shared_db` (ARCH-6, ADR 0005) — a private Python package installed via git URL pin:
```
myblog-shared-db @ git+https://github.com/hyuntohoon/myblog_shared_db.git@v0.1.0
```

Three services import from it:
- `myblog_backend` — `from myblog_shared_db.models import Post, Category, Album, …`
- `myblog_music` — `from myblog_shared_db.models import Album, Artist, Track, …`
- `myblog_worker` — imports `myblog_shared_db.tables` Core Table objects; uses raw SQL for bulk upserts

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
