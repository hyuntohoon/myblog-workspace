# Code Audit — Consolidated (2026-06-13)

Across the four audited service repos (`myblog_music`, `myblog_front`, `myblog_worker`, `myblog_shared_db`), the overall health read is **good and getting better, with no fire**. Convention hygiene is strong everywhere (settings-based config, structured logging, parameterized SQL, fully type-annotated Python, lint-clean front), the load-bearing service-boundary rule (`/api/music/search/unified` is DB-only; no synchronous Spotify on user paths) is respected, and idempotency in the worker is consistently and deliberately handled. The 46 findings cluster into three recurring shapes rather than isolated defects: (1) **performance hot paths that fan out per-row / per-artist to external or DB round-trips** — present in both `music` (O(limit) expansion + decomposition) and `worker` (Spotify-in-transaction, MusicBrainz/Spotify sequential sweeps with no wall-clock budget); (2) **duplication and dead weight** — hand-rolled types/fetchers and unused deps/exports in `front`, a parallel un-migrated search core, dead worker-write methods in the read service, and forked genre-mapping rules in `shared_db`; (3) **test and contract-truth gaps** — `front` has zero test infrastructure, `worker`/`music` lack tests on the SQS producer/consumer boundary, the `shared_db` parity test structurally can't catch a real type drift, and stale README/docs/tests misrepresent the live SQS contract and version pins. The two genuinely load-bearing correctness items are the `shared_db` **Section.id 32-bit-vs-BIGSERIAL type drift** (invisible to CI) and the **15-version-stale `shared_db` pin in `myblog_music`** (dormant, not yet broken). Everything else is perf-batching, a dead-code sweep, a pin bump, and restoring coverage of the candidates→SQS boundary.

## Master findings table (46 findings; H → M → L)

