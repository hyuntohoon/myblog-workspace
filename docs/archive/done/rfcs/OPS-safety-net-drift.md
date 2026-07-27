# OPS-safety-net-drift: controls that are documented as working but aren't

- **Status**: done (2026-07-28 — all four steps closed the same session they were promoted; Step 2 closed by amendment, see its section)
- **Owner**: owner
- **Created**: 2026-07-26
- **Plan row**: `plan.md` → OPS-safety-net-drift
- **Source**: `docs/reviews/AUDIT-2026-07-26-system-audit.md` §9.2 (OPS-1, SEC-1, SEC-2) + §8 (DEP-1)

---

## Goal

Four controls in this system are recorded somewhere as protecting us and do not. After this RFC, each is either **really working** or **honestly deleted from the docs** — and, more importantly, the *mechanism* that let a closed safety net go quietly false is removed, so the next control added doesn't repeat it.

## Why this is an RFC and not four plan rows

The four items are individually small. What makes them one piece of design work is that **`OPS-delivery-safety-gates` was closed as `done` on 2026-07-24, and one of its guarantees was already false by 2026-07-26** — with nothing anywhere able to notice.

That RFC's Step 4 extended `FailedInvocations` alarm coverage "from 2 rules to ALL worker crons", fixing audit item O-4 ("10 of ~12 rules were uncovered"). It did so via a **hand-maintained list**. Two days later a 13th worker cron shipped, the list wasn't touched, and coverage silently reverted to "12 of 13". Its `plan.md` row still advertises "알람 2→12" as an accomplishment; that sentence is now the bug report.

So the question this RFC exists to answer is not "how do we add four controls" — it is **"why did a control we closed as done become false, and what makes the next one durable?"** That is a design decision (derive-vs-declare), and it applies beyond these four instances.

Secondary reason: SEC-2 touches `app/core/auth.py`, which per `CLAUDE.md` is a recurring-bug class requiring a same-PR twin sweep across backend and music. That is not a drive-by row.

## Non-goals

- **Not** a general security review. The audit's own §9.4 lists the surfaces never examined (IAM scope, S3/CloudFront policies, CI workflow files, member-content escaping); this RFC does not open them.
- **Not** rate limiting or abuse protection as a feature. SEC-1 only asks whether the WAF should exist at all.
- **Not** dependency *upgrades*. DEP-1 is about getting told; deciding whether to take the Astro 5→7 jump stays a separate call (audit §7-b).
- **Not** a retro on `OPS-delivery-safety-gates`. Its five steps did ship and did work; only the durability of Step 4's mechanism is in scope.

## Current state

Every claim below was verified against live AWS or source on 2026-07-26; each line names its evidence.

**OPS-1 — alarm coverage regressed and cannot self-detect.**
`infra/monitoring.tf:106-120` declares `local.worker_cron_rules` as a hardcoded 12-entry map, consumed by `for_each` on `aws_cloudwatch_metric_alarm.cron_failed_invocations`. `worker-isrc-backfill` was added to `infra/eventbridge.tf:411` and never added to that map.
- Live: `aws events list-rules` → **15 rules** (13 worker crons + 2 warm-pings). `aws cloudwatch describe-alarms` → **12** `*-failed-invocations` alarms.
- `worker-isrc-backfill` is the only worker cron with no alarm. It runs `cron(0 21 ? * SUN *)` — weekly, i.e. the schedule least likely to be noticed by eye.
- The DLQ side is unaffected: `on_failure` is set on the Lambda's async invoke config, not per rule, so handler failures are still captured. **Only delivery failures are blind.**

**SEC-1 — the WAF is an empty shell that the docs treat as a control.**
`aws wafv2 get-web-acl --scope CLOUDFRONT` on the attached ACL `CreatedByCloudFront-72420c9a` returns `RuleCount: 0`, `Rules: []`, `DefaultAction: {Allow: {}}`.
`infra/README.md:52` describes it as a real thing ("**WAFv2 Web ACL** (CloudFront scope) — console-created; its rules are invisible to `plan`"). The note is accurate about *why* it can't be reviewed and silent about the fact that there is nothing to review. Because it is console-created, `terraform plan` will never surface this.

**SEC-2 — the one missing-config path that fails open.**
`ENV: str = "local"` is the default in **both** `myblog_backend/app/core/config.py:19` and `myblog_music/app/core/config.py:14`. `require_cognito_token` and `require_owner` both return early when `ENV in ("local", "dev")`.
- Missing `COGNITO_USER_POOL_ID` → **503** (fail closed, by design, `auth.py:152-165`).
- Missing **`ENV`** → **all auth disabled**, silently, on both services.
- Prod currently sets `ENV=prod` on both Lambdas (verified via `get-function-configuration`), so this is latent. But the entire fail-closed posture rests on one variable whose *absence* means "trust everyone" — the inverse of the project's own hardening rule.
- The audit's leg A had claimed "no path was found where missing config yields an allowed request". That claim is false, and this is the counterexample.

