import unittest
from http import HTTPStatus

from todo_api.http_layer.app import App
from todo_api.http_layer.http_method import Method
from todo_api.http_layer.http_request import HttpRequest
from todo_api.http_layer.http_response import HttpResponse
from todo_api.http_layer.router import Router, Routes


def ok_view(request: HttpRequest, params: dict[str, str]) -> HttpResponse:
    return HttpResponse.json(HTTPStatus.OK, {"ok": True})


def failing_view(request: HttpRequest, params: dict[str, str]) -> HttpResponse:
    raise RuntimeError("error")


class TestApp(unittest.TestCase):
    def setUp(self) -> None:
        router = Router()
        router.add_route(Method.GET, Routes.Todos.todos, ok_view)
        router.add_route(Method.GET, Routes.Todos.todos_id, failing_view)
        self.app = App(router)

    @staticmethod
    def authenticated_request(path: str) -> HttpRequest:
        request = HttpRequest(Method.GET, path)
        request.user_id = "user-1"
        return request

    def test_returns_view_response(self):
        response = self.app(self.authenticated_request(Routes.Todos.todos))
        self.assertEqual(HTTPStatus.OK, response.status)
        self.assertEqual(b'{"ok": true}', response.body)

    def test_missing_user_returns_401(self):
        response = self.app(HttpRequest(Method.GET, Routes.Todos.todos))
        self.assertEqual(HTTPStatus.UNAUTHORIZED, response.status)
        self.assertEqual("Bearer", response.headers["WWW-Authenticate"])

    def test_unknown_path_returns_404(self):
        response = self.app(self.authenticated_request("/unkown"))
        self.assertEqual(HTTPStatus.NOT_FOUND, response.status)

    def test_unexpected_exception_returns_500(self):
        with self.assertLogs("todo_api.http_layer.app", level="ERROR"):
            response = self.app(self.authenticated_request(Routes.Todos.with_id("1")))
        self.assertEqual(HTTPStatus.INTERNAL_SERVER_ERROR, response.status)
