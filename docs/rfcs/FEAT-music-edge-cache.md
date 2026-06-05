# FEAT-music-edge-cache: Cache the music read path (search, album detail, covers)

- **Status**: in-progress — **code-complete** (all 5 steps merged 2026-06-05); the
  only remaining action is the **human `terraform apply` of Step 2** (CloudFront
  edge cache). Steps 1, 3, 4, 5 are live in prod; Step 2 `.tf` is merged but not
  applied (prod `x-cache: Miss` confirms the edge isn't caching yet).
- **Owner**: 주인장
- **Created**: 2026-06-05
- **Plan row**: `plan.md` → FEAT-music-edge-cache

---

## Goal

The browser-facing music read path — unified search, album detail, and album cover
images — is served from cache instead of a fresh `API Gateway → music Lambda → Neon`
round-trip on every request. After this RFC: GET `/api/music/search/*` and
`/api/music/albums/*` responses carry `Cache-Control` and are cached at the
CloudFront edge **and** in the browser; the search box and album-detail panel reuse
in-session results without refetching; album covers load lazily from Spotify's CDN
with the browser caching them. **No always-on cache infrastructure is added** — every
layer here has $0 marginal cost (CloudFront is already deployed; browser and
in-process caches are free). Staleness is bounded by TTL only (minutes), which the
owner has accepted; there is no active invalidation.

## Non-goals

- **No external cache store.** ElastiCache (Redis/Memcached ~$91/mo, Valkey ~$6/mo
  floor), API Gateway response cache (REST-only — this system is HTTP API — and
  $14.6/mo+ always-on), and a self-run Redis are all rejected on the cost-first
  priority. Momento (serverless, 5 GB/mo free) is noted as a *future* option if
  traffic outgrows the CDN, but is **out of scope here**.
- **No active cache invalidation.** Owner accepted "수 분 지연 OK"; worker album syncs
  surface via natural TTL expiry. No event-driven purge, no CloudFront invalidation
  calls on write.
- **No re-hosting / proxying of album cover images.** `cover_url` is a Spotify
  `i.scdn.co` URL; re-hosting would violate Spotify terms and add egress cost +
  overhead for zero gain (Spotify's CDN + browser cache already cover it). We only
  improve how the `<img>` is loaded.
- **No caching of mutating routes** (`POST/PUT/DELETE /api/*`, `/api/publish`) and
  **no change to the front static path** — Astro SSG + S3 + CloudFront
  `CachingOptimized` is already optimal.
- **No caching of authenticated/per-user responses.** The music read endpoints are
  public; the cache key must not include `Authorization`/`Cookie`, and these
  endpoints carry no per-user data.

## Current state

**Front static** — already optimal: `output: 'static'` (`myblog_front/astro.config.ts`),
posts/categories baked at build via `getCollection('blog')`; served from S3 behind
CloudFront default behavior with managed `CachingOptimized`
(`infra/cloudfront.tf:60-73`). Out of scope.

**CloudFront** (`infra/cloudfront.tf`):
- Default behavior → S3, `CachingOptimized` (`:66`).
- Single ordered behavior `path_pattern = "/api/*"` → API Gateway origin with managed
  **`CachingDisabled`** (`:83`) + `AllViewerExceptHostHeader` origin request policy
  (`:84`). **Every `/api/*` request bypasses the edge cache**, forwards all headers +
  query strings, and hits origin. TTL = 0.

**API Gateway** (`infra/apigateway.tf`): HTTP API (`apigatewayv2`), no response
caching (HTTP APIs do not support it). `ANY /api/music/*` → music Lambda.

**Music read endpoints** (`myblog_music`):
- `GET /api/music/search/unified` — `app/api/routers/search.py:20`; calls
  `DBSearchService(db).unified_search()`. **No `Cache-Control` / `ETag`. No
  in-process cache.** Fresh Neon query every request.
- `GET /api/music/albums/{album_id}` — `app/api/routers/albums.py:9`;
  `AlbumService(db).get_album_detail()`. Also `GET /api/music/albums/by-spotify/{id}`
  (`:14`). **No cache headers.** Stable, idempotent, finite ID set, near-immutable —
  the strongest edge-cache candidate.
- `GET /api/music/artists/{id}/albums` — `app/api/routers/artists.py:18`. Same: no
  cache headers.
- The only in-process caches today are `lru_cache(maxsize=1)` on JWKS
  (`app/core/auth.py:19`) and settings — neither caches data.

**Front runtime fetches** (`myblog_front`):
- `src/scripts/searchBarDb.client.ts:281` — `fetch(${API_BASE}/api/music/search/unified?q=…)`
  on user input. **No client cache** — every keystroke (post-debounce) is a network
  round-trip; backspace/retype refetches identical queries. Maps `cover_url` to thumb
  `img` (`:180, :191, :207, :240, :256`).
- `src/scripts/albumDetail.fetch.client.ts:43` — `fetch(${base}/api/music/albums/{id})`
  on panel open. **No client cache** — reopening the same album refetches.
- `GET /api/categories.json` already sets `Cache-Control: public, max-age=300`
  (`src/pages/api/categories.json.ts:18`) — the one existing HTTP cache header; the
  pattern to mirror.

**Album cover images**: `cover_url` is a Spotify `i.scdn.co` URL stored in
`myblog_shared_db` (`models.py:179`, column `cover_url TEXT`). Rendered with
`loading="lazy"` already in `review-grid.astro:47` and `best-new-music.astro:49`, but
the **search dropdown thumbs** (`searchBarDb.client.ts`, DOM built in JS) and the
**album-detail `AlbumArt`** (`AlbumDetail.tsx:90`) have no explicit lazy/async-decoding
or intrinsic dimensions.

## Target state

- A custom CloudFront cache policy keys on the music query params and applies a short
  TTL; new ordered behaviors for `/api/music/albums/*`, `/api/music/search/*`, and
  `/api/music/artists/*` sit **above** the `/api/*` catch-all and honor origin
  `Cache-Control`. Mutating routes are unaffected (cached methods = GET/HEAD only).
- The three GET music read endpoints emit
  `Cache-Control: public, max-age=<n>, stale-while-revalidate=<m>` (album detail
  longer than search; SWR benefits the browser — CloudFront ignores SWR but honors
  `max-age`). Browser caches even before the edge behavior ships.
- The search box keeps an in-session `query → results` cache (in-memory Map +
  `sessionStorage`); album detail keeps an `albumId → detail` cache. Repeated /
  backspaced searches and reopened albums resolve with no network call.
- Search-dropdown thumbs and `AlbumArt` load with `loading="lazy"` +
  `decoding="async"` + intrinsic `width`/`height` (no layout shift), served straight
  from Spotify's CDN and browser-cached.
- A bounded `cachetools.TTLCache` in the music Lambda shields Neon on the cache-miss
  path for warm containers (in scope — see Step 5).

## Steps

Steps 1–5 are each independently mergeable. Suggested order is 1 → 2 (headers before
edge, though either works alone) then 3, 4 (front, independent), 5 last. All five are
in scope (Step 5 confirmed in, not deferred — Decisions log 2026-06-05). No contract
change in any step (HTTP response headers are not part of the OpenAPI schema) → no
`openapi.json` regen.

### Step 1 — `Cache-Control` headers on music read endpoints (music repo)

Add explicit cache headers to the three GET endpoints (`search/unified`,
`albums/{id}` + `albums/by-spotify/{id}`, `artists/{id}/albums`). Either set
`response.headers["Cache-Control"]` per route or a small response-header dependency /
middleware scoped to these GETs. Proposed values (see OQ1):
- album detail / artist albums: `public, max-age=300, stale-while-revalidate=120`
- search: `public, max-age=60, stale-while-revalidate=60`

This alone turns on **browser** caching immediately, no infra. Must NOT apply to
mutating routes or auth-gated endpoints.

> ✅ Done 2026-06-05, music #39 (`8807eea`). `app/core/cache.py` constants applied
> to the 7 GET endpoints; `tests/test_cache_control.py` (5 cases) asserts 200-sets /
> 400+by-spotify-404-uncached. CI `pytest -m "not integration"`: 45 passed.
> Audit finding: `/search/candidates` (auth + SQS) deliberately left untouched.
> **Prod smoke ✅**: `search/unified` → `public, max-age=60, stale-while-revalidate=60`;
> album detail → `public, max-age=300, stale-while-revalidate=120` (GET; HEAD 405 is
> expected, routes are GET-only).

**Verification**:
```
# music repo: header-assertion pytest (TestClient)
cd myblog_music && pytest -q -k "cache_control"
# post-merge prod:
curl -sI "https://<prod>/api/music/albums/<known-id>" | grep -i cache-control
curl -sI "https://<prod>/api/music/search/unified?q=radiohead&type=album" | grep -i cache-control
```

**Rollback**: trivial — remove the header line(s) / revert PR.

---

### Step 2 — CloudFront edge cache for music read paths (infra)

In `infra/cloudfront.tf`:
1. Add an `aws_cloudfront_cache_policy` (custom): cache key includes **all** query
   strings (`q, type, limit, offset, album_offset, …, explain`) — `explain=1` simply
   lands in a separate cache entry, no bypass, no pollution (Decisions log
   2026-06-05); **no** cookies; **no** `Authorization` header; `min_ttl = 0`,
   `default_ttl = 60`, `max_ttl = 300`; gzip + brotli on. Honoring origin
   `Cache-Control` lets Step 1's per-endpoint `max-age` drive the actual TTL within
   these bounds.
2. Add `ordered_cache_behavior` blocks for `/api/music/albums/*`,
   `/api/music/search/*`, `/api/music/artists/*` → API Gateway origin, custom cache
   policy above, `cached_methods = [GET, HEAD]`, `allowed_methods` = full set
   (POST/etc. pass through uncached), keep the `AllViewerExceptHostHeader` origin
   request policy so the `X-Origin-Verify` origin custom header still reaches the
   Lambda. **These blocks must be ordered before the existing `/api/*` block** (more
   specific patterns first).

Full `terraform plan` (no `-target`, hard rule #6); stop on any unexpected drift
(`viewer_certificate` drift is already suppressed, `cloudfront.tf:101-103`).
Reminder (memory): merging the infra PR ≠ prod change — a human runs `terraform apply`
locally; there is no infra auto-apply.

> ✅ Code merged 2026-06-05, workspace #246 (`ad1536d`). Final scope (audit
> refinements): search behavior is `/api/music/search/unified` **exact** (not
> `/search/*` — excludes auth-gated `/search/candidates`); `/albums/*` + `/artists/*`;
> by-spotify 404s kept uncached via `custom_error_response { 404, min_ttl=0 }`.
> `terraform validate` ok; full `terraform plan` = **1 to add (cache policy) + 1
> in-place (distribution), 0 destroy**, no unexpected drift.
> ⏳ **Pending the human `terraform apply`** — edge caching is NOT live until then
> (prod `x-cache: Miss`). Post-apply: 2nd hit on an album path → `Hit from cloudfront`.

**Verification**:
```
cd infra && terraform plan        # only the new cache policy + 3 behaviors appear
# post-apply prod (2nd hit should be a HIT):
curl -sI "https://<prod>/api/music/albums/<id>" | grep -i x-cache   # Miss…
curl -sI "https://<prod>/api/music/albums/<id>" | grep -i x-cache   # Hit from cloudfront
```

**Rollback**: remove the behaviors + policy, `terraform apply` (human). Non-trivial:
CloudFront config propagation takes minutes; plan the revert window.

---

### Step 3 — In-session client cache for search + album detail (front)

`searchBarDb.client.ts`: add a `Map<string, Result>` (normalized query key:
`q|type|limit|offset`) backed by `sessionStorage`, checked before `fetch`; confirm the
input debounce is present and tuned. `albumDetail.fetch.client.ts`: cache by
`albumId`. Cache is per-session, TTL-less (page reload clears) — bounded by tab
lifetime, so staleness ≤ session and well within the "minutes OK" budget.

> ✅ Done 2026-06-05, front #92 (`b74fb5f`). Implemented as `src/lib/sessionCache.ts`
> (`cached(url, ttlMs, producer)`, in-memory Map + sessionStorage) — TTLs mirror the
> server `max-age` (search 60s, detail 300s) rather than TTL-less, and the key is the
> full URL. **Success-only**: a thrown fetch (incl. by-spotify absorb 404) is never
> cached, so the writer retry still re-fetches. Search is submit/Enter-triggered (no
> debounce needed). `/search/candidates` stays uncached. Lint + astro check clean;
> throwaway `tsx` behavioral check of `cached()` (hit/miss/throw-uncached/expiry) all
> pass; front deploy succeeded (prod live).

**Verification**:
```
cd myblog_front && pnpm lint && pnpm exec astro check
# browser click-through (DoD: UI change): search a term, backspace, retype →
# Network tab shows the repeat resolves with no new request; reopen same album → no refetch.
```

**Rollback**: trivial — revert PR.

---

### Step 4 — Album cover image loading polish (front)

Search-dropdown thumbs (`searchBarDb.client.ts` DOM build) and `AlbumArt`
(`AlbumDetail.tsx:90`): add `loading="lazy"`, `decoding="async"`, and intrinsic
`width`/`height` (prevents layout shift). Images stay sourced from Spotify
`i.scdn.co` (already aggressively CDN- + browser-cached); **no proxy, no re-host**
(Non-goals). Sweep other cover renders for parity with the existing
`review-grid.astro:47` / `best-new-music.astro:49` pattern.

> ✅ Done 2026-06-05, front #93 (`7e4d7d6`). `makeCard.ts` thumbs set
> `loading=lazy` + `decoding=async` (before `src`) + intrinsic 1:1 dims (`.art`
> already reserves space via `aspect-ratio`, so no CLS). `decoding=async` added to
> the already-lazy covers in `AlbumArt` (ui.tsx), best-new-music, review-grid,
> AddAlbumModal, ReviewsIndex. **Excluded** hero/LCP images (`hero-review`,
> `review-hero`) and writer drill-in art — lazy would hurt their LCP. Lint + astro
> check clean; front deploy succeeded (prod live).

**Verification**:
```
cd myblog_front && pnpm lint && pnpm exec astro check
# browser: covers lazy-load on scroll; no CLS on dropdown open; repeat opens hit browser cache (304/from-cache).
```

**Rollback**: trivial — revert PR.

---

### Step 5 — Lambda in-process TTLCache for DB protection (music repo)

Wrap `unified_search()` (and optionally `get_album_detail`) with a bounded
`cachetools.TTLCache` (e.g. `maxsize=256, ttl=60`), keyed on the normalized query
params. Shields Neon on the cache-miss path for warm containers. At personal/small
traffic the per-container hit rate is modest — this is burst insurance, not a primary
win — but confirmed in scope (Decisions log 2026-06-05). Add `cachetools` to
`myblog_music` deps. Ships last (after Steps 1–4 are live), so prod can show whether
the miss path actually needs it before tuning `ttl`/`maxsize`.

> ✅ Done 2026-06-05, music #40 (`c7a2748`). `unified_search` fronts
> `_compute_unified_search` with a module-level `TTLCache(maxsize=256, ttl=60)` keyed
> on the resolved arg tuple (`types=None` collapses to the full-set key; `explain`
> separate). `tests/conftest.py` autouse fixture clears it between tests (units reuse
> `q="MatchedAlbum"` against different mocked DBs); `tests/test_search_cache.py`
> (4 cases). CI `pytest -m "not integration"`: 49 passed. `cachetools>=5.3` added.
> Music deploy succeeded (prod live). Album detail caching left out (CDN covers it;
> revisit if the miss path shows volume).

**Verification**:
```
cd myblog_music && pytest -q tests/test_search_cache.py   # identical→compute once; distinct/explain→recompute
```

**Rollback**: trivial — revert PR; cache is in-memory only.

---

## Open questions

_All resolved at acceptance (2026-06-05) — see Decisions log. None blocking._

## Decisions log

| Date | Decision | Step |
|------|----------|------|
| 2026-06-05 | RFC **accepted** (owner). | — |
| 2026-06-05 | TTLs as proposed: album/artist `max-age=300`, search `max-age=60`; CloudFront `default_ttl=60 / max_ttl=300`. | 1, 2 |
| 2026-06-05 | Edge behaviors **include `/api/music/artists/*`** (alongside `albums` + `search`). | 2 |
| 2026-06-05 | Cache key includes **all** query strings; `?explain=1` lands in a separate entry — **no bypass** (simplest, no pollution). | 2 |
| 2026-06-05 | **Step 5 (Lambda TTLCache) is in scope**, not deferred; ships last so prod can inform `ttl`/`maxsize`. | 5 |
| 2026-06-05 | `stale-while-revalidate` kept for **browser-only** benefit; CloudFront honors `max-age` only — accepted, no Origin Shield / stale-if-error in this RFC. | 1 |
| 2026-06-05 | **Audit refinement:** edge search caching is `/api/music/search/unified` **exact**, NOT `/search/*` — the sibling `/search/candidates` is auth-gated + enqueues to SQS and must never be cached (would skip the enqueue + leak an authed response). | 2 |
| 2026-06-05 | **Audit refinement:** `/{albums,artists}/by-spotify/*` return 404 while the worker absorbs, and the writer polls that 404→200 (`myblog_front SubjectBlock.tsx`). Keep 404s uncached via distribution-level `custom_error_response { error_code=404, error_caching_min_ttl=0 }` rather than per-path CachingDisabled behaviors. Headers are 200-only (Step 1). | 2 |
| 2026-06-05 | **Apply is human** (no infra auto-apply; [[reference-workspace-no-infra-autoapply]]). Step 2 PR merge ships the `.tf` only — CloudFront caching is NOT live until a human runs `terraform apply`. `terraform plan`: 1 to add (cache policy) + 1 in-place (distribution), 0 destroy. | 2 |
| 2026-06-05 | **Code-complete.** All 5 steps merged (music #39/#40, infra #246, front #92/#93). Steps 1/3/4/5 deployed + live; Step 1 prod-smoked (headers confirmed). Only remaining action: human `terraform apply` of Step 2. RFC stays in-flight until applied, then → `done` + archive. | all |
