# FEAT-bucket-object-collapse: make collapsed buckets tangible without restoring album-card sprawl

- **Status**: superseded 2026-08-12 before production implementation; historical accepted record
- **Owner**: 박지훈
- **Created**: 2026-08-11
- **Plan row**: `docs/plan.md` → FEAT-bucket-object-collapse
- **Superseded by**: `docs/rfcs/FEAT-inline-bucket-object-expand.md`
- **Depends on**: none; no remaining implementation step belongs to this superseded RFC
- **Origin**: 2026-08-11 owner brainstorm + standalone visual prototype using the supplied canonical bucket image and paper-label references

---

> **Correction notice (2026-08-12):** This accepted RFC assumed that the shipped desktop bucket
> selector, mobile selector drawer, and single shared detail pane were the desired structure. The
> owner corrected that assumption before this RFC shipped production code. This file remains intact
> as the historical accepted proposal; do not implement its Step 0 or Step 1. The superseding draft
> `FEAT-inline-bucket-object-expand` owns the inline, independently expandable model and the complete
> state-based motion contract. `ARCH-buckit-navigation-shell` Step 2 (URL-backed selection) was never
> implemented and has been dropped.

## Goal

Preserve the density win of the new My Buckit navigation while making a closed bucket feel like a
real product object instead of a generic disclosure row. A bucket whose album cards are not being
shown is represented by a compact bucket illustration with its name on a paper label immediately
below it. The object keeps the board scannable, uses the bucket's existing color as identity, and
gives selection a short lid-motion cue without delaying access to the existing detail pane.

The causal order is important:

1. The old board showed every bucket and every album card at once.
2. `ARCH-buckit-navigation-shell` fixed that structural problem by showing lightweight navigation and
   exactly one selected bucket detail.
3. This RFC makes that collapsed/navigation state distinctive and enjoyable. The illustration is a
   presentation of the density solution, not the reason for adding another surface.

## Non-goals

- No second collapse, selection, URL, or mobile-drawer architecture. Those belong to
  `ARCH-buckit-navigation-shell`; this RFC consumes the shipped shell.
- No redesign of `BucketDetailShell`, album cards, sorting, filtering, research notes, trash, Undo,
  rename, color editing, or public-collection behavior.
- No new bucket name or color fields. Existing `BoardBucket.name` and `BoardBucket.color` remain the
  source of truth and continue to persist through the existing authenticated mutations.
- No inline rename inside the paper label in v1. The prototype used an input only to prove that
  arbitrary names fit; production rename stays in the existing bucket detail action.
- No label-style marketplace or all-16-label selector. V1 ships one approved label treatment.
- No change to `boardDnd.ts`, `pocketBuckit/boardDnd.ts`, native drag payloads, acceptance rules, or
  system-bucket protection.
- No Pocket Buckit tray redesign and no public `/collection` object treatment in this RFC.

## User-facing problem

The pre-shell board made every new album permanent visual weight: all bucket containers and all of
their album cards were visible together. At the owner's current scale this created a long, noisy
surface where bucket identity was harder to scan than the contents inside it. A normal accordion row
would reduce space but make My Buckit read like generic admin navigation.

The structural half is now shipped: the board shows one selected bucket detail and moves the rest
into a lightweight selector. The remaining product gap is that a closed bucket is represented by a
36px text row with a disclosure glyph, a small color dot, its name, and a lifecycle status. It is
functional and compact, but the bucket metaphor disappears precisely when most buckets are closed.

## Verified current state

Verified 2026-08-11 against `myblog_front` `origin/main` `0d4f525`.

- `BucketBoard.tsx:1656-1724` owns `BucketNavRow`. Each row is a `role="treeitem"` with
  `aria-selected`, optional `aria-expanded`, keyboard selection, native bucket drag handlers, live
  album/bucket drop handling, a color dot, the bucket name, and `CrStatus`.
- Child groups stay mounted and switch `display` under the row. This is load-bearing for the shipped
  collapsed-node drag-and-drop contract; visual work must not replace it with conditional unmounting.
- `BucketNavPanel` is shared by the desktop aside and `BucketNavDrawer`, so one object treatment can
  cover both layouts without parallel implementations.
- Desktop gives the selector `minmax(220px, 280px)` beside the detail pane. Mobile opens the same
  selector in a top-anchored drawer and keeps the selected detail underneath.
- `BoardBucket` already carries `name` and `color`; `BucketBoard` already persists rename and color via
  `api.renameBucket` and `api.setBucketColor`. The current palette is default ink, red, amber, green,
  blue, and violet. No backend or contract work is needed to name or tint the object.
