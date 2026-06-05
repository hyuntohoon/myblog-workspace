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
written. The recommended direction below already reflects that critique.

**2026-06-05 empirical correction (OQ2 resolved):** the brainstorm picked
pg_bigm over pg_trgm for Korean. Live probing of the actual prod engine
(Neon Postgres 17) inverted both halves of that premise — pg_bigm is **not
installable on Neon** (not in `neon.allowed_extensions`; `pg_search`/ParadeDB
is deprecated too), and pg_trgm **does work on Korean** on this build:
`show_trgm('방탄소년단')` yields 6 syllable-level trigrams and
`similarity('방탄','방탄소년단') = 0.286`. The matching extension is therefore
**pg_trgm**, no external engine needed. See the Decisions log for scores.

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
  pg_trgm (GIN trigram index accelerating the existing ILIKE substring
  match + `similarity()` for fuzzy ranking / typo tolerance). pg_bigm was
  the brainstorm pick but is unavailable on Neon (OQ2). Multi-token
  queries (artist + album/track combined) return results.
- `album_aliases` + `track_aliases` tables exist in shared_db; worker
  populates them from MusicBrainz release/recording aliases.
- Writer-facing input handles IME composition (no Enter-mid-composition
  phantom searches).
- `?explain=1` query mode returns per-row debug fields
  (`matched_field`, `path`, `similarity`, `popularity`, rank) for dev
  triage. Default response shape unchanged.

## Steps

### Step 1 — D1: IME compose handling (front) ✅ DONE (2026-06-05)

