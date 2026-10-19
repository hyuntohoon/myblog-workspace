#!/usr/bin/env python3
"""One-shot subscription CLI benchmark. No database, retries, or fallback.

Manifest paths are relative to the manifest. Each model has a unique ``id``,
``provider`` (claude/gpt), exact ``model``, and ``availability``. Only the literal
availability ``available`` dispatches. --dry-run never dispatches or writes.
All persistent artifacts live under artifact_dir; fresh temporary working
directories outside the repository avoid inheriting repository instructions.
CLI flags were checked against installed Claude/Codex --help on 2026-10-15.
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import importlib.util
import json
import os
import re
import signal
import subprocess
import sys
import tempfile
import time
import types
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


DEFAULT_GUARD_SRC = "/Users/park_hyun/myblog-workspace/myblog_shared_db/src"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def emit(event: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(event, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_guard(src: Path) -> Any:
    """Import the real guard without shared_db.__init__ loading DB models.

    Its only relative import is exceptions.py. A private package namespace lets
    both source files execute unchanged, with no copied coordination logic.
    The default guard state directory remains shared with production pollers.
    """
    package_name = "_research_benchmark_subscription"
    package = types.ModuleType(package_name)
    package.__path__ = [str(src / "myblog_shared_db" / "llm")]
    sys.modules[package_name] = package
    for leaf in ("exceptions", "subscription_guard"):
        name = f"{package_name}.{leaf}"
        path = src / "myblog_shared_db" / "llm" / f"{leaf}.py"
        spec = importlib.util.spec_from_file_location(name, path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot load subscription guard source: {path}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    return sys.modules[f"{package_name}.subscription_guard"]


def command(model: dict[str, Any], output: Path, mcp_config: Path) -> list[str]:
    effort = model.get("reasoning_effort")
    if model["provider"] == "claude":
        argv = [
            "/Users/park_hyun/.local/bin/claude", "--print", "--verbose",
            "--output-format", "stream-json", "--model", model["model"],
            "--tools", "WebSearch,WebFetch", "--allowedTools", "WebSearch,WebFetch",
            "--permission-mode", "dontAsk", "--permission-prompts", "none",
            "--no-chrome", "--no-session-persistence", "--strict-mcp-config",
            "--mcp-config", str(mcp_config),
            # Without it the lane fires the operator's SessionStart hooks and loads
            # the global CLAUDE.md and auto-memory despite the isolated cwd. --bare
            # would also do it but refuses subscription (OAuth) auth.
            "--safe-mode",
        ]
        if effort:
            argv.extend(["--effort", effort])
        return argv
    # "web_search": false (Stage B round 3 §10 reviewer lane) runs Codex with no web tool.
    # The override must follow `exec`: placed before it, the web tool stayed available (probe 2026-10-19).
    web = model.get("web_search", True)
    argv = [
        "codex", *(["--search"] if web else []), "--ask-for-approval", "never", "exec",
        # With web_search disabled Codex still searched through the ChatGPT apps connector
        # (codex_apps search_service.web_run), so apps and plugins go off too, and the
        # operator's browser-capable MCP servers (~/.codex/config.toml; `mcp_servers={}` does not clear them).
        *([] if web else ["-c", 'web_search="disabled"', "-c", "mcp_servers.chrome-devtools.enabled=false",
                    "-c", "mcp_servers.node_repl.enabled=false", "--disable", "apps", "--disable", "plugins"]),
        "--model", model["model"], "--sandbox", "read-only", "--json",
        "--ephemeral", "--skip-git-repo-check", "--output-last-message", str(output),
    ]
    if effort:
        argv.extend(["-c", f'model_reasoning_effort="{effort}"'])
    argv.append("-")
    return argv


def subscription_environment() -> dict[str, str]:
    """Do not let ambient API-key variables switch a subscription run to API billing."""
    env = os.environ.copy()
    for key in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_BASE_URL",
                "OPENAI_API_KEY", "OPENAI_BASE_URL", "OPENAI_ORG_ID",
                "OPENAI_ORGANIZATION", "OPENAI_PROJECT_ID",
                "CLAUDE_CODE_USE_BEDROCK", "CLAUDE_CODE_USE_VERTEX",
                "CLAUDE_CODE_USE_FOUNDRY"):
        env.pop(key, None)
    return env


def reap_group(proc: subprocess.Popen[str]) -> tuple[str, str]:
    """Reap the CLI and any tool subprocesses, including on timeout/interruption."""
    with contextlib.suppress(ProcessLookupError):
        os.killpg(proc.pid, signal.SIGTERM)
    try:
        return proc.communicate(timeout=3)
    except subprocess.TimeoutExpired:
        with contextlib.suppress(ProcessLookupError):
            os.killpg(proc.pid, signal.SIGKILL)
        return proc.communicate()


def run_process(argv: list[str], prompt: str, cwd: Path, timeout_s: float) -> dict[str, Any]:
    started = time.monotonic()
    proc = subprocess.Popen(argv, cwd=cwd, stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            text=True, encoding="utf-8", errors="replace",
                            env=subscription_environment(), start_new_session=True)
    timed_out = False
    try:
        stdout, stderr = proc.communicate(prompt, timeout=timeout_s)
    except subprocess.TimeoutExpired:
        timed_out = True
        stdout, stderr = reap_group(proc)
    except BaseException:
        reap_group(proc)
        raise
    return {"stdout": stdout, "stderr": stderr, "returncode": proc.returncode,
            "timed_out": timed_out, "process_wall_s": round(time.monotonic() - started, 3)}


def parse_events(stdout: str, provider: str) -> dict[str, Any]:
    events, non_json_lines = [], 0
    for line in stdout.splitlines():
        try:
            value = json.loads(line)
        except ValueError:
            non_json_lines += bool(line.strip())
            continue
        if isinstance(value, dict):
            events.append(value)
    resolved: set[str] = set()
    errors, text_parts, tool_counts = [], [], {}
    usage = []
    hook_events, memory_paths, init = 0, {}, None
    for event in events:
        if event.get("type") == "system" and str(event.get("subtype", "")).startswith("hook_"):
            hook_events += 1
        if event.get("type") == "system" and event.get("subtype") == "init":
            memory_paths = event.get("memory_paths") or {}
            init = {"tools": sorted(event.get("tools") or []),
                    **{f"{k}_count": len(event.get(k) or []) for k in
                       ("skills", "plugins", "agents", "slash_commands", "mcp_servers")}}
        if event.get("model"):
            resolved.add(str(event["model"]))
        if isinstance(event.get("modelUsage"), dict):
            resolved.update(event["modelUsage"])
            usage.append(event["modelUsage"])
        message = event.get("message", {})
        if isinstance(message, dict) and message.get("model"):
            resolved.add(str(message["model"]))
        if event.get("is_error") or event.get("type") in ("error", "turn.failed"):
            errors.append(event)
        if event.get("type") == "result":
            if event.get("result"):
                text_parts = [str(event["result"])]
            if event.get("usage"):
                usage.append(event["usage"])
        if event.get("type") == "assistant" and isinstance(message, dict):
            for block in message.get("content", []):
                if block.get("type") == "text":
                    text_parts.append(block["text"])
                if block.get("type") == "tool_use":
                    name = block.get("name", "unknown")
                    tool_counts[name] = tool_counts.get(name, 0) + 1
        item = event.get("item", {})
        if event.get("type") == "item.completed" and isinstance(item, dict):
            if item.get("type") == "agent_message":
                text_parts.append(item.get("text", ""))
            elif item.get("type") == "web_search":
                tool_counts["web_search"] = tool_counts.get("web_search", 0) + 1
        if event.get("type") == "turn.completed" and event.get("usage"):
            usage.append(event["usage"])
    return {"resolved_models": sorted(resolved), "resolution_evidence":
            "cli_event" if resolved else "not_exposed_by_cli",
            "cli_errors": errors, "usage_reported": usage,
            "tool_counts": tool_counts, "event_count": len(events),
            "hook_event_count": hook_events, "memory_paths": memory_paths, "cli_init": init,
            "non_json_line_count": non_json_lines, "text": "\n\n".join(text_parts)}


def failure_status(result: dict[str, Any], parsed: dict[str, Any]) -> str:
    if result["timed_out"]:
        return "timeout"
    if not result["returncode"] and not parsed["cli_errors"]:
        return "success"
    diagnostic = (result["stderr"] + "\n" +
                  json.dumps(parsed["cli_errors"], ensure_ascii=False)).lower()
    throttle_markers = ("rate limit", "rate_limit", "too many requests",
                        "usage limit", "usage_limit", "hit your limit",
                        "you've hit", "limit reached", "quota exceeded",
                        "exceeded your current quota", "throttl")
    if any(marker in diagnostic for marker in throttle_markers) or re.search(r"\b429\b", diagnostic):
        return "rate_limited"
    unavailable = ("model_not_found", "model not found", "unsupported model",
                   "model is not supported", "model does not exist",
                   "there is no model with", "you don't have access to the model",
                   "not available for your account")
    return "unavailable" if any(x in diagnostic for x in unavailable) else "failed"


def execute_one(model: dict[str, Any], prompt: str, artifact_root: Path,
                timeout_s: float, guard: Any = None,
                process: Callable[..., dict[str, Any]] = run_process,
                *, not_run_reason: str | None = None) -> dict[str, Any]:
    run_dir = artifact_root / model["id"]
    # Atomic directory creation is an exactly-once dispatch claim. A crash or
    # failure never silently authorizes another attempt under the same ID.
    run_dir.mkdir(parents=False, exist_ok=False)
    metadata = {"id": model["id"], "provider": model["provider"],
                "requested_model": model["model"], "model_config": model,
                "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
                "started_at": utc_now(), "status": "claimed", "dispatch_count": 0,
                "orchestration_retry_policy": "none", "orchestration_fallback_policy": "none"}
    write_json(run_dir / "metadata.json", metadata)
    (run_dir / "input.txt").write_text(prompt, encoding="utf-8")
    if not_run_reason or model["availability"] != "available":
        metadata.update(status="unavailable" if not not_run_reason and model["availability"] == "unavailable"
                        else "not_run", reason=not_run_reason or model.get("unavailable_reason", model["availability"]),
                        finished_at=utc_now(), wall_s=0)
        write_json(run_dir / "metadata.json", metadata)
        return metadata
    started = time.monotonic()
    result: dict[str, Any] | None = None
    guard_throttle_detected = False
    try:
        with tempfile.TemporaryDirectory(prefix="research-benchmark-", dir="/private/tmp") as isolated:
            cwd = Path(isolated)
            metadata["isolated_cwd"] = isolated
            mcp = run_dir / "empty-mcp.json"
            write_json(mcp, {"mcpServers": {}})
            argv = command(model, run_dir / "output.md", mcp)
            metadata["argv"] = argv

            def dispatch() -> dict[str, Any]:
                nonlocal result
                metadata["dispatch_count"] = 1
                metadata["status"] = "running"
                write_json(run_dir / "metadata.json", metadata)
                result = process(argv, prompt, cwd, timeout_s)
                parsed = parse_events(result["stdout"], model["provider"])
                if model["provider"] == "claude" and (
                        result["returncode"] or parsed["cli_errors"]):
                    # Preserve the existing shared throttle/cooldown semantics.
                    diagnostic = result["stderr"]
                    if parsed["cli_errors"]:
                        diagnostic += "\n" + json.dumps(parsed["cli_errors"])
                    raise guard.LLMTransientError(f'claude exit {result["returncode"]}: {diagnostic.strip()}')
                return result

            if model["provider"] == "claude":
                if guard is None:
                    raise RuntimeError("Claude requires the existing shared subscription guard")
                guard.coordinated_call(dispatch, feature=f'research-benchmark:{model["id"]}')
            else:
                dispatch()
    except KeyboardInterrupt:
        metadata.update(status="interrupted", error="Interrupted by operator")
        raise
    except Exception as exc:
        metadata.update(status="failed", error_type=type(exc).__name__, error=str(exc))
        if guard is not None and isinstance(exc, guard.LLMSubscriptionCooldown):
            metadata["status"] = "blocked_cooldown"
        elif guard is not None and getattr(guard, "is_throttle_error", lambda exc: False)(exc):
            guard_throttle_detected = True
    finally:
        if result is not None:
            (run_dir / "stdout.jsonl").write_text(result["stdout"], encoding="utf-8")
            (run_dir / "stderr.txt").write_text(result["stderr"], encoding="utf-8")
            parsed = parse_events(result["stdout"], model["provider"])
            metadata.update({k: v for k, v in parsed.items() if k != "text"})
            metadata.update(returncode=result["returncode"], process_wall_s=result["process_wall_s"],
                            status=failure_status(result, parsed))
            if guard_throttle_detected and metadata["status"] == "failed":
                metadata["status"] = "rate_limited"
            if metadata["status"] == "success" and model["provider"] == "claude":
                # Safe mode still lists plugins/skills in init; they are unreachable only
                # because the tool set is exactly the requested one (no Skill/Agent tool).
                init = parsed["cli_init"] or {}
                if (parsed["hook_event_count"] or parsed["memory_paths"]
                        or init.get("tools") != ["WebFetch", "WebSearch"]):
                    metadata.update(status="failed", error="Claude CLI run is not instruction-clean "
                                    "(hook events, memory paths, or a tool set other than WebSearch+WebFetch)")
            output_path = run_dir / "output.md"
            if not output_path.exists() or not output_path.read_text(encoding="utf-8").strip():
                output_path.write_text(parsed["text"], encoding="utf-8")
            if metadata["status"] == "success" and not output_path.read_text(encoding="utf-8").strip():
                metadata.update(status="failed", error="CLI completed without a research note")
        metadata.update(finished_at=utc_now(), wall_s=round(time.monotonic() - started, 3))
        write_json(run_dir / "metadata.json", metadata)
    return metadata


def validate_models(models: Any) -> None:
    if not isinstance(models, list) or not models:
        raise ValueError("manifest.models must be a nonempty list")
    seen = set()
    for model in models:
        model_id = model.get("id", "")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,100}", model_id):
            raise ValueError(f"Invalid model run id: {model_id!r}")
        if model_id in seen:
            raise ValueError(f"Duplicate model run id: {model_id}")
        seen.add(model_id)
        if model.get("provider") not in ("claude", "gpt"):
            raise ValueError(f"Unknown provider: {model.get('provider')}")
        if not isinstance(model.get("model"), str) or not model["model"]:
            raise ValueError("Every entry needs an exact requested model")
        if model.get("availability") not in ("available", "unavailable", "pending_cost_approval", "excluded"):
            raise ValueError("Every entry needs explicit availability")
        if model.get("reasoning_effort") not in (None, "low", "medium", "high", "xhigh", "max", "ultra"):
            raise ValueError("Invalid reasoning effort")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--prompt", required=True, type=Path)
    parser.add_argument("--input", action="append", type=Path, default=[],
                        help="Append shared album/context inputs, in this order")
    parser.add_argument("--provider", choices=("claude", "gpt"))
    parser.add_argument("--only", action="append", default=[])
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    validate_models(manifest.get("models"))
    prompt = "\n\n".join(path.read_text(encoding="utf-8") for path in [args.prompt, *args.input])
    expected_hash = manifest.get("expected_prompt_sha256")
    if expected_hash and expected_hash != hashlib.sha256(prompt.encode()).hexdigest():
        parser.error("Frozen combined prompt SHA256 mismatch; refusing to dispatch")
    root = (args.manifest.resolve().parent / manifest["artifact_dir"]).resolve()
    models = [m for m in manifest["models"] if
              (not args.provider or m["provider"] == args.provider) and
              (not args.only or m["id"] in args.only)]
    if not models:
        parser.error("No models selected")
    timeout_s = float(manifest.get("timeout_s", 1800))
    if timeout_s <= 0:
        parser.error("timeout_s must be positive")
    if args.dry_run:
        for model in models:
            emit({"event": "dry_run", "model": model,
                  "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
                  "argv": command(model, root / model["id"] / "output.md",
                                  root / model["id"] / "empty-mcp.json"),
                  "artifact_dir": str(root / model["id"]), "timeout_s": timeout_s})
        return 0
    # Validate the whole selection before a single dispatch; reruns require a
    # new explicit manifest/ID instead of silently replaying completed models.
    root.mkdir(parents=True, exist_ok=True)
    for model in models:
        if (root / model["id"]).exists():
            parser.error(f'Run already claimed: {model["id"]}; no retries allowed')
    guard = None
    if any(m["provider"] == "claude" and m["availability"] == "available" for m in models):
        guard = load_guard(Path(manifest.get("shared_db_src", DEFAULT_GUARD_SRC)))
    failed = False
    stopped_providers: dict[str, str] = {}
    for model in models:
        emit({"event": "model_start", "id": model["id"], "model": model["model"]})
        reason = stopped_providers.get(model["provider"]) if model["availability"] == "available" else None
        metadata = execute_one(model, prompt, root, timeout_s, guard, not_run_reason=reason)
        emit({"event": "model_complete", **metadata})
        if metadata["status"] in ("rate_limited", "blocked_cooldown"):
            stopped_providers[model["provider"]] = (
                f'Provider lane halted after {model["id"]}: {metadata["status"]}; '
                "no further inference or automatic retry authorized")
        failed |= metadata["status"] not in ("success", "unavailable", "not_run")
    return int(failed)


if __name__ == "__main__":
    raise SystemExit(main())
