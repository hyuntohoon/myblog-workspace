# ARCH-buckit-inline-navigation: canonicalize the inline-disclosure My Buckit structure

- **Status**: done (Step 1 shipped + deployed 2026-08-16, front #409 `20669c34`) — this RFC's only step
  is shipped; nothing further is planned (the `smart` variant is `FEAT-rating-smart-collections`'s own
  future Step 1, not this RFC's).
- **Owner**: 박지훈
- **Created**: 2026-08-15
- **Plan row**: `plan.md` → ARCH-buckit-inline-navigation
- **Retires**: `ARCH-buckit-navigation-shell` (single-selection `BucketDetailShell` design, reverted
  from production twice — front #401 then #402 — never the shape the owner kept) and
  `FEAT-inline-bucket-object-expand` (pail-artwork inline design, also not what shipped). Neither RFC's
  design matches `myblog_front` `origin/main` today. This RFC is the first to describe the code that is
  actually live.
- **Repository**: `myblog_front` only.

---

## Why this RFC exists

Front #402 (`7057a82`, 2026-08-13) shipped the current inline-disclosure structure directly, without
going through any RFC — the owner's own commit message gives the reason: the single-selection shell
made "every other bucket a name in a sidebar, not a bucket you could see and open in place." #403/#404
built further UI on top of it the same day. For two days no RFC or `plan.md` row reflected this;
`ARCH-buckit-navigation-shell`'s Status line still claimed the shell was live. That staleness was caught
and corrected 2026-08-15 (see that RFC's Decisions log), which left an explicit open owner decision:
write a new RFC for the inline structure, revive the shell, or leave things undocumented. The owner
picked writing this RFC, 2026-08-15, this session.

## Goal

Two things become true:

1. The inline-disclosure structure (`BucketInlineNode`/`BucketInlineList`/`BucketInlineContent` in
   `BucketBoard.tsx`) is the documented, accepted My Buckit navigation model — no RFC has to be
   reverse-engineered from `git log` to know what's live.
2. `BucketInlineContent`'s existing but currently-inert `variant: 'manual' | 'system'` prop becomes the
   named extension boundary that `ARCH-global-playback-experience` Step 4's deferred mount-point half
   and `FEAT-rating-smart-collections` build against, replacing the role `BucketDetailShell`'s
   `manual`/`system`/`smart` dispatch was going to play.

## Non-goals

- **No redesign of the inline-disclosure interaction itself.** Expand/collapse, drag-and-drop-while-
  collapsed, motion, mobile behavior — all shipped and unchanged. This RFC documents and extends, it
  does not modify what #402/#403/#404 already put in production.
- **No URL-backed selection.** There is no "selection" concept in this structure — any number of
  buckets can be open at once, each independently, matching the owner's stated reason for rejecting the
  single-selection shell. Reintroducing URL state for "which bucket is open" is out of scope unless the
  owner asks for it separately.
- **No smart-collection rules.** What 평가 완료 / 평가 예정 contain and how they're derived stays
  `FEAT-rating-smart-collections`'s job. This RFC only confirms where that content would render.
- **No change to `boardDnd.ts` / `pocketBuckit/boardDnd.ts` accept/route rules, `bucket_service.py`
  system-bucket delete protection, or any preserved per-bucket behavior** (research/color/rename/trash/
  filters/Undo) — all confirmed live in *Current state* below, none touched here.

## Current state

Verified 2026-08-15 against `myblog_front` `origin/main` (`706d12c`).

### The live structure

`BucketBoard` renders `<BucketInlineList items={visibleTree} .../>` (`BucketBoard.tsx:3157`) plus a
separate library-bucket list (`:3150`). `BucketInlineList` (`:1862`) maps each bucket to a
`BucketInlineNode` (`:1771`). Each node is its own disclosure object: a button toggles `expandedIds`
(owned by `BucketBoard`, not per-node local state, so reordering/filtering never resets it — see the
comment at `:1760`), and the node's content region (`:1841`, `hidden={!expanded}`) stays mounted
regardless of expand state — the same "collapsed nodes stay mounted" invariant
`ARCH-buckit-navigation-shell` established for its own (different) structure, preserved here for the
same drag-and-drop reason. `BucketInlineNode` recurses: it renders its own `BucketInlineContent`
(`:1845`) immediately followed by a nested `BucketInlineList` for `bucket.children` (`:1854`) when any
exist — this *is* the "each bucket its own object, opening one never closes another" model, already
live, not a proposal.

### The extension point already exists in the type system, but nothing reads it yet

`BucketInlineNode` computes `variant={isSystemBucket(bucket) ? 'system' : 'manual'}` (`:1848`) when
mounting `BucketInlineContent`, and `InlineContentProps` types `variant: BucketInlineVariant` where
`type BucketInlineVariant = 'manual' | 'system'` (`:1126-1127`). **`BucketInlineContent`'s own prop
destructuring (`:1129`) does not include `variant`** — grepping the full function body for the word
`variant` returns only these two lines (the type declaration and the call site that passes it). The
prop is computed and passed on every render and then silently dropped. Every bucket, `system`-kind or
not, renders through the exact same manual member-tile grid today. `isSystemBucket()`
(`lib/bucketLifecycle.ts:29`) checks `SYSTEM_BUCKET_KINDS` (`:26`, `[PLAYBACK_KIND, SLIB_KIND,
TOLISTEN_KIND]`) — so the Playback Bucket, the Spotify-library bucket, and 들을 것 all already compute
`variant: 'system'` today; none of them branch on it.

### Where the richer playback content already lives, unattached to this structure

`ARCH-global-playback-experience` Step 4 (front #408, `43cb425`, 2026-08-15) already built the enhanced
queue view — per-row artwork, summary header, 전체재생, pointer/keyboard reorder — as `PlaybackQueue`
(`PlaybackPanel.tsx:278`). It is mounted from `PlaybackMini.tsx:55` and `PlaybackPanel.tsx:475,527` —
both reached only through the Pocket tray (`PocketBuckit`'s mini/expanded player), never from
`BucketBoard.tsx`. Opening the Playback Bucket inline in My Buckit today shows the same plain manual
tile grid every other bucket gets — no artwork, no summary, no reorder — because `BucketInlineContent`
never sees `variant`.

### `smart` has no representation at all yet

`BucketInlineVariant` is a two-value union (`'manual' | 'system'`). There is no `'smart'` value and no
virtual-bucket concept (a synthetic node not backed by a real `review_buckets` row) anywhere in
`BucketBoard.tsx` — confirmed by the same grep that found zero `variant` reads. `FEAT-rating-smart-
collections` has not been drafted yet (no such file exists in `docs/rfcs/` as of this session) and its
own storage-shape decision (Step 0) is still open, so this is expected, not a gap this RFC has to close.

## Target state

- **`BucketInlineContent` starts reading its `variant` prop and branches on it.** For `variant ===
  'system'`, add a further check: `bucket.kind === 'playback_queue'` renders `PlaybackQueue` (imported
  from `playback/PlaybackPanel.tsx`, the same component the Pocket tray already uses — not a second
  implementation) in place of the manual tile grid; every other `system`-kind bucket
  (`spotify_library`, `to_listen`) keeps rendering the existing manual grid, matching what
  `ARCH-buckit-navigation-shell`'s own Target state already specified for those two kinds. This is the
  concrete, minimal change that unblocks `ARCH-global-playback-experience` Step 4's deferred half — it
  is that step's own implementation, not this RFC's.
- **`BucketInlineVariant` gains a third value, `'smart'`, when `FEAT-rating-smart-collections` is ready
  to consume it.** Not added speculatively here — adding an unused union member ahead of the RFC that
  needs it is exactly the kind of premature abstraction this workspace's conventions warn against. That
  RFC's own Step 1 is the right place to extend the union and pass a `variant: 'smart'` for its two
  virtual buckets (which are not real `review_buckets.id` rows — `BucketInlineNode`'s `bucket: BoardBucket`
  prop type may need a synthetic-node accommodation at that point; not designed here, since the storage
  shape it depends on is still an open owner decision in that RFC).
- **No other change to `BucketBoard.tsx`.** Expand/collapse, DnD, mobile behavior, and every preserved
  per-bucket action are unaffected — this RFC only turns on a dispatch that already exists in the type
  system.

## Data / API / contract impact

**None.** Pure frontend, reusing an already-shipped, already-contract-complete component
(`PlaybackQueue`, whose backend `cover_url` field shipped in `ARCH-global-playback-experience` Step 3).
No new endpoint, no schema change, no `infra/apigateway.tf` change.

## Steps

### Step 1 — wire the `system`/`playback_queue` branch

`BucketInlineContent` destructures `variant`; when `variant === 'system' && bucket.kind ===
'playback_queue'`, render `PlaybackQueue` (reusing the existing component and its existing
`removable`/`limit` props as appropriate for an inline-bucket context — full queue, not the
3-row-preview `PlaybackMini` uses) instead of the manual tile grid. Every other bucket (manual and the
other two system kinds) renders exactly as it does today — this is an additive branch, not a rewrite of
the existing render path.

**Verification**:
```
pnpm lint && pnpm exec astro check && pnpm test
```
Real-browser CDP: opening the Playback Bucket inline in My Buckit shows artwork, summary header,
전체재생, and reorder — the same content and behavior already verified for the Pocket-tray path in
`ARCH-global-playback-experience` Step 4's own Decisions log entry; opening any other bucket (manual or
`spotify_library`/`to_listen`) is pixel-identical to before; collapsing/reopening the Playback Bucket
node preserves queue state (no remount-driven data loss, matching the existing `hidden` mount-preserving
pattern the structure already relies on for DnD).

**Rollback**: frontend-only, single PR, additive branch — revert the PR.

**Shipped 2026-08-16** (front #409, squash `20669c34`, deploy run `31895251995` green): `BucketInlineContent`
now destructures `variant` and branches exactly as specced. `pnpm lint` clean, `pnpm exec astro check` 0
errors, `pnpm test` 643/643 (one `ContextPanel.test.tsx` timeout under full-suite resource contention
confirmed a pre-existing environment flake via isolated + clean full-suite reruns, not a regression).
Real-browser CDP against real prod data (LOCAL dev-server + auth-rewrite proxy to the smoke account) on
the real Playback Bucket (13 tracks) confirmed the summary header (`13곡 · 58:33 총 재생 시간`),
전체재생, keyboard reorder (moved a row, confirmed via the live-region announcement + DOM order, then
reverted to leave no residue), and collapse/reopen queue-state preservation.

**Bug found and fixed during this same pass, not in the original spec**: `PlaybackQueue`'s own CSS
(`pocket.css`) is entirely scoped under `.pb-scope`, a class that previously only ever wrapped the
Pocket tray's DOM (`PocketTray.tsx`). Mounting `PlaybackQueue` bare inside `BucketInlineContent` left
every `.pbp-queue-*` rule unmatched — confirmed via CDP screenshot: the row grid collapsed and the cover
rendered at its natural full image size instead of the intended 28×28px thumbnail. Fixed by wrapping the
inline mount in its own `<div className="pb-scope">` — read `.pb-scope`'s own rules first to confirm it
only defines CSS custom properties + a box-sizing reset (no `position:fixed` or other layout side
effects) before reusing it outside the tray.

---

## Open questions

1. **`PlaybackQueue`'s `removable` prop, and its exact size/limit inside the inline-bucket context** —
   **resolved during Step 1 implementation**: kept `removable` (matching the Pocket tray's full-view
   call) with no size/limit prop (full queue). No conflict exists in practice — the branch replaces the
   manual tile grid entirely for the Playback Bucket, so `AlbumChip`'s remove action is never mounted
   alongside `PlaybackQueue`'s own remove buttons for the same bucket.
2. **`'smart'` variant and virtual-bucket typing** — deferred to `FEAT-rating-smart-collections` Step 1
   as noted in *Target state*. Not drafted here because that RFC's storage-shape decision (Step 0) is
   still open and would make any typing choice here speculative.

## Decisions log

| Date | Decision | Step |
|------|----------|------|
| 2026-08-15 | RFC drafted and accepted same session. Owner chose "document inline-disclosure as canonical" over reviving `BucketDetailShell` or leaving the structure undocumented, given the shell had already been rejected twice in production (front #401 revert, then #402 the same day) — see `ARCH-buckit-navigation-shell.md`'s own Decisions log for the reverted history. Current-state verification (extension-point grep, `PlaybackQueue` mount-site audit) run against `myblog_front` `origin/main` `706d12c` before writing Target state, per house rule (`feedback-rfc-current-state-audit`). | — |
| 2026-08-16 | Step 1 shipped (front #409). Open question 1 resolved during implementation (see above). Found and fixed a `.pb-scope` CSS-scoping gap not anticipated by the original spec — see Step 1 note. This RFC has no further steps; done. | 1 |
