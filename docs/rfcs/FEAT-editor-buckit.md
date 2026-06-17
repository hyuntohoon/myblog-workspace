# FEAT-editor-buckit: editorial commissioning desk (pre-writing idea generator)

- **Status**: in-progress (accepted + execution started 2026-06-17, owner-approved)
- **Owner**: 박지훈
- **Created**: 2026-06-17
- **Plan row**: `plan.md` → FEAT-editor-buckit (Active)

---

## Goal

After **Stage 0** of this RFC, the owner can run **one offline `$0` command** that reads the
albums **already saved in their review buckets** (plus those buckets' notes, recommendation
reasons, and AI research notes) and the **current critical conversation pulled live from the web**,
and emits a dated **Markdown idea report** — a short deck of *editorial commission cards*. Each card
answers *"what should I write next, and from what angle?"*: a recommended **album from the owner's
own catalog**, a sharp **core question**, 4–5 probing **subtopics**, a working **title direction**, a
loose **structure**, the **article type**, **why now** (grounded in a real bucket/listening signal),
and **reference links** the web step found (reading material to absorb, not copy).

It is a **pre-writing** tool — it proposes *what to write before a draft exists*. It never writes
prose, never publishes, and is owner-only. Stage 0 is deliberately the cheapest possible proof: a
**single `claude -p` script, no DB table, no backend route, no frontend, no scheduler, no API key** —
mirroring the proven `$0` album-research-note path. Stage 1 (an in-app surface) is **explicitly
gated** on Stage 0 proving the ideas are good *and* on ≥1 review existing — see Non-goals + the
future-steps sketch.

### Relationship to FEAT-ai-editorial-critique (do not conflate)

These are **opposite ends of the same funnel** and are separate features:

| | **FEAT-editor-buckit** (this RFC) | **FEAT-ai-editorial-critique** |
| --- | --- | --- |
| When | *Before* a draft exists | *After* a draft exists |
| Job | Propose what to write (topic / album / angle) | Critique an existing draft against the method doc |
| Input spine | Review **buckets** + live web angles | A draft's `body_mdx` + its album facts |
| Surface | Offline Markdown report (Stage 0) | `POST /api/editorial/critique` (UI-less) |
| Writes prose? | Never | Never (feedback only) |

Editor Buckit is the **commissioning** step; the critique engine is the **editing** step. Neither
depends on the other. Editor Buckit ships standalone.

### Why this is the one AI feature that can run at n=0

The whole roadmap is gated on **editorial volume** (~0–1 published reviews ever; posts reset to 0 in
STAB-5), and prior AI features were parked because tooling at n=0 "automates an empty funnel." Editor
Buckit is the **exception**: at n=0 the binding constraint *is* "I don't know what to write first,"
and that is exactly what this attacks — **provided** it grounds on the buckets (a populated,
intentional signal) rather than the empty review corpus, and **provided** it stays cheap enough that
it can't waste the owner's writing energy. Both provisions are baked into the design below. The tool
is even allowed to conclude *"stop ideating — go write the album already sitting in your bucket."*

## Non-goals

Anti-scope-creep insurance. Each is **out of Stage 0**; most are deferred to Stage 1 or later:

- **No new real-time AI API endpoint.** Generation is offline only. (Hard owner constraint.)
- **No paid LLM path.** No `ANTHROPIC_API_KEY`, no paid Lambda. Stage 0 uses `claude -p` on the
  owner's Max subscription = `$0`, exactly like `scripts/research_poller.py` and
  `scripts/backfill_genres.py`. The dormant `researchWorkerLambda`/`researchSQS`/`myblog/anthropic`
  shell stays inert (it has no consumer code anyway).
- **No DB table** in Stage 0. The report is a file. (Stage 1 introduces one additive table; until
  then, nothing is persisted to Neon.)
- **No backend route, no `openapi.json`/`api.gen.ts` regen, no frontend, no `/profile` tab, no
  `/write` panel** in Stage 0.
- **No scheduler / launchd / cron / auto-fire** in Stage 0. Manual-fire only — the owner runs it when
  the bucket has new signal. (A blind timer would manufacture stale ideas on quiet days — the exact
  repetition the owner fears.)
- **No crawler and no external-article archive.** The web step is a per-run live search read as
  context; nothing is scraped, stored, or republished. Reference links are surfaced on the card as
  reading material.
