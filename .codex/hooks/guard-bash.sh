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
# `cd`/`pushd` (logical) and `-C` (physical), same-command `VAR=…` assignments,
# wrappers (env/command/time/sudo/timeout…, also by path: /usr/bin/env) and
# worktrees created earlier in the same command, through newlines, ( … ), { … } and if/while/until/for/select/case;
# here-document bodies are data and skipped. A pipeline stage, a list ended by
# `&` and a ( … ) run in a subshell: their cd and assignments do not move the
# shell. A cd or assignment that may not have run (after && / ||, in a block
# that may not run — if/loops/case, `a && { … }`, a function body — each nested
# block on its own) makes the location, or the variable (GIT_DIR included),
# unknown once its list or block ends. When the target repo of a commit or
# force-push cannot be named — or GIT_DIR/--git-dir, an unmodelled wrapper
# option or unmatched block syntax may redirect it — it denies (fail closed).
# Not covered: git inside `bash -c "…"`, eval, a here-string, a function call
# or alias, or a script file; a quoted `"}"`/`"fi"` read as the reserved word;
# `cd <existing dir> || git commit` (the commit runs only if that cd fails);
# a wrapper outside the modelled list (`caffeinate git`, `arch -arm64 git`,
# zsh `- git`); quoted operators (`echo ";"`); a loop body's second pass;
# zsh's two-argument `cd old new`; `${x:-)}` and `${ …; }`; a substitution
# in an unquoted here-document body (`<<EOF` … `$(git commit)`); a CDPATH the
# Bash tool shell sets without this hook seeing it in its own environment;
# zsh/bash autocd (`../repo` as a command — off in the Bash tool shell). A
# `case` inside a substitution of a git argument is not parsed and denies.
# A newline after `&&`, `||`, `|` or `|&` continues the list. An array
# `X=(…)`/`X+=(…)` and any name set by declare/typeset/local/readonly/read/
# unset/printf -v/mapfile/getopts/let/for/select is unknown, and a nameref
# (`declare -n`) makes every later target unknown. With CDPATH set (or unknown)
# a relative `cd x` that does not start with ./ or ../ is unknown: bash looks
# there first. A `$( … )` inside double quotes or a backtick substitution runs
# where the shell is, which is not tracked: each git in it targets an unknown
# repo (`echo "$(git commit)"` denies even off main). A redirection inside a git command
# (`git >/dev/null commit`, `git push 2>&1 -f`) is skipped with its file; the
# body of an unquoted `$( … )`, `<( … )` or `>( … )` argument is parsed as a
# command list of its own.
# A cd after a wrapper that starts a program (`env cd x`, `timeout 9 cd x`)
# does not move the shell, nor after a time that follows another wrapper
# (`time time cd x`: /usr/bin/time in both shells); after a bare builtin it
# does; after `command`, zsh noglob/nocorrect, a first time (the reserved word
# or /usr/bin/time depending on position, quoting and the shell: `if time cd
# x` is a program in bash 3.2) or a wrapper option the location is unknown.
# A git after xargs takes its subcommand and -C from stdin: unknown, denies.
# An assignment after any wrapper (`env D=x;`) makes the variable unknown;
# `D+=x` appends to D.
# Backstop: the main-protection ruleset rejects any push to main regardless.
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
OPERATOR = re.compile(r"\|\||&&|;;&|;;|;&|;|\|&|&>>|&>|>>|>&|>\||<<<|<<|<&|<>|>|<|\||&|\(|\)")

