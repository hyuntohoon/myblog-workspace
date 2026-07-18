# SEO-review-structured-data: Review + MusicAlbum JSON-LD on review pages

- **Status**: draft
- **Owner**: 박지훈
- **Created**: 2026-07-18
- **Plan row**: `plan.md` → SEO-review-structured-data
- **Origin**: 2026-07-18 UI planning session, area 10. Scope per owner decision 15: **JSON-LD
  only**; per-review OG-image generation explicitly deferred.

---

## Goal

Every published review page emits valid `schema.org/Review` JSON-LD with a `MusicAlbum`
`itemReviewed`, making review pages eligible for Google review-snippet (star) rich results.
Build-time only — no runtime or API dependency.

## Non-goals

- **Per-review OG image generation** (cover + stars + title composite) — deferred; would add
  satori+resvg deps (only sharp is installed). Revisit as its own small item if snippet uptake
  proves worth it.
- Album-level SEO / album permalinks — not adopted this round; review pages are the focus.
- Artist-page or home-page structured data.
- Changing existing OG/canonical/sitemap behavior (verified healthy).

## Current state (verified 2026-07-18)

- `src/components/seo.astro`: title/description/canonical/OG/twitter emitted; og:image only
  when the page passes one — `/review/[slug]` passes `post.albumCover || post.image` ✓.
  `defaultOgImage` is empty (no site-wide fallback asset).
- **No JSON-LD anywhere** in the front (`ld+json` grep = 0).
- Sitemap via `@astrojs/sitemap` (legacy `/blog/*` stubs excluded); robots.txt sane; `/blog/*`
  are redirect stubs to `/review/*`.
- All needed fields exist at build time in the content collection (`content.config.ts`):
  top-level `rating` (0–10) + `ratingScale`, `musicReview.{title,artists,releaseDate,genres,
  label}`, `albumCover`, plus date/author constants.
- **Google policy (fetched 2026-07-18, review-snippet doc)**: supported types include
  "`MusicPlaylist`, `MusicRecording` **(and their subtypes)**" — `MusicAlbum` is a subtype of
  `MusicPlaylist` ⇒ eligible. Self-serving restriction covers LocalBusiness/Organization only ⇒
  an independent critic reviewing third-party albums is fine. Required: `author`
  (Person, <100 chars), `reviewRating.ratingValue`, `itemReviewed`.

## Target state

`/review/[slug]` emits one `<script type="application/ld+json">` block:

```json
{
  "@context": "https://schema.org",
  "@type": "Review",
  "author": { "@type": "Person", "name": "<site author>" },
  "datePublished": "<post date>",
  "reviewBody": "<description/excerpt>",
  "reviewRating": { "@type": "Rating", "ratingValue": <rating>, "bestRating": <10|5 per ratingScale>, "worstRating": 0 },
  "itemReviewed": {
    "@type": "MusicAlbum",
    "name": "<musicReview.title>",
    "byArtist": [{ "@type": "MusicGroup", "name": "<artist>" }],
    "image": "<absolute albumCover URL>",
    "datePublished": "<releaseDate>"
  }
}
```

Emitted only when `isReview` (album linked OR rating present — reuse the page's existing gate);
rating-less reviews omit `reviewRating` (still valid Review markup, no stars). Non-review posts
emit nothing.

## Steps

### Step 1 — JSON-LD component + wiring (front only, single PR)

`src/components/review-jsonld.astro` (props from the post entry, absolute URLs via `SITE.url`)
included from `/review/[slug].astro`. Escape/serialize via `JSON.stringify` into the script tag
(`set:html` with `<` escaping).

**Verification**:
```
pnpm build && grep -l 'application/ld+json' dist/review/*/index.html | head
# + paste one page into Google Rich Results Test → valid Review detected
```
Post-deploy: Rich Results Test against the live URL; quote result in PR comment. (Actual SERP
stars are at Google's discretion — the exit gate is "valid + eligible", not "stars visible".)

## Open questions

1. **bestRating** — emit the native 0–10 scale or normalize to 5-star (matching the visible
   star UI)? Default: native scale with `bestRating` set per `ratingScale` (Google normalizes).
   Blocks Step 1 constant only.
2. **reviewBody source** — `description` vs first N chars of the MDX body. Default:
   `description`.

## Decisions log

| Date | Decision | Step |
|------|----------|------|
| 2026-07-18 | Owner: JSON-LD only; OG image generation deferred | scope |
