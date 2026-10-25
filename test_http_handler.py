import json
import socket
import tempfile
import unittest
from http import HTTPStatus
from http.client import HTTPConnection
from pathlib import Path
from threading import Thread
from typing import Any

from database import Database
from error import (
    InvalidJsonError,
    MethodNotAllowedError,
    NotFoundError,
    PayloadTooLargeError,
    TodoNotFoundError,
    ValidationError,
)
from http_handler import MAX_REQUEST_BODY_SIZE, HttpHandler
from http_method import Method
from router import Router, Routes
from server import Server
from todo import TodoField
from todo_store import TodoStore


class HttpHandlerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        database = Database(Path(self.temp_dir.name) / "todos.db")
        database.initialize()
        self.store = TodoStore(database)

        self.todos = [
            self.store.create(
                f"todo_{idx}",
                f"Todo Description {idx}",
                idx % 2 == 0,
            )
            for idx in range(5)
        ]
        self.todo = self.todos[0]

        router = Router()
        router.add_route(Method.GET, Routes.Todos.todos, HttpHandler.get_todos)
        router.add_route(Method.POST, Routes.Todos.todos, HttpHandler.create_todo)
        router.add_route(Method.GET, Routes.Todos.todos_id, HttpHandler.get_todo)
        router.add_route(Method.DELETE, Routes.Todos.todos_id, HttpHandler.delete_todo)
        router.add_route(Method.PATCH, Routes.Todos.todos_id, HttpHandler.update_todo)

        self.server = Server(
            ("127.0.0.1", 0),
            HttpHandler,
            store=self.store,
            router=router,
        )
        self.thread = Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

        host, port = self.server.server_address
        self.connection = HTTPConnection(host, port)

    def tearDown(self) -> None:
        self.connection.close()
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.temp_dir.cleanup()

    def request(
        self,
        method: str,
        path: str,
        body: dict[str, Any] | bytes | None = None,
    ):
        if isinstance(body, dict):
            body = json.dumps(body).encode("utf-8")

        self.connection.request(method, path, body)
        response = self.connection.getresponse()
        raw_body = response.read()
        return response, json.loads(raw_body) if raw_body else None

    def assert_error(
        self,
        response,
        data: dict,
        status: int,
        code: str,
        message: str,
    ) -> None:
        self.assertEqual(status, response.status)
        self.assertEqual({"error": {"code": code, "message": message}}, data)

    def test_get_todos_returns_200(self) -> None:
        response, data = self.request(Method.GET, Routes.Todos.todos)

        self.assertEqual(HTTPStatus.OK, response.status)
        self.assertEqual("application/json", response.getheader("Content-Type"))
        self.assertEqual(5, len(data))

    def test_unknown_path_returns_404(self) -> None:
        response, data = self.request(Method.GET, "/unknown")
        self.assert_error(
            response,
            data,
            HTTPStatus.NOT_FOUND,
            NotFoundError.ERROR.code,
            NotFoundError.ERROR.message,
        )

    def test_unsupported_method_returns_405(self) -> None:
        response, data = self.request(Method.DELETE, Routes.Todos.todos)
        self.assert_error(
            response,
            data,
            HTTPStatus.METHOD_NOT_ALLOWED,
            MethodNotAllowedError.ERROR.code,
            MethodNotAllowedError.ERROR.message,
        )
        self.assertEqual(
            f"{Method.GET}, {Method.POST}",
            response.getheader("Allow"),
        )

    def test_nonexistent_todo_returns_404(self) -> None:
        response, data = self.request(Method.GET, Routes.Todos.with_id("non-existent"))
        self.assert_error(
            response,
            data,
            HTTPStatus.NOT_FOUND,
            TodoNotFoundError.ERROR.code,
            TodoNotFoundError.ERROR.message,
        )

    def test_create_requires_name(self) -> None:
        response, data = self.request(
            Method.POST,
            Routes.Todos.todos,
            {TodoField.DESCRIPTION: "Read a book"},
        )
        self.assert_error(
            response,
            data,
            HTTPStatus.BAD_REQUEST,
            ValidationError.ERROR.code,
            "Field 'name' Is Required",
        )

    def test_create_todo_returns_201(self) -> None:
        body = {
            TodoField.NAME: "eat breakfast",
            TodoField.DESCRIPTION: "After learning some python ofcourse",
        }
        response, data = self.request(Method.POST, Routes.Todos.todos, body)

        self.assertEqual(HTTPStatus.CREATED, response.status)
        self.assertEqual(
            Routes.Todos.with_id(data[TodoField.ID]),
            response.getheader("Location"),
        )
        self.assertEqual(
            {
                TodoField.ID: data[TodoField.ID],
                **body,
                TodoField.IS_DONE: False,
            },
            data,
        )

    def test_patch_rejects_id_field(self) -> None:
        response, data = self.request(
            Method.PATCH,
            Routes.Todos.with_id(self.todo.uuid),
            {TodoField.ID: "1234", TodoField.NAME: "changed"},
        )
        self.assert_error(
            response,
            data,
            HTTPStatus.BAD_REQUEST,
            ValidationError.ERROR.code,
            "ID Field Cannot Be Modified",
        )

    def test_create_and_patch_reject_unknown_fields(self) -> None:
        cases = [
            (
                Method.POST,
                Routes.Todos.todos,
                {
                    TodoField.NAME: "valid",
                    "something": "else",
                },
            ),
            (
                Method.PATCH,
                Routes.Todos.with_id(self.todo.uuid),
                {
                    "something": "else",
                },
            ),
        ]

        for method, path, body in cases:
            with self.subTest(method=method):
                response, data = self.request(method, path, body)
                self.assert_error(
                    response,
                    data,
                    HTTPStatus.BAD_REQUEST,
                    ValidationError.ERROR.code,
                    "Unknown Field 'something'",
                )

    def test_create_and_patch_reject_empty_body(self) -> None:
        cases = [
            (Method.POST, Routes.Todos.todos, "POST Body Must Not Be Empty"),
            (
                Method.PATCH,
                Routes.Todos.with_id(self.todo.uuid),
                "PATCH Body Must Not Be Empty",
            ),
        ]

        for method, path, message in cases:
            with self.subTest(method=method):
                response, data = self.request(method, path, {})
                self.assert_error(
                    response,
                    data,
                    HTTPStatus.BAD_REQUEST,
                    ValidationError.ERROR.code,
                    message,
                )

    def test_filter_todos_by_completion_status(self) -> None:
        cases = [
            ("true", [f"todo_{idx}" for idx in (0, 2, 4)]),
            ("false", [f"todo_{idx}" for idx in (1, 3)]),
            (None, [f"todo_{idx}" for idx in range(5)]),
        ]

        for value, expected_names in cases:
            with self.subTest(is_done=value):
                path = Routes.Todos.todos
                if value is not None:
                    path += f"?is_done={value}"

                response, data = self.request(Method.GET, path)

                self.assertEqual(HTTPStatus.OK, response.status)
                self.assertEqual(
                    expected_names,
                    [todo[TodoField.NAME] for todo in data],
                )

    def test_invalid_completion_filter_returns_400(self) -> None:
        response, data = self.request(Method.GET, Routes.Todos.todos + "?is_done=invalid")
        self.assert_error(
            response,
            data,
            HTTPStatus.BAD_REQUEST,
            ValidationError.ERROR.code,
            f"'{TodoField.IS_DONE}' Must Be 'true' or 'false'",
        )

    def test_patch_updates_fields(self) -> None:
        cases = [
            ({TodoField.IS_DONE: True}, TodoField.IS_DONE, True),
            (
                {TodoField.DESCRIPTION: "Updated description"},
                TodoField.DESCRIPTION,
                "Updated description",
            ),
            ({TodoField.DESCRIPTION: None}, TodoField.DESCRIPTION, None),
        ]

        for body, field, expected in cases:
            with self.subTest(field=field, value=expected):
                response, data = self.request(
                    Method.PATCH, Routes.Todos.with_id(self.todo.uuid), body
                )
                self.assertEqual(HTTPStatus.OK, response.status)
                self.assertEqual(expected, data[field])

    def test_invalid_utf8_returns_400(self) -> None:
        response, data = self.request(Method.POST, Routes.Todos.todos, b"\xff")
        self.assert_error(
            response,
            data,
            HTTPStatus.BAD_REQUEST,
            InvalidJsonError.ERROR.code,
            InvalidJsonError.ERROR.message,
        )

    def test_oversized_request_returns_413(self) -> None:
        with socket.create_connection(self.server.server_address) as sock:
            request = (
                f"{Method.POST} {Routes.Todos.todos} HTTP/1.1\r\n"
                "Host: localhost\r\n"
                f"Content-Length: {MAX_REQUEST_BODY_SIZE + 1}\r\n"
                "Connection: close\r\n\r\n"
            )
            sock.sendall(request.encode("ascii"))

            chunks = []
            while chunk := sock.recv(4096):
                chunks.append(chunk)

        response = b"".join(chunks).decode("latin-1")
        self.assertIn(str(HTTPStatus.REQUEST_ENTITY_TOO_LARGE), response)
        self.assertIn(PayloadTooLargeError.ERROR.code, response)
        self.assertIn(PayloadTooLargeError.ERROR.message, response)

    def test_read_all_pagination(self) -> None:
        response, data = self.request(
            Method.GET, Routes.Todos.todos + "?limit=2&offset=1"
        )

        self.assertEqual(HTTPStatus.OK, response.status)
        self.assertEqual(["todo_1", "todo_2"], [todo[TodoField.NAME] for todo in data])

    def test_read_all_sorting(self):
        with self.subTest("Should be able to sort by name in descending order"):
            response, data = self.request(
                Method.GET, Routes.Todos.todos + "?sort_by=name&sort_order=desc"
            )

            self.assertEqual(200, response.status)
            expected = [f"todo_{idx}" for idx in list(range(4, -1, -1))]
            result = [item[TodoField.NAME] for item in data]

            self.assertEqual(expected, result)
