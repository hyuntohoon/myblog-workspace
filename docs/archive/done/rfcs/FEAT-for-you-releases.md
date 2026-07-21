# FEAT-for-you-releases — home "나를 위한 새 앨범" strip + Spotify follow import

- Status: done (2026-07-21, archived — Steps 1–2 both SHIPPED + prod-smoked
  2026-07-21; implementation complete, no observation gates → moved to
  `docs/archive/done/rfcs/`. Original status line below.)
  <br>_draft_ (Step 1 owner-approved in-session 2026-07-21; Step 2
  owner-approved same day — OQ1 + owner-gate decisions in-session)
- Step 1 SHIPPED + prod-smoked 2026-07-21 — ws #677 + backend #128 + front
  #301. Prod smoke: authed track→feed→untrack cycle returned both new fields
  (album_id + cover_url) on real releases (Masego); authed prod-home CDP
  rendered the strip (cover→overlay, artist link, '· 싱글' tag); logged-out
  home hides the strip.
- Step 2 SHIPPED + prod-smoked 2026-07-21 — ws #682 (contract + apigw route,
  applied: probe 404→401) + worker #76 + backend #129 + front #304. Prod
  smoke: non-owner JWT → 403 "Owner only" (fail-closed); owner re-auth minted
  a `user-follow-read` token (probe 200); live import over 6 real follows hit
  ALL three paths — 1 matched-insert (Debussy, 30→31 tracked), 3
  already-tracked skips, 2 uncatalogued (Korstick/Brodsky) fan-out →
  album-sync created both artists (+50/+3 albums) → delayed 900s rerun
  attached them (31→33). Implementation complete — closeout/archive is the
  next owner call.
- Owner decisions (2026-07-21): existing 새 앨범 strip ordering stays as-is
  (recency 60% × popularity 40%); the new strip is named **"나를 위한 새 앨범"**
  (Spotify "New Releases for You" analog); "follow" = the existing
  `user_artist_tracks` tracked-artist edge (no separate follow table); strip
  includes albums **and** singles/EPs.
- Owner decisions (2026-07-21, Step 2 session): **OQ1 = catalog-ingest** —
  followed artists missing from the catalog are expanded onto the existing
  album-sync SQS pipeline (one `get_artist_albums` page, album+single, per
  artist; artists are created by album sync) with ONE delayed (900s) snapshot
  re-import chained so freshly-ingested artists get their tracked edge without
  a second click; leftovers wait for the next manual import. **The trigger
  endpoint is owner-only** (`provisioned_owner_id`): the worker spends the
  OWNER's bootstrap token, so an open member route would copy the owner's
  follows into another member's tracked list.

## Problem

The home 새 앨범 strip is catalog-wide. The owner wants a Spotify-style
personalized row: latest releases from artists *they* follow, and wants to be
able to build that follow list both in-app (already exists —
FEAT-personal-release-tracking CRUD + `/releases/` ManagePanel) and by
importing their followed artists from Spotify (does not exist).

## Current state (audited 2026-07-21)

- `user_artist_tracks` (V47) + tracked-artists CRUD (`/api/me/tracked-artists`,
  POST/GET/DELETE + Buckit-import preview) + `GET /api/me/release-feed`
  (upcoming/recent 30d, soft-grouped multi-source events) — all shipped.
- `ReleaseFeedItem` carries no cover image and no catalog album id → cannot
  render a cover strip.
- Worker `spotify_user_client` scopes: user-library-* + listening only — **no
  `user-follow-read`**; `/me/following` is not implemented.
- Home strips (`NewReleasesCard`) render-nothing on failure/empty; the album
  overlay host is app-wide (`openAlbum`).

## Step 1 — home strip (this session, single PR chain)

1. **Backend**: `ReleaseFeedItem` + `album_id`/`cover_url` (Optional,
   additive) — one IN-query joining confirmed `spotify_album_id` → `albums`.
   No new route ⇒ no API Gateway change.
2. **Contract**: backend `openapi.json` → workspace merge → front
   `api.gen.ts` regen.
3. **Front**: `ForYouReleasesCard` on home, directly below 새 앨범 —
   logged-in members only, `state=recent` releases newest-first (albums +
   singles/EPs), covers open the album overlay when `album_id` resolves;
   render-nothing degradation (no skeleton, no reserved space) when logged
   out / error / empty. Section link → `/releases/`.

Verification: backend pytest; front lint + astro check + real-browser CDP
click-through (mocked feed); prod smoke post-merge.

## Step 2 — Spotify followed-artists import (SHIPPED + prod-smoked 2026-07-21)

- Owner re-auth of the Spotify bootstrap adding `user-follow-read` (user
  action, prerequisite; scope added to `scripts/spotify_bootstrap_token.py`).
- Worker: `GET /me/following?type=artist` (cursor-paged; 403 →
  `SpotifyScopeError`, dropped not retried) → match `artists.spotify_id` →
  snapshot-import into `user_artist_tracks` (same independence contract as
  Buckit import; sorted `ON CONFLICT DO NOTHING` upsert, raw-SQL so no
  shared_db pin bump). Async via SQS — no synchronous Spotify on user-facing
  endpoints (hard rule #9). Message contract:
  - `{"job": "spotify_follow_import", "user_id", "rerun"?}` — the import
    (backend-enqueued; `rerun=true` only from the self-chain, never fans out).
  - `{"job": "spotify_follow_ingest", "artist_sids": [≤10]}` — OQ1 fan-out;
    each chunk expands its artists' recent releases onto album-sync.
- Backend: `POST /api/me/tracked-artists/spotify-import` (owner-only,
  `provisioned_owner_id`, 202 `{queued}`; degrades `queued=false` without a
  queue) + matching `infra/apigateway.tf` JWT route.
- Front: owner-only "Spotify에서 가져오기" entry in the `/releases/`
  ManagePanel (`isOwnerUser()` gate mirrors the server gate).
- OQ1 RESOLVED (owner 2026-07-21): catalog-ingest — see Owner decisions above.

## Rollback

Step 1 fields are Optional-additive (old front ignores them; new front
null-checks). Front strip is an isolated island — revert = remove the island.
