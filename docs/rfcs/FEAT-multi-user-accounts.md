# FEAT-multi-user-accounts: Multi-user platform (social signup, RYM-style reviews, personalized integrations)

- **Status**: draft
- **Owner**: 박지훈
- **Created**: 2026-06-14 (stub, carved from FEAT-member-dashboard Step 6)
- **Rescoped**: 2026-07-06 — full brainstorm + external-constraint research (this revision)
- **Plan row**: `plan.md` → FEAT-multi-user-accounts (Backlog)
- **Absorbs**: Scope B sketch of `FEAT-public-bucket-multiuser.md` (B1–B5; its Scope A — the
  public `/collection` viewer + `is_public` + API hardening — shipped 2026-06-15 and is prior art
  for the "public by default" read model here)

> Brainstorm-backed scoping draft. No code. Promotion to `accepted` is owner-only (hard rule #5).
> All external-constraint claims below were researched 2026-07-06; re-verify before the phase that
> depends on them (policies in this space changed 3 times in the last 14 months).

---

## Goal

Turn the single-owner music-review blog into a multi-user platform: anyone can sign up with
Google or Kakao, rate + comment albums RYM-style (all public), keep their own buckets/to-listen
queues, and optionally connect personal integrations (Spotify listening data; BYOK AI features).
The owner's long-form editorial stays owner-only. After this RFC: a stranger can sign up, review
an album, and their review appears on the album page and their public profile.

## Product positioning (why this beats "just use RYM / Last.fm")

The data source is plumbing, not the product. The differentiation is the **listen → review
workflow** plus the Korean layer:

- **RYM**: strongest rating/review culture, but structurally blind to actual listening data.
- **Last.fm**: perfect listening records, no review culture.
- **stats.fm-alikes**: stats visualization only; no community, no reviews.
- **Nobody** connects "what you actually listened to" with a review workflow. Our bucket system
  already sits exactly there (to-listen → listened → reviewed); listening data automates it
  ("you played this to-listen album 5× this week — review it?").
- Existing moat assets: Korean-first review community (RYM/Last.fm are English-first), the lyrics
  translation pipeline (listening → translated lyrics of the current track exists nowhere), the
  owner-editorial + user-ratings dual layer, AI review drafts grounded in the user's own
  listening/rating history.

**Priority consequence**: Phase 2 (reviews) is the differentiation itself; Phase 3 (listening
integration) is its amplifier. Never ship 3 without 2 — listening stats alone is a stats.fm clone.

## Personas

| Persona | Login | Gets | Implication |
|---|---|---|---|
| Reader / info seeker (incl. lyrics, album data) | none | today's public content (owner editorial, album/lyrics pages) | no change — already works |
| **Reviewer** (new core persona) | signup | RYM-style rating+comment, own buckets/to-listen, opt-in integrations (Spotify, BYOK AI) | Phases 0–4 |
| Writer (full editorial) | — | long-form posts | **owner-only for now** — publish path is GitHub-MDX → static build, structurally single-author; multi-author = separate cold RFC |

## Decisions (owner, 2026-07-06 brainstorm)

1. Purpose = open platform (not friends-only sharing); reviewer is the core new persona.
2. Lightweight reviews (RYM-reference): rating 0.5–5.0 half-steps + optional comment, one per
   user per album, aggregates on album pages, review list on user profiles. DB-only — never
   touches the GitHub publish path.
3. **Everything public, no visibility toggle** (reviews, buckets). RYM model; matches the
   already-public read path. No `visibility` column at all.
4. Social login: **Google + Kakao only. Naver dropped** (not OIDC-compliant → would need a
   wrapper Lambda + Naver app review; not worth it).
5. Account linking (same human via Google today, Kakao tomorrow): **not supported initially** —
   separate accounts per IdP. Cognito's Pre-SignUp `AdminLinkProviderForUser` pattern has a
   known first-login-abort race; Kakao email is consent-optional so email-based auto-link is
   unsafe anyway.
6. Spotify personalization: direct per-user OAuth on our app within the 5-user dev-mode cap,
   plus a **BYOA wizard (PKCE-only, no client_secret collected)** for Premium power users.
   Last.fm bridge rejected as primary path (3-hop UX: our app → Last.fm → Spotify); stays cold.
7. AI features (review drafts, lyrics translation, research notes): **model-agnostic job
   interface** — app owns prompt + JSON output schema; engine/model/key are pluggable. Owner
   keeps running everything centrally (current `claude -p` launchd pipeline) AND users can BYOK.
8. Long-form editorial (writer role) stays owner-only; multi-author is cold.

## External constraints (researched 2026-07-06)

- **Spotify dev mode**: max **5 authenticated users** per app + developer must hold Premium
  (Feb 2026 policy; was 25 users). Extended Quota Mode closed to hobbyists since 2025-05-15
  (registered org + ≥250k-MAU launched service). Refresh tokens expire **6 months** from
  original authorization (2026-06-18 policy) → re-auth flow is mandatory UX, `invalid_grant`
  on refresh means re-login, never retry. Rate limits are per-app, not per-user-token. Feb 2026
  also removed endpoints from dev mode (bulk tracks/albums/artists, browse/new-releases, other
  users' profiles/playlists) — check feature list against the migration guide per phase.
- **Reading now-playing does NOT need Premium** (`GET /v1/me/player/currently-playing`, free
  accounts fine). Premium is required for: Web Playback SDK streaming, playback *control*
  endpoints, and BYOA (the app *owner* must be Premium, which a BYOA user is by definition).
  So the 5 allowlisted users on our app can be Free-tier and still share listening data.
- **BYOA (user registers their own Spotify app)**: technically works; Home Assistant /
  multi-scrobbler instruct users to do exactly this for years, no known enforcement. Gray zone
  for a hosted SaaS (medium risk). PKCE-only (collect Client ID, never a secret) reduces both
  UX friction and ToS exposure. One-time ~5-min dashboard task; no API exists to automate app
  creation. Real blocker is the Premium requirement, not the procedure.
- **YouTube Music: rejected.** No official API exists (watch history API-dead since 2016; the
  only partner API is Content ID — rights management). The unofficial `ytmusicapi` covers
  everything (history/library/likes) but auth = users pasting full Google session cookies (we'd
  custody them) or a flaky TV-device OAuth, and it explicitly violates YouTube ToS → account
  risk for users. Not viable as a hosted-service path.
- **Claude subscription OAuth in third-party apps: ToS-banned** (enforcement began 2026-01-09;
  2026-02-19 policy: Free/Pro/Max OAuth tokens usable only in Claude.ai + Claude Code).
  Supported multi-user paths: Console API keys (usage-based), BYOK, Bedrock. Also: `claude -p`
  programmatic use now draws a separate metered credit pool (2026-06-15: $100/mo included on
  Max 5x, $200 on 20x, API list prices) — owner-central mode is no longer marginal-cost-zero.
- **Cognito**: Google = native social IdP. Kakao = OIDC-compliant since ~2022, works as a
  generic Cognito OIDC provider (issuer `https://kauth.kakao.com`, auto-discovery). Kakao email
  is consent-optional (guaranteed only for verified business apps) → schema must allow
  email-less users. Pricing: Essentials $0.015/MAU with 10k free MAU indefinitely — $0 at our
  scale. Naver: still not OIDC (no id_token, no discovery) — dropped, see decision 4.

## Current state (verified 2026-07-06, cross-repo)

- **Auth is multi-user-ready at the seams**: `myblog_backend/app/core/auth.py` —
  `resolve_owner()` already extracts JWT `sub` (returns `SINGLE_OWNER` sentinel in local/dev);
  code comment explicitly anticipates FEAT-multi-user-accounts as additive. Front PKCE flow
  (`myblog_front/src/lib/auth.ts`) works for any Cognito identity unchanged.
- **DB is the bulk of the work**: no `users` table; no `user_id`/owner column anywhere.
  User-owned-shaped tables in `myblog_shared_db` models: `review_buckets`,
  `review_bucket_items`, `album_to_listen_items`, `spotify_library_albums`,
  `spotify_recent_albums/tracks/now_playing`, `spotify_saved_tracks`,
  `spotify_play_events`/`track_play_events`, `spotify_stream_history`, `album_research`.
  Catalog tables (albums/artists/tracks/genres/posts) stay global.
- **Cognito pool**: `allow_admin_create_user_only = true` (`infra/cognito.tf`) — no
  self-signup, no federated IdPs configured yet.
- **Spotify is already two-lane**: client-credentials catalog reads (`myblog_music`,
  `myblog_worker` — stays global) vs user-token lane (single refresh token in SSM
  `/myblog/spotify`; `myblog_worker/worker/clients/spotify_user_client.py`, backend playback
  token mint, front `spotifyPlayback.ts` — which has a marked seam comment for the multi-user
  variant). Only the user-token lane needs per-user conversion.
- **AI pipelines are owner-local**: `scripts/*_poller.py` shell out to `claude -p` under the
  owner's Max subscription via launchd; zero cloud LLM calls today.
- **GitHub publish** (`publish_service.py`) is single-account single-repo — fine, since
  editorial stays owner-only (decision 8).
- Public read model precedent: `GET /api/buckets/public` + `/collection` viewer + JWT-hardened
  private board (FEAT-public-bucket-multiuser Scope A, prod since 2026-06-15).

## Target state / phases

Each phase is a separate RFC-step group; later phases must not block earlier ones. Sizing is
relative (Phase 0 ≈ the bulk).

### Phase 0 — Identity groundwork (the 80%)
`users` table keyed on Cognito `sub` (email nullable — Kakao), `user_id` FK added to the
user-owned tables above (nullable → backfill everything to the owner → NOT NULL; plain `V{N}__`
SQL, cross-repo rollout order per `reference-shared-db-cross-repo-rollout`), owner filtering
threaded through backend routes/services (`resolve_owner()` output finally consumed), worker
reads `user_id` from SQS payloads. Public reads stay public but become user-scoped in shape
(e.g. `/api/buckets/public` grows a user dimension).

### Phase 1 — Social signup (Google + Kakao)
Cognito: `allow_admin_create_user_only = false`, Google native IdP + Kakao generic-OIDC IdP,
hosted-UI/managed-login callback wiring, backend user-row provisioning on first login
(post-confirmation trigger or lazy-create on first authed request). No account linking (decision
5). Email-less Kakao users supported.

### Phase 2 — RYM-style reviews (the differentiation)
`album_reviews` (user_id, album_id, rating half-steps 0.5–5.0, optional comment text,
timestamps; UNIQUE(user_id, album_id)), write UI on album pages, aggregates (avg/count) on album
pages, review feed + per-user public profile page (`/members/[handle]` — absorbs the old stub's
scope; social graph/follows stay out, see cold list). All public (decision 3).

### Phase 3 — Listening personalization (Spotify)
Per-user OAuth against our app (5-user cap — early users/friends; Free-tier OK for
read endpoints), per-user refresh tokens stored encrypted (KMS envelope, same pattern as Phase 4
keys) replacing the single SSM token for those users; worker sync loops become per-user. Then the
**BYOA wizard**: PKCE-only, screenshot-guided app creation, paste Client ID → immediate
validation OAuth round-trip, 6-month expiry → "reconnect" badge + one-click re-auth. Code is
per-user-token-shaped from Phase 0, so a future quota-policy thaw is config, not code.

### Phase 4 — Model-agnostic AI (BYOK + owner-central)
One `LLMEngine` job interface (feature, prompt_template_id, output JSON schema, engine, model,
user_id): `CliEngine` = existing launchd `claude -p` pollers, owner-only, same schema contract;
`ApiEngine` = Pydantic AI (or a thin adapter over anthropic+openai SDKs if Lambda dependency
weight matters) with per-request key injection — owner's SSM keys or the user's BYOK key.
Structured output: provider-native json_schema where supported, forced-tool-call fallback,
Pydantic re-validation + one retry. `user_api_keys`: KMS-envelope-encrypted ciphertext in
Postgres, live-probe validation on save, masked display (last-4), delete = revoke, never logged.
Metering: per-user/per-feature DB counters checked pre-dispatch (LiteLLM proxy rejected — an
always-on service costs more than it polices at this scale). Owner-mode note: `claude -p` is now
metered credit (see constraints) — plan eventual owner migration onto `ApiEngine` too.

### Cold (recorded, not planned)
- **Multi-author editorial** — requires DB-based posts replacing GitHub-MDX static publishing.
- **YouTube Music integration** — no official API; `ytmusicapi` = ToS violation + session-cookie
  custody. Revisit only if Google ships an official API.
- **Last.fm bridge** — the only official unlimited path to arbitrary users' listening data
  (works even for YTM users via scrobbler extensions); rejected for 3-hop UX. Revisit if the
  Spotify 5-user cap actually bites.
- **Claude subscription connect** — ToS-banned; revisit on policy change.
- **Spotify general-user expansion** — blocked on Spotify quota policy (org + 250k MAU);
  Phase 0/3 architecture keeps it config-only when/if unblocked.
- **Social graph** (follows/lists, from the original stub) — after Phase 2 proves review volume.

## Non-goals

- No native mobile app work; no infra re-platforming.
- No review moderation/anti-abuse system in v1 beyond auth-gated writes (revisit at real volume).
- No per-user private content — everything public (decision 3) → no visibility model.
- No changes to the music-catalog lane (client-credentials Spotify, MusicBrainz, LRCLIB stay
  global/shared; rule #9 — no sync Spotify on user-facing endpoints — unchanged).

## Open questions

1. **Handle model** (blocks Phase 1/2 boundary): derive public handle from IdP nickname with
   uniquifier, or user-chosen at first login? (Kakao nickname collisions likely.)
2. **Phase 2 rating aggregate placement** (blocks Phase 2): live query vs denormalized counters
   on `albums` — decide when review-read QPS is real.
3. **BYOK provider set for v1** (blocks Phase 4): Anthropic+OpenAI+Gemini+OpenRouter all at
   once, or Anthropic-only first?
4. **Per-user Spotify token storage** (blocks Phase 3): dedicated `user_integrations` table
   (provider, ciphertext, expiry, status) — one row shape shared with Phase 4 `user_api_keys`,
   or two tables? (Lean: one `user_integrations` table for both.)

## Decisions log

| Date | Decision | Notes |
|------|----------|-------|
| 2026-06-14 | Stub carved from FEAT-member-dashboard Step 6 | |
| 2026-06-15 | Public-bucket Scope A shipped separately | prior art for public read model |
| 2026-07-06 | Full rescope via brainstorm + 6 research passes | this revision |
| 2026-07-06 | Decisions 1–8 (owner) | see Decisions section |
