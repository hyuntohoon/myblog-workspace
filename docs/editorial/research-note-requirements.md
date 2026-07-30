# What a research note must supply — measured against published reviews (2026-07-26)

> **Purpose.** `album_research_v2.md` (and the v3/v4 candidates) were written from the prompt's
> stated intent. This document is written from a **measurement**: three published Pitchfork reviews
> were decomposed claim by claim and checked against **our own stored note for the same album**.
> It defines what the note can supply, what it must stop trying to supply, and what it can never
> supply. Every gap below is an observed gap, not a hypothesis.

## Method

Three albums for which we hold a stored `album_research` note (all `prompt_version = v2`,
generated 2026-06-11/15 on `claude-opus-4-8`) and Pitchfork published a review:

| Album | Review | Note |
|---|---|---|
| Tyler, the Creator — *CHROMAKOPIA* | 2024 | 6,794 chars |
| Post Malone — *AUSTIN* | 2023 | 5,361 chars |
| Radiohead — *Kid A* | 2000 (DiCrescenzo) | 5,130 chars |

Pitchfork blocks automated fetching; the reviews were read in a real browser. Each review's
load-bearing claims were classified by the kind of information they rest on, then checked against
the note for that same album.

## What the reviews were built on, versus what our note held

| Information type | CHROMAKOPIA | AUSTIN | Our note |
|---|---|---|---|
| **Direct lyric quotation** | 4 | 4 | **0** |
| **Comparison points** (other artists/works) | *Get Out* | Morgan Wallen · Warren Zevon · Antonoff · Nate Ruess · Nirvana · Beethoven | **0** |
| **Quotation from the artist's earlier work** | "Answer" (2013) lyric | — | **0** |
| **Biographical coordinates** (age, origin, relocation) | 33; father Nigerian | LA → Utah | **0** |
| Sample — the source | ✅ Ngozi Family | — | ✅ present |
| Sample — **what the source song is about** | ✅ load-bearing | — | **absent** |
| Interview tied to a specific track | — | Zane Lowe, Martin acoustic in hand | methodology only, snippet-relayed |
| Credits | — | Louis Bell · Andrew Watt | ✅ present, and fuller |
| Video / visual continuity | ✅ carries the whole opening | — | **absent** |
| Sonic description | many | many | absent — **correct by design** |

### The single clearest failure

The CHROMAKOPIA review's decisive move sets the mother's confession beside a lyric from Tyler's
2013 track "Answer" — *"Dad isn't your name, see 'faggot''s a little more fitting"*. The old line
is what makes the reversal a reversal rather than an assertion. **Our note contains the
confession but not the earlier lyric**, so a writer holding only our note cannot make that move,
even though the note already knows the album is about the absent father.

### The counter-example, recorded honestly

The 2000 *Kid A* review is built almost entirely on personal experience and metaphor — a
Radiohead show in Florence, a shooting star — and uses essentially no researched fact. Our Kid A
note's best material (the Paul Lansky citation chain: 1973 IBM mainframe computer music, found
secondhand, sampled into "Idioteque", the chord itself borrowed from Wagner) **goes entirely
unused**.

A strong review can be written with almost nothing from a research note. The note is not a
sufficient condition, and no version of this prompt makes it one. What the 2023–24 reviews show
is that when a review *is* built on research, it is built on the six things below — and we supply
almost none of them.

## The specification

### Must supply — ordered by measured shortfall

1. **Quotable lyrics — 3–5 decisive lines, each with track and position.**
   **Deferred, 2026-07-27 (owner).** Two of three reviews quote four lines each and we supply
   zero, so the measurement stands — but filling it reliably needs Genius. `genius.com` is
   fetch-blocked from the run, `FEAT-lyrics-annotations` is still a draft RFC, and the trial note
   for *BRAT* could only re-quote lines that press articles had already printed. A section that
   can only be filled second-hand is not worth its place in the prompt yet. Revisit when the
   Genius block exists.
2. **Comparison points — 3–6, each with one line on why it is comparable.**
   One review alone names six. `album_research_v2.md` has no section for this at all. The verdict
   stays the critic's; the note supplies candidates.