- `ARCH-buckit-navigation-shell` Step 2 remains open. It will add URL-backed selection in the same
  state area. This RFC's read-only Step 0 may run in parallel because it ships no production code;
  Step 1 must not start a competing `BucketBoard.tsx` implementation before that predecessor is
  merged, deployed, and production-smoked.

## Target experience

### Closed / unselected bucket

- Show the canonical bucket artwork as the primary hit target.
- Show the bucket's existing name on an aged-paper label directly **below** the bucket, never pasted
  onto the bucket face.
- Keep the name as real DOM text over a decorative label texture. Do not bake user text into SVG and
  do not expose the decorative image to assistive technology.
- Clamp the visible label to one line with an ellipsis, preserve the full name in the accessible name
  and tooltip, and test Korean, Latin, mixed-script, and the existing maximum-length name.
- Reflect the existing bucket color through a finite, reviewed mapping for the current palette. The
  default/unknown fallback must remain legible and must not silently reinterpret the stored value.

### Selected bucket

- Selection updates immediately through the existing `onSelect` path and shows the existing
  `BucketDetailShell`; the user never waits for animation before content changes.
- The selected object may hold its lid slightly open and receive the existing selected treatment.
  Unselected objects remain closed. Clicking an already-selected object may replay a small tactile
  response but must not deselect or hide the detail pane.
- The lid cue is short (target 160–240ms), transform/opacity-only, and disabled under
  `prefers-reduced-motion: reduce`.

### Tree, drag-and-drop, and status

- Parent/child hierarchy remains discoverable. The child disclosure control stays independent from
  object selection, keeps its accessible name, and does not trigger selection when toggled.
- Every object remains the same native drag source and album/bucket drop target as today's row.
  Accept/reject preview, reject reason, before/after reorder gaps, nested moves, and cycle prevention
  remain behaviorally unchanged.
- Lifecycle status remains visible without covering the name. Exact placement is chosen in Step 0 at
  the real selector widths; status logic itself is untouched.
- Spotify-library and other system nodes keep their existing identity and protections. Whether they
  receive the same physical object treatment is an owner decision (OQ2), not an implementation guess.

### Desktop and mobile density

The object treatment must not re-create the space problem it exists to solve. The standalone
prototype intentionally explored the object and label at a generous size; it is not a production
layout specification. The production selector must be measured at the actual 220–280px desktop
column and 390px mobile drawer with the owner's real bucket names and nesting.

The acceptance threshold is comparative: at the production bucket count, the selector plus one
detail pane must remain materially shorter and calmer than the pre-shell always-expanded board, and
must not require horizontal page scrolling at 390px. Step 0 chooses the exact one-column, compact-grid,
or mixed hierarchy treatment only after this measurement.

## Asset handling

- Use the supplied canonical bucket image as the visual source. Preserve its black outline, handle,
  shading, and recognizable silhouette; do not redraw it as generic CSS geometry.
- Split the single raster into visual body/lid layers by clipping duplicate instances, as proven in
  the prototype, unless an approved separated export becomes available before implementation.
- Use one blank `clean-straight` paper label derived from the supplied label reference. User text is a
  DOM overlay, not embedded SVG text.
- The supplied `buckit-labels-reference-16-svg.zip` is truncated: only labels 01–06 are recoverable and
  the seventh entry is incomplete. Do **not** commit the broken ZIP or treat it as a reproducible
  source archive. V1 needs only the chosen standalone label; a complete re-export is required before
  any future multi-style feature.
- Normalize and compress the chosen runtime assets before committing. The current source bucket PNG
  (~943KB) plus the clean label SVG's embedded texture (~531KB) are reference-quality inputs, not an
  acceptable unreviewed per-page payload. Target a combined transfer size at or below 300KB without a
  visible loss at the rendered size; record actual sizes in the PR body.
- Load each asset URL once and reuse it across objects. Do not generate one image file per bucket or
  per user name.

## Data, API, contract, and infrastructure impact

None. This is a `myblog_front`-only representation of fields and operations that already exist.

- No database migration.
- No backend route or authorization change.
- No OpenAPI regeneration or frontend API type change.
- No API Gateway or Terraform change.
- No localStorage mirror for the bucket name or color; server state remains authoritative.

## Component boundary

Introduce one presentational component local to the bucket board surface (working name
`BucketObjectNavItem`) and have `BucketNavRow` retain ownership of tree semantics, DnD handlers,
selection, disclosure, and status. The object component receives display-only props (`name`, effective
palette key/color, selected state, reduced-motion-safe state) and emits no domain mutation itself.

