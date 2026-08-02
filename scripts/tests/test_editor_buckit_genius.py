"""FEAT-lyrics-annotations R6 — the catalog-internal graph in editor_buckit.

What these pin:

  * the graph is built from MATCHED rows only (a wrong song's credits must not
    reach an idea deck), and coverage is reported rather than implied — an
    unfetched album must never read as "no connections"
  * a connector must span two genuinely different acts: albums sharing any
    credited artist merge into one act, so a remix EP or a live album cannot
    make a band member look like a cross-artist connector
  * places (`… At`) and music-video crew (`Video …`) are not connectors, and
    post-production names are ranked apart so they cannot crowd out writers
  * a lineage edge is only claimed when BOTH ends are in our catalog, and never
    against a compilation, whose long artist list matches almost any name
  * `_fold` stays byte-identical to its twin `research_poller._fold_title`
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "myblog_shared_db" / "src"))

import editor_buckit as eb  # noqa: E402


def _cand(aid, title, artists):
    return {"album_id": aid, "title": title, "artists": list(artists)}


def _grow(album_id, *, status="matched", credits=None, rels=None, track="T1"):
    return {
        "album_id": album_id,
        "track_title": track,
        "track_no": 1,
        "match_status": status,
        "credits": credits,
        "relationships": rels,
    }


def _perf(role, *artists):
    return {"role": role, "artists": list(artists)}


# ── folding parity with R1 ──────────────────────────────────────────────────

def test_fold_is_identical_to_the_research_poller_twin():
    import research_poller as rp

    corpus = [
        "No.1 Stunna (feat. 100KGOLD)", "왈 (Simon Says)", "Café del Mar",
        "I.F.L.Y.", "New Person, Same Old Mistakes", "", "   ",
        "Beyoncé — RENAISSANCE", "SWEET / I THOUGHT YOU WANTED TO DANCE",
    ]
    for s in corpus:
        assert eb._fold(s) == rp._fold_title(s), f"twin drifted on {s!r}"


# ── the matched-only rule and honest coverage ──────────────────────────────

def test_unmatched_rows_never_contribute_credits_and_coverage_is_stated():
    cand = {"a1": _cand("a1", "A", ["Act1"]), "a2": _cand("a2", "B", ["Act2"])}
    rows = [
        _grow("a1", status="ambiguous", credits={"producers": ["Ghost"]}),
        _grow("a2", status="not_found", credits={"producers": ["Ghost"]}),
    ]
    out = "\n".join(eb._genius_graph_section(rows, cand, [], []))
    assert "Ghost" not in out, "an unmatched row's credits reached the deck"
    assert "매칭 보유 0장" in out
    assert "조회의 부재" in out, "absence of lookup must not read as absence of fact"


def test_coverage_counts_albums_not_rows():
    cand = {"a1": _cand("a1", "A", ["Act1"]), "a2": _cand("a2", "B", ["Act2"]),
            "a3": _cand("a3", "C", ["Act3"])}
    rows = [_grow("a1", track="t1"), _grow("a1", track="t2"),
            _grow("a2", status="not_found")]
    out = "\n".join(eb._genius_graph_section(rows, cand, [], []))
    assert "후보 3장 중 Genius 조회된 앨범 2장" in out
    assert "매칭 보유 1장" in out


# ── connectors ─────────────────────────────────────────────────────────────

def test_same_act_does_not_make_a_connector():
    """A band member across that band's own albums is not a connection."""
    cand = {
        "a1": _cand("a1", "Kid A", ["Radiohead"]),
        "a2": _cand("a2", "Amnesiac", ["Radiohead"]),
    }
    rows = [_grow("a1", credits={"producers": ["Nigel Godrich"]}),
            _grow("a2", credits={"producers": ["Nigel Godrich"]})]
    art, tech = eb._credit_connectors(rows, cand)
    assert art == [] and tech == []


def test_overlapping_artist_credits_count_as_one_act():
    """A remix EP credited to the artist + guests is the same act, not a second."""
    cand = {
        "a1": _cand("a1", "Album", ["Madonna"]),
        "a2": _cand("a2", "Remixes", ["Honey Dijon", "Madonna", "Sabrina Carpenter"]),
    }
    rows = [_grow("a1", credits={"producers": ["Stuart Price"]}),
            _grow("a2", credits={"producers": ["Stuart Price"]})]
    art, _ = eb._credit_connectors(rows, cand)
    assert art == [], "an overlapping artist list was counted as a second act"


def test_connector_across_two_acts_is_reported_with_its_span():
    cand = {"a1": _cand("a1", "IGOR", ["Tyler, The Creator"]),
            "a2": _cand("a2", "SOS", ["SZA"])}
    rows = [_grow("a1", credits={"producers": ["Carter Lang"]}),
            _grow("a2", credits={"writers": ["Carter Lang"]})]
    art, _ = eb._credit_connectors(rows, cand)
    assert len(art) == 1
    assert "Carter Lang" in art[0]
    assert "2팀 2장" in art[0]


