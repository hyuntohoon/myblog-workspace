# FEAT-personal-release-tracking: Personal release tracking (개인 발매 피드 / Release Radar)

- **Status**: accepted (2026-07-15, owner in-session approval — "시작하자"; H1 measured
  2026-07-14 against live #548 poller data: **thin-but-usable, not first-class**.
  **Step 1–3 착수 2026-07-15** — 2-phase execution: Step 1 schema → Steps 2∥3
  parallel via codex worktrees. **Step 4** (multi-source upcoming ingestion)
  remains gated on **OQ2 (per-source ToS) + OQ5 (#548 reconcile)** — owner
  decisions; **Step 5** (front) remains gated on an **owner design gate**.
  These stay open under `accepted`; they do not block Steps 1–3.)
- **Owner**: TBD
- **Created**: 2026-07-08
- **Plan row**: `plan.md` → FEAT-personal-release-tracking
- **Follow-on to**: `FEAT-release-calendar` (#548), which reserved *"per-user
  subscriptions + 확인 state ... Separate RFC ... after
  `FEAT-multi-user-accounts` Phase 0"*. Phase 0 shipped (0c #565, 2026-07-08),
  so this is that RFC.
- **Relationship**: this is the **personalization layer on top of** #548's
  shared release-event data — it does **not** overturn #548's public v1. The
  public home card (Track A) and public calendar (Track B) remain as designed;
  this RFC adds per-user tracked artists, a personalized feed, and Buckit-based
  import. Where this RFC diverges from #548's locked decisions (multi-source
  discovery), that divergence is called out explicitly and left for owner
  reconciliation at accept — see **Divergences from #548**.

> **Status note.** Captures a 2026-07-08 brainstorm + one rebuttal round + a
> UI design exploration. **Accepted 2026-07-15** (owner) after H1 was measured
> against live #548 poller data (2026-07-14: thin-but-usable, **not**
> first-class). Steps 1–3 are implementation-ready and began 2026-07-15.
> Step 4 remains gated on OQ2/OQ5 (owner) and Step 5 on an owner design gate;
> both stay open under `accepted`.

---

## Goal

**One sentence**: a personalized feed of upcoming and recently released music
from artists the user explicitly tracks, with reliability shown as a trust
grade, where confirmed releases connect into the existing listen / review /
Buckit flow.

Two primary states, each split into two categories:

- **Upcoming (예정)** / **Recently Released (최근 발매, rolling 30 days)**
- within each: **Albums & EPs** (grouped) / **Singles** (separated)

This is a *personal management experience*, not a public discovery calendar
(that is #548). The user builds and owns a tracked-artist list; the feed is the
product, and list management is incidental (must not read as a
subscription-settings screen).

## Core stance

- **User-selected tracked artists.** The user picks artists directly. Buckit is
  a **snapshot import source only** — selecting a Buckit yields artist
  candidates derived from its artists / albums / tracks / reviews, which the
  user confirms into the tracked list. **After import the tracked list is
  independent**: deleting a Buckit item, deleting a Buckit, or adding Buckit
  content never changes tracked artists unless the user explicitly re-imports.
- **Release events are shared domain data; user↔event visibility is derived.**
  N users tracking one artist do not create N release events.
- **Reliability is first-class and graded.** "Observed from a source" and
  "confirmed in the catalog" are different levels of certainty and are shown as
  such. Upcoming release info may be delayed, cancelled, renamed, reclassified,
  or vanish from a source — the UI never presents an unconfirmed date as firm.

## Non-goals (v1)

- **Not the public discovery calendar / home card** — that is #548, unaffected.
- **No notifications / push / e-mail.** In-app only. Even an in-app "new since
  last visit" marker is **deferred** (owner, 2026-07-08 — did not want that much
  personalization surface in v1).
- **No auto-merge of ambiguous releases** — incorrectly merging two different
  releases is more harmful than failing to merge (bias to under-merge).
- **No full-catalog daily sweep** — reconciliation is scoped to tracked artists.
- **No rumor / news / social scraping** to fabricate "upcoming" — only sources
  that natively expose a release with a date.
- **No editorial auto-generation** from the feed (possible Editor Buckit
  follow-on, not here).
- **No market-specific availability gating** — global; market is availability
  metadata, not an identity or bucketing axis (see Consistency strategy).
