# Audit A — Python services (backend / music / worker / shared_db)

Date: 2026-07-26 · Scope: `myblog_backend`, `myblog_music`, `myblog_worker`, `myblog_shared_db` (read-only).
Method: grep sweep per bug class across all four repos, then read the enclosing function for every hit.
Adoption bar: a finding is listed only if a concrete input/state → concrete wrong outcome could be written.

5 findings. 4 of the 9 hunted classes came back completely clean (see the bottom section).

---

### A-1: album sync holds an open write transaction — with `ON CONFLICT DO UPDATE` row locks already taken — across a Spotify HTTP loop
- **Severity**: P1
- **Where**: `myblog_worker/worker/service/artist_enrich_service.py:55-66` (called from `myblog_worker/worker/service/sync_service.py:252`, inside the transaction opened at `myblog_worker/worker/handler.py:179-181`)
- **Failure scenario**:
  An SQS message `{"album_ids": [<20 spotify album ids>]}` (produced by `myblog_backend/app/clients/sqs_client.py:send_album_sync`, by `album_ingest`, or by the follow-import fan-out) reaches `_process_batch`. `_process_batch` opens `with SessionLocal() as session, session.begin():` and hands `session.connection()` to `AlbumSyncService`. By line 219 of `sync_service.py` the transaction has already executed the `artists` / `albums` / `tracks` bulk upserts, i.e. it **holds row locks on every artist, album and track row in the batch**. Execution then reaches `sync_service.py:252` → `enrich_artists(self.conn, missing_ids)`, which loops chunks of 50 and calls `spotify.get_artists_batch(chunk)` — an outbound HTTP call — *with that transaction still open*.
  Concrete trigger: the batch introduces ≥1 artist whose `photo_url IS NULL` (true for every first-seen artist), and Spotify answers the batch `GET /v1/artists` with 403/404/410 — a routine response when one id in the batch is a relinked or region-unavailable artist. `myblog_worker/worker/clients/spotify_client.py:118-132` then falls back to **up to 50 sequential single-artist GETs**, each wrapped in `_request_with_retry` (3 tries, `timeout=20`, up to 8 s backoff). The transaction now sits idle-in-transaction for tens of seconds up to well past the worker's 120 s Lambda ceiling.
  Outcome: (a) Neon's pooler drops the idle-in-transaction connection → `ProtocolViolation` → the entire batch rolls back → the record is reported in `batchItemFailures` → SQS redelivers → the same path repeats → DLQ; (b) meanwhile every concurrent album-sync invocation (the account runs 10-way SQS concurrency) that shares an artist/album/track row blocks on the held locks for the whole HTTP window.
- **Evidence**:
  `myblog_worker/worker/handler.py:179-182`
  ```python
  with SessionLocal() as session, session.begin():
      svc = AlbumSyncService(session.connection())
      svc.sync_albums_batch(album_ids, market)
  ```
  `myblog_worker/worker/service/sync_service.py:250-254`
  ```python
  if missing_ids:
      enriched = enrich_artists(self.conn, missing_ids)
  ```
  `myblog_worker/worker/service/artist_enrich_service.py:55-66`
  ```python
  def enrich_artists(conn, spotify_ids: list[str]) -> int:
      """Enrich IDs on the caller's connection and transaction."""
      written = 0
      for i in range(0, len(spotify_ids), 50):
          chunk = spotify_ids[i : i + 50]
          rows = _build_enrich_rows(spotify.get_artists_batch(chunk))   # <-- HTTP inside the caller's open txn
          rows.sort(key=lambda row: row["sid"])
          if rows:
              conn.execute(UPDATE_SQL, rows)
  ```
- **Why it isn't already handled**: The same module contains the *correct* pattern (`run_artist_photo_backfill`, lines 69-126: materialize → close → Spotify loop → fresh short write session per chunk, with a module docstring stating "no database session is held across external HTTP calls"). That fix (commit `d7a5e03`, 2026-07-19) was applied only to the standalone backfill job; the inline album-sync path was left on the caller's transaction by design ("Enrich IDs on the caller's connection and transaction"). No timeout, savepoint, or session hand-off guards the inline path, and `_process_batch` has no wall-clock budget. There is no test covering a slow/erroring `get_artists_batch` inside `sync_albums_batch`.

---

