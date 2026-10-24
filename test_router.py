import unittest

from router import Router
from todo import TodoField


class TestRouter(unittest.TestCase):
    def setUp(self):
        self.router = Router()
        self.router.add_route("GET", "/todos", lambda: None)
        self.router.add_route("GET", "/todos/:id", lambda: None)

    def test_resolve_returns_matching_route(self):
        route, *_ = self.router.resolve("GET", "/todos")
        self.assertIsNotNone(route)
        self.assertEqual({"method": "GET", "path": "/todos"}, route.to_dict())

    def test_resolve_extracts_todo_id(self):
        route, params, *_ = self.router.resolve("GET", "/todos/1234")
        self.assertIsNotNone(route)
        self.assertEqual({"method": "GET", "path": "/todos/:id"}, route.to_dict())
        self.assertEqual({TodoField.ID: "1234"}, params)

    def test_unknown_path(self):
        for path in ["/user", "/unknown", "/todos/1234/extra"]:
            with self.subTest(path=path):
                route, _, _, status, _ = self.router.resolve("GET", path)
                self.assertIsNone(route)
                self.assertEqual(404, status)

    def test_unsupported_method(self):
        route, _, _, status, allowed = self.router.resolve("POST", "/todos/1234")
        self.assertIsNone(route)
        self.assertEqual(405, status)
        self.assertEqual(["GET"], allowed)

    def test_query_params(self):
        route, _, query, *_ = self.router.resolve(
            "GET", "/todos?page=2&sort=name&campaign=test&campaign=lala"
        )
        self.assertIsNotNone(route)
        self.assertEqual(
            {"page": ["2"], "sort": [TodoField.NAME], "campaign": ["test", "lala"]}, query
        )
