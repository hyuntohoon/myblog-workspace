# ARCH-entity-interaction-domain-audit: cross-domain registry + guardrails for entity-interaction fragmentation

- **Status**: draft
- **Owner**: TBD
- **Created**: 2026-08-05
- **Plan row**: `plan.md` → ARCH-entity-interaction-domain-audit
- **Sibling, does not replace**: `docs/rfcs/ARCH-entity-interaction-v2.md` (scopes to album/track/artist/
  drag only; this RFC covers the domains its own non-goals explicitly exclude — reviews/memos,
  playback, lyrics host, bucket-add flows, modal/overlay infra, global events)
- **Origin**: an independent 5-agent architecture audit run 2026-08-05, at owner request, to check
  whether the same fragmentation pattern `ARCH-entity-interaction-v2` found in album/track/artist
  recurs in adjacent domains. Full findings: memory `project-arch-entity-interaction-v2-domain-audit`.
  Two concrete bugs the audit found were fixed same-session as ad hoc, non-RFC-step PRs (front #355,
  `docs/archive/done/2026-08.md` "BUG-20") — this RFC covers everything else.

---

## Goal

One cross-domain registry (`docs/frontend/component-map.md`, scope broadened) that a new
overlay/event/state-owner/add-flow author checks before inventing a new one, plus a small set of
mechanically-enforced guardrails for the two rule classes that are cheap to check automatically
(single-owner predicates, single-owner event names). Everything else stays a review/PR-template
discipline, stated as such rather than oversold as automatable.

## Non-goals

- No merge of `AddToBucketMenu`/`BucketPickerSheet` — independently re-examined during the audit and
  found still justified (they do different jobs; the actual bug was a third, unaudited call site
  missing a shared predicate, not duplication between these two).
- No `BucketBoard.tsx` monolith split — out of scope per `ARCH-entity-interaction-v2`'s existing
  non-goal, unchanged by this audit.
- No new branded-id types (e.g. `type AlbumId = string & {brand}`) — the existing named-field
  convention (`albumId` vs `spotifyAlbumId`) works when followed; the gap found was adoption, not typing.
- No change to the two-album-detail-host decision (E6) or the `DetailTarget`/`OpenAlbumDetail` split —
  both independently re-verified sound in this audit.
- No lyrics-sheet host merge — `MemoWindow`'s local dock and `SelfDashboard`'s shared slot both have a
  real, distinct technical reason (remount-safety for tear/dock); this RFC only asks that the reason be
  written down in the registry, not that the hosts merge.

---

## Target architecture (full detail: audit memory / this session's report)

- `component-map.md` gains three tables beyond its existing entity/navigation content: a global
  CustomEvent registry (name, payload type, dispatcher(s), listener(s)), a state-owner registry (what
  real-world state, canonical module, documented consumers), and a modal/overlay registry (component,
  primitive used, exception reason if not `useDismissable`).
- `lib/playback/session.ts` becomes the single playback-state owner; `NowPlaying`/`LyricsViewer` become
  subscribers instead of independent pollers with independently-invented race guards.
- Every app-level `CustomEvent` name+payload lives in `lib/entityEvents.ts` or
  `lib/pocketBuckit/events.ts` — no inline `new CustomEvent(<literal>)` elsewhere, including vanilla
  scripts (found once already: `PB_ADD_TRACK_EVENT` duplicated as a raw string in
  `scripts/albumDetail.client.ts:176`).
- `useDismissable` is the default for any `role="dialog"` component; today's 8 ad hoc ESC/focus-trap
  reimplementations (some in the same file as correct adopters — `OverviewDash.tsx`, `BucketBoard.tsx`)
  migrate or get a named, registry-recorded exception.
