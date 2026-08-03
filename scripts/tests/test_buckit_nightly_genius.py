"""FEAT-lyrics-annotations R3 — Genius facts as a nightly-draft context field.

What these pin:

  * the facts block reaches the assembled context, per memo, next to the note
  * an album nobody ever fetched degrades to an explicit "조회의 부재" with the
    `[확인: Genius]` tier banned — it never renders as silence, because silence
    reads as "this album has no credits"
  * a render failure fails OPEN (tier ban, drafts still happen) rather than
    costing the night its output
  * the source-priority rule travels WITH the data: the block that carries
    credits also carries "block outranks the note, and the tier marks only what
    came from the block"
  * the batch SQL keeps RESEARCH_SQL's owner scope and LEFT-JOINs tracks, so an
    unfetched album still produces rows to degrade from
"""
from __future__ import annotations

import sys
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "myblog_shared_db" / "src"))

import buckit_nightly as bn  # noqa: E402

ALBUM = "11111111-1111-1111-1111-111111111111"


def _track(title, status, *, credits=None, rels=None, track_no=1, album=ALBUM):
    return {
        "album_id": album,
        "title": title,
        "track_no": track_no,
        "match_status": status,
        "match_confidence": 0.95 if status == "matched" else None,
        "genius_title": title if status == "matched" else None,
        "genius_artist": "Someone" if status == "matched" else None,
        "genius_url": f"https://genius.com/{title}" if status == "matched" else None,
        "credits": credits or {},
        "relationships": rels or {},
        "fetched_at": datetime(2026, 8, 1, tzinfo=timezone.utc) if status else None,
    }


# --- the block itself -----------------------------------------------------

def test_no_rows_at_all_bans_the_tier_and_says_lookup_not_absence():
    for empty in (None, []):
        out = bn._genius_block(empty)
        assert "조회의 부재" in out
        assert "`[확인: Genius]` 표기를 쓰지 말 것" in out


def test_unfetched_album_degrades_instead_of_vanishing():
    """Every track present, none fetched — the whole point of the LEFT JOIN.

    A silently omitted block is indistinguishable from "we checked and this
    album has no credits", which is the claim this pipeline may never make.
    It collapses to one line rather than naming every track: with nothing
    matched, the per-track 미조회 list repeats what the count already said
    (measured on prod — 18 tracks, ~1.1k chars, to say "we never looked").
    """
    rows = [_track("A", None, track_no=1), _track("B", None, track_no=2)]
    out = bn._genius_block(rows)
    assert "(0/2트랙)" in out
    assert "사실의 부재가 아니라 조회의 부재다" in out
    assert "`[확인: Genius]` 표기를 쓰지 말 것" in out
    assert "미조회" not in out          # no per-track enumeration
    assert len(out.splitlines()) == 1


def test_partially_fetched_album_keeps_the_per_track_list():
    """The collapse is only for never-fetched. One match ⇒ which tracks are
    unverified becomes load-bearing again, so the renderer runs."""
    rows = [_track("A", "matched", credits={"producers": ["P1"]}, track_no=1),
            _track("B", None, track_no=2)]
    out = bn._genius_block(rows)
    assert "매칭 1/2트랙" in out
    assert "B" in out and "미조회" in out


def test_matched_album_carries_credits_and_the_priority_rule():
    rows = [
        _track("A", "matched", credits={"producers": ["P1"], "writers": ["W1"]}, track_no=1),
        _track("B", "matched", credits={"producers": ["P1"]}, track_no=2),
    ]
    out = bn._genius_block(rows)
    # the renderer's own output survives the wrapper
    assert "P1" in out and "매칭 근거" in out
    # …and the nightly-specific reading rule rides along with it
    assert "이 블록이 1차 출처다" in out
    assert "이 블록을 따르고, 어긋났다는 사실을 적어라" in out
    assert "이 블록에서 가져온 사실에만" in out
    assert "<<<Genius_사실_시작>>>" in out and "<<<Genius_사실_끝>>>" in out


