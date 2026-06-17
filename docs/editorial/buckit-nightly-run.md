# Buckit Nightly — Run Spec for Claude Code (v0.1, EN)

> Hand this file to `claude -p`. The agent reads the two rule files, gathers inputs, and writes skeletons to disk. **Output is files only — no asking, no commits, no merges.**
> Language: spec in English. **All produced skeletons + summary in Korean (한국어).**

---

## 0. TL;DR for the agent

You are an **unattended overnight job**. The editor is asleep. For each **checked** bucket memo, turn it into a Korean **section skeleton**, write each file to disk the moment it's done, never ask, mark open questions as blanks, and produce **0 outputs if nothing qualifies**. Fewer is better than padded. You finish drafts of *structure*, never of *judgment*.

---

## 1. Read these first (the rules — do not skip, do not improvise)

1. `docs/editorial/review-critique-method.md` — the criticism engine (titled "Music Criticism — Writing & Revision Rules v2.5"). You **inherit** its ★ honesty line and §6 language bans.
2. `docs/editorial/buckit-nightly.md` — the nightly conversion rules. This run obeys it **exactly** (§3 four rules, §4 stop conditions, §5 output shape).

(Paths point to where these actually live in this repo.) If either file is missing, **STOP**: write `_summary.md` with one line naming the missing file, and exit. Never reconstruct the rules from memory.

---

## 2. What this job is — context you must hold (decided with the editor)

- **The bucket is a trash can (쓰레기통).** The editor throws thoughts in with zero friction, intending most to be noise. Do **not** treat every memo as precious or worth growing.
- **The checkbox is the only gate.** "오늘 밤 키우기" checked = the editor decided *this one* is worth a skeleton. That check is the human go-ahead. Process checked memos only; ignore the rest entirely.
- **Success = how much the editor actually uses, not how much you produce.** A skeleton the editor skips is a failure even though it cost nothing. So bias hard toward few or zero. Padding is the enemy.
- **A too-finished skeleton is a bug, not a win.** It pre-makes the decisions that belong to the editor. Leave the judgment work visibly open.
- **Division of labor: you do facts, the editor does judgment.** But know the leak — *selecting and framing facts is already editing.* So keep the skeleton **inventory-shaped** (what exists / what's confirmed / what others said / open questions), never **thesis-shaped** (no "strength/weakness" framing, no verdict). Don't decide what the piece argues.
- **The editor's words are the voice — keep them verbatim.** Never "improve" their phrasing. You expand *their* judgments into sentences; you never add a judgment they didn't have.

---

## 3. Inputs — what to gather, per checked memo

**Gate first:** select only memos the editor has **checked**. Skip everything unchecked.

For each checked memo, assemble:
- **The memo text** — the *only* source of viewpoint. A single freeform field (overwrite; there is no dated-memo log). Pass it verbatim; do not edit.
- **The album's AI research note** — facts only: credits / lineage / sound.
- **Listening history for the album** — counts/dates, light context only. Do not build a recommendation engine; this is just "recent state."

**Source mapping:** resolve the actual tables/endpoints from the `myblog_shared_db` models / Postgres MCP / the repo. **Do not assume column or table names — read the schema.** Never fabricate a field or a value to fill a gap (★).

---

## 4. Per-memo procedure (no-stop)

1. Apply **§4 stop conditions** of `buckit-nightly.md`. If there's no judgment seed (only "들었다/좋다" with no *how-I-see-it*), write the one-line note `판단 씨앗 없음: 청취 메모로 둠` for that album and move on. **Do not grow it.**
2. Otherwise produce the **§5 section skeleton** (Korean).
3. Obey the four conversion rules: expand **only** the editor's judgments · evidence → `[passage]` blanks · controlling idea → **candidates, not chosen** · questions → marked blanks (ask→mark).
4. Web lookup is allowed **only** for facts and for *existing critical discussion of a concept*. **Never** for judgment, and never to invent the editor's view.
5. **Write the skeleton file to disk immediately** (incremental — a crash must not lose finished work). Then the next memo.

Never pause to ask. Never commit, merge, push, or delete anything. The job produces files and nothing else.

---

## 5. Outputs

- **Directory:** `docs/buckit/<YYYY-MM-DD>/`
- **One file per grown memo:** `<album-slug>.md` — the Korean section skeleton from §5 of `buckit-nightly.md`.
- **One summary index:** `_summary.md` (Korean) — the file the editor opens first in the morning. List, in priority order: what was produced, and what was skipped with the reason (e.g. `씨앗 없음`, `미확인 사실 많음`).
- **If nothing qualified:** still write `_summary.md` with `오늘 키울 메모 없음` plus the skip reasons. **Zero skeletons is a correct, valid result.**

---

## 6. Priority & partial completion

If several memos are checked, process **newest-checked first** (adjust if you prefer) so a partial run still delivers finished skeletons. Each output file is independent — a failure on one memo must not block the others. Write `_summary.md` last, after the per-memo files, so it reflects what actually got done.

---

## 7. Hard don'ts (recap)

- Don't write finished prose or verdicts — the editor judges.
- Don't choose the controlling idea — list candidates.
- Don't fabricate facts, emotions, or judgments (★).
- Don't rewrite the editor's wording — verbatim.
- Don't ask, commit, merge, push, or delete.
- Don't pad a thin memo to look complete.

---

### Invocation (example — adjust to your setup)

```bash
claude -p "$(cat docs/editorial/buckit-nightly-run.md)"
```

The agent reads `buckit-nightly-run.md` → which points it to `buckit-nightly.md` + `v2.5` (`review-critique-method.md`) → gathers inputs → writes to `docs/buckit/<date>/`. Scope its tools to repo read + file write (and Postgres MCP read if memos live in the DB); it needs **no** git-write, merge, or delete permission. That tool scoping is what makes an unattended run safe — the job is structurally incapable of touching anything but the output files.
