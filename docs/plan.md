# Plan

Active workspace tracker for cross-repo work. Each row carries `Scope / Order (if multi-repo) / Verification (local + prod smoke) / Rollback / Status`; RFC-backed entries collapse to a one-line pointer at `docs/rfcs/<id>-<slug>.md`. When a row finishes, drop it — `git log` and `docs/archive/done/YYYY-MM.md` are authoritative for history.

---

## Active

_(none — the 2026-05-27 stabilization cycle wrapped with PRs #46–#52. Pick up from Backlog when starting next cycle.)_

---

## Backlog

### BUG-9: Duplicate publish silently creates `-2` slug suffix

- Scope: `myblog_front` (publish flow); may need backend slug-generation change
- Repro: publish a draft titled "X" → slug `x`; publish another draft titled "X" → slug `x-2` with no warning. User loses track of which slug is canonical.
- Acceptance: warn before publishing a duplicate title, or surface the appended suffix in the UI before commit
- Priority: low — no data loss, pure UX. Promote to Active when next feature cycle starts.
