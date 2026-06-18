#!/usr/bin/env python3
"""FEAT-editor-buckit Stage 1 Step 4 — the $0 nightly memo → skeleton runner.

Turns each **checked** bucket memo ("오늘 밤 키우기" = `review_bucket_items.prep_tonight`)
into a Korean **section skeleton** file under `docs/buckit/<YYYY-MM-DD>/`, run unattended
overnight on the owner's Max subscription via headless Claude Code (`claude -p`) = **$0**.
It is the Stage-1 sibling of `scripts/editor_buckit.py` (Stage 0) and clones its read-only
prod-export + `claude -p` heritage.

The output is **inventory-shaped, never thesis-shaped** (see docs/editorial/buckit-nightly.md):
it expands only the editor's own judgments, leaves evidence as `[passage]` blanks, lists the
controlling-idea candidates without choosing, and marks every open question. A too-finished
skeleton is a bug. **Zero outputs is a valid run.** The job writes files and nothing else —
no DB write, no git, no publish.

    myblog_backend/.venv/bin/python scripts/buckit_nightly.py            # full nightly run
    myblog_backend/.venv/bin/python scripts/buckit_nightly.py --dry-run  # print the assembled
        #   checked-memo context + the resolved claude argv, then exit WITHOUT calling claude

Architecture / safety (RFC Stage 1, Step 4) — hardened after an adversarial tool-scope audit
(2026-06-18) that proved the earlier "agentic claude writes the files" design both BROKE the
feature (scoped `Write(docs/buckit/**)` is denied in headless `-p` on CLI 2.1.181 ⇒ zero files
written) AND opened a secret-exfiltration surface (an unscoped `Read` + unrestricted `WebFetch`
could read `~/.aws`/`~/.claude` creds and exfiltrate, driven by a prompt-injection in the memo
text). So this runner reverts to the proven Stage-0 mechanical pattern:

  * **This script** does the entire DB read, **read-only**: `connect()` forces
    `SET default_transaction_read_only = on` + autocommit SELECTs (cloned from
    editor_buckit.py). There is NO write path to prod anywhere in this file. It reads the
    `prep_tonight`-checked, unwritten, not-yet-reviewed bucket items (+ their verbatim
    `note`, album/artist/genre facts, done research-note excerpts, recent listens).
  * **This script also reads the rule docs and writes the skeleton files** — i.e. the
    "repo read + file write + Postgres read" capabilities all live in the script, validated.
    Output filenames are reduced to a safe basename under `docs/buckit/<date>/` — the model
    cannot cause a path escape.
  * **claude -p is a pure text transformer with NO tools.** The three rule docs + the
    read-only context block are inlined into the prompt; `--disallowed-tools` denies the full
    file/network/exec surface (Bash/Edit/Read/Write/WebSearch/WebFetch/…) and
    `--setting-sources user` keeps the broad project-local Bash allow-list out of the run.
    The model only generates the Korean skeletons as a delimited payload and returns it; it
    has no DB tool, no file tool, no network tool ⇒ structurally incapable of touching prod,
    git, the filesystem, or the network.
  * The **checkbox is the only gate**: if zero memos are checked, this script writes a
    `_summary.md` saying so and exits WITHOUT calling claude (a blind nightly timer would
    manufacture stale ideas — the checkbox is what makes the timer non-blind; see the RFC
    Decisions log 2026-06-18).
  * Never logs DATABASE_URL / secrets.

Note on ordering: memos are processed in bucket/item position order (review_bucket_items has
no checked-at timestamp), so run-spec §6's "newest-checked first" recency hint is intentionally
not honored — the order is deterministic instead.

RFC: docs/rfcs/FEAT-editor-buckit.md (Stage 1, Step 4).
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
from datetime import date

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    stream=sys.stderr,
)
log = logging.getLogger("buckit_nightly")

# --- config ---------------------------------------------------------------
REGION = "ap-northeast-2"
SECRET_ID = "myblog/backend"            # holds DATABASE_URL
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

    sm = boto3.client("secretsmanager", region_name=REGION)
    secret = json.loads(sm.get_secret_value(SecretId=SECRET_ID)["SecretString"])
    # SQLAlchemy form `postgresql+psycopg://` -> libpq form psycopg.connect wants.
    return secret["DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://", 1)


def connect():
    import psycopg
    from psycopg.rows import dict_row

    # connect_timeout=30 absorbs Neon cold-start (reference-database-url-psql).
    conn = psycopg.connect(database_url(), connect_timeout=30, row_factory=dict_row)
    # Strictly read-only: force it at the session level (committed BEFORE autocommit flips on,
    # so it survives) — any accidental write raises instead of mutating prod. (editor_buckit.py.)
    conn.execute("SET default_transaction_read_only = on")
    conn.commit()
    conn.autocommit = True
    return conn


# --- read-only context export --------------------------------------------
# Only the CHECKED ("오늘 밤 키우기" = prep_tonight), unwritten (post_id IS NULL),
# not-yet-reviewed (album_id NOT IN post_albums) items. An album checked in two buckets
# is one writing subject ⇒ dedupe by album_id, merging its notes.
CHECKED_SQL = """
SELECT
    i.album_id,
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


