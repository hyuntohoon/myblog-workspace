# ARCH-bucket-album-modal-unification: one bucket album modal for 평가, 리서치 노트, and 메모 + fix the tile badge collision

- **Status**: accepted
- **Owner**: TBD
- **Created**: 2026-08-09
- **Plan row**: `plan.md` → ARCH-bucket-album-modal-unification
- **Origin**: real-time investigation this session plus an independent design opinion solicited from
  Opus, which recommended a different structural answer (keep the three features in separate homes,
  just wire a rating control into `MemoWindow`'s existing dead slot). The owner reviewed both framings
  and picked full unification instead — see Decisions log for the reasoning recorded in-session.
- **Sibling**: `FEAT-album-review-authoring` — its original diagnosis was that "정리"(organizing a
  bucket) and "평가"(rating) are structurally disconnected. That RFC's 2026-08-02 entrance audit
  (front #332) fixed broken links into the *public album overlay's* rating entry but never checked the
  bucket-tile-click path — which, per §Current state below, has no rating affordance at all. This RFC
  closes that specific, previously-unaudited gap.
- **Sibling**: `ARCH-entity-interaction-domain-audit` Step 5 ("memo naming resolution", gated on
  `FEAT-album-review-authoring`'s 2026-08-12+ gate, still that RFC's own step — not duplicated here).
  Its OQ2 asks whether `FEAT-album-review-authoring`'s planned memo design still makes sense next to
  the shipped bucket memo; this RFC's Step 1 is the structural answer that question needs, so Step 5
  should reference this RFC's result rather than re-derive it when it resumes.
- **Reuses, does not redesign**: the `useDismissable`/`useScrollLock` overlay contract
  (`ARCH-overlay-modal-isolation`). `AlbumDetail`'s `StandardModal` + `MemoWindow` are already
  registered with both (`docs/frontend/component-map.md`'s modal/overlay registry, line 481) — this
  RFC adds no new overlay layer.

---

## Goal

Clicking any album tile in a member's bucket board always opens the same modal shape, and that modal
surfaces all three "my relationship to this album" write surfaces the product already has — **평가**
(rating: star + one-line comment), **메모** (memo: free bucket-item scratchpad), and **리서치 노트**
(research note) — in one place, instead of today's state where the click shows 메모 only, 평가 has no
bucket-side entry point at all, and 리서치 노트 is reachable only through a corner control that is
currently overlapped by a later-added button and effectively unclickable.

## Non-goals

- **Bucket structure itself** (bucket names, lifecycle stages) — unchanged, per
  `FEAT-album-review-authoring`'s own existing non-goal on this point.
- **The `album_research` pipeline** (job triggering logic, prompt, polling) — this RFC touches only
  where the research note is *entered from* and *displayed*, not how it's generated.
- **The public album overlay** (`AlbumOverlay.tsx`) / `AlbumDetailView`'s own layout — this RFC is
  scoped to the bucket-member modal surface (`AlbumDetail.tsx`/`MemoWindow`). The public rating
  *write path* (`PUT /api/reviews/albums/{album_id}`) is reused, not the `AlbumDetailView` component.
- **Merging the four write paths** that `component-map.md:469` documents as "no single owner — four
  independent silos, by design, not drift" (rating / candidate-mark / bucket memo / draft-review, each
  its own API call and DB row). That decision governs *writes*; this RFC unifies the *view* they're
  reachable from, not the commands themselves.
- **A new overlay/dismiss/scroll-lock primitive** — `MemoWindow` already has `useDismissable` +
  `useScrollLock` (`component-map.md` registry, line 481); this RFC keeps using it as-is.
- **평론 (long-form review) authoring** — unaffected.

## Current state

- Bucket-tile click routes through `BucketBoard` → `SelfDashboard.tsx:186-194` →
  `AlbumDetail.tsx:58-77`, which **branches to a different component depending on album state**: an
  unrated/unpublished bucket album with a bucket-item handle opens `MemoWindow`
  (`AlbumDetail.tsx:64-65`); a published (or non-writable) album opens `StandardModal`
  (`AlbumDetail.tsx:71-72`). Two different modal shapes for the same tap, contrary to "always the same
  screen."
- `MemoWindow`'s body already has a slot shaped for a rating, but it is dead: `AlbumDetail.tsx:487` —
  `<span className="memo-album-card__rating"><span className="unrated">미평가</span></span>` — hardcoded
  text, wired to nothing. The real rating control, `AlbumRatingBlock`, only mounts inside
  `AlbumDetailView` when `interactive` (`AlbumDetailView.tsx:217`), and `MemoWindow` never renders
  `AlbumDetailView`.
- The bucket tile's own score badge is gated on the bucket being marked done —
  `BucketBoard.tsx:1034-1035`: both `rated` and `score` props are `bucket.isDone && a.itemType === 'album' ? … : null`.
  A rating made while organizing (bucket not yet "done") therefore leaves **zero visible trace**
  anywhere on the board.
- `CoverResearchBadge` (`BucketBoard.tsx:467-483`, rendered `:588`) is a 12×12px dot,
  `.rsh-cover-badge` (`research.css:349-358`: `position:absolute; left:6px; bottom:6px; z-index:2`).
  It is colorless (`background: var(--color-bg)`, border matches the tile background) unless research
  is already active or has a status, so on a fresh, untouched bucket album it visually blends into the
  tile. Clicking it opens a separate `rsh-modal` (`BucketBoard.tsx:2854-2868`), entirely independent of
  `AlbumDetail`/`MemoWindow`.
- **Confirmed bug**: `.bb-tile-mark` (`myblog_front/src/styles/member/widgets.css:114-131`:
  `position:absolute; bottom:6px; left:6px; width:26px; height:26px;` — no `z-index` set), the "평론
  쓸 것" ✎ mark introduced 2026-07-31 (commit `841f372b`), occupies the **identical corner** as
  `.rsh-cover-badge` (introduced 2026-06-11, commit `e8f32335`) inside the same stacking context,
  `.album-card__badge` (`widgets.css:63-68`, `inset:0`). The mark is 26×26px versus the badge's 12×12px
  and has no z-index, so it visually and functionally swallows clicks aimed at the research dot. The
  mark's own introduction comment reasons about not colliding with the kebab (bottom-right) and the
  listened ring, but never checks the research badge that already occupied that corner — an unreviewed
  regression, not a design decision.
- `MemoWindow` already carries the shared overlay contract (`useDismissable` + `useScrollLock`,
  `component-map.md` registry line 481) and is the **dock host** for `DockableLyricsSheet`
  (`component-map.md:369-371`, `AlbumDetail.tsx`, `hostRef={cardRef}`) — deliberately, so the
  tear/dock state machine never crosses a remount boundary.
- `component-map.md:469` records "my relationship to this album" as four independently-owned write
  silos "by design, not drift": `AlbumRatingBlock` (rating/comment/candidate,
  `PUT /api/reviews/albums/{id}`, `album_reviews` row) / `ReviewCandidates` (a separate read of the
  same `review_candidate` flag) / `MemoWindow`+`useBucketMemo` (`PATCH
  /api/buckets/{bucketId}/items/{itemId}`, `review_bucket_items.note`, bucket-item-scoped) /
  `WriterApp` (`posts` row). Separately, `component-map.md:251-252` documents the *view-layer* split
  ("two hosts, by decision") between the public `AlbumDetailView` and member `AlbumDetail` — this is
  the line this RFC changes.

## Target state

- One modal component opens on every bucket-tile click, regardless of the album's rating/publish
  state — the `MemoWindow` vs. `StandardModal` branch at `AlbumDetail.tsx:58-77` no longer decides
  *which component* opens for the bucket-board context (the public overlay path, `AlbumOverlay.tsx`,
  is untouched).
- That modal surfaces all three:
  - **평가** — a live star + ≤60-char one-liner control wired to the existing
    `PUT /api/reviews/albums/{album_id}` write path via `reviews.api.ts`. Reuse the write path, not
    the whole public `AlbumRatingBlock` component — that panel carries public aggregate stats, a
    review list, and a login CTA that don't belong in a member scratchpad.
  - **메모** — the existing `MemoWindow` free-text + `prep_tonight` toggle, autosave behavior
    unchanged.
  - **리서치 노트** — the existing `ResearchNote` component and `album_research` pipeline, unchanged;
    only its entry point moves.
- `CoverResearchBadge`'s click opens this same unified modal (scrolled/focused to the research
  section) instead of a separate `rsh-modal`. This removes one of the two elements sharing
  `left:6px/bottom:6px`, resolving the collision by elimination rather than by repositioning both
  controls. Whether the tile-corner dot remains clickable or becomes a pure status indicator is an
  implementation call (§Open questions).
- The tile's numeric score badge shows whenever a rating exists, independent of `bucket.isDone`; the
  `미평가` pill keeps its existing `isDone` gate.
- `MemoWindow`'s `useDismissable`/`useScrollLock` registration and its `DockableLyricsSheet` dock-host
  role are preserved exactly — switching between the three sections inside the unified modal must not
  remount the modal's outer shell.
- The exact in-modal layout (tabs vs. stacked sections vs. something else) is decided during Step 1
  against the real 390px screen, per this repo's own precedent of measuring instead of assuming
  (`FEAT-album-review-authoring`'s 60-char decision was made the same way).

## Steps

### Step 1 — unified modal shell, live rating write, tile badge/mark collision fix

What changes:

- Bucket-tile click always opens one modal component; retire the `MemoWindow` vs. `StandardModal`
  branch (`AlbumDetail.tsx:58-77`) for the bucket-board context specifically.
- Replace the dead `미평가` placeholder (`AlbumDetail.tsx:487`) with a live rating write control (star
  input + ≤60-char one-liner) wired to the existing `PUT /api/reviews/albums/{album_id}` path.
- Un-gate the tile's numeric score badge from `bucket.isDone` (`BucketBoard.tsx:1034-1035`); leave the
  `미평가` pill's `isDone` gate as-is.
- Reroute `CoverResearchBadge`'s `onOpen` to the unified modal instead of the separate `rsh-modal`,
  eliminating the dual-click-target collision at `left:6px/bottom:6px` structurally rather than by
  repositioning.
- Preserve `MemoWindow`'s `useDismissable`/`useScrollLock` registration and its directly-mounted
  `DockableLyricsSheet` dock-host role; section switches inside the unified modal must not remount the
  shell.
- Size the rating control for real touch: `HalfStarInput` splits each star into two 50%-wide hit zones,
  which at its current default size is roughly 15×30px per half-star — under typical touch-target
  guidance — so size it up for this context. Re-measure the one-liner's row count against this modal's
  actual (narrower) column width rather than assuming the 460px/280px numbers already measured for
  other surfaces (`FEAT-album-review-authoring`'s prior 60-char check).

**Verification**:
```
pnpm test && pnpm lint && pnpm exec astro check
```
Plus a real-browser (CDP) pass at desktop and 390×844: bucket-tile click opens the same modal shape
regardless of album state; a star click round-trips through the real `PUT` and the value persists on
reload; the tile score badge shows without `bucket.isDone`; clicking the former research-badge corner
reliably opens the unified modal's research section with no missed clicks landing on the ✎ mark;
`DockableLyricsSheet` tear/dock still survives switching between the modal's sections.

**Rollback**: UI-only reroute plus one new write wiring into an existing endpoint — no schema or API
contract change. Revert the PR.

---

## Open questions

1. **Exact in-modal layout for the three sections** (tabs / stacked / accordion / other) — blocks
   Step 1's visual implementation. Resolve against the real 390px screen during Step 1 rather than
   deciding in the abstract here.
2. **Does a star click save immediately, or does the modal need an explicit save action?** — blocks
   Step 1's UX detail. Immediate write plus an undo affordance would match
   `FEAT-album-review-authoring`'s "가볍게" premise, but no owner decision on this specific point is
   recorded yet — confirm at implementation time.
3. **Does the tile-corner research dot stay clickable (routing into the modal) or become a
   non-interactive status indicator only** (with the modal reachable via the tile's main open action)?
   — doesn't block Step 1 either way; decide once real screen space is in front of you.
4. **Resolved 2026-08-09**: shipping Step 1 restarts `FEAT-album-review-authoring`'s re-measurement
   gate clock. Owner decision: the gate's clock resets to Step 1's ship date, not 2026-08-12 as
   originally planned — before Step 1, the bucket-click path had no rating affordance at all, so any
   measurement taken beforehand would be against a known-incomplete entrance. See that RFC's own gate
   note for the resulting date.

## Decisions log

| Date | Decision | Step |
|------|----------|------|
| 2026-08-09 | RFC opened. Two modal-restructure options were proposed in-session (3-tab merge of 평가/리서치노트/메모; click-shows-평가-by-default with 메모/리서치노트 behind a secondary action). An independent design opinion was separately solicited from Opus, which read the code and recommended a third path: leave the three features in their existing separate homes, and just wire a live rating control into `MemoWindow`'s existing dead `미평가` slot — reasoning that 메모 is the higher-frequency action and a tab/reorder would tax it to accommodate 평가's lower frequency. The owner reviewed all three framings and rejected all of them in favor of full unification — reasoning given in-session: 평가 is expected to be the single most frequent action (reversing Opus's frequency assumption), and 리서치 노트's entry point is not merely low-discoverability but **actively broken** in current use (confirmed by code read: `.bb-tile-mark`, introduced 2026-07-31, and `.rsh-cover-badge`, introduced 2026-06-11, occupy the identical tile corner with no z-index coordination — an unreviewed regression, not a documented design choice). Final direction: one modal, always the same shape on click, all three sections reachable inside it; the badge collision is resolved by routing the research entry into that same modal rather than by repositioning two competing corner controls. | 0 |
| 2026-08-09 | Owner accepted the RFC as written (Status: draft → accepted), unblocking Step 1. Owner also resolved Open question 4: `FEAT-album-review-authoring`'s re-measurement gate clock restarts at Step 1's ship date rather than running against the pre-existing 2026-08-12 date. | — |
