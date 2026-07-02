# FEAT-lyrics-viewer: Private owner-only lyrics reader on the corpus + future translation

- **Status**: draft
- **Owner**: 박지훈
- **Created**: 2026-07-02
- **Plan row**: `plan.md` → FEAT-lyrics-viewer

---

## Goal

After this RFC, the owner has **one private lyrics-reading surface** that opens from two entry
points — **static** (any track the owner sees inside the private `/profile` workspace) and
**dynamic** (the currently-playing Spotify track from the existing profile now-playing area, with a
manual refresh that reloads the current track and the available playback position). The surface is a
single shared viewer that renders, per the owner's choice, **original lyrics**, **original + Korean
translation**, or **Korean translation only**, and that **emphasizes one focused line at a time** while
visually de-emphasizing the surrounding lines (Spotify-mobile lyrics as the visual reference). In the
MVP the owner moves the focus **manually** — next, previous, or direct selection; **continuous
playback-time-driven progression is explicitly out of scope.** The viewer reads the private corpus
built by **FEAT-lyrics-corpus** (`track_lyrics`) and is built to consume **future translation data**
when that lands, but this RFC does **not** produce translations. It is owner-only: lyrics never appear
on any public page, public API, search result, or shared/edge-cached response — the corpus privacy
boundary is carried forward unchanged.

## Non-goals

Anti-scope-creep insurance. Each is a **separate, later** RFC/step, explicitly **not** here:

- **Lyrics collection and matching.** That is FEAT-lyrics-corpus (matched 7,955 / 20,946 tracks as of
  2026-07-02). This RFC only *reads* `matched` rows; it never collects, matches, re-matches, or writes
  lyrics.
- **Translation generation.** Producing Korean translations is a separate later RFC. This viewer
  *consumes* translation data via an agreed read contract when it exists; it ships original-only until
  then and degrades gracefully (see MVP boundaries). Translation is an **optional input**, never a
  blocker.
- **Lyrics interpretation or research.** No slang/meme/context notes, no per-line commentary, no
  album-level lyrical analysis. The viewer shows text; it does not annotate.
- **Automatic lyric synchronization.** No continuous playback-time-driven progression, no auto-scroll,
  no karaoke-style time tracking. Synced (LRC) timestamps may be used only to **define units** and,
  optionally, to set the **initial** focus on a manual refresh in dynamic mode — never to advance it.
- **Spotify playback controls.** No play/pause/seek/next-track. The viewer is read-only text; it does
  not touch the player. (Playback control is FEAT-spotify-streaming-playback.)
- **Any public, shared, or edge-cached exposure.** Lyrics stay owner-only. No public page, no public
  API schema, no search index, no bucket/post/shared response, no CloudFront-cached response carries
  lyric text or its presence. Same non-negotiable boundary as the corpus RFC.
- **Editing lyrics or translations.** The viewer is read-only. Correction happens in the corpus /
  translation pipelines, not here.
- **A public review/album-page entry point.** The public review tracklist (`pages/review/[slug].astro`
  + `ReviewTrackAdder.tsx`) carries track identity but lives on a **public** page; it is **not** a
  valid static entry. Static entries are the **owner-only** track surfaces only.

## Current state

Verified against code 2026-07-02:

- **Private corpus is live (FEAT-lyrics-corpus Steps 1–3, merged).** `TrackLyrics`
  (`myblog_shared_db/src/myblog_shared_db/models.py:308-330`) is a track-scoped, owner-only table:
  `match_status` (`matched` / `no_lyrics` / `not_found` / `ambiguous` / `review_required`),
  `lyric_plain` (Text), `lyric_synced` (Text, **LRC** `[mm:ss.xx] line`), `evidence` (JSONB),
  `matcher_version`. Phase 2 wrote **7,955 `matched`** rows over 20,946 tracks; **7,253 / 7,955 (91%)**
  carry synced LRC. Privacy comment on the model is explicit: *"Owner-only internal research data,
  never exposed in public API/page/search/shared response"* — same precedent as `album_research` /
  `artists.aliases`. **No endpoint reads `track_lyrics` today; nothing consumes it.**
