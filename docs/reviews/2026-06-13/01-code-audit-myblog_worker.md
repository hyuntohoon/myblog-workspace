# Code Audit — myblog_worker (2026-06-13)

Read-only audit of `myblog_worker` (SQS + EventBridge consumer Lambda; raw `text()` SQL,
no ORM). Entry point `worker/handler.py`; services under `worker/service/`; clients under
`worker/clients/`. Tests under `tests/`. Verification in CI is **pytest only** (no lint /
typecheck — see F4).

## Health read

The repo is in **good shape** for a one-person project. Idempotency is handled deliberately
(`ON CONFLICT DO NOTHING/UPDATE`, dedup keys, SQS `ReportBatchItemFailures` partial-batch
failures, per-row commit in alias fill, `begin_nested()` savepoints in library PULL). Raw SQL
is **uniformly parameterized** — no injection surface found (the one f-string in a URL,
`get_artist_albums`, interpolates an internal Spotify id into a path, not SQL). Spotify
transient retry (429/5xx + transport) is centralised and tested. The SQS visibility-timeout vs
Lambda-timeout hazard the brief flags was already fixed (STAB-3: `blogSQS` 720s ≥ 120s Lambda,
`infra/sqs.tf:14`). The brief's hint about `genre_mapping.py` living in the worker is stale —
it now lives in `myblog_shared_db` (git-pinned `v0.18.1`) and is imported, which is correct.

The load-bearing problems are: (1) Spotify HTTP issued **inside an open DB transaction** during
album sync, holding a Neon connection across multi-second round-trips; (2) the alias-fill path
issues up to ~20 **sequential, rate-limited** MusicBrainz HTTP calls per EventBridge tick with
no per-tick wall-clock guard against the 120s ceiling; (3) **no lint/typecheck gate** in CI;
plus several test-coverage gaps on shipped branches (`album_ingest` handler route, `sqs_producer`)
and a duplicated sentinel literal.

---

## Findings (severity-sorted)

### F1 — Spotify HTTP calls run inside the open DB transaction (album sync) [H / M]
`worker/handler.py:77-80` → `worker/service/sync_service.py:58,237`

The handler opens the transaction, then `sync_albums_batch` does its external I/O inside it:

```python
# handler.py:77
with SessionLocal() as session, session.begin():
    svc = AlbumSyncService(session.connection())
    svc.sync_albums_batch(album_ids, market)
```
```python
# sync_service.py:58  (inside the open tx)
albums = spotify.get_albums(album_ids, market=mkt)
...
# sync_service.py:237 (still inside the tx, per 50-id chunk in a loop)
detail_list = spotify.get_artists_batch(chunk)
```

The `get_albums` batch fetch AND every per-chunk artist-enrich `get_artists_batch` happen while
the Neon connection is checked out and a transaction is open. Each call can block for the
20s httpx timeout, plus retry backoff up to `MAX_BACKOFF_SECONDS=8` per attempt on a 429
(`spotify_user_client.py:84,96`). With SQS `batch_size=10` (`infra/lambda.tf:125`) and an
account-wide concurrency/connection budget that is already tight (account concurrency limit 10
per MEMORY), holding a pooled connection open across seconds of Spotify I/O is wasteful and
widens the lock window on `albums`/`artists`/`album_genres`.

**Proposal:** fetch all Spotify data BEFORE opening the transaction — pass the already-fetched
album/artist payloads into a pure DB-writing method — so the tx only wraps the upserts. (M:
requires splitting `sync_albums_batch` into fetch + write phases; the enrich loop's second
fetch also needs hoisting.)

---

### F2 — Alias fill: up to ~20 sequential rate-limited MB calls per tick, no wall-clock guard [H / M]
`worker/service/sync_service.py:327-406`, `worker/clients/musicbrainz_client.py:40,132,171`

`generate_and_save_aliases` pulls `LIMIT 10` artists, and for each calls
`fetch_artist_mbid_and_aliases`, which issues `musicbrainzngs.search_artists` (1 call) **plus a
`get_artist_by_id` for each candidate it tries** (`musicbrainz_client.py:171`, inside the
candidate loop). `musicbrainzngs.set_rate_limit(1.0)` (`musicbrainz_client.py:40`) serialises
these to ~1 req/s. Worst case per tick ≈ 10 artists × (1 search + ≥1 detail) ≈ 20+ sequential
requests ≈ 20+ seconds, plus the 15s `socket.setdefaulttimeout` per stalled call
(`musicbrainz_client.py:19`). The EventBridge alias cron runs on `blogWorkerLambda` (120s
timeout); a few slow/stalled lookups in one batch can approach or blow the ceiling, and the
batch is **not** chunked by elapsed time — only by `LIMIT 10`.

This is bounded today (LIMIT 10) so it is unlikely to trip the 120s ceiling in the common case,
but there is zero headroom margin and no early-exit on elapsed time; a run of stalls
(each 15s socket timeout) reaches 120s at ~8 stalled lookups.

