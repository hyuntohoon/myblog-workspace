# FEAT-bucket-identity: strengthen the "bucket" as the core workflow unit

- **Status**: in-progress (Direction A DONE 2026-06-16; **Direction B SHIPPED 2026-07-21, front #303** — landing-tab promotion left as an owner-pending proposal; Direction D surfaces remain)
- **Owner**: 박지훈
- **Created**: 2026-06-16
- **Plan row**: `plan.md` → FEAT-bucket-identity
- **Origin**: 2026-06-16 UX brainstorm (item 14 of the UX sweep). A 10-agent
  read-only inspection mapped the current bucket surface; this RFC records the
  directions so B/C aren't lost.

> **2026-06-23 — relationship update.** `docs/rfcs/FEAT-pocket-buckit.md` is now the
> **canonical top-level product + interaction definition** for Buckit. This RFC is
> hereby scoped as the **compatibility / migration / integration** track for the
> *existing* review buckets, the `들을 것` data, and the public-collection (Direction D)
> work — it **aligns to** the Pocket Buckit bucket model rather than competing with it.
> Direction C ("one shelf object") is **subsumed** by Pocket Buckit's generalized-membership
> direction; the technical migration **shipped as V30/V31 2026-06-24** (`들을 것` → `kind='to_listen'`
> system bucket, Neon-prod-live), tracked in `FEAT-pocket-buckit` → D2 + Decisions log. Directions A/B/D
> stay valid as legacy-surface work that must conform to the Pocket Buckit model.

---

## Goal

Make "bucket" read as the product's **core workflow unit** — save an album →
research it → listen → notes → convert to a review → link the finished review
back — instead of a save-list with a confused name. The user-facing object
should have **one name** and a **status that reflects real state**, and the
board should be a visible pipeline rather than a tiny shortcut tile.

## Non-goals

- Renaming the DB tables (`review_buckets` / `review_bucket_items`) — internal,
  not user-facing.
- Merging the listening axis (`spotify_*` caches) into the bucket model
  (that's Direction C, explicitly the "if we commit" option, not the default).
- Multi-user buckets / accounts (covered by `FEAT-multi-user-accounts`).

## Current state (the weakness)

The flow exists end-to-end but is spread across surfaces with **four vocabularies
for one object**:
- product/tab label: `평론 버킷` (`ProfileApp.tsx:21`)
- code + UI: `크레이트` (`BucketBoard.tsx` header/DnD/trash)
- DB/contract: `review_buckets`
- a 4th "status tag" layer **regex-inferred from the bucket's free-text name**
  (`crMeta`, `BucketBoard.tsx:342`) — rename a bucket and its lifecycle tag
  silently changes meaning; only `is_done` is a real typed field.

Other gaps: the listening axis (`최근 들은`/`지금 재생`, `library.py`) is fully
disjoint from the bucket an album lives in; there is no reverse link
review→bucket/research; the board is one small count tile on the 개요 tab
(`OverviewDash.tsx`), the least prominent surface for the product's actual engine.

## Directions (from the brainstorm)

### Direction A — one name, honest naming (front-only, S) — **DONE 2026-06-16**
Collapse the user-facing vocabulary to **버킷** (drop the `크레이트` alias from the
board kicker/comment; the tab is already `평론 버킷`), and align the `is_done`
409 message to the board's `평론 완료` tag. Shipped: front #173 + backend #77.
The internal `crate`/`crMeta` code identifiers are not user-visible and were left.

### Direction B — the board is the workspace (front-mostly, M) — ✅ SHIPPED 2026-07-21 (front #303, front-only)

> **Shipped scope + judgment calls (2026-07-21):** `crMeta` name-regex fully removed; the
> lifecycle tag derives only from typed fields, precedence 완료(`is_done`) → 작성 중 (subtree
> item has `post_id` and not `already_reviewed`) → 조사 중 (subtree item research
> queued/running/**done** — a completed note still marks the research phase; `failed` does
> not elevate) → 담음; parent buckets aggregate their whole subtree; 청취 예정 stays
> kind-based. The name-regex urgency accent (급한/마감) was **dropped** — no typed deadline
> field exists; accent now comes only from the explicit bucket color. `post_id` was already
> on the item contract → mapped as `postId` in `buckets.ts`, zero backend change. Listened
> join = client-side (`GET /api/library/listened-albums` once per board mount, quiet on
> 401/404) → hollow-ring "이미 들음 → 평론 가능" hint on not-yet-reviewed covers. Reverse
> links on ReviewsTab only (버킷 chip: `postId` match, album-id fallback via the shared
> bucketStore; 조사 노트 chip: one batched `/api/research/status` GET), navigating to
> `?tab=bucket`; nothing on public `/review/{slug}` (privacy — owner call). Bonus rider:
> the member-player 6b bucket-row entry ("이 앨범 재생 ▶" in the album action sheet) landed
> in this PR per the file-ownership split with front #302. Verified: lint + astro check
> clean; CDP at prod scale (10 buckets/~200 items) 18/18 + 6/6; prod markers in
> `SelfDashboard.*.js` post-deploy 29783059420.
>
> **Owner-pending (proposed, NOT shipped):** (1) board → `/profile` landing tab promotion;
> (2) research-note deep link from the review chip (needs a board `?album=` param);
> (3) in-place tab switch for the 버킷 chip (one `onSelectTab` prop through SelfDashboard).
Make the pipeline explicit and the board prominent:
- Replace the name-regex `crMeta` with a status **derived from real fields already
  on the contract**: `research_status` (per item), `already_reviewed`,
  `post_id`/draft presence, `is_done` → a `담음 → 조사 중 → 작성 중 → 완료` lifecycle
  that stops lying when a bucket is renamed.
- Surface a per-album "이미 들음 → 평론 가능" hint by joining the listened set
  (`library.py`) onto bucket covers. Read-only; mostly front. A small backend
  add only if you want listened-state inside `GET /api/buckets` instead of a
  second client-side fetch.
- Consider promoting the board from a 개요 shortcut tile to a more prominent
  surface (possibly the landing tab).
- Cross-cutting: add the reverse link **review → source bucket/research** on
  `ReviewsTab` cards and/or the published `/review/{slug}` (research note is
  album-keyed, already exists) so the bucket's role stays visible after publish.

### Direction C — one shelf object (structural, L) — subsumed + SHIPPED by FEAT-pocket-buckit V31
> **Resolved 2026-06-24:** subsumed + SHIPPED by FEAT-pocket-buckit V31 (들을 것 → `kind='to_listen'` system bucket holding `item_type='album'` members, Neon-prod-live 2026-06-24). See `FEAT-pocket-buckit.md` → D2 + Decisions log. The original exploration below is kept for context.

Merge `들을 것` (`album_to_listen_items`, V8) into the bucket model as a seeded
system bucket so there is **one save target** and an album lives one place through
its whole life (담을지/들을지/평론할지 are states, not separate tabs). Library
becomes listening-history-only. Highest identity payoff, highest cost (backend +
data migration + front rework). Propose only if the two save-queues are judged an
accident worth unwinding.

### Direction D — bucket as a flexible PUBLIC collection (owner direction, 2026-06-16)
Beyond the personal save→review workflow, the owner wants **"bucket" = a flexible
collection ("모음")** surfaced publicly, used in several ways:
- **장르 평론 모음** — a curated set of reviews for a genre.
- **플레이리스트 / 추천 음반 모음** — recommended-album collections.
- **아티스트 모음** — an artist's albums as a collection.
- **이번 주 / 신보 모음**, **명반 모음**, etc.

Infra already exists: `FEAT-public-bucket-multiuser` shipped the public bucket
viewer (`/collection`, opt-in `is_public`, `GET /api/buckets` via edge_guard). So
the owner can curate public buckets that read as magazine collections.

**Caveat the owner flagged:** if the flexible-bucket meaning is provided too
*minorly / abstractly*, it loses meaning and confuses readers. So the **home
stays clear/general** — the magazine basics (BNM feature, latest reviews, genres)
in the chosen **Variant B** form — and the multi-meaning bucket collections are
surfaced on dedicated surfaces (`/collection`, genre/artist pages), NOT crammed
onto the home. The B home's mock bucket-curation rows (`이번 주 버킷` / `추천 버킷`)
are therefore **deferred** until curated public-bucket / new-release data is ready
to feed the home in a way readers immediately understand.

Status: **home shipped in Variant B** (front #176, `FEAT-home-redesign-v2` DONE);
the public-collection bucket surfaces are the next concrete step here.

## Open questions

- Direction B prominence: should the board become the `/profile` **landing tab**
  instead of 개요? **(still open — proposed to the owner at B ship, 2026-07-21)**
- ~~Listen→review join: worth a backend change to put listened-state inside
  `GET /api/buckets`, or keep a client-side join?~~ **SETTLED 2026-07-21: client-side**
  (one archive GET per board mount was cheap; keeps B front-only).
- ~~Direction C: are `들을 것` (to-listen) and `평론 버킷` genuinely two intents, or
  an accident of incremental building? (Decides whether C is desirable at all.)~~
  **SETTLED 2026-06-24:** FEAT-pocket-buckit D2 decided yes-merge (one shelf object); V31 executed it (`들을 것` → `kind='to_listen'` system bucket, prod-live).
- Is the lifecycle (담음→조사→작성→완료) the real product spine, or should the board
  stay free-form crates the user names themselves? (If the latter, only A was
  needed and the name-regex `crMeta` is arguably fine.)
