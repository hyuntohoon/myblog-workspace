# FEAT-youtube-playback-provider: YouTube as a second playback provider

- **Status**: draft
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
| `GET /api/playback/resolve?…&provider=` | backend | Extend. Optional param, default `spotify` — no existing caller changes. `provider=youtube` reads `track_provider_refs`, 404s when unmapped, which shipped `uris.ts` already treats as a durable miss. | No — rides `GET /api/{proxy+}` |
| `GET /api/music/search/youtube-candidates?track_id=` | **music** | New. **In music on purpose:** the service-boundary invariant forbids a synchronous provider call from a user-facing *backend* endpoint, and `/api/music/search/candidates` is the standing precedent. Putting it in backend would be the violation. | No — rides `ANY /api/music/{proxy+}` |
| `PUT /api/playback/providers/youtube/mapping` | backend | New. `{track_id, video_id}`, verified with `videos.list` before write. | **Yes** — explicit route + Cognito authorizer |
| `DELETE /api/playback/providers/youtube/mapping/{track_id}` | backend | New. "Wrong video" — without it a bad match is permanent and the feature loses trust on its first miss. | **Yes** — explicit route + Cognito authorizer |
| `GET /api/lyrics/{spotify_track_id}` | backend | **Keep.** Still works under YouTube playback; every catalog track has a `spotify_id`. | Unchanged |
| `GET /api/lyrics/tracks/{track_id}` | backend | **Later, staged.** Sequenced after Milestone A, never bundled into it. | Yes, when it lands |

Every change is additive, so contract merge order is **service → workspace →
front**, with `api.gen.ts` regenerated and committed before the front deploy gate
will pass.

## Steps

Steps A0–A5 are Milestone A. B1–B2 do not begin until Phase 0-B returns GO.

### Step A0 — CSP + Google project

**Partially shipped 2026-09-05.** CSP hosts merged in ws #984; Cloud project,
YouTube Data API v3 and API key created; key stored at SSM `/myblog/youtube`.

Remaining:
- Owner applies the workspace infra locally (`terraform apply`). Merging did not
  deploy it.
- After apply: load the site and confirm zero new CSP violations on home, member
  dashboard and a review page, **and that the Spotify SDK still loads and
  plays** — the CSP change must not regress the incumbent.
- Phase 0-A step 3 was **not run**: load the IFrame API on a throwaway page and
  play three known videos (one embeddable, one embedding-disabled, one deleted),
  confirming `onError` yields `101/150` and `100` as documented. It does not gate
  the GO/NO-GO decision, which rests on the search and embeddable counts, but it
  is the only thing that proves the error path this design maps onto
  `'unavailable'`. Run it before A4.

**Verification**: `terraform plan` read in full (done — `0 to add, 1 to change,
0 to destroy`); post-apply `curl -sI` of the live header; real-browser Spotify
regression check.

**Rollback**: revert the function, re-apply. Seconds, no data involved.

---

### Step A1 — Mapping table + resolve + the false comment

`V55__track_provider_refs.sql`; `resolve_uri` gains a `provider` argument; both
schema mirrors diffed in the same change. **Also corrects the
`FEAT-pocket-buckit` D3 claim and the `spotifyPlayback.ts:37` comment** — see
_Current state_. That correction ships here rather than as its own chore because
this is the step whose design the false claim would otherwise misdirect.

Repos: shared_db → backend → workspace. Prereq: A0.

**Verification**:
```
pytest
# control test: omitting `provider` must still return the Spotify URI,
# so the suite is not self-satisfying
```
Migration applied to production and the Neon test branch in the same session;
`/api/playback/resolve` exercised with and without the param.

**Rollback**: revert the code PR. The table is unread by anything else.

---

### Step A2 — Candidate search in music

`GET /api/music/search/youtube-candidates`: `search.list` + `videos.list`
enrichment, ranked by duration proximity to `tracks.duration_sec` — **ranked,
not auto-accepted** (see the duration finding in _Current state_). Explicit
timeout on every outbound request. Quota exhaustion returns a distinct status
the UI can print, and never retries in a loop.

Repos: music → workspace. Prereq: A0.

**Verification**:
```
pytest   # stub models real latency and returns a payload satisfying
         # every reader-side required field; plus a quota-exhausted case
```
Live call for five known tracks; the daily `search.list` counter read in the
Console afterwards.

---

### Step A3 — Confirm-and-save UI

Two backend mutation routes **plus their Terraform routes**; a picker in the
track row listing candidates with thumbnail, channel and duration delta; a
"wrong video" action. Candidates surface the channel, because 3 of 20 measured
top results were unofficial uploads and the member should see that.

Repos: backend → workspace (infra + contract) → front. Prereq: A1, A2.

**Verification**:
```
pytest
pnpm lint && pnpm exec astro check && pnpm test
```
Each new test mutated to confirm it fails when its assertion is removed.
New protected routes matched against `infra/apigateway.tf` — a missing route is
a 404 at the edge. Real-browser: map a track, reload, confirm persistence, unmap.

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
place where shipped reasoning genuinely does not carry over.

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

1. **Does the owner want Milestone A started at all?** — Phase 0-A returned GO,
   which removes the *technical* objection, not the *priority* one. Blocks A1.
2. **Phase 0-A step 3 (IFrame error codes) was not run.** — Blocks A4, not A1.
   It is the only evidence for the `100`/`101/150` → `'unavailable'` mapping the
   adapter depends on.
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

## Decisions log

| Date | Decision | Step |
|------|----------|------|
| 2026-09-05 | Phase 0-A run. Correct-version **20/20**, embeddable **20/20**, controls pass → **GO**. The "~34% wrong-version" figure carried through three RFCs does not hold on this catalog. | A0 |
| 2026-09-05 | CSP hosts merged (ws #984) without waiting for the numbers, because a closed CSP makes a player spike produce a wrong result rather than a weak one. Not applied — owner applies workspace infra locally. | A0 |
| 2026-09-05 | Google Cloud project + YouTube Data API v3 key created by the owner; stored SSM SecureString `/myblog/youtube`. Console quota figures not read — the documented defaults are assumed and must be confirmed before A2. | A0 |