def test_places_and_video_crew_are_not_connectors():
    cand = {"a1": _cand("a1", "A", ["Act1"]), "a2": _cand("a2", "B", ["Act2"])}
    rows = [
        _grow("a1", credits={"performances": [
            _perf("Mixed At", "Larrabee Sound Studios"),
            _perf("Video Hair Stylist", "Someone"),
            _perf("Label", "Universal Music Group"),
        ]}),
        _grow("a2", credits={"performances": [
            _perf("Mixed At", "Larrabee Sound Studios"),
            _perf("Video Hair Stylist", "Someone"),
            _perf("Label", "Universal Music Group"),
        ]}),
    ]
    art, tech = eb._credit_connectors(rows, cand)
    joined = "\n".join(art + tech)
    for noise in ("Larrabee", "Someone", "Universal Music Group"):
        assert noise not in joined, f"{noise} should not be a connector"


def test_post_production_is_listed_apart_from_creative():
    cand = {"a1": _cand("a1", "A", ["Act1"]), "a2": _cand("a2", "B", ["Act2"])}
    rows = [
        _grow("a1", credits={"producers": ["Writerly"],
                             "performances": [_perf("Mastering Engineer", "Masterly")]}),
        _grow("a2", credits={"producers": ["Writerly"],
                             "performances": [_perf("Mastering Engineer", "Masterly")]}),
    ]
    art, tech = eb._credit_connectors(rows, cand)
    assert any("Writerly" in ln for ln in art)
    assert any("Masterly" in ln for ln in tech)
    assert not any("Masterly" in ln for ln in art)


def test_one_production_credit_moves_a_post_name_to_creative_and_shows_why():
    """The single credit that reclassifies a name must be visible in the line.

    Roles are truncated for width; sorted plainly, an engineer with one
    producer credit displayed three engineering roles and the reason he was
    ranked as creative stayed hidden.
    """
    cand = {"a1": _cand("a1", "A", ["Act1"]), "a2": _cand("a2", "B", ["Act2"])}
    rows = [
        _grow("a1", credits={"producers": ["Bordone"], "performances": [
            _perf("Additional Engineering", "Bordone"),
            _perf("Additional Mixing", "Bordone"),
            _perf("Assistant Mixing Engineer", "Bordone"),
        ]}),
        _grow("a2", credits={"performances": [_perf("Mixing Engineer", "Bordone")]}),
    ]
    art, _ = eb._credit_connectors(rows, cand)
    assert len(art) == 1
    assert art[0].split("(")[1].startswith("프로듀서")


# ── lineage ────────────────────────────────────────────────────────────────

def _index(tracks, albums):
    ti: dict[str, list[dict]] = {}
    for t in tracks:
        ti.setdefault(eb._fold(t["title"]), []).append(t)
    return ti, {a["album_id"]: a for a in albums}


def test_lineage_edge_needs_both_ends_in_the_catalog():
    cand = {"a1": _cand("a1", "channel ORANGE", ["Frank Ocean"])}
    rows = [_grow("a1", track="Sweet Life",
                  rels={"samples": ["Stevie Wonder — Superwoman",
                                    "Someone Else — A Song We Do Not Own"]})]
    ti, ai = _index(
        [{"title": "Superwoman", "album_id": "a9"}],
        [{"album_id": "a9", "title": "Songs In The Key Of Life", "artists": ["Stevie Wonder"]}],
    )
    cross, same = eb._lineage_edges(rows, cand, ti, ai)
    assert len(cross) == 1 and same == 0
    assert "Superwoman" in cross[0] and "Stevie Wonder" in cross[0]
    assert "A Song We Do Not Own" not in cross[0]


def test_same_act_lineage_is_counted_not_listed():
    """Remix/live/deluxe packaging is an edge, but not an idea."""
    cand = {"a1": _cand("a1", "BRAT", ["Charli xcx"])}
    rows = [_grow("a1", track="360", rels={"remixed_by": ["Charli xcx — 360 remix"]})]
    ti, ai = _index(
        [{"title": "360 remix", "album_id": "a2"}],
        [{"album_id": "a2", "title": "Brat remixes", "artists": ["Charli xcx"]}],
    )
    cross, same = eb._lineage_edges(rows, cand, ti, ai)
    assert cross == [] and same == 1


def test_lineage_skips_a_compilation_target():
    """37 credited composers match any composer name — that is a haystack."""
    cand = {"a1": _cand("a1", "CONFESSIONS II", ["Madonna"])}
    rows = [_grow("a1", track="Betrayal", rels={"interpolates": ["Erik Satie — Gnossienne No. 1"]})]
    many = [f"Composer {i}" for i in range(eb.LINEAGE_MAX_TARGET_ARTISTS)] + ["Erik Satie"]
    ti, ai = _index(
        [{"title": "Gnossienne No. 1", "album_id": "a2"}],
        [{"album_id": "a2", "title": '"072 Classical Music Discoveries"', "artists": many}],
    )
    cross, same = eb._lineage_edges(rows, cand, ti, ai)
    assert cross == [] and same == 0


def test_lineage_ignores_the_albums_own_tracks():
    cand = {"a1": _cand("a1", "Album", ["Act1"])}
    rows = [_grow("a1", track="One", rels={"samples": ["Act1 — Two"]})]
    ti, ai = _index(
        [{"title": "Two", "album_id": "a1"}],
        [{"album_id": "a1", "title": "Album", "artists": ["Act1"]}],
    )
    cross, same = eb._lineage_edges(rows, cand, ti, ai)
    assert cross == [] and same == 0


def test_album_label_bounds_a_long_artist_list():
    label = eb._album_label("X", [f"A{i}" for i in range(37)])
    assert "외 34인" in label
    assert len(label) < 60
