# ARCH-entity-interaction-unify: One entity → one interaction, everywhere

- **Status**: in-progress (Step 1 shipped + prod-verified 2026-07-08)
- **Owner**: TBD
- **Created**: 2026-07-08
- **Plan row**: `plan.md` → ARCH-entity-interaction-unify
- **Extends**: `docs/archive/done/rfcs/ARCH-entity-interaction-contract.md`
  (Steps 2+3 established `TrackRow` + `lib/entityLinks.ts`; this RFC completes
  the dispatch to all three entity types and kills the load-bearing
  album-detail duplication)
- **Consumed by**: `FEAT-today-buckit` (its buckit tiles are the first
  consumer that must click identically to every other surface)

---

## Goal

After this RFC, clicking an **artist**, **album**, or **track** does the same
thing no matter which surface it is rendered on, and that behavior is dispatched
through one contract point (`lib/entityLinks.ts`) instead of per-surface
hand-rolling:

- **Artist** → route to `/artist/[id]` (already true via `artistHref`; this RFC
  only closes the remaining not-linkable gaps).
- **Album** → open **one** global album-detail overlay window (mounted app-wide,
  opened by a CustomEvent), on **public and member surfaces alike**. Public album
  cards that were dead (artist-catalog, search) gain this overlay; the read-only
  detail body is shared with the member modal (Step 1). The review page's inline
  editorial tracklist is a distinct surface and stays as-is (see Step 2 audit).
- **Track** → open the album-detail window for the track's album (the album
  window is the canonical track destination in v1; play/add stay reserved).

The concrete win: the `docs/frontend/component-map.md` "Duplicate / overlapping
responsibilities (load-bearing)" item #1 (two album-detail paths) is resolved,
and a new component (like a home buckit tile) can make an entity clickable by
calling one helper, with no knowledge of routes vs overlays.

## Non-goals

- **No new play/add affordances.** `TrackRow`'s `play`/`add` slots stay reserved
  (ARCH-entity-interaction-contract OQ2 default holds). Track click = open album
  window, not play. Existing ▶/＋ on the review tracklist and pocket tray are
  untouched in behavior.
- **No vanilla → React migration of unrelated code.** Only the album-detail
  render path in `scripts/albumDetail.client.ts` is redirected; the review
  page's ▶/＋ track buttons and `ReviewTrackAdder` keep their current wiring.
- **No album detail *route* (`/album/[id]`).** Owner chose a global overlay
  window over a page route (2026-07-08). SEO/deep-link for albums is a possible
  later RFC, not here.
- **No change to the lyrics viewer, bucket DnD, or now-playing paths.**
- **No backend/contract/infra change.** This is a `myblog_front`-only refactor.

## Current state

Verified against `docs/frontend/component-map.md` (stamped 2026-07-03) + source
2026-07-08. Re-verify the 3 load-bearing claims (album-detail duplication,
overlay host, entityLinks surface) at Step 1 per the map's re-verify rule.

- **`lib/entityLinks.ts`** is the contract point but only covers `artistHref(id)`
  and `reviewHref(slug)` (trailing-slash canonical). **No album or track
  dispatch exists.** Album/track "navigation" is an `onOpen(DetailTarget)`
  callback threaded through the member islands, not a route or a shared helper.
- **Album detail = two implementations, but NOT interchangeable** (Step-2
  audit 2026-07-08 corrected the original "delete the duplication" framing):
  1. React `components/member/AlbumDetail.tsx`, mounted **once** by
     `ProfileApp.tsx` (member island only), cache `lib/albumDetail.ts`.
     Branches: `MemoWindow` (writable bucket) / `StandardModal` info / edit.
     Opened via the `onOpen(DetailTarget)` callback. Now composes the shared
     read-only `AlbumDetailView` for its info body (Step 1).
  2. Vanilla `scripts/albumDetail.client.ts` +
     `scripts/albumDetail.fetch.client.ts` on the **public** `/review/[slug]`
     page. **CORRECTION:** this is NOT a click-to-open modal — it renders the
     album's **inline editorial tracklist** (`#albumDetail` inside
     `.lfq-tracklist`, always visible, with ★ recommended-track highlighting +
     per-track ▶/＋ buttons; `sessionCache` lives in the fetch client). It is a
     first-class editorial section of the review article, not a duplicate
     surface that can be deleted. Deleting it would regress the review page.
     So Step 2 does **not** touch it.
