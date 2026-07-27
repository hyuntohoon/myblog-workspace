#!/usr/bin/env python3
"""FEAT-editor-buckit Stage 1 — the $0 nightly memo → review-draft runner.

Turns each **checked** bucket memo ("오늘 밤 키우기" = `review_bucket_items.prep_tonight`)
into a complete Korean **review draft** (readable prose) under `docs/buckit/<YYYY-MM-DD>/`,
run unattended overnight on the owner's Max subscription via headless Claude Code (`claude -p`)
= **$0**. It is the Stage-1 sibling of `scripts/editor_buckit.py` (Stage 0) and clones its
read-only prod-export + `claude -p` heritage.

The output is a **full review draft** the editor wakes to, edits, and publishes manually (see
docs/editorial/buckit-nightly.md, v0.2): it develops the editor's own judgment into prose, may
choose a **provisional controlling idea** from the memo, and marks missing evidence inline as
`[근거 보강 필요: 트랙/구간]` — it never fabricates the editor's facts, emotions, or experiences (★).
**Every checked memo gets a draft (2026-07-26).** A memo carrying no viewpoint no longer yields a
`초안 생성 보류` note; the draft is written anyway, on a provisional controlling idea drawn from the
research note and flagged as provisional. The model is also barred from grading the research note
("충분/얇다") anywhere in its output. **Zero drafts is now a failed run, not a valid one.** Rationale:
the hold fired on 13 of 14 completed runs and its stated reasons were assertions about a note the
model had only seen a truncated, newline-flattened 1,500-char slice of. The job writes files and nothing
else — no DB write, no git, no publish (Stage 2's draft delivery uses the authed API).

    myblog_backend/.venv/bin/python scripts/buckit_nightly.py            # full nightly run
    myblog_backend/.venv/bin/python scripts/buckit_nightly.py --dry-run  # print the assembled
        #   checked-memo context + the resolved claude argv, then exit WITHOUT calling claude

Architecture / safety (RFC Stage 1, Step 4) — hardened after an adversarial tool-scope audit
(2026-06-18) that proved the earlier "agentic claude writes the files" design both BROKE the
feature (scoped `Write(docs/buckit/**)` is denied in headless `-p` on CLI 2.1.181 ⇒ zero files
written) AND opened a secret-exfiltration surface (an unscoped `Read` + unrestricted `WebFetch`
could read `~/.aws`/`~/.claude` creds and exfiltrate, driven by a prompt-injection in the memo
text). So this runner reverts to the proven Stage-0 mechanical pattern:

  * **This script** does the entire DB read **read-only**: `connect()` sets `conn.read_only`
    (TRANSACTION-scoped — a session `SET default_transaction_read_only = on` would LEAK through
    Neon's pgbouncer `-pooler` and make a later writer fail read-only; see connect()). There is NO
    raw DB write anywhere in this file; the only prod writes are Step 7's authed-API draft create +
    memo grow (below). It reads the `prep_tonight`-checked, unwritten, not-yet-reviewed bucket items
    (+ their verbatim `note`, album/artist/genre facts, done research-note excerpts, recent listens).
  * **This script also reads the rule docs and writes the draft files** — i.e. the
    "repo read + file write + Postgres read" capabilities all live in the script, validated.
    Output filenames are reduced to a safe basename under `docs/buckit/<date>/` — the model
    cannot cause a path escape.
  * **claude -p is a pure text transformer with NO tools.** The three rule docs + the
    read-only context block are inlined into the prompt; `--disallowed-tools` denies the full
    file/network/exec surface (Bash/Edit/Read/Write/WebSearch/WebFetch/…) and
    `--setting-sources user` keeps the broad project-local Bash allow-list out of the run.
    The model only generates the Korean review drafts as a delimited payload and returns it; it
    has no DB tool, no file tool, no network tool ⇒ structurally incapable of touching prod,
    git, the filesystem, or the network.
  * The **checkbox is the only gate**: if zero memos are checked, this script writes a
    `_summary.md` saying so and exits WITHOUT calling claude (a blind nightly timer would
    manufacture stale ideas — the checkbox is what makes the timer non-blind; see the RFC
    Decisions log 2026-06-18).
  * Never logs DATABASE_URL / secrets.

Stage 2 Step 7 — in-app draft delivery (default ON; `--no-draft` opts out). After the draft
files are written, the script ALSO creates one **draft** post per memo so the review draft lands
in the `/write` '임시 저장함' inbox, not only a `docs/buckit/` file (owner decision 2026-06-18):

  * It mints a short-lived Cognito JWT for the **nightly draft agent** (`USER_AUTH`, password from
    SSM `/myblog/nightly-agent`; the `scripts/smoke.py get_token` pattern) and calls
    `POST /api/posts {status:'draft', …}` on the raw API Gateway. The password and the token are
    NEVER logged. FIX-nightly-draft-identity Phase A: this identity is **not** owner-equivalent —
    `require_owner` still rejects it on all 38 owner routes, and `create_post` COERCES its posts to
    `status='draft'` server-side. Draft-only is now enforced by the server, not only by this file.
    No raw DB write (the read-only export connection is untouched; writes go through the authed API).
  * **Owner-scoped input (A-4).** `CHECKED_SQL` filters `b.user_id = OWNER_SUB`. Buckets carry a
    user; `posts` do not; this query used to filter by neither, so a second person's checked memo
    would have become a post on the owner's blog. Foreign checked memos are counted and logged as a
    PHASE-B TRIGGER rather than silently dropped.
  * Provenance (album_id / bucket / date) rides as a leading HTML comment in the draft `body_mdx`,
    NOT `Post.extra` — `WritePostRequest` is `extra='ignore'`, so an `extra` field would be silently
    dropped; the comment keeps this a single-repo, no-contract-change job. The draft carries NO
    `album_ids`, so it does NOT enter `post_albums` (the reviewed-set + this job's own exclusion
    source) — a nightly draft is not yet a published review.
  * Grow-once (server-side since backend #134): after a draft is created the script calls
    `POST /api/buckets/nightly-grow {album_id, post_id}` — the backend stamps the post_id AND
    clears `prep_tonight` on every one of the OWNER's checked items for that album, with the
    acting user pinned server-side from OWNER_SUB (never from the request). The generic item
    PATCH could not do this: it is member-scoped (`provisioned_member_id`) and the agent owns no
    buckets, so it 404'd by design — and forcing it open would have meant resolving the acting
    user from something other than the token, the impersonation path Phase A exists to avoid.
    The `post_id` stamp durably excludes the album next run (CHECKED_SQL filters
    `post_id IS NULL`); the album-unique slug makes any re-POST 409 (rejected, never
    duplicated). Delivery failures keep the files (docs/buckit/ is the backup) but now EXIT
    NON-ZERO — 2 = identity rejected, 3 = token mint / delivery infrastructure, 4 = draft
    created but the memo is still checked (grow failed or a 409-stuck leftover) — because a
    silent delivery skip is exactly how the 2026-07 403 hid for 17 days. The model still has NO
    tools; a prompt-injection in a memo cannot redirect a write,
    because every write target (title, album_id, bucket/item ids) comes from the trusted DB export,
    never from the model's text (which only fills `body_mdx`, a draft that is never published).

Note on ordering: memos are processed in bucket/item position order (review_bucket_items has
no checked-at timestamp), so run-spec §6's "newest-checked first" recency hint is intentionally
not honored — the order is deterministic instead.

RFC: docs/archive/done/rfcs/FEAT-editor-buckit.md (Stage 1, Step 4; archived 2026-06-18).
Run spec inlined into the prompt: docs/editorial/buckit-nightly-run.md.
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
import urllib.error
import urllib.request
from datetime import date

# shared_db is read from the LOCAL checkout via src-path injection (not the git
# pin) — same pattern as research_poller (P4 cutover #1). Resolves relative to
# this script so it works from the launchd runtime (workspace main checkout).
sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "myblog_shared_db", "src"))

from myblog_shared_db.llm import CliEngine, LLMJob, ToolPolicy, build_argv  # noqa: E402
from myblog_shared_db.llm.exceptions import LLMTransientError  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    stream=sys.stderr,
)
log = logging.getLogger("buckit_nightly")

# --- config ---------------------------------------------------------------
REGION = "ap-northeast-2"
SECRET_ID = "/myblog/backend"           # SSM SecureString param (holds DATABASE_URL)
RUN_SPEC_FILE = "buckit-nightly-run.md"  # the run spec (entry point), inlined as the base prompt
# Conversion + method rule docs inlined into the prompt (the model has no Read tool). The model
# inherits buckit-nightly.md §3 four rules + review-critique-method.md ★ honesty / §6 language.
INLINE_RULE_FILES = ("buckit-nightly.md", "review-critique-method.md")
CLAUDE_MODEL = "opus"                   # same bench winner as the research / Stage-0 paths
CLAUDE_TIMEOUT_S = 1800                 # multi-memo Korean generation ⇒ longer than a single research run
# The research note is passed WHOLE (2026-07-26). It used to be head-sliced to 1,500 chars and
# newline-flattened, so the drafter never saw any section past the note's opening — including
# 샘플링/기반, the section the research prompt itself marks ★최우선, and 각도, which is where the
# note seeds a viewpoint. Stored notes run 4.3k–9.8k chars and only a handful of memos are ever
# checked per night, so whole notes fit comfortably. No per-note cap now: the assembled prompt
# size is logged every run, and an abnormally large one is a WARNING rather than silent loss.
PROMPT_SIZE_WARN_CHARS = 400_000        # pathological only; log it, never truncate the note
RECENT_DAYS = 30                        # play-event recency window
# claude tool scope — the model is a PURE TEXT TRANSFORMER. It gets NO tools: rule docs +
# context are inlined; the script does all DB read + file write. We disallow the full
# file/network/exec surface as belt-and-suspenders so even a default-on tool can't fire, and
# pin setting-sources so the project-local broad Bash allow-list is never merged in.
DISALLOWED_TOOLS = ("Bash", "Edit", "Read", "Write", "WebSearch", "WebFetch",
                    "Glob", "Grep", "NotebookEdit", "Task", "TodoWrite")
SETTING_SOURCES = "user"
# Output framing: the model emits each file as `<DELIM> <basename>` on its own line, then the
# file body, until the next delimiter. The script splits, validates the basename, and writes.
FILE_DELIM = "=====BUCKIT_FILE:"
FILE_DELIM_RE = re.compile(r"^=====BUCKIT_FILE:\s*(.+?)\s*=*\s*$", re.MULTILINE)

# --- Stage 2 Step 7: in-app draft delivery (authed API; the script is the only writer) ---
BACKEND_AUTHED = "https://ld8pjw3mx4.execute-api.ap-northeast-2.amazonaws.com"  # raw API Gateway
# FIX-nightly-draft-identity Phase A: the job's own identity, not the smoke/test user.
# The backend admits this sub via require_owner_or_draft_agent on POST /api/posts only,
# and coerces its posts to status='draft' — it is not owner-equivalent.
AGENT_SECRET_ID = "/myblog/nightly-agent"   # SSM SecureString (NIGHTLY_AGENT_EMAIL/_PASSWORD)
COGNITO_REGION = "ap-northeast-2"
COGNITO_CLIENT_ID = "68ccmcanfbvla9qbovnb9b18bt"
DEFAULT_AGENT_EMAIL = "nightly-agent@ratemymusic.blog"
DRAFT_SECTION = "Reviews"               # seeded section (reject-unknown); the nightly draft posts here
HTTP_TIMEOUT_S = 30
BODY_MDX_MAX = 32000                     # cap the model's draft before POST (oversize ⇒ 4xx re-fail)


# --- paths ----------------------------------------------------------------
def _repo_root() -> str:
    # scripts/ sits at the workspace repo root.
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _editorial_dir() -> str:
    return os.path.join(_repo_root(), "docs", "editorial")


def _output_reldir() -> str:
    return os.path.join("docs", "buckit", date.today().isoformat())


def _output_dir() -> str:
    return os.path.join(_repo_root(), _output_reldir())


# --- secrets / db ---------------------------------------------------------
def database_url() -> str:
    """Read prod DATABASE_URL from Secrets Manager and normalize for psycopg."""
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
    # Read-only safety, TRANSACTION-SCOPED — NOT a session SET. A session-level
    # `SET default_transaction_read_only = on` LEAKS through Neon's pgbouncer (`-pooler`) onto the
    # shared server connection, so the NEXT writer on that pooled backend — this job's own
    # POST /api/posts in Step 7, or the live backend Lambda serving real users — fails with
    # "cannot execute INSERT in a read-only transaction" (root-caused in Step 7 verification).
    # `conn.read_only` makes psycopg apply READ ONLY per transaction (auto-cleared on commit/
    # rollback), so the export stays write-safe without ever poisoning the pool. autocommit stays
    # False ⇒ the export's SELECTs share one read-only tx, rolled back on close().
    conn.read_only = True
    return conn


# --- read-only context export --------------------------------------------
# Only the CHECKED ("오늘 밤 키우기" = prep_tonight), unwritten (post_id IS NULL),
# not-yet-reviewed (album_id NOT IN post_albums) items. An album checked in two buckets
# is one writing subject ⇒ dedupe by album_id, merging its notes.
CHECKED_SQL = """
SELECT
    i.album_id,
    i.id                    AS item_id,
    i.bucket_id,
    i.note,
    i.rec_reason,
    i.status::text          AS item_status,
    i.prep_tonight,
    b.name                  AS bucket_name,
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
WHERE i.prep_tonight = true
  AND i.post_id IS NULL
  AND i.album_id NOT IN (SELECT album_id FROM post_albums)
  AND b.user_id = %(owner_sub)s
