# FEAT-music-search-recall: Writer-facing music search — recall re-assessment

- **Status**: draft
- **Owner**: 박지훈
- **Created**: 2026-06-04
- **Plan row**: `plan.md` → FEAT-music-search-recall

---

## Goal

Lift writer-facing music search (`/api/music/search/unified`) recall to
**Hit@5 ≥ 0.9 / Hit@1 ≥ 0.6** on a versioned 30-query fixture covering
multi-token / Korean / common-word / typo / alias cases. The fix is
matching-layer first (Postgres extension + alias coverage), with ranking
and frontend touch-ups as supporting work. Spotify fallback boundary stays
out of scope here and is tracked as an open question.

This RFC is the executable form of a brainstorm that was challenged by
three review agents (architect / reviewer / general-purpose) before being
written. The recommended direction below already reflects that critique —
notably, pg_trgm's Korean claim was wrong and has been replaced with a
pg_bigm PoC gate.

## Non-goals

- **External search engine** (Elasticsearch / Meilisearch / Typesense) —
  catalog is small (single writer); dual-write + index-drift cost not
  justified. Reconsidered only if the A1 PoC (Step 2) cannot pass on Neon
  with pg_bigm.
- **Personalization / listener-affinity ranking** — no signal source.
- **Reader-facing search / discovery / browse-by-genre** — writer flow
  only. Genre browse lives in FEAT-genre-taxonomy.
- **DB table storing ranking outputs / per-row debug** — wrong primitive
  (algorithm state, not domain data). A separate `search_misses` event
  table is *deferred* (V10 `spotify_play_events` precedent), not rejected;
  decided after baseline.
- **Spotify auto-fallback in `/unified`** — direct violation of rule #9.
  If pursued later, must be a separate route (`/unified_with_fallback`),
  tracked as Open Question 1.
