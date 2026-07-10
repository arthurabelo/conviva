from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import psycopg
from psycopg.rows import dict_row

BASE_DIR = Path(__file__).resolve().parent.parent
SCHEMA_PATH = BASE_DIR / "schema.sql"
# Prioriza as URLs fornecidas pela integracao Supabase/Postgres (fonte de
# verdade em producao). DATABASE_URL fica por ultimo como override local.
DATABASE_URL = (
    os.getenv("STORAGE_POSTGRES_URL")
    or os.getenv("POSTGRES_URL")
    or os.getenv("STORAGE_POSTGRES_PRISMA_URL")
    or os.getenv("POSTGRES_PRISMA_URL")
    or os.getenv("STORAGE_POSTGRES_URL_NON_POOLING")
    or os.getenv("POSTGRES_URL_NON_POOLING")
    or os.getenv("DATABASE_URL")
)

# Parametros de conexao aceitos pelo libpq. Supabase/Vercel podem anexar
# extras (ex.: supa, pgbouncer) que fazem o psycopg falhar; eles sao removidos.
_LIBPQ_PARAMS = {
    "sslmode",
    "connect_timeout",
    "application_name",
    "options",
    "channel_binding",
    "target_session_attrs",
    "gssencmode",
    "sslrootcert",
    "sslcert",
    "sslkey",
}


def sanitize_conninfo(url: str | None) -> str:
    """Remove parametros nao suportados pelo libpq da URL de conexao."""
    if not url:
        return ""
    parts = urlsplit(url)
    kept = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if k in _LIBPQ_PARAMS]
    if "sslmode" not in dict(kept):
        kept.append(("sslmode", "require"))
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(kept), parts.fragment))


def prepare_sql(sql: str) -> str:
    """Converte placeholders no estilo SQLite (?) para o estilo psycopg (%s)."""
    return sql.replace("?", "%s")


CONNINFO = sanitize_conninfo(DATABASE_URL)

# Regex para descobrir a tabela alvo de um INSERT e devolver a chave primaria.
_INSERT_TABLE_RE = re.compile(r"insert\s+into\s+([a-zA-Z_][\w]*)", re.IGNORECASE)

INSERT_PRIMARY_KEYS = {
    "condominio": "id_condominio",
    "usuario": "id_usuario",
    "sessao_usuario": "id_sessao",
    "lote": "id_lote",
    "reuniao": "id_reuniao",
    "convidado_reuniao": "id_convidado",
    "pauta": "id_pauta",
    "anexo_pauta": "id_anexo",
    "procuracao": "id_procuracao",
    "votacao": "id_votacao",
    "opcao_voto": "id_opcao",
    "voto": "id_voto",
    "voto_escolha": "id_voto_escolha",
    "log_auditoria": "id_log",
}


@dataclass(frozen=True)
class Usuario:
    id_usuario: int
    nome_completo: str
    email: str
    tipo_usuario: str
    ativo: int

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "Usuario":
        return cls(
            id_usuario=int(row["id_usuario"]),
            nome_completo=str(row["nome_completo"]),
            email=str(row["email"]),
            tipo_usuario=str(row["tipo_usuario"]),
            ativo=int(row["ativo"]),
        )


@dataclass(frozen=True)
class Votacao:
    id_votacao: int
    id_pauta: int
    id_reuniao: int
    id_condominio: int
    assunto: str
    pergunta: str
    tipo_votacao: str
    tipo_resposta: str
    tempo_resposta: int
    max_marcacoes: int
    status: str
    iniciou_em: str | None
    encerra_em: str | None
    encerrada_em: str | None

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "Votacao":
        return cls(
            id_votacao=int(row["id_votacao"]),
            id_pauta=int(row["id_pauta"]),
            id_reuniao=int(row["id_reuniao"]),
            id_condominio=int(row["id_condominio"]),
            assunto=str(row["assunto"]),
            pergunta=str(row["pergunta"]),
            tipo_votacao=str(row["tipo_votacao"]),
            tipo_resposta=str(row["tipo_resposta"]),
            tempo_resposta=int(row["tempo_resposta"]),
            max_marcacoes=int(row["max_marcacoes"]),
            status=str(row["status"]),
            iniciou_em=row.get("iniciou_em"),
            encerra_em=row.get("encerra_em"),
            encerrada_em=row.get("encerrada_em"),
        )


