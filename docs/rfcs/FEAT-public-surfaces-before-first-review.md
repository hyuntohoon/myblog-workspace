# FEAT-public-surfaces-before-first-review: Honest public pages while 0 평론 exist

- **Status**: draft
- **Owner**: owner
- **Created**: 2026-10-17
- **Plan row**: `plan.md` → FEAT-public-surfaces-before-first-review
- **Source**: `docs/reviews/2026-10-16-front-uiux-audit.md` §3 step 1 (findings #1, #9, #18), owner decisions §4 (2026-10-17)

> **Decision boundary (read first).** This RFC deliberately does **not** reverse either earlier decision:
> - `FEAT-album-review-authoring` term table + success criterion 5 (owner 2026-07-31): 평가 is "즉시 공개되는 개인 기록. 편집 지면이 아니다" and must not mix into the editorial surfaces (평론 list / 평론 detail).
> - `FEAT-home-redesign` empty-state decision #4 (owner 2026-06-14): with 0 평론 the hero collapses to a single card; the owner publishes first.
>
> The owner chose (2026-10-17) to keep that line and add a **separately labelled** 평가 surface on home, instead of feeding Canon / the hero from ratings. Canon, the hero and `/reviews` stay 평론-only.

---

## Goal

A logged-out visitor on the production site no longer lands on three empty nav destinations, and home shows real owner activity, without any 평가 appearing on an editorial surface. Concretely: nav items whose destination is built from 평론 are hidden while the build has 0 평론 and reappear automatically on the deploy that publishes the first one; home gains a rail labelled as the owner's 평가 (stars + one-liner, linking to the member page) that stays current without a front deploy; the owner's public byline reads a real name instead of "U / @user-0468fd3c" / "이름 없는 회원".

## Non-goals

- Canon, home hero, `/reviews`, Best New Music fed from 평가 (owner declined 2026-10-17).
- Album URL / route, overlay Back handling (audit step 2; D2 decided "history state only" — separate work).
- Renaming the owner's `handle` or touching `OWNER_HANDLE` (`src/lib/member.ts:166`); the canonical member URL decision stays deferred (`FEAT-multi-user-accounts`).
- Copy/terminology sweep (#4, #10), card-contract work (S1–S5), visual batch (#11–13).
- Fixing the four pre-existing build-time fetches without a timeout (observation only).
- Any backend, contract, infra or migration change.

## Current state

Verified on front `origin/main` `f217e7a`, 2026-10-17.

- **Nav**: `src/components/header.astro:25-35` — static `navLinks`: Reviews `/reviews`, Genres, Best New Music `/reviews?bnm=1`, Canon `/canon`, Collection. `src/components/footer.astro:18` also links Canon.
- **평론 source**: build-time `getCollection('blog')` (`index.astro`, `canon.astro`, `reviews/index.astro`, …). `src/content` holds 0 `.mdx`. Publishing writes the `.mdx` to the front repo through the GitHub contents API (`myblog_backend/app/services/publish_service.py`), so the first publish triggers a front build.
- **Home**: `EditorialHome.tsx` `ColdStart()` renders "첫 평론을 준비 중 / 첫 평론이 이 자리에 실립니다" when there are 0 평론 (the 06-14 decision). The "0개 장르" figure (#18) is review-derived.
- **Canon**: `canon.astro` filters the blog collection by rating ≥ 4.0 → empty; its CTA leads to empty `/reviews`.
- **Owner ratings**: public `GET /api/members/user-0468fd3c` → 37 `reviews` (평가), 27 with rating ≥ 4.0; `display_name` is `"user-0468fd3c"`, so `isPlaceholderIdentity` is true and `publicMemberLabel` prints `ANON_MEMBER_LABEL` "이름 없는 회원".
- **Precedent for live data on a static home**: the 새 앨범 strip (`index.astro:60-85`, FIX-home-module-cls) — build-time seed with `AbortSignal.timeout(20_000)`, client re-fetch swapping in place.
- **No scheduled front rebuild exists** (`.github/workflows/main.yml`: push + PR only), so build-time-only data freezes until the next deploy.

## Target state

- Header and footer omit Reviews, Best New Music and Canon when the build-time 평론 count is 0; the routes stay reachable by URL and keep their (honest) empty states. With ≥ 1 평론 the nav is exactly today's.
- Home, below the cold-start card, has a rail headed as the owner's 평가 (wording uses 평가, never 리뷰/평론), showing the most recent N ratings as `AlbumCard`s via an adapter (stars + one-liner) and a link to the owner's member page. Seeded at build time with an explicit timeout, refreshed on the client like the 새 앨범 strip. Fetch failure → rail hidden, page unaffected.
- The "0개 장르" stat is hidden while it is 0 (#18).
- The owner's display name is set (owner action in `/settings`, handle unchanged) → bylines read the name.

## Steps

### Step 0 — owner sets a display name (owner action, no code)

In `/settings` set `display_name` only; leave `handle` as `user-0468fd3c` (changing it breaks `OWNER_HANDLE` and moves the owner's member page URL).

**Verification**: `curl -s https://www.ratemymusic.blog/api/members/user-0468fd3c | jq -r .display_name` ≠ `user-0468fd3c`; `/collection/` byline shows the name.

---

### Step 1 — hide 평론-built nav items while 0 평론 (front, one PR)

Compute the 평론 count once at build time (same `buildReviewCards` filter Canon/home use) and filter `navLinks` + the footer Canon link on it. Hide the "0개 장르" stat at 0. Unit test both branches (0 → hidden, 1 → today's nav); mutation-check that removing the filter turns it red.

**Verification**: `pnpm lint`, `pnpm exec astro check`, `pnpm test`; real-browser clickthrough desktop 1440 + mobile 390 (header, mobile drawer, footer); prod after deploy: header has Genres + Collection only, `/canon` and `/reviews` still 200.

**Rollback**: revert PR.

---

### Step 2 — home "owner's 평가" rail (front, one PR)

New home module fed by `GET /api/members/{OWNER_HANDLE}` (public, existing): build-time seed with explicit timeout, client refresh, hidden on failure or 0 items. Cards via a new adapter onto `shared/AlbumCard` (not another hand-rolled tile — audit S1). Album click opens the existing overlay. Copy reviewed against the 평가/평론 term table.

**Verification**: as Step 1, plus: rail renders 37-item data trimmed to N; offline API → rail absent and no console error; a new rating appears without a redeploy.

**Rollback**: revert PR.

## Open questions

1. **Rail size and placement** (N, above or below the 새 앨범 strip) — default: N = 8, directly under the cold-start card. Blocks Step 2 only; decided on the real screen.
2. **Does the rail stay after the first 평론?** Default: yes — it is a 평가 surface, independent of 평론 count. Blocks nothing now.

## Decisions log

| Date | Decision | Step |
|------|----------|------|
| 2026-10-17 | Owner (audit §4 D1): keep the 07-31 / 06-14 line; hide empty 평론 nav, add a separately labelled home 평가 rail; Canon/hero stay 평론-only | all |
| 2026-10-17 | Owner (audit §4 D3): audit step 1 first, RFC first | — |
| 2026-10-17 | #9 is fixed by `display_name` alone, not a handle change (verified: `isPlaceholderIdentity` keys on `display_name === handle`) | 0 |
