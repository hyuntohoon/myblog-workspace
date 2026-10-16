# Round manifest v1 — calibration and confirmation (acceptance-v1)

- Contract: `acceptance-v1.md` (sha256 `605b72a0…`, v1). Anchors: `a2-anchors/anchors-v1-rc.md`, frozen 2026-10-16 as anchors-v1 (sha256 `b9a3296f…`).
- Date: 2026-10-16 (Stage A-2). Prepared by the orchestrating session (`claude-opus-5-5`). The owner decided the items marked **owner** in chat on 2026-10-16.
- This manifest is frozen **in parts**. The contract fixes when each part must freeze, and nothing may be changed after its point:

| Part | Freezes at | State |
|---|---|---|
| §1 scope, §2 albums and blocks, §3 categories, §4 environments, §5 control and inputs, §8 allocation draw | Stage A-2 (this PR) | **frozen** |
| §6 scoring manual (severity, high-risk classes, M1–M5), reliability criterion | before calibration (contract §6.1, §6.4) | §6.4 values below; manual pending |
| §7 binding floors, zero-denominator rules, quality-gain definition, comparison rules, retry eligibility | before any confirmation output (contract §4.3, §7, §8) | *candidate* values below; **not frozen** |
| Candidate prompt hash | Stage B freeze | pending |

## 1. Scope (contract §1)

| Item | Value |
|---|---|
| Album classes | Post-model-cutoff 2026 releases: US major-label rap and pop (block A), Korean independent hip-hop (block B). Nothing outside these classes is tested. |
| Languages | Sources in any language. The notes under test are expected to cite English and Korean. The owner is the competent reader for Korean and English. Claims needing any other language are *unassessable* without a competent reader (contract §4.4). |
| Access permissions | Web search and fetch only. **No audio access**: every sonic description is assessed under G3a. No database or private material beyond the shared input block (§5). |
| Research time and tool budget | Per producer run: wall ceiling 1,500 s, the pilot value. No tool-call cap; calls are recorded. Per mapping pass: the same. |
| Output language | Korean, which is what both the control (v2) and the pilot prompt specify. |
| Control prompt version | Production v2 (**owner**), see §5 |
| Declared benefit claims | **Time-saving and quality improvement, judged separately** (**owner**, 10-16). The quality-gain definition is §7 *candidate*. |

## 2. Albums and blocks

The catalog IDs are prod `albums.id`, read on 2026-10-16. Selection rule: albums the owner has marked as review candidates or that sit in their to-listen bucket, or (for B2) a catalog album matched to its blockmate. Excluded: anything with an `album_research` row the owner may have read, any owner rating, and any post.

**Confirmation: 4 untouched albums**

