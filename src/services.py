from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Iterable

from . import models, security

DATE_FMT = "%Y-%m-%d %H:%M:%S"


def now_str() -> str:
    return datetime.now().strftime(DATE_FMT)


def parse_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str) and value:
        for fmt in (DATE_FMT, "%Y-%m-%dT%H:%M:%S"):
            try:
                return datetime.strptime(value[:19], fmt)
            except ValueError:
                continue
    return None


@dataclass(frozen=True)
class RequestMeta:
    ip: str = ""
    navegador: str = ""


class AuditoriaService:
    def __init__(self, auditoria_repo: models.AuditoriaRepository):
        self.auditoria_repo = auditoria_repo

    def registrar(self, user: dict[str, Any] | None, acao: str, entidade: str, meta: RequestMeta) -> None:
        self.auditoria_repo.record(
            int(user["id_usuario"]) if user else None,
            acao,
            entidade,
            now_str(),
            meta.ip,
            meta.navegador[:255],
        )


class AuthService:
    def __init__(self, db: models.Database, usuarios: models.UsuarioRepository, auditoria: AuditoriaService):
        self.db = db
        self.usuarios = usuarios
        self.auditoria = auditoria
        self.hasher = security.PasswordHasher()
        self.expire_seconds = int(os.getenv("SESSION_EXPIRE_SECONDS", "86400"))
        self.signer = security.TokenSigner(os.getenv("SECRET_KEY", "conviva-local-demo-secret"))

    def authenticate(self, email: str, password: str, meta: RequestMeta) -> tuple[dict[str, Any] | None, str | None, str | None]:
        user = self.usuarios.by_email(email)
        if not user or not self.hasher.verify(password, user["senha_hash"]):
            return None, None, None
        token, revoked_ip = self.create_session(int(user["id_usuario"]), meta)
        self.auditoria.registrar(user, "entrou no sistema", "sessao", meta)
        notice = None
        if revoked_ip:
            notice = f"Sessao anterior encerrada. IP da maquina anterior: {revoked_ip or 'desconhecido'}."
        return user, token, notice

    def create_session(self, id_usuario: int, meta: RequestMeta) -> tuple[str, str | None]:
        self.cleanup_expired_sessions()
        active = self.db.query_one(
            """
            SELECT id_sessao, ip FROM sessao_usuario
            WHERE id_usuario = ? AND encerrada_em IS NULL AND expira_em > ?
            ORDER BY criada_em DESC
            LIMIT 1
            """,
            [id_usuario, now_str()],
        )
        revoked_ip = str(active["ip"]) if active and active.get("ip") else None
        if active:
            self.db.execute(
                "UPDATE sessao_usuario SET encerrada_em = ? WHERE id_usuario = ? AND encerrada_em IS NULL AND expira_em > ?",
                [now_str(), id_usuario, now_str()],
            )
        expires_ts = int(time.time()) + self.expire_seconds
        token = self.signer.build(id_usuario, expires_ts)
        self.db.execute(
            """
            INSERT INTO sessao_usuario (id_usuario, token_hash, criada_em, expira_em, ip, navegador)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                id_usuario,
                self.signer.token_hash(token),
                now_str(),
                datetime.fromtimestamp(expires_ts).strftime(DATE_FMT),
                meta.ip,
                meta.navegador[:255],
            ],
        )
        return token, revoked_ip

    def current_user(self, cookie_header: str | None) -> dict[str, Any] | None:
        token = security.parse_cookie(cookie_header).get("conviva_session")
        if not token:
            return None
        id_usuario = self.signer.parse(token)
        if not id_usuario:
            return None
        active = self.db.query_one(
            """
            SELECT 1 FROM sessao_usuario
            WHERE id_usuario = ? AND token_hash = ? AND encerrada_em IS NULL AND expira_em > ?
            """,
            [id_usuario, self.signer.token_hash(token), now_str()],
        )
        if not active:
            return None
        return self.usuarios.by_id(id_usuario)

    def logout(self, cookie_header: str | None, meta: RequestMeta) -> None:
        token = security.parse_cookie(cookie_header).get("conviva_session")
        user = self.current_user(cookie_header)
        if token:
            self.db.execute(
                "UPDATE sessao_usuario SET encerrada_em = ? WHERE token_hash = ? AND encerrada_em IS NULL",
                [now_str(), self.signer.token_hash(token)],
            )
        self.auditoria.registrar(user, "saiu do sistema", "sessao", meta)

    def cleanup_expired_sessions(self) -> None:
        self.db.execute(
            "UPDATE sessao_usuario SET encerrada_em = ? WHERE encerrada_em IS NULL AND expira_em <= ?",
            [now_str(), now_str()],
        )

    @staticmethod
    def is_admin(user: dict[str, Any] | None) -> bool:
        return bool(user and user.get("tipo_usuario") == "administrador")


EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
TIPOS_VALIDOS = {"administrador", "proprietario", "procurador"}


class UsuarioService:
    def __init__(
        self,
        usuarios: models.UsuarioRepository,
        auditoria: AuditoriaService,
    ):
        self.usuarios = usuarios
        self.auditoria = auditoria
        self.hasher = security.PasswordHasher()

    def list_usuarios(self, search: str = "", tipo: str = "") -> list[dict[str, Any]]:
        return self.usuarios.list_all(search, tipo)

    def get_usuario(self, id_usuario: int) -> dict[str, Any] | None:
        return self.usuarios.by_id(id_usuario)

    def _validate_common(self, nome: str, email: str, tipo: str, exclude_id: int | None) -> None:
        if not nome.strip():
            raise ValueError("Informe o nome completo do usuario.")
        # EX01 / RN01 - formato e unicidade do e-mail.
        if not EMAIL_RE.match(email.strip()):
            raise ValueError("E-mail invalido ou ja cadastrado no sistema.")
        if self.usuarios.email_exists(email, exclude_id):
            raise ValueError("E-mail invalido ou ja cadastrado no sistema.")
        if tipo not in TIPOS_VALIDOS:
            raise ValueError("Selecione um tipo de usuario valido.")

    def create_usuario(self, form: dict[str, Any], actor: dict[str, Any], meta: RequestMeta) -> int:
        nome = str(form.get("nome_completo", "")).strip()
        email = str(form.get("email", "")).strip()
        tipo = str(form.get("tipo_usuario", "")).strip()
        senha = str(form.get("senha", ""))
        self._validate_common(nome, email, tipo, exclude_id=None)
        if len(senha) < 6:
            raise ValueError("A senha deve possuir ao menos 6 caracteres.")
        id_usuario = self.usuarios.create(nome, email, self.hasher.hash(senha), tipo)
        self.auditoria.registrar(actor, "cadastrou usuario", f"usuario:{id_usuario}", meta)
        return id_usuario

    def update_usuario(self, id_usuario: int, form: dict[str, Any], actor: dict[str, Any], meta: RequestMeta) -> None:
        existente = self.usuarios.by_id(id_usuario)
        if not existente:
            raise ValueError("Usuario nao encontrado.")
        nome = str(form.get("nome_completo", "")).strip()
        email = str(form.get("email", "")).strip()
        tipo = str(form.get("tipo_usuario", "")).strip()
        senha = str(form.get("senha", ""))
        self._validate_common(nome, email, tipo, exclude_id=id_usuario)
        senha_hash = None
        if senha:
            if len(senha) < 6:
                raise ValueError("A senha deve possuir ao menos 6 caracteres.")
            senha_hash = self.hasher.hash(senha)
        self.usuarios.update(id_usuario, nome, email, tipo, senha_hash)
        self.auditoria.registrar(actor, "alterou usuario", f"usuario:{id_usuario}", meta)

    def delete_usuario(self, id_usuario: int, actor: dict[str, Any], meta: RequestMeta) -> None:
        if int(actor["id_usuario"]) == id_usuario:
            raise ValueError("Nao e possivel excluir o proprio usuario em uso.")
        if not self.usuarios.by_id(id_usuario):
            raise ValueError("Usuario nao encontrado.")
        self.usuarios.deactivate(id_usuario)
        self.auditoria.registrar(actor, "excluiu usuario", f"usuario:{id_usuario}", meta)


class LoteService:
    def __init__(
        self,
        lotes: models.LoteRepository,
        usuarios: models.UsuarioRepository,
        condominios: models.CondominioRepository,
        auditoria: AuditoriaService,
    ):
        self.lotes = lotes
        self.usuarios = usuarios
        self.condominios = condominios
        self.auditoria = auditoria

    def _ensure_proprietario(self, id_usuario: int) -> dict[str, Any]:
        usuario = self.usuarios.by_id(id_usuario)
        if not usuario:
            raise ValueError("Usuario nao encontrado.")
        # RN02 - somente proprietarios possuem lotes.
        if usuario["tipo_usuario"] != "proprietario":
            raise PermissionError("Apenas usuarios do tipo Proprietario podem ter lotes vinculados.")
        return usuario

    def _condominio(self) -> dict[str, Any]:
        condominio = self.condominios.default()
        if not condominio:
            raise ValueError("Nenhum condominio ativo cadastrado para vincular lotes.")
        return condominio

    def overview(self, id_usuario: int) -> dict[str, Any]:
        usuario = self._ensure_proprietario(id_usuario)
        registros = self.lotes.list_for_user(id_usuario)
        lotes: list[dict[str, Any]] = []
        total_acumulado = 0.0
        total_efetivo = 0.0
        for lote in registros:
            peso = float(lote["peso_original"])
            inadimplente = int(lote["inadimplente"]) == 1
            # RN04 - inadimplente zera o peso efetivo no voto.
            peso_efetivo = 0.0 if inadimplente else peso
            total_acumulado += peso
            total_efetivo += peso_efetivo
            lotes.append(
                {
                    "id_lote": int(lote["id_lote"]),
                    "identificacao": lote["identificacao"],
                    "peso_original": peso,
                    "inadimplente": inadimplente,
                    "peso_efetivo": peso_efetivo,
                }
            )
        return {
            "usuario": usuario,
            "lotes": lotes,
            "total_acumulado": total_acumulado,  # RN05
            "total_efetivo": total_efetivo,  # RN05
        }

    @staticmethod
    def _parse_peso(valor: Any) -> float:
        try:
            peso = float(str(valor).replace(",", "."))
        except (TypeError, ValueError):
            raise ValueError("O campo Fracao/Peso deve receber um valor numerico superior a 0.00.")
        # EX02 - peso deve ser estritamente maior que zero.
        if peso <= 0:
            raise ValueError("O campo Fracao/Peso deve receber um valor numerico superior a 0.00.")
        return peso

    def add_lote(self, id_usuario: int, form: dict[str, Any], actor: dict[str, Any], meta: RequestMeta) -> None:
        self._ensure_proprietario(id_usuario)
        condominio = self._condominio()
        identificacao = str(form.get("identificacao", "")).strip()
        if not identificacao:
            raise ValueError("Informe a identificacao do lote/unidade.")
        peso = self._parse_peso(form.get("peso"))
        inadimplente = 1 if str(form.get("inadimplente", "0")) in {"1", "sim", "Sim", "true"} else 0
        # EX03 / RN03 - lote unico por proprietario ativo no condominio.
        conflito = self.lotes.owner_of(int(condominio["id_condominio"]), identificacao)
        if conflito:
            raise ValueError("A unidade selecionada ja esta associada a outro proprietario ativo.")
        id_lote = self.lotes.create(int(condominio["id_condominio"]), id_usuario, identificacao, peso, inadimplente)
        self.auditoria.registrar(actor, "vinculou lote", f"lote:{id_lote}", meta)

    def update_lote(self, id_usuario: int, id_lote: int, form: dict[str, Any], actor: dict[str, Any], meta: RequestMeta) -> None:
        self._ensure_proprietario(id_usuario)
        condominio = self._condominio()
        lote = self.lotes.get(id_lote)
        if not lote or int(lote["id_usuario"]) != id_usuario:
            raise ValueError("Lote nao encontrado para este proprietario.")
        identificacao = str(form.get("identificacao", "")).strip()
        if not identificacao:
            raise ValueError("Informe a identificacao do lote/unidade.")
        peso = self._parse_peso(form.get("peso"))
        inadimplente = 1 if str(form.get("inadimplente", "0")) in {"1", "sim", "Sim", "true"} else 0
        conflito = self.lotes.owner_of(int(condominio["id_condominio"]), identificacao, exclude_id=id_lote)
        if conflito:
            raise ValueError("A unidade selecionada ja esta associada a outro proprietario ativo.")
        self.lotes.update(id_lote, identificacao, peso, inadimplente)
        self.auditoria.registrar(actor, "alterou lote", f"lote:{id_lote}", meta)

    def delete_lote(self, id_usuario: int, id_lote: int, actor: dict[str, Any], meta: RequestMeta) -> None:
        lote = self.lotes.get(id_lote)
        if not lote or int(lote["id_usuario"]) != id_usuario:
            raise ValueError("Lote nao encontrado para este proprietario.")
        self.lotes.delete(id_lote)
        self.auditoria.registrar(actor, "removeu lote", f"lote:{id_lote}", meta)


class ReuniaoService:
    def __init__(
        self,
        reunioes: models.ReuniaoRepository,
        auditoria: AuditoriaService,
    ):
        self.reunioes = reunioes
        self.auditoria = auditoria

    def list_for_user(self, user: dict[str, Any], search: str = "") -> list[dict[str, Any]]:
        return self.reunioes.list_for_user(user, search)

    def enter(self, id_reuniao: int, user: dict[str, Any], meta: RequestMeta) -> dict[str, Any]:
        reuniao = self.reunioes.get(id_reuniao)
        if not reuniao:
            raise PermissionError("Reuniao nao encontrada.")
        if not self.reunioes.is_invited(user["id_usuario"], id_reuniao):
            raise PermissionError("Apenas convidados podem acessar esta reuniao.")
        self.reunioes.mark_present(user["id_usuario"], id_reuniao, now_str())
        self.auditoria.registrar(user, "entrou na reuniao", f"reuniao:{id_reuniao}", meta)
        return reuniao

    def leave(self, id_reuniao: int, user: dict[str, Any], meta: RequestMeta) -> None:
        if self.reunioes.is_invited(user["id_usuario"], id_reuniao):
            self.reunioes.mark_absent(user["id_usuario"], id_reuniao, now_str())
        self.auditoria.registrar(user, "saiu da reuniao", f"reuniao:{id_reuniao}", meta)

    def participantes(self, id_reuniao: int) -> list[dict[str, Any]]:
        return self.reunioes.participantes(id_reuniao)

    def pautas(self, id_reuniao: int) -> list[dict[str, Any]]:
        return self.reunioes.pautas(id_reuniao)


class VotingService:
    def __init__(
        self,
        votacoes: models.VotacaoRepository,
        reunioes: models.ReuniaoRepository,
        auditoria: AuditoriaService,
    ):
        self.votacoes = votacoes
        self.reunioes = reunioes
        self.auditoria = auditoria

    def list_all(self, search: str = "") -> list[dict[str, Any]]:
        self.auto_close_expired()
        return self.votacoes.list_all(search)

    def list_for_meeting(self, id_reuniao: int, search: str = "") -> list[dict[str, Any]]:
        self.auto_close_expired()
        return self.votacoes.list_for_meeting(id_reuniao, search)

    def create(self, form: dict[str, Any], user: dict[str, Any], meta: RequestMeta) -> int:
        if user["tipo_usuario"] != "administrador":
            raise PermissionError("Apenas Administradores/Sindicos podem cadastrar votacoes.")

        data, opcoes = self._form_to_data(form)
        self._validate_voting_config(data, opcoes)
        id_votacao = self.votacoes.create(data, opcoes)
        self.auditoria.registrar(user, "criou votacao", f"votacao:{id_votacao}", meta)
        return id_votacao

    def update(self, id_votacao: int, form: dict[str, Any], user: dict[str, Any], meta: RequestMeta) -> None:
        if user["tipo_usuario"] != "administrador":
            raise PermissionError("Apenas Administradores/Sindicos podem editar votacoes.")
        votacao = self._get_required(id_votacao)
        if votacao["status"] != "agendada":
            raise ValueError("Somente votacoes agendadas podem ser editadas.")

        data, opcoes = self._form_to_data(form)
        self._validate_voting_config(data, opcoes)
        self.votacoes.update(id_votacao, data, opcoes)
        self.auditoria.registrar(user, "editou votacao", f"votacao:{id_votacao}", meta)

    @staticmethod
    def _form_to_data(form: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
        opcoes = [line.strip() for line in str(form.get("opcoes", "")).splitlines() if line.strip()]
        data = {
            "id_pauta": int(form.get("id_pauta") or 0),
            "assunto": str(form.get("assunto", "")).strip(),
            "pergunta": str(form.get("pergunta", "")).strip(),
            "tipo_votacao": str(form.get("tipo_votacao", "aberta")).strip(),
            "tipo_resposta": str(form.get("tipo_resposta", "escolha_unica")).strip(),
            "tempo_resposta": int(form.get("tempo_resposta") or 0),
            "max_marcacoes": int(form.get("max_marcacoes") or 1),
        }
        return data, opcoes

    def _validate_voting_config(self, data: dict[str, Any], opcoes: list[str]) -> None:
        if not data["id_pauta"]:
            raise ValueError("Toda votacao deve estar vinculada a uma pauta.")
        if not data["assunto"] or len(data["assunto"]) > 255:
            raise ValueError("Informe o assunto da votacao com ate 255 caracteres.")
        if not data["pergunta"] or len(data["pergunta"]) > 255:
            raise ValueError("Informe a pergunta da votacao com ate 255 caracteres.")
        if data["tipo_votacao"] not in {"aberta", "fechada"}:
            raise ValueError("Tipo de votacao invalido.")
        if data["tipo_resposta"] not in {"escolha_unica", "multipla_escolha", "eleicao"}:
            raise ValueError("Tipo de resposta invalido.")
        if data["tempo_resposta"] <= 0:
            raise ValueError("O tempo de resposta deve ser maior que zero.")
        if len(opcoes) < 2:
            raise ValueError("Cadastre pelo menos duas opcoes de voto.")
        if data["tipo_resposta"] != "multipla_escolha":
            data["max_marcacoes"] = 1
        if data["max_marcacoes"] < 1 or data["max_marcacoes"] > len(opcoes):
            raise ValueError("A quantidade de marcacoes deve estar entre 1 e o total de opcoes.")

    def start(self, id_votacao: int, user: dict[str, Any], meta: RequestMeta) -> None:
        if user["tipo_usuario"] != "administrador":
            raise PermissionError("Apenas Administradores/Sindicos podem iniciar votacoes.")
        votacao = self._get_required(id_votacao)
        if votacao["status"] != "agendada":
            raise ValueError("Somente votacoes agendadas podem ser iniciadas.")
        if votacao["reuniao_status"] != "em_andamento":
            raise ValueError("A votacao somente pode ser iniciada durante a reuniao vinculada.")
        if self.votacoes.has_active_in_meeting(votacao["id_reuniao"], id_votacao):
            raise ValueError("Ja existe uma votacao ativa nesta reuniao.")
        inicio = datetime.now()
        fim = inicio + timedelta(minutes=int(votacao["tempo_resposta"]))
        self.votacoes.start(id_votacao, inicio.strftime(DATE_FMT), fim.strftime(DATE_FMT))
        self.auditoria.registrar(user, "iniciou votacao", f"votacao:{id_votacao}", meta)

    def close(self, id_votacao: int, user: dict[str, Any], meta: RequestMeta) -> None:
        if user["tipo_usuario"] != "administrador":
            raise PermissionError("Apenas Administradores/Sindicos podem encerrar votacoes.")
        votacao = self._get_required(id_votacao)
        if votacao["status"] not in {"agendada", "ativa"}:
            raise ValueError("A votacao ja esta encerrada ou invalidada.")
        self.votacoes.close(id_votacao, now_str())
        self.auditoria.registrar(user, "encerrou votacao", f"votacao:{id_votacao}", meta)

    def active_payload_for_meeting(self, id_reuniao: int, user: dict[str, Any]) -> dict[str, Any]:
        self.auto_close_expired()
        if not self.reunioes.is_present(user["id_usuario"], id_reuniao):
            return {"active": None, "message": "Entre na reuniao para visualizar votacoes ativas."}
        votacao = self.votacoes.active_for_meeting(id_reuniao)
        if not votacao:
            return {"active": None, "message": "Nenhuma votacao ativa no momento."}
        voter = self._voter_context(votacao, user, fail_hard=False)
        ja_votou = False
        if voter.get("id_eleitor_representado"):
            ja_votou = bool(self.votacoes.voto_by_pauta_representado(votacao["id_pauta"], voter["id_eleitor_representado"]))
        return {
            "active": votacao,
            "options": self.votacoes.options(votacao["id_votacao"]),
            "weight": voter.get("peso", 0),
            "can_vote": voter.get("can_vote", False) and not ja_votou,
            "blocked_reason": voter.get("blocked_reason", ""),
            "already_voted": ja_votou,
            "seconds_left": self.seconds_left(votacao),
        }

    def register_vote(
        self,
        id_votacao: int,
        escolhas_raw: int | str | Iterable[int | str],
        user: dict[str, Any],
        meta: RequestMeta,
    ) -> int:
        self.auto_close_if_expired(id_votacao)
        votacao = self._get_required(id_votacao)
        if votacao["status"] != "ativa":
            raise ValueError("A votacao nao esta ativa.")
        if not self.reunioes.is_invited(user["id_usuario"], votacao["id_reuniao"]) or not self.reunioes.is_present(user["id_usuario"], votacao["id_reuniao"]):
            self.votacoes.invalidate(id_votacao, now_str())
            self.auditoria.registrar(user, "tentou votar sem autorizacao; votacao invalidada", f"votacao:{id_votacao}", meta)
            raise PermissionError("Apenas participantes convidados e presentes podem votar.")

        voter = self._voter_context(votacao, user, fail_hard=True)
        id_eleitor = int(voter["id_eleitor_representado"])
        if self.votacoes.voto_by_pauta_representado(int(votacao["id_pauta"]), id_eleitor):
            raise ValueError("Este usuario ja votou nesta pauta.")

        escolhas = self._normalizar_escolhas(escolhas_raw)
        opcoes_validas = {int(row["id_opcao"]) for row in self.votacoes.options(id_votacao)}
        self._validate_choices(votacao, escolhas, opcoes_validas)

        id_voto = self.votacoes.record_vote(
            id_votacao=id_votacao,
            id_usuario=int(user["id_usuario"]),
            id_eleitor_representado=id_eleitor,
            id_procuracao=voter.get("id_procuracao"),
            peso=float(voter["peso"]),
            escolhas=escolhas,
            data_hora=now_str(),
            ip=meta.ip,
            navegador=meta.navegador[:255],
        )
        self.auditoria.registrar(user, "registrou voto", f"votacao:{id_votacao}", meta)
        return id_voto

    def _voter_context(self, votacao: dict[str, Any], user: dict[str, Any], fail_hard: bool) -> dict[str, Any]:
        id_reuniao = int(votacao["id_reuniao"])
        id_condominio = int(votacao["id_condominio"])
        owner_proxy = self.votacoes.proxy_for_owner(int(user["id_usuario"]), id_reuniao)
        if owner_proxy:
            message = f"Voto transferido para o procurador {owner_proxy['procurador_nome']}."
            if fail_hard:
                raise PermissionError(message)
            return {"can_vote": False, "blocked_reason": message}

        attorney_proxy = self.votacoes.proxy_for_attorney(int(user["id_usuario"]), id_reuniao)
        if attorney_proxy:
            represented = int(attorney_proxy["id_proprietario"])
            return {
                "can_vote": True,
                "id_eleitor_representado": represented,
                "id_procuracao": int(attorney_proxy["id_procuracao"]),
                "peso": self.votacoes.peso_usuario(represented, id_condominio),
                "represented_name": attorney_proxy["proprietario_nome"],
            }

        total_lotes = self.votacoes.total_lotes(int(user["id_usuario"]), id_condominio)
        if total_lotes == 0:
            message = "Usuario sem unidade vinculada ao condominio desta votacao."
            if fail_hard:
                raise PermissionError(message)
            return {"can_vote": False, "blocked_reason": message}
        return {
            "can_vote": True,
            "id_eleitor_representado": int(user["id_usuario"]),
            "id_procuracao": None,
            "peso": self.votacoes.peso_usuario(int(user["id_usuario"]), id_condominio),
        }

    def _validate_choices(self, votacao: dict[str, Any], escolhas: list[int], opcoes_validas: set[int]) -> None:
        if not escolhas:
            raise ValueError("Selecione pelo menos uma opcao.")
        if len(escolhas) != len(set(escolhas)):
            raise ValueError("A mesma opcao nao pode ser marcada mais de uma vez.")
        if not set(escolhas).issubset(opcoes_validas):
            raise ValueError("Opcao de voto invalida.")
        if votacao["tipo_resposta"] != "multipla_escolha" and len(escolhas) != 1:
            raise ValueError("Esta votacao permite apenas uma opcao.")
        if len(escolhas) > int(votacao["max_marcacoes"]):
            raise ValueError(f"Selecione no maximo {votacao['max_marcacoes']} opcao(oes).")

    def result(self, id_votacao: int) -> dict[str, Any]:
        self.auto_close_if_expired(id_votacao)
        votacao = self._get_required(id_votacao)
        rows = self.votacoes.option_totals(id_votacao)
        totalizadores = self.votacoes.totalizadores(id_votacao)
        total_peso_opcoes = sum(float(row["peso_acumulado"] or 0) for row in rows)
        opcoes = []
        for row in rows:
            peso = float(row["peso_acumulado"] or 0)
            opcoes.append(
                {
                    "descricao": row["descricao"],
                    "peso": peso,
                    "votos": int(row["total_votos"] or 0),
                    "percentual": (peso / total_peso_opcoes * 100) if total_peso_opcoes else 0,
                }
            )
        nominais: list[dict[str, Any]] = []
        if votacao["tipo_votacao"] == "aberta":
            nominais = self.votacoes.votos_nominais(id_votacao, int(votacao["id_condominio"]))
        return {
            "votacao": votacao,
            "opcoes": opcoes,
            "total_votos": int(totalizadores["total_votos"] or 0),
            "total_peso": float(totalizadores["total_peso"] or 0),
            "total_peso_opcoes": total_peso_opcoes,
            "nominais": nominais,
        }

    def seconds_left(self, votacao: dict[str, Any]) -> int:
        encerra_em = parse_datetime(votacao.get("encerra_em"))
        if not encerra_em:
            return 0
        return max(0, int((encerra_em - datetime.now()).total_seconds()))

    def auto_close_expired(self) -> None:
        for row in self.votacoes.db.query("SELECT id_votacao FROM votacao WHERE status = 'ativa' AND encerra_em IS NOT NULL"):
            self.auto_close_if_expired(int(row["id_votacao"]))

    def auto_close_if_expired(self, id_votacao: int) -> None:
        votacao = self.votacoes.get(id_votacao)
        if not votacao or votacao["status"] != "ativa":
            return
        encerra_em = parse_datetime(votacao.get("encerra_em"))
        if encerra_em and datetime.now() >= encerra_em:
            self.votacoes.close(id_votacao, now_str())

    def _get_required(self, id_votacao: int) -> dict[str, Any]:
        votacao = self.votacoes.get(id_votacao)
        if not votacao:
            raise ValueError("Votacao nao encontrada.")
        return votacao

    @staticmethod
    def _normalizar_escolhas(raw: int | str | Iterable[int | str]) -> list[int]:
        if isinstance(raw, (int, str)):
            values = [raw]
        else:
            values = list(raw or [])
        return [int(value) for value in values if str(value).strip()]
