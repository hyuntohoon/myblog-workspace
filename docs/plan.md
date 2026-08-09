# Plan

Active workspace tracker for cross-repo work. Each row carries `Scope / Order (if multi-repo) / Verification (local + prod smoke) / Rollback / Status`; RFC-backed entries collapse to a one-line pointer at `docs/rfcs/<id>-<slug>.md`. When a row finishes, drop it — `git log` and `docs/archive/done/YYYY-MM.md` are authoritative for history.

---

## Active

- **FEAT-lyrics-sync-precision** (**implementation complete; owner observation only**) — Steps 1+2 SHIPPED + prod-verified 2026-08-01. Fixed `SYNC_LEAD_MS = 300` was structurally removed via next-boundary scheduling, fast-attack/slow-release rendering, and event-driven re-anchoring. Transport playback-change publication was completed by front #342. No polling(D28), no persisted/learned offsets. Step 3 measured `AudioContext.outputLatency` and ended **NO-GO**: Spotify SDK/Connect playback does not share our `AudioContext` output path, so the value cannot represent the actual playback latency. Remaining: **owner real-device listening check 1건**, non-blocking. → `docs/rfcs/FEAT-lyrics-sync-precision.md`.

- **FEAT-multi-user-accounts** (**in-progress since 2026-07-07**) — multi-user platform: Google+Kakao signup, public album ratings, per-user buckets, Last.fm/Spotify member listening, `LLMEngine`. Phases 0–4 + P3b/3c + library user-scope + 07-14 surface-audit remediation + profile-merge PR1–3 are SHIPPED & prod-verified. Read "Phase 4 SHIPPED" narrowly: the owner-central `LLMEngine` interface/CLI/API skeleton + usage metering exists, but **no caller is wired to the API engine yet**; the first user-facing AI call belongs to `FEAT-album-review-authoring`. Existing rating behavior remains unchanged. Remaining work is owner-only: launch gates G1/G2, Google brand verification, Kakao production review, OAuth secret reissue, owner live-login `returnTo` observation, and the necessity-gated canonical member URL decision (`/members/?u=` vs `/members/[handle]`). G1 remains ≥10 reviews by ≥5 non-owner users within 4 weeks after public launch. Owner deferred launch work 2026-07-20; do not re-prompt without a new trigger. → `docs/rfcs/FEAT-multi-user-accounts.md`.

- **FEAT-album-review-authoring** (**in-progress; Steps 1+2 SHIPPED + prod-verified**) — album **평가 = rating**(public star rating + one-line comment), **평론 = review**(editor long-form review). Korean UI must not use "리뷰" for either concept. Step 1 shipped ≤60-char one-line rating comments + private `review_candidate`, extending the existing `album_reviews` state without a new table. Step 2 shipped rating count/average/distribution, sort by newest/rating/name, rating history, and editorial-candidate list. Entrance-link/visibility defects found after Step 2 were fixed and prod-verified.

  **Next gate: re-measure after 2026-08-12.** Gate condition = since front `aebabe7`(2026-08-02 13:40Z), bucket additions ≥10 while owner ratings remain 0. If additions <10, **do not decide**. The earlier assumption that 10 additions would arrive within two days was disproved by the full-history rolling-window measurement, so measuring again before 2026-08-12 adds little information.

  Steps remain:
  - **Step 3** — owner-only AI distillation pilot(C3+C4). OQ3 default-prompt wording remains open and is intentionally deferred until this gate.
  - **Step 4** — unified authoring entry + permission cleanup(C1 + audit E-5). OQ9 entry placement/form remains open.
  - **Step 5** — conditional general AI opening. OQ4 usage limit/wait-state remains open.

  AI behavior remains distillation only: use only material supplied by the author, never add outside facts/evaluations/metaphors, result remains editable, and publishing is always an explicit user action. The user-facing AI request will be the product's first actual API-engine caller. → `docs/rfcs/FEAT-album-review-authoring.md`.

- **DATA-release-noise** (P1 — from FEAT-release-calendar OQ4 + 2026-07-23 audit P-7) — Step (b) read-side compilation-noise filter SHIPPED + prod-smoked 2026-07-24. Prod measurement: homepage compilation noise 7/12→0/12; `/releases/` ~36→1. The former Step (a) ingest-side work is **absorbed by `DATA-catalog-noise-and-lyrics-coverage` Step 2**. Remaining in this row: **(c) exact-dup dedup**. Deps: PERF-home-feed-latency.