class Database:
    def __init__(self, conninfo: str = "") -> None:
        self.conninfo = conninfo or CONNINFO
        if not self.conninfo:
            raise RuntimeError(
                "Nenhuma URL de banco configurada. Defina DATABASE_URL ou "
                "STORAGE_POSTGRES_URL (integracao Supabase/Postgres)."
            )

    def connect(self) -> psycopg.Connection:
        # prepare_threshold=None desabilita prepared statements do lado do
        # cliente, evitando conflitos com o pooler (pgbouncer) do Supabase.
        return psycopg.connect(
            self.conninfo,
            row_factory=dict_row,
            prepare_threshold=None,
        )

    def init_db(self) -> None:
        schema = SCHEMA_PATH.read_text(encoding="utf-8")
        with self.connect() as conn:
            # Sem parametros, o psycopg permite multiplos comandos em um execute.
            conn.execute(schema)
            conn.commit()

    def reset_db(self) -> None:
        drops = [
            "voto_escolha",
            "voto",
            "opcao_voto",
            "votacao",
            "procuracao",
            "anexo_pauta",
            "pauta",
            "convidado_reuniao",
            "reuniao",
            "lote",
            "sessao_usuario",
            "log_auditoria",
            "usuario",
            "condominio",
        ]
        with self.connect() as conn:
            for table in drops:
                conn.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
            conn.commit()
        self.init_db()

    def query(self, sql: str, params: Iterable[Any] = ()) -> list[dict[str, Any]]:
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(prepare_sql(sql), tuple(params))
                return [dict(row) for row in cur.fetchall()]

    def query_one(self, sql: str, params: Iterable[Any] = ()) -> dict[str, Any] | None:
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(prepare_sql(sql), tuple(params))
                row = cur.fetchone()
                return dict(row) if row else None

    def execute(self, sql: str, params: Iterable[Any] = ()) -> int:
        prepared = prepare_sql(sql)
        with self.connect() as conn:
            with conn.cursor() as cur:
                returning_key = self._returning_key(prepared)
                if returning_key:
                    prepared = f"{prepared.rstrip().rstrip(';')} RETURNING {returning_key}"
                cur.execute(prepared, tuple(params))
                new_id = 0
                if returning_key:
                    row = cur.fetchone()
                    if row is not None:
                        new_id = int(row[returning_key])
            conn.commit()
            return new_id

    def execute_many(self, sql: str, seq_of_params: Iterable[Iterable[Any]]) -> None:
        rows = [tuple(params) for params in seq_of_params]
        if not rows:
            return
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.executemany(prepare_sql(sql), rows)
            conn.commit()

    @staticmethod
    def _returning_key(sql: str) -> str | None:
        if "returning" in sql.lower():
            return None
        match = _INSERT_TABLE_RE.search(sql)
        if not match:
            return None
        return INSERT_PRIMARY_KEYS.get(match.group(1).lower())


