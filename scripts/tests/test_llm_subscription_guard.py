from __future__ import annotations

import multiprocessing
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "myblog_shared_db" / "src"))

from myblog_shared_db.llm.subscription_guard import (  # noqa: E402
    LLMSubscriptionCooldown,
    coordinated_call,
)
from myblog_shared_db.llm import LLMTransientError  # noqa: E402


def test_calls_are_serialized_across_threads(tmp_path: Path) -> None:
    active = 0
    max_active = 0
    state_lock = threading.Lock()

    def operation() -> str:
        nonlocal active, max_active
        with state_lock:
            active += 1
            max_active = max(max_active, active)
        time.sleep(0.04)
        with state_lock:
            active -= 1
        return "ok"

    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(
            lambda _: coordinated_call(
                operation,
                feature="test",
                state_dir=tmp_path,
                min_gap_s=0,
            ),
            range(4),
        ))

    assert results == ["ok"] * 4
    assert max_active == 1


def _exit_while_holding_slot(state_dir: str, ready) -> None:
    def exit_now() -> None:
        ready.send(True)
        ready.close()
        os._exit(23)

    coordinated_call(
        exit_now,
        feature="crash-test",
        state_dir=Path(state_dir),
        min_gap_s=0,
    )


def test_process_exit_releases_lock(tmp_path: Path) -> None:
    ctx = multiprocessing.get_context("fork")
    parent, child = ctx.Pipe(duplex=False)
    proc = ctx.Process(target=_exit_while_holding_slot, args=(str(tmp_path), child))
    proc.start()
    assert parent.recv() is True
    proc.join(timeout=3)
    assert proc.exitcode == 23

    assert coordinated_call(
        lambda: "acquired",
        feature="after-crash",
        state_dir=tmp_path,
        min_gap_s=0,
    ) == "acquired"


def test_throttle_sets_shared_cooldown_without_second_call(tmp_path: Path) -> None:
    calls = 0

    def throttled() -> None:
        raise LLMTransientError("claude exit 1: 429 rate limit reached")

    with pytest.raises(LLMTransientError, match="429"):
        coordinated_call(
            throttled,
            feature="first",
            state_dir=tmp_path,
            min_gap_s=0,
            cooldown_s=60,
        )

    def must_not_run() -> None:
        nonlocal calls
        calls += 1

    with pytest.raises(LLMSubscriptionCooldown, match="cooldown active"):
        coordinated_call(
            must_not_run,
            feature="second",
            state_dir=tmp_path,
            min_gap_s=0,
        )
    assert calls == 0


def test_observed_blank_claude_exit_sets_cooldown(tmp_path: Path) -> None:
    def silent_exit() -> None:
        raise LLMTransientError("claude exit 1: ")

    with pytest.raises(LLMTransientError, match="claude exit 1"):
        coordinated_call(
            silent_exit,
            feature="observed-live-throttle",
            state_dir=tmp_path,
            min_gap_s=0,
            cooldown_s=60,
        )

    with pytest.raises(LLMSubscriptionCooldown):
        coordinated_call(
            lambda: None,
            feature="next-worker",
            state_dir=tmp_path,
            min_gap_s=0,
        )


def test_non_throttle_transient_does_not_set_cooldown(tmp_path: Path) -> None:
    def connection_reset() -> None:
        raise LLMTransientError("connection reset by peer")

    with pytest.raises(LLMTransientError, match="connection reset"):
        coordinated_call(
            connection_reset,
            feature="first",
            state_dir=tmp_path,
            min_gap_s=0,
        )

    assert coordinated_call(
        lambda: "retried",
        feature="second",
        state_dir=tmp_path,
        min_gap_s=0,
    ) == "retried"


def test_genius_stops_remaining_chunks_after_first_transient(monkeypatch) -> None:
    import genius_translate_poller as genius

    class DummyConn:
        closed = False

        def close(self) -> None:
            self.closed = True

    calls = 0
    connections: list[DummyConn] = []

    def connect() -> DummyConn:
        conn = DummyConn()
        connections.append(conn)
        return conn

    monkeypatch.setattr(genius, "connect", connect)
    monkeypatch.setattr(genius, "ensure_subscription_available", lambda: None)
    monkeypatch.setattr(genius, "claim", lambda _conn, _limit: [{"id": 1}])
    monkeypatch.setattr(genius, "_chunks", lambda _rows: [[1], [2], [3], [4]])

    def transient(_chunk):
        nonlocal calls
        assert connections and all(conn.closed for conn in connections)
        calls += 1
        return [], [], True

    monkeypatch.setattr(genius, "_do_chunk", transient)

    metrics = genius.run_batch(24)
    assert calls == 1
    assert metrics == {"claimed": 1, "done": 0, "failed": 0, "transient": 1}


