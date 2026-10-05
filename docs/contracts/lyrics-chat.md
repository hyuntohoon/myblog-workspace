# MyBlog translations in Chat

Owner authorized this change on 2026-10-05. The translation executor moves to
Chat; source collection, discovery history, existing translations and the viewer
remain. This document is a single coordinated rollout, not permission to start
background translation.

## Behavior

The private MCP connection offers `prepare_translation`, `submit_translation`,
and `stop_translation`. Each preparation names exactly one Spotify catalog track
and optionally one Genius annotation. There is no queue-list or queue-drain tool,
schedule, event subscription, model API call, shell access or arbitrary DB access.
Ask in Chat to translate a named track; reuse completed results. The site's old
translation button still only records a request: it does not wake a Chat.

The server permits at most two admissions per source/version and ten conservative
admissions per UTC day. The day counter sums attempts of Chat work updated today;
completion of old work can overcount, never provide precise inference billing.
A refusal or cancellation stops that source immediately. Format/temporary errors
may be retried only by a new explicit preparation, within the same limits.

V57 work rows retain the UUID claim and 20-minute lease. There is no transaction
across GPT inference. Completion locks and rechecks the source, validates every
index/gap, completes work and publishes in one transaction. Newer requests and
manual edits win. A new explicit preparation can publish a cached result that lost
an earlier request race, without another model call; manual edits remain protected. Machine results retain `origin=poller`; `model=chatgpt` and
`translator_version=chatgpt/lyrics-ko-v1` or `chatgpt/genius-ko-v1` record provenance
without inventing the actual Chat model. Existing completed translations are reused.

The historical Claude entrypoints and backfill return before DB/model work.
Imported translation dispatch fails closed too. The demand selector
also excludes Chat versions. Installed launchd jobs must remain disabled. The runtime
worktree must receive the entrypoint changes before treating the repository guard as
installed protection. Spotify demand/source producers are retained; their pending
rows cannot cause Chat translation by themselves.

## Authentication

The transport lives at the API Gateway invoke origin's `/mcp`, outside `/api`.
Existing SPA client allowlists, Gateway authorizers and canonical auth verifier
remain unchanged. Every MCP request requires an access token from the real Cognito
pool, for the dedicated Chat client, with `aud` exactly the MCP URL,
`myblog-chat/translate` scope, unexpired token and the configured owner's `sub`.
There is no local/dev authentication bypass on this connection.

Cognito's native discovery lacks the S256/none metadata needed by ChatGPT. The
OAuth-only metadata adapter at `/.well-known/oauth-authorization-server/mcp-auth`
uses this service's `/mcp-auth` issuer and delegates authorization, token and
revocation endpoints directly to the fixed Cognito hosted domain. JWT issuer
validation separately pins the actual Cognito pool. The adapter does not claim to
be OIDC, support dynamic client registration, or return RFC9207 `iss` responses.
ChatGPT must use a predefined public client and PKCE; the exact callback-ID URI
comes from the connection page, not a guessed generic redirect.

## Rollout and verification

1. Run the full backend suite and real PostgreSQL regression tests, export backend
   OpenAPI, merge contracts, and run workspace invariants and Terraform validation.
2. Run a FULL Terraform plan. The checked sanitized plan records an unrelated
   worker setting: live `LYRICS_MEMBER_DEMAND_ENABLED` is unset (application default
   true), while Terraform declares true. This has no effective behavior change but
   needs owner review under AGENTS.md's unexpected-drift rule. Do not target resources.
   The default empty callback list creates no OAuth client and keeps tools disabled.
3. Once the infrastructure plan is approved, bootstrap the reviewed routes/metadata
   and deploy the backend. Verify public metadata and disabled-tool rejection. This
   allows ChatGPT to inspect the connection before an OAuth client exists.
4. Create the private connection entry in ChatGPT developer mode and copy the exact
   callback-ID-specific redirect URI shown there. Use `chat_mcp_url`. Supply that URI
   as `chatgpt_callback_urls` in local Terraform configuration; review the full plan
   again and apply the dedicated client configuration. Do not widen SPA allowlists.
   Configure the connection with `chat_mcp_client_id`, public OAuth authentication
   (no secret), and `myblog-chat/translate` scope.
5. The owner logs in and consents. In ordinary Chat invoke the private connection;
   test one requested track and one annotation. Verify displayed Korean, cache reuse,
   expiry/stale rejection, manual edit protection and refusal stopping. The metadata
   adapter/resource binding must be proven by real linking; local tests alone do not
   establish interoperability or translation quality.

The browser denied access to the ChatGPT registration page because the administrator
policy could not be verified. Do not bypass this block; registration/login needs an
accessible, authorized ChatGPT browser session.

No successful migration claim until OAuth linking, real Chat translation and viewer
readback pass. Do not enable automatic translation while testing the connection.

Rollback: disable the dedicated client or clear its backend client setting. Keep
Claude jobs disabled, preserve completed translations and source/history tables.
No rollback migration is required.

References: [OpenAI authentication](https://developers.openai.com/plugins/build/auth),
[plugins in Chat](https://learn.chatgpt.com/docs/plugins),
[Cognito resource binding](https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-user-pools-define-resource-servers.html).
