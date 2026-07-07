# FEAT-multi-user-accounts: Multi-user platform (social signup, RYM-style reviews, personalized integrations)

- **Status**: in-progress (2026-07-07, owner in-session approval — Phase 0 started)
- **Owner**: 박지훈
- **Created**: 2026-06-14 (stub, carved from FEAT-member-dashboard Step 6)
- **Rescoped**: 2026-07-06 — brainstorm + external research; same-day cold review (phase
  re-sequencing, per-phase gates, Last.fm promoted, BYOA demoted, ops items added)
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
queues, and optionally connect listening sources (Last.fm primarily; Spotify for a small tier)
and BYOK AI features. The owner's long-form editorial stays owner-only. After this RFC: a
stranger can sign up, review an album, and their review appears on the album page and their
public profile.

## Strategic conflict — decide before accepting

The 2026-06-06 whole-project review named **FEAT-ai-editorial-critique** the product's defining
feature (editorial-quality direction). This RFC is a competing bet (community-platform
direction). The layers are compatible long-term (owner editorial + user community), but a solo
maintainer cannot run both programs at once. **Accepting this RFC = platform takes priority for
its duration.** This must be a conscious owner decision, not a side effect.

## Demand risk + per-phase gates

Current state: ~1 published post, single-user traffic. plan.md already freezes
FEAT-genre-recommendation and FEAT-ai-editorial-critique on "review volume" — the same
discipline applies here, so every phase ends with an explicit gate; failing a gate freezes
later phases (the work done stays shipped, nothing is torn down):

- **Gate G1 (after Phase 1)**: ≥10 reviews by ≥5 distinct non-owner users within 4 weeks of
  opening signup (denominator: all reviews by non-owner accounts). Miss → freeze Phases 2–4,
  keep signup+reviews running, redirect effort to the editorial program.
- **Gate G2 (after Phase 3)**: ≥30% of monthly-active reviewers connect a listening source
  (denominator: non-owner accounts with ≥1 review in the month). Miss → Phase 4 stays
  owner-central only (no BYOK build).

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

**Priority consequence**: reviews (Phase 1) are the differentiation itself; listening
integration (Phase 3) is its amplifier. Never ship 3 without 1 — listening stats alone is a
stats.fm clone. For general users the live amplifier is **Last.fm** (unlimited, official);
Spotify live sync is capped at a 5-user tier (see constraints).

## Personas

| Persona | Login | Gets | Implication |
|---|---|---|---|
| Reader / info seeker (incl. lyrics, album data) | none | today's public content (owner editorial, album/lyrics pages) | no change — already works |
| **Reviewer** (new core persona) | signup | RYM-style rating+comment, own buckets/to-listen, opt-in integrations (Last.fm/Spotify, BYOK AI) | Phases 0–4 |
| Writer (full editorial) | — | long-form posts | **owner-only for now** — publish path is GitHub-MDX → static build, structurally single-author; multi-author = separate cold RFC |

## Decisions (owner, 2026-07-06)

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
6. Listening sources (cold-review revision, supersedes the first-pass "Spotify direct + BYOA"):
   **Last.fm is the primary general-user source** — username-only connect (public reads need no
   OAuth), `nowplaying` flag covers the live-lyrics entry, full multi-year scrobble history,
   service-agnostic (covers YTM/Apple Music via scrobbler extensions), unlimited users, ToS-clean.
   **Spotify direct per-user OAuth** stays for a ≤5-user tier (owner + early users; live
   playback + saved-tracks sync). **GDPR-export upload** gives lifetime depth for anyone
   (official, no cap; days-to-weeks delivery lag makes it a power-user ritual, not onboarding).
   **BYOA demoted to cold** (Premium-only, gray-zone, mostly redundant with Last.fm).
7. AI features (review drafts, lyrics translation, research notes): **model-agnostic job
   interface** — app owns prompt + JSON output schema; engine/model/key are pluggable. Owner
   keeps running everything centrally (current `claude -p` launchd pipeline) AND users can BYOK.
8. Long-form editorial (writer role) stays owner-only; multi-author is cold.
9. (Cold review) Phases re-sequenced for time-to-value: the core loop (signup → review →
   profile) needs only a `users` table — `album_reviews` is a new table born with `user_id`.
   Scoping existing tables moves to the phase that uses them.

