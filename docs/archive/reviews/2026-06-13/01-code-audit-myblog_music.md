# Code Audit — myblog_music (2026-06-13)

DB-first music search service (FastAPI → Lambda `musicApi`). Routers → services →
repositories → mappers layering; `/api/music/search/unified` is DB-only, candidates
go Spotify → SQS → worker. Audited read-only. Convention hygiene is good: no
`print()`, no `os.getenv()` (all config via `settings`), `logging.getLogger(__name__)`
throughout, eager-loading (`selectinload`) on the detail/search paths, a typecheck
gate (`pyright app/`) and a `pytest -m "not integration"` gate in CI.

The two structural problems worth real attention are (1) a fan-out N+1 in the
unified-search expansion/decomposition hot path, and (2) accumulated dead code +
stale tests/docs that misrepresent the current SQS contract and routes. Everything
else is lower-stakes cleanup.

---

## Findings (severity-sorted)

### 1. [H] Unified-search expansion + decomposition fan out to O(limit) per-row DB queries
- **Category:** performance
- **Location:** `app/services/search_service.py:199-231` (expansion), `app/services/search_service.py:288-330` (`_decompose`)
- **Evidence:**
  ```python
  if "album" in wanted:
      for ar in literal_artists:
          exp_albums.extend(
              self.album_repo.list_by_artist_id_simple(ar.id, limit=ARTIST_ALBUMS_EXPANSION_CAP)
          )
  if "track" in wanted:
      for ar in literal_artists:
          exp_tracks.extend(
              self.track_repo.list_by_artist_id(ar.id, limit=ARTIST_TRACKS_EXPANSION_CAP)
          )
  ```
  `literal_artists` is bounded by `limit` (route allows `le=100`). With `type=album,artist,track`
  that's up to `2 * len(literal_artists)` queries just for artist→album and artist→track expansion
  (≈200 round-trips at limit=100). `_decompose` adds more: for a 2–3 token query it loops over up
  to `DECOMP_MAX_SPLITS=6` splits, each issuing one `search_by_name` plus one `search_by_title`
  per requested bucket (album+track) → up to ~24 extra queries. Each is a separate Neon round-trip.
- **Why it matters:** This is the single most-hit endpoint (CommandPalette autocomplete fires it on
  keystrokes). Neon is a remote managed PG with non-trivial latency per round-trip; serial fan-out
  multiplies that. Reference note `[reference-pg-trgm-gin-inert-small-catalog]` says single queries
  are ~3–11ms at current catalog size, so today the wall-clock cost is modest, but it scales with
  both `limit` and catalog growth, and there is no batching ceiling on the artist loop other than
  `limit`. The per-process TTL cache (`_unified_cache`, 60s) absorbs *repeats* but not the first
  (cold) query of each distinct keystroke prefix — exactly the autocomplete pattern.
- **fixDifficulty:** M
- **Proposal:** Batch the artist→album / artist→track expansion into one query each, keyed by
  `artist_id IN (...)` (mirror the already-bulk `list_by_album_ids`). Per-artist LIMIT can be kept
  with a `ROW_NUMBER() OVER (PARTITION BY artist_id ...)` window, or relaxed to a single global
  cap if per-artist fairness is not load-bearing. For `_decompose`, collect all `(artist_part,
  title_part)` candidate title-token sets first and issue one batched title search per bucket.
  At minimum, document the worst-case query count and consider lowering the route `limit` ceiling
  for the autocomplete caller.

### 2. [M] `myblog_music` pins `shared_db@v0.3.0` while backend/worker are on `v0.18.1` (15 versions behind)
- **Category:** dependency
- **Location:** `requirements.txt:13`
- **Evidence:**
  ```
  myblog_music/requirements.txt:13: ...@v0.3.0
  myblog_backend/requirements.txt:10: ...@v0.18.1
  myblog_worker/requirements.txt:7:  ...@v0.18.1
  ```
  Verified the columns the music read-path actually touches (`genres`, `aliases`, `views`,
  `best_new`, `label`, `spotify_url`, `popularity`, `followers`) already exist in the `v0.3.0`
  model (`git show v0.3.0:src/myblog_shared_db/models.py`), so **this is not an active break today.**
  The risk is forward drift: `v0.3.0` predates the `categories`→`sections` rename and the
  FEAT-genre-system tables (`genres`/`album_genres`/`track_genres`, added later — see HEAD
  models.py:645+). The music service does not yet query genre tables (its `genres` is the legacy
  Artist JSONB column), so it works — but any future music feature that touches the genre tables,
  or any ORM-level relationship change in shared_db (e.g. the `sections` rename already shipped to
  prod via backend/worker), will silently mismatch the pinned model.
