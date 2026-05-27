# Git Workflow

## Branch Strategy — GitHub Flow + `develop`

This workspace uses a lightweight variant of **GitHub Flow** with an optional `develop` integration branch.

```
main        ← production; always deployable; protected
develop     ← integration target for cross-repo or multi-PR work (optional)
<type>/<id>-<desc>  ← short-lived feature/fix branches; branch off main (or develop for cross-repo work)
```

### When to branch off `main` (default)

- Single-repo changes (bug fixes, refactors, docs, single-service features)
- Anything that can be tested and reviewed independently

### When to use `develop`

- Changes that span two or more repos and need to be tested together before hitting production
- Example: a contract change in `myblog_music` and the corresponding consumer update in `myblog_worker` should both land on `develop` and be integration-tested before either merges to `main`

### Why not Git Flow?

Each service (Lambda) deploys independently on merge to `main`. There are no scheduled release cycles, so the overhead of `release/*` and `hotfix/*` branches is not justified. If a hotfix is needed, branch off `main` directly with `fix/<id>-<desc>`.

### Environment mapping

| Branch | Environment | Deployed by |
|--------|-------------|-------------|
| `main` | Production | GitHub Actions (on push) |
| `develop` | Staging / integration | GitHub Actions (on push, optional) |
| Feature branch | Local / PR preview only | — |

---

## Branch Naming

```
<type>/<plan-id>-<short-desc>
```

| Segment | Description |
|---------|-------------|
| `<type>` | Same types as commit: `fix`, `feat`, `chore`, `refactor`, `docs`, `test`, `ci`, `db` |
| `<plan-id>` | PR or issue ID from `docs/plan.md` (e.g. `PR-7`, `ARCH-1`) |
| `<short-desc>` | Kebab-case summary, 3–5 words |

**Examples**

```
fix/PR-7-worker-sqs-error-handling
feat/PR-4-candidates-auth
db/PR-6-tracks-unique-index
docs/DOC-2-per-repo-claude-md
refactor/PR-9-backend-config-dedup
```

---

## Commit Format — Conventional Commits

```
<type>(<scope>): <subject>

<body>          ← optional, wrap at 72 chars
```

### Types

| Type | When to use |
|------|-------------|
| `feat` | New user-visible feature |
| `fix` | Bug fix |
| `chore` | Maintenance with no behavior change (deps, tooling) |
| `refactor` | Code restructuring with no behavior change |
| `docs` | Documentation only |
| `test` | Adding or fixing tests |
| `ci` | CI/CD pipeline changes |
| `db` | Schema migrations or DB-only changes |

### Scope

Optional. Use the affected service or module name: `myblog_music`, `album_repo`, `sqs_client`, etc.

### Subject

- Lowercase, imperative mood: `fix import path`, not `Fixed import path`
- No trailing period
- 72 characters max

### Body

Optional. Explain *why*, not *what*. Reference plan IDs or ADRs when relevant.

**Examples**

```
fix(myblog_music): move inline import to module top

Inline `import time` inside a class body binds to the class namespace,
causing NameError at call time. Moved to module level per PR-1.
```

```
fix(myblog_worker): re-raise SQS exceptions to enable DLQ routing

Swallowing exceptions and returning True tells the Lambda runtime that
every record succeeded, preventing SQS retries and DLQ delivery.
```

```
chore(myblog_music): remove dead singleflight.py
feat(myblog_backend): add Cognito JWT validation middleware
db: add UNIQUE constraint on tracks.spotify_id
```

---

## AI Git Permissions

The AI may run `git add` and `git commit` directly.
The AI **must ask for explicit approval** before running `git push` or `git merge` — the human approves each push individually.

### AI Trailers

When a commit contains AI-generated or AI-assisted content, append a trailer after a blank line:

```
<type>(<scope>): <subject>

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
```

| Situation | Trailer |
|-----------|---------|
| AI wrote or substantially revised the change | `Co-Authored-By: Claude <model> <noreply@anthropic.com>` |
| Human wrote the change independently | *(no trailer)* |

If the human significantly rewrote AI output, omit the trailer.

---

## `main` Branch Protection Rules

- Direct commits to `main` are **prohibited**. All changes go through a branch and PR.
- Force-push to `main` is **never permitted**.
- Merging requires at least one approval (human or designated reviewer agent).
- CI must pass before merge (unit tests, lint).

---

## PR Flow

1. **Branch** — `git checkout -b <type>/<plan-id>-<desc>` from `main` (or `develop` for cross-repo work).
2. **Change** — make file edits (AI assists; human reviews).
3. **Test locally** — run service tests and verify the golden path before pushing.
4. **Commit** — human runs `git commit` with Conventional Commits format; add AI trailers when applicable.
5. **Push** — `git push -u origin <branch>`.
6. **Open PR** — `gh pr create` targeting `main` (or `develop`); fill in summary and test plan.
7. **Review** — run `/code-review`; address all findings before merge.
8. **Squash merge** — squash into the target branch; the squash commit title must follow Conventional Commits format.
9. **Delete branch** — `git push origin --delete <branch>`.
10. **Update plan** — mark the corresponding entry in `docs/plan.md` as `✅ Done (date, SHA: <7-char>)`.

### `/code-review` — automated PR review

Run after opening a PR:

```
/code-review
```

What it does:
- Launches 4 agents in parallel: CLAUDE.md compliance (×2), bug detection, git blame context analysis
- Scores each issue 0–100 for confidence; filters out anything below 80
- Posts a GitHub PR comment with only high-confidence, actionable issues

Use `/security-review` in addition for PRs that touch auth, secrets, or input handling (PR-8, PR-4, etc.).

---

### `gh pr create` template

```bash
gh pr create \
  --title "<type>(<scope>): <subject>" \
  --body "$(cat <<'EOF'
## Summary
-

## Test plan
- [ ]

## Related
docs/plan.md <PR-ID>

🤖 Generated with Claude Code
EOF
)"
```

---

## Cross-Repo PR Sequencing

When a change spans multiple repos (e.g. a new SQS message field in `myblog_music` consumed by `myblog_worker`):

1. Write or update the contract first: `docs/contracts/<contract-file>.md`.
2. Open PRs in dependency order — producer repo first, consumer repo second.
3. Both PRs target `develop` (not `main`) so they can be integration-tested together.
4. After integration test passes on `develop`, open a final PR from `develop` → `main` per repo.
5. Record the sequence and rollback approach in `docs/plan.md` before starting.

---

## Hotfix

```
git checkout -b fix/<id>-<desc> main
# make the fix
git push -u origin fix/<id>-<desc>
gh pr create --title "fix(<scope>): <subject>" ...
# fast-track review; squash merge to main
```

Hotfixes always branch from `main`, not `develop`, and merge directly to `main`.