- **No public global release calendar** — this feed only ever shows tracked
  artists.

## Domain model — concepts that must stay separate

These are different layers and must not be collapsed; the separation cannot be
retrofitted later.

| Concept | Layer | Notes |
|---|---|---|
| **tracked artist** | personalization | user↔artist edge; a snapshot after Buckit import, then independent. Anchored to our catalog artist id (see below). |
| **release event** | shared domain | one per real-world release; attributable to one or more artists. |
| **release type** | attribute of event | `album` \| `ep` \| `single` \| `other`; **provisional while upcoming, locked at catalog confirmation**, re-resolved only on an authoritative (catalog) change. |
| **release status** | shared lifecycle | announced/upcoming → released; plus `uncertain` (observed-but-unconfirmed). "Source dropped it" ≠ cancelled. |
| **source observation** | audit layer | a per-source sighting ("Spotify saw X", "MB saw Y"). Never blind-merged; the evidence layer under an event. |
| **confirmed catalog item** | catalog link | FK to the existing `albums` row; **nullable** until hard-key matched. |
| **user-specific visibility** | personalization | (tracked artists ∩ release events) + per-user hide/seen state. Derived, not per-user duplicated. |

**Artist identity anchoring (prerequisite).** Tracking and multi-source
attribution only work if a release from any source can be attached to *the same
artist the user tracked*. External source artist IDs differ and collide;
tracked artists must anchor to our catalog artist entity
(`artists.id` / `musicbrainz_id` / `spotify_id`), and external-source artists
must be resolved to that canonical id before attribution.

## Consistency strategy (multi-source, minimize incoherence)

The user wants upcoming data from **any available API**, not Spotify-only. That
raises the reconciliation risk #548 already flagged. To keep the feed coherent:

- **One spine source per event.** Other sources **corroborate / enrich only**
  (provenance-tagged), never overwrite or average. No "vote the date across 3
  sources".
- **Merge only on a hard identity key** (UPC / ISRC / exact). Ambiguous → keep
  separate, show one, mark the rest as candidates. Under-merge bias
  (오병합 > 미병합). Dedup via NOT-EXISTS guards, **not** bare `ON CONFLICT`
  against a partial index (memory `reference-onconflict-partial-index-break`).
- **Catalog confirmation collapses to a single truth.** The messy multi-source
  world lives only in the *observed / upcoming* zone; once an event hard-matches
  the catalog, the catalog is authoritative and upcoming-source noise stops
  mattering.
- **Reconcile only within tracked-artist scope** — never the whole catalog. The
  personalized nature bounds the collision surface.
- **Source trust ranking is for display selection only**; every observation is
  retained (catalog > hard-ID sources e.g. Apple/iTunes UPC > MusicBrainz >
  Wikidata/loose).
- **Market = availability metadata, not identity.** Same release across markets
  is **one event**; canonical timeline anchor = **earliest known release date**
  (deterministic upcoming↔recent bucketing + rolling-window placement).
  Per-market availability is informational only, never a bucketing key.

## Scope decisions locked this session (owner = user, 2026-07-08)

- Personalized, user-selected tracked artists + Buckit-derived candidate import
  (snapshot, independent after import).
- Tracked unit flexible — artist is primary; per-release tracking may be added
  later (not a v1 blocker).
- Upcoming may draw from **any API**, not Spotify-only, subject to the
  Consistency strategy.
- **Market global**; earliest-release-date is the canonical timeline.
- **Recently Released = rolling last 30 days.**
- Newly-tracked artist backfill = the **rolling window** (not from-track-time);
  initial load kept light.
- **Naming**: not "Calendar" — a personal release feed / watchlist
  (working name *Release Radar / Almanac*).
- **Rebuttal-round outcomes** (all adopted): trust badges reduced to **3**
  (`확정` / `예정` / `불확실`), sub-reasons (연결 대기 / 날짜 상충 / 미확인) as
  annotations not extra badges; **empty Upcoming shown honestly** with an
  add-artist prompt (the "fall back to Recently Released" option was
  **rejected** — it would blur the state/trust separation); collab card shows
  **"추적: {artist}"**; per-item type stays provisional until confirmation.
- **Deferred** (owner): in-app "new since last visit" marker.

## UI direction (explored, not final)

