# Investigation notes — 2026-07-25/26 lyrics + Genius session

**Audience: the next Claude session, not the owner.** The owner already lived through this. What
follows is the set of things that were expensive to learn and are invisible from the finished RFCs —
measurement traps, wrong turns, and operational facts. Read this before touching
`FEAT-lyrics-annotations`, `DATA-catalog-noise-and-lyrics-coverage`, `tools/genius_anchor.py`, or the
research-note pipeline.

The RFCs carry the *conclusions*. This file carries the *how it went wrong*, because every mistake
below was reached by a plausible route that a fresh session would take again.

---

## 1. Measurement traps that produced confidently wrong answers

Each of these survived at least one round of my own review before an adversarial pass killed it.

### 1.1 Counting the work, not the outcome (a 2.5× error)

I reported the reassessment job's **drain** as ~145/day. 146/day is the **re-check** rate; 98.5% of
re-checked rows stay parked. The rows actually leaving the pool were **2.25/day**.

The consequence was not cosmetic. Under my number the obvious fix was "raise
`LYRICS_REASSESS_BATCH_LIMIT` 1.5× and the pool converges" — a one-line config change. Under the true
number, break-even needs ~60× and LRCLIB throttles first. **The wrong number pointed at a cheap fix
that does not exist.**

> Rule: when a job both *touches* rows and *resolves* rows, never report the touch count as progress.
> Split the query on the resulting state.

### 1.2 Measuring the ledger instead of the screen

I told the owner the new-releases list was 20.5% classical. That was `artist_release_events` over a
180-day window. What actually **renders** is the home strip (0/12) and `/releases/` July (2/148 =
1.4%). I was off by 15×, in the alarming direction, on the surface the owner cares most about.

> Rule: for any user-visible claim, measure what the endpoint returns, not what the table contains.
> Curl the live route.

### 1.3 A population artifact that inverted a conclusion

I probed "does re-checking recent releases pay off?", got 0/30, and concluded **recency is not a
signal**. Wrong: 4,188 of the 5,205 rows in that population were classical, which probes 0/40 on its
own. Genre-controlled, releases ≤60 days flip **26.7% vs 0.8%** — a 32× signal that my sample had
masked entirely.

> Rule: before concluding "X does not predict Y", check what else is inside the X population. A null
> result on a contaminated sample is not a null result.

### 1.4 Substring matching on Korean genre strings

`클래식` is a substring of `클래식 록` (classic **rock**), `클래식 소울`, `클래식 컨트리`,
`바로크 팝`, `클래식 크로스오버`. A substring exclusion rule would have removed **AC/DC, Led Zeppelin,
Pink Floyd, Queen, The Rolling Stones, James Brown, Stevie Wonder, Johnny Cash, Dolly Parton, Andrea
Bocelli, Pavarotti, 조수미** — several in the owner's library, one on the release calendar right now.

Use exact JSONB element containment (`genres @> '["클래식"]'`) with an explicit decoy exclusion list.

### 1.5 Naming the mechanism before checking it

I called the excluded pool "instrumental works that can never have lyrics." The rows say
`reason='no_plausible_candidate'` — *LRCLIB has no record*. The matcher's genuine instrumental verdict
is a **different status** (`no_lyrics`, 882 rows, 435 of them classical). The honest justification is
measured source yield (0/120 on live re-probe), not a claim about the works.

This matters beyond pedantry: "has no lyrics" is permanent, "our source lacks it" can change — which
is precisely why the exclusion design needs a holdout rather than being fire-and-forget.

### 1.6 A matcher artifact I nearly shipped as a product verdict

First anchoring measurement: **33% placed, median 22%** — below the 40% floor, i.e. "the inline
per-line layer is not viable." That number was my matcher, not the data. Requiring near-equal lengths
between a Genius fragment and an LRC line kills exactly the case the feature is about, because LRC
breaks lines where the vocal breathes and Genius breaks them where the sentence ends. The span
algorithm gives **74.7%**.

> Rule: before reporting a low match rate as a limitation of the data, open ten failures and read
> them. Here every sampled failure was the same fixable artifact.

---

## 2. Things that are true and easy to re-doubt

Verified, cited, and likely to be re-questioned by a session that did not see the evidence.

- **`tracks.views` is 0 on all 26,602 rows.** The search ORDER BY is therefore inert and classical
  wins on volume alone. This is why Step 1 of the noise RFC is a ranking fix with no classifier.
- **The catalog cap has never fired.** 2,934/5,000, and 60 days of CloudWatch Insights over
  `catalog cap reached` returns zero matches. I hypothesised cap starvation; it is false. Classical
  does pull the cap date ~57 days earlier, which is a different and smaller claim.
- **Direct AWS cost of the classical noise is ~$0.02/month.** It is a convergence problem, not a
  money problem. Do not argue it on cost.
- **`review-critique-method.md` exists** at `docs/editorial/`, not `scripts/`. I claimed it was
  missing. The real defect is that `scripts/album_research_v2.md` is a hand-synced copy of lines 1–98
  where the relative link resolves to nothing, the headless run has no Read tool anyway
  (`--allowed-tools WebSearch,WebFetch`), and nothing enforces parity between copy and master.
- **Genius `media` carries `spotify:track:` and `apple_music_id` — but rarely.** 1 of 16 sampled
  library tracks, 0 of 15 LUX tracks. It is a match-confidence upgrade, never a primary key. I
  over-claimed this on first sight; do not repeat that.
- **Genius has no album-level object.** Fifteen song records, no album "about", no label field. A
  future implementer will assume album identity is covered. It is not.
- **Every `translations` relationship is a Genius community translation page**, 8–18 per track, not a
  musical relationship. Counting them inflates "this album has 18 relations" nonsense.
