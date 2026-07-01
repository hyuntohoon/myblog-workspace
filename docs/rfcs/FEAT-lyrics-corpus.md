# FEAT-lyrics-corpus: Private, correctness-first lyrics corpus

- **Status**: accepted
- **Owner**: 박지훈
- **Created**: 2026-07-01
- **Plan row**: `plan.md` → FEAT-lyrics-corpus

---

## Goal

After this RFC, the project has a **private, single-owner lyrics corpus** attached to tracks that
already exist in its own catalog, built **correctness-first, not coverage-first**. Lyrics are
collected from **LRCLIB** (plain + synced where available), matched to our tracks only when the
evidence is strong enough to be safe, and stored as **internal research data that never appears in
any public catalog API, public page, search result, or shared response**. Ambiguous, weak, or
conflicting matches are **left unresolved / review-required rather than matched incorrectly**. A
track that cannot be resolved today can be **re-evaluated later** as source coverage and our own
catalog grow, and a lyric already matched is **never silently replaced** without stronger evidence.
Translation, slang/meme analysis, interpretation, and album-level lyrical analysis are **explicitly
out of scope** — this RFC builds only the trustworthy corpus those later capabilities will stand on.

## Non-goals

Anti-scope-creep insurance. Each is a **separate, later** RFC/step, explicitly **not** here:

- **Any consumer of the lyrics.** No translation, no Korean rendering, no slang/meme/context
  research, no per-track interpretation, no album-level lyrical analysis. This RFC produces the
  corpus and its trust metadata; nothing reads it for a user-facing purpose.
- **Any public exposure.** Lyrics do **not** enter `/api/music/*` responses, `TrackItem`, public
  pages, the unified search index, buckets, posts, or any shared/edge-cached response. This mirrors
  the existing private-data precedent (`artists.aliases` / `artists.musicbrainz_id` are stored but
  never in a public schema; `album_research` is owner-only research text).
- **Public redistribution of lyrics.** The corpus is private research data. This RFC does not build
  a lyrics viewer, export, or any surface that republishes third-party lyric text.
- **lyrics.ovh integration.** Excluded from this scope entirely (instability + romanizes Korean +
  no album/version/duration metadata to match on — see the feasibility research).
- **New catalog ingestion.** This RFC does not add albums/tracks/artists to the catalog. It only
  evaluates and enriches **tracks already present in this project's database**.
- **Treating any source as ground truth for facts.** LRCLIB lyric text is crowd-sourced with mixed
  provenance; it is stored for private research, never asserted as authoritative.

## Current state

Verified against code in the feasibility research (2026-07-01):

- **Track model** (`myblog_shared_db/.../models.py:270`): `Track` has `title`, `track_no`,
  `duration_sec` (**seconds**, not ms), `spotify_id` (UNIQUE, the catalog idempotency key),
  `ext_refs` (JSONB, effectively empty). **No** `isrc`, **no** recording MBID, **no** disc number,
  **no** explicit flag, **no** version/subtitle/disambiguation column — remix / live / demo / edit /
  remaster / rerecording are distinguished only by the **`title` string** plus distinct `spotify_id`.
- **Artist model** (`models.py:167`): `aliases` (JSONB) and `musicbrainz_id` (+ `'not_found'`
  sentinel + partial-unique index) exist and are **stored but not publicly exposed** — used
  server-side only to widen search matching (`artist_repo.py`). `track_artists.role` (free-text)
  exists for featured/credit modeling but is under-used.
- **No lyrics column or table exists anywhere.** The closest precedent for private owner-only
  research text is `album_research` (`models.py:1063`) — Korean markdown keyed by
  `(album_id, prompt_version)`, album-scoped, not exposed publicly.
- **Ownership**: the **worker** is the sole live writer of catalog tables
  (`myblog_worker/.../sync_service.py`, `ON CONFLICT (spotify_id)` upsert). Music and backend are
  read-only on the catalog. Any corpus-building write job therefore belongs in the **worker**.
