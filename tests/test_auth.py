from http import HTTPStatus

from tests.utils.test_server import TestServer
from todo_api.error import AuthenticationError
from todo_api.http_layer.http_method import Method
from todo_api.http_layer.router import Routes


class AuthenticationTest(TestServer):
    def test_missing_authorization_header_returns_401(self):
        response, data = self.request(Method.GET, Routes.Todos.todos, authenticated=False)

        self.assert_error(
            response,
            data,
            HTTPStatus.UNAUTHORIZED,
            AuthenticationError.ERROR.code,
            AuthenticationError.ERROR.message,
        )
        self.assertEqual("Bearer", response.getheader("WWW-Authenticate"))

    def test_malformed_authorization_header_returns_401(self):
        response, data = self.request(
            Method.GET,
            Routes.Todos.todos,
            headers={"Authorization": "invalid-token"},
        )
        self.assert_error(
            response,
            data,
            HTTPStatus.UNAUTHORIZED,
            AuthenticationError.ERROR.code,
            AuthenticationError.ERROR.message,
        )
        self.assertEqual("Bearer", response.getheader("WWW-Authenticate"))

    def test_unknown_token_returns_401(self):
        response, data = self.request(
            Method.GET, Routes.Todos.todos, headers={"Authorization": "Bearer unknown"}
        )

        self.assert_error(
            response,
            data,
            HTTPStatus.UNAUTHORIZED,
            AuthenticationError.ERROR.code,
            AuthenticationError.ERROR.message,
        )
        self.assertEqual("Bearer", response.getheader("WWW-Authenticate"))