| # | Repo | Title | Location | Category | Sev | Fix |
|---|------|-------|----------|----------|-----|-----|
| H1 | music | Unified-search expansion + decomposition fan out to O(limit) per-row DB queries | `app/services/search_service.py:199-231, 288-330` | performance | H | Batch artist→album/track expansion into one `IN (...)` query w/ `ROW_NUMBER() PARTITION BY artist_id`; batch decompose; or lower autocomplete `limit` ceiling |
| H2 | front | No test runner or test suite at all (entire repo) | `package.json` + `.github/workflows/main.yml:50-54` | test-gap | H | Add vitest + units for `lib/reviews.ts`, `lib/member.ts`, `useMusicSearch` race-guard; wire `pnpm test` into CI check job |
| H3 | front | Album-detail response shape hand-rolled in 4 places; generated `Music_AlbumDetail` exists | `lib/albumDetail.ts:18-21`, `CommandPalette.tsx:202-206`, `WriterApp.tsx:56-60`, `writer/types.ts` | duplication | H | Derive one `AlbumDetail = components['schemas']['Music_AlbumDetail']`; single cached+deduped `fetchAlbumDetail` |
| H4 | front | Music-search core extracted for writer but homepage search bar never migrated | `scripts/searchBarDb.client.ts` (509) vs `lib/useMusicSearch.ts` (379) | duplication | H | Migrate homepage bar onto shared core (extract framework-agnostic fetch+map+race-guard); at min port `dedupeBySpotify` |
| H5 | worker | Spotify HTTP calls run inside the open DB transaction during album sync | `worker/handler.py:77-80` → `service/sync_service.py:58,237` | performance | H | Split into fetch phase + pure DB-write phase; open `session.begin()` only around upserts |
| H6 | worker | Alias fill issues ~20 sequential rate-limited MusicBrainz calls/tick, no wall-clock guard | `service/sync_service.py:327-406`; `clients/musicbrainz_client.py:40,132,171` | performance | H | Add per-tick wall-clock budget (~90s) that commits finished rows; consider lowering LIMIT |
| H7 | shared_db | `Section.id` modeled 32-bit `Integer` but prod column is `BIGSERIAL` (type drift) | `models.py:120` | type-safety | H | Change to `BigInteger`, regen `_generated_schema.sql`, bump+tag (Tag.id already correct) |
| H8 | shared_db | README install pin + version table several majors stale (says v0.5.0; real pins v0.18.1) | `README.md:10, 36-40` | other | H | Update snippet to latest tag, regen table from live `requirements.txt`, or drop table for a pointer |
| M1 | music | `shared_db` pinned v0.3.0 while backend/worker on v0.18.1 (15 versions behind) | `requirements.txt:13` | dependency | M | Bump to v0.18.1, run pyright+units, regen openapi, prod-smoke; or add last-verified-compat comment. Flag owner |
| M2 | music | Stale/broken integration test asserts a SQS shape the code never produces | `tests/test_candidates_localstack.py:8,57,94,108` | test-gap | M | Fix route + assert `album_ids`/`market` + drop FIFO, or replace with fast mocked unit test of `search_candidates` |
| M3 | music | Cognito JWT validation does not verify token audience / client_id | `app/core/auth.py:67-78` | security | M | Verify `aud`(id)/`client_id`(access) == `COGNITO_APP_CLIENT_ID`; mirror backend auth |
| M4 | music | Dead code: worker-only write methods + unused helpers in the Lambda bundle | `repositories/album_repo.py`, `track_repo.py`, `clients/spotify_client.py`, `core/singleflight.py`, `utils/mapping.py`, `domain/enums.py`, `mappers/album_candidate_mapper.py` | duplication | M | Delete unused write/Spotify methods, singleflight, mapping, empty enums, candidate mapper; trim SpotifyClient |
| M5 | music | CORS `allow_credentials=True` with wildcard methods/headers, no cookie auth | `app/main.py:10-22` | security | M | `allow_credentials=False`; narrow `allow_methods=['GET']` |
| M6 | front | 4 heavyweight deps unused — zero imports in src (`@dnd-kit/*`, `@toast-ui/editor`) | `package.json:25-27,33` | dependency | M | `pnpm remove` all four; re-run build. Pure subtraction |
| M7 | front | `safeFetch`, `fetchMetrics`, `Metrics` are dead exports (cancelled likes/comments) | `lib/api.ts:3-45` | duplication | M | Delete all three; note `/api/metrics/batch` for backend audit if dead server-side |
| M8 | front | `authFetch` is a dead, refresh-less duplicate of `apiFetch` | `lib/auth.ts:215-225` | duplication | M | Delete `authFetch`; keep `getAccessToken`/`getAuthHeader`/`refreshAccessToken` |
| M9 | front | Candidates endpoint hit with two different auth wrappers across the two search cores | `searchBarDb.client.ts:346` vs `useMusicSearch.ts:275` | error-handling | M | Pick one; candidates is unauthenticated → plain `fetch` no-auth for both, or route both through shared core |
| M10 | front | Cognito `PUBLIC_COGNITO_*` env vars read raw, not in typed env schema | `lib/auth.ts:7-9` + `astro.config.ts:64-76` | type-safety | M | Add COGNITO_DOMAIN/CLIENT_ID/REDIRECT_URI to `env.schema` so missing var fails the build |
| M11 | worker | Album-catalog ingest does 30 sequential per-artist Spotify fetches, no time guard | `service/album_ingest_service.py:85-90` | performance | M | Add wall-clock budget that stops sweeping + enqueues found-so-far, or reduce `SWEEP_ARTISTS_PER_TICK` |
| M12 | worker | CI runs no lint or type check — pytest is the only quality gate | `.github/workflows/deploy.yml:28-34` | test-gap | M | Add `ruff check` (and optionally `mypy worker/`) before pytest |
| M13 | worker | `album_ingest` EventBridge handler branch has no test | `worker/handler.py:112-115`; `tests/test_handler.py` | test-gap | M | Add `test_handler_eventbridge_album_ingest_job` mirroring the listening-job test |
| M14 | worker | Sentinel `"not_found"` duplicated as bare literal instead of `MBID_NOT_FOUND` | `service/sync_service.py:390` vs `clients/musicbrainz_client.py:47` | duplication | M | Import and compare against `MBID_NOT_FOUND` |
| M15 | worker | `sqs_producer.enqueue_album_sync` (the only SQS producer) has no test | `worker/clients/sqs_producer.py` | test-gap | M | Unit test mocking `boto3.client('sqs')`: chunking, unset-URL no-op, exact body shape |
| M16 | shared_db | Schema-parity test compares column names only — H7 passes CI invisibly | `tests/test_schema_parity.py:119-140, 71-103` | test-gap | M | Capture `(name, normalized_type)` and assert type equality (SERIAL→int4, BIGSERIAL→int8) |
| M17 | shared_db | `Tag` model used by `Post.tags` but not exported from package root | `__init__.py:1-38`; `models.py:130` | structure | M | Add `Tag` (+ Spotify cache models if root-imported) to `__init__.py`/`__all__`, or document `.models` import |
| M18 | shared_db | Operational ETL/LLM pipeline (backfill_genres.py + prod-writing plist) lives in a 'models' package | `scripts/backfill_genres.py` (864); `scripts/com.myblog.genre-backfill.plist:33-39` | structure | M | Keep `genre_mapping.py`; consider relocating backfill+plist to worker; if staying, README note. (guess) maybe intentional |
| M19 | shared_db | Genre mapping rules forked between `genre_mapping.py` (S1_RULES) and `backfill_genres.py` (EN_RULES/ITUNES_MAP) | `genre_mapping.py:125-143`; `backfill_genres.py:99-159` | duplication | M | Test Latin-rule idx < reggae-rule idx in BOTH; longer-term move EN_RULES/ITUNES_MAP into shared module |
| L1 | music | `ALLOWED_TYPES` constant duplicated in two modules | `search_service.py:18` and `cadidate_search_service.py:10` | duplication | L | Define once in `app/domain/`; import in both |
| L2 | music | Module filename typo: `cadidate_search_service.py` (missing 'n') | `app/services/cadidate_search_service.py` | structure | L | `git mv` to `candidate_search_service.py`; update single import (add only new path) |
| L3 | music | Local `db/schema.sql` stale vs canonical shared_db schema | `db/schema.sql:36-42` | other | L | Delete (defer to shared_db migrations) or add source-of-truth header + refresh renamed cols |
| L4 | music | README + integration test still describe SQS as 'album-sync FIFO + DLQ' | `README.md:71,85`; `tests/test_candidates_localstack.py:8,57` | other | L | Update README to standard `blogSQS`; align test (covered by M2) |
| L5 | music | JWKS `lru_cache` has no TTL (refresh only reactive on unknown kid) | `app/core/auth.py:19-27` | error-handling | L | Acceptable as-is (reactive `cache_clear` on unknown kid); optional `cachetools` TTLCache ~1h |
| L6 | front | Member dashboard still ships SAMPLE genres/artists/activity to production | `lib/member.ts:115-126`; `OverviewDash.tsx:450-453`, `StatsTab.tsx` | structure | L | (tracked debt) Swap to real `apiFetch` via existing seam when FEAT-genre-artist-distribution lands |
| L7 | front | `clone = JSON.parse(JSON.stringify())` on every bucket-tree mutation | `BucketBoard.tsx:89` (10+ call sites) | performance | L | Use `structuredClone()` — one-line change |
| L8 | front | `apiFetch` (live wrapper) has no request timeout; the dead `safeFetch` does | `lib/api.ts:65-88` vs `:7-8` | error-handling | L | Add ~10-15s AbortController timeout to `apiFetch`; return null on abort |
| L9 | worker | Each `enqueue_album_sync` call constructs a fresh boto3 SQS client | `clients/sqs_producer.py:33-39` | performance | L | Lazily cache the SQS client at module scope |
| L10 | worker | `run_local.py` deletes every SQS message regardless of handler outcome | `worker/run_local.py:49-61` | error-handling | L | Document divergence in header; better, only delete on success / absence from batchItemFailures |
| L11 | worker | Artist genre refresh gated on missing photo, so stale genres never re-enrich | `service/sync_service.py:224-267` | other | L | Decouple enrich predicate from photo presence (also enrich when genres IS NULL), or document poller owns it |
| L12 | worker | `.ruff_cache/` is not gitignored | `.gitignore` | other | L | Add `.ruff_cache/` to the Test/Cache section |
| L13 | shared_db | `album_genres`/`track_genres` source & confidence are open TEXT with no DB CHECK | `migrations/V17__genres.sql:52-53`; `models.py:684-685,702-703` | type-safety | L | Future additive migration: `CHECK (source IN (...))`, `CHECK (confidence IN ('high','low'))` |
| L14 | shared_db | `backfill_genres.py` DB/network/LLM paths untested — incl. prod-writing confidence-upsert invariant | `tests/test_backfill_genres.py`; `backfill_genres.py:715-763` | test-gap | L | Real-engine integration test for `run_execute`: low→high upgrade, never downgrade, re-run no-op |
| L15 | shared_db | `combine_album` K-Pop confidence counting is fragile (dual-purpose voters vars) | `backfill_genres.py:226-232` | error-handling | L | Keep behavior (tests lock it); add inline comment + optionally a named test for the LLM-only nuance |
| L16 | shared_db | `http_get_json` swallows non-retryable errors into a sentinel dict, silently dropping/caching data | `backfill_genres.py:242-256` | error-handling | L | Surface a `fetch_errors` counter in build_report; don't cache `{'genre': None}` when cause was `_error` |

## High

### H1 — Unified-search expansion + decomposition fan out to O(limit) per-row DB queries (music)
`app/services/search_service.py:199-231` (expansion), `:288-330` (`_decompose`).
> `for ar in literal_artists: exp_albums.extend(self.album_repo.list_by_artist_id_simple(ar.id, ...))` and a parallel loop for `exp_tracks`; `literal_artists` is bounded only by route `limit` (`le=100`), so artist→album + artist→track expansion is up to `2*len(literal_artists)` separate Neon round-trips (~200 at limit=100). `_decompose` adds up to `DECOMP_MAX_SPLITS=6` splits each issuing one `search_by_name` + one `search_by_title` per requested bucket (~24 more). The 60s `_unified_cache` only absorbs exact repeats, not the cold first query of each autocomplete keystroke prefix.

