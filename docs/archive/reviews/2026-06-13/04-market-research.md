# Task 4 — Market Research: Music Review Outlets (International + Domestic)

**Date surveyed:** 2026-06-13
**Method:** WebSearch + WebFetch + read-only `curl` of live HTML, cross-checked against Metacritic/AlbumOfTheYear mirrors and primary outlet pages. Every row/claim carries a source URL. Inference (not directly-sourced) is prefixed `(guess)`; anything not confirmable against a fetched source is marked `(unverified)`.

This file consolidates two partial surveys:
- `04a-international.md` — Pitchfork, The Quietus, Bandcamp Daily, Hearing Things, First Floor (5 outlets).
- `04b-domestic.md` — IZM, 음악취향Y (Music Y), 재즈피플 (Jazz People), plus stew! / weiv as defunct/fading data points (4 outlets investigated, 3 active).

**What was surveyed.** Nine outlets total — five international (one ad+paywall aggregation-feeder, two membership-funded webzines, one commerce-subsidized editorial, one author-owned Substack) and four Korean (one star-scoring webzine incumbent, one multi-critic prose webzine, one paid print magazine, one just-shuttered free newsletter). Goal: extract review-format, discovery, reader-feature, and business-model patterns usable as design references for a **one-person** music-review blog.

**Candidate substitutions (already decided in the partials).** The brief's suggested Substacks *Music Journalism Insider* (ended Dec 2023) and *Penny Fractions* (sunset late 2023) are **both defunct** → replaced with verified-active **Hearing Things** and **First Floor**. Domestic **stew!** ended 2026-03-15 (kept only as a cautionary data point) → replaced in the active set by **재즈피플**.

---

## 1. Comparison table (all outlets)

