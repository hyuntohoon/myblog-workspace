# FEAT-youtube-playback-provider: YouTube as a second playback provider

- **Status**: in-progress — promoted from `draft` on **2026-09-05 with explicit owner
  approval in-session** (CLAUDE.md hard rule 7; Claude never self-promotes). The owner
  answered Open question 1 — Milestone A starts — and Step A1 shipped the same day.
- **Owner**: TBD
- **Created**: 2026-09-05
- **Plan row**: `plan.md` → FEAT-youtube-playback-provider

---

## Goal

A member with no Spotify account can play the tracks in their Buckit, because a
second playback provider exists beside Spotify. Spotify remains the catalog, the
ingest path, the listening source and the default player; YouTube is what
someone without Premium gets, and what anyone can choose deliberately. Nothing
about the catalog, the queue, membership or `spotifyPlayback.ts` changes to make
that true.

## Non-goals

- **No unofficial API.** `ytmusicapi` and its kin need custody of a member's
  Google session cookies or a fragile TV-device OAuth flow. Both violate
  YouTube's Terms and put the member's Google account at risk. This confirms the
  standing `FEAT-multi-user-accounts` decision rather than reopening it.
- **No Spotify removal, reduction or migration.** `tracks.spotify_id` stays
  `NOT NULL UNIQUE` and stays in the row.
- **No generic playback engine.** One dispatcher module, roughly forty lines.
  Refactoring `spotifyPlayback.ts` into a provider-agnostic engine before a
  second provider exists in production is building an abstraction against one
  example.
- **No catalog-wide YouTube backfill.** See _Current state → the two limits that
  shape the design_. The arithmetic forbids it; it is not a matter of patience.
- **No YouTube listening history, now-playing or scrobbling**, and no
  channel-subscription import as "followed artists". A channel is not an artist.
- **No remote-device control.** There is no YouTube equivalent of Spotify Connect.
- **No background or audio-only playback, and no UI drawn over the player.**
  Both are explicit YouTube policy prohibitions, not preferences.
- **No YouTube default.** Spotify is chosen first wherever both are available.
- **Milestone B (OAuth, playlist/likes import) is not designed here.** It is
  gated on Phase 0-B and carries a sketch only, deliberately — see _Open
  questions_.

## Current state

Read on `origin/main` at ws `71470e0` · front `a8d9eef` · backend `5675d00` ·
music `d0f8aee` · worker `766fd1f` · shared_db `abf8d57`, in isolated worktrees.
Production row counts read read-only 2026-09-04.

### The seam already exists

`ARCH-playback-authority-convergence` shipped a layering whose own target-state
diagram names `front/src/lib/spotifyPlayback.ts` a **provider adapter**, and
`GET /api/playback/resolve?type=track&id=<uuid>` (backend
`playback_service.py:95`) already maps an internal Track UUID to a provider URI.
The seam the 2026-06 RFCs said would have to be built is built.
`front/src/lib/playback/session.ts` is the only writer and imports 11 symbols
from the adapter.

### Identity, measured

| Identifier | Rows | Total | Coverage |
|---|---:|---:|---:|
| `tracks.spotify_id` | 30,875 | 30,875 | 100% (`NOT NULL`) |
| `tracks.isrc` | 29,119 | 30,875 | 94.3% |
| `albums.ext_refs->>'upc'` | 3,935 | 3,956 | 99.5% |
| `artists.musicbrainz_id` | 6,047 | 6,726 | 89.9% |

`tracks.id` UUID stays canonical. **YouTube cannot be searched by ISRC**, so
ISRC is useful for cross-checking a candidate, never for finding one.

### Two documented premises the code contradicts

1. **"Membership stores a provider-neutral track identity (ISRC / artist+title),
   resolved to a provider id at play time."** — `FEAT-pocket-buckit` D3,
   repeated verbatim as a comment at `front/src/lib/spotifyPlayback.ts:37`.
   **False, and false in our favour.** Playback membership carries
   `review_bucket_items.track_id`, a foreign key to `tracks.id`; all 29
   production playback rows have it. There is no ISRC-or-artist+title resolution
   step to build or unwind. Fixed in Step A1 rather than left to mislead.
2. **"`search.list` costs 100 units against a 10k/day quota."** —
   `FEAT-pocket-buckit` technical validation. Google has since moved
   `search.list` into **its own bucket: 100 calls/day at 1 unit each**. The
   ceiling is unchanged; the consequence is not. Search no longer draws on the
   10,000-unit pool, so a `videos.list` refresh job runs essentially free beside
   it. The old arithmetic reached the right number for the wrong reason and
   would have mispriced the maintenance job.

### The two limits that shape the design

- **YouTube Developer Policy III.E.4.c and III.E.4.d — 30 calendar days, with
  no exception for resource ids.** Stored API data must be deleted or refreshed
  after 30 days, and III.E.4.d extends the same ceiling to a videoId obtained
  from a plain public `search.list`. **"Once mapped, never search again" cannot
  be implemented as a permanent cache.** It survives as a *refreshed* one, and
  cheaply: a refresh is `videos.list?id=…`, 1 unit per 50 ids — a fully-mapped
  30,875-track catalog is 618 calls per 30 days, about 21 units a day. The same
  call returns `status.embeddable`, `status.privacyStatus`, `status.madeForKids`
  and `contentDetails.duration`, so **compliance refresh and dead-video
  detection are one job, not two.**
- **`search.list` at 100 calls/day.** Mapping all 30,875 tracks would take 309
  days of saturated quota, and the earliest rows would expire before the last
  were written. Discovery is the scarce resource; maintenance is not.

Together these force the design into exactly one shape — **on demand,
member-confirmed, small N** — and that forcing function is recorded here so
nobody re-proposes a backfill.

### Phase 0-A — measured 2026-09-05 (this is new evidence)

Phase 0-A existed because two numbers governing this decision were borrowed, not
measured. Probe: 20 tracks sampled from `tracks` with a reproducible seed, plus
2 control tracks whose correct result is not in doubt; `search.list`
(`maxResults=5`) then `videos.list`; top result hand-judged by Claude.

| | Carried in the docs | Measured on our catalog |
|---|---|---|
| Top result is the wrong version | "~34%" (`FEAT-pocket-buckit` D3, unsourced) | **0%** |
| Top result is the correct studio version | — | **20 / 20** (16/20 if every uncertain call is counted against us) |
| No usable result | — | **0** |
| `status.embeddable` | never measured | **20 / 20** |

Gate was `correct ≥ 12/20` and `embeddable ≥ 16/20`. **GO under either reading.**
Both controls passed, so the score is not an artefact of a lenient harness.
By cohort: k-music 6/6 · western-pop 5/5 · classical-compilation 5/5 ·
jazz-compilation 2/2 · other-regional 2/2.

**The "~34% wrong-version" figure was the load-bearing justification for
deferring YouTube across three RFCs. It does not hold here.**

Three findings the counts do not show:

