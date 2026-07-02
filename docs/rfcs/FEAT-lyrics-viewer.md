# FEAT-lyrics-viewer: Authenticated full-screen lyrics viewer overlay

- **Status**: in-progress
- **Owner**: 박지훈
- **Created**: 2026-07-02
- **Plan row**: `plan.md` → FEAT-lyrics-viewer

---

## Goal

A single **full-screen lyrics viewer overlay** (not a route) that renders, for the **currently
playing track only**, the project-normalized lyric content produced by FEAT-lyrics-corpus
(`track_lyrics`). The viewer emphasizes one focused line at a time while visually de-emphasizing the
surrounding lines (Spotify-mobile lyrics as the visual reference), and the owner moves the focus
**manually** — previous / next controls plus vertical swipe/drag, and direct tap-to-focus.
**Continuous playback-time-driven progression is out of scope.**

This RFC is responsible **only** for the overlay viewer UX and for **consuming** the contracts
produced by three dependency RFCs ([Dependencies](#dependencies)). It does **not** define playback
product strategy, the shared track-click interaction, or the lyric normalization model — those land in
their own RFCs, and the viewer conforms to whatever they produce.

## Non-goals

- **A dedicated route.** The viewer is a full-screen overlay (reusing `.lf-scrim` + `useDismissable`),
  not a `/profile/lyrics/[trackId]` page. No deeplink/back-button route semantics.
- **Static entry surfaces — for now.** No static entry points (workbench rows, album tracklists, tray
  items, overview collections) are defined in this RFC. Static entry is deferred until
  **ARCH-frontend-component-map** identifies the real shared track-click interaction flow and the
  overlay's state ownership; this RFC wires nothing until that lands.
- **Synced-only as raw plain text.** The viewer never renders synced-only lyrics by stripping timestamps
  or falling back to a raw plain-text dump. It consumes the **project-normalized lyric segments** from
  **ARCH-lyrics-normalization-model** only; if normalization hasn't produced consumable segments for a
  track, that track has no viewable lyric here.
- **Translation — anything.** Translation UI, translation APIs, and translation authoring are out of
  scope. LLM-based translation is a separate future RFC. This viewer renders **original lyrics only**;
  there is no 원문+번역 / 번역 mode and no dormant translation hook. (Previously proposed translation
  display modes are removed.)
- **Lyrics collection / matching / re-matching / writing.** FEAT-lyrics-corpus owns `track_lyrics`. This
  RFC only reads.
- **Lyrics editing, interpretation, or research.** No correction UI, no slang/meme/context notes, no
  per-line commentary. The viewer shows text; it does not annotate.
- **Automatic synchronization.** No continuous playback-time-driven progression, no auto-scroll, no
  karaoke-style time tracking. Synced timestamps may be used only to **define units** and, optionally,
  to set the **initial** focus on a manual refresh — never to advance it.
- **Playback controls or a custom playback layer.** No play/pause/seek/next-track UI, and no custom
  player implementation. How playback state and position reach the viewer is a contract this RFC
  **consumes** from **RESEARCH-playback-product-architecture** — the viewer does not build it.
- **Any public, shared, or edge-cached exposure.** Lyrics stay readable by authenticated users only;
  write/update/publish require an application-managed operator capability. No public page, public API,
  public search, public route, or shared/edge-cached payload carries lyric text or its presence. Same
  non-negotiable boundary as the corpus RFC.

## Dependencies

Three dependency RFCs produce contracts this viewer consumes. Each owns its topic; this RFC does not
re-derive them.

### RESEARCH-playback-product-architecture

- **Playback product strategy** — what playback surface the product actually ships and how.
- **Spotify SDK / API capability** — which SDK/API operations are available for reading current track
  **and** playback position.
- **Custom control layer / custom playback implementation** — whether any custom control or playback
  layer is needed, or whether platform capability suffices.

The viewer depends on this RFC to settle where playback state and position come from. Until it does,
the dynamic entry cannot bind position; it degrades to track-identity-only (no fallback to recent
history — see [Entry conditions](#entry-conditions)) rather than blocking.

### ARCH-frontend-component-map

- **Track-click ownership** — which component owns the track-click interaction.
- **Shared interaction components** — the real shared track-click flow the viewer binds into.
- **Overlay state ownership** — which route/component owns the overlay's open/close state.
- **Affected routes** — where the overlay mounts and which routes are touched.

The viewer depends on this RFC before wiring any entry. **No static entry surfaces are defined here.**
When this lands, the viewer binds its open action to the shared track-click contract it produces.

### ARCH-lyrics-normalization-model

- **Plain / synced normalization** — how `lyric_plain` and `lyric_synced` normalize to a single shape.
- **Canonical lyric segments** — the segment/unit model the viewer renders (line / stanza / etc.) and
  its line-break source when both plain and synced exist.
- **Raw-source preservation** — whether raw sources are preserved alongside the normalized form.
- **Re-normalization** — how/when already-stored rows get re-normalized.
- **Synced-only exposure rules** — how a synced-only row becomes consumable **without** the viewer
  stripping timestamps or raw-text fallback (see non-goal).

The viewer depends on this RFC for the **normalized segment contract** it renders. The viewer does no
LRC parsing, no plain/synced selection logic, and no timestamp stripping of its own — it renders the
segments the model produces, full stop.

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
- **No translation data, and none is expected here.** There is no Korean-translation column, table, or
  contract, and this RFC introduces none. The viewer renders original lyrics only.
- **Now-playing area exists (the dynamic anchor).** `myblog_front/src/components/member/NowPlaying.tsx`
  (`banner | full | list` variants) shows `track / artist / album / album_cover_url / is_playing /
  updated_at`, fed by a **worker cache snapshot** via `GET /api/library/now-playing`
  (`getNowPlayingData()` in `src/components/member/spotify.api.ts`). It is **manual-refresh only** (no
  live polling) and falls back to "최근 재생" when idle. The backend `NowPlayingResponse`
  (`myblog_backend/app/api/schemas.py:589-603`) is an **intentionally-public single-admin vanity read
  (edge_guard-only)** that **deliberately omits `progress_ms` / `duration_ms` (D28)** — *"a ≤1h-stale
  snapshot can't advance a progress bar."* The worker does fetch and store `progress_ms` /
  `duration_ms` in the snapshot (`worker/service/listening_sync_service.py:254-313`), so position data
  exists server-side but is not exposed. **How playback state and position reach the viewer is owned by
  RESEARCH-playback-product-architecture** — not redesigned here.
- **Spotify streaming/playback plumbing exists, separate from now-playing.**
  `myblog_front/src/lib/spotifyPlayback.ts` (`ensureSdk`, `requestPlayback(target)`, `resolveProviderUri`)
  fires only on ▶ clicks and mints a server streaming token via `GET /api/playback/spotify-token`,
  whose scopes (FEAT-spotify-streaming-playback) include **`user-read-playback-state`**. Whether and how
  the viewer consumes playback capability is settled by RESEARCH-playback-product-architecture.
- **Overlay primitives to reuse.** `src/lib/useDismissable.ts` (ESC + focus trap/restore); `.lf-scrim`
  full-viewport scrim, `.lf-modal-card`, `.lf-slideover` (`src/styles/member.css`), `--z-overlay: 80`
  (`src/styles/global.css`). A dedicated full-bleed viewer panel is expected (the centered 600px
  `StandardModal` is not the Spotify-mobile shape).
- **Authed request path.** Authed API calls go through `apiFetch` (`src/lib/api.ts:65-88`,
  `Authorization: Bearer <token>`, 401 → refresh-once). `/profile` is gated client-side by
  `src/scripts/profile.guard.ts` (`isLoggedIn()` → `goLogin(true)` otherwise). **`/api/library/*`
  reads (incl. now-playing) are edge_guard-only (no JWT)** — lyrics carry the stricter *"never in any
  shared response"* bar and must **not** ride that pattern (see [Access & authorization](#access--authorization)).

## Target state

A single **full-screen overlay** lyrics viewer, readable by **authenticated users**, that renders the
normalized lyric segments of the **currently playing track**:

- **Full-screen overlay.** Mounted over the current route (not a route itself) on `.lf-scrim` +
  `useDismissable` (ESC + focus trap/restore). Mobile-first full-bleed (Spotify-mobile reference),
  adapted up to desktop.
- **Focus-one-line reading.** Exactly one focus unit (the segment shape from
  ARCH-lyrics-normalization-model) is emphasized (larger, full contrast); immediate neighbors are
  de-emphasized (smaller, dimmed); the rest is scrollable but recessed. The viewer renders the
  normalized segments as given — it does **not** strip timestamps or fall back to raw text for
  synced-only rows.
- **Manual navigation.** Previous / next **controls** **plus** a **vertical swipe/drag gesture**, and
  direct **tap-to-focus** on any segment. No auto-advance.
- **Entry — active playback only.** The entry point opens the viewer for the **currently playing
  track**. When there is no active playback, the entry point is **hidden** and there is **no fallback
  access from recent history.** Static entry surfaces are **not defined here** — they wait on
  ARCH-frontend-component-map (see [Dependencies](#dependencies)).
- **Manual refresh.** A single refresh control re-reads the current track and the available playback
  state/position. On a track change the viewer swaps segments; on a position-only change the focus may
  be re-initialized to the matching segment (one-shot) — it never auto-advances thereafter.
- **Availability-aware empty states.** `no_lyrics` / instrumental → "가사 없음 (연주곡)";
  `not_found` / `ambiguous` / `review_required` / no row → "아직 연결된 가사가 없어요". The viewer never
  implies a missing lyric is definitive.
- **Read API (authenticated).** A backend endpoint reads `track_lyrics` by track id and returns the
  lyric content + `match_status` **only to authenticated users** — JWT-gated at the API Gateway
  authorizer, **not** edge_guard-only. New JWT GET route → matching `infra/apigateway.tf` entry + apply.
  No public schema references it.
- **Operator-gated writes (contract, not implemented here).** Write, update, and publish operations on
  lyrics are gated by an **application-managed operator capability**, not a hard-coded single owner
  identity. This RFC does not implement write/update/publish endpoints — it records the boundary so a
  future operator-surface is capability-checked, not identity-checked.
- **Privacy invariant unchanged.** Lyric text and its presence remain absent from every public route,
  public page, public API schema, public search, and shared/edge-cached response. The viewer is the one
  legitimate reader, and it is authenticated-only.

## User flows

- **Open (active playback).** Owner is on `/profile` with the now-playing area showing an actively
  playing track. Opening the viewer loads that track's normalized segments, focus on the first segment
  (or, when position is available, on the segment matching the current playback position — one-shot).
- **No active playback.** The entry point is hidden; there is no recent-history fallback to open.
- **Manual refresh.** While open, the owner taps refresh; the viewer re-reads the current playback
  state — if the track changed, segments swap; if only position changed, focus is re-initialized to the
  matching segment. No continuous tracking. If playback has stopped, refresh reflects "no active track"
  rather than substituting a recent one.
- **Focus navigation.** Owner moves the focus with previous / next controls, with a vertical swipe/drag
  gesture, or by direct tap on any segment; the emphasized segment and de-emphasized neighbors reflow
  accordingly.

## Display & navigation

- **Original lyrics only.** One mode: render the normalized segments for the current track. There is
  no translation mode and no mode selector.
- **Visual reference: Spotify mobile lyrics.** One focused segment emphasized; immediate neighbors
  de-emphasized; the rest readable by scroll but recessed. Full-bleed, mobile-first.
- **Focus unit = the segment from ARCH-lyrics-normalization-model.** The viewer does not choose
  line vs. stanza, does not split plain on newline, and does not parse LRC — it renders whatever
  segment shape the normalization model produces. Synced timestamps are not rendered to the user; they
  only enable optional one-shot initial positioning on refresh.
- **Navigation inputs: all three.** Previous/next controls, vertical swipe/drag gesture, and direct
  tap-to-focus — all move the emphasized segment.

## Access & authorization

- **Read = authenticated.** Lyric reads are JWT-gated at the API Gateway authorizer (modeled on
  `GET /api/playback/spotify-token`'s `require_cognito_token`), **not** the edge_guard-only
  `/api/library/*` pattern. This is a deliberate tier split: now-playing is an intentionally-public
  single-admin vanity read (D28); lyrics carry the corpus RFC's stricter *"never in any shared
  response"* bar and ride JWT only.
- **Write/update/publish = operator capability.** Gated by an application-managed operator capability,
  **not** a hard-coded single owner identity. No such endpoint is implemented in this RFC.
- **No public exposure.** No public route, public page, public API schema, public search, or
  edge-cached payload references lyric text or its presence.

## Dependencies on lyric availability

- **Original lyrics** depend on the corpus (already satisfied by FEAT-lyrics-corpus) **and** on the
  normalized segment contract from ARCH-lyrics-normalization-model. A track is viewable iff (a) it
  has a `matched` `track_lyrics` row **and** (b) the normalization model has produced consumable
  segments for it. Synced-only rows that the model has not normalized are **not** rendered by raw
  fallback — they show the "no viewable lyric" empty state.

## MVP boundaries

- **In scope (MVP):** full-screen overlay; authenticated-only read; render normalized segments;
  focus-one-segment emphasis; previous/next + vertical swipe/drag + tap-to-focus; active-playback-only
  entry; manual refresh of track and (if available) position with optional one-shot initial focus;
  availability empty states.
- **Out of scope (explicit):** a dedicated route; static entry surfaces (await
  ARCH-frontend-component-map); raw-text synced-only fallback (await ARCH-lyrics-normalization-model);
  translation UI/API/authoring (future RFC); continuous progression / auto-scroll / karaoke sync;
  interpretation/annotation; playback controls or a custom playback layer; public or shared exposure;
  editing; write/update/publish operators (boundary recorded only).

## Steps

Milestone-level. Hard rule #4 — one step per session, prod-observe / direction-recheck gate between
steps. Detailed endpoint/component/contract design is produced **at the start of each step**, reviewed,
and not pre-committed here (per RFC scope: behavior/flows now, implementation later). Branch/commit per
repo (`feedback-nested-repo-branch-per-repo`). Steps that consume a dependency RFC are **blocked**
until that RFC produces its contract.

### Step 0 — RFC + plan.md pointer (this document, docs-only)

This RFC + a one-line `plan.md` Backlog pointer. No code, no schema.

**Verification**: doc review against `TEMPLATE.md` / README required sections. `git diff --stat` shows
only the doc files.

---

### Step 1 — authenticated lyrics read API (backend)

A new **JWT-gated (authenticated-only)** endpoint that reads `track_lyrics` by track id and returns
the normalized lyric content + `match_status`. **Not** edge_guard-only — modeled on
`GET /api/playback/spotify-token` (`require_cognito_token`). New JWT GET route → matching
`infra/apigateway.tf` entry + apply. No public schema/response type references it; no shared/edge-cached
response carries lyric text. **Endpoint key (decided 2026-07-02, dependency-RFC review): the
endpoint accepts the `spotify_track_id` the live playback read returns (`item.id`) and resolves
it server-side to the catalog `Track.id`** (reverse of `PlaybackService.resolve_uri`'s direct
read) — one round trip, no separate resolve endpoint.

**Dependency**: the response shape conforms to the segment contract from ARCH-lyrics-normalization-model.
If that contract is not yet produced, this step exposes the raw `match_status` + a marker that segments
are pending, and finalizes the segment shape when the contract lands.

**Verification**: authenticated user gets lyrics for a `matched` track and the correct empty-state
payload for `no_lyrics` / unresolved / missing-row tracks; an unauthenticated request is rejected; a
schema check confirms no public type references lyrics; backend `pytest` passes.

**Rollback**: remove the route + the `apigateway.tf` entry (no consumer depends on it yet).

---

### Step 2 — full-screen Lyrics Viewer overlay (front, MVP)

A full-bleed, authenticated-only, mobile-first overlay reusing `useDismissable` + `.lf-scrim`.
Render normalized segments with focus-one-segment emphasis (focused segment emphasized, neighbors
de-emphasized) and manual **previous/next controls + vertical swipe/drag + tap-to-focus** navigation.
Availability-aware empty states (가사 없음 / 연결된 가사 없음). Reads via `apiFetch` against the Step 1
endpoint. Launched in isolation first (e.g., a debug/owner entry) before wiring the dynamic entry.

**Dependency**: consumes the segment contract from ARCH-lyrics-normalization-model and the overlay
state ownership from ARCH-frontend-component-map. Blocked on the segment contract; blocked on the
overlay-state side of the component-map if it isn't settled by then.

**Verification**: real-browser click-through (`astro check` + `pnpm lint` pass; lint alone misses
render/event regressions — BUG-11→12); swipe/drag and control navigation and tap-to-focus confirmed on
the live DOM; authenticated-only (not reachable unauthenticated); mobile + desktop widths (repro with
prod-realistic long lyrics — `feedback-ui-repro-realistic-data`).

**Rollback**: remove the component + its island mount (no entry wired yet).

---

### Step 3 — dynamic entry + manual refresh (front, active-playback-only)

Open the viewer from `NowPlaying` for the **currently playing track only**. **Track identity
(including the track id — the now-playing snapshot stores no track id) and playback state/position**
come from the contract produced by RESEARCH-playback-product-architecture (live `GET /v1/me/player`
→ `item.id`; not re-derived here). When there is **no active playback**, the
entry point is **hidden** — no recent-history fallback. A manual refresh re-reads track + (if available)
position; on a track change the viewer swaps segments, on a position-only change the focus is
re-initialized (one-shot). Continuous progression stays out of scope. If the playback contract hasn't
settled position, ship track-only refresh (no position) and record the degradation — but still
active-playback-only, never recent-history fallback.

**Dependency**: RESEARCH-playback-product-architecture must settle playback state/position source before
position binding; ARCH-frontend-component-map must settle the track-click/overlay-state flow the
now-playing tap binds into.

**Verification**: opening from now-playing with an active track loads that track's lyrics; with no
active playback the entry is gone and no fallback opens; refresh swaps track when it changed and
re-initializes focus when only position changed; no auto-advance occurs; pre-merge CDP click-through.

**Rollback**: remove the now-playing entry; the viewer is untouched.

---

### (Deferred) static entry surfaces

Static entry (workbench rows, album tracklists, tray items, overview collections) is **not a step
here**. It is deferred until **ARCH-frontend-component-map** identifies the shared track-click
interaction flow and overlay state ownership the viewer should bind into. When that lands, a follow-on
step wires the entry against the real shared component — not the candidate surfaces enumerated in
earlier drafts.

## Risks

- **Privacy leak (highest).** Lyrics are third-party-copyrighted research data with a "never in any
  shared response" bar. Mitigation: the read endpoint is **JWT-gated (authenticated-only)**, not
  edge_guard-only; the viewer lives only on authenticated surfaces; acceptance gate = no public
  route/page/schema/search/shared response references lyric text or its presence.
- **Privacy tier drift.** Future contributors may assume lyrics can ride the edge_guard-only
  `/api/library/*` pattern. Mitigation: stated explicitly here + the acceptance gate.
- **Single-owner hard-coding.** Wiring writes to one identity couples the system to a person.
  Mitigation: write/update/publish recorded as an **application-managed operator capability**, not an
  identity (even though no write endpoint ships in this RFC).
- **Dependency RFCs slip.** Three contracts (playback source, track-click flow, normalized segments)
  are owned externally and can block Steps 1–3. Mitigation: each step states its dependency and a
  degraded path (track-only, no position, no static entry) rather than blocking the MVP entirely.
- **Synced-only rendered wrong.** A contributor might "rescue" a synced-only row by stripping timestamps
  client-side. Mitigation: the viewer consumes normalized segments only and does no LRC parsing; rows
  the normalization model hasn't covered show the empty state, never a raw dump.
- **Position shown as live (D28).** Even when exposed, a manual-refresh position is a single moment —
  the viewer must never present it as a ticking/advancing state. Mitigation: one-shot initial focus
  only; continuous progression stays out of scope.
- **Focus/scroll on long lyrics, mobile.** Heavy lyrics must still keep the focused segment legible and
  neighbors scannable. Mitigation: Spotify-mobile emphasis model, real-browser mobile-width
  verification (`feedback-ui-repro-realistic-data`).
- **Crowd-sourced text correctness.** Corpus text is untrusted for factual correctness. Out of scope to
  fix here, but the viewer should read as an aid, not assert authority.

## Remaining open questions

The previously-listed OQs are resolved or moved to dependency RFCs:

- ~~Viewer surface type (overlay vs route)~~ → resolved: **full-screen overlay**.
- ~~Privacy / gating tier of the read endpoint~~ → resolved: **JWT-gated, authenticated-only**;
  write/update/publish gated by an **operator capability**, not a hard-coded owner.
- ~~Idle / 최근 재생 dynamic behavior~~ → resolved: **active playback only; hide the entry, no fallback**.
- ~~Mobile next/previous input~~ → resolved: **previous/next controls + vertical swipe/drag + tap-to-focus**.
- ~~Static-entry surfaces + affordance~~ → moved to **ARCH-frontend-component-map**; not defined here.
- ~~Playback-position source + the D28 boundary~~ → moved to **RESEARCH-playback-product-architecture**.
- ~~Focus unit + plain/synced parsing; synced-only handling~~ → moved to **ARCH-lyrics-normalization-model**.
- ~~Translation read contract~~ → closed: **translation is out of scope** (UI/API/authoring + LLM
  translation are a future RFC).

No viewer-specific question remains genuinely unresolved at this stage — the rest is
dependency-gated and produced at step-time. If a viewer-only question surfaces during a step, it is
recorded there.

## Acceptance criteria

- The viewer opens as a **full-screen overlay** (not a route) for the **currently playing track**, and
  the entry point is **hidden with no fallback** when there is no active playback.
- Rendered content is the **normalized segment contract** from ARCH-lyrics-normalization-model — never
  a client-side timestamp strip or raw-text fallback for synced-only rows.
- Focus is movable only by **manual** previous/next controls, vertical swipe/drag, or direct
  tap-to-focus; **no** continuous time-driven progression exists.
- Manual refresh reloads the current track and, where the playback contract provides position,
  re-initializes focus once and never auto-advances.
- The lyrics read endpoint is reachable **only** by authenticated users (JWT), not by edge_guard alone.
- Write/update/publish are gated by an **application-managed operator capability** (no hard-coded single
  owner) — verified at the contract/boundary level, since no write endpoint ships here.
- **No public route, public page, public API schema, public search, or shared/edge-cached response**
  references or exposes lyric text or its presence (privacy gate — non-negotiable).
- All `pnpm lint` + `astro check` + backend `pytest` pass; each step's real-browser verification
  quoted in its PR.

## No-go conditions

- Any design lands lyric text (or its presence) in a public route, public page, public API, public
  search, or shared/edge-cached response → **design rejected** (privacy boundary is non-negotiable; same
  as corpus RFC).
- The lyrics read endpoint **cannot** be gated authenticated-only (JWT) → Steps 1–3 **blocked** until it
  can; no edge_guard-only fallback for lyrics.
- Writes are wired to a **hard-coded single owner identity** rather than an operator capability →
  **reject** the write surface (no write endpoints ship in this RFC anyway).
- The viewer renders synced-only lyrics by stripping timestamps or raw-text fallback instead of
  consuming normalized segments → **reject**; wait for ARCH-lyrics-normalization-model.
- Translation is made a dependency of this RFC → **reject**; translation is out of scope.
- Continuous-progression is added to "rescue" a missing position source → **reject**; degrade to
  track-only instead.

## Relationship to later work

This RFC is the **first consumer** of FEAT-lyrics-corpus and a **consumer** (not producer) of three
dependency RFCs: RESEARCH-playback-product-architecture, ARCH-frontend-component-map, and
ARCH-lyrics-normalization-model. It deliberately stops at *reading and rendering normalized lyrics for
authenticated users* — it does not collect, translate, interpret, synchronize, republish, or define the
playback/track-click/normalization contracts it depends on. Translation production is explicitly a
separate future RFC.

## Decisions log

| Date | Decision | Step |
|------|----------|------|
| 2026-07-02 | Viewer is a full-screen overlay, not a dedicated route | 0 |
| 2026-07-02 | Reads are authenticated-only (JWT); writes/update/publish gated by application-managed operator capability, not a hard-coded owner | 0 |
| 2026-07-02 | No public routes / public search / public pages / cached public payloads for lyrics | 0 |
| 2026-07-02 | Entry is active-playback-only; no entry when idle and no recent-history fallback | 0 |
| 2026-07-02 | Navigation = previous/next controls + vertical swipe/drag + direct tap-to-focus; manual only | 0 |
| 2026-07-02 | Static entry surfaces deferred to ARCH-frontend-component-map; not defined here | 0 |
| 2026-07-02 | Viewer consumes project-normalized segments only; no client-side timestamp strip or raw-text fallback | 0 |
| 2026-07-02 | Translation UI/API/authoring out of scope; LLM translation is a future RFC; original-lyrics-only | 0 |
| 2026-07-02 | Playback product strategy, Spotify SDK/API capability, custom control layer → RESEARCH-playback-product-architecture | 0 |
| 2026-07-02 | Track-click ownership, shared interaction components, overlay state ownership, affected routes → ARCH-frontend-component-map | 0 |
| 2026-07-02 | Plain/synced normalization, canonical segments, raw-source preservation, re-normalization, synced-only exposure rules → ARCH-lyrics-normalization-model | 0 |
| 2026-07-02 | Dependency-RFC review: Step 1 endpoint keyed by `spotify_track_id` (server-side resolve → `Track.id`, one round trip); Step 3 track identity comes from the live playback read (`item.id`), not the snapshot (no track id column) — aligned to RESEARCH-playback-product-architecture OQ1/OQ2 | 0 |
| 2026-07-02 | Status draft → in-progress (owner approval in session; all three dependency RFCs done) | 1 |
| 2026-07-02 | Step 1 route = `GET /api/lyrics/{spotify_track_id}` (owner pick; own JWT route, not under `/api/tracks/*` — keeps lyrics off catalog-shaped public-looking paths) | 1 |
