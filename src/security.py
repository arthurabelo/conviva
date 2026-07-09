from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
import time
from http import cookies


class PasswordHasher:
    def hash(self, password: str, salt: bytes | None = None) -> str:
        salt = salt or os.urandom(16)
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 160_000)
        return base64.b64encode(salt).decode("ascii") + "$" + base64.b64encode(digest).decode("ascii")

    def verify(self, password: str, stored: str) -> bool:
        try:
            salt_b64, digest_b64 = stored.split("$", 1)
            salt = base64.b64decode(salt_b64.encode("ascii"))
            expected = base64.b64decode(digest_b64.encode("ascii"))
            calculated = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 160_000)
            return hmac.compare_digest(calculated, expected)
        except Exception:
            return False


class TokenSigner:
    def __init__(self, secret_key: str):
        self.secret_key = secret_key.encode("utf-8")

    def _sign(self, payload: bytes) -> bytes:
        return hmac.new(self.secret_key, payload, hashlib.sha256).digest()

    def build(self, user_id: int, expires_at: int) -> str:
        payload = f"{user_id}:{expires_at}:{secrets.token_urlsafe(18)}".encode("utf-8")
        raw = payload + b"." + self._sign(payload)
        return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")

    def parse(self, token: str) -> int | None:
        try:
            padded = token + ("=" * (-len(token) % 4))
            raw = base64.urlsafe_b64decode(padded.encode("ascii"))
            payload, signature = raw.rsplit(b".", 1)
            if not hmac.compare_digest(signature, self._sign(payload)):
                return None
            user_id, expires_at, *_ = payload.decode("utf-8").split(":")
            if int(expires_at) < int(time.time()):
                return None
            return int(user_id)
        except Exception:
            return None

    @staticmethod
    def token_hash(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()


def parse_cookie(header: str | None) -> dict[str, str]:
    jar = cookies.SimpleCookie()
    if header:
        jar.load(header)
    return {key: morsel.value for key, morsel in jar.items()}

