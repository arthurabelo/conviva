from __future__ import annotations

import json
import mimetypes
import os
import re
from dataclasses import dataclass
from email.message import Message
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlencode

from . import models, services, templates

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"


class NotAuthenticated(Exception):
    pass


@dataclass
class Response:
    body: bytes = b""
    status: int = 200
    headers: dict[str, str] | None = None

    @classmethod
    def html(cls, body: str, status: int = 200, headers: dict[str, str] | None = None) -> "Response":
        final_headers = {"Content-Type": "text/html; charset=utf-8"}
        if headers:
            final_headers.update(headers)
        return cls(body.encode("utf-8"), status, final_headers)

    @classmethod
    def json(cls, payload: dict[str, Any], status: int = 200) -> "Response":
        return cls(
            json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            status,
            {"Content-Type": "application/json; charset=utf-8"},
        )


def redirect(location: str, headers: dict[str, str] | None = None) -> Response:
    final_headers = {"Location": location}
    if headers:
        final_headers.update(headers)
    return Response(b"", 303, final_headers)


def parse_form(body: bytes) -> dict[str, Any]:
    parsed = parse_qs(body.decode("utf-8"), keep_blank_values=True)
    return {key: values[0] if len(values) == 1 else values for key, values in parsed.items()}


def parse_query(query: str) -> dict[str, Any]:
    parsed = parse_qs(query, keep_blank_values=True)
    return {key: values[0] if len(values) == 1 else values for key, values in parsed.items()}


