# FEAT-genre-subgenres: tier-1 editorial sub-genres — tagging, definitions, related-review recommendation

- **Status**: accepted (2026-06-15, owner) — Step 1 in progress
- **Owner**: 박지훈
- **Created**: 2026-06-15
- **Supersedes**: the tier-1 carve-out from FEAT-genre-system (`docs/archive/done/rfcs/FEAT-genre-system.md`) — that RFC shipped tier-0 (12 machine genres + Outliner) and deferred ego-view relationships + sub-genre vocabulary here.

## Goal

A **tier-1 editorial sub-genre layer**. Its purpose is **NOT** a browse/search taxonomy. It links a *review* to precise sub-genres in order to:

1. **Critical authority** — tag each review with the exact sub-genre(s) it concerns. A precise vocabulary is the structured form of the criticism's expertise (Pitchfork browses only ~9 genres but names hundreds of micro-genres *in prose*; this layer is that article-level precision made structured).
2. **Definitions** — every used sub-genre carries an owner-authored definition (`definition_md`), surfaced on review/genre pages so the site reads as a reference.
3. **The edge-graph substrate for related-review recommendation** — the seeded `genre_edges` graph (influenced-by / related) is the data that a recommendation engine will later consume. **The recommendation *experience* itself is split to a follow-on feature** (see Scope below).

Sub-genres are encountered **on review pages**, not browsed to. This single fact reframes the whole design (see Non-goals + the vocabulary decision).

**Scope (rescoped 2026-06-15, owner).** This RFC delivers the sub-genre **tagging + definitions + taxonomy-visualization** layer: the vocabulary + edge-graph data (Step 1/1b ✅), the writer's tagging input (Step 2), the review-page display (Step 3), and the **`/genres` ego-view visualization** (Step 4 — visualizes the live 211-genre taxonomy + 40 edges, **review-volume-independent**). Only the **related-review recommendation** (old Step 5) + **owner edge-authoring** (old Step 6) are split out to **`docs/rfcs/FEAT-genre-recommendation.md`** — deferred, gated on real review volume (nothing to recommend until reviews accrue).

## Non-goals

- **Sub-genre browse/search navigation.** Nobody navigates a sub-genre tree to land on a node. This is why empty nodes are not a problem and why the palette can be rich.
- **Machine labeling of sub-genres.** tier-1 is human/editorial, attached at *review* time, stored per-post. tier-0 (`album_genres`) stays machine-labeled; the two stores never mix and humans never edit `album_genres`.
- **Sub-sub-genres.** The model is **2-tier flat** — every sub-genre attaches directly to one of the 12 tier-0 parents.
- **Multi-parent containment.** Cross-genre membership is expressed as *influence/related edges*, not multiple parents (see Decisions).
- **Related-review recommendation + owner edge-authoring UI** — split to `FEAT-genre-recommendation` (deferred, gated on review volume). This RFC produces the recommendation's data (edge graph + per-review tags) and the genre-map *view* (Step 4), but not the recommendation block itself.

## Current state

- **tier-0 shipped + live** (FEAT-genre-system): `genres(id, slug, label, parent_id, definition_md, position, created_at)` with 12 `parent_id IS NULL` parents (K-Pop, Pop, Latin, Hip-Hop, R&B-Soul, Rock, Electronic, Jazz, Classical, Folk-Country, Soundtrack, World-Other). `GET /api/genres/tree`, `POST`/`PUT /api/genres` (Cognito JWT). `/genres` renders the Outliner (album-share meter + owner inline definition edit). `genres.parent_id` (shared_db V17) already supports a 2-tier tree → tier-1 attaches with **no migration to the genres table**.
- **Design**: the Claude Design "장르 맵" handoff carried 4 layouts; only the **Outliner (Layout A)** was productionized. The **ego-view / Miller-columns / network-diagram** layouts were deferred because they only make sense once sub-genres + relationships exist (a tier-0 containment tree has zero edges). This RFC builds them.
- **Reviews are `posts` rows** (`posts.id` UUID PK + `posts.slug` UNIQUE; the build-time `blog` MDX collection is synced from them). Every post-linked table keys by `post_id UUID REFERENCES posts(id) ON DELETE CASCADE` (post_albums, post_artists, post_tags, post_metrics, …). `musicReview.genres[]` in frontmatter is the *machine* `album_genres` copy — there is no editorial review↔sub-genre link yet. *(Corrected at Step-1 audit — the earlier draft wrongly assumed the blog collection had no DB row.)*
- Catalog signal: ~397 distinct raw artist-genre strings already encode real sub-genres (한국 랩 369, K-발라드 134, 클래식 피아노 100, 바로크 80, 하이퍼팝 39, …). The catalog is K-pop / hip-hop / pop heavy; jazz / classical / latin / rock / electronic are thin.