- **No translation data exists.** There is no Korean-translation column, table, or contract yet. Any
  mode that needs translation has no data behind it today by design.
- **Now-playing area exists (the dynamic anchor).** `myblog_front/src/components/member/NowPlaying.tsx`
  (`banner | full | list` variants) shows `track / artist / album / album_cover_url / is_playing /
  updated_at`, fed by a **worker cache snapshot** via `GET /api/library/now-playing`
  (`getNowPlayingData()` in `src/components/member/spotify.api.ts`). It is **manual-refresh only** (no
  live polling) and falls back to "최근 재생" when idle; its progress bar (32 bars) is decorative.
  Critically, the backend `NowPlayingResponse` (`myblog_backend/app/api/schemas.py:589-603`) is an
  **intentionally-public single-admin vanity read (edge_guard-only)**, and **`progress_ms` /
  `duration_ms` are intentionally omitted (D28)** — *"a ≤1h-stale snapshot can't advance a progress
  bar, so it'd only ever render a misleading frozen one."* The **worker does fetch and store
  `progress_ms` / `duration_ms** in the `spotify_now_playing` snapshot
  (`worker/service/listening_sync_service.py:254-313`), so position data **exists server-side but is
  not exposed**. Net: the dynamic entry can reuse the public now-playing response for **track
  identity**, but **playback position is not exposed today and cannot ride that public response** — it
  needs a separate owner-only read (Open questions).
- **Spotify streaming/playback plumbing exists, separate from now-playing.**
  `myblog_front/src/lib/spotifyPlayback.ts` (`ensureSdk`, `requestPlayback(target)`, `resolveProviderUri`)
  is fired only on ▶ clicks and mints a server streaming token via `GET /api/playback/spotify-token`.
  That token's scopes (FEAT-spotify-streaming-playback) include **`user-read-playback-state`**, so
  reading current track + position is *token-enabled* even though no UI displays it yet.
- **Static track surfaces (owner-only) carry track identity** and are the static entry candidates:
  - 분석 버킷 좋아요한 트랙 workbench — `src/components/member/LikedBoard.tsx` (row `id` =
    `spotify_track_id`; also `albumId` DB id, title, artist).
  - Album detail tracklist — `src/components/member/AlbumDetail.tsx` `Tracklist` (`t.id`, `title`,
    `track_no`, `duration_sec`).
  - Pocket Buckit tray track items — `src/components/member/pocket/PocketTray.tsx` +
    `BucketBoard.tsx` (`trackId`, `title`; `playbackTargetFor()` already maps a track to a target).
  - Overview track collections — `src/components/member/OverviewDash.tsx` `TrackColl` (`id`).
  - (The review tracklist on the public `pages/review/[slug].astro` is **excluded** — public page.)
- **Owner-only boundary.** `/profile` is gated client-side by `src/scripts/profile.guard.ts`
  (`isLoggedIn()` → `goLogin(true)` otherwise; `src/lib/auth.ts`). Authed API calls go through
  `apiFetch` (`src/lib/api.ts:65-88`, `Authorization: Bearer <token>`, 401 → refresh-once). **Note the
  privacy tier split:** `/api/library/*` reads (incl. now-playing) are **edge_guard-only (no JWT)** —
  reachable by any CloudFront-fronted request. Lyrics carry the corpus RFC's stricter *"never in any
  shared response"* bar, so the lyrics read endpoint must be **owner-JWT-gated (Cognito authorizer)**,
  like `GET /api/playback/spotify-token` (`require_cognito_token`) and the posts/publish routes —
  **not** the edge_guard-only library pattern.
- **Overlay primitives to reuse.** `src/lib/useDismissable.ts` (ESC + focus trap/restore); `.lf-scrim`
  full-viewport scrim, `.lf-modal-card`, `.lf-slideover` (`src/styles/member.css`), `--z-overlay: 80`
  (`src/styles/global.css`). The existing centered `StandardModal` (600px) is **not** the Spotify-mobile
  full-screen shape; a dedicated full-bleed viewer panel is expected.

## Target state

A single shared, **owner-only** **Lyrics Viewer** with two entry points and three display modes,
reading `track_lyrics` (and, later, translation) through a JWT-gated endpoint:

- **Three display modes**, owner-selectable; availability is gated by what data exists for the track:
  1. **원문** — original lyrics (from `lyric_plain`, or the text of `lyric_synced` if only synced
     exists). Always available when the track is `matched`.
  2. **원문 + 번역** — original line with the Korean translation shown alongside/below. Available only
     when translation data exists for the track; otherwise disabled with a clear "번역 없음" state.
  3. **번역 (Korean only)** — Korean translation alone. Same availability gate as mode 2.
- **Focus-one-line reading.** Exactly one line (the **focus unit**) is emphasized (larger, full
  contrast); the lines above and below are de-emphasized (smaller, dimmed), echoing Spotify-mobile
  lyrics. The owner moves the focus **manually**: next, previous, or direct tap/select on any line.
- **Two entry points into the same viewer:**
  - **Static** — an owner-only track affordance (분석 버킷 workbench rows, AlbumDetail tracklist, Pocket
    tray track items, Overview collections) opens the viewer for that track's lyrics.
  - **Dynamic** — the now-playing area opens the viewer for the currently-playing track; a **manual
    refresh** control re-reads the current track and the available playback position via a **separate
    owner-only read** (not the public now-playing response, which omits position by D28). On refresh,
    the focus may be **initialized** to the line matching the current position (one-shot); it does
    **not** auto-advance thereafter.
- **Availability-aware empty states.** `no_lyrics` / instrumental → "가사 없음 (연주곡)"; `not_found` /
  `ambiguous` / `review_required` / no row → "아직 연결된 가사가 없어요" (the corpus may re-resolve it
  later). The viewer never implies a missing lyric is definitive.
- **Owner-only read API.** A new backend endpoint reads `track_lyrics` by track id and returns the
  lyric text + match status (and, later, translation) **only to the authenticated owner** — JWT-gated
  at the API Gateway authorizer, **not** edge_guard-only. New JWT GET route → matching
  `infra/apigateway.tf` entry + apply. No public schema references it.
- **Privacy invariant unchanged.** Lyric text and its presence remain absent from every public API
  schema, public page, search index, bucket/post, and edge-cached response. The viewer is the one
  legitimate reader, and it is owner-only.

## User flows

- **Static open.** Owner is on `/profile` (분석 버킷 track row, an album tracklist, a Pocket tray track
  item, or an Overview collection). Tapping the track's lyrics affordance opens the shared viewer on
  that track in **원문** mode (or the owner's last-selected mode if still available for this track),
  focus on the first line.
- **Dynamic open.** Owner is on `/profile` with the now-playing area showing a track. Tapping it opens
  the shared viewer on the currently-playing track, focus initialized to the first line (or to the line
  matching the current playback position, when a position was loaded).
- **Manual refresh (dynamic).** While the viewer is open, the owner taps refresh; the viewer re-reads
  the current playback state — if the track changed, the viewer swaps to the new track's lyrics; if
  only the position changed, the focus is re-initialized to the matching line. No continuous tracking.
- **Mode switch.** Owner switches among 원문 / 원문+번역 / 번역. Modes requiring translation are
  visibly disabled when translation is absent; the active line's emphasis is preserved across switches.
- **Focus navigation.** Owner moves the focused line with next / previous controls or by directly
  selecting a line; the emphasized line and the de-emphasized neighbors reflow accordingly. Plain lyrics
  with no synced data navigate exactly the same way — sync data only affects optional initial
  positioning, never navigation.

## Display modes

- **원문 / 원문+번역 / 번역**, selected by the owner. The selector shows which modes are available for
  the current track and disables the rest.
- **Visual reference: Spotify mobile lyrics.** One focused line emphasized; immediate neighbors
  de-emphasized; the rest of the lyric readable by scroll but recessed. Full-bleed, mobile-first.
- **Focus unit = a line.** For `lyric_plain`, units are lines split on newline. For `lyric_synced`
  (LRC), units are the timestamped lines (timestamps are **not** rendered to the user; they only enable
  optional initial-positioning in dynamic mode).

## Mobile interaction direction

- **Mobile-first, full-bleed.** The viewer is designed for the phone form factor first (Spotify-mobile
  reference), then adapted up — not the reverse.
- **Next / previous** are reachable as controls; direct **tap-to-focus** on any line is supported.
  Whether next/previous is additionally bound to a **vertical swipe/drag gesture** (vs. buttons only)
  is a design decision deferred to step-time (Open questions).
- **Manual refresh** in dynamic mode is a single, obvious control — the same "refresh once" affordance
  pattern the now-playing area already uses, not a live-polling loop.

## Dependencies on lyric / translation availability

- **Original lyrics** depend on the corpus. A track renders in **원문** iff it has a `matched`
  `track_lyrics` row with lyric text. ~7,955 tracks qualify today; the rest get an availability empty
  state. This dependency is **already satisfied** by FEAT-lyrics-corpus.
- **Translation** depends on a **future translation RFC** that does not exist yet. Modes **원문+번역**
  and **번역** are therefore **dormant at launch**: present in the UI, disabled per-track until
  translation data arrives. The viewer agrees a **read contract** for translation now so the future
  producer can fill it without rework (Open questions).
- **Dynamic position** depends on resolving its **source** (OQ1). The worker already stores
  `progress_ms`; the likely path is exposing it via a new owner-only read (D28's frozen-bar objection
  doesn't hold for a manual one-shot). If no source is acceptable, the dynamic entry **degrades** to
  track-only (no position) rather than blocking; static is unaffected.

## MVP boundaries

- **In scope (MVP):** shared owner-only viewer; **원문** mode fully working; focus-one-line emphasis;
  manual next/previous/direct-select navigation; static entry from the owner-only track surfaces;
  dynamic entry from now-playing with **manual refresh** of track + (if available) position and optional
  one-shot initial focus from position; availability empty states.
- **Out of scope (explicit):** continuous playback-time-driven progression / auto-scroll / karaoke sync;
  translation *production*; interpretation/annotation; playback controls; public or shared exposure;
  editing; a public-page entry point.
- **Translation modes are not MVP-blocking.** The MVP ships 원문-first; **원문+번역** / **번역** activate
  (no viewer rewrite) when translation data lands.

## Steps

Milestone-level. Hard rule #4 — one step per session, prod-observe / direction-recheck gate between
steps. Detailed endpoint/component/contract design is produced **at the start of each step**, reviewed,
and not pre-committed here (per RFC scope: behavior/flows now, implementation later). Branch/commit per
repo (`feedback-nested-repo-branch-per-repo`).

### Step 0 — RFC + plan.md pointer (this document, docs-only)

This RFC + a one-line `plan.md` Backlog pointer. No code, no schema. (The `docs/rfcs/README.md` index
entry is intentionally deferred — this session's scope is RFC + plan.md only.)

**Verification**: doc review against `TEMPLATE.md` / README required sections. `git diff --stat` shows
only the two doc files.

---

### Step 1 — owner-only lyrics read API (backend)

A new **JWT-gated (owner-only)** endpoint that reads `track_lyrics` by track id and returns the lyric
text (`lyric_plain` and/or the text of `lyric_synced`) + `match_status` (+ translation when that
contract exists). **Not** edge_guard-only — modeled on `GET /api/playback/spotify-token`
(`require_cognito_token`). New JWT GET route → matching `infra/apigateway.tf` entry + apply. No public
schema/response type references it; no shared/edge-cached response carries lyric text.

**Verification**: authenticated owner gets lyrics for a `matched` track and the correct empty-state
payload for `no_lyrics` / unresolved / missing-row tracks; an unauthenticated or non-owner request is
rejected; a schema check confirms no public type references lyrics; backend `pytest` passes.

**Rollback**: remove the route + the `apigateway.tf` entry (no consumer depends on it yet).

---

### Step 2 — shared Lyrics Viewer component (front, 원문 MVP)

A full-bleed, owner-only, mobile-first viewer reusing `useDismissable` + `.lf-scrim`. **원문** mode with
focus-one-line emphasis (focused line emphasized, neighbors de-emphasized) and manual next/previous +
direct-select navigation. Availability-aware empty states (가사 없음 / 연결된 가사 없음). Reads via
`apiFetch` against the Step 1 endpoint. Translation modes present but disabled (번역 없음). Launched in
isolation first (e.g., a debug/owner entry) before wiring entries.

**Verification**: real-browser click-through (`astro check` + `pnpm lint` pass; lint alone misses
render/event regressions — BUG-11→12); focus navigation and mode-disabled states confirmed on the live
DOM; owner-only (not reachable unauthenticated); mobile + desktop widths.

**Rollback**: remove the component + its island mount (no entry wired yet).

---

### Step 3 — static entry points (front)

Wire the owner-only track surfaces (분석 버킷 `LikedBoard` rows, `AlbumDetail` tracklist, Pocket tray
track items, Overview `TrackColl`) to open the shared viewer for that track. Affordance added per
surface; the public review tracklist is **not** wired.

**Verification**: each owner-only surface opens the viewer on the correct track's lyrics; the public
review page gains no lyrics affordance; full pre-merge real-browser CDP click-through (console 0).

**Rollback**: remove the per-surface affordances; the viewer component itself is untouched.

---

### Step 4 — dynamic entry + manual refresh (front)

Open the viewer from `NowPlaying` for the currently-playing track. Track identity comes from the
existing now-playing snapshot; the **playback position** comes from a **separate owner-only read**
whose source is an open question (the worker already stores `progress_ms`; exposing it is gated by D28
— Open questions). A manual refresh re-reads both; on a track change the viewer swaps lyrics, on a
position-only change the focus is re-initialized (one-shot). Continuous progression remains out of
scope. If no position source is acceptable, ship track-only dynamic (no position) and record the
degradation.

**Verification**: opening from now-playing loads the current track's lyrics; refresh swaps track when
it changed and re-initializes focus when only position changed; no auto-advance occurs; idle/최근 재생
behavior matches the chosen OQ resolution; pre-merge CDP click-through.

**Rollback**: remove the now-playing entry; static entries and the viewer are untouched.

---

### Step 5 — translation display modes (gated on a future translation RFC)

When translation data lands, activate **원문+번역** and **번역** modes against the agreed read contract
(per-line/unit Korean translation joinable to the same focus units). No viewer rewrite — the disabled
states simply become enabled per-track. This step is **blocked until a translation RFC delivers data**;
it is not on the MVP critical path.

**Verification**: tracks with translation render both new modes with line-aligned emphasis; tracks
without translation keep the disabled state; focus preserved across mode switches.

**Rollback**: hide the two modes again (translation data is additive; 원문 is unaffected).

---

## Risks

- **Privacy leak (highest).** Lyrics are single-owner private research data with a "never in any shared
  response" bar. Mitigation: the read endpoint is **owner-JWT-gated**, not edge_guard-only; the viewer
  lives only on owner-only surfaces; acceptance gate = no public schema/page/search/shared response
  references lyric text or its presence.
- **Translation absence.** Two of three modes have no data at launch. Mitigation: 원문-first MVP; the
  other modes are per-track disabled with a clear state, not broken.
- **No live playback position today.** Position is stored server-side (`progress_ms` in the
  `spotify_now_playing` snapshot) but **deliberately not exposed** (D28). Mitigation: expose it via a
  new **owner-only** read (manual-refresh one-shot semantics neutralize D28's "frozen bar" objection);
  if that proves unacceptable, dynamic degrades to track-only. Static is unaffected.
- **Position is a point-in-time snapshot, not live (D28).** Even when exposed, a manual-refresh
  position is a single moment — the viewer must never present it as a ticking/advancing state, or it
  reproduces exactly the misleading frozen bar D28 warned against. Mitigation: one-shot initial focus
  only; continuous progression stays out of scope.
- **Synced lyrics ≠ synced experience.** 91% of `matched` rows carry LRC timestamps; users may expect
  karaoke auto-scroll. Mitigation: explicit MVP boundary (manual focus only); timestamps hidden,
  used only for optional one-shot initial positioning.
- **Focus/scroll on long lyrics, mobile.** Heavy lyrics must still keep the focused line legible and
  neighbors scannable. Mitigation: Spotify-mobile emphasis model, real-browser mobile-width
  verification (repro with prod-realistic long lyrics — `feedback-ui-repro-realistic-data`).
- **Crowd-sourced text correctness.** Corpus text is untrusted for factual correctness (FEAT-lyrics-corpus).
  Out of scope to fix here, but the viewer should read as an aid, not assert authority (no claim of
  accuracy).
- **Privacy tier drift.** Future contributors may assume lyrics can ride the edge_guard-only
  `/api/library/*` pattern. Mitigation: stated explicitly here + the acceptance gate.

## Open questions

1. **Playback-position source + the D28 boundary (blocks Step 4)** — where does the dynamic entry's
   position come from? Candidates: (a) **expose the `progress_ms` / `duration_ms` the worker already
   stores** via a new **owner-only** field/endpoint — i.e. un-D28 it for a *private* surface (D28's
   "misleading frozen bar" rationale does **not** apply to a **manually-refreshed, one-shot** initial
   focus, which never claims to advance); (b) a new **live** read minting the streaming token → Spotify
   `/v1/me/player`; (c) the in-browser SDK player object (only valid if the owner clicked ▶ in *this*
   session — fragile). **Recommend (a)** — the data exists and the refresh semantics neutralize D28.
   Whichever is chosen, the position read must be **owner-only**, never the public now-playing response.
2. **Privacy / gating tier of the lyrics read endpoint (blocks Step 1)** — owner-JWT-gated (Cognito,
   like `GET /api/playback/spotify-token`) vs edge_guard-only (like `/api/library/*`). The now-playing
   endpoint is an **"intentionally-public single-admin vanity read"** (D28); lyric text is third-party
   copyrighted research data with the corpus RFC's stricter *"never in any shared response"* bar, so
   the recommendation is **JWT owner-only**. This is a real **inconsistency** with how now-playing is
   served today — confirm deliberately, don't default it.
3. **Viewer surface type (blocks Step 2)** — full-bleed **overlay** (reuse `.lf-scrim` +
   `useDismissable`, matches the existing modal pattern) vs a dedicated **full-page route** (e.g.
   `/profile/lyrics/[trackId]` — gives mobile back-button + deeplink semantics). Decide.
4. **Focus unit + parsing (blocks Step 2)** — direction: focus unit = a **line** (plain = newline
   split; synced = the LRC timestamped line, timestamps hidden). Open sub-points: when **both**
   `lyric_plain` and `lyric_synced` exist, which defines the line breaks? When **only synced** exists
   (~9% of `matched`, `lyric_plain` is `''`), the viewer must parse `[mm:ss.xx] text` to extract text —
   confirm. Stanza vs single-line emphasis is a step-time design call.
5. **Idle / 최근 재생 dynamic behavior (blocks Step 4)** — when nothing is actively playing (now-playing
   falls back to "최근 재생"), does the dynamic entry open the **last-played** track's lyrics (no
   position), or disable until active playback?
6. **Translation read contract (blocks Step 5, not the MVP)** — what shape does the future translation
   RFC expose? Recommendation: a per-line/unit Korean translation keyed to the same focus units
   (line-index aligned to `lyric_plain` / `lyric_synced`). The viewer agrees this now so the producer
   fills it later without rework. Confirm on translation-RFC acceptance.
7. **Mobile next/previous input (blocks Step 2 detail)** — buttons only, or also a vertical swipe/drag
   gesture? Direct tap-to-focus is included either way.
8. **Static-entry surfaces + affordance (blocks Step 3)** — confirm the exact owner-only track
   surfaces to wire (분석 버킷 `LikedBoard`, `AlbumDetail` tracklist, Pocket tray, Overview) and the
   affordance shape per surface.

## Acceptance criteria

- The shared viewer opens from **both** a static owner-only track surface and the now-playing area.
- **원문** mode renders for any `matched` track; correct empty states render for `no_lyrics` /
  instrumental / unresolved / missing-row.
- Focus is movable only by **manual** next/previous/direct-select; **no** continuous time-driven
  progression exists.
- Dynamic mode's manual refresh reloads the current track and, where available, the playback position;
  position may initialize focus once and never auto-advances.
- **원문+번역** and **번역** modes are present and correctly disabled per-track until translation data
  exists.
- **No public API schema, public page, search index, bucket/post, or shared/edge-cached response**
  references or exposes lyric text or its presence (privacy gate — non-negotiable).
- The lyrics read endpoint is reachable **only** by the authenticated owner (JWT), not by edge_guard
  alone.
- All `pnpm lint` + `astro check` + backend `pytest` pass; each step's real-browser verification
  quoted in its PR.

## No-go conditions

- Any design lands lyric text (or its presence) in a public API, public page, search result, or shared/
  edge-cached response → **design rejected** (privacy boundary is non-negotiable; same as corpus RFC).
- The lyrics read endpoint **cannot** be gated owner-only (JWT) → Steps 1–4 **blocked** until it can;
  no edge_guard-only fallback for lyrics.
- Translation is made a **hard dependency** of the MVP → **reject**; the viewer must ship 원문-first and
  degrade gracefully.
- On-demand playback position is **impossible** without a full player → dynamic entry keeps the track
  but **drops position** (or dynamic defers); static still ships. Continuous-progression is never added
  to "rescue" this.
- Crowd-sourced lyric correctness cannot be lived with even as private reading aid → **shelve the
  viewer** (the corpus stays as research storage).

## Relationship to later work

This RFC is the **first consumer** of FEAT-lyrics-corpus and the **first intended reader** of the
future translation RFC. It deliberately stops at *reading and rendering* lyrics for the owner — it does
not collect, translate, interpret, synchronize, or republish. Keeping the viewer strictly read-only and
owner-only preserves the corpus's privacy boundary and leaves translation production, interpretation,
and any public surface each to their own RFC.

## Decisions log

Filled in during execution.

| Date | Decision | Step |
|------|----------|------|
| 2026-07-02 | Viewer is the first consumer of FEAT-lyrics-corpus; reads `track_lyrics`, never writes/matches | 0 |
| 2026-07-02 | Owner-only, never public/shared/edge-cached — corpus privacy boundary carried forward unchanged | 0 |
| 2026-07-02 | Three modes 원문 / 원문+번역 / 번역; translation is an optional input, MVP ships 원문-first | 0 |
| 2026-07-02 | Manual focus only (next/prev/direct-select); continuous playback-time-driven progression out of scope | 0 |
| 2026-07-02 | Dynamic entry reuses NowPlaying for **track identity only**; playback position is NOT in the public now-playing response (D28 omits `progress_ms`) — position needs a separate owner-only read; source = OQ1 | 0 |
| 2026-07-02 | Focus unit direction = line-level (plain newline-split; synced = LRC timestamped line, timestamps hidden); exact granularity + plain/synced parsing open (OQ4) | 0 |
| 2026-07-02 | Static entries are owner-only track surfaces; public review tracklist excluded | 0 |