class UsuarioRepository:
    def __init__(self, db: Database):
        self.db = db

    def by_email(self, email: str) -> dict[str, Any] | None:
        return self.db.query_one(
            "SELECT * FROM usuario WHERE email = ? AND ativo = 1",
            [email.strip().lower()],
        )

    def by_id(self, id_usuario: int) -> dict[str, Any] | None:
        return self.db.query_one(
            "SELECT * FROM usuario WHERE id_usuario = ? AND ativo = 1",
            [id_usuario],
        )

    def get_any(self, id_usuario: int) -> dict[str, Any] | None:
        return self.db.query_one("SELECT * FROM usuario WHERE id_usuario = ?", [id_usuario])

    def list_active(self, nome: str = "", tipo: str = "") -> list[dict[str, Any]]:
        clauses = ["ativo = 1"]
        params: list[Any] = []
        if nome.strip():
            clauses.append("lower(nome_completo) LIKE ?")
            params.append(f"%{nome.strip().lower()}%")
        if tipo in {"administrador", "proprietario"}:
            clauses.append("tipo_usuario = ?")
            params.append(tipo)
        return self.db.query(
            f"SELECT * FROM usuario WHERE {' AND '.join(clauses)} ORDER BY nome_completo",
            params,
        )

    def email_in_use(self, email: str, except_id: int | None = None) -> bool:
        sql = "SELECT 1 FROM usuario WHERE lower(email) = ?"
        params: list[Any] = [email.strip().lower()]
        if except_id is not None:
            sql += " AND id_usuario <> ?"
            params.append(except_id)
        return bool(self.db.query_one(sql, params))

    def create(self, nome: str, email: str, senha_hash: str, tipo: str) -> int:
        return self.db.execute(
            "INSERT INTO usuario (nome_completo, email, senha_hash, tipo_usuario, ativo) VALUES (?, ?, ?, ?, 1)",
            [nome, email, senha_hash, tipo],
        )

    def update(self, id_usuario: int, nome: str, email: str, tipo: str, senha_hash: str | None = None) -> None:
        if senha_hash:
            self.db.execute(
                "UPDATE usuario SET nome_completo = ?, email = ?, tipo_usuario = ?, senha_hash = ? WHERE id_usuario = ? AND ativo = 1",
                [nome, email, tipo, senha_hash, id_usuario],
            )
        else:
            self.db.execute(
                "UPDATE usuario SET nome_completo = ?, email = ?, tipo_usuario = ? WHERE id_usuario = ? AND ativo = 1",
                [nome, email, tipo, id_usuario],
            )

    def deactivate(self, id_usuario: int) -> None:
        self.db.execute("UPDATE usuario SET ativo = 0 WHERE id_usuario = ?", [id_usuario])

    def default_condominio(self) -> dict[str, Any] | None:
        return self.db.query_one("SELECT * FROM condominio WHERE status = 'ativo' ORDER BY id_condominio LIMIT 1")

    def lots(self, id_usuario: int, id_condominio: int) -> list[dict[str, Any]]:
        return self.db.query(
            "SELECT * FROM lote WHERE id_usuario = ? AND id_condominio = ? ORDER BY identificacao",
            [id_usuario, id_condominio],
        )

    def lot(self, id_lote: int) -> dict[str, Any] | None:
        return self.db.query_one("SELECT * FROM lote WHERE id_lote = ?", [id_lote])

    def lot_in_use(self, id_condominio: int, identificacao: str, except_id: int | None = None) -> bool:
        sql = "SELECT 1 FROM lote WHERE id_condominio = ? AND lower(identificacao) = ?"
        params: list[Any] = [id_condominio, identificacao.strip().lower()]
        if except_id is not None:
            sql += " AND id_lote <> ?"
            params.append(except_id)
        return bool(self.db.query_one(sql, params))

    def save_lot(self, id_usuario: int, id_condominio: int, identificacao: str, peso: float, inadimplente: bool, id_lote: int | None = None) -> int:
        if id_lote is not None:
            self.db.execute(
                "UPDATE lote SET identificacao = ?, peso_original = ?, inadimplente = ? WHERE id_lote = ? AND id_usuario = ? AND id_condominio = ?",
                [identificacao, peso, int(inadimplente), id_lote, id_usuario, id_condominio],
            )
            return id_lote
        return self.db.execute(
            "INSERT INTO lote (id_condominio, id_usuario, identificacao, peso_original, inadimplente) VALUES (?, ?, ?, ?, ?)",
            [id_condominio, id_usuario, identificacao, peso, int(inadimplente)],
        )

    def delete_lot(self, id_lote: int, id_usuario: int, id_condominio: int) -> None:
        self.db.execute(
            "DELETE FROM lote WHERE id_lote = ? AND id_usuario = ? AND id_condominio = ?",
            [id_lote, id_usuario, id_condominio],
        )


