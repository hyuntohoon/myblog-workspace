# FEAT-playback-bucket-player: the system-owned Playback Bucket and its two player forms

- **Status**: accepted (owner approval 2026-08-03, in-session; four decisions recorded below)
- **Owner**: TBD
- **Created**: 2026-08-03
- **Plan row**: `plan.md` → FEAT-playback-bucket-player
- **Builds on (shipped, not blocking)**: `docs/rfcs/FEAT-member-player.md` Step 5 + 5b + 6 + 7 —
  the unified `play(intent)` ladder, the device picker, Media Session, and the `astro:before-swap`
  navigation-persistence override. **All shipped and prod-verified 2026-08-02, cold start
  owner-confirmed 2026-08-03** (front #334 `9df4c7a`, #335 `8e82d74`, #336, #337 `c8e951e`,
  #340 `a592360`, #342). This RFC **consumes** them and must not rebuild them.
- **Prerequisite created by the owner's 2026-08-03 decisions — both live in OTHER RFCs, not here**:
  (a) opening the member `streaming` OAuth scope, which belongs to `FEAT-member-player` (it owns
  `integrations.api.ts` scopes and the re-consent banner idiom); (b) opening `GET /api/lyrics/{id}`
  beyond `require_owner`, which belongs to the lyrics stream that closed it (`FEAT-lyrics-annotations`
  §6.9 O2). This RFC **consumes** both and must not make either change itself — an auth-guard or
  scope change smuggled into a playback step is exactly the pattern CLAUDE.md forbids.
- **Depends on**: `docs/rfcs/ARCH-entity-interaction-v2.md` Steps 1–3 (canonical entity identity +
  the drag-payload contract + the interaction-conflict prototype) — gates this RFC's Step 8 only.
  Exactly two surfaces in the product are draggable today.
- **Supersedes** (named precisely in *Comparison table*): `FEAT-my-buckit-artist`'s "playback-queue
  bucket" non-goal and its closed two-value bucket-`type` enum; `FEAT-pocket-buckit` D8's
  archive-by-default deletion and mandatory 1:N expansion confirmation, **for this bucket only**.
- **Related, unchanged**: `docs/archive/done/rfcs/FEAT-pocket-buckit.md` (canonical Buckit product
  model — D2 generalized membership, D7 tree/projection, D8 duplicate policy, OQ10 hybrid queue),
  `docs/archive/done/rfcs/FEAT-spotify-streaming-playback.md`,
  `docs/archive/done/rfcs/FEAT-lyrics-viewer-playback.md` (owns the in-viewer transport and the
  Spotify-queue **read**; its `queueJump.ts` tail semantics are reused here).

---

## Goal

Every user with eligible Spotify playback permission has exactly one **Playback Bucket** — a
system-owned bucket that is created for them automatically, cannot be deleted or duplicated, and can
be moved anywhere inside Pocket. Its ordered item list **is** the queue: dropping a track or an album
(albums expand into their tracks, in album order) either starts playback immediately (nothing
current) or appends to the queue (something playing or paused); artists are rejected. Completed items
are removed automatically and removing the current item advances to the next. The same playback
session is rendered by two components — a **mini-player** while the bucket sits in Pocket, and an
**expanded player** when it is taken outside — sharing one current track, queue, position and device
state, each offering entry to lyrics, track information and album information. Exactly one browser tab
owns playback at a time; other tabs mirror its state read-only and can take ownership explicitly or
after the owning tab dies. Playback itself is not rebuilt: every play call goes through the shipped
`play(intent)` ladder, its device picker, its Media Session binding and its remote-first policy.

## Non-goals

- **No new playback mechanism.** No second SDK loader, no second token seam, no second transport
  wrapper. `myblog_front/src/lib/spotifyPlayback.ts` stays the only SDK/token owner and `play(intent)`
  the only play entry. If a play path is missing, it is fixed in `FEAT-member-player`, not forked here.
- **No writes to Spotify's own queue for this feature.** `queueTrack()` (member-player 6c,
  `POST /v1/me/player/queue`) exists and stays for the "다음에 듣기" affordance, but it is **not** the
  Playback Bucket's mechanism. Pushing our rows into Spotify's queue would manufacture exactly the
  divergence this RFC refuses to reconcile. The Buckit queue plays by re-issuing its own tail — see
  *Target state T2*.
- **No reverse synchronization of Spotify's external queue.** `GET /v1/me/player/queue` is read for
  *display* today (`components/member/lyrics/queue.api.ts`) and may be read here, but this RFC never
  reconciles it back and never treats a divergence as an error to repair. The Buckit list is
  authoritative for what *we* enqueued; Spotify is authoritative for what is *playing*.
- **No polling.** D28 is upheld unchanged: queue and playhead state advance from events and from
  reads that are 1:1 with a user action or a track boundary, never from a timer loop.
- **No second playback queue and no user-creatable playback buckets.** Exactly one per user,
  system-owned, `type='playback'`.
