# Workflow Review — 2026-05-28

Cold audit of the current Claude Code setup: workspace docs, agents, hooks, skills, plugins, and the day-to-day flow. Focus is on **what is wired up vs. what the rules promise**, and where the gap costs time or correctness.

## TL;DR

- Setup is mature: hooks enforce 3 hard rules, agents are model-tiered (haiku/sonnet/opus), plan.md / RFC split is clean, post-#52 CLAUDE.md is genuinely lean.
- Three concrete inconsistencies were just fixed in this branch: layout missing `myblog_shared_db`, architect agent listed archived `myblog_publish`, reviewer agent pointed at deleted per-repo CLAUDE.md.
- **Top gaps**: (1) RFC status drift — two `accepted` RFCs with no plan.md anchor; (2) hooks cover 3/9 hard rules — three more are cheap wins; (3) `settings.local.json` allow-list is 120+ entries with `myblog_publish` cruft and a `Bash(git *)` wildcard that supersedes most of it; (4) prod smoke is honor-system with no nudge.
- Overall: tighten enforcement of rules that already exist, don't add new rules.

---

## 1. What is currently wired

### 1.1 Agents (`.claude/agents/`)

| Agent | Model | Tools | When to use |
|---|---|---|---|
| `explorer` | haiku | Read/Grep/Glob | 3+ file mapping, returns ≤40-line summary |
| `planner` | sonnet | Read/Grep/Glob/Write | turn requirements/review into `docs/plan.md` |
| `reviewer` | sonnet | Read/Grep/Glob/Bash | post-implementation check before push |
| `test-engineer` | sonnet | Read/Grep/Glob/Bash/Edit/Write | pytest authoring + flake hardening |
| `debugger` | opus | Read/Grep/Glob/Bash | root-cause after 2 failed fixes |
| `architect` | opus | Read/Grep/Glob/Write | structural review, writes `docs/architecture-review.md` |

Model tiering is sensible — read-mostly mapping on haiku, code-changing test work on sonnet, deep reasoning on opus.

### 1.2 Hooks (`.claude/hooks/` via `settings.local.json`)

| Hook | Event | Enforces |
|---|---|---|
| `block-main-commit.sh` | PreToolUse(Bash) | Hard rule #1 — no commits on main/master |
| `block-secret-files.sh` | PreToolUse(Write/Edit) | Hard rule #2 — deny writes to `.env*`, `*.pem`, `*.key`, `credentials*`, `secrets.y*ml`, `config.local.json` |
| `guard-force-push.sh` | PreToolUse(Bash) | Hard rule #7 (partial) — deny force-push to main/master; warn elsewhere |

User-level (`~/.claude/settings.json`):
- `Stop` hook → macOS notification when Claude finishes a turn.

### 1.3 Skills and plugins

User has enabled four plugins: `code-review`, `frontend-design`, `pyright-lsp`, `security-guidance`. Workspace `CLAUDE.md` cites the `frontend-design` skill explicitly in the subagent triggers table.

### 1.4 Memory (`~/.claude/projects/.../memory/`)

Four feedback memories, two project memories. They mirror CLAUDE.md hard rules and the roadmap decision. No drift detected against current code.

---

## 2. Inconsistencies fixed in this branch

| Where | Was | Now |
|---|---|---|
| `CLAUDE.md` Layout | omitted `myblog_shared_db/` | added (git-pinned models package, ARCH-6) |
| `.claude/agents/architect.md` | "5 repos: ..., myblog_publish" | "4 service repos + shared_db; publish absorbed (ARCH-11)" |
| `.claude/agents/reviewer.md` | "repo's `CLAUDE.md`" | "workspace `CLAUDE.md` — per-repo doc no longer exists" + conventions inlined |

---

## 3. Outstanding issues (not fixed — judgment call required)

### 3.1 RFC ↔ plan.md status drift — RESOLVED

**Initial diagnosis was wrong.** First read said ARCH-6 and ARCH-12 were `accepted` with no plan.md row. The truth is worse but simpler:

