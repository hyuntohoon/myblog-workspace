# FEAT-lyrics-match-correction: detect and correct wrongly attached lyrics

- **Status**: draft
- **Owner**: site owner
- **Created**: 2026-10-15
- **Plan row**: `docs/plan.md` → FEAT-lyrics-match-correction
- **Execution**: one step per session (3a and 3b are separate sessions). Steps 1 and 2 are worker-only and need no contract change.

---

## Goal

A wrong lyric attached to a track stops being permanent. Three things are true afterwards:

1. The matcher no longer picks a candidate whose **content** disagrees with the other candidates for
   the same song, and no longer treats a language version (`- Japanese ver.`) as the original.
2. The owner has a **candidate panel** for any track. It shows every candidate, its source, a
   preview, and why it won or lost. From it the owner picks one or marks "no lyrics". The pick is
   **locked**: no automatic job overwrites it, and a rejected candidate is never attached again.
3. Any signed-in member can report wrong lyrics from the viewer with one tap. A report never edits
   lyrics. It triggers an evidence-based recheck and puts the track on the owner's queue, which
   opens the same panel.

## Non-goals

- **Hand-typed or pasted lyrics.** Corrections choose among LRCLIB candidates (or "no lyrics").
  Storing user-authored lyric text is a different licensing and moderation question.
- **Genius song mismatches** (`track_genius_songs`: 175 `ambiguous`, 214 `matched` below 0.8
  confidence on 2026-10-15). Same shape of problem; it gets its own step once this one has shipped.
- **Sync-offset correction** (right words, wrong timing). Not a matching error.
- **A second lyrics source.** LRCLIB stays the only source.

## Incident that started this

Owner report 2026-10-15: Steve Lacy, "Bad Habit" (`Gemini Rights`, spotify `4k6Uh1HXdhtusDW5y8Gbvy`)
shows Ed Sheeran's "Bad Habits".

- Stored row: `match_status='matched'`, `match_basis='exact-title'`, `matcher_version='step3-v1'`,
  `lrclib_id=8996695`, written 2026-07-18.
- LRCLIB 8996695 has correct **metadata** (`Bad Habit` / `Steve Lacy` / 232.0 s / synced) and wrong
  **content**: the body opens with the line `Bad Habits - Ed Sheeran`, then Ed Sheeran's lyric.
- `/api/search` for the same track today returns **20 plausible candidates** (same artist, exact
  title, most at 232 s). All 20 carry the correct Steve Lacy lyric (`I wish I knew you— / Wanted me`).

Every gate in `decide_match` looks at metadata only (artist identity, title, duration, version
tokens). The near-duplicate collapse then picks a group representative by version agreement, exact
title, full-title equality, synced, then plain (`_representative` in
`worker/service/lyrics_matcher.py`). Content never enters the decision, so one bad upload with good
metadata and a synced body can win against twenty good ones.

## Current state

Verified against `origin/main` on 2026-10-15.

**Producers** (all write through `decide_match` → `lyrics_promote` → `TrackLyricsWriter`):

| Job | Selects | Trigger |
|---|---|---|
| `lyrics_incremental` | tracks with no `track_lyrics` row | 15-min EventBridge + self-chain after album sync |
| `lyrics_reassessment` | unresolved rows + `best-of-*` matched rows; optional `album_id` scope | EventBridge + manual SQS |
| `lyrics_demand_source` | album-demand tracks (V57/V58) | EventBridge + manual SQS |
| `tools/lyrics_*.py` (workspace) | batch / dump / backfill | manual; **twin** of the worker selection SQL |

**Storage.** `track_lyrics` has one row per track (V33), upserted on `track_id`. `evidence` carries
`lrclib_id` at the top level for `exact-title` rows. For the 771 `best-of-*` rows it is only under
`evidence.promotion`.

**Never-downgrade guard.** `should_replace` in `lyrics_reassessment_service.py` replaces a resolved
row only with a strictly stronger basis (`_BASIS_STRENGTH_MAP`), and reassessment never *selects* an
`exact-title` row. As a result, **a wrong `exact-title` match is never looked at again**. If someone
cleared it by hand, the next incremental or reassessment run would pick the same candidate again,
because nothing remembers that it was rejected.

