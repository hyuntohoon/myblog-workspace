# FEAT-lyrics-annotations: surface "the story behind the lyrics" (Genius) + lyrics-coverage expedite

- **Status**: draft (exploratory capture — 2026-07-25 session; **not yet scoped for execution**)
- **Owner**: 박지훈
- **Created**: 2026-07-25
- **Plan row**: `plan.md` → FEAT-lyrics-annotations (Backlog)

> **Session-capture note.** This RFC is a checkpoint written at the owner's request to freeze a
> 2026-07-25 brainstorm so the next session starts cold without re-deriving. It bundles **two
> related-but-distinct threads** that surfaced together. Neither is committed to build. All
> concrete probe data from the session is preserved verbatim in the *Session findings* appendix so
> a fresh session can trust it without re-querying. Next-session resume order is at the bottom.

---

## Goal

Two threads, one lyrics domain:

- **Thread 1 — "가사 이야기" (lyric annotations).** The owner's actual want (clarified in-session:
  *"목표는 번역이 아닌 가사에 대한 이야기"* — **not** translation, but the *story/meaning/background* of
  the lyrics). Surface human-sourced per-line commentary (samples, references, artist quotes,
  interpretation) alongside the existing lyrics viewer, sourced from **Genius annotations**.
- **Thread 2 — lyrics-text coverage expedite.** A side-discovery: for a brand-new release the owner
  wants to review, the corpus (`track_lyrics`) can sit `not_found` for weeks because the automatic
  backfill is stalest-first over a ~12.5k pool. Consider a way to **add/expedite lyrics for a
  specific album on demand.**

The threads share the lyrics substrate but are independently shippable. They are captured together
only because they emerged from the same conversation.

## Non-goals

- **Translation.** Explicitly out — the owner corrected the framing. `track_lyrics_translations`
  (Sonnet 의역 poller) is untouched. See `docs/archive/done/rfcs/FEAT-lyrics-translation.md`,
  `FEAT-lyrics-engine-sonnet.md`.
- **Genius as a lyrics-TEXT source.** The Genius official API returns metadata + annotations only,
  **never full lyrics text** (publisher-licensing constraint). Getting lyric/translation *text* from
  Genius requires HTML scraping = **ToS violation + fragile + copyright-sensitive**. Ruled out as an
  automated corpus source. (LRCLIB stays the lyrics-text source of truth.)
- **Public exposure of raw lyrics.** Same owner-only privacy bar as `track_lyrics` /
  `track_lyrics_translations` (derivative + license-sensitive). Annotations carry their own license
  (Genius = CC-BY-NC-SA 3.0 → attribution + non-commercial required even for owner-only display).
- **LLM-generated "story."** Feeding lyrics to an LLM to *invent* backstory is out — the whole point
  of Genius is **verified human-sourced** facts. An LLM hybrid (Genius where available, `[source?]`-
  marked LLM elsewhere) is a possible future direction (mirrors the editorial-critique honesty
  pattern) but NOT this RFC's default; flagged in Open Questions only.
- **Committing to build either thread.** This is a draft capture. Promotion needs owner accept +
  (Thread 1) a coverage-probing gate, (Thread 2) a scope decision.

## Current state

_(Audited live 2026-07-25 against the working tree + prod DB + LRCLIB/Genius APIs.)_

### Lyrics corpus + pipeline

- **Corpus**: `track_lyrics` (shared_db `models.py:319`), keyed by `track_id` UUID → `tracks.id`
  (`tracks.spotify_id` is the Spotify link). Columns: `match_status`
  (`matched` / `not_found` / `no_lyrics` / `ambiguous` / `review_required`), `evidence` JSONB
  (carries `reason`, e.g. `no_plausible_candidate`), `lyric_plain`, `lyric_synced`,
  `matcher_version`. Owner-only; served JWT-gated via backend `GET /api/lyrics/{spotify_track_id}`
  (`lyrics_service.py`, own `infra/apigateway.tf` route).
- **Source of truth**: **LRCLIB** (public API, no auth). Matcher tooling: `tools/lyrics_batch_api.py`
  (resumable; `WHERE tl.track_id IS NULL` when `skip_existing`), `tools/lyrics_dump_matcher.py`.
  Reference: `docs/archive/done/rfcs/FEAT-lyrics-corpus.md`, memory `reference-lrclib-bulk-api-ops`.
