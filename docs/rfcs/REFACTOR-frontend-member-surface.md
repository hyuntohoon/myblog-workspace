# REFACTOR-frontend-member-surface: test net + shared client + boundary extraction for the member surface

- **Status**: accepted (2026-07-23 — owner accepted; Step 1 may begin. Step 4 stays necessity-gated per OQ2)
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

---

### Step 2 — single fetch client with timeout + cancellation (P1)

Extend `apiFetch` (or add `httpClient`) with a default timeout + `AbortSignal`, and migrate the 7 `*.api.ts` modules + hand-rolled `Bearer` callsites onto it so refresh/timeout/cancel semantics are uniform. Add a request-cancel to debounced search.

**Verification**:
```
pnpm test    # fetch-client contract tests (401→refresh once, timeout fires, abort cancels) green
# manual/CDP: search-as-you-type cancels in-flight; a stalled request times out instead of hanging
```
**Rollback**: revert per-module (each `*.api.ts` migration is independent).

---

### Step 3 — extract lifecycle rule to `@lib/buckets` (P1)

Move `crMeta` + `collectItems` + `isResearchEngaged` (and shared field-derivation) into `@lib/buckets`/`@lib/bucketLifecycle`; import from BucketBoard + the 7 consumers. Pure move + re-point; Step 1 tests guard it.

**Verification**:
```
pnpm test              # lifecycle-derivation unit tests green (moved, same outputs)
pnpm exec astro check  # no type breaks across the 7 consumers
```
**Rollback**: revert; the function returns to BucketBoard.

---

### Step 4 — BucketBoard decomposition (P2, necessity-gated — DECISION, not a commitment)

**Gate:** only proceed if, after Steps 1–3, there is concrete evidence the remaining size slows delivery (e.g. repeated merge conflicts in BucketBoard, a bug traced to its coupling, or a feature blocked by it) AND the product has real-user/content signal justifying the churn. If the gate is unmet, **stop here** — Steps 1–3 already removed the sharpest risks (no test net, fragmented client, trapped rule).

If proceeding: extract seams in isolation-friendly order — (a) DnD into a dedicated module/state machine (the genuine unclear-ownership area, audit C-3), (b) Spotify-library-sync side effects, (c) view/modal shells — each behind Step 1's tests, each its own PR.

**Verification**: `pnpm test` green after each extraction; CDP clickthrough of bucket create/move/DnD at prod-realistic scale (per memory `feedback-ui-repro-realistic-data`).
**Rollback**: per-extraction revert.

## Open questions

1. **Test runner choice** — vitest+testing-library (jsdom, fast, covers logic+render) vs adding Playwright for real DnD. DnD across 2 React roots + `window` events may not be faithfully reproducible in jsdom. Blocks Step 1 scope. Recommendation: vitest for Steps 1–3; defer Playwright to Step 4(a) only if DnD proves untestable in jsdom.
2. **Is Step 4 ever justified?** — Per the audit, BucketBoard size is a real but **secondary** problem; the product has 0 published reviews and ~1 real user. The gate may legitimately never open. This RFC's default outcome is Steps 1–3 done, Step 4 deferred indefinitely.
3. **Client migration blast radius** — 42 raw fetches span features beyond the member surface. Step 2 could scope to the 7 `*.api.ts` modules first and leave one-off inline fetches for later. Blocks Step 2 completeness.

## Decisions log

| Date | Decision | Step |
|------|----------|------|
| | | |
