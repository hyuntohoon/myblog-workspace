# ARCH-entity-interaction-contract: Entity interaction contract (front)

- **Status**: accepted
- **Owner**: 박지훈
- **Created**: 2026-07-03
- **Plan row**: `plan.md` → ARCH-entity-interaction-contract

---

## Goal

After this RFC, every (entity × action) interaction the frontend currently re-implements
per surface is **declared in exactly one place**: track-row actions (play / lyrics / add /
open-detail) through a shared `TrackRow` component scoped to React islands, and artist /
review navigation through `lib/entityLinks.ts` href helpers. The purpose is **not code
conciseness** — it is reducing the token cost of future sessions: a future feature (e.g. a
new track action, a new artist affordance) wires **one contract point** instead of hunting
and editing N hand-rolled sites, and `docs/frontend/component-map.md` tracks that contract
point. Each step ships a user-visible deliverable so prod smoke is real: the **static
lyrics entry** (unblocks the FEAT-lyrics-viewer deferral), **clickable artist names** on
member surfaces, and a **trailing-slash drift fix** across review/artist links.

## Non-goals

- **No vanilla → React migration.** The review-page tracklist
  (`scripts/albumDetail.client.ts`) stays vanilla and is **explicitly excluded** from
  `TrackRow` adoption. Claiming "unified track rows" while the highest-traffic tracklist
  can't consume the component would be dishonest; the exclusion is documented instead.
  (Migrating it is a possible later RFC; revival trigger = a track action that must ship
  on the public review page.)
- **No album-detail unification.** The two album-detail paths (vanilla
  `scripts/albumDetail.client.ts` vs React `components/member/AlbumDetail.tsx`, separate
  caches) stay as-is — the *action* "open album detail" is already centralized per context
  (member island → one `AlbumDetail` mount in `ProfileApp`; public → navigate to
  `/review/[slug]`), and the difference is intentional per-context behavior, not drift.
- **No add-to-bucket flow merge.** `AddToBucketMenu` vs `BucketPickerSheet` stay separate
  (nothing is blocked by the duplication; see FEAT-pocket-buckit history).
- **No link wrapper components.** Artist/review links get **href helpers**, not a new
  component layer — every extra layer is context a future session must read. `TrackRow`
  is the only new component, justified by its compound actions.
- **No new public lyric exposure.** The static lyrics entry appears **only** on
  authenticated member-island surfaces; the FEAT-lyrics-viewer privacy invariant (no
  public route/page/search/shared payload carries lyric text **or its presence**) is
  unchanged.
- **No monolith splitting** (e.g. `BucketBoard.tsx` 2,768 LOC) — out of scope.

## Current state

Verified against code 2026-07-03. Baseline structure map:
`docs/frontend/component-map.md` (ARCH-frontend-component-map, verified 2026-07-02).

### Artist navigation — 4 hand-rolled sites, 2 idioms, slash drift, most surfaces dead

| Surface | Site | Idiom |
|---|---|---|
| Pocket tray (artist member) | `components/member/pocket/PocketTray.tsx:527` | `window.location.assign(`/artist/${id}`)` — **no trailing slash** |
| Bucket board (artist member) | `components/member/BucketBoard.tsx:637` | `window.location.assign(`/artist/${id}`)` — **no trailing slash** |
| Header search artist row | `components/search/HeaderSearch.tsx:265` | `action: {type:'navigate', href: `/artist/${id}/`}` |
| Search page artist card | `components/search/SearchPage.tsx:41` | `<a href={`/artist/${id}/`}>` |

Artist names are **not clickable at all** on: `NowPlaying` (all 3 variants + 최근 재생),
`LikedBoard` rows, `AlbumDetail` (member modal), writer surfaces.

### Review navigation — 12+ sites in 9 files, live trailing-slash drift

