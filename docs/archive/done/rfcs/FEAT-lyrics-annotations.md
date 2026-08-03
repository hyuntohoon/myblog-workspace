# FEAT-lyrics-annotations: lyrics coverage + "the story behind the lyrics"

- **Status**: done (2026-08-03, archived — Thread 1 is built out: R0–R4 and R6 shipped and prod-verified,
  and **R5 was dropped by owner decision** (§6.13) once measurement showed it was a cross-repo step
  buying an owner-only prose tier that R0 itself had called "a bonus, not load-bearing". The one
  scheduled item still outstanding — the six-album KR/EN anchor regression, due 2026-07-29 and never
  run — **was run 2026-08-03** and its result is recorded in §6.6 and §6.13; it changed no code by
  decision. Thread 2 executes under `DATA-catalog-noise-and-lyrics-coverage`. No observation gates
  remain → moved to `docs/archive/done/rfcs/`. Original status line below.)
  <br>_accepted_ (promoted 2026-07-26 with explicit owner approval, hard rule 5)
- **Owner**: 박지훈
- **Created**: 2026-07-25
- **Last investigated**: 2026-07-25 (deep investigation session — supersedes the morning capture)
- **Last updated**: 2026-08-03 (closing pass) — **R5 dropped, and the KR/EN anchor regression finally
  ran** (§6.13). R5's own sizing was the argument against it: `description_ko` is read by no code in
  any repo, so a user-visible tier meant migration → pin rollout → poller → backend → contract → front,
  for 526 descriptions on an owner-only sheet that already renders line-anchored Korean annotations.
  The regression contradicted this document's standing assumption that Korean's only risk was
  coverage: coverage **is** thin (62/202 matched songs carry any annotation vs 553/631 for English),
  **and** anchoring is too (KR placed 14.3/27.3/33.3% vs EN 78.1/74.3/76.4%, the English control
  reproducing *LUX*'s 74.7%). All three Korean albums fall below this RFC's own <40% tier line. Left
  unfixed on purpose — the in-text layer reaches 32 Korean songs / 86 annotations catalog-wide (1.4%
  of volume) and the unmatched drawer is the designed fallback. Previously, **R3 shipped** (§6.12): the nightly draft prompt now carries the
  Genius facts block directly, rendered by research_poller's renderer rather than a third copy. The
  measurement that had deferred R3 the same morning was **wrong in its conclusion** — the overlap it
  found was between *albums holding both artifacts*, not between albums whose note actually contains
  the facts. Re-measured: only **3 of 88** Genius-carrying bucket albums have a note written after
  the facts block shipped. Earlier that day, **R6 shipped** (§6.11): the editor-buckit idea deck now
  carries the catalog-internal graph — credit connectors across bucket albums and lineage edges whose
  far side we own — with four measured noise classes filtered. R5 was also re-measured: it is a
  cross-repo M rather than the poller-only S this table claimed.
  Previously, 2026-07-30 — **post-merge gate closed**: the first real research request ran end
  to end in prod (ONYX, click → note in 9 m 57 s; gate held, nudge fired, 12/12 collected in 21 s,
  claimed at 107 s). It caught two block defects — a wrong-song match cited as confirmed, and zero
  source links on nine matched tracks — now fixed by an evidence layer in `_render_genius_block`
  (§6.10). Previously, 2026-07-29 — **R1/R2/R4 implemented**: research requests are now the Genius
  collection trigger (per-album, lyrics-blind eligibility; catalog-wide matched-lyrics pool retired),
  the research claim gate waits for collection readiness (90-min partial fallback + SQS nudge), and
  the prompt gets an album-level facts block derived from the track tables with a `[확인: Genius]`
  tier (O3 re-resolved to **derive**, §6.9). Viewer sub-thread unchanged and live since 07-28.
- **Plan row**: dropped 2026-08-03 — nothing left to track; history in `git log` and
  `docs/archive/done/2026-08.md`

> **How to read this document.** The 2026-07-25 morning session wrote a capture from a brainstorm.
> A second session the same day re-derived every number from prod, live LRCLIB, and source, and
> **most of the original numbers were wrong** — some by 2.5x, one inverted outright. Everything below
> is the corrected state. §9 lists what was superseded so nobody re-derives it. Every number here is
> reproducible; §10 carries the SQL.
>
> **Thread 1's viewer sub-thread is SHIPPED and running in prod** as of 2026-07-28 (fetch → store →
> Korean bodies → owner-only read → render; PR map → §6.5 "Shipped state"). What remains of Thread 1
> is the research-pipeline half (§6.5 R-table statuses). **Thread 2 now executes under
> `DATA-catalog-noise-and-lyrics-coverage`** (accepted 2026-07-28): its Steps 3–4 — pool hygiene and
> the album expedite, this RFC's §5 Step B/Step A — shipped the same day (worker #84/#85/#86), which
> also resolves the §8 filter-shape blocker.

---

## 1. Goal

Two threads sharing the lyrics substrate, independently shippable.

- **Thread 2 — lyrics-text coverage.** Fill lyrics for albums that matter, instead of waiting ~96 days
  in a queue that never converges. This turned out to be the larger and better-evidenced problem.
- **Thread 1 — "가사 이야기" (lyric annotations).** Surface human-sourced commentary — story, meaning,
  samples, credits — alongside the lyrics viewer, from **Genius**. Owner's framing, verbatim:
  *"목표는 번역이 아닌 가사에 대한 이야기"* (not translation; the *story* behind the lyrics).

Thread 2 is now the lead thread. Thread 1 is gated on a token the owner must create (§7).

## 2. Non-goals

- **Translation.** `track_lyrics_translations` (Sonnet 의역 poller) is untouched.
- **Genius as a lyrics-TEXT source.** The official API never returns lyric text (publisher licensing).
  Getting text means HTML scraping = ToS violation. Ruled out. LRCLIB stays the text source of truth.
- **The undocumented Genius internal API** (`https://genius.com/api/`, no token). It exposes album
  endpoints the official API lacks, but it is undocumented and ToS-gray. Out of scope; noted only so a
  future session does not "discover" it and assume it is fair game.
- **LLM-invented backstory.** The point of Genius is *verified human* facts. An LLM-hybrid with
  `[source?]` marking is a possible future direction, not this RFC's default.
- **Public exposure of raw lyrics.** Owner-only privacy bar stands.

---

## 3. Current state (all re-measured 2026-07-25 against prod)

### 3.1 The trigger chain — how a track gets lyrics

This is the mechanism the rest of the document argues about. Two EventBridge jobs, no others.

```
album ingested (album_ingest daily cron, or SQS album sync)
   └─> tracks rows created
        │
        ├─ [1] lyrics_incremental — EventBridge rate(15 minutes)
        │      selects tracks with NO track_lyrics row, ORDER BY t.created_at DESC (newest first)
        │      LYRICS_INCR_BATCH_LIMIT = 150 per run
        │      writes exactly ONE row per track: matched | not_found | no_lyrics
        │      → myblog_worker/worker/service/lyrics_incremental_service.py:_fetch_uncorpused_tracks
        │
        │   *** THE WRITTEN ROW IS A SENTINEL. `WHERE tl.track_id IS NULL` means incremental
        │       NEVER LOOKS AT THAT TRACK AGAIN — even if the row says not_found. ***
        │
        └─ [2] lyrics_reassessment — EventBridge rate(1 day), fires ~04:11 UTC
               selects the unresolved pool, ORDER BY tl.updated_at ASC (STALEST first)
               LYRICS_REASSESS_BATCH_LIMIT = 150 per run
               promote-only + replacement-guarded (should_replace / _BASIS_STRENGTH_MAP)
               → myblog_worker/worker/service/lyrics_reassessment_service.py:_fetch_unresolved_tracks

manual override (both jobs): SQS blogSQS  {"job":"lyrics_incremental"|"lyrics_reassessment", "limit":N}
                             routed at myblog_worker/worker/handler.py:301 and :310
```

**The structural defect.** A brand-new album gets its *single* first-pass attempt within 15 minutes of
ingest — precisely when LRCLIB is least likely to have it, because the crowd has not uploaded yet. It
then falls into a stalest-first queue whose head is still 2026-07-01. There is no album-scoped path and
no "try again in a few days" tier. This exactly explains the Charli XCX case in §3.3.

### 3.2 Queue arithmetic — the pool diverges

| Quantity | Measured value |
|---|---|
| Selectable pool | **16,808** = 14,057 tier-0 (14,035 `not_found` + 22 `review_required`) + 2,751 tier-1 (best-of matched) |
| `ambiguous` rows | **0** — the status is inert; stop describing the pool with it |
| Re-check rate | **146.25/day** (2,925 rewrites over 07-05..07-24). Batch limit 150 is binding |
| **Actual drain** | **2.25/day** (45 rows left the pool in those 20 days) |
| Promotion hit rate | **1.54%** (45 / 2,925) |
| Intake of new unresolved | **129/day median** (23d); mean 186/day; 217/day over 10d is spike-inflated by a 993-row day |
| **Net pool growth** | **≈ +180/day.** Pool went ~10,425 → 14,057 in 20 days (+35%) |
| Reachable cycle | **96 days, stretching ~1.2 days per elapsed day** |
| Never re-checked once | **10,536 of 14,057** tier-0 rows. Queue head is still `2026-07-01 11:06` |

**"Just raise `LYRICS_REASSESS_BATCH_LIMIT`" is dead.** The binding constraint is the 1.54% hit rate,
not re-check volume — break-even needs ~60x the limit. And LRCLIB already returns 429 at concurrency 20
(12 skips on 07-23, 22 on 07-24, zero before). Wall-clock headroom exists (37–43s of a 90s budget) but
the throttle does not.

**Dead code path found.** `_fetch_unresolved_tracks` sorts tier-0 before tier-1 with `LIMIT 150`, and
tier-0 holds 14,057 rows — so the 2,751 tier-1 best-of rows are **structurally unreachable**. The
exact-title-supersedes-best-of promise documented at `lyrics_reassessment_service.py:77-82` has never
executed in production. `_BASIS_STRENGTH_MAP` is correct but dead. Fixing it needs a reserved slot or a
separate cadence, not a bigger limit.

### 3.3 What re-checking is actually worth (live LRCLIB probes)

The morning session concluded "recency is not the signal." **That was inverted** — recency was masked by
classical noise.

| Population | Live LRCLIB flip rate |
|---|---|
| Raw `not_found` pool, random | **0.8%** (1/120) |
| Album released ≤60d **and non-classical** | **26.7%** (32/120) — a **32x lift** |
| Album released 60–365d | 3.3% |
| Album released >1 year | 0.0% |
| Album is in a review bucket (owner picked it) | 25.6% (33/129) — **no lift over plain recency** |
| Any `not_found` row on a classical-tagged album | **0/120** |
| Korean-language releases, even brand-new | **0/6, 0/12** |

Two conclusions:

1. **"New + non-Korean + non-classical" is the yield.** Not "the album the owner cares about" — bucket
   membership adds nothing measurable. A recency-tiered re-check would harvest ~27% automatically.
2. **The classical exclusion is what unmasks this.** The earlier 0/30 probe failed because 4,188 of
   5,205 recent-release rows were classical.

**Charli XCX "Music, Fashion, Film" (2026-07-24)** — the case that started this. Morning capture said
1 of 8 unmatched tracks was on LRCLIB. **Now all 8/8 resolve** through the real `decide_match`. The rows
still sit at `not_found`, untouched since 07-23 23:38, **13,698 places back in the queue = 94 days** to
their next automatic re-check. The gap is 100% our re-check latency; LRCLIB coverage for this album is
complete.

### 3.4 What the pool actually contains

