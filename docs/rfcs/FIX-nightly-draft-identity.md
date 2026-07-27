# FIX-nightly-draft-identity: give the nightly job an identity that can create drafts

- **Status**: draft (**not yet accepted**; promotion is owner-only per hard rule 5)
- **Owner**: 박지훈
- **Created**: 2026-07-27
- **Plan row**: `plan.md` → FIX-nightly-draft-delivery (P0)
- **Direction chosen by the owner 2026-07-27**: option (b), a dedicated service identity — not owner credentials, not relaxing the gate.

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
requires `sub == OWNER_SUB`. This is a regression introduced by backend `392dd50` (2026-07-08), not
an unfinished feature — delivery worked on 06-23 and 07-05.

Since ws #705 removed the hold gate, **every night with a checked memo now produces a draft**, so
this fires nightly rather than twice in history. ws #709 made it loud (non-zero exit); it did not
fix it.

## 2. Constraint that shapes the whole design

`require_owner` guards **38 routes** — editorial authoring, publish, delete, genre taxonomy, the
owner's buckets/library/playback. Widening it to accept a second `sub` would hand the automation
every one of those rights to solve a problem that needs exactly one: *create a draft*.

**So `require_owner` is not modified.** It keeps its current shape and its current 38 call sites.

Note also that `require_owner` lives **only in the backend**. `myblog_music/app/core/auth.py`
exposes `require_cognito_token` and no owner gate, so CLAUDE.md's duplicated-guard twin-sweep rule
does not apply to this change. The twin rule still applies to `require_cognito_token` itself, which
this RFC does not touch.

## 3. Design

### 3.1 A second, narrower dependency — used on one route

```python
# myblog_backend/app/core/auth.py — beside require_owner, not inside it
def require_owner_or_draft_agent(
    claims: Dict[str, Any] = Depends(require_cognito_token),
) -> Dict[str, Any]:
    """Owner, or the nightly draft agent. Fail closed exactly like require_owner:
    local/dev bypass, unset OWNER_SUB ⇒ 503, anything else ⇒ 403.
    An unset DRAFT_AGENT_SUB simply means no agent exists — it must never widen access."""
```

Accept when `sub == OWNER_SUB`, or when `DRAFT_AGENT_SUB` is **non-empty** and `sub` equals it.
An empty `DRAFT_AGENT_SUB` is not a wildcard; it degrades to owner-only.

### 3.2 The agent cannot publish, structurally

Being allowed through the door is not the same as being allowed to publish. `WritePostRequest`
carries `status`, so a bare route-level allow would let the agent create a **published** post.

In `create_post`, when the caller is not the owner, **coerce** `status` to `draft` — do not merely
validate it. Coercion means a compromised or buggy agent cannot publish even if it asks to; a
validation branch can be bypassed by any future code path that forgets to run it.

The same applies to any field that only the owner should set. `create_post` is the only route that
gets this dependency; `PUT`/`DELETE`/publish keep `require_owner` untouched.

The follow-up `PATCH /api/buckets/{id}/items/{id}` (grow-once) is also owner-gated and also fails
today. It is in scope: the same dependency, and no coercion is needed because the job only writes
`prep_tonight` and `post_id`.

### 3.3 Which identity

Two candidates. **Recommendation: a dedicated Cognito user.**

| | Dedicated Cognito user | Reuse the smoke user |
|---|---|---|
| New credential to manage | yes — one SSM entry | none, `/myblog/smoke` already exists |
| Reads correctly in an audit log | yes — "the nightly agent created this" | no — test traffic and automation share a name |
| CI smoke tests gain draft-create | no | yes, as a side effect |
| Work | create user, set password in SSM, set env | set one env var |

The smoke-user shortcut is genuinely cheaper and the coercion in §3.2 bounds it, but it conflates
two identities in the audit trail for the sake of one SSM entry. Take the dedicated user.

Machine-to-machine (Cognito `client_credentials` + resource server + custom scope) is the textbook
answer and is **rejected as disproportionate here**: it needs a new resource server, a new app
client, Terraform, and a second token-minting path in the script, to protect one route that the
coercion already pins to draft-only.

### 3.4 Wiring

- `OWNER_SUB` is set as a literal in `infra/lambda.tf:40`. `DRAFT_AGENT_SUB` follows the same shape.
- `scripts/buckit_nightly.py` `mint_smoke_token()` becomes `mint_agent_token()`, reading the agent
  password from SSM instead of `/myblog/smoke`. Same USER_AUTH flow, same never-log discipline.

## 4. Steps

| ID | What | Where |
|---|---|---|
| **S1** | Create the Cognito user; password → SSM; record the `sub` | AWS console/CLI + SSM (owner or Claude with owner creds) |
| **S2** | `DRAFT_AGENT_SUB` setting + `require_owner_or_draft_agent` + coercion in `create_post` + the bucket-item PATCH; unit tests incl. **empty-setting-must-not-widen** and **agent-cannot-publish** | `myblog_backend` |
| **S3** | `DRAFT_AGENT_SUB` env on the backend Lambda; full `terraform plan`, stop on unexpected drift (hard rule 6) | `infra` |
| **S4** | Point the nightly job at the agent identity | `scripts/buckit_nightly.py` |
| **S5** | Verify on a real 03:00 cycle: a draft reaches `/write` 임시 저장함, exit code 0 | prod |

S2 and S3 must land before S4, or the job breaks in a new way. S1 gates everything.

## 5. Verification that this actually closed

Not "the code merged". The log line to look for on the next cycle:

```
INFO draft delivery: 1 draft(s) created, 1 memo(s) grown, 0 skipped/failed, 0 DENIED
```

and a non-zero exit **absent**. Until that appears, the P0 stays open.

## 6. Open questions

- **OQ1** — Does the agent need `PATCH /api/buckets/...` from day one? Without it the memo is never
  marked grown, so the same album re-drafts every night. The album-unique slug makes the second POST
  409, so it degrades safely, but it wastes a run nightly. §3.2 includes it; confirm.
- **OQ2** — Should the drafts show a distinct author in `/write` so owner-written and agent-written
  drafts are separable at a glance? Currently provenance rides as an HTML comment in `body_mdx`.
- **OQ3** — Does anything else authenticate as the smoke user and quietly depend on it *not* having
  these rights? A grep of the deploy workflows before S4 would settle it.
