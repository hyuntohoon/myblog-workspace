# FEAT-lyrics-translation: Korean translation for designated lyrics in the viewer

- **Status**: accepted
- **Owner**: 박지훈
- **Created**: 2026-07-04
- **Plan row**: `plan.md` → FEAT-lyrics-translation

---

## Goal

Owner-designated tracks gain a segment-aligned Korean translation, rendered in the existing
lyrics viewer as a 원문+번역 toggle. The flow is fully GUI-driven: a **번역 요청** button in the
viewer enqueues a request row; a **local launchd poller** (genre-heal-poller pattern) claims it
and translates line-by-line with **Amazon Translate** on the owner's AWS credentials (engine
swapped from `claude -p` 2026-07-04 — decisions log); the next viewer open shows the
translation. No terminal step, no new AWS infra, no new secret, and no synchronous MT/LLM call
in any user-facing endpoint (rule #9 spirit). Translations carry the corpus's owner-only privacy bar —
as derivative works they are *more* copyright-sensitive than the originals, never less.

## Non-goals

- **Corpus-wide batch translation.** Earlier drafts considered pre-translating the full matched
  corpus (10,652 rows) — dropped 2026-07-04. Only designated tracks are translated. A future
  bulk pass (e.g. Anthropic Batch API, ~$60–80 for ~5k tracks at Sonnet batch rates) is a
  separate RFC if ever wanted.
- **Any public exposure.** Same "never in any shared response" bar as `track_lyrics`
  (FEAT-lyrics-corpus). Translation leaves the server only via the JWT-gated `/api/lyrics` read.
- **Translation editing UI.** Corrections happen by re-requesting (poller re-translates) or by
  an owner-driven Claude-session override (`origin='manual'` upsert via a local tool); the
  viewer never edits.
- **LLM in Lambda / a new secret.** The worker gains no Anthropic dependency; no SSM key is
  provisioned. `claude -p` runs only on the owner's machine (same boundary as genre backfill /
  research notes).
- **MT libraries / non-AWS translation APIs** (DeepL, Papago, Google Translate, Argos…). The
  engine was originally the Claude model itself; after headless `claude -p` proved unusable
  (copyright refusal — decisions log 2026-07-04) the engine moved to **Amazon Translate**
  (existing AWS credentials, no new signup/secret). Other MT providers stay out of scope
  unless the pilot gate fails on Amazon Translate quality.
- **Other target languages**, interpretation / slang / per-line commentary (still a separate
  future RFC), auto re-translation on staleness, and any change to `track_lyrics` or the
  matcher.

## Current state

- **Corpus**: `track_lyrics` (owner-only; 10,652 `matched` — 8,021 exact-title + best-of) with
  raw `lyric_plain` / `lyric_synced` as source of truth. No translation column, table, or
  contract field exists anywhere (asserted by FEAT-lyrics-viewer, verified 2026-07-04).
- **Read path**: `myblog_backend/app/services/lyrics_service.py` — pure, replayable
  `normalize_lyrics` (`NORMALIZER_VERSION = 1`) derives `segments[]{i, text, start_ms}` at read
  time; nothing normalized is stored. Served by JWT-gated `GET /api/lyrics/{spotify_track_id}`
  (`app/api/routes/lyrics.py`, own `infra/apigateway.tf` route — not the edge_guard catch-all).
- **Viewer**: `myblog_front` full-screen overlay (FEAT-lyrics-viewer) renders the segments;
  entry from `NowPlaying` live branches + `?lyrics=<id>` debug entry. Original lyrics only.
- **GUI→local-LLM precedent**: the 분류하기 button → `genre_backfill_requests` (shared_db V25,
  raw-SQL queue, no ORM pin bump) → `scripts/genre_heal_poller.py` (launchd `--once`, claim via
  `FOR UPDATE SKIP LOCKED` + `claimed_at` gate) → local `claude -p`. `scripts/research_poller.py`
  is the same shape with a 20-min re-claim. Pollers read the LOCAL workspace checkout (repos
  must sit on merged `main`).