- **FIX-lyrics-primary-artist + FIX-isrc-backfill** (**implementation complete; observation only**) — code/data/schedule work complete. LRCLIB artist-search accuracy improved **45.3%→96.8%** on the 1,793-track ground truth; `tracks.isrc` reached **26,594/26,619 = 99.9%** and the backlog schedule was reduced to weekly.

  Remaining:
  - **Observation (a)** — confirm once that the weekly ISRC slot picks up newly ingested tracks.
  - **Observation (b)** — measure `not_found` recovery after changed queries. Search terms materially change for **5,412 / 14,034 = 38.6%** of rows; a manual n=40 run recovered 5 rows, but that sample is not a rate estimate.
  - Follow-up evidence only: querying LRCLIB once per credited artist can remove the remaining representative-artist ceiling at higher request cost; exact ISRC duplicates provide a strong future catalog-dedup key (**1,982 duplicate ISRCs / 4,571 rows / 2,589 potentially removable rows**).

  Detailed implementation history → `git log` + `docs/archive/done/2026-07.md`.

_2026-07-18 UI/UX planning session: areas 1–6, 9 and 10 were investigated and folded into the rows below/above; **areas 7·8·11·12 remain deferred to a follow-up measurement/research session.**_

- **FEAT-member-player** (**implementation complete; owner status/observation pending**) — Steps 1–7 and all implementation candidates are SHIPPED. Cold-start playback was confirmed on a real device 2026-08-03, closing the primary gate that existed because playback had failed to start in real use. The rung1→rung2 handoff and in-page device path therefore have real-use evidence, not only tests.

  Remaining owner checks are non-blocking:
  - remaining **5 playback surfaces** individually;
  - real second-device bidirectional transfer;
  - OS media keys;
  - `/write` audio continuity.

  One documented constraint carries forward: **Step 6c (다음에 듣기) ships dormant and track-only** — the Spotify queue endpoint accepts a track or episode uri but never an album, so 6c could not ride 6b's album surfaces, and its only surface is `/review/[slug]` while prod has **zero** published reviews. Adding the action to the live overlay's shared `TrackRow` was refused on purpose as a documented owner product decision. 6c is therefore unreachable until the first review is published.

  Status promotion to done remains an owner decision. → `docs/rfcs/FEAT-member-player.md`.

- **FEAT-playback-bucket-player** (**accepted; Steps 2–7 SHIPPED; Step 8 preflight complete**) — per-user system-owned playback bucket; album→ordered tracks expansion; queue projection; docked/detachable playback panel; queue-replacement playback; cross-tab single-owner playback; live-playback adoption; and playback entry fixes are complete. The queue remains our own ordered list rather than Spotify's queue; playback reuses `FEAT-member-player`'s existing `play(intent)` ladder. No polling(D28).

  Step 8 preflight audit completed 2026-08-04 and fixed the deployed player defects it found, including local-write/adoption races, natural-end detection, live lyrics entry, external album lookup, and misleading mobile tab semantics. **That preflight was not Step 8 itself.**

  The Step 8 prerequisite `ARCH-entity-interaction-v2` Steps 1–3 is satisfied. **Next = Step 8**, owner start decision required. → `docs/rfcs/FEAT-playback-bucket-player.md`.

