#!/usr/bin/env python3
"""FEAT-editor-buckit Step 1 (Stage 0) — the $0 editorial commissioning desk.

Reads the owner's saved-but-unwritten review-bucket albums (+ their notes,
rec_reasons, done research-note excerpts, in-bucket genre/artist clusters, and
recent listens) **read-only** from prod Neon, pulls the current critical
conversation live from the web, and emits a dated Markdown *idea report* — a
short deck of editorial commission cards answering "what should I write next,
and from what angle?". Pre-writing only: it proposes topics; it never writes
prose, never publishes, and writes NOTHING to the DB.

This is the cheapest possible proof (RFC Stage 0): a single `claude -p` run on
the owner's Max subscription = **$0**, mirroring `scripts/research_poller.py`.
No DB table, no backend route, no frontend, no scheduler, no API key. Manual
single-fire — run it when the bucket has new signal.

    myblog_backend/.venv/bin/python scripts/editor_buckit.py            # full run
    myblog_backend/.venv/bin/python scripts/editor_buckit.py --dry-run  # print the
        #   assembled bucket context + exit, WITHOUT calling claude (inspect grounding)

Clone heritage / safety (RFC "Current state"):
  * `database_url()` / `connect()` / `run_claude()` are lifted from
    research_poller.py (same secret `myblog/backend`, same `claude -p` JSON path).
  * The DB session is READ ONLY, transaction-scoped (`conn.read_only`, NOT a leaking session
    `SET default_transaction_read_only`; reference-neon-pooler-readonly-leak) — SELECTs only,
    this script can NOT write to prod. Dropped vs the poller: the claim-gate/queue,
    the launchd loop, and ALL DB writeback (no UPDATE/INSERT anywhere).
  * Never logs DATABASE_URL / secrets. The model gets `--allowed-tools
    WebSearch,WebFetch` only (no Bash/Edit) — a headless run can't touch the repo.

RFC: docs/archive/done/rfcs/FEAT-editor-buckit.md (Stage 0, Step 1; archived 2026-06-18).
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
import time
import unicodedata
from datetime import date
from pathlib import Path

# shared_db is read from the LOCAL checkout via src-path injection (not the git
# pin) — same pattern as research_poller.py. Resolves relative to this script
# so it works from any checkout that carries the nested myblog_shared_db repo.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "myblog_shared_db" / "src"))

from myblog_shared_db.llm import CliEngine, LLMJob, ToolPolicy  # noqa: E402
from myblog_shared_db.llm.subscription_guard import coordinated_run  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    stream=sys.stderr,
)
log = logging.getLogger("editor_buckit")

# --- config ---------------------------------------------------------------
REGION = "ap-northeast-2"
SECRET_ID = "/myblog/backend"         # SSM SecureString param (holds DATABASE_URL)
PROMPT_VERSION = "v1"                  # surfaced in the report header (OQ6)
PROMPT_FILE = "editor-buckit-prompt.md"  # canonical prompt, read live (no vendored copy in Stage 0)
CLAUDE_MODEL = "opus"                  # same bench winner as the research path
CLAUDE_TIMEOUT_S = 1200                # broad web read + many albums ⇒ longer than one research run
RESEARCH_EXCERPT_CHARS = 600          # per done-note excerpt cap (bounds the prompt)
MAX_RESEARCH_EXCERPTS = 30            # cap research notes embedded; log when more exist
RECENT_DAYS = 30                      # play-event recency window
CLUSTER_MIN = 2                       # a genre/artist is a "cluster" at >= this many bucketed albums

# --- Genius catalog graph (FEAT-lyrics-annotations R6) --------------------
# The one thing no external service can compute: relations that hold *inside
# this catalog*. Two shapes, both derived from the track-scoped Genius store
# (`track_genius_songs`), MATCHED rows only — an ambiguous match may be a
# different song entirely, and a wrong credit must not enter an idea deck
# (the same hold R1 applies to research notes).
CONNECTOR_MIN_ALBUMS = 2   # a credit name is a "connector" at >= this many bucket albums
CONNECTOR_MAX = 15         # rendered creative connectors, strongest first
CONNECTOR_TECH_MAX = 8     # …and post-production ones, listed apart so they can't crowd the above
LINEAGE_MAX = 25           # rendered cross-artist lineage edges
# The far side of a lineage edge is confirmed by looking for the Genius artist
# string inside our album's credited artists. That check loses all meaning on a
# compilation: `"072 Classical Music Discoveries"` credits 37 composers, so any
# composer name "matches" it. Above this many credited artists the album is a
# haystack, not an identification.
LINEAGE_MAX_TARGET_ARTISTS = 8

# Corporate boilerplate rides `credits.performances` on nearly every track
# (Label / Publisher / ℗ / © at 14-15/15 on prod). Left in, "Universal Music
# Group connects 30 albums" would outrank every real person. Twin of
# research_poller._BOILERPLATE_ROLES.
_BOILERPLATE_ROLES = {
    "label", "publisher", "distributor",
    "copyright ©", "phonographic copyright ℗",
}

# Post-production hints. These people are real connectors — the RFC's own
# example is an engineer — but a handful of them master most of pop music, so
# they are ranked in their own list instead of ahead of the writers.
_TECH_ROLE_HINTS = ("engineer", "engineering", "mixing", "mastering",
                    "programmer", "programming", "technician")


# --- paths ----------------------------------------------------------------
def _repo_root() -> str:
    # scripts/ sits at the workspace repo root.
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _prompt_path() -> str:
    return os.path.join(_repo_root(), "docs", "editorial", PROMPT_FILE)


def _output_dir() -> str:
    return os.path.join(_repo_root(), "docs", "editorial", "ideas")


# --- secrets / db ---------------------------------------------------------
def database_url() -> str:
    """Read prod DATABASE_URL from SSM Parameter Store and normalize for psycopg."""
    import boto3

    ssm = boto3.client("ssm", region_name=REGION)
    secret = json.loads(ssm.get_parameter(Name=SECRET_ID, WithDecryption=True)["Parameter"]["Value"])
    # SQLAlchemy form `postgresql+psycopg://` -> libpq form psycopg.connect wants.
    return secret["DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://", 1)


def connect():
    import psycopg
    from psycopg.rows import dict_row

    # connect_timeout=30 absorbs Neon cold-start (reference-database-url-psql).
    conn = psycopg.connect(database_url(), connect_timeout=30, row_factory=dict_row)
    # Read-only safety, TRANSACTION-scoped — NOT a session SET. A session-level
    # `SET default_transaction_read_only = on` LEAKS through Neon's pgbouncer (`-pooler`) onto a
    # shared server connection and makes a LATER writer (the backend Lambda's INSERT) fail
    # read-only (root-caused in FEAT-editor-buckit Step 7; reference-neon-pooler-readonly-leak).
    # `conn.read_only` applies READ ONLY per transaction (auto-cleared on commit/rollback ⇒ never
    # poisons the pool). autocommit stays False ⇒ SELECTs share one read-only tx, rolled back on close.
    conn.read_only = True
    return conn


# --- read-only context export --------------------------------------------
UNWRITTEN_SQL = """
SELECT
    i.album_id,
    i.note,
    i.rec_reason,
    i.status::text          AS item_status,
    i.research_selected,
    b.name                  AS bucket_name,
    b.kind                  AS bucket_kind,
    b.research_mode,
    b.is_done               AS bucket_is_done,
    b.position              AS bucket_pos,
    i.position              AS item_pos,
    a.title,
    a.release_date,
    a.album_type,
    a.total_tracks,
    a.label,
    a.best_new,
    COALESCE((SELECT array_agg(ar.name ORDER BY ar.name)
                FROM album_artists aa JOIN artists ar ON ar.id = aa.artist_id
               WHERE aa.album_id = a.id), '{}')            AS artists,
    COALESCE((SELECT array_agg(DISTINCT g.label)
                FROM album_genres ag JOIN genres g ON g.id = ag.genre_id
               WHERE ag.album_id = a.id), '{}')            AS genres