- **No grounding on published reviews as a positive signal** (owner decision — "using my reviews as
  the basis is risky"). Reviews are used **only as an exclusion set** (don't re-pitch what's written).
- **No prose generation, no publishing, no auto-conversion to a draft.** The tool suggests; the owner
  writes.
- **No heavy anti-copy machinery** (mandatory angle-abstraction, headline-overlap rejection,
  outlet-name bans). Owner decision: surfacing a *similar topic* is fine — citing/quoting a live
  critical topic and applying it to the owner's album is desired; the written review's content will
  be the owner's own. The only structural guard kept is **catalog-anchoring** (below), which is a
  *quality* gate, not a copyright gate.
- **No multi-user / `user_id` scoping** (single-user system, consistent with every other table).

## Current state

- **Nothing named "editor-buckit" exists** — verified: zero hits across `docs/`, all 5 repos, and
  memory. The term is new; it is **not** a rename of `FEAT-ai-editorial-critique` (draft) or
  `FEAT-bucket-identity` (in-progress).
- **The proven `$0` generation pattern to clone**: `scripts/research_poller.py` shells
  `claude -p --output-format json --allowed-tools WebSearch,WebFetch --model opus` on the Max
  subscription (no API key), reads prod `DATABASE_URL` from Secrets Manager `myblog/backend`, and
  runs on the `myblog_backend/.venv` (has `psycopg` + `boto3`). It has a `run_claude()` wrapper
  (parses `.result`/usage, handles `is_error`/timeout) that is directly reusable. The companion
  `docs/editorial/album-research-prompt.md` + vendored `scripts/album_research_v2.md` + a
  `PROMPT_VERSION` constant is the prompt-vendoring convention.
- **The bucket spine** (single-user, no `user_id` anywhere): `review_buckets` (id, name, kind
  `review`|`spotify_library`, `is_public`, `research_mode` `off`|`all`|`selected`, `parent_id` tree,
  `is_done`) → `review_bucket_items` (`album_id`, `note`, `rec_reason`, `status`
  candidate|drafting|published, `post_id` FK→posts, `research_selected`). `UNIQUE(bucket_id, album_id)`.
- **Supporting signals**: `album_research` (`result_md`, `status`) = per-album AI research notes for
  bucketed albums; `spotify_play_events` (album-grain listening log, never pruned); `post_albums` M:N
  = the **reviewed-album set** (the exclusion source, same derivation as the `already_reviewed`
  badge / `GET /api/library/reviewed`); the 4-tier genre taxonomy + `post_genres`.
- **Editorial volume**: ~0–1 published reviews ever (STAB-5 reset posts to 0). So the bucket /
  listening / research-note signals are the only meaningful own-data at present — which is precisely
  why grounding is on buckets, not reviews.
- **Future handoff plumbing** (was for the dropped in-app draft-factory; **superseded 2026-06-18** by
  the file-only redesign — Stage 1 no longer seeds drafts into `/write`): `WriterApp.tsx` parses
  `?album=<id>` on mount; `AlbumDetail.tsx:309` builds `/write?album=<id>` links; `Post.extra` (JSONB,
  unused) was the provenance sink; `NoteBody.tsx` + `research.css` the display pattern. Retained here
  only as a record — none of it is on Stage 1's path now.
- **DB safety**: prod `DATABASE_URL` is `postgresql+psycopg://`; convert for `psql`; use
  `BEGIN…ROLLBACK` / read-only SELECTs (`reference-database-url-psql`). Prod Lambda
  `LOG_LEVEL=WARNING` (irrelevant to a local script, but stated for completeness).

## Target state

### Stage 0 (this RFC's MVP) — one command, one report, zero infra

Three new artifacts in the **workspace repo** (operator tooling, not a deployed service):

1. **`scripts/editor_buckit.py`** (~150–200 lines, cloned from `research_poller.py`; **drops** the
   claim-gate/queue/launchd/DB-writeback). Flow per run:
   - `export_bucket_context()` — **read-only** SELECTs against prod Neon (`DATABASE_URL` from secret
     `myblog/backend`; wrap in `BEGIN…ROLLBACK`, never writes). Assembles a compact context block:
     - **Spine**: `review_bucket_items` where `post_id IS NULL` (saved-but-unwritten) + their
       `note` + `rec_reason` + parent bucket name/`research_mode`, resolved to album/artist/genre
       facts.
     - **Amplifier**: matching `album_research.result_md` excerpts (a done note = "ready to write").
     - **Clusters**: genre/artist groupings *within the bucketed albums* (for essay/genre/artist
       angles).
     - **Secondary why-now**: light `spotify_play_events` recency for bucketed albums.
     - **Exclusion only**: `album_id ∈ post_albums` (already-reviewed) → never re-pitch.
   - Builds the prompt (system = the prompt doc below) + the context block.
   - Shells `claude -p --output-format json --allowed-tools WebSearch,WebFetch --model opus`
     (web tools are **load-bearing** here — references are fetched live per run; model never touches
     the DB).
   - Parses `.result`, writes `docs/editorial/ideas/YYYY-MM-DD.md`; logs tokens/model to stderr.
2. **`docs/editorial/editor-buckit-prompt.md`** — the canonical prompt (sibling of
   `review-critique-method.md` / `album-research-prompt.md`). Vendors the voice / North Star from
   `review-critique-method.md`. Instructs, in order:
   1. **Live web read** — WebSearch the current critical conversation (broadly, and around the
      albums/artists/genres in the context block); collect the topics/angles critics are engaging
      with **and their links**. Topic *similarity* is fine; relay reference *opinions/scores* as
      opinion, never as fact.
   2. **Read the bucket context block.**
   3. **Cross-pollinate** → produce **3–5** commission cards (fewer when the bucket is thin),
      **each anchored to a real catalog entity from the context block** — a specific `album_id`, or
      (for essay / genre / artist pieces) an artist or genre present in the bucket. A card with no
      bucket anchor is invalid and must be dropped. Include the reference links found, as
      "참고 / 영감" reading material.
   4. **Self-critique** — drop any card that (a) could exist without *this* catalog (the
      "could a wiki have written this?" kill-test), (b) is grounded only in a just-listened album
      with no bucket/note/research signal, or (c) duplicates a prior report. **Returning fewer cards —
      or zero — is correct and expected**; if the bucket is thin, say so and tell the owner to add
      albums/notes or just write the one already bucketed.
   5. Output **Korean Markdown only**, one section per card with the fields below.
3. **`docs/editorial/ideas/`** (output dir; `.gitkeep`). Reports are **gitignored by default** (they
   reveal unpublished editorial direction); the owner can commit a report deliberately if wanted.

**Idea card fields** (Markdown sections per card):

- **추천 앨범** — album(s) from the bucket context (with `album_id` for a future deep-link).
- **주제 (main topic)** + **핵심 질문 (core question)** — the sharp tension the piece argues.
- **소주제 4–5개** — each an angle/sub-tension, not a section label.
- **글 유형** — `리뷰확장 | 에세이 | 칼럼 | 아티스트론 | 장르론 | 리스트/피처 | 짧은 노트`.
- **제목 방향** — a working title (overridable).
- **구조 스케치** — a loose `##` skeleton.
- **왜 지금** — names the real signal (bucket dormancy / done-research-unwritten / genre cluster /
  recent listen).
- **참고 / 영감** — 1–3 reference links the web step surfaced (to read, not copy).

**The one command**: `myblog_backend/.venv/bin/python scripts/editor_buckit.py`.

### Stage 1 (the nightly memo → skeleton factory — redesigned 2026-06-18, gate now met)

Stage 1 is **not** the in-app draft-factory the earlier sketch described (an `editor_buckit_ideas`
table + poller + `/profile` tab + a `POST /api/posts {status:'draft'}` seed into `/write`). That
design was **dropped 2026-06-18**. Stage 1 keeps the **same `$0` file-only safety class as Stage 0**:
an unattended overnight `claude -p` job that turns a **checked** bucket memo into a Korean **section
skeleton file** under `docs/buckit/<YYYY-MM-DD>/` — no DB write, no backend route, no frontend, no
API key. The only thing it touches is its own output files.

- **Rule docs (canonical, saved):** `docs/editorial/buckit-nightly-run.md` (the run spec / entry
  point handed to `claude -p`) + `docs/editorial/buckit-nightly.md` (the memo→skeleton conversion
  rules), both **inheriting** the ★ honesty line + §6 language bans from
  `docs/editorial/review-critique-method.md` (v2.5). These supersede the retired
  `editor-buckit-draft-prompt.md` strawman (deleted 2026-06-18).
- **What it produces:** an **inventory-shaped** skeleton — what exists / what's confirmed / what
  others said / open questions — never a thesis. It expands *only* the editor's own judgments, leaves
  evidence as `[passage]` blanks, lists the controlling-idea **candidates without choosing one**, and
  marks every open question as a blank. A too-finished skeleton is a bug. **Zero outputs is a valid
  run.**
- **The gate = one explicit checkbox.** "오늘 밤 키우기" checked on a memo is the human go-ahead; the
  job processes only checked memos. This is what reconciles a **nightly scheduler** with Stage 0's
  anti-blind-timer constraint — the timer is not blind, it only ever acts on memos the editor
  deliberately flagged.
- **Build scope (when steps are authored):** the new data the design needs — a "오늘 밤 키우기" flag
  on the memo — plus the output-dir convention. The memo store is a **single freeform field**
  (`note`, overwrite); **no dated-memo log** (dropped 2026-06-18 — no value). Output files likely
  gitignored like `docs/editorial/ideas/` (they reveal unpublished direction).

The Stage 1 gate (Stage 0 proved out + ≥1 hand-published review) is **now met** (the 저스디스 *LIT*
review exists). Stage 1 is therefore unblockable, but still gets its own steps + a human-approved
Status action per hard rules #4/#5 before any build.

## Steps

Each step independently mergeable. Hard rule #4 — one step per session. This is a single-repo
(workspace) docs/tooling RFC; no contract/infra touch in Stage 0.

### Step 0 — RFC + plan.md pointer + README index (docs-only) — *this document*

This RFC, a one-line `plan.md` Backlog pointer, and a `docs/rfcs/README.md` index entry. No code.

> **Verification**: doc review against `docs/rfcs/README.md` "Required sections". `git diff --stat`.

---

### Step 1 — Stage 0: the `$0` script + prompt doc + output dir (the whole MVP)

Create `scripts/editor_buckit.py`, `docs/editorial/editor-buckit-prompt.md`, and
`docs/editorial/ideas/.gitkeep`; add `docs/editorial/ideas/*.md` to `.gitignore`. Clone
`run_claude()` + the Secrets-Manager `DATABASE_URL` read from `research_poller.py`. **Read-only DB**
(`BEGIN…ROLLBACK`); the script never writes to prod. No infra, no backend, no frontend, no API key.

> **Verification** (no local DB on this machine → eyeball, per `feedback-local-db-smoke-fallback`):
> ```
> myblog_backend/.venv/bin/python scripts/editor_buckit.py
> #   → writes docs/editorial/ideas/YYYY-MM-DD.md
> ```
> Read one report and confirm: (a) **every card cites a real bucketed `album_id`**; (b) "왜 지금"
> names an actual signal, not "흥미로워서"; (c) reference links resolve and are surfaced as reading
> material; (d) a thin bucket yields *few or zero* cards + an honest note, not 5 forced ones.
> Success = the owner gets a report they'd act on (ideal: one card pulls them into `/write`).
>
> **Rollback**: delete the three files + the `.gitignore` line. Nothing else touched (trivial).

---

### Steps 2+ — Stage 1: the nightly memo → skeleton factory (gate met, steps to be authored)

The gate (Step 1 proved out **and** ≥1 review hand-published) is now **met** (저스디스 *LIT*). The
rule docs (`buckit-nightly-run.md` + `buckit-nightly.md`) are saved; what remains is the build, which
gets its own steps + a human-approved Status action (rules #4/#5) before execution. Expected shape:

1. **Data + gate** — add the "오늘 밤 키우기" flag on `review_bucket_items` (memo store = single
   freeform `note`, no dated log) + a memo field + the checkbox in the **bucket album-click modal**
   (`AlbumDetail`); needs a PATCH write path (the modal composes a draft today, not the bucket note).
2. **The runner** — a `$0` `claude -p` script (clone `editor_buckit.py`) that reads checked memos +
   facts **read-only**, runs `buckit-nightly-run.md`, and writes skeleton files to
   `docs/buckit/<date>/`. Tool scope = repo read + file write + Postgres MCP read; **no**
   git-write/merge/delete.
3. **Schedule** — overnight fire, gated by the checkbox (not a blind timer).

See the redesigned Stage 1 in Target state.

## Open questions

OQ1–6 resolved 2026-06-17; OQ8 resolved 2026-06-18 (see Decisions log). Reopened 2026-06-18 by the
Stage 1 redesign:

- **OQ7 (gate column):** UX resolved 2026-06-18 (see Decisions) — the memo input + the "오늘 밤
  키우기" checkbox both live in the **review-bucket album-click modal** (`AlbumDetail`, opened by
  `ProfileApp.openDetail` from `BucketBoard`). Remaining build detail: add the boolean flag column on
  `review_bucket_items` (schema has none — verify live) and a memo field bound to
  `review_bucket_items.note` + a PATCH write path. **NB the modal today composes a _draft post_, not
  the bucket note — so memo+checkbox is a net-new write path, not a tweak.**
- **OQ9 (output dir):** `docs/buckit/<date>/` skeleton files — gitignored by default like
  `docs/editorial/ideas/`?

## Decisions log

| Date | Decision | Step |
|------|----------|------|
| 2026-06-17 | Editor Buckit = a *pre-writing* commissioning desk; distinct from FEAT-ai-editorial-critique (opposite funnel end). Proposes what to write; never writes prose / publishes | 0 |
| 2026-06-17 | MVP = Stage 0: a single `$0` `claude -p` script → dated Markdown report. No table, no backend, no frontend, no scheduler, no API key. Stage 1 (in-app) gated on Stage 0 proving out + ≥1 review | 0/1 |
| 2026-06-17 | Grounding spine = review **buckets** (saved-but-unwritten items + notes/rec_reason + research notes). Published reviews used as **exclusion only** — grounding on reviews is "risky" at n=0 (owner) | 1 |
| 2026-06-17 | References = **live per-run WebSearch**, surfaced as 참고/영감 links on the card. Topic *similarity* is fine (not copying — the written review is the owner's own); heavy anti-copy machinery dropped. Only structural guard kept = catalog-anchoring (a quality gate) | 1 |
| 2026-06-17 | "No good idea right now" / "go write the album already in your bucket" are valid, expected outputs — silence beats recycling; addresses the owner's repetition fear | 1 |
| 2026-06-17 | OQ1: live WebSearch is **both** broad (current critical conversation) + narrow (bucket albums/artists/genres) in one pass | 1 |
| 2026-06-17 | OQ2: **3–5** cards per run (fewer/zero when the bucket is thin) | 1 |
| 2026-06-17 | OQ3: anchor may be a specific `album_id` **or** an artist/genre present in the bucket (essay/genre/artist pieces) — never from the void | 1 |
| 2026-06-17 | OQ4: reports **gitignored by default** (`docs/editorial/ideas/*.md`); owner commits a report deliberately if wanted | 1 |
| 2026-06-17 | OQ5: Stage 0 runs *before* the first review (the "what to write first" unblocker); Stage 1 gated until ≥1 review exists | 1 |
| 2026-06-17 | OQ6: a simple version string in the prompt-doc report header only; no poller/service duplication to sync in Stage 0 (full vendoring convention deferred to Stage 1) | 1 |
| 2026-06-17 | Owner accepted + promoted Status draft → in-progress; Step 1 executed on `feat/FEAT-editor-buckit-stage0`: `scripts/editor_buckit.py` (read-only prod export, candidates **deduped by album_id**) + `docs/editorial/editor-buckit-prompt.md` (3-draft judge-panel synthesis) + `docs/editorial/ideas/` (gitignored). Read-only dry-run verified live (68 distinct bucket albums, 1 reviewed excluded) | 1 |
| 2026-06-18 | Stage 1 redesigned: **dropped** the in-app draft-factory sketch (table + poller + `/profile` tab + `POST /api/posts {status:'draft'}` seed into `/write`) → Stage 1 is now a **`$0` file-only nightly** memo→skeleton job, same safety class as Stage 0. Output = Korean skeleton files under `docs/buckit/<date>/`; no DB/route/frontend | 1 |
| 2026-06-18 | Canonical Stage 1 rule docs saved: `docs/editorial/buckit-nightly-run.md` (run spec) + `docs/editorial/buckit-nightly.md` (conversion rules), inheriting ★ + §6 from `review-critique-method.md` (v2.5). The competing strawman `editor-buckit-draft-prompt.md` retired (deleted) | 1 |
| 2026-06-18 | Skeletons are **inventory-shaped, never thesis-shaped** — expand only the editor's judgments, evidence→`[passage]` blanks, controlling idea = candidates not chosen, ask→mark. A too-finished skeleton is a bug; zero outputs is valid | 1 |
| 2026-06-18 | A **nightly scheduler is allowed for Stage 1** (reverses the Stage-0 no-scheduler stance) because the **"오늘 밤 키우기" checkbox** gates it — the timer acts only on memos the editor explicitly flagged, so it is not the "blind timer" Stage 0 banned | 1 |
| 2026-06-18 | OQ8: **no dated-memo log** — the memo store stays a single freeform field (`note`, overwrite). Then→now reappraisal via a dated log is "의미 없어" (owner) → dropped; the nightly run's "prior dated memos" input removed | 1 |
| 2026-06-18 | OQ7 (gate UX): the memo + the "오늘 밤 키우기" checkbox both live in the **review-bucket album-click modal** (`AlbumDetail` via `ProfileApp.openDetail`) — write the memo there, check it there. Build detail: new flag column on `review_bucket_items` + memo bound to `note`; the modal composes a draft post today, so this is a **net-new write path** | 1/2 |
| 2026-06-18 | Stage 1 gate (Stage 0 proved out + ≥1 hand-published review) **met** (저스디스 *LIT*) → Stage 1 unblockable; still needs own steps + human Status action before build | 1/2 |
