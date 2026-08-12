# Plan

Active workspace tracker for cross-repo work. Each row carries `Scope / Order (if multi-repo) / Verification (local + prod smoke) / Rollback / Status`; RFC-backed entries collapse to a one-line pointer at `docs/rfcs/<id>-<slug>.md`. When a row finishes, drop it — `git log` and `docs/archive/done/YYYY-MM.md` are authoritative for history.

---

## Active

> 2026-08-10 reconciliation pass: checked every row below against code/tests/deployment/RFC acceptance
> criteria (not just prior labels). Six RFCs whose every step was shipped+verified, with nothing left but
> a ceremonial status promotion, were promoted to `done` and archived — `docs/archive/done/rfcs/`
> (`ARCH-bucket-album-modal-unification`, `ARCH-entity-interaction-v2`, `FEAT-playback-bucket-player`,
> `FEAT-member-player`, `FEAT-lyrics-sync-precision`, `ARCH-overlay-modal-isolation`). This is a
> self-promotion under CLAUDE.md rule #7's explicit-session-approval exception (owner's own reconciliation
> instructions, this session) — flagged prominently in the session report; reopen any of them freely if
> that judgment call was wrong. Owner-only observation items that don't gate anything stayed inside their
> archived RFC rather than lingering here. `FEAT-multi-user-accounts` moved to **Later** (all-owner-only
> remaining work, explicit "don't re-prompt"). `DATA-multidisc-track-order` and `DATA-release-noise`'s
> `(c)` moved to **Backlog** (draft/unclear-dependency, not concretely startable today).
> `FIX-lyrics-primary-artist + FIX-isrc-backfill` dropped entirely — implementation complete, remaining
> items were pure non-gating observation with no RFC to archive; detail → `docs/archive/done/2026-08.md`.