- **Why it matters:** ARCH-6 git-pins shared_db per service precisely so each can move
  independently, but a 15-version lag means the music ORM models can disagree with the live prod
  schema. The `Post.category`/`section` divergence is already live in prod (backend/worker on v0.18.1).
  Music doesn't read Post, so it's dormant, but it's a latent landmine for the next cross-cutting change.
- **fixDifficulty:** S (bump pin + run tests + regen openapi) but verify-cost is M (need a real-DB
  smoke since music has no local DB here — defer to prod smoke per `[feedback-local-db-smoke-fallback]`).
- **Proposal:** Bump to `v0.18.1` to align with the other services, run pyright + unit tests, regen
  `openapi.json`, and prod-smoke `/unified` + `/albums/:id` + `/artists/:id`. If a deliberate lag is
  desired, add a one-line comment in `requirements.txt` stating why and the last-verified-compatible
  schema version. Flag to owner before merge (cross-repo pin bump).

### 3. [M] Stale/broken integration test asserts a SQS message shape the code never produces
- **Category:** test-gap
- **Location:** `tests/test_candidates_localstack.py:8,57,94,108`
- **Evidence:**
  - Route is wrong: test calls `client.get("/api/search/candidates", ...)` (line 94) but the real
    mount is `prefix="/api/music/search"` → real path `/api/music/search/candidates`
    (`app/main.py:25`). The test request would 404.
  - Message-shape assertion is impossible: `assert msgs[0]["spotify_album_id"] == "alb_111"` (line 108)
    but `enqueue_album_sync` emits `{"album_ids": [...], "market": ...}` (`app/clients/sqs_client.py:75`)
    — there is no `spotify_album_id` key. Even if the route were fixed, the assert can never pass.
  - Queue URL/name hardcodes `album-sync.fifo` (lines 8, 57) — `[project-arch-audit]`/memory note the
    prod queue is the **standard** `blogSQS`, not a FIFO `album-sync.fifo`.
  - Reload comment `import app.api.routers as search_router # ← _sqs 정의된 파일` reloads the package
    `__init__`, not any `_sqs`-defining module (no such module exists).
- **Why it matters:** It's marked `@pytest.mark.integration` so CI skips it (`pytest -m "not integration"`),
  meaning this rot has gone unnoticed. It gives false confidence that the candidates→SQS contract is
  tested end-to-end, when in fact running it would fail at the request and the assert. The candidates
  enqueue path has **no working test at all** (`cadidate_search_service.py` and `sqs_client.py` both
  show 0 test files in the inventory).
- **fixDifficulty:** M
- **Proposal:** Either fix the test to the current contract (correct route, assert on `album_ids`/`market`,
  drop the FIFO assumption) or delete it and replace with a fast unit test of
  `CandidateSearchService.search_candidates` that mocks `spotify.search` + `SqsClient` and asserts the
  enqueued body shape — no LocalStack/Docker needed. Given the candidates path is the SQS contract
  boundary, having *some* green test of the message body is worth more than a skipped LocalStack test.

### 4. [M] Cognito JWT validation does not verify the token `audience` / `client_id`
- **Category:** security
- **Location:** `app/core/auth.py:67-78`
- **Evidence:**
  ```python
  claims = jwt.decode(
      token, key, algorithms=["RS256"], issuer=issuer,
      options={"verify_at_hash": False},
  )
  if claims.get("token_use") not in ("access", "id"):
      raise HTTPException(... "Invalid token type")
  ```
  Signature, issuer, and `token_use` are checked, but neither `aud` (id tokens) nor `client_id`
  (access tokens) is verified. Any RS256 token signed by the same Cognito user pool — including one
  minted for a *different app client* in that pool — passes. The only gated route is
  `/candidates` (read-only Spotify passthrough + SQS enqueue), so blast radius is small, but the
  check is incomplete.
- **Why it matters:** `[project-arch-audit-2026-06-05]` already flags edge_guard Bearer-bypass as a
  HIGH; this is the music-side analogue. For a one-pool/one-client setup it's low practical risk
  today, but it's a latent authz hole if the pool ever gains a second app client.
- **fixDifficulty:** S
- **Proposal:** Add an `audience=settings.COGNITO_APP_CLIENT_ID` (id tokens) or an explicit
  `claims["client_id"] == settings.COGNITO_APP_CLIENT_ID` check (access tokens) after decode, behind
  a settings value. Mirror whatever `myblog_backend/app/core/auth.py` does so the two stay consistent
  (the file comment claims it already mirrors backend for the JWKS-503 path — extend that mirroring).