**Do not call it "instrumental."** All 14,035 `not_found` rows carry `reason='no_plausible_candidate'`,
which means *LRCLIB has no record* — not *the work has no lyrics*. The matcher's genuine instrumental
verdict is a **different status**, `no_lyrics`, firing 882 times, and **435 of those are classical**.
Honest phrasing: *"classical-tagged albums, empirically ~0 yield on LRCLIB."*

Classical footprint: 179 albums / 5,828 tracks / 5,343 `not_found` rows (38% of the pool) / 49 matched.
Owner engagement with classical is ~0 across every signal (15 of 1,062 saved; 1 of 117 bucket items;
1 of 78 research notes; 0.0–1.1% of listening). It is a **catalog artifact** — last full week, 1,610 of
2,153 new tracks (75%) were classical.

### 3.5 The Korean-language problem (new; not in the morning capture)

The morning capture worried that owner taste (classical / K-pop) meant weak Genius coverage. The
classical half is **refuted**. The K-pop half was **mis-measured and is worse than stated**:

- the `k-pop` genre bucket is only 4.7% of engagement, **but 47.4% of the engaged track set is
  Korean-language**, and the largest bucket (hip-hop) is **71.9–83.4% Korean rap**
- Korean releases do not fill on LRCLIB either — 0/6 and 0/12 on brand-new Korean albums, against
  75–100% for Western major releases

So **Korean-language coverage is the single biggest risk to both threads**, and the owner has confirmed
it needs solving. An album-expedite button will do nothing on a Korean album. Any Genius coverage gate
must have a Korean stratum floor or it will pass on a Western sample and fail in real use.

### 3.6 Two matcher defects found in passing

Both are pre-existing and independent of this RFC. **Both were fixed 2026-07-26** (worker #80/#81 +
workspace #698; detail → the `FIX-lyrics-primary-artist + FIX-isrc-backfill` row in `docs/plan.md`,
resolution notes → `DATA-catalog-noise-and-lyrics-coverage.md` "Related defects"). Left in place
because §3.x cites these numbers — **do not re-file as new work.**

1. **Search artist is the alphabetically-first credit, not the primary.**
   `lyrics_eval_core.fetch_one` uses `artist_names[0]`, and `artist_names` comes from
   `ARRAY_AGG(DISTINCT a.name)` — which sorts alphabetically. On a multi-credit track the featured
   guest becomes the LRCLIB search artist: *"Ariana Grande – I Don't Do Drugs (feat. Ariana Grande)"*,
   *"The Quiett – life (feat. The Quiett)"*. **8,765 of 14,035 `not_found` rows (62%) have ≥2 credited
   artists.** `track_artists.role` is NULL on all 44,546 rows, so there is no primary-artist signal to
   fix it with today — the fix needs Spotify's artist ORDER captured at sync time.
   **Duplicated in both lyrics services → twin sweep in one PR.**

2. **`isrc_backfill` was never scheduled.** Service, handler routing (`handler.py:284`), and an
   integration test all exist, but **no `aws_cloudwatch_event_rule` schedules it** — hence
   `tracks.isrc` is 100% NULL. Worse, it writes string sentinels `"not_found"`/`"no_isrc"` into the
   column, so the day it runs every `isrc IS NOT NULL` predicate silently breaks. Note
   `tracks.ext_refs->>'isrc'` **is** populated on 7,335 rows. Move the sentinel before scheduling.

---

## 4. Filtering: how to keep noise out (the 2026-07-25 design thread)

The owner's requirement, in their words: the exclusion must be **verifiable later**, must **not depend
on the owner's own whitelist** (*"이 프로젝트는 사용자가 있는 사이트로 활용할거야"*), and must not be a
blanket genre ban (*"lux 앨범에 클래식 장르가 붙은건 오류가 아니야"* — the tag is correct).

### 4.1 Candidates measured against ground truth

Negatives = the 11,664 `matched` rows (proven to have lyrics). A "false positive" would park a track
that demonstrably has lyrics.

| Rule | Catches (of 14,035 `not_found`) | False positives |
|---|---|---|
| A. album has `classical` genre tag | 5,343 | **49** — incl. 29 ROSALÍA `LUX` tracks |
| B. title matches instrumental-form regex (loose) | 3,836 | 256 |
| C. A **and** B | 3,734 | 1 |
| D. A **or** B | 5,445 | 304 |
| **E. A + instrumental-form + NOT vocal-form** (refined) | **3,494** | **0** |
| **F. empirical label yield** (see 4.3) | **3,493 (24.9%)** | **2** |

### 4.2 Traps found while refining (each cost a real album)

- **Genre tag alone deletes ROSALÍA `LUX`** (29 tracks). The tag is *correct* — LUX genuinely has
  classical character — which is exactly why genre alone must never decide.
- **Roman-numeral regex eats English initialisms**: `I.F.L.Y.` (Bazzi), `V.I.P` (BIGBANG), `X.Y.U.`
  (Smashing Pumpkins), `XXX. FEAT. U2.` (Kendrick Lamar), `I Can't`. Fix: require the numeral to be
  followed by `[.):]` **and a space**.
- **Classical vocabulary appears in pop titles**: `Symphony` (Zara Larsson), `Ghetto Symphony` (A$AP
  Rocky), `Autumn Nocturne` (Smashing Pumpkins), `4th Baby Mama - Prelude` (Summer Walker).
- **Vocal classical forms have text and must be protected**: `cantata` was wrongly in the instrumental
  list. The vocal guard (`requiem|mass in|missa|cantata|oratorio|aria|lieder|lied|opera|chorus|choral|
  hymn|psalm|magnificat|stabat mater|passion|motet|madrigal|ave maria|te deum|vespers|song|chanson`)
  keeps **198** pool rows that genuinely have text (e.g. Mozart *Requiem – Lacrimosa*, which the owner
  has saved).
- **Substring matching on Korean genre strings is catastrophic.** `클래식` is a substring of
  `클래식 록` (classic **rock**), `클래식 소울`, `클래식 컨트리`, `바로크 팝`, `클래식 크로스오버`.
  A substring rule would have removed **AC/DC, Led Zeppelin, Pink Floyd, Queen, The Rolling Stones,
  James Brown, Stevie Wonder, Johnny Cash, Dolly Parton, Andrea Bocelli, Pavarotti, 조수미**.
  Genre terms must be matched **exactly**, from an allowlist.
- **Even exact genre matching hits real listening**: Ryuichi Sakamoto (`Aqua`, `Blu`), 조수미
  (`The Water Is Wide`), Mozart `Requiem – Lacrimosa` are all saved by the owner and all carry a
  classical artist-genre.

### 4.3 The better filter the owner asked for: empirical label yield

`albums.label`, `albums.album_type`, and `albums.popularity` are **already stored and unused**.

`album_type` is a dead end — `compilation` has the *highest* match rate (62%), so the
"compilation farm" theory does not hold.

`label` is the strongest signal found. Labels with a measured **0% match rate over hundreds of attempts**:

| Label | `not_found` | `matched` |
|---|---|---|
| Novus Promusica | 1,041 | **0** |
| Warner Classics | 684 | 1 |
| Digital Devs | 300 | **0** |
| CPO | 283 | **0** |
| SWR Classic | 245 | **0** |
| Oehms Classics | 196 | **0** |
| Naxos Special Projects | 174 | **0** |
| Gramola Records | 155 | **0** |
| New Wave Records / ADA | 122 | **0** |

Rule F: *a label with ≥50 corpus attempts and a <2% match rate is a dead source.*
→ **15 labels, 3,493 rows (24.9% of the pool), 2 false positives.**

Why this is the better shape:

- **Not a taste judgment and not a genre judgment.** It is a measurement of our own source coverage,
  computed from our own data. Identical for every user of the site.
- **Self-correcting.** If a label starts matching, its statistic moves and the exclusion lifts on its
  own. No human re-tuning.
- **Generalizes beyond classical** — it independently caught `Digital Devs`, `New Wave Records / ADA`,
  and flagged `UME - Global Clearing House` (1,860/63 = 3%).
- **No regex, no genre dependency, no per-title vocabulary to maintain.**

Its weakness is cold-start: a new label has no statistic, so it cannot gate a first release. Rule E
covers exactly that case. **They compose** — E as a static prior, F as the learned signal.

### 4.4 Verifiability (owner requirement)

1. **Mark, never delete.** Write the reason + rule version + timestamp into the existing
   `track_lyrics.evidence` JSONB. Reversal is one `UPDATE`.
2. **5% holdout — the load-bearing safeguard.** Leave a random ~5% (≈175 rows) of the excluded set
   *in* the queue, still being re-checked. If the rule is right their promotion rate stays ~0. If it
   climbs, **that rate is the misclassification rate**, measured continuously with no human effort.
   This matters more than usual because the justification is *source coverage*, which can change: if
   LRCLIB ever ingests classical, the holdout is what tells us.
3. **Standing monthly audit** — of the excluded set, how many were later engaged with, and does the
   holdout promotion rate exceed the pool baseline of **1.54% (45 promotions / 2,925 re-checks over 20
   days)**.

### 4.5 Per-surface policy (settled 2026-07-25)

The owner's multi-user point forces different answers per surface. "Exclude classical everywhere" is wrong.

| Surface | Policy | Why |
|---|---|---|
| **Search** | **Do not filter. Fix ranking.** | A classical-liking user must be able to find Chopin. The defect is that relevance ranking is dead — `Butterfly` returns 20 consecutive *Madama Butterfly* scenes. Audit severity **high**; fix is read-side in `myblog_music`, one PR, no contract change. |
| **Lyrics queue** | Exclude via E + F, marked + holdout | Justified by measured 0-yield from our only source. |
| **New releases / ingest** | Filter **spam fingerprint**, not genre | A legitimate classical release should still appear. What nobody wants is `"077 Piano Essentials": Delicatessa` credited to Beethoven. |
| **Daily picks / editorial / research** | **Do not touch** | Audited clean. Every row is owner-initiated; a filter would only delete the owner's own choices — and would have removed `LUX`. |

**Release-calendar reality check.** The ledger `artist_release_events` is 20.5% classical over a 180-day
window (98 of 478), but what actually *renders* is far less: home "새 앨범" strip **0/12**, `/releases/`
July landing view **2/148 (1.4%)**. It is not a flood today; it is growing, and the fix is cheap.
Spam fingerprint on the release title catches 22/478 — require a **leading quote** before the number or
it eats `22 Durnham Dew`, `100 Degrees`, `556 - Single`.

---

## 5. Thread 2 plan (not yet approved)

Owner has chosen scope: **expedite + pool hygiene, plus ingest blocking, plus the same exclusion on the
release calendar.** Owner also decided the MFF tracks get filled **by the feature**, not by a manual
prod write.

**Sequence Step B before Step A.** Both edit the same ~20-line SQL block
(`lyrics_reassessment_service.py:138-163`); second-to-merge conflicts. B-first also means A's
`_fetch_album_tracks` is copied from an already-correct source — and that copy must **omit** the
exclusion, since the expedite path must always bypass it.

- **Step B — pool hygiene.** Apply rule E (+F when ready), marked + 5% holdout, and filter at intake so
  the rows stop entering. Success metric: pool stops growing — net daily change ≤ 0, measured against
  the current **+180/day**.
- **Step A — album-scoped expedite.** PR1 only: `reassess_album(album_id, limit, cooldown_sec)` +
  `_fetch_album_tracks` + one handler dispatch line + a cooldown setting. ~40 lines, worker-only, no
  `terraform apply`, no contract regen; fired by one `aws sqs send-message`. The proposed SQL was
  verified read-only against prod with the real MFF album id and returns exactly those 8 rows.
  **Defer PR2** (owner-gated `POST` + button): it costs an `infra/apigateway.tf` route, a human
  `terraform apply`, and an openapi/`api.gen.ts` round trip across three repos — for a surface used
  once or twice a week (`review_bucket_items` is 117 rows lifetime).
