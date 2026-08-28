# Plan

Active workspace tracker for cross-repo work. Each row carries `Scope / Order (if multi-repo) / Verification (local + prod smoke) / Rollback / Status`; RFC-backed entries collapse to a one-line pointer at `docs/rfcs/<id>-<slug>.md`. When a row finishes, drop it — `git log` and `docs/archive/done/YYYY-MM.md` are authoritative for history.

---

## Active

- **SEC-system-hardening** (`docs/rfcs/SEC-system-hardening.md`, draft) — main governance, keyless
  <!-- rfc: docs/rfcs/SEC-system-hardening.md | status: draft -->
  deploys, one JWT verifier. Steps 1–2 (rulesets on all six repos) and Step 4 (both Cognito guards
  hardened + real signed-token vectors) shipped 2026-08-26; Step 3b (front OIDC pilot) in flight.
  Step 3b (front OIDC), **Step 3c (backend/music/worker OIDC — all three production-verified
  2026-08-28)** and Step 5 (polyrepo assessment — verdict **KEEP POLYREPO**) also done. **No AWS
  credential secret exists in any of the six repositories**, and `github-actions-deploy` has zero
  access keys.
  **Carries a P0 the owner must close personally**: the AWS *root account* access key is the
  credential in `myblog_front`'s Actions secrets, and `myblog_front` is a public repository. Root
  `access_key_2` was rotated 11 s before that secret was last set and was last used against
  CloudFront during a front deploy; a second root key, `access_key_1`, is also active and unused
  since 2025-12-10. Root keys can only be deleted by signing in as root with MFA, so Step 3d-5 is
  not Claude's to perform — and deleting the repo secrets does **not** retire them. Everything else
  in Step 3d is done. Remaining: **the two root keys (owner)** and Step 6 (verifier consolidation).
  Owner-directed delivery hardening follow-ups are sequenced as independent PRs: **workspace PR
  CI/invariants DONE 2026-08-28** (workspace #948 + shared_db #78) → candidates GET/POST side-effect
  split → Python dependency reproducibility → per-service shared_db pin invariants → a small
  non-required Playwright golden suite.

> 2026-08-10 reconciliation pass: checked every row below against code/tests/deployment/RFC acceptance
> criteria (not just prior labels). Six RFCs whose every step was shipped+verified, with nothing left but
> a ceremonial status promotion, were promoted to `done` and archived — `docs/archive/done/rfcs/`
> (`ARCH-bucket-album-modal-unification`, `ARCH-entity-interaction-v2`, `FEAT-playback-bucket-player`,
> `FEAT-member-player`, `FEAT-lyrics-sync-precision`, `ARCH-overlay-modal-isolation`). This is a
> self-promotion under CLAUDE.md rule #7's explicit-session-approval exception (owner's own reconciliation
> instructions, this session) — flagged prominently in the session report; reopen any of them freely if
> that judgment call was wrong. Owner-only observation items that don't gate anything stayed inside their
> archived RFC rather than lingering here. `FEAT-multi-user-accounts` moved to **Later** (all-owner-only
> remaining work, explicit "don't re-prompt"). `DATA-multidisc-track-order` and `DATA-release-noise`'s
> `(c)` moved to **Backlog** (draft/unclear-dependency, not concretely startable today).
> `FIX-lyrics-primary-artist + FIX-isrc-backfill` dropped entirely — implementation complete, remaining
> items were pure non-gating observation with no RFC to archive; detail → `docs/archive/done/2026-08.md`.