**Read path.** `GET /api/lyrics/{spotify_track_id}` (`require_cognito_token`, any member) returns
segments only, with no provenance. Derived data already handles a source change:

- the translation is keyed by `source_fingerprint` and reads as `stale` when the lyric changes
  (`attach_translation`);
- Genius anchors are recomputed on every read (V49 note 1).

**No correction path exists.** There is no endpoint, no table, and no job. Searched `docs/` and all
five repos for report/override/reject on lyrics: nothing.

**Production distribution (2026-10-15, read-only):** 16,950 `matched` (16,179 `exact-title`, 771
`best-of-ambiguous`), 1,173 `no_lyrics`, 18,920 `not_found`, 24 `review_required`.

## Failure classes

| # | Class | Example | Caught by |
|---|---|---|---|
| A | Correct metadata, wrong content (crowd upload) | Bad Habit → Ed Sheeran | Step 1 consensus, when other candidates exist; otherwise a report |
| B | Language version collapsed into the original | BTS `Go Go` (Korean original) serves the Japanese lyric of LRCLIB 13611969 `Go Go (Japanese Ver.)` | Step 1 language tokens |
| C | Best-of promotion picked the wrong group | — (not yet observed) | report |
| D | Homonym artist + same title + coincident duration | — (not yet observed) | report |

**Class B mechanism.** `_strip_noise` runs on both sides. On the candidate side it dropped
`(Japanese Ver.)` because the parenthesis carries no version token: neither `japanese` nor `ver` is in
`_VERSION_TOKENS`. The candidate reduced to `go go` and matched the Korean original as `exact-title`
(evidence `title_noise_stripped: ["candidate"]`). The durations are 235 s and 237 s, so the duration
gate could not separate them.

## Root-cause analysis

The two incidents are symptoms. These are the design-level causes in the matcher and pipeline,
ordered from the incidents outward. By row count RC5 is the largest. RC1 is rare (0 confirmed in a
200-row probe) but produces the most visible failure. Production numbers are from 2026-10-15,
read-only.

**RC1 — Selection is blind to content.** Every gate in `decide_match` and every key in
`_representative` reads metadata or richness: artist, title, duration, version tokens, `synced`,
`plain`. LRCLIB is crowd data, and its metadata and body are uploaded independently, so metadata
agreement does not prove the body is right. When near-duplicates collapse, the richest body wins,
not the most common one. *Explains A (Bad Habit). Fixed by Step 1 (consensus).*

**RC2 — Noise stripping is a deny-list.** `_strip_noise` keeps a parenthesis or dash segment only if
it contains a known rendition token. Anything the list does not name is treated as noise and removed
on both sides: language versions (`Japanese Ver.`), dated re-releases (`2023 Ver.`), and any rendition
nobody listed. After stripping, duration is the only discriminator left, and language or region
versions usually share the original's duration. 1,762 `matched` rows had the candidate side
stripped. Two of them are confirmed language leaks (both `Go Go`); the rest sampled as `feat.` /
`with` / `prod.` credits, which is what the strip was meant for. *Explains B. Fixed by Step 1: the
token list grows, and `ver` / `ver.` marks a segment as a rendition whatever precedes it.*

**RC3 — The chosen body is never validated.** Nothing checks the body against the track it is
attached to:

- the last LRC timestamp against the track duration;
- a first line naming another title or artist (Bad Habit's body opens `Bad Habits - Ed Sheeran`);
- LRC timestamps pasted into the plain field (Bad Habit again).

*Measured in the signal table above; Step 4 uses the signals that turn out to be precise.*

**RC4 — A match is write-once.** An `exact-title` row is never re-selected, and nothing records a
rejected candidate. Every other defect becomes permanent because of this one. *Fixed by Steps 2
and 3.*

**RC5 — `matcher_version` is recorded, but no job acts on it.** V33 says the column "enables
re-evaluation on matcher change". No job selects by it; the only reader is the one-off
`tools/lyrics_bestof_backfill.py`. Production still serves **9,099 resolved rows from `step2-v2`**
(8,001 matched + 450 no_lyrics + 648 best-of). The `step3-v1` noise fixes of 2026-07-04 (worker #64)
never reached them. *Fixed by Step 2, which keys its sweep on `matcher_version`.*

**RC6 — Consensus can only see what retrieval returns.** `/api/search` returns at most 20 rows.
Bad Habit's stored 8996695 is not among today's 20 for the same query. Consensus is therefore a
sample, not a census: it fixes a wrong pick when the good candidates are retrieved, and it says
nothing about a track with a single candidate. *That residue is why Step 3 (reports) exists rather
than relying on Step 1 alone.*

### Automatic signals measured (2026-10-15)

| Signal | Count | Precision |
|---|---|---|
| Last LRC timestamp > track duration + 5 s | 80 / 15,573 synced | unmeasured |
| Lyric ends before 40% of track duration | 49 | unmeasured |
| Same `lrclib_id` on tracks with different titles | 8 | 1 confirmed wrong (Go Go); others are spelling/feat duplicates |
| First line looks like a `Title - Artist` header naming someone else | 10 | 1 / 10 real (Bad Habit); rest are lyric lines with dashes. **Rejected as a signal.** |
| Stored content disagrees with the candidate content majority | 2 / 200 sampled `exact-title` rows | **0 / 2.** Both were the same song in a different transcription (see below) |

**Consensus probe, 2026-10-15.** Random 200 `exact-title` matched rows. Each was re-searched on
LRCLIB with the worker's primary-artist query and filtered through the matcher's own gates. The
stored body was then compared with the plausible candidates (first 500 normalized characters,
`SequenceMatcher` ratio ≥ 0.6). Script: session scratchpad, not committed. The first run at
concurrency 4 drew 429/503 on 161 of 200 requests and was discarded; the rerun went sequential with
backoff and had 0 errors.

- Plausible candidates per track: 0 → 0 tracks; 1 → 25 tracks (consensus impossible, RC6);
  ≥ 2 → 175 tracks.
- Flagged as disagreeing with a ≥ 2 majority: 2. Both were false positives:
  - Travis Scott `BEEP BEEP`: ad-lib parentheses transcribed differently;
  - Tyler, The Creator `Big Poe`: a leading `Welcome` line.
- **Confirmed wrong-content matches: 0 / 200.** With zero in 200, the 95% upper bound on the rate is
  about 1.5%, which is ≤ ~250 of 16,950 matched rows. Class A is rare. Bad Habit was found by a
  person, not by sampling, which supports Step 3 over a bulk sweep alone.
- The similarity measure is too sensitive to transcription style. Step 1 must use a measure that
  ignores parentheticals and line order (word-shingle overlap). Its fixtures must include both
  false positives above as **must-agree** pairs.

## Prior art (researched 2026-10-15)

| Model | Example | How wrong lyrics get fixed |
|---|---|---|
| Licensed provider, fixed upstream | Spotify (Musixmatch) | No in-app report. Users go to Musixmatch → "Report a problem → Wrong lyrics" → staff review. Users report that fixes reach Spotify late |
| Community wiki with tiers | Musixmatch, Genius | Anyone proposes; curators approve. Staff-verified lyrics need admin approval; artist-verified lyrics are locked to everyone |
| Candidate aggregator | Lyrimuse (LyricsX successor) | Scores candidates from several sources on one scale. A per-track panel shows every candidate's score and why the winner won. A manual pick stays locked; unlocked tracks upgrade when a better candidate appears |

This system is the third model: it picks among crowd candidates and cannot correct the source.
LRCLIB exposes no flag or report endpoint that we could find (get / search / publish only). The
design therefore takes:

- the **panel, pick and lock** from the aggregator model;
- the **propose-vs-decide tiering** from the wiki model. `track_lyrics` is one global row per track,
  so a member's action would change the lyric for everyone; members propose and the owner decides.

A report is the entry to the panel, not the fix. Report volume should be small (0 confirmed
wrong-content rows in a 200-row probe), so the panel matters more than the report workflow.
Licensed sources are not immune either: Spotify served fabricated lyrics for My Bloody Valentine and
Cocteau Twins through its provider (MusicTech).

Sources: [Spotify Community thread](https://community.spotify.com/t5/Android/How-do-you-report-or-fix-wrong-lyrics/td-p/5054230),
[Musixmatch locked lyrics](https://musixmatch.helpscoutdocs.com/article/175-locked-lyrics-what-does-it-mean),
[Musixmatch verified lyrics](https://musixmatch.helpscoutdocs.com/article/337-what-are-verified-lyrics),
[Musixmatch curators](https://musixmatch.helpscoutdocs.com/article/61-who-are-the-lyrics-curators-how-can-i-become-one),
[Lyrimuse](https://chatgate.ai/post/lyrimuse),
[lrclib wrapper endpoints](https://lrclibapi.readthedocs.io/en/stable/_modules/lrclib/api.html),
[MusicTech](https://musictech.com/news/industry/how-spotify-ended-up-uploading-fake-and-insulting-lyrics-for-my-bloody-valentine-and-cocteau-twins-music/).

## Target state

```
                      ┌── decide_match (+ content consensus, + rendition markers)               ◀── Step 1
incremental / reassess / demand / tools ──┤── persists the plausible candidate set it judged          ◀── Step 3
                      ├── excludes track_lyrics_rejections(track_id, lrclib_id)                  ◀── Step 3
                      └── never selects or replaces a basis='manual' (locked) row                 ◀── Step 3

member viewer "가사가 틀려요" ─► report ─► SQS recheck {track_id} ─► owner queue                 ◀── Step 3
suspicion sweep (overrun / early end / shared id) ─────────────────► owner queue                 ◀── Step 4

owner candidate panel (from the viewer or the queue)                                            ◀── Step 3
   every candidate: source title/artist/album/duration, synced?, preview, cluster size, verdict
   ├─ pick X      → worker fetches X by id → write basis='manual' (locked)
   ├─ no lyrics   → write no_lyrics, basis='manual' (locked)
   ├─ reject X    → rejection row + recheck (stays unlocked)
   └─ unlock      → back to automatic
```

**Why a member report does not edit.** Reporting is open to every member, and the row is global. If
a report could take lyrics down or swap them, one person could do it to any song for everyone. A
recheck can only move to a candidate that more candidates agree with, so a false report costs one
LRCLIB call and changes nothing. Everything else waits for the owner's panel.

## Steps

### Step 1 — Matcher: content consensus and language versions (worker only)

- `_representative`: among the plausible candidates of one base-title group, cluster by normalized
  content similarity (strip LRC timestamps, lowercase, alnum, first ~500 chars). Prefer the
  **largest content cluster**, then apply the existing keys inside it. When the largest cluster has
  only one member and the group has ≥2 candidates that all disagree, park as `review_required`
  (`reason='content_disagreement'`) instead of picking.
- Add rendition markers so `_strip_noise` keeps those segments and version agreement gates them
  (RC2):
  - `ver` / `ver.` marks a segment as a rendition on its own, so `2023 Ver.` and any future
    `X Ver.` are covered without listing X;
  - language names in en/ko/ja (`japanese`, `english`, `chinese`, `korean`, `spanish`, `일본어`,
    `영어`, `중국어`, `日本語`, …) count only inside a parenthesis or dash segment, never in the
    base title (`English Girl` stays a title).
- Keep the new evidence keys for RC3 diagnostics: `content_cluster_size`, `plausible_count`.
- Write `lrclib_id` at the top level of evidence for promoted rows too.
- Bump `MATCHER_VERSION`. Keep the change pure: `decide_match` only.
- Twin: `tools/lyrics_*.py` import nothing from the worker. Change their copies in the same change or
  record why not.

**Verification:** unit tests built from the two real cases (Bad Habit's 20 + 1 candidates; Go Go /
Go Go - Japanese ver.). Mutation-check each new test: remove the consensus key, then the token, and
confirm the test fails. Worker `test` check green.

### Step 2 — Re-sweep existing matches under the Step 1 matcher (worker + one-off run)

- Extend the replacement guard with one lateral rule: a row produced by an **older** matcher version
  may be replaced at the **same** basis when the new outcome's content differs and the new
  representative belongs to a strictly larger content cluster. A `manual` row is never replaced.
- Run a bounded sweep over resolved rows whose `matcher_version` is older than the current one
  (RC5), oldest version first, using the existing `run_eval_batch` budget. Record per-run counts:
  replaced, unchanged, parked. This closes RC5 for good: every later matcher bump re-opens the sweep
  automatically, with no new one-off script.
- The sweep paces itself to LRCLIB: the 2026-10-15 probe drew 429s on 152 of 200 requests at
  concurrency 4.
- Expected volume. Re-evaluation: all 9,099 `step2-v2` rows plus the `step3-v1` rows once the
  version bumps. **Replacements: few.** The probe found 0 confirmed in 200, so most of the sweep's
  value is RC2/RC5 noise fixes reaching old rows, not consensus swaps. Before the bulk run, replace
  one track (Bad Habit) through the
  `{track_id}` scope and verify it on production.

**Verification:** Bad Habit served with the Steve Lacy lyric on production. Its translation reads
`stale`. Sweep metrics are quoted in the PR.

### Step 3 — Candidate panel, lock, and member reports (shared_db + backend + worker + front + contract + infra)

The panel is the core of this step and the report is its entry, so the step ships in that order.
3a is usable by the owner alone; 3b adds the member entry.

**3a — Candidate panel and lock (owner)**

- **Schema (next V):**
  - `track_lyrics_candidates(track_id, lrclib_id, title, artist, album, duration_sec, has_synced,
    preview, cluster_size, verdict, fetched_at)`, PK (track_id, lrclib_id). Written by every
    evaluation for the plausible set it judged. It holds metadata and a short preview only, never
    full lyric text.
  - `track_lyrics_rejections(track_id, lrclib_id, rejected_by, created_at)`, PK (track_id, lrclib_id).
  - Add `'manual'` to the basis ladder above `isrc`. A `manual` row is the lock.
- **API (owner):**
  - `GET /api/admin/lyrics/{spotify_track_id}/candidates` returns the stored set with verdicts and
    the current pick's provenance. If nothing is stored, or it is stale, it says so.
  - `POST .../candidates/refresh` enqueues a worker recheck that repopulates the set. The request
    makes no LRCLIB call, consistent with the rule that external calls stay out of user-facing
    requests.
  - `POST .../decision` takes `{action: pick, lrclib_id}`, `{action: no_lyrics}`,
    `{action: reject, lrclib_id}` or `{action: unlock}`. Pick enqueues a worker fetch of that id
    (`/api/get/{id}`) and writes basis `manual`; the body is re-fetched, never copied from the
    preview.
- **Worker:**
  - Every selection path drops rejected candidates before `decide_match`, and never selects or
    replaces a `manual` row. That covers incremental, reassessment, demand_source and the
    `tools/lyrics_*` twin.
  - New single-track jobs: `lyrics_recheck {track_id}` and `lyrics_pick {track_id, lrclib_id}`.
- **Front:** "다른 가사 보기" in the lyrics viewer, owner only. It opens the panel: candidates sorted
  by verdict, each with source, preview and the reason it lost; the current pick and its lock state.

**3b — Member reports**

- **Schema:** `track_lyrics_reports(id, track_id, user_sub, created_at, status, resolved_at,
  resolution)`, one open report per (track, user). `user_sub IS NULL` is reserved for Step 4's
  system reports.
- **API:** `POST /api/lyrics/{spotify_track_id}/report` for any member, with a per-user daily limit
  (bucket rate-limit precedent). It records the report and enqueues `lyrics_recheck`. It never
  changes `track_lyrics` directly.
- **Owner queue:** `GET /api/admin/lyrics/reports` lists open reports, each opening the 3a panel.
  If the recheck already switched to a better-agreed candidate, the report shows that as
  `auto_resolved` for the owner to confirm, not as silently closed.
- **Front:** a one-tap "가사가 틀려요" in the viewer for every member, with a confirmation line. It
  shows no candidates.

**Mandatory second passes:** `reviewer` (contract + infra) on 3a and on 3b; the `security-review`
skill on 3b (member input).

**Verification:**

- route parity in `infra/apigateway.tf`;
- contract procedure per `docs/contracts/README.md`;
- real-browser clickthrough as the owner: Bad Habit panel → pick → locked → a reassessment run
  leaves it alone;
- real-browser clickthrough as a member: report → owner queue;
- production smoke.

### Step 4 — Suspicion sweep feeds the same queue

- A periodic read-only job opens system-authored reports (`user_sub = NULL`, `reason = signal`) for
  the measured signals: duration overrun, early end, shared `lrclib_id` across different base titles.
- Sample 20 per signal first. Keep only signals whose measured precision justifies the owner's time;
  record the numbers here.

---

## Matcher patch notes

**Rule for this RFC and every later matcher change:**

- Any PR that changes how a lyric gets chosen adds an entry here in the same PR. That covers
  `lyrics_matcher.py`, `lyrics_promote.py`, the replacement guard, selection SQL, and the
  `tools/lyrics_*` twins.
- An entry records: version string, date, PR, what changed in behaviour, why (the incident or
  measurement), and the **measured effect on production rows** once the sweep has run.
- A PR that leaves the version string unchanged says so in its entry.

These notes are also the first concrete input to the patch-notes goal in `docs/plan.md` Backlog
(*patch notes from commit history*). Keeping them in this form now means that goal does not have to
reconstruct intent from commit subjects later.

Entries before this RFC were reconstructed from `myblog_worker` history on 2026-10-15
(`git log -- worker/service/lyrics_{matcher,promote,reassessment_service,eval_core,label_yield}.py`).
They describe what the commits say they did. Effects are filled in only where a number was recorded.

| Version | Date | PR | Change | Why / effect |
|---|---|---|---|---|
| `step2-v2` | 2026-07-01 | worker #55 | Canonical `decide_match` over the real LRCLIB schema: artist identity, exact/fuzzy title, ±2 s, version tokens | First matcher. Still the version of 9,099 resolved rows on 2026-10-15 (RC5) |
| `step2-v2` | 2026-07-02 | worker #56 | `TrackLyricsWriter` hardening: NUL strip, synced-only rows get `lyric_plain=''` | Rows were being silently dropped by the CHECK |
| — | 2026-07-02 | worker #58 | Periodic reassessment and the never-downgrade replacement guard | Origin of RC4: exact-title rows are never re-selected |
| `+best-of-v1` | 2026-07-03 | worker #60, #61 | Best-of promotion (tier 1) for `ambiguous` / `review_required` | 771 matched + 180 no_lyrics promoted rows on 2026-10-15 |
| `step3-v1` | 2026-07-04 | worker #64 | Noise strip: track-number prefix, non-rendition parentheses, dash segments | Fixed false ambiguity. Introduced RC2 (deny-list strip → Go Go) |
| — | 2026-07-26 | worker #80 | Search LRCLIB with the primary artist, not the alphabetical one | Featured guests were becoming the search artist |
| — | 2026-07-28 | worker #84, #85, #86 | Park dead-source labels by measured yield; album-scoped re-check | Retrieval and scheduling only |
| — | 2026-08-03 | worker #93 | Best-of backlog drained ahead of the unresolved queue | Scheduling only |
| — | 2026-09-09 | worker #104 | Targeted source collection for album demand (V57) | New producer, same decision core |
| *next* | — | — | Step 1 of this RFC: content consensus, rendition markers | Bad Habit (RC1), Go Go (RC2) |

## Open questions

1. **Daily report limit per member** — proposal 20/day. Blocks Step 3.
2. **Does a stale translation re-queue itself after a replacement?** `attach_translation` shows
   `stale`. Whether album-demand work re-links to the new fingerprint without a viewer re-request is
   unverified. Audit at Step 2 kickoff.
3. **Consensus similarity threshold** — 0.6 ratio on the first 500 normalized chars was used for the
   probe. It produced 2 false positives in 200 (transcription variants), so it is not the measure to
   ship. Tune against Step 1 fixtures. Blocks Step 1.

## Decisions log

| Date | Decision | Step |
|------|----------|------|
| 2026-10-15 | Reports are open to every signed-in member (owner) | 3 |
| 2026-10-15 | Step order left to Claude (owner); chosen: matcher → re-sweep → report/reject → signals | all |
| 2026-10-15 | A report triggers a recheck and never unlinks lyrics by itself | 3 |
| 2026-10-15 | Root causes recorded (RC1–RC6). Every matcher change carries a patch-notes entry (owner) | all |
| 2026-10-15 | After the prior-art comparison: the owner's candidate panel with pick-and-lock is the core. Members report only; the owner decides (owner) | 3 |