1. **"- Topic" channels are why this scored so well.** 7 of 20 matched through
   YouTube's auto-generated Topic channels, which carry the same distributed
   master Spotify does — including Welte-Mignon and Duo-Art piano-roll transfers
   on auto-generated compilation albums, matched on an exact title string.
   Obscurity in our catalog does not predict absence on YouTube, because the
   same distributor feeds both services.
2. **3 of 20 top results are unofficial uploads** (fan lyric channels). The
   audio is right, but such an upload can go dead without warning. This is why
   `verify_state` and the refresh job are not optional.
3. **Duration cannot be used as an automatic correctness check.** Music-video
   results run +5s to +17s long because of intros, and the Nirvana control runs
   **−22s** because the official video is an edit. The delta is a useful hint
   for a human and a trap for a validator.

Probe artefacts are throwaway and deliberately uncommitted; the judged output
was reported in-session on 2026-09-05.

### Prerequisite already shipped

`infra/functions/security_headers.js` allowlisted `https://www.youtube.com`
(`script-src`, `frame-src`), `https://www.youtube-nocookie.com` (`frame-src`)
and `https://i.ytimg.com` (`img-src`) in ws #984, merged 2026-09-05.
**Merging did not deploy it** — workspace infra is applied by the owner locally.
Until that apply lands, the IFrame API is still blocked in production, silently.

An API key for YouTube Data API v3 is stored at SSM SecureString
`/myblog/youtube` as `{"YOUTUBE_API_KEY": …}`.

## Target state

One new module per layer, one dispatcher, no generic engine.

```
  CATALOG (unchanged — Spotify remains the only source)
  ┌──────────────────────────────────────────────────────────────────────┐
  │  artists · albums · tracks      tracks.id UUID = canonical identity   │
  └───────────────────────────┬──────────────────────────────────────────┘
                  ┌───────────┴────────────┐
        tracks.spotify_id          track_provider_refs          ← NEW
        (in-row, unchanged)        (track_id, 'youtube', videoId,
                                    embeddable, last_verified_at)
  BACKEND       ▼                        ▼
  GET /api/playback/resolve?type=track&id=<uuid>[&provider=youtube]
        spotify → "spotify:track:…"    youtube → "youtube:video:…" | 404

  FRONTEND
  ┌──────────────────────────────────────────────────────────────────────┐
  │  lib/playback/provider.ts   ← NEW, ~40 lines. Chooses the adapter.    │
  ├────────────────────────────┬─────────────────────────────────────────┤
  │  lib/spotifyPlayback.ts    │  lib/youtubePlayback.ts        ← NEW    │
  │  UNCHANGED                 │  IFrame API · local clock               │
  └────────────────────────────┴─────────────────────────────────────────┘
                              ▼
              lib/playback/session.ts   THE ONLY WRITER (role unchanged)
                              │
        ┌─────────────────────┼──────────────────┬────────────────────┐
        ▼                     ▼                  ▼                    ▼
  GlobalPlaybackBar    PlaybackPanel      LyricsViewer      YouTubePlayerDock
  (unchanged)          (unchanged)        position from      ← NEW. Visible,
                                          ACTIVE provider    ≥200×200, never
                                                             overlaid.

  WORKER (EventBridge, not SQS — MusicBrainz alias-fill precedent)
  youtube_ref_refresh · daily · videos.list, 50 ids/call, 1 unit
  · resets last_verified_at · re-reads embeddable/privacy
  · DELETES any row it cannot refresh inside 30 days  (III.E.4.c/d)
```

Three properties are deliberate. **Spotify's file is not opened** — the
dispatcher wraps it, so a YouTube regression cannot reach Spotify playback.
**The provider is a property of the play attempt, not of the track** — the same
queue row plays either way, which is what keeps Buckit, lyrics and the queue
untouched. **The YouTube player is a separate surface**: policy forbids drawing
anything in front of it, so it cannot be folded into the existing mini-player.

### New table (Step A1)

```sql
CREATE TABLE track_provider_refs (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  track_id         uuid NOT NULL REFERENCES tracks(id) ON DELETE CASCADE,
  provider         text NOT NULL,
  external_id      text NOT NULL,          -- YouTube videoId
  external_kind    text NOT NULL,          -- 'video'
  source           text NOT NULL,
  embeddable       boolean,
  privacy_status   text,
  made_for_kids    boolean,
  duration_sec     integer,
  verify_state     text NOT NULL DEFAULT 'live',
  last_verified_at timestamptz NOT NULL DEFAULT now(),   -- the III.E.4 clock
  created_at       timestamptz NOT NULL DEFAULT now(),
  updated_at       timestamptz NOT NULL DEFAULT now(),

  CONSTRAINT ck_tpr_provider       CHECK (provider IN ('youtube')),
  CONSTRAINT ck_tpr_kind           CHECK (external_kind IN ('video')),
  CONSTRAINT ck_tpr_source         CHECK (source IN ('user_confirmed','playlist_import')),
  CONSTRAINT ck_tpr_verify_state   CHECK (verify_state IN ('live','gone','not_embeddable')),
  CONSTRAINT uq_tpr_track_provider UNIQUE (track_id, provider)
);

CREATE INDEX idx_tpr_stale ON track_provider_refs (last_verified_at)
  WHERE verify_state = 'live';
```

- `tracks.spotify_id` is **not** moved here and **not** made nullable.
  `provider IN ('youtube')` deliberately excludes `'spotify'` so this table
  cannot quietly become a second home for it.
- `UNIQUE (track_id, provider)` means **one video per track in v1**. Official
  Audio vs Music Video vs Live is a real ambiguity, and the v1 answer is that
  the member picks one and can re-pick.
- `source` has no `'search_auto'` value: there is no unconfirmed mapping in v1,
  enforced in the constraint rather than in prose.
- `last_verified_at` is a **compliance field, not a cache hint.** A row past 30
  days is deleted, not merely re-fetched on demand. That belongs in the
  migration comment.
- Precedent: `artist_source_ids` already has this shape for artists. This is its
  track-level sibling, with a retention clock the artist one does not need.

### API surface

| Endpoint | Repo | Change | Gateway route |
|---|---|---|---|
| `GET /api/playback/resolve?…&provider=` | backend | Extend. Optional param, default `spotify` — no existing caller changes. `provider=youtube` reads `track_provider_refs`, 404s when unmapped, which shipped `uris.ts` already treats as a durable miss. **A3 adds `410 Gone`** for a row that exists but is expired/unplayable (OQ8). | No — rides `GET /api/{proxy+}` |
| `GET /api/music/search/youtube-candidates?track_id=` | **music** | New. **In music on purpose:** the service-boundary invariant forbids a synchronous provider call from a user-facing *backend* endpoint, and `/api/music/search/candidates` is the standing precedent. Putting it in backend would be the violation. | No — rides `ANY /api/music/{proxy+}` |
| `PUT /api/playback/track/{track_id}/youtube-mapping` | backend | New. Body `{video_id}`, verified with `videos.list` before write — the row is GLOBAL, so a client-supplied `embeddable` would let one member break everyone's playback. Caller must hold the track in one of their own buckets (OQ7) — not owner-only. Upsert, so a concurrent confirm is not a 500. | **Yes** — explicit route + Cognito authorizer |
| `DELETE /api/playback/track/{track_id}/youtube-mapping` | backend | New. "Wrong video" — without it a bad match is permanent and the feature loses trust on its first miss. Same standing check as the PUT (OQ7). Idempotent: deleting nothing is a 204. | **Yes** — explicit route + Cognito authorizer |
| `GET /api/lyrics/{spotify_track_id}` | backend | **Keep.** Still works under YouTube playback; every catalog track has a `spotify_id`. | Unchanged |
| `GET /api/lyrics/tracks/{track_id}` | backend | **Later, staged.** Sequenced after Milestone A, never bundled into it. | Yes, when it lands |

