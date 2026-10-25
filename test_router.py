import unittest
from http import HTTPStatus

from http_method import Method
from router import Router, Routes
from todo import TodoField


class TestRouter(unittest.TestCase):
    def setUp(self):
        self.router = Router()
        self.router.add_route(Method.GET, Routes.Todos.todos, lambda: None)
        self.router.add_route(Method.GET, Routes.Todos.todos_id, lambda: None)

    def test_resolve_returns_matching_route(self):
        route, *_ = self.router.resolve(Method.GET, Routes.Todos.todos)
        self.assertIsNotNone(route)
        self.assertEqual(
            {"method": Method.GET, "path": Routes.Todos.todos}, route.to_dict()
        )

    def test_resolve_extracts_todo_id(self):
        route, params, *_ = self.router.resolve(Method.GET, Routes.Todos.with_id("1234"))
        self.assertIsNotNone(route)
        self.assertEqual(
            {"method": Method.GET, "path": Routes.Todos.todos_id}, route.to_dict()
        )
        self.assertEqual({TodoField.ID: "1234"}, params)

    def test_unknown_path(self):
        for path in ["/user", "/unknown", Routes.Todos.with_id("1234/extra")]:
            with self.subTest(path=path):
                route, _, _, status, _ = self.router.resolve(Method.GET, path)
                self.assertIsNone(route)
                self.assertEqual(404, status)

    def test_unsupported_method(self):
        route, _, _, status, allowed = self.router.resolve(
            Method.POST, Routes.Todos.with_id("1234")
        )
        self.assertIsNone(route)
        self.assertEqual(HTTPStatus.METHOD_NOT_ALLOWED, status)
        self.assertEqual([Method.GET], allowed)

    def test_query_params(self):
        route, _, query, *_ = self.router.resolve(
            Method.GET,
            Routes.Todos.todos + "?page=2&sort=name&campaign=test&campaign=lala",
        )
        self.assertIsNotNone(route)
        self.assertEqual(
            {"page": ["2"], "sort": [TodoField.NAME], "campaign": ["test", "lala"]}, query
        )
