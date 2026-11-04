from http.server import BaseHTTPRequestHandler

from todo_api.error import (
    AppError,
    InvalidRequestError,
    PayloadTooLargeError,
)
from todo_api.http_layer.app import App
from todo_api.http_layer.http_method import Method
from todo_api.http_layer.http_request import HttpRequest
from todo_api.http_layer.http_response import HttpResponse

MAX_REQUEST_BODY_SIZE = 1024 * 1024  # 1MiB


class HttpHandler(BaseHTTPRequestHandler):
    def __init__(self, request, client_address, server, *, app: App):
        self.app = app
        super().__init__(request, client_address, server)

    def _read_body(self) -> bytes:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError as error:
            raise InvalidRequestError from error

        if length < 0:
            raise InvalidRequestError
        if length > MAX_REQUEST_BODY_SIZE:
            raise PayloadTooLargeError

        return self.rfile.read(length)

    def _handle_request(self, method: Method) -> None:
        try:
            body = self._read_body()
        except AppError as error:
            response = HttpResponse.error(error)
        else:
            response = self.app(HttpRequest(method, self.path, self.headers, body))
        self._send_response(response)

    def _send_response(self, response: HttpResponse) -> None:
        self.send_response(response.status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response.body)))

        for name, value in response.headers.items():
            self.send_header(name, value)

        self.end_headers()
        self.wfile.write(response.body)

    def do_GET(self):
        self._handle_request(Method.GET)

    def do_POST(self):
        self._handle_request(Method.POST)

    def do_DELETE(self):
        self._handle_request(Method.DELETE)

    def do_PATCH(self):
        self._handle_request(Method.PATCH)

    def send_error(
        self, code: int, message: str | None = None, explain: str | None = None
    ) -> None:
        message = message or self.responses.get(code, ("Unknown Error",))[0]
        self._send_response(
            HttpResponse.json(
                code, {"error": {"code": "unknown_error", "message": message}}
            )
        )
