# FEAT-genre-system: Tier-0 genre vocabulary, automated labeling, and the public genre map

- **Status**: draft
- **Owner**: 박지훈
- **Created**: 2026-06-12
- **Plan row**: `plan.md` → FEAT-genre-system
- **Supersedes**: `FEAT-genre-taxonomy` (discarded 2026-06-12 by owner decision; archived to `docs/archive/done/rfcs/`)

---

## Goal

Every artist, album, and track in the catalog carries machine-assigned **tier-0 genres** from a fixed 12-genre English vocabulary, with per-row provenance (`source`) and `confidence` — produced by a pipeline with **zero human labeling work**. A public **`/genres` page** presents the taxonomy as the magazine's editorial stance: each genre node carries an owner-editable definition text (stored in DB, edited in-place by the logged-in owner). `/reviews` filters on real genre data instead of the current artist-copy fake, and the AI editorial facts pipeline (`derive_subject_meta`) consumes real album genres.

## Vocabulary (fixed, owner-confirmed 2026-06-12)

`Pop · K-Pop · Latin · Hip-Hop · R&B-Soul · Rock · Electronic · Jazz · Classical · Folk-Country · Soundtrack · World-Other`

- English labels only (no `label_ko`).
- **K-Pop = idol-industry category** (production system), not nationality. Korean rap/ballad by non-idol artists is NOT K-Pop. **No formal boundary definition is maintained** (owner decision) — edge cases (e.g. IU-type soloists) are absorbed by LLM judgment + `confidence=low` + future editorial layers, mirroring industry practice (no platform defines idol-ness; Apple inherits label claims, Melon avoids the category domestically, Pitchfork files K-pop under Pop/R&B).
- Multi-attach allowed (e.g. K-Pop + Hip-Hop). Ballad/Trot are NOT top-level (Melon-convention rejected); ballads map to Pop.
- **Final lock 2026-06-12 (after cross-platform survey)**: City Pop demoted from top-level → future sub-genre under Pop (S1 `시티 팝` strings map to Pop until the tier-1 RFC); **Latin promoted to top-level** (present in Discogs/Apple/Deezer/Billboard/AllMusic; absorbs 라틴/레게톤/쿰비아/살사/RKT/turreo strings previously routed to World-Other). Reggae/afro/traditional stay in World-Other.

## Non-goals

- **Sub-genre (tier-1) vocabulary + writer picker** — separate brainstorm + RFC (owner 2026-06-12). The `genres.parent_id` column ships now so tier-1 attaches later without migration; `post_genres` (the editorial review-level layer) belongs to that RFC. **Machine tier-0 (`album_genres`) and editorial sub-genres are separate stores by design — humans never edit `album_genres`.**
- **Music search genre filter** — rejected by owner (2026-06-12).
- **/profile genre stats charts** — stays in `FEAT-genre-artist-distribution` (this RFC unblocks it).
- **Genre relations / influence edges** (genealogy graph) — only the 2-tier tree is canonical; the `/genres` visualization renders the tree, nothing more.
- **Deezer / Last.fm / Wikidata / MusicBrainz as genre sources** — benchmarked 2026-06-12 and rejected on measured evidence (see Evidence). MB alias fill in the worker continues unchanged (search aliases, unrelated to genre).
- **Authoring/tree-management UI** — only definition editing on `/genres` + a JWT create route. No rename/merge/delete management (future work if ever needed).

## Current state

