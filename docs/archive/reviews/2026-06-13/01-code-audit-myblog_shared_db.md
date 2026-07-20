# Code Audit — myblog_shared_db (2026-06-13)

Repo: `/Users/park_hyun/myblog-workspace/myblog_shared_db`
Scope: shared SQLAlchemy models + plain `V{N}__` SQL migrations (no Alembic runner) + genre scripts. git-pinned per consuming service.
Method: read all source files end-to-end (`models.py`, `tables.py`, `enums.py`, `genre_mapping.py`, `scripts/backfill_genres.py`, all 16 migrations, the 3 test modules, `_generated_schema.sql`, `tests/canonical_schema.sql`, CI workflow), ran the test suite (45 passed), and cross-checked pins in the 3 consumer repos.

## Health read

This is a small, disciplined, mostly-clean repo. The model layer is fully type-annotated (`Mapped[...]`, `py.typed` shipped), migrations are overwhelmingly idempotent and well-documented, version tags track `pyproject` exactly (HEAD == `v0.18.1` tag), and there is a real schema-parity test in CI. The genre mapping module and its tests are genuinely strong (frozen coverage gate, closed-vocabulary guards, K-Pop arbitration logic). The load-bearing problems are concentrated in two places: (1) one real **model↔DB type drift** (`Section.id` modeled as 32-bit `Integer` but the prod column is `BIGSERIAL`) that the parity test structurally cannot catch because it only compares column *names*; and (2) a **stale README** whose install pin and per-service version table are several major versions behind reality. Everything else is lower-severity polish (a non-exported `Tag` model, business logic living in `shared_db`, untested DB/network paths in the backfill script).

## Biggest wins for this repo

1. **Fix `Section.id` Integer→BigInteger** (F1) — the one genuine type bug; SERIAL vs BIGSERIAL drift that silently passes the parity test.
2. **Refresh `README.md`** (F2) — install snippet `@v0.5.0` and the version table are wrong; this is the doc a new consumer copy-pastes from.
3. **Strengthen the parity test to compare column types, not just names** (F3) — F1 is invisible precisely because the test stops at names; this is the systemic fix that would have caught F1.
4. Export `Tag` from the package root (F4) and add a `CHECK`/comment for the open-vocabulary `source`/`confidence` text columns (F7).

---

## Findings (severity-sorted)

### F1 — `Section.id` modeled as 32-bit `Integer` but prod column is `BIGSERIAL` (type drift) — [type-safety, H]

`src/myblog_shared_db/models.py:120`

```python
class Section(Base):
    __tablename__ = "sections"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
```

The generated DDL emits `id SERIAL` (int4):

```
$ grep -iA2 "create table sections" src/myblog_shared_db/_generated_schema.sql
CREATE TABLE sections (
	id SERIAL NOT NULL,
```

But the canonical / prod schema declares it 64-bit, and the FK side already agrees it should be `BIGINT`:

```
$ grep -iA2 "create table if not exists sections" tests/canonical_schema.sql
  id         BIGSERIAL    PRIMARY KEY,
$ grep -in "section_id" tests/canonical_schema.sql
66:  section_id      BIGINT       REFERENCES sections(id) ON DELETE SET NULL,
```

`Post.section_id` is correctly `BigInteger` (`models.py:301-303`), so the model is internally inconsistent: a 64-bit FK pointing at a 32-bit-modeled PK. Functionally harmless today (only 4 seeded rows), but it is a latent correctness bug — any code that introspects `Section.id.type` or relies on the ORM's type to round-trip a value > 2^31 would be wrong, and the model misrepresents the real column.

- **Category:** type-safety
- **Severity:** H (silent type drift on a PK; parity test cannot see it)
- **Fix difficulty:** S
- **Proposal:** change `Section.id` to `mapped_column(BigInteger, primary_key=True)`, regenerate `_generated_schema.sql`, bump version + tag. Cross-check the same Integer-vs-BigInteger choice on every other integer PK (`Tag.id` already uses `BigInteger`, so Section is the lone offender).

---

### F2 — README install pin + version table are several majors stale (v0.5.0 vs actual v0.18.1) — [other/docs, H]

`README.md:10`, `README.md:36-40`