class ReuniaoRepository:
    def __init__(self, db: Database):
        self.db = db

    def get(self, id_reuniao: int) -> dict[str, Any] | None:
        return self.db.query_one(
            """
            SELECT r.*, c.nome AS condominio_nome
            FROM reuniao r
            JOIN condominio c ON c.id_condominio = r.id_condominio
            WHERE r.id_reuniao = ?
            """,
            [id_reuniao],
        )

    def list_for_user(self, user: dict[str, Any], search: str = "") -> list[dict[str, Any]]:
        term = f"%{search.strip().lower()}%" if search.strip() else ""
        if user["tipo_usuario"] == "administrador":
            query = """
                SELECT r.*, c.nome AS condominio_nome
                FROM reuniao r
                JOIN condominio c ON c.id_condominio = r.id_condominio
            """
            params: list[Any] = []
            if term:
                query += " WHERE lower(r.titulo) LIKE ? OR lower(r.assunto) LIKE ? OR lower(c.nome) LIKE ?"
                params = [term, term, term]
            query += " ORDER BY r.data DESC, r.hora DESC"
            return self.db.query(query, params)
        query = """
            SELECT r.*, c.nome AS condominio_nome, cr.status_presenca
            FROM reuniao r
            JOIN condominio c ON c.id_condominio = r.id_condominio
            JOIN convidado_reuniao cr ON cr.id_reuniao = r.id_reuniao
            WHERE cr.id_usuario = ?
        """
        params = [user["id_usuario"]]
        if term:
            query += " AND (lower(r.titulo) LIKE ? OR lower(r.assunto) LIKE ? OR lower(c.nome) LIKE ?)"
            params.extend([term, term, term])
        query += " ORDER BY r.data DESC, r.hora DESC"
        return self.db.query(query, params)

    def list_all(self) -> list[dict[str, Any]]:
        return self.db.query("SELECT * FROM reuniao ORDER BY data DESC, hora DESC")

    def is_invited(self, id_usuario: int, id_reuniao: int) -> bool:
        row = self.db.query_one(
            """
            SELECT 1 FROM convidado_reuniao
            WHERE id_usuario = ? AND id_reuniao = ? AND status_convite = 'confirmado'
            """,
            [id_usuario, id_reuniao],
        )
        return bool(row)

    def is_present(self, id_usuario: int, id_reuniao: int) -> bool:
        row = self.db.query_one(
            """
            SELECT 1 FROM convidado_reuniao
            WHERE id_usuario = ? AND id_reuniao = ? AND status_presenca = 1
            """,
            [id_usuario, id_reuniao],
        )
        return bool(row)

    def mark_present(self, id_usuario: int, id_reuniao: int, now: str) -> None:
        self.db.execute(
            """
            UPDATE convidado_reuniao
            SET status_presenca = 1,
                data_hora_entrada = COALESCE(data_hora_entrada, ?),
                data_hora_saida = NULL
            WHERE id_usuario = ? AND id_reuniao = ?
            """,
            [now, id_usuario, id_reuniao],
        )

    def mark_absent(self, id_usuario: int, id_reuniao: int, now: str) -> None:
        self.db.execute(
            """
            UPDATE convidado_reuniao
            SET status_presenca = 0, data_hora_saida = ?
            WHERE id_usuario = ? AND id_reuniao = ?
            """,
            [now, id_usuario, id_reuniao],
        )

    def participantes(self, id_reuniao: int) -> list[dict[str, Any]]:
        return self.db.query(
            """
            SELECT u.nome_completo, u.tipo_usuario, cr.status_convite, cr.status_presenca,
                   cr.data_hora_entrada, cr.data_hora_saida
            FROM convidado_reuniao cr
            JOIN usuario u ON u.id_usuario = cr.id_usuario
            WHERE cr.id_reuniao = ?
            ORDER BY cr.status_presenca DESC, u.nome_completo
            """,
            [id_reuniao],
        )

    def pautas(self, id_reuniao: int) -> list[dict[str, Any]]:
        return self.db.query(
            "SELECT * FROM pauta WHERE id_reuniao = ? ORDER BY id_pauta",
            [id_reuniao],
        )

    def anexos_pauta(self, id_pauta: int) -> list[dict[str, Any]]:
        return self.db.query(
            "SELECT * FROM anexo_pauta WHERE id_pauta = ? ORDER BY id_anexo",
            [id_pauta],
        )

    def all_pautas(self) -> list[dict[str, Any]]:
        return self.db.query(
            """
            SELECT p.*, r.titulo AS reuniao_titulo, r.status AS reuniao_status
            FROM pauta p
            JOIN reuniao r ON r.id_reuniao = p.id_reuniao
            ORDER BY r.data DESC, r.hora DESC, p.id_pauta
            """
        )