- The only genre data is `artists.genres` (JSONB, ko-KR-localized Spotify strings; 335 distinct strings, top: 한국 랩 361 / K-발라드 128 / 케이팝 76 / 클래식 57). Worker writes it with `locale=ko_KR` (`myblog_worker/worker/service/sync_service.py:237,247`). **23% of albums (227/978) have artists with no genre strings at all.**
- Albums/tracks have **no genre columns**. "Album genres" in published frontmatter are fake: `myblog_backend/app/services/content_sync.py` `derive_subject_meta()` copies the primary artist's strings.
- `/reviews` filter (`myblog_front/src/lib/reviews.ts`, `components/reviews/ReviewsIndex.tsx`) reads `musicReview.genres[]` with fallback to the section label — i.e. it filters on fake data.
- **No UPC/ISRC stored anywhere** (verified by grep). Spotify `GET /albums` + `GET /tracks` (grandfathered) return them — probed 2026-06-12: UPC 85/85, ISRC 215/215 on a stratified sample. `Album`/`Track`/`Artist` already have `ext_refs JSONB` hooks.
- Front has unrouted genre visualization spikes: `myblog_front/src/components/genres/*` (`GenreGraphSample`, `GenreClusterMap`, `GenreConstellation`, `GenreDetailPanel`, `GenreMapTabs`), `lib/genres-sample.ts`, `styles/genres.css`, `pages/genres/index.astro` (not routed/guarded).
- shared_db latest migration **V16 (`album_research`)**, version **0.16.0** → genres migration = **V17** (re-verify next-free at Step 1; plan.md previously said V16 — stale, corrected in this PR).
- Published posts currently: 0 (post-STAB-5 reset) → frontmatter genre semantics can change with zero re-publish cost.

## Evidence — source benchmark (2026-06-12)

Stratified sample: 85 albums + 215 tracks (segments incl. 12 zero-genre albums, 8 OST/compilations, 5 city pop = entire prod population). Full method + raw caches were session artifacts; numbers condensed here.

| Source | Coverage | Precision proxy* | Verdict |
|---|---|---|---|
| S1 Spotify strings (owned) | 70/85 (zero-genre segment 0/12) | 91% | **Keep** — deterministic mapping, rules cover 98.2% weighted of 335 strings |
| iTunes Search by UPC | 79/85, **zero-genre 12/12** | 85% | **Keep** — the one external anchor; label-declared supply-chain data; no key needed. KR storefront for album genre; US storefront for per-song genres (KR ignores `entity=song`) |
| LLM (`claude -p`, metadata-only) | 85/85 | 88% | **Keep** — fallback + arbitration; beat the rule system on idol detection (correctly rejected 빈지노/에디킴/오혁 false positives) |
| Deezer by UPC | 63/85 | 70% (noisiest) | Reject — fills 1 album beyond S1+iTunes |
| MusicBrainz | genre-bearing 15/85 | 93% | Reject as genre source (K-sparse) |
| Last.fm (owner key) | albums 18/85, **track tags 1/215** | 97% | Reject — per-track hypothesis dead on this catalog |
| Wikidata | 39/85; idol class caught BTS only | 95% | Reject |

*agreement with leave-one-out majority (no human ground truth by design).

Key measured facts driving the design:
1. **S1+iTunes = 84/85; +LLM = 85/85.** Three parts suffice.
2. **Track deviation 14/140 — all 14 in one album (BTS WORLD OST); 0% elsewhere** → tracks inherit album genres; only OST/compilations get a per-song exception pass.
3. Voting across Spotify/iTunes/Deezer overstates independence — they share label-supplied upstream metadata. Fewer, better-understood sources beat a vote.
4. External "K-Pop" values mean *Korean mainstream pop* (iTunes tagged 21/85 incl. non-idols) — **K-Pop votes from sources never attach directly; they only trigger LLM idol arbitration; non-idol → Pop.**

## Target state

### Data model (shared_db, V17)

```sql
CREATE TABLE IF NOT EXISTS genres (
  id            UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  slug          TEXT        NOT NULL UNIQUE,          -- 'k-pop', 'rnb-soul'
  label         TEXT        NOT NULL,                 -- 'K-Pop' (English only)
  parent_id     UUID        REFERENCES genres(id) ON DELETE RESTRICT,  -- NULL = tier-0; tier-1 RFC uses this later
  definition_md TEXT        NOT NULL DEFAULT '',      -- owner-edited on /genres (exemplar albums live inside the markdown)
  position      INTEGER     NOT NULL DEFAULT 0,       -- display order on /genres
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS album_genres (
  album_id   UUID NOT NULL REFERENCES albums(id) ON DELETE CASCADE,
  genre_id   UUID NOT NULL REFERENCES genres(id) ON DELETE RESTRICT,
  source     TEXT NOT NULL,                           -- 'mapping' | 'itunes' | 'llm'  (no 'manual' — machine-only by design)
  confidence TEXT NOT NULL DEFAULT 'high',            -- 'high' (2+ part agreement) | 'low' (singleton)
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (album_id, genre_id)
);
CREATE TABLE IF NOT EXISTS track_genres (             -- override-only; row exists ⇔ track deviates from album
  track_id   UUID NOT NULL REFERENCES tracks(id) ON DELETE CASCADE,
  genre_id   UUID NOT NULL REFERENCES genres(id) ON DELETE RESTRICT,
  source     TEXT NOT NULL,
  confidence TEXT NOT NULL DEFAULT 'high',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (track_id, genre_id)
);
```

