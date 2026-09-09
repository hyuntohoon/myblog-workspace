# FEAT-lyrics-listening-experience: album translation coverage and immediate lyrics access

- **Status**: in-progress (Step 1)
- **Owner**: site owner
- **Created**: 2026-09-08
- **Plan row**: `docs/plan.md` → FEAT-lyrics-listening-experience
- **Design baseline**: approved by the owner on 2026-09-08; [preserved reference and implementation contract](../design/lyrics-listening-experience/README.md).
- **Execution state**: Step 1 is complete, including live-media confirmation on 2026-09-09. The owner requested documentation reconciliation and continuation on 2026-09-09. The owner approved the recommended OQ6 policy on 2026-09-09; Step 2 implementation is authorized and in progress. Steps 3–5 remain outside this session. This request does not settle the remaining policy questions or promote the RFC Status.

## Goal

Spotify-connected members can enter the site, see the song currently playing, and open its lyrics directly. Their saved library, recent listening and followed artists generate durable album-level translation demand, including existing library albums and artists' back catalogs. Missing source lyrics do not silently erase demand. The player fits the site's theme while preserving its existing controls, provider behavior and recovery flows. Claude remains the translation engine; album-level scheduling does not require album-level model calls.

## Non-goals

- Translating the entire catalog independently of member interest, adding product quotas, or changing the translation engine/subscription.
- Automatically following an artist on Spotify after listening, saving or rating. Reading Spotify follows does not authorize writing follows.
- Replacing the playback session, queue model, lyrics host, or provider adapter.
- Resuming the separately deferred `FEAT-member-own-listening-widgets` work or YouTube Milestone B.
- Implementing translation/synchronization policy or Steps 2–5 during Step 1.

## Confirmed requirements

| ID | Owner decision | Consequence |
|---|---|---|
| D1 | Members authenticated/connected to Spotify are the audience | Include members, not only the owner. Use each member's own connection. |
| D2 | Existing and newly saved library content both qualify; translation unit is the album | Backfill existing saved albums and expand newly discovered eligible albums into tracks. The liked-track extension is OQ1. |
| D3 | Recent listening qualifies and already has code | Extend that pipeline; do not invent a seven-day observation rule. |
| D4 | Followed artists qualify, including previous releases | Enumerate back catalogs for already-known artists as well as new artists; keep future release ingestion connected. |
| D5 | Do not consider limits as a product restriction | Do not add daily/member quotas or truncate eligible scope. Provider backoff and resumable worker execution remain operational necessities. |
| D6 | Site/home entry should discover ongoing playback and expose lyrics immediately | Do not require a dashboard visit or opening the queue first. |
| D7 | Preserve existing player functionality and use the latest full-feature design | Device choice, Spotify likes, transport, modes, seek, volume, queue and collapse remain accessible. Apply the preservation matrix below. |
| D8 | Fix the design, preserve it for implementation, record RFC/plan and merge | The approved `integrated` visual reference is versioned in this repository. The earlier reduced/More-based proposal is rejected. |

The owner requested recommendations for follow synchronization and missing-source handling. Those recommendations are specified below and identified as proposals in Open questions, rather than reported as existing or approved behavior.

## Current state

### Evidence boundary

