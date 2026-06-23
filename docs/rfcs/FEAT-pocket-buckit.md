# FEAT-pocket-buckit: Pocket Buckit — a global drop-into-bucket layer (design exploration)

- **Status**: draft
- **Owner**: TBD
- **Created**: 2026-06-23
- **Plan row**: `plan.md` → FEAT-pocket-buckit
- **Related**: `docs/rfcs/FEAT-bucket-identity.md` (Direction C — merge `들을 것` into the bucket model), `docs/rfcs/FEAT-multi-user-accounts.md` (per-user scoping), `docs/rfcs/FEAT-liked-tracks-workbench.md` (the `분석 버킷` track→album promote path)

> **This RFC is a pre-convergence design-exploration brief, not an execution plan.** It deliberately does
> NOT pick a final UI direction. Its job is to (1) audit the existing model, (2) extract reference
> patterns, (3) enumerate the meaningful UI/UX option space, and (4) carry a verbatim "Pocket Buckit
> Design Atlas" prompt (Appendix A) that requires side-by-side visual comparison of the options before
> any implementation. `Steps` are intentionally TBD until the atlas exists and the Open Questions are
> answered.

---

## Goal

A persistent **global interaction layer** ("Pocket Buckit") where a user can encounter an album, track,
review, listening-history record, artist, research-note, analysis-signal, or time-period **anywhere** in
the product and drop it into a **purpose-defined bucket** without leaving that context — annotate,
organize, replay, summarize, or use it for criticism, then connect it to a review or published writing.
Reachable from lower-left and lower-right controls that open a **horizontal bottom tray** showing a row
of visible bucket targets, with cross-type conversion on drop and per-item Undo.

## Non-goals

- This RFC does **not** select a tray-shell family, card treatment, or confirmation pattern — that is
  what the Design Atlas (Appendix A) exists to compare.
- It does **not** introduce any schema, migration, contract, or infra change. (None are written here.)
- It does **not** make Pocket Buckit a full editor — the tray stays quick, reversible, understandable;
  deep work happens on a separate full bucket page.
- It does **not** assume the playback bucket performs real Spotify playback (see OQ2 — rule #9 forbids
  synchronous Spotify calls on user-facing endpoints).

---

## Current state (repository audit — exact paths)

### The reframing: "bucket" already exists and conflicts with the premise

Today the codebase's "bucket" is exactly **one table**, `review_buckets` — an **album-only**,
**single-user** (no `user_id`), **`/profile`-scoped** review-pipeline kanban column
(`myblog_shared_db/src/myblog_shared_db/models.py:354-472`). So Pocket Buckit is the **union of two
net-new efforts**: (1) a global interaction layer (none exists — the bucket UI lives only in
`myblog_front/src/components/member/BucketBoard.tsx`), and (2) a data-model generalization (album-only
membership → polymorphic membership + cross-type conversion + per-item undo + a playback queue). It also
overlaps the in-flight `FEAT-bucket-identity` RFC, where merging the two competing album collections
(`review_buckets` vs `album_to_listen_items` "들을 것") is still **undecided** (Direction C).

**Terminology collision** — one/near-identical word means 4–5 different things and must be resolved
before a coherent user model exists:

| Term | What it actually is | Source |
|---|---|---|
| `buckit` | the **site brand wordmark** (unrelated to the feature) | `myblog_front/src/constants.ts:6`, `header.astro:85` |
| `평론 버킷` | the real DnD bucket board (album-only) | `BucketBoard.tsx`, `ProfileApp.tsx:20` |
| `분석 버킷` | **not a bucket** — the `/profile` analytics dashboard tab | `ProfileApp.tsx:21`, `StatsTab.tsx` |
| `크레이트 (crate)` | internal code alias (user-facing alias dropped in Direction A) | `FEAT-bucket-identity.md:29-43` |
| `들을 것 / to-listen` | a **separate** second album queue, disjoint from buckets | `models.py:484-502` |

### Data model (schema-level)

