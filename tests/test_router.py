import unittest

from todo_api.error import MethodNotAllowedError, NotFoundError
from todo_api.http_layer.http_method import Method
from todo_api.http_layer.router import Router, Routes
from todo_api.todos.todo import TodoField


class TestRouter(unittest.TestCase):
    def setUp(self):
        self.router = Router()
        self.router.add_route(Method.GET, Routes.Todos.todos, lambda: None)
        self.router.add_route(Method.GET, Routes.Todos.todos_id, lambda: None)

    def test_resolve_returns_matching_route(self):
        route, _ = self.router.resolve(Method.GET, Routes.Todos.todos)
        self.assertIsNotNone(route)
        self.assertEqual(
            {"method": Method.GET, "path": Routes.Todos.todos}, route.to_dict()
        )

    def test_resolve_extracts_todo_id(self):
        route, params = self.router.resolve(Method.GET, Routes.Todos.with_id("1234"))
        self.assertIsNotNone(route)
        self.assertEqual(
            {"method": Method.GET, "path": Routes.Todos.todos_id}, route.to_dict()
        )
        self.assertEqual({TodoField.ID: "1234"}, params)

    def test_unknown_path(self):
        for path in ["/user", "/unknown", Routes.Todos.with_id("1234/extra")]:
            with self.subTest(path=path), self.assertRaises(NotFoundError):
                self.router.resolve(Method.GET, path)

    def test_unsupported_method(self):
        with self.assertRaises(MethodNotAllowedError) as ctx:
            self.router.resolve(Method.POST, Routes.Todos.with_id("1234"))
        self.assertEqual(Method.GET, ctx.exception.headers["Allow"])
