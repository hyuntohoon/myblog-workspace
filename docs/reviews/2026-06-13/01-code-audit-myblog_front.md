# Code Audit — `myblog_front` (2026-06-13)

Astro 5 + React 19 → S3 + CloudFront. 104 source files / ~20k LOC. Read-only audit
of `src/components`, `src/lib`, `src/pages`, `src/scripts`.

## Health read

This is a **mature, well-disciplined frontend**. Lint is clean (`pnpm lint` → exit 0,
zero warnings on Node 20.19.5). TypeScript runs `astro/tsconfigs/strict`, and the
codebase has only **3 `as any`** and **2 `@ts-expect-error`/`eslint-disable`** sites
across 20k lines. The authed-fetch story is consistent (every backend mutation rides
`apiFetch` with Bearer + 401-refresh; catalog reads are deliberately unauthenticated
plain `fetch`). Error/loading/empty states on the big islands (BucketBoard,
OverviewDash, the member widgets) are genuinely good — `alive` guards, SWR-from-
localStorage first paint, non-fatal degradation, focus management in modals.

The real problems are **duplication and accumulated dead weight**, not correctness:
the album-detail response shape is hand-rolled in four places while a generated type
exists; the music-search core was extracted for the writer but the original homepage
search bar was never migrated onto it; and four heavyweight dependencies (`@toast-ui/
editor`, the three `@dnd-kit/*` packages) plus two exported-but-uncalled `api.ts`
functions are dead. There is also **zero unit/integration test infrastructure** — CI is
lint + `astro check` + openapi-sync only — which is the single biggest structural gap.

Severity-sorted findings below.

---

## Findings

### 1. No test runner or test suite at all — entire repo (H, test-gap, fix L)
**Location:** repo root (`package.json`), `.github/workflows/main.yml`

`package.json` has no `vitest`/`jest`/`playwright` dependency and no `test` script:

```
grep -in "vitest|jest|playwright|test" package.json   → (no matches)
find . -name '*.test.*' -o -name '*.spec.*'           → (none)
```

CI (`main.yml:50-54`) runs only `astro check` (typecheck) + `pnpm lint` + an
`api.gen.ts` sync diff. There is meaningful pure logic that is trivially unit-testable
and currently unguarded: `lib/reviews.ts` (`selectFeatured`, `buildReviewCards`
rating-normalization 0–10→0–5, `allGenres/allTags/allYears`), `lib/member.ts`
(`computeStats`, `bucketCount` tree walk), and `useMusicSearch.ts`'s
race-guard/dedupe/paging logic (the memory trail shows repeated CP-1/CP-4 seq-race
regressions). The project's own memory notes that lint+`astro check` "miss render/event
regressions" — yet there is no behavioral test layer to catch them either.

**Proposal:** add `vitest` + a handful of pure-function unit tests for `lib/reviews.ts`,
`lib/member.ts`, and the `useMusicSearch` mappers/race-guard; wire `pnpm test` into the
`check` job in `main.yml`. Start with the rating-normalization and `selectFeatured`
edge cases (no-BNM fallback, scale===10 halving) — highest value per line.

---

### 2. Album-detail response shape hand-rolled in 4 places; a generated type exists (H, duplication, fix M)
**Location:** `src/lib/albumDetail.ts:18-21`, `src/components/writer/CommandPalette.tsx:202-206`, `src/components/writer/WriterApp.tsx:56-60`, `src/components/writer/types.ts`

`api.gen.ts:1347` defines `Music_AlbumDetail` (the exact response of
`GET /api/music/albums/{album_id}` and `/by-spotify/{...}`, see `api.gen.ts:2450,2481`).
Yet four files independently re-declare that shape by hand:

- `albumDetail.ts:18-21` — `MusicTrack`/`MusicArtist`/`MusicAlbumOut`/`AlbumDetail`
- `CommandPalette.tsx:202` — `album: { id, title, cover_url, release_date, best_new? }` inline
- `WriterApp.tsx:56` — the identical inline shape (`best_new?: boolean` and all)
- `writer/types.ts` — a third `AlbumDetail`

And `fetchAlbumDetail` itself is implemented three separate times
(`albumDetail.ts:35`, `WriterApp.tsx:51`, plus `searchBarDb.client.ts:376/383`
`fetchAlbumDetail*`). Because these are hand-typed, a music-API field rename/addition
(e.g. the recently-shipped genre fields) won't fail the build in these consumers — the
`api.gen.ts` sync gate only protects code that actually *references* the generated type.

