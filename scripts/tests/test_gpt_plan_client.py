"""No live model calls: transport and account permission are both mocked."""
import json
from pathlib import Path
import sys

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.gpt_plan_auth import PlanUnavailable
from scripts.gpt_plan_client import GPTPlanClient, PAUSE_CODES, PlanInferenceError, RESPONSES_URL

SOURCE = [{"i": 0, "text": "private source"}, {"i": 1, "text": ""}]
RESULT = [{"i": 0, "text_ko": "번역"}, {"i": 1, "text_ko": ""}]
CLAIM = {"segments": SOURCE, "instructions": "Translate into Korean, preserve indices and gaps."}


class Account:
    def __init__(self):
        self.calls = 0

    def credentials(self):
        self.calls += 1
        return {"access_token": "secret-token"}


class Chunks(httpx.SyncByteStream):
    def __init__(self, chunks):
        self.chunks = chunks
        self.closed = False

    def __iter__(self):
        yield from self.chunks

    def close(self):
        self.closed = True


def event(kind, **fields):
    return ("data: " + json.dumps({"type": kind, **fields}, ensure_ascii=False) + "\n\n").encode()


def completed(result=RESULT, model="actual-model"):
    return event("response.completed", response={"status": "completed", "model": model,
        "output": [{"type": "message", "content": [{"type": "output_text", "text": json.dumps(result, ensure_ascii=False)}]}]})


def setup(chunks, status=200, **options):
    requests = []
    stream = Chunks(chunks)
    def handler(request):
        requests.append(request)
        return httpx.Response(status, headers={"x-request-id": "req_safe"}, stream=stream)
    client = httpx.Client(transport=httpx.MockTransport(handler))
    account = Account()
    worker = GPTPlanClient(account, client, **options)
    return worker, requests, stream, account


def assert_failure(worker, reason, pause=False):
    with pytest.raises(PlanInferenceError) as caught:
        worker.translate(CLAIM, "selected-model")
    error = caught.value
    assert error.reason == reason
    assert error.pause is pause
    assert "private source" not in str(error)
    assert "secret-token" not in str(error)
    return error


def test_success_and_exact_public_request():
    worker, requests, stream, account = setup([
        event("response.output_text.delta", delta="discarded partial"), completed()])
    assert worker.translate(CLAIM, "selected-model") == (RESULT, "actual-model")
    assert len(requests) == account.calls == 1
    request = requests[0]
    assert str(request.url) == RESPONSES_URL
    assert request.headers["authorization"] == "Bearer secret-token"
    body = json.loads(request.content)
    assert set(body) == {"model", "store", "stream", "instructions", "input"}
    assert body["store"] is False and body["stream"] is True
    assert body["input"][0]["role"] == "user"
    assert json.loads(body["input"][0]["content"][0]["text"]) == SOURCE
    assert all(isinstance(value, (int, float)) and value > 0 for value in request.extensions["timeout"].values())
    assert stream.closed


def test_chunk_boundaries_utf8_and_crlf_sse():
    payload = b": keepalive\r\n\r\n" + completed().replace(b"\n", b"\r\n")
    worker, *_ = setup([payload[i:i+1] for i in range(len(payload))])
    assert worker.translate(CLAIM, "selected-model")[0] == RESULT


@pytest.mark.parametrize("code", sorted(PAUSE_CODES))
def test_known_terminal_codes_pause_even_after_delta(code):
    worker, requests, stream, _ = setup([
        event("response.output_text.delta", delta=json.dumps(RESULT)),
        event("response.failed", response={"status": "failed", "error": {"code": code, "message": "secret-token private source"}})])
    error = assert_failure(worker, code, pause=True)
    assert error.request_id == "req_safe"
    assert len(requests) == 1 and stream.closed


@pytest.mark.parametrize("kind", ["response.refusal.delta", "response.refusal.done"])
def test_refusal_stops_immediately(kind):
    worker, requests, stream, _ = setup([event(kind, delta="private source"), completed()])
    assert_failure(worker, "refused")
    assert len(requests) == 1 and stream.closed


def test_refusal_inside_completion_stops():
    worker, *_ = setup([event("response.completed", response={"status": "completed", "output": [
        {"content": [{"type": "refusal", "refusal": "private source"}]}]})])
    assert_failure(worker, "refused")


@pytest.mark.parametrize("chunks", [[], [event("response.output_text.delta", delta=json.dumps(RESULT))],
    [event("response.incomplete", response={"status": "incomplete"})],
    [completed().rstrip(b"\n")]])
def test_incomplete_or_unconfirmed_output_is_never_returned(chunks):
    worker, requests, stream, _ = setup(chunks)
    assert_failure(worker, "temporary_error")
    assert len(requests) == 1 and stream.closed