def test_lyrics_closes_read_connection_before_model_wait(monkeypatch) -> None:
    import lyrics_translate_poller as lyrics
    from types import SimpleNamespace

    class Cursor:
        def __init__(self, conn) -> None:
            self.conn = conn

        def __enter__(self):
            return self

        def __exit__(self, *_args) -> None:
            pass

        def execute(self, sql, _params=None) -> None:
            self.conn.last_sql = sql

        def fetchone(self):
            if "UPDATE track_lyrics_translations" in self.conn.last_sql:
                return {"track_id": "track-1", "lang": "ko"}
            return {
                "match_status": "matched",
                "lyric_plain": "hello",
                "lyric_synced": None,
                "title": "Song",
                "artists": ["Artist"],
            }

    class ReadConn:
        closed = False
        last_sql = ""

        def cursor(self):
            return Cursor(self)

        def commit(self) -> None:
            pass

        def close(self) -> None:
            self.closed = True

    read_conn = ReadConn()
    monkeypatch.setattr(lyrics, "ensure_subscription_available", lambda: None)
    monkeypatch.setattr(lyrics, "connect", lambda: read_conn)
    monkeypatch.setattr(
        lyrics,
        "normalize_lyrics",
        lambda _row: SimpleNamespace(
            availability="ok",
            segments=[SimpleNamespace(i=0, text="hello")],
            normalizer_version="v1",
        ),
    )

    def translate(_lines):
        assert read_conn.closed
        raise LLMSubscriptionCooldown(30)

    monkeypatch.setattr(lyrics, "claude_translate", translate)
    with pytest.raises(LLMSubscriptionCooldown):
        lyrics.process_one()


def test_research_closes_read_connection_before_model_wait(monkeypatch) -> None:
    import research_poller as research

    class Cursor:
        def __enter__(self):
            return self

        def __exit__(self, *_args) -> None:
            pass

        def execute(self, _sql, _params=None) -> None:
            pass

        def fetchall(self):
            return []  # nudge sees no waiting albums; facts block renders 0/0

    class ReadConn:
        closed = False

        def cursor(self):
            return Cursor()

        def commit(self) -> None:
            pass

        def close(self) -> None:
            self.closed = True

    read_conn = ReadConn()
    monkeypatch.setattr(research, "ensure_subscription_available", lambda: None)
    monkeypatch.setattr(research, "connect", lambda: read_conn)
    monkeypatch.setattr(research, "claim_row", lambda _conn: {
        "id": "row-1",
        "album_id": "album-1",
        "prompt_version": research.PROMPT_VERSION,
        "result_md": None,
        "last_instruction": None,
    })
    monkeypatch.setattr(research, "album_meta", lambda _conn, _album_id: {
        "title": "Album",
        "artists": ["Artist"],
        "release_date": None,
        "label": None,
        "spotify_id": None,
        "album_type": "album",
        "total_tracks": 1,
    })

    def run(_prompt):
        assert read_conn.closed
        raise LLMSubscriptionCooldown(30)

    monkeypatch.setattr(research, "run_claude", run)
    with pytest.raises(LLMSubscriptionCooldown):
        research.process_one("base")


@pytest.mark.parametrize(
    "relative_path",
    [
        "scripts/genius_translate_poller.py",
        "scripts/lyrics_translate_poller.py",
        "scripts/research_poller.py",
        "scripts/buckit_nightly.py",
        "scripts/editor_buckit.py",
        "myblog_shared_db/scripts/backfill_genres.py",
    ],
)
def test_subscription_call_sites_use_shared_guard(relative_path: str) -> None:
    source = (ROOT / relative_path).read_text(encoding="utf-8")
    assert "llm.subscription_guard import" in source
    assert "coordinated_run(" in source


def test_buckit_cooldown_does_not_spend_retry_budget(monkeypatch) -> None:
    import buckit_nightly as buckit

    calls = 0
    sleeps: list[float] = []

    def run(_prompt: str) -> dict:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise LLMSubscriptionCooldown(7)
        return {"result": "ok"}

    monkeypatch.setattr(buckit, "run_claude", run)
    monkeypatch.setattr(buckit.time, "sleep", sleeps.append)

    assert buckit.run_claude_with_retry("prompt") == {"result": "ok"}
    assert calls == 2
    assert sleeps == [7]