- **`annotation_count` exceeds the stored annotation array by exactly one per track that has a
  description** — Genius counts the description as an annotation. On LUX: 128 vs 115, difference 13,
  matching the 13 described tracks.

---

## 3. The load-bearing numbers, with their denominators

Quote these with denominators or they will be misread later.

| Claim | Number | Denominator / window |
|---|---|---|
| Lyrics pool drain | 2.25/day | 45 promotions / 2,925 re-checks, 07-05..07-24 (20 clean days) |
| Promotion hit rate | 1.54% | same |
| Net pool growth | ≈ +180/day | intake ~129/day median (23 d) minus drain |
| Never re-checked | 10,536 | of 14,057 tier-0 rows |
| Recency lift | 26.7% vs 0.8% | 32/120 (≤60 d, non-classical) vs 1/120 (raw pool), live LRCLIB |
| Genius prose, EN vs KR | 7/8 vs 1/8 | description ≥200 chars, 16 saved tracks |
| Genius credits, EN vs KR | 7/8 vs 7/8 | same sample — the asymmetry is the whole design input |
| Korean share of engagement | 47.4% | engaged track set |
| Anchoring resolved to one span | 74.7% | 71 of 95 lyric-bound annotations, LUX, 13 tracks with `lyric_synced` |
| Anchoring placeable (incl. `repeated`) | 94.7% | 90 of the same 95 — 71 single-span + 19 chorus repeats |
| Anchoring unmatched | 5.3% | 5 of 95 lyric-bound. **The 4.9% quoted elsewhere is the same 5 rows over all 103 annotations** — the two figures do not disagree |
| Research-note sample failures | 78/78 and 75/78 | all 78 stored `album_research` notes |
| Repeat-artist corpus | 69% | 54 of 78 notes |
| Search track results classical | 45.9% → 15.1% | ranking fix alone, no classifier |

---

## 4. Operational facts that cost time

- **Bash `cd` persists across calls in this harness.** A `cd myblog_music` earlier in the session made
  later bare `git` commands resolve against that repo, and the rule-1 hook correctly refused a commit
  because *that* repo was on `main`. The workspace branch was fine the whole time. **Always use
  `git -C <abs-path>`.**
- **The scratchpad is invisible to the owner.** Files written there must be delivered with
  SendUserFile; a path alone is useless to them.
- **`tools/` scripts need a venv.** System python has no sqlalchemy/psycopg; use
  `myblog_backend/.venv/bin/python`. `--self-test` paths should avoid importing drivers at all so they
  run anywhere.
- **Agents writing very large single outputs stall.** Two failures this session: a translation agent
  given 4 tracks / 38 annotations, and a probe-suite agent asked to author five scripts in one go.
  Both died on "response stalled mid-stream" after retries. Splitting the translation into 2+1+1
  succeeded immediately. **Size an agent's output, not just its input.**
- **Subagents leave litter in the repo root.** One dropped nine pip `.whl` files, another a 140 KB
  markdown artifact. Check `git status` before committing anything.
- **Bundling fast and slow work in one workflow is a design error.** The owner asked for a
  translation and got it 40 minutes late because a prompt review was in the same run. Ship the thing
  asked for; run the extras separately.

---

## 5. Owner decisions — settled, do not reopen

| Decision | Consequence |
|---|---|
| Exclusion rules key on **content properties only** — no owner-taste whitelist | The site is becoming multi-user; a rule keyed to one person's listening breaks for everyone else |
| **A correct classical tag is not grounds for exclusion** (ROSALÍA `LUX` is genuinely classical-flavoured and correctly tagged) | Genre may only ever be one condition among several |
| **Search is fixed by ranking, not filtering** | A user who wants Chopin must find Chopin |
| Editorial surfaces (`daily_picks`, `album_research`, buckets) are **not** to be filtered | Audited clean; every row is owner-initiated and a filter would have removed `LUX` |
| Korean-language lyrics coverage is a **problem to solve**, not a caveat | Needs a source we do not have; LRCLIB returns 0/6 and 0/12 on new Korean albums |
| **Terms/licensing is out of scope** — personal, non-commercial research | Recorded in `FEAT-lyrics-annotations` §6.8. Do not re-raise, do not let it shape design, record nothing if rediscovered |
| Research prompt **v3 is a candidate alongside v2**, not a replacement | Run both, compare, then decide |
| Reception/opinion **is allowed in the research note body**, dressed as opinion with vote counts | Resolves the contradiction where §3.5 required the critical conversation while v2 banned it |

---

## 6. Where to pick up

1. Both RFCs are **draft and unaccepted**. Rule 5 makes promotion owner-only; nothing starts without it.
2. `tools/genius_anchor.py` works and is self-tested. A six-album KR/EN regression is scheduled for
   **2026-07-29** (`~/.claude/scheduled-tasks/genius-anchor-multi-album-test/`). Its real question is
   whether Korean albums have *any* annotations to anchor — report coverage count separately from
   anchoring rate, and do not conflate them.
3. `scripts/album_research_v3.md` has not yet been compared against v2 on the same album. The LUX v3
   run was in flight when this file was written.
4. ~~Two pre-existing defects are filed but unowned~~ — **both FIXED 2026-07-26** (worker #80/#81 +
   workspace #698). The alphabetically-first-artist LRCLIB search bug (62% of `not_found` rows have ≥2
   credits) now derives the primary as album-artist → popularity → name: 45.34% → 96.77% on a
   1,793-track ground-truth set, twin sweep across all 8 sites. `isrc_backfill` no longer writes string
   sentinels into `tracks.isrc` (marker moved to `ext_refs.isrc_status`) and its EventBridge rule is
   committed — **but still needs a human `terraform apply` before it runs**. Detail → `docs/plan.md`.
