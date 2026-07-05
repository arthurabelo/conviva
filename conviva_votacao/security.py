import base64
import hashlib
import hmac
import os
import secrets
from http import cookies
from typing import Any

from . import models

_sessions: dict[str, int] = {}
_user_tokens: dict[int, str] = {}


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


def authenticate(email: str, password: str) -> dict[str, Any] | None:
    user = models.query_one("SELECT * FROM usuario WHERE email = ? AND ativo = 1", [email.strip().lower()])
    if user and verify_password(password, user["senha_hash"]):
        return dict(user)
    return None


def has_active_session(user_id: int) -> bool:
    token = _user_tokens.get(user_id)
    return bool(token and token in _sessions)


def create_session(user_id: int) -> str:
    if has_active_session(user_id):
        raise RuntimeError("Já existe uma sessão ativa para este usuário. Saia da sessão anterior antes de entrar novamente.")
    token = secrets.token_urlsafe(32)
    _sessions[token] = user_id
    _user_tokens[user_id] = token
    return token


def delete_session(token: str | None) -> None:
    if token:
        user_id = _sessions.pop(token, None)
        if user_id is not None and _user_tokens.get(user_id) == token:
            _user_tokens.pop(user_id, None)


def parse_cookie(header: str | None) -> dict[str, str]:
    jar = cookies.SimpleCookie()
    if header:
        jar.load(header)
    return {key: morsel.value for key, morsel in jar.items()}


def get_current_user(cookie_header: str | None) -> dict[str, Any] | None:
    token = parse_cookie(cookie_header).get("conviva_session")
    user_id = _sessions.get(token or "")
    if not user_id:
        return None
    user = models.query_one("SELECT * FROM usuario WHERE id_usuario = ? AND ativo = 1", [user_id])
    return dict(user) if user else None


def is_admin(user: dict[str, Any] | None) -> bool:
    return bool(user and user.get("tipo_usuario") == "administrador")
