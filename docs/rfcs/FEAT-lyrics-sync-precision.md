# FEAT-lyrics-sync-precision: remove the fixed sync lead and re-anchor on events

- **Status**: in-progress (all three steps resolved — outstanding: the owner's real-device listen check, see below. Promotion to `done` is the owner's call.)
- **Owner**: 오너
- **Created**: 2026-08-01
- **Plan row**: `plan.md` → FEAT-lyrics-sync-precision

---

## Goal

The lyrics viewer's line advance stops relying on a blanket `SYNC_LEAD_MS = 300` fixed offset. The two error sources that constant was silently cancelling — the 250 ms polling grain and the 350 ms opacity ramp — are removed structurally, leaving a single small constant that is honestly labelled as taste, not latency. Separately, the viewer stops running a clock that has silently diverged: playback discontinuities (pause / resume / track change) re-anchor the estimate the moment they happen, driven by events the browser already receives, with **no polling added** (D28 upheld).

## Non-goals

- **No polling.** No periodic re-read of `GET /v1/me/player` while the viewer is open. Playback rate is 1.0× and browser-vs-device clock drift is ~10 ms over a 4-minute track, so a correct anchor stays correct until an *event* invalidates it. Re-anchoring is event-driven only. (Owner decision 2026-08-01, reversing a mid-brainstorm proposal for adaptive polling; D28 stands.)
- **No stored/learned offset.** No "이게 맞다" calibration button, no per-device or per-track offset persisted in localStorage or the DB. A recorded correction bakes in that moment's network and device conditions and cannot generalize. (Owner decision 2026-08-01.)
- **No server change.** No migration, no new route, no contract change, no `infra/apigateway.tf` entry. Frontend only.
- **No modelling of Spotify's own progress staleness.** Step 2 makes the residual (predicted position vs. actual position at each event re-anchor) observable; acting on it is explicitly deferred. (Owner decision 2026-08-01 — "3번 빼자".)
- **No playback controls or queue UI.** That is `FEAT-lyrics-viewer-playback`, a separate RFC. This RFC only *consumes* the command signal that already exists.
- **No change to the manual browse/suspend model** (`FEAT-lyrics-viewer-controls` Step 1) or to tap-to-focus re-anchoring.

## Current state

All in `myblog_front/src/components/member/lyrics/LyricsViewer.tsx` unless noted.

**The estimate.** `anchor: useRef<ClockAnchor | null>` holds `{ ms, wallMs }`. The focus line is computed as:

```
estimatedMs = estimateMs(anchor) + SYNC_LEAD_MS      // = anchor.ms + (performance.now() - anchor.wallMs) + 300
focus       = focusIndexForMs(segs, estimatedMs)     // last segment whose start_ms <= estimatedMs
```

`estimateMs` lives in `@lib/clockEstimate` (`myblog_front/src/lib/clockEstimate.ts`) and is shared with `NowPlaying.tsx` (member-player Step 3).

**The loop.** `LyricsViewer.tsx:593-622` — a `window.setInterval(tick, 250)` (`ESTIMATE_INTERVAL_MS`). Each tick recomputes `estimatedMs`, calls `setFocus` only when the index changes, and (live entries only) fires the one-shot end-of-track re-sync when `estimatedMs >= durationMs + END_GRACE_MS`. The tick returns early while `document.hidden`.

**The fixed lead.** `LyricsViewer.tsx:98` — `const SYNC_LEAD_MS = 300`, documented as covering "Spotify's own progress staleness and the ≤250ms tick grain". Measured decomposition (2026-08-01):

| Source | Size | Direction |
|---|---|---|
| 250 ms tick grain | +125 ms mean, +250 ms worst | always late |
| `.lyv-line` `transition: opacity 0.35s` (`myblog_front/src/styles/member/layout.css:832`) — perceived midpoint | ≈ +175 ms | always late |
| React commit | ~10–30 ms (unmeasured) | late |
| Spotify `progress_ms` staleness | unmeasured | unknown |
| Request RTT | already midpoint-corrected in `readLivePlayback` | ± |
| Audio output path (Bluetooth ≈ 150–250 ms) | 0–250 ms | late, **not API-observable** |
| LRC file's own offset | per-file | ± |
| LRC `[offset:]` tag dropped by `parse_lrc` | **5 of 11,019 synced rows** (prod, 2026-08-01) | negligible — dead hypothesis |

125 + 175 ≈ 300. The constant is very likely an eyeball cancellation of the first two rows, not a latency correction. **Deleting it without removing those two first would make the viewer read *later* than it does today.**

