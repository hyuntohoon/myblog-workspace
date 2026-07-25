# DATA-catalog-noise-and-lyrics-coverage: stop ingesting noise, make lyrics coverage converge

- **Status**: draft (needs owner accept — hard rule 5)
- **Owner**: 박지훈
- **Created**: 2026-07-25
- **Plan row**: `plan.md` → DATA-catalog-noise-and-lyrics-coverage
- **Absorbs**: `DATA-release-noise` item **(a) ingest-side filter** (Step 2 here is that item, with
  measurements). `DATA-release-noise` (c) exact-dup dedup stays where it is.
- **Sibling**: `FEAT-lyrics-annotations` (Genius / "가사 이야기") — Thread 1 there is **not** in this RFC.

---

## Goal

Four independently-mergeable changes that share one root cause: **the catalog ingests bulk classical
compilation noise, every downstream surface inherits it, and the lyrics pipeline has no way back for a
track it missed on the first try.**

When this RFC is done:

1. Searching a common word returns music the user is looking for instead of opera scenes.
2. Bulk-compilation classical stops entering the catalog at all, which simultaneously cleans the new-
   releases strip, the release calendar, the catalog runway, and the lyrics queue's intake.
3. The unresolved-lyrics pool stops growing and the daily re-check spends its budget where lyrics are
   actually appearing.
4. The owner can force an album's lyrics to fill now instead of waiting ~94 days.

Every number below was measured against prod on 2026-07-25. Provenance and the corrected baseline live
in `FEAT-lyrics-annotations` §3, §4, §9–10.

## Non-goals

- **Hiding classical from users.** This is becoming a multi-user site. A user who wants Chopin must find
  Chopin. Step 1 is a *ranking* fix, not a filter; Step 2 targets bulk compilations credited to dead
  composers, not classical as a genre.
- **Any owner-taste whitelist.** Rules key on properties of the content only — never on what the owner
  has listened to. (Owner decision, 2026-07-25.)
- **Deleting anything.** Every exclusion is a reversible mark plus a holdout.
- **Touching editorial surfaces.** `daily_picks`, `daily_pick_queue`, `album_research`,
  `review_buckets`, `editor_buckit.py`, `buckit_nightly.py` audited clean — every row is owner-initiated
  and a filter there would only delete the owner's own choices (it would have removed ROSALÍA `LUX`).
- **Solving Korean-language lyrics coverage.** Real and confirmed by the owner as a problem to solve
  (LRCLIB returns 0/6 and 0/12 on brand-new Korean albums vs 75–100% for Western majors), but it needs a
  source we do not have. Tracked separately; Step 4 must not pretend to fix it.
- **Genius.** Blocked on an owner-created token. See `FEAT-lyrics-annotations` §6.

## Current state

### The single choke point

`myblog_worker/worker/service/album_ingest_service.py:43-50` `_SELECT_ELIGIBLE` selects the sweep roster
on `artists.popularity >= ARTIST_POP_MIN` (50, `config.py:79`) **and nothing else**. Both the release-
calendar confirm candidates (`:156-167`) and the catalog enqueue (`:191-201`) are derived from that one
query's result. Dead composers clear the popularity bar easily — Bach 75, Mozart 74, Chopin 72,
Beethoven 71, Schubert 62 — because budget-compilation labels credit them as primary artist on
high-stream tracks. **116 of 1,723 eligible artists (6.7%) are classical.**

Consequences, measured:

- last 7 days: **195 new albums, 72 (37%) from classical artists**; **2,498 new tracks, 1,813 (72.6%)**
  on those albums. Weekly classical share of album creation is accelerating: 3/166 (06-01) → 14/510
  (06-22) → 18/156 (07-13) → **68/162 (42%) (07-20)**
- **Franz Schubert produces 39 release-calendar events — the single largest producer in the system**
  (Madonna: 12). Erik Satie 13, Beethoven 12
- 77 of 509 spotify-source release rows (15.1%) are classical-album-linked; **0 of 77 iTunes and 0 of 80
  MusicBrainz rows are** — the noise is 100% the Spotify ingest path

### Search (`myblog_music`)

`app/repositories/track_repo.py:44-49` and `:57` order results by `Track.views.desc()`.
**`tracks.views` is 0 on all 26,602 rows** — the ranking signal is dead, so results fall through to
`created_at` and classical wins on sheer volume.

