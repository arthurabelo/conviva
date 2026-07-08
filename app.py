import io
import os
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from conviva_votacao import controllers, models
from seed import main as seed_main

HOST = "0.0.0.0"
PORT = int(os.getenv("PORT", "8000"))


def bootstrap_database() -> None:
    try:
        seed_main()
    except Exception as exc:
        print(f"Bootstrap de banco falhou: {exc}")


if os.getenv("VERCEL") == "1" or "gunicorn" in sys.modules:
    bootstrap_database()


class ConvivaHandler(BaseHTTPRequestHandler):
    def _send(self, response: controllers.Response) -> None:
        self.send_response(int(response.status))
        self.send_header("Content-Type", "text/html; charset=utf-8")
        for key, value in response.headers.items():
            self.send_header(key, value)
        self.end_headers()
        if response.body:
            self.wfile.write(response.body.encode("utf-8"))

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/login":
            return self._send(controllers.get_login(self))
        if path == "/logout":
            return self._send(controllers.logout(self))
        if path == "/":
            return self._send(controllers.dashboard(self))
        if path == "/votacoes":
            return self._send(controllers.list_votacoes(self))
        if path == "/votacoes/nova":
            return self._send(controllers.nova_votacao_form(self))
        if path == "/logs":
            return self._send(controllers.logs(self))
        parts = [p for p in path.split("/") if p]
        if len(parts) == 3 and parts[0] == "votacoes" and parts[2] == "votar":
            return self._send(controllers.votar_form(self, int(parts[1])))
        if len(parts) == 3 and parts[0] == "votacoes" and parts[2] == "resultado":
            return self._send(controllers.resultado(self, int(parts[1])))
        self._send(controllers.Response("<h1>404 - Página não encontrada</h1>", 404))

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length)
        path = urlparse(self.path).path
        if path == "/login":
            return self._send(controllers.post_login(self, raw))
        if path == "/votacoes/nova":
            return self._send(controllers.nova_votacao_post(self, raw))
        parts = [p for p in path.split("/") if p]
        if len(parts) == 3 and parts[0] == "votacoes" and parts[2] == "iniciar":
            return self._send(controllers.iniciar_votacao(self, int(parts[1])))
        if len(parts) == 3 and parts[0] == "votacoes" and parts[2] == "encerrar":
            return self._send(controllers.encerrar_votacao(self, int(parts[1])))
        if len(parts) == 3 and parts[0] == "votacoes" and parts[2] == "votar":
            return self._send(controllers.votar_post(self, int(parts[1]), raw))
        self._send(controllers.Response("<h1>404 - Página não encontrada</h1>", 404))


class WSGIHandlerAdapter:
    def __init__(self, method: str, path: str, headers: dict[str, str], body: bytes, remote_addr: str = "0.0.0.0"):
        self.command = method
        self.path = path
        self.headers = headers
        self.client_address = (remote_addr, 0)
        self.rfile = io.BytesIO(body)


def _build_headers(environ: dict[str, str]) -> dict[str, str]:
    headers: dict[str, str] = {}
    for name, value in environ.items():
        if name.startswith("HTTP_"):
            header_name = name[5:].replace("_", "-").title()
            headers[header_name] = value
    if "CONTENT_TYPE" in environ:
        headers["Content-Type"] = environ["CONTENT_TYPE"]
    if "CONTENT_LENGTH" in environ:
        headers["Content-Length"] = environ["CONTENT_LENGTH"]
    return headers


def _render_wsgi_response(response: controllers.Response, start_response):
    status = int(response.status)
    status_line = f"{status} {HTTPStatus(status).phrase}"
    response_headers = [(key, value) for key, value in response.headers.items()]
    if not any(key.lower() == "content-type" for key, _ in response_headers):
        response_headers.append(("Content-Type", "text/html; charset=utf-8"))
    body_bytes = response.body.encode("utf-8") if response.body else b""
    response_headers.append(("Content-Length", str(len(body_bytes))))
    start_response(status_line, response_headers)
    return [body_bytes]


def app(environ, start_response):
    path = environ.get("PATH_INFO", "/")
    method = environ.get("REQUEST_METHOD", "GET").upper()
    headers = _build_headers(environ)
    body = environ["wsgi.input"].read(int(environ.get("CONTENT_LENGTH", "0") or 0))
    remote_addr = environ.get("REMOTE_ADDR", "0.0.0.0")
    handler = WSGIHandlerAdapter(method, path, headers, body, remote_addr)

    if method == "GET":
        if path == "/login":
            response = controllers.get_login(handler)
        elif path == "/logout":
            response = controllers.logout(handler)
        elif path == "/":
            response = controllers.dashboard(handler)
        elif path == "/votacoes":
            response = controllers.list_votacoes(handler)
        elif path == "/votacoes/nova":
            response = controllers.nova_votacao_form(handler)
        elif path == "/logs":
            response = controllers.logs(handler)
        else:
            parts = [p for p in path.split("/") if p]
            if len(parts) == 3 and parts[0] == "votacoes" and parts[2] == "votar":
                response = controllers.votar_form(handler, int(parts[1]))
            elif len(parts) == 3 and parts[0] == "votacoes" and parts[2] == "resultado":
                response = controllers.resultado(handler, int(parts[1]))
            else:
                response = controllers.Response("<h1>404 - Página não encontrada</h1>", 404)
    elif method == "POST":
        if path == "/login":
            response = controllers.post_login(handler, body)
        elif path == "/votacoes/nova":
            response = controllers.nova_votacao_post(handler, body)
        else:
            parts = [p for p in path.split("/") if p]
            if len(parts) == 3 and parts[0] == "votacoes" and parts[2] == "iniciar":
                response = controllers.iniciar_votacao(handler, int(parts[1]))
            elif len(parts) == 3 and parts[0] == "votacoes" and parts[2] == "encerrar":
                response = controllers.encerrar_votacao(handler, int(parts[1]))
            elif len(parts) == 3 and parts[0] == "votacoes" and parts[2] == "votar":
                response = controllers.votar_post(handler, int(parts[1]), body)
            else:
                response = controllers.Response("<h1>404 - Página não encontrada</h1>", 404)
    else:
        response = controllers.Response("<h1>405 - Método não permitido</h1>", 405)

    return _render_wsgi_response(response, start_response)


application = app


if __name__ == "__main__":
    bootstrap_database()
    server = ThreadingHTTPServer((HOST, PORT), ConvivaHandler)
    print(f"CONVIVA rodando em http://{HOST}:{PORT}")
    print("Use Ctrl+C para parar.")
    server.serve_forever()
