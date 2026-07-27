# FIX-nightly-draft-identity: give the nightly job an identity that can create drafts

- **Status**: **Phase A done — shipped and live-verified 2026-07-27** (promoted draft → accepted →
  in-progress → done same day on explicit owner approval; hard rule 5 satisfied). The RFC stays in
  `docs/rfcs/` **dormant** because Phase B (§4) is planned and trigger-gated, not abandoned.
  Amendments + the verification record in §6; completion digest in `docs/archive/done/2026-07.md`.
- **Owner**: the owner
- **Created**: 2026-07-27
- **Plan row**: `plan.md` → FIX-nightly-draft-delivery (P0)
- **Owner decisions 2026-07-27**: option (b), a dedicated service identity — not the owner's own
  login, not relaxing the gate. And: **fix narrowly now, widen to multi-user later, but write the
  widening plan today.** Phase B below is that plan.

## 1. The problem, as of this morning

The nightly job generates a review draft and cannot deliver it. Verified on the 03:00 run of
2026-07-27:

```
03:04:31 INFO  done in 262.9s — 2 file(s) in docs/buckit/2026-07-27
03:04:32 ERROR draft REJECTED PERMANENTLY (album 782b7ade…, status 403): {'detail': 'Owner only'}
03:04:32 ERROR EXITING NON-ZERO: 1 draft(s) were generated tonight and permanently rejected
```

`scripts/buckit_nightly.py` authenticates as the **smoke user** (`mint_smoke_token`), and
`POST /api/posts` is gated by `require_owner` (`myblog_backend/app/api/routes/posts.py:64`), which
requires `sub == OWNER_SUB`. This is a regression from backend `392dd50` (2026-07-08), not an
unfinished feature — delivery worked on 06-23 and 07-05.

Since ws #705 removed the hold gate, **every night with a checked memo now produces a draft**, so
this fires nightly rather than twice in history. ws #709 made it loud; it did not fix it.

## 2. The bigger problem the identity question exposed

The system is multi-user by intent — the owner deliberately did not lock this feature to one
person. Measured against that intent, the pipeline is **half-converted**:

| | user-aware? | evidence |
|---|---|---|
| Buckets and memos (the input) | **yes** | `review_buckets.user_id` |
| Posts (the output) | **no** | `posts` has no user/author/owner column at all |
| The nightly job in between | **no** | `CHECKED_SQL` never mentions `user_id` |

`CHECKED_SQL` selects every `prep_tonight` item in every bucket regardless of who owns it. So the
moment a second person checks a memo, **their memo becomes a post on the owner's blog.** Nothing in
the current code prevents this; it is dormant only because one person uses buckets.

It is closer than it looks. `users` already holds **4 rows** and Cognito self-signup is enabled.
Only bucket usage is single-person, and that is a habit, not a constraint.

Useful for both phases: **`review_buckets.user_id` stores the Cognito `sub` directly** — the
owner's bucket rows carry `0468fd3c-2011-70f5-0681-b852ddaade41`, identical to `OWNER_SUB` in
`infra/lambda.tf:40`. No join or mapping table is needed to scope by user.

## 3. Phase A — narrow fix, now

Goal: drafts reach the blog, and the hazard in §2 is **made unreachable rather than merely
documented**.

### A-1. `require_owner` is not modified

It guards **38 routes** — authoring, publish, delete, genre taxonomy, the owner's
buckets/library/playback. Widening it to accept a second `sub` would grant the automation every one
of them to solve a problem that needs exactly one: create a draft. It keeps its current shape and
its 38 call sites.

`require_owner` lives **only in the backend**; `myblog_music/app/core/auth.py` has
`require_cognito_token` and no owner gate, so CLAUDE.md's duplicated-guard twin sweep does not
apply here. Recorded so a later reader does not think it was skipped.

### A-2. A second, narrower dependency on one route

```python
# beside require_owner, not inside it
def require_owner_or_draft_agent(claims = Depends(require_cognito_token)) -> Dict[str, Any]:
    """Owner, or the nightly draft agent. Fail closed exactly like require_owner:
    local/dev bypass, unset OWNER_SUB => 503, anything else => 403.
    An unset DRAFT_AGENT_SUB means no agent exists — it must never widen access."""
```