```
$ sed -n '9,11p;36,40p' README.md   (paraphrased)
git+https://github.com/hyuntohoon/myblog_shared_db.git@v0.5.0
| `myblog_backend` | `v0.5.0`    |
| `myblog_music`   | `v0.3.0`    |
| `myblog_worker`  | `v0.2.2`    |
```

Actual consumer pins (read from the three `requirements.txt`):

```
$ grep -rn "myblog_shared_db.git@" myblog_backend myblog_music myblog_worker
myblog_backend/requirements.txt:10:...@v0.18.1
myblog_music/requirements.txt:13:...@v0.3.0
myblog_worker/requirements.txt:7:...@v0.18.1
```

So backend is `v0.18.1` (README says v0.5.0) and worker is `v0.18.1` (README says v0.2.2). Only `myblog_music` (v0.3.0) happens to still match. The install snippet tells a new copy-paste consumer to pin `@v0.5.0`, which predates the entire genre system, the section rename, and album-research. This is the canonical doc for the shared package; being this wrong invites a consumer to silently pin a release missing the tables it needs.

- **Category:** other (documentation accuracy on a shared contract)
- **Severity:** H (misleads cross-repo pin decisions; this is the package's front door)
- **Fix difficulty:** S
- **Proposal:** update the install snippet to the latest tag (or to "pin the latest tag from `git tag`"), regenerate the version table from the live `requirements.txt` of each service, and add a one-line "this table is hand-maintained, verify against each service's requirements.txt" note — or drop the table entirely and point at the per-service pins as the source of truth, since it will always rot.

---

### F3 — schema-parity test compares column *names* only, not types/nullability/PK — [test-gap, M]

`tests/test_schema_parity.py:119-140` (`test_modeled_columns_present_in_canonical`) and `_extract_columns` at `:71-103`

```python
tokens = clause.split()
if tokens:
    result.add(tokens[0].strip('"').lower())   # only the bare column name is kept
```

The test asserts every modeled column name exists in `canonical_schema.sql`, and that `_generated_schema.sql` is byte-fresh after `_normalize` (which lowercases + collapses whitespace). Neither check compares the column *type*, nullability, default, or PK/FK shape against the canonical. That is exactly why F1 (`SERIAL` vs `BIGSERIAL`) sails through CI: both files have a column literally named `id`. The "drift detector" gives false confidence on the dimension most likely to drift silently (types).

Additionally, `test_generated_schema_is_fresh` only proves the committed `_generated_schema.sql` matches what the models emit *today* — it is a models↔models tautology, not a models↔prod check. The only models↔canonical check is the name-only one above.

- **Category:** test-gap
- **Severity:** M
- **Fix difficulty:** M
- **Proposal:** extend `_extract_columns` to capture `(name, normalized_type)` and assert the modeled type matches the canonical type per column (normalizing `SERIAL`→`integer`, `BIGSERIAL`→`bigint`, `TIMESTAMPTZ`→`timestamp with time zone`, etc.). Even a coarse int4/int8/text/uuid/timestamptz bucketing would have caught F1.

---

### F4 — `Tag` model is defined but not exported from the package root — [structure, M]

`src/myblog_shared_db/models.py:130` defines `class Tag`, and `Post.tags` (`models.py:319`) depends on it, but:

```
$ grep -n "Tag" src/myblog_shared_db/__init__.py
(no output — Tag NOT exported)
```

`__init__.py:1-12` re-exports `Section, ReviewBucket, …, Genre, AlbumGenre, TrackGenre` and lists them in `__all__`, but omits `Tag` (and `SpotifyRecentAlbum`, `SpotifyNowPlaying`, `SpotifyPlayEvent`, `SpotifyRecentTrack`). A consumer doing `from myblog_shared_db import Tag` gets an `ImportError`; `from myblog_shared_db.models import Tag` works. The package presents two inconsistent import surfaces. Given STAB-5 Step 4 added review tags as a first-class axis, `Tag` is the most surprising omission.

- **Category:** structure
- **Severity:** M (broken/inconsistent public API surface for a shipped feature)
- **Fix difficulty:** S
- **Proposal:** add `Tag` (and the four Spotify cache models, if backend/worker are meant to import them via the root) to the `__init__.py` imports + `__all__`. Or, decide the root export is curated-on-purpose and document that consumers import the long tail from `.models` — but the current half-and-half is just an oversight.

---

### F5 — genre-classification business logic lives in `shared_db` (not just models) — [structure, M]

`src/myblog_shared_db/genre_mapping.py` (180 lines of mapping rules + arbitration policy) and `scripts/backfill_genres.py` (864 lines: Spotify/iTunes HTTP, `claude -p` subprocess orchestration, prod-write transaction).

The repo's stated charter (`README.md:3`, `pyproject.toml:8`) is "Canonical SQLAlchemy models for the myblog Neon database." `genre_mapping.py` is *shipped in the wheel* (it's under `src/myblog_shared_db/`) and is genuinely shared (the worker imports `attachable_slugs` at `myblog_worker/worker/service/sync_service.py:9`), so it has a defensible reason to live here. But `backfill_genres.py` is a full ETL/LLM pipeline with network I/O, AWS Secrets resolution, and a `--execute` prod-write path (`backfill_genres.py:715-763`) — that is application/operational logic, not schema. It is excluded from the wheel (`[tool.hatch.build.targets.wheel] packages = ["src/myblog_shared_db"]`), so it doesn't ship, but it sits in the "models" repo and is wired to a launchd plist that writes prod daily (`scripts/com.myblog.genre-backfill.plist:33-39`). A schema-definition package now also owns a live prod-mutating cron job.

