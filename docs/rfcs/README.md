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
| `in-progress (Step N)` | Implementation is authorized; each step's execution record distinguishes preparation, delivery and verification. | Entering `in-progress` requires explicit owner approval. Record completed/next steps without implying unresolved gates have passed. |
| `done` | All steps complete, ADR (if any) merged, file ready to archive. | Final verification and cleanup are complete; obtain explicit owner approval for any required Status promotion. |

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

Both patterns follow the workspace authorization and verification rules: once all applicable
pre-merge checks pass, push, open the PR, wait for required CI, and squash merge autonomously unless
the owner requested a PR-only stop. Deployment and production verification follow merge.
Unresolved owner decisions and RFC Status promotions still require explicit owner input.

Workspace instructions enforce one step per session unless their stated exceptions apply.

## Updating the RFC during execution

When a step completes:

1. Record the completed step and the next step separately. Do not promote RFC Status without
   explicit in-session owner approval; an unresolved gate can leave the next step pending.
2. Add a one-liner under the completed step: `> ✅ Done <date>, SHA: <merge sha>`.
3. If a decision was made mid-step, log it in the Decisions log table.
4. Do **not** delete completed steps from the RFC — they are part of the migration's history. Only when the entire RFC is `done` does the file get archived to `docs/archive/done/rfcs/`.

## Index

Current RFCs, reconciled 2026-09-09. This index summarizes delivery and remaining gates without
changing any RFC Status. Completed RFC history lives in `../archive/done/rfcs/` and `git log`.
`../plan.md` owns current priority; check live session/checkout ownership before starting. Consult
each RFC for every gate outcome.

| RFC | Delivery and remaining work |
|---|---|
| [FEAT-lyrics-listening-experience](FEAT-lyrics-listening-experience.md) | In-progress. Step 1 complete, including live-media confirmation 2026-09-09. Owner requested continuation; Step 2 preparation proceeds, OQ6 gates implementation. Steps 3–5 pending. |
| [FEAT-youtube-playback-provider](FEAT-youtube-playback-provider.md) | In-progress. Milestone A shipped and production-verified 2026-09-06. Owner credential/quota follow-ups remain; Milestone B requires Phase 0-B GO. |
| [SEC-system-hardening](SEC-system-hardening.md) | Accepted. Service/governance changes shipped; root-key retirement and the workspace required-check decision remain. |
| [FEAT-album-review-authoring](FEAT-album-review-authoring.md) | Accepted. Steps 1, 2 and 4 shipped. AI Steps 3/5 deferred; OQ13 resumption decision remains open, including the corrected bucket-memo evidence. |
| [ARCH-entity-interaction-domain-audit](ARCH-entity-interaction-domain-audit.md) | In-progress Status retained. All steps shipped; only owner closeout remains. |
| [FEAT-multi-user-accounts](FEAT-multi-user-accounts.md) | Implementation shipped. Owner launch/verification items and conditional member-URL decision remain deferred. |
| [FEAT-bucket-identity](FEAT-bucket-identity.md) | A/B shipped, C subsumed. D audited and gated on collection/content evidence. |
| [FEAT-blog-to-review-migration](FEAT-blog-to-review-migration.md) | Step 1 shipped. Optional HTTP 301 Step 2 waits for meaningful inbound legacy links. |
| [FIX-nightly-draft-identity](FIX-nightly-draft-identity.md) | Phase A shipped. Phase B waits for the RFC's ownership/scoping triggers. |
| [FEAT-ai-editorial-critique](FEAT-ai-editorial-critique.md) | Draft and deferred. Requires owner acceptance and the documented stale-body corrections before implementation. |
| [FEAT-genre-recommendation](FEAT-genre-recommendation.md) | Frozen; requires sufficient published-review/tag volume. |

[The lyrics/Genius investigation notes](NOTES-2026-07-25-lyrics-genius-investigation.md) are evidence,
not an executable RFC. Use [TEMPLATE.md](TEMPLATE.md) for new proposals.
