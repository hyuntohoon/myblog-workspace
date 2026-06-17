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
  * The DB session is forced READ ONLY (`SET default_transaction_read_only`) and
    runs autocommit SELECTs only — this script can NOT write to prod
    (reference-database-url-psql). Dropped vs the poller: the claim-gate/queue,
    the launchd loop, and ALL DB writeback (no UPDATE/INSERT anywhere).
  * Never logs DATABASE_URL / secrets. The model gets `--allowed-tools
    WebSearch,WebFetch` only (no Bash/Edit) — a headless run can't touch the repo.

RFC: docs/rfcs/FEAT-editor-buckit.md (Stage 0, Step 1).
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import subprocess
import sys
import time
from datetime import date

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    stream=sys.stderr,
)
log = logging.getLogger("editor_buckit")

# --- config ---------------------------------------------------------------
REGION = "ap-northeast-2"
SECRET_ID = "myblog/backend"          # holds DATABASE_URL
PROMPT_VERSION = "v1"                  # surfaced in the report header (OQ6)
PROMPT_FILE = "editor-buckit-prompt.md"  # canonical prompt, read live (no vendored copy in Stage 0)
CLAUDE_MODEL = "opus"                  # same bench winner as the research path
CLAUDE_TIMEOUT_S = 1200                # broad web read + many albums ⇒ longer than one research run
RESEARCH_EXCERPT_CHARS = 600          # per done-note excerpt cap (bounds the prompt)
MAX_RESEARCH_EXCERPTS = 30            # cap research notes embedded; log when more exist
RECENT_DAYS = 30                      # play-event recency window
CLUSTER_MIN = 2                       # a genre/artist is a "cluster" at >= this many bucketed albums


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
    """Read prod DATABASE_URL from Secrets Manager and normalize for psycopg."""
    import boto3

    sm = boto3.client("secretsmanager", region_name=REGION)
    secret = json.loads(sm.get_secret_value(SecretId=SECRET_ID)["SecretString"])
    # SQLAlchemy form `postgresql+psycopg://` -> libpq form psycopg.connect wants.
    return secret["DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://", 1)


def connect():
    import psycopg
    from psycopg.rows import dict_row

    # connect_timeout=30 absorbs Neon cold-start (reference-database-url-psql).
    conn = psycopg.connect(database_url(), connect_timeout=30, row_factory=dict_row)
    # This tool is strictly read-only. Force it at the session level so any
    # accidental write raises instead of mutating prod, then run SELECTs autocommit.
    conn.execute("SET default_transaction_read_only = on")
    conn.commit()
    conn.autocommit = True
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


def export_bucket_context(conn) -> str:
    """Assemble the compact, read-only 버킷 컨텍스트 block (the grounding spine)."""
    rows = _fetch_all(conn, UNWRITTEN_SQL)
    research = _fetch_all(conn, RESEARCH_SQL)
    recency = _fetch_all(conn, RECENCY_SQL)
    reviewed = _fetch_all(conn, REVIEWED_SQL)

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


def run_claude(prompt: str) -> dict:
    """Run headless Claude Code; return parsed {result, tokens_in, tokens_out,
    search_count, model}. Raises on non-zero exit, timeout, JSON/parse failure,
    or an `is_error` result. (Lifted from research_poller.py — same JSON path.)"""
    proc = subprocess.run(
        [
            "claude", "-p",
            "--output-format", "json",
            "--allowed-tools", "WebSearch,WebFetch",
            "--model", CLAUDE_MODEL,
        ],
        input=prompt,
        capture_output=True,
        text=True,
        timeout=CLAUDE_TIMEOUT_S,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"claude exit {proc.returncode}: {proc.stderr.strip()[:500]}")
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"claude JSON parse failed: {e}; stdout head: {proc.stdout[:300]!r}")
    if data.get("is_error"):
        raise RuntimeError(f"claude reported error: {str(data.get('result'))[:500]}")
    result = (data.get("result") or "").strip()
    if not result:
        raise RuntimeError("claude returned an empty result")

    usage = data.get("usage", {}) or {}
    tools = usage.get("server_tool_use", {}) or {}
    search_count = (tools.get("web_search_requests") or 0) + (tools.get("web_fetch_requests") or 0)
    tokens_in = (
        (usage.get("input_tokens") or 0)
        + (usage.get("cache_read_input_tokens") or 0)
        + (usage.get("cache_creation_input_tokens") or 0)
    )
    tokens_out = usage.get("output_tokens") or 0
    model_usage = data.get("modelUsage", {}) or {}
    model = max(model_usage, key=lambda k: model_usage[k].get("outputTokens", 0), default=None) \
        or CLAUDE_MODEL
    return {
        "result": result,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "search_count": search_count,
        "model": model,
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
