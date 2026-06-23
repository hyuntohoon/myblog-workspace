# FEAT-pocket-buckit: Pocket Buckit — the canonical Buckit product + interaction definition (design exploration)

- **Status**: draft
- **Owner**: TBD
- **Created**: 2026-06-23
- **Plan row**: `plan.md` → FEAT-pocket-buckit
- **Related**: `docs/rfcs/FEAT-bucket-identity.md` (now reframed as the **compatibility / migration / integration** track — existing review buckets + `들을 것` + public collections — that aligns to *this* model), `docs/rfcs/FEAT-multi-user-accounts.md` (deferred multi-user scope), `docs/rfcs/FEAT-liked-tracks-workbench.md` (the `분석 버킷` track→album promote path)

> **This RFC is the latest, canonical product + interaction definition for Buckit.** It is still a
> **draft** and still requires a visual **Pocket Buckit Design Atlas** (Appendix A) before any
> implementation. Several product questions are now **decided** (see *Canonical product direction*); what
> remains open is split into **Design-Atlas decisions** (final UI form) and **technical-validation
> decisions** (how to build it) — see *Open questions*. `Steps` stay TBD until the atlas exists and the
> technical-validation items are resolved. This document does not implement code, change schemas, create
> migrations, change APIs, or convert into an execution plan.

---

## Goal

A persistent **global interaction layer** ("Pocket Buckit") where a user can encounter an album, track,
review, listening-history record, artist, research-note, analysis-signal, or time-period **anywhere** in
the product and place it into a **purpose-defined bucket** without leaving that context — collect, move,
transform, play, summarize, organize, and prepare music/review material, then connect it to a review or
published writing. Reachable from a **persistent Pocket control** (one toggle, **or** two lower-left/right
controls — the count is compared in the Design Atlas) that opens a **horizontal bottom tray** showing a
row of visible, independently-droppable **leaf-bucket** targets, with **non-destructive membership**,
**source-preserving cross-type conversion** on drop, and per-item **bucket-local Undo**. Pocket Buckit is
a horizontal quick-access **projection of the full bucket tree ("My Buckit")**, not a replacement for it.

## Non-goals

- This RFC does **not** select the entry-control model, tray-shell family, card treatment, or
  confirmation pattern — that is what the Design Atlas (Appendix A) exists to compare.
- It does **not** introduce any schema, migration, contract, or infra change. (None are written here.)
- It does **not** make Pocket Buckit a full editor, and the tray is **not** a vertical folder explorer —
  the tray stays quick, reversible, understandable; deep work happens on the full bucket page.
- A **standalone Notes/Reference collection is not a v1 core capability** — deferred/optional future scope
  (existing album-review notes are preserved as an album-writing aid; see *Notes scope*).
- v1 is a **single-owner workspace**; multi-user accounts and public collections are **deferred**
  (required later, **not cancelled**, and **not** an atlas blocker — see *Canonical product direction* D5).

---

## Canonical product direction (decided)

These are settled product decisions. They are **not** Open Questions. They constrain the Design Atlas and
any later Steps; only their *technical realization* stays open (see *Open questions → Technical
validation*).

- **D1 — Pocket Buckit is the canonical top-level definition.** Pocket Buckit defines the **future bucket
  model** for Buckit. `FEAT-bucket-identity` remains relevant but is **reframed as a compatibility /
  migration / integration RFC** for the *existing* review buckets, the `들을 것` (to-listen) data, and
  later public-collection work; it **aligns to** this model. The earlier "does Pocket Buckit absorb
  FEAT-bucket-identity?" question is **answered: yes** — legacy bucket-identity work conforms to Pocket
  Buckit, and its Direction C (one shelf object) is subsumed by D2. Only the *technical migration* is open.
- **D2 — Generalized membership (decided).** *Terminology:* "membership" here means the relationship **an
  item belongs to a bucket** — it does **not** mean paid membership, account subscription, or multi-user
  membership. Today the repo has an **album-only** relationship via `review_bucket_items`. Buckit will use
  a **generalized bucket-item relationship** that can support albums, tracks, reviews, playback entries,
  and snapshot items. A bucket item is a **non-destructive relationship to a source object or a snapshot,
  not a copy of the source.** *Whether* to add generalized membership is **decided (yes)**; *how* is a
  technical-validation decision (migration/coexistence with `review_bucket_items`, preserving the
  review-pipeline fields `status`/`research_selected`/`post_id`/existing album-review notes, one new table
  vs a staged migration, and snapshot representation).
- **D3 — Playback aims for real playback.** The Playback bucket aims for **actual in-product playback**
  (not merely intent-recording or a queue snapshot). Provider order: **evaluate Spotify first; if Spotify
  constraints / platform / licensing limits make it insufficient, evaluate YouTube as a fallback
  candidate.** Provider behavior is **provisional** until technical validation (see *Open questions*).
- **D4 — Summary is automatic + asynchronous.** Dropping material into a Summary bucket **auto-starts**
  an asynchronous summary, shows the bucket as **processing**, and signals **completion** with a visible
  indicator (bell/badge) on the bucket and the Pocket tray. Manual regenerate may exist later, but the
  default is *drop → processing → completion notification → inspect* (not manual-refresh-first).
- **D5 — Multi-user later, single-owner now.** Multi-user is a **required future direction**, but
  **deferred** — v1 is designed and validated as a **single-owner** workspace. It must not block the
  Design Atlas or the v1 model. Future ownership scoping must remain **possible**: do not introduce new
  irreversible singleton assumptions. (Not claiming multi-user is solved.)
- **D6 — Entry-control count is OPEN for the atlas.** The user is open to one **or** two persistent
  controls. The Design Atlas compares: (1) one persistent toggle; (2) two lower-left/right controls
  opening the **same** tray; (3) two controls opening **filtered views** of the same bucket tree. Shared
  fixed requirements: clicking the active originating control **closes** the tray; the tray **stays open
  after a drop**; the tray is **horizontal + bottom-anchored**; multiple bucket targets stay individually
  visible and droppable; **no** direction may degrade into a vertical menu, sidebar, command palette, or
  generic folder list.
