# FEAT-inline-bucket-object-expand: restore inline buckets with independent object expansion

- **Status**: accepted (2026-08-12; Step 0 concluded NO-GO, production Step 1 blocked)
- **Owner**: 박지훈
- **Created**: 2026-08-12
- **Plan row**: `docs/plan.md` → FEAT-inline-bucket-object-expand
- **Supersedes**: `FEAT-bucket-object-collapse` before its production implementation
- **Corrects**: the deployed structure from `ARCH-buckit-navigation-shell` Steps 1 and 3
- **Depends on**: no URL-selection step and no other RFC; production work begins only after the gate in *Exact implementation start condition*
- **Repository**: `myblog_front` only

---

## Goal

Restore My Buckit's inline content flow while adding a tangible collapsed state. Each real bucket node
is its own independently expandable object:

```text
[Closed bucket object + paper label]
[Open bucket object + paper label]
  └ Existing content and controls for that bucket
[Open bucket object + paper label]
  └ Existing content and controls for that bucket
[Closed bucket object + paper label]
```

Opening one bucket never closes another. The existing bucket body stays with the bucket that owns it;
there is no navigation selector and no shared detail destination. Motion communicates logical and
drag-and-drop state rather than decorating a selection change.

## Why this is a superseding RFC

`FEAT-bucket-object-collapse` was accepted on 2026-08-12, but it assumed the already-deployed
navigation shell was the desired foundation. Rewriting that accepted proposal would erase why it was
accepted and how its dependency was understood. The accepted file is therefore retained as a
historical record and marked superseded. This RFC contains the corrected implementation contract.

Likewise, `ARCH-buckit-navigation-shell` Steps 1 and 3 were already merged, deployed, and production-
smoked. Their history remains in that RFC and Git. This RFC defines corrective removal from the
deployed state; it does not relabel the shipped work as if it never happened.

## Verified current deployed structure

