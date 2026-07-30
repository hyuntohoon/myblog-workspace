"""Executed-SQL coverage for the research poller's Genius gate (R1/R2).

`scripts/tests/test_research_genius_facts.py` asserts the SQL *text*; this file
runs it — `FOR UPDATE SKIP LOCKED` + the correlated `NOT EXISTS` gate, the
pending/nudge selection, and the facts query — against a real engine (the Neon
test branch), because a bind or gate bug passes every text assertion and dies
on the first prod claim (the isrc lesson).

Guarded by TEST_DB_URL (GHA-only secret; skips locally). Everything runs inside
one transaction that is rolled back — claims made against stray branch rows are
undone with it, and no cleanup is needed.
"""
from __future__ import annotations

import os
import sys
import uuid
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "myblog_shared_db" / "src"))

import research_poller as rp  # noqa: E402

TEST_DB_URL = os.environ.get("TEST_DB_URL")

pytestmark = pytest.mark.skipif(
    not TEST_DB_URL,
    reason="requires TEST_DB_URL env var (Neon test branch)",
)


@pytest.fixture
def conn():
    import psycopg
    from psycopg.rows import dict_row

    c = psycopg.connect(
        TEST_DB_URL.replace("postgresql+psycopg://", "postgresql://", 1),
        connect_timeout=30,
        row_factory=dict_row,
    )
    try:
        yield c
    finally:
        c.rollback()
        c.close()


def _drain_claims(cur, *, stop_at=None, max_rounds=50):
    """Run CLAIM_SQL repeatedly, collecting claimed album ids. Stops when the
    queue is empty or `stop_at` is claimed. Claimed strays go `running` inside
    our (rolled-back) transaction, so each round makes progress."""
    claimed = []
    for _ in range(max_rounds):
        cur.execute(rp.CLAIM_SQL)
        row = cur.fetchone()
        if row is None:
            break
        claimed.append(str(row["album_id"]))
        if stop_at is not None and claimed[-1] == stop_at:
            break
    return claimed


def test_gate_holds_then_claims_then_renders(conn):
    album = str(uuid.uuid4())
    t1, t2 = str(uuid.uuid4()), str(uuid.uuid4())
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO albums (id, spotify_id, title) VALUES (%s, %s, 'Genius Gate Test')",
            (album, f"gate_test_{uuid.uuid4()}"),
        )
        for tid in (t1, t2):
            cur.execute(
                "INSERT INTO tracks (id, album_id, spotify_id, title)"
                " VALUES (%s, %s, %s, 'Gate Test Track')",
                (tid, album, f"gate_test_t_{uuid.uuid4()}"),
            )
        # t1 attempted (matched, with facts); t2 still missing → album NOT ready
        cur.execute(
            """
            INSERT INTO track_genius_songs
                   (track_id, genius_song_id, genius_url, match_status, credits, relationships)
            VALUES (%s, 1, 'https://genius.com/gate-test', 'matched',
                    '{"writers": ["W"], "producers": ["P"], "performances": []}'::jsonb,
                    '{"samples": ["A — B"]}'::jsonb)
            """,
            (t1,),
        )
        cur.execute(
            "INSERT INTO album_research (album_id, prompt_version, status)"
            " VALUES (%s, 'db-test', 'queued')",
            (album,),
        )

        # 1. Held: draining every claimable row must never yield our album.
        claimed = _drain_claims(cur)
        assert album not in claimed, "a fresh request with missing genius rows must be held"

        # 2. Nudge-eligible: the pending selection sees it (unless the branch
        #    holds NUDGE_MAX_ALBUMS older held rows, in which case the LIMIT is
        #    doing its job).
        cur.execute(rp.GENIUS_PENDING_SQL)
        pending = [str(r["album_id"]) for r in cur.fetchall()]
        assert album in pending or len(pending) == rp.NUDGE_MAX_ALBUMS

        # 3. A permanent failure COUNTS AS ATTEMPTED: parking t2 as not_found
        #    makes the album ready — match success is not the readiness bar.
        cur.execute(
            "INSERT INTO track_genius_songs (track_id, genius_song_id, match_status)"
            " VALUES (%s, 0, 'not_found')",
            (t2,),
        )
        claimed = _drain_claims(cur, stop_at=album)
        assert album in claimed, "with every track attempted, the request must claim"

        # 4. Facts derive and render from the same store.
        cur.execute(rp.GENIUS_FACTS_SQL, (album,))
        block = rp._render_genius_block(cur.fetchall())
        assert "매칭 1/2트랙" in block
        assert "P (1/1트랙 — Gate Test Track)" in block, "a few-track credit names its source track"
        assert "[확인: Genius]" in block
        # The evidence columns V49 stores for bad-match detection must survive the
        # round trip through GENIUS_FACTS_SQL, not just exist in the schema.
        assert "### 매칭 근거" in block
        assert "https://genius.com/gate-test" in block