Used on `create_post` and on the dedicated grow-once `POST /api/buckets/nightly-grow`. Nothing
else. *(Amended 2026-07-27 — the original text named the item PATCH; that assumption was wrong,
see §6-1.)*

### A-3. The agent cannot publish, structurally

`WritePostRequest` carries `status`, so a route-level allow alone would let the agent create a
**published** post. In `create_post`, when the caller is not the owner, **coerce** `status` to
`draft` — do not merely validate. A validation branch can be bypassed by any future path that
forgets to run it; a coercion cannot.

### A-4. Scope the job to the owner's own buckets — the part that makes Phase A safe

Add to `CHECKED_SQL`:

```sql
AND b.user_id = <OWNER_SUB>
```

This is the difference between deferring the hazard and removing it. Without it, Phase A ships an
agent that can write posts *and* a query that will hand it other people's memos. With it, a second
user's checked memo is simply not selected, and the failure mode becomes "their memo is ignored" —
visible, harmless, and exactly the signal that Phase B is due.

The job must also **log and count** any `prep_tonight` item skipped for belonging to someone else.
A silently ignored memo is how this class of bug hides; a counted one is a trigger.

### A-5. Identity

A **dedicated Cognito user**, over reusing the smoke user. The shortcut is cheaper and A-3 bounds
it, but it merges test traffic and automation in the audit trail to save one SSM entry.

Cognito machine-to-machine (`client_credentials` + resource server + custom scope) is the textbook
answer and is **rejected as disproportionate**: a new resource server, app client, Terraform, and a
second token-minting path, to protect one route the coercion already pins to draft-only.

### A-6. Steps

| ID | What | Where |
|---|---|---|
| **A-S1** | Create the Cognito user; password to SSM; record its `sub` | AWS + SSM |
| **A-S2** | `DRAFT_AGENT_SUB` setting, `require_owner_or_draft_agent`, the `status` coercion; tests incl. **empty-setting-must-not-widen** and **agent-cannot-publish** | `myblog_backend` |
| **A-S3** | `DRAFT_AGENT_SUB` env on the backend Lambda; full `terraform plan`, stop on unexpected drift (hard rule 6) | `infra` |
| **A-S4** | Owner-scope `CHECKED_SQL` + skip counter; point the job at the agent identity | `scripts/buckit_nightly.py` |
| **A-S5** | Verify on a real 03:00 cycle | prod |

A-S2 and A-S3 land before A-S4, or the job breaks in a new way. A-S1 gates everything.

### A-7. Done means a log line, not a merge

```
INFO draft delivery: 1 draft(s) created, 1 memo(s) grown, 0 skipped/failed, 0 DENIED
```

with no non-zero exit. Until that appears, the P0 stays open. *(Note: `grown` counts item rows —
an album checked in two of the owner's buckets grows 2. Delivery failures now exit non-zero:
2 = identity rejected, 3 = mint/infrastructure, 4 = draft created but memo still checked; §6-3.)*

## 4. Phase B — multi-user, planned now, built when triggered

### B-1. The trigger, stated so it cannot be argued about

Phase B becomes due when **any** of these is true:

1. A `review_buckets` row exists with a `user_id` other than `OWNER_SUB`.
2. The A-4 skip counter logs a non-zero value on any night.
3. The owner decides to offer nightly drafts as a member feature.

(1) and (2) are mechanically checkable. (2) will fire first in practice, which is why A-4 counts
instead of silently filtering.

### B-2. What Phase B has to build

- **`posts` gains an owner column.** This is the real work and the reason Phase B is not Phase A: a
  migration in `myblog_shared_db`, backfilled to `OWNER_SUB` for existing rows, then threaded
  through `PostService`, the write routes, and `/write`. Follow the established column-add rollout
  order (migration → prod apply → service pin → contract → frontend).
- **The agent acts on behalf of a user, never as one.** It must not become "an account that can
  write anyone's posts". The narrow shape: the agent may create a draft **for user X only when the
  source memo sits in a bucket owned by X**, and the server derives that owner **from the bucket,
  never from the request body**. Otherwise the agent's identity becomes an impersonation primitive.
- **Read-side scoping.** `/write` and the drafts inbox filter by owner, so members see their own
  drafts and not each other's.
