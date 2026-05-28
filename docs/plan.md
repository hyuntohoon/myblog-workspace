# Plan

Active workspace tracker for cross-repo work. Each row carries `Scope / Order (if multi-repo) / Verification (local + prod smoke) / Rollback / Status`; RFC-backed entries collapse to a one-line pointer at `docs/rfcs/<id>-<slug>.md`. When a row finishes, drop it — `git log` and `docs/archive/done/YYYY-MM.md` are authoritative for history.

---

## Active

### BUG-12: Writer page filter buttons — instant client-side apply

- **Scope**: `myblog_front` only (SubjectBlock).
- **Verification**: pre-merge `pnpm lint` + `pnpm exec astro check` + 로컬 dev server 매트릭스 클릭; post-merge prod smoke + prod 1회 확인.
- **Rollback**: 단일 PR revert.
- **Status**: draft — BUG-11 회귀 (필터 버튼이 setFilter 만 호출, 재검색/재필터 없음). 클라이언트 필터링으로 즉시 반응.
- **RFC**: [docs/rfcs/BUG-12-writer-filter-instant-apply.md](rfcs/BUG-12-writer-filter-instant-apply.md)

---

## Backlog

_(none)_
