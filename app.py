from __future__ import annotations

import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from src.controllers import ApplicationController

HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))


class ConvivaHandler(BaseHTTPRequestHandler):
    controller = ApplicationController()

    def do_GET(self) -> None:
        self._dispatch()

    def do_POST(self) -> None:
        self._dispatch()

    def log_message(self, format: str, *args) -> None:
        if os.getenv("CONVIVA_HTTP_LOG", "0") == "1":
            super().log_message(format, *args)

    def _dispatch(self) -> None:
        parsed = urlparse(self.path)
        length = int(self.headers.get("Content-Length", "0") or 0)
        body = self.rfile.read(length) if length else b""
        response = self.controller.dispatch(
            method=self.command.upper(),
            path=parsed.path,
            query=parsed.query,
            headers=self.headers,
            body=body,
            client_address=self.client_address[0] if self.client_address else "",
        )
        self.send_response(response.status)
        for key, value in response.headers.items():
            self.send_header(key, value)
        self.end_headers()
        if response.body:
            self.wfile.write(response.body)


def main() -> None:
    ConvivaHandler.controller.ensure_database()
    server = ThreadingHTTPServer((HOST, PORT), ConvivaHandler)
    print(f"CONVIVA rodando em http://localhost:{PORT}")
    print("Use Ctrl+C para parar.")
    server.serve_forever()


if __name__ == "__main__":
    main()
