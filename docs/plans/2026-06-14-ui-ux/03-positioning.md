> **⚠️ HISTORICAL SNAPSHOT — 2026-06-14. SUPERSEDED. Read for IA/positioning rationale only, not as a current spec.**
> This is a frozen overnight UI/UX & IA planning snapshot. Since it was written: the home direction it recommends
> (two-lane WriterStrip + drag-reorder personalization) was **superseded by FEAT-home-redesign-v2** (Variant B
> "Refined Editorial", front #176, 2026-06-16, prod-live), which removed WriterStrip + drag/reorder. The public-bucket
> viewer shipped as **`/collection`** (singular; the `/collections` plural used here was a deferred proposal).
> `FEAT-home-redesign` is **done + archived** (`docs/archive/done/rfcs/FEAT-home-redesign.md`), not "draft".
> See `git log` + the FEAT-* RFCs for current state.

---

# 03 — Positioning: Reconciling Bucket ↔ Publication

**Scope.** A positioning doc that reconciles the project's two pulls — the **bucket** (담기: a
private, personal record the owner builds by putting albums into nested crates) and the
**publication** (a Pitchfork-style criticism magazine that reads as authoritative). It presents
**options + trade-offs**; it does **not** decide. Final picks are the owner's (the design-decision
OQs live in `OPEN_QUESTIONS.md`).

**Inputs.** Grounded in Task 1 (`01-current-frontend.md` — the bucket is real, rich, and 100%
owner-private) and Task 2 (`02-reference-teardown.md` — authority comes from *voice + curated
canon*, not crowd aggregation), the decided home direction (`docs/rfcs/FEAT-home-redesign.md`,
draft), and the owner's editorial method (`docs/editorial/review-critique-method.md`).

**Evidence rule.** Code claims cite `file_path:line`; reference claims cite the 02 teardown section
or a URL; anything unverifiable is marked *speculation*.

**Forbidden conclusion (held throughout).** "Just become Pitchfork." The bucket foundation must
stay load-bearing — the differentiator is that the owner's *own bucket* becomes the critical unit,
not a magazine bolted next to a collection (the Bandcamp two-surface anti-pattern,
`02-reference-teardown.md` Bandcamp §3).

---

## The tension, concretely

The two pulls are not abstract aesthetics; they collide at specific, locatable points in the
current product. Below, each row names *where* bucket-logic and magazine-logic actually conflict,
and *where* they already coexist without friction.

### Where they CONFLICT

1. **Visibility: the record is private; the magazine is public.**
   The bucket is the most developed surface in the app, but it lives entirely behind auth-guarded
   `/profile` and an authed `GET /api/buckets` (`01-current-frontend.md` "Bucket implementation —
   Public vs private boundary"; `src/lib/buckets.ts:6-7`). A magazine's whole job is to be read.
   So the single richest artifact the owner produces is, today, structurally invisible to the very
   audience the publication identity wants. This is the central conflict — everything else is
   downstream of it.

2. **Atomic unit: a bucket entry vs a finished essay.**
   The bucket's atomic act is cheap — drop an album into a crate, optionally rate it (rating chips
   read off the owner's posts only inside the single `is_done`/"평론 완료" bucket,
   `01-current-frontend.md` bucket capabilities; `BoardBucket.isDone` confirmed `buckets.ts:68`).
   The magazine's atomic act is expensive — a `~550-word`, evidence-bearing, single-voice essay
   (`02-reference-teardown.md` IZM §4; the owner's own method, `review-critique-method.md` §1 North
   Star, §3 intent→evidence→judgment). If the public unit must be a finished essay, the site stays
   empty for a long time. If the public unit is a bare rating, it drifts toward the leaderboard tone
   the editorial identity rejects. The unit you expose decides the tone.

