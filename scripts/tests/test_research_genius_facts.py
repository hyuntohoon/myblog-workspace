"""FEAT-lyrics-annotations R1/R2/R4 — research-driven Genius facts.

What these pin:

  * the claim gate holds a fresh request until every album track has a
    track_genius_songs row, with GENIUS_WAIT_MAX as the partial escape hatch —
    and permanent match failures (not_found/ambiguous rows) count as attempted
  * the facts block derives album-level facts from MATCHED rows only (a wrong
    song's credits must not enter a note), distinguishes confirmed absence from
    "could not check", and degrades explicitly at zero matches
  * the block reaches the prompt (R2) with its [확인: Genius] provenance (R4)
  * the SQS nudge is fail-open — a nudge failure must never fail research, and
    a failed nudge SELECT must not poison the claim that follows it
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "myblog_shared_db" / "src"))

import research_poller as rp  # noqa: E402


def _row(title, status, *, credits=None, rels=None, url=None, fetched=None):
    return {
        "title": title,
        "track_no": 1,
        "match_status": status,
        "match_confidence": 0.9 if status == "matched" else None,
        "genius_url": url,
        "credits": credits,
        "relationships": rels,
        "fetched_at": fetched,
    }


FETCHED = datetime(2026, 7, 29, 1, 0, tzinfo=timezone.utc)


# ── the claim gate ──────────────────────────────────────────────────────────

def test_claim_gate_waits_on_missing_genius_rows_with_partial_escape():
    sql = rp.CLAIM_SQL
    assert "track_genius_songs" in sql, "the readiness gate is gone"
    assert rp.GENIUS_WAIT_MAX in sql, "no partial escape hatch — a dead token starves research"
    # Attempted-not-matched rows must satisfy the gate: the readiness predicate
    # keys on row EXISTENCE (g.track_id IS NULL), never on match_status.
    gate = sql[sql.index("NOT EXISTS"):]
    assert "g.track_id IS NULL" in gate
    assert "match_status" not in gate, "readiness must not require matched — not_found is attempted"


def test_pending_sql_mirrors_the_gate_within_the_wait_window():
    sql = rp.GENIUS_PENDING_SQL
    assert "track_genius_songs" in sql
    assert rp.GENIUS_WAIT_MAX in sql
    assert f"LIMIT {rp.NUDGE_MAX_ALBUMS}" in sql


# ── the facts block (R1 derive) ─────────────────────────────────────────────

def test_facts_come_from_matched_rows_only():
    rows = [
        _row("Good", "matched",
             credits={"writers": ["W"], "producers": ["P"], "performances": []},
             rels={"samples": ["X — Y"]}, url="https://genius.com/good", fetched=FETCHED),
        _row("Wrong Song", "ambiguous",
             credits={"writers": ["EVIL"], "producers": ["EVIL"], "performances": []},
             rels={"samples": ["EVIL — EVIL"]}),
    ]
    block = rp._render_genius_block(rows)
    assert "P (1/1트랙)" in block and "W (1/1트랙)" in block
    assert "EVIL" not in block, "an ambiguous match may be a different song entirely"
    assert "매칭 1/2트랙" in block


def test_confirmed_absence_is_distinct_from_unchecked():
    rows = [
        _row("A", "matched", credits={}, rels={}, fetched=FETCHED),
        _row("B", "not_found"),
        _row("C", None),
    ]
    block = rp._render_genius_block(rows)
    assert "관계 없음(확인): 1/1트랙" in block, "matched + no relationships = confirmed absence"
    assert "미등재 1" in block and "미조회 1" in block


def test_zero_matches_degrades_explicitly_and_bans_the_tier():
    block = rp._render_genius_block([_row("A", "not_found"), _row("B", None)])
    assert "사실의 부재가 아니라 조회의 부재다" in block
    assert "사용하지 말" in block
    assert "[확인: Genius] 표기" in block


def test_provenance_carries_fetch_date_and_citation_tier():
    rows = [_row("A", "matched",
                 credits={"writers": [], "producers": ["P"], "performances": []},
                 rels={"interpolates": ["X — Y"]},
                 url="https://genius.com/a", fetched=FETCHED)]
    block = rp._render_genius_block(rows)
    assert "[확인: Genius]" in block
    assert "2026-07-29" in block
    assert "https://genius.com/a" in block, "relationship facts carry their per-track source link"


def test_block_is_capped():
    rows = [
        _row(f"T{i}", "matched",
             credits={"writers": [f"W{i}-{j}" for j in range(30)],
                      "producers": [], "performances": []},
             rels={"samples": [f"Artist {i}-{j} — Very Long Sample Title {j}" for j in range(30)]},
             url=f"https://genius.com/t{i}", fetched=FETCHED)
        for i in range(60)
    ]
    block = rp._render_genius_block(rows)
    assert len(block) <= rp.GENIUS_BLOCK_MAX_CHARS + 100
    assert "절단" in block


# ── prompt injection (R2) ───────────────────────────────────────────────────

def test_genius_block_lands_in_the_prompt_between_album_and_refine():
    meta = {"title": "T", "artists": ["A"], "album_type": "album",
            "release_date": None, "label": None, "total_tracks": 1, "spotify_id": None}
    block = "## Genius 확인 사실 (파이프라인 제공 — 조사 대상 앨범)\n- x\n"
    prompt = rp.build_prompt("BASE", meta, refine=True, prior_note="OLD",
                             instruction="fix", genius_block=block)
    assert block in prompt
    assert prompt.index("## 앨범 (조사 대상)") < prompt.index("## Genius 확인 사실")
    assert prompt.index("## Genius 확인 사실") < prompt.index("## 보강 요청")


def test_prompt_without_block_is_unchanged_shape():
    meta = {"title": "T", "artists": ["A"], "album_type": "album",
            "release_date": None, "label": None, "total_tracks": 1, "spotify_id": None}
    prompt = rp.build_prompt("BASE", meta, refine=False, prior_note=None, instruction=None)
    assert "Genius" not in prompt.replace("BASE", "")


# ── failure plumbing ────────────────────────────────────────────────────────

class _BrokenConn:
    """No cursor at all — the worst case for both helpers."""

    def __init__(self):
        self.rolled_back = False

    def rollback(self):
        self.rolled_back = True


class _Cursor:
    def __init__(self, rows):
        self._rows = rows

    def __enter__(self):
        return self

    def __exit__(self, *_a):
        return False

    def execute(self, *_a, **_k):
        pass

    def fetchall(self):
        return self._rows


class _Conn:
    def __init__(self, rows):
        self._rows = rows
        self.events = []

    def cursor(self):
        return _Cursor(self._rows)

    def commit(self):
        self.events.append("commit")

    def rollback(self):
        self.events.append("rollback")


def test_nudge_is_fail_open_and_rolls_back():
    conn = _BrokenConn()
    rp._nudge_unready_albums(conn)  # must not raise
    assert conn.rolled_back, "a failed SELECT must not poison the claim that follows"


def test_nudge_releases_the_transaction_before_aws_and_honors_cooldown(monkeypatch, tmp_path):
    import types

    sent = []

    class _FakeSQS:
        def get_queue_url(self, QueueName):
            return {"QueueUrl": "q"}

        def send_message(self, QueueUrl, MessageBody):
            sent.append((len(conn.events), MessageBody))

    monkeypatch.setitem(sys.modules, "boto3",
                        types.SimpleNamespace(client=lambda *a, **k: _FakeSQS()))
    monkeypatch.setattr(rp, "_NUDGE_STATE", tmp_path / "state.json")

    conn = _Conn([{"album_id": "album-1"}])
    rp._nudge_unready_albums(conn)
    assert len(sent) == 1 and "album-1" in sent[0][1]
    # the read txn was committed BEFORE the send (Neon idle-in-txn rule)
    assert sent[0][0] >= 1 and conn.events[0] == "commit"

    rp._nudge_unready_albums(conn)  # immediate re-fire: cooldown must hold it
    assert len(sent) == 1, "a held album must not be re-nudged every 60s firing"


def test_facts_block_db_failure_propagates_so_the_row_fails_retryably():
    """A factless note stamped `done` is irreversible; a `failed` row retries —
    and no subscription call has been spent yet, so failing fast is free."""
    import pytest

    with pytest.raises(Exception):
        rp._genius_block(_BrokenConn(), "album-1")


def test_facts_block_render_failure_degrades_the_prompt_not_the_run():
    block = rp._genius_block(_Conn([{"title": "broken row"}]), "album-1")
    assert "정리 실패" in block
    assert "[확인: Genius]" in block and "사용하지 말" in block


# ── prompt vendoring contract ───────────────────────────────────────────────

def test_vendored_prompt_is_byte_identical_prefix_of_canonical():
    """The poller reads scripts/album_research_v2.md; the canonical doc is
    docs/editorial/album-research-prompt.md. The vendoring comment promises the
    vendored file is a byte-exact prefix — this is the only enforcement (the
    workspace has no PR CI)."""
    vendored = (ROOT / "scripts" / "album_research_v2.md").read_bytes()
    canonical = (ROOT / "docs" / "editorial" / "album-research-prompt.md").read_bytes()
    assert canonical.startswith(vendored)