- **No "save queue to playlist" bridge** (a FEAT-pocket-buckit OQ10 seam) — kept possible, not built.
- **No cross-device resume.** The playhead stays client-side (OQ10's hybrid model, retained). One tab
  owns playback; a different *device* is Spotify Connect's job, reached through the shipped device
  picker.
- **No summary/snapshot bucket work** (FEAT-pocket-buckit D4 stays unbuilt and out of scope).
- **No change to the lyrics privacy boundary.** `GET /api/lyrics/{id}` is `require_owner`
  (FEAT-lyrics-annotations §6.9 O2). This RFC surfaces a lyrics entry; whether it is reachable for
  non-owner members is **OQ4**, not decided here.
- **No `openAlbum` overlay redesign**, no album-detail unification, no track-row rewrite — that is
  `ARCH-entity-interaction-v2`'s scope. This RFC consumes its payload contract.

---

## Current state

Verified 2026-08-03 against **`origin/main` of each repo**, not the local checkout.

> **Audit note, recorded because it changed conclusions.** The first pass of this audit read the
> workspace's local checkout, which was ~20 commits behind `origin/main`, and `myblog_front` which
> was 9 commits behind. On that stale tree the play ladder, device picker and Media Session did not
> exist, and this RFC was drafted as *blocked* on FEAT-member-player Step 5. They shipped 2026-08-02.
> Every claim below is re-measured against `origin/main` (`git -C <repo> show origin/main:<path>`).

### The playback layer this RFC consumes — shipped, verified

`myblog_front/src/lib/spotifyPlayback.ts` — the only SDK/token owner. Since front #334/#336/#340/#342:

| Capability | Symbol | Notes |
|---|---|---|
| Unified play ladder | `play(intent): Promise<PlayOutcome>` | rung 1 remote (no `device_id`, default) → rung 2 in-page `'Buckit'` device → rung 3 notice. Attempt-then-fallback on the 404, **not** a devices probe — one request on the happy path, D28 by construction |
| Play intents | `PlayIntent = {kind:'album'\|'track'\|'context'\|'uris'}` | `'uris'` carries an explicit track list and **replaces the context — "always send the whole tail"** |
| Outcome | `PlaySuccess {rung, degraded, message}` / `PlayFailure {reason, status, httpStatus, message}` | `degraded: true` on rung 2; `IN_PAGE_MESSAGE` = `'이 브라우저에서 재생 중 (음질 제한)'` |
| Device picker | `listDevices()` / `transferPlayback(id, {raiseInPageFirst})` | read-on-open, never polled; `raiseInPageFirst` exists because the in-page device does not exist until the SDK connects |
| Media Session | `lib/mediaSession.ts` | **rung 2 only** — on rung 1 the real device's own app owns the OS surface |
| Navigation persistence | `astro:before-swap` in-place `<body>` swap (`layout.astro`) | prod-measured 3 hops / 0 reloads; `/write` rejoined the shell in Step 5b |
| Transport | `sendPlayerCommand(cmd)` | `play\|pause\|seek\|next\|previous\|play-context\|play-uris`; **dispatches `MYBLOG_PLAYBACK_CHANGED`** for transport kinds since front #342 (modes excluded) |
| Modes | `sendPlaybackMode(cmd)` | shuffle / repeat / volume (6e) |
| Spotify-queue append | `queueTrack({trackId})` | 6c "다음에 듣기". **Tracks only** — `POST /me/player/queue` requires a track/episode uri, so an album would be unbounded fan-out. Deliberately **no ladder**: queueing onto a non-playing device is meaningless, so its 404 stays a 404 |
| Liked | `getTrackLiked` / `setTrackLiked` | free-account safe; library 403 never degrades transport |

**Consequence for this RFC's design**: the Buckit queue needs no new Spotify primitive. Playing from
position *n* is `play({kind:'uris', uris: [tracks from n to the end]})` — which is exactly the shape
`FEAT-lyrics-viewer-playback` Step 3 arrived at, including its hard-won lesson that a lone-track
fallback silently drops the tail. `lib/queueJump.ts` already encodes that chain.

**Two live constraints carried in verbatim:**

- **Member scope does not include `streaming`.** `components/member/integrations.api.ts:55` —
  `SPOTIFY_SCOPES = 'user-read-currently-playing user-read-recently-played user-read-playback-state
  user-modify-playback-state user-library-read user-library-modify'`. So a connected Premium **member**
  can drive **rung 1** (remote-control an active device) but cannot raise **rung 2** (in-page device).
  Eligibility is therefore already two-tiered → **OQ1**.
- **The capability matrix is binding.** `@lib/playerCapabilityMatrix` is the single source since
  front #337, and FEAT-member-player's rule stands: every new player feature amends it **in the same
  PR**. This RFC inherits that.

FEAT-member-player's own remaining items are **owner spot-checks** (the five other play surfaces
individually, two-way device switching, OS media keys, `/write` audio by ear) — none of which block
this RFC, and none of which this RFC may quietly claim to close.

### Buckets today — the model this bucket must fit

`myblog_shared_db/src/myblog_shared_db/models.py:542-770` (shared_db is **at** `origin/main`):

- `review_buckets.user_id` **NOT NULL** FK `users(id)` since V40/V42 — per-user ownership is real.
- `kind` — free TEXT, system/role axis: `'review'` (default), `'spotify_library'`, `'to_listen'`.
- `type` — closed CHECK enum **`('general','artist')`** (FEAT-my-buckit-artist V32), member-composition
  axis, set once at create, immutable in v1.
- **Per-user singleton precedent exists twice**: `idx_review_buckets_single_done` and
  `idx_review_buckets_single_spotify_library`, both `unique` partial indexes on `user_id`, re-scoped
  from table-wide to per-user by V40. Exactly the shape "one Playback Bucket per user" needs, and it
  satisfies FEAT-pocket-buckit OQ12 (no *global* singleton).

`review_bucket_items`:

- `item_type` CHECK ∈ `('album','track','review','playback','snapshot','artist')`.
- Per-kind partial uniques for `album` / `track` / `review` / `artist`.
  **`playback` and `snapshot` have none — duplicates are already allowed** (D8). "Duplicate tracks are
  allowed" needs no schema change.
- `position` drives ordering; `PUT /api/buckets/reorder` + `insertAlbum` already persist it.

**Missing entirely: system-bucket protection.** `BucketService.delete_bucket`
(`myblog_backend/app/services/bucket_service.py:464`, re-verified at `origin/main`) is six lines with
**no kind/type guard** — any bucket the caller owns is deletable, including `spotify_library` and
`to_listen`. There is no `isSystem` concept in the frontend either (grep: 0 hits). "Cannot be
deleted" is new work, and closing it also closes a latent hole on the two existing system buckets.

### Drop routing today

`myblog_front/src/lib/boardDnd.ts` (102 lines, unchanged at `origin/main`) — the single source of
drop semantics, shared by the board card, the trash dock and the reverse-DnD Pocket bridge:

- `canAcceptAlbumDrag(bucket, it)` — **`if (bucket.type !== 'artist') return true`**. A General bucket
  accepts everything. A third type needs a third branch.
- `routeAlbumDrop(target, it, ops)` — the Artist branch expands an album/track source into its
  **credited artists** via `ops.expandSource`. **There is no album → tracks expansion anywhere in the
  product**; the only expansion that exists goes to artists.
- `DndItem` (`:23`) already carries `albumId`, `trackId`, `artistId`, `srcItemType` — enough identity
  for a playback drop without a contract change.

**Drag sources are two surfaces only**, re-verified at `origin/main`: `BucketBoard.tsx:569` (member
chip), `:965` (bucket node), `PocketTray.tsx:435,589` (tray member). Nothing else in the product is
draggable — which is why `ARCH-entity-interaction-v2` gates Step 8 rather than being a nicety.

### The tray's leaf model already has the seams

`lib/pocketBuckit/leaf.ts` declares `PocketAction = 'add' | 'queue' | 'play' | 'summarize'` and
`PocketLeaf.ordered?: boolean` — both **declared and unused**: `actionFor()` unconditionally returns
`{ verb: '담기', action: 'add', accepts: '앨범' }` for every kind. The Playback Bucket is the first
consumer of `action: 'queue'` and of `ordered`. `PocketLeaf.n` is `albums.length` and `recent` is
`slice(0,3)` — a queue leaf needs the current track, not three recent covers.

### Two React roots, no shared context; no multi-tab coordination

`PocketBuckit` (layout-mounted) and `BucketBoard` (inside `SelfDashboard`) are separate React roots
communicating only through the `bucketStore` observable singleton and `pb:*` window CustomEvents; the
app-wide `AlbumOverlay` is a third root on `ent:*` events. "Two forms, one session" must therefore
live in a store + events, not React context.

Repo-wide: **zero** `BroadcastChannel`. The only cross-tab signal is `window.addEventListener('storage')`
in `scripts/header.client.ts` (auth). Single-tab playback ownership is entirely new.

---

## Target state

### T1 — the bucket

- A third `type` value: **`playback`**. The closed-enum *principle* of FEAT-my-buckit-artist is
  retained (still not user-extensible); the two-value set is superseded by a three-value set.
- `kind='playback_queue'` marks it system-owned (the free-TEXT role axis, matching
  `spotify_library` / `to_listen`).
