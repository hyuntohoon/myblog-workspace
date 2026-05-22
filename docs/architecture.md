# MyBlog + Music Review — System Architecture

## Overview

A personal blog combined with a music review feature. Blog authoring, music search and sync, and static site publishing are each owned by an independent service.

---

## Services

| Service | Responsibility | Deployment |
|---------|----------------|------------|
| `myblog_front` | Static site + admin authoring UI | S3 + CloudFront |
| `myblog_backend` | Blog post and category CRUD + auth | Lambda + API Gateway |
| `myblog_music` | DB-first music search + sync trigger | Lambda + API Gateway |
| `myblog_worker` | SQS consumer + Spotify sync | Lambda (SQS event source) |
| `myblog_publish` | Static site publishing pipeline | Lambda + API Gateway |

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
          ┌───────────────┼───────────────────┐
          │               │                   │
          ▼               ▼                   ▼
  GET /posts          GET /search/*      POST /publish
  POST /posts         (music search)     (publish trigger)
  /categories
          │               │                   │
          ▼               ▼                   ▼
  ┌───────────────┐ ┌────────────────┐ ┌──────────────────┐
  │ myblog_backend│ │ myblog_music   │ │ myblog_publish   │
  │ (Lambda)      │ │ (Lambda)       │ │ (Lambda)         │
  └───────┬───────┘ └───────┬────────┘ └────────┬─────────┘
          │                 │                    │
          ▼           ┌─────┴──────┐             ▼
         RDS      DB search    SQS enqueue   GitHub API
    (PostgreSQL)  (unified)    (candidates)      │
                      │            │             ▼
                      ▼            ▼        GitHub Actions
                    Spotify      SQS Queue  ├── Astro build
                    Web API          │      ├── S3 upload
                                     │      └── CF invalidation
                                     ▼
                             ┌───────────────┐
                             │ myblog_worker │
                             │ (Lambda)      │
                             └───────┬───────┘
                                     │
                          ┌──────────┴──────────┐
                          ▼                     ▼
                     Spotify API              RDS
                     (batch fetch)       (PostgreSQL)
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
| `myblog_backend` | Post and category CRUD |
| `myblog_music` | Unified music search / Spotify candidate search |
| `myblog_publish` | Publish trigger after post save |

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

**Design rationale** — Spotify outages must not affect post reads or writes. Keeping Cognito JWT validation inside this service narrows the auth surface area.

---

### myblog_music

Handles music search and Spotify sync triggers. The core design principle is **"search from DB; sync only when needed, asynchronously."**

**Two search paths**

```
[Basic search]  GET /search/unified
  → DB ILIKE query → return results (no Spotify call)

[Sync button]   GET /search/candidates
  → Spotify API search
  → ① return candidates immediately
  → ② batch-enqueue album IDs to SQS (up to 20 per message)
```

**Endpoints**

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/music/search/unified` | DB-first unified search |
| `GET` | `/api/music/search/candidates` | Spotify candidates + SQS enqueue |
| `GET` | `/api/music/albums/:id` | Album detail (DB-only) |
| `GET` | `/api/music/albums/by-spotify/:spotify_id` | Album lookup by Spotify ID (DB-only) |

---

### myblog_worker

Background service that consumes SQS messages and syncs Spotify data into the DB. Fully decoupled from the request-response path.

**Processing flow**

```
Receive SQS message (up to 20 album spotify_ids)
  → Spotify GET /albums?ids=... (batch call)
  → Artist / Album / Track upsert (idempotent on spotify_id)
  → Link album_artists and track_artists relations
  → Delete SQS message
```

**Key design points**

- **Batch processing** — groups of up to 20 reduce Spotify API calls to ⌈N/20⌉
- **Idempotency** — `INSERT ON CONFLICT UPDATE` keyed on `spotify_id`; safe to reprocess
- **Failure isolation** — worker delays or failures have no impact on user search UX; SQS handles retries

---

### myblog_publish

Publishing-only service that updates the static site after an admin saves a post.

**Publish flow**

```
Front → POST /publish
  → Create/commit MDX file via GitHub API
  → Triggers GitHub Actions workflow
      → Astro build → S3 upload → CloudFront invalidation
```

**Design rationale**

- "DB transaction (post save)" and "external integration (GitHub → S3 deploy)" have different failure modes and retry strategies — separation keeps each concern clean.
- GitHub API tokens exist only in this service; they are never exposed to Backend or Music APIs.

---

## Shared Infrastructure

| Infrastructure | Used by |
|----------------|---------|
| Amazon RDS (PostgreSQL) | `myblog_backend`, `myblog_music`, `myblog_worker` |
| Amazon SQS | `myblog_music` (enqueue), `myblog_worker` (consume) |
| AWS Cognito | `myblog_backend` (JWT validation), `myblog_front` (login) |
| S3 + CloudFront | `myblog_front` (static serving), `myblog_publish` (deploy target) |
| Spotify Web API | `myblog_music` (search), `myblog_worker` (data collection) |
| GitHub API / Actions | `myblog_publish` (MDX commits, build trigger) |

---

## Service Separation Rationale

| Reason | Services |
|--------|---------|
| Spotify failure isolation — blog core must not be affected by external API failures | `myblog_backend` vs `myblog_music` |
| Latency vs stability — short-timeout API Lambda vs long-timeout Worker Lambda | `myblog_music` vs `myblog_worker` |
| Transaction vs external integration — DB save and GitHub/S3 deploy have different failure units | `myblog_backend` vs `myblog_publish` |
| Security boundary — GitHub tokens in publish only; Cognito validation in backend only | `myblog_publish`, `myblog_backend` |
| CDN for read traffic — static site handles most reads without Lambda invocations | `myblog_front` |
