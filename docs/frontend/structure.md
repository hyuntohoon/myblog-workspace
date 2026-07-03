# Frontend structure map — human-readable

> **Verified 2026-07-02** against `myblog_front/src/` (Astro 5 + React 19).
> Produced by `docs/archive/done/rfcs/ARCH-frontend-component-map.md` Step 1. For file-pinned detail
> (exact `path:line` anchors, per-domain ownership), read [component-map.md](component-map.md).

## The big picture

The site is an Astro 5 multi-page app. Each route is a static Astro page that mounts zero or
more **React islands**; there is no client-side router and no global SPA state. Two React
roots matter site-wide:

```
layouts/layout.astro  (every page except /write)
├─ Header (+ HeaderSearch ⌘K)
├─ <page content>          ← per-route island(s)
├─ Footer
└─ PocketBuckit            ← site-wide tray island (null when logged out)
   └─ PocketBuckitProvider ← the ONE React context
      └─ PocketTray        ← drawer with bucket members, ▶ play

pages/profile.astro
└─ ProfileApp              ← SEPARATE React root (authed)
   ├─ OverviewDash / LikedBoard / ImportAnalysis / ReviewsTab …
   ├─ BucketBoard (+ TrashDrawer)
   └─ AlbumDetail (React modal/slide-over)
```

**The two roots never share React context.** They talk through (a) the `bucketStore`
observable singleton and (b) `pb:*` window CustomEvents. Any feature that must work both
in the tray and on the profile board crosses this boundary.

## Routes by feature area

| Area | Routes | Interactivity |
|---|---|---|
| Editorial (public) | `/`, `/reviews`, `/review/[slug]`, `/canon`, `/collection` | Review page tracklist is **vanilla JS** (`albumDetail.client.ts`), not React |
| Catalog (public) | `/artist/[id]`, `/genres`, `/search` | React islands, runtime fetch |
| Member (authed) | `/profile` (+ `/buckets` → redirect), `/drafts` | `ProfileApp` root; drafts is vanilla |
| Writer (authed) | `/write` | Own layout (`write-layout.astro`), no shared chrome |

Auth guards are per-page scripts (`profile.guard.ts`, `write.guard.ts`); everything else is
public, with edge_guard-only reads for member-ish data (buckets, library).

## The three data/state flows

1. **Bucket tree** — one `bucketStore` singleton (sessionStorage cache + 5-min SWR). Both
   roots subscribe via `useSyncExternalStore`; one optimistic update re-renders both.
2. **Cross-island events** — `pb:toggle`/`pb:closed`/`pb:open-state` mirror the tray's open
   state; `pb:dnd-start`/`pb:dnd-end` (and `pb:board-*`) hand a drag across roots
   synchronously. The review page's vanilla ＋ button also enters React via a window event
   (`pb:add-track` → `ReviewTrackAdder`).
3. **Playback** — every ▶ goes through one SDK owner, `lib/spotifyPlayback.ts`
   (`requestPlayback`): JWT-minted streaming token → lazy Spotify SDK → catalog-id→URI
   resolve → direct client-side `api.spotify.com` call. Nothing loads until a real ▶ click
   (rule #9). `NowPlaying` is a separate, read-only snapshot display — **not a player**.

## What is shared vs duplicated (impact hotspots)

- **Track rows are NOT shared.** Six independent surfaces render track rows (review
  tracklist, pocket tray, member AlbumDetail, LikedBoard, search results, writer pickers);
  only the play *call* is shared, never the row UI. Touching "how a track click behaves"
  means touching up to six places — check the table in [component-map.md](component-map.md).
- **Album detail is duplicated** — a vanilla path (review page) and a React path (profile),
  each with its own cache. A change to album-detail data shape hits both.
- **Add-to-bucket is duplicated** — `AddToBucketMenu` (portable, handles logged-out intent)
  vs `BucketPickerSheet` (member-only picker). Different UX contracts; both end at `ops.*`.
- **Overlays** — slide-over/scrim primitives (`.lf-scrim`/`.lf-slideover`, `--z-panel`) +
  `useDismissable` are the reusable kit; several member modals reuse them, the pocket menus
  intentionally do not. There is no full-bleed (Spotify-mobile-style) overlay primitive today.
- **Orphaned code** — `search-bar.astro` + `searchBarDb.client.ts` (no importers).

## How to use this map in an RFC

Fill the **Component-map impact template** (bottom of [component-map.md](component-map.md))
in the RFC's Current-state section: routes touched, which of the six track-click paths are
hit, overlay/state/cache owners, and which duplication it overlaps. If the answer to
"cross-island?" is yes, the design must name the `pb:*` event or store field it rides on.