Audit date: 2026-09-08. Workspace base: `9c9b2c7` (documentation PR #993). The initial code inspection used local front `a8d9eef`, backend `5675d00`, worker `766fd1f`, music `d0f8aee`, shared DB `abf8d57`. Later frontend compatibility inspection used the available `origin/main` object `9aea4d7`, including its YouTube changes. A subsequent service fetch was unavailable; these are inspected snapshots, not a claim that every deployed service was reverified. Re-read fresh main before implementation.

The live site's surrounding theme, member page and a lyrics view were inspected. No active global player was visible during that inspection, and no real device transfer was performed. The player reference combines the observed theme with the inspected component code. Its controls were tested as a local simulation, not as production Spotify commands.

### Translation and source retrieval

| Location | Observed behavior | Gap |
|---|---|---|
| Workspace `scripts/lyrics_translate_poller.py`, `SWEEP_SQL`, `_claude_translate_once` | Local Claude/Sonnet CLI, one full song per invocation. A run selects up to five songs sequentially, not five songs in one prompt. Sweep requires a research-linked album, usable source and no translation row. | Library, recent listening and follows are not independent translation producers. Increasing the run count is not model batching. |
| Backend `app/services/lyrics_service.py`, `request_translation` | Unknown catalog tracks cannot be requested; missing source is rejected. Explicit requests can replace existing translation state. Source fingerprints detect stale translations. | Automatic producers must not repeatedly invoke a manual overwrite path, lose unknown IDs, or mistake stale detection for automatic repair. |
| Shared DB `migrations/V35__track_lyrics_translations.sql` | Translation rows require a catalog track UUID and have `requested`, `done`, `failed` states. | Cannot directly represent pre-catalog or source-waiting demand. |
| Worker `lyrics_incremental_service.py` and handler `lyrics_incremental` | Global first-source retrieval; album sync and a 15-minute schedule can enqueue it. No album selector in the inspected job. | An eligible album needs targeted first-source retrieval. |
| Worker `lyrics_reassessment_service.py` and handler `lyrics_reassessment` | Album-specific reassessment already exists, but selects existing source rows. | Reassessment alone misses tracks with no source row. |
| Poller source/validation handling | Unavailable source becomes failed; source-ready sweep does not rediscover an existing failed row. Korean-dominant input avoids a model call but is marked failed. | Preserve demand separately; distinguish retryable absence, instrumental and translation-not-needed outcomes. |

Fingerprinting includes normalizer version and segment text, not timestamps. Existing translations are track-keyed, not a reusable cross-track cache. The local subscription guard serializes lyrics with other Claude consumers. Recorded wall time can include waiting for that guard; no measured token-savings claim supports changing invocation strategy yet.

### Members, library, recent listening and follows

| Location | Observed behavior | Required extension |
|---|---|---|
| Front `components/member/integrations.api.ts`; backend `integration_service.connect_spotify` | Scopes include library and recent/playback reads; `user-follow-read` is absent. Connect stores encrypted refresh credentials and scopes, commits and returns, without bootstrap jobs. | Add consent for follow reads and durable asynchronous bootstrap after connection persistence. Existing grants may require reconsent. |
| Worker `spotify_member_sync_service.py`; workspace `infra/eventbridge.tf` | Existing member sync reads the latest 50 recent tracks every 15 minutes. Stored recent metadata lacks the album-ingestion path. | Resolve album identity and emit durable demand asynchronously. Preserve observations before they leave the recent window. |
| Worker `listening_sync_service.py` | Owner recent-listening flow already handles unknown album ingestion; its recent cache is pruned. | Reuse its ingestion pattern without treating owner storage or credentials as member storage. |
| Existing Spotify library storage | Owner-global rather than a complete member-scoped saved-library model. | Member-scoped reconciliation and complete pagination for old/new saved albums. |
| Shared DB `UserArtistTrack`; backend `tracked_artist_service.py`; front `ReleaseRadar.tsx` | Site tracking is explicit or a selected snapshot imported from Buckit. Edges have no origin/exclusion metadata. | Do not describe this as continuous automatic following. Preserve provenance if automatic sync is added. |
| Backend `tracked_artists.py`; worker `follow_import_service.py` | Spotify import is manual and owner-only. Unknown artists trigger limited recent album/single enumeration and one delayed retry. | Generalize to connected members and full pagination, including already-cataloged artists. |
| Worker `album_ingest_service.py` | The union of tracked artists already feeds release ingestion. | Connect resulting albums to translation demand and audit any catalog filters that would silently defeat full requested scope. |

The player's heart writes Spotify saved **tracks**, not saved albums or site ratings. Existing Buckit artist expansion is also distinct from inserting a site tracking edge. These distinctions matter for eligibility and must not be flattened into one generic library/follow event.

### Playback and theme

- Front `GlobalPlaybackBar.tsx` provides identity/like, transport, shuffle, repeat, seek, queue, device picker, volume and collapse. `PlaybackControls.tsx` provides device refresh/transfer, browser fallback, library permission recovery and error messages.
- `PlaybackPanel.tsx` provides queue play/reorder/remove, album/lyrics entries and desktop dock/float behavior. `playbackEntryActions.ts` already opens the common live-lyrics host.
- `usePlaybackViewModel` calls `playbackSession.syncFromLive()` on mount. Site re-entry/navigation behavior must be checked against the persisted island and session lifecycle; a mount read alone does not prove all entry paths refresh.
- `pocket.css` forces a separate blue-black player palette. The observed site uses warm dark surfaces, off-white text, red accents and thin rules.
- Front `9aea4d7` also provides a **YouTube video selection** entry and provider-aware gates: Spotify likes/device controls are not applicable to YouTube. The saved mock predates that entry. Preserve it during implementation; do not copy the prototype as a complete current-main control inventory.

## Target state

### 1. Approved player contract

The [design record](../design/lyrics-listening-experience/README.md) owns the frozen reference, colors, responsive intent and prototype limitations. Use the integrated/page-colored treatment; the raised treatment remains a comparison only.

| Capability | Required behavior after redesign |
|---|---|
| Track identity and Spotify heart | Visible in expanded desktop/mobile Spotify mode. Load actual saved state; preserve permission reconsent, unavailable state and failed-write rollback. |
| Device choice | Direct entry, current output name, fresh list on open, active selection, transfer-in-progress/error/no-device feedback and existing browser fallback. Do not transfer playback merely on site entry. |
| Transport | Preserve session/ownership/provider routing, pending-command behavior and no-device recovery. |
| Shuffle and repeat | Direct controls when supported; repeat remains off/context/track. |
| Seek and time | Preserve pointer and keyboard seeking and correct elapsed/duration. A single accessible rail may replace duplicate visual rails without losing their function. |
| Volume | Preserve wide-screen inline slider and narrow-screen dedicated popover, provider/device capability checks and feedback. The 1024px mock shows the compact form. |
| Queue | Direct entry into the existing full panel: play, reorder, remove, album entry, dock/float and mobile presentation. |
| Collapse | Preserve voluntary collapse/expand and uninterrupted playback. The prototype's compact row is a visual example, not permission to lose existing collapsed-state behavior. |
| Lyrics | New visible button opens the existing current-track lyrics host in one action; available source can be read while translation is pending. |
| YouTube and later current-main controls | Preserve the shipped mapping entry and provider gates. Unsupported Spotify controls do not become active solely because the mock draws them. |
| All surfaces | Coordinate player, device portal, volume popover, queue and collapsed styling; maintain focus, Escape/dismissal, safe-area and content-inset behavior. |

Desktop retains identity / transport / tools. Mobile reflows into three groups with direct actions; the approved mock is taller than the existing 112px bar. Measure actual content height and safe-area offsets instead of retaining a hard-coded 112px inset. Do not recover height by hiding the heart, modes, queue or device entry behind More. Keep the surrounding site navigation/content unchanged; the mock's home content is contextual scenery.

### 2. Site-entry playback and lyrics

Use the existing playback session and provider adapter for initial site load, return to home through client navigation, and foreground/pageshow recovery. Coalesce overlapping reads, respect the owning tab and ignore stale responses. Reuse existing lifecycle hooks where they already cover the requirement.

Display current playing and paused states truthfully. A recent-history item is not proof of active playback. No active playback must not fabricate a current song; temporary read failures must not become a permanent idle state. Do not hijack an active YouTube session to Spotify or transfer audio into the browser merely to discover a song. Keep the existing authority model. New backend endpoints must not synchronously call Spotify.

Resolve current-track identity through the existing lyrics entry. A source-waiting or translation-pending song still has an honest destination/status. Do not delay opening available original lyrics until a Korean translation exists. Site entry is a playback-read trigger; it does not itself authorize catalog-wide translation.

### 3. Durable album demand — proposed mechanism

Separate member discovery provenance from globally reusable translation work:

1. Persist `(member, origin, provider album identity)` when an eligible album is discovered. Accept a Spotify identity before a catalog UUID exists. Repeated events must converge without duplicating work.
2. Resolve/upsert catalog identity asynchronously, then enumerate the album's tracks.
3. If a source row is absent, run targeted first fetch. If present but unresolved, reuse targeted reassessment.
4. Keep unresolved work as source-waiting demand with last-attempt/reason/next-attempt metadata. A durable due-work query can enqueue attempts; do not keep a single SQS message waiting indefinitely.
5. Only usable source enters the existing per-track translation path. Share completed work across members/triggers for the same catalog track, source fingerprint, target language and translation/prompt version.
6. Derive album progress from track states. Instrumental/already-target-language outcomes are explicit not-required states; missing source remains pending, not successful coverage. Failed attempts remain distinguishable from waiting.

Logical names such as `catalog_pending`, `source_pending`, `translation_ready`, `done`, `not_required` and `retryable_error` describe the state machine, not a migration approved in this PR. Define concrete tables/keys and transitions during the schema step. Preserve manual translations; repeated automatic discovery must not reset completed/manual work. A source change can create stale-version work without silently overwriting an editorial correction.

Demand survives recent-window pruning and retry/restart. Disconnect/unfollow stops future discovery from the removed origin; retention of member provenance and unstarted work is OQ6. Completed reusable catalog translations must not be deleted as a side effect of one member disconnecting.

### 4. Bootstrap and synchronization — proposed defaults

- After connection credentials commit, durably schedule bootstrap; a broker failure must be recoverable by reconciliation, not silently lose initial sync. Also backfill already-connected members. Never run full library/discography loops inside the connect request.
- Enumerate saved albums with complete pagination. Reconcile additions/removals per member; existing and newly saved albums use the same eligibility path.
- Reuse the existing recent-listening sync (50 observations per provider read, existing 15-minute cadence). Resolve each observed track's album asynchronously; do not impose a new seven-day cutoff. The provider observation window is not a translation quota.
- Recommend site manual follows **union** Spotify follows, stored with separate origins. Reconcile Spotify follows at bootstrap and on the existing 15-minute schedule; missing follow scope requests reconsent without breaking playback/recent reads.
- Recommend that Spotify unfollow removes only the Spotify origin. A retained manual origin continues site tracking. An explicit site exclusion should prevent automatic re-import resurrection until cleared. Never write follows back to Spotify.
- Enumerate eligible releases across every page for both newly encountered and existing artists; retain cursors/checkpoints across bounded worker invocations. Do not mistake latest album+single or a first page for the complete catalog. Release-type boundaries are OQ4.

### 5. Claude efficiency

Keep one song per invocation initially. Album membership controls discovery/progress; per-track work controls validation/retries. Avoid duplicate model calls across albums, members, retries and unchanged versions before changing prompts or concurrency.

Capture queue age, subscription-guard wait, model runtime, outcome and available usage separately. Do not promise token or time savings from the existing wall-time logs. Longer albums must not lose tracks when a worker run ends; resume work rather than cap coverage.

Multi-song requests are a later measured option: explicit track identifiers, per-track output validation, partial success persistence, isolated retry and preservation of manual work are mandatory. Compare against per-song calls on the same corpus before adopting. No batch size, cost reduction or parallel Claude execution is approved here; the shared subscription guard remains respected.

## Steps

Step 1 was authorized and deployed on 2026-09-08 and its live-media confirmation closed on 2026-09-09. Step 2 preparation was requested on 2026-09-09; the owner then approved OQ6 and Step 2 implementation is in progress. Steps 3–5 have not started. Each numbered step is one session boundary under workspace policy; where multiple repositories are named, carry the migration/consumer sequence through the step's separate PRs and verification gates. Recheck fresh service main and related RFCs before starting.

### Step 1 — Preserve player functionality and add immediate lyrics access

**Current state:** complete in frontend PR #445; local/full-suite, automated production smoke and live-media verification all passed. Live-media confirmation closed on 2026-09-09. The delivery record retains the browser-cache and unverified browser-fallback observations; neither reopens Step 1.

**Scope/order:** frontend only, independent of Steps 2–5. Re-audit current-main controls including YouTube; apply the approved styling and direct lyrics entry; extend the existing session lifecycle for entry/return discovery. Update layout offsets to measured responsive height. Do not resume the deferred member widget initiative.

**Verification:** `pnpm lint`, `pnpm exec astro check`, `pnpm test`; targeted interaction coverage for direct lyrics, lifecycle read deduplication and stale responses. Real-browser clickthrough at 320/360, 736, 1024 and wide desktop in light/dark: all applicable controls, device selection, saved-state change/recovery, seek, volume, queue edit/dock, collapse, navigation/foreground return, paused/missing-source states and Spotify/YouTube transitions. Verify member identity remains self-scoped. Post-deploy production smoke and record the actual result in the PR.

**Rollback:** revert the frontend change; no data rollback.

### Step 2 — Add durable album eligibility and version-safe track work

**Current state:** translation rows require catalog UUIDs; durable pre-catalog/source-waiting album demand and member-origin provenance are absent. **Dependencies:** OQ6 resolved by the owner on 2026-09-09 (policy below).

**Scope/order:** shared DB additive schema → consuming backend/worker dependency pins and dormant service support. Automatic producers remain disabled. Specify member-origin identity, catalog resolution, unique work keys, source/version states and album accounting before writing migrations. Respect member row scoping.

**Verification:** shared DB migration/model checks and affected Python suites; repeated event, two members/one album, missing catalog/source, mixed album states, manual translation, changed fingerprint and process restart cases. Export any changed service OpenAPI, merge workspace contracts, regenerate frontend types in the dependent PR sequence. Exercise additive migration on a non-production database, then follow the repository's forward migration and post-deploy verification process.

**Rollback:** disable new consumers/writers; retain additive schema and demand records. Never run a production rollback migration without owner approval.

#### Step 2 storage contract — V57 (implementation, not yet shipped)

| Store | Responsibility |
|---|---|
| `lyrics_discovery_scopes` | Member/origin-kind fence, active flag and generation. Removing a scope's album/artist provenance retains only this minimal fence; account deletion cascades it. |
| `lyrics_album_jobs` | Global Spotify album identity before catalog ingestion, catalog resolution/retry metadata, explicit enumeration completion and expected track count. |
| `lyrics_album_demands` | Scope + job + origin entity key. Two followed artists can independently justify one album; removal deletes only the matching origin. |
| `lyrics_album_tracks` | Enumeration snapshot, source waiting/not-required reason, current work pointer and UUID observation revision. Source absence never requires a nullable version-work key. |
| `lyrics_translation_work` | Unique track + fingerprint + language + translator version, durable claim/lease token, attempts, retry metadata and immutable completed result. No legacy translation writer. |

The shared package's `LyricsDemandStore` accepts a caller-owned SQLAlchemy connection and performs
only short DB transitions. Backend/worker gain the dormant repository through compatible package
pins; no redundant service wrapper or automatic invocation is required. Provider collection,
normalization, retry intervals and legacy-result publication remain Steps 3–5. In particular,
publication must compare the claimed version and any intervening manual edit; Step 2 cannot activate
the old poller's track-only writeback safely.

Lock ordering is scope → album jobs in UUID order → work in UUID order. A public mutation is one
transaction; `revoke_scopes` prelocks the full union for multi-origin disconnect. Claim/completion
lock only work and never later acquire jobs. Claim rechecks live demand, including after account
FK cascades. Only never-started orphan work is cancelled; new demand can revive it. Completed work
is never reset, and legacy manual translations are neither queued nor overwritten.

Source observations carry the snapshot's UUID revision and previous work pointer, so source waiting,
not-required transitions and deletion/recreation cannot admit an old observation. Album completion
uses a single SQL snapshot and requires explicit full enumeration, unchanged membership/count and
only done/not-required tracks. Partial/empty enumeration and pending/error tracks cannot count as
complete. Removing one entity rotates the entire origin-kind fence: Steps 4/5 must restart or
reconcile rejected in-flight discoveries from that scope instead of treating rejection as success.

#### Step 2 preparation findings — 2026-09-09

Read-only inspection of the available service `origin/main` snapshots found no existing durable
album-demand store. V56 is the latest shared migration in those snapshots. Reconfirm remote main
and migration numbering before implementation.

- Existing manual `LyricsService.request_translation()` requires a catalog track and usable source;
  it can reset an existing result. Automatic discovery must not call it to represent waiting demand.
- The workspace poller claims legacy `requested` rows and its completion writes by `track_id` alone,
  setting `origin=poller`. New dormant work must stay outside that claim path. Step 3 must guard
  completion by the claimed work/source version and preserve manual changes made during a model call.
- Schema rollout starts with the workspace canonical DDL PR, then the shared-db mirror, models,
  migration and tests, then compatible consumer pins. This is the order in
  `docs/contracts/README.md`; the high-level scope/order above does not override it.
- Worker runtime requirements and its CI canonical-schema checkout currently pin different shared-db
  commits. Check `requirements.txt`, the deployed `requirements.lock`, and the workflow schema pin
  together when adding model imports. No producer, route, schema or runtime pin changed during this
  preparation. The owner subsequently approved OQ6 below; these preparation constraints still apply.

### Step 3 — Connect targeted sources to the Claude pipeline

**Current state:** first-source retrieval is global, album reassessment excludes missing rows, and automatic Claude selection is research-linked and source-ready.

**Dependencies:** Step 2 and OQ5/6. **Scope/order:** worker targeted initial fetch/reassessment → workspace poller ready-work consumption. Validate source-ready versions and preserve the existing manual path.

**Verification:** worker suite, poller-specific regression checks; albums with absent rows, unresolved rows, instrumental/target-language tracks, partial translations, duplicate delivery, transient provider/CLI errors and changed source. Confirm waiting demand later progresses without a second manual request and no DB transaction spans an external-API loop. Post-merge source-to-translation smoke with recorded album/track outcomes.

**Rollback:** stop new dispatch/selection and restore the prior poller selection. Retain waiting demand and completed translations for resumption.

### Step 4 — Bootstrap member saved-library and recent-listening demand

**Current state:** connection persists credentials without bootstrap; member recent polling exists, while saved-library storage remains owner-global.

**Dependencies:** Steps 2–3; OQ1 for liked-track inclusion and OQ6 for removal behavior. **Scope/order:** worker member-scoped sync consumers → durable connect/bootstrap producers and existing-member backfill → any required frontend connection recovery/status. Reuse existing recent observations, not owner-only library endpoints.

**Verification:** affected suites; newly connected, already connected, reconnect, disconnected, multi-page library, duplicate recent event and unknown catalog cases. Prove two members cannot read/use one another's credentials or library. Simulate enqueue failure after credential commit and prove reconciliation recovers. Complete route/contract/infra checks for any actual changes, then production smoke with a connected member.

**Rollback:** disable new producers; preserve connection/playback behavior and durable work. Retain schema.

### Step 5 — Reconcile follows and translate complete eligible discographies

**Current state:** Spotify follow import is owner-only/manual; member origin/exclusion reconciliation and complete back-catalog enumeration are absent.

**Dependencies:** Steps 2–4 and OQ2–4/6. **Scope/order:** origin/exclusion support → member worker reconciliation and paginated discography ingestion → follow-read consent/reconsent → backfill and ongoing release linkage. Reuse existing artist ingestion boundaries.

**Verification:** multi-page follows/discography, already-known artists, joint manual/Spotify origins, unfollow, exclusion/re-import, missing scope, partial enumeration retry and new release arrival. Prove complete eligible coverage instead of latest-release-only behavior. Affected suites, contract/API Gateway alignment and full Terraform plan if infra changes; post-deploy member/follow/back-catalog smoke.

**Rollback:** disable automatic follow producers; retain manual tracking and completed catalog/translation work.

### Later optimization gate — multi-song Claude experiment

Not a prerequisite of Steps 1–5. Define a separate bounded comparison after reliable per-track work/metrics exist. Adoption requires preserved segment attribution/coverage, isolated retry and a measured operational improvement. Otherwise retain per-song invocation. No experiment has been run by this RFC PR.

## Open questions

These do not block preserving/merging the approved design. They gate the indicated implementation scope; do not silently convert recommendations into owner decisions.

| ID | Decision to settle | Recommended starting point | Blocks |
|---|---|---|---|
| OQ1 | Does saved-library demand also include liked tracks expanded to their albums? | Saved albums are confirmed. Treat the player's saved-track action as a separate explicit extension. | Step 4 liked-track extension; saved-album/recent work can be specified independently. |
| OQ2 | Which follow origins survive unfollow and site exclusion? | Manual ∪ Spotify; remove only the relevant origin; keep explicit exclusions against resurrection. | Step 5 reconciliation. |
| OQ3 | Automatic Spotify follow reconciliation cadence | Bootstrap plus existing 15-minute cycle, with resumable pagination and provider backoff. | Step 5 scheduler behavior. |
| OQ4 | What releases count as an artist's complete back catalog? | All artist albums/singles/EPs; explicitly decide artist compilations and `appears_on` rather than importing every credited compilation accidentally. | Step 5 enumeration. |
| OQ5 | Missing-source retry/terminal classification | Durable waiting and due-work retries; separate not-found/transient/error from confirmed instrumental or translation-not-needed. Define retry intervals from existing reassessment behavior. | Step 3 activation. |
| OQ6 — resolved 2026-09-09 | Unsave/unfollow/disconnect effects on unstarted demand and member provenance | Owner approved the recommended removal policy below. | No remaining decision gate; implement in Step 2 and wire producers in Steps 4/5. |
| OQ7 | Whether to batch Claude songs | Keep per-song calls until a version-safe measured experiment supports a change. | Optional optimization only. |

### OQ6 — owner-approved removal policy (2026-09-09)

- Unsave, unfollow or disconnect removes the affected origin's album demand and its detailed
  member/album provenance. Other members, other origins and explicit manual requests remain valid.
- Cancel only work that has never started and has no remaining demand/manual request. A claim that
  already started may finish; completed global translations are retained.
- Missing source and a recent observation aging out of Spotify's window do not remove demand.
- Retain only a member/origin generation fence after removal so delayed observations cannot recreate
  removed demand. It contains no album/artist history and cascades on account deletion. Disconnect
  disables that origin until explicitly re-enabled; reconnect issues a fresh generation.
- The source integration/reconciliation producers remain disabled in Step 2. Steps 4/5 must rotate or
  disable the fence in the same transaction as origin removal and carry its generation on delayed work.
  This decision does not settle OQ2 follow-union rules or OQ5 retry intervals/classification.

## Delivery and implementation record

The approved RFC/design baseline is workspace [PR #994](https://github.com/hyuntohoon/myblog-workspace/pull/994), commit `b8ac88d`. Step 1 started from that workspace main and frontend `9aea4d7` ([PR #444](https://github.com/hyuntohoon/myblog_front/pull/444)), including its YouTube provider behavior. A busy shared checkout required isolated workspace/frontend worktrees. The prior planning task was idle; no other active task owned Step 1.

### Step 1 compatibility and implementation

| Requirement | Existing seam retained and result |
|---|---|
| Styling and responsive clearance | `GlobalPlaybackBar` / `pocket.css` use the site's warm light/dark surface, red accent and fine rules. One seek rail; actual border-box height drives `--global-player-h`, including reflow and Astro root swaps. |
| Entry, home and foreground discovery | Shared lifecycle listeners call `playbackSession.syncFromLive`; overlapping reads share work. Mirror tabs request a fresh owner snapshot without taking ownership. Reads do not call play, transfer, pause or load the Spotify SDK. |
| Likes, device, transport and modes | Existing session/provider commands remain. Live device metadata is adopted; cached like identity resets across YouTube so returning to the same Spotify track restores the heart. Errors retain recovery and optimistic-save rollback. |
| Queue, docking and collapse | Existing queue rows, editing, docking and collapse remain; controls are directly reachable. Collapsed clearance is zero and expansion/navigation remeasure it. |
| Current-song lyrics | The bar calls existing `openPlaybackLyrics` and lyrics host. YouTube catalog identity resolves through the URI seam; viewer refresh reads the active provider. Stale provider/track responses cannot open the wrong track. Original text remains readable while translation is requested. |
| Account isolation and stalled requests | Existing `AuthEpoch` scopes token cache, token mint and shared playback reads. Identity/ownership changes invalidate adoption. Token mint is bounded at 8s, playback read at 10s; stale responses cannot populate cache or publish another account's state. No server authorization, route or contract changed. |

### Step 1 local/browser verification

Real browser clickthrough used the actual player/session/provider/lyrics components with deterministic local service responses and a local IFrame SDK fixture. The temporary fixture was removed before final checks and is not shipped. This verifies UI and provider routing, not live YouTube media availability.

- Spotify layouts at 320, 360, 736, 1024 and 1440 CSS pixels in both themes: no controls outside the viewport; measured expanded heights 210, 210, 170, 125 and 106px respectively in the tested no-error state. Resize, collapse and Astro root-attribute reset restore the actual inset.
- Heart success and failed-save rollback; shuffle; repeat off/context/track/off; play/pause; previous/next; keyboard seek and volume; device transfer, failed list read and recovery; mobile queue reorder/removal and desktop float/dock; collapse/expand.
- A paused external track change is discovered on home/return with zero playback writes. Transient read failure retains the previous song, and the next return adopts the new song after recovery.
- Direct lyrics opens the current song with original lines while translation remains requested. Missing source displays the existing empty state. YouTube direct lyrics, refresh, pause/seek and video selection remain provider-aware; return to Spotify restores the heart. The existing minimum YouTube viewport (480px wide / 410px tall), hidden-tab and navigation stop behavior remain unchanged.
- Independent reviewer found no further functional issue after recovery fixes. Primary separately resolved the account-boundary finding by inspecting every cache reuse, mint retry, cache write and read publication against `AuthEpoch`; regression tests cover old/new accounts and stalled-operation retry.

Final local checks: `pnpm lint` passed; `pnpm exec astro check` reported 363 files, 0 errors, 0 warnings (2 existing hints); `pnpm test --maxWorkers=2 --no-file-parallelism` passed 109 files / 1,218 tests. Workspace invariant suite passed 23 tests and plan/RFC/OpenAPI validation passed. Frontend [PR #445](https://github.com/hyuntohoon/myblog_front/pull/445) contains the implementation. PR #445 squash-merged as `f0d9adf4f1c69e2ac7d1e7fb8b52ddab9d99c612`. [Deployment run 34170635240](https://github.com/hyuntohoon/myblog_front/actions/runs/34170635240) passed its full check, build, upload, CloudFront invalidation and post-deploy health smoke. The authenticated production suite reported **PASSED: 30, FAILED: 0, elapsed: 6.2s** after deployment.

Production asset verification passed against the fresh HTML's `PocketBuckit.CZRRJIwQ.js` and `PocketBuckit.78l9l3iJ.css`: direct-lyrics, measured resize/navigation inset and new control style markers are present. The existing browser tab initially kept older HTML (`PocketBuckit.B7psq29B.js`); opening the deployment-qualified URL loaded the new components. A plain reload alone had retained the old document in that tab.

**Live-media confirmation — CLOSED 2026-09-09.** Verified on production against the deployed `PocketBuckit.CZRRJIwQ.js` / `PocketBuckit.78l9l3iJ.css` bundle, in a clean browser profile with a real owner Cognito login (the `id_token` `sub` matched `OWNER_SUB`), driven over CDP with trusted input events. Every playback claim below was checked against an **independent observer** — a separate Spotify Web API session minted from SSM `/myblog/spotify`, not the page's own state — because a player reporting its own success proves nothing.

- **Why the earlier attempt failed, and it was not a defect.** `GET /v1/me/player` answered **204**: nothing was playing and **no device was active**, which is also exactly why the live read yielded no track. With no active device the ladder's rung 1 `PUT /v1/me/player/play` correctly returns **404**, the fallback loads the Web Playback SDK, and the recoverable `재생 토큰을 가져오지 못했어요` notice is what the user then sees. The owner streaming credential itself is healthy: exchanging `streaming_refresh_token` returns **HTTP 200**, `expires_in` 3600, with scope `streaming user-modify-playback-state user-library-read user-follow-read user-library-modify user-read-playback-state user-read-currently-playing user-read-recently-played`. The deployed page minted successfully on its own too — it issued `GET api.spotify.com/v1/me/player` and got the same 204. Note that scope list is the **owner's** credential; the member connect list (`integrations.api.ts` `SPOTIFY_SCOPES`) still lacks `user-follow-read`, so the Current state row above stands — but Step 5's owner-side follow read needs no reconsent.
- **Real Spotify audio and remote-device roundtrip.** After a device was made active, pressing the queue row sent `PUT /v1/me/player/play` → 204 and the independent read reported `playing=true, device=home의 MacBook Air, track=Nikes`, position advancing 1140 → 17520 ms in real time. Pause froze the position at 41076 ms across a 2.5 s window — not merely a flag flip — resume resumed, and a click at 75 % of the rail sent `seek?position_ms=236324` with the independent read at 238667 ms; the bar's own rail read `3:58 / 5:14`.
- **Direct lyrics, on both providers.** One press of the bar's 가사 control fetched `/api/lyrics/19YKaevk2bce4odJkP5L22` → 200 and opened the viewer **SYNCED** on the actually-playing track, original lines plus Korean translation. It behaves identically while YouTube is the active provider, resolving through the URI seam to the same lyrics id.
- **Real YouTube media.** A mapping was confirmed through the product's own picker (`PUT …/youtube-mapping` → 200; `resolve?provider=youtube` → `youtube:video:diIFhc_Kzng`). The explicit catalog-track press then paused Spotify (`PUT /v1/me/player/pause` → 200, independently confirmed `playing=false` frozen at 121760 ms — the two providers are mutually exclusive in fact, not only in code), loaded the IFrame API, and played `youtube.com/embed/diIFhc_Kzng?autoplay=1` at 640×360. The bar showed **5:15** where Spotify reports 5:14, so it is reading the real video's metadata rather than the catalog's. YouTube pause froze the position at 90803 ms across 3 s, resume resumed, and a seek to 70 % jumped 129067 ms to `3:42 / 5:15`. **The test mapping was then deleted through the product's own 이 영상 아님 action** (`DELETE …/youtube-mapping` → 204, `resolve?provider=youtube` back to 404) and the next press correctly fell back to Spotify — production carries no residue.
- **Preserved controls, live.** The bar carried 좋아요, 셔플, 이전/재생·일시정지/다음, 반복, the seek rail (`aria-valuenow` 84614 of `aria-valuemax` 314000), 가사, 재생 대기열, 재생 기기, YouTube 영상 고르기 and 접기. Opening the device picker issued a fresh `GET /v1/me/player/devices` → 200 and listed 이 브라우저 (음질 제한) / Buckit / ● home의 MacBook Air with the active one marked, and the bar's device control adopted the live name. `--global-player-h` measured **106 px** at 1440 CSS px, matching the height recorded from the local pass.
- **A methodology trap worth keeping.** A first YouTube pause/seek attempt read as broken — the toggle never flipped and the position kept advancing. It was the harness: the album overlay and then the lyrics viewer were covering the click point. `document.elementFromPoint` at the button's centre returned `BUTTON.lyv-line`, not the toggle. Re-run with the overlays closed, every control passed. **Hit-test the point before reporting a dead control.**
- **Not verified, and deliberately left open.** The in-page browser rung (`이 브라우저 (음질 제한)`) was never exercised end to end, so what the SDK fallback does after a cold-start 404 is *explained* above but not *proven*. That path predates this step — #445 did not change the ladder — so it is recorded as an observation, not adopted as Step 1 work.

Step 1 is complete. **Status stays `in-progress`.** The owner subsequently requested continuation on 2026-09-09; Step 2 preparation proceeds in the current session, with the owner-approved OQ6 policy below. The other open questions apply only to the scopes listed in the table. The plan row remains until the entire RFC is complete.

## Decisions log

| Date | Decision | Step |
|---|---|---|
| 2026-09-08 | Owner confirmed Spotify-connected audience; old/new library, recent listening, followed artists and prior releases; album unit; no added product limits. | Requirements |
| 2026-09-08 | Owner rejected the reduced player: device choice, likes and other existing functions must retain their roles. | Design |
| 2026-09-08 | Owner fixed the revised full-feature design and requested persistent design/RFC/plan plus push and merge. Source hash and standalone previews are in the design record. | Documentation |
| 2026-09-08 | Preserve the newer YouTube entry/provider gates found in the available main snapshot; the older visual mock is not authority to remove them. | Compatibility |
| 2026-09-08 | Follow/removal/source-waiting/batching details remain identified proposals. No implementation step or production deployment is claimed by this PR. | Planning |
| 2026-09-08 | Owner accepted the RFC and authorized Step 1 implementation, verification and delivery only. Status advanced through accepted to in-progress (Step 1); unresolved policies remain open. Report here after Step 1; no automatic Step 2 or new task. | Step 1 authorization |
| 2026-09-09 | Live-media confirmation closed against the deployed bundle with a real owner session and an independent Spotify Web API observer: real Spotify play/pause/seek on a remote device, real YouTube media, direct lyrics on both providers. Test mapping created and deleted through the product's own actions; no production residue. Status deliberately NOT promoted. | Step 1 |
| 2026-09-09 | Owner requested documentation reconciliation and continuation after the progress review. Reconcile Step 1 completion throughout the RFC/index and move the plan pointer to Active. Prepare Step 2; OQ6 remains an explicit decision gate, and Steps 3–5 are not authorized by this session's scope. No Status promotion. | Step 2 preparation |
| 2026-09-09 | Owner approved the recommended OQ6 option: remove affected origin demand, cancel only unstarted orphan work, preserve manual/other-origin demand and completed translations. Source waiting and recent-window expiry retain demand. Step 2 implementation proceeds; no later step or Status promotion is implied. | OQ6, Step 2 |