**Proposal:** derive a single `AlbumDetail = components['schemas']['Music_AlbumDetail']`
in `lib/albumDetail.ts`, export the one `fetchAlbumDetail` (already has caching +
inflight-dedup — the best implementation), and have CommandPalette/WriterApp import it
instead of re-fetching + re-typing. Collapses 4 type defs + 3 fetch impls into 1.

---

### 3. Music-search core extracted for the writer but homepage search bar never migrated (H, duplication, fix M)
**Location:** `src/scripts/searchBarDb.client.ts` (509 lines) vs `src/lib/useMusicSearch.ts` (379 lines)

`useMusicSearch.ts:1-13` header states it was extracted "so the album-only 평론 버킷
(AddAlbumModal) and, later, the writer's CommandPalette can share one search core
instead of hand-rolling near-identical fetch + race-guard + cooldown logic twice."
But the original homepage search bar (`searchBarDb.client.ts`) was **not** migrated and
still hand-rolls the whole thing in parallel:

| concern | `useMusicSearch.ts` | `searchBarDb.client.ts` |
|---|---|---|
| db→hit mappers | `mapAlbums/mapArtists/mapTracks` (102-142) | `mapCandArtists/mapCandAlbums/mapCandTracks` (238-279) |
| race guard | `seqRef` (204) | `_searchSeq` (334,352) |
| spotify cooldown | `SPOTIFY_COOLDOWN_MS` (57) | inline `setTimeout(...,3000)` (332) |
| dedupe | `dedupeBySpotify` (144) | — (none) |

Two divergent implementations of the same DB-first / candidates / artist→album-recall
contract. Bug fixes (the artist→album recall note, dedupe) landed in one and not the
other.

**Proposal:** migrate the homepage search bar onto `useMusicSearch` (or, since it is a
non-React `.client.ts` island, extract the shared fetch+map+race-guard helpers into a
framework-agnostic module both consume). At minimum, port `dedupeBySpotify` into the
homepage path. Document the divergence if a full merge isn't worth it.

---

### 4. Four heavyweight dependencies are unused — zero imports in `src/` (M, dependency, fix S)
**Location:** `package.json:25-27,33`

```
grep -rn "from '@dnd-kit|from '@toast-ui" src   → (no matches)
```

`@dnd-kit/core`, `@dnd-kit/sortable`, `@dnd-kit/utilities`, and `@toast-ui/editor`
are all in `dependencies` with **no real import anywhere** in `src/`. The only
`dnd-kit` string in `src` is the comment at `OverviewDash.tsx:9` ("kept pointer-based,
NOT @dnd-kit") — the board DnD is hand-rolled pointer logic, so dnd-kit was evaluated
and dropped but never uninstalled. `@toast-ui/editor` (a full WYSIWYG markdown editor)
is wholly unreferenced. These inflate `pnpm install` time, lockfile size, and audit
surface for no benefit.

**Proposal:** `pnpm remove @dnd-kit/core @dnd-kit/sortable @dnd-kit/utilities
@toast-ui/editor`; re-run `pnpm build` to confirm. Pure subtraction, no behavior change.

---

### 5. `safeFetch`, `fetchMetrics`, and `Metrics` in `api.ts` are dead exports (M, dead-code/duplication, fix S)
**Location:** `src/lib/api.ts:3-45`

Only `apiFetch` is ever imported from `api.ts`:

```
grep -rn "import.*safeFetch|import.*fetchMetrics" src   → (no matches)
```

`safeFetch<T>` (3-21), `fetchMetrics` (25-45), and `interface Metrics` (23) have zero
callers. `fetchMetrics` targets `POST /api/metrics/batch` for likes/comments — and the
project roadmap (CLAUDE.md memory: "comments/likes dropped") explicitly killed that
feature, so this is stranded code for a cancelled feature, still referencing a backend
endpoint. It also bypasses the env-schema'd accessor and reads
`import.meta.env.PUBLIC_BACKEND_API_URL` directly.

**Proposal:** delete `safeFetch`, `fetchMetrics`, and `Metrics`. If the metrics endpoint
is also dead server-side, note it for the backend audit.

---

### 6. `authFetch` in `auth.ts` is a dead, refresh-less duplicate of `apiFetch` (M, duplication, fix S)
**Location:** `src/lib/auth.ts:215-225`

```
grep -rn "authFetch" src   → only the definition; zero call sites
```

`authFetch` (auth.ts:215) is a second authed-fetch wrapper that sets a Bearer header but
**does not do the 401→refresh→retry** dance `apiFetch` does. It is unused, but its mere
existence is a trap: a future contributor could grab the wrong wrapper and silently lose
token-refresh on a mutating call. The hard rule "authed calls go through `apiFetch`"
(CLAUDE.md) is undermined by shipping a near-namesake that doesn't.

**Proposal:** delete `authFetch`. Keep `getAccessToken`/`getAuthHeader`/`refreshAccessToken`
(those are used).

---

### 7. Candidates endpoint hit with two different auth wrappers across the two search cores (M, error-handling/structure, fix S)
**Location:** `src/scripts/searchBarDb.client.ts:346` vs `src/lib/useMusicSearch.ts:275`

Same endpoint (`GET /api/music/search/candidates`), two different fetch strategies:

```
searchBarDb.client.ts:346:  const r = await fetch(url, { headers: getAuthHeader() })   // bare header, no refresh
useMusicSearch.ts:275:      const r = await apiFetch(`${MUSIC}/api/music/search/candidates?...`)  // Bearer + 401 refresh
```

The endpoint has **no `security` block** in the merged spec (`api.gen.ts:2624`,
`search_candidates_...` — no `security:` key), i.e. it's unauthenticated (DB read +
SQS enqueue). So neither call *needs* a token — which makes the divergence pure
inconsistency: one path forces a `goLogin()` redirect on a stray 401, the other doesn't,
for an endpoint that is supposed to work logged-out. Functionally low-impact today, but
it's exactly the kind of "which wrapper do I use?" ambiguity finding #6 warns about.