| Block | Album | Artist | Release | Label | Tracks | Spotify | Strata |
|---|---|---|---|---|---:|---|---|
| A | HABIBTI (FOMO) | Drake | 2026-10-02 | OVO/Republic | 15 | `4gvyJRNQPBb1kOWqwZjUYI` | post-cutoff · credit/sample complexity |
| A | Detour (Rare N' Deluxe) | Kim Petras | 2026-09-18 | BunHead / Amigo Records | 18 | `5z3r0mH5guiXBrN8z3iEWh` | post-cutoff · edition complexity (deluxe) |
| B | FREE THE MANE 4 | FREE THE MANE, 비프리 | 2026-10-03 | New Wave Records / ADA | 12 | `51bihzxqpN0YVQGeQ0Lyce` | post-cutoff · non-English primary · sparse documentation |
| B | 안개 속의 JDL (**owner**) | JDL | 2026-10-03 | Blu Tongue | 13 | `6ehP9HPujnWINh6wqzwcjR` | post-cutoff · non-English primary · sparse documentation |

- All four strata of contract §7 are covered.
- "Post-cutoff" means after the stated training cutoff of `claude-opus-5-5` (June 2026). Before generation, the `gpt-6-astra` cutoff is recorded from the account catalog. If it is later than 2026-09-18, that stratum is reported for the Claude lane only.
- **Matching variables:** language of primary sources, label tier, release window (16 days within block A, the same day within block B), track count (15/18, 12/13).
- **Residual differences (catalog facts only; documentation density is not yet measured and will be estimated from the mapping passes).** Block A: Spotify popularity 51 (HABIBTI) vs 71 (Detour), and only Detour's target is a deluxe edition. Block B: popularity 35 (FTM4) vs 24 (JDL), and FTM4 is a two-artist crew release while JDL is a solo release. These differences are reported with every block result.
- **Catalog IDs (`albums.id`):** HABIBTI `eb1817f0-2468-4e14-9926-a3af404b6547` · Detour `50d820b4-b4d6-412d-a45e-dc326c7f6796` · FTM4 `9de8820b-bab2-4648-9957-44dabf5b223c` · JDL `7eb56967-085e-4b55-9427-db7dc0ebc2eb` · QRÖMELIFE `20d2a74c-acc9-4270-b714-baed5adad51c` · 새천년 `621144a4-d025-4aaa-9d8c-085cf7e1a628`.
- **Target editions** are exactly the Spotify IDs above. Detour's target is the 18-track *Rare N' Deluxe*, not any standard edition.

**Calibration: 2 albums, never used for confirmation**

| Album | Artist | Release | Tracks | Spotify | Why |
|---|---|---|---:|---|---|
| QRÖMELIFE | Quavo | 2026-10-02 | 14 | `1wlMQzvQlRuf4zPpPBYoMT` | US rap: calibrates the credit and sample dimensions next to block A |
| 새천년 | 이수린 | 2026-09-19 | 10 | `56gIlt2l9TEQJHyQVGagCt` | Korean independent hip-hop: calibrates translation and sparse-documentation behaviour next to block B |

- QRÖMELIFE has a production v2 note (`album_research` v2 done). The owner has not read it (**owner**, 10-16). That note may serve as one of the about 8 natural calibration outputs.
- Spare, if a calibration album becomes unusable: DO YOU SEE ME? (Q Marsden; v2 note unread by the owner).

**Exposure guard (contract §7, "nothing reaches the owner before its task").**
- A library bucket with `research_mode='all'` exists. Adding any confirmation album to it auto-queues a production v2 note (`library_sync_service._enqueue_research`). Until each album's audit is finished:
  - the owner does not add it to that bucket;
  - the owner does not request research for it;
  - the owner does not read a note on it.
- At the confirmation freeze and before each owner task, the orchestrator checks that `album_research` has no row for the four album IDs, and records the check. If a row exists, the owner's exposure to it is recorded. An exposed album is replaced only by an owner decision, and the replacement is disclosed.

## 3. Essential-question categories and priority (contract §5.2) — **owner**

The categories are album-independent. Mapping lanes propose essentials and a top-3 inside them, and ties are cut in this order:

1. Documented creator statements: intent, concept, making process.
2. Principal credits: production, writing, featured and contributing performers, per track.
3. Sample and interpolation provenance.
4. Release identity and edition.
5. Reception facts: chart and sales data, and attributed critical reception presented as others' judgments (contract §4.5).

## 4. Environments and models

| Role | Claude CLI environment | Codex environment |
|---|---|---|
| Producer (candidate and control) | `claude-opus-5-5`, effort medium, WebSearch + WebFetch | `gpt-6-astra`, effort medium, `--search` |
| Mapping lane (contract §5.1) | `claude-opus-5-5` | `gpt-6.1-sol` |
| CLI | version recorded per run | ChatGPT.app bundled codex-cli (0.162.0-alpha.17.2 at A-2). The PATH 0.147.0 rejects `gpt-6-astra`. |

- **Producers.** These are the strongest model per environment in the pilot. `gpt-6-astra` and `gpt-6.1-sol` tied at the top. `claude-opus-5-5` was the top Claude sample. The pilot is one album and one run, so this choice is a fixed configuration, not a ranking claim.
- **Mapping lanes.** The GPT lane uses `gpt-6.1-sol`, so it is not the GPT producer model. The Claude lane shares the producer model because no other Claude model was comparably strong in the pilot. This shared-model limitation is disclosed with every recall figure.
- **Preservation.** Every run preserves the three records required by contract §3: the tool-call log, the tool output the producer received, and the harness capture of each cited URL. WebFetch output in the Claude lane is model-processed text and is recorded as such.

## 5. Control and shared inputs

- **Control = production v2:** `scripts/album_research_v2.md` (sha256 `8cbdf0e9…`, content last changed `7b47891`, 2026-07-30) followed by the poller's `ADDENDUM` constant (`scripts/research_poller.py`), in the poller's order. These are the bytes production sends before its context blocks.
- **Shared input block, the same bytes for candidate and control per album:**
  - the poller's album block;
  - the Genius facts block and the catalog block, as `build_prompt` renders them (`_album_block`, `_genius_block`, `_catalog_block`).
  - The block is rendered once per album at the confirmation freeze, stored, and hashed. The candidate is not given the production base prompt.
- **Candidate:** the Stage B prompt, frozen with its sha256 before any confirmation dispatch.

## 6. Calibration and reliability (contract §6)

- Calibration material: about 8 blinded natural outputs over the two calibration albums, both environments, candidate and control mixed. Perturbation ladders (≥ 3 rungs, *candidate*) only for dimensions proposed to bind.
- Reliability criterion (§6.4), written here before calibration:
  - delayed repeat ≥ 7 days, with ≥ 2 items per dimension and no use↔reject flip;
  - model annotator matches the owner on all but at most 1 ladder rung.
  - All three numbers are the contract's *candidate* values, now fixed for this round.
- Model annotator for §6.4(ii): `claude-opus-5-5`, fresh context per item, given only the anchors, the scoring manual and the item.

## 7. Candidate values — frozen only before confirmation, after calibration

These values are proposals that calibration can change. They bind only once frozen in a later revision of this file, before any confirmation output exists (contract §4.3).

| Item | Candidate |
|---|---|
| Binding floors | D1: 0 wrong. D2: 0 S1, ≤ 1 S2/S3 among central claims (contract's count form; eligible claims are expected < 20). D3: 0 central upgrades. D6: 0 central role/edition errors. D7: 0 silent top-3 misses (already §8.2). D4 and D5: set from calibration. |
| Zero-denominator rule | A dimension with 0 eligible items is reported "no eligible items". It neither passes nor fails that floor. An output with 0 central claims is *unassessable*. |
| Quality-gain definition (§8 quality improvement) | In each block, the candidate-assisted outline captures ≥ 1 more initial-map essential than its paired baseline, with no more errors at or above S2, within an extra-time allowance of D11 ≤ baseline + 20 %. |
| Retry eligibility | Contract §7 as written: one rerun only for no inference or tool unavailability, with both records kept. |
| Completion criterion | A non-empty note on the target edition, with the run's preservation records present. |

## 8. Allocation (contract §7, drawn 2026-10-16 05:46:56 UTC)

From `round-manifest-v1-allocation-draw.json`: one execution of `secrets.SystemRandom`, output recorded verbatim, before any output exists.

| Block | Candidate-assisted task | Owner's usual research | Candidate environment | Run the owner sees |
|---|---|---|---|---|
| A | HABIBTI (FOMO) | Detour (Rare N' Deluxe) | Claude CLI | run 2 |
| B | FREE THE MANE 4 | 안개 속의 JDL | Codex | run 1 |

Environment and album are confounded with block (contract §8, "Confounding"). Neither environment's result alone shows a repeatable benefit.

## 9. Budgets

- **Producer calls:** 32 confirmatory (contract §7). Mapping: 2 per album × 4 = 8. Calibration generation: about 8, with natural outputs reused where they exist.
- **Owner hours (30–60 h, owner):**
  - planned split: calibration 8–12 h, map adjudication and labelling 6–10 h, the four tasks 8–16 h, audit 10–20 h;
  - actual hours are reported per role;
  - if the budget runs out before the mandatory checks are done, the result is **deferred** (contract §7).
- **Claude subscription:** dispatches go through the shared subscription guard. A throttle stops that lane without retry (pilot rule).
