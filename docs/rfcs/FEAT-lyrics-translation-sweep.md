# FEAT-lyrics-translation-sweep: Auto-queue lyrics translation for research-note albums

- **Status**: in-progress
- **Owner**: 박지훈
- **Created**: 2026-07-05
- **Plan row**: `plan.md` → FEAT-lyrics-translation-sweep

---

## Goal

Every track that (a) belongs to an album with an `album_research` row (any status — the
research trigger creates the row at enqueue time), (b) has viewable lyrics
(`match_status='matched'` + non-empty synced or plain body), and (c) has **no**
`track_lyrics_translations` row yet, gets auto-enqueued for translation by the existing
local lyrics poller — no per-track 번역 요청 click required. This covers, with one
mechanism: (1) new albums entering a research-mode bucket, (2) the ~505-track backlog on
the 71 already-researched albums (prod measured 2026-07-05: 889 tracks / 518 with matched
lyrics / 13 translated), and (3) tracks whose lyrics arrive in the corpus *after* the
research trigger fired (the corpus is filled by manual `tools/` batches, so trigger-time
event coupling would systematically miss them).

## Non-goals

- No backend/API change, no contract change, no schema change, no deploy. The sweep lives
  entirely in `scripts/lyrics_translate_poller.py` (workspace-only).
- No event-trigger in `ResearchService.enqueue_album` — rejected in favor of the
  state-based sweep (owner decision 2026-07-05; see Decisions log).
- No re-translation: rows already `done`/`failed`/`requested` (any origin, incl. `manual`)
  are never touched. The sweep INSERTs only where **no row exists**.
- No translation for albums outside the research system (`research_mode='off'` buckets
  create no `album_research` row → no translation; intentional — the coupling to research
  curation is the scope).
- No enqueue-time Korean-dominant pre-filter: Korean tracks are enqueued and closed once
  by the poller's existing claim-time guard as `failed('korean_source')` ($0 — closes
  before the `claude -p` call; the viewer shows no translation UI for Korean-dominant
  tracks, so the rows are DB-only noise; accepted 2026-07-05).

## Current state

- Translation enqueue has exactly **one** writer: `LyricsService.request_translation`
  (`myblog_backend/app/services/lyrics_service.py:232`), called only from the viewer's
  번역 요청 button (`myblog_front .../LyricsViewer.tsx:342`). Nothing couples research to
  translation — FEAT-lyrics-translation decision 2026-07-04 scoped the trigger to
  "designated tracks only, fully GUI". This RFC reverses that scope decision (owner
  request 2026-07-05).
- `scripts/lyrics_translate_poller.py` (launchd `com.myblog.lyrics-translate-poller`,
  `StartInterval=60`): each firing claims **one** `requested` row (`CLAIM_SQL`, `LIMIT 1
  FOR UPDATE SKIP LOCKED`, 20-min stale-claim window) via `process_one(conn)`; `--drain`
  loops until empty with `INTER_RUN_SLEEP_S` between rows. Non-drain firings process at
  most 1 track/min.
- Research pipeline: `album_research` rows are created by bucket add (`buckets.py:586`),
  `research_selected` check (`buckets.py:628`), bucket-wide mode flip
  (`ResearchService.enqueue_bucket`), and manual trigger; drained by
  `scripts/research_poller.py`.
- `track_lyrics_translations`: PK `track_id`, status CHECK `requested|done|failed`,
  `requested_at`/`updated_at` default `now()`, `lang` default `'ko'`.
- Prod volume (2026-07-05): research-done albums 71 → 889 tracks → 518 with
  `matched` + non-empty body → 13 translated. All content-bearing rows are
  `match_status='matched'` (the V33 CHECK keeps `ambiguous`/`review_required` rows
  body-less), so mis-matched lyrics cannot enter the sweep by construction.

## Target state

`lyrics_translate_poller.py` gains two things:

1. **Sweep** — at the start of every firing, one INSERT derives the queue from state:

   ```sql
   INSERT INTO track_lyrics_translations (track_id, status)
   SELECT t.id, 'requested'
   FROM tracks t
   JOIN track_lyrics tl ON tl.track_id = t.id
   WHERE tl.match_status = 'matched'
     AND (btrim(coalesce(tl.lyric_synced, '')) <> ''
          OR btrim(coalesce(tl.lyric_plain, '')) <> '')
     AND EXISTS (SELECT 1 FROM album_research ar WHERE ar.album_id = t.album_id)
     AND NOT EXISTS (SELECT 1 FROM track_lyrics_translations x WHERE x.track_id = t.id)
   ON CONFLICT (track_id) DO NOTHING
   ```

   The lyrics-body predicate mirrors `normalize_lyrics` `availability=="ok"` exactly
   (matched + non-blank synced or plain), so the sweep can never enqueue a track the
   poller would reject as untranslatable. `NOT EXISTS` + `ON CONFLICT DO NOTHING` is the
   never-touch-existing-rows invariant (idempotent; safe under concurrent button clicks).