**The two mutation paths were CORRECTED on 2026-09-06** (A3 review). This table
originally read `PUT /api/playback/providers/youtube/mapping` with `track_id` in
the body, and `DELETE …/mapping/{track_id}`. The shipped shape puts the track in
the path for both, which is what `infra/apigateway.tf` and `openapi.json` carry.
Corrected here rather than left for A4 to trip over: **A4 is a front leg specced
from this table**, and a route table that names endpoints the backend does not
serve is worse than no table.

Every change is additive, so contract merge order is **service → workspace →
front**, with `api.gen.ts` regenerated and committed before the front deploy gate
will pass.

## Steps

Steps A0–A5 are Milestone A. B1–B2 do not begin until Phase 0-B returns GO.

### Step A0 — CSP + Google project

**SHIPPED 2026-09-06.** CSP hosts merged in ws #984 and **applied**; Cloud
project, YouTube Data API v3 and API key created; key stored at SSM
`/myblog/youtube`.

Applied and verified 2026-09-06:
- `terraform apply` run against the workspace stack. The plan was exactly what
  this step predicted — `0 to add, 1 to change, 0 to destroy`, every CSP
  directive changed by ADDITION only, nothing removed.
- The live edge header now carries `script-src ... https://www.youtube.com`,
  `frame-src ... https://www.youtube.com https://www.youtube-nocookie.com` and
  `img-src ... https://i.ytimg.com`. **Merging really had not deployed it**: the
  LIVE CloudFront function was read immediately beforehand and had no YouTube
  host at all, 32 days after the merge.
- Regression check, run **on the production origin under the enforcing CSP**, so
  it tests the real policy rather than a local approximation: `sdk.scdn.co`
  loads and `window.Spotify` is an object (**the incumbent is not regressed**),
  `www.youtube.com/iframe_api` loads and `window.YT` is an object, a
  `youtube-nocookie.com` iframe frames successfully, and
  `securitypolicyviolation` fired **zero** times. The YouTube half of that
  result is attributable to this apply, because the pre-apply header was read
  first and allowed none of it.
- Public-page sweep (`/`, `/reviews/`, `/genres/`, `/canon/`, `/collection/`,
  `/releases/`, `/members/`): all 200, all carrying the header, no console
  errors. A `/review/` page could not be swept because prod still has zero
  published 평론.

### Phase 0-A step 3 — RUN 2026-09-06, and it corrects this document

The measurement, and it does not match what this RFC assumed. Harness: the
IFrame API on a throwaway local page, two embeddable controls plus one
embed-disabled video and four absent ids, each played muted and settled on
`onError` or a timeout.

| Case | Documented here | **Measured** |
|---|---|---|
| Embeddable control (x2) | plays | **plays, no error, state `1`** |
| Embedding disabled by owner | `101` / `150` | **`150`** |
| Deleted / private / nonexistent (x4) | `100` | **`150`, never `100`** |

**`100` was not produced by a single case.** Everything unavailable collapses to
`150`. The behavioural consequence is nil — both codes were already mapped to
`'unavailable'` — but the design consequence is not: **`onError` cannot tell
"gone" from "embed-disabled"**, so A4 must not branch on the two codes, and the
discriminator has to be `videos.list` in the A5 refresh job. That is what the
`verify_state` design already does, so the design survives the correction; the
claim about `100` does not. Do not write `if (code === 100)` in A4 — it is a
dead branch.

**The embed-disabled video had to be found by measurement, not by memory.** A
batch of 20 famous music videos was 20/20 embeddable; scanning `mostPopular`
music charts across 8 regions found 3 non-embeddable videos out of 240 (1.25%),
all in one region. That 1.25% independently corroborates the 20/20 embeddable
count in the table above.

**A control caught a harness defect before it became a finding.** On the first
run every case returned `150`, *including the embeddable control*. Served from
`http://127.0.0.1:8791` the origin itself is rejected; re-served from
`http://lvh.me:8791` the control played and the discrimination appeared. Without
the control this would have been written down as "the IFrame API returns 150 for
everything", which is false.

*Not measured*: error `2` (malformed id). The probe's own case never settled,
and the case is unreachable by design — ids reach the player from `videos.list`,
never from user input.

**Verification**: `terraform plan` read in full (done); post-apply read of both
the LIVE function code and the live `curl -sI` header; real-browser Spotify
regression check on the production origin (done, above).

**Rollback**: revert the function, re-apply. Seconds, no data involved.

---

### Step A1 — Mapping table + resolve + the false comment

`V55__track_provider_refs.sql`; `resolve_uri` gains a `provider` argument; both
schema mirrors diffed in the same change. **Also corrects the
`FEAT-pocket-buckit` D3 claim and the `spotifyPlayback.ts:37` comment** — see
_Current state_. That correction ships here rather than as its own chore because
this is the step whose design the false claim would otherwise misdirect.

Repos, **in this order**: workspace (canonical schema) → shared_db → backend
(+ the shared-db pin) → workspace (merged contract) → front. Prereq: A0.

The order matters and the obvious one is wrong. shared_db's required `test`
check runs `cmp tests/canonical_schema.sql` against **workspace `main`**
(`ci.yml`), so shared_db cannot go green until the workspace schema PR has
merged — `docs/contracts/README.md` steps 1–3 say the same. And front is not
optional here: this step's own spec corrects `spotifyPlayback.ts`, and the
backend merge invalidates `docs/contracts/openapi.json` until the contract is
re-merged.

**Verification**:
```
pytest
# control test: omitting `provider` must still return the Spotify URI,
# so the suite is not self-satisfying
```
Migration applied to production and the Neon test branch in the same session;
`/api/playback/resolve` exercised with and without the param.

**The shared-db pin has THREE sites in backend, not two** — `requirements.txt`,
`requirements.lock` (regenerate with `scripts/compile_requirements.sh`, never by
hand), and a hardcoded SHA in `.github/workflows/deploy.yml` used to load the
canonical schema for the integration job. `TrackProviderRef` is imported at
module scope, so a missed bump is an import-time failure for the whole Lambda,
not a broken endpoint.

**Rollback**: revert the code PR. The table is unread by anything else.

