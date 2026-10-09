"""One bounded Responses stream using dedicated ChatGPT-plan permission.

There are no transport retries or alternative credentials. Partial streamed text
is never returned: a successful response.completed event is required first.
The total deadline is checked on every stream chunk, including keepalives;
a stalled read can extend it by at most the explicit 30-second read timeout.
"""
from __future__ import annotations

import json
import re
import time
from collections.abc import Callable, Iterator

import httpx

from scripts.gpt_plan_auth import PlanAccount, PlanUnavailable

RESPONSES_URL = "https://api.openai.com/v1/responses"
OUTPUT_LIMIT = 262144
DEADLINE_SECONDS = 300
PAUSE_CODES = frozenset({
    "subscription_sharing_user_not_eligible", "subscription_sharing_usage_limit_exceeded",
    "subscription_sharing_usage_unavailable", "subscription_sharing_unsupported_capability",
    "subscription_sharing_route_not_supported", "subscription_sharing_invalid_user",
    "chatpass_v2_scope_not_authorized", "chatpass_v2_invalid_authorization_context",
})


class PlanInferenceError(RuntimeError):
    """Safe failure metadata; never retains a provider message or request body."""

    def __init__(self, reason: str, *, pause: bool = False, status_code: int | None = None,
                 request_id: str | None = None):
        self.reason = reason
        self.pause = pause
        self.status_code = status_code
        # Headers are untrusted too. Keep only the opaque identifier syntax.
        self.request_id = request_id if isinstance(request_id, str) and re.fullmatch(r"[A-Za-z0-9_-]{1,128}", request_id) else None
        super().__init__(reason)


def _failure(payload, status=None, request_id=None):
    """Classify known codes, without exposing arbitrary error text or codes."""
    value = payload if isinstance(payload, dict) else {}
    for _ in range(3):
        nested = next((value[key] for key in ("response", "error", "detail")
                       if isinstance(value.get(key), dict)), None)
        if nested is None:
            break
        value = nested
    code = value.get("code")
    if isinstance(code, str) and code in PAUSE_CODES:
        return PlanInferenceError(code, pause=True, status_code=status, request_id=request_id)
    if status in (401, 403, 429):
        return PlanInferenceError("plan_authorization_or_usage", pause=True, status_code=status, request_id=request_id)
    if status is not None and 400 <= status < 500 and status != 408:
        return PlanInferenceError("plan_request_rejected", pause=True, status_code=status, request_id=request_id)
    return PlanInferenceError("temporary_error", status_code=status, request_id=request_id)


def _shape(value):
    if not isinstance(value, list) or not value or len(value) > 300:
        raise PlanInferenceError("invalid_output")
    for segment in value:
        if (not isinstance(segment, dict) or set(segment) != {"i", "text_ko"}
                or type(segment["i"]) is not int or segment["i"] < 0
                or not isinstance(segment["text_ko"], str)):
            raise PlanInferenceError("invalid_output")
    return value