- **Consider instead/also: recency-tiered re-check.** Given §3.3, re-ordering the daily job to favour
  recent non-classical releases would raise the hit rate from 1.54% toward ~27% with no new surface at
  all. This may be worth more than the expedite button. **Not yet designed.**

---

## 6. Thread 1 — Genius (token issued 2026-07-25; live-tested against ROSALÍA *LUX*)

Status changed materially on 2026-07-25: the owner issued a client access token, and Thread 1 moved
from speculation to measurement. Everything in this section was verified against the live official API
unless marked otherwise.

### 6.1 Verified API surface

Base `https://api.genius.com/`, header `Authorization: Bearer <token>`. A **client access token is
sufficient** for all reads. `GET /account` needs scope `me` and 401s even with a valid token — **never
use it as a preflight**; use `GET /songs/<known-id>` (verified: 200 vs 401).

| Endpoint | Gives |
|---|---|
| `GET /search?q=&per_page(max 5)` | `hits[].result`: `id`, `title`, `primary_artist`, `annotation_count`, `stats.pageviews`, `url` |
| `GET /songs/{id}?text_format=plain\|html\|markdown\|dom` | `description`, `song_relationships`, `producer_artists`, `writer_artists`, `custom_performances`, `media`, `album`, `language`, `recording_location`, `release_date_for_display`, `apple_music_id`, `translation_songs` |
| `GET /referents?song_id=&per_page(max 50)&page` | `referents[]`: `fragment`, `range`, `classification`, `annotations[]` (`body`, `verified`, `votes_total`) |
| `GET /artists/{id}`, `/artists/{id}/songs`, `/annotations/{id}`, `/web_pages/lookup` | metadata |

No official album endpoint. Album/comments/contributors exist only on the undocumented internal
`https://genius.com/api/` — out of scope, noted so a future session does not "discover" it.

**`song_relationships` type vocabulary** (confirmed from a live response): `samples`, `sampled_in`,
`interpolates`, `interpolated_by`, `cover_of`, `covered_by`, `remix_of`, `remixed_by`,
`live_version_of`, `performed_live_as`, `translation_of`, `translations`.

**`media` carries cross-service IDs** — a Sia lookup returned `spotify:track:4VrWlk8IQxevMvERoX08iC`
plus `apple_music_id`. When present this confirms a match exactly against `tracks.spotify_id`. **But it
is not universal**: only 1 of 16 sampled library tracks and 0 of 15 LUX tracks carried a Spotify link.
Treat it as a match-confidence upgrade, never as the primary key.

### 6.2 Measured coverage — the language split is the whole story

16 tracks sampled from the owner's saved tracks, 8 English / 8 Korean, each run through
`/search` → `/songs` → `/referents`:

| Channel | English | Korean |
|---|---|---|
| description ≥200 chars | **7/8** | **1/8** |
| ≥3 annotated lines | **7/8** | **0/8** |
| **credits (writers/producers)** | **7/8** | **7/8** |
| relationships present | 7/8 | 2/8 |

**Credits are language-independent; prose is not.** 로꼬, pH-1, BewhY, UNEDUCATED KID and 실리카겔 all
returned 0-char descriptions and 0 annotations — but 실리카겔's *Desert Eagle* still returned writers
(김춘추·김한주·김건재·최웅희), producer, arranger, label (매직스트로베리사운드), distributor, and three
engineer roles. Given that 47.4% of the owner's engagement is Korean-language (§3.5), **any Genius
feature that depends on prose will be empty for roughly half the library, and any feature built on
credits or relationships will not.**

One matching failure worth recording: 로꼬's *2025* matched to *"2025 by Molly Yam (Ft. Loco)"* with
`language=en`. Match confidence must be stored per row, or wrong credits enter a review silently.

### 6.3 The *LUX* live test (2026-07-25) — what a full album actually yields

45 API calls, ~25 seconds, all 15 tracks matched on title+artist. Raw dumps and the assembled Korean
material are in the session scratchpad.

- **13/15 descriptions** (157–1,956 chars); **115 annotations**; **0 verified** — every annotation is
  unverified fan writing, votes ranging **−17 to +63, median 9**
- `annotation_count` sums to 128 vs 115 stored: the 13-row difference is exactly the 13 tracks with a
  description, because **Genius counts the song description as one annotation**
- credits are deep: *Berghain* alone carries **55 performance roles**

Facts a critic would not otherwise get, all from credits/relationships:

- **The production core is four people, not three.** David Rodríguez has a producer credit on 1 track
  but is recording engineer + additional production + vocal producer on **15/15**.
- **`Transcription (Notation)` — Kyle Gordon, 15/15.** The album was made to exist as a score; the
  first teaser was piano/vocal sheet images.
- **Recording geography is a division of labour**: four fixed rooms on every track (Larrabee LA,
  Noah's Studio LA, FB House Miami, Air Studios London) plus L'Auditori Barcelona ×10, La Fabrique ×7,
  Escolania de Montserrat ×6, A Tempo Sevilla ×5.
- **Guests are tradition-bearers, not features**: Carminho (fado), Estrella Morente (flamenco),
  Sílvia Pérez Cruz (Catalan), Yahritza Y Su Esencia (sierreño). Björk also takes a writing credit.
- **Pop hitmakers sit underneath**: Ryan Tedder ×2, Pharrell Williams, The-Dream, Andrew Wyatt,
  Tobias Jesso Jr., Guy-Manuel de Homem-Christo. *Magnolias* has 8 writers; *Mio Cristo Piange
  Diamanti* is the only solo-written track. This tension is the most useful thing the data gives.
- **`Translator` credits on 4 tracks** — Asa Kanaseki (JA), Lisa Salker (DE), Halyna Hrabovska (UK),
  Mark Gamal (AR). Multilingualism was **commissioned work**, not improvisation. `language` returns one
  tag per song and is unreliable; at least 11 languages appear across the album.
- **Interpolations**: *Divinize* ← Daniel Johnston *"Some Things Last a Long Time"*; *De Madrugá* ←
  ROSALÍA's own 2018 track. Also official derivatives (Berghain ×2 remixes, *Sauvignon Blanc* a cappella
  + instrumental, *Dios Es Un Stalker* versión Francotiradora).

Reception signal from the 115 unverified annotations: **22 of 115 (19%) are translations rather than
interpretation**, and those drew the highest votes (55, 55, 50). The album's primary reception need was
subtitles. Separately, 8 of 15 tracks are linked by annotators to named female mystics across five
traditions, and the language placement tracks those figures (Arabic ← Sufi Rabia, Japanese ← Zen Ryōnen,
Ukrainian ← Olga of Kyiv).

**Lyric fragments are not reproduced in our derived documents.** The translation pass rendered
descriptions and annotation bodies but pointed at `annotations[i].fragment` in the raw JSON plus the
Genius link instead of copying lyric text. Keep that convention.

### 6.4 Why this fits the research-note pipeline — evidence from 78 real notes

All 78 stored `album_research` notes were read. Every one carries a `출처 못 찾은 것` (could not source)
section, and:

- **78/78 record a failure to confirm samples**
- **75/78 record a failure to confirm credits**

Verbatim from real notes: *"WhoSampled 등 샘플 DB는 페이지 페치가 막혀 스니펫조차 확보 못 함 → 단정
불가"* (뱃사공 『파랑』); *"WhoSampled 1차 페이지: 알려진 fetch-차단 사이트"* (Frank Ocean 『Blonde』);
*"FADER 작사크레딧 표에 'No credited writers listed'로 비어 있는 트랙 존재"*; *"녹음 장소/스튜디오,
정확한 곡별 세션 연주자 매핑 — 위키 인포박스 수준 이상으로는 확인 못 함"* (『CHROMAKOPIA』).

The prompt (`scripts/album_research_v2.md:75-82`) makes `샘플링 / 기반` its **★최우선** section and
names WhoSampled as a known fetch-blocked site. **The pipeline's own 78-run record of what it cannot
find is precisely the field set Genius returns.** That is the justification for Thread 1, and it is
stronger than the lyrics-viewer case.

### 6.5 Plan — R0 through R6

Sequenced; R0 gates everything.

#### R0 RESULT (2026-07-27) — the gate passes

Ran `tools/genius_probe.py --full-run` over **every track of every bucketed album**: 1,073 tracks,
87 albums, no sampling. A track counts as matched only when its normalized title matches exactly, or
when the first hit's primary artist agrees — an artist mismatch is a wrong song and counting it would
inflate the number this probe exists to measure.

| | |
|---|---|
| track match rate | **938 / 1,073 = 87.4%** (86.2% of those exact-title) |
| albums fully matched | 52 / 87 |
| albums with zero matches | **4 / 87** |

Fill rate **on matched tracks** — this is what R1 would materialise:

| Field | Fill | The notes' own record (§6.4) |
|---|---|---|
| 작가·프로듀서 credits | **96.9%** | 75 of 78 notes failed to confirm credits |
| 세션 연주자 performers | **79.5%** | named as unobtainable in several notes |
| 해설 산문 description ≥200 chars | 52.5% | — |
| 샘플·인터폴레이션 relationships | **48.6%** | **78 of 78 notes failed to confirm samples** |
| 녹음 장소 recording location | 30.1% | named as unobtainable |

**Verdict: build R1.** The two fields the pipeline has never once managed to source are the two
Genius fills best. Credits at 96.9% closes the 75/78 failure outright.

Three things worth carrying forward:

1. **48.6% on relationships is not a shortfall.** Many of these albums genuinely have no sample to
   find. The change is not "48.6% coverage" but that a *confirmed absence* replaces "확인 불가" — the
   note currently cannot distinguish "no sample" from "could not check", and 78/78 of them say so.
2. **Relationships run in both directions, and the reverse edge is new.** Outbound —
   `interpolates` 149, `samples` 132 — is what the album was built from, which the notes already try
   (and fail) to establish. Inbound — `sampled_in` 214, `interpolated_by` 174, `covered_by` 177 — is
   what the album later *became material for*. No note has ever carried that, and it is lineage the
   critic cannot get by listening. It also feeds R6's catalog-internal graph directly.
3. **Lower two temper expectations for R5.** Description clears 200 chars on about half of matched
   tracks and recording location on 30%, so the prose tier is a bonus, not a load-bearing field.
   Size R5 accordingly.

A per-language column exists in the probe output (65.4% en / 31.9% ko of matched tracks) and is
deliberately **not** used as a gate — owner decision 2026-07-27, the build/no-build call is made on
the overall numbers.

Raw rows: `tools/out/genius_probe.jsonl` (gitignored; re-runnable and resumable).

#### Shipped state (2026-07-28) — the §6.6/§6.9 viewer sub-thread is live end-to-end

The pipeline this table's R-steps consume from shipped **outside the R-numbering**, as the viewer
sub-thread. Every leg is merged and running in prod:

| Leg | Where | PRs |
|---|---|---|
| Fetch | worker `genius_fetch` job — writes the `track_genius_songs` row **before** its `track_genius_annotations`, one transaction per track; 15 tracks/run; unset token = logged no-op. **Retargeted 2026-07-29**: eligibility is now research demand (`album_research` albums, active requests first, lyrics-blind) + an `album_id` nudge param; the original catalog-wide matched-lyrics pool (~11.3k) is retired | worker #83 + hourly EventBridge ws #726; retarget 2026-07-29 |
| Store | shared_db **V49 applied to prod**, service pins bumped | (rollout → §6.9) |
| Korean bodies | `scripts/genius_translate_poller.py`, resident on launchd (60 s interval); batches by output size; one annotation per call | ws #732 (poller) + #734 (scheduled) + #736 (batching, 18.8 s → 3.4 s/annotation) + #737 (validation-retry loop fix) |
| Read | `annotations` field on `GET /api/lyrics/{spotify_track_id}`, anchored per request, attached above the availability early-return; **owner-only per O2** | backend #135 (read) + #139 (gate) |
| Render | `LyricsSheet.tsx` in-text layer per the render spec | front #317 (+ #316 contract sync, #319 403-as-state, #322 tear-off window fix) |

Translation queue is **steady-state** (prod, 2026-07-28): 2,416 `done`, backlog cleared; pending at
any instant is fresh hourly-fetch arrivals draining, plus any rows the claim SQL holds because the
parent song's `match_status ≠ 'matched'` (by design — a wrong song's commentary must not be paid for).

**The research-pipeline half landed 2026-07-29 (R1/R2/R4)**; statuses below re-verified against
code the same day. Remaining: R3, R5's description tier, R6.