**SHIPPED AND DEPLOYED 2026-09-05**, across five PRs in the corrected order:
workspace #986 (canonical DDL, this RFC's promotion, the `FEAT-pocket-buckit`
errata) → workspace #987 (the review fixes below) → shared_db #80 (`65a13f9`) →
backend #174 (`9629e0b`, deploy run `33936566712` green) → workspace #988
(contract) → front #443 (`0f1598e`).

`V55__track_provider_refs.sql` was applied to **prod and the Neon test branch in
the same session**, structure read back column-by-column from both and found
identical. Constraints were exercised as *behaviour* rather than confirmed
present: `provider='spotify'` rejected, a non-`user_confirmed` source rejected, a
valid row accepted with `verify_state='live'` and the III.E.4 clock set, a second
video for the same track rejected, deleting the track cascading the mapping to
zero. Those checks now live as **committed** tests in the backend integration
suite, because a manual session is not a regression test.

**Verified against production after the deploy**, not only in CI: the control
(no `provider`) still returns the Spotify URI; `provider=spotify` is identical;
`provider=youtube` on an unmapped track is 404; `provider=soundcloud` is 422 at
the edge and never falls through to Spotify. With one temporary mapping row,
`provider=youtube` returned `youtube:video:…` **while the default still returned
the Spotify URI**, and the same row aged to 31 days was correctly refused by the
retention filter. Row deleted afterwards; the table is back to 0. `smoke.sh prod`
30/30, 0 failures.

**Corrected mid-step after an independent review, before the remaining merges.**
Three of the findings were defects this step would otherwise have shipped:

- `idx_tpr_stale` was partial on `verify_state='live'` while its comment claimed
  it served the III.E.4 sweep. It **excluded exactly the rows the sweep exists
  for** — a `'gone'` row still stores a videoId, `privacy_status` and
  `made_for_kids`, so the 30-day clock applies to it in full. Now unconditional.
- `ck_tpr_source` permitted `'playlist_import'`, advertising a capability the
  table's shape cannot deliver (see open question 7). Narrowed to
  `'user_confirmed'`.
- The backend integration file opened with `CREATE TABLE IF NOT EXISTS <the whole
  DDL>`, which would have made those tests green **whether or not V55 was applied
  or correct**. It now asserts the table and all five constraints exist and fails
  loudly if the pin was not bumped.

Both DDL corrections were applied to prod and the test branch as an explicit
delta under a row-count guard that refuses to run on a non-empty table.

Also from the review, and now written into this step: the shared-db pin has
**three** sites in backend, and the merge order stated here was wrong in a way
that would have redded a required check.

Resolve additionally filters on `last_verified_at` inside 30 days — the review's
observation that the compliance argument had no enforcement at all until the
Step-A5 job exists, and that a sweep which is down is not a sweep.

The two false `FEAT-pocket-buckit` claims and the `spotifyPlayback.ts` comment
were corrected in the same step. The "29 production playback rows carry
`track_id`" figure was re-measured directly rather than quoted: `item_type =
'playback'` → 29 rows, 29 with `track_id`, 0 without.

One number in _Current state_ is already a snapshot rather than a constant:
`tracks` read **31,096** rows on 2026-09-05, against the 30,875 measured 2026-09-04.
The backfill arithmetic is unaffected — it is still hundreds of days of saturated
`search.list` quota — but do not quote 30,875 as a fixed catalog size.

---

### Step A2 — Candidate search in music

`GET /api/music/search/youtube-candidates`: `search.list` + `videos.list`
enrichment, ranked by duration proximity to `tracks.duration_sec` — **ranked,
not auto-accepted** (see the duration finding in _Current state_). Explicit
timeout on every outbound request. Quota exhaustion returns a distinct status
the UI can print, and never retries in a loop.

The track is identified by **catalog id**, not by a caller-supplied title and
duration: that is what makes the ranking trustworthy, since a caller cannot
shift the ordering by misreporting the duration, and the query is built in one
place. Track artists first, album artists as the fallback — a compilation track
carries its performer on the track, which is how the Phase 0-A probe matched the
classical and jazz compilations.

Candidates that are not embeddable or not public are filtered out **in the
service**, using the same predicate as the resolve read (`embeddable IS TRUE`,
OQ9), so the two cannot drift apart and an unpickable candidate never reaches a
member.

Repos: music → workspace. Prereq: A0.

**Verification**:
```
pytest   # stub models real latency and returns a payload satisfying
         # every reader-side required field; plus a quota-exhausted case