class GPTPlanClient:
    def __init__(self, account: PlanAccount, client=None, *, deadline_seconds=DEADLINE_SECONDS,
                 output_limit=OUTPUT_LIMIT, clock: Callable[[], float] = time.monotonic):
        if deadline_seconds <= 0 or output_limit <= 0:
            raise ValueError("Stream limits must be positive")
        self.account = account
        self.client = client or httpx.Client(
            timeout=httpx.Timeout(connect=15, read=30, write=15, pool=5),
            transport=httpx.HTTPTransport(retries=0), follow_redirects=False)
        self.deadline_seconds = deadline_seconds
        self.output_limit = output_limit
        self.clock = clock

    def _check_deadline(self, deadline):
        if self.clock() >= deadline:
            raise PlanInferenceError("temporary_error")

    def _events(self, response, deadline) -> Iterator[dict]:
        """Parse SSE before decoding, bounding even unterminated event lines."""
        pending = bytearray()
        data = []
        event_size = 0
        received = 0
        for chunk in response.iter_bytes():
            self._check_deadline(deadline)  # Includes blank/comment keepalive chunks.
            received += len(chunk)
            if received > max(self.output_limit * 4, 65536):
                raise PlanInferenceError("output_limit")
            pending.extend(chunk)
            while b"\n" in pending:
                raw, _, remainder = pending.partition(b"\n")
                pending = bytearray(remainder)
                raw = raw.rstrip(b"\r")
                if not raw:
                    if data:
                        try:
                            value = json.loads(b"\n".join(data))
                        except (UnicodeDecodeError, ValueError):
                            raise PlanInferenceError("invalid_output") from None
                        if not isinstance(value, dict):
                            raise PlanInferenceError("invalid_output")
                        yield value
                    data = []
                    event_size = 0
                elif raw.startswith(b"data:"):
                    part = raw[5:].lstrip(b" ")
                    event_size += len(part)
                    if event_size > self.output_limit + 65536:
                        raise PlanInferenceError("output_limit")
                    data.append(part)
            if len(pending) > self.output_limit + 65536:
                raise PlanInferenceError("output_limit")
        self._check_deadline(deadline)
        # An unterminated final event is not sufficient confirmation.

    def translate(self, claim, model):
        if not isinstance(model, str) or not model.strip():
            raise PlanInferenceError("model_selection_required", pause=True)
        try:
            credentials = self.account.credentials()
        except (PlanUnavailable, httpx.HTTPError, ValueError, KeyError):
            raise PlanInferenceError("plan_sign_in_required", pause=True) from None
        token = credentials.get("access_token") if isinstance(credentials, dict) else None
        if not isinstance(token, str) or not token:
            raise PlanInferenceError("plan_sign_in_required", pause=True)
        source = claim.get("segments")
        if not isinstance(source, list) or not source or len(source) > 300:
            raise PlanInferenceError("invalid_source")
        if any(not isinstance(s, dict) or set(s) != {"i", "text"}
               or type(s.get("i")) is not int or s["i"] < 0
               or not isinstance(s.get("text"), str) for s in source):
            raise PlanInferenceError("invalid_source")
        if sum(len(s["text"]) for s in source) > 16000:
            raise PlanInferenceError("invalid_source")
        instructions = claim.get("instructions")
        if not isinstance(instructions, str) or not instructions:
            raise PlanInferenceError("invalid_source")
        body = {"model": model, "store": False, "stream": True,
                "instructions": instructions + " Return only a JSON array of {i,text_ko} objects; no Markdown fences or explanation.",
                "input": [{"role": "user", "content": [{"type": "input_text", "text": json.dumps(source, ensure_ascii=False)}]}]}
        deadline = self.clock() + self.deadline_seconds
        output = []
        output_size = 0
        try:
            # Per-operation timeout also bounds a stalled read with no keepalives.
            timeout = httpx.Timeout(connect=min(15, self.deadline_seconds),
                                    read=min(30, self.deadline_seconds),
                                    write=min(15, self.deadline_seconds), pool=min(5, self.deadline_seconds))
            with self.client.stream("POST", RESPONSES_URL, headers={"Authorization": "Bearer " + token,
                    "Accept": "text/event-stream"}, json=body, timeout=timeout, follow_redirects=False) as response:
                request_id = response.headers.get("x-request-id")
                if response.status_code != 200:
                    # Read a bounded diagnostic body, only to classify known codes.
                    error_bytes = bytearray()
                    for chunk in response.iter_bytes():
                        self._check_deadline(deadline)
                        error_bytes.extend(chunk[:65536 - len(error_bytes)])
                        if len(error_bytes) >= 65536:
                            break
                    try:
                        error = json.loads(error_bytes)
                    except (ValueError, UnicodeDecodeError):
                        error = {}
                    raise _failure(error, response.status_code, request_id)
                for event in self._events(response, deadline):
                    kind = event.get("type")
                    if kind in ("response.refusal.delta", "response.refusal.done"):
                        raise PlanInferenceError("refused", request_id=request_id)
                    if kind in ("response.failed", "error"):
                        raise _failure(event, request_id=request_id)
                    if kind == "response.incomplete":
                        raise PlanInferenceError("temporary_error", request_id=request_id)
                    if kind == "response.output_text.delta":
                        delta = event.get("delta")
                        if not isinstance(delta, str):
                            raise PlanInferenceError("invalid_output")
                        output_size += len(delta.encode("utf-8"))
                        if output_size > self.output_limit:
                            raise PlanInferenceError("output_limit")
                        output.append(delta)
                    elif kind == "response.completed":
                        completed = event.get("response")
                        if not isinstance(completed, dict) or completed.get("status") != "completed":
                            raise PlanInferenceError("temporary_error")
                        texts = []
                        items = completed.get("output", [])
                        if not isinstance(items, list):
                            raise PlanInferenceError("invalid_output")
                        for item in items:
                            if not isinstance(item, dict):
                                raise PlanInferenceError("invalid_output")
                            contents = item.get("content", [])
                            if not isinstance(contents, list):
                                raise PlanInferenceError("invalid_output")
                            for content in contents:
                                if not isinstance(content, dict):
                                    raise PlanInferenceError("invalid_output")
                                if content.get("type") == "refusal":
                                    raise PlanInferenceError("refused", request_id=request_id)
                                if content.get("type") == "output_text":
                                    text = content.get("text")
                                    if not isinstance(text, str):
                                        raise PlanInferenceError("invalid_output")
                                    texts.append(text)
                        text = "".join(texts if texts else output)
                        if len(text.encode("utf-8")) > self.output_limit:
                            raise PlanInferenceError("output_limit")
                        try:
                            segments = _shape(json.loads(text))
                        except (ValueError, UnicodeDecodeError):
                            raise PlanInferenceError("invalid_output") from None
                        actual_model = completed.get("model", model)
                        if not isinstance(actual_model, str) or not actual_model.strip() or len(actual_model) > 200:
                            raise PlanInferenceError("invalid_output")
                        return segments, actual_model
        except (httpx.HTTPError, UnicodeEncodeError):
            raise PlanInferenceError("temporary_error") from None
        raise PlanInferenceError("temporary_error")
