"""Dedicated local Sign in with ChatGPT credentials. Never reads Codex/API keys."""
from __future__ import annotations

import base64
import fcntl
import hashlib
import hmac
import json
import os
import secrets
import stat
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import urlencode, urlsplit
from uuid import uuid4

import httpx
from jose import JWTError, jwt

ISSUER = "https://auth.openai.com"
RESOURCE = "https://api.openai.com/v1"
AUTHORIZE = ISSUER + "/api/accounts/authorize"
TOKEN = ISSUER + "/api/accounts/oauth/token"
REQUIRED = {"resource.invoke", "chatgpt.tokens.use.direct"}
SCOPES = "openid profile email offline_access resource.invoke chatgpt.tokens.use.direct"
DEFAULT_DIR = Path.home() / ".local/share/myblog-gpt"


class PlanUnavailable(RuntimeError):
    """Stop the consumer; credentials/details must not appear in exception text."""


class PrivateState:
    def __init__(self, directory: Path = DEFAULT_DIR):
        self.directory = directory
        if directory.is_symlink():
            raise PlanUnavailable("Unsafe state directory")
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        info = directory.stat()
        if info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise PlanUnavailable("State directory must be private (0700)")

    def _path(self, name):
        if not name.replace("-", "").replace(".", "").isalnum():
            raise ValueError("Invalid state filename")
        path = self.directory / name
        if path.is_symlink():
            raise PlanUnavailable("Unsafe state file")
        return path

    def read(self, name, default=None):
        path = self._path(name)
        try:
            descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        except FileNotFoundError:
            return default
        with os.fdopen(descriptor) as handle:
            info = os.fstat(handle.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
                raise PlanUnavailable("State file must be private (0600)")
            return json.load(handle)

    def write(self, name, value):
        path = self._path(name)
        descriptor, temporary = tempfile.mkstemp(prefix=".write-", dir=self.directory)
        try:
            with os.fdopen(descriptor, "w") as handle:
                os.fchmod(handle.fileno(), 0o600)
                json.dump(value, handle, ensure_ascii=False)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
        finally:
            Path(temporary).unlink(missing_ok=True)

    @contextmanager
    def lock(self, name="account.lock", blocking=True):
        descriptor = os.open(self._path(name), os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        with os.fdopen(descriptor, "r+") as handle:
            info = os.fstat(handle.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
                raise PlanUnavailable("Lock file must be private")
            fcntl.flock(handle, fcntl.LOCK_EX | (0 if blocking else fcntl.LOCK_NB))
            yield

    def host_id(self):
        with self.lock():
            host = self.read("host.json")
            if host is None:
                host = {"id": "urn:uuid:" + str(uuid4())}
                self.write("host.json", host)
            return host["id"]

    def settings(self):
        return self.read("settings.json", {"enabled": False, "daily_cap": 10, "active": None, "model": None})


class PlanAccount:
    def __init__(self, state: PrivateState, client=None):
        self.state = state
        self.client = client or httpx.Client(timeout=30, follow_redirects=False)

    def begin(self, redirect_uri, returning=None):
        parsed = urlsplit(redirect_uri)
        if (parsed.scheme != "http" or parsed.hostname != "127.0.0.1" or not parsed.port
                or parsed.path != "/auth/callback" or parsed.query or parsed.fragment or parsed.username):
            raise PlanUnavailable("Invalid loopback callback")
        verifier = secrets.token_urlsafe(48)
        pending = {"state": secrets.token_urlsafe(32), "nonce": secrets.token_urlsafe(32),
                   "verifier": verifier, "redirect_uri": redirect_uri, "created": time.time(),
                   "client_id": returning["client_id"] if returning else "dynamic_agent_client",
                   "subject": returning["subject"] if returning else None}
        query = {"client_id": pending["client_id"], "ext_agent_host_id": self.state.host_id(),
                 "response_type": "code", "redirect_uri": redirect_uri, "scope": SCOPES,
                 "resource": RESOURCE, "state": pending["state"], "nonce": pending["nonce"],
                 "code_challenge_method": "S256",
                 "code_challenge": base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")}
        if returning:
            if returning.get("id_token"):
                query["id_token_hint"] = returning["id_token"]
        else:
            query["agent_name_hint"] = "MyBlog GPT translation worker"
        # Caller holds this in memory only. Never log an authorization URL containing an ID token hint.
        return pending, AUTHORIZE + "?" + urlencode(query)

    def validate_identity(self, token, client_id, nonce=None, access_token=None):
        response = self.client.get(ISSUER + "/.well-known/jwks.json")
        if response.status_code != 200:
            raise PlanUnavailable("Identity verification unavailable")
        try:
            keys = response.json()
            kid = jwt.get_unverified_header(token).get("kid")
            key = next(k for k in keys["keys"] if k.get("kid") == kid)
            # OpenAI ID tokens carry at_hash; jose refuses them unless given the paired access token,
            # and then also proves the ID token was issued together with that access token.
            claims = jwt.decode(token, key, algorithms=["RS256"], issuer=ISSUER, audience=client_id,
                                access_token=access_token,
                                options={"require_exp": True, "require_sub": True, "require_aud": True})
            if nonce is not None and not hmac.compare_digest(str(claims.get("nonce", "")), nonce):
                raise JWTError("nonce")
            if not isinstance(claims.get("sub"), str) or not claims["sub"]:
                raise JWTError("subject")
            return claims
        except (JWTError, ValueError, TypeError, KeyError, StopIteration):
            raise PlanUnavailable("Identity verification failed") from None

    @staticmethod
    def granted(response, previous=None):
        scope = response.get("scope")
        if scope is not None and not isinstance(scope, str):
            raise PlanUnavailable("Invalid returned permission")
        scopes = scope.split() if isinstance(scope, str) else (previous or {}).get("scopes", [])
        if not REQUIRED.issubset(scopes):
            raise PlanUnavailable("ChatGPT plan use is not authorized")
        if response.get("token_type", "").lower() != "bearer" or not response.get("access_token"):
            raise PlanUnavailable("Invalid credential response")
        return scopes

    def finish(self, pending, query):
        state = query.get("state", "")
        if time.time() - pending["created"] > 600 or not hmac.compare_digest(state, pending["state"]):
            raise PlanUnavailable("Sign-in expired or did not match")
        if query.get("error"):
            raise PlanUnavailable("Sign-in permission was declined")
        client_id = query.get("client_id", pending["client_id"])
        if not client_id or client_id == "dynamic_agent_client" or not query.get("code"):
            raise PlanUnavailable("Client registration incomplete")
        if pending["client_id"] != "dynamic_agent_client" and client_id != pending["client_id"]:
            raise PlanUnavailable("Returning client does not match")
        response = self.client.post(TOKEN, data={"grant_type": "authorization_code", "client_id": client_id,
            "code": query["code"], "code_verifier": pending["verifier"],
            "redirect_uri": pending["redirect_uri"], "resource": RESOURCE})
        if response.status_code != 200:
            raise PlanUnavailable("Sign-in exchange failed; start again")
        tokens = response.json()
        scopes = self.granted(tokens)
        claims = self.validate_identity(tokens.get("id_token", ""), client_id, pending["nonce"],
                                        access_token=tokens.get("access_token"))
        if pending["subject"] is not None and claims["sub"] != pending["subject"]:
            raise PlanUnavailable("Returning account does not match")
        if not tokens.get("refresh_token"):
            raise PlanUnavailable("Renewable plan permission was not granted")
        record = {**tokens, "issuer": ISSUER, "subject": claims["sub"], "email": claims.get("email", ""),
                  "client_id": client_id, "scopes": scopes, "expires_at": time.time() + int(tokens["expires_in"])}
        key = hashlib.sha256((client_id + "\x00" + claims["sub"]).encode()).hexdigest()
        with self.state.lock():
            self.state.write(key + ".json", record)
            settings = self.state.settings()
            # Sign-in never starts background inference by itself.
            settings.update(active=key, enabled=False, model=None, pause_reason=None)
            self.state.write("settings.json", settings)
        return key, record

    def credentials(self):
        with self.state.lock():
            settings = self.state.settings()
            key = settings.get("active")
            record = self.state.read(key + ".json") if key else None
            if not record or not REQUIRED.issubset(record.get("scopes", [])):
                raise PlanUnavailable("Continue with ChatGPT is required")
            if record.get("expires_at", 0) > time.time() + 120:
                return record
            if not record.get("refresh_token") or not record.get("access_token"):
                raise PlanUnavailable("Continue with ChatGPT is required")
            response = self.client.post(TOKEN, data={"grant_type": "refresh_token", "client_id": record["client_id"],
                "refresh_token": record["refresh_token"], "resource": RESOURCE})
            if response.status_code != 200:
                try:
                    failure = response.json()
                    code = failure.get("error")
                    if isinstance(code, dict):
                        code = code.get("code")
                except (ValueError, AttributeError):
                    code = None
                if code in {"invalid_grant", "invalid_refresh_token", "token_expired", "refresh_token_expired",
                            "refresh_token_invalidated", "refresh_token_reused"}:
                    for field in ("access_token", "refresh_token", "id_token"):
                        record.pop(field, None)
                    record["expires_at"] = 0
                    self.state.write(key + ".json", record)
                raise PlanUnavailable("Plan session renewal failed; review sign-in")
            tokens = response.json()
            scopes = self.granted(tokens, record)
            if tokens.get("id_token"):
                identity = self.validate_identity(tokens["id_token"], record["client_id"],
                                                  access_token=tokens.get("access_token"))
                if identity["sub"] != record["subject"]:
                    raise PlanUnavailable("Renewed account does not match")
            record.update(tokens, scopes=scopes, expires_at=time.time() + int(tokens["expires_in"]))
            self.state.write(key + ".json", record)
            return record

    def models(self):
        record = self.credentials()
        response = self.client.get(RESOURCE + "/models", headers={"Authorization": "Bearer " + record["access_token"]})
        if response.status_code != 200:
            raise PlanUnavailable("Account model catalog is unavailable")
        return [{"slug": m["slug"], "display_name": m.get("display_name", m["slug"])}
                for m in response.json().get("models", []) if m.get("visibility") == "list"]
