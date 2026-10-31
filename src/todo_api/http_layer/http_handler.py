import json
import logging
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler

from todo_api.error import (
    AppError,
    AuthenticationError,
    ErrorCode,
    InternalError,
    InvalidJsonError,
    InvalidRequestError,
    MethodNotAllowedError,
    NotFoundError,
    PayloadTooLargeError,
    TodoNotFoundError,
    UnsupportedMediaTypeError,
    ValidationError,
)
from todo_api.http_layer.http_method import Method
from todo_api.http_layer.http_request import HttpRequest
from todo_api.http_layer.http_response import HttpResponse
from todo_api.http_layer.router import Routes
from todo_api.http_layer.server import Server
from todo_api.todos.todo import TodoField
from todo_api.todos.todo_schemas import (
    TodoCreateRequest,
    TodoListQuery,
    TodoUpdateRequest,
)
from todo_api.todos.todo_service import TodoService

logger = logging.getLogger(__name__)
MAX_REQUEST_BODY_SIZE = 1024 * 1024  # 1MiB


class HttpHandler(BaseHTTPRequestHandler):
    def __init__(self, request, client_address, server: Server):
        self.store = server.store
        self.service = TodoService(self.store)
        self.router = server.router
        dispatch = self.__dispatch
        for middleware_class in reversed(server.middlewares):
            dispatch = middleware_class(self, dispatch)
        self._dispatch = dispatch
        self.http_request: HttpRequest

        super().__init__(request, client_address, server)

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

    def __parse_request(self) -> dict:
        try:
            content_length = int(self.http_request.headers.get("Content-Length", "0"))
        except ValueError as error:
            raise InvalidRequestError from error

        if content_length <= 0:
            raise InvalidRequestError

        if content_length > MAX_REQUEST_BODY_SIZE:
            raise PayloadTooLargeError

        content_type = self.http_request.headers.get("Content-Type", "")
        if not content_type.startswith("application/json"):
            raise UnsupportedMediaTypeError

        body = self.rfile.read(content_length)
        self.http_request.body = body
        data = self.http_request.json()
        return data

    def __dispatch(self, method: str) -> HttpResponse:
        try:
            route, params, query, status, allowed_methods = self.router.resolve(
                self.http_request
            )

            if status == HTTPStatus.METHOD_NOT_ALLOWED:
                response = self.__create_error_response(
                    HTTPStatus.METHOD_NOT_ALLOWED,
                    MethodNotAllowedError.ERROR,
                    {"Allow": ", ".join(allowed_methods)},
                )

            elif status == HTTPStatus.NOT_FOUND or not route:
                response = self.__create_error_response(
                    HTTPStatus.NOT_FOUND, NotFoundError.ERROR
                )

            elif self.http_request.auth is None:
                raise AuthenticationError

            else:
                response = route.action(self, params, query)

        except TodoNotFoundError as error:
            response = self.__create_error_response(HTTPStatus.NOT_FOUND, error)
        except (ValidationError, InvalidRequestError) as error:
            response = self.__create_error_response(HTTPStatus.BAD_REQUEST, error)
        except PayloadTooLargeError as error:
            response = self.__create_error_response(
                HTTPStatus.REQUEST_ENTITY_TOO_LARGE, error
            )
        except json.JSONDecodeError, UnicodeDecodeError:
            response = self.__create_error_response(
                HTTPStatus.BAD_REQUEST, InvalidJsonError.ERROR
            )
        except UnsupportedMediaTypeError as error:
            response = self.__create_error_response(
                HTTPStatus.UNSUPPORTED_MEDIA_TYPE, error
            )
        except AuthenticationError as error:
            response = self.__create_error_response(
                HTTPStatus.UNAUTHORIZED, error, {"WWW-Authenticate": "Bearer"}
            )
        except Exception:
            logger.exception("Unexpected error while handling request")
            response = self.__create_error_response(
                HTTPStatus.INTERNAL_SERVER_ERROR, InternalError.ERROR
            )

        return response

    def _handle_request(self, method: str) -> None:
        self.http_request = HttpRequest(method, self.path, self.headers)
        response = self._dispatch(method)
        self.__send_response(response)

    def do_GET(self):
        self._handle_request(Method.GET)

    def do_POST(self):
        self._handle_request(Method.POST)

    def do_DELETE(self):
        self._handle_request(Method.DELETE)

    def do_PATCH(self):
        self._handle_request(Method.PATCH)

    def get_todos(self, params=None, query=None):
        query_params = TodoListQuery.from_query_params(query)
        todos = self.service.get_all(
            is_done=query_params.is_done,
            limit=query_params.limit,
            offset=query_params.offset,
            sort_by=query_params.sort_by,
            sort_order=query_params.sort_order,
            search=query_params.search,
        )
        response = self.__create_response(HTTPStatus.OK, todos)
        return response

    def get_todo(self, params: dict, query=None):
        todo = self.service.find_by_id(params[TodoField.ID])
        response = self.__create_response(HTTPStatus.OK, todo)
        return response

    def delete_todo(self, params: dict, query=None):
        todo = self.service.delete(params[TodoField.ID])
        response = self.__create_response(HTTPStatus.OK, todo)
        return response

    def create_todo(self, params=None, query=None):
        data = self.__parse_request()
        request = TodoCreateRequest.from_dict(data)
        todo = self.service.create(request.name, request.description)
        response = self.__create_response(
            HTTPStatus.CREATED, todo, {"Location": Routes.Todos.with_id(todo["id"])}
        )
        return response

    def update_todo(self, params: dict, _):
        data = self.__parse_request()
        request = TodoUpdateRequest.from_dict(data)
        todo = self.service.update_todo(params[TodoField.ID], request)
        response = self.__create_response(HTTPStatus.OK, todo)
        return response

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
