# FEAT-multi-user-accounts: Multi-user platform (social signup, RYM-style reviews, personalized integrations)

- **Status**: in-progress (Phases 0–3a shipped + prod-verified — **3a residual CLOSED 2026-07-12**: owner connected Last.fm, poller filled 60 real scrobble rows; Phase 4 engine shipped + cutover 5/5; **3b-a/3b-b/3b-c ALL SHIPPED 2026-07-12** — 3b-a ws #608, 3b-b V45 prod-applied + shared_db #64, 3b-c backend #113 + ws #610 + front #268, prod-smoked 401/503-fail-closed/204. **3b-d SHIPPED + INFRA FULLY APPLIED 2026-07-12** (worker #69 + ws #612; apply complete 6add/2change — owner-directed in-session self-grant via iam:PutUserPolicy, policy trimmed to key-read-only after; authed PUT flipped 503→400 = connect path LIVE, poll armed). **3b SPINE + owner connect e2e COMPLETE 2026-07-12** — 3b-e front #269 (SpotifyConnect UI) + owner real-account connect end-to-end: first real KMS encrypt/decrypt, 50 `spotify_member_recent_tracks` rows polled, rotation re-encrypt verified. **3c-a/3c-b COMPLETE 2026-07-12** — shared_db #65: V46 prod-applied (`user_id` on `spotify_stream_history`+`stream_import_runs`, 4,523+6 owner backfill) + `--user` import mode. **library_service user-scope SHIPPED 2026-07-13** — backend #114 (8 stream-history readers JWT + member-scoped) + pin hotfix #115; prod-smoked member 200×8 / unauth 401 / suite 19/0. **Privacy §2 SHIPPED 2026-07-13** (front #270). **OQ5 direction = Option 1 full merge (owner 2026-07-13) + profile-merge PR1 SHIPPED** (front #272 — dormant until member pages prebuild); contract ws #617 + front #271. **profile-merge PR2 SHIPPED + prod-smoked 2026-07-13** (front #274 — 평론 tab runtime, static-JSON owner leg, member memo path preserved). **2026-07-14 product-surface coherence audit → remediation batch SHIPPED same day** (owner adopted the recommendation set; OQ6–OQ9 resolved): public-bucket attribution (backend #116 + front #275), runtime member surface + login intent + owner-gated UI (front #276), now-playing provenance + source merge + review-author sub removal (backend #117 + front #277, ws #620/#621) — all prod-verified. PR3 preconditions (reachability, login flow, owner gating) are now met. Next concrete step: profile-merge PR3 (lyrics dock + `/profile` redirect+delete) after a short soak; then launch gates G1/G2)
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
existing pool kept; **APPLIED + verified 2026-07-08**, ws #565/#566 — see the 0c status block
below) → **0d** backend `GET/PATCH /api/me`
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
member's own @handle; ProfileApp tab row 설정 ↗ entry. **Signup entry SHIPPED 2026-07-08 as a
front follow-on to 0c** — front #253: `goLogin(force, identityProvider?)` appends
`identity_provider=Google|Kakao` to /oauth2/authorize (omit → hosted UI); the Login button opens
a popover (카카오/Google/이메일) reusing the existing `/admin/callback`. Prod clickthrough:
Login→popover→Google lands accounts.google.com, Kakao lands kauth.kakao.com — both via Cognito
`/oauth2/idpresponse`, hosted-UI picker skipped).

**Phase 0 is code-complete (2026-07-08).** 0a/0b/0c(infra+backend gate)/0d/0e + the front signup
entry are all live in prod. Everything that remains is owner-only and does not block the code:
(1) **Kakao `email_verified`** — confirm the claim on the owner's first real Kakao login
(`/v1/oidc/userinfo`; prod authorize already requests `scope=account_email`) and map it into the
IdP `attribute_mapping` if present; missing does not block sign-in. (2) **Public-launch gate** —
Google publish-to-production (Route53 TXT + Search Console domain verification, owner-only) +
Kakao production review (see the deferred-gate paragraph below). (3) **OAuth secret re-issue** —
the Google client secret + Kakao secret were pasted in-transcript during console setup; rotate
them (SSM `/myblog/oauth/*` update + targeted `terraform -replace` on the IdP, per the drift
caveat) when convenient. Opening signup to the general public is gated on (1)+(2); Phase 1 begins
independently.

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

**0c hardening — owner-gate before self-signup (found 2026-07-08 current-state audit; NOT
optional).** The backend gated all editorial-authoring, publish, genre-taxonomy, and (unscoped)
bucket/library/playback routes on `require_cognito_token` alone — i.e. "any valid pool token ==
owner", true only while the pool holds one account. Turning on self-signup fills the pool with
federated members, so those 27 routes would become member-reachable (a member could publish/delete
the owner's editorial and clobber the owner's buckets — the edge_guard routes don't check
`client_id`, so a separate member client would not have helped). Fix (backend, myblog_backend PR):
a fail-closed `require_owner` (`sub == OWNER_SUB`; local/dev bypass; 503 on unset `OWNER_SUB`; 403
non-owner) applied to all 27 single-owner routes; `/api/me`, `/api/lyrics`, and music search stay
on `require_cognito_token`. **Deploy ordering (hard):** the backend owner-gate must reach prod
(auto-deploy on merge) **before** the infra `terraform apply` flips `allow_admin_create_user_only`
to false — otherwise there is an authoring window. 0c is therefore two coordinated PRs: backend
gate merges + deploys + prod-smokes first, then the owner applies the Cognito infra. Per-user
scoping (buckets P2, listening P3) later relaxes the gate route-by-route as those tables gain
`user_id`.