**Proposal:** Batch the artist→album/track expansion into one query each keyed by `artist_id IN (...)`, mirroring the already-bulk `list_by_album_ids`; keep per-artist LIMIT via `ROW_NUMBER() OVER (PARTITION BY artist_id ...)`. Batch `_decompose` title searches per bucket. At minimum lower the route limit ceiling for the autocomplete caller and document worst-case query count.

### H2 — No test runner or test suite at all (front)
`package.json` + `.github/workflows/main.yml:50-54`.
> `grep -in 'vitest|jest|playwright|test' package.json` → (no matches); `find . -name '*.test.*'` → (none); CI 'check' job runs only `astro check` + `pnpm lint` + `api.gen.ts` diff. Testable unguarded logic: `lib/reviews.ts` `selectFeatured`/`buildReviewCards` (0-10→0-5 rating normalize), `lib/member.ts` `computeStats`/`bucketCount`, `useMusicSearch` seq-race (CP-1/CP-4 regression history).

**Proposal:** Add vitest + unit tests for `lib/reviews.ts` (selectFeatured no-BNM fallback, scale===10 halving), `lib/member.ts` (computeStats, bucketCount tree walk), and the `useMusicSearch` mappers/race-guard; wire `pnpm test` into the main.yml check job.

### H3 — Album-detail response shape hand-rolled in 4 places; generated `Music_AlbumDetail` type exists (front)
`src/lib/albumDetail.ts:18-21`, `src/components/writer/CommandPalette.tsx:202-206`, `src/components/writer/WriterApp.tsx:56-60`, `src/components/writer/types.ts`.
> `api.gen.ts:1347` defines `Music_AlbumDetail` (returned by `/api/music/albums/{album_id}` per `api.gen.ts:2450,2481`). Yet `albumDetail.ts:18-21` (MusicTrack/MusicArtist/MusicAlbumOut), `CommandPalette.tsx:203` inline `album:{id,title,cover_url,release_date,best_new?}`, `WriterApp.tsx:57` the identical inline shape, and `writer/types.ts` all re-declare it by hand. `fetchAlbumDetail` is also implemented 3x (`albumDetail.ts:35`, `WriterApp.tsx:51`, `searchBarDb.client.ts:376/383`). Hand-typed consumers won't fail the `api.gen.ts` sync gate on a music-API field change.

**Proposal:** Derive one `AlbumDetail = components['schemas']['Music_AlbumDetail']` in `lib/albumDetail.ts`, export the single cached+inflight-deduped `fetchAlbumDetail`, and have CommandPalette/WriterApp import it instead of re-fetching + re-typing.

### H4 — Music-search core extracted for the writer but homepage search bar never migrated (front)
`src/scripts/searchBarDb.client.ts` (509 lines) vs `src/lib/useMusicSearch.ts` (379 lines).
> `useMusicSearch.ts:1-13` header: extracted 'so... CommandPalette can share one search core instead of hand-rolling near-identical fetch + race-guard + cooldown logic twice.' But `searchBarDb.client.ts` still hand-rolls all of it in parallel: db mappers `useMusicSearch.ts:102-142` (mapAlbums/mapArtists/mapTracks) vs `searchBarDb.client.ts:238-279` (mapCandArtists/mapCandAlbums/mapCandTracks); race guard `seqRef:204` vs `_searchSeq:334,352`; cooldown `SPOTIFY_COOLDOWN_MS:57` vs inline `setTimeout(...,3000):332`; `dedupeBySpotify:144` has no homepage equivalent.

**Proposal:** Migrate the homepage search bar onto the shared core (extract framework-agnostic fetch+map+race-guard helpers since `searchBarDb` is a non-React `.client.ts` island). At minimum port `dedupeBySpotify` into the homepage path.

### H5 — Spotify HTTP calls run inside the open DB transaction during album sync (worker)
`worker/handler.py:77-80` → `worker/service/sync_service.py:58,237`.
> `handler.py:77` `with SessionLocal() as session, session.begin(): svc = AlbumSyncService(session.connection()); svc.sync_albums_batch(album_ids, market)` — then `sync_service.py:58` `albums = spotify.get_albums(album_ids, market=mkt)` and `sync_service.py:237` `detail_list = spotify.get_artists_batch(chunk)` (in the per-50-chunk enrich loop) BOTH execute inside that open transaction. Each httpx call can block 20s + retry backoff up to `MAX_BACKOFF_SECONDS=8` (`spotify_user_client.py:84,96`), with SQS `batch_size=10` (`infra/lambda.tf:125`).

**Proposal:** Split `sync_albums_batch` into a fetch phase (all Spotify I/O, incl. the artist-enrich fetch) and a pure DB-write phase; open `session.begin()` only around the upserts so a Neon connection is not held across seconds of Spotify round-trips and the lock window on albums/artists/album_genres stays minimal.

### H6 — Alias fill issues ~20 sequential rate-limited MusicBrainz calls per tick with no wall-clock guard (worker)
`worker/service/sync_service.py:327-406`; `worker/clients/musicbrainz_client.py:40,132,171`.
> `sync_service.py:333` pulls `LIMIT 10` artists; for each, `fetch_artist_mbid_and_aliases` does `musicbrainz_client.py:132` `search_artists(...)` plus `musicbrainz_client.py:171` `get_artist_by_id(mbid, includes=['aliases'])` per candidate tried (inside the candidate loop). `musicbrainz_client.py:40` `set_rate_limit(1.0)` serialises to ~1 req/s; `musicbrainz_client.py:19` `socket.setdefaulttimeout(15)`. Worst case ~10*(1+>=1) >= 20 serial requests; 8 stalled 15s lookups reach the 120s Lambda ceiling. No elapsed-time chunking, only LIMIT 10.

**Proposal:** Add a per-tick wall-clock budget (break once `time.monotonic()-start` exceeds ~90s) so the run commits finished rows and the next cron continues; consider lowering LIMIT given the 15s socket timeout × candidate fan-out.

### H7 — `Section.id` modeled as 32-bit `Integer` but prod column is `BIGSERIAL` (type drift) (shared_db)
`src/myblog_shared_db/models.py:120`.
> `models.py:120` `id: Mapped[int] = mapped_column(Integer, primary_key=True)` → generated `_generated_schema.sql`: `id SERIAL NOT NULL`. Canonical/prod: `tests/canonical_schema.sql` `id BIGSERIAL PRIMARY KEY` and `posts.section_id BIGINT REFERENCES sections(id)`. The FK side (`Post.section_id`, `models.py:301`) is correctly BigInteger, so the model is internally inconsistent: a 64-bit FK pointing at a 32-bit-modeled PK.

