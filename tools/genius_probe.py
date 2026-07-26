#!/usr/bin/env python3
"""FEAT-lyrics-annotations R0 — Genius coverage probe over the bucketed catalog.

R0 gates every later step of the RFC. Before building `album_genius_facts` (R1) and
wiring it into the research prompt (R2), measure what Genius would actually return
for the albums this system works on: **how many tracks match at all**, and for the
matched ones, **how often each field the research notes cannot source is present**.

The field set is not chosen by what Genius offers. It is what the pipeline's own
78 stored `album_research` notes record as unobtainable (RFC §6.4): 78/78 failed to
confirm samples, 75/78 failed to confirm credits, and several name recording
location and per-track session players specifically. Those are the four fields
below. A high match rate with empty `song_relationships` would mean R1 buys little.

READ-ONLY. Touches no table, writes only its own JSONL under `tools/out/`.

Resumable, in the shape of `tools/lyrics_batch_api.py`: every probed track appends
one JSON line immediately, and a re-launch skips track ids already present. An
interrupted or rate-limited run is safe to re-run.

Requires the backend venv (boto3 + psycopg) and `GENIUS_ACCESS_TOKEN` in SSM
`/myblog/worker`. The token is never logged (CLAUDE.md never-log list).

Usage:
    myblog_backend/.venv/bin/python tools/genius_probe.py --limit 60     # slice
    myblog_backend/.venv/bin/python tools/genius_probe.py --full-run     # all
    myblog_backend/.venv/bin/python tools/genius_probe.py --report-only  # re-read JSONL
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
import urllib.parse
import urllib.request
from collections import Counter

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
                    stream=sys.stderr)
log = logging.getLogger("genius_probe")

REGION = "ap-northeast-2"
WORKER_PARAM = "/myblog/worker"      # holds GENIUS_ACCESS_TOKEN
BACKEND_PARAM = "/myblog/backend"    # holds DATABASE_URL
API = "https://api.genius.com"
HTTP_TIMEOUT_S = 20                  # CLAUDE.md: outbound HTTP always sets an explicit timeout
SLEEP_S = 0.35                       # ~3 req/s; the anchor-test recipe used 0.3s and held
MAX_RETRIES = 3
OUT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out", "genius_probe.jsonl")

# The four fields the research notes record as unobtainable (RFC §6.4), plus the two
# that decide whether the prose tier (R5) is worth building.
FIELDS = [
    ("relationships", "샘플·인터폴레이션"),
    ("credits",       "작가·프로듀서"),
    ("performances",  "세션 연주자"),
    ("rec_location",  "녹음 장소"),
    ("description",   "해설 산문"),
    ("media",         "외부 식별자"),
]


def _ssm(name: str) -> dict:
    import boto3
    ssm = boto3.client("ssm", region_name=REGION)
    return json.loads(ssm.get_parameter(Name=name, WithDecryption=True)["Parameter"]["Value"])


def _get(path: str, token: str, params: dict) -> dict | None:
    """One Genius GET with retries. Returns the `response` object, or None."""
    url = f"{API}{path}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT_S) as r:
                return json.loads(r.read().decode("utf-8")).get("response")
        except urllib.error.HTTPError as e:
            if e.code == 401:
                raise SystemExit("Genius returned 401 — the token in SSM is rejected. Stopping.")
            if e.code == 404:
                return None
            if e.code == 429 or e.code >= 500:
                wait = SLEEP_S * (4 ** attempt)
                log.warning("HTTP %s on %s — backing off %.1fs (%d/%d)",
                            e.code, path, wait, attempt, MAX_RETRIES)
                time.sleep(wait)
                continue
            log.warning("HTTP %s on %s — giving up on this call", e.code, path)
            return None
        except Exception as e:  # noqa: BLE001 — network flake; retry then skip
            log.warning("%s on %s (%d/%d)", type(e).__name__, path, attempt, MAX_RETRIES)
            time.sleep(SLEEP_S * (2 ** attempt))
    return None


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "").lower()
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"\((feat|with)[^)]*\)|\[[^\]]*\]|- .*(remix|version|edit).*$", " ", s)
    return re.sub(r"[^0-9a-z가-힣]+", "", s)


def probe_track(token: str, artist: str, title: str) -> dict:
    """Search, pick the hit whose normalized title matches, then read its fields."""
    hits = (_get("/search", token, {"q": f"{artist} {title}", "per_page": 5}) or {}).get("hits", [])
    want = _norm(title)
    chosen, how = None, "none"
    for h in hits:
        r = h.get("result") or {}
        if _norm(r.get("title", "")) == want:
            chosen, how = r, "title-exact"
            break
    if chosen is None and hits:
        # Fall back to the first hit only when its artist agrees — an artist mismatch is
        # a wrong song, and counting it inflates the match rate this probe exists to measure.
        r = hits[0].get("result") or {}
        pa = ((r.get("primary_artist") or {}).get("name") or "")
        if _norm(pa) and _norm(pa) in _norm(artist) or _norm(artist) in _norm(pa):
            chosen, how = r, "artist-fallback"
    if chosen is None:
        return {"matched": False, "how": how}

    song = _get(f"/songs/{chosen['id']}", token, {"text_format": "plain"}) or {}
    s = song.get("song") or {}
    desc = (((s.get("description") or {}).get("plain")) or "").strip()
    rels = [r for r in (s.get("song_relationships") or [])
            if r.get("relationship_type") != "translations" and r.get("songs")]
    return {
        "matched": True,
        "how": how,
        "genius_id": chosen["id"],
        "lang": s.get("language"),
        "relationships": sum(len(r.get("songs") or []) for r in rels),
        "rel_types": sorted({r.get("relationship_type") for r in rels if r.get("relationship_type")}),
        "credits": len(s.get("writer_artists") or []) + len(s.get("producer_artists") or []),
        "performances": len(s.get("custom_performances") or []),
        "rec_location": 1 if s.get("recording_location") else 0,
        "description": len(desc) if len(desc) >= 200 else 0,
        "media": len(s.get("media") or []),
        "annotation_count": s.get("annotation_count") or 0,
    }


ALBUM_SQL = """
SELECT a.id AS album_id, a.title AS album, t.id AS track_id, t.track_no, t.title AS track,
       COALESCE((SELECT string_agg(ar.name, ', ' ORDER BY ar.name)
                   FROM album_artists aa JOIN artists ar ON ar.id = aa.artist_id
                  WHERE aa.album_id = a.id), '') AS artist
