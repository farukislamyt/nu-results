"""Shared API security/session helpers for NU result modules."""

import base64
import hashlib
import json
import os
import time
from typing import Any

from cryptography.fernet import Fernet, InvalidToken
from fastapi import Request

SESSION_TTL = 5 * 60
RATE_WINDOW = 60
RATE_LIMIT = 20
_rate_cache: dict[str, list[float]] = {}


def session_key() -> bytes:
    configured = os.environ.get("SESSION_SIGNING_SECRET", "")
    if not configured:
        raise RuntimeError("SESSION_SIGNING_SECRET is not configured")
    return hashlib.sha256(configured.encode()).digest()


def fernet() -> Fernet:
    return Fernet(base64.urlsafe_b64encode(session_key()))


def seal(payload: dict[str, Any]) -> str:
    now = int(time.time())
    data = {**payload, "iat": now, "exp": now + SESSION_TTL}
    return fernet().encrypt(json.dumps(data, separators=(",", ":")).encode()).decode()


def unseal(value: str) -> dict[str, Any]:
    try:
        raw = fernet().decrypt(value.encode(), ttl=SESSION_TTL)
        data = json.loads(raw.decode())
        if int(data.get("exp", 0)) < int(time.time()):
            raise ValueError("expired")
        return data
    except (InvalidToken, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        raise ValueError("Invalid or expired session") from exc


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    return forwarded.split(",")[0].strip() or (request.client.host if request.client else "unknown")


def rate_limited(request: Request) -> bool:
    now = time.time()
    ip = client_ip(request)
    hits = [t for t in _rate_cache.get(ip, []) if now - t < RATE_WINDOW]
    if len(hits) >= RATE_LIMIT:
        _rate_cache[ip] = hits
        return True
    hits.append(now)
    _rate_cache[ip] = hits
    if len(_rate_cache) > 1000:
        for key in list(_rate_cache)[:100]:
            if not _rate_cache[key] or now - _rate_cache[key][-1] > RATE_WINDOW:
                _rate_cache.pop(key, None)
    return False


__all__ = ["SESSION_TTL", "seal", "unseal", "rate_limited", "client_ip"]
