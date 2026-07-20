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

- **FEAT-multi-user-accounts** (in-progress) — multi-user platform umbrella (Google+Kakao signup, RYM-style public reviews, per-user buckets, Last.fm/Spotify member listening). **Phases 0–4 + 3b/3c + library user-scope + 07-14 surface-audit remediation + profile-merge PR1–3 all shipped & prod-verified**; remaining = owner-only launch gates G1/G2 + deferred canonical-link decision. → `FEAT-multi-user-accounts.md` (Phase 4 engine → archived `docs/archive/done/rfcs/FEAT-multi-user-accounts-p4-llmengine.md`).
- **FEAT-multi-user-accounts-p4-llmengine** (done 2026-07-11, **archived** — breadcrumb) — `LLMEngine.run(job)` ABC unifying the 5 `claude -p` callsites (engine home = `myblog_shared_db/.../llm/`; shared_db #59, `llm_usage` prod-applied; live-site cutover 5/5). Necessity-gated residue rides with the RFC: `/myblog/anthropic` SSM provisioning at the first real ApiEngine caller; BYOK → Gate G2. 본문 → `docs/archive/done/rfcs/FEAT-multi-user-accounts-p4-llmengine.md`.
- **FEAT-member-player** (in-progress) — capability-tiered player bar rebuild of '지금 듣는 음악' (D1; D28 no-polling upheld). **Steps 1–4 shipped + prod-smoked 2026-07-19→20** (scopes/re-consent; per-member token mint, member-without-connection → 404 per #126; hairline-LCD bar + Connect remote + clock-estimate fallback, front #293; 'Listening on <device>' bottom-edge hint, front #297; Step 4 owner real-device check confirmed 2026-07-20). Next = Step 5 in-page SDK device (opt-in output) + Step 6 candidate menu (Connect control extensions) + Step 7 candidate (capability transparency: 연동 안내/설명서, backed by the RFC's user-situation capability matrix) — owner selects subsets at promotion. → `FEAT-member-player.md`.
- **RFC-ui-surface-unification** (in-progress) — dual-modal rule codified + dead-spot fixes + artist links with full id plumbing. **Steps 1–3 shipped + prod-smoked** (front #290/#292 + #296 404-fallback shell 2026-07-20). Next = Step 4 id plumbing (the one contract change, cross-repo). → `RFC-ui-surface-unification.md`.
- **FEAT-lyrics-viewer-controls** (done 2026-07-20, **archived** — breadcrumb) — scroll-suspend + return behaviors + header ⚙ popover (Steps 1+2, front #289/#295). Owner keeper pick 2026-07-20 = **D (browse) + A's circular countdown ring**; loser-removal chore front #298 shipped + prod-smoked same day. 본문 → `docs/archive/done/rfcs/FEAT-lyrics-viewer-controls.md`.
- **SEO-review-structured-data** (in-progress) — `Review` + `MusicAlbum` JSON-LD on `/review/[slug]`, build-time only. **Step 1 shipped 2026-07-19** (front #288; inert in prod until the first review publish). Remaining = Rich Results Test on the first live review URL, then close. → `SEO-review-structured-data.md`.
- **FEAT-release-calendar** (accepted — implementation complete) — public new-release surfaces (home 새 앨범 card + `/releases/` 신보 캘린더, multi-source MB+iTunes poller + day-0 confirm). **Steps 1–7 all shipped 2026-07-11→13.** Remaining trigger: OQ4 singles/noise review ~07-27 + `no_upc` sentinel re-check. → `FEAT-release-calendar.md`.
- **FEAT-personal-release-tracking** (accepted — implementation closed) — personal release feed (tracked artists + Buckit import, `/radar`) on #548's `artist_release_events`. **Steps 1–5 shipped + prod-smoked 2026-07-17→18.** Remaining trigger: H1 re-measure ~07-27 (post-merge hardening `FIX-personal-release-tracking-postmerge-guards` shipped + prod-smoked 2026-07-20). → `FEAT-personal-release-tracking.md`.
- **FEAT-ai-editorial-critique** (draft — deferred 2026-07-20) — AI editorial critic **Phase 0** thin slice: `POST /api/editorial/critique` running the critique method over a draft + its `post_albums`-linked facts → grounded Korean feedback, reconstruction/feedback only. UI-less, golden-draft eval gated. Resume order in plan.md (promote → fold in the 2-stage pipeline + method §3.5 → re-audit the stale "Current state" → Step 1). → `FEAT-ai-editorial-critique.md`.
- **FEAT-bucket-identity** (in-progress) — compatibility/migration track aligning review buckets + `들을 것` + public collections to the Pocket Buckit model. Direction A done 2026-06-16; C subsumed + shipped via Pocket Buckit V31; B next / D open — awaiting owner go. → `FEAT-bucket-identity.md`.
- **FEAT-blog-to-review-migration** (Step 1 done + prod-live 2026-06-14) — kept open only for the optional **Step 2** true 301 via the console-managed CloudFront Function (owner-applied; trigger = inbound `/blog` links accumulating). → `FEAT-blog-to-review-migration.md`.
- **FEAT-genre-recommendation** (frozen — review-volume gated) — the "장르 기준 추천 평론" related-review recommendation (shared sub-genre tags + genre-edge graph). 미착수. → `FEAT-genre-recommendation.md`.
- **BUG-artist-image-backfill** (done 2026-07-19, **archived** — breadcrumb) — artist NULL-image backfill: worker #74/#75 (Spotify-first enrich + `no_image` sentinel + one-shot run, `still_null` 463→0) + ws #647 weekly EventBridge sweep (applied). Weekly `still_null ≈ 0` observation gate tracked in plan.md Later. 본문 → `docs/archive/done/rfcs/BUG-artist-image-backfill.md`.

Older archives (the 2026-05/06 batches — STAB series, home/reviews/writer redesigns, genre system, lyrics corpus/best-of series, pocket-buckit series, today-buckit, entity-interaction contract, spotify-library-sync, listening-history import, liked-tracks workbench, component-map/playback/lyrics research docs, ARCH-6/11/12 …) all live in `docs/archive/done/rfcs/` with monthly digests in `docs/archive/done/`.
