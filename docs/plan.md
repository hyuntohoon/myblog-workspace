# Plan

Active workspace tracker for cross-repo work. Each row carries `Scope / Order (if multi-repo) / Verification (local + prod smoke) / Rollback / Status`; RFC-backed entries collapse to a one-line pointer at `docs/rfcs/<id>-<slug>.md`. When a row finishes, drop it — `git log` and `docs/archive/done/YYYY-MM.md` are authoritative for history.

---

## Active

> Open decisions, gates and observations only. Shipped detail lives in `git log`, in each RFC, and in
> `docs/archive/done/`. A row that has nothing left but a status promotion is not Active — close it.

- **SEC-system-hardening** (`docs/rfcs/SEC-system-hardening.md`, accepted) — main governance, keyless
  <!-- rfc: docs/rfcs/SEC-system-hardening.md | status: accepted -->
  deploys, one JWT verifier. **Steps 1–6 are all shipped and production-verified** (rulesets on all six
  repos, front + backend/music/worker OIDC, both Cognito guards hardened with signed-token vectors,
  polyrepo verdict KEEP POLYREPO, and one canonical byte-identical `app/core/auth.py` across backend and
  music with a daily drift workflow). No AWS credential secret exists in any of the six repositories and
  `github-actions-deploy` has zero access keys. Full per-step record → the RFC and `git log`.

  **What is still open — one P0 and one question, both the owner's:**
  - **The AWS root account access keys.** Deleting the `myblog_front` repo secret did not retire the key.
    `AccountAccessKeysPresent = 1` **re-verified 2026-09-03**; the per-key reading from 2026-08-29 is
    `access_key_1` (rotated 2025-11-13, last used 2025-12-10, ap-northeast-2/cloudformation) and
    `access_key_2` (rotated 2025-10-22, last used **2026-08-26**, the last front deploy before the OIDC
    cutover) — both `Active`. Root keys can only be deleted by signing in as root with MFA, so this is
    not Claude's to perform. Everything else in Step 3d is done.
  - **Should `workspace-check` become a required check?** The workspace repo gained a `pull_request`
    workflow in ws #948 and it has passed on eleven PRs; its ruleset still carries only `main-protection`.
    Making it required is an open item, not a decision already taken.