**Proposal:** pick one. Since candidates is unauthenticated, plain `fetch` (no auth
header at all) is the honest choice for both; or route both through the shared core
from finding #3.

---

### 8. Cognito `PUBLIC_COGNITO_*` env vars read raw, not in the typed env schema (M, type-safety, fix S)
**Location:** `src/lib/auth.ts:7-9`, `astro.config.ts:64-76`

`astro.config.ts` declares a typed `env.schema` — but only for `PUBLIC_API_URL` and
`PUBLIC_BACKEND_API_URL`. The four login-critical Cognito vars are read raw:

```
auth.ts:7  const COGNITO_DOMAIN = import.meta.env.PUBLIC_COGNITO_DOMAIN as string
auth.ts:8  const CLIENT_ID      = import.meta.env.PUBLIC_COGNITO_CLIENT_ID as string
auth.ts:9  const REDIRECT_URI   = import.meta.env.PUBLIC_COGNITO_REDIRECT_URI as string
grep "COGNITO" astro.config.ts env.d.ts → (not in schema)
```

The `as string` cast means a missing/typo'd var becomes `undefined` cast to `string`,
producing a malformed `https://undefined/oauth2/authorize` URL discovered only at
runtime when a user clicks login. The CI build *does* inject them (`main.yml:88-91`),
so a deploy with a missing var would build green and fail in prod. (auth.ts:79 does
guard one shape — domain-contains-slash — but not absence.)

**Proposal:** add `PUBLIC_COGNITO_DOMAIN/CLIENT_ID/REDIRECT_URI` (+ `USER_POOL_ID`,
which `main.yml:90` already passes) to the `env.schema` in `astro.config.ts` so a
missing var fails the build, not the user.

---

### 9. Member dashboard still ships SAMPLE genres/artists/activity to production (L, structure, fix M)
**Location:** `src/lib/member.ts:115-126`, consumed at `OverviewDash.tsx:450-453`, `StatsTab.tsx`

`member.ts` is a documented "swap seam" (FEAT-member-dashboard) — but `getGenres()`,
`getArtists()`, `getActivity()`, `getNowPlaying()`, and `getLibrary()` still return
hardcoded `member.sample.ts` data, rendered into real-looking donut/bar charts on
`/profile`'s 개요 dash (`OverviewDash.tsx:450 case 'genre'`, `:451 case 'artists'`,
`:453 case 'activity'`) and StatsTab. A "샘플" badge mitigates this, but the genre chart
in particular now contradicts the **real** genre system that shipped to prod
(FEAT-genre-system Steps 0–4) — the profile shows fake genres while `/reviews` shows
real ones. This is expected per the RFC's incremental plan, so it's a tracked-debt note,
not a defect.