FROM review_bucket_items i
JOIN review_buckets b ON b.id = i.bucket_id
JOIN albums a         ON a.id = i.album_id
WHERE i.post_id IS NULL
ORDER BY b.position, i.position;
"""

RESEARCH_SQL = """
SELECT album_id, result_md, finished_at
FROM album_research
WHERE status = 'done' AND result_md IS NOT NULL
  AND album_id IN (SELECT DISTINCT album_id FROM review_bucket_items WHERE post_id IS NULL)
ORDER BY finished_at DESC NULLS LAST;
"""

RECENCY_SQL = f"""
SELECT album_id,
       max(played_at)                                                       AS last_played,
       count(*) FILTER (WHERE played_at > now() - INTERVAL '{RECENT_DAYS} days') AS plays_recent
FROM spotify_play_events
WHERE album_id IN (SELECT DISTINCT album_id FROM review_bucket_items WHERE post_id IS NULL)
GROUP BY album_id;
"""

REVIEWED_SQL = """
SELECT pa.album_id,
       a.title,
       COALESCE((SELECT string_agg(ar.name, ', ' ORDER BY ar.name)
                   FROM album_artists aa JOIN artists ar ON ar.id = aa.artist_id
                  WHERE aa.album_id = a.id), '') AS artists
FROM post_albums pa
JOIN albums a ON a.id = pa.album_id;
"""

# R6. Every Genius row for a bucket candidate — ALL statuses, so coverage can
# be reported honestly (the RFC's "사실의 부재가 아니라 조회의 부재" rule); the
# graph itself is built from the `matched` subset only.
GENIUS_SQL = """
SELECT t.album_id,
       t.title           AS track_title,
       t.track_no,
       g.match_status,
       g.credits,
       g.relationships
