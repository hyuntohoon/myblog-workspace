# FEAT-playback-bucket: make a bucket playable, and put the player where the audio is

- **Status**: draft
- **Owner**: 박지훈
- **Created**: 2026-08-02
- **Plan row**: `plan.md` → FEAT-playback-bucket
- **Origin**: 2026-08-02 owner brainstorm — "지금 플레이어가 프로필 개요에만 있는데, 버킷을 통해서
  재생 버킷을 활용하려 했다". An RFC + code audit found the feature is **half-built and shipped
  that way**: the write path (put tracks in a queue) is live in prod, the read path (play them)
  does not exist.
- **Depends on**: `FEAT-member-player` Step 5 (the `play()` ladder — front #334, merged
  2026-08-02 18:03 KST). This RFC consumes that ladder; it does not modify it.

---

## Goal

A bucket can be played. Pressing "이 버킷 재생 ▶" on any bucket starts its items, in bucket
order, as one continuous listening session — and the resulting player is reachable from
every page, not only `/profile?tab=overview`. Two halves of one thing: the bucket supplies
the queue, and the Pocket tray — already global, already bottom-anchored, already persisted —
supplies the player that shows and controls it.

## Non-goals

- A new bucket type or a new `item_type`. Owner decision D-A (below): **every** bucket is
  playable; `item_type='playback'` keeps exactly its current meaning (a duplicate-allowed
  queue entry) and gains no new privileges.
- Queue reordering, insert-at-position ("다음에 듣기"), or a save-queue-to-bucket bridge.
  Pocket Buckit D3 names Play next / Add to queue; only **Play now** is in scope here
  (6c "대기열에 추가" remains a `FEAT-member-player` candidate).
- Shuffle / repeat / volume (`FEAT-member-player` 6e candidate).
- Any change to the `play()` ladder's rung order, token minting, or device picker.
- Any synchronous Spotify call from a user-facing endpoint (hard rule 9). Every new server
  read in this RFC is a catalog DB read.
- Multi-user rollout decisions. This RFC inherits whatever tier `FEAT-member-player` has
  opened at implementation time (owner-only as of 2026-08-02).

## Current state (audited 2026-08-02, exact paths)

### The queue write path shipped without a read path

This is the defect, stated precisely. All three pieces exist and none of them are connected:

| Piece | Where | State |
|-------|-------|-------|
| Queue **storage** | `myblog_backend/app/services/bucket_service.py:661-732`; `app/api/schemas.py:192` | ✅ live. `item_type='playback'`, track FK, duplicate-allowed (D8), appended at the end, unknown track → 404 |
| Queue **write UI** | `myblog_front/src/components/member/pocket/AddToBucketMenu.tsx:225` | ✅ live. A track add offers **"재생 큐로 (중복 허용)"** next to "트랙으로" |
| Queue **playback** | — | ❌ **does not exist.** `playAll` / "전체 재생" / any multi-item play: 0 hits across `myblog_front/src` |

So a member can fill a bucket with queue entries today and there is no way to hear them.
Every play surface in the product is **single-item**: one album (`AlbumOverlay.tsx:77`,
`BucketBoard.tsx:2619`) or one track (`PocketTray.tsx:422`).

### What already exists and can be reused unchanged

- **The multi-track play primitive**: `play({ kind: 'uris', uris: string[] })`
  (`myblog_front/src/lib/spotifyPlayback.ts:321`) plays an arbitrary ordered track list. The
  lyrics queue jump (`lyrics/queueJump.ts:45`) already uses it in prod.
- **DB id → Spotify URI**: `GET /api/playback/resolve?type=album|track&id=`
  (`myblog_backend/app/api/routes/playback.py:67`, service at `playback_service.py`
  `resolve_uri`). A direct catalog read off `Album.spotify_id` / `Track.spotify_id` —
  documented in-code as rule-9-safe. **One item per request.**
- **Album → tracks**: `GET /api/music/albums/{id}` returns `tracks[]` with `spotify_id` and
  `track_no` (`myblog_front/src/lib/albumDetail.ts:19,44`). DB-only and already
  CloudFront-edge-cached (FEAT-music-edge-cache), with an in-memory + inflight-dedup cache
  in front of it.
- **Bucket-level action sheet**: `BucketBoard.tsx:2684` — an existing per-bucket sheet, the
  natural home for a "이 버킷 재생 ▶" entry (the per-album sheet at :2619 is its sibling).
- **A global, persisted, bottom-anchored island**: `PocketBuckit`
  (`layout.astro:76`, `transition:persist="pocket-buckit"`).

### The player is at one address; the audio is everywhere

`NowPlaying` renders from exactly one place — the overview widget registry,
`OverviewDash.tsx:483` (`case 'nowplaying'`). It is not mounted on the bucket tab, any other
profile tab, or any public page.

