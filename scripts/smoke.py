#!/usr/bin/env python3
"""
End-to-end smoke test for the myblog system.

Hits the critical user paths and asserts response shapes. Designed to run
in <60s. Exits 0 on full pass, 1 on any failure.

Usage:
    python3 scripts/smoke.py prod
    python3 scripts/smoke.py local   # backends on :8000 (backend) + :8001 (music)

Required env vars:
    AWS credentials with cognito-idp + secretsmanager:GetSecretValue (for prod)
    MYBLOG_SMOKE_PASSWORD     — Cognito test user password (prod only)
    MYBLOG_SMOKE_EMAIL        — Cognito test user email (default: test@ratemymusic.blog)

Local mode skips Cognito auth (services bypass on ENV=local).
"""
from __future__ import annotations

import json
import os
import sys
import time
import datetime
import urllib.error
import urllib.request

# ---------- Configuration ----------------------------------------------------

# Two backend URLs in prod:
#   "backend_authed" — raw API Gateway, used for Cognito-JWT routes
#       (Bearer-token requests bypass edge_guard at Lambda).
#   "backend_public" — CloudFront, used for unauthed routes
#       (CloudFront function injects x-origin-verify so edge_guard passes).
#   "music"          — CloudFront (same routing as backend_public).
PROD = {
    "backend_authed": "https://ld8pjw3mx4.execute-api.ap-northeast-2.amazonaws.com",
    "backend_public": "https://www.ratemymusic.blog",
    "music":          "https://www.ratemymusic.blog",
}
LOCAL = {
    "backend_authed": "http://localhost:8000",
    "backend_public": "http://localhost:8000",
    "music":          "http://localhost:8001",
}

COGNITO_REGION = "ap-northeast-2"
COGNITO_USER_POOL_ID = "ap-northeast-2_54vEJKEU5"
COGNITO_CLIENT_ID = "68ccmcanfbvla9qbovnb9b18bt"

# ---------- Test framework --------------------------------------------------

class SmokeError(Exception):
    pass

