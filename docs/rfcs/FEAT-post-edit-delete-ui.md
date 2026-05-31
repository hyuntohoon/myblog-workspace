# FEAT-post-edit-delete-ui: Author-facing edit / delete for published posts

- **Status**: draft
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
- Publish flow (`:264-305`): when `dbPostId` is set it calls `updatePost(dbPostId, {status:'published'})` **then `publishToGit`** (re-writes the MDX). So editing a published post and re-publishing already works — *if* the user can reach the editor with `?id=`.

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

### Step 3 — un-publish removes the static MDX (gated on Q1)

Make "delete/unpublish a published post" also remove the published MDX so the static page disappears. Exact shape depends on Q1: either (a) extend the backend delete/archive path to delete the GitHub content file via the existing publish/GitHub client (cross-repo: backend + contract), or (b) add a frontend `unpublishFromGit` call mirroring `publishToGit`. Whichever, the static site must rebuild without the page.

**Verification**:
```
# delete a published post → its /blog/<slug>/ returns 404 after rebuild; content file gone from the repo
```

**Rollback**: restore the content file + `PATCH /restore`; non-trivial because it spans DB + content repo — document the manual restore in the PR.

---

## Open questions

1. **Should un-publish/delete remove the MDX, and where does that logic live?** — `PostService.delete` is DB-only today. Options: (a) backend owns it (delete the content file in the same path the publish flow writes, ARCH-11 absorbed publish into backend) — cleanest, single source of truth, but cross-repo (backend + contract); (b) frontend issues a separate `unpublishFromGit` after the DELETE — simpler, but splits the publish/unpublish logic across tiers. **Blocks Step 3.** Recommendation: (a).
2. **Archive vs hard-delete as the default destructive action for a published post.** Archive (recoverable, unpublish MDX, keep DB row) is safer and matches the existing `보관함` model; hard-delete stays an explicit secondary action. **Blocks Step 1 wording.** Recommendation: archive-as-default.
3. **Edit semantics: does re-publishing an edited post overwrite the same slug/MDX, or create a new file?** WriterApp's update path keeps the same `dbPostId`; confirm the publish flow overwrites the existing slug's MDX rather than orphaning the old file on a title/slug change. **Blocks Step 2 acceptance** (a slug change on edit could strand the old static page — same class of problem as Step 3).

## Decisions log

| Date | Decision | Step |
|------|----------|------|
| | | |
