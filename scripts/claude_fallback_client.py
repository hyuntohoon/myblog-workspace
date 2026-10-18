"""Claude CLI translation used only while the ChatGPT plan is in a usage-limit wait.

Owner request 2026-10-18: the queue keeps moving while GPT is limited (the ChatGPT weekly
limit stopped it for days). Same claim, instructions and output shape as GPTPlanClient; the
model runs through the owner's Claude subscription with no tools, no settings, no MCP and an
empty working directory, so lyrics text cannot reach anything but the model. Calls go through
the shared subscription guard, which serializes every local Claude job and cools down on a
throttle. Provider text (the model's result, stderr) is never logged or kept in an error.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import time
from collections.abc import Callable
from pathlib import Path

from myblog_shared_db.llm.exceptions import LLMTransientError
from myblog_shared_db.llm.subscription_guard import LLMSubscriptionCooldown, coordinated_call, is_throttle_error
from scripts.gpt_plan_client import PlanInferenceError, _shape

DEFAULT_BINARY = Path.home() / '.local' / 'bin' / 'claude'
TIMEOUT_SECONDS = 300
# The DB lease is 20 minutes. Waiting on the guard behind another job must not let a claim
# start a call it cannot finish inside the lease (submit would then be rejected after the spend).
LEASE_MARGIN_SECONDS = TIMEOUT_SECONDS + 120
FEATURE = 'gpt-worker-fallback'


class FallbackError(RuntimeError):
    """``retry`` means the source itself did not fail (throttle, cooldown, lease, CLI missing):
    it stays eligible for the fallback. Otherwise the fallback skips that source until GPT is back."""

    def __init__(self, reason: str, *, retry: bool = False, throttle: bool = False):
        self.reason, self.retry, self.throttle = reason, retry, throttle
        super().__init__(reason)


def _envelope(stdout: str):
    try:
        data = json.loads(stdout)
    except (ValueError, TypeError):
        return None
    return data if isinstance(data, dict) else None


def _throttle_detail(envelope) -> str:
    """Throttle evidence for the guard's markers, without carrying any provider text: the
    status code, and a fixed phrase when the envelope's own result reads as a usage limit."""
    if envelope is None:
        return ''
    detail = ''
    status = envelope.get('api_error_status')
    if isinstance(status, int):
        detail += f' api_error_status={status}'
    if is_throttle_error(LLMTransientError(str(envelope.get('result') or ''))):
        detail += ' usage limit'
    return detail


def _array_text(result: str) -> str:
    text = result.strip()
    if text.startswith('```'):
        text = re.sub(r'^```[a-zA-Z]*\s*', '', text)
        text = re.sub(r'\s*```$', '', text)
    return text


class ClaudeFallbackClient:
    def __init__(self, binary: Path = DEFAULT_BINARY, workdir: Path | None = None, *,
                 run=subprocess.run, call=coordinated_call, clock: Callable[[], float] = time.monotonic,
                 timeout_seconds: int = TIMEOUT_SECONDS):
        self.binary, self.workdir = Path(binary), workdir
        self.run, self.call, self.clock, self.timeout_seconds = run, call, clock, timeout_seconds

    def argv(self, model, instructions):
        return [str(self.binary), '-p', '--safe-mode', '--tools', '', '--strict-mcp-config',
                '--setting-sources', '', '--no-session-persistence', '--output-format', 'json',
                '--model', model, '--system-prompt',
                instructions + ' Return only a JSON array of {i,text_ko} objects; no Markdown fences or explanation.']

    def translate(self, claim, model, claimed_at=None):
        """(segments, actual_model, usage) like GPTPlanClient.translate, or FallbackError."""
        source = claim.get('segments')
        instructions = claim.get('instructions')
        if (not isinstance(source, list) or not source or not isinstance(instructions, str) or not instructions
                or not isinstance(model, str) or not model.strip()):
            raise FallbackError('invalid_source')
        if not self.binary.is_file() or not os.access(self.binary, os.X_OK):
            raise FallbackError('claude_cli_missing', retry=True)
        started = self.clock() if claimed_at is None else claimed_at
        lease = claim.get('lease_seconds', 1200)

        def dispatch():
            if self.clock() - started > lease - LEASE_MARGIN_SECONDS:
                raise FallbackError('lease_too_short', retry=True)
            try:
                proc = self.run(self.argv(model, instructions), input=json.dumps(source, ensure_ascii=False),
                                capture_output=True, text=True, timeout=self.timeout_seconds,
                                cwd=str(self.workdir) if self.workdir else None)
            except subprocess.TimeoutExpired:
                raise FallbackError('temporary_error') from None
            except OSError:
                raise FallbackError('claude_cli_missing', retry=True) from None
            envelope = _envelope(proc.stdout)
            if proc.returncode != 0 or envelope is None or envelope.get('is_error'):
                # LLMTransientError so the guard can recognise a throttle and cool every job down.
                raise LLMTransientError(f'claude exit {proc.returncode}:{_throttle_detail(envelope)}')
            return envelope

        try:
            envelope = self.call(dispatch, feature=FEATURE)
        except LLMSubscriptionCooldown:
            raise FallbackError('claude_cooldown', retry=True, throttle=True) from None
        except LLMTransientError as error:
            if is_throttle_error(error):
                raise FallbackError('claude_throttled', retry=True, throttle=True) from None
            raise FallbackError('temporary_error') from None
        result = envelope.get('result')
        if not isinstance(result, str) or not result.strip():
            raise FallbackError('invalid_output')
        try:
            segments = _shape(json.loads(_array_text(result)))
        except (ValueError, PlanInferenceError):
            # Prose instead of a JSON array is how Claude refuses lyrics (FEAT-lyrics-chat).
            raise FallbackError('invalid_output') from None
        models = envelope.get('modelUsage') if isinstance(envelope.get('modelUsage'), dict) else {}
        matching = [name for name in models if model.lower() in name.lower()] or list(models)
        actual = max(matching, key=lambda name: (models[name] or {}).get('outputTokens', 0) or 0, default=None)
        actual = actual if isinstance(actual, str) and actual.strip() and len(actual) <= 200 else 'claude/' + model
        usage = envelope.get('usage') if isinstance(envelope.get('usage'), dict) else {}
        tokens = {'input_tokens': int(usage.get('input_tokens') or 0) + int(usage.get('cache_creation_input_tokens') or 0),
                  'cached_input_tokens': int(usage.get('cache_read_input_tokens') or 0),
                  'output_tokens': int(usage.get('output_tokens') or 0), 'reasoning_tokens': 0}
        return segments, actual, tokens
