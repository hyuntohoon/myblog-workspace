# ARCH-entity-interaction-v2: one canonical definition per entity — identity, URL, open, data, actions, drag payload

- **Status**: accepted (owner approval 2026-08-03, in-session)
- **Owner**: TBD
- **Created**: 2026-08-03
- **Plan row**: `plan.md` → ARCH-entity-interaction-v2
- **Extends** (does not replace): `docs/archive/done/rfcs/ARCH-entity-interaction-contract.md`
  (`TrackRow` + `lib/entityLinks.ts` contract points),
  `docs/archive/done/rfcs/ARCH-entity-interaction-unify.md` (`openAlbum`/`openTrackAlbum` dispatch +
  the app-wide `AlbumOverlay`), `docs/archive/done/rfcs/RFC-ui-surface-unification.md` (the
  public-overlay vs member-modal rule + the surface × treatment table).
- **Consumed by**: `docs/rfcs/FEAT-playback-bucket-player.md` Step 8 (its drop sources need this
  RFC's drag-payload contract; only two surfaces in the product are draggable today).
- **Reopens, with cause**: `ARCH-entity-interaction-contract` OQ2 (`play`/`add` reserved slots) and
  its "no album-detail unification" non-goal; `RFC-ui-surface-unification` owner decision 8 (keep the
  dual album-detail system); `ARCH-entity-interaction-unify`'s "no album detail *route*" decision.
  Each is named individually in the *Comparison table* with what changed since it was taken.

---

## Goal

For each of **album**, **track** and **artist** there is one written, code-enforced definition of:
its **canonical id**, its **canonical URL** (or the explicit decision that it has none), what
**opening** it does, what **data** is displayed, what **actions** are available, and what its
**drag payload** is. Every surface in `myblog_front` conforms to that definition or is listed as a
documented, reasoned exception — no surface invents its own behavior. Most album, track and artist
representations become draggable with a uniform payload, the internal-**move** vs external-**copy/add**
distinction is preserved unchanged, and every drop target declares which of **direct-add**,
**transform** or **reject** it performs for each entity type, with a visible state for each. Mobile
and pointer conflicts (click vs drag vs scroll) are settled by a measured prototype, not by picking a
library. `docs/frontend/component-map.md` carries the resulting contract and is re-stamped.

## Non-goals

- **No backend or contract change unless the audit proves a payload gap.** The three predecessor RFCs
  were front-only; the one that needed ids (`RFC-ui-surface-unification` Step 4) added them
  additively with no migration. Same posture here: a missing id is a flagged, separately-scoped
  contract add, not something smuggled into a refactor.
- **No new entity types.** Album, track, artist. Review, snapshot, playback and research-note
  membership kinds exist and are untouched.
- **No vanilla → React migration for its own sake.** The `/review/[slug]` inline editorial tracklist
  (`scripts/albumDetail.client.ts`, ★ picks + ▶/＋) is a first-class editorial surface, not a
  duplicate — the `ARCH-entity-interaction-unify` Step-2 audit established that deleting it is a UX
  regression. It participates in this contract through the existing window-event bridge idiom
  (`pb:add-track` → `ReviewTrackAdder`), or it is documented as an exception. It does not get rewritten.
- **No monolith splitting** (`BucketBoard.tsx` is 2,752 lines) and no `AddToBucketMenu` /
  `BucketPickerSheet` merge — nothing is blocked by either, and `necessity-gate` applies.
- **No change to the member-writable path's architecture.** The architect rule from
  `ARCH-entity-interaction-unify` Step 1 stands: the `ent:*` event cannot carry writable/bucket
  context, so member surfaces stay on `onOpen(DetailTarget)`. "Unifying" member call sites onto the
  lossy event is explicitly forbidden, not merely unwanted.
- **No playback behavior.** Queue semantics, the play ladder and the player forms belong to
  `FEAT-playback-bucket-player` and `FEAT-member-player`. This RFC defines only the *payload* a
  playback drop consumes and the *action slot* a play affordance occupies.
- **No lyrics-privacy change.** `GET /api/lyrics/{id}` is `require_owner`; the lyrics action slot is
  defined here, its authorization is not.

---

## Current state

Measured 2026-08-03 against `myblog_front/src`. **`docs/frontend/component-map.md` is stale** — see
the last subsection; that staleness is itself evidence that Step 1 must re-measure rather than copy.

### Entity definitions today — three different shapes

| | Album | Track | Artist |
|---|---|---|---|
| Canonical id | DB uuid `albumId`; `spotifyAlbumId` on some payloads; **null** = not in catalog | DB uuid `trackId`; `spotify_id` on some; **null** = Spotify-only hit | DB uuid; **often absent** from payloads |
| Canonical URL | **none** — no `/album/[id]` route (owner decision 2026-07-08) | **none** | `/artist/[id]/` — trailing slash canonical (`artistHref`) |
| Open behavior | **three paths**: `openAlbum` event → app-wide read-only `AlbumOverlay`; `onOpen(DetailTarget)` → member writable `AlbumDetail`; the `/review/[slug]` **inline editorial tracklist** (vanilla, always visible, not a modal) | `openTrackAlbum` → the album overlay (public bespoke rows); `TrackRow.open` → the member modal (LikedBoard) | route navigation |
| Actions | 담기 (`AddToBucketMenu` / `BucketPickerSheet`), 이 앨범 재생 ▶ (`sendConnectPlay`, member-only), 평론 후보 mark | 가사 (`TrackRow.lyrics` → `LyricsSheet`), ▶ (review tracklist + pocket tray only), ＋ (review tracklist), ★ (writer) | — (navigate only) |
| Drag payload | `DndItem` from **two surfaces only** | same `DndItem`, `trackId` set | same `DndItem`, `artistId` set |

### Drag exists on exactly two surfaces

Repo-wide `draggable` grep: `BucketBoard.tsx:569` (member chip), `BucketBoard.tsx:965` (bucket node),
`PocketTray.tsx:435` + `:589` (tray member). **Nothing else in the product is draggable** — not
search cards, not the album overlay, not `ArtistHub`, not the review page, not `NowPlaying`, not
`LikedBoard`, not the home strips, not `/releases/`.

The payload is `DndItem` (`lib/boardDnd.ts:23`):

```ts
interface DndItem { kind: 'album' | 'bucket', itemId?, fromBucketId?, bucketId?, copy?,
                    albumId?, fromLib?, source?, trackId?, artistId?, srcItemType? }
```

Note `kind: 'album' | 'bucket'` is a **misnomer** — `kind:'album'` means "a bucket member of any
`srcItemType`", so an artist member drags as `kind:'album'` with `srcItemType:'artist'`. Any new
external drag source inherits this confusion unless the payload is renamed.

### The move/add/transform/reject rules already exist and work

`lib/boardDnd.ts` (102 lines, extracted by `REFACTOR-frontend-member-surface` Step 4a specifically so
these are unit-testable) is the **single source of drop semantics** for the board card, the trash
dock, and the reverse-DnD Pocket bridge. It already encodes all four states the brief asks for:

- **direct-add** — General bucket, matching type → `copyAlbum` / `insertAlbum`.
- **transform** — Artist bucket + album/track source → `expandSource` (album/track → **credited
  artists**). The source row is never stored; the original is never removed.
- **reject** — `canAcceptAlbumDrag` returns false → no glow, no optimistic insert, and (the D-series
  invariant) the target **stays in place, muted** — the tray must not reflow during a drag.
- **internal move vs external copy/add** — `copy` (recent-plays strip) and `fromLib` (the
  sync-owned library bucket) drop as a **COPY**; a real member with `fromBucketId !== target.id`
  drops as a **MOVE** (`insertAlbum`). Same-bucket drops are guarded so they do not persist a
  spurious reorder.

`lib/pocketBuckit/boardDnd.ts` mirrors the accept-gate for the Pocket island (two React roots cannot
share the payload, so a window event carries it) and explicitly re-checks authoritatively on drop.

**This is the asset of this RFC, not its problem.** The rules are right; they are reachable from two
surfaces.

### Non-drag path already exists and is the primary path on touch

`AddToBucketMenu` (`components/member/pocket/AddToBucketMenu.tsx`, 281 lines) is the WCAG 2.5.7
non-drag peer — self-styled, `member.css`-independent so it works on any surface, with a logged-out
`pb:resume` intent handoff (`lib/pocketBuckit/intent.ts`, tagged union over `album | track | review`,
single-drain, TTL-bounded). `BucketPickerSheet` is the member-only variant. FEAT-pocket-buckit's
cross-cutting rule stands: **no default may depend on HTML5 drag**.

### The album-detail situation, stated accurately

The brief asks to "explicitly revisit the previous decision to retain two album-detail systems."
That decision has been taken **and re-affirmed twice**, and what exists now is not what the phrase
suggests:

1. `ARCH-entity-interaction-contract` (2026-07-03) non-goal: "No album-detail unification… the
   difference is intentional per-context behavior, not drift."
2. `ARCH-entity-interaction-unify` (2026-07-08) **partially resolved it**: Step 1 extracted the shared
   read-only `components/album/AlbumDetailView.tsx`, used by **both** the app-wide `AlbumOverlay`
   (public, event-opened) and the member writable `AlbumDetail` (memo/edit stay member-side). The
   component-map's "load-bearing duplication #1" was struck as *resolved*.
3. `RFC-ui-surface-unification` (2026-07-18, owner decision 8) re-affirmed the split and **codified
   the rule** instead: *public/read contexts open the shared overlay; dashboard work contexts open
   the member modal; the overlay is the default for anything new.*

So today it is **one shared read body, two hosts** (differing in whether they can carry writable
bucket context), plus a **third, genuinely different surface** — the review page's inline editorial
tracklist. The honest open question is not "merge two duplicates" (they are already merged where they
can be) but: **does the read-only host and the writable host need to be two components at all, now
that the read body is shared?** The architect rule says the *event* cannot carry writable context —
it does not say the *component* cannot. That is the question Step 2 answers, with the answer allowed
to be "no change".

There is a smaller, concrete duplication the map does flag and which is *not* resolved: the member
`AlbumDetail`'s `MemoWindow` replaced `TrackRow` with its own `memo-trow`, so **the lyrics affordance
exists twice, hand-rolled** — "a place a change must be made twice."

### Component-map is stale — measured

`docs/frontend/component-map.md` is stamped **2026-07-08** and states artist names are "**Not
linkable** (payload carries names only, no artist ids): `NowPlaying`, `LikedBoard` rows". Both are
false as of today:

- `components/member/NowPlaying.tsx:43` imports `artistHref`; `ArtistNames` (`:761`) renders real
  links at `:949` and `:999` (shipped in FEAT-member-player #293, 2026-07-19).
- `components/member/LikedBoard.tsx:15,39,91,318` carries `artistId` from `SavedTrackItem.artist_id`
  and links it (shipped in `RFC-ui-surface-unification` Step 4, front #299, 2026-07-21).

The map's own rule — "a stale Verified stamp is the signal to re-verify, not to trust" — applies.
**Step 1 re-measures every row; nothing is copied forward.**

### Interaction-conflict surface (unmeasured today)

Nothing in the product currently has to resolve click-vs-drag-vs-scroll, because the two draggable
surfaces are grid tiles and list rows inside scroll containers that were built around them. Making a
search result card, a home strip tile, a review-page track row and a player queue row all draggable
introduces conflicts that **have not been measured here**:

- HTML5 native DnD has **no touch support** — `BucketBoard` already falls back to `ActionSheet`.
- A drag threshold on a horizontally-scrolling home strip competes with the scroll gesture.
- The lyrics viewer's vertical drag is already line-stepping (FEAT-lyrics-viewer-playback chose a
  full-screen queue swap over a sheet **for exactly this reason**) — a precedent that gesture
  collisions in this product are resolved by changing the surface, not by tuning thresholds.

---

## Target state

### E1 — canonical entity definitions (written here, enforced in code)

One table per entity covering: canonical id + null semantics, canonical URL (or "none, by decision"),
open behavior, displayed data, action set, drag payload. Produced by Step 2 from Step 1's audit,
recorded in this RFC **and** in `component-map.md`.

### E2 — one drag payload

`lib/entityDrag.ts` — a single typed payload used by every draggable representation:

```ts
type EntityRef =
  | { entity: 'album',  albumId: string,  title, artist, cover }
  | { entity: 'track',  trackId: string,  albumId: string | null, title, artist }
  | { entity: 'artist', artistId: string, name, image }

type DragPayload = {
  ref: EntityRef
  /** internal = a real bucket membership (MOVE default); external = any other surface (COPY/ADD). */
  origin: { kind: 'internal', itemId: string, fromBucketId: string } | { kind: 'external' }
}
```

- **The move/add distinction is preserved by construction**: `origin.kind` carries it, replacing
  today's implicit `copy` / `fromLib` / `fromBucketId` triad.
- `DndItem` is **adapted, not deleted** — `boardDnd.ts`'s rules are correct and unit-tested; Step 3
  introduces an adapter both ways so board behavior is provably byte-identical before any surface is
  rewired. Renaming `kind:'album'` (which really means "a member of any type") is part of Step 3.
- **A null id is non-draggable**, not a crashing drag — the `openTrackAlbum` no-op precedent
  (`ARCH-entity-interaction-unify` OQ4) extended to drag.

### E3 — drop-target declarations

Every drop target declares, per entity type, one of **direct-add** / **transform** / **reject**, and
each has a required visible state:

| State | Visual contract | Existing precedent |
|---|---|---|
| direct-add | target highlights, verb visible | General bucket `add` |
| transform | target highlights **and names the transform** (`앨범 → 트랙 14곡`) | Artist bucket album→artists |
| reject | target **stays in place**, muted, with a concise reason — never hidden, tray never reflows | `canAcceptAlbumDrag` false branch |

Known targets and their matrix — General bucket, Artist bucket, Playback Bucket, trash dock, bucket
node — filled in Step 2. The Playback Bucket's row is *specified* by
`FEAT-playback-bucket-player` and *consumed* here.

### E4 — action slots opened

`TrackRow`'s `play` and `add` slots — reserved since `ARCH-entity-interaction-contract` OQ2 pending a
product decision — are **granted** by this RFC's owner-approved scope, and `drag` joins them. Track
row actions become `{lyrics?, open?, play?, add?, drag?}`. The two hand-rolled twins (`memo-trow`,
review tracklist) are either brought onto the contract or listed as reasoned exceptions with a
revival trigger — no fake unification (the `ARCH-entity-interaction-contract` house rule).

### E5 — mobile and pointer conflicts, settled by measurement

A prototype, not a library choice, decides: the pointer-drag threshold that coexists with vertical
and horizontal scroll, and the non-drag equivalent on touch. The default candidate is the shipped
`AddToBucketMenu` (already the WCAG primary path); the prototype's job is to prove or refute that it
covers the new surfaces, and to measure whether a long-press drag can coexist with the scroll
containers those surfaces live in.

---

## Comparison table — existing decision / retained / superseded / new

| # | Existing decision | Source | Verdict | What this RFC does |
|---|---|---|---|---|
| 1 | `lib/entityLinks.ts` is the artist/review href contract point; trailing slash canonical | contract Step 3 | **Retained** | Extended, not replaced |
| 2 | `openAlbum` / `openTrackAlbum` window events; album/track have **no route** | unify Step 1/3 | **Retained** (the overlay); **URL question reopened with cause** | unify called an album route "a possible later RFC, not here" — the brief asks to define canonical URLs, so this *is* that later RFC → **OQ1** |
| 3 | Artist click → route `/artist/[id]` | unify | **Retained unchanged** | The one entity whose canonical URL is settled |
| 4 | Member surfaces stay on `onOpen(DetailTarget)`; the `ent:*` event cannot carry writable context | unify Step 1 architect rule | **Retained — load-bearing** | Constrains E1; "unifying" member call sites onto the event stays forbidden |
| 5 | Null ids are first-class; non-navigable entities no-op rather than crash | unify OQ3/OQ4 | **Retained, extended to drag** | A null-id entity is non-draggable |
| 6 | Read-only album body shared (`AlbumDetailView`); duplication #1 struck as resolved | unify Step 1 | **Retained** | The revisit starts from this state, not from "two duplicate modals" |
| 7 | **Keep the dual album-detail system**, codify the rule instead | ui-surface-unification owner decision 8 | **Reopened with cause; outcome open** | What changed: the read body is now shared (#6) and drag is about to be added to every album representation. Step 2 answers "two hosts or one"; "no change" is an allowed answer → **OQ2** |
| 8 | The `/review/[slug]` inline editorial tracklist is a **distinct surface**, not a duplicate; deleting it regresses UX | unify Step-2 audit | **Retained unchanged** | Participates via the event bridge or is a documented exception; never rewritten |
| 9 | `TrackRow` `play`/`add` are **reserved slots**; granting them is a product decision needing approval | contract OQ2 | **Superseded by owner product scope** | The brief's "most representations should support drag and drop" + playback drops *is* that approval. Slots open; `drag` added |
| 10 | Vanilla review tracklist excluded from `TrackRow`; **revival trigger = a track action that must ship on the public review page** | contract non-goal | **Trigger fires — evaluated, not auto-executed** | Drag on public track rows meets the stated trigger. Step 4 decides bridge-vs-adopt; the non-goal against gratuitous migration still holds |
| 11 | Internal **MOVE** default + external **ADD/COPY**; conversion preserves the original; bucket-local Undo | pocket-buckit D-series | **Retained — explicitly preserved** | Encoded structurally in `DragPayload.origin` instead of inferred from three flags |
| 12 | Reject state: target **stays in place**, muted, reasoned; the tray never reflows mid-drag | pocket-buckit D-series | **Retained as a hard visual invariant** | Becomes a required declaration per target × entity |
| 13 | Cross-type 1:N expansion requires **mandatory confirmation** | pocket-buckit D8 | **Retained as the general rule**; superseded **only** for an intentional Playback-Bucket drop | The exception is scoped and owned by `FEAT-playback-bucket-player` OQ3, not generalized here |
| 14 | No default may depend on HTML5 drag; `AddToBucketMenu` is the WCAG 2.5.7 **primary** path on touch | pocket-buckit | **Retained — binding** | E5's prototype must prove coverage, not replace the principle |
| 15 | `boardDnd.ts` is the single source of drop semantics, pure + unit-tested | REFACTOR-frontend-member-surface 4a | **Retained** | Payload is adapted around it; the rules are not rewritten |
| 16 | Two "add to bucket" flows (`AddToBucketMenu` / `BucketPickerSheet`) stay separate — nothing blocked | contract non-goal + component-map #2 | **Retained** | Necessity gate: no merge without a named concrete harm |
| 17 | `component-map.md` is the contract registry; a stale stamp means re-verify | ARCH-frontend-component-map | **Retained, and enforced** | Measured stale today (NowPlaying/LikedBoard artist links). Step 1 re-measures; Step 6 re-stamps |
| — | **One typed drag payload across all surfaces** | — | **NEW** | `DndItem` is board-internal and its `kind` is a misnomer |
| — | **Most album/track/artist representations draggable** | — | **NEW** | Exactly 2 surfaces are draggable today |
| — | **Per-target × per-entity direct-add / transform / reject declaration** | — | **NEW** | The three states exist in code but are implicit and General-vs-Artist only |
| — | **Canonical URL decided per entity** (incl. "none, by decision") | — | **NEW** | Never written down; artist has one by accident of being a route |
| — | **Measured click/drag/scroll conflict resolution + mobile equivalent** | — | **NEW** | Never measured; the only precedent is "change the surface" (lyrics queue swap) |

---

## Steps

One step per session (hard rule #4). Steps 1–3 are the prerequisite block for
`FEAT-playback-bucket-player` Step 8.

### Step 1 — full surface re-audit (docs-only, measurement)

Re-measure **every** album / track / artist representation in `myblog_front/src` — id availability
and nullability, open behavior, displayed data, actions, draggability — and compare relevant external
product patterns (Spotify, Apple Music, Are.na, Finder/Yoink for drag semantics; the
FEAT-pocket-buckit reference analysis is the precedent for how this repo does that, and its
conclusions on Spotify's overloaded "Add" and its churning queue are already recorded — extend, do
not repeat). Nothing is copied from `component-map.md`; it is **measured stale** (NowPlaying /
LikedBoard artist links) and that is the reason.

Output: a surface × entity × (id / URL / open / data / actions / drag) matrix in this RFC, plus a
list of surfaces whose payload lacks the id needed to act — flagged, **not** fixed here.

**Verification**: every row cites `path:line`; a spot-check of ≥5 rows in a real browser; the
"payload gap" list is grep-reproducible.

---

### Step 2 — canonical definitions + drop matrix + the album-detail decision (docs-only)

Fill E1 and E3 from Step 1. Resolve **OQ1** (canonical URLs) and **OQ2** (two album-detail hosts or
one) with the owner, both allowed to resolve as "no change". Record the drop matrix including the
Playback Bucket row.

**Verification**: doc review; each decision names the prior decision it retains or supersedes and
what changed since.

---

### Step 3 — `lib/entityDrag.ts` + adapter, board behavior provably unchanged (front-only)

Introduce the payload and a bidirectional adapter to `DndItem`; rename `kind:'album'` to what it
means; keep `boardDnd.ts`'s rules untouched. **No surface gains a drag in this step** — the point is
that the board and the tray behave identically through the new payload before anything new depends
on it.

**Verification**: `pnpm lint` (antfu, before commit) + `pnpm exec astro check` (Node 20) +
`pnpm test`; `boardDnd.test.ts` extended to run every existing case through the adapter and assert
identical `ops` calls; real-browser CDP on the board + tray: move, copy-from-recent, library copy,
artist expansion, trash, bucket-into-bucket, and a rejected drag that does **not** reflow the tray.

**Rollback**: revert — additive until a surface uses it.

---

### Step 4 — pointer/gesture prototype + mobile equivalent (measurement, then a narrow decision)

Prototype in a real browser on real surfaces (not a synthetic harness — memory
`feedback-front-verify-live-dom-not-harness`): drag threshold vs vertical scroll on a list, vs
horizontal scroll on a home strip, vs a click on a card that also opens an overlay; and the touch
path. Measure; then decide, recording the numbers.

**Verification**: CDP with `emulate("390x844x3,mobile,touch")` (not `resize_page` — memory
`reference-cdp-mobile-emulation`); a recorded table of threshold × surface × outcome; a decision row
in the Decisions log naming what was measured. **A decision made without the measurement fails this
step.**

---

### Step 5 — roll the contract out across surfaces (front-only, possibly split by surface group)

Apply E1–E4 surface by surface. Open `TrackRow`'s `play`/`add`/`drag` slots. Bring or document the
two hand-rolled track-row twins. This is the step most likely to need splitting; the split axis is
**surface group** (public read surfaces / member dashboard / search / writer), never entity type — a
half-migrated entity is worse than a half-migrated surface.

**Verification**: lint + astro check + `pnpm test`; CDP matrix — one drag and one non-drag add per
surface group, an id-less entity proving non-draggable, mobile 390 pass; grep gate: no hand-rolled
drag payload outside `lib/entityDrag.ts`.

---

### Step 6 — `component-map.md` rewrite + re-stamp (docs-only)

Entity-navigation, track-click and ownership sections rewritten to the new contract; the
2026-07-08 stale rows corrected; impact template filled; `Verified` re-stamped.

**Verification**: doc-only; every claim spot-checked against code in the same session.

---

## Dependencies and sequencing

- **Steps 1–3 gate `FEAT-playback-bucket-player` Step 8.** That RFC's Steps 1–7 do not depend on this
  one; only its external drop sources do.
- **Step 2's drop matrix consumes `FEAT-playback-bucket-player`'s Playback Bucket row** — that row is
  specified there and referenced here. If the playback RFC has not reached Step 2 yet, the row is
  recorded as pending and the matrix ships without it.
- **Step 4 blocks Step 5**, and its outcome feeds `FEAT-playback-bucket-player` OQ5 (the mobile
  add-to-queue path).
- No cross-repo ordering: this RFC is front-only unless Step 1's payload-gap list turns into a
  separately-scoped contract add (the `RFC-ui-surface-unification` Step 4 precedent, which needed no
  migration).

---

## Open questions

1. **Does an album get a canonical URL?** *(blocks Step 2.)* `ARCH-entity-interaction-unify` decided
   **no `/album/[id]` route** (owner, 2026-07-08) in favor of the app-wide overlay, and explicitly
   parked "SEO/deep-link for albums" as "a possible later RFC". The brief now asks to define canonical
   URLs — so this is that later RFC and the question is legitimately live, not a re-litigation.
   What actually changed since: `SEO-review-structured-data` shipped `MusicAlbum` JSON-LD on review
   pages, and the 404 fallback shell (`NotFoundShell`) proved a runtime-hydrated entity page works
   without a build. **No default asserted** — the trade (deep-linkable/shareable/indexable vs one more
   route, a build-time path problem for a growing catalog, and a second way to open an album) needs
   the owner, and the same question applies to tracks with a different answer likely.
2. **Two album-detail hosts, or one?** *(blocks Step 2.)* Stated accurately in *Current state*: the
   read body is already shared; the split is read-only-event-host vs writable-prop-host. What changed
   since owner decision 8: the shared body landed, and drag is about to be added to every album
   representation, which means a third behavior to keep in sync across hosts.
   **Recommended default: keep two hosts, unify nothing further** — the architect rule that the event
   cannot carry writable context is unchanged, and a merged host would have to branch on
   `isLoggedIn()` + bucket presence internally, which is the option the Step-1 architect pass already
   rejected in favor of extraction. The genuinely actionable item is the smaller one: the
   `memo-trow` / `TrackRow` twin, where a lyrics change must be made twice. Owner confirmation still
   needed, because the brief asked for the revisit explicitly.
3. **How far does "most representations" go?** *(blocks Step 5's scope.)* Some representations are
   arguably not drag sources: header-search dropdown rows (single-action keyboard rows — already
   excluded once, deliberately, in `RFC-ui-surface-unification` Step 4), writer ★-pick rows (a
   different selection semantic), and analysis-chart data points (query output with no entity id).
   **Recommended default**: drag every representation that has a stable entity id **and** lives in a
   browsing context; exclude command/keyboard surfaces and selection-mode rows, listing each
   exclusion with its reason. Needs a yes because "most" is the owner's word and the boundary is a
   product call.
4. **What replaces drag on touch?** *(blocks Step 5; answered by Step 4's measurement, not by
   opinion.)* Candidates: the shipped `AddToBucketMenu` on every surface (lowest risk, already the
   WCAG primary path), long-press drag, or a selection mode. Recorded as an OQ rather than
   pre-decided because the brief explicitly asks to prototype before fixing one interaction.

---

## Risks

- **A refactor that changes behavior while claiming not to.** `boardDnd.ts`'s rules are subtle
  (same-bucket guard, `copy` vs `fromLib` vs move, the library album-id guard). Mitigation: Step 3's
  adapter must make every existing `boardDnd.test.ts` case assert *identical* `ops` calls, and no
  surface changes in that step.
- **Fake unification.** The house rule from `ARCH-entity-interaction-contract` — do not claim
  "unified track rows" while the highest-traffic tracklist cannot consume the component. Two
  hand-rolled twins exist; each must be adopted or documented with a revival trigger. A grep gate
  only proves *hand-rolled payloads* are gone, not that behavior converged.
- **Gesture decisions made from a synthetic harness.** Layout and overlay behavior must be verified
  against the live DOM (memory `feedback-front-verify-live-dom-not-harness`), and a stub that answers
  instantly erases the very races a drag threshold has to survive.
- **Scope inflation via "most".** OQ3 exists to bound it; Step 5 splits by surface group so a
  descope leaves whole surfaces consistent rather than entities half-done.
- **Re-litigating settled decisions.** Three of the four reopened items were decided by the owner
  with a written rationale. Each is reopened with an explicit "what changed since", and two carry a
  recommended default of **no change** — the reopen is a check, not a presumption of reversal.

## Decisions log

| Date | Decision | Step |
|------|----------|------|
| 2026-08-03 | **Owner: Status draft → accepted.** Runs in parallel with `FEAT-playback-bucket-player` (different repos, no shared files); only that RFC's Step 8 waits on Steps 1–3 here | 1 |
| 2026-08-03 | Filed as a draft alongside `FEAT-playback-bucket-player` after a joint audit; scoped as the **third** RFC in the entity-interaction lineage (contract → unify → v2), inheriting both predecessors' contract points rather than replacing them | 1 |
| 2026-08-03 | **`component-map.md` measured stale** — its "NowPlaying / LikedBoard artists not linkable" claim is false since front #293 (2026-07-19) and #299 (2026-07-21). Step 1 therefore re-measures every row instead of extending the map | 1 |
| 2026-08-03 | **The album-detail revisit starts from the accurate state**, not the brief's framing: `ARCH-entity-interaction-unify` Step 1 already extracted the shared read body and struck component-map duplication #1. The live question is two hosts vs one, and the recommended default is **no further change** | 2 |
| 2026-08-03 | `boardDnd.ts`'s move/transform/reject rules are **retained verbatim**; only the payload around them is unified. Rewriting proven, unit-tested drop semantics was rejected as the largest avoidable risk in this RFC | 3 |
| 2026-08-03 | `ARCH-entity-interaction-contract` OQ2's reserved `play`/`add` slots are **granted** — the brief's drag-and-drop scope plus the Playback Bucket's track drops constitute the product approval that OQ2's default was waiting for | 5 |
