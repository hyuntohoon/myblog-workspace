# Contract & Feature Parity Audit — 2026-05-28

Cross-check of `myblog_front` API consumption against `myblog_backend` + `myblog_music` route surface, anchored on the merged contract `docs/contracts/openapi.json` (regenerated 2026-05-28).

## Scope

- Frontend: every `apiFetch` / direct `fetch` call in `myblog_front/src/`
- Backend: every FastAPI route in `myblog_backend/app/api/` + `myblog_music/app/api/`
- Contract: 14 paths currently published in `docs/contracts/openapi.json`

## Method

1. Parallel `explorer` subagents on each repo → route + caller inventories
2. Hand cross-check of suspected drifts against `docs/contracts/openapi.json`
3. Pydantic source inspection for any field-coverage doubt
4. AWS API Gateway routes (`infra/apigateway.tf`) sanity check

## Endpoint Parity Matrix

| Endpoint | Frontend caller | Backend handler | Contract | Drift |
| --- | --- | --- | --- | --- |
| `GET /health` | — | `backend/main.py:73` | ✅ | — |
| `GET /api/db/ping` | — | `backend/main.py:78` | ✅ | — |
| `GET /api/categories` | `write/api.ts:16` | `routes/categories.py:11` | ✅ | L-2 (loose typing) |
| `POST /api/categories` | `write/api.ts:26` | `routes/categories.py:18` | ✅ | — |
| `GET /api/posts?status=` | `drafts.astro:273` | `routes/posts.py:24` | ✅ | — |
| `POST /api/posts` | `write/api.ts:54` | `routes/posts.py:48` | ✅ | — |
| `GET /api/posts/{id}` | `write/api.ts:70` | `routes/posts.py:99` | ✅ | — |
| `PUT /api/posts/{id}` | `write/api.ts:62`, `WriterApp.tsx:203,244` | `routes/posts.py:124` | ✅ | **H-1 (data loss)** |
| `DELETE /api/posts/{id}` | `drafts.astro:245` | `routes/posts.py:139` | ✅ | — |
| `POST /api/publish` | `write/api.ts:118` | `routes/publish.py:33` | ✅ | — |
| `POST /api/metrics/batch` | `lib/api.ts:62` | `routes/metrics.py:8` | ✅ | M-3 (in-memory mock) |
| `GET /api/music/search?mode=` | dev pages only (`searchTest/`) | `music/routers/search.py:43` | ✅ | M-2 (legacy, prod-unused) |
| `GET /api/music/search/unified` | `SubjectBlock.tsx:58`, `searchBarDb.client.ts:176` | `music/routers/search.py:20` | ✅ | — |
| `GET /api/music/search/candidates` | `SubjectBlock.tsx:127`, others | `music/routers/search.py:59` | ⚠ schema `{}` | M-1 (untyped response) |
| `GET /api/music/albums/{id}` | `SubjectBlock.tsx:204`, `albumDetail.fetch.client.ts:41` | `music/routers/albums.py:9` | ✅ | L-1 (front hand-rolled type) |
| `GET /api/music/albums/by-spotify/{id}` | `SubjectBlock.tsx:203`, others | `music/routers/albums.py:14` | ✅ | — |
| `GET /api/music/artists/{id}/albums` | `searchBarDb.client.ts:309` | `music/routers/artists.py:12` | ✅ | — |
| `GET /api/music/artists/spotify/{id}/albums` | `searchBarSpotify.client.ts:265` | `music/routers/artists.py:23` | ✅ | — |

**No orphan endpoints** (every route in the contract has a caller, every caller hits an existing route).

## Findings (ranked by severity)

### H-1 — Editing a draft silently loses category / album / artist (HIGH)

**Where**

- Frontend: `myblog_front/src/components/writer/WriterApp.tsx:195-204` builds a payload that includes `category`, `album_ids`, `artist_ids` and submits it via `updatePost(id, payload)` (`scripts/write/api.ts:61`).
- Backend: `myblog_backend/app/api/schemas.py:69` `UpdatePostRequest` only declares `title`, `description`, `body_mdx`, `posted_date`, `status`, `rating`. Pydantic default `extra="ignore"` (no `model_config` set, unlike `WritePostRequest` at `schemas.py:18`) drops every other field before the handler ever sees it.
- Handler: `routes/posts.py:124` does `req.model_dump(exclude_unset=True)` → those fields are already gone, so `PostService.update` never receives them.

**Impact**
A user opens an existing draft, changes the category or swaps the album, hits "임시저장". The frontend reports success, the database keeps the original values. There is no UI warning because the request is 200 OK.

**Fix sketch**

