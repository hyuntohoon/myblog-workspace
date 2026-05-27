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

### 3.2 Hook coverage — UPDATED

Three more hooks added in `chore/hard-rule-hooks`. Current state: **6 of 9 hard rules auto-enforced** (was 3).

| Hard rule | Hook | Script |
|---|---|---|
| #1 no main commit | ✅ | `block-main-commit.sh` |
| #2 no secrets in repo files | ✅ | `block-secret-files.sh` |
| #3 no rollback migrations on prod | ❌ | low priority — destructive command lives outside Claude's typical shell |
| #4 ≤1 RFC step / session | ❌ | hard to enforce mechanically — leave to convention |
| #5 no self-promoting RFC status | ✅ | `block-rfc-self-promote.sh` (denies Edit/Write that introduces `Status: accepted/in-progress` to `docs/rfcs/*.md`; README/TEMPLATE exempt) |
| #6 no `terraform apply -target=...` | ✅ | `block-terraform-target.sh` |
| #7 no push/merge without "ok push" | ⚠️ partial | `guard-force-push.sh` covers force-push only. Full enforcement would need a session-scoped approval flag — likely overkill. |
| #8 no `--no-verify` / `--no-gpg-sign` | ✅ | `block-skip-hooks-flag.sh` |
| #9 no sync Spotify on user-facing endpoint | ❌ | static check, needs a grep-style review script — reviewer agent already implies it |

All three new hooks were validated with synthetic STDIN payloads (deny + pass paths). `.claude/hooks/` is gitignored, so the scripts live locally; `CLAUDE.md` now annotates each rule with 🔒 when a hook backs it.

### 3.3 `settings.local.json` allow-list bloat — RESOLVED

Hand-pruned in `chore/prune-settings-local`. **136 → 28 entries** (79% reduction). A backup of the original (`settings.local.json.bak.2026-05-28`) sits next to the file in case anything breaks.

What was dropped:
- All `git -C /path/...` and `git -C /path checkout ...` entries — superseded by `Bash(git *)`.
- All `myblog_publish` references (archived repo) — dead.
- One-off `awk '/aws_lambda_event_source_mapping.../'` tfplan patterns from a specific debug session — single-use.
- `tar -xOf -` / `gunzip /Users/.../webfetch-cache.bin` paths from a single `frontend-design` plugin download — single-use.
- Specific `pytest tests/test_handler.py -v ...` and `pytest tests/test_unit.py -v` variants — folded into `Bash(pytest *)`.
- `aws SERVICE *` granularity (14 entries) — folded into `Bash(aws *)` since the user already had broad AWS access in practice.
- `pip cache *`, `pip show *`, `pip3 show *`, `pip install *` — folded into `Bash(pip *)` / `Bash(pip3 *)`.
- One-off `DATABASE_URL=... python3 -c '...'` debug strings (4 variants), `curl -s -o ... <specific-url>` (4 variants superseded by `curl *`), `mkdir -p /tmp/...`, `cp <bundle>`, `chmod +x <specific-script>`, `zip -q placeholder.zip`, `xxd`, `wait`, `jobs -l`, `xargs cat`, etc.

What was kept (28 entries): broad wildcards for the tooling families actually used — `git *`, `gh *`, `python(3) *`, `pip(3) *`, `pytest *`, `npx/npm/pnpm *`, `nvm use *`, `aws *`, `terraform *`, `sam validate *`, `psql *`, `brew *`, `curl *`, `claude *`; both Skills currently used; two WebFetch domains; six Read paths.

The hooks block (Write|Edit and Bash PreToolUse hooks for hard rules #1/#2/#5/#6/#7-partial/#8) was preserved unchanged.

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

1. ~~**Reconcile RFC status** (§3.1)~~ — done.
2. ~~**Add hooks for hard rules #5, #6, #8** (§3.2)~~ — done.
3. ~~**Prune `settings.local.json`** (§3.3)~~ — done (136 → 28 entries).
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
