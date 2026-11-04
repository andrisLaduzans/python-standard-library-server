import unittest
from http import HTTPStatus
from http.client import HTTPMessage

from tests.utils.test_store import TestStore
from todo_api.db.token_store import TokenStore
from todo_api.http_layer.http_method import Method
from todo_api.http_layer.http_request import HttpRequest
from todo_api.http_layer.http_response import HttpResponse
from todo_api.http_layer.middleware import AuthenticationMiddleware, RequestIdMiddleware


class AuthenticationMiddlewareTest(TestStore):
    def setUp(self) -> None:
        self._init_database("tokens.db")
        self.token_store = TokenStore(self.database)
        self.token = self.token_store.create("user-1")

    def get_response(self, request: HttpRequest):
        self.seen = request
        return HttpResponse.json(HTTPStatus.OK, {})

    def test_sets_user_id_for_valid_token(self):
        headers = HTTPMessage()
        headers["Authorization"] = f"Bearer {self.token}"
        middleware = AuthenticationMiddleware(self.get_response, self.token_store)
        middleware(HttpRequest(Method.GET, "/todos", headers))
        self.assertEqual("user-1", self.seen.user_id)

    def test_leaves_user_id_unset_without_header(self):
        middleware = AuthenticationMiddleware(self.get_response, self.token_store)
        middleware(HttpRequest(Method.GET, "/todos"))
        self.assertIsNone(self.seen.user_id)


class RequestMiddlewareTest(unittest.TestCase):
    def get_response(self, request):
        self.seen = request
        return HttpResponse.json(HTTPStatus.OK, {})

    def call(self, request_id=None):
        headers = HTTPMessage()
        if request_id is not None:
            headers["X-Request-ID"] = request_id
        middleware = RequestIdMiddleware(self.get_response)
        return middleware(HttpRequest(Method.GET, "/todos", headers))

    def test_generates_request_id_when_missing(self):
        response = self.call()
        request_id = response.headers["X-Request-ID"]
        self.assertEqual(32, len(request_id))
        self.assertEqual(request_id, self.seen.request_id)

    def test_reuses_incoming_request_id(self):
        response = self.call("abc-123")
        self.assertEqual("abc-123", self.seen.request_id)
        self.assertEqual("abc-123", response.headers["X-Request-ID"])

    def test_replaces_invalid_incoming_request_id(self):
        response = self.call("bad id")
        self.assertNotEqual("bad id", response.headers["X-Request-ID"])