### 5. [M] Dead code: worker-only write methods + unused helpers shipped in the Lambda bundle
- **Category:** duplication
- **Location:** `app/repositories/album_repo.py:83-127,230-239`, `app/repositories/track_repo.py:122-192`, `app/clients/spotify_client.py:66-120`, `app/core/singleflight.py`, `app/utils/mapping.py`, `app/domain/enums.py`, `app/mappers/album_candidate_mapper.py`
- **Evidence:** grep for call sites returned none inside `app/` for: `upsert_album_min`,
  `link_album_artists`, `list_by_spotify_artist`, `upsert_tracks_with_artists_db_only`,
  `SpotifyClient.search_albums` / `get_album` / `get_album_tracks_all` / `get_artists`,
  `single_flight`/`SingleFlight`, `normalize_release_date` (utils/mapping), `AlbumCandidateMapper`.
  `app/domain/enums.py` is 0 bytes. These are the album/track *write* path (which belongs to the
  worker) plus the synchronous Spotify album/tracks fetchers — none of which a DB-first read service
  should call (and rule #9 forbids sync Spotify on user paths). `spotify.search` *is* used (candidates);
  the other Spotify methods are not.
- **Why it matters:** It's cross-repo duplication of the worker's write logic living dormant in the
  music Lambda — it inflates the bundle, confuses readers about the service boundary (a reader could
  wrongly believe music writes albums), and `singleflight.py`'s `_locks` dict grows unbounded if ever
  wired up (latent memory leak). The `spotify_client.py` header comment even says it's a "Parallel
  implementation" of the worker's client that "must stay in sync" — but only `search` is used here.
- **fixDifficulty:** S
- **Proposal:** Delete the unused write methods, the unused Spotify methods, `singleflight.py`,
  `utils/mapping.py`, the empty `enums.py`, and `album_candidate_mapper.py` (confirm against
  `tests/` first — none reference them). Trim `SpotifyClient` to just `_get_token`/`_headers`/`search`.
  This is read-only-friendly; it shrinks the audited surface and removes the misleading "music can
  write" affordance.

### 6. [M] No `Set-Cookie`/credentials review: CORS `allow_credentials=True` with broad methods/headers
- **Category:** security
- **Location:** `app/main.py:10-22`
- **Evidence:**
  ```python
  app.add_middleware(CORSMiddleware,
      allow_origins=[... "https://www.ratemymusic.blog"],
      allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
  ```
- **Why it matters:** `allow_credentials=True` combined with `allow_methods/headers=["*"]` is the
  permissive corner of CORS. The origin allowlist is explicit (good — not `"*"`), so this is not a
  wildcard-credentials bug. But the service has no cookie auth (it uses Bearer tokens), so
  `allow_credentials=True` is unnecessary and broadens the surface for no benefit. Low practical risk
  given the explicit origin list; flagged for tightening.
- **fixDifficulty:** S
- **Proposal:** Set `allow_credentials=False` (Bearer tokens don't need it) and narrow
  `allow_methods=["GET"]` (all public routes are GET). If a future route needs more, widen then.

### 7. [L] `ALLOWED_TYPES` constant duplicated in two modules
- **Category:** duplication
- **Location:** `app/services/search_service.py:18` and `app/services/cadidate_search_service.py:10`
- **Evidence:** Both define `ALLOWED_TYPES: Set[str] = {"album", "artist", "track"}` independently.
  The router imports the search_service one (`search.py:15`); candidate_search_service redefines its own.
- **Why it matters:** Two sources of truth for the same vocabulary — a future 4th type (or a typo)
  could be added to one and missed in the other, silently diverging unified vs candidates behavior.
- **fixDifficulty:** S
- **Proposal:** Define once (e.g. in `app/domain/`) and import in both. Minor.

### 8. [L] Typo'd module name `cadidate_search_service.py` (missing 'n')
- **Category:** structure
- **Location:** `app/services/cadidate_search_service.py` (filename)
- **Evidence:** File is `cadidate_search_service.py`; the class inside is correctly `CandidateSearchService`.
  Imported as `from app.services.cadidate_search_service import CandidateSearchService` (`search.py:14`).
- **Why it matters:** Cosmetic, but it's an import-path typo that will trip greps and autocomplete and
  looks unprofessional in a contract-boundary module.
- **fixDifficulty:** S
- **Proposal:** Rename to `candidate_search_service.py` and update the one import. (Per memory
  `[reference-git-mv-then-add-atomic-abort]`, do the `git mv` + add the new path only.)

### 9. [L] Local `db/schema.sql` is stale vs the canonical shared_db schema
- **Category:** other
- **Location:** `db/schema.sql:36-42` (and throughout)
- **Evidence:** Declares `category_id BIGINT REFERENCES categories(id)` and `idx_posts_category_id`,
  but shared_db HEAD renamed `categories`→`sections` / `category_id`→`section_id` (HEAD models.py:301).
  It also lacks any `pg_trgm` GIN index (`grep -niE 'gin|trgm' db/schema.sql` → none) even though the
  service ships a pg_trgm fuzzy path. The canonical schema lives in shared_db migrations
  (`[reference-schema-sql-bootstrap-tables]`), so this file is a non-authoritative bootstrap copy.
- **Why it matters:** A developer could read this file and believe `categories` is current, or that no
  trgm index exists in prod. It's not load-bearing (no migration runner consumes it here) but it's
  misleading documentation. Note: `[reference-pg-trgm-gin-inert-small-catalog]` says the trgm GIN is
  inert at current catalog size anyway, so the missing index here is informational, not a perf bug.
- **fixDifficulty:** S
- **Proposal:** Either delete `db/schema.sql` (defer to shared_db migrations as canonical) or add a
  header pointing to shared_db as the source of truth and refresh the renamed columns.

### 10. [L] README and integration test still describe SQS as `album-sync FIFO + DLQ`
- **Category:** other
- **Location:** `README.md:71,85`, `tests/test_candidates_localstack.py:8,57`
- **Evidence:** `README.md:71` `| 비동기 큐 | Amazon SQS (album-sync FIFO + DLQ)|`; config default
  `QUEUE_NAME = "test-queue"` (`config.py:46`). Per `[reference-architecture-md-unreliable]` /
  `[project-arch-audit]`, prod SQS is the **standard** queue `blogSQS`, not a FIFO `album-sync.fifo`.
  The `enqueue_album_sync` code is FIFO-aware (`if self.is_fifo:` adds `MessageGroupId`/dedup) keyed
  off `queue_name.endswith(".fifo")`, so on the standard prod queue the FIFO branch never fires — the
  code is correct, but the docs/test imply FIFO.
- **Why it matters:** Documentation drift that contradicts the live infra; compounds finding #3.
- **fixDifficulty:** S
- **Proposal:** Update README to reflect the standard `blogSQS` queue (or whatever infra/README.md
  canonically names), and align the test (covered by #3).

### 11. [L] `_get_jwks` lru_cache cleaks app-client/JWKS state but never times out
- **Category:** error-handling
- **Location:** `app/core/auth.py:19-27`
- **Evidence:** `@lru_cache(maxsize=1)` caches the JWKS forever within a warm Lambda container; only
  the "unknown kid" path calls `_get_jwks.cache_clear()` (`auth.py:60`). Cognito key rotation is rare
  and the unknown-kid path does force a refetch, so this is mostly fine — but a successful-then-rotated
  key set is only refreshed reactively (on the first failing token), and there's no TTL.
- **Why it matters:** Low risk (Cognito rotation is infrequent and the reactive clear handles it), but
  worth noting the cache has no time bound. The STAB-2 Step 4 fix correctly made JWKS *fetch failures*
  return 503 instead of 500 (`auth.py:46-57`) — that part is solid.
- **fixDifficulty:** S
- **Proposal:** Acceptable as-is given the reactive `cache_clear` on unknown kid. If hardened, swap to
  a TTL cache (cachetools is already a dep) with e.g. 1h TTL. Optional.

---

## Biggest wins for this repo
1. **Batch the unified-search expansion N+1 (#1)** — the one change that touches the hottest path and
   scales with catalog growth. Bulk `artist_id IN (...)` queries + windowed per-artist cap.
2. **Bump shared_db pin to v0.18.1 (#2)** — removes a 15-version drift landmine and re-aligns with the
   other three services; cheap to do, must prod-smoke.
3. **Fix-or-delete the broken candidates SQS test + add a real unit test (#3)** — the candidates→SQS
   contract boundary currently has zero working test coverage, and the existing one asserts a shape the
   code never emits.
4. **Sweep dead code (#5, #7, #8)** — delete worker-only write methods, unused Spotify fetchers,
   `singleflight`, `utils/mapping`, empty `enums.py`, the candidate mapper; fix the `cadidate`
   filename typo and the duplicate `ALLOWED_TYPES`. Shrinks the bundle and clarifies the read-only
   service boundary.

## What's genuinely clean (not inventing issues)
- Convention hygiene: no `print()`, no `os.getenv()` (all `settings.*`), `logging.getLogger(__name__)`
  everywhere, correct `logger.error(..., exc_info=True)` on the DB/SQS failure paths.
- Eager-loading is correct on the detail and search paths (`selectinload(Album.artists)`,
  `selectinload(Track.album).selectinload(Album.artists)`), so within a single result set there is no
  per-row lazy-load N+1 — the N+1 in #1 is the *cross-bucket expansion fan-out*, a different shape.
- The DB-only boundary holds: `/unified` and all detail endpoints make zero synchronous Spotify calls;
  Spotify is reached only from `/candidates` (rule #9 respected).
- Error handling on the user path is sane: 404s raise before Cache-Control is set, JWKS outage → 503
  not 500, SQS enqueue failures are swallowed-and-logged so a candidates response still returns.
- CI has a real typecheck gate (`pyright app/`) plus an openapi-drift gate — better than convention-only.