| Outlet | Region | Review format (score / length / structure) | Discovery features | Reader features (search / tags / subscribe / RSS) | Business model | Source |
|---|---|---|---|---|---|---|
| **Pitchfork** | Intl (US) | Numeric **0.0–10.0** decimal (mean ≈7.0, cluster 6.4–7.8) + **Best New Music** badge (~5%, BNM mean ≈8.62). Long-form single essay, `(guess)` ~600–1500 words | Year-end "Best Albums of [year]"; Best New Music/Reissue rails; Sunday Review; genre + decade ("200 Best of [decade]") lists | Subscriber accounts comment + rate albums (0–10); searchable archive (subscriber-gated); email/RSS historically exist `(unverified)` | Condé Nast (folded into GQ Jan 2024). **$5/mo paywall since Jan 20 2026**; non-subs 4 free reviews/mo. Display ads + subscription | https://www.metacritic.com/publication/pitchfork/ |
| **The Quietus** | Intl (UK) | **No native score** (essayistic long-form). Metacritic shows uniform "80" = `(guess)` Metacritic default for an unscored pub. Word counts `(unverified)` (site 403s) | "Music of the Month" roundups → subscriber playlist; annual "Albums of the Year" (w/ Norman Records); "Albums of the Year So Far"; "Album of the Week"; Charts hub | Free reading; "Subscriber Area" / "Sound & Vision"; monthly subscriber newsletter + playlists; 30-day trial. Search/RSS standard but `(unverified)` | Independent, **reader-funded membership via Steady**: ~£5/mo entry → "Sound & Vision" £20/mo (funds ~4 commissioned releases/yr). Ad + membership hybrid, membership-led | https://www.metacritic.com/publication/the-quietus/ |
| **Bandcamp Daily** | Intl (US) | **No score.** "Album of the Day" = ~450–500 word, ~5-paragraph essay (measured from fetch). "Essential Releases" = staff roundup, short blurb/pick. Embedded audio + **buy/pre-order links** | "Album of the Day" (daily); "Essential Releases" (weekly staff picks); "Lists" (themed/genre/year-end); "Big Ups"; Bandcamp Radio; genre verticals | Free, no paywall; genre nav; audio preview players; "Latest"/"Top Stories" rails; contributor pages. Editorial email/RSS/search `(unverified)` | **Commerce-subsidized editorial** — free, no ads-led/subscription on editorial side; funded by marketplace fees. Owner: Songtradr (since Oct 2023). No Beatport sale | https://daily.bandcamp.com/essential-releases/essential-releases-june-12-2026 |
| **Hearing Things** | Intl (US) | **No score.** Column/theme-driven, no single template: "Five Songs", "Five Albums", "Gear Crush", "Live Review", features/interviews. `(guess)` mid-length essays | Weekly "Five Albums" recs (paid); weekly "Five Songs"; features/interviews. Year-end lists `(guess)` likely (ex-Pitchfork DNA), `(unverified)` | **Free weekly email newsletter**; on-site search; tag/section nav; **RSS feed**; social. Paid subs get "Five Albums" + comments | **Membership/subscription, 100% worker-owned** (5 ex-Pitchfork founders, no parent). Top "Super Deluxe…Hi-Fi" tier + merch/playlists/CDs. Ad partnerships + tip jar. Subscription-led | https://www.hearingthings.co/ |
| **First Floor** | Intl (US, electronic) | **Not a scored review outlet** — analysis/criticism newsletter: essays, producer interviews, weekly news digest, **curated recs** (not rated single-album reviews). No scores | Weekly curated album recs / digest; year-end lists; archive by content type (essays/interviews/digests/recs) | Substack-native: **email subscribe (free + paid)**; full archive by type; web+app; RSS (Substack default); comments (paid) | **Substack paid-subscription / patronage** — author-owned (Shawn Reynaldo), no parent, no display ads. Price `(unverified)` | https://firstfloor.substack.com/ |
| **IZM (이즘)** | KR | **5.0 star scale** (0.5 steps). No domestic 5.0 ever; ~20 works at 4.5. Medium-form single-critic essay, named byline. Score is reviewer-dependent | **Year-end canon** "올해의 국내 앨범/싱글" + "Editors' Choice" (signature); monthly "월간 음악 추천" → "이즘 뮤직 클라우드" podcast; Picks | Live HTML has **search (검색), RSS, tags**, modern /posts + /picks routing. Multi-channel: site + YouTube + X + Spotify/Apple podcast | **Patron/sponsorship-supported**, no visible paywall/ads (footer = copyright + email only). Early Samyang Chemical patron + free Hongdae office. `(guess)` adjacent podcast/YT revenue | https://www.izm.co.kr/ |
| **음악취향Y (Music Y)** | KR | **Two modes:** Single-Out (weekly singles) = **no score**, multi-critic prose, named bylines; album reviews ("Album-Out") = **0–5 stars** (`(unverified)` scale, search synthesis). Genre-eclectic, low bias | **"Best" section** = year-end "올해의 앨범/싱글/신인"; curated canon lists syndicated to Melon/Bugs ("발라드 Best 100", "댄스 Best 120") | Live HTML has **search + tags**; nav About/Best/Choice/Review/Zine. RSS/subscribe **not found** `(unverified)`. HTTPS cert mismatch → served over HTTP | `(unverified)` no paywall/ads/donation widget found. `(guess)` volunteer critic-collective (2006 Naver-cafe origin, KMA-panel staff). No revenue evidenced | http://musicy.kr/?c=review |
| **재즈피플 (Jazz People)** | KR (jazz) | Monthly **print** jazz-culture magazine: jazz/performance news, artist profiles, reviews. Site is artist/venue-centric. Numeric/star score in print `(unverified)` (print-gated) | **Live-club schedule / gig calendar** (/lives) — a discovery feature webzines lack; artist pages. Year-end best-jazz feature `(unverified)` | **Member login** + accounts (/login). Durable reader feature = **paid postal subscription**, not on-site reading | **Paid print subscription — 156,000 KRW/yr (12 issues)** — only outlet with a clear recurring paid model. `(guess)` print ads + newsstand/Aladin sales supplement | https://themagazine.co.kr/product/jazz-people-재즈피플-연12회/2815/ |
| **stew!** (DEFUNCT — ended 2026-03-15) | KR (K-pop) | Was a K-pop newsletter ("맛있는 케이팝 뉴스레터"), **not score-based**: feature essays + artist deep-dives + fan recaps + news. Schedule 5th/15th/25th, ~7-person volunteer crew | `(unverified)` feature-essay/rec driven, no confirmed year-end list before shutdown | **Stibee email subscription** + public web archive. Subscribe button on landing | **Free Stibee newsletter, volunteer crew, no paid tier.** Farewell cites "newsletter market environment" — free-volunteer model proved unsustainable | https://kpop-stew.stibee.com/p/132 |
| **weiv (웨이브)** (FADING — excluded) | KR (indie) | Album reviews lapsed ~2021–2023; now `(guess)` ~one-person occasional columns/interviews | — | HTTP 500 on every fetch this session (transient/geo `(unverified)`) | `(unverified)` | https://ko.wikipedia.org/wiki/웨이브_(웹진) |

