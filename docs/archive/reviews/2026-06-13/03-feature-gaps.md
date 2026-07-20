# 03 — UX Gap Analysis (writer flow + reader flow)

Date: 2026-06-13. Input: `03a-feature-inventory.md` (code-derived inventory). All gaps below are
grounded in code (`path:line`) or doc lines. Inferences are prefixed `(guess)`.

Convention: each gap = **{audience · severity · evidence · what's blocking it}**. Gaps are split
into **structural / missing-feature** (a capability is absent or wired to fake data) vs **small
polish** (the capability exists, a corner is rough). Severity is product-impact for a one-person
music-review blog: H = blocks a core flow or ships a fake-looking feature to readers; M = real
friction or a half-finished capability; L = cosmetic / niche.

---

## Writer-flow gaps

### Structural / missing-feature

**W1 · Editorial critique has zero code — the product's defining feature is 100% unbuilt.**
- Audience: writer. Severity: **H**.
- Evidence: `grep -rni 'editorial\|critique' myblog_backend/app` returns **nothing**; the only
  `claude`/`anthropic` hits in backend are a doc comment (`research_service.py:6`) and a test
  string (`tests/api/test_research.py:20`). RFC self-states "Zero AI/LLM code in any of the 5
  repos" (`FEAT-ai-editorial-critique.md:53`). plan.md lists it as **draft, in Backlog**, not
  Active (`plan.md` Backlog block).
- Blocking: RFC is `draft`, needs owner accept (rule #5, human-only). Then OQ1 (method-doc
  single-source vs drift), OQ2 (model id + cost ceiling — first-ever paid usage on a $0-bias
  owner), OQ3 (facts-block source) must be settled (`FEAT-ai-editorial-critique.md:207-231`).
  Full deep-dive in §"The three required deep-dives".

**W2 · Artist drill-in has no "show full discography / load-more" toggle, and `album_count` /
`track_count` are computed but never shown.**
- Audience: writer. Severity: **M**.
- Evidence: the drill-in fetches a **fixed** `fetchArtistTopTracks(hero.id, 10)` +
  `fetchArtistAlbums(hero.id, 24)` with no offset paging and no follow-up fetch
  (`CommandPalette.tsx:321-324`). `ArtistDetail.tsx` renders those arrays flat with no load-more
  control and no album-type grouping (`ArtistDetail.tsx:144-171`). The service computes
  `album_count` / `track_count` for the hero (`artist_service.py:73`,
  `ArtistHero` schema `schemas.py:144-145`) and they cross the wire into `api.gen.ts:1420,1446`,
  but **no frontend file renders them** (`grep album_count myblog_front/src` → only
  `api.gen.ts`). So a writer drilling into a prolific artist sees a silently-truncated 24-album
  discography with no signal that more exist and no way to page. The repo layer *does* support
  paging (`album_repo.list_by_artistId_artist` takes `limit`/`offset`,
  `album_repo.py:216-227`) and the route exposes `offset` (`artists.py:23`) — the gap is purely
  frontend (no toggle calls the next page).
- Blocking: nothing technical — backend paging + counts already exist. This is the **BUG-19
  follow-up "artist detail toggle"** (full deep-dive in §"The three required deep-dives").

**W3 · Discography has no album-type filter (정규/EP/싱글/컴필) toggle.**
- Audience: writer. Severity: **L**.
- Evidence: the discography query orders by `popularity DESC, release_date DESC` with **no
  `album_type` filter or grouping** (`album_repo.py:195-198`,
  `_list_by_artistId_artist_filter`); `album_type` is carried per-row and rendered inline as a
  text suffix only (`ArtistDetail.tsx:164`). For an artist with many singles, the 24-row cap
  (W2) fills with singles and can crowd out the albums the writer actually wants to review. A
  type toggle (앨범만 / 전체) is the natural partner to W2's load-more.
- Blocking: the model has `Album.album_type`; the music service would need a `?album_type=`
  query param on `/artists/{id}/albums` + a frontend toggle. Small additive change. Belongs in
  the same "artist detail toggle" follow-up as W2.

**W4 · No "other albums by this artist" inline expansion in unified search — by deliberate
design, but the only escape hatch (artist drill-in) is the under-built W2 panel.**
- Audience: writer. Severity: **L** (working as designed; flagged for completeness).
- Evidence: BUG-19 explicitly made "other albums by this artist" a **non-goal** of search and
  pushed it behind artist-detail (`BUG-19-...md:17` Non-goals, `:72` "must not expand into other
  albums … belongs behind artist-detail"). That decision is sound; the residual gap is that the
  designated home for that capability (the drill-in) is itself incomplete (W2/W3). So the
  BUG-19-era promise "tap the artist to see their other albums" is only ~partially delivered.
- Blocking: resolving W2 closes this.

### Small polish

**W5 · Editorial method doc is applied by hand, not in the product — a daily manual step.**
- Audience: writer. Severity: **M** (it is the writer's actual current workflow).
- Evidence: `review-critique-method.md` is "applied **by hand** in a chat tool; it is not wired
  into the product" (`FEAT-ai-editorial-critique.md:53-56`). Every review the owner writes today
  requires copy-pasting the draft + method doc into a separate chat tool. This is the friction
  W1 is meant to remove; listing it here because the *gap as experienced today* is a writer
  inconvenience, not just a missing endpoint.
- Blocking: same as W1.

**W6 · Research note execution depends on an out-of-band local poller (`claude -p`), not the
product.**
- Audience: writer. Severity: **L** (works, but fragile/host-bound).
- Evidence: research POST only flips a `queued` DB row; a `$0` local poller
  (`scripts/research_poller.py`) runs `claude -p` and writes the note back — "there is no
  server-side AI call" (`03a-feature-inventory.md:72-75`; plan.md FEAT-album-research-notes
  "EXECUTION BACKEND PIVOTED 2026-06-11"). If the owner's laptop/launchd is off, a 조사하기 click
  sits `queued` forever with no server-side fallback (the paid researchSQS/Lambda is dormant).
- Blocking: this is an accepted cost/architecture decision ($0-bias), not a bug. Flagging the UX
  consequence: queued-forever has no user-visible timeout/SLA in the UI.

---

## Reader-flow gaps

### Structural / missing-feature

**R1 · `/genres` ships a polished interactive graph over HARDCODED sample data — readers see a
fake feature.**
- Audience: reader. Severity: **H**.
- Evidence: `/genres` renders `GenreMapTabs` which (and every child:
  `GenreClusterMap.tsx:5`, `GenreConstellation.tsx:5`, `GenreGraphSample.tsx:16`,
  `GenreDetailPanel.tsx:2`) imports from **`@lib/genres-sample`** — a hardcoded seed. It never
  calls the backend: `grep 'api/genres' myblog_front/src/pages/genres myblog_front/src/components`
  finds **no** `/api/genres/tree` call. Meanwhile the real genre system is **prod-live**: 982/982
  albums labeled, `GET /api/genres/tree` returns 12 seeds (plan.md FEAT-genre-system Steps 1-4
  DONE 2026-06-12). So the most visually-impressive reader page is disconnected from the real,
  shipped data — a reader exploring `/genres` is browsing fiction.
- Blocking: FEAT-genre-system Step 6 ("public `/genres` map page with owner-editable DB
  definitions" — plan.md) is **not yet shipped** (only Steps 1-4 done; Steps 5-7 remain). The
  page → API wiring is the unbuilt step. This is the single biggest reader-facing
  fake-feature today.

**R2 · No public artist hub/page — readers can't browse by artist at all.**
- Audience: reader. Severity: **M**.
- Evidence: `find myblog_front/src/pages -iname '*artist*'` → **none**; the only artist UI is the
  writer-only `ArtistDetail.tsx` inside the auth-gated CommandPalette
  (`CommandPalette.tsx:19,392`). The music service already serves a public, DB-only artist hero +
  discography + top-tracks (`artists.py:19-78`, all unauthed reads), and the project roadmap
  states "artist = hub page + search" as a decided feature (memory `project-feature-roadmap`).
  A reader who reads a review of album X by artist Y has no link to "see Y's other reviewed
  albums" — `[slug].astro` carries `artistIds` (`[slug].astro:151`) but links nowhere.
- Blocking: a new `/artist/[id]` (or by-spotify) Astro page consuming the existing
  `/api/music/artists/*` endpoints. The data + API are done; the reader page is missing. (guess)
  Modest scope — the writer `ArtistDetail` component is mostly reusable.

**R3 · `POST /api/metrics/batch` returns likes/comments to readers, but there is NO write path —
the numbers can only ever be zero.**
- Audience: reader. Severity: **L** (vestigial).
- Evidence: the metrics route is read-only — `repo.get_many` then returns `{likes, comments}`
  (`metrics.py:11-20`); there is **no** like/comment POST route or UI (`grep POST.*like /
  onLike / addComment` → none; the only hits are the bootstrap tables `post_comments` /
  `post_likes` in `schema_v0.sql:56,65`). The roadmap dropped comments/likes (memory
  `project-feature-roadmap` "comments/likes dropped"). So this endpoint surfaces counts that no
  user action can increment.
- Blocking: a decision — either remove the dead read endpoint + tables, or it's intentionally
  parked. Not a feature to *build*; a cleanup/clarify item. (Cross-ref the code-audit's dead-code
  findings.)

### Small polish

**R4 · `/` and `/reviews` are the same island under two routes — no cross-link from a review to
the `/genres` map or to an artist.**
- Audience: reader. Severity: **L**.
- Evidence: both routes render `ReviewsIndex` with different `variant`
  (`03a-feature-inventory.md:20-21`). `ReviewsIndex.tsx` has a genre **filter** but no link out
  to the `/genres` page or any per-genre landing (`grep '/genres\|href=.*genre' ReviewsIndex.tsx`
  → none). The reader's discovery graph is shallow: review → (filter) → review, with no
  genre-page or artist-page hop. Once R1 (real /genres) and R2 (artist page) exist, adding these
  cross-links is the cheap connective tissue.
- Blocking: depends on R1 + R2 existing first.

**R5 · Track-by-track list on the read page is a client fetch with (guess) no explicit
empty/error state surfaced to the reader.**
- Audience: reader. Severity: **L**.
- Evidence: the track list is fetched client-side from the music API
  (`[slug].astro:147-173,606-614`, `scripts/albumDetail.fetch.client.ts`; inventory C). (guess)
  If the music Lambda is cold/down, the section behavior under failure isn't obvious from the
  Astro page alone — worth a one-look QA pass. Low priority (graceful-degradation, not broken).
- Blocking: needs a live-DOM check (out of scope for this static read).

---

## The three required deep-dives

### A. BUG-19 follow-up "artist detail toggle"

**What BUG-19 was.** The writer/global music-search 1-hop cross-expansion + per-bucket offset fix
(`BUG-19-writer-music-search-context.md`, shipped 2026-05-30). It **deliberately excluded**
"other albums by this artist" from search and routed it to artist-detail
(`BUG-19-...md:17,72` Non-goals).

**Where the artist detail lives.** There is **no public reader artist page**
(`find myblog_front/src/pages -iname '*artist*'` → none). The only artist-detail surface is the
**writer-only drill-in**: `ArtistDetail.tsx`, rendered inside the auth-gated CommandPalette
(`CommandPalette.tsx:19,392`), fed by `loadArtistDetail` (`CommandPalette.tsx:313-330`). Backing
API = `/api/music/artists/{id}` + `/{id}/albums` + `/{id}/top-tracks` + `/by-spotify/{id}`
(`artists.py:19-78`), all DB-only/unauthed (rule #9 honored, `artists.py:30-32`).

**Actual current state vs the gap (the "toggle"):**
1. **Albums fetch is a fixed, unpageable 24.** `fetchArtistAlbums(hero.id, 24)`
   (`CommandPalette.tsx:323`), rendered flat (`ArtistDetail.tsx:144-171`). There is **no
   load-more / "전체 보기" toggle** even though the route + repo support `offset`
   (`artists.py:23`, `album_repo.py:216-227`). A prolific artist's discography is silently
   truncated at 24.
2. **Top-tracks fixed at 10** (`CommandPalette.tsx:322`), also no expand.
3. **`album_count` / `track_count` are computed and sent but never displayed**
   (`artist_service.py:73`, `schemas.py:144-145`, present in `api.gen.ts:1420,1446`,
   **zero** render-site in `myblog_front/src`). So the panel can't even say "24 of 137" — the
   total is on the wire, unused. This is the most concrete "unfinished toggle" signal: the data
   for a "show all N" affordance was plumbed through and then never wired to UI.
4. **No album-type (정규/EP/싱글) filter toggle** — `album_type` is rendered as inline text only
   (`ArtistDetail.tsx:164`); the query has no type filter (`album_repo.py:195-198`).

**Verdict:** The "artist detail toggle" is a **real, unfinished gap (Severity M)**. The drill-in
is functional but capped and count-blind; the backend already supports the paging the toggle
needs. Closing it = a frontend load-more (and optionally a type filter) + surfacing
`album_count`/`track_count`. No backend work strictly required for load-more. See W2/W3/W4.

### B. Spotify RFC remaining / deferred items

`FEAT-spotify-library-sync` is **done + prod-live + archived** (album-level two-way Library
mirror; `FEAT-spotify-library-sync.md:3`). What remains **explicitly deferred or uncaptured**:

1. **In-app PKCE OAuth flow (D27) — still deferred.** The Spotify refresh token is minted
   out-of-band by `scripts/spotify_bootstrap_token.py`, not an in-app flow; "building a
   self-service OAuth UI … is deferred (**D27**)" (`FEAT-member-dashboard.md:197-200`). The 연동
   tab is "a thin status surface, not an OAuth flow … D27 defers the in-app PKCE flow to a later
   RFC" (`SpotifyIntegrationTab.tsx:3-6`). **No RFC exists** for this. Consequence: token
   re-auth after a Spotify revoke is a manual CLI run, not a button. Severity: **L** for a
   single-owner site (the owner can run a script), **M** if/when multi-user (R2/FEAT-multi-user).

2. **Scheduled / auto reconcile of the Library — deferred by choice.** Library sync is
   **explicit-only** (a 동기화 button); "Auto / scheduled reconcile … No EventBridge rule
   (unattended writes to the owner's real account are high blast-radius). Documented future
   option behind a flag" (`FEAT-spotify-library-sync.md:33-35`). Uncaptured future work; safe to
   leave deferred. Severity: **L**.

3. **Playlists — permanent non-goal.** "Playlists (album-level Library sync only)"
   (`FEAT-spotify-library-sync.md:33`, Non-goal). Not a gap; recorded so it isn't re-proposed.

4. **Un-catalogable Library album handling (OQ3) — shipped as "UI note now, counter later".**
   An album in the Spotify Library but never in our catalog can loop "enqueued, never appears";
   the resolution was a UI note, with a miss-counter `needs_attention` cap deferred
   (`FEAT-spotify-library-sync.md:220-222`). Minor deferred robustness item. Severity: **L**.

5. **Spotify write scopes beyond Library (playlist-export, etc.) — D11 lineage, mostly closed.**
   D11 deferred "save album / playlist export / library modify" (`FEAT-member-dashboard.md:398`);
   library-sync delivered the save/modify half. **Playlist-export remains uncaptured** (folded
   into the playlists non-goal above). Severity: **L**.

6. **`FEAT-new-release-feed` (Frozen idea) — the largest uncaptured Spotify-adjacent reader
   feature.** EventBridge → fetch recent albums by the owner's reviewed artists →
   `artist_new_releases` → `GET /api/music/feed/new-releases` → a main-page card
   (`plan.md` Frozen, FEAT-new-release-feed (L)). This is **frozen (idea only, no RFC)** and is
   the one Spotify-flavored *reader* feature that's wholly unbuilt. Note the
   album-catalog-ingest worker already discovers new releases by catalog artists
   (`03a-feature-inventory.md:215-218`), so the data-fetch half has a precedent — but there is no
   reader feed. Severity: **M** as a reader-discovery feature; correctly frozen.

**Caveat to note (not Spotify-deferral but a Spotify reliability fact):** memory
`reference-spotify-devmode-endpoints-live` — `new-releases` returns 200 but ROTTEN data; a
`FEAT-new-release-feed` must source from `/artists/{id}/albums` (fresh), not `/browse/new-releases`.
Bake this into that RFC when it starts.

### C. AI editorial critique API

**Status:** RFC `FEAT-ai-editorial-critique.md` is **`draft`** (`:3`), parked in plan.md
**Backlog** (not Active), "needs owner accept before Active" (plan.md Backlog block). It is named
"**the product's defining feature**" (plan.md; memory `project-ai-editorial-greenfield`).

**What exists vs what does not:**
- **Exists:** the *methodology* only — `review-critique-method.md` (v2.5), a polished
  English-rules/Korean-output spec the owner currently pastes into a chat tool by hand
  (`review-critique-method.md:1-104`; `FEAT-ai-editorial-critique.md:53-56`). And the
  *precondition data* — a draft already resolves to its album's DB facts via the `post_albums`
  M:N link with **no schema change** (`FEAT-ai-editorial-critique.md:64-69`); `Post.extra`
  (JSONB) is a ready zero-migration persistence sink (`:70-71`).
- **Does NOT exist:** **any code.** `grep -rni 'editorial\|critique' myblog_backend/app` → **0
  hits**. No `llm_client.py`, no `editorial_service.py`, no `routes/editorial.py`, no `anthropic`
  dependency, no `ANTHROPIC_API_KEY` in settings/Secrets, no prompt asset, no
  `apigateway.tf editorial_critique_post`, no golden-eval test. RFC confirms "Zero AI/LLM code in
  any of the 5 repos" (`:53`).

**Concrete next steps (from the RFC's own plan):**
1. **Owner accept** the draft RFC (rule #5, human-only) → promote to Active.
2. **Settle 3 blocking OQs** (`:207-231`): OQ1 method-doc single-source (recommend vendored copy
   + sha gate, `:216`); OQ2 model id + input-token cost ceiling (the first paid usage on a
   $0-bias owner — confirm current model id via the `claude-api` skill, do **not** hardcode;
   `:218-223`); OQ3 facts-block source (recommend direct shared_db read, `:224-228`).
3. **Step 1 (backend, local-only):** `llm_client.py` + `editorial_service.py` +
   `routes/editorial.py` + `schemas.py` (CritiqueResult) + `anthropic` dep + settings +
   `tests/test_editorial_critique.py` golden eval (wrong-date / thin-viewpoint / clean). Proven by
   curl under `ENV=local` **before** paying any infra/contract tax (`:162-187`).
4. **Step 2 (prod):** `apigateway.tf editorial_critique_post` (copy `buckets_post` JWT, **never**
   `categories_post`) + openapi regen + workspace contract merge (`:189-204`).

**How far from existing:** **maximally far — it is greenfield (0% code).** Everything upstream is
ready (data model, method doc, the `buckets_post` JWT pattern to copy, the `Post.extra` sink), so
the *path* is short and well-specified, but **not a single line is written**, the RFC is unaccepted,
and three cost/architecture OQs are open. The defining feature is a 2-step backend RFC away from a
first curl-provable slice — pending only an owner go.

---

## Biggest gaps — ranking

1. **W1/C · Editorial critique = 0% built** (H, writer). The product's defining feature has no
   code; everything that would feed it is ready. Highest leverage, fully greenfield, gated on
   owner accept + 3 OQs.
2. **R1 · `/genres` is a fake-data showcase** (H, reader). The most polished reader page renders
   hardcoded seed while the real 982-album genre system is prod-live and unconsumed by it.
   FEAT-genre-system Step 6 closes it.
3. **R2 · No public artist page** (M, reader). The DB-only artist API is fully shipped and
   unauthed; readers (and the read page's `artistIds`) have nowhere to link. A new `/artist/[id]`
   page over existing endpoints.
4. **W2/W3/A · Artist drill-in "toggle" unfinished** (M, writer — the BUG-19 follow-up).
   Discography capped at an unpageable 24, `album_count`/`track_count` plumbed-but-unrendered, no
   album-type filter. Backend paging already exists; pure frontend completion.
5. **B6 · FEAT-new-release-feed frozen** (M, reader). The one unbuilt Spotify-adjacent reader
   feature; correctly frozen, flagged so the rotten-`new-releases`-endpoint caveat is captured.

Polish-tier (L): W3 type filter, R3 vestigial metrics endpoint/tables, R4 reader cross-links, R5
track-list failure state, W6 research-poller queued-forever, Spotify D27/auto-reconcile/playlist
deferrals.

---

## openQuestions

1. **Editorial critique — accept now or hold?** It's the defining feature but unaccepted draft
   with an open cost OQ (first paid LLM usage on a $0-bias owner). Is the intent to ship Phase 0
   next, or does it stay parked behind FEAT-genre-system Steps 5-7? (Affects whether W1/C is "the"
   priority.)
2. **`/genres` real-data wiring — is FEAT-genre-system Step 6 the agreed home for R1**, or should
   a thin "swap sample → `/api/genres/tree`" fix land sooner so readers stop seeing fiction? The
   gap is live in prod *now* while the full RFC has Steps 5-7 outstanding.
3. **Public artist page (R2) — in scope before FEAT-multi-user-accounts, or bundled with it?**
   The single-owner artist hub needs no auth/user model and the API is ready; confirm it isn't
   being (guess) implicitly blocked on the multi-user RFC.
4. **Artist drill-in toggle (A/W2) — is the 24-album cap a deliberate writer-focus choice** (keep
   the picker tight) or an unfinished follow-up? If deliberate, surfacing `album_count` ("24 of
   N") may be enough without full paging.
5. **Vestigial metrics/likes/comments (R3) — remove or keep parked?** Confirm comments/likes are
   permanently dropped so the dead read endpoint + `post_comments`/`post_likes` tables can be
   cleaned (cross-ref code-audit dead-code list).

ASSUMPTIONS made to proceed (also in openQuestions above): (i) "artist detail" in the brief = the
writer-only drill-in, since no public artist page exists; (ii) severities are scaled to a
single-owner blog, so multi-user-only gaps (D27 PKCE) are rated L today.