- **ARCH-entity-interaction-domain-audit** (**draft; owner approved audit conclusions, but explicit status promotion has not occurred**) — independent audit of review/memo commands, playback-state ownership, lyrics hosting, bucket-add flow, modal infrastructure, and global events. Steps **1, 2, 3 (3a/3b/3c) and 4** are complete and prod-verified.
  - **Step 3a** fixed `NowPlaying`'s `controlBusyRef` race for external playback events using `localWriteSeq`.
  - **Step 3b** made `NowPlaying` subscribe to `playbackSession` for track identity + anchor convergence while keeping tier/mode/like/device/reconnect local.
  - **Step 3c** SHIPPED 2026-08-06 (front #374), closing Step 3 — it moved `LyricsViewer` synchronization-anchor ownership, the highest-risk part because it touches the sub-100ms synchronization path tuned by `FEAT-lyrics-sync-precision`.

  **Next = Step 5** (memo naming conflict; blocked behind the `FEAT-album-review-authoring` gate of 2026-08-12+) — new session. → `docs/rfcs/ARCH-entity-interaction-domain-audit.md`.

- **ARCH-entity-interaction-v2** (**accepted; implementation closed; owner status promotion pending**) — Steps 1–6 all completed by 2026-08-06. Canonical album/track/artist definitions, drop matrix, single drag payload + adapters, real gesture measurement, surface-level play/add/drag grants, and `component-map.md` refresh are complete. No implementation step remains in this RFC.

  Erratum recorded 2026-08-06: the Step 5 completion summary was too broad at slot-pair level — `MemoWindow` received `drag` without the touch-accessible `add` counterpart required by Rule #14. The RFC was not reopened; the defect was tracked independently and **resolved by `ARCH-album-card-contract-and-composition` Stage 7 (front #382)**.

  Status promotion from accepted remains an owner decision. → `docs/rfcs/ARCH-entity-interaction-v2.md`.

- **DATA-multidisc-track-order** (confirmed 2026-08-06 — structural defect, already self-documented and deferred) — the `tracks` table has **no `disc_no`/`disc_number` column at all** (ORM `myblog_shared_db/src/myblog_shared_db/models.py:273-320`, canonical schema `tests/canonical_schema.sql:265-279`, zero hits across all 51 migrations — it was never added, not dropped). `myblog_music`(`track_repo.py:163`) and `myblog_worker`(`sync_service.py:174`) both read only Spotify's `track_number` and never reference `disc_number`, so a schema fix needs a twin-drift sweep across both. Every album-tracklist read path orders by `track_no ASC NULLS LAST` alone, including `FEAT-playback-bucket-player`'s album→tracks queue expansion (`myblog_backend/bucket_service.py:1044-1050`). Because Spotify restarts `track_number` at 1 per disc, disc 1 track 3 and disc 2 track 3 tie and fall back to arbitrary `created_at`/`id` insertion order. `bucket_service.py:1018-1022`'s own docstring already records this limit — known deferred debt, not a new finding. The frontend does no reordering and correctly trusts backend order, since `track_no` alone carries no signal to resolve a disc collision. No repo fixture contains a real multi-disc album, so a **live-data spot check is required first** — verification SQL → `inv-8-multidisc-ordering.md` §5.

  Managed as a data-model migration, independent of the card/playback-state refactors: (1) `myblog_shared_db` migration adding `tracks.disc_no INTEGER` + prod apply **before merge**; (2) backfill requires a Spotify re-fetch (not locally computable) plus the `myblog_music`/`myblog_worker` twin fix to start collecting `disc_number`; (3) switch every `ORDER BY` in `myblog_music`/`myblog_backend` to `(disc_no, track_no)`; (4) OpenAPI re-export → contract merge → frontend type regeneration (no frontend logic change).

- **ARCH-overlay-modal-isolation** (**draft**, created 2026-08-06; **Step 3 keyboard half SHIPPED 2026-08-06** in front #382) — owns the remaining systemic overlay-isolation gap: **16 of 27 scrim-backed dialogs still omit `useScrollLock`**, and the app lacks shared overscroll/iOS containment. Front #382 independently registered `AddToBucketMenu` with `useDismissable`; nested-host tests and a real 390×844 browser pass now prove autofocus, Tab trapping, top-layer Escape, and trigger-focus restoration. The picker still lacks scroll locking, so **Step 1/2 and Step 3's scroll-isolation half remain open**. → `docs/rfcs/ARCH-overlay-modal-isolation.md`.

_2026-08-06 playback/modal/security audit (8 parallel investigations over playback entry points, queue identity, modals and multi-user authorization). Everything it confirmed has since shipped except the two rows above; the only remaining deferral is its track-info no-op item, deliberately held for the canonical-track scope. Evidence and the full issue matrix live in the audit record and `git log`._

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

---

## Later (트리거 대기)

- **SEO-review-structured-data 첫 발행 검증** — implementation DONE 2026-07-19 and RFC archived. `Review` + `MusicAlbum` JSON-LD is already generated and locally validated. **Trigger = first production review publication** → run Rich Results Test once against the real published URL. → `docs/archive/done/rfcs/SEO-review-structured-data.md`.

- **FIX-nightly-draft-identity Phase B** (**planned; trigger-gated**) — the P0/Phase A problem was resolved 2026-07-27 with a dedicated nightly Cognito identity, draft-only coercion, owner-pinned grow, counted Phase-B trigger, and live E2E verification. Phase B adds multi-user post ownership, bucket-derived acting user, and read-side scoping only when any RFC §4 trigger fires. Watch `PHASE-B TRIGGER` in nightly logs. → `docs/rfcs/FIX-nightly-draft-identity.md`.

---

## Frozen (아이디어만, RFC 없음)

확장 기능 후보. 의향이 생기면 그때 RFC를 시작하며 지금은 작업하지 않는다.

- **FEAT-genre-autoheal — cloud heal** — only the cloud iTunes-only variant remains deferred. Local daily genre-heal and the on-demand request queue are already live. Blocker: the richer local S3 pass shells `claude -p` using subscription auth unavailable in Lambda, so any cloud-only baseline pass would need a distinct partial marker and must not suppress the later local LLM pass.

- **Per-genre exemplar albums** — start inside `definition_md` markdown; introduce structured linking only when an actual consumer requires it.