**Proposal:** Change `Section.id` to `mapped_column(BigInteger, primary_key=True)`, regenerate `_generated_schema.sql`, bump version + tag. `Tag.id` already uses BigInteger so Section is the lone offender.

### H8 — README install pin + version table several majors stale (says v0.5.0, real pins v0.18.1) (shared_db)
`README.md:10`, `README.md:36-40`.
> `README.md:10` install snippet `...@v0.5.0`; table claims backend v0.5.0 / music v0.3.0 / worker v0.2.2. Actual: `grep -rn myblog_shared_db.git@` → backend `requirements.txt:10` @v0.18.1, music `:13` @v0.3.0, worker `:7` @v0.18.1. Backend & worker are 13 minors ahead of what the README states.

**Proposal:** Update the install snippet to the latest tag, regenerate the table from each service's live `requirements.txt`, or drop the table and point at the per-service pins as source of truth (it will always rot).

## Medium

### M1 — `shared_db` pinned at v0.3.0 while backend/worker are on v0.18.1 (music)
`requirements.txt:13`.
> `myblog_music/requirements.txt:13` pins `...@v0.3.0`; `myblog_backend/requirements.txt:10` and `myblog_worker/requirements.txt:7` both pin `...@v0.18.1`. Verified via `git show v0.3.0:src/myblog_shared_db/models.py` that the Album/Artist/Track columns music reads (genres, aliases, views, best_new, label, spotify_url) already exist at v0.3.0, so it is NOT broken today; but v0.3.0 predates the categories→sections rename (live in prod via backend/worker) and the FEAT-genre-system tables (HEAD `models.py:645+`), which music does not yet query.

**Proposal:** Bump to v0.18.1 to re-align, run pyright + unit tests, regen `openapi.json`, and prod-smoke `/unified` + `/albums/:id` + `/artists/:id` (no local DB here, defer real verification to prod smoke). If a deliberate lag is wanted, add a comment in `requirements.txt` stating the last-verified-compatible schema version. Flag to owner before merge.

### M2 — Stale/broken integration test asserts a SQS message shape the code never produces (music)
`tests/test_candidates_localstack.py:8,57,94,108`.
> Test GETs `/api/search/candidates` but the real mount is `prefix='/api/music/search'` (`app/main.py:25`) so the request 404s. It asserts `msgs[0]['spotify_album_id']=='alb_111'` (line 108) but `enqueue_album_sync` emits `{'album_ids':[...],'market':...}` (`app/clients/sqs_client.py:75`) — no `spotify_album_id` key exists. Queue hardcodes `album-sync.fifo` (lines 8,57) though prod is the standard `blogSQS`. Marked `@pytest.mark.integration` so CI (`pytest -m 'not integration'`) skips it; `candidate_search_service` and `sqs_client` have 0 test files in the inventory.

**Proposal:** Fix the route + assert on `album_ids`/`market` + drop the FIFO assumption, or delete and replace with a fast unit test of `CandidateSearchService.search_candidates` that mocks `spotify.search` + `SqsClient` and asserts the enqueued body shape (no LocalStack/Docker). The candidates→SQS contract boundary currently has no working test.

### M3 — Cognito JWT validation does not verify token audience / client_id (music)
`app/core/auth.py:67-78`.
> `jwt.decode(token, key, algorithms=['RS256'], issuer=issuer, options={'verify_at_hash': False})` checks signature/issuer and then `claims.get('token_use') in ('access','id')`, but never verifies `aud` (id tokens) or `client_id` (access tokens). Any RS256 token signed by the same Cognito user pool — including one minted for a different app client — passes. Only `/candidates` is gated (read-only Spotify passthrough + SQS enqueue), so blast radius is small.

**Proposal:** After decode, verify `audience=settings.COGNITO_APP_CLIENT_ID` (id tokens) or `claims['client_id']==settings.COGNITO_APP_CLIENT_ID` (access tokens), behind a settings value, and mirror whatever `myblog_backend/app/core/auth.py` does to keep the two consistent.

### M4 — Dead code: worker-only write methods + unused helpers shipped in the Lambda bundle (music)
`app/repositories/album_repo.py:83-127,230-239`; `track_repo.py:122-192`; `clients/spotify_client.py:66-120`; `core/singleflight.py`; `utils/mapping.py`; `domain/enums.py`; `mappers/album_candidate_mapper.py`.
> grep for call sites inside `app/` returned none for `upsert_album_min`, `link_album_artists`, `list_by_spotify_artist`, `upsert_tracks_with_artists_db_only`, `SpotifyClient.search_albums/get_album/get_album_tracks_all/get_artists`, `single_flight/SingleFlight`, `normalize_release_date` (utils/mapping), `AlbumCandidateMapper`. `app/domain/enums.py` is 0 bytes. `spotify_client.py` header even calls itself a 'Parallel implementation' of the worker client; only `.search()` is used. `singleflight._locks` grows unbounded if ever wired up.

**Proposal:** Delete the unused write methods, unused Spotify methods, `singleflight.py`, `utils/mapping.py`, empty `enums.py`, and `album_candidate_mapper.py` (confirm none are referenced under `tests/` first); trim SpotifyClient to `_get_token`/`_headers`/`search`. Shrinks the bundle and removes the misleading 'music can write albums' affordance.

### M5 — CORS `allow_credentials=True` with wildcard methods/headers and no cookie auth (music)
`app/main.py:10-22`.
> `app.add_middleware(CORSMiddleware, allow_origins=[... 'https://www.ratemymusic.blog'], allow_credentials=True, allow_methods=['*'], allow_headers=['*'])`. The service uses Bearer tokens, not cookies, so `allow_credentials=True` is unnecessary; `methods=['*']` is broad though all public routes are GET. Origin list is explicit (not '*'), so this is not a wildcard-credentials bug.

**Proposal:** Set `allow_credentials=False` (Bearer tokens do not need it) and narrow `allow_methods=['GET']`; widen later only if a non-GET route is added.

### M6 — Four heavyweight dependencies are unused — zero imports in src (front)
`package.json:25-27,33`.
> `grep -rn "from '@dnd-kit|from '@toast-ui" src` → (no matches). `@dnd-kit/core`, `@dnd-kit/sortable`, `@dnd-kit/utilities`, `@toast-ui/editor` all in dependencies with no real import. Only dnd-kit string in src is the comment `OverviewDash.tsx:9` 'kept pointer-based, NOT @dnd-kit' (board DnD is hand-rolled). `@toast-ui/editor` (full WYSIWYG) wholly unreferenced.

**Proposal:** `pnpm remove @dnd-kit/core @dnd-kit/sortable @dnd-kit/utilities @toast-ui/editor`; re-run `pnpm build` to confirm. Pure subtraction.

### M7 — `safeFetch`, `fetchMetrics`, and `Metrics` in api.ts are dead exports (cancelled likes/comments) (front)
`src/lib/api.ts:3-45`.
> `grep -rn 'import.*safeFetch|import.*fetchMetrics' src` → (no matches); only `apiFetch` is imported from api.ts. `fetchMetrics` (25-45) targets `POST /api/metrics/batch` for likes/comments — a feature CLAUDE.md memory records as 'comments/likes dropped'. So this is stranded code for a cancelled feature still referencing a backend endpoint.