- **Publishing stays out of scope.** Whether a member's review appears on the blog is a product
  decision, not an auth one. Phase B ends at "the draft lands in the right person's inbox".

### B-3. What Phase A deliberately does not prejudge

Phase A adds no column, no impersonation path, and no member-visible behaviour. `DRAFT_AGENT_SUB`
and the coercion survive into Phase B unchanged; only A-4's owner filter is replaced by
per-bucket owner derivation. Nothing built in Phase A has to be undone.

## 5. Open questions

- **OQ1** — Phase A skips non-owner memos. Should it also *uncheck* them so the member gets a
  signal, or leave them checked so Phase B picks them up later? Leaving them checked is proposed.
- **OQ2** — Should agent-written drafts be visually separable in `/write`? Provenance currently
  rides as an HTML comment in `body_mdx`.
- **OQ3** — Does anything else authenticate as the smoke user and quietly depend on it *not* having
  draft-create rights? A grep of the deploy workflows settles it before A-S4.
  **Answered 2026-07-27: the opposite is asserted.** `scripts/smoke.py` prod mode *requires* the
  smoke user to get **403** on `POST /api/posts` (`_run_member_gate` — the member-gate probe).
  Nothing depends on the smoke user having draft rights, and because the agent is a separate
  account, #133 kept that assertion true. Reusing the smoke user (the A-5 shortcut) would have
  broken the prod smoke — one more reason the dedicated identity was right.

## 6. Amendments — 2026-07-27 (post-acceptance, same day)

Everything below shipped the same day the RFC was accepted; recorded here so the body above
stays readable as the original design.

1. **A-2's PATCH assumption was wrong.** `PATCH /api/buckets/{id}/items/{id}` is not owner-gated —
   it resolves the acting user from the verified JWT `sub` (`provisioned_member_id`), so the agent
   404s (owns no buckets). Forcing it open would require an impersonation primitive. Backend #133
   recorded this and shipped `require_owner_or_draft_agent` on `create_post` only; grow-once was
   left deliberately inert (ws #716).
2. **Grow-once shipped as a dedicated narrow endpoint** instead: `POST /api/buckets/nightly-grow
   {album_id, post_id}` (backend #134, route ws #717). The server stamps `post_id` + clears
   `prep_tonight` on the OWNER's checked items for the album; the acting user is pinned to
   `OWNER_SUB` from settings — never the request body — so Phase B only swaps that pin for
   bucket-derived ownership. Post must exist and be a draft; existing `post_id` never overwritten;
   idempotent (repeat call → `grown=0`).
3. **Hardening beyond the original scope** (backend #134 + the script cutover):
   - `create_post` coercion widened: a non-owner caller's editorial fields (`album_ids` →
     `post_albums`, `artist_ids`, `tags`, `genre_ids`, `rating`, `album_classics`,
     `recommended_track_ids`, `subject_best_new` → `albums.best_new`) are dropped server-side.
     The agent's writable surface is title/body/date/section.
   - The nightly script exits non-zero on every delivery-broken state (2 = identity rejected,
     3 = token mint / delivery infrastructure, 4 = draft created but memo still checked), not
     only on 401/403 — a silent skip is how the original 403 hid for 17 days.
   - `RESEARCH_SQL` / `RECENCY_SQL` candidate subqueries mirror A-4's owner scope (they could
     not leak, but unscoped reads of foreign rows are drift waiting to happen).
4. **Operational runbook** for the agent account (rotation / kill switch / repoint / exit-code
   recovery) lives in `infra/README.md` → "Nightly draft agent"; the Cognito user and SSM param
   are recorded as out-of-IaC items there.
5. **A-7 satisfied — live e2e, 2026-07-27 14:58 KST.** A manual full run of the shipped script
   (launchd invokes the same file) produced the done-line verbatim and exit 0:
   `draft delivery: 1 draft(s) created, 1 memo(s) grown, 0 skipped/failed, 0 DENIED`. DB after
   (read-only check): the memo `prep_tonight=false` + `post_id` stamped, the post
   `status='draft'` (The Strokes, post `5886620f…`), zero items still checked. A-S5's residual —
   the launchd *trigger* itself — is unchanged from the weeks it has fired nightly; the next
   naturally-checked memo exercises it end to end. **The P0 is closed.**