**DEP-1 — nothing would ever tell us a dependency is vulnerable.**
`gh api repos/hyuntohoon/<repo>/dependabot/alerts` returns `403 "Dependabot alerts are disabled for this repository"` for **all six** repos. No `pnpm audit` / `pip-audit` step exists in any CI workflow.
Consequence measured in audit §8: `astro@5.15.9` carries 9 advisories and is two majors behind; 3 direct runtime npm deps and 16 Python packages carry advisories. None of it had ever been reported.

**The shared shape.** OPS-1 and SEC-1 are both *absence* defects — the missing thing has no test that fails and no line of code to read. Grep-and-read auditing is structurally blind to them, which is why they survived a full audit pass and only surfaced when someone went looking at live AWS state.

## Target state

1. Alarm coverage for worker crons is **derived from the rule resources**, so adding a cron cannot silently skip its alarm. A new cron either gets an alarm or fails `plan`.
2. The CloudFront WAF either carries agreed managed rules, or is deleted and removed from `infra/README.md`. No third option where the doc claims a control that returns `RuleCount: 0`.
3. `ENV` cannot be absent-and-permissive: either the default flips to the safe value, or the local bypass moves to its own explicit flag that prod cannot inherit by omission.
4. A vulnerable dependency produces a notification without anyone running a script.
5. `OPS-delivery-safety-gates`' `plan.md` row no longer advertises a guarantee that regressed.

## Steps

Steps are **independent and individually mergeable**; they are ordered by ratio of harm-removed to risk-taken, not by dependency. Rule #4 applies — one step per session unless the owner says otherwise.

### Step 1 — derive the cron alarm map, and fix the stale row (P1, infra + docs)

**Built 2026-07-28.** Went one level deeper than the sentence below: the 13 worker-cron rule/target/permission trios were consolidated into a single `local.worker_crons` map (`infra/eventbridge.tf`) generating all three via `for_each`, and the alarm's `for_each` iterates `aws_cloudwatch_event_rule.worker_cron` — the resource map itself — so the hand-written alarm list no longer exists at all and a new cron gets its alarm by construction. 39 `moved` blocks keep state; **plan gate met exactly: `1 to add (cron_failed_invocations["isrc_backfill"]), 0 to change, 0 to destroy`.** Post-apply alarm-count check recorded in the PR.

Original spec: Replace `local.worker_cron_rules`' hand-written map with one derived from the `aws_cloudwatch_event_rule` resources that target the worker Lambda, so coverage tracks reality. Correct the `plan.md` OPS row's "알람 2→12" sentence to state current coverage.

```
# verify: terraform plan must show exactly the one missing alarm being added
#   (worker-isrc-backfill-failed-invocations), and 0 changed / 0 destroyed.
# post-apply: aws cloudwatch describe-alarms | count *-failed-invocations == worker cron count
```

Deliberately fixes the mechanism, not just the instance — adding only the missing map entry would leave the 14th cron to repeat this.

### Step 2 — resolve the WAF honestly (P1, infra + docs)

