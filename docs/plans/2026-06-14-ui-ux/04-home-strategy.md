# 04 — Home Page Strategy

**Scope.** Three distinct home-page CONCEPTS for `/`, each grounded in what the static
Astro `blog` collection + the one DB-backed input (`/genres` `album_count`) can actually
fill today, judged against the bucket-vs-publication premise. This doc presents **options +
trade-offs**; it does **not** decide. Final picks are the owner's (the design-decision OQs
live in `OPEN_QUESTIONS.md` and the open lines at the foot of this doc).

**Inputs.** Builds on Task 1 (`01-current-frontend.md` — the home today is a duplicate of
`/reviews`; the bucket is real but 100% owner-private), Task 2 (`02-reference-teardown.md` —
authority comes from voice + curated canon, not crowd aggregation), and Task 3
(`03-positioning.md` — recommended "Letterboxd-foundation / IZM-surface" model, with the
public/private boundary as the crux). Its baseline is the already-decided two-lane editorial
home in `docs/rfcs/FEAT-home-redesign.md` (draft).

**Evidence rule.** Code/data claims cite `file_path:line`. Reference claims cite the 02
teardown section or a URL. Anything unverifiable is marked *speculation*.

**Data-confirmation note (replaces the "Postgres MCP" step).** No Postgres MCP is connected,
and the home is a **static** Astro site (`output: 'static'`, `01-current-frontend.md` "Pages &
routes" intro). The home's data is therefore the `blog` **content collection** read at build
(`index.astro:12`), normalized by `buildReviewCards` (`reviews.ts:108-148`); the *only*
DB-backed home input is `/genres` `album_count`, fetched **client-side** at runtime
(`genres.ts:61-65`; `api.gen.ts:868-894`). So the content schema (`content.config.ts`) IS the
right evidence for what each module can be filled with. Every module below cites the concrete
field that fills it, and flags where the data **does not exist yet**.

---

## Intro — relationship to FEAT-home-redesign

`FEAT-home-redesign.md` (draft) has **already chosen** the home direction: a two-lane editorial
front page — a public reader module stack (BNM hero / Latest reviews / Browse-by-genre / By-the-
numbers) plus an auth-gated writer strip, with reader drag-personalization behind a "홈 편집"
toggle and empty-state as a first-class requirement (`FEAT-home-redesign.md` "Target state",
"Module registry", decisions #1-5). Per working rule 6, this doc does **not** re-propose that as
new.

What this doc adds is a **stress-test**: it frames the decided two-lane home as **one of three
distinct concepts** (Concept B), bracketed by a more bucket-forward concept (Concept A — a
personal-record/dashboard home) and a leaner editorial-feed concept (Concept C — a latest-reviews
front page). The point is to let the owner **confirm or adjust** the FEAT-home-redesign direction
against two honestly-different alternatives — to see what it gives up and what it over-builds —
not to reopen a settled decision. All three are sized against the same data reality, so the
comparison is about *tone and bucket-fit*, not feasibility hand-waving.

The throughline question (from `03-positioning.md`): **a home that buries the bucket fails the
premise.** Each concept is scored on whether it projects the owner's private bucket record into
public editorial output, or just shows reviews next to a hidden collection (the Bandcamp two-
surface anti-pattern, `02-reference-teardown.md` Bandcamp §3).

---

## Concept A — Personal-record / dashboard home

**One-liner.** The home reads as *the owner's living record of what they're listening to and
ranking* — closest to the bucket foundation, closest to a Letterboxd logged-in profile front
(`02-reference-teardown.md` Letterboxd §1-2). The publication tone is layered *on top of* a
visibly-personal spine, not the other way around.

**What it surfaces (top to bottom), and what it ranks/features by:**

1. **Now / recently-*reviewed* strip** — the owner's most-recent rated albums as a horizontal
   record-shelf (cover + ★), newest first. Ranks by `date` desc. *(A true "recently-rated" shelf —
   including rated-but-unwritten bucket entries — needs the unbuilt public-bucket read path; see
   DATA CONFIRMATION below + `03-positioning.md` Option 2/3. Absent that, it degrades to recently
   reviewed, i.e. published posts only.)*
2. **명반 canon + year-end Picks rail** — the owner's curated standing lists (≥4.0★ canon,
   non-ranked year-end Picks), projected as editorial selections (`03-positioning.md` Model
   recommendation; `02-reference-teardown.md` IZM §3 BORROW #3/#5).
3. **Latest reviews** — the same review feed, but framed as "what I've written up," secondary to
   the record shelf.
4. **By the numbers** — honest counts (reviews / albums covered / genres), framing the record's
   scale.
5. **Writer strip** (auth-gated) — pinned, as in FEAT-home-redesign.

**DATA CONFIRMATION (per module):**

- *Now / recently-rated strip* — fillable from `blog` posts that carry a `rating`
  (`content.config.ts:118` top-level `rating`, `:119` `ratingScale`; normalized 0–5 by
  `reviews.ts:131`), sorted by `date` (`content.config.ts:77`). **BUT** this only shows
  *published, written-up* albums — a post must exist. The richer "everything I've bucketed and
  rated, prose or not" version **does NOT exist as home data**: buckets are owner-private behind an
  authed `GET /api/buckets` (`01-current-frontend.md` "Public vs private boundary";
  `buckets.ts:6-7`), and there is **no public bucket read path and no rated-but-unwritten public
  record** today (`03-positioning.md` Option 3 — likely a `shared_db` visibility column-add). So at
  the home level this strip degrades to "recently *reviewed*," not "recently *rated*."
- *명반 canon + year-end Picks rail* — partially fillable: a ≥4.0★ canon can be **computed from
  published reviews' `rating`** (`content.config.ts:118`) with no new data. But a curated,
  *ordered*, blurbed Picks **list object does NOT exist** — there is no editor-lists feature
  (`FEAT-home-redesign.md` non-goals: "No editor-curated lists feature… unbuilt"), and a bucket
  carries no list-level public metadata today (`03-positioning.md` "non-album bucket members" OQ).
  A blurb-free ≥4.0★ filter ships now; a true curated Picks list is **inert / unbuilt**.
- *Latest reviews* — `buildReviewCards` over the `blog` collection, date-desc
  (`reviews.ts:108-115`). Real, ships now.
- *By the numbers* — counts derivable at build from the `blog` collection: review count
  (`reviews.length`), distinct genres (`allGenres`, `reviews.ts:51-63`), distinct years
  (`allYears`, `reviews.ts:81-85`). "Albums covered" ≈ review count (one album per review). All
  honest, no new data.
- *Writer strip* — same as Concept B (see there).

**Near-zero-content behavior (posts=0 today).** Harsh. The whole concept is built on "the owner's
record," and with 0 published posts the record shelf, canon, and by-the-numbers are all empty
(`01-current-frontend.md` "What the home surfaces today" — live state is the empty-state line).
Worse than the other concepts, because this concept's *identity* is the volume of personal record
it shows; an empty record-shelf reads as "this person has logged nothing," which is the opposite
of the intended impression. Mitigation would require either (a) surfacing the **private bucket**
publicly so the record isn't empty even before prose (Option 2/3 in `03-positioning.md` — net-new
public bucket API + tone risk), or (b) leaning hard on the writer strip + an empty-state editorial
card (the FEAT-home-redesign decision #4 posture).

**Trade-offs + does it harm the bucket foundation?** *Best bucket-foundation fit of the three* —
it is the only concept whose front-page *spine* is the personal record, exactly the
"organize into a personalized record" half of the premise (`01-current-frontend.md` bucket gap
#1). **But** it pays for that fit two ways: (1) it has the **worst empty state**, and (2) to be
honestly *personal* (not just "reviewed albums") it **depends on the unbuilt public-bucket
projection** — without it, the "record" is just the review feed re-skinned, so the concept's
differentiator is the part that doesn't exist yet. It also risks tipping toward "private
spreadsheet made public" rather than a magazine (`03-positioning.md` Model A risk) — the publication
half is the layer most at risk of feeling thin.

---

## Concept B — Two-lane editorial front page *(the FEAT-home-redesign direction)*

**One-liner.** A magazine front page: a curated editorial reader lane (BNM hero leading) with an
auth-gated writer lane pinned on top. This is the decided baseline (`FEAT-home-redesign.md` "Target
state") — included here so it can be compared, not re-proposed.

**What it surfaces (top to bottom), and what it ranks/features by:**

1. **Writer strip** (auth-gated, pinned under header) — `버킷에 담은 앨범 N장 · 이어쓸 초안 N개 ·
   [새 평론 쓰기 →]` (`FEAT-home-redesign.md` "Target state" #2). Logged-out readers never see it.
2. **Best New Music hero** — one large featured pick + up to 2 supporting, ranked by
   `selectFeatured` (BNM-first, then highest-rated; `reviews.ts:40-48`).
3. **Latest reviews** — editorial card feed, date-desc.
4. **Browse by genre** — share-bars mirroring `/genres`, click → filtered `/reviews`.
5. **By the numbers** — honest counts.
   (Reader-personalizable order + hide/restore behind a "홈 편집" toggle; `FEAT-home-redesign.md`
   OQ1 resolved.)

**DATA CONFIRMATION (per module):**

- *Writer strip* — drafts count is fetchable (`/api/posts*`, used by `/drafts`,
  `01-current-frontend.md` `/drafts` row). The **bucket count** is the open input: today the home
  can only read it from the localStorage SWR cache the board writes (`BUCKETS_KEY='lf_buckets'`,
  `member.ts:129`; `bucketCount()` reads it, `member.ts:138-141`) — which is **empty until the
  owner has opened `/profile` in that browser** and is per-browser, not authoritative
  (`FEAT-home-redesign.md` OQ2, still open; `01-current-frontend.md` "localStorage is used only as
  SWR cache"). A reliable count needs a light authed read of `GET /api/buckets`
  (`buckets.ts:139`). Either way this lane is **owner-only**, so it never affects the public face.
- *Best New Music hero* — `bestNew` frontmatter flag (`content.config.ts:122`) via `selectFeatured`
  (`reviews.ts:41`). Real field; **but** `selectFeatured` falls back to "latest 3" when **no post
  has `bestNew`** (`reviews.ts:42-43`), and no post sets it at 0 content — so the "hero" is just the
  3 newest until the owner flags a BNM. The *editorial anointing* tone (`02-reference-teardown.md`
  Pitchfork §3, IZM §1) only appears once `bestNew` is actually used.
- *Latest reviews* — `buildReviewCards`, date-desc (`reviews.ts:108-115`). Real, ships now.
- *Browse by genre* — `album_count` per genre, fetched **client-side** from `GET /api/genres/tree`
  (`genres.ts:61-65`; `album_count` field at `api.gen.ts:873`, mapped at `genres.ts:47`). This is
  the **only DB-backed module**, and it's **runtime-fetched, not build-time** — so the module is
  empty/loading until the API responds and isn't in the static HTML (same caveat as `/genres`,
  `01-current-frontend.md` `/genres` row). `album_count` counts **album_genres rows, not reviews**
  — so this module can show real genre share *even at 0 published reviews* (the catalog is larger
  than the review set). This is the one module that is **not** hostage to the empty content set.
- *By the numbers* — build-time counts from the `blog` collection (as Concept A). Honest, ships now.

**Near-zero-content behavior (posts=0 today).** Designed for it — this is the explicit point of
FEAT-home-redesign decision #4: at 0 reviews, hero + latest grid collapse to a single "첫 평론을
준비 중" editorial card, and the writer strip is given visual prominence
(`FEAT-home-redesign.md` "Empty-state strategy"). Browse-by-genre can still render real
`album_count` bars (catalog ≠ review set) — **but only once its client-side fetch resolves; it is
not in the static HTML and is invisible to crawlers / no-JS / cold first paint** (DATA CONFIRMATION
above). So the "isn't entirely empty" edge over Concept A holds for an interactive reader *after
hydration*, not at first paint or for SEO — unless `album_count` is snapshotted at build (an OQ
below). Best behaved of the three at near-zero content, *with that qualifier*.

**Trade-offs + does it harm the bucket foundation?** Strongest *publication* tone and best empty
state, and it keeps the rating gated behind the article (the home reads as a publication, not a
scoreboard — `02-reference-teardown.md` IZM BORROW #7). **Bucket-foundation fit is its weakness:**
the bucket appears **only inside the auth-gated writer strip** — i.e. it stays a private workflow
shortcut, never a public editorial surface. So this concept satisfies the *publication* premise
fully but the *bucket* premise only privately; it does **not by itself** close `01-current-
frontend.md` bucket gap #1 (no public projection of the personal record). It is the safest, most
buildable concept, at the cost of leaving the bucket's public projection to a later, separate
decision (`03-positioning.md` Option 2/3). It does not *harm* the foundation (the bucket still
drives the owner's work), but it doesn't *advance the public half* of it either.

---

## Concept C — Latest-reviews editorial feed (lean / IZM-minimal)

**One-liner.** The leanest editorial front page: essentially the current `/` but reframed as a
real home — a single reverse-chronological review feed with a light masthead, no module stack, no
personalization. Closest to IZM/Bandcamp Daily's home (`02-reference-teardown.md` IZM §1, Bandcamp
§1: a hero/lead item over reverse-chronological rails, nothing else).

**What it surfaces (top to bottom), and what it ranks/features by:**

1. **Editorial masthead** — a real wordmark + tagline (replacing the literal `<h1>Reviews</h1>`,
   `index.astro:22`), not a module.
2. **Lead review** — the single newest (or single `bestNew`) review, large.
3. **Latest reviews feed** — reverse-chronological cards, date-desc.
4. **Writer strip** (auth-gated) — optional, same as Concept B.

No browse-by-genre module, no by-the-numbers, no reader personalization.

**DATA CONFIRMATION (per module):**

- *Editorial masthead* — static copy + existing wordmark (`index.astro:38`). No data dependency.
- *Lead review* — `selectFeatured(reviews)[0]` (`reviews.ts:40-48`) or simply `reviews[0]`
  (date-desc, `reviews.ts:115`). Real; falls back to newest when no `bestNew`
  (`content.config.ts:122`).
- *Latest reviews feed* — `buildReviewCards` (`reviews.ts:108-148`), the exact data the home reads
  today (`index.astro:12`). Real, ships now, **zero new data**.
- *Writer strip* — same bucket-count caveat as Concept B (localStorage SWR vs authed read).

**Everything that does NOT exist is simply omitted** — there is no genre module (so no client-fetch
dependency), no by-the-numbers, no canon/Picks. This is the only concept with **no data gaps**,
because it surfaces only the one thing that already fully exists.

**Near-zero-content behavior (posts=0 today).** Degrades to roughly today's empty-state
(`index.astro:27-30`), but a lean concept can own that honestly: one "첫 평론을 준비 중" editorial
card + the writer strip, with no empty module skeletons to look broken. Graceful, but visually
*sparse* — there's nothing to look at but the empty card, because there are no other modules to
carry weight (unlike Concept B's genre bars).

**Trade-offs + does it harm the bucket foundation?** Lowest build cost (it's close to the current
page, reframed), most honest, cleanest IZM-style publication tone. **But it harms the bucket
foundation the most:** it surfaces *only* reviews and (optionally, privately) the writer strip —
the bucket has **zero public presence and no path to one** in this concept. It is essentially
"become a small IZM," which edges toward the forbidden "just become Pitchfork/IZM" conclusion
(`03-positioning.md` Model B; SHARED CONTEXT forbidden conclusion) — it makes the magazine the
whole product and discards the differentiator. It also wastes the genre Outliner already shipped
(`01-current-frontend.md` `/genres`) by not surfacing it on the home. Good as a *fallback floor* if
the owner wants to ship the smallest honest home now and defer everything else; weak as a
destination.

---

## Comparison table

| Concept | Surfaces first | Ranks/features by | Bucket-foundation fit | Near-zero behavior | Build cost |
|---|---|---|---|---|---|
| **A — Personal-record / dashboard** | Owner's recently-rated record shelf | `date` desc on rated posts; ≥4.0★ canon | **Best** — record is the front-page spine — *but* honest version needs the unbuilt public-bucket projection (`03-positioning.md` Option 2/3); without it the "record" is just the review feed re-skinned | **Worst** — identity *is* record volume; empty shelf reads as "logged nothing" | **High** — public-bucket read path + canon/Picks list object (mostly unbuilt) |
| **B — Two-lane editorial** *(FEAT-home-redesign)* | BNM hero (writer strip above, auth-gated) | `selectFeatured` (BNM→rating); genre by `album_count` | **Partial** — bucket lives only in the *private* writer strip; public bucket projection deferred (does not close bucket gap #1) | **Best** — decision #4 empty-state; genre bars render (`album_count`≠review count) *after the client fetch resolves — not in static HTML / not for crawlers* | **Medium** — module stack + personalization + writer-strip count source (OQ2) |
| **C — Latest-reviews feed** | Lead review + chronological feed | `date` desc (or single `bestNew`) | **Worst** — reviews only; bucket has no public presence or path to one; nearest the forbidden "just become IZM" | Graceful but **sparse** — only the empty card carries the page | **Lowest** — close to today's `/`, reframed |

---

## Recommended direction (with trade-offs — explicitly NOT a final decision)

**Recommended: ship Concept B (the FEAT-home-redesign two-lane home) as the structure, but bias it
toward Concept A by treating the bucket's *public* projection as the next move, not an afterthought.**
Concretely: build B now (it is the most buildable and the best-behaved at near-zero content), and
when content justifies it, add **one Concept-A surface** — a public 명반 canon / year-end Picks rail
that is *literally a curated bucket projected publicly* (`03-positioning.md` Option 2; the cleanest
reconciliation point, `03-positioning.md` "coexist" #3). That sequence — **B's frame → an A-style
public bucket surface layered in** — is the home-page expression of `03-positioning.md`'s
recommended "Letterboxd-foundation / IZM-surface" model and its 1→2→3 boundary sequencing.

**Why B as the frame.** It is the already-decided direction (so this is *confirm*, not reopen), it
has the only genuinely empty-state-safe design (decision #4 + the `album_count` genre module that
renders even at 0 reviews), and it keeps the home reading as a publication rather than a scoreboard
(IZM rule, `02-reference-teardown.md` BORROW #7). Pure Concept A is the better *premise* fit but has
the worst empty state **and** depends on an unbuilt public-bucket API — too much net-new work and
too harsh a launch at 0 posts. Pure Concept C is the cheapest and most honest but discards the
differentiator and flirts with the forbidden conclusion.

**Trade-offs of the recommendation (named honestly):**
- **It does not, on day one, close the bucket's public gap.** Shipping B alone leaves the bucket
  private (in the writer strip only); the "personal record made public" half of the premise waits
  for the A-style canon/Picks rail. If the owner weights the *bucket* premise over buildability,
  Concept A (with its public-bucket cost paid up front) is the more premise-faithful pick.
- **The strongest A-surface (a curated, blurbed, ordered Picks list) is unbuilt** — no editor-lists
  feature, no list-level bucket metadata (`FEAT-home-redesign.md` non-goals; `03-positioning.md`
  bucket-as-list OQ). A ≥4.0★ canon computed from review `rating` ships cheaply; a true curated Picks
  list is a later feature. So "layer in an A surface" starts as a computed canon, not a hand-curated
  list, until that feature exists.
- **The writer-strip bucket count is still an open input** (`FEAT-home-redesign.md` OQ2): reading
  the localStorage SWR cache is zero-cost but empty-until-`/profile`-opened and per-browser; a
  reliable count needs a light authed `GET /api/buckets`. This blocks only the (private) writer
  strip, not the public face.
- **Browse-by-genre is runtime-fetched, not static** (`genres.ts:61-65`) — so that one module is
  empty until the API responds and is invisible to crawlers. Acceptable (it mirrors `/genres`
  already), but it means the home is not 100% static-rendered.

**What would change the recommendation.** If the owner decides the public-bucket projection
(`03-positioning.md` Option 2/3) is the *point* and wants it now — not deferred — then lead with
Concept A and accept the empty-state and API cost. If the owner wants the smallest honest thing
shippable this week and is content to defer both the bucket projection and the module stack, Concept
C is the floor. The recommendation assumes the owner wants the decided B structure **plus** a
credible path to the bucket's public half — which is the middle, and the only option that serves
both pulls.

---

## Open questions

OQ: Confirm the FEAT-home-redesign two-lane home (Concept B) as the home structure, or adjust toward
the personal-record home (Concept A) / the lean latest-reviews feed (Concept C)? (This doc
recommends B-as-frame + an A-style public bucket surface layered later — confirm or override.)

OQ: Is the home expected to project the **bucket** publicly at all, or is it acceptable for the
bucket to stay private (writer-strip-only) on the home while the public half waits for a separate
canon/Picks surface? (Decides whether Concept A's record-shelf spine is in scope for `/` at all —
ties to `03-positioning.md` Option 1/2/3.)

OQ: For the home's curated/authority rail, ship a **computed ≥4.0★ canon from review `rating`**
(`content.config.ts:118`) now, and defer a **hand-curated, blurbed year-end Picks list** until the
editor-lists / bucket-as-list feature exists (`FEAT-home-redesign.md` non-goals;
`03-positioning.md` bucket-as-list OQ)? (Mirrors OQ-3 canon/Picks.)

OQ: Resolve the **writer-strip bucket count source** (`FEAT-home-redesign.md` OQ2): read the
localStorage SWR cache `lf_buckets` (zero-cost, empty-until-`/profile`-opened, per-browser) or a
light authed `GET /api/buckets` (`buckets.ts:139`) for a reliable count?

OQ: Is the **Best New Music hero** allowed to silently fall back to "latest 3" when no post sets
`bestNew` (`reviews.ts:42-43`; `content.config.ts:122`), or should the hero module **self-hide /
show the empty-state editorial card** until a real BNM exists, so the home never presents un-anointed
"latest" as if it were an editorial pick? (Empty-state tone for the marquee slot.)

OQ: Is the **runtime-fetched** Browse-by-genre module (client-side `GET /api/genres/tree`,
`genres.ts:61-65`) acceptable on the home as-is, or should `album_count` be fetched/snapshotted at
build so the home is fully static and crawlable? (Trade-off: build-time freshness vs static
rendering; same caveat as `/genres` today, `01-current-frontend.md` `/genres` row.)

OQ: On the home, does the per-album score stay **gated behind the article** (IZM rule — keeps the
home a publication, not a scoreboard; `02-reference-teardown.md` BORROW #7), which also constrains
how a Concept-A record-shelf can display ratings? (Mirrors the SHARED-CONTEXT score-placement OQ and
`03-positioning.md` score-gating OQ.)