FROM albums a
JOIN tracks t ON t.album_id = a.id
WHERE a.id IN (SELECT DISTINCT album_id FROM review_bucket_items)
ORDER BY a.title, t.track_no
"""


def load_tracks() -> list[dict]:
    import psycopg
    from psycopg.rows import dict_row
    url = _ssm(BACKEND_PARAM)["DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://", 1)
    with psycopg.connect(url, connect_timeout=60, row_factory=dict_row) as c:
        c.execute("BEGIN READ ONLY")   # txn-scoped; a session-level SET leaks through the pooler
        return list(c.execute(ALBUM_SQL))


def done_ids() -> set[str]:
    if not os.path.exists(OUT_PATH):
        return set()
    out = set()
    with open(OUT_PATH, encoding="utf-8") as f:
        for line in f:
            try:
                out.add(json.loads(line)["track_id"])
            except Exception:  # noqa: BLE001 — a torn last line from an interrupted run
                pass
    return out


def report() -> None:
    rows = []
    with open(OUT_PATH, encoding="utf-8") as f:
        for line in f:
            try:
                rows.append(json.loads(line))
            except Exception:  # noqa: BLE001
                pass
    if not rows:
        print("no rows")
        return
    albums = {r["album_id"] for r in rows}
    matched = [r for r in rows if r.get("matched")]
    print(f"\n=== Genius coverage probe — {len(rows)} tracks / {len(albums)} albums ===\n")
    print(f"track match rate      {len(matched):>5}/{len(rows):<5} {len(matched)/len(rows)*100:5.1f}%")
    exact = sum(1 for r in matched if r.get("how") == "title-exact")
    print(f"  of which exact-title{exact:>5}/{len(matched):<5} "
          f"{(exact/len(matched)*100 if matched else 0):5.1f}%")

    per_album = Counter(r["album_id"] for r in matched)
    full = sum(1 for a in albums if per_album.get(a, 0) ==
               sum(1 for r in rows if r["album_id"] == a))
    none = sum(1 for a in albums if per_album.get(a, 0) == 0)
    print(f"albums fully matched  {full:>5}/{len(albums)}")
    print(f"albums with 0 matches {none:>5}/{len(albums)}")

    print("\n--- fill rate on MATCHED tracks (this is what R1 would store) ---")
    for key, label in FIELDS:
        n = sum(1 for r in matched if (r.get(key) or 0) > 0)
        pct = n / len(matched) * 100 if matched else 0
        print(f"  {label:<14} {n:>5}/{len(matched):<5} {pct:5.1f}%")

    rel = Counter(t for r in matched for t in (r.get("rel_types") or []))
    if rel:
        print("\n--- relationship types found ---")
        for t, n in rel.most_common():
            print(f"  {t:<28} {n}")

    langs = Counter(r.get("lang") or "?" for r in matched)
    print("\n--- language of matched tracks ---")
    for lg, n in langs.most_common(8):
        print(f"  {lg:<6} {n:>5}  ({n/len(matched)*100:4.1f}%)")


def main() -> None:
    ap = argparse.ArgumentParser(description="FEAT-lyrics-annotations R0 coverage probe.")
    ap.add_argument("--limit", type=int, default=60, help="probe at most N tracks (default 60)")
    ap.add_argument("--full-run", action="store_true", help="probe every bucketed track")
    ap.add_argument("--report-only", action="store_true", help="re-read the JSONL and print")
    args = ap.parse_args()

    if args.report_only:
        report()
        return

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    token = _ssm(WORKER_PARAM)["GENIUS_ACCESS_TOKEN"]   # never logged
    tracks = load_tracks()
    already = done_ids()
    todo = [t for t in tracks if str(t["track_id"]) not in already]
    if not args.full_run:
        todo = todo[:args.limit]
    log.info("%d bucketed tracks; %d already probed; probing %d", len(tracks), len(already), len(todo))

    t0 = time.monotonic()
    with open(OUT_PATH, "a", encoding="utf-8") as f:
        for i, t in enumerate(todo, 1):
            res = probe_track(token, t["artist"], t["track"])
            res.update({"track_id": str(t["track_id"]), "album_id": str(t["album_id"]),
                        "album": t["album"], "artist": t["artist"], "track": t["track"]})
            f.write(json.dumps(res, ensure_ascii=False) + "\n")
            f.flush()
            if i % 25 == 0:
                log.info("  %d/%d (%.0fs elapsed)", i, len(todo), time.monotonic() - t0)
            time.sleep(SLEEP_S)
    log.info("probed %d tracks in %.0fs → %s", len(todo), time.monotonic() - t0, OUT_PATH)
    report()


if __name__ == "__main__":
    main()