- **D7 — The tree is canonical; Pocket is its projection.** "My Buckit" is a **tree**; Pocket Buckit is a
  horizontal **quick-access projection** of it (see *Tree model*).
- **D8 — Settled behaviors** for duplicates, ordering, confirmation, and deletion safety (see *Decided
  behaviors*).

---

## Current state (repository audit — exact paths)

### The reframing: "bucket" already exists and must align to this model

Today the codebase's "bucket" is exactly **one table**, `review_buckets` — an **album-only**,
**single-user** (no `user_id`), **`/profile`-scoped** review-pipeline kanban column
(`myblog_shared_db/src/myblog_shared_db/models.py:354-472`). So Pocket Buckit is the **union of two
net-new efforts**: (1) a global interaction layer (none exists — the bucket UI lives only in
`myblog_front/src/components/member/BucketBoard.tsx`), and (2) a data-model generalization (album-only
membership → generalized membership + cross-type conversion + per-item undo + a playback path). It
overlaps the in-flight `FEAT-bucket-identity` RFC (review buckets + `album_to_listen_items` "들을 것" +
public collections); **per the Canonical product direction (D1/D2), this RFC now defines the future
bucket model and that work aligns to it** — only the *technical migration/coexistence* remains open.

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
| Membership | `review_bucket_items`: **album_id FK NOT NULL** + UNIQUE(bucket_id, album_id). note, status ∈ {candidate,drafting,published}, post_id, research_selected, prep_tonight. **No item_type/track_id column → generalized membership is net-new.** | `models.py:422-472`; `migrations/V6,V22` |
| Second album queue | `album_to_listen_items` ("들을 것"): album_id UNIQUE, position, note. No bucket_id, no user_id. Disjoint from `review_buckets`. | `models.py:484-502`; `migrations/V8` |
| Membership≠source split | **Only one place**: `spotify_library_albums.in_bucket` bool (bespoke to Spotify sync). Not a general primitive. | `models.py:515-546`; `migrations/V15` |
| Playback/queue | **None.** `now-playing` is read-only worker telemetry; no queue-membership table; no in-product player. | `models.py:589-641` |
| Tree | `review_buckets.parent_id` self-FK already gives a nested tree; `PUT /api/buckets/{id}/move` has **server-side cycle prevention** (can't move a node into itself/its descendant). | `models.py:354-419`; `buckets.py:398-417` |

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
  reset listeners. **No drag on touch** → `ActionSheet` fallback. Already distinguishes album **copy**
  (from a read-only source) vs **move** (a real item) — a seed for the internal-move/external-add split.
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
401/403. The model is single-owner (no `user_id`); per D5 **v1 assumes a single-owner workspace** and
treats multi-user scoping (`FEAT-multi-user-accounts.md`, unstarted) as **deferred, not a v1
prerequisite**. The public-page **sign-in handoff** for a drop is a technical-validation item. Any new
Pocket Buckit POST/PUT/DELETE **404s until added to `infra/apigateway.tf` + applied** (memory
`reference-apigateway-post-route-required`).

### Concrete conflicts between the existing model and the (now decided) direction

1. **Membership is album-only** — generalized membership is net-new (decided in D2; migration is the open
   part). (`models.py:422-472`, `schemas.py:161-163`, front `DndItem.kind:'album'|'bucket'`
   `BucketBoard.tsx:47`)
2. **No bucket "types"** — none of albums-to-hear / track-collection / playlist / playback-queue /
   read-reviews / summary exist as types. `kind` has 2 values. playlist/queue/summary have no backend.
3. **Cross-type conversion unimplemented** — the reads (track→album parent, album→tracks, artist→albums)
   all exist on the music API, but the bucket write accepts only `album_id`. Generalized membership (D2)
   is what lets a track collection / playlist of tracks be persisted.
4. **No per-item Undo** — hard cascade DELETE; no soft-delete/tombstone (and deletion should default to
   **archive**, D8). (Membership≠source split exists only as the bespoke `spotify_library_albums.in_bucket`.)
5. **No global layer** — bucket UI is one `/profile` tab; no persistent bottom tray / corner control.
6. **No playback/queue backend / no player** + **hard rule #9** (no synchronous Spotify calls on
   user-facing endpoints) → real in-product playback (D3) is net-new and must be async/architecture-aware.
7. **review/note/artist/period are not identifiable/storable today** — review = slug (no DB id), note =
   album-keyed attribute, period = query parameter (→ snapshot representation, a technical-validation item).
8. **Two album collections coexist** (`review_bucket_items` vs `album_to_listen_items`) — D1/D2 decide one
   generalized model; reconciling the two is the migration item, not an open product question.

---

## Design exploration (behaviors + option matrix + flows + risks)

> Full verbatim Claude Design prompt: Appendix A. This section is the condensed English record. The
> *product direction* is decided (above); the *final UI form* is what the atlas compares.

### Reference-product analysis (borrow / avoid / adapt)

Seven products analyzed; transferable vs non-transferable separated.

- **Strong transfer**: Apple Music (purpose-named destinations with stable verbs; Play Next = an
  insertion *position*; non-destructive removal); Are.na (item-as-connection, remove = membership only);
  Raindrop / read-later (save-first-organize-later — but we do **not** adopt an Inbox-first default;
  intentional placement into purpose-defined buckets stays the core identity); Pinterest (top targets
  first + search + inline create); Yoink/Dropover (edge shelf + count badge + flocking); **React Aria /
  WCAG 2.5.7** (non-drag "Add to…" + keyboard DnD — legally required, not optional).