With trailing slash: `EditorialHome.tsx:95,143`, `AlbumDetail.tsx:221`,
`SearchPage.tsx:25`, `HeaderSearch.tsx:243`, `ArtistHub.tsx:150`.
**Without**: `CanonPage.tsx:19`, `ReviewsTab.tsx:63`, `ReviewsIndex.tsx:208,214,228,244`.
The site is Astro static output on S3+CloudFront (directory format → `/review/[slug]/index.html`);
the slashless form depends on redirect behavior rather than hitting the object directly.

### Track actions — 6 fragmented paths, play affordance on only 2

The full table lives in `docs/frontend/component-map.md` ("Track-click behavior"). Summary:
review tracklist (vanilla ▶+＋), `PocketTray` (React ▶), `AlbumDetail` (read-only `<li>`),
`LikedBoard` (open-detail + ⋯ menu), search rows (`action:'static'`, not clickable),
writer pick (★ select). `requestPlayback` (`lib/spotifyPlayback.ts:242`) is the shared SDK
layer but its UI importers are exactly 2: `scripts/albumDetail.client.ts`,
`components/member/pocket/PocketTray.tsx`. A `RowAction` union already exists in
`components/search/atoms.tsx` (navigate | static) — the pattern to promote.

### Lyrics entry — dynamic only; static blocked on this contract

FEAT-lyrics-viewer (done 2026-07-03) deferred static entry surfaces to a track-click
contract. The viewer mounts once in `ProfileApp.tsx:448`; it already supports a
non-live open shape `{trackId, progressMs: null, live: false}` (the `?lyrics=<id>` debug
entry, `ProfileApp.tsx:321-333`) with availability-aware empty states.

### Orphans

`components/search-bar.astro` + `scripts/searchBarDb.client.ts` (509 LOC) have no importer
(superseded by `HeaderSearch`/`SearchPage`). Re-verify at step time before deleting.

## Target state

- `myblog_front/src/lib/entityLinks.ts` — `artistHref(id)`, `reviewHref(slug)` returning
  the canonical (trailing-slash) form. **Every** artist/review href in `components/` and
  `scripts/` is built by these helpers; a grep for hand-rolled `/artist/` / `/review/`
  template literals outside this file and `pages/` returns nothing.
- `myblog_front/src/components/shared/TrackRow.tsx` — one row component with a declared
  action set (`{lyrics?, play?, add?, open?}`), promoting the `atoms.tsx` `RowAction`
  idea from navigation-only to compound actions. Consumers: member-island React surfaces
  (`AlbumDetail` tracklist, `LikedBoard`). The vanilla review tracklist is documented as
  excluded, in both this RFC and `component-map.md`.
- Static lyrics entry live on member surfaces via `TrackRow`'s `lyrics` action → opens the
  existing `ProfileApp` viewer mount with `{trackId, progressMs: null, live: false}`.