- **The real public gap is DEAD album cards, not the review page.** The album
  cards that today have NO interaction and that `openAlbum` was built to serve:
  - `/artist/[id]` **catalog albums** (`ArtistHub` `.art-disco-item`, the
    "아직 평론 없음" grid) — plain `<div>`, no click, no href.
  - Search **album cards** (`SearchPage` `AlbumCard`) — explicitly
    "non-navigable (no album page) — static figure".
  These are the Step-2 targets: wire them to `openAlbum`. Home
  `TodayAlbumBuckit` already does this (the one existing consumer).
- **Track click** varies per surface (`component-map.md` track table):
  member `AlbumDetail`/`LikedBoard` use shared `components/shared/TrackRow.tsx`
  with declared actions `{lyrics?, open?}` (`open` → album detail; `lyrics` →
  viewer); review tracklist is vanilla ▶/＋; pocket tray is ▶ play; search rows
  are `action:'static'` (not clickable). `play`/`add` are reserved-unimplemented.
- **Overlay infrastructure is reusable and ready.** `lib/useDismissable.ts`
  (ESC + focus trap + module-level nested-overlay stack — overlays already nest,
  e.g. lyrics over album-detail); primitives `.lf-scrim` / `.lf-slideover` /
  `.lf-modal-card` (`styles/member.css`), z-tokens `--z-overlay:80` /
  `--z-panel:90` (`styles/global.css:52`).
- **Cross-island messaging pattern exists.** `lib/pocketBuckit/events.ts`
  (`pb:*` CustomEvents) + `bucketStore` singleton already carry tray↔board
  handoffs across separate React roots. A global album-open event follows this
  established idiom.
- **Null ids are a first-class case.** Search/board payloads carry
  `id: string|null` (null = not-in-catalog) and already render dead/no-op cards
  (`SearchPage.tsx:42`). The unified dispatch must preserve non-navigable
  entities, not crash on them.

## Target state

- **`lib/entityLinks.ts` becomes the full dispatch.** Add, alongside
  `artistHref`/`reviewHref`:
  - `openAlbum(target)` — dispatches a window CustomEvent (proposed
    `ent:open-album`, namespaced like `pb:*`) carrying an album identity
    (`{albumId?, spotifyAlbumId?, cover?, title?}`), or a no-op when the id is
    null.
  - `openTrackAlbum(track)` — resolves the track's album id and calls
    `openAlbum`.
  - `artistHref` unchanged; the "not linkable" gaps (`NowPlaying`, `LikedBoard`
    rows, null-id search cards) close **only** when a real id is in the payload
    (backend payload changes are out of scope — flagged where they block).
- **One global album-detail overlay host.** A single `AlbumDetail` overlay is
  mounted **app-wide** (in `layouts/layout.astro`, sibling to `PocketBuckit`),
  listening for `ent:open-album`. It renders the **read-only** `StandardModal`
  branch for everyone; the **writable** `MemoWindow` / edit branches stay gated
  behind `isLoggedIn()` + bucket context (so public visitors get info-only, the
  owner keeps authoring). This is the design crux — OQ1 decides whether
  `AlbumDetail` can be lifted out of `ProfileApp` cleanly or needs a thin
  read-only variant.
- **Public review page dispatches the event.** `scripts/albumDetail.client.ts`
  stops rendering its own `#albumDetail` and instead dispatches `ent:open-album`;
  the vanilla `sessionCache` album-detail render path is deleted, converging on
  the `lib/albumDetail.ts` cache. The ▶/＋ track buttons on that page keep their
  current `requestPlayback` / `pb:add-track` wiring (non-goal to touch).
- **Track click routes through the album window** on every non-excluded surface
  via `TrackRow`'s `open` action → `openTrackAlbum`.
- **`docs/frontend/component-map.md` updated**: entity-navigation section gains
  album/track dispatch; the "load-bearing duplication #1" item is struck; the
  impact template is filled for this RFC.

## Steps

Sequential (each mergeable; rule 4 one-step-per-session applies). **Architect
review recommended at Step 1** — lifting a member-coupled modal to app scope is
a structural change (workspace trigger table: cross-repo/structural design).

### Step 1 — Global album overlay host + `entityLinks` dispatch (behavior-preserving)

Mount a single app-wide `AlbumDetail` overlay host in `layout.astro` opened by
`ent:open-album`; add `openAlbum`/`openTrackAlbum` to `entityLinks.ts`. Migrate
`ProfileApp`'s existing mount to dispatch through the same host (or have the host
coexist and `ProfileApp` delegate) so member behavior is unchanged. No public
surface rewired yet. Re-verify the 3 component-map claims first.