- **A2-related multi-token UX** in front (e.g. "did you mean these
  sub-queries") — only a structured-query parsing boundary is in scope.

## Current state

### Endpoint and matching
- `GET /api/music/search/unified` (`myblog_music/app/api/routers/search.py:20–48`).
  Params `q`, `type`, `limit`, `offset`, per-bucket offsets. DB-only;
  Spotify is a separate route (`/candidates`) gated by manual UI toggle.
- Matching per entity (`artist_repo.py:40–63`, `album_repo.py:38–48`,
  `track_repo.py:29–41`):
  - artist: `ILIKE '%q%'` on `artists.name` + JSONB array
    `artists.aliases` (MB-sourced)
  - album: `ILIKE '%q%'` on `albums.title` — **no alias column**
  - track: `ILIKE '%q%'` on `tracks.title` — **no alias column**
- No `pg_trgm`, no `pg_bigm`, no `tsvector`, no `unaccent`. No Hangul jamo
  or romanization normalization. All text indexes are btree on identity
  columns only.

### Ranking
- Bucket sort tuples (`search_service.py:188–231`):
  - artist/album: `(path_group, −similarity, −popularity)`
  - track: literal `(0, −sim, 0)`, expansion `(1, has_release_date,
    −release_date.toordinal())`. **There is no `tracks.popularity`
    column** — DB-layer fetch orders tracks by `views DESC, created_at
    DESC`.
- `similarity` is a 4-bucket Python score (`3 = exact`, `2 = startswith`,
  `1 = contains`, `0 = none`) computed *after* the DB fetch. A high-
  similarity row sitting outside the DB-ordered top page never enters
  ranking.

### Expansion
- 1-hop, all in DB (`search_service.py:88–127`). Literal artist → its
  albums + tracks; album → tracks + linked artists; track → album +
  linked artists. Dedup by id, literal wins.
- **R7 (uncovered today)**: album-title matches expand into the track
  bucket and can crowd out direct track-title matches before the
  per-bucket limit fills.

### Frontend (writer)
- `myblog_front/src/components/writer/SubjectBlock.tsx` — 3 sections
  (artist/album/track), Enter-only search firing. **No debounce, no IME
  composition handling.** Single-line ellipsised subtitle for tracks. No
  duration in tile.
- DB ↔ Spotify is an explicit user toggle; empty DB result surfaces a
  status text, not a CTA.

### Storage
- `artists.aliases` is the only alias surface. Albums/tracks have no
  alias column.
- No search-related tables (no `search_logs`, `search_debug`,
  `query_log`). `spotify_play_events` (V10, 2026-06-04) is the closest
  precedent for "event table for analytics over what was previously
  logs-only".

## Target state

After all steps below complete:

- `tests/fixtures/search_cases.yaml` (30 queries × expected top-N) exists
  in `myblog_music`. A single pytest integration test asserts Hit@5 ≥ 0.9
  and Hit@1 ≥ 0.6 against it.
- `/api/music/search/unified` matches against Hangul + Latin queries with
  a CJK-capable Postgres extension (pg_bigm preferred). Multi-token
  queries (artist + album/track combined) return results.
- `album_aliases` + `track_aliases` tables exist in shared_db; worker
  populates them from MusicBrainz release/recording aliases.
- Writer-facing input handles IME composition (no Enter-mid-composition
  phantom searches).
- `?explain=1` query mode returns per-row debug fields
  (`matched_field`, `path`, `similarity`, `popularity`, rank) for dev
  triage. Default response shape unchanged.

## Steps

### Step 1 — D1: IME compose handling (front)

Add `onCompositionStart` / `onCompositionEnd` handlers (or
`e.nativeEvent.isComposing` guard) to `SubjectBlock.tsx:326`, so Enter
during Hangul composition does not fire the search.

**Verification**:
```
pnpm --filter myblog_front lint && pnpm --filter myblog_front exec astro check
# Manual browser check: type 한글 query mid-composition, press Enter,
# confirm search fires only after composition end.
```

**Rollback**: revert single file.

---

### Step 2 — E2: Fixture set + Hit@K gate

Create `myblog_music/tests/fixtures/search_cases.yaml` with 30 queries
covering: multi-token (8), Korean (8), common-word ambiguous (6), typo
(4), alias (4). Each entry: `query`, `expected_top_5_ids` (list of
artist/album/track ids OR the special value `EMPTY` for valid no-result
cases).

Add `tests/integration/test_search_recall_gate.py` that loads the
fixture, runs each query through `search_service.unified_search`, and
asserts Hit@5 ≥ 0.9 and Hit@1 ≥ 0.6. Failure prints per-query results.

This step's job is to establish the **baseline measurement**. Expect the
gate to fail on the current code — that failure is the diff against
which later steps are evaluated.

**Verification**:
```
cd myblog_music && pytest tests/integration/test_search_recall_gate.py -v
# Expected: gate fails (baseline). Record the baseline numbers in the
# Decisions log.
```

**Rollback**: delete the two files.

---

### Step 3 — A1 PoC: pg_bigm on Neon

Verify that pg_bigm is installable on the Neon prod DB and that it
handles Korean queries with usable similarity scores.

Local check first (test branch):
```
psql "$TEST_DB_URL" -c "CREATE EXTENSION IF NOT EXISTS pg_bigm;"
# Run a short script: insert 10 KO seed rows, query similarity for
# '방탄' → '방탄소년단', '봄날' → '봄날', etc. Capture scores.
```

If Neon does not support pg_bigm, this step pivots: try `pg_trgm` on the
same set and accept its (limited) Korean behavior, OR escalate to a
Meilisearch reconsideration as a side RFC. **Either branch is recorded
in the Decisions log; further steps do not start until this branch is
chosen.**

**Verification**: the Decisions log gets an entry stating "pg_bigm
available: yes/no" + scores on the KO probe queries.

**Rollback**: drop extension on the test branch.

---

### Step 4 — A1 implementation (shared_db V11 + music repos)

Contingent on Step 3 outcome.

- shared_db V11: `CREATE EXTENSION pg_bigm` + GIN indexes on
  `artists.name`, `albums.title`, `tracks.title`. (If Step 3 forced
  pg_trgm, the migration is the trgm equivalent.)
- bump shared_db version; apply to prod Neon BEFORE service pin bumps
  (`reference-shared-db-cross-repo-rollout`).
- pin bump in `myblog_music`, `myblog_backend`, `myblog_worker` to keep
  schema consistent (extensions are global to the database; even
  services that don't query the search columns must reference the new
  pin).
- replace `ILIKE '%q%'` in the three search repos with the extension's
  operator + similarity-ordered `LIMIT N`.
- track ranking: do not blindly replace `views DESC, created_at DESC` —
  consider a hybrid score (`similarity × log1p(views)`) so cold catalog
  items do not displace engagement-strong ones.
- ship behind a feature flag (`SEARCH_USE_PG_BIGM=true`) for one
  deployment cycle to allow A/B comparison via the fixture gate.

**Verification**:
```
# Local
pytest tests/integration/test_search_recall_gate.py -v
# Expected: Hit@5 improves materially over Step 2 baseline.

# Prod smoke (after merge + deploy)
curl https://<music-prod>/api/music/search/unified?q=방탄소년단 | jq '.artists[0].name'
```

**Rollback**: flip flag off, then drop the GIN indexes in a follow-up
migration. The extension itself can stay.

---

### Step 5 — A3: album/track aliases

- shared_db V12: `album_aliases (album_id, alias)` +
  `track_aliases (track_id, alias)` with `(target_id, alias)` unique.
- Worker (`myblog_worker`): extend the existing MB fetch path that fills
  `artists.aliases` to also persist `release.aliases[]` and
  `recording.aliases[]` from the same MB response. **No new API call.**
- Music search repos: include alias join in album/track matching
  (same shape as today's artist alias check, but over GIN-indexed columns).

**Verification**:
```
pytest tests/integration/test_search_recall_gate.py -v
# Expected: Hit@5 improves on the alias subset of fixture queries.

# Prod evidence: query an album by a known non-canonical alias and
# confirm it surfaces.
```

**Rollback**: drop the two tables; revert the search repo joins. Worker
write is idempotent so leftover rows are harmless even before drop.

---

### Step 6 — A2: query decomposition

For queries with ≥ 2 tokens, decompose into a structured shape (parsed
once at a single boundary in `search_service.py`) and try combinations
where token *i* matches artist and token *j* matches album/track. Clamp
to ≤ 3 tokens / ≤ 6 combinations.

**Verification**:
```
pytest tests/integration/test_search_recall_gate.py -v
# Expected: Hit@5 on the multi-token subset improves to ≥ 0.9.
```

**Rollback**: revert single file.

---

### Step 7 — E1: `?explain=1` response mode

Add an optional `explain` query param. When set, the response wraps each
row with `{ row, debug: { matched_field, path, similarity, popularity,
rank } }`. Default response shape unchanged. Music openapi regen →
workspace contract → front `pnpm generate:types`
(`feedback-frontend-api-gen-sync`).

**Verification**:
```
curl '<music-prod>/api/music/search/unified?q=...&explain=1' | jq '.debug'
```

**Rollback**: remove the param handler + response wrapper.

---

## Open questions

1. **Spotify fallback boundary** — C1 (manual, status quo) / C4
   (proactive empty-state CTA) / C2 (separate `/unified_with_fallback`
   route). Blocks any future step that wants to soften the DB-only
   boundary. C3 (always parallel DB + Spotify on `/unified`) is rejected
   here as a direct rule #9 violation.
2. **pg_bigm availability on Neon** — Blocks Step 3 onward. Practical
   check: `CREATE EXTENSION pg_bigm` on the test branch. If unavailable,
   Step 3 branches to pg_trgm-with-known-limits or to a side RFC for
   Meilisearch reconsideration.
3. **A1 rollout: feature flag vs UI release window** — Step 4 currently
   defaults to a feature flag. If the writer is fine with an immediate
   ranking shift, flag can be removed.
4. **`search_misses` table** — Deferred to post-baseline. The decision
   is: after Step 2's baseline + Step 4/5 lifts, do we still need a
   table to surface real-world queries that fall outside the fixture,
   or is that question answerable from CloudWatch + fixture review? V10
   precedent says a table is in-bounds if the question is real.
5. **Writer persona vs future reader-facing search** — assumed
   writer-only here. If reader search ships later, B-series ranking
   polish (Top result card, popularity damp) gets reweighted.

## Decisions log

| Date | Decision | Step |
|------|----------|------|
|      |          |      |
