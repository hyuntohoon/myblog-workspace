# ARCH-playback-queue-atomic-replace: one request, one transaction for ▶

- **Status**: accepted — owner approved in-session 2026-10-07; Step 1 in progress
- **Owner**: site owner
- **Created**: 2026-10-07
- **Plan row**: `docs/plan.md` → ARCH-playback-queue-atomic-replace
- **Origin**: `OPS-project-stabilization` Step 2A, open item 3 ("Popstar ▶ started Backwards"),
  reproduced 2026-10-07. The owner chose a structural fix over a front-only retry patch.

---

## Goal

Pressing ▶ on an album or track replaces the member's playback queue **atomically on the server**
and returns rows that already carry their Spotify URI. One ▶ is one backend request. A partial
failure leaves the queue either fully replaced or untouched, never a mix. The Spotify tail sent to
`PUT /me/player/play` always equals the visible queue from the pressed row onward.

## Non-goals

- Raising the account Lambda concurrency limit (owner, Service Quotas — tracked in
  `OPS-project-stabilization`). This RFC must hold at concurrency 10.
- The YouTube resolver path (`provider=youtube` in `lib/playback/uris.ts`). Its mappings are
  revocable and stay resolved at play time.
- Changing what ▶ means (replace, not append — owner decision 2026-08-03) or the Undo UX.
- The SDK `ready` timeout and failure notices (`OPS-project-stabilization` 2A open item 1).
- Queue reorder/delete paths other than replace and Undo.

## Current state

Read against origin/main on 2026-10-07: backend `0e2014a`, front `af440e9`, ws `03c41d8`.

**The replace is orchestrated by the browser as independent requests.**
`myblog_front/src/lib/playback/session.ts` `replaceQueueAndPlay` → `rewriteQueue`:

1. `POST /api/buckets/{id}/items` with `source_album_id` (backend `expand_album_tracks` appends
   the album's tracks, `buckets.py` `add_item`).
2. `GET /api/buckets` to learn the new item ids.
3. Optimistic local prune of the old rows, then `deleteRows` — one
   `DELETE /api/buckets/{id}/items/{item_id}` per displaced row.
4. Concurrently, `playFrom(0)` → `resolveTail` → `Promise.all` of one
   `GET /api/playback/resolve?type=track&id=…` per uncached row.

This shape was a deliberate Step 6b trade-off ("there is no bulk delete ⇒ write first, delete
second", `docs/archive/done/rfcs/FEAT-playback-bucket-player.md` decisions 2026-08-04). The fix that
removes the resolver — surface `tracks.spotify_id` on playback items — was recorded as a follow-up
on 2026-08-03 and never taken.

**Measured 2026-10-07, owner Chrome, one tab, one press of "이 앨범 재생 ▶" on *Popstar* (16
tracks), replacing a 14-track queue:**

| Request group | Sent | 503 (Lambda throttle) |
|---|---|---|
| `resolve` | 16 at once | **8** |
| `DELETE …/items/{id}` | 14 | **4** (the first four) |
| `PUT /me/player/play` | 1 | 0 (204, rung 1) |

Audio was correct (Sunglasses, track 1). The queue was not. Read-only DB check afterwards:
positions 390–393 were the four undeleted *QRÖMELIFE* rows (**Backwards (feat. T.I.)**, BA,
Hit-A-Lik, Away), followed by the 16 *Popstar* rows. `deleteRows` refetches after a failure, so
the old rows reappear **at the head of the queue**, and anything that later plays "from the top"
starts *Backwards*. That matches the 2026-10-07 report. The original press that day could not be
reconstructed; the backend log group held no events for the window.

Two further consequences of the same shape:

- `resolveTail` drops `transient` rows from the tail without a notice. Spotify then holds a
  shorter list than the screen, and natural advance skips tracks the member can see.
- Each ▶ costs about `1 + 1 + N + N` requests (≈ 32 for a 16-track album over a 14-row queue),
  fired in bursts against an account limit of 10 concurrent executions.

**Not reproduced: "⏭ sent no request."** After the replace above, ⏭ sent
`PUT /me/player/play` starting at track 2 as expected. One false reproduction came from clicking
⏭ while the album overlay's backdrop covered the bar. That is recorded so nobody repeats it.

## Target state

- **Backend:** `PUT /api/buckets/{id}/playback-queue` with a body of either `{ "album_id": … }` or
  `{ "track_ids": [...] }`. One DB transaction: lock the bucket row, read the displaced rows' track
  ids, delete every `item_type='playback'` row, insert the new rows in album order (the
  `expand_album_tracks` ordering) or in request order. It returns the new rows (item id, track id,
  `spotify_uri`) and `displaced_track_ids`. The same gates as today apply: owner of the bucket,
  playback type, not a system bucket, and the daily cap (OQ2).
- **Tree payload:** playback items in `GET /api/buckets` carry `spotify_uri`
  (`spotify:track:<tracks.spotify_id>`; the column is `NOT NULL UNIQUE`).
- **Front:** `replaceQueueAndPlay` and `undoReplace` call the new endpoint once, then play URIs
  taken straight from the rows. The Spotify branch of `resolveTail` reads the payload, so it costs
  zero requests even cold. `rewriteQueue`/`deleteRows` are removed. The YouTube branch is unchanged.
- **Failure semantics:** if the endpoint fails, the queue is untouched and the existing
  `REPLACE_FAILED` notice shows. If it succeeds and play fails, the queue is replaced and Undo is
  offered (unchanged from today).

## Steps

Additive change. Merge order per `docs/contracts/README.md`: service → workspace contract → front.

### Step 1 — Backend endpoint + payload field

- `BucketService.replace_playback_queue(...)` in one transaction. Delete and insert in a stable
  order. No external call inside the transaction.
- Route in `app/api/routes/buckets.py`. `spotify_uri` on playback items in the tree response.
- `openapi.json` regenerated and committed.
- **`infra/apigateway.tf`:** new route `PUT /api/buckets/{id}/playback-queue` behind the Cognito
  authorizer (`buckets_patch` pattern). Infra merge does not auto-apply; a human applies it before
  Step 3 ships.
- Mandatory: `reviewer` (contract + infra touch) and `security-review` (new authenticated mutation,
  user input).

**Verification:**
- Real-DB integration test: replace an N-row queue. Inject a failure after the delete and before
  the insert; assert the original rows survive unchanged. Mutation-test it: removing the
  transaction boundary must fail it.
- Cross-member test: member B's bucket id → 404, no rows touched.
- Required checks `check`, `test`, `contract`, `integration` green; `terraform plan` shows exactly
  one new route (it reuses the shared `backend` integration) and no other drift; post-apply `curl` of the new route without a
  JWT → 401, not 404.

**Rollback:** revert the PR. The old endpoints are untouched, so the shipped front keeps working.

### Step 2 — Workspace contract

Merge the regenerated contract per `docs/contracts/README.md`; `workspace-check` re-merges from
service `main`.

### Step 3 — Front switch

- `replaceQueueAndPlay` / `undoReplace` → the new endpoint. Delete `rewriteQueue` and `deleteRows`.
- `resolveTail` (Spotify) reads `spotify_uri` from the row. Regenerate and commit `api.gen.ts`.
- Unit tests: one request per ▶, no `resolve` call for Spotify rows, endpoint failure ⇒ queue
  untouched + `REPLACE_FAILED`. Stubs must model response latency, not answer instantly.
  Mutation-test each new test.

**Verification:**
- `pnpm lint`, `astro check`, `pnpm test`.
- Real-browser clickthrough against prod after deploy, with the 2026-10-07 recipe: one ▶ on a
  16-track album over a 14-row queue. Pass = exactly one backend mutation request, zero `resolve`
  requests, DB queue = exactly the 16 new rows, `PUT /play` carries 16 URIs. Control: the same
  press on the pre-deploy build shows the throttled shape recorded above.

**Rollback:** revert the front PR; the Step 1 endpoint stays, unused.

## Open questions

1. **Endpoint shape** — a dedicated `PUT …/playback-queue` (recommended: idempotent by
   construction, own authorizer line) vs. a `replace: true` flag on `POST …/items` (no new API
   Gateway route, but overloads a route that already has four branches). Blocks Step 1.
2. **Daily cap** — does a replace count its inserted rows against `BUCKET_ITEM_DAILY_CAP` (500)?
   Today it does, through `expand_album_tracks`. Recommend: keep counting inserts, so the cap still
   bounds abuse. Blocks Step 1.
3. **Undo payload size** — `track_ids` replays can exceed one album. Recommend a server-side cap
   equal to the largest album in the catalog (or 200). Blocks Step 1.

**Resolved 2026-10-07 (owner, in-session): all three as recommended.** OQ1 → dedicated
`PUT /api/buckets/{id}/playback-queue`. OQ2 → inserts count against the cap, checked *before* the
delete. This is **not** a churn bound: the cap counts rows that still exist, so displaced rows stop
counting once deleted and a replace can be repeated — the same property `POST /items` + `DELETE`
always had. What bounds a single call is OQ3. OQ3 → 200. Prod
read-only check the same day: the largest album has 50 tracks and the longest live queue 20, so
200 clips nothing that exists.

## Alternatives considered

- **Front-only: retry 503 with backoff, cap resolve concurrency.** Cheaper and same-day, but the
  replace stays non-atomic: a tab closed mid-sequence or a 4xx still leaves a mixed queue, and the
  request count per ▶ stays ≈ 2N. Rejected by the owner 2026-10-07 in favor of this RFC.
- **Raise Lambda concurrency only.** Lowers the throttle rate and changes nothing about atomicity.
  Worth doing anyway (owner), not a substitute.
- **Delete-first ordering.** Already rejected in Step 6b: a failure then leaves an empty queue.

## Decisions log

| Date | Decision | Step |
|------|----------|------|
| 2026-10-07 | Owner: fix the cause structurally (server-side atomic replace) rather than patch retries in the front | — |
| 2026-10-07 | Owner: the four leftover *QRÖMELIFE* rows in the live queue are left for the owner to remove by hand; Claude does not touch them | — |
| 2026-10-07 | Owner: RFC accepted (draft → accepted); OQ1–3 taken as recommended (dedicated PUT, cap counts inserts, 200 tracks max) | 1 |