- **FEAT-album-review-authoring** (`docs/rfcs/FEAT-album-review-authoring.md`, accepted) — album
  <!-- rfc: docs/rfcs/FEAT-album-review-authoring.md | status: accepted -->
  **평가 = rating** (public star rating + one-line comment), **평론 = review** (editor long-form review).
  Korean UI must not use "리뷰" for either concept. Steps 1 and 2 are shipped and prod-verified, along
  with the entrance-link/visibility defects found after Step 2.

  **The usage gate is RETIRED (owner 2026-09-03). No longer blocked on a counter.** Prod on
  2026-09-03: **37 owner ratings** (first 08-10, last 08-19, plus 1 non-owner) against **9** additions
  since front `2dcabd0` (2026-08-15).

  **This row is where the gate failed, and the failure is worth keeping.** The RFC's gate had *three*
  branches — pass · **fail** · under-threshold — and the fail branch said exactly what to do here:
  *"if the rating count leaves 0, this step's premise collapses; re-open what to build with the owner."*
  **It became true on 2026-08-10 and nobody acted on it for 24 days**, because this row had flattened
  the three branches into one AND — *"additions ≥10 **while owner ratings stay 0**"* — which drops the
  fail branch entirely. What survived the summary was only "if additions <10, do not decide", so the
  single action a reader could take was to wait. Three sessions read the counter and stepped back.
  **When copying a gate into this file, carry every outcome branch or link to the RFC instead** — the
  "re-open the decision if this breaks" branch is the first one a summary loses and the one that keeps
  a gate alive.

  **The measurement it was meant to produce came out anyway, and it inverts the gate's assumption.**
  The gate read "owner ratings > 0" as evidence the owner rates instead of stockpiling for reviews.
  In fact **36 of the 37 rated albums were albums already sitting in a bucket** (1 was not; 73
  bucketed albums remain unrated): the 담기 → 평가 funnel worked. On 08-17 the owner drained 35 of
  them in one sitting, and additions stopped that same day — the counter stalled at 9 because the
  backlog was spent, not because the funnel died. Weekly additions: 07-20:3 · 07-27:23 · 08-03:4 ·
  08-10:4 · 08-17:5 · then 0 for 17 days.

  **Two premises behind the remaining steps were falsified by the same measurement**, and both are
  recorded in the RFC: **33 of 37 ratings are star-only** (4 carry text, averaging 17 characters), and
  **C6 평론 후보 표시 has exactly 1 mark ever** (2026-08-10, on a row with no rating; none of the 38
  rated rows is marked). Published reviews remain **0** (5 drafts, last touched 07-27).

  **Step 4 is SHIPPED and production-verified (2026-09-03, front #442 `a8d9eef`).** OQ9 and OQ14 are
  closed. One 쓰기 entry in the header for every signed-in account, offering only what the viewer may
  write; 평가 hands off to the EXISTING album-overlay rating editor rather than a second form, which is
  also what makes C1's "entered from a card, the album is already chosen" true with no card changes.
  The 평론 후보 mark moved into that write as an owner-only checkbox saved in the same PUT.

  **Audit E-5 is closed — and it was SIX places, not the one this row and the RFC named.** `/write`
  and `/drafts` each carried their own `isLoggedIn()` check (never a data hole — every `/api/posts*`
  mutation is `require_owner` and fails closed — but the client surface was open); the same proxy
  then turned up in the dashboard 평론 tab, the bucket tile mark, the album rating mark, and, found by
  `security-review`, the 편집 link on every published 평론 page plus the memo window's editor link.
  **Do not size a sweep off the count a document gives you.** Verified on production with a real
  member Cognito session: `/write/` and `/drafts/` both bounce, prod smoke 30/0.
  *Still unverifiable*: the published-평론 편집 link — prod has **zero** `/review/` pages.

  · **Step 3 (owner-only AI distillation, C3+C4) — DEFERRED, and its deferral evidence has an erratum
  the owner has not yet seen (2026-09-03).** Its premise is that the owner writes unstructured 자유 감상
  for the AI to distill. **Do not start it, and do not tune OQ3's default prompt, until the owner sets a
  new resumption condition** — that has not changed, and an erratum is not a start signal.
  **What the erratum says**: the "owner writes essentially no text" measurement was taken on
  `album_reviews.comment`, a field capped at `RATING_COMMENT_MAX = 60` — a number this RFC's own Step 1
  picked so that *"문단 쓰기는 물리적으로 막는다."* The owner's long-form album text exists in the bucket
  memo (7 albums, mean 436 chars, max 1,429; 6 of the 7 also carry a rating row), **dormant since
  2026-08-03**. This does not choose among OQ13's three candidates — it changes the case for each, and
  the RFC's OQ13 carries that per-candidate breakdown. **The decision is the owner's and is still open.**
  · **Step 5 (conditional general AI opening) — DEFERRED**, dependent on Step 3.
  AI behaviour, if Step 3 ever resumes, remains distillation only: use only material the author
  supplied, never add outside facts/evaluations/metaphors, the result stays editable, and publishing
  is always an explicit user action.

- **ARCH-entity-interaction-domain-audit** (`docs/rfcs/ARCH-entity-interaction-domain-audit.md`,
  <!-- rfc: docs/rfcs/ARCH-entity-interaction-domain-audit.md | status: in-progress -->
  in-progress) — independent audit of review/memo commands, playback-state ownership, lyrics hosting,
  bucket-add flow, modal infrastructure and global events. **Every step is now shipped** — Steps 1, 2,
  3 (3a/3b/3c) and 4 prod-verified 2026-08-05/06, and **Step 5 shipped 2026-09-03** (docs-only).

  **The only thing left is an owner Status promotion** (`in-progress` → `done`; 하드 룰 7 — Claude never
  self-promotes). Once promoted, drop this row.

  **Step 5 refuted its own charter, which is why it is worth a line here rather than just in the RFC.**
  It was written as *"rename the memo, and correct the one-user-album-state premise against the bucket
  memo."* Neither half survived contact: there was **no name to rename** (that RFC calls the concept
  자유 감상 원문, never 메모 — the collision is functional, with the already-shipped 버킷 메모), and the
  premise is false in **five** state stores rather than the one the audit named — including
  `planned_ratings`, which **the owner deliberately chose on 2026-08-13 knowing it broke the invariant**.
  A third finding fell out of the same sweep and is the one with a live consequence → see the
  `FEAT-album-review-authoring` row below. Full evidence, tables and the branch that was *not* taken:
  the RFC's Step 5 and its Decisions log — **not restated here**, so no outcome branch can be lost in
  the copy.