This boundary keeps the decorative asset and motion code testable without moving the load-bearing
navigation and drag rules out of their current owner. It also prevents the standalone prototype's
editable local input state from becoming a second source of truth for a persisted bucket name.

## Dependency and repository order

Single repository: `myblog_front`.

Step 0 is explicitly **parallel/additive** with `ARCH-buckit-navigation-shell` Step 2: it is a
read-only design measurement, creates no production branch in `myblog_front`, and does not change
selection state. The owner authorized it to start immediately on 2026-08-12.

Step 1 retains the hard predecessor: `ARCH-buckit-navigation-shell` Step 2 must be squash-merged,
deployed, production-smoked, and recorded in that RFC before implementation begins. The reason is
file/state ownership, not conceptual uncertainty: both production implementations touch the same
`BucketBoard.tsx` selection surface.

## Step and PR boundaries

One step per session under workspace rule #4. Step 0 is a concluded design gate and does not ship
production code; Step 1 is one frontend implementation PR.

### Step 0 — real-board object-layout gate (no production code)

Start immediately from the owner-approved recommended baseline — a compact mixed layout, physical
objects for top-level manual/artist buckets, selected lid held slightly open after a short cue, and
`color=null` mapped to neutral ink — then render the bucket + below-label treatment against the real
`BucketNavPanel` constraints: desktop 220px and 280px widths, mobile 390×844 drawer, current production
bucket count, longest real name, at least one nested parent/child pair, one system bucket, and each
palette color. Use the existing standalone prototype only as the visual seed. These are test inputs,
not permission to ignore a failed density or hierarchy gate.

Decide and record:

1. object layout at each viewport (one column, compact grid, or a hierarchy-preserving mix);
2. which node kinds receive the physical object treatment;
3. object/label size, status placement, and disclosure placement;
4. whether selected state holds the lid open or uses a one-shot cue only.

**GO** only if the result remains meaningfully denser than the old always-expanded board, hierarchy
and drag targets stay understandable, Korean names remain readable, and the owner accepts one target
layout. A **NO-GO** concludes the step without shipping and records which constraint failed; do not
force the large standalone prototype into the narrow production selector.

**Verification**: real-browser measurement at 1440px and emulated 390×844×3; keyboard traversal order;
reduced-motion rendering; captured viewport dimensions and chosen object/label sizes in the RFC
Decisions log.

### Step 1 — shared desktop/mobile object navigation

Ship the accepted Step 0 treatment through the shared `BucketNavPanel` path. Add optimized assets,
`BucketObjectNavItem`, palette mapping, selected lid cue, label truncation/accessibility, and styling.
Preserve current `BucketNavRow` semantics and all native DnD/drop-gap behavior. Do not alter the
detail pane or persistence calls.

**Local verification**:

```text
cd myblog_front
pnpm lint
pnpm exec astro check
pnpm test
```

Add focused tests for: bucket name rendering and accessible full name; selected/unselected lid state;
known palette mapping plus unknown fallback; disclosure not selecting the node; reduced-motion class;
and preserved `role="treeitem"` / `aria-selected` / `aria-expanded` state.

**Required real-browser clickthrough**:

- Desktop 1440px: select every object; exactly one existing detail pane updates; selected lid cue and
  name/color match; no album-card sprawl returns.
- Desktop narrow selector: 220px and 280px widths keep label, status, hierarchy, and disclosure usable.
- Mobile 390×844×3 touch: open drawer, select an object, drawer closes, existing detail updates, reopen
  drawer, focus restores, and no page-level horizontal scroll appears.
- DnD: album drop onto closed/unselected object accepts or rejects exactly as before; bucket reorder,
  nested move, reject reason, collapsed-parent drop, and Pocket cross-island drop all still work.
- Rename/color in existing detail: mutation survives reload and the object label/tint updates from
  refreshed server state.
- Keyboard: traverse, select, expand/collapse, and read full names without relying on the image.
- Reduced motion: no lid transform animation, with selection still obvious.

**Pre-merge gate**: PR body quotes all three frontend commands, asset transfer sizes, and the browser
matrix above. Every required PR CI check must be green. No Terraform plan is applicable.

**Post-merge gate**: wait for the frontend deploy, run the standard production smoke, quote the result
in the PR comment, then remove the plan row. Do not claim done before both are complete.

## Rollout and rollback

Normal frontend deploy, no feature flag and no stored-state migration. Rollback is a revert of Step 1
and a frontend redeploy; existing bucket names, colors, hierarchy, selection URL, and detail content
remain valid because none of their shapes change.

## Risks and mitigations