| ID | Status (2026-07-28) | What | Size | Key files |
|---|---|---|---|---|
| **R0** | ✅ **done** — ws #712, 2026-07-26 | Coverage probe over the 88 bucketed albums: per-language match rate and per-field fill rate for the four fields the notes actually lack | S | new `tools/genius_probe.py`, cloning the resumable-batch skeleton of `tools/lyrics_batch_api.py:1-27` |
| **R1** | ✅ **done 2026-07-29, as DERIVE**; **evidence layer added 2026-07-30** — album-level facts are computed at prompt-build time from the track tables (`_render_genius_block` in `scripts/research_poller.py`): coverage counts, producer/writer cores, session-staff recurrences (corporate boilerplate filtered), per-track sample/interpolation relations both directions, confirmed-absence line. `album_genius_facts` + `genius_facts_poller.py` were **not** built — O3 re-resolved, §6.9. The first real e2e (§6.10) showed the aggregate alone is not citable: it now also ships a **매칭 근거** section (per matched track: Genius title, confidence, URL, `⚠︎ 곡명 불일치`), **names** the unmatched tracks instead of counting them, and attributes any credit on ≤3 tracks to those tracks | M | `scripts/research_poller.py` (`GENIUS_FACTS_SQL`, `_render_genius_block`) |
| **R2** | ✅ **done 2026-07-29** — `_genius_block` appended in `build_prompt` after the 앨범 block; the claim gate holds a fresh request until every album track has a `track_genius_songs` row (any status = attempted), with a 90-min partial fallback and an SQS `album_id` nudge to the worker (Records-loop routed + handler test; 5-min/album cooldown; hourly cron = fallback). Gate→nudge→attempted→claim→render executed on the Neon test branch, and hold/claim simulated on prod inside BEGIN..ROLLBACK | S | `scripts/research_poller.py` (`CLAIM_SQL` gate, `GENIUS_PENDING_SQL`, `_nudge_unready_albums`), worker `handler.py` Records branch |
| **R3** | ✅ **done 2026-08-03** — `GENIUS_SQL` (batched, LEFT JOIN, RESEARCH_SQL's owner scope) + `_genius_block` + `m['genius_md']` in `export_checked_memos`, emitted directly after the note. The renderer is **imported** from `research_poller`, not reimplemented — a third copy of that derivation logic is the twin-drift class. Source priority is now stated in both rule docs (`buckit-nightly.md` v0.6, run spec §3): for credits and relationships the block outranks the note, disagreement is followed *and* recorded, and `[확인: Genius]` may not be attached to a note-derived sentence. **The morning's deferral measurement was re-measured and reversed** — see §6.12 | Facts as a first-class **nightly-draft** context field | ~~M~~ **S–M** (renderer reused) | `scripts/buckit_nightly.py`; tests `scripts/tests/test_buckit_nightly_genius.py` |
| **R4** | ✅ **done 2026-07-29**, tightened 2026-07-30 — `[확인: Genius]` confirmed tier in the ★ honesty block (+ 샘플링/기반 1차-근거 rule + 출처-못-찾은-것 exclusion); block-side provenance = fetch-date range + per-track 근거 링크, and the zero-match/lookup-failure paths explicitly ban the tier. **The tier is per matched track, not per album**: a `⚠︎ 곡명 불일치` track is carved out of the cite-without-re-searching rule (§6.10). Vendored `album_research_v2.md` and canonical `docs/editorial/album-research-prompt.md` are identical **over the shared range** — the canonical file also carries a workspace-only validation log behind an explicit "do not paste" marker, so they were never byte-identical end to end (this row said so until 2026-07-30). Parity is now pinned by `scripts/tests/test_prompt_mirror.py` rather than by convention | S | `scripts/album_research_v2.md`, `docs/editorial/album-research-prompt.md` |
| **R5** | ❌ **DROPPED 2026-08-03, owner decision** (§6.13). Annotation bodies were always done (viewer pipeline above); the **song-description tier is the part that will not be built**. Final numbers: 1,086 songs, **860 carry a description, 526 clear 200 chars**, `description_ko` still **0-filled**, all 526 on tracks that already have a lyrics row (66 albums, avg 659 chars, 347k total). The sizing is what killed it — `description_ko` appears in *no code in any repo*, only in the schema (`models.py`, V49, the two mirrors), and the store has no `description_source_fingerprint` / `description_translation_status` columns, so matching the annotation path's staleness guard means V51 → prod apply → four service pins → poller → backend → `openapi.json` → `api.gen.ts` → sheet render. A "cheap prompt-side R5" was considered and **rejected on provenance grounds**, not cost: a 6-sample read found 3 of 6 descriptions are pure interpretation or encyclopedia digression with no marker separating them from the citable 3, and R4's whole design is that separation | ~~S~~ **M+, cross-repo** — not built | — |
| **R6** | ✅ **done 2026-08-03** — `export_bucket_context` now emits a 카탈로그 내부 연결 block: credit connectors (a name on ≥2 candidate albums spanning ≥2 *acts*) split into 창작 / 후반, plus catalog-internal lineage edges (a sample/interpolation/cover whose far side is a track we own), cross-act listed and same-act counted. Coverage is stated per the degradation rule, so an unfetched album never reads as "no connections". Four noise classes were found by running it against prod and are filtered, each for a stated reason (§6.11) | M | `scripts/editor_buckit.py` (`GENIUS_SQL`, `_credit_connectors`, `_lineage_edges`, `_genius_graph_section`); tests `scripts/tests/test_editor_buckit_genius.py` |

**R6 is the capability no external service can provide**, because it is a property of *this* catalog
rather than of any album: "three albums in this bucket share Noah Goldstein" is only computable here.

**Degradation is designed, not incidental.** Every R-step renders an explicit
`Genius 미매칭 (0/n 트랙) — 사실의 부재가 아니라 조회의 부재다` rather than silence, so a thin note is
visibly thin-because-unsourced instead of looking like a lazy draft. This matters most for Korean
albums (§6.2).

**Widest integration surface is the album view, not the lyrics sheet.** `AlbumDetailView.tsx` is
rendered by the public overlay (`AlbumOverlay.tsx:120`), the member modal (`member/AlbumDetail.tsx:96`)
and the public review page's tracklist, all reading `GET /api/music/albums/{id}`; and
`ANY /api/music/{proxy+}` (`infra/apigateway.tf:68-71`) means **no new API Gateway route and no
terraform apply**. One contract change reaches every screen an album appears on. The lyrics sheet by
comparison is owner-only and reachable for just 1,921 renderable tracks.

### 6.6 The lyrics-viewer sub-thread (the original ask) — measured 2026-07-26, clears the bar

Anchoring feasibility was the open gate in the 2026-07-25 draft. It has since been **measured** by
`tools/genius_anchor.py` against ROSALÍA *LUX*, and the tiers below resolve in favour of the in-text
layer. What remains open is Korean *coverage*, not anchoring feasibility.

**The measurement.** 15 tracks, 13 carrying `lyric_synced`, 103 annotations on those 13:

| Status | Count | Share of lyric-bound |
|---|---|---|
| `unique` + `partial` — resolved to one span | 71 | **74.7%** |
| `repeated` — several occurrences (a chorus) | 19 | 20.0% |
| `unmatched` — genuinely absent from our text | 5 | 5.3% |
| `section` — `[Verso 1]` style markers, never lyric-bound | 8 | (excluded from the denominator) |

**Denominators, because these two numbers get quoted against each other as if they disagreed.** Every
percentage above is over **95 lyric-bound** annotations (103 minus the 8 section markers). Over all 103
the unmatched share is **4.9%** — the same 5 rows, a different denominator. Median per-track placed rate
is 75.0%.

**94.7% is the number that decides the UI; 74.7% is the number that describes the matcher.** `repeated`
is not a failure — those are chorus passages whose location *is* known, found in several places rather
than none. Rendering on the first occurrence and stating the repeat is the intended handling, so
71 + 19 = **90 of 95 (94.7%) are placeable**. Quoting 74.7% alone reads as a far weaker result than the
data supports; quoting 94.7% alone hides that a fifth of annotations need repeat handling. Quote both,
with their denominators.

**An annotation covers a range, not a line.** Median 2 lines, mean 2.3, one in six covers 4 or more,
longest 12. The phrase this section previously used — *inline per-line layer* — understates the shape
and points at the wrong UI: a per-line marker cannot express a 12-line span. Overlap, by contrast, is a
non-problem: 3 of 201 marked lines are claimed by two annotations and never by three, so no stacking
system is needed. Marker density is roughly 1 line in 3 (201 of 590 lines album-wide), ranging 9.5% to
64.7% per track — and the chosen visual direction's own author records that it is weakest at the dense
end (`docs/design/lyrics-annotations/README.md`).

**How it matches, and why nothing is stored.** Genius fragments are offsets into Genius's lyric text;
our segments come from `parse_lrc(lyric_synced)` via LRCLIB and are not byte-identical — LRC breaks
lines where the vocal breathes, Genius where the sentence ends. **1,565 of 1,686 renderable rows (92.8%)
carry `lyric_synced`**, and `normalize_lyrics` (`lyrics_service.py:176-184`) derives segments from the
synced text, **not** from `lyric_plain`, so anchoring targets synced segments. Line-to-line comparison
scores 33% — a matcher artifact, not a property of the data (§9; NOTES §1.6). The tool drops line
boundaries instead: concatenate every segment into one normalized string while remembering which
segment each character came from, find the fragment as a plain substring, then map the matched span
back to `(start_segment, end_segment)`.

Anchoring is a **pure function over the current lyric text, never stored**. Stored offsets would rot the
first time `lyrics_reassessment` re-matches a track against a different LRCLIB upload; recomputing costs
microseconds and self-heals. It also means the annotation store does not depend on lyrics existing at
all — a track with no lyrics yields an empty anchor list rather than an error, which is what lets the
annotation feature ship independently of the lyrics viewer.

**Tier decision — recorded, now closed.** ≥70% ⇒ in-text layer; 40–70% ⇒ hybrid with an unanchored
drawer; <40% ⇒ song-level panel only. At 94.7% located and 74.7% unambiguous, **the in-text layer is the
decision**, with the drawer retained for the unmatched remainder rather than as the primary surface.

**Korean — the regression ran 2026-08-03, and this paragraph's prediction was half wrong.** What it
used to say: *LUX* is one non-Korean album; §6.2 measured 0/8 Korean tracks with ≥3 annotated lines,
so the Korean risk is "almost certainly *coverage* … rather than the anchoring rate", and a six-album
KR/EN regression was scheduled for **2026-07-29**. **That regression never ran** — the scheduled-task
directory it named (`~/.claude/scheduled-tasks/genius-anchor-multi-album-test/`) does not exist. It was
run on 2026-08-03 during the closing pass, against the V49 store rather than a live collection (the
tool predates the store, so its `--genius-json` input was generated from `track_genius_annotations`).

Reported as two separate numbers, exactly as this paragraph demanded — because they disagree with
each other's implication:

| | matched songs | with ≥1 annotation | annotations | per annotated song |
|---|---|---|---|---|
| EN | 631 | 553 (87.6%) | 6,747 | 12.2 |
| KO | 202 | **62 (30.7%)** | **140** | **2.3** |

| Album (3 KR + 3 EN) | placed (unique+partial) | located at all |
|---|---|---|
| KO *24:26* | 33.3% | 41.7% |
| KO *킁* | 27.3% | 63.6% |
| KO *NOWITZKI* | 14.3% | 28.6% |
| EN *ICEMAN* | 78.1% | 93.2% |
| EN *Swimming* | 74.3% | 86.6% |
| EN *Blonde* | 76.4% | 82.5% |

**The English control reproduces *LUX*'s 74.7%**, so the Korean numbers are the catalog's, not the
harness's — that control is the reason to trust the rest of the table. Coverage is thin as predicted
(2.3 annotations per annotated Korean song against 12.2), **but anchoring is also poor**, which this
paragraph said it almost certainly would not be. Against the tier rule recorded just above, all three
Korean albums fall in the **<40% ⇒ song-level panel only** band while English sits in the ≥70% in-text
band.

**Left unfixed, deliberately.** The in-text layer only engages where a track has both annotations and
synced lyrics: **32 Korean songs / 86 annotations** catalog-wide, against 496 songs / 6,227 annotations
in English — Korean is 1.4% of the exposed volume. A Korean-specific tier branch is not worth building
for that, and the unmatched drawer is the designed fallback, so a Korean sheet reads thin rather than
broken. Revisit if the Korean catalog grows; the harness to re-measure is in §10.

**Where it renders.** `myblog_front/src/components/member/lyrics/LyricsSheet.tsx` — the static reader,
**not** `LyricsViewer.tsx`. The sheet renders each line as a `<p>` and already keys on the server segment
index (`s.i`) that anchors are expressed in; the viewer wraps every line in a `<button>`, so an
interactive marker inside a line would be invalid nested content, and it caches per-line pixel offsets
that an async annotation load would silently invalidate. Full reasoning and the chosen visual direction:
`docs/design/lyrics-annotations/README.md`.

**The render spec is decided** (2026-07-27) and lives in that same file under *The render spec*. It is
the contract the implementation is built against, and it fixes more than the visual direction: the long
span rule (A2, ends-only at 4+ segments), the overlap rule (B2, shorter span owns the line, with a
required containment fallback), repeat/unmatched/disputed handling, ordering, note placement and the
dark-theme ink rule. **One axis is a setting and only one** — the highlight treatment (`M0`–`M3`,
default `M0`, persisted as `lys:anno-style`) — because marker density runs 9.5% to 64.7% per track and
no fixed treatment is correct across that range. The other axes each have one answer the measurements
point at, so they are not exposed.

**Reproducing.** `python3 tools/genius_anchor.py --self-test` needs no DB and no network (PASS as of
2026-07-26). The album measurement needs both a prod `DATABASE_URL` (SSM `/myblog/backend`, read-only)
and a collected Genius payload:

```bash
python3 tools/genius_anchor.py --album-id <album-uuid> --genius-json <payload.json>
```

The *LUX* payload lived in the 2026-07-25 session scratchpad and **was not preserved**; re-collecting it
is 45 API calls and ~25 seconds (§6.3). The table above is carried from that run. R0's `tools/genius_probe.py`
should write its payload somewhere durable so the next re-measure does not start by re-fetching.

Placement warning: `get_normalized` early-returns (`if out.availability != "ok"`) before
`attach_translation`. Anything attached there is invisible for `not_found` tracks, so the metadata block
must attach **above** that return. **Honoured in the shipped read path** — backend #135 attaches
annotations above the early return (`lyrics_service.py`, `attach_annotations`), so no-lyrics tracks
still carry their annotations.

The store this section's anchors run against: **§6.9**.

### 6.7 Token

Issued 2026-07-25. Client access token only — Client ID/Secret are unused for reads.
**Placed: `GENIUS_ACCESS_TOKEN` is in SSM `/myblog/worker` (verified 2026-07-28) and the worker
`genius_fetch` job reads it** — an unset key degrades to a logged no-op, not an error. It is on
CLAUDE.md's never-log list.

### 6.8 Licensing / terms

**Owner ruled this out of scope on 2026-07-25 — do not re-raise it and do not let it shape the
design.** This is personal, non-commercial research and the owner has accepted the position. Any
future session that rediscovers terms-of-service material should record nothing and move on; treat
storage and LLM use of Genius content as permitted for this project.

### 6.9 Storage — two track-scoped tables, one read route (shared_db V49)

Design settled 2026-07-26. This is the schema the viewer sub-thread (§6.6) builds on. It lives here
rather than in a migration file because the migration is R-step work: write `V49`, get it applied to
prod by a human (rule 3), then bump the service pins — in that order, never all in one PR.

**Shape in one line.** Two tables keyed on `track_id`, mirroring the existing `track_lyrics` /
`track_lyrics_translations` pair; the Korean translation is a **column on the annotation row**, not a
third table; and reading is a **field addition to the existing `GET /api/lyrics/{spotify_track_id}`**,
not a new route.

**Why track-scoped and not album-scoped.** Genius has no album-level object at all — 15 song records,
no album "about", no label field (NOTES §2). Album-level facts are a *derivative* of the track rows,
never a source. This is also why the store must not be folded into R1's `album_genius_facts`: that
store is a materialised per-album view for the research prompt, and it should be computed from these
tables rather than fetched separately. (Open question O3 below.)

#### `track_genius_songs` — one row per track

| Column | Type | Why it exists |
|---|---|---|
| `track_id` | UUID PK → `tracks.id` CASCADE | Same key shape as `track_lyrics`; a deleted track takes its Genius rows with it |
| `genius_song_id` | BIGINT NOT NULL | Genius's own id; the re-fetch key |
| `genius_url` | TEXT | Provenance link rendered in the UI; the design record's convention is to *point at* Genius rather than copy lyric text |
| `match_status` | TEXT NOT NULL | `matched` \| `ambiguous` \| `not_found`. Mirrors `track_lyrics.match_status` |
| `match_confidence` | REAL | **Required by §6.2**: 로꼬's *2025* matched to a different artist's song. Without a per-row confidence, wrong credits enter a research note silently |
| `genius_title`, `genius_artist` | TEXT | What Genius *thinks* this track is, so a bad match is visible in a query without an API call |
| `description`, `description_ko` | TEXT | The song description (13/15 on *LUX*, 157–1,956 chars). Korean is the body a reader sees, per the owner decision; the original stays as the collapsible secondary |
| `annotation_count` | INT | Genius's own count. Stored so drift against the annotation rows is detectable — it is expected to exceed them **by exactly one per described track**, because Genius counts the description as an annotation (NOTES §2) |
| `credits` | JSONB | writers / producers / performances. The language-independent channel (7/8 in both KR and EN, §6.2) and the one that answers 75/78 of the research pipeline's recorded failures (§6.4) |
| `relationships` | JSONB | interpolations / samples / derivatives. **Filter out `translations`** on write — every one is a Genius community translation page, not a musical relationship (NOTES §2) |
| `language` | TEXT | Genius's tag. Stored but **not trusted** — one tag per song, and *LUX* has ≥11 languages across 15 tracks (§6.3) |
| `fetched_at`, `fetcher_version` | TIMESTAMPTZ, TEXT | Re-fetch bookkeeping, matching `track_lyrics.matcher_version` |
| `created_at`, `updated_at` | TIMESTAMPTZ NOT NULL DEFAULT now() | House convention |

#### `track_genius_annotations` — one row per annotation

The four load-bearing columns are marked ★.

| Column | Type | Why it exists |
|---|---|---|
| ★ `genius_annotation_id` | BIGINT **PK** | The natural key. Globally unique on Genius, so re-fetch is a plain `ON CONFLICT (genius_annotation_id) DO UPDATE` with no synthetic id and no delete-then-insert window. Bulk upserts **sort by this key** (house rule: row-lock deadlock avoidance) |
| `track_id` | UUID NOT NULL → `tracks.id` CASCADE, indexed | Read path is always "all annotations for one track" |
| ★ `fragment` | TEXT NOT NULL | The referent text — **the anchor *input*, never the anchor *result***. §6.6 forbids storing resolved `(start_segment, end_segment)` offsets; storing the fragment is what makes re-anchoring a pure function possible at all |
| ★ `referent_ordinal` | INT NOT NULL | Document order of the referent within the Genius song. Two jobs: deterministic ordering for annotations that anchoring cannot place, and a stable tiebreak when two anchors resolve to the same start segment |
| ★ `body_ko` | TEXT | The Korean body. Owner decision: the body a reader sees is always Korean |
| `body_source`, `body_source_lang` | TEXT | Original-language body, kept as the collapsible secondary. Also the input the Korean body is derived from |
| `body_source_fingerprint` | TEXT | Hash of `body_source` at translation time. **Staleness is computed at read time, never stored** — exactly the `track_lyrics_translations.source_fingerprint` pattern (`lyrics_service.py:67-90`): a changed Genius body reads as `stale` with `body_ko` withheld rather than showing a translation of text that no longer exists |
| `translation_status` | TEXT NOT NULL | `pending` \| `done` \| `failed`. The translation lifecycle lives **here**, not in a second table — a translation is a property of an annotation, and `track_lyrics_translations` is a separate table only because a lyric translation spans a whole track |
| `translated_at`, `translator_model`, `translator_version` | TIMESTAMPTZ, TEXT, TEXT | Same provenance columns `track_lyrics_translations` already carries |
| `votes_total` | INT | Drives the **disputed** treatment only — the chosen design strips the highlight from negative-vote annotations. Range on *LUX* is −17..+63, median 9. **Never an ORDER BY**: sorting by votes surfaces translations, which are an explicit non-goal (§2) |
| `is_verified`, `state` | BOOLEAN, TEXT | 0 of 115 *LUX* annotations were verified; the column records that rather than implying it |
| `fetched_at` | TIMESTAMPTZ | Re-fetch bookkeeping |
| `created_at`, `updated_at` | TIMESTAMPTZ NOT NULL DEFAULT now() | House convention |

Section-marker referents (`[Verso 1]`, 8 of 103 on *LUX*) **are stored**. They carry real bodies; the
read path classifies them via `anchor.status == "section"` and keeps them out of the in-text layer.

#### Reading — one route, additive fields

`GET /api/lyrics/{spotify_track_id}` already exists, is Cognito-gated at the API Gateway authorizer,
and is matched by the existing `/api/lyrics/*` authorizer entry — so **no new route and no
`terraform apply`**. `LyricsResponse` (`app/api/schemas.py:1048`) gains one optional field:

```
annotations: [ { id, ordinal, start_i, end_i, occurrences, status,
                 body_ko, translation_status, body_source_lang,
                 votes_total, disputed, genius_url } ]
```

- `start_i` / `end_i` are **segment indices in the same `s.i` coordinate the viewer already keys on**
  (`LyricsSegment.i`), computed per request by `tools/genius_anchor.py`'s span algorithm. Nothing
  positional is persisted.
- Ordering is **position in the lyrics** — `(start_i, referent_ordinal)`, with unanchored rows sorted
  by `referent_ordinal` alone and rendered in the drawer. Never by votes.
- `disputed` is derived (`votes_total < 0`), not stored.
- **Attach above the `availability != "ok"` early return** (`lyrics_service.py:229-233`). This is the
  §6.6 placement warning and it is load-bearing here: 2 of 15 *LUX* tracks carry 12 annotations and no
  synced lyrics, and the standalone (no-lyrics) mode is the whole reason the annotation store does not
  depend on `track_lyrics`.

#### Migration and rollout

**Done 2026-07-27.** `V49__track_genius_annotations.sql` is applied to prod, the service pins are
bumped (backend and worker both import the models), the contract is merged, and `api.gen.ts` was
regenerated (front #316). The rollout followed the planned order: migration written → **prod apply
(pre-merge, human-run)** → each service repo's `shared_db` git pin bumped → `openapi.json` regenerated
and merged in the workspace → frontend types regenerated (`pnpm generate:types`). The canonical
schema mirror pair — workspace `docs/contracts/schema.sql` ↔ shared_db `tests/canonical_schema.sql`,
whose byte-identity is convention-only and has silently drifted before — is **byte-identical with the
V49 tables present (verified 2026-07-28)**. (An earlier draft of this section named
`_generated_schema.sql` as the twin; that file is generated-from-models and was never the
byte-identity pair.)

#### Questions raised by this design — all three answered 2026-07-26

- **O1 — who writes the rows → the worker Lambda. Shipped** (worker #83 + hourly EventBridge
  ws #726; the token prerequisite is met — §6.7). §8's secondary list carried "worker Lambda vs
  local poller" unresolved; the owner chose the worker. A local poller dies with the Mac, and there is
  precedent — a 07-20 reboot stalled a queue for 3 days. One nuance the shipped state added: the
  **fetch** runs in Lambda, but the **Korean-body translation** runs as a resident local poller
  (`genius_translate_poller.py`, ws #732/#734) — it needs `claude -p` on the owner's subscription,
  which has no Lambda equivalent. Different answer, different reason; not an inconsistency.

- **O2 — the read route moves to owner-only.** `get_lyrics` currently depends on
  `require_cognito_token`, so **every logged-in member** can read the lyrics corpus, while
  `track_lyrics` is documented as owner-only research data (`models.py:315-318`). The owner chose to
  close that gap: `GET /api/lyrics/{spotify_track_id}` becomes `require_owner`, and the annotation
  fields inherit the tightened gate rather than widening it.

  **Shipped 2026-07-28 as its own pair of PRs, per the plan below**: backend #139 (route guard,
  fail-closed, + tests that can actually see the gate) and front #319 (the 403 rendered as a state,
  not an error). The original reasoning, kept for the record: this is a regression for existing
  members — the lyrics sheet has been live since FEAT-lyrics-sheet (2026-07-08) and is reachable from
  the `/members/` 개요 tab, so a non-owner member reading lyrics gets a 403 after this change. That is
  why it needed its own small PR, never bundled into the annotation store.

- **O3 — `album_genius_facts` stays a separate store.** The owner chose to keep both: R1 fetches for
  the research prompt, these tables serve the viewer. That is the simpler build, and it is recorded
  here with its known cost — **the same Genius fact can be stored twice and disagree**, because the
  two stores are fetched at different times from a source that changes. Two consequences to design
  around rather than discover: the two stores must never be joined and presented as one number, and
  when a research note and the viewer disagree about a credit, **`fetched_at` is the tiebreak** —
  which is why both tables carry it. If drift becomes visible in practice, collapsing R1 onto these
  tables remains available and this decision is the thing to revisit.

  **Re-resolved 2026-07-29 — R1 built as DERIVE, no second store.** By the time R1 was built, the
  implemented state had answered the question this decision left open: the track-scoped store was
  already accumulating exactly the credits/relationships R1 needs, and the drift cost this entry
  itself names ("stored twice and disagree") had no remaining upside to buy. Album-level facts are
  now computed at prompt-build time from `track_genius_songs` (`_render_genius_block` in
  `scripts/research_poller.py`); there is one store, `fetched_at` still rides every derived block as
  its provenance date range, and the viewer and the research prompt can no longer disagree by
  construction.

### 6.10 First real research request, e2e (2026-07-30) — the post-merge gate, and what it caught

The R1/R2/R4 merge left one gate open: a real owner-issued research request, end to end in prod.
Ran it on **ONYX / 사이먼 도미닉** — the only bucketed album with no research row and no Genius rows,
so the readiness gate had to hold. Chain, from the owner's click:

| +t | Event | Evidence |
|---|---|---|
| 0 s | `POST /api/research/albums/{id}` → `queued` | `album_research` row |
| 3 s | poller fires: nudge sent, **claim held** | `nudged genius_fetch for 1 waiting album(s)` immediately followed by `queue empty` — a queued row that did not claim |
| 21 s | worker collection complete, 12/12 tracks | matched 9 · ambiguous 3 · not_found 0 |
| 107 s | next firing **claims** → `running` | `claimed … album=ONYX` |
| 597 s | `done`, 12,077 chars | 489.9 s model run; `[확인: Genius]` used 4× |

The gate, the nudge, the attempted-counts-as-ready rule and the tier all behaved as designed. The
90-minute partial fallback never engaged and the hourly cron never participated — exactly the
intended division of labour. **Two defects surfaced that only a real note could surface.**

**(1) A wrong-song match was presented as citable.** Track 2 `Simon Says` matched Genius's *왈
(Simon Says)* — a different 2018 single by the same artist — at confidence **0.7424**, status
`matched`, and its credits (slom / Pharoahe Monch / Simon Dominic) entered the block under the
`[확인: Genius]` tier. The note caught it on its own, cross-checking 벅스 and a lyrics page to show
the 2026 track carries no feature credit, and filed it as 상충 · 미해결. That is the honesty layer
working, but it worked *despite* the block: the prompt told it to cite the tier without
re-searching, and nothing in the block hinted the row was worth doubting.

The one column that showed the collision — `genius_title`, added by V49 with the comment "so a bad
match is visible in a query without an API call" — **was never selected into `GENIUS_FACTS_SQL`.**
The evidence had been collected and stored for exactly this, and then not rendered.

**Raising `GENIUS_MIN_CONFIDENCE` (0.62) would not have helped, and would have cost.** The collision
scored 0.7424 with **0.91 title similarity** (`왈 (Simon Says)` contains `Simon Says` outright),
while four *correct* matches on the same album scored lower — 0.6526, 0.6535, 0.6651, 0.6758. Any
threshold that kills the false positive kills them first. The separation is not on the score axis,
so the fix is evidence, not arithmetic.

**(2) Nine matched tracks produced zero source links.** The block emitted 근거 링크 only for tracks
carrying a *relationship*; ONYX has none, so every one of its nine matched Genius URLs was dropped.
The note recorded the consequence twice — "미매칭 3트랙(어느 트랙인지 블록에 미기재)" — and could not
attribute the suspect credits to a track, which is precisely why (1) had to stay 미해결.

**Fix** (`scripts/research_poller.py`, workspace-only — no schema, no contract, no deploy):

- `GENIUS_FACTS_SQL` selects `genius_title` / `genius_artist`
- a **매칭 근거** section, before the credits that depend on it: per matched track, the Genius title,
  the confidence, the URL, and `⚠︎ 곡명 불일치` when the titles differ (trailing `(feat. …)` normalised
  away first — Genius drops feature credits from titles and flagging that would bury the real signal)
- unmatched tracks are **named** with their status, not counted
- a credit on ≤3 tracks names those tracks, so a suspect credit traces to a suspect row
- the flag's own line states it is not a verdict: 원제/로마자 병기 makes benign divergence common in a
  Korean catalogue (4 of 9 ONYX rows flag, one of them the true positive)
- the prompt's tier rule is now **per matched track**, carving the flagged track out of
  cite-without-re-searching (both prompt copies, §6.5 R4)

Rejected while fixing: `search_count` is not a defect — `run_claude` hardcodes 0 and documents why
(`LLMResult` does not surface `usage.server_tool_use`; the field was ruled unreliable 2026-06-11).
All nine historical rows read 0. The citations inside `result_md` remain the grounding evidence.

Not built, deliberately: Genius exposes a song's release date and album, which would catch this
collision class *decisively* rather than by flag. That is a V50 column plus a worker change plus a
cross-repo pin rollout — a step of its own, and the evidence layer above removes its urgency. Left
as a follow-up rather than folded into a bug fix.

### 6.11 R6 (2026-08-03) — the catalog graph, and the four noise classes a real run exposed

R6 is the one capability no external service can supply, so the question was never *whether* the
relations exist but whether enough of them resolve **inside this catalog** to be worth a section.
Measured on prod before writing any code: 89 of the 103 unwritten bucket albums carry Genius rows,
114 credit names sit on ≥2 of those albums, and 3,019 relationship strings resolve to **101
catalog-internal edges**. That cleared the bar; the rest of the work was separating signal from a
noise floor that only appeared once the block was rendered against real data.

**Four filters, each with its measurement.** None of them are taste calls — each one was a category
that outnumbered and displaced the thing the section exists to show.

1. **Same-act edges are counted, not listed** — 69 of the 101. A remix EP, a live album and a
   deluxe reissue all produce genuine `remixed_by` / `performed_live_as` edges, and at equal weight
   they buried the 31 cross-act ones (Frank Ocean → Stevie Wonder, Tyler → Kendrick, Tame Impala →
   Rihanna). They are summarised in one line rather than dropped silently.
2. **Albums sharing any credited artist merge into one act.** Without the merge, a remix EP credited
   `Honey Dijon, Madonna, Sabrina Carpenter` reads as a second act against Madonna's own album, and
   every Radiohead member becomes a "connector" across Radiohead's own discography. Of the 114 names
   on ≥2 albums, only **56 survive the merge**, and 7 span ≥3 acts.
3. **Places are not people.** `Mastered At` / `Mixed At` carry ~490 credits, and in the first
   rendered run **five of the top twelve connectors were studios** (Larrabee, MixStar, Sterling
   Sound, Bernie Grundman). `Video …` roles — director, editor, hair stylist — staff the video, not
   the record. Both categories are excluded, and the block says so.
4. **Post-production is ranked apart, not removed.** A handful of people master most of pop music:
   mixed into one list, Mike Bozzi (13 albums), Randy Merrill, Manny Marroquin and Șerban Ghenea
   pushed Pharrell, Carter Lang, Max Martin and Cirkut off the bottom. Two lists keep both facts —
   "these records share a finish" is a real observation, just not the same one as "these records
   share a writer". The RFC's own example (Noah Goldstein, an engineer) is why deletion was wrong.

**One guard on the lineage side.** The far end of an edge is confirmed by looking for the Genius
artist string inside our album's credited artists — a check that dissolves on a compilation.
`"072 Classical Music Discoveries"` credits 37 composers, so *any* composer name matches it, and it
produced both a false-feeling edge and a single 600-character line. Targets above 8 credited artists
are skipped, and `_album_label` bounds the artist list independently.

**A display defect worth recording, because it is the general shape.** Roles are truncated for
width. Sorted alphabetically, an engineer with one producer credit (Bryce Bordone) rendered as three
engineering roles in the *creative* list — the single credit that classified him was the one the
line hid. Creative roles now sort first, 작가/프로듀서 ahead of the rest: **a line must show the
evidence for its own classification**, the same principle §6.10 applied to `genius_title`.

Not built, deliberately: an "already reviewed" flag on the far end of an edge. `post_albums` holds
**1 row**, so the flag would be dead code today. Worth revisiting once reviews exist.

Verification: `python3 scripts/editor_buckit.py --dry-run` against prod (read-only, 4.7 s including
the 27k-track / 3.1k-album catalog index) plus 14 unit tests, including a parity test pinning
`editor_buckit._fold` byte-identical to its twin `research_poller._fold_title`.

### 6.12 R3 (2026-08-03) — the deferral that its own measurement reversed

R3 was deferred that same morning on a measurement, and shipped that same afternoon because the
measurement was re-taken. Both numbers were right; the first one answered the wrong question.

**What the morning measured.** Of the 89 (now 88, after the day's bucket churn) unwritten bucket
albums carrying Genius rows, **80 also carry a done research note**. Since `RESEARCH_SQL` embeds the
whole `result_md`, the inference was: the facts already reach the nightly prompt through the note,
so R3's margin is the 9 albums with no note at all.

**What the afternoon measured.** That overlap is between albums *holding both artifacts*. It says
nothing about whether the note **contains** the facts — and the note is prose a model wrote, not the
block. Splitting the 80 by when the note was written:

| | albums |
|---|---|
| note written **after** the R1 facts block shipped (2026-07-29) | **3** |
| note predates it — written when no Genius data existed | **77** |
| no note at all | 8 |

So for **85 of 88** the nightly prompt carried no Genius-derived fact of any kind. An independent
marker grep agrees and is blunter: across the 81 freshest notes on unwritten bucket albums, 7
mention Genius at all, **3** carry the `[확인: Genius]` tier, **1** has a 매칭 근거 section.

The general trap, since this pipeline invites it repeatedly: *a stage's input existing is not the
same as its output containing it.* Two artifacts co-existing on the same album is a join, not
evidence of transfer. What had to be measured was the note text, and the note text was reachable
all along.

**Cost re-measured too.** The R-table sized R3 as an M against a not-yet-written renderer. R1's
`_render_genius_block` has existed since 2026-07-29 — 167 lines encoding matched-rows-only, per-track
evidence with `genius_title` (the ONYX mis-match, §6.10), confirmed-absence vs could-not-check, and
per-role attribution maps. Reusing it makes R3 batch SQL + wiring + a source-priority rule.

**Two fact sources now, so they are ranked.** The nightly rules said flatly "the research note is
your fact source". Adding a second one silently would have left conflicts to resolve themselves
toward the prose. `buckit-nightly.md` v0.6 and run spec §3 now say: for credits and
sample/interpolation relations the block outranks the note, a disagreement is followed *and*
recorded, tracks marked 확인 불가 stay unclaimed in both directions, and `[확인: Genius]` marks only
what came from the block — never a sentence carried over from the note.

**Two things only running it showed** (the §6.11 lesson again — a harmless execution path is the
best review):

1. **Never-fetched albums were paying ~1.1k chars to say nothing.** With zero matched tracks the
   renderer lists every track as 미조회 and then states 0/n 미매칭 — the same fact twice. On LUX
   (18 tracks) that is 1,124 chars; 13 of the 101 unwritten bucket albums are in this state. The
   nightly collapses that case to a single tier-ban line (118 chars). The renderer is untouched —
   a research note's needs are not a draft's, and the per-track list earns its length only once
   *some* tracks matched.
2. **The 6,000-char cap is real on rich albums.** IGOR renders 9/12 matched and truncates inside the
   샘플·관계 list; coverage, evidence and the full 크레딧 section survive, so what is lost is the tail
   of the derivative-relations list. Left as is deliberately: the cap belongs to the shared renderer,
   and raising it here would change research prompts too.

**One import trap, worth stating because the failure is silent.** `research_poller` calls
`logging.basicConfig()` at module scope *without* `stream=`, and `basicConfig` no-ops once the root
logger has handlers. A module-level import in `buckit_nightly` would run first and move the nightly's
logs off stderr. The import is therefore lazy, inside `_genius_block`.

Verification: 71 unit tests pass (1 skipped — the pre-existing `TEST_DB_URL` Neon test, GHA-only),
plus the real context assembled against **prod** with three representative albums flipped to
`prep_tonight` inside a transaction that is always rolled back (the R2 simulate-on-prod pattern):
genius+note, genius-without-note, and no-genius-at-all all render as designed.

### 6.13 R5 dropped, and the regression that closed the document (2026-08-03)

The closing session was asked one question — build R5 or not — and answered it by sizing R5 honestly
for the first time. The answer changed the document's ending.

**What R5 actually is.** The R-table sized the description tier as **S, poller-only**: extend
`genius_translate_poller.py` to translate `description` into `description_ko`, done. A grep of
`description_ko` across all six repos on `origin/main` says otherwise — it exists in
`myblog_shared_db` (`models.py`, the V49 migration, `_generated_schema.sql`, `canonical_schema.sql`)
and in workspace documentation, **and in no executable code anywhere**. Neither prompt reads it
either: `research_poller.GENIUS_FACTS_SQL` and `buckit_nightly.GENIUS_SQL` both select credits and
relationships and never touch `description`. Translating it would have produced a column nothing
reads, so a user-visible R5 is poller + backend read field + `openapi.json` + `api.gen.ts` + sheet
render.

It is worse than that, because of a column asymmetry V49 left behind. `track_genius_annotations`
carries six columns that make the translation *safe* — `body_source_fingerprint`,
`translation_status`, `translated_at`, `translator_model`, `translator_version`, `body_source_lang` —
and `attach_annotations` uses the first two to withhold a Korean body whose source has changed since
translation (`compute_body_fingerprint`). `track_genius_songs` has `description` and `description_ko`
and nothing else. Holding descriptions to the standard already set for annotation bodies therefore
means a V51 migration, which per `reference-shared-db-cross-repo-rollout` means prod apply before
merge, four service pins, then contract, then front. Skipping the guard would ship a path that
silently serves a translation of text Genius has since rewritten — the exact failure the annotation
path was built to prevent.

**The store, finally measured** (prod, 2026-08-03): 1,086 songs, **860 with a description**, **526
over 200 characters**, **0 translated**, avg 659 chars, 347k characters total, across **66 albums**.
All 526 sit on tracks that already carry a `track_lyrics` row, so reach was never the objection.

**A cheaper R5 existed and was rejected on provenance, not cost.** Since neither prompt carries
`description`, the workspace-only variant — inject the English description into the nightly/research
prompt, no translation, no contract, no deploy, the same shape as R3 and R6 — looked attractive. Six
descriptions were read before proposing it. Three carry citable fact (*Cookie*: third single, debut
self-titled EP, the release backlash; *The Abyss*: preview date, first performance city; *Nikes*: the
magazine version's KOHH verse). Three do not: two are pure interpretation (*Glitter*, *Woods* — "Tyler's
confession of love", "the woods as the worst of it") and one is an encyclopedia digression about
decompression sickness (*The Bends*). **Nothing in the payload marks which is which.** R4 exists to
keep confirmed fact separable from reading; feeding this blend into the prompt would import another
writer's interpretation under the pipeline's own fact tier. Rejected.

**Owner decision: drop.** The viewer already renders line-anchored Korean annotation bodies on the
same sheet, which is the interpretive layer a whole-song summary would partly duplicate; the surface
is owner-only; and R0 sized the prose tier as "a bonus, not load-bearing" before any of this was
built. Nothing downstream depends on it. The schema columns stay — dropping them would cost a
migration to remove data no one is harmed by.

**The last scheduled item, run at last.** Closing the document required checking that nothing was
outstanding, which surfaced two items. The `isrc_backfill` EventBridge rule that §8 recorded as
awaiting a human `terraform apply` **is live** — `worker-isrc-backfill`, `ENABLED`,
`cron(0 21 ? * SUN *)`. The six-album KR/EN anchor regression scheduled for 2026-07-29 **had never
run**; its scheduled-task directory does not exist. It was run during this pass and its result is in
§6.6. It contradicts this document's assumption that Korean's risk was coverage alone: coverage is
thin (62 of 202 matched Korean songs carry any annotation, 2.3 per annotated song against English's
12.2) **and** anchoring is poor (placed 14.3% / 27.3% / 33.3% against an English control of 78.1% /
74.3% / 76.4% that reproduces *LUX*'s 74.7%). All three Korean albums land under this RFC's own <40%
tier line. Left unfixed by the same decision that dropped R5 — the in-text layer touches 32 Korean
songs and 86 annotations catalog-wide, 1.4% of exposed volume, and degrades to the unmatched drawer
rather than breaking.

**Method note for whoever re-runs it.** `tools/genius_anchor.py` predates V49: its `--album-id` path
loads lyric segments from the DB but still expects annotations via `--genius-json`, a payload shaped
for the live-API collection that no longer happens. Its module docstring advertises `--album-id`
alone, which errors. §10 carries the bridge query.

---

## 7. Decisions log

| Date | Decision | Thread |
|------|----------|--------|
| 2026-07-25 | Owner goal is **annotations/"이야기", not translation** | 1 |
| 2026-07-25 | Genius = annotations only (API-legal); **never a lyrics-text source** | both |
| 2026-07-25 | Thread 2 scope = **expedite + pool hygiene**, both | 2 |
| 2026-07-25 | Also **block classical at new-catalog ingest**, and apply the same to the release calendar | 2 |
| 2026-07-25 | MFF's 8 tracks get filled **by the feature**, not by a manual prod write | 2 |
| 2026-07-25 | **No owner-whitelist dependency** — the site will have real users; rules must key on content properties only | all |
| 2026-07-25 | **A correct classical tag is not grounds for exclusion** (LUX). Genre may only ever be one condition among several | all |
| 2026-07-25 | Korean-language lyrics coverage is a **problem to solve**, not just a caveat | both |
| 2026-07-26 | **Korean tracks are out of scope** for the annotation viewer — not annotating them may simply be the efficient answer | 1 |
| 2026-07-26 | **Show every annotation**, ordered by position in the lyrics. No editorial selection, no relevance score, **no vote sorting** | 1 |
| 2026-07-26 | The body a reader sees is **always Korean**; the original language is secondary and collapsible | 1 |
| 2026-07-26 | Host is the static reader **`LyricsSheet.tsx`**, not `LyricsViewer.tsx` (§6.6) | 1 |
| 2026-07-26 | Visual direction: the **Genius house style** (`docs/design/lyrics-annotations/README.md`) | 1 |
| 2026-07-26 | Storage: **two track-scoped tables**, translation as a column on the annotation row, one existing read route (§6.9) | 1 |
| 2026-07-26 | Public-cache concerns for the music service are **deferred** — "지금은 걱정하지 말자" | 1 |
| 2026-07-26 | **Worker Lambda writes the Genius rows**, not a local poller — a local poller dies with the Mac (§6.9 O1) | 1 |
| 2026-07-26 | `GET /api/lyrics/{id}` tightens to **`require_owner`**. Ships as its own PR — it 403s members who can read lyrics today (§6.9 O2) | 1 |
| 2026-07-26 | `album_genius_facts` **stays a separate store**; `fetched_at` is the tiebreak when it disagrees with the track tables (§6.9 O3) | 1 |
| 2026-07-27 | **Render spec fixed** — long spans A2 (ends-only at 4+), overlap B2 (shorter span owns the line) + containment fallback, note tracks its range, dark theme inverts ink only where the fill lands → design record | 1 |
| 2026-07-27 | **Highlight treatment is the only setting** (`M0`–`M3`, default `M0`). Density runs 9.5–64.7% per track, so a fixed treatment is wrong on one end or the other; the other axes are not exposed | 1 |
| 2026-07-29 | **Research requests are the Genius collection trigger.** Eligibility = `album_research` demand, per album, lyrics-blind (credits/relationships are useful without lyrics); the catalog-wide matched-lyrics pool (~11.3k) is retired | 1 |
| 2026-07-29 | **Research waits for collection readiness**: claim gate holds until every album track has a row (matched/ambiguous/not_found all count as attempted — permanent failures never block), SQS `album_id` nudge for immediacy, 90-min partial fallback, hourly cron as backstop | 1 |
| 2026-07-29 | **O3 re-resolved: R1 derives at prompt time from the track tables** — no `album_genius_facts`, no second fetch, no cross-store drift; facts from `matched` rows only (the translate poller's wrong-song hold, applied to notes) | 1 |
| 2026-07-29 | **Tradeoff recorded with the retarget**: a bucketed-but-never-researched album no longer accumulates viewer annotations (the sheet reads stored rows only). Demand flows exclusively through research requests; widening eligibility to bucket membership (`OR review_bucket_items`) is available but needs an explicit owner call | 1 |
| 2026-07-30 | **`matched` ships its evidence, and the confidence threshold stays put.** The block renders each matched track's Genius title, confidence and URL, names the unmatched tracks, and attributes few-track credits to their source track. A threshold raise was considered and rejected: the ONYX collision scored 0.7424 with 0.91 title similarity, above four *correct* matches on the same album — the separation is not on the score axis (§6.10) | 1 |
| 2026-08-03 | **R6 ships as two lists and one counted remainder.** Same-act lineage edges (69 of 101) are summarised not listed; places and video crew are not connectors; post-production names rank in their own list rather than being deleted or mixed in. Every filter is a measured displacement, not a taste call (§6.11) | 1 |
| 2026-08-03 | **A rendered line must carry the evidence for its own classification** — creative roles sort first so the one credit that put a name in the creative list is the one shown. Same principle as §6.10's `genius_title` | 1 |
| 2026-08-03 | **Two fact sources in the nightly prompt, explicitly ranked.** For credits and sample/interpolation relations the Genius block outranks the research note, a disagreement is followed *and* recorded, and `[확인: Genius]` marks only what came from the block. Adding a second fact source without a stated priority would have let conflicts resolve toward whichever prose the model read first (§6.12) | 1 |
| 2026-08-03 | **A deferral built on an overlap count was reversed by measuring the text.** 80 of 88 albums holding both a Genius row and a note looked like coverage; only 3 of those notes were written after the facts block existed. Co-existence of two artifacts is a join, not evidence that one carries the other (§6.12) | 1 |
| 2026-08-03 | **R5 dropped (owner).** `description_ko` is read by no code in any repo, and the store lacks the fingerprint/status columns that make the annotation path's translations safe — so the tier the R-table called an S is a migration-led cross-repo rollout, bought for an owner-only prose layer that R0 called a bonus. The columns stay; removing them would cost a migration of its own (§6.13) | 1 |
| 2026-08-03 | **The cheap version of R5 was rejected on provenance, not on cost.** Injecting raw Genius descriptions into the prompt needed no contract and no deploy, but 3 of 6 sampled descriptions are interpretation or digression with nothing marking them apart from the citable 3 — and separating fact from reading is what R4 is for (§6.13) | 1 |
| 2026-08-03 | **Korean's anchoring gap is recorded and left unfixed.** The regression this document scheduled for 07-29 and never ran was run at close: Korean anchors at 14–33% placed against an English control at 74–78%, below this RFC's own <40% tier line, so the assumption that Korean's only risk was coverage was half wrong. Not fixed — 32 songs / 86 annotations catalog-wide, and the drawer is the designed fallback (§6.6) | 1 |
| 2026-07-30 | **A `⚠︎ 곡명 불일치` flag is a prompt to verify, never a verdict.** Korean catalogues carry 원제/로마자 병기 routinely, so the literal-difference test flags benign rows too; the block says so, and the prompt carves the flagged track out of the "cite without re-searching" rule instead of demoting it (§6.10) | 1 |

## 8. What blocks execution

1. ~~**RFC promotion `draft → accepted`**~~ — **done 2026-07-26**, explicit owner approval. Thread 1
   is cleared to build.
2. ~~**Filter shape — still open, and it blocks Thread 2 only.**~~ — **resolved 2026-07-28**: the
   filter shipped as **E ∪ F composed** through `DATA-catalog-noise-and-lyrics-coverage` Step 3
   (worker #84 + bind-param fix #85), with the album expedite (§5 Step A) following as its Step 4
   (worker #86, prod-smoked on MFF — 8/8 `not_found` → `matched`). Thread 2's execution lives in
   that RFC from here on; this RFC keeps the measurements (§3–§5) as their evidence base. The
   original record, for context: E (genre + title form + vocal guard, 0 FP) vs F (empirical label
   yield, 2 FP, no genre dependency) vs both composed.

Secondary, non-blocking: split Thread 2 into its own `plan.md` row (the RFC's own OQ5).

Resolved since this section was written: the two matcher defects (§3.6) were **fixed 2026-07-26**
(worker #80/#81 + workspace #698). The `isrc_backfill` EventBridge rule that this line recorded as
awaiting a human `terraform apply` **is live** — verified 2026-08-03 against AWS:
`worker-isrc-backfill`, `ENABLED`, `cron(0 21 ? * SUN *)`. **Thread 1's viewer sub-thread has since shipped end-to-end** (2026-07-27/28 —
fetch, store, translation, owner-only read, render; PR map → §6.5 "Shipped state"), so nothing blocks
Thread 1 execution anymore; what remains of Thread 1 is the research-pipeline half of §6.5
(R1–R4, R6, and R5's description remainder).

## 9. Superseded — do not re-derive

The morning capture's *Session findings* appendix and these specific claims are wrong or stale:

- "MFF: 1 of 8 available on LRCLIB, the other 7 genuinely empty" → **8/8 available**
- "pool ~12.5k, cycles in 2–3 months" → **16,808 selectable, 96-day reachable cycle, diverging**
- "drain ≈ 145/day" → 146/day is the *re-check* rate; **drain is 2.25/day**
- "yield ~3.2/day, ~2.2%" → **2.25/day, 1.54%** (the 70-row count was contaminated by the 07-03
  best-of backfill and an 07-04 matcher-version deploy)
- "the pool is mostly instrumental works" → the rows say *LRCLIB has no record*; the real instrumental
  verdict is a different status with 882 rows
- "owner taste skews classical/K-pop ⇒ weak Genius coverage" → classical **refuted**; the real risk is
  **Korean-language (47.4% of engaged tracks)**
- "recency is not the signal" → **inverted**; recency is a 32x signal once classical is controlled for
- the resume instruction "do not re-query to trust the appendix" → **actively wrong**, it was stale
  within one day

## 10. Reproducing the numbers

Prod DB (read-only):

```bash
aws ssm get-parameter --name /myblog/backend --with-decryption --query 'Parameter.Value' --output text \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['DATABASE_URL'].replace('postgresql+psycopg','postgresql'))"
```

Schema gotchas that cost time: `tracks.track_no` (not `track_number`); `genres.slug`/`genres.label`
(no `name`); `album_genres.source ∈ mapping|itunes|llm` with `confidence ∈ high|low`.

Drain vs re-check rate — the distinction the morning session got wrong:

```sql
SELECT updated_at::date AS day,
       count(*) AS rechecked,
       count(*) FILTER (WHERE match_status IN ('matched','no_lyrics')) AS actually_drained
FROM track_lyrics
WHERE updated_at > created_at + INTERVAL '1 hour'
GROUP BY 1 ORDER BY 1 DESC;
```

Empirical label yield (rule F):

```sql
WITH label_stats AS (
  SELECT al.label, count(*) AS attempts,
         count(*) FILTER (WHERE tl.match_status='matched') AS hits
  FROM track_lyrics tl JOIN tracks t ON t.id=tl.track_id JOIN albums al ON al.id=t.album_id
  WHERE al.label IS NOT NULL GROUP BY 1
)
SELECT * FROM label_stats WHERE attempts >= 50 AND hits::float/attempts < 0.02 ORDER BY attempts DESC;
```

KR/EN anchor regression (§6.6). `tools/genius_anchor.py` predates V49 and still reads its annotations
from `--genius-json`, so bridge the store into the payload it expects — one file per album, then feed
both to the tool. Its docstring's `--album-id`-alone form errors:

```sql
-- → [{"no": track_no, "title": ..., "annotations": [{"fragment": ...}, ...]}, ...]
SELECT t.track_no, t.title, a.fragment
  FROM tracks t
  JOIN track_genius_songs g ON g.track_id = t.id
  JOIN track_genius_annotations a ON a.track_id = t.id
 WHERE t.album_id = :album_id
 ORDER BY t.track_no, a.referent_ordinal;
```

```bash
python3 tools/genius_anchor.py --album-id <uuid> --genius-json <bridged.json>
```

Run at least one English album as a control in the same pass — a harness defect and a genuinely
unanchorable catalogue look identical without one. English should land near *LUX*'s 74.7% placed.

Coverage vs anchoring must be reported separately (§6.6):

```sql
SELECT g.language, count(*) AS matched,
       count(*) FILTER (WHERE g.annotation_count > 0) AS with_anno,
       sum(g.annotation_count) AS annos
FROM track_genius_songs g WHERE g.match_status='matched' GROUP BY 1 ORDER BY 2 DESC;
```

Standing holdout audit (run monthly once Step B ships):

```sql
SELECT (evidence ? 'excluded_by') AS excluded,
       count(*) AS rows,
       count(*) FILTER (WHERE match_status IN ('matched','no_lyrics')) AS promoted,
       round(100.0*count(*) FILTER (WHERE match_status IN ('matched','no_lyrics'))/count(*), 2) AS pct
FROM track_lyrics
WHERE evidence ? 'excluded_by' OR evidence ? 'holdout'
GROUP BY 1;
-- holdout promotion rate materially above the 1.54% baseline (45/2,925 over 20 days) ⇒ rule is wrong
```

## 11. Closed — what this document is for now

**There is no next session on this RFC.** It closed 2026-08-03 with R0–R4 and R6 shipped and R5
dropped (§6.13). It is kept as the evidence base, not as a work queue. What to take from it:

1. **Thread 2 is not here.** It executes under `DATA-catalog-noise-and-lyrics-coverage` — its Steps
   3–4 are this RFC's §5 Step B / Step A and shipped 2026-07-28 (worker #84/#85/#86). §3's
   measurements remain that RFC's evidence base; **do not re-derive them**, and §9 lists what was
   already superseded (the lesson of §9 is that LRCLIB coverage moves within a day).
2. **Before touching the shipped Genius pipeline**, read §6.10 (the first real request, and the two
   block defects it caught) and §6.12 (the nightly facts block, and the source-priority rule that
   governs conflicts between the block and a research note).
3. **The one follow-up this RFC deliberately did not build**: Genius release-date/album corroboration
   as a V50 column — the decisive fix for the same-artist same-title collision class of §6.10. It is
   unclaimed and unrowed; give it its own plan row if it ever matters.
4. **Two numbers here have measured expiry dates.** The anchoring tier was decided on *LUX* and holds
   for English (§6.6 control, 74–78% placed) but **not for Korean** (14–33%, below the RFC's own <40%
   line) — the Korean gap is recorded and knowingly unfixed at 32 songs / 86 annotations. If the
   Korean catalogue grows materially, re-run the regression with §10's harness before assuming the
   in-text layer is still the right tier for it.
5. **Do not re-open R5 without re-reading §6.13 first.** Two of its arguments were sizing (which
   would change if the schema or the read path changed) but the third was not: raw Genius
   descriptions blend fact and interpretation with no marker, and that is a property of the source.
