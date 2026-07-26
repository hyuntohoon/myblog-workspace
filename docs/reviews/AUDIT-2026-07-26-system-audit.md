# System Audit — 2026-07-26 (code / architecture / UI-UX / functional)

**Branch**: `docs/system-audit-2026-07-26` (workspace only; docs-only, no code changes)
**Owner decisions (2026-07-26 02:4x KST, before owner went to sleep)**:

1. **Docs only** — no code/infra changes, no PRs. Findings are written up; fixes are a separate decision after owner reads this.
2. **Necessity gate** — a finding is adopted only if concrete harm-if-unfixed can be demonstrated. Taste/style/hypothetical items are dropped. "Nothing to fix in axis X" is a valid result.
3. **UI/UX = real browser + code** — CDP against production, read-only navigation. No write actions.
4. **Usage limit is expected to interrupt.** This file is the resume ledger. A cron trigger re-enters and continues from the checklist below.

---

## RESUME STATE (read this first on any re-entry)

**How to resume**: `git -C /Users/park_hyun/myblog-workspace checkout docs/system-audit-2026-07-26`, read this file,
find the first row in the checklist that is not `DONE`, and continue from there. Do not restart finished rows.

| # | Leg | Status | Evidence lands in |
|---|-----|--------|-------------------|
| A | Backend/music/worker code audit (recurring bug classes: fail-closed guards, session lifecycle, upsert sort, HTTP timeouts, twin drift) | **DONE** — 5 findings, 4 classes swept clean. Full detail in `audit-2026-07-26-raw/A-python-services.md` | §1 |
| B | Architecture audit (service boundaries, sync-Spotify rule, contract/OpenAPI drift, shared_db pin drift, infra↔code drift) | **DONE** — 0 findings; all six structural checks clean. Redone from scratch in the main loop | §2 |
| C | Frontend code audit (islands, CSS scoping traps, api.gen.ts drift, auth/token handling, error/empty states) | **DONE** — 0 new findings (frontend defects are E-1/E-3/E-4, found live). Done from scratch in the main loop | §3 |
| D | Functional audit (plan.md open items vs reality, launchd pipeline health, DLQ/queue state, prod smoke) | **DONE** — 3 findings (one P0), rest verified healthy. Done in the main loop after the subagent died | §4 |
| E | UI/UX live verification via CDP on production (desktop + mobile emulation, console errors, key flows) | **DONE** for the logged-out public surface (home / reviews / genres / canon / collection / artist, 1440px + 390×844×3 mobile, Lighthouse, CLS attribution). **Authed `/members/` surface NOT covered** — optional deepening | §5 |
| F | Necessity-gate pass — refute every candidate finding, drop unproven ones | **DONE** — D-1 and A-2 adversarially verified; 8 candidates dropped with reasons recorded | §6 |
| G | Final write-up + plan.md candidate rows + owner feedback questions | **DONE** — 12 findings, 7 owner questions. plan.md rows deliberately NOT added (owner decides scope first) | §6, §7 |

| H | **Deepening pass** — adversarially refute recorded findings + sweep the not-covered areas (fired by the 5 h resume trigger, ~09:20 KST) | **DONE** — 6 findings upgraded to production-verified, 0 overturned, 1 new (E-5); authed surface swept | §6b |

| I | **Re-review** — 5 parallel verifier agents attack this report and its 12 commits; owner-requested (~10:30 KST) | **DONE** — 14 claims corrected, 5 new findings (PUB-1 / OPS-1 / SEC-1 / SEC-2 / E-6), DEP-2's applicability overturned. The judge + synthesis stages died on the session cap, so **every correction was re-verified by hand in the main loop** | §9 |

**AUDIT COMPLETE — main run + deepening pass + re-review.** Nothing is left to resume. If another trigger fires, **stop and do nothing.**

⚠️ **Before anything is merged, read §9.2 PUB-1**: these repos are public, and this document contains reproduction detail for defects that are still unfixed.

Remaining uncovered surfaces are enumerated in **§9.4** (which supersedes the shorter list in §6b): `infra/` beyond apigateway/eventbridge/lambda/monitoring, all six CI workflow files, `tools/` and the non-buckit `scripts/`, frontend server-side code, PWA/SW config, escaping of member-supplied content, plus load testing, DB data quality, Terraform state, and Python CVE call-path tracing.

**Raw agent output / intermediate notes**: `docs/reviews/audit-2026-07-26-raw/`

**Traps hit during this run — read before resuming:**

- **The workspace branch got silently reset to `docs/album-research-v4-evidence` mid-session** (once, ~02:55). Re-check `git branch --show-current` before every write and every commit, and `git checkout docs/system-audit-2026-07-26` if it drifted.
- **Bare `git commit` gets denied by the rule-#1 hook** once the session cwd wanders out of the workspace root — the hook judges by session cwd, not by the repo. Use `git -C /Users/park_hyun/myblog-workspace ...` for every git call.
- **Subagents die on the session usage cap** (three of four did at ~03:05). Per the known fallback, the cap blocks *subagent spawns* while the main loop keeps working — so **do the remaining legs directly in the main loop**, do not re-spawn agents and wait.
- `git commit -S` fails (`cannot run gpg`); the repo default signing config works, so just don't pass `-c commit.gpgsign=true`.

---

## 1. Backend / music / worker code — findings

Full evidence (quoted code, call chains, ruled-out guards) in **`docs/reviews/audit-2026-07-26-raw/A-python-services.md`**.
Method: grep sweep per bug class across all four Python repos, then read the enclosing function for every hit. 5 findings adopted.

| ID | Sev | Claim |
|----|-----|-------|
| **A-1** | P1 | **Album sync holds an open write transaction across a Spotify HTTP loop** — and it already holds `ON CONFLICT DO UPDATE` row locks on artists/albums/tracks when it does. `handler.py:179` opens the txn → `sync_service.py:252` → `artist_enrich_service.py:60`. A 403/404/410 on the batch `GET /v1/artists` (routine for a relinked or region-locked artist id) fans out to up to 50 sequential retried GETs while the txn stays open → Neon drops the idle-in-txn connection → `ProtocolViolation` → whole batch rolls back → SQS redelivers → DLQ; meanwhile 10-way concurrent invocations block on the held locks. **This is the exact bug class CLAUDE.md calls out, and the correct pattern already exists ~10 lines below in the same file (`run_artist_photo_backfill`) — it was just never applied to the inline path.** |
| **A-2** | P1 | **A quote in an album title can break the whole site build.** `publish_service.py:43-47` writes MDX frontmatter via Python `repr()`. A title containing **both** `'` and `"` — e.g. `Taylor Swift's "1989"` — emits `title: 'Taylor Swift\'s "1989"'`, which is invalid YAML (confirmed against PyYAML). Publish still returns 200, so it looks like it worked; the next Astro build then fails at `getCollection` and the **entire site deploy is blocked** until someone finds the file by hand. |
| **A-3** | P2 | **Malformed id → 500 instead of 404 on publicly reachable routes.** `/api/research/albums/{id}` and `/api/research/status` pass an unvalidated `str` into a `PGUUID` column; SQLAlchemy 2.0.50 installs no bind processor for that type (verified), so a `DataError` surfaces as a 500. `reviews.py:54` already has the `_parse_album_id` guard for precisely this — it was never propagated. Same shape on ~12 owner-gated routes. |
| **A-4** | P2 | **Today's Pick uses UTC while everything else uses KST.** `todays_pick_service.py:36/176` uses Postgres `current_date`. A pick posted at 08:00 KST is stored under the previous date and disappears from the home tile at 09:00 KST — i.e. the feature silently misfires for a 9-hour window every day. |
| **A-5** | P2 | **musicApi does a blocking AWS control-plane call on every search.** `infra/lambda.tf:83-88` sets `QUEUE_NAME` but not `SQS_QUEUE_URL`, so the per-request `SqsClient()` at `search.py:80` issues `sqs:GetQueueUrl` on every `/candidates` call — *outside* the best-effort enqueue `try/except`. Any control-plane hiccup 500s the writer's search. The backend twin already degrades to a logged no-op; this one doesn't. |

### Classes swept clean (leg A)

- **Auth guards failing open** — backend and music `app/core/auth.py` diffed line by line: behaviourally identical, and all three config gates (`COGNITO_USER_POOL_ID`, `EDGE_SECRET`, `OWNER_SUB`) fail closed. **No twin drift.**
- **Unsorted bulk `ON CONFLICT`** — all 25 call sites read. Every high-concurrency one is explicitly sorted. The two unsorted ones are single-owner jobs with no constructible deadlock interleaving, so deliberately not reported.
- **Outbound HTTP without `timeout=`** — zero hits across all four repos, including the `musicbrainzngs` socket-default workaround.
- **Synchronous Spotify on a user-facing path** — `/api/music/search/unified` is DB-only. The two `accounts.spotify.com` token mints are the documented exception and fail closed before any call.
- **Secrets logged or leaked** — zero.
- **`os.getenv` / `print` in app code** — zero `os.getenv`; `print` only in the local-dev SQS harness.
- **SQS handler correctness** — partial-batch reporting correct, chunk sizes sized to the 120 s Lambda ceiling, wall-clock budgets on every long job, poison-message paths guarded. The one retry-loop risk is A-1.

## 2. Architecture — findings

**Zero findings adopted.** Every structural check came back clean. Done mechanically in the main loop (the subagent died on the session cap before writing anything, so none of its partial claims were used).

This section is deliberately mostly "clean" evidence — under the necessity gate, proving the drift *isn't* there is the deliverable.

### Route ↔ API Gateway parity — CLEAN (both directions)

This is the highest-value check in the leg, because a missing entry means a route that 404s in prod, and it's a known repeat failure mode.

- **43 mutation routes** (`POST`/`PUT`/`PATCH`/`DELETE`) enumerated from the FastAPI source by resolving each `include_router(..., prefix=...)` against every `@router.<verb>` decorator.
- **48 `route_key` entries** in `infra/apigateway.tf`.
- **Mutations missing from `apigateway.tf`: 0.** Every single one is explicitly wired.
- The 3 entries that look unmatched — `ANY /api/music`, `ANY /api/music/{proxy+}`, `GET /api/{proxy+}` — are the intentional catch-alls, not stale rows. The 43 code routes that appear "unwired" are **all GETs**, covered by `GET /api/{proxy+}` by design (e.g. `genres.py:45` carries the explicit comment *"read (edge_guard only — no JWT; covered by GET /api/{proxy+})"*).

### OpenAPI contract — CLEAN