**0c status — SHIPPED + APPLIED + verified 2026-07-08.** Two coordinated PRs both merged:
backend **#107** (fail-closed `require_owner` on 27 single-owner routes; deployed; prod smoke
19/0 — a member `sub ≠ OWNER_SUB` now 403s on `POST /api/posts` + `/api/publish`, hole closed)
then workspace **#565** (`infra/cognito_idp.tf` — Google native + Kakao OIDC IdPs, self-signup
on, spa_client += Google/Kakao). **`terraform apply` run by Claude with owner go-ahead**:
`2 added, 2 changed, 0 destroyed`, pool id unchanged (no replacement). Live-verified: both IdPs
present, `AllowAdminCreateUserOnly=False`, spa_client `SupportedIdentityProviders=COGNITO+Google
+Kakao`; IdP handoff curl-probed (Google→302 accounts.google.com, Kakao→302 kauth.kakao.com).
Post-apply drift fix ws **#566** (`lifecycle.ignore_changes=[provider_details]` on both IdPs —
Cognito auto-derives endpoint fields on read → was a perpetual 2-change plan; now plan clean).
Caveat: secret rotation now needs an SSM update + a targeted `-replace`.

### Phase 1 — RYM-style reviews (the differentiation) → Gate G1
`album_reviews` (user_id, album_id, rating half-steps 0.5–5.0, optional comment text,
timestamps; UNIQUE(user_id, album_id)) — new table, born scoped. Write UI on album pages,
aggregates (avg/count) on album pages, per-user public profile (`/members/[handle]`, absorbs the
old stub) with review feed. All public. Anti-abuse minimum: per-user daily review cap + owner
delete-any-review (admin claim on the owner account). Public profiles + reviews in the sitemap
(SEO = the growth channel). **Then evaluate Gate G1.**