- The unshipped `FEAT-album-review-authoring` Step 3 "memo" (free-text → AI distillation) gets a
  different name before it ships — it would otherwise collide with the already-shipped bucket-item
  memo (`review_bucket_items.note`, FEAT-editor-buckit). That RFC's "one user-album state" premise is
  also false today (the bucket memo is a second, bucket-scoped state) and should be re-audited before
  Step 3 resumes (already gated to 2026-08-12+ for unrelated reasons).

---

## Guardrails

| # | Rule | Prevents | Enforcement | Enforceable? |
|---|---|---|---|---|
| G1 | New album/review/memo-shaped action names which of the 3 existing commands (`album_reviews` PUT, `review_bucket_items` PATCH, `posts` POST/PUT) it extends, or justifies a 4th | a silent 4th "state of my relationship to an album" (the class of bug `FEAT-album-review-authoring`'s memo already has vs. the bucket memo) | PR description + reviewer checklist | No — review-only |
| G2 | A `*Id`-typed field never receives a foreign-namespace id or a client-`temp:` id | id-namespace conflation (`releaseShared.tsx:212-214`) / temp-id-to-server forwarding (BUG-20's second bug) | grep/CI gate on `temp:`-prefixed strings reaching a delete/add call; targeted unit test per site | Partially |
| G3 | Every app CustomEvent declared in `entityEvents.ts`/`pocketBuckit/events.ts`; no inline literal elsewhere | duplicated-literal drift (`PB_ADD_TRACK_EVENT`) | ESLint `no-restricted-syntax` banning `new CustomEvent(` outside the two files | **Yes** |
| G4 | New `role="dialog"` components use `useDismissable` or document the exception | continued ad hoc modal reinvention (8 found, some intra-file) | partial grep-diff + reviewer checklist + component-map entry | Partially |
| G5 | The `spotify_library` exclusion rule has exactly one owner (`isManualAddTarget` in `lib/buckets.ts`); no other file hardcodes the string | recurrence of BUG-20's bug class | ESLint `no-restricted-syntax` banning the string literal outside `lib/buckets.ts` | **Yes** |
| G6 | New playback-state consumers subscribe to `lib/playback/session.ts`; no new `readLivePlayback()`/`MYBLOG_PLAYBACK_CHANGED` direct caller | recurrence of the 3-tracker split (a 4th surface inventing a 4th tracker) | grep-diff CI gate capping today's known call-site count (baseline diff, not absolute zero — memory `feedback-grep-gate-needs-baseline-diff`) | Yes, as a diff-gate (stops new drift; does not itself consolidate the existing 3) |
| G7 | PR body states which registry entry was checked before adding a new overlay/event/command/state owner | the root cause itself — narrow-scoped RFCs missing adjacent-domain duplication | PR template field | No — procedural only, paired with G3/G5/G6's mechanical gates |
| G8 | New/changed overlay, drag source, or add-to-bucket flow ships with ≥1 component-level (render+interaction) test | the current near-absence of interaction-regression coverage (3/27 test files before BUG-20's PR added a 4th) | coverage-diff check (new/changed component file, no matching `*.test.tsx`) + review | Partially — presence checkable, quality is not |

Rejected as unenforceable-and-vague: "reuse components where possible," "maintain consistency."

## Rule ownership and placement

- **Single source of truth**: `docs/frontend/component-map.md` **in this workspace repo**
  (broadened scope) — corrected 2026-08-05 (external review item 1): this doc previously read
  `myblog_front/docs/frontend/component-map.md`, but `myblog_front` has no `docs/` directory at
  all. The file has always lived here (same repo as this RFC, `plan.md`, and every other RFC
  about `myblog_front`-only work) — the RFC's own path was wrong, not the file's location. Two
  in-repo `myblog_front` comments (`src/components/shared/TrackRow.tsx:5`,
  `src/lib/entityLinks.ts:5`) point at `docs/frontend/component-map.md` with no repo prefix
  either; both now say `myblog-workspace/docs/frontend/component-map.md (sibling repo)` so a
  developer working solely in `myblog_front` doesn't look for it in their own checkout.
- **Historical record**: this RFC + `ARCH-entity-interaction-v2` + the feature RFCs, unmodified.
- **Executable enforcement**: myblog_front's own ESLint config / CI (G3, G5 shipped Step 2; G6,
  G2, G8 as follow-on gates) — not the workspace repo, which has no per-repo CLAUDE.md by design
  (repo specifics live in code + README).
- **PR template**: `myblog_front/.github/PULL_REQUEST_TEMPLATE.md` gains G1/G7/G8 checklist
  lines — shipped 2026-08-05 (external review item 3; front #358).
- No workspace-level CLAUDE.md change — nothing here crosses a repo boundary. (The
  component-map.md ↔ myblog_front code-comment mismatch above was a documentation bug, not a
  boundary decision — the doc's *ownership* was never in question, only its stated path.)

---

## Steps

One step per session (hard rule #4), same discipline as `ARCH-entity-interaction-v2`.

### Step 0 — two ad hoc bug fixes (already shipped, not a step of this RFC's sequence)

`BUG-20` (front #355, `734925e`, 2026-08-05): `isManualAddTarget` single-owner predicate (closes the
live `LikedBoard` gap) + the `trashAlbum` temp-id guard. See `docs/archive/done/2026-08.md`. Recorded
here only as the prerequisite G5 partially already satisfies (the function exists; the ESLint gate in
Step 2 below still needs to ship to make it durable).

### Step 1 — `component-map.md` rewrite as cross-domain registry (docs-only) — ✅ **DONE 2026-08-05**

Results: added the **Global CustomEvent registry**, **State-owner registry**, and **Modal / overlay
registry** tables. Corrected the two factual errors this audit found — the false `AddToBucketMenu`
"manual ESC" claim (it has zero ESC handling; `BucketPickerSheet` does have real ESC handling, so the
old line's symmetry claim was also wrong, not just the "manual" word) and the stale-since-July "NowPlaying
/ LikedBoard artists not linkable" claim (`ARCH-entity-interaction-v2` had already measured this false
on 2026-08-04 but the doc itself was never fixed — corrected now, with a note that a *found*-stale claim
can still outlive the finding). Noted the `MemoWindow` lyrics-dock exception's actual reason (remount
safety for tear/dock) inline, since it previously existed only as a code comment.

**Scope decision on the `ARCH-entity-interaction-v2` Step 6 overlap**: handed off, not merged. This
step does NOT transcribe that RFC's E1 canonical album/track/artist definitions into `component-map.md`
— `ARCH-entity-interaction-v2.md` stays the source for E1/E2/E3 until its own Step 6 runs. Recorded
explicitly in the doc's header so a future reader doesn't assume E1 lives here.

**Also updated while verifying claims** (found, not part of the original scope, fixed as trivial
corrections rather than deferred): `TrackRow`'s "Ownership by domain" bullet and its "no play
affordance" line both still described the pre-Step-5 `{lyrics?, open?}` action set — updated to the
current `{lyrics?, open?, openLyrics?, play?, add?, drag?}` shape and to state precisely that the
`play`/`add`/`drag` slots exist but are ungranted, not reserved.

**Verification**: doc review; every claim in this step's new/changed prose was spot-checked against
`myblog_front` `origin/main` `734925e` in this session (`TrackRow.tsx`'s `TrackRowActions` interface,
`entityEvents.ts`/`pocketBuckit/events.ts`/`ReviewTrackAdder.tsx`'s event exports,
`AlbumDetail.tsx`'s `MemoWindow` TrackRow usage, `AddToBucketMenu.tsx`/`BucketPickerSheet.tsx`'s ESC
handling by direct grep) — same bar as `ARCH-entity-interaction-v2` Step 1/2.

### Step 2 — mechanical guardrails: G3 + G5 (front-only) — ✅ **DONE 2026-08-05**

ESLint `no-restricted-syntax` rules banning (a) inline `new CustomEvent('literal')` outside
`lib/entityEvents.ts`/`lib/pocketBuckit/events.ts`, (b) the string literal `'spotify_library'`
outside `lib/buckets.ts`. Both selectors live in a **single** `no-restricted-syntax` rule entry —
flat config replaces, not merges, an array-valued rule when two config objects match the same file,
so a first attempt at two separate blocks silently dropped the G3 selector (caught by the
deliberately-reintroduced-violation check below, not by `pnpm lint` alone).

Fixed the one live G3 violation: `PB_ADD_TRACK_EVENT` was a raw string literal in
`scripts/albumDetail.client.ts:176`. Moved the constant out of `ReviewTrackAdder.tsx` (its prior
home) into `lib/pocketBuckit/events.ts` — a React-free module — so the vanilla script can import it
without pulling React into its bundle, which is the exact concern the old inline comment cited for
keeping the literal duplicated instead of shared. G5 had zero live app-code violations (BUG-20 had
already fixed the three call sites); one test fixture in `leaf.test.ts` used the raw literal for a
bucket mock and was switched to `SLIB_KIND` so the rule holds with no exceptions carved out for
tests. `scripts/albumDetail.fetch.client.ts`'s `album:detail` literal is excluded from G3 by
filename — it's the registry's documented intentional exception, not the drift pattern this guards.

**Verification**: `pnpm lint` clean with the new rules active; a throwaway probe file confirmed both
selectors actually fire (reverted before commit, never entered the diff); `pnpm exec astro check`
0 errors; `pnpm test` 463/463 passing. Shipped as front #356, prod smoke 19/19 after deploy.

### Step 3 — playback state consolidation (front-only, cross-cutting `FEAT-member-player` +
`FEAT-playback-bucket-player`)

**OQ1 resolved 2026-08-05**: stays a step of this RFC. `FEAT-member-player` has shipped every
non-gated step and has no open slot to take new scope. `FEAT-playback-bucket-player`'s own Step 8
preflight audit (front #351/#823) already looked at this exact gap — `NowPlaying`/`LyricsViewer`
staying a separate tracker from `lib/playback/session.ts` — and explicitly flagged unifying them as
"a larger, out-of-scope change" for itself, mid-sequence, while a concurrent session runs its later
steps. Neither RFC claims this consolidation; this RFC exists for cross-cutting cleanup exactly like
it, so it stays here.

**Split into 3a/3b/3c 2026-08-05, against actual code, not the original one-paragraph estimate.**
The step's original text ("subscribe to `session.ts` instead of polling; collapse `controlBusyRef`
into `localWriteSeq`") undersold the size by roughly two orders of magnitude: `NowPlaying.tsx` is
1,710 lines and `LyricsViewer.tsx` is 1,764, and neither's playback state is a thin wrapper — tier
detection, device picker, shuffle/repeat/volume, liked-state, reconnect flow, Media Session
publishing (`NowPlaying`) and the sub-100ms sync-precision anchor math `FEAT-lyrics-sync-precision`
just finished tuning (`LyricsViewer`) all live in hooks structurally unrelated to `session.ts`'s
queue-first model. A single-session rewrite of either is exactly the "larger, out-of-scope change"
`FEAT-playback-bucket-player`'s own Step 8 audit already declined. Splitting isolates the one
concretely-named bug from the two open-ended migrations, so the bug fix can ship on its own
regression-testable PR while the bigger merges get their own session and design scrutiny each.

#### Step 3a — fix the named race: `controlBusyRef` drops real external events (front-only, `NowPlaying.tsx` only) — ✅ **DONE 2026-08-05**

The actual bug `controlBusyRef` causes today: `NowPlaying`'s `onPlaybackChanged` listener does
`if (controlBusyRef.current) return` — a blanket "ignore every `MYBLOG_PLAYBACK_CHANGED` while ANY
of our own control calls (`playPause`/`seek`/`skip`/`setMode`) is in flight". That drops not only the
echo of our own call (each of which already has its own confirmation read) but also a genuinely
external change landing in the same window — e.g. someone pauses from their phone the instant this
tab's own pause request is still in flight, and the card never learns about it until the next
unrelated event. `session.ts` already solved this exact shape of problem with `localWriteSeq`: a
monotonic counter bumped on every LOCAL authoritative write, so a read discards itself only if a
*newer* local write raced ahead of it — never a blanket "was busy" flag. Port that pattern into
`NowPlaying.tsx`'s own module scope (no dependency on `session.ts` itself, no new cross-module
subscription — this step does not touch the architecture, only the guard). Grep confirmed
`LyricsViewer.tsx`'s own `MYBLOG_PLAYBACK_CHANGED` listener (`onCommand` → `resync('command')`) has
no equivalent busy-guard — it rate-limits instead (`EVENT_RESYNC_FLOOR_MS`) and deliberately does NOT
ignore its own commands (that is how OQ4's residual-series measurement works) — so there is no twin
to sweep here.

**Verification**: a unit test simulating an in-flight control call plus a concurrent external
`MYBLOG_PLAYBACK_CHANGED` (asserting the external event is NOT dropped); existing `NowPlaying` tests
stay green; no real-device step needed — the fix is a pure guard-logic change, testable with mocked
timing per `feedback-stub-must-model-async-lag`.

**Shipped (front #360).** Ported `localWriteSeq` into a component-scope `useRef` counter on
`NowPlaying`'s own hook (`useNowPlaying`, exported for testability) rather than a true module-level
variable — a top-level `let` would leak state across the hook's mount/unmount in tests. Each of
`playPause`/`seek`/`skip` bumps the counter right after its command comes back ok (the same point
`rememberSpotifyTransportProbe('available')` already marks); `onPlaybackChanged` captures the
counter before starting its read and discards the read only if the counter moved meanwhile.
`controlBusyRef` itself is untouched — it still guards re-entrancy on all four control functions,
including `setMode`, which never dispatches the event at all (`sendPlaybackMode` is excluded from
`notifies`, confirmed by grep) and so needed no seq bump, only the listener decoupling.
`NowPlaying.test.ts` (new) covers both halves: a genuinely external event landing while our own
command is held open lands correctly, and the fix was confirmed to catch the regression by
temporarily reverting to the old blanket guard and watching that case go red before restoring it;
a second test holds a deferred echo-read open until *after* our own command's bump lands, proving
the echo still self-discards (not just "usually wins the race" — the RFC's own "correct at any
window width" framing, made deterministic rather than relying on incidental microtask ordering).
lint 0 · astro check 0 · vitest 38/38 files · 482/482. Prod smoke 19/19 (general suite — no
playback-specific prod check needed for a pure client guard-logic change). 3b/3c unstarted, gated
as originally sequenced.

#### Step 3b — `NowPlaying` sources "what's currently playing" from `playbackSession` (front-only)

Narrower than the original full-hook merge: `NowPlaying` keeps its own tier/mode/like/device/
reconnect state entirely local (none of that has a `session.ts` equivalent and folding it in is not
this step's job). Only "what track is playing and its anchor" moves to read from `playbackSession`
instead of `NowPlaying`'s own parallel `adoptLive`-equivalent, so a play started from the Playback
Bucket panel is reflected here without `NowPlaying` running a second, independent live-read poller
racing the session's own.

**Verification**: cross-tracker consistency test (today: zero, confirmed by this audit) — start
playback from the Bucket panel, assert `NowPlaying` converges without a page reload; real-browser
check that lock-screen Media Session control still works with the shared source.

#### Step 3c — `LyricsViewer` sources its sync anchor from `playbackSession` (front-only) — gated on 3b

Highest-risk of the three: this is the exact file `FEAT-lyrics-sync-precision` tuned to sub-100ms
drift, so any anchor-source change re-opens that measurement. Deliberately sequenced last, and gated
on 3b landing and being prod-stable first — do not start 3c in the same session as 3b.

**Verification**: the full CDP sync-precision regression battery `FEAT-lyrics-sync-precision` Step 2
used (not unit tests alone) — real playback, boundary transitions, pause/resume — before this can be
called done.

### Step 4 — `useDismissable` adoption sweep + G4 (front-only) — ✅ **DONE 2026-08-05**

Migrate the ad hoc ESC/focus-trap components found (`ActionSheet` may stay documented as an
intentional exception; `RecentAlbumsModal`, `RecentTracksModal`, `TrashDrawer`, `ImportAnalysis`,
`CommandPalette`, `DraftsInbox`, `gm-shared`'s peek dialog do not have a stated reason to stay
separate). Ship with a `useDismissable.test.ts` (zero coverage today despite 15+ consumers) and at
least one interaction test per migrated component.

**Verification**: `pnpm test` green including the new tests; CDP spot-check that ESC/backdrop/focus
restore still work per migrated component.

**Results (front #357).** All seven migrated to `useDismissable`, preserving `CommandPalette`'s and
`DraftsInbox`'s conditional ESC (artist drill-in backs out / an armed delete row disarms, before
falling through to `onClose`) rather than flattening them to a plain close. `ActionSheet` untouched,
per the RFC's documented exception. Added `useDismissable.test.ts` (ESC-when-open,
no-ESC-when-closed, Tab wrap both directions, focus-restore-on-close, nested-stack top-only, and
`autoFocus:false`) plus one interaction test per migrated component, modeled on the existing
`ActionSheet.test.tsx` pattern (render → ESC / backdrop / ✕ close, click-inside does not close).
`pnpm lint` 0 errors, `astro check` 0 errors, `pnpm test` 36/36 files · 478/478 tests.

**OQ3 resolved**: owner confirmed `TrashDrawer`'s non-portal mount was unintentional, not a
documented exception — migrated on the same footing as the other six. Step 4's scope was the
dismiss mechanism only, so the mount method itself is untouched; `TrashDrawer` now differs from its
portaled siblings on exactly that one remaining axis (recorded in `component-map.md`, not a new OQ).

**Real-browser CDP check found a live bug**, exactly the kind unit tests in isolation can miss:
`gm-shared`'s `Peek` is never unmounted by `GenreMap.tsx` — it mounts once with `nodeId=null` and
later flips `nodeId` — so passing `useDismissable(true, ...)` (the pattern correct for all six other,
genuinely mount-on-open components) ran the hook's mount-time effect exactly once, while
`ref.current` was still `null`. ESC still worked (`onClose` is read through a ref updated every
render, independent of effect timing) but autoFocus and the Tab-trap silently never fired — a live
regression against exactly what G4 exists to prevent, and one the render+interaction unit test for
`Peek` didn't catch either (it renders `Peek` with a truthy `nodeId` from the first render, which
never exercises the always-mounted-then-opened path `GenreMap.tsx` actually uses). Fixed by keying
`open` off `!!node`; added a regression test that mounts `Peek` closed first, matching real usage,
and confirmed it fails without the fix. Verified twice in a real browser: local dev (prod genre data
via a `fetch` stub, since prod CORS blocks direct localhost calls) before merge, and
`www.ratemymusic.blog/genres/` with live data after deploy — both show autoFocus landing on the `✕`
close button, Shift+Tab wrapping to the last focusable, and Escape closing + restoring focus to the
trigger chip.

### Step 5 — memo naming resolution (docs-only, coordinates with `FEAT-album-review-authoring`)

Rename the planned Step 3 "memo" concept in `FEAT-album-review-authoring` before that RFC's gate
reopens (2026-08-12+), and correct its "one user-album state" premise against the shipped bucket memo.

**Verification**: doc review only; no code changes in this step.

---

## Open questions

1. ~~**Who owns Step 3 (playback consolidation)** — a step here, or a step in `FEAT-member-player` /
   `FEAT-playback-bucket-player`?~~ **Resolved 2026-08-05**: stays this RFC's Step 3 — see Step 3 body
   for reasoning.
2. **What is the actual planned design of `FEAT-album-review-authoring` Step 3's memo?** The gate gap
   means it hasn't been re-measured since 2026-08-03; whether its design still makes sense next to the
   shipped bucket memo is a product-intent question this audit can't answer from code.
3. ~~**Is `TrashDrawer`'s non-portal mount intentional** or simply missed?~~ **Resolved 2026-08-05**:
   unintentional — migrated to `useDismissable` in Step 4 on the same footing as its siblings; the
   non-portal mount itself is untouched (out of Step 4's scope) and is now the component's only
   remaining divergence, tracked in `component-map.md`.
4. **Should `useDismissable` also own backdrop+portal-mounting** (today it only owns ESC/focus-trap), or
   should a second shared primitive cover that half? Design-taste call, not code-dictated.

---

## Decisions log

| Date | Decision | Step |
|------|----------|------|
| 2026-08-05 | Owner reviewed the domain-audit findings and approved proceeding with all recommendations in-session ("다 추천으로 ㄱ"). Two concrete bugs (BUG-20) shipped immediately as ad hoc fixes, outside this RFC's step sequence, since they are plain bugs not architecture decisions. This RFC captures the remaining, genuinely multi-step work | 0 |
| 2026-08-05 | `AddToBucketMenu`/`BucketPickerSheet` non-merge re-examined and reconfirmed — the real bug (BUG-20) was a third, unaudited call site (`LikedBoard`) missing a shared predicate, not duplication between the two named components. Non-goal restated accordingly | 0 |
| 2026-08-05 | OQ1 answered — owner kept Step 3 (playback state consolidation) as this RFC's own step, not handed to `FEAT-member-player` (no open slot) or `FEAT-playback-bucket-player` (mid-sequence, already declared this exact unification out of its own scope) | 3 |
| 2026-08-05 | **Step 3 split into 3a/3b/3c.** Reading `NowPlaying.tsx`/`LyricsViewer.tsx` against the RFC's one-paragraph estimate found the real scope roughly two orders of magnitude larger — ~3,500 combined lines of hardware-timing-sensitive code, not a thin polling wrapper. Owner: split rather than attempt in one session — 3a isolates the one concretely-named, cheaply-testable bug (`controlBusyRef` dropping real external events); 3b/3c are the actual architectural merges, sequenced by risk (`LyricsViewer`'s sync-precision anchor last, gated on 3b) | 3 |
| 2026-08-05 | **Step 1 shipped.** `component-map.md`'s `ARCH-entity-interaction-v2` Step 6 overlap resolved by explicit handoff, not merge: E1 (entity canonical definitions) stays that RFC's own Step 6 to transcribe; this step added only the genuinely new cross-domain material (events/state-owners/modals) plus fixed two claims found actively wrong during verification, not merely stale | 1 |
| 2026-08-05 | While spot-checking Step 1's claims, found `component-map.md`'s `TrackRow` action-set description and "no play affordance" line both still described the pre-`ARCH-entity-interaction-v2`-Step-5 shape. Fixed as part of this step rather than filed separately — a doc correction discovered while doing the doc-review verification this step already required, not new scope | 1 |
| 2026-08-05 | **Step 2 shipped** (front #356). `PB_ADD_TRACK_EVENT` relocated from `ReviewTrackAdder.tsx` to `lib/pocketBuckit/events.ts` rather than left in place and merely allow-listed — the file's own React-free status is what let the vanilla script import it in the first place, so the fix and the guardrail's own rationale point the same direction. `album:detail` in `albumDetail.fetch.client.ts` kept as a named exception (filename-scoped), not moved — it's a documented-intentional single-file listener, not a drift pair | 2 |
| 2026-08-05 | **OQ3 resolved.** Owner: `TrashDrawer`'s non-portal mount was unintentional, not a documented reason to diverge — Step 4 migrated it to `useDismissable` alongside its six siblings. The mount method itself stayed out of Step 4's scope, so it's now the component's sole remaining divergence from its portaled neighbors | 4 |
| 2026-08-05 | **Step 4 shipped** (front #357). Migrated seven ad hoc ESC-only dialogs to `useDismissable`; `ActionSheet` stays the one documented exception. A real-browser CDP check (not just the new unit tests) caught a live bug: `gm-shared`'s `Peek` is permanently mounted by `GenreMap.tsx` (`nodeId` starts `null`, flips later) rather than mount-on-open like the other six migrated components, so a first attempt at `useDismissable(true, ...)` ran its mount effect once while `ref.current` was still `null` — ESC kept working (reads `onClose` via a ref updated every render) but autoFocus/Tab-trap silently never fired. Fixed by keying `open` off `!!node`, with a regression test that mounts `Peek` closed first to match real usage. Confirmed on prod after deploy | 4 |
| 2026-08-05 | **External review of this RFC + Steps 1/2/4** ran (9 hypotheses, verified against code not the RFC's prose). Confirmed: (1) this RFC's own path for `component-map.md` had a `myblog_front/` prefix the file doesn't live under — corrected above, file itself unmoved; (3) the PR template promised in "Rule ownership and placement" was never shipped; (4) G3/G5's shared ESLint `ignores` cross-exempted each other's owner file — probed live, confirmed, fixed; (5) `spotify_library` had zero backend enforcement, not just frontend-only as designed — a direct API call bypassed `isManualAddTarget()` entirely on 4 service methods; (6) CI is real and required-to-pass-to-merge in practice (both #356/#357 had genuine green checks) but not *gated* — no branch protection; (9) G2 found two live, unfixed instances of the exact pattern it exists to prevent. Rejected: (8) — host selection is data-driven, not location-driven; only `ARCH-entity-interaction-v2`'s E6 prose was imprecise, not the code. Partially confirmed: (2) inventory/guardrail mixing exists but doesn't need a new document, just tighter pointers; (7) Step 2/4 status itself was accurate, Step 2 just had the scoping gap above. Fixes: front #358 (ESLint split, PR template, `insertAlbum` temp-id guard, `releaseShared.tsx` id-fallback gate), front #359 (doc-comment repo-prefix), backend #151 (`_assert_manual_add_allowed` on 4 methods) | — |
| 2026-08-05 | **Step 3a shipped** (front #360). `controlBusyRef`'s blanket "ignore every event while ANY control call is in flight" replaced with a `localWriteSeq`-style per-read staleness check, scoped as a `useRef` counter inside `NowPlaying.tsx`'s own hook rather than true module scope (avoids state leaking across mount/unmount in tests, and the hook has only ever had one live instance anyway). `useNowPlaying` exported for testability. New unit tests confirmed against both the fix and a temporary revert to the old guard (red on revert, green on fix) | 3 |
| 2026-08-05 | **G2 status corrected from "table row" to "two live gaps found, both fixed, still no CI gate."** `BucketBoard.tsx`'s `insertAlbum` had no `temp:`-id guard (same class BUG-20 fixed for `trashAlbum`); `releaseShared.tsx` passed a Spotify id into a DB-id-only field. Both fixed in front #358 (see item 9 above). The grep/CI gate G2 describes as its enforcement mechanism still does not exist — **G2 remains "Partially" enforceable, not "Yes,"** until that gate ships; do not read the two fixes as closing G2 itself | 2 |