| Item | State today | Path |
|---|---|---|
| Bucket | `review_buckets`: name, position, color, is_done (≤1 "평론 완료"), **kind ∈ {'review','spotify_library'}** (only type axis; both album-only), is_public, research_mode ∈ {off,all,selected}, parent_id (self-ref tree). **No `user_id`.** | `models.py:354-419`; `migrations/V6,V11,V15,V16,V18` |
| Membership | `review_bucket_items`: **album_id FK NOT NULL** + UNIQUE(bucket_id, album_id). note, status ∈ {candidate,drafting,published}, post_id, research_selected, prep_tonight. **No item_type/track_id column → polymorphism impossible.** | `models.py:422-472`; `migrations/V6,V22` |
| Second album queue | `album_to_listen_items` ("들을 것"): album_id UNIQUE, position, note. No bucket_id, no user_id. Disjoint from `review_buckets`. | `models.py:484-502`; `migrations/V8` |
| Membership≠source split | **Only one place**: `spotify_library_albums.in_bucket` bool (bespoke to Spotify sync). Not a general primitive. | `models.py:515-546`; `migrations/V15` |
| Playback/queue | **None.** `now-playing` is read-only worker telemetry; no queue-membership table. | `models.py:589-641` |

### Item types — where each renders and what action exists today

| Item | Render location | Current action | As a drop source |
|---|---|---|---|
| **Album** | review hero (`review/[slug].astro:127-168`); search `AlbumCard` **non-navigable `<div class="is-static">`** (`SearchPage.tsx:54-65`); header search row (static); `BucketBoard` cover tiles; `AlbumDetail` modal | add to bucket (the only member type), detail modal | The only bucketable type; public surfaces expose no action |
| **Track** | review tracklist `<li class="lfq-tt-row">` (no id/handle, `albumDetail.client.ts:62-68`); search `TrackRow` (non-navigable); `LikedBoard` rows | "평론 버킷에 담기" only in `LikedBoard` → silently resolves to **parent album**, no confirm, gated on catalogued | Cannot be stored as membership; uri-only rows are gated |
| **review/평론** | MDX content entry (`content.config.ts`), `/review/[slug]` article; search `ReviewCard` (navigable) | read/navigate | **No DB id** — slug + albumIds only; no key to put in a "read-reviews" bucket (collapses to album) |
| **research note** | album-keyed slide-over `components/research/NoteBody.tsx` | view/generate | Not a standalone entity — "notes belong to the ALBUM" (`research.py:1-7`) |
| **artist** | `/artist/[id]` hub (only navigable music entity); search `ArtistCard` | navigate | No artist item type; drop would need discography/top-track expansion or a new type |
| **listening-record** | aggregate-only; no per-event UI identity; `LikedBoard` row is the smallest graspable unit | drill-down (read-only) | No per-record drop target |
| **analysis-signal / time-period** | `ImportAnalysis.tsx` charts/clock/retrospective; period is a **scope selector** (not draggable) | chart click → read-only drill-down (slide-over has **zero actions**) | Query output; no entity id to persist; `charts.tsx` is onClick-only, never draggable |

> There is **no standalone `/album/[id]` or `/track/[id]` route.** Detail is only the `/profile`
> `AlbumDetail` modal + the review-page tracklist. Pocket Buckit cannot assume an entity page hosts
> actions.

### Reusable primitives (all `/profile`-scoped, album-only — the generalization starting points)

- **`BucketPickerSheet.tsx`** — body-portaled bottom sheet listing the bucket tree (flat/indented) for
  tap-to-pick; the coarse-pointer (touch) fallback. The closest existing "pick a bucket target" UI
  (vertical modal sheet, not a horizontal tray).
- **`BucketBoard.tsx` (2288 lines)** — HTML5 native DnD; module-global `let dnd: DndItem|null` (kind is
  `'album'|'bucket'` only), `ops.copyAlbum/insertAlbum/moveBucketInto/moveBucketTo`, document-level
  reset listeners. **No drag on touch** → `ActionSheet` fallback.
- **`TrashDock`** — body-portaled **bottom-center card, mounted only during a drag** (not persistent);
  delete-on-drop. The existing "bottom dock" precedent.
- **localStorage album trash** (`lf_crate_trash`) — the only "undo a removal" (restore via re-add); not
  a per-add Undo toast.
- **`atoms.tsx` `RowAction` union** `{navigate|button|static}` — search rows already have a per-item
  action abstraction (담기 = button); extensible to a bucket-drop action.
