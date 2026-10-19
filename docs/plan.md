# Plan

Active workspace tracker for cross-repo work. Each row carries `Scope / Order (if multi-repo) / Verification (local + prod smoke) / Rollback / Status`; RFC-backed entries collapse to a one-line pointer at `docs/rfcs/<id>-<slug>.md`. When a row finishes, drop it — `git log` and `docs/archive/done/YYYY-MM.md` are authoritative for history.

---

## Active

> **Owner priority override, 2026-10-15:** CHORE-research-model-evaluation is the first planned task, superseding the earlier planned order below. Existing emergency/security incidents still take precedence. The owner subsequently expanded the goal to joint acceptance criteria and iterative prompt validation; production adoption remains separate.

- **CHORE-research-model-evaluation** — **FIRST PLANNED PRIORITY; draft; research explicitly authorized 2026-10-15.** **2026-10-16: `acceptance-v1` frozen (Astra + Claude, 4 rounds) and the all-model pilot completed (both reviewers; harness confound recorded). Stage A-2 met 2026-10-16: anchors-v1 frozen (4 rounds, both CONFIRM FREEZE) and round manifest v1 frozen except the §6 manual and §7 floors. Stage B round 1 ran 2026-10-16 (P1 = pilot prompt + 7 converged amendments vs P0; 2 albums × 2 environments; 8 generations, 16 blind audits): **P1 does not advance** (FAILs in 3/4 outputs; worse than P0 in 2/4 cells; longer notes everywhere; 3 gate allegations unresolved, adjudication deferred by owner). Claude CLI lane found loading global user settings/hooks. **Round 2 PAUSED 2026-10-16** (owner-confirmed: P2 = P0 + 4 overlapping definition/deletion edits vs P0, same albums, 2 runs/cell, agreed-FAIL rule; Claude lane now `--safe-mode`): Claude 8/8 generated clean; Codex 4/8, then ChatGPT usage limit. **2026-10-18: limit lifted early; owner approved an early resume (ROUND.md §11, Codex CLI now 0.163) — 4/4 Codex `-resume` runs succeeded, all 16 cells have an outcome.** **2026-10-18: round 2 reviewed — P2 does not advance** (agreed FAILs on 2 Claude-lane P2 outputs; worse than P0 in both Claude CLI cells; Codex · P2 0 FAILs; length 1.098×). **2026-10-20: round 3 (Gemini Rights only; P0 / P3 / P3G = P3 + Genius-annotation block) — neither advances, on length only** (Claude lane P3: FAILs 2 vs P0 5, no agreed FAIL, but 1.248× length; P3G 1.303×). **Owner 10-19: Codex producer lane discontinued (cost), Astra kept as a no-web reviewer of Claude-lane outputs only.** Owner 10-20: no annotation arm in round 4; D6 judged by the Claude reviewer alone. **2026-10-20: round 4 (Claude lane only; P0 vs P4 = P3 − edit 3 + 3 overlap points + a whole-note length cap; 3 runs/cell) — P4 does not advance on one orchestrator-confirmed D5 FAIL (a dropped "tentative"), but length is solved (1.005×), FAIL marks 3 vs P0 5, defect 2 eliminated.** Claude reviewer: 0 D6 FAILs in 37 audits, so D6 is unmeasured under the current design. **2026-10-20: round 5 (Claude lane only; P0 vs P5 = P4 + role strings original-first, source uncertainty markers kept, exclusive/negative statements checked; 3 runs/cell) — P5 advances under the round rule after the owner dismissed both G4 allegations: FAIL marks 3 vs 9, length 0.879×, no confirmed single FAIL, 0 dropped uncertainty markers, defect 4 down for the first time.** Not the Stage B gate: D6 is still unmeasured (Claude 0 D6 FAILs in 44 audits; sentinel control failed by both reviewers), D7 not assessed, and change 3 did not stop unchecked "없음" claims. Next: owner decides D6 measurement / next step — `stage-b/round5/RESULTS.md`.** **2026-10-20 D6 instrument check (`stage-b/d6-measurement/`): owner adopted R-a–R-c (authoritative row = distributor/label/store credit listing or liner notes; secondary-only credits with an accessible row take the FAIL route; narrowing defined) for development rounds, applying from round 6. 16 blind Claude audits with a frozen Qobuz row + 3 planted mutants of P5 r3: role-drop and guessed-credit mutants detected 2/2 (old packet 0/3), negative control PASS, sentinel FAIL for the first time; the edition mutant (Sped Up in a coverage count) was seen but scored under D1/D2 → predeclared verdict: instrument not usable as designed. Owner 10-20 chose (a): D6 goes to §6 owner calibration (Stage C); development rounds report it descriptively under R-a–R-c, not as a round-rule gate. `stage-b/d6-measurement/RESULTS.md`.** **2026-10-20: round 6 (Claude lane only; P0 vs P6 = P5 + the exclusive/negative check restated at the ③ cells / lines under ③ and in ⑤'s selective-transcription rule; reviewer packets carry R-a–R-c + the re-checked Qobuz row; D6 descriptive) — P6 does not advance on one orchestrator-confirmed Claude D4 FAIL** (r2 quoted a line received in a multi-link search summary under a link that does not contain it). Otherwise: FAIL marks 2 vs 8, length 0.813×, 0 contradicted absence values in P6 tables (P0 1), no open allegation. D6 under R-a–R-c tracks one fact: only the run that opened the Qobuz row is BORDERLINE (P0 3/3, P6 2/3 FAIL; sentinel FAIL for both reviewers). P5 stays the development base. Next: owner picks the next step — `stage-b/round6/RESULTS.md`.** **2026-10-20: round 7 (P7 = P6 + search-summary attribution; owner-confirmed with P6 as base, fidelity check both CONFIRM FREEZE) was stopped by the owner after 3 of 6 generations, before any review — no verdict. Owner: dev rounds have diminishing returns; stop and move to Stage C with a lighter procedure. Next: Stage C design — `stage-b/round7/RESULTS.md`.** Complete a prompt that passes jointly designed **GPT-6 Astra + Claude** criteria for efficient evidence collection useful to a music critic; structure/outline/expression may vary. Preserve the revised-prompt all-model pilot, agree measurable thresholds, iterate bounded prompt comparisons, then verify on held-out albums and critic-use tasks. Subscription models only; separately billed Fable excluded. Production adoption remains separate. → `docs/rfcs/CHORE-research-model-evaluation.md`. <!-- rfc: docs/rfcs/CHORE-research-model-evaluation.md | status: draft -->

- **FEAT-public-surfaces-before-first-review** — **accepted 2026-10-17; Steps 1–2 deployed 2026-10-17 (front #472, #473; prod smoke 32/0); remaining: Step 0 owner action (display name), then Status done needs owner approval** (from the 2026-10-16 front UI/UX audit §4, owner decisions D1/D3). While 0 평론 exist: hide nav items built from 평론 (Reviews, Best New Music, Canon) and add a separately labelled home rail of the owner's 평가; Canon/hero stay 평론-only. Step 0 is an owner action (set a display name, handle unchanged). Front-only. Outside this RFC, audit §3 step 2: the overlay Back (D2) shipped in front #477 and the login-intent sheet (S5) in front #479, so that step is complete → `docs/reviews/2026-10-16-front-uiux-audit.md`. → `docs/rfcs/FEAT-public-surfaces-before-first-review.md` <!-- rfc: docs/rfcs/FEAT-public-surfaces-before-first-review.md | status: accepted -->

- **FEAT-lyrics-chat** — **live 2026-10-09**: translation queue runs on a local GPT worker on the owner's Mac (ChatGPT Plus sign-in, `gpt-5.6-sol`, `store=false`; launchd every 60 s; budget 300/UTC day, 3 concurrent inferences). **2026-10-18 (owner request):** a plan usage limit no longer stops the worker (hourly GPT probe), and during the wait an owner-enabled Claude fallback (`opus`, 50/day, refunded failures) keeps the queue moving — RFC _Usage-limit fallback_. **Open (observe):** first fallback night (refusal rate, Claude usage) — not yet: GPT recovered 10-18 16:39 KST, 0 fallback calls as of 10-19, measured at the next limit event; plan usage vs. Plus allowance. First-days measurements (0 refusals in 298) → the RFC. [Design, architecture, delivery record](rfcs/FEAT-lyrics-chat.md). <!-- rfc: docs/rfcs/FEAT-lyrics-chat.md | status: draft -->

> Open decisions, gates and observations only. Shipped detail lives in `git log`, in each RFC, and in
> `docs/archive/done/`. A row that has nothing left but a status promotion is not Active — close it.

> **Owner priority, 2026-09-28:** reconcile progress → home lyrics entry and automatic next-track
> lyrics → other lyrics operational gaps → validate real user journeys. Existing P0/security
> incidents take precedence. This is planning priority, not runtime implementation approval.

- **OPS-project-stabilization** — **in-progress (Step 2A) since 2026-09-30 (owner); previous first planned priority, superseded by the 2026-10-15 override.**
  <!-- rfc: docs/rfcs/OPS-project-stabilization.md | status: in-progress -->
  Steps 1, 2B, 2C and 2D are closed (record per step in the RFC; 2C closed 2026-10-19 after the
  refresh re-fired on its own at 24 h). **Step 2A** — home playback discovery with
  direct lyrics, and automatic next-track lyrics — is deployed in all three parts (front #447, #448,
  #449, follow-ups #450, #451, #453) and the viewer cases passed the 2026-10-06/07 real-device run;
  phones are untested. Lambda concurrency raised to 1000 (closed 2026-10-20). **Next:** owner runs
  the 2A Exit phone/member checklist P1–P6 (P3 settles item 4), then 2A Exit. Step 3: inspect real
  user journeys.
  → `docs/rfcs/OPS-project-stabilization.md`

- **FEAT-lyrics-listening-experience** — in-progress; **Steps 1–4 complete and production-verified; Step 5 deployed and running but NOT complete** (2026-09-30 audit).
  <!-- rfc: docs/rfcs/FEAT-lyrics-listening-experience.md | status: in-progress -->
  Step 4 delivery, its security review, and the measurements that sized Step 5 → the RFC. Step 5
  shipped 2026-09-18; *Step 5 delivery* and the 2026-09-30 audit in the RFC are what this row tracks.
  - **Back-catalogue ingest and the 24 h refresh are live and verified** (worker #125,
    2026-10-18; OPS Step 2C closed 2026-10-19). The refresh re-fired on its own at 10-19 08:39Z.
    Back-catalogue drained 10-18 13:39Z: follow jobs 863 resolved, 372 below the popularity gate
    (resting 30 days), 0 `album_not_in_catalog`. → `OPS-project-stabilization`
    *Step 2C execution record (2026-10-19)*.
  - **Owner decisions taken 2026-10-20:** catalog cap 8,000 → 12,000 (worker #126, deployed 10-19; ~4 months at
    ~320 albums/week), and Michael Korstick excluded from follow discovery (913/925 `not_found`,
    0 translated; manual edge kept; 53/53 jobs cancelled on the next sync). → RFC *Owner decisions (2026-10-20)*.
  - **Step 5 re-smoked 2026-10-20 (read-only, after worker #125): every case production can show
    passes.** New-release pickup works in steady state: the refresh re-opened 35 artists at 10-18 08:24Z
    and again at 10-19 08:39Z with no new follow. Follow jobs: 816 resolved, 369 below the popularity
    gate, 0 `album_not_in_catalog`. Control: prod smoke 32/0, excluded artists at 0 demand. **Still
    not verified:** joint unfollow, re-import and a grant without the scope need the owner; multi-page
    follows and enumeration retry are suite-only. "Production-verified" stays withdrawn until the owner
    decides. → RFC *Step 5 smoke (2026-10-20)*.
  - **Follow metrics in CloudWatch:** visible since worker #124 (2026-10-18 07:57Z); confirmed by the
    10-20 re-smoke (3,106 `[INFO]` lines in 50 h). INFO is raised for `worker.*` only.
  - **`infra/lambda.tf` kill switches are unapplied.** The live Lambda has only the console-set
    `LYRICS_FOLLOW_DEMAND_ENABLED=true`, so `terraform plan` shows 1 change. Needs a human apply.
  Carry the Step 1 cold-start Spotify 404/browser-fallback observation. → `docs/rfcs/FEAT-lyrics-listening-experience.md`.

- **SEC-system-hardening** (`docs/rfcs/SEC-system-hardening.md`, accepted) — main governance, keyless
  <!-- rfc: docs/rfcs/SEC-system-hardening.md | status: accepted -->
  deploys, one JWT verifier. **Steps 1–6 are all shipped and production-verified.** Full per-step
  record → the RFC and `git log`.

  **What is still open — one P0 and two questions, all the owner's (Step 5 follow-ups 1–5 are done):**
  - **The AWS root account access keys** (`AccountAccessKeysPresent = 1`, re-verified 2026-09-03; both
    keys `Active`). Root keys can only be deleted by signing in as root with MFA. Per-key reading → the
    RFC, Step 3d.
  - **Should `workspace-check` become a required check?** The workspace repo gained a `pull_request`
    workflow in ws #948 and it has passed on eleven PRs; its ruleset still carries only `main-protection`.
    Making it required is an open item, not a decision already taken.
  - **Should the front `e2e` check become required?** Step 5 follow-up 5 shipped it advisory on
    2026-10-18 (front #478): 7 Playwright tests over 5 mocked-boundary journeys, `pull_request` only,
    `retries: 0` so a flake shows red. Evidence so far: green on 2 PR pushes. Promote only on repeated
    PR evidence; the decision is the owner's. → the RFC, *Step 5 follow-ups*, item 5.

---

## Owner-only (nothing here is Claude's to do)

Items with no remaining implementation, kept visible because dropping them would lose the only record.

- **Lyrics match correction: two first-use checks.** `FEAT-lyrics-match-correction` closed 2026-10-18
  (all steps shipped, worker #112–#121, backend #189/#190, front #469/#474). Not yet seen with a live owner
  session: the owner's first pick-and-lock through the candidate panel, and the owner's first look at the
  report queue. → `docs/archive/done/rfcs/FEAT-lyrics-match-correction.md`
- **Set the `To Review` bucket back to 비공개** (프로필 → 버킷 탭 → 공개 설정). It is the only public bucket, so
  this empties `/collection`. Carried over from `FEAT-bucket-identity`, closed 2026-10-18 →
  `docs/archive/done/rfcs/FEAT-bucket-identity.md`.
- **AWS root account access keys** — see `SEC-system-hardening` above. Requires a root sign-in with MFA.
- **BEST NEW ALBUM toggle: one live click-test.** Shipped 2026-08-25 (backend #161 `a75b943`, front #424
  `9e34228`, ws #933 `2784f97`) — owner-only mark/unmark of `albums.best_new` directly from
  `AlbumRatingBlock`. Everything verifiable without an owner session was verified (prod smoke 19/19, the
  public aggregate carrying `best_new`, and a 403 for a non-owner token on the new route). The actual
  owner-success toggle path was **not** verified, because it needs a live owner Cognito session rather
  than the smoke member account. One click as the owner closes it. Detail →
  `docs/archive/done/2026-09.md`.
- **FEAT-youtube-playback-provider** — Milestone A shipped and production-verified 2026-09-06 (front
  #444). Owner-only: rotate and API-restrict SSM `/myblog/youtube` (OQ6), and read the actual daily
  `search.list` quota in Console. RFC Status stays `in-progress` pending an explicit owner decision.
  **Milestone B remains closed: no design or code before Phase 0-B GO.** → `docs/rfcs/FEAT-youtube-playback-provider.md`
- **FEAT-multi-user-accounts** (in-progress since 2026-07-07) — Phases 0–4 and follow-ups shipped and
  prod-verified; no service calls `ApiEngine` yet (re-verified 2026-09-30). **Every remaining item needs
  the owner**: launch gates G1/G2 (≥10 reviews by ≥5 non-owner users within 4 weeks of public launch),
  Google brand verification, Kakao production review, OAuth secret reissue, owner live-login `returnTo`
  observation, and the canonical member URL decision (`/members/?u=` vs `/members/[handle]`; the owner
  and smoke user both have prebuilt static pages alongside the runtime `?u=` view). Owner deferred
  launch work 2026-07-20; **do not re-prompt without a new trigger.** → `docs/rfcs/FEAT-multi-user-accounts.md`

---

## 2026-07-23 감사 파생 작업 (남은 것 = P2뿐)

> Source: `docs/reviews/2026-07-23-current-state-audit.md`.
>
> Only verified/accepted findings remain here. P0/P1 work is complete and archived.

### P2 — 실사용자 증거 후

- **CHORE-dep-reproducibility** — Lockfiles done 2026-08-29 (`SEC-system-hardening` Step 5 follow-up 3: `requirements.lock` is the bundle input on backend, music and worker); the SHA-to-tag half is superseded (SHA pins are the convention). **Residual:** `myblog-shared-db` is still built on the runner from an unpinned build backend (needs a hashed wheel), and the wildcard `requirements.txt` inputs (`SQLAlchemy==2.*`, `psycopg[binary]==3.*`, bare `fastapi`/`boto3`) still mislead CVE search. Trigger: another deployment 500 caused by dependency drift.

- **DISCOVERY-flow** (**hypothesis; rejected for now**) — potential `signup → import → Buckit → publish → discovery` investment. Current evidence remains insufficient: published content, other-user activity, and public collections are too sparse for discovery investment to be meaningful. Re-evaluate only after real-user + content evidence. What the product's core flow should be remains an owner strategy decision.

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

- **CHORE-research-prompt-port-not-swap** (**legs 1–6 SHIPPED 2026-07-30; measurements remain**) — `album_research_v2` keeps the useful v4 pressure ported in, retains the no-verdict rule, and keeps `PROMPT_VERSION=v2`. The owner-prioritized revised-prompt/model experiment is tracked separately in `CHORE-research-model-evaluation`. Remaining measurements only:
  1. Re-run RENAISSANCE against the checked-in 22-item sheet + ONYX with `grep -ci izm = 0`; record score, wall clock, output length and **actual per-hop citation support**. Pass target = recover ≥3 of items 5/6/8/22 at ≤1.3× v2 wall clock.
  2. Generalisation test on one album not used to create the rules.
  3. First `[확인]` precision audit; no false-`[확인]` denominator exists yet.

  Highest-information measurement remains owner writing **one review from one research note** and marking used/unused material. Evidence → `docs/editorial/research-note-requirements.md` + `docs/reviews/measurements/2026-07-30-research-prompt-v2-vs-v4/`.

- **FEAT-ai-editorial-critique** (**draft; deferred**) — Phase 0 thin slice: backend-only AI editorial critic that runs the existing critique method over a draft + already-linked album DB facts, returning grounded Korean feedback + uncertainty/checklist markers, never rewriting the draft. Step 1 = local implementation + golden eval; Step 2 = infra JWT route + contract. UI, persistence, planner, publish gate and broader fact checking remain non-goals. Needs owner accept before Active.

  Open thread (from `FEAT-editor-buckit`, 2026-06-19) — on promotion: fold in the explicit two-stage editorial pipeline (nightly full-draft → critique pass), re-audit the RFC's stale Current State (written 2026-06-06), and gate via `require_owner` rather than bare `require_cognito_token`. → `docs/rfcs/FEAT-ai-editorial-critique.md`.

- **FEAT-genre-recommendation** (**Frozen; gated on review volume**) — related-review recommendation on `/review/{slug}` based on shared sub-genres + linked genre edges. Substrate is live, but there is not enough published review volume to rank meaningfully. Re-open after sufficient review/tag volume exists. Owner edge-authoring API remains lowest priority. → `docs/rfcs/FEAT-genre-recommendation.md`.

- **CHORE-neuralwatt-credit-burn** (**opt-in path SHIPPED; default switch rejected by parity gate**) — NeuralWatt glm-5.2 routing exists for genre-heal, but identical input produced unstable K-Pop/idol classifications on an axis that writes `confidence=high` DB state. Default therefore remains `claude -p`; burn is deferred. Open owner decision: retry with a hardened idol-axis rubric or leave NeuralWatt opt-in only. Key location remains the owner's prior decision and should not be re-raised.

---

## Later (트리거 대기)

- **FEAT-album-review-authoring** (accepted) — **평가 = rating** (public star rating + one-line
  comment), **평론 = review** (editor long-form review); Korean UI must not use "리뷰" for either.
  Steps 1, 2 and 4 are shipped and prod-verified; the usage gate is retired (owner 2026-09-03). The
  gate retrospective, the rating/memo measurements and the E-5 sweep are recorded in the RFC.
  **Step 3 (owner-only AI distillation) — DEFERRED. Do not start it, and do not tune OQ3's default
  prompt, until the owner sets a new resumption condition.** Its deferral evidence has an erratum
  (the "owner writes no text" measurement was taken on a field capped at 60 chars; the long-form text
  lives in the bucket memo) recorded under OQ13 in the RFC; the decision is the owner's.
  **Step 5 (conditional general AI opening) — DEFERRED**, dependent on Step 3. AI behaviour, if
  Step 3 ever resumes, remains distillation only. → `docs/rfcs/FEAT-album-review-authoring.md`

- **SEO-review-structured-data 첫 발행 검증** — implementation DONE 2026-07-19 and RFC archived. `Review` + `MusicAlbum` JSON-LD is already generated and locally validated. **Trigger = first production review publication** → run Rich Results Test once against the real published URL. → `docs/archive/done/rfcs/SEO-review-structured-data.md`.

- **FIX-nightly-draft-identity Phase B** (**planned; trigger-gated**) — the P0/Phase A problem was resolved 2026-07-27 with a dedicated nightly Cognito identity, draft-only coercion, owner-pinned grow, counted Phase-B trigger, and live E2E verification. Phase B adds multi-user post ownership, bucket-derived acting user, and read-side scoping only when any RFC §4 trigger fires. Watch `PHASE-B TRIGGER` in nightly logs. → `docs/archive/done/rfcs/FIX-nightly-draft-identity.md`.

- **DATA-tracked-release-day-ingest** (**decision deferred by the owner 2026-10-17 — measure first; trigger = 2026-11-07**) — question: should tracked artists' new releases bypass `ALBUM_POP_MIN` (20) so they reach the catalog (cover, add-to-bucket, highlights) on release day? Today they arrive 1–3 days late, and front #475 opens them on click. Prod 2026-09-17..10-17: 13 tracked releases were confirmed and 13/13 are in `albums`. Arrival: day 0 1, +1–3 days 9, +4 days or later 3. Two are iTunes-only with no Spotify id, and a bypass cannot help those. That 13/13 is survivorship: never-announced Spotify releases that stay below 20 leave no row. [worker #119](https://github.com/hyuntohoon/myblog_worker/pull/119) adds `tracked_enqueue_gate_skipped` / `tracked_confirm_gate_skipped` plus WARNING logs with id and popularity, with no behaviour change. On the trigger date, read the `album_ingest summary` / `tracked release below` lines in CloudWatch, check each held id against `albums`, and bring the owner the count of releases that never got in. If the owner then approves a bypass, it must be bounded to the confirm window: the enqueue gate has no date window beyond `INGEST_SINCE`, so an unbounded bypass dumps the tracked artists' post-June back-catalogue on the first tick. It also needs its own per-tick cap so it cannot crowd the shared `MAX_ENQUEUE_PER_TICK` 60. Do not change `ALBUM_POP_MIN` / `MAX_CATALOG_ALBUMS` without that decision.

---

## Frozen (아이디어만, RFC 없음)

확장 기능 후보. 의향이 생기면 그때 RFC를 시작하며 지금은 작업하지 않는다.

- **FEAT-automation-model-controls** — expose model selection on the owner's automation page only where an executor supports it, distinguishing the requested model, the saved automation setting and the observed execution model (never inferred from the Work chat composer). Split from FEAT-automation-admin OQ2 (2026-10-17). No executor supports it, and the trigger it was backlogged on (Work Cloud, ws #1022) was closed unmerged on 2026-10-16. Origin: `docs/archive/done/rfcs/FEAT-automation-admin.md` (Target state, OQ2).

- **FEAT-genre-autoheal — cloud heal** — only the cloud iTunes-only variant remains deferred. Local daily genre-heal and the on-demand request queue are already live. Blocker: the richer local S3 pass shells `claude -p` using subscription auth unavailable in Lambda, so any cloud-only baseline pass would need a distinct partial marker and must not suppress the later local LLM pass.

- **Per-genre exemplar albums** — start inside `definition_md` markdown; introduce structured linking only when an actual consumer requires it.
