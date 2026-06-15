# FEAT-blog-to-review-migration: `/blog/*` → `/review/*` URL migration

- **Status**: **Step 1 done + prod-live 2026-06-14** (front #153 / ws #344; zero 404s) — only the **optional Step 2** (true HTTP 301 via the console-managed CloudFront Function, owner-applied) remains; RFC kept open for it.
- **Owner**: TBD
- **Created**: 2026-06-14
- **Plan row**: `plan.md` → FEAT-blog-to-review-migration (Backlog)
- **Extracted from**: `FEAT-home-redesign` **Step 6** (the home-redesign RFC carried this as a
  pending "separate future work" step; per its own note — "consider splitting to its own RFC if
  the redirect mechanism … is non-trivial" — it is hereby split out so home-redesign's own scope
  (steps 1–5 + `/canon`) is complete and promotable independently).

> **Implementation status (2026-06-14): Step 1 MERGED + PROD-LIVE.** front #153 + ws #344
> squash-merged to `main`; front deploy run 27497324862 success (api.gen.ts sync gate passed).
> **Prod smoke PASSED:** old `/blog/lit/`, `/blog/lit`, `/blog/`, `/blog/category/`,
> `/blog/category/Reviews/` all return **HTTP 200** (zero 404s) and redirect to `/review/` resp.
> `/reviews/`; `/review/lit/` renders the review. `pnpm lint`/`astro check`/`build` all green.
> **Only optional Step 2 (true 301) remains** → the RFC stays open for it. (The `Status:` field
> above is left for the owner to flip per rule 5; the work itself is done + verified.)

---

## Goal

Move the review read page off the `/blog/` URL prefix to `/review/[slug]` (singular — owner
decision **D9**, since plural `/reviews/[slug]` would collide with the surviving `/reviews`
browser), remove the redundant `/blog/category` listing, and do it so that **every old `/blog/*`
URL keeps resolving (HTTP 200, never a 404)** for inbound/external/search-index links. After this
ships, the canonical review URL is `https://www.ratemymusic.blog/review/<slug>/`; old `/blog/*`
paths transparently forward to their new home.

## Non-goals

- **No backend / DB / contract / infra change.** This is a `myblog_front`-only routing change.
  The content collection is still named `blog` and still loads from `content/blog/` on disk
  (an internal path, decoupled from the public URL) — neither is renamed.
- **No true HTTP 301 in this PR.** A real 301 needs an edge rewrite (see "Redirect strategy").
  The static-stub mechanism meets the hard "never 404" requirement without touching infra; the
  301 upgrade is an optional, owner-applied follow-up (Step 2).
- **No change to the `/reviews` browser, `/canon`, or the read page's content/layout** — only the
  read page's *route* moves.
- **No `content/blog` → `content/review` rename**, no DB slug changes (the DB stores bare slugs,
  not full URLs).

## Current state (inventory — every `/blog` touchpoint)

Site model: Astro 5 `output: 'static'`, `trailingSlash: 'always'`, `build.format: 'directory'`,
deployed to an **S3 static-website origin** (`myblog-prod-web.s3-website…`, `IndexDocument =
index.html`) behind CloudFront. Implications:
- A directory request `/x/` serves `x/index.html`; a no-slash `/x` gets a **302 → `/x/`** from the
  S3 website endpoint — so existing no-trailing-slash card links keep working.
- There is **no server runtime** → no `Astro.redirect()` 301 at request time; redirects must be
  either prebuilt static pages or an edge function.
- A CloudFront Function `handler` (viewer-request, SPA routing) already exists but its **source is
  not in IaC** (referenced by ARN in `infra/cloudfront.tf:90`, console-managed).

Routes (before):
- `src/pages/blog/[slug].astro` — the review **read page** (`getStaticPaths` over the `blog`
  collection; `prerender`). The only review URL surface.
- `src/pages/blog/category/[category].astro` + `src/pages/blog/category/index.astro` — flat
  title+date category tables (redundant with the `/reviews` browser).
- There is **no** `blog/index.astro` (the bare `/blog/` currently 404s; `WriterApp` nonetheless
  redirects there post-publish — a latent bug, fixed here).

Internal `/blog/<slug>` links (all swapped to `/review/<slug>`):
- `src/components/home/BnmHero.tsx` (×2), `home/LatestReviews.tsx`, `canon/CanonPage.tsx`,
  `reviews/ReviewsIndex.tsx` (×6), `member/LibraryTab.tsx`, `member/ReviewsTab.tsx`,
  `member/AlbumDetail.tsx` (link + comment), `pages/rss.xml.ts` (feed `<link>`),
  `pages/canon.astro` (comment).
- `src/components/writer/WriterApp.tsx` — post-publish `window.location.href` was `/blog/`.
- `src/constants.ts` — the **dead** `HEADER` const (defined, never imported; `header.astro` has
  its own `navLinks` already on `/reviews`/`/genres`/`/canon`) had stale `/blog` URLs.

NOT URLs — intentionally untouched: the `blog` content-collection name (`content.config.ts`),
the `content/blog` on-disk base, `schema.sql`'s `'/blog/:slug'` comment, `assistant.ts`'s
`content/blog/...` authoring path, and `myblog_backend`/`infra`/`myblog_shared_db` references to
`content/blog` (Lambda `CONTENT_DIR`) / `blog:1234` (local DB creds) — none of these are public URLs.

Live blast radius today: **one published post** (`content/blog/2026-06-08--lit/`, slug `lit`,
`draft: false`) → exactly one live URL `/blog/lit/`. Posts were reset to 0 in STAB-5, so external
inbound-link exposure is minimal — but the mechanism must hold for every future post too.

## Target state

- `src/pages/review/[slug].astro` — the read page (moved via `git mv`, content identical; canonical
  + OG auto-derive from `Astro.url.pathname` in `seo.astro`, so they now emit `/review/<slug>/`).
- `src/components/redirect-stub.astro` — a reusable static redirect page: `location.replace()` +
  `<meta http-equiv="refresh">` + `<link rel="canonical">` to the new URL + `robots: noindex,
  follow` + a visible fallback link.
- Legacy stubs (all return **200** with an instant client redirect; never 404):
  - `pages/blog/[slug].astro` → per-slug stub (keeps `getStaticPaths` over the `blog` collection) →
    `/review/<slug>/`. Builds one stub per post (current + future) so old links forward forever.
  - `pages/blog/index.astro` → `/reviews/`.
  - `pages/blog/category/index.astro` → `/reviews/`.
  - `pages/blog/category/[category].astro` → per-category stub → `/reviews/`.
- `astro.config.ts` sitemap `filter` excludes `/blog/*` (stubs are noindex and must not be indexed);
  `/review/*` is included automatically. Verified: built `sitemap-0.xml` lists `/review/lit/`,
  zero `/blog`.
- `WriterApp` post-publish redirect → `/reviews/`.

## Redirect strategy (the crux)

| Mechanism | HTTP status on `/blog/x/` | No-404 guarantee | Infra/ACL change | SEO link-equity |
|---|---|---|---|---|
| **Static stub (this PR)** | `200` + client redirect (`location.replace` / meta-refresh) | ✅ yes — every old path has a built `index.html` | **none** (front-only) | good: `canonical` + `noindex,follow` consolidate to the new URL; Google treats meta-refresh→same content as a redirect |
| **CloudFront Function 301 (Step 2, optional)** | `301` | ✅ yes | edits the console-managed `handler` viewer-request function (owner-applied) | best: true permanent redirect |

The static stub fully satisfies the hard requirement ("never 404") with zero infra/ACL risk, so it
is what ships now. The 301 is a pure SEO nicety and is deferred to keep this PR self-contained and
within the overnight no-infra-wiring guardrails.

Rollout order (single PR, no sequencing hazard because both old and new paths build in the same
deploy): merge → CloudFront auto-deploy → both `/review/<slug>/` (real) and `/blog/<slug>/` (stub)
exist simultaneously → no 404 window. Rollback = revert the PR (the `/blog/[slug]` read page returns
via the same `git mv` in reverse); nothing persisted, no data migration.

## Steps

### Step 1 — Front migration + static no-404 redirects ✅ (implemented, PR open, NOT merged)

Everything in "Target state" above. **Verification (all green 2026-06-14):**
- `pnpm lint` clean · `pnpm exec astro check` 0 errors/0 warnings (3 pre-existing hints) ·
  `pnpm build` 13 pages.
- Built artifacts confirmed: `dist/review/lit/index.html` (real, self-canonical to
  `…/review/lit/`); `dist/blog/lit/index.html`, `dist/blog/index.html`,
  `dist/blog/category/index.html`, `dist/blog/category/Reviews/index.html` (stubs →
  `/review/lit/` resp. `/reviews/`); `sitemap-0.xml` has `/review/lit/`, no `/blog`.
- **Manual (owner, post-merge — see checklist below): hit 3–4 old `/blog/*` URLs in a browser and
  confirm each forwards to a 200 page (no 404).**

**Rollback:** `git revert` the PR. Reverse `git mv` restores `/blog/[slug]`; stubs vanish; links
revert. No infra/data state to undo.

### Step 2 — (Optional, owner-applied) true 301 via CloudFront Function

Extend the existing `handler` viewer-request function to emit a 301 for legacy `/blog/*` URLs.
Ready-to-paste (CloudFront Functions JS, ES5-safe — no template literals / arrow fns). Paste the
`/blog` block at the **top** of the existing `handler(event)` body (right after `var uri = ...`),
keep the existing SPA-routing logic below it, and add the `redirect301` helper:

```js
function handler(event) {
  var request = event.request;
  var uri = request.uri;

  // ── FEAT-blog-to-review-migration Step 2: true 301 for legacy /blog/* URLs ──
  // Mirrors the static stubs (already no-404); upgrades them to a real permanent
  // redirect for SEO link-equity. Order matters: /blog/category before the slug rule.
  if (uri === '/blog' || uri === '/blog/' || uri.indexOf('/blog/category') === 0) {
    return redirect301('/reviews/');
  }
  if (uri.indexOf('/blog/') === 0) {
    var slugPath = uri.substring('/blog/'.length);          // "lit/" | "lit"
    if (slugPath.charAt(slugPath.length - 1) !== '/') { slugPath += '/'; }
    return redirect301('/review/' + slugPath);              // → "/review/lit/"
  }

  // ===== existing SPA-routing logic stays below — DO NOT REMOVE =====
  return request;
}

function redirect301(location) {
  return {
    statusCode: 301,
    statusDescription: 'Moved Permanently',
    headers: { location: { value: location } },
  };
}
```

Covers: `/blog`, `/blog/`, `/blog/category`, `/blog/category/*` → `301 /reviews/`; `/blog/<slug>`
and `/blog/<slug>/` → `301 /review/<slug>/` (trailing slash normalized to the canonical form).

**Console steps (owner — non-IaC):** CloudFront → Functions → open the existing `handler` →
fold in the block above → **Save changes** → **Publish** → confirm it stays associated to the
distribution's default behavior on **Viewer request** (it already is). Verify:
`curl -I https://www.ratemymusic.blog/blog/lit/` → `HTTP/2 301` + `location: /review/lit/`.

Caveats: the function source lives in the console (not IaC) → owner edits it; verify CloudFront
**Functions** are permitted on the current **Free flat-rate plan** (Functions are generally
plan-independent, unlike the custom *cache policies* the Free plan rejects — but confirm before
relying on it). With Step 2 live, the static stubs become a redundant safety net (harmless; can be
kept or later pruned). **Not started; requires owner go-ahead (infra change).**

## Open questions

1. **True 301 now or never?** Step 2 is optional. If the owner wants strict SEO correctness,
   approve the CloudFront Function edit; otherwise the static stubs are indefinitely sufficient for
   a low-inbound-link site. (Recommendation: ship Step 1, add Step 2 only if/when inbound `/blog`
   links actually accumulate.)
2. **Prune the stubs later?** Once Step 2 lands (or once we're confident no `/blog` inbound links
   remain), the `/blog/*` stub pages could be deleted. Default: keep them (cheap, maximally safe).
3. **`content/blog` → `content/review` on disk?** Out of scope and unnecessary (disk path ≠ URL),
   but noted in case a future cleanup wants name alignment — would touch `content.config.ts`,
   backend `CONTENT_DIR`, and `assistant.ts`, so it is its own (larger) change, not this RFC.

## Manual test checklist (owner — run post-merge, after CloudFront deploy)

> The build proves the files generate; this proves the live edge behavior. Static-stub redirects
> return **200 then client-navigate** (not a literal 301) until/unless Step 2 ships — that is
> expected and still satisfies "never 404".

- [ ] `https://www.ratemymusic.blog/blog/lit/` → lands on `/review/lit/` (the review renders).
- [ ] `https://www.ratemymusic.blog/blog/lit` (no trailing slash) → still lands on `/review/lit/`.
- [ ] `https://www.ratemymusic.blog/blog/` → lands on `/reviews/`.
- [ ] `https://www.ratemymusic.blog/blog/category/` and `/blog/category/Reviews/` → land on `/reviews/`.
- [ ] Open `/` (home) — click a Best-New / Latest / Canon card → URL is `/review/<slug>/`, renders.
- [ ] `/reviews/` — click a grid card and a list-row → `/review/<slug>/`, renders.
- [ ] `/rss.xml` — each `<link>` is `…/review/<slug>/`.
- [ ] View source on `/blog/lit/`: `rel=canonical` → `/review/lit/`, `robots` = `noindex, follow`.
- [ ] (If logged in) publish a draft → after the toast you land on `/reviews/` (not a 404).

## Decisions log

| Date | Decision | Source |
|------|----------|--------|
| 2026-06-14 | New prefix = **`/review/[slug]`** (singular) | home-redesign D9 (plural collides with `/reviews` browser) |
| 2026-06-14 | Remove `/blog/category` (fold into `/reviews`) | home-redesign site-scope decision |
| 2026-06-14 | No-404 via **static redirect stubs** (front-only); true 301 via CloudFront Function deferred to optional Step 2 | this RFC — S3-website/static model + overnight no-infra guardrail |
| 2026-06-14 | Extracted from home-redesign Step 6 into its own RFC | this RFC header |