- **Reusable enrichment pattern**: the MusicBrainz **alias-fill** job (EventBridge, not SQS) is the
  template for a periodic external-enrichment job — select N rows lacking the field, call the
  external source, **commit per row, write a sentinel on miss** so the row leaves the pool, isolate
  failures so an external outage never blocks album sync. `_request_with_retry` (429/5xx backoff,
  `Retry-After`) and `musicbrainzngs` at `set_rate_limit(1.0)` already exist.
- **Sources (live-probed, primary)**: LRCLIB serves real plain + synced lyrics for both English and
  Korean tracks, flags instrumentals (`instrumental:true`), and publishes a **full SQLite dump
  (~28.6 GiB compressed, refreshed ~weekly, `lrclib.net/db-dumps`)** enabling offline bulk matching
  with no rate limit. Its `albumName` field is unreliable. MusicBrainz supplies structured artist
  aliases (IU → 아이유 / 이지은 / Lee Ji-eun) and recording length/disambiguation but **no lyric
  text**. lyrics.ovh is unstable and romanizes Korean.

## Target state

A **private corpus** that associates each evaluated catalog track with, at most, one **matched**
lyric record (plain + synced where available) **or** an explicit **unresolved-state** record, plus
the **evidence and confidence** behind that outcome. Concretely, at the principle level (detailed
schema, columns, and any endpoint deferred to step-time — see Non-goals + Open questions):

- **A private, track-scoped lyrics store**, owner-only, following the `album_research` / `aliases`
  privacy precedent — never joined into a public response. Holds the lyric text (plain + synced),
  the source + source record id, and the match evidence/confidence used.
- **A match-status lifecycle per evaluated track**, reusing the alias-fill sentinel idea:
  - `matched` — high-confidence, lyric attached.
  - `no_lyrics` — source has the track but it is instrumental / genuinely has no lyrics.
  - `not_found` — no candidate in the source at all (leaves the active pool; re-checkable later).
  - `ambiguous` — multiple plausible candidates that evidence cannot separate → **not matched**.
  - `review_required` — a candidate exists but confidence is below the auto-attach bar → **not
    matched**, queued for owner decision.
  A track is **never** auto-attached out of `ambiguous` / `review_required`; those are safer
  resting states than a wrong match.
- **Matching evidence, in priority order**: (1) **artist identity** resolved through
  `artists.aliases` + MusicBrainz aliases (transliteration / punctuation / localized / credited
  names); (2) **normalized track title**; (3) **`duration_sec` within a tight tolerance** (feasibility
  probe: LRCLIB gates `/api/get` on duration within a few seconds); (4) **ISRC** as a strong
  identity/version anchor — **added to `Track` in Step 1** (OQ5 resolved: adopt now, not deferred);
  (5) MusicBrainz **recording +
  disambiguation + length** as version evidence. **Album name is a weak signal only — never a hard
  match key** (LRCLIB `albumName` was empirically junk: `""`, `"TravisScottVEVO"`, etc.).
- **Version safety**: remix / live / demo / edit / cover / remaster / rerecording are **never
  silently merged**. A candidate whose version evidence (duration, disambiguation, version tokens in
  the title) does not agree with our track is downgraded to `ambiguous` / `review_required`, not
  attached.
- **Periodic local LRCLIB processing** against the **~28.6 GiB dump**, run **locally / as a bounded
  batch** (Lambda is unsuitable at that size; precedent: the existing local `claude -p` / launchd
  jobs). The batch **only ever evaluates tracks already in this project's database** — it iterates
  our catalog and looks each track up in the dump, never the reverse (it does not import the dump's
  catalog). Only match outcomes + accepted lyric text land in the DB.
- **Incremental collection** for **newly ingested** tracks, following the alias-fill worker pattern
  (select recently-added tracks lacking a corpus record, evaluate, commit per row + sentinel).
- **Periodic reassessment** of `not_found` / `ambiguous` / `review_required` (and previously
  unmatched) tracks, because new releases and source coverage change over time — a re-check that can
  *promote* an outcome but, under the replacement rule below, does not *downgrade or overwrite* a
  good match without stronger evidence.
- **Replacement policy**: a track already `matched` is **never silently replaced**. A re-evaluation
  may only replace an existing lyric when it presents **strictly stronger evidence** (e.g. an ISRC or
  MusicBrainz recording match supersedes a title+duration match); otherwise the existing match stands
  and any competing candidate is recorded as review evidence, not applied.

