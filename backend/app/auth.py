"""
Authentication and authorisation (stdlib only).

 * Passwords: PBKDF2-HMAC-SHA256, per-user random salt, 600k iterations (stored as "pbkdf2_sha256$iters$salt$hash").
 * Sessions: signed HS256 tokens (JWT format) with an expiry. The user is re-read from the database on every
   request, so a deleted user or a changed role takes effect immediately.
 * Roles: employee < support_engineer < admin.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from collections import defaultdict
from typing import Any, Callable, Optional

from fastapi import Depends, Header, HTTPException

from .config import settings
from .db.repo import get_repo, public_user

ROLES = ("employee", "support_engineer", "admin")
STAFF = ("support_engineer", "admin")
PBKDF2_ITERS = 600_000


# ---------- passwords ----------
def _b64e(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def _b64d(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def hash_password(password: str, iterations: Optional[int] = None) -> str:
    iters = iterations or PBKDF2_ITERS
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iters)
    return f"pbkdf2_sha256${iters}${_b64e(salt)}${_b64e(dk)}"


def verify_password(password: str, stored: Optional[str]) -> bool:
    try:
        scheme, iters, salt, digest = (stored or "").split("$")
        if scheme != "pbkdf2_sha256":
            return False
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(), _b64d(salt), int(iters))
        return hmac.compare_digest(dk, _b64d(digest))
    except Exception:  # malformed hash
        return False


# A real hash to compare against when the email is unknown, so timing doesn't reveal which emails exist.
_DUMMY_HASH = hash_password("not-a-real-password", iterations=1000)


# ---------- tokens ----------
def _sign(data: bytes) -> str:
    return _b64e(hmac.new(settings.auth_secret.encode(), data, hashlib.sha256).digest())


def create_token(user: dict[str, Any]) -> str:
    now = int(time.time())
    header = _b64e(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode())
    payload = _b64e(json.dumps({"sub": user["user_id"], "role": user["role"], "iat": now,
                                "exp": now + settings.token_ttl_hours * 3600}, separators=(",", ":")).encode())
    return f"{header}.{payload}.{_sign(f'{header}.{payload}'.encode())}"


def decode_token(token: str) -> dict[str, Any]:
    try:
        header_b64, payload_b64, sig = token.split(".")
        if not hmac.compare_digest(sig, _sign(f"{header_b64}.{payload_b64}".encode())):
            raise ValueError("bad signature")
        if json.loads(_b64d(header_b64)).get("alg") != "HS256":
            raise ValueError("bad alg")
        payload = json.loads(_b64d(payload_b64))
        if int(payload["exp"]) < time.time():
            raise ValueError("expired")
        return payload
    except Exception as exc:
        raise HTTPException(401, "Your session is invalid or has expired. Please sign in again.") from exc


# ---------- login throttling ----------
_FAILS: dict[str, list[float]] = defaultdict(list)
MAX_FAILS, WINDOW_S = 5, 15 * 60


def check_rate_limit(key: str) -> None:
    now = time.time()
    _FAILS[key] = [t for t in _FAILS[key] if now - t < WINDOW_S]
    if len(_FAILS[key]) >= MAX_FAILS:
        raise HTTPException(429, "Too many failed sign-in attempts. Try again in 15 minutes.")


def record_failure(key: str) -> None:
    _FAILS[key].append(time.time())


def clear_failures(key: str) -> None:
    _FAILS.pop(key, None)


# ---------- dependencies ----------
def current_user(authorization: Optional[str] = Header(None)) -> dict[str, Any]:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "Sign in to continue.")
    payload = decode_token(authorization.split(" ", 1)[1].strip())
    user = get_repo().get("users", payload["sub"])
    if not user:
        raise HTTPException(401, "This account no longer exists. Please sign in again.")
    return public_user(user)


def require_roles(*roles: str) -> Callable[..., dict[str, Any]]:
    def dependency(user: dict[str, Any] = Depends(current_user)) -> dict[str, Any]:
        if user["role"] not in roles:
            raise HTTPException(403, "Your role does not have access to this.")
        return user
    return dependency


staff_only = require_roles(*STAFF)
admin_only = require_roles("admin")