ORDER BY b.position, i.position;
"""

# FIX-nightly-draft-identity A-4. Buckets carry `user_id`; `posts` carry no user column at
# all; this query used to filter by neither. So a second person checking a memo would have
# produced a post on the OWNER's blog — dormant only because one person uses buckets, and
# `users` already holds 4 rows with self-signup enabled. Scoping here makes that unreachable
# rather than merely documented: a foreign memo is simply not selected.
#
# `review_buckets.user_id` stores the Cognito sub directly, so this needs no join.
#
# Counted, not silently dropped. A silently ignored memo is how this bug class hides; the
# count below is the mechanical trigger for Phase B (multi-user), per the RFC.
OWNER_SUB = "0468fd3c-2011-70f5-0681-b852ddaade41"

FOREIGN_CHECKED_SQL = """
SELECT count(*) AS n, count(DISTINCT b.user_id) AS users
FROM review_bucket_items i
JOIN review_buckets b ON b.id = i.bucket_id
WHERE i.prep_tonight = true
  AND i.post_id IS NULL
  AND b.user_id <> %(owner_sub)s;
"""

# The candidate subqueries below mirror CHECKED_SQL's owner scope (A-4). They cannot leak —
# their results only ever attach to memos CHECKED_SQL exported — but reading foreign users'
# checked rows for nothing is exactly the kind of drift the owner filter exists to prevent.
RESEARCH_SQL = """
SELECT album_id, result_md, finished_at
FROM album_research
WHERE status = 'done' AND result_md IS NOT NULL
  AND album_id IN (
        SELECT i.album_id FROM review_bucket_items i
        JOIN review_buckets b ON b.id = i.bucket_id
        WHERE i.prep_tonight = true AND i.post_id IS NULL
          AND b.user_id = %(owner_sub)s
  )
