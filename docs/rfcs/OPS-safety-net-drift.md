# OPS-safety-net-drift: controls that are documented as working but aren't

- **Status**: draft
- **Owner**: TBD
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

Replace `local.worker_cron_rules`' hand-written map with one derived from the `aws_cloudwatch_event_rule` resources that target the worker Lambda, so coverage tracks reality. Correct the `plan.md` OPS row's "알람 2→12" sentence to state current coverage.

```
# verify: terraform plan must show exactly the one missing alarm being added
#   (worker-isrc-backfill-failed-invocations), and 0 changed / 0 destroyed.
# post-apply: aws cloudwatch describe-alarms | count *-failed-invocations == worker cron count
```

Deliberately fixes the mechanism, not just the instance — adding only the missing map entry would leave the 14th cron to repeat this.

### Step 2 — resolve the WAF honestly (P1, infra + docs)

Owner picks: attach AWS managed rule groups, **or** delete the ACL and strike it from `infra/README.md:52`. Either is acceptable; the current state is not.

```
# verify (if kept):    aws wafv2 get-web-acl → RuleCount > 0, and a blocked request in sampled requests
# verify (if deleted): the ACL is gone AND infra/README.md no longer claims it
```

Note: the ACL is console-created and invisible to `plan`, so whichever way this goes, record in `infra/README.md` how to check it — that is the only durable part.

### Step 3 — close the `ENV` fail-open (P2, auth — Claude directly, no delegation)

Make absence safe. Options in the Open questions below. Must land in **both** `myblog_backend` and `myblog_music` `app/core/auth.py` / `config.py` in the same PR (`CLAUDE.md` twin-sweep rule), with the sweep named in the PR body.

```
# verify: unit test asserting that with ENV unset, require_cognito_token rejects (not bypasses)
#         + the same test in both repos (this is a duplicated-code bug class)
# verify: prod smoke unchanged — ENV=prod behaviour must be byte-identical
```

### Step 4 — turn on dependency notification (P1, repo settings + optional CI)

Enable Dependabot **alerts** on all six repos (a setting, not code). Decide separately whether to enable automatic PRs — with 5 repos and a manual contract-merge flow, auto-PR volume may cost more than it saves.

The audit left a working scanner at `docs/reviews/audit-2026-07-26-raw/osv_scan.py` (OSV.dev, no auth, handles both npm and PyPI). If a CI step is wanted instead of/alongside Dependabot, promote that script to `tools/` first — per audit §9 C-14 it does not belong in a dated audit directory.

```
# verify: gh api repos/hyuntohoon/<repo>/dependabot/alerts returns a list, not 403, for all six
```

## Open questions

- **OQ1 (Step 3, needs an owner call)** — how to make `ENV` safe. (a) flip the default to `"prod"` so absence is restrictive; (b) keep the default but require an explicit `ALLOW_LOCAL_AUTH_BYPASS` flag for the bypass; (c) leave it and rely on Terraform always setting `ENV`. (a) is the smallest diff; (b) is the most honest about intent; (c) is the status quo and is what this finding argues against. **Recommendation: (a).**
- **OQ2 (Step 2)** — does the owner want a WAF at all? For a personal blog with no significant traffic, deleting it and documenting "no WAF, bounded by Lambda concurrency" may be more honest than a token managed rule set. This RFC has no opinion beyond "don't claim one that's empty".
- **OQ3 (Step 4)** — Dependabot alerts only, or alerts + automatic PRs?
- **OQ4 (scope)** — should the derive-not-declare principle from Step 1 be applied anywhere else it already applies? Candidates not investigated: any other hand-maintained list in `infra/` that is supposed to cover a set of resources. Worth one grep before closing this RFC.

## Decisions log

- 2026-07-26 — Owner chose "1 RFC + a grouped `plan.md` section" for the 21 audit findings, rather than one RFC per cluster or rows only. This RFC is that one RFC; the other 17 findings are `plan.md` rows.
- 2026-07-26 — D-1 (nightly 403) deliberately **excluded** from this RFC. Its fix shape depends on an unmade owner decision between three auth approaches; if (b) service-identity or (c) relaxed draft gate is chosen, it becomes auth work and earns its own RFC. Tracked as a `plan.md` row with the options stated. See audit §7-1.
- 2026-07-26 — DEP-2 excluded: its applicability was overturned during re-review (audit §9 C-4), leaving version hygiene only.