Measured: **45.9% of track results are classical.** Of 50 common one-word queries, 20 are ≥50% classical
and 5 are **20/20**: `Prelude`, `Suite`, `Nocturne`, `Butterfly`, `Theme`. Searching `Butterfly` returns
twenty *Madama Butterfly* scenes; BTS / Travis Scott / Smashing Pumpkins sit at ranks 41–49, three "more"
pages down. `Suite` puts Billie Eilish's *BITTERSUITE* at **rank 226**. This surface backs `/search`,
the writer CommandPalette, the 오늘의 곡 picker, and AddAlbumModal.

### New releases / release calendar

Live prod, 2026-07-25: home "새 앨범" strip **0/12 classical**; `/releases/` July (landing view)
**2/148 (1.4%)**; **June, one "‹ 이전" click away, 18/167 (10.8%)**.

Today's clean strip is **luck plus a filter shipped yesterday**, not a solved problem:

- the 30-day candidate pool is **53 of 89 (59.6%) classical**; the compilation filter removes 50, and the
  3 survivors rank 31/36/37 **only because they were released 2026-06-26 and recency decay sank them**
- simulated at release-day recency over the last 180 days, **22 of 22 classical albums would have entered
  the top 12** — roughly one every 8 days
- the shipped filter (`myblog_music/app/services/compilation_filter.py:11-16`) **explicitly promises to
  preserve "genuine classical performances."** That is the opposite of the owner's requirement. Its
  efficacy also swings by month (94.6% July, 64.7% June) because it keys on label/artist-count/title
  pattern, not on classical-ness
