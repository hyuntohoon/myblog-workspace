# FIX-auth-identity-lifecycle: one account boundary for async auth and private client state

- **Status**: accepted
- **Owner**: 박지훈
- **Created**: 2026-08-30
- **Accepted**: 2026-09-02 (owner, with both open questions taking their stated defaults)
- **Plan row**: `plan.md` → FIX-auth-identity-lifecycle (Active, accepted)
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

### Acceptance re-audit (2026-09-02, against `origin/main` front `03f19ae`)

All four claims above were re-checked against the code before acceptance and all four hold:
`auth.ts:214-260` single-flights but captures nothing and its refresh `fetch` (241) carries no
signal, while `logout()` (262-275) never touches `inflightRefresh`; `bucketStore.ts:57-58` freezes
`scope`/`cacheKey` as module constants with no recomputation anywhere, and the only `storage`
listeners in the app are `ownership.ts:183` and `header.client.ts:81`; `ownership.ts:5-7` keys the
lease, bus and channel off fixed strings with no `sub`.

Two refinements the audit added, both of which shape Step 1 rather than contradict it:

1. **The same-tab logout race is narrow; the exposure is cross-tab.** `logout()` calls
   `location.assign` to the Cognito logout URL (274), a full-document navigation that kills the JS
   context — so a delayed refresh can only write back during the few hundred ms before unload. The
   durable defects are (a) another tab's in-flight refresh writing tokens back into `localStorage`
   after this tab logged out, and (b) `api.ts:106` awaiting an unsignalled `refreshAccessToken()`,
   which the 15s timer at 96-99 cannot cut. **Step 1's regression tests must be shaped as cross-tab
   scenarios**, not same-tab ones; a same-tab-only test would pass against the current code.
2. **Claim 4 is not merely "fragmented" — the handoff is broken in production today.**
   `writePocketIntent` has three callers (`AddToBucketMenu.tsx:117-121`); `drainPocketIntent` has
   exactly one (`PocketResume.tsx`), and that island is mounted only on `src/pages/index.astro:97`.
   Since `callback.client.ts:39` returns to `consumeReturnTo()` rather than home, a logged-out 담기
   on `/review/[slug]` or an album page writes an intent that no consumer ever drains: the add is
   silently lost, or fires unprompted if the user happens to reach home inside the 30-minute TTL.
   Two comments (`intent.ts:5-6`, `PocketResume.tsx:2`) still assert the old
   `location.replace('/')` behaviour, which is why earlier passes read over it. Step 2 owns the fix;
   the stale comments are corrected with it.

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

Both were resolved to their stated defaults at acceptance (owner, 2026-09-02).

1. ~~Should drawer layout preferences be account-private or device preferences?~~ **Resolved:
   account-private**, because bucket ids and open positions reveal private tree structure.
2. ~~Should logout stop remote Spotify playback or only release/reset this site's controller?~~
   **Resolved: release/reset the site controller only**; logout does not issue a remote pause as a
   side effect.