def tok_punct(c):
    lex = shlex.shlex(c, posix=True, punctuation_chars=True)
    lex.whitespace_split = True
    lex.commenters = ""                       # comments are removed by strip_heredocs
    # shlex glues adjacent punctuation (`);`, `((`, `;>`, `|>`): split it into
    # single operators so `$( … )` skipping, subshell tracking and redirections
    # never swallow a `;`, `|` or `&&`
    out = []
    for t in lex:
        if SEP.match(t) and len(t) > 1:
            out.extend(OPERATOR.findall(t))
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
                if m.group(2) in ("\"", SQ):
                    if c[k:k + 1] == m.group(2):
                        k += 1                # the closing quote of <<"EOF"
                elif m.group(2) not in ("", "\\"):
                    return c                  # <<$EOF, <<1EOF …: not an opener we model
                if k < n and c[k] not in " \t\n;&|<>()":
                    return c                  # <<EOF.x, <<EOF-1 …: not a word we model
                out.append(c[m.start():k]); continue
        out.append(ch); k += 1
    return "".join(out)

# A newline ends a command just like `;` (shlex treats it as whitespace, which
# hid every git call after the first line); a backslash-newline joins lines,
# and so do newlines (blank lines too) after && / || / | / |&: the list goes on
# (`false &&` then `cd x` on the next line is one list, not two commands).
# An odd run of backslashes escapes the operator (`\\|` is a word), an even one does not.
CONTINUED = re.compile(r"(?<!\\)((?:\\\\)*)(&&|\|\||\|&|\|)[ \t]*\n(?:[ \t]*\n)*")

def lines_as_commands(c):
    c = CONTINUED.sub(lambda m: m.group(1) + m.group(2) + " ", c.replace("\\\n", " "))
    return c.replace("\n", " ; ")

# A $\x27…\x27 string with an escaped quote in it (bash and zsh ANSI-C quoting)
ANSI_C_ESCAPED_QUOTE = re.compile(r"\$\x27(?:[^\x27\\]|\\[^\x27])*\\\x27")

def quoted_bodies(c, prose=None):
    """Bodies of each $( … ) inside double quotes and of each `…`, outside single
    quotes and here-document bodies. They run, but tok_punct keeps them inside one
    word (`echo "$(git commit)"`) or splits them into plain words (backticks)."""
    bodies, n = [], len(c)

    def backtick(k):                          # k: just past the opening backtick
        a = k
        while k < n and c[k] != "`":
            k += 2 if c[k] == "\\" else 1
        # inside backticks \` \$ \\ stand for the plain character: the body can hold
        # its own backticks and quoted substitutions, so it is scanned again
        body = re.sub(r"\\([\\`$])", r"\1", c[a:k])
        bodies.append(body)
        bodies.extend(quoted_bodies(body))
        return k + 1

    def dquote(k):                            # k: just past the opening quote
        while k < n and c[k] != "\"":
            if c[k] == "\\":
                k += 2
            elif c.startswith("$(", k) and not c.startswith("$((", k):
                a = k + 2
                k = paren(a)
                bodies.append(c[a:k - 1])
            elif c[k] == "`":
                k = backtick(k + 1)
            else:
                k += 1
        return k + 1

    def paren(k):                             # k: just past $( — index past its )
        depth, pending = 1, []
        while k < n:
            ch = c[k]
            if ch == "\\":
                k += 2; continue
            if ch == SQ:
                e = c.find(SQ, k + 1); k = n if e < 0 else e + 1; continue
            if ch == "\"":
                k = dquote(k + 1); continue
            if ch == "`":
                k = backtick(k + 1); continue
            if ch == "#" and c[k - 1] in " \t\n;&|()":
                nl = c.find("\n", k); k = n if nl < 0 else nl; continue
            if ch == "\n" and pending:        # here-document bodies: prose, not syntax
                k += 1
                while pending and k < n:
                    nl = c.find("\n", k)
                    line = c[k:] if nl < 0 else c[k:nl]
                    dash, word = pending[0]
                    if (line.lstrip("\t") if dash else line) == word:
                        pending.pop(0)
                    elif prose is not None:
                        prose.append((k, n if nl < 0 else nl + 1))
                    k = n if nl < 0 else nl + 1
                continue
            if c.startswith("<<", k) and not c.startswith("<<<", k):
                m = HEREDOC_OP.match(c, k)
                if m:
                    pending.append((m.group(1) == "-", m.group(3)))
                    k = m.end()
                    if m.group(2) in ("\"", SQ) and c[k:k + 1] == m.group(2):
                        k += 1
                    continue
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0:
                    return k + 1
            k += 1
        return n + 1

    k = 0
    while k < n:
        ch = c[k]
        if ch == "\\":
            k += 2
        elif ch == SQ:
            e = c.find(SQ, k + 1); k = n if e < 0 else e + 1
        elif ch == "\"":
            k = dquote(k + 1)
        elif ch == "`":
            k = backtick(k + 1)
        else:
            k += 1
    return bodies

