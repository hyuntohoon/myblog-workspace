"""Focused offline contract checks: no model calls and no production DB access."""
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "research_model_benchmark.py"
spec = importlib.util.spec_from_file_location("research_benchmark_under_test", SCRIPT)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class BenchmarkTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.model = {"id": "gpt-one", "provider": "gpt", "model": "gpt-example",
                      "availability": "available", "reasoning_effort": "medium"}

    def tearDown(self):
        self.tmp.cleanup()

    def result(self, text="research note", rc=0):
        return {"stdout": json.dumps({"type": "item.completed", "item": {
            "type": "agent_message", "text": text}}) + "\n", "stderr": "",
            "returncode": rc, "timed_out": False, "process_wall_s": 1.0}

    def test_exactly_one_dispatch_and_claim_refuses_replay(self):
        calls = []

        def fake(argv, prompt, cwd, timeout):
            calls.append(argv)
            self.assertFalse((cwd / "AGENTS.md").exists())
            self.assertNotEqual(cwd.parent, self.root)
            return self.result()

        metadata = runner.execute_one(self.model, "frozen prompt", self.root, 1, process=fake)
        self.assertEqual(metadata["status"], "success")
        self.assertEqual(metadata["dispatch_count"], 1)
        self.assertEqual(len(calls), 1)
        with self.assertRaises(FileExistsError):
            runner.execute_one(self.model, "frozen prompt", self.root, 1, process=fake)
        self.assertEqual(len(calls), 1)
        self.assertEqual((self.root / "gpt-one/input.txt").read_text(), "frozen prompt")

    def test_failed_model_is_not_retried_or_substituted(self):
        calls = []

        def fake(*args):
            calls.append(args[0])
            result = self.result(rc=1)
            result["stderr"] = "service unavailable"
            return result

        metadata = runner.execute_one(self.model, "input", self.root, 1, process=fake)
        self.assertEqual(metadata["status"], "failed")
        self.assertEqual(len(calls), 1)
        self.assertIn("gpt-example", calls[0])
        self.assertEqual(metadata["resolved_models"], [])
        self.assertEqual(metadata["resolution_evidence"], "not_exposed_by_cli")

    def test_unavailable_and_cost_pending_never_dispatch(self):
        def forbidden(*args):
            self.fail("Unavailable model dispatched")

        for availability, status in [("unavailable", "unavailable"),
                                     ("pending_cost_approval", "not_run")]:
            model = {**self.model, "id": availability, "availability": availability,
                     "unavailable_reason": "documented inventory evidence"}
            metadata = runner.execute_one(model, "input", self.root, 1, process=forbidden)
            self.assertEqual(metadata["status"], status)
            self.assertEqual(metadata["dispatch_count"], 0)

    def test_timeout_retains_partial_events_and_reaps_process(self):
        script = 'import json,time; print(json.dumps({"type":"start"}),flush=True); time.sleep(20)'

        def actual_timeout(argv, prompt, cwd, timeout):
            return runner.run_process([sys.executable, "-c", script], prompt, cwd, .15)

        metadata = runner.execute_one(self.model, "input", self.root, .15, process=actual_timeout)
        self.assertEqual(metadata["status"], "timeout")
        self.assertEqual(metadata["dispatch_count"], 1)
        self.assertLess(metadata["wall_s"], 5)
        self.assertIn('"start"', (self.root / "gpt-one/stdout.jsonl").read_text())
        self.assertIsNotNone(metadata["returncode"])

    def test_model_error_event_even_exit_zero_is_failure(self):
        def fake(*args):
            result = self.result()
            result["stdout"] += json.dumps({"type": "turn.failed", "error": "broken"})
            return result

        metadata = runner.execute_one(self.model, "input", self.root, 1, process=fake)
        self.assertEqual(metadata["status"], "failed")

    def test_claude_dispatch_is_inside_guard_without_fallback(self):
        class Guard:
            class LLMTransientError(Exception):
                pass

            class LLMSubscriptionCooldown(Exception):
                pass

            active = False
            calls = 0

            def coordinated_call(self, operation, *, feature):
                self.calls += 1
                self.active = True
                try:
                    return operation()
                finally:
                    self.active = False

        guard = Guard()
        model = {**self.model, "provider": "claude", "model": "claude-example"}

        def fake(argv, *args):
            self.assertTrue(guard.active)
            self.assertNotIn("--fallback-model", argv)
            self.assertEqual(argv[argv.index("--tools") + 1], "WebSearch,WebFetch")
            self.assertIn("--permission-prompts", argv)
            self.assertNotIn("--dangerously-skip-permissions", argv)
            return {"stdout": json.dumps({"type": "result", "result": "note",
                "modelUsage": {"claude-example-resolved": {"inputTokens": 12}}}),
                "stderr": "", "returncode": 0, "timed_out": False, "process_wall_s": 1}

        metadata = runner.execute_one(model, "input", self.root, 1, guard, fake)
        self.assertEqual(guard.calls, 1)
        self.assertEqual(metadata["status"], "success")
        self.assertEqual(metadata["resolved_models"], ["claude-example-resolved"])

    def test_empty_output_fails_and_duplicate_manifest_rejected(self):
        metadata = runner.execute_one(self.model, "input", self.root, 1,
                                      process=lambda *args: self.result(text=""))
        self.assertEqual(metadata["status"], "failed")
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            runner.validate_models([self.model, self.model])

    def test_guard_cooldown_is_a_blocked_non_attempt(self):
        class Guard:
            class LLMSubscriptionCooldown(Exception):
                pass

            def coordinated_call(self, operation, *, feature):
                raise self.LLMSubscriptionCooldown("shared account cooldown")

        model = {**self.model, "provider": "claude"}
        metadata = runner.execute_one(model, "input", self.root, 1, Guard(),
                                      lambda *args: self.fail("Dispatched during cooldown"))
        self.assertEqual(metadata["status"], "blocked_cooldown")
        self.assertEqual(metadata["dispatch_count"], 0)

    def test_throttle_stops_remaining_provider_lane_without_inference(self):
        models = [{**self.model, "id": f"gpt-{number}"} for number in range(3)]
        models.append({**self.model, "id": "excluded-fable", "provider": "claude",
                       "availability": "excluded", "unavailable_reason": "cost excluded"})
        manifest = self.root / "manifest.json"
        manifest.write_text(json.dumps({"artifact_dir": "runs", "models": models}))
        prompt = self.root / "prompt.md"
        prompt.write_text("frozen")
        dispatches = []
        original_execute = runner.execute_one

        def fake_process(*args):
            dispatches.append(args[0])
            result = self.result(rc=1)
            result["stderr"] = "HTTP 429: rate limit exceeded"
            return result

        def execute(*args, **kwargs):
            return original_execute(*args, process=fake_process, **kwargs)

        with patch.object(runner, "execute_one", side_effect=execute):
            self.assertEqual(runner.main(["--manifest", str(manifest), "--prompt", str(prompt)]), 1)
        self.assertEqual(len(dispatches), 1)
        first = json.loads((self.root / "runs/gpt-0/metadata.json").read_text())
        self.assertEqual(first["status"], "rate_limited")
        for run_id in ("gpt-1", "gpt-2"):
            metadata = json.loads((self.root / f"runs/{run_id}/metadata.json").read_text())
            self.assertEqual(metadata["status"], "not_run")
            self.assertEqual(metadata["dispatch_count"], 0)
            self.assertIn("Provider lane halted after gpt-0", metadata["reason"])
        excluded = json.loads((self.root / "runs/excluded-fable/metadata.json").read_text())
        self.assertEqual(excluded["reason"], "cost excluded")

    def test_error_event_throttle_even_with_zero_exit_is_rate_limited(self):
        result = self.result()
        result["stdout"] += json.dumps({"type": "turn.failed", "error": {
            "message": "You've hit your usage limit"}})
        parsed = runner.parse_events(result["stdout"], "gpt")
        self.assertEqual(runner.failure_status(result, parsed), "rate_limited")

    def test_frozen_hash_mismatch_never_creates_artifact_root(self):
        manifest = self.root / "manifest.json"
        manifest.write_text(json.dumps({"artifact_dir": "runs", "models": [self.model],
                                         "expected_prompt_sha256": "wrong"}))
        prompt = self.root / "prompt.md"
        prompt.write_text("changed")
        with self.assertRaises(SystemExit):
            runner.main(["--manifest", str(manifest), "--prompt", str(prompt)])
        self.assertFalse((self.root / "runs").exists())

    def test_live_search_read_only_and_never_approval_flags(self):
        argv = runner.command(self.model, self.root / "output", self.root / "mcp")
        self.assertIn("--search", argv)
        self.assertEqual(argv[argv.index("--sandbox") + 1], "read-only")
        self.assertEqual(argv[argv.index("--ask-for-approval") + 1], "never")
        self.assertNotIn("--ignore-rules", argv)
        self.assertNotIn("--ignore-user-config", argv)

    def test_dry_run_has_no_artifacts_or_dispatch(self):
        manifest = self.root / "manifest.json"
        manifest.write_text(json.dumps({"artifact_dir": "runs", "models": [self.model]}))
        prompt = self.root / "prompt.md"
        prompt.write_text("frozen")
        self.assertEqual(runner.main(["--manifest", str(manifest), "--prompt", str(prompt),
                                      "--dry-run"]), 0)
        self.assertFalse((self.root / "runs").exists())


if __name__ == "__main__":
    unittest.main()
