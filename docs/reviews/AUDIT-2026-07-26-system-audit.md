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
| A | Backend/music/worker code audit (recurring bug classes: fail-closed guards, session lifecycle, upsert sort, HTTP timeouts, twin drift) | PENDING | §1 |
| B | Architecture audit (service boundaries, sync-Spotify rule, contract/OpenAPI drift, shared_db pin drift, infra↔code drift) | PENDING | §2 |
| C | Frontend code audit (islands, CSS scoping traps, api.gen.ts drift, auth/token handling, error/empty states) | PENDING | §3 |
| D | Functional audit (plan.md open items vs reality, launchd pipeline health, DLQ/queue state, prod smoke) | PENDING | §4 |
| E | UI/UX live verification via CDP on production (desktop + mobile emulation, console errors, key flows) | IN PROGRESS — logged-out public surface swept (home / reviews / genres / canon / collection / artist, at 1440px and 390px mobile). Remaining: Lighthouse numbers, authed `/members/` surface | §5 |
| F | Necessity-gate pass — refute every candidate finding, drop unproven ones | PENDING | §6 |
| G | Final write-up + plan.md candidate rows + owner feedback questions | PENDING | §6, §7 |

**Raw agent output / intermediate notes**: `docs/reviews/audit-2026-07-26-raw/` (gitignored-by-intent; delete before commit if noisy)

---

## 1. Backend / music / worker code — findings

_(pending)_

## 2. Architecture — findings

_(pending)_

## 3. Frontend code — findings

_(pending)_

## 4. Functional / operational — findings

_(pending)_

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

### Checked and clean (live, logged-out)

- **Console**: zero `error` and zero `warn` messages on `/`, `/reviews/`, `/genres/`, `/canon/`, `/collection/`, `/artist/<id>/`. This is unusually clean.
- **Trailing-slash routing**: both `/reviews` and `/reviews/` (and genres/canon/collection) return **200, no redirect** — header links use the trailing slash, footer links omit it, and both work. Not a finding.
- **Mobile horizontal overflow**: none. `scrollWidth === clientWidth === 390` on the homepage. Elements extending past 390 px are all inside intentional horizontal scroll rails (`nrl-card`) or the off-canvas drawer (`hdr-drawer`, negative offsets) — correct, not overflow.
- **Broken images**: none found on `/`, `/genres/`, `/collection/` (46 covers), `/artist/<id>/` (15 covers).
- **Empty states**: `/reviews/` ("아직 리뷰가 없습니다"), `/canon/` ("아직 명반이 없습니다" + explanation of the ★4.0 rule), artist page ("아직 이 아티스트의 평론이 없습니다") all render deliberate, written empty states rather than blank regions or dead spinners.
- **Async discography**: artist page shows "불러오는 중…" then resolves to a populated catalog within 6 s — not a stuck spinner.

### Observed but NOT adopted as findings (necessity gate)

- **Homepage stat block reads "0편 평론 / 0개 장르 / — 최근 업데이트"** while the section directly above reports 4,479 catalogued albums across 13 genres. Consistent if "장르" means *genres that have a published review* (there are 0 reviews). Contradictory-looking to a reader, but no demonstrable harm and possibly intended. → **owner decision item (§7), not a defect.**
- **"첫 리뷰를 작성해 보세요" shown to logged-out visitors** on `/reviews/` — an owner-facing call to action on a public page. Cosmetic; no harm proven. → §7.
- **Tap targets under 44 px on mobile**: LOGIN button 38×29, header icon buttons 40×40. Below the 44 px HIG guideline but not demonstrably causing mis-taps. → dropped.
- **Duplicate "ICEMAN (2026 · ALBUM)" entries in Drake's discography** — this is release-noise in the catalog, already the subject of the tracked `DATA-release-noise` workstream. → **not re-reported as new.**

## 6. Necessity-gate verdicts

_(pending)_

## 7. Questions for the owner

_(pending)_