- **Engine evidence** (2026-07-04 session): ROSALÍA "Berghain" (43 non-gap lines, DE/ES/EN
  mixed) translated via one `claude -p` call with a count-preserving JSON-array prompt —
  **43/43 length validation on the first attempt, 28.1s, 0 mistranslations** in owner review.
  Per-track payload is small (~1k tokens in / ~2k out); the CLI's ~19k system-prompt overhead is
  mostly cache reads. Sample ran on a top-tier model; Sonnet quality is re-validated by the
  Step 3 pilot gate.
- Latest shared_db migration: V34 → this RFC takes **V35**.

## Target state

- **Schema (V35)**: `track_lyrics_translations` — one row per designated track, request
  lifecycle and result in the same row:
  - `track_id` UUID PK → `tracks.id` ON DELETE CASCADE
  - `status` TEXT: `requested` | `done` | `failed`; `claimed_at` TIMESTAMPTZ (poller claim gate,
    20-min re-claim; `requested AND claimed_at IS NULL` = pending, partial index)
  - `lang` TEXT DEFAULT `'ko'`; `segments` JSONB (`[{i, text_ko}]`, aligned 1:1 to the
    normalized segments, gap segments carried as `""`)
  - `source_fingerprint` TEXT (sha256 over `normalizer_version` + all source segment texts) +
    `normalizer_version` INT — staleness is *computed at read time*, never stored
  - `origin` TEXT: `'poller'` | `'manual'`; `model`, `translator_version`, `error`,
    `requested_at`, `translated_at`, `updated_at`
- **Backend**: `POST /api/lyrics/{spotify_track_id}/translation-request` (JWT,
  `require_cognito_token`, its own `infra/apigateway.tf` route like GET /api/lyrics) upserts
  `status='requested'` (idempotent while pending; allowed again on `done`/`failed`/stale — an
  explicit re-request may overwrite a `manual` row, but the poller never touches `manual`
  otherwise). `GET /api/lyrics/{id}` gains an **additive** `translation` object
  (`status: none|requested|done|failed|stale`, `origin`, `lang`) and each segment an optional
  `text_ko` (populated only when `done` and the fingerprint matches; mismatch reads as `stale`
  with `text_ko` omitted).
- **Poller**: `scripts/lyrics_translate_poller.py` + `com.myblog.lyrics-translate-poller.plist`
  (launchd `--once`, **60s `StartInterval`** — a no-pending run is one Neon connection + one
  SELECT, exiting in ms; effective designate→readable latency ≈ 1–2 min) — claim one pending
  row → load `track_lyrics` → normalize with the SAME `normalize_lyrics` imported from the
  local `myblog_backend` checkout (fingerprint parity by construction) → **per-line Amazon
  Translate** (`auto`→`ko`, `Formality=INFORMAL` for lyric register; 1:1 alignment by
  construction so no length validation; already-Korean lines pass through untouched) →
  re-insert gaps → upsert `done` + fingerprint (`model='amazon.translate'`).
  Belt-and-suspenders Korean guard: a Korean-dominant source (same Hangul-ratio heuristic as
  the viewer) is never sent to the engine — the row is closed as `failed` +
  `error='korean_source'` without an MT call.
- **Viewer**: when `translation.status == 'done'` a 번역 toggle interleaves each `text_ko`
  dimmed under its original line (focus/nav unit stays the original segment — existing focus
  logic untouched); when `none`/`failed`/`stale` a 번역 요청 button fires the POST and flips to
  a passive 요청됨 state; `requested` shows 요청됨. **Korean-dominant tracks get no request
  button** (client-side Hangul-ratio heuristic over the non-gap segment text, ~≥50% → treated
  as already-Korean; nothing to translate).

## Steps

Cross-repo rollout order per `reference-shared-db-cross-repo-rollout`: migration → prod apply →
service pin → contract → front.

### Step 1 — shared_db V35 + model + pin

