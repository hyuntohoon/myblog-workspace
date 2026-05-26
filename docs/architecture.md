# MyBlog + Music Review — System Architecture

## Overview

A personal blog combined with a music review feature. Blog authoring, music search and sync, and static site publishing are each owned by an independent service.

---

## Services

| Service | Responsibility | Lambda 함수명 | Deployment |
|---------|----------------|--------------|------------|
| `myblog_front` | Static site + admin authoring UI | — | S3 + CloudFront |
| `myblog_backend` | Blog post and category CRUD + auth | `ratemymusic-api` | Lambda + API Gateway (`lambdaAPI`) |
| `myblog_music` | DB-first music search + sync trigger | `musicApi` | Lambda + API Gateway (`lambdaAPI`) |
| `myblog_worker` | SQS consumer + Spotify sync | `blogWorkerLambda` | Lambda (SQS: `blogSQS`) |
| `myblog_publish` | Static site publishing pipeline | `publisher-github` | Lambda + API Gateway (`lambdaAPI`) |

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
        Neon      DB search    SQS enqueue   GitHub API
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
                     Spotify API             Neon
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

**Endpoints** (2026-05-26 기준 실제 라우트)

| Method | Path | Auth | Notes |
|--------|------|------|-------|
| `POST` | `/api/posts` | Cognito JWT | 작성·수정 (현재 단일 엔드포인트) |
| `GET` | `/api/categories` | None | 카테고리 목록 |
| `POST` | `/api/categories` | Cognito JWT | 카테고리 생성 |
| `POST` | `/api/metrics/batch` | None | 좋아요·댓글 수 배치 조회 |
| `GET` | `/health`, `/api/db/ping` | None | 헬스체크 |

**상태 (2026-05-26)** — `GET /api/posts*`, `PUT /api/posts/{id}`, `DELETE /api/posts/{id}` **미구현**. 프론트 `drafts.astro`가 호출하는 `GET /api/posts?status=draft`, `DELETE /api/posts/{id}`는 404로 깨져 있다. FEAT-POST-1(M1)에서 추가 예정. 자세한 격차는 `docs/plan.md` REVIEW-1 참조.

**리뷰 데이터의 정적·동적 이중 트랙**

- **정적 (공개 읽기)** — 발행 후 `myblog_publish`가 GitHub에 MDX 커밋 → Astro 빌드 → S3/CloudFront. 모든 공개 블로그 리스트·상세는 이 경로(정적 콘텐츠).
- **동적 (작성·임시저장·편집)** — 백엔드 `posts` 테이블. 작성 중인 글, 드래프트, 발행 메타데이터(rating, post_id) 보관. **현재 CRUD 미완성** (B1 격차).

**Design rationale** — Spotify outages must not affect post reads or writes. Keeping Cognito JWT validation inside this service narrows the auth surface area. 공개 읽기는 CDN으로 처리해 Lambda 호출 비용·지연을 줄인다.

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

**Endpoints** (2026-05-26 기준 실제 라우트)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/api/music/search/unified` | None | DB-only 통합 검색 (artists/albums/tracks) |
| `GET` | `/api/music/search/` | None | DB 기본 검색 |
| `GET` | `/api/music/search/candidates` | Cognito JWT | Spotify 후보 + SQS enqueue |
| `GET` | `/api/music/albums/{id}` | None | 앨범 상세 (DB-only) |
| `GET` | `/api/music/albums/by-spotify/{spotify_album_id}` | None | Spotify ID로 앨범 상세 (DB-only) |
| `GET` | `/api/music/artists/{artist_id}/albums` | None | 아티스트 디스코그라피 |
| `GET` | `/api/music/artists/spotify/{spotify_id}/albums` | None | Spotify ID로 디스코그라피 |

**아티스트 상세 (`GET /api/music/artists/{id}`)는 미구현** — 디스코그라피 엔드포인트만 존재. FEAT-ARTIST-1(M2)에서 추가 예정 (이름·aliases·photo_url 메타 포함).

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

| Infrastructure | Used by | Notes |
|----------------|---------|-------|
| **Neon PostgreSQL** (ap-southeast-1) | `myblog_backend`, `myblog_music`, `myblog_worker` | Serverless Postgres; connection via pooler URL |
| Amazon SQS (`blogSQS`) | `myblog_music` (enqueue), `myblog_worker` (consume) | Standard queue, ap-northeast-2 |
| AWS Cognito (`MyBlogAdminPool`) | `myblog_backend` (JWT validation), `myblog_front` (login) | Pool ID: ap-northeast-2_54vEJKEU5 |
| S3 (`myblog-prod-web`) + CloudFront | `myblog_front` (static serving), `myblog_publish` (deploy target) | CF: d2y4n52sgjlrz6.cloudfront.net |
| Spotify Web API | `myblog_music` (search), `myblog_worker` (data collection) | |
| GitHub API / Actions | `myblog_publish` (MDX commits, build trigger) | |

---

## Service Separation Rationale

| Reason | Services |
|--------|---------|
| Spotify failure isolation — blog core must not be affected by external API failures | `myblog_backend` vs `myblog_music` |
| Latency vs stability — short-timeout API Lambda vs long-timeout Worker Lambda | `myblog_music` vs `myblog_worker` |
| Transaction vs external integration — DB save and GitHub/S3 deploy have different failure units | `myblog_backend` vs `myblog_publish` |
| Security boundary — GitHub tokens in publish only; Cognito validation in backend only | `myblog_publish`, `myblog_backend` |
| CDN for read traffic — static site handles most reads without Lambda invocations | `myblog_front` |