ORDER BY finished_at DESC NULLS LAST;
"""

RECENCY_SQL = f"""
SELECT album_id,
       max(played_at)                                                       AS last_played,
       count(*) FILTER (WHERE played_at > now() - INTERVAL '{RECENT_DAYS} days') AS plays_recent
FROM spotify_play_events
WHERE album_id IN (
        SELECT i.album_id FROM review_bucket_items i
        JOIN review_buckets b ON b.id = i.bucket_id
        WHERE i.prep_tonight = true AND i.post_id IS NULL
          AND b.user_id = %(owner_sub)s
  )
GROUP BY album_id;
"""


def _fetch_all(conn, sql, params=None):
    with conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def _fmt_date(d) -> str:
    if d is None:
        return "?"
    try:
        return d.date().isoformat()  # datetime -> YYYY-MM-DD
    except AttributeError:
        return d.isoformat()         # already a date


def _slug(title: str, artists: list[str]) -> str:
    """Filename-safe slug from artist + title. ASCII-fold where possible; keep Hangul.
    Falls back to a short id so two distinct albums never collide on an empty slug."""
    base = f"{artists[0]}-{title}" if artists else (title or "memo")
    base = unicodedata.normalize("NFKC", base)
    # keep word chars (incl. Hangul/CJK via \w under re.UNICODE) + spaces/hyphens; drop the rest
    base = re.sub(r"[^\w\s-]", "", base, flags=re.UNICODE)
    base = re.sub(r"[\s_]+", "-", base).strip("-").lower()
    return base[:60] or "memo"


def _research_block(md: str | None) -> str:
    """The album's research note, whole and with its markdown intact.

    Emitted as a delimited block instead of a bullet value. The note carries its own `## `
    headers, so the previous behaviour — flatten newlines, slice the head, inline it after
    `- AI 리서치 노트:` — collapsed a multi-section document into one unstructured run of text
    and dropped everything after the first section. The delimiters exist so the model does not
    mistake the note's own headers for this context block's structure.
    """
    if not md:
        return "- AI 리서치 노트: 없음"
    return (
        "- AI 리서치 노트(사실 — **전문**). 아래 두 구분선 사이가 노트다. 그 안의 `##` 제목은\n"
        "  노트 자신의 목차이지 이 컨텍스트 블록의 구조가 아니다:\n\n"
        "<<<리서치_노트_시작>>>\n"
        f"{md.strip()}\n"
        "<<<리서치_노트_끝>>>\n"
    )


def _listen_line(rec: dict | None) -> str:
    if not rec:
        return "기록 없음"
    last = rec.get("last_played")
    recent = rec.get("plays_recent") or 0
    if last and recent:
        return f"최근 {RECENT_DAYS}일 {recent}회, 마지막 {_fmt_date(last)}"
    if last:
        return f"최근 {RECENT_DAYS}일 0회 (휴면), 마지막 {_fmt_date(last)}"
    return "기록 없음"


def export_checked_memos(conn) -> tuple[list[dict], str]:
    """Assemble the read-only context block for every CHECKED memo.

    Returns (memos, context_markdown). The block IS the model's §3 input — it carries
    the verbatim memo (viewpoint), album facts, the done research note (facts), and recent
    listens, plus a suggested output filename per memo. The model gets no DB tool."""
    rows = _fetch_all(conn, CHECKED_SQL, {"owner_sub": OWNER_SUB})
    # Count what the owner-scope filter above excluded. Non-zero here is the RFC's Phase B
    # trigger: somebody other than the owner is using the nightly pipeline, and posts still
    # have no user column to land in.
    foreign = _fetch_all(conn, FOREIGN_CHECKED_SQL, {"owner_sub": OWNER_SUB})[0]
    if foreign["n"]:
        log.warning(
            "PHASE-B TRIGGER: %d checked memo(s) from %d non-owner user(s) were SKIPPED — "
            "posts have no user column, so drafting them would publish someone else's memo to "
            "the owner's blog. See docs/rfcs/FIX-nightly-draft-identity.md §4.",
            foreign["n"], foreign["users"],
        )
    research = _fetch_all(conn, RESEARCH_SQL, {"owner_sub": OWNER_SUB})
    recency = _fetch_all(conn, RECENCY_SQL, {"owner_sub": OWNER_SUB})

    research_md: dict[str, str] = {}
    for r in research:  # newest finished_at first ⇒ keep the freshest note per album
        aid = str(r["album_id"])
        research_md.setdefault(aid, r["result_md"])
    recency_by = {str(r["album_id"]): r for r in recency}

    # dedupe checked items by album_id (an album checked in two buckets is one subject)
    memo_by: dict[str, dict] = {}
    for row in rows:
        aid = str(row["album_id"])
        m = memo_by.get(aid)
        if m is None:
            m = {
                "album_id": aid,
                "title": row["title"],
                "release_date": row["release_date"],
                "album_type": row.get("album_type"),
                "total_tracks": row.get("total_tracks"),
                "label": row.get("label"),
                "best_new": row.get("best_new"),
                "artists": list(row.get("artists") or []),
                "genres": list(row.get("genres") or []),
                "buckets": [],
                "items": [],
                "notes": [],
                "rec_reasons": [],
            }
            memo_by[aid] = m
        if row["bucket_name"] not in m["buckets"]:
            m["buckets"].append(row["bucket_name"])
        item_ref = {"bucket_id": str(row["bucket_id"]), "item_id": str(row["item_id"])}
        if item_ref not in m["items"]:  # every checked item for this album → unchecked on grow
            m["items"].append(item_ref)
        note = (row.get("note") or "").strip()
        if note and note not in m["notes"]:
            m["notes"].append(note)
        reason = (row.get("rec_reason") or "").strip()
        if reason and reason not in m["rec_reasons"]:
            m["rec_reasons"].append(reason)

    memos = list(memo_by.values())
    used_slugs: set[str] = set()
    for m in memos:
        slug = _slug(m["title"], m["artists"])
        cand, n = slug, 2
        while cand in used_slugs:  # disambiguate slug collisions deterministically
            cand = f"{slug}-{n}"
            n += 1
        used_slugs.add(cand)
        m["slug"] = cand
        m["research_md"] = research_md.get(m["album_id"])
        m["listen"] = _listen_line(recency_by.get(m["album_id"]))

    today = date.today().isoformat()
    parts: list[str] = []
    parts.append(f"# 오늘 밤 키울 메모 (read-only export, {today})\n")
    parts.append(
        "> 이 블록이 run spec §3의 입력이다. **너에겐 DB 접근 권한도, 어떤 도구도 없다** — "
        "아래에 제공된 사실만 사용하고, 없는 것은 지어내지 말고 빈칸으로 둬라(★)."
    )
    parts.append(f"> 체크된 메모: **{len(memos)}개**. 메모마다 독립 파일 1개 + 마지막에 _summary.md.\n")

    for idx, m in enumerate(memos, 1):
        artists = ", ".join(m["artists"]) or "(미상)"
        genres = ", ".join(m["genres"]) or "(장르 미상)"
        buckets = ", ".join(m["buckets"]) or "(버킷 미상)"
        parts.append(f"## 메모 {idx} — [{m['album_id']}] {m['title']} — {artists}")
        parts.append(f"- 출력 파일명(제안): `{m['slug']}.md`")
        parts.append(
            f"- 앨범 사실: 장르 {genres} · 발매 {_fmt_date(m['release_date'])} · "
            f"구분 {m.get('album_type') or '?'} · 트랙 {m.get('total_tracks') if m.get('total_tracks') is not None else '?'} · "
            f"레이블 {m.get('label') or '?'}{' · BNM' if m.get('best_new') else ''}"
        )
        parts.append(f"- 버킷: {buckets}")
        if m["notes"]:
            parts.append("- 던진 메모(원본 — 한 글자도 고치지 말 것):")
            for note in m["notes"]:
                quoted = note.replace("\n", "\n  > ")
                parts.append(f"  > {quoted}")
        else:
            parts.append("- 던진 메모(원본): (비어 있음 — 판단 씨앗 없음일 수 있다, §4)")
        if m["rec_reasons"]:
            # a system tag (신보/인기), NOT an editorial viewpoint — label it as such so the
            # model never mistakes it for a judgment seed (run spec: memo is the only viewpoint).
            parts.append("- 시스템 추천 태그(사실, 판단 아님): " + " / ".join(m["rec_reasons"]))
        parts.append(_research_block(m["research_md"]))
        parts.append(f"- 청취 기록: {m['listen']}")
        parts.append("")

    return memos, "\n".join(parts)


# --- prompt assembly ------------------------------------------------------
def _rule_path(name: str) -> str:
    return os.path.join(_editorial_dir(), name)


def missing_rule_files() -> list[str]:
    return [n for n in (RUN_SPEC_FILE, *INLINE_RULE_FILES) if not os.path.exists(_rule_path(n))]


def _read_doc(name: str) -> str:
    with open(_rule_path(name), encoding="utf-8") as f:
        return f.read()


ADDENDUM = """
---
## 실행 지침 (headless — 사람이 중간에 없음, 도구 없음)

