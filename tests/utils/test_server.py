import json
import tempfile
import unittest
from functools import partial
from http.client import HTTPConnection, HTTPResponse
from pathlib import Path
from threading import Thread
from typing import Any

from todo_api.db.database import Database
from todo_api.db.todo_store import TodoStore
from todo_api.db.token_store import TokenStore
from todo_api.http_layer.http_handler import HttpHandler
from todo_api.http_layer.http_method import Method
from todo_api.http_layer.middleware import (
    AuthenticationMiddleware,
    RequestLoggingMiddleware,
)
from todo_api.http_layer.router import Router, Routes
from todo_api.http_layer.server import Server
from todo_api.todos.todo_service import TodoService
from todo_api.todos.views import TodoViews

LOCALHOST_ADDRESS = "127.0.0.1"


class TestServer(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        database = Database(Path(self.temp_dir.name) / "todos.db")
        database.initialize()
        self.store = TodoStore(database)
        self.token_store = TokenStore(database)
        self.user_id = "test-user"
        self.token = self.token_store.create(self.user_id)

        self.todos = [
            self.store.create(
                f"todo_{idx}",
                f"Todo Description {idx}",
                idx % 2 == 0,
                owner_id=self.user_id,
            )
            for idx in range(5)
        ]
        self.todo = self.todos[0]

        views = TodoViews(TodoService(self.store))

        router = Router()
        router.add_route(Method.GET, Routes.Todos.todos, views.list_todos)
        router.add_route(Method.POST, Routes.Todos.todos, views.create_todo)
        router.add_route(Method.GET, Routes.Todos.todos_id, views.get_todo)
        router.add_route(Method.DELETE, Routes.Todos.todos_id, views.delete_todo)
        router.add_route(Method.PATCH, Routes.Todos.todos_id, views.update_todo)

        self.server = Server(
            (LOCALHOST_ADDRESS, 0),
            HttpHandler,
            store=self.store,
            router=router,
            middlewares=(
                RequestLoggingMiddleware,
                partial(AuthenticationMiddleware, token_store=self.token_store),
            ),
        )
        self.thread = Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

        self.connection = HTTPConnection(LOCALHOST_ADDRESS, self.server.server_port)

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
        body: dict[Any, Any] | bytes | None = None,
        headers: dict[str, str] | None = None,
        authenticated: bool = True,
    ) -> tuple[HTTPResponse, Any]:
        if isinstance(body, dict):
            body = json.dumps(body).encode("utf-8")

        default_headers = {"Content-Type": "application/json"}
        if authenticated:
            default_headers["Authorization"] = f"Bearer {self.token}"

        self.connection.request(
            method, path, body, {**default_headers, **(headers or {})}
        )

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
