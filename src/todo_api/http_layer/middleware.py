import logging
from abc import ABC, abstractmethod
from collections.abc import Callable
from time import perf_counter
from typing import Protocol
from urllib.parse import urlsplit

from todo_api.http_layer.http_method import Method
from todo_api.http_layer.http_request import HttpRequest
from todo_api.http_layer.http_response import HttpResponse

logger = logging.getLogger(__name__)


class RequestHandlerT(Protocol):
    http_request: HttpRequest


class Middleware(ABC):
    def __init__(
        self, handler: RequestHandlerT, next_dispatch: Callable[[Method], HttpResponse]
    ):
        self.handler = handler
        self.next_dispatch = next_dispatch

    @abstractmethod
    def __call__(self, method: Method) -> HttpResponse: ...


class RequestLoggingMiddleware(Middleware):
    def __call__(self, method: Method) -> HttpResponse:
        started_at = perf_counter()
        response = self.next_dispatch(method)
        elapsed_ms = (perf_counter() - started_at) * 1000

        http_request = self.handler.http_request
        logger.info(
            "method=%s path=%s status=%s duration_ms=%.2f",
            http_request.method,
            urlsplit(http_request.target).path,
            response.status,
            elapsed_ms,
        )

        return response


class AuthenticationMiddleware(Middleware):
    def __call__(self, method: Method) -> HttpResponse:
        http_request = self.handler.http_request
        authorization = http_request.headers.get("Authorization", "")
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() == "bearer" and token.strip():
            http_request.auth = token.strip()

        return self.next_dispatch(method)