이 작업은 무인 야간 실행이다. 위 run spec + 인라인 규칙(buckit-nightly.md, review-critique-method.md)을
그대로 따르되:

- **너에겐 어떤 도구도 없다.** DB도 파일도 웹도 접근 못 한다. 규칙은 위에 인라인으로 다 들어 있고,
  입력은 아래 "오늘 밤 키울 메모" 블록이 전부다. 블록에 없는 사실/가사/크레딧/날짜는 지어내지 말고
  `[근거 보강 필요: 트랙/구간]`(출처 미상이면 `[source?]`)로 본문 안에 표시해라(★). 파일을 직접
  쓰려 하지 말 것 — 아래 형식으로 텍스트만 반환하면 스크립트가 파일로 저장한다.
- **출력은 전부 한국어 — 메모마다 완결형 평론 초안(읽히는 산문)이다. 스켈레톤/개요가 아니다.**
  메모에 판단이 있으면 그것을 잠정 controlling idea로 삼아 도입에서 끌고 가며 전개해라. 메모의 결론을
  뒤집지 말 것(전개이지 대체가 아니다, ★). 근거가 비면 `[근거 보강 필요: 트랙/구간]`로 인라인 표시.
  **점수 정당화로 닫지 말고** 비평적 판단·이미지·여운으로 닫아라. 음향 디테일 나열보다 표현·편곡·장르
  맥락·비평 프레이밍을 우선.
  ★ **메모가 얇아도 초안을 쓴다. 보류는 없다.** 메모가 청취 표시("전체곡", "들었다")뿐이어도 완결형
  초안을 낸다 — 이때 잠정 controlling idea는 리서치 노트에서 끌어오고, 도입 한 줄로 "이 각도는 잠정"
  임을 밝혀 편집자가 어디를 갈아끼우면 되는지 알게 해라. 없는 근거는 그 자리에 인라인 표시하는 것이
  전부이고, 그것이 초안을 내지 않을 이유가 되지는 않는다. **0개 출력은 오답이다.**
  ★ **리서치 노트가 충분한지 얕은지 평가하지 말 것.** 초안에도 _summary.md에도 "노트는 충분하다 /
  얇다 / 부족하다" 류의 서술을 쓰지 마라. 아무도 그 판단을 요청하지 않았다. 없는 사실은 없는 자리에
  표시하면 되고, 그것 외에 노트에 대해 보고할 것은 없다. 편집자에게 감정·경험·판단을 지어 붙이는 것
  역시 금지(★) — 노트에서 끌어온 각도는 편집자의 것이 아니라 초안 자신의 읽기로 쓴다.