- **DATA-release-noise (c) exact-dup dedup** — promoted from Backlog 2026-08-16 on owner approval.
  <!-- rfc: none -->
  **The only Active row that is startable today**: no RFC, no gate, no owner decision pending, and its
  one stated dependency was retired on promotion — the `PERF-home-feed-latency` note was stale and has
  never existed as an RFC or a plan row.

  Re-measured before promotion, and smaller than the original row implied: artist-scoped exact
  duplicates (same normalized title **and** same artist set) are **56 groups / 57 redundant rows of
  3,440 albums = 1.7%**. A title-only count reads 107 groups / 169 rows, but that conflates distinct
  artists sharing an album title and is not the dedup population — do not size the work off it.
  *Scope*: catalog dedup, small enough to live in this row rather than an RFC. *Verification*: the
  touched repo's gate + a before/after count against prod. *Rollback*: nothing is destructive until the
  delete step; keep it reversible. *Status*: not started. **Re-measure before starting** — the figure
  above is from 2026-08-16 and the catalog has grown since.

- **FEAT-youtube-playback-provider** (`docs/rfcs/FEAT-youtube-playback-provider.md`, draft) — a second
  <!-- rfc: docs/rfcs/FEAT-youtube-playback-provider.md | status: draft -->
  playback provider so a member without a Spotify account can play the tracks in their Buckit. Spotify
  stays the catalog, the ingest path and the default player; nothing in `spotifyPlayback.ts`, the queue
  or membership changes.

  **Phase 0-A ran 2026-09-05 and returned GO.** It existed because the two numbers governing this
  decision were borrowed rather than measured. On a 20-track reproducible sample of our own catalog
  plus 2 controls: top result is the **correct studio version 20/20** (16/20 if every uncertain call is
  counted against us), **wrong-version 0**, **no-result 0**, **`status.embeddable` 20/20**. Gate was
  ≥12/20 and ≥16/20. Both controls passed, so the score is not a lenient-harness artefact. **The
  "~34% wrong-version" figure carried through three RFCs is not true of this catalog** — it was the
  load-bearing justification for the deferral and it does not hold. Cohort split, the three findings
  the counts do not show, and the sample composition → the RFC's *Current state*.

  **Shipped already**: the CSP allowlist (ws #984) and the Cloud project + API key in SSM
  `/myblog/youtube`. **Merging #984 did not deploy it** — workspace infra is applied by the owner
  locally, so the IFrame API is still blocked in production until that apply lands.

  **What is open — all of it the owner's:**
  - **Does Milestone A start?** Phase 0-A removed the technical objection, not the priority one.
    Steps A1–A5 are specified and independently revertible; nothing is under way.
  - **The owner applies the workspace infra** (`terraform apply`), then a real-browser check that the
    Spotify SDK still loads — a CSP edit affects every page.
  - **The API key was pasted into a session transcript 2026-09-05 and is an exposed credential.** The
    owner chose to keep using it. Rotate before A2 puts it on a live user-facing path.
  - Phase 0-A step 3 (IFrame `onError` codes `100` / `101/150`) was **not run**. It gates A4, not A1.
  - Milestone B stays closed behind Phase 0-B, which needs a real account with real YouTube Music use.
    No table is designed until it returns — that is the specific failure mode `FEAT-pocket-buckit`
    demonstrated over fifteen months.

- **Settings-loader required-key sweep (music + worker)** — **DEFERRED by the owner 2026-08-29.**
  <!-- rfc: none -->
  Tracked here because it is a *known, reproduced* defect whose only other record is a merged PR body.
  `myblog_backend` #172 made its SSM loader fail closed on a missing required key and fixed the
  *formulation* as well: it inspects the SSM **payload** and rejects whitespace-only, non-string and
  non-object values. `myblog_music/app/core/config.py` and `myblog_worker/worker/core/config.py` still
  check the **resolved settings** (`if not v`), which is weaker in two ways. Reproduced against music's
  own loader, not inferred: `{"DATABASE_URL": "   "}` boots with a whitespace DSN, and
  `{"SPOTIFY_CLIENT_ID": 12345}` boots storing an `int` in a `str` field (neither model sets
  `validate_assignment`). Second, latent: their check can be satisfied by a Lambda **env var** standing
  in for a key the parameter is missing — dormant today (neither `musicApi` nor `blogWorkerLambda`
  carries those variables) but it is the hole backend now has a test against.
  *Scope*: `myblog_music`, `myblog_worker` — port `_present` + payload-based validation. Their required
  **sets** are already correct (`DATABASE_URL`, `SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET`; worker's
  `LASTFM_API_KEY` / `GENIUS_ACCESS_TOKEN` correctly optional) — do not change them. *Order*:
  independent, either first. *Verification*: each repo's `test` gate + a boot simulation per the backend
  PR. *Rollback*: revert the per-repo PR. *Status*: not started, deferred — **do not re-prompt the owner
  on this without a new trigger.**

---

## Owner-only (nothing here is Claude's to do)

Items with no remaining implementation, kept visible because dropping them would lose the only record.

- **AWS root account access keys** — see `SEC-system-hardening` above. Requires a root sign-in with MFA.
- **BEST NEW ALBUM toggle: one live click-test.** Shipped 2026-08-25 (backend #161 `a75b943`, front #424
  `9e34228`, ws #933 `2784f97`) — owner-only mark/unmark of `albums.best_new` directly from
  `AlbumRatingBlock`. Everything verifiable without an owner session was verified (prod smoke 19/19, the
  public aggregate carrying `best_new`, and a 403 for a non-owner token on the new route). The actual
  owner-success toggle path was **not** verified, because it needs a live owner Cognito session rather
  than the smoke member account. One click as the owner closes it. Detail →
  `docs/archive/done/2026-09.md`.
- **SEO-review-structured-data** — trigger is the first production review publication; see *Later*.

---

## 2026-07-23 감사 파생 작업 (남은 것 = P2뿐)

> Source: `docs/reviews/2026-07-23-current-state-audit.md`.
>
> Only verified/accepted findings remain here. P0/P1 work is complete and archived.
>
> **Owner decision 2026-07-23:** prioritize safety/quality before discovery; retain the criticism-publication framing; OPS/REFACTOR RFCs accepted; documentation reconciliation approved.

### P2 — 실사용자 증거 후

- **CHORE-dep-reproducibility** — `myblog_backend` + `myblog_music`. Add lockfiles and pin `fastapi`/`boto3`/`SQLAlchemy`; replace backend non-tag SHA dependency with a tag. Trigger: another deployment 500 caused by dependency drift. Current additive convention remains accepted until then. Additional 2026-07-26 evidence: `SQLAlchemy==2.*` and `psycopg[binary]==3.*` re-resolve on deploy and wildcard strings create misleading CVE-search results. Dependency *notification* is separate → `OPS-safety-net-drift` Step 4.

- **DISCOVERY-flow** (**hypothesis; rejected for now**) — potential `signup → import → Buckit → publish → discovery` investment. Current evidence remains insufficient: published content, other-user activity, and public collections are too sparse for discovery investment to be meaningful. Re-evaluate only after real-user + content evidence. What the product's core flow should be remains an owner strategy decision.

---

## 2026-07-26 감사 파생 작업 (전부 종료 — 열린 항목 없음)

> Source: `docs/reviews/AUDIT-2026-07-26-system-audit.md` (ws #704, squash `9d4711c`). The report contains the evidence; these rows are pointers.
>
> **E-2/E-4/E-6/DEP-2 fixed + deployed + prod-smoked 2026-08-09** (front #389, ws #871). E-2/E-6/DEP-2 shipped code, verified live against the deployed bundle (`_astro/CollectionView.*.js` calls `publicMemberLabel`, `_astro/AlbumDetailView.*.js` carries the scoped `.lf-artist-link` rule, `/rss.xml` parses under 4.0.19). E-4 needed no code — superseded by the front #379–#384 home-card migration (merged 2026-08-06), whose `AlbumCard` open-hit button has no visible text content, so the WCAG 2.5.3 failure it described no longer exists.

### Decided, no action

- **D-2** — closed 2026-08-16 with no action (owner decision). `LLMTransientError` engine-level retry; every caller was found to have its own defence, so the fix was defence-in-depth and did not justify a cross-repo `myblog_shared_db` change + three re-pins. Evidence and reasoning → `docs/archive/done/2026-08.md`.

- **PUB-1** — workspace and four service repos are public; owner chose to merge the audit as-is on 2026-07-26. The report overstated dependency-version disclosure because manifests were already public. A-3 is fixed; the remaining E-5 surfaces are tracked under `FEAT-album-review-authoring` Step 4.

### Audit coverage boundary

The audit did **not** cover the full infra/IAM/S3/CloudFront/KMS/Cognito surface, all CI workflows, all tools/non-buckit scripts, frontend server-side code, PWA/service-worker config, all member-content escaping sites, load/concurrency testing, DB-level data quality, Terraform state, or complete Python-CVE call-path tracing. Do not read its clean findings as broader guarantees.

---

## Backlog

> Scope-ready drafts/deferred work. Each still needs an owner go (+ RFC accept where draft) before promotion to Active.

- **FEAT-durable-job-status** (**backlogged 2026-09-02; needs owner go + an RFC**) — a durable,
  readable status for the async jobs a user can start from the UI: the Spotify album sync
  (`POST /api/music/sync-requests`) and the Release Radar's Spotify follow import
  (`POST /api/me/tracked-artists/spotify-import`). Today both answer *accepted* and go silent; the
  worker finishes minutes later and nothing tells the surface.
  <!-- rfc: none -->
  **Why it is here rather than in the leg that met it.** `FIX-user-flow-state-consistency` leg 4
  shipped the honest half — `syncRequested` lets a surface offer a catalog re-read after an accepted
  request — and deliberately did **not** invent a status contract to hang a spinner on. That row
  named this as "a separate durable job-status design across backend/worker/front" and was dropped
  when its four legs finished, so this is that pointer surviving its parent.
  *Scope*: `myblog_backend` (or `myblog_music`) + `myblog_worker` + `myblog_front` — a job record the
  worker writes terminal state to, and a read the surface can poll or subscribe to. *Order*: schema →
  worker write → service read → contract → front. *Verification*: each repo's gate, plus a real
  clickthrough that watches a request go from accepted to done without a manual refresh.
  *Rollback*: revert per repo PR; the front degrades to leg 4's manual re-read.
  **Do not size this off the UI.** The interesting half is the worker: what counts as terminal for a
  bulk album sync where some ids succeed and some fail, and how long a completed job stays readable.
  *On promotion to Active*: drop the pointer below — `scripts/check_workspace_invariants.py` rejects
  an Active row referencing `docs/archive/done/`.
  Background → `docs/archive/done/2026-09.md` (FIX-user-flow-state-consistency, *Deliberately not
  done*).

- **FEAT-member-own-listening-widgets** (**deferred 2026-09-01 by owner decision; trigger-gated**) —
  give a non-owner member their OWN now-playing and 최근 재생 트랙 cards, over the V45
  `spotify_member_now_playing` / `spotify_member_recent_tracks` tables the worker's per-member poll
  already writes. These are Steps 2 and 3 of the closed `SEC-member-listening-data-boundary`, moved
  here rather than left in an open security RFC.
  <!-- rfc: none -->
  **This is a feature gap, not a boundary defect.** That RFC's Step 1 shipped and was
  production-verified 2026-08-30 with all nine owner-global `GET /api/library/*` routes
  `require_owner`-gated — the leak measures **zero**. Nothing is exposed by this sitting here.
  **Why it is deferred rather than built.** A current-state audit on 2026-09-01, run before starting
  Step 2, counted the addressable population in production: 4 users, **1** with a Spotify
  integration, and that one is the owner. `spotify_member_recent_tracks` holds 1,953 rows across
  exactly **1** distinct `user_id`. The other three accounts have no Spotify and no Last.fm
  integration and zero rows. Step 2 serves **0 of 3** non-owner accounts, would render an empty card
  for each of them, and its own verification line — *"non-owner clickthrough: their OWN Spotify play
  appears in 지금 재생 중"* — cannot be performed, because no second connected account exists.
  **Trigger**: a second account connects **Spotify**. Not Last.fm — a Last.fm connect writes
  `lastfm_recent_tracks`, never the V45 `spotify_member_*` tables this row is scoped to, so firing on
  it would promote work whose named source is still empty. Re-count before promoting — the numbers
  above are the denominator, and they are what makes this worth doing or not.
  **Banked so it is not re-derived** (both from the closed RFC): `/api/me/now-playing` reads
  `spotify_member_now_playing` **directly, Spotify-only** — not a self-scoped reuse of
  `public_now_playing`'s Last.fm+Spotify merge (owner, 2026-09-01), keeping `nowplaying` as the
  Spotify card and the existing `lastfm-nowplaying` as the Last.fm one. And members already have
  `lastfm-nowplaying` (it is not in `OWNER_ONLY_WIDGETS`), so the *code* gap is the **Spotify half
  only** — but do not size the work off that: none of the three non-owner accounts has a Last.fm
  integration either, so every real member's Last.fm card is empty too. Registry-true, user-false.
  Step 1 removed the widget ids from a non-owner's registry entirely and rewrote their saved
  `lf_ov_rows`, so this work **re-admits** the widgets and must also put them back on the board or
  say plainly that the member re-adds them via ＋ 컴포넌트 추가.
  *On promotion to Active*: drop the pointer below — `scripts/check_workspace_invariants.py` rejects
  an Active row referencing `docs/archive/done/`.
  Background → `docs/archive/done/rfcs/SEC-member-listening-data-boundary.md` (Closeout audit).

- **MEASURE-playback-boundary-buffer** (**backlogged 2026-09-01 by owner decision**) — the 1500 ms
  end-of-track boundary tolerance is a first-pass estimate, never measured. It was OQ4 of
  `ARCH-playback-authority-convergence`, stayed open through all four of that RFC's steps because each
  deliberately kept it out, and was moved here on that RFC's archival rather than closed.
  <!-- rfc: none -->
  **Why it is not simply closed.** `scheduleBoundaryCheck()` (`myblog_front/src/lib/playback/session.ts:2194`, guard at `:2196`)
  arms only while `isOwner && rung === 'remote' && playing` and fires at
  `Math.max(500, remaining + BOUNDARY_BUFFER_MS)`. What it fires is `confirmCompletion()` → `adoptLive()`,
  and `adoptLive()` is where the deleting gate lives (`session.ts:1081` —
  `positionNow() >= previousDurationMs - BOUNDARY_BUFFER_MS` → `deleteBucketItem`). **These are not two
  independent consumers; one calls the other.** The constant sets both the instant the check happens and
  the tolerance it is judged by, and `positionNow()` keeps extrapolating by wall clock while `playing`,
  so raising it defers the read *and* loosens the gate — leaving "the URI changed" plus `!anchorAmbiguous`
  as the real protection on a path that deletes a queue row. A mid-track skip on another device raises no
  `MYBLOG_PLAYBACK_CHANGED` here and is first seen by exactly this scheduled read. That is the same window
  as the archived RFC's residual risk OQ3(a). Smaller, conversely, leaves finished tracks in the queue
  until the next event. Measuring the constant is the only way to size a risk that was recorded rather
  than fixed. *Caveat carried from the RFC*: OQ3(a) could not be reproduced in the harness — the adoption
  that runs during a reissue sees a position near zero, not near the end — so this is an unsized risk, not
  a known-live one.
  **Sweep set — the quantity is declared twice.** A retune must not stop at `session.ts`:
  `BOUNDARY_BUFFER_MS = 1_500` (`session.ts:1011`, used at `:1081` and `:2204`) and
  `END_GRACE_MS = 1500` (`src/components/member/lyrics/LyricsViewer.tsx:151`, used at `:594` and `:1171`)
  are the same boundary tolerance at the same value under two names, and `:594` is the same
  `duration - GRACE` predicate shape. `src/lib/playback/session.test.ts:1458` hardcodes `180_000 + 1_500 + 100`.
  Editing only `session.ts` leaves the viewer's end-of-track auto re-sync on the old estimate — the
  duplicated-constant class CLAUDE.md names.
  **What a session would do — and what will NOT work.** The obvious route is a dead end and is written
  down here so it is not rediscovered: the `[lyrics-sync] residual` series
  (`LyricsViewer.tsx:505`) **cannot measure this**. Its own comment says only same-track reads reach it,
  because "a residual is predicted-minus-actual position, and a track change destroys the prediction" —
  and this constant governs precisely the track-change transition. It is also `console.debug` only
  (nothing collects it, and only while the viewer is open), and `predicted` includes `leadMs` (20–80 ms),
  so its samples are not raw ack→apply lag either. A real measurement needs a purpose-built sample of
  ack→apply lag at a track boundary on the `remote` rung, then a value chosen against that distribution
  and OQ3(a) re-checked at the chosen width.
  *Trigger*: owner go, or a reproduced instance of OQ3(a) in the wild. Blocks nothing today.
  *On promotion to Active*: drop the archive pointer below — `scripts/check_workspace_invariants.py`
  rejects an Active row that references `docs/archive/done/`.
  Background → `docs/archive/done/rfcs/ARCH-playback-authority-convergence.md` (OQ3, OQ4).

- **CHORE-research-prompt-port-not-swap** (**legs 1–6 SHIPPED 2026-07-30; measurements remain**) — do **not** replace `album_research_v2` with v4 wholesale. Controlled RENAISSANCE comparison scored **v2 12/22, v4 12/22**, with complementary rather than strictly better coverage. v4 improved biography/primary-statement pressure but lost v2's explicit "do not import others' critical verdicts" protection and costs more tokens/wall time. The shipped approach ports the useful v4 pressure into v2, retains the no-verdict rule, adds liner-notes and sample-chain-depth requirements, injects catalog context, and intentionally keeps `PROMPT_VERSION=v2` so stored notes remain visible.

  Remaining measurements only:
  1. Re-run RENAISSANCE against the checked-in 22-item sheet + ONYX with `grep -ci izm = 0`; record score, wall clock, output length and **actual per-hop citation support**. Pass target = recover ≥3 of items 5/6/8/22 at ≤1.3× v2 wall clock.
  2. Generalisation test on one album not used to create the rules.
  3. First `[확인]` precision audit; no false-`[확인]` denominator exists yet.

  Highest-information measurement remains owner writing **one review from one research note** and marking used/unused material; the current prompt metrics are proxies because 80 notes have produced 0 completed reviews. Evidence → `docs/editorial/research-note-requirements.md` + `docs/reviews/measurements/2026-07-30-research-prompt-v2-vs-v4/`.

- **FEAT-ai-editorial-critique** (**draft; deferred**) — Phase 0 thin slice: backend-only AI editorial critic that runs the existing critique method over a draft + already-linked album DB facts, returning grounded Korean feedback + uncertainty/checklist markers, never rewriting the draft. Step 1 = local implementation + golden eval; Step 2 = infra JWT route + contract. UI, persistence, planner, publish gate and broader fact checking remain non-goals. Needs owner accept before Active.

  Open thread (from `FEAT-editor-buckit`, 2026-06-19) — on promotion: fold in the explicit two-stage editorial pipeline (nightly full-draft → critique pass), re-audit the stale "zero AI/LLM code" Current State, gate via `require_owner` rather than bare `require_cognito_token`, and convert its Secrets Manager references to SSM (`CHORE-secrets-ssm-migration`). → `docs/rfcs/FEAT-ai-editorial-critique.md`.

- **FEAT-genre-recommendation** (**Frozen; gated on review volume**) — related-review recommendation on `/review/{slug}` based on shared sub-genres + linked genre edges. Substrate is live, but there is not enough published review volume to rank meaningfully. Re-open after sufficient review/tag volume exists. Owner edge-authoring API remains lowest priority. → `docs/rfcs/FEAT-genre-recommendation.md`.

- **FEAT-blog-to-review-migration** — Step 1 `/blog → /review` prefix migration DONE + prod-live 2026-06-14. Only optional Step 2 remains: true HTTP 301 via the console-managed CloudFront Function if meaningful inbound `/blog` links accumulate. Static stubs already prevent 404s, so Step 2 is SEO-only. → `docs/rfcs/FEAT-blog-to-review-migration.md`.

- **CHORE-neuralwatt-credit-burn** (**opt-in path SHIPPED; default switch rejected by parity gate**) — NeuralWatt glm-5.2 routing exists for genre-heal, but identical input produced unstable K-Pop/idol classifications on an axis that writes `confidence=high` DB state. Default therefore remains `claude -p`; burn is deferred. Open owner decision: retry with a hardened idol-axis rubric or leave NeuralWatt opt-in only. Key location remains the owner's prior decision and should not be re-raised.

- **FEAT-bucket-identity** (**A DONE; B DONE; C subsumed; D audited + gated**) — Direction D's old "next concrete step" is stale because 4/5 proposed collection types already exist as dedicated non-bucket surfaces; only genre-review collections remain unbuilt. Review-based collections remain gated by published-review volume, and album-based public collections remain gated by owner curation/public-bucket evidence. Re-open only when the RFC's audit gates are met and re-measured. Existing proposals such as `/profile` landing tab, research-note deep link and in-place bucket-tab switch remain proposals, not active work. → `docs/rfcs/FEAT-bucket-identity.md`.

---

## Later (트리거 대기)

- **FEAT-multi-user-accounts** (**in-progress since 2026-07-07; all remaining work is owner-only**) — multi-user platform: Google+Kakao signup, public album ratings, per-user buckets, Last.fm/Spotify member listening, `LLMEngine`. Phases 0–4 + P3b/3c + library user-scope + 07-14 surface-audit remediation + profile-merge PR1–3 are SHIPPED & prod-verified. Read "Phase 4 SHIPPED" narrowly: the owner-central `LLMEngine` interface/CLI/API skeleton + usage metering exists, but **no caller is wired to the API engine yet**; the first user-facing AI call belongs to `FEAT-album-review-authoring`. Existing rating behavior remains unchanged. **Every remaining item needs the owner, not Claude**: launch gates G1/G2 (≥10 reviews by ≥5 non-owner users within 4 weeks of public launch), Google brand verification, Kakao production review, OAuth secret reissue, owner live-login `returnTo` observation, and the necessity-gated canonical member URL decision (`/members/?u=` vs `/members/[handle]`). Owner deferred launch work 2026-07-20; **do not re-prompt without a new trigger.** → `docs/rfcs/FEAT-multi-user-accounts.md`.

- **SEO-review-structured-data 첫 발행 검증** — implementation DONE 2026-07-19 and RFC archived. `Review` + `MusicAlbum` JSON-LD is already generated and locally validated. **Trigger = first production review publication** → run Rich Results Test once against the real published URL. → `docs/archive/done/rfcs/SEO-review-structured-data.md`.

- **FIX-nightly-draft-identity Phase B** (**planned; trigger-gated**) — the P0/Phase A problem was resolved 2026-07-27 with a dedicated nightly Cognito identity, draft-only coercion, owner-pinned grow, counted Phase-B trigger, and live E2E verification. Phase B adds multi-user post ownership, bucket-derived acting user, and read-side scoping only when any RFC §4 trigger fires. Watch `PHASE-B TRIGGER` in nightly logs. → `docs/rfcs/FIX-nightly-draft-identity.md`.

---

## Frozen (아이디어만, RFC 없음)

확장 기능 후보. 의향이 생기면 그때 RFC를 시작하며 지금은 작업하지 않는다.

- **FEAT-genre-autoheal — cloud heal** — only the cloud iTunes-only variant remains deferred. Local daily genre-heal and the on-demand request queue are already live. Blocker: the richer local S3 pass shells `claude -p` using subscription auth unavailable in Lambda, so any cloud-only baseline pass would need a distinct partial marker and must not suppress the later local LLM pass.

- **Per-genre exemplar albums** — start inside `definition_md` markdown; introduce structured linking only when an actual consumer requires it.