- **Exactly one per user**: `idx_review_buckets_single_playback` — `unique` partial index on
  `user_id WHERE kind = 'playback_queue'`, verbatim the V40 per-user idiom. OQ12 honored.
- **Auto-created**, lazily and idempotently, on the first bucket-tree read once the user is
  playback-eligible. Not a migration backfill (see Step 2 rationale).
- **Non-deletable, non-duplicable, position-movable.** Enforced server-side (the client guard is
  cosmetic): `delete_bucket` rejects `kind IN ('playback_queue','spotify_library','to_listen')` with
  409; `create_bucket` rejects `type='playback'` from user input; `move_bucket`/`reorder` are
  untouched, so position and parent stay fully user-controlled.
- **Eligibility (owner decision 2026-08-03): members get BOTH rungs.** The member OAuth scope set
  opens to include `streaming`, so a connected Premium member can remote-control an active device
  (rung 1) *and* raise this tab as the in-page device (rung 2), exactly as the owner can. Free
  accounts still fail rung 2 at `account_error` → `unsupported`, which the shipped ladder already
  handles. The scope change itself is `FEAT-member-player`'s to make (see *Prerequisite* above).
- **Losing Spotify permission preserves bucket and queue.** Eligibility gates *playing*, never
  *existing*. A member whose token route returns 404/503, or whose transport probe 403s, keeps the
  bucket, keeps every row, and sees a disabled player with the reason and the fix — the
  `playerCapabilityMatrix` copy is the source for that sentence, not a new string.

### T2 — the queue semantics

- **Members**: `item_type='playback'` rows carrying `track_id`, ordered by `position`. Duplicates
  allowed (no partial unique on that kind — see Step 2 for why not `'track'`).
- **Accepted drops**: `track` → one row. `album` → expands to its tracks **in album order**, appended
  as N rows. `artist` → **rejected** at drag-over (no glow, no optimistic insert) and again on the
  server (400) — the Artist-bucket rejection idiom, inverted.
- **Drop is a playback action, not just a write**:
  - no current track → the first dropped track starts immediately;
  - a track is playing **or paused** → append only, never interrupt;
  - the write lands first, the play call follows; a play failure never rolls back the write.
- **Playing is re-issuing our own tail.** Starting at position *n* is
  `play({kind:'uris', uris: [n … end]})` through the ladder — no writes to Spotify's queue, so no
  divergence to reconcile, and the "always send the whole tail" rule is satisfied by construction.
  `lib/queueJump.ts`'s existing chain is the reference.
- **Completion removes**: when a track finishes, its row is deleted and the next becomes current.
- **Removing the current item advances** to the next (and starts it if we were playing).
- **Failures preserve.** Any play/transport failure leaves the queue exactly as it was and surfaces an
  *actionable* error, reusing the shipped taxonomy verbatim rather than inventing one:
  `PlayFailure.reason ∈ no-capability | unresolvable | unavailable | transient | token` plus
  `StreamingStatus ∈ dormant | disconnected | unauthorized | unsupported | error`. Each already has a
  written Korean sentence; none becomes a generic "재생 실패".

### T3 — one session, two forms

