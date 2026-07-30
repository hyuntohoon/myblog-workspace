# Research prompt v2 vs v4 — measured head-to-head, 2026-07-30

The coding sheet behind the `12/22` quoted in `docs/plan.md`
(`CHORE-research-prompt-port-not-swap`) and in
`docs/editorial/research-note-requirements.md` §"Consequences for the prompt versions".

Recorded because those two documents quoted the denominator without the items, so the
score could not be checked and the notes lived only in a session temp directory.

## Method

Both arms out of band: **no `PROMPT_VERSION` change, no `album_research` write**. Album block,
Genius block, engine (`CliEngine`), model (`claude-opus-5`), tool policy (`WebSearch`/`WebFetch`)
and `ADDENDUM` held identical. **Base prompt was the only variable** —
`scripts/album_research_v2.md` against `scripts/album_research_v4.md`.

Runner: `research_poller.build_prompt` + `run_claude`, so argv parity with the live poller holds.

| File | What |
|---|---|
| `renaissance-v2.md` / `renaissance-v4.md` | the clean arm (below) |
| `renaissance-genius-block.md` | the block both arms were fed — **contains the #748 credit-attribution bug** (both arms equally, so the comparison holds; the absolute credit lines are degraded) |
| `onyx-v2.md` / `onyx-v4.md` | the contaminated arm (below) |
| `onyx-genius-block.md` | the block both ONYX arms were fed (post-#747, pre-#748) |
| `onyx-prod-note-old-block.md` | the real prod note from the 10:19 e2e, generated with the **pre-#747** block — the baseline showing the block fix changed behaviour |

## The clean arm — RENAISSANCE against Pitchfork

Beyoncé *RENAISSANCE*, scored against
[Pitchfork's review](https://pitchfork.com/reviews/albums/beyonce-renaissance/) — Julianne
Escobedo Shepherd, 9.0, reviewed 2022-08-01. Chosen as a Pitchfork **#1 album of the year within
the last ten years** that is also in our catalogue (2024's #1, Cindy Lee's *Diamond Jubilee*, is
not on streaming and so not in a Spotify-derived catalogue).

**Neither note cited pitchfork.com**, so the yardstick stayed independent. Verify with
`grep -ci pitchfork renaissance-v2.md renaissance-v4.md` → 0, 0.

### The 22 items — every non-audible claim the review uses

O = present in that note, X = absent. Scored by the loose case-insensitive patterns in the last
column, over the note text.

| # | Item | Role in the review | v2 | v4 | pattern |
|---|---|---|---|---|---|
| 1 | Kevin Aviance "Cunty" (1996) | `PURE/HONEY` ballroom sample | O | O | `aviance\|cunty` |
| 2 | Moi Renee "Miss Honey" (1992) | `PURE/HONEY` ballroom sample | O | O | `moi renee\|miss honey` |
| 3 | MikeQ / "Feels Like" (2012) | ball DJ, the link in the chain | O | O | `mikeq\|feels like` |
| 4 | **Vjuan Allure** (d. 2021) | reworked the "Ha" → invented contemporary vogue fem | **O** | X | `vjuan` |
| 5 | **"The Ha Dance"** (1991) | the root of that chain | **X** | **X** | `ha dance\|the ha` |
| 6 | **Masters At Work** | authors of "The Ha Dance" | **X** | **X** | `masters at work` |
| 7 | Clark Sisters sample | `CHURCH GIRL` gospel source | O | O | `clark sisters` |
| 8 | **Trigger Man beat** | `CHURCH GIRL` bounce base | **X** | **X** | `trigger man\|트리거` |
| 9 | Tommy Wright III | `I'M THAT GIRL` sample | O | O | `tommy wright` |
| 10 | Princess Loko | same sample's co-author | **O** | X | `princess loko` |
| 11 | **dembow / Shabba Ranks** | the Caribbean route under it | **X** | **X** | `dembow\|뎀보\|shabba` |
| 12 | Honey Dijon | Black trans DJ/producer, `COZY` | O | O | `honey dijon` |
| 13 | **Kelman Duran** | Dominican musician who built that route | **X** | **X** | `kelman` |
| 14 | A. G. Cook / PC Music | `ALL UP IN YOUR MIND` | **O** | X | `a\. ?g\. ?cook\|pc music` |
| 15 | BloodPop | same track | O | O | `bloodpop` |
| 16 | Ts Madison | `COZY`, trans self-determination | X | **O** | `ts madison\|madison` |
| 17 | **Uncle Jonny dedication** | the album's dedication; HIV; house entered via family | X | **O** | `uncle jonny\|jonny\|조니` |
| 18 | "Act I" / trilogy | from the liner notes | O | O | `act i\b\|3부작\|trilogy\|삼부작` |
| 19 | *Lemonade* (2016) | last proper studio album | O | O | `lemonade` |
| 20 | **Ivy Park** | the hiatus-filling activity list | **X** | **X** | `ivy park` |
| 21 | Homecoming / Beychella | framed the discography in Black performance history | X | **O** | `homecoming\|beychella` |
| 22 | **liner notes as a source** | "safe place…", the dedication text | **X** | **X** | `라이너\|liner note` |

**v2 12/22 · v4 12/22.** Each missed 10. **Both missed 7** — items 5, 6, 8, 11, 13, 20, 22.

Found only by v2: **4, 10, 14**. Found only by v4: **16, 17, 21**. The axes differ rather than the
quality — v4 on biography and primary statements, v2 on genealogy and credits — which is why a swap
trades one for the other and a port does not.

### The seven neither prompt reaches

Five of the seven are one continuous chain plus its siblings: `PURE/HONEY` → MikeQ → **Vjuan
Allure** → his rework of **Masters at Work's "The Ha Dance" (1991)**, originally for b-boys in Latin
clubs; and `CHURCH GIRL`'s **Trigger Man** beat; and `I'M THAT GIRL`'s **dembow/Shabba Ranks** route
via **Kelman Duran**. This is the review's most impressive passage, and it is *depth* — one sample
resolved back through three generations — which no rule in either prompt asks for.

Item 22 is the other kind of miss: **liner notes are never named as a source** in either prompt, yet
they carry "Act I", the "safe place" statement and the dedication. v4 reached the dedication anyway
(item 17) through press coverage, not through the notes themselves.

Item 20 (**Ivy Park**) is the only both-missed item that is merely a detail rather than a class.

## The contaminated arm — ONYX, and why it is void as a score

Simon Dominic *ONYX* was scored first, against
[IZM](https://www.izm.co.kr/posts?id=34039) (박승민, 2026-06-04). **v4 read that review** — 20
references — so every fact that looked like a v4 win there traces to the yardstick itself. The
score is discarded. Recorded so nobody re-derives it.

What the arm did establish, and what the RENAISSANCE arm cannot: **v4 dropped v2's ban on other
critics' verdicts.**

- `album_research_v2.md` rule 36 — "No ratings, scores, awards, chart positions, **or others'
  critical verdicts**"
- `album_research_v4.md` rule 32 — "No ratings, scores, chart positions, awards, or certifications"

With the clause gone, v4 imported IZM's *readings* as inputs: its genre characterisation
("중후한 웨스트코스트 풍"), its tempo observation about `후반전`, and its verdict on `PPAP` cited as
`확인 1건`. A rebuild from a coding of 38 published reviews can see what reviews *contain* and never
what a research note must *avoid* — the same blindness that made v4's evidence base miss the lyrics
and biography gaps recorded in `research-note-requirements.md`.

## Also measured here: the #747 block fix changed behaviour

`onyx-prod-note-old-block.md` (pre-#747 block) *discovered* the wrong-song match incidentally and
left it 미해결. With the evidence layer, **both** prompts resolved it — and v2 went further, triaging
all four `⚠︎ 곡명 불일치` flags individually (three benign 원제/로마자 pairs, one real collision) and
invalidating the entire credit aggregate that traced to the bad row. See the
`Genius 확인 사실 블록 — 실사용 판정` section in `onyx-v2.md`.

## Cost

| Album | Arm | Wall clock | tokens in | tokens out | chars |
|---|---|---|---|---|---|
| ONYX | v2 | 567 s | 944,946 | 29,845 | 14,752 |
| ONYX | v4 | 708 s | 1,412,389 | 35,331 | 18,695 |
| RENAISSANCE | v2 | 424 s | 486,809 | 20,649 | 17,456 |
| RENAISSANCE | v4 | 712 s | 1,487,141 | 28,104 | 19,688 |

v4 draws 1.5–3× the input tokens and 1.25–1.7× the wall clock. The 03:00 draft agent shares the
same subscription.

## Reproducing

The prompts are in the repo (`scripts/album_research_v2.md`, `scripts/album_research_v4.md`); the
album and Genius blocks are derived from prod by `research_poller._album_block` /
`_genius_block`, and the two blocks as fed are checked in here. Album ids:
ONYX `2cb43340-5f8b-4b41-b01a-c1c7d3eb15fd`, RENAISSANCE
`ee4ed417-8533-4422-ac56-3821a316c74f`. Re-running costs four subscription runs and will not
reproduce the notes verbatim — the *coding* above is the reusable artifact, not the notes.