3. **Quotable fragments from the artist's earlier work** — lyrics, personas, past statements.
   Not "this is their eighth album" but *the earlier text itself*. This is the only material that
   lets a review prove a reversal, a turn, or a growth claim.
4. **What a sample's source actually is** — not only that it was sampled.
   "Sampled Ngozi Family" (ours) versus "that song is partly about warding off harm" (Pitchfork).
   The second makes an argument; the first is a citation.
5. **Biographical coordinates** — age at release, origin, relocation, family facts.
   All searchable. Present in neither v2 nor v4.
6. **An interview tied to a specific track**, primary source where reachable.

### Must not supply

- **Sonic description.** The critic hears it; any adjective we write is noise. This is already
  the v2 rule and it is correct.
- **Structural verdicts** — "it has a bridge", "it is too short to land". These are listening
  judgments wearing a factual coat.
- **Ratings, scores, chart positions, awards.**
- **An assessment of the note's own adequacy.** (See `buckit-nightly.md` v0.4 — the nightly
  drafter is now barred from writing this too.)

### Can never supply

Personal experience, and **the viewpoint**. Every published review above is organised by a
judgment its writer arrived at by listening. No research note produces that, and a note that
tries is writing the review.

## Consequences for the prompt versions

| Gap | Addressed by v4? |
|---|---|
| 2 — comparison points | **Yes** — `계보와 비교 좌표` is a new section aimed exactly here |
| 6 — interview primaries | **Yes** — "when an annotation points at an interview, go and get the interview" |
| 4 — meaning of a sample source | Partly — `무엇으로 만들었나` exists but never asks what the source song is |
| 3 — earlier-work quotation | Partly — `아티스트와 전작` names prior work but does not ask for quotable text |
| **1 — lyrics** | **No. v4 has no section for this.** |
| **5 — biography** | **No. v4 has no section for this.** |

The two largest measured gaps are covered by neither v2, v4, nor the Genius RFC. v4's evidence
base was a coding of 38 reviews by information type; lyric quotation most likely disappeared into
the "sonic description" bucket, which is why a rebuild from statistics missed it.

This also **raises** the value of the Genius block (`FEAT-lyrics-annotations`, draft): Genius
supplies lyrics, links to the artist's earlier work, and annotations that point at interviews —
gaps 1, 3, and 6 at once. It remains unbuildable as currently scoped (its R0/R1 steps do not
exist and no `GENIUS_ACCESS_TOKEN` is in SSM), but its priority is higher than previously judged.

## Changes made from this measurement

`전기적 좌표` was added to the live prompt
(`docs/editorial/album-research-prompt.md` and its vendored twin `scripts/album_research_v2.md`,
kept byte-identical over the shared range) and to `scripts/album_research_v4.md`, since neither
version had it.

`인용 가능한 가사` was added to both on 07-26 and **removed again on 07-27** — see gap 1 above.

Two owner decisions on 07-27 shrank the credits work rather than growing it:

- **Credits are not a priority.** v4's `크레딧` is now optional, capped at a line or two of
  argument, with the full roster in the appendix.
- **The mandatory cross-tabulation rule is deleted.** It was written after one album (*LUX*) and
  its example column pairs — recording room × choir, arranger × guest — are artifacts of that
  record. Forcing it on a thin roster invites a correlation manufactured from two rows and
  presented as the note's best finding, which is the failure the rule existed to prevent. An
  independent adversarial review of v4 had flagged the same rule as overfit before the owner
  raised it.

Net: **v2 covers 1 of the 6 gaps, v4 covers 4** (comparison points, interview primaries, and
partially earlier-work and sample meaning). ~~That remains the argument for adopting v4 rather than
continuing to patch v2.~~

**Overturned by measurement, 2026-07-30 — port, do not swap.** The section-count comparison above
was never run against output. It has now been, twice, out of band (no `PROMPT_VERSION` change, no DB
write), with the album block, the Genius block, engine, model and tools held identical and the base
prompt as the only variable.