```
Live call for five known tracks.

**SHIPPED 2026-09-06** (music PR, workspace infra + contract PR).

- 254 passed / 7 skipped / 1 pre-existing environmental failure
  (`test_candidates_localstack` needs a running LocalStack; it fails identically
  on a pristine `origin/main` worktree and CI runs it against a real service
  container). 43 tests are new; all 7 skips are `TEST_DB_URL` integration tests
  that CI runs for real and fails on skip.
- **Every new test mutated — 11 mutations, all caught**, and one SURVIVED the
  first pass and exposed a real defect: the ISO-8601 duration regex required a
  `T` section, so the live-stream shape `P0D` returned `None` by failing to
  match rather than through the zero-guard. The test passed for the wrong reason
  and the guard was unreachable. Both fixed; that mutation now kills four tests.
- **Live call, 5 production tracks, real API (500 quota units): 5/5 returned
  candidates with the correct match ranked first.**

**The live call re-confirmed "ranked, never auto-accepted" against our own
catalog, and more sharply than Phase 0-A did.** Phase 0-A's argument was that 3
of 20 top results were unofficial uploads. The stronger version is what
proximity ranking actually surfaces: for 호미들 "끝" the top candidate by delta is
a fan LYRIC video at 1s, *tied* with the correct `- Topic` upload; for Baby Keem
"scapegoats" an INSTRUMENTAL ties the official audio at 3s. A karaoke,
instrumental or lyric re-upload routinely matches the real track's duration to
the second — so duration proximity does not merely fail to detect a wrong
version, it actively **promotes** one. Only a human reading `channel_title` can
separate them, which is why that field is in the response and why there is no
threshold anywhere in this step.

**Two API behaviours were measured while building it**, both now encoded:
`contentDetails.duration` is a bare `P0D` for a live stream (no `T` section at
all), and zero must read as UNKNOWN or it wins every proximity comparison; and
`videos.list` reports a deleted or private id by **omission**, never as an
error.

**Infra**: no `infra/apigateway.tf` change — music is fronted by the `ANY
/api/music/{proxy+}` catch-all and auth is enforced in-app. The workspace leg
adds `YOUTUBE_SECRETS_PARAM` to the music Lambda and `/myblog/youtube` to
`myblog-music-ssm-read`. The IAM policy `description` was deliberately left
unretitled: changing it forces `aws_iam_policy` **replacement**, and the
destroy/create window would drop the attachment long enough for a music cold
start to fail its required-key check and 500. `policy` updates in place, so the
final plan is `0 to add, 2 to change, 0 to destroy`.

#### The review blocked the first revision on three defects, and all three were real

**1. The API key leaked into httpx's own INFO log.** The first revision put the
key in the query string — the shape most of Google's documentation shows — and
closed only the *exception* channel, with a test asserting exactly that. httpx
logs `request.url` at INFO on every completed request, so the key was one
`basicConfig(level=INFO)` or one Lambda `ApplicationLogLevel` change from
CloudWatch, and the only thing holding it back was the prod root logger
defaulting to WARNING: **an unset default, not a control**. Worse than the hole
itself, the passing test made the suite *read as* "key leakage is covered".
The key now travels as `X-goog-api-key`, matching `spotify_client.py`.
Demonstrated against the live API with `basicConfig(level=INFO)` deliberately
on: httpx logged 10 full request URLs and the key appears in **none** of them.
Under the previous code all 10 would have carried it.

**2. The DB transaction was held open across both outbound calls** — verbatim
the recurring bug class that produced the Neon `ProtocolViolation`. `get_db`
closes only in its `finally`, which runs *after* the response is built, i.e.
after the network calls. The handler now does fetch → materialise → close →
external work, and the artist fallback moved into the SELECT as a second alias
of `artists`, which also removed a lazy load that would have raised
`DetachedInstanceError` once the session was closed. The test asserts the
**ordering** (`db.close` before `search.list`), because "close was called" is
also true of a handler that closes it last.

**3. A malformed `track_id` reached psycopg and 500'd** — the AUDIT-2026-07-26
A-3 class, with `parse_uuid_or_404` already in the repo one import away. The
route is now in `tests/test_malformed_ids.py` beside the original four, as the
first *authenticated* member of that list.

Six should-fixes were also taken; the two worth recording as design facts are
that **the timeout budget exceeded the Lambda ceiling** (10s × 2 sequential
calls against `musicApi`'s 15s, so a slow-but-not-failing YouTube killed the
function before either timeout fired and the whole 429/503/502 taxonomy never
ran — now 4.0s, asserted by a test against the 15s figure), and that
**`rateLimitExceeded` was being told to come back tomorrow** when it is a
short window that clears in seconds. Daily quota and rate limit are now
separate exceptions: both 429, different advice, different `Retry-After`.

**`videoCategoryId=10` was removed on a measurement.** It looked like an obvious
narrowing and was a change to the exact input Phase 0-A scored 20/20 on.
Re-running the same 5 production tracks with and without it returned 5
candidates each and the identical top match both ways — narrowing an input that
already scores 20/20 can only lose results.

#### The local venv was behind `requirements.lock`, and its green was false

fastapi 0.136.3 / starlette 1.1.0 locally against **0.141.1 / 1.6.0** in CI. A
test passed locally and failed in CI with a bare `StopIteration`, because
**FastAPI 0.141 no longer flattens `include_router` into `app.routes`** — it
inserts `_IncludedRouter` wrappers reachable only through `original_router`, and
the child route's `.path` is the *unprefixed* path. So neither `app.routes` nor
a full-path comparison finds an endpoint. Anything in this codebase that walks
`app.routes` looking for routes is broken on the locked version. This step's
worktree now carries its own venv built from `requirements.lock`.

#### A second vacuous test, found by mutation

21 mutations were run and 20 were caught. The survivor: folding the rate-limit
reasons into the daily-quota set leaves `RATE_LIMIT_REASONS` **empty**, and a
`pytest.mark.parametrize` over an empty set collects **zero cases** — it reports
as one *skip*, not a failure. The disjointness assertion beside it is likewise
satisfied by two empty sets. Both tests now pin membership by name. This is the
second time in this step that a test passed for a reason unrelated to what it
claimed to check; **parametrising over a production constant makes the test as
deletable as the constant.**

---

### Step A3 — Confirm-and-save UI

Two backend mutation routes **plus their Terraform routes**; a picker in the
track row listing candidates with thumbnail, channel and duration delta; a
"wrong video" action. Candidates surface the channel, because 3 of 20 measured
top results were unofficial uploads and the member should see that.

A3 also carries three things decided on 2026-09-05 (Open questions 7–9), because
A3 is the first writer and the table is still at 0 rows when it runs:

- **Write authorization is standing, not ownership** (OQ7). Both mutations
  require the caller to hold the track in one of their own buckets —
  `review_bucket_items.track_id` under `review_buckets.user_id = <sub>`.
  **Not `require_owner`**: a non-owner member holds 13 of the 29 live playback
  rows and would otherwise be unable to fix their own bad matches.
- **`created_by_member_id` is recorded for attribution only** (OQ7). It must
  never be read by an authorization check — doing so reintroduces per-member
  ownership through the back door, which this RFC decided against.
- **`embeddable` becomes `NOT NULL`** and `resolve`'s filter tightens from
  `IS NOT FALSE` to `IS TRUE` in the same change (OQ9).
- **`resolve` gains `410 Gone`** for a row that exists but fails the liveness /
  retention / embeddable filter, keeping `404` for "no row" (OQ8). Backend leg,
  so A4 stays pure front.

Repos: backend → workspace (infra + contract) → front. Prereq: A1, A2.

**Verification**:
```
pytest
pnpm lint && pnpm exec astro check && pnpm test
```
Each new test mutated to confirm it fails when its assertion is removed.
New protected routes matched against `infra/apigateway.tf` — a missing route is
a 404 at the edge. Real-browser: map a track, reload, confirm persistence, unmap.

The authorization decision needs its own negative test, not just a happy path:
a member authenticated as A must be **rejected** when mutating a track only
member B has bucketed, and that test must be mutated to confirm it fails when
the standing check is removed. `410` vs `404` needs both branches asserted —
an unmapped track and a row aged past retention — since a single-branch test
passes against a service that always returns one of them.

---

### Step A4 — Adapter, dispatcher, dock

`youtubePlayback.ts`, `playback/provider.ts`, `YouTubePlayerDock`,
provider-keyed `uris.ts` cache, capability matrix gains a provider dimension.

The adapter implements only what YouTube has — `play`, `sendPlayerCommand`
(play/pause/seek), a position getter, and a state subscription mapped from
`onStateChange`. It does **not** implement `listDevices`, `transferPlayback`,
`getTrackLiked`, `setTrackLiked`, `sendPlaybackMode` or `getStreamingToken`; it
returns the shipped `'no-capability'` outcome, which the existing UI renders.
Error codes `100` and `101/150` map to `'unavailable'` and mark the mapping row
for re-verification.

`uris.ts` today keys the memo cache on `trackId` alone and carries a comment
saying "ids are immutable, a hit can never go stale". **That stops being true
for YouTube** — a YouTube entry must expire with the mapping. This is the one
place where shipped reasoning genuinely does not carry over. Concretely, the
memo is unsound for YouTube in **both** directions, and the positive one is the
easier to miss: `verify_state` flips under A5, retention expires at 30 days, and
A3 re-points — so a cached `youtube:video:…` can outlive its row just as a
cached miss can. Any TTL must sit well under the 30-day retention window, and
the A3 mutations must invalidate the entry outright.

With OQ8 answered, the three states are distinguishable at last: `200` plays,
`410` is mapped-but-unplayable and drives the re-pick affordance (never memoised
durably), `404` is unmapped and keeps today's durable-miss behaviour.

The dock is 16:9, at least 480×270 where the viewport allows, never below the
200×200 floor, carries the YouTube attribution mark, and **nothing may be drawn
over it** — which specifically rules out reusing the lyrics blur backdrop.

Repos: front. Prereq: A3. **Difficulty High · Risk High — this is the step that
can break shipped Spotify playback.**

**Verification**:
```
pnpm test   # the full session.test.ts suite must pass UNCHANGED —
            # that is the regression proof