### Source trust boundary

- **LRCLIB** — the **only lyric-text source** (primary). Crowd-sourced, mixed provenance →
  **untrusted for factual correctness**, stored for **private research use only**, never
  redistributed, never asserted as authoritative. Its structural signals (duration, instrumental
  flag) are usable for matching; its `albumName` is not.
- **MusicBrainz** — **identity + version evidence only**, never a lyric source. Higher trust for
  structured identity (aliases, recording length, disambiguation) at 1 req/s.
- **lyrics.ovh** — excluded.

### Privacy boundary

Lyrics are **owner-only internal research data**. No path — API schema, public page, search index,
bucket, post, edge-cached response — exposes lyric text or its presence. Enforcement mirrors the
existing pattern where `aliases` / `musicbrainz_id` are read server-side but excluded from every
public schema. A pre-merge check that no public schema/response gained a lyrics field is an
acceptance gate (see below).

## Steps

Milestone-level. Hard rule #4 — one step per session, prod-observe / direction-recheck gate between
steps. Detailed schema/endpoint/DDL design is produced **at the start of each step**, reviewed, and
not pre-committed here (per RFC scope: correctness principles now, implementation later).
Branch/commit per repo (`feedback-nested-repo-branch-per-repo`).

### Step 0 — RFC + plan.md pointer (this document, docs-only)

This RFC + a one-line `plan.md` Backlog pointer + the `docs/rfcs/README.md` index entry. No code,
no schema.

**Verification**: doc review against `TEMPLATE.md` / README required sections. `git diff --stat`
shows only the three doc files.

---

### Step 1 — private corpus store + match-status model + ISRC column (shared_db, schema-only)

Introduce the **private, track-scoped lyrics store + match-status lifecycle** (states above) as a
`shared_db` migration, owner-only, with **no public exposure and no consumer**. Schema detail
designed at step start. Nothing writes to the lyrics store yet; this step lands the storage + status
vocabulary and confirms the privacy boundary holds (no public schema references it).