**Proposal:** Delete `safeFetch`, `fetchMetrics`, and `interface Metrics`. If `/api/metrics/batch` is also dead server-side, note for the backend audit.

### M8 — `authFetch` in auth.ts is a dead, refresh-less duplicate of `apiFetch` (front)
`src/lib/auth.ts:215-225`.
> `grep -rn 'authFetch' src` → only the definition; zero call sites. `authFetch` sets a Bearer header but does NOT do the 401→refresh→retry that `apiFetch` does (`auth.ts:166-197`). Shipping a near-namesake that silently lacks token refresh undermines the CLAUDE.md rule 'authed calls go through apiFetch' — a future contributor could grab the wrong one.

**Proposal:** Delete `authFetch`. Keep `getAccessToken`/`getAuthHeader`/`refreshAccessToken` (those are used).

### M9 — Candidates endpoint hit with two different auth wrappers across the two search cores (front)
`src/scripts/searchBarDb.client.ts:346` vs `src/lib/useMusicSearch.ts:275`.
> Same endpoint `GET /api/music/search/candidates`: `searchBarDb.client.ts:346` `fetch(url,{headers:getAuthHeader()})` (bare header, no refresh) vs `useMusicSearch.ts:275` `apiFetch(...)` (Bearer + 401 refresh). The endpoint has no `security` block in the merged spec (`api.gen.ts:2624` `search_candidates_...` has no security key) → unauthenticated. So neither needs a token; one path forces `goLogin()` on a stray 401, the other doesn't, for an endpoint meant to work logged-out.

**Proposal:** Pick one. Since candidates is unauthenticated, plain `fetch` with no auth header for both is the honest choice; or route both through the shared core from H4.

### M10 — Cognito `PUBLIC_COGNITO_*` env vars read raw, not in the typed env schema (front)
`src/lib/auth.ts:7-9` + `astro.config.ts:64-76`.
> `astro.config.ts` `env.schema` declares only `PUBLIC_API_URL` + `PUBLIC_BACKEND_API_URL`. Login-critical vars read raw: `auth.ts:7-9` `import.meta.env.PUBLIC_COGNITO_DOMAIN/CLIENT_ID/REDIRECT_URI as string`. `grep 'COGNITO' astro.config.ts env.d.ts` → not in schema. A missing var becomes undefined-cast-to-string → malformed `https://undefined/oauth2/authorize` discovered only at runtime; CI build injects them (`main.yml:88-91`) so a missing var builds green and fails in prod.

**Proposal:** Add `PUBLIC_COGNITO_DOMAIN/CLIENT_ID/REDIRECT_URI` (+ `USER_POOL_ID`, already passed at `main.yml:90`) to `env.schema` in `astro.config.ts` so a missing var fails the build, not the user.

### M11 — Album-catalog ingest does 30 sequential per-artist Spotify fetches with no time guard (worker)
`worker/service/album_ingest_service.py:85-90`.
> `for artist_sid in sweep:` (up to `SWEEP_ARTISTS_PER_TICK=30`, `config.py:57`) then `items = catalog_client.get_artist_albums(artist_sid, include_groups='album')` — 30 serial `GET /artists/{id}/albums` calls, each up to 20s + retry backoff, all on the 120s blogWorkerLambda, with no elapsed-time bound or early-exit.

**Proposal:** Add a wall-clock budget that stops sweeping and enqueues what was found so far (the stateless day-bucket rotation tolerates a partial sweep), or reduce `SWEEP_ARTISTS_PER_TICK`.

### M12 — CI runs no lint or type check — pytest is the only quality gate (worker)
`.github/workflows/deploy.yml:28-34`.
> The test job runs only `pytest tests/ -v --alluredir=allure-results`; no ruff/mypy step despite a local `.ruff_cache/` existing (ruff run by hand, not in CI). Codebase is fully annotated (`from __future__ import annotations` throughout). Worker has no PR-stage CI (deploy is push-to-main only), so this job is the entire automated gate. Dead vars like `loc` in `spotify_client.py:66,99` would be caught.

**Proposal:** Add a `ruff check` (and optionally `mypy worker/`) step before pytest in the test job.

### M13 — `album_ingest` EventBridge handler branch has no test (worker)
`worker/handler.py:112-115`; `tests/test_handler.py`.
> grep `album_ingest` over `tests/test_handler.py` returns NONE. `test_handler.py` covers aws.events alias, spotify_listening, spotify_refresh, spotify_library_sync, batch, unknown-format, error→batchItemFailures — but not the `{"job": "album_ingest"}` branch, which ships to prod via a daily EventBridge cron (`infra/eventbridge.tf:84`). The service itself is tested (`test_album_ingest.py`, 7 cases); only the handler dispatch is untested.

**Proposal:** Add `test_handler_eventbridge_album_ingest_job` mirroring `test_handler_eventbridge_listening_job`: assert `_run_album_ingest` is called and the other job paths are not.

### M14 — Sentinel `"not_found"` duplicated as a bare literal instead of importing `MBID_NOT_FOUND` (worker)
`worker/service/sync_service.py:390` vs `worker/clients/musicbrainz_client.py:47`.
> `musicbrainz_client.py:47` `MBID_NOT_FOUND = "not_found"`. `sync_service.py:390` `if mbid == "not_found":` uses the bare literal even though it imports `fetch_artist_mbid_and_aliases` from the same client (line 11). If the sentinel value changes, this counter-bucketing silently mis-classifies every result as `succeeded` (the UPDATE still writes the sentinel so IS-NULL eviction still works — only the log signal breaks).

**Proposal:** `from worker.clients.musicbrainz_client import MBID_NOT_FOUND` and compare against the constant.

### M15 — `sqs_producer.enqueue_album_sync` (the only SQS producer) has no test (worker)
`worker/clients/sqs_producer.py`.
> grep `sqs_producer` over `tests/` returns 0 files. The sole producer that closes the catalog feedback loop (re-enqueues unknown albums onto blogSQS) is exercised only as a mock in callers. Its own logic is untested: `_MAX_PER_MESSAGE=20` chunking (`sqs_producer.py:40`), `SQS_QUEUE_URL`-unset no-op (`:29`), empty-list short-circuit, and the body shape `{"album_ids": [...], "market": ...}` the consumer must parse.

**Proposal:** Add a unit test mocking `boto3.client('sqs')`: assert 20-id chunking, the unset-URL no-op, and the exact body shape the handler consumes.

### M16 — Schema-parity test compares column names only, not types/nullability/PK — H7 passes CI invisibly (shared_db)
`tests/test_schema_parity.py:119-140` (and `_extract_columns :71-103`).
> `_extract_columns` keeps only `tokens[0]` (the bare column name): `result.add(tokens[0].strip('"').lower())`. `test_modeled_columns_present_in_canonical` asserts name presence only. `test_generated_schema_is_fresh` is a models↔models tautology. So SERIAL vs BIGSERIAL drift (H7) sails through because both files have a column literally named `id`. Verified: full suite passes 45/45 with the type drift present.