def strip_prose(c):
    """Drop the here-document bodies inside a quoted $( … ) (`--body "$(cat <<EOF`):
    strip_heredocs keeps them, being inside quotes, and their quotes and
    apostrophes would end the string for shlex."""
    spans = []
    quoted_bodies(c, spans)
    for a, b in reversed(spans):
        c = c[:a] + c[b:]
    return c

stripped = strip_prose(strip_heredocs(cmd))
try:
    punct = tok_punct(lines_as_commands(stripped))
except ValueError:
    punct = None
# Names a `${D:=x}` / `${D=x}` / zsh `${D::=x}` expansion may set, anywhere in the
# command: unknown wherever they are used
EXPANDED = set(re.findall(r"\$\{([A-Za-z_][A-Za-z0-9_]*):{0,2}=", stripped))

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
ASSIGN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*\+?=")
VALUE_FLAGS = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--super-prefix"}

def is_git(t):
    return t == "git" or t.endswith("/git")

VAR_REF = re.compile(r"\$\{?([A-Za-z_][A-Za-z0-9_]*)\}?")
# Words that put the next word back in command position.
WRAPPERS = {"env", "command", "builtin", "exec", "time", "nice", "nohup", "sudo",
            "timeout", "gtimeout", "xargs", "stdbuf", "noglob", "nocorrect"}
# Wrappers whose first operand is not the command (timeout DURATION cmd …).
OPERANDS = {"timeout": 1, "gtimeout": 1}
# Wrappers that run a cd in the shell itself, in bash and zsh alike. After
# `command` it depends on the shell (zsh runs /usr/bin/cd), as after the zsh
# modifiers noglob/nocorrect (no such command in bash) and a first `time` (the
# reserved word only at some positions, and unquoted: bash 3.2 runs
# /usr/bin/time after if/while/!, `\time` is always the program); after another
# wrapper `time` is /usr/bin/time in both shells. The rest start a program, so
# a cd after them (`env cd x`, `timeout 9 cd x`) moves nothing.
IN_SHELL = {"builtin", "time"}
UNSURE = {"command", "noglob", "nocorrect", "time"}

def wrapper(t):
    """Wrapper name t runs as — /usr/bin/env is env — else None."""
    name = t.rsplit("/", 1)[-1]
    return name if name in WRAPPERS else None
KEYWORDS = {"if", "while", "until", "for", "select", "case", "!"}
OPEN_CTL = {"if", "while", "until", "for", "select", "case"}
CLOSERS = {"fi": {"if"}, "done": {"while", "until", "for", "select"}, "esac": {"case"}}
CLOSE_CTL = set(CLOSERS)
GIT_DIR_VARS = {"GIT_DIR", "GIT_WORK_TREE"}
# Builtins that set the variables they name (bash and zsh)
SETTERS = {"declare", "typeset", "local", "readonly", "read", "unset", "printf", "print",
           "mapfile", "readarray", "getopts", "let", "integer", "float", "vared",
           "foreach"}                         # zsh `foreach D (x y)`: its body is not tracked
NAME_WORD = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)(?:\+?=|$)")
created = {}                                  # dirs made by `git worktree add` in this command → branch

