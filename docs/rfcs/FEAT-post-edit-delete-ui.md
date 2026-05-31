# FEAT-post-edit-delete-ui: Author-facing edit / delete for published posts

- **Status**: accept
- **Owner**: TBD
- **Created**: 2026-06-01
- **Plan row**: `plan.md` → FEAT-post-edit-delete-ui

---

## Goal

After this RFC, the logged-in author can **edit** and **remove** an already-**published** post entirely from the UI, with deletion also un-publishing the static page. Today the backend fully supports edit/delete/restore and the editor can re-open any post by id — but there is **no UI path** from a published post to those capabilities, and deleting a published post leaves its static MDX page live on the site. This closes both gaps.

## Non-goals

- **No backend route changes for edit.** `PUT /api/posts/{id}` and the WriterApp republish flow already work end-to-end.
- **No comments / likes write paths** — separate dormant feature.
- **No genre taxonomy work** — FEAT-genre-taxonomy explicitly "rides with the future post edit/delete logic"; this RFC unblocks it but does not implement multi-genre editing.
- **No bulk operations** (multi-select delete/archive).
- **No new list/search surface** beyond reusing the existing `/drafts` page infrastructure.

## Current state

Concrete, verified 2026-06-01:

**Backend (done, JWT-gated at API Gateway + in-Lambda after the recent auth fix):**

- `PUT /api/posts/{id}` — `myblog_backend/app/api/routes/posts.py` `update_post`.
- `DELETE /api/posts/{id}?hard=<bool>` — `delete_post`: `hard=false` soft-archives (`status='archived'`, 200), `hard=true` hard-deletes (204). **`PostService.delete` touches the DB only — it does NOT remove the published MDX from GitHub.**
- `PATCH /api/posts/{id}/restore` — `restore_post`.

**Frontend editor (`myblog_front/src/components/writer/WriterApp.tsx`):**

- `?id=` in the URL loads a post from the DB for editing (`WriterApp.tsx:136-143`, `fetchPostById`).
- Publish flow (`:264-305`): when `dbPostId` is set it calls `updatePost(dbPostId, {status:'published'})` **then `publishToGit`** (re-writes the MDX). So editing a published post and re-publishing already works — _if_ the user can reach the editor with `?id=`.

**Frontend list (`myblog_front/src/pages/drafts.astro`):**

- Two tabs only: `초안` (status=draft) and `보관함` (status=archived). Published posts are **not listed**.
- Per-row actions already implemented: `편집` (→ `/write?id=`), archive, restore, hard-delete (confirm modal).

**The gaps:**

1. A **published** post appears in no author list (`/drafts` excludes `published`), and `/blog/[slug]` has no author affordance — so there is no entry point to edit or delete it.
2. Deleting a published post (archive or hard) leaves the **static MDX page live** (the content file is never removed / the site never rebuilds the removal).

## Target state

- `/drafts` gains a `발행됨` (published) tab listing `status=published` posts, reusing the existing row + action infrastructure: `편집` (→ `/write?id=`), `발행 취소`(unpublish→archive), `완전 삭제`(hard delete).
- `/blog/[slug]` shows an author-only `편집` link (rendered when `isLoggedIn()`), deep-linking to `/write?id=<post-id>`.
- Deleting **or** unpublishing a published post also removes its MDX from the content repo and triggers a rebuild, so the static page disappears.

## Steps

Steps 1 and 2 are frontend-only and independently mergeable. Step 3 is gated on Open Question 1 and may be cross-repo.

### Step 1 — `발행됨` tab on `/drafts`

Add a third view tab (`published`) to `drafts.astro` + its client script, filtering `GET /api/posts?status=published`. Reuse the existing row renderer and action handlers; map the primary destructive action to `발행 취소` (archive) and keep `완전 삭제` (hard). `편집` already routes to `/write?id=`.

**Verification**:

```
# local: log in, publish a post, open /drafts → 발행됨 tab lists it; 편집 opens /write?id=; archive moves it to 보관함
pnpm lint && pnpm exec astro check
# prod smoke: GET /drafts renders the published tab; deployed JS chunk contains the new tab handler
```

**Rollback**: revert the PR; no data migration.

---

### Step 2 — author `편집` affordance on `/blog/[slug]`

In `myblog_front/src/pages/blog/[slug].astro`, render an author-only `편집` link (gated on `isLoggedIn()`, client-side) that points to `/write?id=<post-id>`. Post id is already available on the page (currently emitted as hidden data).

**Verification**:

```
pnpm lint && pnpm exec astro check
# local: logged in → 편집 link visible on a post page and opens the editor pre-loaded; logged out → link absent
# prod smoke: deployed [slug] chunk gates the link behind the auth check
```

**Rollback**: revert the PR.

---

### Step 3 — un-publish removes the static MDX, restore re-publishes it (backend-only)

Resolved per Q1 → **backend owns it**, and per the NEW symmetry decision → **archive↔restore stay symmetric**. Backend-only; **no contract change** (DELETE/restore signatures unchanged).

- Add `github_delete_file(owner, repo, branch, path, token)` to `publish_service.py` (GET sha → DELETE; **404 on the GET is an idempotent no-op** so deleting a never-published draft is safe).
- Add a `publish_post_from_row(db, post)` helper that re-derives every `publish_to_github` input from the `Post` row (title/slug/description/posted_date/body_mdx/album_cover_url/rating from columns; category/album_ids/artist_ids/recommended_track_ids from relations; `best_new`/`music_review` from the single subject album — same derivation as the publish route, extracted for reuse).
- Wire `DELETE /api/posts/{id}` (both `hard=true` and the soft archive) to compute `path = {CONTENT_DIR}/{posted_date}--{slug}/index.mdx` and call `github_delete_file` after the DB op. Capture slug+date **before** a hard delete removes the row.
- Wire `PATCH /api/posts/{id}/restore` to call `publish_post_from_row` after flipping status back to `published`.
- GitHub failures surface as `502` (mirrors the publish route) but never roll back the DB op — log + report; the file op is best-effort cleanup.

**Verification**:

```
pytest  # unit: github_delete_file builds the right path + idempotent 404; restore re-publish derivation
# local smoke (no GitHub creds): pytest + lint stand in; full path verified in prod smoke
# prod smoke: 발행 취소 a published post → /blog/<slug>/ 404s after rebuild + content file gone;
#             복구 it → file reappears, /blog/<slug>/ renders again after rebuild
```

**Rollback**: revert the PR; `복구`(restore) re-publishes, so no manual content-repo surgery needed for archived posts. Hard-deleted posts are unrecoverable by design (unchanged from today).

---

## Open questions

_All resolved 2026-06-01 — see Decisions log._

1. ~~Should un-publish/delete remove the MDX, and where does that logic live?~~ → **(a) backend owns it.** Decisive factor: `GITHUB_TOKEN` is a backend-only secret (Secrets Manager `myblog/backend`, `settings.GITHUB_TOKEN`); the frontend **physically cannot** delete the content file, so option (b) "frontend `unpublishFromGit`" would still require a new backend endpoint — no simplicity win. Backend already owns publish (ARCH-11) and has every input on the `Post` row (`posted_date` + `slug`) plus settings (`GITHUB_REPO_OWNER/NAME/BRANCH`, `CONTENT_DIR`). MDX removal becomes a side-effect of the existing `DELETE /api/posts/{id}` — **no contract change** (signature unchanged).
2. ~~Archive vs hard-delete default for a published post.~~ → **archive-as-default.** `발행됨` tab actions: `편집` / `발행 취소`(archive, soft) / `완전 삭제`(hard, secondary).
3. ~~Edit semantics: overwrite same slug or orphan?~~ → **overwrites; no orphan.** Verified: `PostService.update` never recomputes the slug (slugify runs only in `create`), and WriterApp re-publishes with the DB's stable `json.slug`. Path `{CONTENT_DIR}/{posted_date}--{slug}/index.mdx` is stable across a title edit. **Residual edge case (out of scope):** editing the *publish date* changes the path → orphans the old file (same class as Step 3); flagged for a future follow-up.

## Decisions log

| Date       | Decision                                                                                                                                                              | Step |
| ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---- |
| 2026-06-01 | Q1 → **backend** owns MDX removal (GitHub token is backend-only; frontend can't delete). Side-effect of `DELETE`; no contract change.                                 | 3    |
| 2026-06-01 | Q2 → **archive-as-default** for published posts (`발행 취소`=archive, `완전 삭제`=hard).                                                                                | 1    |
| 2026-06-01 | Q3 → re-publish **overwrites** same slug/path (slug immutable on update); no orphan. Publish-date-change orphan deferred.                                             | 2    |
| 2026-06-01 | **NEW** — archive↔restore must stay **symmetric**: `발행 취소`(archive) removes the MDX, so `복구`(restore) must **re-publish** it (else restore leaves a 404'd live post). Restore re-derives the MDX from the `Post` row (same `best_new`/`music_review` derivation as the publish route). Backend-only; expands Step 3. | 3    |
