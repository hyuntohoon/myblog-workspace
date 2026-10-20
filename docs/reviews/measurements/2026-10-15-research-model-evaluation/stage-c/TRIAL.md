# Stage C — owner-use trial (light), predeclared

- Parent: `docs/rfcs/CHORE-research-model-evaluation.md` §C. Predecessor: `../stage-b/round7/RESULTS.md`.
- Date: 2026-10-20. Prepared by the orchestrating session (`claude-opus-5-5`). It was reviewed read-only by a Fable subagent before the owner saw it. The review made 13 findings, none a blocker; each was checked against the files.
  - Applied: "caught" counted from the owner's pre-check form; the order of events enforced by tooling; an owner "relied-on" field for centrality, with the owner's final word on disputed items; the quote rule scoped to central claims; a new check-packet builder and brief, hashed before generation; a two-album redaction tool; honest wording on the reserved albums; a defined task endpoint; the RFC Decisions-log entry.
  - Also applied: the deviation from acceptance-v1 §3 stated, with a raw count beside the verdict; the same-model reviewer listed as a limit; an exposure-check script; owner time stated without listening; the "usual research time" estimate dropped.
  - Not taken: dropping the harness-failure rerun. A harness failure says nothing about the prompt.
- **Owner confirmed this design in chat on 2026-10-20 ("이대로 확정"), before any Stage C dispatch.**

## 0. Owner decisions (2026-10-20, in chat)

1. Stop single-album development rounds. The returns had become small, and round 7 was stopped before review.
2. Move to Stage C with a **lighter procedure**: **2 albums** (option "더 가볍게: 2개만"). The owner accepted that this gives thinner evidence.
3. Candidate: **P6**.

## 1. What this trial is, and what it is not

It answers one question: **on albums it has never seen, does a P6 note help the owner in a real rating task, without a critical error slipping past the owner?**

It is not the acceptance-v1 confirmation in `../criteria/round-manifest-v1.md`. That design needs:
- 30–60 owner hours and 32 producer calls;
- two environments, one of them the Codex lane, discontinued 2026-10-19;
- two calibration albums;
- the §6 scoring manual and the §7 floors.

