from http import HTTPStatus
from typing import Any
from urllib.parse import parse_qs

from . import security, services, templates


class Response:
    def __init__(self, body: str = "", status: int = 200, headers: dict[str, str] | None = None):
        self.body = body
        self.status = status
        self.headers = headers or {}


def redirect(location: str, headers: dict[str, str] | None = None) -> Response:
    final_headers = {"Location": location}
    if headers:
        final_headers.update(headers)
    return Response("", HTTPStatus.SEE_OTHER, final_headers)


def parse_form(raw: bytes) -> dict[str, Any]:
    data = parse_qs(raw.decode("utf-8"), keep_blank_values=True)
    return {k: v[0] if len(v) == 1 else v for k, v in data.items()}


def client_ip(handler: Any) -> str:
    return handler.client_address[0] if handler.client_address else ""


def user_agent(handler: Any) -> str:
    return handler.headers.get("User-Agent", "")[:255]


def require_user(handler: Any) -> dict[str, Any] | Response:
    user = security.get_current_user(handler.headers.get("Cookie"))
    if not user:
        return redirect("/login")
    return user


def require_admin(handler: Any) -> dict[str, Any] | Response:
    user = require_user(handler)
    if isinstance(user, Response):
        return user
    if not security.is_admin(user):
        return Response(templates.base("Acesso negado", "<section class='card'><h1>Acesso negado</h1><p>Apenas Administrador/Síndico pode acessar esta função.</p></section>", user), 403)
    return user


def get_login(handler: Any) -> Response:
    return Response(templates.login())


def post_login(handler: Any, raw: bytes) -> Response:
    form = parse_form(raw)
    user = security.authenticate(form.get("email", ""), form.get("senha", ""))
    if not user:
        return Response(templates.login("E-mail ou senha inválidos."), 401)
    try:
        token = security.create_session(user["id_usuario"], client_ip(handler), user_agent(handler))
    except RuntimeError as exc:
        return Response(templates.login(str(exc)), 409)
    services.audit(user, "entrou no sistema", "sessao", client_ip(handler), user_agent(handler))
    return redirect("/", {"Set-Cookie": f"conviva_session={token}; Path=/; HttpOnly; SameSite=Lax"})


def logout(handler: Any) -> Response:
    cookie = security.parse_cookie(handler.headers.get("Cookie"))
    token = cookie.get("conviva_session")
    user = security.get_current_user(handler.headers.get("Cookie"))
    services.audit(user, "saiu do sistema", "sessao", client_ip(handler), user_agent(handler))
    security.delete_session(token)
    return redirect("/login", {"Set-Cookie": "conviva_session=; Path=/; Max-Age=0; HttpOnly; SameSite=Lax"})


def dashboard(handler: Any) -> Response:
    user = require_user(handler)
    if isinstance(user, Response):
        return user
    return Response(templates.dashboard(user, services.list_votacoes()))


def list_votacoes(handler: Any, message: str = "", error: str = "") -> Response:
    user = require_user(handler)
    if isinstance(user, Response):
        return user
    return Response(templates.votacoes(user, services.list_votacoes(), message, error))


def nova_votacao_form(handler: Any, error: str = "") -> Response:
    user = require_admin(handler)
    if isinstance(user, Response):
        return user
    reunioes = services.list_reunioes()
    pautas = {r["id_reuniao"]: services.list_pautas_by_reuniao(r["id_reuniao"]) for r in reunioes}
    return Response(templates.form_votacao(user, reunioes, pautas, error))


def nova_votacao_post(handler: Any, raw: bytes) -> Response:
    user = require_admin(handler)
    if isinstance(user, Response):
        return user
    form = parse_form(raw)
    try:
        services.create_votacao(form, user, client_ip(handler), user_agent(handler))
        return redirect("/votacoes")
    except Exception as exc:
        return nova_votacao_form(handler, str(exc))


def iniciar_votacao(handler: Any, id_votacao: int) -> Response:
    user = require_admin(handler)
    if isinstance(user, Response):
        return user
    try:
        services.iniciar_votacao(id_votacao, user, client_ip(handler), user_agent(handler))
        return redirect("/votacoes")
    except Exception as exc:
        return list_votacoes(handler, error=str(exc))


def encerrar_votacao(handler: Any, id_votacao: int) -> Response:
    user = require_admin(handler)
    if isinstance(user, Response):
        return user
    try:
        services.encerrar_votacao(id_votacao, user, client_ip(handler), user_agent(handler))
        return redirect(f"/votacoes/{id_votacao}/resultado")
    except Exception as exc:
        return list_votacoes(handler, error=str(exc))


def votar_form(handler: Any, id_votacao: int, error: str = "", message: str = "") -> Response:
    user = require_user(handler)
    if isinstance(user, Response):
        return user
    data = services.resultado_votacao(id_votacao)
    votacao = data["votacao"]
    if votacao["status"] != "ativa" and not message:
        return Response(templates.resultado(user, data, "A votação não está ativa."))
    peso = services.calcular_peso_usuario(user["id_usuario"], votacao["id_condominio"])
    return Response(templates.votar(user, data, services.get_opcoes(id_votacao), peso, error, message))


def votar_post(handler: Any, id_votacao: int, raw: bytes) -> Response:
    user = require_user(handler)
    if isinstance(user, Response):
        return user
    form = parse_form(raw)
    try:
        services.registrar_voto(id_votacao, form.get("id_opcao") or [], user, client_ip(handler), user_agent(handler))
        return votar_form(handler, id_votacao, message="Voto confirmado com sucesso.")
    except Exception as exc:
        return votar_form(handler, id_votacao, error=str(exc))


def resultado(handler: Any, id_votacao: int) -> Response:
    user = require_user(handler)
    if isinstance(user, Response):
        return user
    result = services.resultado_votacao(id_votacao)
    if result["votacao"]["status"] not in {"encerrada", "invalidada"}:
        return Response(templates.resultado(user, result, "O resultado só fica disponível após o encerramento da votação."))
    services.audit(user, "visualizou resultado", f"votacao:{id_votacao}", client_ip(handler), user_agent(handler))
    return Response(templates.resultado(user, result))


def logs(handler: Any) -> Response:
    user = require_admin(handler)
    if isinstance(user, Response):
        return user
    return Response(templates.logs(user, services.list_logs()))