**Proposal:** Extend `_extract_columns` to capture `(name, normalized_type)` and assert modeled type == canonical type per column, normalizing SERIAL→integer, BIGSERIAL→bigint, TIMESTAMPTZ→timestamptz. Even coarse int4/int8/text/uuid bucketing would catch H7.

### M17 — `Tag` model defined and used by `Post.tags` but not exported from the package root (shared_db)
`src/myblog_shared_db/__init__.py:1-38`; `src/myblog_shared_db/models.py:130`.
> `grep -n Tag src/myblog_shared_db/__init__.py` → no output (Tag NOT in imports or `__all__`), yet `models.py:130` defines `class Tag` and `models.py:319` `Post.tags` relationship depends on it. The four Spotify cache models (SpotifyRecentAlbum/NowPlaying/PlayEvent/RecentTrack) are also unexported. `from myblog_shared_db import Tag` → ImportError; `from myblog_shared_db.models import Tag` works — two inconsistent import surfaces.

**Proposal:** Add `Tag` (and the Spotify cache models if consumers import them via root) to `__init__.py` imports + `__all__`, or document that the long tail is imported from `.models` on purpose. Current half-and-half is an oversight for a shipped STAB-5 feature.

### M18 — Operational ETL/LLM pipeline (backfill_genres.py + prod-writing launchd plist) lives in a 'models' package (shared_db)
`scripts/backfill_genres.py` (864 lines); `scripts/com.myblog.genre-backfill.plist:33-39`.
> Repo charter (`README.md:3` / `pyproject.toml:8`) = 'Canonical SQLAlchemy models'. `backfill_genres.py:715-763` `run_execute` is a 5-block prod-write transaction; `:242-290` do Spotify/iTunes HTTP + AWS Secrets; `:497-519` spawn `claude -p` subprocesses. `com.myblog.genre-backfill.plist:33-39` wires `--incremental --execute` to a daily launchd job that mutates prod. `genre_mapping.py` (shared, imported by worker `sync_service.py:9`) defensibly belongs here; the full ETL+cron does not.

**Proposal:** Keep `genre_mapping.py` (genuine shared pure function). Consider relocating `backfill_genres.py` + plist to `myblog_worker` (already imports the shared mapping, owns the Spotify/EventBridge surface). If staying, add a README note so it isn't mistaken for drift. (guess) may be intentional co-location — flag, don't auto-move.

### M19 — Genre mapping rules forked between `genre_mapping.py` (S1_RULES) and `backfill_genres.py` (EN_RULES/ITUNES_MAP) (shared_db)
`src/myblog_shared_db/genre_mapping.py:125-143`; `scripts/backfill_genres.py:99-159`.
> `genre_mapping.py:125-143` S1_RULES (Spotify-string regex) + S1_EXPLICIT; `backfill_genres.py:99-159` a parallel ITUNES_MAP + EN_RULES with the same vocabulary lock. The Latin-before-reggae ordering invariant is duplicated as comments in both (`genre_mapping.py:11-14`, `backfill_genres.py:138-139,150-151`) but not cross-checked by any test. `grep -c re.compile` → `genre_mapping.py:1`, `backfill_genres.py:2`. Vocabulary half IS guarded (`test_all_table_outputs_in_vocab`, `test_itunes_map_values_are_valid_labels`); ordering half is not.

**Proposal:** Add a test asserting Latin-rule index < reggae-rule index in BOTH S1_RULES and EN_RULES. Longer term, consider moving EN_RULES/ITUNES_MAP into the shared `genre_mapping` module so all genre rules live in one importable place.

## Low

### L1 — `ALLOWED_TYPES` constant duplicated in two modules (music)
`app/services/search_service.py:18` and `app/services/cadidate_search_service.py:10`.
> Both define `ALLOWED_TYPES: Set[str] = {'album','artist','track'}` independently; the router imports the search_service copy (`search.py:15`) while `candidate_search_service` redefines its own and uses it for validation (`cadidate_search_service.py:76,79`).

**Proposal:** Define `ALLOWED_TYPES` once (e.g. in `app/domain/`) and import in both so unified and candidates can't silently diverge on the allowed-type vocabulary.

### L2 — Module filename typo: `cadidate_search_service.py` (missing 'n') (music)
`app/services/cadidate_search_service.py` (filename).
> File is `cadidate_search_service.py` while the class is correctly `CandidateSearchService`; imported as `from app.services.cadidate_search_service import CandidateSearchService` (`search.py:14`).

**Proposal:** `git mv` to `candidate_search_service.py` and update the single import (add only the new path per the git-mv-then-add caveat).

### L3 — Local `db/schema.sql` is stale vs canonical shared_db schema (music)
`db/schema.sql:36-42`.
> Declares `category_id BIGINT REFERENCES categories(id)` and `idx_posts_category_id`, but shared_db HEAD renamed categories→sections / category_id→section_id (HEAD `models.py:301`). `grep -niE 'gin|trgm' db/schema.sql` returns nothing despite the service shipping a pg_trgm fuzzy path. Canonical schema lives in shared_db migrations, so this file is a non-authoritative bootstrap copy.

**Proposal:** Delete `db/schema.sql` (defer to shared_db migrations as canonical) or add a header naming shared_db as source of truth and refresh the renamed columns.

### L4 — README and integration test still describe SQS as 'album-sync FIFO + DLQ' (music)
`README.md:71,85`; `tests/test_candidates_localstack.py:8,57`.
> `README.md:71` lists 'Amazon SQS (album-sync FIFO + DLQ)'; config default `QUEUE_NAME='test-queue'` (`config.py:46`). Per project memory/arch-audit the prod queue is the standard `blogSQS`, not FIFO `album-sync.fifo`. `enqueue_album_sync` is FIFO-aware (`is_fifo` branch keyed on `queue_name.endswith('.fifo')`) so on the standard queue the FIFO branch never fires — code is correct, docs/test imply FIFO.

**Proposal:** Update README to the standard `blogSQS` queue (per `infra/README.md` canonical name) and align the test (covered by M2).

### L5 — JWKS `lru_cache` has no TTL (refresh only reactive on unknown kid) (music)
`app/core/auth.py:19-27`.
> `@lru_cache(maxsize=1)` on `_get_jwks` caches forever within a warm container; only the unknown-kid path calls `_get_jwks.cache_clear()` (`auth.py:60`). No time bound. The STAB-2 Step 4 fix correctly returns 503 (not 500) on JWKS fetch failure (`auth.py:46-57`).

**Proposal:** Acceptable as-is given the reactive `cache_clear` on unknown kid (Cognito rotation is rare). If hardened, swap to a `cachetools` TTLCache (already a dep) with ~1h TTL. Optional.

