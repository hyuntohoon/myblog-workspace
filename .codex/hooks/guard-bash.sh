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
# smuggle a commit/push past the guard. The state machine also follows
# `cd`/`pushd` (logical) and `-C` (physical), subshells, newlines, `&`/`|`
# (a cd there does not move the shell), same-command `VAR=…` assignments,
# wrappers (env/command/time/sudo…) and worktrees created earlier in the same
# command; here-document bodies are data and skipped. A cd or assignment that
# may not have run (after && / ||, inside if/while/for/case) makes the location
# unknown once its list or block ends. When the target repo of a commit or
# force-push cannot be named — or GIT_DIR/--git-dir or an unmodelled wrapper
# option may redirect it — it denies (fail closed). Not covered: git inside
# `bash -c "…"`, eval, a here-string, functions/aliases, or a script file.
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

SEP = re.compile(r"^[;&|()<>]+$")

def tok_punct(c):
    lex = shlex.shlex(c, posix=True, punctuation_chars=True)
    lex.whitespace_split = True
    lex.commenters = ""                       # comments are removed by strip_heredocs
    # shlex glues adjacent punctuation (`);`, `((`): give each paren its own token
    # so `$( … )` skipping and subshell tracking never swallow a `;` or `&&`
    out = []
    for t in lex:
        if SEP.match(t) and len(t) > 1 and ("(" in t or ")" in t):
            out.extend(re.findall(r"[()]|[^()]+", t))
        else:
            out.append(t)
    return out

# <<WORD, <<-WORD, <<"WORD", <<\WORD and the single-quoted form (any one
# non-word char before WORD, so this script needs no single quote); not <<<.
HEREDOC_OP = re.compile(r"<<(-?)\s*([^A-Za-z_\s]?)([A-Za-z_][A-Za-z0-9_]*)")
SQ = chr(39)

def strip_heredocs(c):
    """Drop here-document bodies: they are data (a commit message, a PR body),
    not commands, and may quote git commands checks 4+5 would otherwise judge.
    Only a << outside quotes, comments and arithmetic ($(( … )), (( … )),
    $[ … ]) opens one, and if any body has no
    terminator line the raw text is judged instead — a lookalike must not be
    able to hide the commands after it."""
    out, pending, k, n = [], [], 0, len(c)
    quote, arith, brack = None, 0, 0
    while k < n:
        ch = c[k]
        if quote:
            if ch == "\\" and quote == "\"":
                out.append(c[k:k + 2]); k += 2; continue
            if ch == quote:
                quote = None
            out.append(ch); k += 1; continue
        if ch == "\n" and pending:
            out.append(ch); k += 1
            while pending:                    # consume the bodies, in order
                if k >= n:
                    return c
                nl = c.find("\n", k)
                line = c[k:] if nl < 0 else c[k:nl]
                k = n if nl < 0 else nl + 1
                dash, word = pending[0]
                if (line.lstrip("\t") if dash else line) == word:
                    pending.pop(0)
            continue
        if ch == "\\":
            out.append(c[k:k + 2]); k += 2; continue
        word_start = k == 0 or c[k - 1] in " \t\n;&|()"
        if ch == "#" and word_start:          # comment: dropped up to end of line
            nl = c.find("\n", k)
            k = n if nl < 0 else nl; continue
        if ch in ("\"", SQ):
            quote = ch
        elif c.startswith("$((", k) or (word_start and c.startswith("((", k)):
            step = 3 if ch == "$" else 2
            arith += 1; out.append(c[k:k + step]); k += step; continue
        elif arith and c.startswith("))", k):
            arith -= 1; out.append("))"); k += 2; continue
        elif c.startswith("$[", k):
            brack += 1; out.append("$["); k += 2; continue
        elif brack and ch in "[]":
            brack += 1 if ch == "[" else -1
        elif not arith and not brack and c.startswith("<<", k) and not c.startswith("<<<", k) \
                and (k == 0 or c[k - 1] != "<"):
            m = HEREDOC_OP.match(c, k)
            if m:
                pending.append((m.group(1) == "-", m.group(3)))
                k = m.end()
                if m.group(2) in ("\"", SQ) and c[k:k + 1] == m.group(2):
                    k += 1                    # the closing quote of <<"EOF"
                if k < n and c[k] not in " \t\n;&|<>()":
                    return c                  # <<EOF.x, <<EOF-1 …: not a word we model
                out.append(c[m.start():k]); continue
        out.append(ch); k += 1
    return "".join(out)

# A newline ends a command just like `;` (shlex treats it as whitespace, which
# hid every git call after the first line); a backslash-newline joins lines.
def lines_as_commands(c):
    return c.replace("\\\n", " ").replace("\n", " ; ")

try:
    punct = tok_punct(lines_as_commands(strip_heredocs(cmd)))
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
ASSIGN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
VALUE_FLAGS = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--super-prefix"}

