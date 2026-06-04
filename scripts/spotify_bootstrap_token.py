#!/usr/bin/env python3
"""One-time Spotify refresh-token bootstrap (FEAT-member-dashboard Step 3, D27).

The /me/player/* endpoints are user-scoped, so the worker needs a refresh token
minted via the Authorization-Code flow — which requires a human to approve consent
in a browser once. Rather than build a full in-app OAuth UI (deferred per D27), an
admin runs this script once; the resulting refresh token is stored in Secrets
Manager `myblog/spotify` and the worker uses it forever after.

ONE-TIME SETUP (Spotify Developer Dashboard, https://developer.spotify.com):
  Add this exact Redirect URI to the app's settings:
      http://127.0.0.1:8888/callback

REQUIRES: httpx (+ boto3 for --write).  pip install httpx boto3

USAGE:
  export SPOTIFY_CLIENT_ID=...        # the app's client id
  export SPOTIFY_CLIENT_SECRET=...    # the app's client secret
  python scripts/spotify_bootstrap_token.py            # prints the refresh token
  python scripts/spotify_bootstrap_token.py --write    # also writes myblog/spotify

The token value is NEVER logged or printed unless you pass --show (avoid that on a
shared terminal). With --write it goes straight into Secrets Manager.

Scopes requested (read-only; write scopes deferred per D11):
  user-read-recently-played, user-read-currently-playing
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import secrets
import sys
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer

import httpx

REDIRECT_URI = "http://127.0.0.1:8888/callback"
SCOPES = "user-read-recently-played user-read-currently-playing"
AUTH_URL = "https://accounts.spotify.com/authorize"
TOKEN_URL = "https://accounts.spotify.com/api/token"
SECRET_ID = "myblog/spotify"
REGION = "ap-northeast-2"


class _CallbackHandler(BaseHTTPRequestHandler):
    code: str | None = None
    state_expected: str | None = None
    error: str | None = None

    def do_GET(self):  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path != "/callback":
            self.send_response(404)
            self.end_headers()
            return
        params = urllib.parse.parse_qs(parsed.query)
        if params.get("state", [""])[0] != _CallbackHandler.state_expected:
            _CallbackHandler.error = "state mismatch (possible CSRF)"
        elif "error" in params:
            _CallbackHandler.error = params["error"][0]
        else:
            _CallbackHandler.code = params.get("code", [None])[0]
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        msg = "인증 실패" if _CallbackHandler.error else "인증 완료 — 터미널로 돌아가세요"
        self.wfile.write(f"<html><body><h2>{msg}</h2></body></html>".encode())

    def log_message(self, format, *args):  # noqa: A002 — silence default logging
        return


def _capture_code(client_id: str) -> str:
    state = secrets.token_urlsafe(16)
    _CallbackHandler.state_expected = state
    query = urllib.parse.urlencode({
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPES,
        "state": state,
    })
    url = f"{AUTH_URL}?{query}"
    print("브라우저에서 Spotify 동의 화면을 엽니다. 안 열리면 아래 URL을 직접 여세요:\n", url)
    webbrowser.open(url)

    server = HTTPServer(("127.0.0.1", 8888), _CallbackHandler)
    while _CallbackHandler.code is None and _CallbackHandler.error is None:
        server.handle_request()
    server.server_close()

    if _CallbackHandler.error:
        sys.exit(f"OAuth 실패: {_CallbackHandler.error}")
    assert _CallbackHandler.code
    return _CallbackHandler.code


def _exchange(code: str, client_id: str, client_secret: str) -> str:
    basic = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    r = httpx.post(
        TOKEN_URL,
        headers={"Authorization": f"Basic {basic}", "Content-Type": "application/x-www-form-urlencoded"},
        data={"grant_type": "authorization_code", "code": code, "redirect_uri": REDIRECT_URI},
        timeout=20,
    )
    r.raise_for_status()
    token = r.json().get("refresh_token")
    if not token:
        sys.exit("응답에 refresh_token이 없습니다 (이미 동의된 앱이면 재동의 필요할 수 있음)")
    return token


def _write_secret(client_id: str, client_secret: str, refresh_token: str) -> None:
    import boto3

    sm = boto3.client("secretsmanager", region_name=REGION)
    # Merge into any existing payload so unrelated keys survive. Only treat a
    # genuinely-absent secret as empty — any other read error must abort rather
    # than clobber the existing keys.
    try:
        existing = json.loads(sm.get_secret_value(SecretId=SECRET_ID)["SecretString"])
    except sm.exceptions.ResourceNotFoundException:
        existing = {}
    existing.update({
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
    })
    sm.put_secret_value(SecretId=SECRET_ID, SecretString=json.dumps(existing))
    print(f"✅ refresh token을 Secrets Manager {SECRET_ID} 에 저장했습니다 (값은 출력하지 않음).")


def main() -> None:
    ap = argparse.ArgumentParser(description="Mint a Spotify user refresh token (one-time).")
    ap.add_argument("--write", action="store_true", help=f"write the token to Secrets Manager {SECRET_ID}")
    ap.add_argument("--show", action="store_true", help="print the token (avoid on shared terminals)")
    args = ap.parse_args()

    client_id = os.environ.get("SPOTIFY_CLIENT_ID", "").strip()
    client_secret = os.environ.get("SPOTIFY_CLIENT_SECRET", "").strip()
    if not client_id or not client_secret:
        sys.exit("SPOTIFY_CLIENT_ID / SPOTIFY_CLIENT_SECRET 환경변수를 설정하세요.")

    code = _capture_code(client_id)
    refresh_token = _exchange(code, client_id, client_secret)

    if args.write:
        _write_secret(client_id, client_secret, refresh_token)
    if args.show:
        print("refresh_token:", refresh_token)
    if not args.write and not args.show:
        print("✅ refresh token 발급 완료. 저장하려면 --write, 직접 확인하려면 --show 를 사용하세요.")


if __name__ == "__main__":
    main()
