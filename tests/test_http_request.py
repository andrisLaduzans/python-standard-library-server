import unittest

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
