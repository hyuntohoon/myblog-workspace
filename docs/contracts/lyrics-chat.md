# Automatic GPT translations

The manual-only MCP proposal is superseded by the owner's 2026-10-05 correction.
Keep queue-triggered execution. See [design and rollout](../rfcs/FEAT-lyrics-chat.md).

Existing Claude translation jobs stay disabled. No new AWS OAuth client, MCP routes,
Terraform apply, or per-song manual Chat prompt is required for the selected local
executor. A dedicated ChatGPT plan login, model selection and queue-enable control
are required before automatic consumption. Never reuse Codex credentials or silently
switch to paid API keys.


## Local setup and cutover

Run `scripts/install_gpt_translation_worker.py` with the backend Python 3.12
interpreter and explicit backend/shared checkout paths. It freezes workspace,
backend and shared revisions, installs a private runtime at
`~/.local/share/myblog-gpt/runtime`, and installs
`com.myblog.gpt-translate-poller` disabled. Existing Claude translation labels
remain disabled; unrelated research jobs are outside this cutover.

Start the installed runtime's `scripts/gpt_worker_setup.py` with its `.venv`
Python. Open its printed `http://127.0.0.1:<port>` URL manually, choose **Continue
with ChatGPT**, approve plan-use permission, fetch eligible models and save one
with the daily admission budget. Default budget is 10 conservative admissions
per UTC day; settings remain disabled. The setup page's Stop button disables
consumption; an already active foreground call may finish.

After owner sign-in, first run the installed `scripts/gpt_queue_worker.py
--smoke` once while launchd stays disabled. This consumes at most one eligible
queued source and therefore uses the owner's plan allowance. Verify actual
source-aligned result/model in the DB and the existing authenticated viewer,
then run another tick with no eligible source to confirm no inference. The
owner-authorized agent can set the private settings' `enabled` flag only after
these gates and enable/bootstrap `gui/<uid>/com.myblog.gpt-translate-poller`.
Do not repeat a failed smoke blindly; review the persisted stop reason.

Never change `model`, `active`, token files or budget while the worker holds
`worker.lock`; use setup controls. Credentials/host ID/settings are private
0600 files in a 0700 application directory and are never committed. Refusal
stops the source/version; temporary failure waits ten minutes with a total
two-attempt ceiling. An exhausted admission budget preserves the queue and
continues on the next UTC day. Plan/auth/usage rejection persists a global pause
even if DB cleanup fails. A new login and explicit settings save can clear the
pause, but do not reset a source's exhausted attempts.

No DB transaction spans a model call. Failed/incomplete/partial responses never
publish, and expired/replaced claims, changed sources, withdrawn album demands,
newer requests and manual edits reject publication. Saved work retains actual
model provenance in a reserved first-segment metadata field that is stripped
before viewer publication; older cache rows lacking it are explicitly labeled
`chatgpt/cache-model-unavailable` rather than inventing a model.

Stream deadline is 300 seconds plus at most one 30-second stalled read, source
limit is 16,000 characters/300 segments, and output is bounded to 262,144 bytes.
Oversized sources stay queued for a later explicit workflow; they are never
truncated. These bounds are local operational controls, not exact token billing
limits or member-catalog truncation. Plan eligibility is account-dependent;
there is no API-key billing fallback. Manage per-app plan permission and limits
in [ChatGPT usage settings](https://chatgpt.com/settings/usage).