Per **OQ5 (resolved: adopt ISRC now)**, this step **also** adds the **additive `Track.isrc` column**
as an identity/version anchor — schema only, **no writer** (consistent with "storage only, nothing
writes yet"). ISRC is **server-side identity evidence only** — same privacy precedent as `aliases` /
`musicbrainz_id`, **not** exposed in any public schema/response. **Populating** `isrc` is deferred to
**Step 1b** (below): a mechanism check (2026-07-01) found isrc **cannot** ride the album-sync path —
`sync_service.py:99` documents that album-nested tracks are Spotify `SimplifiedTrackObject`s with
**no `external_ids`**, and `spotify_client.py` has only `get_albums`/`get_artists`, **no
`get_tracks`** — so population is non-trivial worker code and is kept out of this schema-only step.
Step 1 is therefore a **single-repo (`shared_db`), purely additive** migration.

**Verification**: migration applies cleanly on a test branch; a schema check confirms no public
API/response type references the lyrics store or `isrc`; `pytest` for shared_db parity passes
(`reference-shared-db-test-pythonpath-src`); `_generated_schema.sql` / canonical schema regenerated.

**Rollback**: drop the lyrics store + `isrc` column (no consumer depends on either yet).

---

### Step 1b — ISRC population (worker: `get_tracks` fetch + bounded backfill)

Populate the `Track.isrc` column added in Step 1. Adds a new `GET /v1/tracks?ids=` client method
(≤50/call, reads `external_ids.isrc`) and a **bounded backfill job** over existing tracks lacking
isrc (chunk 50, per-batch commit, alias-fill failure-isolation pattern). Going-forward population for
newly ingested tracks rides the same `get_tracks` path (a follow-up full-track fetch after album
sync, since the album path lacks track `external_ids`). Worker-only; the writer-bearing half of the
ISRC adoption, split from Step 1 so the schema step stays additive/no-writer (hard rule #4).

**Verification**: `get_tracks` returns `external_ids.isrc` on a stubbed response; backfill dry-run on
a bounded sample writes isrc for tracks that have one and a sentinel (design at step start) for
tracks Spotify returns without one; no impact on album sync; worker `pytest` passes.

**Rollback**: disable the backfill job; the `isrc` column stays but unpopulated (no consumer depends
on it until Step 2).

---

### Step 2 — offline LRCLIB dump matcher (historical backfill, local batch)

A **local, bounded batch** that downloads/refreshes the LRCLIB dump and, **iterating only tracks
already in our catalog**, computes match outcomes (artist-alias + normalized title + duration
tolerance; album ignored) and writes `matched` / `no_lyrics` / `not_found` / `ambiguous` /
`review_required` + evidence/confidence. Conservative thresholds: **auto-attach only above a high
confidence bar; everything else parks in a non-matching state.** Runs locally (dump size unfit for
Lambda), writing only outcomes + accepted lyric text to the DB.

**Verification**: run over a **representative labelled sample of N catalog tracks** (Korean +
English + hard cases: aliases, non-Latin, featured, same-title, remix, live, rerelease, likely-missing)
and report the six metrics below; **auto-match precision ≥ target and version-conflict false-match
count = 0** on the sample before any full run. Manual audit of a random slice of `matched`.

**Rollback**: outcomes are additive per track; clear the corpus rows produced by the batch.

**Phase 1 result (2026-07-01, N=100 random prod catalog, read-only, LRCLIB `/api/search`)**:
matched 39 · no_lyrics 4 · not_found 39 · ambiguous 18 · review_required 0. Coverage
(matched+no_lyrics)/total = 43%; ambiguous_rate 18%. **Consistency gate PASS** (0 inconsistent
matched). **Precision audit of all 39 `matched` (denom = 39): 39/39 correct → 100%** — every row
had duration Δ ≤ 1s vs the LRCLIB candidate and artist identity matched; the 5 version-token rows
(Queen ×2 "Remastered 2011", Liam Gallagher / BIGBANG "Live", McCartney "Full Length") were all
same-version → same-version (no cross-version merge). **Version-conflict false-match count = 0.**
→ Phase 1 gate (precision ≥ bar, version-conflict = 0) **met**; Phase 2 (full dump batch) is the
next step (rule #4 — separate session). Audit JSON is local-only (gitignored; contains lyric snippets).

**Phase 2 result (2026-07-02, full catalog = 20,946 tracks, all written to `track_lyrics`)**:
The **local LRCLIB dump could not be used** — the current dump is **30.68 GiB gzip**
(`db-dumps.lrclib.net/lrclib-db-dump-20260624T025818Z.sqlite3.gz`; the RFC's `lrclib.net/lrclib.db`
URL is a stale SPA page) which **decompresses to >60 GiB** against **~54 GiB free disk**. Owner
approved (2026-07-02) running the **same canonical matcher over the LRCLIB `/api/search` API** for
the full backfill instead of the dump (identical `decide_match` logic + written outcomes; the dump
would only have avoided per-request latency). `/api/search` is ~8 s/request server-side, so
`tools/lyrics_batch_api.py` fetches candidates across a thread pool (`decide_match` + writes stay
single-threaded), resumable per-row. **Concurrency finding**: LRCLIB caps effective throughput at
~2.5 req/s — **30 workers** was optimal (~0.5% transient-skip); 60 hit ~30% throttle-skip with no
good-throughput gain (100 would be strictly worse), so higher concurrency is pointless, not a win.

**Outcomes**: matched **7,955 (38.0%)** · no_lyrics **417 (2.0%)** · not_found **9,798 (46.8%)** ·
ambiguous **2,743 (13.1%)** · review_required **33 (0.2%)** (denominator = 20,946 evaluated).
Resolved coverage (matched+no_lyrics)/eval = **40.0%**; synced (LRC) present on **7,253 / 7,955**
matched (91%). **Consistency gate PASS** (inconsistent matched = 0). **Version-conflicts detected &
parked = 13; version-conflict false-match count = 0** (every remix/live/remaster/instrumental
candidate parked to `review_required`, never auto-attached). **Precision audit: 25 random `matched`
(denom = 7,955) all correct (title + artist identity, duration Δ ≤ 2 s)** → with Phase 1's 39/39 =
**64/64 = 100%** audited. **Acceptance gate (precision ≥ 99%, version-conflict = 0) MET.** Three
latent `TrackLyricsWriter` bugs were found + fixed mid-run (JSONB dict bind → `CAST(:evidence AS
jsonb)` + `json.dumps`; `matched`-with-only-synced → `lyric_plain` None→'' for the V33 CHECK;
embedded NUL in LRCLIB crowd data → `_strip_nul`) — myblog_worker writer PR. Phase 2 report is
local-only (gitignored; lyric snippets). → **Step 2 DONE**; Step 3 (worker incremental) next
(rule #4 — separate session).

---

### Step 3 — incremental collection for newly ingested tracks (worker)

A periodic **worker** job (alias-fill pattern: EventBridge job string, select recently-added tracks
lacking a corpus record, evaluate via the LRCLIB **API** for freshness, commit per row + sentinel on
miss, failure-isolated so a source outage never blocks album sync). Same conservative matcher and
states as Step 2. API (not dump) because increments are small and need current data.

**Verification**: job processes a bounded batch on a test run; per-row commit + sentinel behavior
observed; the six metrics on the incremental cohort; no impact on album sync latency.

**Rollback**: disable the job (no catalog write path depends on it).

**Implementation (2026-07-02, pending merge + prod verify)**: new worker
`LyricsIncrementalService` (`worker/service/lyrics_incremental_service.py`) + `LrclibClient`
(`worker/clients/lrclib_client.py`), routed by `handler.py` on `{"job":"lyrics_incremental"}`
(same pattern as `album_ingest` / `isrc_backfill`) and scheduled by a new EventBridge rule
`worker-lyrics-incremental` (`rate(12 hours)`, `infra/eventbridge.tf`). Selects recently-added
tracks (`created_at DESC`) lacking a `track_lyrics` row — the row itself is the sentinel that
drops a track from the pool — evaluates each via LRCLIB `/api/search` with the **same canonical
`decide_match`** as Step 2, and writes one outcome per row (`TrackLyricsWriter`, per-row commit).
**Failure isolation**: transient LRCLIB errors (network/5xx/429, retried then raised as
`LrclibTransientError`) *skip* the track (unwritten → retried next run, never poisoned as
`not_found`); this is a separate Lambda invocation from the SQS album path, so a lyrics-source
outage can never block album sync. **Bounded to the 120s worker timeout** by
`settings.LYRICS_INCR_BATCH_LIMIT` (150) + a `LYRICS_INCR_TIME_BUDGET_SEC` (90s) wall-clock guard
+ `LYRICS_INCR_CONCURRENCY` (20, ≈ LRCLIB's ~2.5 req/s cap per the Phase 2 finding); an
over-budget run leaves leftovers for the next tick (per-row commits make it resumable). A matched
outcome with `version_agrees=False` (impossible by construction) is guarded — logged + not
written. Tests (DB-free): `tests/test_lyrics_incremental.py` (12) + 2 handler-routing tests; full
worker suite 238 passed / 34 skipped. Live LRCLIB `/api/search` smoke confirmed the contract
(no-match → `[]` → `not_found`, no exception). `terraform plan`: 3 to add, 0 change, 0 destroy.

---

### Step 4 — periodic reassessment + replacement guard

A periodic re-check of `not_found` / `ambiguous` / `review_required` / previously-unmatched tracks
(coverage changes over time), enforcing the **replacement policy**: may *promote* an unresolved
track to `matched`, may replace an existing match **only on strictly stronger evidence**, and
**never silently overwrites** a good match. Ambiguity that persists stays parked.

**Verification**: on a seeded set of previously-unresolved tracks, confirm promotions happen and
that a weaker competing candidate does **not** replace an existing match; version-conflict
false-match count stays 0.

**Rollback**: disable the reassessment schedule; existing outcomes untouched.

---

## Metrics (denominators explicit)

Evaluated on a labelled representative sample and tracked on each run:

1. **Auto-match precision** — of tracks auto-attached (`matched`), the fraction whose lyric is
   *correct for that exact track/version* under manual audit. *Denominator = auto-`matched` count.*
   Primary gate.
2. **Auto-match coverage** — fraction of evaluated tracks that reached `matched`.
   *Denominator = all evaluated tracks.* (Reported, **not** maximized — never at precision's expense.)
3. **Review-required rate** — fraction ending in `review_required`.
   *Denominator = all evaluated tracks.*
4. **Unresolved / no-lyrics rate** — fraction in `not_found` + `no_lyrics`.
   *Denominator = all evaluated tracks.* (`not_found` and `no_lyrics` reported separately too.)
5. **Version-conflict false-match count** — absolute number of audited cases where a wrong *version*
   (remix / live / demo / edit / cover / remaster / rerecording) was attached. **Target = 0.**
6. **Source-quality conflict rate** — fraction of `matched` where the lyric text is internally
   suspect (e.g. romanized where original-script expected, truncated, or two sources disagree).
   *Denominator = auto-`matched` count.*

## Risks

- **False-match on popular tracks** — crowd DBs carry many near-duplicate/junk uploads at slightly
  different durations; the duration gate loosens on popular titles. Mitigation: tight tolerance +
  version-token check + park-on-ambiguity.
- **Album name unreliability** — designed around (album never a hard key).
- **Provenance / legal** — mixed-source crowd text kept strictly private-research; no public
  redistribution; explicit owner acceptance of that boundary required.
- **Missing identity anchors** — no ISRC / recording MBID on tracks today weakens hardest cases
  (same-title different-artist, covers). Open question below.
- **Dump size / operational** — ~28.6 GiB local batch; must stay local and bounded (not Lambda).
- **Silent corpus drift** — mitigated by the replacement guard (Step 4) + never-overwrite rule.

## Open questions

1. **Storage shape (blocks Step 1)** — dedicated private track-scoped table vs an extension of an
   existing structure. Recommend a **dedicated private table** (mirrors `album_research`). Confirm.
2. **Acquisition mode (blocks Step 2/3)** — recommend **both**: bulk dump for historical backfill
   (Step 2) + API for increments (Step 3). Confirm the split, and confirm the dump batch runs
   **local-only** (claude -p / launchd precedent), writing only outcomes to the DB.
3. **Auto-attach thresholds (blocks Step 2)** — duration tolerance (proposed tight, ±~2s), title
   normalization rules, and the confidence bar above which we auto-attach vs park. Owner sets the
   precision-vs-coverage bar; default bias = **precision**. **RESOLVED (2026-07-01, direction only —
   exact numbers still tuned at Step 2 with the labelled sample)**: keep the **auto-attach bar
   conservative** (artist-identity via aliases AND normalized-title exact match AND duration within a
   tight tolerance AND no version-token conflict → `matched`; anything short → park); precision and
   the ≥99% / version-conflict=0 acceptance gate are **unchanged**. Coverage is grown through the
   **`review_required` queue**, not by loosening auto-attach: a weak-but-present candidate is parked
   in `review_required` (owner can manually accept) rather than discarded to `not_found`. The review
   queue is the coverage lever; auto-attach stays precision-first.
4. **synced (LRC) storage (blocks Step 1)** — store both plain **and** synced where available
   (confirmed direction) — confirm no size/handling concern.
5. **ISRC adoption (optional, affects hardest cases)** — Spotify track objects expose
   `external_ids.isrc`; storing it during catalog sync would give a strong identity/version anchor
   (and enable the MusicBrainz-recording cross-check). **RESOLVED (2026-07-01): adopt now — fold
   `Track.isrc` into Step 1** (shared_db column + worker `sync_service` populate from
   `external_ids.isrc` + bounded backfill), server-side identity evidence only, never publicly
   exposed. The matcher gets the anchor from day one on covers / same-title / remaster cases.
6. **Provenance/legal boundary (blocks acceptance)** — explicit owner sign-off that crowd-sourced
   lyric text is stored for **private research only**, never redistributed publicly. **RESOLVED
   (2026-07-01): owner signed off** — lyrics are single-owner private research data, never in any
   public API/page/search/shared/edge-cached response, never redistributed, never asserted as
   authoritative; residual legal risk accepted.
7. **Review-required surface** — how the owner reviews the `review_required` queue (minimal owner-only
   list vs deferred). Kept intentionally out of implementation detail here.

## Acceptance criteria

- On the labelled representative sample: **auto-match precision ≥ the owner-set bar** (proposed
  ≥ 99%) with **version-conflict false-match count = 0**.
- Every ambiguous/weak case demonstrably parks in `ambiguous` / `review_required` and is **never**
  auto-attached.
- **No public schema or response** references or exposes lyric text or its presence (privacy gate).
- A previously-unresolved track can be promoted on re-check; a `matched` track is **not** replaced
  without strictly stronger evidence (replacement guard).
- All six metrics reported per run with denominators.

## No-go conditions

- Conservative matcher cannot hold precision at the bar (persistent false matches / version
  bleed) → **halt auto-attach; corpus becomes review-only** (manual owner decisions).
- LRCLIB dump/service access or licensing turns out to be unusable even for private research → the
  feature is **shelved**.
- Any design lands lyric text (or its presence) in a public API, page, or search response → **design
  rejected** (privacy boundary is non-negotiable).

## Relationship to later work

This RFC deliberately stops at a **trustworthy corpus + trust metadata**. Translation, slang/meme /
context research, per-track interpretation, and album-level lyrical analysis are **each a separate
later RFC** that consumes this corpus. Keeping construction and analysis separate is the same
discipline used by FEAT-ai-editorial-critique (build/prove the grounded substrate before any
consumer).

## Decisions log

Filled in during execution.

| Date | Decision | Step |
|------|----------|------|
| 2026-07-01 | Corpus is correctness-first, private, single-owner; lyrics never in any public API/page/search/shared response (aliases / album_research privacy precedent) | 0 |
| 2026-07-01 | LRCLIB = only lyric-text source (primary); MusicBrainz = identity/version evidence only; lyrics.ovh excluded | 0 |
| 2026-07-01 | Album name is never a hard match key; evidence = artist identity+aliases, normalized title, duration tolerance, ISRC where available, MB recording/version | 0 |
| 2026-07-01 | Never silently merge remix/live/demo/edit/cover/remaster/rerecording; park ambiguity as ambiguous/review_required rather than mismatch | 0 |
| 2026-07-01 | Periodic local dump batch evaluates only tracks already in this DB; never imports the dump's catalog | 0 |
| 2026-07-01 | Previously matched lyric never silently replaced — only on strictly stronger evidence | 0 |
| 2026-07-01 | Translation / slang-meme / interpretation / album-level analysis explicitly out of scope (later RFCs) | 0 |
| 2026-07-01 | OQ6 resolved — owner sign-off: lyrics are private single-owner research data, never public/redistributed, residual legal risk accepted | 0 |
| 2026-07-01 | OQ5 resolved — adopt ISRC now: `Track.isrc` folded into Step 1 (shared_db col + worker populate + backfill), server-side identity evidence only, never public | 1 |
| 2026-07-01 | OQ3 resolved (direction) — auto-attach bar stays conservative/precision-first (acceptance gate unchanged); coverage grown via the `review_required` queue, not by loosening auto-attach; exact numbers tuned at Step 2 | 2 |
| 2026-07-01 | Status draft → accepted | 0 |
| 2026-07-02 | Phase 2 ran via LRCLIB `/api/search` (not the dump): 30.68 GiB gz dump decompresses >60 GiB vs ~54 GiB free disk; same matcher + outcomes, dump only avoids latency (owner-approved) | 2 |
| 2026-07-02 | Concurrency ceiling = LRCLIB, not local HW: effective ~2.5 req/s; 30 workers optimal, 60 → ~30% throttle-skip, higher is pointless | 2 |
| 2026-07-02 | Step 2 DONE — 20,946 tracks: matched 38.0% / no_lyrics 2.0% / not_found 46.8% / ambiguous 13.1% / review_required 0.2%; consistency PASS, version-conflict false-match 0, precision 64/64=100% audited (gate MET) | 2 |
| 2026-07-02 | Step 3 implemented (worker) — `lyrics_incremental` EventBridge job (`rate(12 hours)`), alias-fill pattern: recently-added tracks lacking a `track_lyrics` row → LRCLIB `/api/search` → same `decide_match` → per-row commit + sentinel; transient errors skip (never `not_found`), separate invocation isolates album sync; bounded by batch-limit(150)+time-budget(90s)+concurrency(20) for the 120s Lambda. Pending merge + prod verify | 3 |