**Proposal:** add a per-tick wall-clock budget (e.g. break the loop once `time.monotonic()-start`
exceeds ~90s) so the run commits what it finished and the next cron continues, and/or lower
`LIMIT` if the 15s socket timeout × candidate fan-out proves too wide. (M)

---

### F3 — Album-catalog ingest: sequential per-artist Spotify fetch with no time guard [M / M]
`worker/service/album_ingest_service.py:85-90`

```python
for artist_sid in sweep:                      # up to SWEEP_ARTISTS_PER_TICK = 30
    items = catalog_client.get_artist_albums(artist_sid, ...)   # 1 HTTP each, serial
```

30 sequential `GET /artists/{id}/albums` calls per daily tick, each up to 20s + retry backoff,
all on the 120s `blogWorkerLambda`. Then `get_albums(novel_ids)` chunks at 20/call. There is no
elapsed-time bound; a slow Spotify period (30 × a few seconds) eats the budget. Unlike F2 this
job only DISCOVERS+ENQUEUES (the docstring's design intent), so it stays light in the happy
path, but 30 serial round-trips have no margin and no early-exit.

**Proposal:** add a wall-clock budget that stops sweeping artists and enqueues what was found so
far (the stateless day-bucket rotation already tolerates a partial sweep), or reduce
`SWEEP_ARTISTS_PER_TICK`. (M)

---

### F4 — CI runs no lint or type check — only pytest [M / S]
`.github/workflows/deploy.yml:28-34`

The `test` job runs `pytest tests/` and nothing else. There is no `ruff`, `mypy`, or any static
gate, despite a local `.ruff_cache/` existing (ruff is run by hand, not in CI). The codebase is
fully type-annotated (`from __future__ import annotations` throughout), so a `mypy`/`ruff` gate
would catch real regressions (unused vars like `loc` in `spotify_client.get_albums:66` and
`get_artists:99` are dead; a sentinel-literal drift like F6 would be caught by a constant check).
Worker has no PR-stage CI either (deploy is push-to-main only, per MEMORY), so this `test` job is
the entire automated quality gate.

**Proposal:** add a `ruff check` (and optionally `mypy worker/`) step before `pytest` in the
`test` job. (S)

---

### F5 — `album_ingest` EventBridge handler branch has no test [M / S]
`worker/handler.py:112-115`; `tests/test_handler.py`

`test_handler.py` covers the `aws.events` alias branch, `spotify_listening`, `spotify_refresh`,
`spotify_library_sync`, batch, unknown-format, and error→`batchItemFailures`. It does **not**
cover the `{"job": "album_ingest"}` branch (grep: `album_ingest` absent from `test_handler.py`).
That branch ships to prod via a daily EventBridge cron (`infra/eventbridge.tf:84`). A routing
regression (e.g. the branch order, or `_run_album_ingest` wiring) would not be caught.
`album_ingest_service` itself is well-tested (`test_album_ingest.py`, 7 cases) — only the handler
dispatch is untested.

**Proposal:** add a `test_handler_eventbridge_album_ingest_job` mirroring the existing
`test_handler_eventbridge_listening_job`, asserting `_run_album_ingest` is called and the other
job paths are not. (S)

---

### F6 — Sentinel `"not_found"` duplicated as a bare literal instead of importing `MBID_NOT_FOUND` [M / S]
`worker/service/sync_service.py:390` vs `worker/clients/musicbrainz_client.py:47`

```python
# musicbrainz_client.py:47
MBID_NOT_FOUND = "not_found"
```
```python
# sync_service.py:390  — duplicated magic string, the constant is NOT imported
if mbid == "not_found":
    skipped_precheck += 1
```

`sync_service.py` imports `fetch_artist_mbid_and_aliases` from the client (line 11) but compares
its return value against the bare literal `"not_found"` rather than the exported `MBID_NOT_FOUND`
constant. If the sentinel value is ever changed in the client, this counter-bucketing silently
mis-classifies every result as `succeeded` (and the UPDATE still writes the sentinel into
`musicbrainz_id`, so the IS-NULL eviction still works — only the log counters break, masking a
real signal). Low blast radius, trivial fix.

**Proposal:** `from worker.clients.musicbrainz_client import MBID_NOT_FOUND` and compare against
it. (S)

---

### F7 — `sqs_producer.enqueue_album_sync` has no test [M / S]
`worker/clients/sqs_producer.py`; grep: `sqs_producer` referenced in **0** test files

The sole SQS *producer* — it re-enqueues unknown recently-played / saved / ingested albums onto
`blogSQS`, the feedback edge of the whole pipeline — has zero direct test coverage. It is exercised
only indirectly (callers pass `enqueue_unknown` as a mock). Its own logic — `_MAX_PER_MESSAGE=20`
chunking (`sqs_producer.py:40`), the `SQS_QUEUE_URL`-unset no-op (`:29`), empty-list short-circuit,
and the message body shape `{"album_ids": [...], "market": ...}` that the consumer must parse — is
untested. A regression in the chunk size or body key would silently break the catalog feedback loop.

**Proposal:** add a unit test mocking `boto3.client("sqs")`, asserting chunking at 20, the
unset-URL no-op, and the exact body shape the handler consumes. (S)

---

### F8 — Each `enqueue_album_sync` call constructs a fresh boto3 SQS client [L / S]
`worker/clients/sqs_producer.py:33-39`

```python
def enqueue_album_sync(album_ids):
    ...
    import boto3
    sqs = boto3.client("sqs", ...)   # new client every call
```

A new boto3 client (and its botocore session / credential resolution) is built on every invocation.
In a single listening-sync tick this fires once, so impact is small, but a warm Lambda rebuilds it
each EventBridge cron. The Secrets Manager clients in `config.py:75` and `spotify_user_client.py:121,166`
follow the same per-call pattern. Module-level (or `functools.lru_cache`) client reuse is the
standard Lambda warm-container optimization.

**Proposal:** lazily cache the SQS client at module scope. (S) — low priority; correctness is fine.

---

### F9 — `run_local.py` deletes every SQS message regardless of handler outcome [L / S]
`worker/run_local.py:49-61`

The local poller catches a handler exception, logs it, and **still deletes the message**
("재시도 비활성 정책" / retry-disabled policy, `:55`). This is local-dev only (never deployed; not
referenced by infra or CI — confirmed by grep), so it cannot cause prod data loss. But it diverges
sharply from prod semantics (prod uses `ReportBatchItemFailures` → redrive → DLQ after 3 tries),
so local testing of the failure path gives a false "it's fine, message gone" signal. It also ignores
the handler's `batchItemFailures` return entirely.

**Proposal:** at minimum document the divergence in the file header; better, only delete on success
or when `messageId` is absent from the returned `batchItemFailures`. (S) — local only, low priority.

---

### F10 — Artist genre refresh is gated on missing photo, so stale genres never re-enrich [L / M]
`worker/service/sync_service.py:224-267`

The enrich step only re-fetches artists where `photo_url IS NULL OR photo_url = ''` (`:227-229`),
and that same fetch is what backfills `genres`, `followers`, `popularity`. So an artist that already
has a photo but whose `genres` are stale/empty (e.g. Spotify added genres after first sync, or a
first sync that returned no genres) is never refreshed — and since S1 genre mapping
(`:276-309`) reads `artists.genres`, that album never gets its tier-0 genre attached on re-sync.
First-seen artists are unaffected (they always lack a photo, so they enrich). This is a correctness
edge, not a hot bug; the daily Step-3 enrichment poller (outside this repo) is the intended catch-up.

**Proposal:** decouple the enrich predicate from photo presence (e.g. also enrich when
`genres IS NULL`), or document that genre backfill for already-photographed artists is the poller's
job, not the sync path's. (M)

---

### F11 — `.ruff_cache/` is not gitignored [L / S]
`.gitignore` (no `.ruff_cache/` entry); `git ls-files .ruff_cache` → 0

`.gitignore` covers `.pytest_cache/`, `.mypy_cache/`, `allure-results/`, `build/`, `bundle.zip`,
but not `.ruff_cache/`. It is currently untracked (0 files in git), so no harm done yet, but a
careless `git add -A` could land cache files. Trivial.

**Proposal:** add `.ruff_cache/` to the Test/Cache section of `.gitignore`. (S)

---

## Biggest wins for this repo

1. **F1** — move Spotify fetches out of the open DB transaction in `sync_albums_batch`
   (connection-pool + lock-window win on the hottest path; the account is connection-tight).
2. **F2 / F3** — add a per-tick wall-clock budget to the two serial-HTTP scheduled jobs
   (alias fill, album ingest) so they degrade gracefully under the 120s ceiling instead of
   risking a timeout with zero margin.
3. **F4** — add a `ruff`/`mypy` gate to CI; it is currently pytest-only and would catch dead
   vars, the F6 literal-drift class, and type regressions cheaply.
4. **F5 + F7 + F6** — close the cheap test/consistency gaps on shipped code: the `album_ingest`
   handler route, the `sqs_producer` producer, and the duplicated `"not_found"` sentinel.

## Notes / non-issues verified

- SQL injection: none found — all `text()` statements use bound params; `ANY(:ids)`, `jsonb_build_object(CAST(:x AS text))` etc. The one f-string URL (`get_artist_albums`) is a Spotify path, not SQL.
- SQS visibility (720s) ≥ Lambda timeout (120s): already correct (`infra/sqs.tf:14`, STAB-3).
- Partial-batch failure: handled via `batchItemFailures` + `ReportBatchItemFailures` ESM (`handler.py:164`, `infra/lambda.tf:128`).
- Idempotency: deliberate and consistent (ON CONFLICT, dedup keys, per-row commit, savepoints).
- `genre_mapping.py`: correctly lives in `myblog_shared_db` (pinned), not duplicated in the worker — the brief's hint was stale.
- `researchWorkerLambda` shares this handler but the worker has **no research-mode branch**; a research message would fall through to `logger.warning("Unknown message format")` and be deleted. This matches the MEMORY note that the paid research Lambda is dormant (executor is a local poller), so it is expected, not a bug — flagged here only so it is not mistaken for dead routing later.
