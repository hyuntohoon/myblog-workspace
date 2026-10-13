"""automation_heartbeats writer (FEAT-automation-admin 2e): contract, throttle, failure isolation.

DB cases run against TEST_DB_URL with a unique agent key each and delete their own row.
"""
import json
import os
import re
import sys
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import pytest

from scripts import automation_heartbeat as hb

TEST_DB_URL = os.environ.get('TEST_DB_URL')
db = pytest.mark.skipif(not TEST_DB_URL, reason='TEST_DB_URL not set')


def libpq(url):
    return re.sub(r'^postgresql\+\w+', 'postgresql', url)


@pytest.fixture
def key():
    value = 'test-hb-' + uuid4().hex[:12]
    yield value
    if TEST_DB_URL:
        import psycopg

        with psycopg.connect(libpq(TEST_DB_URL), connect_timeout=30) as conn:
            conn.execute('DELETE FROM automation_heartbeats WHERE agent_key=%s', (value,))


def row(key):
    import psycopg

    with psycopg.connect(libpq(TEST_DB_URL), connect_timeout=30) as conn:
        return conn.execute("""SELECT enabled, last_outcome, details,
            extract(epoch FROM now() - observed_at) FROM automation_heartbeats WHERE agent_key=%s""",
                            (key,)).fetchone()


def test_agent_key_strips_the_launchd_prefix():
    assert hb.agent_key('com.myblog.gpt-translate-poller') == 'gpt-translate-poller'
    assert hb.KEY.match(hb.agent_key('com.myblog.buckit-nightly'))
    assert not hb.KEY.match('com.myblog.buckit-nightly')


def test_codes_never_carry_free_text():
    assert hb.code('temporary_error') == 'temporary_error'
    assert hb.code('connection to server at "host" failed') == 'other'
    assert hb.code(None) == 'other'
    assert hb.counts_summary({'saved': 2, 'temporary_error': 5, 'Bad text!': 1, 'x y': 1}) == \
        'temporary_error 5, other 2, saved 2'
    assert hb.counts_summary({}) == 'nothing'


@db
def test_write_upserts_one_row_with_db_time(key):
    url = libpq(TEST_DB_URL)
    assert hb.write(url, key, enabled=True, last_outcome='x' * 500, details={'outcomes': {'saved': 1}})
    enabled, outcome, details, age = row(key)
    assert enabled is True and outcome == 'x' * 200
    assert details == {'outcomes': {'saved': 1}}
    assert 0 <= age < 60
    assert hb.write(url, key, enabled=False, last_outcome='stopped')
    assert row(key)[:3] == (False, 'stopped', {})


@db
def test_oversized_details_are_replaced_not_rejected(key):
    assert hb.write(libpq(TEST_DB_URL), key, details={'blob': 'a' * 10000})
    assert row(key)[2] == {'dropped': 'details_too_large'}


@db
def test_rejected_key_and_dead_db_never_raise(key, caplog):
    assert hb.write(libpq(TEST_DB_URL), 'com.myblog.' + key) is False
    assert row(key) is None
    dsn = 'postgresql://user:hunter2-secret@127.0.0.1:1/none'
    assert hb.write(dsn, key, last_outcome='x') is False
    assert 'hunter2-secret' not in caplog.text


class FakeClock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


def test_heartbeat_throttles_maybe_but_not_force():
    clock, writes = FakeClock(), []
    beat = hb.Heartbeat('url', 'k', 120, clock=clock, writer=lambda url, key, **f: writes.append(f) or True)
    assert beat.maybe(lambda: {'last_outcome': 'a'}) is False  # window opens at construction
    clock.now += 119
    assert beat.maybe(lambda: {'last_outcome': 'b'}) is False
    clock.now += 1
    assert beat.maybe(lambda: {'last_outcome': 'c'}) is True
    assert beat.force(lambda: {'last_outcome': 'd'}) is True
    clock.now += 60
    assert beat.maybe(lambda: {'last_outcome': 'e'}) is False  # force restarted the window
    assert [w['last_outcome'] for w in writes] == ['c', 'd']


def test_heartbeat_swallows_a_failing_field_builder():
    clock = FakeClock()
    beat = hb.Heartbeat('url', 'k', 0, clock=clock, writer=lambda *a, **f: pytest.fail('no write'))

    def broken():
        raise OSError('disk full at /secret/path')

    clock.now += 1
    assert beat.maybe(broken) is False
    assert beat.force(broken) is False


def recorder():
    writes = []
    return writes, (lambda url, key, **fields: writes.append((key, fields)) or True)


@pytest.mark.parametrize('result, outcome', [(None, 'ok'), (0, 'ok'), (2, 'exit 2')])
def test_run_and_record_returns_the_entry_point_result(monkeypatch, result, outcome):
    writes, writer = recorder()
    monkeypatch.setattr(hb, 'write', writer)
    assert hb.run_and_record(lambda: 'url', 'agent', lambda: result) == result
    assert writes[0][0] == 'agent' and writes[0][1]['last_outcome'] == outcome


@pytest.mark.parametrize('error, outcome', [
    (SystemExit(4), 'exit 4'),
    (SystemExit('STOP: rules missing at /Users/x'), 'exit nonzero'),
    (ValueError('password=hunter2'), 'error ValueError'),
])
def test_run_and_record_reraises_and_records_no_text(monkeypatch, error, outcome):
    writes, writer = recorder()
    monkeypatch.setattr(hb, 'write', writer)

    def entry():
        raise error

    with pytest.raises(type(error)):
        hb.run_and_record(lambda: 'url', 'agent', entry)
    assert writes[0][1]['last_outcome'] == outcome
    assert 'hunter2' not in json.dumps(writes)


def test_unavailable_url_does_not_change_the_agent_result(monkeypatch):
    monkeypatch.setattr(hb, 'write', lambda *a, **f: pytest.fail('no URL, no write'))

    def no_url():
        raise RuntimeError('ssm down')

    assert hb.run_and_record(no_url, 'agent', lambda: 3) == 3


@db
def test_exec_records_the_command_exit_code(key):
    code = hb.exec_command(lambda: libpq(TEST_DB_URL), key, [sys.executable, '-c', 'raise SystemExit(3)'])
    assert code == 3
    enabled, outcome, details, _ = row(key)
    assert outcome == 'exit 3' and details['exit_code'] == 3 and enabled is True


def test_failed_write_logs_the_exception_type_only(monkeypatch, caplog):
    import psycopg

    def leaky(*args, **kwargs):
        raise psycopg.OperationalError('connection to postgresql://u:hunter2-secret@h failed')

    monkeypatch.setattr(psycopg, 'connect', leaky)
    assert hb.write('postgresql://u:hunter2-secret@h/db', 'agent', last_outcome='x') is False
    assert 'OperationalError' in caplog.text and 'hunter2-secret' not in caplog.text


@db
def test_write_survives_a_session_with_a_read_only_default(key):
    # A pooled session can carry a leaked default_transaction_read_only (Neon -pooler).
    sep = '&' if '?' in TEST_DB_URL else '?'
    read_only = libpq(TEST_DB_URL) + sep + 'options=-c%20default_transaction_read_only%3Don'
    assert hb.write(read_only, key, last_outcome='written')
    assert row(key)[1] == 'written'