- **리서치 노트를 적극 활용해 살을 붙여라.** 노트는 사실 확인용이 아니라 글의 '세계'다 — 계보(이전
  앨범/씬), 앨범이 표방한 의도, 구성(막/서사/싱글), 협업자, 실제 맥락을 끌어와 판단을 받쳐라. 메모를
  재나열하지 말 것. 그리고 **칭찬만 늘어놓지 말고 긴장(한계·대가·반론) 하나는 세워** 인상비평을 비평으로
  만들어라(확인 못 할 경험적 주장이면 `[확인 필요]`). **제목을 달고**, 증거는 결정적 순간 1–2개만 깊게
  (트랙 줄세우기 금지), 길이는 재료가 받쳐주는 만큼(채우기 금지).

### 출력 형식 (반드시 이대로 — 이 외 텍스트 금지)

파일마다 아래 구분자 한 줄로 시작하고, 그 다음 줄부터 그 메모의 완결형 한국어 평론 초안(마크다운)을 쓴다:

```
=====BUCKIT_FILE: <파일명.md>=====
<그 메모의 완결형 평론 초안 (마크다운)>
```

- `<파일명.md>` 는 각 메모의 "출력 파일명(제안)"을 그대로 쓴다(예: `frank-ocean-channel-orange.md`). 경로/슬래시 없이 파일명만.
- **메모마다 한 파일. 예외 없다.** 체크된 메모는 전부 초안 파일 하나씩을 낸다. 파일을 안 내는 경우는 없다.
- **맨 마지막 파일은 반드시 `_summary.md`** — 아침에 가장 먼저 여는 인덱스. 초안마다 잠정 controlling idea, 세운 긴장(한계), 보존한 편집자 표현, `[근거 보강 필요]`/`[확인 필요]` 표시를 정리한다. 보류 목록은 없다(보류가 없으므로). 체크된 메모가 아예 0개였던 경우에만 `_summary.md` 하나에 '오늘 체크된 메모 없음'.
- 구분자 줄과 파일 본문 외에 서문/맺음말("Here is…", "아래는…") 절대 금지. 구분자 문자열(`=====BUCKIT_FILE:`)을 본문 안에서 재현하지 말 것.

오늘 날짜 = {today}.

# 오늘 밤 키울 메모
{context}
"""


def build_prompt(context: str) -> str:
    blocks = [_read_doc(RUN_SPEC_FILE)]
    for i, name in enumerate(INLINE_RULE_FILES, 1):
        blocks.append(f"\n\n===== 인라인 규칙 {i}/{len(INLINE_RULE_FILES)}: {name} =====\n")
        blocks.append(_read_doc(name))
    blocks.append(ADDENDUM.format(today=date.today().isoformat(), context=context))
    return "".join(blocks)


# --- claude -p (pure text transform — NO tools; the script writes the files) -----------
# P4 cutover (FEAT-multi-user-accounts-p4-llmengine): argv byte-parity with the
# previous inline subprocess call is pinned by shared_db
# tests/test_llm_engine.py::test_golden_argv_buckit_nightly, and --dry-run still
# prints the exact argv (built by the same build_argv the engine dispatches).
# No metering session_factory — this script never wrote llm_usage.
ENGINE = CliEngine()


def _job(prompt: str) -> LLMJob:
    return LLMJob(
        feature="buckit_nightly",
        prompt=prompt,
        model=CLAUDE_MODEL,
        tools=ToolPolicy(disallowed=DISALLOWED_TOOLS),
        output_mode="json",
        timeout_s=CLAUDE_TIMEOUT_S,
        setting_sources=SETTING_SOURCES,
        cwd=_repo_root(),
    )


def claude_argv() -> list[str]:
    return build_argv(_job(""))


# A transient `claude exit 1` used to cost the entire night: CliEngine only retries when a job
# carries an output_schema (cli_engine.py `attempts = 2 if job.output_schema is not None else 1`),
# and this job has none. That is what happened on 2026-07-26 — one failure at 03:00 and the run
# produced nothing until the next night. The job fires once a day, so retrying is cheap and the
# alternative is a 24-hour gap.
LLM_RETRIES = 3
LLM_RETRY_SLEEP_S = 60


def run_claude_with_retry(prompt: str) -> dict:
    """run_claude, retried on transient engine failures. Validation errors are terminal."""
    last: Exception | None = None
    for attempt in range(1, LLM_RETRIES + 1):
        try:
            return run_claude(prompt)
        except LLMTransientError as e:
            last = e
            if attempt == LLM_RETRIES:
                break
            log.warning("claude attempt %d/%d failed transiently (%s) — retrying in %ds",
                        attempt, LLM_RETRIES, str(e)[:160], LLM_RETRY_SLEEP_S)
            time.sleep(LLM_RETRY_SLEEP_S)
    log.error("claude failed %d/%d attempts — giving up for tonight", LLM_RETRIES, LLM_RETRIES)
    raise last  # type: ignore[misc]


def run_claude(prompt: str) -> dict:
    """Run headless Claude Code as a pure text transformer (NO tools) via shared_db
    CliEngine and return parsed {result, tokens_in, tokens_out, model}. `result` is the
    delimited multi-file payload the caller splits + writes. Raises LLMTransientError /
    LLMValidationError on non-zero exit, timeout, JSON/parse failure, an `is_error`
    result, or an empty result (uncaught in main, same crash-and-log outcome as the
    RuntimeErrors it replaces)."""
    res = ENGINE.run(_job(prompt))
    return {
        "result": res.result,
        "tokens_in": res.tokens_in,
        "tokens_out": res.tokens_out,
        "model": res.model or CLAUDE_MODEL,
    }


# --- output: split the delimited payload + write files (the script is the only writer) ---
def _safe_basename(name: str) -> str | None:
    """Reduce a model-supplied filename to a safe `.md` basename under the output dir.
    Returns None if it can't be made safe (so a junk delimiter is skipped, not written)."""
    base = os.path.basename(name.strip()).strip()
    base = base.lstrip(".")              # no leading-dot/hidden files
    if not base:
        return None
    if not base.endswith(".md"):
        base += ".md"
    if not re.fullmatch(r"[\w.\- ()]+", base, flags=re.UNICODE):  # defensive whitelist
        base = re.sub(r"[^\w.\- ()]", "-", base, flags=re.UNICODE)
    return base or None