3. **Organization logic: personal taxonomy vs editorial taxonomy.**
   Buckets are a *personal* nested tree — arbitrary, owner-meaningful crates ("여름밤", "재평가 대기",
   color-coded, nestable; `01-current-frontend.md` data model; `BoardBucket.children` is a real
   tree, `buckets.ts:84`). A magazine organizes by *legible public axes* — genre, year, Best New
   Music, a 명반 canon (`02-reference-teardown.md` IZM §2, Bandcamp §2). A private "재평가 대기" crate
   is meaningless to a reader; a "Best of 2025" list is meaningless as a private workflow stage. The
   same tree cannot serve both without a projection layer that decides which crates are *publishable
   as editorial surfaces* and which stay backstage workflow.

4. **Scale signaling: a sparse log reads as "empty"; a magazine implies volume.**
   Posts are reset to 0 (STAB-5; `01-current-frontend.md` "What the home surfaces today"). A
   personal log degrades gracefully at near-zero content (one rated album is a legitimate diary
   entry). A magazine front page at near-zero content reads as broken — a big BNM hero over nothing
   (`FEAT-home-redesign.md` decision #4). The magazine framing *raises* the empty-state cost that
   the bucket framing would shrug off.

5. **Authority source: the magazine references claim authority by crowd; this site can't.**
   Every aggregation-pole reference (RYM Bayesian weighting, AOTY dual User Score, Pitchfork's 2026
   Reader Score) manufactures authority from *many* logs (`02-reference-teardown.md` NOT-BORROW
   list). A single author has no crowd, so any imitation is fake scale — explicitly ruled out. The
   magazine *look* tempts you toward crowd-authority machinery the single-author *reality* forbids.

### Where they COEXIST (already, or cheaply)

1. **The rating scale is shared.** The bucket's decided unit (0.5–5★, 0.5 steps, stored 0–10 +
   `ratingScale`) is *identical* to the scale Letterboxd/RYM/IZM use as their public record unit
   (`02-reference-teardown.md` comparison table). The personal log and the magazine want the same
   number — no conflict, a free alignment.

2. **A single voice IS the authority mechanism.** The editorial method is built around one
   consistent palate — intent → evidence → judgment, observer stance by default, "could a wiki have
   written this?" as the kill-test (`review-critique-method.md` §3-4, §7). That is exactly the
   authority source Task 2 says a solo site must use *instead of* crowd weighting
   (`02-reference-teardown.md` BORROW: "supply authority through voice, not weighting"). The bucket
   being one person's record is not a weakness to hide — it's the precondition for the calibrated,
   one-palate authority the magazine references can't replicate.

3. **Curated lists are both a bucket and an editorial surface.** A "명반 (≥4.0★)" standing tab or a
   non-ranked "Best of 2025" Picks list (IZM/Music Y/Bandcamp all run these,
   `02-reference-teardown.md` BORROW) is *literally a curated bucket* projected publicly. The nested
   tree already models exactly this object. Here the two pulls are the *same* feature seen from two
   sides — the cleanest reconciliation point in the whole design.

4. **RSS plumbing already exists.** The site ships RSS (`01-current-frontend.md` `/rss.xml`). The
   Letterboxd "log → public record → RSS" pipeline (`02-reference-teardown.md` BORROW) is half-built;
   projecting bucket activity into it is plumbing on one person's logs, no crowd needed.

**Net.** The conflict is concentrated almost entirely in **#1 (visibility) and #2 (which unit goes
public)**; the organizational, scale, and authority tensions are downstream of those two. The
coexistence points show the reconciliation is *available* — the bucket's rating unit, single voice,
and curated-list object all already double as magazine primitives. The design problem is therefore
not "bucket vs magazine" as a fork; it is **where to draw the public/private line through the bucket
so its publishable parts become editorial output and its workflow parts stay backstage.**

---

## Models for "a personal journal that feels like a magazine"

Two reference models bracket the design space. Task 2's axis data places every site on a
**personal-log ↔ editorial-authority** spectrum; the question is which *foundation* is load-bearing
and which is the surface effect.

### Model A — Letterboxd-type (the log is the foundation; authority is emergent/curated)