FROM track_genius_songs g
JOIN tracks t ON t.id = g.track_id
WHERE t.album_id IN (SELECT DISTINCT album_id FROM review_bucket_items WHERE post_id IS NULL)
ORDER BY t.album_id, t.track_no;
"""

# The far side of a lineage edge can be ANY album we own, not just a bucketed
# one — "this bucket album samples something already in the catalog" is the
# whole point. So the index spans the catalog (27k tracks / 3.1k albums on
# prod, two flat queries; the per-row artist subquery that made an earlier
# probe slow is deliberately split out into CATALOG_ALBUM_SQL).
CATALOG_TRACK_SQL = """
SELECT t.title, t.album_id FROM tracks t;
"""

CATALOG_ALBUM_SQL = """
SELECT a.id AS album_id,
       a.title,
       COALESCE((SELECT array_agg(ar.name ORDER BY ar.name)
                   FROM album_artists aa JOIN artists ar ON ar.id = aa.artist_id
                  WHERE aa.album_id = a.id), '{}') AS artists
FROM albums a;
"""


def _fetch_all(conn, sql):
    with conn.cursor() as cur:
        cur.execute(sql)
        return cur.fetchall()


def _fmt_date(d) -> str:
    if d is None:
        return "?"
    try:
        return d.date().isoformat()  # datetime -> YYYY-MM-DD
    except AttributeError:
        return d.isoformat()         # already a date


def _bucket_label(b: dict) -> str:
    """Bucket membership with its research_mode + done flag (real why-now signals)."""
    tag = f"리서치 {b['research_mode']}" if b.get("research_mode") else ""
    if b.get("is_done"):
        tag = (tag + " · 완료") if tag else "완료"
    return b["name"] + (f"({tag})" if tag else "")


def _signal_lines(c: dict) -> list[str]:
    """The grounded 'why now' fuel for one candidate — only real signals."""
    out: list[str] = []
    for note in c.get("notes", []):
        out.append(f"  - 노트: {note}")
    for reason in c.get("rec_reasons", []):
        out.append(f"  - 추천 근거: {reason}")
    if c.get("research_md"):
        excerpt = c["research_md"].strip().replace("\n", " ")[:RESEARCH_EXCERPT_CHARS]
        out.append(f"  - 리서치 노트(done) 발췌: {excerpt}…")
    last = c.get("last_played")
    recent = c.get("plays_recent") or 0
    if last and recent:
        out.append(f"  - 청취: 최근 {RECENT_DAYS}일 {recent}회, 마지막 {_fmt_date(last)}")
    elif last:  # listened before, but not in the recency window → an explicit 휴면 signal
        out.append(f"  - 청취: 최근 {RECENT_DAYS}일 0회 (휴면), 마지막 {_fmt_date(last)}")
    else:
        out.append("  - 청취: 기록 없음")
    if c.get("best_new"):
        out.append("  - 표시: Best New Music(BNM)")
    return out


# --- R6: the catalog-internal graph ---------------------------------------
_REL_LABELS = {
    "samples": "샘플",
    "interpolates": "인터폴레이션",
    "sampled_in": "이 곡을 샘플한 쪽",
    "interpolated_by": "이 곡을 인터폴레이션한 쪽",
    "cover_of": "커버 원곡",
    "covered_by": "커버한 쪽",
    "remix_of": "리믹스 원곡",
    "remixed_by": "리믹스한 쪽",
    "live_version_of": "라이브 원곡",
    "performed_live_as": "라이브 버전",
}

_FEAT_RE = re.compile(r"\s*[\(\[]\s*(?:feat|ft|featuring|with)\b[^\)\]]*[\)\]]", re.I)


def _fold(text: str) -> str:
    """Comparison form for matching Genius's free-text relation strings against
    our own titles/artists.

    Byte-for-byte twin of `research_poller._fold_title`, and the parity is
    pinned by `scripts/tests/test_editor_buckit_genius.py` rather than by
    convention — the two scripts are independent operator tools and importing a
    whole poller (which configures logging and constructs an engine at import)
    for one helper would couple them far more than the copy costs.
    """
    text = _FEAT_RE.sub("", text or "")
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return " ".join("".join(ch if ch.isalnum() or ch.isspace() else " " for ch in text.lower()).split())


def _album_label(title: str, artists: list[str]) -> str:
    """`Artist 『Title』`, with the artist list bounded.

    Uncapped, one compilation ("072 Classical Music Discoveries", 37 credited
    composers) turns a single edge into a 600-character line.
    """
    if not artists:
        who = "(미상)"
    elif len(artists) > 3:
        who = ", ".join(artists[:3]) + f" 외 {len(artists) - 3}인"
    else:
        who = ", ".join(artists)
    return f"{who} 『{title}』"


def _role_class(role: str) -> str | None:
    """창작 / 기술, or None when the role does not belong in a connector list.

    Two whole categories are dropped, both of which outnumber the people they
    would displace. A studio is a place, not shared personnel — `Mastered At`
    and `Mixed At` alone carry ~490 credits on prod, and in the first run of
    this section five of the top twelve "connectors" were studios. `Video …`
    roles (director, editor, hair stylist) staff the music video, not the
    record an idea card would be about.
    """
    r = (role or "").strip().lower()
    if not r or r in _BOILERPLATE_ROLES or r.endswith(" at") or r.startswith("video "):
        return None
    return "기술" if any(h in r for h in _TECH_ROLE_HINTS) else "창작"


def _distinct_artist_groups(artist_sets: list[frozenset[str]]) -> int:
    """How many genuinely different acts these albums represent.

    Any two albums sharing a credited artist merge into one group. Without the
    merge, a remix EP credited "Honey Dijon, Madonna, Sabrina Carpenter" counts
    as a second act against Madonna's own album, and every same-artist
    packaging edge — remix EP, live album, deluxe reissue — reads as a
    cross-artist connection. Measured on prod: 114 names sit on ≥2 bucket
    albums, but only 56 span ≥2 acts once this merge runs.
    """
    groups: list[set[str]] = []
    for s in artist_sets:
        cur = set(s)
        for g in [g for g in groups if g & cur]:
            groups.remove(g)
            cur |= g
        groups.append(cur)
    return len(groups)


def _credit_connectors(matched: list[dict],
                       cand_by: dict[str, dict]) -> tuple[list[str], list[str]]:
    """People who tie two or more bucket albums together.

    "이 버킷의 세 앨범이 Noah Goldstein을 공유한다" is a property of *this*
    bucket; no external service can compute it. A connector must span ≥2 acts,
    otherwise it is just a band member appearing across their own discography.

    Returns (창작, 기술) separately. Mixed into one list the post-production
    names win outright — they work on nearly everything — and the writers and
    producers, which are what an idea card is actually made of, fall off the
    bottom.
    """
    by_name: dict[str, dict[str, set[str]]] = {}
    creative: set[str] = set()

    def _seen(name: str, role: str, album_id: str, klass: str) -> None:
        n = (name or "").strip()
        if not n:
            return
        by_name.setdefault(n, {}).setdefault(album_id, set()).add(role)
        if klass == "창작":
            creative.add(n)

    for r in matched:
        aid = str(r["album_id"])
        if aid not in cand_by:
            continue
        credits = r["credits"] or {}
        for w in set(credits.get("writers") or []):
            _seen(w, "작가", aid, "창작")
        for p in set(credits.get("producers") or []):
            _seen(p, "프로듀서", aid, "창작")
        for perf in credits.get("performances") or []:
            role = (perf.get("role") or "").strip()
            klass = _role_class(role)
            if klass is None:
                continue
            for a in set(perf.get("artists") or []):
                _seen(a, role, aid, klass)

    ranked = []
    for name, albums in by_name.items():
        if len(albums) < CONNECTOR_MIN_ALBUMS:
            continue
        sets = [frozenset(_fold(a) for a in cand_by[aid]["artists"]) for aid in albums]
        acts = _distinct_artist_groups(sets)
        if acts < 2:
            continue
        ranked.append((acts, len(albums), name, albums))

    ranked.sort(key=lambda t: (-t[0], -t[1], t[2]))

    def _line(acts: int, n_alb: int, name: str, albums: dict[str, set[str]]) -> str:
        # Creative roles first, because the displayed roles are truncated and
        # the creative one is what put this name in the creative list. Sorted
        # alphabetically, Bryce Bordone showed as three engineering roles while
        # the single producer credit that classified him stayed hidden.
        roles = sorted(
            {role for rs in albums.values() for role in rs},
            key=lambda r: (0 if r in ("작가", "프로듀서") else 1 if _role_class(r) == "창작" else 2, r),
        )
        role_s = "·".join(roles[:3]) + ("…" if len(roles) > 3 else "")
        where = ", ".join(
            _album_label(cand_by[aid]["title"], cand_by[aid]["artists"]) for aid in list(albums)[:5]
        )
        more = f" 외 {n_alb - 5}장" if n_alb > 5 else ""
        return f"- {name} ({role_s}) — {acts}팀 {n_alb}장: {where}{more}"

    art = [_line(*t) for t in ranked if t[2] in creative][:CONNECTOR_MAX]
    tech = [_line(*t) for t in ranked if t[2] not in creative][:CONNECTOR_TECH_MAX]
    return art, tech


def _lineage_edges(matched: list[dict], cand_by: dict[str, dict],
                   track_index: dict[str, list[dict]],
                   album_index: dict[str, dict]) -> tuple[list[str], int]:
    """Sample/interpolation/cover relations whose OTHER side we also own.

    Genius stores a relation as the free string "Artist — Title", so the far
    side is resolved by folded title plus an artist check; an unresolvable
    string is simply not an edge (this never asserts a relation we cannot see
    both ends of). Returns the cross-act edges — the ones worth an idea card —
    and a count of the same-act ones, which on prod are overwhelmingly release
    packaging (a remix EP, a live album) and would bury the rest at equal
    weight: 31 cross vs 69 same on the 2026-08-03 measurement.
    """
    cross: list[str] = []
    same = 0
    seen: set[tuple] = set()

    for r in matched:
        aid = str(r["album_id"])
        cand = cand_by.get(aid)
        if cand is None:
            continue
        from_acts = frozenset(_fold(a) for a in cand["artists"])
        for typ, items in (r["relationships"] or {}).items():
            if not isinstance(items, list):
                continue
            for raw in items:
                if "—" not in (raw or ""):
                    continue
                other_artist, other_title = raw.split("—", 1)
                ft, fa = _fold(other_title), _fold(other_artist)
                if not ft or not fa:
                    continue
                for target in track_index.get(ft, ()):
                    if target["album_id"] == aid:
                        continue  # same album: not an inter-album edge
                    meta = album_index.get(target["album_id"])
                    if meta is None or len(meta["artists"]) > LINEAGE_MAX_TARGET_ARTISTS:
                        continue
                    if fa not in _fold(", ".join(meta["artists"])):
                        continue
                    key = (aid, r["track_title"], typ, ft)
                    if key in seen:
                        break
                    seen.add(key)
                    if from_acts & frozenset(_fold(a) for a in meta["artists"]):
                        same += 1
                    else:
                        cross.append(
                            f"- [{_REL_LABELS.get(typ, typ)}] "
                            f"{_album_label(cand['title'], cand['artists'])} / {r['track_title']}"
                            f" → {_album_label(meta['title'], meta['artists'])} / {target['title']}"
                        )
                    break
    return cross, same


def _genius_graph_section(genius_rows: list[dict], cand_by: dict[str, dict],
                          cat_tracks: list[dict], cat_albums: list[dict]) -> list[str]:
    """The R6 block: shared credits inside the bucket, lineage inside the catalog."""
    if not cand_by:
        return []

    rows = [r for r in genius_rows if str(r["album_id"]) in cand_by]
    matched = [r for r in rows if r["match_status"] == "matched"]
    with_rows = {str(r["album_id"]) for r in rows}
    with_matched = {str(r["album_id"]) for r in matched}

    out = ["## 카탈로그 내부 연결 (Genius 크레딧·관계 파생 — 외부 서비스로는 계산 불가)"]
    out.append(
        f"- 커버리지: 후보 {len(cand_by)}장 중 Genius 조회된 앨범 {len(with_rows)}장"
        f" (그중 크레딧을 인용할 수 있는 매칭 보유 {len(with_matched)}장)."
        " 조회되지 않은 앨범에 대해 '연결이 없다'고 쓰지 말 것 —"
        " 사실의 부재가 아니라 조회의 부재다."
    )
    if not matched:
        out.append("- 매칭된 Genius 행이 없어 이번 회차에 계산할 연결이 없다.")
        out.append("")
        return out

    track_index: dict[str, list[dict]] = {}
    for t in cat_tracks:
        track_index.setdefault(_fold(t["title"]), []).append(
            {"title": t["title"], "album_id": str(t["album_id"])}
        )
    album_index = {
        str(a["album_id"]): {"title": a["title"], "artists": list(a["artists"] or [])}
        for a in cat_albums
    }

    art, tech = _credit_connectors(matched, cand_by)
    cross, same = _lineage_edges(matched, cand_by, track_index, album_index)

    out.append("")
    out.append(f"### 크레딧 연결자 — 창작 (버킷 앨범 ≥{CONNECTOR_MIN_ALBUMS}장 참여 + 서로 다른 팀 ≥2)")
    out.extend(art or ["- 없음 — 이번 버킷의 앨범들은 창작 인력을 공유하지 않는다."])
    if tech:
        out.append("")
        out.append("### 크레딧 연결자 — 믹싱·마스터링 등 후반 (같은 마감을 공유한다는 뜻)")
        out.extend(tech)
    out.append("")
    out.append("(스튜디오 같은 장소 역할과 뮤직비디오 크루는 위 두 목록에서 제외했다.)")
    out.append("")
    out.append("### 카탈로그 내부 혈통 (샘플·인터폴레이션·커버의 반대편을 우리가 보유)")
    if cross:
        out.extend(cross[:LINEAGE_MAX])
        if len(cross) > LINEAGE_MAX:
            out.append(f"- … 외 {len(cross) - LINEAGE_MAX}건 (길이 제한으로 생략)")
    else:
        out.append("- 없음 (다른 팀으로 이어지는 간선 기준).")
    if same:
        out.append(
            f"- 같은 팀 내부 간선 {same}건은 생략 — 대부분 리믹스반·라이브반·디럭스 같은 발매 포장이다."
        )
    out.append("")
    return out


def export_bucket_context(conn) -> str:
    """Assemble the compact, read-only 버킷 컨텍스트 block (the grounding spine)."""
    rows = _fetch_all(conn, UNWRITTEN_SQL)
    research = _fetch_all(conn, RESEARCH_SQL)
    recency = _fetch_all(conn, RECENCY_SQL)
    reviewed = _fetch_all(conn, REVIEWED_SQL)
    genius = _fetch_all(conn, GENIUS_SQL)
    cat_tracks = _fetch_all(conn, CATALOG_TRACK_SQL)
    cat_albums = _fetch_all(conn, CATALOG_ALBUM_SQL)

    reviewed_ids = {str(r["album_id"]) for r in reviewed}

    # done-note excerpt per album (newest first, capped to bound the prompt)
    research_ids = {str(r["album_id"]) for r in research}
    research_md: dict[str, str] = {}
    for r in research:
        aid = str(r["album_id"])
        if aid not in research_md and len(research_md) < MAX_RESEARCH_EXCERPTS:
            research_md[aid] = r["result_md"]

    recency_by: dict[str, dict] = {str(r["album_id"]): r for r in recency}

    # candidates = unwritten bucket items, DEDUPED by album_id (an album in two
    # buckets is one writing subject), minus anything already reviewed (exclusion).
    cand_by: dict[str, dict] = {}
    for row in rows:
        aid = str(row["album_id"])
        if aid in reviewed_ids:
            continue  # belt-and-suspenders: never re-pitch a reviewed album
        c = cand_by.get(aid)
        if c is None:
            c = {
                "album_id": aid,
                "title": row["title"],
                "release_date": row["release_date"],
                "artists": list(row.get("artists") or []),
                "genres": list(row.get("genres") or []),
                "best_new": row.get("best_new"),
                "buckets": [],
                "notes": [],
                "rec_reasons": [],
            }
            cand_by[aid] = c
        if not any(b["name"] == row["bucket_name"] for b in c["buckets"]):
            c["buckets"].append({
                "name": row["bucket_name"],
                "research_mode": row.get("research_mode"),
                "is_done": row.get("bucket_is_done"),
            })
        note = (row.get("note") or "").strip()
        if note and note not in c["notes"]:
            c["notes"].append(note)
        reason = (row.get("rec_reason") or "").strip()
        if reason and reason not in c["rec_reasons"]:
            c["rec_reasons"].append(reason)

    candidates = list(cand_by.values())  # insertion order follows bucket/item position
    for c in candidates:
        c["research_md"] = research_md.get(c["album_id"])
        rec = recency_by.get(c["album_id"])
        if rec:
            c["last_played"] = rec["last_played"]
            c["plays_recent"] = rec["plays_recent"]

    # genre / artist clusters over DISTINCT bucketed albums
    genre_count: dict[str, list[str]] = {}
    artist_count: dict[str, list[str]] = {}
    for c in candidates:
        for g in c["genres"]:
            genre_count.setdefault(g, []).append(c["title"])
        for ar in c["artists"]:
            artist_count.setdefault(ar, []).append(c["title"])

    def _clusters(d: dict[str, list[str]]) -> list[str]:
        lines = []
        for name, titles in sorted(d.items(), key=lambda kv: -len(kv[1])):
            if len(titles) >= CLUSTER_MIN:
                lines.append(f"- {name}: {len(titles)}장 — {', '.join(titles[:6])}")
        return lines

    n_research = sum(1 for c in candidates if c.get("research_md"))
    n_recent = sum(1 for c in candidates if c.get("plays_recent"))
    n_buckets = len({b["name"] for c in candidates for b in c["buckets"]})
    # done notes that belong to actual candidates but weren't excerpted (cap overflow)
    cand_research_ids = {c["album_id"] for c in candidates if c["album_id"] in research_ids}
    extra_notes = max(0, len(cand_research_ids) - n_research)

    parts: list[str] = []
    parts.append(f"# 버킷 컨텍스트 (read-only export, {date.today().isoformat()})\n")
    parts.append("## 요약")
    parts.append(f"- 미작성 버킷 앨범(중복 제거): {len(candidates)}개 (버킷 {n_buckets}개)")
    parts.append(
        f"- done 리서치 노트: {n_research}개 본문 발췌"
        + (f" (+{extra_notes}개 더 있음, 발췌 생략)" if extra_notes else "")
    )
    parts.append(f"- 최근 {RECENT_DAYS}일 청취된 버킷 앨범: {n_recent}개")
    parts.append(f"- 이미 평론한 앨범(재추천 금지): {len(reviewed)}개\n")

    g_clusters = _clusters(genre_count)
    a_clusters = _clusters(artist_count)
    if g_clusters:
        parts.append(f"## 장르 클러스터 (버킷 내 ≥{CLUSTER_MIN}장)")
        parts.extend(g_clusters)
        parts.append("")
    if a_clusters:
        parts.append(f"## 아티스트 클러스터 (버킷 내 ≥{CLUSTER_MIN}장)")
        parts.extend(a_clusters)
        parts.append("")

    parts.extend(_genius_graph_section(genius, cand_by, cat_tracks, cat_albums))

    parts.append("## 미작성 버킷 앨범 (작성 후보 · 앨범별 1회, 버킷 멤버십 병기)")
    parts.append("형식: [album_id] 제목 — 아티스트 | 장르 | 발매 | 버킷 | 신호\n")
    for c in candidates:
        artists = ", ".join(c["artists"]) or "(미상)"
        genres = ", ".join(c["genres"]) or "(장르 미상)"
        bkts = ", ".join(_bucket_label(b) for b in c["buckets"])
        parts.append(
            f"- [{c['album_id']}] {c['title']} — {artists} | {genres} "
            f"| {_fmt_date(c['release_date'])} | 버킷: {bkts}"
        )
        parts.extend(_signal_lines(c))
    parts.append("")

    if reviewed:
        parts.append("## 이미 평론한 앨범 — 재추천 금지 (제외 집합)")
        for r in reviewed:
            parts.append(f"- [{r['album_id']}] {r['title']} — {r['artists'] or '(미상)'}")
        parts.append("")

    return "\n".join(parts)


# --- claude -p ------------------------------------------------------------
def load_base_prompt() -> str:
    with open(_prompt_path(), encoding="utf-8") as f:
        return f.read()


ADDENDUM = """
---
## 실행 지침 (headless — 사람이 중간에 없음)