### A-2: MDX frontmatter is emitted with Python `repr()` — a title containing both `'` and `"` publishes invalid YAML and breaks the whole site build
- **Severity**: P1
- **Where**: `myblog_backend/app/services/publish_service.py:43-47` (also 59)
- **Failure scenario**:
  Owner publishes a review titled `Taylor Swift's "1989"` via `POST /api/publish`. `make_mdx_frontmatter` emits `f"title: {title!r}"`. Python's `repr` picks single quotes when the string contains a `"` and backslash-escapes the embedded `'`, producing:
  `title: 'Taylor Swift\'s "1989"'`
  YAML does not honour backslash escapes inside single-quoted scalars (the escape is `''`), so the scalar terminates at `Swift\` and the parser errors. Verified locally with PyYAML:
  ```
  YAML ERROR: ParserError while parsing a block mapping
    expected <block end>, but found '<scalar>'  (line 1, column 23)
  ```
  The publish route still returns **200** (GitHub accepted the file). The breakage lands on the next frontend build: `myblog_front/src/content.config.ts` loads `content/blog/**` through an Astro content collection, and a YAML parse error in a single entry fails `getCollection` → the whole static build fails → the site deploy is blocked until someone hand-edits the MDX in the content repo. Same expression is used for `description` (line 45), `category` (line 47) and `post_id` (line 59), and the identical path is reachable from the restore/re-publish flow (`content_sync`).
- **Evidence**: `myblog_backend/app/services/publish_service.py:41-47`
  ```python
  lines = [
      "---",
      f"title: {title!r}",
      f"slug: {slug!r}",
      f"description: {(description or '')!r}",
      f"date: {posted_date.isoformat()}",
      f"category: {cat!r}",
  ```
- **Why it isn't already handled**: `CreatePostReq.title` is validated only with `Field(min_length=1)` (`app/api/routes/publish.py:24`) — no character restriction. `slugify` sanitises only the slug, not the title. The other frontmatter fields on the same list that *can* contain arbitrary text (`tags`, `subgenres`, `albumIds`, `albumCover`, `musicReview`) all go through `json.dumps(...)`, which is valid YAML flow syntax — the `!r` fields are the only ones that don't. No test in `tests/api/test_publish.py` covers a quote-bearing title.

---

### A-3: `/api/research/*` passes an unvalidated path/query id straight into a `uuid` column — a malformed id 500s a publicly reachable GET
- **Severity**: P2
- **Where**: `myblog_backend/app/api/routes/research.py:65` and `:75` → `myblog_backend/app/services/research_service.py:38`, `:57`, `:65`
- **Failure scenario**:
  `GET https://www.ratemymusic.blog/api/research/albums/foo` or `GET /api/research/status?album_ids=foo`. Both routes ride the unauthenticated `GET /api/{proxy+}` API-Gateway catch-all (`infra/apigateway.tf:82`) and are reachable by anyone through CloudFront (the route's own comment says so). `album_id` is typed `str`, is not parsed, and is compared against `AlbumResearch.album_id` / `Album.id`, both `PGUUID(as_uuid=True)`. SQLAlchemy 2.0.50 installs **no** bind processor for that type (verified: `PGUUID(as_uuid=True).dialect_impl(psycopg_dialect).bind_processor(...)` returns `None`), so the raw string reaches Postgres and `uuid = 'foo'` raises `InvalidTextRepresentation` → SQLAlchemy `DataError` → unhandled → HTTP 500 instead of 404. Same shape on the owner-gated `POST /api/research/albums/{album_id}` via `_album_exists`.
- **Evidence**: `myblog_backend/app/api/routes/research.py:68-78`
  ```python
  @router.get("/albums/{album_id}", response_model=AlbumResearchResponse)
  def get_album_research(
      album_id: str,
      ...
      row = svc.get_research(db, album_id)
  ```
  `myblog_backend/app/services/research_service.py:34-42`
  ```python
  return (
      db.query(AlbumResearch)
      .filter(
          AlbumResearch.album_id == album_id,
  ```
- **Why it isn't already handled**: The project already recognises this exact class and fixed it *once*, in the sibling reviews router — `myblog_backend/app/api/routes/reviews.py:54-58` has a dedicated `_parse_album_id()` that converts a `ValueError` into a 404 — and again in `PlaybackService.resolve_uri` (`app/services/playback_service.py:106-109`, `uuid.UUID(str(item_id))` inside a `try`). Neither guard was propagated to `research.py`. The 500 does not leak a stack trace (`debug=False` in prod), so the damage is limited to a wrong status code and a noisy Lambda error metric. The same unguarded `str` id shape also exists on the owner-only routes `buckets.py:390/446/495/526/631/671`, `posts.py:102/138/164/203`, `genres.py:86`, `library.py:627`, `todays_pick.py:180/193` — lower reachability (owner JWT required), same root cause, worth fixing in one sweep.

---

### A-4: today's-pick uses the Postgres UTC `current_date` while the site's day boundary is KST — a pick posted between 00:00 and 09:00 KST vanishes at 09:00 KST
- **Severity**: P2
- **Where**: `myblog_backend/app/services/todays_pick_service.py:36` and `:176`
- **Failure scenario**:
  Owner posts the song of the day at 08:00 KST on 2026-07-26 (= 23:00 UTC on 2026-07-25). `_daily_pick_upsert_stmt` pins `"pick_date": func.current_date()`, which the session evaluates in UTC, so the row is stored with `pick_date = 2026-07-25`. One hour later, at 09:00 KST, the UTC date rolls to 2026-07-26 and `get_today()` — `WHERE DailyPick.pick_date == func.current_date()` — returns `None`. `GET /api/todays-pick` returns null and the `TodaySongBuckit` home tile hides itself for the remaining 23 hours of the KST day. Symmetrically, every evening's pick keeps showing from 00:00 to 09:00 KST the next morning instead of clearing at KST midnight, and a re-post inside the 00:00–09:00 window silently creates a *second* row (different `pick_date`) rather than upserting the one the owner just made.
- **Evidence**: `myblog_backend/app/services/todays_pick_service.py:33-37`
  ```python
  def get_today(self, db: Session) -> Optional[DailyPick]:
      return db.execute(
          select(DailyPick).where(DailyPick.pick_date == func.current_date())
      ).scalar_one_or_none()
  ```
  and `:175-177`
  ```python
  values = {
      "pick_date": func.current_date(),
  ```
- **Why it isn't already handled**: The rest of the codebase treats KST as the canonical day boundary and says so explicitly — `myblog_backend/app/api/routes/release_feed.py:35-41` (`"Day boundary is KST wall-clock (site convention; DB stores UTC)"`, computed Python-side precisely so "a UTC Lambda session doesn't roll the day at 09:00 KST"), and `app/services/library_service.py:845-846, 967, 1044` all wrap timestamps in `func.timezone("Asia/Seoul", ...)`. Those conversions would be no-ops if the DB session were on KST, which confirms the session TZ is UTC. `todays_pick_service.py` is the only date-bounded surface that never applies the conversion; no test exercises it near a UTC midnight.

---

### A-5: musicApi has no `SQS_QUEUE_URL`, so every `/api/music/search/candidates` request makes a blocking `sqs:GetQueueUrl` call — outside the enqueue try/except
- **Severity**: P2
- **Where**: `myblog_music/app/api/routers/search.py:80` → `myblog_music/app/clients/sqs_client.py:44-49`; env gap at `infra/lambda.tf:76-95`
- **Failure scenario**:
  The musicApi Lambda's environment sets `QUEUE_NAME = "blogSQS"` but never sets `SQS_QUEUE_URL` (unlike the backend at `lambda.tf:46` and the worker at `:119`). `Settings.SQS_QUEUE_URL` therefore stays `None`. `search_candidates` constructs `SqsClient()` inline in the route signature body — `service = CandidateSearchService(db=db, sqs=SqsClient())` — and `SqsClient.__init__` ends with `self.queue_url = self._client.get_queue_url(QueueName=self.queue_name)["QueueUrl"]`, a synchronous AWS control-plane round trip **on every single request** to the writer's Spotify candidate search.
  Any failure of that call — SQS control-plane throttling, a transient `EndpointConnectionError`, or an IAM change that drops `sqs:GetQueueUrl` from `LambdaRDSControlRole` — raises out of the route and returns HTTP 500, even though the enqueue itself is explicitly designed to be best-effort. The `try/except Exception` that swallows enqueue failures lives at `cadidate_search_service.py:60-68`, i.e. strictly *after* the client has already been constructed, so it cannot cover the constructor.
- **Evidence**: `infra/lambda.tf:83-88`
  ```hcl
  ENV                  = "prod"
  FASTAPI_ROOT_PATH    = "/api"
  QUEUE_NAME           = "blogSQS"
  SECRETS_PARAM        = "/myblog/music"
  ```
  (no `SQS_QUEUE_URL`) — versus `myblog_music/app/clients/sqs_client.py:44-49`
  ```python
  if not self.queue_url:
      if self.is_local:
          self.queue_url = f"{self.endpoint_url}/{self.account_id}/{self.queue_name}"
      else:
          self.queue_url = self._client.get_queue_url(QueueName=self.queue_name)["QueueUrl"]
  ```
  and `myblog_music/app/api/routers/search.py:80-86`
  ```python
  service = CandidateSearchService(db=db, sqs=SqsClient())
  try:
      return service.search_candidates(...)
  except ValueError as ve:
      raise HTTPException(status_code=400, detail=str(ve))
  ```
- **Why it isn't already handled**: The boto3 *client* is `lru_cache`d (`_get_boto_sqs`), but the `get_queue_url` **response** is not — it is re-resolved per `SqsClient()` instance, and a new instance is built per request. Nothing memoises the resolved URL on the module, and the route does not catch a generic exception. The backend twin avoids this entirely by reading `settings.SQS_QUEUE_URL` and degrading to a logged no-op when it is unset (`myblog_backend/app/clients/sqs_client.py:38-41`); that hardening was never applied to the music copy.

---

## Checked and clean

These classes were swept across all four repos and produced **no** finding that clears the adoption bar. Listing them is deliberate evidence of coverage.

1. **Auth guards that fail open — CLEAN.**
   `myblog_backend/app/core/auth.py` and `myblog_music/app/core/auth.py` were diffed line by line. Both fail closed on an unset `COGNITO_USER_POOL_ID` (503, logged), both map a JWKS-fetch `httpx.HTTPError` to 503 rather than letting it escape as a 500, both reject `token_use` outside `{access, id}`, and both clear the JWKS `lru_cache` on an unknown `kid`. The only structural difference is that the backend factors validation into a shared `verify_token()` (so `edge_guard` and `require_cognito_token` validate identically) while music inlines it — the *behaviour* is identical, and music has no edge_guard to share with. `require_owner` (`backend auth.py:133-165`) fails closed on an unset `OWNER_SUB` (503) and 403s a non-owner sub. `edge_guard` (`backend app/main.py:55`) requires `settings.EDGE_SECRET` truthy *before* the header compare, so an empty secret can no longer match an empty/absent header, and a bad Bearer token is validated rather than trusted by prefix. No path was found where missing config yields an allowed request.
   (Also checked: `/openapi.json` and `/docs` bypass `edge_guard` because they don't start with `/api` — but no matching API Gateway route exists (`infra/apigateway.tf`), so they are unreachable in prod. Not a finding.)

2. **DB session held open across an external-API loop — one finding (A-1); everything else CLEAN.**
   Every session/HTTP interleaving was read: `library_sync_service` (explicit Phase 1 READ / Phase 2 external I/O / Phase 3 WRITE split), `saved_tracks_sync_service`, `lastfm_sync_service`, `spotify_member_sync_service`, `release_upcoming_service` (both passes), `album_ingest_service`, `artist_enrich_service.run_artist_photo_backfill`, `isrc_backfill_service` (commits the read txn at line 128 before the first Spotify call), `lyrics_eval_core.run_eval_batch` (per-row commit keeps the connection warm), `listening_sync_service`. All follow fetch → materialize → close → loop → fresh short write session. `generate_and_save_aliases` (`sync_service.py:299`) commits after the SELECT and commits per artist row; its only open-txn window is one MusicBrainz call inside a single artist iteration (sub-second under the 1 req/s limiter), which is not a Neon idle-drop risk. A-1 is the sole violation.

3. **Bulk `ON CONFLICT` upserts not sorted by conflict key — CLEAN.**
   All 25 upsert sites were read. The high-concurrency ones are explicitly sorted with a comment naming the deadlock rule: `sync_service.py:135` (artists), `:152` (albums), `:202` (tracks), `artist_enrich_service.py:62/104`, `isrc_backfill_service.py:288/297`, `release_upcoming_service.py:190/449`, `spotify_member_sync_service.py:195`, `follow_import_service.py` (`ORDER BY id` pushed into the `INSERT … SELECT`). The unsorted ones (`saved_tracks_sync_service._upsert_rows`, `listening_sync_service` recent-albums) are single-owner jobs whose two possible concurrent producers read the same Spotify pagination in the same order and are debounced 60 s apart — no concrete interleaving that deadlocks could be constructed, so they are deliberately **not** reported.

4. **Outbound HTTP without an explicit `timeout=` — CLEAN.**
   Every `httpx` / `requests` / `urllib` call site in the four repos carries an explicit timeout: backend `auth.py:25` (10), `playback_service.py:181` (10), `integration_service.py:180` (10), `publish_service.py:114/125/144/158` (10); music `auth.py:25` (10), `spotify_client.py:24/61/73/82/96/112` (20); worker `spotify_user_client._request_with_retry` (all callers pass `timeout=20`), `lrclib_client.py:45` (client-level `timeout=20.0`), `itunes_client.py:34` (20), `lastfm_client.py:78` (20); shared_db scripts `urlopen(..., timeout=30)`. `musicbrainzngs` exposes no per-request timeout, and `musicbrainz_client.py:19` bounds it with a documented `socket.setdefaulttimeout(15)`.

5. **Synchronous Spotify (or slow external) call on a user-facing request path — CLEAN.**
   `/api/music/search/unified` is DB-only end to end (`search_service.py` touches only the three repositories plus a per-process `TTLCache`); `/candidates` is the intentional, Cognito-gated Spotify read. Backend `/api/playback/spotify-token` and `PUT /api/integrations/spotify` hit `accounts.spotify.com` (the auth host) only — the documented rule-#9 exception — and both fail closed with 503 *before* any outbound call when creds/KMS are unprovisioned. `connect_lastfm` explicitly performs no Last.fm call. Every `/api/library/*` and `/api/members/*` read is served from worker-written cache tables. The music routers (`albums`, `artists`, `feed`, `releases`) are DB-only.

6. **Secrets logged or leaked — CLEAN.**
   Every logging call matching `token|secret|password|DATABASE_URL|client_secret|api_key|refresh` was read. `config.py` masks the DSN via `_mask()` and only logs it at DEBUG. Spotify/KMS failures log a status code or `type(e).__name__` only (`playback_service.py:203/261`, `integration_service.py:146/195`, `spotify_member_sync_service.py:269/328`). `publish.py:56` logs `token_set=bool(token)`, never the token. `_persist_token_state` logs the exception without the token value. The publish 502 body relays a GitHub error body (`RuntimeError(f"GitHub API error {r.status_code}: {r.text[:500]}")` → `HTTPException(502, str(e))`) — GitHub error bodies never echo the credential, and the route is `require_owner`-gated, so this is not reported.

7. **`os.getenv()` instead of `settings.*`, `print()` instead of a logger — CLEAN (no behavioural impact).**
   Zero `os.getenv` / `os.environ` reads exist in `myblog_backend/app`, `myblog_music/app`, `myblog_worker/worker`, or `myblog_shared_db/src` — all config goes through pydantic-settings. The only `print()` calls are in `myblog_worker/worker/run_local.py` (a local SQS polling harness that never runs on Lambda), which causes no production behaviour change.

8. **Unhandled error paths that become 500s on a user-facing route — one finding (A-3).**
   The publish, lyrics, members, release-feed, reviews, me, playback, integrations and todays-pick routes were read for uncaught exception paths. All map their domain exceptions to explicit status codes (`LyricsTrackNotFoundError`→404, `MemberNotFoundError`→404, `HandleTakenError`→409, `Playback*Error`→503/404/502, `CognitoDeleteError`→502, `SpotifyCodeRejectedError`→400). Request bodies validate CHECK-constraint-shaped fields at the edge (`UpdateMeRequest` handle pattern, `AlbumReviewUpsertRequest` half-step rating) precisely so a constraint violation 422s instead of 500ing. A-3 is the only surviving gap.

9. **SQS handler correctness — CLEAN.**
   `myblog_worker/worker/handler.py:357-444` wraps each record in its own `try/except`, collects failures into `batchItemFailures` (partial-batch reporting is correct), and returns `{}` for the EventBridge branches. A malformed JSON body fails only its own record. Poison-message risk is bounded: `sync_albums_batch` skips the `null` array elements Spotify returns for unknown ids (`sync_service.py:70-77`) so one bad id can't fail a whole record, and the producers chunk at 20 album ids per message (`backend sqs_client.py:_ALBUM_SYNC_CHUNK`, worker `sqs_producer._MAX_PER_MESSAGE`) explicitly sized against the 120 s Lambda timeout. Long-running jobs carry wall-clock budgets (`isrc_backfill` `ISRC_BACKFILL_TIME_BUDGET_SEC`, `release_upcoming` `RELEASE_POLL_TIME_BUDGET_SEC`, `lyrics_eval_core` `time_budget_sec` with `cancel_futures=True`). The lyrics-incremental chain-enqueue is best-effort and cannot fail the album records. Idempotency is handled per job (`ON CONFLICT DO NOTHING` dedup keys, the D31 60 s manual-refresh debounce, `writes_enabled` read from worker settings rather than the message). The one gap that *would* turn a record into a retry loop is A-1's unbounded HTTP inside the open transaction, reported there rather than duplicated here.