- **Category:** structure (layering / single-responsibility)
- **Severity:** M
- **Fix difficulty:** L (it's a placement decision with cross-repo blast radius — likely accepted-as-is)
- **Proposal:** keep `genre_mapping.py` here (it's a genuine shared pure function). Consider relocating `backfill_genres.py` + its plist into `myblog_worker` (which already imports the shared mapping and owns the Spotify/EventBridge surface) so the model package stays purely declarative. If staying, add a short "why operational code lives here" note to the README so it isn't mistaken for drift. (guess) The owner may have intentionally co-located it with the mapping module it depends on; flag for confirmation rather than auto-move.

---

### F6 — mapping rules duplicated/forked between `genre_mapping.py` and `backfill_genres.py` — [duplication, M]

`src/myblog_shared_db/genre_mapping.py:125-143` defines `S1_RULES` (Korean→tier-0 regex table) and `S1_EXPLICIT`. `scripts/backfill_genres.py:99-159` re-defines a *parallel* `ITUNES_MAP` + `EN_RULES` table with the same shape and overlapping intent, and `map_itunes` falls back to `map_string` (`backfill_genres.py:169`). The two rule tables encode the same vocabulary lock ("Latin before reggae", "City Pop → Pop") in two places, with the ordering invariant duplicated as comments in both (`genre_mapping.py:11-14` and `backfill_genres.py:138-139, 150-151`).

```
$ grep -c "re.compile" src/myblog_shared_db/genre_mapping.py scripts/backfill_genres.py
genre_mapping.py:1
backfill_genres.py:2
```

This isn't pure copy-paste (S1 is Spotify-string rules, EN_RULES is iTunes-name rules — different inputs), so it's defensible. The risk is the *shared invariant* (the 12-label closed vocabulary + the Latin-before-reggae ordering) being edited in one table and not the other. The tests partly guard this (`test_all_table_outputs_in_vocab`, `test_itunes_map_values_are_valid_labels` both assert outputs ⊆ `LABELS`), so the vocabulary half is protected — but the ordering invariant is not cross-checked.

- **Category:** duplication
- **Severity:** M (low odds, but a silent mis-classification if one table's ordering drifts)
- **Fix difficulty:** M
- **Proposal:** add a test asserting the Latin-rule index < reggae-rule index in *both* `S1_RULES` and `EN_RULES` (the one invariant the comments promise). Longer term, consider whether `EN_RULES`/`ITUNES_MAP` belong in the shared `genre_mapping` module so all genre rules live in one importable place.

---

### F7 — open-vocabulary TEXT columns for `source`/`confidence`/`research.status` have no DB `CHECK` (but `album_research.status` does) — [type-safety, L]

`migrations/V17__genres.sql:52-53` and `models.py:684-685, 702-703`:

```sql
source     TEXT NOT NULL,                           -- 'mapping' | 'itunes' | 'llm'  (no 'manual' …)
confidence TEXT NOT NULL DEFAULT 'high',            -- 'high' … | 'low' …
```

The intended domains are closed (`'mapping'|'itunes'|'llm'` and `'high'|'low'`) and documented only in comments. By contrast `album_research.status` *does* enforce its domain with a `CHECK` (`migrations/V16__album_research.sql:45-46`) and `review_buckets.research_mode` too (`V16:64-65`). So the codebase has an inconsistent convention: some enumerable TEXT columns get a `CHECK`, the genre ones don't. A typo'd `source='itnues'` from a future writer would be silently accepted, defeating the per-row provenance the genre system relies on.

- **Category:** type-safety
- **Severity:** L (machine-only writers today, low blast radius; convention inconsistency)
- **Fix difficulty:** S
- **Proposal:** in a future additive migration add `CHECK (source IN ('mapping','itunes','llm'))` and `CHECK (confidence IN ('high','low'))` on `album_genres`/`track_genres`, matching the `album_research`/`research_mode` precedent. Low priority — note it, don't rush it.

---

### F8 — `scripts/backfill_genres.py` DB/network/LLM paths are untested (only pure logic is) — [test-gap, L]

`tests/test_backfill_genres.py` covers `map_itunes`, `is_ost_or_compilation`, `combine_album`, `extract_json_object`, `norm_title` — the pure functions. Untested: `load_catalog` (the two-query catalog read, `backfill_genres.py:314-362`), `run_execute` (the prod-write transaction with 5 `executemany` blocks, `:715-763`), `fetch_keys`/`fetch_itunes_*` (HTTP), `claude_batch` (subprocess + threading), and `run_label` (the orchestration). The `run_execute` SQL — especially the `ON CONFLICT (album_id, genre_id) DO UPDATE … WHERE album_genres.confidence='low' AND EXCLUDED.confidence='high'` upsert (`:738-741`) that encodes the "never downgrade confidence" invariant — has no test, yet it runs against prod daily via launchd.

This is partly inherent (no local DB on this machine — per the workspace memory) and the script is excluded from the wheel, so it's a lower bar. But the confidence-upsert invariant is exactly the kind of SQL that a real-engine test (SQLite/Postgres in-memory or the Neon test branch) should pin.

- **Category:** test-gap
- **Severity:** L (pure logic is covered; the gap is the I/O glue, hard to unit-test)
- **Fix difficulty:** M
- **Proposal:** add a real-engine integration test (in-memory Postgres or the existing `TEST_DB_URL` Neon test branch the worker already uses) for `run_execute`: seed an album + genre, run with a `low` then a `high` decision, assert the upsert upgrades but never downgrades, and that re-running is a no-op (the idempotency the docstring promises at `:43-46`).

---

### F9 — `combine_album` K-Pop confidence can mis-count when only the LLM voted K-Pop — [error-handling, L]

`scripts/backfill_genres.py:226-232`

```python
if idol and (kpop_voters or llm_voted_kpop):
    votes_n = 1 + len(kpop_voters)  # llm + the source parts that voted
    rows.append({
        "label": "K-Pop",
        "source": "llm",
        "confidence": "high" if votes_n >= 2 else "low",
    })
```

`votes_n` counts `1` (the LLM) plus the *source* parts that originally voted K-Pop. When the LLM independently asserts K-Pop (`llm_voted_kpop=True`) but no source part voted (`kpop_voters=[]`), `votes_n = 1` → `confidence='low'`, which the test `test_llm_kpop_claim_alone_needs_idol_flag` confirms is intended. That case is fine. The subtle part is that `llm_voted_kpop` is in the guard but never contributes to `votes_n` — so it only gates *whether* the row is appended, and confidence is driven purely by `kpop_voters`. This matches all current tests, so it is behaving as specified; the smell is that the variable name `votes_n` ("votes") under-counts the LLM's own K-Pop vote when `llm_voted_kpop` is the sole trigger (the LLM voted, but `votes_n` would still be `1` either way because the `+1` already is the LLM). Net: correct today, but the dual-purpose `kpop_voters`/`llm_voted_kpop` logic is fragile to future edits.

- **Category:** error-handling (correctness robustness, not a live bug)
- **Severity:** L
- **Fix difficulty:** S
- **Proposal:** leave behavior as-is (tests lock it), but add an inline comment clarifying that `llm_voted_kpop` gates *appending* while `kpop_voters` drives *confidence*, and that an LLM-only idol K-Pop is intentionally `low`. Optionally add a test for "idol=True, llm genres include K-Pop, both sources empty" naming the `low` confidence explicitly (currently covered by `test_llm_kpop_claim_alone_needs_idol_flag` but not named for this nuance).

---

### F10 — `http_get_json` swallows non-retryable HTTP errors into a sentinel dict, silently dropping iTunes/Spotify data — [error-handling, L]

`scripts/backfill_genres.py:242-256`

```python
except urllib.error.HTTPError as e:
    if e.code in (403, 429, 500, 502, 503):
        time.sleep(30 * (attempt + 1)); continue
    return {"_error": str(e.code)}
except Exception as e:  # noqa: BLE001
    logger.warning("GET %s failed: %s", url, e)
    time.sleep(5)
```

A non-retryable code (e.g. 404, 400) returns `{"_error": "..."}`, and callers like `fetch_itunes_album` (`:415`) just do `d.get("results") or []` → silently treat it as "no genre" and cache `{"genre": None}` (`:420`). Network exceptions retry up to 4× then fall through to `return {"_error": "retries-exhausted"}` (`:256`). So a transient failure on a key album is indistinguishable from a genuine "iTunes has no entry," and the result is cached, so a later re-run won't retry it. For a $0 best-effort enrichment this is an acceptable design choice, but it means coverage can silently degrade with no signal in the report (the report counts `itunes_name` hits, not fetch failures).

- **Category:** error-handling
- **Severity:** L (best-effort pipeline; acceptable but worth a counter)
- **Fix difficulty:** S
- **Proposal:** surface a `fetch_errors` counter in `build_report` (alongside `unmapped_itunes`) so a run with many `_error` responses is visible, and consider *not* caching `{"genre": None}` when the cause was `_error` vs a genuine empty result (so a re-run retries transient failures).

---

## What is clean (verified, not assumed)

- **Migration idempotency:** every migration except the two intentionally-non-idempotent ones is guarded (`IF NOT EXISTS` / `ON CONFLICT` / `DROP … IF EXISTS`). V13 (`ALTER TABLE categories RENAME TO sections`, `:42-43`) and V5 are necessarily one-shot ALTERs — both are documented as one-time prod applies with explicit human-approval notes; that is correct for a no-runner plain-SQL scheme, not a defect.
- **Version/tag discipline:** `pyproject.toml` `version = "0.18.1"` == `git describe` `v0.18.1` == `git tag --points-at HEAD`. Tags run contiguously v0.0.1→v0.18.1. Clean.
- **Model type annotations:** every model column is `Mapped[...]` + `mapped_column(...)`; `py.typed` is shipped; `from __future__ import annotations` used. Strong.
- **Superseded migration handling:** V7 (`library_items`) is properly dropped by V8 (`:21-22`) — not leftover drift.
- **Bootstrap-table policy honored:** canonical_schema has `outbox_events`, `publishing_runs`, `op_logs`, `post_metrics`, `post_comments`, `post_likes`, `tags`/`post_tags` that aren't all modeled — consistent with the documented "intentional bootstrap tables, not drift" rule; the parity test correctly allows canonical-only tables.
- **Genre mapping tests:** frozen coverage gate (≥98% weighted, `test_weighted_coverage_ge_98`), closed-vocab guards on both the dump and the rule tables, K-Pop arbitration logic, and the Latin-before-reggae ordering all have tests. This module is the strongest-tested part of the repo.
- **Working tree:** clean; `.pytest_cache/` is correctly ignored (auto `.gitignore` inside it); no `.venv`/cache tracked in git.
- **Dependencies:** minimal and bounded — `SQLAlchemy>=2.0,<3` (upper-bounded, good), `pytest>=8` dev-only. No abandoned/duplicated deps. `requires-python>=3.12`. No dependency risk.

## Open questions

- Is `backfill_genres.py` + its launchd plist deliberately co-located in `shared_db` (next to the `genre_mapping` module it imports), or should the operational pipeline move to `myblog_worker`? (F5)
- Is the `__init__.py` export list curated on purpose (only "primary" models) or is `Tag` / the Spotify cache models' omission an oversight? (F4) — assumed oversight for the report.
- Should the README version table be maintained at all, or replaced by a pointer to each service's `requirements.txt` (it will always rot)? (F2)
