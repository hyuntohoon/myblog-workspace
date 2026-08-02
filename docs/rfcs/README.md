# RFCs

Multi-step migrations, architectural changes, and any work that:

- spans 2+ repos
- needs more than one session to complete
- has reversibility / migration order concerns that don't fit in a `plan.md` row

…lives here as a long-form RFC. `plan.md` keeps a one-line pointer.

## RFC vs ADR

These two often get confused. They serve different purposes and have different lifecycles.

| | RFC (`docs/rfcs/`) | ADR (`docs/archive/decisions/`) |
|---|---|---|
| **Purpose** | Plan and execute future work | Record the outcome of a past decision |
| **Lifecycle** | Created → executed → archived to `docs/archive/done/rfcs/` | Created → permanent |
| **Tense** | "We will…" | "We decided…" |
| **Updates** | Live document; Status + steps update during execution | Append-only; if reversed, write a new ADR superseding the old |
| **Length** | Long — full migration steps, verification, rollback | Short — context, decision, consequences |

An RFC that involves a structural decision usually produces an ADR as its final step (e.g. ARCH-6 → ADR 0005). The ADR survives; the RFC moves to `done/`.

## When to write an RFC vs. just a `plan.md` row

| Use `plan.md` only | Write an RFC |
|--------------------|--------------|
| Single repo, < 1 day | 2+ repos OR multi-day |
| One PR | Multiple PRs with ordering constraint |
| Rollback is trivial (revert) | Rollback needs explicit steps |
| No structural decision | Introduces or changes a structural rule |

## File naming

`<PLAN_ID>-<short-kebab-desc>.md` — same plan ID as the `plan.md` row.

Example: `ARCH-6-shared-db-package.md` ↔ `plan.md` row `ARCH-6`.

## Status lifecycle

RFCs go through four states. Both the RFC's own `Status:` line and the matching `plan.md` row must reflect the same state.

| Status | Meaning | Transition trigger |
|--------|---------|--------------------|
| `draft` | Author writing or revising. Not yet ready for execution. | Author edits until they think it's executable as-is. |
| `accepted` | Reviewed and approved. Step 1 may begin. | Human says "accepted" explicitly. AI never self-promotes. |
| `in-progress (Step N)` | Step N is the next step to execute. (Not "currently running" — "next up".) | After a step's verification passes and the merge SHA is recorded, bump N. |
| `done` | All steps complete, ADR (if any) merged, file ready to archive. | Final step verification + cleanup pass complete. |

Once `done`, the RFC is moved to `docs/archive/done/rfcs/<PLAN_ID>-*.md`.

## Required sections

Every RFC must have:

1. **Status** — one of the four above. Single source of truth for progress.
2. **Goal** — one paragraph, no preamble. What's true after this is done?
3. **Non-goals** — what we explicitly will not do in this RFC. Prevents scope creep mid-execution.
4. **Current state** — concrete: file paths, function names, current behavior. No abstractions.
5. **Target state** — same concreteness as current state.
6. **Steps** — ordered, each step independently mergeable when possible. Each step has its own Verification block. Each step that's non-trivial to revert has its own Rollback block.
7. **Open questions** — any unresolved decision that blocks a step.
8. **Decisions log** — table of in-flight decisions made during execution, with date and step.

See `TEMPLATE.md` for a starting skeleton.

## How to give an RFC to Claude Code

These RFCs are written assuming Claude Code is the executor. Two usage patterns:

**Pattern A — full RFC, let Claude pick the next step:**
```
Read docs/rfcs/<PLAN_ID>-<slug>.md. Tell me the current Status,
then propose the next step's plan before touching code.
```

**Pattern B — pin to a specific step:**
```
Read docs/rfcs/<PLAN_ID>-<slug>.md. Execute Step 2 only.
Stop after Verification and report results.
```

Both patterns end the same way: Claude commits but does not push or merge.
Human runs verification commands or trusts Claude's verification output,
then says "ok push" / "ok merge" explicitly.

Workspace `CLAUDE.md` enforces one-step-per-session as a hard rule unless the RFC marks steps as parallel-safe.

## Updating the RFC during execution

When a step completes:

1. Bump the RFC `Status` line (e.g. `in-progress (Step 2)` → `in-progress (Step 3)`).
2. Add a one-liner under the completed step: `> ✅ Done <date>, SHA: <merge sha>`.
3. If a decision was made mid-step, log it in the Decisions log table.
4. Do **not** delete completed steps from the RFC — they are part of the migration's history. Only when the entire RFC is `done` does the file get archived to `docs/archive/done/rfcs/`.

