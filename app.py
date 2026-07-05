from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from conviva_votacao import controllers

HOST = "0.0.0.0"
PORT = 8000


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


if __name__ == "__main__":
    server = ThreadingHTTPServer((HOST, PORT), ConvivaHandler)
    print(f"CONVIVA rodando em http://{HOST}:{PORT}")
    print("Use Ctrl+C para parar.")
    server.serve_forever()