**Proposal:** (tracked debt) when the genre-distribution API lands
(FEAT-genre-artist-distribution is in draft), swap `getGenres/getArtists` to real
`apiFetch` calls — the seam is designed for exactly this. Flag here so it isn't
forgotten as "looks done."

---

### 10. `clone = JSON.parse(JSON.stringify(...))` on every bucket-tree mutation (L, performance, fix S)
**Location:** `src/components/member/BucketBoard.tsx:89`, called at 1219,1240,1262,1291,1321,1354,1367,1377,1394,1406…

```
const clone = (t: BoardBucket[]): BoardBucket[] => JSON.parse(JSON.stringify(t))
```

Every crate add/move/remove/reorder deep-serializes the entire bucket tree via
JSON round-trip (10+ call sites). For a one-person blog's bucket counts this is
negligible (sub-millisecond), but JSON-clone also silently drops any non-JSON values
and is O(n) on the whole tree per keystroke-ish interaction. Listed as a
correctness/perf footgun, not an active problem.

**Proposal:** use `structuredClone()` (available in all supported runtimes, Node 20 +
modern browsers) — same semantics, faster, and preserves more types. One-line change.

---

### 11. `api.ts` `safeFetch` has an 8s AbortController but the authed `apiFetch` has none (L, error-handling, fix S)
**Location:** `src/lib/api.ts:65-88` vs `:7-8`

`safeFetch` wraps an 8s `AbortController` timeout (api.ts:7-8), but the actually-used
`apiFetch` (65) has **no timeout** — a hung backend request (Lambda cold-start + Neon
cold-start can stack) leaves the promise pending indefinitely, and the calling island
sits in its loading skeleton forever with no error path. Several consumers
(`spotify.api.ts`, `buckets.ts`, `research.ts`) rely on `apiFetch` rejecting/returning
to flip out of `loading`. Low severity because cold-start hangs are rare and the user
can reload, but it's an asymmetry: the dead helper has the safety net, the live one
doesn't.

**Proposal:** add an `AbortController` timeout (~10–15s, above the documented ~1s edge
miss + cold-start budget) to `apiFetch`, mirroring `safeFetch`. Return `null` on abort
so existing `!res` branches already handle it.

---

## Biggest wins for this repo

1. **Add a `vitest` unit layer** for `lib/reviews.ts` + `lib/member.ts` + the
   `useMusicSearch` race-guard (finding #1) — the one structural gap; everything else is
   cleanup. Highest ROI: the rating-normalization and seq-race logic have a documented
   regression history.
2. **Collapse the 4 album-detail type defs + 3 fetch impls onto the generated
   `Music_AlbumDetail`** (finding #2) — restores the api.gen.ts contract-drift safety net
   on the writer's pick path.
3. **`pnpm remove` 4 dead deps + delete 3 dead `api.ts`/`auth.ts` exports**
   (findings #4, #5, #6) — pure subtraction, ~zero risk, shrinks install + audit surface
   and removes the "wrong fetch wrapper" trap.
4. **Migrate the homepage search bar onto the shared search core** (finding #3) — finishes
   a refactor that was started but left half-done, ending the two-implementations drift.

## What's genuinely clean (don't "fix")

- **Authed-fetch discipline:** every backend mutation rides `apiFetch` (Bearer + 401
  refresh); catalog reads are deliberately plain `fetch`. The boundary is correct.
- **Error/loading/empty states:** BucketBoard + OverviewDash widgets use `alive` guards,
  SWR-from-localStorage first paint, and non-fatal degradation. Mature.
- **Type safety:** `astro/tsconfigs/strict`, only 3 `as any` in 20k LOC, generated types
  used throughout the member/research/buckets API layers.
- **a11y:** focus management + ESC + focus-restore in modals (`drafts.astro:324-363`),
  `aria-busy` skeletons, real `<button type="button">` (no div-onClick) on islands.
- **No N+1 / no sync external calls on request paths:** `/` and `/reviews` render from
  server-built `buildReviewCards(getCollection('blog'))` props; `rule #9` (no sync
  Spotify) is respected — all Spotify data comes from worker-fed cache GETs.
- **Lint clean:** `pnpm lint` → exit 0, zero warnings (Node 20.19.5).
