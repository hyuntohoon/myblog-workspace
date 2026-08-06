#!/usr/bin/env bash
# PreToolUse (Bash) — consolidated guard: ONE python spawn per Bash call.
#
# Merges the five former single-purpose hooks (2026-07-03; measured overhead
# 184ms/call with 5 separate spawns → ~40ms with one):
#   1. secret-file args   (block-secret-files.sh)     — Hard Rule #2
#   2. skip-hooks flags   (block-skip-hooks-flag.sh)  — Hard Rule #8
#   3. terraform -target  (block-terraform-target.sh) — Hard Rule #6
#   4. commit on main     (block-main-commit.sh)      — Hard Rule #1
#   5. force-push guard   (guard-force-push.sh)       — Hard Rule #7
#
# Parsing strategy unchanged from the originals (hook red-team 2026-06-21):
# checks 1-3 use plain shlex.split (quoted prose is a single token → a secret
# name or flag inside a commit message is never matched); checks 4-5 use
# shlex(punctuation_chars=True) + a command-position state machine so shell
# separators, env-var prefixes (VAR=val git …), subshells and `git -C` can't
# smuggle a commit/push past the guard.
#
# File writes to secret paths are covered by guard-file-edits.sh. This hook
# covers the Bash path: a command that names a secret file as a bare argument
# (cat/grep/base64/curl-data exfil).
# First deny wins; the non-main force-push warning is emitted only when no
# check denies. All decisions exit 0 — malformed/unparseable input fails open.
set -euo pipefail

input=$(cat)

printf '%s' "$input" | python3 -c '
import sys, json, shlex, subprocess, re, os, fnmatch

try:
    data = json.load(sys.stdin)
except Exception:
    sys.exit(0)  # malformed stdin — fail open silently.

if data.get("tool_name", "") != "Bash":
    sys.exit(0)

cmd = data.get("tool_input", {}).get("command", "")
cwd = data.get("cwd", "")

def deny(reason):
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": reason}}))
    sys.exit(0)

# ---- tokenizations (each fails open independently, like the originals) ----
try:
    plain = shlex.split(cmd, posix=True)
except ValueError:
    plain = None

def tok_punct(c):
    lex = shlex.shlex(c, posix=True, punctuation_chars=True)
    lex.whitespace_split = True
    return list(lex)

try:
    punct = tok_punct(cmd)
except ValueError:
    punct = None

# =========================================================================
# Check 1 — secret file named as a bare argument (Hard Rule #2)
# =========================================================================
PATTERNS = [".env", ".env.*", "*.env", "secrets.yaml", "secrets.yml",
            "config.local.json", "*.pem", "*.key", "credentials",
            "credentials.json", ".credentials.json"]

def secret_base(name):
    return any(fnmatch.fnmatch(name, pat) for pat in PATTERNS)

def token_is_secret(t):
    # shlex tokens with internal whitespace come from a quoted string (prose,
    # commit message) — never a bare path argument, so skip them.
    if not t or any(c.isspace() for c in t):
        return False
    core = t
    if core[0] == "-" and "=" in core:      # --data=@./x/.env , --upload-file=…
        core = core.split("=", 1)[1]
    core = core.lstrip("@<>")               # curl -d @.env , redirections
    return secret_base(os.path.basename(core.rstrip("/")))

if plain is not None:
    for t in plain:
        if token_is_secret(t):
            deny("Hard rule: refusing a Bash command that names a secret file "
                 "(%s). Secret values must not be read/copied into the "
                 "transcript; use AWS SSM Parameter Store / GitHub Actions "
                 "Secrets." % os.path.basename(t.lstrip("@<>")))

# =========================================================================
# Check 2 — git hook-skipping flags / hooksPath bypass (Hard Rule #8)
# =========================================================================
if plain is not None and any(a == "git" or a.endswith("/git") for a in plain):
    if any(a in ("--no-verify", "--no-gpg-sign") for a in plain):
        deny("Hard rule #8: never skip git hooks (--no-verify, --no-gpg-sign). "
             "If a hook fails, investigate and fix it. "
             "If you truly need to bypass, ask the human first.")
    # `git -c core.hooksPath=…` disables hooks with no flag — same rule.
    c_vals, i = [], 0
    while i < len(plain):
        a = plain[i]
        if a == "-c" and i + 1 < len(plain):
            c_vals.append(plain[i + 1]); i += 2; continue
        if a.startswith("-c="):
            c_vals.append(a[3:])
        elif a.startswith("-c") and len(a) > 2:
            c_vals.append(a[2:])
        i += 1
    if any(v.startswith("core.hooksPath") for v in c_vals):
        deny("Hard rule #8: overriding core.hooksPath disables git hooks "
             "without a flag and is treated the same as --no-verify. "
             "If a hook fails, fix it. If you truly need to bypass, ask first.")

