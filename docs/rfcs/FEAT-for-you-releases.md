# FEAT-for-you-releases — home "나를 위한 새 앨범" strip + Spotify follow import

- Status: draft (Step 1 owner-approved in-session 2026-07-21)
- Step 1 SHIPPED + prod-smoked 2026-07-21 — ws #677 + backend #128 + front
  #301. Prod smoke: authed track→feed→untrack cycle returned both new fields
  (album_id + cover_url) on real releases (Masego); authed prod-home CDP
  rendered the strip (cover→overlay, artist link, '· 싱글' tag); logged-out
  home hides the strip. Remaining: Step 2 only.
- Owner decisions (2026-07-21): existing 새 앨범 strip ordering stays as-is
  (recency 60% × popularity 40%); the new strip is named **"나를 위한 새 앨범"**
  (Spotify "New Releases for You" analog); "follow" = the existing
  `user_artist_tracks` tracked-artist edge (no separate follow table); strip
  includes albums **and** singles/EPs.

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

## Step 2 — Spotify followed-artists import (next session, rule-4 gated)

- Owner re-auth of the Spotify bootstrap adding `user-follow-read` (user
  action, prerequisite).
- Worker: `GET /me/following?type=artist` (cursor-paged) → resolve/upsert
  catalog artists → snapshot-import into `user_artist_tracks` (same
  independence contract as Buckit import). Async via SQS/EventBridge — no
  synchronous Spotify on user-facing endpoints (hard rule #9).
- Front: "Spotify에서 가져오기" entry in the `/releases/` ManagePanel.
- Open question OQ1: artists followed on Spotify but absent from the catalog —
  enqueue for catalog ingest vs skip-and-report count.

## Rollback

Step 1 fields are Optional-additive (old front ignores them; new front
null-checks). Front strip is an isolated island — revert = remove the island.
