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

### Stage 1 — the nightly memo → skeleton factory (gate met)

The gate (Step 1 proved out **and** ≥1 review hand-published) is **met** (저스디스 *LIT*). The rule
docs (`buckit-nightly-run.md` + `buckit-nightly.md`) are saved. The build is split into the steps
below; each is independently mergeable and gets the usual per-step prod-observe gate (rule #4). The
RFC Status is already `in-progress` (no further Status promotion needed); each step still gets explicit
in-session go-ahead before execution.

**Code-reality correction (found while scoping Step 2, 2026-06-18):** the earlier sketch said "the
modal composes a draft today, not the bucket note — so memo+checkbox is a net-new write path." That is
only half right. The backend **already** exposes `PATCH /api/buckets/{bucket_id}/items/{item_id}`
(`update_item`) and it **already writes `note`** (+ `research_selected`); the frontend client
(`setItemResearchSelected`) already calls it. So the net-new write work is small: (a) one new
`prep_tonight` field threaded through that existing route, and (b) **frontend plumbing** — the modal's
`DetailTarget` does not carry `bucketId`/`itemId`/`note` today (`BoardAlbum` omits `note` too), so the
memo cannot be prefilled/PATCHed until those are passed through `AlbumChip.onOpen`.

#### Step 2 — Stage 1 data layer: `prep_tonight` column + backend PATCH field

Add the "오늘 밤 키우기" gate as `review_bucket_items.prep_tonight` (BOOLEAN NOT NULL DEFAULT false;
memo store stays the existing freeform `note` — OQ8, no new column, no dated log) and thread it through
the existing item PATCH. **shared_db**: V22 additive migration + model column + regenerated
`_generated_schema.sql`/`canonical_schema.sql` + version bump → **prod apply** (`ALTER … ADD COLUMN IF
NOT EXISTS`, additive, before merge per the cross-repo rollout order). **backend**: `prep_tonight` on
`UpdateBucketItemRequest`/`BucketItemResponse` + `update_item` (set-only, **no enqueue/side-effect** —
unlike `research_selected`; the offline nightly job is the only reader) + `_item_response`; bump the
shared_db pin to the new tag; regenerate `openapi.json`. No frontend in this step.

> **Verification**: `pytest` (shared_db parity + backend buckets), `terraform plan` clean (no infra
> touch), prod schema probe confirms the column. Prod smoke post-merge.
> **Rollback**: `ALTER TABLE review_bucket_items DROP COLUMN IF EXISTS prep_tonight;` + revert the pin.

#### Step 3 — Stage 1 frontend: the memo + "오늘 밤 키우기" gate in the album-click modal — ✅ DONE (PR #177, merged + prod-smoked 2026-06-18)

**Shipped per the Claude Design handoff (`앨범 메모 컴포넌트`), which reshaped the original sketch.** Clicking
a writable, unreviewed 평론 버킷 album now opens a dedicated 2-column memo "쓰레기통" overlay (`MemoWindow`)
— album identity left, one freeform memo (→ `note`) + the "오늘 밤 키우기" toggle (→ `prep_tonight`) right —
**replacing** the old inline draft composer (`WriteBody`/`RatingInput` removed), rather than bolting a
textarea+checkbox into write-mode. Overwrite model, **debounced autosave with flush-on-unmount** (no save
button), night-mode on toggle, size m/l/xl, textarea autofocus. One "전체 에디터에서 작성 →" link preserves
the path to `/write`. Threaded `bucketId`/`itemId`/`note`/`prepTonight` through `BoardAlbum` →
`AlbumChip.onOpen` → `DetailTarget`; `updateBucketItemMemo` PATCH client (reuses the Step 2 set-only route);
`api.gen.ts` regenerated off the merged contract. Verified by a headless-CDP browser click-through
(render / toggle→night / autosave-PATCH / flush-on-close / size / ESC / autofocus) + a 5-dimension
adversarial review (1 high data-loss + 4 med/low fixed); prod-smoked via deployed-chunk grep.

#### Step 4 — Stage 1 runner: the `$0` nightly memo → skeleton job — ✅ DONE + MERGED 2026-06-18 (PR #385)

`scripts/buckit_nightly.py` (cloned from `editor_buckit.py`): a **read-only** prod export of the
`prep_tonight`-checked, unwritten, not-yet-reviewed bucket items (verbatim `note` + album/artist/genre
facts + done research-note excerpt + recent listens, **deduped by `album_id`**), then headless
`claude -p` (opus, **$0**) turns them into Korean section skeletons under `docs/buckit/<date>/`
(gitignored, OQ9 = yes). **The checkbox is the only gate**: zero checked memos ⇒ a one-line
`_summary.md` and **no claude call** (a blind timer would manufacture stale ideas).

**Architecture hardened after an adversarial tool-scope audit (this session).** The first cut let the
model write the files agentically (`--allowed-tools Write(docs/buckit/**)`). The audit refuted it on
two counts, both verified live on CLI 2.1.181: (a) the scoped `Write` glob is **denied** in headless
`-p` ⇒ the job wrote **zero files** (silently broken); (b) an unscoped `Read` + unrestricted `WebFetch`
was a **secret-exfiltration surface** (readable `~/.aws`/`~/.claude` creds, driveable by a
prompt-injection in the memo/research text). Fix: the model is now a **pure text transformer with NO
tools** — the three rule docs + the read-only context block are **inlined** into the prompt,
`--disallowed-tools` denies the whole file/network/exec surface, and `--setting-sources user` keeps the
project-local broad Bash allow-list out of the run. The model returns a delimited multi-file payload;
**the script** parses it, reduces each filename to a safe basename, and writes under `docs/buckit/<date>/`.
So "repo read + file write + Postgres read" all live in the (validated) script; the model touches
nothing — strictly safer than the agentic design and faithful to the Stage-0 clone. The
DB-write-surface and run-spec-faithfulness audit lenses both returned **safe**.

> **Verification** (no local-DB smoke harness — per `feedback-local-db-smoke-fallback` the real run
> *is* the check): a temporary `prep_tonight=true` memo was injected on one real bucket item (Frank
> Ocean — *channel ORANGE*), the job run once (**$0, 77s, opus, 2 files**), the skeleton inspected —
> inventory-shaped ✓ / candidates-not-chosen ✓ / `[passage]` blanks ✓ / verbatim memo ✓ / caught a real
> label fact-conflict ✓ / not too-finished ✓ — then the injection **fully reverted (zero residue**:
> checked-count + note-count back to 0). `py_compile` clean; `plutil -lint` OK; no PR-stage CI on the
> workspace repo (`reference-pr-ci-matrix`).
> **Rollback**: delete `scripts/buckit_nightly.py` (+ the `docs/buckit/**/*.md` gitignore line / `.gitkeep`).

#### Step 5 — Stage 1 schedule: overnight fire, checkbox-gated — ✅ DONE + MERGED 2026-06-18 (PR #385); nightly ENABLED 2026-06-18

`scripts/com.myblog.buckit-nightly.plist` (cloned from `com.myblog.research-poller.plist`): a `launchd`
agent firing `buckit_nightly.py` **once per night at 03:00** (`StartCalendarInterval`). **Host = the
owner's machine, not cloud cron** — `claude -p` is $0 only on the Max-subscription login in
`~/.claude/.credentials.json` (cloud cron needs a paid key); same precedent as the research poller.
**Not a blind timer**: it only ever acts on `prep_tonight`-checked memos; a quiet night writes a
one-line `_summary.md` and never calls claude. `RunAtLoad=false` (nightly, not on-demand); laptop-safe
(a missed 03:00 fire runs once at next wake, no stacking). Committed as an artifact + INSTALL/STATUS/STOP
instructions in the header — **the owner runs `launchctl load` to flip the schedule on** (the plist is
not auto-loaded), exactly like the research poller.

**Enabled 2026-06-18** — installed to `~/Library/LaunchAgents/` + `launchctl load -w`, then
`kickstart`-verified end-to-end under launchd's own env (found AWS creds, prod read-only, hit the
0-checked-memo gate → wrote `_summary.md`, exit 0, **$0** no claude call). The nightly and **manual**
on-demand runs (`python scripts/buckit_nightly.py`) coexist — both just invoke the same single-fire
script.