def parse_payload(result: str) -> list[tuple[str, str]]:
    """Split the model's delimited payload into [(basename, content), …]. Tolerant of
    stray preamble before the first delimiter (dropped)."""
    matches = list(FILE_DELIM_RE.finditer(result))
    out: list[tuple[str, str]] = []
    for i, mt in enumerate(matches):
        raw_name = mt.group(1)
        start = mt.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(result)
        content = result[start:end].strip("\n")
        base = _safe_basename(raw_name)
        if base and content.strip():
            out.append((base, content))
    return out


def write_files(files: list[tuple[str, str]]) -> list[str]:
    out_dir = _output_dir()
    os.makedirs(out_dir, exist_ok=True)
    written: list[str] = []
    for base, content in files:
        path = os.path.join(out_dir, base)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content if content.endswith("\n") else content + "\n")
        written.append(base)
    return written


def write_summary_only(text: str) -> str:
    """Deterministic _summary.md for the short-circuit paths (zero checked memos / missing
    rule files / unparseable payload). The script is the only writer."""
    out_dir = _output_dir()
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "_summary.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(text if text.endswith("\n") else text + "\n")
    return path


# --- Stage 2 Step 7: mint the draft-agent JWT + deliver each generated draft as a draft post ----
def mint_agent_token() -> str:
    """Mint a short-lived (≈60-min) Cognito access token for the **nightly draft agent** via
    USER_AUTH (2-step), reading its password from SSM `/myblog/nightly-agent`. $0; the password and
    the token are NEVER logged. (scripts/smoke.py get_token pattern.)

    FIX-nightly-draft-identity Phase A. This used to authenticate as the smoke/test user, whose
    docstring claimed the token was "owner-equivalent in this single-user system". That stopped
    being true on 2026-07-08 (backend 392dd50 owner-gated POST /api/posts), and every delivery has
    failed 403 since. The job now has its own identity — nightly-agent@ratemymusic.blog, sub
    64885d4c-00c1-7082-8c40-8cb1a31d8078 — which the backend admits via
    `require_owner_or_draft_agent` on POST /api/posts and the grow-once
    POST /api/buckets/nightly-grow (backend #134), and **nowhere else**.

    Blast radius, and how it is bounded: this identity is NOT owner-equivalent. `require_owner`
    still rejects it on all 38 owner routes, and `create_post` COERCES its posts to status='draft'
    server-side, so it cannot publish even if this script asked it to. The draft-only limit is now
    enforced by the server, not merely by this file — which is the point of the change.

    The env override is dev-only — launchd sets no env var; never set it on the nightly job (a
    plaintext pw in the process env is exposable via `ps e` / crash dumps)."""
    import boto3

    ssm = boto3.client("ssm", region_name=REGION)
    secret = json.loads(ssm.get_parameter(Name=AGENT_SECRET_ID, WithDecryption=True)["Parameter"]["Value"])
    pw = os.environ.get("NIGHTLY_AGENT_PASSWORD") or secret.get("NIGHTLY_AGENT_PASSWORD")
    email = (os.environ.get("NIGHTLY_AGENT_EMAIL")
             or secret.get("NIGHTLY_AGENT_EMAIL") or DEFAULT_AGENT_EMAIL)
    if not pw:
        raise RuntimeError(f"nightly-agent password missing (SSM {AGENT_SECRET_ID})")
    c = boto3.client("cognito-idp", region_name=COGNITO_REGION)
    r = c.initiate_auth(
        AuthFlow="USER_AUTH",
        AuthParameters={"USERNAME": email},
        ClientId=COGNITO_CLIENT_ID,
    )
    r2 = c.respond_to_auth_challenge(
        ClientId=COGNITO_CLIENT_ID,
        ChallengeName="SELECT_CHALLENGE",
        Session=r["Session"],
        ChallengeResponses={"USERNAME": email, "ANSWER": "PASSWORD", "PASSWORD": pw},
    )
    return r2["AuthenticationResult"]["AccessToken"]


def _api(method: str, path: str, token: str, body: dict | None = None) -> tuple[int, dict | None]:
    """One authed JSON request to the raw API Gateway. The Bearer token skips edge_guard; BOTH
    POST /api/posts and POST /api/buckets/nightly-grow are explicit Cognito-authorized routes (the
    agent token passes the API-GW authorizer / the backend's require_cognito_token). Returns
    (status, parsed_body_or_None); **status 0 = a transport error** (DNS/connect/timeout), which the
    caller treats as a non-ok skip — so a Neon/Lambda cold-start at 03:00 can't crash the run.
    The token is NEVER logged; an HTTP error surfaces as its code + a short body."""
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {token}"}
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BACKEND_AUTHED + path, data=data, headers=headers, method=method)
    try:
        resp = urllib.request.urlopen(req, timeout=HTTP_TIMEOUT_S)
        raw = resp.read()
        return resp.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as e:           # 4xx/5xx with a body (HTTPError ⊂ URLError ⇒ first)
        raw = e.read()
        try:
            return e.code, json.loads(raw)
        except (ValueError, TypeError):
            return e.code, {"raw": raw.decode(errors="replace")[:300]}
    except (urllib.error.URLError, TimeoutError, OSError) as e:  # connect/DNS/timeout ⇒ skip, no crash
        return 0, {"err": type(e).__name__}


def _draft_title(m: dict) -> str:
    """Working title for the draft. Appends a short hex album-id token so the SERVER-derived slug
    stays unique per album: slugify_title strips to [a-z0-9], so a fully-Korean title would slug to
    the same 'untitled' and the create would 409 after the first one. The hex survives slugify."""
    artist = m["artists"][0].strip() if m["artists"] else ""
    title = (m["title"] or "무제").strip()
    head = f"[초고] {artist} — {title}" if artist else f"[초고] {title}"
    return f"{head} · {m['album_id'][:8]}"


def _draft_body(m: dict, draft: str) -> str:
    """Prepend a machine-readable provenance comment (invisible on render, visible in the /write
    editor source) to the draft. Provenance can't go to Post.extra (WritePostRequest is
    extra='ignore' ⇒ silently dropped), so it rides in body_mdx — no contract change needed. The
    draft is length-capped so a prompt-injected oversize block can't make every POST 4xx-fail."""
    body = draft.rstrip()
    if len(body) > BODY_MDX_MAX:
        body = body[:BODY_MDX_MAX].rstrip() + "\n\n<!-- buckit-nightly: 초안이 길어 잘림 — 원본은 docs/buckit 파일 -->"
    buckets = "; ".join(m.get("buckets") or []) or "?"
    prov = (f"<!-- buckit-nightly draft · album_id={m['album_id']} · bucket={buckets} · "
            f"generated={date.today().isoformat()} · via=memo-draft -->")
    return f"{prov}\n\n{body}\n"


def _norm_key(s: str) -> str:
    """Aggressive fold for binding a model-emitted filename to a memo slug despite case / space /
    separator drift. Keeps alnum + Hangul/Kana/CJK only (the script's _slug yields lowercased
    word-chars incl. Hangul, so a memo slug and a faithful model filename fold to the same key)."""
    return re.sub(r"[^0-9a-z가-힣぀-ヿ一-鿿]+", "", (s or "").lower())


