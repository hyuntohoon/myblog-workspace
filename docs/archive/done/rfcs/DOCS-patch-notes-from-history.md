# DOCS-patch-notes-from-history: Monthly patch notes on the site, written from merge history

- **Status**: **done** (2026-10-16 — Steps 1–2 shipped; archived). Owner approved the Status change
  in-session under CLAUDE.md rule #7. Last shipment: Step 1, `myblog_front#468` (`94bde96`, deploy run
  38883906906, prod `/updates/` 200 with 2 `<article>`).
- **Owner**: site owner
- **Created**: 2026-10-16
- **Plan row**: removed at close (Step 2). Monthly entries are routine work under `myblog_front/README.md` § 패치 노트.

---

## Goal

A public Korean `/updates/` page on buckit lists, month by month, the changes a visitor or member
could notice and why each was made. Nobody has to open a PR to learn what changed. Each month is one
Markdown entry, drafted from the merged PRs of the five service repos and the RFC records behind them,
and approved by the owner before it is published. The first release carries October 2026 in full and a
single condensed entry for July–September. A five-line procedure in `myblog_front/README.md` lets any
later session write the next month without this RFC.

## Non-goals

- **No per-PR process change.** No PR-template field, label, or commit trailer (see *Classification*).
- **No classifier script and no unattended publishing.** A `gh pr list` loop gathers the month's PRs.
  Deciding what is user-visible and writing the text stays human work: Claude drafts, the owner approves.
- **No notification surface.** No RSS item, e-mail, badge, or "new" dot. `rss.xml` stays reviews-only.
- **No owner-only changes in the public notes.** `/admin/*`, automation controls, CI, docs, research
  and dependency pins are excluded. Their history is already in `git log` and the RFCs.
- **No rewrite of the Matcher patch notes.** That table in `FEAT-lyrics-match-correction.md` stays the
  engineering record. A public entry may state its outcome in plain words.
- **No backend, DB, or contract change.**

## Current state

**Source material (measured 2026-10-16 on `origin/main`):**

| Repo | Commits since 2026-07-01 | of which `feat`/`fix` | Last 30 days |
|---|---|---|---|
| `myblog_front` | 267 | 187 | 22 |
| `myblog_backend` | 91 | 67 | 10 |
| `myblog_worker` | 59 | 43 | 11 |
| `myblog_shared_db` | 43 | 20 | 10 |
| `myblog_music` | 32 | 17 | 1 |

- Every service-repo commit in the last 30 days is a squash merge with a Conventional-Commit subject
  ending in `(#N)`, usually naming the plan ID and step.
- Subjects are English and written for engineers. The "why" lives in the PR body (`## What`) and in
  the RFC execution record.
