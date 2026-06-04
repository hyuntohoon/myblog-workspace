# FEAT-multi-user-accounts

**Status**: draft

User / profile model, public `/members/[handle]`, followers / following / lists.
Un-hides the social stats currently hidden on `/profile`. Carved out of
`FEAT-member-dashboard` (was its "Step 6", always flagged "large, separate; may graduate
to its own RFC"; closed/archived at `docs/archive/done/rfcs/FEAT-member-dashboard.md`).

## Scope

- First-class user / profile model — today the dashboard is single-admin at `/profile`.
- Public member pages at `/members/[handle]`.
- Social graph: followers / following / curated lists.
- Un-hide the follower / following / list stats that Step 1 deliberately hid.

## Origin decisions (from FEAT-member-dashboard)

- `Route = /profile`; multi-user public profiles → `/members/[handle]` later (Step 1/6).
- Hide follower / following / list stats in Step 1 (social = multi-user) (Step 1/6).

## Status

Not yet scoped beyond this carve — the largest member-dashboard follow-on. Needs its own
data model (users, follows, lists), an auth model (multi-user vs the current single-admin
Cognito posture), and a migration plan before promotion to `accepted`.