이 작업은 무인 실행이다. 위 시스템 프롬프트(editor-buckit-prompt.md)의 규칙을 그대로 따르되:
- 먼저 WebSearch로 현재 비평 대화를 읽어라(넓게 + 아래 버킷의 앨범/아티스트/장르를 중심으로). 참고 링크를 수집하고, 타인의 평가/점수는 의견으로만(출처 링크와 함께) 옮겨라 — 사실로 단정 금지.
- 그다음 아래 "버킷 컨텍스트"만을 근거로 커미션 카드를 작성하라. 모든 카드는 컨텍스트에 실재하는 album_id(또는 버킷에 존재하는 아티스트/장르)에 앵커돼야 한다. 앵커 없는 카드는 무효 — 폐기하라.
- 카드가 적거나 0개인 것이 정답일 수 있다. 버킷이 얇으면 솔직히 말하고, 이미 버킷에 있는 앨범을 그냥 쓰라고 권하라.
- 너의 응답 전체는 오직 한국어 마크다운 리포트여야 한다(맨 위 헤더 한 줄에 날짜 {today}와 prompt 버전 {version} 포함). 서문/맺음말("Here is…" 등) 금지.

# 버킷 컨텍스트
{context}
"""


def build_prompt(base: str, context: str) -> str:
    return base + ADDENDUM.format(
        today=date.today().isoformat(), version=PROMPT_VERSION, context=context
    )


# P4 cutover (FEAT-multi-user-accounts-p4-llmengine): argv byte-parity with
# the previous inline subprocess call is pinned by shared_db
# tests/test_llm_engine.py::test_golden_argv_editor_buckit. No metering
# session_factory — this script never wrote llm_usage (its DB conn is
# read-only by design); wiring metering is a separate decision.
ENGINE = CliEngine()


def run_claude(prompt: str) -> dict:
    """Run headless Claude Code via CliEngine; return {result, tokens_in,
    tokens_out, search_count, model}. Raises LLMTransientError /
    LLMValidationError (previously RuntimeError — equally fatal to this
    manual single-fire run).

    search_count: LLMResult does not surface `usage.server_tool_use`, so this
    now always records 0 — same documented delta as the research_poller
    cutover (the CLI aggregate was already unreliable, 2026-06-11); the links
    inside the report remain the real grounding evidence. tokens_in stays
    cache-inclusive (an order-of-magnitude audit field, not a bill — $0 on
    the subscription).
    """
    res = coordinated_run(ENGINE, LLMJob(
        feature="editor_buckit",
        prompt=prompt,
        model=CLAUDE_MODEL,
        tools=ToolPolicy(allowed=("WebSearch", "WebFetch")),
        output_mode="json",
        timeout_s=CLAUDE_TIMEOUT_S,
    ), feature="editor_buckit")
    return {
        "result": res.result,
        "tokens_in": res.tokens_in,
        "tokens_out": res.tokens_out,
        "search_count": 0,
        "model": res.model or CLAUDE_MODEL,
    }


# --- report ---------------------------------------------------------------
def write_report(text: str) -> str:
    out_dir = _output_dir()
    os.makedirs(out_dir, exist_ok=True)
    today = date.today().isoformat()
    path = os.path.join(out_dir, f"{today}.md")
    n = 2
    while os.path.exists(path):  # don't clobber an earlier same-day report
        path = os.path.join(out_dir, f"{today}-{n}.md")
        n += 1
    with open(path, "w", encoding="utf-8") as f:
        f.write(text if text.endswith("\n") else text + "\n")
    return path


# --- orchestration --------------------------------------------------------
def main() -> None:
    ap = argparse.ArgumentParser(description="$0 editorial commissioning desk (Stage 0).")
    ap.add_argument("--dry-run", action="store_true",
                    help="assemble + print the bucket context and exit; do NOT call claude")
    args = ap.parse_args()

    conn = connect()
    try:
        context = export_bucket_context(conn)
    finally:
        conn.close()

    if args.dry_run:
        log.info("dry-run: assembled context = %d chars; not calling claude", len(context))
        sys.stdout.write(context + "\n")
        return

    base = load_base_prompt()
    prompt = build_prompt(base, context)
    log.info("prompt assembled: %d chars (context %d) — running claude -p (model=%s)…",
             len(prompt), len(context), CLAUDE_MODEL)
    t0 = time.monotonic()
    res = run_claude(prompt)
    dt = time.monotonic() - t0
    path = write_report(res["result"])
    log.info(
        "report written: %s — %.1fs, %d chars, tokens_in=%d tokens_out=%d web=%d model=%s",
        path, dt, len(res["result"]), res["tokens_in"], res["tokens_out"],
        res["search_count"], res["model"],
    )


if __name__ == "__main__":
    main()
