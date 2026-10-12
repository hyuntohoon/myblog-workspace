#!/usr/bin/env python3
"""Local-agent heartbeat writer for `automation_heartbeats` (FEAT-automation-admin 2e).

One row per agent, upserted in place with `observed_at = now()` on the DB side; the
owner page derives fresh/stale from its age (2 × schedule interval, minimum 15 min).
Writer contract (RFC "Design notes fixed for 2a–2e"):

* `agent_key` is the launchd label without `com.myblog.` (the key CHECK rejects dots).
* `last_outcome` is cut to 200 characters; `details` stays a small JSON object.
* Never credentials, tokens, member data or raw exception text — callers pass codes and
  counts, and this module logs only an exception's type.
* A failed write never fails the agent. It is logged; the row then goes stale, which the
  page shows as stale/unknown, never healthy.

Run as a script it wraps a scheduled command, for agents whose code lives in another repo:
    automation_heartbeat.py exec <agent_key> -- <command...>
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import re
import subprocess
import sys
import threading
import time

log = logging.getLogger(__name__)

LABEL_PREFIX = 'com.myblog.'
KEY = re.compile(r'^[a-z0-9][a-z0-9-]{0,63}$')
CODE = re.compile(r'^[a-z][a-z0-9_]{0,63}$')
OUTCOME_LIMIT = 200
# The CHECK caps the stored jsonb at 8 KB (pg_column_size); stay far below it in text.
DETAILS_LIMIT = 2048
CONNECT_TIMEOUT_SECONDS = 10
STATEMENT_TIMEOUT = '5s'
REGION = 'ap-northeast-2'
SSM_PARAM = '/myblog/backend'  # SecureString JSON holding DATABASE_URL, as the agents read it

UPSERT = """
INSERT INTO automation_heartbeats (agent_key, observed_at, enabled, last_outcome, details)
VALUES (%s, now(), %s, %s, %s::jsonb)
ON CONFLICT (agent_key) DO UPDATE SET observed_at = now(), enabled = EXCLUDED.enabled,
  last_outcome = EXCLUDED.last_outcome, details = EXCLUDED.details