- **Two EventBridge jobs already exist** (`infra/eventbridge.tf`):
  - `lyrics_incremental` — **every 15 min**, targets tracks with **no** `track_lyrics` row (new
    tracks only). First-pass matching.
  - `lyrics_reassessment` — **rate(1 day)**, re-checks the **unresolved pool**
    (`not_found` / `ambiguous` / `review_required`, **stalest-first**) against current LRCLIB,
    **promote-only + replacement-guarded**. Bounded per run (`LYRICS_REASSESS_BATCH_LIMIT` + wall
    clock). **Cycles the ~12.5k unresolved pool in ~2–3 months.** Worker handler
    `_run_lyrics_reassessment(limit=…)`; manual fire via blogSQS `{"job":"lyrics_reassessment"}`.
  - **Limitation for a specific new album**: stalest-first means a *just-ingested* album is at the
    **back** of the queue → a manual reassessment fire does **not** prioritize it. There is **no
    album-scoped reassessment** today.

### Genius

- **Zero integration.** No code, config, or token anywhere in the repo (grep-confirmed). Using Genius
  needs an owner-created free API client → access token → SSM (SecureString), per
  CHORE-secrets-ssm-migration (no Secrets Manager).
- **API capability**: `/search`, `/songs`, `/referents` (annotations). Annotations ARE returned
  (this is Genius's designed use) → **Thread 1 is API-legal, no scraping.** Full lyrics text is NOT
  returned (→ Non-goals).
- **Coverage risk (unmeasured)**: annotations are dense for popular English hip-hop/pop/rock, **sparse
  for classical (≈0), partial for K-pop (often romanization pages), variable for indie/non-English.**
  The owner's taste (ROSALÍA, classical, K-pop, indie per release-calendar/genre-heal history) skews
  toward the weak-coverage end → **a coverage-probing gate must precede any build.**

## Target state

_Deliberately not fully specified — this is a draft. Sketches only._

- **Thread 1**: a `track_lyric_annotations`-style store (schema TBD) populated from Genius `/referents`
  keyed to `track_id` + a character/line offset, rendered as an opt-in layer in the existing viewer
  (FEAT-lyrics-viewer). English annotations either shown as-is or LLM-translated via the existing
  Sonnet pipeline. Owner-only, attribution-bearing. Manual/GUI-triggered fetch (no synchronous
  external call in a user-facing endpoint — rule #9).
- **Thread 2**: an **album-scoped expedite** — a way to say "re-check *this album's* `not_found`
  tracks against LRCLIB now" (either a small param on the reassessment job, or a one-off local
  matcher run over the album's `track_id`s). Fills tracks the instant LRCLIB has them, instead of
  waiting for the stalest-first sweep.

## Steps

_TBD on promotion. Rough ordering intuition:_

- **Thread 2 is the cheap, legal, immediately-useful one** — likely a small first deliverable
  (album-scoped reassessment or a documented manual re-match recipe).
- **Thread 1 gates on a coverage probe** — Step 0 must be "probe Genius annotation hit-rate over ~20
  of the owner's real tracks; if hit-rate is too low, stop." Only then schema → fetch → viewer.

## Open questions

1. **Genius annotation coverage over the owner's real library** — blocks all of Thread 1. Must probe
   ~20 recently-played/bucketed tracks (incl. classical + K-pop) before any schema/UI work. If
   coverage is thin, Thread 1 may die here.
2. **Annotation language** — show English annotations as-is, or LLM-translate to Korean? Blocks
   Thread 1 viewer step. (Reuse the Sonnet poller vs. inline.)
3. **Thread 2 shape** — album-scoped param on the existing `lyrics_reassessment` job, vs. a one-off
   local matcher script, vs. a GUI "expedite this album" button (parallels the 분류하기 →
   `genre_backfill_requests` on-demand pattern). Blocks Thread 2 Step 1.
4. **LLM-hybrid for annotations** — if Genius coverage is patchy, fill gaps with `[source?]`-marked
   LLM interpretation (editorial-critique honesty pattern)? Or leave gaps empty? Product decision;
   blocks Thread 1 scope.
5. **Should these be two separate RFCs?** They share only the domain. On promotion, consider splitting
   Thread 2 into a `plan.md` row (small, single-repo-ish) and keeping this RFC for Thread 1 only.

## Session findings (2026-07-25) — preserved verbatim so next session trusts them

**Test albums chosen by owner: Charli XCX "Music, Fashion, Film" (2026-07-24, brand new) + "BRAT".**
("music fashion film" turned out to be a real, just-released album in the catalog — not a
mis-transcription.)

Charli XCX catalog lyrics coverage (prod DB, `artists`→`album_artists`→`albums`→`tracks`→`track_lyrics`):

| Album | Release | Tracks | matched | unmatched |
|---|---|---|---|---|
| **BRAT** | 2024-06-07 | 15 | **15** | 0 — fully complete, no gap |
| Brat and it's completely different… | 2024-10-11 | 34 | 29 | 5 |
| **Music, Fashion, Film** | 2026-07-24 | 11 | **3** | **8** |
| (older: Pop 2, Charli, hifn, etc.) | — | — | mostly complete | — |

"Music, Fashion, Film" per-track (the gap the owner cares about):

- **matched (3)**: Rock Music, SS26, Wink Wink — these were pre-released singles → already on LRCLIB.
- **not_found (8)**, all `reason=no_plausible_candidate`: 2007, Camera, Card Declined, I'm Afraid,
  Magic Metal Montana, No One Lasts Forever (feat. David Cronenberg), Persona, Yeah.

LRCLIB re-probe of the 8 unmatched (live, filtered to artist=Charli xcx), 2026-07-25:

- **Camera** → LRCLIB **now has it** (synced + plain, album "Music, Fashion, Film"). Our matcher just
  hasn't re-run since LRCLIB got it → will auto-promote via `lyrics_reassessment` eventually (weeks,
  stalest-first).
- **The other 7** → **0 real hits** on LRCLIB (brand-new, crowd hasn't uploaded). ("2007" only returns
  a false hit "Calabria 2007" from a Boiler Room set.)

**Conclusion**: the gap has two causes — (a) *LRCLIB caught up, our matcher hasn't* (Camera →
expedite fixes now); (b) *LRCLIB genuinely empty* (7 tracks → wait for crowd, days–weeks for a major
artist; or a non-scraping source we don't have). The "add when missing" machinery (`lyrics_reassessment`)
**already exists** — the only real deficiency is **latency / lack of per-album prioritization**.

**Add-method options weighed:**

- **A. Expedite existing reassessment for a specific album** — cheapest, legal, no new source. Camera
  fills immediately; the 7 fill as LRCLIB crowd catches up. Needs album-scoping (absent today). ✅
  recommended for the coverage thread.
- **B. Genius as lyrics-text source** — gets new lyrics fast BUT API withholds text → scraping → ToS.
  ❌ rejected.
- **C. Publish to LRCLIB (their publish API)** — contributes upstream, but chicken-egg: you need the
  correct lyrics to publish. Only viable via owner manual transcription. ❌ not worth it.

## Decisions log

| Date | Decision | Thread |
|------|----------|--------|
| 2026-07-25 | Owner goal is **annotations/"이야기", not translation** | 1 |
| 2026-07-25 | Genius = annotations only (API-legal); **never a lyrics-text source** (scraping/ToS) | both |
| 2026-07-25 | Lyrics-text coverage: **expedite existing reassessment**, not Genius/scrape | 2 |
| 2026-07-25 | RFC created as a **draft session-capture**; no build committed | — |

---

## Next-session resume order

1. Re-read this RFC (all probe data is above — do **not** re-query to trust it, but the MFF `not_found`
   set may have shrunk if `lyrics_reassessment` ran meanwhile; a quick prod re-check of the 8 tracks is
   cheap).
2. Owner picks the entry point:
   - **Thread 2 (coverage expedite)** — small, legal, immediately useful. Decide OQ3 shape → build.
     Could ship as a `plan.md` row rather than living in this RFC.
   - **Thread 1 (Genius annotations)** — start with the OQ1 **coverage probe** (needs an owner-created
     Genius API token in SSM first). Do **not** design schema/UI before the probe passes.
3. On promotion, resolve OQ5 (split vs. keep bundled) and add/repoint the `plan.md` row.