def is_git(t):
    return t == "git" or t.endswith("/git")

VAR_REF = re.compile(r"\$\{?([A-Za-z_][A-Za-z0-9_]*)\}?")
# Words that put the next word back in command position.
WRAPPERS = {"env", "command", "builtin", "exec", "time", "nice", "nohup", "sudo"}
KEYWORDS = {"if", "then", "elif", "else", "while", "until", "for", "case", "do", "{", "!"}
OPEN_CTL, CLOSE_CTL = {"if", "while", "until", "for", "case"}, {"fi", "done", "esac"}
GIT_DIR_VARS = {"GIT_DIR", "GIT_WORK_TREE"}
created = {}                                  # dirs made by `git worktree add` in this command → branch

def expand_path(path, base, env, physical=False):
    """Absolute path a cd / -C argument names, or None when it cannot be known
    statically (unset variable, command substitution, ~user). `cd` is logical
    (bash default); `git -C` is physical — `-C link/..` is the parent of the link target."""
    if base is None:
        return None
    p = VAR_REF.sub(lambda m: env.get(m.group(1), m.group(0)), path)
    if p == "~" or p.startswith("~/"):
        p = os.path.expanduser(p)
    if "$" in p or "`" in p or p.startswith("~"):
        return None
    p = os.path.join(base, p)
    return os.path.realpath(p) if physical else os.path.normpath(p)

def resolve_dir(path, base, env, physical=False):
    """Existing directory a cd / -C argument names, else None. None makes checks
    4+5 fail closed: a repo we cannot name is not a repo we have proven is off
    main (worktree audit 2026-10-17 — `cd <repo> && git commit` and
    `git -C "$WT" commit` both used to pass on main)."""
    p = expand_path(path, base, env, physical)
    if p is None:
        return None
    return p if os.path.isdir(p) or os.path.realpath(p) in created else None

def worktree_add_branch(rest):
    """(path, branch) a `git worktree add …` will create, from its arguments."""
    branch, positional, k = None, [], 1
    while k < len(rest):
        a = rest[k]
        if a in ("-b", "-B", "--orphan") and k + 1 < len(rest):
            branch = rest[k + 1]; k += 2; continue
        if a == "--reason":
            k += 2; continue
        if a == "--detach":
            branch = "HEAD"
        elif not a.startswith("-"):
            positional.append(a)
        k += 1
    if not positional:
        return None, None
    if branch is None:
        branch = positional[1] if len(positional) > 1 else os.path.basename(positional[0].rstrip("/"))
    return positional[0], branch

