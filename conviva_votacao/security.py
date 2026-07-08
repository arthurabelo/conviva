import base64
import hashlib
import hmac
import os
import secrets
import time
from datetime import datetime
from http import cookies
from typing import Any

from . import models

SECRET_KEY = os.getenv("SECRET_KEY", "conviva-dev-secret")
SESSION_EXPIRE_SECONDS = int(os.getenv("SESSION_EXPIRE_SECONDS", "86400"))
DATE_FMT = "%Y-%m-%d %H:%M:%S"


class PasswordHasher:
    def hash(self, password: str, salt: bytes | None = None) -> str:
        salt = salt or os.urandom(16)
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120_000)
        return base64.b64encode(salt).decode() + "$" + base64.b64encode(digest).decode()

    def verify(self, password: str, stored: str) -> bool:
        try:
            salt_b64, digest_b64 = stored.split("$", 1)
            salt = base64.b64decode(salt_b64.encode())
            expected = base64.b64decode(digest_b64.encode())
            calculated = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120_000)
            return hmac.compare_digest(calculated, expected)
        except Exception:
            return False


class SessionManager:
    def __init__(self, secret_key: str, expire_seconds: int):
        self.secret_key = secret_key
        self.expire_seconds = expire_seconds

    def sign(self, payload: bytes) -> bytes:
        return hmac.new(self.secret_key.encode("utf-8"), payload, hashlib.sha256).digest()

    def build_token(self, user_id: int) -> str:
        expires = int(time.time()) + self.expire_seconds
        payload = f"{user_id}:{expires}:{secrets.token_urlsafe(12)}".encode("utf-8")
        signature = self.sign(payload)
        return base64.urlsafe_b64encode(payload + b"." + signature).decode("utf-8").rstrip("=")

    def parse_token(self, token: str) -> int | None:
        try:
            padded = token + ("=" * (-len(token) % 4))
            decoded = base64.urlsafe_b64decode(padded.encode("utf-8"))
            payload, signature = decoded.rsplit(b".", 1)
            if not hmac.compare_digest(signature, self.sign(payload)):
                return None
            user_id_str, expires_str, *_ = payload.decode("utf-8").split(":")
            if int(expires_str) < int(time.time()):
                return None
            return int(user_id_str)
        except Exception:
            return None

    def token_hash(self, token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def now(self) -> str:
        return datetime.now().strftime(DATE_FMT)

    def expires_at(self) -> str:
        return datetime.fromtimestamp(int(time.time()) + self.expire_seconds).strftime(DATE_FMT)

    def cleanup_expired(self) -> None:
        models.execute(
            "UPDATE sessao_usuario SET encerrada_em = ? WHERE encerrada_em IS NULL AND expira_em <= ?",
            [self.now(), self.now()],
        )

    def create(self, user_id: int, ip: str = "", navegador: str = "") -> str:
        self.cleanup_expired()
        active = models.query_one(
            "SELECT id_sessao FROM sessao_usuario WHERE id_usuario = ? AND encerrada_em IS NULL AND expira_em > ?",
            [user_id, self.now()],
        )
        if active:
            raise RuntimeError("Já existe uma sessão ativa para este usuário. Saia da outra sessão antes de entrar novamente.")

        token = self.build_token(user_id)
        models.execute(
            """
            INSERT INTO sessao_usuario (id_usuario, token_hash, criada_em, expira_em, ip, navegador)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [user_id, self.token_hash(token), self.now(), self.expires_at(), ip, navegador],
        )
        return token

    def close(self, token: str | None) -> None:
        if not token:
            return
        models.execute(
            "UPDATE sessao_usuario SET encerrada_em = ? WHERE token_hash = ? AND encerrada_em IS NULL",
            [self.now(), self.token_hash(token)],
        )

    def is_active(self, token: str, user_id: int) -> bool:
        row = models.query_one(
            """
            SELECT id_sessao FROM sessao_usuario
            WHERE id_usuario = ? AND token_hash = ? AND encerrada_em IS NULL AND expira_em > ?
            """,
            [user_id, self.token_hash(token), self.now()],
        )
        return bool(row)


hasher = PasswordHasher()
sessions = SessionManager(SECRET_KEY, SESSION_EXPIRE_SECONDS)


def hash_password(password: str, salt: bytes | None = None) -> str:
    return hasher.hash(password, salt)


def verify_password(password: str, stored: str) -> bool:
    return hasher.verify(password, stored)


def authenticate(email: str, password: str) -> dict[str, Any] | None:
    user = models.query_one("SELECT * FROM usuario WHERE email = ? AND ativo = 1", [email.strip().lower()])
    if user and verify_password(password, user["senha_hash"]):
        return dict(user)
    return None


def create_session(user_id: int, ip: str = "", navegador: str = "") -> str:
    return sessions.create(user_id, ip, navegador)


def delete_session(token: str | None) -> None:
    sessions.close(token)


def parse_cookie(header: str | None) -> dict[str, str]:
    jar = cookies.SimpleCookie()
    if header:
        jar.load(header)
    return {key: morsel.value for key, morsel in jar.items()}


def get_current_user(cookie_header: str | None) -> dict[str, Any] | None:
    token = parse_cookie(cookie_header).get("conviva_session")
    if not token:
        return None
    user_id = sessions.parse_token(token)
    if not user_id or not sessions.is_active(token, user_id):
        return None
    user = models.query_one("SELECT * FROM usuario WHERE id_usuario = ? AND ativo = 1", [user_id])
    return dict(user) if user else None


def is_admin(user: dict[str, Any] | None) -> bool:
    return bool(user and user.get("tipo_usuario") == "administrador")