## Target state

### Data model

- **Containment = single `genres.parent_id`.** The global tree stays a clean, readable single-parent containment tree (matches the FEAT-genre-system "global = readable Outliner" decision). Multi-parent is **available as a fallback edge type but unused in v1** — every sub-genre has exactly one parent.
- **New `genre_edges`** — the relationship layer (the ego-view source AND the recommendation engine):
  ```
  genre_edges(
    from_genre_id  UUID NOT NULL REFERENCES genres(id) ON DELETE RESTRICT,
    to_genre_id    UUID NOT NULL REFERENCES genres(id) ON DELETE RESTRICT,
    type           TEXT NOT NULL CHECK (type IN ('parent','influenced_by','related')),
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (from_genre_id, to_genre_id, type)
  )
  ```
  - `influenced_by` — directed, no timeline (e.g. City Pop ← Funk/AOR/Disco; Jazz Rap ← Jazz).
  - `related` — lateral, undirected (see-also; absorbs regional variants).
  - `parent` — the multi-parent fallback; **0 rows in v1** (cross-genre membership uses `influenced_by`/`related` instead).
  - **ON DELETE RESTRICT** on both genre FKs — matches V17's "all genre_id FKs RESTRICT" rule (vocabulary rows are never deleted out from under attachments). *(Corrected from the draft's CASCADE at Step-1 audit.)*
- **New `post_genres`** — the editorial review↔sub-genre link, per-post, separate from `album_genres`. Mirrors `post_tags` exactly:
  ```
  post_genres(
    post_id    UUID NOT NULL REFERENCES posts(id)  ON DELETE CASCADE,
    genre_id   UUID NOT NULL REFERENCES genres(id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (post_id, genre_id)
  )
  ```
  Keyed by `post_id` (FK to `posts.id`) — the established post-children convention; survives slug renames. *(OQ1 resolved at Step-1 audit: reviews ARE `posts` rows.)*

### Vocabulary — a rich seeded palette, organically displayed

- **Palette = 211 sub-genres** (Appendix A; seeded by V20), built up front from credible, real-site-sourced taxonomies (RYM / Wikipedia / AllMusic / Discogs / Pitchfork). This is the **writer's pick-list**, optimized for *tagging precision*, not browse leanness.
- **Display = populated-only.** `/genres` renders a sub-node only when it has ≥1 `post_genres` row (or ≥1 album under it). The tree grows organically and is **never empty** — no dead-end clicks — even though the palette is large. (This resolves the seed-vs-organic fork: seed the palette, display organically.)
- **Definitions on-demand.** `definition_md` is authored when a sub-genre is first used; unused palette entries carry no definition and no display node. Owner burden scales with reviews, not with palette size.

### Cross-genre links → influence/related edges (not multi-parent)

Every sub-genre that musically spans two tier-0 parents is filed under one **primary parent** with an `influenced_by`/`related` edge to the other — e.g. Jazz Rap: `parent = Hip-Hop`, `influenced_by → Jazz`. Appendix A marks these with `→`.

### Rendering (both designs)