**The anchor sources.** `readLivePlayback()` (`playback.api.ts`) returns `progressMs` + `readAtMs` (request-window midpoint) + `durationMs` + `deviceName`. It is called on: viewer open (via the entry's one-shot, handed in as `initialProgressMs`/`initialProgressAtMs`), manual ↻ (`refresh()`, `LyricsViewer.tsx:433`), and once per detected end-of-track. `applyAnchor()` (`LyricsViewer.tsx:350`) re-seeds from a fresh position. Tap-to-focus re-anchors to the tapped segment's `start_ms` (`moveFocusTo`, `LyricsViewer.tsx:499`).

**What is not handled at all.**

1. **Pause is invisible to the viewer.** There is no `paused` state and no `running` flag in the viewer's loop — unlike `NowPlaying.tsx:681` which passes `!paused` to `useClockEstimate`. Pause for 30 s and the viewer is 30 s ahead until something else fires. The end-of-track re-sync partially rescues this (the estimate hits `durationMs` early, fires one read, re-anchors) but `endSynced` is one-shot per anchor seed, so a second pause is unrecoverable without manual ↻.
2. **Tab return does not re-verify.** `tick` returns early while `document.hidden`, but the anchor keeps ageing in wall-clock — i.e. the code assumes playback continued. Leaving the tab to operate Spotify elsewhere is precisely the case where that assumption breaks.
3. **Our own playback commands are ignored.** `MYBLOG_PLAYBACK_CHANGED` (`@lib/spotifyPlayback:34`) is dispatched after every successful `sendPlayerCommand`. `NowPlaying.tsx:524` subscribes. The lyrics viewer does not.

## Target state

```
estimatedMs = anchor.ms + (performance.now() - anchor.wallMs) + PERCEPTUAL_LEAD_MS   // ≈ 80, taste
```

- No 250 ms interval. A single `setTimeout` is scheduled to the *exact* wall instant the next segment's `start_ms` is reached; on fire it advances the focus and schedules the next one. Crossing error drops from 0–250 ms to one frame. The end-of-track re-sync is scheduled the same way.
- `.lyv-line` gains a fast attack (~120 ms into focus) while keeping the slow release (0.35 s out of focus), so the line reads as "now" at its leading edge rather than at the midpoint of a symmetric ramp.
- The viewer holds a `playing` flag. While paused the estimate is frozen at the anchor position and no timer is armed; on resume the anchor is re-seeded at the resume instant.
- Re-anchor fires on: `MYBLOG_PLAYBACK_CHANGED`, `visibilitychange` → visible, end-of-track, manual ↻, tap-to-focus. Nothing else. No timer polls playback state.
- Every event-driven read logs `predicted − actual` at `debug` level. This is the accuracy measurement; nothing consumes it yet.

## Steps

Steps are sequential but each is independently mergeable and independently revertable. Owner granted go-ahead for all steps in one session (2026-08-01), so rule 4's per-step gate is satisfied by explicit approval, not by parallel-safety.

### Step 1 — Boundary-scheduled focus + fast attack + honest lead constant

> ✅ Done 2026-08-01 — front #325, merge SHA `0f5748b` (shipped with Step 2 in one PR: Step 2's `playing` flag is a scheduler guard, so splitting them would have merged a scheduler that cannot be paused). Deploy run `30647516837` succeeded; prod bundle `SelfDashboard.DnJ4MT3o.js` carries the new code and no longer contains `SYNC_LEAD_MS`, and prod CSS `collection.B36CYv6u.css` serves `.lyv-line.is-focus{…transition:opacity .12s ease-out,…}`.
>
> **Measured on the real DOM** (CDP against the actual `/members/?me` dashboard, with only `api.spotify.com/v1/me/player` stubbed by a controllable fake player), line flip vs. the stub's true position:
>
> ```
> toLine 4  flip at 12935ms   line starts 13000ms   lead 65ms
> toLine 5  flip at 15935ms   line starts 16000ms   lead 65ms
> toLine 6  flip at 18935ms   line starts 19000ms   lead 65ms
> toLine 7  flip at 21935ms   line starts 22000ms   lead 65ms
> ```
>
> **Zero variance.** 65 rather than 80 is the rAF sampler costing ~1 frame. The old interval's spread was 0–250 ms by construction, so this is the structural claim confirmed by measurement rather than argument. Computed style confirmed the asymmetry: focused line `0.12s`, every other line `0.35s`.

Replaces the 250 ms interval with next-boundary `setTimeout` scheduling, splits the line transition into fast-attack / slow-release, and re-derives the residual lead constant.

**Changes**

- `LyricsViewer.tsx`: delete the `setInterval(tick, ESTIMATE_INTERVAL_MS)` loop. Introduce a scheduler that, given the current anchor and focus, computes `msUntilNextBoundary = segs[focus+1].start_ms - estimatedNow` and arms one `setTimeout`. On fire: advance focus by one, re-arm. Re-arm from scratch whenever the anchor, `suspended`, `segs`, or the lead constant changes. Clear on unmount and while suspended.
  - Gap segments (`text === ''`) keep their own boundaries — the focus unit is unchanged.
  - Segments with `start_ms == null` (mixed plain/synced rows) are skipped as boundaries; the next *timed* segment is the target.
  - A boundary already in the past (anchor seeded mid-track) resolves by computing the focus directly from `focusIndexForMs` before arming, exactly as today.
  - `setTimeout` is clamped to ~1 s granularity in background tabs; the scheduler therefore re-derives the focus from the anchor on every fire and on `visibilitychange`, so a throttled timer can only be late, never wrong.
  - Long instrumental gaps produce long timers. Drift does not accumulate because every fire recomputes from the anchor, not from an accumulator.
- `myblog_front/src/styles/member/layout.css`: `.lyv-line.is-focus` gets its own shorter `transition` (~120 ms) so entering focus is fast while leaving focus keeps the base 0.35 s. `.lyv-list`'s 0.45 s transform is left alone (it is position motion, not the "which line is now" signal). The `prefers-reduced-motion` block is unchanged.
- `SYNC_LEAD_MS = 300` → `PERCEPTUAL_LEAD_MS = 80`, with a comment stating plainly that it is a taste constant (deliberate early flip so the line can be read as it starts), **not** a latency correction, and that the latency terms it used to hide are now removed at their source.

**Verification**

```
cd myblog_front
pnpm lint && pnpm exec astro check && pnpm test
```

Plus a real-browser clickthrough (front UI change → DoD): open the viewer on a synced track and confirm lines advance, browse/suspend + countdown ring still work, tap-to-focus still re-anchors, and reduced-motion still disables animation.

**Rollback**: revert the commit. No state is persisted and no contract changed.

---

### Step 2 — Event-driven re-anchoring + pause awareness

> ✅ Done 2026-08-01 — front #325, merge SHA `0f5748b`. Prod bundle carries `[lyrics-sync] residual` and `state:l.is_playing?"playing":"paused"`.
>
> **Discontinuities measured mid-track** (the first run happened to freeze on the *last* line, where "did not advance" is trivially true — redone):
>
> ```
> seek backwards to 5200ms  → re-anchored to line 1        (expected 1)  PASS
> pause at line 2, hold 7s  → still line 2, 2 boundaries passed          PASS
> resume                    → line 3                       (expected 3)  PASS
> ```
>
> Resume lands on truth rather than on a clock that kept running through the pause — the point of carrying the position on `paused`.
>
> **Request floor**, attributed per subscriber: 8 events in ~500 ms → 1 viewer read; 2 events 1.7 s apart → 1 viewer read; `visibilitychange` → 1 viewer read.
>
> **Deviation from the RFC as written, and why.** The RFC planned to treat an `idle` result at a previously-playing anchor as "paused". That cannot freeze *accurately* — `idle` carries no position, so the frozen line would have been guessed from an already-ageing estimate. Instead `readLivePlayback` gained a real `paused` state carrying the held position. The cost is a shared-type change, so all three consumers were swept rather than left to a default: `NowPlaying.applyLive` keeps its idle behavior explicitly, and **`NowPlayingLyricsEntry` was routing the new state into its `확인 실패` branch** — a real latent bug in the change, caught by the sweep and not by the type checker.
>
> **Known cost, recorded not hidden**: with the viewer open on the dashboard, one transport command now causes **two** reads — `NowPlaying`'s pre-existing 1:1 confirmation read plus the viewer's. Attributed by closing the viewer and re-measuring (2 → 1). Both are 1:1 with a user action, so it is not a storm; it is a natural dedupe target once `FEAT-lyrics-viewer-playback` gives the viewer its own transport buttons.

Teaches the viewer that playback can stop or jump, using signals the browser already delivers.

**Changes**

- `LyricsViewer.tsx`: add a `playing` flag (seeded `true` for live entries with a position, `false` when a read reports non-playing). While `!playing`, no timer is armed and the focus holds at the anchor position — the same freeze semantics `useClockEstimate` already implements for `NowPlaying`.
- Subscribe to `MYBLOG_PLAYBACK_CHANGED` (live entries only). On fire, run one `readLivePlayback()` and re-anchor through the existing `applyAnchor` / track-swap paths. This is the same one-shot read the manual ↻ already performs — no new request *kind*, only a new trigger.
- Subscribe to `visibilitychange`. On becoming visible after being hidden, run one `readLivePlayback()` and re-anchor. Guard with a short floor (no second read within ~2 s) so tab-flicking cannot burst.
- `readLivePlayback()` currently collapses paused playback into `state: 'idle'` (`playback.api.ts:111` — `!body?.is_playing` → idle). Keep the existing `idle` semantics for the entry-visibility contract, but the viewer treats an `idle` result arriving at a *previously playing* anchor as "paused": freeze, keep the lyrics on screen, no notice change. Only an `idle` result with no prior anchor keeps today's "지금 재생 중인 곡이 없어요".
- Log `predicted − actual` (`debug` level, `LyricsViewer`) on every event-driven re-anchor that lands on the same track. This is the accuracy series; nothing reads it yet.

**Residual gap, accepted**: the owner operates Spotify on a phone while this tab stays visible on another machine. No event reaches us. Mitigations already present: end-of-track re-sync and the manual ↻. Widening this would require polling, which is out of scope by decision.

**Verification**

```
cd myblog_front
pnpm lint && pnpm exec astro check && pnpm test
```

Plus a real-browser clickthrough: pause from the member player bar with the viewer open → lyrics freeze; resume → lyrics resume at the right line; switch tab away and back → lyrics land on the correct line.

**Rollback**: revert the commit. Listeners are added in `useEffect` cleanups; no persisted state.

---

### Step 3 — Measure the in-page output latency (go/no-go)

> ❌ **NO-GO 2026-08-01 — measured, then closed. Ships no code.** The step was written to be its own answer, and the answer is no.
>
> ```
> baseLatency     0.00533 s   (5.3 ms)
> outputLatency   0.016   s   (16 ms)  — steady across suspended / resumed / actively rendering
> sinkId          unsupported
> ```
>
> 16 ms is an order of magnitude below the terms Step 1 removed (125 ms, 175 ms), so even a perfect reading would not be worth an estimate term. But the decisive objection is **structural, not empirical**: Spotify's SDK does not play through our `AudioContext`, so this measures our own graph, not Spotify's pipeline — and for Connect remote playback, the dominant case, the audio is not even on this machine. Bluetooth A2DP delay is 150–250 ms; an API reporting 16 ms for our own sink cannot see it. `sinkId` being unsupported means we could not even confirm which output device the context was bound to.
>
> Scope of the measurement, stated so it is not over-read: one machine, one output path, Chrome. The structural objection holds regardless of hardware, which is why no Bluetooth re-test was pursued.
>
> **Consequence**: audio output delay is now a recorded, accepted limit of this RFC rather than an open thread. Nothing in the shipped system tries to correct it.

The one error source that cannot be derived from the API is how long after `progress_ms` the sound actually reaches the owner's ears. It is unobservable for Spotify Connect remote playback. It *may* be observable when the browser itself is the active device (the `Buckit` SDK device in `@lib/spotifyPlayback`), via `AudioContext.outputLatency` / `baseLatency`.

**This step is a measurement first.** Instrument and read the values on the owner's real devices (wired, Bluetooth, in-page SDK device active vs. not). Then:

- If the values are meaningful and move with the output path → add them to the estimate, but only while the in-page SDK device is the active device.
- If the values are 0, constant, or unrelated to the actual output path → **delete the step, report the measurement, and close it.** Do not ship a correction we cannot justify.

**Verification**

```
cd myblog_front
pnpm lint && pnpm exec astro check && pnpm test
```

Plus the measurement itself, quoted in the PR: `outputLatency` / `baseLatency` readings per output path, and whether they differ.

**Rollback**: revert the commit, or never merge if the measurement is a no-go.

---

## Open questions

1. ~~**`PERCEPTUAL_LEAD_MS` final value**~~ — **STILL OPEN, but the question was malformed and is now two questions.** Shipped at 80 ms. Everything measurable was measured; what remains cannot be: whether it *feels* right is the owner's ear on the owner's hardware.

   **2026-08-02 — the owner reported the lyrics running early, on the `flat` style. That was not taste drifting; it was a real defect this RFC shipped.** 80 was derived as "~60 ms midpoint of the new 120 ms attack + ~20 ms deliberate lead" — but **only `blur` has an attack.** `blur` announces "now" by fading opacity over that ramp; `flat` announces it in colour, which snaps with no ramp at all (`layout.css` — deliberate, it is the Apple-Music look the owner asked for, and the Step 1 comment even notes the flat variant "never had this lag"). Applying one number to both therefore left `flat` leading by the full 80 ms while `blur` led by ~20 ms net. Split in front #333 into `BLUR_LEAD_MS = 80` / `FLAT_LEAD_MS = 20`, with the relationship pinned by a unit test rather than by prose. The look was not touched — only the mis-calibrated number.

   **The methodological point, because this RFC is about exactly this:** Step 1's own reasoning named the attack midpoint as a *term in the sum*, and the code then applied the sum to a variant where that term is zero. A constant justified by a mechanism must be scoped to where the mechanism exists. The Step 1 comment claiming the change "converges the two variants onto the same timing" was the tell, and it was wrong: 120 ms and 0 ms are not converged.

   *Remaining:* the owner re-listens on **flat at 20 ms** and on **blur at 80 ms** — two judgements now, not one. Feels late → raise; flips early → lower. Each is still a one-line change.
2. ~~**Does `AudioContext.outputLatency` reflect the actual output path?**~~ — **ANSWERED 2026-08-01: no.** See Step 3.

## Not verified, and why

The live path against **real Spotify playback** was never exercised locally: the viewer only opens while something is actually playing on the owner's account, and the CDP run stubbed `api.spotify.com/v1/me/player` with a controllable fake player. Everything downstream of that stub — the scheduler, the freeze, the re-anchor, the CSS — ran on the real DOM in the real dashboard. What the stub cannot tell us is whether Spotify's own `progress_ms` is stale in practice.

That is exactly what Step 2's residual log is for: `[lyrics-sync] residual` in the browser console, on every event re-anchor. It is now collecting in prod, from real use, and nothing acts on it — by design (see the Decisions log).

## Decisions log

| Date | Decision | Step |
|------|----------|------|
| 2026-08-01 | The fixed 300 ms is a cancellation of tick grain (+125) and animation ramp (+175), not a latency correction. Remove both sources; keep ~80 ms labelled as taste. | 1 |
| 2026-08-01 | LRC `[offset:]` tags are a dead hypothesis — 5 of 11,019 synced prod rows carry one. Do not build for it. | — |
| 2026-08-01 | Owner: periodic re-sync is wrong ("싱크는 한번 맞으면 안 바뀌는게 맞아"). Playback is 1.0× and drift is ~10 ms per track, so only *events* invalidate an anchor. Adaptive polling proposal dropped; D28 upheld unchanged. | 2 |
| 2026-08-01 | Owner: a stored "이게 맞다" calibration is not viable — network and situation vary, so a recorded value bakes in one moment. Learned/persisted offsets and their server-side sharing dropped entirely; the multi-user propagation concern disappears with them. | — |
| 2026-08-01 | Owner: drop live staleness estimation ("3번 빼자"). The residual is still logged by Step 2, so acting on it later needs data, not a rewrite. | 2 |
| 2026-08-01 | Owner: playback controls + queue split into `FEAT-lyrics-viewer-playback` (draft). This RFC consumes `MYBLOG_PLAYBACK_CHANGED`, which already exists, so it does not wait on that RFC. | 2 |
| 2026-08-01 | Owner approved all steps in one session (rule 4 satisfied by explicit approval) and promoted this RFC to `accepted` (rule 5). | — |
| 2026-08-01 | Steps 1+2 shipped in ONE PR (front #325, `0f5748b`) rather than two: Step 2's `playing` flag is a guard on Step 1's scheduler, so merging Step 1 alone would have put a scheduler in prod that cannot be paused. | 1, 2 |
| 2026-08-01 | `readLivePlayback` gained a real `paused` state instead of the RFC's planned "treat `idle` as paused". `idle` carries no position, so freezing on it means guessing from an ageing estimate — the opposite of this RFC's point. Cost paid: a shared-type change swept across all three consumers, which surfaced `NowPlayingLyricsEntry` mis-routing the new state into its failure branch. | 2 |
| 2026-08-01 | **Step 3 NO-GO.** `outputLatency` = 16 ms here, but the disqualifier is structural: the Spotify SDK does not play through our `AudioContext`, and under Connect the audio is on another device entirely. Audio output delay becomes a recorded accepted limit, not an open thread. | 3 |
| 2026-08-01 | Two reads per transport command while the viewer is open (`NowPlaying`'s + the viewer's) accepted as-is and recorded, rather than deduped now — both are 1:1 with a user action, and `FEAT-lyrics-viewer-playback` is the natural place to collapse them. | 2 |
