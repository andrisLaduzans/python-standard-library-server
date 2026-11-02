import logging
from abc import ABC, abstractmethod
from collections.abc import Callable
from time import perf_counter

from todo_api.db.token_store import TokenStore
from todo_api.http_layer.http_request import HttpRequest
from todo_api.http_layer.http_response import HttpResponse

logger = logging.getLogger(__name__)

type GetResponse = Callable[[HttpRequest], HttpResponse]


class Middleware(ABC):
    def __init__(self, get_response: GetResponse):
        self.get_response = get_response

    @abstractmethod
    def __call__(self, request: HttpRequest) -> HttpResponse: ...


class RequestLoggingMiddleware(Middleware):
    def __call__(self, request: HttpRequest) -> HttpResponse:
        started_at = perf_counter()
        response = self.get_response(request)
        elapsed_ms = (perf_counter() - started_at) * 1000

        logger.info(
            "method=%s path=%s status=%s duration_ms=%.2f",
            request.method,
            request.path,
            response.status,
            elapsed_ms,
        )

        return response


class AuthenticationMiddleware(Middleware):
    def __init__(self, get_response: GetResponse, token_store: TokenStore):
        super().__init__(get_response)
        self.token_store = token_store

    def __call__(self, request: HttpRequest) -> HttpResponse:
        authorization = request.headers.get("Authorization", "")
        scheme, _, token = authorization.partition(" ")
        token = token.strip()

        if scheme.lower() == "bearer" and token:
            request.auth = token
            request.user_id = self.token_store.find_user_id(token)

        return self.get_response(request)
