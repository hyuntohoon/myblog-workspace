#!/usr/bin/env python3
"""FEAT-album-research-notes Step 3 — the $0 local research poller.

Drains `album_research(status='queued')` rows by running the album-research
prompt through **headless Claude Code** (`claude -p`), which executes on the
owner's Claude Code **subscription** — so each research run costs **$0** at
opus-4.8 quality (the 2026-06-11 bench winner). The DB writeback is done by
THIS script, not the model; the model only gets `--allowed-tools
WebSearch,WebFetch` (no Bash/Edit) so a headless run can't touch the repo.

This is a standalone operator script. It is NOT deployed anywhere and shares no
code with the dormant `researchWorkerLambda` (the paid cloud path, kept inert in
$0 mode). RFC: docs/rfcs/FEAT-album-research-notes.md (Execution backend, Step 3).

REQUIRES a Python with `psycopg` (v3) + `boto3`, and the `claude` CLI logged in
to the Max subscription. The repo's backend venv already has the Python deps:

    myblog_backend/.venv/bin/python scripts/research_poller.py --once
    myblog_backend/.venv/bin/python scripts/research_poller.py            # loop

Auth/secret model (no Anthropic key needed — $0 path):
  * `claude -p` uses the subscription login already on this machine.
  * prod `DATABASE_URL` is read from Secrets Manager `myblog/backend` with the
    owner's AWS creds (`postgresql+psycopg://` → `postgresql://`; Neon cold-start
    ⇒ connect_timeout=30).

Dedupe / single-flight (RFC "Claim gate"): a conditional UPDATE claims one
`queued`/`failed`/stale-`running` row at a time (`FOR UPDATE SKIP LOCKED`), so
two poller instances never double-run a row and a crash-stranded `running` row
(laptop sleep, `claude -p` crash) is re-claimed after 20 min. Processing is
**serial** with an inter-run sleep so a bucket-wide `research_mode='all'` flip
drains steadily instead of spiking the subscription rate limit.

Refine vs. fresh: a claimed row is a **refine** iff it still carries a prior
`result_md` (restart clears it, first-run never had one); the prior note + the
owner's `last_instruction` are then sent for an integrated update, and a failed
refine keeps the old note (never blanks the panel). Otherwise it's a fresh run.

Genius readiness (FEAT-lyrics-annotations R1/R2/R4): a research request is also
the trigger for the worker's per-album Genius collection. The claim gate holds
a fresh request until every album track carries a `track_genius_songs` row
(any match_status counts as attempted — permanent match failures never block),
nudging the worker via SQS meanwhile; past `GENIUS_WAIT_MAX` the run proceeds
partial. The prompt then gets an album-level facts block DERIVED from the
track-scoped store (credits / sample·interpolation relationships, matched
tracks only), citable as `[확인: Genius]`.

OQ5 (poller host/schedule): start by running `--once` by hand or under `/loop`;
formalize to launchd/cron only if draining-by-hand proves annoying. Correctness
does not depend on it — queued rows simply wait until the poller runs.
"""
from __future__ import annotations

import argparse
import json
import logging
import re
import sys
import time
import unicodedata
from pathlib import Path

# shared_db is read from the LOCAL checkout via src-path injection (not the git
# pin) — same pattern as lyrics_translate_poller's backend injection. Resolves
# relative to this script so it works from any checkout that carries the nested
# myblog_shared_db repo (the launchd runtime = the workspace main checkout).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "myblog_shared_db" / "src"))