**The clean test — Beyoncé *RENAISSANCE*, scored against Pitchfork's review** (Julianne Escobedo
Shepherd, 9.0, 2022-08-01; chosen as a Pitchfork #1 album of the year inside the last ten years that
is also in our catalogue). Neither note cited pitchfork.com, so the yardstick stayed independent.
Coding the 22 non-audible claims the review actually uses:

**v2 12/22, v4 12/22 — a tie, with almost no overlap in *which* twelve.**

| | Found only by this arm |
|---|---|
| **v2** | Vjuan Allure (the root of the vogue-fem "Ha" lineage), Princess Loko, A. G. Cook / PC Music |
| **v4** | the Uncle Jonny dedication (HIV, and house music entering the family home — sourced to Exclaim! + W + a Tina Knowles quote, with the death date correctly left `[미확인]`), Ts Madison, Homecoming/Beychella |

The axes differ rather than the quality: v4 is stronger on biography and primary statements, v2 on
genealogy and credits. Swapping trades one for the other. **Both miss the same seven**: "The Ha Dance" (1991),
Masters at Work, the Trigger Man beat, the dembow/Shabba Ranks route, Kelman Duran, Ivy Park, and
**liner notes as a source at all**. Five of those are one continuous chain plus its siblings —
*Pure/Honey* back through MikeQ to Vjuan Allure's rework of "The Ha Dance", the review's most
impressive passage — so the miss is *depth*, which no rule in either prompt asks for. **That gap
belongs to neither prompt and is the larger opportunity.**

**The coding sheet, the raw notes and the exact blocks as fed are checked in** at
`docs/reviews/measurements/2026-07-30-research-prompt-v2-vs-v4/` — all 22 items with their per-arm
O/X and match patterns, so the `12/22` above is checkable rather than asserted.

**A regression found in v4, independent of the tie.** v2's rule 36 bans "ratings, scores, awards,
chart positions, **or others' critical verdicts**"; v4's rule 32 keeps everything except that last
clause. In the second test (*ONYX*) v4 duly read the published IZM review and pulled its *readings*
in as inputs — 20 references, including IZM's genre characterisation, its tempo observation, and its
verdict on `PPAP` cited as `확인 1건`. This is the contamination v2's clause exists to prevent, and
it is a predictable cost of rebuilding from a coding of 38 reviews: a statistical pass can see what
reviews *contain*, never what a research note must *avoid*.

(That same contamination voids the *ONYX* arm as an independent score — every fact there that looked
like a v4 win traces to the review being used as the yardstick. Recorded so nobody re-derives it.)

**Cost.** v4 draws 1.5–3× the input tokens and 1.25–1.7× the wall clock per note (*RENAISSANCE*:
424 s / 487k in for v2 against 712 s / 1,487k for v4). The 03:00 draft agent shares the same
subscription.

**Therefore:** port v4's biography / primary-statement pressure into v2, keep v2's others'-verdicts
ban, and add the liner-notes + sample-chain-depth rule neither prompt has. Adoption of v4 as a swap
would additionally have to solve the two blockers below (the `PROMPT_VERSION` filter hiding all
existing notes, and `[확인: Genius]` appearing 0× in v4 against 3× in v2 — switching today would
drop the wrong-song defence added on 2026-07-30). Tracked in `plan.md`.

Also fixed while here: `research_poller.py`'s `ADDENDUM` instructed the model to record residual
disambiguation "inside the `앨범 식별` section", a section v4 does not define. It is now written
prompt-agnostically ("whichever section the output format uses for identification, or failing that
its unconfirmed-items section"), so the same addendum is correct for v2 and v4 alike. That
mismatch was the last mechanical blocker to running v4 through the pipeline.

## Provenance caveat

`research_poller.py` and `research_service.py` both pin `PROMPT_VERSION = "v2"`, and
`mark_done` never re-stamps it, so notes generated after this edit are stored under the same
label as notes generated before it. The two are no longer the same prompt. Bumping the constant
would hide all 78 existing notes from the UI, since `get_research`/`status_map` filter on it —
that fix (newest-row-per-album) is tracked separately and is not part of this change.
