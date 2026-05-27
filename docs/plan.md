# Plan

Active workspace tracker for cross-repo work. Each row carries `Scope / Order (if multi-repo) / Verification (local + prod smoke) / Rollback / Status`; RFC-backed entries collapse to a one-line pointer at `docs/rfcs/<id>-<slug>.md`. When a row finishes, drop it — `git log` and `docs/archive/done/YYYY-MM.md` are authoritative for history.

---

## Active

_(none — BUG-9 wrapped 2026-05-28 with backend #23 / front #25 / workspace #59. Prod smoke 20/20 + direct 409 round-trip verified.)_

---

## Backlog

_(empty — promote next item here when picking up a new cycle.)_