from myblog_shared_db.llm import CliEngine, LLMJob, ToolPolicy  # noqa: E402
from myblog_shared_db.llm.subscription_guard import (  # noqa: E402
    LLMSubscriptionCooldown,
    coordinated_run,
    ensure_subscription_available,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger("research_poller")

# --- config ---------------------------------------------------------------
REGION = "ap-northeast-2"
SECRET_ID = "/myblog/backend"         # SSM SecureString param (holds DATABASE_URL)
PROMPT_VERSION = "v2"                  # must match the vendored prompt below
PROMPT_FILE = "album_research_v2.md"   # vendored copy of docs/editorial/album-research-prompt.md
                                       # (its prompt head, through the Output-format fence; keep the
                                       # two byte-identical — the workspace doc stays canonical,
                                       # this is the build copy)
CLAUDE_MODEL = "opus"                  # bench winner = opus 4.8
CLAUDE_TIMEOUT_S = 900                 # a run is 3-8 min; 15-min hard ceiling
STALE_RUNNING = "20 minutes"          # crash-recovery re-claim window (a run is <=~10 min)
DEFAULT_INTERVAL_S = 120              # poll cadence when no row is waiting
DEFAULT_INTER_RUN_SLEEP_S = 30       # serial spacing between runs (rate-limit guard)

# Genius readiness (FEAT-lyrics-annotations R1/R2). A research request is the
# trigger for the worker's per-album Genius collection; the claim gate below
# holds a fresh request until every track has a track_genius_songs row, and
# GENIUS_WAIT_MAX is the partial fallback — past it, research runs with whatever
# was collected (an unset token or a worker outage must not starve research).
GENIUS_WAIT_MAX = "90 minutes"
SQS_QUEUE_NAME = "blogSQS"            # worker queue for the genius_fetch nudge
NUDGE_MAX_ALBUMS = 3                  # nudges per firing; hourly worker cron is the fallback
NUDGE_COOLDOWN_S = 300                # per-album re-nudge bound: launchd fires every 60s and a
                                      # 15-track worker batch runs ~53s — without this bound a
                                      # held album is re-nudged every firing (90+ messages when
                                      # the token is unset, the exact case the fallback covers)
GENIUS_BLOCK_MAX_CHARS = 6000         # prompt-size cap for the facts block
_NUDGE_STATE = Path.home() / ".cache" / "myblog" / "genius_nudge_state.json"


# --- secrets / db ---------------------------------------------------------
def database_url() -> str:
    """Read prod DATABASE_URL from SSM Parameter Store and normalize for psycopg."""
    import boto3

    ssm = boto3.client("ssm", region_name=REGION)
    secret = json.loads(ssm.get_parameter(Name=SECRET_ID, WithDecryption=True)["Parameter"]["Value"])
    url = secret["DATABASE_URL"]
    # SQLAlchemy form `postgresql+psycopg://` -> libpq form psycopg.connect wants.
    return url.replace("postgresql+psycopg://", "postgresql://", 1)


def connect():
    import psycopg
    from psycopg.rows import dict_row

    # connect_timeout=30 absorbs Neon cold-start (reference-database-url-psql).
    return psycopg.connect(database_url(), connect_timeout=30, row_factory=dict_row)


# --- prompt assembly ------------------------------------------------------
def _prompt_path() -> str:
    import os

    return os.path.join(os.path.dirname(os.path.abspath(__file__)), PROMPT_FILE)


def load_base_prompt() -> str:
    with open(_prompt_path(), encoding="utf-8") as f:
        return f.read()


def _album_block(meta: dict) -> str:
    artists = ", ".join(meta["artists"]) or "(미상)"
    return (
        "## 앨범 (조사 대상)\n"
        f"- 아티스트: {artists}\n"
        f"- 제목: {meta['title']}\n"
        f"- 구분(album_type): {meta.get('album_type') or '(미상)'}\n"
        f"- 발매일: {meta.get('release_date') or '(미상)'}\n"
        f"- 레이블: {meta.get('label') or '(미상)'}\n"
        f"- 트랙 수: {meta.get('total_tracks') if meta.get('total_tracks') is not None else '(미상)'}\n"
        f"- Spotify ID: {meta.get('spotify_id') or '(미상)'}\n"
    )


# --- Genius facts block (R1 derive + R2 inject + R4 provenance) -------------
_REL_LABELS = {
    "samples": "샘플",
    "interpolates": "인터폴레이션",
    "sampled_in": "이후 이 곡을 샘플",
    "interpolated_by": "이후 이 곡을 인터폴레이션",
    "cover_of": "커버 원곡",
    "covered_by": "이후 커버됨",
    "remix_of": "리믹스 원곡",
    "remixed_by": "이후 리믹스됨",
    "live_version_of": "라이브 원곡",
    "performed_live_as": "라이브 버전",
}

# Corporate boilerplate rides custom_performances on nearly every track (Label /
# Publisher / ℗ / © at 14-15/15 on prod) and would crowd the people — engineers,
# session players, translators — out of the capped staff line.
_BOILERPLATE_ROLES = {
    "label", "publisher", "distributor",
    "copyright ©", "phonographic copyright ℗",
}


# A credit carried by only a few tracks is the one a wrong match can forge, so
# those name their tracks; a credit spanning the record needs no pointer and the
# list would just crowd the block.
ATTRIB_MAX_TRACKS = 3
# Per-track evidence lines, capped so a 60-track compilation cannot crowd out the
# credit/relationship sections that follow it.
EVIDENCE_MAX_LINES = 30

_FEAT_RE = re.compile(r"\s*[\(\[]\s*(?:feat|ft|featuring|with)\b[^\)\]]*[\)\]]", re.I)


def _fold_title(text: str) -> str:
    """Comparison form for our-title vs Genius-title.

    The trailing feature credit is stripped first: Genius routinely titles a
    track without it (`No.1 Stunna` for our `No.1 Stunna (feat. 100KGOLD)`), and
    flagging that benign difference would bury the one that matters.
    """
    text = _FEAT_RE.sub("", text or "")
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return " ".join("".join(ch if ch.isalnum() or ch.isspace() else " " for ch in text.lower()).split())


def _track_label(row: dict) -> str:
    no = row.get("track_no")
    return f"{no} {row['title']}" if no is not None else str(row["title"])


def _top_counts(counter: dict, matched: int, cap: int,
                attrib: dict | None = None) -> list[str]:
    ranked = sorted(counter.items(), key=lambda kv: (-kv[1], kv[0]))[:cap]
    out = []
    for name, n in ranked:
        where = ""
        if attrib and n <= ATTRIB_MAX_TRACKS:
            tracks = attrib.get(name) or []
            if tracks:
                where = " — " + " · ".join(tracks)
        out.append(f"{name} ({n}/{matched}트랙{where})")
    return out


def _render_genius_block(rows: list[dict]) -> str:
    """Album-level Genius facts, derived from the track-scoped store.

    Facts come ONLY from `matched` rows — an ambiguous match may be a different
    song entirely, and wrong credits must not enter a research note silently
    (same hold the translate poller applies). Unmatched/unfetched tracks are
    reported as coverage so the model can tell a *confirmed* absence (matched,
    no relationships) from "could not check" — the distinction 78/78 past notes
    could not make.

    `matched` is a threshold verdict, not a guarantee, so every matched track
    also ships its evidence: the Genius title, the confidence and the song URL.
    The 2026-07-30 ONYX e2e is why — our `Simon Says` matched Genius's *왈
    (Simon Says)*, a different 2018 single by the same artist, at 0.7424, and
    its credits went into the block as citable while the one column that showed
    the collision (`genius_title`, stored by V49 for exactly this) was never
    rendered. Raising the threshold would not have caught it: title similarity
    was 0.91, and four correct matches on the same album scored lower.
    """
    total = len(rows)
    matched = [r for r in rows if r["match_status"] == "matched"]
    unmatched = [r for r in rows if r["match_status"] != "matched"]
    ambiguous = sum(1 for r in rows if r["match_status"] == "ambiguous")
    not_found = sum(1 for r in rows if r["match_status"] == "not_found")
    missing = sum(1 for r in rows if r["match_status"] is None)

    lines = ["## Genius 확인 사실 (파이프라인 제공 — 조사 대상 앨범)"]
    lines.append(
        f"- 커버리지: 매칭 {len(matched)}/{total}트랙"
        f" (모호 {ambiguous} · Genius 미등재 {not_found} · 미조회 {missing})"
    )
    if unmatched:
        _status_ko = {"ambiguous": "모호", "not_found": "Genius 미등재", None: "미조회"}
        lines.append(
            "- 사실 확인 불가 트랙: "
            + " · ".join(
                f"{_track_label(r)} [{_status_ko.get(r['match_status'], r['match_status'])}]"
                for r in unmatched
            )
            + " — 이 트랙들에 대해서는 크레딧·관계의 유무를 어느 쪽으로도 주장하지 말 것"
        )
    if not matched:
        lines.append(
            f"- Genius 미매칭 (0/{total} 트랙) — 사실의 부재가 아니라 조회의 부재다. "
            "이 앨범의 크레딧·샘플 관계는 Genius로 확인 불가. "
            "[확인: Genius] 표기를 사용하지 말고, 미확인은 통상 규칙대로 처리할 것."
        )
        return "\n".join(lines) + "\n"

    fetched = [r["fetched_at"] for r in matched if r["fetched_at"]]
    when = ""
    if fetched:
        lo, hi = min(fetched).date(), max(fetched).date()
        when = f", 수집 {lo}" + (f"~{hi}" if hi != lo else "")
    lines.append(
        f"- 출처: Genius API 공식 크레딧·관계 데이터{when}. 아래 항목은 트랙 단위로 "
        "`[확인: Genius]`로 인용 가능(⚠︎ 표시 트랙 제외 — 아래 매칭 근거 참조); "
        "웹 출처와 상충하면 상충으로 기록할 것."
    )

    # Per-track evidence FIRST: the credits below are only citable to the extent
    # the reader can check which song they actually came from.
    lines.append("### 매칭 근거 (트랙별 — Genius가 이 트랙이라고 본 곡)")
    divergent = 0
    for r in matched[:EVIDENCE_MAX_LINES]:
        got = r.get("genius_title") or "(곡명 미저장)"
        conf = r.get("match_confidence")
        conf_s = f"{conf:.2f}" if conf is not None else "?"
        flag = ""
        if r.get("genius_title") and _fold_title(r["title"]) != _fold_title(r["genius_title"]):
            flag = " ⚠︎ 곡명 불일치"
            divergent += 1
        url = f" {r['genius_url']}" if r.get("genius_url") else ""
        lines.append(f"- {_track_label(r)} → Genius “{got}” (신뢰도 {conf_s}){url}{flag}")
    if len(matched) > EVIDENCE_MAX_LINES:
        lines.append(f"- … 외 {len(matched) - EVIDENCE_MAX_LINES}트랙 (길이 제한으로 생략)")
    if divergent:
        lines.append(
            f"- ⚠︎ {divergent}건은 우리 트랙 표기와 Genius 곡명이 문자적으로 다르다는 뜻일 뿐, "
            "오매칭 확정이 아니다 (한국어 원제와 로마자·영문 병기가 흔하다). 다만 **같은 아티스트의 "
            "동명이곡**일 수 있으므로, 해당 트랙의 크레딧·관계를 `[확인: Genius]`로 인용하기 전에 "
            "그 Genius 곡이 이 앨범의 그 트랙이 맞는지 확인하고, 확인되지 않으면 상충으로 기록할 것."
        )

    writers: dict[str, int] = {}
    producers: dict[str, int] = {}
    perf: dict[str, int] = {}
    # One attribution map PER ROLE, never one shared map. A person credited in
    # two roles (Beyoncé and The-Dream produce and write on RENAISSANCE) would
    # otherwise pool both roles' tracks under one key, so the count and the
    # track list disagreed and tracks repeated — "The-Dream (3/14트랙 — 1 … · 6
    # BREAK MY SOUL · 6 BREAK MY SOUL · …)".
    attrib_w: dict[str, list[str]] = {}
    attrib_p: dict[str, list[str]] = {}
    attrib_perf: dict[str, list[str]] = {}

    def _seen(bucket: dict[str, int], attrib: dict[str, list[str]],
              key: str, row: dict) -> None:
        bucket[key] = bucket.get(key, 0) + 1
        attrib.setdefault(key, []).append(_track_label(row))

    for r in matched:
        credits = r["credits"] or {}
        for w in set(credits.get("writers") or []):
            _seen(writers, attrib_w, w, r)
        for p in set(credits.get("producers") or []):
            _seen(producers, attrib_p, p, r)
        seen_perf = set()
        for entry in credits.get("performances") or []:
            role = entry.get("role") or ""
            if role.strip().lower() in _BOILERPLATE_ROLES:
                continue
            for a in entry.get("artists") or []:
                seen_perf.add(f"{role} — {a}" if role else a)
        for key in seen_perf:
            _seen(perf, attrib_perf, key, r)

    m = len(matched)
    lines.append(f"### 크레딧 ({m}개 매칭 트랙 집계 — 소수 트랙 크레딧은 출처 트랙 병기)")
    if producers:
        lines.append("- 프로듀서: " + " · ".join(_top_counts(producers, m, 12, attrib_p)))
    if writers:
        lines.append("- 작곡·작사: " + " · ".join(_top_counts(writers, m, 12, attrib_w)))
    recurring_perf = {k: n for k, n in perf.items() if n >= 2} or perf
    if recurring_perf:
        lines.append("- 세션·스태프(반복 크레딧 위주): "
                     + " · ".join(_top_counts(recurring_perf, m, 10, attrib_perf)))

    lines.append("### 샘플·인터폴레이션 / 파생 관계")
    rel_tracks = []
    no_rel = 0
    for r in matched:
        rels = r["relationships"] or {}
        if not rels:
            no_rel += 1
            continue
        parts = []
        for kind, targets in rels.items():
            label = _REL_LABELS.get(kind, kind)
            targets = list(targets or [])
            shown = "; ".join(targets[:4])
            if len(targets) > 4:
                shown += f" 외 {len(targets) - 4}건"
            parts.append(f"{label}: {shown}")
        rel_tracks.append((_track_label(r), parts))
    for label, parts in rel_tracks:
        lines.append(f"- {label}: " + " / ".join(parts))
    if no_rel:
        lines.append(
            f"- 관계 없음(확인): {no_rel}/{m}트랙 — 매칭된 트랙에 등재된 샘플·인터폴레이션·파생 "
            "관계가 없음을 확인. (미매칭 트랙의 관계 유무는 확인 불가로 남음)"
        )
    # No separate link section: the per-track 근거 URLs now sit in 매칭 근거 above,
    # for every matched track rather than only the ones carrying a relationship.
    # That gap is what left 9 matched tracks with 0 links on ONYX (2026-07-30).

    block = "\n".join(lines) + "\n"
    if len(block) > GENIUS_BLOCK_MAX_CHARS:
        block = block[:GENIUS_BLOCK_MAX_CHARS] + "\n… (Genius 블록 길이 초과로 절단)\n"
    return block


def _genius_block(conn, album_id) -> str:
    """Fetch + render the facts block.

    Failure semantics are deliberately split: a DB failure PROPAGATES — the row
    is marked `failed`, which is retryable, and no subscription call has been
    spent yet — because a silently factless note goes `done` and is never
    re-researched. A RENDER failure fails open with an explicit tier ban: a
    rendering bug must degrade the prompt, not block research indefinitely.
    """
    with conn.cursor() as cur:
        cur.execute(GENIUS_FACTS_SQL, (album_id,))
        rows = cur.fetchall()
    try:
        return _render_genius_block(rows)
    except Exception as e:  # noqa: BLE001 — render-only fail-open
        log.warning("genius facts render failed for album %s: %s", album_id, e)
        return (
            "## Genius 확인 사실 (파이프라인 제공)\n"
            "- 수집 데이터 정리 실패 — 이번 런에서는 Genius 사실을 사용할 수 없다. "
            "[확인: Genius] 표기를 사용하지 말 것.\n"
        )


# Pipeline addendum (RFC "Prompt vendoring"): there is no human mid-run, so the
# model must pin the release itself and emit ONLY the note markdown.
#
# The disambiguation bullet deliberately names NO fixed section. It used to say
# "record it inside the 앨범 식별 section", which v2 has and v4 does not — under v4
# that instruction points at nothing. Keep it section-agnostic so one addendum is
# correct for every vendored prompt version. Nothing here is addressed to a human
# reader: every line the model receives should be an instruction it can act on.
ADDENDUM = """
---
## Pipeline addendum (headless — no human in the loop)

This runs unattended; there is NO human to confirm with mid-run. Therefore:
- Workflow step 1 (disambiguate): do NOT pause to ask, and never end the run
  asking for confirmation. Pin the exact release yourself from the album
  metadata below (artist, title, release date, label, Spotify id). Record any
  residual ambiguity **inside whichever section the output format above uses for
  identification, or failing that its unconfirmed-items section** — never stop.
- Your ENTIRE reply must be ONLY the research-note markdown (the Output-format
  sections above, Korean headers). No preamble, no "Here is…", no closing line.
"""

REFINE_HEADER = """
## 보강 요청 (refine)
아래는 이전에 생성된 리서치 노트다. 폐기하지 말고, 다음 지시를 반영해 **전체 노트를
업데이트**해서 반환하라(기존의 좋은 내용은 유지, 정직성 규칙 동일 — 새 주장에는 새 출처 필수).
출력은 동일하게 노트 마크다운만.

### 지시
{instruction}

### 기존 노트
{prior_note}
"""


def build_prompt(base: str, meta: dict, *, refine: bool, prior_note: str | None,
                 instruction: str | None, genius_block: str | None = None) -> str:
    parts = [base, ADDENDUM, _album_block(meta)]
    if genius_block:
        parts.append(genius_block)
    if refine:
        parts.append(REFINE_HEADER.format(
            instruction=(instruction or "(지시 없음 — 출처 재검증 및 보강)").strip(),
            prior_note=(prior_note or "").strip(),
        ))
    return "\n".join(parts)


# --- claude -p (via shared_db CliEngine) -----------------------------------
# P4 cutover #1 (FEAT-multi-user-accounts-p4-llmengine): argv byte-parity with
# the previous inline subprocess call is pinned by shared_db
# tests/test_llm_engine.py::test_golden_argv_research_poller. No metering
# session_factory yet — this poller never wrote llm_usage; wiring pollers into
# owner-audit metering is a separate decision.
ENGINE = CliEngine()


def run_claude(prompt: str) -> dict:
    """Run headless Claude Code via CliEngine; return {result, tokens_in,
    tokens_out, search_count, model}. Raises LLMTransientError /
    LLMValidationError so the caller can mark the row failed.

    search_count: LLMResult does not surface `usage.server_tool_use`, so this
    now always records 0. The field was already documented as unreliable (the
    `claude -p` JSON aggregate often reported 0 even when the model demonstrably
    fetched — 2026-06-11); the citations inside result_md remain the real
    grounding evidence. tokens_in stays cache-inclusive (an order-of-magnitude
    audit field, not a bill — $0 on the subscription).
    """
    res = coordinated_run(ENGINE, LLMJob(
        feature="research_poller",
        prompt=prompt,
        model=CLAUDE_MODEL,
        tools=ToolPolicy(allowed=("WebSearch", "WebFetch")),
        output_mode="json",
        timeout_s=CLAUDE_TIMEOUT_S,
    ), feature="research_poller")
    return {
        "result": res.result,
        "tokens_in": res.tokens_in,
        "tokens_out": res.tokens_out,
        "search_count": 0,
        "model": res.model or CLAUDE_MODEL,
    }


# --- db ops ---------------------------------------------------------------
# The Genius readiness gate: a claimable row is HELD while any of its album's
# tracks still lacks a track_genius_songs row. Any row counts as attempted —
# matched, ambiguous and not_found alike — so a permanent match failure never
# blocks the album. The GENIUS_WAIT_MAX escape hatch turns "stuck" into
# "partial": past it the row claims regardless, and the prompt says so.
# (failed/refined rows carry an old requested_at, so they claim immediately.)
CLAIM_SQL = f"""
UPDATE album_research SET status = 'running', started_at = now()
WHERE id = (
    SELECT ar.id FROM album_research ar
    WHERE (ar.status IN ('queued', 'failed')
       OR (ar.status = 'running' AND ar.started_at < now() - INTERVAL '{STALE_RUNNING}'))
      AND (
        ar.requested_at < now() - INTERVAL '{GENIUS_WAIT_MAX}'
        OR NOT EXISTS (
            SELECT 1 FROM tracks t
            LEFT JOIN track_genius_songs g ON g.track_id = t.id
            WHERE t.album_id = ar.album_id AND g.track_id IS NULL
        )
      )
    ORDER BY ar.requested_at
    LIMIT 1
    FOR UPDATE SKIP LOCKED
)
RETURNING id, album_id, prompt_version, refine_count, last_instruction, result_md;
"""

# Albums whose research is waiting on the gate above (still inside the wait
# window). Each gets an SQS nudge so the worker collects them NOW instead of at
# the next hourly cron — the nudge is idempotent on the worker side (it selects
# only still-missing tracks, and every write is an ON CONFLICT upsert).
GENIUS_PENDING_SQL = f"""
SELECT ar.album_id
FROM album_research ar
WHERE (ar.status IN ('queued', 'failed')
   OR (ar.status = 'running' AND ar.started_at < now() - INTERVAL '{STALE_RUNNING}'))
  AND ar.requested_at >= now() - INTERVAL '{GENIUS_WAIT_MAX}'
  AND EXISTS (
      SELECT 1 FROM tracks t
      LEFT JOIN track_genius_songs g ON g.track_id = t.id
      WHERE t.album_id = ar.album_id AND g.track_id IS NULL
  )
GROUP BY ar.album_id
ORDER BY min(ar.requested_at)
LIMIT {NUDGE_MAX_ALBUMS};
"""

ALBUM_SQL = """
SELECT a.title, a.release_date, a.label, a.spotify_id, a.album_type, a.total_tracks,
       COALESCE(
           array_agg(ar.name ORDER BY ar.name) FILTER (WHERE ar.name IS NOT NULL),
           '{}'
       ) AS artists
FROM albums a
LEFT JOIN album_artists aa ON aa.album_id = a.id
LEFT JOIN artists ar ON ar.id = aa.artist_id
WHERE a.id = %s
GROUP BY a.id;
"""

# One row per album track, with its Genius songs row when collected. The
# album-level facts (R1) are DERIVED from the track store at prompt-build time —
# there is no separate album_genius_facts table (RFC §6.9 O3, re-resolved
# 2026-07-29 against the implemented state: the track tables already accumulate
# credits/relationships, and a second fetched store could silently disagree).
GENIUS_FACTS_SQL = """
SELECT t.title, t.track_no, g.match_status, g.match_confidence,
       g.genius_title, g.genius_artist,
       g.genius_url, g.credits, g.relationships, g.fetched_at
FROM tracks t
LEFT JOIN track_genius_songs g ON g.track_id = t.id
WHERE t.album_id = %s
ORDER BY t.track_no NULLS LAST, t.title;
"""


def claim_row(conn) -> dict | None:
    with conn.cursor() as cur:
        cur.execute(CLAIM_SQL)
        row = cur.fetchone()
    conn.commit()  # release the row lock; 'running' is now visible to other pollers
    return row


def _load_nudge_state() -> dict:
    try:
        return json.loads(_NUDGE_STATE.read_text())
    except Exception:  # noqa: BLE001 — missing/corrupt state = empty state
        return {}


def _save_nudge_state(state: dict) -> None:
    try:
        _NUDGE_STATE.parent.mkdir(parents=True, exist_ok=True)
        _NUDGE_STATE.write_text(json.dumps(state))
    except Exception as e:  # noqa: BLE001 — cooldown is best-effort
        log.warning("nudge state not saved: %s", e)


def _nudge_unready_albums(conn) -> None:
    """SQS-nudge the worker for albums whose research is held by the Genius gate.

    Duplicate nudges are DB-safe (the worker selects only still-missing tracks;
    every write is an ON CONFLICT upsert), but not free — each one is a Lambda
    invoke and up to 45 Genius API calls — so a local state file bounds re-fires
    to one per album per NUDGE_COOLDOWN_S. Fail-open: any failure here (no AWS
    creds, queue missing, SQL error) is logged and the hourly worker cron
    remains the fallback collection path.
    """
    try:
        with conn.cursor() as cur:
            cur.execute(GENIUS_PENDING_SQL)
            albums = [str(r["album_id"]) for r in cur.fetchall()]
        # Release the read transaction BEFORE any AWS call — holding it across
        # network I/O is the Neon idle-in-txn failure this repo has already hit.
        conn.commit()
        if not albums:
            return
        now = time.time()
        state = {k: v for k, v in _load_nudge_state().items() if now - v < 7200}
        due = [a for a in albums if now - state.get(a, 0) >= NUDGE_COOLDOWN_S]
        if not due:
            return
        import boto3

        sqs = boto3.client("sqs", region_name=REGION)
        url = sqs.get_queue_url(QueueName=SQS_QUEUE_NAME)["QueueUrl"]
        for album_id in due:
            sqs.send_message(
                QueueUrl=url,
                MessageBody=json.dumps({"job": "genius_fetch", "album_id": album_id}),
            )
            state[album_id] = now
        _save_nudge_state(state)
        log.info("nudged genius_fetch for %d waiting album(s)", len(due))
    except Exception as e:  # noqa: BLE001 — fail-open by design
        log.warning("genius nudge skipped: %s", e)
        try:
            conn.rollback()  # a failed SELECT must not poison the claim that follows
        except Exception:  # noqa: BLE001
            pass


def album_meta(conn, album_id) -> dict:
    with conn.cursor() as cur:
        cur.execute(ALBUM_SQL, (album_id,))
        row = cur.fetchone()
    if row is None:
        raise RuntimeError(f"album {album_id} not found")
    return row


def mark_done(conn, row_id, res: dict) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE album_research
            SET status = 'done', result_md = %s, model = %s,
                tokens_in = %s, tokens_out = %s, search_count = %s,
                error = NULL, finished_at = now()
            WHERE id = %s;
            """,
            (res["result"], res["model"], res["tokens_in"], res["tokens_out"],
             res["search_count"], row_id),
        )
    conn.commit()


def mark_failed(conn, row_id, error: str) -> None:
    # Refine keeps the prior result_md (this UPDATE never touches it), so a failed
    # refine degrades to "old note + error", never an empty panel.
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE album_research SET status = 'failed', error = %s, finished_at = now() WHERE id = %s;",
            (error[:4000], row_id),
        )
    conn.commit()


# --- orchestration --------------------------------------------------------
def _mark_research_done_fresh(row_id, res: dict) -> None:
    conn = connect()
    try:
        mark_done(conn, row_id, res)
    finally:
        conn.close()


def _mark_research_failed_fresh(row_id, error: str) -> None:
    conn = connect()
    try:
        mark_failed(conn, row_id, error)
    finally:
        conn.close()


def process_one(base_prompt: str) -> bool:
    """Claim and process one row. Returns True if a row was handled, False if the
    queue was empty."""
    row = None
    try:
        # Do not turn a known shared cooldown into one new running row per
        # launchd firing. The model dispatch rechecks under the same lock.
        ensure_subscription_available()
        read_conn = connect()
        try:
            # Before claiming: ask the worker to collect Genius rows for any album
            # still held by the readiness gate, so collection overlaps this run
            # (or the idle wait) instead of waiting for the hourly cron.
            _nudge_unready_albums(read_conn)
            row = claim_row(read_conn)
            if row is None:
                return False
            meta = album_meta(read_conn, row["album_id"])
            genius_block = _genius_block(read_conn, row["album_id"])
        finally:
            # Materialize the claimed job before any shared-lock wait or web/model call.
            read_conn.close()

        row_id = row["id"]
        refine = bool(row["result_md"])  # restart clears result_md; first-run never had one
        kind = "refine" if refine else "research"
        if row["prompt_version"] != PROMPT_VERSION:
            log.warning("row %s prompt_version=%s but poller vendors %s — using vendored",
                        row_id, row["prompt_version"], PROMPT_VERSION)
        log.info("claimed %s [%s] album=%s — %s", row_id, kind, meta["title"], meta["artists"])
        prompt = build_prompt(
            base_prompt, meta,
            refine=refine,
            prior_note=row["result_md"],
            instruction=row["last_instruction"],
            genius_block=genius_block,
        )
        t0 = time.monotonic()
        res = run_claude(prompt)
        dt = time.monotonic() - t0
        _mark_research_done_fresh(row_id, res)
        log.info(
            "done %s in %.1fs — %d chars, tokens_in=%d tokens_out=%d web=%d model=%s",
            row_id, dt, len(res["result"]), res["tokens_in"], res["tokens_out"],
            res["search_count"], res["model"],
        )
    except LLMSubscriptionCooldown:
        # Keep status=running as the existing 20-minute stale-claim retry gate;
        # do not turn a shared cooldown into an immediate failed-row retry loop.
        raise
    except Exception as e:  # noqa: BLE001 — any failure marks the row, loop continues
        if row is None:
            raise
        row_id = row["id"]
        log.error("FAILED %s: %s", row_id, e)
        _mark_research_failed_fresh(row_id, str(e))
    return True


def main() -> None:
    ap = argparse.ArgumentParser(description="$0 local poller for album research notes.")
    ap.add_argument("--once", action="store_true",
                    help="drain the queue once and exit (no idle polling loop)")
    ap.add_argument("--interval", type=int, default=DEFAULT_INTERVAL_S,
                    help=f"idle poll interval seconds (default {DEFAULT_INTERVAL_S})")
    ap.add_argument("--sleep", type=int, default=DEFAULT_INTER_RUN_SLEEP_S,
                    help=f"inter-run sleep seconds, rate-limit guard (default {DEFAULT_INTER_RUN_SLEEP_S})")
    args = ap.parse_args()

    base_prompt = load_base_prompt()
    log.info("poller up (model=%s, prompt=%s, db=myblog/backend)", CLAUDE_MODEL, PROMPT_VERSION)
    try:
        while True:
            try:
                handled = process_one(base_prompt)
            except LLMSubscriptionCooldown as e:
                log.info(
                    "subscription cooldown — stopping this firing; queue work remains retryable: %s",
                    e,
                )
                return
            if handled:
                time.sleep(args.sleep)        # serial spacing between runs
                continue
            # queue empty
            if args.once:
                log.info("queue empty — exiting (--once)")
                return
            time.sleep(args.interval)
    except KeyboardInterrupt:
        log.info("interrupted — exiting")


if __name__ == "__main__":
    main()
