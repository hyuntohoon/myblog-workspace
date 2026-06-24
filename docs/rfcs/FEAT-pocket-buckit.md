# FEAT-pocket-buckit: Pocket Buckit — the canonical Buckit product + interaction definition (design exploration)

- **Status**: in-progress (promoted from draft 2026-06-24 with explicit owner approval — design decided, Pocket Buckit Design Atlas + an interactive configurator built on claude.ai/design, OQ 1–5 resolved as a **user-selectable design setting**, execution plan finalized below via a 7-agent audit+design+review workflow)
- **Owner**: TBD
- **Created**: 2026-06-23
- **Plan row**: `plan.md` → FEAT-pocket-buckit
- **Related**: `docs/rfcs/FEAT-bucket-identity.md` (now reframed as the **compatibility / migration / integration** track — existing review buckets + `들을 것` + public collections — that aligns to *this* model), `docs/rfcs/FEAT-multi-user-accounts.md` (deferred multi-user scope), `docs/rfcs/FEAT-liked-tracks-workbench.md` (the `분석 버킷` track→album promote path)

> **This RFC is the latest, canonical product + interaction definition for Buckit, now IN PROGRESS.** Product
> direction, technical-validation (OQ 6–12), and the Design-Atlas UI (OQ 1–5) are all **decided** — the latter
> as a **user-selectable `design` setting** (the Design Atlas + an interactive configurator were built on
> claude.ai/design). The **execution plan is finalized** (see *Steps*) and the RFC is **promoted to
> in-progress** with explicit owner approval (2026-06-24); push/merge are owner-pre-approved. Build proceeds
> **front-first**: the selectable-design tray on the existing bucket API ships before the
> generalized-membership backend.

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
  not a copy of the source.** *Whether* to add generalized membership is **decided (yes)**; *how* is now
  **resolved (2026-06-23): a staged in-place widening of `review_bucket_items`** (add `item_type` default
  `'album'` + nullable typed FKs; relax `album_id NOT NULL`/UNIQUE in a follow-up step; fold `들을 것` via
  `INSERT…SELECT` into a system bucket) — the album review-pipeline fields stay untouched on album rows.
  See *Technical-validation findings* OQ6.
- **D3 — Playback aims for real playback; v1 = Spotify Premium.** The Playback bucket aims for **actual
  in-product playback** (not intent-recording or a queue snapshot). **Resolved (2026-06-23): v1 uses the
  Spotify Web Playback SDK** — full-track, client-side; requires the **listener's own Spotify Premium** +
  a **per-listener OAuth `streaming` scope** (separate from the read-only worker token); rule #9 holds
  (only an async token mint, no synchronous Spotify on a user-facing endpoint). Membership stores a
  **provider-neutral track identity** (ISRC / artist+title) resolved to a provider id at play time, so a
  **YouTube fallback is DEFERRED** (kept possible, not built — its ToS forbids background/audio-only and
  metadata matching runs ~34% wrong-version). Non-Premium listeners get a preview/disabled state. Provider
  remains **provisional**. See *Technical-validation findings* OQ8/9.
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
- **D9 — The design is a user-selectable setting (decided 2026-06-24).** The Pocket entry-control, tray-shell
  (+weight), ordering, overflow, tree-depth, and quick-inspection are **not** a single hard pick — they are a
  persisted `design` setting the owner switches at will, shipped with a recommended default and **every value
  usable** (all designs selectable). The Design Atlas + an interactive configurator (claude.ai/design) are the
  blueprint. See *Open questions → Design-Atlas decisions* + *Steps*.

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

### Playback (decided goal — D3; v1 resolved 2026-06-23)

The Playback bucket aims for **actual in-product playback** (Play now / Play next / Add to queue — explicit
insertion positions). **v1 = the Spotify Web Playback SDK**: full-track, gapless, client-side JS (fits the
S3 + CloudFront + Astro/React stack), requiring the **listener's own Spotify Premium** and a **per-listener
OAuth `streaming` (+ `user-read-email`/`user-read-private`) scope** — the existing read-only worker token
**cannot** carry streaming, so this is a **new per-listener consent**. **rule #9 holds**: the play path is
client-side; the server only async-mints/refreshes a short-lived token (e.g. `GET /api/playback/spotify-token`),
never proxying a Spotify content call inline. Membership/snapshots store a **provider-neutral track
identity** (ISRC / artist+title) resolved to a provider id at play time, so the provider stays
**provisional/switchable**. **YouTube fallback is DEFERRED** (kept possible by the provider-neutral design,
not built in v1) because: its Developer Policy **forbids background + audio-only playback** and requires a
visible ≥200×200 player with ads (no real music-player UX); public YouTube **cannot search by ISRC** so
matching is title/artist/duration with a measured **~34% wrong-version** rate; and `search.list` costs 100
units against a 10k/day quota. Non-Premium listeners get a **30s preview or a disabled state** (no YouTube
in v1). A queue is more session-like than a stored playlist (a "Save queue to playlist" bridge — internal,
server-side membership copy — converts a session into a stored collection). **Caveats for launch**: a
playback app is a Spotify "Streaming SDA" (monetizing/advertising on it needs Spotify's **prior written
approval**); post-Feb-2026 Spotify Dev Mode caps at **5 authorized users** → an **extended-quota/production
request** is required before any public or multi-user launch; **attribution** (Spotify Marks + link-back)
is mandatory. See *Technical-validation findings* OQ8/9.

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

The product direction is decided (above). The **technical-validation** group is now **resolved
(2026-06-23)** — recorded below as findings/decisions with residual sub-forks deferred to implementation.
The **Design-Atlas** group is now **RESOLVED (2026-06-24)** — the atlas + an interactive configurator were
built (claude.ai/design) and OQ 1–5 are decided as a **user-selectable `design` setting** (below). No open
questions remain; the RFC is promoted to **in-progress** with a finalized execution plan (see *Steps*).

### Design-Atlas decisions (RESOLVED 2026-06-24 — design is a user-selectable setting)

