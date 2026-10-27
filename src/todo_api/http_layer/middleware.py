import logging
from collections.abc import Callable
from time import perf_counter
from typing import Protocol
from urllib.parse import urlsplit

from todo_api.http_layer.http_method import Method

logger = logging.getLogger(__name__)


class RequestHandlerT(Protocol):
    path: str
    response_status: int | None


class RequestLoggingMiddleware:
    def __init__(self, handler: RequestHandlerT, next_dispatch: Callable[[Method], None]):
        self.handler = handler
        self.next_dispatch = next_dispatch

    def __call__(self, method: Method) -> None:
        started_at = perf_counter()
        try:
            self.next_dispatch(method)
        finally:
            elapsed_ms = (perf_counter() - started_at) * 1000
            logger.info(
                "method=%s path=%s status=%s duration_ms=%.2f",
                method,
                urlsplit(self.handler.path).path,
                self.handler.response_status,
                elapsed_ms,
            )
