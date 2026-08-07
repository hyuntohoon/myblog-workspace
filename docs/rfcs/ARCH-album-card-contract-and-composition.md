# ARCH-album-card-contract-and-composition: one canonical album-card display model, composed by capability, not inherited

- **Status**: accepted
- **Owner**: TBD
- **Created**: 2026-08-06
- **Plan row**: removed after Stage 9 post-merge Definition of Done (2026-08-07)
- **Sibling, does not reopen**: `docs/rfcs/ARCH-entity-interaction-v2.md` (**closed**, ws #843) — that RFC
  owns the canonical *entity* contract (identity, URL/open behavior, drag-payload shape, one
  `TrackRow` capability contract). This RFC does not relitigate any of its settled decisions
  (two album-detail hosts, no `/album/[id]` route, `AddToBucketMenu` as the WCAG 2.5.7 touch
  primary). It builds the *presentational + compositional* layer one level up — the album **card**,
  not the album **entity** — using that RFC's own `TrackRow` capability-contract pattern as the
  direct precedent (see §Alternatives).
- **Sibling, does not overlap steps with**: `docs/rfcs/ARCH-entity-interaction-domain-audit.md`
  (draft, in-progress — cross-domain registry/guardrails for events/state-owners/modals). No shared
  steps; this RFC's migration references two of that audit's guardrails (G2, G5) as prior art for
  "capability injection instead of ad hoc grep-and-hope."
- **Origin**: 2026-08-06 evidence-based audit, at owner request, following `ARCH-entity-interaction-v2`'s
  closure — 7 parallel investigations run directly against `origin/main` (not against either RFC's
  own completion claims) covering 6 hypothesized defects plus a full album-card representation
  inventory. Exact HEADs inspected: `myblog-workspace` `b914194e0cec32f9bb2b795195a46f91740b45c8`,
  `myblog_front` `bcb654405bde477c040a8e60a764212887c2c4f3`, `myblog_backend`
  `9fa9c0f463faa37ff329922104ac2ee7ddc71543`.

---

## 0. Verified-defect summary (full evidence in §19)

| # | Hypothesis | Verdict | One-line evidence |
|---|---|---|---|
| 1 | temp-ID cross-bucket movement race | **CONFIRMED** | `copyAlbum`'s resolve handler looks up its own closure `toBucketId`, not wherever the tile actually moved (`BucketBoard.tsx:2035-2098`) |
| 2 | NowPlaying session update loss | **MIXED — named bug fixed, structurally identical gap survives elsewhere** | `onPlaybackChanged`'s blanket drop is fixed (front #360); the `playbackSession` convergence effect (Step 3b) still drops external updates during any control call with no confirmation read — worst for `setMode` — and the codebase's own test calls this "the accepted tradeoff" (`NowPlaying.tsx:700-743`, `NowPlaying.test.ts:254-303`) |
| 3 | Concurrent queue replacement | **CONFIRMED, self-admitted in code** | `replaceQueueAndPlay()`/`rewriteQueue()` has no mutex/single-flight/generation-token/abort; one call site's own comment states the double-click race is untested and accepted (`session.ts:519-745`, `AlbumOverlay.tsx:108-111`) |
| 4 | Missing touch alternative in MemoWindow | **CONFIRMED** | `MemoWindow`'s `TrackRow` was granted `drag` (front #368) without its required `add` tap-fallback peer — the one call site in the whole app where a drag grant shipped unpaired (`AlbumDetail.tsx:549-560`, cf. `TrackRow.tsx:199-209`) |
| 5 | Ambiguous `OpenAlbumDetail` ID contract | **STRUCTURAL RISK, not currently live** | The namespace-conflating pattern exists in the type (`entityEvents.ts:15-31`) but exactly one of 27 producers uses it, and that one is already correctly guarded (`releaseShared.tsx:218`) — nothing type-enforces the pairing for the *next* producer |
| 6 | Claude Review CI false-green | **CONFIRMED, live today** | `code-review.yml` step-skips (not job-skips) when `ANTHROPIC_API_KEY` is absent, and the key is not configured on `myblog_front` right now — every PR shows green identically whether the review ran or not |

Defects 1/3/4/6 are CONFIRMED and unresolved. Defect 2 is partially fixed with a newly-found residual
gap. Defect 5 is a real but currently-contained risk. None of the four confirmed defects were closed
by `ARCH-entity-interaction-v2`'s closure or by `ARCH-entity-interaction-domain-audit`'s Steps 1-4 —
see §19 for why each is tracked as an independent item rather than folded into this RFC's migration.

---

## 1. Context and concrete current inconsistencies

A single visual concept — "here is an album" — is implemented independently at least **9 times** in
`myblog_front` (inventory, HEAD `bcb6544`):

| Representation (file:line) | Layout | Nav | Play | Add | Drag | Touch alt | Image fallback |
|---|---|---|---|---|---|---|---|
| `NewReleasesCard.CardItem` (`home/NewReleasesCard.tsx:77-107`) | grid tile | `openAlbum()` | — | — | — | n/a | `Cover` (home/ui.tsx) |
| `ForYouReleasesCard.CardItem` (`home/ForYouReleasesCard.tsx:71-102`) | grid tile | `openAlbum()`, conditional on id | — | — | — | n/a | `Cover` |
| `TodayAlbumBuckit.Card` (`home/TodayAlbumBuckit.tsx:56-104`) | grid tile | `openAlbum()` | — | — | — | n/a | `Cover` |
| `TodaySongBuckit` (`home/TodaySongBuckit.tsx`) | single row | `openAlbum()` via button | — | — | — | n/a | `Cover` |
| `BucketBoard.AlbumChip` (`member/BucketBoard.tsx:476-728`) | grid tile, bucket-scoped | `onOpen(DetailTarget)` | — | *is* the add target | full HTML5 DnD, 3 origin kinds | kebab action sheet | `AlbumArt` (member/ui.tsx, delegates to `Cover`) |
| `LikedBoard.LkCover` row (`member/LikedBoard.tsx:276-350`) | table row | `openDetail()` | — | — | — | n/a | `LkCover` (own, 3rd impl) |
| `AlbumDetail.MemoWindow` header (`member/AlbumDetail.tsx:417-556`) | modal header | n/a (already detail) | — | n/a | tracklist only, via shared `TrackRow` | **none — BUG-24** | `AlbumArt` |
| `writer/SubjectHero` (`writer/SubjectHero.tsx`) | editor hero | n/a | — | — | — | n/a | inline hashed-glyph (4th impl) |
| `AlbumOverlay`/`AlbumDetailView.Header` (`album/AlbumOverlay.tsx`) | modal, public | n/a | **▶, the only inline play in the app** | — | tracklist rows | n/a | not inspected |

**Already-unified, worth preserving as precedent**: album/artist navigation (`openAlbum()` /
`artistHref()` via `lib/entityLinks.ts`/`lib/entityEvents.ts`) is called identically from 6+ sites and
is the one piece of this surface area `ARCH-entity-interaction-v2` already fixed correctly. The
inconsistency is entirely in the **markup and capability wiring around** that shared navigation, not
in navigation itself.

**Accidental duplication, not intentional variation**:
- `NewReleasesCard.CardItem`, `ForYouReleasesCard.CardItem`, `TodayAlbumBuckit.Card` are the same
  component hand-copied three times — identical cover-wrap → title → artist-link → date structure,
  only the scoped-CSS prefix (`nrl-`/`fyr-`/`otd-`) differs; the `dateLabel()` formatter is
  byte-identical in two of the three.
- Cover-art fallback exists **4 independent times** with 4 different visual results for the same
  "no image" case: `Cover` (`home/ui.tsx:10-28`, initials span), `AlbumArt` (`member/ui.tsx:20-33`,
  delegates to `Cover` for the no-image branch but has its own `<img>` for the has-image branch),
  `LkCover` (`LikedBoard.tsx:343-350`, a third independent img-or-fallback wrapper), and
  `SubjectHero`'s inline single-glyph hashed-hue background (fourth, no shared function at all).
- `AlbumArt` already imports `Cover` across the `home/`↔`member/` directory boundary — this
  **disproves** any assumption that home-owned and member-owned primitives can't be shared today;
  the boundary is organizational, not technical.

**A real, working precedent already exists one level down**: `shared/TrackRow.tsx`'s
`TrackRowActions = {lyrics?, open?, openLyrics?, play?, add?, drag?}` is a genuine capability-contract
component, consumed today by both `AlbumDetail.MemoWindow` and `LikedBoard` with different capability
subsets granted per surface. This RFC's canonical model is that pattern moved up one level (album),
not invented from scratch.

**The one anti-pattern already live**: `BucketBoard.AlbumChip` bakes bucket-item identity (`itemId`,
`temp:*` handling, move/reorder/remove ownership) directly into the presentational tile rather than
receiving it as an injected capability. It is also the site of BUG-21 (§19) — evidence that domain
state living inside a "shared" visual component is not just an architecture smell, it is where the
one confirmed data-integrity bug in this audit actually lives.

**Positive precedent for the review/editorial boundary**: `ARCH-entity-interaction-v2` Step 5's E7
slice already projects `albumIds`/`artistIds` onto `ReviewCard`/`ReviewHit` (front #362) specifically
so a published review's cover can open an album peek **without pretending the review document is an
album**. `ReviewCard` stays its own type. This RFC formalizes that boundary rather than inventing it.

---

## 2. Problem statement

There is no single answer to "what does an album look like in this product," so every new surface
either hand-copies an existing tile (accidental duplication, 3 already) or bakes surface-specific
state into what should be a dumb presentational component (`AlbumChip`, the one component
implicated in a live data-integrity bug). Every future surface — the planned
`FEAT-album-review-authoring` write entry (C1), any new Home recommendation rail, a future
`/genres`-adjacent album list — faces the same choice with no contract to follow, and the DnD
semantics (copy vs. move vs. reorder, album identity vs. bucket-item identity) are not written down
anywhere a new author would find them.

---

## 3. Goals

- One canonical album display-data shape, consumed by every surface.
- One shared presentational primitive owning layout, typography, cover-fallback (consolidating the
  3 album-surface implementations into 1), loading/skeleton state, and badge slots. `LikedBoard`'s
  `LkCover` stays outside this goal because it renders saved-track rows/cards, not album cards;
  Stage 3 retains it only as a comparative legacy fallback fixture.
- Small, named capability contracts (`open`, `play`, `add`, `drag`) injected per surface — the
  `TrackRowActions` pattern, one level up.
- Thin, surface-owned adapters (Home, Bucket, Memo, editorial) that hold all domain state
  (`itemId`, `temp:*`, reorder, optimistic sync, memo text, editorial document state) and inject
  capabilities into the shared primitive — never the reverse.
- An explicit, written DnD contract distinguishing copy/add, reorder, and move, and album-entity
  identity vs. bucket-item identity, so a new drag source or drop target has something to read before
  inventing its own rule.
- A durable fix path for the one confirmed touch-fallback gap (BUG-24) and a hardening path for the
  one currently-contained ID-namespace risk (§19 defect 5), each as an individually-tracked
  prerequisite/dependency — not silently absorbed into "the RFC is done."

## 4. Non-goals

- **Not reopening `ARCH-entity-interaction-v2`.** Its E1-E7 entity-level decisions (two album-detail
  hosts, no `/album/[id]` route, drag-payload shape, `AddToBucketMenu` as touch primary) are inputs
  to this RFC, not subjects of it.
- **Not a big-bang replacement.** See §15 — surfaces migrate one at a time; legacy components are
  deleted only after parity tests pass (Stage 9).
- **No new branded-id types workspace-wide.** The sibling domain-audit RFC's non-goal stands for the
  *existing* `albumId`/`spotifyAlbumId` convention. This RFC's canonical model introduces exactly two
  named fields (`catalogAlbumId`, `spotifyAlbumId`, §6) for the *new* type it defines — a named-field
  addition, not a branded-type retrofit of 27 existing call sites.
- **Not merging `AlbumOverlay`/`AlbumDetail` (E6).** Independently re-affirmed twice already
  (`ARCH-entity-interaction-v2` 2026-08-04, `ARCH-entity-interaction-domain-audit` 2026-08-05). Out
  of scope again here.
- **Not a `BucketBoard.tsx` monolith split.** Inherited non-goal from `ARCH-entity-interaction-v2`.
  This RFC extracts `AlbumChip`'s *presentational* half onto the canonical primitive; `BucketBoard`
  keeps owning bucket state, move/reorder ops, and the temp-id lifecycle (once BUG-21 is fixed).
- **Not fixing BUG-21/22/23 or the Claude-review CI item as part of this RFC's migration diff.** Each
  is an independently verifiable, independently mergeable item (§19). BUG-21 is a hard prerequisite
  for Stage 6; the others are tracked but not blocking.
- **Not touching `OpenAlbumDetail`'s existing `albumId`/`unresolved` shape.** §6's smart-constructor
  hardening (defect 5) is scoped as its own small chore, referenced here as a dependency, not
  rewritten by this RFC.

---

## 5. Canonical album display model

```ts
// New type — does not replace OpenAlbumDetail, DetailTarget, or BoardAlbum.
// Surface adapters project their own state into this shape; the shared primitive
// never sees anything but this shape plus injected capabilities.
interface AlbumCardDisplayData {
  title: string
  artist: string | null
  artistId: string | null         // for artist-nav capability; null = artist not linkable
  cover: string | null
  year: number | null
  loading?: boolean                // skeleton state — distinct from "loaded with no cover"
}

declare const unresolvedAlbumCardBrand: unique symbol

type AlbumCardData = AlbumCardDisplayData & (
  | { catalogAlbumId: string; spotifyAlbumId: null }
  | { catalogAlbumId: null; spotifyAlbumId: null }
  | {
      catalogAlbumId: null
      spotifyAlbumId: string
      readonly [unresolvedAlbumCardBrand]: true // made only by unresolvedAlbumCardData(...)
    }
)
```

Two always-present, independently-named fields — not one field plus a boolean flag. Stage 8 closed
the remaining construction gap by branding the Spotify-only union member and exposing
`unresolvedAlbumCardData()` as its only type-valid constructor. This is a
direct, deliberate correction of the risk found in `OpenAlbumDetail` (§19 defect 5): a future author
reading this type cannot construct an `AlbumCardData` that puts a Spotify id where a consumer expects
a DB id, because there is no field that means both depending on a third field's value and the foreign
fallback pair cannot be hand-built.

The shared primitive renders purely off this shape (plus §7's injected capabilities) and off nothing
else — no `itemId`, no `temp:` string, no bucket reference, no memo text, no review/editorial status.

---

## 6. Explicit identifier model

- `catalogAlbumId: string | null` — the only field ever passed to a write call (rating, queue-replace,
  bucket add). Null is legal and renders as non-interactive for those capabilities (mirrors the
  existing, sound `null`-is-first-class convention from `ARCH-entity-interaction-v2` E1 Rule 0).
- `spotifyAlbumId: string | null` — populated only as a display/navigation fallback when
  `catalogAlbumId` is null. Never passed to a catalog-DB write call; a capability that needs a DB id
  (rating, add-to-bucket) is simply not injected when `catalogAlbumId` is null, rather than trusting
  every capability implementation to check the right field.
- **Bucket-item identity is not album identity** and is never part of `AlbumCardData`. A bucket
  surface adapter (`BucketAlbumCardAdapter`, §9) holds `itemId: string` (real id or `temp:${...}`)
  separately, keyed alongside the `AlbumCardData` it renders. This is the direct fix for the
  *architectural* half of BUG-21: today `AlbumChip` conflates "which album is this" with "which
  bucket row is this" in one component, which is exactly why `copyAlbum`'s resolve handler had
  nowhere unambiguous to look up "wherever this row is now."
- **Dependency, not scope**: `OpenAlbumDetail`'s existing single-field-plus-flag shape
  (`entityEvents.ts:15-31`) is not migrated to this model by this RFC. Its independent Stage 1
  hardening shipped `openAlbumUnresolved(spotifyAlbumId, display)` so fallback producers cannot split
  the id from the flag. Stage 8 mirrors that invariant inside `AlbumCardData` with
  `unresolvedAlbumCardData()` and migrates its sole current Spotify-only producer; it does not migrate
  the separate `AlbumOverlay`/`AlbumDetailView` host boundary.

---

## 7. Capability interfaces

Modeled directly on `TrackRowActions`, one level up:

```ts
interface AlbumCardCapabilities {
  open?: () => void                    // required for any interactive card; absent = display-only
  play?: () => void                    // absent = no play affordance rendered
  add?: () => void                     // absent = no add-to-bucket affordance rendered
  drag?: DragPayload                   // presence makes the tile draggable; ARCH-entity-interaction-v2's payload type
  artistOpen?: () => void              // separate from `open` — the album tile and the artist name navigate independently
}
```

Rules, carried over from `TrackRow`'s working precedent and from `ARCH-entity-interaction-v2`'s
binding Rule #14:

- **A capability that is not injected renders no affordance at all** — no disabled button, no
  placeholder. This is what already makes `TrackRow` degrade cleanly when a slot is omitted, and is
  the mechanism that must not be skipped again the way it was for `MemoWindow`'s `add` (BUG-24).
- **`drag` must never be the only path to an operation.** Per Rule #14 (binding, measured by CDP:
  native `draggable` fires zero `dragstart` events on touch at any distance), any adapter that
  injects `drag` for an operation (move-to-bucket, reorder) **must** also inject a capability that
  reaches the same operation without drag (typically `add`, opening `AddToBucketMenu`/an action
  sheet). This rule is stated here as an enforceable contract precisely because BUG-24 shows the
  narrative version of this rule (already written in `ARCH-entity-interaction-v2`) was not enough —
  it needs to be a property of the capability type itself, checked at the adapter (§16 test strategy),
  not prose an author has to remember.

---

## 8. Shared visual component responsibilities

`AlbumCard` (new, `components/shared/AlbumCard.tsx`) owns and only owns:

- Layout (grid tile / row — a `layout` prop, not a variant string, selects between the two literal
  DOM shapes that already exist; no third layout is invented speculatively)
- Typography (title, artist, year rendering)
- Cover-art rendering + the single consolidated album fallback (replacing `Cover`/`AlbumArt`/
  `SubjectHero`'s inline glyph with one implementation — `AlbumArt`'s existing delegation to `Cover`
  is the natural merge base since that cross-boundary import already works)
- Loading/skeleton rendering, keyed off `AlbumCardData.loading`
- Rendering exactly the affordances implied by which capabilities are present (§7)
- Named, typed slots for surface-contextual content (`badge?: ReactNode`, `secondaryLine?: ReactNode`)
  — e.g. `TodayAlbumBuckit`'s "N년 전" pill, a future "selection reason" line, a future review-status
  badge — rendered by the primitive but populated only by adapters

`AlbumCard` must not import, reference, or receive as a typed prop: `itemId`, any `temp:`-shaped
string, bucket/board types, `useBucketMemo` or any memo state, review/editorial document types, or
any reorder/move/optimistic-sync function. If a future change needs the primitive to know about one
of these, that is the signal the abstraction has been asked to do an adapter's job — per the user's
explicit constraint, this is a redesign trigger, not a prop to add.

---

## 9. Surface adapter responsibilities

Each adapter maps its own domain state → `AlbumCardData` + `AlbumCardCapabilities`, and owns
everything `AlbumCard` must not:

- **`HomeAlbumCardAdapter`** (`NewReleasesCard`, `ForYouReleasesCard`, `TodayAlbumBuckit`,
  `ReviewCandidates`'s candidate row) — injects `open` (+`artistOpen` where an artist id exists),
  and for catalog-backed albums pairs external copy `drag` with `AddToBucketMenu`. Spotify-only
  data remains display-only with an explicit catalog-registration status. Owns per-surface badge
  population (release-date pill, "N년 전", rating stars).
- **`BucketAlbumCardAdapter`** (`BucketBoard.AlbumChip`'s presentational half) — the one adapter that
  owns `itemId`/`temp:*` lifecycle, injects `open`, `add` (kebab action sheet — already the shipped
  touch path here), and `drag` (paired, per Rule #14, already correctly paired today via the kebab
  fallback). **Gated on BUG-21's fix landing first** (§15 Stage 6, §19).
- **`MemoAlbumCardAdapter`** (`AlbumDetail.MemoWindow`'s header + its `TrackRow` usage) — owns memo
  text state (`useBucketMemo`), injects `open`-equivalent (already n/a, it's the detail view itself)
  for the album header, and for the **tracklist** must inject a paired `add` alongside the existing
  `drag` — this is BUG-24's fix, done at the adapter boundary rather than by hand-patching
  `MemoWindow` in place, so the pairing rule (§7) is structurally enforced going forward.
- **`EditorialAlbumTargetAdapter`** (`writer/SubjectHero`, future review-authoring write entry C1) —
  injects `open` (reopen album search) and a contextual `secondaryLine` slot for
  "BEST NEW MUSIC"/selection reason. **Never** wraps a `ReviewCard` — see §12.

---

## 10. DnD entity and command contracts

Building directly on `ARCH-entity-interaction-v2`'s `DragPayload`/`EntityRef` (E2/E3, unchanged,
not reopened), stated explicitly for album cards because BUG-21 is exactly a case where this
distinction was not tracked cleanly at the call-site level:

| Source → Target | Command | Payload identity | Notes |
|---|---|---|---|
| Home → Bucket | copy/add | album entity identity only (`catalogAlbumId`) | no bucket-item identity exists yet; server creates a new row |
| External album source → Bucket | copy/add | album entity identity only | same as above; "external" is `origin.kind='external'` per `BucketBoard.tsx:592-601` |
| Bucket → same Bucket | reorder | bucket-item identity (`itemId`) | album identity is irrelevant to the command; server reorders existing rows |
| Bucket → another Bucket | move | bucket-item identity (`itemId`) **and** the album identity the row denotes | both are needed: the item moves, and if the item id is still `temp:*` the client must know which album it denotes to correlate with the eventual add-POST response (BUG-21's exact gap) |

A shared visual card never determines which of these four a given drag is — that decision is made by
the **adapter** reading its own source/target `EntityRef`/`origin.kind`, exactly as `BucketBoard.tsx`'s
`routeAlbumDrop`/`boardDnd.ts` already does at the entity level. This RFC does not change that
routing logic (non-goal); it only requires that `BucketAlbumCardAdapter` be the single place that
holds `itemId` alongside `catalogAlbumId`, so a move-in-flight has one, not zero, places to look up
"where did this temp id actually end up" — the structural fix BUG-21's own bug report recommends.

---

## 11. Mouse, keyboard, and touch behavior

- **Mouse**: hover reveals affordances currently hidden by default (matches `FEAT-album-review-authoring`'s
  existing "quietly present" pattern for bucket action buttons — not reinvented here).
- **Keyboard**: `open` is always reachable via Enter/Space on the tile (mirrors `TrackRow`'s existing
  `role="button"` + manual keyboard handling for `openLyrics`, the established pattern for a
  whole-row/whole-tile actionable target).
- **Touch**: every capability that has a `drag`-based path **must** have a non-drag (tap) path, per
  Rule #14 restated as a capability-type property in §7. `AddToBucketMenu`/kebab action-sheet is the
  default primary touch path for add/move, matching the measured, owner-approved default
  (`ARCH-entity-interaction-v2` OQ4, CDP-measured: native `draggable` produces zero `dragstart` on
  touch at any distance). This RFC does not re-measure that finding; it inherits it as settled and
  enforces it structurally for album cards the way BUG-24 shows it was not enforced for `MemoWindow`.

---

## 12. Review/editorial boundary

- **An album selected as the subject of a future review** (the writer's chosen subject before
  publishing, `ReviewCandidates`' "평론 쓰기 →" queue) is still an *album* — it uses `AlbumCard` with
  contextual slots (`secondaryLine` for "선정 사유"/rating hint), via `EditorialAlbumTargetAdapter`.
- **A published review/editorial document about an album** is a *document*, not an album, and
  continues to render via `ReviewCard`/`ReviewHit` (`lib/reviews.ts`), unchanged by this RFC. This
  boundary is not new — `ARCH-entity-interaction-v2` E7 already shipped exactly this separation
  (`ReviewCard` gained a peek-open `albumIds`/`artistIds` projection specifically so it could *reference*
  an album without *becoming* one). This RFC states the boundary explicitly as a standing rule so a
  future author does not fold `ReviewCard` into `AlbumCard` "for consistency" — consistency here means
  citing the same album id shape, not sharing a rendering primitive.

---

## 13. Alternatives considered

- **Extend `TrackRow`'s pattern upward without a new component** — i.e. let `AlbumCard` just be a
  `TrackRow` with different fields. Rejected: an album tile's layout (grid, cover-first) is
  structurally different from a track row's (list, no-cover), and forcing one component to cover both
  shapes is exactly the "growing variant" anti-pattern (§14) one level removed.
- **Fix `AlbumChip` in place, generalize later** — patch BUG-21 inside `BucketBoard.tsx` without
  extracting a shared primitive. Rejected as the sole plan: it would leave the other 8 representations
  duplicated, and (per §1) the duplication itself, not just BUG-21, is the audited problem. Accepted as
  a *sequencing* decision instead — BUG-21 is fixed as its own bug-fix PR before `AlbumChip` migrates
  (§15 Stage 6), so the fix isn't entangled with an unrelated refactor's diff.
- **A single `AlbumCard` with a `context: 'home' | 'bucket' | 'memo' | 'review'` prop** — considered
  and rejected; see §14.

## 14. Rejected inheritance, giant-variant, and God-props designs

- **`HomeAlbumCard extends AlbumCard`** (or any inheritance chain) — rejected. Inheritance couples a
  subclass to a superclass's internals across every future superclass change; the capability-injection
  model (§7-9) gets the same code reuse without that coupling, and is already proven at the `TrackRow`
  level.
- **`variant="home" | "bucket" | "review" | ...`** — rejected. A variant string forces the shared
  primitive to internally branch on domain concerns it is not supposed to know about (§8), which is
  the same shape of problem `NowPlaying.tsx`'s multiple hand-rolled race guards created independently
  in three different files (§19 defect 2) — branchy "shared" components accumulate untested edge paths
  exactly where a typed capability list would have made the missing case (BUG-24's missing `add`) a
  visible gap in a props object instead of an invisible gap in a branch nobody wrote.
- **A growing list of optional callbacks bolted onto one giant props interface** (`onPlay?`, `onAdd?`,
  `onDrag?`, `onRemove?`, `onReorder?`, `onMove?`, ... each surface adding its own) — rejected in favor
  of the small, named `AlbumCardCapabilities` object (§7), which is closed over what a *card* can do,
  not open-ended to what any *surface* might eventually want to do to it. Move/reorder/remove stay
  adapter-owned operations that call `add`/`drag`'s injected functions, never new fields on the
  capability type.
- **Overloads that conceal incompatible domain contracts** (e.g. one `albumId: string` field silently
  meaning "DB id" in some call paths and "Spotify id, degrade the UI" in others, gated by an unrelated
  boolean) — rejected; this is precisely defect 5's risk shape (§19), and §6's two-named-field model
  is the direct alternative.

---

## 15. Migration stages

Corrected against the requested default ordering using this audit's evidence — reordered where a
stage's actual current-code cost or risk differs from the generic assumption.

**Stage 1 — identifier hardening (SHIPPED 2026-08-06, front #372, `14ccaef`)**
Scope: ship the `openAlbumUnresolved()` smart constructor for `OpenAlbumDetail` (§6, §19 defect 5).
Tests: unit test proving the constructor cannot be called without both fields agreeing.
Compat: no consumer change required (existing call sites keep working; only the one fallback
producer, `releaseShared.tsx`, migrates to the constructor).
Rollback: trivial revert, zero downstream coupling since nothing depends on it yet.
Result: `openAlbumUnresolved(spotifyAlbumId, display)` now owns both `albumId` and
`unresolved: true`; `releaseShared.tsx` is the only migrated producer. Verification: lint pass,
Astro check 0 errors, Vitest 48 files / 507 tests, deploy run `31074197178` success, prod smoke
19/19. No API, contract, infrastructure, database, or rendered-UI change.

**Stage 2 — canonical card model + capability contracts (SHIPPED 2026-08-06, front #373, `386539f`)**
Scope: land `AlbumCardData`/`AlbumCardCapabilities` (§5, §7) as types + a no-op `AlbumCard` shim that
is not yet wired into any surface.
Tests: type-only; a snapshot test asserting the shim renders nothing observable when unused.
Compat: zero — nothing consumes it yet.
Rollback: delete the new files, no blast radius.
Result: `components/shared/AlbumCard.tsx` now owns the canonical display model and capability contract.
The capability type makes Rule #14 structural: a `drag` grant does not typecheck without the paired
`add` tap/action-sheet path. The exported component intentionally returns `null`; a source sweep
confirmed that no live surface imports it. Verification: lint pass, Astro check 0 errors, Vitest 49
files / 509 tests (2 new), deploy run `31075214832` success, prod smoke 19/19. No rendered UI, API,
contract, infrastructure, or database change.

**Stage 3 — extract the shared presentational primitive (SHIPPED 2026-08-06, front #377, `c32949a`)**
Scope: implement `AlbumCard`'s real rendering (§8), establishing the single target for the 3
album-surface fallback implementations (built on `AlbumArt`'s existing delegation to `Cover`, since that cross-boundary
import already works today — no new dependency direction needed).
Tests: freeze each of the 4 existing fallback renderers' actual DOM/style signature, then test the
canonical renderer's deliberate normalization separately (has-image / no-image / broken-image-url
cases). Exact cross-renderer parity was an invalid premise: the legacy renderers already disagree.
Compat: still not wired into any live surface — pure addition.
Rollback: delete; no live surface depends on it yet.
Result: `AlbumCard` now renders grid/row layouts, cover/fallback/loading states, title/artist/year,
badge and secondary slots, and capability-gated `open`/`play`/`add`/`artistOpen`/`drag` behavior.
Artist navigation remains a canonical anchor (modified clicks retain browser behavior), and drag
dispatches both existing Pocket bridge pairs with origin-correct `effectAllowed`. The component
imports no bucket/memo/editorial state, and a source sweep confirms zero live consumers.

The legacy tests preserve the real differences rather than inventing equivalence: Home `Cover`
omits `decoding`, `AlbumArt`/`LkCover` use `loading="lazy" decoding="async"`, `SubjectHero` uses an
eager image; three no-image fallbacks show `KI`, while `SubjectHero` shows `K`. Broken URLs remain
in the image branch on every legacy renderer. The canonical component deliberately normalizes to
the two-letter `Cover` fallback and lazy/async images. Verification: lint pass, Astro check 0 errors
and 0 warnings (2 existing hints), Vitest 49 files / 539 tests (24 AlbumCard cases), production
build 21 pages + PWA, project reviewer pass, deploy run `31079317610` success, and prod smoke 19/19.
No live rendered surface, API, contract, infrastructure, or database behavior changed.

**Stage 4 — migrate one low-risk Home surface (SHIPPED 2026-08-06, front #379, `e1268a7`)**
Scope: `NewReleasesCard` — chosen over `ForYouReleasesCard`/`TodayAlbumBuckit` as the simplest: no
optional-id degrade branch (unlike `ForYouReleasesCard`), no unused-but-defined `spotify_album_id`
field to reconcile (unlike `TodayAlbumBuckit`). Public, read-only, `open`-only capability.
Tests: interaction test (click → `openAlbum()` called with correct id), visual parity against the
pre-migration markup.
Compat: `NewReleasesCard`'s old `CardItem` stays in the file, dead-code-eligible, until Stage 9.
Rollback: swap the import back; no shared state touched.
Result: `NewReleaseAlbumCardAdapter` is the first live consumer of the canonical `AlbumCard`. It
projects the feed item into `AlbumCardData`, grants only album-open and artist-open navigation, and
keeps release-date copy, the reviewed-artist badge, intent prefetch, and the overlay display payload
at the Home boundary. The old renderer remains as `LegacyCardItem` for the Stage 9 parity gate.

Verification: lint passed; Astro check reported 0 errors and 0 warnings (2 existing hints); Vitest
passed 49 files / 544 tests; the production build generated 21 pages plus the PWA. A local
read-only fixture drove the real browser: at 1280×720 the 150px card opened the expected album
overlay, and at 390×844 the 128px card retained its title, artist, release date, and badge with no
card or section overflow. Deploy run `31082278000` passed through S3 upload, CloudFront invalidation,
and built-in health smoke; the independent production regression smoke passed 19/19. No API,
contract, infrastructure, database, auth, or other Home-surface behavior changed.

**Stage 5 — migrate the remaining Home surfaces (SHIPPED 2026-08-06, front #380, `cb3a734`)**
Scope: `ForYouReleasesCard` (wire the optional-id degrade as "no `open` capability injected" rather
than a conditional `<span>`), `TodayAlbumBuckit` (badge slot for "N년 전"), `ReviewCandidates`'
candidate row (badge slot for rating stars + the "평론 쓰기 →" link as a `secondaryLine`).
Tests: one interaction + one parity test per surface, per the Stage 4 pattern.
Compat: same as Stage 4, per surface.
Rollback: per-surface, independent of the others.
Result: `ForYouReleaseAlbumCardAdapter`, `TodayAlbumCardAdapter`, and
`ReviewCandidateAlbumCardAdapter` now project their surface data and capabilities onto the canonical
card. A For You item without a catalog id remains display-only and carries only its Spotify fallback
id; Today Album keeps its anniversary badge; Review Candidates keeps its rating stars, comment, and
editor link in the row slots. By owner decision, `TodaySongBuckit` remains bespoke because its
single-pick curation controls do not fit the shared capability set. All three legacy renderers remain
as Stage 9 parity fixtures.

Verification: lint passed; Astro check reported 0 errors and 0 warnings (2 existing hints); Vitest
passed 50 files / 551 tests. Real-browser checks passed on desktop and at 390×844: all three album
open paths worked, the review-editor link navigated correctly, the row card retained its 56px cover,
and no horizontal overflow appeared. Deploy run `31084951887` passed, including the built-in health
smoke; the independent production regression smoke passed 19/19.

**Stage 6 — migrate Bucket via `BucketAlbumCardAdapter` (SHIPPED 2026-08-06, front #381, `5803776`)**
Scope: extract `AlbumChip`'s presentational half onto `AlbumCard`; `BucketBoard.tsx` keeps 100% of
`itemId`/`temp:*`/move/reorder/copy ownership, now expressed as capability injection instead of
inline JSX branching.
**Hard prerequisite**: BUG-21 must be fixed and its regression test (§19, fork-proposed delayed-promise
test) merged *before* this stage starts — migrating the presentational half while the promotion bug
is still live would mean the new adapter inherits and potentially obscures the same bug behind a
refactored surface.
Tests: the existing `BucketBoard.tsx` has zero component-level tests today (confirmed by this audit) —
this stage is also where a `BucketBoard.test.tsx` (render + interaction, not just `boardDnd.test.ts`'s
mocked-ops decision tables) is added, for both the adapter and to carry BUG-21's regression test
forward once fixed.
Compat: `AlbumChip`'s external props (as consumed by `BucketBoard.tsx`'s render loop) stay the same
shape; only its internals change.
Rollback: revert the adapter extraction; `BucketBoard.tsx`'s state ownership is untouched either way.
Result: live `item_type === 'album'` memberships now render through the bucket-owned
`BucketAlbumCardAdapter` and canonical `AlbumCard`. The adapter closes over `itemId`, bucket id,
writable memo detail, temporary-id/move/reorder/copy operations, badges, research/mark state, and the
existing `ActionSheet`; none enters the shared component. `AlbumCardAction` gained a domain-neutral
descriptor form so Bucket can preserve its established `⋯` / "앨범 동작" control without teaching the
primitive about buckets. Non-album memberships deliberately stay on the generalized legacy renderer,
which is also exported as the Stage 9 parity fixture. BUG-21's delayed-promise regression remains live
and green, with new tests pinning adapter projection, exact drag payloads, null-id inertness, legacy
parity, and the non-album fallback.

Verification: lint passed; Astro check reported 0 errors and 2 existing hints; Vitest passed 50 files /
557 tests; the production build generated 21 pages plus the PWA. A local real-browser pass verified
desktop and 390px card layouts, whole-card album-detail open, and the 390px action sheet with its
mark/play/move/trash verbs. The full-card open hit-area is now a native drag source whenever drag is
granted, and the component test starts drag from that real hit target to prove both DnD bridge pairs
fire. Exact CDP touch emulation was unavailable in this session: the in-app browser exposed no CDP
capability and the active Chrome profile had no control extension; the unchanged coarse-pointer CSS
class and action callback remain covered by regression tests. Deploy run `31089538369` passed through
S3 upload, CloudFront invalidation, and built-in health smoke; the independent production regression
smoke passed 19/19. No API, contract, infrastructure, database, auth, or Spotify-call behavior changed.

**Stage 7 — migrate Memo and verify touch alternatives (SHIPPED 2026-08-06, front #382, `775f683`)**
Scope: `MemoAlbumCardAdapter` for `MemoWindow`'s header; for the tracklist, add the paired `add`
capability to `MemoWindow`'s `TrackRow` usage alongside the existing `drag` (the structural fix for
BUG-24, done here rather than as an isolated patch, so §7's pairing rule governs it going forward).
Tests: `AlbumDetail.dragTrack.test.tsx`-style unit test for the new `add` wiring, **plus a real CDP
390px touch check** confirming a tap on the new affordance opens `AddToBucketMenu` from within
`MemoWindow` — the exact verification step `ARCH-entity-interaction-v2`'s own Step 5 bar required
(mobile 390 pass) but the ninth slice's own "Verified" section did not include for this surface.
Compat: `MemoWindow`'s header markup changes; its memo-text state (`useBucketMemo`) is untouched.
Rollback: revert the adapter; `TrackRow`'s `add` slot already exists and is safe to leave granted
elsewhere even if this specific wiring is reverted.
Result: `MemoAlbumCardAdapter` now projects the memo's album identity and contextual metadata onto
the canonical card while the host retains memo state, track actions, and lyrics ownership. The
adapter's track-action return type requires `add` and `drag` together, closing BUG-24 at the boundary
instead of relying on another call-site convention. `TrackRow` keeps whole-row lyrics only when it
is the sole control; when `add` is present, lyrics becomes an identity-cell native button beside the
add button, so interactive elements never nest. The shared card gained an optional display-only
`eyebrow` slot to preserve the established cover → kicker → title order.

The browser review also exposed a pre-existing nested-overlay gap: `AddToBucketMenu`'s portal was not
registered above its host dismissable. It now joins the shared dismissable stack, autofocuses and
traps focus inside the picker, closes before the memo on Escape, and restores focus to the track add
button. Scroll locking remains owned by `ARCH-overlay-modal-isolation`; this stage did not widen into
that RFC's 16-overlay adoption sweep.

Verification: lint passed; Astro check reported 0 errors and 2 existing hints; Vitest passed 51 files /
561 tests; the production build generated 21 pages plus the PWA. A real in-app browser pass at
390×844 measured zero horizontal overflow and zero nested interactive elements, preserved the
cover/eyebrow/title order, and confirmed that each draggable track exposes `add`. Tapping `So What`
opened only the bucket picker, not lyrics. Real keyboard presses confirmed autofocus, Tab wrap,
top-layer Escape, and trigger-focus restoration. The browser surface did not expose raw CDP touch
dispatch, so the exact-CDP limitation remains recorded rather than overstated; the requested real
390px touch/click path itself passed. Deploy run `31097251431` passed through S3 upload, CloudFront
invalidation, and built-in health smoke; the independent production regression smoke passed 19/19.
No API, contract, infrastructure, database, auth, or Spotify-call behavior changed.

**Stage 8 — integrate editorial/review album targets (SHIPPED 2026-08-07, front #383, `1788bf1`)**
Scope: `EditorialAlbumTargetAdapter` for `writer/SubjectHero`; migrate its bespoke single-glyph
fallback and layout onto `AlbumCard` with a `secondaryLine` slot for BEST NEW MUSIC/selection reason.
Explicitly reaffirm (§12): `ReviewCard` is not touched and does not migrate onto `AlbumCard` — this
stage's own tests must include a negative assertion that `ReviewCard`'s rendering path is unchanged.
Tests: interaction test for `SubjectHero`'s "작품 변경" reopen flow; explicit `ReviewCard`-unchanged
regression test.
Compat: `SubjectHero`'s rating-input/BEST NEW MUSIC toggle are editorial-only state, untouched, passed
through as adapter-owned controls alongside the card.
Rollback: revert the adapter; `SubjectHero`'s editorial state is independent of the card's markup.

Result: live writer album subjects now compose `AlbumCard` through
`EditorialAlbumTargetAdapter`; rating, BEST NEW MUSIC, reopen, and the writer glow/layout remain
writer-owned. Empty and artist subjects stay on the bespoke path. `ReviewCard` remains on its
published-document renderer and has a negative regression test proving that no canonical card is
introduced there. OQ2 was resolved with a branded `unresolvedAlbumCardData()` construction path;
the sole current Spotify-only `AlbumCardData` producer in `ForYouReleasesCard` now uses it, while
`AlbumOverlay` and `AlbumDetailView` remain explicitly outside this stage.

Verification: lint passed; Astro check reported 0 errors and 2 existing hints; Vitest passed 52 files /
567 tests; the production build generated 21 pages plus the PWA. Desktop and 390px real-browser
checks confirmed canonical writer rendering, BEST NEW MUSIC toggle, reopen-dialog focus restoration,
keyboard rating input, zero horizontal overflow, and zero nested interactive elements. Deploy run
`31136547054` passed S3 upload, CloudFront invalidation, and built-in health smoke; the independent
production regression smoke passed 19/19.

**Stage 9 — remove duplicated legacy cards (SHIPPED 2026-08-07, front #384, `2799542`)**
Scope: delete `NewReleasesCard.CardItem`/`ForYouReleasesCard.CardItem`/`TodayAlbumBuckit.Card`'s old
bespoke markup, `SubjectHero`'s inline fallback glyph, and the
now-unused paths through `Cover`/`AlbumArt` that only the legacy components used.
Tests: full parity-test suite (from Stages 4-8) must be green with zero regressions before any
deletion. The original no-new-behavior premise was superseded by the owner's Stage 9 parity gate:
Home had lost desktop drag during migration, so closing the RFC required restoring it and its
mandatory touch alternative before deleting the fixtures.
Compat: none needed — by construction, nothing outside the deleted files references the old markup.
Rollback: `git revert` front #384 as one unit; the removal and Home parity repair share a commit so
the old fixtures and old Pocket handoff cannot be restored independently by accident.

Result: `LegacyCardItem`, `LegacyForYouReleaseCard`, `LegacyTodayAlbumCard`,
`LegacyReviewCandidateCard`, `LegacyAlbumChip`, `LegacyMemoAlbumHeader`, and `LegacySubjectHero`
were deleted together with their private Home/Memo/writer styles, the Bucket `canonical` switch,
and legacy-comparison tests. The surviving generalized Bucket tile is now explicitly non-album.
`Cover` and `AlbumArt` were not deleted wholesale: a fresh import graph found legitimate non-card
consumers, so only legacy-only paths and styles were removed. Source, runtime lazy-import, and built
bundle scans found no remaining deleted symbol or selector reference.

Functional parity fix: `HomeAlbumCardAdapter` now composes every applicable New Releases, For You,
Today, and Review Candidate card. A non-null `catalogAlbumId` grants both an external
`{kind:'external', copies:true}` copy drag and the existing `AddToBucketMenu` action. Home does not
mount `BucketBoard`, so Pocket now completes this one external album copy directly: General routes
to `addBucketItem`, Artist to `expandSourceArtists`, and Playback to `expandAlbumTracks`; the
sync-owned Spotify library target remains rejected by the existing manual-add policy. Spotify-only
For You releases stay display-only and show “catalog registration required”; `spotifyAlbumId`
remains display/navigation fallback data and is never converted into a catalog write id. Album
opening, artist anchors, unresolved handling, badges/secondary lines, ratings/comments, editor
entry, Memo, Bucket, and writer presentation remain surface-owned and unchanged.

Verification: lint passed; Astro check reported 0 errors and 2 existing hints; Vitest passed 53
files / 565 tests; the production build generated 21 pages plus the PWA. Browser checks covered
Home, Bucket, Memo, Review Candidate, writer, and published critique surfaces. At 390×844,
`AddToBucketMenu` added the same catalog album to Pocket with
`{album_id: 0912b807-be97-4227-ab55-c829347fa71a, item_type: album}`. The selected in-app browser
could not emit a trusted HTML5 native drag gesture; this is not overstated. Instead, the live DOM
confirmed `draggable=true`, adapter tests captured the exact copy payload/effect, and routing tests
proved General/Artist/Playback writes plus Spotify-library rejection. After deploy, a cache-busted
real prod Home loaded `EditorialHome.rhuzOFnH.js`; all 15 catalog cards exposed drag, add, and open,
with zero console errors. Deploy run `31140363308` passed, including health smoke; the independent
production regression smoke passed 19/19.

---

## 16. Test strategy

- **Capability-contract unit tests** per slot (open/play/add/drag present vs. absent → correct
  affordance rendered vs. not), mirroring `TrackRow.test.tsx`'s existing 9-case pattern.
- **One render+interaction test per migrated surface adapter**, following the precedent set by the
  domain-audit RFC's Step 4 `useDismissable` sweep (a real interaction test per migrated component,
  not just a decision-table unit test) — that sweep's own real-browser CDP check caught a live bug
  (`gm-shared`'s `Peek`) that its unit test alone missed; this RFC's Stage 6/7 CDP checks exist for
  the same reason.
- **BUG-21's regression test** (delayed/controlled `addBucketItem()` promise; §19) ships as part of
  BUG-21's own independent fix PR, not authored by this RFC's stages — Stage 6 only re-asserts it
  still passes once `BucketAlbumCardAdapter` is layered on top.
- **CDP 390px touch matrix** for every surface gaining a `drag` capability (Stage 6, mandatory for
  Stage 7) — the verification bar `ARCH-entity-interaction-v2` itself established but the ninth slice
  skipped for `MemoWindow`; this RFC does not repeat that omission.
- **Frozen legacy DOM/style signatures plus per-surface migration parity tests**: Stage 3 records
  what each legacy fallback actually emits and the canonical normalization separately; Stages 4-8
  must prove each migrated live surface preserves its intended visual/interaction result before the
  legacy component is deleted (Stage 9's gate).

## 17. Rollback strategy

Stages 4-8 each left the pre-existing bespoke component unused but present so an individual stage
could be rolled back by swapping one import. Stage 9 has now removed those fixtures; rolling back
Stage 3 or any migrated surface past that boundary requires restoring the deleted paths from git
history. Revert front #384 as a unit if Stage 9 itself must roll back, because the Home drag/add
repair and Pocket completion path are part of its functional-parity gate.

## 18. Acceptance criteria

- `AlbumCardData`/`AlbumCardCapabilities` types exist and typecheck; `AlbumCard` imports none of the
  forbidden domain types listed in §8.
- All four applicable Home/Home-adjacent adapters (New Releases, For You, Today, Review Candidate)
  preserve presentation/open navigation and pair catalog-backed drag with `AddToBucketMenu`.
- `BucketAlbumCardAdapter` (Stage 6) does not ship until BUG-21's fix + regression test are merged;
  the regression test still passes with the adapter layered on top.
- `MemoAlbumCardAdapter` (Stage 7) ships with a working tap alternative for every drag-gated action,
  confirmed by unit coverage and a real 390px browser interaction check. Raw CDP touch dispatch was
  unavailable in the selected browser and is explicitly recorded rather than claimed.
- `ReviewCard`'s rendering path is provably unchanged after Stage 8 (explicit negative test).
- `docs/frontend/component-map.md` gains a canonical album-card registry entry once Stage 3 ships
  (component + capability contract + consumer list) — not written speculatively now, before the
  primitive exists (per the owner's instruction to update that doc only after verifying real
  ownership).
- Legacy per-surface card markup (Stage 9) is deleted only after every prior stage's parity tests are
  green.
- Stage 9 leaves zero source, lazy-runtime, or built-bundle reference to a deleted legacy renderer;
  Spotify-only data remains outside catalog writes and displays the existing unresolved policy.

---

## 19. Dependencies on unresolved defects (full evidence)

Each item below is independently verifiable and independently mergeable — none is a step of this
RFC's own migration; each is referenced here only where it gates or elevates risk in a specific stage.

### BUG-21 — temp-ID cross-bucket movement race (hard prerequisite for Stage 6)

**CONFIRMED.** `BucketBoard.tsx:2035-2098`'s `copyAlbum(albumId, toBucketId)` splices an optimistic
tile (`tempId = temp:${Date.now()}:${albumId}`) into `toBucketId`, fires
`api.addBucketItem(toBucketId, albumId)`, and on resolve looks up `toBucketId` — its own closure
variable, captured at call time — to find and promote the temp tile. `insertAlbum`
(`BucketBoard.tsx:2101-2144`) correctly moves the tile (by `itemId`, which may be `temp:`-prefixed)
between buckets in the tree and correctly skips `api.reorderItems` while any `temp:`-prefixed id is
present. But if a user moves the still-pending tile from A to B before the POST resolves,
`copyAlbum`'s resolve handler still looks in **A** (not wherever the tile now lives), finds nothing,
and returns — the temp id is never promoted. The server's real row lands in A (that's what the POST
targeted); the tile is stuck at `temp:*` in B until a full `refresh()` snaps it back to A. Additionally,
the stuck temp tile permanently satisfies `insertAlbum`'s reorder-skip guard, so bucket B's reorders
silently stop persisting as long as the ghost tile sits there. Not covered by BUG-20's two fixes
(`trashAlbum`'s temp-id guard, `insertAlbum`'s reorder-skip) — both predate and survive this gap.
Zero test coverage exists for `BucketBoard.tsx` at all (`boardDnd.test.ts` mocks `copyAlbum`/
`insertAlbum` as `vi.fn()` and never exercises the real closures).

**Proposed regression test**: mount the real `BucketBoard` ops (not mocked), stub `addBucketItem`
with a manually-controlled deferred promise, call `copyAlbum(albumId, 'A')`, then `insertAlbum(tempId,
'A', 'B', null)` before resolving, then resolve — assert the tile in B is promoted to the real id (not
stuck at `tempId`), and that no orphan row is left in A.

**RESOLVED 2026-08-06** (front #369, standalone bugfix, deployed + prod-verified). Added
`findBucketByItemId` (searches the whole tree by `itemId`) and used it in place of
`findBucket(t, toBucketId)` in `copyAlbum`'s resolve handler, so promotion always finds the tile
wherever it currently lives, not just in the closure's original destination. `BucketBoard.test.tsx`
(new, 0 prior coverage) pins exactly the scenario above via the real action-sheet UI + a manually
deferred `addBucketItem` — confirmed to fail without the fix and pass with it. Known, intentionally
out-of-scope residual: the server-side row still lands under the original `toBucketId` (A) even when
the tile visually moved to B before the add resolved; this fix reconciles the client tree only. That
row self-heals the next time A's order is persisted via a reorder. Full server-side relocation was
judged out of scope for a standalone bugfix — Stage 6's hard prerequisite is satisfied either way,
since Stage 6 only needed the promotion race itself fixed.

### BUG-22 — `playbackSession` convergence effect drops updates during no-confirmation control calls (not a card-architecture dependency; tracked separately)

**Partially confirmed** — the originally-hypothesized bug (`onPlaybackChanged`'s blanket
`controlBusyRef` drop) is fixed (front #360, `localWriteSeq`-style sequence gating,
`NowPlaying.tsx:639-662`). A structurally identical, currently-shipped gap survives in the separate
`playbackSession` convergence effect (Step 3b, `NowPlaying.tsx:704-743`): it gates on
`controlBusyRef.current` directly, with no sequence check and no deferred replay. The code comment
justifying this (`:700-702`) claims the card's own confirmation read supersedes the drop "a moment
later" — true for `playPause`/`seek`/`skip`, false for `setMode` (`:525-560`), which never dispatches
`MYBLOG_PLAYBACK_CHANGED` and has no confirmation read at all. `NowPlaying.test.ts:254-303` proves
this is not incidental: it deliberately asserts the deferred update stays stale with the inline
comment "the accepted tradeoff." **No dependency edge into this RFC** — it is a playback-state bug
unrelated to any album-card surface; listed here only so it does not disappear behind either RFC's
"done" framing. Recommended fix: correct the safety-claim comment to name the `setMode` exception, and
either extend `localWriteSeq`-style gating to this effect or accept and document the narrower risk.

### BUG-23 — `replaceQueueAndPlay()` has no concurrency protection — **CLOSED 2026-08-06** (front #371, `b979992`)

**CONFIRMED, self-admitted in code.** `session.ts:692-745`'s `replaceQueueAndPlay()` has no mutex,
single-flight dedup, generation token, or `AbortController`. `rewriteQueue` (`:519-537`) snapshots a
`beforeIds` set, awaits the network round-trip, then diffs against that now-stale snapshot — two
overlapping calls can each delete rows the other already removed (silently counted as `failed`) and
both append, degrading "▶ replaces the queue" to "▶s append to each other's leftovers." `state.busy`
is read as a UI `disabled` guard only on `PlaybackPanel.tsx`'s transport buttons, never on any of the
5 actual queue-replace call sites. One call site's own comment (`AlbumOverlay.tsx:108-111`) states
outright that the double-click race is untested and has "carried that exact risk with no reported
issue" — a known, accepted, untested race. Today only `AlbumOverlay` exposes an inline `play`
capability (§1 inventory); **this RFC's capability model (§7) makes `play` easy to grant to more
surfaces**, which would multiply this race's exposure.

**Erratum on this section's own original recommendation.** This section originally recommended a
generation-token check on `replaceQueueAndPlay`'s final `authoritativePatch` (the BUG-22 pattern) as
the fix. That was implemented first and proven **insufficient** by a delayed-promise regression test:
the generation guard correctly drops the stale call's own final write, but `rewriteQueue`'s
`beforeIds` corruption happens upstream of that write, in the snapshot itself — two overlapping calls
both computed `added` against the SAME pre-press tree, so the second (generation-current) call's own
`playFrom(0)` still named the FIRST press's track, because the queue itself, not just who gets to
report on it, was already wrong. Shipped fix instead serializes `replaceQueueAndPlay()` onto a shared
promise chain, so a new press's `beforeIds` snapshot is only ever taken after the prior press has
fully settled (write, play, and its deletes) — closing the race at its actual source. Kept here as a
recorded lesson for the next "soft dependency, fix later" bug in this RFC: verify a proposed minimal
fix against a reproduction before treating the write-up's own recommendation as sufficient.

### BUG-24 — MemoWindow `TrackRow` drag grant shipped without paired touch alternative (RESOLVED by Stage 7)

**CONFIRMED.** See §1/§15 Stage 7. `AlbumDetail.tsx:549-560` grants `drag` to `MemoWindow`'s `TrackRow`
usage (front #368, the RFC's own "ninth slice") without `add` — the one place in the app where a drag
grant shipped unpaired, violating `ARCH-entity-interaction-v2`'s own binding Rule #14. An erratum is
recorded directly in that RFC (see below); the fix itself is this RFC's Stage 7 deliverable, not a
separately-tracked bug, since fixing it in place (rather than via the new adapter) would just
reproduce the same un-enforced-pairing risk for the next surface.

**Resolved 2026-08-06** in front #382 (`775f683`, deploy `31097251431`, prod smoke 19/19):
`MemoAlbumCardAdapter` constructs a paired track-action set whose type requires both `add` and `drag`;
the tap path opens `AddToBucketMenu` inside `MemoWindow`, and the real 390px browser check passed.

**Erratum recorded in `ARCH-entity-interaction-v2.md`** (decisions log, dated 2026-08-06): the Step 5
header's claim that "E4's original `play`/`add`/`drag` slot set is now granted somewhere sensible
across all three TrackRow surface groups" is accurate at the surface-group level but not at the
per-slot-pairing level for the `AlbumDetail modals` group specifically — `StandardModal` has `add`+
`drag` paired; `MemoWindow` has `drag` alone. `component-map.md`'s own "Ownership by domain" table
(`:244`, `openLyrics?+drag`) already recorded this correctly; only the Step 5 header's aggregate
framing overclaimed.

### Defect 5 — `OpenAlbumDetail` ID-namespace risk (soft prerequisite for §6, Stage 1)

**STRUCTURAL RISK, not currently live.** `entityEvents.ts:15-31`'s `OpenAlbumDetail.albumId: string`
+ `unresolved?: boolean` can hold a Spotify id in a DB-id-shaped field, but of 27 producers found, only
`releaseShared.tsx:218` ever does — and it already sets `unresolved` correctly (fixed front #358). The
one consumer (`AlbumOverlay.tsx:153-168`) correctly gates `interactive`/`onPlayTrack` on the flag.
Nothing type-enforces the pairing for a *future* producer, though. Recommended (§15 Stage 1, own
chore, not this RFC's diff): an `openAlbumUnresolved()` smart constructor that always sets both fields
together, closing the adoption gap without a branded-type retrofit.

### Defect 6 — Claude Review CI false-green (unrelated; no dependency edge)

**CONFIRMED, live today.** `myblog_front/.github/workflows/code-review.yml`'s `keycheck` step sets
`has_key=false` and both real-review steps step-skip (not job-skip) when `ANTHROPIC_API_KEY` is
absent — and it is absent today (`gh secret list --repo hyuntohoon/myblog_front` shows no such
secret). A step-level skip does not produce a job-level "Skipped" conclusion in GitHub Actions; the
Checks tab shows identical green whether the review ran or never ran. Deliberate since day one
(`6b8551b`, chosen to avoid blocking PRs on a missing secret) — not a regression. Recommended: split
into a `keycheck` job + a `code-review` job gated by a **job-level** `if:`, so a missing key produces
a visibly grey "Skipped" check instead of green "Success." **No dependency edge into this RFC** —
pure CI-infra hygiene, included in this audit's scope only because the owner's task explicitly asked
for it; tracked as its own CHORE item in `plan.md`.

---

## 20. Affected files and components (final state based on `myblog_front` @ `2799542`)

- `src/components/shared/AlbumCard.tsx` — **new**, the canonical primitive (Stage 3)
- `src/components/shared/TrackRow.tsx` — unchanged, the direct precedent this RFC follows
- `src/lib/entityLinks.ts`, `src/lib/entityEvents.ts` — unchanged by this RFC; `entityEvents.ts:15-31`
  (`OpenAlbumDetail`) is the target of the independent Stage-1 hardening chore only
- `src/components/home/NewReleasesCard.tsx` (Stage 4), `ForYouReleasesCard.tsx`, `TodayAlbumBuckit.tsx`
  (Stage 5), `home/ui.tsx` (`Cover`, consolidation target for Stage 3)
- `src/components/home/HomeAlbumCardAdapter.tsx` (Stage 9) — shared Home catalog add/drag pairing;
  Spotify-only status boundary
- `src/components/member/ReviewCandidates.tsx` (Stage 5)
- `src/components/member/BucketBoard.tsx` (`AlbumChip` extraction, Stage 6; also BUG-21's fix site),
  `member/ui.tsx` (`AlbumArt`, consolidation base for Stage 3)
- `src/components/member/AlbumDetail.tsx` (`MemoWindow`, Stage 7 — also BUG-24's fix site;
  `StandardModal` unchanged, already correctly paired)
- `src/components/member/LikedBoard.tsx` (`LkCover`, Stage 3 comparative fixture only; unchanged
  because it renders saved-track rows/cards rather than an album-card surface)
- `src/components/writer/SubjectHero.tsx` (Stage 8)
- `src/components/member/pocket/PocketBuckitProvider.tsx`, `PocketTray.tsx`,
  `src/lib/pocketBuckit/externalAlbumDrop.ts` (Stage 9) — direct external album-copy completion for
  Home, which has no `BucketBoard` island
- `src/components/album/AlbumOverlay.tsx`, `album/AlbumDetailView.tsx` — read only by this RFC;
  `AlbumOverlay`'s `play` capability and its `replaceQueueAndPlay()` dependency are BUG-23's context,
  not migrated by this RFC
- `src/lib/reviews.ts` (`ReviewCard`) — explicitly unchanged, negative-tested in Stage 8
- `docs/frontend/component-map.md` — canonical registry entry added in Stage 3
- Not touched by this RFC, but named as dependencies: `src/lib/playback/session.ts` (BUG-23),
  `member/NowPlaying.tsx` (BUG-22), `.github/workflows/code-review.yml` (defect 6)

---

## Open questions

1. **Resolved 2026-08-06 — keep `TodaySongBuckit` bespoke.** Its single-pick, owner-only curation
   controls are unlike the shared card capability set; Stage 5 therefore migrated only the three
   album-oriented surfaces named in its scope.
2. **Resolved 2026-08-07 — require a smart constructor for Spotify-only `AlbumCardData`.**
   `unresolvedAlbumCardData()` is the only type-valid way to pair `catalogAlbumId: null` with a
   Spotify fallback. Stage 8 migrated the sole current direct fallback producer in
   `ForYouReleasesCard`; `AlbumOverlay`/`AlbumDetailView` were not migrated because their separate
   detail-host boundary is outside the editorial target scope.

## Decisions log

| Date | Decision | Step |
|------|----------|------|
| 2026-08-07 | Stage 9 shipped (front #384, `2799542`; deploy `31140363308`; prod smoke 19/19), closing all nine implementation stages. Deleted seven legacy Home/Bucket/Memo/writer card renderers, private styles, the Bucket compatibility switch, and comparison fixtures; source/lazy/bundle scans found zero runtime references. The Stage 9 parity gate also repaired Home: catalog-backed New Releases, For You, Today, and Review Candidate cards now pair external copy drag with `AddToBucketMenu`, and Pocket completes General/Artist/Playback drops without a `BucketBoard` island. Spotify-only releases remain explicit display-only fallbacks and no Spotify id is written as a catalog id. Local browser checks covered Home/Bucket/Memo/editor/critique and the 390px add POST; prod Home rendered 15/15 catalog cards with drag+add+open and zero console errors. The selected browser could not emit a trusted native HTML5 drag, so exact payload + route tests and live `draggable` DOM evidence are recorded instead of claiming the gesture. | 9 |
| 2026-08-07 | Stage 8 shipped (front #383, `1788bf1`; deploy `31136547054`; prod smoke 19/19). `EditorialAlbumTargetAdapter` now renders live writer album subjects through the canonical card while rating, BEST NEW MUSIC, reopen, and writer layout remain surface-owned; empty/artist subjects stay bespoke and a negative test freezes published `ReviewCard` on its document renderer. OQ2 resolved to require `unresolvedAlbumCardData()` for Spotify-only fallbacks, with the sole current producer migrated. Desktop and 390px browser checks passed with keyboard rating, BNM, reopen/focus restoration, zero overflow, and zero nested interaction. Next is Stage 9 legacy removal, gated on the full parity suite. | 8 |
| 2026-08-06 | Stage 7 shipped (front #382, `775f683`; deploy `31097251431`; prod smoke 19/19). `MemoAlbumCardAdapter` now renders the memo identity through the canonical card, and its typed track-action boundary requires `add` beside every `drag`, resolving BUG-24. The 390×844 real-browser pass found zero overflow/nested interaction and confirmed add opens only the bucket picker. A review-discovered nested-overlay gap was fixed at the shared `AddToBucketMenu`: focus, Tab, Escape order, and trigger restoration now work above the memo. Raw CDP touch dispatch was unavailable and is not claimed. Next is Stage 8, gated on Open Question 2's smart-constructor decision. | 7 |
| 2026-08-06 | Stage 6 shipped (front #381, `5803776`; deploy `31089538369`; prod smoke 19/19). Live Bucket album memberships now use `BucketAlbumCardAdapter` over the canonical card; membership identity and operations remain bucket-owned, while non-album members remain on the legacy generalized renderer. Desktop and 390px real-browser layout/open/action-sheet checks passed; exact CDP touch emulation was unavailable because the in-app browser exposed no CDP and the active Chrome profile lacked the control extension, so that limitation is recorded rather than overstated. Next is Stage 7 (Memo adapter + BUG-24). | 6 |
| 2026-08-06 | Stage 5 shipped (front #380, `cb3a734`; deploy `31084951887`; prod smoke 19/19). `ForYouReleasesCard`, `TodayAlbumBuckit`, and `ReviewCandidates` now use surface-owned adapters over the canonical card; optional-id For You items remain display-only, and the anniversary, rating, comment, and editor affordances retain their slots. Desktop and 390px real-browser checks passed. Per owner decision, `TodaySongBuckit` remains bespoke. Next is Stage 6 (Bucket adapter; BUG-21 prerequisite already shipped). | 5 |
| 2026-08-06 | Stage 4 shipped (front #379, `e1268a7`; deploy `31082278000`; prod smoke 19/19). `NewReleasesCard` is the first live `AlbumCard` consumer through a Home-owned adapter; its release label, reviewed badge, intent prefetch, artist link, and album-overlay payload remain surface-owned. Desktop and 390px real-browser checks passed with no overflow, and the legacy renderer remains as the Stage 9 parity fixture. Next is Stage 5 (remaining Home surfaces). | 4 |
| 2026-08-06 | Stage 3 shipped (front #377, `c32949a`; deploy `31079317610`; prod smoke 19/19). The shared `AlbumCard` now owns canonical grid/row presentation and capability-gated interaction, while remaining unused by live surfaces. Tests freeze the four legacy renderers' real, different DOM/style signatures and separately pin the intentional canonical normalization; `docs/frontend/component-map.md` now records the component contract and zero-consumer state. Next is Stage 4 (`NewReleasesCard`, open-only). | 3 |
| 2026-08-06 | Stage 2 shipped (front #373, `386539f`; deploy `31075214832`; prod smoke 19/19). `AlbumCardData` and `AlbumCardCapabilities` now form the canonical shared contract; the capability union rejects drag without its `add` tap fallback. The unused `AlbumCard` shim renders `null` and has no live consumers. Next is Stage 3 (shared presentation, still no live-surface migration). | 2 |
| 2026-08-06 | Stage 1 shipped (front #372, `14ccaef`; deploy `31074197178`; prod smoke 19/19). `openAlbumUnresolved()` makes the Spotify-fallback id and `unresolved: true` an inseparable construction path, and the sole fallback producer now uses it. The independent `CHORE-openalbumdetail-id-pairing-guard` plan row is complete and removed; next is Stage 2 (types only). | 1 |
| 2026-08-06 | Owner promoted the RFC from `draft` to `accepted`; implementation starts with Stage 1 only, preserving the RFC's staged migration and one-step-per-session gate. | 1 |
| 2026-08-06 | RFC filed following the 2026-08-06 evidence-based audit (7 parallel investigations against `origin/main`, not against either sibling RFC's own completion claims). 4 of 6 hypothesized defects confirmed unresolved (BUG-21/23/24, defect 6); 1 partially fixed with a newly-found residual (BUG-22); 1 downgraded from "confirmed" to "structural risk, currently contained" (defect 5) | 0 |
| 2026-08-06 | BUG-22 fixed independently (front #370, `71bd0a3` / deploy 31064849495, prod smoke 19/19): the `playbackSession` convergence effect now bumps a `controlGen` counter in `setMode`'s `finally`, included in its dependency array, replaying the deferred session state once `setMode`'s busy window closes. `playPause`/`seek`/`skip`'s existing confirm-read path and its pinning test are unchanged. No card-architecture dependency — no effect on this RFC's stages. | — |