**Verification**:
```
cd myblog_front && pnpm lint && pnpm exec astro check
# real-browser: member /profile album click still opens the same modal (info +
# writable MemoWindow for a writable bucket); ESC nesting with lyrics viewer
# still correct; console 0.
```

**Rollback**: revert PR — the host is additive until a surface dispatches to it.

---

### Step 2 — Dead public album cards → `openAlbum` (RESCOPED 2026-07-08)

**Original framing (redirect the `/review` vanilla path, delete `#albumDetail`)
was dropped:** the Step-2 current-state audit found the review page's
`albumDetail.client.ts` renders an **inline editorial tracklist** (★ picks +
▶/＋), not a click-to-open modal — deleting it is a UX regression, and the
read-only overlay is not a substitute (it renders neither ★ picks nor ▶/＋).
The review page keeps its inline tracklist untouched.

**Rescoped work:** wire the genuinely non-navigable public album cards to
`openAlbum` so a click opens the app-wide read-only overlay (Step 1's host):
- `ArtistHub` catalog albums (`.art-disco-item`) → `<button>` calling
  `openAlbum({albumId, title, artist, cover, year})`; id-less (Spotify-only)
  rows stay static `<div>`.
- `SearchPage` `AlbumCard` → same, keyed on the DB `id`; null-id hits stay a
  static figure (OQ3 non-navigable payloads).
- Button-reset CSS so the interactive card is visually identical to the prior
  div (`button.art-disco-item`, `button.gs-albcard`); hover selectors widened
  from `a.…:hover` to `.…:not(.is-static):hover`.

**Verification**:
```
cd myblog_front && pnpm lint && pnpm exec astro check
# real-browser (temp page mounting real ArtistHub + fetch-mock, no local
# backend): catalog album click → app-wide overlay opens read-only (header +
# artists + tracklist, NO 가사 affordance = privacy); ESC closes; scroll lock
# restored; button-reset keeps layout identical; console clean bar offline
# backend (buckets/me/community-ratings, fail-soft).
# prod smoke (post-deploy): /artist/[id] catalog album + /search album card
# click → overlay opens.
```

**Rollback**: revert PR (cards return to non-navigable div/figure).

---

### Step 3 — Track click → album window (RESCOPED 2026-07-08)

**Audit finding:** the "wire `TrackRow`'s `open`" framing didn't match reality —
`LikedBoard` **already** wires `TrackRow` `open` (→ `onOpen(DetailTarget)` → the
**writable member modal**), and per the Step-1 architect rule member surfaces must
stay on that prop path (the event can't carry writable context). So member
surfaces are left as-is. The real gaps were **bespoke public track rows** with no
album-open: `SearchPage` `SearchTrackRow`, `HeaderSearch` dropdown track rows,
`ArtistHub` top-tracks. Rescoped work: add `openTrackAlbum(track)` (no-op when
`albumId` null, OQ4) and wire those three surfaces to it; also wired `HeaderSearch`
**album** rows (Step-2 leftover the dropdown surface missed). Original text below:

Wire `TrackRow`'s `open` action to `openTrackAlbum` and extend to any surface
carrying an album id per the component-map table (search track rows stay static
unless they gain an id — flagged, not forced).

**Verification**:
```
cd myblog_front && pnpm lint && pnpm exec astro check
# real-browser: a track row click (member AlbumDetail / LikedBoard) opens the
# album window for that track's album; console 0.
```

**Rollback**: revert PR.

---

### Step 4 — Update `docs/frontend/component-map.md`

Fill the impact template (below), strike load-bearing duplication #1, update the
entity-navigation + track-click sections, re-stamp Verified.

**Verification**: doc-only. (The original grep-gate "no `#albumDetail` vanilla
render remains" is **void** — the Step-2 audit established the `/review` inline
editorial tracklist stays; the vanilla render and its `sessionCache` path are
intentionally kept, not a leftover.)

---

## Component-map impact — ARCH-entity-interaction-unify

```
Verified: 2026-07-08 (re-verify at Step 1)
Routes touched:        / (layout host) — public; /review/[slug] — public; /profile (ProfileApp) — authed
Track-click paths hit:  review-tracklist (album-open only) | liked-board-onOpen | albumdetail-readonly
Play path:              none (▶ buttons unchanged — still requestPlayback)
Overlay changed:        album-detail promoted to a single app-wide host (reuses useDismissable + .lf-scrim)
State owner:            ad-hoc → new ent:* window event + lib/albumDetail.ts cache (single)
Cross-island?:          yes (new event: ent:open-album ; shared store: none)
Cache touched:          albumDetail (kept, now sole) ; sessionCache album-detail path (removed)
Duplicate it overlaps:  album-detail paths (RESOLVED by this RFC)
```

## Open questions

1. **Can `AlbumDetail` be lifted out of `ProfileApp` cleanly?** (blocks Step 1,
   the crux) — it currently assumes member/bucket context (`MemoWindow`,
   writable-bucket branch, `bucketStore`). Options: (a) mount the same component
   app-wide and gate the writable branches on `isLoggedIn()` + bucket presence
   (public = read-only `StandardModal`); (b) extract a thin read-only
   `AlbumDetailView` shared by both a public host and the member modal.
   **Architect pass at Step 1 start.** Recommend (a) if the member coupling is
   only the writable branches; (b) if data-loading is entangled with
   `ProfileApp` state.
2. **Event payload shape** (blocks Step 1) — does `ent:open-album` carry a full
   `DetailTarget` (`lib/member.ts:51`) or a minimal `{albumId|spotifyAlbumId}`
   the host re-fetches via `lib/albumDetail.ts`? Recommend minimal identity +
   host-side fetch (dedup/inflight cache already exists), so public callers need
   no member types.
3. **Not-linkable payloads** (blocks nothing here) — `NowPlaying` / `LikedBoard`
   rows / null-id search cards carry no artist/album id. They stay non-navigable
   until the backend adds ids to those payloads (separate change). Record which
   surfaces still can't dispatch after Step 3.
4. **Track → album resolution when albumId is absent** (blocks Step 3) —
   `TrackHit` carries `albumId` + `albumSpotifyId` (`useMusicSearch.ts:82`) but
   some track payloads may only have the spotify album id. `openTrackAlbum` must
   accept either; confirm every consumer surface has at least one.

## Decisions log

| Date | Decision | Step |
|------|----------|------|
| 2026-07-08 | Album click → single global overlay window (not a route page); resolve the vanilla/React duplication onto it (owner) | design |
| 2026-07-08 | Track click → open the album window for the track's album; no new play/add (owner) | design |
| 2026-07-08 | Artist click stays route `/artist/[id]` (unchanged) | design |
| 2026-07-08 | OQ1 resolved — architect rec **(b)**: `AlbumDetail` uses ZERO React context (usePocket/bucketStore = 0), so the crash worry was moot; but the event can't carry member types, so the app-wide overlay is inherently read-only. Extract a read-only `AlbumDetailView`; keep MemoWindow/edit member-side. Eval → `docs/archive/reviews/ARCH-entity-interaction-unify-step1-eval.md` | Step 1 |
| 2026-07-08 | OQ2 resolved — `ent:open-album` carries **primitives** `{albumId, title?, artist?, cover?, year?}` (host re-fetches via lib/albumDetail); public callers import no member types | Step 1 |
| 2026-07-08 | Step 1 SHIPPED — front #255 (`a549ec5`, deploy 28882687379). New `components/album/AlbumDetailView` + `AlbumOverlay` (un-gated, layout-mounted) + `lib/entityEvents.openAlbum`; member `AlbumDetail` delegates read-only body to the shared view. Public prod smoke: overlay opens on event, fetch 200/15 tracks, header+artists+tracklist render, **0 lyrics affordance** (privacy), artist link `/artist/…/`, ESC closes. Member live MemoWindow/edit gesture deferred to owner spot-check (shared view prod-proven; extraction behavior-preserving; MemoWindow untouched) | Step 1 |
| 2026-07-08 | **Step 2 RESCOPED (owner)** — current-state audit found the `/review` album detail is an inline editorial tracklist (★ picks + ▶/＋), NOT a click-to-open modal → the "delete the vanilla duplication" premise was wrong; review page stays untouched. Real public gap = **dead album cards** (artist-catalog `.art-disco-item` + search `AlbumCard`, both non-navigable today). Step 2 wires those to `openAlbum`. | Step 2 |
| 2026-07-08 | **Steps 3+4 shipped together (owner-approved single PR).** Step 3 RESCOPED — `LikedBoard` already wires `TrackRow` `open` → the writable **member modal** (kept, per architect rule); real gaps were bespoke **public** track rows. Added `openTrackAlbum` (no-op on null `albumId`, OQ4); wired `SearchPage` track rows, `HeaderSearch` dropdown **track + album** rows (album = Step-2 leftover), `ArtistHub` top-tracks. Step 4 — component-map re-verified/stamped 2026-07-08: track-click table + entity-nav album/track dispatch + overlay host + duplication #1 reframed (read body shared; review inline tracklist intentionally separate → the original "no `#albumDetail`" grep-gate is void). | Steps 3–4 |
