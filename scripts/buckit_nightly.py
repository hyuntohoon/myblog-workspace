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
`[근거 보강 필요: 트랙/구간]` — it never fabricates facts, emotions, experiences, or a verdict the
memo didn't hold (★). A memo too thin to support a review yields a short `초안 생성 보류` note
instead of a fabricated draft. **Zero outputs is a valid run.** The job writes files and nothing
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

  * It mints a short-lived Cognito JWT for the smoke/test user (`USER_AUTH`, password from Secrets
    Manager `myblog/smoke`; the `scripts/smoke.py get_token` pattern) and calls
    `POST /api/posts {status:'draft', …}` on the raw API Gateway. The password and the token are
    NEVER logged. The job's ONLY new capability is **create-a-draft** — it never publishes
    (`status` is hard-wired to `draft`) and makes no raw DB write (the read-only export connection
    is untouched; every write goes through the authed API).
  * Provenance (album_id / bucket / date) rides as a leading HTML comment in the draft `body_mdx`,
    NOT `Post.extra` — `WritePostRequest` is `extra='ignore'`, so an `extra` field would be silently
    dropped; the comment keeps this a single-repo, no-contract-change job. The draft carries NO
    `album_ids`, so it does NOT enter `post_albums` (the reviewed-set + this job's own exclusion
    source) — a nightly draft is not yet a published review.
  * Grow-once: after a draft is created the script marks that memo grown — it stamps the new
    `post_id` on the item AND clears `prep_tonight` in one PATCH. The `post_id` stamp durably
    excludes the album next run (CHECKED_SQL filters `post_id IS NULL`), so even a lost
    `prep_tonight` clear or a crash between POST and PATCH does NOT re-create the draft — and the
    album-unique slug makes any re-POST 409 (rejected, never duplicated). A draft or PATCH failure
    is non-fatal — the `docs/buckit/` file is the backup. The model still has NO tools; a
    prompt-injection in a memo cannot redirect a write,
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
import subprocess
import sys
import time
import unicodedata
import urllib.error
import urllib.request
from datetime import date

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
RESEARCH_EXCERPT_CHARS = 1500           # per done-note excerpt cap (facts only; bounds the prompt)
RECENT_DAYS = 30                        # play-event recency window
# claude tool scope — the model is a PURE TEXT TRANSFORMER. It gets NO tools: rule docs +
# context are inlined; the script does all DB read + file write. We disallow the full
# file/network/exec surface as belt-and-suspenders so even a default-on tool can't fire, and
# pin setting-sources so the project-local broad Bash allow-list is never merged in.
DISALLOWED_TOOLS = ["Bash", "Edit", "Read", "Write", "WebSearch", "WebFetch",
                    "Glob", "Grep", "NotebookEdit", "Task", "TodoWrite"]
SETTING_SOURCES = "user"
# Output framing: the model emits each file as `<DELIM> <basename>` on its own line, then the
# file body, until the next delimiter. The script splits, validates the basename, and writes.
FILE_DELIM = "=====BUCKIT_FILE:"
FILE_DELIM_RE = re.compile(r"^=====BUCKIT_FILE:\s*(.+?)\s*=*\s*$", re.MULTILINE)

# --- Stage 2 Step 7: in-app draft delivery (authed API; the script is the only writer) ---
BACKEND_AUTHED = "https://ld8pjw3mx4.execute-api.ap-northeast-2.amazonaws.com"  # raw API Gateway
SMOKE_SECRET_ID = "/myblog/smoke"       # SSM SecureString param (MYBLOG_SMOKE_PASSWORD)
COGNITO_REGION = "ap-northeast-2"
COGNITO_CLIENT_ID = "68ccmcanfbvla9qbovnb9b18bt"
DEFAULT_SMOKE_EMAIL = "test@ratemymusic.blog"
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
ORDER BY b.position, i.position;
"""

RESEARCH_SQL = """
SELECT album_id, result_md, finished_at
FROM album_research
WHERE status = 'done' AND result_md IS NOT NULL
  AND album_id IN (
        SELECT album_id FROM review_bucket_items
        WHERE prep_tonight = true AND post_id IS NULL
  )
ORDER BY finished_at DESC NULLS LAST;
"""

RECENCY_SQL = f"""
SELECT album_id,
       max(played_at)                                                       AS last_played,
       count(*) FILTER (WHERE played_at > now() - INTERVAL '{RECENT_DAYS} days') AS plays_recent
FROM spotify_play_events
WHERE album_id IN (
        SELECT album_id FROM review_bucket_items
        WHERE prep_tonight = true AND post_id IS NULL
  )