PASSED: list[str] = []
FAILED: list[tuple[str, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    if ok:
        PASSED.append(name)
        print(f"  PASS  {name}" + (f" — {detail}" if detail else ""))
    else:
        FAILED.append((name, detail))
        print(f"  FAIL  {name}" + (f" — {detail}" if detail else ""))


def request_json(url: str, *, method: str = "GET", body: dict | None = None, token: str | None = None) -> tuple[int, dict | None]:
    headers: dict[str, str] = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        resp = urllib.request.urlopen(req, timeout=20)
        raw = resp.read()
        return resp.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as e:
        body_raw = e.read()
        try:
            return e.code, json.loads(body_raw)
        except Exception:
            return e.code, {"raw": body_raw.decode(errors="replace")}


# ---------- Cognito auth ----------------------------------------------------

def get_token() -> str:
    """Get a Cognito access token for the test user (prod only)."""
    try:
        import boto3
    except ImportError:
        print("boto3 not installed — pip install boto3 (needed for prod smoke)")
        sys.exit(2)

    pw = os.environ.get("MYBLOG_SMOKE_PASSWORD")
    email = os.environ.get("MYBLOG_SMOKE_EMAIL", "test@ratemymusic.blog")
    if not pw:
        print("MYBLOG_SMOKE_PASSWORD env var not set — needed for prod smoke")
        sys.exit(2)

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


# ---------- Test suites -----------------------------------------------------

def run_unauth_tests(host: dict[str, str]) -> None:
    print("\n[health + categories + DB]")
    s, b = request_json(host["backend_public"] + "/api/db/ping")
    check("/api/db/ping returns 200", s == 200, f"status={s}")
    check("/api/db/ping body is 'Database connected'",
          b is not None and b.get("message") == "Database connected", str(b))

    s, b = request_json(host["backend_public"] + "/api/categories")
    check("/api/categories returns 200", s == 200)
    check("/api/categories returns list",
          isinstance(b, dict) and "categories" in b and isinstance(b["categories"], list),
          str(b)[:100])

    print("\n[search filter — BUG-2 regression guard]")
    for t in ("album", "artist", "track"):
        s, b = request_json(host["music"] + f"/api/music/search/unified?q=radiohead&type={t}&limit=3")
        check(f"search?type={t} returns 200", s == 200)
        if b:
            empty = [k for k in ("artists", "albums", "tracks") if k != f"{t}s" and b.get(k)]
            check(f"search?type={t} returns only {t}s",
                  len(empty) == 0,
                  f"unexpected non-empty: {empty}" if empty else "")

    print("\n[album detail wrapper — BUG-3 regression guard]")
    s, b = request_json(host["music"] + "/api/music/search/unified?q=radiohead&type=album&limit=1")
    spotify_id = b["albums"][0]["spotify_id"] if (s == 200 and b and b.get("albums")) else None
    check("got an album with spotify_id", spotify_id is not None)
    if spotify_id:
        s, b = request_json(host["music"] + f"/api/music/albums/by-spotify/{spotify_id}")
        check("/albums/by-spotify/{id} returns 200", s == 200)
        check("response has {album, artists, tracks, meta}",
              isinstance(b, dict) and {"album", "artists", "tracks", "meta"}.issubset(set(b)),
              "(missing keys)" if b else "")
        check("album.id is non-empty",
              bool(b and isinstance(b.get("album"), dict) and b["album"].get("id")))
        check("artists list has at least 1 element with id",
              bool(b and b.get("artists") and b["artists"][0].get("id")))


def run_authed_tests(host: dict[str, str], token: str | None) -> None:
    # In local mode, token can be None — backend bypasses on ENV=local.
    print("\n[post CRUD round-trip]")
    # Title must be unique per run: backend now hard-rejects duplicate slugs
    # with 409 (BUG-9), so re-runs after a previous run leaked a row would
    # otherwise collide.
    unique_title = f"SMOKE test {int(time.time())} — do not keep"
    payload = {
        "title": unique_title,
        "description": "smoke",
        "body_mdx": "# smoke",
        "posted_date": str(datetime.date.today()),
        "status": "draft",
        "category": "default",
        "album_ids": [],
        "artist_ids": [],
        "rating": None,
        "album_classics": {},
        "recommended_tracks": [],
    }
    s, b = request_json(host["backend_authed"] + "/api/posts", method="POST", body=payload, token=token)
    check("POST /api/posts returns 200", s == 200, f"status={s}, body={b}")
    if s != 200 or not b:
        return
    post_id = b["id"]

    s, b = request_json(host["backend_authed"] + f"/api/posts/{post_id}", token=token)
    check("GET /api/posts/{id} returns 200", s == 200)
    check("GET detail title matches",
          b is not None and b.get("title") == payload["title"], str(b)[:100] if b else "")

    s, b = request_json(host["backend_authed"] + f"/api/posts/{post_id}",
                        method="PUT", body={"title": "SMOKE updated"}, token=token)
    check("PUT /api/posts/{id} returns 200", s == 200, f"status={s}")

    s, _ = request_json(host["backend_authed"] + f"/api/posts/{post_id}",
                        method="DELETE", token=token)
    # urllib raises HTTPError for 204 (no body); request_json catches that and returns 204 with None
    check("DELETE /api/posts/{id} returns 204", s == 204, f"status={s}")


# ---------- Entry point -----------------------------------------------------

def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] not in ("prod", "local"):
        print(__doc__)
        return 2

    env = sys.argv[1]
    host = PROD if env == "prod" else LOCAL
    print(f"smoke target: {env} (backend={host['backend_public']}, music={host['music']})")
    started = time.time()

    token = None
    if env == "prod":
        token = get_token()

    try:
        run_unauth_tests(host)
        run_authed_tests(host, token)
    except urllib.error.URLError as e:
        print(f"\nFATAL: cannot reach host — {e}")
        return 2

    print("\n" + "=" * 60)
    print(f"PASSED: {len(PASSED)}")
    print(f"FAILED: {len(FAILED)}")
    for name, detail in FAILED:
        print(f"  ✗ {name}: {detail}")
    print(f"elapsed: {time.time() - started:.1f}s")
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