- **Mount point**: `src/layouts/layout.astro:32-37` (`<Header/> + <slot/> + <Footer/>`) is the only
  persistent page chrome. Z-index budget (`global.css:46-53`): header = sticky 50, review progress bar =
  progress 60, toast = 100 → a bottom tray must clear 50/60.

### API & auth boundary — the "auth asymmetry" problem

| Surface | Auth | Implication |
|---|---|---|
| `myblog_music` (`/api/music/*`: unified search, album, artist, top-tracks) | **None** (CORS only; no API-GW authorizer; no edge_guard — effectively public) | Drop **sources** are world-readable. track→album parent (`TrackItem.album_id`), album→tracklist (`GET /api/music/albums/{id}`), artist→albums/top-tracks reads all **already exist** |
| `myblog_backend` GET reads (`/api/buckets`, `/api/library/*` analysis/stream-history/research) | **edge_guard only** (CloudFront `x-origin-verify`; no JWT) | Single-owner assumption; analysis = signal/period sources |
| Bucket/library **mutations** (POST/PUT/PATCH/DELETE) | **Cognito JWT** + an explicit route in `infra/apigateway.tf` (404 until added) | All drop **writes** require login |

**Conflict**: on public review/search pages an anonymous user could drag an item, but every drop is
401/403. Single-owner (no `user_id`) means "my purpose buckets" needs multi-user scoping first
(`FEAT-multi-user-accounts.md`, unstarted). Any new Pocket Buckit POST/PUT/DELETE **404s until added to
`infra/apigateway.tf` + applied** (memory `reference-apigateway-post-route-required`).

### Concrete conflicts between the existing model and the premise

1. **Membership is album-only** — a polymorphic membership schema is net-new. (`models.py:422-472`,
   `schemas.py:161-163`, front `DndItem.kind:'album'|'bucket'` `BucketBoard.tsx:47`)
2. **No bucket "types"** — none of albums-to-hear / track-collection / playlist / playback-queue /
   read-reviews / summary / notes exist. `kind` has 2 values. playlist/queue/summary have no backend.
3. **Cross-type conversion unimplemented** — the reads (track→album parent, album→tracks, artist→albums)
   all exist on the music API, but the bucket write accepts only `album_id`, so every conversion must
   terminate at album_id(s). **A track collection / playlist of tracks cannot be persisted today.**
4. **No per-item Undo** — hard cascade DELETE; no soft-delete/tombstone. (Membership≠source split exists
   only as the bespoke `spotify_library_albums.in_bucket`.)
5. **No global layer** — bucket UI is one `/profile` tab; no persistent bottom tray / FAB / corner
   control.
6. **No playback/queue backend** + **hard rule #9** (no synchronous Spotify calls on user-facing
   endpoints) → play now/next/queue is net-new + rule-constrained.
7. **review/note/artist/period are not identifiable/storable** — review = slug (no DB id), note =
   album-keyed attribute, period = query parameter.
8. **Two album collections coexist** (`review_bucket_items` vs `album_to_listen_items`) — "albums-to-hear"
   maps to both and they are not interchangeable; FEAT-bucket-identity leaves the merge undecided.

---

## Design exploration (reference analysis + option matrix + flows + risks)

> Full Korean working brief + the verbatim Claude Design prompt: see Appendix A. This section is the
> condensed English record. It does **not** converge.

### Reference-product analysis (borrow / avoid / adapt)

Seven products analyzed; transferable vs non-transferable separated.

- **Strong transfer**: Apple Music (purpose-named destinations with stable verbs; Play Next = an
  insertion *position*; non-destructive removal); Are.na (item-as-connection, remove = membership only);
  Raindrop / read-later (zero-decision Inbox, save-first-organize-later); Pinterest (top targets first +
  search + inline create); Yoink/Dropover (edge shelf + count badge + flocking); **React Aria / WCAG
  2.5.7** (non-drag "Add to…" + keyboard DnD — legally required, not optional).
- **Anti-patterns (avoid)**: Spotify (single overloaded "Add"; a queue that silently churns/evaporates →
  save-vs-play ambiguity); Milanote/Kosmik (pure spatial canvas → disorder at scale); **Mymind**
  (rationale-free AI auto-organization → destroys editorial trust → provenance is mandatory).