**Phase 1 SHIPPED + prod-verified 2026-07-08** (code-complete; Gate G1 evaluation follows real
public signups). OQ2 resolved: **aggregates computed live at read time** (no denormalized counter
on `albums`). Cross-repo spine, all merged + deployed:
- **shared_db V38** `album_reviews` (born user-scoped; both FKs `ON DELETE CASCADE` so account
  deletion drops owned reviews at the schema level; `mod(rating,0.5)=0` half-step CHECK;
  UNIQUE(user_id,album_id) = the "edit my review" upsert key). Prod-applied + verified (#54).
- **backend #108** reviews API: `PUT`/`DELETE /api/reviews/albums/{album_id}` (member, lazy-
  provision), `DELETE /api/reviews/{review_id}` (owner `require_owner`), public `GET
  /api/reviews/albums/{album_id}` aggregate + `GET /api/members[/{handle}]`. Anti-abuse =
  per-member rolling-24h create cap (`REVIEW_DAILY_CAP=50`; edits exempt) → 429. GET routes ride
  the edge_guard catch-all; the 3 mutations got API GW JWT routes (ws #573 apply, 3 add/0/0).
- **front #257**: `AlbumRatingBlock` (aggregate + 0.5-step write panel) on every album surface via
  `AlbumDetailView.topSlot`; `MemberProfile` island + `/members/[handle].astro` (getStaticPaths
  prebuild, in the sitemap). **Static-generation caveat**: a new member's profile page appears
  only on the next deploy (no SSR — infra re-platform is a non-goal); the album-overlay aggregate
  + write work immediately. At launch the member index is empty by design.
- **Prod smoke (via CloudFront + minted member JWT)**: PUT→aggregate 4.0/1→profile feed→member
  index→edit(in-place, count stays 1)→delete→0; invalid half-step 4.3→422; real-browser
  clickthrough (overlay write panel + `/members/[handle]` render) then cleaned up (album_reviews
  back to 0). Owner-only residual: none — Gate G1 is a post-public-launch metric.

### Phase 2 — Per-user buckets/to-listen
`user_id` on `review_buckets` + `review_bucket_items` + `album_to_listen_items` (nullable →
backfill owner → NOT NULL; plain `V{N}__` SQL, rollout order per
`reference-shared-db-cross-repo-rollout`), owner filtering threaded through bucket/library
routes (`resolve_owner()` output finally consumed), `/api/buckets/public` + `/collection` grow a
user dimension. Spotify-lane tables are NOT touched here.

**Phase 2 (step 1) SHIPPED + prod-verified 2026-07-08** — per-user scoping of the existing
bucket/to-listen surfaces (NOT NULL flip = step 2, after a backfill soak):
- **shared_db V40** — nullable `user_id` on `review_buckets` + `album_to_listen_items`, owner
  backfill, per-user unique re-scope; `review_bucket_items` transitive (inherits owner via the
  bucket). Prod-applied + verified (#56).
- **backend #109** — `provisioned_member_id` scoping threaded through the bucket routes; the
  owner's Spotify-library sync stays owner-only (Phase 3 scopes its tables).
- **ws #582** — `GET /to-listen` moved from the catch-all onto HTTPBearer (member-scoped read).
**Prod smoke**: a member `GET /api/buckets` returns 0 buckets — their own empty board, NOT the
owner's 6 → per-user scoping confirmed live. The NOT NULL flip is deliberately step 2 (post-
backfill soak); the nullable column is the safe additive state.

**Public-read user dimension SHIPPED 2026-07-14** (the "`/api/buckets/public` + `/collection`
grow a user dimension" leg, found un-done by the 07-14 audit): `list_public_buckets` joins
`users` and the additive `PublicBucket.owner {handle, display_name}` attributes every published
shelf; `/collection` renders the attribution and drops the 저자가 framing; privacy §5 corrected
(buckets are public only when the member opts in). Merge order: workspace contract → backend
(deploy) → front.

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

**Phase 3a (Last.fm) SHIPPED + prod-verified 2026-07-08** — the username-only connect + now-
playing read, worker per-user poll, and the front now-playing widget are all live; **no sync
Last.fm call on any user-facing endpoint** (rule #9 — the worker pulls, the API only reads). 3b
(Spotify 5-user tier) and 3c (GDPR-export upload) remain unbuilt.
- **shared_db V41** — `user_integrations` (OQ4 = one table; holds Last.fm username now, the
  Spotify-token + AI-key shapes later) + `lastfm_recent_tracks` (per-user recent-tracks cache).
  Prod-applied + verified (#57).
- **backend #110** — `/api/integrations` connect/disconnect/list + `/lastfm/now-playing`
  (self-scoped GET; reuses the reviews pattern — member lazy-provision). Connect writes the
  username; disconnect clears the row.
- **worker #67** — per-user `user.getRecentTracks` poll: raw SQL/no pin bump, fetch→close,
  NOT-EXISTS dedup, prod-SQL-validated. The poll is **dormant until the owner sets
  `LASTFM_API_KEY`** in SSM `/myblog/worker` (the handler guards on it) — by design, so the
  live-scrobble path is only observable post-key.
- **ws #583** — contract + apigateway JWT routes for the two member mutations
  (PUT/DELETE `/api/integrations/lastfm`; the GETs ride the edge_guard catch-all) + the
  EventBridge rule (15-min `lastfm_recent_tracks` job, copies the spotify_listening pattern —
  no-op until the key lands). Terraform applied by the owner: 5/0/0.
- **front #260 + #261** — #260 settings 연동 Last.fm connect field + `api.gen.ts`; #261
  `LastfmNowPlaying` opt-in dashboard widget (states 미연동·오류·재생 중·재생 중 아님).
**Prod smoke**: connect→list→now-playing→disconnect all 200/204; real-browser CDP click-through
of the widget's 4 states (0 console errors); prod bundle carries the wiring.
**OWNER RESIDUAL (non-blocking, sole remaining 3a item)**: set `LASTFM_API_KEY` in SSM
`/myblog/worker` — until then the worker poll + the dormant eventbridge rule no-op and the
widget rests on idle/미연동 (by design).

**Phase 3b/3c design — LOCKED 2026-07-12 (current-state audit + owner decisions in-session;
implementation not started).** Audit verified: V41 pre-provisioned 3b's token store
(`user_integrations` provider CHECK already allows `'spotify'`, status CHECK already models
`'reauth'`, `payload TEXT` reserved for KMS-envelope ciphertext) — no schema change for token
custody; `spotify_stream_history` has NO `user_id` (V27 unique = `(ts, spotify_track_uri)`);
infra has NO customer-managed KMS key (only the AWS-managed SSM alias); the Spotify app is
dashboard console-managed (zero TF); 분석 `library_service` stream readers are global-scoped
(fine while owner-only). Owner decisions (2026-07-12, AskUserQuestion):

1. **3b member listening data = born-scoped NEW tables** (mirror the 3a
   `lastfm_recent_tracks` pattern: per-user recent rows + single now-playing row) — the
   owner-global `spotify_*` caches and their 3 worker jobs stay untouched; folding the owner
   lane in is a later pass.
2. **3b token custody = new customer-managed KMS CMK** (per the original Phase-3 lock):
   `aws_kms_key` + alias in TF, Encrypt grant to the backend role (connect path),
   Encrypt+Decrypt to the worker role (poll + rotation re-encrypt). Owner applies
   (`claude_aws_manager` may lack kms:* — warn at PR).
3. **3c intake v1 = owner-run `import_streaming_history.py --user <sub>` mode** (zero infra;
   GDPR delivery lag makes this a power-user ritual, demand-validating). Self-serve upload
   (S3 presigned + async parse — export zips can exceed the API GW 10 MB limit) deferred
   until demand.
4. Scope note: 3b v1 syncs **now-playing + recently-played reads only**; member saved-tracks
   sync and member ▶ playback (Premium-per-listener) are explicitly NOT in the first spine —
   revisit inside the 5-user tier after the read path proves out.

Sub-steps (each rule-4 gated): **3b-a** infra KMS CMK + grants (**SHIPPED 2026-07-12** ws #608:
`aws_kms_key.user_tokens` rotation-on/30d-window + `alias/myblog-user-tokens` + key-ARN-scoped
role policies — backend Encrypt+GenerateDataKey, worker +Decrypt; plan 4add/0/0; **owner
`terraform apply` pending** — merging changed nothing in prod) → **3b-b**
shared_db V45 born-scoped member listening tables (**SHIPPED 2026-07-12** shared_db #64,
prod-applied pre-merge: `spotify_member_recent_tracks` FULL UNIQUE(user_id, played_at,
spotify_track_id) + `spotify_member_now_playing` PK=user_id; pytest 91/91) → **3b-c** backend
`PUT/DELETE /api/integrations/spotify` (**SHIPPED 2026-07-12** backend #113 + ws #610 routes
applied + front #268 api.gen.ts; server-side code exchange, KMS-envelope →
`user_integrations.payload` `{v, ciphertext, scope, expires_in, obtained_at}` — the 3b-d
decrypt contract; fail-closed matrix prod-smoked: unauth 401 / authed **503
dormant-but-safe while the CMK is unapplied** (config gate fires before any outbound call —
the one-time code is not burned) / DELETE 204; `SPOTIFY_MEMBER_REDIRECT_URI` =
`https://www.ratemymusic.blog/settings/spotify/callback` — the exact string the owner must
register in the Spotify dashboard; lambda env `USER_TOKENS_KMS_KEY_ID` rides the owner's
pending CMK apply) → **3b-d** worker per-user poll (**SHIPPED 2026-07-12** worker #69 +
ws #612: `{"job":"spotify_member_poll"}` rate(15 min), KMS decrypt → refresh →
rotate/re-encrypt (persisted before player reads) → V45 writes; `invalid_grant` ⇒
`status='reauth'` never retried, infra failures never touch status, plaintext never
written; raw SQL/no pin bump; 328 tests; prod manual invoke = clean 0-user no-op —
dormant until CMK + connected members; eventbridge target/permission ride the owner
apply batch) → **3b-e** front
`SpotifyConnect` + callback + reconnect badge (`status==='reauth'`) + `api.gen.ts`.
**3c-a** shared_db V{N} `user_id` on `spotify_stream_history` + `stream_import_runs`
(nullable → owner backfill → unique re-scope `(user_id, ts, spotify_track_uri)` → NOT NULL
flip after soak, the V40/V42 pattern; FK CASCADE so account deletion reaches listening
history) → **3c-b** `--user` mode threading user_id through parse/insert/resolve/ledger →
(**3c-c** self-serve upload — deferred). Cross-cutting before member exposure of 분석:
user-scope the `library_service` stream readers; update 개인정보처리방침 for member
listening-history custody + the deletion path. **Owner console prerequisites (can run
anytime before 3b-c)**: Spotify dashboard — add the front callback redirect URI + register
the ≤5 allowlist users (User Management); owner stays Premium.

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

**Phase 4 design — MERGED 2026-07-08 (ws #584), implementation awaits owner confirm.** An
`architect` subagent evaluated the §Phase 4 design against all 5 live `claude -p` call sites +
the 3 service `requirements.txt` + shared_db `pyproject.toml`. Decisions (full detail in
`docs/rfcs/FEAT-multi-user-accounts-p4-llmengine.md`): engine home =
`myblog_shared_db/src/myblog_shared_db/llm/` (the one shared import surface both poller
families already reach via local src → **zero git pin bump**); interface = one ABC
`LLMEngine.run(job: LLMJob) -> LLMResult` with `output_schema` defaulting None (the 5 live sites
keep their bespoke extractors; structured output fires only for new ApiEngine callers); error
split = a raised exception hierarchy (`LLMTransientError`/`LLMValidationError`/`LLMQuotaError`,
lifted from the existing `lyrics_translate_poller`), not a buried flag. **This pass scopes to
owner-central scaffolding only; BYOK / `user_api_keys` deferred to Gate G2.** No code lands
until the owner confirms the design.

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
2. ~~**Rating aggregate placement** (blocks Phase 1)~~ — **RESOLVED 2026-07-08 (implementation)**:
   live query (avg/count over `album_reviews`, `idx_album_reviews_album_id`). No denormalized
   counter on `albums`; revisit only if read QPS proves it out (it won't at launch scale).
3. ~~**BYOK provider set for v1** (blocks Phase 4)~~ — **RESOLVED 2026-07-11 (owner)**:
   **Anthropic-only v1**, adapter designed for four (Decisions log 2026-07-11, Phase 4
   scaffolding entry — owner confirmed in-session via AskUserQuestion).
4. ~~**`user_integrations` shape** (blocks Phase 3)~~ — **RESOLVED 2026-07-08
   (implementation)**: **one table** — shared_db V41 `user_integrations` holds the Last.fm
   username now and the Spotify-token + AI-key shapes later (Decisions log 2026-07-08,
   Phase 3a entry).
5. ~~**Owner data migration UX** (blocks Phase 2/3)~~ — **RESOLVED 2026-07-08 (owner)**: the
   owner account is a **regular member** — owner data backfills to the owner user row (V40
   pattern); `/profile` retires in favor of `/members/[owner-handle]` as member scoping lands.
6. ~~**Member-page reachability model** (blocks the rescoped profile-merge PR3)~~ —
   **RESOLVED 2026-07-14 (owner adopted the recommendation set; option (a) SHIPPED front
   #276)**: runtime member surface at `/members/` — no param = member directory (runtime
   fetch), `?u=<handle>` = runtime profile for ANY provisioned user, `?me` = self; static
   `[handle]` pages stay for SEO. Prod-verified: a 0-review provisioned user's profile renders
   with no deploy dependency. Original finding (2026-07-14 audit): `/members/[handle]` is `getStaticPaths`-prebuilt from `GET /api/members`,
   which INNER-JOINs reviews (zero-review members excluded) and is empty in prod → **every
   member page 404s, including the owner's and a brand-new member's own**. A runtime-created
   user cannot see any profile until they review AND the next deploy runs. Options: (a) a
   runtime member page (e.g. query-param route or client-side takeover) with static pages kept
   for SEO, (b) index all users (still deploy-lagged), (c) deploy trigger on first review,
   (d) SSR re-platform (RFC non-goal). Blocks retiring `/profile` — it is currently the only
   working self-dashboard.
7. ~~**Last.fm listening attribution**~~ — **RESOLVED 2026-07-14 (owner adopted the
   recommendation set; SHIPPED backend #117 + front #277)**: public now-playing carries
   provenance (`source` + `source_username`, shown only while playing — the idle
   `{is_playing:false}` privacy collapse is unchanged, so integration status stays private
   when idle) AND merges the Spotify member source (V45) with Last.fm, actively-playing
   winner. Spoofing remains possible by design (no OAuth) but is now publicly attributed to
   its Last.fm source. Original finding: username-only connect means any member can claim any
   Last.fm account (a celebrity's, another member's) and `GET /api/members/{handle}/now-playing`
   publicly displays that listening as theirs. Inherent to the no-OAuth model (accepted
   decision 6); mitigation options: none (accept), show provenance ("via Last.fm @username") on
   public surfaces — note this conflicts with the 07-11 decision to keep integration status
   private — or a soft profile-existence+recency heuristic. Also: the public now-playing route
   reads `lastfm_recent_tracks` only — a Spotify-connected member's now-playing (V45) never
   shows publicly; decide whether to merge sources.
8. ~~**Bucket publicness model vs decision 3**~~ — **RESOLVED 2026-07-14 (owner adopted the
   recommendation set): decision 3 is amended — buckets are opt-in public (the `is_public`
   toggle is the product), attributed to their owner on `/collection`; reviews/ratings stay
   unconditionally public; to-listen stays private.** Shipped alignment: backend #116 + front
   #275 + privacy §5. Original finding: decision 3 said "everything public, no
   visibility column", but `review_buckets.is_public` (V18, pre-RFC) survived P2: member
   buckets are **private by default** with an opt-in 공개 toggle, and to-listen has no public
   projection at all. 2026-07-14: the public read + `/collection` + privacy §5 were aligned to
   the *toggle* reality (attributed, opt-in). Decide whether decision 3 is amended (buckets =
   opt-in public) or the toggle is to be removed later.
9. ~~**Owner editorial vs community ratings (two rating systems)**~~ — **RESOLVED 2026-07-14
   (owner adopted the recommendation set): Canon/BNM/`/reviews`/home stay owner-editorial
   ("저자" framing is intentional and stays); a community-ratings dimension (charts, member
   review feeds beyond the per-album aggregate) is deferred until Gate G1 holds.** Original
   finding: `/canon` (명반 전당, ★4.0+
   threshold), Best New Music, `/reviews`, and the home feed are all built from the owner's MDX
   collection only; member `album_reviews` appear nowhere except the per-album aggregate.
   "저자가 ★4.0 이상을 준 앨범" copy is single-author by design, but decide the long-term
   relationship (keep Canon owner-editorial-only and label it as such, or grow a community
   dimension after Gate G1).

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
| 2026-07-08 | **0c audit found a privilege-escalation gap: self-signup would expose 27 single-owner backend routes to any member** (they gated on `require_cognito_token` = any pool token). Added fail-closed `require_owner`; backend PR must deploy BEFORE the infra apply (owner approval via AskUserQuestion). 0c = 2 coordinated PRs (backend gate → infra) | current-state audit; auth boundary |
| 2026-07-08 | **0c SHIPPED + APPLIED + verified**: backend #107 (owner-gate deployed, prod smoke 19/0) → ws #565 (Cognito self-signup + Google/Kakao IdPs, apply 2 add/2 change/0 destroy, no pool replacement) → drift fix ws #566 (`ignore_changes=provider_details`). IdP handoff curl-probed both IdPs | Claude applied with owner go-ahead |
| 2026-07-08 | **Front signup entry SHIPPED** (front #253): `goLogin` optional `identity_provider` deep-link + Login popover (카카오/Google/이메일), reuses `/admin/callback`. Prod clickthrough — Google→accounts.google.com, Kakao→kauth.kakao.com, hosted-UI picker skipped. **Phase 0 code-complete.** Residual (owner-only): Kakao `email_verified` live-check, public-launch gate (Google prod publish + Kakao 심사), OAuth secret rotation | popover placement picked by owner via AskUserQuestion |
| 2026-07-08 | **Phase 1 (RYM reviews) SHIPPED + prod-verified** — shared_db V38 `album_reviews` (prod-applied #54) → backend #108 (reviews CRUD + live aggregate + `/members` feed + daily cap; API GW routes ws #573 apply 3/0/0) → front #257 (album rating block + `/members/[handle]`). OQ2 = live query. Full prod smoke + browser clickthrough, cleaned up. Gate G1 evaluation deferred to post-public-launch. Owner OK'd running all steps + push/merge this session (rule #4 gate waived, DB prod-apply observed) | cross-repo spine, 4 PRs |
| 2026-07-08 | **Phase 2 (per-user buckets, step 1) SHIPPED + prod-verified** — shared_db V40 (nullable `user_id` on `review_buckets` + `album_to_listen_items`, owner backfill, per-user unique re-scope; prod-applied #56) → backend #109 (`provisioned_member_id` scoping; Spotify-library owner-only) → ws #582 (`GET /to-listen` → HTTPBearer). Prod smoke: a member `GET /api/buckets` returns 0 (their own board, not the owner's 6). NOT NULL flip = step 2, post-backfill soak (the nullable column is the safe additive state) | cross-repo spine, 3 PRs |
| 2026-07-08 | **Phase 3a (Last.fm) backend+worker+contract+infra SHIPPED + prod-verified** — shared_db V41 (`user_integrations` [OQ4=one table] + `lastfm_recent_tracks`; prod-applied #57) → backend #110 (`/api/integrations` connect/disconnect/list + `/lastfm/now-playing`, self-scoped; **no sync call** — rule #9) → worker #67 (per-user `user.getRecentTracks` poll, raw SQL/no pin bump, fetch→close, NOT-EXISTS dedup) → ws #583 (contract + apigw PUT/DELETE JWT routes + eventbridge rule 15min; terraform applied 5/0/0) → front #260 (settings connect field + `api.gen.ts`). Prod smoke: connect→list→now-playing→disconnect 200/204. **Owner residual (non-blocking)**: `LASTFM_API_KEY` in SSM `/myblog/worker` — until then the worker poll + dormant eventbridge rule no-op, the widget rests on idle/미연동 (by design) | cross-repo spine, 5 PRs |
| 2026-07-08 | **Phase 3a now-playing widget SHIPPED** (front #261) — `LastfmNowPlaying` opt-in `OverviewDash` dashboard widget consuming the existing self-scoped `GET /api/integrations/lastfm/now-playing` + `getIntegrations`. Front-only (type already in `api.gen.ts`; no contract/infra). States 미연동(→/settings)·오류·재생 중·재생 중 아님 + ↻. Not in `DEFAULT_ROWS` (opt-in, no owner/Spotify-dashboard clutter). Endpoint self-scoped → own `/profile` only; public `/members/[handle]` now-playing = later follow-on (needs a handle-scoped route). Verified: lint + astro check + build + real-browser CDP all 4 states (0 console err); prod bundle carries the wiring. This closes the last Phase 3a code item — sole remaining 3a residual = owner sets `LASTFM_API_KEY` in SSM `/myblog/worker` (live scrobble path dormant until then) | front-only, opt-in dashboard widget |
| 2026-07-08 | **Phase 4 (LLMEngine) design MERGED** (ws #584) — `architect` eval of §Phase 4 against all 5 live `claude -p` call sites + service deps. Engine home = `myblog_shared_db/.../llm/` (zero pin bump), interface = one ABC `LLMEngine.run(job) -> LLMResult` (`output_schema` defaults None so live sites keep bespoke extractors), errors = raised exception hierarchy. This pass = owner-central scaffolding only; BYOK/`user_api_keys` → Gate G2. **Implementation awaits owner confirm — no code lands yet.** Full detail → `docs/rfcs/FEAT-multi-user-accounts-p4-llmengine.md` | design doc, architect eval |
| 2026-07-08 | **OQ5 resolved: the owner is a regular member** (no special-cased member identity); `/profile` retires toward `/members/[owner-handle]` as member scoping lands | owner data backfills to the owner user row (V40 pattern) |
| 2026-07-11 | **Phase 2 step 2 SHIPPED + prod-applied** — shared_db **V42** flips `user_id` to NOT NULL on `review_buckets` + `album_to_listen_items` (#58; version 0.33.0). Soak evidence: 3 days post-V40, 0 NULL rows both tables; write-path sweep confirmed every live insert sets `user_id` (worker only writes transitively-owned `review_bucket_items`). Prod BEGIN…ROLLBACK dry-run → apply → verified (`attnotnull=true` ×2, buckets=6 intact). Companion worker #68 fixes the one V42-incompatible integration fixture (seeds a throwaway `users` row). Phase 2 data model complete | shared_db #58 + worker #68, parallel-session track B |
| 2026-07-11 | **Phase 4 scaffolding SHIPPED + V43 prod-applied** — owner confirmed the design + **OQ3 = Anthropic-only v1** in-session (AskUserQuestion). shared_db **#59** (version 0.34.0): `llm/` subpackage (interface/exceptions/cli_engine/api_engine skeleton/metering), **V43 `llm_usage`** (append-only; prod dry-run → applied → verified), `[llm-api]` optional extra — `[project]` stays SQLAlchemy-only, no pin weight. pytest **91/91** incl. byte-identical golden-argv tests for all 5 live `claude -p` sites (buckit_nightly 11-disallow + `--setting-sources user` atomic; backfill no-`--model`; lyrics no-`--output-format` → `output_mode=None`). No live poller edited. Residual: `/myblog/anthropic` SSM provisioning + one real-engine session-lifecycle test at first real ApiEngine caller; live-site cutover = later one-at-a-time golden-diff PRs; BYOK = Gate G2 | shared_db #59, parallel-session track A |
| 2026-07-11 | **Phase 3a residual burned down**: owner provided the Last.fm API key in-session → `LASTFM_API_KEY` merged into SSM `/myblog/worker` (existing keys preserved; worker Lambda redeployed same minute via #68 merge, cold start reads it). Remaining 3a = owner connects a Last.fm username on `/settings/` (then verify `lastfm_recent_tracks` fill + widget). **Phase 0 residual progress**: owner's first real Kakao login attempt failed **KOE205** (unconfigured consent-item request; we request `openid account_email profile_nickname`) → owner console checklist issued (OIDC toggle ON / 비즈앱 전환 + email 동의항목 / redirect URI). `email_verified` live-check still pending on a successful login | SSM write + diagnosis, parallel-session tracks C/D |
| 2026-07-11 | **Kakao login LIVE-VERIFIED — Phase 0 `email_verified` residual CLOSED.** Owner fixed the console per the KOE205 checklist and completed a real Kakao login: Cognito federated user `kakao_4986059004` created (sub `14d89d7c-…`), **email claim present** (`zlxldgus123@naver.com` — the 0c "수집 후 제공" guarantee confirmed live), **`email_verified=false`** as designed (claim intentionally unmapped in `cognito_idp.tf`; Kakao OIDC userinfo doesn't provide it; not sign-in-blocking, no member flow depends on Cognito email verification). DB lazy-provisioning confirmed: `users` row id=sub, `handle user-14d89d7c`, email NULL (access token carries no email claim — 0d design). **Remaining Phase 0 = public-launch gates only** (Google brand verification, Kakao 프로덕션 심사, OAuth secret reissue) | live Cognito + prod DB evidence |
| 2026-07-11 | **P4 cutover #1 SHIPPED** — `research_poller` moved off inline `claude -p` onto `myblog_shared_db.llm.CliEngine` (ws #597; argv byte-identical per golden tests 25/25; launchd pipeline uninterrupted — 2 post-merge cycles clean). Known delta: `search_count` always 0 (field documented unreliable since 2026-06-11). Remaining 4 sites (lyrics/genre prod-data validators, buckit_nightly secret guard, editor_buckit) = later one-at-a-time PRs. Detail → `FEAT-multi-user-accounts-p4-llmengine.md` Cutover log | parallel-batch Track 1 |
| 2026-07-11 | **Phase 3a follow-on SHIPPED — public `/members/[handle]` now-playing** (the handle-scoped route anticipated in the 07-08 widget entry). `GET /api/members/{handle}/now-playing` (backend #112, reuses `LastfmNowPlayingResponse`; unknown handle 404; 미연동 and idle both `{is_playing:false}` — integration status stays private; rule #9 clean — reads only worker-written `lastfm_recent_tracks`; rides the GET catch-all, no apigateway.tf change) → contract ws #599 → front #265 strip on the member profile (renders only on `is_playing:true`, else fully hidden). pytest 457 pass; both UI states CDP-verified pre-merge; prod: route live (404 body from the route), member pages structurally absent until a member posts a review (`getStaticPaths` off the empty member index) | parallel-batch Track 2, 3 PRs |
| 2026-07-12 | **P4 live-site cutover COMPLETE (5/5)** — final site `backfill_genres` → CliEngine (shared_db #61; golden-argv byte-parity + live trivial dispatch pre- and post-merge; known delta: timeout/exit≠0/empty now transient-retried→fail-closed None instead of killing the run). All 5 `claude -p` sites now dispatch through `myblog_shared_db.llm.CliEngine`. Detail → `FEAT-multi-user-accounts-p4-llmengine.md` Cutover log 5 | shared_db #61, parallel-batch |
| 2026-07-12 | **Phase 3b/3c design LOCKED (owner in-session, AskUserQuestion ×4)** — (1) 3b member listening = born-scoped new tables (3a pattern; owner-global `spotify_*` untouched); (2) token custody = new customer-managed KMS CMK + role grants (V41 `payload` was pre-provisioned — no schema change); (3) 3c intake v1 = owner-run `import_streaming_history.py --user` mode (self-serve S3 upload deferred until demand); (4) tonight = design recorded only, implementation next sessions. Current-state audit facts + sub-steps 3b-a…3b-e / 3c-a…3c-b recorded in §Phase 3. Owner console prereqs: Spotify dashboard redirect URI + ≤5-user allowlist | design pass, no code |
| 2026-07-13 | **library_service user-scope SHIPPED + prod-verified** — backend #114: all 8 `/api/library/stream-history/*` readers JWT-required + strictly member-scoped (`provisioned_member_id` pattern); live tail from `spotify_track_play_events` owner-gated, fails closed on unset `OWNER_SUB`. Hotfix backend #115: the deployed shared_db pin (eadb952, V41-era) predated the V46 model attribute → all 8 readers 500'd in prod ~30 min; pin bumped to 2b5180e (0.37.0). Test-escape root cause: local venv held a newer shared_db than the pin — hotfix verified in a clean venv installed strictly from requirements.txt. Prod smoke: member JWT → 200 with zero rows on all 8; unauth → 401; full suite 19/0 | backend #114 + hotfix #115 |
| 2026-07-13 | **개인정보처리방침 §2 SHIPPED** (front #270) — member listening-data collection, KMS custody, and the deletion path documented against the V41/V45/V46-verified `ON DELETE CASCADE` chain; prod-verified | front #270 |
| 2026-07-13 | **OQ5 implementation direction DECIDED** (owner via mockup gate): **Option 1 full merge** — `/members/[handle]` absorbs the dashboard behind an authed isSelf gate; `/profile` eventually redirects then deletes. **Profile-merge PR1 SHIPPED** (front #272): self-view tabs 개요/My Buckit/분석 버킷/연동 on the member page, React.lazy chunk split (public chunk 7.8 KB), fail-safe public on any auth error; dormant in prod until member pages prebuild (prod `/api/members` currently empty). 평론 runtime rebuild = PR2; lyrics dock + `/profile` redirect = PR3 | front #272; contract ws #617 + api.gen front #271 |
| 2026-07-13 | **PR2 owner-평론 runtime source DECIDED** (owner via AskUserQuestion, audit-informed): **build-time static JSON** (`profile-reviews.json.ts`, prerendered from `getCollection` via a mapper extracted from profile.astro — search-index.json precedent). Front-only, zero contract/infra churn, exact `MemberReview[]` parity for all four consumers (ReviewsTab / OverviewDash 최근 평론 / BucketBoard chips / AlbumDetail 발행 배너); posts-API extension noted as the runtime-first successor if freshness ever matters. Rejected: public posts endpoint (owner-special-cased contract), per-post hydrate (N+1) | PR2 design |
| 2026-07-13 | **Owner signal on member pages DECIDED** (owner): build-time owner-handle constant (`user-0468fd3c`, the auto-provisioned prod row) compared against `getMe().handle` — front-only, pairs with the static-JSON choice; `MEMBER_IDENTITY.handle='buckit'` is a front-side fiction and must not gate anything. 403-probe and `is_owner` contract field rejected (per-page request / contract churn) | PR2 design |
| 2026-07-13 | **Audit finding flagged to owner**: prod has ZERO published 평론 anywhere (0 MDX in content/blog on main, posts table 4 rows all draft, 0 album_reviews, live search-index.json `[]`) — predates PR2; the 평론 surfaces are empty in prod regardless. PR2 correctness proven via local fixture; owner chose to proceed | PR2 scope |
| 2026-07-13 | **profile-merge PR2 SHIPPED + prod-smoked** (front #274, deploy 29215222813): 평론 tab hosted in the member self-dashboard — owner leg = `/profile-reviews.json` (200 `[]` live; fixture-proven non-empty), member leg = mapped rating rows (보기→overlay, 수정/삭제 hidden); OverviewDash 최근 평론 / BucketBoard chips / AlbumDetail 발행 배너 fed runtime data (fixes the PR1 MemoWindow-vs-banner gap); follow-up commit post-gates the published matcher on `slug !== ''` (owner-decided — member ratings keep the memo path). Public chunk 7,873 B (no growth). CDP 8-scenario + post-fix re-verify. Still dormant until member pages prebuild. **Next = PR3** (lyrics dock + /profile redirect+delete) | front #274 |
| 2026-07-14 | **Product-surface coherence audit (full-stack) + PR3 RESCOPE.** Backend/data model is multi-user; the product surface still runs single-owner in load-bearing places. **Verified problems**: (1) member-page reachability dead end — `/members/*` all 404 in prod (empty reviewer-only index × static prebuild), a new member has NO reachable profile → OQ6; (2) `/profile` shows every member the owner fiction (`MEMBER_IDENTITY` 'buckit') + owner MDX 평론 as their own, and the header avatar + Pocket tray + `/buckets` redirect all route members there; (3) post-login always `location.replace('/')` — pre-login intent (e.g. rating an album) lost, and `AlbumRatingBlock` shows anon users NO login CTA; (4) `isLoggedIn()` used as an owner proxy (`TodaySongBuckit` et al., write-link, play ▶) → members see owner controls that 403; (5) `GET /api/buckets/public` had NO user dimension — any member's 공개 bucket landed anonymously in the owner-framed `/collection` (**FIXED this session**: backend joins users, `PublicBucket.owner{handle,display_name}` additive contract, front attributes each shelf + copy 저자가→회원들이, privacy §5 bucket claim precision + 시행일 2026-07-14); (6) Last.fm spoofing/attribution + Spotify-now-playing gap → OQ7; (7) two rating systems (owner MDX drives Canon/BNM/home; `album_reviews` invisible outside per-album aggregate) → OQ9; (8) member discovery loop absent (no directory, no cross-user feed; only the 404-blocked handle links). **Checked NOT problems**: backend row-level isolation (buckets/to-listen/stream-history/integrations), Spotify OAuth+KMS custody, deletion CASCADE chain, member email/integration-status privacy, music repo. **Rescope**: PR3 (`/profile` redirect+delete) is premature — reachability (OQ6) + login flow + front owner-gating must land first; `/profile` is currently the only working self-dashboard. Minor backlog: public review author `id` = Cognito sub (drop from contract), `user-<sub8>` handle defaults read as placeholders on public surfaces, rate-limit coverage beyond reviews | audit session; fix branches: backend `fix/multi-user-public-bucket-attribution`, front `fix/multi-user-collection-attribution`, ws `chore/multi-user-surface-audit` |
| 2026-07-14 | **Audit remediation batch SHIPPED + prod-verified (owner: "다 추천으로 작업하고 병렬 실행으로 모두 다 해결하고 푸시머지" — recommendation set adopted, OQ6–OQ9 all resolved).** Serial-merged: ws #620 (audit record + PublicBucket.owner contract) → backend **#116** (public-bucket attribution; prod: `/api/buckets/public` carries owner) → front **#275** (/collection attribution chip `@user-0468fd3c · 44장` live + 회원들이 copy + privacy §5 bucket precision, 시행일 07-14) → front **#276** (Track 1, parallel-built: runtime member surface `/members/` [directory + `?u=` + `?me`] — prod-verified a 0-review user's profile renders; login returnTo capture/consume; anon 평가 CTA; my-review keyed by handle; `isOwnerUser()` gating on 글쓰기/오늘의 곡/Pocket ▶; per-role avatar target) → ws #621 (contract) → backend **#117** (Track 2, parallel-built: `MemberNowPlayingResponse` — Last.fm+Spotify merged, provenance `source`/`source_username` only while playing, idle collapse intact; `ReviewAuthor.id` Cognito-sub removed AFTER #276 deployed — removal order held) → front **#277** (strip `via Last.fm @user` / `via Spotify`; bundle marker verified). Full suites green each hop (backend 487→493, front lint/check/build + CDP fixture runs). Residuals: owner live-login returnTo round-trip observation; Pocket ▶ gate visual check; `/buckets` now targets `/members/?me&tab=bucket` for everyone (flagged); OQ4-era backlog (rate limits beyond reviews, `user-<sub8>` display names) unchanged | 2 fork tracks in worktrees + serial merges, owner-approved batch |
