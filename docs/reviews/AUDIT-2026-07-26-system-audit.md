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
| B | Architecture audit (service boundaries, sync-Spotify rule, contract/OpenAPI drift, shared_db pin drift, infra↔code drift) | **INCOMPLETE — restart** — killed by the session limit before writing anything. Its only partial signal: "contract chain clean", **unverified, do not adopt**. Remaining: twin drift, boundary checks, route↔apigateway diff, shared_db pin drift, schema mirror diff | §2 |
| C | Frontend code audit (islands, CSS scoping traps, api.gen.ts drift, auth/token handling, error/empty states) | **NOT STARTED — restart** — killed by the session limit before reading anything | §3 |
| D | Functional audit (plan.md open items vs reality, launchd pipeline health, DLQ/queue state, prod smoke) | **INCOMPLETE — restart** — killed by the session limit before writing anything. Partial signal: "key signal found in the nightly log", **content unknown**. Re-check the launchd pipeline logs first | §4 |
| E | UI/UX live verification via CDP on production (desktop + mobile emulation, console errors, key flows) | IN PROGRESS — logged-out public surface swept (home / reviews / genres / canon / collection / artist, at 1440px and 390px mobile). Remaining: Lighthouse numbers, authed `/members/` surface | §5 |
| F | Necessity-gate pass — refute every candidate finding, drop unproven ones | PENDING | §6 |
| G | Final write-up + plan.md candidate rows + owner feedback questions | PENDING | §6, §7 |

**Raw agent output / intermediate notes**: `docs/reviews/audit-2026-07-26-raw/` (gitignored-by-intent; delete before commit if noisy)

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

_(pending)_

## 3. Frontend code — findings

_(pending)_

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
  1. **It had never had a draft to deliver before.** Every run from 07-11 to 07-24 logged `0 draft(s) created, 0 memo(s) grown, 0 skipped/failed` — which reads as healthy but actually means "nothing was produced". 07-25 was the first night the pipeline generated a review, and it failed on delivery.
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

### Verified healthy / observed (leg D, partial)

- **All 5 launchd agents are loaded**: `com.myblog.research-poller`, `com.myblog.lyrics-translate-poller`, `com.myblog.buckit-nightly`, `com.myblog.genre-backfill`, `com.myblog.genre-heal-poller`. Last exit status 0 for all except `buckit-nightly` (1, = D-2 tonight). This is **not** a repeat of the "reboot drops the agents" trap — they are genuinely loaded.
- **Nightly run history is continuous except one known gap**: runs present for 07-11…07-20, then **07-21 / 07-22 / 07-23 missing entirely** (no start line at all), then 07-24 / 07-25 / 07-26 present. That 3-night gap is the already-documented 07-20 reboot incident, not a new fault — **not re-reported.**
- **Draft generation itself is reliable**: 15 successful `claude -p` runs, 50–92 s typical (one 918 s outlier on 07-20), consistent token counts.

### Still outstanding in leg D (do these on resume)

- SQS queue + DLQ depths (`get-queue-attributes` on every queue — any non-zero DLQ is a finding)
- Lambda recent ERROR lines for `ratemymusic-api`, `musicApi`, `blogWorkerLambda` (24–48 h window; remember prod runs `LOG_LEVEL=WARNING`, so absent INFO is normal)
- EventBridge rules: enabled/disabled, and any rule targeting a dead Lambda
- Open PRs + recent deploy runs across the 4 repos (`gh ... --repo` explicitly)
- `docs/plan.md` open rows vs reality (shipped-but-not-dropped, and regression re-adds)

## 5. UI/UX (live production) — findings

Production site: `https://www.ratemymusic.blog` (CloudFront `E2Q2JH5EAYVU1O`). Verified logged-out, read-only, via CDP.
Swept 2026-07-26 ~02:45–03:00 KST at 1440×900 desktop and 390×844×3 mobile+touch emulation.

### E-1: The homepage downloads a 742 KB genre tree (292 KB over the wire) to draw six bars, and it is uncacheable

- **Severity**: P1 — every visitor, every visit, including repeat visits and mobile data.
- **Where**: homepage `/` → `GET /api/genres/tree` (backend route; the frontend genre-distribution module on `/`)
- **Measured on production (mobile emulation, 390×844)**:
  - Homepage total network transfer: **296,971 bytes across 77 resources**
  - `/api/genres/tree` alone: **291,928 bytes transferred / 741,895 bytes decoded / 1,257 ms**
  - → **98.3 % of the entire homepage's bytes is this one API call.** All JS/CSS/font/image resources together were served from cache (0 transfer); this call cannot be.
- **Why it cannot be cached**: the response carries **no `cache-control` header at all**, so CloudFront never stores it —
  repeated `curl` shows `x-cache: Miss from cloudfront` every time, TTFB 0.75–1.3 s.
  The two sibling homepage endpoints DO set it and DO cache:
  - `/api/music/albums/on-this-day` → `cache-control: public, max-age=60, stale-while-revalidate=60` → 2nd request `x-cache: Hit from cloudfront, age: 19`
  - `/api/music/feed/new-releases` → same header, same behaviour
  So this is header **drift between sibling endpoints**, not a deliberate freshness choice.
- **What the payload actually contains**: 1,230 genre nodes, 5 levels deep (13 / 247 / 779 / 179 / 12 per level),
  including the full `definition_md` markdown body of every node — **120,774 bytes of markdown prose**.
  Stripping only `definition_md` drops the payload from 773,644 → 246,085 bytes (-68 %).
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

### E-3: First-visit mobile CLS is 0.315 — three times the "poor" threshold — because homepage sections mount with no reserved height

- **Severity**: P1 — affects every first-time visitor; content jumps under the reader's thumb.
- **Where**: homepage `/` — the "오늘, 이 앨범들" rail, the "장르로 탐색" distribution module, and the new-releases `hstrip`.
- **Measured**:
  - **Lighthouse, mobile navigation, cold profile: CLS = 0.315.** Google's thresholds: good ≤ 0.10, poor > 0.25.
  - Independent reproduction in a fresh isolated browser context (no service worker: `navigator.serviceWorker.controller === null`), 390×844×3, Slow 4G: **CLS = 0.1405 over 6 shifts**.
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

_(pending)_

## 7. Questions for the owner

_(pending)_