- **Adapt for music-and-criticism**: extend the uniform-drop surface to **non-playable** types (review,
  note, signal, period) so the **bucket** (not the item) decides the transform; make album→tracks
  expansion **explicit/confirmable/undoable** (Apple expands silently); the playback bucket is the
  **only** transient-by-design bucket (kill save-vs-play ambiguity by splitting play from persist);
  duplicate identity is **musical** (album/track ids), warned **at drop time**; every summary membership
  carries a **provenance badge** + "why is this here".

### Mandatory option matrix (A–G) — do NOT converge; `[visual]` = must be rendered side by side

- **A. Entry controls** — `[visual]` left/right open the SAME tray vs FILTERED views (pinned vs
  recent/contextual) vs single control; icon-only vs icon+text; floating button vs edge tab; states
  idle/hover/open/**drag-active**; bucket-count badge. (Decided/textual: shake/modifier summon is an
  accelerator only, corner controls are primary.)
- **B. Bottom tray shell** — `[visual]` **four families**: tangible bucket row / editorial shelf /
  modular utility dock / immersive music-workspace tray. Each compared across: compact-closed, opened,
  drag-active, **many-bucket overflow** (scroll vs paginate vs "more" vs search), pinned vs recent vs
  contextual ordering, how much source page stays visible, desktop, mobile.
- **C. Target card representation** — `[visual]` 5 variants: literal-restrained container / minimal
  editorial / album-art-driven / icon+action-driven / dense utility. Each must communicate: name,
  purpose/verb, accepted-type-or-compatible-drop-state (live vs the dragged item), item count, and the
  outcome (add/convert/play/queue/summarize/write). Plus: empty, single-cover, stacked-grid, pinned,
  "transient-by-design" (playback).
- **D. Drag feedback** — `[visual]` compatible direct / incompatible / conversion-required / one-to-many
  expansion (with a "+14" semantic count badge) / executable / **duplicate** / processing / success /
  **Undo** / error; insertion line for ordered buckets.
- **E. Confirmation patterns** — `[visual]` inline-above-tray / popover anchored to target / expanded
  bottom sheet / focused dialog (high-risk only), mapped to risk per case: ① 1:1 direct add → instant +
  visible Undo; ② 1:1 conversion → compact confirm; ③ 1:N expansion → **mandatory** confirm + count +
  alternatives; ④ executable/generative → preview/choice; ⑤ ambiguous → never silently guess; ⑥ removal
  → membership only + Undo. Cases: track→album, album→track ("Add all 14 / Select tracks / Cancel"),
  album→playlist, track→playback (now/next/queue), album|review|note→summary (source preview + refresh),
  ambiguous review (surface candidates).
- **F. Quick inspection/editing** — `[visual]` inspect-above-tray / expandable card / side peek / mini
  drawer; normal inspection, **Apple-like Edit mode** (minus = remove-from-bucket ≠ delete source, Done
  exits), reorder (playlist/playback only), removal Undo, explicit "remove from bucket" vs "delete
  source" visual language. Keep it lightweight + a separate path to the full bucket page.
- **G. Bucket settings/creation** — `[visual]` **template-first** (not a raw rule-builder): template
  picker, create, edit, pin-to-Pocket, accepted source types, plain-language conversion description,
  default drop action, display/order, archive/delete safety; advanced rules hidden until needed.

### End-to-end interaction flows (6 source contexts)

Each: `source → Pocket open → drag/drop target → conversion/immediate action → feedback/Undo →
inspect/edit`, with current-code constraints. (Full chains in Appendix A §4.)

1. **Listening history (analysis tab `ImportAnalysis`)** — top-album datum (has album_id) → corner
   control → albums-to-hear / review-research → 1:1 add → inline Undo → inspect bucket card.
   *Constraint: charts are onClick-only (not draggable); drill-down slide-over has zero actions; top-track
   datum is uri-only → needs track→album resolve; time-period is a selector, not an item.*
2. **Review reading (`/review/[slug]`)** — hero album → read-reviews/review-research; or a tracklist
   song → track-collection / playback (now/next/queue) → "added — Undo" toast (tray stays open) →
   inspect + Edit-mode minus (source preserved). *Constraint: track `<li>` has no id/handle; review has
   no DB id (slug); page is prerender + public → drop is 401.*
3. **Album detail** — album → track bucket ("Add all 14 tracks?") / playlist (expand) / playback (set,
   one position prompt) / summary (as source) → 1:N confirm + count → "14 tracks added — Undo" (set-level)
   → inspect: tracklist + reorder + per-item removal Undo. *Constraint: no public album page; render as a
   PROPOSED surface, label "new surface."*
4. **Track detail** — track → album bucket (parent-resolve compact confirm) / track-collection (direct)
   / playback (now/next/queue) / playlist → "○○ album added — Undo" → inspect: reorder + removal + remove
   ≠ delete. *Same "no dedicated page" constraint.*
5. **Analysis page (signal/period)** — analysis-signal (e.g. "2010s" or an artist signal) →
   summary/review-research **as a cited source** (provenance shown) → "source added — Undo" + dropped/
   rule/AI badge → inspect: source list + visible refresh control + "why is this here" + source removal
   (re-summarize, source signal preserved). *Constraint: signal = query result (no persistent id) → needs
   a snapshot/reference design.*
6. **Another bucket as source** — promote/move between buckets (albums-to-hear album → review-research;
   playback-queue → playlist "save queue" bridge); make move-vs-copy explicit + Undo.

### UX risks (12)

Cognitive overload · too many visible buckets · accidental drops · weak metaphor (the `buckit` /
`평론 버킷` / `분석 버킷` / `들을 것` collision) · visual clutter · mobile DnD limits (touch has no
HTML5 drag — `BucketBoard` already falls back to ActionSheet) · **playback ambiguity** (split play from
persist; rule #9 may make it "intent/record" not real playback) · **AI summary trust/provenance** ·
duplicate handling (musical-id normalization, warn at drop) · data-model complexity (polymorphic
membership / conversion / undo / queue / multi-user all net-new) · premature generic-workspace behavior
(stay quick/reversible; deep work on the full page) · membership≠source confusion (file-shelf mental
model). Each carries a mitigation in Appendix A §5.

### Recommended design-exploration scope (what the atlas must render)

Not reducible to 3 polished screens. Minimum: **4 shells × 9 states (≈36 panels)** + **component atlas
A–I** + **6 source-page prototypes** + **6 required interaction sequences** + **bucket-settings flow** +
**responsive/accessibility variants** — all annotated, side by side, at realistic scale (14-track
expansion, 15+ bucket overflow). See Appendix A for the verbatim Claude Design prompt.

---

## Open questions

Each blocks the design atlas direction and/or any future `Steps`. These are **product decisions**, not
inferable from the repo.

1. **Polymorphic membership** — will we add a polymorphic item model (an `item_type` discriminator) so a
   bucket can hold track/review/artist/note/signal/period? No such column/migration/draft exists today.
   *If "no," Pocket Buckit collapses to album-centric.* — **Blocks**: the whole cross-type premise, all
   Steps.
2. **"Playback" semantics** — does the playback bucket perform real Spotify control, or record a
   play-intent/queue snapshot? Rule #9 (no synchronous Spotify on user-facing endpoints) makes the
   latter the safe default; worker playback-scope existence is unknown (`myblog_worker` not audited). —
   **Blocks**: the playback bucket type + its drag feedback.
3. **Relationship to `FEAT-bucket-identity`** — does Pocket Buckit supersede/absorb that RFC (esp.
   Direction C — merging `album_to_listen_items` into the bucket model as one save target)? Direction C
   is currently deferred/undecided. — **Blocks**: bucket-collection unification, "albums-to-hear" target.
4. **Multi-user timeline** — single-owner only (no `user_id` anywhere) or multi-user first
   (`FEAT-multi-user-accounts`, unstarted)? — **Blocks**: ownership scoping, public exposure, the
   auth-asymmetry resolution.
5. **Public collection direction (FEAT-bucket-identity Direction D)** — do public "magazine collections"
   (genre/artist/weekly 모음) imply new bucket kinds or stay name-only curation? — **Blocks**: whether
   bucket `kind` grows.

---

## Steps

**TBD** — intentionally empty. Pending (a) the Design Atlas (Appendix A) so the option space is judged
visually, and (b) answers to the Open Questions (esp. OQ1 polymorphic membership, OQ3 bucket-identity
relationship). When those resolve, this RFC will gain concrete, independently-mergeable Steps
(data-model migration order, contract delta, infra routes, frontend tray) following the standard
cross-repo rollout order in `CLAUDE.md`.

## Decisions log

| Date | Decision | Step |
|------|----------|------|
| 2026-06-23 | Filed as a draft design-exploration RFC (not converged). Documented in English per CLAUDE.md doc-language; brief authored in Korean per the task, translated here. | — |

---

## Appendix A — Pocket Buckit Design Atlas prompt (verbatim, for Claude Design)

> Paste the block below into Claude Design as-is. The point is a **comparison atlas**, not a single
> final mockup.

```text
# Pocket Buckit — Design Atlas (comparison board, NOT a single final mockup)

You are designing the visual + interaction option space for "Pocket Buckit," a persistent global
music-and-criticism workspace layer. Your deliverable is a COMPARISON ATLAS: every significant
alternative rendered SIDE BY SIDE at realistic UI scale, with annotations, so a human can visually
judge directions. DO NOT converge on one polished final screen. DO NOT rely on prose to explain
differences — the differences must be VISIBLE. Label every panel so alternatives are instantly comparable.

## Product context (ground truth)
Pocket Buckit is a persistent global interaction layer over a music-review blog. A user encounters an
album, track, review, listening-history record, artist, research-note, analysis-signal, or time-period
ANYWHERE (review reading page, search, listening-analysis dashboard, artist hub, inside another bucket)
and drops it into a purpose-defined "bucket" without leaving that context.
- Reachable from lower-left AND lower-right controls. Clicking a control opens a HORIZONTAL tray across
  the bottom showing a ROW of actual bucket targets side by side (NOT a vertical menu, popover, sidebar,
  file tree, or folder list). Clicking again closes it. The tray STAYS OPEN after a drop (add several
  consecutively).
- Bucket types (each has a distinct VERB): Inbox/Unsorted (zero-decision default), Albums-to-hear,
  Track-collection, Playlist, Playback-queue, Read-reviews, Summary, Review/Research, Notes/Reference.
- Core invariant: an item in a bucket is a MEMBERSHIP (a connection), never a copy. Removing from a
  bucket removes membership ONLY — it NEVER deletes the source album/track/review/listening-record.
  Every add AND every removal shows an immediate inline Undo.
- Cross-type conversion on drop (the bucket's type drives the transform):
  * track -> album bucket: resolve & add the parent album, compact confirmation first.
  * album -> track bucket: show count, ask "Add all 14 tracks from this album?" with Add all /
    Select tracks / Cancel.
  * album -> playlist: expand into tracks after confirmation.
  * track -> playback bucket: offer Play now / Play next / Add to queue (explicit INSERTION POSITIONS).
  * album / review / note / listening-period -> summary bucket: accumulate as cited SOURCES; explicitly
    show the source list + summary-refresh behavior; NEVER look like unexplained AI magic (show
    provenance: dropped-by-user / rule-matched / AI-suggested + a "why is this here").
  * album or review -> read-reviews: do NOT blindly convert; when the relationship is ambiguous, surface
    related review CANDIDATES instead of guessing.
- The Playback-queue bucket is the ONLY bucket that is transient-by-design; visually distinguish
  "plays-and-forgets" targets from "stores-forever" targets so save-vs-play is never ambiguous. Offer a
  "Save queue to playlist" bridge.
- Duplicate handling uses MUSICAL identity (album/track IDs), not URLs: an album reached two ways is one
  membership; warn/merge AT drop time, not after.

## Visual direction
House style is an editorial music-criticism site (serif editorial headings, restrained palette, album
art as the dominant imagery). Do NOT copy Apple Music / Milanote / Raindrop visual identity — borrow
interaction structure only. The tray must clear page chrome (a fixed header and a reading progress bar
exist) and must keep as much of the source page visible as the chosen density allows.

## MANDATORY DELIVERABLE STRUCTURE (render ALL of it, side by side, annotated)

### 1. Four complete TRAY-SHELL FAMILIES — render all four, never pick one
   F1 Tangible bucket row (literal-but-restrained container metaphor)
   F2 Editorial shelf / collection rail (magazine shelf)
   F3 Modular utility dock / drawer
   F4 Immersive music-workspace tray
   For EACH family, render this full 9-state strip in a labeled row so the four families line up column-
   for-column for direct comparison:
   (a) collapsed control (idle)        (b) open tray (resting, ~6 visible buckets)
   (c) compatible drag (valid target highlighted, insertion line where ordered)
   (d) incompatible drag (invalid targets dimmed / hidden)
   (e) conversion-required drag (e.g. track over an album bucket — shows the pending resolution)
   (f) successful drop WITH inline Undo  (g) quick inspection of one bucket (count, purpose, recent adds)
   (h) Apple-like Edit mode (per-item minus = remove-from-bucket, Done exits; reorder for playlist/queue)
   (i) many-bucket overflow (15+ buckets: show the chosen strategy — horizontal scroll vs paginate vs
       "more" vs search).

### 2. COMPONENT OPTION ATLAS — each option set rendered as a side-by-side comparison grid, labeled
   A. Entry controls: lower-left/right opening the SAME tray vs FILTERED views (pinned vs recent/
      contextual) vs single control; icon-only vs icon+text; compact floating button vs edge-attached
      tab; states idle/hover/open(active)/drag-active; bucket-count badge.
   B. Tray density: how much source page stays visible (short bar vs tall sheet vs translucent),
      pinned vs recent vs contextual ordering.
   C. Bucket target CARD treatments (5, side by side): literal-restrained container / minimal editorial
      / album-art-driven / icon+action-driven / dense utility. Each card MUST communicate: name,
      purpose/verb, accepted-type-or-compatible-drop-state (live vs the currently dragged item:
      compatible / convert / incompatible), item count, and the drop outcome (add / convert / play /
      queue / summarize / write). Also render: empty bucket, single-cover, stacked-grid, pinned marker,
      "transient-by-design" (playback) marker.
   D. Drag feedback states (all, side by side): compatible direct drop, incompatible, conversion-
      required, one-to-many expansion-required (with a "+14" semantic count badge), executable-action,
      duplicate (already present), processing, success-add, Undo, error. Include the insertion line for
      ordered buckets.
   E. Confirmation patterns (4, compared against each case): small inline confirm above tray / compact
      popover anchored to the target bucket / expanded bottom sheet / focused dialog (higher-risk only).
      Map them to: track->album, album->track ("Add all 14 / Select tracks / Cancel"), album->playlist,
      track->playback (now/next/queue), album|review|note->summary (source preview + refresh), ambiguous
      review relationship (candidate surfacing).
   F. Quick-inspection patterns (4, side by side): inspect-above-tray panel / expandable tray card /
      side peek / mini drawer. Each with: normal inspection, Edit mode, minus badges, Done, reordering,
      removal Undo, and an explicit visual distinction between "remove from bucket" and "delete source."
      Keep Pocket Buckit lightweight — show the separate path to open the FULL bucket page for deep work.
   G. Bucket settings & creation (template-FIRST, not a raw rule-builder): template picker gallery,
      create bucket, edit bucket, pin-to-Pocket, accepted source types, a simple plain-language
      conversion-behavior description, default drop action, display/order settings, archive/delete
      safety. Show how ADVANCED rules stay hidden until needed (progressive disclosure).
   H. Mobile alternatives (render INSIDE this atlas, beside each desktop component): the touch entry
      control, the long-press lift + flock variant, the card/confirmation/quick-inspection at phone
      width, and the non-drag "Add to…" overflow action that enumerates live bucket targets with their
      conversion verbs. (Full responsive treatment also appears in section 5; the atlas must still carry
      the side-by-side desktop-vs-mobile component comparison here.)
   I. Keyboard focus + accessibility states (render INSIDE this atlas, beside each component): visible
      focus rings on the entry control, bucket cards, tray items, and confirmations; the keyboard-drag
      focus path through the tray (lift / choose target / drop / cancel); and the reduced-motion variant
      of drag feedback. (Cross-references section 5, but the per-component focus/accessibility states
      belong in the atlas grid so no component is shown without them.)

### 3. SOURCE-PAGE PROTOTYPES (render the tray IN CONTEXT on each; the item that gets dragged is real)
   - Listening-history / analysis dashboard (charts, clock heatmap, retrospective — drag a top-album,
     a top-track, and a time-period; note that a time-period becomes a droppable item here)
   - Review reading page (drag the hero album AND a track from the tracklist)
   - Album page (album -> track/playlist/playback/summary). NOTE: a standalone album page does not exist
     yet in the product — render it as a PROPOSED surface and label it "new surface."
   - Track page (track -> album/track-collection/playback). Same "new surface" note.
   - Analysis page (analysis-signal / artist signal -> summary/review-research as a cited source)
   - Another bucket as source (move/promote an item between buckets; playback-queue -> playlist bridge)

### 4. REQUIRED INTERACTION SEQUENCES (storyboard each as an annotated left-to-right strip)
   - track -> album conversion (parent resolve + compact confirm + Undo)
   - album -> tracks / playlist expansion with the "Add all 14 tracks?" confirmation (+ Select tracks)
   - playback choices (Play now / Play next / Add to queue) and the transient-vs-stored distinction
   - summary-bucket source accumulation: source preview list, provenance badges, and the generated
     result with a visible refresh control
   - duplicate handling at drop time (musical-identity match -> warn/merge, originals untouched)
   - Undo after an ADD and Undo after a REMOVAL (membership-only, source survives)

### 5. RESPONSIVE / ACCESSIBILITY VARIANTS (render as paired comparisons)
   - Desktop drag-and-drop (pointer) vs Mobile long-press lift + flock + count badge
   - Mobile non-drag fallback: an explicit "Add to…" overflow action that ENUMERATES live bucket targets
     WITH their conversion verbs (Add to Playlist / Queue next / Add 14 tracks / Add to Summary) — this
     is a peer to drag, not an afterthought (WCAG 2.5.7).
   - Keyboard navigation model: focus a draggable item, Enter/Space to lift, Tab/arrow to choose a
     bucket target (insertion position for ordered buckets), Enter to drop, Esc to cancel — show focus
     order through the tray.
   - Visible focus states on controls, bucket cards, tray items, confirmations.
   - Reduced-motion-friendly behavior: show the no-flocking / instant-reposition variant next to the
     animated one.

## OUTPUT FORMAT REQUIREMENTS
- Organize as labeled comparison BOARDS, one board per matrix dimension above. Within each board, place
  alternatives in a row/grid so they are directly comparable; caption every panel with its option name
  and the one-line tradeoff it represents.
- The four tray-shell families must appear together on a master comparison board (column per family,
  row per state) so the user can scan one state across all four shells at once.
- Annotate states (compatible/incompatible/convert/duplicate/processing/success/undo/error) with small
  labels ON the panels.
- Use realistic music data (album covers, real-length tracklists ~12–16 tracks, Korean + English
  titles) so density and overflow are honest. Do NOT idealize counts — show a 15+ bucket overflow case
  and a 14-track expansion case explicitly.
- This is an ATLAS for comparison and decision-making. Do not produce a single hero screen, do not
  declare a winner, and do not omit any of the four shell families or any matrix dimension above.
```

## Appendix B — reference source links

- **Apple Music**: support.apple.com/en-us/109336 · /guide/iphone create-edit-delete-playlists ·
  musconv add-to-library-vs-playlist · macrumors add-songs-multiple-playlists · idownloadblog 2021 swiping
- **Milanote**: help.milanote.com (images / moving-content-between-boards / web-clipper) · g2 / trustpilot reviews
- **Raindrop**: help.raindrop.io (collections / duplicates / ui) · canny warn-when-adding-duplicate
- **Music queue**: support.spotify.com play-queue · 9to5google youtube-music-save-queue-playlist ·
  medium mental-models-for-queues · community.spotify queue-disappears
- **Read-later**: docs.readwise.io/reader saving-content · zapier instapaper-vs-pocket ·
  bulkmark why-twitter-bookmarks-pile-up · news.itsfoss omnivore
- **Boards**: help.are.na (connections / channels / blocks) · help.pinterest save-pins-browser-button ·
  mymind how-does-it-work · en.eagle.cool smart-folders
- **DnD shelves**: dropoverapp.com · eternalstorms.at/yoink · support.apple.com/guide/ipad drag-and-drop ·
  react-aria.adobe.com/blog/drag-and-drop · w3.org WCAG22 dragging-movements (2.5.7) ·
  medium salesforce-ux accessible-drag-and-drop