- **Anti-patterns (avoid)**: Spotify (single overloaded "Add"; a queue that silently churns/evaporates →
  save-vs-play ambiguity); Milanote/Kosmik (pure spatial canvas → disorder at scale); **Mymind**
  (rationale-free AI auto-organization → destroys editorial trust → provenance is mandatory).
- **Adapt for music-and-criticism**: the **bucket** (not the item) decides the transform; make album→track
  expansion **explicit/confirmable/undoable** and **order-preserving** (Apple expands silently);
  distinguish a **queue** (ordered, may allow duplicates, more session-like) from a **stored** collection;
  every Summary membership carries a **provenance badge**; the YouTube-Music "Save queue to playlist"
  bridge is a useful queue→stored handoff.

### Tree model ("My Buckit") and Pocket as a projection (decided — D7)

- The canonical structure is a **tree** ("My Buckit"). The repo already supports it (`parent_id`).
- **Parent nodes are folders / organizational nodes.** They do **not** directly receive dropped items by
  default. **Leaf buckets** are the actionable destinations that receive items and perform bucket-specific
  behavior.
- **Moving a bucket node** inside My Buckit moves the node **and its child subtree** to a new parent.
- **Bucket-node duplication is explicit only** — never the default drag behavior.
- **Invalid tree moves are prevented** (a node into itself or one of its descendants — server-side cycle
  prevention already exists, `buckets.py:398-417`).
- **Pocket Buckit is a horizontal quick-access projection of the tree, not a replacement:** it shows
  **pinned or contextually-selected leaf buckets** in the tray, a **compact path** such as `Review / Read
  reviews`, and allows deeper tree navigation **only when needed**. It must **not** become a vertical
  folder explorer.

### Membership semantics: move, add, and transform (decided — directive of this RFC)

**A. Internal: Buckit → Buckit, same object type.** When an item is dragged from one bucket to another
within My Buckit:
- default behavior is **MOVE** — remove membership from the source bucket, create membership in the
  destination bucket;
- do **not** delete or alter the source album/track/review/listening-record or any original object;
- bucket-local feedback: **`Moved · Undo`**;
- provide an explicit **Copy** action only when the user intentionally needs the item in both buckets.

**B. External source → Buckit.** From an external context (review pages, listening history, recent plays,
liked tracks, album/track detail, search, analysis, artist pages, public reading pages), default behavior
is **ADD / COPY AS A MEMBERSHIP**; the source context is unchanged. Bucket-local feedback: **`Added ·
Undo`** (e.g. `Album added · Undo`). Examples: an album from listening history → an album bucket; a review
→ a read-reviews bucket; a track → a playlist bucket.

**C. Cross-type conversion** (item type ≠ bucket type): **preserve the original item and original
membership**; add the **transformed result** to the destination bucket only after the appropriate
confirmation; **never silently remove the original** because a conversion happened.
- track → album bucket: resolve parent album, compact confirmation, then add the album;
- album → track bucket: mandatory confirmation showing the count — **Add all / Select tracks / Cancel**;
- album → playlist: mandatory confirmation before expansion (**preserves the original album track order**);
- review → album bucket: show the reviewed album only when the relationship is unambiguous; otherwise
  surface candidates;
- album → read-reviews: surface related review candidates rather than guessing.

**D. Feedback language** (bucket-local, anchored to the affected target or quick-inspection surface; a
global toast may be **secondary** status feedback only): `Moved · Undo`, `Added · Undo`, `Album added ·
Undo`, `14 tracks added · Undo`, `Removed from this bucket · Undo`.

### Notes scope (narrowed — v1)

Existing notes are primarily **album-review records** used when writing or researching an album.
Therefore: preserve existing album/review note semantics; do **not** treat notes as an important
standalone bucket member type in v1; do **not** require per-bucket "why I put this here" notes; do **not**
make a Notes bucket a core template in the primary Pocket tray; mark a standalone notes/reference
collection as **deferred / optional future scope only**. Keep the product focused on collecting, moving,
transforming, playing, summarizing, and preparing music/review material.

### Listening-history vs snapshot (decided — directive of this RFC)

- **Ordinary item from listening history.** Adding an album from listening history into a normal album /
  review / playlist / playback bucket adds the **album reference only**; do **not** auto-copy play count,
  listening time, date range, or analysis statistics. Current listening data may be viewed later through
  the source relation, but it is **not** preserved as part of the membership.
- **Snapshot bucket.** Adding a **period / analysis-signal / trend / aggregated insight** to a dedicated
  **snapshot / summary-oriented** bucket **preserves the contemporaneous period, filters, values, and
  source context** — a *snapshot*, because the meaning would otherwise drift as listening data evolves.
  An explicit future **"refresh with current data"** action may exist, but it **never silently overwrites**
  the historical snapshot.

### Playback (decided goal — D3)

