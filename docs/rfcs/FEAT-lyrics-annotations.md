# FEAT-lyrics-annotations: lyrics coverage + "the story behind the lyrics"

- **Status**: draft (**not yet accepted**; promotion is owner-only per hard rule 5)
- **Owner**: 박지훈
- **Created**: 2026-07-25
- **Last investigated**: 2026-07-25 (deep investigation session — supersedes the morning capture)
- **Plan row**: `plan.md` → FEAT-lyrics-annotations (Backlog)

> **How to read this document.** The 2026-07-25 morning session wrote a capture from a brainstorm.
> A second session the same day re-derived every number from prod, live LRCLIB, and source, and
> **most of the original numbers were wrong** — some by 2.5x, one inverted outright. Everything below
> is the corrected state. §9 lists what was superseded so nobody re-derives it. Every number here is
> reproducible; §10 carries the SQL.
>
> **Nothing here is committed to build.** Two owner decisions block execution (§8).

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

Both are pre-existing, independent of this RFC, and worth their own `plan.md` rows.

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

## 6. Thread 1 plan (blocked on an owner-created token)

### 6.1 Verified API surface (from the official client source; `docs.genius.com` is unreachable from
this environment)

Base `https://api.genius.com/`, header `Authorization: Bearer <token>`. A **client access token is
sufficient** for reads; OAuth is only for scoped endpoints. `GET /account` needs scope `me` and 401s
even with a valid token — **do not use it as a preflight**; use `GET /songs/<known-id>`.

| Endpoint | Gives |
|---|---|
| `GET /search?q=&per_page(max 5)` | `hits[].result` incl. `id`, `title`, `primary_artist`, **`annotation_count`**, `stats.pageviews` |
| `GET /songs/{id}?text_format=plain\|html\|markdown\|dom` | **`description`** ("About" prose), **`song_relationships`** (samples/interpolations/covers/remixes), `producer_artists`, `writer_artists`, `custom_performances`, `media`, `album` |
| `GET /referents?song_id=&per_page(max 50)&page` | `referents[]` with `fragment`, `range`, `classification`, `annotations[]` (`body`, `verified`, `votes_total`) |
| `GET /artists/{id}`, `/artists/{id}/songs`, `/annotations/{id}`, `/web_pages/lookup` | metadata |

No official album endpoint. `/search` and `/referents` both 401 without a token (probed live). No
`GENIUS_*` key exists in `/myblog/backend`, `/myblog/music`, or `/myblog/worker`.

### 6.2 The channels the morning capture missed

**Three of the four content channels need no lyric anchoring at all** — this is the key finding:

- `/songs/{id}.description` — the "About" prose. This *is* 가사 이야기 at song level, one call, no
  matching into our lyric text.
- `song_relationships` — samples / interpolations / covers / remixes. Highest value-per-effort for a
  music blog, factual rather than interpretive, and **language-independent**, so it survives a poor
  Korean coverage result.
- `writer_artists` / `producer_artists` — credits Spotify does not provide.
- Only `/referents` needs anchoring.

### 6.2b Capability catalog — what could actually be built, ranked

Each row is scored on what it gives the owner, what it costs to integrate, and — the column that
decides everything — **how it degrades when Genius has nothing for a track.** Ranked by value/effort.

| # | Feature | Source field | Anchoring? | Language risk | Effort | Degrades to |
|---|---|---|---|---|---|---|
| **1** | **샘플/인터폴레이션 계보** — "this song samples X, is covered by Y" | `song_relationships` | none | **none** (structural data) | S | empty section, no visual hole |
| **2** | **곡 해설 패널** — the "About" prose under the lyrics | `description` | none | high | S | hide the panel |
| **3** | **크레딧** — writers, producers, featured performers | `writer_artists`, `producer_artists`, `custom_performances` | none | low | S | fall back to Spotify credits |
| **4** | **커버리지 배지** — "Genius has 42 annotations" + deep link | `annotation_count` from `/search` | none | none | **XS** | no badge |
| **5** | **줄별 주석 오버레이** — the original ask | `/referents` | **required** | **high** | **L** | — (this is the one that can fail outright) |

**Feature 1 is the sleeper and should probably lead.** It is the only channel that is *language-
independent* — a sample/interpolation edge is structural metadata, so it survives the Korean-coverage
problem that threatens everything else (§3.5). For a music blog it is also the most "blog-shaped"
content Genius holds: it answers *"where does this come from"* rather than *"what does this line mean."*
It needs no lyric anchoring, no per-line UI, and no storage of licensed prose — the relationship is a
fact, not an annotation body, which also sidesteps the unresolved storage question in §6.6.

**Feature 4 is nearly free and should ship with whatever else is chosen.** `annotation_count` already
comes back on the `/search` call the matcher has to make anyway, so a "Genius에서 보기" deep link plus a
count badge costs one extra stored integer and zero licensed text. It is also the designated fallback if
the gate fails outright.

**Feature 5 is the expensive one and the only one that can fail on a technicality.** It needs every
Genius `fragment` to resolve to a unique segment of *our* lyric text, which came from a different source.
Do not design its schema or UI before the anchoring measurement in §6.3 comes back.

**Recommended Step 1 if Thread 1 proceeds:** features **1 + 3 + 4** as a single metadata block —
no anchoring, no licensed prose stored, language-independent, and useful even if annotation coverage
turns out thin. Then re-evaluate 2 and 5 against the gate results.