def export_checked_memos(conn) -> tuple[int, str]:
    """Assemble the read-only context block for every CHECKED memo.

    Returns (n_memos, context_markdown). The block IS the model's §3 input — it carries
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
                "notes": [],
                "rec_reasons": [],
            }
            memo_by[aid] = m
        if row["bucket_name"] not in m["buckets"]:
            m["buckets"].append(row["bucket_name"])
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

    return len(memos), "\n".join(parts)


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
  입력은 아래 "오늘 밤 키울 메모" 블록이 전부다. 블록에 없는 사실은 지어내지 말고 `[source?]`/`[passage]`로
  비워라(★). 파일을 직접 쓰려 하지 말 것 — 아래 형식으로 텍스트만 반환하면 스크립트가 파일로 저장한다.
- **출력은 전부 한국어.** 스켈레톤은 **인벤토리형**(있는 것/확인된 것/타인 견해/열린 질문) — thesis 금지.
  판단은 편집자(메모) 것만 펴고, 근거는 `[passage]` 빈칸, controlling idea는 후보만(택1하지 말 것),
  질문은 표시(ask→mark). **너무 완성된 스켈레톤은 버그다. 0개 출력도 정답이다.**

### 출력 형식 (반드시 이대로 — 이 외 텍스트 금지)

파일마다 아래 구분자 한 줄로 시작하고, 그 다음 줄부터 그 파일의 한국어 마크다운 본문을 쓴다:

```
=====BUCKIT_FILE: <파일명.md>=====
<그 파일의 마크다운 본문>
```

- `<파일명.md>` 는 각 메모의 "출력 파일명(제안)"을 그대로 쓴다(예: `frank-ocean-channel-orange.md`). 경로/슬래시 없이 파일명만.
- 메모마다 한 파일. 자랄 판단 씨앗이 없는 메모(§4)는 파일을 만들지 말고 _summary.md의 '생략' 목록에만 한 줄로 남겨라.
- **맨 마지막 파일은 반드시 `_summary.md`** — 아침에 가장 먼저 여는 인덱스. 생성한 것 + 생략한 것(이유: 씨앗 없음 / 미확인 사실 많음 등)을 우선순위로 정리. 아무 것도 자라지 않았으면 `_summary.md` 하나만, '오늘 키울 메모 없음' + 이유.
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


# --- orchestration --------------------------------------------------------
def main() -> None:
    ap = argparse.ArgumentParser(description="$0 nightly memo→skeleton runner (Stage 1).")
    ap.add_argument("--dry-run", action="store_true",
                    help="assemble + print the checked-memo context and the claude argv, "
                         "then exit; do NOT call claude and write no files")
    args = ap.parse_args()

    missing = missing_rule_files()

    conn = connect()
    try:
        n_memos, context = export_checked_memos(conn)
    finally:
        conn.close()

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
            "'오늘 밤 키우기'를 체크해 두면 다음 밤에 골격을 잡아 둡니다.\n"
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


if __name__ == "__main__":
    main()