- **third path has no filter at all**: `myblog_backend/app/api/routes/release_feed.py:125-180`
  (`GET /api/me/release-feed`) serving `/radar/` and the home ForYou strip. Its own comment declares
  `Cross-repo twin: myblog_music/app/services/release_calendar_service.py`, but only the music twin got
  the filter. Latent today (owner's feed: 5 rows, 0 classical) and live the moment a classical artist is
  followed — the owner already tracks Claude Debussy and Michael Korstick

**Catalog cap is NOT currently starving anything** (a hypothesis this investigation disproved):
`MAX_CATALOG_ALBUMS = 5000` (`config.py:83`), albums = 2,934 (58.7%), and a 60-day CloudWatch Insights
scan for `catalog cap reached` returns **0 matches**. Enqueue budget is not binding either (max 26 of
`MAX_ENQUEUE_PER_TICK=60` over 12 daily ticks). What classical *does* do is spend the runway: cap arrival
moves from ~2027-02-01 to **~2026-12-06, 57 days earlier**. Direct AWS cost is **~$0.02/month** — this is
a convergence problem, not a money problem.

### Lyrics pipeline

Trigger chain and the full corrected arithmetic: `FEAT-lyrics-annotations` §3.1–3.3. Load-bearing facts:

- `lyrics_incremental` (every 15 min) gives a new track **exactly one attempt**, ~15 minutes after
  ingest — precisely when LRCLIB is emptiest. The written row is a sentinel (`WHERE tl.track_id IS NULL`),
  so incremental never returns
- `lyrics_reassessment` (daily, stalest-first, 150/run) is the only way back. Re-check rate 146/day,
  **actual drain 2.25/day**, hit rate **1.54%**, intake ~129/day median ⇒ **net +180/day**
- **10,536 of 14,057** tier-0 rows have never been re-checked; the queue head is still `2026-07-01`
- raising the batch limit cannot work: the constraint is the 1.54% hit rate (break-even ≈ 60×), and
  LRCLIB already 429s at concurrency 20 (12 skips 07-23, 22 on 07-24)
- **recency is a 32× signal once classical is controlled for**: albums released ≤60 d and non-classical
  flip **26.7% (32/120)** vs **0.8% (1/120)** for the raw pool; 3.3% at 60–365 d; **0.0%** beyond a year.
  Review-bucket membership adds nothing (25.6%) — it is recency, not ownership
- tier-1 (2,751 best-of rows) is **structurally unreachable**: tier-0 always fills `LIMIT 150`, so the
  supersession promised at `lyrics_reassessment_service.py:77-82` has never executed

## Target state

- `track_repo.search_by_title` ranks by album popularity; classical share of track results **45.9% → 15.1%**
  with no classifier at all, and **→ 7.0%** with the optional Step 1b predicate.
- `_SELECT_ELIGIBLE` excludes classical-artist sweeps behind `INGEST_EXCLUDE_CLASSICAL`, with a
  deterministic 1-in-20 holdout that keeps measuring the misclassification rate forever.
- The unresolved-lyrics pool stops growing (net daily change ≤ 0, against today's **+180/day**) and the
  daily job re-checks recent non-classical releases first, lifting the hit rate from **1.54%** toward the
  measured **26.7%** ceiling for that population.
- One `aws sqs send-message` fills a named album's lyrics in the next worker invocation.

## Steps

**Step 1 and Step 2 are `parallel`** — different repos, no shared file, no ordering constraint.
**Step 3 must precede Step 4** (both edit `_fetch_unresolved_tracks`; and Step 4 copies that method, so
it must copy an already-correct version — while deliberately *omitting* the exclusion, because the
expedite path must always bypass it).

---

### Step 1 — search ranking (`parallel`)

**1a (required).** `myblog_music/app/repositories/track_repo.py:44-49` and `:57`: replace
`Track.views.desc()` with `Album.popularity.desc().nullslast()`, adding an explicit
`.join(Album, Track.album_id == Album.id)` to the `base` select at `:32-35` (`selectinload` does not
produce a joinable alias). Keep `Track.views` as a trailing tiebreak so the column still matters if it is
ever populated.

Safe: `models.py:287-289` declares `album_id` NOT NULL and prod has **0 orphan tracks**;
`albums.popularity` is populated on **2,934 of 2,934**. This makes the track bucket consistent with
`album_repo.py:58-62` and with the Python blend at `search_service.py:102-112`, which already weights
popularity.

**Measured effect: 45.9% → 15.1% classical, with zero classifier and therefore zero false-positive
surface.**

**1b (optional, decide after 1a lands).** A reversible read-side predicate in the same `WHERE`, isolated
in a new `myblog_music/app/services/classical_filter.py` mirroring how `compilation_filter.py` isolates
the DATA-release-noise predicate, behind `CLASSICAL_FILTER_ENABLED: bool = False` and
`CLASSICAL_FILTER_HOLDOUT_HEX: str = "0"` (1-in-16 rows stay visible, so the misclassification rate stays
measurable). Combined effect **45.9% → 7.0%**. The classifier *alone* only reaches 26.8%, because much of
the residue is opera/aria titles carrying no opus token — **1a is what handles those**, which is why 1b is
optional and second.

No contract change (response shape unchanged), no new route ⇒ no `infra/apigateway.tf`, no
`terraform apply`.

**Verification**:
```
cd myblog_music && pytest && \
psql "$DATABASE_URL" -c "SELECT count(*) FROM tracks t LEFT JOIN albums a ON a.id=t.album_id WHERE a.id IS NULL"   # must be 0
# post-deploy, prod:
curl -s "$MUSIC_API/api/music/search/unified?q=Butterfly&type=track&limit=20" | jq -r '.tracks[].title'
# BTS / Travis Scott / Smashing Pumpkins must appear inside the first 20
```

**Rollback**: revert the ORDER BY (1a) / flip `CLASSICAL_FILTER_ENABLED=False` (1b).

---

### Step 2 — ingest choke point (`parallel`)

`myblog_worker/worker/service/album_ingest_service.py:43-50`, `_SELECT_ELIGIBLE`: exclude artists whose
**artist-level** Spotify genres are classical, with an allowlist escape and a holdout.

```sql
SELECT spotify_id, id AS artist_id, (popularity >= :watch_min) AS watch
  FROM artists a
 WHERE popularity >= :pop_min
   AND ( NOT EXISTS (
           SELECT 1 FROM jsonb_array_elements_text(a.genres) g
            WHERE g NOT IN ('클래식 록','클래식 소울','클래식 컨트리','바로크 팝','클래식 크로스오버')
              AND ( g ~ '클래식|바로크|오페라|오케스트라|협주곡|체임버|인상주의|낭만주의'
                    OR g IN ('발레','합창') ) )
         OR a.spotify_id = ANY(:classical_allowlist)
         OR (abs(hashtext(a.spotify_id)) % :holdout_mod) = 0 )
 ORDER BY spotify_id
```

`myblog_worker/worker/core/config.py`, beside `MAX_CATALOG_ALBUMS` (`:83`):
```python
INGEST_EXCLUDE_CLASSICAL: bool = True
INGEST_CLASSICAL_HOLDOUT_MOD: int = 20   # 1-in-20 keeps flowing → misclassification rate stays measured
INGEST_CLASSICAL_ALLOWLIST: list[str] = []   # owner-opted-in classical artists
```
Add `classical_excluded` / `classical_holdout` counters to the summary log at `:228-237`, emitted with
`warning()` (prod Lambdas run `LOG_LEVEL=WARNING`, so `info()` is invisible).

**Why here.** Calendar confirm candidates and catalog enqueue both derive from this one query. Gating
lower down (`:220-223`, the confirm gate) would stop the calendar while catalog and lyrics intake kept
flowing.

**Why the artist-genre key, not this RFC's other classifiers.** At ingest time the tracks do not exist
yet, so no title rule can apply. Measured on rendered calendar events, the track-level classifier
**misses 11 of the 18 visible June classical events** — budget comps like *"Peaceful Cello"* and
*"Lock In: Classical Piano"* are announced-only (no album row) or carry no `album_genres` tag, so its
genre condition can never fire. The artist-genre key catches **all 36** rendered classical events across
every window.

**Why exact JSONB element matching, never substring.** `클래식` is a substring of `클래식 록`
(classic **rock**), `클래식 소울`, `클래식 컨트리`, `바로크 팝`, `클래식 크로스오버`. A substring rule
would remove **AC/DC, Led Zeppelin, Pink Floyd, Queen, The Rolling Stones, James Brown, Stevie Wonder,
Johnny Cash, Dolly Parton, Andrea Bocelli, Pavarotti, 조수미** — several of which are in the owner's
library and one of which (Rolling Stones) is on the calendar right now. Hence the explicit decoy
exclusion list above.

**ROSALÍA is safe by construction**: `SELECT genres FROM artists WHERE name='ROSALÍA'` → `["라틴"]`. The
`LUX` album carries a classical *album* tag, but this key reads the *artist*, so the false positive that
killed genre-alone (29 tracks) cannot occur.

Owner engagement with `클래식`-tagged artists is 4/1,062 saved (0.4%), 0/117 bucket items, and 2/33
`user_artist_tracks` — Debussy and Michael Korstick, i.e. **deliberately followed**, which is exactly
what `INGEST_CLASSICAL_ALLOWLIST` is for.

House-rule cost: **zero.** No new route, no secret, no migration, no contract change, no synchronous
external call (genres are already in the DB — rule 9 safe).

**Also in this step (twin sweep, mandatory per CLAUDE.md):** apply the existing noise predicate to
`myblog_backend/app/api/routes/release_feed.py:125-180`. Its own comment declares the music-side twin;
only one side got the filter.

**Verification**:
```
cd myblog_worker && pytest tests/test_album_ingest.py
# prod, after one daily tick:
aws logs filter-log-events --log-group-name /aws/lambda/blogWorkerLambda \
  --filter-pattern "album_ingest summary" --limit 3     # classical_excluded > 0, classical_holdout small
psql "$DATABASE_URL" -c "SELECT count(*) FILTER (WHERE EXISTS (SELECT 1 FROM album_artists aa JOIN artists ar ON ar.id=aa.artist_id WHERE aa.album_id=al.id AND ar.genres @> '[\"클래식\"]'::jsonb))::float/count(*) FROM albums al WHERE al.created_at > now() - interval '7 days'"
# must fall from 0.37 toward ~1/20 (the holdout)
```

**Success metric**: classical share of albums created in the trailing 7 days drops from **37% (72/195)**
to **≤ 8%** within two weeks.

**Rollback**: `INGEST_EXCLUDE_CLASSICAL=False`. Nothing is deleted; already-ingested rows are untouched.

---

### Step 3 — lyrics pool hygiene + recency-tiered re-check

Two changes to `myblog_worker/worker/service/lyrics_reassessment_service.py:138-163`.

**3a — stop re-checking rows our only source will never answer.** Mark, never delete: write
`{"excluded_by": "...", "rule_version": "v1", "excluded_at": "..."}` into the existing
`track_lyrics.evidence` JSONB and skip marked rows in `_fetch_unresolved_tracks`. Reversal is one UPDATE.

Rule, measured against the 11,664 `matched` rows as negatives:

| Candidate | Catches (of 14,035) | False positives |
|---|---|---|
| genre tag alone | 5,343 | **49** (incl. 29 ROSALÍA `LUX`) |
| **E** — classical album tag **AND** instrumental-form title **AND NOT** vocal-form title | 3,494 | **0** |
| **F** — empirical label yield: ≥50 attempts, <2% match rate | 3,493 (24.9%) | 2 |

Ship **E ∪ F**. E is the cold-start prior; F is the learned signal — *"Novus Promusica: 1,041 attempts,
0 matches"* is a measurement of our own source coverage, taste-free, genre-free, and **self-correcting**:
if a label starts matching, its statistic moves and the exclusion lifts with no human action. F also
generalises beyond classical (it independently flagged `Digital Devs`, `New Wave Records / ADA`, and
`UME - Global Clearing House` at 3%).

Regex details that cost real albums during design and must survive review: the roman-numeral pattern
requires `[.):]` **followed by a space** (otherwise it eats `I.F.L.Y.`, `V.I.P`, `X.Y.U.`,
`XXX. FEAT. U2.`), and the vocal-form guard (`requiem|mass in|missa|cantata|oratorio|aria|lieder|lied|
opera|chorus|choral|hymn|psalm|magnificat|stabat mater|passion|motet|madrigal|ave maria|te deum|vespers|
song|chanson`) protects **198** pool rows that genuinely have text — including the Mozart *Requiem –
Lacrimosa* the owner has saved.

**Honest framing.** These rows are not proven instrumental. All 14,035 carry
`reason='no_plausible_candidate'`, which means *LRCLIB has no record* — the matcher's real instrumental
verdict is a different status (`no_lyrics`, 882 rows, 435 of them classical). The justification is
**measured source yield: 0/120 on live re-probe**, not a claim about the works. Because the ground can
move, the holdout is mandatory, not optional.

**3b — re-order the queue by release recency.** Replace stalest-first with a recency tier: albums
released ≤60 days first, then 60–365, then the rest. Expected hit rate **1.54% → toward 26.7%** for the
recent tier. Reserve a small slot for tier-1 so the best-of supersession path
(`lyrics_reassessment_service.py:77-82`, currently **dead** — tier-0 always fills `LIMIT 150`) can
finally execute.

**Holdout**: leave a random ~5% (≈175 rows) of the excluded set in the queue. If the rule is right their
promotion rate stays ~0; if it climbs, that rate **is** the misclassification rate. Baseline for
comparison: **1.54% (45 promotions / 2,925 re-checks over 20 days)**.

**Verification**:
```
cd myblog_worker && pytest tests/test_lyrics_reassessment.py
# prod, after 3 daily ticks:
psql "$DATABASE_URL" -f docs/sql/lyrics_pool_health.sql   # net daily change must be <= 0 (today: +180/day)
```

**Success metric**: net pool change ≤ 0/day within 7 days (from **+180/day**), and daily promotions rise
from **2.25/day**.

**Rollback**: `UPDATE track_lyrics SET evidence = evidence - 'excluded_by' WHERE evidence ? 'excluded_by';`
plus reverting the ORDER BY.

---

### Step 4 — album-scoped expedite (after Step 3)

`reassess_album(album_id, limit=None, cooldown_sec=None)` + `_fetch_album_tracks` (a copy of the Step-3
`_fetch_unresolved_tracks` that **omits the exclusion**), one dispatch line in
`myblog_worker/worker/handler.py:310` reading `event.get("album_id")`, and
`LYRICS_EXPEDITE_COOLDOWN_SEC: float = 600.0` in `config.py` as the idempotency bound (the writer's
`ON CONFLICT` sets `updated_at = NOW()`, so a cooldown is what makes a double-fire safe).

~40 lines, worker-only, no `terraform apply`, no contract regen. Fired by one
`aws sqs send-message` to blogSQS — a path `infra/eventbridge.tf` already documents.

The proposed SQL was verified read-only against prod with the real MFF album id
(`62bc17c7-962d-4ebd-9fc6-f0f5488487b2`) and returns exactly its 8 `not_found` rows.

**Defer the route + button (former "PR2").** It costs an `infra/apigateway.tf` route, a human
`terraform apply`, and an openapi/`api.gen.ts` round trip across three repos — for a surface used once or
twice a week (`review_bucket_items` is 117 rows lifetime). Revisit only if the SQS path proves annoying
in practice. **If it is built, it needs a "LRCLIB에 아직 없음" empty state**, or Korean albums (which
return 0/6, 0/12 even brand-new) will look like a bug.

**Verification**:
```
aws sqs send-message --queue-url "$BLOG_SQS" --message-body '{"job":"lyrics_reassessment","album_id":"62bc17c7-962d-4ebd-9fc6-f0f5488487b2"}'
psql "$DATABASE_URL" -c "SELECT t.title, tl.match_status FROM tracks t JOIN track_lyrics tl ON tl.track_id=t.id WHERE t.album_id='62bc17c7-962d-4ebd-9fc6-f0f5488487b2' ORDER BY t.title"
# all 11 rows matched (8 currently not_found + 3 already matched)
```

**Rollback**: the job is promote-only and replacement-guarded; nothing to roll back beyond reverting the code.

---

## Related defects found during investigation (not steps — file as `plan.md` rows)

> **BOTH RESOLVED 2026-07-26** (worker #80/#81 + workspace #698) — see the
> `FIX-lyrics-primary-artist + FIX-isrc-backfill` row in `docs/plan.md` for the shipped detail
> and the one remaining owner action. Kept here because the numbers below are cited elsewhere in
> this RFC; **do not re-file them as new work.**

1. ~~**LRCLIB is searched with the alphabetically-first credit.**~~ **FIXED.** `lyrics_eval_core.fetch_one`
   used `artist_names[0]` from `ARRAY_AGG(DISTINCT a.name)`, so a featured guest became the search artist
   (*"Ariana Grande – I Don't Do Drugs (feat. Ariana Grande)"*). **8,765 of 14,035 `not_found` rows (62%)
   have ≥2 credits** (re-derived 07-26: 8,767 of 14,034). `track_artists.role` is NULL on all 44,546 rows,
   so rather than wait for Spotify's artist order to be captured at sync time, the primary is **derived**:
   album-artist credit first, then `artists.popularity`, then name — via a LATERAL, since Postgres rejects
   `ARRAY_AGG(DISTINCT x ORDER BY y)`. Measured on a 1,793-track ground-truth set built from feature
   clauses in prod titles: **45.34% → 96.77%** (52.45% → 88.26% reweighted to the `not_found` stratum mix).
   Twin sweep covered 8 sites (2 worker services + 6 `tools/`), sharing one imported constant.
   **NB the derived rule is a proxy, not a substitute** — capturing Spotify's `artists[]` ordinal at sync
   time would still collapse both residual failure modes (no album-artist credit; several album-artist
   credits on joint releases), and remains the correct long-term fix.
2. ~~**`isrc_backfill` was never scheduled.**~~ **FIXED.** Service, handler routing (`handler.py:284`) and an
   integration test existed, but no `aws_cloudwatch_event_rule` fired it — hence `tracks.isrc` was 100% NULL.
   It also wrote string sentinels `"not_found"`/`"no_isrc"` into the column, so scheduling it as-is would
   have silently broken every `isrc IS NOT NULL` predicate. The marker moved to `ext_refs->>'isrc_status'` —
   **not** `ext_refs->>'isrc'`, which already means "a real ISRC" on 7,335 rows and is `backfill_genres.py`'s
   "already fetched" predicate. A Spotify **Track Relinking** hazard found in review (a market param can
   return a different `id`, producing a *permanent* false miss) was fixed in the same PR. The EventBridge
   rule is committed but **still needs a human `terraform apply`**.

## Open questions

1. **Ship Step 1b, or stop at 1a?** — 1a alone is 45.9% → 15.1% with zero false-positive surface; 1b adds
   a classifier for → 7.0%. Blocks Step 1's second half. *(Recommend: land 1a, look at the result, then
   decide. 1a carries no classification risk at all.)*
2. **Is `INGEST_CLASSICAL_ALLOWLIST` seeded with Debussy and Michael Korstick?** — the owner already
   follows both via `user_artist_tracks`. Blocks Step 2. *(Recommend: yes, seed them.)*
3. **Does Step 3b (recency re-order) make Step 4 unnecessary?** — 3b lifts the automatic hit rate toward
   26.7% for recent releases, which is most of what the expedite button was for. Blocks Step 4 scope.
   *(Recommend: land 3, measure for a week, then decide whether 4 still earns its keep.)*
4. **How many steps this session?** — hard rule 4 allows one per session unless the owner says go. Steps
   1 and 2 are marked `parallel` and touch different repos. *(Recommend: 1 and 2 together, then 3, then 4.)*

## Decisions log

| Date | Decision | Step |
|------|----------|------|
| 2026-07-25 | Exclusion rules key on content properties only — **no owner-taste whitelist** (site will have real users) | all |
| 2026-07-25 | A correct classical genre tag is **not** grounds for exclusion (ROSALÍA `LUX`); genre may only ever be one condition among several | all |
| 2026-07-25 | Search is fixed by **ranking, not filtering** — classical must stay findable | 1 |
| 2026-07-25 | Block at ingest, not at each downstream surface | 2 |
| 2026-07-25 | Every exclusion is reversible **and** carries a holdout that measures its own error rate | 2, 3 |
| 2026-07-25 | MFF's 8 tracks get filled **by the feature**, not by a manual prod write | 4 |
