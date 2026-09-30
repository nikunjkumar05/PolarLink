from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from typing import Any

from ..config import JWT_ALGORITHM, JWT_SECRET, JWT_TTL_SECONDS

_PBKDF2_ROUNDS = 240_000


def hash_password(password: str) -> str:
    """PBKDF2-HMAC-SHA256 with a per-user random salt, stored as one string."""
    if len(password) < 8:
        raise ValueError("password must be at least 8 characters")
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _PBKDF2_ROUNDS)
    return f"pbkdf2_sha256${_PBKDF2_ROUNDS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algorithm, rounds, salt_hex, digest_hex = stored.split("$")
        if algorithm != "pbkdf2_sha256":
            return False
        expected = bytes.fromhex(digest_hex)
        actual = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), bytes.fromhex(salt_hex), int(rounds)
        )
        return hmac.compare_digest(expected, actual)
    except (ValueError, TypeError):
        return False


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _unb64(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def create_token(user_id: int, role: str, email: str) -> tuple[str, int]:
    """Return (token, expires_in_seconds)."""
    expires_at = int(time.time()) + JWT_TTL_SECONDS
    header = {"alg": JWT_ALGORITHM, "typ": "JWT"}
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "role": role,
        "email": email,
        "exp": expires_at,
    }
    segments = [
        _b64(json.dumps(header, separators=(",", ":")).encode()),
        _b64(json.dumps(payload, separators=(",", ":")).encode()),
    ]
    signing_input = ".".join(segments).encode()
    signature = hmac.new(JWT_SECRET.encode(), signing_input, hashlib.sha256).digest()
    segments.append(_b64(signature))
    return ".".join(segments), JWT_TTL_SECONDS


class TokenError(ValueError):
    pass


def decode_token(token: str) -> dict[str, Any]:
    try:
        header_b64, payload_b64, signature_b64 = token.split(".")
    except ValueError as exc:
        raise TokenError("malformed token") from exc

    signing_input = f"{header_b64}.{payload_b64}".encode()
    expected = hmac.new(JWT_SECRET.encode(), signing_input, hashlib.sha256).digest()
    try:
        provided = _unb64(signature_b64)
    except Exception as exc:  # noqa: BLE001
        raise TokenError("malformed signature") from exc
    if not hmac.compare_digest(expected, provided):
        raise TokenError("signature mismatch")

    try:
        header = json.loads(_unb64(header_b64))
        payload = json.loads(_unb64(payload_b64))
    except Exception as exc:  # noqa: BLE001
        raise TokenError("malformed token body") from exc

    if header.get("alg") != JWT_ALGORITHM:
        raise TokenError("unsupported algorithm")
    if int(payload.get("exp", 0)) < int(time.time()):
        raise TokenError("token expired")
    return payload


__all__ = [
    "TokenError",
    "create_token",
    "decode_token",
    "hash_password",
    "verify_password",
]