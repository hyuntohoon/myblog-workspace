# ADR-0001: Multi-Repo Workspace Meta-Management Pattern

Date: 2026-05-20 (retroactive)
Status: Accepted

## Context

The myblog project consists of five independent services (`myblog_backend`, `myblog_front`, `myblog_music`, `myblog_publish`, `myblog_worker`), each in its own repository. Cross-repo changes — API contract updates, shared schema changes, infrastructure modifications — had no single coordination point. Without one, decisions, rationale, and in-flight work were scattered across individual repos or existed only in conversation.

## Decision

Introduce a dedicated workspace repository (`myblog-workspace`) that acts as the meta-management layer for all five service repos. It owns:

- `docs/architecture.md` — system-wide architecture, not duplicated in each repo
- `docs/plan.md` — cross-repo work plan; all multi-repo PRs are planned here first
- `docs/contracts/` — SQS message schemas and service-to-service API contracts
- `docs/conventions/` — shared coding and workflow standards
- `docs/decisions/` — architectural decision records (this directory)
- `CLAUDE.md` — workspace-level instructions for AI assistants

Each service repo retains its own `CLAUDE.md` for service-specific guidance.

## Consequences

**Easier:**
- Cross-repo changes have a single planning and review surface.
- Contract changes are written once in `docs/contracts/` before being propagated.
- AI assistants have a consistent entry point for project-wide context.
- Architectural decisions are recorded and findable.

**Harder:**
- Developers must check two places (workspace + service repo) when starting work.
- The workspace repo requires its own maintenance discipline.

**Constraints introduced:**
- Cross-repo work must not begin without a `docs/plan.md` entry.
- Service contracts must not change in a service repo without first updating `docs/contracts/`.
