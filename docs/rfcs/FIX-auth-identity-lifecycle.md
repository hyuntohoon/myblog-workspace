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

**Shipped 2026-09-02** — front #439 (`e8eb156`, deploy 33574285362, prod smoke 19/0).
`src/lib/authIdentity.ts` is the lifecycle source; `auth.ts` gates the callback and refresh
commits on the captured epoch and `logout()` invalidates before it clears; `apiFetch` awaits the
401 refresh under its own deadline and no longer treats a missed deadline as a dead session;
`bucketStore` rescopes and drops account A's in-flight read; the Pocket provider closes private UI,
account-scopes `pb:drawers:<sub>` and loads the new account's tree; playback ownership stamps and
filters bus envelopes by account and releases the lease at the boundary; the playback session
resets and clears the reconnect hint. Two things are worth carrying forward: a real two-tab
clickthrough found the tray sitting empty for the new account — every unit test asserted the
clearing half and was happy — and a mutation proved the `typeof message.acct` check in
`isOwnershipMessage` is a type-level guard, not the second filter its comment claimed.

### Step 2 — general post-login intent

Replace the Pocket-only blob with a tagged `PostLoginIntent` store and a layout-mounted consumer.
Ship `bucket-add` and `rate-album` first. `rate-album` reopens the same album's rating editor;
`bucket-add` reopens the existing picker. Corrupt, expired, duplicate and unsupported intents drop
without replay. Spotify candidate/sync may join only when its explicit public UI is implemented.

**Shipped 2026-09-02** — front #440 (`3685350`, deploy 33577690006, prod smoke 19/0).
`src/lib/postLoginIntent.ts` is the tagged store and `components/auth/PostLoginResume`, mounted in
`layout.astro`, is its single consumer, so the resume happens wherever the callback lands instead of
only on home. `bucket-add` reopens the picker; `rate-album` reopens the album overlay with its rating
editor, and the CTA parks an intent at all for the first time. Three gates drop rather than replay:
TTL, tag, and the account boundary — an intent records `getAuthIdentity()` at capture, and a capture
naming a real account resumes only for that account, which matters because `isLoggedIn()` goes false
the moment the access token expires while A's `id_token` is still in storage.

Four things are worth carrying into Step 3. A latch (`openAlbumLatched`) was needed because the
overlay and the resume are sibling `client:only` islands whose mount effects are unordered, so a
plain dispatch could land before the overlay had a listener and take the drained intent with it. The
rating auto-open waits for the member's current 평가 to load, or it would seed the 4-star default
over a rating they already have. The new store deliberately has **no** `bucketId`: the predecessor
carried one that nothing ever read, and `security-review` is what surfaced it. And a mutation
corrected a claim rather than a test — the module-scope drain cache does not protect against
StrictMode (React discards the second render pass), it protects against a remount; the comment said
StrictMode only because the predecessor's did.

The prod clickthrough is deliberately partial and Step 3 owns the rest: the capture half was
verified on production (the real CTA parks the intent, and a logged-out load leaves it parked), but
the resume completing under a genuine session was verified against the same build on a LAN-bound dev
server, because any placeholder token trips a 401 redirect first and a real login would have put the
smoke password through the session transcript.

### Step 3 — browser validation and residual cleanup

Real-browser test cross-tab logout/account switch, delayed refresh, both login-resume actions and
playback ownership reset. Remove the archived Pocket-only assumptions/comments after production
verification; keep `FEAT-multi-user-accounts`' owner-only launch gates in Later.

**Shipped 2026-09-02** — front #441 (`4280155`, deploy 33614309445, prod smoke 30/0), plus this
record. The blocker Step 2 handed forward is gone: a full authenticated client flow **is** observable on production. Driving Chrome
over CDP from a local Node script rather than through a tool call means the smoke password and the
minted tokens are read from disk by the driver and typed into the hosted UI directly, so neither
ever passes through a transcript — which is what made "a real Cognito login leaks the password" a
false constraint rather than a real one. Every scenario below ran against the deployed bundle as
`test@ratemymusic.blog`, and nothing was written to production (no rating saved, no bucket add
completed).

**The clickthrough found a defect, which is the second session running where a fully green suite
did.** `PostLoginResume` is layout-mounted, so it runs in every open tab and re-attempts its drain
on every account change, while the intent lives in `localStorage`, which all tabs share. Signing in
was a race the visitor's own tab lost. With the tab count as the only variable, on
`/search?q=radiohead`:

| other tabs open | the tab that signed in | the other tab |
|---|---|---|
| 0 | «Radiohead» 담기 picker | — |
| 1 (sitting on `/canon/`) | nothing at all | «Radiohead» 담기 picker |

A probe injected before any page script showed the intent key already gone at the landing
document's start — consumed ~250 ms earlier, while `/admin/callback` was still running. Front #441
gives a record an owning tab (`sessionStorage`, which is per-tab and survives the hosted-UI round
trip — re-checked on the deployed bundle rather than assumed). The tab id is a delivery address,
not a permission: the account gate still runs after it, and must stay the thing that keeps A's
parked add out of B's bucket. Re-running the same experiment against the deployed fix, in a fresh
browser profile, inverts the second row — the picker lands in the tab that signed in and the other
tab shows nothing — while the first row is unchanged.

What passed, with the control that shows each assertion could have failed:

- **`bucket-add` resume**, real sign-in, non-home route: picker reopens on the page the visitor
  left. **`rate-album` resume**: the album overlay reopens with its rating editor seeded from the
  intent — so Step 2's `openAlbumLatched` is confirmed to work in real island hydration order,
  which was the open question it left.
- **Cross-tab logout**: tab 2, on another route with the tray open and a drawer expanded over
  account A's 13-item queue, went fully empty — tray cleared, the open drawer closed,
  `pb:drawers:<A>` removed, `pb:cache:buckets:<A>` pruned. No A state survived.
- **Account switch A→B**, driven from a genuine second tab so the `storage` event is real: drawers
  closed, cache rescoped `<A>`→`<B>`, and the tray **refetched and repainted** — the Step 1 defect
  (tray empty for the life of the tab) stays fixed. B's `id_token` is fabricated, so the server
  still answered with A's rows; what is under test is the rescope/refetch mechanism, not the data.
- **Delayed refresh**: the real Cognito 200 was held at the response stage and released after
  another tab logged out. Held-and-released with no logout, the token **is** written back (control);
  with the logout, it is not, and the tab correctly reports the session gone. A signed-out session
  cannot be resurrected by an in-flight refresh.
- **Playback bus account filter**: the same `state` message, sent from another tab, stamped with
  the current account repaints now-playing (`— — —` → `Come Back to Earth`); stamped with a
  different account it is dropped. Step 1 flagged this check as possibly only a type-level guard —
  it is a real one.

**Not verifiable on production, and why.** The playback *lease* release could not be exercised:
`GET /api/playback/spotify-token` answers 404 for this account because it has no connected Spotify
integration, which is the route's designed dormant response, so the transport never initialises and
`ensureOwner()` is never reached. The lease half of the account boundary therefore rests on Step 1's
tests and the bus result above. It becomes observable the first time a test account connects Spotify.

**Residual cleanup was smaller than this RFC's own text implied**, because Step 2 already did the
source half. The one live doc left was `docs/frontend/component-map.md`, which still listed
`PocketResume` as a home island; it now describes the layout-mounted `PostLoginResume` and why the
mounting point is what forced the owning-tab rule. The four `pb:resume` mentions still in `src` are
deliberate — a one-deploy legacy migration key and the comments explaining the change — and the
archived RFCs under `docs/archive/` are historical records, not stale claims.

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