One **playback session store** (`lib/playback/session.ts`), a framework-agnostic observable singleton
in the `bucketStore` idiom, holding: current item, queue (projected from `bucketStore`), position
anchor (`@lib/clockEstimate`, already shared with the lyrics viewer), play state, rung + `degraded`,
device, capability tier, and tab-ownership state. It subscribes to `MYBLOG_PLAYBACK_CHANGED` — which
now fires for transport commands (#342) as well as Connect plays. Both forms are thin renderers over
it; neither owns state, neither talks to Spotify directly.

- **Mini-player** — the Playback Bucket's representation inside Pocket, replacing the generic leaf
  chip/drawer for this one bucket: current track identity, transport, a compact queue, and the three
  entries. First real use of `PocketAction='queue'` and `PocketLeaf.ordered`.
- **Expanded player** — the form when the bucket is taken outside Pocket. **Which form is not decided
  here** — Step 6 compares in-page expansion, a floating player, and a dedicated player surface side
  by side before one is picked (**OQ2**).
- Both forms expose **lyrics**, **track information**, **album information**. Album info reuses
  `openAlbum` (`lib/entityEvents.ts`) — no new album surface. Track info and the lyrics entry route
  through `ARCH-entity-interaction-v2`'s canonical track behavior; the lyrics entry's reachability for
  non-owner members is **OQ4**.
- Rung 2 must **say it is degraded** (`PlaySuccess.degraded` / `IN_PAGE_MESSAGE`) — the shipped ladder
  makes this the caller's obligation, and both forms are callers.

### T4 — single-tab playback ownership

- Ownership is a **lease** in `localStorage` (`pb:playback-owner` = `{tabId, heartbeatAt}`), mirrored
  over `BroadcastChannel('myblog:playback')`, with the `storage` event as fallback.
- The owning tab renews on a heartbeat; non-owning tabs render **the same session state, read-only**,
  with an explicit "이 탭에서 재생하기".
- **Explicit transfer**: a non-owner claiming the lease takes it; the previous owner demotes to mirror
  on the next channel message. It does **not** stop the music on rung 1 — the audio is in neither tab.
- **Owner-tab failure recovery**: a stale lease is claimable by any tab. The heartbeat interval and
  staleness timeout are **measured, not guessed** — a backgrounded tab is throttled by the browser, so
  a naive timeout lets tabs steal ownership from a merely-hidden owner (Step 7).
- Ownership matters **only for rung 2**. On rung 1 every tab is equally a remote control, so the lease
  governs who owns the SDK device and issues transport, not who may see or edit the queue. This falls
  out of the shipped ladder's own rung-2-only framing of Media Session and persistence.

---

## Comparison table — existing decision / retained / superseded / new

| # | Existing decision | Source | Verdict | What this RFC does |
|---|---|---|---|---|
| 1 | Generalized membership `item_type` on `review_bucket_items` | pocket-buckit D2 | **Retained** | Queue rows are ordinary typed members; no new membership table |
| 2 | Duplicate policy is bucket-type-specific; playback/queue **allow duplicates** | pocket-buckit D8 | **Retained** — now load-bearing | Schema already permits it |
| 3 | Queue = **hybrid** — server-persisted ordered membership, client-ephemeral playhead | pocket-buckit OQ10 | **Retained, promoted to the spine** | "The item order is the Buckit-owned queue" is OQ10 made user-visible |
| 4 | Tree canonical; Pocket is its projection; bucket position is user-controlled | pocket-buckit D7 | **Retained** | Movable position falls out of it |
| 5 | Bucket deletion **defaults to archive** (recoverable) | pocket-buckit D8 | **Superseded for this bucket only** | Not archivable and not deletable at all. Every other bucket unchanged |
| 6 | **Mandatory confirmation** on cross-type 1:N expansion (album → tracks) | pocket-buckit D8 | **Superseded for an intentional Playback-Bucket drop** (default; **OQ3** sets the ceiling) | A drop onto a queue *is* the intent to hear the album. Undo replaces confirm |
| 7 | Bucket `type` is a **closed enum of two**; further types "stay deferred non-goals" | my-buckit-artist | **Superseded** (enum), **retained** (principle) | Third value `playback`; still closed, still not user-extensible |
| 8 | "**playback-queue bucket**" is an explicit product non-goal; "playback stays a future single transient global player, **separate from Buckit**" | my-buckit-artist non-goals | **Superseded — the central reversal of this RFC** | The queue becomes a first-class bucket. Recorded there as a dated forward pointer, not an edit |
| 9 | Artist buckets reject non-artist sources at drag-over **and** re-check on the server | my-buckit-artist | **Retained as the pattern** | Reused inverted: this bucket rejects artists, same two-layer shape |
| 10 | `expandSource` expands an album/track into its **credited artists** | my-buckit-artist / `boardDnd.ts` | **Retained, joined by a sibling** | Album → **tracks** expansion is new; it does not replace album → artists |
| 11 | No global-singleton index shape; per-user partial uniques only | pocket-buckit OQ12 + V40 | **Retained** | `unique (user_id) WHERE kind='playback_queue'` |
| 12 | **D28 — no polling**, ever | member-player | **Retained unchanged** | Events + action-coupled reads only. The shipped ladder already holds this by construction |
| 13 | **D1 capability tiers**, detected by 403-probe, no `product` dependency | member-player | **Retained** | "Eligible playback permission" *is* the existing probe |
| 14 | **`play(intent)` ladder / device picker / Media Session / persistence / remote-first** | member-player Step 5, 5b | **Retained — shipped, and consumed as-is** | Verified present at `origin/main` 2026-08-03. **Not** a blocker; the first draft of this RFC said otherwise from a stale checkout |
| 15 | Step 5 shipped with the member `streaming` scope **closed** | member-player + `integrations.api.ts:55` | **Open conflict, sharpened** | A member gets rung 1 only; rung 2 is owner-only → **OQ1** |
| 16 | Every new player feature amends the **capability matrix in the same PR**; the matrix has one source (`@lib/playerCapabilityMatrix`) | member-player Step 7 | **Retained as process** | Each player step here amends it |
| 17 | `sendPlayerCommand` dispatches `MYBLOG_PLAYBACK_CHANGED` for transport kinds (modes excluded) | lyrics-viewer-playback OQ4, closed front #342 | **Retained — and it is why the session store works** | The session store subscribes. The first draft listed this as an open gap; it closed 2026-08-03 |
| 18 | `queueTrack()` writes to **Spotify's** queue; tracks only; no ladder | member-player 6c | **Retained for "다음에 듣기"; explicitly NOT this bucket's mechanism** | Using it would manufacture the divergence the no-reverse-sync rule forbids |
| 19 | Spotify's external queue is **display-only**; `uris` replaces the context so a fallback must carry the tail | lyrics-viewer-playback Step 3 | **Retained and generalized** | Becomes this RFC's non-goal + the `{kind:'uris'}` play mechanism |
| 20 | `GET /api/lyrics/{id}` is `require_owner` | lyrics-annotations §6.9 O2 | **Retained** | Not overridden. Member reachability = **OQ4** |
| 21 | rule #9 — no synchronous Spotify call on a user-facing backend endpoint | CLAUDE.md | **Retained** | All Spotify calls stay client-side; the only server hit is the async token mint |
| — | **System buckets cannot be deleted** | — | **NEW** | `delete_bucket` has no guard today. Closes the hole for `spotify_library`/`to_listen` too |
| — | **Auto-creation** of a bucket the user did not make | — | **NEW** | `spotify_library` is created on first sync; nothing is created on eligibility |
| — | **Album → tracks in album order** | — | **NEW** | Never built; the only expansion goes to artists |
| — | **Drop is a transport action** (start-if-idle / append-if-busy) | — | **NEW** | Every drop today is a pure write |
| — | **Auto-removal on completion; remove-current advances** | — | **NEW** | No membership row has ever been deleted by playback progress |
| — | **Single-tab playback ownership + transfer + failure recovery** | — | **NEW** | Zero `BroadcastChannel` in the repo; no tab coordination of any kind |
| — | **Two forms over one session** (mini / expanded) | — | **NEW** | The tray drawer and the player bar are unrelated components today |
| — | **A bucket that renders as a player** | — | **NEW** | `PocketAction='queue'`/`'play'` and `PocketLeaf.ordered` are declared-but-unused seams |

---

## RFC boundary — why two RFCs, and why not one, three, or none

**Two successor RFCs.** The default split holds, and the audit supports it rather than merely
permitting it:

1. **Different repos, different blast radius.** This RFC is cross-repo: `myblog_shared_db` (a
   migration), `myblog_backend` (guards, auto-create, expansion, `openapi.json`), `myblog_front`.
   `ARCH-entity-interaction-v2` is, on the evidence of its two predecessors (both explicitly
   "front-only"), a frontend contract RFC. Merging them would put a schema migration and a
   presentation-contract sweep under one Status line, and rule #4 would then serialize work with no
   ordering relationship.
2. **Different kinds of decision, and of verification.** This one is a product state machine plus
   Spotify integration, verified with live sessions and a real device. v2 is canonical identity and
   interaction vocabulary across ~15 surfaces, verified with a CDP surface matrix and a mobile gesture
   prototype.
3. **The entity work is genuinely broader than playback.** Canonical IDs/URLs, the album-detail
   revisit and the drag payload apply to every album/track/artist representation. Scoping them inside
   a playback RFC would silently narrow them to "whatever playback needed".
4. **v2 is a real prerequisite for one step, which argues for two RFCs rather than one.** Only two
   surfaces are draggable today. Making that a visible dependency edge is the point; folding it in
   would hide it.

**Rejected alternatives.** *One combined RFC*: no shared verification, no shared rollback, and rule #4
would serialize independent work. *Three RFCs (splitting the system-bucket schema out)*:
`FEAT-my-buckit-artist` shipped a strictly larger schema change as one RFC; one migration plus two
guards does not clear the RFC bar alone. *Folding the player forms into `FEAT-member-player`*: that
RFC's Step 5/5b/6/7 are shipped and its remaining items are owner spot-checks — appending a
bucket-shaped feature would reopen a finished scope and make a future "the sound stopped" ambiguous
across three concerns instead of two (the reason its own 5b was split out).

---

## Steps

One step per session (hard rule #4). Steps 1–7 have no external gate; Step 8 is gated on
`ARCH-entity-interaction-v2`.

### Step 1 — this RFC + plan rows + index + cross-references (docs-only)

This document, `ARCH-entity-interaction-v2.md`, two `plan.md` rows, two `docs/rfcs/README.md` index
entries, and dated forward-pointer blockquotes on the affected archived RFCs (house style:
`FEAT-pocket-buckit` already carries three `> **SUPERSEDED …**` blocks — pointers are added,
decisions are never edited).

**Verification**: doc review against `TEMPLATE.md`; `git diff --stat` shows only `docs/`.

---

### Step 2 — `shared_db`: the `playback` bucket type + per-user singleton (rule #4 schema step)

> ✅ **SHIPPED 2026-08-03** — shared_db #72, `V51__playback_bucket.sql`. Applied to Neon **prod**
> and to the Neon **test branch** (the latter was current through V50, so Step 3's integration tests
> do not start from drift). Dry-run confirmed the index actually rejects a second queue for the same
> user before the apply; live re-verify on a fresh connection: `indisunique=t indisvalid=t`, 6 bucket
> rows, 0 playback rows. **Do not re-apply.** Everything below is the original plan, unedited.

`V<N>__playback_bucket.sql` (own `BEGIN…COMMIT`): widen `ck_review_buckets_type` to
`('general','artist','playback')`; add `idx_review_buckets_single_playback` —
`UNIQUE (user_id) WHERE kind = 'playback_queue'`. **No data backfill**: prod has 4 users of whom one
is playback-eligible, so a backfill would create three buckets nobody can use, and auto-creation
(Step 3) is idempotent anyway. Regenerate `_generated_schema.sql` **and** edit
`tests/canonical_schema.sql` in the same PR or `test_schema_parity.py` fails; bump `pyproject` + tag.

**Decision recorded here, not deferred**: queue rows are `item_type='playback'`, **not** `'track'`.
`'track'` carries `uq_review_bucket_items_track`, which would **reject the duplicate tracks this
bucket must allow**; widening that index would touch every other bucket. `'playback'` already exists,
already allows duplicates, and its serializer path already ships (the member-authoring follow-on
renders playback tiles off the shared `TrackBrief`).

**Gate**: applied to Neon prod on the owner's go-ahead — **not human-only**. Hard rule #3 restricts
*rollback* migrations; a forward migration is applied by Claude with approval, and there is precedent
(V30/V31, 2026-06-24, "Claude, owner-approved"; V50, 2026-07-31). Procedure, which is what the gate
actually enforces: `BEGIN…ROLLBACK` dry-run against prod first, then apply (each `V{N}__` file wraps
its own `BEGIN…COMMIT` — memory `reference-migration-file-self-commits`), then re-verify the CHECK +
index live, **before** the backend pin bump (`reference-shared-db-cross-repo-rollout`). Connection
string via SSM `/myblog/backend` (`reference-database-url-psql`).

**Rollback**: `DROP INDEX` + restore the two-value CHECK — trivial while no `type='playback'` row
exists, **not** once one does, so it stays in its own migration.

---

### Step 3 — backend: auto-create, delete/create guards, album→tracks expansion

> ✅ **SHIPPED 2026-08-03** — backend #149. Two things below turned out to be wrong when checked
> against the code, and are corrected in place with the original text kept alongside:
>
> 1. **No new API Gateway route, and no `terraform apply`.** The plan called the expansion "a new
>    authed POST", but the sibling it names — `expand_artist_source` — is **not** a separate
>    endpoint: it rides `POST /api/buckets/{id}/items` with `item_type='artist'` + `source_album_id`,
>    and `AddBucketItemRequest` already carries the `source_*` fields. Album expansion follows the
>    same idiom (`item_type='playback'` + `source_album_id`), so `buckets_items_post`
>    (`infra/apigateway.tf:410`) already covers it. Owner chose this shape 2026-08-03. The route
>    probe (401=live vs 404=missing) is therefore moot — the route was live already.
> 2. **There is no disc-number column.** The plan said "confirm the exact ordering columns —
>    disc/track number"; the answer is that `tracks` carries `track_no` only. Order is
>    `track_no ASC NULLS LAST` + `created_at`/`id` as a stable tiebreak, matching the canonical
>    album-track order already used by `myblog_music`'s `track_repo`. Consequence, recorded rather
>    than hidden: **multi-disc albums interleave**, because Spotify's `track_number` restarts on each
>    disc. That gap is shared by every album-track read in the product and is not introduced here;
>    closing it needs a `disc_no` column + backfill, which is not this RFC's.
>
> Also swept in the same PR, beyond the delete guard the plan named: the **publish** guard had the
> identical per-kind drift (`is_public` rejected `spotify_library` only), so both now read one
> `SYSTEM_BUCKET_KINDS` tuple. The type gate was extracted to `_assert_item_type_allowed` so the
> single-row and expansion paths cannot drift apart either.
>
> Everything below is the original plan, unedited.

- `get_or_create_playback_bucket(db, user_id)` — idempotent, mirroring
  `get_or_create_spotify_library_bucket`; called from the bucket-tree read.
- `delete_bucket` — reject `kind IN ('playback_queue','spotify_library','to_listen')` → **409**.
  This is a **pattern fix, not a feature**: the same missing guard leaves the two pre-existing system
  buckets deletable. Sweep named in the PR body (CLAUDE.md pattern-bug rule).
- `create_bucket` / `update_bucket` — reject `type='playback'` from user input (extend the existing
  immutable-type rule).
- `add_item` type gate — extend the existing `BucketTypeError` branch: a `type='playback'` bucket
  accepts `item_type='playback'` (with `track_id`) only; **artist → 400**; album → 400 on the
  single-row path (albums go through expansion).
- `expand_album_tracks(bucket_id, album_id)` — appends the album's tracks **in album order**
  (confirm the exact ordering columns — disc/track number — at implementation and **assert the order
  in the test**; do not trust insertion order). Sibling of `expand_artist_source`, not a replacement.
- `openapi.json` exported **in this PR**; the expansion endpoint is a new authed POST → **one new
  `infra/apigateway.tf` route** (404 until applied; probe `curl -X` 401=live vs 404=missing).

**Verification**: `pytest` + a real-engine integration test for expansion ordering and the 409 delete
guard (mocks cannot prove index/CHECK behavior — memory `feedback-sa-session-lifecycle-mock-blind`);
`openapi` diff committed; route probed live.

**Gate**: `terraform apply` for the new route on the owner's go-ahead — again not human-only. Hard
rule #6 bans `-target` without a go-ahead and requires a **full plan**; stop on unexpected drift.
Precedent: the `worker-isrc-backfill` rule was applied this way (2026-07-26, "오너 승인으로
`terraform apply` 실행, 3 add/0/0"). Then prod smoke quoted in the PR comment.

---

### Step 4 — workspace: regenerate the merged contract

> ✅ **SHIPPED 2026-08-03** — workspace #811. `tools/merge_openapi.py` over backend `6d5f02d` +
> music `fa2e70d`: **88 paths, 155 schemas**, +39 lines and nothing removed. The whole diff is
> three things, and each one confirms a Step-3 claim rather than adding to it:
>
> - `Backend_TrackExpansion` + `Backend_TrackExpansionResponse` — the album-drop response shape.
> - `DELETE /api/buckets/{bucket_id}` gains a **409** response ("System bucket — cannot be deleted"),
>   so the delete guard is now contract, not just behavior.
> - `POST /api/buckets/{bucket_id}/items` gains a **third** union member next to `BucketItemResponse`
>   and `ArtistExpansionResponse` — which is exactly what the front discriminates on in Step 5.
>
> **Zero path changes**, which is the independent check on Step 3's correction: had album expansion
> really been a new authed POST, a new path would appear here and `infra/apigateway.tf` would be out
> of date. It did not, and it is not.
>
> The front `api.gen.ts` regen (front #344) went out in the **same session, right behind the
> workspace merge** — not as an early start on Step 5, but because the front deploy gate diffs
> `api.gen.ts` against workspace `main`, so the two are one change split across two repos
> (`feedback-frontend-api-gen-sync`). Order held: workspace merged first
> (`reference-workspace-contract-merge-order`). Nothing else from Step 5 was touched.

`tools/merge_openapi.py` → `docs/contracts/openapi.json`, merged **before** the front regen
(`reference-workspace-contract-merge-order`).

---

### Step 5 — front: the bucket, the drop rules, the queue model (no player yet)

> ✅ **SHIPPED 2026-08-03** — front #345. The queue is a correct, orderable,
> duplicate-tolerating list and **not one note has been played**, which is what makes a
> Step-6 regression unambiguously a player bug.
>
> Verified in a real browser against **prod data** (dev server → local proxy rewriting the
> smoke JWT), not a synthetic harness:
>
> - **album → 12 rows in album order.** Dropping *OK Computer* expanded to Airbag →
>   Paranoid Android → … → The Tourist, exactly the canonical order, from one POST.
> - **duplicate track drop succeeds** — 12 → 13 rows, Paranoid Android now present twice,
>   appended at the tail, flashed 추가 (not 이미 담겨 있어요; there is no 409 path here).
> - **artist rejected, muted-not-hidden, no reflow.** Drag-over is not accepted
>   (`defaultPrevented === false`) and **zero writes** are issued. In the tray the queue
>   chip goes `opacity 0.38` with the reason `재생 대기열 — 트랙 · 앨범만 받아요` while
>   staying visible, and every chip's `x/y/width` is byte-identical before / during /
>   after the drag — the D-series no-reflow invariant, measured rather than assumed.
> - **delete refused, without the blink.** The ⋯ menu offers only 이동 / 중첩 on the queue
>   (삭제 present on a normal crate); the trash dock answers 시스템 버킷은 삭제할 수 없어요
>   and opens no confirm dialog. This closes the prod observation carried since Step 3
>   (the row vanished optimistically and then came back on the 409 refresh).
> - **position move persists** — nested under a user crate and back out, server-confirmed,
>   with all 13 rows intact. Non-deletable and position-movable are independent (T1).
>
> **`api.gen.ts` was NOT regenerated here** — it shipped in Step 4 (front #344) because the
> front deploy gate diffs it against workspace `main`. The line below is stale; this step
> only *consumed* `Backend_TrackExpansionResponse`.
>
> **Two things this step found that the plan did not predict:**
>
> 1. **`canAcceptAlbumDrag` has an in-repo twin** — `lib/pocketBuckit/boardDnd.ts`'s
>    `boardDragAccepts`, which the tray uses because the Pocket island cannot read the
>    board's live `dnd` (two React roots). A playback branch in only one of them would have
>    let a tray chip preview an acceptance the board then refuses. Both were changed in the
>    same PR and a table-driven test now pins them together case-for-case.
> 2. 🔴 **The Step-3 delete guard is bypassable, and this step's client guard cannot close
>    it** (see `BUG-playback-system-bucket-cascade` in `plan.md`). `review_buckets.parent_id`
>    is `ON DELETE CASCADE` and `delete_bucket` checks only the *target's* own `kind`, so
>    nesting a system bucket under a user crate and deleting that crate removes it. Measured
>    on the test account: direct `DELETE` → **409**, but nest-then-delete-parent → **204**,
>    and the Playback Bucket came back with a new id and 0 items. Reachable entirely through
>    shipped UI (이동 / 중첩, then 삭제) and it affects `spotify_library` and `to_listen` too.
>    **Deliberately not fixed here**: the fix belongs in `delete_bucket` (reject when the
>    subtree contains a system bucket), and adding a client-only guard would be a fail-open
>    mirror — it would hide the hole while the API stayed open.

`api.gen.ts` regen. `boardDnd.ts` gains the third branch: `canAcceptAlbumDrag` rejects an artist
source onto a `type==='playback'` target (drag-over: **stays in place**, muted, with a reason — the
D-series invariant that the tray never reflows mid-drag); `routeAlbumDrop` routes album →
`expandAlbumTracks`, track → append. `leaf.ts` `actionFor()` becomes kind-aware and finally returns
`{verb:'재생 대기열에 추가', action:'queue', accepts:'트랙 · 앨범'}` with `ordered: true`. Client-side
delete guard (cosmetic; server authoritative). Queue projection off `bucketStore` — **no second store
for the item list**.

**Deliberately excluded**: any play call. The queue is a correct, orderable, duplicate-tolerating list
before a single note is played, so a Step-6 regression is unambiguously a player bug.

**Verification**: `pnpm lint` (antfu, before commit) + `pnpm exec astro check` (Node 20) + `pnpm test`;
real-browser CDP — album drop expands to N rows in album order, duplicate track drop succeeds, artist
drag-over is muted-not-hidden and the tray does not reflow, delete is refused, position move persists.

---

### Step 6 — front: the two player forms over one session

`lib/playback/session.ts` + the mini-player + the expanded player. **Every play/transport call goes
through the shipped ladder** — a review gate for this step is a grep proving no `api.spotify.com`
string was added outside `lib/spotifyPlayback.ts`.

Start-if-idle / append-if-busy; play-from-*n* as `play({kind:'uris', …tail})`; auto-remove on
completion; remove-current advances; the shipped failure taxonomy rendered as one sentence + one
action per outcome; rung 2 labelled degraded. Lyrics / track info / album info on both forms.
**Capability matrix amended in the same PR** (`@lib/playerCapabilityMatrix`).

**Before the UI is written**: Step 6 opens with the **OQ2 comparison** — in-page expansion vs floating
player vs dedicated surface, rendered side by side at realistic scale (`frontend-design` skill; the
FEAT-pocket-buckit Design Atlas is this repo's precedent for comparing UI options). The owner picks;
the pick is recorded in the Decisions log before implementation.

**Verification**: real-browser clickthrough (DoD) — drop into an empty queue starts audio; drop while
playing appends without interrupting; drop while **paused** appends without resuming; completion
removes the row and advances; removing the current item advances; a forced 404/403 leaves the queue
intact with the right sentence; both forms reflect one session; mobile 390 via `emulate`.

**Harness requirement, not optional**: the stub must model Spotify's asynchronous apply (≥1.2 s).
`FEAT-lyrics-viewer-playback` shipped a real bug precisely here — a 204 is acceptance, not
application, and a same-tick stub erases the window where a stale read returns the previous track
(memory `feedback-stub-must-model-async-lag`).

---

### Step 7 — front: single-tab ownership, transfer, and owner-tab failure recovery

Lease + `BroadcastChannel` + `storage` fallback; mirror-mode rendering; explicit transfer; stale-lease
reclaim.

**Measurement-first.** Before constants are chosen, measure in a real browser how long a backgrounded
tab's heartbeat is actually throttled to, and what a hard tab kill leaves behind. A guessed timeout
either lets a hidden tab lose ownership it is still using, or leaves playback unclaimable after a
crash. Recorded as a measured number with its recipe (memory `feedback-verify-by-running-not-reading`).

**Verification**: two real tabs — transfer both directions; kill the owner (task-manager kill, not a
clean close) and confirm the survivor can claim; background the owner past the timeout and confirm it
is **not** stolen; rung-1 case confirms both tabs stay usable controls.

---

### Step 8 — front: drop sources beyond Buckit **[gated: `ARCH-entity-interaction-v2` Steps 1–3 merged]**

Wire the v2 drag payload so album/track representations across the product can be dropped into the
Playback Bucket, and so the mobile non-drag path (v2's prototype outcome) reaches it too.

**Verification**: CDP matrix — one drop per source surface; mobile 390 via
`emulate("390x844x3,mobile,touch")` (not `resize_page` — memory `reference-cdp-mobile-emulation`); an
id-less (Spotify-only) entity is non-draggable rather than a crashing drag.

---

## Dependencies and sequencing

```
FEAT-member-player  S5 · S5b · S6 · S7  ✅ SHIPPED 2026-08-02 (cold start owner-confirmed 08-03)
                          │ ladder · device picker · Media Session · persistence
                          v
FEAT-playback-bucket-player  S1 ─> S2 ─> S3 ─> S4 ─> S5 ─> S6 ─> S7 ─> [S8]
                             docs   db    api   ctr  front player tabs  sources
                              ✅     ✅  (S1 08-03; S2 prod-applied 08-03, shared_db #72)
                                                                          ^
ARCH-entity-interaction-v2   S1 ──> S2 ──> S3 ────────────────────────────┘
                             audit  canon  payload contract
```

- **S2 → S3**: schema applied to prod before the backend pin bump.
- **S3 → S4 → S5**: the three-artifact contract chain (backend export → workspace merge → front
  regen); never collapse the export and the merge.
- **v2 S1–S3 → S8**: hard gate. Without the payload contract only Buckit-internal surfaces can fill
  the queue.
- **S2 and S6 are the two rule-#4-sensitive steps** (a schema step; a step that changes audio behavior
  globally); neither shares a session with another step.
- `ARCH-entity-interaction-v2` S1–S3 may run **in parallel** with this RFC's S2–S5 — different repos,
  no shared files.

---

## Open questions

Only questions whose answer changes the work.

1. ~~**Who gets a Playback Bucket, and which rung do they get?**~~ **RESOLVED 2026-08-03 (owner):
   members get BOTH rungs — open the `streaming` scope.** This goes past the recommended default
   (rung 1 only, no scope change), so the costs are recorded rather than discovered later:
   - **The scope change is not this RFC's to make.** `SPOTIFY_SCOPES` lives at
     `myblog_front/src/components/member/integrations.api.ts:55` and the re-consent banner is
     `FEAT-member-player` Step 1's idiom. It ships there, before this RFC's Step 6 can claim a member
     tier. Filed as a prerequisite in the header.
   - **Every already-connected member must re-consent.** Today that set is exactly one account (the
     owner), whose stored grant already carries `streaming` — so the migration cost is ~zero *now* and
     grows with each member who connects before the scope opens. Opening it sooner is cheaper.
   - **It ships unverified on a second account.** Prod has 4 users and **1** Spotify integration. This
     is precisely why `FEAT-member-player` Step 5 scoped itself owner-only. The member path will be
     built and tested against mocks but not exercised by a real second Premium account unless one is
     provisioned. Named here so it stays a known gap, not a surprise.
   - Unchanged and fine: Extended Quota Mode is measured, so there is no user cap or allowlist, and a
     free member still degrades correctly at rung 2 through the existing `unsupported` path.
2. **Which expanded-player form?** *(blocks Step 6.)* In-page expansion / floating player / dedicated
   player surface / another justified option. **Not decidable from the code** — a product and design
   judgment, and the brief asks for a comparison first. Step 6 opens with a side-by-side comparison at
   realistic scale; the owner picks. **No default asserted**, because asserting one would defeat the
   comparison.
3. ~~**Where does "no confirmation" stop?**~~ **RESOLVED 2026-08-03 (owner): no confirmation at any
   size, bucket-local Undo always.** A 40-track compilation expands silently like anything else. This
   reverses FEAT-pocket-buckit D8's mandatory 1:N confirmation **for a drop onto this bucket only**;
   every other bucket keeps it. Revisit only if a real expansion turns out to surprise in use — Undo
   is what makes that cheap to find out.
4. ~~**Is the lyrics entry reachable for non-owner members?**~~ **RESOLVED 2026-08-03 (owner): open
   lyrics to members.** This goes past the recommended default (ship the existing owner-only state and
   leave the gate alone), and it reverses a decision that shipped with a written rationale, so:
   - **The guard change is not this RFC's to make.** `myblog_backend/app/api/routes/lyrics.py:37,56,75`
     depends on `require_owner`; reverting it to `require_cognito_token` is an auth-guard change, which
     CLAUDE.md routes to Claude directly, fail-closed, with a cross-repo twin grep. It belongs to the
     lyrics stream (`FEAT-lyrics-annotations` §6.9 O2 shipped it as backend #139 + front #319), not to
     a playback step. Filed as a prerequisite in the header.
   - **What O2's rationale actually rested on**: `track_lyrics` is documented as **owner-only research
     data** (`models.py:315-318`), and members *could* read lyrics until 2026-07-28. So this is a
     re-widening, not a new exposure — the front already has the 403-as-a-state UI from #319 that would
     become dead code.
   - The FEAT-lyrics-viewer **public** invariant is untouched either way: no public route, page, search
     or shared payload carries lyric text or its presence. Members are authed, not public.

4b. ~~**Do the annotations open too?**~~ **RESOLVED 2026-08-03 (owner): yes — annotations open with
   the lyric text.** Past the recommendation (lyric text only), so the scope of the lyrics-opening
   step is now the full read: `GET /api/lyrics/{id}` and the `annotations` field it carries, both to
   `require_cognito_token`. Consequences to carry into that step, which still lives in the lyrics
   stream and not here:
   - **`models.py:315-318` must change in the same PR.** It documents `track_lyrics` as *owner-only
     research data*; after this it is member-readable and the comment is simply false. A stale
     comment on a table is how the next session mis-scopes a guard.
   - **Front #319's 403-as-a-state UI becomes dead code** — both the sheet's "가사는 운영자만 볼 수
     있어요" branch and the viewer's. Delete it in the same PR or it rots as an unreachable state.
   - **The annotations carry third-party derived content** (Genius facts + Korean translations), which
     the lyric text does not. Members are authed, so the FEAT-lyrics-viewer **public** invariant is
     untouched either way; but attribution obligations, if any, now apply to a wider audience than
     one person. Worth one look at the Genius terms in that step — not a blocker, and not this RFC's
     call.

**OQ2 (expanded-player form) remains the one genuinely open product question**, by design — it is
decided at Step 6 after the side-by-side comparison, not before.

> **Closed before filing** — recorded so they are not re-opened: *does `sendPlayerCommand` announce
> transport changes?* **Yes** since front #342 (transport kinds; modes excluded) — the session store
> depends on it. *Do the ladder / device picker / Media Session / persistence exist?* **Yes**, shipped
> front #334/#335/#340; the first draft of this RFC said otherwise from a stale checkout.

---

## Risks

- **Building a second play path by accident.** Mitigation is mechanical: a grep gate in Step 6's
  review — no `api.spotify.com` string outside `lib/spotifyPlayback.ts`.
- **Using Spotify's queue because `queueTrack()` is right there.** It ships, it is tempting, and it
  would create the divergence the no-reverse-sync rule exists to avoid. The mechanism is
  `play({kind:'uris', …tail})`; the non-goal states this explicitly so a future session does not
  "simplify" it.
- **A stub that answers instantly hides a propagation race.** See Step 6's harness requirement — this
  already shipped a bug once in `FEAT-lyrics-viewer-playback`.
- **Auto-removal is destructive.** A completion handler firing on a bad "track finished" signal deletes
  a real row. Removal must be driven by a confirmed track change, and it is a membership delete (never
  a source delete) with bucket-local Undo — the non-destructive-membership invariant still holds.
- **Tab-ownership timeouts stealing from a hidden tab.** Mitigated by Step 7's measurement-first rule.
- **Auditing a stale checkout.** This RFC's first draft concluded the play ladder did not exist,
  because the local workspace was ~20 commits behind and `myblog_front` 9 behind. Every step here
  re-verifies its "Current state" claims against `origin/main` at step time
  (memory `feedback-rfc-current-state-audit`).
- **Verifying with one Spotify account.** Prod has exactly 1 integration. If OQ1 opens the member
  tier, the member path ships unverified unless a second account is provisioned. Named here so it is a
  decision, not a discovery.

## Decisions log

| Date | Decision | Step |
|------|----------|------|
| 2026-08-03 | Filed as a draft after auditing the four named RFCs + `RESEARCH-playback-product-architecture`, `ARCH-entity-interaction-unify`, `FEAT-my-buckit-artist`, `FEAT-pocket-buckit-viewers`, `FEAT-bucket-identity`, the multi-user RFC, `component-map.md`, and the live code | 1 |
| 2026-08-03 | **Boundary = two successor RFCs**, not one: different repos (cross-repo vs front-only), different decision and verification kinds, and the entity work is broader than playback. Rejected: one combined RFC, a schema-only third RFC, folding the forms into `FEAT-member-player` | 1 |
| 2026-08-03 | **Correction to this RFC's own first draft**: it was written against a checkout ~20 commits behind `origin/main` and concluded the play ladder, device picker, Media Session and persistence did not exist, gating Step 6 on `FEAT-member-player` Step 5. All four **shipped 2026-08-02** (front #334/#335/#340) and the cold start was owner-confirmed 2026-08-03. The gate is removed; the dependency is now "builds on", and the same stale read had listed `MYBLOG_PLAYBACK_CHANGED` as an open gap when front #342 had closed it | 1 |
| 2026-08-03 | **The Buckit queue plays by re-issuing its own tail** — `play({kind:'uris', uris:[n…end]})` — and never writes to Spotify's queue via `queueTrack()`. Using Spotify's queue would manufacture the exact divergence the no-reverse-sync rule refuses to reconcile; the `'uris'` intent already carries the "always send the whole tail" semantics | 5, 6 |
| 2026-08-03 | Queue rows use `item_type='playback'` + `track_id`, **not** `'track'` — `uq_review_bucket_items_track` would reject the duplicates this bucket must allow, and widening that index would touch every other bucket | 2 |
| 2026-08-03 | "Exactly one per user" uses the **existing per-user partial-unique idiom** (V40 re-scoped `single_done`/`single_spotify_library` from table-wide to per-user), so OQ12's no-global-singleton rule is honored by construction | 2 |
| 2026-08-03 | The system-bucket delete guard is a **pattern fix, not a feature**: `delete_bucket` has no guard today, so `spotify_library` and `to_listen` are also deletable. Same PR, sweep named in the body | 3 |
| 2026-08-03 | Step 5 (queue model) ships with **no play call at all**, so a Step-6 regression is unambiguously a player bug rather than a queue bug | 5 |
| 2026-08-03 | **Correction (owner caught it): the schema and infra gates were written as "human applies", which misreads hard rule #3.** That rule restricts *rollback* migrations; a forward migration is Claude-applied with owner approval, and this repo has done exactly that (V30/V31 2026-06-24, V50 2026-07-31; `terraform apply` 2026-07-26). What the gate really enforces is the **procedure and the ordering** — dry-run, apply, live re-verify, and only then the pin bump — not who types it. Steps 2 and 3 corrected | 2, 3 |
| 2026-08-03 | **Owner: Status draft → accepted**, both successor RFCs promoted, playback bucket first (v2's audit runs in parallel — different repos, no shared files) | — |
| 2026-08-03 | **Owner (past the recommendation): members get BOTH rungs — open the `streaming` scope.** Recorded costs: the scope + re-consent belong to `FEAT-member-player`, every connected member re-consents (today: 1 account, already holding `streaming`), and the member tier ships unverified until a second Premium account exists. OQ1 closed | 3, 6 |
| 2026-08-03 | **Owner: no expansion confirmation at any size + bucket-local Undo.** Reverses pocket-buckit D8's 1:N confirmation for this bucket only. OQ3 closed | 5 |
| 2026-08-03 | **Owner: album expansion rides the existing `POST /api/buckets/{id}/items`**, not a new endpoint — the sibling this step was modelled on (`expand_artist_source`) already does exactly that, and `AddBucketItemRequest` already carries `source_*`. Consequence: **no `infra/apigateway.tf` route and no `terraform apply`**, so the gate that this step was expected to stop at does not exist. Found by auditing the RFC's own claims against the code before writing any (memory `feedback-rfc-current-state-audit`) | 3 |
| 2026-08-03 | **Album order is `track_no ASC NULLS LAST`; there is no disc column.** Recorded as a known limit rather than fixed: multi-disc albums interleave because Spotify's `track_number` restarts per disc. Pre-existing across every album-track read; a `disc_no` column + backfill is out of scope | 3 |
| 2026-08-03 | **Owner: the annotations open too** (OQ4b, past the recommended lyric-text-only). The lyrics-opening step therefore covers the whole read — route + `annotations` field — and must, in the same PR, correct `models.py:315-318` ("owner-only research data", now false) and delete front #319's 403-as-a-state UI. Flagged for that step, not decided here: the annotations carry Genius-derived content, so attribution now reaches a wider audience | 6 |
| 2026-08-03 | **Owner (past the recommendation): open lyrics to members.** Reverses `FEAT-lyrics-annotations` §6.9 O2 (shipped backend #139 + front #319). The guard change belongs to the lyrics stream, not a playback step. Surfaced a sub-question the decision did not cover — **do the Genius-derived annotations open too** (OQ4b, recommended: lyric text only) — plus the now-false `models.py:315-318` "owner-only research data" comment. OQ4 closed | 6 |
| 2026-08-03 | Eligibility is **two-tiered in shipped code** (member scope omits `streaming` → rung 1 only; owner gets both), so OQ1 is not "owner vs members" but "which rung does a member get" | 3, 6 |