GROUP BY album_id;
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


def _slug(title: str, artists: list[str]) -> str:
    """Filename-safe slug from artist + title. ASCII-fold where possible; keep Hangul.
    Falls back to a short id so two distinct albums never collide on an empty slug."""
    base = f"{artists[0]}-{title}" if artists else (title or "memo")
    base = unicodedata.normalize("NFKC", base)
    # keep word chars (incl. Hangul/CJK via \w under re.UNICODE) + spaces/hyphens; drop the rest
    base = re.sub(r"[^\w\s-]", "", base, flags=re.UNICODE)
    base = re.sub(r"[\s_]+", "-", base).strip("-").lower()
    return base[:60] or "memo"


def _research_excerpt(md: str | None) -> str:
    if not md:
        return "없음"
    flat = md.strip().replace("\n", " ")
    return flat[:RESEARCH_EXCERPT_CHARS] + ("…" if len(flat) > RESEARCH_EXCERPT_CHARS else "")


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
    rows = _fetch_all(conn, CHECKED_SQL)
    research = _fetch_all(conn, RESEARCH_SQL)
    recency = _fetch_all(conn, RECENCY_SQL)

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
        parts.append(f"- AI 리서치 노트(사실 — 발췌): {_research_excerpt(m['research_md'])}")
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
  메모의 판단을 잠정 controlling idea로 골라(택1) 도입에서 끌고 가며 한 편의 글로 전개해라. 단, 메모에
  없는 평가/결론은 새로 만들지 말 것(편집자 판단의 전개이지 대체가 아니다, ★). 근거가 비면
  `[근거 보강 필요: 트랙/구간]`로 인라인 표시. **점수 정당화로 닫지 말고** 비평적 판단·이미지·여운으로
  닫아라. 음향 디테일 나열보다 표현·편곡·장르 맥락·비평 프레이밍을 우선. 메모가 너무 얇아 평론이
  안 되면 지어내지 말고 `초안 생성 보류`로 둬라(§4). **0개 출력도 정답이다.**
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
- 메모마다 한 파일. 평론으로 자라기엔 너무 얇은 메모(§4)는 파일을 만들지 말고 _summary.md의 '초안 생성 보류' 목록에 이유 한 줄로 남겨라.
- **맨 마지막 파일은 반드시 `_summary.md`** — 아침에 가장 먼저 여는 인덱스. 생성한 초안 + 보류한 것(이유: 메모 얇음 / 미확인 사실 많음 등)을 우선순위로 정리. 아무 것도 자라지 않았으면 `_summary.md` 하나만, '오늘 키울 메모 없음' + 이유.
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
def claude_argv() -> list[str]:
    return ["claude", "-p", "--output-format", "json", "--model", CLAUDE_MODEL,
            "--setting-sources", SETTING_SOURCES,
            "--disallowed-tools", *DISALLOWED_TOOLS]