class ApplicationController:
    def __init__(self) -> None:
        self.db = models.Database()
        self.usuarios = models.UsuarioRepository(self.db)
        self.reunioes = models.ReuniaoRepository(self.db)
        self.votacoes = models.VotacaoRepository(self.db)
        self.auditoria_repo = models.AuditoriaRepository(self.db)
        self.auditoria = services.AuditoriaService(self.auditoria_repo)
        self.auth = services.AuthService(self.db, self.usuarios, self.auditoria)
        self.user_management = services.UserManagementService(self.usuarios, self.auditoria)
        self.reuniao_service = services.ReuniaoService(self.reunioes, self.auditoria)
        self.voting = services.VotingService(self.votacoes, self.reunioes, self.auditoria)

    def ensure_database(self) -> None:
        self.db.init_db()
        auto_seed = os.getenv("CONVIVA_AUTO_SEED", "1" if os.getenv("VERCEL") == "1" else "0") == "1"
        if not auto_seed:
            return
        row = self.db.query_one("SELECT COUNT(*) AS total FROM usuario")
        if row and int(row.get("total", 0)) > 0:
            return
        # Import local para evitar custo e dependencias em chamadas onde nao ha seed.
        from seed import main as seed_main

        seed_main()

    def dispatch(
        self,
        method: str,
        path: str,
        query: str,
        headers: Message,
        body: bytes,
        client_address: str,
    ) -> Response:
        meta = services.RequestMeta(ip=client_address, navegador=headers.get("User-Agent", ""))
        query_params = parse_query(query)
        try:
            if method == "GET" and path.startswith("/static/"):
                return self.static_file(path)
            if method == "GET" and path == "/login":
                return Response.html(templates.login())
            if method == "POST" and path == "/login":
                return self.login(body, meta)
            if method == "GET" and path == "/logout":
                return self.logout(headers, meta)

            user = self.require_user(headers)
            if method == "GET" and path == "/":
                return self.dashboard(
                    user,
                    search=str(query_params.get("busca", "")),
                    message=str(query_params.get("mensagem", "")),
                )
            if method == "GET" and path == "/votacoes":
                return Response.html(
                    templates.votacoes(
                        user,
                        self.voting.list_all(str(query_params.get("busca", ""))),
                        search=str(query_params.get("busca", "")),
                        message=str(query_params.get("mensagem", "")),
                        error=str(query_params.get("erro", "")),
                    )
                )
            if method == "GET" and path == "/votacoes/nova":
                return self.nova_votacao_form(user)
            if method == "POST" and path == "/votacoes/nova":
                return self.nova_votacao_post(user, body, meta)
            match = re.fullmatch(r"/votacoes/(\d+)/editar", path)
            if method == "GET" and match:
                return self.editar_votacao_form(user, int(match.group(1)))
            match = re.fullmatch(r"/votacoes/(\d+)/editar", path)
            if method == "POST" and match:
                return self.editar_votacao_post(user, int(match.group(1)), body, meta)
            if method == "GET" and path == "/logs":
                return self.logs(user)
            if method == "GET" and path == "/usuarios":
                return self.listar_usuarios(user, query_params)
            if method == "GET" and path == "/usuarios/novo":
                return self.usuario_form(user)
            if method == "POST" and path == "/usuarios/novo":
                return self.usuario_post(user, body, meta)
            match = re.fullmatch(r"/usuarios/(\d+)/editar", path)
            if method == "GET" and match:
                return self.usuario_form(user, int(match.group(1)))
            match = re.fullmatch(r"/usuarios/(\d+)/editar", path)
            if method == "POST" and match:
                return self.usuario_post(user, body, meta, int(match.group(1)))
            match = re.fullmatch(r"/usuarios/(\d+)/excluir", path)
            if method == "POST" and match:
                return self.excluir_usuario(user, int(match.group(1)), meta)
            match = re.fullmatch(r"/usuarios/(\d+)/lotes", path)
            if method == "GET" and match:
                return self.gerenciar_lotes(user, int(match.group(1)), query_params)
            match = re.fullmatch(r"/api/usuarios/(\d+)/lotes", path)
            if method == "POST" and match:
                return self.salvar_lote_api(user, int(match.group(1)), body, meta)
            match = re.fullmatch(r"/api/usuarios/(\d+)/lotes/(\d+)/excluir", path)
            if method == "POST" and match:
                return self.excluir_lote_api(user, int(match.group(1)), int(match.group(2)), meta)
            match = re.fullmatch(r"/usuarios/(\d+)", path)
            if method == "GET" and match:
                return self.visualizar_usuario(user, int(match.group(1)))

            match = re.fullmatch(r"/reunioes/(\d+)", path)
            if method == "GET" and match:
                return self.reuniao(user, int(match.group(1)), meta)
            match = re.fullmatch(r"/reunioes/(\d+)/sair", path)
            if method == "POST" and match:
                return self.sair_reuniao(user, int(match.group(1)), meta)
            match = re.fullmatch(r"/api/reunioes/(\d+)/votacao-ativa", path)
            if method == "GET" and match:
                return self.api_votacao_ativa(user, int(match.group(1)))
            match = re.fullmatch(r"/api/votacoes/(\d+)/votar", path)
            if method == "POST" and match:
                return self.api_votar(user, int(match.group(1)), body, meta)
            match = re.fullmatch(r"/votacoes/(\d+)/iniciar", path)
            if method == "POST" and match:
                return self.iniciar_votacao(user, int(match.group(1)), meta)
            match = re.fullmatch(r"/votacoes/(\d+)/encerrar", path)
            if method == "POST" and match:
                return self.encerrar_votacao(user, int(match.group(1)), meta)
            match = re.fullmatch(r"/votacoes/(\d+)/votar", path)
            if method == "GET" and match:
                return self.votar_form(user, int(match.group(1)))
            match = re.fullmatch(r"/votacoes/(\d+)/votar", path)
            if method == "POST" and match:
                return self.votar_post(user, int(match.group(1)), body, meta)
            match = re.fullmatch(r"/votacoes/(\d+)/resultado", path)
            if method == "GET" and match:
                return self.resultado(user, int(match.group(1)), meta)
            return Response.html(templates.not_found(user), 404)
        except NotAuthenticated:
            return redirect("/login")
        except PermissionError as exc:
            user = self.auth.current_user(headers.get("Cookie"))
            return Response.html(templates.message_page("Acesso negado", str(exc), user), 403)
        except Exception as exc:
            user = self.auth.current_user(headers.get("Cookie"))
            return Response.html(templates.message_page("Operacao nao concluida", str(exc), user), 400)

    def static_file(self, path: str) -> Response:
        parts = [part for part in path.removeprefix("/static/").split("/") if part]
        file_path = STATIC_DIR.joinpath(*parts).resolve()
        if not str(file_path).startswith(str(STATIC_DIR.resolve())) or not file_path.exists():
            return Response.html("<h1>404</h1>", 404)
        content_type = mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"
        return Response(file_path.read_bytes(), 200, {"Content-Type": content_type})

    def require_user(self, headers: Message) -> dict[str, Any]:
        user = self.auth.current_user(headers.get("Cookie"))
        if not user:
            raise NotAuthenticated()
        return user

    def require_admin(self, user: dict[str, Any]) -> None:
        if not self.auth.is_admin(user):
            raise PermissionError("Apenas Administradores/Sindicos podem acessar esta funcao.")

    def login(self, body: bytes, meta: services.RequestMeta) -> Response:
        form = parse_form(body)
        user, token, notice = self.auth.authenticate(str(form.get("email", "")), str(form.get("senha", "")), meta)
        if not user or not token:
            return Response.html(templates.login("E-mail ou senha invalidos."), 401)
        location = "/"
        if notice:
            location = f"/?{urlencode({'mensagem': notice})}"
        return redirect(location, {"Set-Cookie": f"conviva_session={token}; Path=/; HttpOnly; SameSite=Lax"})

    def logout(self, headers: Message, meta: services.RequestMeta) -> Response:
        self.auth.logout(headers.get("Cookie"), meta)
        return redirect(
            "/login",
            {"Set-Cookie": "conviva_session=; Path=/; Max-Age=0; HttpOnly; SameSite=Lax"},
        )

    def dashboard(self, user: dict[str, Any], search: str = "", message: str = "") -> Response:
        return Response.html(
            templates.dashboard(
                user=user,
                reunioes=self.reuniao_service.list_for_user(user, search),
                votacoes=self.voting.list_all(search),
                search=search,
                message=message,
            )
        )

    def nova_votacao_form(self, user: dict[str, Any], error: str = "") -> Response:
        self.require_admin(user)
        return Response.html(
            templates.form_votacao(
                user=user,
                pautas=self.reunioes.all_pautas(),
                error=error,
            )
        )

    def nova_votacao_post(self, user: dict[str, Any], body: bytes, meta: services.RequestMeta) -> Response:
        self.require_admin(user)
        form = parse_form(body)
        try:
            self.voting.create(form, user, meta)
            return redirect("/votacoes?" + urlencode({"mensagem": "Votacao criada com sucesso."}))
        except Exception as exc:
            return self.nova_votacao_form(user, str(exc))

    def editar_votacao_form(self, user: dict[str, Any], id_votacao: int, error: str = "") -> Response:
        self.require_admin(user)
        votacao = self.votacoes.get(id_votacao)
        if not votacao:
            return Response.html(templates.message_page("Votacao nao encontrada", "A votacao solicitada nao existe.", user), 404)
        if votacao["status"] != "agendada":
            return Response.html(
                templates.message_page(
                    "Editar votacao",
                    "Somente votacoes agendadas podem ser editadas.",
                    user,
                ),
                403,
            )
        opcoes = self.votacoes.options(id_votacao)
        return Response.html(
            templates.form_votacao(
                user=user,
                pautas=self.reunioes.all_pautas(),
                error=error,
                votacao=votacao,
                opcoes_text="\n".join(str(opcao["descricao"]) for opcao in opcoes),
                action=f"/votacoes/{id_votacao}/editar",
                title="Editar votacao",
                submit_label="Salvar alteracoes",
            )
        )

    def editar_votacao_post(self, user: dict[str, Any], id_votacao: int, body: bytes, meta: services.RequestMeta) -> Response:
        self.require_admin(user)
        form = parse_form(body)
        try:
            self.voting.update(id_votacao, form, user, meta)
            return redirect("/votacoes?" + urlencode({"mensagem": "Votacao atualizada com sucesso."}))
        except Exception as exc:
            return self.editar_votacao_form(user, id_votacao, str(exc))

    def reuniao(self, user: dict[str, Any], id_reuniao: int, meta: services.RequestMeta) -> Response:
        reuniao = self.reuniao_service.enter(id_reuniao, user, meta)
        active = self.voting.active_payload_for_meeting(id_reuniao, user)
        active_html = templates.vote_panel(user, active)
        return Response.html(
            templates.reuniao(
                user=user,
                reuniao=reuniao,
                pautas=self.reuniao_service.pautas(id_reuniao),
                participantes=self.reuniao_service.participantes(id_reuniao),
                votacoes=self.voting.list_for_meeting(id_reuniao),
                active_vote_html=active_html,
            )
        )

    def sair_reuniao(self, user: dict[str, Any], id_reuniao: int, meta: services.RequestMeta) -> Response:
        self.reuniao_service.leave(id_reuniao, user, meta)
        return redirect("/")

    def api_votacao_ativa(self, user: dict[str, Any], id_reuniao: int) -> Response:
        payload = self.voting.active_payload_for_meeting(id_reuniao, user)
        return Response.json(
            {
                "html": templates.vote_panel(user, payload),
                "seconds_left": payload.get("seconds_left", 0),
                "has_active": bool(payload.get("active")),
            }
        )

    def api_votar(self, user: dict[str, Any], id_votacao: int, body: bytes, meta: services.RequestMeta) -> Response:
        form = parse_form(body)
        try:
            self.voting.register_vote(id_votacao, form.get("id_opcao") or [], user, meta)
            votacao = self.votacoes.get(id_votacao)
            payload = self.voting.active_payload_for_meeting(int(votacao["id_reuniao"]), user) if votacao else {}
            return Response.json({"ok": True, "message": "Voto confirmado com sucesso.", "html": templates.vote_panel(user, payload, message="Voto confirmado com sucesso.")})
        except Exception as exc:
            votacao = self.votacoes.get(id_votacao)
            payload = self.voting.active_payload_for_meeting(int(votacao["id_reuniao"]), user) if votacao else {}
            return Response.json({"ok": False, "message": str(exc), "html": templates.vote_panel(user, payload, error=str(exc))}, 400)

    def iniciar_votacao(self, user: dict[str, Any], id_votacao: int, meta: services.RequestMeta) -> Response:
        self.voting.start(id_votacao, user, meta)
        votacao = self.votacoes.get(id_votacao)
        if votacao:
            return redirect(f"/reunioes/{votacao['id_reuniao']}")
        return redirect("/votacoes")

    def encerrar_votacao(self, user: dict[str, Any], id_votacao: int, meta: services.RequestMeta) -> Response:
        self.voting.close(id_votacao, user, meta)
        return redirect(f"/votacoes/{id_votacao}/resultado")

    def votar_form(self, user: dict[str, Any], id_votacao: int) -> Response:
        votacao = self.votacoes.get(id_votacao)
        if not votacao:
            raise ValueError("Votacao nao encontrada.")
        payload = self.voting.active_payload_for_meeting(int(votacao["id_reuniao"]), user)
        return Response.html(templates.base("Votar", templates.vote_panel(user, payload), user))

    def votar_post(self, user: dict[str, Any], id_votacao: int, body: bytes, meta: services.RequestMeta) -> Response:
        form = parse_form(body)
        self.voting.register_vote(id_votacao, form.get("id_opcao") or [], user, meta)
        votacao = self.votacoes.get(id_votacao)
        return redirect(f"/reunioes/{votacao['id_reuniao']}" if votacao else "/")

    def resultado(self, user: dict[str, Any], id_votacao: int, meta: services.RequestMeta) -> Response:
        result = self.voting.result(id_votacao)
        if result["votacao"]["status"] not in {"encerrada", "invalidada"}:
            return Response.html(
                templates.message_page(
                    "Resultado indisponivel",
                    "O resultado somente fica disponivel apos o encerramento da votacao.",
                    user,
                ),
                403,
            )
        self.auditoria.registrar(user, "visualizou resultado", f"votacao:{id_votacao}", meta)
        return Response.html(templates.resultado(user, result))

    def logs(self, user: dict[str, Any]) -> Response:
        self.require_admin(user)
        return Response.html(templates.logs(user, self.auditoria_repo.list_recent()))

    def listar_usuarios(self, user: dict[str, Any], query: dict[str, Any]) -> Response:
        self.require_admin(user)
        nome = str(query.get("nome", ""))
        tipo = str(query.get("tipo", ""))
        return Response.html(
            templates.usuarios(
                user,
                self.user_management.list(nome, tipo),
                nome,
                tipo,
                str(query.get("mensagem", "")),
                str(query.get("erro", "")),
            )
        )

    def usuario_form(
        self,
        user: dict[str, Any],
        id_usuario: int | None = None,
        error: str = "",
        values: dict[str, Any] | None = None,
    ) -> Response:
        self.require_admin(user)
        usuario = values or (self.user_management.get(id_usuario) if id_usuario is not None else {})
        return Response.html(templates.form_usuario(user, usuario, error, id_usuario))

    def usuario_post(
        self,
        user: dict[str, Any],
        body: bytes,
        meta: services.RequestMeta,
        id_usuario: int | None = None,
    ) -> Response:
        self.require_admin(user)
        form = parse_form(body)
        try:
            self.user_management.save(form, user, meta, id_usuario)
            message = "Usuário atualizado com sucesso." if id_usuario else "Usuário cadastrado com sucesso."
            return redirect("/usuarios?" + urlencode({"mensagem": message}))
        except Exception as exc:
            return self.usuario_form(user, id_usuario, str(exc), form)

    def visualizar_usuario(self, user: dict[str, Any], id_usuario: int) -> Response:
        self.require_admin(user)
        usuario = self.user_management.get(id_usuario)
        condominio = self.usuarios.default_condominio()
        lotes = []
        if usuario["tipo_usuario"] == "proprietario" and condominio:
            lotes = self.usuarios.lots(id_usuario, int(condominio["id_condominio"]))
        return Response.html(templates.visualizar_usuario(user, usuario, lotes))

    def excluir_usuario(self, user: dict[str, Any], id_usuario: int, meta: services.RequestMeta) -> Response:
        self.require_admin(user)
        try:
            self.user_management.delete(id_usuario, user, meta)
            return redirect("/usuarios?" + urlencode({"mensagem": "Usuário excluído com sucesso."}))
        except Exception as exc:
            return redirect("/usuarios?" + urlencode({"erro": str(exc)}))

    def gerenciar_lotes(self, user: dict[str, Any], id_usuario: int, query: dict[str, Any]) -> Response:
        self.require_admin(user)
        usuario, condominio, lotes = self.user_management.lots_context(id_usuario)
        return Response.html(
            templates.gerenciar_lotes(
                user,
                usuario,
                condominio,
                lotes,
                str(query.get("mensagem", "")),
                str(query.get("erro", "")),
            )
        )

    def salvar_lote_api(self, user: dict[str, Any], id_usuario: int, body: bytes, meta: services.RequestMeta) -> Response:
        self.require_admin(user)
        try:
            self.user_management.save_lot(id_usuario, parse_form(body), user, meta)
            _, _, lotes = self.user_management.lots_context(id_usuario)
            return Response.json({"ok": True, "message": "Lote vinculado com sucesso.", "html": templates.lotes_table(id_usuario, lotes)})
        except Exception as exc:
            return Response.json({"ok": False, "message": str(exc)}, 400)

    def excluir_lote_api(
        self,
        user: dict[str, Any],
        id_usuario: int,
        id_lote: int,
        meta: services.RequestMeta,
    ) -> Response:
        self.require_admin(user)
        try:
            self.user_management.delete_lot(id_usuario, id_lote, user, meta)
            _, _, lotes = self.user_management.lots_context(id_usuario)
            return Response.json({"ok": True, "message": "Vínculo removido com sucesso.", "html": templates.lotes_table(id_usuario, lotes)})
        except Exception as exc:
            return Response.json({"ok": False, "message": str(exc)}, 400)
