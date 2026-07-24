# REFACTOR-frontend-member-surface: test net + shared client + boundary extraction for the member surface

- **Status**: ✅ **DONE (Steps 1–4) 2026-07-24** — owner accepted 2026-07-23. Step 1 front #307 (`c084746`); Step 2 #308 (`c2b0637`); Step 3 #309 (`b6085af`); **Step 4 gate opened by owner** and shipped as 4a #310 (`a4797fa`) + 4b #311 (`2c65841`) + 4c #312 (`03d5332`). All prod-smoked 19/0. BucketBoard's DnD routing, Spotify surface, and sheet shell are each now a tested, importable unit; the component's LOC + coupling are materially reduced.
- **Owner**: TBD
- **Created**: 2026-07-23
- **Plan row**: `plan.md` → REFACTOR-frontend-member-surface
- **Source**: `docs/reviews/2026-07-23-current-state-audit.md` §C-1..C-6

---

## Goal

After this RFC, the highest-coupled frontend surface can be changed without silent regressions: a frontend **test harness exists** and covers the critical member flows (bucket create/move/DnD, publish, lifecycle derivation); every authed request goes through **one fetch client** with a timeout and cancellation; and the bucket **lifecycle rule** lives in `@lib/buckets`, callable and unit-tested, instead of inside a 2895-LOC component. The full decomposition of `BucketBoard.tsx` is explicitly **gated behind evidence** that its size is slowing delivery — this RFC de-risks that future work rather than committing to it blind.

## Non-goals

- No introduction of classes / formal OOP. The verified evidence (audit C-2, C-3) shows `bucketStore` (a functional `useSyncExternalStore` singleton) already works well; the fix is **module extraction + a shared client + a test net**, not an object model. Any step proposing a class must justify it against the functional baseline.
- No state-management library swap (no zustand/redux/jotai). `bucketStore` stays.
- No behavior change visible to users in Steps 1–3 — these are characterization-test + pure-refactor steps. A UI/UX change is out of scope.
- **No full `BucketBoard.tsx` rewrite in this RFC.** Step 4 is a necessity-gated decision point, not a committed rewrite.
- No backend/contract change. Frontend-only.

## Current state

Verified against `myblog_front` working tree (audit 2026-07-23):

- **`src/components/member/BucketBoard.tsx` — 2895 LOC**, 33 `useState` / 18 `useEffect` / 6 `useRef`, imports from ~20 modules. One component owns: server-state fetch/mutation (`@lib/buckets`), `bucketStore` subscription, lifecycle domain rule `crMeta()` (`:439-451`, with `collectItems` `:421`, `isResearchEngaged` `:435`), native HTML5 DnD + a module-level mutable `dnd` payload, 8 cross-island `window` CustomEvents (`src/lib/pocketBuckit/events.ts`), research-status policy, Spotify library sync, and view/modal/scroll-lock UI.
- **Zero tests**: no `*.test.*` / `*.spec.*`, no vitest/playwright/jest config, no `test` script in `package.json`. CI `check` = api.gen.ts diff + `astro check` + `pnpm lint` only (no behavioral gate).
- **`crMeta` is centralized** (single function, 3 occurrences all in BucketBoard) — so it is **not duplicated**, but it is trapped inside the mega-component and not importable. Field-level interpretation of the same lifecycle fields is spread across 7 files (`AddAlbumModal.tsx`, `ReviewsTab.tsx`, `ResearchNote.tsx`, `writer/ResearchDoc.tsx`, `lib/buckets.ts`, `lib/research.ts`).
- **`src/lib/api.ts` `apiFetch` (88 LOC) is not the single client**: 42 raw `fetch(` calls across ~25 files + 7 dedicated `*.api.ts` modules (`reviews/analysis/integrations/lyrics/playback/me/spotify.api.ts`) each with their own BASE/headers. Some set `Authorization: Bearer` by hand and bypass `apiFetch`'s single-flight 401→`refreshAccessToken()` retry (`spotifyPlayback.ts:306,358`). `apiFetch` has **no timeout / no AbortController** (only `safeFetch` has an 8s timeout). Cancellation exists only in `api.ts`; debounced search (`useMusicSearch.ts`) has none.
- `bucketStore.ts` (199 LOC) is a coherent central store for the bucket tree (SWR + sessionStorage, sub-scoped, fetch-sequence dedup) — the strength to build on, not replace.

