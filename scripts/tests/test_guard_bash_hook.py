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

    def test_force_push(self):
        self.assertDecision("deny", "git -C onmain push --force origin main")
        self.assertDecision("deny", "cd onmain && git push -f")
        self.assertDecision("allow", "git -C feature push --force-with-lease")


if __name__ == "__main__":
    unittest.main()