- **The visual metaphor re-introduces vertical weight.** Mitigated by Step 0's real-width density gate;
  the standalone prototype size is explicitly non-normative.
- **A decorative component breaks DnD or tree semantics.** Mitigated by keeping ownership in
  `BucketNavRow` and repeating the shipped collapsed-node/Pocket DnD browser checks.
- **Raster tint does not match stored bucket color.** Mitigated by a finite audited mapping for the
  current palette and an explicit unknown fallback; never synthesize arbitrary filters silently.
- **Long or mixed-script names become unreadable.** Mitigated by real DOM text, a one-line clamp, full
  accessible name/title, and Step 0 tests with real and worst-case names.
- **Animation delays navigation or causes motion discomfort.** Mitigated by immediate selection,
  transform-only short motion, and reduced-motion disablement.
- **Reference assets bloat the bundle.** Mitigated by shipping one optimized bucket asset and one
  chosen label asset, with a measured 300KB combined budget; never ship the broken archive.

## Rejected alternatives

- **Return to independently expanded bucket cards.** Rejected because it restores the album-card
  sprawl that motivated collapse and conflicts with the shipped one-selected-detail architecture.
- **Keep only generic text rows.** Functionally valid but rejected as the product direction: it solves
  density while discarding the bucket metaphor and user-specific identity.
- **Put the name label on the bucket face.** Rejected by the owner; the label belongs immediately below
  the bucket.
- **Bake each bucket name into an SVG.** Rejected because names are mutable user data and must remain
  semantic DOM text without per-name asset generation.
- **Make the paper label an inline input.** Rejected for v1 because rename already has a persisted,
  authenticated owner and an input nested in a draggable/selectable tree item creates competing
  pointer and keyboard behavior. The prototype input was exploratory only.
- **Ship all 16 label variants.** Rejected for v1 on scope, payload, and source-integrity grounds.

## Step 0 decisions to validate

The owner accepted the recommended baseline on 2026-08-12 so none of these blocks Step 0 from
starting. Step 0 must still validate each choice against real geometry before Step 1 treats it as
final:

1. **Layout baseline:** compact mixed layout — top-level objects, hierarchy-preserving compact rows
   below them. Compare against one-column and compact-grid failure modes at the real widths.
2. **Object baseline:** top-level manual/artist buckets only; Spotify, system, and nested nodes retain
   compact rows unless measurement demonstrates a clearer treatment.
3. **Selected-state lid baseline:** short opening cue, then remain slightly open while selected.
4. **Default color baseline:** map `color=null` to neutral ink; explicit red uses the canonical red.

## Relationship to existing RFCs

- **Extends, does not reopen** `ARCH-buckit-navigation-shell`. That RFC owns collapse, selection,
  shared desktop/mobile navigation, URL state, and the detail shell. This RFC changes the closed node's
  visual grammar after its final step concludes.
- **Reuses** `FEAT-bucket-identity` Direction B's typed lifecycle status and existing bucket color; it
  does not infer state from names or redefine the lifecycle.
- **Does not touch** `ARCH-global-playback-experience` or `FEAT-rating-smart-collections` detail
  variants. OQ2 only decides how their selector entries look.
- **Does not touch** Pocket Buckit's tray/object model. Any later reuse requires a separate RFC and
  measurement at that surface's much tighter geometry.

## Decisions log

| Date | Decision | Step |
| --- | --- | --- |
| 2026-08-11 | Drafted from owner brainstorm. The primary problem is album-card density; the bucket illustration is the enjoyable closed-state representation, not a new content surface | — |
| 2026-08-11 | Existing `ARCH-buckit-navigation-shell` confirmed as the structural owner. This RFC is a frontend-only visual follow-up and cannot start before that RFC's Step 2 post-merge DoD | — |
| 2026-08-11 | Owner placed the paper name label below the bucket, not on its face. Production v1 treats it as display text backed by existing persisted rename, not a second inline editor | — |
| 2026-08-11 | Supplied label ZIP confirmed truncated; v1 uses one standalone clean label and never commits the broken archive | — |
| 2026-08-12 | **Accepted by owner.** Owner explicitly approved promotion and immediate Step 0 start. Step 0 is parallel/additive with the still-open navigation-shell Step 2 because it ships no production code; Step 1 remains hard-blocked on that predecessor's post-merge DoD | — |
| 2026-08-12 | Owner accepted the recommended Step 0 baseline: mixed top-level object layout, manual/artist object scope, selected lid held slightly open after a short cue, and neutral-ink `color=null`. Step 0 remains a real-browser GO/NO-GO measurement, not a pre-approved production design | 0 |