"""


def database_url() -> str:
    """libpq URL for `exec`, which may run under a venv without the backend app."""
    url = os.environ.get('DATABASE_URL')
    if not url:
        import boto3

        ssm = boto3.client('ssm', region_name=REGION)
        url = json.loads(ssm.get_parameter(Name=SSM_PARAM, WithDecryption=True)['Parameter']['Value'])['DATABASE_URL']
    return re.sub(r'^postgresql\+\w+', 'postgresql', url)


def agent_key(label: str) -> str:
    return label[len(LABEL_PREFIX):] if label.startswith(LABEL_PREFIX) else label


def code(value) -> str:
    """A reason/outcome code, or `other` — free text never reaches the row."""
    return value if isinstance(value, str) and CODE.match(value) else 'other'


def counts_summary(counts: dict) -> str:
    """`saved 41, temporary_error 13` — largest first, codes only."""
    merged = {}
    for key, value in counts.items():
        merged[code(key)] = merged.get(code(key), 0) + int(value)
    ordered = sorted(merged.items(), key=lambda item: (-item[1], item[0]))
    return ', '.join(f'{key} {value}' for key, value in ordered) or 'nothing'


def _details_json(details) -> str:
    text = json.dumps(details or {}, separators=(',', ':'), sort_keys=True, default=str)
    if len(text.encode()) > DETAILS_LIMIT:
        log.warning('Heartbeat details over %d bytes; replaced with a marker', DETAILS_LIMIT)
        return json.dumps({'dropped': 'details_too_large'})
    return text


def write(database_url: str, key: str, *, enabled=None, last_outcome=None, details=None) -> bool:
    """Upsert one heartbeat in its own short connection. Never raises."""
    if not KEY.match(key or ''):
        log.warning('Heartbeat key rejected before write: not a short agent key')
        return False
    try:
        outcome = None if last_outcome is None else str(last_outcome)[:OUTCOME_LIMIT]
        payload = _details_json(details if isinstance(details, dict) else {})
        import psycopg

        with psycopg.connect(database_url, connect_timeout=CONNECT_TIMEOUT_SECONDS) as conn:
            with conn.transaction():
                # A pooled session can carry a leaked read-only default (Neon -pooler).
                conn.execute('SET TRANSACTION READ WRITE')
                conn.execute(f"SET LOCAL statement_timeout = '{STATEMENT_TIMEOUT}'")
                conn.execute(UPSERT, (key, enabled, outcome, payload))
        return True
    except Exception as error:  # noqa: BLE001 — a heartbeat never fails the agent
        # Driver exception text can echo the DSN; log the type only.
        log.warning('Heartbeat write failed for %s (%s)', key, type(error).__name__)
        return False


class Heartbeat:
    """Throttled writer for a long run. `build` returns the row fields and is called only
    when a write happens; nothing here raises into the agent."""

    def __init__(self, database_url: str, key: str, interval_seconds: float = 120,
                 clock=time.monotonic, writer=write):
        self.database_url, self.key, self.interval = database_url, key, interval_seconds
        self.clock, self.writer = clock, writer
        self._lock = threading.Lock()
        # The window opens at construction: a short run writes only its `force` at the end.
        self._last = clock()

    def maybe(self, build) -> bool:
        """Write at most once per interval; a sibling thread already writing is enough."""
        if not self._lock.acquire(blocking=False):
            return False
        try:
            now = self.clock()
            if now - self._last < self.interval:
                return False
            self._last = now
            return self._write(build)
        finally:
            self._lock.release()

    def force(self, build) -> bool:
        with self._lock:
            self._last = self.clock()
            return self._write(build)

    def _write(self, build) -> bool:
        try:
            fields = build()
        except Exception as error:  # noqa: BLE001
            log.warning('Heartbeat fields unavailable for %s (%s)', self.key, type(error).__name__)
            return False
        return self.writer(self.database_url, self.key, **fields)


def record(database_url_fn, key: str, last_outcome: str, details=None) -> bool:
    """One write for an agent that runs once per start. Never raises."""
    try:
        url = database_url_fn()
    except Exception as error:  # noqa: BLE001
        log.warning('Heartbeat database URL unavailable (%s)', type(error).__name__)
        return False
    return write(url, key, enabled=True, last_outcome=last_outcome, details=details)


def _exit_outcome(code_) -> str:
    # sys.exit('message') carries text; only an integer status reaches the row.
    if code_ in (None, 0):
        return 'ok'
    return f'exit {code_}' if isinstance(code_, int) else 'exit nonzero'


def run_and_record(database_url_fn, key: str, fn):
    """Call an agent's entry point, then record how it ended; its result or error wins."""
    started = time.time()
    outcome = 'error'
    try:
        result = fn()
        outcome = _exit_outcome(result)
        return result
    except SystemExit as stop:
        outcome = _exit_outcome(stop.code)
        raise
    except BaseException as error:
        outcome = f'error {type(error).__name__}'
        raise
    finally:
        record(database_url_fn, key, outcome, {'duration_seconds': round(time.time() - started)})


def exec_command(database_url_fn, key: str, command: list) -> int:
    """Run a scheduled command and record its exit code; the command's own result wins."""
    started = time.time()
    try:
        returncode = subprocess.run(command).returncode
    except OSError as error:
        log.error('Heartbeat exec could not start the command (%s)', type(error).__name__)
        returncode = 127
    record(database_url_fn, key, 'ok' if returncode == 0 else f'exit {returncode}',
           {'exit_code': returncode, 'duration_seconds': round(time.time() - started)})
    return returncode


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='action', required=True)
    run = sub.add_parser('exec', help='run a command, then record its exit code')
    run.add_argument('agent_key')
    run.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    command = args.command[1:] if args.command[:1] == ['--'] else args.command
    if not command or not KEY.match(args.agent_key):
        parser.error('exec needs a short agent key and a command after --')
    return exec_command(database_url, args.agent_key, command)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    sys.exit(main())