Verified 2026-08-12 against `myblog_front` `origin/main` `0d4f525`, with the relevant history at
`7921a9f` (front #396) and `7a597f7` (front #397).

- `BucketBoard.tsx` owns one `selectedBucketId` and automatically selects the first manual root (or
  the Spotify library fallback) after the tree loads or the selected bucket disappears.
- `BucketNavRow` is a lightweight `role="treeitem"` selection and drop surface. Its own local
  `expanded` state only shows or hides descendant navigation rows; it does not expand that bucket's
  content inline.
- `BucketDetailShell` / `BucketDetailBody` renders the complete content for exactly one selected
  bucket. Switching buckets replaces that one detail subtree.
- Desktop renders a two-column grid: `minmax(220px, 280px)` navigation aside plus one detail main.
- Mobile uses a full-width trigger and `BucketNavDrawer`; choosing a row closes the drawer and swaps
  the one detail main underneath.
- No bucket URL selection shipped. `BucketBoard.tsx` contains no bucket path/query handling and no
  `pushState` or `replaceState`; reload and back/forward do not restore or change the selected bucket.
- The existing detail body still contains the pre-shell album/track/artist tiles, add actions,
  rename, color, research, public state, lifecycle status, sort/group/genre/type filters, nested
  hierarchy behavior, trash/Undo flows, album modal entry, mobile `ActionSheet`, and native DnD.
- `useBucketDropTarget` still delegates acceptance and routing to `lib/boardDnd.ts`; Pocket cross-
  island DnD still uses `lib/pocketBuckit/boardDnd.ts` and `lib/pocketBuckit/events.ts`.
- System deletion protection remains backend-authoritative in
  `myblog_backend/app/services/bucket_service.py`; frontend guards are only a mirror.

### Historical inline baseline confirmed from Git

The parent of the shell merge, front `01c6e35`, used `BucketList` → `BucketCard` recursion.
`BucketCard` rendered its own header, controls, member grid, and then its child `BucketList` in the
same document flow. It did not yet have collapse state, but it proves that the preserved behaviors
already had an inline owner before #396 moved them into the selected-detail shell.

## Incorrect assumptions removed

This RFC removes the following assumptions from future work:

1. Density requires exactly one selected bucket detail.
2. A desktop navigation aside is the correct owner of bucket hierarchy.
3. Mobile needs a bucket-selection drawer before content can be reached.
4. A shared `BucketDetailShell` must be the only rendering destination for manual, system, or future
   smart content.
5. Bucket opening is navigation or selection and should be URL-addressable.
6. Parent disclosure and bucket-content visibility are separate user actions.
7. A short selected-lid cue is a sufficient animation contract.
8. Only top-level manual buckets should receive the physical-object treatment.

The correct density mechanism is independent inline collapse: closed buckets are compact objects;
open buckets reveal only their own existing content.

## Final inline behavior and state ownership

### Node structure

Each real bucket node owns, in order:

1. one bucket-object toggle containing the canonical artwork and the paper label;
2. that bucket's existing content region when open;
3. its existing nested child-bucket list in the same hierarchy position.

The object and label are one activation target. The paper label stays directly below the object, and
the name is real DOM text over the decorative label asset. Edit, filter, add, menu, and other controls
remain inside the expanded content; they are not nested inside the toggle.

For a parent bucket, closing hides its content and descendant presentation without mutating any
descendant's open bit. Reopening the parent restores each child's prior in-memory open/closed state.
Deleting a bucket removes its id from open state.

### Local state

`BucketBoard` owns an in-memory `Set<string>` of expanded bucket ids keyed by stable bucket id. A
per-node equivalent is acceptable only if it demonstrably survives reorder and filter hide/show with
the same behavior. The set is UI state layered over the server-synced tree:

- default after mount or reload: closed;
- toggle adds or removes only that bucket id;
- several ids may be present simultaneously;
- no `localStorage`, `sessionStorage`, cookie, server field, API mutation, path, or query parameter;
- no `pushState`, `replaceState`, `popstate` selection listener, reload restoration, or browser-
  history entry;
- browser back/forward may still change the dashboard's existing top-level route/tab, but it never
  opens, closes, or switches an individual bucket.

## Existing behavior that must remain inside each bucket

The correction moves ownership back inline; it does not redesign the existing bucket body. Preserve:

- album, track, artist, library, playback, and other existing member rendering;
- album detail modal entry and existing rating/memo/research behavior;
- add, rename, color, research-mode, public-state, lifecycle-status, and bucket action controls;
- sort, group, genre filter, type filter, manual ordering, and filtered-empty states;
- nested bucket creation, reordering, moving, cycle prevention, and parent/child display;
- album copy/move/reorder, library rules, Artist expansion rules, Playback acceptance, reject reasons,
  trash, restore, delete confirmation, and Undo;
- Pocket-to-board and board-to-Pocket event bridge behavior;
- mobile `ActionSheet` fallback and all coarse-pointer actions;
- server-authoritative protection of `playback_queue`, `spotify_library`, and `to_listen`, including
  protection of an ancestor whose deletion would cascade through a system bucket.

No preserved control may move into a global/shared detail surface.

## Deployed behavior requiring corrective removal

The production PR must remove or stop using the following board structure introduced by #396/#397:

- `selectedBucketId` and the first-bucket auto-selection effect;
- `BucketNavPanel`, `BucketNavRow`, and `BucketNavList` as a separate selection UI;
- `aria-selected` bucket semantics and tests that assume exactly one selected detail;
- the desktop two-column selector/detail grid and `aside`;
- the mobile bucket trigger, `navDrawerOpen`, and `BucketNavDrawer`;
- `BucketDetailShell` as a one-at-a-time shared destination. Its content implementation may be reused
  or renamed, but it must render under the bucket that owns it;
- current tests and comments whose contract is "switch selection to render bucket B."

Do not remove `useIsMobileHost` merely because the drawer disappears; `AlbumDetail` is an independent
consumer. Do not remove DnD helpers, content controls, or server protection with the shell.

There is no URL-backed bucket selection to revert because Step 2 never shipped.

## Complete interaction and motion specification

### Located sources

The previous standalone prototype is preserved outside the repositories at:

`/Users/park_hyun/.codex/visualizations/2026/08/11/019ff0d2-46c2-7972-bb31-1a69269062d4`

Its implementation is `app/BucketPrototype.tsx` plus `app/globals.css`. The workspace root also has
the untracked source/reference inputs:

- `buckit-bucket-base-canonical.png`;
- `buckit-bucket-motion-states-reference-a.jpeg`;
- `buckit-bucket-motion-states-reference-b.jpeg`;
- `buckit-labels-reference-16-svg-verified.zip`.

The reference boards confirm the named visual states `IDLE`, `HOVER`, `DRAG`, `DROP`, `MOVE`,
`INVALID`, `DELETE`, and `LOCKED`. They show lift/ghosting on drag, an upright handle during drag,
an open lid for drop, movement trails, rejection emphasis, and a locked treatment, but contain no
numeric timing, easing, transform, halo, or shake constants.

### Verified exact prototype values

These values are evidence, not estimates. Preserve them for the matching production state unless the
Step 0 gate records an owner-approved replacement:

| Concern | Verified value | Source |
| --- | --- | --- |
| Art response | `transition: transform .45s cubic-bezier(.2,.8,.2,1)` | prototype `app/globals.css` |
| Logical open lift | `translateY(-4px)` | prototype `.bucket-art.is-open` |
| Lid layer crop | body `clip-path: inset(14% 0 0 0)`; lid `inset(0 0 79% 0)` | prototype layer split |
| Lid pivot | `transform-origin: 82% 17%` | prototype `.bucket-lid` |
| Lid spring-like transition | `transform .62s cubic-bezier(.22,1,.36,1)` | prototype `.bucket-lid` |
| Open lid endpoint | `translate(-10%, -15%) rotate(-18deg)` | prototype `.bucket-art.is-open .bucket-lid` |
| Hover | `translateY(-8px) rotate(-1deg)` | prototype trigger hover |
| Pressed | `translateY(-3px) scale(.98)` | prototype trigger active |
| Focus-visible | `2px solid` ink outline, `8px` offset | prototype trigger focus |
| Base art shadow | `drop-shadow(0 15px 10px rgba(20,18,15,.2))` | prototype `.bucket-art` |
| Asset-filter transition | `.4s ease` | prototype image layers; not approval to recolor |
| Reduced motion | all animation and transition durations forced to `.01ms !important` | prototype reduced-motion query |
| Current valid-drop halo | `0 0 0 3px color-mix(in srgb, var(--color-accent) 14%, transparent)` plus `1px` accent border | deployed `BucketNavRow` / detail drop surface |
| Current source/reject fade | dragged bucket opacity `.45`; rejected target opacity `.4`; related transitions `.12s` | deployed `BucketNavRow` / pre-shell card history |

The prototype's lid response is CSS cubic-bezier motion, not a physics-spring library. Do not silently
translate it into different spring parameters.

### Required state machine

The component exposes logical states `closed`, `opening`, `open`, and `closing`, plus orthogonal
interaction states `hover`, `focus-visible`, `pressed`, `dragging-source`, `valid-drop-target`,
`rejected-drop`, `item-received`, and `disabled`.

- **Closed → opening → open:** click, Enter, or Space updates `aria-expanded` and starts the verified
  art/lid transition. Content expansion belongs to the same bucket region; it must not wait for the
  lid animation to become usable. No content-height/opacity transition values were found; use an
  immediate content state unless Step 0 records approved values.
- **Open → closing → closed:** the same inputs reverse the verified endpoints. Closing one bucket
  changes no sibling or descendant open bit.
- **Lid motion:** use the verified pivot, endpoint, `.62s` duration, and easing in both directions.
  It is the primary open/close state cue.
- **Handle motion:** a light handle spring is required. The reference boards confirm the handle rises
  for drag and responds at its hinges; the available single raster and prototype do not provide an
  independently animated handle or exact constants. Step 0 must prove a non-destructive layer method
  and record its pivot, endpoints, duration, and easing before production CSS is written.
- **Hover:** use the verified hover transform only on hover-capable pointers. It must not imply open.
- **Focus-visible:** the verified outline remains visible regardless of lid, drag-target, or received
  feedback. Focus is additive, not a transform competitor.
- **Pressed:** use the verified pressed transform while activation is held; release resolves toward
  the new logical open or closed endpoint.
- **Dragging source:** on drag start the object rotates, lifts, gains a stronger shadow, and raises the
  handle as confirmed by the reference boards. The exact rotation, lift, shadow, handle transform,
  duration, and easing were not found and are a Step 0 blocking constant set. The deployed `.45`
  source opacity may be retained only if the calibrated object state remains legible.
- **Valid drop target:** use the exact deployed `1px` accent border and 3px/14% halo. The reference
  boards confirm an open-lid acceptance cue; the verified open lid endpoint may be used as a temporary
  visual preview without changing logical expansion. Leaving the target returns to its actual logical
  open/closed endpoint.
- **Rejected drop:** keep the current reject reason and add the required one-shot shake. It must not
  open the lid or reflow neighbors. Shake keyframes, distance, duration, and easing were not found and
  are a Step 0 blocking constant set; do not infer them from the still images.
- **Item received:** after a successful routed drop, play a distinct one-shot received response, then
  settle to the bucket's actual logical open/closed endpoint. It does not toggle expansion. The
  response's lid/handle/body sequence and exact constants were not found and are a Step 0 blocking
  constant set.
- **Disabled:** suppress hover, pressed, drag source, and drop-target motion; expose the semantic
  disabled state and a non-motion visual. Do not treat every system bucket as disabled: system-bucket
  delete protection is action-specific, while opening and allowed drops remain available. The
  reference `LOCKED` frame confirms the state but supplies no exact opacity, color, or transition.

No motion loops while idle. Every animation must explain an input, logical transition, allowed drop,
rejected drop, or completed receipt.

### State priority and conflict resolution

Transform and feedback channels resolve in this order, highest first:

1. `prefers-reduced-motion` removes non-essential interpolation while preserving immediate states;
2. `disabled` blocks pointer/drag motion;
3. `dragging-source` owns the source object's body/handle/shadow transform and ignores click toggle;
4. `rejected-drop` overrides valid-target and lid-preview feedback on the target;
5. `valid-drop-target` owns the halo and temporary acceptance lid preview;
6. `item-received` runs only after the successful drop has cleared valid-target state;
7. `opening` / `closing` / `open` / `closed` provide the logical resting endpoint;
8. `pressed`, then `hover`, modify only when none of the higher transform states is active.

`focus-visible` is always additive and never removed by this priority. When a drag ends or leaves, the
object reconciles to its logical open/closed endpoint; DnD feedback never mutates the expanded-id set.

### `prefers-reduced-motion`

Under `reduce`:

- keep the prototype's verified `.01ms !important` duration override or an equivalent effectively
  immediate state change;
- no spring interpolation, lift, rotation, shake, bounce, or item-received travel;
- open/closed remains visible through the static lid endpoint and `aria-expanded`;
- valid drop retains the static border/halo and reject retains its reason/non-motion invalid styling;
- received state uses a brief static highlight only if Step 0 records an accessible, non-motion value;
- focus outline, disabled semantics, and all functionality remain unchanged.

## Desktop and mobile behavior

Desktop and mobile use the same inline component tree and activation model.

- Buckets appear in normal document order, one inline node after another; no desktop selector column.
- Each open bucket's current responsive tile/content layout expands directly beneath its object.
- Nested buckets retain visible indentation/containment and existing ordering. A closed parent hides
  descendants from interaction; reopening restores their retained in-memory state.
- Mobile scales the object/label only after measurement, keeps the expanded content in document flow,
  and retains the existing `ActionSheet` touch fallback. There is no bucket-selection trigger or
  drawer.
- Neither viewport creates horizontal page scrolling for the longest required names or nested content.

## Drag-and-drop and hierarchy contract

- The closed object wrapper remains an album and bucket drop target; users need not open it before a
  valid drop.
- The open object's header/content and the object wrapper route through the same current acceptance
  helpers so preview and completed routing cannot drift.
- Album reorder inside an open bucket, cross-bucket move/copy, library rules, Artist source expansion,
  Playback album/track acceptance, Pocket bridge events, and trash behavior remain unchanged.
- Bucket reorder gaps, top-level unnest, nesting, and cycle prevention remain available in the inline
  hierarchy. Feedback must not cause layout reflow.
- A drop onto a closed bucket may update its data and play item-received feedback, but must not open it.
- Closing a parent makes hidden descendants non-targetable; it does not clear their local open bits.

## Keyboard and accessibility

- Implement the object as a native button or equivalent native disclosure control, not a clickable
  image-only `div`.
- Enter and Space toggle only that bucket. Pointer activation and keyboard activation are equivalent.
- Expose `aria-expanded` and `aria-controls` linking the object to its own content region. The region
  has an accessible name derived from the full bucket name.
- The button's accessible name contains the full untruncated bucket name and open/close purpose.
- The decorative canonical image and paper texture have empty alternative text / are hidden from the
  accessibility tree; the bucket name is real DOM text.
- Visual truncation may use an ellipsis, but it must not truncate the accessible name. Verify long
  Korean, English, and mixed-language names.
- Use the verified focus-visible outline and maintain logical tab order through object, then its open
  controls/content, then the next bucket.
- Do not reuse `aria-selected`; this is disclosure, not single selection.
- Disabled and action-specific system protection must be announced without disabling allowed open or
  drop behavior.

## Asset constraints and destinations

The canonical sources are currently untracked at the shared workspace root; none is in
`myblog_front` `origin/main`. The production PR must add only the selected runtime files:

| Source | Required runtime destination |
| --- | --- |
| `buckit-bucket-base-canonical.png` | `myblog_front/public/buckit/buckit-bucket-base-canonical.png` |
| ZIP entry `buckit-label-01-clean-straight.svg` | `myblog_front/public/buckit/buckit-label-01-clean-straight.svg` |

`buckit-label-01-clean-straight.svg` is selected because its paper substrate is the label used by the
prior prototype and it is present in the now-complete verified 16-entry archive. Do not ship the ZIP,
the other 15 candidates, either motion-reference JPEG, or any per-bucket/name derivative.

**Step 0 correction:** the visual paper substrate is the same, but the two SVG files are not byte-
identical. The ZIP entry contains a literal SVG `<text>` node with `MY BUCKIT`; the prototype's
`public/bucket-label.svg` removes that node so the editable/DOM text is not doubled. Their embedded
paper PNG payloads have the same SHA-256 (`a145891d836bd725cf5fb69caf80fcb99eac0c1ed46e0f0a9476c389c71ab744`).
The ZIP entry therefore cannot be copied to the runtime destination unchanged while also satisfying
the real-DOM-text rule. Step 1 stays blocked until the blank runtime source/normalization is explicitly
resolved; Step 0 did not extract or modify either supplied file.

- Use only the canonical bucket raster. Do not redraw it with CSS shapes or replace it with an SVG.
- Layering clipped duplicates of the same canonical image is allowed only where the prototype proves
  the body/lid split; independent handle layering still requires the Step 0 visual-integrity proof.
- Keep the paper label below the bucket and render its name as DOM text over the texture.
- Normalize/optimize the two selected runtime assets without changing the outline, shading, texture,
  or silhouette; record source and output checksums/sizes in the implementation PR.
- The prototype contains exact CSS filter experiments for blue, green, violet, and orange, but no
  comparison proved that they preserve the black outline, shading, or paper-like texture. They are
  evidence of an experiment, not an approved palette mapping.
- Step 0 must compare every existing stored bucket color at production render size. If reliable
  recoloring is not demonstrated, every object uses the canonical red image and existing color
  identity remains as a separate DOM swatch/accent in the expanded header/object metadata. Do not
  invent a filter or create colored image files.

## Data, API, contract, and infrastructure impact

None. This is a frontend render/state correction over the existing tree and operations.

- no schema, migration, backend, authorization, API Gateway, Terraform, OpenAPI, or generated type
  change;
- no new persistence field or endpoint;
- no synchronous Spotify request;
- no URL contract.

## Implementation steps and dependencies

One RFC step per session. Step 1 is a declared single corrective production PR because removing the
only current renderer without installing the inline renderer in the same deploy would leave My Buckit
unusable.

### Step 0 — motion and asset evidence gate (no production code)

Use the located prototype and the four supplied inputs; do not make a substitute asset. Record in this
RFC:

1. exact handle pivot/endpoints/duration/easing and proof that independent handle motion does not
   damage the canonical raster;
2. exact drag-start rotation/lift/shadow/handle values;
3. exact invalid-shake keyframes/distance/duration/easing;
4. exact item-received sequence/transforms/durations/easing;
5. exact disabled non-motion visual values and whether content reveal stays immediate or receives an
   approved non-layout-shifting transition;
6. color-by-color recolor comparison and the canonical-red fallback decision;
7. final production object/label sizes at desktop and 390×844 mobile;
8. reduced-motion static states.

Values must first be recovered from an earlier source not yet found. If recovery still fails, Step 0
stops and records the gap; defining new measured values requires separate explicit owner authorization.
The owner granted that authorization on 2026-08-12 for a separate measured-specification recovery task,
not for the production PR. Values must be measured and recorded there, never guessed during production
implementation. A NO-GO on
independent handle layering selects a non-destructive no-handle-motion fallback only with explicit
owner approval; it does not authorize redrawing the bucket.

#### Step 0 conclusion — NO-GO (2026-08-12)

**Result: NO-GO.** No production code or runtime asset was changed. Production Step 1 remains blocked;
this evidence pass did not authorize new motion/layout values or the no-handle-motion fallback.

Evidence searched:

- the standalone prototype's source, compiled client/server chunks, public/dist assets, and build
  metadata;
- the complete original Codex session record
  `rollout-2026-08-11T21-35-40-019ff0d2-46c2-7972-bb31-1a69269062d4.jsonl`, including the owner
  discussion before and after the prototype and label work;
- all reachable relevant workspace and `myblog_front` refs/history, including workspace `12c864b`,
  `40b3266`, `36f8e88`, `44d35e1` and front `01c6e35`, `7921a9f`, `7a597f7`, `0d4f525`; searches
  covered bucket-object/asset names, handle/hinge, drag transforms/shadows, shake/invalid,
  received/drop, disabled/locked, reduced motion, sizing, and recolor/filter terms;
- both 1536×1024 reference boards, the 1536×1024 RGBA canonical raster, and the verified label ZIP
  (all 16 entries pass `unzip -t`).

Confirmed asset facts:

- the supplied canonical PNG and the prototype's `public/bucket-canonical.png` are byte-identical
  (SHA-256 `9f60d9b474852a9c6fb8f628003047bb1f4f9a04886468295bbd75928306021f`);
- the canonical PNG is one flattened raster. Its lowered handle is already composited over the body.
  Moving a clipped duplicate would leave the original lowered handle visible; masking it would also
  remove the hidden red body shading/texture, which the source does not contain. The boards show an
  upright drag handle but provide neither a clean handle layer nor the pixels behind the lowered one.
  **Non-destructive independent handle isolation is not proven and is NO-GO with the supplied art.**
- the lid/body clipped-duplicate method remains proven only for the prototype's existing lid motion;
  it does not extend to the handle.
- the selected archive label's paper payload matches the prototype, but the archive entry includes
  fixed SVG text while the prototype uses a blank derivative, as recorded above.

Missing-value result:

| Required Step 0 fact | Result after search |
| --- | --- |
| Handle pivot/endpoints/duration/easing | unavailable; no independent handle layer or constants found |
| Drag-start rotation/lift/shadow/handle response | unavailable; only deployed source opacity `.45` and related `.12s` transitions remain verified |
| Invalid shake | unavailable; deployed reject reason, opacity `.4`, and `.12s` transitions are verified, but no shake keyframes/distance/duration/easing exist |
| Item received | unavailable; no sequence, transforms, duration, easing, or static reduced-motion highlight value found |
| Disabled visual | unavailable; `LOCKED` is only a qualitative board frame with no opacity/color/transition constants |
| Content reveal | no prior transition values found; retain the accepted RFC's immediate reveal default, with no invented interpolation |
| Reduced motion | `.01ms !important`, static lid endpoint, valid halo, reject reason, and focus semantics remain verified; received highlight stays unavailable |

Size evidence is prototype-only and non-normative: desktop CSS uses a `162×214px` object and
`158×46px` label; at an actual 390×844 viewport its media rule renders a `142×190px` object and
`146×43px` label. The original session explicitly left actual profile placement/size and mobile
scaling for later production decisions, and the obsolete selector-layout RFC also calls the prototype
size non-normative. **Final production object/label sizes for desktop and 390×844 are unavailable.**

Color-by-color result against the deployed stored palette:

| Stored value | Step 0 result |
| --- | --- |
| `null` (default ink) | no raster mapping; `filter: none` remains canonical red |
| `#c8332b` (red) | canonical `filter: none` is the only proven non-destructive treatment |
| `oklch(0.66 0.12 70)` (amber) | no prototype mapping |
| `oklch(0.58 0.10 155)` (green) | prototype green filter keeps outline/shading visibly present at prototype sizes, but is not calibrated to this stored value |
| `oklch(0.56 0.10 245)` (blue) | prototype blue filter keeps outline/shading visibly present at prototype sizes, but is not calibrated to this stored value |
| `oklch(0.55 0.11 300)` (violet) | prototype violet filter keeps outline/shading visibly present at prototype sizes, but is not calibrated to this stored value |

The prototype's orange filter has no matching stored palette value. Because two stored cases have no
mapping and the other non-red mappings are uncalibrated experiments, reliable recoloring of every
existing bucket color is not demonstrated. The already-specified fallback therefore applies: use the
canonical red raster for every object and preserve color identity in a separate DOM swatch/accent.

#### Step 0 recovery decision — measured specification authorized (2026-08-12)

The owner selected recovery option 1 after reviewing the NO-GO. A separate measured-specification task
is authorized to define the missing motion, layout, disabled, and reduced-motion values and to resolve
the blank runtime label source or a normalization path. This is authorization to perform and document
the measurement/design work; it is not approval of any particular constant, independent-handle
fallback, label transformation, replacement artwork, runtime asset, or production implementation.

The recovery task must preserve every already-verified constant, use the canonical art without
destructive layer extraction or redraw, compare proposed behavior at desktop and 390×844, and record
the resulting exact values and label-source decision in this RFC. It must conclude with either:

1. **GO** — every implementation-start fact is exact and the label path is explicitly resolved; or
2. **NO-GO** — the remaining exact blocker is recorded without starting production Step 1.

Until that conclusion is merged, the existing Step 0 NO-GO remains effective and production Step 1
stays blocked. The no-handle-motion fallback remains unapproved unless the recovery task presents it
and the owner explicitly accepts it.

### Step 1 — single corrective inline implementation PR

After Step 0 GO, remove the deployed selector/shared-detail structure, restore recursive inline
ownership, add independent local expanded ids, add the two selected runtime assets, implement the
approved state machine, and update focused tests. Preserve all behavior named above.

Run:

```text
cd myblog_front
pnpm lint
pnpm exec astro check
pnpm test
```

Because this changes frontend UI, complete a real-browser clickthrough before merge. After required PR
checks pass, squash merge, wait for the normal frontend deploy, run production smoke, quote the smoke
result in the PR comment, and then remove the plan row.

## Regression and production-smoke matrix

The future implementation is not green until it verifies all of the following:

- open buckets A and B; both content regions remain present; close A and B remains open;
- every existing bucket content/control class named in this RFC works inside its own expanded region;
- clicking/toggling buckets leaves `location.pathname`, `location.search`, `location.hash`,
  `history.length`, and back/forward behavior unchanged for bucket state; spies observe no
  `pushState`/`replaceState` from bucket toggles;
- parent close/reopen, retained child open bits, indentation, reorder, nesting, unnesting, and cycle
  rejection behave correctly;
- album reorder/copy/move and bucket drag work for open and closed targets as applicable;
- valid halo, invalid reason + shake, and successful item-received response are distinct;
- Enter and Space open/close, focus-visible is visible, and `aria-expanded` / `aria-controls` match the
  rendered region;
- long Korean, long English, and mixed-language names truncate visually without losing the full
  accessible name;
- desktop and mobile inline layouts have no selector/drawer and no horizontal page scroll;
- reduced motion has immediate/static equivalents and no spring/lift/rotation/shake/received travel;
- system buckets remain openable and accept only their current allowed items, while delete and
  ancestor-cascade protection remain unchanged;
- mobile `ActionSheet`, album modal, Pocket cross-island DnD, trash, restore, and Undo still work;
- production smoke passes after deploy and the result is quoted in the PR comment.

## Exact implementation start condition

Production Step 1 may begin only when all three conditions are true:

1. the owner explicitly promotes this RFC from `draft` to `accepted` in-session;
2. Step 0 records a GO with every currently missing motion constant or an explicitly approved
   non-destructive fallback, plus the label, size, reduced-motion, and recolor decisions;
3. current `origin/main` is rechecked and no conflicting unmerged `BucketBoard.tsx` work or foreign
   worktree commits exist.

`ARCH-buckit-navigation-shell` Step 2 is not a condition; it is dropped and must remain unimplemented.

## Explicit non-goals

- No bucket path/query/deep link, URL restoration, history integration, or shareable open state.
- No desktop selection panel, mobile bucket-selection drawer, or single shared detail panel.
- No persistence of open/closed state across reload.
- No redesign of album/track cards, bucket controls, DnD rules, Pocket Buckit, public collections,
  Playback architecture, or smart-collection derivation.
- No backend, database, contract, auth, API Gateway, or infrastructure work.
- No CSS-drawn or replacement-SVG bucket, no per-bucket image, and no shipping all label candidates.
- No unverified recolor filter and no destructive attempt to separate raster layers.
- No decorative idle loop or animation that delays content access.

## Unresolved facts and search record

Searched 2026-08-12:

- current `myblog_front` `origin/main` and reachable Git history, including shell merges `7921a9f` /
  `7a597f7`, the pre-shell parent `01c6e35`, reject visual history, and existing member animation CSS;
- workspace RFC/plan Git history (`12c864b`, `40b3266`, and navigation-shell records);
- the standalone visualization source and its session record at the path above;
- both motion-reference JPEGs, the canonical PNG, and the complete verified label ZIP listing.

Confirmed: inline pre-shell ownership; current deployed single-selection structure; absence of URL
wiring; full prototype lid/hover/pressed/focus/reduced-motion values; reference-board state intent;
current valid halo and reject/source opacity values; canonical and label filenames.

Step 0's expanded source/session/all-ref search is recorded in its conclusion above. Still unavailable:
independent handle constants and a non-destructive layer; drag-start rotation/lift/shadow/handle
constants; invalid-shake constants; item-received sequence/constants and reduced-motion highlight;
exact disabled styling; final desktop/mobile production sizes; and a complete calibrated palette
mapping. No content-region transition evidence exists beyond immediate visibility. The blank label
runtime source also needs explicit resolution because the verified archive entry contains fixed text.
These gaps produced the Step 0 NO-GO and continue to block production Step 1. The owner has authorized
a separate measured-specification recovery task to resolve them, but no particular new value or asset
operation is approved yet; the authorization does not justify guessed production numbers, destructive
raster edits, or replacement artwork.

## Decisions log

| Date | Decision | Step |
| --- | --- | --- |
| 2026-08-12 | Owner corrected the structure to independent inline expansion and prohibited desktop/mobile selection surfaces, shared detail, URL state, and history writes | — |
| 2026-08-12 | Accepted `FEAT-bucket-object-collapse` is preserved as a superseded historical record rather than materially rewritten; shipped navigation-shell Steps 1/3 remain recorded and become explicit corrective removal targets | — |
| 2026-08-12 | Selected `buckit-label-01-clean-straight.svg` from the complete verified archive because it is the exact prior-prototype label; only it and the canonical bucket image may become runtime assets | — |
| 2026-08-12 | Restored every confirmed prototype motion value and separated missing constants into a blocking evidence gate instead of inventing values | — |
| 2026-08-12 | **Accepted by owner.** Step 0 motion/asset evidence work may start; production Step 1 remains blocked until Step 0 records GO and the remaining implementation-start conditions are rechecked | — |
| 2026-08-12 | **Step 0 NO-GO.** Prototype source/build/session, all reachable relevant workspace/front refs, canonical/board inputs, and the verified 16-label archive yielded no handle, drag-start, shake, received, disabled, or final production-size constants. The flattened canonical raster cannot isolate and move the handle non-destructively | 0 |
| 2026-08-12 | Reliable full-palette recoloring is not demonstrated, so the RFC's canonical-red raster plus separate DOM color-accent fallback applies. The selected ZIP label also contains fixed `MY BUCKIT` text while the prototype uses the same paper payload blank; production remains blocked pending explicit fallback/value and blank-label-source decisions | 0 |
| 2026-08-12 | **Owner selected recovery option 1.** A separate measured-specification task may define the missing motion/layout/disabled/reduced-motion values and resolve a blank-label source or normalization path. No particular value, handle fallback, label transformation, runtime asset, or production implementation is approved by this decision; Step 1 remains blocked until the recovery task records GO | 0 recovery |