def test_lyrics_cooldown_stops_current_firing(monkeypatch) -> None:
    import lyrics_translate_poller as lyrics

    class DummyConn:
        def close(self) -> None:
            pass

    calls = 0

    def process_one() -> bool:
        nonlocal calls
        calls += 1
        raise LLMSubscriptionCooldown(30)

    monkeypatch.setattr(lyrics, "connect", DummyConn)
    monkeypatch.setattr(lyrics, "sweep", lambda _conn: None)
    monkeypatch.setattr(lyrics, "process_one", process_one)
    monkeypatch.setattr(sys, "argv", ["lyrics_translate_poller.py"])

    assert lyrics.main() == 0
    assert calls == 1


@pytest.mark.parametrize("module_name", ["lyrics_translate_poller", "research_poller"])
def test_cooldown_preflight_happens_before_queue_claim(monkeypatch, module_name: str) -> None:
    module = __import__(module_name)
    monkeypatch.setattr(
        module,
        "ensure_subscription_available",
        lambda: (_ for _ in ()).throw(LLMSubscriptionCooldown(30)),
    )
    monkeypatch.setattr(
        module,
        "connect",
        lambda: pytest.fail("DB queue must not be touched during a known cooldown"),
    )

    with pytest.raises(LLMSubscriptionCooldown):
        if module_name == "lyrics_translate_poller":
            module.process_one()
        else:
            module.process_one("base prompt")


def test_lyrics_source_lookup_failure_is_closed_on_the_claimed_row(monkeypatch) -> None:
    import lyrics_translate_poller as lyrics

    class Cursor:
        def __init__(self, conn) -> None:
            self.conn = conn

        def __enter__(self):
            return self

        def __exit__(self, *_args) -> None:
            pass

        def execute(self, sql, _params=None) -> None:
            if "FROM tracks t" in sql:
                raise RuntimeError("source read failed")
            self.conn.last_sql = sql

        def fetchone(self):
            return {"track_id": "track-1", "lang": "ko"}

    class ReadConn:
        last_sql = ""
        closed = False

        def cursor(self):
            return Cursor(self)

        def commit(self) -> None:
            pass

        def close(self) -> None:
            self.closed = True

    failed: list[tuple[str, str]] = []
    read_conn = ReadConn()
    monkeypatch.setattr(lyrics, "ensure_subscription_available", lambda: None)
    monkeypatch.setattr(lyrics, "connect", lambda: read_conn)
    monkeypatch.setattr(
        lyrics,
        "_mark_failed_fresh",
        lambda track_id, error: failed.append((track_id, error)),
    )

    assert lyrics.process_one() is True
    assert read_conn.closed
    assert failed == [("track-1", "source read failed")]


def test_genre_heal_cooldown_does_not_claim_request(monkeypatch) -> None:
    import genre_heal_poller as genre

    monkeypatch.delenv("GENRE_HEAL_LLM", raising=False)
    monkeypatch.setattr(
        genre,
        "ensure_subscription_available",
        lambda: (_ for _ in ()).throw(LLMSubscriptionCooldown(30)),
    )
    monkeypatch.setattr(
        genre,
        "_db_url",
        lambda: pytest.fail("DB queue must not be touched during a known cooldown"),
    )

    assert genre.run_once() == 0


@pytest.mark.parametrize(
    ("return_code", "expected_sql"),
    [(0, "SET finished_at = now()"), (75, "SET claimed_at = NULL, finished_at = NULL")],
)
def test_genre_heal_only_finishes_successful_backfill(
    monkeypatch, return_code: int, expected_sql: str
) -> None:
    import genre_heal_poller as genre

    executed: list[str] = []
    connections = 0

    class Cursor:
        def __enter__(self):
            return self

        def __exit__(self, *_args) -> None:
            pass

        def execute(self, sql, _params=None) -> None:
            executed.append(" ".join(sql.split()))

        def fetchone(self):
            return (7,)

    class Conn:
        def __enter__(self):
            return self

        def __exit__(self, *_args) -> None:
            pass

        def cursor(self):
            return Cursor()

        def commit(self) -> None:
            pass

    def connect(_url):
        nonlocal connections
        connections += 1
        return Conn()

    monkeypatch.delenv("GENRE_HEAL_LLM", raising=False)
    monkeypatch.setattr(genre, "ensure_subscription_available", lambda: None)
    monkeypatch.setattr(genre, "_db_url", lambda: "postgresql://test")
    monkeypatch.setattr(genre, "_run_backfill", lambda: return_code)
    monkeypatch.setattr(genre.psycopg, "connect", connect)

    assert genre.run_once() == return_code
    assert connections == 2
    assert expected_sql in executed[-1]
