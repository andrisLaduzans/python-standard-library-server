import unittest
from http.client import HTTPMessage

from todo_api.error import (
    InvalidRequestError,
    UnsupportedMediaTypeError,
)
from todo_api.http_layer.http_method import Method
from todo_api.http_layer.http_request import HttpRequest
from todo_api.http_layer.router import Routes
from todo_api.todos.todo import TodoField


class HttpRequestTest(unittest.TestCase):
    def test_path_excludes_query_string(self):
        request = HttpRequest(Method.GET, Routes.Todos.todos + "?is_done=true")
        self.assertEqual("/todos", request.path)

    def test_query_params(self):
        request = HttpRequest(
            Method.GET,
            Routes.Todos.todos + "?page=2&sort=name&campaign=test&campaign=lala",
        )
        self.assertEqual(
            {"page": ["2"], "sort": [TodoField.NAME], "campaign": ["test", "lala"]},
            request.query,
        )

    def test_json_rejects_empty_body(self):
        request = HttpRequest(Method.POST, Routes.Todos.todos)

        with self.assertRaises(InvalidRequestError):
            request.json()

    def test_json_rejects_non_json_content_type(self):
        headers = HTTPMessage()
        headers["Content-Type"] = "text/plain"
        request = HttpRequest(Method.POST, Routes.Todos.todos, headers, b"{}")
        with self.assertRaises(UnsupportedMediaTypeError):
            request.json()
