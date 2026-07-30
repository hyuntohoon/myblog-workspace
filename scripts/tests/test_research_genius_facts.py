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


def _row(title, status, *, credits=None, rels=None, url=None, fetched=None,
         track_no=1, genius_title=None, confidence=None):
    return {
        "title": title,
        "track_no": track_no,
        "match_status": status,
        "match_confidence": confidence if confidence is not None
        else (0.9 if status == "matched" else None),
        "genius_title": genius_title if genius_title is not None else title,
        "genius_artist": "A",
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
    assert "P (1/1트랙 — 1 Good)" in block and "W (1/1트랙 — 1 Good)" in block
    assert "EVIL" not in block, "an ambiguous match may be a different song entirely"
    assert "매칭 1/2트랙" in block


# ── match evidence (the 2026-07-30 ONYX e2e findings) ───────────────────────

def test_unmatched_tracks_are_named_not_just_counted():
    """"미매칭 3트랙" with no names left the note unable to say which facts were
    missing — it recorded the gap as 미해결 rather than as a track list."""
    rows = [
        _row("Fine", "matched", track_no=1, credits={}, rels={}, fetched=FETCHED),
        _row("Murky", "ambiguous", track_no=2),
        _row("Absent", "not_found", track_no=3),
        _row("Unseen", None, track_no=4),
    ]
    block = rp._render_genius_block(rows)
    assert "2 Murky [모호]" in block
    assert "3 Absent [Genius 미등재]" in block
    assert "4 Unseen [미조회]" in block


def test_every_matched_track_carries_its_genius_title_confidence_and_url():
    """ONYX: 9 matched tracks, 0 relationships, and therefore 0 source links —
    the old block emitted links only for relationship-bearing tracks."""
    rows = [
        _row("Solo", "matched", track_no=1, credits={"producers": ["P"]}, rels={},
             url="https://genius.com/solo", confidence=0.74, fetched=FETCHED),
    ]
    block = rp._render_genius_block(rows)
    assert "https://genius.com/solo" in block, "a matched track with no relationship still needs its source"
    assert "신뢰도 0.74" in block
    assert "### 매칭 근거" in block


def test_title_divergence_is_flagged_without_being_called_a_verdict():
    """The real collision: our `Simon Says` → Genius `왈 (Simon Says)`, a
    different 2018 single by the same artist, matched at 0.7424."""
    rows = [
        _row("Simon Says", "matched", track_no=2, genius_title="왈 (Simon Says)",
             credits={"writers": ["Pharoahe Monch"], "producers": ["slom"]},
             rels={}, url="https://genius.com/ss", confidence=0.7424, fetched=FETCHED),
    ]
    block = rp._render_genius_block(rows)
    assert "⚠︎ 곡명 불일치" in block
    assert "왈 (Simon Says)" in block, "the stored genius_title is the evidence"
    assert "동명이곡" in block, "the flag must name the failure mode it guards"
    assert "오매칭 확정이 아니다" in block, "a literal difference is not a verdict"
    # and the suspect credits must point back at the suspect track
    assert "slom (1/1트랙 — 2 Simon Says)" in block


def test_a_person_credited_in_two_roles_does_not_pool_their_tracks():
    """RENAISSANCE, 2026-07-30: Beyoncé and The-Dream both produce AND write, and
    a single shared attribution map pooled the two roles under one key — the
    count said 3/14 while the list showed six tracks, one of them twice."""
    rows = [
        _row("T1", "matched", track_no=1, url="u1", fetched=FETCHED,
             credits={"producers": ["X"], "writers": ["X"], "performances": []}, rels={}),
        _row("T2", "matched", track_no=2, url="u2", fetched=FETCHED,
             credits={"producers": ["X"], "writers": [], "performances": []}, rels={}),
    ]
    block = rp._render_genius_block(rows)
    assert "프로듀서: X (2/2트랙 — 1 T1 · 2 T2)" in block
    assert "작곡·작사: X (1/2트랙 — 1 T1)" in block, "the writer line must not inherit producer tracks"
    assert "1 T1 · 1 T1" not in block, "no track may repeat inside one credit"


def test_feature_suffix_alone_is_not_a_divergence():
    """Genius routinely drops the feature credit from a title; flagging that
    benign difference would bury the one that matters."""
    rows = [
        _row("No.1 Stunna (feat. 100KGOLD)", "matched", track_no=7,
             genius_title="No.1 Stunna", credits={}, rels={},
             url="https://genius.com/n", fetched=FETCHED),
    ]
    block = rp._render_genius_block(rows)
    assert "⚠︎ 곡명 불일치" not in block, "a dropped feature credit is not a divergence"
    assert "7 No.1 Stunna" in block


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