- **ARCH-global-playback-experience** (**in-progress; accepted 2026-08-11; Steps 1+2+3+4 SHIPPED + prod-verified**,
  <!-- rfc: docs/rfcs/ARCH-global-playback-experience.md | status: in-progress -->
  front #398 `0d4f525` 2026-08-11, #405 `55ccd47` 2026-08-15, backend #156 `dd627bd`
  + ws #907 `a18d940` + front #407 `afe783c` + front #408 `43cb425` 2026-08-15 + front #409 `20669c34`
  2026-08-16)
  — closes the gaps
  `FEAT-playback-bucket-player`
  (done) and `ARCH-entity-interaction-domain-audit` Step 3 (3a/3b/3c done) left open, verified rather than
  assumed: `session.ts` now owns capability tier/device-list/shuffle/repeat/volume/liked/reconnect
  (previously `NowPlaying` kept them local "by design" per `component-map.md`'s own state-owner
  registry — that registry now needs updating to reflect Step 1), `readLivePlayback()` is single-flight
  (a single `MYBLOG_PLAYBACK_CHANGED` used to fan out to 3 uncoordinated live reads), live lyrics now
  open from any route (Step 2 — see below), and the Playback Bucket's queue view still has no per-row
  artwork/reorder/play-all/summary — artwork needs one small, additive backend field
  (`Backend_TrackBrief.cover_url`, does not exist today; Step 3's scope). No new player, queue, or
  Home-specific playback state. Step 1 verification: `pnpm test` 60/60 files (623 tests) green, `pnpm
  lint` clean, `pnpm exec astro check` 0 errors — all independently re-run, not just self-reported by the
  implementing agent. A real regression was found and fixed during review before merge:
  `resolveCapability()`'s first draft permanently locked `capabilityTier` at `'fallback'` after any
  transient first-mint failure for the rest of the tab session (this codebase's `ClientRouter` keeps
  `session.ts`'s module state alive across route transitions while `NowPlaying` remounts per route) —
  fixed to dedupe-only semantics matching the original per-mount re-resolve behavior. Real-browser CDP
  verification of the live-Spotify-specific convergence behavior (shuffle/device across both surfaces,
  lock-screen Media Session) was not performed — no `.env` access in the isolated worktree — merged on
  explicit owner instruction accepting unit/lint/astro-check coverage as sufficient for this step; worth a
  live spot-check when convenient. Production smoke 19/19 passed post-deploy (quoted on front #398).
  **Step 2 shipped 2026-08-15** (front #405, `55ccd47`): `ENT_OPEN_LIVE_LYRICS`'s listener relocated from
  `SelfDashboard` (dashboard-scoped) to `PocketBuckit.tsx` (already layout-mounted app-wide, already the
  event's dispatch source via `PocketTray`) — 가사 now opens from Home/`/search/`/artist hubs, not just
  the member dashboard. `SelfDashboard` keeps its own direct-call live-lyrics path (`NowPlaying`'s 가사
  tap) untouched, so the two entries can't double-open on the dashboard route. Also fixed a real bug the
  relocation surfaced: `LyricsViewer`'s `.lyv-*` CSS lived in `member/layout.css` (loads only via
  `member.css`, dashboard + `/collection` only) — mounting from `PocketBuckit` would have shipped the
  viewer with zero styles on every non-dashboard route, the same `member.css` trap already hit 4 times
  (`.lf-artist-link`'s prior "MOVED OUT" fix in the same file). Extracted to `src/styles/lyricsViewer.css`,
  self-imported by `LyricsViewer.tsx`, mirroring the existing `modal.css`/`pocket.css` precedent. `pnpm
  test` 635/635, `pnpm lint` clean, `pnpm exec astro check` 0 errors; real-browser CDP against a local dev
  server confirmed the overlay opens fully styled on Home and `/search/` and via the layout-level listener
  on the dashboard route, exactly one instance each time, ✕ close works. A live authenticated prod
  click-through was not additionally performed (pure frontend relocation, no backend/data dependency —
  see front #405's PR comment). Production smoke 19/19 passed post-deploy (quoted on front #405).
  **Step 3 shipped 2026-08-15** (backend #156 `dd627bd`, ws #907 `a18d940`, front #407 `afe783c`):
  `Backend_TrackBrief` gains a nullable `cover_url`, resolved server-side in `_track_brief()` off the
  track's own `album_id → albums.cover_url` (mirroring `_album_brief()`'s pattern) — Open question 4
  resolved this session, owner picked the recommendation over exposing `tracks.spotify_id` for a
  client-side Spotify resolve. `list_buckets()`'s eager-load gained `Track.album` (`lazy="select"` by
  default) alongside its existing `Track.artists` chain to keep `GET /api/buckets` at zero added
  queries — a real N+1 a review caught before merge. Backend `pytest` 664 passed + real-DB integration
  suite (Neon test branch) 83 passed, including two new query-count tests proving no N+1. `openapi.json`
  diff exactly one field, `api.gen.ts` regen exactly one field, no component changes (unused field until
  Step 4). Production smoke 19/19 passed, plus a targeted authenticated `GET /api/buckets` check showing
  `cover_url` live on every track/playback row (quoted on backend #156).
  **Step 4 split 2026-08-15 — its stated second prerequisite does not hold.** Before starting, a direct
  grep against `myblog_front` `origin/main` found `ARCH-buckit-navigation-shell` Step 1's
  `BucketDetailShell`/`playback_queue` slot does not exist — superseded again by front #402/#403/#404
  (see that RFC's row above). **Step 4 panel-enhancement half shipped 2026-08-15** (front #408,
  `43cb425`): `PlaybackQueue` gains per-row artwork (fixed a real bug in the same pass — `lib/buckets.ts`'s
  `mapItem()` never actually read the new `cover_url` field for track/playback rows, always falling
  through to the null album relation), a summary header (`N곡 · MM:SS 총 재생 시간`, degrades to `—`
  on any unknown-duration row), a 전체재생 action, and pointer-drag + keyboard reorder — scoped to the
  full queue view only, persisted via the existing `PUT /api/buckets/reorder`. `pnpm test` 643/643 (4
  new), `pnpm lint` clean, `pnpm exec astro check` 0 errors. Real-browser CDP via an `initScript`-stubbed
  `fetch` (no local backend/DB in this environment, and the local dev server hitting prod directly is
  CORS-blocked) confirmed artwork, the summary degrade, play-all, and both pointer-drag and keyboard
  reorder on desktop, plus touch-drag on a 390×844×3 mobile emulation. **Owner decisions 2026-08-15,
  same day both blockers resolved:** the second mount-point half would target the new
  `ARCH-buckit-inline-navigation` RFC's `variant` branch (was deferred against the retired
  `BucketDetailShell` slot); **Open question 1 resolved** — owner picked the always-visible bar after
  seeing Steps 1–4 shipped, so **Step 5 is unconditional and also unblocked**, queued after Step 4's
  second half. **Step 4 fully shipped 2026-08-16**: the second mount-point half was delivered as
  `ARCH-buckit-inline-navigation` Step 1 (front #409, `20669c34`, now archived) —
  `BucketInlineContent` now renders
  `PlaybackQueue` inline in My Buckit for the Playback Bucket instead of the manual tile grid; verified
  via CDP against the real prod queue (13 tracks) plus one CSS-scoping bug (`.pb-scope`) found and fixed
  in the same pass. **Step 5 shipped 2026-08-16** (front #410, `379b6f1`) — the persistent compact
  playback bar (Open question 1's option b): a new `PlaybackPersistentBar` (56px, identity + transport)
  mounted inside `PocketBuckit`'s existing layout-level root, visible whenever `session.ts` reports
  `currentItemId != null || external != null`, independent of Pocket's own open/closed state; reuses
  `PlaybackIdentity`/`PlaybackTransport` verbatim, click opens the Playback Bucket's existing mini drawer
  via the same `usePocket().openDrawer` path the tray's own tile already uses — no new player logic, no
  new queue. `.site-shell` reserves the bar's height via a `--pb-bar-h` custom property, the same
  reservation-contract shape as the existing `--pbp-dock-w`. `pnpm test` 87/87 in the playback/pocket-scoped
  suite (full-suite run hit unrelated system-load timeout flakes in `BucketBoard.test.tsx`/
  `CatalogAlbumCardAdapter.drag.test.tsx` — both confirmed passing in isolation, not touched by this
  diff), `pnpm lint` clean, `pnpm exec astro check` 0 errors. Real-browser CDP via an `initScript`-stubbed
  `fetch` (no local backend in this environment) confirmed the bar's identity/transport render correctly,
  content reserves space with no overlap on desktop and 390×844×3 mobile, and click opens the Pocket tray
  (`setOpen(true)`, `openDrawer` no-ops gracefully when the account has no Playback Bucket yet). **Scope
  decision made this step**: the RFC's Tests section left one detail open — a possible new
  `scripts/smoke.sh` check ("bar visible on `/`"). `smoke.py` is a pure API-level (boto3/HTTP) harness
  with no browser rendering, so no literal DOM check was added; deferred to a one-time authenticated CDP
  click-through against prod. Production smoke 19/19 passed post-deploy (quoted on front #410). **This
  was the RFC's last step — all 5 steps now shipped.** →
  `docs/rfcs/ARCH-global-playback-experience.md`.
- **BEST NEW ALBUM toggle from the rating surface** — shipped 2026-08-25 (non-RFC, single session,
  <!-- rfc: none -->
  owner explicitly chose to skip an RFC for this — no schema change). Owner-only mark/unmark of the
  existing `albums.best_new` column (introduced by the archived `FEAT-writer-lowfreq-redesign`) directly
  from `AlbumRatingBlock`, without opening the post editor — a second entry point onto the same column
  the post editor's `subject_best_new` already writes. Traced `content_sync.py` / `publish_service.py` /
  `post_service.py` first to confirm publish/sync never unconditionally overwrites the column (only an
  explicit `subject_best_new` value from the owner-only `/api/posts` write does), so the two paths don't
  fight — last-writer-wins between them is the same as it was before this change. New
  `PUT /api/reviews/albums/{album_id}/best-new` (`require_owner`); `best_new` added to the public rating
  aggregate; new API Gateway route, `terraform apply` run this session (1 add / 0 change / 0 destroy).
  `myblog_backend` #161 `a75b943`, `myblog_front` #424 `9e34228`, ws #933 `2784f97`. Backend `pytest` 683
  passed / 170 skipped (all skips are the standing `TEST_DB_URL not set` Neon-test-branch fallback, not
  introduced here); front `pnpm lint` / `astro check` / `pnpm test` all green (710/710).
  **Process gap hit again**: contract+infra-touching change, and `reviewer` is still missing from the
  Agent roster (same gap as the `FEAT-album-rerating` follow-on above and `~/.claude/myblog-rfc-chain.json`'s
  A11Y-chain observation, 2026-08-16/19) — this time flagged to the owner mid-session rather than merged
  silently; owner chose to substitute an independent `general-purpose` review following the `reviewer.md`
  brief verbatim (✅ Pass, two cosmetic nits fixed) plus the `security-review` skill (no findings). Prod
  smoke: baseline `scripts/smoke.sh prod` 19/19, plus a targeted check confirming `best_new` on the public
  aggregate and a 403 for a non-owner token on the new route (quoted on all three PRs). **Not verified**:
  the actual owner-success toggle path, since that needs the live owner Cognito session rather than the
  smoke test member account — recommend one live click-test as the owner.
- **FEAT-album-review-authoring** (**accepted; Steps 1+2 SHIPPED + prod-verified**) — album **평가 = rating**(public star rating + one-line comment), **평론 = review**(editor long-form review). Korean UI must not use "리뷰" for either concept. Step 1 shipped ≤60-char one-line rating comments + private `review_candidate`, extending the existing `album_reviews` state without a new table. Step 2 shipped rating count/average/distribution, sort by newest/rating/name, rating history, and editorial-candidate list. Entrance-link/visibility defects found after Step 2 were fixed and prod-verified.
  <!-- rfc: docs/rfcs/FEAT-album-review-authoring.md | status: accepted -->

  **Next gate: re-measure, baseline reset 2026-08-15.** Gate condition = since front `2dcabd0`(2026-08-15, front #406 merge — `/search` album grid moved onto the canonical `AlbumCard` with a 담기 entrance, the most direct "find an album" path gaining one for the first time), bucket additions (`review_bucket_items` where `item_type='album'`) ≥10 while owner ratings (`album_reviews.rating IS NOT NULL` for `user_id = OWNER_SUB`) remain 0. If additions <10, **do not decide**.

  Re-measured 2026-08-15 against the prior `bd56910`(2026-08-09) baseline before resetting: album bucket additions since 0809 = **0** (denominator: 2026-08-09–2026-08-15, 6 days; the most recent album addition of any kind predates the baseline, at 2026-08-07), and the "owner ratings remain 0" premise had already been violated — the owner's own `album_reviews` row (`rating=3.5`) was created 2026-08-10, inside that window. With the counter at 0, not "near 10," the reset costs nothing. Owner decided 2026-08-15 to reset again on top of that: front #406 changes the funnel this gate measures, the same reasoning that invalidated the `aebabe7`(2026-08-02) baseline. No fixed re-check date — check the counter directly rather than a calendar guess.

  Steps remain:
  - **Step 3** — owner-only AI distillation pilot(C3+C4). OQ3 default-prompt wording remains open and is intentionally deferred until this gate.
  - **Step 4** — unified authoring entry + permission cleanup(C1 + audit E-5). OQ9 entry placement/form remains open.
  - **Step 5** — conditional general AI opening. OQ4 usage limit/wait-state remains open.

  AI behavior remains distillation only: use only material supplied by the author, never add outside facts/evaluations/metaphors, result remains editable, and publishing is always an explicit user action. The user-facing AI request will be the product's first actual API-engine caller. → `docs/rfcs/FEAT-album-review-authoring.md`.

- **ARCH-entity-interaction-domain-audit** (**in-progress**) — independent audit of review/memo commands, playback-state ownership, lyrics hosting, bucket-add flow, modal infrastructure, and global events. Steps **1, 2, 3 (3a/3b/3c) and 4** are complete and prod-verified.
  <!-- rfc: docs/rfcs/ARCH-entity-interaction-domain-audit.md | status: in-progress -->
  - **Step 3a** fixed `NowPlaying`'s `controlBusyRef` race for external playback events using `localWriteSeq`.
  - **Step 3b** made `NowPlaying` subscribe to `playbackSession` for track identity + anchor convergence while keeping tier/mode/like/device/reconnect local.
  - **Step 3c** SHIPPED 2026-08-06 (front #374), closing Step 3 — it moved `LyricsViewer` synchronization-anchor ownership, the highest-risk part because it touches the sub-100ms synchronization path tuned by the (now-archived) `FEAT-lyrics-sync-precision`.

  **Next = Step 5** (memo naming conflict; blocked behind the `FEAT-album-review-authoring` gate above) — new session. → `docs/rfcs/ARCH-entity-interaction-domain-audit.md`.

- **DATA-multidisc-track-order** (**accepted 2026-08-16; Step 1+2+3 shipped**) — promoted from Backlog this
  <!-- rfc: docs/rfcs/DATA-multidisc-track-order.md | status: accepted -->
  session on owner approval. `tracks` had no `disc_no` column, so every tracklist read path orders by
  `track_no` alone and multi-disc albums interleave; the tie-break falls through to arbitrary `id` order.
  Both of the draft's load-bearing claims were re-measured against prod before promotion rather than
  carried over: `information_schema` still reports **zero** `disc_no`/`disc_number` columns, and the
  collision population is **78 of 3,440 albums (2.27%)** against the draft's 77 of 3,313 — same rate, so
  it tracks catalog growth rather than being a one-off import artifact.

  Promoted ahead of the other candidates because it is the only open item whose completion depends on
  nothing but implementation — every other Active row waits on owner authoring/curation behaviour — and
  because `ARCH-global-playback-experience` Step 4 has just put a play-all / reorder queue on top of
  exactly these `ORDER BY` sites.

  **Step 1** (`myblog_shared_db` migration `V53__add_tracks_disc_no.sql` adding `tracks.disc_no INTEGER`,
  nullable/no default) applied to prod and the Neon test branch this session, before merge.

  **Next = Step 2, and it is smaller than the draft said.** A kickoff current-state audit on 2026-08-16
  (no code written) re-measured the population — **78 / 3,445 albums, 2,241 tracks, zero missing
  `spotify_id`**, so the backfill is unchanged and 100% re-fetchable — but overturned three of the draft's
  Step 2 claims and one of Step 4's. There is **one** live track-ingest site, not a symmetric twin pair:
  `myblog_worker/worker/service/sync_service.py:174`, which needs **no shared_db pin bump** (raw SQL;
  worker imports only `genre_mapping`). `myblog_music`'s `Track(...)` writer has **zero callers** — dead
  code, optional hygiene. `CandidateTrackItem` is **not** on the SQS contract (`enqueue_album_sync` sends
  album IDs only), so it is dropped. And Step 4's regen will **not** pick the field up on its own —
  `TrackItem`/`TrackOut` are hand-written Pydantic — making Step 4 a consumer-less contract widening, now
  gated on an explicit owner yes and expected to be dropped.

  **Step 2 shipped and run 2026-08-16** (`myblog_worker` #94 `1254c1e` + #95 `ad93b2f`, owner-approved
  invoke): the ingest fix is deployed to prod, and the one-off backfill ran against all 78 colliding
  albums. First pass matched 2,208/2,241 tracks; a post-run DB check found 2 albums (10 track_no ties)
  still unresolved due to Spotify market Track Relinking, fixed in #95 and re-invoked. **76/78 albums
  (97.4%) fully resolved.** The remaining 2 (Queen's "Sheer Heart Attack (Deluxe Remastered Version)" and
  "The Game (Deluxe Remastered Version)") have local `spotify_id`s that no longer resolve in Spotify's
  live catalog at all (not relinking — the ids appear orphaned/re-issued) and would need a full album
  re-sync to fix; out of scope for this bounded backfill, no regression (same arbitrary tie-break as
  before this RFC). `pytest` 533 passed / 3 skipped, both PRs deployed and Lambda-confirmed.

  **Step 3 shipped 2026-08-17** (`myblog_backend` #157 `11013e7`, `myblog_music` #68 `0ca8444`). All 4
  `ORDER BY` sites now lead with `disc_no` before `track_no`. Paid the shared_db pin bump this required —
  `myblog_music` `v0.26.0`(`dd016c4`) → `8319a56`, `myblog_backend` `029f8db` → `8319a56`, both treated as
  their own reviewable change (pytest green before/after the bump alone in both repos, unchanged pass
  counts). `pyright` 0 errors, `openapi.json` regen no diff in either repo. Live-verified against prod:
  `GET /api/music/albums/{In Utero (Deluxe Edition) id}` returns disc 1 in full (tracks 1–20) before disc
  2 restarts at track_no=1. Production smoke 19/19 quoted on both PRs. The 2 unresolved Queen albums from
  Step 2 keep their pre-RFC arbitrary tie-break, as expected — no regression.

  Remaining: **Step 4** (OpenAPI/contract/frontend surfacing of `disc_no`) only if the owner wants it —
  gated on an explicit yes, expected to be dropped per the RFC's own text (no consumer, Non-goals already
  forbid a disc-number UI). → `docs/rfcs/DATA-multidisc-track-order.md`.

- **A11Y-modal-background-inert** (**accepted 2026-08-16; Steps 1+2 SHIPPED — front #411, #412**) —
  <!-- rfc: docs/rfcs/A11Y-modal-background-inert.md | status: accepted -->
  promoted from Frozen this session on owner approval, as `ARCH-overlay-modal-isolation` OQ2 recommended
  (a separate RFC, not a reopening of that one). While a scrim modal is open, nothing removes the page
  behind it from the accessibility tree: **zero occurrences of `inert` in `myblog_front/src`**.

  The current-state audit narrowed the defect and corrected the origin line, which claimed "screen
  readers/**tab order**": `useDismissable` already has a working, tested Tab focus trap with a nesting
  stack, so tab order is not the problem. The real hole is **screen-reader browse mode** — a virtual
  cursor does not move DOM focus, so a focus trap constrains nothing and `aria-modal` is advisory. It
  also found a pre-existing gap the frozen idea never mentioned: `ActionSheet`, `BucketPickerSheet` and
  `PocketDesignSettings` are scrim modals with `aria-modal="true"` that **never adopted `useDismissable`
  at all**, so today they have no focus trap and no focus restore — now Step 2.

  Scope is small because the modal population is enumerable from an existing signal rather than judged:
  this codebase already encodes "is this modal?" as "does it lock background scroll?" (11
  `lockScroll: true` call sites + 13 direct `useScrollLock` callers). `myblog_front` only, no contract,
  no backend. **OQ1 resolved 2026-08-16 (owner): option (a) — the persistent playback bar is inerted
  along with the rest of the background.** Nothing blocks Step 1 now. Owner's reasoning matched the
  RFC's: a screen-reader user should not retain reach that the scrim already takes away from a sighted
  user; pausing requires closing the dialog, same as clicking does today.
  → `docs/rfcs/A11Y-modal-background-inert.md`.

  **Step 1 shipped 2026-08-16 (front #411).** `inertBackground` lives in `src/lib/useDismissable.ts`,
  defaulting to the resolved `lockScroll`; a module-level refcounted controller recomputes off
  `openStack`. Measured before/after on the home page with the album overlay open: the accessibility
  tree went from **176 background nodes** (primary nav, every album card, the footer, the Pocket tray)
  alongside the dialog, to **the dialog alone**. OQ1's consequence was verified with the persistent
  playback bar actually rendered, against a control — not assumed. `ClientRouter` navigation with the
  modal open strands nothing (5 inert before, 0 after). Gate: lint clean, `astro check` 0 errors,
  `pnpm test` 654 passed / 0 skipped incl. 8 new tests, each checked against a deliberately broken
  build so none is tautological.

  **Step 2 shipped 2026-08-16 (front #412), found already-merged and docs-synced 2026-08-17.**
  `ActionSheet`, `BucketPickerSheet` and `PocketDesignSettings` now call
  `useDismissable(true, onClose, ref, { lockScroll: true })` and inherit background `inert` from Step 1.
  Two RFC current-state claims were wrong and corrected on implementation: `BucketPickerSheet` had the
  same hand-rolled `window` ESC listener the RFC attributed only to `ActionSheet` (both deleted, moved to
  the shared `document`-level listener), and `PocketDesignSettings` had `role="dialog"` with **no**
  `aria-modal` and no keyboard exit at all (`aria-modal="true"` added). `pnpm lint` clean, `astro check` 0
  errors (301 files), `pnpm test` 663/663 (+9, each checked against the pre-PR code to confirm it
  actually fails there — none tautological). CDP against real prod data, all three: background a11y
  nodes went from 63/218/(portal, not separately counted) down to 2/0/0 with marks applied (the
  `PocketDesignSettings` 2 are Step 1's documented shape — its own island's other tray controls, not a
  regression), autofocus/Tab-wrap/ESC/focus-restore all confirmed with real key input.
  **Production smoke 19/19 passed** (run 2026-08-17 against the deployed HEAD, quoted on front #412 — no
  smoke result had been posted since the 2026-08-16 merge, closing that gap). **This was the RFC's last
  step — both steps now shipped.** Status remains `accepted`; promoting to `done`/archiving needs explicit
  owner sign-off, not done here. → `docs/rfcs/A11Y-modal-background-inert.md`.

- **DATA-release-noise (c) exact-dup dedup** — promoted from Backlog 2026-08-16 on owner approval, and
  <!-- rfc: none -->
  its blocking question resolved in the same pass: the `PERF-home-feed-latency` dependency note is
  **stale and is now dropped**, exactly as the Backlog row suspected — that name has never existed as an
  RFC or plan row and appears nowhere outside the line that cited it. Nothing sequences ahead of this.

  Re-measured before promotion, and the number is smaller than the row implied: artist-scoped exact
  duplicates (same normalized title **and** same artist set) are **56 groups / 57 redundant rows of
  3,440 albums = 1.7%**. A title-only count reads 107 groups / 169 rows, but that conflates distinct
  artists sharing an album title and is not the dedup population. **Lowest priority of the three
  promoted this session** — kept Active so it stops being re-litigated, not because 1.7% is urgent.
  No RFC file; scope is small enough to live in this row.

_2026-08-06 playback/modal/security audit (8 parallel investigations over playback entry points, queue identity, modals and multi-user authorization). Everything it confirmed has since shipped; the only remaining deferral is its track-info no-op item, deliberately held for the canonical-track scope. Evidence and the full issue matrix live in the audit record and `git log`._

_Shipped implementation detail belongs in `git log`, RFCs and `docs/archive/done/`; plan.md retains only open decisions, gates, observations and status transitions._

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

- **CHORE-research-prompt-port-not-swap** (**legs 1–6 SHIPPED 2026-07-30; measurements remain**) — do **not** replace `album_research_v2` with v4 wholesale. Controlled RENAISSANCE comparison scored **v2 12/22, v4 12/22**, with complementary rather than strictly better coverage. v4 improved biography/primary-statement pressure but lost v2's explicit "do not import others' critical verdicts" protection and costs more tokens/wall time. The shipped approach ports the useful v4 pressure into v2, retains the no-verdict rule, adds liner-notes and sample-chain-depth requirements, injects catalog context, and intentionally keeps `PROMPT_VERSION=v2` so stored notes remain visible.

  Remaining measurements only:
  1. Re-run RENAISSANCE against the checked-in 22-item sheet + ONYX with `grep -ci izm = 0`; record score, wall clock, output length and **actual per-hop citation support**. Pass target = recover ≥3 of items 5/6/8/22 at ≤1.3× v2 wall clock.
  2. Generalisation test on one album not used to create the rules.
  3. First `[확인]` precision audit; no false-`[확인]` denominator exists yet.

  Highest-information measurement remains owner writing **one review from one research note** and marking used/unused material; the current prompt metrics are proxies because 80 notes have produced 0 completed reviews. Evidence → `docs/editorial/research-note-requirements.md` + `docs/reviews/measurements/2026-07-30-research-prompt-v2-vs-v4/`.

- **FEAT-ai-editorial-critique** (**draft; deferred**) — Phase 0 thin slice: backend-only AI editorial critic that runs the existing critique method over a draft + already-linked album DB facts, returning grounded Korean feedback + uncertainty/checklist markers, never rewriting the draft. Step 1 = local implementation + golden eval; Step 2 = infra JWT route + contract. UI, persistence, planner, publish gate and broader fact checking remain non-goals. Needs owner accept before Active.

  Open thread (from `FEAT-editor-buckit`, 2026-06-19) — on promotion: fold in the explicit two-stage editorial pipeline (nightly full-draft → critique pass), re-audit the stale "zero AI/LLM code" Current State, gate via `require_owner` rather than bare `require_cognito_token`, and convert its Secrets Manager references to SSM (`CHORE-secrets-ssm-migration`). → `docs/rfcs/FEAT-ai-editorial-critique.md`.

- **DATA-catalog-noise-and-lyrics-coverage** (**accepted; implementation complete except observation gates**) — Steps **1a + 2 + 3a + 3b + 4 SHIPPED**; Step **1b DROPPED** by owner decision 2026-08-03. Search noise is handled by ranking rather than catalog filtering so classical material remains findable. Step 2 is the ingest choke point and absorbs `DATA-release-noise (a)`. Step 3a parks empirically low-yield lyrics rows; Step 3b drains the previously unreachable `best-of-*` supersession backlog first; Step 4 album-scoped reassessment is live.

  **Observations measured 2026-08-16 — two closed, one on track, and the verification tool was found
  to be lying.** Full record in the RFC's new "Observation gates" section; summary:
  1. trailing-7-day classical album share — **MET**. 37% (72/195) baseline → **0.64% (1 of 156)**,
     inside the ≤8% gate.
  2. classical-holdout misclassification rate — **RETIRED as unmeasurable**, samples so far clean.
     Exactly **one** album has passed the predicate since 08-01 (a Franco Fagioli / Il Pomo d'Oro Vinci
     opera aria — correctly classified). At ~1 sample per two weeks no future date makes this
     answerable. The Verification block's CloudWatch route is also dead: prod Lambda runs
     `LOG_LEVEL=WARNING`, so the `classical_excluded`/`classical_holdout` `logger.info` counters never
     reach CloudWatch; measured from DB state instead.
  3. best-of backlog → ~450 — **ON TRACK, ahead of schedule**. 2,765 → **1,141**, of which **672** are
     selectable today (rest held by the 30-day rest interval). ~4–5 more ticks, so the arm should go
     quiet around **2026-08-21**, not the estimated 08-29. Watch query 6's new `arm_gone_quiet` boolean
     rather than a calendar date.

  **`docs/sql/lyrics_pool_health.sql` — the file this RFC's Verification block points at — reported the
  lyrics pool draining while it was growing, and is fixed in this change.** Query 2 printed
  `net_per_day = -61.7`; the pool actually went **11,033 → 11,928 between 08-03 and 08-16 = +68.8/day**
  (both endpoints on the identical predicate; the 11,033 is recorded in `_fetch_unresolved_tracks`'s own
  docstring). Sign inverted, not just magnitude. Cause: `drained_per_day` credited any `matched` row
  whose `updated_at` moved, and Step 3b added two writers that move it on rows that were never in the
  unresolved pool — `TrackLyricsWriter.touch` advancing the rotation cursor on guard-kept best-of rows
  (**33.4/day**, content unchanged) and best-of supersessions. The sweep was being counted as pool
  drainage. Query 6 had the mirror-image bug: it computed `unresolved < 150`, the right test only under
  the *pre*-3b ordering that 3b inverted, so it read "arm unreachable" throughout the sweep it existed to
  monitor. Query 4's recency tiers are contaminated the same way and are commented as
  not-comparable-until-quiet. **No shipped code path or past decision changes** — the retired "net ≤ 0/day"
  metric was retired on correct reasoning and its `+38/day` was nearer truth than anything the tool printed
  after. Only figures quoted from this tool between 08-03 and 08-16 are unusable.
  → `docs/rfcs/DATA-catalog-noise-and-lyrics-coverage.md`.

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
