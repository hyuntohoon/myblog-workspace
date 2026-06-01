# FEAT-design-system-measure: Design token scale completion + content measure unify

- **Status**: draft
- **Owner**: park_hyun
- **Created**: 2026-06-01
- **Plan row**: `plan.md` → FEAT-design-system-measure

---

## Goal

The `myblog_front` design system is fully tokenized — `global.css` `@theme`
carries spacing, radius, z-index, and a Spotify brand color alongside the existing
color/font tokens, and the large page stylesheets reference those tokens instead of
magic numbers and raw hex. The reading/writing content column is unified at a single
**800px** measure (up from a cramped, inconsistent 720/720/760), with a Pitchfork-style
**break-out** so the album hero and tracklist extend wider than the prose. The unused
`daisyui` dependency is gone, and `writer.css` (1497 lines) is split into feature
modules. The warm-cream editorial visual direction is unchanged — this is the token
layer and column width underneath it, not a redesign.

## Non-goals

- **No change to the visual identity** — palette, fonts (Newsreader/IBM Plex/Noto
  Serif KR), accent red `#c8332b`, dark-mode behavior all stay as-is.
- **No new color values** — Step 2 substitutions are value-preserving except the
  intended measure widening.
- **No backend / contract / infra / shared_db touch** — frontend CSS + markup +
  one `package.json` dependency removal only. No `openapi.json` regen.
- **No Tailwind utility-class migration** — we are not converting custom classes to
  Tailwind utilities; daisyUI is only being *removed*, not replaced.
- **No content/data changes** — MDX posts, review data, ratings untouched.

## Current state

- `src/styles/global.css` `@theme` defines only `--color-*` and `--font-*`. No
  spacing/radius/z-index/breakpoint scale.
- **z-index literals** scattered raw: `2` (`reviews.css:81`), `30/50/80/90/100`
  (`writer.css:1060/48/1089/1105/1464`), `60` + `40` (`[slug].astro` progress bar /
  size toggle).
- **Spotify green `#1DB954` hardcoded 5×** in `writer.css` (182, 183, 406, 407, 550).
- **Breakpoints mixed**: `640 / 720 / 760 / 880 / 1320` across stylesheets; 640/720/760
  serve near-identical roles. `global.css` already uses Tailwind `--breakpoint-lg` via
  `--theme(--breakpoint-lg)` for `.container`, so the mechanism exists but isn't applied
  consistently.
- **`daisyui` installed** in `package.json` (`^5.3.10`) + referenced in
  `tailwind.config.js`, with no observed usage in `src/` (to be confirmed in Step 3).
- **Content width**: read-view `.lfq-shell` = 720px (`[slug].astro:355`), writer
  `.surface` = 720px (`writer.css:134`), writer `.preview-surface` = 760px
  (`writer.css:141`). Editor and preview disagree; 720 reads cramped for long-form prose.
- **`writer.css`** is a single 1497-line file with at least one duplicated rule block
  (`.hdr-bnm`), while the React writer is split into 11 components under
  `src/components/writer/`.

## Target state

- `global.css` `@theme` additionally defines:
  - `--z-base / --z-sticky / --z-overlay / --z-toast` (mapping current 2 / 50 / 80-90 / 100;
    progress bar `60` + size toggle `40` + bubble toolbar `30` fold into the scale)
  - `--space-*` scale covering the recurring 8/10/12/14/24/28/32… values
  - `--radius-*` scale
  - `--color-spotify: #1DB954` (brand-fixed, no dark variant)
  - `--measure: 800px` and `--measure-wide: 1080px`
- `.lfq-shell`, `.surface`, `.preview-surface` all reference `var(--measure)` → unified 800px.
- `.lfq-hero` + `.lfq-tracklist` sit in a break-out wrapper reaching `var(--measure-wide)`.
- All `#1DB954` → `var(--color-spotify)`; all z-index literals → `--z-*`; breakpoints
  consolidated onto Tailwind `--breakpoint-*`.
- `daisyui` removed from `package.json` + `tailwind.config.js` (if Step 3 confirms unused).
- `writer.css` split into modules under `src/styles/writer/` (`chrome.css`, `subject.css`,
  `settings.css`, `preview.css`, …) aggregated via `@import`; duplicate rules removed.

## Steps

**Single-PR merge.** Every change is frontend-only, additive, and non-destructive
(reversible by `git revert`, no contract/infra/migration). Per CLAUDE.md rule 4, this
RFC **declares a single-PR merge** — the four steps are sequential commits in one PR
for bisectability, not separate prod-observe gates. The half-applied state of any one
step is not prod-breaking.

### Step 1 — Define token scales

Add `--z-*`, `--space-*`, `--radius-*`, `--color-spotify`, `--measure`, `--measure-wide`
to `global.css` `@theme`. Definition only — no existing rule changed, nothing references
the new tokens yet → zero visual diff.