---

## 2. Patterns

### What the successful outlets share
- **Discovery = recurring curated rails + year-end canon, NOT a searchable score database.** Every active outlet leans on "of the day / week / month" cadence plus an annual list: Pitchfork "Best Albums of [year]", Quietus "Music of the Month" + "Albums of the Year", Bandcamp Daily "Album of the Day" / "Essential Releases", Hearing Things "Five Albums/Songs", First Floor weekly digest, IZM "올해의 국내 앨범", Music Y "Best (올해의 앨범/싱글/신인)". The **year-end list is the single most universal artifact** — present at every surviving editorial outlet on both continents (sources: https://www.albumoftheyear.org/ratings/1-pitchfork-highest-rated/2026/1 ; https://thequietus.com/columns/tq-charts/albums-of-the-year/ ; https://www.izm.co.kr/posts?id=33746 ; http://musicy.kr/?c=best). It is table-stakes for critical credibility.
- **A consistent, named review format + bylines.** Whether scored (Pitchfork, IZM) or essayistic (Quietus, Bandcamp Daily, Music Y), each outlet has a *recognizable* template and named critics. Bandcamp Daily's ~450–500 word, ~5-paragraph "Album of the Day" is a measured, repeatable shape (source: https://daily.bandcamp.com/album-of-the-day/ana-roxanne-poem-1-review).
- **Reader plumbing (search / tags / RSS / subscribe) is a cheap differentiator.** IZM has all four (search/RSS/tags/podcast) and is the Korean reference incumbent; Music Y has search + tags but **no confirmed RSS/subscribe** and is visibly more dated (HTTP-only, cert mismatch). Internationally, Substack/worker-owned outlets get email + RSS for free from the platform.

### How scoring conventions differ
- **Numeric decimal (aggregation-feeder):** Pitchfork 0.0–10.0 one-decimal + Best New Music badge — the only outlet whose scores feed Metacritic/AlbumOfTheYear (source: https://nolanbconaway.github.io/blog/2017/pitchfork-roundup.html).
- **Star scale:** IZM 5.0 in 0.5 steps (no domestic perfect score ever; ~20 at 4.5), Music Y album reviews 0–5 stars `(unverified)` (sources: https://namu.wiki/w/이즘 ; https://sports.khan.co.kr/article/202512031906003).
- **No score / essayistic:** The Quietus, Bandcamp Daily, Hearing Things, First Floor, and Music Y's high-volume Single-Out series — **the majority convention** among respected critical outlets. A numeric/star score is used mainly by the aggregation-feeder (Pitchfork) and the Korean incumbent (IZM); four of five international outlets and the highest-volume Korean series run **score-free**. This corroborates the workspace's existing "album rating only, 0–5/0.5, stars-only" decision (`project-feature-roadmap`) as a deliberate IZM-style choice, *not* an industry default.

### How newsletters monetize vs ad-supported webzines
- **Reader-funding is displacing ads for serious criticism in 2026.** Pitchfork (the ad-incumbent) just added a $5/mo paywall after ~30 years free (source: https://www.brooklynvegan.com/pitchfork-owner-conde-nast-putting-all-titles-behind-paywalls/). The Quietus (Steady membership, £5–£20/mo), Hearing Things (worker-owned subscription), and First Floor (Substack paid) are **all direct-reader-funded**. Ad-only is no longer the default.
- **The free-volunteer-newsletter model is the documented failure mode.** stew! (free Stibee, ~7-person volunteer crew) shut down 2026-03-15 explicitly citing "newsletter market environment" shifts (source: https://kpop-stew.stibee.com/p/132). Durable newsletters (First Floor, Hearing Things) are author/worker-owned with a **clear paid tier**; longevity tracks with direct reader revenue, not free-only.
- **Two non-subscription exceptions exist:** Bandcamp Daily is **commerce-subsidized** (marketplace fees fund free editorial + buy links in every review — source: https://daily.bandcamp.com/essential-releases/essential-releases-june-12-2026), and IZM runs on **patronage + donated office space** with `(guess)` adjacent podcast/YouTube revenue (source: http://archive.izm.co.kr/faq.asp). Both avoid both ads and paywalls — but each depends on an external subsidy (a marketplace; a patron) a solo blog does not have.

---

## 3. THE KEY DELIVERABLE — recommendations for a one-person blog

### What a solo blog should realistically adopt

1. **RSS feed.** WHY: zero-maintenance once wired (Astro generates it from content collections), it is the cheapest reader-retention and syndication primitive, and Music Y's *absence* of confirmed RSS is exactly what makes it feel dated next to IZM. Model: **IZM** (search + RSS + tags present in live HTML — https://www.izm.co.kr/) and every Substack outlet (RSS is free from the platform — https://firstfloor.substack.com/). **→ NOTE (verified 2026-06-13): the blog ALREADY ships this** — `myblog_front/src/pages/rss.xml.ts` (`@astrojs/rss`, prerendered) + autodiscovery `<link rel="alternate" …>` in `layout.astro:18`. So this recommendation is already satisfied; only the placeholder `"buckit"` title + a human-visible subscribe link remain (XS). It is **not** new work — see `05-feature-candidates.md` #1 correction.

2. **One consistent, named review format.** WHY: a fixed, repeatable template (e.g. a ~450–600 word essay with a stable section shape: context → overview → standout tracks → verdict + 0–5 star rating) makes solo output recognizable and lowers per-post decision cost. A solo writer cannot sustain variety *and* quality; consistency is the leverage. Model: **Bandcamp Daily** "Album of the Day" (measured ~450–500 words, ~5 paragraphs — https://daily.bandcamp.com/album-of-the-day/ana-roxanne-poem-1-review) + **IZM** medium-form single-critic essay with star score (https://www.izm.co.kr/).

3. **An annual year-end list ("Best Albums of [year]").** WHY: it is the single most universal artifact across every surviving outlet on both continents, it is produced once a year (negligible ongoing cost), and it is the most *shareable* credibility signal a small outlet can make. Model: **Pitchfork** "Best Albums of [year]" (https://www.albumoftheyear.org/ratings/1-pitchfork-highest-rated/2026/1), **IZM** "올해의 국내 앨범" (https://www.izm.co.kr/posts?id=33746), **Music Y** "Best" (http://musicy.kr/?c=best).

4. **Lightweight curated rails (a recurring "Album of the Week/Month" or short "Essential" roundup).** WHY: discovery at every outlet runs on cadence rails, not a ratings leaderboard; a weekly/monthly short-blurb roundup is far cheaper than daily full reviews yet gives the site a "freshness" pulse. The blog already has a review-bucket/board surface to anchor this. Model: **Bandcamp Daily** "Essential Releases" weekly (https://daily.bandcamp.com/essential-releases/essential-releases-june-12-2026), **Quietus** "Music of the Month" (https://thequietus.com/tq-charts/music-of-the-month/music-of-the-month-the-best-albums-and-tracks-of-may-2026/), **Hearing Things** "Five Albums" (https://www.hearingthings.co/).

5. **Email subscribe (free tier first; paid optional later).** WHY: email is the most durable reader-retention channel and (via Substack/Stibee/Buttondown) costs nothing to start; it is the on-ramp the durable independents (First Floor, Hearing Things) all use. Keep it *free* initially — the paid tier is a later, optional step, not a launch requirement. Model: **Hearing Things** free weekly newsletter ("Discover new music in your inbox each week. It's free!" — https://www.hearingthings.co/), **First Floor** free+paid Substack (https://firstfloor.substack.com/). CAUTION: see the stew! lesson in the NOT-adopt list — a *free-only volunteer* newsletter with no other revenue is the documented failure mode, so treat email as retention, not as the business model.

6. **Search + tags over the review archive.** WHY: low-cost (Astro static search / content-collection tag pages), and it is the baseline reader feature both Korean webzines ship; it makes a growing solo archive navigable without any backend work. Model: **IZM** and **Music Y** both expose search + tags in live HTML (https://www.izm.co.kr/ ; http://musicy.kr/?c=review).

7. **A clear 0–5 / 0.5 star rating, applied consistently (already decided).** WHY: a star score is a recognizable hook (IZM markets "평점 X점"; outlets quote it — https://sports.khan.co.kr/article/202512031906003) and is trivially cheap for a solo writer vs. Pitchfork's higher-resolution decimal scale. The workspace already chose album-only 0–5/0.5 stars; this survey confirms it as the *IZM* path (deliberate), not an accidental default. Model: **IZM** 5.0 scale (https://www.izm.co.kr/).

### What a solo blog should NOT adopt

1. **Daily review cadence.** WHY: Bandcamp Daily's "Album of the Day" and IZM's stream of K-pop reviews are **staff-fed**; a solo writer cannot sustain daily original reviews without quality collapse. Use weekly/monthly curated rails instead (see adopt #4). Evidence: Bandcamp Daily multi-staff bylines per roundup (https://daily.bandcamp.com/essential-releases/essential-releases-june-12-2026).

2. **High-volume / multi-critic coverage.** WHY: Pitchfork's review throughput and Music Y's multi-named-critic Single-Out series both require a *roster*; a one-person blog has one voice and one set of hands. Depth-over-breadth (fewer, better reviews) is the only solo-viable strategy. Evidence: Music Y multi-critic bylines per single (https://musicy.kr/index.php?c=review); Pitchfork volume (https://www.metacritic.com/publication/pitchfork/).

3. **Comment sections / reader ratings requiring moderation.** WHY: Pitchfork only added comments + reader album-ratings *behind a paywall* (i.e. gated to manage volume — https://www.brooklynvegan.com/pitchfork-owner-conde-nast-putting-all-titles-behind-paywalls/); First Floor/Hearing Things gate comments to *paid* subscribers. Open unmoderated comments are a spam/abuse sink with no solo bandwidth to police. Skip, or gate hard, until there is reason and capacity.

4. **A paywall as the launch business model.** WHY: Pitchfork could paywall only on the back of ~30 years of brand equity + Condé Nast scale; a new solo blog has no archive depth or audience to gate. Paywalling pre-audience just suppresses the growth a small outlet needs. Evidence: Pitchfork paywall arrived Jan 2026 after ~30 years free (https://en.wikipedia.org/wiki/Pitchfork_(website)).

5. **A free-only volunteer newsletter as the *primary* product.** WHY: this is the freshly-documented failure mode — stew! ran a ~7-person volunteer free Stibee newsletter for ~4 years and shut down 2026-03-15 citing market conditions (https://kpop-stew.stibee.com/p/132). Email is fine as a *retention* channel (adopt #5); it is not viable as the whole business with no other revenue and no paid staff.

6. **Live charts / real-time aggregation / a ratings leaderboard.** WHY: aggregation (Metacritic/AlbumOfTheYear feeding off Pitchfork scores) and live charts need either a feeder ecosystem or constant data upkeep; no surveyed *solo* outlet runs one, and discovery everywhere is editorial rails, not live charts (sources: https://www.albumoftheyear.org/ratings/1-pitchfork-highest-rated/2026/1 ; https://thequietus.com/charts/). A static year-end list (adopt #3) delivers the same credibility at a fraction of the cost.

7. **Print / physical product (and other capital-intensive perks).** WHY: 재즈피플's 156,000 KRW/yr print subscription is the *only* clean recurring-revenue model in the set, but print requires layout, printing, fulfillment, and capital a solo web blog cannot carry; Hearing Things' handmade mix-CDs/cassettes + annual merch are similarly staff-and-capital intensive. Stay web-native. Evidence: 재즈피플 print subscription (https://themagazine.co.kr/product/jazz-people-재즈피플-연12회/2815/); Hearing Things merch/CD perks (https://www.hearingthings.co/).

8. **A commissioned-release / label arm (Quietus "Sound & Vision").** WHY: The Quietus' £20/mo top tier funds ~4 commissioned music releases/year — that is a label operation requiring A&R, contracts, and budget far beyond a solo reviewer. Out of scope. Evidence: https://thequietus.com/articles/28506-membership.

---

## Source index

International (full per-outlet sourcing in `04a-international.md`):
- https://www.metacritic.com/publication/pitchfork/ — Pitchfork active, dated reviews + scores
- https://www.brooklynvegan.com/pitchfork-owner-conde-nast-putting-all-titles-behind-paywalls/ — $5/mo paywall, 4 free/mo, 0–10 scale, rate/comment
- https://en.wikipedia.org/wiki/Pitchfork_(website) — Condé Nast/GQ, paywall date
- https://nolanbconaway.github.io/blog/2017/pitchfork-roundup.html — 0.0–10.0 scale stats
- https://www.albumoftheyear.org/ratings/1-pitchfork-highest-rated/2026/1 — year-end discovery
- https://www.metacritic.com/publication/the-quietus/ — Quietus active, uniform "80"
- https://thequietus.com/tq-charts/music-of-the-month/music-of-the-month-the-best-albums-and-tracks-of-may-2026/ — Music of the Month (active)
- https://thequietus.com/columns/tq-charts/albums-of-the-year/ — year-end list
- https://steady.page/en/magazine/posts/e0068cc5-1017-468e-9450-7f90e01dda0a — Steady membership model
- https://thequietus.com/articles/28506-membership — membership tiers (£5–£20)
- https://daily.bandcamp.com/essential-releases/essential-releases-june-12-2026 — active Jun 12 2026, no score, buy links
- https://daily.bandcamp.com/album-of-the-day/ana-roxanne-poem-1-review — May 6 2026, ~450–500 words
- https://en.wikipedia.org/wiki/Bandcamp — Songtradr ownership, fees
- https://www.songtradr.com/blog/posts/songtradr-bandcamp-acquisition/ — acquisition
- https://www.hearingthings.co/ — active, format, free newsletter, search/tags/RSS, membership
- https://www.hearingthings.co/hearing-things-is-now-100-worker-owned-2/ — 100% worker-owned
- https://www.avclub.com/hearing-things-former-pitchfork-writers-music-new-site — Oct 2024 launch
- https://firstfloor.substack.com/ — June 2026 issues #315, free/paid, recs, year-end lists
- https://soundoffractures.substack.com/p/5-substack-newsletters-i-read-to — May 25 2026, First Floor active; MJI/Penny Fractions defunct

Domestic (full per-outlet sourcing in `04b-domestic.md`):
- https://www.izm.co.kr/ — IZM homepage (2026 ©, reviews, search/RSS/tags markers)
- https://izm.co.kr/picks — IZM Picks / Editors' Choice / 2026 feature
- https://www.izm.co.kr/posts?id=33746 — IZM "2025 올해의 국내 앨범"
- https://sports.khan.co.kr/article/202512031906003 — 리센느 'lip bomb' IZM 평점 4점 (2025-12-03)
- https://namu.wiki/w/이즘 — IZM 5-point scale / 4.5 list
- http://archive.izm.co.kr/faq.asp — IZM funding (Samyang patron, Hongdae office)
- http://musicy.kr/?c=review — Music Y Single-Out #604, 2026.06.08 (curl)
- http://musicy.kr/?c=best — Music Y "Best" 올해의 앨범/싱글/신인 (curl)
- https://musicy.kr/index.php?c=review — Music Y multi-critic, no-score Single-Out
- https://ko.wikipedia.org/wiki/음악취향Y — "운영 중", founding, KMA panel
- https://themagazine.co.kr/product/jazz-people-재즈피플-연12회/2815/ — 재즈피플 156,000 KRW/yr
- https://www.aladin.co.kr/shop/wproduct.aspx?ItemId=388957744 — 재즈피플 2026.4 issue
- https://jazzpeople.co.kr/lives — 재즈피플 live-club schedule
- https://kpop-stew.stibee.com/p/132 — stew! final issue 128호, 2026-03-15 (farewell)
- https://ko.wikipedia.org/wiki/웨이브_(웹진) — weiv decline

---

## Open questions / unverified items

1. **Pitchfork** exact review length/section structure + whether RSS/email newsletter still exist — pitchfork.com is unfetchable (403); evidenced only via Metacritic mirror. Length assumed ~600–1500 words `(guess)`.
2. **The Quietus** per-review word counts + meaning of Metacritic's uniform "80" — thequietus.com 403s WebFetch. Assumed unscored, Metacritic default `(guess)`.
3. **Bandcamp Daily** editorial-side search/RSS/email (vs the commerce platform's fan accounts) not confirmed on fetched pages.
4. **Hearing Things** per-article publication dates + whether it runs year-end lists — homepage showed no dates; June 2026 inferred from "Pride Month" framing `(guess)`.
5. **First Floor** exact paid-tier price not captured on the fetched archive page `(unverified)`.
6. **Bandcamp ownership** secondary-source conflict (a blog claimed a 2024 Beatport sale + "went quiet") — rejected in favor of primary sources (Songtradr/Paul Wiltshire, active June 2026). Confirm against a 2026-dated primary source if a precise legal owner name is needed.
7. **음악취향Y business/revenue model** unconfirmed — no paywall/ads/donation widget in fetched HTML; volunteer critic-collective is a `(guess)`. Needs an About page or press interview.
8. **음악취향Y album star scale** (claimed 0–5) is a WebSearch synthesis, not a quoted scale graphic — confirm against an actual Album-Out review page showing the score widget.
9. **음악취향Y RSS/subscribe** — no RSS/newsletter marker found in fetched HTML; existence unconfirmed.
10. **재즈피플 review format** — whether print album reviews carry numeric/star scores is unverifiable from public web (print-gated); needs a scanned issue. Year-end best-jazz feature also unconfirmed.
11. **weiv (웨이브)** returned HTTP 500 on every fetch — could be transient or US-geoblocking. A KR-vantage retry would confirm whether it has any 2025–2026 posts before fully writing it off.
12. **IZM current (vs historical) revenue** is inferred — documented funding is the FAQ-cited Samyang patron + free office; whether IZM now earns from podcast/YouTube/merch is a `(guess)`.
13. **Korean-vantage caveat:** WebSearch here is US-only and several outlet pages are JS-rendered SPAs/ASP; date/title extraction relied on curl HTML parsing. A KR-locale crawl could surface additional active outlets (디깅클럽서울/사운드네트워크/비웨이브/한국대중음악상 site) not fully verified this pass.
14. **Candidate substitutions** (MJI→Hearing Things, Penny Fractions→First Floor international; stew!→재즈피플 domestic) — confirm these are acceptable replacements for the brief's named examples.
