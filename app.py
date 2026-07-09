from __future__ import annotations

import io
import os
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from src.controllers import ApplicationController

HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))

_controller = ApplicationController()
_db_ready = False


def _ensure_database_once() -> None:
    global _db_ready
    if _db_ready:
        return
    _controller.ensure_database()
    _db_ready = True


class ConvivaHandler(BaseHTTPRequestHandler):
    controller = _controller

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


def app(environ, start_response):
    """WSGI entrypoint required by Vercel Python runtime."""
    _ensure_database_once()

    method = (environ.get("REQUEST_METHOD") or "GET").upper()
    path = environ.get("PATH_INFO") or "/"
    query = environ.get("QUERY_STRING") or ""

    headers = {}
    for key, value in environ.items():
        if not key.startswith("HTTP_"):
            continue
        header_name = key[5:].replace("_", "-")
        headers[header_name] = value
    if environ.get("CONTENT_TYPE"):
        headers["Content-Type"] = environ["CONTENT_TYPE"]
    if environ.get("CONTENT_LENGTH"):
        headers["Content-Length"] = environ["CONTENT_LENGTH"]

    length = int(environ.get("CONTENT_LENGTH") or 0)
    body_stream = environ.get("wsgi.input") or io.BytesIO(b"")
    body = body_stream.read(length) if length else b""

    response = _controller.dispatch(
        method=method,
        path=path,
        query=query,
        headers=headers,
        body=body,
        client_address=environ.get("REMOTE_ADDR", ""),
    )

    try:
        reason = HTTPStatus(response.status).phrase
    except ValueError:
        reason = "OK"
    status_text = f"{response.status} {reason}"
    wsgi_headers = [(name, value) for name, value in response.headers.items()]
    start_response(status_text, wsgi_headers)
    return [response.body or b""]


def main() -> None:
    _ensure_database_once()
    server = ThreadingHTTPServer((HOST, PORT), ConvivaHandler)
    print(f"CONVIVA rodando em http://localhost:{PORT}")
    print("Use Ctrl+C para parar.")
    server.serve_forever()


if __name__ == "__main__":
    main()
