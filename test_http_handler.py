import json
import tempfile
import unittest
from http.client import HTTPConnection
from pathlib import Path
from threading import Thread
from typing import Any

from database import Database
from http_handler import HttpHandler
from router import Router
from server import Server
from todo import TodoField
from todo_store import TodoStore


class HttpHandlerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        database = Database(Path(self.temp_dir.name) / "todos.db")
        database.initialize()
        self.store = TodoStore(database)

        self.todo = self.store.create("read a book", "Read a book")
        self.store.create("learn python", "Learn Python server development")
        self.store.create("go to bed")
        self.completed_todo = self.store.create("done todo")
        self.store.update_todo(
            self.completed_todo.uuid,
            {TodoField.IS_DONE: True},
        )

        router = Router()
        router.add_route("GET", "/todos", HttpHandler.get_todos)
        router.add_route("POST", "/todos", HttpHandler.create_todo)
        router.add_route("GET", "/todos/:id", HttpHandler.get_todo)
        router.add_route("DELETE", "/todos/:id", HttpHandler.delete_todo)
        router.add_route("PATCH", "/todos/:id", HttpHandler.update_todo)

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
        data = json.loads(raw_body) if raw_body else None
        return response, data

    def assert_error(
        self,
        response,
        data: dict,
        status: int,
        code: str,
        message: str,
    ) -> None:
        self.assertEqual(status, response.status)
        self.assertEqual(
            {"error": {"code": code, "message": message}},
            data,
        )

    def test_get_todos_returns_200(self) -> None:
        response, data = self.request("GET", "/todos")

        self.assertEqual(200, response.status)
        self.assertEqual("application/json", response.getheader("Content-Type"))
        self.assertEqual(4, len(data))

    def test_unknown_path_returns_404(self) -> None:
        response, data = self.request("GET", "/unknown")

        self.assert_error(response, data, 404, "not_found", "Not Found")

    def test_unsupported_method_returns_405(self) -> None:
        response, data = self.request("DELETE", "/todos")

        self.assert_error(response, data, 405, "method_not_allowed", "Method Not Allowed")
        self.assertEqual("GET, POST", response.getheader("Allow"))

    def test_nonexistent_todo_returns_404(self) -> None:
        response, data = self.request("GET", "/todos/non-existent")

        self.assert_error(response, data, 404, "item_not_found", "Item Not Found")

    def test_create_requires_name(self) -> None:
        response, data = self.request(
            "POST",
            "/todos",
            {TodoField.DESCRIPTION: "Read a book"},
        )

        self.assert_error(
            response,
            data,
            400,
            "validation_error",
            "Field 'name' Is Required",
        )

    def test_create_todo_returns_201(self) -> None:
        response, data = self.request(
            "POST",
            "/todos",
            {
                TodoField.NAME: "eat breakfast",
                TodoField.DESCRIPTION: "After learning some python ofcourse",
            },
        )

        self.assertEqual(201, response.status)
        self.assertEqual(
            f"/todos/{data[TodoField.ID]}",
            response.getheader("Location"),
        )
        self.assertEqual(
            {
                TodoField.ID: data[TodoField.ID],
                TodoField.NAME: "eat breakfast",
                TodoField.DESCRIPTION: "After learning some python ofcourse",
                TodoField.IS_DONE: False,
            },
            data,
        )

    def test_patch_rejects_id_field(self) -> None:
        response, data = self.request(
            "PATCH",
            f"/todos/{self.todo.uuid}",
            {TodoField.ID: "1234", TodoField.NAME: "changed"},
        )

        self.assert_error(
            response,
            data,
            400,
            "validation_error",
            "ID Field Cannot Be Modified",
        )

    def test_patch_accepts_partial_data(self) -> None:
        response, data = self.request(
            "PATCH",
            f"/todos/{self.todo.uuid}",
            {TodoField.IS_DONE: True},
        )

        self.assertEqual(200, response.status)
        self.assertEqual(
            {**self.todo.to_dict(), TodoField.IS_DONE: True},
            data,
        )

    def test_create_and_patch_reject_unknown_fields(self) -> None:
        cases = [
            ("POST", "/todos", {TodoField.NAME: "valid", "something": "else"}),
            ("PATCH", f"/todos/{self.todo.uuid}", {"something": "else"}),
        ]

        for method, path, body in cases:
            with self.subTest(method=method):
                response, data = self.request(method, path, body)
                self.assert_error(
                    response,
                    data,
                    400,
                    "validation_error",
                    "Unknown Field 'something'",
                )

    def test_create_and_patch_reject_empty_body(self) -> None:
        cases = [
            ("POST", "/todos", "POST Body Must Not Be Empty"),
            ("PATCH", f"/todos/{self.todo.uuid}", "PATCH Body Must Not Be Empty"),
        ]

        for method, path, message in cases:
            with self.subTest(method=method):
                response, data = self.request(method, path, {})
                self.assert_error(response, data, 400, "validation_error", message)

    def test_filter_todos_by_completion_status(self) -> None:
        cases = [
            ("true", ["done todo"]),
            ("false", ["read a book", "learn python", "go to bed"]),
            (None, ["read a book", "learn python", "go to bed", "done todo"]),
        ]

        for value, expected_names in cases:
            with self.subTest(is_done=value):
                path = "/todos" if value is None else f"/todos?is_done={value}"
                response, data = self.request("GET", path)

                self.assertEqual(200, response.status)
                self.assertEqual(
                    expected_names,
                    [todo[TodoField.NAME] for todo in data],
                )

                if value is not None:
                    expected_status = value == "true"
                    self.assertTrue(
                        all(todo[TodoField.IS_DONE] is expected_status for todo in data)
                    )

    def test_invalid_completion_filter_returns_400(self) -> None:
        response, data = self.request("GET", "/todos?is_done=invalid")

        self.assert_error(
            response,
            data,
            400,
            "validation_error",
            f"'{TodoField.IS_DONE}' Must Be 'true' or 'false'",
        )

    def test_patch_can_clear_description(self) -> None:
        response, data = self.request(
            "PATCH",
            f"/todos/{self.todo.uuid}",
            {TodoField.DESCRIPTION: None},
        )

        self.assertEqual(200, response.status)
        self.assertIsNone(data[TodoField.DESCRIPTION])
        self.assertEqual("read a book", data[TodoField.NAME])