Seed = the 12 tier-0 rows (`source` of truth for slugs/labels lives in the migration). Effective track genre = `track_genres` if any rows else album's. Artist genre = derived view over their albums (no artist_genres table; compute in queries).

UPC/ISRC land in existing `ext_refs` JSONB (`albums.ext_refs.upc`, `tracks.ext_refs.isrc`) — no migration needed for keys.

### Labeling pipeline (3 parts, zero human)

```
[S1]  artists.genres strings ──static mapping (ko→12-vocab rules, 98.2% weighted)──▶ candidate genres
[S2]  album UPC ──iTunes lookup (KR storefront)──▶ candidate genre
[S3]  LLM (claude -p, $0 poller pattern) ──▶ (a) albums with zero S1+S2 signal
                                              (b) K-Pop idol arbitration (definition one-liner in prompt; label string as evidence)
                                              (c) S1↔S2 conflict arbitration
confidence: 2+ parts agree = high; singleton = low. K-Pop never attaches without (b) passing.
OST/compilation albums (album_type='compilation' OR title ~OST): iTunes US storefront per-song pass → track_genres.
LLM output validated against the closed 12-vocab whitelist (prompt-injection containment).
```

- **Backfill (one-shot, local script)**: UPC/ISRC backfill (~150 Spotify calls) → label all ~978 albums (~1,000 iTunes calls, throttled) → `--dry-run` report → human go/no-go gate (gate is on *running the prod write*, not on labels) → execute.
- **Ongoing**: worker stores `external_ids` into `ext_refs` at sync (zero extra calls) and applies the deterministic S1 mapping inline; iTunes+LLM enrichment for new albums runs through the existing $0 poller (launchd) in `--incremental` mode. No Lambda-side external genre calls; no user-facing endpoint ever calls out (hard rule #9 intact).
- Mapping rules (ko→12-vocab) live in shared_db as data+helper so the worker, backfill script, and backend share one implementation.

### Backend API (myblog_backend)

| Method | Path | Purpose | Auth |
|---|---|---|---|
| GET | `/api/genres/tree` | tree + definitions for `/genres` page and pickers | edge_guard (catch-all, no infra change) |
| POST | `/api/genres` | create node (future tier-1 use) | **Cognito JWT** — copy `buckets_post` pattern (NOT `categories_post`) |
| PUT | `/api/genres/{id}` | edit `definition_md` / `label` / `position` | **Cognito JWT** — same pattern |

`GenreService` follows `bucket_service` style (ORM + typed exceptions). Contract: backend `openapi.json` regen → workspace merge → front `pnpm generate:types` (workspace merges first — `reference-workspace-contract-merge-order`).

### Frontend (myblog_front)

- **`/genres` (public)**: renders the 12 nodes (reuse/adapt the existing spike components — cluster/constellation view of the 2-tier tree) + per-node `definition_md`. Logged-in owner sees an inline edit affordance per node → PUT via `apiFetch`. Public reads go through CloudFront (X-Origin-Verify injected — `reference-front-all-traffic-via-cloudfront`).
- **`/reviews`**: filter + card chips keep reading `musicReview.genres[]` frontmatter — which becomes real because `derive_subject_meta` swaps to `album_genres` (high-confidence rows). 0 published posts → no re-publish migration needed.

## Steps

Each step independently mergeable. Hard rule #4 — one step per session, prod-observe gate between steps. Per-repo branches (`feedback-nested-repo-branch-per-repo`).

### Step 0 — This RFC + discard old + plan.md sync (docs-only, this PR)

New RFC; `FEAT-genre-taxonomy.md` → `docs/archive/done/rfcs/` with discard note; `docs/rfcs/README.md` + `docs/plan.md` rows replaced (incl. stale V16 → V17 correction; `FEAT-genre-artist-distribution` dependency repointed here).

**Verification**: docs review; `git diff --stat`.

### Step 1 — shared_db V17: genres + album_genres + track_genres + seed

`migrations/V17__genres.sql` (DDL above + 12 seed rows), `models.py` (`Genre`, `AlbumGenre`, `TrackGenre`), `_generated_schema.sql` regen, canonical `docs/contracts/schema.sql` sync, version bump (0.17.0 — re-verify next-free V/version at execution).

**Rollout (CRITICAL — `reference-shared-db-cross-repo-rollout`)**: apply V17 to prod Neon **before** merging; `\dt genres` confirm; then merge + tag.

**Verification**:
```
cd myblog_shared_db && pytest
psql "$TEST_DB_URL" -f migrations/V17__genres.sql -v ON_ERROR_STOP=1   # idempotent re-apply clean
```
**Rollback**: `DROP TABLE track_genres, album_genres, genres;` (additive; prod DROP needs human approval — rule #3).

### Step 2 — shared_db mapping module + worker ext_refs capture — **DONE 2026-06-12**

shared_db: `genre_mapping.py` (ko→12-vocab rules from the bench, weighted coverage test ≥98%). worker: store `external_ids` → `albums.ext_refs.upc` during sync (the album response carries it — zero new calls); apply S1 mapping → `album_genres(source='mapping')` for new albums; pin bump.

**Drift correction (found at execution)**: track ISRC is NOT capturable at sync with zero calls — album-nested tracks are `SimplifiedTrackObject` without `external_ids` (the bench's ISRC 215/215 probe used separate `GET /tracks` calls). Track ISRCs move wholly to the Step 3 backfill `--keys` mode (which was already going to fetch them for the existing catalog; new-album ISRCs ride the poller `--incremental` pass when the OST/compilation per-song exception needs them).

**Shipped**: shared_db PR #27 → v0.18.0 (98.2% weighted coverage on the frozen 335-string dump, identical to bench; K-Pop arbitration gate in `attachable_labels/attachable_slugs`; Latin rule ordered before the reggae rule — `레게톤` contains `레게`, the bench ordering silently routed reggaeton strings to World-Other). worker PR #44 (UPC capture; ext_refs replace→merge `||` + `jsonb_strip_nulls` so re-syncs can't clobber backfilled keys; S1 inline mapping with `confidence='low'` singletons; pin v0.2.2→v0.18.0). Prod e2e: candidates→SQS→worker on Bad Bunny — 3 albums synced, all with `ext_refs.upc`, all attached `latin/mapping/low`.

**Verification** (as run):
```
cd myblog_shared_db && pytest tests/test_genre_mapping.py   # 31 passed; coverage 1607/1636 weighted = 98.2%
cd myblog_worker && pytest                                   # 189 passed, 3 skipped (real-engine — feedback-sa-session-lifecycle-mock-blind)
```
**Rollback**: revert worker pin; mapping module is inert without callers.

### Step 3 — backfill run (script + prod execution, human-gated) — **DONE 2026-06-12**

`myblog_shared_db/scripts/backfill_genres.py` — modes: `--keys` (UPC/ISRC via Spotify, ~150 calls), `--label` (S1+iTunes+LLM per pipeline above), `--dry-run` (default; prints label table + distribution sanity + unmapped log, writes nothing), `--execute` (BEGIN/COMMIT, idempotent `ON CONFLICT DO NOTHING`), `--incremental` (poller mode). Run dry-run → owner reviews the *run* (not labels) → execute against prod.

**Shipped (shared_db PR #28 → v0.18.1)**: full-catalog dry-run (982 albums — catalog grew from 978) reviewed by owner → `--execute`: **982/982 albums labeled, 1,552 album_genres rows (high 845 / low 707), 32 track_genres overrides, UPC 979, ISRC 7,335 tracks; all gates pass** (max share Hip-Hop 49.3% < 50%, World-Other 3.4% < 15%, zero-label 0). LLM arbitrated 376 albums, 0 failures; track overrides landed exactly on the bench-predicted set (BTS WORLD OST / BTS THE BEST / Little Women OST). Implementation deltas found at execution: (a) `--execute` replays a reviewed `decisions.json` (cache-replayable runs) rather than relabeling, so what the owner reviewed is byte-what gets written; (b) upsert is `ON CONFLICT DO UPDATE` upgrading confidence low→high only (never downgrades/rewrites source) — required so the pass corroborates worker inline S1 rows; (c) processed-marker = `albums.ext_refs.genre_pipeline` (incremental selection key); (d) dry-run review caught `클래식 록/클래식 소울/클래식 컨트리/바로크 팝` mapping to Classical (classic-X ≠ classical music) → explicit overrides in genre_mapping **v0.18.1** (worker pin bump to v0.18.1 pending); (e) per-call iTunes throttle 3.5s, LLM chunks 4-way parallel.

**Verification** (as run, 2026-06-12):
```
python scripts/backfill_genres.py                  # dry-run ×3 (cache-replayed); gates ALL PASS
psql "$DATABASE_URL" -c "SELECT g.label, count(*) FROM album_genres ag JOIN genres g ON g.id=ag.genre_id GROUP BY 1 ORDER BY 2 DESC;"
psql "$DATABASE_URL" -c "SELECT count(DISTINCT album_id) FROM album_genres;"   # 982 == albums count ✓
python scripts/backfill_genres.py --incremental    # post-execute: "nothing to process" ✓
```
**Rollback**: `DELETE FROM track_genres; DELETE FROM album_genres; UPDATE albums SET ext_refs = ext_refs - 'genre_pipeline';` (= all rows, v1).

### Step 4 — backend genres API + infra + contract — **DONE 2026-06-12**

`app/api/routes/genres.py` (GET tree / POST / PUT), `GenreService`, schemas, `infra/apigateway.tf` `genres_post` + `genres_put` (copy `buckets_post`; **never** `categories_post`), `openapi.json` regen, tests. Then workspace contract merge PR.

**Shipped**: backend PR #64 (`GenreService` bucket-style; `GET /api/genres/tree` public via edge_guard catch-all; `POST`/`PUT /api/genres/{genre_id}` Cognito-JWT; shared_db pin `v0.16.0 → v0.18.1`; openapi regen; 15 tests). Workspace PR #321 (`genres_post`+`genres_put` JWT routes; merged contract) — **merged first** so the backend post-merge `notify-contract` dispatch was a no-op (no stale auto-PR). Human-approved `terraform apply` after merge: 2 routes added, 0 change/destroy. Implementation notes: PUT mutates `label`/`definition_md`/`position` only (slug/parent_id owner-stable, no rename/delete UI per non-goals); `list_tree` assembles the 2-tier forest in Python (no recursive CTE).

**Verification** (as run, 2026-06-12):
```
cd myblog_backend && pyright app/                 # 0 errors (CI runs pyright + openapi-verify, NOT pytest)
.venv/bin/pytest tests/api/test_genres.py tests/test_genre_service.py   # 15 passed
cd infra && terraform plan                         # 2 add (genres_post/put), 0 change/destroy — no drift
python tools/merge_openapi.py && git diff --stat docs/contracts/openapi.json
```
Prod smoke (post-deploy + apply): `GET /api/genres/tree` → 200, 12 tier-0 seeds in position order (Latin@3, no City Pop); `POST`/`PUT /api/genres*` no-token → **401** (authorizer gating; control route → 404). Authenticated write happy-path deferred to Step 7's browser edit-save-reload DoD (avoids a stray prod genre row — no DELETE route by design).

**Rollback**: revert router include + infra entries (`terraform apply` removes the 2 routes); tables untouched (Step 1 scope).

### Step 5 — backend `derive_subject_meta` swap (F8) — **DONE 2026-06-13**

`content_sync.py`: frontmatter `musicReview.genres[]` ← album's `album_genres` labels (12-vocab English), shared by both the publish route and restore re-publish.

**Drift correction (found at execution — `feedback-rfc-current-state-audit`)**: the "should not happen post-Step 3" assumption was **wrong**. Prod `album_genres`: 713/983 albums have a high-confidence row, **269 are low-only** (all carrying real 12-vocab English labels), 1 album has no rows. Strict high-only + artist-copy fallback would have reverted 27% of the catalog to the fake ko-KR Spotify strings and broken Step 6's real-genre filter. **Owner decision 2026-06-13: high-first, else the album's own low rows; artist-copy stays a last-resort fallback only for an album with zero `album_genres` rows.** (Consistent with open-Q4: low rows stay hidden whenever a high row exists; they surface only when there is no high row at all.)

**Shipped (backend PR #65)**: `_album_genre_labels(db, album_id)` helper — one query (`Genre.label`+`AlbumGenre.confidence` joined, ordered by `Genre.position`), high rows preferred, else all (low) rows. `derive_subject_meta` consumes it; artist-copy retained as the zero-rows fallback. No contract change (internal frontmatter, not an API schema) → no `openapi.json` regen. 0 published posts → `derive_subject_meta` does not run at runtime, so there is no live frontmatter to prod-smoke; unit tests are the effective verification and real output validates on the owner's first publish.

**Verification** (as run, 2026-06-13):
```
cd myblog_backend && .venv/bin/pytest tests/api/test_unpublish.py   # 18 passed (real-genre / low-only / artist-copy fallback / high-first selector)
.venv/bin/pyright app/services/content_sync.py                       # 0 errors (CI gate; CI runs pyright + openapi-verify, NOT pytest)
```
(Full-suite has 13 pre-existing failures — `reference-backend-test-config-import-collection` collection-order config-cache pollution, identical on a clean tree; not introduced here. The RFC's `-k content_sync` selector matches no test name — the tests live in `test_unpublish.py::TestDeriveSubjectMeta`/`TestAlbumGenreLabels`.)

**Rollback**: revert to artist-copy derivation (pure function swap).

### Step 6 — front `/reviews` real filter + genre chips (F5)

`pnpm generate:types` + commit `api.gen.ts`; `reviews.ts` drops the section-label fallback (real genres now guaranteed); filter rail + card chips verified in a real browser (DoD).

**Verification**:
```
cd myblog_front && pnpm lint && pnpm exec astro check
# browser click-through: filter by Hip-Hop → only hip-hop reviews; chips render English labels
```
**Rollback**: revert front PR (display-only).

### Step 7 — front `/genres` public page + owner inline edit (F3)

Route `pages/genres/index.astro` (public, no guard) + adapt spike components to the real tree from `GET /api/genres/tree`; logged-in edit affordance → `PUT /api/genres/{id}` via `apiFetch`. Design via `frontend-design` skill. Browser click-through incl. edit-save-reload persistence.

**Verification**:
```
cd myblog_front && pnpm lint && pnpm exec astro check
# browser: public render logged-out; logged-in edit → save → reload persists; 15+ nodes layout sanity
```
**Rollback**: remove page/components (no other screen depends).

## Open questions

1. ~~**(Step 3)** Incremental labeling cadence — fold into the existing research poller launchd schedule vs separate timer~~ — resolved 2026-06-12 (owner): **separate launchd plist, daily 09:30** (`scripts/com.myblog.genre-backfill.plist`, installed + loaded; research poller untouched — different venv, cadence, kill switch).
2. **(Step 7)** Which spike visualization to productionize (cluster map vs constellation vs plate) — decide with `frontend-design` at execution; tree data model is view-agnostic.
3. ~~**(Step 1)** Re-verify V17/0.17.0 next-free at execution~~ — resolved 2026-06-12: V17/0.17.0 confirmed next-free and shipped.
4. **(post-v1)** When the tier-1 RFC lands, revisit whether `confidence=low` rows should surface on `/reviews` chips or stay filter-only.

## Decisions log

| Date | Decision | Step |
|---|---|---|
| 2026-06-12 | Unit: track-level via album inheritance + OST/compilation per-song exceptions (bench: deviation 14/140, all in 1 OST) — owner + evidence | — |
| 2026-06-12 | Vocabulary: 12 tier-0, English labels only; Melon conventions (Ballad/Trot) dropped; City Pop top-level — owner | — |
| 2026-06-12 | **Vocabulary final lock after cross-platform survey (Pitchfork/Discogs/RYM/Apple/Deezer/Billboard/AllMusic/Melon): City Pop demoted → future Pop sub-genre; Latin promoted to top-level** — owner | — |
| 2026-06-12 | K-Pop = idol-industry category; **no formal boundary definition** (LLM judgment + low-confidence + revisability) — owner | — |
| 2026-06-12 | Tier-0 labeling = zero human; pipeline minimized to S1 mapping + iTunes + LLM after 7-source benchmark (Deezer/Last.fm/Wikidata/MB rejected on measured evidence) — owner + evidence | — |
| 2026-06-12 | External K-Pop votes never attach directly — idol arbitration only; non-idol → Pop | — |
| 2026-06-12 | Machine layer (`album_genres`) and editorial layer are separate stores; no `source='manual'` in album_genres — owner | — |
| 2026-06-12 | Music search genre filter rejected; sub-genre vocab + writer picker split to a future RFC — owner | — |
| 2026-06-12 | `/genres` public; definitions stored in DB (`definition_md`) with owner inline edit (no separate admin/authoring UI) — owner | — |
| 2026-06-12 | First front consumer after data = `/reviews` real filter — owner | — |
| 2026-06-12 | `FEAT-genre-taxonomy` discarded (authoring-first approach superseded by labeling-first) — owner | 0 |
| 2026-06-12 | Step 1 executed: V17/0.17.0 re-verified next-free; Current-state claims re-audited against code (all held); test-branch idempotent re-apply ×2 clean; prod-applied before merge (shared_db PR #26 → v0.17.0). Workspace `docs/contracts/schema.sql` found stale at V15 → V16 backfilled in the same sync | 1 |
| 2026-06-12 | Step 2 executed (shared_db #27 → v0.18.0, worker #44): track ISRC dropped from sync scope — album-nested tracks carry no `external_ids` (RFC drift, corrected; ISRC → Step 3 `--keys`/`--incremental`). ext_refs upsert switched replace→merge (`\|\|` + strip_nulls). S1 inline attach = `confidence='low'` singletons; K-Pop gate enforced in shared helper. Prod e2e: Bad Bunny ×3 → upc + `latin/mapping/low` | 2 |
| 2026-06-12 | Step 3 executed (shared_db #28 → v0.18.1): owner reviewed full dry-run → `--execute` — 982/982 albums, 1,552 rows, gates ALL PASS. Dry-run review caught classic-not-classical strings (`클래식 록` et al → AC/DC in Classical) → v0.18.1 explicit overrides; worker pin bump pending. Execute replays reviewed `decisions.json`; upsert upgrades low→high only; processed marker `ext_refs.genre_pipeline`. Incremental cadence resolved: separate daily plist (09:30), not the research poller — owner | 3 |
| 2026-06-12 | Step 4 executed (backend #64, workspace #321): genres API — public `GET /tree`, JWT `POST`/`PUT`. Merge-order: workspace first → backend notify-contract no-op (no stale auto-PR). Human-approved `terraform apply` post-merge (2 routes, no drift). Prod smoke: tree 200/12 seeds; POST/PUT no-token 401. PUT scoped to label/definition/position (no rename/delete). Auth write happy-path → Step 7 browser DoD | 4 |
| 2026-06-13 | Step 5 executed (backend #65): `derive_subject_meta` swapped artist-copy → real `album_genres`. Audit corrected the "zero-high should not happen" drift: prod = high 713 / low-only **269** / no-rows 1. Owner chose **high-first, else the album's own low rows** (artist-copy only at zero rows) — strict high-only would have reverted 27% of the catalog to fake ko-KR + broken Step 6's filter. No contract change. 0 published posts → no runtime invocation to prod-smoke; unit tests (18) are the verification | 5 |