### L6 — Member dashboard still ships SAMPLE genres/artists/activity to production (front)
`src/lib/member.ts:115-126` (consumed at `OverviewDash.tsx:450-453`, `StatsTab.tsx`).
> `member.ts:121-123` `getGenres`/`getArtists`/`getActivity` return hardcoded `member.sample.ts` data, rendered into real-looking charts at `OverviewDash.tsx:450` (case 'genre' DistChart), `:451` (case 'artists'), `:453` (case 'activity'). A '샘플' badge mitigates, but the genre chart now contradicts the real genre system shipped to prod (FEAT-genre-system Steps 0-4): `/profile` shows fake genres while `/reviews` shows real ones. Per-RFC incremental plan (`member.ts` is a documented swap seam), so tracked debt not a defect.

**Proposal:** (tracked debt) When FEAT-genre-artist-distribution lands, swap `getGenres`/`getArtists` to real `apiFetch` via the existing seam. Flagged so it isn't forgotten as 'looks done.'

### L7 — `clone = JSON.parse(JSON.stringify())` on every bucket-tree mutation (front)
`src/components/member/BucketBoard.tsx:89` (called at 1219,1240,1262,1291,1321,1354,1367,1377,1394,1406).
> `BucketBoard.tsx:89` `const clone = (t) => JSON.parse(JSON.stringify(t))`; 10+ call sites deep-serialize the whole bucket tree per crate add/move/remove/reorder. Negligible at one-person scale but JSON round-trip silently drops non-JSON values and is O(n) per interaction.

**Proposal:** Use `structuredClone()` (available Node 20 + modern browsers) — same semantics, faster, preserves more types. One-line change.

### L8 — `apiFetch` (the live wrapper) has no request timeout; the dead `safeFetch` does (front)
`src/lib/api.ts:65-88` vs `:7-8`.
> `safeFetch` wraps an 8s AbortController (`api.ts:7-8`) but the actually-used `apiFetch` (65-88) has no timeout — a hung Lambda+Neon cold-start leaves the promise pending forever and the calling island stuck in its loading skeleton. `spotify.api.ts`/`buckets.ts`/`research.ts` rely on `apiFetch` returning/rejecting to exit loading. The dead helper has the safety net; the live one doesn't.

**Proposal:** Add an AbortController timeout (~10-15s) to `apiFetch` mirroring `safeFetch`; return null on abort so existing `!res` branches handle it.

### L9 — Each `enqueue_album_sync` call constructs a fresh boto3 SQS client (worker)
`worker/clients/sqs_producer.py:33-39`.
> `import boto3; sqs = boto3.client("sqs", region_name=settings.AWS_DEFAULT_REGION, endpoint_url=(settings.LOCALSTACK_ENDPOINT or None))` builds a new client (and credential resolution) every call. Same per-call pattern at `config.py:75` and `spotify_user_client.py:121,166`. A warm Lambda rebuilds it each cron.

**Proposal:** Lazily cache the SQS client at module scope (`functools.lru_cache` or a module global). Low priority — correctness is fine.

### L10 — `run_local.py` deletes every SQS message regardless of handler outcome (worker)
`worker/run_local.py:49-61`.
> `run_local.py:55` comment '성공/실패 상관없이 삭제 (재시도 비활성 정책)' — the poller catches a handler exception, logs it, then still calls `sqs.delete_message`; it ignores the handler's `batchItemFailures` return. Local-dev only (not referenced by infra or CI — grep confirmed), so no prod data loss, but it diverges from prod ReportBatchItemFailures→redrive→DLQ semantics, giving a false 'message gone, fine' signal when testing failure paths locally.

**Proposal:** Document the divergence in the file header; better, only delete on success or when messageId is absent from the returned batchItemFailures.

### L11 — Artist genre refresh is gated on missing photo, so stale genres never re-enrich (worker)
`worker/service/sync_service.py:224-267`.
> The enrich step fetches only artists where `photo_url IS NULL OR photo_url = ''` (`sync_service.py:227-229`), and that same fetch backfills genres/followers/popularity (`:247-253`). An artist that already has a photo but stale/empty genres is never refreshed; since S1 genre mapping reads `artists.genres` (`:276-309`), that album gets no tier-0 genre on re-sync. First-seen artists are unaffected (always lack a photo). The Step-3 enrichment poller (outside this repo) is the intended catch-up.

**Proposal:** Decouple the enrich predicate from photo presence (also enrich when genres IS NULL), or document that genre backfill for already-photographed artists is the poller's job, not the sync path's.

### L12 — `.ruff_cache/` is not gitignored (worker)
`.gitignore`.
> `.gitignore` Test/Cache section covers `.pytest_cache/`, `.mypy_cache/`, `allure-results/`, `build/`, `bundle.zip` but not `.ruff_cache/`. `git ls-files .ruff_cache` returns 0 (currently untracked), but `git check-ignore .ruff_cache` reports NOT IGNORED — a careless `git add -A` could land cache files.

**Proposal:** Add `.ruff_cache/` to the Test/Cache section of `.gitignore`.

### L13 — `album_genres`/`track_genres` source & confidence are open TEXT with no DB CHECK (shared_db)
`migrations/V17__genres.sql:52-53`; `src/myblog_shared_db/models.py:684-685,702-703`.
> `V17__genres.sql:52-53` `source TEXT NOT NULL` / `confidence TEXT NOT NULL DEFAULT 'high'` — closed domains documented only in comments, no CHECK (`grep -in check V17` → none). By contrast `V16__album_research.sql:45-46` enforces `CHECK (status IN ('queued','running','done','failed'))` and `:64-65` `CHECK (research_mode IN ('off','all','selected'))`. A typo'd `source='itnues'` from a future writer is silently accepted, defeating per-row provenance.

**Proposal:** Future additive migration: add `CHECK (source IN ('mapping','itunes','llm'))` and `CHECK (confidence IN ('high','low'))` on `album_genres`/`track_genres`, matching the album_research/research_mode precedent. Low priority.

### L14 — `backfill_genres.py` DB/network/LLM paths untested — incl. the prod-writing confidence-upsert invariant (shared_db)
`tests/test_backfill_genres.py`; `scripts/backfill_genres.py:715-763`.
> `test_backfill_genres.py` covers only pure functions (`map_itunes`, `is_ost_or_compilation`, `combine_album`, `extract_json_object`, `norm_title`). Untested: `load_catalog` (`:314-362`), `run_execute` (`:715-763`), `fetch_keys`/`fetch_itunes_*` (HTTP), `claude_batch` (subprocess+threading), `run_label`. The 'never downgrade confidence' upsert (`:738-741` `ON CONFLICT ... DO UPDATE ... WHERE album_genres.confidence='low' AND EXCLUDED.confidence='high'`) has no test yet runs against prod daily via launchd.

**Proposal:** Add a real-engine integration test (in-memory Postgres or the Neon `TEST_DB_URL` the worker already uses) for `run_execute`: seed album+genre, run low then high decision, assert upsert upgrades but never downgrades and re-run is a no-op (the idempotency the docstring promises at `:43-46`).