def git_invocations(toks):
    """Yield (subcmd, target_repo, args_after_subcmd) per git invocation.
    target_repo is None when it cannot be resolved statically."""
    out = []
    env = {"HOME": os.path.expanduser("~")}
    here = cwd or os.getcwd()                 # directory the next command runs in
    stack = []                                # saved `here` per open subshell
    undo = None                               # `here` before the last cd, until the list continues
    prefix = {}                               # VAR=… prefixes of the current simple command
    exporting = False
    opaque = False                            # wrapper options we do not model (nice -n 5, env -C …)
    # A cd or assignment that may not have run — after && / || or inside
    # if/while/for/case — leaves the location unknown once that list or block
    # ends: `false && cd x; git commit` still commits where it started.
    conditional, depth = False, 0
    chain_cd, chain_vars, block_cd, block_vars = False, set(), False, set()

    def forget(cd_flag, names):
        nonlocal here
        if cd_flag:
            here = None
        for name in names:
            env.pop(name, None)
    i, n, expect_cmd = 0, len(toks), True
    while i < n:
        t = toks[i]
        if SEP.match(t):
            # `cd x &` / `cd x | …` run the cd in a subshell: the shell stays put
            if undo is not None and (t == "&" or (t.startswith("|") and not t.startswith("||"))):
                here = undo[0]
            if t[0] not in "<>":
                undo = None
            if t in ("&&", "||"):
                if t == "||":                 # `a && cd x || cmd`: cmd runs where the cd may not have
                    forget(chain_cd, chain_vars)
                    chain_cd, chain_vars = False, set()
                conditional = True
            elif ";" in t or t == "&" or "(" in t or ")" in t:
                forget(chain_cd, chain_vars)  # end of an && / || list
                chain_cd, chain_vars, conditional = False, set(), False
            for ch in t:                      # ( … ) restores the outer directory
                if ch == "(":
                    stack.append(here)
                elif ch == ")" and stack:
                    here = stack.pop()
            prefix, exporting, opaque = {}, False, False
            expect_cmd = True; i += 1; continue
        if expect_cmd and t == "export":
            exporting = True; i += 1; continue
        if (expect_cmd or exporting) and ASSIGN.match(t):
            j = i
            assigns = {}
            while j < n and ASSIGN.match(toks[j]):
                name, _, value = toks[j].partition("=")
                assigns[name] = value; j += 1
            if exporting or j >= n or SEP.match(toks[j]):
                env.update(assigns)           # standalone: lasts for the rest of the line
                if depth:
                    block_vars |= set(assigns)
                elif conditional:
                    chain_vars |= set(assigns)
            else:
                prefix.update(assigns)        # prefix: applies to its own command only
            i = j; continue
        if expect_cmd and t in CLOSE_CTL:
            depth = max(depth - 1, 0)
            if depth == 0:
                forget(block_cd, block_vars)
                block_cd, block_vars = False, set()
            expect_cmd = False; i += 1; continue
        if expect_cmd and (t in WRAPPERS or t in KEYWORDS):
            if t in OPEN_CTL:
                depth += 1
            i += 1
            if t in WRAPPERS and i < n and toks[i].startswith("-"):
                # options may take arguments (nice -n 5, sudo -u x, env -C dir):
                # skip to the git word, if any, and treat its repo as unknown
                opaque = True
                while i < n and not SEP.match(toks[i]) and not is_git(toks[i]):
                    i += 1
            continue
        if expect_cmd and t in ("cd", "pushd", "popd"):
            arg = toks[i + 1] if i + 1 < n and not SEP.match(toks[i + 1]) else None
            undo = (here,)
            if depth:
                block_cd = True
            elif conditional:
                chain_cd = True
            if t == "popd" or arg is None or arg.startswith("-"):
                here = None                   # cd -, bare cd, popd: not tracked
            else:
                here = resolve_dir(arg, here, env)
            i += 2 if arg is not None else 1
            expect_cmd = False; continue
        if expect_cmd and is_git(t):
            target, subcmd, rest, j = here, None, [], i + 1
            if opaque or GIT_DIR_VARS & (set(prefix) | set(env)):
                target = None                 # GIT_DIR / GIT_WORK_TREE redirect the repo
            while j < n:
                tj = toks[j]
                if tj.startswith("(") and toks[j - 1].endswith("$"):
                    paren = 0                 # $( … ) is one opaque argument
                    while j < n:
                        if SEP.match(toks[j]):
                            paren += toks[j].count("(") - toks[j].count(")")
                        j += 1
                        if paren <= 0:
                            break
                    continue
                if SEP.match(tj):
                    break
                if subcmd is None and tj.split("=", 1)[0] in ("--git-dir", "--work-tree"):
                    target = None
                if tj == "-C" and j + 1 < n:
                    target = resolve_dir(toks[j + 1], target, env, True); j += 2; continue
                if tj.startswith("-C") and len(tj) > 2:
                    target = resolve_dir(tj[2:], target, env, True); j += 1; continue
                if subcmd is None and tj in VALUE_FLAGS and j + 1 < n:
                    j += 2; continue
                if subcmd is None and tj.startswith("-"):
                    j += 1; continue
                if subcmd is None:
                    subcmd = tj; j += 1; continue
                rest.append(tj); j += 1
            if subcmd == "worktree" and rest[:1] == ["add"]:
                path, branch = worktree_add_branch(rest)
                new_dir = expand_path(path, target, env, True) if path else None
                if new_dir is not None:
                    created[new_dir] = branch
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
    # the map only vouches for a dir that does not exist yet — never over a real repo
    if not os.path.isdir(target) and os.path.realpath(target) in created:
        return created[os.path.realpath(target)]
    try:
        return subprocess.check_output(
            ["git", "-C", target, "rev-parse", "--abbrev-ref", "HEAD"],
            stderr=subprocess.DEVNULL, text=True).strip()
    except Exception:
        return ""

warn = None
if punct is not None:
    invocations = git_invocations(punct)

    UNRESOLVED = ("cannot tell which repo this `git %s` targets (shell variable, "
                  "command substitution, `cd -`/`popd`, GIT_DIR/--git-dir, or a path "
                  "that does not exist yet — mkdir/clone in the same command). Use a "
                  "literal path in its own call: `git -C /absolute/path %s …`.")

    # Check 4 — commit on main/master (Hard Rule #1)
    for subcmd, target, _rest in invocations:
        if subcmd != "commit":
            continue
        if target is None:
            deny("Hard rule #1: " + UNRESOLVED % ("commit", "commit"))
        if current_branch(target) in ("main", "master"):
            deny("Hard rule #1: never commit on main. Create a branch first: "
                 "git checkout -b <type>/<plan-id>-<desc>")

    # Check 5 — force-push: deny on main/master, warn elsewhere (Hard Rule #7)
    forced = [target for subcmd, target, rest in invocations
              if subcmd == "push"
              and any(is_force(t) or is_force_refspec(t) for t in rest)]
    if any(target is None for target in forced):
        deny("Hard rule #7: " + UNRESOLVED % ("push --force", "push"))
    forced_branches = [current_branch(target) for target in forced]
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