def expand_path(path, base, env, physical=False):
    """Absolute path a cd / -C argument names, or None when it cannot be known
    statically (unset variable, command substitution, ~user). `cd` is logical
    (bash default); `git -C` is physical — `-C link/..` is the parent of the link target."""
    if base is None:
        return None
    p = VAR_REF.sub(lambda m: m.group(0) if m.group(1) in EXPANDED
                    else env.get(m.group(1), m.group(0)), path)
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

def git_invocations(toks, start=False, env0=None, depth=0):
    """Yield (subcmd, target_repo, args_after_subcmd) per git invocation.
    target_repo is None when it cannot be resolved statically. start / env0:
    the directory and variables of the command a substitution body runs inside."""
    if depth > 16:
        return [("commit", None, [])]         # nesting this deep is not parsed: deny, never crash open
    out = []
    env = dict(env0) if env0 is not None else {"HOME": os.path.expanduser("~")}
    if env0 is None and os.environ.get("CDPATH"):
        env["CDPATH"] = os.environ["CDPATH"]  # best effort: the Bash tool shell may set its own
    here = (cwd or os.getcwd()) if start is False else start  # directory the next command runs in
    prefix = {}                               # VAR=… prefixes of the current simple command
    exporting = False
    opaque = False                            # wrapper options we do not model (nice -n 5, env -C …)
    external = False                          # the command runs as a program, not in this shell
    unsure = False                            # `command cd x`: moves the shell in bash, not in zsh
    wrapped = False                           # a wrapper came first: `env D=x` is no shell assignment
    piped_args = False                        # after xargs: git takes more arguments from stdin
    fd_word = False                           # a bare number was skipped as the fd of a redirection
    broken = False                            # unmatched or unmodelled block syntax: nothing after it is trusted
    # The and-or list / pipeline being parsed. A cd or assignment that may not
    # have run — after && / || — leaves the location unknown once the list ends:
    # `false && cd x; git commit` still commits where it started. A pipeline
    # stage, and a list ended by `&`, runs in a subshell: the shell goes back to
    # where that pipeline / list started (`cd x | cat`, `cd x && y &`).
    def fresh():
        return {"conditional": False, "has_or": False, "chain_cd": False,
                "chain_vars": set(), "piped": False, "list_start": here,
                "pipe_start": here, "list_vars": set(), "pipe_vars": set()}
    ctx = fresh()
    # Open ( … ), { … } and if/while/until/for/select/case, innermost last. Each
    # keeps the outer list state and its own cd / assignments: a block that may
    # not run (if/loops/case, `a && { … }`) forgets them when it closes, nested
    # or not; a ( … ) or a block that is a later pipeline stage runs in a subshell.
    stack = []

    def forget(cd_flag, names):
        nonlocal here
        if cd_flag:
            here = None
        for name in names:                    # unknown, not unset: GIT_DIR may still be set
            env[name] = "$" + name

    def end_list():
        nonlocal ctx
        forget(ctx["chain_cd"], ctx["chain_vars"])
        ctx = fresh()

    def open_block(kind, may_skip):
        nonlocal ctx
        stack.append({"kind": kind, "outer": ctx, "here": here, "may_skip": may_skip,
                      "sub": ctx["piped"], "cd": False, "vars": set()})
        ctx = fresh()

    def close_block(kinds):
        nonlocal ctx, here, broken
        if not stack or stack[-1]["kind"] not in kinds:
            broken = True
            return
        b = stack.pop()
        ctx = b["outer"]
        if b["kind"] == "(":
            here = b["here"]                  # ( … ) restores the outer directory
            forget(False, b["vars"])
        elif b["sub"]:
            forget(b["cd"], b["vars"])        # `x | { cd y; }`: a subshell in bash, not in zsh
        elif b["may_skip"]:
            forget(b["cd"], b["vars"])
        else:                                 # a plain { … } is part of the list around it
            touched(b["cd"], b["vars"])

    def touched(cd_flag, names):
        """Record a cd / assignment in every open scope that may undo it."""
        if stack:
            stack[-1]["cd"] |= cd_flag
            stack[-1]["vars"] |= names
        if ctx["conditional"]:
            ctx["chain_cd"] |= cd_flag
            ctx["chain_vars"] |= names
        ctx["list_vars"] |= names
        ctx["pipe_vars"] |= names

    def substitution_end(j):
        """Index past the balanced ( … ) at toks[j]."""
        paren = 0
        while j < n:
            if SEP.match(toks[j]):
                paren += toks[j].count("(") - toks[j].count(")")
            j += 1
            if paren <= 0:
                break
        return j

    def substitution(j):
        """Index past the balanced ( … ) at toks[j]. Its body is a command list of
        its own, run where the git command runs: `git status <(git commit -m x)`."""
        a, j = j, substitution_end(j)
        body = toks[a + 1:j - 1]
        if "case" in body:
            # a case pattern `a)` would end the count early: `<(case x in a) git commit;; esac)`
            out.append(("commit", None, []))
            return j
        inner = git_invocations(body, here, env, depth + 1)
        out.extend((s, None if broken or opaque else t, r) for s, t, r in inner)
        return j

    i, n, expect_cmd = 0, len(toks), True
    while i < n:
        t = toks[i]
        if SEP.match(t) and ("<" in t or ">" in t):
            # a redirection: its operand is a file, not a command
            if i + 1 < n and not SEP.match(toks[i + 1]):
                i += 1
            i += 1; continue
        if expect_cmd and re.fullmatch(r"[0-9]+", t) and i + 1 < n and re.match(r"^[<>]", toks[i + 1]):
            # `2>/dev/null git …`: the fd of a redirection. The tokens cannot tell
            # it from `2 >/dev/null cd x`, where 2 is the command and cd its argument
            fd_word = True; i += 1; continue
        if expect_cmd and t == "function":
            broken = True; i += 1; continue   # `function f …`: a body we do not model
        if SEP.match(t):
            for ch in re.findall(r"\|\||&&|;+&?|\|&?|&|\(|\)", t):
                if ch == "(":
                    open_block("(", False)
                elif ch == ")":
                    end_list()
                    if not (stack and stack[-1]["kind"] == "case"):
                        close_block({"("})    # else `case x in a) …`: a pattern, not a subshell
                elif ch in ("|", "|&"):
                    here = ctx["pipe_start"]  # the stage before ran in a subshell
                    forget(False, ctx["pipe_vars"])
                    ctx["pipe_vars"] = set()
                    ctx["piped"] = True
                elif ch == "&":
                    here = ctx["list_start"]  # the whole list ran in the background
                    forget(False, ctx["list_vars"])
                    end_list()
                elif ch in ("&&", "||"):
                    if ch == "||":            # `a && cd x || cmd`: cmd runs where the cd may not have
                        forget(ctx["chain_cd"], ctx["chain_vars"])
                        ctx["chain_cd"], ctx["chain_vars"] = False, set()
                        ctx["has_or"] = True
                    ctx["conditional"] = True
                    ctx["piped"], ctx["pipe_start"], ctx["pipe_vars"] = False, here, set()
                else:                         # ; ;; ;& ;;&
                    end_list()
            prefix, exporting, opaque, fd_word, external, wrapped = {}, False, False, False, False, False
            unsure = piped_args = False
            expect_cmd = True; i += 1; continue
        if expect_cmd and t == "export":
            exporting = True; i += 1; continue
        if expect_cmd and t in SETTERS:
            # `declare D=x`, `read D`, `printf -v D …` set variables this does not model:
            # every name among the words becomes unknown (GIT_DIR included). The words
            # themselves are parsed as usual, so `declare D=$(git commit)` is still judged
            k, names = i + 1, set()
            while k < n:
                m = NAME_WORD.match(toks[k])
                if m:
                    names.add(m.group(1))
                elif SEP.match(toks[k]) and ("<" in toks[k] or ">" in toks[k]):
                    k += 1                                # `read <f D`: the file is no name
                elif SEP.match(toks[k]):
                    break
                k += 1
            if t == "unset":
                names &= set(env)             # `unset GIT_DIR` when it was never set: no change
            if t in ("declare", "typeset", "local") and any(
                    w.startswith("-") and "n" in w for w in toks[i + 1:k]):
                broken = True                 # a nameref: a later `D=x` may set GIT_DIR
            forget(False, names)
            touched(False, names)
            expect_cmd = False; i += 1; continue
        if (expect_cmd or exporting) and ASSIGN.match(t):
            j = i
            assigns = {}
            appended = False
            while j < n and ASSIGN.match(toks[j]):
                name, _, value = toks[j].partition("=")
                if not value and j + 1 < n and toks[j + 1] == "(":
                    # `D=(x)`, `D+=(x)`: an array, $D is its first word. Unknown; the
                    # ( … ) that follows is parsed as a subshell, so a substitution in it is judged
                    assigns[name.rstrip("+")] = "$" + name.rstrip("+"); j += 1
                    break
                if name.endswith("+"):        # `D+=/sub` appends to D; unknown D stays unknown
                    name = name[:-1]
                    value = assigns.get(name, env.get(name, "$" + name)) + value
                    appended = True
                assigns[name] = value; j += 1
            if exporting or j >= n or SEP.match(toks[j]):
                if (ctx["conditional"] and ctx["has_or"]) or ctx["piped"] or fd_word or wrapped \
                        or (exporting and appended):  # `export D+=x`: an error in zsh
                    forget(False, assigns)    # `true || X=… && git -C "$X"`: may have been skipped;
                                              # `env X=…;`: a program named X=…, X stays as it was
                else:
                    env.update(assigns)       # standalone: lasts for the rest of the line
                touched(False, set(assigns))
            else:
                prefix.update(assigns)        # prefix: applies to its own command only
            i = j; continue
        if expect_cmd and t == "{":
            # `a && { …; }` may not run at all; nor does a function body `f() { … }`
            k = i - 1
            while k >= 0 and toks[k] == ";":   # newlines between `f()` and its body
                k -= 1
            fn = k >= 1 and toks[k - 1] == "(" and toks[k] == ")"
            open_block("{", ctx["conditional"] or fn)
            i += 1; continue
        if expect_cmd and t == "}":
            end_list()
            close_block({"{"})
            expect_cmd = False; i += 1; continue
        if expect_cmd and t in CLOSE_CTL:
            end_list()
            close_block(CLOSERS[t])
            expect_cmd = False; i += 1; continue
        if expect_cmd and t in ("then", "do", "else", "elif"):
            if t in ("else", "elif") and stack:
                b = stack[-1]                 # `if false; then cd x; else git …`: the then-branch did not run
                forget(b["cd"], b["vars"])
            i += 1; continue
        if expect_cmd and t == "!" and i and (ASSIGN.match(toks[i - 1]) or (
                i > 1 and not SEP.match(toks[i - 1]) and SEP.match(toks[i - 2])
                and ("<" in toks[i - 2] or ">" in toks[i - 2]))):
            # right after an assignment or a redirection (`D=1 ! cd x`, `>f ! cd x`): a
            # command named ! in bash, a parse error in zsh. After `>f {` it is the keyword
            expect_cmd = False; i += 1; continue
        if expect_cmd and (wrapper(t) or t in KEYWORDS):
            if t in ("for", "select"):
                # `for D in x; do …; done` sets D; zsh takes several names (`for a b in …`)
                k, names = i + 1, set()
                while k < n and toks[k] not in ("in", "do") and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", toks[k]):
                    names.add(toks[k]); k += 1
                forget(False, names)
                touched(False, names)
            if t in OPEN_CTL:
                open_block(t, True)
            w = wrapper(t)
            bare = "/" not in t
            i += 1
            if w == "time" and bare and wrapped:
                external = True
            elif bare and w in UNSURE:
                unsure = True
            elif w and (w not in IN_SHELL or not bare):
                external = True
            wrapped = wrapped or bool(w)
            piped_args = piped_args or w == "xargs"
            if w and i < n and toks[i].startswith("-"):
                # options may take arguments (nice -n 5, sudo -u x, env -C dir):
                # skip to the git word, if any, and treat its repo as unknown
                opaque = True
                while i < n and not SEP.match(toks[i]) and not is_git(toks[i]):
                    if not external and toks[i] in ("cd", "pushd", "popd"):
                        here = None           # `command -p cd x` moves in bash, `command -v cd x`
                        touched(True, set())  # and `time -- cd x` do not, nor anything in zsh
                    i += 1
            elif w in OPERANDS:
                k = 0
                while k < OPERANDS[w] and i < n and not is_git(toks[i]):
                    if re.fullmatch(r"[0-9]+", toks[i]) and i + 1 < n and re.match(r"^[<>]", toks[i + 1]):
                        # `timeout 2>f 60 git` or `timeout 2 >f git`: the tokens cannot tell an
                        # fd from a duration, but either way git runs here; the loop stops at git
                        i += 1; continue
                    if SEP.match(toks[i]) and ("<" in toks[i] or ">" in toks[i]):
                        i += 1                # `timeout >/dev/null 60 git`: a file, not the duration
                        if i < n and toks[i] == "(":
                            i = substitution(i)   # `2> >(cat)`
                        elif i < n and not SEP.match(toks[i]):
                            i += 1
                        continue
                    if SEP.match(toks[i]):
                        break
                    i += 1; k += 1            # `timeout 60 git …`: 60 is not the command
            continue
        if expect_cmd and t in ("cd", "pushd", "popd"):
            arg = toks[i + 1] if i + 1 < n and not SEP.match(toks[i + 1]) else None
            before = here
            if not external:
                touched(True, set())
            # zsh ties the cdpath array to CDPATH; `.` in it can come after another entry
            cdpath = prefix.get("CDPATH", env.get("CDPATH", "")) or prefix.get("cdpath", env.get("cdpath", "")) \
                or {"CDPATH", "cdpath"} & EXPANDED
            if t == "popd" or arg is None or arg.startswith("-"):
                here = None                   # cd -, bare cd, popd: not tracked
            elif cdpath and not (arg.startswith(("/", "~", "./", "../")) or arg in (".", "..")):
                here = None                   # bash looks in CDPATH first (zsh: the directory first)
            else:
                here = resolve_dir(arg, here, env)
            if external:
                here = before                 # `env cd x`: a program, the shell stays put
            elif unsure:
                here = None
            elif (ctx["conditional"] and ctx["has_or"]) or ctx["piped"] or fd_word:
                here = None                   # `true || cd x && git …`: the cd was skipped;
                                              # `true | cd x`: a subshell in bash, not in zsh;
                                              # `2 >f cd x`: maybe not a cd at all
            i += 2 if arg is not None else 1
            expect_cmd = False; continue
        if expect_cmd and is_git(t):
            target, subcmd, rest, j = here, None, [], i + 1
            unknown = False                   # `git -C <f x commit`: the value is past a redirection
            if opaque or broken or GIT_DIR_VARS & (set(prefix) | set(env) | EXPANDED):
                target = None                 # GIT_DIR / GIT_WORK_TREE redirect the repo
            while j < n:
                tj = toks[j]
                if tj.startswith("(") and toks[j - 1].endswith("$"):
                    j = substitution(j)       # $( … ) is one argument
                    continue
                if SEP.match(tj) and ("<" in tj or ">" in tj):
                    # `git >/dev/null commit`, `git push 2>&1 -f`: a redirection and its
                    # file, not the end of the command
                    j += 1
                    if j < n and toks[j] == "(":
                        j = substitution(j)   # `2> >(cat)`, `<(true)`
                    elif j < n and not SEP.match(toks[j]):
                        j += 1
                    continue
                if re.fullmatch(r"[0-9]+", tj) and j + 1 < n and re.match(r"^[<>]", toks[j + 1]):
                    j += 1; continue                  # the fd of the redirection that follows
                if SEP.match(tj):
                    break
                if subcmd is None and tj.split("=", 1)[0] in ("--git-dir", "--work-tree"):
                    target = None
                value = j + 1 < n and not SEP.match(toks[j + 1])   # `git -C; git commit`: no value
                if (tj == "-C" or (subcmd is None and tj in VALUE_FLAGS)) and j + 1 < n and (
                        (not value and ("<" in toks[j + 1] or ">" in toks[j + 1]))
                        or (re.fullmatch(r"[0-9]+", toks[j + 1]) and j + 2 < n
                            and re.match(r"^[<>]", toks[j + 2]))):   # `-C 2>/dev/null x`, or `-c 2 >f`
                    unknown = True
                if tj == "-C":
                    target = resolve_dir(toks[j + 1], target, env, True) if value else None
                    j += 2 if value else 1; continue
                if tj.startswith("-C") and len(tj) > 2:
                    target = resolve_dir(tj[2:], target, env, True); j += 1; continue
                if subcmd is None and tj in VALUE_FLAGS and value:
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
            if piped_args or unknown:
                subcmd, target = "commit", None   # `echo commit | xargs git`: unknown, deny
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
GIT_WRITE = re.search(r"\bgit\b", stripped) and re.search(r"\b(commit|push)\b", stripped)
if punct is None and GIT_WRITE:
    deny("Hard rule #1/#7: this command does not tokenize (unbalanced quotes to "
         "shlex), so a git commit/push in it cannot be judged. Run the git command "
         "in its own call.")