`docs/contracts/openapi.json` carries 84 paths; the backend source declares 70. **Routes in code but absent from the merged spec: 0.** Despite the service→workspace notify dispatch being dead (D-3) and the merge being manual, the contract has not drifted.

### Schema mirror — CLEAN

`docs/contracts/schema.sql` vs `myblog_shared_db/tests/canonical_schema.sql`: **byte-identical**. This parity is convention-only and cannot be enforced by a test (it's cross-repo), and it drifted for 5 days once before — so it is worth stating that it currently holds.

### shared_db pin divergence — REAL, but safe and already documented

The three services do not agree:

| Service | Pin | Resolves to |
|---|---|---|
| `myblog_backend` | `@50d33c39…` (untagged SHA) | V48 — shared_db HEAD |
| `myblog_music` | `@v0.26.0` | `dd016c4` = V32 |
| `myblog_worker` | `@v0.26.0` | `dd016c4` = V32 |

music and worker are **21 commits / 16 schema versions behind** backend. This is the setup for the "tests pass locally, deploy 500s" trap, so it was verified rather than assumed:

- **worker** imports exactly one symbol from the package — `from myblog_shared_db.genre_mapping import attachable_slugs` (`worker/service/sync_service.py:9`). Confirmed present at `v0.26.0` (`genre_mapping.py:176`). Everything else is raw `text()` SQL.
- **music** imports 10 names from `myblog_shared_db.models` — `Album, AlbumGenre, Artist, Base, Genre, Track, album_artists_table, post_albums_table, post_artists_table, track_artists_table`. **All 10 confirmed present at `v0.26.0`.**
- → the lag is intentional (a consumer that doesn't need new columns doesn't bump), and currently harmless.
- The related smell — *"backend pins a moving untagged SHA, not a release tag — a reproducibility smell"* — is **already recorded** in `docs/architecture.md:254` as audit item C-10 from 2026-07-23. **Not re-reported.**

### Service boundaries — CLEAN

No cross-service imports exist. `grep` for `myblog_music` / `myblog_backend` inside the other's `app/` returns **only comments** (`release_feed.py:29` "Cross-repo twin: …", `music/app/core/auth.py:40,67` "Mirrors myblog_backend/…"). The boundary that keeps a Spotify outage away from posts is intact at the import level.

### Auth guard twins — CLEAN (behaviourally)

`myblog_backend/app/core/auth.py` and `myblog_music/app/core/auth.py` differ structurally in ~108 lines: the backend factors out a `verify_token()` helper shared by `require_cognito_token` **and** `edge_guard`; music, which has no edge layer, inlines the same logic. Leg A diffed them line by line and confirmed **behavioural equivalence — all three config gates (`COGNITO_USER_POOL_ID`, `EDGE_SECRET`, `OWNER_SUB`) fail closed in both.** The structural difference is by design, not drift.

## 3. Frontend code — findings

**Zero *new* findings adopted.** The frontend defects this audit found are the three live-verified ones in §5 (E-1, E-3, E-4); the static sweep of the known-recurring frontend bug classes came back clean. Done in the main loop (the subagent died on the session cap before reading anything).

Worth saying plainly: **`myblog_front` is the healthiest part of this system.** Several of the traps below are ones the codebase has clearly been burned by before, and in each case the code now carries an explicit comment showing the lesson stuck.

### Where E-1 actually lives (the fix site)

- `src/components/home/BrowseGenres.tsx:191` calls `fetchGenreTree()`
- → `src/lib/genres.ts:78-86`, which does `apiFetch(BASE + '/api/genres/tree')` behind a module-level promise cache
- `BrowseGenres.tsx:213-215` then keeps only `{ slug, label, albumCount }` for **tier-0 genres**, sorts by count, and `.slice(0, TOP_N)`.

So the homepage needs roughly **13 rows × 3 fields**, and requests 1,230 nodes × 8 fields including 120 KB of markdown. The component's own header comment explains the design intent — *"via fetchGenreTree() — so there is one album_count source of truth"* — which is a reasonable goal; it just doesn't require shipping the whole forest to the client. → §7.

### Checked and clean (leg C)

- ~~**`member.css` dashboard-only trap** — clean.~~ ⚠️ **VERDICT WITHDRAWN — this was WRONG. See §9 finding E-6:** `.lf-artist-link` is emitted site-wide by the `AlbumOverlay` island (mounted from `layouts/layout.astro`) but styled only in `member/layout.css`, which loads on just `/collection/` and `/settings/`. Live-verified unstyled on the production homepage. **4th recurrence of this documented trap.**
  What the sweep *did* establish correctly, and still holds: `qb-*` rules live in `src/styles/modal.css` (not `member.css`), both home-page consumers carry explicit defensive comments (`TodayPickHistory.tsx:13` — *"qb-* modal shell — home page never loads member.css. See TodaySongPicker."*), and `ByTheNumbers.tsx:28`'s `lf-numbers` is fully self-contained. The sweep's error was scoping to page-level components and missing the site-wide island.
- **Tailwind `@theme` token pruning** — 17 of 66 `@theme` tokens are never `var()`-referenced, and **live verification confirms 12 of them were pruned out of the production build** (absent from `getComputedStyle(document.documentElement)`: `--bp-lg/sm/tab/xl/xs`, `--space-1/7/10/14/30`, `--text-display`, `--z-raised`). So the trap is real and active — but **no harm**: the `--bp-*` tokens are documentation constants (global.css:97 says they are *"aligned to"* Tailwind's breakpoints, and the real responsive code uses Tailwind's own namespace, e.g. global.css:159 `--theme(--breakpoint-lg)`). Verified against the built CSS: `md:` and `lg:` each generate **57 rules**, and the emitted media queries are Tailwind's defaults (40/48/64/80/96rem). No responsive class is silently dead. `--color-primary`, `--color-ic-bg`, `--color-ic-border` survive but have zero usage — dead but harmless. **Cleanup opportunity, not a defect** → dropped under the necessity gate.
- **`apiFetch` bypass** — every raw `fetch()` to an API base was checked against its route's actual guard in the backend source. All of them target genuinely public endpoints (music feed, on-this-day, releases calendar, album/artist lookups, `/api/members*`, `/api/reviews/albums/{id}` — confirmed guard-free at `reviews.py:61-67`). **No authed endpoint is called without auth.**
- **The one hand-rolled auth call is the most carefully written code in the sweep.** `src/lib/spotifyPlayback.ts:104` attaches `getAuthHeader()` manually rather than using `apiFetch`, and then maps **every** status to an explicit capability state: 503 → `dormant`, 404 → `disconnected` (documented as "a capability state, not an error"), 401/403 → `unauthorized`, other `!ok` → `error`, plus `try/catch` around both the fetch and the `.json()`, plus a missing-`access_token` guard. Nothing falls through.
- **The two API base env vars** — `PUBLIC_API_URL` (music) vs `PUBLIC_BACKEND_API_URL` (backend), a documented past mix-up. Every consumer is on the correct one: music-service concerns (`albumDetail`, `artistNames`, `spotifyCatalog`, `useMusicSearch`) use `PUBLIC_API_URL`; backend concerns (`buckets`, `genres`, `research`, `todaysPick`, `spotifyPlayback`, `api.ts`) use `PUBLIC_BACKEND_API_URL`. **No crossovers.**
- **Contract drift** — covered by the leg B check: 0 backend routes missing from the merged spec, and the front's `api.gen.ts` gate is enforced in CI (which is green).
- **Empty / loading / error states** — verified live rather than by reading (§5): every empty surface renders written copy, and the one async spinner resolves.

## 4. Functional / operational — findings

Partial: the launchd / nightly-pipeline half is done. SQS/DLQ depths, Lambda error logs, EventBridge rules, open PRs
and plan.md-vs-reality are **still outstanding** — see the RESUME STATE table.

### D-1: The nightly Editor Buckit pipeline can write a review draft but cannot deliver it — it 403s, and has done so on the only night it ever had one

- **Severity**: **P0** — the flagship automation is broken end-to-end, and its failure is invisible from the outside.
- **Observed state** (`~/Library/Logs/myblog-buckit-nightly.log`, run of 2026-07-25):
  ```
  2026-07-25 03:01:30,174 INFO  done in 81.7s — 2 file(s) in docs/buckit/2026-07-25:
                                the-strokes-is-this-it.md, _summary.md
  2026-07-25 03:01:31,745 WARNING draft not created (album 782b7ade-3ed1-465e-84c2-89f38db8bf9b,
                                status 403): {'detail': 'Owner only'} — memo left checked, file kept
  2026-07-25 03:01:31,745 INFO  draft delivery: 0 draft(s) created, 0 memo(s) grown, 1 skipped/failed
  ```
  The generated draft is still sitting on disk at `docs/buckit/2026-07-25/the-strokes-is-this-it.md` (6,360 bytes). It never reached the blog.
- **Root cause** — a stale assumption that the multi-user migration invalidated:
  - `scripts/buckit_nightly.py:568` `mint_smoke_token()` authenticates the pipeline as the **smoke/test user**, and its own docstring at **line 573** states the premise: *"Blast radius: in this single-user, no-per-user-scoping system the token is owner-equivalent — it CAN publish/edit/delete any post."*
  - That premise is no longer true. `myblog_backend/app/core/auth.py:138` records why: *"FEAT-multi-user-accounts 0c: enabling Cognito self-signup fills the pool with federated members, so `require_cognito_token` alone (any valid pool token) no longer implies the owner."*
  - `POST /api/posts` is gated by `require_owner` (`app/api/routes/posts.py:64`), which requires `sub == OWNER_SUB`. The smoke user's `sub` is not `OWNER_SUB`. → permanent 403.
  - The follow-up `PATCH /api/buckets/{id}/items/{id}` (`buckit_nightly.py:717`) is owner-gated too, so the "grow" step would fail identically.
- **Why nobody noticed** — three independent things hide it, which is why this deserves the P0:
  1. **It is a regression from a named PR, and 17 days passed before anything tripped it.** ⚠️ *Corrected in §9 (C-3) — the original text here claimed the pipeline had never produced a draft before, which is false.* Delivery **worked twice**: `2026-06-23` and `2026-07-05`, both logging `1 draft(s) created, 1 memo(s) grown, 0 skipped/failed`. It was broken by **`392dd50` — "feat(auth): owner-gate single-owner routes before self-signup opens the pool (#107)", 2026-07-08** — which added `require_owner` to `POST /api/posts`. No draft was produced between 07-08 and 07-25, so the regression had nothing to trip it for 17 days. Every run in that window logged `0 draft(s) created, 0 skipped/failed`, which reads as healthy but only means nothing was produced.
  2. **The error is classified as retryable when it is permanent.** `buckit_nightly.py:705-711` lumps the failure in with `409 ⇒ already exists` and `5xx ⇒ transient; retry next run`. A 403 is neither — it will recur every single night, forever, one `WARNING` line at a time.
  3. **The process still exits 0.** `main()` wraps delivery in a never-crash guard ("never crash after files are written", line 829), so `launchctl list` reports success and no alert fires.
- **Impact**: the entire point of the nightly pipeline — get a drafted review into the blog — does not work. Reviews accumulate as untracked files in `docs/buckit/` and the site still shows "아직 리뷰가 없습니다" and "0편 평론" (see §5). This also explains the homepage's empty state.
- **Not yet verified** (needs owner input or a live check): whether the intended fix is to give the pipeline owner credentials, to add a service identity that `require_owner` accepts, or to relax the gate for `status:'draft'` creation. **This is a design decision, not a patch — hence docs-only.** → §7.

### D-2: `LLMTransientError` is never retried, so one transient failure silently costs a whole night

- **Severity**: P2 — no data loss, but the night's output is gone with no retry and no alert.
- **Observed state**: tonight's run (2026-07-26 03:00) died with a traceback and **exit 1**; `docs/buckit/2026-07-26/` was never created.
  ```
  File ".../scripts/buckit_nightly.py", line 504, in run_claude
      res = ENGINE.run(_job(prompt))
  File ".../myblog_shared_db/src/myblog_shared_db/llm/cli_engine.py", line 166, in _dispatch_once
      raise LLMTransientError(
  myblog_shared_db.llm.exceptions.LLMTransientError: claude exit 1:
  ```
- **Evidence**: `cli_engine.py:131-146` — `run()` retries **only** `LLMValidationError` (`attempts = 2 if job.output_schema is not None else 1`). `LLMTransientError` — raised for CLI timeout (`:162`), missing binary (`:164`), and any non-zero exit (`:165-168`) — propagates out of `run()` on the first occurrence. A class named *transient* has no retry, no backoff, and no alert path.
- **Failure scenario**: any momentary condition — CLI timeout, a shared usage cap, a network blip — permanently loses that night's draft. Recovery requires a human to notice and re-run by hand.
- **Honest attribution for tonight specifically**: this audit session ran concurrently with the 03:00 job and shares the same usage limit, which is the documented hazard "parallel night sessions kill 03:00 `claude -p` via shared usage limit". So **this session most likely caused tonight's failure.** That does not make the finding invalid — the missing retry is what turns a shared-cap collision into a lost night — but the trigger tonight was self-inflicted and should not be counted as an independent incident.

### D-3: A workflow that is documented as dead is still enabled, and has failed on every run for three weeks

- **Severity**: P2 — no functional impact; the harm is that it trains you to ignore red CI.
- **Observed state**: `myblog_music` → workflow **"Notify workspace of openapi.json update"**:
  ```
  failure  2026-07-20T16:05:06Z
  failure  2026-07-20T15:11:01Z
  failure  2026-07-12T15:22:36Z
  failure  2026-07-11T14:51:23Z
  failure  2026-07-07T16:09:13Z
  success  2026-06-15T01:58:56Z   ← last time it worked
  ```
  Five consecutive failures since 2026-07-07; it fires on every music deploy.
- **Impact**: `CLAUDE.md` already documents this path as dead ("the service→workspace notify-contract dispatch 401s — auto-merge is dead") and the contract merge is now done by hand. So the job produces nothing but a red ✗ on otherwise-green deploys. Every deploy now ships with a failure the team has been taught to ignore — which is exactly the state in which a *real* deploy failure gets waved through.
- **Why it isn't already handled**: the manual replacement process was adopted, but the dead workflow was never disabled or deleted. Disabling it is trivial; deciding between "disable" and "fix the 401" is an owner call. → §7.

### Verified healthy / observed (leg D)

- **All 5 launchd agents are loaded**: `com.myblog.research-poller`, `com.myblog.lyrics-translate-poller`, `com.myblog.buckit-nightly`, `com.myblog.genre-backfill`, `com.myblog.genre-heal-poller`. Last exit status 0 for all except `buckit-nightly` (1, = D-2 tonight). This is **not** a repeat of the "reboot drops the agents" trap — they are genuinely loaded.
- **Nightly run history is continuous except one known gap**: runs present for 07-11…07-20, then **07-21 / 07-22 / 07-23 missing entirely** (no start line at all), then 07-24 / 07-25 / 07-26 present. That 3-night gap is the already-documented 07-20 reboot incident, not a new fault — **not re-reported.**
- **Draft generation itself is reliable**: 15 successful `claude -p` runs, 50–92 s typical (one 918 s outlier on 07-20), consistent token counts.

- **SQS is completely drained.** All three queues at zero on every counter — including **both DLQs**:

  | Queue | Available | In flight | Delayed |
  |---|---|---|---|
  | `blogSQS` | 0 | 0 | 0 |
  | `album-sync-dlq` | 0 | 0 | 0 |
  | `worker-cron-dlq` | 0 | 0 | 0 |

  Note this also means **A-1 has not actually fired in production yet** — it is a latent defect, not an active incident.
- **Zero Lambda errors in 48 h.** `filter-log-events` with `?ERROR ?Traceback ?"Task timed out"` over the last 48 h returned **nothing** for `ratemymusic-api`, `musicApi`, and `blogWorkerLambda`.
- **All EventBridge rules ENABLED, every target resolves to a live Lambda.** Both 5-minute warm-pings (backend + music) are running; no rule points at a deleted function. ⚠️ **Corrected in §9 (C-1):** there are **15** rules, not the 14 counted here — `worker-isrc-backfill` was applied at ~08:07 KST on 2026-07-26, mid-audit. And per **OPS-1**, that 13th worker cron is the one with **no `FailedInvocations` alarm**.
- **No open PRs** in any of the 6 repos.
- **Deploys are green.** Latest deploy per repo all `success`: backend 07-24, front 07-24, music 07-24, worker 07-25. The only red is D-3.
- ~~**`docs/plan.md` is accurate and current** (84 lines)~~ — ⚠️ **WITHDRAWN, see §9 (C-2).** The copy inspected was **3 commits behind `origin/main`** and was never re-fetched, so this verdict is unsupported. The rows that *were* spot-checked against `git log` and `docs/archive/done/` showed no staleness, but that says nothing about current `origin/main` (90 lines).

### Still outstanding in leg D

- Nothing. (The earlier item here — "confirm `worker-isrc-backfill` is still un-applied" — was **wrong**: the rule was applied mid-audit and is live. See §9 C-1. What replaces it is **OPS-1**: that rule has no `FailedInvocations` alarm.)

## 5. UI/UX (live production) — findings

Production site: `https://www.ratemymusic.blog` (CloudFront `E2Q2JH5EAYVU1O`). Verified logged-out, read-only, via CDP.
Swept 2026-07-26 ~02:45–03:00 KST at 1440×900 desktop and 390×844×3 mobile+touch emulation.

### E-1: The homepage downloads a 742 KB genre tree (292 KB over the wire) to draw six bars, and it is uncacheable

- **Severity**: P1 — every visitor, every visit, including repeat visits and mobile data.
- **Where**: homepage `/` → `GET /api/genres/tree` (backend route; the frontend genre-distribution module on `/`)
- **Measured on production (mobile emulation, 390×844)**:
  - `/api/genres/tree`: **291,928 bytes transferred / 741,895 bytes decoded / 1,257 ms — on every visit.** This is the finding, and it is unaffected by the correction below.
  - Share of page weight, ⚠️ **corrected in §9 (C-5)** — the original text quoted only the larger figure:
    - **warm repeat visit**: total transfer 296,971 B across 77 resources → this one call is **~98 %** of it (everything else came from cache; this call cannot).
    - **cold first visit**: the page is ~**2.0 MB**, so this call is **~14 %** of it.
  - Both are true of different visits. The honest statement is the per-visit cost plus the uncacheability, not the percentage.
- **Why it cannot be cached**: the response carries **no `cache-control` header at all**, so CloudFront never stores it —
  repeated `curl` shows `x-cache: Miss from cloudfront` every time, TTFB 0.75–1.3 s.
  The two sibling homepage endpoints DO set it and DO cache:
  - `/api/music/albums/on-this-day` → `cache-control: public, max-age=60, stale-while-revalidate=60` → 2nd request `x-cache: Hit from cloudfront, age: 19`
  - `/api/music/feed/new-releases` → same header, same behaviour
  So this is header **drift between sibling endpoints**, not a deliberate freshness choice.
- **What the payload actually contains** — ⚠️ **corrected in §9 (C-6)**; the original decomposition was wrong and pointed the fix at the wrong field:
  - 1,230 genre nodes, 5 levels deep (13 / 247 / 779 / 179 / 12 per level)
  - `definition_md` markdown bodies: **242,646 B** of UTF-8 (120,774 characters). Stripping them gives 741,895 → **475,305 B, only −36 %**.
  - **The largest unused chunk is the `edges` array — 2,064 entries, ~246 KB — which `/` never reads at all.** Node scaffolding is a further ~229 KB.
  - So the cheapest big win is dropping `edges` (and levels 1–4) for the homepage, not trimming the markdown.
- **What the homepage renders from it**: six rows — Pop 1,253 / Hip-Hop 1,191 / Rock 501 / R&B-Soul 336 / K-Pop 318 / Electronic 309 — i.e. the label + `album_count` of the top 6 top-level genres. Nothing else on `/` reads the tree, the definitions, or levels 2–5.
- **Failure scenario**: a first-time mobile visitor on a normal cellular connection waits ~1.3 s of blocking API time and spends ~292 KB of data before the genre strip paints; a returning visitor pays it again in full because nothing caches. The same page's other three API calls cost 4.4 KB combined.
- **Note**: `/genres/` (the Genre Map page) legitimately needs the full tree — it renders all 13 top-level nodes with subtree counts and expandable definitions. The finding is scoped to `/` only.
- **Why it isn't already handled**: checked response headers on all four homepage calls; only this one lacks `cache-control`. Checked the rendered DOM of the genre section — it consumes label + `album_count` only.

### E-2: A public page shows a raw Cognito-sub fragment as a user's display name

- **Severity**: P2 — cosmetic + minor identifier exposure, on a public unauthenticated page.
- **Where**: `/collection/` — the shared My Buckit list
- **Observed**: the collection "To Review" (46 albums) is bylined **`@user-0468fd3c`**. `0468fd3c…` is the owner's Cognito `sub` prefix (`OWNER_SUB`). Any anonymous visitor sees it.
- **Failure scenario**: the flagship public "회원들이 공개한 My Buckit을 모았습니다" page attributes its only collection to a machine identifier, so the section reads as unfinished; and a stable per-user identifier fragment is published where none needs to be.
- **Why it isn't already handled**: this is the fallback used when a member has no display name set. Whether the fix is "require a display name" or "render a neutral label" is an owner decision, not a code bug per se — recorded as a decision item, not a defect to patch blindly.

### E-3: First-visit mobile CLS measures 0.14–0.32 — always worse than "good", usually worse than "poor" — because homepage sections mount with no reserved height

- **Severity**: P1 — affects every first-time visitor; content jumps under the reader's thumb.
- **Where**: homepage `/` — the "오늘, 이 앨범들" rail, the "장르로 탐색" distribution module, and the new-releases `hstrip`.
- **Measured** — ⚠️ **corrected in §9 (C-7)**: the original text led with the single worst run and mis-stated the threshold. Cold first-visit CLS is **run-to-run variable: 0.1405 / 0.2445 / 0.2919 / 0.315** across independent cold runs. Google's thresholds are good ≤ 0.10, poor > 0.25 — so every run is worse than "good" and most are worse than "poor". 0.315 is ~3× the *good* threshold, not 3× the poor one.
  - Lighthouse, mobile navigation, cold profile: **CLS = 0.315** (the high end).
  - Independent reproduction in a fresh isolated browser context (no service worker: `navigator.serviceWorker.controller === null`), 390×844×3, Slow 4G: **CLS = 0.1405 over 6 shifts** (the low end).
  - Warm repeat visit (service worker in control): CLS = 0.0202. **So this is a first-visit-only defect** — which is exactly the visit that matters, and exactly the one the owner never sees while developing.
- **Attribution** (`PerformanceObserver` on `layout-shift`, with `sources`):
  - `t = 984 ms`, shift 0.0431 — the 장르로 탐색 block goes from height **0 → 70 px**; "오늘, 이 앨범들" jumps from y=644 to y=482.
  - `t = 1996 ms`, shift **0.0971** (largest) — "오늘, 이 앨범들" moves y=482 → y=849 and collapses 349 px → 51 px, while `DIV.hstrip` collapses 219 → 0 and the genre block collapses 70 → 0. The sections re-render a second time as their data resolves.
  - Remaining four shifts are ≤ 0.0002 (header bar settling, font metrics) — negligible.
- **Failure scenario**: on a phone over cellular, a visitor starts reading the "오늘, 이 앨범들" album rail about a second into the load; at ~2 s the whole rail is displaced 367 px down the page and collapses. A tap aimed at an album lands on whatever slides into place.
- **Link to E-1**: the largest shift lands at ~2 s, and the genre module is the block that appears then disappears then re-renders. It is gated on `/api/genres/tree` — the 292 KB uncacheable payload from E-1. Shrinking that payload shortens the window; reserving height removes the shift. They are the same defect seen from two angles, and worth fixing together.
- **Why it isn't already handled**: Lighthouse Accessibility / Best-Practices / SEO all score **100** on this page, so a category-score check would show nothing wrong. CLS is the only failing metric and it is invisible on a warm reload, which is the normal way to look at your own site.

### E-4: Eight homepage album buttons fail WCAG 2.5.3 "Label in Name"

- **Severity**: P2 — real conformance failure, narrow real-world impact.
- **Where**: homepage new-releases rail, `button.nrl-open` inside `div.hstrip > div.hstrip-track > article.nrl-card` (8 instances on the current homepage).
- **Observed**: each button's visible text is e.g. `Reality Awaits / The Strokes / 07.24 발매`, while its accessible name is `aria-label="Reality Awaits — The Strokes 앨범 보기"`. The visible text is not contained in the accessible name (the release-date line is absent and the separator differs), which is what axe's `label-content-name-mismatch` reports — a **WCAG 2.5.3 Level A** failure.
- **Failure scenario**: a speech-input user saying "click Reality Awaits 07.24 발매" — or any voice-control matcher that requires the visible label to be a prefix/substring of the accessible name — cannot activate the card.
- **Why it isn't already handled**: this is the *only* accessibility rule that fails on the page; the Accessibility category still scores 100 because this rule is not weighted into that score. It will not be caught by a score check.

### E-5: `/write/` — the owner-only editor — renders in full for any logged-in member, publish buttons and all

_(found in the deepening pass, 2026-07-26 ~09:30 KST, using a minted non-owner member token)_

- **Severity**: P2 — **not** a security breach (the backend fails closed, verified below), but a real UX defect and a gap in a pattern the codebase otherwise applies consistently.
- **Where**: `src/pages/write.astro` → `src/components/writer/WriterApp.tsx`
- **Observed**: navigating to `https://www.ratemymusic.blog/write/` as a **non-owner member** (`sub a4f83dcc…`, ≠ `OWNER_SUB 0468fd3c…`) renders the complete authoring surface: 작성 / 미리보기 / 임시저장 / **발행**, the 임시 저장함 inbox, and the full 발행 설정 panel with sections, review tags, and the entire 13-branch subgenre taxonomy with counts. The only indication anything is wrong is a single silent console line: `GET /api/posts?status=draft → 403`.
- **Why this is a gap and not a decision**: the frontend already has an owner-gating helper, `isOwnerUser()` from `@lib/owner`, applied in `TodaySongBuckit.tsx:80`, `ReleaseRadar.tsx:153`, `PocketTray.tsx:359` and `header.client.ts:22` (`SelfDashboard.tsx:97` uses a handle comparison instead). `write.astro` and `WriterApp.tsx` contain **no owner check at all** (the sole `owner` match in `WriterApp.tsx:25` is an unrelated design-decision comment). The authoring surface was simply missed by the pattern.
- ⚠️ **Scope widened in §9 (C-11): `src/pages/drafts.astro` is ALSO ungated** — no owner check, no redirect. A fix scoped to `/write/` alone leaves that hole open. Treat the owner-only *runtime* surfaces as a class (`/write/`, `/drafts/`, and `/settings/` — the last unverified).
- **Secondary**: `DraftsInbox.tsx` has **no 403 or error handling** — the 403 renders as a normal empty drafts list, not as "권한 없음".
- **Failure scenario**: Cognito self-signup is enabled, so any member can reach `/write/`. They compose a full review, press 발행, and the backend correctly 403s — after they have done all the work, with no prior signal that they were never permitted to publish.
- **Explicitly ruled out**: no data risk. `POST /api/posts` is `require_owner` and returns 403 for this token (probed live). Nothing a member does here can be saved.

### Checked and clean (live, logged-out)

- **Console**: zero `error` and zero `warn` messages on `/`, `/reviews/`, `/genres/`, `/canon/`, `/collection/`, `/artist/<id>/`. This is unusually clean.
- **Trailing-slash routing**: both `/reviews` and `/reviews/` (and genres/canon/collection) return **200, no redirect** — header links use the trailing slash, footer links omit it, and both work. Not a finding.
- **Mobile horizontal overflow**: none. `scrollWidth === clientWidth === 390` on the homepage. Elements extending past 390 px are all inside intentional horizontal scroll rails (`nrl-card`) or the off-canvas drawer (`hdr-drawer`, negative offsets) — correct, not overflow.
- **Broken images**: none found on `/`, `/genres/`, `/collection/` (46 covers), `/artist/<id>/` (15 covers).
- **Empty states**: `/reviews/` ("아직 리뷰가 없습니다"), `/canon/` ("아직 명반이 없습니다" + explanation of the ★4.0 rule), artist page ("아직 이 아티스트의 평론이 없습니다") all render deliberate, written empty states rather than blank regions or dead spinners.
- **Async discography**: artist page shows "불러오는 중…" then resolves to a populated catalog within 6 s — not a stuck spinner.
- **Lighthouse (mobile, navigation)**: Accessibility **100**, Best Practices **100**, SEO **100**; 53 audits passed, 2 failed (both recorded above as E-3 and E-4). This is a genuinely well-built front end — the two findings are the exceptions, not the pattern.
- **LCP**: 158 ms on a warm load (TTFB 58 ms + 100 ms render delay). No render-blocking savings available (`RenderBlocking` insight: FCP 0 ms, LCP 0 ms estimated savings).

### Observed but NOT adopted as findings (necessity gate)

- **Homepage stat block reads "0편 평론 / 0개 장르 / — 최근 업데이트"** while the section directly above reports 4,479 catalogued albums across 13 genres. Consistent if "장르" means *genres that have a published review* (there are 0 reviews). Contradictory-looking to a reader, but no demonstrable harm and possibly intended. → **owner decision item (§7), not a defect.**
- **"첫 리뷰를 작성해 보세요" shown to logged-out visitors** on `/reviews/` — an owner-facing call to action on a public page. Cosmetic; no harm proven. → §7.
- **Tap targets under 44 px on mobile**: LOGIN button 38×29, header icon buttons 40×40. Below the 44 px HIG guideline but not demonstrably causing mis-taps. → dropped.
- **Duplicate "ICEMAN (2026 · ALBUM)" entries in Drake's discography** — this is release-noise in the catalog, already the subject of the tracked `DATA-release-noise` workstream. → **not re-reported as new.**

## 6. Necessity-gate verdicts

**21 findings adopted** — 12 in the main run, E-5 from the deepening pass, DEP-1/2/3 from the dependency scan (§8), and **PUB-1 / OPS-1 / SEC-1 / SEC-2 / E-6 from the re-review (§9.2)**. Roughly as many candidates were dropped for failing the bar.

**Verification status**: the 13 pre-§8 findings are each directly measured on production or independently verified. DEP-1/2/3 rest partly on untraced applicability (§8 says so, and DEP-2's applicability was subsequently **overturned** — §9 C-4). The five §9.2 findings were verified by hand at discovery. ⚠️ *The original text here claimed "none rests on a single unchecked inference", which overstated the position — corrected per §9 (C-13).*

| ID | Sev | One-line | Leg |
|----|-----|----------|-----|
| **D-1** | **P0** | Nightly pipeline writes drafts it can never deliver — permanent 403, exit code still 0 | ops |
| **A-1** | P1 | Album sync holds a locked write txn across a Spotify HTTP loop → Neon drop → DLQ | worker |
| **A-2** | P1 | An album title with both `'` and `"` emits invalid YAML → the whole site build breaks | backend |
| **E-1** | P1 | Homepage ships a 742 KB uncacheable genre tree (98.3 % of its bytes) to draw 6 bars | front/live |
| **E-3** | P1 | First-visit mobile CLS 0.315 — 3× the "poor" threshold — from sections mounting with no reserved height | front/live |
| **A-3** | P2 | Malformed id → 500 instead of 404 on publicly reachable research routes | backend |
| **A-4** | P2 | Today's Pick uses UTC `current_date` while the system is KST → picks vanish for 9 h/day | backend |
| **A-5** | P2 | musicApi does a blocking `sqs:GetQueueUrl` per search, outside the best-effort guard | music/infra |
| **D-2** | P2 | `LLMTransientError` is never retried → one blip silently costs a whole night | shared_db |
| **D-3** | P2 | A workflow documented as dead is still enabled and has failed every run for 3 weeks | ci |
| **E-2** | P2 | Public collection page bylines a raw Cognito-sub fragment as a display name | front/live |
| **E-4** | P2 | 8 homepage album buttons fail WCAG 2.5.3 "Label in Name" | front/live |
| **E-5** | P2 | `/write/` owner-only editor renders in full for any member, publish buttons included (no data risk — backend fails closed) | front/live |
| **DEP-1** | P1 | Dependabot is off on all 6 repos and no CI audit step exists — nothing would ever report a vulnerable dependency | deps |
| **DEP-2** | ~~P2~~ **hygiene** | `@astrojs/rss@4.0.13` → 4.0.19. ⚠️ **Applicability overturned (§9 C-4)** — the advisory's vulnerable fields are never populated and the feed is empty. Not a security fix. | deps |
| **DEP-3** | P2 | `@astrojs/node` declared but never used (`output: 'static'`, no adapter) — carries 6 non-applicable advisories forever | deps |
| **PUB-1** | **P1** | The workspace + 4 service repos are **PUBLIC** — merging this report publishes reproduction detail for still-unfixed live defects (§9.2) | process |
| **OPS-1** | **P1** | `worker-isrc-backfill` has no `FailedInvocations` alarm — `monitoring.tf`'s hardcoded 12-cron map silently regressed the OPS-RFC's "ALL worker crons" guarantee (§9.2) | ops/infra |
| **SEC-1** | **P1** | The CloudFront-attached WAF has **0 rules and default Allow** — a documented control that does nothing (§9.2) | infra |
| **SEC-2** | P2 | `ENV` defaults to `"local"` in both services, and `local\|dev` disables the auth guards entirely — the one missing-config path that fails **open** (§9.2) | auth |
| **E-6** | P2 | `.lf-artist-link` ships unstyled site-wide (styled only on `/collection/` + `/settings/`) — **4th recurrence** of the `member.css` trap, live-verified (§9.2) | front/live |

### Adversarial verification (leg F)

The two highest-stakes claims were attacked rather than accepted:

- **D-1 — the competing explanation was refuted.** A 403 from `require_owner` could mean either (a) the smoke user isn't the owner, or (b) `OWNER_SUB` is unset in prod, which would break the *owner's* access too — a much worse bug with a different fix. `app/core/auth.py:152-165` distinguishes them precisely: unset `OWNER_SUB` → **503 "Auth not configured"**; `sub` mismatch → **403 "Owner only"**. The log shows exactly `403 {'detail': 'Owner only'}`, and `aws lambda get-function-configuration ratemymusic-api` confirms **`OWNER_SUB = 0468fd3c-201…` is set**. Hypothesis (b) is dead; (a) is confirmed. *(This also independently confirms E-2 — the `@user-0468fd3c` byline on the public collection page is that same OWNER_SUB prefix.)*
- **A-2 — reproduced independently**, not taken on the subagent's word. Running the actual `f"title: {title!r}"` construction from `publish_service.py:43` through PyYAML:
  - `Taylor Swift's "1989"` → emits `title: 'Taylor Swift\'s "1989"'` → **`ParserError`** (single-quoted YAML escapes `'` by doubling it, never with a backslash)
  - `It's Only Rock` → emits `"It's Only Rock"` → parses fine
  - `"Heroes"` → emits `'"Heroes"'` → parses fine
  - It genuinely requires **both** quote characters in one title. Confirmed, and correctly scoped.
- **A-1's blast radius was checked against reality**: all three SQS queues and **both DLQs are at zero**, so A-1 has **not fired in production yet**. It is latent, not an active incident — which is why it is P1 and not P0.

### Candidates raised and deliberately dropped

Recording these matters as much as the findings — under a necessity gate, "we looked and it doesn't warrant work" is a result.

- **shared_db pin lag** (music/worker 16 schema versions behind backend) — looked alarming; **verified harmless**. All 10 model names music imports and the single symbol worker imports exist at `v0.26.0`. The related "backend pins a moving untagged SHA" smell is already logged as C-10 in `architecture.md:254`. Dropped.
- **Tailwind `@theme` pruning** — the trap is genuinely active (12 tokens confirmed missing from the live build) but causes **no** broken style: the `--bp-*` tokens are documentation constants and the real responsive code uses Tailwind's own namespace (`md:`/`lg:` each emit 57 rules in prod). Cleanup opportunity only. Dropped.
- **Homepage stats reading "0편 / 0개"** beside "4,479장 · 13 genres" — reads as contradictory, but is consistent if "장르" counts *genres with a published review*. No harm proven. → §7 decision, not a defect.
- **"첫 리뷰를 작성해 보세요" shown to logged-out visitors** — owner-facing CTA on a public page. Cosmetic. → §7.
- **Sub-44 px mobile tap targets** (LOGIN 38×29, icon buttons 40×40) — below the HIG guideline, no demonstrated mis-tap harm. Dropped.
- **Duplicate "ICEMAN" in Drake's discography** — real, but it is catalog release-noise already owned by the tracked `DATA-release-noise` workstream. Not re-reported.
- **3-night nightly gap (07-21…07-23)** — real, but it is the already-documented 07-20 reboot incident. Not re-reported.
- **`auth.py` twin differs by ~108 lines** — structural, not behavioural; backend factors out `verify_token()` for its `edge_guard`, music has no edge layer. Both fail closed on all three config gates. Dropped.

---

## 6b. Deepening pass (2026-07-26 ~09:20–09:45 KST, fired by the 5 h resume trigger)

All 7 checklist rows were already DONE, so per the trigger's instruction this was a **refutation + gap-sweep** pass rather than new discovery. It produced **one new finding (E-5)**, **upgraded six findings from "inferred" to "verified on production"**, and **overturned nothing**.

### Findings that survived direct attack

| ID | How it was attacked | Result |
|----|---------------------|--------|
| **D-1** | Minted the actual smoke token and decoded it | **PROVEN, not inferred.** Smoke `sub = a4f83dcc-0071-703c-e2e6-7864735d2e20`; prod `OWNER_SUB = 0468fd3c-201…`. They differ. Then probed live: `GET /api/posts → 403`, `GET /api/todays-pick/queue → 403` with that exact token. The 403 in the nightly log is reproduced end to end. |
| **A-3** | Probed production directly (unauthenticated GET) | **CONFIRMED, and sharper than reported.** `/api/research/albums/not-a-uuid → 500`; the *same route* with a well-formed but absent uuid → **404**. So the 500 is purely the id-parse failure, and it is reachable with no credentials at all. |
| **A-5** | `aws lambda get-function-configuration musicApi` | **CONFIRMED exactly.** `QUEUE_NAME=blogSQS` present, `SQS_QUEUE_URL` **absent**. |
| **A-1** | Re-read the call chain independently of leg A | **CONFIRMED, and strengthened.** `handler.py:179` `with SessionLocal() as session, session.begin():` wraps the whole `sync_albums_batch`, and `sync_service.py:251-252` calls `enrich_artists(self.conn, …)` inside it. Decisive corroboration: `_run_isrc_backfill` **in the same file** carries the comment *"No handler-owned session.begin(): … Wrapping this in session.begin() would…"* — the codebase knows the correct pattern and this path is the exception. |
| **A-4** | Looked for the project's own day-boundary convention | **CONFIRMED, and it violates an explicit written rule.** `release_feed.py:36-41` states *"Day boundary is KST wall-clock (site convention; DB stores UTC)"* and implements `datetime.now(_KST).date()`, naming **09:00 KST** as the rollover. `todays_pick_service.py:36,176` uses Postgres `func.current_date()` (UTC). The 00:00–09:00 KST harm window is exactly as described. |
| **A-2** | Re-ran the construction through PyYAML (leg F) | **CONFIRMED**, needs both `'` and `"`. |

### Severity NOT raised (attacks that failed to make things worse)

- **A-3 does not leak internals.** The 500 body is the literal string `Internal Server Error` (`content-type: text/plain`) — no traceback, no SQL, no schema. Stays P2.
- **A-1 has still never fired.** Re-checked: all queues and both DLQs at 0. Latent, not active.

### Gap sweep — authenticated surface (previously "NOT covered")

Swept read-only with a minted non-owner member token. **No write action was performed.**

- **The four member-scoped routes probed return correctly isolated results.** A non-owner member calling `/api/library/stream-history/clock`, `/stream-history/top-artists`, `/api/me/release-feed`, and `/api/integrations` gets **empty results** — none of the owner's listening history, feed, or integrations leaks. Verified against live prod. ⚠️ **Scope corrected in §9 (C-10):** the original text generalised this 4-route sample to "multi-user row-scoping genuinely isolates". Four routes do not establish that; the rest of the member surface was not probed.
- **A false alarm was chased down and dismissed.** `/api/library/stream-history/clock` returned **200** to a non-owner, which looked like an auth bypass. Reading `library.py:520-528` shows it takes `member_id: uuid.UUID = Depends(provisioned_member_id)` and queries `user_id=member_id` — a correctly row-scoped **member** route by design. The `require_owner` at `library.py:545` belongs to `POST /saved-tracks/classify`. **Not a finding.**
- **`/members/` and `/radar/` are clean when authed** — header flips to LOGOUT, the POCKET tray mounts, both render written empty states, **zero console errors, no horizontal overflow**.
- **`/write/` is the exception** → E-5 above.

### Still not covered, even after deepening

- ~~**Dependency / CVE scan — attempted and blocked.**~~ **DONE — see §8.** The `pnpm audit` timeout was not a network problem; it was that one legacy endpoint. Re-done via OSV.dev against the lockfiles directly.
- **No load or concurrency testing** — A-1's lock-contention path remains reasoned, not observed.
- **No database-level data-quality audit** (orphan rows, constraint violations, duplicate catalog entries).
- **No review of Terraform state** (only `.tf` source was read).
- **Member-profile surfaces could not be meaningfully exercised**: `/api/members` is empty in prod (no member has rated an album yet), so `/members/[handle]` dashboards have no data to render. This is a data precondition, not a defect.

### What this audit did NOT cover

Stated so the clean verdicts aren't read as broader than they are:

- The **authenticated surface** (`/members/`, `/write`, admin, the player bar, the lyrics sheet) was not exercised live — leg E covered the logged-out public surface only.
- **No load or concurrency testing.** A-1's deadlock/lock-contention path is reasoned from the code plus the 10-way SQS concurrency setting, not observed.
- **No database-level data-quality audit** (orphan rows, constraint violations, duplicate catalog entries beyond what the UI surfaced).
- **No dependency/CVE scan**, and no review of the Terraform state itself (only the `.tf` source).

---

## 8. Dependency vulnerabilities (owner-requested re-run, 2026-07-26 ~10:00 KST)

`pnpm audit` had timed out earlier, so this was redone by a different route. Method: parse the lockfiles → query **OSV.dev** (`/v1/querybatch`) → fetch each advisory. Script kept at `audit-2026-07-26-raw/osv_scan.py`, raw output at `audit-2026-07-26-raw/osv-report.txt`.

**Why the first attempt failed**: not a network block. `registry.npmjs.org` answers in **34 ms** from here — it is specifically pnpm's legacy `POST /-/npm/v1/security/audits` endpoint that hangs. Worth knowing so this isn't misdiagnosed again.

### Two corrections that changed the answer

Recording these because the naive version of this scan produces a **false CRITICAL** and would have wasted a day:

1. **Never feed `requirements.txt` versions to a CVE database here.** Several pins are wildcards — `SQLAlchemy==2.*`, `psycopg[binary]==3.*`, `python-dotenv==1.*`. Querying OSV for version literal `"2.*"` matches **CVE-2012-0805 / CVE-2019-7164 / CVE-2019-7548 — three CRITICAL SQL-injection advisories against SQLAlchemy 0.x/1.x**. The real installed version is **2.0.50**, which none of them touch. The corrected scan reads actual versions out of each service's venv.
2. **npm hits must be split by whether they can reach a user.** This is a prebuilt static site on S3 — no npm code runs on a server. 31 of the 34 npm packages with advisories are build tooling (`vite`, `node-tar`, `fast-xml-parser`, `yaml`, …) that never ships. Reporting those as vulnerabilities would be noise.

### Scan coverage

| Ecosystem | Scanned | Packages with advisories |
|---|---|---|
| npm (`pnpm-lock.yaml`, all resolved) | 1,419 | 34 — of which **3 are direct runtime deps** |
| PyPI (4 service venvs) | 149 | 16 |

150 advisory instances total (2 CRITICAL, 56 HIGH, 73 MODERATE, 19 LOW) — but see the triage: most are unreachable in this deployment.

### DEP-1 (P1): Nothing in this system would ever tell you a dependency is vulnerable

- **Severity**: P1 — a missing safety net, in a system where the owner has explicitly prioritised safety nets (2026-07-23 decision).
- **Observed**: `gh api repos/hyuntohoon/<repo>/dependabot/alerts` returns **`403 "Dependabot alerts are disabled for this repository"` for all six repos** (backend, front, music, worker, shared_db, workspace). No `pnpm audit` / `pip-audit` step exists in any CI workflow either.
- **Impact**: the advisories below accumulated with **zero** signal. `astro` is 9 advisories and two major versions behind; `@astrojs/rss` has a live XML-injection advisory against an endpoint that serves 200 in prod. Neither would ever surface.
- **Fix is trivial**: enabling Dependabot alerts is a repo setting, not code. Whether to also enable *automatic PRs* is a separate call. → §7.

### DEP-2 (P2): `@astrojs/rss` is behind a patch fix for XML injection, and `/rss.xml` is live

- **Where**: `myblog_front` → `@astrojs/rss@4.0.13`
- **Advisory**: `GHSA-8j5q-mfj2-5q9q` / **CVE-2026-59728** — *XML Injection via Unescaped RSS Feed Fields* (MODERATE). Fixed in **4.0.19**; latest is also 4.0.19.
- ⚠️ **DOWNGRADED to version hygiene — NOT applicable. See §9 (C-4).** The original text below claimed applicability was confirmed; re-verification overturned it:
  - `src/pages/rss.xml.ts` populates only `title`, `description`, and `customData`. The advisory's two vulnerable fields — **`source.title` and `enclosure.type` — are never set.**
  - The feed currently emits **zero items** (no published reviews), and the route is prerendered static.
  - So there is no exploitable path today. Bumping `4.0.13 → 4.0.19` is still worth doing as hygiene (it is a patch inside the same minor), but it is **not a security fix** and should not be prioritised as one.
- What does hold: `https://www.ratemymusic.blog/rss.xml` returns **200** and is a real prerendered route, so the *package* is genuinely in use.

### DEP-3 (P2): `@astrojs/node` is declared as a dependency but the project never uses it

- **Where**: `myblog_front/package.json:21` `"@astrojs/node": "^9.5.1"`
- **Observed**: `astro.config.ts:38` sets **`output: 'static'`** and declares **no `adapter:`**. `@astrojs/node` appears **nowhere** in `src/` or in the config — its only occurrence in the repo is that package.json line.
- **Impact**: it contributes **6 advisories** (SSRF via Host header, Server Islands / Server Actions memory-exhaustion DoS, cache poisoning, …) that are attributed to this project for a package it does not run. Every future scan and every future Dependabot alert will re-raise them.
- **All 6 are non-applicable** — they need a running Node SSR server, which this deployment does not have. **Deleting the dependency removes them permanently** and changes no behaviour.

### Astro core — a real decision, not a quick fix (→ §7)

`astro@5.15.9` carries **9 advisories (2 HIGH, 4 MODERATE, 3 LOW)**. Latest is **7.1.3** — two majors ahead — and some fixes only land in 7.x. So this is a framework upgrade, not a bump.

Triaged against what this site actually does, rather than pasted as a list:

| Advisory class | Applies here? | Basis |
|---|---|---|
| Server Islands replay / DoS | **No** | `grep server:defer` → **0 hits** |
| Host-header SSRF in error-page fetch, `matchPathname` allowlist bypass | **No** | needs a running SSR server; `output: 'static'`, no adapter |
| Reflected XSS via unescaped **slot name** (HIGH) | **Unlikely** | "reflected" needs request-derived input; slot names here are author-written (2 uses) |
| XSS via `define:vars` incomplete `</script>` sanitisation (MODERATE) | **Possibly** | `define:vars` **is used** (2 sites) and ships to the browser |
| XSS via unescaped **View Transition** animation properties / `transition:*` on hydrated islands (MODERATE + LOW) | **Possibly** | `transition:*` used in **4 files**, `ViewTransitions`/`ClientRouter` in **12** — client-side, so static output does not protect |

**Honest limit**: whether those three are *exploitable here* depends on whether attacker-controlled data reaches those exact spots, which I did not trace end-to-end. They are the three worth reading the advisories for; the other six are ruled out structurally.

### Python side — runs inside the Lambdas, so applicability is real

Eight HIGH-severity packages, all present in **both** backend and music:

| Package | Advisory | Note |
|---|---|---|
| `starlette@1.1.0` | `CVE-2026-54283` — `request.form()` limits silently ignored for `x-www-form-urlencoded` → DoS | **Look at this one first.** Starlette is FastAPI's request layer, so it sits directly in the path of every request both services take. |
| `cryptography@48.0.0` | `GHSA-537c-gmf6-5ccf` — vulnerable OpenSSL bundled in the wheels | transitive; fix is a wheel bump |
| `pyasn1@0.6.3` | `CVE-2026-59885/59886` — quadratic complexity + resource exhaustion in OID / REAL decoding | reached only via ASN.1 parsing (JWT/cert paths) |
| `ecdsa@0.19.2` | `CVE-2024-23342` — Minerva timing attack on P-256 | pulled in by the JWT stack; Cognito uses RS256, so P-256 is likely never exercised — **unverified** |

**Not adjudicated**: I did not trace call paths for the Python items. `starlette` is called out because it is unambiguously in the request path; the rest need a look before anyone spends effort on them.

### Related observation (not adopted as a finding)

`SQLAlchemy==2.*` and `psycopg[binary]==3.*` are **open major-range pins**. Each deploy resolves them fresh, so a new minor can change prod behaviour with no code change and no review. Same family as the already-logged C-10 *"backend pins a moving untagged SHA"* (`architecture.md:254`). No harm observed, so it stays an observation — but if the owner ever fixes C-10, these belong in the same pass.

---

## 9. Re-review corrections (2026-07-26 ~10:30–11:30 KST, owner-requested)

Five independent verifier agents re-checked this report and its 12 commits, deliberately trying to break it. The judge and synthesis stages died on the session cap, so **every correction below was re-verified by hand in the main loop** — none is taken on an agent's word.

**Verdict: the audit holds up in substance — all 16 findings survive as real — but it carried more factual error than it should have.** 14 claims needed correcting and 5 new findings were missed. The pattern in the errors is consistent and worth naming: **the audit repeatedly stated a narrow measurement as a general truth** (one warm page load → "98.3 % of bytes"; four probed routes → "row-scoping isolates"; one Lighthouse run → a single CLS number; one plan.md copy → "accurate and current").

### 9.1 Corrections — claims that were wrong

| # | Section | Was | Is | Changes a fix decision? |
|---|---|---|---|---|
| C-1 | §4 outstanding | "`worker-isrc-backfill` rule is still un-applied (absent from the 14 rules)" | **Applied and ENABLED**, `cron(0 21 ? * SUN *)`. There are **15** rules, not 14. Verified: `aws events list-rules`. Item deleted. | yes — closed a non-issue |
| C-2 | §4 healthy | "`docs/plan.md` is accurate and current (84 lines) … no stale rows" | Assessed against a copy **3 commits behind `origin/main`**. `origin/main` is at 90 lines; the `worker-isrc-backfill` owner-action row is superseded by ws #699/#701. **The claim is withdrawn** — plan.md was never checked against current `origin/main`. | yes |
| C-3 | §4 D-1 | "It had never had a draft to deliver before … 07-25 was the first night the pipeline generated a review" | **False, and the truth is worse.** Delivery **worked twice**: `2026-06-23` (`1 draft(s) created, 1 memo(s) grown`) and `2026-07-05`. It was **broken by a known PR** — `392dd50` "feat(auth): owner-gate single-owner routes before self-signup opens the pool (#107)", **2026-07-08** — which added `require_owner` to `POST /api/posts`. The next draft was not produced until 07-25, so the regression sat invisible for **17 days**. | **yes — D-1 is a regression with a named cause, not an unfinished feature** |
| C-4 | §8 DEP-2 | "Applicability confirmed … feed fields are built from post titles … exactly the shape this advisory is about" | **Not applicable.** `src/pages/rss.xml.ts` populates only `title`, `description`, `customData`. The advisory's vulnerable fields — `source.title` and `enclosure.type` — are **never set**. The feed also currently emits **zero items**, and the route is prerendered static. **DEP-2 downgrades to version hygiene.** | **yes — removes a recommended fix** |
| C-5 | §5 E-1 | "**98.3 %** of the entire homepage's bytes" | That is a **warm repeat visit** figure — every other asset came from cache in that measurement. On a **cold first visit** the page is ~2.0 MB, so the genre tree is **~14 %** of it. Both numbers are true of different visits; quoting only the larger one was misleading. The real finding — **~292 KB gzip / 742 KB decoded on *every* visit, uncacheable** — survives untouched. | no (finding stands) |
| C-6 | §5 E-1 | "Stripping `definition_md` drops the payload 773,644 → 246,085 bytes (−68 %)" | Wrong decomposition. Stripping definitions gives **741,895 → 475,305 B (−36 %)**. The largest single unused chunk is the **2,064-entry `edges` array (~246 KB)**, which `/` never reads at all. | **yes — points the fix at `edges`, not the markdown** |
| C-7 | §5 E-3 | "CLS 0.315 — three times the 'poor' threshold" | Two errors. (a) 0.315 is *above* the 0.25 poor threshold, ~3× the **0.10 good** threshold. (b) It is one run of a spread: cold first-visit CLS measures **0.14–0.32 run-to-run**. Report the range, not the maximum. | no (finding stands) |
| C-8 | §1, §2 | "all three config gates (`COGNITO_USER_POOL_ID`, `EDGE_SECRET`, `OWNER_SUB`) fail closed **in both**" | `EDGE_SECRET` and `OWNER_SUB` **do not exist in `myblog_music` at all** (no edge layer, no owner-gated route). Only `COGNITO_USER_POOL_ID` is shared, and it does fail closed identically. The behavioural-equivalence core of the claim holds; the "all three, in both" phrasing was false. | no |
| C-9 | §1 | "Unsorted bulk `ON CONFLICT` — the two unsorted ones are single-owner jobs with no constructible deadlock interleaving" | **False.** Inside the high-concurrency album-sync path itself, `album_artists` (`sync_service.py:192`) and `track_artists` (`:230`) insert **unsorted** pair lists, while their three siblings in the *same function* sort explicitly and carry comments saying sorting is required for concurrency safety (`:135`, `:152`, `:202`). They are `DO NOTHING` rather than `DO UPDATE`, so the deadlock risk is lower than A-1's — but "two, both single-owner" was wrong. | yes — widens A-1's neighbourhood |
| C-10 | §6b | "**Multi-user row-scoping genuinely isolates.**" | Overstated from a 4-route sample. Correct statement: *the four member-scoped routes probed (`stream-history/clock`, `stream-history/top-artists`, `/api/me/release-feed`, `/api/integrations`) correctly return empty results to a non-owner.* No general isolation claim is supported. | no |
| C-11 | §5 E-5 | "`write.astro` and `WriterApp.tsx` contain no owner check" — scoped to `/write/` | True but **too narrow**: `src/pages/drafts.astro` is **also ungated** (no owner check, no redirect). E-5 must be scoped to the owner-only runtime surfaces as a class, or the recommended §7-a fix leaves a hole. | **yes — a fix scoped to `/write/` alone is incomplete** |
| C-12 | §2 | "backend source declares 70 paths"; "the 43 code routes that appear unwired" | **72** and **44**. Independent re-enumeration via live FastAPI `app.routes` introspection. Both substantive conclusions are unaffected: 0 backend routes missing from the merged spec, 0 mutations missing from `apigateway.tf`. | no |
| C-13 | §6 | "every finding is either directly measured on production or independently verified — none rests on a single unchecked inference" | Written before §8 existed. **DEP-1/2/3 partly rest on untraced applicability**, as §8 itself admits. Scope the sentence to the 13 pre-§8 findings. | no |
| C-14 | header | "docs-only, no code changes" | Precisely: no service code or infra changed, but the branch **adds one new script**, `docs/reviews/audit-2026-07-26-raw/osv_scan.py`. If it is meant to be re-runnable (DEP-1 implies it), it belongs under `tools/`, not in a dated audit directory. | no |

### 9.2 New findings the audit missed

**PUB-1 (P1, process — read this before merging anything)**

`myblog-workspace`, `myblog_backend`, `myblog_front`, `myblog_music`, `myblog_worker` are all **PUBLIC** on GitHub (only `myblog_shared_db` is private). Verified via `gh repo view`.

Merging this report therefore **publishes a working exploitation guide for defects that are still live**: A-3's exact 500-producing URL, E-5/C-11's ungated `/write/` and `/drafts/` surfaces, D-1's auth gap, and the exact vulnerable dependency versions from §8. The audit treated "docs only" as the whole risk statement and never considered publication. → **§7 decision.**

**OPS-1 (P1): the "all worker crons are alarmed" guarantee silently regressed, and nothing can notice**

`infra/monitoring.tf:106-120` defines `local.worker_cron_rules` as a **hardcoded 12-entry map**, consumed by `for_each` on `cron_failed_invocations`. `worker-isrc-backfill` was added to `eventbridge.tf` as a 13th worker cron but **never added to that map**.

- Live: **12** `*-failed-invocations` alarms exist; **13** worker crons run. `worker-isrc-backfill` is the only one uncovered.
- The comment right above the map reads *"OPS-delivery-safety-gates Step 4: extended from 2 rules to ALL worker crons (audit O-4 — 10 of ~12 rules were uncovered)"*. That guarantee is now false again, by the identical shape of gap the RFC was written to close.
- **Harm**: an EventBridge delivery failure on the weekly ISRC job — the one job whose schedule fires rarely enough that nobody would notice by eye — raises no alarm.
- **Root cause worth fixing over the symptom**: a hand-maintained list can drift from the rules it is meant to cover. Deriving the map from the rule resources removes the whole class.

**SEC-1 (P1): the CloudFront WAF has zero rules and defaults to Allow**

`aws wafv2 get-web-acl --scope CLOUDFRONT` on the attached ACL `CreatedByCloudFront-72420c9a` returns `RuleCount: 0`, `Rules: []`, `DefaultAction: {Allow: {}}`. It is attached and it does **nothing**.

`infra/README.md:52` documents this ACL as a real control ("console-created; its rules are invisible to `plan`"), so the documented abuse posture rests on an empty shell. Combined with there being no rate limiting found on the public API surface, the effective bound on abuse of the unauthenticated endpoints is Lambda concurrency and the bill. → **§7 decision** (add managed rules, or delete the ACL and stop claiming it).

**SEC-2 (P2): every missing config fails closed except the one that disables all of them**

`ENV: str = "local"` is the default in **both** `myblog_backend/app/core/config.py:19` and `myblog_music/app/core/config.py:14`. `require_cognito_token` and `require_owner` both short-circuit and return early when `ENV in ("local", "dev")`.

So: a missing `COGNITO_USER_POOL_ID` → **503** (fail closed, as designed). A missing **`ENV`** → **auth disabled entirely**, silently, on both services. Prod currently sets `ENV=prod` on both Lambdas (verified), so this is latent, not live — but the entire fail-closed posture rests on one env var whose *absence* means "trust everyone", which inverts the project's own hardening rule. Leg A's claim *"no path was found where missing config yields an allowed request"* is therefore false.

**E-6 (P2): the `member.css` dashboard-only trap has recurred a 4th time — live-verified**

- `.lf-artist-link` is defined only in `src/styles/member/layout.css:971`, reachable only through `@styles/member.css`, which is imported by exactly **two pages**: `collection.astro:10` and `settings.astro:6`. `member.css:16` even states *"member.css never loads outside the dashboard."*
- But `AlbumDetailView.tsx:94` emits `className="lf-artist-link"`, and `AlbumOverlay` is mounted from **`src/layouts/layout.astro`** — i.e. **every page on the site**.
- **Verified live on the production homepage**: the rule is absent from all 5 loaded stylesheets, yet the element renders — `<a class="lf-artist-link">Ludwig Göransson</a>` — with computed `text-decoration: none`, `border-bottom: 0px solid`, `font-weight: 400`.
- **User-visible effect**: artist names inside the album overlay get **no hover affordance anywhere except `/collection/` and `/settings/`** — no colour change, no underline — so they do not look clickable, even though they navigate to the artist hub. On those two pages the identical link highlights on hover.
- §3 called this class clean. **That verdict is withdrawn.**

### 9.3 Re-verified as correct (the main product of a re-review)

Independently redone with different methods and confirmed:

- **Route ↔ API Gateway parity** — re-enumerated via live FastAPI `app.routes` + dependency-graph introspection instead of regex. **43 mutation routes, 0 missing from `apigateway.tf`, 48 `route_key`s.** Holds.
- **OpenAPI contract** — 0 backend routes absent from the merged spec. Holds.
- **Canonical schema pair** — `docs/contracts/schema.sql` vs `myblog_shared_db/tests/canonical_schema.sql` byte-identical, confirmed by sha256. Holds.
- **shared_db pin safety** — re-tested by importing from each service's own venv. Every symbol music and worker use exists at `v0.26.0`. Holds.
- **No cross-service imports.** Holds.
- **Auth-guard behavioural equivalence** — both `auth.py` files read end to end and all eight paths walked (missing config, absent/malformed/expired token, JWKS failure, unknown kid, wrong issuer, wrong `token_use`). **No path where one service allows what the other rejects.** Holds (with C-8's phrasing fix).
- **Zero outbound HTTP without an explicit timeout.** Holds.
- **No secrets logged or leaked.** Holds.
- **`/api/music/search/unified` is DB-only** (hard rule #9). Holds.
- **A-1, A-2, A-3, A-4, A-5, D-1, D-2, D-3, E-1, E-2, E-3, E-4, E-5, DEP-1, DEP-3 all survive** as real defects. Only DEP-2's *applicability* was overturned.
- **Commits are clean on hard rule #2**: all 14 unique blobs the branch introduces were extracted and searched — **zero JWTs, zero `Bearer` tokens, zero AWS/GitHub keys, zero connection strings, zero private keys.** Every `password`/`secret`/`DATABASE_URL` hit is prose in the report. The minted token never entered git.
- **Docs-only held**: per-commit inspection confirms every commit touches only `docs/` (the `git diff origin/main..HEAD` appearance of `infra/eventbridge.tf` and `scripts/album_research_v4.md` changes is the branch being 3 commits *behind*, not changes made here).
- **Nothing was pushed**; no PR exists; rule #1 honoured throughout.

### 9.4 Still not covered, after the re-review

The completeness critic named surfaces this audit never opened, and they remain open: **`infra/` beyond apigateway/eventbridge/lambda/monitoring** (IAM policy scope, S3 bucket policies, CloudFront behaviours, KMS, Cognito settings), **all six GitHub Actions workflow files** (secrets handling, injection via PR title, `permissions:` scope), **`tools/` and the non-buckit `scripts/`**, **frontend server-side code** (`.astro` frontmatter, `src/pages/**/*.ts` endpoints), **PWA/service-worker config**, and **escaping of member-supplied content** (bucket notes, reviews, display names) at every render site. Also still open from §6b: load/concurrency testing, DB-level data quality, Terraform state, and call-path tracing for the Python CVEs.

One unadopted lead worth recording: `MetricsBatchRequest.slugs` is the only unauthenticated, unbounded-collection input in the system and carries no `max_items`/`max_length`. No DoS was demonstrated, so it is not a finding — but it is where to look first if abuse protection is ever revisited.

---

## 7. Questions for the owner

결정이 필요한 항목들입니다. 코드는 아직 하나도 안 건드렸습니다.

**0. PUB-1 — 이 문서를 머지하기 전에 먼저 정해야 합니다 (§9.2).**
`myblog-workspace`와 서비스 리포 4개가 **전부 PUBLIC**입니다 (`myblog_shared_db`만 private). 이 문서를 머지하면 **아직 안 고친 결함의 재현 방법이 그대로 공개**됩니다 — A-3의 500 나는 URL, E-5/`drafts.astro`의 무방비 화면, D-1의 인증 공백, §8의 정확한 취약 버전까지.
   - (a) **먼저 고치고 머지** — A-3·E-5·DEP-3은 다 작은 수정입니다. **추천.**
   - (b) URL·버전을 가린 요약본만 머지하고 전체는 로컬에 보관
   - (c) 리포를 private으로 전환
   - (d) 그대로 머지 (개인 블로그이고 위험이 낮다고 판단하면)
   저는 (a)를 추천하지만, 이건 사장님 판단입니다.


**1. D-1 (P0) — 나이틀리가 만든 초안이 블로그에 못 올라가는 문제, 어떻게 뚫을까요?**
파이프라인이 smoke 테스트 계정으로 로그인하는데, `POST /api/posts`는 오너 본인만 통과시킵니다. 선택지 세 가지:
   - (a) 파이프라인에 오너 자격증명을 주기 — 제일 빠르지만, 자동화 스크립트가 "무엇이든 발행·수정·삭제 가능한" 권한을 갖게 됩니다.
   - (b) 서비스 전용 신원을 만들어 `require_owner`가 인정하게 하기 — 가장 깔끔하지만 인증 코드를 손대야 합니다(= 반복 버그 구역).
   - (c) `status:'draft'` 생성에 한해 게이트를 완화하기 — 범위는 좁지만 공개 경로에 새 구멍이 생깁니다.
   추천은 **(b)**. 다만 인증 변경이라 별도 세션에서 신중히 해야 합니다.

**2. E-1 (P1) — 홈 장르 막대 6개를 위해 742KB를 받는 문제, 어디를 고칠까요?**
   - (a) 홈 전용 경량 응답(tier-0의 `slug/label/album_count`만) — 약 99% 감소.
   - (b) 기존 엔드포인트에 `?depth=0` 같은 파라미터 추가 — "album_count 소스는 하나" 원칙을 유지.
   - (c) 일단 `cache-control` 헤더만 붙이기 — 한 줄이고, 형제 엔드포인트와 일관되며, 재방문 비용이 사라짐.
   추천은 **(c)를 즉시 + (b)를 뒤이어**. (c)만으로도 첫 방문 외 비용은 사라집니다.

**3. E-3 (P1) — 첫 방문 모바일에서 화면이 튀는 문제(CLS 0.315), 지금 잡을까요?**
   섹션들에 최소 높이만 잡아주면 되는 종류입니다. E-1과 원인을 공유하니 같이 처리하는 게 효율적입니다. 같이 갈까요, 아니면 E-1만 먼저?

**4. E-2 — 공개 컬렉션 페이지의 `@user-0468fd3c` 표기, 어떻게 할까요?**
   (a) 표시 이름을 필수로 받기 / (b) 이름 없으면 중립적인 라벨로 보여주기 / (c) 그대로 두기.
   참고로 저 값은 오너 본인의 Cognito sub 앞자리입니다.

**5. 홈 하단 "0편 평론 / 0개 장르" — 의도한 표시가 맞나요?**
   바로 위 섹션은 "4,479장 · 13개 장르"라고 말하고 있어서, 처음 온 사람에겐 모순으로 읽힙니다. 저 "장르"가 *평론이 달린 장르 수*를 뜻하는 거라면 숫자는 맞습니다 — 라벨만 바꾸면 될지, 아니면 그대로 둘지 결정해 주세요.

**6. D-3 — 3주째 매번 실패하는 "Notify workspace" 워크플로, 끌까요?**
   이미 죽은 경로로 문서화돼 있고 수동 절차가 대체했습니다. (a) 비활성화/삭제 / (b) 401 원인을 고쳐 되살리기.
   추천은 **(a)**. 지금은 정상 배포에 빨간 X만 붙이고 있어서, 진짜 실패를 놓치게 만듭니다.

**7-a. E-5 — `/write/` 에디터가 일반 회원에게 다 열리는 문제 (심화 패스에서 추가 발견)**
   데이터 위험은 없습니다(서버가 제대로 막습니다). 다만 회원이 평론을 다 쓰고 발행을 누른 뒤에야 막힙니다.
   프론트에 이미 `isOwnerUser()`가 있고 다른 화면 3곳에는 적용돼 있으니, `/write/`에도 같은 걸 붙이면 됩니다.
   (a) 오너 아니면 페이지 자체를 리다이렉트 / (b) 에디터는 두되 발행 버튼만 숨기기 / (c) 그대로 두기.
   추천은 **(a)**.

**7-b. 의존성 취약점 (§8) — 어디까지 하실래요?**
   - **Dependabot 켜기** (DEP-1): 리포 설정만 바꾸면 되고 코드 변경 0건입니다. 알림만 받을지, 자동 PR까지 받을지는 따로 정하셔야 합니다. **추천: 알림만 먼저.**
   - **`@astrojs/rss` 4.0.13 → 4.0.19** (DEP-2): 같은 마이너 안의 패치입니다. `/rss.xml`이 실제로 돌아가고 있고, 피드에 들어가는 제목이 Spotify에서 온 앨범·아티스트 이름이라 딱 이 취약점이 말하는 모양입니다. **이번 감사에서 제일 싼 실제 수정.**
   - **`@astrojs/node` 삭제** (DEP-3): 안 쓰는 패키지인데 권고문 6건을 계속 달고 다닙니다. 지우면 동작 변화 없이 6건이 사라집니다.
   - **Astro 5.15.9 → 7.x**: 이건 메이저 2단계 업그레이드라 별건입니다. 9건 중 6건은 SSR 전용이라 이 사이트엔 해당 없고, `define:vars`·View Transition 관련 3건만 실제로 볼 필요가 있습니다. 지금 할지, 권고문 3건만 먼저 읽고 판단할지 정해 주세요. **추천: 3건 먼저 읽기.**
   - **`starlette` (Python)**: FastAPI의 요청 처리 계층이라 백엔드·뮤직 양쪽 모든 요청 경로에 있습니다. Python 쪽에서 제일 먼저 볼 것.

**7-c. 재검토에서 새로 나온 것 4가지 (§9.2)**
   - **OPS-1 (P1)** — `worker-isrc-backfill`에 실패 알람이 없습니다. `monitoring.tf`의 워커 크론 목록이 **손으로 관리하는 12개 하드코딩 맵**이라, 13번째가 추가되면서 조용히 빠졌습니다. OPS RFC가 "모든 워커 크론"을 보장한다고 적어둔 게 다시 깨진 겁니다.
     (a) 맵에 한 줄 추가 / (b) **규칙 리소스에서 맵을 자동 도출**해서 이 문제 유형 자체를 없애기. **추천: (b)** — 같은 사고가 세 번째입니다.
   - **SEC-1 (P1)** — CloudFront에 붙은 WAF가 **규칙 0개 + 기본 Allow**입니다. `infra/README.md:52`는 이걸 실제 보호 장치처럼 적어놨는데 아무 일도 안 합니다.
     (a) AWS 관리형 규칙 붙이기 / (b) ACL을 지우고 문서에서 빼기(있는 척 안 하기). **둘 중 하나는 해야 합니다.**
   - **SEC-2 (P2)** — `ENV`가 두 서비스 모두 기본값 `"local"`이고, `local|dev`면 인증 가드가 통째로 꺼집니다. 다른 설정은 없으면 503(fail-closed)인데 **`ENV`만 없으면 fail-open**입니다. 지금은 Terraform이 `ENV=prod`를 넣어주고 있어서 잠재적입니다.
     기본값을 `prod`로 바꾸거나, 로컬 우회를 별도 플래그로 분리하는 게 맞습니다.
   - **E-6 (P2)** — `member.css` 함정 **4번째 재발**. 앨범 오버레이의 아티스트 이름이 `/collection/`·`/settings/` 밖에서는 hover 반응이 없습니다(클릭 가능해 보이지 않음). 프로덕션에서 직접 확인했습니다.

**7. 21건의 처리 순서 — 어떻게 갈까요?**
   추천 순서: **PUB-1 결정 → D-1 → A-2 → SEC-1+OPS-1 → A-3·E-5·DEP-3(작고 독립적, 공개 리스크도 같이 줄임) → E-1+E-3 → A-1 → 나머지 P2**.
   DEP-2는 보안 수정이 아니라 위생 작업으로 내려갔으니 급하지 않습니다.
   근거: D-1은 서비스의 존재 이유가 막혀 있고, A-2는 앨범 제목 하나로 전체 배포가 멈출 수 있으며, E-1/E-3은 모든 방문자가 매번 지불하고, A-1은 아직 터지지 않았지만(DLQ 0건) 터지면 조용히 DLQ로 샙니다.
