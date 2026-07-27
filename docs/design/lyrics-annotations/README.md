# Lyrics-annotation UI — design record (2026-07-26)

Ten design directions explored for **FEAT-lyrics-annotations Thread 1**: a static lyrics reader where
tapping a marked passage opens the Genius commentary attached to it.

**Chosen: the Genius house style** (`houses/genius.html`). Owner decision, 2026-07-26.

`FEAT-lyrics-annotations` was promoted to **accepted on 2026-07-26**, so Thread 1 is cleared to build
against this direction. This is the visual half of the record; the mechanism lives in
`docs/rfcs/FEAT-lyrics-annotations.md` §6, and the storage schema in §6.9.

---

## Owner decisions this record encodes

| Decision | Consequence for any design here |
|---|---|
| Korean tracks are **out of scope** — not annotating them may simply be the efficient answer | No design needs a Korean-coverage fallback. The empty-annotation state stays a plain empty state |
| **Show every annotation** — no editorial selection | No relevance score, no ranking. Order is position in the lyrics |
| **Always translate the commentary into Korean** | The body a reader sees is Korean; the original language is secondary and collapsible |
| Host is the **static** reader, not the immersive viewer | `LyricsSheet.tsx` — see "Where this lands" below |

## Constraints measured from real data — a design that breaks one is wrong

From ROSALÍA *LUX*, 13 tracks with synced lyrics, 103 annotations measured (`tools/genius_anchor.py`):

- **An annotation covers a RANGE, not a line.** Median 2 lines, mean 2.3, 1 in 6 covers 4 or more,
  longest 12. "One line, one marker" is the wrong mental model — the RFC used to say "inline per-line
  layer", which understated it; §6.6 has since been corrected to say *range*.
- **94.7% of lyric-bound annotations can be placed** (90 of 95); **74.7%** (71 of 95) resolve to a
  single unambiguous span. The gap is `repeated` (19, 20%) — chorus passages whose location *is*
  known; rendering them on the first occurrence and admitting the repeat is the intended handling.
  Both figures are correct and share the 95 lyric-bound denominator — quote them together.
- **Marker density is ~1 line in 3** — 201 of 590 lines across the album. Per track it ranges from
  9.5% to 64.7%, so every design was checked against both ends.
- **Overlap is a non-problem.** 3 of 201 marked lines are claimed by two annotations, never three.
  No stacking system is needed.
- **Bodies are long.** Several exceed 1,000 characters, with paragraphs and nested quotations. The
  reading surface is not a tooltip.
- **Votes can be negative** (lowest −17 in this album) — a disputed reading must not look endorsed.
  Sorting by votes is prohibited: it surfaces translations, which are an explicit non-goal.
- **Commentary can exist without lyrics.** 2 of 15 *LUX* tracks carry 12 annotations and no synced
  lyrics, which is why the store is independent of lyrics and the renderer has a standalone mode.

## The rounds

1. **Four interaction shapes** — 행간 펼침 (inline expand) · 측주 단 (margin column) · 바닥 시트
   (bottom sheet) · 숨은 주석 (reveal-on-hover). Owner picked the margin column's *structure*.
