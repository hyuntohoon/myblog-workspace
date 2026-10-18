"""Hard rules #1 / #7 in the Bash guard hook: commit and force-push target resolution.

Feeds synthetic PreToolUse JSON to `.codex/hooks/guard-bash.sh` (override with
GUARD_BASH_HOOK to test the local `.claude/hooks/` twin). Nothing is committed: the
hook only prints a decision. Regression for the 2026-10-17 worktree audit, where
`cd <repo> && git commit` and `git -C "$WT" commit` passed on main.
"""

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

HOOK = Path(os.environ.get(
    "GUARD_BASH_HOOK",
    Path(__file__).resolve().parents[2] / ".codex" / "hooks" / "guard-bash.sh",
))


def _git(*args, cwd):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


def _repo(path, branch):
    path.mkdir()
    _git("init", "-q", "-b", branch, cwd=path)
    # an unborn branch makes `rev-parse --abbrev-ref HEAD` fail → reads as "not main"
    _git("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q",
         "--allow-empty", "-m", "init", cwd=path)


class GuardBashTargetTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls.root = Path(cls._tmp.name).resolve()
        _repo(cls.root / "onmain", "main")
        _repo(cls.root / "feature", "feat/x")
        # feature/lnk -> onmain/sub: `-C feature/lnk/..` is onmain to git (physical path)
        (cls.root / "onmain" / "sub").mkdir()
        os.symlink(cls.root / "onmain" / "sub", cls.root / "feature" / "lnk")

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def decide(self, command, cwd=None):
        payload = {"tool_name": "Bash", "cwd": str(cwd or self.root),
                   "tool_input": {"command": command}}
        out = subprocess.run(["bash", str(HOOK)], input=json.dumps(payload),
                             capture_output=True, text=True, check=True).stdout
        return "deny" if '"permissionDecision": "deny"' in out else "allow"

    def assertDecision(self, expected, command, cwd=None):
        self.assertEqual(expected, self.decide(command, cwd), command)

    def test_commit_on_main_is_denied_in_every_spelling(self):
        main, feat = self.root / "onmain", self.root / "feature"
        for cmd in [
            "git commit -m x",                                   # cwd = main repo
            "git -C onmain commit -m x",                         # relative -C joins hook cwd
            f"git -C {main} commit -m x",
            "cd onmain && git commit -m x",                      # was allowed before 10-17
            "(cd onmain; git commit -m x)",
            f"WT={main}; git -C \"$WT\" commit -m x",            # recipe form, was allowed
            f"export WT={main} && git -C $WT commit -m x",
            f"pushd {main} && git commit -m x",
            f"(cd {feat}; git status); git -C onmain commit -m x",
        ]:
            cwd = main if cmd == "git commit -m x" else None
            self.assertDecision("deny", cmd, cwd)

    def test_unresolvable_target_fails_closed(self):
        for cmd in [
            "git -C \"$UNSET_WT\" commit -m x",
            "git -C does-not-exist commit -m x",
            "cd - && git commit -m x",
            "cd onmain && popd && git commit -m x",
            "git -C $(pwd) commit -m x",
            "git -C \"$UNSET_WT\" push --force origin x",
        ]:
            self.assertDecision("deny", cmd)

    def test_commit_off_main_is_allowed(self):
        feat = self.root / "feature"
        for cmd in [
            "git -C feature commit -m x",
            "cd feature && git commit -m x",
            f"WT={feat}; git -C \"$WT\" commit -m x",
            f"export WT={feat} && git -C $WT commit -m x",
            "(cd onmain; git status); git -C feature commit -m x",
            "git -C ~/does-not-matter status",                   # not a commit
            "cd onmain && git status",
        ]:
            self.assertDecision("allow", cmd)
        self.assertDecision("allow", 'git commit -m "cd onmain"', cwd=feat)

    def test_subshell_restores_outer_directory(self):
        self.assertDecision("allow", "(cd ../feature; git commit -m x)",
                            cwd=self.root / "onmain")
        self.assertDecision("deny", "(cd ../feature; true); git commit -m x",
                            cwd=self.root / "onmain")

    def test_background_or_pipeline_cd_does_not_move_the_shell(self):
        main = self.root / "onmain"
        self.assertDecision("deny", "cd ../feature & git commit -m x", cwd=main)
        self.assertDecision("deny", "cd ../feature | true; git commit -m x", cwd=main)
        self.assertDecision("allow", "cd ../feature || exit 1; git commit -m x", cwd=main)

    def test_wrappers_and_git_dir_overrides(self):
        main = self.root / "onmain"
        for cmd in ["env git commit -m x", "command git commit -m x",
                    "time git commit -m x", "if true; then git commit -m x; fi",
                    "{ git commit -m x; }"]:
            self.assertDecision("deny", cmd, cwd=main)
        # from a feature repo, GIT_DIR / --git-dir can point the commit at main
        for cmd in ["git --git-dir=../onmain/.git commit -m x",
                    "git --git-dir ../onmain/.git commit -m x",
                    "GIT_DIR=../onmain/.git git commit -m x",
                    "export GIT_DIR=../onmain/.git; git commit -m x"]:
            self.assertDecision("deny", cmd, cwd=self.root / "feature")
        # a prefix assignment applies to its own command only
        self.assertDecision("deny", f"WT={self.root / 'feature'} git status; "
                                    "git -C \"$WT\" commit -m x")

    def test_worktree_created_in_the_same_command(self):
        self.assertDecision("allow", "git -C onmain worktree add -b feat/new ../wt-new "
                                     "&& cd wt-new && git commit -m x")
        self.assertDecision("deny", "git -C onmain worktree add -b main2 ../wt-x "
                                    "&& git -C wt-y commit -m x")   # not the created path
        self.assertDecision("deny", "mkdir n && cd n && git init && git commit -m x")

    def test_missing_cwd_falls_back_to_process_cwd(self):
        payload = {"tool_name": "Bash", "tool_input": {"command": "git commit -m x"}}
        for repo, expected in (("onmain", "deny"), ("feature", "allow")):
            out = subprocess.run(["bash", str(HOOK)], input=json.dumps(payload),
                                 cwd=self.root / repo, capture_output=True,
                                 text=True, check=True).stdout
            got = "deny" if '"permissionDecision": "deny"' in out else "allow"
            self.assertEqual(expected, got, repo)

    def test_heredoc_body_is_data_not_commands(self):
        feat, main = self.root / "feature", self.root / "onmain"
        body = 'cd onmain && git commit -m x\ngit -C "$WT" commit -m x\n'
        self.assertDecision("allow", f"gh pr create --body-file - <<'EOF'\n{body}EOF", cwd=feat)
        self.assertDecision("allow", f"git commit -F - <<-EOF\n{body}\tEOF", cwd=feat)
        self.assertDecision("allow", f'cat <<"EOF" > f\n{body}EOF', cwd=feat)
        self.assertDecision("allow", f"cat <<\\EOF\n{body}EOF", cwd=feat)
        self.assertDecision("allow", f"x=a#b; cat <<EOF\n{body}EOF", cwd=feat)   # # inside a word
        # the command after the terminator is still checked
        self.assertDecision("deny", f"cat <<EOF\n{body}EOF\ngit commit -m x", cwd=main)
        self.assertDecision("deny", "cat <<< 'x'; git commit -m x", cwd=main)

    def test_heredoc_lookalikes_do_not_hide_commands(self):
        main = self.root / "onmain"
        for cmd in ['echo "<<EOF"; git commit -m x',                  # no terminator line
                    'echo "<<EOF"\ngit commit -m x\nEOF',             # << inside quotes
                    'echo "x <<EOF y"\ngit commit -m x\nEOF',
                    "echo '<<EOF'\ngit commit -m x\nEOF",
                    "echo $((1<<X))\ngit commit -m x\nX",             # arithmetic shift
                    "((y = 1<<X))\ngit commit -m x\nX",
                    "echo $[1<<X]\ngit commit -m x\nX",
                    "true # <<EOF\ngit commit -m x\nEOF",               # comment
                    "cat <<EOF\nno terminator\ngit commit -m x"]:
            self.assertDecision("deny", cmd, cwd=main)

    def test_worktree_add_onto_an_existing_dir_does_not_vouch_for_it(self):
        self.assertDecision("deny", "git -C feature worktree add -b feat/zz ../onmain "
                                    "&& git -C onmain commit -m x")

    def test_newline_separates_commands(self):
        main = self.root / "onmain"
        self.assertDecision("deny", "echo hi\ngit commit -m x", cwd=main)
        self.assertDecision("deny", "echo hi # a note\ngit commit -m x", cwd=main)
        self.assertDecision("deny", "echo a#b; git commit -m x", cwd=main)  # not a comment
        self.assertDecision("deny", "git \\\n  commit -m x", cwd=main)
        self.assertDecision("allow", "cd ../feature \\\n  && git commit -m x", cwd=main)
        self.assertDecision("allow", 'git commit -m "line one\nline two"', cwd=self.root / "feature")

    def test_conditional_cd_and_assignment_make_the_location_unknown(self):
        main = self.root / "onmain"
        for cmd in ["false && cd ../feature; git commit -m x",
                    "true || cd ../feature; git commit -m x",
                    "if false; then cd ../feature; fi; git commit -m x",
                    "while false; do cd ../feature; done; git commit -m x",
                    f"true || WT={self.root / 'feature'}; git -C \"$WT\" commit -m x"]:
            self.assertDecision("deny", cmd, cwd=main)
        for cmd in ["cd ../feature && git commit -m x",            # same chain: runs only after cd
                    "cd ../feature || exit 1; git commit -m x",
                    "if true; then cd ../feature; git commit -m x; fi"]:
            self.assertDecision("allow", cmd, cwd=main)

    def test_conditional_cd_review_followup(self):
        main = self.root / "onmain"
        for cmd in ["false && cd ../feature || git commit -m x",          # cd skipped, || runs
                    "if false; then git log $(date); cd ../feature; fi; git commit -m x",
                    "if false; then cd ../feature; git log $(date); fi; git commit -m x"]:
            self.assertDecision("deny", cmd, cwd=main)

    def test_review_round3(self):
        main = self.root / "onmain"
        for cmd in ["true || cd ../feature && git commit -m x",       # cd skipped, && runs
                    # bash ends these bodies before the line we would wait for
                    "cat <<$EOF\nx\n$EOF\ngit commit -m x\nEOF",
                    'cat <<"EOF  x"\nEOF  x\ngit commit -m x\nEOF',
                    "git -C /tmp commit -m x",                           # not a repo: branch unknown
                    "git -C /tmp push --force origin x"]:
            self.assertDecision("deny", cmd, cwd=main)
        self.assertDecision("allow", "cd ../feature || exit 1; git commit -m x", cwd=main)

    def test_review_round4(self):
        main, feat = self.root / "onmain", self.root / "feature"
        for cmd in [
            # a { … } group after && / || may not run at all: its cd / assignment
            # (after an inner `;`, which ends the inner list) must not outlive it
            "false && { true; cd ../feature; }; git commit -m x",
            "true || { true; cd ../feature; }; git commit -m x",
            f"false && {{ true; WT={feat}; }}; git -C \"$WT\" commit -m x",
            "false && { if true; then true; fi; cd ../feature; }; git commit -m x",
            # an assignment after || in the same list may have been skipped
            f"true || WT={feat} && git -C \"$WT\" commit -m x",
            f"WT={main}; true || WT={feat} && git -C \"$WT\" commit -m x",
        ]:
            self.assertDecision("deny", cmd, cwd=main)
        for cmd in ["{ cd ../feature; }; git commit -m x",             # unconditional group
                    "true && { cd ../feature; git commit -m x; }",     # commit inside the group
                    "false || { cd ../feature && git commit -m x; }",  # the group's list is its own
                    f"{{ WT={feat}; }}; git -C \"$WT\" commit -m x",
                    f"WT={feat} && git -C \"$WT\" commit -m x"]:
            self.assertDecision("allow", cmd, cwd=main)

    def test_review_round4_nested_blocks_and_forgotten_git_dir(self):
        main, feat = self.root / "onmain", self.root / "feature"
        for cmd in [
            # an inner block forgets its cd even while an outer one is open
            "if true; then if false; then cd ../feature; fi; git commit -m x; fi",
            "if true; then false && { cd ../feature; }; git commit -m x; fi",
            "true && { false && { cd ../feature; }; git commit -m x; }",
            # a chain inside a block still ends at its `;`
            "if true; then false && cd ../feature; git commit -m x; fi",
            "true && { false && cd ../feature; git commit -m x; }",
            f"if true; then false && WT={feat}; git -C \"$WT\" commit -m x; fi",
            "if true; then true || { cd ../feature; } && git commit -m x; fi",
            "if false; then { cd ../feature; }; fi; git commit -m x",
            # a group or a stage after | runs in a subshell
            "{ cd ../feature; } | cat; git commit -m x",
            "{ cd ../feature; } & wait; git commit -m x",
            f"{{ WT={feat}; }} | cat; git -C \"$WT\" commit -m x",
            "true | cd ../feature; git commit -m x",
            f"true | WT={feat}; git -C \"$WT\" commit -m x",
        ]:
            self.assertDecision("deny", cmd, cwd=main)
        # a GIT_DIR that may have been exported is unknown, not unset
        for cmd in ["false || export GIT_DIR=../onmain/.git && git commit -m x",
                    "true && export GIT_DIR=../onmain/.git; git commit -m x",
                    "if true; then export GIT_DIR=../onmain/.git; fi; git commit -m x"]:
            self.assertDecision("deny", cmd, cwd=feat)
        for cmd in ["if true; then cd ../feature; if true; then true; fi; git commit -m x; fi",
                    "true && { cd ../feature; if true; then true; fi; git commit -m x; }"]:
            self.assertDecision("allow", cmd, cwd=main)

    def test_review_round4_subshell_lists_and_block_syntax(self):
        main, feat = self.root / "onmain", self.root / "feature"
        for cmd in [
            # a list ended by & runs in the background, whole
            "cd ../feature && true & git commit -m x",
            "cd ../feature && (true) & wait; git commit -m x",
            # redirections do not hide the | after a group
            "{ cd ../feature; } >/dev/null 2>&1 | cat; git commit -m x",
            # a group / block that is a later pipeline stage
            "true | { cd ../feature; }; git commit -m x",
            "true | while read l; do cd ../feature; done; git commit -m x",
            # unmodelled or unmatched block syntax fails closed
            "if false; then select x in a; do true; done; cd ../feature; fi; git commit -m x",
            "if true; then cd ../feature; done; git commit -m x",
            "function f { cd ../feature; }; git commit -m x",
            # a function body does not run where it is defined
            "f() { cd ../feature; }; git commit -m x",
            # an assignment inside ( … ) does not leave it
            f"(WT={feat}); git -C \"$WT\" commit -m x",
            # nor one in a list sent to the background
            f"WT={feat} && true & git -C \"$WT\" commit -m x",
            # the else branch runs only when the then branch did not
            "if false; then cd ../feature; else git commit -m x; fi",
            # glued operators and fd numbers do not hide the next command
            "true;>/dev/null git commit -m x",
            "true|>/dev/null git commit -m x",
            "true; 2>/dev/null git commit -m x",
            # `2 >f cd x`: 2 is the command and cd its argument — same tokens as `2>f cd x`
            "2 >/dev/null cd ../feature; git commit -m x",
            f"2 >/dev/null WT={feat}; git -C \"$WT\" commit -m x",
            # a function body on the next line, or after `function`
            "f()\n{ cd ../feature; }\ngit commit -m x",
            "function f\n{ cd ../feature; }\ngit commit -m x",
        ]:
            self.assertDecision("deny", cmd, cwd=main)
        for cmd in ["2>/dev/null true; cd ../feature; git commit -m x", # the fd doubt ends with its command
                    "cd ../feature && git status & wait",               # no commit at all
                    "(cd ../feature) && cd ../feature && git commit -m x",
                    "cd ../feature; git log | head -1 > /dev/null; git commit -m x",
                    "cd ../feature && git log | head -1 && git commit -m x",
                    ">/dev/null cd ../feature; git commit -m x",        # redirection before the command
                    "select x in a; do true; done; cd ../feature; git commit -m x"]:
            self.assertDecision("allow", cmd, cwd=main)
        # a case pattern's `)` is not the end of a subshell
        self.assertDecision("allow", "case a in a) true;; b) true;; esac; git commit -m x", cwd=feat)

    def test_heredoc_delimiter_must_be_a_plain_word(self):
        main = self.root / "onmain"
        for cmd in ["cat <<EOF.x\ngit commit -m x\nEOF\nEOF.x",          # real delimiter is EOF.x
                    "cat <<EOF-1\ngit commit -m x\nEOF\nEOF-1",
                    "echo $[a[1] <<X ]\ngit commit -m x\nX"]:
            self.assertDecision("deny", cmd, cwd=main)

    def test_wrapper_options_fail_closed(self):
        for cmd in ["nice -n 5 git commit -m x", "env -C ../onmain git commit -m x",
                    "sudo -u me git commit -m x", "time -p git commit -m x"]:
            self.assertDecision("deny", cmd, cwd=self.root / "feature")
        self.assertDecision("allow", "env git commit -m x", cwd=self.root / "feature")

    def test_wrapper_by_path_or_with_a_positional_argument(self):
        main, feat = self.root / "onmain", self.root / "feature"
        for cmd in ["/usr/bin/env git commit -m x",            # used to read `/usr/bin/env` as the command
                    "/usr/bin/time git commit -m x",
                    "/usr/bin/env GIT_DIR=x git status; git commit -m x",
                    "timeout 60 git commit -m x",               # `60` used to end command position
                    "gtimeout 5m git push --force origin main",
                    "timeout 60 env git commit -m x",
                    "/usr/bin/timeout 60 git commit -m x",
                    "timeout -s KILL 60 git commit -m x"]:
            self.assertDecision("deny", cmd, cwd=main)
        for cmd in ["/usr/bin/env git commit -m x",
                    "timeout 60 git commit -m x",
                    "/usr/bin/env GIT_DIR=x true; git commit -m x"]:  # a prefix stays on its command
            self.assertDecision("allow", cmd, cwd=feat)
        for cmd in ["/usr/bin/env GIT_DIR=../onmain/.git git commit -m x",
                    "timeout 60 /usr/bin/env -C ../onmain git commit -m x",
                    "timeout -s KILL 60 git commit -m x"]:      # options: repo unknown, as for nice -n
            self.assertDecision("deny", cmd, cwd=feat)

    def test_cd_after_a_program_wrapper_does_not_move_the_shell(self):
        main, feat = self.root / "onmain", self.root / "feature"
        for cmd in ["env cd ../feature && git commit -m x",   # used to follow the cd and allow
                    "nohup cd ../feature; git commit -m x",
                    "timeout 60 cd ../feature && git commit -m x",
                    "/usr/bin/time cd ../feature && git commit -m x",
                    "true && env cd ../feature; git commit -m x",
                    "command cd ../feature && git commit -m x"]:  # zsh runs /usr/bin/cd
            self.assertDecision("deny", cmd, cwd=main)
        self.assertDecision("allow", "builtin cd ../feature && git commit -m x", cwd=main)
        self.assertDecision("allow", "env cd ../onmain && git commit -m x", cwd=feat)

    def test_review_round6(self):
        main, feat = self.root / "onmain", self.root / "feature"
        for cmd in [# after a wrapper, D=… is a program name: D stays unset, -C "" is here
                    "env D=../feature; git -C \"$D\" commit -m x",
                    "timeout 5 D=../feature; git -C \"$D\" commit -m x",
                    "/usr/bin/env export D=../feature; cd $D && git commit -m x",
                    # a redirection before the duration is not the duration
                    "timeout 2>/dev/null 60 git commit -m x",
                    "timeout >/dev/null 60 git commit -m x",
                    "timeout 2> >(cat) 60 git commit -m x",
                    "timeout 2 >/dev/null git commit -m x",   # 2 is the duration here
                    # -v / -V only print what cd is: the shell stays put
                    "command -v cd ../feature && git commit -m x",
                    "command -V cd ../feature; git commit -m x",
                    "command -pv cd ../feature; git commit -m x",
                    "command -v pushd ../feature; git commit -m x",
                    # after an option the cd may not run (bash time takes one -p, no --;
                    # zsh time takes none, zsh command runs /usr/bin/cd): unknown
                    "time -- cd ../feature; git commit -m x",
                    "time -p -- cd ../feature; git commit -m x",
                    "time -p -p cd ../feature; git commit -m x",
                    "time -p cd ../feature; git commit -m x",
                    "command -p cd ../feature; git commit -m x",
                    "command -- cd ../feature; git commit -m x",
                    "command -p -- cd ../feature; git commit -m x",
                    "builtin -- cd ../feature; git commit -m x"]:
            self.assertDecision("deny", cmd, cwd=main)
        for cmd in ["command -p cd ../onmain; git commit -m x",   # options do not hide a real cd
                    "command -- cd ../onmain; git commit -m x",
                    "time -p cd ../onmain; git commit -m x"]:
            self.assertDecision("deny", cmd, cwd=feat)
        for cmd in ["timeout 2>/dev/null 60 git commit -m x",
                    "timeout 60 >/dev/null git commit -m x"]:
            self.assertDecision("allow", cmd, cwd=feat)

    def test_append_assignment(self):
        main, feat = self.root / "onmain", self.root / "feature"
        for cmd in [# `D+=` used to be a command word: D stayed the feature repo
                    f"D={feat}; D+=/../onmain; git -C \"$D\" commit -m x",
                    f"D={feat}; D+=/../onmain; cd $D && git commit -m x",
                    f"D={feat}; export D+=/../onmain; git -C \"$D\" commit -m x",
                    # zsh rejects `export D+=`: D stays the main repo there
                    f"D={main}; export D+=/../feature; git -C \"$D\" commit -m x",
                    "D+=../feature; git -C \"$D\" commit -m x",                  # D was unknown
                    "GIT_DIR+=x git commit -m x"]:
            self.assertDecision("deny", cmd, cwd=main)
        for cmd in [f"D={self.root}; D+=/feature; git -C \"$D\" commit -m x",
                    f"D={main}; D+=/../feature E=1; cd \"$D\" && git commit -m x"]:
            self.assertDecision("allow", cmd, cwd=main)

    def test_a_first_time_makes_the_location_unknown(self):
        main, feat = self.root / "onmain", self.root / "feature"
        for cmd in [# after a wrapper both shells run /usr/bin/time: the shell stays put
                    f"time time cd {feat}; git commit -m x",
                    f"builtin time cd {feat}; git commit -m x",
                    # the reserved word or /usr/bin/time by position, quoting and shell:
                    # bash 3.2 runs the program after if/while/!, zsh times in the shell
                    f"time cd {feat}; git commit -m x",
                    f"if time cd {feat}; then git commit -m x; fi",
                    f"until time cd {feat}; do git commit -m x; done",
                    f"! time cd {feat}; git commit -m x",
                    f"case x in x) time cd {feat}; git commit -m x;; esac",
                    f"D=1 time cd {feat}; git commit -m x",
                    f"2>/dev/null time cd {feat}; git commit -m x",
                    f">then time cd {feat}; git commit -m x",       # then is a file name here
                    f"\\time cd {feat}; git commit -m x",            # always /usr/bin/time
                    f"\"time\" cd {feat}; git commit -m x",
                    f"t\"\"ime cd {feat}; git commit -m x",
                    f"time builtin cd {feat}; git commit -m x"]:   # `\\time builtin`: a program
            self.assertDecision("deny", cmd, cwd=main)
        for cmd in [f"builtin builtin cd {feat}; git commit -m x",
                    f"time git -C {feat} commit -m x"]:
            self.assertDecision("allow", cmd, cwd=main)
        for cmd in ["if /usr/bin/time cd ../onmain; then git commit -m x; fi",
                    "time time cd ../onmain; git commit -m x",
                    "command time cd ../onmain; git commit -m x"]:
            self.assertDecision("allow", cmd, cwd=feat)

    def test_xargs_stdbuf_and_zsh_modifiers_are_wrappers(self):
        main, feat = self.root / "onmain", self.root / "feature"
        for cmd in ["xargs git commit -m x", "echo | xargs git commit -m x",
                    "stdbuf -o0 git commit -m x", "noglob git commit -m x",
                    "nocorrect git commit -m x",
                    # xargs appends stdin: the subcommand and -C come from there
                    "echo commit -m x | xargs git", "echo commit | xargs -n9 git",
                    "echo commit | xargs -I{} git {} -m x",
                    f"noglob cd {feat}; git commit -m x",       # zsh moves, bash has no noglob
                    f"nocorrect cd {feat}; git commit -m x"]:
            self.assertDecision("deny", cmd, cwd=main)
        self.assertDecision("deny", "echo -C ../onmain commit -m x | xargs git", cwd=feat)
        for cmd in ["noglob git commit -m x",
                    "xargs cd ../onmain; git commit -m x",      # xargs runs /usr/bin/cd
                    "echo x | xargs echo; git commit -m x"]:
            self.assertDecision("allow", cmd, cwd=feat)
        self.assertDecision("deny", "noglob cd ../onmain; git commit -m x", cwd=feat)

    def test_a_value_flag_does_not_take_a_separator(self):
        # `-C` used to swallow the `;`, hiding the second git as an argument of the first
        for cmd in ["git -C; git commit -m x", "git -C || git commit -m x",
                    "git -c || git commit -m x", "git --git-dir || git commit -m x"]:
            self.assertDecision("deny", cmd, cwd=self.root / "onmain")
        self.assertDecision("allow", "git -C; git commit -m x", cwd=self.root / "feature")

    def test_bang_after_an_assignment_or_redirection_is_a_command(self):
        main, feat = self.root / "onmain", self.root / "feature"
        # bash: `!: command not found`, the cd never runs; zsh: a parse error
        for cmd in [f"D=1 ! cd {feat}; git commit -m x", f"D+=x ! cd {feat}; git commit -m x",
                    f">/dev/null ! cd {feat}; git commit -m x", f"2>/dev/null ! cd {feat}; git commit -m x"]:
            self.assertDecision("deny", cmd, cwd=main)
        self.assertDecision("allow", f"! cd {feat}; git commit -m x", cwd=main)

    def test_dash_c_uses_the_physical_path(self):
        self.assertDecision("deny", "git -C feature/lnk/.. commit -m x")

    def test_redirection_inside_a_git_command(self):
        main, feat = self.root / "onmain", self.root / "feature"
        for cmd in ["git >/dev/null commit -m x",            # used to read no subcommand at all
                    "git 2>/dev/null commit -m x",           # nor `2` as the subcommand
                    "git 2>&1 commit -m x",
                    "git </dev/null commit -m x",
                    "git -C ../feature >/dev/null -C ../onmain commit -m x",
                    "git push >/dev/null --force origin main",  # flags after a redirection
                    "git push 2>&1 -f",
                    "git push origin >/dev/null +main",
                    # a process substitution as the file is one balanced ( … )
                    "git 2> >(cat) commit -m x",
                    "git push 2> >(grep -v x >&2) --force origin main",
                    "git push <(true) -f"]:
            self.assertDecision("deny", cmd, cwd=main)
        for cmd in ["git >/dev/null commit -m x",
                    "git 2>&1 commit -m x >/dev/null",
                    "git 2> >(cat) commit -m x"]:
            self.assertDecision("allow", cmd, cwd=feat)
        # the redirection ends nothing: the next command after ; still counts
        self.assertDecision("deny", "git status >/dev/null; git commit -m x", cwd=main)

    def test_substitution_body_inside_a_git_command(self):
        main, feat = self.root / "onmain", self.root / "feature"
        for cmd in ["git status <(git commit -m x)",          # #1113 skipped the body unread
                    "git status >(git commit -m x)",
                    "git status 2> >(git commit -m x)",
                    "git status $(git commit -m x)",           # never parsed before
                    "git status <(case x in a) git commit -m x;; esac)",  # a pattern `)` is not the end
                    "git status $(case x in a|b) git commit -m x;; esac)"]:
            self.assertDecision("deny", cmd, cwd=main)
        for cmd in ["git status $(cd ../onmain && git commit -m x)",  # runs where the shell is
                    "GIT_DIR=x; git status $(git commit -m x)",       # and sees its variables
                    "cd ../onmain; git status $(git commit -m x)"]:   # after an earlier cd
            self.assertDecision("deny", cmd, cwd=feat)
        self.assertDecision("allow", "cd ../feature; git status $(git commit -m x)", cwd=main)
        # deep nesting fails closed instead of crashing the hook (a crash lets the call through)
        deep = "git status " + "$(git status " * 600 + "x" + ")" * 600
        self.assertDecision("deny", deep, cwd=feat)
        self.assertDecision("allow", "git status $(git status $(git status x))", cwd=feat)
        for cmd in ["git status <(git log -1)",
                    "git commit -m $(date +%s)",
                    "git status $(cd ../onmain); git commit -m x"]:   # a cd in the body stays there
            self.assertDecision("allow", cmd, cwd=feat)

    def test_force_push(self):
        self.assertDecision("deny", "git -C onmain push --force origin main")
        self.assertDecision("deny", "cd onmain && git push -f")
        self.assertDecision("allow", "git -C feature push --force-with-lease")


if __name__ == "__main__":
    unittest.main()
