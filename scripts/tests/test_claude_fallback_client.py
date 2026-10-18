"""Claude fallback client: argv, envelope parsing and failure mapping; no real CLI call."""
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
for path in (ROOT, ROOT / 'myblog_backend', ROOT / 'myblog_shared_db' / 'src'):
    sys.path.insert(0, str(path))

import pytest
from myblog_shared_db.llm.subscription_guard import LLMSubscriptionCooldown, coordinated_call
from scripts.claude_fallback_client import LEASE_MARGIN_SECONDS, ClaudeFallbackClient, FallbackError

CLAIM = {'segments': [{'i': 0, 'text': 'first line'}, {'i': 1, 'text': ''}],
         'instructions': 'Translate into Korean.', 'lease_seconds': 1200}
GOOD = [{'i': 0, 'text_ko': '첫 줄'}, {'i': 1, 'text_ko': ''}]


def envelope(result, **extra):
    data = {'is_error': False, 'result': result, 'usage': {'input_tokens': 3, 'cache_read_input_tokens': 5,
            'cache_creation_input_tokens': 2, 'output_tokens': 7},
            'modelUsage': {'claude-haiku-5-5': {'outputTokens': 900}, 'claude-opus-5-5': {'outputTokens': 7}}}
    data.update(extra)
    return json.dumps(data)


@pytest.fixture
def binary(tmp_path):
    path = tmp_path / 'claude'
    path.write_text('#!/bin/sh\n')
    path.chmod(0o700)
    return path


def client(binary, tmp_path, stdout='', returncode=0, raises=None, clock=None):
    calls = []

    def run(argv, **kwargs):
        calls.append((argv, kwargs))
        if raises:
            raise raises
        return SimpleNamespace(returncode=returncode, stdout=stdout, stderr='provider said secret things')

    def call(operation, feature):
        return coordinated_call(operation, feature=feature, state_dir=tmp_path / 'guard', min_gap_s=0)

    made = ClaudeFallbackClient(binary, tmp_path, run=run, call=call, clock=clock or (lambda: 0.0))
    return made, calls


def test_success_returns_segments_requested_model_and_usage(binary, tmp_path):
    made, calls = client(binary, tmp_path, stdout=envelope(json.dumps(GOOD, ensure_ascii=False)))
    segments, model, usage = made.translate(CLAIM, 'opus')
    assert segments == GOOD
    # The requested model wins over a helper that wrote more (cli_engine._attributed_model).
    assert model == 'claude-opus-5-5'
    assert usage == {'input_tokens': 5, 'cached_input_tokens': 5, 'output_tokens': 7, 'reasoning_tokens': 0}
    argv, kwargs = calls[0]
    for flag in ('--safe-mode', '--strict-mcp-config', '--no-session-persistence'):
        assert flag in argv
    assert argv[argv.index('--tools') + 1] == '' and argv[argv.index('--setting-sources') + 1] == ''
    assert argv[argv.index('--model') + 1] == 'opus'
    # Only the source array goes on stdin; instructions go in the system prompt.
    assert json.loads(kwargs['input']) == CLAIM['segments']
    assert kwargs['cwd'] == str(tmp_path) and kwargs['timeout'] == 300


def test_fenced_array_is_accepted(binary, tmp_path):
    made, _ = client(binary, tmp_path, stdout=envelope('```json\n' + json.dumps(GOOD) + '\n```'))
    assert made.translate(CLAIM, 'opus')[0] == GOOD


@pytest.mark.parametrize('result', ['이 가사는 저작권이 있어 번역할 수 없습니다.', '[{"i":0}]', '[]'])
def test_prose_or_bad_shape_is_invalid_output_and_skips(binary, tmp_path, result):
    made, _ = client(binary, tmp_path, stdout=envelope(result))
    with pytest.raises(FallbackError) as error:
        made.translate(CLAIM, 'opus')
    assert error.value.reason == 'invalid_output' and not error.value.retry
    assert 'secret' not in str(error.value) and '저작권' not in str(error.value)


@pytest.mark.parametrize('stdout,returncode', [
    (envelope("You've hit your limit · resets 5am", is_error=True), 1),
    (envelope('ignored', is_error=True, api_error_status=429), 0)])
def test_throttle_is_retryable_and_cools_the_shared_guard(binary, tmp_path, stdout, returncode):
    made, calls = client(binary, tmp_path, stdout=stdout, returncode=returncode)
    with pytest.raises(FallbackError) as error:
        made.translate(CLAIM, 'opus')
    assert error.value.reason == 'claude_throttled' and error.value.retry and error.value.throttle
    # Every other local Claude job now sees the cooldown, and so does the next fallback call.
    with pytest.raises(FallbackError) as again:
        made.translate(CLAIM, 'opus')
    assert again.value.reason == 'claude_cooldown' and again.value.throttle
    assert len(calls) == 1


def test_blank_failed_exit_is_not_a_throttle(binary, tmp_path):
    made, _ = client(binary, tmp_path, stdout='', returncode=1)
    with pytest.raises(FallbackError) as error:
        made.translate(CLAIM, 'opus')
    assert error.value.reason == 'temporary_error' and not error.value.retry


def test_timeout_is_temporary_and_missing_cli_is_retryable(binary, tmp_path):
    made, _ = client(binary, tmp_path, raises=subprocess.TimeoutExpired('claude', 300))
    with pytest.raises(FallbackError) as error:
        made.translate(CLAIM, 'opus')
    assert error.value.reason == 'temporary_error'
    missing = ClaudeFallbackClient(tmp_path / 'nope', tmp_path)
    with pytest.raises(FallbackError) as error:
        missing.translate(CLAIM, 'opus')
    assert error.value.reason == 'claude_cli_missing' and error.value.retry


def test_a_claim_that_waited_too_long_for_the_guard_is_not_dispatched(binary, tmp_path):
    now = [0.0]
    made, calls = client(binary, tmp_path, stdout=envelope(json.dumps(GOOD)), clock=lambda: now[0])
    now[0] = 1200 - LEASE_MARGIN_SECONDS + 1
    with pytest.raises(FallbackError) as error:
        made.translate(CLAIM, 'opus', claimed_at=0.0)
    assert error.value.reason == 'lease_too_short' and error.value.retry
    assert calls == []


def test_existing_cooldown_raises_before_any_call(binary, tmp_path):
    def cooling(operation, feature):
        raise LLMSubscriptionCooldown(60)
    made = ClaudeFallbackClient(binary, tmp_path, run=lambda *a, **k: pytest.fail('dispatched'), call=cooling)
    with pytest.raises(FallbackError) as error:
        made.translate(CLAIM, 'opus')
    assert error.value.reason == 'claude_cooldown'