@pytest.mark.parametrize("status", [401, 403, 429])
def test_pre_stream_auth_or_usage_errors_pause(status):
    worker, requests, _, _ = setup([b'{"detail":"secret-token private source"}'], status=status)
    error = assert_failure(worker, "plan_authorization_or_usage", pause=True)
    assert error.status_code == status
    assert len(requests) == 1


def test_detail_code_and_transient_unknown_messages_are_sanitized():
    worker, *_ = setup([json.dumps({"detail": {"code": "subscription_sharing_usage_unavailable", "message": "secret-token"}}).encode()], status=503)
    assert_failure(worker, "subscription_sharing_usage_unavailable", pause=True)
    worker, *_ = setup([event("error", code="private source secret-token", message="secret-token")])
    assert_failure(worker, "temporary_error")


@pytest.mark.parametrize("chunk", [event("response.output_text.delta", delta="한" * 40), completed([{ "i": 0, "text_ko": "한" * 40}]), b"data:" + b"x" * 65637])
def test_output_and_unterminated_event_bounds(chunk):
    worker, requests, stream, _ = setup([chunk], output_limit=100)
    assert_failure(worker, "output_limit")
    assert len(requests) == 1 and stream.closed


@pytest.mark.parametrize("result", [{"segments": RESULT}, [], [{"i": True, "text_ko": "x"}],
    [{"i": 0, "text_ko": None}], [{"i": 0, "text_ko": "x", "other": "private source"}], [{"i": -1, "text_ko": "x"}]])
def test_invalid_json_shapes_are_rejected(result):
    worker, *_ = setup([completed(result)])
    assert_failure(worker, "invalid_output")


def test_invalid_json_does_not_echo_model_output():
    worker, *_ = setup([event("response.output_text.delta", delta="private source secret-token"),
        event("response.completed", response={"status": "completed"})])
    assert_failure(worker, "invalid_output")


def test_actual_model_falls_back_to_selected_catalog_slug():
    worker, *_ = setup([event("response.output_text.delta", delta=json.dumps(RESULT)),
        event("response.completed", response={"status": "completed"})])
    assert worker.translate(CLAIM, "selected-model") == (RESULT, "selected-model")


def test_transport_timeout_is_bounded_and_never_retried():
    requests = []
    def handler(request):
        requests.append(request)
        raise httpx.ReadTimeout("secret-token private source", request=request)
    worker = GPTPlanClient(Account(), httpx.Client(transport=httpx.MockTransport(handler)))
    assert_failure(worker, "temporary_error")
    assert len(requests) == 1


def test_total_deadline_includes_blank_keepalives():
    ticks = iter([0, 100, 200, 301])
    worker, requests, stream, _ = setup([b"\n", b": blank\n\n", b"\n", completed()], clock=lambda: next(ticks))
    assert_failure(worker, "temporary_error")
    assert len(requests) == 1 and stream.closed


def test_plan_auth_failure_prevents_any_response_call():
    worker, requests, _, account = setup([completed()])
    def denied():
        raise PlanUnavailable("secret-token private source")
    account.credentials = denied
    assert_failure(worker, "plan_sign_in_required", pause=True)
    assert requests == []


def test_missing_model_prevents_even_permission_lookup():
    worker, requests, _, account = setup([completed()])
    with pytest.raises(PlanInferenceError, match="model_selection_required"):
        worker.translate(CLAIM, "")
    assert account.calls == 0 and requests == []


@pytest.mark.parametrize("output", [None, "private source", [None], [{"content": None}], [{"content": [None]}]])
def test_malformed_completed_envelopes_fail_safely(output):
    worker, *_ = setup([event("response.completed", response={"status": "completed", "output": output})])
    assert_failure(worker, "invalid_output")


def test_non_string_error_code_and_nested_detail_fail_safely():
    worker, *_ = setup([event("error", error={"code": {"secret-token": "private source"}})])
    assert_failure(worker, "temporary_error")
    worker, *_ = setup([json.dumps({"detail": {"error": {"code": "subscription_sharing_usage_limit_exceeded"}}}).encode()], status=429)
    assert_failure(worker, "subscription_sharing_usage_limit_exceeded", pause=True)


@pytest.mark.parametrize("segments", [[], [{"i": -1, "text": "private source"}], [{"i": 0, "text": "private source", "auxiliary": "secret-token"}], [{"i": 0, "text": "x" * 16001}]])
def test_invalid_source_does_not_start_inference(segments):
    worker, requests, *_ = setup([completed()])
    with pytest.raises(PlanInferenceError, match="invalid_source"):
        worker.translate({**CLAIM, "segments": segments}, "selected-model")
    assert requests == []