class VotacaoRepository:
    def __init__(self, db: Database):
        self.db = db

    def list_all(self, search: str = "") -> list[dict[str, Any]]:
        term = f"%{search.strip().lower()}%" if search.strip() else ""
        query = """
            SELECT v.*, p.assunto AS pauta_assunto, r.titulo AS reuniao_titulo, r.id_reuniao
            FROM votacao v
            JOIN pauta p ON p.id_pauta = v.id_pauta
            JOIN reuniao r ON r.id_reuniao = p.id_reuniao
        """
        params: list[Any] = []
        if term:
            query += " WHERE lower(v.assunto) LIKE ? OR lower(v.pergunta) LIKE ? OR lower(p.assunto) LIKE ? OR lower(r.titulo) LIKE ?"
            params = [term, term, term, term]
        query += " ORDER BY v.id_votacao DESC"
        return self.db.query(query, params)

    def list_for_meeting(self, id_reuniao: int, search: str = "") -> list[dict[str, Any]]:
        term = f"%{search.strip().lower()}%" if search.strip() else ""
        query = """
            SELECT v.*, p.assunto AS pauta_assunto
            FROM votacao v
            JOIN pauta p ON p.id_pauta = v.id_pauta
            WHERE p.id_reuniao = ?
        """
        params: list[Any] = [id_reuniao]
        if term:
            query += " AND (lower(v.assunto) LIKE ? OR lower(v.pergunta) LIKE ? OR lower(p.assunto) LIKE ?)"
            params.extend([term, term, term])
        query += " ORDER BY v.id_votacao DESC"
        return self.db.query(query, params)

    def get(self, id_votacao: int) -> dict[str, Any] | None:
        return self.db.query_one(
            """
            SELECT v.*, p.assunto AS pauta_assunto, p.descricao AS pauta_descricao,
                   r.titulo AS reuniao_titulo, r.id_reuniao, r.id_condominio,
                   r.status AS reuniao_status
            FROM votacao v
            JOIN pauta p ON p.id_pauta = v.id_pauta
            JOIN reuniao r ON r.id_reuniao = p.id_reuniao
            WHERE v.id_votacao = ?
            """,
            [id_votacao],
        )

    def active_for_meeting(self, id_reuniao: int) -> dict[str, Any] | None:
        return self.db.query_one(
            """
            SELECT v.*, p.assunto AS pauta_assunto, p.descricao AS pauta_descricao,
                   r.titulo AS reuniao_titulo, r.id_reuniao, r.id_condominio,
                   r.status AS reuniao_status
            FROM votacao v
            JOIN pauta p ON p.id_pauta = v.id_pauta
            JOIN reuniao r ON r.id_reuniao = p.id_reuniao
            WHERE r.id_reuniao = ? AND v.status = 'ativa'
            ORDER BY v.iniciou_em DESC
            LIMIT 1
            """,
            [id_reuniao],
        )

    def options(self, id_votacao: int) -> list[dict[str, Any]]:
        return self.db.query(
            "SELECT * FROM opcao_voto WHERE id_votacao = ? ORDER BY ordem",
            [id_votacao],
        )

    def create(self, data: dict[str, Any], opcoes: list[str]) -> int:
        id_votacao = self.db.execute(
            """
            INSERT INTO votacao
                (id_pauta, assunto, pergunta, tipo_votacao, tipo_resposta,
                 tempo_resposta, max_marcacoes, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'agendada')
            """,
            [
                data["id_pauta"],
                data["assunto"],
                data["pergunta"],
                data["tipo_votacao"],
                data["tipo_resposta"],
                data["tempo_resposta"],
                data["max_marcacoes"],
            ],
        )
        self.db.execute_many(
            "INSERT INTO opcao_voto (id_votacao, descricao, ordem) VALUES (?, ?, ?)",
            [[id_votacao, descricao, ordem] for ordem, descricao in enumerate(opcoes, start=1)],
        )
        return id_votacao

    def update(self, id_votacao: int, data: dict[str, Any], opcoes: list[str]) -> None:
        with self.db.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    prepare_sql("""
                    UPDATE votacao
                    SET id_pauta = ?,
                        assunto = ?,
                        pergunta = ?,
                        tipo_votacao = ?,
                        tipo_resposta = ?,
                        tempo_resposta = ?,
                        max_marcacoes = ?
                    WHERE id_votacao = ?
                    """),
                    [
                        data["id_pauta"],
                        data["assunto"],
                        data["pergunta"],
                        data["tipo_votacao"],
                        data["tipo_resposta"],
                        data["tempo_resposta"],
                        data["max_marcacoes"],
                        id_votacao,
                    ],
                )
                cur.execute(prepare_sql("DELETE FROM opcao_voto WHERE id_votacao = ?"), [id_votacao])
                cur.executemany(
                    prepare_sql("INSERT INTO opcao_voto (id_votacao, descricao, ordem) VALUES (?, ?, ?)"),
                    [(id_votacao, descricao, ordem) for ordem, descricao in enumerate(opcoes, start=1)],
                )
            conn.commit()

    def start(self, id_votacao: int, iniciou_em: str, encerra_em: str) -> None:
        self.db.execute(
            """
            UPDATE votacao
            SET status = 'ativa', iniciou_em = ?, encerra_em = ?, encerrada_em = NULL
            WHERE id_votacao = ?
            """,
            [iniciou_em, encerra_em, id_votacao],
        )

    def close(self, id_votacao: int, encerrada_em: str) -> None:
        self.db.execute(
            "UPDATE votacao SET status = 'encerrada', encerrada_em = ? WHERE id_votacao = ?",
            [encerrada_em, id_votacao],
        )

    def invalidate(self, id_votacao: int, encerrada_em: str) -> None:
        self.db.execute(
            "UPDATE votacao SET status = 'invalidada', encerrada_em = ? WHERE id_votacao = ?",
            [encerrada_em, id_votacao],
        )

    def has_active_in_meeting(self, id_reuniao: int, except_id: int | None = None) -> bool:
        params: list[Any] = [id_reuniao]
        extra = ""
        if except_id:
            extra = "AND v.id_votacao <> ?"
            params.append(except_id)
        row = self.db.query_one(
            f"""
            SELECT 1
            FROM votacao v
            JOIN pauta p ON p.id_pauta = v.id_pauta
            WHERE p.id_reuniao = ? AND v.status = 'ativa' {extra}
            LIMIT 1
            """,
            params,
        )
        return bool(row)

    def voto_by_representado(self, id_votacao: int, id_eleitor_representado: int) -> dict[str, Any] | None:
        return self.db.query_one(
            "SELECT * FROM voto WHERE id_votacao = ? AND id_eleitor_representado = ?",
            [id_votacao, id_eleitor_representado],
        )

    def voto_by_pauta_representado(self, id_pauta: int, id_eleitor_representado: int) -> dict[str, Any] | None:
        return self.db.query_one(
            """
            SELECT vt.*
            FROM voto vt
            JOIN votacao v ON v.id_votacao = vt.id_votacao
            WHERE v.id_pauta = ? AND vt.id_eleitor_representado = ?
            LIMIT 1
            """,
            [id_pauta, id_eleitor_representado],
        )

    def record_vote(
        self,
        id_votacao: int,
        id_usuario: int,
        id_eleitor_representado: int,
        id_procuracao: int | None,
        peso: float,
        escolhas: list[int],
        data_hora: str,
        ip: str,
        navegador: str,
    ) -> int:
        id_voto = self.db.execute(
            """
            INSERT INTO voto
                (id_usuario, id_eleitor_representado, id_procuracao, id_votacao,
                 data_hora_voto, peso_aplicado, ip, navegador)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [id_usuario, id_eleitor_representado, id_procuracao, id_votacao, data_hora, peso, ip, navegador],
        )
        self.db.execute_many(
            "INSERT INTO voto_escolha (id_voto, id_opcao) VALUES (?, ?)",
            [[id_voto, id_opcao] for id_opcao in escolhas],
        )
        return id_voto

    def peso_usuario(self, id_usuario: int, id_condominio: int) -> float:
        row = self.db.query_one(
            """
            SELECT COALESCE(SUM(CASE WHEN inadimplente = 1 THEN 0 ELSE peso_original END), 0) AS peso
            FROM lote
            WHERE id_usuario = ? AND id_condominio = ?
            """,
            [id_usuario, id_condominio],
        )
        return float(row["peso"] if row else 0)

    def total_lotes(self, id_usuario: int, id_condominio: int) -> int:
        row = self.db.query_one(
            "SELECT COUNT(*) AS total FROM lote WHERE id_usuario = ? AND id_condominio = ?",
            [id_usuario, id_condominio],
        )
        return int(row["total"] if row else 0)

    def proxy_for_owner(self, id_usuario: int, id_reuniao: int) -> dict[str, Any] | None:
        return self.db.query_one(
            """
            SELECT pr.*, u.nome_completo AS procurador_nome
            FROM procuracao pr
            JOIN usuario u ON u.id_usuario = pr.id_procurador
            WHERE pr.id_proprietario = ? AND pr.id_reuniao = ? AND pr.ativa = 1
            """,
            [id_usuario, id_reuniao],
        )

    def proxy_for_attorney(self, id_usuario: int, id_reuniao: int) -> dict[str, Any] | None:
        return self.db.query_one(
            """
            SELECT pr.*, u.nome_completo AS proprietario_nome
            FROM procuracao pr
            JOIN usuario u ON u.id_usuario = pr.id_proprietario
            WHERE pr.id_procurador = ? AND pr.id_reuniao = ? AND pr.ativa = 1
            """,
            [id_usuario, id_reuniao],
        )

    def option_totals(self, id_votacao: int) -> list[dict[str, Any]]:
        return self.db.query(
            """
            SELECT o.id_opcao, o.descricao,
                   COALESCE(SUM(v.peso_aplicado), 0) AS peso_acumulado,
                   COUNT(v.id_voto) AS total_votos
            FROM opcao_voto o
            LEFT JOIN voto_escolha ve ON ve.id_opcao = o.id_opcao
            LEFT JOIN voto v ON v.id_voto = ve.id_voto
            WHERE o.id_votacao = ?
            GROUP BY o.id_opcao, o.descricao, o.ordem
            ORDER BY o.ordem
            """,
            [id_votacao],
        )

    def totalizadores(self, id_votacao: int) -> dict[str, Any]:
        return self.db.query_one(
            """
            SELECT COUNT(*) AS total_votos, COALESCE(SUM(peso_aplicado), 0) AS total_peso
            FROM voto
            WHERE id_votacao = ?
            """,
            [id_votacao],
        ) or {"total_votos": 0, "total_peso": 0}

    def votos_nominais(self, id_votacao: int, id_condominio: int) -> list[dict[str, Any]]:
        return self.db.query(
            """
            SELECT v.id_voto,
                   u.nome_completo AS responsavel_nome,
                   rep.nome_completo AS representado_nome,
                   STRING_AGG(DISTINCT l.identificacao, ', ') AS imoveis,
                   STRING_AGG(DISTINCT o.descricao, ', ') AS voto,
                   v.peso_aplicado,
                   v.data_hora_voto
            FROM voto v
            JOIN usuario u ON u.id_usuario = v.id_usuario
            JOIN usuario rep ON rep.id_usuario = v.id_eleitor_representado
            JOIN voto_escolha ve ON ve.id_voto = v.id_voto
            JOIN opcao_voto o ON o.id_opcao = ve.id_opcao
            LEFT JOIN lote l ON l.id_usuario = v.id_eleitor_representado AND l.id_condominio = ?
            WHERE v.id_votacao = ?
            GROUP BY v.id_voto, u.nome_completo, rep.nome_completo, v.peso_aplicado, v.data_hora_voto
            ORDER BY v.data_hora_voto
            """,
            [id_condominio, id_votacao],
        )


class AuditoriaRepository:
    def __init__(self, db: Database):
        self.db = db

    def record(self, id_usuario: int | None, acao: str, entidade: str, data_hora: str, ip: str, navegador: str) -> None:
        self.db.execute(
            """
            INSERT INTO log_auditoria (id_usuario, acao, entidade, data_hora, ip, navegador)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [id_usuario, acao, entidade, data_hora, ip, navegador],
        )

    def list_recent(self) -> list[dict[str, Any]]:
        return self.db.query(
            """
            SELECT l.*, u.nome_completo
            FROM log_auditoria l
            LEFT JOIN usuario u ON u.id_usuario = l.id_usuario
            ORDER BY l.id_log DESC
            LIMIT 100
            """
        )