## Index

In-flight RFCs only. Once `done`, an entry stays here for one cycle as a breadcrumb to the archive, then gets dropped — `git log` and `docs/archive/done/rfcs/` are authoritative for history.

- **OPS-delivery-safety-gates** (done 2026-07-24, **archived** — breadcrumb) — CI merge gates + deploy smoke + async failure boundaries. **Steps 1–5 all shipped**: PR-blocking pytest/check gates (backend #130 / worker #77 / front #306); post-deploy health-only smoke (Step 3: backend #132·music #59·worker #78+#79·front #313, worker IAM `lambda:InvokeFunction` v2 + `function-updated-v2` waiter); async cron boundary (Step 4: `worker-cron-dlq` + worker `event_invoke_config` on_failure + `FailedInvocations` 2→12, `terraform apply` 14 add/0/0 AWS-verified); rollback runbook (`docs/ops/rollback.md`). 본문 → `docs/archive/done/rfcs/OPS-delivery-safety-gates.md`.
- **REFACTOR-frontend-member-surface** (done 2026-07-24, **archived** — breadcrumb) — test net + shared fetch client + boundary extraction for the member surface. **Steps 1–4 all shipped + prod-smoked 2026-07-24** (front #307/#308/#309 + Step 4 #310/#311/#312): vitest harness (33 tests) → apiFetch timeout/abort → `crMeta` → `@lib/bucketLifecycle` → (Step 4, owner opened the necessity gate) DnD logic → `@lib/boardDnd`, Spotify surface → `useSpotifyLibrary`, `ActionSheet` shell → own file. Final suite **66 tests**. 본문 → `docs/archive/done/rfcs/REFACTOR-frontend-member-surface.md`.
- **FEAT-lyrics-sync-precision** (in-progress — **Steps 1+2 shipped + prod-verified 2026-08-01**, front #325 `0f5748b`; **Step 3 measured → NO-GO, ships no code**; remaining = the owner's real-device listen check on `PERCEPTUAL_LEAD_MS = 80`) — killed the viewer's fixed `SYNC_LEAD_MS = 300` by removing the two error sources it was silently cancelling (250 ms tick grain +125, `.lyv-line` 0.35 s opacity ramp +175). CDP on the real dashboard measured the result: line flip **65 ms before `start_ms`, zero variance** (was 0–250 ms spread by construction). Step 2 closed the three silent-divergence cases — the viewer had no pause concept at all — via `MYBLOG_PLAYBACK_CHANGED` + tab return, and carved a position-carrying `paused` state out of `idle`, whose consumer sweep caught `NowPlayingLyricsEntry` mis-routing it into `확인 실패`. **No polling (D28 upheld unchanged), no stored/learned offset, frontend only.** → `FEAT-lyrics-sync-precision.md`.
- **FEAT-lyrics-viewer-playback** (done 2026-08-03, **archived** — breadcrumb) — transport bar (⏮ ⏸ ⏭) + full-screen queue swap inside the live lyrics viewer. **Steps 1–3 all shipped + prod-smoked and all owner-confirmed on a real device** (front #327/#328/#329, follow-ups #330/#333); queue is a screen swap, not a sheet, because the viewer's vertical drag is already line-stepping; row tap tries `context_uri`+`offset` and falls back to `uris` carrying the visible **tail**, never a lone track. Both blocking OQs closed by evidence rather than assumption — OQ1 by minting the live grant (the scope constant under-described it), OQ2 by the owner picking try→fall back→give up. **OQ4 closed 2026-08-03** (front #342): `sendPlayerCommand` dispatches now, which finally puts a transport command into `FEAT-lyrics-sync-precision`'s `'command'` residual series — and exposed that `NowPlaying.applyLive` had been folding `paused` into `idle`. 본문 → `docs/archive/done/rfcs/FEAT-lyrics-viewer-playback.md`.
- **FEAT-multi-user-accounts** (in-progress) — multi-user platform umbrella (Google+Kakao signup, RYM-style public reviews, per-user buckets, Last.fm/Spotify member listening). **Phases 0–4 + 3b/3c + library user-scope + 07-14 surface-audit remediation + profile-merge PR1–3 all shipped & prod-verified**; remaining = owner-only launch gates G1/G2 + deferred canonical-link decision. → `FEAT-multi-user-accounts.md` (Phase 4 engine → archived `docs/archive/done/rfcs/FEAT-multi-user-accounts-p4-llmengine.md`).
- **FEAT-multi-user-accounts-p4-llmengine** (done 2026-07-11, **archived** — breadcrumb) — `LLMEngine.run(job)` ABC unifying the 5 `claude -p` callsites (engine home = `myblog_shared_db/.../llm/`; shared_db #59, `llm_usage` prod-applied; live-site cutover 5/5). Necessity-gated residue rides with the RFC: `/myblog/anthropic` SSM provisioning at the first real ApiEngine caller; BYOK → Gate G2. 본문 → `docs/archive/done/rfcs/FEAT-multi-user-accounts-p4-llmengine.md`.
- **FEAT-member-player** (in-progress) — capability-tiered player bar rebuild of '지금 듣는 음악' (D1; D28 no-polling upheld). **Steps 1–4 shipped + prod-smoked 2026-07-19→20** (scopes/re-consent; per-member token mint, member-without-connection → 404 per #126; hairline-LCD bar + Connect remote + clock-estimate fallback, front #293; 'Listening on <device>' bottom-edge hint, front #297; Step 4 owner real-device check confirmed 2026-07-20). Next = Step 5 in-page SDK device (opt-in output) + Step 6 candidate menu (Connect control extensions) + Step 7 candidate (capability transparency: 연동 안내/설명서, backed by the RFC's user-situation capability matrix) — owner selects subsets at promotion. → `FEAT-member-player.md`.
- **RFC-ui-surface-unification** (done 2026-07-21, **archived** — breadcrumb) — dual-modal rule codified + dead-spot fixes + artist links with full id plumbing. **Steps 1–5 all shipped + prod-smoked** (Steps 1–3 front #290/#292/#296; Step 4 id plumbing ws #673/backend #127/music #57/front #299; Step 5 ws #676/music #58/front #300). 본문 → `docs/archive/done/rfcs/RFC-ui-surface-unification.md`. _(2026-07-23 audit O-9: index had stale in-progress entry — corrected.)_
- **FEAT-lyrics-viewer-controls** (done 2026-07-20, **archived** — breadcrumb) — scroll-suspend + return behaviors + header ⚙ popover (Steps 1+2, front #289/#295). Owner keeper pick 2026-07-20 = **D (browse) + A's circular countdown ring**; loser-removal chore front #298 shipped + prod-smoked same day. 본문 → `docs/archive/done/rfcs/FEAT-lyrics-viewer-controls.md`.
- **SEO-review-structured-data** (done 2026-07-19, **archived** — breadcrumb) — `Review` + `MusicAlbum` JSON-LD on `/review/[slug]`, build-time only. **Step 1 shipped 2026-07-19** (front #288; inert in prod until the first review publish). Remaining observation gate: Rich Results Test on the first live review URL (indefinite) → plan.md row. 본문 → `docs/archive/done/rfcs/SEO-review-structured-data.md`.
- **FEAT-release-calendar** (done 2026-07-23, **archived** — breadcrumb) — public new-release surfaces (home 새 앨범 card + `/releases/` 신보 캘린더, multi-source MB+iTunes poller + day-0 confirm). **Steps 1–7 all shipped 2026-07-11→13**; owner promoted accepted→done 2026-07-23. Data-quality follow-on (OQ4 noise + 2026-07-23 audit P-7) → `plan.md` DATA-release-noise. 본문 → `docs/archive/done/rfcs/FEAT-release-calendar.md`.
- **FEAT-for-you-releases** (done 2026-07-21, **archived** — breadcrumb) — home "나를 위한 새 앨범" strip (release-feed `album_id`/`cover_url`, ws #677 + backend #128 + front #301) + owner Spotify followed-artists import (`user-follow-read` re-auth; owner-gated `POST /api/me/tracked-artists/spotify-import` → worker snapshot-import + OQ1 catalog-ingest fan-out + delayed 900s re-import; ws #682 + worker #76 + backend #129 + front #304). **Both steps shipped + prod-smoked 2026-07-21** (live 6-follow import: 30→33 tracked across all three paths). 본문 → `docs/archive/done/rfcs/FEAT-for-you-releases.md`.
- **FEAT-personal-release-tracking** (done 2026-07-18, **archived** — breadcrumb) — personal release feed (tracked artists + Buckit import, `/radar`) on #548's `artist_release_events`. **Steps 1–5 shipped + prod-smoked 2026-07-17→18** (post-merge hardening `FIX-personal-release-tracking-postmerge-guards` shipped + prod-smoked 2026-07-20). Observation gate **CLOSED 2026-08-03** — H1 re-measured over 3 weeks of poller data, verdict unchanged (thin-but-usable, not first-class); plan.md row. 본문 → `docs/archive/done/rfcs/FEAT-personal-release-tracking.md`.
- **FEAT-ai-editorial-critique** (draft — deferred 2026-07-20) — AI editorial critic **Phase 0** thin slice: `POST /api/editorial/critique` running the critique method over a draft + its `post_albums`-linked facts → grounded Korean feedback, reconstruction/feedback only. UI-less, golden-draft eval gated. Resume order in plan.md (promote → fold in the 2-stage pipeline + method §3.5 → re-audit the stale "Current state" → Step 1). → `FEAT-ai-editorial-critique.md`.
- **FEAT-lyrics-annotations** (**accepted 2026-07-26** — Thread 1 cleared to build; Thread 2 still waits on the filter-shape decision, §8) — two lyrics-domain threads, fully re-measured 2026-07-25. Thread 2: the unresolved-lyrics pool **diverges** (+180/day; drain 2.25/day at a 1.54% hit rate; 96-day cycle) and recency is a 32× signal once classical is excluded. Thread 1: Genius token issued and live-tested — **credits are language-independent (7/8 KR and EN), prose is not (1/8 KR)**, and annotation anchoring measures **74.7% single-span / 94.7% placeable** over 95 lyric-bound annotations via `tools/genius_anchor.py`, clearing the in-text-layer bar (RFC §6.6). §9 lists every superseded claim. → `FEAT-lyrics-annotations.md`.
- **DATA-catalog-noise-and-lyrics-coverage** (draft — **not yet accepted**) — stop ingesting bulk classical compilation noise and make lyrics coverage converge. Four steps: search **ranking** fix (`tracks.views` is 0 on all rows — 45.9%→15.1% classical with no classifier), a single ingest choke point at `_SELECT_ELIGIBLE` (absorbs DATA-release-noise (a)), lyrics pool hygiene + recency re-order, album-scoped expedite. Search is fixed by ranking not filtering; every exclusion is reversible with a self-measuring holdout. → `DATA-catalog-noise-and-lyrics-coverage.md`.
- **FEAT-bucket-identity** (in-progress) — compatibility/migration track aligning review buckets + `들을 것` + public collections to the Pocket Buckit model. Direction A done 2026-06-16; **B done 2026-07-21** (front #303: typed-field bucket lifecycle 담음→조사 중→작성 중→완료 + listened-state ring + review↔bucket chips); C subsumed + shipped via Pocket Buckit V31; D open — awaiting owner go (+ 3 owner-pending B follow-on proposals). → `FEAT-bucket-identity.md`.
- **FEAT-blog-to-review-migration** (Step 1 done + prod-live 2026-06-14) — kept open only for the optional **Step 2** true 301 via the console-managed CloudFront Function (owner-applied; trigger = inbound `/blog` links accumulating). → `FEAT-blog-to-review-migration.md`.
- **FEAT-genre-recommendation** (frozen — review-volume gated) — the "장르 기준 추천 평론" related-review recommendation (shared sub-genre tags + genre-edge graph). 미착수. → `FEAT-genre-recommendation.md`.
- **BUG-artist-image-backfill** (done 2026-07-19, **archived** — breadcrumb) — artist NULL-image backfill: worker #74/#75 (Spotify-first enrich + `no_image` sentinel + one-shot run, `still_null` 463→0) + ws #647 weekly EventBridge sweep (applied). Weekly `still_null ≈ 0` observation gate **CLOSED 2026-08-03** — measured 0 / 5,700 artists; plan.md row dropped. 본문 → `docs/archive/done/rfcs/BUG-artist-image-backfill.md`.

Older archives (the 2026-05/06 batches — STAB series, home/reviews/writer redesigns, genre system, lyrics corpus/best-of series, pocket-buckit series, today-buckit, entity-interaction contract, spotify-library-sync, listening-history import, liked-tracks workbench, component-map/playback/lyrics research docs, ARCH-6/11/12 …) all live in `docs/archive/done/rfcs/` with monthly digests in `docs/archive/done/`.
