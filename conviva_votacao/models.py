import os
import re
from pathlib import Path
from typing import Any, Iterable

import psycopg2
from psycopg2.extras import RealDictCursor

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
}


def _database_url() -> str:
    return os.getenv(
        "DATABASE_URL",
        "postgresql://conviva:conviva@localhost:5432/conviva_db",
    )


def get_conn():
    return psycopg2.connect(_database_url(), cursor_factory=RealDictCursor)


def _prepare(sql: str) -> str:
    prepared = sql.replace("?", "%s")
    prepared = prepared.replace("datetime('now')", "NOW()")
    prepared = prepared.replace("GROUP_CONCAT(l.identificacao, ', ')", "STRING_AGG(l.identificacao, ', ')")
    return prepared


def _with_returning(sql: str) -> str:
    if re.search(r"\bRETURNING\b", sql, flags=re.I):
        return sql
    match = re.match(r"\s*INSERT\s+INTO\s+([a-zA-Z_][a-zA-Z0-9_]*)", sql, flags=re.I)
    if not match:
        return sql
    table = match.group(1).lower()
    pk = PK_MAP.get(table)
    if not pk:
        return sql
    return sql.rstrip().rstrip(";") + f" RETURNING {pk};"


def query(sql: str, params: Iterable[Any] = ()) -> list[dict[str, Any]]:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(_prepare(sql), tuple(params))
            return list(cur.fetchall())


def query_one(sql: str, params: Iterable[Any] = ()) -> dict[str, Any] | None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(_prepare(sql), tuple(params))
            return cur.fetchone()


def execute(sql: str, params: Iterable[Any] = ()) -> int:
    prepared = _with_returning(_prepare(sql))
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(prepared, tuple(params))
            returned = cur.fetchone() if cur.description else None
            conn.commit()
            if returned:
                return int(next(iter(returned.values())))
            return 0


def execute_many(sql: str, seq_of_params: Iterable[Iterable[Any]]) -> None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.executemany(_prepare(sql), [tuple(params) for params in seq_of_params])
            conn.commit()


def init_db() -> None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(SCHEMA_PATH.read_text(encoding="utf-8"))
            conn.commit()
