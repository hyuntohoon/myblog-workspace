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

- **Single source of truth**: `myblog_front/docs/frontend/component-map.md` (broadened scope).
- **Historical record**: this RFC + `ARCH-entity-interaction-v2` + the feature RFCs, unmodified.
- **Executable enforcement**: myblog_front's own ESLint config / CI (G3, G5 immediately; G6, G2, G8 as
  follow-on gates) — not the workspace repo, which has no per-repo CLAUDE.md by design (repo specifics
  live in code + README).
- **PR template**: `myblog_front/.github/PULL_REQUEST_TEMPLATE.md` gains G1/G7/G8 checklist lines.
- No workspace-level CLAUDE.md change — nothing here crosses a repo boundary.

---

## Steps

One step per session (hard rule #4), same discipline as `ARCH-entity-interaction-v2`.

### Step 0 — two ad hoc bug fixes (already shipped, not a step of this RFC's sequence)

`BUG-20` (front #355, `734925e`, 2026-08-05): `isManualAddTarget` single-owner predicate (closes the
live `LikedBoard` gap) + the `trashAlbum` temp-id guard. See `docs/archive/done/2026-08.md`. Recorded
here only as the prerequisite G5 partially already satisfies (the function exists; the ESLint gate in
Step 2 below still needs to ship to make it durable).

### Step 1 — `component-map.md` rewrite as cross-domain registry (docs-only)

Add the event/state-owner/modal tables described above. Correct the two factual errors this audit
found (the false `AddToBucketMenu` "manual ESC" claim; the incomplete ad hoc-modal exception list).
Note the `MemoWindow` lyrics-dock exception with its actual reason. Subsumes/broadens
`ARCH-entity-interaction-v2` Step 6's re-stamp, which should either merge into this step or explicitly
hand off scope.

**Verification**: doc review; every claim spot-checked against code in the same session (same bar as
`ARCH-entity-interaction-v2` Step 1/2).

### Step 2 — mechanical guardrails: G3 + G5 (front-only)

ESLint rules banning (a) inline `new CustomEvent(` outside the two designated files, (b) the string
literal `'spotify_library'` outside `lib/buckets.ts`. Fix the one live violation each rule would catch
(`PB_ADD_TRACK_EVENT` in `scripts/albumDetail.client.ts:176`) in the same PR.

**Verification**: `pnpm lint` clean with the new rules active; a deliberately-reintroduced violation
in a throwaway diff confirms each rule actually fires, then is reverted before commit.

### Step 3 — playback state consolidation (front-only, cross-cutting `FEAT-member-player` +
`FEAT-playback-bucket-player`)

`NowPlaying`/`LyricsViewer` subscribe to `lib/playback/session.ts` instead of independently polling
`readLivePlayback()`/listening to `MYBLOG_PLAYBACK_CHANGED`. Collapses `controlBusyRef` into
`session.ts`'s existing `localWriteSeq` guard.

**Open question before this step starts**: which RFC houses it — a step here, or a step in one of the
two playback RFCs? Owner call (see Open Questions).

**Verification**: existing `playback/session.test.ts`/`NowPlaying`-adjacent tests extended to assert
cross-tracker consistency (today: zero such tests, confirmed by this audit); real-browser check that
lock-screen Media Session control still works when playback originates from the Playback Bucket panel.

### Step 4 — `useDismissable` adoption sweep + G4 (front-only)

Migrate the ad hoc ESC/focus-trap components found (`ActionSheet` may stay documented as an
intentional exception; `RecentAlbumsModal`, `RecentTracksModal`, `TrashDrawer`, `ImportAnalysis`,
`CommandPalette`, `DraftsInbox`, `gm-shared`'s peek dialog do not have a stated reason to stay
separate). Ship with a `useDismissable.test.ts` (zero coverage today despite 15+ consumers) and at
least one interaction test per migrated component.

**Verification**: `pnpm test` green including the new tests; CDP spot-check that ESC/backdrop/focus
restore still work per migrated component.

### Step 5 — memo naming resolution (docs-only, coordinates with `FEAT-album-review-authoring`)

Rename the planned Step 3 "memo" concept in `FEAT-album-review-authoring` before that RFC's gate
reopens (2026-08-12+), and correct its "one user-album state" premise against the shipped bucket memo.

**Verification**: doc review only; no code changes in this step.

---

## Open questions

1. **Who owns Step 3 (playback consolidation)** — a step here, or a step in `FEAT-member-player` /
   `FEAT-playback-bucket-player`? Needs an explicit owner sequencing call.
2. **What is the actual planned design of `FEAT-album-review-authoring` Step 3's memo?** The gate gap
   means it hasn't been re-measured since 2026-08-03; whether its design still makes sense next to the
   shipped bucket memo is a product-intent question this audit can't answer from code.
3. **Is `TrashDrawer`'s non-portal mount intentional** or simply missed? No comment states a reason
   either way; needs a decision before Step 4 treats it as an exception or a migration target.
4. **Should `useDismissable` also own backdrop+portal-mounting** (today it only owns ESC/focus-trap), or
   should a second shared primitive cover that half? Design-taste call, not code-dictated.

---

## Decisions log

| Date | Decision | Step |
|------|----------|------|
| 2026-08-05 | Owner reviewed the domain-audit findings and approved proceeding with all recommendations in-session ("다 추천으로 ㄱ"). Two concrete bugs (BUG-20) shipped immediately as ad hoc fixes, outside this RFC's step sequence, since they are plain bugs not architecture decisions. This RFC captures the remaining, genuinely multi-step work | 0 |
| 2026-08-05 | `AddToBucketMenu`/`BucketPickerSheet` non-merge re-examined and reconfirmed — the real bug (BUG-20) was a third, unaudited call site (`LikedBoard`) missing a shared predicate, not duplication between the two named components. Non-goal restated accordingly | 0 |
