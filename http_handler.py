import json
import logging
from http.server import BaseHTTPRequestHandler

from error import InvalidRequestError, TodoNotFoundError, ValidationError
from server import Server
from todo import TodoField
from todo_schemas import TodoCreateRequest, TodoListQuery, TodoUpdateRequest
from todo_service import TodoService

logger = logging.getLogger(__name__)


class HttpHandler(BaseHTTPRequestHandler):
    def __init__(self, request, client_address, server: Server):
        self.store = server.store
        self.service = TodoService(self.store)
        self.router = server.router

        super().__init__(request, client_address, server)

    def __response(
        self, status: int, data: dict | list, headers: dict[str, str] | None = None
    ):
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

        body = self.rfile.read(content_length)
        data = json.loads(body)
        return data

    def __dispatch(self, method: str) -> None:
        try:
            route, params, query, status, allowed_methods = self.router.resolve(
                method, self.path
            )

            if status == 405:
                self.__error_response(
                    405,
                    "method_not_allowed",
                    "Method Not Allowed",
                    {"Allow": ", ".join(allowed_methods)},
                )
                return

            if status == 404 or not route:
                self.__error_response(404, "not_found", "Not Found")
                return

            route.action(self, params, query)

        except TodoNotFoundError:
            self.__error_response(404, "item_not_found", "Item Not Found")
            return
        except ValidationError as error:
            self.__error_response(400, "validation_error", str(error))
            return
        except InvalidRequestError:
            self.__error_response(400, "invalid_request", "Invalid Request")
            return
        except json.JSONDecodeError:
            self.__error_response(400, "invalid_json", "Invalid JSON")
            return
        except Exception:
            logger.exception("Unexpected error while handling request")
            self.__error_response(500, "internal_error", "Internal Server Error")

    def do_GET(self):
        self.__dispatch("GET")

    def do_POST(self):
        self.__dispatch("POST")

    def do_DELETE(self):
        self.__dispatch("DELETE")

    def do_PATCH(self):
        self.__dispatch("PATCH")

    def get_todos(self, params=None, query=None):
        query_params = TodoListQuery.from_query_params(query)
        todos = self.service.get_all(is_done=query_params.is_done)
        self.__response(200, todos)

    def get_todo(self, params: dict, query=None):
        todo = self.service.get(params[TodoField.ID])
        self.__response(200, todo)

    def delete_todo(self, params: dict, query=None):
        todo = self.service.delete(params[TodoField.ID])
        self.__response(200, todo)

    def create_todo(self, params=None, query=None):
        data = self.__parse_request()
        request = TodoCreateRequest.from_dict(data)
        todo = self.service.create(request.name, request.description)
        self.__response(201, todo, {"Location": f"/todos/{todo['id']}"})

    def update_todo(self, params: dict, _):
        data = self.__parse_request()
        request = TodoUpdateRequest.from_dict(data)
        todo = self.service.update_todo(params[TodoField.ID], request)
        self.__response(200, todo)

    def send_error(
        self, code: int, message: str | None = None, explain: str | None = None
    ) -> None:
        self.__error_response(
            code,
            "unknown_error",
            message or self.responses.get(code, ("Unknown Error",))[0],
        )

    def __error_response(
        self, status: int, code: str, message: str, headers: dict[str, str] | None = None
    ) -> None:
        self.__response(status, {"error": {"code": code, "message": message}}, headers)