## External constraints (researched 2026-07-06)

- **Spotify dev mode**: max **5 authenticated users** per app + developer must hold Premium
  (Feb 2026 policy; was 25 users). Extended Quota Mode closed to hobbyists since 2025-05-15
  (registered org + ≥250k-MAU launched service). Refresh tokens expire **6 months** from
  original authorization (2026-06-18 policy) → the reconnect badge + one-click re-auth UX is a
  Phase 3 requirement even for the 5-user tier; `invalid_grant` on refresh = re-login, never
  retry. Rate limits are per-app. Feb 2026 also removed endpoints from dev mode (bulk
  tracks/albums/artists, browse/new-releases, other users' profiles/playlists) — check feature
  list against the migration guide per phase.
- **Reading now-playing does NOT need Premium** (`GET /v1/me/player/currently-playing`, free
  accounts fine). Premium is required for: Web Playback SDK streaming, playback *control*
  endpoints, and BYOA (the app *owner* must be Premium). So the 5 allowlisted users can be
  Free-tier and still share listening data; in-browser ▶ playback stays Premium-only.
- **Last.fm**: public-profile reads (`user.getRecentTracks` incl. `nowplaying`,
  `user.getLovedTracks`, top charts) need only an API key + username — no per-user OAuth, no
  token custody, no user cap; non-commercial use free. Requires the user to have scrobbling set
  up (native Spotify→Last.fm connect; browser-extension scrobblers for YTM et al.).
- **BYOA (user registers their own Spotify app)**: technically works (Home Assistant /
  multi-scrobbler precedent, no known enforcement); PKCE-only reduces exposure. Gray zone for a
  hosted SaaS + Premium-required + ~5-min manual dashboard setup. **Cold** (decision 6).
- **YouTube Music: rejected.** No official API (watch history API-dead since 2016; the only
  partner API is Content ID). Unofficial `ytmusicapi` = users pasting full Google session
  cookies (we'd custody them) or flaky TV-device OAuth, explicit YouTube ToS violation →
  account risk. Not viable for a hosted service; Last.fm covers YTM users indirectly.
- **Claude subscription OAuth in third-party apps: ToS-banned** (enforcement 2026-01-09; policy
  2026-02-19: Free/Pro/Max OAuth tokens usable only in Claude.ai + Claude Code). Supported
  multi-user paths: Console API keys, BYOK, Bedrock. Also: `claude -p` programmatic use now
  draws a metered credit pool (2026-06-15: $100/mo included on Max 5x, $200 on 20x, API list
  prices) — owner-central mode is no longer marginal-cost-zero.
- **Cognito**: Google = native social IdP. Kakao = OIDC-compliant since ~2022, works as a
  generic Cognito OIDC provider (issuer `https://kauth.kakao.com`, auto-discovery). Kakao email
  is consent-optional → schema must allow email-less users. Managed-login UI is customization-
  limited; a self-built login page can deep-link per-IdP via the `identity_provider` authorize
  param. Pricing: Essentials $0.015/MAU, 10k free MAU indefinitely — $0 at our scale. Naver:
  still not OIDC — dropped (decision 4).
- **Cognito pool immutability risk (found 2026-07-07 current-state audit, blocks the infra
  sub-step)**: the existing pool has `username_attributes = ["email"]` + email schema
  `required = true` — both immutable after creation (change = pool replacement; pool holds the
  owner account, `deletion_protection = ACTIVE`). A Kakao user who declines the optional email
  consent cannot satisfy the required-attribute check on federated sign-in. Resolution options
  to research before Phase 0's infra sub-step: (a) Kakao app email as 필수 동의 (requires 비즈앱
  conversion — verify current eligibility for solo/personal developers), (b) a separate member
  pool without required email (backend then validates two issuers), (c) placeholder-email
  mapping (last resort — pollutes email semantics). Re-verify Cognito's federated
  required-attribute enforcement behavior at the same time.
  **RESOLVED 2026-07-07 — option (a) adopted (owner approval in-session); existing pool kept,
  no replacement.** Research findings:
  - Cognito enforcement re-verified (AWS docs + re:Post): every *required* pool attribute must
    have an IdP attribute mapping, and if the IdP omits the claim, federated sign-in fails with
    `attributes required: [email]`. So the fix must guarantee the email claim is always present.
  - Kakao: a solo developer **without a 사업자등록번호 can self-serve convert to a 개인 개발자
    비즈앱** — requirements are only app-owner phone 본인인증 (계정 설정 > 본인인증) + 카카오
    비즈니스 통합 서비스 약관 동의, via [앱] > [일반] > [비즈니스 정보] > [개인 개발자 비즈 앱].
    Only documented limitation: no 비즈니스 채널 연결 (irrelevant — we use no KakaoTalk channel).
    Email as 필수 동의 is available to 개인 개발자 비즈앱.
  - With 필수 동의 + the "카카오계정으로 수집 후 제공" option, a user whose Kakao account lacks
    an email is prompted to register one during login → the email claim is always present.
  - (b) rejected: two issuers means touching the duplicated auth guard in backend **and** music,
    double JWKS, front pool-selection — unjustified when (a) is self-serve. (c) rejected:
    pollutes email semantics in a `username_attributes = ["email"]` pool.
  - Residual check at 0c implementation: Cognito maps federated emails as *unverified* unless an
    `email_verified` claim is mapped; Kakao OIDC docs don't confirm `email_verified` in the
    userinfo response (JS-rendered docs) → verify with one live `/v1/oidc/userinfo` call. Not
    sign-in-blocking either way, and email-based auto-link is already excluded (decision 5).
  - New owner console prerequisites (before 0c infra apply): phone 본인인증 → 개인 개발자 비즈앱
    전환 → 동의항목에서 email = 필수 동의 (수집 후 제공) 설정.
- **Compliance/ops (Korean users)**: 개인정보처리방침 (privacy policy) is required by both the
  Google OAuth consent screen and Kakao production review — author it + budget review lead time
  in Phase 0. Account deletion is a 개인정보보호법 obligation → Phase 0 feature, not polish.

## Current state (verified 2026-07-06, cross-repo)

- **Auth is multi-user-ready at the seams**: `myblog_backend/app/core/auth.py` —
  `resolve_owner()` already extracts JWT `sub` (returns `SINGLE_OWNER` sentinel in local/dev);
  code comment explicitly anticipates FEAT-multi-user-accounts as additive. Front PKCE flow
  (`myblog_front/src/lib/auth.ts`) works for any Cognito identity unchanged.
- **DB**: no `users` table; no `user_id`/owner column anywhere. User-owned-shaped tables in
  `myblog_shared_db` models: `review_buckets`, `review_bucket_items`, `album_to_listen_items`,
  `spotify_library_albums`, `spotify_recent_albums/tracks/now_playing`, `spotify_saved_tracks`,
  `spotify_play_events`/`track_play_events`, `spotify_stream_history`, `album_research`.
  Catalog tables (albums/artists/tracks/genres/posts) stay global. Note: `album_reviews` does
  not exist yet — it is new, so the core loop needs only `users` up front (decision 9).
- **Cognito pool**: `allow_admin_create_user_only = true` (`infra/cognito.tf`) — no
  self-signup, no federated IdPs configured yet.
- **Spotify is already two-lane**: client-credentials catalog reads (`myblog_music`,
  `myblog_worker` — stays global) vs user-token lane (single refresh token in SSM
  `/myblog/spotify`; `myblog_worker/worker/clients/spotify_user_client.py`, backend playback
  token mint, front `spotifyPlayback.ts` with a marked multi-user seam). Only the user-token
  lane needs per-user conversion, and only in Phase 3.
- **Lifetime listening import** (`spotify_stream_history`, FEAT-listening-history-import) is an
  owner-run script over a GDPR export file — API-cap-independent by nature; a user-facing
  upload turns it multi-user without external constraints.
- **AI pipelines are owner-local**: `scripts/*_poller.py` shell out to `claude -p` under the
  owner's Max subscription via launchd; zero cloud LLM calls today.
- **GitHub publish** (`publish_service.py`) is single-account single-repo — fine, since
  editorial stays owner-only (decision 8).
- Public read model precedent: `GET /api/buckets/public` + `/collection` viewer + JWT-hardened
  private board (FEAT-public-bucket-multiuser Scope A, prod since 2026-06-15).

## Target state / phases

Re-sequenced 2026-07-06 (cold review): ship the core loop first, scope existing tables later.

### Phase 0 — Identity minimum
`users` table keyed on Cognito `sub` (email nullable — Kakao; handle unique; display name +
avatar URL from IdP claims only — **no image uploads**). Cognito: self-signup on, Google native
IdP + Kakao generic-OIDC IdP, user-row provisioning on first login (**lazy-create on first
authed API call — decided 2026-07-07**; post-confirmation trigger rejected: extra Lambda +
federated-flow quirks + sign-up-blocking failure mode). **Settings page**: handle/display name,
connected-integrations list (empty at first), **account deletion** (개인정보보호법 — deletes
user row + owned rows + Cognito user). 개인정보처리방침 page (blocks Google consent screen +
Kakao production review). No existing table is touched.

Sub-steps (started 2026-07-07): **0a** shared_db V36 `users` + model + prod apply → **0b**
개인정보처리방침 page (front-only; unblocks owner-side Google/Kakao console setup) → **0c**
infra Cognito self-signup + IdPs (pool-immutability research RESOLVED 2026-07-07 — option (a),
existing pool kept; still blocked on owner console prerequisites: Google OAuth client, Kakao
app + 개인 개발자 비즈앱 전환 + email 필수 동의 설정) → **0d** backend `GET/PATCH /api/me`
lazy-provisioning + account deletion (**implemented 2026-07-07**: backend
`feat/multi-user-0d-api-me` — GET also lazy-provisions and rides the API GW GET catch-all;
DELETE goes Cognito-first (ListUsers by sub → AdminDeleteUser, idempotent) then the DB row so
retries converge; `OWNER_SUB` env 403-guards the admin identity. Workspace infra: PATCH/DELETE
JWT routes + pool-scoped IAM + OWNER_SUB — **applied + e2e-verified 2026-07-07** (backend #105,
ws #561; PATCH 401/200 probes, throwaway-user DELETE → 204, Cognito+DB both empty). Note:
access-token bearers carry no email/name claims, so provisioned defaults degrade to
`user-<sub8>` — the 0e settings page prompts a handle pick anyway) → **0e** front settings page
+ signup entry (**settings slice SHIPPED 2026-07-07**, front #249 prod-smoked: `/settings/` —
profile edit with handle-format mirror, 연동 empty state, account deletion armed by typing the
member's own @handle; ProfileApp tab row 설정 ↗ entry. **Signup entry deliberately deferred to
0c** — no self-signup flow exists to link until the IdPs land).

Phase 0 remaining: owner console setup (Google OAuth client; Kakao 본인인증 → 개인 개발자
비즈앱 → email 필수 동의) → **0c infra** (self-signup + IdPs + signup entry link-up). All other
sub-steps (0a/0b/0d/0e-settings) are live in prod.

**Console setup progress + deferred public-launch gate (2026-07-07).** OAuth credentials for
both IdPs are stored in SSM SecureString — `/myblog/oauth/{google-client-id, google-client-secret,
kakao-rest-api-key, kakao-client-secret}` (0c Terraform reads these; the Kakao value is the **카카오
로그인** client secret, not 비즈니스 인증). Google OAuth web client created (redirect
`https://<cognito-hosted-domain>/oauth2/idpresponse`). **For 0c build + test, the Google consent
screen stays in Testing mode with the owner added as a test user, and Kakao stays in dev mode** —
federated login works for the owner without any verification, so this does **not** block 0c.
**Deferred to the public-signup launch step (a later Phase 0 task, NOT a 0c blocker):** (1) Google
publish-to-production triggers brand verification, which requires Google Search Console **domain
ownership verification of `ratemymusic.blog`** — add the Search-Console TXT record to the Route53
hosted zone (DNS is on AWS Route53, console-managed / not in Terraform; `claude_aws_manager` has
**no `route53` IAM permission** → owner-only), verify under the **same Google account that owns the
Cloud project**, then click 문제를 해결함 → 브랜딩 재인증; (2) Kakao production review
(개인정보처리방침 + 비즈앱 심사). Both gate opening signup to the general **public**, not the 0c IdP
wiring or owner-account testing.

### Phase 1 — RYM-style reviews (the differentiation) → Gate G1
`album_reviews` (user_id, album_id, rating half-steps 0.5–5.0, optional comment text,
timestamps; UNIQUE(user_id, album_id)) — new table, born scoped. Write UI on album pages,
aggregates (avg/count) on album pages, per-user public profile (`/members/[handle]`, absorbs the
old stub) with review feed. All public. Anti-abuse minimum: per-user daily review cap + owner
delete-any-review (admin claim on the owner account). Public profiles + reviews in the sitemap
(SEO = the growth channel). **Then evaluate Gate G1.**

### Phase 2 — Per-user buckets/to-listen
`user_id` on `review_buckets` + `review_bucket_items` + `album_to_listen_items` (nullable →
backfill owner → NOT NULL; plain `V{N}__` SQL, rollout order per
`reference-shared-db-cross-repo-rollout`), owner filtering threaded through bucket/library
routes (`resolve_owner()` output finally consumed), `/api/buckets/public` + `/collection` grow a
user dimension. Spotify-lane tables are NOT touched here.

### Phase 3 — Listening personalization → Gate G2
**3a Last.fm (primary)**: settings-page connect = username input (+ optional profile-privacy
probe), worker EventBridge poll per connected user via `user.getRecentTracks` (incremental,
`nowplaying` flag) into per-user play events; profile "now playing" + listen→review prompts;
live-lyrics entry point accepts Last.fm nowplaying. **3b Spotify 5-user tier**: per-user refresh
tokens (KMS-encrypted in `user_integrations`, replacing the single SSM token for those users),
per-user worker sync, reconnect badge + one-click re-auth (6-month expiry). **3c GDPR-export
upload**: user-facing upload of the official Spotify data export into `spotify_stream_history`
(per-user), reusing the existing import pipeline — unlimited users, official, lifetime depth.
Spotify-lane tables get `user_id` here (same nullable→backfill→NOT NULL pattern). **Then
evaluate Gate G2.**

### Phase 4 — Model-agnostic AI (BYOK + owner-central; BYOK half gated on G2)
One `LLMEngine` job interface (feature, prompt_template_id, output JSON schema, engine, model,
user_id): `CliEngine` = existing launchd `claude -p` pollers, owner-only, same schema contract;
`ApiEngine` = Pydantic AI (or a thin adapter over anthropic+openai SDKs if Lambda dependency
weight matters) with per-request key injection — owner's SSM keys or the user's BYOK key.
Structured output: provider-native json_schema where supported, forced-tool-call fallback,
Pydantic re-validation + one retry. `user_api_keys` rows in `user_integrations`: KMS-envelope-
encrypted ciphertext, live-probe validation on save, masked display (last-4), delete = revoke,
never logged. Metering: per-user/per-feature DB counters checked pre-dispatch (LiteLLM proxy
rejected — an always-on service costs more than it polices at this scale). Owner-mode note:
`claude -p` is now metered credit — plan eventual owner migration onto `ApiEngine` too.

### Cold (recorded, not planned)
- **Multi-author editorial** — requires DB-based posts replacing GitHub-MDX static publishing.
- **BYOA wizard** (demoted 2026-07-06) — PKCE-only guided self-registered Spotify apps;
  Premium-only + ToS gray zone + mostly redundant with Last.fm. Revisit only if a cohort of
  Premium users demands live Spotify beyond the 5-user tier.
- **Charts** (RYM's flagship: aggregate rating charts by year/genre) — cheap once reviews
  exist, meaningless without volume. Build after Gate G1 holds for a quarter.
- **Review upvotes/comments + social graph** (follows/lists, from the original stub) — after
  review volume proves out.
- **YouTube Music integration** — no official API; `ytmusicapi` = ToS violation + session-cookie
  custody. Revisit only if Google ships an official API.
- **Claude subscription connect** — ToS-banned; revisit on policy change.
- **Spotify general-user expansion** — blocked on Spotify quota policy (org + 250k MAU);
  Phase 3 architecture keeps it config-only if unblocked.

## Non-goals

- No native mobile app work; no infra re-platforming.
- No moderation system beyond the Phase 1 minimum (daily cap + owner delete) until real volume.
- No per-user private content — everything public (decision 3) → no visibility model.
- **No user image uploads** (avatars = IdP profile picture URL only — avoids image moderation
  and S3 upload surface entirely).
- **No email notifications / no notification system v1** (no email infra; Kakao emails not
  guaranteed anyway). No RSS of user reviews v1.
- No changes to the music-catalog lane (client-credentials Spotify, MusicBrainz, LRCLIB stay
  global/shared; rule #9 — no sync Spotify on user-facing endpoints — unchanged).

## Open questions

1. ~~**Handle model** (blocks Phase 0)~~ — **RESOLVED 2026-07-07 (owner)**: user-chosen with an
   IdP-nickname-derived unique default, editable in settings.
2. **Rating aggregate placement** (blocks Phase 1): live query vs denormalized counters on
   `albums` — decide at implementation with real read QPS in mind; live query is fine at launch.
3. **BYOK provider set for v1** (blocks Phase 4): all four (Anthropic/OpenAI/Gemini/OpenRouter)
   vs Anthropic-only first. Lean: Anthropic-only first, adapter designed for four.
4. **`user_integrations` shape** (blocks Phase 3): one table for Last.fm username + Spotify
   tokens + AI keys (provider, payload ciphertext, status, expiry) vs per-kind tables. Lean: one
   table.
5. **Owner data migration UX** (blocks Phase 2/3): the owner's existing buckets/listening data
   backfills to the owner user row — decide whether the owner account is a normal member page
   (`/members/[owner-handle]`) or keeps `/profile` as a special surface.

## Decisions log

| Date | Decision | Notes |
|------|----------|-------|
| 2026-06-14 | Stub carved from FEAT-member-dashboard Step 6 | |
| 2026-06-15 | Public-bucket Scope A shipped separately | prior art for public read model |
| 2026-07-06 | Full rescope via brainstorm + 6 research passes | decisions 1–8 |
| 2026-07-06 | Cold review: phases re-sequenced (users-only Phase 0, reviews before bucket scoping), per-phase gates G1/G2 added, strategic conflict with FEAT-ai-editorial-critique surfaced | decision 9 |
| 2026-07-06 | **Last.fm promoted to primary listening source; BYOA demoted to cold** (owner reversed the earlier 3-hop-UX rejection after the cold review) | decision 6 revised |
| 2026-07-06 | Final completeness sweep: settings page + account deletion made explicit (Phase 0), charts + review-upvotes added as cold, no-image-uploads + no-notifications made explicit non-goals | owner: "no more features" |
| 2026-07-06 | **Status draft → accepted** (owner in-session approval: "draft 은 승격하자") — accepting = platform takes priority over FEAT-ai-editorial-critique for the program's duration | |
| 2026-07-07 | **Status accepted → in-progress** (owner in-session approval) — Phase 0 started, plan row promoted to Active | |
| 2026-07-07 | OQ1 resolved: handle = user-chosen with IdP-derived unique default. Provisioning = backend lazy-create (no post-confirmation Lambda). Phase 0 split into sub-steps 0a–0e; session scope 0a+0b | owner picks via AskUserQuestion |
| 2026-07-07 | Current-state audit found the Cognito pool-immutability risk (required email × Kakao optional consent) — research gate added before sub-step 0c | |
| 2026-07-07 | **0c research gate resolved: option (a) — Kakao 개인 개발자 비즈앱 + email 필수 동의; existing pool kept** (owner approval via AskUserQuestion). Solo devs convert self-serve via phone 본인인증; "수집 후 제공" guarantees the email claim. (b)/(c) rejected. Residual: verify `email_verified` in Kakao OIDC userinfo at implementation | web research, sources in risk bullet |
| 2026-07-07 | OAuth creds stored in SSM `/myblog/oauth/*`; Google web client created. **Public-launch gates deferred** (not 0c blockers): Google brand/domain verification (Route53 TXT + Search Console, owner-only — `claude_aws_manager` has no route53 perm) + Kakao production review. 0c builds/tests in Google Testing + Kakao dev mode with owner as test user | console setup this session |
