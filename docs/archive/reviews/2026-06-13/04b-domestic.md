# Task 4 — Korean / Domestic Music Webzine & Newsletter Research (2026-06-13)

Research goal: catalog currently-active Korean music webzines / newsletters as competitive / design references for a music-review blog. Required outlet: **IZM**. Plus 2–3 other outlets verified active right now, with evidence (recent dated content), review format, discovery features, reader features, and business model. Every field is backed by a fetched source URL.

**Method note.** All "active" claims are anchored to a dated artifact (a review byline date, an issue number + send date, or a subscription/issue listing dated 2026). Several target sites are JS-rendered SPAs or ASP pages where `WebFetch` (small model, US-only) saw only the shell; in those cases I `curl`-ed the raw HTML (read-only) and parsed dates/titles/nav directly. namu.wiki and grokipedia 403 `WebFetch` but surface in WebSearch snippets, which I treat as secondary corroboration only (primary = the outlet's own live page).

**Headline result.** 4 outlets investigated in depth:

- **IZM** — ACTIVE (reference-grade incumbent; 5-pt star scores, year-end canon, RSS/search/podcast).
- **음악취향Y (Music Y)** — ACTIVE (multi-critic prose Single-Out, 0–5 album scores, year-end "Best", search + tags).
- **재즈피플 (Jazz People)** — ACTIVE (monthly **print** magazine, paid subscription; the only sustainable revenue model of the set).
- **stew!** — **JUST ENDED.** Final issue (128호) sent **2026-03-15**, explicitly winding down regular publication. Documented here as a recently-defunct data point (per the "if defunct, say so and pick another" instruction) — it is *not* counted as one of the active outlets; 재즈피플 is the replacement.

A `weiv` (웨이브) probe is also recorded below as a second cautionary "fading webzine" data point (intermittent 500s, album reviews lapsed) — excluded from the active set.

---

## 1. IZM (이즘) — ACTIVE

- **URL:** https://www.izm.co.kr/ (archive mirror: http://archive.izm.co.kr/)
- **What it is:** Korea's longest-running pop-music webzine. Founded **2001-08-30** by critic Im Jin-mo (임진모); editorial by Jang Jun-hwan (장준환). Covers domestic gayo, K-pop, and overseas pop.

### Active evidence (dated)
- Homepage footer reads "**2026 IZM © All Rights Reserved**" and lists fresh K-pop single/album reviews: aespa "Lemonade", Treasure "If I", Kacey Musgraves "Middle Of Nowhere", Tray B feat. 지코·개코 (each with a named critic byline). Source: https://www.izm.co.kr/ (WebFetch homepage).
- A 2026-dated feature exists in Picks: "2026 북중미 월드컵 기념 캐나다 뮤지션 23" (Canadian musicians for the 2026 World Cup). Source: https://izm.co.kr/picks (WebFetch).
- Independent press corroboration of *current* review activity: Sports Khan (2025-12-03) reports 리센느 'lip bomb' received an **IZM 평점 4점** (rating 4/5). Source: https://sports.khan.co.kr/article/202512031906003

### Review format — **5-point star/score system**
- IZM scores out of **5.0** (0.5 increments). No domestic album has ever received a perfect 5; only ~20 works have ever reached 4.5 (e.g. Epik High `[e]`, Cho Yong-pil "The Dreams", 산울림 "내 마음", 빛과 소금 "Here We Go"). 리센느 'lip bomb' = 4.0; 리센느 'LOVE ATTACK' hit a rare recent 4.5 (2024-09). Sources: https://namu.wiki/w/%EC%9D%B4%EC%A6%98 (WebSearch snippet), https://v.daum.net/v/20240911222907429 (4.5 record), https://sports.khan.co.kr/article/202512031906003 (4.0).
- Known characteristic: score varies by which critic reviews; sometimes weighs non-musical controversy. (per namu snippet — secondary, label this a community-perception claim not a fact.)
- Length/structure: medium-form single-critic essay per release, named byline, no fixed template visible.

### Discovery features
- **Year-end canon is IZM's signature.** Annual "올해의 국내 앨범 / 올해의 국내 싱글" (Albums/Singles of the Year) and "Editors' Choice": "2025 올해의 국내 앨범 by IZM" lives at https://www.izm.co.kr/posts?id=33746; "2025 에디터스 초이스" and "2025 올해의 국내 싱글" surfaced on the Picks page (https://izm.co.kr/picks). YouTube playlist mirror: "이즘(IZM) 연말결산 2025 올해의 국내 앨범".
- Monthly recommendation series "월간 음악 추천" (also pushed as the "이즘 뮤직 클라우드" podcast on Spotify/Apple). Source: https://open.spotify.com/show/1yKkDDIFtX3bN5jFbfmlDz
- "Picks" / "Monthly Pick" curated lists. Source: https://izm.co.kr/picks

### Reader features
- Live homepage HTML contains **search (검색), RSS, tags (tag), and a modern `/posts` + `/picks`** routing. Sections: Review, Interview, Feature, Picks, Contact. Source: curl of https://www.izm.co.kr/ (raw HTML, 716 KB) — markers `search`, `검색`, `RSS`, `tag`, `/posts`, `picks` all present.
- Multi-channel: website + YouTube + X (@IZMtweet) + Spotify/Apple podcast. Sources: https://x.com/IZMtweet , https://podcasts.apple.com/gb/podcast/id1635020245

### Business model — **patron / sponsorship-supported, no visible paywall or ads**
- No paywall, membership, or display-ad units visible on the editorial pages (footer = copyright + `webzineizm@gmail.com` only). Source: https://www.izm.co.kr/ (WebFetch).
- Historically sustained by patronage, not subscriptions: IZM's own FAQ credits early financial support from Samyang Chemical CEO Kim Rae-kyung, and currently free Hongdae office space from "Big Puzzle" Prof. Yoon Young-hoon; staffed by members + external contributors. Source: http://archive.izm.co.kr/faq.asp (via WebSearch snippet). (guess) Adjacent revenue likely flows through the podcast/YouTube channels rather than the webzine itself — not directly evidenced.

---

## 2. 음악취향Y (Music Y) — ACTIVE

- **URL:** http://musicy.kr/ (also https://musicy.kr — note: the HTTPS cert is mismatched / `ERR_TLS_CERT_ALTNAME_INVALID`, so the site is effectively served over HTTP).
- **What it is:** Genre-broad webzine, "당신의 취향이 역사가 됩니다" ("your taste becomes history"). Started 2006 as a Naver cafe by critic Cho Il-dong (조일동); relaunched as a standalone webzine in 2014. Wikipedia status box: "**현재 상태: 운영 중**" (currently in operation). Source: https://ko.wikipedia.org/wiki/%EC%9D%8C%EC%95%85%EC%B7%A8%ED%96%A5Y

### Active evidence (dated)
- Live review-list page shows the running **Single-Out series at #604**, with publication dates **2026.06.08 / 2026.06.01 / 2026.05.25** and entries like "[Single-Out #604] 구원찬, 모허, 안예은, **에스파 「Lemonade」**, 이동현"; also "[Single-Out #603-5] 태양 「Live Fast Die Slow」", "[Single-Out #602] 사이먼도미닉, 엔믹스 …". Source: curl of http://musicy.kr/?c=review (raw HTML, 41 KB) — dates and titles parsed directly. (WebSearch also independently reported "Single-Out #558" earlier, consistent with a still-incrementing series.)

### Review format — **two modes; mostly score-less prose**
- **Single-Out** (weekly singles roundup) = **no star score**; pure short-form critical prose with **multiple named critics writing on each single** (e.g. examples "[Single-Out #276-2] 마미손 …", "[Single-Out #235-5] 오이스터 …" carry critic bylines like [김병우], [열심히]). Source: https://musicy.kr/index.php?c=review (Single-Out permalinks via WebSearch).
- **Regular album reviews ("Album-Out")** use a **0–5 star system** (distinct from Single-Out). Source: WebSearch synthesis over musicy.kr review permalinks. (Treat the 0–5 album-scale claim as well-supported but secondary — derived from a search synthesis, not a single quoted scale graphic.)
- Genre-eclectic, comparatively low genre bias (covers metal, jazz, and is unusually receptive to idol pop).

### Discovery features
- Dedicated **"Best" section** = year-end results: live `?c=best` page surfaces "**올해의 앨범 / 올해의 싱글 / 올해의 신인**" (Album / Single / Rookie of the Year). Source: curl of http://musicy.kr/?c=best (raw HTML). Corroboration: an artist tweeting about being a "음악취향Y 선정 올해의 앨범 후보" (year-end album nominee). Source: https://x.com/xeudamusic/status/1883814429051302322
- Also publishes curated canon/playlist lists syndicated to streamers: "음악취향Y 선정 한국 발라드 Best 100" (Melon), "음악취향 Y 선정 댄스 Best 120" (Bugs). Sources: https://www.melon.com/mymusic/dj/mymusicdjplaylistview_inform.htm?plylstSeq=101591704 , https://music.bugs.co.kr/musicpost/624
- Editorial weight: editor Cho Il-dong is a standing judge for the 한국대중음악상 (Korean Music Awards); writers served on the 2007/2018 "한국 대중음악 명반 100" canon panels. Source: https://ko.wikipedia.org/wiki/%EC%9D%8C%EC%95%85%EC%B7%A8%ED%96%A5Y

### Reader features
- Live HTML confirms **search (검색/search) and tags (태그/tag)** are present; nav sections = About / Best / Choice / Review / Zine (`?c=about|best|choice|review|zine`). Source: curl of http://musicy.kr/?c=review (markers `검색`, `search`, `태그`, `tag`, `ad` present; nav `?c=` routes parsed).
- (unverified) Subscribe / RSS: no explicit newsletter or RSS marker found in the parsed HTML; not confirmed present.

### Business model
- (unverified) No paywall, membership, ad-network, or donation widget was confirmable from the fetched pages. The HTML contained an `ad` token but its purpose is unconfirmed. Volunteer/critic-collective operation is the (guess) likely model given its cafe origin and KMA-panel staffing, but no revenue source is directly evidenced. → flagged as an open question.

---

## 3. 재즈피플 (Jazz People) — ACTIVE

- **URL:** https://jazzpeople.co.kr/ ; subscription via https://themagazine.co.kr/ ; Instagram https://www.instagram.com/jazzpeople_magazine/
- **What it is:** Korea's monthly **jazz-culture print magazine** ("재즈문화지"), published by Kim Kwang-hyun (Seongnam, Gyeonggi). Included as the genre-specialist, print-first counterpoint to the web-native webzines.

### Active evidence (dated)
- The **2026.4 (April 2026) issue** is listed for sale on Aladin, listed as of 2026-03-26. Source: https://www.aladin.co.kr/shop/wproduct.aspx?ItemId=388957744 (via WebSearch)
- Subscription product page offers start months **March 2026 → June 2027**, and displays current monthly cover images — confirming ongoing publication. Source: https://themagazine.co.kr/product/jazz-people-재즈피플-연12회/2815/ (WebFetch).

### Review format
- Editorial mix: "최신 재즈관련 및 공연 소식, 예술인" (latest jazz news, live/performance news, artist profiles, reviews). Source: same themagazine.co.kr product page.
- Live site is artist/venue-centric: homepage HTML is dominated by jazz ensemble/format terms (쿼텟/트리오/퀸텟/듀오, venues 클럽에반스 / 천년동안도 / 낙원, artists 한상원, 이종원). Source: curl of https://jazzpeople.co.kr/ (raw HTML, parsed Korean term frequencies).
- (unverified) Whether print reviews carry a numeric/star score is not confirmable from the public web pages (content is behind print).

### Discovery features
- Site carries a **라이브 클럽 일정** (live-club schedule / gig calendar) at https://jazzpeople.co.kr/lives — a discovery feature the webzines lack. Source: https://jazzpeople.co.kr/lives (URL surfaced in WebSearch result list).
- **Artist pages** (e.g. /artists/627 "타임머신써킷"). Source: https://jazzpeople.co.kr/artists/627
- (unverified) Year-end "best jazz albums" feature: plausible for a monthly mag but not directly evidenced in fetched pages → open question.

### Reader features
- Member login (https://jazzpeople.co.kr/login) and account system present. Source: WebSearch result list.
- Print magazine, so the durable "reader feature" is **paid postal subscription**, not on-site reading.

### Business model — **paid print subscription (the sustainable model of the set)**
- **156,000 KRW / year for 12 monthly print issues.** Source: https://themagazine.co.kr/product/jazz-people-재즈피플-연12회/2815/ (WebFetch). This is the only outlet here with a clear, recurring paid-revenue model. (guess) Print ad pages + single-issue newsstand/Aladin sales likely supplement it.

---

## 4. stew! — RECENTLY ENDED (data point, not counted active)

- **URL:** https://kpop-stew.stibee.com/ (Stibee newsletter); landing https://page.stibee.com/archives/167678
- **What it was:** "맛있는 케이팝 뉴스레터 stew!" — a K-pop newsletter run by a ~7-person volunteer crew. Format = K-pop feature essays + artist deep-dives + fan-submitted event recaps + news, food-metaphor voice (not score-based reviews). Schedule: 5th/15th/25th monthly. Sources: https://blog.stibee.com/k-pop-newsletter/ , issue pages below.

### Why it's NOT in the active set — verified end date
- Issue numbering was probed directly: `…/p/131` = **127호**, `…/p/132` = **128호** (title "안녕은 영원한 헤어짐은 아니겠지요" — "goodbye isn't forever"), `…/p/133`+ return an empty 28 KB SPA shell (no issue) → the archive ceiling is **128호**. Source: curl of https://kpop-stew.stibee.com/p/131..139 (byte-size + `<title>` per issue).
- WebFetch of the final issue confirms: **issue 128, sent 2026-03-15**, explicitly "stew!를 마무리하는 … stew!의 정기적인 발행은 128호에서 끝나지만" — regular publication ends at 128, citing crew-life changes and shifts in the K-pop / newsletter market; leaves the door open to return. Source: https://kpop-stew.stibee.com/p/132
- (Anchor for timeline: issue 70호 "2주년" = 2024-03-15, so the run was ~2022-03 → 2026-03, ~4 years. Source: https://kpop-stew.stibee.com/p/73)

### Business model (relevant lesson)
- Free Stibee newsletter; volunteer crew; no evidenced paid tier. The farewell note attributes the shutdown partly to "newsletter market environment" shifts — i.e. the **free volunteer-newsletter model proved unsustainable**, a directly relevant cautionary data point for any newsletter-driven plan. Source: https://kpop-stew.stibee.com/p/132

---

## 5. weiv (웨이브) — FADING (secondary cautionary data point, excluded)

- **URL:** https://www.weiv.co.kr (founded 1999-08 by Shin Hyun-jun; indie/alternative focus)
- Returned **HTTP 500** on every WebFetch attempt during this session (homepage, /archives/category/review, the 음악비평 tag page) — could be transient or US-geo, but combined with reporting that **album reviews lapsed ~2021–2023** and it now runs "more like a one-person media project" with only occasional columns/interviews, weiv does not meet the "verifiably active right now" bar. Sources: WebSearch snippets over https://namu.wiki/w/weiv and https://ko.wikipedia.org/wiki/웨이브_(웹진) ; 500s observed on https://www.weiv.co.kr and https://www.weiv.co.kr/archives/tag/음악비평. Excluded; kept here so the next pass doesn't re-investigate it cold.

---

## Cross-outlet synthesis (for the blog's design decisions)

- **Scoring is split.** IZM commits to a **5.0 star scale** (and leans on it as a marketing hook — outlets report "IZM 평점 X점"). 음악취향Y deliberately runs its highest-volume series (Single-Out) **score-free / multi-critic prose**, reserving 0–5 stars for full album reviews. → A new site must consciously choose; "stars everywhere" is not the Korean-webzine default (the project already chose album-only 0–5/0.5 stars, which mirrors IZM, not Music Y).
- **Year-end canon is the shared discovery anchor.** Every surviving editorial outlet (IZM "올해의 앨범", Music Y "Best / 올해의 앨범·싱글·신인") leans on the year-end list as its signature recurring, shareable artifact. A 연말결산 feature is table-stakes for credibility.
- **Reader plumbing is uneven.** IZM has search + RSS + tags + podcast; Music Y has search + tags but no confirmed RSS/subscribe; the print mag (Jazz People) substitutes a gig calendar + artist pages. RSS/subscribe is a differentiator a modern site can win on cheaply.
- **Revenue reality.** Only the **paid print** outlet (Jazz People, 156k KRW/yr) shows a clean recurring-revenue model. The two web-native editorial outlets run on **patronage / volunteer labor** (IZM patron + free office; Music Y critic-collective). The **free volunteer newsletter (stew!) just died** citing market conditions. → Sustainability for a web-native music-review site is an unsolved problem in this market; patronage or a non-newsletter revenue line is the empirical pattern, and a free-newsletter-only plan has a fresh cautionary failure.

---

## Sources (fetched this session)

Primary (outlet's own live pages):
- https://www.izm.co.kr/ — IZM homepage (2026 © + current reviews + curl markers: search/RSS/tags)
- https://izm.co.kr/picks — IZM Picks / Editors' Choice / year-end singles / 2026 feature
- https://www.izm.co.kr/posts?id=33746 — IZM "2025 올해의 국내 앨범"
- http://musicy.kr/?c=review — Music Y Single-Out #604, dates 2026.06.08/06.01/05.25 (curl)
- http://musicy.kr/?c=best — Music Y "Best": 올해의 앨범/싱글/신인 (curl)
- https://musicy.kr/index.php?c=review — Music Y Single-Out permalink format (no score, multi-critic)
- https://jazzpeople.co.kr/ — Jazz People homepage (curl term-frequency)
- https://jazzpeople.co.kr/lives — Jazz People live-club schedule
- https://jazzpeople.co.kr/artists/627 — Jazz People artist page
- https://themagazine.co.kr/product/jazz-people-재즈피플-연12회/2815/ — 156,000 KRW/yr, Mar 2026–Jun 2027
- https://kpop-stew.stibee.com/p/132 — stew! final issue 128호, 2026-03-15 (farewell)
- https://kpop-stew.stibee.com/p/131 , /p/133..139 — stew! ceiling probe (curl titles)
- https://kpop-stew.stibee.com/p/73 — stew! 70호 = 2024-03-15 (timeline anchor)
- https://www.weiv.co.kr — weiv (HTTP 500 each attempt)

Secondary (corroboration only — WebSearch snippets / 403 to WebFetch):
- https://sports.khan.co.kr/article/202512031906003 — 리센느 'lip bomb' IZM 평점 4점 (2025-12-03)
- https://v.daum.net/v/20240911222907429 — 리센느 'LOVE ATTACK' IZM 4.5 record (2024-09)
- https://namu.wiki/w/이즘 — IZM 5-point scale / 4.5 list
- http://archive.izm.co.kr/faq.asp — IZM funding (Samyang Chemical patron, Hongdae office)
- https://ko.wikipedia.org/wiki/음악취향Y — Music Y "운영 중", 2006/2014 founding, KMA panel
- https://x.com/xeudamusic/status/1883814429051302322 — Music Y year-end album nominee
- https://www.melon.com/mymusic/dj/mymusicdjplaylistview_inform.htm?plylstSeq=101591704 — Music Y "발라드 Best 100"
- https://music.bugs.co.kr/musicpost/624 — Music Y "댄스 Best 120"
- https://www.aladin.co.kr/shop/wproduct.aspx?ItemId=388957744 — Jazz People 2026.4 issue (2026-03-26)
- https://blog.stibee.com/k-pop-newsletter/ — stew! schedule / K-pop newsletter roundup
- https://namu.wiki/w/weiv , https://ko.wikipedia.org/wiki/웨이브_(웹진) — weiv decline

---

## Final Korean summary (한국어 요약)

현재 활동 중인 국내 음악 매체 3곳을 확정했습니다.

1. **IZM(이즘)** — 활동 중. 2026년 K팝 리뷰(에스파 'Lemonade' 등) 게재, **5점 만점 별점제**(국내 만점 0개, 4.5점 20여 개), 연말결산 "올해의 앨범/싱글"이 시그니처. 검색·RSS·태그·팟캐스트 보유. 수익모델은 후원 기반(초기 삼양화학 대표 후원, 홍대 사무실 무상 제공) — 유료화/광고 없음.
2. **음악취향Y** — 활동 중("운영 중"). **Single-Out #604, 2026.06.08까지** 발행. 싱글 리뷰는 **점수 없이 여러 필자 평론**, 정규 앨범 리뷰만 0~5점. 연말 "Best(올해의 앨범/싱글/신인)" 섹션, 검색·태그 있음. 한국대중음악상 심사진과 연계. 수익모델은 (추정) 평론가 집단 자원봉사형 — 미확인.
3. **재즈피플(Jazz People)** — 활동 중(2026년 4월호 발매, 2027년까지 구독 가능). **월간 인쇄 매거진, 연 12회 156,000원 유료 구독** — 이 중 유일하게 명확한 정기 수익모델. 라이브 클럽 일정·아티스트 페이지 제공.

추가로 **stew!**(케이팝 뉴스레터)는 **2026-03-15 128호로 정기 발행을 종료** — "뉴스레터 시장 환경 변화"를 이유로 명시한, 무료 자원봉사 뉴스레터 모델의 지속불가능성을 보여주는 최신 사례라 별도 기록했습니다(활동 매체에서는 제외). **weiv(웨이브)**는 세션 내내 HTTP 500 + 앨범 리뷰 장기 중단으로 사실상 1인 운영 상태라 제외했습니다.

시사점: (a) 국내 웹진의 기본값은 "별점 전면 적용"이 아님 — IZM만 전면 별점, 음악취향Y는 핵심 시리즈를 무점수 평론으로 운영. (b) **연말결산은 신뢰도의 기본 장치**라 모든 생존 매체가 보유. (c) 웹 기반 음악 매체의 **지속가능한 수익모델은 미해결 과제** — 유료 모델은 인쇄(재즈피플)뿐이고, 무료 뉴스레터(stew!)는 방금 종료, 웹진들은 후원/자원봉사에 의존.