## Target state

- `myblog_front` has a test runner (**vitest** + `@testing-library/react` recommended — jsdom, no browser needed for logic/render; Playwright only if a true DnD e2e is later justified) with a `pnpm test` script.
- Characterization tests exist for: `crMeta`/lifecycle derivation, bucket create/move against a mocked `bucketStore`, publish gating, and the fetch-client contract (401 refresh, timeout, abort).
- One fetch client (`apiFetch` extended, or a thin `httpClient`) that all authed calls route through, with a default timeout + `AbortSignal` support and the single-flight refresh. The 7 `*.api.ts` modules call it instead of raw `fetch`.
- `crMeta` + lifecycle helpers moved to `@lib/buckets` (or `@lib/bucketLifecycle`), imported by BucketBoard and the 7 consumer files — one definition, unit-tested.
- `BucketBoard.tsx` decomposition: **decided in Step 4**, not predetermined.

## Steps

Steps 1 → 2 → 3 are independently mergeable and behavior-preserving (protected by Step 1's tests). Step 4 is a gate.

### Step 1 — frontend test harness + characterization tests (P1, do first)

Add vitest + testing-library + jsdom, a `pnpm test` script, and a small suite that pins **current** behavior of the critical flows before any refactor (characterization, not aspirational). Wire `pnpm test` into the front PR gate (coordinates with `OPS-delivery-safety-gates` Step 2).

**Verification**:
```
cd myblog_front && pnpm test          # new suite green against current code
pnpm lint && pnpm exec astro check    # unchanged, still green
```
**Rollback**: remove the test deps + suite (additive; nothing else depends on it).

> ✅ Done 2026-07-24 — front #307 (squash `c084746`). Added vitest + @testing-library/react + jsdom (`pnpm test`), aliases mirroring tsconfig, jsdom setup (jest-dom + auto cleanup). Three characterization suites, **33 tests**: `api.test.ts` (fetch-client contract — guards Step 2, incl. the current no-timeout state asserted), `bucketStore.test.ts` (SWR fetch-once/fresh-skip/stale-refetch/force-supersedes/error/setTree/clear), `bucketLifecycle.test.ts` (crMeta/collectItems/isResearchEngaged tag derivation — guards Step 3). Added export-only to the 3 pure helpers in BucketBoard.tsx (**no relocation** — Step 3 does that). Wired `pnpm test` into the front PR `check` gate. Pinned `@types/node ^20.19` (vitest pulled node24 whose `Timer` type broke astro check on existing `setInterval` callsites — types-only). Local: 33 passed / lint clean / astro check 0 errors. Post-merge: deploy success, system prod smoke **19/0**. **"publish gating" (RFC-listed) not covered** — no pure gate helper exists (publish = WriterChrome→API callback); bucket-side publish state already covered by the lifecycle tags. Next = Step 2, rule-4 gated.

---

### Step 2 — single fetch client with timeout + cancellation (P1)

Extend `apiFetch` (or add `httpClient`) with a default timeout + `AbortSignal`, and migrate the 7 `*.api.ts` modules + hand-rolled `Bearer` callsites onto it so refresh/timeout/cancel semantics are uniform. Add a request-cancel to debounced search.

**Verification**:
```
pnpm test    # fetch-client contract tests (401→refresh once, timeout fires, abort cancels) green
# manual/CDP: search-as-you-type cancels in-flight; a stalled request times out instead of hanging
```
**Rollback**: revert per-module (each `*.api.ts` migration is independent).

> ✅ Done 2026-07-24 — front #308 (squash `c2b0637`). Extended `apiFetch` with a default 15s timeout + caller-`signal` composition (one AbortController drives the original request AND its post-refresh retry; timeout/caller-abort/transport error → null, only 401-after-refresh redirects; new `timeoutMs` on `ApiFetchOptions`; manual composition for jsdom parity). `useMusicSearch` gained a shared AbortController that cancels the prior in-flight request on a newer runDbSearch/runSpotifySync/loadMore, with `signal.aborted` catch-guards so a cancelled search no longer flashes 검색 실패. Tests: flipped Step 1's no-timeout assertion + added timeout/override/caller-abort/already-aborted + a new `useMusicSearch.test.ts` (39 passed). Local: 39 passed / lint clean / astro check 0 errors. Post-merge: deploy success, prod smoke **19/0**. **RFC premise correction (current-state audit):** the "hand-rolled Bearer callsites to migrate" (`spotifyPlayback.ts:306/:358`, `playback.api.ts readLivePlayback`) are **Spotify-API-direct** calls on a minted **streaming token** (NOT the Cognito access token) — routing them through apiFetch would break auth; `ForYouReleasesCard` bypasses apiFetch **on purpose** (passive home strip must never login-redirect, doc'd at `:14/:115`). All three correct as-is, intentionally NOT migrated. The 7 `*.api.ts` modules already route through apiFetch, so Step 2's real delta was the timeout/abort extension + search cancel. Next = Step 3, rule-4 gated.

---

### Step 3 — extract lifecycle rule to `@lib/buckets` (P1)

Move `crMeta` + `collectItems` + `isResearchEngaged` (and shared field-derivation) into `@lib/buckets`/`@lib/bucketLifecycle`; import from BucketBoard + the 7 consumers. Pure move + re-point; Step 1 tests guard it.

**Verification**:
```
pnpm test              # lifecycle-derivation unit tests green (moved, same outputs)
pnpm exec astro check  # no type breaks across the 7 consumers
```
**Rollback**: revert; the function returns to BucketBoard.

> ✅ Done 2026-07-24 — front #309 (squash `b6085af`). Moved `crMeta` + `collectItems` + `isResearchEngaged` + `TOLISTEN_KIND` (with their domain comments) out of `BucketBoard.tsx` into a new pure module `src/lib/bucketLifecycle.ts` (imports only types — `BoardAlbum`/`BoardBucket` from `./buckets`, `ResearchStatus` from `./research`; no fetch, no import cycle). BucketBoard dropped 53 net LOC and now `import { crMeta } from '@lib/bucketLifecycle'` (its only internal user is `CrStatus`; the other three symbols were used solely inside `crMeta`). `bucketLifecycle.test.ts` import re-pointed to the new module, **assertions unchanged** — Step 1's characterization suite proves the move is a no-op. **RFC premise correction (same shape as Step 2):** the "7 consumers to re-point" were files interpreting the lifecycle *fields* directly, NOT callers of `crMeta`; the only importer of these four symbols outside BucketBoard was the test, so re-pointing was one line. Local: **39 tests passed** / lint clean / astro check 0 errors (Node 20.19.5). Post-merge: deploy success, system prod smoke **19/0**. This completes the RFC's committed scope (Steps 1–3); Step 4 remains necessity-gated (OQ2) — no further work unless the gate opens.

---

### Step 4 — BucketBoard decomposition (P2, necessity-gated — DECISION, not a commitment)

**Gate:** only proceed if, after Steps 1–3, there is concrete evidence the remaining size slows delivery (e.g. repeated merge conflicts in BucketBoard, a bug traced to its coupling, or a feature blocked by it) AND the product has real-user/content signal justifying the churn. If the gate is unmet, **stop here** — Steps 1–3 already removed the sharpest risks (no test net, fragmented client, trapped rule).

If proceeding: extract seams in isolation-friendly order — (a) DnD into a dedicated module/state machine (the genuine unclear-ownership area, audit C-3), (b) Spotify-library-sync side effects, (c) view/modal shells — each behind Step 1's tests, each its own PR.

**Verification**: `pnpm test` green after each extraction; CDP clickthrough of bucket create/move/DnD at prod-realistic scale (per memory `feedback-ui-repro-realistic-data`).
**Rollback**: per-extraction revert.

> ✅ Done 2026-07-24 — owner opened the gate explicitly (the objective gate — delivery-slowdown evidence + real-user signal — was NOT met: ~1 user / 0 published reviews; proceeded on owner discretion). All three seams shipped + prod-smoked as separate PRs, each with an observe gate between:
> - **4a** front #310 (`a4797fa`) — DnD **decision logic** → `@lib/boardDnd` (`DndItem`, `DropOps`, `routeAlbumDrop`, `canAcceptAlbumDrag`, `canAcceptBucketDrag`); tree walkers `visit`/`findBucket`/`subtreeHas` + `SLIB_KIND` → `@lib/buckets`. Gesture wiring stays in the component. **+19 tests** (drop routing is headless-reproducible; only the gesture needs a browser, and it was untouched).
> - **4b** front #311 (`2c65841`) — Spotify-library surface → `useSpotifyLibrary` hook (sync state, badge map, listened-archive hint, debounced-sync poll); bucketStore refresh injected as `onSynced`. **+4 tests** (renderHook + mocked api).
> - **4c** front #312 (`03d5332`) — `ActionSheet` modal shell (+ `SheetAction`) → own file. The heavy modals (AddAlbum/AddArtist/BucketPicker/ResearchNote) were already separate components, so this was the last shell primitive; the two thin board-coupled inline dialogs (confirm-delete, research-note) were intentionally left in place. **+4 tests** (render + all close paths).
>
> Each: `pnpm test` green (final **66/66**), lint clean, astro check 0 errors; prod smoke **19/0**; prod-bundle marker grep confirmed each seam shipped (not tree-shaken). No CDP full native-drag drive — 4a/4c are byte-identical-handler / verbatim-relocation moves within one island, fully unit-covered, `member.css` untouched. **RFC fully complete (Steps 1–4).**

## Open questions

1. **Test runner choice** — vitest+testing-library (jsdom, fast, covers logic+render) vs adding Playwright for real DnD. DnD across 2 React roots + `window` events may not be faithfully reproducible in jsdom. Blocks Step 1 scope. Recommendation: vitest for Steps 1–3; defer Playwright to Step 4(a) only if DnD proves untestable in jsdom.
2. **Is Step 4 ever justified?** — Per the audit, BucketBoard size is a real but **secondary** problem; the product has 0 published reviews and ~1 real user. The gate may legitimately never open. This RFC's default outcome is Steps 1–3 done, Step 4 deferred indefinitely.
3. **Client migration blast radius** — 42 raw fetches span features beyond the member surface. Step 2 could scope to the 7 `*.api.ts` modules first and leave one-off inline fetches for later. Blocks Step 2 completeness.

## Decisions log

| Date | Decision | Step |
|------|----------|------|
| 2026-07-24 | Lifecycle rule extracted to a **new dedicated `@lib/bucketLifecycle`** module (not folded into `@lib/buckets`): matches the test filename, keeps the already-large `buckets.ts` fetch module lean, no import cycle. | 3 |
| 2026-07-24 | RFC's "7 consumers to re-point" corrected — those files read lifecycle *fields*, they don't call `crMeta`; the only external importer was the test. Committed scope (1–3) complete; Step 4 gate left closed (product still ~1 user / 0 published reviews per OQ2). | 3 |
| 2026-07-24 | **Step 4 gate opened by owner discretion** despite unmet objective criteria (~1 user / 0 reviews). Executed as 3 separate PRs with a prod-observe gate between each (rule-4 rationale preserved inside one session). Answers **OQ2**: the gate *can* open on owner call, not only on delivery-slowdown evidence. | 4 |
| 2026-07-24 | **OQ1 resolved without Playwright** — the DnD *decision logic* is headless-reproducible (unit-tested in jsdom), and the native gesture was left untouched by 4a, so no browser DnD driver was needed. Playwright still deferred indefinitely. | 4a |
| 2026-07-24 | 4c scoped to the `ActionSheet` primitive only — the heavy modals were already components; the two thin inline dialogs stay board-coupled (extraction = prop/ref churn, no real decoupling). | 4c |