| RFC | Real file Status | Real location | Index claimed |
|---|---|---|---|
| ARCH-6 | done | `docs/archive/done/rfcs/` | accepted |
| ARCH-11 | done | `docs/archive/done/rfcs/` | done (→ wrong path `docs/done/rfcs/`) |
| ARCH-12 | done | `docs/archive/done/rfcs/` | accepted |

All three RFCs are complete, all three have matching ADRs (0005 / 0006 / 0007). `docs/rfcs/README.md` Index was simply never updated — and two body paragraphs also pointed to a non-existent `docs/done/rfcs/`.

**Fix applied in this branch:**
- Index now lists in-flight RFCs only (currently `_(none)_`) with a one-line breadcrumb to the archived three.
- Two body references to `docs/done/rfcs/` corrected to `docs/archive/done/rfcs/`.

**Process implication:** the rule *"RFC Status must match plan.md row"* was not the broken link — the README Index was a third state nobody was syncing. Going forward there are now only two places to keep aligned (RFC file's `Status:` line + plan.md), and the Index serves as a breadcrumb register, not as a source of truth.

### 3.2 Hooks cover 3 of 9 hard rules — 3 more are cheap

| Hard rule | Currently enforced by hook? | Suggested |
|---|---|---|
| #1 no main commit | ✅ |  |
| #2 no secrets in repo files | ✅ (filename match) |  |
| #3 no rollback migrations on prod | ❌ | low priority — destructive command lives outside Claude's typical shell |
| #4 ≤1 RFC step / session | ❌ | hard to enforce mechanically — leave to convention |
| #5 no self-promoting RFC status | ❌ | Edit hook on `docs/rfcs/*.md` that denies `Status:` line edits to `accepted`. **Cheap and high-value.** |
| #6 no `terraform apply -target=...` | ❌ | PreToolUse(Bash) hook denying that exact pattern. **Trivial.** |
| #7 no push/merge without "ok push" | ⚠️ partial (force-push only) | the spirit is "never push without confirmation"; could deny `git push` outright until session-scoped approval flag is set. Heavier — likely overkill. |
| #8 no `--no-verify` / `--no-gpg-sign` | ❌ | PreToolUse(Bash) deny on those flags. **Trivial.** |
| #9 no sync Spotify on user-facing endpoint | ❌ | static — needs a script, not a hook. Could be a reviewer-agent check (already implied). |

Recommended next: add hooks for #5, #6, #8. All three are ~15-line bash scripts mirroring the existing ones.

### 3.3 `settings.local.json` allow-list bloat

120+ entries, mostly accreted from debugging sessions. Issues:

- **`Bash(git *)` wildcard** (line ~12) supersedes ~12 specific `git -C ...` entries above it — they can all be deleted.
- **`myblog_publish` references** (gh run / workflow lookups) — the repo is archived. Dead entries.
- **One-off bash incantations** like the `awk '/aws_lambda_event_source_mapping.worker_sqs ...` patterns from a specific tfplan inspection. These will never match again.
- **`tar -xOf -` / `gunzip` cache paths** from a `frontend-design` plugin download — single-use.
- **Duplicates**: `pytest tests/test_handler.py -v` and `pytest tests/test_handler.py -v -p no:allure` could collapse to `pytest *`.

Recommended action: run the `/fewer-permission-prompts` skill on a fresh transcript, or hand-prune. Target shape: ~25–35 entries, with broad wildcards for tooling families (`git *`, `gh *`, `pytest *`, `terraform *`, `aws * *`) and the small set of specific reads/writes that fall outside those families.

### 3.4 Prod smoke is unenforced

DoD says: *"Never claim 'done' before the post-merge items are green."* But nothing nudges the model to run `scripts/smoke.sh prod` after a merge. Options:

- **(a)** Add a SessionStart hook that lists recently-merged PRs missing a "prod smoke ✅" comment and surfaces them. Heavy.
- **(b)** Convention only — leave it to the feedback memory (`prod-smoke-required` already exists). Lighter, currently in use.
- **(c)** A scheduled routine (`/schedule`) that runs smoke every N hours and posts result to the most recent merged PR. Most robust but adds infra.

Default to (b); revisit if a prod-affecting PR ever gets marked done without a smoke quote.

### 3.5 Skill vs. agent overlap

Both `reviewer` agent and `code-review` skill exist. They overlap. The `code-review` plugin is a generic Anthropic skill; the local `reviewer` agent is myblog-specific (knows about sync Spotify rule, SQS contract). The CLAUDE.md table only mentions the agent — fine, but worth a one-line note about which to invoke for what.

Suggested phrasing in CLAUDE.md:
> *Use the local `reviewer` subagent for myblog-specific contract / boundary checks. The `code-review` skill is for generic correctness review and runs separately.*

### 3.6 Subagent triggers table mixes agents and skills without flagging

The table lists `frontend-design skill` in the last row but no other skill. Either:
- Add the `code-review` skill / `security-review` skill / `simplify` skill explicitly (they are user-invokable today),
- Or move skills out of the agent table into a separate "Skills" row.

The current format gives the impression skills only matter for frontend work — they do not.

---

## 4. Workflow shape — observations

### 4.1 What works well

- **Branch-name plan-id linkage** (`feat/PR-12-...`) makes `git log` self-narrating. Plan-id-optional escape valve for `docs/`/`chore/` is the right exception.
- **Pre-merge vs. post-merge DoD split** is the single best thing in this CLAUDE.md. It prevents the most common AI failure mode of declaring success before deploy.
- **plan.md kept tiny** (currently 1 backlog row) — the discipline of dropping rows post-merge has held since #52.
- **RFC ↔ plan.md pointer pattern** keeps long-form migration docs out of the small, hot plan.

### 4.2 Friction points

- **"Substantial PR" threshold for reviewer agent is undefined.** A diff-size or files-changed heuristic would remove ambiguity (e.g., "≥3 files changed in a service repo, or any contract/infra touch").
- **Cross-repo order** is described in prose (*"update `docs/plan.md` before code"*) but not encoded. For 2-repo PRs this is fine; for 3+ a small RFC-style sequence is safer than freehand planning.
- **`debugger` agent is opus** — correct for hard bugs, but the 15-minute gate is vague. Consider rephrasing as "after 2 failed fix attempts" (which is also how the agent description itself frames it). The two phrasings already disagree subtly.
- **No agent for ops/deploy verification.** After merge, prod smoke is human-driven. If smoke ever grows past `smoke.sh prod`, a dedicated agent could compress the loop. Not urgent.

### 4.3 Things the current setup does **not** need

- A per-repo CLAUDE.md (removed in #52 — correct).
- A separate "release" doc — `git log` carries it.
- More agents. Six is already at the upper edge of what gets routinely used; adding more dilutes the trigger table.

---

## 5. Recommended next actions

Ordered by leverage / effort ratio.

1. ~~**Reconcile RFC status** (§3.1)~~ — done in this branch.
2. **Add hooks for hard rules #5, #6, #8** (§3.2). ~30 min total, all in `.claude/hooks/`.
3. **Prune `settings.local.json`** (§3.3). Run `/fewer-permission-prompts` skill, then manually drop `myblog_publish` and one-off entries. ~15 min.
4. **Clarify reviewer vs. code-review** in CLAUDE.md (§3.5). One sentence. ~2 min.
5. **Tighten subagent trigger thresholds** (§4.2). "Substantial PR" → concrete heuristic. ~2 min.

Nothing here is blocking. The system runs; these are polish.

---

## 6. References

- `CLAUDE.md` — workspace conventions (~100 lines, post-#52 lean)
- `docs/plan.md` — active cross-repo tracker
- `docs/rfcs/README.md` — RFC vs. ADR lifecycle, status rules
- `infra/README.md` — AWS identifiers
- `~/.claude/projects/.../memory/MEMORY.md` — feedback / project memory index
- `.claude/agents/*.md` — agent definitions
- `.claude/hooks/*.sh` — current PreToolUse enforcement scripts