A design mockup was iterated this session (v3): an **almanac** — a month
**calendar navigator** (click a day → that day; click the month → the whole
month) beside a **card list**. Cards carry an **album cover + a circular artist
image + artist name**, a trust badge only when the state is exceptional
(예정 / 불확실), a date, and a one-line reason annotation. Calendar days with
releases are marked with rounded outline boxes colored by state. **Recently
Released confirmed** cards expose **▶ Play / ✎ Review / ＋ Buckit** actions;
upcoming / uncertain cards expose no actions and a reason line. Empty Upcoming
renders an honest "no announced releases — add more artists" state.

The UI shape is a later design-gate decision with the owner (`frontend-design`
skill applies; real-browser click-through incl. 390px mobile per DoD). Range
selection (day / week / month) is an open question.

Design exploration (claude.ai artifacts, owner-private — "더 다듬을 것", not
final):

- Almanac v3 (current — calendar navigator + riso duotone cards, stress-tested
  on adversarial data):
  <https://claude.ai/code/artifact/fa5fd24d-b9cf-47fe-b021-24560876b016>
- v1 grid mockup (rejected — read as a stiff dashboard):
  <https://claude.ai/code/artifact/3421b1cf-3227-4b18-93ab-7ff36a1c2258>

## Relationship to existing infra — reuse vs separate