def run_claude(prompt: str) -> dict:
    """Run headless Claude Code as a pure text transformer (NO tools) and return parsed
    {result, tokens_in, tokens_out, model}. `result` is the delimited multi-file payload the
    caller splits + writes. Raises on non-zero exit, timeout, JSON/parse failure, an
    `is_error` result, or an empty result. (Lifted from research_poller.py JSON path.)"""
    proc = subprocess.run(
        claude_argv(),
        input=prompt,
        capture_output=True,
        text=True,
        timeout=CLAUDE_TIMEOUT_S,
        cwd=_repo_root(),
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
    tokens_in = (
        (usage.get("input_tokens") or 0)
        + (usage.get("cache_read_input_tokens") or 0)
        + (usage.get("cache_creation_input_tokens") or 0)
    )
    tokens_out = usage.get("output_tokens") or 0
    model_usage = data.get("modelUsage", {}) or {}
    model = max(model_usage, key=lambda k: model_usage[k].get("outputTokens", 0), default=None) \
        or CLAUDE_MODEL
    return {"result": result, "tokens_in": tokens_in, "tokens_out": tokens_out, "model": model}


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


# --- Stage 2 Step 7: mint a smoke JWT + deliver each generated draft as a draft post --------
def mint_smoke_token() -> str:
    """Mint a short-lived (≈60-min) Cognito access token for the smoke/test user via USER_AUTH
    (2-step), reading the password from Secrets Manager `myblog/smoke`. $0; the password and the
    token are NEVER logged. (scripts/smoke.py get_token pattern.)

    Blast radius: in this single-user, no-per-user-scoping system the token is owner-equivalent —
    it CAN publish/edit/delete any post. The draft-only / create-only limit is enforced by THIS code
    (status hard-wired to 'draft'; no PUT/DELETE), not by the credential. The MYBLOG_SMOKE_PASSWORD
    env override is dev-only — launchd sets no env var; never set it on the nightly job (a plaintext
    pw in the process env is exposable via `ps e` / crash dumps)."""
    import boto3

    ssm = boto3.client("ssm", region_name=REGION)
    secret = json.loads(ssm.get_parameter(Name=SMOKE_SECRET_ID, WithDecryption=True)["Parameter"]["Value"])
    pw = os.environ.get("MYBLOG_SMOKE_PASSWORD") or secret.get("MYBLOG_SMOKE_PASSWORD")
    email = (os.environ.get("MYBLOG_SMOKE_EMAIL")
             or secret.get("MYBLOG_SMOKE_EMAIL") or DEFAULT_SMOKE_EMAIL)
    if not pw:
        raise RuntimeError("smoke password missing (Secrets Manager myblog/smoke / MYBLOG_SMOKE_PASSWORD)")
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
    POST /api/posts and the bucket item PATCH are explicit Cognito-authorized routes (the smoke
    token passes the API-GW authorizer / the backend's require_cognito_token). Returns
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
    GROWN: stamp the new post_id on the item AND clear prep_tonight, both in one PATCH. NEVER
    publishes; makes no raw DB write (every write goes via the authed API). Drafts carry NO
    album_ids → they never enter post_albums (the reviewed-set / exclusion source).

    Durable grow-once (audit fix): stamping post_id excludes the album next run via CHECKED_SQL's
    `post_id IS NULL`, so even a lost prep_tonight clear / a crash between POST and PATCH does NOT
    re-create the draft — create+exclude are idempotent. The album-unique slug (see _draft_title)
    means a re-POST after a stamp failure 409s (REJECTED, never duplicated). All non-2xx is
    non-fatal: the docs/buckit file is the backup. Returns {created, grown, skipped}."""
    pairs, orphans = _pair_files_to_memos(memos, files)
    created: list[tuple[str, str]] = []
    grown = 0
    skipped: list[str] = []

    for m, draft in pairs:
        payload = {"title": _draft_title(m), "body_mdx": _draft_body(m, draft),
                   "status": "draft", "category": DRAFT_SECTION}
        status, resp = _api("POST", "/api/posts", token, payload)
        if status != 200 or not resp or "id" not in resp:
            # 409 ⇒ this album's draft already exists (a prior run created it but failed to stamp);
            # do NOT duplicate. status 0 / 5xx ⇒ transient; retry next run. Either way leave checked.
            log.warning("draft not created (album %s, status %s): %s — memo left checked, file kept",
                        m["album_id"], status, str(resp)[:200])
            skipped.append(m["album_id"])
            continue
        post_id = resp["id"]
        created.append((post_id, payload["title"]))
        log.info("draft created: id=%s slug=%s title=%r (album %s)",
                 post_id, resp.get("slug"), payload["title"], m["album_id"])
        for it in m.get("items", []):  # grow-once: post_id (durable exclude) + clear prep_tonight
            ps, pb = _api("PATCH", f"/api/buckets/{it['bucket_id']}/items/{it['item_id']}",
                          token, {"prep_tonight": False, "post_id": post_id})
            if ps == 200:
                grown += 1
            else:
                log.warning("grow PATCH failed (item %s, status %s): %s — post_id not stamped; memo "
                            "stays checked but the album-unique slug makes next run 409-skip (no dup)",
                            it["item_id"], ps, str(pb)[:160])

    if orphans:
        log.warning("%d draft file(s) matched no memo — kept on disk, no draft: %s",
                    len(orphans), ", ".join(orphans))
    return {"created": created, "grown": grown, "skipped": skipped}


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
    t0 = time.monotonic()
    res = run_claude(prompt)
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
        token = mint_smoke_token()
    except Exception as e:  # noqa: BLE001 — any mint failure ⇒ keep the files, skip drafts
        log.error("draft delivery skipped — smoke token mint failed: %s; draft files were "
                  "written and remain the backup", str(e)[:300])  # message distinguishes AccessDenied
        return
    try:
        summary = deliver_drafts(memos, files, token)
    except Exception as e:  # noqa: BLE001 — never crash after files are written (token in frame locals)
        log.error("draft delivery error (%s) — draft files were written and remain the backup",
                  type(e).__name__)
        return
    log.info("draft delivery: %d draft(s) created, %d memo(s) grown, %d skipped/failed",
             len(summary["created"]), summary["grown"], len(summary["skipped"]))


if __name__ == "__main__":
    main()
