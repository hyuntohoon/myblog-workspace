# FEAT-lyrics-match-correction: detect and correct wrongly attached lyrics

- **Status**: accepted (owner approval 2026-10-16)
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

**Manual fix 2026-10-16 (owner-approved, prod data write).** The row now carries LRCLIB 34738767
(`Bad Habit (Single)`, 232 s, synced), whose body is shared by 19 of today's 20 search results.
Evidence keeps `basis=exact-title`, `matcher_version=step3-v1`, and adds
`manual_fix {replaced_lrclib_id: 8996695, …}`. Verified through `GET /api/lyrics/4k6Uh1HXdhtusDW5y8Gbvy`
as the smoke member: first line `I wish I knew you—`, translation `stale`, no Korean text served.
There is no lock until Step 3a; a later sweep that re-evaluates the row under the Step 1 matcher
picks the same majority body, so it does not reintroduce Ed Sheeran.

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
| `lyrics_reassessment` | unresolved rows + `best-of-*` matched rows; optional `album_id` scope. *Since Step 2 (worker #114): also a re-sweep arm over resolved rows from any other matcher version (`sweep_limit`), and a single-row `track_id` scope* | EventBridge + manual SQS |
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
| B′ | Language version uploaded **under the plain title** | BTS `Go Go`: 16 of the 17 plausible uploads titled plain `Go Go` carry the Japanese body; one (23791915) carries the Korean one | **not by Step 1** — consensus follows the majority. Panel (3a) or a report |
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
   ├─ reject X    → rejection row; if X is served: taken down now + recheck (unlocked)
   └─ unlock      → back to automatic + recheck
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
  record why not. *(Corrected at Step 1: `lyrics_batch_api.py`, `lyrics_dump_matcher.py`,
  `lyrics_bestof_backfill.py`, `lyrics_bestof_probe.py` and `lyrics_matcher_noise_probe.py` put `myblog_worker` on `sys.path` and
  import `decide_match` / `promote_best` from it. Only the selection SQL is duplicated. The decision
  change therefore reaches them with no copy to edit.)*

**Verification:** unit tests built from the two real cases (Bad Habit's 20 + 1 candidates; Go Go /
Go Go - Japanese ver.). Mutation-check each new test: remove the consensus key, then the token, and
confirm the test fails. Worker `test` check green.

**Step 1 result (2026-10-16).**

- Fixtures: `tests/fixtures/lyrics_consensus.json` holds real LRCLIB responses for Bad Habit (20 + the
  stored 8996695), Big Poe, BEEP BEEP and Go Go (+ 13611969). Lyric words are replaced by hash tokens
  after the matcher's own strip and normalization, so similarity is exact and no lyric text is
  committed.
- Mutation: 12 mutants, 12 killed. They removed the consensus key, the disagreement park, `ver`, the
  language tokens, the `ver`→`version` alias, the ad-lib strip and the apostrophe strip; reverted the
  window to 150 words; raised the threshold to 0.6; and in best-of, dropped the disagreement guard,
  the top-level id and the consensus rank.
- Replay before shipping: 168 production tracks (120 random `matched`, 28 with a Hangul-named artist,
  20 `ambiguous`/`review_required`). Each was re-searched on LRCLIB sequentially (0 errors) and the
  same candidates were run through `origin/main` and the new matcher (+ best-of).
  - 167 had an identical outcome.
  - 0 parked as `content_disagreement`.
  - 1 changed: G-DRAGON `One Of A Kind`, from 26071681 to 26034284. It is the same song in the
    transcription shared by 3 of the 5 plausible candidates.
  - Control: the old matcher on today's candidates reproduces the stored pick for 90 / 148 matched
    rows. The rest is retrieval drift since the original write, not a matcher difference.
- Class B′ (above): `Go Go` itself is **not** fixed by Step 1, because the Japanese body is the
  majority under the plain title. Step 2 will not change it either; it needs the Step 3a panel.

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
*Amended 2026-10-16 (owner):* Bad Habit had already been fixed by hand (`evidence.manual_fix`)
before Step 2 shipped, and the owner kept the lock. So the check became: the `{track_id}` run on
Bad Habit reports `locked`, and its body stays unchanged.

**Step 2 result (2026-10-16).**

- Shipped in worker #114 (`2fedef3`). The lateral rule (`assess_lateral` / `should_replace`): same
  basis, older matcher, content differs, new cluster strictly larger. The re-sweep arm is
  `_fetch_stale_version_tracks`. It orders by numeric `stepN-vM`, excludes rows already stamped under
  the running version, and excludes `manual_fix` / `basis='manual'` / `excluded_by`. Each judged row
  gets an `evidence.resweep` stamp with a verdict (`replaced` / `superseded` / `unchanged` / `kept` /
  `parked` / `locked`). The `track_id` scope runs through `reassess_track`. The lock is checked
  first: a hand-fixed row is never rewritten by any producer.
- **Shadow mode first** (owner). `LYRICS_RESWEEP_SHADOW` shipped on. Shadow mode stamps
  `evidence.resweep_shadow`, and its `would_replace` / `would_supersede` verdicts mark a would-be
  rewrite without writing it. The only write allowed in shadow is the pre-Step-2 best-of
  supersession.
- Bad Habit via `{"job":"lyrics_reassessment","track_id":…}` gave `resweep_locked=1`, verdict
  `locked`, `same_content=true` (cluster 11 / 11), and the body unchanged.
- Shadow drain: 18,166 eligible rows (`step2-v2` 9,099 · `step3-v1` 9,067). 70 sequential
  slices, about 2 h, and 0 eligible rows left at the end. Verdicts per row:

  | verdict | matched | no_lyrics |
  |---|---:|---:|
  | unchanged | 16,779 | – |
  | parked | 167 | 1,163 |
  | would_replace | 32 | 1 |
  | would_supersede | – | 9 |
  | superseded (real write: best-of → exact-title) | 10 | – |
  | kept | 5 | – |
  | locked¹ | 1 | – |

  ¹ Bad Habit, from the `track_id` run. The sweep itself excludes `manual_fix`, so this row is not one
  of the 18,166, and the table sums to 18,167.

- **Audit of the 42 would-rewrite rows.** Each old/new pair was fetched from LRCLIB and read by
  hand:
  - **18 corrections.** The old body was another song, a translation, romanised, or a different
    language. Examples: Camila Cabello `In the Dark`, Snow Patrol `It's Beginning To Get To Me`
    (which held `You Could Be Happy`), Kendrick Lamar `Savior` (which held the interlude), Elvis
    Presley `Slicin' Sand` (French text), and ヨルシカ `火星人` (with Vietnamese lines interleaved).
    The no_lyrics → matched corrections include `rockstar`, `Fly Me To The Moon` and `プレデター`.
  - **8 same-song transcription differences.**
  - **8 regressions.** These are the `Go Go` class the owner flagged. Three swap the language
    version (LE SSERAFIM `HOT (Japanese ver.)` → the non-Japanese text; BIGBANG `IF YOU` ×2 → the
    Japanese version). One is a different song (BIGBANG `Bigbang`). Two are junk bodies (BIGBANG
    `Intro (Big Bang)` at 102 lines for 25 s; ABBA `Arrival`, which is instrumental, given a
    metadata stub). Two give lyrics to an instrumental or the wrong language (Evan Call `Beyond the
    Journey's End`; Disney `Happy Ending` → a German fragment).
  - **8 unclear** without listening.
- **Real pass** (owner). First the 16 regression / unclear rows were locked with
  `evidence.manual_fix` (`approved_by: owner`, `kept_lrclib_id`, `rejected_lrclib_id`). Then worker
  #115 (`e01bd34`) turned shadow off and the sweep was drained again under the `evidence.resweep`
  stamp. The drain was emptied 03:11–06:56Z: two
  runs of sequential `sweep_limit=280` slices, 60 s apart because LRCLIB answered 429 / 503. Rows
  skipped on a transient error were simply selected again by a later slice. The end was confirmed
  with the selection's own predicates, which return 0 rows on prod. The script stopped on
  `NO SUMMARY LOG` rather than an empty-queue line: the summary is logged only for a non-empty
  sweep, and `nothing to process` is INFO, which prod drops. Final `evidence.resweep` verdicts:

  | verdict | rows |
  |---|---:|
  | unchanged | 16,779 |
  | parked (no rewrite) | 1,330 |
  | kept | 5 |
  | **replaced** | **20** |
  | **superseded** (no_lyrics / best-of → exact-title) | **6** |
  | total | 18,140 |

  The total is the shadow population, 18,166, minus the 10 best-of rows already superseded for real
  in shadow (re-versioned to `step4-v1`), minus the 16 hand-locked rows. Nothing is missing, so the
  drain left no unstamped consistency-error rows behind.

  The 26 rewrites are exactly the 26 unlocked audited rows (18 corrections + 8 transcription-only).
  None was outside the audited 42, and none of the 16 hand-locked rows was stamped or rewritten.
  The CloudWatch summaries sum to the same 20 + 6. Bad Habit is still locked: `manual_fix`, Steve
  Lacy body, last written by the hand fix. Result posted on worker #115.
  *Not verified:* a real write replaces `evidence` wholesale. So the DB cannot show that each real
  outcome is the LRCLIB id its shadow pass predicted; only membership in the audited list was
  checked.
- **Step 2 closed 2026-10-16.**
- Not fixed by the lateral rule, as designed. A language-version swap is decided by cluster size
  alone, so the rule cannot tell a minority-language original from noise. Those rows need the Step 3a
  panel. A language/script guard in the lateral rule is a candidate for the next matcher bump.
- Operational note (review Y-b). Rows that raise a consistency error are rotated but never stamped.
  On a drain, "done" therefore means `resweep_selected == consistency_errors`, not 0.

### Step 3 — Candidate panel, lock, and member reports (shared_db + backend + worker + front + contract + infra)

The panel is the core of this step and the report is its entry, so the step ships in that order.
3a is usable by the owner alone; 3b adds the member entry.

**3a — Candidate panel and lock (owner)**

- **Schema (next V):**
  - `track_lyrics_candidates(track_id, lrclib_id, title, artist, album, duration_sec, has_synced,
    has_plain, instrumental, preview, cluster_size, verdict, matcher_version, fetched_at)`, PK
    (track_id, lrclib_id) — V63. ~~Written by every evaluation for the plausible set it judged.~~
    *Amended (3a decisions below):* written only by an explicit single-track re-check, replaced
    wholesale, and holding every candidate LRCLIB returned with its verdict. It holds metadata
    and a short preview only (CHECK ≤ 300 chars), never full lyric text.
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
  - New single-track job: `lyrics_pick {track_id, lrclib_id}`. ~~`lyrics_recheck {track_id}`~~ —
    *amended:* the existing `lyrics_reassessment {track_id}` scope (Step 2) is the re-check.
- **Front:** "다른 가사 보기" in the lyrics viewer, owner only. It opens the panel: candidates sorted
  by verdict, each with source, preview and the reason it lost; the current pick and its lock state.

**3a design decisions (2026-10-16, owner; recommendations taken).** Checked against
`origin/main` before building:

- *Already there.* The `{track_id}` scope of `lyrics_reassessment` (Step 2) **is** the
  `lyrics_recheck` job; 3a reuses it rather than adding one. The guard and the re-sweep
  selection already treat `manual_fix` / `basis='manual'` as locked.
- *Gap.* The shared writer (`TrackLyricsWriter.write_outcomes`) had no lock, the demand-source
  selection projects no `existing_locked`, and `manual` was missing from the basis ladder
  (strength 0). So a `manual` "no lyrics" row could be superseded by an `exact-title` from the
  demand job, and a `manual_fix` row (basis `exact-title`) by an `mb-recording` / `isrc` one. 3a puts the lock **in the writer's upsert** (`ON CONFLICT … WHERE NOT locked`),
  which every producer and the `tools/lyrics_*` twin go through; it tests both lock keys
  (`manual_fix`, basis `manual`). `manual` also gets the top rung of the ladder. The owner's
  own pick goes through a separate writer path that is allowed over a lock.
- **Candidate set: stored only by an explicit single-track re-check** (the panel's refresh),
  not by every evaluation. The scheduled jobs would otherwise rewrite up to 20 rows per track
  on every pass. The panel says when nothing is stored and offers the refresh. It shows every
  candidate LRCLIB returned, including the ones a metadata gate dropped, each with its reason.
- **Rejecting the attached candidate takes it down at once.** The row goes to
  `review_required` (`reason='owner_rejected'`) and a re-check is enqueued. If the re-check
  fails (429), the unresolved queue picks the row up anyway. Rejecting any other candidate only
  records it. A rejection never locks.
- **Translation re-queue (OQ2): on an owner pick only,** when the body changed and a
  non-manual translation existed (`done` / `failed` → `requested`). Automatic replacements do
  not re-queue, so a matcher bump cannot flood the poller.
- **A pick is limited to the stored candidate set** (409 otherwise). The worker re-fetches the
  body by id.
- Writes: "no lyrics", reject and unlock are DB-only, so the backend writes them directly.
  Pick and refresh need LRCLIB, so the backend enqueues them for the worker. Unlock removes
  the lock keys, sets the basis to `unlocked` (strength 0) and enqueues a re-check, so the row
  is automatic again.

**Step 3a result (2026-10-16).**

- Shipped: schema V63 (ws #1080, shared_db #92 `b5d0670`, applied to test and prod), backend #189
  (`9fb1071`), worker #117 (`505ab4b`), front #469 (`f896fee`), ws #1082 (`8957a44`: the three
  JWT routes, applied with `3 to add, 0 to change, 0 to destroy`; batch tools filter rejections;
  SQS contract rows), music #81 (`c9e7e2e`, SQS timeout sweep).
- Review changed the design in two places:
  - The lock **and** the owner's rejections are re-read **at write time**, inside the writer's
    upsert, and on the first insert as well. A decision can be a 90 s LRCLIB batch old by the time
    it is written, and the owner may reject the very candidate in between. The pick re-checks
    the rejection under the row lock after its fetch.
  - A refused write counts as `guard_kept` and is touched for rotating callers. The demand
    selection projects `existing_locked`. Without both, a locked row pinned the demand job's
    ladder at the head of its queue.
- The single-track re-check now `LEFT JOIN`s `track_lyrics`, so the panel can refresh a track
  that has never been evaluated. A transient LRCLIB error on it raises, so SQS redelivers.
- Sweep: every SQS client in backend, worker and music now has explicit timeouts (connect 3 s,
  read 5 s, 2 attempts). Other boto3 clients (Cognito, KMS, SSM settings loaders) still use the
  defaults; they predate this step and are not swept here.
- Verification:
  - Tests: worker 771 unit + real-DB, backend 1189 unit + 11 real-DB, front 1515. Mutants
    killed: 10/10 worker, 6/6 backend, 2/2 migration.
  - Real-browser clickthrough against a local backend on the test branch: render, reject the
    served lyric, no lyrics, unlock, the pick's 503 path, and the non-owner control.
  - Prod smoke 32/32. The three routes answer 401 with no token and 403 for a member.
  - A prod refresh of Bad Habit stored 20 candidates. The served 34738767 is `same_body`
    (cluster 11), the body md5 and the `manual_fix` lock are unchanged, and the verdict is
    `locked`. Numbers are in the backend #189, worker #117 and front #469 comments.
- **Not verified on prod:** the owner's own pick through the panel. No owner token in the
  session.

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

**3b design decisions (2026-10-16, owner; recommendations taken after a Fable review).**
Checked against `origin/main` before building:

- **Daily limit (OQ1): 20 reports per member per rolling 24 h**, a setting
  (`LYRICS_REPORT_DAILY_CAP`) like `REVIEW_DAILY_CAP`. Every report created in the window
  counts, resolved ones included, so an owner decision does not refund the budget. A repeat
  on a track the member already has open returns `already_reported` and costs nothing.
- **Re-check only on the track's first open report.** Later reporters only add a row. The
  insert locks the `tracks` row, so two first reporters cannot both enqueue. The member
  re-check carries `cooldown_sec: 3600`: a track re-checked in the last hour is a no-op at
  the worker. The owner's refresh keeps `cooldown_sec: 0`. A member's re-check is
  best effort; the owner queue holds the report either way.
- **What can be reported:** the viewer's own verdicts, `availability` `ok` (lyrics shown) or
  `no_lyrics` (a wrong "가사 없음" is a class the automatic queue never revisits). Anything
  else is 409 `not_reportable`. The first front ships the button on shown lyrics only.
- **Schema amended:** `user_sub` → `user_id` (FK `users.id`, which is the Cognito sub, like
  every member table; the route provisions the row). `reason` (`'member'`, or the Step 4
  signal), a snapshot of what was served (`reported_status`, `reported_lrclib_id`,
  `reported_body_sha`), and `resolution` / `resolved_by`. A second partial unique serves
  Step 4: one open report per (track, signal). A Step 4 open report counts as "another
  open report" and so suppresses a member re-check.
- **Owner queue state is derived, never stored:** `auto_resolved` when the served status or
  body hash differs from the snapshot. Most report-triggered re-checks change nothing on a
  `matched` row (the replacement guard refuses lateral swaps), so the common effect is a
  fresh candidate set for the panel.
- **Closing a report is a panel decision.** New action `keep` ("what it serves is right"):
  resolves the track's open reports and leaves `track_lyrics` and its lock untouched.
  `no_lyrics` and rejecting the served candidate resolve them in the same transaction;
  `pick` resolves them after its send succeeds; rejecting another candidate and `unlock`
  resolve nothing.
- The member response carries no `recheck_enqueued`: it would tell a member that someone
  else reported the track first. The owner queue shows counts, never reporters.

**Step 3b result (2026-10-17).**

- Shipped: schema V64 (ws #1092, shared_db #93 `3b57706`, applied to test and prod), backend #190
  (`a1f104a`), ws #1096 (`2855761`: the two JWT routes, applied with `2 to add, 0 to change,
  0 to destroy`; merged contract; the SQS contract row records `cooldown_sec: 3600`), front #474
  (`c8e0cb7`). The worker needed no change: the track scope of `lyrics_reassessment` already
  honours `cooldown_sec`.
- Review changed the design in one place. A member's reports are serialised by a **per-member**
  advisory lock taken before the per-track one (fixed order, so no deadlock). With the track lock
  alone, parallel reports on different tracks each read the 24 h count before any of them
  committed, so the cap could be overshot, with one LRCLIB re-check per overshoot. The RFC text
  says "the insert locks the `tracks` row"; the code uses an advisory lock keyed on the track,
  which is equivalent. **Step 4's system-report writer must take the same ("track", track_id)
  key** (`_advisory_key` in `lyrics_report_service.py`), or a member's and a signal's first
  reports could both enqueue a re-check.
- Verification:
  - Tests: backend 1203 unit + 305 real-DB (zero skips in CI), front 1548, shared_db 190 in CI.
    Mutants killed: 2/2 migration (member partial unique, author CHECK), 2/2 backend (member
    lock, closing reports before the pick's send).
  - Local smoke and a real-browser clickthrough against a local backend on the test branch:
    member report → confirmation line; owner queue → `auto_resolved` after a simulated re-check →
    panel opens → `keep` closes it; the non-owner control is bounced to `/`.
  - Prod smoke 32/32 after both deploys. On prod: both routes 401 without a token; the queue and
    `keep` 403 for a member; report 404 on an unknown id and 409 `not_reportable` on a track with
    no lyrics row. No report row was written on prod.
- **Not verified on prod:** the owner's view of the queue, and a member report that reaches it
  (no owner token in the session, and no prod write was made from the smoke member).

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
| `step4-v1` | 2026-10-16 | worker #112 | Content consensus ranks right after version agreement; ≥ 2 same-stance bodies that all disagree park as `review_required` / `content_disagreement`. `ver` is a rendition marker; language names count inside segments. Best-of never promotes a `content_disagreement`, ranks tier 1 by consensus, writes top-level `lrclib_id`. Evidence gains `content_cluster_size`, `plausible_count` | Bad Habit (RC1), Go Go `(Japanese Ver.)` (RC2). **Pre-ship replay** (see Step 1 result): 167 / 168 sampled prod tracks unchanged, 0 parked for content, 1 same-song transcription swap. Production effect on stored rows: none until the Step 2 sweep |
| `step4-v1` (unchanged) | 2026-10-16 | worker #114, #115 | Step 2 re-sweep. Resolved rows from older versions are re-judged once per version (`evidence.resweep` stamp). The lateral rule lets the same basis be replaced by a strictly larger content cluster. A hand-fixed row (`manual_fix`) is locked against every producer. Shadow mode came first (#114), then the real pass (#115) | Shadow drain over 18,166 rows: 16,779 unchanged, 1,330 parked (no rewrite), 42 would-rewrite (plus 10 best-of rows superseded for real, 5 kept, and Bad Habit locked). Of those 42: 18 corrections, 8 transcription-only, 8 regressions, 8 unclear. The 16 regression / unclear rows were hand-locked. Real pass: 26 rewrites (20 replaced, 6 superseded), all inside the audited list, 0 locked rows touched |

| `step4-v1` (unchanged) | 2026-10-16 | worker #117 | Step 3a. The writer refuses a locked row (`manual_fix` / basis `manual`) and any outcome attaching a candidate the owner rejected for that track, re-read at write time (first insert included). `run_eval_batch` drops rejected candidates before `decide_match` / `promote_best`. `manual` tops the basis ladder. New owner-only `lyrics_pick` writes a re-fetched body locked. Version string unchanged: the decision core is unchanged for any track without an owner decision. *Entry added after merge in the docs PR, not in #117 itself.* | No row changed by the deploy. Rows the owner rejects or picks change one at a time through the panel |

## Open questions

1. ~~**Daily report limit per member**~~ — **resolved 2026-10-16: 20 per rolling 24 h** (owner, the
   proposal), a setting. See "3b design decisions".
2. ~~**Does a stale translation re-queue itself after a replacement?**~~ — **resolved 2026-10-16:
   no.** The legacy translation poller queues only tracks that have no translation row. The V57
   demand path does not re-pick `done` rows. Only the owner's translation-request POST re-queues a
   stale one. A replaced row keeps serving its old translation marked `stale` until someone requests
   it again. Potential blast radius: 3,179 poller-origin translations if their rows were replaced. The
   real pass replaces only the audited rows, so this stays small. Re-queueing on replacement is left
   to Step 3a.
3. ~~**Consensus similarity threshold**~~ — **resolved 2026-10-16.** Word 3-shingles over the whole
   body (capped at 2,000 words), LRC timestamps, parenthesised ad-libs and apostrophes removed,
   compared with the overlap coefficient; agree at ≥ 0.4. On the real fixtures the lowest same-song
   pair scores 0.55 (Pharrell Williams `Big Poe`, two transcriptions with a different section order),
   Korean vs Japanese `Go Go` 0.22, Bad Habit's Ed Sheeran body vs the good ones 0.01, and unrelated
   songs ≤ 0.01. A leading window was measured and rejected: at 150 words the Big Poe pair falls to
   0.32. The probe's two false positives were misattributed to Travis Scott / Tyler, The Creator; the
   stored rows are SahBabii `BEEP BEEP` and Pharrell Williams `Big Poe (feat. Sk8brd)`, and both are
   now must-agree fixtures.

## Decisions log

| Date | Decision | Step |
|------|----------|------|
| 2026-10-15 | Reports are open to every signed-in member (owner) | 3 |
| 2026-10-15 | Step order left to Claude (owner); chosen: matcher → re-sweep → report/reject → signals | all |
| 2026-10-15 | A report triggers a recheck and never unlinks lyrics by itself | 3 |
| 2026-10-15 | Root causes recorded (RC1–RC6). Every matcher change carries a patch-notes entry (owner) | all |
| 2026-10-15 | After the prior-art comparison: the owner's candidate panel with pick-and-lock is the core. Members report only; the owner decides (owner) | 3 |
| 2026-10-16 | RFC accepted (owner). OQ3 taken on the recommendation: shingle overlap, tuned on real fixtures | 1 |
| 2026-10-16 | Bad Habit fixed by hand on production ahead of Step 2 (owner) | — |
| 2026-10-16 | Consensus ranks **after** version agreement, not first: a larger cluster of a different rendition must not outrank the agreeing one. `content_disagreement` is judged among same-stance candidates only, so the Korean original is not parked just because a Japanese version disagrees | 1 |
| 2026-10-16 | Best-of promotion never promotes a `content_disagreement` park, and ranks its tier 1 by the same consensus before richness. Otherwise the promotion layer would undo the park by picking the richest body | 1 |
| 2026-10-16 | Shadow drain first: the re-sweep judges and stamps every row without rewriting, and the owner reviews the would-rewrite list before the real pass (owner). Why: the lateral rule can overwrite a correct minority body (Go Go reproduced on real data) | 2 |
| 2026-10-16 | The `manual_fix` lock is kept before Step 3a, against the earlier "no lock before 3a" text. Hand-fixed rows are never changed automatically (owner) | 2 |
| 2026-10-16 | Real pass after the audit: the 8 regression and 8 unclear rows are hand-locked (`manual_fix`), then shadow is turned off (owner) | 2 |
| 2026-10-16 | Real pass drained to empty: 26 rewrites, all inside the audited 42. Step 2 closed | 2 |
| 2026-10-16 | 3a: candidate set stored by explicit re-check only; rejecting the attached candidate demotes the row at once; translation re-queued on owner pick only; pick limited to the stored set; lock enforced in the shared writer (owner) | 3a |
| 2026-10-16 | 3a shipped. Review moved the lock and rejection check to write time (first insert included); refused writes rotate like guard-kept rows | 3a |
| 2026-10-16 | OQ1: 20 reports per member per 24 h. A report enqueues the re-check only when the track had no other open report (owner) | 3b |
| 2026-10-16 | 3b: `ok` and `no_lyrics` are reportable; member re-check cooldown 3600 s; owner closes reports with panel decisions plus a new `keep`; `auto_resolved` derived from a served snapshot (owner, after Fable review) | 3b |
| 2026-10-17 | 3b shipped. Review added a per-member advisory lock ahead of the per-track one, so the daily cap holds under parallel reports; Step 4 must reuse the track key | 3b |