**Binding decision: the design is not a single hard pick — it is a user-selectable `design` setting** (the
five atlas axes), persisted client-side, with the *recommended combo* as the shipped default and **every
value switchable** (owner directive: all designs usable via settings). The atlas configurator's axis
structure is the blueprint (one source of truth). Decisions:

1. **OQ1 — Entry-control model:** selectable; **default = single persistent toggle**; switchable to
   dual-same-tray and (later) dual-filtered-views. Single is the lowest-risk D6-invariant-compliant baseline
   (re-click closes, tray stays open after drop, horizontal bottom-anchored, no left/right branch ambiguity).
2. **OQ2 — Tray-shell family:** selectable across **F1–F6 + an Editorial/Light weight** (forced light for
   F5/F6); **default = F2 editorial-shelf at LIGHT weight**. F2 keeps named, individually-droppable
   destination *containers* (at-a-glance "which bucket receives this") and mixes into the editorial house
   style; the owner's LIGHT lean is routed into the *weight* axis (translucent, page shows through) while
   **F5 floating-pill / F6 sticker-shelf ship real and selectable** for maximum lightness.
3. **OQ3 — Ordering & overflow:** both selectable; **defaults = order `pinned` · overflow `more (+N)`**;
   order switchable to recent/contextual, overflow to scroll/search. Pinned never reshuffles (the
   "spatially stable during a drag" invariant); "more" is the legible non-gestural handoff.