**Verification**:
```
cd myblog_front && pnpm lint && pnpm exec astro check
# visual diff = 0 (no references added yet)
```

### Step 2 — Substitute + unify measure + break-out

- (a) Live-measure Pitchfork's article column in a browser (Playwright/Chrome, reuse
  memory `reference-playwright-e2e-pattern`). Confirm `--measure: 800px`; adjust only if
  the measurement strongly contradicts it, within a **760–840 guard**. Record any change
  in the Decisions log + PR body.
- (b) `.lfq-shell` (720), `.surface` (720), `.preview-surface` (760) → `var(--measure)`.
- (c) Add a break-out wrapper so `.lfq-hero` + `.lfq-tracklist` extend to `var(--measure-wide)`
  while prose stays at `--measure`.
- (d) `#1DB954` ×5 → `var(--color-spotify)`.
- (e) z-index literals → `--z-*` tokens.
- (f) breakpoints 640/720/760 → Tailwind `--breakpoint-*`.

**Verification**:
```
cd myblog_front && pnpm lint && pnpm exec astro check && pnpm build
```
Plus browser matrix click-through (light + dark): `/write`, `/blog/<review-slug>`,
`/blog/<plain-slug>`, `/reviews`, `/`. Before/after screenshots — the only intended
visual change is wider body + break-out hero; everything else is pixel-stable.

**Rollback**: `git revert` the commit; the substitution is 1:1 value-preserving except
the measure change, so revert restores exact prior layout.

### Step 3 — Resolve daisyUI

`grep -r daisyui src/` (+ class-name scan for daisyUI component classes). If unused
(expected): remove from `package.json` + `tailwind.config.js`, regenerate lockfile. If
used: skip removal, record the usage sites in the Decisions log instead.

**Verification**:
```
cd myblog_front && pnpm install && pnpm lint && pnpm exec astro check && pnpm build
# build proves no daisyUI class silently broke
```

**Rollback**: `git revert` + restore `pnpm-lock.yaml`.

### Step 4 — Split writer.css + dedup

Split `src/styles/writer.css` (1497 lines) into feature modules under
`src/styles/writer/` (e.g. `chrome.css`, `subject.css`, `settings.css`, `preview.css`),
re-aggregated via an `@import` index that `write-layout.astro` imports. Remove the
duplicate `.hdr-bnm` block and any other dupes found.

**Verification**:
```
cd myblog_front && pnpm lint && pnpm exec astro check && pnpm build
```
Built CSS byte-diff ≈ 0 aside from dedup; browser matrix on `/write` (light + dark)
pixel-stable vs. pre-split.

**Rollback**: `git revert` — imports collapse back to the monolith.

---

## Post-merge (single-PR)

- Prod smoke after auto-deploy on `https://www.ratemymusic.blog`. Auth-gated `/write`
  uses deployed CSS/JS chunk curl+grep, not in-DOM (memory:
  `reference-prod-smoke-auth-gated-front`). Quote result in PR comment.
- Drop the plan.md row; archive this RFC to `docs/archive/done/rfcs/`.

## Open questions

None remaining. Measure (800px + break-out) and writer.css split were resolved with the
user on 2026-06-01. The Step 2 Pitchfork measurement is a confirmation check, not an
open decision (guarded to 760–840).

## Decisions log

| Date | Decision | Step |
|------|----------|------|
| 2026-06-01 | Content measure = **800px** (≈76ch), Step 2 Pitchfork measure is sanity check only (guard 760–840) | 2 |
| 2026-06-01 | Adopt **break-out** wide elements (hero + tracklist → `--measure-wide` ~1080px) | 2 |
| 2026-06-01 | writer.css physical split **included** in this RFC (Step 4), not deferred | 4 |
| 2026-06-01 | **Single-PR merge** declared (rule-4 exception): all 4 steps frontend-only, additive, non-destructive | all |
| 2026-06-01 | Steps 1–4 implemented + locally verified (lint/astro check/build all green; browser matrix light+dark, desktop 1280 + mobile 375). Commits on `feat/FEAT-design-system-measure`: 50f8911 (S1), 15b7799 (S2), a59e7a1 (S3), dacfd3c (S4), 7dec8ba (S2 mobile-gutter fix). Pitchfork live-measure blocked (bot-gate); 800px stands per guard. Awaiting push approval. | all |
| 2026-06-01 | Breakpoint tokenization (Step 2f) **descoped**: CSS `@media` cannot consume custom properties, and writer/reviews stylesheets aren't run through Tailwind's `--theme()` processor, so 640/720/760 stay as literals. z-index/spotify/measure tokenization done; breakpoint scale would need a different mechanism (Sass-style or PostCSS). | 2 |
