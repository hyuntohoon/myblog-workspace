# FEAT-my-buckit-artist: My Buckit restructure + fixed bucket types (Artist Buckit)

- **Status**: done (all 6 steps shipped + prod-verified 2026-06-30; Step 6 tray-open DnD = front #217 `d2cfbeb`)
- **Owner**: TBD
- **Created**: 2026-06-25
- **Plan row**: `plan.md` → FEAT-my-buckit-artist
- **Related**: `docs/rfcs/FEAT-pocket-buckit.md` (canonical Buckit product — generalized membership; this RFC adds the **first bucket-level type discriminator**, a deliberate scoping of that model), `docs/rfcs/FEAT-bucket-identity.md` (Direction D public artist-collections — this RFC is the private, typed precursor), `docs/archive/done/rfcs/FEAT-pocket-buckit-workspace.md` (the tray drawer workspace this builds on)

> Renames the user-facing **Critique Buckit** management area to **My Buckit** (the full hierarchical
> bucket tree), introduces a **closed, fixed set of bucket types** — **General Buckit** (today's behavior,
> 100% preserved) and **Artist Buckit** (accepts artist members only) — adds a single persistent
> **Pocket Buckit open/close toggle** inside My Buckit, a **NEW marker** on drag-added items, and wires
> **Pocket-open drag into visible buckets**. All built by **reusing** the existing membership API, native
> DnD, detail surfaces, and intent/resume flow — no parallel architectures.

---

## Goal

After this RFC: the profile `평론 버킷` area is **My Buckit** (full tree, hierarchy preserved). A user can
create a bucket as one of two **fixed** types — **General** (unchanged: holds album/track/review/playback/
snapshot) or **Artist** (holds **artist members only**). Artist buckets reject non-artist sources, never
silently convert, dedupe artists within a bucket, and — when a **featuring track or compilation album** is
dropped on them — **explicitly expand** the source into its credited artists (the source itself is not
stored). My Buckit has one persistent `aria-expanded` **Pocket Buckit toggle** (local state, no API), a
**type filter** that narrows the tree while preserving each match's ancestor path, and a transient **NEW
marker** on drag-added items that clears on a short timeout or when the bucket drawer closes. Artist members
click through to the existing `/artist/[id]` hub. No new modal system, no parallel detail/mutation API.

**Design principle** — the bucket-type discriminator is a *scoped, first application* of the
generalized-membership model (FEAT-pocket-buckit D2): an Artist Buckit constrains **member composition**
(which item types it accepts) while the underlying schema stays polymorphic. The type set is a **closed
enum** (`general`, `artist`) — deliberately not user-configurable — so we validate the typed-bucket pattern
on one concrete, high-value case (artist collections, the FEAT-bucket-identity Direction-D precursor) without
committing to arbitrary custom schemas. `general` = today's polymorphic bucket, unchanged. Further types
(playback-queue, summary, …) stay deferred non-goals.

## Non-goals

- **User-configurable bucket types / custom member rules / custom schemas.** The type set is a closed enum
  (`general`, `artist`) only.
- **Snapshot bucket, playback-queue bucket, multiple playback queues, folder-only type** (explicit product
  non-goals; playback stays a future single transient global player, separate from Buckit).
- **A new bucket-specific detail modal or a parallel detail/mutation API.** Reuse `AlbumDetail`, the
  `/artist/[id]` page, the existing `POST /api/buckets/{id}/items` membership route, native DnD, and the
  intent/resume flow.
- **Public surfacing of Artist buckets** (Direction D / `FEAT-bucket-identity`, `FEAT-public-bucket-multiuser`)
  — v1 Artist buckets are private to the single owner.
- **Logged-out artist add** — artist add is logged-in only in v1 (no `artistId` intent/resume variant).
- **Retroactive conversion** of existing buckets or system buckets into Artist buckets.
- **Changing a bucket's type after creation** (v1: type is set once at create).
- **Renaming genuinely review-specific terms** (review / 평론 draft / 평론 workflow stay review-specific).

> **FORWARD POINTER 2026-08-03 — the "playback-queue bucket" non-goal above is superseded (the
> decision itself stands as the record of what was true then).** `docs/rfcs/FEAT-playback-bucket-player.md` makes the playback
> queue a **first-class bucket** (`type='playback'`, `kind='playback_queue'`, one per user), which
> reverses both "playback-queue bucket is a non-goal" and "playback stays separate from Buckit".
> The **closed-enum principle** of this RFC is retained — the set becomes `('general','artist',
> 'playback')` and stays non-user-extensible. This RFC's Artist accept-gate + server re-check
> pattern and its `expandSource` idiom are reused, not replaced (album → **tracks** is a new
> sibling of album → credited artists).

## Current state

Verified against code 2026-06-25 (5-area discovery + a 3-agent adversarial fact-check).

**Bucket model — no bucket-level type, no artist member.**
- `ReviewBucket` columns: `id, name, position, color, is_done, kind, is_public, research_mode, parent_id`
  (`myblog_shared_db/src/myblog_shared_db/models.py:376-411`). **No `type` column.** `kind` encodes
  role/system only (`review` | `spotify_library` | `to_listen`); system buckets are identified by `kind`
  (e.g. partial-unique `idx_review_buckets_single_spotify_library`, `models.py:368-374`).
- `parent_id` self-ref (NULL = root); **non-leaf buckets may hold members** (no schema constraint).
- `ReviewBucketItem.item_type` CHECK = `album|track|review|playback|snapshot` (`models.py:449-452`); FKs
  `album_id, track_id, review_target_id` (`models.py:475-489`). **No `artist` type, no `artist_id`.**
- Per-kind dedup = V30 partial-uniques `uq_review_bucket_items_{album,track,review}` (`models.py:431-448`);
  playback/snapshot allow dups. Consumers use **NOT-EXISTS** dedup, not bare `ON CONFLICT`
  (worker #52 `7bc0514`; memory `reference-onconflict-partial-index-break`).
- `add_item()` dispatches album → `_add_album_item`, else `_add_typed_item`
  (`myblog_backend/app/services/bucket_service.py:358-400`); route `POST /api/buckets/{id}/items`
  (`buckets.py:464-523`). **No gate validating item_type against the bucket** — any item_type is accepted on
  any bucket.

**Artist entity — fully present, not yet a bucket member.**
- `Artist` ORM (`models.py:166-214`): canonical id = `Artist.id` (UUID); also `spotify_id` (UNIQUE),
  `musicbrainz_id`. **Structured credits exist**: `album_artists` + `track_artists` M2M tables
  (`models.py:62-72`), `Album.artists` / `Track.artists` relationships (`models.py:259-260,299-300`) — so a
  featuring/compilation source's artists are resolvable.
- A **Various Artists** guard already exists for attribution — `is_va_compilation()` + a VA-name filter in
  `myblog_backend/.../distribution.py:97-104` (used by `LibraryService`). Expansion must reuse it.
- Search: `GET /api/music/search/unified?type=artist` → `ArtistItem` (id, name, photo_url, genres,
  followers, popularity). Detail: `GET /api/music/artists/{id}` (`ArtistHero`) + static page
  `myblog_front/src/pages/artist/[id].astro`. **Canonical artist detail = the `/artist/[id]` page (not a
  modal).** NB `AlbumDetail.tsx:184-197` currently renders artist rows as **plain text (no link yet)** —
  linking them to `/artist/[id]` is part of Step 5, not existing behavior.

**Frontend — profile nav, DnD, detail.**
- Top-level profile tabs in `ProfileApp.tsx`; the bucket tab label `평론 버킷` (`ProfileApp.tsx:20`), board
  heading in `BucketBoard.tsx`. `/buckets.astro` and `/profile?tab=bucket` are the board entry points (deep
  links to keep stable). A **per-bucket-card** item-type filter already exists (`albumTypes()/passesType()`,
  `BucketBoard.tsx:1125-1142`) — but there is **no board-level type filter** and **no bucket-type** concept.
- DnD = native HTML5 + module-level payload (`BucketBoard.tsx:48-50,556-571,759-794`); validation
  `acceptCol`/`canAcceptBucket` check `kind`/ancestry **but not `bucket.type`** (`:521-526,750-758`); visual
  drop feedback (red insertion line + border glow, `:553,873-877`); **drops are optimistic-first** then
  `api.addBucketItem`. `ops.copyAlbum` (`:1779-1807`) is the genuine copy-in path; `ops.insertAlbum`
  (`:1830`) is shared by **reorder (same-bucket), move (cross-bucket), and insert** (`:742,746,790`).
  Click-vs-drag guard = `suppressClick` (`PocketTray.tsx:507-513`).
- Drawer lifecycle: `PocketBuckitProvider` multi-drawer — `openDrawer`/`closeDrawer`/`closeAllDrawers`/
  `isDrawerOpen` (`PocketBuckitProvider.tsx:56-68,205-209`); tray open/close = `open`/`setOpen` (already
  local-persistent, no API). The tray is currently a **read-only drop *display*** — actual drops land on the
  board.
- Detail: album → `AlbumDetail.tsx` (MemoWindow / 600px StandardModal); track → read-only tile (no modal);
  review/playback/snapshot → labeled tiles. All overlays use `useDismissable`. Add picker =
  `AddToBucketMenu` (transport-agnostic) + intent/`PocketResume` (handles `album`|`track` only,
  `PocketResume.tsx:37-41`) for logged-out handoff. **No NEW/recent highlight pattern exists.**

## Target state

- **My Buckit** = the full tree (default view = real hierarchy, position-ordered). Header is a single toolbar
  row: `My Buckit` title · **type-filter chips** (`전체 / General / Artist`) · one **Pocket Buckit toggle**
  (`aria-expanded`, bound to the existing `usePocketTray()` open state — no new state, no fetch). Type chips
  narrow what renders; a type-filtered match shows the matching bucket **plus all ancestors** (path
  preserved, never flattened). System buckets appear only under `전체`, never inside Artist results, never
  vanish.
- **Bucket types**: `review_buckets.type` ∈ {`general`,`artist`}, default `general`. `kind` (system/role)
  unchanged and orthogonal. Existing + system buckets are `general` → behavior 100% preserved; never
  retro-converted. Type is chosen once at create (segmented General/Artist); not changeable in v1.
- **Artist Buckit**: holds `item_type='artist'` members (`artist_id` → `artists.id`). Add via unified search
  (`type=artist`). Non-artist drops are **rejected at drag-over** (no glow, no optimistic insert; no silent
  convert). **No duplicate artist** in one bucket (partial-unique + NOT-EXISTS skip). Dropping a **featuring
  track / compilation album** **explicitly expands** the source into its credited artists (`album_artists` /
  `track_artists`, **excluding Various Artists**), inserting each not-already-present artist and **skipping
  duplicates**, with feedback ("참여 아티스트 N명 담음 · M명 중복"); the source is **not** stored. Member click →
  `/artist/[id]`.
- **NEW marker**: items **entering** a bucket by drag get an in-memory NEW dot, cleared on **~8s timeout OR
  drawer close (`closeDrawer`), whichever first**. No backend, no localStorage.
- **Pocket-open DnD into visible buckets**: while the tray is open, visible bucket targets (including nested
  buckets visible via expanded ancestors) accept compatible drops, reusing the board's handlers/validation/
  optimistic-update/error-handling — extended, not forked. Artist targets enforce the artist-only rule.

## Steps

Cross-repo order follows the shared_db rollout rule (memory `reference-shared-db-cross-repo-rollout`):
migration → **prod-apply (pre-merge)** → backend pin → workspace contract → frontend. Steps 4–6 are
front-only and **sequentially mergeable after the contract lands** — Step 4 opens only after Step 3 merges
(it regenerates + commits `api.gen.ts` from the merged contract, memory `feedback-frontend-api-gen-sync`);
each step is a one-session unit per rule #4 (ordered, not parallel).

### Step 1 — shared_db: schema migration (V32) + ORM

Additive, reversible. Plain `V32__*.sql` (memory: plain `V{N}__` SQL).
- `ALTER TABLE review_buckets ADD COLUMN type TEXT NOT NULL DEFAULT 'general'` + `CHECK (type IN
  ('general','artist'))`.
- `ALTER TABLE review_bucket_items ADD COLUMN artist_id UUID NULL REFERENCES artists(id) ON DELETE CASCADE`.
- Extend `item_type` CHECK to include `'artist'` (widen — safe; no existing row has `item_type='artist'`).
- `CREATE UNIQUE INDEX uq_review_bucket_items_artist ON review_bucket_items (bucket_id, artist_id) WHERE
  item_type='artist'` (the no-dup-artist guarantee).
- `CHECK (item_type <> 'artist' OR artist_id IS NOT NULL)` — i.e. *an artist row must carry an artist_id*
  (mirrors the album_id constraint; existing non-artist rows pass trivially).
- ORM: `ReviewBucket.type`, `ReviewBucketItem.artist_id` + `Artist` relationship; bump version tag.

**Verification**: `shared_db` pytest schema-parity (memory `reference-shared-db-test-pythonpath-src`,
`PYTHONPATH=src`); apply to Neon prod pre-merge + `\d review_bucket_items` shows the column/index/constraints.
**Rollback**: drop the index + columns (additive — no data migration, fully reversible).

---

### Step 2 — backend: artist membership + bucket-type gate + source-expansion + create-type

Reuses the existing membership route/service; no new route.
- `AddBucketItemRequest`: add `artist_id: Optional[str]` + expansion inputs `source_album_id` /
  `source_track_id: Optional[str]`; `@model_validator` requires (for `item_type='artist'`) **either**
  `artist_id` **or** exactly one `source_*`.
- **Type gate** (`add_item`): if `bucket.type=='artist'` and `item_type!='artist'` and no `source_*` → 400
  (reject non-artist into an Artist bucket). `general` accepts all (today's behavior).
- `bucket_service`: `ArtistNotFoundError`; `_add_typed_item` `artist` branch (validate artist exists;
  per-kind **NOT-EXISTS** dedup → skip, never a bare `ON CONFLICT`).
- **Source-expansion** (OQ1 — recommended backend-side): for `item_type='artist'` + a `source_*`, resolve
  credited artists via `Album.artists` / `Track.artists`, **excluding the Various Artists placeholder**
  (reuse `is_va_compilation()` / VA-name filter, `distribution.py:97-104` — a VA compilation adds **zero**
  artists, not a junk member), then insert each **not-already-present** artist (best-effort NOT-EXISTS skip;
  a mid-batch dup is skipped, not a 409). The source row is never stored.
- **Bucket create** (`POST /api/buckets`): accept `type` (default `general`); system buckets (`kind` set)
  forced `general`. **Type immutability**: `update_bucket` gains an *explicit* guard — if a `type` is
  supplied and differs from `bucket.type`, raise (400) — even though `UpdateBucketRequest` omits the field
  today (pre-empt a future field add).
- Serializer: `_artist_brief` + `_item_response` artist branch (eager-load Artist; null-safe for non-artist
  rows, mirroring the album-only guards).
- **OpenAPI** (exported in this PR): `AddBucketItemRequest` gains `artist_id?`, `source_album_id?`,
  `source_track_id?`; the add response gains an optional `expansion: { added: ArtistBrief[], skipped:
  ArtistBrief[] }` (present only for a `source_*` artist add); new `ArtistBrief { id, name, photo_url? }` on
  `BucketItemResponse` for artist rows; `BucketResponse` gains `type`.

**Verification**: **automated** `pytest` — artist add; **dup-artist skip** (re-add → skipped, no 409);
type-gate reject (album→Artist bucket = 400); single + multi expansion with skip counts; **VA compilation →
0 artists**; create-with-`type`; PATCH type-change rejected. **manual** `curl` add + expand. **Infra**: no
terraform — `POST /api/buckets` + `POST /api/buckets/{id}/items` are already gated in `infra/apigateway.tf`
(extending request bodies needs no route change). (memory `reference-backend-test-config-import-collection` —
lazy-import settings in fixtures.)

---

### Step 3 — workspace: regenerate merged contract

Merge the backend-exported `openapi.json` → regenerate `docs/contracts/openapi.json`
(`scripts/merge_openapi.py`); workspace contract gate. This merged contract is the source `api.gen.ts` derives
from in Step 4. (memory `reference-workspace-contract-merge-order`, `reference-openapi-pydantic-version-drift`
— match local pydantic/fastapi before regen.)

**Verification**: `openapi-verify` clean; diff = only the additive artist/type fields (`type`, `artist_id`,
`source_album_id`, `source_track_id`, `expansion`, `ArtistBrief`).

---

### Step 4 — front: foundation (rename + header toolbar + type filter + Pocket toggle)

Front-only; **opens only after Step 3 merges**.
- Regenerate + commit `src/lib/api.gen.ts` from the Step-3 merged contract (memory
  `feedback-frontend-api-gen-sync` — commit it or the deploy gate fails). This is the Step-3 → Step-4
  dependency.
- **My Buckit rename** (user-facing only; identifiers/`?tab=bucket`/`/buckets`/`kind` unchanged): tab label
  (`ProfileApp.tsx:20`), board heading, empty states, tooltips, aria-labels, `<title>`. Leave review/평론
  workflow strings untouched.
- **Header toolbar row**: `My Buckit` title + **type-filter chips** (`전체/General/Artist`, reusing the
  existing chip pattern) + **single Pocket Buckit toggle** (one button, `aria-expanded`, bound to
  `usePocketTray()` `open`/`setOpen` — no new state, no refetch; not a per-card collapse, not duplicated).
- **Type filter** narrows the rendered tree; a match renders **with all ancestors** (dimmed path), never
  flattened; system buckets only under `전체`.

**Verification**: `pnpm lint` (memory `feedback-front-lint-before-commit`) + `astro check`; **real-browser
click-through** (memory `reference-front-interaction-qa-patterns`) — chips filter + path preserved, toggle
`aria-expanded` flips with **no network call** (DevTools), deep links intact.

---

### Step 5 — front: Artist Buckit (create + render + add + DnD gate + source-expansion)

- **Create flow**: General/Artist segmented control at bucket create.
- **Artist member render**: `ArtistBrief` tile (name + photo_url), click → `/artist/[id]` (page nav, not
  modal); `suppressClick` so a drag doesn't navigate.
- **Add an artist**: reuse unified search (`type=artist`) → `AddToBucketMenu` artist variant. **Logged-out
  artist add is out of scope for v1** (logged-in only) — `PocketResume`/intent stay `album|track`, no
  `artistId` variant.
- **DnD type-gate**: extend `acceptCol`/`canAcceptBucket` (the `onDragOver` validators) to inspect
  `bucket.type` — a non-artist source over an Artist bucket shows **no glow and no optimistic insert** (fail
  *before* drop, not a flash-insert-then-revert on the backend 400); artist source over a General bucket is
  allowed (General accepts all). Backend (Step 2) stays the authoritative gate; this is its UX mirror.
- **Source-expansion drop**: featuring track / compilation album dropped on an Artist bucket calls the Step-2
  expansion, then toasts "참여 아티스트 N명 담음 · M명 중복 건너뜀" (silent + idempotent when all skipped). No silent
  conversion (explicit, with feedback).

**Verification**: lint + `astro check` + browser click-through — create Artist bucket; add via search; an
album drag over an Artist bucket shows **no glow**; drop a featuring track → N artists added, re-drop → all
skipped (dup guard); a VA compilation → 0 added; member click → `/artist/[id]`.

---

### Step 6 — front: NEW marker + Pocket-open DnD into visible buckets

- **NEW marker**: tag only genuine *entries* into a bucket — `ops.copyAlbum` (copy-in from recent/library)
  and `ops.insertAlbum` **only when `fromBucketId !== toBucketId`** (cross-bucket move-in); **never a
  same-bucket reorder** (`ops.insertAlbum` is also the reorder path, `BucketBoard.tsx:742,746,790`). Store in
  an in-memory `Set` of itemIds; small NEW dot on the tile; clear on **~8s timeout OR `closeDrawer`/
  `closeAllDrawers`, whichever first**. No localStorage, no API.
- **Pocket-open DnD into visible buckets**: while the tray is open, make visible bucket targets (incl. nested
  visible via expanded ancestors) accept drops by reusing the board's `acceptCol`/`canAcceptBucket` +
  `ops.*` + optimistic update + error handling (extend, do not fork). Only buckets that already accept
  members are targets (don't make a structural container a target). Artist targets enforce artist-only via
  the same Step-5 drag-over gate.

**Verification**: browser click-through — a drag-in shows NEW, fades at ~8s and on drawer close; a
same-bucket reorder shows **no** NEW; tray-open drop into a nested visible bucket commits via the existing
path (one add request); invalid drop rejected; no extra fetches on open/close/filter/drag (DevTools).

---

## Post-merge verification (prod smoke)

After each step's auto-deploy (CLAUDE.md DoD — quote results in the PR comment; if any item fails, do **not**
drop the plan.md row):
- **Schema (Step 1)**: `\d review_buckets` / `\d review_bucket_items` on Neon prod show `type`, `artist_id`,
  `uq_review_bucket_items_artist`, the widened `item_type` CHECK.
- **Backend (Step 2)**: create an Artist bucket; add one artist (201); re-add → skipped (no 409); drop a
  featuring track via `source_track_id` → N artists, re-drop → all skipped; a Various-Artists compilation →
  0 artists; album→Artist bucket = 400; PATCH type-change = 400. (Throwaway bucket + hard-delete cleanup,
  memory `reference-prod-inline-publish-e2e`.)
- **Front (Steps 4–6)**: chunk-grep the deployed bundle for the new markers (My Buckit copy, type chips,
  toggle `aria-expanded`); CDP/browser click-through (memory `reference-authed-front-prod-cdp-e2e`) — type
  filter preserves ancestor path, toggle flips with **no network call**, Artist create + add + invalid-drop
  rejection (no glow), NEW dot fades at ~8s and on drawer close, tray-open drop into a nested visible bucket.

## Open questions

1. **Source-expansion location** — *(blocks Step 2/5)* backend-side additive on `POST items` (recommended:
   atomic, dedup + VA-filter server-side, one round-trip, no new read endpoint) **vs** frontend-orchestrated
   N normal artist-adds (needs a track→artist-ids read; more requests). Recommend **backend-side**.
2. **Single-artist source on an Artist bucket** — *(RESOLVED 2026-06-25)* any artist-bearing source expands
   to its credited artist(s) — single → 1, multi → N — deduped (already-present artists skipped), VA
   excluded. Uniform with the multi-artist case. See Decisions log.
3. **`type` column vs `kind='artist'`** — *(blocks Step 1)* dedicated `type` column (recommended — keeps
   system/role `kind` orthogonal to member-composition) vs overloading `kind`. Recommend **`type` column**.
4. **NEW marker scope** — *(Step 6)* drag-*entries* only (copy-in + cross-bucket move-in), per the Decisions
   log; broaden to menu/search adds later if wanted. Default as decided.
5. **RFC Status promotion** — *(RESOLVED 2026-06-25)* owner approved ("승격하자") → promoted `draft →
   in-progress`.

## Decisions log

| Date | Decision | Step |
|------|----------|------|
| 2026-06-25 | Adopt all §5 product recommendations from the Phase-1 proposal (type filter = chips not tabs; single `aria-expanded` Pocket toggle = command; default = full tree; filtered view keeps ancestor path; management stays in full-tree context; system buckets orthogonal to type; type immutable v1; public surfacing out of scope). | all |
| 2026-06-25 | **D6**: Artist Buckit = artist members only; multi-artist collection allowed; **featuring/compilation source → explicit auto-expansion** into credited artists (source not stored). Relaxes "no silent conversion" to "explicit, fed-back expansion for artist-bearing sources only". | 2, 5 |
| 2026-06-25 | **Hard invariants (owner-reaffirmed)** — an Artist bucket holds **only** artist members (type gate rejects non-artist with 400; sources are never stored, only their credited artists) and **never duplicate artists**. | 1, 2, 5 |
| 2026-06-25 | **No duplicate artist per bucket** — `uq_review_bucket_items_artist` partial-unique + NOT-EXISTS skip on expansion (no bare `ON CONFLICT`). | 1, 2 |
| 2026-06-25 | **OQ2 resolved** — any artist-bearing source dropped on an Artist bucket expands to its credited artist(s) (single → 1, multi → N), deduped (skip already-present), VA excluded; non-artist-bearing sources rejected. | 2, 5 |
| 2026-06-25 | **Source-expansion excludes *Various Artists*** (reuse `is_va_compilation()` / VA filter) — a VA compilation adds 0 artists, never a junk member. | 2 |
| 2026-06-25 | **NEW marker** — drag-*entries* only: `copyAlbum` + cross-bucket move-in (`fromBucketId !== toBucketId`); **never** a same-bucket reorder; in-memory; clears on ~8s timeout OR drawer close, whichever first; no backend/localStorage. | 6 |
| 2026-06-25 | **DnD type-gate mirrored on the front** — `acceptCol`/`canAcceptBucket` check `bucket.type` (no glow/insert on invalid); backend `add_item` is authoritative. | 2, 5 |
| 2026-06-25 | **Logged-out artist add out of scope (v1)** — artist add is logged-in only; no `artistId` intent variant. | 5 |
| 2026-06-25 | Detail reuse — album = `AlbumDetail`; artist = `/artist/[id]` page (no new modal); no parallel detail/mutation API. | 5, 6 |