def _pair_files_to_memos(memos: list[dict],
                         files: list[tuple[str, str]]) -> tuple[list[tuple[dict, str]], list[str]]:
    """Bind each written draft file to its memo WITHOUT trusting the model's exact filename.
    Primary = exact `<slug>.md`; fallback = a collision-safe normalized fold (a fold key shared by
    2+ memos is dropped, so two memos can never cross-pair). `_summary.md` and any file that matches
    no memo (or a second file folding onto an already-paired memo) are returned as orphans (kept on
    disk, no draft). Returns ([(memo, content)], orphan_basenames)."""
    by_slug = {f"{m['slug']}.md": m for m in memos}
    norm_index: dict[str, dict | None] = {}
    for m in memos:
        k = _norm_key(m["slug"])
        norm_index[k] = None if k in norm_index else m  # ambiguous fold ⇒ disable (no cross-pair)
    pairs: list[tuple[dict, str]] = []
    used: set[str] = set()
    orphans: list[str] = []
    for base, content in files:
        if base == "_summary.md":
            continue
        stem = base[:-3] if base.endswith(".md") else base
        memo = by_slug.get(base) or norm_index.get(_norm_key(stem))
        if memo is None or memo["album_id"] in used:
            orphans.append(base)
            continue
        used.add(memo["album_id"])
        pairs.append((memo, content))
    return pairs, orphans


def deliver_drafts(memos: list[dict], files: list[tuple[str, str]], token: str) -> dict:
    """Create one `status='draft'` post per memo whose draft was written, then mark that memo
    GROWN via the dedicated endpoint: `POST /api/buckets/nightly-grow {album_id, post_id}`
    stamps the post_id AND clears prep_tonight on every one of the OWNER's checked items for
    that album, server-side (backend #134; the acting user is pinned from the Lambda's
    OWNER_SUB, never from this request). The generic item PATCH cannot do this — it is
    member-scoped and the agent owns no buckets (404 by design). NEVER publishes; makes no raw
    DB write. Drafts carry NO album_ids → they never enter post_albums (the reviewed-set /
    exclusion source).

    Failure accounting — the buckets drive main()'s exit code:
      * denied      — 401/403 on create: identity wiring broke (permanent) → exit 2.
      * stuck       — 409 on create: a PRIOR run created this album's draft but its grow never
        landed, so the memo is still checked and regenerates nightly. Recover with one
        nightly-grow call using the post id from that run's "draft created: id=…" log line,
        or uncheck the memo. → exit 4.
      * grow_failed — created tonight but the grow call did not land; same consequence and
        recovery as stuck. → exit 4.
      * skipped     — transport error / 5xx: transient, retry next night → exit 0.
    Returns {created, grown, skipped, denied, stuck, grow_failed}."""
    pairs, orphans = _pair_files_to_memos(memos, files)
    created: list[tuple[str, str]] = []
    grown = 0
    skipped: list[str] = []
    denied: list[str] = []       # 401/403 — permanent auth rejection, never "retry next run"
    stuck: list[str] = []        # 409 — draft exists from a prior run, its grow never landed
    grow_failed: list[str] = []  # created tonight, but the grow call did not land

    for m, draft in pairs:
        payload = {"title": _draft_title(m), "body_mdx": _draft_body(m, draft),
                   "status": "draft", "category": DRAFT_SECTION}
        status, resp = _api("POST", "/api/posts", token, payload)
        if status in (401, 403):
            # PERMANENT, not transient. Since FIX-nightly-draft-identity Phase A the job holds
            # its own identity which the backend admits on this route, so a 401/403 here means
            # the wiring broke — DRAFT_AGENT_SUB unset/mismatched in the Lambda env, the guard
            # reverted, or the agent account disabled (see infra/README.md "Nightly draft
            # agent"). Lumping it in with 409/5xx is what hid the original failure for 17 days.
            log.error("draft REJECTED PERMANENTLY (album %s, status %s): %s — the agent identity "
                      "was not accepted. It will fail identically every night until the wiring is "
                      "fixed. The file under docs/buckit/ is now the ONLY copy of this draft.",
                      m["album_id"], status, str(resp)[:200])
            denied.append(m["album_id"])
            continue
        if status == 409:
            # A prior run created this album's draft but never stamped the memo (pre-#134 grow
            # was inert, or a crash between create and grow). Tonight's generation was wasted
            # and will be again tomorrow. Do NOT duplicate the draft; flag loudly, exit 4.
            log.error("draft already exists but the memo is STUCK checked (album %s): %s — its "
                      "grow never landed. Recover: POST /api/buckets/nightly-grow with the post "
                      "id from the original 'draft created: id=…' log line, or uncheck the memo.",
                      m["album_id"], str(resp)[:200])
            stuck.append(m["album_id"])
            continue
        if status != 200 or not resp or "id" not in resp:
            # status 0 / 5xx ⇒ transient; retry next run. Leave checked.
            log.warning("draft not created (album %s, status %s): %s — memo left checked, file kept",
                        m["album_id"], status, str(resp)[:200])
            skipped.append(m["album_id"])
            continue
        post_id = resp["id"]
        created.append((post_id, payload["title"]))
        log.info("draft created: id=%s slug=%s title=%r (album %s)",
                 post_id, resp.get("slug"), payload["title"], m["album_id"])
        # Grow-once, server-side: ONE call per memo. Album-level — an album checked in two of
        # the owner's buckets is stamped in both rows by the server (grown counts item rows).
        gs, gb = _api("POST", "/api/buckets/nightly-grow", token,
                      {"album_id": m["album_id"], "post_id": post_id})
        n = gb.get("grown") if isinstance(gb, dict) else None
        if gs == 200 and isinstance(n, int):
            grown += n
            if n == 0:
                # Gate passed and the service ran, but no row matched — the memo was already
                # stamped/unchecked (e.g. a concurrent manual run). Not a failure.
                log.warning("grow matched 0 items (album %s) — memo already stamped/unchecked?",
                            m["album_id"])
        else:
            log.error("grow FAILED (album %s, status %s): %s — post_id not stamped; the memo "
                      "stays checked and tomorrow night regenerates + 409s. Recover with one "
                      "nightly-grow call using post id %s, or uncheck the memo.",
                      m["album_id"], gs, str(gb)[:160], post_id)
            grow_failed.append(m["album_id"])

    if orphans:
        log.warning("%d draft file(s) matched no memo — kept on disk, no draft: %s",
                    len(orphans), ", ".join(orphans))
    return {"created": created, "grown": grown, "skipped": skipped, "denied": denied,
            "stuck": stuck, "grow_failed": grow_failed}