The Playback bucket aims for **actual in-product playback** (Play now / Play next / Add to queue — explicit
insertion positions). Preferred provider order: **Spotify first; YouTube as a fallback candidate** if
Spotify constraints make it insufficient. The Design Atlas shows playback as a **real intended user
action** while **clearly labeling provider behavior as provisional** until technical validation. A queue
is more session-like than a stored playlist (a "Save queue to playlist" bridge converts a session into a
stored collection). Unresolved technical/product items (see *Open questions*): Spotify playback feasibility
/ eligibility; whether a YouTube fallback is necessary/acceptable; Spotify→YouTube matching policy;
provider attribution + user expectations; queue persistence/recovery; legal/terms/platform-policy review;
asynchronous architecture constraints (rule #9).

### Summary bucket (decided — D4)

When material is dropped into a Summary bucket: add the source material; **begin a summary update
automatically**; show the bucket as **processing**; on completion show a **visible indicator (bell/badge)**
on the bucket and the Pocket tray; opening the bucket or quick-inspection reveals the new summary; preserve
**visible source provenance** and distinguish **user-dropped / rule-matched / AI-suggested** source where
applicable. A manual regenerate may exist later, but the **default** interaction is *drop → processing →
completion notification → inspect* — **not** a manual "Refresh summary" as the primary v1 behavior.

### Decided behaviors (D8)

- **Duplicate policy is bucket-type-specific**: album / review / research collections → **no duplicate
  membership**; playlist / playback queue → **duplicates may be allowed**.
- **Ordering is bucket-type-specific**: collection buckets → **recent-add** default; playlist / playback →
  **manual ordered list**; review / research → manual order **and pinning may exist**.
- **album → track expansion preserves the original album track order.**
- **Direct same-type internal moves do not require confirmation** — use **immediate MOVE + Undo**.
- **Cross-type conversion and one-to-many expansion require confirmation.**
- **Bucket deletion defaults to archive** (recoverable).
- **Archiving/deleting a parent bucket requires the user to decide how child buckets are handled.**
- **No Inbox-first default**: items are placed intentionally into purpose-defined buckets; an
  Inbox/Unsorted bucket is at most **one optional template**, never the default or first destination.

### Option matrix — `[visual]` = must be rendered side by side in the atlas

- **A. Entry controls** — `[visual]` **three options** (D6 — count is open): (1) **one** persistent
  Pocket toggle; (2) **two** lower-left/right controls opening the **same** tray; (3) **two** controls
  opening **filtered views** of the same bucket tree. Shared fixed requirements: the active originating
  control **closes** the tray; the tray **stays open after a drop**; horizontal + bottom-anchored;
  multiple targets individually visible + droppable; never a vertical menu / sidebar / command palette /
  folder list. Treatments: icon-only vs icon+text; floating button vs edge tab; states
  idle/hover/open/**drag-active**; bucket-count badge.
- **B. Bottom tray shell** — `[visual]` **four families**: tangible bucket row / editorial shelf / modular
  utility dock / immersive music-workspace tray. **Invariant across all four**: a horizontal bottom tray
  of multiple individually-visible, independently-droppable **leaf-bucket targets** that read as
  destination containers (not generic commands) and show a **compact tree path** — they must **not**
  degrade into a toolbar / command palette / sidebar / vertical list / folder menu. Compared across:
  compact-closed, opened, drag-active, many-bucket overflow, pinned vs recent vs contextual ordering, how
  much source page stays visible, desktop, mobile.
- **C. Target card representation** — `[visual]` 5 variants: literal-restrained container / minimal
  editorial / album-art-driven / icon+action-driven / dense utility. Each must communicate: name, compact
  path, purpose/verb, accepted-type-or-compatible-drop-state (live vs the dragged item), item count, and
  the outcome (add / move / convert / play / queue / summarize). Plus: empty, single-cover, stacked-grid,
  pinned, processing (summary), and a "queue" marker.
- **D. Drag feedback** — `[visual]` compatible (highlighted) / conversion-required (visibly explains the
  pending transform) / **incompatible (stays in the same position, muted/disabled with a concise reason —
  never hidden; the tray must not reflow/reshuffle during a drag)** / one-to-many expansion (`+14` count
  badge) / executable / **duplicate** (per bucket-type policy) / processing / success / **bucket-local
  Undo on the affected target** / error; insertion line for ordered (playlist/playback) buckets.
- **E. Confirmation patterns** — `[visual]` inline-above-tray / popover anchored to target / expanded
  bottom sheet / focused dialog (high-risk only), mapped to risk: ① same-type internal move →
  **immediate move + Undo, no confirm**; ② external 1:1 add → instant + Undo; ③ 1:1 conversion → compact
  confirm; ④ 1:N expansion → **mandatory** confirm + count + alternatives; ⑤ ambiguous → never silently
  guess; ⑥ removal → membership only + bucket-local Undo. Cases: track→album, album→track (Add all 14 /
  Select tracks / Cancel), album→playlist (order-preserving), track→playback (now/next/queue),
  album|review|period→summary (auto-processing + provenance), ambiguous review (surface candidates).
- **F. Quick inspection/editing** — `[visual]` inspect-above-tray / expandable card / side peek / mini
  drawer; normal inspection, **Apple-like Edit mode** (minus = remove-from-bucket ≠ delete source, Done
  exits), reorder (playlist/playback; review/research pinning), removal Undo, explicit "remove from
  bucket" vs "delete source," and the path to the **full bucket page**. Lightweight, not a giant editor.
- **G. Bucket settings/creation** — `[visual]` **template-first**: template picker (Albums-to-hear /
  Track-collection / Playlist / Playback / Read-reviews / Summary / Review-Research — **Notes/Reference is
  not a core default template**), create, edit, pin-to-Pocket, accepted source types, plain-language
  conversion description, default drop action, display/order, **archive-by-default deletion** + **parent
  child-handling prompt**; advanced rules hidden until needed.

### End-to-end interaction flows (6 source contexts)

Each: `source → Pocket open → drop target → move/add/convert → bucket-local feedback/Undo →
inspect/edit`, with current-code constraints.

1. **Listening history (analysis tab `ImportAnalysis`)** — top-album datum (has album_id) → Pocket
   control → albums-to-hear / review-research → **external ADD** (album reference only; **no stats
   copied**) → `Album added · Undo` on the target → inspect bucket card. *Constraint: charts are
   onClick-only (not draggable); drill-down slide-over has zero actions; top-track datum is uri-only →
   needs track→album resolve; time-period is a selector, not yet a draggable item.*
2. **Review reading (`/review/[slug]`)** — hero album → read-reviews/review-research (external ADD); or a
   tracklist song → track-collection / playback (now/next/queue) → `Added · Undo` on the target bucket
   (tray stays open) → inspect + Edit-mode minus (source preserved). *Constraint: track `<li>` has no
   id/handle; review has no DB id (slug); page is prerender + public → drop needs a sign-in handoff.*
3. **Album detail** — album → track bucket (Add all 14 tracks? / Select tracks / Cancel; **order
   preserved**) / playlist (expand) / playback (set, one position prompt) / summary (auto-processing) →
   1:N confirm + count → `14 tracks added · Undo` on the target (set-level) → inspect: tracklist + reorder
   + per-item removal Undo. *Constraint: no public album page; render as a PROPOSED "new surface."*
4. **Track detail** — track → album bucket (parent-resolve compact confirm) / track-collection (direct) /
   playback (now/next/queue) / playlist → `Album added · Undo` on the target → inspect: reorder + removal
   + remove ≠ delete. *Same "no dedicated page" constraint.*
5. **Analysis page (signal/period)** — analysis-signal (e.g. "2010s" or an artist signal) →
   summary/snapshot bucket **as a preserved snapshot** (period+filters+values frozen) + auto-processing →
   `Source added · Undo` + dropped/rule/AI badge → on completion a **bell/badge** → inspect: source list +
   provenance + "why is this here" + optional explicit "refresh with current data" (never silent). *Constraint:
   signal = query result (no persistent id) → snapshot storage is a technical-validation item.*
6. **Another bucket as source (internal)** — drag a leaf item from one bucket to another within My Buckit
   → **default MOVE** (`Moved · Undo`); explicit **Copy** only on intent; or a node move (moves the
   subtree, cycle-prevented); playback-queue → playlist "save queue" bridge. *Source object never altered.*

### UX risks (12)

Cognitive overload · too many visible buckets · accidental drops · weak metaphor (the `buckit` /
`평론 버킷` / `분석 버킷` / `들을 것` collision) · visual clutter · mobile DnD limits (touch has no
HTML5 drag — `BucketBoard` already falls back to ActionSheet) · **move-vs-add confusion** (internal MOVE
vs external ADD must read differently) · **AI summary trust/provenance** (auto-processing must show
provenance + completion, never feel like magic) · duplicate handling (bucket-type-specific; musical-id) ·
data-model complexity (generalized membership / conversion / undo / playback / snapshots all net-new) ·
**playback provider risk** (Spotify feasibility / YouTube fallback / matching / policy — provider marked
provisional) · premature generic-workspace / vertical-folder-explorer behavior (the tray is a projection,
not the tree). Mitigations are embedded in the relevant behavior sections + Appendix A.

### Recommended design-exploration scope (what the atlas must render)

Not reducible to 3 polished screens, and not one giant single-canvas collage. The atlas is packaged as
**four numbered comparison boards** (consistent data + scale): **Board 1** — Pocket controls (the **three**
entry-control options) + the 4 tray-shell families × 9 states + tree-path + density; **Board 2** — target
cards + drag feedback + **internal-move vs external-add** + source-preserving conversions + confirmations +
duplicates + bucket-local Undo; **Board 3** — quick inspection + Apple-like Edit mode + membership removal
+ reordering + full-bucket handoff + **archive-safe deletion (incl. parent child-handling)**; **Board 4** —
settings/creation + the 6 source flows (incl. **ordinary-add vs snapshot-drop** and **summary
auto-processing + bell/badge** and **playback with provisional provider**) + mobile + keyboard +
reduced-motion. End with a **coverage checklist** mapping every option/state to its board + panel.

---

## Open questions

The product direction is decided (above). What remains is grouped into two kinds. **Neither group blocks
the Design Atlas from starting** (the atlas itself resolves the first group); the second is technical
validation that precedes implementation Steps.

### Design-Atlas decisions (resolved by rendering + choosing)

1. Final Pocket **entry-control model** (one toggle vs two same-tray vs two filtered-views).
2. Final **horizontal tray-shell family**.
3. **Tray ordering and overflow** behavior (pinned vs recent vs contextual; scroll vs paginate vs search).
4. **Tree-navigation depth** reachable inside Pocket (how deep before handing off to the full page).
5. **Quick-inspection / edit** surface form.

### Technical-validation decisions (precede Steps)

6. **Generalized-membership migration** from album-only `review_bucket_items` — one new table vs staged
   migration; preserving review-pipeline fields (`status`, `research_selected`, `post_id`, existing
   album-review notes); coexistence with / absorption of `album_to_listen_items` ("들을 것").
7. **Snapshot storage representation** (period/signal/trend frozen values + source context).
8. **Spotify playback feasibility / eligibility** constraints.
9. **YouTube fallback** necessity/acceptability + **Spotify→YouTube matching** policy + provider
   attribution.
10. **Queue persistence / recovery.**
11. **Public-page authentication / sign-in handoff** for a drop from an unauthenticated reading page.
12. **Future multi-user ownership migration** strategy (keep it possible; no new irreversible singletons).

---

## Steps

**TBD** — intentionally empty. Pending (a) the **Design Atlas** (Appendix A) so the UI form is chosen, and
(b) the **technical-validation decisions** above (esp. #6 generalized-membership migration, #8/#9 playback
provider). When those resolve, this RFC will gain concrete, independently-mergeable Steps (data-model
migration order, contract delta, infra routes, frontend tray) following the standard cross-repo rollout
order in `CLAUDE.md`.

## Decisions log

| Date | Decision | Step |
|------|----------|------|
| 2026-06-23 | Filed as a draft design-exploration RFC. Documented in English per CLAUDE.md doc-language; brief authored in Korean per the task, translated here. | — |
| 2026-06-23 | Corrections v2: bucket-local Undo (not a global toast); incompatible drop targets stay visible/stable during a drag; bucket-target invariant across all tray shells; Design Atlas repackaged into four numbered boards + a coverage checklist. | — |
| 2026-06-23 | Corrections v3 (this version is canonical): Pocket Buckit is the canonical top-level product/interaction definition; FEAT-bucket-identity reframed as its compatibility/migration/integration track (absorb-question answered: yes). Generalized **membership** decided (item↔bucket relationship, not a copy; "membership" ≠ paid/multi-user). Tree ("My Buckit") canonical; Pocket = its projection (parent=folders, leaf=actionable). Move/add/transform semantics fixed (internal MOVE default + Undo; external ADD; source-preserving conversion). Notes narrowed (standalone Notes/Reference deferred). Ordinary listening-add ≠ snapshot (no auto stat-copy; snapshots frozen). **Playback aims for real playback** (Spotify→YouTube, provider provisional). **Summary** auto-async + bell/badge (not manual-refresh-first). Multi-user deferred (v1 single-owner; not an atlas blocker; keep scoping possible). **Entry-control count re-opened** (1 or 2 controls; single-control comparison restored; dual-non-negotiable wording removed). Decided behaviors fixed (duplicate/ordering by type; album→track order preserved; same-type move no-confirm; conversion/expansion confirm; delete→archive; parent child-handling). Open Questions split into Design-Atlas vs Technical-validation. | — |

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
Pocket Buckit is a persistent global interaction layer over a music-review blog, and a horizontal
quick-access PROJECTION of a bucket TREE called "My Buckit". A user encounters an album, track, review,
listening-history record, artist, research-note, analysis-signal, or time-period ANYWHERE (review reading
page, search, listening-analysis dashboard, artist hub, inside another bucket) and places it into a
purpose-defined bucket without leaving that context.

- Entry control COUNT is an OPEN comparison — render all THREE: (1) ONE persistent Pocket toggle; (2) TWO
  lower-left/right controls opening the SAME tray; (3) TWO controls opening FILTERED views of the same
  bucket tree. Shared FIXED requirements for every option: clicking the active originating control CLOSES
  the tray; the tray STAYS OPEN after a drop (add several consecutively); the tray is HORIZONTAL and
  bottom-anchored; multiple bucket targets stay individually visible and droppable; NO option may degrade
  into a vertical menu, sidebar, command palette, or generic folder list.
- TREE model: "My Buckit" is a tree. PARENT nodes are folders / organizational nodes and do NOT receive
  dropped items by default. LEAF buckets are the actionable drop targets that perform bucket-specific
  behavior. The Pocket tray shows pinned/contextual LEAF buckets + a compact path (e.g. "Review / Read
  reviews"); deeper tree navigation only when needed. The tray is NOT a vertical folder explorer. Moving a
  bucket node moves its whole subtree; moving a node into itself/a descendant is prevented; node
  duplication is explicit only, never the default drag.
- Bucket types (each a distinct VERB): Albums-to-hear, Track-collection, Playlist, Playback-queue,
  Read-reviews, Summary, Review/Research. A standalone Notes/Reference collection is NOT a core default
  template (deferred/optional; existing album-review notes are an album-writing aid, not a v1 bucket
  member type). There is NO Inbox-first default; items are placed INTENTIONALLY; an Inbox/Unsorted bucket
  is at most ONE optional template, never the default or first destination.
- Membership invariant: a bucket item is a NON-DESTRUCTIVE RELATIONSHIP to a source object or a snapshot,
  NEVER a copy of the source. Removing from a bucket removes membership ONLY — it never deletes the source.
- MOVE vs ADD vs CONVERT (the core of the model — make these read DIFFERENTLY):
  * INTERNAL move (bucket -> bucket within My Buckit, same object type): default is MOVE — remove source
    membership, create destination membership; source object untouched; feedback "Moved · Undo"; an
    explicit COPY action only when the user wants it in both buckets.
  * EXTERNAL add (from review / listening history / recent plays / liked tracks / album or track detail /
    search / analysis / artist / public reading pages): default is ADD as a membership; the source context
    is unchanged; feedback "Added · Undo" / "Album added · Undo".
  * CROSS-TYPE conversion (item type != bucket type): PRESERVE the original item AND original membership;
    add the transformed result only after the appropriate confirmation; NEVER silently remove the
    original. track->album (resolve parent, compact confirm); album->track (mandatory confirm with count:
    Add all / Select tracks / Cancel); album->playlist (mandatory confirm before expansion, PRESERVES the
    original album track order); review->album bucket (show the reviewed album only if unambiguous, else
    surface candidates); album->read-reviews (surface related review candidates, do not guess).
- Feedback language (bucket-local, anchored to the affected target / quick-inspection surface; a global
  toast is SECONDARY status only): "Moved · Undo", "Added · Undo", "Album added · Undo", "14 tracks added
  · Undo", "Removed from this bucket · Undo". The tray stays open after the operation.
- Listening-history vs SNAPSHOT: adding an ordinary album from listening history into a normal album /
  review / playlist / playback bucket adds the ALBUM REFERENCE ONLY — do NOT auto-copy play count,
  listening time, date range, or analysis stats (viewable later via the source relation, not stored in the
  membership). But adding a PERIOD / analysis-signal / trend / aggregate into a Snapshot/Summary-oriented
  bucket PRESERVES the contemporaneous period + filters + values + source context (a snapshot, because the
  meaning drifts as data evolves); an explicit future "refresh with current data" may exist but NEVER
  silently overwrites the historical snapshot.
- PLAYBACK aims for ACTUAL in-product playback (Play now / Play next / Add to queue — explicit insertion
  positions). Provider is PROVISIONAL: Spotify evaluated first, YouTube as a fallback candidate if needed.
  Render playback as a REAL intended user action while clearly LABELING provider behavior as provisional /
  under technical validation. A queue is more session-like than a stored playlist; offer a "Save queue to
  playlist" bridge.
- SUMMARY bucket = AUTOMATIC asynchronous summarization: dropping material adds the source AND starts a
  summary update; show the bucket as PROCESSING; on completion show a visible indicator (bell/badge) on
  BOTH the bucket and the Pocket tray; opening / quick-inspecting reveals the new summary; preserve visible
  source PROVENANCE (user-dropped / rule-matched / AI-suggested). Default flow is drop -> processing ->
  completion notification -> inspect (NOT a manual "Refresh summary" first; a manual regenerate may exist
  later).
- Decided behaviors: DUPLICATE policy is bucket-type-specific (album/review/research collections reject
  duplicate membership; playlist/playback queue may allow duplicates). ORDERING is bucket-type-specific
  (collections default recent-add; playlist/playback are manual ordered lists; review/research allow
  manual order + pinning). Direct same-type internal MOVE needs NO confirmation (immediate move + Undo);
  conversion and one-to-many expansion REQUIRE confirmation. Bucket DELETION defaults to ARCHIVE; archiving
  or deleting a PARENT bucket requires the user to decide how child buckets are handled.
- v1 is a SINGLE-OWNER workspace. Keep multi-user OUT of this atlas (deferred, not a v1 blocker), but do
  not bake in irreversible single-owner visual assumptions.

## Visual direction
House style is an editorial music-criticism site (serif editorial headings, restrained palette, album
art as the dominant imagery). Do NOT copy Apple Music / Milanote / Raindrop visual identity — borrow
interaction structure only. The tray must clear page chrome (a fixed header and a reading progress bar
exist) and must keep as much of the source page visible as the chosen density allows.

## MANDATORY DELIVERABLE STRUCTURE — package as FOUR numbered comparison boards
Render the FULL option space below, but PACKAGE it as four numbered comparison boards (NOT one giant
single-canvas collage), using the SAME representative music data and a CONSISTENT visual scale across all
four boards. Do not reduce the option space or drop any required state. At the very end, output a visible
COVERAGE CHECKLIST mapping every mandatory option and state to the exact board + panel where it appears.

INVARIANTS — hold on EVERY board and EVERY tray-shell family (never violate, even for tone/density):
- Pocket Buckit is a HORIZONTAL bottom tray and a PROJECTION of the My Buckit tree (pinned/contextual LEAF
  buckets + a compact path); never a vertical folder explorer, vertical menu, sidebar, command palette, or
  toolbar. Parent nodes are folders that do not receive drops by default; leaf buckets are the drop
  targets.
- Entry-control COUNT is compared as three options (one toggle / two same-tray / two filtered-views) — do
  NOT declare a single fixed count. For every option the active originating control CLOSES the tray and the
  tray stays open after a drop.
- The tray shows MULTIPLE bucket TARGETS, each individually visible and independently droppable, reading
  as destination CONTAINERS (not generic commands). The user must understand "which bucket will receive
  this item" at a glance.
- During a drag the tray is spatially STABLE: compatible targets highlighted; conversion-required targets
  visibly explain the pending transform; INCOMPATIBLE targets stay in the SAME position, muted/disabled,
  with a concise reason — never hidden; no reflow/reshuffle.
- Feedback + Undo are BUCKET-LOCAL on the affected target ("Moved · Undo", "Added · Undo", "14 tracks added
  · Undo", "Removed from this bucket · Undo"); the tray stays open. A global toast is SECONDARY status only.
- Membership is a non-destructive relationship, never a copy. Deletion defaults to ARCHIVE; deleting a
  parent prompts for child handling.
- No Inbox-first default; Notes/Reference is not a core default template.

### BOARD 1 — Pocket controls + horizontal tray-shell families
Render all FOUR tray-shell families, never pick one:
   F1 Tangible bucket row (literal-but-restrained container metaphor)
   F2 Editorial shelf / collection rail (magazine shelf)
   F3 Modular utility dock / drawer
   F4 Immersive music-workspace tray
For EACH family, render this full 9-state strip in a labeled row, and place the four families together
(column per family, row per state) so one state can be scanned across all four at once:
   (a) collapsed control (idle)        (b) open tray (resting, ~6 visible LEAF buckets + compact paths)
   (c) compatible drag (valid target highlighted, insertion line where ordered)
   (d) incompatible drag (invalid targets STAY IN PLACE, muted/disabled with a concise reason — NOT
       hidden; the tray must not reflow or reshuffle)
   (e) conversion-required drag (e.g. track over an album bucket — visibly explains the pending resolution)
   (f) successful drop WITH bucket-local Undo ON the affected target ("Added · Undo"); tray stays open
   (g) quick inspection of one bucket (count, purpose, recent adds)
   (h) Apple-like Edit mode (per-item minus = remove-from-bucket, Done exits; reorder for playlist/queue)
   (i) many-bucket overflow (15+ buckets: horizontal scroll vs paginate vs "more" vs search).
Also on Board 1, compare ENTRY CONTROLS and TRAY DENSITY side by side:
   - Entry controls — render ALL THREE options: (1) one persistent toggle; (2) two lower-left/right
     controls opening the SAME tray; (3) two controls opening FILTERED views of the same bucket tree.
     Treatments: icon-only vs icon+text; floating button vs edge-attached tab. States: idle / hover /
     open(active) / drag-active; bucket-count badge. The active originating control closes the tray.
   - Tray density: how much source page stays visible (short bar vs tall sheet vs translucent); pinned vs
     recent vs contextual INITIAL ordering (must not reshuffle during a drag); how the compact tree path
     reads at each density.

### BOARD 2 — Target cards, move/add/convert, drag feedback, confirmations, duplicates, bucket-local Undo
   - Bucket target CARD treatments (5, side by side): literal-restrained container / minimal editorial /
     album-art-driven / icon+action-driven / dense utility. Each card MUST read as a destination CONTAINER
     and communicate: name, compact tree path, purpose/verb, accepted-type-or-compatible-drop-state (live
     vs the dragged item), item count, and the outcome (add / move / convert / play / queue / summarize).
     Also render: empty, single-cover, stacked-grid, pinned, processing (summary), and a "queue" marker.
   - INTERNAL MOVE vs EXTERNAL ADD (make them read differently): an internal bucket->bucket drag shows
     "Moved · Undo" with an explicit Copy affordance; an external-source drop shows "Added · Undo". Show
     both side by side so the default difference is obvious.
   - Source-preserving CONVERSION sequences (annotated left-to-right strips): track->album (parent resolve
     + compact confirm + "Album added · Undo"; original track untouched); album->track / album->playlist
     expansion with "Add all 14 tracks?" (+ Select tracks / Cancel; PRESERVES album track order); the
     original album membership is preserved.
   - Drag feedback states (all): compatible (highlighted), conversion-required (explains transform),
     incompatible (stays in place, muted, concise reason — never hidden, no reflow), one-to-many expansion
     (`+14` badge), executable, duplicate (per bucket-type policy — rejected for collections, allowed for
     playlist/queue), processing, success, bucket-local Undo on the target, error. Insertion line for
     ordered buckets.
   - Confirmation patterns (4) mapped to cases: same-type internal move (NO confirm — immediate move +
     Undo); track->album; album->track (Add all 14 / Select tracks / Cancel); album->playlist; track->
     playback (now/next/queue); album|review|period->summary; ambiguous review (surface candidates).

### BOARD 3 — Quick inspection, Edit mode, removal, reordering, full-bucket handoff, archive-safe delete
   - Quick-inspection patterns (4, side by side): inspect-above-tray panel / expandable tray card / side
     peek / mini drawer. Each with: normal inspection (purpose, count, recent adds, current action), Edit
     mode, minus badges, Done, reordering (playlist/playback manual order; review/research pinning),
     bucket-local removal Undo, and an explicit visual distinction between "remove from bucket" (membership
     only) and "delete source".
   - Keep Pocket Buckit lightweight — show the separate path to open the FULL bucket page for deep work.
   - Deletion safety: bucket deletion defaults to ARCHIVE (recoverable); deleting/archiving a PARENT bucket
     prompts the user to decide how CHILD buckets are handled (move up / archive together / etc.).

### BOARD 4 — Settings/creation, source-page flows, mobile, keyboard, reduced-motion
   - Bucket settings & creation (template-FIRST): template picker (Albums-to-hear / Track-collection /
     Playlist / Playback / Read-reviews / Summary / Review-Research — Notes/Reference is NOT a core default
     template), create, edit, pin-to-Pocket, accepted source types, plain-language conversion-behavior
     description, default drop action, display/order settings, archive-by-default deletion + parent
     child-handling. Advanced rules hidden until needed.
   - Source-page prototypes (render the tray IN CONTEXT; the dragged item is real):
     * Listening-history / analysis dashboard — drag an ordinary top-album (external ADD, ALBUM REFERENCE
       ONLY, no stats copied) AND drag a time-period/signal into a Snapshot/Summary bucket (snapshot:
       period+values FROZEN; auto-processing; bell/badge on completion). Show the difference explicitly.
     * Review reading page (drag the hero album AND a track from the tracklist)
     * Album page (album -> track/playlist/playback/summary). A standalone album page does not exist yet —
       render it as a PROPOSED surface, labeled "new surface."
     * Track page (track -> album/track-collection/playback). Same "new surface" note.
     * Analysis page (analysis-signal -> Summary as a preserved snapshot, auto-processing + bell/badge +
       provenance + "why is this here")
     * Another bucket as source — INTERNAL MOVE by default ("Moved · Undo"), explicit Copy on intent; a
       node move carries its subtree; playback-queue -> playlist "save queue" bridge.
   - PLAYBACK: show Play now / Play next / Add to queue as real actions, with provider clearly marked
     PROVISIONAL (Spotify first, YouTube fallback candidate).
   - Mobile alternatives (beside each desktop equivalent): touch entry control(s), long-press lift + flock
     + count badge, card/confirmation/quick-inspection at phone width, and the non-drag "Add to…" / "Move
     to…" overflow action that ENUMERATES live bucket targets WITH their verbs (Add to Playlist / Move to /
     Queue next / Add 14 tracks / Add to Summary) — a peer to drag, not an afterthought (WCAG 2.5.7).
   - Keyboard navigation: focus a draggable item, Enter/Space to lift, Tab/arrow to choose a bucket target
     (insertion position for ordered buckets), Enter to drop, Esc to cancel — show focus order through the
     tray, with visible focus rings on controls, bucket cards, tray items, and confirmations.
   - Reduced-motion: show the no-flocking / instant-reposition variant next to the animated one.

## OUTPUT FORMAT REQUIREMENTS
- Deliver exactly FOUR numbered comparison boards (Board 1-4 above), NOT one giant single-canvas collage.
  Use the SAME representative music data and a CONSISTENT visual scale across all four boards.
- Within each board, place alternatives in a row/grid so they are directly comparable; caption every panel
  with its option name and the one-line tradeoff it represents. On Board 1, place the four shell families
  together (column per family, row per state) so one state can be scanned across all four at once.
- Annotate states (move / add / convert / compatible / incompatible / duplicate / processing / success /
  bucket-local undo / error) with small labels ON the panels.
- Use realistic music data (album covers, real-length tracklists ~12–16 tracks, Korean + English titles)
  so density and overflow are honest. Do NOT idealize counts — show a 15+ bucket overflow case and a
  14-track expansion case explicitly.
- End with a visible COVERAGE CHECKLIST: a table mapping every mandatory option and state (the three
  entry-control options, the four shell families, each of the 9 states, the tree-path projection, the 5
  card treatments, internal-move vs external-add, every drag-feedback state, the conversion + confirmation
  cases, duplicate handling by type, bucket-local Undo, quick-inspection + edit/remove/reorder + full-bucket
  handoff, archive-safe deletion incl. parent child-handling, settings/creation, the 6 source pages
  (incl. ordinary-add vs snapshot-drop + summary auto-processing + playback provisional), mobile, keyboard,
  reduced-motion) to the exact board + panel where it appears.
- This is an ATLAS for comparison and decision-making. Do not produce a single hero screen, do not declare
  a winner, and do not omit any tray-shell family or any option/state above.
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
