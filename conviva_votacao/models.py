import os
import re
import sqlite3
from pathlib import Path
from typing import Any, Iterable

BASE_DIR = Path(__file__).resolve().parent.parent
SCHEMA_PATH = BASE_DIR / "schema.sql"

PK_MAP = {
    "condominio": "id_condominio",
    "usuario": "id_usuario",
    "lote": "id_lote",
    "reuniao": "id_reuniao",
    "convidado_reuniao": "id_convidado",
    "pauta": "id_pauta",
    "votacao": "id_votacao",
    "opcao_voto": "id_opcao",
    "voto": "id_voto",
    "voto_escolha": "id_voto_escolha",
    "log_auditoria": "id_log",
    "sessao_usuario": "id_sessao",
}


class Database:
    def __init__(self, database_url: str | None = None, sqlite_path: str | Path | None = None):
        self.database_url = self._normalize_database_url(database_url or os.getenv("DATABASE_URL", ""))
        self.engine = self._detect_engine()
        self.sqlite_path = Path(sqlite_path or os.getenv("SQLITE_PATH", BASE_DIR / "conviva.sqlite3"))

    def _normalize_database_url(self, url: str) -> str:
        if url.startswith("postgres://"):
            return url.replace("postgres://", "postgresql://", 1)
        return url

    def _detect_engine(self) -> str:
        engine = os.getenv("DATABASE_ENGINE", "").strip().lower()
        if engine in {"sqlite", "postgres"}:
            return engine
        if self.database_url.startswith("sqlite:///"):
            return "sqlite"
        if self.database_url.startswith("postgresql://"):
            return "postgres"
        return "sqlite"

    def connect(self):
        if self.engine == "postgres":
            import psycopg2
            from psycopg2.extras import RealDictCursor

            return psycopg2.connect(self.database_url, cursor_factory=RealDictCursor)

        path = self.database_url.removeprefix("sqlite:///") if self.database_url.startswith("sqlite:///") else str(self.sqlite_path)
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def prepare(self, sql: str) -> str:
        if self.engine != "postgres":
            return sql
        prepared = sql.replace("?", "%s")
        prepared = prepared.replace("datetime('now')", "NOW()")
        return prepared

    def schema_sql(self) -> str:
        sql = SCHEMA_PATH.read_text(encoding="utf-8")
        if self.engine == "postgres":
            return sql
        sql = sql.replace("SERIAL PRIMARY KEY", "INTEGER PRIMARY KEY AUTOINCREMENT")
        sql = re.sub(r"\bTIMESTAMP\b", "TEXT", sql)
        return sql

    def with_returning(self, sql: str) -> str:
        if self.engine != "postgres" or re.search(r"\bRETURNING\b", sql, flags=re.I):
            return sql
        match = re.match(r"\s*INSERT\s+INTO\s+([a-zA-Z_][a-zA-Z0-9_]*)", sql, flags=re.I)
        if not match:
            return sql
        table = match.group(1).lower()
        pk = PK_MAP.get(table)
        if not pk:
            return sql
        return sql.rstrip().rstrip(";") + f" RETURNING {pk};"

    def query(self, sql: str, params: Iterable[Any] = ()) -> list[dict[str, Any]]:
        conn = self.connect()
        try:
            cur = conn.cursor()
            cur.execute(self.prepare(sql), tuple(params))
            rows = cur.fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def query_one(self, sql: str, params: Iterable[Any] = ()) -> dict[str, Any] | None:
        conn = self.connect()
        try:
            cur = conn.cursor()
            cur.execute(self.prepare(sql), tuple(params))
            row = cur.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def execute(self, sql: str, params: Iterable[Any] = ()) -> int:
        conn = self.connect()
        try:
            cur = conn.cursor()
            prepared = self.with_returning(self.prepare(sql))
            cur.execute(prepared, tuple(params))
            returned = cur.fetchone() if cur.description else None
            conn.commit()
            if returned:
                return int(next(iter(dict(returned).values())))
            return int(getattr(cur, "lastrowid", 0) or 0)
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def execute_many(self, sql: str, seq_of_params: Iterable[Iterable[Any]]) -> None:
        conn = self.connect()
        try:
            cur = conn.cursor()
            cur.executemany(self.prepare(sql), [tuple(params) for params in seq_of_params])
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def init_db(self) -> None:
        if self.engine == "sqlite":
            self.sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        conn = self.connect()
        try:
            if self.engine == "postgres":
                cur = conn.cursor()
                cur.execute(self.schema_sql())
            else:
                conn.executescript(self.schema_sql())
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def ping(self) -> None:
        self.query_one("SELECT 1")


database = Database()


def configure(database_url: str | None = None, sqlite_path: str | Path | None = None) -> None:
    global database
    database = Database(database_url=database_url, sqlite_path=sqlite_path)


def get_conn():
    return database.connect()


def query(sql: str, params: Iterable[Any] = ()) -> list[dict[str, Any]]:
    return database.query(sql, params)


def query_one(sql: str, params: Iterable[Any] = ()) -> dict[str, Any] | None:
    return database.query_one(sql, params)


def execute(sql: str, params: Iterable[Any] = ()) -> int:
    return database.execute(sql, params)


def execute_many(sql: str, seq_of_params: Iterable[Iterable[Any]]) -> None:
    database.execute_many(sql, seq_of_params)


def init_db() -> None:
    database.init_db()


def ping() -> None:
    database.ping()