**Closed by amendment 2026-07-28 (ws #727 + #728).** The owner chose delete (OQ2); AWS rejected it at apply: `InvalidArgument: Distributions with a pricing plan subscription must have a web ACL resource`. The distribution is on the CloudFront **Free flat-rate pricing plan**, which force-attaches an ACL — the `RuleCount: 0` shell is a **pricing-plan artifact auto-created at subscription, not a forgotten control**; both this RFC and the audit missed that premise. Neither of the two options offered below was actually available. Outcome: nothing changed in AWS (the update failed atomically, final `terraform plan` clean); `web_acl_id` stays in `cloudfront.tf` marked as a plan requirement; `infra/README.md` now says **"attached but NOT a control"** with the refusal error and a `get-web-acl` honesty check. The RFC's real target — no doc claiming a control that returns `RuleCount: 0` — is met by truthful documentation. Optional follow-up (not blocking): add real managed rules to the mandatory ACL.

Original spec: Owner picks: attach AWS managed rule groups, **or** delete the ACL and strike it from `infra/README.md:52`. Either is acceptable; the current state is not.

```
# verify (if kept):    aws wafv2 get-web-acl → RuleCount > 0, and a blocked request in sampled requests
# verify (if deleted): the ACL is gone AND infra/README.md no longer claims it
```

Note: the ACL is console-created and invisible to `plan`, so whichever way this goes, record in `infra/README.md` how to check it — that is the only durable part.

### Step 3 — close the `ENV` fail-open (P2, auth — Claude directly, no delegation)

**Done 2026-07-28 (backend #137 + music #61, paired twin PRs; OQ1 = option (a)).** `ENV` default flipped `"local"` → `"prod"` in both `config.py` twins; prod byte-identical (Terraform sets `ENV=prod`; prod smoke 19/0 after both deploys). New tests in both repos construct `Settings` the way an ENV-less runtime would (`delenv` + `_env_file=None`) and assert the guard raises — the pre-existing fail-closed tests all hand-wrote `ENV="prod"` and could not see this defect. Music's test suite had itself been inheriting the permissive default; its `conftest.py` now opts in to `ENV=local` explicitly (mirrors backend). Sweep note: `myblog_worker` declares `ENV` but nothing consumes it (grep-verified) — left unchanged.

Original spec: Make absence safe. Options in the Open questions below. Must land in **both** `myblog_backend` and `myblog_music` `app/core/auth.py` / `config.py` in the same PR (`CLAUDE.md` twin-sweep rule), with the sweep named in the PR body.

```
# verify: unit test asserting that with ENV unset, require_cognito_token rejects (not bypasses)
#         + the same test in both repos (this is a duplicated-code bug class)
# verify: prod smoke unchanged — ENV=prod behaviour must be byte-identical
```

### Step 4 — turn on dependency notification (P1, repo settings + optional CI)

**Done 2026-07-28 (OQ3 = alerts only).** Dependabot alerts enabled on all six repos via `gh api PUT /repos/hyuntohoon/<repo>/vulnerability-alerts`; verify gate met — the alerts API returns a list (not 403) on all six. Counts were 0 at enable time because GitHub's scan is asynchronous; the audit's measured advisories (§8) should surface as scans complete. Automatic PRs deliberately NOT enabled. The OSV scanner promotion to `tools/` was skipped — Dependabot alone satisfies "a vulnerable dependency produces a notification without anyone running a script".

Original spec: Enable Dependabot **alerts** on all six repos (a setting, not code). Decide separately whether to enable automatic PRs — with 5 repos and a manual contract-merge flow, auto-PR volume may cost more than it saves.

The audit left a working scanner at `docs/reviews/audit-2026-07-26-raw/osv_scan.py` (OSV.dev, no auth, handles both npm and PyPI). If a CI step is wanted instead of/alongside Dependabot, promote that script to `tools/` first — per audit §9 C-14 it does not belong in a dated audit directory.

```
# verify: gh api repos/hyuntohoon/<repo>/dependabot/alerts returns a list, not 403, for all six
```

## Open questions — all resolved 2026-07-28

- **OQ1 (Step 3)** — ~~how to make `ENV` safe~~ **owner chose (a)**: default flipped to `"prod"`; absence is restrictive.
- **OQ2 (Step 2)** — ~~does the owner want a WAF at all~~ **owner chose delete → AWS refused** (pricing plan mandates the ACL); resolved as "attached but documented as not-a-control". Optional later: managed rules on the mandatory ACL.
- **OQ3 (Step 4)** — **owner chose alerts only**; automatic PRs off.
- **OQ4 (scope)** — grep done before closing: the only other literal `for_each` maps in `infra/` are `local.lambda_functions` (a fixed 3-Lambda enum feeding log groups + error/throttle alarms — a closed set that changes with new *services*, not the OPS-1 shape of "a growing set with per-item coverage") and the same map's reuse sites. No second instance of the declare-vs-derive defect found; nothing further to convert.

## Decisions log

- 2026-07-28 — **RFC closed (done).** Steps 2·3·4 all executed the same day on explicit owner scope approval ("Step 2·3·4 전부") with OQ answers 1=(a), 2=delete, 3=alerts-only. Step 2's delete was refused by AWS (pricing-plan-mandated ACL) and closed by amendment as documented-not-a-control — recorded here because the audit's SEC-1 framing ("console-created, presumably forgotten") was wrong about *why* the empty ACL exists, and any future reader deciding to "clean it up" must know deletion is structurally impossible on this pricing plan.
- 2026-07-28 — Step 1's derive mechanism was validated in production the same day it shipped, by accident of parallel work: a concurrent session merged a 14th worker cron (`worker-genius-fetch`, ws #726) with no monitoring edit, and the alarm `worker-genius-fetch-failed-invocations` was created automatically by its apply. Under the pre-Step-1 structure this would have been the OPS-1 regression again (a 14th cron, hand-list untouched, 13-of-14 coverage); under the new structure the alarm existed before anyone thought about it.
- 2026-07-28 — Owner promoted draft → in-progress in session ("다음 rfc 찾아서 승격하고 작업 진행해보자") and Step 1 was built the same session. Design call: full `for_each` consolidation over the lighter "rebuild the map from resource references" reading — the lighter form still leaves a second hand-list to forget, which is the exact OPS-1 mechanism. `target_id`/`statement_id` are frozen per entry (both force replacement) so the consolidation is a pure state move.
- 2026-07-26 — Owner chose "1 RFC + a grouped `plan.md` section" for the 21 audit findings, rather than one RFC per cluster or rows only. This RFC is that one RFC; the other 17 findings are `plan.md` rows.
- 2026-07-26 — D-1 (nightly 403) deliberately **excluded** from this RFC. Its fix shape depends on an unmade owner decision between three auth approaches; if (b) service-identity or (c) relaxed draft gate is chosen, it becomes auth work and earns its own RFC. Tracked as a `plan.md` row with the options stated. See audit §7-1.
- 2026-07-26 — DEP-2 excluded: its applicability was overturned during re-review (audit §9 C-4), leaving version hygiene only.