`migrations/V35__track_lyrics_translations.sql` (additive, plain SQL, down-migration comment,
V25-style header) + ORM model `TrackLyricsTranslation` + tag `v0.27.x`. Prod apply is
owner-approved manual (rule #3). Backend pin bump rides Step 2's PR.

**Verification**:
```
cd myblog_shared_db && PYTHONPATH=src pytest   # schema/model parity
psql "$PROD" -c "\d track_lyrics_translations" # post-apply, owner-run
```

**Rollback**: `DROP TABLE track_lyrics_translations;` (additive, no data dependency).

---

### Step 2 — backend request endpoint + additive read extension + contract

`POST /api/lyrics/{spotify_track_id}/translation-request` + `translation`/`text_ko` on
`LyricsResponse`; new `infra/apigateway.tf` JWT route (POST 404s until applied —
`reference-apigateway-post-route-required`) + owner-run `terraform apply`. Export
`openapi.json` in the same PR; merge workspace contract first
(`reference-workspace-contract-merge-order`), regen front `api.gen.ts`.

**Verification**:
```
cd myblog_backend && pytest
curl -X POST "$APIGW/api/lyrics/<sid>/translation-request" -H "Authorization: Bearer $T"  # 200, row requested
curl "$APIGW/api/lyrics/<sid>" -H ... | jq .translation.status                            # "requested"
```

---

### Step 3 — local poller + plist + pilot audit gate

`scripts/lyrics_translate_poller.py` (+ plist). Verify end-to-end on prod rows created via the
Step 2 endpoint (curl — steady-state stays GUI-only). **Pilot gate before calling the step
done**: the first **15** poller-translated tracks are owner-audited in full; pass bar **≥90% of
audited tracks with zero mistranslated lines** (denominator = the 15 audited tracks); the
sample must include ≥3 non-English-source tracks (multilingual check of the MT engine). Fail →
tune engine settings or swap provider (Papago named fallback), reset rows to `requested`,
repeat.

**Verification**:
```
python scripts/lyrics_translate_poller.py            # claims 1 row, done + fingerprint set
launchctl list | grep lyrics-translate               # loaded
psql: status='done' AND jsonb_array_length(segments) == source segment count
```

**Rollback**: unload the plist; rows stay inert (viewer just shows 번역 요청 again).

---

### Step 4 — viewer 번역 toggle + 번역 요청 button

Front-only. Interleaved dimmed `text_ko`, request button + 요청됨/실패 states, `origin`
badge for `manual` rows (minor). Real-browser CDP click-through pre-merge (DoD), prod smoke
via the `?lyrics=<id>` debug entry on a translated track.

**Verification**:
```
pnpm lint && pnpm exec astro check   # Node 20 (.nvmrc)
CDP: toggle renders text_ko under each line; focus nav unchanged; request button POSTs once
```

---

## Open questions

1. ~~**Poller cadence**~~ — RESOLVED 2026-07-04 (owner): **60s `StartInterval`** (no-op runs
   are ~free; latency floor is the ~30s translation, so designate→readable ≈ 1.5–2 min).
2. ~~**Pilot gate size**~~ — RESOLVED 2026-07-04 (owner): **15 tracks**, pass ≥90% of audited
   tracks with zero mistranslated lines (denominator = the 15 audited tracks), ≥3
   non-English-source tracks included.
3. ~~**Korean-dominant tracks**~~ — RESOLVED 2026-07-04 (owner): Korean lyrics need no
   translation. Viewer hides the request button on Korean-dominant tracks (Hangul-ratio
   heuristic); poller double-guards with a no-op `failed('korean_source')` close.
4. **Later poller consolidation** — 4 launchd jobs now exist; folding lyrics translation into a
   single multi-queue poller is a possible later chore, out of scope here.

## Decisions log

| Date | Decision | Step |
|------|----------|------|
| 2026-07-04 | Engine = Claude LLM via local `claude -p` — no MT library/API (DeepL/Google/Argos rejected: lyric register, slang, metaphor, code-switching). Evidence: Berghain sample — 43/43 first-try length validation, 28.1s, 0 mistranslations, DE/ES/EN handled | 0 |
| 2026-07-04 | Model pinned **sonnet** (`claude -p --model sonnet`) — subscription-usage economy; quality re-validated at Sonnet tier by the Step 3 pilot gate | 0 |
| 2026-07-04 | Scope = **designated tracks only** (research-note-style curation). Corpus-wide batch + Anthropic-API hybrid plan dropped; no SSM anthropic key needed | 0 |
| 2026-07-04 | Trigger fully **GUI**: viewer 번역 요청 → request row → local launchd poller (genre-heal V25 pattern). Owner rejected a manual terminal sync step | 0 |
| 2026-07-04 | Storage = segment-aligned JSONB + read-time `source_fingerprint` staleness (stale → hidden + re-request); raw lyrics stay source of truth | 0 |
| 2026-07-04 | Manual override kept: `origin='manual'` rows written via owner-driven Claude session; poller overwrites them only on an explicit re-request | 0 |
| 2026-07-04 | Status draft → **accepted** (explicit owner approval in-session: "이걸로 rfc 승격") | — |
| 2026-07-04 | OQ3 resolved — Korean-dominant tracks are excluded: no request button in the viewer (Hangul-ratio heuristic) + poller no-op guard (`failed('korean_source')`); designated-only flow means nothing else auto-translates | 3, 4 |
| 2026-07-04 | OQ1 resolved — poller cadence 60s `StartInterval` (owner wanted the shortest sensible; no-op runs cost one Neon SELECT, latency floor is the ~30s translation) | 3 |
| 2026-07-04 | OQ2 resolved — pilot gate 15 tracks, ≥90% of audited tracks mistranslation-free (denominator = audited tracks), ≥3 non-English sources | 3 |
| 2026-07-04 | Step 1 executed — shared_db #51 (`V35__track_lyrics_translations.sql` + `TrackLyricsTranslation`, tag `v0.27.0`), V35 prod-applied (owner-approved) | 1 |
| 2026-07-04 | Step 2 executed — backend #99 (POST translation-request + additive `translation`/`text_ko` on the read; pin bump `v0.27.0`), ws #520 (JWT route + merged contract), front #229 (`api.gen.ts` regen). Route terraform-applied same day (1 add, 0 change/destroy; owner-approved in session). Prod smoke: full suite 28/0; GET unauth 401 / authed `translation:{status:"none"}`; POST unauth 401 / authed `requested` / idempotent; GET reflects `requested`; smoke row deleted (poller not yet deployed) | 2 |
| 2026-07-04 | **Engine swapped Claude → Amazon Translate** (owner-approved). Headless `claude -p` consistently REFUSES full-lyrics translation on copyright grounds — sonnet (2 prompts + honest private-use context) and opus (same context) both; the in-session Berghain 43/43 evidence does not replicate headless, and prompt-engineering around a consistent principled refusal was ruled out. Amazon Translate chosen over DeepL/Papago: no new signup or secret (owner AWS creds + a `translate:TranslateText` inline policy on `claude_aws_manager`), per-line calls give 1:1 alignment by construction (length validation obsolete), 12-month free tier then ~$0.02/track. Quality bar unchanged — the 15-track pilot gate now audits MT output; Papago is the named fallback if it fails | 3 |
| 2026-07-04 | Step 3 executed + **pilot gate PASSED** (ws #523 poller/plist + #524 passthrough fix). Pilot = ROSALÍA **LUX (Complete Works)**: all 13 `matched` tracks (2 album tracks are corpus `not_found` — owner accepted **13 as the denominator** in place of 15), 590 lines, ES/IT/DE/EN/Latin mixed (non-English ≥3 satisfied). Owner audited the full 원문↔번역 doc and passed all 13 ("이걸로 가자"). Findings folded back: real-Latin lines (`Porcelana` "Ego sum nihil") now pass through untranslated instead of failing the track (UnsupportedLanguagePair per-line fallback); launchd + `--drain` concurrent claims verified live (SKIP LOCKED, no double-processing). Poller live via launchd 60s | 3 |
