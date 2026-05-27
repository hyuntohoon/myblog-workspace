# Plan

Active workspace tracker for cross-repo work. Each row carries `Scope / Order (if multi-repo) / Verification (local + prod smoke) / Rollback / Status`; RFC-backed entries collapse to a one-line pointer at `docs/rfcs/<id>-<slug>.md`. When a row finishes, drop it — `git log` and `docs/archive/done/YYYY-MM.md` are authoritative for history.

---

## Active

### BUG-9: Duplicate publish silently creates `-2` slug suffix

- Scope: `myblog_backend` (slug uniqueness enforcement), `myblog_front` (publish/draft flow), workspace (openapi regen)
- Decision: **hard block** on duplicate — backend returns 409 instead of auto-appending suffix. Applied to both draft save and publish (consistency: catch conflict early).
- Sub-fix discovered: `WriterApp.onPublish` always calls `savePost` (POST = new row) even when `dbPostId` exists, so draft→publish currently creates 2 rows. Switching to `updatePost` when `dbPostId` is set.
- Order: backend (409 + service exception) → frontend (updatePost on publish + 409 toast) → workspace openapi regen
- Verification: backend pytest 409 case + frontend lint/astro check + local smoke; prod smoke post-merge
- Rollback: revert `fix/BUG-9-publish-duplicate-slug-warning` branch (single PR per repo)
- Status: in-progress (branch: `fix/BUG-9-publish-duplicate-slug-warning`)

---

## Backlog

_(empty — promote next item here when picking up a new cycle.)_