4. **OQ4 — Tree-navigation depth:** selectable; **default = depth 1** (one folder expand to its leaves, then
   hand off to the full page — the RFC's own recommended balance). Depth 0/2 selectable; depth 2 carries the
   explicit "don't become a vertical folder explorer" anti-goal warning.
5. **OQ5 — Quick-inspection surface:** selectable; **default = inspect-above-tray** (rises as one paired
   surface, identical desktop/mobile); switchable to card/side/drawer.

Cross-cutting: no default depends on HTML5 drag (the non-drag "Add to…/Move to…" peer is the WCAG-2.5.7
PRIMARY path on touch); the editorial F1–F4 engine is animation-free and the light F5/F6 animations are
`prefers-reduced-motion`-guarded, so the **F2-light default is reduced-motion-safe by construction**.

### Design-settings architecture (decided 2026-06-24)

A single typed `PocketBuckitDesign` object (the five axes + `schemaVersion`), persisted as one atomic
localStorage blob under `pb:design` (single-owner; future per-owner = additive `pb:design:<sub>` — **no**
`owner_id`, no global-singleton shape, per D5/OQ12). A pure `normalizeDesign()` coerces F5/F6→light and
clamps unknown/removed enums back to the default (graceful forward-compat). Components reuse the
configurator's variant-dispatch verbatim: a **single `PocketTray` dispatcher** selects the engine by
`shell+weight` (never a per-variant fork), the option tables + live-preview settings panel are lifted from
`atlas-configurator.jsx` (settings UI and configurator share one source of truth), surfaced in `/profile` +
an inline gear on the open tray. Gated (not-yet-wired-to-data) variants are **disabled** in the picker, not
silently no-op.

### Technical-validation findings (resolved 2026-06-23)

Owner decisions on the three load-bearing forks: **playback = Spotify Premium-only v1**; **membership =
staged in-place widening**; **multi-user forward-compat = defer all now** (just avoid the global-singleton
shape in new tables). Findings (evidence + sources in the workflow research log):

6. **Generalized-membership migration → staged in-place widening of `review_bucket_items`.** STEP 1
   (additive, no rewrite): `ADD item_type TEXT NOT NULL DEFAULT 'album'` (CHECK ∈ album/track/review/
   playback/snapshot) + nullable typed target FKs (`track_id`→tracks CASCADE, a distinct review-target FK,
   etc.); every existing row is implicitly `item_type='album'`, so the album review-pipeline columns
   (`status`/`note`/`post_id`/`research_selected`/`prep_tonight`) and serializers are **unchanged**. STEP 2
   (after contract+front read `item_type`): relax `album_id NOT NULL`, replace `UNIQUE(bucket_id,album_id)`
   with **per-kind partial-uniques** so non-album kinds become writable. `들을 것` folds in via
   `INSERT…SELECT` into a system bucket; old table kept as a deprecated read-through until front cutover.
   Real typed FKs keep ON DELETE integrity. Rollout: shared_db migration → prod apply → pin → openapi regen
   → front `api.gen.ts` regen. *Residual sub-forks (implementation):* review-member target = a `posts` FK
   vs a future first-class review entity (and disambiguate from the existing `post_id` = "the review this
   album produced"); **playback/snapshot members copy a denormalized payload in a side-table rather than FK
   a volatile listening row** (`spotify_play_events` is prunable); per-kind duplicate policy (D8).
7. **Snapshot storage → a side-table snapshot row** (keyed to the membership) with **typed header columns**
   (`as_of`, `captured_at`, `metric`, `from`, `to`, `unit`, totals, `unresolved/unclassified`) + a `kind`
   discriminator + a **verbatim `frozen` JSONB** payload + `source_album_ids uuid[]` (GIN) + a
   `schema_version`. **Append-only**: "refresh with current data" is a **new row** (new `captured_at`/`as_of`,
   optional `refreshed_from` self-FK), **never an UPDATE** — the never-silently-overwrite rule becomes a
   structural guarantee. The label shows `as_of`, not `captured_at`. Capture is a DB-only read + insert
   (rule #9 safe). Mirrors the `SpotifyLibraryAlbum` side-table idiom so the album-membership hot path
   stays narrow. *Residual:* retention cap; refresh-lineage diff view.
8/9. **Playback → Spotify Web Playback SDK (Premium, per-listener OAuth), YouTube deferred.** (See *Playback*
   above for the full finding.) Membership stores a provider-neutral track identity; the play path is
   client-side with an async token-mint (rule #9). YouTube fallback is **kept possible but not built** (ToS
   forbids background/audio-only; ~34% wrong-version match; quota). *Residual / must-do before launch:* file
   the Spotify **extended-quota/production-access** request (Dev Mode caps at 5 users); resolve the
   "Streaming SDA" **monetization** question with Spotify in writing if monetizing; honor **attribution**;
   real-device **iOS Safari** QA (autoplay/`setVolume` quirks); non-Premium UX (preview vs disabled).
10. **Queue persistence → hybrid.** The queue is a server-persisted **ordered, duplicate-allowed**
   generalized-membership collection under a new `kind='playback_queue'` bucket (the single-special-bucket
   partial-unique idiom, single-owner); the **live playhead** (current item + progress + is_playing) stays
   **client-side**, restored on reload from a small `localStorage` hint (re-seek) — never written to the DB,
   so no rule-#9 conflict and it survives a provider swap. "Save queue to playlist" = a **server-side
   membership copy** into a stored bucket (no Spotify write; a future push-to-Spotify goes enqueue→worker).
   *Residual:* fractional/gap `position` for heavy reorder churn; cross-device resume out of v1 scope.
11. **Public-page sign-in handoff → capture intent + resume.** An anonymous drop writes a **thin
   pending-intent** (`{ts, target bucket-or-sentinel, item descriptor}`, TTL-stamped, **not a content
   copy**) to `localStorage`, then triggers the existing **Cognito PKCE** login; because the callback forces
   `location.replace('/')`, a **resume-checker** (single-drain, idempotent) completes the drop after auth.
   The drop endpoint **must be an explicit Cognito-JWT route** (not edge_guard, which trusts any CloudFront
   request) and the server reads the owner from the verified JWT `sub`, never the body. *Residual:*
   default-bucket auto-create vs forced picker; resume-on-home vs a return-path (touches the shared login
   flow); silent vs confirmed completion.
12. **Multi-user forward-compat → DEFER all now (owner decision).** v1 adds **no `owner_id`** anywhere. The
   single binding rule carried forward: **new generalized-membership/tree tables must NOT use a global
   singleton / partial-unique shape** (no `idx_..._single_done` / `CHECK(id=1)` analog), since that is the
   *only* shape whose later per-owner generalization is a destructive DROP+recreate rather than a plain
   additive `owner_id`. Legacy tables, `_claims['sub']→owner` wiring, and edge_guard per-owner authz are all
   deferred to `FEAT-multi-user-accounts`.

---

## Steps (execution plan — finalized 2026-06-24, promoted to in-progress)

**Re-sequenced front-first** (owner directive: the design implementation must be *actually applied*, with
**all** designs usable via a settings option). The Pocket **design layer** — the user-selectable-design
horizontal tray wired to the **existing album-only** bucket API — ships **first**, so the visible, switchable
design is real before the generalized-membership backend exists; the deeper item types, snapshots, playback,
and sign-in resume then **extend** it. Each step is independently mergeable (standard cross-repo rollout per
CLAUDE.md). **Push/merge are owner pre-approved (2026-06-24).**

**Invariants carried into execution** (from the safety + sequencing review):
- **rule #4** — the two schema steps (**Step 2** / **Step 6**) are SEPARATE sessions with a prod-observe gap.
- **rule #9** — playback is a client SDK + an async token-mint, never a synchronous Spotify call.
- **Contract chain** (strict order) — backend `openapi.json` export *in the backend PR* → workspace
  `scripts/merge_openapi.py` regenerates `docs/contracts/openapi.json` → front `pnpm generate:types`
  regenerates `api.gen.ts` (front CI diffs → fails on drift). These are three distinct artifacts; do not
  collapse the backend export and the workspace merge.
- **Schema-parity gate** — any `shared_db` model change requires regenerating `_generated_schema.sql` **and**
  editing `tests/canonical_schema.sql` in the same PR or `test_schema_parity.py` fails. shared_db **and**
  backend have no real PR-stage CI gate → **local `pytest`+lint(+openapi-diff) is the merge decision**.
- **OQ12** — no new table/index uses the global-singleton shape (no `(TRUE)` partial-unique / `CHECK(id=1)`;
  that shape exists only on *legacy* `review_buckets`/`spotify_now_playing`).
- **owner read** — use `claims.get('sub')` with a single-owner fallback; `require_cognito_token` returns `{}`
  in local/dev, so a bare `claims['sub']` KeyErrors.

1. **front — Pocket design layer on the EXISTING bucket API (no backend/schema dependency).** The
   selectable-design tray, actually applied. `src/lib/pocketBuckit/design.ts`: `PocketBuckitDesign` type +
   frozen `POCKET_DESIGN_DEFAULTS` (`entry:single · shell:f2 · weight:light · order:pinned · overflow:more ·
   treeDepth:1 · inspect:above · schemaVersion:1`) + the axis OPTION TABLES lifted from
   `atlas-configurator.jsx` (one source of truth with the configurator) + a pure `normalizeDesign()`
   (coerce f5/f6→light, clamp unknown enums to default, fill missing axes). Persistence = one atomic
   localStorage key `pb:design`, SSR-safe (`typeof window` guard), schemaVersion-migrated, corrupt→silent
   default (mirror the existing theme provider). `src/components/member/pocket/`: `PocketBuckitProvider`
   (context = resolved design + runtime tray state; `usePocketDesign()`/`usePocketTray()`; mounted ONCE in
   `layout.astro`), `PocketEntry` (entry variants), `PocketTray` (the **single dispatcher** —
   `shell∈{f5,f6}||weight==='light' → LightTray else EditorialTray`; ports `atlas-tray.jsx` F1–F4 +
   `atlas-light.jsx` F1L–F4L/F5/F6 from window-globals to ES modules, fixtures→live buckets),
   `PocketBucketTarget`, `PocketOverflow`, `PocketTreeNav`, `PocketInspect`, `AddToBucketMenu` (the non-drag
   **WCAG 2.5.7** peer — PRIMARY on touch — reusing `BucketPickerSheet.tsx`). Settings: `PocketDesignSettings`
   hosted in `/profile` (ProfileApp) + an inline gear on the open tray → the same panel as a bottom sheet;
   **live preview** bound to the in-progress selection; a `추천` badge on each default; gated values are
   **disabled, not just labeled**. **All 6 shells + every axis value are real and selectable** (the owner
   directive — all designs usable); the only later-gated items are those that need data from a deeper step
   (generalized item types, playback). Wire to the **existing** `GET /api/buckets` + the current album
   add/move/remove (`src/lib/buckets.ts`) — album membership only for now. New `--z-pocket ≈70` token in
   `global.css` (between progress 60 and overlay 80; do not reuse 50/60). Mount in `layout.astro` after
   `<Footer/>` (covers profile + review; the writer's `write-layout.astro` stays OFF in v1). **Acceptance:**
   `pnpm lint` (antfu, before commit) + `astro check` on Node 20 (.nvmrc 20.19.5); a real-browser CDP
   click-through of entry open/close, an album drop with bucket-local Undo, incompatible-stays-in-place (no
   reflow), the touch AddToBucketMenu path, and the settings panel switching **every** axis with live preview
   persisting across reload (functional-setState multi-select correctness only surfaces in a live
   click-through). **Gate:** prod smoke of the deployed bundle (classNames survive minify); observe one clean
   cycle.

2. **shared_db — STEP-1 additive membership widening + snapshot side-table + playback_queue kind (V28/V29)**
   [rule #4 schema step A]. `V28__review_bucket_items_generalize.sql` (BEGIN…COMMIT): `ADD COLUMN item_type
   TEXT NOT NULL DEFAULT 'album' CHECK item_type IN ('album','track','review','playback','snapshot')`; `ADD
   COLUMN track_id UUID NULL REFERENCES tracks(id) ON DELETE CASCADE`; `ADD COLUMN review_target_id UUID NULL
   REFERENCES posts(id) ON DELETE CASCADE` (**DISTINCT** from the existing `post_id` = "the review this album
   PRODUCED", SET NULL) + supporting indexes + one-line DROP-COLUMN rollback per the V18/V22 idiom.
   `V29__bucket_item_snapshots.sql` (side-table mirroring V15: `item_id` FK CASCADE, kind, `as_of`/
   `captured_at`, metric/from/to/unit/totals/unresolved/unclassified, `frozen` JSONB NOT NULL,
   `source_album_ids UUID[]` + GIN index, `schema_version`, `refreshed_from` self-FK; **APPEND-ONLY**; **no**
   singleton shape). `playback_queue` kind needs no enum widening (`kind` is free TEXT) — **do NOT** add a
   per-kind singleton partial-unique. `models.py` (import `ARRAY` — net-new here; JSONB already imported),
   export `BucketItemSnapshot`, **regen `_generated_schema.sql` + edit `canonical_schema.sql`**, bump
   `pyproject` + tag. **Do NOT** relax `album_id NOT NULL`/UNIQUE here (that is Step 6). **Gate:** human
   applies V28+V29 to Neon prod (rule #3) and confirms columns exist **before** the backend pin bump
   (reference-shared-db-cross-repo-rollout).

3. **backend — generalize add_item/serializers on item_type + snapshot-capture + async playback token +
   JWT public-drop.** Bump the shared_db git pin (read the REAL pin in pyproject/requirements; README is
   stale at v0.5.0). `schemas.py`: widen `AddBucketItemRequest`/`BucketItemResponse` with `item_type` + a
   typed payload (non-album rows serialize **without** a required nested `AlbumBrief`) + Playback-token /
   public-drop / SnapshotCapture schemas. `bucket_service.add_item`: branch on `item_type` (keep the exact
   album path: Album lookup + `_score` seeding + UNIQUE dedup; resolve+validate typed targets for the other
   kinds; per-kind duplicate policy D8; seed position separately for non-album kinds — `_score` is
   album-typed); snapshot-capture = read `library/stream-history` aggregate + **append-only INSERT** (never
   UPDATE; rule #9 safe); a short-lived Spotify-token **mint/refresh-only** helper (no inline Spotify content
   call). `buckets.py`: branch `_item_response`/`_album_brief` (today `str(item.album_id)` is unconditional →
   500s on non-album rows); album-only auto-research enqueue. NEW `routes/playback.py` `GET
   /api/playback/spotify-token` (Cognito-JWT). Public-drop = an **explicit Cognito-JWT route** reading owner
   from `claims.get('sub')` (first sub consumer; **no `owner_id` in v1**). `infra/apigateway.tf`: one
   `aws_apigatewayv2_route` per new endpoint (`authorizer_id=cognito`) — the token GET as its **own** explicit
   route, NOT the `GET /api/{proxy+}` edge_guard catch-all. `make export-openapi` + commit `openapi.json` in
   the **same PR**. **Acceptance:** local pytest+lint (no local DB → defer to prod smoke; **local
   pytest+lint+openapi-diff is the merge decision**); `GET /api/buckets` serializes a mixed album+non-album
   bucket without 500; probe routes live with `curl -X` (401=live vs 404). **Must-fix probe:** the token route
   **rejects an edge-only request** (x-origin-verify, *no* Bearer) with 401/403 — proving it did not fall into
   the edge_guard catch-all (else any CloudFront-fronted request mints a streaming token). **Gate:** human
   applies the apigateway routes; prod smoke quoted in the PR comment; public-drop confirmed JWT-gated
   (`curl` 401 not 404) reading owner from sub, before front wires the drop.

   > **Build note (2026-06-24, owner-confirmed scope):** V28/V29 (Step 2) kept `album_id NOT
   > NULL` + the named UNIQUE — the relax is **Step 6** — so a non-album row **cannot be
   > INSERTed yet**. Pulling the relax forward would violate rule #4 + the serializer-before-relax
   > gate. Step 3 therefore ships the **read-side serializer + scaffolding ONLY**: the
   > `item_type`-tolerant serializer (deployed + prod-verified before the relax), `add_item`
   > threading `item_type` but **rejecting non-album writes with 422** (`TypedMembershipNotEnabledError`),
   > the dormant async `GET /api/playback/spotify-token` (own JWT route; 503 until the Step-5
   > `streaming` consent — Spotify app creds confirmed present in the `myblog/spotify` secret +
   > a new `streaming_refresh_token` key, so NO 501 stub was needed), and `resolve_owner`. The
   > **non-album `add_item` branches, the snapshot-capture INSERT, and per-kind dedup move to
   > Step 6** (alongside the relax, where they are end-to-end testable). The "public-drop" is the
   > existing `POST /api/buckets/{id}/items` JWT route now reading owner from `sub` (no separate
   > endpoint). Shipped as backend `fcd01cb` + the one apigateway route (clean `1 add / 0 change`).

4. **workspace — regenerate the merged contract.** `scripts/merge_openapi.py` → `docs/contracts/openapi.json`
   (merge workspace first so the service notify is a no-op — reference-workspace-contract-merge-order). This
   is a distinct artifact from the backend export; it unblocks the front regen. **Gate:** merged contract on
   main **before** Step 5's `api.gen.ts` regen.

5. **front — generalized item types + playback SDK + sign-in resume + drop sources (extends Step 1).**
   **Split into 5a / 5b (owner-approved 2026-06-24)** at the marked sub-boundary (item-types as 5a;
   playback+resume as 5b) — the dispatcher is never forked, only extended. 5a ships the generalized
   item-type render + the non-drag add path + the logged-out resume; 5b adds the Spotify SDK, the
   per-listener streaming consent, the play/queue UI, and the public drop SOURCES that exercise the 5a
   handoff. The `api.gen.ts` regen (post-Step-4 merged contract) shipped with 5a.

   **5a — generalized item types + non-drag add + sign-in resume. ✅ DONE + prod-live 2026-06-24**
   (myblog_front PR **#203** `b7040ee`, deploy `28068681050`). Generalized the tray/board render off
   `item_type` so a non-album row is **null-album-safe** (item rows + `BucketBoard` 17-site guard — the
   first non-album row can no longer 500 the board); **`api.gen.ts` regenerated** off the Step-4 merged
   contract (`item_type`/`track_id`/`review_target_id`, album/album_id → Optional). NEW **self-styled
   non-drag `AddToBucketMenu`** — the WCAG 2.5.7 PRIMARY path (touch + keyboard peer to drag), inline
   sheet + bucket-local toast, **`member.css`-independent** (no `/profile`-scope dependency so it works on
   any surface). NEW **`PocketResume`** home island — **single-drain, idempotent, TTL-bounded** replay of
   the `pb:resume` pending-intent written by a logged-out drop (callback forces `location.replace('/')`),
   the drop completed by the existing JWT route reading owner from `sub`. Wired the **ImportAnalysis** drop
   source (album add). **Acceptance met:** `pnpm lint` (antfu) + `astro check` on Node 20; real-browser CDP
   click-through **13/13** (entry open/close, generalized add, logged-out → `pb:resume` → `goLogin` → home
   resume, the touch `AddToBucketMenu` path, settings persistence across reload). **Prod-live + smoked.**

   **5b — Spotify Web Playback SDK (lazy/dormant) + play UI + public review drop sources. ✅ DONE +
   prod-live 2026-06-24** (myblog_front PR **#204** `473237f`, deploy `28070507378`). **Token model A+
   (owner-decided this session):** v1 streaming token is **single-owner, server-minted** via `GET
   /api/playback/spotify-token` (Cognito-JWT), **503-dormant** (`"Spotify playback not configured"`) until
   the owner provisions a `streaming_refresh_token` key in the `myblog/spotify` secret — so only the
   **dormant path** is reachable now (non-Premium → preview/disabled later). **No browser per-listener
   Spotify OAuth was built**: the backend mints from the owner secret, so a per-listener browser flow would
   be dead code until multi-user. Cognito **`auth.ts` is UNCHANGED** (non-playback login provably
   untouched); the per-listener consent is left as a **documented seam** (a future `spotifyAuth.ts`, not a
   change to the Cognito SCOPES) for `FEAT-multi-user-accounts`. NEW `src/lib/spotifyPlayback.ts` —
   **lazy-loads `sdk.scdn.co/spotify-player.js` only inside an explicit play action's live-token branch**
   (never at module import / tray mount / for an anonymous visitor / on a public review page — rule #9).
   **Token-first:** `getStreamingToken()` (the single swappable token seam) uses a raw `fetch`+`getAuthHeader`
   (NOT `apiFetch`, so a play click never redirects to login; an anonymous caller short-circuits with zero
   network call), and a 503/unauthorized returns **before** any SDK pull. Identity is provider-neutral
   (`PlaybackTarget`); the SDK loader + `Player.connect` are real-but-gated; the one genuine gap (no Spotify
   URI surfaced on items) is the documented `resolveProviderUri` seam. No `owner_id`/singleton (OQ12). UI:
   an inspect-row ▶ on the 5a-generalized item rows → dormant notice; the **public review hero** mounts
   `AddToBucketMenu` (`client:only=react`) — the real entry into the 5a logged-out `pb:resume` → `goLogin`
   → home `PocketResume` handoff — and the tracklist gets a per-track ▶ **play** (dormant), **not** a
   track-as-bucket-member (a track write 422s until the Step-6 relax — deferred). **Verified:** `pnpm lint`
   (antfu) + `astro check` clean on Node 20; a real-browser **CDP** run on a temp local review page — SDK
   **not** loaded at tray mount or after a dormant play (the negative test), explicit play → token fetch →
   503 → dormant notice, hero 담기 island hydrates, 2 tracklist ▶ render; an adversarial 3-lens review
   (rule-#9/correctness, regression, brief-completeness) **PASS**. **Prod smoke:** deployed
   `spotifyPlayback.*.js` ships the token path + the SDK URL as a lazy string + the dormant message; the home
   page eager-loads `sdk.scdn.co` **0×**; the token route returns **401** unauthenticated (live + Cognito-gated;
   503-with-JWT verified in backend Step 3, and 5b touched no backend). Full review-page click-through on prod
   awaits a published review article (none is published on prod yet); Spotify Dev-Mode 5-user cap → file the
   extended-quota request before any multi-user launch (out-of-band, not a v1 merge blocker).

6. **shared_db — STEP-2 relax (V30/V31)** [rule #4 schema step B — SEPARATE session]. Relax `album_id NOT
   NULL`; replace `uq_review_bucket_items_bucket_album` with **per-kind partial-uniques** (album/review/
   research reject dupes; playlist/playback_queue allow — D8); fold `album_to_listen_items` via
   `INSERT…SELECT` into a system bucket (old table kept as a deprecated read-through until front cutover).
   Regen schema + canonical. **No** global-singleton shape. **Acceptance must-fix:** after V30/V31 an
   album-row **duplicate INSERT still raises** (the new per-kind partial-unique must cover `album` — the
   dropped named UNIQUE was the old dedup that `bucket_service.add_item` relies on; confirm against prod).
   **Gate (rule #4 + serializer hazard):** the `item_type`-branching serializer (Step 3) must already be
   **PROD-deployed and verified** serializing a mixed bucket **before** this relax, else the first non-album
   row 500s the whole `GET /api/buckets` board. Separate session from Step 2; human applies to Neon prod
   (rule #3); confirm no album-row regression before dropping the plan.md row. Note: re-adding `album_id NOT
   NULL` is **not** trivially reversible once non-album rows exist — kept in its own migration so V28 stays
   cleanly rollback-able.

   **Build note (2026-06-24 — DONE + Neon-prod-live; V30/V31 APPLIED this session, all acceptance proofs green vs live).** V30/V31 authored + merged to shared_db
   `main` (PR #47 `496a290`). **D8 mapping resolved as Option A** (owner-decided): `album`/`track`/`review`
   get per-kind partial-uniques (`uq_review_bucket_items_{album,track,review}`, predicate
   `WHERE item_type='<kind>'`); `playback`/`snapshot` allow duplicates. Added
   `ck_review_bucket_items_album_id_present` (`item_type<>'album' OR album_id IS NOT NULL`) so dropping NOT
   NULL can't admit a NULL-album `album` row that escapes the album partial-unique. V31 folds
   `album_to_listen_items` into a `kind='to_listen'` system bucket (idempotent NOT-EXISTS guards, no
   singleton index). Parity 58/58; a 3-lens adversarial review confirmed the dup-album must-fix (proven vs
   live Postgres) + OQ12. **Worker co-requisite (PR #52 `7bc0514`):** `library_sync._insert_bucket_item`
   used a bare `ON CONFLICT (bucket_id, album_id)` that cannot infer the V30 partial album index → would 500
   the Spotify library sync on V30 apply; replaced with a schema-agnostic NOT-EXISTS dedup + a real-engine
   integration test. **Rollout DONE (2026-06-24, Claude, owner-approved):** applied — worker deployed first (✅ run `28072…`-class green) → `BEGIN…ROLLBACK` dry-run clean on Neon → applied V30 then V31 (each file's own `BEGIN…COMMIT`) → live re-verify all green: `album_id` nullable, 3 per-kind partial-uniques, `ck_..._album_id_present`, `들을 것` `kind='to_listen'` bucket created (prod queue empty → 0 members folded), 96 album rows untouched, dup-album INSERT → `unique_violation` + NULL-album `album` row → `check_violation`; board `GET /api/buckets` → 200 incl. the empty to_listen (smoke JWT). **Resume-verification caught that the migrations were merged but NOT applied** (the live DB was still V28/V29 when this session began). **Backend follow-on now DONE + prod-live** (myblog_backend #93 — see decisions log); still-deferred:
   front track-as-bucket-member (5b Q1) + `들을 것` front cutover off the old `album_to_listen_items` table.

> **Continuation pointer (for an uninterrupted multi-session build):** Step 1 (front design layer) is first
> and dependency-free. Build order: **1 → 2 → 3 → 4 → 5 → 6**. Steps 2 and 6 are the rule-#4 schema pair
> (separate sessions). If Step 1 or Step 5 grows too large for one PR, split at the marked sub-boundaries
> (Step 1: tray+settings as 1a, drop-source wiring as 1b; Step 5: item-types as 5a, playback+resume as 5b) —
> the dispatcher is never forked, only extended. The design defaults + the must-fix guards are recorded in
> memory `reference-pocket-buckit-execution-plan`.

## Decisions log

| Date | Decision | Step |
|------|----------|------|
| 2026-06-23 | Filed as a draft design-exploration RFC. Documented in English per CLAUDE.md doc-language; brief authored in Korean per the task, translated here. | — |
| 2026-06-23 | Corrections v2: bucket-local Undo (not a global toast); incompatible drop targets stay visible/stable during a drag; bucket-target invariant across all tray shells; Design Atlas repackaged into four numbered boards + a coverage checklist. | — |
| 2026-06-23 | Corrections v3 (this version is canonical): Pocket Buckit is the canonical top-level product/interaction definition; FEAT-bucket-identity reframed as its compatibility/migration/integration track (absorb-question answered: yes). Generalized **membership** decided (item↔bucket relationship, not a copy; "membership" ≠ paid/multi-user). Tree ("My Buckit") canonical; Pocket = its projection (parent=folders, leaf=actionable). Move/add/transform semantics fixed (internal MOVE default + Undo; external ADD; source-preserving conversion). Notes narrowed (standalone Notes/Reference deferred). Ordinary listening-add ≠ snapshot (no auto stat-copy; snapshots frozen). **Playback aims for real playback** (Spotify→YouTube, provider provisional). **Summary** auto-async + bell/badge (not manual-refresh-first). Multi-user deferred (v1 single-owner; not an atlas blocker; keep scoping possible). **Entry-control count re-opened** (1 or 2 controls; single-control comparison restored; dual-non-negotiable wording removed). Decided behaviors fixed (duplicate/ordering by type; album→track order preserved; same-type move no-confirm; conversion/expansion confirm; delete→archive; parent child-handling). Open Questions split into Design-Atlas vs Technical-validation. | — |
| 2026-06-23 | Technical-validation OQs **resolved** (10-agent research/design workflow + owner decisions). **Playback v1 = Spotify Web Playback SDK (Premium, per-listener `streaming` OAuth, client-side; rule-#9 token-mint); YouTube deferred** (provider-neutral track identity keeps it possible). **Membership = staged in-place widening** of `review_bucket_items` (`item_type`+nullable typed FKs; relax in STEP 2; fold `들을 것`). **Snapshot = side-table** (typed header + `frozen` JSONB + `source_album_ids[]` + `schema_version`, append-only refresh). **Queue = hybrid** (server ordered+dup-allowed membership `kind='playback_queue'`; client-ephemeral playhead; internal save-to-playlist). **Sign-in handoff = localStorage thin-intent + Cognito PKCE + single-drain resume**; drop route must be explicit Cognito-JWT. **Multi-user = defer all** (owner decision) — no `owner_id` now; the one rule: new tables avoid the global-singleton shape. Steps now gated only on the Design Atlas. | — |
| 2026-06-24 | **Design Atlas + interactive configurator built** (claude.ai/design project `cf932975` — `Pocket Buckit configurator.html` + `atlas-configurator.jsx`; clickable 5-axis configurator over the atlas engines). **OQ 1–5 resolved** as a **user-selectable `design` setting** (default = single-toggle / F2-editorial-light / pinned / more / depth-1 / inspect-above; all axes switchable, all 6 shells real — D9). **Design-settings architecture decided** (`PocketBuckitDesign` blob under `pb:design`, single `PocketTray` dispatcher, configurator as blueprint). **Execution plan finalized** via a 7-agent audit+design+review workflow; both adversarial-review must-fixes baked in (`claims.get('sub')`; token-route edge-only probe; STEP-2 gated on serializer-prod-deployed + album-dup-survives-the-swap; 3-artifact contract chain; gated-variants-disabled). **Promoted draft→in-progress with explicit owner approval; push/merge owner-pre-approved.** Re-sequenced **front-first** (design layer on existing buckets ships before the membership backend). | All |
| 2026-06-24 | **Steps 1–4 + 5a DONE + prod-live.** Step 5 **split into 5a / 5b (owner-approved)** at the marked item-types ‖ playback+resume sub-boundary so the Spotify SDK + per-listener `streaming` consent get their own session (the `PocketTray` dispatcher is never forked, only extended). **5a shipped** (myblog_front PR **#203** `b7040ee`, deploy `28068681050`, prod-live + smoked): generalized item-type render (null-album-safe rows + `BucketBoard` 17-site guard so the first non-album row can't 500 the board), `api.gen.ts` regen off the Step-4 merged contract, self-styled non-drag **`AddToBucketMenu`** (WCAG 2.5.7 primary, `member.css`-independent inline sheet/toast), **`PocketResume`** single-drain/idempotent/TTL-bounded `pb:resume` home island for the logged-out drop handoff, ImportAnalysis drop source; CDP 13/13. **5b deferred to its own session** (the playback SDK lazy-loads only on explicit play — never at tray mount / for anonymous visitors / on public review pages, rule #9; the `GET /api/playback/spotify-token` route stays **503-dormant** until the owner provisions `streaming_refresh_token`, so only the dormant path is verifiable until then). | 5 |
| 2026-06-24 | **Step 5b DONE + prod-live** (myblog_front PR **#204** `473237f`, deploy `28070507378`). **Token-model decision "A+" (owner)**: when the implementer surfaced that the Step-3 backend mints the streaming token **server-side from the owner's `streaming_refresh_token`** (single-owner), the owner chose **A+** — ship the **server-mint single-owner** path now (the only thing that functions in v1) while keeping the future per-listener path open via seams, and **build no multi-user code**. Concretely: token acquisition is one swappable `getStreamingToken()` seam, identity is provider-neutral, no `owner_id`/singleton, and Cognito **`auth.ts` is UNCHANGED** (the per-listener browser OAuth is a documented seam → `FEAT-multi-user-accounts`, NOT built — it would be dead until the backend stores a per-listener token). **Scope (owner Q1)**: the review tracklist gets a (dormant) **play** affordance only; **track-as-bucket-member is deferred to Step 6** (the backend 422s non-album writes until the relax). The SDK lazy-loads only inside an explicit play action's live-token branch (token-first; a 503/anon short-circuits before any SDK pull — rule #9); a play click never redirects (raw `fetch`, not `apiFetch`). Verified: lint+astro-check, real-browser CDP (negative test + dormant play), adversarial 3-lens review PASS, prod smoke (bundle carries the code, no eager SDK, token route 401-live). **Next = Step 6** (shared_db STEP-2 relax) — separate session per rule #4, gated on the prod-deployed Step-3 serializer. | 5b |
| 2026-06-24 | **Step 6 V30/V31 APPLIED to Neon prod** (Claude, owner-approved, this session). Worker co-req deployed first → `BEGIN…ROLLBACK` dry-run clean → applied V30 (relax `album_id NOT NULL` + per-kind partial-uniques album/track/review + `ck_..._album_id_present`) then V31 (`들을 것`→`kind='to_listen'` system bucket; prod `album_to_listen_items` empty → 0 members folded) → live re-verify all green (dup-album → `unique_violation`, NULL-album → `check_violation`, board 200 incl. the empty to_listen). **Resume-verification caught that #47/#52 were merged but the migrations were NOT yet on prod** (live DB still V28/V29). shared_db #47 left `pyproject` at v0.25.0 + untagged → the backend pins V30/V31 by **commit SHA `496a290`**, not a tag. **Next = the deferred backend follow-on** (non-album `add_item` branches + snapshot-capture append-only INSERT + per-kind dedup + `AddBucketItemRequest` typed targets), then the front (track-as-member + `들을 것` cutover). | 6 |
| 2026-06-24 | **Step 6 backend follow-on DONE + prod-live** (myblog_backend #93). Enabled non-album `add_item` (track/review/playback/snapshot) + append-only snapshot-capture (`bucket_item_snapshots`) + per-kind dedup matching the V30 partial-uniques + `AddBucketItemRequest` typed targets (`album_id` optional) + `TrackBrief`; shared_db pin → SHA `496a290`; openapi + workspace contract regenerated. A 3-lens adversarial review (verdict fix-blockers-first) caught + fixed a **blocker** — `research_service.enqueue_bucket` fed `str(None)` into the NOT-NULL `album_research.album_id` for non-album rows in an all/selected bucket (silent partial-enqueue via `update_bucket`/`reorder`) — plus 2 lows (snapshot `source_album_ids` → `List[UUID]`; IntegrityError→409 scoped to the de-duped kinds). Verified: pytest **323** / pyright **0** / **live-integration 12/12** (rolled back vs prod schema) / **prod smoke** (track POST 201 was-422 w/ TrackBrief, dup→409, review→201, missing-target→422, hard-delete cleanup). **Deploy anomaly:** the #93 squash-merge push created **no** workflow run (`total_count=0`; Step 3's fired in ~55s) → added `workflow_dispatch` (#94) + a main-only ref guard for it (#95, from a background security finding); the #94 merge push auto-deployed `main` HEAD. **Next = front** track-as-member (5b Q1) + `들을 것` cutover (regen `api.gen.ts` first). | 6 |
| 2026-06-24 | **Step 6 front follow-on DONE + prod-live** (myblog_front PR **#207** `b3ea989`, deploy `28084986578`) — completes Step 6 and the RFC's 6 planned steps. **(1) track-as-bucket-member** (5b-deferred Q1): `addBucketTrack` (`POST { track_id, item_type:'track' }`) via a shared `postBucketItem`; `mapItem` renders a track row from `it.track` (`TrackBrief`) while keeping `albumId` **NULL** so album-only ops (copy/restore/undo/dedup) skip it (the backend sends `album_id=NULL` on a track row — the track's parent album lives in `TrackBrief.album_id`, deliberately not surfaced as `BoardAlbum.albumId`); `AddToBucketMenu`/`PocketResume`/`intent.ts` generalized to a tagged `album|track` union with `open`/`pick` kept referentially stable (the `autoOpen` effect depends on `open`'s identity); `BucketBoard` track tile (트랙 badge, no album-detail open, no rating/research) + a new guard rejecting a track drop into the sync-owned `spotify_library` bucket (no `album_id` to reconcile). The public **review tracklist** (vanilla DOM, injected by `albumDetail.client.ts`) gains a per-track **담기** button that dispatches a `pb:add-track` window event to a new **`ReviewTrackAdder`** island (mounted `client:only` in `review/[slug].astro`) which opens the shared `AddToBucketMenu` for the track — the vanilla script can't mount React, so this is an event bridge (same shape as the existing `album:detail` one; the event name is a string literal duplicated in both, documented). Logged-out routes through the menu's `pb:resume` → Cognito → home `PocketResume` handoff. **(2) `들을 것` cutover**: `crMeta` tags the system queue by canonical `kind='to_listen'` (the V31 fold), with the `/들을|예정/` name regex kept only as a legacy fallback for user-named buckets — the front never called `/api/library/to-listen`, so there is **no read-through to remove**; the cutover is name→kind (rename-proof) identification. `api.gen.ts` regenerated off the merged contract (front deploy gate). **Verification**: `pnpm lint` (antfu) + `astro check` 0-err; real-browser **CDP** (local dev + temp review page — the 담기 button → `pb:add-track` → `ReviewTrackAdder` island → `AddToBucketMenu.open()` → `listBuckets()` chain fired); **prod build** compiles the 5-col tracklist grid (`3ch 1fr auto auto auto`) + `.lfq-tt-add` (the dev `:global()` quirk resolves at build); adversarial 4-lens self-review (the workflow's subagents hit a session-cap, so run in the main loop) surfaced + fixed the `spotify_library` track-drop guard, album path / hook-stability / contract-body / `mapItem` albumId-NULL invariant / `crMeta` ordering all confirmed intact. **Prod smoke**: the new code is LIVE in the deployed `PocketResume` (album|track reconstruction) / `AddToBucketMenu` (track branch + 트랙 hint) / `buckets` (`item_type:"track"`+`track_id`) / `ProfileApp` (`to_listen`) chunks; home hydrates clean (no regression). The review-page 담기 surface is **DORMANT** on prod until a review is published (prod has 0 reviews → `/review/[slug]` pages aren't built); the actual `POST item_type='track'` → 201 w/ `TrackBrief` is proven by the **#93** backend prod smoke (the endpoint the front now calls). **Remaining future kinds** (review-as-member / playback-queue / snapshot front surfaces) are documented seams the backend already supports — not committed steps of this RFC. | 6 |

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
  positions). v1 PROVIDER = Spotify (Web Playback SDK): render REAL playback for a Spotify-PREMIUM listener,
  AND a distinct NON-PREMIUM state (a 30s preview or a disabled "Premium required" affordance). A YouTube
  fallback is DEFERRED (NOT in v1) — show the provider as PROVISIONAL/switchable, never a hidden background
  player. A queue is more session-like than a stored playlist; offer an (internal) "Save queue to playlist"
  bridge.
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
   - PLAYBACK: show Play now / Play next / Add to queue as real actions for a Spotify-PREMIUM listener, AND
     a distinct NON-PREMIUM state (30s preview or a disabled "Premium required" affordance). v1 provider =
     Spotify; YouTube fallback DEFERRED; mark the provider PROVISIONAL (never a hidden background player).
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
