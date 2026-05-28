# Plan

Active workspace tracker for cross-repo work. Each row carries `Scope / Order (if multi-repo) / Verification (local + prod smoke) / Rollback / Status`; RFC-backed entries collapse to a one-line pointer at `docs/rfcs/<id>-<slug>.md`. When a row finishes, drop it — `git log` and `docs/archive/done/YYYY-MM.md` are authoritative for history.

---

## Active

### BUG-11: Writer page music search filter — album/track/artist 동작 불일치

- **Scope**: `myblog_front` only (SubjectBlock + types). 백엔드/계약/인프라 변경 없음.
- **Verification**: pre-merge `pnpm lint` + `pnpm exec astro check`; post-merge prod smoke (4 필터 × 2 버튼 매트릭스 + 트랙 클릭 라우팅).
- **Rollback**: 단일 PR revert.
- **Status**: draft — RFC 작성 완료, 구현 대기.
- **RFC**: [docs/rfcs/BUG-11-write-page-search-filter.md](rfcs/BUG-11-write-page-search-filter.md)

---

## Backlog

_(none)_