> **Rollback / kill switch**: `launchctl unload -w ~/Library/LaunchAgents/com.myblog.buckit-nightly.plist`
> (checked memos simply wait); delete the plist to remove the artifact.

### Stage 2 — in-app draft delivery (reverses the Stage-1 file-only *delivery* stance)

**Owner decision 2026-06-18 (this session):** the nightly skeleton should arrive as an **in-app
draft** the editor opens in `/write` next morning — not *only* a `docs/buckit/` file. This
reverses the file-only **delivery** decision (2026-06-18) but keeps everything else: the skeleton
**content is still inventory-shaped** (not prose — Stage 1's whole point), and generation is still
`$0 claude -p`. It is **not** the full dropped draft-factory (no new table, no `/profile` tab) —
investigation this session found the backend **already fully ready**, so the gap is small.

**Already exists (verified this session):** `posts.status` (draft|published|archived) + `body_mdx`
+ `extra` JSONB (`myblog_shared_db/.../models.py:304`); `POST /api/posts {status:'draft'}` /
`GET /api/posts?status=draft` / `GET /api/posts/{id}` (`myblog_backend/app/api/routes/posts.py:55/28/100`,
all Cognito-JWT); `/write` already loads `?id=<uuid>` for editing via `fetchPostById`
(`myblog_front/.../WriterApp.tsx:149`); `listDrafts()` exists but is **unused** (`front .../write/api.ts:20`).

**Owner-chosen shape:** **draft + local file (both)** — the draft is primary, the `docs/buckit/`
file stays as a gitignored backup (survives an API-write failure); discovery via a **'임시 저장'
inbox inside `/write`**.

#### Step 6 — frontend: '임시 저장' (drafts) inbox in `/write` — ✅ DONE (PR #178, merged + prod-live 2026-06-18)

Wired the unused `listDrafts()` + the already-wired `?id=` load into a small drafts list in `/write`:
lists `status='draft'` posts (title / `posted_date · category` / `album_cover_url`), each opening
`/write?id=<post-id>`. **Frontend-only, no backend/contract change.** Useful even before the job writes
drafts (a manually created draft shows up). Built first so discovery exists before any write path is
switched on, and because it touches only `myblog_front` (parallel-safe vs other repos).

**Shipped** as `DraftsInbox.tsx` (a `임시 저장함` dialog opened from the writer chrome's `임시 저장함`
button), statically imported by `WriterApp.tsx`. Merge commit `13fd2a9`; **Deploy Front (S3+CF)
succeeded** post-merge; the `임시 저장함` literals are present in the deployed `WriterApp.*.js` chunk
(auth-gated-front prod-smoke method, `reference-prod-smoke-auth-gated-front`).

> **Verification**: `pnpm lint` + `astro check` + a logged-in browser click-through (inbox renders,
> lists a draft, click opens it in `/write?id=`) — done pre-merge in the front PR; deployed-chunk
> literal grep confirmed live. **Rollback**: remove the inbox component.

#### Step 7 — nightly job: dual-write the skeleton as a draft post — ✅ DONE — built + verified live (e2e 9/9, $0, zero residue)

`buckit_nightly.py` keeps writing the `docs/buckit/` file **and additionally** creates a draft post:
mint a smoke-user Cognito JWT (`smoke.py get_token` USER_AUTH pattern, **$0**) → `POST /api/posts
{status:'draft', title, body_mdx:<skeleton+provenance>, category:'Reviews'}`. The job's only new
capability is **create-a-draft** (never publish — `status` hard-wired; no raw DB write — all writes via
the authed API). **Grow-once dedup** (audit-hardened): after a draft is created the job marks the memo
grown by **stamping the new `post_id` AND clearing `prep_tonight` in one item PATCH** — the `post_id`
stamp durably excludes the album next run (CHECKED_SQL `post_id IS NULL`) even if the `prep_tonight`
clear is lost, and the album-unique slug makes any re-POST 409 (rejected, never duplicated). Generation
stays `$0 claude -p`.

**Code-reality corrections (current-state audit before build):**
- **Provenance rides in `body_mdx`** (a leading HTML comment), **not `Post.extra`** — `WritePostRequest`
  is `extra='ignore'`, so an `extra` field is silently dropped and `svc.create()` has no `extra` param.
  This keeps Step 7 a **single-repo, no-contract-change** job (honoring the RFC's "no contract change"
  constraint; `openapi.json` untouched — confirmed). The draft carries **no `album_ids`** — linking
  would insert into `post_albums` (the reviewed-set + this job's own exclusion source), corrupting the
  `already_reviewed` badge and grow-once. Token read from Secrets Manager `myblog/smoke` (launchd-robust).

**Adversarial audit (re-run per the gate; 5 independent refutation lenses + synthesis).** Initial verdict
**unsafe** → fixed before ship: (#1 high) durable dedup via the `post_id` stamp above (was: a failed
uncheck → unbounded duplicate drafts); (#2 high) ASCII hex discriminator in the title — Korean-only titles
all `slugify` to `untitled`/date-digits → a 409 storm that starved delivery at ~2/night; (#3 med) `_api`
now catches transport errors (URLError/timeout → status 0 skip) + the delivery call is wrapped, so a
03:00 Neon cold-start can't crash mid-loop; (#4 med) collision-safe normalized file↔memo pairing (the
model's filename is no longer load-bearing); body-length cap; docstring/least-privilege corrections.
What held: cannot publish, no raw DB write, no `album_ids` pollution, create-only, not injection-drivable,
password/token never logged.

**Prod-pool read-only leak found + fixed (root-caused in this verification).** The first live run 500'd
on `POST /api/posts` — CloudWatch showed `cannot execute INSERT in a read-only transaction`. Root cause:
`connect()`'s session-level `SET default_transaction_read_only = on` **leaks through Neon's pgbouncer
(`-pooler`)** onto a shared server connection, which the backend Lambda then reused → its INSERT ran
read-only. Pre-existing (Step-4 code), latent until Step 7 became the first writer right after the export.
Fix: read-only is now **transaction-scoped** (`conn.read_only = True`), which never poisons the pool
(empirically: old session-`SET` → 1/14 fresh pooled conns inherit read-only; `conn.read_only` → 0/14).
This also de-poisons the already-live nightly. **`editor_buckit.py` (Stage 0) carried the same
session-`SET` leak → fixed in the same session**; `research_poller.py` + `backfill_genres.py` were
checked and connect read-**write** (no session read-only SET ⇒ no leak). See
`reference-neon-pooler-readonly-leak`.

> **Verification** (the real run *is* the check — no local DB): temp-injected a checked memo on a real item
> (혁오 *20*) → ran the full job (real opus, **94s, $0**) → asserted **9/9**: draft created (`GET ?status=draft`
> +1, `status='draft'`, `[초고]`+hex title, provenance comment w/ album_id), file backup written, memo grown
> (`post_id` stamped + `prep_tonight` cleared) → cleaned up (draft hard-deleted, item restored) = **zero
> residue**. `py_compile` + `ruff` clean. `openapi.json` unaffected (no route/contract change). No PR-stage CI
> on the workspace repo (`reference-pr-ci-matrix`).
> **Rollback**: revert the job's draft-delivery block (the read-only export + file path stay; keep the
> `conn.read_only` leak fix regardless — it is independently correct).

## Open questions

OQ1–6 resolved 2026-06-17; OQ8 resolved 2026-06-18 (see Decisions log). Reopened 2026-06-18 by the
Stage 1 redesign:

- **OQ7 (gate column):** UX resolved 2026-06-18 (see Decisions) — the memo input + the "오늘 밤
  키우기" checkbox both live in the **review-bucket album-click modal** (`AlbumDetail`, opened by
  `ProfileApp.openDetail` from `BucketBoard`). Remaining build detail: add the boolean flag column on
  `review_bucket_items` (schema has none — verify live) and a memo field bound to
  `review_bucket_items.note` + a PATCH write path. **NB the modal today composes a _draft post_, not
  the bucket note — so memo+checkbox is a net-new write path, not a tweak.**
- **OQ9 (output dir):** RESOLVED 2026-06-18 (Step 4) — `docs/buckit/<date>/` skeleton files are
  **gitignored by default** (`docs/buckit/**/*.md`, `.gitkeep` keeps the dir), like
  `docs/editorial/ideas/`. Commit a skeleton deliberately if wanted.

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
| 2026-06-18 | Stage 1 steps formalized (Step 2 data layer / 3 frontend / 4 runner / 5 schedule). **Step 2 built** (owner-approved, backend-only this session): shared_db V22 `prep_tonight` BOOLEAN + model + parity files + version bump 0.20.0→0.21.0 (prod-applied via `ALTER … ADD COLUMN IF NOT EXISTS`, verified live); backend `prep_tonight` on the **existing** item-PATCH (`update_item`, set-only no enqueue) + pin→v0.21.0 + openapi regen + test. **Correction**: the item PATCH route already existed and already wrote `note` — net-new write work was only the field + (deferred) frontend plumbing, not a whole new route | 2 |
| 2026-06-18 | Step 3 built + merged (PR #177, front-only) + prod-smoked. The Claude Design handoff (`앨범 메모 컴포넌트`) reshaped the sketch: the memo is a **dedicated 2-column `MemoWindow`** (album identity + one freeform memo + "오늘 밤 키우기" toggle; debounced autosave w/ flush-on-unmount; no save button; night-mode; size m/l/xl) that **replaces** the inline draft composer — not a textarea+checkbox in write-mode. Owner-chosen: keep one "전체 에디터에서 작성" /write link. Note→`note`, toggle→`prep_tonight` via the existing set-only item PATCH; `api.gen.ts` regen. Verified in-browser (CDP) + adversarial review (1 high data-loss + 4 med/low fixed). Only Step 4 (runner) + Step 5 (schedule) remain | 3 |
| 2026-06-18 | **Steps 4+5 built in one session** (rule #4 exception — owner explicitly OK'd doing 4+5 together; each still got its own verification gate). Step 4 = `scripts/buckit_nightly.py` ($0 nightly runner: read-only checked-memo export → `claude -p` opus → Korean skeletons in `docs/buckit/<date>/`, gitignored). Step 5 = `scripts/com.myblog.buckit-nightly.plist` (03:00 `launchd`, checkbox-gated, owner-installed; cloud cron rejected — `claude -p` $0 only on the local Max login). Verified by a temp-inject→run→revert on a real bucket item (*channel ORANGE*): skeleton confirmed inventory-shaped / candidates-not-chosen / `[passage]` blanks / verbatim memo / caught a real fact-conflict, **zero prod residue** | 4/5 |
| 2026-06-18 | **Audit-driven architecture hardening (Step 4).** An adversarial 3-lens tool-scope audit refuted the first "agentic claude writes the files" cut: scoped `Write(docs/buckit/**)` is **denied** in headless `-p` (CLI 2.1.181) ⇒ zero files written; **and** unscoped `Read` + unrestricted `WebFetch` was a **secret-exfil** surface drivable by a memo prompt-injection. Redesigned: claude = **pure text transformer, NO tools** (rule docs + context inlined; `--disallowed-tools` full file/net/exec surface; `--setting-sources user`); the **script** does all repo-read + file-write + Postgres-read and reduces output filenames to safe basenames. DB-write-surface + run-spec-faithfulness audit lenses returned **safe** | 4 |
| 2026-06-18 | **Stage 2 opened — in-app draft delivery.** Owner reversed the file-only *delivery* stance: the nightly skeleton should land as an **in-app draft** opened in `/write`, not only a file. Skeleton CONTENT (inventory-shaped) + `$0` generation unchanged; NOT the full dropped factory — investigation found the backend already ready (posts.status/body_mdx/extra; POST/GET draft routes Cognito-JWT; `/write` loads `?id=`; unused `listDrafts()`). Owner-chosen: **draft + local file both**; discovery via a **'임시 저장' inbox in `/write`**. Steps 6 (frontend inbox — independent, first, `myblog_front`-only) / 7 (job dual-writes a draft via a minted smoke JWT, audit-gated; auto-unchecks the memo after = grow-once) | 6/7 |
| 2026-06-18 | **Step 6 DONE + MERGED + prod-live** (front #178, `13fd2a9`; Deploy Front success; `임시 저장함` literals verified in the deployed `WriterApp.*.js` chunk). `DraftsInbox.tsx` lists `status='draft'` posts → `/write?id=`, statically imported by `WriterApp` | 6 |
| 2026-06-18 | **Step 7 built + verified live** (workspace `buckit_nightly.py` only). Two RFC-premise corrections from a current-state audit: provenance → `body_mdx` HTML comment (NOT `Post.extra` — `WritePostRequest` is `extra='ignore'` ⇒ dropped), and **no `album_ids`** on the draft (would pollute `post_albums`). Adversarial re-audit (5 lenses) returned **unsafe** → fixed: durable grow-once stamps `post_id`+clears `prep_tonight` in one PATCH; ASCII hex title discriminator kills the Korean-`untitled`-slug 409 storm; `_api` catches transport errors; collision-safe file↔memo pairing; body cap. **Prod-pool read-only leak root-caused + fixed**: session `SET default_transaction_read_only=on` leaks through Neon pgbouncer (`-pooler`) → backend INSERT 500'd; switched to transaction-scoped `conn.read_only` (empirically 0/14 vs 1/14 poisoned). Verified live: temp-inject 혁오 *20* → real opus run (94s, $0) → 9/9 (draft+file+grown) → zero residue. `openapi.json` unaffected (no contract change). `editor_buckit.py` (Stage 0) carried the same leak → fixed same session; research_poller/backfill_genres verified read-write (no leak). `reference-neon-pooler-readonly-leak` | 7 |