- **Global = Outliner** (single-parent, populated nodes; current `/genres`, extended to sub-nodes).
- **Per-node ego-view** — clicking a node opens a small **local** diagram: that node + its immediate neighbors (parent, children, `influenced_by`, `related`). Explicitly **reject** the global dense edge-wall + chronology axis (kills readability — owner's #1 priority); borrow musicmap's *local neighborhood* feel only.
- Miller-columns layout optional (low priority).

### Recommendation engine

"Related reviews" on a review page = reviews sharing a `post_genres` sub-genre **+** reviews tagged with sub-genres one edge away (`influenced_by`/`related`) in `genre_edges`. Ranking: shared-sub-genre first, then edge-distance.

### Parent-specific decisions

- **Classical** — **both** an era axis (Medieval … Contemporary) and a form axis (Opera, Piano, Chamber, …) as parallel flat tier-1 leaves. A Baroque concerto carries two classical tags (Baroque + Concerto); both axes are large catalog signals, so neither can be dropped.
- **Soundtrack** — a **format axis**, documented as such: its children (Film Score, VGM, Anime OST, …) are media/formats, not sonic genres. A soundtrack review also carries its sonic sub-genre tag.
- **Metal** — under **Rock** (Heavy / Black / Death / Doom / Thrash / Metalcore + the deeper Deathcore/Djent). No separate Metal tier-0; promote later if metal coverage grows.
- **K-Pop** — **simplified, sound-based**: K-Pop (idol pop) + K-Ballad (+ 4th-Gen/Noise). The agency-vs-independent boundary is **dropped** — Korean rap / R&B / rock are filed by *sound* under Hip-Hop / R&B-Soul / Rock (한국 랩 369 already lives under Hip-Hop), not duplicated as idol-variants under K-Pop.
- **Reggae family** — under **World-Other** for now (musically a self-contained Jamaican lineage; revisit a standalone tier-0 if it grows).

## Trim methodology (major-site-grounded)

A 6-agent benchmark (Pitchfork / RYM / AllMusic / Discogs / Apple / Spotify) established: editorial peers cap browse at **1–2 tiers** (Pitchfork 9 nodes/1-tier; AllMusic 21+~1,400 styles/2-tier; Discogs 15+540, deliberate cap); only RYM (6–7 tiers) and Spotify (6,291 algorithmic) go deep, both on labor/data engines this site lacks. **But because this layer is for tagging/authority/recommendation — not browse — leanness is not the objective; tagging precision is.** So the trim is minimal:

- **Cut (~12, hurt tagging precision):** duplicates (Bolero ⊂ Mariachi, Snap ⊂ Crunk, Turreo ⊂ RKT, Smooth Soul ⊂ Quiet Storm, Country Folk = Folk+Country edge, Sonata ⊂ Classical Piano, Oratorio ⊂ Choral), format/non-genre (Library Music, TV Soundtrack → belong in a format facet), made-up umbrella (J-Traditional → use Gagaku/Min'yō), marketing catch-alls (Tropical = AllMusic-self-described "catch-all", Europop = geographic marketing umbrella).
- **Keep niche-but-real** (Gypsy Jazz, Horrorcore, Forró, Fado, Klezmer, Crunk, Bubblegum, …): legitimate precise tags; empty-browse cost is zero under populated-only display.
- **1 correction:** Lo-Fi Hip-Hop was mis-flagged as trim — it is a genuine major-site browse pillar (Spotify lofi ecosystem, ongoing releases) → kept. **2 placement fixes:** UK Garage belongs under Electronic (not R&B); Glitch only as the proper AllMusic style (drop the "EDM micro-hybrid" framing).

## Steps

> Cross-repo: shared_db (schema + seed) → backend (API) → workspace contract → front. Each step prod-observed before the next (CLAUDE.md rule #4).

### Step 1 — schema + seed (shared_db) ✅ + backend tree/edges API (Step 1b, pending)
**Schema + seed DONE + prod-applied 2026-06-15** (shared_db V20): `genre_edges` + `post_genres` created, 211 tier-1 genres + 40 edges (33 influenced_by / 7 related) seeded; verified on prod (tier1=211, tier0=12, post_genres=0). Backend API + ORM models = **Step 1b (pending)**.

Original plan: `genre_edges` + `post_genres` tables (plain `V{N}__*.sql`, no Alembic). Seed the palette as tier-1 `genres` rows (`parent_id` = the tier-0 parent; `position`; `definition_md` NULL until authored) + the `influenced_by`/`related` edges from Appendix A. Dry-run → owner reviews the seed → execute against prod (REQUIRED before merge per `reference-shared-db-cross-repo-rollout`). Backend: `GET /api/genres/tree` returns tier-1 nodes + edges; `POST /api/genres/{id}/edges` + `POST /api/posts/{slug}/genres` (Cognito JWT, copy `buckets_post` pattern). Contract: `openapi.json` regen + workspace merge.

### Step 2 — writer picker (front `/write`)
Sub-genre multi-select in the `/write` SettingsPanel (below section / review-tag pickers), drawing from the palette (searchable — large palette, so filter-as-you-type). Persists `post_genres` on publish/restore via `content_sync`.

### Step 3 — review-page tags + definitions (front)
Render a review's `post_genres` as labeled tags on `/review/{slug}`; each tag links to its definition (popover or `/genres#slug`). Owner sees an inline "define" affordance for an as-yet-undefined used sub-genre.

### Step 4 — `/genres` ego-view + taxonomy visualization (front)
Extend `/genres` to render the **tier-1 taxonomy + relationships** from the live `GET /api/genres/tree` (211 genres + 40 edges): the Outliner shows sub-nodes, and clicking any node opens a small **local ego-diagram** (that node + its parent/children + `influenced_by`/`related` neighbours). Reuses the deferred "장르 맵" Claude Design layouts (ego-view / Miller-columns / diagram — see `GenreMap.tsx`). **Read-only** (edge authoring is split out). Review-volume-independent — it visualizes the taxonomy itself, so it's buildable now. Open Q: show the full palette vs populated-only in the local diagram (the global tree may stay populated-only for readability). FEAT-genre-subgenres is **done at Step 4**.

> **Steps 5–6 split out (rescoped 2026-06-15).** The related-review recommendation (old Step 5 — the "장르 기준 추천 평론") and owner edge-authoring (old Step 6) move to **`docs/rfcs/FEAT-genre-recommendation.md`**, deferred: gated on real review volume (the recommendation has nothing to rank until reviews are tagged). The ego-view viz (Step 4) was **kept here** — it's review-volume-independent.

## Open questions

1. ~~**`post_genres` key** — slug vs a synthesized post id.~~ **RESOLVED (Step-1 audit):** reviews are `posts` rows; key by `post_id` FK to `posts.id` (the established post-children convention).
2. **Recommendation ranking** — shared-sub-genre weight vs edge-distance vs recency; needs ≥10–20 reviews to tune (precondition: real review volume, like FEAT-ai-editorial-critique).
3. **Ultra-granular palette entries** — House sub-forms (Deep/Tech/Prog/Electro/Future), Djent, Drumstep are 3rd-level flattened to tier-1; keep for precision or collapse to their canonical parent? Owner call at authoring time.
4. **Edge type at authoring** — is the influenced_by/related distinction worth the owner's effort per edge, or default everything to `related` and promote selectively?
5. **Build cost** — ~220 seed rows is fine; the edge seed (Appendix A `→` links) is the larger authoring surface — seed the obvious ones, grow the rest organically.

## Decisions log

| Date | Decision | By |
|---|---|---|
| 2026-06-12 | Owner wants a dedicated brainstorm before any RFC; sub-genres = editorial per-post layer (`post_genres`), writer picker in `/write` | owner |
| 2026-06-13 | Rendering = per-node ego-view, not a global graph; reject dense edge-wall + time axis; exactly 3 relationship types (parent / influenced-by / related) | owner |
| 2026-06-15 | **Goal reframed**: NOT browse/search — it's review↔sub-genre linkage for authority + definitions + related-review recommendation. Empty-node concern dissolves; precision > leanness | owner |
| 2026-06-15 | Multi-parent → **single `parent_id` + influence/related edges**; multi-parent kept as fallback, 0 rows in v1 | owner |
| 2026-06-15 | Classical = era + form both (flat); Soundtrack = format axis (explicit); Metal under Rock; K-Pop simplified sound-based (no agency axis); Reggae under World-Other | owner |
| 2026-06-15 | Vocabulary = seeded rich palette (~220) + populated-only display + on-demand definitions; trim only ~12 dupes/format/junk-marketing; Lo-Fi Hip-Hop kept; UK Garage→Electronic, Glitch→proper style | owner |
| 2026-06-15 | Trim methodology grounded in a major-site benchmark (Pitchfork/RYM/AllMusic/Discogs/Apple/Spotify) | — |
| 2026-06-15 | **Accepted** → Step 1. Step-1 audit corrections: `post_genres` keys by `post_id` FK (reviews ARE `posts` rows — OQ1 resolved); `genre_edges` ON DELETE RESTRICT (not CASCADE) per the all-genre_id-FKs-RESTRICT rule. Migration = V20 | owner |
| 2026-06-15 | **Step 1 schema+seed DONE + prod-applied** (V20). Owner Step-1 trims: dropped generic "Soundtrack" node, folded House sub-forms, dropped Djent/Drumstep, K-Pop = idol-pop + ballad → palette 220→211; 7 lateral edges set to `related` (33 influenced_by / 7 related). Backend API = Step 1b | owner |
| 2026-06-15 | **Step 1b DONE + prod-live** (shared_db #35→v0.20.0 / backend #73 / ws #364 / front #162): ORM models, `GET /tree` edges, editorial tagging via post create/update payload `genre_ids`→`post_genres`. `/api/genres/tree` = 12+211+40 live | owner |
| 2026-06-15 | **Rescoped: Steps 5–6 split out** to `FEAT-genre-recommendation` (deferred — gated on review volume): related-review recommendation + owner edge-authoring. **Step 4 (ego-view taxonomy viz) kept here** (revived — it visualizes the live taxonomy, review-volume-independent). FEAT-genre-subgenres = tagging + definitions + genre-map viz, **done at Step 4** | owner |

---

## Appendix A — the seed palette (211, by parent)

Notation: `✓N` = already present in the catalog (artist-count); `→X` = `influenced_by`/`related` edge to tier-0 parent X (filed under the **primary** parent listed). Cuts applied (Bolero, Snap, Turreo, Smooth Soul, Country Folk, Sonata, Oratorio, Library Music, TV Soundtrack, J-Traditional, Tropical, Europop). Owner Step-1 trims (2026-06-15): dropped the generic "Soundtrack" sub-node, folded the House sub-forms into House, dropped Djent + Drumstep, K-Pop kept to idol-pop + ballad.

**K-Pop** (2) — K-Pop (Idol) ✓81 · K-Ballad ✓134

**Pop** (19) — J-Pop ✓26 · Hyperpop ✓39 →Electronic · City Pop ✓9 · Bedroom Pop ✓7 →Rock · P-Pop ✓10 · OPM ✓12 →World-Other · Synth-Pop →Electronic · Dance-Pop →Electronic · Electropop →Electronic · Art Pop · Indie Pop →Rock · Baroque Pop · Chamber Pop · Mandopop/C-Pop · Cantopop · Sophisti-Pop · Sunshine Pop · Teen Pop · Bubblegum

**Hip-Hop** (28) — Korean Hip-Hop ✓369 · Southern ✓14 · Japanese ✓14 · Cloud Rap ✓11 · Jazz Rap ✓11 →Jazz · Melodic Rap ✓9 · Grime ✓16 →Electronic · Experimental ✓8 · East Coast ✓7 · Phonk ✓6 · Lo-Fi Hip-Hop →Electronic · Trap · Boom Bap · Drill · Conscious · G-Funk →R&B-Soul · Gangsta · West Coast · Hardcore · Emo Rap · Pop Rap →Pop · Abstract · UK Hip-Hop · French Hip-Hop · Crunk · Horrorcore · Hyphy · Bounce

**R&B-Soul** (12) — Alternative R&B ✓15 · Neo-Soul ✓7 · Japanese R&B ✓6 · Contemporary R&B · Soul · Funk →Pop · New Jack Swing →Hip-Hop · Quiet Storm · Progressive Soul · Korean R&B · Trap Soul →Hip-Hop · Psychedelic Soul →Rock

**Rock** (32) — Korean Rock ✓53 · Alternative Rock · Indie Rock · Punk · Post-Punk · Hardcore Punk · Grunge · Shoegaze · Post-Rock · Math Rock · Progressive Rock · Psychedelic Rock · Garage Rock · Art Rock · Noise Rock · Emo · Pop Punk · Classic Rock · Hard Rock · Surf Rock · Krautrock · Folk Rock →Folk-Country · Dream Pop →Pop · Jangle Pop →Pop · Power Pop →Pop · Heavy Metal · Black Metal · Death Metal · Doom Metal · Thrash Metal · Metalcore · Deathcore

**Electronic** (21) — EDM ✓11 · IDM ✓7 · Big Room ✓7 · Electroclash ✓7 · EDM Trap ✓6 →Hip-Hop · House · Techno · Trance · Drum & Bass · Dubstep · Ambient · Downtempo · Trip-Hop →Hip-Hop · Synthwave · Vaporwave · Electro · Future Bass · UK Garage · Breakbeat · Hardstyle · Glitch

**Jazz** (23) — Bebop · Swing · Hard Bop · Cool Jazz · Modal Jazz · Free Jazz · Jazz Fusion →Rock · Spiritual Jazz · Vocal Jazz · Big Band · Soul Jazz →R&B-Soul · Jazz-Funk · Smooth Jazz · Latin Jazz →Latin · Afro-Cuban Jazz →Latin · Post-Bop · Nu Jazz →Electronic · Dixieland/Trad · Acid Jazz →Electronic · Gypsy Jazz · Third Stream →Classical · Avant-Garde Jazz · Kansas City Jazz

**Classical** (19) — *era*: Medieval ✓11 · Renaissance ✓38 · Baroque ✓80 · Classical period · Romantic · Impressionism ✓44 · Expressionism ✓11 · Neoclassicism ✓13 · Contemporary Classical ✓17 · Minimalism — *form*: Opera ✓101 · Classical Piano ✓100 · Chamber ✓42 · Orchestral ✓39 · Choral ✓39 · Concerto ✓38 · Ballet ✓10 · Gregorian Chant ✓8 · Art Song/Lied

**Latin** (19) — Reggaeton · Salsa · Bossa Nova →Jazz · Samba · Cumbia · Latin Pop →Pop · Candombe ✓13 · Murga ✓9 · Brazilian Phonk ✓6 →Electronic · Bachata · Merengue · Latin Rock →Rock · Tango · RKT · Baile Funk →Electronic · MPB · Tropicália · Mariachi · Forró

**Folk-Country** (13) — Folk · Contemporary Folk · Indie Folk · Singer-Songwriter →Pop · Americana · Country · Alt-Country · Freak Folk · Bluegrass · Outlaw Country · Country Pop →Pop · Progressive Folk · Anti-Folk

**Soundtrack** (6, *format axis*) — Film Score →Classical · Video Game Music · Anime OST ✓17 · Film Soundtrack · Musical Theatre · K-Drama OST

**World-Other** (17) — Reggae ✓14 · Roots Reggae ✓7 · Dancehall ✓11 · Dub · Riddim ✓7 · Afrobeat ✓13 · Afrobeats →Pop · Amapiano →Electronic · Gugak/Korean Traditional · Raga/Indian Classical ✓12 · Ragga · Highlife · Pansori · Flamenco · Fado · Klezmer · Celtic →Folk-Country

## Appendix B — cut candidates (excluded, with reason)

Bolero (⊂ Mariachi) · Snap (⊂ Crunk) · Turreo (⊂ RKT) · Smooth Soul (⊂ Quiet Storm) · Country Folk (= Folk+Country edge) · Sonata (⊂ Classical Piano) · Oratorio (⊂ Choral) · Library Music (format) · TV Soundtrack (format) · J-Traditional (made-up umbrella → Gagaku/Min'yō) · Tropical (catch-all) · Europop (geographic marketing). Re-add only if a clear, non-redundant need appears.
