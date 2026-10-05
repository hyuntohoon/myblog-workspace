# OPS-project-stabilization: reconcile progress, repair lyrics reliability, validate real use

- **Status**: in-progress (Step 2A) — owner approved in-session 2026-09-30; Step 1 delivered; Step 2A's rollback part deployed, real-device gate open
- **Owner**: site owner
- **Created**: 2026-09-28 (rebuilt on `main` 2026-09-30 after the Step 5 post-delivery audit, ws #1013)
- **Plan row**: `docs/plan.md` → OPS-project-stabilization
- **Priority**: first planned priority; home-entry and next-track lyrics are the first runtime fix.
- **Authorization**: accepted by the owner in-session on 2026-09-30, which authorized Step 1.
  Promoted to `in-progress` by the owner in-session on 2026-09-30, authorizing Step 2A. Each later
  step is still a separate session/PR; recurring-spend activation (Step 2C) remains an explicit
  owner decision.

---

## Goal

Reconcile progress documentation, repair the known lyrics reliability and operational gaps, then
inspect real user journeys before selecting further product work.

Homepage playback discovery and automatic next-track lyrics must satisfy the owner's existing
requirements. A completed deployment must not stand in for a working user journey.

## Non-goals

- New playback providers, YouTube Milestone B, AI authoring, recommendations or a Buckit redesign.
- Broad architecture/security rewrites or dependency upgrades.
- Catalog-wide translation runs or blanket replay of failed work.
- Publishing reviews, modifying personal collections or reconnecting accounts merely to create test
  evidence.
- Automatically promoting existing RFC lifecycle states.

## Current state

### Evidence baseline

The analysis read these revisions on 2026-09-28:

| Repository | Revision |
|---|---|
| `myblog-workspace` | `bd044c4d75df96ddf710d8cac5d63c2ebf48ed24` |
| `myblog_front` | `757b37b506f97db54c2ef5c791128a077b1449c7` |
| `myblog_backend` | `0e2014af` |
| `myblog_music` | `2c7d791f` |
| `myblog_worker` | `e29b6693` |

`myblog_shared_db` was **not** inspected; direct access was unavailable. Nothing below is a claim
about it.

Re-checked 2026-09-29 while writing this RFC: workspace, frontend and worker `main` were still at the
revisions above; backend and music were not re-read. That re-check corrected one finding (Worker
transaction boundary, below). These are dated source findings, not proof of deployed behavior —
recheck the current source before carrying any of them into an implementation step.

**Rebuilt 2026-09-30** on workspace `9318958`. Between the first draft and this rebuild, workspace
#1008–#1013 recorded Step 5's delivery and then withdrew its "production-verified" claim in a
read-only *Post-delivery audit (2026-09-30)* in `FEAT-lyrics-listening-experience.md`. That audit is
this RFC's evidence baseline for Steps 2C and 2D; its figures are not restated here beyond what a step
needs. Service `main` at the rebuild: frontend `757b37b`, worker `e29b669`, backend `0e2014a`, music
`2c7d791`, shared_db `98875c8`. Frontend and worker are the revisions findings A–C and finding 4 were
read at, so those findings stand unchanged. Worker `4d4c181` was re-compared against `e29b669` on
2026-09-30: the three non-test files show no diff and the real-DB test is still absent (finding 4
confirmed). **That last clause was wrong** — the test was looked for at `tests/`, and it lives at
`tests/integration/`; corrected 2026-10-01 under finding 4 and Step 2B.

### Evidence classes

Every finding below is labelled with one of:

1. **Owner-reported** — symptom observed by the owner in the deployed site.
2. **Source-confirmed** — behavior read from the cited source revision.
3. **Isolated reproduction** — the cited logic blocks executed outside the app.
4. **Unverified** — authenticated production behavior nobody has observed or captured.

### Owner requirements and reports

The owner's requirements, repeated several times:

1. Arriving on the homepage with music already playing discovers the current song and makes its
   lyrics directly accessible.
2. No profile → overview → playback bar → lyrics path, and no queue visit, is required.
3. While the lyrics screen stays open, it switches to the next song's lyrics when playback moves on.
4. It does not keep refreshing the previous song, and does not require closing and reopening the
   viewer.

This is not a new requirement. `FEAT-lyrics-listening-experience` D6 already says *"Site/home entry
should discover ongoing playback and expose lyrics immediately"* and *"Do not require a dashboard
visit or opening the queue first."* It is incomplete acceptance and reliability work on an existing
requirement.

**Owner-reported (2026-09-28):**

- Homepage direct lyrics access still does not work as requested.
- Visiting the profile makes the lyrics entry available, but updates are slow.
- With lyrics open when the next song starts, the viewer refreshes the old song instead of showing
  the new one.

The failed request in the owner's browser was **not captured** (Unverified). The source findings
below explain the symptoms; they do not prove which path fired for the owner.

### A. Homepage discovery and delayed updates (Source-confirmed)

1. `src/components/member/playback/GlobalPlaybackBar.tsx` — the bar renders only when
   `currentItemId != null || external != null`. With no discovered track, the lyrics entry
   disappears together with the bar.
2. `src/lib/playback/lifecycle.ts` — reads happen on `astro:page-load`, `visibilitychange`,
   `pageshow` and `focus`. Nothing observes external Spotify changes between those events, and an
   initial failure has no bounded autonomous recovery while the user stays on the page.
3. `src/lib/playback/session.ts` — `adoptLive()` can discover external playback without
   establishing the state `scheduleBoundaryCheck()` requires (`current.isOwner`,
   `current.rung === 'remote'`, `current.playing`). Opening home during externally initiated
   playback therefore does not necessarily arm next-song confirmation. An external mid-track skip is
   a separate case: waiting for the old song's estimated end cannot detect it promptly.
4. `syncFromLive()` passes `Promise.all([prefetchUris(...), resolveCapability()])` into
   `adoptLive()`, so current-song display can wait for queue URI prefetch and capability resolution
   that it does not need.
5. `src/components/member/playback/playbackEntryActions.ts` — `openPlaybackLyrics` uses stored track
   identity rather than a fresh provider observation, so stale playback state can open stale lyrics.
6. `src/components/member/NowPlaying.tsx` — the profile entry performs another live read; its
   fallback is the worker-written snapshot, and an unsuccessful live read keeps old data. This does
   **not** mean playback always lags by an hour: a successful direct Spotify read replaces the
   fallback.

### B. Open viewer reverts from the next song to the previous one

`src/components/member/lyrics/LyricsViewer.tsx` (Source-confirmed):

1. The viewer and the shared `playbackSession` both identify song A.
2. The viewer's `refresh()` reads Spotify directly and receives song B.
3. `refresh()` sets the viewer's local `trackId` to B but does not publish that observation into
   `playbackSession`.
4. The session-adoption effect depends on local `trackId`, so it re-runs.
5. That effect trusts `playbackSession.currentSpotifyTrackId()`, still A ("session-confirmed
   identity beats a viewer-local guess").
6. It sets the viewer back to A.

**Isolated reproduction** — the refresh and adoption logic blocks were executed in isolation:

| Provider | Shared session identity | Viewer |
|---|---|---|
| B | A (stale) | A → B → **A** |
| B | null | A → B |
| B | B | A → B |

This is a deterministic source-logic reproduction. It is **not** a mounted React test, an
authenticated browser reproduction, or live Spotify verification. It does not show that natural
completion, an external-app skip and the in-viewer next button all reach this path — those remain
separate acceptance cases in Step 2A.

### C. Additional automatic-transition gaps (Source-confirmed)

1. The viewer's end detection is coupled to the timed lyric-line scheduler.
2. That scheduler exits on `!trackable || suspended || !playing || n === 0`.
3. Plain, missing or failed lyrics, or manual browsing, can therefore disable this end-detection
   path.
4. The end read uses a `duration + 1500 ms` threshold (`END_GRACE_MS`) and a one-shot guard.
5. An unavailable, idle or still-old-track response near the end does not guarantee another
   confirming read.

### D. Why the earlier Step 1 completion does not close these defects

`FEAT-lyrics-listening-experience` Step 1 recorded completion, but:

- local verification used deterministic fixtures and recovery on a *later* return;
- the live-media record primarily validated lyrics after a *site-initiated* queue play;
- a passing deployment, or clicking lyrics after local playback, does not establish the requested
  cold-home / external-playback journey.

Speculative cache-clearing or relogin advice is not a substitute for this diagnosis.

### E. Playback-polling rule attribution (Source-confirmed, corrected 2026-09-29)

The frontend's no-polling rule is cited in code comments as **D28** (`LyricsViewer.tsx`,
`NowPlaying.tsx`, `playback.api.ts`, `queue.api.ts`: "never polled (D28)"). The only D28 in the
workspace documents is `FEAT-member-dashboard` D28 (archived), which records the **privacy posture**
of the listening GETs and the removal of `progress_ms`/`duration_ms` from `now-playing`; it does
not itself state a polling ban. Step 2A must locate the actual owning record of the no-polling rule
(or record that it exists only as a code-level convention) before reconciling it — and must not
introduce an interval without that reconciliation.

**Located 2026-10-01 (home-discovery part of Step 2A).** No single record owns it. "D28 — no
polling" is a convention carried forward by every playback RFC since `FEAT-member-player`
(`FEAT-playback-bucket-player` lists it as "D28 — no polling, ever | member-player | Retained";
`ARCH-global-playback-experience` "carried from `FEAT-member-player`"). The closest it has to an
owning statement is:

- the **permitted-trigger list** in `ARCH-playback-authority-convergence` (non-goals): *SDK push,
  `MYBLOG_PLAYBACK_CHANGED`, `visibilitychange`, a natural track boundary, a bounded confirmation
  burst, an explicit refresh* — "no new polling loop anywhere";
- the **owner's own statement** in `FEAT-lyrics-sync-precision` (2026-08-01): periodic re-sync is
  wrong, only *events* invalidate an anchor; adaptive polling was dropped.

**Reconciliation for the discovery retry.** Front #448 adds one trigger that is on neither list:
after a read that **failed** for a reason asking again can fix (network, timeout, 5xx, token-route
error — not 401/403/429), while nothing is known to be playing and the page is visible, the session
reads again at +2 s, +5 s and +15 s, then stops and says so. It is a bounded burst keyed to a failed
read, as the confirmation bursts are keyed to a command or a boundary: it never starts from a
successful answer (`idle` included), it is finite (≤ 3 extra reads per lifecycle event), and the
next read is again 1:1 with a lifecycle event or a press. It is **not** an observation mechanism
for playback that was read successfully — an external skip remains undetected until the next event,
and that question stays OQ2.

**Owning record of the exception (2026-10-01, OQ2 resolved).** Since no single record owned the
no-polling rule, this paragraph owns its one exception. The rule itself is unchanged everywhere
else: no surface polls playback, and the permitted-trigger list above still governs.

*The exception.* While the lyrics viewer is open, `playbackSession` reads `GET /v1/me/player` every
**10 s** (`EXTERNAL_WATCH_INTERVAL_MS`). A timer exists only while all of these hold: a surface
asked for the watch (today only the open lyrics viewer); the page is visible; this tab may adopt
(the owner tab, or any tab while nobody owns playback); a track is known; the audio is not this
tab's in-page SDK device (which pushes); the provider is Spotify.

*Why it does not contradict the owner's 2026-08-01 statement.* That decision was about the sync
**anchor** — "싱크는 한번 맞으면 안 바뀌는게 맞아", drift ≈ 10 ms per track, so only events invalidate
it. It still holds: a read that agrees with the session changes nothing (no patch, no re-anchor, no
re-render). The watch exists because some events never reach a visible tab — a skip, seek or pause
made in another Spotify client — and it re-anchors only when it observes one: another track, a
play/pause flip, or a position more than 2 s from where the clock says it should be. The same RFC
recorded exactly this gap as "Residual gap, accepted … Widening this would require polling";
the owner has now widened it.

*Bounds.* A paused track is watched for 5 minutes, then left until the next event (owner confirmed
in-session: without it a phone pause is seen and the phone resume never is). 401/403/429, or three
failures in a row, stop it until some other read gets an answer. One `idle` read is not adopted; it
goes to the boundary burst. Cost: ≈ 24 reads per 4-minute song per open, visible viewer, against 1
before.

*Not covered, by decision.* A mirror tab; a page with no viewer open (the bar alone); playback
that starts from nothing while the session is idle. Adding a second watcher surface, or changing
the interval, is a change to this record.

### Other stabilization findings

1. **Progress documents disagree — partly resolved 2026-09-30.** Workspace #1013 corrected the
   `FEAT-lyrics-listening-experience` header, execution-state line and Open questions table (OQ2–4
   now read *resolved 2026-09-13*), and the plan row now says Steps 1–4 complete, Step 5 deployed
   but not complete. Still stale: the `docs/rfcs/README.md` lyrics row ("Steps 4–5 automatic
   producers remain unimplemented"), which this PR only qualifies, and the Step 1 completion claim,
   which the owner's 2026-09-28 report reopens (Step 2A).
2. **Security follow-up tracking.** The lockfile work was completed as `SEC-system-hardening` Step 5
   follow-up 3 (2026-08-29). Follow-ups 4 (per-service shared_db pin invariants) and 5 (frontend
   Playwright golden E2E) have no completion evidence and are absent from the plan row's
   "What is still open" summary and from the RFC index.
3. **Recurring lyrics catalog refresh.** `worker/handler.py` nudges enumeration only when
   `due_count(...) > 0`. `due_count` covers incomplete registrations; `_REOPEN_STALE` runs inside the
   enumeration job the nudge would need to start. All-complete but stale registrations can
   therefore never restart. Worker #107 and the lyrics plan row record the unresolved cycle.
   Re-read 2026-09-30: `lyrics_artist_discographies` 34/34 `complete`, `last_complete_at`
   2026-09-19 03:58–04:00Z — unchanged since the 2026-09-20 reading and the 2026-09-30 audit.
4. **Worker transaction boundary — corrected 2026-09-29.** The handoff and the lyrics plan row say
   worker `4d4c1819471767301b0221b4514f917bbc1adc99` (*close collector transactions before provider
   waits*) was not on `main`. **The service change is on `main`**: the squash merge of worker #104
   (`4ece539`, 2026-09-09) contains the same `self.session.commit()` calls in
   `LyricsIncrementalService` and `LyricsReassessmentService`, and `git diff 4d4c181 e29b669` over
   both service files is empty. What is **not** on `main` is that commit's real-DB regression test,
   `tests/test_lyrics_transaction_boundary_db.py`. Deployment of the fix to the running Lambda was
   not checked (Unverified).
   **Corrected again 2026-10-01 (Step 2B): the test is on `main` too.** It was searched for at the
   path above; the file is `tests/integration/test_lyrics_transaction_boundary_db.py`, it arrived in
   the same #104 squash, and `git diff 4d4c181 e29b669` over it is empty. Nothing from `4d4c181`
   was ever missing from `main`. Deployment is now verified — see Step 2B's execution record.
5. **Residual counts — superseded by the 2026-09-30 audit.** The first draft carried one
   `album_not_in_catalog` job and 43 `failed` translations. The audit (items 1, 4, 5) and a read-only
   re-read on 2026-09-30 show a different picture:
   - **Back-catalogue ingestion gap.** 687 jobs wait on `album_not_in_catalog`: 686 from the `follow`
     origin (28 artists, all created 09-19) and the 1 `saved` job the first draft counted. Nothing
     sends an enumerated album missing from `albums` to album sync, so a follow translates only the
     ~35% of a discography the catalog already held. This is not a residual failure; it is a Step 5
     coverage gap, and fixing it is a spend decision (one Spotify catalog read per album, plus the
     translations that follow).
   - **Translation outage 09-27 → 09-30** from an expired `claude` CLI login.
     `subscription_guard.is_throttle_error` classifies a blank `claude exit 1:` as a throttle, so
     every claim logged "subscription throttled" and cooled down for 15 minutes. It recovered after
     the owner's `/login`. No spend is needed to fix the classification.
   - **Model copyright refusals.** `track_lyrics_translations` `failed` is 54 (was 43). Work rows
     re-claimed after `engine_validation: no JSON array in output:` refusals: 14 at the audit, 5
     still `running` on 2026-09-30. The refusal rate is unmeasured.
     **Corrected 2026-10-01 (Step 2C read):** the `failed` rows are not refusals. Of 52, 51 are
     `korean_source` (the legacy path's way of recording a Korean original) and 1 is a malformed
     JSON reply. The refusals live in `lyrics_translation_work`: 23 rows in `retryable_error`,
     every one at 9 attempts with an `engine_validation: no JSON array in output:` refusal text,
     against 1,433 `done` — 1.6% of work rows, still being retried.
   - **Step 5 verification list unmet.** The post-deploy member/follow/back-catalogue smoke was never
     run.
   - **`infra/lambda.tf` kill switches declared but unapplied.** Until a human `terraform apply`, the
     console value of `LYRICS_FOLLOW_DEMAND_ENABLED` is the only producer lever.
   The refresh estimate (34 registrations, ~42 provider pages per day) dates from 2026-09-20 and is
   not an approved budget.
6. **Product evidence.** The 2026-09-03 record reports 0 published reviews and 5 drafts. Long-form
   bucket notes existed for 7 albums, averaging 436 characters. Lack of long-form writing demand
   cannot be inferred from a 60-character rating-comment field or from zero published reviews alone.

Historical delivery records stay as they are; blanket completion claims about the home-entry and
next-track journeys are qualified, not deleted.

## Target state

- `plan.md`, the RFC index, RFC headers, execution summaries and decision tables agree, and each
  earlier discrepancy has a dated resolution or an explicit unknown.
- A connected member or the owner who opens the homepage while Spotify is already playing sees the
  current song and a direct lyrics entry, with bounded recovery from an initial failure.
- An open lyrics viewer moves to the next song and stays there, whatever triggered the change and
  whether or not the new song has timed lyrics.
- Worker collector transactions are proven closed across provider waits by a regression test that
  fails on the old shape.
- Stale-but-complete discography registrations can be refreshed, at a measured and owner-approved
  cadence, or the refresh is explicitly recorded as deferred.
- Residual failures are classified, and the next product investment is chosen from a dated
  user-journey report.

## Ownership

This RFC owns sequencing, priorities and cross-cutting evidence.

- `FEAT-lyrics-listening-experience` keeps its data/removal contracts and playback-policy decisions.
- `SEC-system-hardening` keeps its security delivery work.
- `FEAT-album-review-authoring` and `FEAT-youtube-playback-provider` keep their existing product
  gates.

Do not create duplicate implementations or silently transfer decisions between RFCs. Existing
P0/security incidents take precedence over every step here.

## Steps

**Execution order:** Step 1 → Step 2A → Step 2B → Step 2C → Step 2D → Step 3.

Each implementation leg is a separate verified session/PR under the current workspace rules. A
deferred recurring-spend decision must not block unrelated documentation or frontend repair.

### Step 1 — Reconcile progress documents

**Scope:**

- Recheck current repository heads and delivery evidence.
- Reconcile `plan.md`, the RFC index, execution summaries and decision tables.
- Correct the remaining lyrics stage summaries. The RFC header, execution-state line and OQ2–4 were
  done by workspace #1013; the `docs/rfcs/README.md` lyrics row is left.
- Qualify the previous lyrics Step 1 completion claim with the reopened home/next-track defects.
- Remove or qualify completed lockfile work; keep genuine residual dependency issues (for example,
  `myblog-shared-db` built on the runner from an unpinned build backend).
- Restore the missing security follow-ups 4 and 5 with their original ownership and order.
- Correct the multi-user Phase 4 and URL-migration descriptions without changing launch gates.
- Correct the stale "worker `4d4c181` sits unmerged" note (finding 4). This PR adds a dated
  correction beside it; Step 1 folds that correction into the note.
- Preserve dated history; put the current answer before superseded descriptions.
- Do not promote any RFC lifecycle Status.

**Deliverable:** a dated stabilization-progress report and consistent plan/RFC/index summaries.

**Verification:**

```
python3 -m unittest discover -s scripts/tests -p 'test_workspace_invariants.py'
python3 scripts/check_workspace_invariants.py \
  --backend-openapi <current backend openapi.json> \
  --music-openapi <current music openapi.json>
git diff --check
```

Plus applicable workspace CI, and a manual check of statuses, links, decisions, ownership and
remaining work.

**Exit:** each discrepancy has a dated resolution or an explicit unknown.

**Rollback:** revert the documentation change; historical evidence is retained.

#### Step 1 execution record — 2026-09-30

Delivered as one workspace PR after owner acceptance. Every item below was re-read on 2026-09-30,
not carried from the 2026-09-28 analysis.

**Repository heads** (`origin/main`, all equal to the handoff baseline): workspace `9ba84f6`,
backend `0e2014a`, frontend `757b37b`, music `2c7d791`, worker `e29b669`, shared_db `98875c8`.
`myblog_shared_db` was read this time (the 2026-09-28 baseline had not inspected it); the only
finding used below is the absence of any `ApiEngine` caller outside it.

| # | Discrepancy | Resolution (2026-09-30) |
|---|---|---|
| 1 | `docs/rfcs/README.md` lyrics row still led with "Steps 4–5 automatic producers remain unimplemented", qualified only by an appended note. | Row rewritten current-answer-first: Steps 1–4 production-verified, Step 5 deployed but not complete, home-entry/next-track reopened. The superseded summary is no longer restated; `git log` holds it. |
| 2 | Lyrics RFC Step 1 *Current state* said the retained observations "neither reopens Step 1". | Qualified: the owner's 2026-09-28 report reopens the home-entry and next-track journeys; the historical delivery record is kept unchanged. |
| 3 | `plan.md` lyrics row carried "worker `4d4c181` sits unmerged … Decide whether to PR it" beside a dated correction. | Folded into one current note: the service change is on `main` via #104 (`4ece539`); only the real-DB test is missing → Step 2B. No owner decision is pending on it. |
| 4 | `SEC-system-hardening` follow-ups 4 (per-service shared_db pin invariants) and 5 (frontend Playwright golden E2E) were in the RFC but absent from the plan row's open list and the RFC index. | Restored to both, in their original order and under `SEC-system-hardening` ownership; neither has started. Item 5 still waits for item 4. |
| 5 | `CHORE-dep-reproducibility` still asked to "add lockfiles" and replace a SHA dependency with a tag. | Qualified: lockfiles shipped as SEC Step 5 follow-up 3 (2026-08-29; `requirements.lock` present on backend, music and worker `main`), and SHA pins are now the convention (shared_db tags were abandoned). Residuals kept: the unpinned build backend for `myblog-shared-db`, and wildcard `requirements.txt` inputs that still mislead CVE search. |
| 6 | Multi-user Phase 4 read as shipped. | Kept narrow in both places: owner-central `LLMEngine` scaffolding + V43 metering exist in shared_db; `git grep` over backend, music and worker `main` finds **no `ApiEngine` caller**. The BYOK half remains behind G2. No gate changed. |
| 7 | Multi-user canonical member URL decision was "necessity-gated while prod `/api/members` is empty — 0 duplicate URLs today". | **That premise is false.** Prod `GET /api/members` returns two members (the owner, 37 ratings; the smoke user, 1); `album_reviews` holds 39 rows from 2 users (2026-08-10 → 08-19). The sitemap lists both static `/members/<handle>/` pages, which canonicalize to themselves; the runtime `/members/?u=<handle>` view canonicalizes to `/members/`. `/profile` redirects to `/members/?me` (front #280). The decision stays deferred and owner-only — only the stated reason is corrected. |

**Unknowns left explicit:** whether the running worker Lambda carries `4ece539` (Step 2B —
resolved 2026-10-01: it does); the
copyright-refusal rate (Step 2D); the actual owning record of the no-polling rule (finding E, Step 2A).

**Verification:** see the PR body; statuses, links and ownership were checked by hand against the
files above.

---

### Step 2A — Home entry and automatic next-track lyrics

Highest runtime priority. Frontend first.

**Requirements:**

- Discover already-running external playback on initial home entry and on client navigation.
- Expose direct lyrics without visiting the profile or queue, or starting playback from the site.
- Provide usable loading/failure/retry states and bounded recovery from an initial failure.
- Do not fabricate current playback from recent history.
- Do not play, pause, transfer playback or take over a device merely to discover its state.
- Do not delay current-song display on unrelated queue URI resolution.
- Give passive external playback a reliable observation lifecycle.
- Converge fresh playback observations through shared session state.
- Prevent an older shared A snapshot from overwriting a fresh B observation.
- Fence stale responses by account, provider and newer playback intent.
- Separate song identity/end detection from timed lyric-line highlighting.
- Plain/missing/loading/failed lyrics, scrolling and the queue view must not disable song detection.
- Preserve truthful pause/idle states and within-track manual browsing.
- Use bounded confirmation when the natural boundary first returns the previous track or a transient
  result.
- Handle genuine idle, hidden state and rate limits without unbounded retries.

**Policy:** define a measurable external-skip detection latency and the mechanism that supports it.
The frontend's no-polling rule (cited as D28; see finding E) forbids regular playback polling;
reconcile any proposed change in the owning record before introducing an interval. *(Resolved
2026-10-01: target — the open viewer is on the new song within one 10 s interval plus the read;
mechanism and its record — finding E.)* Do not promise
immediate external detection from lifecycle events alone. Playback observation is separate from the
worker catalog refresh and its spend gate.

**Required acceptance cases:**

1. Spotify already playing → open home → current song and direct lyrics appear. Test a connected
   member and the owner, on desktop and mobile.
2. Initial read fails → provider recovers → same-page bounded recovery.
3. A ends; provider reports B while the shared session still says A. The **same mounted** viewer
   adopts B and keeps B. Assert final identity, title and rendered lyrics — not merely that B was
   requested.
4. The boundary first returns old A, unavailable, or transitional idle, then B. Verify bounded
   recovery, and termination when playback genuinely stopped.
5. External skip, the viewer's next button, and rapid A → B → C, each tested separately.
6. Delayed and reordered responses: the latest confirmed song wins.
7. Plain/missing/failed lyrics, manual scrolling and the queue view. A must not stay presented as
   current merely because B has no lyrics.
8. Pause/resume, repeat-one, background return, multiple tabs, account changes and provider changes.
   YouTube behavior and account isolation are preserved.

**Verification:**

- A regression test that fails on the current rollback behavior, using the same mounted component —
  no remount to make it pass.
- Frontend `pnpm lint`, `pnpm exec astro check`, `pnpm test`, and the required `check`.
- Real-browser clickthrough.
- After deployment: authenticated real-Spotify evidence with the deployed revision, independently
  observed track identity, transition timing and request counts.

A passing build/deployment, or a lyrics click after site-initiated playback, is not sufficient.
Missing production access remains an unverified gate, not a pass.

**Exit:** the acceptance cases pass and `FEAT-lyrics-listening-experience` records the corrected
verification evidence.

**Rollback:** revert this frontend change independently; keep the defect record. No production data
migration is planned.


#### Step 2A execution record — 2026-09-30 (rollback part)

**Scope delivered:** findings B and C — acceptance cases 3, 4, 6 and 7. Front #447, merged as
`048fc31`. **Not delivered:** home discovery (finding A, case 1–2); external-skip detection latency
(case 5 — blocked on OQ2 / finding E); case 8 (pause/repeat/background/multi-tab/account/provider)
beyond the paths the regression suite already touches.

**What changed:**

- **B.** The viewer's Spotify read goes through the new `playbackSession.observeLive()` →
  `adoptLive()`, so an observation of B becomes the session's B under the existing fences — the
  same single request in the owner tab. `observeLive()` does not read while the session is
  settling a command or a boundary. A mirror tab reads for itself and forwards a sync to the owner
  only when its answer disagrees. The adoption effect refuses a session identity whose anchor
  predates the viewer's own read (latest confirmed wins); an anchor-less identity is adopted as
  before.
- **C.** End detection runs on its own song clock, independent of the lyric scheduler, as a bounded
  burst (4 × 500 ms). **The session's `confirmCompletion` no longer settles on `idle`:** a
  transitional idle between tracks used to stop it while the next song was about to start. The
  viewer and session now share one settle rule; the viewer defers to a running session burst and
  follows its outcome, including a genuine stop.

**Verification (Verified locally / Deployed; real-device gate open):**

- Front `pnpm lint`, `astro check`, `pnpm test` (111 files, 1252 passed, 0 skipped) and required
  `check`, all on the merged head. A mounted-component regression suite (18 tests, no remount)
  fails 12/13 of its original cases against the pre-fix component, including the isolated row
  "provider B, session A". 12 mutants over the fix were each killed.
- Independent `reviewer` pass found one blocker (the session burst settling on transitional idle
  stranded a deferring viewer) and three should-fixes. All four were fixed before merge, each with a
  test that fails without the fix.
- Real-browser clickthrough (stub backend, in-page Spotify stub with a lag window at each boundary):
  - **Control, `757b37b`:** the one end read landed in the lag window, got A, and nothing asked
    again. Viewer and Global Player stayed on A while B played.
  - **Fix:** reads `26.50:A · 27.03:A · 27.55:A · 28.08:B`; viewer and bar on B at 28.3 s.
    Plain-lyrics B's end detected. Genuine stop: 4 idle reads, then none.
- Deploy run `36660035883` success. Production smoke 30/0. New-bundle marker (`"superseded"`,
  `"mirror"`: 0 in source at `757b37b`, present in the deployed `session` and `PlaybackPanel`
  chunks). Evidence comment on front #447.

**Open gate (Unverified):** authenticated real-Spotify evidence on the deployed revision —
observed identity, transition timing and request counts on a real device, for a natural end, an
external-app skip, the viewer's ⏭ and a genuine stop. Needs the owner's account and device. Step
2A's Exit (`FEAT-lyrics-listening-experience` records the corrected evidence) waits on it and on
the undelivered parts above.

#### Step 2A execution record — 2026-10-01 (home-discovery part)

**Scope:** finding A — acceptance cases 1 and 2 (A1, A2, A3, A4, A5). Front #448. **Still not
delivered:** external-skip detection latency (case 5, OQ2); case 8 beyond what the suites touch;
finding A6 (the profile `NowPlaying` fallback) — unchanged.

**What changed:**

- **A2 — bounded recovery.** `{state:'unavailable'}` now carries `retryable` for failures asking
  again can fix. After such a failure with nothing known, the session retries at 2/5/15 s (visible
  page, reader tab only), stops at the first answer of any kind, and when the budget is spent sets
  `discoveryFailed`; the Global Player then shows a "다시 시도" pill instead of rendering nothing.
  A member without connected Spotify never sees it (not retryable). Rationale: finding E.
- **A3 — boundary for adopted playback.** The end-of-track read used to require `isOwner &&
  rung === 'remote'`, both set only by a play from this site, so playback adopted from a phone at
  home entry (no owner, `rung: null`) was never confirmed at its end. Now: any tab allowed to adopt
  (owner, or any tab while nobody owns playback) arms it, unless the adopted device is this tab's
  in-page SDK device; ownerless tabs skip it while hidden.
- **A4 — no queue wait.** Adoption no longer waits for queue URI prefetch and capability. A song
  first shown as external is re-matched to its queue row when the cache warms, without a second
  read. The anchored row's own URI is still warmed before a read (T2 completion delete).
- **A5 — fresh read at the press.** 가사 reads what is playing at the press (through the session,
  so the Global Player moves too) and opens that; it falls back to the stored identity only when the
  read fails or the session is settling a command or boundary.

**Verification (Verified locally / Deployed; real-device gate open):**

- Front `pnpm lint`, `astro check`, `pnpm test` (111 files, 1294 passed, 0 skipped) on HEAD
  `8d09494`; 42 new tests. Mutation: 27 of 29 mutants over the new logic killed; the two survivors
  are equivalent (a redundant guard re-checked when the timer fires; the re-match anchor once the
  anchored URI is pre-warmed).
- Independent `reviewer`, three passes. Pass 1: no blockers, six should-fixes, all fixed (cold-cache
  completion delete and boundary in a tab promoted from mirror; in-page decided by the adopted
  device, not the sticky `rung`; 401/429 not retried; the re-match no longer holds the sync or the
  가사 press; tests; this reconciliation). Pass 2 caught that the cold-cache fix was a no-op in
  production — `prefetchUris([id])` skips an id the queue-wide prefetch already has in flight, and
  the test stub did not model the skip, so the tests were falsely green. Fixed by joining the
  in-flight `resolveUri` (capped at 1 s) and a stub that models the skip. Pass 3: pass.
- Real-browser clickthrough (stub backend, in-page Spotify stub with a 3 s boundary lag, origin/main
  `048fc31` as control):
  - **A1/A3, no viewer open.** Control: bar on A from the first read, then **no read at all**; bar
    still on A at 25 s while B had played since 13 s. HEAD: reads `1.38:A · 11.50:A · 12.01:A ·
    12.52:A · 13.03:B`, bar on B at 14 s; next boundary `36.50–38.03` → C; nothing in between.
  - **A2.** Reads fail until 4 s. Control: one failed read, no bar, no lyrics entry at 15 s. HEAD:
    `0.27:FAIL · 2.27:FAIL · 7.27:A`, bar at 8.5 s, no further reads.
  - **Budget.** All reads fail: `0.23 · 2.24 · 7.24 · 22.24`, pill at 23.5 s, no read to 35 s;
    pill press after recovery: one read, song shown, pill gone; 가사 then spends one fresh read
    (A5) and opens the viewer on that song.
  - **Mobile 390/360 px:** pill sits one row above Pocket's entry (360 px: pill 682–718, Pocket
    726–762; no horizontal scroll); recovery → bar → 가사 → viewer with the song's lyrics.
  - Not isolable in this harness: A5 on the control (CDP's own focus event fires a lifecycle read).
    Covered by unit tests and mutants instead.
- Found, not fixed (pre-existing, outside 2A): at 360 px the lyrics viewer's ✕ extends to x=370 on
  origin/main as well.

- Deployed: merged as front `9dd3546`, deploy run `36806429741` success. New-bundle markers (0 in
  source at `048fc31`) present in production: the pill text and class in `PocketBuckit.*.js/.css`,
  the retry delays `2e3,5e3,15e3` in `session.*.js` (56 assets crawled to a fixed point).
  Production smoke 30/0. Evidence comment on front #448.

**Open gate (Unverified):** authenticated real-Spotify evidence on the deployed revision, for a
connected member and the owner, desktop and mobile: home entry during phone playback, an initial
failure, and the natural end of an adopted song. Same owner-device gate as the rollback part.

#### Step 2A execution record — 2026-10-01 (external-skip part, OQ2)

**Scope:** acceptance case 5, external skip — the part blocked on OQ2. Front #449, merged as
`c7994a3`. The viewer's ⏭ and rapid A → B → C were delivered with the rollback part. **Still not
delivered:** case 8 beyond what the suites touch; finding A6.

**Decision (owner, in-session):** offered a conditional periodic read (A), a read on user input
inside the viewer (B), and no change with the limit recorded (C). Owner chose **A at 10 s**. During
implementation the "only while playing" condition was widened to "a paused track for 5 minutes";
the owner confirmed that before merge. Record: finding E.

**What changed:** `playbackSession.watchExternalPlayback()` — a ref-counted, quiet watch owned by
the session; the viewer asks for it while bound to live playback and releases it on close, and
spends no read of its own. A detected change is adopted through the ordinary `adoptLive()` with the
read that saw it, under the existing fences.

**Verification (Verified locally / Deployed; real-device gate open):**

- Front `pnpm lint`, `astro check`, `pnpm test` (111 files, 1321 passed, 0 skipped; 27 new) and the
  required `check` on the PR head.
- Mutation: 29 mutants over the new logic, 28 killed. The first pass left 10 survivors — the tests
  were tightened for 9 and one redundant guard was removed. The remaining survivor is equivalent
  (the YouTube guard: a YouTube session is `rung: 'in-page'` and already excluded).
- Real-browser clickthrough (stub backend; in-page Spotify stub mutated at runtime; 240 s songs so
  no boundary interferes; origin/main `9dd3546` as control). Home → 가사 → the "phone" skips to B:
  - **Control:** reads `1.5:A 6.3:A`, then none; viewer and bar on Song A 30 s after the skip.
  - **Fix:** skip at 4.4 s → reads `12.7:B 22.7:B 32.7:B`; viewer and bar on B at the first of
    them (8.3 s after the skip), on the line B's own position implies.
  - Phone seek → re-anchored at the next read. Phone pause → shown paused, line held across two
    further reads. Phone resume → following again. 429 → one failed read, then none for 25 s;
    manual ↻ answered → the cadence resumed. Viewer closed → 0 reads in 22 s.
  - Not exercised in the browser: a hidden tab (unit-tested).
- No independent `reviewer` pass: no contract, infra or auth touch, so not mandatory; skipped
  deliberately. The two earlier parts each had one, and each found defects — weigh this record
  accordingly.
- Deployed: deploy run `36814741411` success. `watchExternalPlayback` (0 in source at `9dd3546`)
  present in production `session.*.js` and `PlaybackPanel.*.js` (54 assets crawled to a fixed
  point). Production smoke 30/0. Evidence comment on front #449.

**Open gate (Unverified):** real-Spotify evidence on a real device — an external-app skip, seek,
pause and resume with the viewer open: identity, latency against the 10 s target, and request
count. Same owner-device gate as the two parts above. Two things only a real device can show: how
far Spotify's reported `progress_ms` strays from the session's clock on an untouched song (if it
exceeds 2 s the watch re-anchors on agreement, which is the behaviour the 2026-08-01 decision
rejected), and whether the read rate draws a 429.

---

### Step 2B — Worker transaction boundaries

After Step 2A. **Rescoped 2026-09-29** by finding 4: the service change already landed with worker
#104, so this step is mostly proof, not a port.

- Re-compare `4d4c1819471767301b0221b4514f917bbc1adc99` with current worker `main`; port only what is
  still missing. As of `e29b669` that is the real-DB regression test
  (`tests/test_lyrics_transaction_boundary_db.py`), not the service code (the commit's
  `tests/test_lyrics_incremental.py` change is also already on `main`). Do not merge the old branch
  wholesale.
- Inspect both `LyricsIncrementalService` and `LyricsReassessmentService` for any remaining path that
  holds a transaction across a provider wait: fetch → materialize → close → external work → fresh
  short write session.
- Preserve retry, idempotency and write correctness.
- Confirm the deployed worker revision contains the fix.

**Verification:**

- A real-DB regression proves no transaction stays open while a provider response is held; it must
  fail when the `commit()` calls are removed, and the later write must still succeed.
- Worker verification gates (required `test`), deployed fingerprint, production smoke and a bounded
  observation. No bulk replay or artificial demand solely to produce evidence.

**Rollback:** revert independently.

**Execution record (2026-10-01) — proof only; no worker change, no deploy.**

The step's premise was wrong in one respect: the regression test it set out to add already exists
(finding 4, second correction). Nothing was ported. What was established, all against worker
`main` `e29b669`:

| Claim | Evidence |
|---|---|
| The test runs in CI rather than skipping | Run `35569268246` (push, `e29b669`): all four cases of `tests/integration/test_lyrics_transaction_boundary_db.py` `PASSED`; 713 passed, 3 skipped; the skip gate reports `db_bound_skips: 0` (the 3 are the allowed MusicBrainz live skips). `test` is a required check, and CI sets `TEST_DB_URL` to a Postgres 16 service loaded from the canonical schema. |
| The test fails when a `commit()` is removed, on its assertion | Each of the four `self.session.commit()` calls was removed in turn, on a local Postgres 14.19 loaded from shared_db `98875c8` `tests/canonical_schema.sql` + the worker fixtures, with a venv built from `requirements.lock`. Baseline 4 passed. Every mutant: 1 failed / 3 passed, failing with `AssertionError: assert 'idle in transaction' not in ['idle in transaction']` — never a crash. `lyrics_incremental_service.py:71` → `[incremental]`; `:98` (lost-race guard) → `test_incremental_lost_race_…`; `lyrics_reassessment_service.py:123` → `[reassess]`; `:174` → `[album]`. One test per commit, no overlap. |
| The running Lambda carries the fix | `blogWorkerLambda` `$LATEST`, `LastModified` 2026-09-21T06:39:54Z (the deploy job of the same run), `CodeSha256` `KEDveHQG7FQSSumjEYdYk8cEqFQBZ3rqNh0v5JIGooY=`. The deployed bundle was downloaded and its `worker/` tree diffed against `e29b669`: identical. |
| No other path holds a transaction across a provider wait | Read, not run. `run_eval_batch` has three callers; all commit after their selection (`LyricsDemandSourceService.collect` is the third, with its own `pg_stat_activity` test). Inside the loop every branch that touches the session ends in a commit: `write_outcomes` and `touch` commit per row; the incremental lost-race guard commits; reassessment's `should_replace` is in-memory; the demand-source gate's query is followed by a write or a `touch` (`touch_on_guard_kept=True`). The transient-error and consistency-violation branches do not touch the session. |
| Bounded production observation | CloudWatch `/aws/lambda/blogWorkerLambda`, from that deploy (2026-09-21T06:40Z) to 2026-10-01T05:09Z, all pages: 0 events matching `ProtocolViolation`, 0 `idle in transaction`, 0 `Task timed out`. Control in the same pass: 6,040 `REPORT` lines, i.e. the search reads the window and the function ran 6,040 times in it. Read-only; no replay and no demand was injected. |

**Not established, stated rather than implied:**

- *"The later write must still succeed"* is not asserted by this file for the incremental and
  reassessment entry points: its provider fake raises before the writer, and the lost-race case
  ends in a guard-kept row. The write after the same commit shape is exercised on a real database
  only through the demand-source suite (`tests/integration/test_lyrics_demand_source_db.py`),
  which shares `run_eval_batch` and `TrackLyricsWriter`. No test was added for it here.
- With `concurrency > 1` the per-row write transactions overlap other rows' in-flight provider
  calls by design; what is ruled out is a transaction left *open and idle* across a wait.
- The log observation is an absence of three strings over 6,040 invocations, not a measurement of
  `pg_stat_activity` in production.

---

### Step 2C — Recurring catalog refresh

After Step 2B.

- Remeasure registrations, page counts, retries and configuration read-only.
- Separate Spotify enumeration, LRCLIB lookups and Claude translation costs.
- Do not apply a vocal-music translation rate to instrumental catalogs.
- Present measured cadence/cost to the owner before activating recurring reads.

Repair the all-complete-but-stale scheduling cycle, preserving:

- `_CONSUMED` semantics;
- member isolation;
- unfollow/exclusions and disconnected-member handling;
- backoff and resumable pagination;
- producer and consumer kill switches;
- bounded overlapping ticks and SQS retries;
- protection against partial pagination deleting unseen data.

Also classify empty-first-pass / uncatalogued-artist behavior; do not claim complete new-release
coverage while those cannot refresh.

**Back-catalogue ingestion (added 2026-09-30, finding 5).** This is the same coverage question from
the other side. The refresh finds new releases; this finds old ones the catalog never held. Present
both spend decisions together, each measured on its own: the refresh as provider pages per day, the
back-catalogue as catalog reads for the 686 waiting `follow` jobs plus the translations they unlock.
Measure the translations on a sampled subset first, not from the catalog's existing rate. Either
decision can be declined independently. A declined back-catalogue decision leaves Step 5's coverage
recorded as partial, not complete. The fix, if approved, sends enumerated albums missing from
`albums` to album sync; `_resolve_one_catalog`'s "not ingested yet" assumption then becomes true.
Do not reuse `run_follow_ingest`, which reads one 50-album page and only for uncatalogued artists.

**Rollback lever.** Until the `infra/lambda.tf` kill switches are applied by a human, the only
producer lever is the console value of `LYRICS_FOLLOW_DEMAND_ENABLED`. Record which lever the
rollback relies on before activating anything.

**Verification:**

- All complete + stale + no new follow starts a refresh.
- A newly returned release reaches album demand.
- Fresh or unconsumed rows do not trigger unnecessary reads.
- Repeated messages/ticks stay bounded.
- The switches stop both scheduling and queued consumption.
- After approved activation, observe an actual interval without creating a new follow to trigger it.
- Run the post-deploy member/follow/back-catalogue smoke that `FEAT-lyrics-listening-experience`
  Step 5's verification list requires and the 2026-09-30 audit found unrun; record the result in
  that RFC.

Record request counts, errors, completion, runtime identity and the user-visible result. A declined
budget means unresolved/deferred, not complete.

**Rollback:** disable the relevant follow-demand producer/consumer, confirm fencing, then revert if
needed. Preserve data/checkpoints and the separate saved/recent producer switch.

**Execution record (2026-10-01) — measurement leg and owner decisions; nothing activated, no code.**

Read-only against production at 2026-10-01 05:22Z, worker `main` `e29b669`. Nothing was written
and no registration was made due. Outside reads: 35 Spotify `GET /albums` calls (client
credentials, the 686 waiting ids, results kept local) and 74 LRCLIB `/api/search` calls.

*Current state, re-read before measuring.* 34/34 registrations `complete`, `last_complete_at`
2026-09-19 03:58–04:00Z, none due, all 34 consumed under `_CONSUMED`, all 34 catalogued. Follow
scope: 1,082 demands over 1,061 jobs — 372 resolved, **686 `album_not_in_catalog` (28 artists)**,
2 `album_partially_ingested`, 1 `album_has_no_tracks`. One connected Spotify member. Findings 3
and 5 hold as written, except the refusal count (corrected under finding 5).

**Refresh.**

| Measure | Value | Basis |
|---|---|---|
| Spotify pages per pass | **42** | `sum(max(1, ceil(album_total / 50)))` over the 34 registrations; 7 need 2–3 pages, largest `album_total` 132 |
| Runs per pass | 4 chained | `LYRICS_DISCOGRAPHY_ARTISTS_PER_RUN=10`, hop cap 20 |
| Retries | ≤ 3 attempts per page in `_request_with_retry`; a failed page defers 900 s and keeps its checkpoint | code |
| Cadence | `LYRICS_DISCOGRAPHY_REFRESH_HOURS=24` → 42 pages/day | config |
| New releases it would find | **98 in the 365 days before enumeration** (≈ 2/week) | `release_date ≥ 2025-09-19`: 74 already in `albums`, 24 among the waiting 686 |
| LRCLIB / Claude | ≈ 300 tracks and ≈ 160 translations a year | extrapolated from the 24 waiting recent releases (64 tracks) and the per-artist rates below — an estimate, not a measurement |

Without the refresh a new release can reach the catalog and still create no lyrics demand, because
demand is derived from `lyrics_artist_albums`. With the refresh but without the ingestion fix, a
release the catalog does not hold joins the `album_not_in_catalog` pile. The two are coupled.

**Back-catalogue (the 686).**

| Cost | Value | Basis |
|---|---|---|
| Spotify | 35 `GET /albums` calls (20 ids each), plus `get_artists` batches for new artists without a photo | `sync_albums_batch` |
| Catalog rows | 686 albums (64 `album`, 622 `single`), **2,064 tracks**, none truncated at 50, none already in `tracks` | the 35 reads |
| LRCLIB | 2,064 first lookups, one `/api/search` each; the not-found share then joins the retry ladder | `LrclibClient.search_candidates` |
| Claude | **≈ 1,100–1,200 translations** | two methods, below |

*Translations were not taken from the catalog's rate.* Two estimates, both specific to these
artists:

- **Per-artist measured outcome.** The 3,059 follow tracks the catalog already held split as
  29.6% translated (`linked` 659 + `already_translated` 245), 65.4% `not_found`, 3.7%
  `korean_source`, 1.3% `no_lyrics` — and the aggregate describes no artist. Charli xcx, The
  Weeknd, Mac Miller, Olivia Rodrigo, Lorde, sombr, Frank Ocean and Radiohead translate at
  93–100%; the Korean hip-hop artists (B-Free, Paloalto, Sik-K, Kid Milli, CHANGMO, Legit Goons,
  Skyminhyuk, JDL, Bassagong) at 0–8%, because LRCLIB does not have them or the source is Korean;
  Michael Korstick, a classical pianist, at 0% of 925. Applying each artist's own rate to their
  waiting tracks gives **1,094**. One artist (Yu Su, 54 tracks) has no resolved tracks and is
  counted as 0.
- **Direct LRCLIB sample**, seeded, of the waiting tracks: 27 of 30 from the high-rate artists and
  4 of 20 from the rest returned a duration-matched non-Korean body → 1,103 × 0.90 + 961 × 0.20 ≈
  **1,185**. The second stratum is n = 20 and wide. **Control in the same pass:** 24 tracks with a
  known pipeline outcome — 8/8 `linked`, 7/8 `korean_source`, 7/8 `not_found` reproduced (22/24).
  The probe is `/api/search` plus a ±3 s duration filter, not `decide_match`, so it runs slightly
  lenient.

*Three things the count alone hides.*

1. **`MAX_CATALOG_ALBUMS = 5000`.** `albums` is 4,788. All 686 make it 5,474, and
   `run_album_ingest` returns before sweeping once the cap is reached — which stops the daily
   new-release sweep and the release-calendar confirmation that only that sweep drives. The cap is
   checked only there; `sync_albums_batch` would write straight past it.
2. **312 of the 686 are below `ALBUM_POP_MIN = 20`**, the gate the scheduled ingest already
   applies. They carry ≈ 93 of the translations.
3. **468 of the 2,064 tracks (23%) repeat a title** the catalog already holds for that artist or
   that appears earlier in the 686 — singles and remix bundles. Reuse is per track
   (`already_translated` compares this track's own published row), so each is a separate model
   call. Excluding them leaves ≈ 713. Title equality is a proxy; ISRC was not read.

| Scope | Releases | Tracks | Translations (per-artist rate) | `albums` after |
|---|---|---|---|---|
| All | 686 | 2,064 | ≈ 1,094 | 5,474 |
| Popularity ≥ 20 | 374 | 1,239 | ≈ 1,002 | 5,162 |
| `album` group only | 64 | 930 | ≈ 521 | 4,852 |

Claude is a shared subscription, not a metered bill: the poller has completed 150 work rows per
active day on average (maximum 270), so ≈ 1,000 is about a week of that budget.

**Owner decisions (2026-10-01, in-session).**

- **Refresh: approved at 24 h** — 42 provider pages a day at today's 34 registrations.
- **Back-catalogue: approved for releases with popularity ≥ 20 only** (374 of the 686, ≈ 1,000
  translations), with the catalog cap raised to make room. Step 5's follow coverage is therefore
  recorded as *complete within the existing curation gate*, not complete: the 312 releases under
  the gate stay out by decision.

**What the implementation leg inherits.** Not started; a separate session and worker PR.

- Popularity is not in the `/artists/{id}/albums` listing, so the gate is applied to the
  `GET /albums` response — all waiting ids are read, only those passing are written.
- The releases under the gate need a resting disposition. Today they would stay
  `album_not_in_catalog` and be re-checked on the catalog ladder for ever.
- The new `MAX_CATALOG_ALBUMS` value is not chosen. 5,162 is the floor; the catalog was 212 short
  of the cap before this decision.
- The rollback lever is still the console value of `LYRICS_FOLLOW_DEMAND_ENABLED`; the
  `infra/lambda.tf` switches remain unapplied.
- This step's Verification list is untouched: nothing here was activated, so none of it is met.

**Observed while measuring, not acted on (Step 2D).**

- Michael Korstick: 925 resolved tracks, 913 `not_found`, 12 `no_lyrics`, none translated — the
  Debussy shape. He is 46% of the 2,002 follow tracks on the LRCLIB retry ladder (gaps of 8 and 16
  days today). `user_artist_follow_exclusions` would stop it with no code change; that is the
  owner's call and was not asked.

**Execution record (2026-10-05) — implementation leg narrowed to the catalog cap; the rest held.**

Production moved between the decision and the implementation (read-only, 2026-10-05):

- **The refresh ran once by the old accident.** A 35th artist was followed at 2026-10-03 03:53Z;
  that new registration made the enumeration job due, and the job re-opened and re-read all 35
  stale registrations (`last_complete_at` 2026-10-03 for all 35). Finding 3's cycle still holds:
  nothing re-opens them again without another new follow. The waiting follow releases grew from
  686 to **848**.
- **The catalog reached the cap.** `albums` 5,002; CloudWatch 2026-10-05 05:31:53Z
  `album_ingest: catalog cap reached (5001 >= 5000) — skipping tick`. The daily new-release sweep
  and release-calendar confirmation stopped — before any back-catalogue ingest, from ordinary
  growth of ~190 albums/week (151–229 over ten weeks).
- **Automatic Claude translation is being retired** in favour of explicitly requested translation
  (ws #1022, draft; launchd translation jobs already disabled). The back-catalogue spend was
  approved for the ≈ 1,000 translations it would unlock automatically; that benefit no longer
  follows from ingesting the releases.

**Owner decision (2026-10-05, in-session):** work as conservatively as possible and close this
leg; the translation move is handled separately. **Shipped:** worker #108 (`89b8e6b`) —
`MAX_CATALOG_ALBUMS` 5000 → 8000, the value the owner chose on 2026-10-01 (~14 weeks at the
current rate). Nothing else changed.

- CI `test` green on the PR and on `main` (713 passed / 3 skipped, all `musicbrainz_live`,
  `db_bound_skips: 0`); deploy run 37291037299 green; `blogWorkerLambda` `CodeSha256`
  `KEDveHQG…` → `L3l9UxDm…` at 09:37:39Z; `scripts/smoke.sh prod` 30/0, quoted on #108.
- **Open:** the next daily `album_ingest` tick (~2026-10-06 05:32Z) must log an
  `album_ingest summary:` line instead of the cap message. Deliberately not triggered by hand —
  a manual invoke is an extra sweep of Spotify reads.

**Held, not shipped:** the refresh-reachability fix (a `refresh_due_count` the nudge also asks)
and the gated back-catalogue ingest (claim → `GET /albums` → write ≥ `ALBUM_POP_MIN`, rest the
rest for 30 days, stop at the cap). Both were written and tested (740 passed against a local
Postgres with the canonical schema; 31 mutants, all killed) and are kept on an unpushed worker
branch, `feat/OPS-project-stabilization-step2c-refresh-backcatalogue` (`2ca9b40`). Re-decide
them once the translation path is settled: with on-request translation the back-catalogue
would only pre-fill catalog and lyrics sources out of the irreplaceable Spotify quota. Until
then Step 5's follow coverage stays **partial**, and this step's Verification list is unmet
except for the cap.

---

### Step 2D — Residual failures

After the Step 2C decision.

- Remeasure `album_not_in_catalog` and failed work by reason, age and retry eligibility. Count the
  686 `follow`-origin back-catalogue jobs under Step 2C, not here; they are a coverage gap, not
  failures. The non-follow `saved` job is residual.
- **Subscription guard.** A blank `claude exit 1:` must not count as a throttle unless the CLI's JSON
  envelope says so; read the stdout the guard currently discards. No spend. The change goes into
  `myblog_shared_db`, then each consuming service's pin moves to the new `main` SHA. The regression
  test must fail on the 2026-07-28 rule, and a genuine throttle envelope must still cool down. It
  needs no spend decision and caused a three-day outage, so it is a candidate to run earlier. The
  order stays as the owner set it unless the owner moves it.
- **Copyright refusals.** Measure the refusal rate and classify refusal output as terminal for that
  source revision, rather than letting lease expiry re-claim it indefinitely.
- Separate terminal/source-missing rows from stranded retryable work.
- Use bounded, justified remediation with before/after counts.
- Do not reset all failures or overwrite completed/manual translations.
- Give larger newly found defects their own scoped entries.

**Exit (Steps 2B–2D):** each operational leg has deployed/verified evidence or an explicit
blocked/deferred disposition.

---

### Step 3 — Inspect real user journeys

Read-only measurements and browser journeys; reversible writes only in an authorized test account.

**Journeys:**

- Search → save → organize → play → lyrics.
- Signed-out action → login → resume.
- Saved album → rating or long-form note → return later.
- Owner note/research → draft → preview.
- Sync/import accepted → completed.

Include desktop/mobile and owner/member/signed-out states where relevant.

**Record:** deployed revision and observation date; connected-service capability; attempted and
completed actions, errors, steps and elapsed time; missing access and unverified paths; fresh usage
counts with denominators.

Do not publish a review or recruit users merely to satisfy validation. Do not equate missing evidence
with missing demand. Evaluate long-form notes separately from bounded rating comments.

**Deliverable:** a dated user-journey report with at most three ranked improvements and one
recommended next item — or a recommendation to avoid new features if the evidence does not support
them. Rank by affected users, severity, frequency, effort and regression risk.

**Exit:** observations are reproducible; defects have owners and plan entries; the owner selects the
next product investment.

**Rollback:** remove authorized test fixtures; keep dated observations without secrets or private
content.

## Open questions

1. ~~**RFC lifecycle approval**~~ — **resolved 2026-09-30**: the owner accepted the RFC in-session
   (`draft` → `accepted`). Promotion to `in-progress` is a separate owner decision.
2. ~~**External playback observation policy**~~ — **resolved 2026-10-01** (owner, in-session): a
   conditional 10 s read while the lyrics viewer is open, quiet unless something changed. The
   exception and its bounds are owned by finding E; delivered as front #449. *History: the
   question was to define the latency/mechanism and reconcile the no-polling rule before
   introducing regular polling; the bounded discovery retry (front #448) did not answer it.*
3. ~~**Recurring catalog refresh cadence and spend**~~ — **resolved 2026-10-01** (owner,
   in-session): approved at 24 h, measured at 42 provider pages a day. Record under Step 2C.
4. ~~**Back-catalogue ingestion spend**~~ (added 2026-09-30) — **resolved 2026-10-01** (owner,
   in-session): approved for releases with popularity ≥ 20 only — 374 of the 686 waiting `follow`
   albums — with the catalog cap raised. The 312 under the gate stay out. Record under Step 2C.
5. **Next product investment** — decide after Step 3 rather than from old usage counts.

## Decisions log

| Date | Decision | Step |
|------|----------|------|
| 2026-09-28 | Owner requested a coordinating RFC and a first-priority plan entry for progress reconciliation, lyrics reliability/operations and evidence-based product review. | — |
| 2026-09-28 | Owner reported homepage lyrics access and open-viewer next-track failures and asked for both to be added to the plan/RFC. | 2A |
| 2026-09-28 | Frontend repair designated Step 2A, the first runtime priority; transaction, recurring refresh and residual-failure legs follow as 2B/2C/2D. | 2A–2D |
| 2026-09-29 | Documentation handoff prepared because the original integration could not write to GitHub (`403 Resource not accessible by integration`). This is not evidence of implementation, deployment or lifecycle promotion. | — |
| 2026-09-29 | Re-check of worker `main` (`e29b669`) found the `4d4c181` service change already merged via worker #104 (`4ece539`); only its real-DB regression test is missing. Step 2B rescoped from "port" to "prove and confirm deployed". The no-polling rule's "D28" attribution recorded as unresolved (finding E). | 2B, 2A |
| 2026-09-30 | Rebuilt on workspace `main` `9318958`; the original PR's branch conflicted with #1013 in `docs/plan.md`. The Step 5 post-delivery audit (#1013) was absorbed as the evidence baseline. Findings 1 and 5 were rewritten against it. Step 2C gains the back-catalogue ingestion decision (OQ4), the rollback-lever note and the unrun Step 5 smoke. Step 2D gains the subscription-guard fix and copyright refusals. Worker `4d4c181` finding re-confirmed. Status stays `draft`. | 1, 2C, 2D |
| 2026-10-01 | Step 2B found its own premise false: the real-DB regression test was already on worker `main` (`tests/integration/…`, in #104), looked for at the wrong path twice. Owner approved in-session narrowing the step to proof — CI execution, mutation, deployed bundle, residual-path read, bounded log observation — with no worker change. Record under Step 2B. | 2B |
| 2026-09-30 | **Owner promoted the RFC to `in-progress`** in-session and chose the Step 2A rollback part first (cases 3, 4, 6, 7; OQ2-independent). Delivered as front #447 (`048fc31`); record under Step 2A. Review changed the session's boundary burst: `idle` is no longer a settled answer. | 2A |
| 2026-10-01 | Owner chose the Step 2A home-discovery part (finding A, cases 1–2). No-polling rule located — a convention without a single owning record (finding E); the bounded retry after a failed read reconciled there. Delivered as front #448; record under Step 2A. | 2A |
| 2026-09-30 | **Owner accepted the RFC** in-session (`draft` → `accepted`) and chose Step 1 first. Step 1 delivered; execution record under Step 1. Canonical member URL premise found false (prod `/api/members` non-empty) — recorded, decision not re-opened. | 1 |
| 2026-10-01 | **OQ2 resolved by the owner:** external changes are observed by a conditional 10 s read while the lyrics viewer is open (option A of three). This reverses, for song identity and observed discontinuities only, the 2026-08-01 acceptance of the "phone operated while the tab stays visible" gap; the no-periodic-re-sync rule itself stands (an agreeing read changes nothing). Owner also confirmed watching a paused track for 5 minutes. Finding E now owns the exception. Delivered as front #449. | 2A |
| 2026-10-01 | **OQ3 and OQ4 resolved by the owner** from the Step 2C read-only measurement. Refresh approved at 24 h (42 pages/day). Back-catalogue approved for popularity ≥ 20 only (374 of 686 releases, ≈ 1,000 translations) with `MAX_CATALOG_ALBUMS` raised; follow coverage is recorded as complete within the curation gate, not complete. Nothing activated; implementation is a separate leg. Finding 5's refusal count corrected. | 2C, 2D |