- Artist names clickable (via `artistHref`) on `NowPlaying`, `LikedBoard`, `AlbumDetail`.
- Orphaned search-bar pair deleted.
- `docs/frontend/component-map.md` updated: contract points registered, track-click table
  amended, "Verified" stamp bumped (this RFC's impact template touches track-click).

## Component-map impact — ARCH-entity-interaction-contract

```
Verified: 2026-07-03
Routes touched:        /profile (ProfileApp island) — authed; link call sites across public islands
Track-click paths hit:  albumdetail-readonly, liked-board-onOpen (gain TrackRow); review-tracklist EXCLUDED (vanilla)
Play path:              requestPlayback unchanged (no new play affordance in this RFC unless OQ2 says otherwise)
Overlay changed:        none (reuses ProfileApp LyricsViewer mount)
State owner:            profile-local (lyrics overlay state stays in ProfileApp)
Cross-island?:          no (PocketTray lyrics deferred — OQ4)
Cache touched:          none
Duplicate it overlaps:  album-detail paths (documented, untouched)
```

## Steps

One step per session (hard rule #4). Steps 2 and 3 are independent of each other
(different files; either order), but each still gets its own session.

### Step 1 — this RFC + plan row + index (docs-only)

This document, a one-line `plan.md` Backlog row, and a `docs/rfcs/README.md` index entry.

**Verification**: doc review against `TEMPLATE.md`; `git diff --stat` shows only docs.

---

### Step 2 — `TrackRow` contract + static lyrics entry (front-only)

Create `components/shared/TrackRow.tsx` (declared actions: `lyrics`, `open`; `play`/`add`
per OQ2). Adopt on `AlbumDetail`'s tracklist and `LikedBoard` rows (ProfileApp island
only). Wire the `lyrics` action to `ProfileApp`'s existing viewer mount via the non-live
open shape. Register the contract point in `component-map.md` (+ stamp bump).

**Verification**: `pnpm lint` + `pnpm exec astro check` (Node 20); real-browser
click-through (DoD): tracklist row → 가사 → overlay opens non-live (no refresh affordance),
availability empty-state on a lyric-less track, ESC/scrim close restores focus; grep
confirms no lyric affordance in any public-route component. Prod smoke post-merge.

**Rollback**: revert the front PR (additive component + call-site edits, no contract/infra).

---

### Step 3 — `entityLinks` helpers + artist affordances + orphan deletion (front-only)

Create `lib/entityLinks.ts`; replace all artist (4) and review (12+) href sites; add
artist links on `NowPlaying`/`LikedBoard`/`AlbumDetail` (member island; vanilla review
page excluded); delete `search-bar.astro` + `searchBarDb.client.ts` after re-verifying
zero importers. Resolve OQ3 (canonical slash + prod slashless behavior probe) first.

**Verification**: lint + astro check; `grep -rnE "/(artist|review)/\$\{" src --include='*.ts*' | grep -v entityLinks`
→ only `pages/` internals; CDP click-through of one changed site per idiom (tray artist
member, ReviewsIndex card, NowPlaying artist name); prod smoke: slashless URLs still
resolve (redirect) + new artist links navigate. Prod smoke post-merge.

**Rollback**: revert the front PR.

---

## Open questions

1. **Lyrics entry visibility (blocks Step 2)** — always show 가사 on authed rows and let
   the viewer's availability empty-state handle misses, vs pre-probing availability per
   row (extra API surface, N calls). **Default: always show** — the viewer already handles
   `unavailable` gracefully, and a per-row probe would leak effort for no privacy gain
   (surfaces are authed).
2. **Play/add breadth (blocks Step 2 scope)** — does `TrackRow` adoption also *add* ▶ /
   담기 to `LikedBoard`/`AlbumDetail` rows (new affordances), or declare only what each
   surface has today + `lyrics`? **Default: lyrics only in Step 2**; new play/add
   affordances are product decisions, not refactoring, and get their own approval.
3. **Canonical slash form (blocks Step 3)** — default trailing slash (matches Astro
   directory output + the majority idiom + `HeaderSearch.tsx:103` prefetch list), but
   probe prod first: does the slashless form 301/307 or 404? If slashless 404s on any
   surface today, that's a live bug worth noting in the PR.
4. **PocketTray lyrics (blocks nothing — deferred)** — the tray is a separate React root
   from `ProfileApp`; a tray-side lyrics action would need a cross-island `pb:*` event or
   a second viewer mount. Out of scope until wanted.

## Decisions log

| Date | Decision | Step |
|------|----------|------|
| 2026-07-03 | Scope cut from a 6-step full refactor to 3 steps after cold review: TrackRow is the only structural payoff; links become helpers not components; album-detail/add-to-bucket dedup rejected (nothing blocked); inventory folded into this RFC's Current state | 1 |
| 2026-07-03 | Vanilla review tracklist explicitly excluded from TrackRow (no fake unification; revival trigger documented) | 1 |
| 2026-07-03 | Status draft → accepted (explicit owner approval in session: "B도 승격해") | 1 |