2. **Four visual treatments of the margin column** — 교정쇄 (hairline bracket + line numbers) · 여백
   (no rail, the lyric's own ink changes) · 역전 (lyrics recede, commentary carries the weight) ·
   편집 (magazine spread with a headline). Structure confirmed, treatment rejected.
3. **Six house styles** — this directory. The same feature rendered in the visual language of six
   well-known products, to break out of the project's own palette. Genius chosen.
4. **The dense-track stress test** — the chosen style at its three undrawn failure points
   (density, repeats/unmatched, dark). Findings below.

## The six house styles

Each is an isolated module in `houses/`: one `<style>` block whose every selector is prefixed
`.h-<slug>`, plus a `mount(root, data, trackNo)` registered on `window.HOUSES`. They share no CSS and
no markup, so each owns its interaction model, not just its skin.

Each author stated their own bet and their own weakest point. Their admissions are the more useful
half of this record — they are what a future implementer would otherwise have to rediscover.

| Slug | Reference | The bet | Where its author says it breaks |
|---|---|---|---|
| `genius` | Genius annotation page | **Chosen.** Yellow highlight whose block length *is* the range, a margin bracket and an "N행" tail so the reader sees how far it runs, and negative-vote annotations stripped of the yellow and marked disputed | At 36.8% of lines marked, "the yellow stops meaning *this one is special*" — chips, line numbers, brackets and range tails pile up and the page gets noisy |
| `apple` | Apple Music lyrics | With no playback, **scroll position becomes the playhead**: a band at 42% of the viewport brightens whatever it touches, and a whole annotated range lights as one slab | Type is so large that a 12-line range never fits one screen; on the sparse track the band sits over nothing for long stretches |
| `spotify` | Spotify lyrics | Moves the "line being sung" contrast to "passage being read" — the open range flips to highlighter yellow, everything else sinks toward the field colour | Never stops shouting; reading a 2,500-character body inside a black card with blue and yellow pressing in. Knocked-back lyric contrast ~3.9:1 is at the legibility floor |
| `medium` | Medium reading surface | One 604px measure, 21px serif, near-monochrome — the lyrics are read as an essay, the note waits in the margin | Gave up colour and density, so you cannot see at a glance where the readings cluster; you have to open them one at a time |
| `notion` | Notion document + comments | Annotations as **comment threads** in the margin — the only version that shows many at once, anchored to their highlighted span | Where an annotation has no gist, the collapsed card opens on Spanish source text before reaching the Korean |
| `nyt` | Newspaper longform | Marks leave the text entirely: a red number and a bracket in the margin, the same number recurring in the margin, the footnote and the end list; the 5 unlocatable annotations get ㄱ·ㄴ·ㄷ so they are not lost | Opening a note pushes the body down; all 14 open makes the page over 10,000px, so reading the lyrics and reading the notes fight each other |

`genius.html` is worth reading even if the visual direction changes later: its screen-reader label
announces the range ("해설 1번, 3행부터 4행까지 2행"), and its index states in the UI that ordering
follows the lyrics rather than vote counts. Its author's own caveat above is the one to carry
forward — the chosen design is weakest exactly on the dense track.

**All six commit to a single theme** (verified: none respond to `data-theme`). That was a deviation
from the brief, which asked for both, and it is the right one — Apple's lyrics screen is dark,
Spotify's is a colour field and Genius's is white, so forcing both themes would break the reference.
It does mean the light/dark question is unanswered for the real implementation, where the product
already supports both. Only the shell chrome around the stage is theme-aware.

## Round four — the dense-track stress test (2026-07-26)

The six house styles were all drawn against **placed annotations only** (`build_mock_data.py` sets
`placed_pct: 74.7`), all in a **single theme**, and at a comfortable density. So three things had
never been drawn at all: the `repeated` 20%, the `unmatched` 5.3%, and either theme's failure mode.
A fourth round put the chosen style at those points — link in `local/ARTIFACTS.md`, synthetic data
only (density, span length, body length and vote distribution reproduced; no real lyrics).

What it settled:

- **Dark is not a token swap — it is an ink problem.** The stage's body ink is near-white, and
  near-white on the highlight yellow measures ~1.5:1. The fix is not a different yellow; it is
  inverting the text **only on the lines the fill actually reaches** (12.4:1 after), while lines that
  never receive the fill — disputed, repeat echoes, section labels — keep the light ink. A 1px rule
  also needs a brighter tone on near-black than on white.
- **M0 is not wrong, it is density-blind.** At 65% marked the yellow becomes the ground and the
  *unmarked* lines are what stand out — the figure/ground inversion the author predicted. At the
  album average of 34.1% the same treatment is fine. That points at a density-adaptive rule rather
  than a different treatment.
- **Three alternatives were drawn and each has a named cost**: `M1` rule-not-fill (loses scanability
  — the medium house's exact weakness), `M2` margin-only (loses the signal that annotations exist,
  and has no margin on narrow screens), `M3` reveal-on-open (loses discoverability, and is the only
  treatment that gets *better* as density rises).
- **A repeat is a second occurrence, not a failure.** Proposal, now drawn: number and bracket the
  first occurrence only; later occurrences get an unnumbered quiet rule and a `반복` tail; opening
  either shows the same note and states "곡에서 N번 나옵니다". No annotation ever carries two numbers.
- **Unmatched annotations go to a drawer** under the sheet with ㄱ·ㄴ·ㄷ marks (the nyt house's idea),
  not discarded — they re-anchor by themselves if the lyrics are re-matched, because anchors are
  computed at read time.
- **Negative-vote annotations never receive the fill**, in any of the four treatments — a −17 reading
  rendered in the endorsing yellow reads as the site agreeing with it.
- **The margin column only works if the note tracks its range.** The first build pinned the column
  with `position: sticky`, so opening an annotation on line 30 put its commentary at the top of the
  screen, far from the passage it explains — which defeats the entire reason the margin structure was
  chosen over a bottom sheet. The note must be positioned to the range's first line and clamped so a
  note opened near the last line does not hang off the bottom. Below the two-column breakpoint there
  is no margin to sit in, so the note opens **inline directly under its own range** instead.

Still unsolved, and visible in the artifact: a **12-line span** looks bad under every treatment
(M0 eats the screen, M2's bracket scrolls out of view), and the **3-in-201 overlap** has no rule —
the later annotation currently just wins.

## The render spec — decided 2026-07-27

Everything above is exploration. This section is the **contract the implementation is built against**,
written so a later change is diffable: if the rendering stops matching this, either the code drifted or
this section did, and one of them is a bug.

### One setting, two fixed rules

**Highlight treatment is a setting; long spans and overlap are not.** That split is not a matter of
taste — it follows from the measurements.

Marker density is **9.5% to 64.7% per track** (201 of 590 lines album-wide). No single treatment
survives that whole range: the yellow fill is right at the album average and becomes the page's ground
at the dense end, while a treatment tuned for the dense end is invisible on a sparse track. **The data
says a fixed choice is wrong here**, which is what justifies exposing it. Long spans and overlap are
different — each has one answer the measurements point at, and offering alternatives would only invite
picking a worse one.

| Axis | Decision | Why it is settled or not |
|---|---|---|
| Highlight treatment | **Setting**, default `M0` | Density varies 6× per track; no fixed answer is correct across it |
| Long spans | **Fixed: A2**, threshold 4 segments | One shape reads best at 12 lines and the alternatives each lose something |
| Overlapping lines | **Fixed: B2** + containment fallback | The current behaviour can make an annotation unreachable; B2 cannot |
| Repeats, unmatched, disputed, ordering | **Fixed** | Owner decisions or direct consequences of the measurement |

### Highlight treatment — `lys:anno-style`, default `M0`

Persisted beside the existing typographic mode (`lys:mode`, doc/liner) in `localStorage`, same pattern.

- **`M0` — fill (default).** The chosen Genius house: a yellow block whose length is the range, a
  margin bracket, an `N행` tail. Correct at the album average.
- **`M1` — rule.** No fill; a bottom rule per marked line, and the fill is spent only on the open
  annotation. For dense tracks. Costs scanability — you can no longer see where readings cluster.
- **`M2` — margin only.** The text is untouched; the margin carries the whole affordance. Best reading
  of the lyrics themselves; weakest signal that annotations exist, and there is no margin below the
  two-column breakpoint.
- **`M3` — reveal on open.** A faint rule everywhere, yellow only on the open annotation — yellow made
  rare by construction. The only treatment that improves as density rises; costs discoverability.

### Long spans — A2, ends only, at 4 segments or more

One annotation in six covers 4+ segments; the longest measured is 12. At 12, a full fill takes two
whole stanzas and the yellow stops being emphasis.

- Fill **the first and last segment only**; leave the middle text alone.
- The **gutter bracket runs the full height** and is what holds the two ends together as one
  annotation — it is load-bearing, not decoration. Verified at 12 segments; **a span tall enough to
  leave the viewport has not been verified** and is the known gap.
- The `N행` tail sits at the last segment.
- Below the threshold nothing changes — short spans keep the treatment the setting selects.

### Overlapping lines — B2, the shorter span owns the line

3 of 201 marked lines carry two claims; never three.

- The line is owned by the **shorter (more specific)** span. The longer one stays reachable from its
  own other lines, so nothing is lost.
- The shared line renders a **doubled gutter rule** and a `해설 2` chip.
- **Fallback, required:** if the shorter span is fully contained in the longer one *and* the longer one
  has no unshared line, B2 would make the longer one unreachable. In that case open **both** notes,
  stacked in lyric order. This case does not occur in the LUX measurement, so it will not show up in
  testing — implement it from this rule, not from observed data.
- What this replaces: the previous behaviour was "the later annotation wins", which was **a side effect
  of a loop overwriting per line, not a decision**, and it silently deleted the other annotation.

### The rules that were already settled

- **Repeats (20%).** Number and bracket the **first occurrence only**. Later occurrences get an
  unnumbered quiet rule and a `반복` tail. Opening either shows the same note, which states
  `곡에서 N번 나옵니다`. No annotation ever carries two numbers.
- **Unmatched (5.3%).** Not discarded — listed in a drawer under the sheet marked ㄱ·ㄴ·ㄷ. They
  re-anchor by themselves if the lyrics are re-matched, because anchors are computed at read time.
- **Disputed (`votes_total < 0`).** **Never receives the fill, in any treatment.** A −17 reading drawn
  in the endorsing yellow reads as the site agreeing with it; it gets a rust rule and a
  `커뮤니티에서 반박된 해석` flag instead.
- **Ordering is position in the lyrics** — `(start_i, referent_ordinal)`, unanchored rows by
  `referent_ordinal` alone. **Never by votes**: vote order surfaces translations, an explicit non-goal.
- **Section referents** (`[Verso 1]`, 8 of 103) are stored and rendered on the section label itself,
  never as an in-text highlight.

### Note placement

- **The note tracks its range.** Aligned to the first segment of the open span, clamped so a note
  opened near the last line does not hang off the bottom. A column pinned to the top of the viewport
  defeats the reason the margin structure was chosen at all.
- **Below the two-column breakpoint** there is no margin, so the note opens **inline directly under its
  own range**.

### Dark theme

Not a token swap. The body ink is near-white and near-white on the highlight yellow measures ~1.5:1.

- The highlight shifts toward amber on the dark ground (`#FFF06A` → `#F5D316`).
- **Invert the text to near-black only on lines the fill actually reaches** (12.4:1 after). Lines that
  never receive the fill — disputed, repeat echoes, section labels — keep the light ink.
- A 1px rule needs a brighter tone on near-black than it does on white.

### Still unverified

- A span tall enough to scroll out of the viewport (A2's bracket is the only thing joining its ends).
- The B2 containment fallback — absent from the LUX data, so it has no test case yet.
- Everything here was judged on **synthetic data matched to the measured properties**, not on real
  lyrics. Density, span length, body length and vote distribution are reproduced; the words are not.

## Where this lands

The host is **`myblog_front/src/components/member/lyrics/LyricsSheet.tsx`** — the static reader that
already shipped (FEAT-lyrics-sheet, 2026-07-08), not `LyricsViewer.tsx`:

- the sheet renders each line as a `<p>`; the viewer wraps every line in a `<button>`, so an
  interactive marker inside a line would be invalid nested content
- the sheet already keys on the server's segment index (`s.i`) — the coordinate annotations need
- the sheet already renders gap segments as `· · ·`, which the numbering counts
- the viewer caches per-line pixel offsets that an async annotation load would silently invalidate

## Running it

```bash
python3 build_mock_data.py     # rebuild local/lux_mock_data.json (needs the source dumps + backend venv)
python3 assemble_houses.py     # houses/*.html -> local/annotation_houses.html
```

`assemble_houses.py` rejects any fragment whose CSS is not fully namespaced, so the six stylesheets
cannot fight on one page. Fonts are deliberately not loaded — the real faces (SF Pro, Circular,
Programme) are unavailable, so the stacks fall back to system faces. Judge proportion, weight,
spacing and density, not letterforms.

## What is NOT in this directory, and why

`local/` is gitignored. **This repository is public**, and the assembled mockups and
`lux_mock_data.json` inline complete *LUX* lyrics and Genius annotation bodies. Publishing those would
break the owner-only privacy bar (`FEAT-lyrics-annotations` §2) and matches the existing
`tools/.lyrics-phase1-*` exclusion, which is ignored for exactly this reason.

The files in `houses/` carry no lyrics — they receive data through `mount(root, data)`. The only
matches for song text in the committed files are track *titles* in comments, which are public
metadata.

Rendered artifact links live in `local/ARTIFACTS.md`, not here: the artifacts are private to the
owner's account and contain the lyric data.