**Placement warning.** `lyrics_service.get_normalized` early-returns at `:229-233`
(`if out.availability != "ok": return out`) *before* `attach_translation`. A metadata block placed there
is unreachable for every `not_found` track — i.e. exactly the slice Thread 2 has not filled. Features 1,
3 and 4 do not depend on lyrics existing, so they must attach **above** that early return.

### 6.3 The gate (run ONE 60-track pass, dump raw responses, answer both questions offline)

Sample = engaged ∩ `match_status='matched'` (**N=1,921** — the only rows the viewer can render),
**60 tracks stratified 17 KR / 43 non-KR**.

- **G1 (primary):** usable story on **≥36 of 60** (60%), usable = strict artist+title match **and** ≥3
  referents with non-empty body and `is_description=false`
- **G1-KR (stratum floor):** **≥6 of 17** Korean-artist tracks (35%)
- **G2 (fallback):** About description ≥200 normalized chars on **≥36 of 60** (60%)
- G1 and G1-KR pass ⇒ build the per-line layer. G1 <24/60 **and** G2 <24/60 ⇒ stop, fall back to a
  zero-storage "Genius에서 보기" deep link + `annotation_count` badge. G1 fail + G2 pass ⇒ song-level
  panel only.

**Anchoring feasibility (same data, zero extra calls).** Byte-matching is impossible — confirmed on
prod that LRCLIB's `lyric_plain` for Charli XCX "360" has no section headers and its own punctuation
conventions. Critically **1,565 of 1,686 renderable rows (92.8%) carry `lyric_synced`**, and
`normalize_lyrics` derives segments from `parse_lrc(lyric_synced)`, **not** from `lyric_plain` — so
anchoring must be measured against the synced segments the viewer actually renders. Metric: referents
resolving to a *unique* segment range. **≥70% overall + median ≥60%/track** ⇒ per-line feasible;
40–70% ⇒ hybrid with an unanchored drawer; **<40%** ⇒ song-level panel only. Report KR/non-KR
separately.

### 6.4 Probe script status

A draft exists in this session's scratchpad (not committed — it targets the wrong population and has a
known false-PASS bug where the `usable` metric omits the `not loose` term that `strict` has, so a
wrong-artist title-only match scores as coverage). Before running: fix that, replace the hand-rolled
`norm()` with `canonical_base_title` / `_artist_identity_ok` from `lyrics_matcher.py`, add an
`artists.aliases` query ladder (**27 of 67** Hangul-named artists in the sample population have no
Latin alias and their Genius pages are romanized), paginate `/referents`, and abort on 401 rather than
reporting 0% coverage.

### 6.5 Token — owner action, do not paste the value into chat

1. genius.com → sign in → `https://genius.com/api-clients` → New API Client
   (Website `https://www.ratemymusic.blog`; Redirect URI is cosmetic, we never run OAuth)
2. "Generate Access Token" — that value only; Client ID/Secret are irrelevant
3. Put it in SSM yourself. Adding a key to `/myblog/worker` is inert for the running Lambda
   (`config.py:151-168` `_load_secrets` reads only known keys; `GEMINI_API_KEY` sits there unwired as
   precedent). Omit `--key-id` to keep the existing KMS key.
4. Add `GENIUS_ACCESS_TOKEN` to CLAUDE.md's never-log list.

### 6.6 Licensing — UNVERIFIED, owner must check

The morning capture asserted CC-BY-NC-SA 3.0. **Not confirmed.** genius.com serves a JS-challenge shell
(terms page is an ~11KB bootstrap with no text; `/static/licensing` 403s) and is unreachable from this
environment. The one clause confirmed from docs.genius.com: **"Commercial use of the Genius API is not
allowed without a license."** Owner should check, in a real browser:
(a) `genius.com/static/terms` — the licence on user-contributed annotations;
(b) `genius.com/api-clients` — the API terms, specifically **whether annotation bodies may be stored in
our DB or only displayed**. If storage is disallowed, Thread 1 reduces to metadata (samples/credits).
Also settle whether `ratemymusic.blog` counts as commercial (ads/affiliate/paid anything).

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

## 8. What blocks execution

1. **RFC promotion `draft → accepted`** — hard rule 5, owner-only. Nothing starts without it.
2. **Filter shape** — E (genre + title form + vocal guard, 0 FP) vs F (empirical label yield, 2 FP,
   no genre dependency) vs both composed. Owner was mid-decision when this record was written;
   **F emerged after the question was asked and may change the answer.**

Secondary, non-blocking: split Thread 2 into its own `plan.md` row (the RFC's own OQ5); whether to file
the two matcher defects (§3.6) as separate rows; whether to run Genius from the worker Lambda or a local
poller (a local poller dies with the Mac — there is precedent: a 07-20 reboot stalled a queue 3 days).

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
- "Genius annotations are CC-BY-NC-SA 3.0" → **unverified**
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

## 11. Next-session resume order

1. Read this document. **Do not re-derive §3; do re-check anything time-sensitive** (LRCLIB coverage
   moves within a day — that is the lesson of §9).
2. Get the two blockers in §8 answered.
3. If Thread 2 is approved: Step B, then Step A, in separate sessions unless the owner says "go".
4. Thread 1 stays parked until the owner produces a Genius token and answers §6.6.