- **REUSE (this RFC depends on #548 Track B landing first)**: the shared
  `artist_release_events` table, the MB upcoming poller, and the release-day
  confirmation inside `album_ingest` (#548 Steps 3–5) are exactly the shared
  release-event layer this feature personalizes. This RFC adds a per-user
  **`user_artist_tracks`** join (atop the anchored catalog artist), a Buckit
  import path, per-user visibility, and a personalized read endpoint.
- **SEPARATE / unaffected**: the public home "새 앨범" card (#548 Track A).

### Divergences from #548 (need owner reconciliation at accept)

> **Divergence 1 resolved 2026-07-11 (owner)**: #548's discovery lock was
> re-opened — its Track B discovery will be **redesigned multi-source**
> (corroborating hard-ID sources within watchlist scope), absorbing this RFC's
> source-expansion proposal at the shared `artist_release_events` layer (see
> #548 Decisions log 2026-07-11). OQ2 (per-source ToS review) and the H1
> density measurement remain open here.

- #548 locked discovery = **MB per-artist future queries + Spotify day-0 diff**,
  explicitly **rejecting a global MB sweep** (long-tail) and **not** integrating
  Spotify `/browse/new-releases` (removed / stale). This RFC proposes
  **additional hard-keyed sources** (e.g. Apple/iTunes pre-order) within tracked
  scope. Note the rejection in #548 was of a *global* sweep, not of adding
  corroborating hard-ID sources for *tracked* artists — but this is a real
  scope change and must be owner-confirmed (OQ2/OQ5).
- #548 v1 is **public, no user concept**; this RFC introduces the user layer it
  reserved. Not a reversal — an extension — but the owner should confirm the two
  surfaces (public calendar + personal feed) coexist rather than the personal
  feed replacing the public v1.

## Critical data caveat (already evidenced by #548)

#548's MusicBrainz probe (2026-07-06) is directly load-bearing here:

- Popular-tier **future window is nearly empty** — Taylor Swift future window =
  0 (genuine, not a query bug); global 30-day future ≈ 1,327 releases (1,207
  official), **long-tail dominated, no overlap with our catalog's popular tier**.

**Implication**: for a realistic tracked-artist set, **Upcoming will be thin**
from MB alone. Therefore (a) Upcoming should **not** be a dominant/default
surface until density is validated (H1); (b) the empty/sparse Upcoming state is
load-bearing UI, not an afterthought; (c) the "any API" expansion
(Apple/iTunes pre-order, Wikidata) is specifically motivated by this thinness —
its payoff is exactly what H1 must measure.

## Hypotheses to validate before implementation

- **H1 (blocks treating Upcoming as first-class)** — real observable upcoming
  volume and lead-time for a realistic tracked set across candidate sources.
  #548's probe already suggests MB-only is near-empty for the popular tier;
  measure whether adding sources changes this.
  **MEASURED 2026-07-14** (read-only probe over #548's live `artist_release_events`,
  ~46 h of poller data): future rows 57 across **47 / 1,533 = 3.1%** of the
  watchlist (MB 38 rows/37 artists + iTunes 19/17, overlap 7 → iTunes adds
  **+45% artist coverage** over MB-only); lead time p50 **31 d** / p90 62 d /
  max 80 d; type split 48 album / 6 single / 2 EP / 1 other; confirm link
  0/57 (all `announced`, expected pre-release). **Verdict: thin-but-usable,
  NOT first-class** — supports OQ1's "appears-only-when-present strip" over a
  tab. Caveat: ~46 h ≈ currently-announced inventory, not steady-state
  discovery; re-measure at #548's OQ4 checkpoint (~2026-07-27) before final
  placement.
- **H2** — new-release detection latency after release + dedup accuracy.
- **H3** — album/EP/single classification disagreement across sources.
- **H4** — release-event → catalog match rate (drives how often "confirmed →
  listen/review" actually connects).
- **H5** — collaborative-credit coverage across sources (missing credits leak a
  tracked artist's collab out of the feed).
- **H6** — Buckit → artist-candidate extraction quality / volume.

## Open questions

1. **Upcoming placement** (H1) — first-class tab, or an "appears-only-when-
   present" strip that vanishes when empty? Do not finalize before H1.
2. **Upcoming sources beyond MB** (OQ blocks multi-source) — Apple/iTunes
   pre-order, Wikidata, others; plus a source trust ranking and a licensing/ToS
   check per source before betting on it.
3. **Merge identity thresholds** — decide against real match failures /
   over-merge samples, not upfront.
4. **Type-resolution rules** (H3) — which source wins the album/EP/single call
   at confirmation.
5. **Reconcile "any API" with #548's locked discovery decisions** (owner).
6. **Range selection UX** — day / week / month in the calendar navigator.
7. **Tracked-release granularity** — support tracking a single announced
   release (not just an artist) in v1, or later?

## Steps (shape only — not sequenced; needs owner accept + H1)

Deliberately not a step plan yet. Once accepted and H1 is measured, the rough
shape (each step gated per rule 4, with #548 Track B as prerequisite):

1. Personalization schema — `user_artist_tracks` atop #548's
   `artist_release_events`, anchored to catalog artist id.
2. Buckit → artist-candidate import path (snapshot, user-confirmed).
3. Per-user visibility query + personalized feed endpoint (DB-only read).
4. Multi-source upcoming ingestion (pending OQ2/OQ5 + H1).
5. Personalized almanac front (design gate with owner).

## Decisions log

| Date | Decision | Note |
|------|----------|------|
| 2026-07-08 | This is the personalization follow-on #548 reserved; a **new RFC**, not a rewrite of #548 (owner) | scope |
| 2026-07-08 | Personalized, user-selected tracked artists; Buckit = snapshot import source only, tracked list independent after import (owner) | scope |
| 2026-07-08 | Upcoming may draw from any API, not Spotify-only, under the spine-source consistency strategy (owner) — reconcile with #548's locked discovery at accept | design |
| 2026-07-08 | Market global; one event across markets; earliest-release-date is the canonical timeline (owner) | consistency |
| 2026-07-08 | Recently Released = rolling last 30 days; newly-tracked backfill uses the rolling window (owner) | scope |
| 2026-07-08 | Trust badges reduced to 3 (확정/예정/불확실); empty-Upcoming shown honestly, no fallback-to-recent; collab shows "추적: {artist}" (owner, rebuttal round) | UX |
| 2026-07-08 | "New since last visit" marker deferred (owner) | scope |
| 2026-07-08 | Naming: personal feed / watchlist, not "Calendar" (owner) | naming |
| 2026-07-14 | **H1 measured against live #548 poller data** (46 h): 3.1% watchlist coverage, iTunes +45% artists over MB-only, lead p50 31 d — **thin-but-usable, not first-class**; details inline at the H1 hypothesis. Re-measure ~07-27 (initial-inventory caveat). H2–H6 + owner accept still open — RFC stays draft | H1 |
| 2026-07-15 | **RFC accepted** (owner "시작하자") — H1 verdict (thin-but-usable, not first-class) recorded; **Step 1–3 착수**; **Step 4** (OQ2 per-source ToS + OQ5 #548 reconcile) and **Step 5** (owner design gate) deferred as separate gates under `accepted`. 2-phase execution: Step 1 schema → Steps 2∥3 parallel via codex worktrees; Claude authors the critical-path Step 1, codex owns the parallel Phase B legs | accept |