### L15 — `combine_album` K-Pop confidence counting is fragile (dual-purpose voters vars) (shared_db)
`scripts/backfill_genres.py:226-232`.
> `if idol and (kpop_voters or llm_voted_kpop): votes_n = 1 + len(kpop_voters)` — `llm_voted_kpop` is in the guard but never contributes to `votes_n`; confidence is driven purely by `kpop_voters`. An LLM-only idol K-Pop (`kpop_voters=[]`) → `votes_n=1` → low (intended per `test_llm_kpop_claim_alone_needs_idol_flag`). Correct today but the variable name `votes_n` under-represents the LLM's own vote and the dual-purpose logic is brittle to future edits.

**Proposal:** Leave behavior (tests lock it) but add an inline comment that `llm_voted_kpop` gates appending while `kpop_voters` drives confidence, and that LLM-only idol K-Pop is intentionally low. Optionally name a test for that nuance.

### L16 — `http_get_json` swallows non-retryable errors into a sentinel dict, silently dropping (and caching) data (shared_db)
`scripts/backfill_genres.py:242-256`.
> `:252` non-retryable codes return `{'_error': str(e.code)}`; `:253-255` network exceptions log+sleep then fall through to `:256 return {'_error': 'retries-exhausted'}`. Callers (`fetch_itunes_album :415`) do `d.get('results') or []` → treat as 'no genre' and cache `{'genre': None}` (`:420`), so a later re-run won't retry. `build_report` counts itunes_name hits, not fetch failures — transient drops are invisible.

**Proposal:** Surface a `fetch_errors` counter in `build_report` alongside `unmapped_itunes`; do not cache `{'genre': None}` when the cause was `_error` vs a genuine empty result, so re-runs retry transient failures.

## Cross-cutting themes

These are the patterns that recur across two or more repos — fixing the pattern once is worth more than fixing each instance.

1. **Per-row / per-item fan-out to external or DB round-trips on a bounded-but-marginless loop.** The single most consequential theme, spanning both backend service repos. `music` H1 fans out O(limit) per-row to Neon on the autocomplete hot path; `worker` H5 holds a DB transaction open across multi-second Spotify HTTP, H6 makes ~20 serial rate-limited MusicBrainz calls per tick with no wall-clock budget, and M11 sweeps 30 serial Spotify fetches with no time guard. None is on fire today (limits cap them), but all share the same fragility: no elapsed-time budget, no batching, zero headroom against an upstream slowdown. A shared "fetch-all-then-write, with a per-tick wall-clock break" pattern addresses H5/H6/M11 together.

2. **Duplication: the same shape/logic hand-rolled in N places instead of derived once.** `front` H3 (album-detail type in 4 places + fetcher in 3), H4 (two parallel search cores), M7/M8 (dead duplicate fetch wrappers), M9 (one endpoint, two auth wrappers); `music` M4 (a whole parallel Spotify client + worker-write methods duplicating worker logic), L1 (ALLOWED_TYPES twice); `shared_db` M19 (genre rules forked between two modules). Theme: extracted-but-not-fully-adopted abstractions (H4, the half-migrated search core) and copy-paste constants/types that can silently diverge.

3. **Dead weight shipped to prod.** `front` M6 (4 unused heavyweight deps), M7/M8 (dead exports for cancelled features); `music` M4 (dead write methods + helpers + empty `enums.py` in the Lambda bundle); `worker` L12 + `shared_db` (cache dirs / misplaced ETL). Pure-subtraction wins that shrink bundles and remove misleading affordances (e.g. "music can write albums", "use authFetch").

4. **Test & contract-truth gaps at service boundaries.** `front` H2 (zero test infra), `worker` M12 (no lint/typecheck in CI), M13 (album_ingest handler untested), M15 (SQS producer untested); `music` M2 (broken/skipped candidates→SQS test); `shared_db` M16 (parity test can't catch type drift), L14 (prod-writing upsert untested). The candidates→SQS boundary specifically is asserted-wrong in `music` (M2) and untested in `worker` (M15) — **the same contract is broken on the producer side and untested on the consumer side**, a shared finding across two repos.

5. **Stale docs / pins / schema copies that misrepresent the live system.** `shared_db` H8 (README pin table 13 minors behind) and `music` M1 (the pin those README rows describe — v0.3.0, 15 versions behind) are **two views of the same version-drift fact**: the README is wrong about the pins AND one of the pins is stale. `music` L3/L4 (stale schema.sql + FIFO-SQS README) and `shared_db`'s general doc-rot belong to the same theme: non-authoritative copies of canonical truth that rot silently.

6. **Auth/JWT validation looseness on low-blast-radius paths.** `music` M3 (no aud/client_id check) and M5 (needless `allow_credentials=True`) — small blast radius today (only `/candidates`, Bearer-not-cookie), but the proposal is explicitly to "mirror backend auth" so the two services don't diverge on validation strictness.

## Top 5 highest-impact fixes

Weighing severity × blast-radius × cheapness-of-fix:

1. **H7 — `Section.id` BigInteger fix (shared_db).** A real model↔prod type drift (32-bit PK behind a 64-bit FK) that the parity test structurally cannot see; the fix is a one-token change + regen + tag. Highest severity, smallest fix, and it's the canonical schema every service pins — cheapest correctness win on the board. Pair with M16 (teach the parity test to compare types) so the class of bug can't recur silently.

2. **H5/H6/M11 bundled — wall-clock-budget + fetch/write split (worker).** One architectural pattern (fetch-all-then-write, break on per-tick time budget) retires two H's and one M at once, on the exact paths most exposed to an upstream Spotify/MusicBrainz slowdown given the account-wide Lambda concurrency-10 / tight-Neon-pool constraint. Highest blast-radius cluster; medium fix amortized across three findings.

3. **M1 + H8 — bump music's shared_db pin to v0.18.1 and fix the README pin table (music + shared_db).** Two repos, one fact: music is 15 versions behind on the shared schema and the README that documents the pins is itself stale. Cheap (a pin bump + a doc edit), re-aligns the whole workspace on one schema version, and removes the latent footgun where music silently lags the categories→sections rename and genre tables. Gated on a prod smoke (no local DB) and an owner flag.

4. **H3 — derive the album-detail type from `Music_AlbumDetail` + single fetcher (front).** The hand-rolled shape in 4 places (+ 3 fetcher copies) is the one duplication that also defeats the CI contract gate: a music-API field change won't fail the `api.gen.ts` sync check because the consumers are hand-typed. Fixing it restores the contract safety net the workspace already invested in, not just dedupes code.

5. **H2 — add vitest + a thin unit suite (front).** The single biggest structural gap: the front has documented regression history (CP-1/CP-4 search races, rating-scale halving) in exactly the pure logic that's trivially unit-testable, yet zero test infra exists. Low fix difficulty (add runner + a handful of tests, wire into the existing CI check job), and it converts a recurring class of "lint+astro-check pass but the logic regressed" incidents into caught-at-PR failures.
