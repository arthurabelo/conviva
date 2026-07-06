import base64
import hashlib
import hmac
import os
import secrets
import time
from http import cookies
from typing import Any

from . import models

SECRET_KEY = os.getenv("SECRET_KEY", "conviva-dev-secret")
SESSION_EXPIRE_SECONDS = int(os.getenv("SESSION_EXPIRE_SECONDS", "86400"))


def hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120_000)
    return base64.b64encode(salt).decode() + "$" + base64.b64encode(digest).decode()


def verify_password(password: str, stored: str) -> bool:
    try:
        salt_b64, digest_b64 = stored.split("$", 1)
        salt = base64.b64decode(salt_b64.encode())
        expected = base64.b64decode(digest_b64.encode())
        calculated = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120_000)
        return hmac.compare_digest(calculated, expected)
    except Exception:
        return False


def _sign(payload: bytes) -> bytes:
    return hmac.new(SECRET_KEY.encode("utf-8"), payload, hashlib.sha256).digest()


def _build_token(user_id: int) -> str:
    expires = int(time.time()) + SESSION_EXPIRE_SECONDS
    payload = f"{user_id}:{expires}".encode("utf-8")
    signature = _sign(payload)
    token = base64.urlsafe_b64encode(payload + b"." + signature)
    return token.decode("utf-8")


def _parse_token(token: str) -> int | None:
    try:
        decoded = base64.urlsafe_b64decode(token.encode("utf-8"))
        payload, signature = decoded.rsplit(b".", 1)
        if not hmac.compare_digest(signature, _sign(payload)):
            return None
        payload_text = payload.decode("utf-8")
        user_id_str, expires_str = payload_text.split(":", 1)
        if int(expires_str) < int(time.time()):
            return None
        return int(user_id_str)
    except Exception:
        return None


def authenticate(email: str, password: str) -> dict[str, Any] | None:
    user = models.query_one("SELECT * FROM usuario WHERE email = ? AND ativo = 1", [email.strip().lower()])
    if user and verify_password(password, user["senha_hash"]):
        return dict(user)
    return None


def create_session(user_id: int) -> str:
    return _build_token(user_id)


def delete_session(token: str | None) -> None:
    return None


def parse_cookie(header: str | None) -> dict[str, str]:
    jar = cookies.SimpleCookie()
    if header:
        jar.load(header)
    return {key: morsel.value for key, morsel in jar.items()}


def get_current_user(cookie_header: str | None) -> dict[str, Any] | None:
    token = parse_cookie(cookie_header).get("conviva_session")
    if not token:
        return None
    user_id = _parse_token(token)
    if not user_id:
        return None
    user = models.query_one("SELECT * FROM usuario WHERE id_usuario = ? AND ativo = 1", [user_id])
    return dict(user) if user else None


def is_admin(user: dict[str, Any] | None) -> bool:
    return bool(user and user.get("tipo_usuario") == "administrador")
