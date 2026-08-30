# FIX-auth-identity-lifecycle: one account boundary for async auth and private client state

- **Status**: draft
- **Owner**: 박지훈
- **Created**: 2026-08-30
- **Plan row**: `plan.md` → FIX-auth-identity-lifecycle (Active, draft)
- **Related**: `FEAT-multi-user-accounts`, `ARCH-playback-authority-convergence`, archived
  `FEAT-pocket-buckit`

## Goal

Make an authenticated browser identity a versioned lifecycle boundary. Async work started by
account A must not commit after logout or account B becomes current; persistent private UI must
reset and rescope at the same boundary; and a login handoff must resume the user's action rather
than only its URL.

## Current state (re-audited against `origin/main`, 2026-08-30)

1. `auth.ts` single-flights refresh, but captures no auth epoch and writes refreshed access/id
   tokens unconditionally. `logout()` removes tokens without invalidating a delayed completion.
   The Cognito refresh request receives no AbortSignal, so `apiFetch` can wait past its advertised
   15-second ceiling.
2. `bucketStore.ts` computes the Cognito `sub` and session cache key once at module load. The
   layout-mounted, transition-persisted Pocket provider does not subscribe to identity changes;
   its tree, drawers, optimistic work and in-flight fetches can survive A→logout→B.
3. Playback ownership keys/channel and the playback session singleton are origin-scoped rather
   than account-scoped. The active playback-authority RFC converges transport ownership and queue
   correctness; it does not define logout/account-switch behavior.
4. Cognito callback correctly consumes a same-origin `returnTo`, but action state is fragmented.
   Pocket writes a `pb:resume` intent whose only consumer is on Home, while callback now returns to
   the source route. Rating stores no intent at all, so the album overlay/edit entry is lost.

These are client-state isolation defects, not server authorization bypasses.

## Invariants

- Every token commit is conditional on the auth generation and refresh credential captured when
  the async operation began still being current.
- Logout/account switch invalidates pending auth, private fetch and mutation completions before
  clearing or repainting state.
- `apiFetch`'s deadline covers refresh waiting as well as the original request and retry; timeout or
  caller abort never triggers a login redirect.
- Pocket cache, open drawers, optimistic work and persisted positions are scoped to the current
  Cognito `sub`; no A state may render under B.
- Playback lease, bus messages and session state cannot cross an account boundary. Transport
  correctness remains owned by `ARCH-playback-authority-convergence`.
- Post-login intents are a single TTL-bounded tagged union with one global consumer. They are
  single-drain and resume only an explicitly supported action; no feature adds a private ad-hoc key.

## Steps

### Step 1 — auth generation and account-scoped private reset

Add one auth lifecycle source that publishes the current identity/generation in the same tab and
across tabs. Gate callback/refresh token writes on the captured generation and credential, compose
refresh with the caller deadline, dynamically rescope Pocket, cancel stale Pocket work, and close
private Pocket UI on identity change. Regression tests must cover delayed refresh→logout, A→B,
hung refresh, delayed A bucket fetch and Pocket close/reset.

Playback integration in this step is limited to the account boundary: release/reset ownership and
session state and reject old-account messages. Do not absorb transport/queue work from the active
playback RFC.

### Step 2 — general post-login intent

Replace the Pocket-only blob with a tagged `PostLoginIntent` store and a layout-mounted consumer.
Ship `bucket-add` and `rate-album` first. `rate-album` reopens the same album's rating editor;
`bucket-add` reopens the existing picker. Corrupt, expired, duplicate and unsupported intents drop
without replay. Spotify candidate/sync may join only when its explicit public UI is implemented.

### Step 3 — browser validation and residual cleanup

Real-browser test cross-tab logout/account switch, delayed refresh, both login-resume actions and
playback ownership reset. Remove the archived Pocket-only assumptions/comments after production
verification; keep `FEAT-multi-user-accounts`' owner-only launch gates in Later.

## Verification

- Front: `pnpm lint`, `pnpm exec astro check`, `pnpm test`.
- Named deterministic tests for every invariant above, including reversed async completion.
- Real-browser: two tabs, account switch, Pocket drawers, active playback, logged-out Buckit add and
  rating entry through Cognito return.
- Production smoke result and browser evidence quoted in the PR comment after deploy.

## Rollback

Revert one step at a time. No server contract, database migration, Cognito configuration or stored
user data changes are required. A rollback may leave ignored namespaced browser keys, which a later
successful identity initialization prunes.

## Open questions

1. Should drawer layout preferences be account-private or device preferences? Default for Step 1:
   account-private, because bucket ids and open positions reveal private tree structure.
2. Should logout stop remote Spotify playback or only release/reset this site's controller? Default:
   release/reset the site controller; do not issue a remote pause as a side effect of logout.