This trial uses none of them.
- `acceptance-v1`, the anchors and `round-manifest-v1` stay frozen as records. They are not amended, and no result here is reported as an acceptance-v1 pass or fail.
- The RFC goal's endpoint ("a candidate passes those criteria on development and held-out albums") therefore cannot be claimed from this trial. The RFC records the owner's replacement of the Stage C gate (§8).
- Two confirmation albums stay untouched: Detour (Rare N' Deluxe) and FREE THE MANE 4. This trial uses one album from each round-manifest-v1 block, which breaks both allocation pairs. acceptance-v1 §7 needs four untouched albums. **A later full confirmation would need two new albums and a new allocation draw.**

## 2. Albums

From the round-manifest-v1 confirmation set, one per block. Both are post-cutoff for `claude-opus-5-5`.

| Slug | Album | Artist | Release | Tracks | `albums.id` | Spotify | Why |
|---|---|---|---|---:|---|---|---|
| `habibti` | HABIBTI (FOMO) | Drake | 2026-10-02 | 15 | `eb1817f0-2468-4e14-9926-a3af404b6547` | `4gvyJRNQPBb1kOWqwZjUYI` | English; credit/sample complexity |
| `jdl` | 안개 속의 JDL | JDL | 2026-10-03 | 13 | `7eb56967-085e-4b55-9427-db7dc0ebc2eb` | `6ehP9HPujnWINh6wqzwcjR` | Korean primary sources; sparse documentation; the owner's own pick (round-manifest-v1 §2) |

**Exposure guard.** `exposure_check.sh` counts `album_research` rows for all four confirmation albums in a read-only transaction. Each run writes its SQL and output to `exposure/<UTC>.txt`. The first run (`exposure/20261020T111401Z.txt`) found 0 rows for all four. It runs again right before generation and before each owner task. Until the owner has done both tasks:
- the owner does not add either album to the `research_mode='all'` bucket, which would auto-queue a production v2 note;
- the owner does not request research for either album;
- the owner does not read any other note on them.

## 3. Producer

- Prompt: `prompts/P6.md`, a byte copy of `../stage-b/round6/prompts/P6.md` (`ac7c63023f66ffcd2dbadda6fe4509f9651037e4aea8a084cb7630f40f26af74`).
- Claude CLI only: `claude-opus-5-5`, medium effort, WebSearch + WebFetch, `--safe-mode`. The CLI version is recorded at dispatch (2.1.304 on 2026-10-20).
- **Inputs.** `prepare.py` writes them at dispatch:
  - each album's shared input is rendered read-only from prod by `../stage-b/round1/render_inputs.py`, which uses the poller's own block renderers with `conn.read_only = True`;
  - the common run block is round 1's, with `조사 기준일` set to the dispatch date;
  - one manifest per album pins the combined prompt hash, which the runner enforces;
  - `inputs-record.json` records all hashes.

  The unredacted inputs stay outside the repository.
- **One run per album**, 1,500 s ceiling: `run_trial.sh generate <input dir> <slug>`. One `-rerun` only for a harness failure (no inference, tool unavailable, hooks or memory loaded), with both records kept.
- No control arm. The comparison is the owner's experience of their usual research (limit, §7).

## 4. Order of events per album

1. Generate the note.
2. **Owner task.** The owner prepares their rating of the album the way they normally would, using the note. Endpoint: the owner's rating draft (score, or the notes they would write it from) plus the questions they still have open. The orchestrator shows the owner nothing but the note. The owner fills in `owner/<slug>.md` (§5), and it is committed and pushed. Its commit sha is recorded.
3. Model check (§6). `run_trial.sh check <slug>` refuses to dispatch unless `owner/<slug>.md` is committed and unchanged. The check's dispatch time, in its `metadata.json`, must postdate that commit.
4. The owner sees the confirmed items and may comment on each. The comments do not change the count in §7.

## 5. Owner record

`owner/<slug>.md` is a short form, written in step 2:
- **Time**: minutes spent using the note in the task.
- **Errors**: each item the owner found wrong or doubtful, with its location in the note.
- **Relied on**: the items the rating draft actually relies on, by location.
- **Use**: 쓸 만함, 조건부 or 안 씀, plus one line on why.
- **Missing**: what the owner needed that the note did not have, if anything.

## 6. Model check

- One Claude reviewer (`claude-opus-5-5`, safe mode, web tools), fresh context, one audit per note.
- Its packet is built by `build_check_inputs.py`. It holds:
  - the brief `LEAD` (sha256 `98137319…`);
  - acceptance-v1's central-claim definition (§2) and its integrity-gate section (§3), verbatim;
  - the shared input and the note;
  - the anonymous web trace, with tool results cut at 6,000 characters each, as in Stage B.

  The owner's form is never in the packet.
- It reports **critical failures only**:
  - (A) a G1–G9 pattern on a central claim;
  - (B) a direct quotation on a central claim that is not at the source the note cites for it (anchors R5's non-recovery, scoped to central claims for this trial).

  Other errors are listed as (C) and do not enter §7.
- **Confirmation.** The orchestrator checks every (A) and (B) item against the full `stdout.jsonl` and the cited source. It records each item in a table as confirmed or not confirmed, with the evidence.
  - Centrality uses acceptance-v1's indicators. The owner's "Relied on" list is indicator (c).
  - The owner has the final word on any item the owner disputes (acceptance-v1 §3: the owner adjudicates gates).

## 7. Outcome (predeclared)

- **Ready to discuss a production trial** if both hold:
  - (i) the owner marks both notes 쓸 만함 or 조건부;
  - (ii) no confirmed (A) or (B) item in either note was missed. An item counts as *caught* only if its location appears in that note's **Errors** list as committed in step 2. Every other confirmed item counts as *missed*.
- Beside the verdict, the record reports the raw number of confirmed (A)/(B) items per note, caught or not.
  - This rule is deliberately weaker than acceptance-v1 §3, under which one owner-confirmed gate instance fails the note.
  - The trial asks whether the note is safe in the owner's hands, not whether it is clean.
- Otherwise the record names the failed condition and its items. The next step is the owner's decision.
- Production adoption (prompt, `PROMPT_VERSION`, poller) is a separate decision either way.

Limits, stated with the result:
- 2 albums × 1 run, and no control;
- one reviewer, which is the same model as the producer;
- one rater, who is also the owner.

It supports "worth trying in production, under watch" or "not yet". It supports no general quality claim.

## 8. RFC and plan

- RFC §C gets a dated note, and the Decisions log gets a row. Both say that on 2026-10-20 the owner replaced the acceptance-v1 confirmation with this owner-use trial (2 albums, P6). The Goal's acceptance-v1 endpoint is therefore not claimed. The round-manifest-v1 confirmation stays unrun, and a full one would need new albums and a new draw. Stage D delivers P6, the trial evidence and its limits.
- RFC Status stays draft (hard rule 7).

## 9. Budget and stop conditions

- Claude: 2 generations + 2 checks = 4 dispatches, plus at most 2 harness reruns. No Astra dispatch.
- **Owner: about 1–2 h per album for the task and the form.** Listening, reviewing the PR that commits the form, and the step-4 comments come on top.
- Stop conditions:
  - an `album_research` row appears for either album before its owner task (report it; the owner decides);
  - a rate limit (the lane halts, and resumes only on the owner's word);
  - a CLI change that is not patch-class.

## 10. Publication and tooling

- `redact_for_publication.py <input dir>` replaces each album's owner-collection line in every record, in plain and JSON-escaped forms. It then scans for those lines' bucket names and must find 0. Original hashes go into `PUBLICATION-REDACTIONS.json`. The per-album "버킷에 담김" marker is kept, as in rounds 1–7.
  - The scan was checked: a planted unredacted input was redacted, and a planted stray bucket name failed the scan.
- The owner's form is committed only as the owner writes it.
- Tool sha256 at predeclaration:

  | Tool | sha256 |
  |---|---|
  | `prepare.py` | `0f3b0f03…` |
  | `build_check_inputs.py` | `288f52a6…` (built on round-6 stand-ins: two packets, trace counts matching round 6) |
  | `run_trial.sh` | `0831e070…` |
  | `redact_for_publication.py` | `b9f2a095…` |
  | `exposure_check.sh` | `a2b5a5a8…` |