if ANSI_C_ESCAPED_QUOTE.search(stripped) and GIT_WRITE:
    # shlex ends a $-quoted string at its escaped quote, so every word after it is read
    # on the wrong side of a quote (or the command does not parse at all): deny
    deny("Hard rule #1/#7: a $-quoted string with an escaped quote hides which words are "
         "commands, so this git commit/push cannot be judged. Run the git command in its "
         "own call without that quoting.")
if punct is not None:
    invocations = git_invocations(punct)
    # A substitution inside double quotes or backticks runs too. Where it runs is
    # not tracked: each git in it is judged with an unknown repo
    for body in quoted_bodies(stripped):
        try:
            inner = git_invocations(tok_punct(lines_as_commands(strip_heredocs(body))), None)
        except ValueError:
            inner = [("commit", None, [])] if re.search(r"\bgit\b", body) and re.search(r"\b(commit|push)\b", body) else []
        invocations.extend((s, None, r) for s, _t, r in inner)

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
        branch = current_branch(target)
        if not branch:
            deny("Hard rule #1: " + UNRESOLVED % ("commit", "commit"))
        if branch in ("main", "master"):
            deny("Hard rule #1: never commit on main. Create a branch first: "
                 "git checkout -b <type>/<plan-id>-<desc>")

    # Check 5 — force-push: deny on main/master, warn elsewhere (Hard Rule #7)
    forced = [target for subcmd, target, rest in invocations
              if subcmd == "push"
              and any(is_force(t) or is_force_refspec(t) for t in rest)]
    if any(target is None for target in forced):
        deny("Hard rule #7: " + UNRESOLVED % ("push --force", "push"))
    forced_branches = [current_branch(target) for target in forced]
    if any(not b for b in forced_branches):
        deny("Hard rule #7: " + UNRESOLVED % ("push --force", "push"))
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
