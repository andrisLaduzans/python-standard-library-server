import logging
from http.server import BaseHTTPRequestHandler

from todo_api.error import (
    AppError,
    AuthenticationError,
    ErrorCode,
    InternalError,
    InvalidRequestError,
    PayloadTooLargeError,
)
from todo_api.http_layer.http_method import Method
from todo_api.http_layer.http_request import HttpRequest
from todo_api.http_layer.http_response import HttpResponse
from todo_api.http_layer.server import Server

logger = logging.getLogger(__name__)
MAX_REQUEST_BODY_SIZE = 1024 * 1024  # 1MiB


class HttpHandler(BaseHTTPRequestHandler):
    def __init__(self, request, client_address, server: Server):
        self.router = server.router
        dispatch = self.__dispatch
        for middleware in reversed(server.middlewares):
            dispatch = middleware(dispatch)
        self._dispatch = dispatch
        self.http_request: HttpRequest

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
            self.__send_response(
                self.__create_error_response(error.STATUS, error, error.headers)
            )
            return

        self.http_request = HttpRequest(method, self.path, self.headers, body)
        response = self._dispatch(self.http_request)
        self.__send_response(response)

    def __create_response(
        self, status: int, data: dict | list, headers: dict[str, str] | None = None
    ) -> HttpResponse:
        return HttpResponse.json(status, data, headers or {})

    def __create_error_response(
        self, status: int, error: AppError, headers: dict[str, str] | None = None
    ):
        response = self.__create_response(
            status, {"error": {"code": error.code, "message": error.message}}, headers
        )
        return response

    def __send_response(self, response: HttpResponse) -> None:
        self.send_response(response.status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response.body)))

        for name, value in response.headers.items():
            self.send_header(name, value)

        self.end_headers()
        self.wfile.write(response.body)

    def __dispatch(self, request: HttpRequest) -> HttpResponse:
        try:
            route, params = self.router.resolve(request.method, request.path)

            if request.user_id is None:
                raise AuthenticationError
            response = route.action(request, params)

        except AppError as error:
            response = self.__create_error_response(error.STATUS, error, error.headers)
        except Exception:
            logger.exception("Unexpected error while handling request")
            response = self.__create_error_response(InternalError.STATUS, InternalError())

        return response

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
        error = AppError(
            ErrorCode(
                "unknown_error",
                message or self.responses.get(code, ("Unknown Error",))[0],
            )
        )
        response = self.__create_response(
            code,
            {"error": {"code": error.code, "message": error.message}},
        )
        self.__send_response(response)