# --- orchestration --------------------------------------------------------
def main() -> None:
    ap = argparse.ArgumentParser(description="$0 nightly memo→review-draft runner (Stage 1).")
    ap.add_argument("--dry-run", action="store_true",
                    help="assemble + print the checked-memo context and the claude argv, "
                         "then exit; do NOT call claude and write no files")
    ap.add_argument("--no-draft", action="store_true",
                    help="write the docs/buckit draft files only; skip in-app draft creation "
                         "(Stage 2 Step 7). Default: also create one draft post per memo.")
    args = ap.parse_args()

    missing = missing_rule_files()

    conn = connect()
    try:
        memos, context = export_checked_memos(conn)
    finally:
        conn.close()
    n_memos = len(memos)

    if args.dry_run:
        log.info("dry-run: %d checked memo(s); context = %d chars; not calling claude",
                 n_memos, len(context))
        if missing:
            log.warning("dry-run: MISSING rule file(s): %s", ", ".join(missing))
        log.info("dry-run: claude argv = %s", " ".join(claude_argv()))
        log.info("dry-run: output dir = %s", _output_reldir())
        sys.stdout.write(context + "\n")
        return

    today = date.today().isoformat()

    # The checkbox is the only gate. No checked memo ⇒ no claude run (a blind timer would
    # manufacture stale ideas). Still leave the morning index, per run spec §5.
    if n_memos == 0:
        note = "" if not missing else f" (주의: 규칙 파일 누락 — {', '.join(missing)})"
        path = write_summary_only(
            f"# Buckit Nightly — {today}\n\n"
            f"오늘 키울 메모 없음 (체크된 메모 0개).{note} 키우고 싶은 메모에 "
            "'오늘 밤 키우기'를 체크해 두면 다음 밤에 완결형 평론 초안을 만들어 둡니다.\n"
        )
        log.info("no checked memos — wrote %s and exiting (no claude call, $0)", path)
        if missing:
            log.warning("rule file(s) missing: %s (would STOP a real run)", ", ".join(missing))
        return

    if missing:  # fail loud: don't run the model against an incomplete ruleset (run spec §1)
        path = write_summary_only(
            f"# Buckit Nightly — {today}\n\n"
            f"STOP: 규칙 파일 누락 — {', '.join(missing)}. "
            "규칙을 기억으로 복원하지 않습니다. 파일 복구 후 다시 실행하세요.\n"
        )
        log.error("missing rule file(s) %s — wrote %s and exiting (no claude call)",
                  ", ".join(missing), path)
        sys.exit(1)

    prompt = build_prompt(context)
    log.info("running claude -p (model=%s, NO tools, %d checked memo(s), prompt %d chars) → %s/",
             CLAUDE_MODEL, n_memos, len(prompt), _output_reldir())
    if len(prompt) > PROMPT_SIZE_WARN_CHARS:
        # Research notes are passed whole, so prompt size scales with the number of checked
        # memos. Surface an abnormal night rather than silently truncating anything.
        log.warning("prompt is %d chars (> %d) across %d memo(s) — check for over-checked memos",
                    len(prompt), PROMPT_SIZE_WARN_CHARS, n_memos)
    t0 = time.monotonic()
    res = run_claude_with_retry(prompt)
    dt = time.monotonic() - t0

    files = parse_payload(res["result"])
    if not files:
        # The model returned something but it didn't match the delimited format. Don't lose it:
        # park the raw result for inspection rather than silently writing nothing.
        path = write_summary_only(
            f"# Buckit Nightly — {today}\n\n"
            "경고: 모델 출력이 예상 구분자 형식과 맞지 않아 파싱된 파일이 없습니다. "
            "아래는 원본 출력입니다.\n\n---\n\n" + res["result"]
        )
        log.warning("payload had no parseable files — parked raw output at %s "
                    "(%.1fs, tokens_in=%d tokens_out=%d model=%s)",
                    path, dt, res["tokens_in"], res["tokens_out"], res["model"])
        return

    written = write_files(files)
    log.info("done in %.1fs — %d file(s) in %s: %s | tokens_in=%d tokens_out=%d model=%s",
             dt, len(written), _output_reldir(), ", ".join(written),
             res["tokens_in"], res["tokens_out"], res["model"])
    if "_summary.md" not in written:
        log.warning("model did not emit _summary.md (run spec §5 wants a morning index)")

    # Stage 2 Step 7: ALSO deliver each generated draft as an in-app draft (default on). The files
    # above are the backup — a token-mint / API failure here degrades gracefully (files written).
    if args.no_draft:
        log.info("--no-draft: skipping in-app draft delivery (draft files only)")
        return
    try:
        token = mint_agent_token()
    except Exception as e:  # noqa: BLE001 — keep the files, but a mint failure is delivery-broken
        log.error("draft delivery FAILED — agent token mint failed: %s; draft files were "
                  "written and remain the backup", str(e)[:300])  # message distinguishes AccessDenied
        sys.exit(3)  # was exit 0 — a silent delivery skip is how the 2026-07 403 hid for 17 days
    try:
        summary = deliver_drafts(memos, files, token)
    except Exception as e:  # noqa: BLE001 — never crash-dump after files are written (token in frame locals)
        log.error("draft delivery error (%s) — draft files were written and remain the backup",
                  type(e).__name__)
        sys.exit(3)
    log.info("draft delivery: %d draft(s) created, %d memo(s) grown, %d skipped/failed, %d DENIED",
             len(summary["created"]), summary["grown"],
             len(summary["skipped"]) + len(summary["stuck"]) + len(summary["grow_failed"]),
             len(summary["denied"]))
    if summary["denied"]:
        # Everything is already written to disk, so exiting non-zero costs nothing and is the only
        # signal that reaches outside the log: `launchctl list` reports the exit status, and until
        # ws #709 a permanently-rejected draft still exited 0 and read as a healthy run.
        log.error("EXITING NON-ZERO: %d draft(s) were generated tonight and permanently rejected on "
                  "delivery. They exist only as files under %s/. Fix the agent wiring.",
                  len(summary["denied"]), _output_reldir())
        sys.exit(2)
    if summary["stuck"] or summary["grow_failed"]:
        # The draft exists but its memo is still checked — tomorrow night regenerates it for
        # nothing. Distinct exit code so `launchctl list` separates "identity broken" (2) from
        # "grow didn't land" (4); per-album recovery lines are above.
        log.error("EXITING NON-ZERO: %d memo(s) remain checked with their draft already created "
                  "(stuck=%d, grow_failed=%d) — tomorrow night regenerates them for nothing. "
                  "See the per-album recovery lines above.",
                  len(summary["stuck"]) + len(summary["grow_failed"]),
                  len(summary["stuck"]), len(summary["grow_failed"]))
        sys.exit(4)


if __name__ == "__main__":
    main()