- **Foundation = the log.** The atomic act is logging (rate + optional like + optional note); that
  single write simultaneously builds a private diary AND emits a public, syndicated record
  (`02-reference-teardown.md` Letterboxd §3). Prose is optional; the rating is the unit.
- **Authority is a *second-order* effect** layered on top: at Letterboxd/RYM it's crowd aggregation
  (Top-500 average, Bayesian charts) — which this site **cannot** reuse (no crowd). The transferable
  part is the *plumbing*: log → public record → RSS, and the **rate-without-prose** minimal unit
  (`02-reference-teardown.md` BORROW #1, #2).
- **Fit for this project:** the bucket already IS a log; this model keeps the bucket foundation
  load-bearing and lets the site populate at near-zero content (one author rates fast, writes
  slowly). **Risk:** with no crowd to aggregate, a pure log has *no* authority surface — it reads as
  a private spreadsheet made public, not a magazine. The "feels like a magazine" half is unmet
  unless you add a curation layer on top.

### Model B — Pitchfork-type (editorial voice is the foundation; the log is backstage)

- **Foundation = the editorial verdict.** The atomic act is a finished, bylined critical essay with
  one authoritative score; Best New Music is an editorial *anointing*
  (`02-reference-teardown.md` Pitchfork §3). There is **no user collection page** — the personal
  record exists only as an anonymized aggregate *under* the critic's number (the 2026 Reader Score).
- **The log is hidden or absent.** The editorial pole's answer to "personal records" is to collapse
  them into one subordinate stat, never a per-person showcase
  (`02-reference-teardown.md` Pitchfork §3 lesson). IZM/Music Y/Bandcamp Daily go further — no
  personal layer at all, authority entirely from editor-curated canon + year-end Picks
  (`02-reference-teardown.md` IZM §3, Bandcamp §3).
- **Fit for this project:** delivers the magazine authority immediately and matches the editorial
  method (`review-critique-method.md`). **Risk:** it discards the bucket foundation — the project's
  one differentiator. Taken straight, this *is* the forbidden "just become Pitchfork." And it has the
  worst near-zero-content failure mode: a magazine with no essays is just empty.

### Proposed model for THIS project (recommended option, not a verdict)

**A bucket-founded log with a thin, owner-curated editorial projection on top — "Letterboxd
foundation, IZM surface."** Concretely:

- **Foundation stays the bucket/log (Model A).** The owner keeps doing what the app already supports
  best: bucket albums, rate them, optionally research and write. The atomic public unit is the
  **rated bucket entry** (0.5–5★ + tags + optional note), with prose *layered later* — matching
  Task 2's BORROW #2 and the owner's method, where "score is last, a by-product"
  (`review-critique-method.md` §4). This is what lets the site exist at near-zero published prose.
- **Authority comes from voice + curation, not crowd (Model B's *surface*, not its foundation).**
  Two cheap, single-author authority surfaces — both of which are *just curated buckets projected
  publicly*: a **명반-style standing canon** (≥4.0★) and a **non-ranked year-end Picks** list,
  exactly the IZM/Music Y pattern (`02-reference-teardown.md` BORROW #3, #5). These read as
  editorial because they're *selections with a stated stance*, not leaderboards.
- **The score stays gated behind the article on the home (IZM rule),** so the front page reads as a
  publication, not a scoreboard (`02-reference-teardown.md` BORROW #7). Whether the score *also*
  becomes a sortable `/reviews` facet is an open question (OQ below; the home tone is the thing to
  protect).
- **The single voice is the authority engine.** The "could a wiki have written this?" kill-test
  (`review-critique-method.md` §7) is what makes one person's bucket read as criticism rather than a
  catalog. The bucket's one-person-ness is reframed from a scale weakness into the *calibration*
  selling point (Letterboxd's deliberately un-standardized half-star, applied to one palate —
  `02-reference-teardown.md` BORROW #4).

**Why this is the recommended option.** It is the only model that keeps the bucket load-bearing
(satisfying the project premise and the forbidden-conclusion constraint), supplies magazine authority
through mechanisms a single author can actually sustain (voice + curated canon, not crowd), and
degrades gracefully at near-zero content (a log tolerates sparsity; the curation surfaces sit inert
until ≥1 review exists). It also aligns with the already-decided `FEAT-home-redesign` direction (an
editorial home over honest data + an auth-gated writer lane) rather than reopening it.

**Trade-offs / what it costs.**
- It requires building the **public projection layer** that does not exist today — the bucket API is
  owner-only (`01-current-frontend.md` bucket boundary; `buckets.ts:6-7`). This is net-new work
  (sized in the next section).
- It risks a **muddled middle**: a log that's too sparse to feel like a magazine and a magazine
  surface too thin to feel authoritative. Mitigation = foreground the writer lane and the
  empty-state until content accumulates (`FEAT-home-redesign.md` decision #4), and treat the canon /
  year-end surfaces as inert-until-earned rather than seeded with filler.
- It demands **editorial discipline about which buckets are public** — without a clear
  publish/backstage boundary, the personal taxonomy leaks into the public IA (conflict #3).

**The alternatives remain valid for the owner to pick.** Pure Model A (log-first, minimal curation)
is the fastest to ship and the most honest at near-zero content, but barely "feels like a magazine."
Pure Model B (essays + canon only, bucket stays 100% private) is the most immediately authoritative
and lowest-build (no projection layer), but abandons the differentiator and has the harshest empty
state. The recommendation is the middle path *because* the bucket is already real and rich — throwing
it away (B) wastes the most developed surface in the app, and shipping it raw (A) wastes the
editorial method the owner has already written down.

---

## Designing the bucket concept itself

### What goes IN a bucket

- **Albums — confirmed.** The decided rated unit is the album (0.5–5★); track ratings were rolled
  back (2026-05-28) and artist ratings rejected (memory roadmap; `02-reference-teardown.md` notes
  the scale match). The bucket's `BoardAlbum` is album-keyed (`buckets.ts:22`). So the *rated*
  thing in a bucket is always an album, never a track or artist.
- **Open: non-album bucket members (themes / lists).** A bucket today holds albums and child
  buckets (`BoardBucket.albums` + `.children`, `buckets.ts:83-84`). Should a bucket also be allowed
  to *be* a themed list (e.g. "Shoegaze entry points", "2025 picks") — i.e. is a bucket a
  **container of albums** or also a **publishable themed list object**? The nested tree already
  supports the structure; the question is whether a bucket carries list-level editorial metadata (a
  blurb, an ordering intent, a "this is public" flag) that turns it into the IZM-style Picks unit.
  This is the hinge between "bucket as private workflow" and "bucket as editorial surface." (OQ
  below.) Tracks/artists stay out as *rated* units, but a bucket-as-list could still *reference*
  artists/genres as a theme — that's organization, not a new rated unit.

### How buckets are categorized & displayed (reuse the real nested tree)

- **Reuse what exists.** The board is a real nested tree with drag-to-reorder / nest / unnest, per-
  bucket accent color, the single `is_done`/"평론 완료" column that drives rating chips, per-bucket
  client-side view controls (sort newest/oldest/popular, group by artist/genre, genre-filter chips),
  and a special `spotify_library` mirror bucket (`01-current-frontend.md` bucket capabilities;
  `BoardBucket` fields `buckets.ts:65-85`). Any public projection should *render from this same tree*,
  not invent a parallel model.
- **Two bucket roles already implicit in the data.** The `kind` field already distinguishes a normal
  `'review'` crate from the `'spotify_library'` mirror (`buckets.ts:74-77`), and `isDone` already
  flags the "평론 완료" crate (`buckets.ts:68`). These existing flags are the natural seam for a
  public/private distinction — a public projection can key off "which buckets are marked
  publishable" the same way the board already keys rating chips off `isDone`.
- **Display options for a public bucket:** (a) as a **share-bar / list grid** mirroring the `/genres`
  Outliner pattern already shipped (`01-current-frontend.md` `/genres`); (b) as an **IZM Picks-style
  card grid** (cover + artist + title + optional blurb); (c) as a **Letterboxd-list-style ordered
  list with per-entry notes**. All three render cleanly from the existing tree; the choice is tone
  (magazine grid vs personal list).

### Where the public ↔ private boundary should sit — the key question

This is the crux (it is conflict #1 above, and the central design problem named in SHARED CONTEXT).
Three boundary options, each with trade-offs and a build-cost estimate *relative to Task 1's current
owner-only API* (`GET /api/buckets` + mutations are all Bearer-gated, `buckets.ts:6-7`; no public
read path exists).

**Option 1 — Fully private (status quo). Buckets stay 100% backstage; only finished reviews +
editorial canon/Picks pages are public.**
- *Public unit:* the published review (existing `/blog/[slug]`) and owner-curated canon/year-end
  pages built from *reviews*, not raw buckets.
- *Trade-off:* simplest, most honest at near-zero content, zero leak risk; but the "organize into a
  personalized record" half of the premise stays invisible (`01-current-frontend.md` bucket gap #1)
  — this is essentially Model B and flirts with the forbidden conclusion.
- *Build cost vs Task 1:* **lowest** — no public bucket API at all; canon/Picks pages read the
  existing public `blog` collection. The projection is "reviews → curated page," not "bucket →
  public."

**Option 2 — Selected buckets public as curated lists.** The owner marks specific buckets (or a
specific `kind`) as public; those render as reader-facing IZM-style lists / 명반 canon, while all
other buckets and the raw board stay private.
- *Public unit:* a *bucket-as-curated-list* (a themed collection with a stance), not the raw board.
- *Trade-off:* directly projects the bucket foundation into editorial output (the recommended
  model's authority surfaces are exactly this), reuses the real tree, and keeps workflow crates
  ("재평가 대기") backstage. Risk: requires an explicit publish boundary + editorial discipline, and a
  half-empty public list reads as thin at near-zero content (mitigate: inert-until-earned).
- *Build cost vs Task 1:* **medium** — needs (a) a `public`/visibility flag on the bucket model
  (the existing `kind`/`isDone` pattern shows the precedent), (b) a **public, unauthed read endpoint**
  for public buckets only (today every bucket read is Bearer-gated — this is the real new surface
  area, and it must fail closed: only flagged buckets, never the tree), and (c) a reader-facing
  render (reuse `/genres` or ReviewsIndex card patterns). Backend route + contract change.

**Option 3 — Per-entry public rating record.** Every rated bucket entry (0.5–5★ + tags + optional
note) is itself a first-class *public* record — a Letterboxd-style diary projected to a public
"ratings / recently rated" surface, with the full essay layered on later when written.
- *Public unit:* the **rated-but-unwritten entry** as the atomic public artifact (Task 2 BORROW #2;
  the SHARED-CONTEXT bucket-unit OQ).
- *Trade-off:* maximal "log feels public" (the Model-A pipeline), populates the site fastest, and
  makes the rating-decoupled-from-prose unit load-bearing. Risk: pushes hardest toward leaderboard /
  scoreboard tone (a public stream of bare scores), the exact thing the IZM "score gated behind the
  article" borrow guards against (`02-reference-teardown.md` BORROW #7) — needs careful framing to
  stay editorial, not a ratings ticker.
- *Build cost vs Task 1:* **highest** — the current schema is built for *owner-private* items; a
  rated-but-unwritten entry as a first-class **public** record needs a public read path *and* a
  per-entry public/private distinction *and* a new reader surface, plus a decision on whether an
  entry is public the moment it's rated or only when the owner promotes it. **Open whether the bucket
  schema even supports a public rated-but-unwritten entry today** — Task 1 shows items are
  owner-private with no public-visibility concept (`01-current-frontend.md` bucket boundary). This is
  the SHARED-CONTEXT OQ and likely a shared_db column-add (per the cross-repo rollout order).

**Reading across the three.** They are a spectrum, not mutually exclusive: Option 1 is the floor
(ship today), Option 2 is the recommended-model's authority surface (public *curated* buckets), and
Option 3 is the most ambitious log-as-public-record. A plausible sequencing is **1 → 2 → 3**:
ship canon/Picks from reviews now (no new API), add selected-public-bucket lists when content
justifies them, and only consider per-entry public records once the owner wants the full
log-is-public model and is willing to pay the schema + tone cost. The recommendation does **not**
decide this — it flags Option 2 as the cleanest fit for the recommended "Letterboxd-foundation /
IZM-surface" model, with Option 1 as the honest near-zero-content starting point.

### Boundary projection rule (the hard part — never leak the tree)

Whichever option is chosen, the public line must be drawn against two **verified** Task 1 facts:
every bucket read is Bearer-gated, and the *same* `GET /api/buckets` returns the full **nested tree
with descendants inlined** (`01-current-frontend.md` "Public vs private boundary"; `buckets.ts:139`).
So a public projection that keys off a per-bucket `public` flag must **publish only that bucket's own
albums — never auto-publish its children, parent, or siblings.** A public child of a private parent
ships without parent context; a private child of a public parent stays hidden. Concretely:

- The public endpoint returns a **flattened, per-bucket view** (one flagged bucket → its own albums),
  **not the tree** — the recursion that inlines `children` is exactly what must not cross the boundary.
- The public DTO is a **narrowed projection** of `BoardAlbum`: `title / artist / cover / year /
  rating-if-reviewed` only — **never** the owner-workflow fields (`researchSelected`, `researchStatus`,
  `alreadyReviewed`) or client-only state (trash, per-bucket views). Reuse the *model*, not the *shape*.
- Default-closed: absent an explicit `public` flag, a bucket and every entry in it is private.

This is what "fail closed" means here, and it — not the choice of which buckets to show — is the real
new surface area Options 2 and 3 must build on top of the current owner-only API.

---

## Open positioning questions

OQ: Which model is the target — pure log-first (Model A), pure editorial-canon (Model B), or the
recommended "Letterboxd-foundation / IZM-surface" middle (bucket-founded log + thin owner-curated
editorial projection)?

OQ: Where should the public/private boundary sit — Option 1 (buckets fully private, only
reviews+canon public), Option 2 (selected buckets public as curated lists), or Option 3 (per-entry
public rating record)? And should it be sequenced 1 → 2 → 3 rather than chosen once?

OQ: Is a bucket a *container of albums* only, or also a publishable *themed-list object* (carrying a
blurb / ordering intent / public flag) that becomes the IZM-style Picks unit? (This decides whether
"themes / lists" go in a bucket.)

OQ: Does the current bucket schema support a **rated-but-unwritten entry as a first-class PUBLIC
record**, or does Option 3 require a shared_db visibility column-add? (SHARED-CONTEXT bucket-unit OQ;
today every bucket read is Bearer-gated — `buckets.ts:6-7`.)

OQ: On the home/public surfaces, does the per-album score stay **gated behind the article** (IZM
rule, protects editorial tone), or also become a **sortable facet on `/reviews`** (risks leaderboard
tone)? (Mirrors OQ-2.1.)

OQ: Build the **명반 (≥4.0★) standing canon** + **non-ranked year-end Picks** surfaces now (inert
until content), or defer as premature at near-zero published reviews? (Mirrors OQ-2.2.)

OQ: Ship a short **"how I rate"** page that makes the single-author subjective-scale stance explicit
(turning "no universal scale" into the selling point), as the framing that keeps a public rating
record from reading as a leaderboard? (Mirrors OQ-2.3.)

OQ: Is the **Letterboxd-style log → RSS** projection of bucket activity in scope (reuse existing
`/rss.xml` plumbing), or does syndicating bucket entries pre-suppose the Option-3 public-entry
decision?

OQ: When a public bucket / curated list is near-empty, is the accepted posture **inert-until-earned**
(hide / "coming soon"), consistent with `FEAT-home-redesign` empty-state-first, rather than seeding
filler?
