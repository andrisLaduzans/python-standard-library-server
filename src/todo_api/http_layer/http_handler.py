import json
import logging
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler

from todo_api.error import (
    AppError,
    ErrorCode,
    InternalError,
    InvalidJsonError,
    InvalidRequestError,
    MethodNotAllowedError,
    NotFoundError,
    PayloadTooLargeError,
    TodoNotFoundError,
    ValidationError,
)
from todo_api.http_layer.http_method import Method
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
        self.response_status = None
        dispatch = self.__dispatch
        for middleware_class in reversed(server.middlewares):
            dispatch = middleware_class(self, dispatch)
        self._dispatch = dispatch

        super().__init__(request, client_address, server)

    def __response(
        self, status: int, data: dict | list, headers: dict[str, str] | None = None
    ):
        self.response_status = status
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))

        if headers:
            for keyword, value in headers.items():
                self.send_header(keyword, value)

        self.end_headers()
        self.wfile.write(body)

    def __parse_request(self) -> dict:
        try:
            content_length = int(self.headers.get("Content-Length", "0"))
        except ValueError as error:
            raise InvalidRequestError from error

        if content_length <= 0:
            raise InvalidRequestError

        if content_length > MAX_REQUEST_BODY_SIZE:
            raise PayloadTooLargeError

        body = self.rfile.read(content_length)
        data = json.loads(body)
        return data

    def __dispatch(self, method: str) -> None:
        try:
            route, params, query, status, allowed_methods = self.router.resolve(
                method, self.path
            )

            if status == HTTPStatus.METHOD_NOT_ALLOWED:
                self.__error_response(
                    HTTPStatus.METHOD_NOT_ALLOWED,
                    MethodNotAllowedError.ERROR,
                    {"Allow": ", ".join(allowed_methods)},
                )
                return

            if status == HTTPStatus.NOT_FOUND or not route:
                self.__error_response(HTTPStatus.NOT_FOUND, NotFoundError.ERROR)
                return

            route.action(self, params, query)

        except TodoNotFoundError as error:
            self.__error_response(HTTPStatus.NOT_FOUND, error)
            return
        except (ValidationError, InvalidRequestError) as error:
            self.__error_response(HTTPStatus.BAD_REQUEST, error)
            return
        except PayloadTooLargeError as error:
            self.__error_response(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, error)
            return
        except json.JSONDecodeError, UnicodeDecodeError:
            self.__error_response(HTTPStatus.BAD_REQUEST, InvalidJsonError.ERROR)
            return
        except Exception:
            logger.exception("Unexpected error while handling request")
            self.__error_response(HTTPStatus.INTERNAL_SERVER_ERROR, InternalError.ERROR)

    def do_GET(self):
        self._dispatch(Method.GET)

    def do_POST(self):
        self._dispatch(Method.POST)

    def do_DELETE(self):
        self._dispatch(Method.DELETE)

    def do_PATCH(self):
        self._dispatch(Method.PATCH)

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
        self.__response(HTTPStatus.OK, todos)

    def get_todo(self, params: dict, query=None):
        todo = self.service.find_by_id(params[TodoField.ID])
        self.__response(HTTPStatus.OK, todo)

    def delete_todo(self, params: dict, query=None):
        todo = self.service.delete(params[TodoField.ID])
        self.__response(HTTPStatus.OK, todo)

    def create_todo(self, params=None, query=None):
        data = self.__parse_request()
        request = TodoCreateRequest.from_dict(data)
        todo = self.service.create(request.name, request.description)
        self.__response(
            HTTPStatus.CREATED, todo, {"Location": Routes.Todos.with_id(todo["id"])}
        )

    def update_todo(self, params: dict, _):
        data = self.__parse_request()
        request = TodoUpdateRequest.from_dict(data)
        todo = self.service.update_todo(params[TodoField.ID], request)
        self.__response(HTTPStatus.OK, todo)

    def send_error(
        self, code: int, message: str | None = None, explain: str | None = None
    ) -> None:
        self.__error_response(
            code,
            AppError(
                ErrorCode(
                    "unknown_error",
                    message or self.responses.get(code, ("Unknown Error",))[0],
                ),
            ),
        )

    def __error_response(
        self, status: int, error: AppError, headers: dict[str, str] | None = None
    ) -> None:
        self.__response(
            status, {"error": {"code": error.code, "message": error.message}}, headers
        )