- Add `category: Optional[str] = None`, `album_ids: Optional[List[str]] = None`, `artist_ids: Optional[List[str]] = None` to `UpdatePostRequest`.
- Extend `PostService.update` / `PostRepository.update` to handle these (M2M for album/artist requires the same path the create flow uses, not naive `setattr`).
- Pytest: round-trip POST → PUT(category change) → GET asserting persistence.
- Regenerate `myblog_backend/openapi.json`, re-merge to `docs/contracts/openapi.json`, regenerate frontend types.
- Prod smoke: extend `scripts/smoke.sh` with an update-category step.

Tracker row: **BUG-10**.

### M-1 — `/api/music/search/candidates` response is unschematised (MEDIUM)

**Where**

- `myblog_music/app/api/routers/search.py:59` returns `Dict[str, Any]`; OpenAPI schema is `{}`.
- Frontend `SubjectBlock.tsx:127` and `searchBarSpotify.client.ts:233` consume it via `any`.

**Impact**
No compile-time guard against field renames (e.g. if a Spotify field is renamed from `images[0].url` → `cover_url`, neither side detects it). Also blocks any future client wanting type safety.

**Fix sketch**

- Define `Music_CandidateSearchResult` (albums, artists, tracks each with their own model, plus `*_pagination` blocks).
- Wire as `response_model`. Re-merge contract. Regenerate front types. Replace `any` usages.

Tracker row: **PR-12** (contract hardening).

### M-2 — Legacy `/api/music/search?mode=` only used by dev pages (MEDIUM)

**Where**

- `myblog_music/app/api/routers/search.py:43` exposes `/api/music/search` (mode + q).
- Production import graph (`grep` on `src/pages/`, `src/components/`) → zero references; only `src/scripts/searchBar.client.ts` (loaded by `searchTest/` Astro dev pages).

**Impact**
Public Lambda route with no production consumer. Surface area we have to keep working without test coverage.

**Fix sketch (pick one)**

1. Delete the endpoint + dev pages, remove from contract. Simplest.
2. Gate it behind `ENV in {local, dev}` and remove from the published contract.

Tracker row: **CHORE / PR-13**.

### M-3 — `/api/metrics/batch` is mock-only (MEDIUM, not a contract issue)

**Where**
`routes/metrics.py:6` uses `InMemoryMetricsRepository`. The handler shape matches the contract, but values are synthetic.

**Impact**
Frontend displays fake like/comment counts on post pages. Affects credibility, not correctness — flagging so the plan can prioritise.

Tracker row: keep on backlog; not part of this cycle.

### L-1 — Hand-rolled `AlbumDetail` interface in frontend (LOW)

`myblog_front/src/scripts/review/index.ts:5` redefines `AlbumDetail` locally instead of importing `components['schemas']['Music_AlbumDetail']` from `lib/api.gen.ts`. Drift risk.

### L-2 — `fetchCategories` reads non-existent `json.items` fallback (LOW)

`myblog_front/src/scripts/write/api.ts:22` returns `json?.items || json?.categories || []`. Backend never sends `items`; the fallback is dead code that lets a wrong response shape slip through silently.

### L-3 — Loose typing across all `searchBar*.client.ts` mappers (LOW)

Every mapper uses `any` for the response — same drift risk as L-1 multiplied across three files.

## Non-findings (verified, OK)

- **`POST /api/posts` open auth** — intentional; CLAUDE.md confirms only `POST/PUT/DELETE /api/posts/*` go through the Cognito API Gateway, but `POST /api/posts` in the contract reflects the CloudFront direct path used by the editor with a Bearer token; FastAPI's `require_cognito_token` is enforced inside the handler chain for the mutating routes.
- **`album_cover_url` missing from `WritePostRequest`** — intentional; the field is comment-documented (`scripts/write/api.ts:7`) as a frontend-only metadata passthrough for the publish step.
- **`/api/posts/{post_id}` vs API Gateway `/api/posts/{id}`** — path parameter names differ but path templates match; AWS forwards regardless of placeholder name.

## Suggested PR rotation

| Order | Tracker | Repos touched | Notes |
| --- | --- | --- | --- |
| 1 | **BUG-10** | backend + workspace (contract) + front (regen types) | Fix H-1 first; ships with pytest + prod smoke. |
| 2 | **PR-12** | music + workspace + front | Type candidates response; trivial after BUG-10's contract-regen pipeline is freshly exercised. |
| 3 | **PR-13** | music + front + workspace | Decide delete vs gate for legacy `/api/music/search`. |
| 4 | **CHORE-N** | front only | L-1 / L-2 / L-3 hygiene; can be bundled. |

Each PR follows the standard flow in `CLAUDE.md` (branch → impl → local smoke → push, wait for "ok push" → squash → prod smoke → quote in PR comment → drop plan.md row).