`FEAT-member-player` Step 5 (front #334, merged today) made the **audio** global:
`scripts/playbackPersist.client.ts` keeps the SDK iframe's browsing context alive across
`ClientRouter` navigations, and `lib/mediaSession.ts` publishes OS-level metadata and
transport handlers. The result is a new asymmetry, one day old:

> On `/reviews/` or `/genres/` the music plays and the OS media keys work, but there is no
> player anywhere on screen. The only in-page transport is back on `/profile?tab=overview`.

Rung 1 (remote Connect device) was always global — the audio is on another device entirely.
Step 5 made rung 2 global too. Neither made the **UI** global.

## Target state

### A bucket resolves to an ordered URI list, server-side

New backend route: **`GET /api/buckets/{bucket_id}/playback-uris`** → an ordered
`spotify:track:<id>` list plus a count of what was skipped. One request per play, all
expansion and ordering logic in one testable place.

Server-side rather than in the browser, for four reasons:

1. **One request instead of N.** A 10-album bucket resolved client-side is 10
   `/api/music/albums/{id}` calls plus per-track resolves; server-side it is one.
2. **Ordering is a single rule.** Bucket item order, then `track_no` within an expanded
   album. Expressible as one query, testable in pytest.
3. **Unplayable items get counted, not silently dropped.** Rows with no `spotify_id` are
   skipped and reported, so the UI can say "3곡은 재생할 수 없어요" instead of quietly
   playing a shorter list.
4. **The URI cap is enforced where it can be enforced** (OQ1).

Rule 9 holds by construction: `Album`/`Track`/`ReviewBucketItem` reads only, exactly like the
existing `resolve_uri` it generalizes.

### Item handling (owner decision D-C — expand albums to tracks)

| Bucket row | Becomes |
|------------|---------|
| `item_type='album'` | its DB tracks, ordered by `track_no`, each with a `spotify_id` |
| `item_type='track'` | one track URI |
| `item_type='playback'` | one track URI — **duplicates preserved** (D8); this is the whole point of the type |
| `item_type='review' \| 'snapshot' \| 'artist'` | skipped, counted |
| any row whose target has no `spotify_id` | skipped, counted |

Expanding albums (rather than playing them as a `context_uri`) is what lets a **mixed**
bucket — the normal case, since album and track rows already coexist — play as one
continuous session in bucket order. It costs the album's Spotify "context": Spotify will not
auto-continue past the end of a sent `uris` list. That is the same trade the lyrics queue
jump already made and the owner already accepted (`FEAT-lyrics-viewer-playback` OQ2).

### The Pocket tray becomes the player (owner decision D-B)

The tray is already global, bottom-anchored, persisted across navigation, and carries a ▶ per
item. It gains a **"지금 재생" row**: cover + title/artist + the transport and progress bar
`NowPlaying` already renders, plus a marker naming the bucket currently playing.

This is deliberately not a second bottom bar. A standalone global mini-player would put two
kinds of control at the bottom edge of every page, and the tray is the one the product
already committed to as the global entry surface (Pocket Buckit D6/D7 — the tray is the
canonical projection of the bucket tree).

Consequences that must be handled, not discovered:

- **Weight.** The tray must not become heavy for a member who never plays anything. The
  row appears only when there is something to show.
- **D9 (design is a user-selectable setting).** The tray's shell, weight and ordering are a
  persisted `design` setting with every value usable. A new row has to work in every one of
  them, or explicitly opt out of some.
- **`NowPlaying` belongs to another RFC.** See file ownership below.

### File ownership

`NowPlaying.tsx`, `playback.api.ts`, `spotifyPlayback.ts` and `LyricsOpenTarget` are owned by
`FEAT-member-player` (its Decisions log, 2026-07-19). This RFC **consumes** them and does not
restructure them: Step 3 extracts the presentational player body from `NowPlaying` so both
the overview widget and the tray render the same component. That extraction is the one
change inside the other stream's files, and it lands in this RFC's PR with the member-player
RFC cross-referenced — the same arrangement `FEAT-bucket-identity` B and
`FEAT-member-player` 6b used for the bucket-row entry (front #302/#303).

## Steps

### Step 1 — `GET /api/buckets/{id}/playback-uris` (backend)

Resolve one bucket to an ordered playable URI list. New route on the existing buckets router,
`require_cognito_token` + row-scoped by `user_id` like every other bucket read. Album
expansion, `track_no` ordering, duplicate preservation for `playback` rows, skip-and-count
for everything unplayable. Response: `{ uris: string[], skipped: int, truncated: bool }`.

New authed route ⇒ **`infra/apigateway.tf` entry required** (a missing route 404s; probe:
401 = live, 404 = missing). Contract change ⇒ regenerate `openapi.json` in backend, then
`tools/merge_openapi.py` in workspace.

**Verification**:
```
pytest                       # incl. mixed-bucket ordering, duplicate preservation,
                             # skip counting, empty bucket, foreign bucket → 404
terraform plan               # apigateway stack clean
scripts/smoke.sh             # anon 401; member 200 on own bucket; 404 on someone else's
```

---

### Step 2 — "이 버킷 재생 ▶" (front)

The bucket action sheet (`BucketBoard.tsx:2684`) and the Pocket tray drawer head each gain a
play entry: fetch the URI list, hand it to `play({ kind: 'uris', uris })`, and surface the
outcome with the flash idiom already used at `BucketBoard.tsx:2619` — including the
rung-2 "이 브라우저에서 재생 중 (음질 제한)" message and the `disconnected` branch. An empty
or fully-skipped bucket says so instead of calling `play()`.

**Verification**: `pnpm lint` + `pnpm exec astro check` + `pnpm test`; CDP fetch-mocked
matrix (mixed bucket order, all-skipped bucket, empty bucket, rung-1 vs rung-2 message,
disconnected, mobile 390); owner real-device clickthrough — a mixed bucket plays in bucket
order on a real Connect device.

---

### Step 3 — the tray becomes the player (front)

Extract the presentational player body from `NowPlaying.tsx` and mount it as a "지금 재생" row
in the Pocket tray, showing which bucket is playing. The overview widget keeps rendering the
same component — no visual change there, which is the regression bar for this step.

Blast radius is the whole tray, which is on every page, so this step carries its own
regression pass over the D9 design variants and over the tray's existing drag/drop and
drawer behavior.

**Verification**: `pnpm lint` + `pnpm exec astro check` + `pnpm test`; overview widget
pixel-unchanged; CDP across the D9 design values + mobile 390 with no horizontal overflow;
playback continues and the row stays correct across ≥3 client-side navigations; owner
real-browser clickthrough.

---

### Step 4 (candidate, not scoped) — the queue as a surface

Recorded so it is not re-invented: a queue panel listing what is playing next, "다음에 듣기"
(`FEAT-member-player` 6c), reorder, and a save-queue-to-bucket bridge (a pattern the
pocket-buckit research flagged as useful — YouTube Music's "Save queue to playlist").
Owner selects a subset if and when this is promoted.

## Open questions

1. **The `uris` cap — UNMEASURED, blocks Step 1's `truncated` behavior.** Spotify's `PUT
   /me/player/play` is documented to accept on the order of 100 URIs; **this was not
   measured here** (no AWS CLI in this session's container, so no SSM token could be minted —
   the recipe in `FEAT-member-player` "Measured 2026-08-02" is re-runnable where creds
   exist). Measure before implementing, then decide: hard-truncate with a notice, or refuse
   to play an oversized bucket. Do not guess the number.
2. **What "재생 중인 버킷" means after the fact** — blocks Step 3's marker. Once a URI list is
   sent, Spotify owns the session; the user can skip out of it in the Spotify app and we will
   not know. Options: treat it as a client-side session label that clears on any external
   change, or drop the marker. D28 (no polling) forbids watching for drift.
3. **Album expansion vs. album context, revisited at scale** — a bucket of 20 albums is
   ~200 tracks, which will exceed the cap in OQ1 regardless of the answer. Does an
   albums-only bucket fall back to `context_uri` for its first album, or does the cap notice
   simply apply? Blocks Step 1's truncation rule; interacts with D-C.
4. **Tray weight under D9** — blocks Step 3. Does the "지금 재생" row apply to every design
   value, or do some opt out? Owner picks at implementation time, from mockups.

## Decisions log

| Date | Decision | Step |
|------|----------|------|
| 2026-08-02 | **D-A (owner): every bucket is playable — no new bucket type.** "이 버킷 재생 ▶" attaches to any bucket; `item_type='playback'` keeps its current meaning (duplicate-allowed queue entry) and gains no privileges. Rejected: a dedicated `playback` bucket type (backend enum + migration + seeding, and existing buckets would stay unplayable) | 1, 2 |
| 2026-08-02 | **D-B (owner): the player UI goes into the Pocket tray**, not a separate global mini-bar and not more profile tabs. The tray is already global, bottom-anchored and persisted, so this adds no new page chrome and puts the queue and its controls in one place. Rejected: a standalone persisted mini-player (two kinds of bottom-edge control on every page); profile-tabs-only (leaves Step 5's audio-global / UI-local asymmetry in place) | 3 |
| 2026-08-02 | **D-C (owner): album rows expand to their tracks** rather than playing as a `context_uri`, so a mixed album+track bucket plays as one continuous session in bucket order. Accepted cost: the album's Spotify context is replaced, so playback stops at the end of the sent list — the same trade already accepted in `FEAT-lyrics-viewer-playback` OQ2 | 1 |
| 2026-08-02 | **Audit finding recorded as the RFC's premise**: the queue write path is live in prod (`AddToBucketMenu` "재생 큐로", `item_type='playback'` storage) with no read path anywhere — a member can fill a queue that nothing can play. This RFC's Steps 1–2 close that specific dead end; Step 3 is the placement half of the same brainstorm | — |
| 2026-08-02 | Resolution is **server-side** (`GET /api/buckets/{id}/playback-uris`) rather than a client-side fan-out over `/api/music/albums/{id}` + `/api/playback/resolve`: one request instead of N, ordering as one testable rule, skipped items counted rather than silently dropped, and the OQ1 cap enforceable. Rule 9 holds — catalog DB reads only, generalizing the existing `resolve_uri` | 1 |