- **ARCH-buckit-navigation-shell** (**correction required; Step 1 + Step 3 remain SHIPPED**, front
  #396 `7921a9f` 2026-08-10, front #397 `7a597f7` 2026-08-10) — the deployed desktop selector + one
  shared detail and mobile drawer are preserved as implementation/deployment history but rejected as
  the future My Buckit structure. Step 2 URL-backed selection was confirmed absent at front
  `origin/main` `0d4f525` and **dropped unimplemented**; no URL/history work remains and it is not a
  blocker. Corrective removal is owned by the accepted `FEAT-inline-bucket-object-expand`, which restores
  independent inline expansion and keeps sibling Playback/smart content inside its owning inline
  bucket rather than a shared selection destination. **Its Step 0 concluded NO-GO on 2026-08-12:**
  required motion/size evidence and non-destructive handle isolation remain unavailable, so no
  implementation starts before an explicit owner-approved fallback/value decision. →
  `docs/rfcs/ARCH-buckit-navigation-shell.md`, `docs/rfcs/FEAT-inline-bucket-object-expand.md`.
- **FEAT-inline-bucket-object-expand** (**accepted; Step 0 NO-GO 2026-08-12 — OWNER DECISION REQUIRED**) — supersedes the
  accepted-but-unimplemented `FEAT-bucket-object-collapse`. The final target is one inline object +
  below-paper-label per bucket, independently expandable with local non-persistent state and no
  desktop/mobile selector, shared detail destination, or URL/history effects. Preserve all existing
  content, controls, hierarchy, DnD, Pocket bridge, mobile actions, and system protection. Step 0
  exhausted the prototype source/build/session, all reachable relevant workspace/front refs, and the
  supplied assets without recovering the required handle, drag-start, invalid-shake, item-received,
  disabled, or final production-size facts. The flattened raster cannot isolate the handle without
  losing body pixels; full-palette recoloring is unproven, so canonical red + a DOM accent is the
  recorded fallback; the ZIP label's fixed SVG text also differs from the blank prototype derivative.
  **Next = owner decision on explicitly defining new values and/or approving non-destructive fallbacks
  plus the blank runtime label source.** Production Step 1 remains blocked. No dependency on
  navigation-shell Step 2. → `docs/rfcs/FEAT-inline-bucket-object-expand.md`.
- **ARCH-global-playback-experience** (**accepted 2026-08-11; Step 1 SHIPPED + prod-verified**, front
  #398 `0d4f525` 2026-08-11) — closes the gaps `FEAT-playback-bucket-player` (done) and
  `ARCH-entity-interaction-domain-audit` Step 3 (3a/3b/3c done) left open, verified rather than
  assumed: `session.ts` now owns capability tier/device-list/shuffle/repeat/volume/liked/reconnect
  (previously `NowPlaying` kept them local "by design" per `component-map.md`'s own state-owner
  registry — that registry now needs updating to reflect Step 1), `readLivePlayback()` is single-flight
  (a single `MYBLOG_PLAYBACK_CHANGED` used to fan out to 3 uncoordinated live reads), live lyrics' open
  event is still app-wide with its only listener dashboard-scoped (`SelfDashboard`, unchanged — Step 2's
  scope), and the Playback Bucket's queue view still has no per-row artwork/reorder/play-all/summary —
  artwork needs one small, additive backend field (`Backend_TrackBrief.cover_url`, does not exist today;
  Step 3's scope). No new player, queue, or Home-specific playback state. Step 1 verification: `pnpm
  test` 60/60 files (623 tests) green, `pnpm lint` clean, `pnpm exec astro check` 0 errors — all
  independently re-run, not just self-reported by the implementing agent. A real regression was found
  and fixed during review before merge: `resolveCapability()`'s first draft permanently locked
  `capabilityTier` at `'fallback'` after any transient first-mint failure for the rest of the tab
  session (this codebase's `ClientRouter` keeps `session.ts`'s module state alive across route
  transitions while `NowPlaying` remounts per route) — fixed to dedupe-only semantics matching the
  original per-mount re-resolve behavior. Real-browser CDP verification of the live-Spotify-specific
  convergence behavior (shuffle/device across both surfaces, lock-screen Media Session) was not
  performed — no `.env` access in the isolated worktree — merged on explicit owner instruction accepting
  unit/lint/astro-check coverage as sufficient for this step; worth a live spot-check when convenient.
  Production smoke 19/19 passed post-deploy (quoted on front #398). **Next = Step 2** (one app-wide live
  lyrics host — relocate `ENT_OPEN_LIVE_LYRICS`'s listener from `SelfDashboard` to a layout-level mount),
  no ordering dependency on Step 1, startable in a new session. →
  `docs/rfcs/ARCH-global-playback-experience.md`.
- **FEAT-rating-smart-collections** (**draft — Step 0 decision gate blocks all implementation**) —
  평가 완료 (derived view over existing `rating IS NOT NULL` rows, zero new storage, already-shipped
  read endpoints + `lib/ratingStats.ts`) and 평가 예정 (new private per-user-album rating-intent state,
  explicitly distinct from `review_candidate`/평론 쓸 것 per `FEAT-album-review-authoring`'s own
  terminology prohibition). Storage shape (extend `album_reviews` vs. a dedicated table) is an open
  owner decision — `album_reviews`'s `ck_album_reviews_state_not_empty` CHECK makes "extend the same
  row" a real, non-free cost, not a trivial default. Nothing past Step 0 is startable yet. →
  `docs/rfcs/FEAT-rating-smart-collections.md`.

- **FEAT-album-review-authoring** (**in-progress; Steps 1+2 SHIPPED + prod-verified**) — album **평가 = rating**(public star rating + one-line comment), **평론 = review**(editor long-form review). Korean UI must not use "리뷰" for either concept. Step 1 shipped ≤60-char one-line rating comments + private `review_candidate`, extending the existing `album_reviews` state without a new table. Step 2 shipped rating count/average/distribution, sort by newest/rating/name, rating history, and editorial-candidate list. Entrance-link/visibility defects found after Step 2 were fixed and prod-verified.

  **Next gate: re-measure, baseline reset 2026-08-09.** Gate condition = since front `bd56910`(2026-08-09, `ARCH-bucket-album-modal-unification` Step 1 ship — the bucket-click path's first 평가 entry point at all), bucket additions ≥10 while owner ratings remain 0. If additions <10, **do not decide**. The prior baseline (`aebabe7`, 2026-08-02) was invalidated by owner decision 2026-08-09: before Step 1 shipped, the bucket-click path had no rating affordance, so any measurement against it would be against a known-incomplete entrance. No fixed re-check date — the earlier "two days" assumption was already disproved once by the full-history rolling-window measurement, so check the counter directly rather than waiting on a calendar guess.

  Steps remain:
  - **Step 3** — owner-only AI distillation pilot(C3+C4). OQ3 default-prompt wording remains open and is intentionally deferred until this gate.
  - **Step 4** — unified authoring entry + permission cleanup(C1 + audit E-5). OQ9 entry placement/form remains open.
  - **Step 5** — conditional general AI opening. OQ4 usage limit/wait-state remains open.

  AI behavior remains distillation only: use only material supplied by the author, never add outside facts/evaluations/metaphors, result remains editable, and publishing is always an explicit user action. The user-facing AI request will be the product's first actual API-engine caller. → `docs/rfcs/FEAT-album-review-authoring.md`.

- **ARCH-entity-interaction-domain-audit** (**draft; owner approved audit conclusions, but explicit status promotion has not occurred**) — independent audit of review/memo commands, playback-state ownership, lyrics hosting, bucket-add flow, modal infrastructure, and global events. Steps **1, 2, 3 (3a/3b/3c) and 4** are complete and prod-verified.
  - **Step 3a** fixed `NowPlaying`'s `controlBusyRef` race for external playback events using `localWriteSeq`.
  - **Step 3b** made `NowPlaying` subscribe to `playbackSession` for track identity + anchor convergence while keeping tier/mode/like/device/reconnect local.
  - **Step 3c** SHIPPED 2026-08-06 (front #374), closing Step 3 — it moved `LyricsViewer` synchronization-anchor ownership, the highest-risk part because it touches the sub-100ms synchronization path tuned by the (now-archived) `FEAT-lyrics-sync-precision`.

  **Next = Step 5** (memo naming conflict; blocked behind the `FEAT-album-review-authoring` gate above) — new session. → `docs/rfcs/ARCH-entity-interaction-domain-audit.md`.

_2026-08-06 playback/modal/security audit (8 parallel investigations over playback entry points, queue identity, modals and multi-user authorization). Everything it confirmed has since shipped; the only remaining deferral is its track-info no-op item, deliberately held for the canonical-track scope. Evidence and the full issue matrix live in the audit record and `git log`._

_Shipped implementation detail belongs in `git log`, RFCs and `docs/archive/done/`; plan.md retains only open decisions, gates, observations and status transitions._

---

## 2026-07-23 감사 파생 작업 (남은 것 = P2뿐)

> Source: `docs/reviews/2026-07-23-current-state-audit.md`.
>
> Only verified/accepted findings remain here. P0/P1 work is complete and archived.
>
> **Owner decision 2026-07-23:** prioritize safety/quality before discovery; retain the criticism-publication framing; OPS/REFACTOR RFCs accepted; documentation reconciliation approved.

### P2 — 실사용자 증거 후

- **CHORE-dep-reproducibility** — `myblog_backend` + `myblog_music`. Add lockfiles and pin `fastapi`/`boto3`/`SQLAlchemy`; replace backend non-tag SHA dependency with a tag. Trigger: another deployment 500 caused by dependency drift. Current additive convention remains accepted until then. Additional 2026-07-26 evidence: `SQLAlchemy==2.*` and `psycopg[binary]==3.*` re-resolve on deploy and wildcard strings create misleading CVE-search results. Dependency *notification* is separate → `OPS-safety-net-drift` Step 4.

- **DISCOVERY-flow** (**hypothesis; rejected for now**) — potential `signup → import → Buckit → publish → discovery` investment. Current evidence remains insufficient: published content, other-user activity, and public collections are too sparse for discovery investment to be meaningful. Re-evaluate only after real-user + content evidence. What the product's core flow should be remains an owner strategy decision.

---

## 2026-07-26 감사 파생 작업 (남은 것 = D-2 owner 결정뿐)

> Source: `docs/reviews/AUDIT-2026-07-26-system-audit.md` (ws #704, squash `9d4711c`). The report contains the evidence; these rows are pointers.
>
> **E-2/E-4/E-6/DEP-2 fixed + deployed + prod-smoked 2026-08-09** (front #389, ws #871). E-2/E-6/DEP-2 shipped code, verified live against the deployed bundle (`_astro/CollectionView.*.js` calls `publicMemberLabel`, `_astro/AlbumDetailView.*.js` carries the scoped `.lf-artist-link` rule, `/rss.xml` parses under 4.0.19). E-4 needed no code — superseded by the front #379–#384 home-card migration (merged 2026-08-06), whose `AlbumCard` open-hit button has no visible text content, so the WCAG 2.5.3 failure it described no longer exists.

- **D-2** — `LLMTransientError` is never retried at the engine level (`cli_engine.py:131-146` retries only `LLMValidationError`). **Re-measured 2026-08-09**: every caller was walked and none is exposed — `buckit_nightly.py` has its own 3×60s retry wrapper (fixed 2026-07-31), `research_poller.py`/`lyrics_translate_poller.py`/`genius_translate_poller.py` are self-healing via their claim queries, and `editor_buckit.py` is manual single-fire by design. The engine fix itself is real but is now defence-in-depth, not a live bug — shipping it means a cross-repo `myblog_shared_db` change + re-pin in backend/music/worker. **Owner call needed**: open it as its own cross-repo item, or close D-2 with no further action?

### Decided, no action

- **PUB-1** — workspace and four service repos are public; owner chose to merge the audit as-is on 2026-07-26. The report overstated dependency-version disclosure because manifests were already public. A-3 is fixed; the remaining E-5 surfaces are tracked under `FEAT-album-review-authoring` Step 4.

### Audit coverage boundary

The audit did **not** cover the full infra/IAM/S3/CloudFront/KMS/Cognito surface, all CI workflows, all tools/non-buckit scripts, frontend server-side code, PWA/service-worker config, all member-content escaping sites, load/concurrency testing, DB-level data quality, Terraform state, or complete Python-CVE call-path tracing. Do not read its clean findings as broader guarantees.

---

## Backlog

> Scope-ready drafts/deferred work. Each still needs an owner go (+ RFC accept where draft) before promotion to Active.

- **CHORE-research-prompt-port-not-swap** (**legs 1–6 SHIPPED 2026-07-30; measurements remain**) — do **not** replace `album_research_v2` with v4 wholesale. Controlled RENAISSANCE comparison scored **v2 12/22, v4 12/22**, with complementary rather than strictly better coverage. v4 improved biography/primary-statement pressure but lost v2's explicit "do not import others' critical verdicts" protection and costs more tokens/wall time. The shipped approach ports the useful v4 pressure into v2, retains the no-verdict rule, adds liner-notes and sample-chain-depth requirements, injects catalog context, and intentionally keeps `PROMPT_VERSION=v2` so stored notes remain visible.

  Remaining measurements only:
  1. Re-run RENAISSANCE against the checked-in 22-item sheet + ONYX with `grep -ci izm = 0`; record score, wall clock, output length and **actual per-hop citation support**. Pass target = recover ≥3 of items 5/6/8/22 at ≤1.3× v2 wall clock.
  2. Generalisation test on one album not used to create the rules.
  3. First `[확인]` precision audit; no false-`[확인]` denominator exists yet.

  Highest-information measurement remains owner writing **one review from one research note** and marking used/unused material; the current prompt metrics are proxies because 80 notes have produced 0 completed reviews. Evidence → `docs/editorial/research-note-requirements.md` + `docs/reviews/measurements/2026-07-30-research-prompt-v2-vs-v4/`.

- **FEAT-ai-editorial-critique** (**draft; deferred**) — Phase 0 thin slice: backend-only AI editorial critic that runs the existing critique method over a draft + already-linked album DB facts, returning grounded Korean feedback + uncertainty/checklist markers, never rewriting the draft. Step 1 = local implementation + golden eval; Step 2 = infra JWT route + contract. UI, persistence, planner, publish gate and broader fact checking remain non-goals. Needs owner accept before Active.

  Open thread (from `FEAT-editor-buckit`, 2026-06-19) — on promotion: fold in the explicit two-stage editorial pipeline (nightly full-draft → critique pass), re-audit the stale "zero AI/LLM code" Current State, gate via `require_owner` rather than bare `require_cognito_token`, and convert its Secrets Manager references to SSM (`CHORE-secrets-ssm-migration`). → `docs/rfcs/FEAT-ai-editorial-critique.md`.

- **DATA-catalog-noise-and-lyrics-coverage** (**accepted; implementation complete except observation gates**) — Steps **1a + 2 + 3a + 3b + 4 SHIPPED**; Step **1b DROPPED** by owner decision 2026-08-03. Search noise is handled by ranking rather than catalog filtering so classical material remains findable. Step 2 is the ingest choke point and absorbs `DATA-release-noise (a)`. Step 3a parks empirically low-yield lyrics rows; Step 3b drains the previously unreachable `best-of-*` supersession backlog first; Step 4 album-scoped reassessment is live.

  Remaining observations:
  1. trailing-7-day classical album share **37% → ≤8% around 2026-08-11**;
  2. holdout misclassification rate after enough `classical_holdout` samples accumulate;
  3. lyrics-pool query 6 should trend toward ~450 unsupersedable rows by ~2026-08-29, after which unresolved recovery should naturally return to the queue head.

  Step 3b's first production tick already confirmed **102 `best-of-*` rows superseded** on 2026-08-03. → `docs/rfcs/DATA-catalog-noise-and-lyrics-coverage.md`.

- **FEAT-genre-recommendation** (**Frozen; gated on review volume**) — related-review recommendation on `/review/{slug}` based on shared sub-genres + linked genre edges. Substrate is live, but there is not enough published review volume to rank meaningfully. Re-open after sufficient review/tag volume exists. Owner edge-authoring API remains lowest priority. → `docs/rfcs/FEAT-genre-recommendation.md`.

- **FEAT-blog-to-review-migration** — Step 1 `/blog → /review` prefix migration DONE + prod-live 2026-06-14. Only optional Step 2 remains: true HTTP 301 via the console-managed CloudFront Function if meaningful inbound `/blog` links accumulate. Static stubs already prevent 404s, so Step 2 is SEO-only. → `docs/rfcs/FEAT-blog-to-review-migration.md`.

- **CHORE-neuralwatt-credit-burn** (**opt-in path SHIPPED; default switch rejected by parity gate**) — NeuralWatt glm-5.2 routing exists for genre-heal, but identical input produced unstable K-Pop/idol classifications on an axis that writes `confidence=high` DB state. Default therefore remains `claude -p`; burn is deferred. Open owner decision: retry with a hardened idol-axis rubric or leave NeuralWatt opt-in only. Key location remains the owner's prior decision and should not be re-raised.

- **FEAT-bucket-identity** (**A DONE; B DONE; C subsumed; D audited + gated**) — Direction D's old "next concrete step" is stale because 4/5 proposed collection types already exist as dedicated non-bucket surfaces; only genre-review collections remain unbuilt. Review-based collections remain gated by published-review volume, and album-based public collections remain gated by owner curation/public-bucket evidence. Re-open only when the RFC's audit gates are met and re-measured. Existing proposals such as `/profile` landing tab, research-note deep link and in-place bucket-tab switch remain proposals, not active work. → `docs/rfcs/FEAT-bucket-identity.md`.

- **DATA-multidisc-track-order** (**draft RFC written 2026-08-09; not yet owner-approved**) — the `tracks` table has **no `disc_no`/`disc_number` column at all** (ORM `myblog_shared_db/src/myblog_shared_db/models.py:273-321`, canonical schema `tests/canonical_schema.sql:265-279`, zero hits across all 50 migrations — it was never added, not dropped). `myblog_music`(`track_repo.py:163`) and `myblog_worker`(`sync_service.py:174`) both read only Spotify's `track_number` and never reference `disc_number`, so a schema fix needs a twin-drift sweep across both. **Live-data spot check done 2026-08-09**: `GROUP BY album_id, track_no HAVING count(*) > 1` finds **77 of 3313 albums (~2.3%)** with a repeated `track_no`, both classical multi-work compilations and clean 2-disc mainstream releases (Nirvana *In Utero (Deluxe Edition)*, *Hamilton* OBC, *SOS Deluxe: LANA*, *SWAG II*, Rolling Stones *Forty Licks*). Confirmed real interleaving on *In Utero*, not just adjacent duplicate `track_no` values: disc 1/disc 2 "Serve The Servants" both land at `track_no=1` with identical `created_at`, so the tie-break falls through to arbitrary `id` order.

  Managed as a data-model migration, independent of the card/playback-state refactors: (1) `myblog_shared_db` migration adding `tracks.disc_no INTEGER` + prod apply **before merge**; (2) backfill the ~77 currently-colliding albums via a one-off Spotify re-fetch (not locally computable) plus the `myblog_music`/`myblog_worker` twin fix; (3) switch every `ORDER BY` to `(disc_no, track_no)` — **4 sites** (`bucket_service.py` + 3 in `myblog_music/track_repo.py`); (4) OpenAPI re-export → contract merge → frontend type regeneration. **Needs owner RFC-accept before promotion to Active.** → `docs/rfcs/DATA-multidisc-track-order.md`.

- **DATA-release-noise (c) exact-dup dedup** (P1 remainder — from FEAT-release-calendar OQ4 + 2026-07-23 audit P-7) — Step (b) read-side compilation-noise filter SHIPPED + prod-smoked 2026-07-24 (homepage compilation noise 7/12→0/12; `/releases/` ~36→1); former Step (a) ingest-side work is **absorbed by `DATA-catalog-noise-and-lyrics-coverage` Step 2**. Only **(c) exact-dup dedup** remains, and its plan.md dependency note (`PERF-home-feed-latency`) has never been a real RFC/plan row — it appears nowhere outside this line since it was written 2026-07-23, so treat it as a stale/unconfirmed sequencing preference, not a hard blocker; **owner should confirm whether it's still intended before this is picked up.**

---

## Later (트리거 대기)

- **FEAT-multi-user-accounts** (**in-progress since 2026-07-07; all remaining work is owner-only**) — multi-user platform: Google+Kakao signup, public album ratings, per-user buckets, Last.fm/Spotify member listening, `LLMEngine`. Phases 0–4 + P3b/3c + library user-scope + 07-14 surface-audit remediation + profile-merge PR1–3 are SHIPPED & prod-verified. Read "Phase 4 SHIPPED" narrowly: the owner-central `LLMEngine` interface/CLI/API skeleton + usage metering exists, but **no caller is wired to the API engine yet**; the first user-facing AI call belongs to `FEAT-album-review-authoring`. Existing rating behavior remains unchanged. **Every remaining item needs the owner, not Claude**: launch gates G1/G2 (≥10 reviews by ≥5 non-owner users within 4 weeks of public launch), Google brand verification, Kakao production review, OAuth secret reissue, owner live-login `returnTo` observation, and the necessity-gated canonical member URL decision (`/members/?u=` vs `/members/[handle]`). Owner deferred launch work 2026-07-20; **do not re-prompt without a new trigger.** → `docs/rfcs/FEAT-multi-user-accounts.md`.

- **SEO-review-structured-data 첫 발행 검증** — implementation DONE 2026-07-19 and RFC archived. `Review` + `MusicAlbum` JSON-LD is already generated and locally validated. **Trigger = first production review publication** → run Rich Results Test once against the real published URL. → `docs/archive/done/rfcs/SEO-review-structured-data.md`.

- **FIX-nightly-draft-identity Phase B** (**planned; trigger-gated**) — the P0/Phase A problem was resolved 2026-07-27 with a dedicated nightly Cognito identity, draft-only coercion, owner-pinned grow, counted Phase-B trigger, and live E2E verification. Phase B adds multi-user post ownership, bucket-derived acting user, and read-side scoping only when any RFC §4 trigger fires. Watch `PHASE-B TRIGGER` in nightly logs. → `docs/rfcs/FIX-nightly-draft-identity.md`.

---

## Frozen (아이디어만, RFC 없음)

확장 기능 후보. 의향이 생기면 그때 RFC를 시작하며 지금은 작업하지 않는다.

- **FEAT-genre-autoheal — cloud heal** — only the cloud iTunes-only variant remains deferred. Local daily genre-heal and the on-demand request queue are already live. Blocker: the richer local S3 pass shells `claude -p` using subscription auth unavailable in Lambda, so any cloud-only baseline pass would need a distinct partial marker and must not suppress the later local LLM pass.

- **Per-genre exemplar albums** — start inside `definition_md` markdown; introduce structured linking only when an actual consumer requires it.

- **Background `inert`/`aria-hidden` on open modals** — `useDismissable` doesn't deactivate the background for screen readers/tab order while a modal is open; `ARCH-overlay-modal-isolation`'s own scope (Non-goals) deliberately excluded this, only fixing scroll isolation. Recommended as a separate accessibility RFC if pursued, not a reopening of that RFC. → `docs/archive/done/rfcs/ARCH-overlay-modal-isolation.md` OQ2.
