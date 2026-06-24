# Architectural Decision Records (ADRs)

This directory records significant architectural and workflow decisions made in the myblog project. Each file captures *what* was decided, *why*, and *what the consequences are*.

## Format

Each ADR is a Markdown file named `NNNN-short-title.md` and contains:

```markdown
# ADR-NNNN: Title

Date: YYYY-MM-DD
Status: Proposed | Accepted | Deprecated | Superseded by ADR-NNNN

## Context
Why this decision was needed. What problem or constraint drove it.

## Decision
What was decided. State it clearly and directly.

## Consequences
What becomes easier, harder, or different as a result.
```

## Status Values

| Status | Meaning |
|--------|---------|
| `Proposed` | Under discussion, not yet committed |
| `Accepted` | In effect |
| `Deprecated` | No longer relevant; kept for history |
| `Superseded by ADR-NNNN` | Replaced by a newer decision |
| `Paused` | Deferred pending further information |

## Index

| ADR | Title | Status |
|-----|-------|--------|
| [0001](0001-multi-repo-workspace.md) | Multi-Repo Workspace Meta-Management Pattern | Accepted |
| [0002](0002-paused-pr5-pr6.md) | PR-5, PR-6 보류 | Paused |
| [0003](0003-schema-canonical.md) | Single Canonical Database Schema | Accepted |
| [0004](0004-spotify-client-duplication.md) | Accept Spotify Client Duplication | Accepted |
| [0005](0005-shared-db-package.md) | Shared DB Models Package | Accepted |
| [0006](0006-publish-absorbed-into-backend.md) | Absorb `myblog_publish` into `myblog_backend` | Accepted |
| [0007](0007-contract-first-openapi.md) | Contract-first workflow with strict OpenAPI enforcement | Accepted |