2. **Batch drain** — a non-`--drain` firing processes up to `BATCH_PER_RUN = 5` claims
   (loop `process_one` with `INTER_RUN_SLEEP_S` between, stop early when empty) instead
   of exactly one, so the ~505-track backlog drains in ~2 awake hours instead of ~8.5,
   while staying serial on the shared Max subscription (same rate-limit posture as the
   research poller). `--drain` behavior unchanged (loop to empty).

The viewer needs no change: swept tracks surface as the existing `requested` →
"번역 준비 중" state, then `done` with `origin='poller'`.

## Steps

Single step (one script, one PR). The backfill is not a separate step — the first firing
after merge *is* the backfill.

### Step 1 — sweep + batch drain in the lyrics poller

- Add `SWEEP_SQL` (above) + `sweep(conn) -> int`, called once per `main()` invocation
  before claiming; log the inserted count when > 0.
- Non-drain path: replace the single `process_one(conn)` call with a loop of up to
  `BATCH_PER_RUN = 5`, sleeping `INTER_RUN_SLEEP_S` between claims, breaking when
  `process_one` returns False.
- `--once` keeps meaning "one firing" (sweep + up to 5 claims). Add `--sweep-only`
  (sweep, report count, exit — no claims) for dry observation.

**Verification** (local, against prod DB — poller already runs against prod):
```
# 1. Dry count before: expected sweep candidates
psql "$DBURL" -c "SELECT count(*) FROM tracks t JOIN track_lyrics tl ON tl.track_id=t.id
  WHERE tl.match_status='matched' AND (btrim(coalesce(tl.lyric_synced,''))<>'' OR btrim(coalesce(tl.lyric_plain,''))<>'')
  AND EXISTS (SELECT 1 FROM album_research ar WHERE ar.album_id=t.album_id)
  AND NOT EXISTS (SELECT 1 FROM track_lyrics_translations x WHERE x.track_id=t.id)"
# 2. --sweep-only inserts exactly that count; second run inserts 0 (idempotent)
# 3. One --once firing: ≤5 claims processed, done rows carry origin='poller', model='claude.sonnet'
# 4. Existing 13 done rows byte-identical (updated_at unchanged)
```

**Rollback**: revert the script commit; already-inserted `requested` rows are inert
without a poller claiming them (or bulk-delete `status='requested' AND claimed_at IS NULL`
rows if a full unwind is wanted — never touches done/failed).

---

## Exit gate

Sweep-candidate count (the SQL in Verification #1 — denominator: matched-lyrics tracks on
research-row albums with no translation row) reaches **0** and stays 0 across two
consecutive days of normal poller operation; `done + failed('korean_source')` accounts for
all swept rows (no stuck `requested` older than 1 day while the laptop was awake).

## Open questions

1. **Drain-window session pressure** — 5 tracks/min × sonnet whole-lyric calls for ~2
   hours shares the Max subscription with interactive sessions. If a session cap is hit
   during the initial backfill, transient `claude -p` failures leave claims in place
   (20-min stale window retries), so nothing is lost — but if interactive work is
   noticeably throttled, drop `BATCH_PER_RUN` to 2–3. Blocks nothing; observe during
   backfill.

## Decisions log

| Date | Decision | Step |
|------|----------|------|
| 2026-07-05 | Scope reversal of FEAT-lyrics-translation "designated tracks only": research-curated albums now auto-translate all matched-lyrics tracks (owner request) | — |
| 2026-07-05 | Mechanism = state-based sweep in the poller, NOT an event trigger in `ResearchService.enqueue_album` — corpus lags the research trigger (manual `tools/` batches), so event coupling misses late-arriving lyrics; sweep also *is* the backfill. Workspace-only, no deploy | 1 |
| 2026-07-05 | Drain rate: `BATCH_PER_RUN = 5` per 60s firing, serial + inter-run sleep (research-poller posture) | 1 |
| 2026-07-05 | Korean-dominant tracks: no enqueue-time pre-filter; claim-time guard closes them once as `failed('korean_source')` (row-absence predicate → never re-swept; $0; no viewer exposure) | 1 |
