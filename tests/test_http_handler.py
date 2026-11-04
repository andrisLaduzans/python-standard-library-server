import io
import socket
from http import HTTPStatus
from unittest.mock import patch

from tests.utils.test_server import LOCALHOST_ADDRESS, TestServer
from todo_api.error import (
    InvalidJsonError,
    MethodNotAllowedError,
    NotFoundError,
    PayloadTooLargeError,
    TodoNotFoundError,
    ValidationError,
)
from todo_api.http_layer.http_handler import MAX_REQUEST_BODY_SIZE
from todo_api.http_layer.http_method import Method
from todo_api.http_layer.router import Routes
from todo_api.todos.todo import TodoField


class HttpHandlerTest(TestServer):
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
            {"Content-Type": "application/json"},
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
            (
                Method.POST,
                Routes.Todos.todos,
                "POST Body Must Not Be Empty",
                {"Content-Type": "application/json"},
            ),
            (
                Method.PATCH,
                Routes.Todos.with_id(self.todo.uuid),
                "PATCH Body Must Not Be Empty",
                {"Content-Type": "application/json"},
            ),
        ]

        for method, path, message, header in cases:
            with self.subTest(method=method):
                response, data = self.request(
                    method,
                    path,
                    {},
                    header,
                )
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
        with socket.create_connection(
            (LOCALHOST_ADDRESS, self.server.server_port)
        ) as sock:
            request = (
                f"{Method.POST} {Routes.Todos.todos} HTTP/1.1\r\n"
                "Host: localhost\r\n"
                f"Content-Length: {MAX_REQUEST_BODY_SIZE + 1}\r\n"
                f"Authorization: Bearer {self.token}\r\n"
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

    def test_search_todos(self):
        with self.subTest("Should be able to search todo with search param"):
            response, data = self.request(Method.GET, Routes.Todos.todos + "?search=3")
            self.assertEqual(HTTPStatus.OK, response.status)

            expected = ["todo_3"]
            actual = [item[TodoField.NAME] for item in data]
            self.assertEqual(expected, actual)

        with self.subTest("Should be able to combine search with is done filter"):
            response, data = self.request(
                Method.GET, Routes.Todos.todos + "?is_done=true&search=2&search=4"
            )
            self.assertEqual(HTTPStatus.OK, response.status)
            self.assertEqual(
                [
                    {
                        "name": "todo_2",
                        "is_done": True,
                    },
                    {
                        "name": "todo_4",
                        "is_done": True,
                    },
                ],
                [
                    {
                        TodoField.NAME: item[TodoField.NAME],
                        TodoField.IS_DONE: item[TodoField.IS_DONE],
                    }
                    for item in data
                ],
            )

    def test_request_logging_middleware_logs_request(self):
        with self.assertLogs("todo_api.http_layer.middleware", level="INFO") as logs:
            response, data = self.request(Method.GET, Routes.Todos.todos)

            self.assertEqual(HTTPStatus.OK, response.status)
            self.assertEqual(5, len(data))
            self.assertIn(
                "method=GET path=/todos status=200 duration_ms=", logs.output[0]
            )

    def test_request_logging_middleware_logs_not_found_response(self):
        with self.assertLogs("todo_api.http_layer.middleware", level="INFO") as logs:
            response, _ = self.request(Method.GET, "/unknown")

        self.assertEqual(HTTPStatus.NOT_FOUND, response.status)
        self.assertIn("status=404", logs.output[0])

    def test_unsupported_content_type_returns_415(self):
        body = {
            TodoField.NAME: "eat breakfast",
            TodoField.DESCRIPTION: "valid json, wrong content type",
        }
        response, data = self.request(
            Method.POST, Routes.Todos.todos, body, headers={"Content-Type": "text/plain"}
        )
        self.assertEqual(HTTPStatus.UNSUPPORTED_MEDIA_TYPE, response.status)

    def test_malformed_json_returns_400(self):
        response, data = self.request(Method.POST, Routes.Todos.todos, b"{")
        self.assert_error(
            response,
            data,
            HTTPStatus.BAD_REQUEST,
            InvalidJsonError.ERROR.code,
            InvalidJsonError.ERROR.message,
        )

    def test_standard_library_access_log_is_silenced(self):
        with patch("sys.stderr", new_callable=io.StringIO) as stderr:
            self.request(Method.GET, Routes.Todos.todos)
        self.assertEqual("", stderr.getvalue())

    def test_request_log_includes_user_id(self):
        with self.assertLogs("todo_api.http_layer.middleware", level="INFO") as logs:
            self.request(Method.GET, Routes.Todos.todos)
        self.assertIn(f"user_id={self.user_id}", logs.output[0])

    def test_request_log_marks_anonymous_use(self):
        with self.assertLogs("todo_api.http_layer.middleware", level="INFO") as logs:
            self.request(Method.GET, Routes.Todos.todos, authenticated=False)
        self.assertIn("user_id=-", logs.output[0])