# =========================================================================
# Check 3 — terraform apply -target (Hard Rule #6)
# =========================================================================
if plain is not None:
    seen_tf = seen_apply = False
    for a in plain:
        if a == "terraform" or a.endswith("/terraform"):
            seen_tf, seen_apply = True, False
            continue
        if seen_tf and a == "apply":
            seen_apply = True
            continue
        if seen_apply and a.startswith("-target="):
            deny("Hard rule #6: never `terraform apply -target=...` without "
                 "explicit human go-ahead. Run a full `terraform plan` and "
                 "stop on unexpected drift.")

# =========================================================================
# Checks 4+5 — git invocation state machine (Hard Rules #1, #7)
# =========================================================================
SEP = re.compile(r"^[;&|()<>]+$")
ASSIGN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
VALUE_FLAGS = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--super-prefix"}

def is_git(t):
    return t == "git" or t.endswith("/git")

def git_invocations(toks):
    """Yield (subcmd, target_repo, args_after_subcmd) per git invocation."""
    out = []
    i, n, expect_cmd = 0, len(toks), True
    while i < n:
        t = toks[i]
        if SEP.match(t):
            expect_cmd = True; i += 1; continue
        if expect_cmd and ASSIGN.match(t):
            i += 1; continue                  # env-var prefix; still expecting cmd
        if expect_cmd and is_git(t):
            target, subcmd, rest, j = cwd, None, [], i + 1
            while j < n:
                tj = toks[j]
                if SEP.match(tj):
                    break
                if tj == "-C" and j + 1 < n:
                    target = toks[j + 1]; j += 2; continue
                if tj.startswith("-C") and len(tj) > 2:
                    target = tj[2:]; j += 1; continue
                if subcmd is None and tj in VALUE_FLAGS and j + 1 < n:
                    j += 2; continue
                if subcmd is None and tj.startswith("-"):
                    j += 1; continue
                if subcmd is None:
                    subcmd = tj; j += 1; continue
                rest.append(tj); j += 1
            out.append((subcmd, target, rest))
            i = j; expect_cmd = False; continue
        expect_cmd = False; i += 1
    return out

FORCE_EXACT = {"--force", "--force-with-lease", "-f"}

def is_force(t):
    if t in FORCE_EXACT:
        return True
    if t.startswith("--force-with-lease=") or t.startswith("--force="):
        return True
    # bundled short flags containing f: -fv, -vf, -fq, -ff …
    if len(t) >= 2 and t[0] == "-" and t[1] != "-" and "f" in t[1:]:
        return True
    return False

def is_force_refspec(t):
    # a leading-+ refspec force-updates the remote ref, no flag needed
    return len(t) >= 2 and t.startswith("+") and not t.startswith("++")

def current_branch(target):
    try:
        return subprocess.check_output(
            ["git", "-C", target, "rev-parse", "--abbrev-ref", "HEAD"],
            stderr=subprocess.DEVNULL, text=True).strip()
    except Exception:
        return ""

warn = None
if punct is not None:
    invocations = git_invocations(punct)

    # Check 4 — commit on main/master (Hard Rule #1)
    for subcmd, target, _rest in invocations:
        if subcmd == "commit" and current_branch(target) in ("main", "master"):
            deny("Hard rule #1: never commit on main. Create a branch first: "
                 "git checkout -b <type>/<plan-id>-<desc>")

    # Check 5 — force-push: deny on main/master, warn elsewhere (Hard Rule #7)
    forced_branches = [current_branch(target)
                       for subcmd, target, rest in invocations
                       if subcmd == "push"
                       and any(is_force(t) or is_force_refspec(t) for t in rest)]
    if any(b in ("main", "master") for b in forced_branches):
        deny("Refusing force-push to main/master.")
    if forced_branches:
        # user-visible warning via the documented systemMessage channel
        warn = ("WARN: force-push detected on branch %r. "
                "Confirm this is intended and approved." % (forced_branches[0] or "unknown"))

if warn:
    print(json.dumps({"systemMessage": warn}))
sys.exit(0)
'