def test_render_failure_fails_open_with_the_tier_banned(monkeypatch):
    import research_poller as rp

    def boom(_rows):
        raise RuntimeError("renderer bug")

    monkeypatch.setattr(rp, "_render_genius_block", boom)
    out = bn._genius_block([_track("A", "matched")])
    assert "조회의 부재" in out
    assert "`[확인: Genius]` 표기를 쓰지 말 것" in out


def test_renderer_is_imported_not_reimplemented():
    """Third copy of the derivation logic = the twin-drift class. Keep one."""
    src = (ROOT / "scripts" / "buckit_nightly.py").read_text(encoding="utf-8")
    assert "from research_poller import _render_genius_block" in src
    for owned_by_the_renderer in ("match_confidence", "_BOILERPLATE_ROLES", "인터폴레이션"):
        assert src.count(owned_by_the_renderer) <= 1, owned_by_the_renderer


# --- the batch SQL --------------------------------------------------------

def test_batch_sql_keeps_owner_scope_and_left_joins_tracks():
    sql = bn.GENIUS_SQL
    assert "LEFT JOIN track_genius_songs" in sql       # unfetched albums still yield rows
    assert "i.prep_tonight = true" in sql              # only tonight's memos
    assert "i.post_id IS NULL" in sql
    assert "b.user_id = %(owner_sub)s" in sql          # A-4 owner scope, as RESEARCH_SQL
    assert "ORDER BY t.album_id" in sql                # grouping relies on it


# --- assembly into the context block --------------------------------------

class _Cur:
    def __init__(self, table):
        self._table = table
        self._rows: list[dict] = []

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def execute(self, sql, params=None):
        self._rows = self._table.get(sql, [])

    def fetchall(self):
        return self._rows


class _Conn:
    def __init__(self, table):
        self._table = table

    def cursor(self):
        return _Cur(self._table)


def _checked_row(album=ALBUM):
    return {
        "album_id": album, "item_id": "i1", "bucket_id": "b1",
        "note": "좋았다", "rec_reason": None, "item_status": "candidate",
        "prep_tonight": True, "bucket_name": "8월", "research_mode": "auto",
        "bucket_is_done": False, "bucket_pos": 1, "item_pos": 1,
        "title": "TestAlbum", "release_date": date(2026, 1, 1), "album_type": "album",
        "total_tracks": 2, "label": "L", "best_new": False,
        "artists": ["Artist"], "genres": ["pop"],
    }


def _conn_with(genius_rows, research=()):
    return _Conn({
        bn.CHECKED_SQL: [_checked_row()],
        bn.FOREIGN_CHECKED_SQL: [{"n": 0, "users": 0}],
        bn.RESEARCH_SQL: list(research),
        bn.RECENCY_SQL: [],
        bn.GENIUS_SQL: genius_rows,
    })


def test_context_block_carries_the_facts_next_to_the_note():
    rows = [_track("A", "matched", credits={"producers": ["P1"]}, track_no=1)]
    note = [{"album_id": ALBUM, "result_md": "## 노트\n본문", "finished_at": None}]
    memos, ctx = bn.export_checked_memos(_conn_with(rows, note))
    assert len(memos) == 1
    assert memos[0]["genius_md"]
    assert "<<<Genius_사실_시작>>>" in ctx and "P1" in ctx
    # note first, facts immediately after — the conflict is meant to be readable side by side
    assert ctx.index("리서치_노트") < ctx.index("Genius_사실_시작") < ctx.index("청취 기록")


def test_album_with_no_genius_rows_still_gets_the_ban_line():
    memos, ctx = bn.export_checked_memos(_conn_with([]))
    assert "조회의 부재" in ctx
    assert "<<<Genius_사실_시작>>>" not in ctx


def test_rows_are_grouped_per_album():
    other = "22222222-2222-2222-2222-222222222222"
    rows = [
        _track("A", "matched", credits={"producers": ["Mine"]}, track_no=1),
        _track("Z", "matched", credits={"producers": ["Theirs"]}, track_no=1, album=other),
    ]
    memos, _ = bn.export_checked_memos(_conn_with(rows))
    assert "Mine" in memos[0]["genius_md"]
    assert "Theirs" not in memos[0]["genius_md"]
