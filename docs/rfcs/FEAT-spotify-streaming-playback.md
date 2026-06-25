# FEAT-spotify-streaming-playback: Spotify Premium playback, end-to-end

- **Status**: accepted
- **Owner**: 박지훈 (single-owner)
- **Created**: 2026-06-25
- **Accepted**: 2026-06-25
- **Plan row**: `plan.md` → FEAT-spotify-streaming-playback (Backlog)

---

## Goal

The ▶ buttons that already exist (Pocket tray per-item, `PocketTray.tsx:399`; review/album tracklist, `albumDetail.client.ts:130`) actually play audio for the logged-in owner on a Spotify Premium session. Today they are wired but **dormant**: the backend token route is deployed, but no streaming token is provisioned and the front cannot turn an item into a Spotify URI. This RFC closes both gaps so a click on ▶ connects the Web Playback SDK device and starts playback.

This continues the playback seam shipped in FEAT-pocket-buckit Step 5b (the single-owner, server-minted token route) — it does **not** rebuild it.

## Non-goals

- **In-app OAuth/PKCE consent flow** — stays deferred (D27). Provisioning remains a one-time, owner-run local script. No browser "Connect Spotify" button.
- **Multi-listener / per-user streaming tokens** — v1 is single-owner (the owner's Premium account streams; other visitors do not get playback). Multi-user playback is a separate RFC, gated on FEAT-multi-user-accounts.
- **Non-Premium fallback** (30s preview clips, deep-link-to-Spotify-app) — out of scope. Premium is required by the Web Playback SDK; non-Premium surfaces the existing 'unsupported' message.
- **Queue / playlist context playback** (playback-queue item_type) — this RFC plays a single album/track target; queue semantics are a later kind.
- Changing the dormant-state UX copy beyond what is needed to distinguish "not provisioned" from "no Premium device".

## Current state

Verified against code + live AWS (2026-06-25):

- **Backend route is live.** `GET /api/playback/spotify-token` — `myblog_backend/app/api/routes/playback.py:30-48`, Cognito-JWT gated (`require_cognito_token`), maps `PlaybackNotConfiguredError`→503, `PlaybackProviderError`→502. Deployed: API Gateway `ld8pjw3mx4` route `GET /api/playback/spotify-token` (JWT authorizer `6eia7l`), integration = Lambda `ratemymusic-api`. Infra source `infra/apigateway.tf:325-331`.
- **Token store is SSM, not SM.** `playback_service.py:55-95` reads SSM param `SPOTIFY_SECRETS_PARAM=/myblog/spotify` (live Lambda env confirms; no `SPOTIFY_SECRETS_ARN`). It mints via a refresh-token grant against `accounts.spotify.com` (`:106-119`) using **only** the JSON key `streaming_refresh_token` (`:89-91`). Doc comments still say "Secrets Manager myblog/spotify" — **stale** (SM emptied by CHORE-secrets-ssm-migration).
- **503-dormant today** because live SSM `/myblog/spotify` holds `client_id`, `client_secret`, `refresh_token` (the worker's read token, 131 chars), `last_successful_refresh_at` — and **no `streaming_refresh_token` key**.
- **Bootstrap script is wrong for streaming.** `scripts/spotify_bootstrap_token.py:54-58` requests worker scopes (`user-read-recently-played user-read-currently-playing user-library-read user-library-modify`) — **no `streaming` scope** — and `:146-156` writes the `refresh_token` key. Running it as-is only refreshes the worker token; the route stays 503. No code anywhere requests `streaming` or writes `streaming_refresh_token`.
- **Front cannot resolve a URI.** `myblog_front/src/lib/spotifyPlayback.ts:204-206` — `resolveProviderUri` hard-throws `provider-uri-resolution-not-implemented`. `requestPlayback` (`:226-256`) gets a token, connects an SDK device, calls `resolveProviderUri`, catches the throw, and returns a 'dormant'/"트랙 식별 기능은 다음 단계" message. `PlaybackTarget` (`:32-34`) carries `albumId`/`trackId` DB ids only (no Spotify URI/ISRC for album). Token re-mint on expiry is a TODO (`:177-179`, `getOAuthToken` closes over the initial token).
- **The catalog already has Spotify ids.** `Album.spotify_id`, `Track.spotify_id`, `Artist.spotify_id` are all `Text NOT NULL, unique` (`myblog_shared_db/src/myblog_shared_db/models.py:243/291/192`). So every playable item has a known Spotify id — a resolve is a **direct DB read**, no Spotify search needed.

## Target state

- SSM `/myblog/spotify` carries a `streaming_refresh_token` minted with `streaming user-read-playback-state user-modify-playback-state` scopes from the owner's Premium account. `GET /api/playback/spotify-token` returns 200 `{access_token, expires_in, token_type}`.
- A `PlaybackTarget` resolves to a Spotify URI by reading the item's stored `spotify_id`: `track.spotify_id`→`spotify:track:<id>`, `album.spotify_id`→`spotify:album:<id>` (used as `context_uri`).
- `requestPlayback` mints a token → connects/links the Web Playback SDK device → resolves the URI → `PUT /v1/me/player/play` (or transfer) to the device → audio plays. Token is re-minted when it expires within a session. Non-Premium surfaces a clear 'Premium 필요' message.
- ▶ on the Pocket tray and on the review tracklist plays audio for the owner on a Premium browser session.

## Steps

Each step is independently mergeable. Per workspace rule #4, run **one step per session** unless explicitly OK'd — each gap is a prod-observe + direction-recheck gate.

### Step 1 — Streaming-scoped token provisioning (flips 503 → 200)

`scripts/spotify_bootstrap_token.py`: add a `--streaming` mode (flag or sibling entrypoint) that requests `SCOPES = "streaming user-read-playback-state user-modify-playback-state"` and writes the resulting refresh token to the JSON key **`streaming_refresh_token`** in SSM `/myblog/spotify`, reusing the existing `_write_secret` merge so the worker's `refresh_token` key survives untouched. No backend/front change.

Owner runs it once locally (Premium account consent in the browser; redirect `http://127.0.0.1:8888/callback` must be registered in the Spotify app; needs local AWS creds with `ssm:PutParameter` on `/myblog/spotify`).

**Verification**:
```
# token key now present (read-only)
aws ssm get-parameter --name /myblog/spotify --with-decryption --query 'Parameter.Value' --output text | jq 'keys'
# route mints (allow up to ~300s warm-cache TTL or a cold start)
curl -s -H "Authorization: Bearer $(python scripts/... get_token)" https://<api>/api/playback/spotify-token | jq '.token_type'   # "Bearer", not 503
```

**Rollback**: delete the `streaming_refresh_token` key from the SSM JSON → route reverts to 503-dormant. No user-facing data risk (the worker key is never touched).

> NB this step alone makes the endpoint return 200 but does **not** play audio (Steps 2–3 do). Ship it first because it is isolated and lets the rest be developed against a live token.

---

### Step 2 — Resolve a PlaybackTarget to a Spotify URI (direct DB read)

Every `Album`/`Track` has `spotify_id`. Two viable shapes — pick one in OQ2:

- **(a) Brief-carried (preferred for bucket items):** add `spotify_id` to `AlbumBrief`/`TrackBrief` in the contract so the front builds the URI client-side with no extra round-trip. Contract change → regen + commit `openapi.json` + `api.gen.ts`.
- **(b) Resolve endpoint (needed for the review tracklist, which only has a DB id):** `GET /api/playback/resolve?type=album|track&id=<db_id>` → `{uri}` (`spotify:track:<id>` / `spotify:album:<id>`). Same JWT authorizer as the token route. Backend reads `Album.spotify_id`/`Track.spotify_id`.

Likely both: (a) for the tray (briefs are already loaded) and (b) for contexts that hold only a DB id.

**Verification**:
```
curl -s -H "Authorization: Bearer <jwt>" "https://<api>/api/playback/resolve?type=track&id=<known>" | jq .uri   # spotify:track:...
# paste the uri into a Spotify client → it resolves to the expected track
```

**Rollback**: front `resolveProviderUri` keeps throwing → dormant message; no behavior regression.

---

### Step 3 — Front playback wiring (resolveProviderUri + transfer/play + re-mint)

`myblog_front/src/lib/spotifyPlayback.ts`: implement `resolveProviderUri` to use Step 2 (read `spotify_id` off the brief or call `/resolve`). In `requestPlayback`: token → connect SDK device → resolve URI → `PUT /v1/me/player/play` with `uris`/`context_uri` to the device id. Re-mint the token when it expires within a session (`getOAuthToken` TODO `:177-179`). Map Premium `account_error` to a clear "Spotify Premium이 필요해요" message distinct from "아직 연결 안 됨".

**Verification**:
```
pnpm lint && pnpm exec astro check
```
Real-browser CDP click-through on a **Premium** owner session: ▶ on the tray + on a review tracklist → SDK device connects, audio starts, transport responds. (UI change ⇒ browser click-through is a DoD requirement.) If Step 2 added a contract path/field, regen + commit `api.gen.ts` (front deploy gate fails otherwise).

**Rollback**: revert the front commit → dormant message returns; token route + resolve endpoint stay live and harmless.

---

### Step 4 — Prod verify + cutover

After Step 3 deploys, owner Premium session prod smoke: ▶ plays on prod (`www.ratemymusic.blog`), token route 200, resolve returns valid URIs, no console errors. Quote the result in the PR comment + drop the plan row.

---

## Open questions

1. ~~**Premium account identity** — which Spotify account holds the owner's catalog/library, and is it Premium?~~ **RESOLVED 2026-06-25**: the catalog/library account is Premium; the owner granted the `streaming` consent from it in Step 1 and `GET /api/playback/spotify-token` mints a live token (200). No longer blocks Step 4.
2. **Resolve shape (2a vs 2b vs both)** — brief-carried `spotify_id` (no round-trip, contract change) vs a `/resolve` endpoint (works from a bare DB id). The review tracklist holds only a DB id, so at least (b) is likely required; (a) is an optimization for the tray. *Blocks Step 2.*
3. **Token re-mint strategy** — `getOAuthToken` closes over the initial token; for sessions longer than `expires_in` (~3600s) the SDK callback must re-mint via `getStreamingToken()`. Confirm the SDK's `getOAuthToken` callback is re-invoked on 401 or whether we must proactively refresh. *Blocks Step 3 robustness.*
4. **Album playback semantics** — play an album as a `context_uri` (full album context) vs enqueue its tracks. `context_uri` is simplest. Confirm desired behavior for an album ▶. *Blocks Step 3.*
5. **Region/availability** — a track's `spotify_id` may be unplayable in the account's market. Decide the UX when `play` returns 404/restriction (skip vs message). *Minor; Step 3.*

## Decisions log

Filled in during execution.

| Date | Decision | Step |
|------|----------|------|
| 2026-06-25 | Accepted by owner (승격). Step 1 (streaming-scope bootstrap) queued for the next session — not started this session (rule #4 one-step gate). | — |
| 2026-06-25 | Step 1 code shipped: `--streaming` mode added to `scripts/spotify_bootstrap_token.py` — requests scopes `streaming user-read-playback-state user-modify-playback-state`, writes the SSM JSON key `streaming_refresh_token` via the existing `_write_secret` merge (worker `refresh_token` + D30 markers `last_successful_refresh_at`/`needs_reauth` left untouched). No backend/front change. Local verify: py_compile + `--help` + static scope/key assertions + a fake-SSM `_write_secret` run proving the worker-token-preservation invariant (both paths). Adversarial 3-lens review (contract-match / regression-invariant / rfc-scope-security) = pass, 0 blockers. **NOT yet provisioned**: owner must run `--streaming --write` once on a **Premium** account (browser consent + local AWS `ssm:PutParameter` on `/myblog/spotify`) to flip `GET /api/playback/spotify-token` 503→200. OQ1 (which catalog account is Premium) blocks the owner-run. | 1 |
| 2026-06-25 | **Step 1 DONE + prod-verified.** Owner ran `--streaming --write` (Premium consent); `streaming_refresh_token` written to SSM `/myblog/spotify`. Verified `GET /api/playback/spotify-token` on the API Gateway authed host (`ld8pjw3mx4`) with a smoke Cognito JWT → **HTTP 200**, body `{access_token (len 295), token_type: "Bearer", expires_in: 3600}` — i.e. the backend successfully exchanged the streaming refresh token against Spotify (token valid, scopes accepted), not merely "key present". **503→200 confirmed.** OQ1 resolved (account is Premium). | 1 |