```
New YouTube tests stub the IFrame API with realistic lag, never instant returns.
Real-browser, both providers in one session: Spotify play → pause → seek, then a
YouTube-mapped track and repeat. Player measured ≥200×200 and unobstructed.

**Rollback**: revert the front PR — one squash commit, restores a state already
verified in production.

---

### Step A5 — Refresh job

`youtube_ref_refresh` on EventBridge, daily. Selects by `last_verified_at`
ascending, batches 50 ids into `videos.list`, writes back `embeddable`,
`privacy_status`, `made_for_kids`, `duration_sec`, `last_verified_at`. An id
absent from the response is deleted or private → `verify_state='gone'`. Any row
still unrefreshed at 30 days is **deleted** — policy, not tidy-up.

Loop shape is fetch ids → materialise → **close session** → HTTP → fresh short
write session. Holding a transaction across the API loop is the recurring bug
class that produced the Neon `ProtocolViolation`.

Repos: worker → workspace (EventBridge rule). Prereq: A1 — but **ship in the
same week as A4, not later**: it is invisible and therefore easy to defer, and
deferring it puts the feature out of policy on day 31.

**Verification**:
```
pytest   # including a row aged past 30 days that must be DELETED, not skipped
```
Run once manually before scheduling — a job verified only by reading is not
verified. Confirm `last_verified_at` actually moved in the database.

**Rollback**: disable the EventBridge rule.

---

### Steps B1–B2 — Milestone B (gated, sketch only)

**Do not begin until Phase 0-B returns GO.** B1 is YouTube OAuth
(`user_integrations` CHECK += `'youtube'`, KMS-enveloped refresh token,
disconnect deletes all YouTube-derived rows within 7 days per III.E.4).
B2 is playlist/likes import. Neither is designed here, on purpose: designing
against an unmeasured API is how the "provider-neutral membership" claim in
`FEAT-pocket-buckit` got written down and believed for fifteen months.

Phase 0-B is 8 steps run on a real account with real YouTube Music use; the
governing question is whether a playlist created *inside YouTube Music* appears
in `playlists.list(mine=true)`. Google does not document it, every secondary
source says no, and none of them is Google.

## Open questions

1. ~~**Does the owner want Milestone A started at all?**~~ — **ANSWERED 2026-09-05:
   yes.** The owner approved starting Milestone A and promoting this RFC in the same
   instruction. A1 shipped that day; A2 was then blocked on the Console quota
   read — which was **never Open question 2**, despite this line having said so.
   That gate lived only in the Decisions log and had no number; the mis-pointer
   propagated into two session hand-offs before anyone read both. It is resolved
   below.
2. ~~**Phase 0-A step 3 (IFrame error codes) was not run.**~~ — **ANSWERED
   2026-09-06: run, and it refuted the documented mapping.** Everything
   unavailable returns `150`; `100` was not produced by any of four absent-video
   cases. See Step A0 for the table, the harness-defect control, and the
   consequence for A4 (`onError` cannot distinguish "gone" from
   "embed-disabled" — only `videos.list` can, which is the A5 job).
3. **When does Phase 0-B run?** — Blocks B1 and B2 entirely. Requires an owner
   with real YouTube Music use; no code is written until it returns.
4. **Is the `youtube.readonly` scope labelled "sensitive" or "restricted" in the
   Console?** — Restricted implies an annual third-party security assessment,
   an owner-level cost decision. Blocks B1. Read the literal label during
   Phase 0-B step 8.
5. **One video per track, or several with a choice at play time?** — v1 answers
   "one, re-pickable" via `UNIQUE (track_id, provider)`. Revisit only if the
   confirm UI shows members wanting both an audio and a video mapping.

6. **The API key in SSM `/myblog/youtube` was pasted into a session transcript
   on 2026-09-05 and is therefore an exposed credential.** The owner chose to
   keep using it. It should be rotated before A2 puts it on a live user-facing
   path. Blocks nothing today.

7. ~~**Are mappings global or per-member?**~~ — **ANSWERED 2026-09-05: global,
   with writes scoped to standing rather than to ownership.** Decided by Claude
   under an explicit owner delegation ("너가 알아서 해봐" — "handle it as you
   see fit"), not chosen by the owner; it is recorded here so it can be
   overturned cheaply, and the measurement it rests on is below.

   **What was measured** (prod, read-only, 2026-09-05). Playback membership is
   not owner-only: of the 29 `review_bucket_items` rows with
   `item_type='playback'`, the owner holds **16** and a single non-owner member
   holds **13**. Gating the A3 mutations behind `require_owner` — the obvious
   way to close the hole without touching the schema — would therefore lock the
   second-heaviest user of this exact surface out of fixing their own bad
   matches. That option is rejected on evidence, not on taste.

   **The collision surface is empty, and that is weaker evidence than it looks.**
   Tracks held by *both* members: **0** (16 + 13 = 29 = the union). But two
   members drawing 16 and 13 tracks from a 31,096-row catalog would be expected
   to overlap 0.007 times by chance, so zero overlap measures **sparse usage,
   not disjoint taste**. It says there is no contention to fix today; it does
   not say the design prevents contention. Do not cite it as if it did.

   **The "expensive later" pressure is overstated.** This question was framed as
   decide-now because "adding `member_id` later means altering a UNIQUE
   constraint on a populated table". Bounded: discovery is capped at
   `search.list` 100 calls/day *and* requires per-row member confirmation, and
   this RFC forbids a backfill outright (309 saturated days). The table reaches
   hundreds of rows, not 31k. A UNIQUE change at that size is a non-event.

   **The decision.** The mapping stays global — one row per track, no
   `member_id` in the key. It is a catalog fact discovered with a *shared*
   scarce resource (100 `search.list` calls/day for everyone) and carried by a
   *shared* 30-day compliance clock; per-member rows would duplicate both.
   `artist_source_ids` remains the right precedent.

   The authorization hole is closed separately, because it is real whether or
   not anyone collides: A3's mutations require that **the member holds the track
   in one of their own buckets** (`review_bucket_items.track_id` under a
   `review_buckets.user_id = <sub>`). Standing, not ownership — it grants the
   write to exactly the people the mapping affects, needs no schema change, and
   keeps the non-owner curator working. Known constraint, accepted rather than
   hidden: a track nobody has bucketed cannot be mapped, so an album-view picker
   must bucket first. A3 records `created_by_member_id` for **attribution and
   audit only** — never read for authorization, or it becomes per-member
   ownership by the back door.

   **Revisit when**, and only when: Phase 0-B returns GO (B1's per-member
   disconnect and B2's import genuinely need the member dimension, and B is
   still sealed), or the cross-member overlap above stops being 0. Re-measure it
   with the same query rather than assuming.

8. ~~**`resolve` collapses "never mapped" and "mapped but dead" into one 404.**~~
   — **ANSWERED 2026-09-05: `404` keeps meaning "no row", and a row that exists
   but fails the liveness / retention / embeddable filter answers `410 Gone`.**
   Semantically exact, and it is the smallest thing that lets A3's "wrong video"
   affordance ever appear.

   Correcting the framing this question shipped with: two of the three things it
   implied were missing are **already in Step A4's scope** — the provider-keyed
   `uris.ts` cache and the fact that the file's "ids are immutable, a hit can
   never go stale" comment stops holding for YouTube are both written there. The
   genuinely open part was only the discriminator, and that is what is decided
   here. (Re-read A4 before quoting this question; it was easy to double-count.)

   Placement: the `410` lands in **A3's backend leg**, not A4, so A4 stays a
   pure front change. No shipped behaviour is at risk — nothing sends
   `provider=youtube` until A4, and the Spotify path never returns `410`. A4's
   rewritten cache must treat `410` as *unplayable-but-mapped*: not memoised
   durably, and surfaced as the re-pick affordance rather than as a dead row.

9. ~~**Should `embeddable` be `NOT NULL` at write time?**~~ — **ANSWERED
   2026-09-05: yes, landed in A3**, and the `resolve` filter tightens from
   `IS NOT FALSE` to `IS TRUE` in the same change. The Step-A1 review was right
   that the NULL tolerance protects nothing in v1.

   Why A3 and not a V56 now: A3 is the *first writer*, so the table is still at
   **0 rows** when A3 runs — the constraint is exactly as free then as it is
   today, and shipping it inside A3 avoids a migration and a deploy for a table
   nobody writes to yet. If A3 slips far enough that another writer appears
   first, take it as its own migration instead.

10. ~~**What is the project's real `search.list` quota, and does A2 wait for
    it?**~~ — **ANSWERED 2026-09-06: A2 does not wait. The figure is
    operational, not a gate.** This is the gate that was recorded only in the
    Decisions log ("documented defaults are assumed and must be confirmed before
    A2") and mis-cited as Open question 2 above. Three things retire it:

    - **No code path depends on the number.** A2 never counts units. It reacts
      to Google's own 403 `reason`, maps it to a distinct `429`, and does not
      retry. A cap of 100 or of 1,000 changes how many mappings a day the
      members get, not what the service does.
    - **The one thing the number was load-bearing for is already decided.** It
      justified forbidding a catalog-wide backfill — and that prohibition holds
      at *any* plausible cap, so re-reading it cannot reopen the question.
    - **Live behaviour was measured instead, which is the stronger evidence.**
      On 2026-09-06 five real `search.list` calls (500 units) and ~15
      `videos.list` units succeeded against the production key. The pool is
      therefore ≥515 units and both endpoints are enabled and unrestricted. A
      Console reading would add only the ceiling.

    *Residual, stated so it is not lost*: if the cap is the documented 10,000
    units/day, that is ~100 discovery searches across all members per day. The
    member-visible consequence of hitting it is a `429` telling them to come
    back — never a wrong mapping and never a crash. The owner can read the
    Console figure whenever convenient; nothing waits on it.


## Decisions log

| Date | Decision | Step |
|------|----------|------|
| 2026-09-06 | **A3's review found the PUT would ship dead, asymmetrically.** `YOUTUBE_SECRETS_PARAM` and the `/myblog/youtube` IAM grant were added for MUSIC only; backend had neither, so the SSM read would raise AccessDenied, `config.py` would swallow it by design, and **every PUT would answer 503 while DELETE kept working** — it makes no outbound call. A smoke that only unmapped would have reported the feature healthy. **Rule: when a fail-closed path and a no-op path share a feature, a smoke that exercises only the no-op path proves nothing.** | A3 |
| 2026-09-06 | **Concurrent confirm was a 500, and it needed only one member.** The write was read-then-write with a commit AND up to 4s of `videos.list` between the read and the INSERT, so two callers both saw "no row" and both inserted — and `_map_mapping_errors` had no `IntegrityError` branch. OQ7's own design is that several members may re-point the same GLOBAL row, and a double-click reproduces it alone. Now `ON CONFLICT DO UPDATE` with `created_by_member_id` excluded from the update set; a residual collision maps to 409 | A3, OQ7 |
| 2026-09-06 | **Step A5 shipped.** Expire-then-refresh, expire FIRST so a quota failure cannot postpone a policy deletion. Refresh takes only `'live'` rows: a settled `'gone'` row polled daily would have its clock reset forever — compliant on paper, permanently useless — while left alone it gives the member up to 30 days of the useful `410` signal and is then reclaimed. The job fails LOUDLY on a missing key, unlike the request-path clients, because **a retention sweep that silently does nothing looks identical to a healthy run** | A5 |
| 2026-09-06 | **This RFC's own API-surface table named routes the code does not serve** (`/api/playback/providers/youtube/mapping`, with `track_id` in the body). Corrected to the shipped `/api/playback/track/{track_id}/youtube-mapping`. Worth a row because **A4 is a front leg specced from that table** — a route table that names endpoints the backend does not serve is worse than no table | A3, A4 |
| 2026-09-06 | **`410` was invisible to the contract.** `raise HTTPException` never reaches FastAPI's schema generator, so OQ8's entire purpose — letting A4 branch on 410 vs 404 — lived only in prose. Declared in `responses=`. **A status code the front must branch on is part of the contract, and only the decorator puts it there** | A3, OQ8, A4 |
| 2026-09-06 | **A2's review found the API key in httpx's INFO log — and a passing test that hid it.** The key was a query parameter; httpx logs `request.url` at INFO on every completed request. The first revision closed the *exception* channel and shipped a test asserting exactly that, so the suite read as "key leakage is covered" while the larger channel stayed open, held shut only by the prod root logger defaulting to WARNING — an unset default, not a control. Now `X-goog-api-key`. Verified live with `basicConfig(level=INFO)` on: 10 request URLs logged, key in none. **Rule: when closing a leak, enumerate the channels before writing the test that says it is closed** — a test naming one channel is evidence about that channel and nothing else | A2 |
| 2026-09-06 | **The local venv was behind `requirements.lock` and produced a false green.** fastapi 0.136.3/starlette 1.1.0 local vs 0.141.1/1.6.0 in CI. **FastAPI 0.141 stopped flattening `include_router` into `app.routes`** — routes hide behind `_IncludedRouter.original_router` and carry the *unprefixed* path — so a route lookup by path finds nothing and fails as a bare `StopIteration`. Anything walking `app.routes` is broken on the locked version. Step worktrees now build their own venv from the lock | A2 |
| 2026-09-06 | **Step A2 shipped, and the live call sharpened the "never auto-accept" rule.** 5 prod tracks against the real API: 5/5 correct match ranked first. But the top candidate by duration proximity for 호미들 "끝" is a fan LYRIC video tied at 1s with the correct `- Topic` upload, and Baby Keem "scapegoats" ties the official audio at 3s with an INSTRUMENTAL. **Duration proximity does not merely fail to detect a wrong version — it promotes one**, because a karaoke/instrumental/lyric re-upload matches the real duration to the second. `channel_title` is in the response because a human is the only component that can separate them. Quota exhaustion maps to a distinct **429** (healthy service, valid request, spent budget) with no retry; a missing key fails closed at 503. 11 mutations run on the new tests, all caught — and one survived first pass, exposing a duration regex that made its own zero-guard unreachable | A2, OQ10 |
| 2026-09-06 | **Step A0 completed — and "merged" was not "deployed" for 32 days.** The ws #984 CSP was applied; the LIVE CloudFront function read immediately beforehand carried no YouTube host at all. Post-apply regression **on the production origin under the enforcing CSP**: `window.Spotify` and `window.YT` both load, a nocookie iframe frames, zero `securitypolicyviolation` events. The YouTube half is attributable to the apply because the pre-apply header was read first | A0 |
| 2026-09-06 | **Phase 0-A step 3 run — it refutes this RFC's error-code mapping.** Embed-disabled → `150` as documented, but four separate absent/deleted/nonexistent ids ALSO returned `150`; **`100` was produced by nothing**. Behaviour is unchanged (both already mapped to `'unavailable'`) but the design consequence is real: `onError` cannot distinguish "gone" from "embed-disabled", so A4 must not branch on the codes and the discriminator must be `videos.list` in A5 — which is what `verify_state` already does. A CONTROL caught a harness defect first: served from `http://127.0.0.1` every case returned `150` *including the embeddable control*; re-served from `http://lvh.me` the control played and the discrimination appeared. Without the control this would have been recorded as "the API returns 150 for everything" | A0, OQ2, A4 |
| 2026-09-06 | **The Console quota read is retired as a gate (OQ10), and the gate had no number.** It lived only in this log and OQ1 mis-cited it as "Open question 2" — which is the IFrame error codes — and that mis-pointer propagated through two session hand-offs. Retired because no code path depends on the figure (A2 reacts to Google's own 403 `reason`, never counts units), the one thing it was load-bearing for (forbidding a backfill) holds at any plausible cap, and live behaviour is stronger evidence than a Console figure: 500 `search.list` units plus ~15 `videos.list` units succeeded on 2026-09-06, so the pool is >=515 and both endpoints are enabled. Residual: at the documented 10,000/day the ceiling is ~100 discovery searches across all members, surfaced as a `429` — never a wrong mapping | A2, OQ10 |
| 2026-09-05 | Phase 0-A run. Correct-version **20/20**, embeddable **20/20**, controls pass → **GO**. The "~34% wrong-version" figure carried through three RFCs does not hold on this catalog. | A0 |
| 2026-09-05 | CSP hosts merged (ws #984) without waiting for the numbers, because a closed CSP makes a player spike produce a wrong result rather than a weak one. Not applied — owner applies workspace infra locally. | A0 |
| 2026-09-05 | Google Cloud project + YouTube Data API v3 key created by the owner; stored SSM SecureString `/myblog/youtube`. Console quota figures not read — the documented defaults are assumed and must be confirmed before A2. | A0 |
| 2026-09-05 | **Owner approved starting Milestone A and promoted this RFC `draft` → `in-progress`** (hard rule 7 — the approval was given in-session; Claude does not self-promote). Open question 1 closes. `in-progress` rather than `accepted` because A1 shipped the same day, so `accepted` would understate the state. | A1 |
| 2026-09-05 | **Step A1 shipped.** V55 applied to prod + the Neon test branch in one session; constraints verified as behaviour on the test branch (spotify rejected, search_auto rejected, one-video-per-track enforced, FK CASCADE confirmed), not merely listed from `pg_constraint`. `resolve_uri(provider=…)` added with the control test that omitting the argument still returns the Spotify URI. | A1 |
| 2026-09-05 | **Step A1 review found three shipping defects**, all fixed before the remaining merges: a partial `idx_tpr_stale` that excluded the rows the III.E.4 sweep exists for; `ck_tpr_source` advertising `'playlist_import'` against a table shape that cannot support it; and an integration suite that created its own copy of the table and so could not fail if V55 were wrong. Also caught: a third pin site in `deploy.yml`, and a stated merge order that would have redded shared_db's required check. Open questions 7-9 opened rather than silently decided. | A1 |
| 2026-09-05 | **A1 deployed and verified in production** — backend run `33936566712`, `smoke.sh prod` 30/30. The endpoint was exercised live on six paths including the no-parameter control and a temporary mapping row (deleted afterwards). **A2 is NOT unblocked**: it still needs the real `search.list` quota read from the Console. | A1 |
| 2026-09-05 | **Open questions 7, 8 and 9 answered under owner delegation** ("너가 알아서 해봐" / "handle it as you see fit"), no code written. OQ7: mappings stay **global**, and A3's write authorization is **standing** (the member holds the track in one of their own buckets), not `require_owner`. OQ8: `410 Gone` for a row that exists but is expired/unplayable, `404` stays "no row", landing in A3's backend leg. OQ9: `embeddable NOT NULL` + filter tightened to `IS TRUE`, landed in A3 while the table is still 0 rows. | A3/A4 |
| 2026-09-05 | **The measurement that decided OQ7**, read-only on prod: the 29 `item_type='playback'` rows split owner **16** / one non-owner member **13**, so `require_owner` would have locked out 45% of live usage of this surface. Cross-member track overlap is **0** — but chance alone predicts 0.007 for 16 and 13 draws from a 31,096-row catalog, so it measures **sparse usage, not disjoint taste** and must not be cited as evidence that contention cannot happen. | A3 |
| 2026-09-05 | **OQ7's "decide now, expensive later" framing was found overstated.** Discovery is capped at `search.list` 100/day *and* per-row member confirmation, and a backfill is forbidden by this RFC, so the table reaches hundreds of rows — a UNIQUE change at that size is a non-event. The question was still worth answering, but not under the urgency it claimed. | A3 |
| 2026-09-05 | **OQ8 was found to double-count Step A4.** Two of the three gaps it implied — the provider-keyed `uris.ts` cache and the "ids are immutable" comment ceasing to hold — were already written into A4's scope. Only the discriminator was genuinely open. Recorded because the same over-count would otherwise be inherited by whoever runs A4. | A4 |
| 2026-09-05 | **`FEAT-pocket-buckit` corrected in place** (two errata in `docs/archive/done/rfcs/`): the provider-neutral-membership claim never shipped, "~34% wrong-version" is unsourced and false on this catalog, and the `search.list` quota shape has changed. The archived text is left standing with the correction attached rather than rewritten — the record of what was believed is itself the finding. | A1 |