- `feat`/`fix` does not mean "a member can see it". In the last 30 days, 5 of 8 `feat` commits on
  `myblog_backend` (#181–#184, #188) and 6 of 22 commits on `myblog_front` (#456–#459, #463, #467) are
  the owner-only automation page.
- The first curated per-feature log already exists: **Matcher patch notes** in
  `docs/rfcs/FEAT-lyrics-match-correction.md`.

**Audience (prod read, 2026-10-16):** `users` has **5 rows** (4 created 2026-07, 1 in 2026-09).

**Front:**

- The site is fully static (`astro.config.ts`: `output: 'static'`). There is no changelog or updates
  page.
- `src/content.config.ts` defines one collection, `blog`, as a `glob` over `./content/blog/**/*.mdx`.
- **`content/blog/` is machine-written:** the backend publish path PUTs MDX files straight to `main`
  through the GitHub contents API (`myblog_backend/app/services/publish_service.py` `github_put_file`;
  `config.py`: `GITHUB_REPO_BRANCH="main"`, `CONTENT_DIR="content/blog"`). A hand-curated
  `content/updates/` next to it is separate. The publish path never touches it, and humans never
  write under `content/blog/`.
- `src/pages/help/player.astro` is a Korean info page. It is a style precedent only, because it renders
  from a TS module, not Markdown.
- `src/components/footer.astro` has a `BROWSE` array (`둘러보기`) and base links. A link fits in either
  without changing the grid.

## Target state

- `myblog_front/content/updates/YYYY-MM.md` (plus one `2026-07-09.md` condensed entry). Frontmatter:
  `title`, `period` (display string), `published` (date), `summary` (one line). The body is a list of
  items. Each item says **what changed** from the visitor's side, **why** in one sentence, the
  **effect** only when a number was recorded, and the PR links in small print. The repos are public.
- `src/pages/updates/index.astro`: entries newest first. Linked from the footer.
- `myblog_front/README.md` § *Patch notes*: the monthly procedure (below).

### Monthly procedure (goes into the front README)

1. List the month's merged PRs. KST month boundaries, explicit limit:
   `for r in myblog_front myblog_backend myblog_worker myblog_music myblog_shared_db; do gh pr list --repo hyuntohoon/$r --state merged --search "merged:<start>..<end>" --limit 500 --json number,title,mergedAt,url; done`
2. Read every title, not just `feat`/`fix`. Open the PR body and the RFC record for anything a member
   or visitor could notice.
3. Include changes visible on the public site or a member's pages. Exclude owner-only, CI, docs,
   research, and dependency work. Group by feature, not by PR. Fold a fix that was superseded within
   the month into its final state.
4. Write `content/updates/YYYY-MM.md`. Terms follow the site rules: 평가 = rating, 평론 = review,
   never "리뷰".
5. Open a front PR. **Owner approval of the wording is a verification item for that PR.** An unchecked
   item blocks merge like a red check (CLAUDE.md § *Verification*). No rule exception is involved.

### Classification: why no per-PR marker

The alternative is a `User-visible: yes/no` line plus a Korean one-liner in every PR body. It is not
adopted:

- It costs every PR, about 80 `feat`/`fix` a month across the services, for one read a month by an
  audience of five accounts.
- Month-end reading uses better evidence than a guess at merge time: the RFC record, and whether the
  change was reverted or superseded within the month. Several 2A playback fixes (front #447–#451) were
  superseded within days, and a per-PR line would have announced each one.
- Revisiting this is an owner judgement, not a measured gate. A miss rate cannot be measured honestly
  when the person drafting also decides what counts as a miss.

## Steps

### Step 1 — `/updates/` page, October entry, condensed July–September entry, procedure (front)

One `myblog_front` PR:

- Add an `updates` collection to `src/content.config.ts` (`glob` over `./content/updates/*.md`, the
  schema above).
- Add `src/pages/updates/index.astro`, styled after `help/player.astro`.
- Add the footer link (placement: OQ2).
- Add `content/updates/2026-10.md` and `content/updates/2026-07-09.md`, drafted by following the
  procedure above for October (in full) and July–September (condensed: the five to eight changes a
  member would most likely have noticed).
- Add the procedure to `README.md`.

**Verification** (all required before merge):
```
pnpm lint && pnpm exec astro check && pnpm test        # required check: `check`
# real-browser clickthrough on the dev server: footer link → /updates/ → both entries render,
#   PR links resolve, phone width has no horizontal scroll, dark mode readable
# owner has approved the wording on the PR   ← verification item, blocks merge if absent
# after deploy: curl -s https://<site>/updates/ | grep -c '<article'  → 2
```

**Rollback**: revert the front PR. The page is static and nothing depends on it.

---

### Step 2 — Close (workspace)

Remove the `docs/plan.md` row and archive this RFC to `docs/archive/done/rfcs/`. November and later
are routine work under the README procedure. They are not RFC steps.

**Verification**: the Step 1 PR is merged and `/updates/` serves both entries in production. The
`curl` result is quoted in a PR comment.

---

## Open questions

Each has a recommendation, and work proceeds on it unless the owner says otherwise.

1. **Audience: public visitors, or the owner's own record?** Recommendation: **public, written for
   members and visitors.** The owner already has `git log`, the RFCs and the Matcher patch notes. The
   goal says "for the site". Blocks Step 1.
2. **Footer placement.** Recommendation: **a base link next to the existing small links** (`업데이트`),
   not a `둘러보기` item and not the top nav. A monthly page for five accounts does not earn more.
   Blocks Step 1.
3. **Cadence.** Recommendation: **monthly**, written in the first days of the next month. The site
   deploys continuously, so there is no release unit. Not blocking.

## Execution record

**Step 1 — shipped 2026-10-16**, `myblog_front#468` (squash `94bde96`, deploy run 38883906906).
`updates` collection, `/updates/` page, footer base link `업데이트`, `content/updates/2026-10.md`
(Oct 1–16, 4 items), `content/updates/2026-07-09.md` (July–September condensed, 7 items), README
§ 패치 노트. lint / `astro check` / `pnpm test` (1509) green; chrome-devtools clickthrough; all 37 PR
links resolve to merged PRs; owner approved the wording in-session. Prod smoke quoted on #468:
`/updates/` 200, `<article>` 2.

Deviations from the plan above, as recorded in the #468 body:

- The footer link went in as the **first** base link, not appended. For a signed-in member the fixed
  Pocket pill covers the right end of that row.
- The README procedure gained one rule: if the month's file already exists, extend it.
- Excluded beyond the Non-goals: Spotify library autosync (the library bucket is owner-only) and
  YouTube playback (front #444; its CSP change ws #984 was recorded as merged but not applied, so
  member availability was not shown).

**Step 2 — this close, 2026-10-16.** Re-checked before archiving: `curl -s
https://www.ratemymusic.blog/updates/ | grep -c '<article'` → `2`.

**Correction to *Current state* (Front).** The RFC says `content/blog/` is machine-written on front
`main`. The publish path is still configured for it (`myblog_backend/app/core/config.py` on
`origin/main`: `GITHUB_REPO_BRANCH = "main"`, `CONTENT_DIR = "content/blog"`), but front `origin/main`
(`94bde96`) tracks **no** files under `content/blog/`; the only tracked files under `content/` are the
two `content/updates/` entries. The directory was emptied by STAB-5 Step 6 (2026-06-06). The
separation `content/updates/` relies on holds either way. No code change.

**Left open, outside this RFC:**

- The October entry covers Oct 1–16 only. Oct 17–31 is appended in early November under the README
  procedure. Not an RFC step.
- Pre-existing defect seen during the Step 1 hit-test: for a signed-in member the Pocket pill covers
  the footer's `RSS` base link (RSS stays reachable from the 구독 column). Not fixed here; the owner
  decides whether to track it.

## Decisions log

| Date | Decision | Step |
|------|----------|------|
| 2026-10-16 | RFC drafted. Fable review cut it from four steps to two. Dropped: the classifier script, the miss-rate gate (circular: the drafter defines a miss) and the three-month backfill (one condensed entry instead). Owner approval is a verification item, not a rule-9 exception | — |
| 2026-10-16 | RFC accepted (owner). OQ1–3 taken on the recommendations: public audience, a small footer base link `업데이트`, monthly | 1 |
| 2026-10-16 | Step 1 shipped (front #468) and prod-verified | 1 |
| 2026-10-16 | Closed: plan row removed, RFC archived; Status → done with owner approval in-session | 2 |
