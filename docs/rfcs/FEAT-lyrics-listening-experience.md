# FEAT-lyrics-listening-experience: album translation coverage and immediate lyrics access

- **Status**: draft
- **Owner**: site owner
- **Created**: 2026-09-08
- **Plan row**: `docs/plan.md` → FEAT-lyrics-listening-experience
- **Design baseline**: approved by the owner on 2026-09-08; [preserved reference and implementation contract](../design/lyrics-listening-experience/README.md).
- **Execution state**: documentation and design preservation only; no implementation step has started. Design approval does not settle the open product policies in §Open questions or promote this RFC to `in-progress`.

## Goal

Spotify-connected members can enter the site, see the song currently playing, and open its lyrics directly. Their saved library, recent listening and followed artists generate durable album-level translation demand, including existing library albums and artists' back catalogs. Missing source lyrics do not silently erase demand. The player fits the site's theme while preserving its existing controls, provider behavior and recovery flows. Claude remains the translation engine; album-level scheduling does not require album-level model calls.

## Non-goals

- Translating the entire catalog independently of member interest, adding product quotas, or changing the translation engine/subscription.
- Automatically following an artist on Spotify after listening, saving or rating. Reading Spotify follows does not authorize writing follows.
- Replacing the playback session, queue model, lyrics host, or provider adapter.
- Resuming the separately deferred `FEAT-member-own-listening-widgets` work or YouTube Milestone B.
- Deploying application changes as part of this RFC/documentation PR.

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

No implementation step is completed by this documentation merge. Each numbered step is one session boundary under workspace policy; where multiple repositories are named, carry the migration/consumer sequence through the step's separate PRs and verification gates. Recheck fresh service main and related RFCs before starting.

### Step 1 — Preserve player functionality and add immediate lyrics access

**Current state:** the existing controls and mount-time live synchronization are present, while player styling overrides the site palette. Recheck current-main lifecycle coverage and YouTube controls before editing.

**Scope/order:** frontend only, independent of Steps 2–5. Re-audit current-main controls including YouTube; apply the approved styling and direct lyrics entry; extend the existing session lifecycle for entry/return discovery. Update layout offsets to measured responsive height. Do not resume the deferred member widget initiative.

**Verification:** `pnpm lint`, `pnpm exec astro check`, `pnpm test`; targeted interaction coverage for direct lyrics, lifecycle read deduplication and stale responses. Real-browser clickthrough at 320/360, 736, 1024 and wide desktop in light/dark: all applicable controls, device selection, saved-state change/recovery, seek, volume, queue edit/dock, collapse, navigation/foreground return, paused/missing-source states and Spotify/YouTube transitions. Verify member identity remains self-scoped. Post-deploy production smoke and record the actual result in the PR.

**Rollback:** revert the frontend change; no data rollback.

### Step 2 — Add durable album eligibility and version-safe track work

**Current state:** translation rows require catalog UUIDs; durable pre-catalog/source-waiting album demand and member-origin provenance are absent. **Dependencies:** OQ6 for removal/retention schema behavior.

**Scope/order:** shared DB additive schema → consuming backend/worker dependency pins and dormant service support. Automatic producers remain disabled. Specify member-origin identity, catalog resolution, unique work keys, source/version states and album accounting before writing migrations. Respect member row scoping.

**Verification:** shared DB migration/model checks and affected Python suites; repeated event, two members/one album, missing catalog/source, mixed album states, manual translation, changed fingerprint and process restart cases. Export any changed service OpenAPI, merge workspace contracts, regenerate frontend types in the dependent PR sequence. Exercise additive migration on a non-production database, then follow the repository's forward migration and post-deploy verification process.

**Rollback:** disable new consumers/writers; retain additive schema and demand records. Never run a production rollback migration without owner approval.

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
| OQ6 | Unsave/unfollow/disconnect effects on unstarted demand and member provenance | Stop future discovery from that origin; preserve reusable translations; settle member-provenance retention and orphan-work cancellation explicitly. Preserve demand while a source is pending and a recent observation ages out. | Steps 2–5 removal/retention rules. |
| OQ7 | Whether to batch Claude songs | Keep per-song calls until a version-safe measured experiment supports a change. | Optional optimization only. |

## Delivery and implementation handoff

- This PR stores the RFC, plan/index pointers, exact approved fragment and standalone dark/light previews. It changes no service, route, migration, infrastructure or runtime setting.
- Run the workspace's existing invariant suite and plan/contract checker, validate saved preview JavaScript and local links, and open the exported previews in a real browser. Wait for actual PR CI before merging.
- A docs-only merge has no application deployment to verify. Record that fact rather than inventing a production smoke result. The plan row remains because all implementation steps are outstanding; drop it only when the feature's final production verification is complete.
- Next implementation entry: Step 1, after RFC acceptance under workspace policy and a fresh-main compatibility inventory. Read the design README and preservation matrix first. Do not start a new implementation task automatically merely because this planning PR merged.

## Decisions log

| Date | Decision | Step |
|---|---|---|
| 2026-09-08 | Owner confirmed Spotify-connected audience; old/new library, recent listening, followed artists and prior releases; album unit; no added product limits. | Requirements |
| 2026-09-08 | Owner rejected the reduced player: device choice, likes and other existing functions must retain their roles. | Design |
| 2026-09-08 | Owner fixed the revised full-feature design and requested persistent design/RFC/plan plus push and merge. Source hash and standalone previews are in the design record. | Documentation |
| 2026-09-08 | Preserve the newer YouTube entry/provider gates found in the available main snapshot; the older visual mock is not authority to remove them. | Compatibility |
| 2026-09-08 | Follow/removal/source-waiting/batching details remain identified proposals. No implementation step or production deployment is claimed by this PR. | Planning |