> ✅ Done 2026-06-05 — PR `hyuntohoon/myblog_front#90`, merge SHA `9b7305c`.
> Guarded `onSearchKeyDown` with `e.nativeEvent.isComposing` (the keyCode 229
> fallback was dropped — it tripped a deprecation hint and `isComposing` covers
> the modern path). Manual IME click-through deferred (can't simulate headless).

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

### Step 2 — E2: Fixture set + Hit@K gate ✅ DONE (2026-06-05)

> ✅ Done 2026-06-05 — PR `hyuntohoon/myblog_music#35`, merge SHA `cbd3195`.
> **Baseline (read-only against the prod catalog): Hit@5 = 18/30 = 0.600,
> Hit@1 = 18/30 = 0.600.** The 12 misses are exactly the later-step gaps: all 8
> multi-token (no decomposition → Step 6) and all 4 typo (ILIKE substring can't
> span a one-edit typo → Step 4 pg_trgm `similarity()`). korean / common-word /
> artist-alias (18/18) already pass. Gate is `@pytest.mark.integration` +
> `RECALL_GATE_DB_URL`/`TEST_DB_URL`-gated → excluded from CI (`pytest -m "not
> integration"`), so the failing baseline does not block the build.

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

### Step 3 — A1 PoC: extension selection on Neon ✅ DONE (2026-06-05)

**Resolved.** Probed the prod engine (Neon PG17) directly via `$TEST_DB_URL`:

- `pg_bigm`: **not available** — not in `pg_available_extensions`; `CREATE
  EXTENSION pg_bigm` → "not in the allowed extensions list".
- `pg_search` (ParadeDB BM25): **deprecated, not allowed**.
- `pg_trgm`: **available and working on Korean** — `similarity('방탄',
  '방탄소년단') = 0.286`, `'소년단'↔'방탄소년단' = 0.25`,
  `show_trgm('방탄소년단')` = 6 syllable trigrams, `show_trgm('봄날')` = 3.
- Also available if ever needed: `rum`, `vector` (pgvector). External engine
  (Meilisearch) **not** needed.

**Decision: pg_trgm.** Caveat captured for Step 4 — the default
`pg_trgm.similarity_threshold` is 0.3, and `'방탄'↔'방탄소년단'` scores
0.286, *below* it. So the `%` operator alone would miss it. The plan is
therefore to keep ILIKE substring semantics (accelerated by a
`gin_trgm_ops` index) and use `similarity()` only for ranking/typo, rather
than swapping ILIKE for the `%` operator wholesale.

**Rollback**: n/a — probe extensions were dropped, test branch restored.

---

### Step 4 — A1 implementation (shared_db V12 + music repos) ✅ DONE (2026-06-05)

> ✅ Done 2026-06-05 — shared_db `#20` (`32baccd`, tag `v0.11.0`), music `#36`
> (`c65f26c`), infra flag-on `#236` (`7f87a09`). **V12 applied to prod Neon, flag
> flipped on (`terraform apply`, 1 change). Recall gate against the prod catalog:
> 0.600 → 1.000 (Hit@5 = Hit@1 = 30/30) — RFC goal met.** Prod smoke: typo
> `방탕소년단`→방탄소년단, `Radiohad`→Radiohead; exact/alias/multi-token all
> correct, no regression.
>
> Deviations from the step as written, with reasons:
> - **No backend/worker pin bump** (and no music pin bump): V12 adds no ORM
>   column — only the extension + GIN indexes — and `similarity()` is raw SQL, so
>   no service gains a model dependency at V12. Per the necessity gate, a pin bump
>   with no model delta is pure churn; it lands in Step 5 (V13 alias models) where
>   music actually needs the new tables. (GIN index *declarations* were still added
>   to `models.py` for schema-parity, but they're inert at runtime.)
> - **pg_trgm fuzzy fallback also fixed all multi-token cases** (query trigrams
>   overlap the title's), so the gate hit 1.000 without Step 6 decomposition. The
>   RFC goal is therefore met at Step 4; Steps 5–7 are additive capability beyond
>   the goal metric (see Decisions log).
> - **No hybrid `similarity × log1p(views)` track score**: kept the existing
>   `views DESC` ordering inside the substring tier (preserves passing cases) with
>   similarity only as the fuzzy-tail signal + tiebreaker. The gate passed 30/30,
>   so the hybrid wasn't needed to clear the goal.

Per Step 3, the extension is **pg_trgm**.

> **Migration numbering (2026-06-05 deconfliction)**: V12 (pg_trgm, this step)
> + V13 (album/track aliases, Step 5) are this RFC's. `FEAT-genre-taxonomy`'s
> genres migration was renumbered V12 → **V14** to avoid the collision; its V14
> applies after this RFC's V12/V13 (hand-numbered `V{N}__` must apply
> contiguously — `reference-shared-db-cross-repo-rollout`).

- shared_db V12: `CREATE EXTENSION pg_trgm` + `gin_trgm_ops` GIN indexes on
  `artists.name`, `albums.title`, `tracks.title`.
- bump shared_db version; apply to prod Neon BEFORE service pin bumps
  (`reference-shared-db-cross-repo-rollout`).
- pin bump in `myblog_music`, `myblog_backend`, `myblog_worker` to keep
  schema consistent (extensions are global to the database; even
  services that don't query the search columns must reference the new
  pin).
- **keep** `ILIKE '%q%'` substring semantics (now index-accelerated by the
  trgm GIN index) and add `similarity()` to the ORDER BY for fuzzy / typo
  ranking. Do NOT swap ILIKE for the `%` operator — the default 0.3
  threshold drops valid prefix matches (Step 3 caveat: `'방탄'` = 0.286).
  If a fuzzy-only path is wanted for true typos, use a lowered
  `set_limit()` / `word_similarity` explicitly, measured against the gate.
- track ranking: do not blindly replace `views DESC, created_at DESC` —
  consider a hybrid score (`similarity × log1p(views)`) so cold catalog
  items do not displace engagement-strong ones.
- ship behind a feature flag (`SEARCH_USE_PG_TRGM=true`) for one
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

- shared_db V13: `album_aliases (album_id, alias)` +
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

1. ~~**Spotify fallback boundary**~~ — **RESOLVED 2026-06-05: C1 (manual,
   status quo).** `/unified` stays DB-only with the existing manual toggle;
   no fallback work in this RFC. C4 (empty-state CTA) / C2 (separate route)
   deferred to a future RFC if writer demand appears. C3 stays rejected
   (rule #9).
2. ~~**pg_bigm availability on Neon**~~ — **RESOLVED 2026-06-05.** pg_bigm
   not allowed on Neon; pg_trgm available and works on Korean (syllable
   trigrams). Direction = pg_trgm, no external engine. See Step 3 + Decisions.
3. ~~**A1 rollout: feature flag vs UI release window**~~ — **RESOLVED
   2026-06-05: feature flag** (`SEARCH_USE_PG_TRGM`) for one deploy cycle,
   A/B'd via the fixture gate, off-switch on regression. Step 4 keeps the
   flag as written.
4. **`search_misses` table** — Deferred to post-baseline. The decision
   is: after Step 2's baseline + Step 4/5 lifts, do we still need a
   table to surface real-world queries that fall outside the fixture,
   or is that question answerable from CloudWatch + fixture review? V10
   precedent says a table is in-bounds if the question is real.
5. ~~**Writer persona vs future reader-facing search**~~ — **RESOLVED
   2026-06-05: keep reader in mind.** Execution stays writer-only (scope
   unchanged), but ranking choices in Step 4/6 should avoid writer-only
   assumptions that would block a later reader-facing surface — i.e.
   prefer readable, popularity-aware ordering over raw-similarity ordering
   where the two diverge. A dedicated reader-search RFC still owns the
   B-series polish (Top result card, popularity damp).

## Decisions log

| Date | Decision | Step |
|------|----------|------|
| 2026-06-05 | OQ2 resolved by live probe of Neon PG17 (`$TEST_DB_URL`): **pg_bigm not installable** (not in `neon.allowed_extensions`), `pg_search` deprecated → **pg_trgm chosen**. pg_trgm works on Korean: `similarity('방탄','방탄소년단')=0.286`, `'소년단'↔'방탄소년단'=0.25`, `show_trgm('방탄소년단')`=6 trigrams. Caveat: 0.286 < default 0.3 threshold → keep ILIKE (trgm-GIN-accelerated) + similarity for ranking, don't swap to `%` operator. Probe extensions dropped, test branch restored. | 3 |
| 2026-06-05 | OQ1 = **C1 (status quo)**: `/unified` stays DB-only + manual toggle; Spotify fallback (C4/C2) deferred to a later RFC. | — |
| 2026-06-05 | OQ3 = **feature flag** (`SEARCH_USE_PG_TRGM`) for one deploy cycle, A/B'd via fixture gate. | 4 |
| 2026-06-05 | OQ5 = **keep reader in mind**: execution writer-only, but prefer readable/popularity-aware ordering over raw-similarity where they diverge; reader-search RFC owns B-series polish. | 4/6 |
| 2026-06-05 | shared_db migration V12 collision with `FEAT-genre-taxonomy` resolved: this RFC keeps **V12** (pg_trgm) + **V13** (aliases, plan.md reservation); genre-taxonomy renumbers genres → V14. | 4 |
| 2026-06-05 | **Gate DB source = `RECALL_GATE_DB_URL` (fallback `TEST_DB_URL`), read-only.** TEST_DB (Neon test branch) is *not* a current mirror of prod (250/124/660 rows vs prod 1046/697/4883; prod ids absent), so a prod-id fixture can't run there. The recall gate only reads (no seeding) → point it at the prod catalog read-only for a true baseline; expected-id-absent cases degrade to data-misses, not recall failures. | 2 |
| 2026-06-05 | **Step 2 baseline recorded: Hit@5 = Hit@1 = 0.600 (18/30).** Misses = 8 multi-token + 4 typo (the Step 6 / Step 4 gaps). korean/common-word/artist-alias already pass. Fixture uses real prod ids; alias category currently tests *artist* aliases only (album/track alias cases arrive with Step 5 V13 data). | 2 |
| 2026-06-05 | **No pin bump at Step 4** (necessity gate): V12 adds no ORM column (extension + GIN indexes only) and `similarity()` is raw SQL → no service gains a model dependency; pin bump deferred to Step 5 (V13 alias models). | 4 |
| 2026-06-05 | **RFC goal MET at Step 4: Hit@5 = Hit@1 = 1.000 (30/30), prod-verified + flag live.** pg_trgm's fuzzy fallback recovered typos *and* multi-token (query trigrams overlap title trigrams) at threshold 0.3, no tuning needed. Steps 5 (album/track aliases), 6 (decomposition), 7 (`?explain=1`) are now **additive capability beyond the goal metric**, not required to hit the target — to be scoped/sequenced by the owner as follow-ons. | 4 |
